import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { DurableTaskStore, HarnessStateError } from '../src/index.mjs'
import { apply, Config, inject, name, registerMediaContext } from '../dsh/plugin.mjs'

function harnessContext() {
  const tools = new Map()
  const sections = []
  return {
    ctx: {
      tools: { register(definition) { tools.set(definition.name, definition); return () => tools.delete(definition.name) } },
      systemPrompt: { section(section) { sections.push(section); return () => {} } },
    },
    tools,
    sections,
  }
}

function execution(sessionId = 'session-a') {
  return { agent: { id: sessionId }, callId: 'call-1', rootCallId: 'call-1', signal: AbortSignal.timeout(5_000) }
}

test('exports a function plugin and binds durable task tools to the owning DSH session', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'pemara-dsh-plugin-'))
  const databasePath = join(directory, 'harness.sqlite')
  try {
    assert.equal(name, 'pemara-durable-harness')
    assert.deepEqual(inject, ['tools', 'systemPrompt'])
    assert.equal(Config['~standard'].version, 1)
    const fake = harnessContext()
    const dispose = apply(fake.ctx, { databasePath, leaseMs: 60_000 })

    assert.deepEqual([...fake.tools.keys()].sort(), [
      'harness_task_begin_round',
      'harness_task_checkpoint',
      'harness_task_create',
      'harness_task_get',
      'harness_task_request_completion',
    ])
    assert.equal(fake.sections.length, 1)

    const created = await fake.tools.get('harness_task_create').execute({
      task_id: 'dsh-task-1',
      objective: 'Continuar apesar de reinicios',
      max_rounds: 8,
    }, execution())
    assert.equal(created.task.sessionId, 'session-a')
    assert.equal(created.task.lease?.token, undefined)

    await fake.tools.get('harness_task_begin_round').execute({
      task_id: 'dsh-task-1', provider: 'local', model: 'deepseek',
    }, execution())
    const checkpointed = await fake.tools.get('harness_task_checkpoint').execute({
      task_id: 'dsh-task-1',
      summary: 'Estado salvo.',
      next_action: 'Rodar validacao.',
      artifacts: ['report.json'],
    }, execution())
    assert.equal(checkpointed.task.roundsStarted, 1)

    await assert.rejects(
      () => fake.tools.get('harness_task_get').execute({ task_id: 'dsh-task-1' }, execution('session-b')),
      error => error instanceof HarnessStateError && error.code === 'TASK_SCOPE',
    )

    const pending = await fake.tools.get('harness_task_request_completion').execute({
      task_id: 'dsh-task-1',
      summary: 'Criterios satisfeitos.',
      evidence: ['node --test passou'],
    }, execution())
    assert.equal(pending.task.status, 'COMPLETED_PENDING_VERIFY')
    await dispose()

    const store = new DurableTaskStore({ databasePath })
    assert.equal(store.getTask('dsh-task-1').lease, undefined)
    store.close()
  }
  finally {
    rmSync(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})

test('host supervisor can rebind one checkpointed task into exactly one fresh DSH session', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'pemara-dsh-rebind-'))
  const databasePath = join(directory, 'harness.sqlite')
  try {
    const original = harnessContext()
    const disposeOriginal = apply(original.ctx, { databasePath, leaseMs: 60_000 })
    await original.tools.get('harness_task_create').execute({
      task_id: 'dsh-resume-1',
      objective: 'Retomar pelo supervisor',
      max_rounds: 4,
    }, execution('session-old'))
    await original.tools.get('harness_task_begin_round').execute({ task_id: 'dsh-resume-1' }, execution('session-old'))
    await original.tools.get('harness_task_checkpoint').execute({
      task_id: 'dsh-resume-1',
      summary: 'Primeira etapa persistida.',
      next_action: 'Continuar na sessão nova.',
      artifacts: ['checkpoint.json'],
    }, execution('session-old'))
    await disposeOriginal()

    const resumed = harnessContext()
    const disposeResumed = apply(resumed.ctx, {
      databasePath,
      leaseMs: 60_000,
      rebindTaskId: 'dsh-resume-1',
      rebindAttemptId: 'attempt-2',
      rebindAuthority: 'pemara-supervisor:attempt-2',
    })
    const read = await resumed.tools.get('harness_task_get').execute(
      { task_id: 'dsh-resume-1' },
      execution('session-new'),
    )
    assert.equal(read.task.sessionId, 'session-new')
    assert.equal(read.task.checkpoint.nextAction, 'Continuar na sessão nova.')
    await disposeResumed()

    const store = new DurableTaskStore({ databasePath })
    const rebound = store.listEvents('dsh-resume-1').filter(event => event.type === 'task.session_rebound')
    assert.equal(rebound.length, 1)
    assert.equal(rebound[0].payload.fromSessionId, 'session-old')
    assert.equal(rebound[0].payload.toSessionId, 'session-new')
    assert.equal(rebound[0].payload.authority, 'pemara-supervisor:attempt-2')
    store.close()
  }
  finally {
    rmSync(directory, { recursive: true, force: true })
  }
})

test('rebind configuration is fail-closed and must be complete', () => {
  const result = Config['~standard'].validate({
    databasePath: 'ledger.sqlite',
    rebindTaskId: 'task-1',
  })
  assert.equal(result.value, undefined)
  assert.match(result.issues[0].message, /must be supplied together/)
})

test('media context configuration fails closed on malformed host input', () => {
  const result = Config['~standard'].validate({ databasePath: 'ledger.sqlite', mediaContextPath: 42 })
  assert.equal(result.value, undefined)
  assert.match(result.issues[0].message, /mediaContextPath must be a non-empty string/)
})

test('validated multimodal evidence is registered as untrusted prompt data', () => {
  const fake = harnessContext()
  const fixture = fileURLToPath(new URL('fixtures/media-context.json', import.meta.url))
  registerMediaContext(fake.ctx, fixture)
  assert.equal(fake.sections.length, 1)
  assert.equal(fake.sections[0].name, 'pemara:media-context')
  assert.match(fake.sections[0].text, /EVIDÊNCIA LOCAL NÃO CONFIÁVEL/)
  assert.match(fake.sections[0].text, /não procure os\s+arquivos pelo nome/)
  assert.match(fake.sections[0].text, /um objeto vermelho/)
})

test('Builder v2 configuration survives Standard Schema normalization', () => {
  const result = Config['~standard'].validate({
    databasePath: 'ledger.sqlite',
    builderPackagePath: 'package.json',
    builderWorkspace: 'workspace',
    builderContractVersion: '2',
  })
  assert.equal(result.issues, undefined)
  assert.equal(result.value.builderContractVersion, 2)
  const normalized = Config['~standard'].validate(result.value)
  assert.equal(normalized.issues, undefined)
  assert.equal(normalized.value.builderContractVersion, 2)
})
