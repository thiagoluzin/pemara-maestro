import assert from 'node:assert/strict'
import { chmodSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'

import { DurableTaskStore } from '../src/index.mjs'
import { createGitCandidate, executeGit, reconcileGitCandidate } from '../src/effects/git.mjs'

function git(repositoryRoot, args, options = {}) {
  const result = spawnSync('git', ['-C', repositoryRoot, ...args], {
    encoding: 'utf8',
    windowsHide: true,
    shell: false,
    ...options,
  })
  assert.equal(result.status, 0, result.stderr)
  return result.stdout.trim()
}

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-git-effect-'))
  const repositoryRoot = join(root, 'repo with spaces')
  mkdirSync(repositoryRoot)
  git(repositoryRoot, ['init', '-b', 'main'])
  git(repositoryRoot, ['config', 'user.name', 'Fixture'])
  git(repositoryRoot, ['config', 'user.email', 'fixture@example.invalid'])
  writeFileSync(join(repositoryRoot, 'work.txt'), 'base\n')
  git(repositoryRoot, ['add', 'work.txt'])
  git(repositoryRoot, ['commit', '-m', 'base'])
  const baseSha = git(repositoryRoot, ['rev-parse', 'HEAD'])

  const databasePath = join(root, 'ledger.sqlite')
  const store = new DurableTaskStore({ databasePath })
  store.createTask({ id: 'git-task', objective: 'Preparar candidato Git' })
  const lease = store.claimTask('git-task', { owner: 'fixture', leaseMs: 60_000 })
  store.startRound('git-task', lease.token)
  store.checkpoint('git-task', lease.token, { summary: 'base confirmada', nextAction: 'preparar patch' })
  return {
    root,
    repositoryRoot,
    baseSha,
    databasePath,
    store,
    lease,
    cleanup() {
      store.close()
      rmSync(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 })
    },
  }
}

function candidatePatch(repositoryRoot) {
  const before = git(repositoryRoot, ['hash-object', 'work.txt'])
  const after = git(repositoryRoot, ['hash-object', '--stdin'], { input: 'candidate\n' })
  return `diff --git a/work.txt b/work.txt
index ${before}..${after} 100644
--- a/work.txt
+++ b/work.txt
@@ -1 +1 @@
-base
+candidate
`
}

test('creates a local candidate commit without changing HEAD or the working tree', () => {
  const fx = fixture()
  const calls = []
  try {
    const hookMarker = join(fx.root, 'hook-was-invoked.txt')
    const hook = join(fx.repositoryRoot, '.git', 'hooks', 'reference-transaction')
    writeFileSync(hook, `#!/bin/sh\nprintf invoked > '${hookMarker.replaceAll('\\', '/')}'\n`)
    chmodSync(hook, 0o755)
    const patch = candidatePatch(fx.repositoryRoot)
    const result = createGitCandidate({
      store: fx.store,
      taskId: 'git-task',
      leaseToken: fx.lease.token,
      key: 'candidate-work',
      repositoryRoot: fx.repositoryRoot,
      baseSha: fx.baseSha,
      patch,
      gitExec(request) {
        calls.push(request.args)
        return executeGit(request)
      },
    })
    assert.equal(result.effect.status, 'COMMITTED')
    assert.equal(git(fx.repositoryRoot, ['rev-parse', 'HEAD']), fx.baseSha)
    assert.equal(readFileSync(join(fx.repositoryRoot, 'work.txt'), 'utf8'), 'base\n')
    assert.equal(git(fx.repositoryRoot, ['status', '--porcelain']), '')
    assert.equal(git(fx.repositoryRoot, ['show', `${result.commitSha}:work.txt`]), 'candidate')
    assert.equal(git(fx.repositoryRoot, ['rev-parse', result.branch]), result.commitSha)
    assert.equal(existsSync(hookMarker), false, 'repository hooks must stay disabled')
    assert.ok(calls.every(args => !['push', 'reset', 'merge', 'rebase', 'checkout', 'switch'].includes(args[0])))

    const repeated = createGitCandidate({
      store: fx.store,
      taskId: 'git-task',
      leaseToken: fx.lease.token,
      key: 'candidate-work',
      repositoryRoot: fx.repositoryRoot,
      baseSha: fx.baseSha,
      patch,
    })
    assert.equal(repeated.reused, true)
    assert.equal(repeated.commitSha, result.commitSha)
    assert.equal(fx.store.listEffects('git-task').length, 1)
  }
  finally {
    fx.cleanup()
  }
})

test('divergent base blocks instead of overwriting newer work', () => {
  const fx = fixture()
  try {
    const patch = candidatePatch(fx.repositoryRoot)
    writeFileSync(join(fx.repositoryRoot, 'new.txt'), 'newer\n')
    git(fx.repositoryRoot, ['add', 'new.txt'])
    git(fx.repositoryRoot, ['commit', '-m', 'newer base'])
    assert.throws(
      () => createGitCandidate({
        store: fx.store,
        taskId: 'git-task',
        leaseToken: fx.lease.token,
        key: 'stale-base',
        repositoryRoot: fx.repositoryRoot,
        baseSha: fx.baseSha,
        patch,
      }),
      error => error?.code === 'GIT_BASE_DIVERGED',
    )
    assert.equal(git(fx.repositoryRoot, ['branch', '--list', 'pemara/candidate/*']), '')
  }
  finally {
    fx.cleanup()
  }
})

test('dirty worktree blocks candidate creation without touching user changes', () => {
  const fx = fixture()
  try {
    const patch = candidatePatch(fx.repositoryRoot)
    writeFileSync(join(fx.repositoryRoot, 'work.txt'), 'user change\n')
    assert.throws(
      () => createGitCandidate({
        store: fx.store,
        taskId: 'git-task',
        leaseToken: fx.lease.token,
        key: 'dirty',
        repositoryRoot: fx.repositoryRoot,
        baseSha: fx.baseSha,
        patch,
      }),
      error => error?.code === 'GIT_WORKTREE_DIRTY',
    )
    assert.equal(readFileSync(join(fx.repositoryRoot, 'work.txt'), 'utf8'), 'user change\n')
  }
  finally {
    fx.cleanup()
  }
})

test('crash after ref publication reconciles the exact candidate commit', () => {
  const fx = fixture()
  try {
    const patch = candidatePatch(fx.repositoryRoot)
    assert.throws(
      () => createGitCandidate({
        store: fx.store,
        taskId: 'git-task',
        leaseToken: fx.lease.token,
        key: 'crash-after-ref',
        repositoryRoot: fx.repositoryRoot,
        baseSha: fx.baseSha,
        patch,
        fault(step) { if (step === 'after-ref') throw new Error('queda após ref') },
      }),
      /queda após ref/,
    )
    const effect = fx.store.listEffects('git-task')[0]
    fx.store.recover()
    const result = reconcileGitCandidate({
      store: fx.store,
      effectId: effect.id,
      repositoryRoot: fx.repositoryRoot,
      resolver: 'host-test',
      evidence: ['ref, parent e trailers inspecionados'],
    })
    assert.equal(result.status, 'committed-by-ref')
    assert.equal(result.effect.status, 'COMMITTED')
    assert.equal(git(fx.repositoryRoot, ['rev-parse', result.branch]), result.commitSha)
    assert.equal(git(fx.repositoryRoot, ['rev-parse', 'HEAD']), fx.baseSha)
  }
  finally {
    fx.cleanup()
  }
})
