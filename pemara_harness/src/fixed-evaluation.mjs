import { createHash, randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn, spawnSync } from 'node:child_process'

const evaluatorPath = fileURLToPath(import.meta.url)
const hash = value => createHash('sha256').update(value).digest('hex')
const json = value => JSON.stringify(value, null, 2) + '\n'
const MAX_LOG_BYTES = 32 * 1024 * 1024

function inside(root, name) {
  const target = resolve(root, name)
  const rel = relative(root, target)
  if (isAbsolute(rel) || rel === '..' || rel.startsWith('..' + sep)) throw new Error('PATH_OUTSIDE_ROOT')
  if (existsSync(target)) {
    const actual = relative(realpathSync(root), realpathSync(target))
    if (isAbsolute(actual) || actual === '..' || actual.startsWith('..' + sep)) throw new Error('SYMLINK_OUTSIDE_ROOT')
  }
  return target
}

function walk(root, directory) {
  const path = inside(root, directory)
  if (!existsSync(path)) return []
  const result = []
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const name = `${directory}/${entry.name}`
    if (entry.isSymbolicLink()) throw new Error(`SYMLINK_IN_SOURCE: ${name}`)
    if (entry.isDirectory()) result.push(...walk(root, name))
    else if (entry.isFile()) result.push(name)
  }
  return result.sort()
}

function hashes(root, names) {
  return Object.fromEntries([...new Set(names)].sort().map(name => [name, hash(readFileSync(inside(root, name)))]))
}

function snapshot(root) {
  const names = ['src', 'bin', 'dsh', 'scripts', 'test'].flatMap(dir => walk(root, dir))
  for (const name of ['package.json', 'package-lock.json', 'pnpm-lock.yaml']) {
    if (existsSync(join(root, name))) names.push(name)
  }
  const files = hashes(root, names)
  const git = spawnSync('git', ['-c', `safe.directory=${root.replaceAll('\\', '/')}`, '-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8', windowsHide: true })
  return { sha256: hash(JSON.stringify(files)), files, gitHead: git.status === 0 ? git.stdout.trim() : null }
}

function testFiles(root, files) {
  if (!Array.isArray(files) || files.length === 0) throw new Error('EMPTY_SUITE')
  if (new Set(files).size !== files.length) throw new Error('DUPLICATE_TEST_PATH')
  for (const name of files) {
    if (typeof name !== 'string' || !/^test\/[A-Za-z0-9_./-]+\.test\.mjs$/.test(name) || name.split('/').includes('..')) {
      throw new Error('UNSAFE_TEST_PATH')
    }
    if (!existsSync(inside(root, name))) throw new Error(`MISSING_TEST: ${name}`)
  }
  return [...files]
}

export function defaultEvaluationFiles(root) {
  const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'))
  if (typeof pkg.scripts?.test !== 'string' || !pkg.scripts.test.startsWith('node --test ')) {
    throw new Error('UNSUPPORTED_TEST_COMMAND: supply explicit test paths')
  }
  return testFiles(root, pkg.scripts.test.slice('node --test '.length).trim().split(/\s+/))
}

function assertProtected(root, contract) {
  if (hash(readFileSync(evaluatorPath)) !== contract.evaluatorSha256) throw new Error('EVALUATOR_CHANGED')
  const expectedNames = Object.keys(contract.protectedFiles)
  const currentNames = walk(root, 'test')
  const fixedTestNames = expectedNames.filter(name => name.startsWith('test/'))
  if (JSON.stringify(currentNames) !== JSON.stringify(fixedTestNames.sort())) throw new Error('PROTECTED_FILE_CHANGED: test inventory')
  for (const [name, expected] of Object.entries(contract.protectedFiles)) {
    if (!existsSync(inside(root, name)) || hash(readFileSync(inside(root, name))) !== expected) {
      throw new Error(`PROTECTED_FILE_CHANGED: ${name}`)
    }
  }
  testFiles(root, contract.files)
}

