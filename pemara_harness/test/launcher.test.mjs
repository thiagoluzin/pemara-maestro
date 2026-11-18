import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync, writeFileSync } from 'node:fs'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const workspaceRoot = dirname(projectRoot)
const engineLauncher = join(projectRoot, 'bin', 'start-pemara-dsh.ps1')
const desktopLauncher = join(projectRoot, 'bin', 'Open-PemaraHarness.ps1')

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
    ], {
      cwd: projectRoot,
      env: { ...process.env, DSH_TELEMETRY_MODE: 'DISABLED' },
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk })
    child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk })
    child.on('error', reject)
    child.on('close', code => resolve({ code, stdout, stderr }))
  })
}

test('engine launcher runs the official DSH source entry from an explicit workspace', async () => {
  const source = await readFile(engineLauncher, 'utf8')

  assert.match(source, /\[CmdletBinding\(PositionalBinding = \$false\)\]/)
  assert.match(source, /\[string\]\s*\$Workspace/)
  assert.match(source, /apps\\cli\\src\\bin\.ts/)
  assert.match(source, /node_modules\\tsx\\dist\\esm\\index\.mjs/)
  assert.match(source, /node-os-userinfo-fallback\.cjs/)
  assert.match(source, /node --require \$nodeUserInfoFallback --import/)
  assert.match(source, /\[System\.Uri\]\s*\$tsxLoaderPath/)
  assert.match(source, /\$previousTsxTsconfigPath = \$env:TSX_TSCONFIG_PATH/)
  assert.match(source, /\$env:TSX_TSCONFIG_PATH = Join-Path \$dshRoot 'tsconfig\.json'/)
  assert.match(source, /Remove-Item Env:TSX_TSCONFIG_PATH/)
  assert.match(source, /Push-Location \$workspaceRoot/)
  assert.doesNotMatch(source, /Push-Location \$dshRoot\s*(?:\r?\n|$)/)
  assert.doesNotMatch(source, /corepack pnpm dsh/)
  assert.match(source, /PEMARA_MEDIA_CONTEXT_PATH/)
  assert.match(source, /PEMARA_TASK_FILE/)
  assert.match(source, /Remove-Item Env:PEMARA_TASK_FILE/)
  assert.match(source, /MediaContextPath precisa ficar no runtime isolado/)
})

test('desktop launcher auto-starts the exact local model without forcing GPU eviction', async () => {
  const source = await readFile(desktopLauncher, 'utf8')

  assert.match(source, /http:\/\/127\.0\.0\.1:11436\/v1\/models/)
  assert.match(source, /qwen3\.8-27b-uncensored-yarn-524k/)
  assert.match(source, /Start-Qwen38-Yarn524K\.ps1/)
  assert.match(source, /Start-Process -FilePath \$powerShell/)
  assert.match(source, /-WindowStyle Hidden/)
  assert.match(source, /Get-QwenAdmission/)
  assert.match(source, /queue_running/)
  assert.match(source, /Invoke-RestMethod -Uri \$ComfyFreeEndpoint -Method Post/)
  assert.match(source, /unload_models = \$true/)
  assert.match(source, /free_memory = \$true/)
  assert.match(source, /-Workspace/)
  assert.doesNotMatch(source, /Start-Qwen38-Yarn524K\.ps1[^\r\n]*-Force/)
  assert.match(source, /prepare-media-context\.mjs/)
  assert.match(source, /process-media-attachment\.py/)
  assert.match(source, /AttachmentsManifest exige TaskFile/)
})

test('desktop launcher dry-run reports the resolved execution contract without starting a task', {
  skip: process.platform !== 'win32',
}, async () => {
  const task = 'auditoria seca do launcher Pemara'
  const result = await runPowerShell([
    '-File', desktopLauncher,
    '-Workspace', workspaceRoot,
    '-Task', task,
    '-DryRun',
  ])

  assert.equal(result.code, 0, result.stderr)
  const report = JSON.parse(result.stdout.trim())
  assert.equal(report.workspace, workspaceRoot)
  assert.equal(report.task, task)
  assert.equal(report.profile, 'pemara')
  assert.equal(report.qwen.endpoint, 'http://127.0.0.1:11436/v1/models')
  assert.equal(report.qwen.expectedModel, 'qwen3.8-27b-uncensored-yarn-524k')
  assert.equal(report.safety.autoStartsModel, true)
  assert.equal(report.safety.startsInSeparatePowerShell, true)
  assert.equal(report.safety.forceGpuEviction, false)
  assert.equal(report.safety.minimumFreeGpuMiB, 12000)
  assert.equal(report.safety.waitsForComfyQueue, true)
  assert.equal(report.safety.releasesIdleComfyCache, true)
  assert.equal(report.safety.idleGpuSampleCount, 5)
  assert.equal(report.safety.maximumIdleGpuUtilizationPercent, 5)
})

