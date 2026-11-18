import { isAbsolute } from 'node:path'

import {
  EXPECTED_BUILDER_TOOLS,
  FORBIDDEN_TOOL_MARKERS,
  MIN_PROTECTED_PATHS,
  pathMatchesEntry,
  validateBuilderPackage,
} from './builder-contract.mjs'

export const BUILDER_CONTRACT_VERSION_V2 = 2
export const BUILDER_CONTRACT_ID_V2 = 'qwen-builder-v2'
export const MAX_BUILDER_FILE_BYTES = 256 * 1024
export const MAX_BUILDER_TEST_OUTPUT_BYTES = 256 * 1024
export const MAX_BUILDER_TEST_TIMEOUT_MS = 15 * 60 * 1000

export const MIN_PROTECTED_PATHS_V2 = Object.freeze([
  ...MIN_PROTECTED_PATHS,
  'src/builder-contract-v2.mjs',
  'src/builder-runtime.mjs',
  'src/effects/subprocess-network-guard.mjs',
  'dsh/plugin.mjs',
  'dsh/builder-policy.mjs',
  'test/builder-contract-v2.test.mjs',
  'test/builder-tools.test.mjs',
])

export const EXPECTED_BUILDER_TOOLS_V2 = Object.freeze([
  ...EXPECTED_BUILDER_TOOLS,
  'builder_file_read',
  'builder_file_write',
  'builder_test_run',
])

const COMMAND_ID = /^[a-z0-9][a-z0-9._-]{0,63}$/
const SHA256 = /^[a-f0-9]{64}$/
const SENSITIVE_ARG = /(bearer|token|secret|password|credential|api[_-]?key|private[_-]?key)|\bsk-[a-z0-9_-]+/iu
const HOST_OWNED_NODE_FLAG = /^(?:--(?:no-)?(?:experimental-)?permission(?:=|$)|--allow-|--import(?:=|$)|--require(?:=|$)|-r$|--inspect|--experimental-loader|--env-file)/u
const WINDOWS_RESERVED_NAME = /^(?:aux|con|nul|prn|com[1-9]|lpt[1-9])(?:\.|$)/iu

