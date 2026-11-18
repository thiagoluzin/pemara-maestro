import assert from 'node:assert/strict'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'
import {
  reconcileAllowlistedSubprocess,
  runAllowlistedSubprocess,
} from '../src/effects/subprocess.mjs'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const COMMAND = join(ROOT, 'test', 'fixtures', 'subprocess-command.mjs')

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-subprocess-effect-'))
  const workspace = join(root, 'workspace with spaces')
  mkdirSync(workspace)
  const databasePath = join(root, 'ledger.sqlite')
  const store = new DurableTaskStore({ databasePath })
  store.createTask({ id: 'process-task', objective: 'Executar comando permitido' })
  const lease = store.claimTask('process-task', { owner: 'fixture', leaseMs: 60_000 })
  store.startRound('process-task', lease.token)
  store.checkpoint('process-task', lease.token, { summary: 'comando escolhido', nextAction: 'executar uma vez' })
  return {
    root,
    workspace,
    databasePath,
    store,
    lease,
    command(id, mode, options = {}) {
      return {
        [id]: {
          executable: process.execPath,
          args: [COMMAND, mode, ...(options.markerPath ? [options.markerPath] : [])],
          cwd: workspace,
          timeoutMs: options.timeoutMs ?? 2_000,
          maxOutputBytes: options.maxOutputBytes ?? 1_024,
          env: { PEMARA_FIXTURE: 'true' },
        },
      }
    },
    cleanup() {
      store.close()
      rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
    },
  }
}

function alive(pid) {
  try { process.kill(pid, 0); return true } catch { return false }
}

async function waitFor(check, timeoutMs = 8_000) {
  const deadline = Date.now() + timeoutMs
  let lastError
  while (Date.now() < deadline) {
    try {
      const value = check()
      if (value) return value
    }
    catch (error) { lastError = error }
    await new Promise(resolveDelay => setTimeout(resolveDelay, 25))
  }
  throw lastError ?? new Error('condition not met')
}

test('runs only a fixed allowlisted command and journals its bounded output', async () => {
  const fx = fixture()
  try {
    const result = await runAllowlistedSubprocess({
      store: fx.store,
      taskId: 'process-task',
      leaseToken: fx.lease.token,
      key: 'run-success',
      commandId: 'test-success',
      workspaceRoot: fx.workspace,
      commands: fx.command('test-success', 'success'),
    })
    assert.equal(result.status, 'succeeded')
    assert.equal(result.effect.status, 'COMMITTED')
    assert.equal(result.effect.result.stdout, 'subprocess-ok\n')
    assert.equal(result.effect.result.stderr, 'diagnostic-ok\n')
    assert.match(result.effect.request.commandFingerprint, /^[a-f0-9]{64}$/)

    const repeated = await runAllowlistedSubprocess({
      store: fx.store,
      taskId: 'process-task',
      leaseToken: fx.lease.token,
      key: 'run-success',
      commandId: 'test-success',
      workspaceRoot: fx.workspace,
      commands: fx.command('test-success', 'success'),
    })
    assert.equal(repeated.reused, true)
    assert.equal(fx.store.listEffects('process-task').length, 1)
  }
  finally {
    fx.cleanup()
  }
})

test('unknown command ids and sensitive environment overlays fail before an effect', async () => {
  const fx = fixture()
  try {
    await assert.rejects(
      runAllowlistedSubprocess({
        store: fx.store,
        taskId: 'process-task',
        leaseToken: fx.lease.token,
        key: 'not-allowed',
        commandId: 'whoami',
        workspaceRoot: fx.workspace,
        commands: fx.command('test-success', 'success'),
      }),
      error => error?.code === 'SUBPROCESS_COMMAND_DENIED',
    )
    const command = fx.command('bad-env', 'success')
    command['bad-env'].env.API_TOKEN = 'must-not-be-persisted'
    await assert.rejects(
      runAllowlistedSubprocess({
        store: fx.store,
        taskId: 'process-task',
        leaseToken: fx.lease.token,
        key: 'bad-env',
        commandId: 'bad-env',
        workspaceRoot: fx.workspace,
        commands: command,
      }),
      error => error?.code === 'SUBPROCESS_ENV_DENIED',
    )
    assert.equal(fx.store.listEffects('process-task').length, 0)
  }
  finally {
    fx.cleanup()
  }
})