test('desktop launcher starts an offline Qwen child and waits for the expected model', {
  skip: process.platform !== 'win32',
}, async () => {
  const runtimeRoot = join(projectRoot, '.runtime')
  await mkdir(runtimeRoot, { recursive: true })
  const temporaryRoot = await mkdtemp(join(runtimeRoot, 'launcher-autostart-'))
  const markerPath = join(temporaryRoot, 'qwen-started.txt')
  const fakeLauncher = join(temporaryRoot, 'Start-FakeQwen.ps1')
  const escapedMarkerPath = markerPath.replaceAll("'", "''")
  await writeFile(fakeLauncher, [
    '[CmdletBinding()]',
    'param()',
    `Set-Content -LiteralPath '${escapedMarkerPath}' -Value 'started' -Encoding ASCII`,
    '',
  ].join('\r\n'), 'utf8')

  const expectedModel = 'qwen3.8-test-model'
  const server = createServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    if (request.url === '/queue') {
      response.statusCode = 200
      response.end(JSON.stringify({ queue_running: [], queue_pending: [] }))
      return
    }
    if (request.url === '/v1/models' && existsSync(markerPath)) {
      response.statusCode = 200
      response.end(JSON.stringify({ data: [{ id: expectedModel }] }))
      return
    }
    response.statusCode = 503
    response.end(JSON.stringify({ error: 'model offline' }))
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  assert.ok(address && typeof address === 'object')

  try {
    const result = await runPowerShell([
      '-File', desktopLauncher,
      '-Workspace', workspaceRoot,
      '-Task', ':sair',
      '-Once',
      '-QwenLauncher', fakeLauncher,
      '-QwenEndpoint', `http://127.0.0.1:${address.port}/v1/models`,
      '-ExpectedModel', expectedModel,
      '-ComfyQueueEndpoint', `http://127.0.0.1:${address.port}/queue`,
      '-MinimumFreeGpuMiB', '0',
      '-QwenStartupTimeoutSec', '15',
      '-RetryIntervalSec', '1',
    ])

    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.equal(existsSync(markerPath), true)
    assert.match(result.stdout, /Iniciando Qwen automaticamente/)
    assert.match(result.stdout, /Qwen pronto/)
  }
  finally {
    await new Promise(resolve => server.close(resolve))
    await rm(temporaryRoot, { recursive: true, force: true })
  }
})

test('desktop launcher keeps waiting after the starter exits while the model is still loading', {
  skip: process.platform !== 'win32',
}, async () => {
  const runtimeRoot = join(projectRoot, '.runtime')
  await mkdir(runtimeRoot, { recursive: true })
  const temporaryRoot = await mkdtemp(join(runtimeRoot, 'launcher-loading-model-'))
  const markerPath = join(temporaryRoot, 'starter-finished.txt')
  const fakeLauncher = join(temporaryRoot, 'Start-FakeQwen.ps1')
  const escapedMarkerPath = markerPath.replaceAll("'", "''")
  await writeFile(fakeLauncher, [
    '[CmdletBinding()]',
    'param()',
    `Set-Content -LiteralPath '${escapedMarkerPath}' -Value 'starter-exited-zero' -Encoding ASCII`,
    'exit 0',
    '',
  ].join('\r\n'), 'utf8')

  const expectedModel = 'qwen3.8-delayed-ready-test-model'
  let firstLoadingResponseAt = null
  const server = createServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    if (request.url === '/queue') {
      response.statusCode = 200
      response.end(JSON.stringify({ queue_running: [], queue_pending: [] }))
      return
    }
    if (request.url === '/v1/models' && existsSync(markerPath)) {
      firstLoadingResponseAt ??= Date.now()
      if (Date.now() - firstLoadingResponseAt >= 1500) {
        response.statusCode = 200
        response.end(JSON.stringify({ data: [{ id: expectedModel }] }))
        return
      }
    }
    response.statusCode = 503
    response.end(JSON.stringify({ error: 'Loading model' }))
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  assert.ok(address && typeof address === 'object')

  try {
    const result = await runPowerShell([
      '-File', desktopLauncher,
      '-Workspace', workspaceRoot,
      '-Task', ':sair',
      '-Once',
      '-QwenLauncher', fakeLauncher,
      '-QwenEndpoint', `http://127.0.0.1:${address.port}/v1/models`,
      '-ExpectedModel', expectedModel,
      '-ComfyQueueEndpoint', `http://127.0.0.1:${address.port}/queue`,
      '-MinimumFreeGpuMiB', '0',
      '-QwenStartupTimeoutSec', '15',
      '-RetryIntervalSec', '1',
    ])

    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.equal(existsSync(markerPath), true)
    assert.match(result.stdout, /Qwen pronto/)
  }
  finally {
    await new Promise(resolve => server.close(resolve))
    await rm(temporaryRoot, { recursive: true, force: true })
  }
})

