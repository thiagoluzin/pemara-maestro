#!/usr/bin/env node

import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'

import { DurableTaskStore, HarnessStateError, TASK_STATUS } from '../src/index.mjs'

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const COMMANDS = new Set([
  'create', 'status', 'list', 'events', 'recover', 'resolve-effect', 'resume', 'verify', 'doctor',
  'research-plan', 'research', 'research-status',
])

const NEEDS_STORE = new Set([
  'create', 'status', 'list', 'events', 'recover', 'resolve-effect', 'resume', 'verify',
])

const USAGE = `Pemara Harness durable ledger

Usage:
  pemara-harness [--db PATH] create --objective TEXT [--id ID] [--max-rounds N] [--session ID]
  pemara-harness [--db PATH] status --id ID
  pemara-harness [--db PATH] list [--status STATUS]
  pemara-harness [--db PATH] events --id ID [--from-seq N]
  pemara-harness [--db PATH] recover
  pemara-harness [--db PATH] resolve-effect --effect-id ID --resolver NAME --outcome committed|failed --evidence TEXT [--result-json JSON]
  pemara-harness [--db PATH] resume --id ID --resolver NAME --reason TEXT --evidence TEXT
  pemara-harness [--db PATH] verify --id ID --verifier NAME --evidence TEXT [--evidence TEXT] [--outcome pass|fail]
  pemara-harness [--db PATH] doctor [--root PATH] [--qwen-url URL]
  pemara-harness research-plan --spec PUBLIC_SPEC.json
  pemara-harness research --spec PUBLIC_SPEC.json --output NEW_DIRECTORY
  pemara-harness research-status --output DIRECTORY

The model may request completion, but only this independent verifier command can
promote a task to COMPLETED_VERIFIED.

doctor is read-only: it diagnoses node, sqlite, repo, ledger, manifest, profile
and Qwen endpoint and exits 1 when any check fails (Qwen offline is a warning).
`

function usageError(message) {
  return new HarnessStateError('CLI_USAGE', `${message}\n\n${USAGE}`)
}

function parse(argv) {
  const args = [...argv]
  let databasePath = process.env.PEMARA_HARNESS_DB
  const dbIndex = args.indexOf('--db')
  if (dbIndex !== -1) {
    if (dbIndex + 1 >= args.length || args[dbIndex + 1].startsWith('--')) {
      throw usageError('--db requires a path.')
    }
    databasePath = args[dbIndex + 1]
    args.splice(dbIndex, 2)
  }
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h' || args[0] === 'help') {
    return { help: true }
  }
  const command = args.shift()
  if (!COMMANDS.has(command)) throw usageError(`Unknown command "${command}".`)

  const options = new Map()
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index]
    if (!token.startsWith('--')) throw usageError(`Unexpected positional argument "${token}".`)
    const key = token.slice(2)
    const value = args[index + 1]
    if (key === '' || value === undefined || value.startsWith('--')) {
      throw usageError(`${token} requires a value.`)
    }
    const values = options.get(key) ?? []
    values.push(value)
    options.set(key, values)
    index += 1
  }
  return {
    help: false,
    command,
    databasePath,
    options,
  }
}

const DEFAULT_DB_PATH = () => resolve(process.cwd(), '.pemara-harness', 'harness.sqlite')

function allowed(options, names) {
  for (const key of options.keys()) {
    if (!names.includes(key)) throw usageError(`Unknown option --${key}.`)
  }
}

function one(options, key, { required = false } = {}) {
  const values = options.get(key)
  if (values === undefined) {
    if (required) throw usageError(`--${key} is required.`)
    return undefined
  }
  if (values.length !== 1) throw usageError(`--${key} may be provided only once.`)
  return values[0]
}

function integerOption(options, key, settings = {}) {
  const value = one(options, key, settings)
  if (value === undefined) return undefined
  if (!/^[1-9][0-9]*$/.test(value)) throw usageError(`--${key} must be a positive integer.`)
  const number = Number(value)
  if (!Number.isSafeInteger(number)) throw usageError(`--${key} exceeds the safe integer range.`)
  return number
}

