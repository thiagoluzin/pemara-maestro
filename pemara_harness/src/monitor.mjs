import { execFile } from 'node:child_process'
import { createReadStream, existsSync } from 'node:fs'
import { access, readdir, readFile, stat } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, join, normalize, relative, resolve, sep } from 'node:path'
import { DatabaseSync } from 'node:sqlite'
import { pathToFileURL } from 'node:url'
import { promisify } from 'node:util'
import { zstdDecompressSync } from 'node:zlib'

import { CHAT_ID, createCockpitStore, PROJECT_ID } from './cockpit-store.mjs'
import { createProviderStore, PROVIDER_ID } from './provider-store.mjs'
import { createTaskRunner, normalizeTaskSubmission } from './task-runner.mjs'

const execFileAsync = promisify(execFile)
const ZSTD_MAGIC = 0xFD2FB528
const DEFAULT_PORT = 3080
const DEFAULT_REFRESH_MS = 1500
const MAX_TAIL_FRAMES = 1600
const MAX_ACTIVITIES = 180
const MAX_SESSIONS = 8
const STATIC_CONTENT_TYPES = Object.freeze({
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.woff2': 'font/woff2',
})
const SENSITIVE_KEY = /^(?:authorization|proxy-authorization|api[-_]?key|password|passwd|secret|credential|cookie|set-cookie|access[-_]?token|refresh[-_]?token)$/iu
const OMIT_DIRECTORIES = new Set(['.git', '.runtime', 'node_modules'])

export function resolveGitExecutable({ env = process.env, fileExists = existsSync } = {}) {
  const configured = env.PEMARA_GIT_PATH
  const candidates = [
    configured,
    env.ProgramFiles && join(env.ProgramFiles, 'Git', 'cmd', 'git.exe'),
    env.ProgramFiles && join(env.ProgramFiles, 'Git', 'bin', 'git.exe'),
    env['ProgramFiles(x86)'] && join(env['ProgramFiles(x86)'], 'Git', 'cmd', 'git.exe'),
  ].filter(Boolean)
  return candidates.find(candidate => fileExists(candidate)) ?? 'git'
}

const GIT_EXECUTABLE = resolveGitExecutable()

function safeJsonParse(value, fallback = undefined) {
  try {
    return JSON.parse(value)
  }
  catch {
    return fallback
  }
}

function truncateText(value, limit = 3000) {
  const text = String(value ?? '').replaceAll('\u0000', '')
  if (text.length <= limit) return text
  return `${text.slice(0, limit)}\n… [truncado: ${text.length - limit} caracteres]`
}

function redactString(value) {
  return value
    .replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/giu, 'Bearer [redigido]')
    .replace(/\b(api[-_]?key|password|passwd|secret|authorization|access[-_]?token|refresh[-_]?token)\s*[:=]\s*([^\s,;]+)/giu, '$1=[redigido]')
}

export function redactSensitive(value, key = '', depth = 0) {
  if (SENSITIVE_KEY.test(key)) return '[redigido]'
  if (depth > 8) return '[profundidade omitida]'
  if (typeof value === 'string') return redactString(truncateText(value, 6000))
  if (Array.isArray(value)) {
    const items = value.slice(0, 80).map(item => redactSensitive(item, '', depth + 1))
    if (value.length > items.length) items.push(`[${value.length - items.length} itens omitidos]`)
    return items
  }
  if (value !== null && typeof value === 'object') {
    const output = {}
    for (const [entryKey, entryValue] of Object.entries(value).slice(0, 100)) {
      output[entryKey] = redactSensitive(entryValue, entryKey, depth + 1)
    }
    return output
  }
  return value
}

function scanZstdFrames(buffer) {
  const frames = []
  let offset = 0
  while (offset < buffer.length) {
    const start = offset
    if (buffer.length - offset < 4) return { frames, tornStart: start }
    if (buffer.readUInt32LE(offset) !== ZSTD_MAGIC) {
      throw new Error(`session log zstd invalido no byte ${offset}`)
    }
    offset += 4
    if (offset === buffer.length) return { frames, tornStart: start }

    const descriptor = buffer.readUInt8(offset)
    offset += 1
    if ((descriptor & 0x18) !== 0) throw new Error(`cabecalho zstd invalido no byte ${offset - 1}`)
    const contentSizeFlag = descriptor >>> 6
    const singleSegment = (descriptor & 0x20) !== 0
    const checksum = (descriptor & 0x04) !== 0
    const dictionaryFlag = descriptor & 0x03
    const dictionaryBytes = dictionaryFlag === 3 ? 4 : dictionaryFlag
    const contentSizeBytes = contentSizeFlag === 0 ? (singleSegment ? 1 : 0) : 1 << contentSizeFlag
    const headerRemainder = (singleSegment ? 0 : 1) + dictionaryBytes + contentSizeBytes
    if (buffer.length - offset < headerRemainder) return { frames, tornStart: start }
    offset += headerRemainder

    for (;;) {
      if (buffer.length - offset < 3) return { frames, tornStart: start }
      const blockHeader = buffer.readUIntLE(offset, 3)
      offset += 3
      const lastBlock = (blockHeader & 1) !== 0
      const blockType = (blockHeader >>> 1) & 0x03
      const blockSize = blockHeader >>> 3
      if (blockType === 0x03) throw new Error(`bloco zstd reservado no byte ${offset - 3}`)
      const payloadBytes = blockType === 0x01 ? 1 : blockSize
      if (buffer.length - offset < payloadBytes) return { frames, tornStart: start }
      offset += payloadBytes
      if (lastBlock) break
    }

    if (checksum) {
      if (buffer.length - offset < 4) return { frames, tornStart: start }
      offset += 4
    }
    frames.push({ start, end: offset })
  }
  return { frames }
}

function recordLines(buffer, sourcePath, maxTailFrames) {
  if (sourcePath.endsWith('.jsonl')) return buffer.toString('utf8').split(/\r?\n/u).filter(Boolean)
  const { frames } = scanZstdFrames(buffer)
  if (frames.length === 0) throw new Error('session log zstd sem frame completo')
  const tail = frames.length <= maxTailFrames + 1
    ? frames
    : [frames[0], ...frames.slice(-maxTailFrames)]
  const lines = []
  for (const frame of tail) {
    const decoded = zstdDecompressSync(buffer.subarray(frame.start, frame.end)).toString('utf8')
    lines.push(...decoded.split(/\r?\n/u).filter(Boolean))
  }
  return lines
}

