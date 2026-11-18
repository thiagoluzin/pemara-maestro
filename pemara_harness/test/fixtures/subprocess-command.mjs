import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'

const [mode, markerPath] = process.argv.slice(2)

if (mode === 'success') {
  process.stdout.write('subprocess-ok\n')
  process.stderr.write('diagnostic-ok\n')
}
else if (mode === 'large') {
  process.stdout.write('x'.repeat(16_384))
}
else if (mode === 'sleep-success') {
  setTimeout(() => process.stdout.write('late-success\n'), 500)
}
else if (mode === 'environment') {
  const leaked = Object.keys(process.env)
    .filter(key => /(token|secret|password|credential|api[_-]?key)/iu.test(key))
  process.stdout.write(`${JSON.stringify({ fixture: process.env.PEMARA_FIXTURE, leaked })}\n`)
}
else if (mode === 'hang-tree') {
  const grandchild = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], {
    windowsHide: true,
    stdio: 'ignore',
  })
  writeFileSync(markerPath, `${JSON.stringify({ parentPid: process.pid, childPid: grandchild.pid })}\n`)
  setInterval(() => {}, 1_000)
}
else {
  process.stderr.write(`unknown mode: ${String(mode)}\n`)
  process.exitCode = 7
}