async function dispatch(store, command, options, databasePath) {
  switch (command) {
    case 'research-plan':
    case 'research': {
      allowed(options, command === 'research' ? ['spec', 'output'] : ['spec'])
      const { runResearch, validateResearchSpec } = await import('../src/research.mjs')
      const spec = validateResearchSpec(JSON.parse(readFileSync(one(options, 'spec', { required: true }), 'utf8')))
      if (command === 'research-plan') return { spec, networkCalls: 0,
        maximumExternalCalls: (spec.query ? 1 : 0) + spec.maxSources + 1, automaticRetry: false }
      const report = await runResearch({ spec, output: one(options, 'output', { required: true }) })
      return { id: report.id, state: report.state, approved: false, dossierPath: report.dossierPath,
        reviewQueue: report.reviewQueue, verification: report.verification, durationMs: report.durationMs }
    }
    case 'research-status': {
      allowed(options, ['output'])
      const { inspectResearch } = await import('../src/research.mjs')
      return inspectResearch(one(options, 'output', { required: true }))
    }
    case 'doctor': {
      allowed(options, ['root', 'qwen-url'])
      const { runDoctor } = await import('../src/doctor.mjs')
      const report = await runDoctor({
        root: one(options, 'root') ?? REPO_ROOT,
        ...(one(options, 'qwen-url') === undefined ? {} : { qwenUrl: one(options, 'qwen-url') }),
        ...(databasePath === undefined ? {} : { dbPath: databasePath }),
      })
      return { report }
    }
    case 'create': {
      allowed(options, ['id', 'objective', 'max-rounds', 'session'])
      const task = store.createTask({
        ...(one(options, 'id') === undefined ? {} : { id: one(options, 'id') }),
        objective: one(options, 'objective', { required: true }),
        ...(integerOption(options, 'max-rounds') === undefined
          ? {}
          : { maxRounds: integerOption(options, 'max-rounds') }),
        ...(one(options, 'session') === undefined ? {} : { sessionId: one(options, 'session') }),
      })
      return { task }
    }
    case 'status': {
      allowed(options, ['id'])
      return { task: store.getTask(one(options, 'id', { required: true })) }
    }
    case 'list': {
      allowed(options, ['status'])
      const status = one(options, 'status')
      if (status !== undefined && !Object.values(TASK_STATUS).includes(status)) {
        throw usageError(`--status must be one of ${Object.values(TASK_STATUS).join(', ')}.`)
      }
      return { tasks: store.listTasks(status === undefined ? {} : { status }) }
    }
    case 'events': {
      allowed(options, ['id', 'from-seq'])
      return {
        events: store.listEvents(one(options, 'id', { required: true }), {
          fromSeq: integerOption(options, 'from-seq') ?? 1,
        }),
      }
    }
    case 'recover': {
      allowed(options, [])
      return store.recover()
    }
    case 'resolve-effect': {
      allowed(options, ['effect-id', 'resolver', 'outcome', 'evidence', 'result-json'])
      const outcome = one(options, 'outcome', { required: true })
      if (outcome !== 'committed' && outcome !== 'failed') {
        throw usageError('--outcome must be committed or failed.')
      }
      const rawResult = one(options, 'result-json')
      let result
      if (rawResult !== undefined) {
        try {
          result = JSON.parse(rawResult)
        }
        catch (error) {
          throw usageError(`--result-json is invalid JSON: ${error instanceof Error ? error.message : String(error)}`)
        }
      }
      return store.resolveEffect(one(options, 'effect-id', { required: true }), {
        resolver: one(options, 'resolver', { required: true }),
        outcome,
        evidence: options.get('evidence') ?? [],
        ...(rawResult === undefined ? {} : { result }),
      })
    }
    case 'resume': {
      allowed(options, ['id', 'resolver', 'reason', 'evidence'])
      return {
        task: store.resumeTask(one(options, 'id', { required: true }), {
          resolver: one(options, 'resolver', { required: true }),
          reason: one(options, 'reason', { required: true }),
          evidence: options.get('evidence') ?? [],
        }),
      }
    }
    case 'verify': {
      allowed(options, ['id', 'verifier', 'evidence', 'outcome'])
      const evidence = options.get('evidence') ?? []
      const outcome = one(options, 'outcome') ?? 'pass'
      if (outcome !== 'pass' && outcome !== 'fail') throw usageError('--outcome must be pass or fail.')
      return {
        task: store.verifyCompletion(one(options, 'id', { required: true }), {
          verifier: one(options, 'verifier', { required: true }),
          outcome,
          evidence,
        }),
      }
    }
    default:
      throw usageError(`Unknown command "${command}".`)
  }
}

let store
try {
  const parsed = parse(process.argv.slice(2))
  if (parsed.help) {
    process.stdout.write(USAGE)
  }
  else {
    store = NEEDS_STORE.has(parsed.command)
      ? new DurableTaskStore({ databasePath: parsed.databasePath ?? DEFAULT_DB_PATH() })
      : undefined
    const result = await dispatch(store, parsed.command, parsed.options, parsed.databasePath)
    if (parsed.command === 'doctor' && result.report && !result.report.ok) {
      process.exitCode = 1
    }
    if (parsed.command === 'research-status' && result.integrity !== 'ok') process.exitCode = 1
    process.stdout.write(`${JSON.stringify(result, undefined, 2)}\n`)
  }
}
catch (error) {
  const known = error instanceof HarnessStateError
  const body = {
    error: {
      code: known ? error.code : 'INTERNAL',
      message: error instanceof Error ? error.message : String(error),
      ...(known && error.details !== undefined ? { details: error.details } : {}),
    },
  }
  process.stderr.write(`${JSON.stringify(body)}\n`)
  process.exitCode = 1
}
finally {
  store?.close()
}