test('allowlisted child receives only the minimal host environment and explicit non-sensitive overlay', async () => {
  const fx = fixture()
  try {
    const result = await runAllowlistedSubprocess({
      store: fx.store,
      taskId: 'process-task',
      leaseToken: fx.lease.token,
      key: 'minimal-environment',
      commandId: 'environment',
      workspaceRoot: fx.workspace,
      commands: fx.command('environment', 'environment'),
    })
    const environment = JSON.parse(result.effect.result.stdout)
    assert.equal(environment.fixture, 'true')
    assert.deepEqual(environment.leaked, [])
  }
  finally {
    fx.cleanup()
  }
})

test('stdout is capped and the truncation is explicit', async () => {
  const fx = fixture()
  try {
    const result = await runAllowlistedSubprocess({
      store: fx.store,
      taskId: 'process-task',
      leaseToken: fx.lease.token,
      key: 'large-output',
      commandId: 'large',
      workspaceRoot: fx.workspace,
      commands: fx.command('large', 'large', { maxOutputBytes: 64 }),
    })
    assert.equal(result.effect.result.stdout.length, 64)
    assert.equal(result.effect.result.stdoutTruncated, true)
  }
  finally {
    fx.cleanup()
  }
})

test('timeout terminates only the allowlisted process tree and records a known failure', async () => {
  const fx = fixture()
  const markerPath = join(fx.root, 'tree.json')
  try {
    const result = await runAllowlistedSubprocess({
      store: fx.store,
      taskId: 'process-task',
      leaseToken: fx.lease.token,
      key: 'timeout-tree',
      commandId: 'hang-tree',
      workspaceRoot: fx.workspace,
      commands: fx.command('hang-tree', 'hang-tree', { markerPath, timeoutMs: 400 }),
    })
    assert.equal(result.status, 'timed_out')
    assert.equal(result.effect.status, 'FAILED')
    assert.equal(result.effect.result.detail.status, 'timed_out')
    const pids = JSON.parse(readFileSync(markerPath, 'utf8'))
    await waitFor(() => !alive(pids.parentPid) && !alive(pids.childPid))
  }
  finally {
    fx.cleanup()
  }
})

test('a live worker after host loss is observed, then terminal state is reconciled once', async () => {
  const fx = fixture()
  let worker
  try {
    await assert.rejects(
      runAllowlistedSubprocess({
        store: fx.store,
        taskId: 'process-task',
        leaseToken: fx.lease.token,
        key: 'host-loss',
        commandId: 'late',
        workspaceRoot: fx.workspace,
        commands: fx.command('late', 'sleep-success', { timeoutMs: 3_000 }),
        fault(step, context) {
          if (step === 'after-worker-spawn') {
            worker = context.worker
            throw new Error('host caiu')
          }
        },
      }),
      /host caiu/,
    )
    const effect = fx.store.listEffects('process-task')[0]
    const statePath = join(fx.root, 'subprocess-effects', `${effect.id}.state.json`)
    const running = await waitFor(() => {
      if (!existsSync(statePath)) return undefined
      const state = JSON.parse(readFileSync(statePath, 'utf8'))
      return state.status === 'running' ? state : undefined
    })
    fx.store.recover()
    const observed = reconcileAllowlistedSubprocess({
      store: fx.store,
      effectId: effect.id,
      resolver: 'host-test',
      evidence: ['worker e fingerprint inspecionados'],
      inspectProcess: pid => ({
        alive: pid === running.workerPid,
        processStartedAt: running.workerStartedAt,
        runnerFingerprint: running.workerFingerprint,
      }),
    })
    assert.equal(observed.status, 'running-observed')
    assert.equal(fx.store.getEffect(effect.id).status, 'OUTCOME_UNKNOWN')

    await waitFor(() => {
      const state = JSON.parse(readFileSync(statePath, 'utf8'))
      return state.status === 'succeeded' ? state : undefined
    })
    const reconciled = reconcileAllowlistedSubprocess({
      store: fx.store,
      effectId: effect.id,
      resolver: 'host-test',
      evidence: ['state terminal atômico inspecionado'],
    })
    assert.equal(reconciled.status, 'committed-from-worker-state')
    assert.equal(reconciled.effect.status, 'COMMITTED')
    assert.equal(reconciled.effect.result.stdout, 'late-success\n')
    await waitFor(() => worker.exitCode !== null || worker.signalCode !== null)
    assert.equal(worker.exitCode, 0)
  }
  finally {
    if (worker?.exitCode === null && worker?.pid !== undefined && alive(worker.pid)) worker.kill('SIGKILL')
    fx.cleanup()
  }
})
