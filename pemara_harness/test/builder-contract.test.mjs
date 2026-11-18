import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import {
  BUILDER_CONTRACT_VERSION,
  EXPECTED_BUILDER_TOOLS,
  MAX_FILES_CHANGED_LIMIT,
  MAX_ROUNDS_LIMIT,
  MIN_PROTECTED_PATHS,
  SKILL_COUNT_MAX,
  SKILL_COUNT_MIN,
  TASK_ID_PATTERN,
  captureFileHashes,
  checkToolSurface,
  entriesIntersect,
  hashPackage,
  isPathAllowed,
  pathMatchesEntry,
  validateBuilderPackage,
  verifyFileHashes,
} from '../src/builder-contract.mjs'

function validPackage() {
  return {
    task_id: 'QB-001',
    objective: 'Implement read-only doctor.',
    allowed_paths: ['src/doctor.mjs', 'bin/pemara-harness.mjs', 'test/doctor.test.mjs'],
    forbidden_paths: [...MIN_PROTECTED_PATHS, 'src/index.mjs', 'dsh/plugin.mjs'],
    acceptance_commands: ['node test/doctor.test.mjs', 'npm run manifest:check'],
    required_artifacts: ['diff', 'test output', 'checkpoint'],
    skills: ['test-driven-development', 'debugging-and-error-recovery', 'incremental-implementation'],
    max_rounds: 6,
    max_files_changed: 5,
    network: 'denied',
    service_control: 'denied',
    gpu_control: 'denied',
    commit_or_publish: 'denied',
    stop_conditions: ['protected test failed', 'path outside scope', 'budget exhausted'],
  }
}

function codes(result) {
  return result.issues.map(issue => issue.code)
}

test('contract exposes the owner-approved budgets and protected set', () => {
  assert.equal(BUILDER_CONTRACT_VERSION, 1)
  assert.equal(MAX_ROUNDS_LIMIT, 6)
  assert.equal(MAX_FILES_CHANGED_LIMIT, 5)
  assert.equal(SKILL_COUNT_MIN, 3)
  assert.equal(SKILL_COUNT_MAX, 12)
  assert.ok(TASK_ID_PATTERN.test('QB-042'))
  assert.ok(!TASK_ID_PATTERN.test('qb-42'))
  assert.ok(!TASK_ID_PATTERN.test('QB-1234'))
  for (const path of MIN_PROTECTED_PATHS) {
    assert.ok(pathMatchesEntry(path, path))
  }
})

test('a valid closed package is admitted', () => {
  const result = validateBuilderPackage(validPackage())
  assert.deepEqual(result, { valid: true, issues: [] })
})

test('invalid task id is rejected', () => {
  const pkg = validPackage()
  pkg.task_id = 'QWEN-1'
  assert.equal(validateBuilderPackage(pkg).valid, false)
  assert.ok(codes(validateBuilderPackage(pkg)).includes('INVALID_TASK_ID'))
})

test('missing or oversized budgets are rejected', () => {
  const missing = validPackage()
  delete missing.max_rounds
  delete missing.max_files_changed
  const resultMissing = validateBuilderPackage(missing)
  assert.equal(resultMissing.valid, false)
  assert.ok(codes(resultMissing).includes('MISSING_BUDGET'))

  const oversized = validPackage()
  oversized.max_rounds = 7
  oversized.max_files_changed = 6
  const resultOversized = validateBuilderPackage(oversized)
  assert.equal(resultOversized.valid, false)
  assert.ok(codes(resultOversized).includes('BUDGET_EXCEEDED'))
})

test('skills outside 3 to 12 are rejected', () => {
  const tooFew = validPackage()
  tooFew.skills = ['one', 'two']
  assert.ok(codes(validateBuilderPackage(tooFew)).includes('SKILLS_OUT_OF_RANGE'))

  const tooMany = validPackage()
  tooMany.skills = Array.from({ length: 13 }, (_, index) => `skill-${index}`)
  assert.ok(codes(validateBuilderPackage(tooMany)).includes('SKILLS_OUT_OF_RANGE'))

  const duplicated = validPackage()
  duplicated.skills = ['same', 'same', 'other']
  assert.ok(codes(validateBuilderPackage(duplicated)).includes('DUPLICATE_SKILLS'))
})

test('a path outside the allowlist is not allowed', () => {
  const pkg = validPackage()
  assert.equal(isPathAllowed('src/doctor.mjs', pkg.allowed_paths), true)
  assert.equal(isPathAllowed('src/index.mjs', pkg.allowed_paths), false)
  assert.equal(isPathAllowed('docs/ARCHITECTURE.md', pkg.allowed_paths), false)
  assert.equal(isPathAllowed('evidence/validation-20260821.json', pkg.allowed_paths), false)
})