function eventTime(record) {
  if (Number.isFinite(record?.time)) return record.time
  if (Number.isFinite(record?.time0)) return record.time0
  return undefined
}

function visibleMessageText(message) {
  if (!Array.isArray(message?.content)) return ''
  return message.content
    .filter(block => block?.type === 'text' && typeof block.text === 'string')
    .map(block => block.text)
    .join('\n')
    .trim()
}

function toolResultText(message) {
  if (!Array.isArray(message?.content)) return { text: '', isError: false }
  const parts = []
  let isError = false
  for (const wrapper of message.content) {
    if (wrapper?.type !== 'tool-result') continue
    isError ||= wrapper.isError === true
    if (!Array.isArray(wrapper.content)) continue
    for (const block of wrapper.content) {
      if (block?.type === 'text' && typeof block.text === 'string') parts.push(block.text)
      if (block?.type === 'resource_link' && typeof block.name === 'string') parts.push(`Artefato: ${block.name}`)
    }
  }
  return { text: parts.join('\n').trim(), isError }
}

function summarizeTool(name, args) {
  if (args === null || typeof args !== 'object') return truncateText(String(args ?? ''), 500)
  const candidate = args.description
    ?? args.command
    ?? args.cmd
    ?? args.file_path
    ?? args.path
    ?? args.pattern
    ?? args.objective
    ?? args.task_id
    ?? args.query
  if (candidate !== undefined) return truncateText(redactString(String(candidate)), 700)
  return truncateText(JSON.stringify(redactSensitive(args)), 700)
}

export function decodeSessionArtifact(buffer, {
  sourcePath = 'session.jsonl.zstd',
  maxTailFrames = MAX_TAIL_FRAMES,
} = {}) {
  const lines = recordLines(buffer, sourcePath, maxTailFrames)
  let session
  let lastEventType = 'session'
  let lastEventAt
  let currentTurn = 0
  let currentStep = 0
  let status = 'idle'
  let usage
  const activities = []
  const toolByCall = new Map()
  const pendingAssistantByTurn = new Map()

  function appendActivity(activity) {
    activities.push(activity)
    if (activity.kind === 'tool' && activity.callId) toolByCall.set(activity.callId, activity)
    if (activities.length > MAX_ACTIVITIES * 2) activities.splice(0, activities.length - MAX_ACTIVITIES)
  }

  for (const line of lines) {
    const record = safeJsonParse(line)
    if (record === undefined || record === null || typeof record !== 'object') continue
    if (record.type === 'session') {
      session = {
        id: String(record.id),
        createdAt: record.createdAt,
        cwd: record.cwd,
        parentSession: record.parentSession,
        agentPreset: record.agentPreset,
      }
      continue
    }
    if (record.type === 'reasoning-chunks') continue

    lastEventType = String(record.type ?? 'unknown')
    lastEventAt = eventTime(record) ?? lastEventAt
    const data = record.data ?? {}
    currentTurn = Number.isFinite(data.turn) ? data.turn : currentTurn
    currentStep = Number.isFinite(data.step) ? data.step : currentStep
    if (record.type === 'turn/start') {
      status = 'running'
      continue
    }
    if (record.type === 'turn/end') {
      const finalMessage = pendingAssistantByTurn.get(String(data.turn ?? currentTurn))
      if (finalMessage !== undefined) appendActivity(finalMessage)
      pendingAssistantByTurn.delete(String(data.turn ?? currentTurn))
      status = 'completed'
      continue
    }
    if (record.type === 'step/start') {
      status = 'running'
      continue
    }
    if (record.type === 'text-chunks') continue
    if (record.type === 'tool-call-chunks') {
      status = 'running'
      continue
    }
    if (record.type === 'assistant/chunk') {
      const chunk = data.chunk
      if (chunk?.type === 'usage') usage = redactSensitive(chunk.usage)
      continue
    }
    if (record.type === 'assistant/message') {
      const text = visibleMessageText(data.message)
      if (text !== '') {
        pendingAssistantByTurn.set(String(data.turn ?? currentTurn), {
          id: `message:${String(record.seq)}`,
          kind: 'message',
          seq: record.seq,
          time: record.time,
          turn: data.turn,
          step: data.step,
          text: truncateText(redactString(text), 5000),
        })
      }
      continue
    }
    if (record.type === 'user/message') {
      const text = visibleMessageText(data.message)
      if (text !== '') {
        appendActivity({
          id: `user:${String(record.seq)}`,
          kind: 'user',
          seq: record.seq,
          time: record.time,
          turn: data.turn,
          text: truncateText(redactString(text), 5000),
        })
      }
      continue
    }
    if (record.type === 'tool/call') {
      pendingAssistantByTurn.delete(String(data.turn ?? currentTurn))
      const parsedArgs = typeof data.arguments === 'string'
        ? (safeJsonParse(data.arguments, { raw: data.arguments }))
        : data.arguments
      const args = redactSensitive(parsedArgs)
      appendActivity({
        id: `tool:${String(data.callId ?? record.seq)}`,
        kind: 'tool',
        callId: data.callId,
        seq: record.seq,
        time: record.time,
        turn: data.turn,
        step: data.step,
        name: String(data.name ?? 'tool'),
        status: 'running',
        summary: summarizeTool(data.name, args),
        detail: truncateText(JSON.stringify(args, null, 2), 2200),
        result: '',
        files: [],
      })
      continue
    }
    if (record.type === 'tool/result') {
      const callId = data.message?.source?.callId
      let activity = toolByCall.get(callId)
      if (activity === undefined) {
        activity = {
          id: `tool:${String(callId ?? record.seq)}`,
          kind: 'tool',
          callId,
          seq: record.seq,
          time: record.time,
          turn: data.turn,
          step: data.step,
          name: 'tool',
          status: 'running',
          summary: 'Resultado de ferramenta',
          detail: '',
          result: '',
          files: [],
        }
        appendActivity(activity)
      }
      const outcome = toolResultText(data.message)
      activity.status = outcome.isError ? 'error' : 'success'
      activity.endedAt = record.time
      activity.result = truncateText(redactString(outcome.text), 4500)
      activity.files = Array.isArray(data.meta?.diffs)
        ? data.meta.diffs.map(diff => diff?.path).filter(path => typeof path === 'string').slice(0, 30)
        : []
      continue
    }
    if (record.type === 'step/end') continue
  }

  return {
    session: session ?? { id: 'sessao-desconhecida' },
    sourcePath,
    status,
    currentTurn,
    currentStep,
    lastEventType,
    lastEventAt,
    liveText: '',
    usage,
    activities: activities.slice(-MAX_ACTIVITIES),
  }
}

