import { createHash, randomUUID } from 'node:crypto'
import { fork } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, realpathSync } from 'node:fs'
import { readFile, rename, writeFile } from 'node:fs/promises'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

import { HarnessStateError } from '../index.mjs'

const WORKER_ENTRY = fileURLToPath(new URL('./subprocess-worker.mjs', import.meta.url))
const TERMINAL = new Set(['succeeded', 'failed', 'timed_out', 'cancelled', 'spawn_failed'])
const SENSITIVE_ENV = /(token|secret|password|credential|api[_-]?key|private[_-]?key)/iu
const SENSITIVE_ARG = /(^|[=:\s])(bearer|token|secret|password|api[_-]?key)([=:\s]|$)|\bsk-[a-z0-9_-]+/iu

function subprocessError(code, message, details = undefined) {
  return new HarnessStateError(code, message, details)
}

function requiredText(value, field) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw subprocessError('INVALID_INPUT', `${field} must be a non-empty string.`)
  }
  return value.trim()
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonicalize(value[key])]))
  }
  return value
}

function digest(value) {
  return createHash('sha256').update(JSON.stringify(canonicalize(value))).digest('hex')
}

function pathKey(path) {
  return process.platform === 'win32' ? path.toLowerCase() : path
}

function within(root, candidate) {
  const rel = relative(pathKey(root), pathKey(candidate))
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

function positiveInteger(value, field, maximum) {
  if (!Number.isSafeInteger(value) || value <= 0 || value > maximum) {
    throw subprocessError('INVALID_INPUT', `${field} must be between 1 and ${maximum}.`)
  }
  return value
}

const ESSENTIAL_ENV_KEYS = Object.freeze([
  'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL',
])

export function sanitizedSubprocessEnvironment(source = process.env, overlay = {}) {
  const environment = {}
  for (const key of ESSENTIAL_ENV_KEYS) {
    const value = source[key]
    if (typeof value === 'string' && value !== '') environment[key] = value
  }
  for (const [key, value] of Object.entries(overlay)) environment[key] = value
  environment.CI = '1'
  environment.PEMARA_SUBPROCESS_SANDBOX = '1'
  return Object.freeze(environment)
}

function normalizeCommand(workspaceRoot, commandId, commands) {
  const id = requiredText(commandId, 'commandId')
  if (commands === null || typeof commands !== 'object' || Array.isArray(commands)) {
    throw subprocessError('INVALID_INPUT', 'commands must be a host-owned command map.')
  }
  const raw = commands[id]
  if (raw === undefined) {
    throw subprocessError('SUBPROCESS_COMMAND_DENIED', `Command "${id}" is not in the allowlist.`)
  }
  const allowedKeys = new Set(['executable', 'args', 'cwd', 'timeoutMs', 'maxOutputBytes', 'env'])
  const extra = Object.keys(raw).filter(key => !allowedKeys.has(key))
  if (extra.length > 0) throw subprocessError('INVALID_INPUT', `Unknown command fields: ${extra.join(', ')}.`)
  const root = realpathSync.native(resolve(requiredText(workspaceRoot, 'workspaceRoot')))
  const executableInput = requiredText(raw.executable, 'command.executable')
  if (!isAbsolute(executableInput) || !existsSync(executableInput)) {
    throw subprocessError('SUBPROCESS_EXECUTABLE_INVALID', 'Allowlisted executable must be an existing absolute path.')
  }
  const executable = realpathSync.native(resolve(executableInput))
  const cwdInput = requiredText(raw.cwd, 'command.cwd')
  if (!isAbsolute(cwdInput) || !existsSync(cwdInput)) {
    throw subprocessError('SUBPROCESS_CWD_INVALID', 'Allowlisted cwd must be an existing absolute directory.')
  }
  const cwd = realpathSync.native(resolve(cwdInput))
  if (!within(root, cwd)) {
    throw subprocessError('SUBPROCESS_CWD_ESCAPE', 'Allowlisted cwd escapes the workspace.', { root, cwd })
  }
  if (!Array.isArray(raw.args) || raw.args.some(argument => typeof argument !== 'string' || argument.includes('\u0000'))) {
    throw subprocessError('INVALID_INPUT', 'command.args must be an array of strings without NUL bytes.')
  }
  if (raw.args.some(argument => SENSITIVE_ARG.test(argument))) {
    throw subprocessError('SUBPROCESS_ARGUMENT_DENIED', 'Credential-like arguments are not allowed in persisted commands.')
  }
  const env = raw.env ?? {}
  if (env === null || typeof env !== 'object' || Array.isArray(env)
    || Object.entries(env).some(([key, value]) => key.trim() === '' || typeof value !== 'string')) {
    throw subprocessError('INVALID_INPUT', 'command.env must map names to strings.')
  }
  const sensitive = Object.keys(env).filter(key => SENSITIVE_ENV.test(key))
  if (sensitive.length > 0) {
    throw subprocessError('SUBPROCESS_ENV_DENIED', 'Credential-like environment keys are not allowed.', { keys: sensitive })
  }
  const timeoutMs = positiveInteger(raw.timeoutMs, 'command.timeoutMs', 60 * 60 * 1000)
  const maxOutputBytes = positiveInteger(raw.maxOutputBytes, 'command.maxOutputBytes', 1024 * 1024)
  const environment = sanitizedSubprocessEnvironment(process.env, env)
  const environmentFingerprint = digest(environment)
  const command = {
    id,
    executable,
    args: [...raw.args],
    cwd,
    timeoutMs,
    maxOutputBytes,
    env: environment,
    environmentFingerprint,
  }
  return Object.freeze({
    ...command,
    commandFingerprint: digest(command),
  })
}

async function writeJsonAtomic(path, value) {
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  await rename(temporary, path)
}

async function readState(path) {
  try { return JSON.parse(await readFile(path, 'utf8')) } catch (error) {
    if (error?.code === 'ENOENT') return undefined
    throw error
  }
}

function defaultInspectProcess(pid) {
  try { process.kill(pid, 0); return { alive: true } } catch { return { alive: false } }
}

function resultFromState(state) {
  return {
    status: state.status,
    commandFingerprint: state.commandFingerprint,
    workerPid: state.workerPid,
    workerStartedAt: state.workerStartedAt,
    workerFingerprint: state.workerFingerprint,
    childPid: state.childPid ?? null,
    childStartedAt: state.childStartedAt ?? null,
    exitCode: state.exitCode ?? null,
    signal: state.signal ?? null,
    stdout: state.stdout ?? '',
    stderr: state.stderr ?? '',
    stdoutTruncated: state.stdoutTruncated === true,
    stderrTruncated: state.stderrTruncated === true,
    error: state.error,
    finishedAt: state.finishedAt,
  }
}

function reuse(effect) {
  if (effect.status === 'COMMITTED') {
    return Object.freeze({ status: effect.result.status, effect, reused: true })
  }
  if (effect.status === 'FAILED') {
    return Object.freeze({ status: effect.result?.detail?.status ?? 'failed', effect, reused: true })
  }
  throw subprocessError('SUBPROCESS_EFFECT_IN_PROGRESS', `Subprocess effect is ${effect.status}.`, {
    effectId: effect.id,
  })
}

function workerCompletion(worker) {
  return new Promise(resolveResult => {
    let settled = false
    const settle = value => {
      if (settled) return
      settled = true
      resolveResult(value)
    }
    worker.once('error', error => settle({ error }))
    worker.once('exit', (code, signal) => settle({ code, signal }))
  })
}

/** Execute one immutable command definition through the fixed collector worker. */
export async function runAllowlistedSubprocess({
  store,
  taskId,
  leaseToken,
  key,
  commandId,
  workspaceRoot,
  commands,
  runtimeRoot,
  forkImpl = fork,
  signal,
  fault = () => {},
} = {}) {
  if (store === null || typeof store?.prepareEffect !== 'function') {
    throw subprocessError('INVALID_INPUT', 'store must be a DurableTaskStore.')
  }
  if (typeof forkImpl !== 'function' || typeof fault !== 'function') {
    throw subprocessError('INVALID_INPUT', 'forkImpl and fault must be functions.')
  }
  const command = normalizeCommand(workspaceRoot, commandId, commands)
  const root = runtimeRoot === undefined
    ? join(dirname(store.databasePath), 'subprocess-effects')
    : resolve(requiredText(runtimeRoot, 'runtimeRoot'))
  const request = {
    commandId: command.id,
    commandFingerprint: command.commandFingerprint,
    executable: command.executable,
    args: command.args,
    cwd: command.cwd,
    timeoutMs: command.timeoutMs,
    maxOutputBytes: command.maxOutputBytes,
    environmentFingerprint: command.environmentFingerprint,
  }
  const effect = store.prepareEffect(taskId, leaseToken, {
    key,
    kind: 'subprocess.allowlisted',
    request,
  })
  if (effect.status !== 'PREPARED') return reuse(effect)
  store.markEffectStarted(taskId, leaseToken, effect.id)
  mkdirSync(root, { recursive: true })
  const configPath = join(root, `${effect.id}.config.json`)
  const statePath = join(root, `${effect.id}.state.json`)
  const workerFingerprint = digest({
    workerEntry: WORKER_ENTRY,
    effectId: effect.id,
    commandFingerprint: command.commandFingerprint,
  })
  await writeJsonAtomic(configPath, {
    version: 1,
    effectId: effect.id,
    commandFingerprint: command.commandFingerprint,
    workerFingerprint,
    executable: command.executable,
    args: command.args,
    cwd: command.cwd,
    timeoutMs: command.timeoutMs,
    maxOutputBytes: command.maxOutputBytes,
    env: command.env,
    statePath,
  })

  const worker = forkImpl(WORKER_ENTRY, [configPath], {
    cwd: command.cwd,
    env: command.env,
    windowsHide: true,
    detached: false,
    stdio: ['ignore', 'ignore', 'ignore', 'ipc'],
  })
  const completion = workerCompletion(worker)
  fault('after-worker-spawn', { worker, effectId: effect.id, configPath, statePath })
  const cancel = () => {
    try { worker.send({ type: 'cancel' }) } catch {}
  }
  signal?.addEventListener('abort', cancel, { once: true })
  if (signal?.aborted) cancel()
  let outcome
  try { outcome = await completion } finally { signal?.removeEventListener('abort', cancel) }
  const state = await readState(statePath)
  fault('after-worker-exit', { worker, effectId: effect.id, configPath, statePath, state, outcome })
  if (state === undefined || !TERMINAL.has(state.status)) {
    throw subprocessError('SUBPROCESS_OUTCOME_UNKNOWN', 'Collector exited without a terminal state.', {
      effectId: effect.id,
      workerExitCode: outcome.code,
      workerSignal: outcome.signal,
      workerError: outcome.error instanceof Error ? outcome.error.message : undefined,
    })
  }
  const result = resultFromState(state)
  if (state.status === 'succeeded') {
    const committed = store.commitEffect(taskId, leaseToken, effect.id, result)
    return Object.freeze({ status: state.status, effect: committed, statePath, reused: false })
  }
  const failed = store.failEffect(
    taskId,
    leaseToken,
    effect.id,
    `Allowlisted command ended as ${state.status}.`,
    result,
  )
  return Object.freeze({ status: state.status, effect: failed, statePath, reused: false })
}

function normalizeEvidence(evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0
    || evidence.some(item => typeof item !== 'string' || item.trim() === '')) {
    throw subprocessError('INVALID_INPUT', 'evidence must contain at least one non-empty string.')
  }
  return evidence.map(item => item.trim())
}

