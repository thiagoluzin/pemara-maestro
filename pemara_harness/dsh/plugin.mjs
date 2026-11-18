import { randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'

import { BuilderRuntime } from '../src/builder-runtime.mjs'
import { DurableTaskStore, HarnessStateError, TASK_STATUS } from '../src/index.mjs'
import { parseMediaContext, renderMediaContextPrompt } from '../src/media-context.mjs'

export const name = 'pemara-durable-harness'
export const inject = ['tools', 'systemPrompt']

const DEFAULT_LEASE_MS = 30_000

function objectArgs(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new HarnessStateError('INVALID_INPUT', 'Tool arguments must be an object.')
  }
  return value
}

function textArg(args, key, { optional = false } = {}) {
  const value = args[key]
  if (value === undefined && optional) return undefined
  if (typeof value !== 'string' || value.trim() === '') {
    throw new HarnessStateError('INVALID_INPUT', `${key} must be a non-empty string.`)
  }
  return value.trim()
}

function integerArg(args, key, { optional = false } = {}) {
  const value = args[key]
  if (value === undefined && optional) return undefined
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new HarnessStateError('INVALID_INPUT', `${key} must be a positive safe integer.`)
  }
  return value
}

function stringsArg(args, key, { optional = false } = {}) {
  const value = args[key]
  if (value === undefined && optional) return undefined
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || item.trim() === '')) {
    throw new HarnessStateError('INVALID_INPUT', `${key} must be an array of non-empty strings.`)
  }
  return value.map(item => item.trim())
}

function sessionId(exec) {
  const id = exec?.agent?.id
  if (typeof id !== 'string' || id === '') {
    throw new HarnessStateError('AGENT_REQUIRED', 'Pemara harness tools require an owning DSH agent.')
  }
  return id
}

function publicTask(task) {
  return {
    id: task.id,
    objective: task.objective,
    status: task.status,
    ...(task.sessionId === undefined ? {} : { sessionId: task.sessionId }),
    maxRounds: task.maxRounds,
    roundsStarted: task.roundsStarted,
    createdAt: task.createdAt,
    updatedAt: task.updatedAt,
    version: task.version,
    ...(task.lease === undefined ? {} : {
      lease: { owner: task.lease.owner, expiresAt: task.lease.expiresAt },
    }),
    ...(task.checkpoint === undefined ? {} : { checkpoint: task.checkpoint }),
    ...(task.detail === undefined ? {} : { detail: task.detail }),
  }
}

const OUTPUT = {
  schema: { type: 'object' },
  render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
}

function definition({ name: toolName, description, properties, required = [], execute }) {
  return {
    name: toolName,
    description,
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties,
      ...(required.length === 0 ? {} : { required }),
    },
    output: OUTPUT,
    execute,
    presentCall: args => ({ card: 'generic', title: toolName, kind: 'other', rawInput: args }),
  }
}

function resolveConfig(config = {}) {
  const databasePath = typeof config.databasePath === 'string' && config.databasePath.trim() !== ''
    ? config.databasePath.trim()
    : undefined
  if (databasePath === undefined) {
    throw new HarnessStateError('INVALID_CONFIG', 'databasePath is required for pemara-durable-harness.')
  }
  const leaseMs = config.leaseMs ?? DEFAULT_LEASE_MS
  if (!Number.isSafeInteger(leaseMs) || leaseMs < 1_000) {
    throw new HarnessStateError('INVALID_CONFIG', 'leaseMs must be a safe integer of at least 1000 ms.')
  }
  if (config.mediaContextPath !== undefined
    && (typeof config.mediaContextPath !== 'string' || config.mediaContextPath.trim() === '')) {
    throw new HarnessStateError('INVALID_CONFIG', 'mediaContextPath must be a non-empty string when supplied.')
  }
  const rebindValues = [
    config.rebindTaskId,
    config.rebindAttemptId,
    config.rebindAuthority,
  ]
  const hasRebind = rebindValues.some(value => value !== undefined)
  if (hasRebind && rebindValues.some(value => typeof value !== 'string' || value.trim() === '')) {
    throw new HarnessStateError(
      'INVALID_CONFIG',
      'rebindTaskId, rebindAttemptId and rebindAuthority must be supplied together.',
    )
  }
  const builderValues = [config.builderPackagePath, config.builderWorkspace, config.builderContractVersion]
  const hasBuilder = builderValues.some(value => value !== undefined)
  const builderPathsValid = typeof config.builderPackagePath === 'string'
    && config.builderPackagePath.trim() !== ''
    && typeof config.builderWorkspace === 'string'
    && config.builderWorkspace.trim() !== ''
  const builderVersion = String(config.builderContractVersion ?? '').trim()
  if (hasBuilder && (!builderPathsValid || builderVersion === '')) {
    throw new HarnessStateError(
      'INVALID_CONFIG',
      'builderPackagePath, builderWorkspace and builderContractVersion must be supplied together.',
    )
  }
  if (hasBuilder && builderVersion !== '2') {
    throw new HarnessStateError('INVALID_CONFIG', 'Only Builder contract version 2 exposes mutation tools.')
  }
  return {
    databasePath,
    leaseMs,
    ...(typeof config.mediaContextPath === 'string'
      ? { mediaContextPath: config.mediaContextPath.trim() }
      : {}),
    ...(hasRebind ? {
      rebindTaskId: config.rebindTaskId.trim(),
      rebindAttemptId: config.rebindAttemptId.trim(),
      rebindAuthority: config.rebindAuthority.trim(),
    } : {}),
    ...(hasBuilder ? {
      builderPackagePath: config.builderPackagePath.trim(),
      builderWorkspace: config.builderWorkspace.trim(),
      builderContractVersion: 2,
    } : {}),
  }
}