export function parseTodoProgress(markdown) {
  const items = []
  let section = 'Geral'
  for (const line of String(markdown ?? '').split(/\r?\n/u)) {
    const heading = /^#{1,6}\s+(.+?)\s*$/u.exec(line)
    if (heading !== null) {
      section = heading[1]
      continue
    }
    const checkbox = /^\s*-\s+\[([ xX])\]\s+(.+?)\s*$/u.exec(line)
    if (checkbox === null) continue
    items.push({ section, done: checkbox[1].toLowerCase() === 'x', text: checkbox[2] })
  }
  return {
    completed: items.filter(item => item.done).length,
    total: items.length,
    items: items.slice(0, 160),
  }
}

function statusPath(line) {
  if (typeof line !== 'string' || line.length < 4 || line.startsWith('##')) return undefined
  let path = line.slice(3).trim()
  if (path.includes(' -> ')) path = path.split(' -> ').at(-1)
  if (path.startsWith('"') && path.endsWith('"')) path = safeJsonParse(path, path.slice(1, -1))
  return String(path).replaceAll('\\', '/')
}

export function evaluateTaskContract(taskPackage, statusLines) {
  const allowed = new Set(Array.isArray(taskPackage?.allowed_paths)
    ? taskPackage.allowed_paths.map(path => String(path).replaceAll('\\', '/'))
    : [])
  const touched = [...new Set((statusLines ?? []).map(statusPath).filter(Boolean))].sort()
  const violations = touched.filter(path => !allowed.has(path))
  const maxFiles = Number.isFinite(taskPackage?.max_files_changed) ? taskPackage.max_files_changed : undefined
  const overBudget = maxFiles !== undefined && touched.length > maxFiles
  return {
    taskId: String(taskPackage?.task_id ?? 'pacote-desconhecido'),
    state: violations.length > 0 || overBudget ? 'violated' : 'clean',
    stopRequired: violations.length > 0 || overBudget,
    touched,
    touchedCount: touched.length,
    allowedCount: allowed.size,
    maxFiles,
    violations,
    overBudget,
  }
}

async function activeTaskContract(projectRoot, todo) {
  const active = todo.items.find(item => !item.done && /\[QWEN\]/u.test(item.text))
  const taskId = /\bQB-\d+\b/u.exec(active?.text ?? '')?.[0]
  if (taskId === undefined) return { state: 'inactive', stopRequired: false }

  const packagePath = join(projectRoot, 'evidence', 'packages', `${taskId}.json`)
  const worktree = resolve(projectRoot, '..', 'worktrees', 'pemara-harness-qwen', taskId)
  if (!(await pathExists(packagePath)) || !(await pathExists(worktree))) {
    return {
      taskId,
      state: 'inactive',
      stopRequired: false,
      packagePath,
      worktree,
    }
  }
  try {
    const taskPackage = JSON.parse(await readFile(packagePath, 'utf8'))
    const { stdout } = await execFileAsync(GIT_EXECUTABLE, [
      '-c', `safe.directory=${worktree}`,
      '-c', 'core.quotepath=false',
      'status', '--porcelain=v1', '--untracked-files=all',
    ], {
      cwd: worktree,
      windowsHide: true,
      timeout: 2500,
      maxBuffer: 256 * 1024,
    })
    return {
      ...evaluateTaskContract(taskPackage, stdout.split(/\r?\n/u).filter(Boolean)),
      packagePath,
      worktree,
    }
  }
  catch (error) {
    return {
      taskId,
      state: 'unavailable',
      stopRequired: true,
      packagePath,
      worktree,
      detail: error instanceof Error ? error.message : String(error),
      violations: [],
      touched: [],
    }
  }
}

async function pathExists(path) {
  try {
    await access(path)
    return true
  }
  catch {
    return false
  }
}

async function findSessionArtifacts(root) {
  if (!(await pathExists(root))) return []
  const output = []
  const stack = [root]
  while (stack.length > 0) {
    const directory = stack.pop()
    const entries = await readdir(directory, { withFileTypes: true })
    for (const entry of entries) {
      const path = join(directory, entry.name)
      if (entry.isDirectory()) stack.push(path)
      else if (entry.isFile() && (entry.name === 'session.jsonl.zstd' || entry.name === 'session.jsonl')) {
        const metadata = await stat(path)
        output.push({ path, size: metadata.size, mtimeMs: metadata.mtimeMs })
      }
    }
  }
  return output
}

async function readSessions(projectRoot) {
  const roots = [
    { kind: 'pemara', path: join(projectRoot, '.runtime', 'dsh-home', 'sessions') },
    { kind: 'builder', path: join(projectRoot, '.runtime', 'dsh-home-builder', 'sessions') },
  ]
  const artifacts = (await Promise.all(roots.map(async root => (
    await findSessionArtifacts(root.path)
  ).map(artifact => ({ ...artifact, kind: root.kind })))))
    .flat()
    .sort((left, right) => right.mtimeMs - left.mtimeMs)
    .slice(0, MAX_SESSIONS)

  const sessions = []
  for (let index = 0; index < artifacts.length; index += 1) {
    const artifact = artifacts[index]
    try {
      const decoded = decodeSessionArtifact(await readFile(artifact.path), {
        sourcePath: artifact.path,
        maxTailFrames: index < 2 ? MAX_TAIL_FRAMES : 120,
      })
      sessions.push({
        ...decoded,
        kind: artifact.kind,
        size: artifact.size,
        updatedAt: artifact.mtimeMs,
      })
    }
    catch (error) {
      sessions.push({
        session: { id: artifact.path.split(sep).at(-2) ?? 'sessao-invalida' },
        kind: artifact.kind,
        sourcePath: artifact.path,
        size: artifact.size,
        updatedAt: artifact.mtimeMs,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
        activities: [],
      })
    }
  }
  return sessions
}

