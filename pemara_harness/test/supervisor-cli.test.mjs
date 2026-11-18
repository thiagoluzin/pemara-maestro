import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const CLI = join(ROOT, 'bin', 'pemara-supervisor.mjs')
const CHILD = join(ROOT, 'test', 'fixtures', 'supervisor-child.mjs')

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-supervisor-cli-'))
  const databasePath = join(root, 'ledger.sqlite')
  const store = new DurableTaskStore({ databasePath })
  store.createTask({ id: 'cli-task', objective: 'Provar o supervisor CLI' })
  store.close()
  return {
    root,
    databasePath,
    cleanup() { rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 }) },
  }
}

function cli(args, options = {}) {
  return spawnSync(process.execPath, [CLI, ...args], {
    cwd: ROOT,
    encoding: 'utf8',
    timeout: 15_000,
    windowsHide: true,
    ...options,
  })
}

test('supervisor CLI configures, runs once and reports the durable journal', () => {
  const fx = fixture()
  try {
    const configured = cli([
      '--db', fx.databasePath,
      'configure',
      '--task-id', 'cli-task',
      '--executable', process.execPath,
      '--workspace', fx.root,
      '--arg', CHILD,
      '--arg', '{{PEMARA_TASK}}',
    ])
    assert.equal(configured.status, 0, configured.stderr)
    assert.equal(JSON.parse(configured.stdout).job.status, 'READY')

    const run = cli(['--db', fx.databasePath, 'run', '--task-id', 'cli-task', '--once'])
    assert.equal(run.status, 0, run.stderr)
    assert.equal(JSON.parse(run.stdout).status, 'COMPLETED')

    const status = cli(['--db', fx.databasePath, 'status', '--task-id', 'cli-task'])
    assert.equal(status.status, 0, status.stderr)
    const body = JSON.parse(status.stdout)
    assert.equal(body.job.status, 'COMPLETED')
    assert.equal(body.attempts.length, 1)
    assert.equal(body.attempts[0].result.stdout, 'fixture:true\n')
  }
  finally {
    fx.cleanup()
  }
})

test('supervisor CLI rejects unknown options without launching anything', () => {
  const fx = fixture()
  try {
    const result = cli([
      '--db', fx.databasePath,
      'configure',
      '--task-id', 'cli-task',
      '--executable', process.execPath,
      '--workspace', fx.root,
      '--command', 'whoami',
    ])
    assert.equal(result.status, 1)
    const body = JSON.parse(result.stderr)
    assert.equal(body.error.code, 'CLI_USAGE')
    assert.match(body.error.message, /--command/)
  }
  finally {
    fx.cleanup()
  }
})
