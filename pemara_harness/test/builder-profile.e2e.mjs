import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { DurableTaskStore, TASK_STATUS } from '../src/index.mjs'
import { EXPECTED_BUILDER_TOOLS } from '../src/builder-contract.mjs'
import { EXPECTED_BUILDER_TOOLS_V2, MIN_PROTECTED_PATHS_V2 } from '../src/builder-contract-v2.mjs'
import {
  stageBuilderSkills,
  validateBuilderProfile,
  validateBuilderRequest,
} from '../dsh/builder-policy.mjs'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const dshRoot = join(projectRoot, '..', 'third_party', 'deepseek-harness')
const dshCli = join(dshRoot, 'apps', 'cli', 'src', 'bin.ts')
const tsxLoader = join(dshRoot, 'node_modules', 'tsx', 'dist', 'esm', 'index.mjs')
const nodeUserInfoFallback = join(projectRoot, 'bin', 'node-os-userinfo-fallback.cjs')
const builderHome = join(projectRoot, '.runtime', 'dsh-home-builder')
const builderProfile = join(builderHome, 'profiles', 'pemara-builder')
const builderV2Profile = join(builderHome, 'profiles', 'pemara-builder-v2')
const builderLedger = join(builderHome, 'pemara-builder', 'ledger.sqlite')
const operationalProfile = join(projectRoot, '.runtime', 'dsh-home', 'profiles', 'pemara')
const operationalLedger = join(projectRoot, '.runtime', 'dsh-home', 'pemara', 'ledger.sqlite')
const skillRoot = join(dirname(projectRoot), '.agents', 'skills')
const approvedSkills = [
  'test-driven-development',
  'incremental-implementation',
  'api-and-interface-design',
  'observability-and-instrumentation',
]

function sha256(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function profileHashes() {
  return Object.fromEntries(
    ['cordis.patch.yml', 'cordis.yml', 'package.json', 'pnpm-workspace.yaml']
      .map(name => [name, sha256(join(operationalProfile, name))]),
  )
}

function toolEvents(id, name, args) {
  return [
    JSON.stringify({
      choices: [{
        delta: {
          tool_calls: [{
            index: 0,
            id,
            type: 'function',
            function: { name, arguments: JSON.stringify(args) },
          }],
        },
        index: 0,
        finish_reason: null,
      }],
    }),
    JSON.stringify({
      choices: [{ delta: {}, index: 0, finish_reason: 'tool_calls' }],
      usage: { prompt_tokens: 20, completion_tokens: 8 },
    }),
    '[DONE]',
  ]
}

function textEvents(content) {
  return [
    JSON.stringify({ choices: [{ delta: { role: 'assistant', content: '' }, index: 0, finish_reason: null }] }),
    JSON.stringify({ choices: [{ delta: { content }, index: 0, finish_reason: null }] }),
    JSON.stringify({
      choices: [{ delta: {}, index: 0, finish_reason: 'stop' }],
      usage: { prompt_tokens: 20, completion_tokens: 4 },
    }),
    '[DONE]',
  ]
}

function sendEvents(response, events) {
  response.writeHead(200, { 'content-type': 'text/event-stream' })
  response.end(`${events.map(event => `data: ${event}`).join('\n\n')}\n\n`)
}

function runDsh({
  workspace,
  overlay,
  prompt,
  profile = 'pemara-builder',
  env = {},
  timeoutMs = 180_000,
}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [
      '--require', nodeUserInfoFallback,
      '--import', pathToFileURL(tsxLoader).href,
      dshCli,
      '--profile', profile,
      '--patch', overlay,
      prompt,
    ], {
      cwd: workspace,
      env: {
        ...process.env,
        DSH_HOME: builderHome,
        DSH_PERMISSION_MODE: 'read-only',
        DSH_TELEMETRY_MODE: 'DISABLED',
        DSH_TOOLS_MODE: 'native',
        PEMARA_QWEN_API_KEY: 'llama-local',
        TSX_TSCONFIG_PATH: join(dshRoot, 'tsconfig.json'),
        ...env,
      },
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk })
    child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk })
    const timer = setTimeout(() => {
      child.kill()
      reject(new Error(`Builder E2E timed out after ${timeoutMs} ms\n${stderr}\n${stdout}`))
    }, timeoutMs)
    child.once('error', (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.once('close', (code) => {
      clearTimeout(timer)
      resolve({ code, stdout, stderr })
    })
  })
}