function sessionUserText(session) {
  return session?.activities?.find(activity => activity.kind === 'user' && activity.text)?.text ?? ''
}

function sessionPreview(session) {
  const activity = [...(session?.activities ?? [])].reverse().find(item => item.kind === 'message' || item.kind === 'user')
  return activity?.text?.split(/\r?\n/u)[0]?.slice(0, 140) ?? null
}

function responseFromCompletedJob(job) {
  const terminal = job?.status === 'completed' || job?.status === 'failed' || job?.status === 'interrupted'
  if (!terminal) return null
  if (job.status !== 'completed') return String(job.stderr || job.detail || 'A execução foi interrompida antes de produzir uma resposta.').trim()
  let text = String(job.stdout ?? '').replaceAll('\r', '')
  const marker = 'Executando tarefa...'
  const markerOffset = text.lastIndexOf(marker)
  if (markerOffset >= 0) text = text.slice(markerOffset + marker.length)
  text = text.replace(/\nTarefa encerrada pelo runtime(?: com codigo \d+)?\.[\s\S]*$/u, '').trim()
  return text || String(job.detail || 'A tarefa foi concluída, mas o runtime não registrou texto de resposta.').trim()
}

async function reconcileCompletedChat({ cockpitStore, chats, job }) {
  if (!job?.chatId || !['completed', 'failed', 'interrupted'].includes(job.status)) return chats
  const chat = chats.find(item => item.id === job.chatId)
  if (chat === undefined) return chats
  const messages = Array.isArray(chat.messages) ? chat.messages : []
  const response = responseFromCompletedJob(job)
  if (!messages.some(message => message.role === 'user' && message.text === job.task)) {
    await cockpitStore.appendChatMessage(chat.id, {
      role: 'user',
      text: job.task,
      jobId: job.id,
      createdAt: job.createdAt ?? Date.now(),
    })
  }
  if (!messages.some(message => message.jobId === job.id && (message.role === 'assistant' || message.role === 'system'))) {
    if (response) {
      await cockpitStore.appendChatMessage(chat.id, {
        role: job.status === 'completed' ? 'assistant' : 'system',
        text: response,
        jobId: job.id,
        createdAt: job.finishedAt ?? job.heartbeatAt ?? Date.now(),
      })
    }
  }
  const preview = response?.split(/\r?\n/u)[0]?.slice(0, 140) ?? chat.preview
  if (chat.status !== job.status || chat.preview !== preview) {
    await cockpitStore.updateChat(chat.id, {
      status: job.status,
      preview,
      updatedAt: job.finishedAt ?? job.heartbeatAt ?? Date.now(),
    })
  }
  return cockpitStore.listChats()
}

function mergeChatViews({ chats, sessions, projects, job }) {
  const visible = []
  const matchedSessions = new Set()
  const projectById = new Map(projects.map(project => [project.id, project]))
  for (const chat of chats) {
    const matching = sessions.find(session => (
      (chat.sessionId !== null && chat.sessionId !== undefined && session.session?.id === chat.sessionId)
      || (chat.lastTask && sessionUserText(session) === chat.lastTask)
    ))
    if (matching !== undefined) matchedSessions.add(matching.session?.id)
    const active = job?.chatId === chat.id ? job : undefined
    const project = projectById.get(chat.projectId)
    visible.push({
      ...chat,
      projectPath: project?.path ?? chat.projectPath,
      sessionId: matching?.session?.id ?? chat.sessionId ?? null,
      status: active?.status ?? matching?.status ?? chat.status,
      updatedAt: Math.max(chat.updatedAt ?? 0, matching?.updatedAt ?? 0, active?.heartbeatAt ?? 0),
      preview: sessionPreview(matching) ?? chat.preview ?? chat.lastTask ?? null,
    })
  }
  for (const session of sessions) {
    const sessionId = session.session?.id
    if (sessionId === undefined || matchedSessions.has(sessionId)) continue
    const project = projects.find(item => item.path === session.session?.cwd)
    visible.push({
      id: `legacy-${sessionId}`,
      title: sessionUserText(session) || `Sessão ${sessionId.slice(0, 12)}`,
      projectId: project?.id ?? null,
      projectPath: project?.path ?? null,
      createdAt: session.updatedAt,
      updatedAt: session.updatedAt,
      status: session.status,
      sessionId,
      jobId: null,
      lastTask: sessionUserText(session) || null,
      preview: sessionPreview(session),
      legacy: true,
    })
  }
  return visible.sort((left, right) => (right.updatedAt ?? 0) - (left.updatedAt ?? 0)).slice(0, 80)
}

function parseDatabaseJson(value) {
  if (typeof value !== 'string' || value === '') return undefined
  return safeJsonParse(value)
}

function readLedger(path, kind) {
  if (!existsSync(path)) return []
  let database
  try {
    database = new DatabaseSync(path, { readOnly: true })
    const rows = database.prepare(`
      SELECT id, objective, status, session_id, max_rounds, rounds_started,
             updated_at, version, status_detail_json
      FROM tasks ORDER BY updated_at DESC LIMIT 50
    `).all()
    return rows.map(row => ({
      kind,
      id: row.id,
      objective: row.objective,
      status: row.status,
      sessionId: row.session_id ?? undefined,
      maxRounds: row.max_rounds,
      roundsStarted: row.rounds_started,
      updatedAt: row.updated_at,
      version: row.version,
      detail: parseDatabaseJson(row.status_detail_json),
    }))
  }
  catch (error) {
    return [{ kind, status: 'LEDGER_ERROR', id: `${kind}-ledger-error`, objective: error instanceof Error ? error.message : String(error) }]
  }
  finally {
    database?.close()
  }
}

async function recentProjectFiles(projectRoot) {
  const output = []
  const stack = [projectRoot]
  while (stack.length > 0 && output.length < 1200) {
    const directory = stack.pop()
    let entries
    try {
      entries = await readdir(directory, { withFileTypes: true })
    }
    catch {
      continue
    }
    for (const entry of entries) {
      if (entry.isDirectory() && OMIT_DIRECTORIES.has(entry.name)) continue
      const path = join(directory, entry.name)
      if (entry.isDirectory()) stack.push(path)
      else if (entry.isFile()) {
        const metadata = await stat(path)
        output.push({
          path: relative(projectRoot, path).replaceAll('\\', '/'),
          updatedAt: metadata.mtimeMs,
          size: metadata.size,
        })
      }
    }
  }
  return output.sort((left, right) => right.updatedAt - left.updatedAt).slice(0, 24)
}