export function readContract(path, expectedSha) {
  const raw = readFileSync(path)
  if (!/^[a-f0-9]{64}$/.test(expectedSha ?? '') || hash(raw) !== expectedSha) throw new Error('CONTRACT_HASH_MISMATCH')
  const contract = JSON.parse(raw)
  if (contract.schemaVersion !== 1 || contract.policy !== 'fixed-tests-human-review-v1' ||
      contract.baselineReceipt !== 'baseline.json' ||
      !Number.isInteger(contract.timeoutMs) || contract.timeoutMs < 1000 || contract.timeoutMs > 600000) {
    throw new Error('INVALID_CONTRACT')
  }
  const baselineRaw = readFileSync(join(dirname(path), contract.baselineReceipt))
  if (hash(baselineRaw) !== contract.baselineSha256) {
    throw new Error('BASELINE_HASH_MISMATCH')
  }
  const baseline = JSON.parse(baselineRaw)
  for (const [name, expected] of [['stdout.tap', baseline.logs.stdoutSha256], ['stderr.log', baseline.logs.stderrSha256]]) {
    if (hash(readFileSync(join(dirname(path), 'baseline', name))) !== expected) throw new Error('BASELINE_LOG_CHANGED')
  }
  return contract
}

async function runSuite(root, files, output, timeoutMs) {
  const before = snapshot(root)
  const startedAt = new Date().toISOString()
  const execution = await new Promise((resolveRun, rejectRun) => {
    const env = { ...process.env }
    // A gate test may launch another real test runner. Node propagates this
    // internal marker, which would otherwise silently suppress that suite.
    delete env.NODE_TEST_CONTEXT
    const child = spawn(process.execPath, ['--test', '--test-reporter=tap', ...files], {
      cwd: root, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
    })
    let stdout = '', stderr = '', bytes = 0, timedOut = false, overflow = false
    const timer = setTimeout(() => { timedOut = true; child.kill() }, timeoutMs)
    const append = (kind, data) => {
      bytes += data.length
      if (bytes > MAX_LOG_BYTES) { overflow = true; child.kill(); return }
      if (kind === 'stdout') stdout += data.toString()
      else stderr += data.toString()
    }
    child.stdout.on('data', data => append('stdout', data))
    child.stderr.on('data', data => append('stderr', data))
    child.on('error', error => { clearTimeout(timer); rejectRun(error) })
    child.on('close', (exitCode, signal) => { clearTimeout(timer); resolveRun({ exitCode, signal, timedOut, overflow, stdout, stderr }) })
  })
  const after = snapshot(root)
  const summary = {}
  for (const key of ['tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo']) {
    const matches = [...execution.stdout.matchAll(new RegExp(`^# ${key} (\\d+)\\r?$`, 'gm'))]
    summary[key] = matches.length ? Number(matches.at(-1)[1]) : null
  }
  mkdirSync(output, { recursive: true })
  writeFileSync(join(output, 'stdout.tap'), execution.stdout, { flag: 'wx' })
  writeFileSync(join(output, 'stderr.log'), execution.stderr, { flag: 'wx' })
  const valid = summary.tests > 0 && summary.pass + summary.fail > 0 && ['pass', 'fail', 'cancelled', 'skipped', 'todo'].every(key => summary[key] !== null) &&
    !execution.timedOut && !execution.overflow && before.sha256 === after.sha256
  return { startedAt, finishedAt: new Date().toISOString(),
    command: [process.execPath, '--test', '--test-reporter=tap', ...files],
    nodeVersion: process.version, exitCode: execution.exitCode, signal: execution.signal,
    timedOut: execution.timedOut, overflow: execution.overflow, valid,
    sourceChangedDuringRun: before.sha256 !== after.sha256,
    summary, source: before,
    logs: { stdoutSha256: hash(execution.stdout), stderrSha256: hash(execution.stderr) } }
}

