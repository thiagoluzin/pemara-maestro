import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'

import { DurableTaskStore } from './index.mjs'
import { SupervisorStateError, SupervisorStore } from './supervisor-store.mjs'

const TASK_PLACEHOLDER = '{{PEMARA_TASK}}'
const DEFAULT_LEASE_MS = 120_000
const DEFAULT_HEARTBEAT_MS = 5_000
const DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024

function supervisorError(code, message, details = undefined) {
  return new SupervisorStateError(code, message, details)
}

function defaultDelay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(supervisorError('SUPERVISOR_CANCELLED', 'Supervisor was cancelled.'))
      return
    }
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(supervisorError('SUPERVISOR_CANCELLED', 'Supervisor was cancelled.'))
    }, { once: true })
  })
}

function defaultInspectProcess(pid) {
  try {
    process.kill(pid, 0)
    // Node has no cross-platform public API for another process's creation
    // fingerprint. Alive-without-identity is deliberately not treated as the
    // original child; stale recovery will block for a human instead of rerun.
    return { alive: true }
  }
  catch (error) {
    return error?.code === 'ESRCH' ? { alive: false } : { alive: true }
  }
}

function defaultTerminateChild(child, signal = 'SIGTERM') {
  if (child === undefined || child.pid === undefined) return false
  return child.kill(signal)
}

function selfFingerprint() {
  return createHash('sha256')
    .update(JSON.stringify({ pid: process.pid, execPath: process.execPath, argv: process.argv }))
    .digest('hex')
}

