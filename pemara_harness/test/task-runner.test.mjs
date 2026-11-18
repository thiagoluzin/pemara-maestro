import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { createTaskRunner, normalizeTaskSubmission, runTaskWorker } from '../src/task-runner.mjs'

test('task submissions accept only one bounded task field', () => {
  assert.deepEqual(
    normalizeTaskSubmission({ task: '  Corrigir o harness  ' }),
    { task: 'Corrigir o harness', attachmentIds: [] },
  )
  assert.throws(() => normalizeTaskSubmission({ task: '' }), /tarefa/i)
  assert.throws(() => normalizeTaskSubmission({ task: 'ok', command: 'pwsh' }), /campo/i)
  assert.throws(() => normalizeTaskSubmission({ task: `x${'a'.repeat(16_000)}` }), /16\.000/i)
  assert.throws(() => normalizeTaskSubmission({ task: 'linha\u0000invalida' }), /caractere/i)
})

test('task runner persists one detached job without putting the task on its command line', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-task-runner-'))
  const launches = []
  const runner = createTaskRunner({
    projectRoot: root,
    workspaceRoot: root,
    now: () => 1_787_330_000_000,
    launchDetached(entry, args, options) {
      launches.push({ entry, args, options })
      return { pid: 43210, unref() {} }
    },
  })

  const job = await runner.start({ task: 'Executar uma tarefa durável', workspace: root })
  assert.equal(job.status, 'queued')
  assert.equal(job.runnerPid, 43210)
  assert.equal(launches.length, 1)
  assert.equal(launches[0].entry, process.execPath)
  assert.equal(launches[0].options.detached, true)
  assert.equal(launches[0].args.includes('Executar uma tarefa durável'), false)
  assert.equal(launches[0].args[launches[0].args.indexOf('--provider-id') + 1], 'local-qwen')

  const taskFileIndex = launches[0].args.indexOf('--task-file') + 1
  assert.equal(await readFile(launches[0].args[taskFileIndex], 'utf8'), 'Executar uma tarefa durável')
  const snapshot = await runner.snapshot()
  assert.equal(snapshot.id, job.id)
  assert.equal(snapshot.status, 'queued')

  await assert.rejects(
    runner.start({ task: 'Segunda tarefa', workspace: root }),
    error => error?.code === 'TASK_ACTIVE',
  )
})

test('task runner accepts a selected project inside the workspace boundary', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-task-project-'))
  const project = join(root, 'meu-projeto')
  await mkdir(project, { recursive: true })
  const launches = []
  const runner = createTaskRunner({
    projectRoot: root,
    workspaceRoot: root,
    launchDetached(entry, args, options) {
      launches.push({ entry, args, options })
      return { pid: 54321, unref() {} }
    },
  })

  const job = await runner.start({ task: 'Trabalhar no projeto escolhido', workspace: project, chatId: 'chat-local', projectId: 'project-local' })
  assert.equal(job.workspace, project)
  assert.equal(job.chatId, 'chat-local')
  assert.equal(job.projectId, 'project-local')
  assert.equal(launches[0].args[launches[0].args.indexOf('--workspace') + 1], project)
  assert.equal(job.providerId, 'local-qwen')
})

test('detached worker invokes only the fixed launcher and records the exit atomically', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-task-worker-'))
  const jobRoot = join(root, '.runtime', 'monitor', 'task-runner', 'jobs', 'job-test')
  await mkdir(jobRoot, { recursive: true })
  const paths = {
    projectRoot: root,
    workspace: root,
    stateFile: join(root, '.runtime', 'monitor', 'task-runner', 'current.json'),
    taskFile: join(jobRoot, 'task.txt'),
    stdoutFile: join(jobRoot, 'stdout.log'),
    stderrFile: join(jobRoot, 'stderr.log'),
  }
  await writeFile(paths.taskFile, 'Corrigir sem shell concatenado')
  await writeFile(paths.stateFile, JSON.stringify({
    id: 'job-test',
    task: 'Corrigir sem shell concatenado',
    status: 'queued',
    createdAt: 1,
  }))

  const launches = []
  const child = new EventEmitter()
  child.pid = 9876
  const code = await runTaskWorker(paths, {
    now: () => 2_000,
    launch(executable, args, options) {
      launches.push({ executable, args, options })
      process.nextTick(() => child.emit('close', 0, null))
      return child
    },
  })

  assert.equal(code, 0)
  assert.equal(launches.length, 1)
  assert.match(launches[0].args[launches[0].args.indexOf('-File') + 1], /Open-PemaraHarness\.ps1$/)
  assert.equal(launches[0].args.includes('-Task'), false)
  assert.equal(launches[0].args[launches[0].args.indexOf('-TaskFile') + 1], paths.taskFile)
  assert.equal(launches[0].args.includes('Corrigir sem shell concatenado'), false)
  assert.equal(launches[0].args[launches[0].args.indexOf('-ProviderId') + 1], 'local-qwen')
  assert.equal(launches[0].options.cwd, root)
  const finalState = JSON.parse(await readFile(paths.stateFile, 'utf8'))
  assert.equal(finalState.status, 'completed')
  assert.equal(finalState.exitCode, 0)
  assert.equal(finalState.childPid, 9876)
})