/** Cordis consumes the Standard Schema contract without requiring a runtime dependency. */
export const Config = Object.freeze({
  '~standard': Object.freeze({
    version: 1,
    vendor: 'pemara-harness',
    validate(value) {
      try {
        return { value: resolveConfig(value) }
      }
      catch (error) {
        return {
          issues: [{ message: error instanceof Error ? error.message : String(error) }],
        }
      }
    },
  }),
})

export function registerMediaContext(ctx, path) {
  const mediaContext = parseMediaContext(readFileSync(path))
  return ctx.systemPrompt.section({
    name: 'pemara:media-context',
    order: 114,
    text: renderMediaContextPrompt(mediaContext),
  })
}

export function apply(ctx, config) {
  const resolved = resolveConfig(config)
  const store = new DurableTaskStore({ databasePath: resolved.databasePath })
  let recovery
  let builder
  try {
    recovery = store.recover()
    builder = resolved.builderContractVersion === 2
      ? new BuilderRuntime({
          store,
          packagePath: resolved.builderPackagePath,
          workspaceRoot: resolved.builderWorkspace,
        })
      : undefined
  }
  catch (error) {
    store.close()
    throw error
  }
  const instanceId = randomUUID()
  const leases = new Map()
  const disposers = []

  if (recovery.uncertainEffects.length > 0) {
    ctx.logger?.warn?.(
      `pemara-durable-harness: ${recovery.uncertainEffects.length} effect(s) require verification`,
    )
  }

  function scopedTask(taskId, ownerSession) {
    let task = store.getTask(taskId)
    if (task.sessionId !== ownerSession) {
      if (resolved.rebindTaskId !== taskId) {
        throw new HarnessStateError(
          'TASK_SCOPE',
          `Task "${taskId}" belongs to a different DSH session.`,
        )
      }
      task = store.rebindTaskSession(taskId, {
        ...(task.sessionId === undefined ? {} : { fromSessionId: task.sessionId }),
        toSessionId: ownerSession,
        authority: resolved.rebindAuthority,
        evidence: [
          `Supervisor attempt ${resolved.rebindAttemptId}.`,
          'Host rehydrated the durable checkpoint into a fresh DSH session.',
        ],
      })
    }
    return task
  }

  function leaseFor(taskId, ownerSession) {
    scopedTask(taskId, ownerSession)
    const cached = leases.get(taskId)
    if (cached !== undefined && cached.sessionId === ownerSession) {
      try {
        const renewed = store.heartbeat(taskId, cached.token, resolved.leaseMs)
        cached.expiresAt = renewed.expiresAt
        return cached.token
      }
      catch (error) {
        if (!(error instanceof HarnessStateError)
          || !['LEASE_INVALID', 'LEASE_EXPIRED'].includes(error.code)) throw error
        leases.delete(taskId)
      }
    }
    const lease = store.claimTask(taskId, {
      owner: `dsh:${instanceId}:${ownerSession}`,
      leaseMs: resolved.leaseMs,
    })
    leases.set(taskId, { sessionId: ownerSession, token: lease.token, expiresAt: lease.expiresAt })
    return lease.token
  }

  disposers.push(ctx.systemPrompt.section({
    name: 'pemara:durable-harness',
    order: 113,
    text: 'For long-running work, use harness_task_create once, then harness_task_begin_round at the start '
      + 'of each autonomous work cycle. Persist concrete progress with harness_task_checkpoint before external '
      + 'side effects and after meaningful milestones. Use the same task id throughout. Request completion only '
      + 'with artifact-backed evidence; a separate verifier, never this model call, promotes it to verified.',
  }))

  if (resolved.mediaContextPath !== undefined) {
    try {
      disposers.push(registerMediaContext(ctx, resolved.mediaContextPath))
    }
    catch (error) {
      store.close()
      throw new HarnessStateError(
        'INVALID_CONFIG',
        `Contexto multimodal inválido: ${error instanceof Error ? error.message : String(error)}`,
      )
    }
  }

  disposers.push(ctx.tools.register(definition({
    name: 'harness_task_create',
    description: 'Create a durable task ledger bound to this DSH session for long-running work.',
    properties: {
      task_id: { type: 'string', description: 'Optional stable task id.' },
      objective: { type: 'string', description: 'Concrete completion objective.' },
      max_rounds: { type: 'integer', description: 'Durable upper bound for autonomous rounds.' },
    },
    required: ['objective'],
    async execute(raw, exec) {
      const args = objectArgs(raw)
      const ownerSession = sessionId(exec)
      if (builder !== undefined) {
        const requestedId = args.task_id === undefined ? builder.taskId : textArg(args, 'task_id')
        const requestedObjective = textArg(args, 'objective')
        const requestedRounds = args.max_rounds === undefined
          ? builder.package.max_rounds
          : integerArg(args, 'max_rounds')
        if (requestedId !== builder.taskId
          || requestedObjective !== builder.package.objective
          || requestedRounds !== builder.package.max_rounds) {
          throw new HarnessStateError(
            'BUILDER_TASK_SCOPE',
            'Builder task identity, objective and round budget are fixed by the host package.',
          )
        }
        let task
        try {
          task = store.createTask({
            id: builder.taskId,
            objective: builder.package.objective,
            maxRounds: builder.package.max_rounds,
            sessionId: ownerSession,
          })
        }
        catch (error) {
          if (!(error instanceof HarnessStateError) || error.code !== 'TASK_EXISTS') throw error
          task = scopedTask(builder.taskId, ownerSession)
          if (task.objective !== builder.package.objective
            || task.maxRounds !== builder.package.max_rounds) {
            throw new HarnessStateError(
              'BUILDER_TASK_DRIFT',
              'Existing durable task differs from the host-owned Builder package.',
            )
          }
        }
        return { task: publicTask(task) }
      }
      const task = store.createTask({
        ...(args.task_id === undefined ? {} : { id: textArg(args, 'task_id') }),
        objective: textArg(args, 'objective'),
        ...(args.max_rounds === undefined ? {} : { maxRounds: integerArg(args, 'max_rounds') }),
        sessionId: ownerSession,
      })
      return { task: publicTask(task) }
    },
  })))

  disposers.push(ctx.tools.register(definition({
    name: 'harness_task_get',
    description: 'Read one durable task or list durable tasks belonging to this DSH session.',
    properties: { task_id: { type: 'string', description: 'Task id; omit to list this session.' } },
    async execute(raw, exec) {
      const args = objectArgs(raw)
      const ownerSession = sessionId(exec)
      if (args.task_id !== undefined) {
        return { task: publicTask(scopedTask(textArg(args, 'task_id'), ownerSession)) }
      }
      return {
        tasks: store.listTasks()
          .filter(task => task.sessionId === ownerSession)
          .map(publicTask),
      }
    },
  })))

  disposers.push(ctx.tools.register(definition({
    name: 'harness_task_begin_round',
    description: 'Durably count the next autonomous work round before making its LLM request.',
    properties: {
      task_id: { type: 'string' },
      provider: { type: 'string' },
      model: { type: 'string' },
      prompt_hash: { type: 'string' },
    },
    required: ['task_id'],
    async execute(raw, exec) {
      const args = objectArgs(raw)
      const ownerSession = sessionId(exec)
      const taskId = textArg(args, 'task_id')
      const token = leaseFor(taskId, ownerSession)
      const started = store.startRound(taskId, token, {
        ...(args.provider === undefined ? {} : { provider: textArg(args, 'provider') }),
        ...(args.model === undefined ? {} : { model: textArg(args, 'model') }),
        ...(args.prompt_hash === undefined ? {} : { promptHash: textArg(args, 'prompt_hash') }),
      })
      return { round: started.round, task: publicTask(started.task) }
    },
  })))

  disposers.push(ctx.tools.register(definition({
    name: 'harness_task_checkpoint',
    description: 'Durably persist resumable progress and the single next action for a task.',
    properties: {
      task_id: { type: 'string' },
      summary: { type: 'string' },
      next_action: { type: 'string' },
      artifacts: { type: 'array', items: { type: 'string' } },
      data: {},
    },
    required: ['task_id', 'summary', 'next_action'],
    async execute(raw, exec) {
      const args = objectArgs(raw)
      const ownerSession = sessionId(exec)
      const taskId = textArg(args, 'task_id')
      const token = leaseFor(taskId, ownerSession)
      const task = store.checkpoint(taskId, token, {
        summary: textArg(args, 'summary'),
        nextAction: textArg(args, 'next_action'),
        ...(args.artifacts === undefined ? {} : { artifacts: stringsArg(args, 'artifacts') }),
        ...(args.data === undefined ? {} : { data: args.data }),
      })
      return { task: publicTask(task) }
    },
  })))

  disposers.push(ctx.tools.register(definition({
    name: 'harness_task_request_completion',
    description: 'Submit completion evidence for an independent host-side verification gate.',
    properties: {
      task_id: { type: 'string' },
      summary: { type: 'string' },
      evidence: { type: 'array', items: { type: 'string' } },
    },
    required: ['task_id', 'summary', 'evidence'],
    async execute(raw, exec) {
      const args = objectArgs(raw)
      const ownerSession = sessionId(exec)
      const taskId = textArg(args, 'task_id')
      const token = leaseFor(taskId, ownerSession)
      const task = store.requestCompletion(taskId, token, {
        summary: textArg(args, 'summary'),
        evidence: stringsArg(args, 'evidence'),
      })
      leases.delete(taskId)
      return { task: publicTask(task) }
    },
  })))

  if (builder !== undefined) {
    disposers.push(ctx.tools.register(definition({
      name: 'builder_file_read',
      description: 'Read one text file explicitly allowed by the host-owned Builder v2 contract.',
      properties: {
        task_id: { type: 'string' },
        path: { type: 'string', description: 'Exact contract-relative file path.' },
      },
      required: ['task_id', 'path'],
      async execute(raw, exec) {
        const args = objectArgs(raw)
        const ownerSession = sessionId(exec)
        const taskId = textArg(args, 'task_id')
        scopedTask(taskId, ownerSession)
        return { file: builder.readFile(taskId, textArg(args, 'path')) }
      },
    })))

    disposers.push(ctx.tools.register(definition({
      name: 'builder_file_write',
      description: 'Atomically write one text file allowed by Builder v2, with host baseline and file budget enforcement.',
      properties: {
        task_id: { type: 'string' },
        path: { type: 'string', description: 'Exact contract-relative file path.' },
        content: { type: 'string', description: 'Complete replacement text.' },
      },
      required: ['task_id', 'path', 'content'],
      async execute(raw, exec) {
        const args = objectArgs(raw)
        const ownerSession = sessionId(exec)
        const taskId = textArg(args, 'task_id')
        const token = leaseFor(taskId, ownerSession)
        const result = builder.writeFile(taskId, token, {
          path: textArg(args, 'path'),
          content: typeof args.content === 'string' ? args.content : undefined,
        })
        return {
          write: {
            path: result.effect.result.relativePath,
            sha256: result.sha256,
            bytes: result.effect.result.bytes,
            reused: result.reused,
          },
        }
      },
    })))

    disposers.push(ctx.tools.register(definition({
      name: 'builder_test_run',
      description: 'Run one host-defined Node test command by id; arbitrary commands and shell syntax are unavailable.',
      properties: {
        task_id: { type: 'string' },
        command_id: { type: 'string', description: 'Exact id from the Builder v2 contract.' },
      },
      required: ['task_id', 'command_id'],
      async execute(raw, exec) {
        const args = objectArgs(raw)
        const ownerSession = sessionId(exec)
        const taskId = textArg(args, 'task_id')
        const token = leaseFor(taskId, ownerSession)
        const result = await builder.runTest(taskId, token, textArg(args, 'command_id'))
        return {
          test: {
            status: result.status,
            reused: result.reused,
            ...(result.effect.result === undefined ? {} : { result: result.effect.result }),
          },
        }
      },
    })))
  }

  return async () => {
    for (const dispose of disposers.toReversed()) dispose?.()
    for (const [taskId, lease] of leases) {
      try {
        store.releaseLease(taskId, lease.token)
      }
      catch (error) {
        ctx.logger?.warn?.(`pemara-durable-harness: failed to release ${taskId}: ${String(error)}`)
      }
    }
    leases.clear()
    store.close()
  }
}

export { TASK_STATUS }
