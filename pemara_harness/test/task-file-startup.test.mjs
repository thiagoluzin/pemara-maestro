import assert from 'node:assert/strict'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { apply, readTaskFile } from '../dsh/task-file-startup.mjs'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const monitorRoot = join(projectRoot, '.runtime', 'monitor')

test('task-file startup keeps monitor tasks out of argv while preserving manual fallback', () => {
  mkdirSync(monitorRoot, { recursive: true })
  const directory = mkdtempSync(join(monitorRoot, 'startup-test-'))
  const taskPath = join(directory, 'task.txt')
  const previous = process.env.PEMARA_TASK_FILE
  try {
    writeFileSync(taskPath, 'Analise os anexos com segurança.')
    assert.equal(readTaskFile(taskPath), 'Analise os anexos com segurança.')

    let provided
    process.env.PEMARA_TASK_FILE = taskPath
    apply({
      get(name) { return name === 'cmdlineArgs' ? { get: () => ['texto-que-nao-deve-ser-usado'] } : undefined },
      provide(name, value) { provided = { name, value } },
    })
    assert.deepEqual(provided, { name: 'headlessStartup', value: { task: 'Analise os anexos com segurança.' } })

    delete process.env.PEMARA_TASK_FILE
    apply({
      get(name) { return name === 'cmdlineArgs' ? { get: () => ['tarefa', 'manual'] } : undefined },
      provide(name, value) { provided = { name, value } },
    })
    assert.equal(provided.value.task, 'tarefa manual')
  }
  finally {
    if (previous === undefined) delete process.env.PEMARA_TASK_FILE
    else process.env.PEMARA_TASK_FILE = previous
    rmSync(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})

test('task-file startup refuses files outside the isolated monitor runtime', () => {
  assert.throws(() => readTaskFile(import.meta.filename), /recusado pelo limite/)
})
