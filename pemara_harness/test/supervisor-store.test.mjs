import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import { DatabaseSync } from 'node:sqlite'

import { DurableTaskStore } from '../src/index.mjs'
import { SupervisorStore, fingerprintCommand } from '../src/supervisor-store.mjs'

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-supervisor-store-'))
  const databasePath = join(root, 'ledger.sqlite')
  const ledger = new DurableTaskStore({ databasePath })
  ledger.createTask({ id: 'task-1', objective: 'Retomar depois da queda', maxRounds: 6 })
  ledger.close()
  return {
    root,
    databasePath,
    cleanup() { rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 }) },
  }
}

function configure(store, fx, overrides = {}) {
  return store.configureJob({
    taskId: 'task-1',
    executable: process.execPath,
    args: ['fixture-child.mjs'],
    workspace: fx.root,
    maxRestarts: 3,
    backoffMs: [5_000, 15_000, 45_000],
    sessionId: 'dsh-attempt-1',
    ...overrides,
  })
}

test('configures one stable supervisor job and persists its command fingerprint', () => {
  const fx = fixture()
  try {
    const store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => 1_000 })
    const job = configure(store, fx)
    assert.equal(job.status, 'READY')
    assert.equal(job.taskId, 'task-1')
    assert.equal(job.sessionStrategy, 'checkpoint-rehydrate')
    assert.equal(job.commandFingerprint, fingerprintCommand({
      executable: process.execPath,
      args: ['fixture-child.mjs'],
      workspace: fx.root,
    }))
    assert.deepEqual(job.backoffMs, [5_000, 15_000, 45_000])
    assert.deepEqual(configure(store, fx), job)
    assert.throws(
      () => configure(store, fx, { args: ['different.mjs'] }),
      error => error?.code === 'SUPERVISOR_CONFIG_CONFLICT',
    )
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('two store handles admit only one live supervisor for a task', () => {
  const fx = fixture()
  try {
    const first = new SupervisorStore({ databasePath: fx.databasePath, clock: () => 2_000 })
    const second = new SupervisorStore({ databasePath: fx.databasePath, clock: () => 2_000 })
    configure(first, fx)
    const lock = first.acquire('task-1', {
      owner: 'host-a',
      leaseMs: 30_000,
      processFingerprint: 'host-a:pid:100',
    })
    assert.equal(lock.owner, 'host-a')
    assert.throws(
      () => second.acquire('task-1', {
        owner: 'host-b',
        leaseMs: 30_000,
        processFingerprint: 'host-b:pid:200',
      }),
      error => error?.code === 'SUPERVISOR_LOCK_HELD',
    )
    first.close()
    second.close()
  }
  finally {
    fx.cleanup()
  }
})

test('attempt results persist exact restart budget and backoff across reopen', () => {
  const fx = fixture()
  let now = 10_000
  try {
    let store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
    configure(store, fx)
    let lock = store.acquire('task-1', {
      owner: 'host-a', leaseMs: 60_000, processFingerprint: 'supervisor-a',
    })

    for (let attemptNumber = 1; attemptNumber <= 4; attemptNumber += 1) {
      const attempt = store.admitAttempt('task-1', lock.token, {
        runnerFingerprint: `child-${attemptNumber}`,
        sessionId: `dsh-attempt-${attemptNumber}`,
      })
      store.markAttemptRunning('task-1', lock.token, attempt.id, {
        pid: 5_000 + attemptNumber,
        processStartedAt: now,
      })
      const result = store.finishAttempt('task-1', lock.token, attempt.id, {
        status: 'FAILED', exitCode: 23, result: { attemptNumber },
      })
      if (attemptNumber <= 3) {
        assert.equal(result.job.status, 'BACKOFF')
        assert.equal(result.job.restartsUsed, attemptNumber)
        assert.equal(result.job.nextAttemptAt, now + [5_000, 15_000, 45_000][attemptNumber - 1])
        assert.throws(
          () => store.admitAttempt('task-1', lock.token, { runnerFingerprint: 'too-early' }),
          error => error?.code === 'SUPERVISOR_BACKOFF',
        )
        now = result.job.nextAttemptAt
        store.close()
        store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
        lock = store.acquire('task-1', {
          owner: 'host-a', leaseMs: 60_000, processFingerprint: 'supervisor-a',
        })
      }
      else {
        assert.equal(result.job.status, 'EXHAUSTED')
        assert.equal(result.job.restartsUsed, 3)
      }
    }

    assert.deepEqual(store.listAttempts('task-1').map(attempt => attempt.status), [
      'FAILED', 'FAILED', 'FAILED', 'FAILED',
    ])
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('stale recovery distinguishes a dead child from PID reuse', () => {
  const fx = fixture()
  let now = 20_000
  try {
    let store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
    configure(store, fx)
    const lock = store.acquire('task-1', {
      owner: 'host-a', leaseMs: 1_000, processFingerprint: 'supervisor-a',
    })
    const attempt = store.admitAttempt('task-1', lock.token, {
      runnerFingerprint: 'child-command-fingerprint', sessionId: 'dsh-a',
    })
    store.markAttemptRunning('task-1', lock.token, attempt.id, {
      pid: 4242, processStartedAt: 19_900,
    })
    store.close()

    now = 22_000
    store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
    const recovery = store.recoverStale('task-1', {
      inspectProcess: () => ({
        alive: true,
        processStartedAt: 21_500,
        runnerFingerprint: 'some-other-process',
      }),
    })
    assert.equal(recovery.recovered, true)
    assert.equal(recovery.reason, 'pid-reused')
    assert.equal(store.listAttempts('task-1')[0].status, 'OUTCOME_UNKNOWN')
    assert.equal(store.getJob('task-1').status, 'BLOCKED')
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('an exact live child blocks recovery and cannot be replaced by PID alone', () => {
  const fx = fixture()
  let now = 30_000
  try {
    let store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
    configure(store, fx)
    const lock = store.acquire('task-1', {
      owner: 'host-a', leaseMs: 1_000, processFingerprint: 'supervisor-a',
    })
    const attempt = store.admitAttempt('task-1', lock.token, {
      runnerFingerprint: 'child-exact', sessionId: 'dsh-a',
    })
    store.markAttemptRunning('task-1', lock.token, attempt.id, {
      pid: 4242, processStartedAt: 29_900,
    })
    store.close()

    now = 32_000
    store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => now })
    const recovery = store.recoverStale('task-1', {
      inspectProcess: () => ({
        alive: true,
        processStartedAt: 29_900,
        runnerFingerprint: 'child-exact',
      }),
    })
    assert.deepEqual(recovery, {
      recovered: false,
      reason: 'child-still-running',
      attemptId: attempt.id,
      pid: 4242,
    })
    assert.throws(
      () => store.acquire('task-1', {
        owner: 'host-b', leaseMs: 1_000, processFingerprint: 'supervisor-b',
      }),
      error => error?.code === 'SUPERVISOR_RECOVERY_REQUIRED',
    )
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('non-active tasks and v1 databases fail closed', () => {
  const fx = fixture()
  try {
    const ledger = new DurableTaskStore({ databasePath: fx.databasePath })
    const lease = ledger.claimTask('task-1', { owner: 'worker', leaseMs: 10_000 })
    ledger.startRound('task-1', lease.token)
    ledger.checkpoint('task-1', lease.token, { summary: 'feito', nextAction: 'verificar' })
    ledger.requestCompletion('task-1', lease.token, { summary: 'feito', evidence: ['teste'] })
    ledger.close()

    const store = new SupervisorStore({ databasePath: fx.databasePath, clock: () => 40_000 })
    assert.throws(() => configure(store, fx), error => error?.code === 'TASK_NOT_SUPERVISABLE')
    store.close()

    const db = new DatabaseSync(fx.databasePath)
    db.exec('PRAGMA user_version=1')
    db.close()
    assert.throws(
      () => new SupervisorStore({ databasePath: fx.databasePath }),
      error => error?.code === 'SCHEMA_MIGRATION_REQUIRED',
    )
  }
  finally {
    fx.cleanup()
  }
})
