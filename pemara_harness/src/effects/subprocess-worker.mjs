import { randomUUID } from 'node:crypto'
import { spawn, spawnSync } from 'node:child_process'
import { readFile, rename, writeFile } from 'node:fs/promises'
import { isAbsolute, join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const TERMINAL = new Set(['succeeded', 'failed', 'timed_out', 'cancelled', 'spawn_failed'])

async function writeState(path, value) {
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  await rename(temporary, path)
}

function appendLimited(state, chunk) {
  const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk))
  const remaining = state.limit - state.bytes
  if (remaining <= 0) {
    state.truncated = true
    return
  }
  const accepted = buffer.subarray(0, remaining)
  state.chunks.push(accepted)
  state.bytes += accepted.length
  if (accepted.length < buffer.length) state.truncated = true
}

function text(state) {
  return Buffer.concat(state.chunks, state.bytes).toString('utf8')
}

function terminateTree(child, environment = process.env) {
  if (!Number.isSafeInteger(child?.pid) || child.pid <= 0) return
  if (process.platform === 'win32') {
    const windowsRoot = environment.SystemRoot || environment.WINDIR || 'C:\\Windows'
    const taskkill = join(windowsRoot, 'System32', 'taskkill.exe')
    const result = spawnSync(taskkill, ['/PID', String(child.pid), '/T', '/F'], {
      windowsHide: true,
      shell: false,
      stdio: 'ignore',
    })
    if (result.status !== 0) {
      try { child.kill('SIGKILL') } catch {}
    }
    return
  }
  try { process.kill(-child.pid, 'SIGTERM') } catch {
    try { child.kill('SIGTERM') } catch {}
  }
  const force = setTimeout(() => {
    try { process.kill(-child.pid, 'SIGKILL') } catch {
      try { child.kill('SIGKILL') } catch {}
    }
  }, 1_000)
  force.unref?.()
}

function validate(config) {
  if (config?.version !== 1) throw new Error('unsupported subprocess worker config')
  for (const key of ['effectId', 'commandFingerprint', 'executable', 'cwd', 'statePath']) {
    if (typeof config[key] !== 'string' || config[key].trim() === '') throw new Error(`invalid ${key}`)
  }
  if (!isAbsolute(config.executable) || !isAbsolute(config.cwd) || !isAbsolute(config.statePath)) {
    throw new Error('worker paths must be absolute')
  }
  if (!Array.isArray(config.args) || config.args.some(argument => typeof argument !== 'string')) {
    throw new Error('invalid args')
  }
  if (!Number.isSafeInteger(config.timeoutMs) || config.timeoutMs <= 0) throw new Error('invalid timeoutMs')
  if (!Number.isSafeInteger(config.maxOutputBytes) || config.maxOutputBytes <= 0) throw new Error('invalid maxOutputBytes')
  if (config.env === null || typeof config.env !== 'object' || Array.isArray(config.env)
    || Object.entries(config.env).some(([key, value]) => key.trim() === '' || typeof value !== 'string')) {
    throw new Error('invalid env')
  }
  return config
}

export async function runSubprocessWorker(configInput) {
  const config = validate(configInput)
  const workerStartedAt = Date.now()
  const workerFingerprint = config.workerFingerprint
  const base = {
    version: 1,
    effectId: config.effectId,
    commandFingerprint: config.commandFingerprint,
    workerPid: process.pid,
    workerStartedAt,
    workerFingerprint,
    statePath: config.statePath,
  }
  await writeState(config.statePath, { ...base, status: 'starting', updatedAt: Date.now() })

  const stdout = { chunks: [], bytes: 0, limit: config.maxOutputBytes, truncated: false }
  const stderr = { chunks: [], bytes: 0, limit: config.maxOutputBytes, truncated: false }
  const childStartedAt = Date.now()
  let child
  let termination = undefined
  let timeout
  let cancelListener
  try {
    child = spawn(config.executable, config.args, {
      cwd: config.cwd,
      env: config.env,
      windowsHide: true,
      shell: false,
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    const completion = new Promise(resolveResult => {
      let settled = false
      const settle = value => {
        if (settled) return
        settled = true
        resolveResult(value)
      }
      child.stdout?.on('data', chunk => appendLimited(stdout, chunk))
      child.stderr?.on('data', chunk => appendLimited(stderr, chunk))
      child.once('error', error => settle({ error }))
      child.once('close', (code, signal) => settle({ code, signal }))
    })
    if (!Number.isSafeInteger(child.pid) || child.pid <= 0) throw new Error('spawned command has no PID')
    const running = {
      ...base,
      status: 'running',
      childPid: child.pid,
      childStartedAt,
      updatedAt: Date.now(),
    }
    await writeState(config.statePath, running)
    process.send?.({ type: 'running', state: running })

    cancelListener = message => {
      if (message?.type !== 'cancel' || termination !== undefined) return
      termination = 'cancelled'
      terminateTree(child, config.env)
    }
    process.on('message', cancelListener)
    timeout = setTimeout(() => {
      if (termination !== undefined) return
      termination = 'timed_out'
      terminateTree(child, config.env)
    }, config.timeoutMs)

    const outcome = await completion
    const status = outcome.error !== undefined
      ? 'spawn_failed'
      : termination ?? (outcome.code === 0 ? 'succeeded' : 'failed')
    const terminal = {
      ...running,
      status,
      exitCode: Number.isSafeInteger(outcome.code) ? outcome.code : null,
      signal: typeof outcome.signal === 'string' ? outcome.signal : null,
      stdout: text(stdout),
      stderr: text(stderr),
      stdoutTruncated: stdout.truncated,
      stderrTruncated: stderr.truncated,
      error: outcome.error instanceof Error ? outcome.error.message : undefined,
      finishedAt: Date.now(),
      updatedAt: Date.now(),
    }
    await writeState(config.statePath, terminal)
    process.send?.({ type: 'terminal', state: terminal })
    return terminal
  }
  catch (error) {
    const failed = {
      ...base,
      status: 'spawn_failed',
      childPid: child?.pid ?? null,
      childStartedAt,
      exitCode: null,
      signal: null,
      stdout: text(stdout),
      stderr: text(stderr),
      stdoutTruncated: stdout.truncated,
      stderrTruncated: stderr.truncated,
      error: error instanceof Error ? error.message : String(error),
      finishedAt: Date.now(),
      updatedAt: Date.now(),
    }
    await writeState(config.statePath, failed)
    return failed
  }
  finally {
    if (timeout !== undefined) clearTimeout(timeout)
    if (cancelListener !== undefined) process.removeListener('message', cancelListener)
  }
}

async function main() {
  const configPath = process.argv[2]
  if (typeof configPath !== 'string' || !isAbsolute(configPath)) throw new Error('absolute config path is required')
  const config = JSON.parse(await readFile(resolve(configPath), 'utf8'))
  const state = await runSubprocessWorker(config)
  if (!TERMINAL.has(state.status)) throw new Error(`worker stopped in ${state.status}`)
  process.disconnect?.()
}

const invoked = process.argv[1] === undefined ? undefined : pathToFileURL(resolve(process.argv[1])).href
if (invoked === import.meta.url) {
  main().catch(error => {
    process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`)
    process.exitCode = 1
  })
}