function mockOverlay(port, { builderV2 = false, ledgerPath } = {}) {
  const harnessOverride = builderV2
    ? `
- id: pemara-durable-harness
  config:
    databasePath: '${ledgerPath.replaceAll('\\', '/')}'
    leaseMs: 30000
    builderPackagePath: !!js process.env.PEMARA_BUILDER_PACKAGE
    builderWorkspace: !!js process.env.PEMARA_BUILDER_WORKSPACE
    builderContractVersion: !!js process.env.PEMARA_BUILDER_CONTRACT_VERSION
`
    : ''
  return `
- id: llm-pi-ai
  config:
    providers:
      pemara-qwen38:
        displayName: Pemara Builder E2E Loopback
        apiKeyEnv: PEMARA_QWEN_API_KEY
        api: openai-completions
        baseURL: http://127.0.0.1:${port}/v1
        reasoning: low
        compat:
          thinkingFormat: deepseek
          supportsDeveloperRole: false
          maxTokensField: max_tokens
        models:
          - id: qwen3.8-27b-uncensored-yarn-524k
            name: Qwen Builder E2E
            contextWindow: 524288
            maxTokens: 16384
            input: [text, image]
            reasoningEfforts:
              off:
              low: low
              medium: medium
              xhigh: xhigh
${harnessOverride}
`
}

function builderV2Package(source, taskId) {
  return {
    contract_version: 2,
    task_id: taskId,
    objective: 'Replace work.txt and prove the protected result.',
    allowed_paths: ['work.txt'],
    forbidden_paths: [...MIN_PROTECTED_PATHS_V2],
    acceptance_commands: ['verify-work'],
    command_allowlist: [{
      id: 'verify-work',
      runtime: 'node',
      args: ['-e', "import {readFileSync,writeFileSync} from 'node:fs'; import {tmpdir} from 'node:os'; import {join} from 'node:path'; import http2 from 'node:http2'; import dns from 'node:dns'; if(readFileSync('work.txt','utf8')!=='new\\n') process.exit(19); const scratchFile=join(tmpdir(),'scratch-ok.txt'); writeFileSync(scratchFile,'ok'); if(readFileSync(scratchFile,'utf8')!=='ok') process.exit(20); try { await fetch('http://127.0.0.1:9/') ; process.exit(18) } catch (error) { if(error.code!=='PEMARA_NETWORK_DENIED') process.exit(17) }; try { writeFileSync('escape.txt','denied') ; process.exit(16) } catch (error) { if(error.code!=='ERR_ACCESS_DENIED') process.exit(15) }; try { http2.connect('http://127.0.0.1:9/'); process.exit(14) } catch (error) { if(error.code!=='PEMARA_NETWORK_DENIED') process.exit(13) }; try { await new dns.promises.Resolver().resolve4('example.com'); process.exit(12) } catch (error) { if(error.code!=='PEMARA_NETWORK_DENIED') process.exit(11) }; try { process.binding('tcp_wrap'); process.exit(10) } catch (error) { if(error.code!=='PEMARA_NETWORK_DENIED') process.exit(9) }; console.log('verified scratch-write-allowed network-denied fs-write-denied http2-denied dns-resolver-denied binding-denied')"],
      cwd: '.',
      timeout_ms: 10_000,
      max_output_bytes: 16_384,
    }],
    file_baselines: { 'work.txt': createHash('sha256').update(source).digest('hex') },
    required_artifacts: ['diff', 'test output', 'checkpoint'],
    skills: [...approvedSkills],
    max_rounds: 6,
    max_files_changed: 1,
    network: 'denied',
    service_control: 'denied',
    gpu_control: 'denied',
    commit_or_publish: 'denied',
    stop_conditions: ['protected test failed', 'path outside scope', 'budget exhausted'],
  }
}

