import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const pemaraRoot = dirname(projectRoot)
const launcher = join(projectRoot, 'bin', 'start-pemara-builder-dsh.ps1')
const preflight = join(projectRoot, 'bin', 'pemara-builder-prepare.mjs')
const taskPackage = join(projectRoot, 'evidence', 'packages', 'QB-002.json')
const taskWorkspace = join(pemaraRoot, 'worktrees', 'pemara-harness-qwen', 'QB-002')

function runNode(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { cwd: projectRoot, windowsHide: true })
    let stdout = ''
    let stderr = ''
    child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk })
    child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk })
    child.once('error', reject)
    child.once('close', code => resolve({ code, stdout, stderr }))
  })
}

test('Builder launcher is isolated, read-only, native-tool mode, and has no installer bypass', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /\[Parameter\(Mandatory = \$true\)\]\s*\[string\]\s*\$Workspace/)
  assert.match(source, /\[Parameter\(Mandatory = \$true\)\]\s*\[string\]\s*\$Package/)
  assert.match(source, /pemara-builder-prepare\.mjs/)
  assert.match(source, /\.runtime\\dsh-home-builder/)
  assert.match(source, /\$env:DSH_PERMISSION_MODE = 'read-only'/)
  assert.match(source, /\$env:DSH_TOOLS_MODE = 'native'/)
  assert.match(source, /'pemara-builder-v2'.*'pemara-builder'/)
  assert.match(source, /--profile \$profileName/)
  assert.match(source, /PEMARA_BUILDER_PACKAGE/)
  assert.match(source, /PEMARA_BUILDER_WORKSPACE/)
  assert.match(source, /PEMARA_BUILDER_CONTRACT_VERSION/)
  assert.match(source, /apps\\cli\\src\\bin\.ts/)
  assert.match(source, /node_modules\\tsx\\dist\\esm\\index\.mjs/)
  assert.match(source, /node-os-userinfo-fallback\.cjs/)
  assert.match(source, /node --require \$nodeUserInfoFallback --import/)
  assert.doesNotMatch(source, /pnpm install/)
  assert.doesNotMatch(source, /-Force/)
  assert.doesNotMatch(source, /--patch/)
})

test('Builder preflight admits the closed QB-002 package only in its dedicated worktree', {
  skip: process.platform !== 'win32',
}, async () => {
  const result = await runNode([
    preflight,
    '--package', taskPackage,
    '--workspace', taskWorkspace,
    '--check',
  ])

  assert.equal(result.code, 0, result.stderr)
  const report = JSON.parse(result.stdout)
  assert.equal(report.status, 'ready')
  assert.equal(report.taskId, 'QB-002')
  assert.equal(report.workspace, taskWorkspace)
  assert.equal(report.skills.staged, false)
  assert.deepEqual(report.tools, [
    'harness_task_create',
    'harness_task_get',
    'harness_task_begin_round',
    'harness_task_checkpoint',
    'harness_task_request_completion',
  ])
})

test('Builder preflight refuses the main checkout as a task workspace', {
  skip: process.platform !== 'win32',
}, async () => {
  const result = await runNode([
    preflight,
    '--package', taskPackage,
    '--workspace', projectRoot,
    '--check',
  ])

  assert.notEqual(result.code, 0)
  const report = JSON.parse(result.stderr)
  assert.equal(report.code, 'WORKSPACE_OUTSIDE_BUILDER_ROOT')
})
