import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

import { DurableTaskStore, TASK_STATUS } from '../src/index.mjs'

const worker = fileURLToPath(new URL('./fixtures/crash-worker.mjs', import.meta.url))

test('recovers an actual child process exit without repeating its started effect', () => {
  const directory = mkdtempSync(join(tmpdir(), 'pemara-crash-'))
  const databasePath = join(directory, 'harness.sqlite')
  try {
    const child = spawnSync(process.execPath, [worker, databasePath], {
      encoding: 'utf8',
      windowsHide: true,
    })
    assert.equal(child.status, 23, child.stderr)

    const store = new DurableTaskStore({ databasePath })
    const report = store.recover()
    assert.equal(report.uncertainEffects.length, 1)
    assert.equal(store.getEffect(report.uncertainEffects[0]).status, 'OUTCOME_UNKNOWN')
    assert.equal(store.getTask('crash-task').status, TASK_STATUS.BLOCKED_HUMAN)
    assert.equal(store.listEffects('crash-task').length, 1)
    store.close()
  }
  finally {
    rmSync(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})
