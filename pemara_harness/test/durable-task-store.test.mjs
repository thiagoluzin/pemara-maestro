import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import {
  DurableTaskStore,
  HarnessStateError,
  TASK_STATUS,
} from '../src/index.mjs'

function fixture() {
  const directory = mkdtempSync(join(tmpdir(), 'pemara-harness-'))
  const databasePath = join(directory, 'harness.sqlite')
  let now = 1_800_000_000_000
  const open = () => new DurableTaskStore({ databasePath, clock: () => now })
  return {
    databasePath,
    open,
    advance(milliseconds) { now += milliseconds },
    cleanup() { rmSync(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 }) },
  }
}

function expectCode(code) {
  return error => error instanceof HarnessStateError && error.code === code
}

test('persists a task and its append-only events across a process-style reopen', () => {
  const fx = fixture()
  try {
    let store = fx.open()
    const created = store.createTask({
      id: 'task-persist',
      objective: 'Construir um harness duravel',
      maxRounds: 12,
      sessionId: 'session-1',
    })
    assert.equal(created.status, TASK_STATUS.ACTIVE)
    assert.equal(created.version, 1)
    store.close()

    store = fx.open()
    const loaded = store.getTask('task-persist')
    assert.equal(loaded.objective, 'Construir um harness duravel')
    assert.equal(loaded.maxRounds, 12)
    assert.equal(loaded.sessionId, 'session-1')
    assert.deepEqual(store.listEvents('task-persist').map(event => event.seq), [1])
    assert.equal(store.listEvents('task-persist')[0].type, 'task.created')
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('uses durable leases to prevent two workers and recovers an expired owner', () => {
  const fx = fixture()
  try {
    let store = fx.open()
    store.createTask({ id: 'task-lease', objective: 'Retomar sem duplicar' })
    const first = store.claimTask('task-lease', { owner: 'worker-a', leaseMs: 1_000 })
    assert.equal(first.owner, 'worker-a')
    assert.throws(
      () => store.claimTask('task-lease', { owner: 'worker-b', leaseMs: 1_000 }),
      expectCode('LEASE_HELD'),
    )
    store.close()

    fx.advance(1_001)
    store = fx.open()
    const report = store.recover()
    assert.deepEqual(report.releasedLeases, ['task-lease'])
    const second = store.claimTask('task-lease', { owner: 'worker-b', leaseMs: 2_000 })
    assert.equal(second.owner, 'worker-b')
    assert.notEqual(second.token, first.token)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('releases a lease explicitly during graceful worker shutdown', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'task-release', objective: 'Encerrar sem deixar trava' })
    const first = store.claimTask('task-release', { owner: 'worker-a', leaseMs: 60_000 })
    const released = store.releaseLease('task-release', first.token)
    assert.equal(released.lease, undefined)
    const second = store.claimTask('task-release', { owner: 'worker-b', leaseMs: 1_000 })
    assert.equal(second.owner, 'worker-b')
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('checkpoints progress and enforces a durable round budget', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'task-rounds', objective: 'Trabalhar com limite', maxRounds: 1 })
    const lease = store.claimTask('task-rounds', { owner: 'worker-a', leaseMs: 5_000 })

    const round = store.startRound('task-rounds', lease.token, {
      provider: 'local',
      model: 'deepseek',
      promptHash: 'sha256:abc',
    })
    assert.equal(round.round, 1)

    const checkpoint = store.checkpoint('task-rounds', lease.token, {
      summary: 'Arquitetura identificada e testes definidos.',
      nextAction: 'Implementar o adaptador DSH.',
      artifacts: ['docs/ARCHITECTURE.md'],
    })
    assert.equal(checkpoint.roundsStarted, 1)
    assert.equal(checkpoint.checkpoint.nextAction, 'Implementar o adaptador DSH.')

    assert.throws(
      () => store.startRound('task-rounds', lease.token, { provider: 'local', model: 'deepseek' }),
      expectCode('ROUND_LIMIT'),
    )
    assert.equal(store.getTask('task-rounds').status, TASK_STATUS.FAILED_EXHAUSTED)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('requires a fresh checkpoint before a side effect and never blindly repeats an uncertain effect', () => {
  const fx = fixture()
  try {
    let store = fx.open()
    store.createTask({ id: 'task-effect', objective: 'Executar efeitos com seguranca' })
    const lease = store.claimTask('task-effect', { owner: 'worker-a', leaseMs: 5_000 })

    assert.throws(
      () => store.prepareEffect('task-effect', lease.token, {
        key: 'publish:artifact-1',
        kind: 'publish',
        request: { artifact: 'artifact-1' },
      }),
      expectCode('CHECKPOINT_REQUIRED'),
    )

    store.checkpoint('task-effect', lease.token, {
      summary: 'Artefato pronto; publicacao ainda nao iniciada.',
      nextAction: 'Publicar artifact-1 usando a mesma chave.',
      artifacts: ['artifact-1'],
    })
    const prepared = store.prepareEffect('task-effect', lease.token, {
      key: 'publish:artifact-1',
      kind: 'publish',
      request: { artifact: 'artifact-1' },
    })
    store.markEffectStarted('task-effect', lease.token, prepared.id)
    store.close() // simula queda depois do inicio e antes de gravar o resultado

    fx.advance(5_001)
    store = fx.open()
    const report = store.recover()
    assert.deepEqual(report.uncertainEffects, [prepared.id])
    assert.equal(store.getEffect(prepared.id).status, 'OUTCOME_UNKNOWN')
    assert.equal(store.getTask('task-effect').status, TASK_STATUS.BLOCKED_HUMAN)
    assert.throws(
      () => store.resumeTask('task-effect', {
        resolver: 'owner', reason: 'Tentar retomar sem reconciliar.', evidence: ['checagem incompleta'],
      }),
      expectCode('EFFECT_RECONCILIATION_REQUIRED'),
    )

    const resolved = store.resolveEffect(prepared.id, {
      resolver: 'owner',
      outcome: 'committed',
      evidence: ['sistema remoto confirmou operation_id=42'],
      result: { operationId: 42 },
    })
    assert.equal(resolved.effect.status, 'COMMITTED')
    assert.equal(resolved.task.status, TASK_STATUS.ACTIVE)
    const resumedLease = store.claimTask('task-effect', { owner: 'worker-b', leaseMs: 5_000 })
    assert.equal(resumedLease.owner, 'worker-b')

    const events = store.listEvents('task-effect')
    assert.deepEqual(events.map(event => event.seq), events.map((_, index) => index + 1))
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('allows the host to resume a human-blocked task after a rejected completion gate', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'task-rejected', objective: 'Corrigir ate o gate passar' })
    const lease = store.claimTask('task-rejected', { owner: 'worker-a', leaseMs: 5_000 })
    store.checkpoint('task-rejected', lease.token, {
      summary: 'Primeira tentativa.', nextAction: 'Submeter ao gate.', artifacts: ['candidate-1'],
    })
    store.requestCompletion('task-rejected', lease.token, {
      summary: 'Candidato pronto.', evidence: ['candidate-1'],
    })
    store.verifyCompletion('task-rejected', {
      verifier: 'owner-gate', outcome: 'fail', evidence: ['teste funcional falhou'],
    })
    assert.equal(store.getTask('task-rejected').status, TASK_STATUS.BLOCKED_HUMAN)

    const resumed = store.resumeTask('task-rejected', {
      resolver: 'owner',
      reason: 'Nova tentativa autorizada depois da rejeicao.',
      evidence: ['rejeicao registrada no gate'],
    })
    assert.equal(resumed.status, TASK_STATUS.ACTIVE)
    assert.equal(store.listEvents('task-rejected').at(-1).type, 'task.resumed')
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('deduplicates committed effects by task-local idempotency key', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'task-idempotent', objective: 'Nao publicar duas vezes' })
    const lease = store.claimTask('task-idempotent', { owner: 'worker-a', leaseMs: 5_000 })
    store.checkpoint('task-idempotent', lease.token, {
      summary: 'Pronto para a escrita.',
      nextAction: 'Gravar uma vez.',
    })
    const first = store.prepareEffect('task-idempotent', lease.token, {
      key: 'write:manifest',
      kind: 'filesystem-write',
      request: { path: 'manifest.json' },
    })
    store.markEffectStarted('task-idempotent', lease.token, first.id)
    store.commitEffect('task-idempotent', lease.token, first.id, { sha256: 'abc' })

    const second = store.prepareEffect('task-idempotent', lease.token, {
      key: 'write:manifest',
      kind: 'filesystem-write',
      request: { path: 'manifest.json' },
    })
    assert.equal(second.id, first.id)
    assert.equal(second.status, 'COMMITTED')
    assert.equal(store.listEffects('task-idempotent').length, 1)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('separates claimed completion from independent verification', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'task-verify', objective: 'Terminar somente com prova' })
    const lease = store.claimTask('task-verify', { owner: 'worker-a', leaseMs: 5_000 })
    store.checkpoint('task-verify', lease.token, {
      summary: 'Implementacao e testes concluidos.',
      nextAction: 'Executar gate independente.',
      artifacts: ['report.json'],
    })
    const pending = store.requestCompletion('task-verify', lease.token, {
      summary: 'Todos os criterios implementados.',
      evidence: ['report.json'],
    })
    assert.equal(pending.status, TASK_STATUS.COMPLETED_PENDING_VERIFY)
    assert.throws(
      () => store.verifyCompletion('task-verify', { verifier: 'gate-1', outcome: 'pass', evidence: [] }),
      expectCode('EVIDENCE_REQUIRED'),
    )

    const verified = store.verifyCompletion('task-verify', {
      verifier: 'gate-1',
      outcome: 'pass',
      evidence: ['node --test: 6 passed'],
    })
    assert.equal(verified.status, TASK_STATUS.COMPLETED_VERIFIED)
    assert.throws(
      () => store.claimTask('task-verify', { owner: 'worker-b', leaseMs: 1_000 }),
      expectCode('TASK_NOT_CLAIMABLE'),
    )
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('host-only session rebind keeps the task id and records an auditable boundary', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'rebind-task', objective: 'Sobreviver a uma nova sessão', sessionId: 'session-a' })
    const rebound = store.rebindTaskSession('rebind-task', {
      fromSessionId: 'session-a',
      toSessionId: 'session-b',
      authority: 'pemara-supervisor:attempt-2',
      evidence: ['checkpoint reidratado', 'nenhum efeito incerto'],
    })
    assert.equal(rebound.id, 'rebind-task')
    assert.equal(rebound.sessionId, 'session-b')
    const event = store.listEvents('rebind-task').at(-1)
    assert.equal(event.type, 'task.session_rebound')
    assert.deepEqual(event.payload, {
      fromSessionId: 'session-a',
      toSessionId: 'session-b',
      authority: 'pemara-supervisor:attempt-2',
      evidence: ['checkpoint reidratado', 'nenhum efeito incerto'],
    })
    assert.equal(store.rebindTaskSession('rebind-task', {
      toSessionId: 'session-b',
      authority: 'pemara-supervisor:attempt-2',
      evidence: ['idempotent'],
    }).version, rebound.version)
    store.close()
  }
  finally {
    fx.cleanup()
  }
})

