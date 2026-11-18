import { createHash, randomUUID } from 'node:crypto'
import { existsSync, realpathSync, unlinkSync } from 'node:fs'
import { isAbsolute, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { spawnSync } from 'node:child_process'

import { HarnessStateError } from '../index.mjs'

const ALLOWED_GIT_VERBS = new Set([
  'rev-parse', 'status', 'read-tree', 'apply', 'write-tree',
  'commit-tree', 'show-ref', 'update-ref', 'show',
])
const ZERO_SHA1 = '0'.repeat(40)
const DISABLED_HOOKS_PATH = join(tmpdir(), `pemara-git-hooks-disabled-${process.pid}-${randomUUID()}`)
const DISABLED_GLOBAL_CONFIG = join(tmpdir(), `pemara-git-config-disabled-${process.pid}-${randomUUID()}`)

function gitError(code, message, details = undefined) {
  return new HarnessStateError(code, message, details)
}

function requiredText(value, field) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw gitError('INVALID_INPUT', `${field} must be a non-empty string.`)
  }
  return value.trim()
}

function hash(value) {
  return createHash('sha256').update(value).digest('hex')
}

function pathKey(path) {
  return process.platform === 'win32' ? path.toLowerCase() : path
}

function normalizeEvidence(evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0
    || evidence.some(item => typeof item !== 'string' || item.trim() === '')) {
    throw gitError('INVALID_INPUT', 'evidence must contain at least one non-empty string.')
  }
  return evidence.map(item => item.trim())
}

/** Execute one internal, allowlisted Git plumbing command without a shell. */
export function executeGit({
  executable = 'git',
  repositoryRoot,
  args,
  input,
  env,
  allowExitCodes = [0],
} = {}) {
  const program = requiredText(executable, 'git executable')
  const root = requiredText(repositoryRoot, 'repositoryRoot')
  if (!Array.isArray(args) || args.length === 0 || args.some(argument => typeof argument !== 'string')) {
    throw gitError('INVALID_INPUT', 'Git args must be a non-empty array of strings.')
  }
  if (!ALLOWED_GIT_VERBS.has(args[0])) {
    throw gitError('GIT_COMMAND_DENIED', `Git command "${args[0]}" is not allowed.`)
  }
  const baseEnvironment = Object.fromEntries(Object.entries(process.env)
    .filter(([key]) => !key.toUpperCase().startsWith('GIT_')))
  const result = spawnSync(program, ['-C', root, ...args], {
    encoding: 'utf8',
    windowsHide: true,
    shell: false,
    input,
    env: {
      ...baseEnvironment,
      ...env,
      GIT_CONFIG_NOSYSTEM: '1',
      GIT_CONFIG_GLOBAL: DISABLED_GLOBAL_CONFIG,
      GIT_TERMINAL_PROMPT: '0',
      GCM_INTERACTIVE: 'never',
      GIT_CONFIG_COUNT: '3',
      GIT_CONFIG_KEY_0: 'core.hooksPath',
      GIT_CONFIG_VALUE_0: DISABLED_HOOKS_PATH,
      GIT_CONFIG_KEY_1: 'commit.gpgSign',
      GIT_CONFIG_VALUE_1: 'false',
      GIT_CONFIG_KEY_2: 'core.fsmonitor',
      GIT_CONFIG_VALUE_2: 'false',
    },
    maxBuffer: 8 * 1024 * 1024,
  })
  if (result.error !== undefined) {
    throw gitError('GIT_EXEC_FAILED', result.error.message, { args })
  }
  if (!allowExitCodes.includes(result.status)) {
    throw gitError('GIT_COMMAND_FAILED', `git ${args[0]} exited with ${String(result.status)}.`, {
      args,
      exitCode: result.status,
      stderr: result.stderr.trim(),
    })
  }
  return Object.freeze({
    status: result.status,
    stdout: result.stdout,
    stderr: result.stderr,
  })
}

function run(gitExec, executable, repositoryRoot, args, options = {}) {
  return gitExec({ executable, repositoryRoot, args, ...options })
}

function output(gitExec, executable, repositoryRoot, args, options = {}) {
  return run(gitExec, executable, repositoryRoot, args, options).stdout.trim()
}

function repository(repositoryRoot, gitExecutable, gitExec) {
  const rootInput = requiredText(repositoryRoot, 'repositoryRoot')
  if (!isAbsolute(rootInput)) throw gitError('INVALID_INPUT', 'repositoryRoot must be absolute.')
  const root = realpathSync.native(resolve(rootInput))
  const top = output(gitExec, gitExecutable, root, ['rev-parse', '--show-toplevel'])
  const realTop = realpathSync.native(resolve(top))
  if (pathKey(realTop) !== pathKey(root)) {
    throw gitError('GIT_ROOT_MISMATCH', 'repositoryRoot must be the exact Git worktree root.', {
      requested: root,
      actual: realTop,
    })
  }
  return root
}

function branchName(taskId, key) {
  const task = requiredText(taskId, 'taskId').replaceAll(/[^a-zA-Z0-9._-]+/gu, '-').slice(0, 80)
  return `pemara/candidate/${task}/${hash(requiredText(key, 'key')).slice(0, 16)}`
}

