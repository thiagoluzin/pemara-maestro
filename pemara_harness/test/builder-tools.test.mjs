import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { MIN_PROTECTED_PATHS_V2, EXPECTED_BUILDER_TOOLS_V2 } from '../src/builder-contract-v2.mjs'
import { BuilderRuntime } from '../src/builder-runtime.mjs'
import { DurableTaskStore, HarnessStateError } from '../src/index.mjs'
import { apply } from '../dsh/plugin.mjs'

function hash(value) { return createHash('sha256').update(value).digest('hex') }

function harnessContext() {
  const tools = new Map()
  return {
    ctx: {
      tools: { register(definition) { tools.set(definition.name, definition); return () => tools.delete(definition.name) } },
      systemPrompt: { section() { return () => {} } },
    },
    tools,
  }
}

function execution(id = 'builder-session') {
  return { agent: { id }, callId: 'call-1', rootCallId: 'call-1', signal: AbortSignal.timeout(10_000) }
}

function packageFor(workspace, source) {
  return {
    contract_version: 2,
    task_id: 'QB-011',
    objective: 'Replace work.txt and prove the result.',
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
    file_baselines: { 'work.txt': hash(source) },
    required_artifacts: ['diff', 'test output', 'checkpoint'],
    skills: ['test-driven-development', 'debugging-and-error-recovery', 'incremental-implementation'],
    max_rounds: 6,
    max_files_changed: 1,
    network: 'denied',
    service_control: 'denied',
    gpu_control: 'denied',
    commit_or_publish: 'denied',
    stop_conditions: ['protected test failed', 'path outside scope', 'budget exhausted'],
  }
}

test('Builder v2 plugin atomically edits an allowed file and runs only a fixed test id', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'pemara-builder-v2-'))
  const source = 'old\n'
  const packagePath = join(workspace, 'package.json')
  const databasePath = join(workspace, 'ledger.sqlite')
  writeFileSync(join(workspace, 'work.txt'), source)
  writeFileSync(packagePath, JSON.stringify(packageFor(workspace, source)))
  const fake = harnessContext()
  let dispose
  try {
    dispose = apply(fake.ctx, {
      databasePath,
      leaseMs: 60_000,
      builderPackagePath: packagePath,
      builderWorkspace: workspace,
      builderContractVersion: '2',
    })
    assert.deepEqual([...fake.tools.keys()].sort(), [...EXPECTED_BUILDER_TOOLS_V2].sort())

    await fake.tools.get('harness_task_create').execute({
      task_id: 'QB-011',
      objective: 'Replace work.txt and prove the result.',
      max_rounds: 6,
    }, execution())
    const duplicateCreate = await fake.tools.get('harness_task_create').execute({
      task_id: 'QB-011',
      objective: 'Replace work.txt and prove the result.',
      max_rounds: 6,
    }, execution())
    assert.equal(duplicateCreate.task.id, 'QB-011')
    await fake.tools.get('harness_task_begin_round').execute({ task_id: 'QB-011' }, execution())
    await fake.tools.get('harness_task_checkpoint').execute({
      task_id: 'QB-011', summary: 'Baseline lida.', next_action: 'Escrever arquivo.',
    }, execution())

    const before = await fake.tools.get('builder_file_read').execute({ task_id: 'QB-011', path: 'work.txt' }, execution())
    assert.equal(before.file.content, source)
    await assert.rejects(
      () => fake.tools.get('builder_file_read').execute({ task_id: 'QB-011', path: '../RULES.md' }, execution()),
      error => error instanceof HarnessStateError && error.code === 'BUILDER_PATH_DENIED',
    )

    const written = await fake.tools.get('builder_file_write').execute({
      task_id: 'QB-011', path: 'work.txt', content: 'new\n',
    }, execution())
    assert.equal(written.write.path, 'work.txt')
    assert.equal(readFileSync(join(workspace, 'work.txt'), 'utf8'), 'new\n')

    await fake.tools.get('harness_task_checkpoint').execute({
      task_id: 'QB-011', summary: 'Arquivo escrito.', next_action: 'Executar teste fixo.',
    }, execution())
    const checked = await fake.tools.get('builder_test_run').execute({
      task_id: 'QB-011', command_id: 'verify-work',
    }, execution())
    assert.equal(checked.test.status, 'succeeded', JSON.stringify(checked.test.result, null, 2))
    assert.match(checked.test.result.stdout, /verified scratch-write-allowed network-denied fs-write-denied/)
    assert.equal(existsSync(join(workspace, 'escape.txt')), false)

    const repeated = await fake.tools.get('builder_test_run').execute({
      task_id: 'QB-011', command_id: 'verify-work',
    }, execution())
    assert.equal(repeated.test.reused, true)
    await assert.rejects(
      () => fake.tools.get('builder_test_run').execute({ task_id: 'QB-011', command_id: 'pwsh' }, execution()),
      error => error instanceof HarnessStateError && error.code === 'BUILDER_COMMAND_DENIED',
    )
  }
  finally {
    await dispose?.()
    rmSync(workspace, { recursive: true, force: true })
  }
})

