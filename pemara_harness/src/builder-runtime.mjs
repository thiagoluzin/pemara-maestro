import { createHash } from 'node:crypto'
import { existsSync, lstatSync, mkdirSync, readFileSync, realpathSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { isPathAllowed, isPathForbidden } from './builder-contract.mjs'
import {
  MAX_BUILDER_FILE_BYTES,
  normalizeBuilderPath,
  validateBuilderPackageV2,
} from './builder-contract-v2.mjs'
import { applyAtomicWrite } from './effects/filesystem.mjs'
import { runAllowlistedSubprocess } from './effects/subprocess.mjs'
import { HarnessStateError } from './index.mjs'

const NETWORK_GUARD = fileURLToPath(new URL('./effects/subprocess-network-guard.mjs', import.meta.url))

function builderError(code, message, details = undefined) {
  return new HarnessStateError(code, message, details)
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex')
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical)
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]))
  }
  return value
}

function digest(value) {
  return sha256(JSON.stringify(canonical(value)))
}

function within(root, candidate) {
  const left = process.platform === 'win32' ? root.toLowerCase() : root
  const right = process.platform === 'win32' ? candidate.toLowerCase() : candidate
  const rel = relative(left, right)
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

function safeFile(workspaceRoot, requested) {
  const path = normalizeBuilderPath(requested)
  if (path === undefined) throw builderError('BUILDER_PATH_DENIED', 'Path must be an exact relative file.')
  const root = realpathSync.native(resolve(workspaceRoot))
  const target = resolve(root, path)
  if (!within(root, target)) throw builderError('BUILDER_PATH_DENIED', `Path escapes the Builder worktree: ${path}`)
  let cursor = root
  for (const segment of relative(root, target).split(/[\\/]/u).filter(Boolean)) {
    cursor = resolve(cursor, segment)
    if (!existsSync(cursor)) break
    if (lstatSync(cursor).isSymbolicLink()) {
      throw builderError('BUILDER_LINK_DENIED', `Links are not allowed in Builder paths: ${path}`)
    }
  }
  return { root, target, path }
}

function inspectFile(workspaceRoot, path, { includeContent = false } = {}) {
  const safe = safeFile(workspaceRoot, path)
  if (!existsSync(safe.target)) return { ...safe, exists: false, sha256: null, bytes: 0 }
  const stat = lstatSync(safe.target)
  if (!stat.isFile()) throw builderError('BUILDER_TARGET_NOT_FILE', `Builder target is not a file: ${safe.path}`)
  if (stat.size > MAX_BUILDER_FILE_BYTES) {
    throw builderError('BUILDER_FILE_TOO_LARGE', `Builder file exceeds ${MAX_BUILDER_FILE_BYTES} bytes: ${safe.path}`)
  }
  const buffer = readFileSync(safe.target)
  if (includeContent && buffer.includes(0)) throw builderError('BUILDER_BINARY_DENIED', `Binary file denied: ${safe.path}`)
  return {
    ...safe,
    exists: true,
    sha256: sha256(buffer),
    bytes: buffer.length,
    ...(includeContent ? { content: buffer.toString('utf8') } : {}),
  }
}

export function readBuilderPackage(packagePath) {
  let pkg
  try { pkg = JSON.parse(readFileSync(resolve(packagePath), 'utf8')) } catch (error) {
    throw builderError('BUILDER_PACKAGE_READ_FAILED', `Cannot read Builder package: ${error.message}`)
  }
  const result = validateBuilderPackageV2(pkg)
  if (!result.valid) throw builderError('BUILDER_PACKAGE_REJECTED', 'Builder v2 package failed validation.', { issues: result.issues })
  return Object.freeze(pkg)
}

export function verifyBuilderBaselines(workspaceRoot, pkg) {
  const violations = []
  for (const path of pkg.allowed_paths) {
    const actual = inspectFile(workspaceRoot, path).sha256
    const expected = pkg.file_baselines[path]
    if (actual !== expected) violations.push({ path, expected, actual })
  }
  return violations
}

export function expectedBuilderHashes(pkg, effects = []) {
  const expected = { ...pkg.file_baselines }
  const issues = []
  for (const effect of effects) {
    if (effect.kind !== 'filesystem.atomic-write') continue
    const path = normalizeBuilderPath(effect.request?.relativePath)
    if (path === undefined || !Object.hasOwn(expected, path)) {
      issues.push({ code: 'BUILDER_EFFECT_PATH_DRIFT', effectId: effect.id, path })
      continue
    }
    if (effect.status === 'STARTED' || effect.status === 'OUTCOME_UNKNOWN') {
      issues.push({ code: 'BUILDER_EFFECT_RECONCILIATION_REQUIRED', effectId: effect.id, path })
      continue
    }
    if (effect.status !== 'COMMITTED') continue
    const previous = effect.request?.expectedPreviousSha256 ?? null
    const desired = effect.request?.desiredSha256
    const result = effect.result?.sha256
    if (previous !== expected[path] || typeof desired !== 'string' || result !== desired) {
      issues.push({
        code: 'BUILDER_EFFECT_CHAIN_INVALID',
        effectId: effect.id,
        path,
        expectedPrevious: expected[path],
        journaledPrevious: previous,
        desired,
        result,
      })
      continue
    }
    expected[path] = result
  }
  return Object.freeze({ expected: Object.freeze(expected), issues: Object.freeze(issues) })
}

export function verifyBuilderWorkspaceState(workspaceRoot, pkg, effects = []) {
  const history = expectedBuilderHashes(pkg, effects)
  const violations = [...history.issues]
  for (const path of pkg.allowed_paths) {
    const actual = inspectFile(workspaceRoot, path).sha256
    const expected = history.expected[path]
    if (actual !== expected) violations.push({ code: 'BUILDER_WORKSPACE_DRIFT', path, expected, actual })
  }
  return violations
}

function commandMap(workspaceRoot, pkg) {
  return Object.fromEntries(pkg.command_allowlist.map(command => [command.id, {
    executable: process.execPath,
    args: [
      '--permission',
      `--allow-fs-read=${workspaceRoot}`,
      `--allow-fs-read=${NETWORK_GUARD}`,
      '--import', pathToFileURL(NETWORK_GUARD).href,
      ...(command.args[0] === '--test' ? ['--test-isolation=none'] : []),
      ...command.args,
    ],
    cwd: command.cwd === '.' ? workspaceRoot : resolve(workspaceRoot, command.cwd),
    timeoutMs: command.timeout_ms,
    maxOutputBytes: command.max_output_bytes,
    env: {},
  }]))
}

export class BuilderRuntime {
  #store
  #workspace
  #pkg
  #commands
  #scratchRoot

  constructor({ store, packagePath, workspaceRoot } = {}) {
    if (store === null || typeof store?.listEffects !== 'function') {
      throw builderError('INVALID_CONFIG', 'Builder runtime requires a DurableTaskStore.')
    }
    this.#store = store
    this.#workspace = realpathSync.native(resolve(workspaceRoot))
    this.#pkg = readBuilderPackage(packagePath)
    const existing = store.listTasks().find(task => task.id === this.#pkg.task_id)
    if (existing !== undefined
      && (existing.objective !== this.#pkg.objective || existing.maxRounds !== this.#pkg.max_rounds)) {
      throw builderError('BUILDER_TASK_DRIFT', 'Durable task identity differs from the Builder package.', {
        task: { id: existing.id, objective: existing.objective, maxRounds: existing.maxRounds },
      })
    }
    const effects = existing === undefined ? [] : store.listEffects(this.#pkg.task_id)
    const violations = verifyBuilderWorkspaceState(this.#workspace, this.#pkg, effects)
    if (violations.length > 0) {
      const reconciliation = violations.some(item => item.code === 'BUILDER_EFFECT_RECONCILIATION_REQUIRED')
      throw builderError(
        reconciliation ? 'BUILDER_EFFECT_RECONCILIATION_REQUIRED' : 'BUILDER_BASELINE_MISMATCH',
        reconciliation
          ? 'Builder has an uncertain effect that requires host reconciliation.'
          : 'Builder worktree does not match its durable expected state.',
        { violations },
      )
    }
    this.#commands = commandMap(this.#workspace, this.#pkg)
    this.#scratchRoot = join(
      tmpdir(),
      'pemara-builder-scratch',
      digest({ databasePath: store.databasePath, taskId: this.#pkg.task_id }),
    )
  }

  get taskId() { return this.#pkg.task_id }
  get package() { return this.#pkg }

  #assertTask(taskId) {
    if (taskId !== this.#pkg.task_id) {
      throw builderError('BUILDER_TASK_SCOPE', `Builder package belongs to ${this.#pkg.task_id}.`)
    }
  }

  #assertPath(path) {
    const normalized = normalizeBuilderPath(path)
    if (normalized === undefined
      || !isPathAllowed(normalized, this.#pkg.allowed_paths)
      || isPathForbidden(normalized, this.#pkg.forbidden_paths)) {
      throw builderError('BUILDER_PATH_DENIED', `Path is outside the Builder contract: ${String(path)}`)
    }
    return normalized
  }

  readFile(taskId, path) {
    this.#assertTask(taskId)
    const normalized = this.#assertPath(path)
    const inspected = inspectFile(this.#workspace, normalized, { includeContent: true })
    return Object.freeze({
      path: normalized,
      exists: inspected.exists,
      sha256: inspected.sha256,
      bytes: inspected.bytes,
      ...(inspected.exists ? { content: inspected.content } : {}),
    })
  }

  writeFile(taskId, leaseToken, { path, content }) {
    this.#assertTask(taskId)
    const normalized = this.#assertPath(path)
    if (typeof content !== 'string' || Buffer.byteLength(content) > MAX_BUILDER_FILE_BYTES) {
      throw builderError('BUILDER_CONTENT_INVALID', `content must be text up to ${MAX_BUILDER_FILE_BYTES} bytes.`)
    }
    const effects = this.#store.listEffects(taskId)
    const occupiedPaths = new Set(effects
      .filter(effect => effect.kind === 'filesystem.atomic-write' && effect.status !== 'FAILED')
      .map(effect => effect.request.relativePath))
    if (!occupiedPaths.has(normalized) && occupiedPaths.size >= this.#pkg.max_files_changed) {
      throw builderError('BUILDER_FILE_BUDGET', `Builder reached its ${this.#pkg.max_files_changed}-file budget.`)
    }
    const priorWrites = effects
      .filter(effect => effect.kind === 'filesystem.atomic-write'
        && effect.request.relativePath === normalized
        && effect.status === 'COMMITTED')
    const expected = priorWrites.at(-1)?.result?.sha256 ?? this.#pkg.file_baselines[normalized]
    const desired = sha256(Buffer.from(content, 'utf8'))
    return applyAtomicWrite({
      store: this.#store,
      taskId,
      leaseToken,
      key: `builder-write:${normalized}:${desired}`,
      workspaceRoot: this.#workspace,
      relativePath: normalized,
      content,
      expectedPreviousSha256: expected,
    })
  }

  async runTest(taskId, leaseToken, commandId, options = {}) {
    this.#assertTask(taskId)
    if (typeof commandId !== 'string' || this.#commands[commandId] === undefined) {
      throw builderError('BUILDER_COMMAND_DENIED', `Command is outside the Builder contract: ${String(commandId)}`)
    }
    const state = Object.fromEntries(this.#pkg.allowed_paths.slice().sort()
      .map(path => [path, inspectFile(this.#workspace, path).sha256]))
    const stateFingerprint = digest(state)
    const command = this.#commands[commandId]
    const scratch = join(this.#scratchRoot, commandId, stateFingerprint)
    mkdirSync(scratch, { recursive: true })
    const importIndex = command.args.indexOf('--import')
    if (importIndex < 0) throw builderError('BUILDER_COMMAND_INVALID', 'Protected network preload is missing.')
    const commands = {
      [commandId]: {
        ...command,
        args: [
          ...command.args.slice(0, importIndex),
          `--allow-fs-read=${scratch}`,
          `--allow-fs-write=${scratch}`,
          ...command.args.slice(importIndex),
        ],
        env: { ...command.env, TEMP: scratch, TMP: scratch, TMPDIR: scratch },
      },
    }
    return runAllowlistedSubprocess({
      store: this.#store,
      taskId,
      leaseToken,
      key: `builder-test:${commandId}:${stateFingerprint}`,
      commandId,
      workspaceRoot: this.#workspace,
      commands,
      ...options,
    })
  }
}