test('session rebind refuses a live lease or any unfinished external effect', () => {
  const fx = fixture()
  try {
    const store = fx.open()
    store.createTask({ id: 'guarded-rebind', objective: 'Não duplicar efeito', sessionId: 'session-a' })
    const lease = store.claimTask('guarded-rebind', { owner: 'worker-a', leaseMs: 5_000 })
    assert.throws(
      () => store.rebindTaskSession('guarded-rebind', {
        toSessionId: 'session-b', authority: 'supervisor', evidence: ['tentativa'],
      }),
      error => error?.code === 'LEASE_HELD',
    )
    store.checkpoint('guarded-rebind', lease.token, { summary: 'antes do efeito', nextAction: 'efeito' })
    const effect = store.prepareEffect('guarded-rebind', lease.token, {
      key: 'external', kind: 'fixture', request: { value: 1 },
    })
    store.markEffectStarted('guarded-rebind', lease.token, effect.id)
    store.releaseLease('guarded-rebind', lease.token)
    assert.throws(
      () => store.rebindTaskSession('guarded-rebind', {
        toSessionId: 'session-b', authority: 'supervisor', evidence: ['tentativa'],
      }),
      error => error?.code === 'EFFECT_RECONCILIATION_REQUIRED',
    )
    assert.equal(store.getTask('guarded-rebind').sessionId, 'session-a')
    store.close()
  }
  finally {
    fx.cleanup()
  }
})