test('Builder v2 identity and baseline are host-owned', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'pemara-builder-v2-scope-'))
  const source = 'old\n'
  const packagePath = join(workspace, 'package.json')
  writeFileSync(join(workspace, 'work.txt'), source)
  writeFileSync(packagePath, JSON.stringify(packageFor(workspace, source)))
  const fake = harnessContext()
  let dispose
  try {
    dispose = apply(fake.ctx, {
      databasePath: join(workspace, 'ledger.sqlite'),
      leaseMs: 60_000,
      builderPackagePath: packagePath,
      builderWorkspace: workspace,
      builderContractVersion: '2',
    })
    await assert.rejects(
      () => fake.tools.get('harness_task_create').execute({
        task_id: 'QB-999', objective: 'Do anything', max_rounds: 99,
      }, execution()),
      error => error instanceof HarnessStateError && error.code === 'BUILDER_TASK_SCOPE',
    )
  }
  finally {
    await dispose?.()
    rmSync(workspace, { recursive: true, force: true })
  }

  const drifted = mkdtempSync(join(tmpdir(), 'pemara-builder-v2-drift-'))
  try {
    const packagePath = join(drifted, 'package.json')
    writeFileSync(join(drifted, 'work.txt'), 'changed outside contract\n')
    writeFileSync(packagePath, JSON.stringify(packageFor(drifted, source)))
    assert.throws(
      () => apply(harnessContext().ctx, {
        databasePath: join(drifted, 'ledger.sqlite'),
        leaseMs: 60_000,
        builderPackagePath: packagePath,
        builderWorkspace: drifted,
        builderContractVersion: '2',
      }),
      error => error instanceof HarnessStateError && error.code === 'BUILDER_BASELINE_MISMATCH',
    )
  }
  finally {
    rmSync(drifted, { recursive: true, force: true })
  }
})

test('Builder v2 reconstructs committed writes in causal order after restart', () => {
  const workspace = mkdtempSync(join(tmpdir(), 'pemara-builder-v2-restart-'))
  const source = 'old\n'
  const packagePath = join(workspace, 'package.json')
  const databasePath = join(workspace, 'ledger.sqlite')
  writeFileSync(join(workspace, 'work.txt'), source)
  writeFileSync(packagePath, JSON.stringify(packageFor(workspace, source)))
  let store = new DurableTaskStore({ databasePath, clock: () => 1_000 })
  try {
    store.createTask({ id: 'QB-011', objective: 'Replace work.txt and prove the result.', maxRounds: 6 })
    const lease = store.claimTask('QB-011', { owner: 'restart-fixture', leaseMs: 60_000 })
    store.startRound('QB-011', lease.token)
    store.checkpoint('QB-011', lease.token, { summary: 'baseline', nextAction: 'first write' })
    const runtime = new BuilderRuntime({ store, packagePath, workspaceRoot: workspace })
    runtime.writeFile('QB-011', lease.token, { path: 'work.txt', content: 'one\n' })
    store.checkpoint('QB-011', lease.token, { summary: 'first write', nextAction: 'second write' })
    runtime.writeFile('QB-011', lease.token, { path: 'work.txt', content: 'two\n' })
    store.releaseLease('QB-011', lease.token)
    store.close()

    store = new DurableTaskStore({ databasePath, clock: () => 2_000 })
    assert.doesNotThrow(() => new BuilderRuntime({ store, packagePath, workspaceRoot: workspace }))
    assert.equal(readFileSync(join(workspace, 'work.txt'), 'utf8'), 'two\n')
  }
  finally {
    store.close()
    rmSync(workspace, { recursive: true, force: true })
  }
})

test('Builder v2 rebinds one committed worktree into the supervisor retry session', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'pemara-builder-v2-rebind-'))
  const source = 'old\n'
  const packagePath = join(workspace, 'package.json')
  const databasePath = join(workspace, 'ledger.sqlite')
  writeFileSync(join(workspace, 'work.txt'), source)
  writeFileSync(packagePath, JSON.stringify(packageFor(workspace, source)))
  const first = harnessContext()
  let disposeFirst
  let disposeSecond
  try {
    disposeFirst = apply(first.ctx, {
      databasePath,
      leaseMs: 60_000,
      builderPackagePath: packagePath,
      builderWorkspace: workspace,
      builderContractVersion: '2',
    })
    const sessionA = execution('builder-session-a')
    await first.tools.get('harness_task_create').execute({
      task_id: 'QB-011', objective: 'Replace work.txt and prove the result.', max_rounds: 6,
    }, sessionA)
    await first.tools.get('harness_task_begin_round').execute({ task_id: 'QB-011' }, sessionA)
    await first.tools.get('harness_task_checkpoint').execute({
      task_id: 'QB-011', summary: 'baseline', next_action: 'write',
    }, sessionA)
    await first.tools.get('builder_file_write').execute({
      task_id: 'QB-011', path: 'work.txt', content: 'new\n',
    }, sessionA)
    await first.tools.get('harness_task_checkpoint').execute({
      task_id: 'QB-011', summary: 'write committed', next_action: 'resume in a new session',
    }, sessionA)
    await disposeFirst()
    disposeFirst = undefined

    const second = harnessContext()
    disposeSecond = apply(second.ctx, {
      databasePath,
      leaseMs: 60_000,
      rebindTaskId: 'QB-011',
      rebindAttemptId: 'attempt-retry-1',
      rebindAuthority: 'pemara-supervisor:attempt-retry-1',
      builderPackagePath: packagePath,
      builderWorkspace: workspace,
      builderContractVersion: '2',
    })
    const rebound = await second.tools.get('harness_task_create').execute({
      task_id: 'QB-011', objective: 'Replace work.txt and prove the result.', max_rounds: 6,
    }, execution('builder-session-b'))
    assert.equal(rebound.task.sessionId, 'builder-session-b')
    const store = new DurableTaskStore({ databasePath })
    try {
      assert.equal(store.listEvents('QB-011').at(-1).type, 'task.session_rebound')
      assert.equal(store.getTask('QB-011').sessionId, 'builder-session-b')
    }
    finally { store.close() }
  }
  finally {
    await disposeFirst?.()
    await disposeSecond?.()
    rmSync(workspace, { recursive: true, force: true })
  }
})
