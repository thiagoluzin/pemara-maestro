import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const dshRoot = join(dirname(projectRoot), 'third_party', 'deepseek-harness')
const loader = join(dshRoot, 'node_modules', 'tsx', 'dist', 'esm', 'index.mjs')
const fallback = join(projectRoot, 'bin', 'node-os-userinfo-fallback.cjs')
const gate = join(projectRoot, 'test', 'real-dsh-compat.mts')

for (const required of [loader, fallback, gate]) {
  if (!existsSync(required)) throw new Error(`DSH compatibility prerequisite missing: ${required}`)
}

const result = spawnSync(process.execPath, [
  '--require', fallback,
  '--import', pathToFileURL(loader).href,
  gate,
], {
  cwd: projectRoot,
  stdio: 'inherit',
  windowsHide: true,
})

if (result.error) throw result.error
process.exitCode = result.status ?? 1