test('real DSH request is fail-closed to five ledger tools and four staged skills', {
  skip: process.platform !== 'win32',
  timeout: 240_000,
}, async () => {
  assert.equal(validateBuilderProfile(builderProfile).ok, true)
  assert.ok(existsSync(dshCli), `DSH source CLI missing: ${dshCli}`)
  assert.ok(existsSync(tsxLoader), `DSH TSX loader missing: ${tsxLoader}`)
  const staged = stageBuilderSkills({
    homeDir: builderHome,
    skills: approvedSkills,
    sourceRoots: [skillRoot],
  })
  assert.equal(staged.ok, true)

  const temporary = mkdtempSync(join(tmpdir(), 'pemara-builder-e2e-'))
  const workspace = join(temporary, 'workspace')
  const overlay = join(temporary, 'mock.patch.yml')
  const agentRequests = []
  const authHeaders = []
  const taskId = `builder-policy-e2e-${process.pid}-${Date.now()}`
  const beforeProfile = profileHashes()
  const beforeOperationalLedger = existsSync(operationalLedger) ? sha256(operationalLedger) : undefined

  let server
  try {
    writeFileSync(join(temporary, 'placeholder'), '')
    // mkdir through the already-created temporary root without shell helpers.
    const { mkdirSync } = await import('node:fs')
    mkdirSync(workspace)

    server = createServer((request, response) => {
      if (request.method === 'GET' && request.url === '/v1/models') {
        response.writeHead(200, { 'content-type': 'application/json' })
        response.end(JSON.stringify({
          object: 'list',
          data: [{ id: 'qwen3.8-27b-uncensored-yarn-524k', object: 'model' }],
        }))
        return
      }

      let raw = ''
      request.setEncoding('utf8')
      request.on('data', chunk => { raw += chunk })
      request.on('end', () => {
        if (request.method !== 'POST' || request.url !== '/v1/chat/completions') {
          response.writeHead(404).end()
          return
        }
        const body = JSON.parse(raw)
        authHeaders.push(request.headers.authorization)
        const toolNames = (body.tools ?? []).map(tool => tool.function?.name)
        if (!toolNames.includes('harness_task_create')) {
          sendEvents(response, textEvents('Pemara Builder Gate'))
          return
        }

        agentRequests.push(body)
        if (agentRequests.length === 1) {
          sendEvents(response, toolEvents('create', 'harness_task_create', {
            task_id: taskId,
            objective: 'Prove the fail-closed Builder request.',
            max_rounds: 3,
          }))
        }
        else if (agentRequests.length === 2) {
          sendEvents(response, toolEvents('round', 'harness_task_begin_round', {
            task_id: taskId,
            provider: 'pemara-qwen38',
            model: 'qwen3.8-27b-uncensored-yarn-524k',
          }))
        }
        else if (agentRequests.length === 3) {
          sendEvents(response, toolEvents('checkpoint', 'harness_task_checkpoint', {
            task_id: taskId,
            summary: 'Builder policy request captured.',
            next_action: 'Request independent host verification.',
          }))
        }
        else if (agentRequests.length === 4) {
          sendEvents(response, toolEvents('complete', 'harness_task_request_completion', {
            task_id: taskId,
            summary: 'Fail-closed Builder route completed.',
            evidence: ['captured request with exact tool and skill surfaces'],
          }))
        }
        else {
          sendEvents(response, textEvents(`PEMARA_BUILDER_POLICY_OK task=${taskId}`))
        }
      })
    })
    await new Promise((resolve, reject) => {
      server.once('error', reject)
      server.listen(0, '127.0.0.1', resolve)
    })
    const address = server.address()
    assert.ok(address && typeof address === 'object')
    writeFileSync(overlay, mockOverlay(address.port))

    const result = await runDsh({
      workspace,
      overlay,
      prompt: 'Run the deterministic Builder policy gate and finish with the required marker.',
    })
    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.match(result.stdout, new RegExp(`PEMARA_BUILDER_POLICY_OK task=${taskId}`))
    assert.ok(agentRequests.length >= 5)

    const first = agentRequests[0]
    const toolNames = (first.tools ?? []).map(tool => tool.function?.name)
    assert.deepEqual(validateBuilderRequest({ tools: toolNames, skills: approvedSkills }), { ok: true, issues: [] })
    assert.deepEqual([...toolNames].sort(), [...EXPECTED_BUILDER_TOOLS].sort())
    for (const forbidden of ['pwsh', 'bash', 'str_replace_editor', 'web_search', 'run_code', 'subagent']) {
      assert.ok(!toolNames.includes(forbidden), `forbidden tool leaked: ${forbidden}`)
    }

    const promptText = first.messages
      .map(message => Array.isArray(message.content)
        ? message.content.map(part => part.text ?? '').join('\n')
        : String(message.content ?? ''))
      .join('\n')
    const catalog = promptText.match(/<available_skills>([\s\S]*?)<\/available_skills>/)?.[1] ?? ''
    const names = [...catalog.matchAll(/^- `([^`]+)`: /gm)].map(match => match[1])
    assert.deepEqual(names.sort(), [...approvedSkills].sort())
    assert.ok(authHeaders.every(value => value === 'Bearer llama-local'))
    assert.equal(first.model, 'qwen3.8-27b-uncensored-yarn-524k')
    assert.equal(first.reasoning_effort, 'low')

    const store = new DurableTaskStore({ databasePath: builderLedger })
    try {
      assert.equal(store.getTask(taskId).status, TASK_STATUS.COMPLETED_PENDING_VERIFY)
    }
    finally {
      store.close()
    }

    assert.deepEqual(profileHashes(), beforeProfile)
    if (beforeOperationalLedger !== undefined) {
      assert.equal(sha256(operationalLedger), beforeOperationalLedger)
    }
    assert.deepEqual(readdirSync(workspace), [])
  }
  finally {
    if (server) await new Promise(resolve => server.close(resolve))
    rmSync(temporary, { recursive: true, force: true })
  }
})

test('real DSH Builder v2 edits and tests only through the eight protected tools', {
  skip: process.platform !== 'win32',
  timeout: 240_000,
}, async () => {
  assert.equal(validateBuilderProfile(builderV2Profile, {
    profileName: 'pemara-builder-v2',
    ledgerRel: 'pemara-builder-v2/ledger.sqlite',
    contractVersion: 2,
  }).ok, true)
  assert.ok(existsSync(dshCli), `DSH source CLI missing: ${dshCli}`)
  assert.ok(existsSync(tsxLoader), `DSH TSX loader missing: ${tsxLoader}`)
  const staged = stageBuilderSkills({
    homeDir: builderHome,
    skills: approvedSkills,
    sourceRoots: [skillRoot],
  })
  assert.equal(staged.ok, true)

  const temporary = mkdtempSync(join(tmpdir(), 'pemara-builder-v2-e2e-'))
  const workspace = join(temporary, 'workspace')
  const packagePath = join(temporary, 'builder-package.json')
  const ledgerPath = join(temporary, 'ledger.sqlite')
  const overlay = join(temporary, 'mock.patch.yml')
  const source = 'old\n'
  const taskId = 'QB-998'
  const agentRequests = []
  const authHeaders = []
  const beforeProfile = profileHashes()
  const beforeOperationalLedger = existsSync(operationalLedger) ? sha256(operationalLedger) : undefined

  let server
  try {
    mkdirSync(workspace)
    writeFileSync(join(workspace, 'work.txt'), source)
    writeFileSync(packagePath, JSON.stringify(builderV2Package(source, taskId), null, 2))

    server = createServer((request, response) => {
      if (request.method === 'GET' && request.url === '/v1/models') {
        response.writeHead(200, { 'content-type': 'application/json' })
        response.end(JSON.stringify({
          object: 'list',
          data: [{ id: 'qwen3.8-27b-uncensored-yarn-524k', object: 'model' }],
        }))
        return
      }

      let raw = ''
      request.setEncoding('utf8')
      request.on('data', chunk => { raw += chunk })
      request.on('end', () => {
        if (request.method !== 'POST' || request.url !== '/v1/chat/completions') {
          response.writeHead(404).end()
          return
        }
        const body = JSON.parse(raw)
        authHeaders.push(request.headers.authorization)
        const toolNames = (body.tools ?? []).map(tool => tool.function?.name)
        if (!toolNames.includes('builder_file_write')) {
          sendEvents(response, textEvents('Pemara Builder v2 Gate'))
          return
        }

        agentRequests.push(body)
        const actions = [
          ['create-v2', 'harness_task_create', {
            task_id: taskId,
            objective: 'Replace work.txt and prove the protected result.',
            max_rounds: 6,
          }],
          ['round-v2', 'harness_task_begin_round', {
            task_id: taskId,
            provider: 'pemara-qwen38',
            model: 'qwen3.8-27b-uncensored-yarn-524k',
          }],
          ['checkpoint-before-v2', 'harness_task_checkpoint', {
            task_id: taskId,
            summary: 'Contract and baseline loaded.',
            next_action: 'Read the allowed file.',
          }],
          ['read-v2', 'builder_file_read', { task_id: taskId, path: 'work.txt' }],
          ['write-v2', 'builder_file_write', { task_id: taskId, path: 'work.txt', content: 'new\n' }],
          ['checkpoint-after-v2', 'harness_task_checkpoint', {
            task_id: taskId,
            summary: 'Allowed file atomically replaced.',
            next_action: 'Run the fixed protected test.',
            artifacts: ['work.txt'],
          }],
          ['test-v2', 'builder_test_run', { task_id: taskId, command_id: 'verify-work' }],
          ['checkpoint-tested-v2', 'harness_task_checkpoint', {
            task_id: taskId,
            summary: 'Protected test passed after the atomic write.',
            next_action: 'Request independent host verification.',
            artifacts: ['work.txt', 'verify-work output'],
          }],
          ['complete-v2', 'harness_task_request_completion', {
            task_id: taskId,
            summary: 'Builder v2 edit and protected test completed.',
            evidence: ['atomic write effect', 'protected test effect', 'durable checkpoints'],
          }],
        ]
        const action = actions[agentRequests.length - 1]
        if (action) sendEvents(response, toolEvents(...action))
        else sendEvents(response, textEvents(`PEMARA_BUILDER_V2_OK task=${taskId}`))
      })
    })
    await new Promise((resolve, reject) => {
      server.once('error', reject)
      server.listen(0, '127.0.0.1', resolve)
    })
    const address = server.address()
    assert.ok(address && typeof address === 'object')
    writeFileSync(overlay, mockOverlay(address.port, { builderV2: true, ledgerPath }))

    const result = await runDsh({
      workspace,
      overlay,
      profile: 'pemara-builder-v2',
      prompt: 'Run the deterministic Builder v2 protected edit gate and finish with the required marker.',
      env: {
        PEMARA_BUILDER_PACKAGE: packagePath,
        PEMARA_BUILDER_WORKSPACE: workspace,
        PEMARA_BUILDER_CONTRACT_VERSION: '2',
      },
    })
    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.match(result.stdout, new RegExp(`PEMARA_BUILDER_V2_OK task=${taskId}`))
    assert.ok(agentRequests.length >= 10)

    const first = agentRequests[0]
    const toolNames = (first.tools ?? []).map(tool => tool.function?.name)
    assert.deepEqual(validateBuilderRequest({
      tools: toolNames,
      skills: approvedSkills,
      contractVersion: 2,
    }), { ok: true, issues: [] })
    assert.deepEqual([...toolNames].sort(), [...EXPECTED_BUILDER_TOOLS_V2].sort())
    for (const forbidden of ['pwsh', 'bash', 'str_replace_editor', 'web_search', 'run_code', 'subagent', 'git']) {
      assert.ok(!toolNames.includes(forbidden), `forbidden tool leaked: ${forbidden}`)
    }
    assert.ok(authHeaders.every(value => value === 'Bearer llama-local'))
    assert.equal(readFileSync(join(workspace, 'work.txt'), 'utf8'), 'new\n')
    assert.equal(existsSync(join(workspace, 'escape.txt')), false)

    const store = new DurableTaskStore({ databasePath: ledgerPath })
    try {
      const effects = store.listEffects(taskId)
      assert.equal(
        store.getTask(taskId).status,
        TASK_STATUS.COMPLETED_PENDING_VERIFY,
        `${result.stderr}\n${result.stdout}\n${JSON.stringify(effects, null, 2)}`,
      )
      assert.ok(effects.some(effect => effect.kind === 'filesystem.atomic-write' && effect.status === 'COMMITTED'))
      assert.ok(effects.some(effect => effect.kind === 'subprocess.allowlisted' && effect.status === 'COMMITTED'))
    }
    finally {
      store.close()
    }

    assert.deepEqual(profileHashes(), beforeProfile)
    if (beforeOperationalLedger !== undefined) {
      assert.equal(sha256(operationalLedger), beforeOperationalLedger)
    }
  }
  finally {
    if (server) await new Promise(resolve => server.close(resolve))
    rmSync(temporary, { recursive: true, force: true })
  }
})
