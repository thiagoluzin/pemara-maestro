import { createHash, randomUUID } from 'node:crypto'
import { isAbsolute, resolve } from 'node:path'
import { DatabaseSync } from 'node:sqlite'

import { SCHEMA_VERSION } from './migrations.mjs'

const ACTIVE_ATTEMPT_STATUSES = new Set(['ADMITTED', 'RUNNING'])
const TERMINAL_JOB_STATUSES = new Set(['COMPLETED', 'STOPPED', 'EXHAUSTED', 'BLOCKED'])
const ATTEMPT_RESULTS = new Set([
  'SUCCEEDED', 'FAILED', 'INTERRUPTED', 'CANCELLED', 'OUTCOME_UNKNOWN',
])

export class SupervisorStateError extends Error {
  constructor(code, message, details = undefined) {
    super(message)
    this.name = 'SupervisorStateError'
    this.code = code
    this.details = details
  }
}

function requiredText(value, field) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new SupervisorStateError('INVALID_INPUT', `${field} must be a non-empty string.`)
  }
  return value.trim()
}

function nonNegativeInteger(value, field) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new SupervisorStateError('INVALID_INPUT', `${field} must be a non-negative safe integer.`)
  }
  return value
}

function positiveInteger(value, field) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new SupervisorStateError('INVALID_INPUT', `${field} must be a positive safe integer.`)
  }
  return value
}

function encodeJson(value, field) {
  try {
    const encoded = JSON.stringify(value)
    if (encoded === undefined) throw new TypeError('undefined is not serializable')
    return encoded
  }
  catch (error) {
    throw new SupervisorStateError('INVALID_JSON', `${field} must be JSON serializable.`, {
      cause: error instanceof Error ? error.message : String(error),
    })
  }
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value).sort().map(key => [key, canonicalize(value[key])]),
    )
  }
  return value
}

function normalizeCommand({ executable, args = [], workspace }) {
  const program = requiredText(executable, 'executable')
  const cwd = requiredText(workspace, 'workspace')
  if (!isAbsolute(program)) {
    throw new SupervisorStateError('INVALID_INPUT', 'executable must be an absolute path.')
  }
  if (!isAbsolute(cwd)) {
    throw new SupervisorStateError('INVALID_INPUT', 'workspace must be an absolute path.')
  }
  if (!Array.isArray(args) || args.some(argument => typeof argument !== 'string' || argument.includes('\u0000'))) {
    throw new SupervisorStateError('INVALID_INPUT', 'args must be an array of strings without NUL bytes.')
  }
  return Object.freeze({ executable: resolve(program), args: Object.freeze([...args]), workspace: resolve(cwd) })
}

export function fingerprintCommand(command) {
  const normalized = normalizeCommand(command)
  return createHash('sha256')
    .update(JSON.stringify(canonicalize(normalized)))
    .digest('hex')
}

function jobFromRow(row) {
  if (row === undefined) return undefined
  const command = JSON.parse(row.command_json)
  return Object.freeze({
    taskId: row.task_id,
    sessionStrategy: row.session_strategy,
    sessionId: row.session_id ?? undefined,
    command: Object.freeze({
      executable: command.executable,
      args: Object.freeze([...command.args]),
    }),
    commandFingerprint: row.command_fingerprint,
    workspace: row.workspace,
    status: row.status,
    maxRestarts: row.max_restarts,
    restartsUsed: row.restarts_used,
    backoffMs: Object.freeze(JSON.parse(row.backoff_json)),
    nextAttemptAt: row.next_attempt_at ?? undefined,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    version: row.version,
    lock: row.lock_token === null ? undefined : Object.freeze({
      owner: row.lock_owner,
      token: row.lock_token,
      expiresAt: row.lock_expires_at,
      processFingerprint: row.lock_process_fingerprint,
    }),
  })
}

