#!/usr/bin/env node

import { resolve } from 'node:path'

import { runSupervisor } from '../src/supervisor.mjs'
import { SupervisorStateError, SupervisorStore } from '../src/supervisor-store.mjs'

const USAGE = `Pemara Harness durable supervisor

Usage:
  pemara-supervisor --db PATH configure --task-id ID --executable PATH --workspace PATH [--arg VALUE] [--max-restarts N] [--backoff-ms 5000,15000,45000]
  pemara-supervisor --db PATH run --task-id ID [--once]
  pemara-supervisor --db PATH status --task-id ID

The command is configured by the host, journaled in schema v2 and never grants
the model commit, publication, network, service or GPU authority.
`

function usageError(message) {
  const error = new Error(`${message}\n\n${USAGE}`)
  error.name = 'SupervisorCliError'
  error.code = 'CLI_USAGE'
  return error
}

function parse(argv) {
  const args = [...argv]
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) return { help: true }
  const dbIndex = args.indexOf('--db')
  if (dbIndex === -1 || dbIndex + 1 >= args.length || args[dbIndex + 1].startsWith('--')) {
    throw usageError('--db PATH is required.')
  }
  const databasePath = resolve(args[dbIndex + 1])
  args.splice(dbIndex, 2)
  const command = args.shift()
  if (!['configure', 'run', 'status'].includes(command)) {
    throw usageError(`Unknown command "${String(command)}".`)
  }
  const options = new Map()
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index]
    if (!token.startsWith('--')) throw usageError(`Unexpected positional argument "${token}".`)
    const key = token.slice(2)
    if (key === 'once') {
      const values = options.get(key) ?? []
      values.push(true)
      options.set(key, values)
      continue
    }
    const value = args[index + 1]
    if (key === '' || value === undefined || value.startsWith('--')) {
      throw usageError(`${token} requires a value.`)
    }
    const values = options.get(key) ?? []
    values.push(value)
    options.set(key, values)
    index += 1
  }
  return { help: false, command, databasePath, options }
}

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

function integer(value, field) {
  if (!/^(0|[1-9][0-9]*)$/.test(String(value))) throw usageError(`${field} must be a non-negative integer.`)
  const number = Number(value)
  if (!Number.isSafeInteger(number)) throw usageError(`${field} exceeds the safe integer range.`)
  return number
}

async function dispatch(parsed) {
  const { command, databasePath, options } = parsed
  if (command === 'configure') {
    allowed(options, ['task-id', 'executable', 'workspace', 'arg', 'max-restarts', 'backoff-ms', 'session-id'])
    const maxRestartsRaw = one(options, 'max-restarts')
    const backoffRaw = one(options, 'backoff-ms')
    const backoffMs = backoffRaw === undefined
      ? undefined
      : backoffRaw.split(',').map((value, index) => {
        const parsedValue = integer(value, `--backoff-ms item ${index + 1}`)
        if (parsedValue === 0) throw usageError('--backoff-ms values must be positive.')
        return parsedValue
      })
    const store = new SupervisorStore({ databasePath })
    try {
      const job = store.configureJob({
        taskId: one(options, 'task-id', { required: true }),
        executable: resolve(one(options, 'executable', { required: true })),
        workspace: resolve(one(options, 'workspace', { required: true })),
        args: options.get('arg') ?? [],
        ...(maxRestartsRaw === undefined ? {} : { maxRestarts: integer(maxRestartsRaw, '--max-restarts') }),
        ...(backoffMs === undefined ? {} : { backoffMs }),
        ...(one(options, 'session-id') === undefined ? {} : { sessionId: one(options, 'session-id') }),
      })
      return { job }
    }
    finally {
      store.close()
    }
  }
  if (command === 'status') {
    allowed(options, ['task-id'])
    const taskId = one(options, 'task-id', { required: true })
    const store = new SupervisorStore({ databasePath })
    try {
      return { job: store.getJob(taskId), attempts: store.listAttempts(taskId) }
    }
    finally {
      store.close()
    }
  }
  allowed(options, ['task-id', 'once'])
  const once = options.has('once')
  if ((options.get('once')?.length ?? 0) > 1) throw usageError('--once may be provided only once.')
  const controller = new AbortController()
  const cancel = () => controller.abort()
  process.once('SIGINT', cancel)
  process.once('SIGTERM', cancel)
  try {
    return await runSupervisor({
      databasePath,
      taskId: one(options, 'task-id', { required: true }),
      once,
      signal: controller.signal,
    })
  }
  finally {
    process.removeListener('SIGINT', cancel)
    process.removeListener('SIGTERM', cancel)
  }
}

try {
  const parsed = parse(process.argv.slice(2))
  if (parsed.help) {
    process.stdout.write(USAGE)
  }
  else {
    const result = await dispatch(parsed)
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)
    if (parsed.command === 'run' && !['COMPLETED', 'STOPPED', 'RUNNING'].includes(result.status)) {
      process.exitCode = 1
    }
  }
}
catch (error) {
  const known = error instanceof SupervisorStateError || typeof error?.code === 'string'
  process.stderr.write(`${JSON.stringify({
    error: {
      code: known ? error.code : 'INTERNAL',
      message: error instanceof Error ? error.message : String(error),
      ...(known && error.details !== undefined ? { details: error.details } : {}),
    },
  })}\n`)
  process.exitCode = 1
}