function branchRef(branch) {
  return `refs/heads/${branch}`
}

function resolveBase(gitExec, gitExecutable, root, baseSha) {
  const requested = requiredText(baseSha, 'baseSha')
  try {
    return output(gitExec, gitExecutable, root, ['rev-parse', '--verify', `${requested}^{commit}`])
  }
  catch (error) {
    throw gitError('GIT_BASE_INVALID', `Base commit does not exist: ${requested}`, {
      cause: error instanceof Error ? error.message : String(error),
    })
  }
}

function refValue(gitExec, gitExecutable, root, ref) {
  const result = run(gitExec, gitExecutable, root, ['rev-parse', '--verify', '--quiet', `${ref}^{commit}`], {
    allowExitCodes: [0, 1],
  })
  return result.status === 0 ? result.stdout.trim() : undefined
}

function assertRepositoryReady(gitExec, gitExecutable, root, base) {
  const head = output(gitExec, gitExecutable, root, ['rev-parse', '--verify', 'HEAD'])
  if (head !== base) {
    throw gitError('GIT_BASE_DIVERGED', 'Repository HEAD no longer matches the approved base.', {
      expected: base,
      actual: head,
    })
  }
  const status = output(gitExec, gitExecutable, root, ['status', '--porcelain=v1', '--untracked-files=all'])
  if (status !== '') {
    throw gitError('GIT_WORKTREE_DIRTY', 'Repository has user changes; candidate creation is blocked.', {
      status: status.split(/\r?\n/u).slice(0, 50),
    })
  }
}

function verifyCommittedEffect(effect, root, gitExecutable, gitExec) {
  const commitSha = effect.result?.commitSha
  const branch = effect.result?.branch
  if (typeof commitSha !== 'string' || typeof branch !== 'string') {
    throw gitError('GIT_COMMITTED_RESULT_INVALID', 'Committed Git effect lacks branch or commit SHA.')
  }
  const actual = refValue(gitExec, gitExecutable, root, branchRef(branch))
  if (actual !== commitSha) {
    throw gitError('GIT_COMMITTED_DRIFT', 'Candidate branch no longer points to its committed result.', {
      expected: commitSha,
      actual,
      branch,
    })
  }
  return Object.freeze({
    effect,
    branch,
    commitSha,
    baseSha: effect.request.baseSha,
    patchSha256: effect.request.patchSha256,
    reused: true,
  })
}

/**
 * Build a deterministic local candidate commit through a temporary index.
 * HEAD and the working tree are never switched or modified.
 */
export function createGitCandidate({
  store,
  taskId,
  leaseToken,
  key,
  repositoryRoot,
  baseSha,
  patch,
  gitExecutable = 'git',
  gitExec = executeGit,
  fault = () => {},
} = {}) {
  if (store === null || typeof store?.prepareEffect !== 'function') {
    throw gitError('INVALID_INPUT', 'store must be a DurableTaskStore.')
  }
  if (typeof gitExec !== 'function' || typeof fault !== 'function') {
    throw gitError('INVALID_INPUT', 'gitExec and fault must be functions.')
  }
  if (typeof patch !== 'string' || patch.trim() === '') {
    throw gitError('INVALID_INPUT', 'patch must be a non-empty string.')
  }
  const patchText = patch.endsWith('\n') ? patch : `${patch}\n`
  if (Buffer.byteLength(patchText, 'utf8') > 4 * 1024 * 1024) {
    throw gitError('GIT_PATCH_TOO_LARGE', 'Patch exceeds the 4 MiB candidate limit.')
  }
  const root = repository(repositoryRoot, gitExecutable, gitExec)
  const base = resolveBase(gitExec, gitExecutable, root, baseSha)
  assertRepositoryReady(gitExec, gitExecutable, root, base)
  const branch = branchName(taskId, key)
  const patchSha256 = hash(patchText)
  const request = {
    repositoryRoot: root,
    baseSha: base,
    patchSha256,
    branch,
  }
  const effect = store.prepareEffect(taskId, leaseToken, {
    key,
    kind: 'git.local-candidate',
    request,
  })
  if (effect.status === 'COMMITTED') {
    return verifyCommittedEffect(effect, root, gitExecutable, gitExec)
  }
  if (effect.status !== 'PREPARED') {
    throw gitError('GIT_EFFECT_IN_PROGRESS', `Git effect is ${effect.status}.`, { effectId: effect.id })
  }
  store.markEffectStarted(taskId, leaseToken, effect.id)

  const indexRaw = output(gitExec, gitExecutable, root, ['rev-parse', '--git-path', 'index'])
  const indexPath = isAbsolute(indexRaw) ? indexRaw : resolve(root, indexRaw)
  const temporaryIndex = `${indexPath}.pemara-${effect.id}.tmp`
  if (existsSync(temporaryIndex)) {
    throw gitError('GIT_TEMP_INDEX_EXISTS', `Temporary candidate index already exists: ${temporaryIndex}`)
  }
  const seconds = Math.floor(effect.createdAt / 1000)
  const identityEnv = {
    GIT_INDEX_FILE: temporaryIndex,
    GIT_AUTHOR_NAME: 'Pemara Candidate Adapter',
    GIT_AUTHOR_EMAIL: 'candidate@pemara.invalid',
    GIT_COMMITTER_NAME: 'Pemara Candidate Adapter',
    GIT_COMMITTER_EMAIL: 'candidate@pemara.invalid',
    GIT_AUTHOR_DATE: `@${seconds} +0000`,
    GIT_COMMITTER_DATE: `@${seconds} +0000`,
  }
  let commitSha
  try {
    run(gitExec, gitExecutable, root, ['read-tree', base], { env: identityEnv })
    run(gitExec, gitExecutable, root, ['apply', '--cached', '--whitespace=nowarn'], {
      env: identityEnv,
      input: patchText,
    })
    const tree = output(gitExec, gitExecutable, root, ['write-tree'], { env: identityEnv })
    const message = [
      `candidate: ${requiredText(taskId, 'taskId')}`,
      '',
      `Pemara-Effect: ${effect.id}`,
      `Pemara-Patch: ${patchSha256}`,
      '',
    ].join('\n')
    commitSha = output(gitExec, gitExecutable, root, ['commit-tree', tree, '-p', base], {
      env: identityEnv,
      input: message,
    })
    const ref = branchRef(branch)
    const existing = refValue(gitExec, gitExecutable, root, ref)
    if (existing !== undefined && existing !== commitSha) {
      throw gitError('GIT_CANDIDATE_REF_CONFLICT', `Candidate branch already points to another commit: ${branch}`, {
        existing,
        expected: commitSha,
      })
    }
    if (existing === undefined) {
      run(gitExec, gitExecutable, root, ['update-ref', ref, commitSha, ZERO_SHA1])
    }
    fault('after-ref', { effectId: effect.id, branch, commitSha })
  }
  finally {
    if (existsSync(temporaryIndex)) unlinkSync(temporaryIndex)
  }
  const committed = store.commitEffect(taskId, leaseToken, effect.id, {
    repositoryRoot: root,
    branch,
    commitSha,
    baseSha: base,
    patchSha256,
  })
  return Object.freeze({
    effect: committed,
    branch,
    commitSha,
    baseSha: base,
    patchSha256,
    reused: false,
  })
}

