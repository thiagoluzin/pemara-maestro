import { existsSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'

import { SCHEMA_VERSION } from './index.mjs'
import { MIN_SUPPORTED_SCHEMA_VERSION } from './migrations.mjs'

const DEFAULT_QWEN_URL = 'http://127.0.0.1:11436/v1/models'
const EXPECTED_QWEN_MODEL = 'qwen3.8-27b-uncensored-yarn-524k'
const MIN_NODE_MAJOR = 24
const REQUIRED_TABLES = ['effects', 'task_events', 'tasks']
const PROFILE_DIR = join('.runtime', 'dsh-home', 'profiles', 'pemara')
const PROFILE_FILES = ['cordis.patch.yml', 'cordis.yml', 'package.json', 'pnpm-workspace.yaml']
const LEDGER_PATH = join('.runtime', 'dsh-home', 'pemara', 'ledger.sqlite')
const QWEN_TIMEOUT_MS = 3000

function ok(name, code, detail) {
  return Object.freeze({ name, status: 'ok', code, ...(detail === undefined ? {} : { detail }) })
}

function warn(name, code, detail) {
  return Object.freeze({ name, status: 'warn', code, ...(detail === undefined ? {} : { detail }) })
}

function fail(name, code, detail) {
  return Object.freeze({ name, status: 'fail', code, ...(detail === undefined ? {} : { detail }) })
}

function checkNode(nodeVersion) {
  const version = String(nodeVersion)
  const major = Number(version.split('.')[0])
  if (!Number.isFinite(major) || major < MIN_NODE_MAJOR) {
    return fail('node', 'NODE_VERSION_LOW', { version, required: `>=${MIN_NODE_MAJOR}` })
  }
  return ok('node', 'NODE_OK', { version })
}

async function checkSqlite() {
  try {
    const mod = await import('node:sqlite')
    if (typeof mod.DatabaseSync !== 'function') {
      return fail('sqlite', 'SQLITE_MODULE_MISSING', { module: 'node:sqlite' })
    }
    return ok('sqlite', 'SQLITE_OK', { module: 'node:sqlite' })
  }
  catch (error) {
    return fail('sqlite', 'SQLITE_MODULE_MISSING', {
      module: 'node:sqlite',
      error: error instanceof Error ? error.message : String(error),
    })
  }
}

function checkRepo(root) {
  const required = ['package.json', 'MANIFEST_SHA256.csv']
  const missing = required.filter(file => !existsSync(join(root, file)))
  if (missing.length > 0) {
    return fail('repo', 'REPO_ROOT_MISSING', { missing })
  }
  return ok('repo', 'REPO_OK', { root })
}

async function checkDatabase(dbPath) {
  if (!existsSync(dbPath)) {
    return fail('database', 'DB_PATH_MISSING', { path: dbPath })
  }
  const { DatabaseSync } = await import('node:sqlite')
  let db
  try {
    // Read-only open: a clean WAL ledger must survive the diagnosis without
    // a single byte changing in the main file.
    db = new DatabaseSync(dbPath, { readOnly: true })
  }
  catch (error) {
    return fail('database', 'DB_OPEN_FAILED', {
      path: dbPath,
      error: error instanceof Error ? error.message : String(error),
    })
  }

  try {
    const schemaVersion = db.prepare('PRAGMA user_version').get().user_version
    if (schemaVersion !== SCHEMA_VERSION && schemaVersion !== MIN_SUPPORTED_SCHEMA_VERSION) {
      return fail('database', 'DB_SCHEMA_UNSUPPORTED', {
        schemaVersion,
        expected: SCHEMA_VERSION,
      })
    }

    const names = db.prepare(`
      SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name
    `).all().map(row => row.name)
    const tableSet = new Set(names)
    const missingTables = REQUIRED_TABLES.filter(table => !tableSet.has(table)).sort()
    if (missingTables.length > 0) {
      return fail('database', 'DB_TABLES_MISSING', {
        schemaVersion,
        tables: names,
        missingTables,
      })
    }

    const integrity = db.prepare('PRAGMA integrity_check').all().map(row => row.integrity_check ?? row[0])
    if (integrity.length !== 1 || integrity[0] !== 'ok') {
      return fail('database', 'DB_INTEGRITY_FAILED', { integrity })
    }

    const counts = {}
    for (const table of REQUIRED_TABLES) {
      counts[table] = db.prepare(`SELECT COUNT(*) AS count FROM ${table}`).get().count
    }

    const detail = {
      schemaVersion,
      integrity: 'ok',
      tables: names,
      counts,
    }
    return schemaVersion === SCHEMA_VERSION
      ? ok('database', 'DB_OK', detail)
      : warn('database', 'DB_SCHEMA_MIGRATION_AVAILABLE', { ...detail, target: SCHEMA_VERSION })
  }
  finally {
    db.close()
  }
}

async function checkManifest(root, manifestCheck) {
  try {
    const result = await manifestCheck(root)
    return Object.freeze({
      name: 'manifest',
      status: result?.status === 'ok' ? 'ok' : 'fail',
      code: typeof result?.code === 'string' ? result.code : 'MANIFEST_CHECK_FAILED',
      ...(result?.detail === undefined ? {} : { detail: result.detail }),
    })
  }
  catch (error) {
    return fail('manifest', 'MANIFEST_CHECK_FAILED', {
      error: error instanceof Error ? error.message : String(error),
    })
  }
}

function checkProfile(root) {
  const profileDir = join(root, PROFILE_DIR)
  const missing = PROFILE_FILES.filter(file => !existsSync(join(profileDir, file)))
  if (missing.length > 0) {
    return fail('profile', 'PROFILE_FILES_MISSING', { missing: missing.sort() })
  }
  return ok('profile', 'PROFILE_OK', { directory: profileDir })
}

async function checkQwen(qwenUrl, expectedModel, fetchImpl) {
  let body
  try {
    const response = await fetchImpl(qwenUrl)
    body = await response.json()
  }
  catch {
    return warn('qwen', 'QWEN_OFFLINE', { url: qwenUrl })
  }
  const models = Array.isArray(body?.data)
    ? body.data.map(item => item?.id).filter(id => typeof id === 'string')
    : []
  if (!models.includes(expectedModel)) {
    return warn('qwen', 'QWEN_MODEL_MISSING', { url: qwenUrl, models })
  }
  return ok('qwen', 'QWEN_OK', { url: qwenUrl, model: expectedModel })
}

function defaultFetch(url) {
  return fetch(url, { signal: AbortSignal.timeout(QWEN_TIMEOUT_MS) })
}

/**
 * Read-only diagnosis of the Pemara Harness environment.
 *
 * The report shape is a protected contract (see test/doctor.test.mjs):
 * stable check order, stable codes, and `ok` false as soon as any check
 * fails. Warnings (Qwen offline, model not loaded) never block the report.
 */
export async function runDoctor(options = {}) {
  const root = resolve(options.root ?? process.cwd())
  const dbPath = options.dbPath === undefined
    ? join(root, LEDGER_PATH)
    : resolve(options.dbPath)
  const qwenUrl = options.qwenUrl ?? DEFAULT_QWEN_URL
  const expectedModel = options.expectedModel ?? EXPECTED_QWEN_MODEL
  const fetchImpl = options.fetchImpl ?? defaultFetch
  const manifestCheck = options.manifestCheck ?? (await import('./manifest.mjs')).checkManifest
  const nodeVersion = options.nodeVersion ?? process.versions.node

  const checks = [
    checkNode(nodeVersion),
    await checkSqlite(),
    checkRepo(root),
    await checkDatabase(dbPath),
    await checkManifest(root, manifestCheck),
    checkProfile(root),
    await checkQwen(qwenUrl, expectedModel, fetchImpl),
  ]

  return Object.freeze({
    ok: checks.every(check => check.status !== 'fail'),
    root,
    generatedAt: Date.now(),
    checks: Object.freeze(checks),
  })
}

export { DEFAULT_QWEN_URL, EXPECTED_QWEN_MODEL, PROFILE_FILES }