async function gitStatus(projectRoot) {
  try {
    const { stdout } = await execFileAsync(GIT_EXECUTABLE, ['-c', `safe.directory=${projectRoot}`, 'status', '--short', '--branch'], {
      cwd: projectRoot,
      windowsHide: true,
      timeout: 2500,
      maxBuffer: 256 * 1024,
    })
    return stdout.trim().split(/\r?\n/u).filter(Boolean).slice(0, 120)
  }
  catch (error) {
    return [`git indisponivel: ${error instanceof Error ? error.message : String(error)}`]
  }
}

async function probeJson(url, timeoutMs = 900) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) })
    if (!response.ok) return { ok: false, status: response.status }
    return { ok: true, status: response.status, data: await response.json() }
  }
  catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) }
  }
}

export function parseQwenSlotProgress(slots) {
  const values = Array.isArray(slots) ? slots : slots === undefined || slots === null ? [] : [slots]
  const active = values.find(slot => slot?.is_processing === true)
  if (active === undefined) return { active: false }
  const token = Array.isArray(active.next_token) ? active.next_token[0] : undefined
  return {
    active: true,
    slot: active.id,
    taskId: active.id_task,
    contextTokens: active.n_ctx,
    promptTokens: active.n_prompt_tokens,
    decodedTokens: token?.n_decoded,
    remainingTokens: token?.n_remain,
    maxOutputTokens: active.params?.n_predict,
  }
}

async function healthSnapshot(enabled) {
  if (!enabled) return { qwen: { state: 'disabled' }, comfy: { state: 'disabled' } }
  const [qwen, comfy, slots] = await Promise.all([
    probeJson('http://127.0.0.1:11436/v1/models'),
    probeJson('http://127.0.0.1:8188/queue'),
    // Prompt evaluation can briefly delay /slots on a busy local GGUF. Give
    // this diagnostic probe more time so the visual panel does not flicker
    // offline while the model is actually working.
    probeJson('http://127.0.0.1:11436/slots', 3000),
  ])
  const qwenModel = qwen.ok && Array.isArray(qwen.data?.data) ? qwen.data.data[0] : undefined
  const running = comfy.ok && Array.isArray(comfy.data?.queue_running) ? comfy.data.queue_running.length : undefined
  const pending = comfy.ok && Array.isArray(comfy.data?.queue_pending) ? comfy.data.queue_pending.length : undefined
  return {
    qwen: {
      state: qwen.ok ? 'ready' : 'offline',
      model: qwenModel?.id,
      context: qwenModel?.meta?.n_ctx_train ?? qwenModel?.n_ctx,
      generation: slots.ok ? parseQwenSlotProgress(slots.data) : { active: false },
      detail: qwen.ok ? undefined : qwen.error ?? `HTTP ${String(qwen.status)}`,
    },
    comfy: {
      state: comfy.ok ? (running > 0 ? 'busy' : 'idle') : 'offline',
      running,
      pending,
      detail: comfy.ok ? undefined : comfy.error ?? `HTTP ${String(comfy.status)}`,
    },
  }
}

export function normalizeSessionLiveness(sessions, health, now = Date.now()) {
  if (health?.qwen?.state !== 'offline') return sessions
  return sessions.map(session => {
    if (session.status !== 'running' || !Number.isFinite(session.updatedAt) || now - session.updatedAt <= 15_000) {
      return session
    }
    return {
      ...session,
      status: 'interrupted',
      interruption: 'O modelo local está offline e esta sessão deixou de registrar eventos.',
    }
  })
}

export async function createMonitorSnapshot({ projectRoot, workspaceRoot = resolve(projectRoot, '..'), probeHealth = true, taskRunner, cockpitStore = createCockpitStore({ projectRoot, workspaceRoot }), providerStore = createProviderStore({ projectRoot }) }) {
  const todoPath = join(projectRoot, 'tasks', 'todo.md')
  const todoText = await readFile(todoPath, 'utf8').catch(() => '')
  const todo = parseTodoProgress(todoText)
  const [sessions, health, files, repository, contract, job, projects, initialChats, providers] = await Promise.all([
    readSessions(projectRoot),
    healthSnapshot(probeHealth),
    recentProjectFiles(projectRoot),
    gitStatus(projectRoot),
    activeTaskContract(projectRoot, todo),
    taskRunner === undefined ? { status: 'disabled' } : taskRunner.snapshot(),
    cockpitStore.listProjects(),
    cockpitStore.listChats(),
    providerStore.listProviders(),
  ])
  const chats = await reconcileCompletedChat({ cockpitStore, chats: initialChats, job })
  const tasks = [
    ...readLedger(join(projectRoot, '.runtime', 'dsh-home', 'pemara', 'ledger.sqlite'), 'pemara'),
    ...readLedger(join(projectRoot, '.runtime', 'dsh-home-builder', 'pemara-builder', 'ledger.sqlite'), 'builder'),
  ]
  const visibleSessions = normalizeSessionLiveness(sessions, health)
  const visibleChats = mergeChatViews({ chats, sessions: visibleSessions, projects, job })
  return {
    generatedAt: Date.now(),
    projectRoot,
    control: {
      taskSubmission: taskRunner !== undefined,
      singleActiveTask: true,
      job: redactSensitive(job),
    },
    health,
    projects,
    providers,
    chats: visibleChats,
    sessions: visibleSessions,
    tasks,
    todo,
    contract,
    files,
    repository,
  }
}

function trustedHost(requestHost) {
  if (typeof requestHost !== 'string') return false
  try {
    const parsed = new URL(`http://${requestHost}`)
    return parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost' || parsed.hostname === '[::1]'
  }
  catch {
    return false
  }
}

function securityHeaders(response, contentType) {
  response.setHeader('Cache-Control', 'no-store')
  response.setHeader('Content-Type', contentType)
  response.setHeader('Referrer-Policy', 'no-referrer')
  response.setHeader('X-Content-Type-Options', 'nosniff')
  response.setHeader('X-Frame-Options', 'DENY')
  response.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
}

function sendJson(response, status, value) {
  securityHeaders(response, 'application/json; charset=utf-8')
  response.statusCode = status
  response.end(JSON.stringify(value))
}

