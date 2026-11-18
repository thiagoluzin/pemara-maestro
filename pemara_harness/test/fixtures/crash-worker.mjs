import { DurableTaskStore } from '../../src/index.mjs'

const databasePath = process.argv[2]
const store = new DurableTaskStore({ databasePath })
store.createTask({ id: 'crash-task', objective: 'Sobreviver a morte do worker' })
const lease = store.claimTask('crash-task', { owner: 'doomed-worker', leaseMs: 60_000 })
store.checkpoint('crash-task', lease.token, {
  summary: 'Efeito preparado antes da queda.',
  nextAction: 'Executar e reconciliar o resultado.',
})
const effect = store.prepareEffect('crash-task', lease.token, {
  key: 'external:crash-test',
  kind: 'external-test',
  request: { value: 1 },
})
store.markEffectStarted('crash-task', lease.token, effect.id)

// Intencional: não chama close() nem grava resultado.
process.exit(23)
