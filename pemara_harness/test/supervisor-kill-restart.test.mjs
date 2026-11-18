import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'
import { SupervisorStore } from '../src/supervisor-store.mjs'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DRIVER = join(ROOT, 'test', 'fixtures', 'supervisor-driver.mjs')
const CHILD = join(ROOT, 'test', 'fixtures', 'supervisor-kill-child.mjs')
const LOCK_PROCESS = join(ROOT, 'test', 'fixtures', 'supervisor-lock-process.mjs')

function isAlive(pid) {
  try { process.kill(pid, 0); return true } catch { return false }
}

async function waitFor(check, { timeoutMs = 8_000, intervalMs = 25 } = {}) {
  const deadline = Date.now() + timeoutMs
  let lastError
  while (Date.now() < deadline) {
    try {
      const value = check()
      if (value) return value
    }
    catch (error) {
      lastError = error
    }
    await new Promise(resolveDelay => setTimeout(resolveDelay, intervalMs))
  }
  throw lastError ?? new Error(`condition not met in ${timeoutMs}ms`)
}

function collect(child) {
  let stdout = ''
  let stderr = ''
  child.stdout.on('data', chunk => { stdout += chunk })
  child.stderr.on('data', chunk => { stderr += chunk })
  return new Promise(resolveResult => {
    child.once('close', (code, signal) => resolveResult({ code, signal, stdout, stderr }))
  })
}

test('two real processes admit exactly one supervisor lock', { timeout: 10_000 }, async () => {
  const root = mkdtempSync(join(tmpdir(), 'pemara-supervisor-lock-'))
  const databasePath = join(root, 'ledger.sqlite')
  const readyA = join(root, 'a.ready.json')
  const readyB = join(root, 'b.ready.json')
  let holder
  try {
    const ledger = new DurableTaskStore({ databasePath })
    ledger.createTask({ id: 'lock-task', objective: 'Excluir concorrência real' })
    ledger.close()
    const supervisor = new SupervisorStore({ databasePath })
    supervisor.configureJob({
      taskId: 'lock-task',
      executable: process.execPath,
      args: [CHILD, join(root, 'unused.json')],
      workspace: root,
    })
    supervisor.close()

    holder = spawn(process.execPath, [
      LOCK_PROCESS, databasePath, 'lock-task', 'holder-a', readyA, '700',
    ], { cwd: ROOT, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    const holderCompletion = collect(holder)
    await waitFor(() => existsSync(readyA))

    const contender = spawnSync(process.execPath, [
      LOCK_PROCESS, databasePath, 'lock-task', 'holder-b', readyB, '0',
    ], { cwd: ROOT, windowsHide: true, encoding: 'utf8', timeout: 5_000 })
    assert.equal(contender.status, 2)
    assert.equal(JSON.parse(contender.stderr).code, 'SUPERVISOR_LOCK_HELD')
    assert.equal(existsSync(readyB), false)

    const holderExit = await holderCompletion
    assert.equal(holderExit.code, 0, holderExit.stderr)
    assert.equal(JSON.parse(holderExit.stdout).acquired, true)
  }
  finally {
    if (holder !== undefined && isAlive(holder.pid)) holder.kill('SIGKILL')
    await new Promise(resolveDelay => setTimeout(resolveDelay, 50))
    rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})

test('real supervisor kill recovers the same task from its checkpoint without an orphan', { timeout: 20_000 }, async () => {
  const root = mkdtempSync(join(tmpdir(), 'pemara-kill-restart-'))
  const databasePath = join(root, 'ledger.sqlite')
  const markerPath = join(root, 'first-child.json')
  let firstSupervisor
  let secondSupervisor
  let firstChildPid
  try {
    const ledger = new DurableTaskStore({ databasePath })
    ledger.createTask({ id: 'kill-task', objective: 'Continuar depois de uma queda real' })
    const lease = ledger.claimTask('kill-task', { owner: 'fixture', leaseMs: 60_000 })
    ledger.startRound('kill-task', lease.token)
    ledger.checkpoint('kill-task', lease.token, {
      summary: 'Checkpoint anterior à queda',
      nextAction: 'Executar somente a próxima etapa',
      artifacts: ['durable-checkpoint'],
    })
    ledger.releaseLease('kill-task', lease.token)
    ledger.close()

    const supervisor = new SupervisorStore({ databasePath })
    supervisor.configureJob({
      taskId: 'kill-task',
      executable: process.execPath,
      args: [CHILD, markerPath, '{{PEMARA_TASK}}'],
      workspace: root,
      maxRestarts: 3,
      backoffMs: [100, 200, 300],
    })
    supervisor.close()

    firstSupervisor = spawn(process.execPath, [DRIVER, databasePath, 'kill-task'], {
      cwd: ROOT,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    const firstCompletion = collect(firstSupervisor)
    const marker = await waitFor(() => {
      if (!existsSync(markerPath)) return undefined
      return JSON.parse(readFileSync(markerPath, 'utf8'))
    })
    firstChildPid = marker.pid
    await waitFor(() => {
      const store = new SupervisorStore({ databasePath })
      try { return store.listAttempts('kill-task')[0]?.status === 'RUNNING' } finally { store.close() }
    })

    firstSupervisor.kill('SIGKILL')
    const firstExit = await firstCompletion
    assert.notEqual(firstExit.code, 0)
    // Windows may tear down the descendant with the killed parent; if it does
    // not, terminate only the exact journaled fixture PID before recovery.
    if (isAlive(firstChildPid)) process.kill(firstChildPid, 'SIGKILL')
    await waitFor(() => !isAlive(firstChildPid))
    await new Promise(resolveDelay => setTimeout(resolveDelay, 900))

    secondSupervisor = spawn(process.execPath, [DRIVER, databasePath, 'kill-task'], {
      cwd: ROOT,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    const secondExit = await collect(secondSupervisor)
    assert.equal(secondExit.code, 0, secondExit.stderr)
    assert.equal(JSON.parse(secondExit.stdout).status, 'COMPLETED')

    const finalStore = new SupervisorStore({ databasePath })
    const attempts = finalStore.listAttempts('kill-task')
    assert.deepEqual(attempts.map(attempt => attempt.status), ['INTERRUPTED', 'SUCCEEDED'])
    assert.equal(attempts[0].taskId, 'kill-task')
    assert.equal(attempts[1].taskId, 'kill-task')
    assert.match(attempts[1].result.stdout, /resumed-from-durable-checkpoint/)
    assert.equal(finalStore.getJob('kill-task').status, 'COMPLETED')
    finalStore.close()

    const finalLedger = new DurableTaskStore({ databasePath })
    const task = finalLedger.getTask('kill-task')
    assert.equal(task.checkpoint.summary, 'Checkpoint anterior à queda')
    assert.equal(finalLedger.listEvents('kill-task').filter(event => event.type === 'task.checkpointed').length, 1)
    assert.equal(finalLedger.listEffects('kill-task').length, 0)
    finalLedger.close()
    assert.equal(isAlive(firstChildPid), false)
  }
  finally {
    if (firstSupervisor !== undefined && isAlive(firstSupervisor.pid)) firstSupervisor.kill('SIGKILL')
    if (secondSupervisor !== undefined && isAlive(secondSupervisor.pid)) secondSupervisor.kill('SIGKILL')
    if (firstChildPid !== undefined && isAlive(firstChildPid)) process.kill(firstChildPid, 'SIGKILL')
    await new Promise(resolveDelay => setTimeout(resolveDelay, 50))
    rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
  }
})
