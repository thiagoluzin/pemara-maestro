import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const launcher = join(projectRoot, 'bin', 'Open-PemaraMonitor.ps1')
const shortcutInstaller = join(projectRoot, 'scripts', 'Install-MonitorShortcut.ps1')

function runPowerShell(args) {
  const shell = join(
    process.env.SystemRoot ?? 'C:\\Windows',
    'System32',
    'WindowsPowerShell',
    'v1.0',
    'powershell.exe',
  )
  return new Promise((resolve, reject) => {
    const child = spawn(shell, [
      '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
      ...args,
    ], { cwd: projectRoot, windowsHide: true })
    let stdout = ''
    let stderr = ''
    child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk })
    child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk })
    child.on('error', reject)
    child.on('close', code => resolve({ code, stdout, stderr }))
  })
}

test('visual monitor launcher is loopback-only and starts its server hidden', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /http:\/\/127\.0\.0\.1:/)
  assert.match(source, /src\\monitor\.mjs/)
  assert.match(source, /-WindowStyle Hidden/)
  assert.match(source, /--app=/)
  assert.match(source, /\/api\/health/)
  assert.match(source, /Start-Process -FilePath \$nodePath/)
  assert.doesNotMatch(source, /0\.0\.0\.0/)
})

test('visual monitor launcher dry-run reports the reusable launch contract', {
  skip: process.platform !== 'win32',
}, async () => {
  const result = await runPowerShell(['-File', launcher, '-Port', '3080', '-DryRun'])

  assert.equal(result.code, 0, result.stderr)
  const report = JSON.parse(result.stdout.trim())
  assert.equal(report.url, 'http://127.0.0.1:3080')
  assert.equal(report.loopbackOnly, true)
  assert.equal(report.readOnly, false)
  assert.equal(report.taskSubmission, true)
  assert.equal(report.singleActiveTask, true)
  assert.equal(report.reusesExistingServer, true)
  assert.equal(report.browserMode, 'edge-app')
})

test('desktop shortcut installer targets the visual launcher and supports dry-run', {
  skip: process.platform !== 'win32',
}, async () => {
  const source = await readFile(shortcutInstaller, 'utf8')
  assert.match(source, /WScript\.Shell/)
  assert.match(source, /Open-PemaraMonitor\.ps1/)
  assert.match(source, /Pemara Harness Visual\.lnk/)

  const result = await runPowerShell(['-File', shortcutInstaller, '-DryRun'])
  assert.equal(result.code, 0, result.stderr)
  const report = JSON.parse(result.stdout.trim())
  assert.match(report.shortcutPath, /Pemara Harness Visual\.lnk$/)
  assert.equal(report.windowStyle, 'hidden')
})