async function readJsonBody(request, maxBytes = 32 * 1024) {
  const chunks = []
  let total = 0
  for await (const chunk of request) {
    total += chunk.length
    if (total > maxBytes) {
      const error = new Error('O pedido ultrapassa o limite permitido.')
      error.code = 'BODY_TOO_LARGE'
      throw error
    }
    chunks.push(chunk)
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'))
  }
  catch {
    const error = new Error('JSON inválido.')
    error.code = 'INVALID_JSON'
    throw error
  }
}

function trustedMutation(request, kind, { contentType } = {}) {
  if (request.headers['x-pemara-request'] !== kind) return false
  if (contentType !== undefined
    && !String(request.headers['content-type'] ?? '').toLowerCase().startsWith(contentType)) return false
  const origin = request.headers.origin
  if (typeof origin !== 'string' || typeof request.headers.host !== 'string') return false
  try {
    const parsed = new URL(origin)
    return parsed.protocol === 'http:'
      && parsed.host === request.headers.host
      && (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost' || parsed.hostname === '[::1]')
  }
  catch {
    return false
  }
}

function safeStaticPath(staticRoot, pathname) {
  const requested = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '')
  const resolved = resolve(staticRoot, normalize(requested))
  const boundary = `${resolve(staticRoot)}${sep}`
  if (resolved !== resolve(staticRoot) && !resolved.startsWith(boundary)) return undefined
  return resolved
}

function invalidRequest(message, code = 'INVALID_REQUEST') {
  const error = new Error(message)
  error.code = code
  return error
}

function normalizeProjectRequest(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw invalidRequest('O projeto deve ser um objeto JSON.')
  const keys = Object.keys(value)
  if (keys.some(key => !['path', 'name'].includes(key))) throw invalidRequest('Os únicos campos permitidos são path e name.')
  if (typeof value.path !== 'string' || value.path.trim() === '') throw invalidRequest('O caminho do projeto é obrigatório.', 'INVALID_PROJECT_PATH')
  if (value.name !== undefined && (typeof value.name !== 'string' || value.name.length > 120)) throw invalidRequest('O nome do projeto é inválido.', 'INVALID_PROJECT_NAME')
  return { path: value.path, name: value.name }
}

function normalizeChatRequest(value) {
  if (value === undefined) return {}
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw invalidRequest('O chat deve ser um objeto JSON.')
  const keys = Object.keys(value)
  if (keys.some(key => !['projectId', 'title', 'providerId'].includes(key))) throw invalidRequest('Os únicos campos permitidos são projectId, title e providerId.')
  if (value.projectId !== undefined && (typeof value.projectId !== 'string' || !PROJECT_ID.test(value.projectId))) {
    throw invalidRequest('O identificador do projeto é inválido.', 'INVALID_PROJECT_ID')
  }
  if (value.title !== undefined && (typeof value.title !== 'string' || value.title.length > 120)) {
    throw invalidRequest('O título do chat é inválido.', 'INVALID_CHAT_TITLE')
  }
  if (value.providerId !== undefined && (typeof value.providerId !== 'string' || !PROVIDER_ID.test(value.providerId))) {
    throw invalidRequest('O identificador do provedor é inválido.', 'INVALID_PROVIDER_ID')
  }
  return { projectId: value.projectId, title: value.title, providerId: value.providerId }
}

function normalizeTaskRequest(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw invalidRequest('A tarefa deve ser um objeto JSON.')
  const keys = Object.keys(value)
  if (keys.some(key => !['task', 'attachmentIds', 'chatId', 'projectId'].includes(key))) {
    throw invalidRequest('Os campos permitidos são task, attachmentIds, chatId e projectId.')
  }
  if (value.chatId !== undefined && (typeof value.chatId !== 'string' || !CHAT_ID.test(value.chatId))) {
    throw invalidRequest('O identificador do chat é inválido.', 'INVALID_CHAT_ID')
  }
  if (value.projectId !== undefined && (typeof value.projectId !== 'string' || !PROJECT_ID.test(value.projectId))) {
    throw invalidRequest('O identificador do projeto é inválido.', 'INVALID_PROJECT_ID')
  }
  return {
    ...normalizeTaskSubmission({ task: value.task, attachmentIds: value.attachmentIds }),
    chatId: value.chatId,
    projectId: value.projectId,
  }
}

