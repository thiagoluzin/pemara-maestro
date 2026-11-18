import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { PassThrough } from 'node:stream'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'
import { runSupervisor } from '../src/supervisor.mjs'
import { SupervisorStore } from '../src/supervisor-store.mjs'

function fixture({ checkpoint = true } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'pemara-supervisor-'))
  const databasePath = join(root, 'ledger.sqlite')
  const ledger = new DurableTaskStore({ databasePath })
  ledger.createTask({ id: 'task-1', objective: 'Concluir o adaptador', maxRounds: 6 })
  if (checkpoint) {
    const lease = ledger.claimTask('task-1', { owner: 'fixture', leaseMs: 60_000 })
    ledger.startRound('task-1', lease.token)
    ledger.checkpoint('task-1', lease.token, {
      summary: 'O contrato já foi escrito',
      nextAction: 'Implementar sem repetir a etapa anterior',
      artifacts: ['test/contract.test.mjs'],
    })
    ledger.releaseLease('task-1', lease.token)
  }
  ledger.close()
  const supervisor = new SupervisorStore({ databasePath })
  supervisor.configureJob({
    taskId: 'task-1',
    executable: process.execPath,
    args: ['fixture-child.mjs', '{{PEMARA_TASK}}'],
    workspace: root,
    maxRestarts: 3,
    backoffMs: [5_000, 15_000, 45_000],
  })
  supervisor.close()
  return {
    root,
    databasePath,
    cleanup() { rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 }) },
  }
}

function fakeChild({ pid, code = 0, stdout = '', stderr = '', onKill } = {}) {
  const child = new EventEmitter()
  child.pid = pid
  child.stdout = new PassThrough()
  child.stderr = new PassThrough()
  child.kill = signal => {
    onKill?.(signal)
    queueMicrotask(() => child.emit('close', null, signal ?? 'SIGTERM'))
    return true
  }
  queueMicrotask(() => {
    if (stdout) child.stdout.write(stdout)
    if (stderr) child.stderr.write(stderr)
    child.stdout.end()
    child.stderr.end()
    child.emit('close', code, null)
  })
  return child
}

test('run once rehydrates the durable checkpoint and journals a successful child', async () => {
  const fx = fixture()
  const launches = []
  try {
    const result = await runSupervisor({
      databasePath: fx.databasePath,
      taskId: 'task-1',
      once: true,
      owner: 'test-host',
      processFingerprint: 'test-supervisor',
      spawnImpl(executable, args, options) {
        launches.push({ executable, args, options })
        return fakeChild({ pid: 7001, stdout: 'obra pronta\n' })
      },
      inspectLaunchedProcess: (_pid, context) => ({
        alive: true,
        processStartedAt: context.startedAt,
        runnerFingerprint: context.expectedFingerprint,
      }),
    })
    assert.equal(result.status, 'COMPLETED')
    assert.equal(launches.length, 1)
    assert.equal(launches[0].executable, process.execPath)
    const prompt = launches[0].args.at(-1)
    assert.match(prompt, /Concluir o adaptador/)
    assert.match(prompt, /O contrato já foi escrito/)
    assert.match(prompt, /Implementar sem repetir a etapa anterior/)
    assert.equal(launches[0].options.shell, false)
    assert.equal(launches[0].options.env.PEMARA_SUPERVISOR_TASK_ID, 'task-1')
    assert.match(launches[0].options.env.PEMARA_SUPERVISOR_ATTEMPT_ID, /^[a-f0-9-]{36}$/)
    assert.match(launches[0].options.env.PEMARA_SUPERVISOR_REBIND_AUTHORITY, /^pemara-supervisor:/)

    const store = new SupervisorStore({ databasePath: fx.databasePath })
    const [attempt] = store.listAttempts('task-1')
    assert.equal(attempt.status, 'SUCCEEDED')
    assert.equal(attempt.exitCode, 0)
    assert.equal(attempt.result.stdout, 'obra pronta\n')
    assert.equal(store.getJob('task-1').lock, undefined)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('once means exactly one process and leaves a failed job resumable after backoff', async () => {
  const fx = fixture()
  let launches = 0
  try {
    const result = await runSupervisor({
      databasePath: fx.databasePath,
      taskId: 'task-1',
      once: true,
      owner: 'test-host',
      processFingerprint: 'test-supervisor',
      spawnImpl() {
        launches += 1
        return fakeChild({ pid: 7100, code: 9, stderr: 'falhou\n' })
      },
    })
    assert.equal(launches, 1)
    assert.equal(result.status, 'BACKOFF')
    const store = new SupervisorStore({ databasePath: fx.databasePath })
    assert.equal(store.getJob('task-1').lock, undefined)
    assert.equal(store.listAttempts('task-1')[0].status, 'FAILED')
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('bounded mode performs exactly three persisted restarts then exhausts', async () => {
  const fx = fixture()
  let launches = 0
  let now = 100_000
  const waits = []
  try {
    const result = await runSupervisor({
      databasePath: fx.databasePath,
      taskId: 'task-1',
      owner: 'test-host',
      processFingerprint: 'test-supervisor',
      clock: () => now,
      leaseMs: 120_000,
      heartbeatMs: 60_000,
      async delay(ms) {
        waits.push(ms)
        now += ms
      },
      spawnImpl() {
        launches += 1
        return fakeChild({ pid: 7200 + launches, code: 17 })
      },
    })
    assert.equal(result.status, 'EXHAUSTED')
    assert.equal(launches, 4)
    assert.deepEqual(waits, [5_000, 15_000, 45_000])
    const store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
    assert.equal(store.getJob('task-1').restartsUsed, 3)
    assert.equal(store.listAttempts('task-1').length, 4)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('abort terminates the owned child and records cancellation without an orphan', async () => {
  const fx = fixture()
  const controller = new AbortController()
  let killedWith
  try {
    const result = await runSupervisor({
      databasePath: fx.databasePath,
      taskId: 'task-1',
      once: true,
      owner: 'test-host',
      processFingerprint: 'test-supervisor',
      signal: controller.signal,
      spawnImpl() {
        const child = new EventEmitter()
        child.pid = 7300
        child.stdout = new PassThrough()
        child.stderr = new PassThrough()
        child.kill = signal => {
          killedWith = signal
          queueMicrotask(() => child.emit('close', null, signal))
          return true
        }
        queueMicrotask(() => controller.abort())
        return child
      },
    })
    assert.equal(result.status, 'STOPPED')
    assert.equal(killedWith, 'SIGTERM')
    const store = new SupervisorStore({ databasePath: fx.databasePath })
    assert.equal(store.listAttempts('task-1')[0].status, 'CANCELLED')
    assert.equal(store.getJob('task-1').lock, undefined)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('a task waiting for independent verification never launches a child', async () => {
  const fx = fixture()
  let launches = 0
  try {
    const ledger = new DurableTaskStore({ databasePath: fx.databasePath })
    const lease = ledger.claimTask('task-1', { owner: 'fixture-2', leaseMs: 60_000 })
    ledger.requestCompletion('task-1', lease.token, { summary: 'feito', evidence: ['teste'] })
    ledger.close()

    await assert.rejects(
      runSupervisor({
        databasePath: fx.databasePath,
        taskId: 'task-1',
        once: true,
        spawnImpl() { launches += 1; return fakeChild({ pid: 7400 }) },
      }),
      error => error?.code === 'TASK_NOT_SUPERVISABLE',
    )
    assert.equal(launches, 0)
  }
  finally {
    fx.cleanup()
  }
})
