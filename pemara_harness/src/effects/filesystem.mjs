import { createHash } from 'node:crypto'
import {
  closeSync,
  existsSync,
  fsyncSync,
  lstatSync,
  mkdirSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from 'node:fs'
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path'

import { HarnessStateError } from '../index.mjs'

function filesystemError(code, message, details = undefined) {
  return new HarnessStateError(code, message, details)
}

function requiredText(value, field) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw filesystemError('INVALID_INPUT', `${field} must be a non-empty string.`)
  }
  return value.trim()
}

function normalizedHash(value, field) {
  if (value === null) return null
  if (typeof value !== 'string' || !/^[a-fA-F0-9]{64}$/.test(value)) {
    throw filesystemError('INVALID_INPUT', `${field} must be null or a SHA256 hex digest.`)
  }
  return value.toLowerCase()
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

function pathKey(path) {
  return process.platform === 'win32' ? path.toLowerCase() : path
}

function within(root, candidate) {
  const rel = relative(pathKey(root), pathKey(candidate))
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

function assertLinkContained(root, candidate) {
  const resolvedLink = realpathSync.native(candidate)
  if (!within(root, resolvedLink)) {
    throw filesystemError('FILESYSTEM_PATH_ESCAPE', `Link escapes workspace: ${candidate}`, {
      workspaceRoot: root,
      resolvedLink,
    })
  }
  throw filesystemError(
    'FILESYSTEM_LINK_UNSUPPORTED',
    `Atomic writes through links are not supported: ${candidate}`,
  )
}

function inspectExistingPath(root, candidate) {
  const rel = relative(root, candidate)
  let cursor = root
  for (const segment of rel.split(/[\\/]/u).filter(Boolean)) {
    cursor = resolve(cursor, segment)
    if (!existsSync(cursor)) break
    const stat = lstatSync(cursor)
    if (stat.isSymbolicLink()) assertLinkContained(root, cursor)
  }
}

function safeTarget(workspaceRoot, relativePath, { parentMustExist = true } = {}) {
  const rootInput = requiredText(workspaceRoot, 'workspaceRoot')
  const requested = requiredText(relativePath, 'relativePath')
  if (!isAbsolute(rootInput)) throw filesystemError('INVALID_INPUT', 'workspaceRoot must be absolute.')
  if (isAbsolute(requested)) {
    throw filesystemError('FILESYSTEM_PATH_ESCAPE', 'relativePath must not be absolute.')
  }
  const root = realpathSync.native(resolve(rootInput))
  const target = resolve(root, requested)
  if (!within(root, target)) {
    throw filesystemError('FILESYSTEM_PATH_ESCAPE', `Path escapes workspace: ${requested}`)
  }
  inspectExistingPath(root, target)
  const parent = dirname(target)
  if (parentMustExist && !existsSync(parent)) {
    throw filesystemError('FILESYSTEM_PARENT_MISSING', `Parent directory does not exist: ${parent}`)
  }
  if (existsSync(parent)) {
    const realParent = realpathSync.native(parent)
    if (!within(root, realParent)) {
      throw filesystemError('FILESYSTEM_PATH_ESCAPE', `Parent escapes workspace: ${requested}`)
    }
  }
  return Object.freeze({
    root,
    target,
    parent,
    relativePath: relative(root, target).split(sep).join('/'),
  })
}

function fileHash(path) {
  if (!existsSync(path)) return null
  const stat = lstatSync(path)
  if (stat.isSymbolicLink()) throw filesystemError('FILESYSTEM_LINK_UNSUPPORTED', `Target is a link: ${path}`)
  if (!stat.isFile()) throw filesystemError('FILESYSTEM_TARGET_NOT_FILE', `Target is not a file: ${path}`)
  return sha256(readFileSync(path))
}

function assertPrecondition(target, expectedPreviousSha256) {
  const actual = fileHash(target)
  if (actual !== expectedPreviousSha256) {
    throw filesystemError(
      'FILESYSTEM_PRECONDITION_FAILED',
      `Target changed before the atomic write: ${target}`,
      { expected: expectedPreviousSha256, actual },
    )
  }
  return actual
}

function normalizeEvidence(evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0
    || evidence.some(item => typeof item !== 'string' || item.trim() === '')) {
    throw filesystemError('INVALID_INPUT', 'evidence must contain at least one non-empty string.')
  }
  return evidence.map(item => item.trim())
}

/**
 * Write one file through a same-directory temporary and a single rename.
 * The caller must provide the exact prior hash (or null for an absent file),
 * making overwrites of concurrent user work fail closed.
 */
export function applyAtomicWrite({
  store,
  taskId,
  leaseToken,
  key,
  workspaceRoot,
  relativePath,
  content,
  expectedPreviousSha256,
  createParents = false,
  fault = () => {},
} = {}) {
  if (store === null || typeof store?.prepareEffect !== 'function') {
    throw filesystemError('INVALID_INPUT', 'store must be a DurableTaskStore.')
  }
  if (typeof createParents !== 'boolean') throw filesystemError('INVALID_INPUT', 'createParents must be boolean.')
  if (typeof fault !== 'function') throw filesystemError('INVALID_INPUT', 'fault must be a function.')
  const payload = Buffer.isBuffer(content)
    ? Buffer.from(content)
    : typeof content === 'string'
      ? Buffer.from(content, 'utf8')
      : undefined
  if (payload === undefined) throw filesystemError('INVALID_INPUT', 'content must be a string or Buffer.')
  const expected = normalizedHash(expectedPreviousSha256, 'expectedPreviousSha256')
  const path = safeTarget(workspaceRoot, relativePath, { parentMustExist: !createParents })
  const desiredSha256 = sha256(payload)
  const request = {
    relativePath: path.relativePath,
    expectedPreviousSha256: expected,
    desiredSha256,
    contentBytes: payload.length,
    createParents,
  }
  const effect = store.prepareEffect(taskId, leaseToken, {
    key,
    kind: 'filesystem.atomic-write',
    request,
  })
  if (effect.status === 'COMMITTED') {
    const actual = fileHash(path.target)
    if (actual !== desiredSha256) {
      throw filesystemError('FILESYSTEM_COMMITTED_DRIFT', 'Committed file no longer matches its journaled hash.', {
        path: path.target,
        expected: desiredSha256,
        actual,
      })
    }
    return Object.freeze({ effect, path: path.target, sha256: actual, reused: true })
  }
  if (effect.status !== 'PREPARED') {
    throw filesystemError('FILESYSTEM_EFFECT_IN_PROGRESS', `Filesystem effect is ${effect.status}.`, {
      effectId: effect.id,
    })
  }

  assertPrecondition(path.target, expected)
  store.markEffectStarted(taskId, leaseToken, effect.id)
  if (createParents) mkdirSync(path.parent, { recursive: true })
  const checked = safeTarget(workspaceRoot, relativePath)
  assertPrecondition(checked.target, expected)
  const temporary = `${checked.target}.pemara-${effect.id}.tmp`
  let descriptor
  try {
    descriptor = openSync(temporary, 'wx')
    writeFileSync(descriptor, payload)
    fsyncSync(descriptor)
  }
  finally {
    if (descriptor !== undefined) closeSync(descriptor)
  }
  fault('after-temp', { effectId: effect.id, temporary, target: checked.target })
  renameSync(temporary, checked.target)
  fault('after-rename', { effectId: effect.id, temporary, target: checked.target })
  const actual = fileHash(checked.target)
  if (actual !== desiredSha256) {
    throw filesystemError('FILESYSTEM_POSTCONDITION_FAILED', 'Atomic rename did not produce the desired hash.', {
      expected: desiredSha256,
      actual,
    })
  }
  const committed = store.commitEffect(taskId, leaseToken, effect.id, {
    relativePath: checked.relativePath,
    sha256: actual,
    bytes: payload.length,
  })
  return Object.freeze({ effect: committed, path: checked.target, sha256: actual, reused: false })
}

/** Reconcile a recovered OUTCOME_UNKNOWN write from target/temp hashes only. */
export function reconcileAtomicWrite({
  store,
  effectId,
  workspaceRoot,
  resolver,
  evidence,
} = {}) {
  if (store === null || typeof store?.getEffect !== 'function') {
    throw filesystemError('INVALID_INPUT', 'store must be a DurableTaskStore.')
  }
  const proof = normalizeEvidence(evidence)
  const effect = store.getEffect(requiredText(effectId, 'effectId'))
  if (effect.kind !== 'filesystem.atomic-write') {
    throw filesystemError('FILESYSTEM_EFFECT_KIND', `Effect ${effect.id} is ${effect.kind}.`)
  }
  if (effect.status !== 'OUTCOME_UNKNOWN') {
    throw filesystemError('EFFECT_NOT_UNCERTAIN', `Effect ${effect.id} is ${effect.status}.`)
  }
  const path = safeTarget(workspaceRoot, effect.request.relativePath, { parentMustExist: false })
  const temporary = `${path.target}.pemara-${effect.id}.tmp`
  const targetSha256 = fileHash(path.target)
  const temporarySha256 = fileHash(temporary)
  const desired = effect.request.desiredSha256
  const previous = effect.request.expectedPreviousSha256
  const inspection = { targetSha256, temporarySha256, desiredSha256: desired, previousSha256: previous }

  if (targetSha256 === desired) {
    const resolved = store.resolveEffect(effect.id, {
      resolver,
      outcome: 'committed',
      evidence: [...proof, `target sha256=${targetSha256}`],
      result: {
        relativePath: path.relativePath,
        sha256: targetSha256,
        reconciled: true,
      },
    })
    return Object.freeze({ status: 'committed-by-hash', effect: resolved.effect, path: path.target, ...inspection })
  }

  const targetStillPrevious = targetSha256 === previous
  const candidateValid = temporarySha256 === null || temporarySha256 === desired
  if (targetStillPrevious && candidateValid) {
    const resolved = store.resolveEffect(effect.id, {
      resolver,
      outcome: 'failed',
      evidence: [...proof, `target sha256=${String(targetSha256)}`, `temporary sha256=${String(temporarySha256)}`],
      result: {
        relativePath: path.relativePath,
        reconciled: true,
        reason: 'rename-not-observed',
        candidatePath: temporarySha256 === desired ? temporary : undefined,
      },
    })
    return Object.freeze({
      status: 'failed-before-rename',
      effect: resolved.effect,
      path: path.target,
      candidatePath: temporarySha256 === desired ? temporary : undefined,
      ...inspection,
    })
  }

  return Object.freeze({
    status: 'needs-human',
    effect,
    path: path.target,
    candidatePath: existsSync(temporary) ? temporary : undefined,
    ...inspection,
  })
}