test('allowed and forbidden paths must not intersect', () => {
  const overlappingDir = validPackage()
  overlappingDir.allowed_paths = ['src/']
  assert.equal(entriesIntersect(overlappingDir.allowed_paths, overlappingDir.forbidden_paths), true)

  const result = validateBuilderPackage(overlappingDir)
  assert.equal(result.valid, false)
  assert.ok(codes(result).includes('ALLOWED_FORBIDDEN_INTERSECTION'))

  const overlappingFile = validPackage()
  overlappingFile.allowed_paths = ['src/', 'test/']
  assert.equal(entriesIntersect(overlappingFile.allowed_paths, overlappingFile.forbidden_paths), true)
})

test('forbidden paths must cover the minimum protected set', () => {
  const pkg = validPackage()
  pkg.forbidden_paths = ['RULES.md']
  const result = validateBuilderPackage(pkg)
  assert.equal(result.valid, false)
  assert.ok(codes(result).includes('PROTECTED_SET_INCOMPLETE'))
})

test('network, service, gpu or promotion must be denied', () => {
  for (const field of ['network', 'service_control', 'gpu_control', 'commit_or_publish']) {
    const pkg = validPackage()
    pkg[field] = 'allowed'
    const result = validateBuilderPackage(pkg)
    assert.equal(result.valid, false, field)
    assert.ok(codes(result).includes('CONTROL_NOT_DENIED'), field)
  }
})

test('unknown package fields are rejected (closed package)', () => {
  const pkg = validPackage()
  pkg.bonus_rounds = 99
  const result = validateBuilderPackage(pkg)
  assert.equal(result.valid, false)
  assert.ok(codes(result).includes('UNKNOWN_FIELD'))
})

test('package hash is canonical: stable under key order, sensitive to values', () => {
  const base = validPackage()
  const reordered = {
    stop_conditions: base.stop_conditions,
    task_id: base.task_id,
    objective: base.objective,
    allowed_paths: base.allowed_paths,
    forbidden_paths: base.forbidden_paths,
    acceptance_commands: base.acceptance_commands,
    required_artifacts: base.required_artifacts,
    skills: base.skills,
    max_rounds: base.max_rounds,
    max_files_changed: base.max_files_changed,
    network: base.network,
    service_control: base.service_control,
    gpu_control: base.gpu_control,
    commit_or_publish: base.commit_or_publish,
  }
  assert.equal(hashPackage(reordered), hashPackage(base))

  const changed = validPackage()
  changed.max_rounds = 4
  assert.notEqual(hashPackage(changed), hashPackage(base))
})

test('changing a protected file fails the gate', () => {
  const root = mkdtempSync(join(tmpdir(), 'pemara-contract-'))
  try {
    mkdirSync(join(root, 'evidence'), { recursive: true })
    writeFileSync(join(root, 'RULES.md'), 'rule one\n')
    writeFileSync(join(root, 'policy.txt'), 'policy v1\n')
    const captured = captureFileHashes(root, ['RULES.md', 'policy.txt'])

    assert.deepEqual(verifyFileHashes(root, captured), [])

    writeFileSync(join(root, 'RULES.md'), 'rule one, edited by the builder\n')
    const violations = verifyFileHashes(root, captured)
    assert.equal(violations.length, 1)
    assert.equal(violations[0].code, 'PROTECTED_FILE_CHANGED')
    assert.equal(violations[0].path, 'RULES.md')

    rmSync(join(root, 'policy.txt'))
    const missing = verifyFileHashes(root, captured)
    assert.ok(missing.some(item => item.code === 'PROTECTED_FILE_MISSING'))
  }
  finally {
    rmSync(root, { recursive: true, force: true })
  }
})

test('the builder tool surface admits only the five ledger tools', () => {
  assert.deepEqual(checkToolSurface(EXPECTED_BUILDER_TOOLS), [])

  const withNetwork = [...EXPECTED_BUILDER_TOOLS, 'web_search']
  const network = checkToolSurface(withNetwork)
  assert.ok(network.some(item => item.reason === 'network'))
  assert.ok(network.some(item => item.reason === 'unexpected'))

  const withPromotion = EXPECTED_BUILDER_TOOLS.filter(name => name !== 'harness_task_request_completion')
  const missing = checkToolSurface(withPromotion)
  assert.ok(missing.some(item => item.reason === 'missing'))

  const withGpu = [...EXPECTED_BUILDER_TOOLS, 'gpu_free']
  assert.ok(checkToolSurface(withGpu).some(item => item.reason === 'gpu'))

  const withService = [...EXPECTED_BUILDER_TOOLS, 'job_output']
  assert.ok(checkToolSurface(withService).some(item => item.reason === 'service'))
})