export function normalizeBuilderPath(value) {
  if (typeof value !== 'string' || value.trim() === '') return undefined
  const path = value.trim().normalize('NFC').replaceAll('\\', '/').replace(/^\.\//u, '')
  if (path === '' || path.endsWith('/') || isAbsolute(path) || /^[a-z]:/iu.test(path)
    || /[\u0000-\u001f<>:"|?*\[\]]/u.test(path)) return undefined
  const segments = path.split('/')
  if (segments.some(segment => segment === '' || segment === '.' || segment === '..'
    || /[. ]$/u.test(segment) || WINDOWS_RESERVED_NAME.test(segment))) return undefined
  return path
}

function validateCommand(command, fail) {
  if (command === null || typeof command !== 'object' || Array.isArray(command)) {
    fail('INVALID_COMMAND', 'Every command_allowlist entry must be an object.')
    return undefined
  }
  const known = new Set(['id', 'runtime', 'args', 'cwd', 'timeout_ms', 'max_output_bytes'])
  for (const key of Object.keys(command)) {
    if (!known.has(key)) fail('UNKNOWN_COMMAND_FIELD', `Unknown command field "${key}".`)
  }
  if (typeof command.id !== 'string' || !COMMAND_ID.test(command.id)) {
    fail('INVALID_COMMAND_ID', 'Command id must use lowercase letters, digits, dot, dash or underscore.')
  }
  if (command.runtime !== 'node') {
    fail('COMMAND_RUNTIME_DENIED', 'Only the host Node.js runtime is allowed.')
  }
  if (!Array.isArray(command.args)
    || command.args.some(arg => typeof arg !== 'string' || arg.includes('\u0000')
      || SENSITIVE_ARG.test(arg) || HOST_OWNED_NODE_FLAG.test(arg))) {
    fail('INVALID_COMMAND_ARGS', 'Command args must be credential-free strings without NUL bytes.')
  }
  const cwd = command.cwd ?? '.'
  if (cwd !== '.' && normalizeBuilderPath(cwd) === undefined) {
    fail('INVALID_COMMAND_CWD', 'Command cwd must be a relative directory inside the worktree.')
  }
  if (!Number.isSafeInteger(command.timeout_ms) || command.timeout_ms < 1
    || command.timeout_ms > MAX_BUILDER_TEST_TIMEOUT_MS) {
    fail('INVALID_COMMAND_TIMEOUT', `Command timeout_ms must be 1..${MAX_BUILDER_TEST_TIMEOUT_MS}.`)
  }
  if (!Number.isSafeInteger(command.max_output_bytes) || command.max_output_bytes < 1
    || command.max_output_bytes > MAX_BUILDER_TEST_OUTPUT_BYTES) {
    fail('INVALID_COMMAND_OUTPUT', `Command max_output_bytes must be 1..${MAX_BUILDER_TEST_OUTPUT_BYTES}.`)
  }
  return typeof command.id === 'string' ? command.id : undefined
}

/** Validate the executable Builder package. V1 remains intact as rollback. */
export function validateBuilderPackageV2(pkg) {
  if (pkg === null || typeof pkg !== 'object' || Array.isArray(pkg)) {
    return { valid: false, issues: [{ code: 'BUILDER_PACKAGE_INVALID', message: 'package must be a plain object.' }] }
  }
  const issues = []
  const fail = (code, message) => issues.push({ code, message })
  if (pkg.contract_version !== BUILDER_CONTRACT_VERSION_V2) {
    fail('INVALID_CONTRACT_VERSION', `contract_version must be ${BUILDER_CONTRACT_VERSION_V2}.`)
  }

  const v1Shape = { ...pkg }
  delete v1Shape.contract_version
  delete v1Shape.command_allowlist
  delete v1Shape.file_baselines
  issues.push(...validateBuilderPackage(v1Shape).issues)

  const allowed = Array.isArray(pkg.allowed_paths) ? pkg.allowed_paths : []
  const normalizedAllowed = allowed.map(normalizeBuilderPath)
  if (normalizedAllowed.some(path => path === undefined)) {
    fail('V2_PATH_NOT_EXACT', 'V2 allowed_paths must contain exact relative files, without directories or globs.')
  }
  if (allowed.some((path, index) => path !== normalizedAllowed[index])) {
    fail('V2_PATH_NOT_CANONICAL', 'V2 allowed_paths must use canonical forward-slash NFC paths.')
  }
  if (new Set(normalizedAllowed.filter(Boolean).map(path => path.toLowerCase())).size !== normalizedAllowed.length) {
    fail('DUPLICATE_ALLOWED_PATH', 'V2 allowed_paths must be unique after normalization.')
  }

  if (Array.isArray(pkg.forbidden_paths)) {
    for (const protectedPath of MIN_PROTECTED_PATHS_V2) {
      if (!pkg.forbidden_paths.some(entry => pathMatchesEntry(protectedPath, entry))) {
        fail('V2_PROTECTED_SET_INCOMPLETE', `forbidden_paths must include "${protectedPath}".`)
      }
    }
  }

  if (pkg.file_baselines === null || typeof pkg.file_baselines !== 'object'
    || Array.isArray(pkg.file_baselines)) {
    fail('INVALID_FILE_BASELINES', 'file_baselines must map every allowed file to SHA256 or null.')
  }
  else {
    const baselineKeys = Object.keys(pkg.file_baselines)
    const allowedSet = new Set(allowed.filter(path => typeof path === 'string'))
    if (baselineKeys.length !== allowedSet.size
      || baselineKeys.some(path => !allowedSet.has(path))) {
      fail('FILE_BASELINE_SCOPE', 'file_baselines keys must exactly match allowed_paths.')
    }
    for (const [path, hash] of Object.entries(pkg.file_baselines)) {
      if (normalizeBuilderPath(path) === undefined || (hash !== null && (typeof hash !== 'string' || !SHA256.test(hash)))) {
        fail('INVALID_FILE_BASELINE', `Invalid baseline for "${path}".`)
      }
    }
  }

  if (!Array.isArray(pkg.command_allowlist) || pkg.command_allowlist.length === 0) {
    fail('COMMAND_ALLOWLIST_MISSING', 'command_allowlist must contain at least one fixed command.')
  }
  else {
    const ids = pkg.command_allowlist.map(command => validateCommand(command, fail)).filter(Boolean)
    if (new Set(ids).size !== ids.length) fail('DUPLICATE_COMMAND_ID', 'Command ids must be unique.')
    const accepted = Array.isArray(pkg.acceptance_commands) ? pkg.acceptance_commands : []
    const acceptedSet = new Set(accepted)
    const idSet = new Set(ids)
    if (acceptedSet.size !== idSet.size || [...acceptedSet].some(id => !idSet.has(id))) {
      fail('COMMAND_SCOPE_MISMATCH', 'acceptance_commands must exactly name command_allowlist ids.')
    }
  }

  return { valid: issues.length === 0, issues }
}

export function checkBuilderV2ToolSurface(toolNames) {
  if (!Array.isArray(toolNames)) return [{ tool: '(surface)', reason: 'invalid', marker: 'array' }]
  const violations = []
  const names = toolNames.map(name => String(name).toLowerCase())
  for (const name of names) {
    for (const { marker, reason } of FORBIDDEN_TOOL_MARKERS) {
      if (name.includes(marker)) violations.push({ tool: name, reason, marker })
    }
  }
  for (const expected of EXPECTED_BUILDER_TOOLS_V2) {
    if (!names.includes(expected)) violations.push({ tool: expected, reason: 'missing', marker: expected })
  }
  for (const name of new Set(names)) {
    if (!EXPECTED_BUILDER_TOOLS_V2.includes(name)) {
      violations.push({ tool: name, reason: 'unexpected', marker: name })
    }
  }
  return violations
}