function attemptFromRow(row) {
  if (row === undefined) return undefined
  return Object.freeze({
    id: row.id,
    taskId: row.task_id,
    attemptNo: row.attempt_no,
    sessionId: row.session_id ?? undefined,
    commandFingerprint: row.command_fingerprint,
    runnerFingerprint: row.runner_fingerprint,
    pid: row.pid ?? undefined,
    processStartedAt: row.process_started_at ?? undefined,
    status: row.status,
    startedAt: row.started_at,
    heartbeatAt: row.heartbeat_at,
    finishedAt: row.finished_at ?? undefined,
    exitCode: row.exit_code ?? undefined,
    signal: row.signal ?? undefined,
    result: row.result_json === null ? undefined : JSON.parse(row.result_json),
  })
}

/**
 * Host-owned supervisor journal. Its lock is independent from the child
 * DurableTaskStore lease and is never considered valid from PID alone.
 */
export class SupervisorStore {
  #db
  #clock
  #closed = false

  constructor({ databasePath, clock = Date.now } = {}) {
    const path = requiredText(databasePath, 'databasePath')
    if (typeof clock !== 'function') {
      throw new SupervisorStateError('INVALID_INPUT', 'clock must be a function.')
    }
    this.databasePath = path === ':memory:' ? path : resolve(path)
    this.#clock = clock
    this.#db = new DatabaseSync(this.databasePath)
    try {
      this.#db.exec('PRAGMA foreign_keys=ON')
      this.#db.exec('PRAGMA trusted_schema=OFF')
      this.#db.exec('PRAGMA busy_timeout=5000')
      if (this.databasePath !== ':memory:') this.#db.exec('PRAGMA journal_mode=WAL')
      this.#db.exec('PRAGMA synchronous=FULL')
      const version = this.#db.prepare('PRAGMA user_version').get().user_version
      if (version !== SCHEMA_VERSION) {
        throw new SupervisorStateError(
          version === 1 ? 'SCHEMA_MIGRATION_REQUIRED' : 'SCHEMA_UNSUPPORTED',
          `Supervisor requires schema ${SCHEMA_VERSION}; database is ${version}.`,
          { actual: version, expected: SCHEMA_VERSION },
        )
      }
    }
    catch (error) {
      this.#db.close()
      this.#closed = true
      throw error
    }
  }

  #assertOpen() {
    if (this.#closed) throw new SupervisorStateError('STORE_CLOSED', 'SupervisorStore is closed.')
  }

  #transaction(work) {
    this.#assertOpen()
    this.#db.exec('BEGIN IMMEDIATE')
    try {
      const result = work()
      this.#db.exec('COMMIT')
      return result
    }
    catch (error) {
      try { this.#db.exec('ROLLBACK') } catch {}
      throw error
    }
  }

