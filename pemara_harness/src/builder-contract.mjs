import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * Protected contract for the Qwen Builder ("pedreiro"), version 1.
 *
 * The host owns this module and its tests. A Builder task is a closed YAML
 * package; the validator below decides whether the package is admissible
 * before any worktree is handed over. Hashes of protected files are captured
 * by the host before delivery and re-verified after the Builder finishes, so
 * the worker can never edit the gate it is measured by.
 */

export const BUILDER_CONTRACT_VERSION = 1
export const CONTRACT_ID = 'qwen-builder-v1'

/* Budgets approved by the owner (plan open decision 3). */
export const MAX_ROUNDS_LIMIT = 6
export const MAX_FILES_CHANGED_LIMIT = 5
export const MAX_RESTARTS_LIMIT = 3
export const SKILL_COUNT_MIN = 3
export const SKILL_COUNT_MAX = 12
export const TASK_ID_PATTERN = /^QB-[0-9]{3}$/

/*
 * Minimum protected set. Every Builder package must forbid at least these
 * paths, and no allowed path may intersect them.
 */
export const MIN_PROTECTED_PATHS = Object.freeze([
  'RULES.md',
  'SPEC.md',
  'evidence/',
  'tasks/contracts/',
  'test/builder-contract.test.mjs',
  'scripts/check-protected.mjs',
])

/* Closed list of the model-facing tools the Builder profile may expose. */
export const EXPECTED_BUILDER_TOOLS = Object.freeze([
  'harness_task_create',
  'harness_task_get',
  'harness_task_begin_round',
  'harness_task_checkpoint',
  'harness_task_request_completion',
])

/* Substrings that must never appear in a Builder tool name. */
export const FORBIDDEN_TOOL_MARKERS = Object.freeze([
  { marker: 'verify', reason: 'promotion' },
  { marker: 'promote', reason: 'promotion' },
  { marker: 'web_', reason: 'network' },
  { marker: '_fetch', reason: 'network' },
  { marker: 'http', reason: 'network' },
  { marker: 'service', reason: 'service' },
  { marker: 'gpu', reason: 'gpu' },
  { marker: 'job_', reason: 'service' },
  { marker: 'subagent', reason: 'service' },
])

function normalizePath(value) {
  return value.replaceAll('\\', '/').replace(/^\.\//, '')
}

/**
 * True when `path` equals the entry or lies inside a directory entry.
 * Directory entries end with "/"; anything else is an exact file.
 */
export function pathMatchesEntry(path, entry) {
  const p = normalizePath(path)
  const e = normalizePath(entry)
  if (e.endsWith('/')) return p === e.slice(0, -1) || p.startsWith(e)
  return p === e
}

export function isPathAllowed(path, allowedPaths) {
  if (!Array.isArray(allowedPaths)) return false
  return allowedPaths.some(entry => pathMatchesEntry(path, entry))
}

export function isPathForbidden(path, forbiddenPaths) {
  if (!Array.isArray(forbiddenPaths)) return false
  return forbiddenPaths.some(entry => pathMatchesEntry(path, entry))
}

/**
 * An allowed directory that contains a forbidden file (or vice versa) is a
 * conflict: the Builder would be able to touch what the host protects.
 */
export function entriesIntersect(allowedPaths, forbiddenPaths) {
  for (const allowed of allowedPaths) {
    const a = normalizePath(allowed)
    if (isPathForbidden(a, forbiddenPaths)) return true
    if (a.endsWith('/')) {
      for (const forbidden of forbiddenPaths) {
        const f = normalizePath(forbidden)
        if (f.startsWith(a)) return true
      }
    }
  }
  return false
}

function nonEmptyStrings(value, field, { required = true } = {}) {
  if (value === undefined) return required ? 'missing' : null
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || item.trim() === '')) return 'type'
  return null
}

function positiveInt(value, field) {
  return Number.isSafeInteger(value) && value > 0
}

/**
 * Validate one closed Builder task package. Returns `{ valid, issues }` where
 * every issue carries a stable code so gates can assert on them.
 */
