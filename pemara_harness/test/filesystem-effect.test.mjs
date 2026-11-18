import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'
import { applyAtomicWrite, reconcileAtomicWrite } from '../src/effects/filesystem.mjs'

function sha256(value) {
  return createHash('sha256').update(value).digest('hex')
}

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-filesystem-effect-'))
  const workspace = join(root, 'workspace with spaces')
  mkdirSync(workspace)
  const databasePath = join(root, 'ledger.sqlite')
  const store = new DurableTaskStore({ databasePath })
  store.createTask({ id: 'fs-task', objective: 'Escrever atomicamente' })
  const lease = store.claimTask('fs-task', { owner: 'fixture', leaseMs: 60_000 })
  store.startRound('fs-task', lease.token)
  store.checkpoint('fs-task', lease.token, { summary: 'pronto', nextAction: 'escrever arquivo' })
  return {
    root,
    workspace,
    databasePath,
    store,
    lease,
    cleanup() {
      store.close()
      rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
    },
  }
}

test('atomic filesystem write is idempotent and supports Windows paths with spaces', () => {
  const fx = fixture()
  try {
    const first = applyAtomicWrite({
      store: fx.store,
      taskId: 'fs-task',
      leaseToken: fx.lease.token,
      key: 'write-readme',
      workspaceRoot: fx.workspace,
      relativePath: 'docs com espaço/resultado.txt',
      content: 'resultado estável\n',
      expectedPreviousSha256: null,
      createParents: true,
    })
    assert.equal(first.effect.status, 'COMMITTED')
    assert.equal(first.sha256, sha256('resultado estável\n'))
    const target = join(fx.workspace, 'docs com espaço', 'resultado.txt')
    assert.equal(readFileSync(target, 'utf8'), 'resultado estável\n')

    const second = applyAtomicWrite({
      store: fx.store,
      taskId: 'fs-task',
      leaseToken: fx.lease.token,
      key: 'write-readme',
      workspaceRoot: fx.workspace,
      relativePath: 'docs com espaço/resultado.txt',
      content: 'resultado estável\n',
      expectedPreviousSha256: null,
      createParents: true,
    })
    assert.equal(second.effect.id, first.effect.id)
    assert.equal(second.reused, true)
    assert.equal(fx.store.listEffects('fs-task').length, 1)
  }
  finally {
    fx.cleanup()
  }
})

test('failure before rename preserves the original and reconciles as failed', () => {
  const fx = fixture()
  try {
    const target = join(fx.workspace, 'existing.txt')
    writeFileSync(target, 'original\n')
    assert.throws(
      () => applyAtomicWrite({
        store: fx.store,
        taskId: 'fs-task',
        leaseToken: fx.lease.token,
        key: 'fault-before-rename',
        workspaceRoot: fx.workspace,
        relativePath: 'existing.txt',
        content: 'novo\n',
        expectedPreviousSha256: sha256('original\n'),
        fault(step) { if (step === 'after-temp') throw new Error('queda antes do rename') },
      }),
      /queda antes do rename/,
    )
    assert.equal(readFileSync(target, 'utf8'), 'original\n')
    const effect = fx.store.listEffects('fs-task')[0]
    fx.store.recover()
    const resolution = reconcileAtomicWrite({
      store: fx.store,
      effectId: effect.id,
      workspaceRoot: fx.workspace,
      resolver: 'host-test',
      evidence: ['hash original e temporário inspecionados'],
    })
    assert.equal(resolution.status, 'failed-before-rename')
    assert.equal(resolution.effect.status, 'FAILED')
    assert.equal(readFileSync(target, 'utf8'), 'original\n')
    assert.equal(existsSync(resolution.candidatePath), true)
  }
  finally {
    fx.cleanup()
  }
})

test('failure after rename reconciles by desired hash without writing twice', () => {
  const fx = fixture()
  try {
    assert.throws(
      () => applyAtomicWrite({
        store: fx.store,
        taskId: 'fs-task',
        leaseToken: fx.lease.token,
        key: 'fault-after-rename',
        workspaceRoot: fx.workspace,
        relativePath: 'promoted.txt',
        content: 'promovido uma vez\n',
        expectedPreviousSha256: null,
        fault(step) { if (step === 'after-rename') throw new Error('queda após rename') },
      }),
      /queda após rename/,
    )
    const effect = fx.store.listEffects('fs-task')[0]
    fx.store.recover()
    const resolution = reconcileAtomicWrite({
      store: fx.store,
      effectId: effect.id,
      workspaceRoot: fx.workspace,
      resolver: 'host-test',
      evidence: ['hash final corresponde ao desejado'],
    })
    assert.equal(resolution.status, 'committed-by-hash')
    assert.equal(resolution.effect.status, 'COMMITTED')
    assert.equal(readFileSync(join(fx.workspace, 'promoted.txt'), 'utf8'), 'promovido uma vez\n')
  }
  finally {
    fx.cleanup()
  }
})

test('precondition mismatch blocks instead of overwriting user work', () => {
  const fx = fixture()
  try {
    writeFileSync(join(fx.workspace, 'owned.txt'), 'mudança do usuário\n')
    assert.throws(
      () => applyAtomicWrite({
        store: fx.store,
        taskId: 'fs-task',
        leaseToken: fx.lease.token,
        key: 'stale-base',
        workspaceRoot: fx.workspace,
        relativePath: 'owned.txt',
        content: 'agente\n',
        expectedPreviousSha256: sha256('base antiga\n'),
      }),
      error => error?.code === 'FILESYSTEM_PRECONDITION_FAILED',
    )
    assert.equal(readFileSync(join(fx.workspace, 'owned.txt'), 'utf8'), 'mudança do usuário\n')
  }
  finally {
    fx.cleanup()
  }
})

test('path traversal and a junction escaping the workspace are refused', t => {
  const fx = fixture()
  try {
    assert.throws(
      () => applyAtomicWrite({
        store: fx.store,
        taskId: 'fs-task',
        leaseToken: fx.lease.token,
        key: 'escape-dotdot',
        workspaceRoot: fx.workspace,
        relativePath: '..\\fora.txt',
        content: 'não\n',
        expectedPreviousSha256: null,
      }),
      error => error?.code === 'FILESYSTEM_PATH_ESCAPE',
    )

    const outside = join(fx.root, 'outside')
    mkdirSync(outside)
    try {
      symlinkSync(outside, join(fx.workspace, 'escape-link'), process.platform === 'win32' ? 'junction' : 'dir')
    }
    catch (error) {
      if (error?.code === 'EPERM') {
        t.diagnostic('junction creation unavailable; traversal assertion still executed')
        return
      }
      throw error
    }
    assert.throws(
      () => applyAtomicWrite({
        store: fx.store,
        taskId: 'fs-task',
        leaseToken: fx.lease.token,
        key: 'escape-link',
        workspaceRoot: fx.workspace,
        relativePath: 'escape-link/payload.txt',
        content: 'não\n',
        expectedPreviousSha256: null,
        createParents: true,
      }),
      error => error?.code === 'FILESYSTEM_PATH_ESCAPE',
    )
  }
  finally {
    fx.cleanup()
  }
})