test('desktop launcher accepts a model that becomes ready after its starter exits non-zero', {
  skip: process.platform !== 'win32',
}, async () => {
  const runtimeRoot = join(projectRoot, '.runtime')
  await mkdir(runtimeRoot, { recursive: true })
  const temporaryRoot = await mkdtemp(join(runtimeRoot, 'launcher-nonzero-starter-'))
  const markerPath = join(temporaryRoot, 'starter-finished.txt')
  const fakeLauncher = join(temporaryRoot, 'Start-FakeQwen.ps1')
  const escapedMarkerPath = markerPath.replaceAll("'", "''")
  await writeFile(fakeLauncher, [
    '[CmdletBinding()]',
    'param()',
    `Set-Content -LiteralPath '${escapedMarkerPath}' -Value 'starter-exited-nonzero' -Encoding ASCII`,
    'exit 1',
    '',
  ].join('\r\n'), 'utf8')

  const expectedModel = 'qwen3.8-nonzero-starter-test-model'
  let firstLoadingResponseAt = null
  const server = createServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    if (request.url === '/queue') {
      response.statusCode = 200
      response.end(JSON.stringify({ queue_running: [], queue_pending: [] }))
      return
    }
    if (request.url === '/v1/models' && existsSync(markerPath)) {
      firstLoadingResponseAt ??= Date.now()
      if (Date.now() - firstLoadingResponseAt >= 6_000) {
        response.statusCode = 200
        response.end(JSON.stringify({ data: [{ id: expectedModel }] }))
        return
      }
    }
    response.statusCode = 503
    response.end(JSON.stringify({ error: 'Loading model' }))
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  assert.ok(address && typeof address === 'object')

  try {
    const result = await runPowerShell([
      '-File', desktopLauncher,
      '-Workspace', workspaceRoot,
      '-Task', ':sair',
      '-Once',
      '-QwenLauncher', fakeLauncher,
      '-QwenEndpoint', `http://127.0.0.1:${address.port}/v1/models`,
      '-ExpectedModel', expectedModel,
      '-ComfyQueueEndpoint', `http://127.0.0.1:${address.port}/queue`,
      '-MinimumFreeGpuMiB', '0',
      '-QwenStartupTimeoutSec', '15',
      '-RetryIntervalSec', '1',
    ])

    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.equal(existsSync(markerPath), true)
    assert.match(result.stdout, /Qwen pronto/)
  }
  finally {
    await new Promise(resolve => server.close(resolve))
    await rm(temporaryRoot, { recursive: true, force: true })
  }
})

test('desktop launcher refuses to start Qwen while ComfyUI has running work', {
  skip: process.platform !== 'win32',
}, async () => {
  const runtimeRoot = join(projectRoot, '.runtime')
  await mkdir(runtimeRoot, { recursive: true })
  const temporaryRoot = await mkdtemp(join(runtimeRoot, 'launcher-busy-'))
  const markerPath = join(temporaryRoot, 'must-not-start.txt')
  const fakeLauncher = join(temporaryRoot, 'Start-FakeQwen.ps1')
  const escapedMarkerPath = markerPath.replaceAll("'", "''")
  await writeFile(fakeLauncher, [
    '[CmdletBinding()]',
    'param()',
    `Set-Content -LiteralPath '${escapedMarkerPath}' -Value 'started' -Encoding ASCII`,
    '',
  ].join('\r\n'), 'utf8')

  const server = createServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    if (request.url === '/queue') {
      response.statusCode = 200
      response.end(JSON.stringify({ queue_running: [['active-job']], queue_pending: [] }))
      return
    }
    response.statusCode = 503
    response.end(JSON.stringify({ error: 'model offline' }))
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  assert.ok(address && typeof address === 'object')

  try {
    const result = await runPowerShell([
      '-File', desktopLauncher,
      '-Workspace', workspaceRoot,
      '-Task', ':sair',
      '-Once',
      '-QwenLauncher', fakeLauncher,
      '-QwenEndpoint', `http://127.0.0.1:${address.port}/v1/models`,
      '-ExpectedModel', 'qwen3.8-test-model',
      '-ComfyQueueEndpoint', `http://127.0.0.1:${address.port}/queue`,
      '-MinimumFreeGpuMiB', '0',
      '-QwenStartupTimeoutSec', '15',
      '-RetryIntervalSec', '1',
    ])

    assert.equal(result.code, 3, `${result.stderr}\n${result.stdout}`)
    assert.equal(existsSync(markerPath), false)
    assert.match(result.stdout, /ComfyUI tem 1 trabalho/)
  }
  finally {
    await new Promise(resolve => server.close(resolve))
    await rm(temporaryRoot, { recursive: true, force: true })
  }
})