function attemptFingerprint(commandFingerprint, attemptId) {
  return createHash('sha256').update(`${commandFingerprint}\u0000${attemptId}`).digest('hex')
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

function outputText(state) {
  return Buffer.concat(state.chunks, state.bytes).toString('utf8')
}

function commandArguments(args, task) {
  const occurrences = args.filter(argument => argument === TASK_PLACEHOLDER).length
  if (occurrences > 1) {
    throw supervisorError(
      'SUPERVISOR_COMMAND_INVALID',
      `Command may contain ${TASK_PLACEHOLDER} at most once.`,
    )
  }
  return occurrences === 1
    ? args.map(argument => argument === TASK_PLACEHOLDER ? task : argument)
    : [...args, task]
}

export function composeAttemptTask(task) {
  const lines = [
    'TAREFA DURÁVEL PEMARA',
    `Task ID: ${task.id}`,
    `Objetivo: ${task.objective}`,
    '',
  ]
  if (task.checkpoint === undefined) {
    lines.push('Checkpoint: nenhum. Comece pela primeira ação verificável.')
  }
  else {
    lines.push(
      'Retome exclusivamente do checkpoint durável abaixo:',
      `Resumo: ${task.checkpoint.summary}`,
      `Próxima ação: ${task.checkpoint.nextAction}`,
      `Artefatos: ${(task.checkpoint.artifacts ?? []).join(', ') || '(nenhum)'}`,
    )
    if (task.checkpoint.data !== undefined) {
      lines.push(`Dados: ${JSON.stringify(task.checkpoint.data)}`)
    }
  }
  lines.push(
    '',
    'Não repita efeito externo já iniciado. Se o resultado de um efeito for incerto, pare e peça reconciliação humana.',
    'Solicite conclusão somente com checkpoint final e evidência; a verificação é independente.',
  )
  return lines.join('\n')
}

function childCompletion(child, outputLimit) {
  const stdout = { chunks: [], bytes: 0, limit: outputLimit, truncated: false }
  const stderr = { chunks: [], bytes: 0, limit: outputLimit, truncated: false }
  child.stdout?.on('data', chunk => appendLimited(stdout, chunk))
  child.stderr?.on('data', chunk => appendLimited(stderr, chunk))
  const completion = new Promise(resolve => {
    let settled = false
    const settle = value => {
      if (settled) return
      settled = true
      resolve(value)
    }
    child.once('error', error => settle({ error }))
    child.once('close', (code, signal) => settle({ code, signal }))
  })
  return {
    completion,
    result() {
      return {
        stdout: outputText(stdout),
        stderr: outputText(stderr),
        stdoutTruncated: stdout.truncated,
        stderrTruncated: stderr.truncated,
      }
    },
  }
}

async function runOneAttempt({
  store,
  task,
  job,
  lock,
  spawnImpl,
  inspectLaunchedProcess,
  terminateChild,
  signal,
  clock,
  heartbeatMs,
  leaseMs,
  maxOutputBytes,
}) {
  if (signal?.aborted) throw supervisorError('SUPERVISOR_CANCELLED', 'Supervisor was cancelled.')
  const admitted = store.admitAttempt(task.id, lock.token, {
    runnerFingerprint: `pending:${job.commandFingerprint}`,
  })
  const expectedFingerprint = attemptFingerprint(job.commandFingerprint, admitted.id)
  const prompt = composeAttemptTask(task)
  const args = commandArguments(job.command.args, prompt)
  let child
  let heartbeat
  let abortListener
  let completionState
  let startedAt = clock()
  let cancelled = false

  try {
    child = spawnImpl(job.command.executable, args, {
      cwd: job.workspace,
      env: {
        ...process.env,
        PEMARA_SUPERVISOR_TASK_ID: task.id,
        PEMARA_SUPERVISOR_ATTEMPT_ID: admitted.id,
        PEMARA_SUPERVISOR_REBIND_AUTHORITY: `pemara-supervisor:${admitted.id}`,
      },
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    completionState = childCompletion(child, maxOutputBytes)
    if (!Number.isSafeInteger(child.pid) || child.pid <= 0) {
      throw supervisorError('SUPERVISOR_CHILD_PID_MISSING', 'Spawned child did not expose a valid PID.')
    }
    const observed = inspectLaunchedProcess?.(child.pid, { startedAt, expectedFingerprint })
    if (observed?.alive === false) {
      throw supervisorError('SUPERVISOR_CHILD_NOT_RUNNING', 'Spawned child exited before identity capture.')
    }
    const processStartedAt = Number.isSafeInteger(observed?.processStartedAt)
      ? observed.processStartedAt
      : startedAt
    const runnerFingerprint = typeof observed?.runnerFingerprint === 'string' && observed.runnerFingerprint.trim() !== ''
      ? observed.runnerFingerprint.trim()
      : expectedFingerprint
    store.markAttemptRunning(task.id, lock.token, admitted.id, {
      pid: child.pid,
      processStartedAt,
      runnerFingerprint,
    })
    heartbeat = setInterval(() => {
      try { store.heartbeat(task.id, lock.token, leaseMs) } catch {}
    }, heartbeatMs)
    heartbeat.unref?.()
    abortListener = () => {
      cancelled = true
      terminateChild(child, 'SIGTERM')
    }
    signal?.addEventListener('abort', abortListener, { once: true })
    if (signal?.aborted) abortListener()

    const outcome = await completionState.completion
    const captured = completionState.result()
    if (cancelled || signal?.aborted) {
      return store.finishAttempt(task.id, lock.token, admitted.id, {
        status: 'CANCELLED',
        ...(typeof outcome.signal === 'string' ? { signal: outcome.signal } : {}),
        result: captured,
      })
    }
    if (outcome.error !== undefined) {
      return store.finishAttempt(task.id, lock.token, admitted.id, {
        status: 'FAILED',
        result: { ...captured, error: outcome.error instanceof Error ? outcome.error.message : String(outcome.error) },
      })
    }
    const succeeded = outcome.code === 0
    return store.finishAttempt(task.id, lock.token, admitted.id, {
      status: succeeded ? 'SUCCEEDED' : 'FAILED',
      ...(Number.isSafeInteger(outcome.code) && outcome.code >= 0 ? { exitCode: outcome.code } : {}),
      ...(typeof outcome.signal === 'string' ? { signal: outcome.signal } : {}),
      result: captured,
    })
  }
  catch (error) {
    if (child !== undefined && completionState !== undefined) {
      try { terminateChild(child, 'SIGTERM') } catch {}
    }
    const current = store.listAttempts(task.id).find(attempt => attempt.id === admitted.id)
    if (current?.status === 'ADMITTED' || current?.status === 'RUNNING') {
      return store.finishAttempt(task.id, lock.token, admitted.id, {
        status: signal?.aborted ? 'CANCELLED' : 'FAILED',
        result: { error: error instanceof Error ? error.message : String(error) },
      })
    }
    throw error
  }
  finally {
    if (heartbeat !== undefined) clearInterval(heartbeat)
    if (abortListener !== undefined) signal?.removeEventListener('abort', abortListener)
  }
}

/**
 * Run one or a bounded series of attempts from the durable supervisor journal.
 * No unjournaled child is launched and every restart consumes persisted budget.
 */
export async function runSupervisor({
  databasePath,
  taskId,
  once = false,
  owner = `pemara-supervisor:${process.pid}`,
  processFingerprint = selfFingerprint(),
  leaseMs = DEFAULT_LEASE_MS,
  heartbeatMs = DEFAULT_HEARTBEAT_MS,
  maxOutputBytes = DEFAULT_MAX_OUTPUT_BYTES,
  clock = Date.now,
  delay = defaultDelay,
  spawnImpl = spawn,
  inspectStaleProcess = defaultInspectProcess,
  inspectLaunchedProcess,
  terminateChild = defaultTerminateChild,
  signal,
} = {}) {
  if (typeof once !== 'boolean') throw supervisorError('INVALID_INPUT', 'once must be a boolean.')
  if (typeof clock !== 'function' || typeof delay !== 'function' || typeof spawnImpl !== 'function') {
    throw supervisorError('INVALID_INPUT', 'clock, delay and spawnImpl must be functions.')
  }
  if (!Number.isSafeInteger(leaseMs) || leaseMs <= 0) throw supervisorError('INVALID_INPUT', 'leaseMs must be positive.')
  if (!Number.isSafeInteger(heartbeatMs) || heartbeatMs <= 0 || heartbeatMs >= leaseMs) {
    throw supervisorError('INVALID_INPUT', 'heartbeatMs must be positive and lower than leaseMs.')
  }
  if (!Number.isSafeInteger(maxOutputBytes) || maxOutputBytes <= 0) {
    throw supervisorError('INVALID_INPUT', 'maxOutputBytes must be positive.')
  }

  const store = new SupervisorStore({ databasePath, clock })
  let lock
  try {
    let job = store.getJob(taskId)
    if (job.lock !== undefined && job.lock.expiresAt <= clock()) {
      const recovery = store.recoverStale(taskId, { inspectProcess: inspectStaleProcess })
      if (!recovery.recovered) {
        return Object.freeze({ status: 'RUNNING', recovery, job: store.getJob(taskId) })
      }
      job = store.getJob(taskId)
      if (job.status === 'BLOCKED' || job.status === 'EXHAUSTED') {
        return Object.freeze({ status: job.status, recovery, job })
      }
    }

    lock = store.acquire(taskId, { owner, leaseMs, processFingerprint })
    while (true) {
      job = store.getJob(taskId)
      if (job.status === 'BACKOFF') {
        const waitMs = Math.max(0, (job.nextAttemptAt ?? clock()) - clock())
        if (waitMs > 0) {
          store.heartbeat(taskId, lock.token, leaseMs)
          await delay(waitMs, signal)
          lock = store.heartbeat(taskId, lock.token, leaseMs)
        }
      }

      let ledger = new DurableTaskStore({ databasePath })
      let task
      try {
        task = ledger.getTask(taskId)
        if (task.lease !== undefined && task.lease.expiresAt > clock()) {
          const leaseWaitMs = task.lease.expiresAt - clock()
          ledger.close()
          ledger = undefined
          store.heartbeat(taskId, lock.token, leaseMs)
          await delay(leaseWaitMs, signal)
          lock = store.heartbeat(taskId, lock.token, leaseMs)
          ledger = new DurableTaskStore({ databasePath })
          ledger.recover()
          task = ledger.getTask(taskId)
        }
      }
      finally { ledger?.close() }
      if (task.status !== 'ACTIVE') {
        throw supervisorError(
          'TASK_NOT_SUPERVISABLE',
          `Task "${taskId}" is ${task.status}; only ACTIVE tasks may run.`,
          { status: task.status },
        )
      }

      const outcome = await runOneAttempt({
        store,
        task,
        job: store.getJob(taskId),
        lock,
        spawnImpl,
        inspectLaunchedProcess,
        terminateChild,
        signal,
        clock,
        heartbeatMs,
        leaseMs,
        maxOutputBytes,
      })
      const current = outcome.job
      if (once || current.status !== 'BACKOFF') {
        return Object.freeze({ status: current.status, job: current, attempt: outcome.attempt })
      }
      lock = store.heartbeat(taskId, lock.token, leaseMs)
    }
  }
  finally {
    if (lock !== undefined) {
      try {
        const job = store.getJob(taskId)
        if (job.lock?.token === lock.token) store.release(taskId, lock.token)
      }
      catch {}
    }
    store.close()
  }
}

export {
  DEFAULT_HEARTBEAT_MS,
  DEFAULT_LEASE_MS,
  DEFAULT_MAX_OUTPUT_BYTES,
  TASK_PLACEHOLDER,
}
