#!/usr/bin/env node

import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

import {
  captureFileHashes,
  checkToolSurface,
  validateBuilderPackage,
  verifyFileHashes,
} from '../src/builder-contract.mjs'

const USAGE = `Pemara Builder protected gate (host-owned)

Usage:
  check-protected [--root PATH] --capture --files PATH,PATH,... [--out EVIDENCE_JSON]
  check-protected [--root PATH] --verify --evidence EVIDENCE_JSON
  check-protected [--root PATH] --package TASK_PACKAGE_JSON
  check-protected [--root PATH] --tools TOOL,TOOL,...

--root defaults to this repository. Use it to verify a Builder worktree.
All checks may be combined. Exit code 0 means every gate passed.
`

function parseArgs(argv) {
  const args = [...argv]
  const options = { capture: false, verify: false, files: [], out: undefined, evidence: undefined, packagePath: undefined, tools: [], root: undefined }
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index]
    const next = () => args[index + 1]
    switch (token) {
      case '--help':
      case '-h':
        options.help = true
        break
      case '--root':
        options.root = next()
        index += 1
        break
      case '--capture':
        options.capture = true
        break
      case '--verify':
        options.verify = true
        break
      case '--files':
        options.files = next().split(',').map(item => item.trim()).filter(Boolean)
        index += 1
        break
      case '--out':
        options.out = next()
        index += 1
        break
      case '--evidence':
        options.evidence = next()
        index += 1
        break
      case '--package':
        options.packagePath = next()
        index += 1
        break
      case '--tools':
        options.tools = next().split(',').map(item => item.trim()).filter(Boolean)
        index += 1
        break
      default:
        throw new Error(`Unknown option ${token}`)
    }
  }
  return options
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8').replace(/^\uFEFF/, ''))
}

const defaultRoot = resolve(dirname(new URL(import.meta.url).pathname.replace(/^\/(?:([A-Za-z]):)/, '$1:')), '..')
const options = parseArgs(process.argv.slice(2))

if (options.help) {
  process.stdout.write(USAGE)
  process.exit(0)
}

const root = options.root === undefined ? defaultRoot : resolve(options.root)

const report = { gates: [] }
const fail = gate => report.gates.push({ gate, ok: false })
const pass = (gate, detail) => report.gates.push({ gate, ok: true, ...(detail === undefined ? {} : { detail }) })

if (options.capture) {
  try {
    const files = captureFileHashes(root, options.files)
    const payload = { contract: 'qwen-builder-v1', capturedAt: new Date().toISOString(), files }
    if (options.out) {
      writeFileSync(resolve(root, options.out), `${JSON.stringify(payload, undefined, 2)}\n`)
      pass('capture', options.out)
    }
    else {
      process.stdout.write(`${JSON.stringify(payload, undefined, 2)}\n`)
      pass('capture', `${Object.keys(files).length} files`)
    }
  }
  catch (error) {
    fail('capture')
    report.error = `capture: ${error instanceof Error ? error.message : String(error)}`
  }
}

if (options.verify) {
  const evidencePath = resolve(root, options.evidence)
  const captured = readJson(evidencePath)
  const violations = verifyFileHashes(root, captured.files)
  if (violations.length === 0) pass('protected-hashes', Object.keys(captured.files).length)
  else {
    fail('protected-hashes')
    report.violations = violations
  }
}

if (options.packagePath) {
  const pkg = readJson(resolve(root, options.packagePath))
  const result = validateBuilderPackage(pkg)
  if (result.valid) pass('package')
  else {
    fail('package')
    report.packageIssues = result.issues
  }
}

if (options.tools.length > 0) {
  const violations = checkToolSurface(options.tools)
  if (violations.length === 0) pass('tool-surface', options.tools.length)
  else {
    fail('tool-surface')
    report.toolViolations = violations
  }
}

if (report.gates.length === 0) {
  process.stderr.write(`${USAGE}\nNo gate selected.\n`)
  process.exitCode = 2
}
else {
  const ok = report.gates.every(gate => gate.ok)
  process.stdout.write(`${JSON.stringify({ ok, ...report }, undefined, 2)}\n`)
  process.exitCode = ok ? 0 : 1
}
