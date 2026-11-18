import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { freezeEvaluation, compareEvaluation, readContract } from '../src/fixed-evaluation.mjs'

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'pemara-fixed-eval-'))
  mkdirSync(join(root, 'test'))
  mkdirSync(join(root, 'src'))
  writeFileSync(join(root, 'package.json'), JSON.stringify({ type: 'module' }))
  writeFileSync(join(root, 'src', 'value.mjs'), 'export const value = 2\n')
  writeFileSync(join(root, 'test', 'value.test.mjs'),
    "import test from 'node:test'; import assert from 'node:assert/strict'; import {value} from '../src/value.mjs'; test('value',()=>assert.equal(value,2))\n")
  return { root, output: join(root, '.runtime', 'evaluation'), files: ['test/value.test.mjs'] }
}

test('unchanged passing candidate requires review and reports no measured improvement', async () => {
  const { root, output, files } = fixture()
  const frozen = await freezeEvaluation({ root, output, files })
  const compared = await compareEvaluation({ root, contractPath: frozen.contractPath, expectedSha: frozen.sha256 })
  assert.equal(compared.status, 'NO_REGRESSION_REVIEW_REQUIRED')
  assert.equal(compared.sameSource, true)
  assert.equal(compared.accepted, false)
  assert.equal(compared.candidate.summary.tests, 1)
})

test('changed acceptance tests are rejected before candidate execution', async () => {
  const { root, output, files } = fixture()
  const frozen = await freezeEvaluation({ root, output, files })
  writeFileSync(join(root, files[0]), "throw new Error('test must not run')")
  await assert.rejects(compareEvaluation({ root, contractPath: frozen.contractPath, expectedSha: frozen.sha256 }), /PROTECTED_FILE_CHANGED/)
})

test('source regression is measured and rejected', async () => {
  const { root, output, files } = fixture()
  const frozen = await freezeEvaluation({ root, output, files })
  writeFileSync(join(root, 'src', 'value.mjs'), 'export const value = 3\n')
  const result = await compareEvaluation({ root, contractPath: frozen.contractPath, expectedSha: frozen.sha256 })
  assert.equal(result.status, 'REGRESSION')
  assert.equal(result.accepted, false)
  assert.equal(result.candidate.summary.fail, 1)
})

test('contract edits, empty suites and path escapes cannot produce a passing evaluation', async () => {
  const { root, output, files } = fixture()
  await assert.rejects(freezeEvaluation({ root, output, files: [] }), /EMPTY_SUITE/)
  await assert.rejects(freezeEvaluation({ root, output, files: ['../outside.test.mjs'] }), /UNSAFE_TEST_PATH/)
  const frozen = await freezeEvaluation({ root, output, files })
  const contract = JSON.parse(readFileSync(frozen.contractPath, 'utf8'))
  contract.files = []
  writeFileSync(frozen.contractPath, JSON.stringify(contract))
  assert.throws(() => readContract(frozen.contractPath, frozen.sha256), /CONTRACT_HASH_MISMATCH/)
})

test('changed baseline logs cannot be used as trusted evidence', async () => {
  const { root, output, files } = fixture()
  const frozen = await freezeEvaluation({ root, output, files })
  writeFileSync(join(output, 'baseline', 'stdout.tap'), 'forged evidence')
  assert.throws(() => readContract(frozen.contractPath, frozen.sha256), /BASELINE_LOG_CHANGED/)
})

test('an all-skipped suite is not valid baseline evidence', async () => {
  const { root, output, files } = fixture()
  writeFileSync(join(root, files[0]), "import test from 'node:test'; test.skip('nothing measured',()=>{})")
  await assert.rejects(freezeEvaluation({ root, output, files }), /INVALID_BASELINE/)
})

test('adding a test after freezing requires a new contract', async () => {
  const { root, output, files } = fixture()
  const frozen = await freezeEvaluation({ root, output, files })
  writeFileSync(join(root, 'test', 'extra.test.mjs'), "import test from 'node:test'; test('extra',()=>{})")
  await assert.rejects(compareEvaluation({ root, contractPath: frozen.contractPath, expectedSha: frozen.sha256 }), /PROTECTED_FILE_CHANGED/)
})
