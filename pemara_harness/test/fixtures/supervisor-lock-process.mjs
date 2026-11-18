import { writeFileSync } from 'node:fs'

import { SupervisorStore } from '../../src/supervisor-store.mjs'

const [databasePath, taskId, owner, readyPath, holdRaw = '0'] = process.argv.slice(2)
const store = new SupervisorStore({ databasePath })
try {
  const lock = store.acquire(taskId, {
    owner,
    leaseMs: 5_000,
    processFingerprint: `fixture:${owner}:${process.pid}`,
  })
  writeFileSync(readyPath, `${JSON.stringify({ pid: process.pid, token: lock.token })}\n`, { flag: 'w' })
  await new Promise(resolveDelay => setTimeout(resolveDelay, Number(holdRaw)))
  store.release(taskId, lock.token)
  process.stdout.write(`${JSON.stringify({ acquired: true, owner })}\n`)
}
catch (error) {
  process.stderr.write(`${JSON.stringify({ code: error?.code, message: error?.message })}\n`)
  process.exitCode = 2
}
finally {
  store.close()
}