export function createMonitorServer({
  projectRoot,
  workspaceRoot = resolve(projectRoot, '..'),
  staticRoot = join(projectRoot, 'web-monitor'),
  probeHealth = true,
  refreshMs = DEFAULT_REFRESH_MS,
  taskRunner = createTaskRunner({ projectRoot, workspaceRoot }),
  providerStore,
} = {}) {
  if (typeof projectRoot !== 'string' || projectRoot.trim() === '') throw new TypeError('projectRoot is required')
  const resolvedWorkspace = resolve(workspaceRoot)
  const cockpitStore = createCockpitStore({ projectRoot: resolve(projectRoot), workspaceRoot: resolvedWorkspace })
  const resolvedProviderStore = providerStore ?? createProviderStore({ projectRoot: resolve(projectRoot) })
  const snapshotOptions = { projectRoot: resolve(projectRoot), workspaceRoot: resolvedWorkspace, probeHealth, taskRunner, cockpitStore, providerStore: resolvedProviderStore }
  const snapshotTtlMs = Math.max(250, refreshMs)
  let cachedSnapshot
  let cachedAt = 0
  let pendingSnapshot

  async function getSnapshot() {
    if (cachedSnapshot !== undefined && Date.now() - cachedAt < snapshotTtlMs) return cachedSnapshot
    if (pendingSnapshot !== undefined) return pendingSnapshot
    pendingSnapshot = createMonitorSnapshot(snapshotOptions)
      .then(snapshot => {
        cachedSnapshot = snapshot
        cachedAt = Date.now()
        return snapshot
      })
      .finally(() => { pendingSnapshot = undefined })
    return pendingSnapshot
  }

  return createServer(async (request, response) => {
    if (!trustedHost(request.headers.host)) {
      sendJson(response, 403, { error: 'host_not_trusted' })
      return
    }
    const url = new URL(request.url ?? '/', 'http://127.0.0.1')
    if (url.pathname === '/api/providers') {
      if (request.method !== 'GET') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      try {
        sendJson(response, 200, { providers: await resolvedProviderStore.listProviders() })
      }
      catch (error) {
        sendJson(response, 500, { error: 'providers_unavailable', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    const providerPatch = /^\/api\/providers\/([a-z0-9-]+)$/u.exec(url.pathname)
    if (providerPatch !== null) {
      if (request.method !== 'PATCH') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'provider', { contentType: 'application/json' })) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        const body = await readJsonBody(request)
        if (body === null || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).some(key => key !== 'enabled')) {
          throw invalidRequest('O único campo permitido é enabled.')
        }
        const provider = await resolvedProviderStore.setEnabled(providerPatch[1], body.enabled)
        cachedSnapshot = undefined
        cachedAt = 0
        sendJson(response, 200, { provider: redactSensitive(provider) })
      }
      catch (error) {
        const status = error?.code === 'PROVIDER_NOT_FOUND' ? 404 : error?.code === 'BODY_TOO_LARGE' ? 413 : 400
        sendJson(response, status, { error: error?.code ?? 'invalid_provider', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    if (url.pathname === '/api/projects') {
      if (request.method === 'GET') {
        try {
          sendJson(response, 200, { projects: await cockpitStore.listProjects() })
        }
        catch (error) {
          sendJson(response, 500, { error: 'projects_unavailable', message: error instanceof Error ? error.message : String(error) })
        }
        return
      }
      if (request.method !== 'POST') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'project', { contentType: 'application/json' })) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        const project = await cockpitStore.registerProject(normalizeProjectRequest(await readJsonBody(request)))
        cachedSnapshot = undefined
        cachedAt = 0
        sendJson(response, 201, { project: redactSensitive(project) })
      }
      catch (error) {
        const status = error?.code === 'PROJECT_NOT_FOUND' ? 404
          : error?.code === 'PROJECT_OUTSIDE_WORKSPACE' || error?.code === 'PROJECT_RUNTIME_FORBIDDEN' ? 422
            : error?.code === 'BODY_TOO_LARGE' ? 413
              : 400
        sendJson(response, status, { error: error?.code ?? 'invalid_project', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    if (url.pathname === '/api/chats') {
      if (request.method === 'GET') {
        try {
          sendJson(response, 200, { chats: await cockpitStore.listChats() })
        }
        catch (error) {
          sendJson(response, 500, { error: 'chats_unavailable', message: error instanceof Error ? error.message : String(error) })
        }
        return
      }
      if (request.method !== 'POST') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'chat', { contentType: 'application/json' })) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        const input = normalizeChatRequest(await readJsonBody(request))
        const project = input.projectId === undefined ? (await cockpitStore.listProjects())[0] : await cockpitStore.getProject(input.projectId)
        if (project === undefined) throw invalidRequest('Projeto não encontrado.', 'PROJECT_NOT_FOUND')
        if (input.providerId !== undefined) await resolvedProviderStore.requireRunnableModel(input.providerId)
        const chat = await cockpitStore.createChat({ projectId: project.id, providerId: input.providerId ?? 'local-qwen' })
        const updated = input.title === undefined ? chat : await cockpitStore.updateChat(chat.id, { title: input.title })
        cachedSnapshot = undefined
        cachedAt = 0
        sendJson(response, 201, { chat: redactSensitive(updated) })
      }
      catch (error) {
        const status = error?.code === 'PROJECT_NOT_FOUND' ? 404 : error?.code === 'BODY_TOO_LARGE' ? 413 : 400
        sendJson(response, status, { error: error?.code ?? 'invalid_chat', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    const chatPatch = /^\/api\/chats\/(chat-[0-9a-f-]+)$/u.exec(url.pathname)
    if (chatPatch !== null) {
      if (request.method !== 'PATCH') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'chat', { contentType: 'application/json' })) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        const input = normalizeChatRequest(await readJsonBody(request))
        if (input.providerId !== undefined) await resolvedProviderStore.requireRunnableModel(input.providerId)
        const updated = await cockpitStore.updateChat(chatPatch[1], input)
        cachedSnapshot = undefined
        cachedAt = 0
        sendJson(response, 200, { chat: redactSensitive(updated) })
      }
      catch (error) {
        const status = error?.code === 'CHAT_NOT_FOUND' || error?.code === 'PROJECT_NOT_FOUND' ? 404 : error?.code === 'BODY_TOO_LARGE' ? 413 : 400
        sendJson(response, status, { error: error?.code ?? 'invalid_chat', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    if (url.pathname === '/api/attachments') {
      if (request.method !== 'POST') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'attachment')) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        const rawFilename = request.headers['x-pemara-filename']
        if (typeof rawFilename !== 'string' || rawFilename.length > 720) {
          const error = new Error('Nome do anexo ausente ou inválido.')
          error.code = 'INVALID_ATTACHMENT'
          throw error
        }
        let filename
        try { filename = decodeURIComponent(rawFilename) }
        catch {
          const error = new Error('Nome do anexo não está codificado corretamente.')
          error.code = 'INVALID_ATTACHMENT'
          throw error
        }
        const rawLength = request.headers['content-length']
        const contentLength = rawLength === undefined ? undefined : Number(rawLength)
        const attachment = await taskRunner.stageAttachment({
          stream: request,
          filename,
          mediaType: String(request.headers['content-type'] ?? ''),
          contentLength,
        })
        sendJson(response, 201, { attachment: redactSensitive(attachment) })
      }
      catch (error) {
        const status = error?.code === 'ATTACHMENT_TOO_LARGE' ? 413
          : error?.code === 'UNSUPPORTED_MEDIA' ? 415
            : 400
        sendJson(response, status, { error: error?.code ?? 'invalid_attachment', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    const attachmentDelete = /^\/api\/attachments\/(att-[0-9a-f-]+)$/u.exec(url.pathname)
    if (attachmentDelete !== null) {
      if (request.method !== 'DELETE') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'attachment')) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        await taskRunner.discardAttachment(attachmentDelete[1])
        response.statusCode = 204
        response.end()
      }
      catch (error) {
        sendJson(response, 400, { error: error?.code ?? 'invalid_attachment', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    if (url.pathname === '/api/tasks') {
      if (request.method !== 'POST') {
        sendJson(response, 405, { error: 'method_not_allowed' })
        return
      }
      if (!trustedMutation(request, 'task', { contentType: 'application/json' })) {
        sendJson(response, 403, { error: 'mutation_not_trusted' })
        return
      }
      try {
        const submission = normalizeTaskRequest(await readJsonBody(request))
        const projects = await cockpitStore.listProjects()
        const project = submission.projectId === undefined
          ? projects[0]
          : projects.find(item => item.id === submission.projectId)
        if (project === undefined) throw invalidRequest('Projeto não encontrado.', 'PROJECT_NOT_FOUND')
        const chat = submission.chatId === undefined ? await cockpitStore.createChat({ projectId: project.id }) : await cockpitStore.getChat(submission.chatId)
        if (chat === undefined) throw invalidRequest('Chat não encontrado.', 'CHAT_NOT_FOUND')
        if (chat.projectId !== project.id) throw invalidRequest('O chat e o projeto não correspondem.', 'CHAT_PROJECT_MISMATCH')
        const provider = await resolvedProviderStore.requireRunnableModel(chat.providerId ?? 'local-qwen')
        if (provider.id !== 'local-qwen' && submission.attachmentIds.length > 0) {
          throw invalidRequest('A rota DeepSeek deste corte aceita somente texto. Use Qwen local para foto, áudio ou vídeo.', 'PROVIDER_MEDIA_UNSUPPORTED')
        }
        const title = chat.title === 'Nova conversa' ? submission.task.split(/\r?\n/u)[0].slice(0, 88) : chat.title
        await cockpitStore.updateChat(chat.id, {
          title,
          projectId: project.id,
          projectPath: project.path,
          lastTask: submission.task,
          preview: submission.task.split(/\r?\n/u)[0].slice(0, 140),
          status: 'queued',
        })
        await cockpitStore.appendChatMessage(chat.id, { role: 'user', text: submission.task })
        const selectedWorkspace = project.isDefault ? resolvedWorkspace : project.path
        const job = await taskRunner.start({ ...submission, workspace: selectedWorkspace, chatId: chat.id, projectId: project.id, providerId: provider.id })
        await cockpitStore.updateChat(chat.id, { jobId: job.id, status: job.status, updatedAt: Date.now() })
        cachedSnapshot = undefined
        cachedAt = 0
        sendJson(response, 202, { job: redactSensitive(job) })
      }
      catch (error) {
        const status = error?.code === 'TASK_ACTIVE' ? 409
          : error?.code === 'BODY_TOO_LARGE' ? 413
          : error?.code === 'ATTACHMENT_NOT_FOUND' || error?.code === 'CHAT_NOT_FOUND' || error?.code === 'PROJECT_NOT_FOUND' ? 404
            : error?.code === 'CHAT_PROJECT_MISMATCH' ? 409
              : error?.code === 'WORKSPACE_OUTSIDE_BOUNDARY' ? 422
              : 400
        sendJson(response, status, { error: error?.code ?? 'invalid_task', message: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    if (request.method !== 'GET') {
      sendJson(response, 405, { error: 'method_not_allowed' })
      return
    }
    if (url.pathname === '/api/snapshot') {
      try {
        sendJson(response, 200, await getSnapshot())
      }
      catch (error) {
        sendJson(response, 500, { error: error instanceof Error ? error.message : String(error) })
      }
      return
    }
    if (url.pathname === '/api/health') {
      sendJson(response, 200, {
        ok: true,
        now: Date.now(),
        taskSubmission: true,
        mediaUploads: true,
        acceptedMedia: ['image', 'audio', 'video'],
      })
      return
    }
    if (url.pathname === '/events') {
      securityHeaders(response, 'text/event-stream; charset=utf-8')
      response.setHeader('Connection', 'keep-alive')
      response.flushHeaders()
      let closed = false
      let working = false
      const push = async () => {
        if (closed || working) return
        working = true
        try {
          const snapshot = await getSnapshot()
          response.write(`event: snapshot\ndata: ${JSON.stringify(snapshot)}\n\n`)
        }
        catch (error) {
          response.write(`event: monitor-error\ndata: ${JSON.stringify({ message: error instanceof Error ? error.message : String(error) })}\n\n`)
        }
        finally {
          working = false
        }
      }
      void push()
      const interval = setInterval(() => void push(), Math.max(250, refreshMs))
      request.on('close', () => {
        closed = true
        clearInterval(interval)
      })
      return
    }

    const path = safeStaticPath(staticRoot, url.pathname)
    if (path === undefined || !(await pathExists(path))) {
      sendJson(response, 404, { error: 'not_found' })
      return
    }
    const contentType = STATIC_CONTENT_TYPES[extname(path).toLowerCase()] ?? 'application/octet-stream'
    securityHeaders(response, contentType)
    response.statusCode = 200
    createReadStream(path).pipe(response)
  })
}

function parseCli(argv) {
  const values = { port: DEFAULT_PORT, host: '127.0.0.1', root: resolve(import.meta.dirname, '..') }
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--port') values.port = Number(argv[++index])
    else if (argument === '--host') values.host = argv[++index]
    else if (argument === '--root') values.root = resolve(argv[++index])
    else if (argument === '--workspace') values.workspace = resolve(argv[++index])
    else throw new Error(`argumento desconhecido: ${argument}`)
  }
  if (values.host !== '127.0.0.1') throw new Error('o monitor aceita somente --host 127.0.0.1')
  if (!Number.isInteger(values.port) || values.port < 0 || values.port > 65535) throw new Error('porta invalida')
  values.workspace ??= resolve(values.root, '..')
  return values
}

async function main() {
  const options = parseCli(process.argv.slice(2))
  const server = createMonitorServer({ projectRoot: options.root, workspaceRoot: options.workspace })
  await new Promise((resolveListen, reject) => {
    server.once('error', reject)
    server.listen(options.port, options.host, resolveListen)
  })
  const address = server.address()
  if (address === null || typeof address === 'string') throw new Error('endereco do monitor indisponivel')
  console.log(`PEMARA_MONITOR_URL=http://127.0.0.1:${String(address.port)}`)
  const shutdown = () => server.close(() => process.exit(0))
  process.once('SIGINT', shutdown)
  process.once('SIGTERM', shutdown)
}

const invokedPath = process.argv[1] === undefined ? undefined : pathToFileURL(resolve(process.argv[1])).href
if (invokedPath === import.meta.url) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.stack : String(error))
    process.exitCode = 1
  })
}
