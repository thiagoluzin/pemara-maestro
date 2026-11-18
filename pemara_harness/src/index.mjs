import { randomUUID } from 'node:crypto'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { DatabaseSync } from 'node:sqlite'

import {
  installSupervisorSchema,
  migrateHarnessSchema,
  MIN_SUPPORTED_SCHEMA_VERSION,
  SCHEMA_VERSION as CURRENT_SCHEMA_VERSION,
} from './migrations.mjs'

export const SCHEMA_VERSION = CURRENT_SCHEMA_VERSION
const DEFAULT_MAX_ROUNDS = 256

export const TASK_STATUS = Object.freeze({
  ACTIVE: 'ACTIVE',
  PAUSED: 'PAUSED',
  BLOCKED_HUMAN: 'BLOCKED_HUMAN',
  COMPLETED_PENDING_VERIFY: 'COMPLETED_PENDING_VERIFY',
  COMPLETED_VERIFIED: 'COMPLETED_VERIFIED',
  CANCELLED: 'CANCELLED',
  FAILED_EXHAUSTED: 'FAILED_EXHAUSTED',
})

const TERMINAL_STATUSES = new Set([
  TASK_STATUS.COMPLETED_VERIFIED,
  TASK_STATUS.CANCELLED,
  TASK_STATUS.FAILED_EXHAUSTED,
])

export class HarnessStateError extends Error {
  constructor(code, message, details = undefined) {
    super(message)
    this.name = 'HarnessStateError'
    this.code = code
    this.details = details
  }
}

function requiredText(value, field) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new HarnessStateError('INVALID_INPUT', `${field} must be a non-empty string.`)
  }
  return value.trim()
}

function positiveInteger(value, field) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new HarnessStateError('INVALID_INPUT', `${field} must be a positive safe integer.`)
  }
  return value
}

function encodeJson(value, field) {
  try {
    const encoded = JSON.stringify(value)
    if (encoded === undefined) throw new TypeError('undefined is not JSON serializable')
    return encoded
  }
  catch (error) {
    throw new HarnessStateError('INVALID_JSON', `${field} must be JSON serializable.`, {
      cause: error instanceof Error ? error.message : String(error),
    })
  }
}

function decodeJson(value) {
  return value === null || value === undefined ? undefined : JSON.parse(value)
}

function normalizeStringArray(value, field, { required = false } = {}) {
  if (value === undefined && !required) return []
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || item.trim() === '')) {
    throw new HarnessStateError('INVALID_INPUT', `${field} must be an array of non-empty strings.`)
  }
  const normalized = value.map(item => item.trim())
  if (required && normalized.length === 0) {
    throw new HarnessStateError('EVIDENCE_REQUIRED', `${field} must contain at least one item.`)
  }
  return normalized
}

function taskFromRow(row) {
  if (row === undefined) return undefined
  return Object.freeze({
    id: row.id,
    objective: row.objective,
    status: row.status,
    sessionId: row.session_id ?? undefined,
    maxRounds: row.max_rounds,
    roundsStarted: row.rounds_started,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    version: row.version,
    lease: row.lease_token === null ? undefined : Object.freeze({
      owner: row.lease_owner,
      token: row.lease_token,
      expiresAt: row.lease_expires_at,
    }),
    checkpoint: decodeJson(row.checkpoint_json),
    detail: decodeJson(row.status_detail_json),
  })
}

function effectFromRow(row) {
  if (row === undefined) return undefined
  return Object.freeze({
    id: row.id,
    taskId: row.task_id,
    key: row.idempotency_key,
    kind: row.kind,
    request: decodeJson(row.request_json),
    status: row.status,
    result: decodeJson(row.result_json),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  })
}

/**
 * Durable orchestration ledger. Every state mutation and event append happens
 * under BEGIN IMMEDIATE and reaches SQLite with synchronous=FULL before return.
 */
export class DurableTaskStore {
  #db
  #clock
  #closed = false

  constructor({ databasePath, clock = Date.now, migrateSchema = false }) {
    const path = requiredText(databasePath, 'databasePath')
    if (typeof clock !== 'function') {
      throw new HarnessStateError('INVALID_INPUT', 'clock must be a function.')
    }
    if (typeof migrateSchema !== 'boolean') {
      throw new HarnessStateError('INVALID_INPUT', 'migrateSchema must be a boolean.')
    }
    this.databasePath = path === ':memory:' ? path : resolve(path)
    this.#clock = clock
    if (this.databasePath !== ':memory:') mkdirSync(dirname(this.databasePath), { recursive: true })
    this.#db = new DatabaseSync(this.databasePath)
    this.#configure()
    this.#initializeSchema(migrateSchema)
  }

