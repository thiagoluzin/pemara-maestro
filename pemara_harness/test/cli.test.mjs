import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

import { DurableTaskStore, TASK_STATUS } from '../src/index.mjs'

const cli = fileURLToPath(new URL('../bin/pemara-harness.mjs', import.meta.url))

function fixture() {
  const directory = mkdtempSync(join(tmpdir(), 'pemara-cli-'))
  const databasePath = join(directory, 'harness.sqlite')
  function run(...args) {
    return spawnSync(process.execPath, [cli, '--db', databasePath, ...args], {
      encoding: 'utf8',
      windowsHide: true,
    })
  }
  return { directory, databasePath, run }
}

test('CLI creates, inspects, recovers, and independently verifies a durable task', () => {
  const fx = fixture()
  try {
    const created = fx.run(
      'create', '--id', 'cli-task', '--objective', 'Gate independente', '--max-rounds', '3',
    )
    assert.equal(created.status, 0, created.stderr)
    assert.equal(JSON.parse(created.stdout).task.id, 'cli-task')

    const status = fx.run('status', '--id', 'cli-task')
    assert.equal(status.status, 0, status.stderr)
    assert.equal(JSON.parse(status.stdout).task.status, TASK_STATUS.ACTIVE)

    const store = new DurableTaskStore({ databasePath: fx.databasePath })
    const lease = store.claimTask('cli-task', { owner: 'test-worker', leaseMs: 5_000 })
    store.checkpoint('cli-task', lease.token, {
      summary: 'Gate pronto.', nextAction: 'Verificar.', artifacts: ['report.json'],
    })
    store.requestCompletion('cli-task', lease.token, {
      summary: 'Criterios satisfeitos.', evidence: ['report.json'],
    })
    store.close()

    const verified = fx.run(
      'verify', '--id', 'cli-task', '--verifier', 'owner-gate', '--evidence', 'node --test passou',
    )
    assert.equal(verified.status, 0, verified.stderr)
    assert.equal(JSON.parse(verified.stdout).task.status, TASK_STATUS.COMPLETED_VERIFIED)

    const events = fx.run('events', '--id', 'cli-task')
    assert.equal(events.status, 0, events.stderr)
    const parsedEvents = JSON.parse(events.stdout).events
    assert.equal(parsedEvents.at(-1).type, 'completion.verified')
    assert.deepEqual(parsedEvents.map(event => event.seq), parsedEvents.map((_, index) => index + 1))

    const recovery = fx.run('recover')
    assert.equal(recovery.status, 0, recovery.stderr)
    assert.deepEqual(JSON.parse(recovery.stdout).uncertainEffects, [])
  }
  finally {
    rmSync(fx.directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})

test('CLI rejects an unknown command with structured failure output', () => {
  const fx = fixture()
  try {
    const result = fx.run('explode')
    assert.notEqual(result.status, 0)
    assert.equal(JSON.parse(result.stderr).error.code, 'CLI_USAGE')
  }
  finally {
    rmSync(fx.directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})

test('CLI reconciles an uncertain effect and resumes a rejected task without model authority', () => {
  const fx = fixture()
  try {
    let store = new DurableTaskStore({ databasePath: fx.databasePath })
    store.createTask({ id: 'cli-reconcile', objective: 'Reconciliar e continuar' })
    let lease = store.claimTask('cli-reconcile', { owner: 'worker-a', leaseMs: 60_000 })
    store.checkpoint('cli-reconcile', lease.token, {
      summary: 'Antes do efeito.', nextAction: 'Executar.', artifacts: ['candidate'],
    })
    const effect = store.prepareEffect('cli-reconcile', lease.token, {
      key: 'publish:candidate', kind: 'publish', request: { candidate: 1 },
    })
    store.markEffectStarted('cli-reconcile', lease.token, effect.id)
    store.close()

    const recovered = fx.run('recover')
    assert.equal(recovered.status, 0, recovered.stderr)
    assert.deepEqual(JSON.parse(recovered.stdout).uncertainEffects, [effect.id])

    const resolved = fx.run(
      'resolve-effect', '--effect-id', effect.id, '--resolver', 'owner', '--outcome', 'committed',
      '--evidence', 'remote operation 42 exists', '--result-json', '{"operationId":42}',
    )
    assert.equal(resolved.status, 0, resolved.stderr)
    assert.equal(JSON.parse(resolved.stdout).task.status, TASK_STATUS.ACTIVE)

    store = new DurableTaskStore({ databasePath: fx.databasePath })
    lease = store.claimTask('cli-reconcile', { owner: 'worker-b', leaseMs: 5_000 })
    store.checkpoint('cli-reconcile', lease.token, {
      summary: 'Efeito reconciliado.', nextAction: 'Submeter conclusao.', artifacts: ['operation-42'],
    })
    store.requestCompletion('cli-reconcile', lease.token, {
      summary: 'Primeira conclusao.', evidence: ['operation-42'],
    })
    store.verifyCompletion('cli-reconcile', {
      verifier: 'owner-gate', outcome: 'fail', evidence: ['falta teste de aceitacao'],
    })
    store.close()

    const resumed = fx.run(
      'resume', '--id', 'cli-reconcile', '--resolver', 'owner',
      '--reason', 'Executar o teste de aceitacao faltante.', '--evidence', 'gate rejection recorded',
    )
    assert.equal(resumed.status, 0, resumed.stderr)
    assert.equal(JSON.parse(resumed.stdout).task.status, TASK_STATUS.ACTIVE)
  }
  finally {
    rmSync(fx.directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})
