export const SCHEMA_VERSION = 2
export const MIN_SUPPORTED_SCHEMA_VERSION = 1

const SUPERVISOR_JOBS_SQL = `
  CREATE TABLE IF NOT EXISTS supervisor_jobs (
    task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE RESTRICT,
    session_strategy TEXT NOT NULL CHECK (session_strategy IN ('checkpoint-rehydrate')),
    session_id TEXT,
    command_json TEXT NOT NULL,
    command_fingerprint TEXT NOT NULL,
    workspace TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
      'READY', 'RUNNING', 'BACKOFF', 'COMPLETED', 'STOPPED', 'EXHAUSTED', 'BLOCKED'
    )),
    max_restarts INTEGER NOT NULL CHECK (max_restarts >= 0),
    restarts_used INTEGER NOT NULL DEFAULT 0 CHECK (restarts_used >= 0),
    backoff_json TEXT NOT NULL,
    next_attempt_at INTEGER,
    lock_owner TEXT,
    lock_token TEXT,
    lock_expires_at INTEGER,
    lock_process_fingerprint TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    CHECK (restarts_used <= max_restarts),
    CHECK (
      (lock_owner IS NULL AND lock_token IS NULL AND lock_expires_at IS NULL AND lock_process_fingerprint IS NULL)
      OR
      (lock_owner IS NOT NULL AND lock_token IS NOT NULL AND lock_expires_at IS NOT NULL AND lock_process_fingerprint IS NOT NULL)
    )
  ) STRICT;
`

const SUPERVISOR_ATTEMPTS_SQL = `
  CREATE TABLE IF NOT EXISTS supervisor_attempts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES supervisor_jobs(task_id) ON DELETE RESTRICT,
    attempt_no INTEGER NOT NULL CHECK (attempt_no > 0),
    session_id TEXT,
    command_fingerprint TEXT NOT NULL,
    runner_fingerprint TEXT NOT NULL,
    pid INTEGER,
    process_started_at INTEGER,
    status TEXT NOT NULL CHECK (status IN (
      'ADMITTED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'INTERRUPTED', 'CANCELLED', 'OUTCOME_UNKNOWN'
    )),
    started_at INTEGER NOT NULL,
    heartbeat_at INTEGER NOT NULL,
    finished_at INTEGER,
    exit_code INTEGER,
    signal TEXT,
    result_json TEXT,
    UNIQUE (task_id, attempt_no)
  ) STRICT;
`

const SUPERVISOR_INDEXES_SQL = `
  CREATE INDEX IF NOT EXISTS idx_supervisor_jobs_state
    ON supervisor_jobs(status, next_attempt_at, updated_at);
  CREATE INDEX IF NOT EXISTS idx_supervisor_attempts_task
    ON supervisor_attempts(task_id, attempt_no);
  CREATE INDEX IF NOT EXISTS idx_supervisor_attempts_pid
    ON supervisor_attempts(pid, process_started_at);
`

export const SUPERVISOR_SCHEMA_SQL = `
  ${SUPERVISOR_JOBS_SQL}
  ${SUPERVISOR_ATTEMPTS_SQL}
  ${SUPERVISOR_INDEXES_SQL}
`

function schemaError(code, message, details = undefined) {
  const error = new Error(message)
  error.name = 'HarnessSchemaError'
  error.code = code
  error.details = details
  return error
}

export function installSupervisorSchema(database) {
  database.exec(SUPERVISOR_SCHEMA_SQL)
}

export function migrateHarnessSchema(database, { fault = () => {} } = {}) {
  if (database === null || typeof database?.exec !== 'function' || typeof database?.prepare !== 'function') {
    throw new TypeError('database must be an open node:sqlite DatabaseSync handle')
  }
  if (typeof fault !== 'function') throw new TypeError('fault must be a function')
  const from = database.prepare('PRAGMA user_version').get().user_version
  if (from === SCHEMA_VERSION) return Object.freeze({ from, to: SCHEMA_VERSION, migrated: false })
  if (from !== 1) {
    throw schemaError(
      'SCHEMA_UNSUPPORTED',
      `Harness database schema ${from} cannot migrate to ${SCHEMA_VERSION}.`,
      { actual: from, expected: [1, SCHEMA_VERSION] },
    )
  }

  database.exec('BEGIN IMMEDIATE')
  try {
    database.exec(SUPERVISOR_JOBS_SQL)
    fault('after-supervisor-jobs')
    database.exec(SUPERVISOR_ATTEMPTS_SQL)
    fault('after-supervisor-attempts')
    database.exec(SUPERVISOR_INDEXES_SQL)
    fault('after-supervisor-indexes')
    database.exec(`PRAGMA user_version=${SCHEMA_VERSION}`)
    fault('after-user-version')
    database.exec('COMMIT')
  }
  catch (error) {
    try { database.exec('ROLLBACK') } catch {}
    throw error
  }
  return Object.freeze({ from, to: SCHEMA_VERSION, migrated: true })
}