  #configure() {
    this.#db.exec('PRAGMA foreign_keys=ON')
    this.#db.exec('PRAGMA trusted_schema=OFF')
    this.#db.exec('PRAGMA busy_timeout=5000')
    if (this.databasePath !== ':memory:') this.#db.exec('PRAGMA journal_mode=WAL')
    this.#db.exec('PRAGMA synchronous=FULL')
  }

  #initializeSchema(migrateSchema) {
    const version = this.#db.prepare('PRAGMA user_version').get().user_version
    if (version !== 0 && version !== MIN_SUPPORTED_SCHEMA_VERSION && version !== SCHEMA_VERSION) {
      throw new HarnessStateError(
        'SCHEMA_UNSUPPORTED',
        `Harness database schema ${version} is not supported by this build (expected ${MIN_SUPPORTED_SCHEMA_VERSION} or ${SCHEMA_VERSION}).`,
      )
    }

    if (version === MIN_SUPPORTED_SCHEMA_VERSION) {
      if (migrateSchema) migrateHarnessSchema(this.#db)
      return
    }
    if (version === SCHEMA_VERSION) return

    this.#db.exec('BEGIN IMMEDIATE')
    try {
      this.#db.exec(`
      CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        objective TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN (
          'ACTIVE', 'PAUSED', 'BLOCKED_HUMAN', 'COMPLETED_PENDING_VERIFY',
          'COMPLETED_VERIFIED', 'CANCELLED', 'FAILED_EXHAUSTED'
        )),
        session_id TEXT,
        max_rounds INTEGER NOT NULL CHECK (max_rounds > 0),
        rounds_started INTEGER NOT NULL DEFAULT 0 CHECK (rounds_started >= 0),
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        version INTEGER NOT NULL CHECK (version > 0),
        lease_owner TEXT,
        lease_token TEXT,
        lease_expires_at INTEGER,
        checkpoint_json TEXT,
        checkpoint_event_seq INTEGER,
        last_effect_event_seq INTEGER NOT NULL DEFAULT 0,
        status_detail_json TEXT,
        next_event_seq INTEGER NOT NULL DEFAULT 1,
        CHECK ((lease_token IS NULL AND lease_owner IS NULL AND lease_expires_at IS NULL)
          OR (lease_token IS NOT NULL AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL))
      ) STRICT;

      CREATE TABLE IF NOT EXISTS task_events (
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
        seq INTEGER NOT NULL CHECK (seq > 0),
        type TEXT NOT NULL,
        at INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY (task_id, seq)
      ) STRICT;

      CREATE TABLE IF NOT EXISTS effects (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
        idempotency_key TEXT NOT NULL,
        kind TEXT NOT NULL,
        request_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN (
          'PREPARED', 'STARTED', 'COMMITTED', 'FAILED', 'OUTCOME_UNKNOWN'
        )),
        result_json TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        UNIQUE (task_id, idempotency_key)
      ) STRICT;

      CREATE INDEX IF NOT EXISTS idx_tasks_claimable
        ON tasks(status, lease_expires_at, updated_at);
      CREATE INDEX IF NOT EXISTS idx_effects_task
        ON effects(task_id, created_at, id);
      `)
      installSupervisorSchema(this.#db)
      this.#db.exec(`PRAGMA user_version=${SCHEMA_VERSION}`)
      this.#db.exec('COMMIT')
    }
    catch (error) {
      try { this.#db.exec('ROLLBACK') } catch {}
      throw error
    }
  }

  #assertOpen() {
    if (this.#closed) throw new HarnessStateError('STORE_CLOSED', 'DurableTaskStore is closed.')
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
      try {
        this.#db.exec('ROLLBACK')
      }
      catch {
        // Preserve the original failure. A failed rollback poisons this handle;
        // the caller will see the next SQLite failure and reopen the process.
      }
      throw error
    }
  }

  #taskRow(id) {
    const row = this.#db.prepare('SELECT * FROM tasks WHERE id = ?').get(id)
    if (row === undefined) throw new HarnessStateError('TASK_NOT_FOUND', `Task "${id}" does not exist.`)
    return row
  }

  #effectRow(id) {
    const row = this.#db.prepare('SELECT * FROM effects WHERE id = ?').get(id)
    if (row === undefined) throw new HarnessStateError('EFFECT_NOT_FOUND', `Effect "${id}" does not exist.`)
    return row
  }

  #appendEvent(taskId, type, payload, at = this.#clock()) {
    const row = this.#taskRow(taskId)
    const seq = row.next_event_seq
    this.#db.prepare(`
      INSERT INTO task_events(task_id, seq, type, at, payload_json)
      VALUES (?, ?, ?, ?, ?)
    `).run(taskId, seq, requiredText(type, 'event type'), at, encodeJson(payload, 'event payload'))
    const updated = this.#db.prepare(`
      UPDATE tasks SET next_event_seq = ? WHERE id = ? AND next_event_seq = ?
    `).run(seq + 1, taskId, seq)
    if (updated.changes !== 1) {
      throw new HarnessStateError('EVENT_SEQUENCE_CONFLICT', `Could not reserve event ${seq} for task "${taskId}".`)
    }
    return seq
  }

  #assertActiveLease(taskId, leaseToken) {
    const token = requiredText(leaseToken, 'leaseToken')
    const task = this.#taskRow(taskId)
    if (task.status !== TASK_STATUS.ACTIVE) {
      throw new HarnessStateError('TASK_NOT_ACTIVE', `Task "${taskId}" is ${task.status}, not ACTIVE.`)
    }
    if (task.lease_token !== token) {
      throw new HarnessStateError('LEASE_INVALID', `Lease does not own task "${taskId}".`)
    }
    if (task.lease_expires_at <= this.#clock()) {
      throw new HarnessStateError('LEASE_EXPIRED', `Lease for task "${taskId}" has expired.`)
    }
    return task
  }

  createTask({ id = randomUUID(), objective, maxRounds = DEFAULT_MAX_ROUNDS, sessionId } = {}) {
    const taskId = requiredText(id, 'id')
    const text = requiredText(objective, 'objective')
    const rounds = positiveInteger(maxRounds, 'maxRounds')
    const session = sessionId === undefined ? null : requiredText(sessionId, 'sessionId')
    const now = this.#clock()

    try {
      return this.#transaction(() => {
        this.#db.prepare(`
          INSERT INTO tasks(
            id, objective, status, session_id, max_rounds, rounds_started,
            created_at, updated_at, version
          ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, 1)
        `).run(taskId, text, TASK_STATUS.ACTIVE, session, rounds, now, now)
        this.#appendEvent(taskId, 'task.created', {
          objective: text,
          maxRounds: rounds,
          sessionId: session ?? undefined,
        }, now)
        return taskFromRow(this.#taskRow(taskId))
      })
    }
    catch (error) {
      if (String(error?.message).includes('UNIQUE constraint failed: tasks.id')) {
        throw new HarnessStateError('TASK_EXISTS', `Task "${taskId}" already exists.`)
      }
      throw error
    }
  }

  getTask(id) {
    this.#assertOpen()
    return taskFromRow(this.#taskRow(requiredText(id, 'id')))
  }

  listTasks({ status } = {}) {
    this.#assertOpen()
    const rows = status === undefined
      ? this.#db.prepare('SELECT * FROM tasks ORDER BY created_at, id').all()
      : this.#db.prepare('SELECT * FROM tasks WHERE status = ? ORDER BY created_at, id').all(status)
    return rows.map(taskFromRow)
  }

  listEvents(taskId, { fromSeq = 1 } = {}) {
    this.#assertOpen()
    const id = requiredText(taskId, 'taskId')
    positiveInteger(fromSeq, 'fromSeq')
    this.#taskRow(id)
    return this.#db.prepare(`
      SELECT task_id, seq, type, at, payload_json
      FROM task_events WHERE task_id = ? AND seq >= ? ORDER BY seq
    `).all(id, fromSeq).map(row => Object.freeze({
      taskId: row.task_id,
      seq: row.seq,
      type: row.type,
      at: row.at,
      payload: decodeJson(row.payload_json),
    }))
  }

  claimTask(taskId, { owner, leaseMs }) {
    const id = requiredText(taskId, 'taskId')
    const worker = requiredText(owner, 'owner')
    const duration = positiveInteger(leaseMs, 'leaseMs')
    const now = this.#clock()
    const token = randomUUID()

    return this.#transaction(() => {
      let task = this.#taskRow(id)
      if (task.status !== TASK_STATUS.ACTIVE) {
        throw new HarnessStateError('TASK_NOT_CLAIMABLE', `Task "${id}" is ${task.status}.`)
      }
      if (task.lease_token !== null && task.lease_expires_at > now) {
        throw new HarnessStateError('LEASE_HELD', `Task "${id}" is leased by "${task.lease_owner}".`, {
          owner: task.lease_owner,
          expiresAt: task.lease_expires_at,
        })
      }
      if (task.lease_token !== null) {
        this.#db.prepare(`
          UPDATE tasks SET lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
            updated_at = ?, version = version + 1 WHERE id = ?
        `).run(now, id)
        this.#appendEvent(id, 'lease.expired', { owner: task.lease_owner }, now)
        task = this.#taskRow(id)
      }
      this.#db.prepare(`
        UPDATE tasks SET lease_owner = ?, lease_token = ?, lease_expires_at = ?,
          updated_at = ?, version = version + 1 WHERE id = ?
      `).run(worker, token, now + duration, now, id)
      this.#appendEvent(id, 'lease.claimed', { owner: worker, expiresAt: now + duration }, now)
      return Object.freeze({ taskId: id, owner: worker, token, expiresAt: now + duration })
    })
  }

  heartbeat(taskId, leaseToken, leaseMs) {
    const id = requiredText(taskId, 'taskId')
    const duration = positiveInteger(leaseMs, 'leaseMs')
    const now = this.#clock()
    return this.#transaction(() => {
      const task = this.#assertActiveLease(id, leaseToken)
      const expiresAt = now + duration
      this.#db.prepare(`
        UPDATE tasks SET lease_expires_at = ?, updated_at = ?, version = version + 1 WHERE id = ?
      `).run(expiresAt, now, id)
      this.#appendEvent(id, 'lease.renewed', { owner: task.lease_owner, expiresAt }, now)
      return Object.freeze({ taskId: id, owner: task.lease_owner, token: leaseToken, expiresAt })
    })
  }

  releaseLease(taskId, leaseToken) {
    const id = requiredText(taskId, 'taskId')
    const token = requiredText(leaseToken, 'leaseToken')
    const now = this.#clock()
    return this.#transaction(() => {
      const task = this.#taskRow(id)
      if (task.lease_token === null) return taskFromRow(task)
      if (task.lease_token !== token) {
        throw new HarnessStateError('LEASE_INVALID', `Lease does not own task "${id}".`)
      }
      this.#db.prepare(`
        UPDATE tasks SET lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
          updated_at = ?, version = version + 1 WHERE id = ?
      `).run(now, id)
      this.#appendEvent(id, 'lease.released', { owner: task.lease_owner }, now)
      return taskFromRow(this.#taskRow(id))
    })
  }

  startRound(taskId, leaseToken, route = {}) {
    const id = requiredText(taskId, 'taskId')
    const provider = route.provider === undefined ? undefined : requiredText(route.provider, 'provider')
    const model = route.model === undefined ? undefined : requiredText(route.model, 'model')
    const promptHash = route.promptHash === undefined ? undefined : requiredText(route.promptHash, 'promptHash')
    const now = this.#clock()
    const outcome = this.#transaction(() => {
      const task = this.#assertActiveLease(id, leaseToken)
      if (task.rounds_started >= task.max_rounds) {
        this.#db.prepare(`
          UPDATE tasks SET status = ?, status_detail_json = ?,
            lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
            updated_at = ?, version = version + 1 WHERE id = ?
        `).run(
          TASK_STATUS.FAILED_EXHAUSTED,
          encodeJson({ code: 'round-limit', maxRounds: task.max_rounds }, 'status detail'),
          now,
          id,
        )
        this.#appendEvent(id, 'task.failed_exhausted', { maxRounds: task.max_rounds }, now)
        return { exhausted: true, maxRounds: task.max_rounds }
      }
      const round = task.rounds_started + 1
      this.#db.prepare(`
        UPDATE tasks SET rounds_started = ?, updated_at = ?, version = version + 1 WHERE id = ?
      `).run(round, now, id)
      this.#appendEvent(id, 'round.started', { round, provider, model, promptHash }, now)
      return { exhausted: false, round, task: taskFromRow(this.#taskRow(id)) }
    })
    if (outcome.exhausted) {
      throw new HarnessStateError('ROUND_LIMIT', `Task "${id}" reached ${outcome.maxRounds} rounds.`)
    }
    return Object.freeze(outcome)
  }

  checkpoint(taskId, leaseToken, checkpoint) {
    const id = requiredText(taskId, 'taskId')
    if (checkpoint === null || typeof checkpoint !== 'object' || Array.isArray(checkpoint)) {
      throw new HarnessStateError('INVALID_INPUT', 'checkpoint must be an object.')
    }
    const value = Object.freeze({
      summary: requiredText(checkpoint.summary, 'checkpoint.summary'),
      nextAction: requiredText(checkpoint.nextAction, 'checkpoint.nextAction'),
      artifacts: normalizeStringArray(checkpoint.artifacts, 'checkpoint.artifacts'),
      data: checkpoint.data === undefined ? undefined : checkpoint.data,
    })
    const encoded = encodeJson(value, 'checkpoint')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertActiveLease(id, leaseToken)
      const seq = this.#appendEvent(id, 'task.checkpointed', value, now)
      this.#db.prepare(`
        UPDATE tasks SET checkpoint_json = ?, checkpoint_event_seq = ?,
          updated_at = ?, version = version + 1 WHERE id = ?
      `).run(encoded, seq, now, id)
      return taskFromRow(this.#taskRow(id))
    })
  }

  prepareEffect(taskId, leaseToken, { key, kind, request }) {
    const id = requiredText(taskId, 'taskId')
    const effectKey = requiredText(key, 'key')
    const effectKind = requiredText(kind, 'kind')
    const requestJson = encodeJson(request, 'request')
    const now = this.#clock()

    return this.#transaction(() => {
      this.#assertActiveLease(id, leaseToken)
      const existing = this.#db.prepare(`
        SELECT * FROM effects WHERE task_id = ? AND idempotency_key = ?
      `).get(id, effectKey)
      if (existing !== undefined) {
        if (existing.kind !== effectKind || existing.request_json !== requestJson) {
          throw new HarnessStateError(
            'IDEMPOTENCY_CONFLICT',
            `Effect key "${effectKey}" was already used with a different request.`,
          )
        }
        return effectFromRow(existing)
      }

      const task = this.#taskRow(id)
      if (task.checkpoint_event_seq === null || task.checkpoint_event_seq <= task.last_effect_event_seq) {
        throw new HarnessStateError(
          'CHECKPOINT_REQUIRED',
          `Task "${id}" needs a fresh durable checkpoint before another side effect.`,
        )
      }

      const effectId = randomUUID()
      this.#db.prepare(`
        INSERT INTO effects(
          id, task_id, idempotency_key, kind, request_json, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'PREPARED', ?, ?)
      `).run(effectId, id, effectKey, effectKind, requestJson, now, now)
      const seq = this.#appendEvent(id, 'effect.prepared', {
        effectId,
        key: effectKey,
        kind: effectKind,
        request,
      }, now)
      this.#db.prepare(`
        UPDATE tasks SET last_effect_event_seq = ?, updated_at = ?, version = version + 1 WHERE id = ?
      `).run(seq, now, id)
      return effectFromRow(this.#effectRow(effectId))
    })
  }

  markEffectStarted(taskId, leaseToken, effectId) {
    const id = requiredText(taskId, 'taskId')
    const target = requiredText(effectId, 'effectId')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertActiveLease(id, leaseToken)
      const effect = this.#effectRow(target)
      if (effect.task_id !== id) {
        throw new HarnessStateError('EFFECT_TASK_MISMATCH', `Effect "${target}" does not belong to task "${id}".`)
      }
      if (effect.status === 'STARTED' || effect.status === 'COMMITTED') return effectFromRow(effect)
      if (effect.status !== 'PREPARED') {
        throw new HarnessStateError('EFFECT_STATE', `Effect "${target}" cannot start from ${effect.status}.`)
      }
      this.#db.prepare(`UPDATE effects SET status = 'STARTED', updated_at = ? WHERE id = ?`).run(now, target)
      this.#appendEvent(id, 'effect.started', { effectId: target, key: effect.idempotency_key }, now)
      this.#db.prepare(`UPDATE tasks SET updated_at = ?, version = version + 1 WHERE id = ?`).run(now, id)
      return effectFromRow(this.#effectRow(target))
    })
  }

  commitEffect(taskId, leaseToken, effectId, result) {
    const id = requiredText(taskId, 'taskId')
    const target = requiredText(effectId, 'effectId')
    const resultJson = encodeJson(result, 'result')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertActiveLease(id, leaseToken)
      const effect = this.#effectRow(target)
      if (effect.task_id !== id) {
        throw new HarnessStateError('EFFECT_TASK_MISMATCH', `Effect "${target}" does not belong to task "${id}".`)
      }
      if (effect.status === 'COMMITTED') {
        if (effect.result_json !== resultJson) {
          throw new HarnessStateError('EFFECT_RESULT_CONFLICT', `Effect "${target}" has a different committed result.`)
        }
        return effectFromRow(effect)
      }
      if (effect.status !== 'STARTED') {
        throw new HarnessStateError('EFFECT_STATE', `Effect "${target}" cannot commit from ${effect.status}.`)
      }
      this.#db.prepare(`
        UPDATE effects SET status = 'COMMITTED', result_json = ?, updated_at = ? WHERE id = ?
      `).run(resultJson, now, target)
      this.#appendEvent(id, 'effect.committed', { effectId: target, result }, now)
      this.#db.prepare(`UPDATE tasks SET updated_at = ?, version = version + 1 WHERE id = ?`).run(now, id)
      return effectFromRow(this.#effectRow(target))
    })
  }

  failEffect(taskId, leaseToken, effectId, error, detail = undefined) {
    const id = requiredText(taskId, 'taskId')
    const target = requiredText(effectId, 'effectId')
    const message = requiredText(error, 'error')
    const now = this.#clock()
    return this.#transaction(() => {
      this.#assertActiveLease(id, leaseToken)
      const effect = this.#effectRow(target)
      if (effect.task_id !== id) {
        throw new HarnessStateError('EFFECT_TASK_MISMATCH', `Effect "${target}" does not belong to task "${id}".`)
      }
      if (effect.status !== 'STARTED') {
        throw new HarnessStateError('EFFECT_STATE', `Effect "${target}" cannot fail from ${effect.status}.`)
      }
      const result = detail === undefined ? { error: message } : { error: message, detail }
      this.#db.prepare(`
        UPDATE effects SET status = 'FAILED', result_json = ?, updated_at = ? WHERE id = ?
      `).run(encodeJson(result, 'effect failure'), now, target)
      this.#appendEvent(id, 'effect.failed', { effectId: target, error: message }, now)
      this.#db.prepare(`UPDATE tasks SET updated_at = ?, version = version + 1 WHERE id = ?`).run(now, id)
      return effectFromRow(this.#effectRow(target))
    })
  }

  getEffect(effectId) {
    this.#assertOpen()
    return effectFromRow(this.#effectRow(requiredText(effectId, 'effectId')))
  }

  listEffects(taskId) {
    this.#assertOpen()
    const id = requiredText(taskId, 'taskId')
    this.#taskRow(id)
    return this.#db.prepare(`
      SELECT * FROM effects WHERE task_id = ? ORDER BY created_at, rowid
    `).all(id).map(effectFromRow)
  }

  recover() {
    const now = this.#clock()
    return this.#transaction(() => {
      const released = []
      const expired = this.#db.prepare(`
        SELECT id, lease_owner FROM tasks
        WHERE lease_token IS NOT NULL AND lease_expires_at <= ? ORDER BY id
      `).all(now)
      for (const task of expired) {
        this.#db.prepare(`
          UPDATE tasks SET lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
            updated_at = ?, version = version + 1 WHERE id = ?
        `).run(now, task.id)
        this.#appendEvent(task.id, 'lease.expired', { owner: task.lease_owner }, now)
        released.push(task.id)
      }

      const uncertain = []
      const started = this.#db.prepare(`
        SELECT * FROM effects WHERE status = 'STARTED' ORDER BY task_id, created_at, id
      `).all()
      for (const effect of started) {
        this.#db.prepare(`
          UPDATE effects SET status = 'OUTCOME_UNKNOWN', updated_at = ? WHERE id = ?
        `).run(now, effect.id)
        this.#appendEvent(effect.task_id, 'effect.outcome_unknown', {
          effectId: effect.id,
          key: effect.idempotency_key,
          reason: 'process-recovery',
        }, now)
        const task = this.#taskRow(effect.task_id)
        if (!TERMINAL_STATUSES.has(task.status)) {
          this.#db.prepare(`
            UPDATE tasks SET status = ?, status_detail_json = ?,
              lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
              updated_at = ?, version = version + 1 WHERE id = ?
          `).run(
            TASK_STATUS.BLOCKED_HUMAN,
            encodeJson({
              code: 'effect-outcome-unknown',
              effectId: effect.id,
              message: 'Verify the external effect before retrying or resolving it.',
            }, 'status detail'),
            now,
            effect.task_id,
          )
          this.#appendEvent(effect.task_id, 'task.blocked', {
            code: 'effect-outcome-unknown',
            effectId: effect.id,
          }, now)
        }
        uncertain.push(effect.id)
      }

      return Object.freeze({
        releasedLeases: Object.freeze(released),
        uncertainEffects: Object.freeze(uncertain),
        resumableTasks: Object.freeze(this.#db.prepare(`
          SELECT id FROM tasks WHERE status = 'ACTIVE' AND lease_token IS NULL ORDER BY updated_at, id
        `).all().map(row => row.id)),
      })
    })
  }

  resolveEffect(effectId, { resolver, outcome, evidence, result } = {}) {
    const target = requiredText(effectId, 'effectId')
    const authority = requiredText(resolver, 'resolver')
    if (outcome !== 'committed' && outcome !== 'failed') {
      throw new HarnessStateError('INVALID_INPUT', 'outcome must be "committed" or "failed".')
    }
    const proof = normalizeStringArray(evidence, 'evidence', { required: true })
    const resolvedResult = result === undefined
      ? { resolvedBy: authority, outcome, evidence: proof }
      : result
    const resultJson = encodeJson(resolvedResult, 'result')
    const now = this.#clock()

    return this.#transaction(() => {
      const effect = this.#effectRow(target)
      if (effect.status !== 'OUTCOME_UNKNOWN') {
        throw new HarnessStateError(
          'EFFECT_NOT_UNCERTAIN',
          `Effect "${target}" is ${effect.status}, not OUTCOME_UNKNOWN.`,
        )
      }
      const task = this.#taskRow(effect.task_id)
      if (task.status !== TASK_STATUS.BLOCKED_HUMAN) {
        throw new HarnessStateError(
          'TASK_NOT_BLOCKED',
          `Task "${effect.task_id}" is ${task.status}, not BLOCKED_HUMAN.`,
        )
      }

      const status = outcome === 'committed' ? 'COMMITTED' : 'FAILED'
      this.#db.prepare(`
        UPDATE effects SET status = ?, result_json = ?, updated_at = ? WHERE id = ?
      `).run(status, resultJson, now, target)
      const resolution = {
        effectId: target,
        resolver: authority,
        outcome,
        evidence: proof,
        result: resolvedResult,
      }
      this.#appendEvent(effect.task_id, 'effect.resolved', resolution, now)

      const remaining = this.#db.prepare(`
        SELECT id FROM effects WHERE task_id = ? AND status = 'OUTCOME_UNKNOWN' ORDER BY created_at, id
      `).all(effect.task_id)
      if (remaining.length === 0) {
        this.#db.prepare(`
          UPDATE tasks SET status = ?, status_detail_json = ?,
            lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
            updated_at = ?, version = version + 1 WHERE id = ?
        `).run(
          TASK_STATUS.ACTIVE,
          encodeJson({ code: 'effect-resolved', ...resolution }, 'status detail'),
          now,
          effect.task_id,
        )
        this.#appendEvent(effect.task_id, 'task.resumed', {
          resolver: authority,
          reason: `Effect ${target} was resolved as ${outcome}.`,
          evidence: proof,
        }, now)
      }
      else {
        this.#db.prepare(`
          UPDATE tasks SET status_detail_json = ?, updated_at = ?, version = version + 1 WHERE id = ?
        `).run(
          encodeJson({
            code: 'effect-outcome-unknown',
            effectId: remaining[0].id,
            remaining: remaining.length,
            message: 'Resolve every uncertain external effect before resuming.',
          }, 'status detail'),
          now,
          effect.task_id,
        )
      }

      return Object.freeze({
        effect: effectFromRow(this.#effectRow(target)),
        task: taskFromRow(this.#taskRow(effect.task_id)),
      })
    })
  }

  /**
   * Host-only ownership transfer used by a checkpoint-rehydrated supervisor.
   * It is intentionally not registered as a model-facing tool.
   */
  rebindTaskSession(taskId, { fromSessionId, toSessionId, authority, evidence } = {}) {
    const id = requiredText(taskId, 'taskId')
    const expectedSession = fromSessionId === undefined
      ? undefined
      : requiredText(fromSessionId, 'fromSessionId')
    const nextSession = requiredText(toSessionId, 'toSessionId')
    const owner = requiredText(authority, 'authority')
    const proof = normalizeStringArray(evidence, 'evidence', { required: true })
    const now = this.#clock()
    return this.#transaction(() => {
      const task = this.#taskRow(id)
      if (task.status !== TASK_STATUS.ACTIVE) {
        throw new HarnessStateError('TASK_NOT_REBINDABLE', `Task "${id}" is ${task.status}.`)
      }
      if (task.session_id === nextSession) return taskFromRow(task)
      if (expectedSession !== undefined && task.session_id !== expectedSession) {
        throw new HarnessStateError(
          'SESSION_REBIND_CONFLICT',
          `Task "${id}" belongs to session "${String(task.session_id)}", not "${expectedSession}".`,
        )
      }
      if (task.lease_token !== null) {
        throw new HarnessStateError('LEASE_HELD', `Task "${id}" still has a worker lease.`, {
          owner: task.lease_owner,
          expiresAt: task.lease_expires_at,
        })
      }
      const openEffects = this.#db.prepare(`
        SELECT id, status FROM effects
        WHERE task_id = ? AND status IN ('PREPARED', 'STARTED', 'OUTCOME_UNKNOWN')
        ORDER BY created_at, id
      `).all(id)
      if (openEffects.length > 0) {
        throw new HarnessStateError(
          'EFFECT_RECONCILIATION_REQUIRED',
          `Task "${id}" has ${openEffects.length} unfinished external effect(s).`,
          { effects: openEffects },
        )
      }
      const previousSession = task.session_id
      this.#db.prepare(`
        UPDATE tasks SET session_id = ?, updated_at = ?, version = version + 1 WHERE id = ?
      `).run(nextSession, now, id)
      this.#appendEvent(id, 'task.session_rebound', {
        fromSessionId: previousSession,
        toSessionId: nextSession,
        authority: owner,
        evidence: proof,
      }, now)
      return taskFromRow(this.#taskRow(id))
    })
  }

  resumeTask(taskId, { resolver, reason, evidence } = {}) {
    const id = requiredText(taskId, 'taskId')
    const authority = requiredText(resolver, 'resolver')
    const explanation = requiredText(reason, 'reason')
    const proof = normalizeStringArray(evidence, 'evidence', { required: true })
    const now = this.#clock()
    return this.#transaction(() => {
      const task = this.#taskRow(id)
      if (task.status !== TASK_STATUS.BLOCKED_HUMAN) {
        throw new HarnessStateError('TASK_NOT_BLOCKED', `Task "${id}" is ${task.status}, not BLOCKED_HUMAN.`)
      }
      const unresolved = this.#db.prepare(`
        SELECT id FROM effects WHERE task_id = ? AND status = 'OUTCOME_UNKNOWN' ORDER BY created_at, id
      `).all(id)
      if (unresolved.length > 0) {
        throw new HarnessStateError(
          'EFFECT_RECONCILIATION_REQUIRED',
          `Task "${id}" has ${unresolved.length} uncertain effect(s) that must be resolved first.`,
          { effectIds: unresolved.map(effect => effect.id) },
        )
      }
      const detail = { resolver: authority, reason: explanation, evidence: proof }
      this.#db.prepare(`
        UPDATE tasks SET status = ?, status_detail_json = ?,
          lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
          updated_at = ?, version = version + 1 WHERE id = ?
      `).run(TASK_STATUS.ACTIVE, encodeJson(detail, 'resume detail'), now, id)
      this.#appendEvent(id, 'task.resumed', detail, now)
      return taskFromRow(this.#taskRow(id))
    })
  }

  requestCompletion(taskId, leaseToken, { summary, evidence }) {
    const id = requiredText(taskId, 'taskId')
    const completionSummary = requiredText(summary, 'summary')
    const proof = normalizeStringArray(evidence, 'evidence', { required: true })
    const now = this.#clock()
    return this.#transaction(() => {
      const task = this.#assertActiveLease(id, leaseToken)
      if (task.checkpoint_event_seq === null || task.checkpoint_event_seq <= task.last_effect_event_seq) {
        throw new HarnessStateError(
          'CHECKPOINT_REQUIRED',
          `Task "${id}" needs a checkpoint after its last side effect before completion.`,
        )
      }
      const openEffects = this.#db.prepare(`
        SELECT COUNT(*) AS count FROM effects
        WHERE task_id = ? AND status IN ('PREPARED', 'STARTED', 'OUTCOME_UNKNOWN')
      `).get(id).count
      if (openEffects > 0) {
        throw new HarnessStateError('EFFECTS_OPEN', `Task "${id}" has ${openEffects} unresolved effect(s).`)
      }
      const detail = { summary: completionSummary, evidence: proof }
      this.#db.prepare(`
        UPDATE tasks SET status = ?, status_detail_json = ?,
          lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
          updated_at = ?, version = version + 1 WHERE id = ?
      `).run(TASK_STATUS.COMPLETED_PENDING_VERIFY, encodeJson(detail, 'completion'), now, id)
      this.#appendEvent(id, 'completion.requested', detail, now)
      return taskFromRow(this.#taskRow(id))
    })
  }

  verifyCompletion(taskId, { verifier, outcome, evidence }) {
    const id = requiredText(taskId, 'taskId')
    const gate = requiredText(verifier, 'verifier')
    if (outcome !== 'pass' && outcome !== 'fail') {
      throw new HarnessStateError('INVALID_INPUT', 'outcome must be "pass" or "fail".')
    }
    const proof = normalizeStringArray(evidence, 'evidence', { required: outcome === 'pass' })
    const now = this.#clock()
    return this.#transaction(() => {
      const task = this.#taskRow(id)
      if (task.status !== TASK_STATUS.COMPLETED_PENDING_VERIFY) {
        throw new HarnessStateError(
          'TASK_NOT_PENDING_VERIFY',
          `Task "${id}" is ${task.status}, not COMPLETED_PENDING_VERIFY.`,
        )
      }
      const status = outcome === 'pass' ? TASK_STATUS.COMPLETED_VERIFIED : TASK_STATUS.BLOCKED_HUMAN
      const detail = { verifier: gate, outcome, evidence: proof }
      this.#db.prepare(`
        UPDATE tasks SET status = ?, status_detail_json = ?, updated_at = ?, version = version + 1
        WHERE id = ?
      `).run(status, encodeJson(detail, 'verification'), now, id)
      this.#appendEvent(id, outcome === 'pass' ? 'completion.verified' : 'completion.rejected', detail, now)
      return taskFromRow(this.#taskRow(id))
    })
  }

  close() {
    if (this.#closed) return
    this.#db.close()
    this.#closed = true
  }
}