export function validateBuilderPackage(pkg) {
  if (pkg === null || typeof pkg !== 'object' || Array.isArray(pkg)) {
    return {
      valid: false,
      issues: [{ code: 'BUILDER_PACKAGE_INVALID', message: 'package must be a plain object.' }],
    }
  }

  const issues = []
  const fail = (code, message) => issues.push({ code, message })
  const knownKeys = new Set([
    'task_id', 'objective', 'allowed_paths', 'forbidden_paths', 'acceptance_commands',
    'required_artifacts', 'skills', 'max_rounds', 'max_files_changed', 'network',
    'service_control', 'gpu_control', 'commit_or_publish', 'stop_conditions',
  ])

  for (const key of Object.keys(pkg)) {
    if (!knownKeys.has(key)) fail('UNKNOWN_FIELD', `Unknown package field "${key}".`)
  }

  if (typeof pkg.task_id !== 'string' || !TASK_ID_PATTERN.test(pkg.task_id)) {
    fail('INVALID_TASK_ID', 'task_id must match QB-NNN.')
  }
  if (typeof pkg.objective !== 'string' || pkg.objective.trim() === '') {
    fail('INVALID_OBJECTIVE', 'objective must be a non-empty string.')
  }

  const allowedProblem = nonEmptyStrings(pkg.allowed_paths, 'allowed_paths')
  if (allowedProblem === 'missing') fail('MISSING_BUDGET', 'allowed_paths is required and must be a closed list.')
  else if (allowedProblem === 'type') fail('INVALID_ALLOWED_PATHS', 'allowed_paths must be a non-empty list of paths.')

  const forbiddenProblem = nonEmptyStrings(pkg.forbidden_paths, 'forbidden_paths')
  if (forbiddenProblem === 'missing') fail('MISSING_FORBIDDEN', 'forbidden_paths is required.')
  else if (forbiddenProblem === 'type') fail('INVALID_FORBIDDEN_PATHS', 'forbidden_paths must be a non-empty list of paths.')
  else {
    for (const protectedPath of MIN_PROTECTED_PATHS) {
      if (!pkg.forbidden_paths.some(entry => pathMatchesEntry(protectedPath, entry))) {
        fail('PROTECTED_SET_INCOMPLETE', `forbidden_paths must include "${protectedPath}".`)
      }
    }
  }

  if (allowedProblem === null && forbiddenProblem === null
    && entriesIntersect(pkg.allowed_paths, pkg.forbidden_paths)) {
    fail('ALLOWED_FORBIDDEN_INTERSECTION', 'allowed_paths and forbidden_paths must not intersect.')
  }

  for (const field of ['acceptance_commands', 'required_artifacts', 'stop_conditions']) {
    const problem = nonEmptyStrings(pkg[field], field)
    if (problem === 'missing') fail('MISSING_FIELD', `${field} is required.`)
    else if (problem === 'type') fail('INVALID_FIELD', `${field} must be a non-empty list of strings.`)
  }

  const skillsProblem = nonEmptyStrings(pkg.skills, 'skills')
  if (skillsProblem === 'missing') fail('MISSING_SKILLS', 'skills is required (3 to 12 names).')
  else if (skillsProblem === 'type') fail('INVALID_SKILLS', 'skills must be a list of non-empty strings.')
  else {
    const unique = new Set(pkg.skills)
    if (unique.size !== pkg.skills.length) fail('DUPLICATE_SKILLS', 'skills must be unique.')
    if (pkg.skills.length < SKILL_COUNT_MIN || pkg.skills.length > SKILL_COUNT_MAX) {
      fail('SKILLS_OUT_OF_RANGE', `skills must contain ${SKILL_COUNT_MIN} to ${SKILL_COUNT_MAX} names.`)
    }
  }

  if (pkg.max_rounds === undefined) fail('MISSING_BUDGET', 'max_rounds budget is required.')
  else if (!positiveInt(pkg.max_rounds)) fail('INVALID_BUDGET', 'max_rounds must be a positive integer.')
  else if (pkg.max_rounds > MAX_ROUNDS_LIMIT) fail('BUDGET_EXCEEDED', `max_rounds must not exceed ${MAX_ROUNDS_LIMIT}.`)

  if (pkg.max_files_changed === undefined) fail('MISSING_BUDGET', 'max_files_changed budget is required.')
  else if (!positiveInt(pkg.max_files_changed)) fail('INVALID_BUDGET', 'max_files_changed must be a positive integer.')
  else if (pkg.max_files_changed > MAX_FILES_CHANGED_LIMIT) {
    fail('BUDGET_EXCEEDED', `max_files_changed must not exceed ${MAX_FILES_CHANGED_LIMIT}.`)
  }

  for (const field of ['network', 'service_control', 'gpu_control', 'commit_or_publish']) {
    if (pkg[field] !== 'denied') {
      fail('CONTROL_NOT_DENIED', `${field} must be "denied" for the Builder.`)
    }
  }

  return { valid: issues.length === 0, issues }
}

/** Deterministic object form used for hashing (sorted keys, no undefined). */
export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (value !== null && typeof value === 'object') {
    const out = {}
    for (const key of Object.keys(value).sort()) {
      const item = value[key]
      if (item !== undefined) out[key] = canonicalize(item)
    }
    return out
  }
  return value
}

export function hashPackage(pkg) {
  return createHash('sha256').update(JSON.stringify(canonicalize(pkg))).digest('hex')
}

/** SHA256 map for host-protected files, keyed by repo-relative path. */
export function captureFileHashes(root, files) {
  const out = {}
  for (const file of files) {
    const key = normalizePath(file)
    out[key] = createHash('sha256').update(readFileSync(resolve(root, file))).digest('hex')
  }
  return out
}

/** Re-verify a captured map; any change or missing file is a violation. */
export function verifyFileHashes(root, captured) {
  const violations = []
  for (const [file, expected] of Object.entries(captured)) {
    let actual
    try {
      actual = createHash('sha256').update(readFileSync(resolve(root, file))).digest('hex')
    }
    catch {
      violations.push({ path: file, code: 'PROTECTED_FILE_MISSING' })
      continue
    }
    if (actual !== expected) {
      violations.push({ path: file, code: 'PROTECTED_FILE_CHANGED', expected, actual })
    }
  }
  return violations
}

/**
 * Check a tool catalog against the Builder surface. A clean surface has
 * exactly EXPECTED_BUILDER_TOOLS and no forbidden marker in any name.
 */
export function checkToolSurface(toolNames) {
  const violations = []
  const names = toolNames.map(name => String(name).toLowerCase())

  for (const name of names) {
    for (const { marker, reason } of FORBIDDEN_TOOL_MARKERS) {
      if (name.includes(marker)) {
        violations.push({ tool: name, reason, marker })
      }
    }
  }

  for (const expected of EXPECTED_BUILDER_TOOLS) {
    if (!names.includes(expected)) {
      violations.push({ tool: expected, reason: 'missing', marker: expected })
    }
  }

  // Anything outside the closed five-tool list is unexpected, on top of any
  // marker violation it may already carry.
  for (const name of new Set(names)) {
    if (!EXPECTED_BUILDER_TOOLS.includes(name)) {
      violations.push({ tool: name, reason: 'unexpected', marker: name })
    }
  }

  return violations
}
