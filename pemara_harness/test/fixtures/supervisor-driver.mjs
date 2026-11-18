import { runSupervisor } from '../../src/supervisor.mjs'

const [databasePath, taskId] = process.argv.slice(2)
const result = await runSupervisor({
  databasePath,
  taskId,
  leaseMs: 800,
  heartbeatMs: 100,
})
process.stdout.write(`${JSON.stringify(result)}\n`)
process.exitCode = result.status === 'COMPLETED' ? 0 : 1
