import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { dirname, join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { DurableTaskStore, TASK_STATUS } from '../src/index.mjs'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const workspaceRoot = dirname(projectRoot)
const launcher = join(projectRoot, 'bin', 'start-pemara-dsh.ps1')
const ledgerPath = join(projectRoot, '.runtime', 'dsh-home', 'pemara', 'ledger.sqlite')

function toolCallEvents(id, name, args) {
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
      usage: { prompt_tokens: 16, completion_tokens: 8 },
    }),
    '[DONE]',
  ]
}

function textEvents(text) {
  return [
    JSON.stringify({ choices: [{ delta: { role: 'assistant', content: '' }, index: 0, finish_reason: null }] }),
    JSON.stringify({ choices: [{ delta: { content: text }, index: 0, finish_reason: null }] }),
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

function runHarness(prompt) {
  const shell = join(process.env.SystemRoot ?? 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
  return new Promise((resolve, reject) => {
    const child = spawn(shell, [
      '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
      '-File', launcher, '-Workspace', workspaceRoot, prompt,
    ], {
      cwd: projectRoot,
      env: { ...process.env, DSH_TELEMETRY_MODE: 'DISABLED' },
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk })
    child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk })
    child.on('error', reject)
    child.on('close', code => resolve({ code, stdout, stderr }))
  })
}

test('real DSH profile routes through the Qwen OpenAI seam and executes Pemara tools', {
  skip: process.platform !== 'win32',
  timeout: 120_000,
}, async () => {
  const taskId = `qwen-route-e2e-${process.pid}-${Date.now()}`
  const chatRequests = []
  const agentRequests = []
  const authHeaders = []
  const server = createServer((request, response) => {
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
      chatRequests.push(body)
      authHeaders.push(request.headers.authorization)
      const toolNames = (body.tools ?? []).map(tool => tool.function?.name)
      if (!toolNames.includes('harness_task_create')) {
        sendEvents(response, textEvents('Pemara Qwen Route Test'))
        return
      }

      agentRequests.push(body)
      if (agentRequests.length === 1) {
        sendEvents(response, toolCallEvents('qwen-create', 'harness_task_create', {
          task_id: taskId,
          objective: 'Provar a rota Qwen real do perfil Pemara sem usar GPU.',
          max_rounds: 3,
        }))
      }
      else if (agentRequests.length === 2) {
        sendEvents(response, toolCallEvents('qwen-checkpoint', 'harness_task_checkpoint', {
          task_id: taskId,
          summary: 'Rota Qwen local e ferramenta de criação executadas.',
          next_action: 'Solicitar verificação independente da conclusão.',
          artifacts: ['qwen-profile-e2e'],
        }))
      }
      else if (agentRequests.length === 3) {
        sendEvents(response, toolCallEvents('qwen-complete', 'harness_task_request_completion', {
          task_id: taskId,
          summary: 'Rota Qwen e ferramenta durável executadas.',
          evidence: ['DSH recebeu e executou chamadas OpenAI-compatible locais.'],
        }))
      }
      else {
        sendEvents(response, textEvents(`PEMARA_QWEN_ROUTE_OK task=${taskId}`))
      }
    })
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(11436, '127.0.0.1', resolve)
  })

  try {
    const result = await runHarness('Execute a prova deterministica da rota Qwen Pemara e finalize com o marcador solicitado.')
    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.match(result.stdout, new RegExp(`PEMARA_QWEN_ROUTE_OK task=${taskId}`))
    assert.equal(agentRequests.length, 4)
    assert.equal(agentRequests[0].model, 'qwen3.8-27b-uncensored-yarn-524k')
    assert.equal(agentRequests[0].reasoning_effort, 'low')
    assert.ok(agentRequests[0].tools.some(tool => tool.function?.name === 'harness_task_create'))
    assert.ok(agentRequests[0].tools.some(tool => tool.function?.name === 'harness_task_checkpoint'))
    assert.ok(agentRequests[0].tools.some(tool => tool.function?.name === 'harness_task_request_completion'))
    assert.ok(chatRequests.length >= agentRequests.length)
    assert.ok(authHeaders.every(value => value === 'Bearer llama-local'))

    const catalogMessage = agentRequests[0].messages
      .map(message => Array.isArray(message.content)
        ? message.content.map(part => part.text ?? '').join('\n')
        : String(message.content ?? ''))
      .find(content => content.includes('<available_skills>'))
    assert.ok(catalogMessage, 'the E:\\Pemara skill catalog must reach the model')
    const skillNames = [...catalogMessage.matchAll(/^- `([^`]+)`: /gm)]
      .map(match => match[1])
    assert.equal(skillNames.length, 296)
    assert.ok(skillNames.includes('pemara-ecosystem-orchestrator'))
    assert.ok(skillNames.includes('test-driven-development'))
    assert.ok(!skillNames.includes('hsb-app'))

    const store = new DurableTaskStore({ databasePath: ledgerPath })
    try {
      assert.equal(store.getTask(taskId).status, TASK_STATUS.COMPLETED_PENDING_VERIFY)
      const verified = store.verifyCompletion(taskId, {
        verifier: 'qwen-route-e2e-host-gate',
        outcome: 'pass',
        evidence: ['4 agent OpenAI-compatible requests; 3 Pemara tool calls; DSH exit 0.'],
      })
      assert.equal(verified.status, TASK_STATUS.COMPLETED_VERIFIED)
    }
    finally {
      store.close()
    }
  }
  finally {
    await new Promise(resolve => server.close(resolve))
  }
})