/** Reconcile an uncertain candidate strictly from its local ref and trailers. */
export function reconcileGitCandidate({
  store,
  effectId,
  repositoryRoot,
  resolver,
  evidence,
  gitExecutable = 'git',
  gitExec = executeGit,
} = {}) {
  if (store === null || typeof store?.getEffect !== 'function') {
    throw gitError('INVALID_INPUT', 'store must be a DurableTaskStore.')
  }
  const proof = normalizeEvidence(evidence)
  const effect = store.getEffect(requiredText(effectId, 'effectId'))
  if (effect.kind !== 'git.local-candidate') {
    throw gitError('GIT_EFFECT_KIND', `Effect ${effect.id} is ${effect.kind}.`)
  }
  if (effect.status !== 'OUTCOME_UNKNOWN') {
    throw gitError('EFFECT_NOT_UNCERTAIN', `Effect ${effect.id} is ${effect.status}.`)
  }
  const root = repository(repositoryRoot, gitExecutable, gitExec)
  if (pathKey(root) !== pathKey(realpathSync.native(effect.request.repositoryRoot))) {
    throw gitError('GIT_ROOT_MISMATCH', 'Reconciliation repository differs from the journaled root.')
  }
  const branch = effect.request.branch
  const ref = branchRef(branch)
  const commitSha = refValue(gitExec, gitExecutable, root, ref)
  if (commitSha === undefined) {
    const resolved = store.resolveEffect(effect.id, {
      resolver,
      outcome: 'failed',
      evidence: [...proof, `ref ausente: ${ref}`],
      result: { branch, baseSha: effect.request.baseSha, patchSha256: effect.request.patchSha256, reconciled: true },
    })
    return Object.freeze({ status: 'failed-before-ref', effect: resolved.effect, branch })
  }
  const parent = output(gitExec, gitExecutable, root, ['rev-parse', '--verify', `${commitSha}^`])
  const message = output(gitExec, gitExecutable, root, ['show', '-s', '--format=%B', commitSha])
  const valid = parent === effect.request.baseSha
    && message.includes(`Pemara-Effect: ${effect.id}`)
    && message.includes(`Pemara-Patch: ${effect.request.patchSha256}`)
  if (!valid) {
    return Object.freeze({
      status: 'needs-human',
      effect,
      branch,
      commitSha,
      parent,
    })
  }
  const resolved = store.resolveEffect(effect.id, {
    resolver,
    outcome: 'committed',
    evidence: [...proof, `ref=${ref}`, `commit=${commitSha}`, `parent=${parent}`],
    result: {
      repositoryRoot: root,
      branch,
      commitSha,
      baseSha: parent,
      patchSha256: effect.request.patchSha256,
      reconciled: true,
    },
  })
  return Object.freeze({ status: 'committed-by-ref', effect: resolved.effect, branch, commitSha, parent })
}