  #taskRow(taskId) {
    const row = this.#db.prepare('SELECT * FROM tasks WHERE id = ?').get(taskId)
    if (row === undefined) {
      throw new SupervisorStateError('TASK_NOT_FOUND', `Task "${taskId}" does not exist.`)
    }
    return row
  }

  #assertTaskSupervisable(taskId) {
    const task = this.#taskRow(taskId)
    if (task.status !== 'ACTIVE') {
      throw new SupervisorStateError(
        'TASK_NOT_SUPERVISABLE',
        `Task "${taskId}" is ${task.status}; only ACTIVE tasks may run.`,
        { status: task.status },
      )
    }
    const uncertain = this.#db.prepare(`
      SELECT id FROM effects WHERE task_id = ? AND status = 'OUTCOME_UNKNOWN' LIMIT 1
    `).get(taskId)
    if (uncertain !== undefined) {
      throw new SupervisorStateError(
        'EFFECT_RECONCILIATION_REQUIRED',
        `Task "${taskId}" has an uncertain external effect.`,
        { effectId: uncertain.id },
      )
    }
    return task
  }

  #jobRow(taskId) {
    const row = this.#db.prepare('SELECT * FROM supervisor_jobs WHERE task_id = ?').get(taskId)
    if (row === undefined) {
      throw new SupervisorStateError('SUPERVISOR_JOB_NOT_FOUND', `Task "${taskId}" has no supervisor job.`)
    }
    return row
  }

  #attemptRow(attemptId) {
    const row = this.#db.prepare('SELECT * FROM supervisor_attempts WHERE id = ?').get(attemptId)
    if (row === undefined) {
      throw new SupervisorStateError('SUPERVISOR_ATTEMPT_NOT_FOUND', `Attempt "${attemptId}" does not exist.`)
    }
    return row
  }

  #latestActiveAttempt(taskId) {
    return this.#db.prepare(`
      SELECT * FROM supervisor_attempts
      WHERE task_id = ? AND status IN ('ADMITTED', 'RUNNING')
      ORDER BY attempt_no DESC LIMIT 1
    `).get(taskId)
  }

  #appendTaskEvent(taskId, type, payload, at) {
    const task = this.#taskRow(taskId)
    const seq = task.next_event_seq
    this.#db.prepare(`
      INSERT INTO task_events(task_id, seq, type, at, payload_json) VALUES (?, ?, ?, ?, ?)
    `).run(taskId, seq, type, at, encodeJson(payload, 'event payload'))
    const update = this.#db.prepare(`
      UPDATE tasks SET next_event_seq = ?, updated_at = ?, version = version + 1
      WHERE id = ? AND next_event_seq = ?
    `).run(seq + 1, at, taskId, seq)
    if (update.changes !== 1) {
      throw new SupervisorStateError('EVENT_SEQUENCE_CONFLICT', `Task "${taskId}" event sequence changed.`)
    }
  }

  #assertLock(taskId, token, now) {
    const job = this.#jobRow(taskId)
    if (job.lock_token === null || job.lock_token !== requiredText(token, 'lockToken')) {
      throw new SupervisorStateError('SUPERVISOR_LOCK_INVALID', `Supervisor lock does not own task "${taskId}".`)
    }
    if (job.lock_expires_at <= now) {
      throw new SupervisorStateError('SUPERVISOR_LOCK_EXPIRED', `Supervisor lock for task "${taskId}" expired.`)
    }
    return job
  }

  configureJob({
    taskId,
    executable,
    args = [],
    workspace,
    maxRestarts = 3,
    backoffMs = [5_000, 15_000, 45_000],
    sessionId,
  } = {}) {
    const id = requiredText(taskId, 'taskId')
    const command = normalizeCommand({ executable, args, workspace })
    const restarts = nonNegativeInteger(maxRestarts, 'maxRestarts')
    if (!Array.isArray(backoffMs) || backoffMs.some((value, index) => {
      try { positiveInteger(value, `backoffMs[${index}]`); return false } catch { return true }
    })) {
      throw new SupervisorStateError('INVALID_INPUT', 'backoffMs must contain positive safe integers.')
    }
    if (backoffMs.length < restarts) {
      throw new SupervisorStateError('INVALID_INPUT', 'backoffMs must cover every allowed restart.')
    }
    const dshSession = sessionId === undefined ? null : requiredText(sessionId, 'sessionId')
    const fingerprint = fingerprintCommand(command)
    const commandJson = encodeJson({ executable: command.executable, args: command.args }, 'command')
    const backoffJson = encodeJson([...backoffMs], 'backoffMs')
    const now = this.#clock()

    return this.#transaction(() => {
      this.#assertTaskSupervisable(id)
      const existing = this.#db.prepare('SELECT * FROM supervisor_jobs WHERE task_id = ?').get(id)
      if (existing !== undefined) {
        const same = existing.command_fingerprint === fingerprint
          && existing.workspace === command.workspace
          && existing.max_restarts === restarts
          && existing.backoff_json === backoffJson
          && existing.session_id === dshSession
        if (!same) {
          throw new SupervisorStateError(
            'SUPERVISOR_CONFIG_CONFLICT',
            `Task "${id}" already has a different supervisor configuration.`,
          )
        }
        return jobFromRow(existing)
      }
      this.#db.prepare(`
        INSERT INTO supervisor_jobs(
          task_id, session_strategy, session_id, command_json, command_fingerprint,
          workspace, status, max_restarts, restarts_used, backoff_json,
          created_at, updated_at, version
        ) VALUES (?, 'checkpoint-rehydrate', ?, ?, ?, ?, 'READY', ?, 0, ?, ?, ?, 1)
      `).run(
        id, dshSession, commandJson, fingerprint, command.workspace,
        restarts, backoffJson, now, now,
      )
      this.#appendTaskEvent(id, 'supervisor.configured', {
        commandFingerprint: fingerprint,
        maxRestarts: restarts,
        sessionStrategy: 'checkpoint-rehydrate',
      }, now)
      return jobFromRow(this.#jobRow(id))
    })
  }

  getJob(taskId) {
    this.#assertOpen()
    return jobFromRow(this.#jobRow(requiredText(taskId, 'taskId')))
  }

  listAttempts(taskId) {
    this.#assertOpen()
    const id = requiredText(taskId, 'taskId')
    this.#jobRow(id)
    return this.#db.prepare(`
      SELECT * FROM supervisor_attempts WHERE task_id = ? ORDER BY attempt_no
    `).all(id).map(attemptFromRow)
  }

  acquire(taskId, { owner, leaseMs, processFingerprint } = {}) {
    const id = requiredText(taskId, 'taskId')
    const lockOwner = requiredText(owner, 'owner')
    const duration = positiveInteger(leaseMs, 'leaseMs')
    const identity = requiredText(processFingerprint, 'processFingerprint')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertTaskSupervisable(id)
      let job = this.#jobRow(id)
      if (TERMINAL_JOB_STATUSES.has(job.status)) {
        throw new SupervisorStateError('SUPERVISOR_JOB_TERMINAL', `Supervisor job for task "${id}" is ${job.status}.`)
      }
      if (job.lock_token !== null && job.lock_expires_at > now) {
        if (job.lock_owner === lockOwner && job.lock_process_fingerprint === identity) {
          this.#db.prepare(`
            UPDATE supervisor_jobs SET lock_expires_at = ?, updated_at = ?, version = version + 1
            WHERE task_id = ?
          `).run(now + duration, now, id)
          job = this.#jobRow(id)
          return Object.freeze({
            taskId: id,
            owner: job.lock_owner,
            token: job.lock_token,
            expiresAt: job.lock_expires_at,
            processFingerprint: job.lock_process_fingerprint,
          })
        }
        throw new SupervisorStateError('SUPERVISOR_LOCK_HELD', `Task "${id}" already has a live supervisor.`, {
          owner: job.lock_owner,
          expiresAt: job.lock_expires_at,
        })
      }
      if (this.#latestActiveAttempt(id) !== undefined) {
        throw new SupervisorStateError(
          'SUPERVISOR_RECOVERY_REQUIRED',
          `Task "${id}" has an unfinished attempt that must be reconciled first.`,
        )
      }
      const token = randomUUID()
      this.#db.prepare(`
        UPDATE supervisor_jobs SET lock_owner = ?, lock_token = ?, lock_expires_at = ?,
          lock_process_fingerprint = ?, updated_at = ?, version = version + 1
        WHERE task_id = ?
      `).run(lockOwner, token, now + duration, identity, now, id)
      return Object.freeze({
        taskId: id, owner: lockOwner, token, expiresAt: now + duration, processFingerprint: identity,
      })
    })
  }

  heartbeat(taskId, lockToken, leaseMs) {
    const id = requiredText(taskId, 'taskId')
    const duration = positiveInteger(leaseMs, 'leaseMs')
    const now = this.#clock()
    return this.#transaction(() => {
      const job = this.#assertLock(id, lockToken, now)
      const expiresAt = now + duration
      this.#db.prepare(`
        UPDATE supervisor_jobs SET lock_expires_at = ?, updated_at = ?, version = version + 1
        WHERE task_id = ?
      `).run(expiresAt, now, id)
      this.#db.prepare(`
        UPDATE supervisor_attempts SET heartbeat_at = ?
        WHERE task_id = ? AND status IN ('ADMITTED', 'RUNNING')
      `).run(now, id)
      return Object.freeze({
        taskId: id,
        owner: job.lock_owner,
        token: job.lock_token,
        expiresAt,
        processFingerprint: job.lock_process_fingerprint,
      })
    })
  }

  release(taskId, lockToken) {
    const id = requiredText(taskId, 'taskId')
    const token = requiredText(lockToken, 'lockToken')
    const now = this.#clock()
    return this.#transaction(() => {
      const job = this.#jobRow(id)
      if (job.lock_token === null) return jobFromRow(job)
      if (job.lock_token !== token) {
        throw new SupervisorStateError('SUPERVISOR_LOCK_INVALID', `Supervisor lock does not own task "${id}".`)
      }
      if (this.#latestActiveAttempt(id) !== undefined) {
        throw new SupervisorStateError('SUPERVISOR_ATTEMPT_ACTIVE', `Task "${id}" still has an active attempt.`)
      }
      this.#db.prepare(`
        UPDATE supervisor_jobs SET lock_owner = NULL, lock_token = NULL,
          lock_expires_at = NULL, lock_process_fingerprint = NULL,
          updated_at = ?, version = version + 1 WHERE task_id = ?
      `).run(now, id)
      return jobFromRow(this.#jobRow(id))
    })
  }

  admitAttempt(taskId, lockToken, { runnerFingerprint, sessionId } = {}) {
    const id = requiredText(taskId, 'taskId')
    const runner = requiredText(runnerFingerprint, 'runnerFingerprint')
    const dshSession = sessionId === undefined ? null : requiredText(sessionId, 'sessionId')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertTaskSupervisable(id)
      const job = this.#assertLock(id, lockToken, now)
      if (job.status === 'BACKOFF' && job.next_attempt_at > now) {
        throw new SupervisorStateError('SUPERVISOR_BACKOFF', `Task "${id}" is waiting for its restart backoff.`, {
          nextAttemptAt: job.next_attempt_at,
        })
      }
      if (job.status !== 'READY' && job.status !== 'BACKOFF') {
        throw new SupervisorStateError('SUPERVISOR_JOB_NOT_READY', `Supervisor job for task "${id}" is ${job.status}.`)
      }
      if (this.#latestActiveAttempt(id) !== undefined) {
        throw new SupervisorStateError('SUPERVISOR_ATTEMPT_ACTIVE', `Task "${id}" already has an active attempt.`)
      }
      const attemptNo = this.#db.prepare(`
        SELECT COALESCE(MAX(attempt_no), 0) + 1 AS value
        FROM supervisor_attempts WHERE task_id = ?
      `).get(id).value
      const attemptId = randomUUID()
      this.#db.prepare(`
        INSERT INTO supervisor_attempts(
          id, task_id, attempt_no, session_id, command_fingerprint,
          runner_fingerprint, status, started_at, heartbeat_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'ADMITTED', ?, ?)
      `).run(
        attemptId, id, attemptNo, dshSession ?? job.session_id,
        job.command_fingerprint, runner, now, now,
      )
      this.#db.prepare(`
        UPDATE supervisor_jobs SET status = 'RUNNING', next_attempt_at = NULL,
          session_id = COALESCE(?, session_id), updated_at = ?, version = version + 1
        WHERE task_id = ?
      `).run(dshSession, now, id)
      this.#appendTaskEvent(id, 'supervisor.attempt_admitted', {
        attemptId, attemptNo, sessionId: dshSession ?? job.session_id,
      }, now)
      return attemptFromRow(this.#attemptRow(attemptId))
    })
  }

  markAttemptRunning(taskId, lockToken, attemptId, { pid, processStartedAt, runnerFingerprint } = {}) {
    const id = requiredText(taskId, 'taskId')
    const target = requiredText(attemptId, 'attemptId')
    const processId = positiveInteger(pid, 'pid')
    const processStart = nonNegativeInteger(processStartedAt, 'processStartedAt')
    const runner = runnerFingerprint === undefined
      ? undefined
      : requiredText(runnerFingerprint, 'runnerFingerprint')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertLock(id, lockToken, now)
      const attempt = this.#attemptRow(target)
      if (attempt.task_id !== id) {
        throw new SupervisorStateError('SUPERVISOR_ATTEMPT_MISMATCH', `Attempt "${target}" belongs to another task.`)
      }
      if (attempt.status === 'RUNNING') return attemptFromRow(attempt)
      if (attempt.status !== 'ADMITTED') {
        throw new SupervisorStateError('SUPERVISOR_ATTEMPT_STATE', `Attempt "${target}" is ${attempt.status}.`)
      }
      this.#db.prepare(`
        UPDATE supervisor_attempts SET status = 'RUNNING', pid = ?, process_started_at = ?,
          runner_fingerprint = COALESCE(?, runner_fingerprint), heartbeat_at = ? WHERE id = ?
      `).run(processId, processStart, runner ?? null, now, target)
      this.#appendTaskEvent(id, 'supervisor.attempt_running', {
        attemptId: target, pid: processId, processStartedAt: processStart,
      }, now)
      return attemptFromRow(this.#attemptRow(target))
    })
  }

  #finishJobAfterAttempt(job, status, now) {
    if (status === 'SUCCEEDED') {
      return { status: 'COMPLETED', restartsUsed: job.restarts_used, nextAttemptAt: null, clearLock: true }
    }
    if (status === 'CANCELLED') {
      return { status: 'STOPPED', restartsUsed: job.restarts_used, nextAttemptAt: null, clearLock: true }
    }
    if (status === 'OUTCOME_UNKNOWN') {
      return { status: 'BLOCKED', restartsUsed: job.restarts_used, nextAttemptAt: null, clearLock: true }
    }
    if (job.restarts_used >= job.max_restarts) {
      return { status: 'EXHAUSTED', restartsUsed: job.restarts_used, nextAttemptAt: null, clearLock: true }
    }
    const backoff = JSON.parse(job.backoff_json)
    const delay = backoff[job.restarts_used]
    return {
      status: 'BACKOFF',
      restartsUsed: job.restarts_used + 1,
      nextAttemptAt: now + delay,
      clearLock: false,
    }
  }

  finishAttempt(taskId, lockToken, attemptId, {
    status,
    exitCode,
    signal,
    result,
  } = {}) {
    const id = requiredText(taskId, 'taskId')
    const target = requiredText(attemptId, 'attemptId')
    if (!ATTEMPT_RESULTS.has(status)) {
      throw new SupervisorStateError('INVALID_INPUT', `status must be one of ${[...ATTEMPT_RESULTS].join(', ')}.`)
    }
    if (exitCode !== undefined && (!Number.isSafeInteger(exitCode) || exitCode < 0)) {
      throw new SupervisorStateError('INVALID_INPUT', 'exitCode must be a non-negative safe integer.')
    }
    const processSignal = signal === undefined || signal === null ? null : requiredText(signal, 'signal')
    const resultJson = result === undefined ? null : encodeJson(result, 'result')
    const now = this.#clock()
    return this.#transaction(() => {
      const job = this.#assertLock(id, lockToken, now)
      const attempt = this.#attemptRow(target)
      if (attempt.task_id !== id) {
        throw new SupervisorStateError('SUPERVISOR_ATTEMPT_MISMATCH', `Attempt "${target}" belongs to another task.`)
      }
      if (!ACTIVE_ATTEMPT_STATUSES.has(attempt.status)) {
        throw new SupervisorStateError('SUPERVISOR_ATTEMPT_STATE', `Attempt "${target}" is ${attempt.status}.`)
      }
      const next = this.#finishJobAfterAttempt(job, status, now)
      this.#db.prepare(`
        UPDATE supervisor_attempts SET status = ?, heartbeat_at = ?, finished_at = ?,
          exit_code = ?, signal = ?, result_json = ? WHERE id = ?
      `).run(status, now, now, exitCode ?? null, processSignal, resultJson, target)
      this.#db.prepare(`
        UPDATE supervisor_jobs SET status = ?, restarts_used = ?, next_attempt_at = ?,
          lock_owner = CASE WHEN ? THEN NULL ELSE lock_owner END,
          lock_token = CASE WHEN ? THEN NULL ELSE lock_token END,
          lock_expires_at = CASE WHEN ? THEN NULL ELSE lock_expires_at END,
          lock_process_fingerprint = CASE WHEN ? THEN NULL ELSE lock_process_fingerprint END,
          updated_at = ?, version = version + 1 WHERE task_id = ?
      `).run(
        next.status, next.restartsUsed, next.nextAttemptAt,
        next.clearLock ? 1 : 0, next.clearLock ? 1 : 0,
        next.clearLock ? 1 : 0, next.clearLock ? 1 : 0,
        now, id,
      )
      this.#appendTaskEvent(id, 'supervisor.attempt_finished', {
        attemptId: target,
        status,
        exitCode: exitCode ?? null,
        signal: processSignal,
        nextJobStatus: next.status,
        nextAttemptAt: next.nextAttemptAt,
      }, now)
      return Object.freeze({
        attempt: attemptFromRow(this.#attemptRow(target)),
        job: jobFromRow(this.#jobRow(id)),
      })
    })
  }

  recoverStale(taskId, { inspectProcess } = {}) {
    const id = requiredText(taskId, 'taskId')
    if (typeof inspectProcess !== 'function') {
      throw new SupervisorStateError('INVALID_INPUT', 'inspectProcess must be a function.')
    }
    const now = this.#clock()
    this.#assertOpen()
    const snapshot = this.#jobRow(id)
    if (snapshot.lock_token === null || snapshot.lock_expires_at > now) {
      return Object.freeze({ recovered: false, reason: 'lock-not-stale' })
    }
    const active = this.#latestActiveAttempt(id)
    if (active === undefined) {
      return this.#transaction(() => {
        const job = this.#jobRow(id)
        if (job.lock_token !== null && job.lock_expires_at <= now) {
          this.#db.prepare(`
            UPDATE supervisor_jobs SET lock_owner = NULL, lock_token = NULL,
              lock_expires_at = NULL, lock_process_fingerprint = NULL,
              updated_at = ?, version = version + 1 WHERE task_id = ?
          `).run(now, id)
        }
        return Object.freeze({ recovered: true, reason: 'stale-lock-cleared' })
      })
    }

    const observed = active.pid === null
      ? { alive: false }
      : inspectProcess(active.pid)
    const exactIdentity = observed?.alive === true
      && observed.processStartedAt === active.process_started_at
      && observed.runnerFingerprint === active.runner_fingerprint
    if (exactIdentity) {
      return Object.freeze({
        recovered: false,
        reason: 'child-still-running',
        attemptId: active.id,
        pid: active.pid,
      })
    }
    const reason = observed?.alive === true ? 'pid-reused' : 'child-not-running'
    return this.#transaction(() => {
      const job = this.#jobRow(id)
      const attempt = this.#attemptRow(active.id)
      if (job.lock_token === null || job.lock_expires_at > now || !ACTIVE_ATTEMPT_STATUSES.has(attempt.status)) {
        throw new SupervisorStateError('SUPERVISOR_RECOVERY_RACE', `Task "${id}" changed during recovery.`)
      }
      const recoveredStatus = reason === 'pid-reused' ? 'OUTCOME_UNKNOWN' : 'INTERRUPTED'
      const next = this.#finishJobAfterAttempt(job, recoveredStatus, now)
      this.#db.prepare(`
        UPDATE supervisor_attempts SET status = ?, heartbeat_at = ?, finished_at = ?,
          result_json = ? WHERE id = ?
      `).run(recoveredStatus, now, now, encodeJson({ reason, observed }, 'recovery result'), active.id)
      this.#db.prepare(`
        UPDATE supervisor_jobs SET status = ?, restarts_used = ?, next_attempt_at = ?,
          lock_owner = NULL, lock_token = NULL, lock_expires_at = NULL,
          lock_process_fingerprint = NULL, updated_at = ?, version = version + 1
        WHERE task_id = ?
      `).run(next.status, next.restartsUsed, next.nextAttemptAt, now, id)
      this.#appendTaskEvent(id, 'supervisor.attempt_recovered', {
        attemptId: active.id, pid: active.pid, reason, nextJobStatus: next.status,
      }, now)
      return Object.freeze({ recovered: true, reason, attemptId: active.id, pid: active.pid ?? undefined })
    })
  }

  close() {
    if (this.#closed) return
    this.#closed = true
    this.#db.close()
  }
}
