import { existsSync, writeFileSync } from 'node:fs'

const marker = process.argv[2]
if (!existsSync(marker)) {
  writeFileSync(marker, `${JSON.stringify({ pid: process.pid, startedAt: Date.now() })}\n`, { flag: 'wx' })
  setInterval(() => {}, 1_000)
}
else {
  process.stdout.write('resumed-from-durable-checkpoint\n')
}
