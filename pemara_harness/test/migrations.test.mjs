import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import { DatabaseSync } from 'node:sqlite'

import { DurableTaskStore, SCHEMA_VERSION } from '../src/index.mjs'
import { migrateHarnessSchema } from '../src/migrations.mjs'

function temporaryDatabase() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-migration-'))
  return {
    path: join(root, 'ledger.sqlite'),
    cleanup() { rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 }) },
  }
}

function createV1(path, { version = 1 } = {}) {
  const db = new DatabaseSync(path)
  db.exec(`
    PRAGMA foreign_keys=ON;
    CREATE TABLE tasks (
      id TEXT PRIMARY KEY,
      objective TEXT NOT NULL,
      status TEXT NOT NULL,
      session_id TEXT,
      max_rounds INTEGER NOT NULL,
      rounds_started INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      version INTEGER NOT NULL,
      lease_owner TEXT,
      lease_token TEXT,
      lease_expires_at INTEGER,
      checkpoint_json TEXT,
      checkpoint_event_seq INTEGER,
      last_effect_event_seq INTEGER NOT NULL DEFAULT 0,
      status_detail_json TEXT,
      next_event_seq INTEGER NOT NULL DEFAULT 1
    ) STRICT;
    CREATE TABLE task_events (
      task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
      seq INTEGER NOT NULL,
      type TEXT NOT NULL,
      at INTEGER NOT NULL,
      payload_json TEXT NOT NULL,
      PRIMARY KEY (task_id, seq)
    ) STRICT;
    CREATE TABLE effects (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
      idempotency_key TEXT NOT NULL,
      kind TEXT NOT NULL,
      request_json TEXT NOT NULL,
      status TEXT NOT NULL,
      result_json TEXT,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      UNIQUE (task_id, idempotency_key)
    ) STRICT;
    INSERT INTO tasks(
      id, objective, status, session_id, max_rounds, rounds_started,
      created_at, updated_at, version, next_event_seq
    ) VALUES ('task-v1', 'Preservar a tarefa', 'ACTIVE', 'session-v1', 6, 1, 100, 200, 3, 2);
    INSERT INTO task_events(task_id, seq, type, at, payload_json)
      VALUES ('task-v1', 1, 'task.created', 100, '{"objective":"Preservar a tarefa"}');
    INSERT INTO effects(
      id, task_id, idempotency_key, kind, request_json, status, result_json, created_at, updated_at
    ) VALUES ('effect-v1', 'task-v1', 'write-a', 'filesystem', '{"path":"a.txt"}', 'COMMITTED', '{"sha256":"abc"}', 150, 160);
    PRAGMA user_version=${version};
  `)
  return db
}

function tables(db) {
  return db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").all().map(row => row.name)
}

test('new ledgers use schema v2 with the supervisor journal', () => {
  const fx = temporaryDatabase()
  try {
    const store = new DurableTaskStore({ databasePath: fx.path })
    store.createTask({ id: 'task-new', objective: 'Nascer no schema atual' })
    store.close()

    const db = new DatabaseSync(fx.path, { readOnly: true })
    assert.equal(SCHEMA_VERSION, 2)
    assert.equal(db.prepare('PRAGMA user_version').get().user_version, 2)
    assert.deepEqual(
      tables(db).filter(name => name.startsWith('supervisor_')),
      ['supervisor_attempts', 'supervisor_jobs'],
    )
    db.close()
  }
  finally {
    fx.cleanup()
  }
})

test('explicit v1 to v2 migration preserves ledger rows and passes integrity_check', () => {
  const fx = temporaryDatabase()
  try {
    const db = createV1(fx.path)
    const result = migrateHarnessSchema(db)
    assert.deepEqual(result, { from: 1, to: 2, migrated: true })
    assert.equal(db.prepare('PRAGMA user_version').get().user_version, 2)
    assert.equal(db.prepare('SELECT objective FROM tasks WHERE id = ?').get('task-v1').objective, 'Preservar a tarefa')
    assert.equal(db.prepare('SELECT type FROM task_events WHERE task_id = ?').get('task-v1').type, 'task.created')
    assert.equal(db.prepare('SELECT status FROM effects WHERE id = ?').get('effect-v1').status, 'COMMITTED')
    assert.equal(db.prepare('PRAGMA integrity_check').get().integrity_check, 'ok')
    assert.deepEqual(tables(db).filter(name => name.startsWith('supervisor_')), ['supervisor_attempts', 'supervisor_jobs'])
    db.close()
  }
  finally {
    fx.cleanup()
  }
})

test('an injected migration failure rolls back tables and schema version completely', () => {
  const fx = temporaryDatabase()
  try {
    const db = createV1(fx.path)
    assert.throws(
      () => migrateHarnessSchema(db, {
        fault(step) {
          if (step === 'after-supervisor-jobs') throw new Error('falha injetada')
        },
      }),
      /falha injetada/,
    )
    assert.equal(db.prepare('PRAGMA user_version').get().user_version, 1)
    assert.deepEqual(tables(db).filter(name => name.startsWith('supervisor_')), [])
    assert.equal(db.prepare('SELECT COUNT(*) AS count FROM tasks').get().count, 1)
    assert.equal(db.prepare('PRAGMA integrity_check').get().integrity_check, 'ok')
    db.close()
  }
  finally {
    fx.cleanup()
  }
})

test('unknown schema versions are refused without mutation', () => {
  const fx = temporaryDatabase()
  try {
    const db = createV1(fx.path, { version: 99 })
    assert.throws(
      () => migrateHarnessSchema(db),
      error => error?.code === 'SCHEMA_UNSUPPORTED',
    )
    assert.equal(db.prepare('PRAGMA user_version').get().user_version, 99)
    assert.deepEqual(tables(db).filter(name => name.startsWith('supervisor_')), [])
    db.close()
  }
  finally {
    fx.cleanup()
  }
})

test('v1 remains operational until the host explicitly opts into migration', () => {
  const fx = temporaryDatabase()
  try {
    createV1(fx.path).close()
    let store = new DurableTaskStore({ databasePath: fx.path })
    assert.equal(store.getTask('task-v1').objective, 'Preservar a tarefa')
    store.close()

    let db = new DatabaseSync(fx.path, { readOnly: true })
    assert.equal(db.prepare('PRAGMA user_version').get().user_version, 1)
    db.close()

    store = new DurableTaskStore({ databasePath: fx.path, migrateSchema: true })
    assert.equal(store.getTask('task-v1').sessionId, 'session-v1')
    store.close()
    db = new DatabaseSync(fx.path, { readOnly: true })
    assert.equal(db.prepare('PRAGMA user_version').get().user_version, 2)
    db.close()
  }
  finally {
    fx.cleanup()
  }
})
