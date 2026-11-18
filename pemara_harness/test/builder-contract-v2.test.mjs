import assert from 'node:assert/strict'
import test from 'node:test'

import { MIN_PROTECTED_PATHS } from '../src/builder-contract.mjs'
import {
  BUILDER_CONTRACT_VERSION_V2,
  EXPECTED_BUILDER_TOOLS_V2,
  MIN_PROTECTED_PATHS_V2,
  checkBuilderV2ToolSurface,
  normalizeBuilderPath,
  validateBuilderPackageV2,
} from '../src/builder-contract-v2.mjs'

const ZERO = '0'.repeat(64)

function validPackage() {
  return {
    contract_version: 2,
    task_id: 'QB-011',
    objective: 'Edit one allowed file and run the protected check.',
    allowed_paths: ['src/worker.mjs'],
    forbidden_paths: [...MIN_PROTECTED_PATHS_V2],
    acceptance_commands: ['focused-test'],
    command_allowlist: [{
      id: 'focused-test',
      runtime: 'node',
      args: ['--test', 'test/worker.test.mjs'],
      cwd: '.',
      timeout_ms: 60_000,
      max_output_bytes: 65_536,
    }],
    file_baselines: { 'src/worker.mjs': ZERO },
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

function codes(result) { return result.issues.map(issue => issue.code) }

test('Builder v2 admits exact files, fixed Node commands and the eight-tool surface', () => {
  const result = validateBuilderPackageV2(validPackage())
  assert.deepEqual(result, { valid: true, issues: [] })
  assert.equal(BUILDER_CONTRACT_VERSION_V2, 2)
  assert.deepEqual(checkBuilderV2ToolSurface(EXPECTED_BUILDER_TOOLS_V2), [])
  assert.equal(normalizeBuilderPath('src\\worker.mjs'), 'src/worker.mjs')
  assert.equal(normalizeBuilderPath('../RULES.md'), undefined)
  assert.equal(normalizeBuilderPath('src/'), undefined)
  assert.equal(normalizeBuilderPath('work.txt:secret'), undefined)
  assert.equal(normalizeBuilderPath('NUL.txt'), undefined)
  assert.equal(normalizeBuilderPath('src/file. '), undefined)
  for (const path of MIN_PROTECTED_PATHS) assert.ok(MIN_PROTECTED_PATHS_V2.includes(path))
})

test('Builder v2 refuses raw runtimes, command drift and credential-like arguments', () => {
  const shell = validPackage()
  shell.command_allowlist[0].runtime = 'powershell'
  assert.ok(codes(validateBuilderPackageV2(shell)).includes('COMMAND_RUNTIME_DENIED'))

  const drift = validPackage()
  drift.acceptance_commands = ['another-command']
  assert.ok(codes(validateBuilderPackageV2(drift)).includes('COMMAND_SCOPE_MISMATCH'))

  const credential = validPackage()
  credential.command_allowlist[0].args = ['--api-key=secret-value']
  assert.ok(codes(validateBuilderPackageV2(credential)).includes('INVALID_COMMAND_ARGS'))

  const permissionEscape = validPackage()
  permissionEscape.command_allowlist[0].args = ['--no-permission', '--test', 'test/worker.test.mjs']
  assert.ok(codes(validateBuilderPackageV2(permissionEscape)).includes('INVALID_COMMAND_ARGS'))
})

test('Builder v2 refuses directory grants, incomplete baselines and protected gate access', () => {
  const directory = validPackage()
  directory.allowed_paths = ['src/']
  directory.file_baselines = { 'src/': null }
  assert.ok(codes(validateBuilderPackageV2(directory)).includes('V2_PATH_NOT_EXACT'))

  const baseline = validPackage()
  baseline.file_baselines = {}
  assert.ok(codes(validateBuilderPackageV2(baseline)).includes('FILE_BASELINE_SCOPE'))

  const alias = validPackage()
  alias.allowed_paths = ['src/worker.mjs', 'SRC/WORKER.mjs']
  alias.file_baselines = { 'src/worker.mjs': ZERO, 'SRC/WORKER.mjs': ZERO }
  assert.ok(codes(validateBuilderPackageV2(alias)).includes('DUPLICATE_ALLOWED_PATH'))

  const gate = validPackage()
  gate.forbidden_paths = [...MIN_PROTECTED_PATHS]
  assert.ok(codes(validateBuilderPackageV2(gate)).includes('V2_PROTECTED_SET_INCOMPLETE'))
})

test('Builder v2 tool surface keeps shell, Git, network and promotion unavailable', () => {
  for (const extra of ['pwsh', 'git_commit', 'web_search', 'harness_task_verify']) {
    const violations = checkBuilderV2ToolSurface([...EXPECTED_BUILDER_TOOLS_V2, extra])
    assert.ok(violations.some(item => item.tool === extra && item.reason !== 'missing'), extra)
  }
})