test('desktop launcher unloads only idle ComfyUI cache before starting Qwen', {
  skip: process.platform !== 'win32',
}, async () => {
  const runtimeRoot = join(projectRoot, '.runtime')
  await mkdir(runtimeRoot, { recursive: true })
  const temporaryRoot = await mkdtemp(join(runtimeRoot, 'launcher-idle-cache-'))
  const cacheReleasedMarker = join(temporaryRoot, 'comfy-cache-released.txt')
  const qwenStartedMarker = join(temporaryRoot, 'qwen-started.txt')
  const fakeQwenLauncher = join(temporaryRoot, 'Start-FakeQwen.ps1')
  const fakeNvidiaSmi = join(temporaryRoot, 'nvidia-smi.cmd')
  const escapedQwenMarker = qwenStartedMarker.replaceAll("'", "''")
  await writeFile(fakeQwenLauncher, [
    '[CmdletBinding()]',
    'param()',
    `Set-Content -LiteralPath '${escapedQwenMarker}' -Value 'started' -Encoding ASCII`,
    '',
  ].join('\r\n'), 'utf8')
  await writeFile(fakeNvidiaSmi, [
    '@echo off',
    `if exist "${cacheReleasedMarker}" (`,
    '  echo 20000, 0',
    ') else (',
    '  echo 1000, 0',
    ')',
    'exit /b 0',
    '',
  ].join('\r\n'), 'utf8')

  const expectedModel = 'qwen3.8-idle-cache-test-model'
  const server = createServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    if (request.url === '/queue') {
      response.statusCode = 200
      response.end(JSON.stringify({ queue_running: [], queue_pending: [] }))
      return
    }
    if (request.url === '/free' && request.method === 'POST') {
      writeFileSync(cacheReleasedMarker, 'released', 'utf8')
      response.statusCode = 200
      response.end('{}')
      return
    }
    if (request.url === '/v1/models' && existsSync(qwenStartedMarker)) {
      response.statusCode = 200
      response.end(JSON.stringify({ data: [{ id: expectedModel }] }))
      return
    }
    response.statusCode = 503
    response.end(JSON.stringify({ error: 'model offline' }))
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  assert.ok(address && typeof address === 'object')

  try {
    const result = await runPowerShell([
      '-File', desktopLauncher,
      '-Workspace', workspaceRoot,
      '-Task', ':sair',
      '-Once',
      '-QwenLauncher', fakeQwenLauncher,
      '-QwenEndpoint', `http://127.0.0.1:${address.port}/v1/models`,
      '-ExpectedModel', expectedModel,
      '-ComfyQueueEndpoint', `http://127.0.0.1:${address.port}/queue`,
      '-ComfyFreeEndpoint', `http://127.0.0.1:${address.port}/free`,
      '-NvidiaSmiPath', fakeNvidiaSmi,
      '-MinimumFreeGpuMiB', '12000',
      '-IdleGpuSampleCount', '1',
      '-IdleGpuSampleIntervalSec', '1',
      '-ComfyReleaseTimeoutSec', '10',
      '-QwenStartupTimeoutSec', '15',
      '-RetryIntervalSec', '1',
    ])

    assert.equal(result.code, 0, `${result.stderr}\n${result.stdout}`)
    assert.equal(existsSync(cacheReleasedMarker), true)
    assert.equal(existsSync(qwenStartedMarker), true)
    assert.match(result.stdout, /Liberando somente o cache ocioso do ComfyUI/)
    assert.match(result.stdout, /Qwen pronto/)
  }
  finally {
    await new Promise(resolve => server.close(resolve))
    await rm(temporaryRoot, { recursive: true, force: true })
  }
})