export async function freezeEvaluation({ root, output, files, timeoutMs = 180000 }) {
  root = realpathSync(root)
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 600000) throw new Error('INVALID_TIMEOUT')
  files = testFiles(root, files ?? defaultEvaluationFiles(root))
  output = resolve(output)
  const contractPath = join(output, 'contract.json')
  if (existsSync(contractPath) || existsSync(join(output, 'baseline.json'))) throw new Error('OUTPUT_ALREADY_EXISTS')
  const protectedNames = [...walk(root, 'test'), 'package.json']
  for (const name of ['package-lock.json', 'pnpm-lock.yaml']) if (existsSync(join(root, name))) protectedNames.push(name)
  const protectedFiles = hashes(root, protectedNames)
  const evaluatorSha256 = hash(readFileSync(evaluatorPath))
  const baseline = await runSuite(root, files, join(output, 'baseline'), timeoutMs)
  if (!baseline.valid) throw new Error('INVALID_BASELINE: inspect baseline logs')
  const protectedAfter = hashes(root, protectedNames)
  if (JSON.stringify(protectedAfter) !== JSON.stringify(protectedFiles)) throw new Error('PROTECTED_FILE_CHANGED')
  if (hash(readFileSync(evaluatorPath)) !== evaluatorSha256) throw new Error('EVALUATOR_CHANGED')
  const baselineRaw = json(baseline)
  writeFileSync(join(output, 'baseline.json'), baselineRaw, { flag: 'wx' })
  const contract = { schemaVersion: 1, policy: 'fixed-tests-human-review-v1',
    createdAt: new Date().toISOString(), nodeVersion: process.version, files, protectedFiles, evaluatorSha256,
    timeoutMs, baselineReceipt: 'baseline.json', baselineSha256: hash(baselineRaw),
    authorization: { merge: false, publish: false, restartServices: false, automaticAcceptance: false } }
  const raw = json(contract)
  writeFileSync(contractPath, raw, { flag: 'wx' })
  const sha256 = hash(raw)
  writeFileSync(join(output, 'contract.sha256'), sha256 + '\n', { flag: 'wx' })
  return { contractPath, sha256, baseline: baseline.summary }
}

export async function compareEvaluation({ root, contractPath, expectedSha }) {
  root = realpathSync(root)
  contractPath = resolve(contractPath)
  const contract = readContract(contractPath, expectedSha)
  if (contract.nodeVersion !== process.version) throw new Error('NODE_VERSION_CHANGED')
  assertProtected(root, contract)
  const baseline = JSON.parse(readFileSync(join(dirname(contractPath), contract.baselineReceipt), 'utf8'))
  const output = join(dirname(contractPath), 'candidates', randomUUID())
  const candidate = await runSuite(root, contract.files, output, contract.timeoutMs)
  assertProtected(root, contract)
  // Hashes, unchanged tests, and passing checks establish technical evidence only.
  // They cannot establish artistic quality or authorize merging/deployment.
  let status = 'NO_REGRESSION_REVIEW_REQUIRED'
  if (!candidate.valid || !baseline.valid || candidate.summary.tests !== baseline.summary.tests) status = 'INVALID_EVIDENCE'
  else if (candidate.exitCode !== 0 || candidate.summary.fail > 0 || candidate.summary.cancelled > 0 ||
           candidate.summary.skipped > baseline.summary.skipped || candidate.summary.todo > baseline.summary.todo) status = 'REGRESSION'
  else if (baseline.exitCode !== 0 || baseline.summary.fail > 0) status = 'IMPROVEMENT_REVIEW_REQUIRED'
  const result = { schemaVersion: 1, status, accepted: false, contractSha256: expectedSha,
    sameSource: candidate.source.sha256 === baseline.source.sha256, baseline: baseline.summary, candidate }
  writeFileSync(join(output, 'comparison.json'), json(result), { flag: 'wx' })
  return { ...result, receiptPath: join(output, 'comparison.json') }
}
