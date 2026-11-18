import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'
import { runDoctor } from '../src/doctor.mjs'

const CHECK_NAMES = ['node', 'sqlite', 'repo', 'database', 'manifest', 'profile', 'qwen']
const QWEN_MODEL = 'qwen3.8-27b-uncensored-yarn-524k'
const PROFILE_FILES = [
  'cordis.patch.yml',
  'cordis.yml',
  'package.json',
  'pnpm-workspace.yaml',
]

function sha256(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function makeFixture(base) {
  const root = join(base, 'repo')
  const dbDir = join(root, '.runtime', 'dsh-home', 'pemara')
  const profileDir = join(root, '.runtime', 'dsh-home', 'profiles', 'pemara')
  mkdirSync(profileDir, { recursive: true })
  writeFileSync(join(root, 'package.json'), `{"name":"fixture","version":"0.0.0"}`)
  writeFileSync(join(root, 'MANIFEST_SHA256.csv'), 'path,sha256\n')
  for (const file of PROFILE_FILES) writeFileSync(join(profileDir, file), `profile ${file}\n`)
  const store = new DurableTaskStore({ databasePath: join(dbDir, 'ledger.sqlite') })
  store.createTask({ id: 'fixture-1', objective: 'fixture task' })
  store.close()
  return {
    root,
    dbPath: join(dbDir, 'ledger.sqlite'),
    profileDir,
  }
}

function okManifestCheck() {
  return async () => ({ status: 'ok', code: 'MANIFEST_OK' })
}

function qwenOnlineFetch() {
  return async () => ({
    ok: true,
    status: 200,
    json: async () => ({ object: 'list', data: [{ id: QWEN_MODEL, name: QWEN_MODEL }] }),
  })
}

function qwenOfflineFetch() {
  return async () => {
    throw new Error('connect ECONNREFUSED 127.0.0.1:11436')
  }
}

function doctorOptions(fx, { fetchImpl = qwenOnlineFetch(), manifestCheck = okManifestCheck(), dbPath } = {}) {
  return {
    root: fx.root,
    dbPath: dbPath ?? fx.dbPath,
    fetchImpl,
    manifestCheck,
    nodeVersion: '24.16.0',
  }
}

test('doctor returns a full green report in stable check order', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const report = await runDoctor(doctorOptions(fx))
    assert.equal(report.ok, true)
    assert.equal(typeof report.generatedAt, 'number')
    assert.equal(report.root, fx.root)
    assert.deepEqual(report.checks.map(check => check.name), CHECK_NAMES)
    for (const check of report.checks) {
      assert.equal(check.status, 'ok', check.name)
    }
    const database = report.checks.find(check => check.name === 'database')
    assert.equal(database.code, 'DB_OK')
    assert.equal(database.detail.schemaVersion, 2)
    assert.equal(database.detail.counts.tasks, 1)
    assert.deepEqual(database.detail.tables, [
      'effects',
      'supervisor_attempts',
      'supervisor_jobs',
      'task_events',
      'tasks',
    ])
    const qwen = report.checks.find(check => check.name === 'qwen')
    assert.equal(qwen.code, 'QWEN_OK')
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('supported v1 ledger remains healthy and reports migration available', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const { DatabaseSync } = await import('node:sqlite')
    const db = new DatabaseSync(fx.dbPath)
    db.exec('PRAGMA user_version=1')
    db.close()

    const report = await runDoctor(doctorOptions(fx))
    const database = report.checks.find(check => check.name === 'database')
    assert.equal(report.ok, true)
    assert.equal(database.status, 'warn')
    assert.equal(database.code, 'DB_SCHEMA_MIGRATION_AVAILABLE')
    assert.deepEqual(
      { schemaVersion: database.detail.schemaVersion, target: database.detail.target },
      { schemaVersion: 1, target: 2 },
    )
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('qwen offline is a warning with a stable code, not a crash', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const report = await runDoctor(doctorOptions(fx, { fetchImpl: qwenOfflineFetch() }))
    assert.equal(report.ok, true)
    const qwen = report.checks.find(check => check.name === 'qwen')
    assert.equal(qwen.status, 'warn')
    assert.equal(qwen.code, 'QWEN_OFFLINE')
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('qwen endpoint without the expected model warns QWEN_MODEL_MISSING', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const fetchImpl = async () => ({
      ok: true,
      status: 200,
      json: async () => ({ object: 'list', data: [{ id: 'other-model' }] }),
    })
    const report = await runDoctor(doctorOptions(fx, { fetchImpl }))
    const qwen = report.checks.find(check => check.name === 'qwen')
    assert.equal(qwen.status, 'warn')
    assert.equal(qwen.code, 'QWEN_MODEL_MISSING')
    assert.equal(report.ok, true)
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('missing database file fails the report', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const report = await runDoctor(doctorOptions(fx, { dbPath: join(fx.root, 'nope.sqlite') }))
    assert.equal(report.ok, false)
    const database = report.checks.find(check => check.name === 'database')
    assert.equal(database.status, 'fail')
    assert.equal(database.code, 'DB_PATH_MISSING')
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('unsupported schema version fails with DB_SCHEMA_UNSUPPORTED', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const { DatabaseSync } = await import('node:sqlite')
    const db = new DatabaseSync(fx.dbPath)
    db.exec('PRAGMA user_version=99')
    db.close()
    const report = await runDoctor(doctorOptions(fx))
    const database = report.checks.find(check => check.name === 'database')
    assert.equal(report.ok, false)
    assert.equal(database.status, 'fail')
    assert.equal(database.code, 'DB_SCHEMA_UNSUPPORTED')
    assert.equal(database.detail.schemaVersion, 99)
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('schema without the ledger tables fails with DB_TABLES_MISSING', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const { DatabaseSync } = await import('node:sqlite')
    const db = new DatabaseSync(fx.dbPath)
    db.exec('DROP TABLE effects')
    db.close()
    const report = await runDoctor(doctorOptions(fx))
    const database = report.checks.find(check => check.name === 'database')
    assert.equal(database.status, 'fail')
    assert.equal(database.code, 'DB_TABLES_MISSING')
    assert.deepEqual(database.detail.missingTables, ['effects'])
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('doctor is read-only: ledger hash and directory stay unchanged', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const beforeHash = sha256(fx.dbPath)
    const dbDir = join(fx.root, '.runtime', 'dsh-home', 'pemara')
    const beforeFiles = new Set(readdirSync(dbDir))

    await runDoctor(doctorOptions(fx))

    assert.equal(sha256(fx.dbPath), beforeHash)
    const afterFiles = readdirSync(dbDir)
    for (const file of afterFiles) {
      assert.ok(
        beforeFiles.has(file)
          || file === 'ledger.sqlite-shm'
          || file === 'ledger.sqlite-wal',
        `unexpected file created by doctor: ${file}`,
      )
    }
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('missing profile files are listed in the failure detail', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    rmSync(join(fx.profileDir, 'package.json'))
    rmSync(join(fx.profileDir, 'cordis.yml'))
    const report = await runDoctor(doctorOptions(fx))
    assert.equal(report.ok, false)
    const profile = report.checks.find(check => check.name === 'profile')
    assert.equal(profile.status, 'fail')
    assert.equal(profile.code, 'PROFILE_FILES_MISSING')
    assert.deepEqual(profile.detail.missing.sort(), ['cordis.yml', 'package.json'])
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('a stale manifest fails the report', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const manifestCheck = async () => ({
      status: 'fail',
      code: 'MANIFEST_STALE',
      detail: { changed: 2, missing: 0, unexpected: 0 },
    })
    const report = await runDoctor(doctorOptions(fx, { manifestCheck }))
    assert.equal(report.ok, false)
    const manifest = report.checks.find(check => check.name === 'manifest')
    assert.equal(manifest.status, 'fail')
    assert.equal(manifest.code, 'MANIFEST_STALE')
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('node below 24 fails the report', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-doctor-'))
  try {
    const fx = makeFixture(base)
    const report = await runDoctor({ ...doctorOptions(fx), nodeVersion: '20.11.0' })
    assert.equal(report.ok, false)
    const node = report.checks.find(check => check.name === 'node')
    assert.equal(node.status, 'fail')
    assert.equal(node.code, 'NODE_VERSION_LOW')
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})