/** Reconcile OUTCOME_UNKNOWN from the collector's atomic state file. */
export function reconcileAllowlistedSubprocess({
  store,
  effectId,
  resolver,
  evidence,
  inspectProcess = defaultInspectProcess,
} = {}) {
  if (store === null || typeof store?.getEffect !== 'function') {
    throw subprocessError('INVALID_INPUT', 'store must be a DurableTaskStore.')
  }
  if (typeof inspectProcess !== 'function') throw subprocessError('INVALID_INPUT', 'inspectProcess must be a function.')
  const proof = normalizeEvidence(evidence)
  const effect = store.getEffect(requiredText(effectId, 'effectId'))
  if (effect.kind !== 'subprocess.allowlisted') {
    throw subprocessError('SUBPROCESS_EFFECT_KIND', `Effect ${effect.id} is ${effect.kind}.`)
  }
  if (effect.status !== 'OUTCOME_UNKNOWN') {
    throw subprocessError('EFFECT_NOT_UNCERTAIN', `Effect ${effect.id} is ${effect.status}.`)
  }
  const statePath = join(dirname(store.databasePath), 'subprocess-effects', `${effect.id}.state.json`)
  let state
  try {
    state = existsSync(statePath) ? JSON.parse(readFileSync(statePath, 'utf8')) : undefined
  }
  catch (error) {
    throw subprocessError('SUBPROCESS_STATE_INVALID', 'Collector state cannot be parsed.', {
      error: error instanceof Error ? error.message : String(error),
    })
  }
  if (state === undefined) return Object.freeze({ status: 'needs-human', reason: 'state-missing', effect, statePath })
  if (TERMINAL.has(state.status)) {
    const result = resultFromState(state)
    const outcome = state.status === 'succeeded' ? 'committed' : 'failed'
    const resolved = store.resolveEffect(effect.id, {
      resolver,
      outcome,
      evidence: [...proof, `collector status=${state.status}`, `worker pid=${state.workerPid}`],
      result,
    })
    return Object.freeze({
      status: outcome === 'committed' ? 'committed-from-worker-state' : 'failed-from-worker-state',
      effect: resolved.effect,
      state,
      statePath,
    })
  }
  if (state.status === 'running' || state.status === 'starting') {
    const observed = inspectProcess(state.workerPid, state)
    const exact = observed?.alive === true
      && observed.processStartedAt === state.workerStartedAt
      && observed.runnerFingerprint === state.workerFingerprint
    if (exact) return Object.freeze({ status: 'running-observed', effect, state, statePath })
    return Object.freeze({
      status: 'needs-human',
      reason: observed?.alive === true ? 'pid-unverified' : 'worker-ended-without-terminal-state',
      effect,
      state,
      statePath,
    })
  }
  return Object.freeze({ status: 'needs-human', reason: 'state-unknown', effect, state, statePath })
}
