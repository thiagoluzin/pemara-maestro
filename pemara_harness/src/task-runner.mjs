import { spawn } from 'node:child_process'
import { closeSync, constants as fsConstants, createReadStream, openSync } from 'node:fs'
import { copyFile, mkdir, open, readFile, rename, rm, stat, writeFile } from 'node:fs/promises'
import { basename, extname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { createHash, randomUUID } from 'node:crypto'
import { pathToFileURL } from 'node:url'

const MAX_TASK_CHARS = 16_000
const MAX_LOG_BYTES = 48 * 1024
export const MAX_ATTACHMENTS = 8
export const MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024 * 1024
export const MAX_ATTACHMENT_TOTAL_BYTES = 4 * 1024 * 1024 * 1024
const ACTIVE_STATUSES = new Set(['queued', 'running'])
const STALE_QUEUED_MS = 45_000
const STALE_HEARTBEAT_MS = 15_000
const ATTACHMENT_ID = /^att-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u
const PROVIDER_ID = /^(?:local-qwen|deepseek-api)$/u
const MEDIA_EXTENSIONS = Object.freeze({
  image: new Set(['.avif', '.bmp', '.gif', '.heic', '.heif', '.jpeg', '.jpg', '.png', '.tif', '.tiff', '.webp']),
  audio: new Set(['.aac', '.aiff', '.alac', '.flac', '.m4a', '.mp3', '.oga', '.ogg', '.opus', '.wav', '.webm', '.wma']),
  video: new Set(['.avi', '.m2ts', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.mts', '.ogv', '.ts', '.webm', '.wmv']),
})

function taskError(message, code = 'INVALID_TASK') {
  const error = new Error(message)
  error.code = code
  return error
}

export function normalizeTaskSubmission(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw taskError('A tarefa deve ser um objeto JSON.')
  }
  const keys = Object.keys(value)
  if (!keys.includes('task') || keys.some(key => !['task', 'attachmentIds'].includes(key))) {
    throw taskError('Os únicos campos permitidos são task e attachmentIds.')
  }
  if (typeof value.task !== 'string') throw taskError('O texto da tarefa é obrigatório.')
  if (value.task.includes('\u0000')) throw taskError('A tarefa contém caractere inválido.')
  const attachmentIds = value.attachmentIds === undefined ? [] : value.attachmentIds
  if (!Array.isArray(attachmentIds)
    || attachmentIds.some(id => typeof id !== 'string' || !ATTACHMENT_ID.test(id))) {
    throw taskError('A lista de anexos contém um identificador inválido.', 'INVALID_ATTACHMENT')
  }
  if (attachmentIds.length > MAX_ATTACHMENTS) {
    throw taskError(`Uma tarefa aceita no máximo ${MAX_ATTACHMENTS} anexos.`, 'TOO_MANY_ATTACHMENTS')
  }
  if (new Set(attachmentIds).size !== attachmentIds.length) {
    throw taskError('A lista de anexos contém identificador duplicado.', 'DUPLICATE_ATTACHMENT')
  }
  let task = value.task.trim()
  if (task.length < 3 && attachmentIds.length === 0) {
    throw taskError('Descreva a tarefa com pelo menos 3 caracteres.')
  }
  if (task.length < 3) task = 'Analise os anexos enviados e responda com base neles.'
  if (task.length > MAX_TASK_CHARS) throw taskError('A tarefa deve ter no máximo 16.000 caracteres.')
  return { task, attachmentIds: [...attachmentIds] }
}

function normalizedFilename(value) {
  if (typeof value !== 'string' || value.includes('\u0000')) {
    throw taskError('Nome de anexo inválido.', 'INVALID_ATTACHMENT')
  }
  const leaf = basename(value.replaceAll('\\', '/')).normalize('NFC').trim()
  if (leaf === '' || leaf === '.' || leaf === '..') return 'anexo'
  return leaf.slice(0, 180)
}

function mediaKind(filename, mediaType) {
  const declared = typeof mediaType === 'string' ? mediaType.split(';', 1)[0].trim().toLowerCase() : ''
  const declaredKind = ['image', 'audio', 'video'].find(kind => declared.startsWith(`${kind}/`))
  const extension = extname(filename).toLowerCase()
  const extensionKind = Object.entries(MEDIA_EXTENSIONS).find(([, extensions]) => extensions.has(extension))?.[0]
  if (declaredKind !== undefined && extensionKind !== undefined && declaredKind !== extensionKind) {
    throw taskError('Tipo e extensão do anexo não correspondem.', 'UNSUPPORTED_MEDIA')
  }
  const kind = declaredKind ?? extensionKind
  if (kind === undefined) {
    throw taskError('Somente imagem, áudio e vídeo são aceitos.', 'UNSUPPORTED_MEDIA')
  }
  return {
    kind,
    mediaType: declaredKind === undefined ? `${kind}/unknown` : declared,
  }
}

function publicAttachment(metadata) {
  return {
    id: metadata.id,
    name: metadata.name,
    kind: metadata.kind,
    mediaType: metadata.mediaType,
    bytes: metadata.bytes,
    sha256: metadata.sha256,
  }
}

async function sha256File(path) {
  const hash = createHash('sha256')
  for await (const chunk of createReadStream(path)) hash.update(chunk)
  return hash.digest('hex')
}

function isWithin(root, candidate) {
  const rel = relative(resolve(root), resolve(candidate))
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

async function writeJsonAtomic(path, value) {
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  await rename(temporary, path)
}

async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, 'utf8'))
  }
  catch (error) {
    if (error?.code === 'ENOENT') return undefined
    throw error
  }
}

async function readTail(path, maxBytes = MAX_LOG_BYTES) {
  let handle
  try {
    handle = await open(path, 'r')
    const { size } = await handle.stat()
    const length = Math.min(size, maxBytes)
    const buffer = Buffer.alloc(length)
    await handle.read(buffer, 0, length, Math.max(0, size - length))
    const text = buffer.toString('utf8').replaceAll('\u0000', '').trim()
    return size > length ? `… [início omitido]\n${text}` : text
  }
  catch (error) {
    if (error?.code === 'ENOENT') return ''
    throw error
  }
  finally {
    await handle?.close()
  }
}

function publicState(state, now) {
  if (state === undefined) return { status: 'idle' }
  const heartbeatAt = Number(state.heartbeatAt ?? state.createdAt)
  const stale = state.status === 'queued'
    ? now - heartbeatAt > STALE_QUEUED_MS
    : state.status === 'running' && now - heartbeatAt > STALE_HEARTBEAT_MS
  if (!stale) return state
  return {
    ...state,
    status: 'interrupted',
    phase: 'stopped',
    detail: 'O executor deixou de atualizar o trabalho. O histórico foi preservado e uma nova tarefa pode ser iniciada.',
  }
}

function defaultLaunchDetached(entry, args, options) {
  return spawn(entry, args, options)
}

export function createTaskRunner({
  projectRoot,
  workspaceRoot,
  now = Date.now,
  launchDetached = defaultLaunchDetached,
} = {}) {
  if (typeof projectRoot !== 'string' || projectRoot.trim() === '') throw new TypeError('projectRoot is required')
  if (typeof workspaceRoot !== 'string' || workspaceRoot.trim() === '') throw new TypeError('workspaceRoot is required')
  const project = resolve(projectRoot)
  const workspaceBoundary = resolve(workspaceRoot)
  const runtimeRoot = join(project, '.runtime', 'monitor', 'task-runner')
  const jobsRoot = join(runtimeRoot, 'jobs')
  const stagingRoot = join(runtimeRoot, 'staging')
  const statePath = join(runtimeRoot, 'current.json')
  const workerEntry = resolve(import.meta.filename)
  let starting = false

  async function snapshot() {
    const state = publicState(await readJson(statePath), now())
    if (state.status === 'idle') return state
    const [stdout, stderr] = await Promise.all([
      state.stdoutPath ? readTail(state.stdoutPath) : '',
      state.stderrPath ? readTail(state.stderrPath) : '',
    ])
    return { ...state, stdout, stderr }
  }

  async function stageAttachment({ stream, filename, mediaType, contentLength } = {}) {
    if (stream === null || typeof stream?.[Symbol.asyncIterator] !== 'function') {
      throw taskError('O corpo do anexo é obrigatório.', 'INVALID_ATTACHMENT')
    }
    const name = normalizedFilename(filename)
    const classified = mediaKind(name, mediaType)
    if (contentLength !== undefined
      && (!Number.isSafeInteger(contentLength) || contentLength < 0 || contentLength > MAX_ATTACHMENT_BYTES)) {
      throw taskError('O anexo excede o limite de 2 GiB.', 'ATTACHMENT_TOO_LARGE')
    }
    const id = `att-${randomUUID()}`
    const storageName = `${id}.media`
    const dataPath = join(stagingRoot, storageName)
    const metadataPath = join(stagingRoot, `${id}.json`)
    const temporary = `${dataPath}.${process.pid}.${randomUUID()}.tmp`
    await mkdir(stagingRoot, { recursive: true })
    let handle
    let bytes = 0
    const hash = createHash('sha256')
    try {
      handle = await open(temporary, 'wx')
      for await (const raw of stream) {
        const chunk = Buffer.isBuffer(raw) ? raw : Buffer.from(raw)
        bytes += chunk.length
        if (bytes > MAX_ATTACHMENT_BYTES) {
          throw taskError('O anexo excede o limite de 2 GiB.', 'ATTACHMENT_TOO_LARGE')
        }
        hash.update(chunk)
        await handle.write(chunk)
      }
      if (bytes === 0) throw taskError('O anexo está vazio.', 'INVALID_ATTACHMENT')
      await handle.sync()
      await handle.close()
      handle = undefined
      await rename(temporary, dataPath)
      const metadata = {
        version: 1,
        id,
        name,
        ...classified,
        bytes,
        sha256: hash.digest('hex'),
        storageName,
        createdAt: now(),
      }
      await writeJsonAtomic(metadataPath, metadata)
      return publicAttachment(metadata)
    }
    catch (error) {
      await handle?.close().catch(() => {})
      await Promise.all([
        rm(temporary, { force: true }).catch(() => {}),
        rm(dataPath, { force: true }).catch(() => {}),
        rm(metadataPath, { force: true }).catch(() => {}),
      ])
      throw error
    }
  }

  async function stagedAttachment(id) {
    if (typeof id !== 'string' || !ATTACHMENT_ID.test(id)) {
      throw taskError('Identificador de anexo inválido.', 'INVALID_ATTACHMENT')
    }
    const metadataPath = join(stagingRoot, `${id}.json`)
    const metadata = await readJson(metadataPath)
    if (metadata === undefined
      || metadata.version !== 1
      || metadata.id !== id
      || metadata.storageName !== `${id}.media`) {
      throw taskError(`Anexo não encontrado ou inválido: ${id}`, 'ATTACHMENT_NOT_FOUND')
    }
    const dataPath = join(stagingRoot, metadata.storageName)
    const details = await stat(dataPath).catch(() => undefined)
    if (details === undefined || !details.isFile() || details.size !== metadata.bytes) {
      throw taskError(`Anexo incompleto ou ausente: ${id}`, 'ATTACHMENT_NOT_FOUND')
    }
    if (await sha256File(dataPath) !== metadata.sha256) {
      throw taskError(`Integridade do anexo não confere: ${id}`, 'ATTACHMENT_CORRUPT')
    }
    return { metadata, metadataPath, dataPath }
  }

  async function discardAttachment(id) {
    if (typeof id !== 'string' || !ATTACHMENT_ID.test(id)) {
      throw taskError('Identificador de anexo inválido.', 'INVALID_ATTACHMENT')
    }
    await Promise.all([
      rm(join(stagingRoot, `${id}.media`), { force: true }),
      rm(join(stagingRoot, `${id}.json`), { force: true }),
    ])
  }

  async function start({ task, attachmentIds = [], workspace: requestedWorkspace = workspaceBoundary, chatId = null, projectId = null, providerId = 'local-qwen' } = {}) {
    if (starting) throw taskError('Uma tarefa já está sendo preparada.', 'TASK_ACTIVE')
    const selectedWorkspace = resolve(requestedWorkspace)
    if (!isWithin(workspaceBoundary, selectedWorkspace)) throw taskError('O workspace da interface precisa ficar dentro do workspace Pemara.', 'WORKSPACE_OUTSIDE_BOUNDARY')
    if (typeof providerId !== 'string' || !PROVIDER_ID.test(providerId)) throw taskError('O provedor selecionado não é permitido.', 'INVALID_PROVIDER')
    const submission = normalizeTaskSubmission({ task, attachmentIds })
    starting = true
    try {
      const current = await snapshot()
      if (ACTIVE_STATUSES.has(current.status)) {
        throw taskError('Uma tarefa já está em execução. Aguarde ela terminar.', 'TASK_ACTIVE')
      }

      const id = `job-${new Date(now()).toISOString().replaceAll(/[:.]/gu, '-')}-${randomUUID().slice(0, 8)}`
      const jobRoot = join(jobsRoot, id)
      const taskPath = join(jobRoot, 'task.txt')
      const attachmentsRoot = join(jobRoot, 'attachments')
      const attachmentsManifestPath = join(jobRoot, 'attachments.json')
      const stdoutPath = join(jobRoot, 'stdout.log')
      const stderrPath = join(jobRoot, 'stderr.log')
      const staged = []
      let totalBytes = 0
      for (const attachmentId of submission.attachmentIds) {
        const item = await stagedAttachment(attachmentId)
        totalBytes += item.metadata.bytes
        if (totalBytes > MAX_ATTACHMENT_TOTAL_BYTES) {
          throw taskError('Os anexos excedem o limite total de 4 GiB.', 'ATTACHMENTS_TOO_LARGE')
        }
        staged.push(item)
      }
      await mkdir(jobRoot, { recursive: true })
      try {
        await writeFile(taskPath, submission.task, { encoding: 'utf8', flag: 'wx' })
        const manifestAttachments = []
        if (staged.length > 0) {
          await mkdir(attachmentsRoot, { recursive: true })
          for (const item of staged) {
            const target = join(attachmentsRoot, item.metadata.storageName)
            await copyFile(item.dataPath, target, fsConstants.COPYFILE_EXCL)
            if (await sha256File(target) !== item.metadata.sha256) {
              throw taskError(`Cópia do anexo falhou na verificação: ${item.metadata.id}`, 'ATTACHMENT_CORRUPT')
            }
            manifestAttachments.push({
              ...publicAttachment(item.metadata),
              relativePath: `attachments/${item.metadata.storageName}`,
            })
          }
          await writeJsonAtomic(attachmentsManifestPath, {
            version: 1,
            jobId: id,
            attachments: manifestAttachments,
          })
        }
      }
      catch (error) {
        await rm(jobRoot, { recursive: true, force: true })
        throw error
      }
      const publicAttachments = staged.map(item => publicAttachment(item.metadata))
      const initial = {
        version: 2,
        id,
        task: submission.task,
        attachments: publicAttachments,
        status: 'queued',
        phase: 'preparing',
        createdAt: now(),
        heartbeatAt: now(),
        workspace: selectedWorkspace,
        chatId,
        projectId,
        providerId,
        stdoutPath,
        stderrPath,
      }
      await mkdir(runtimeRoot, { recursive: true })
      await writeJsonAtomic(statePath, initial)
      await Promise.all(staged.flatMap(item => [
        rm(item.dataPath, { force: true }).catch(() => {}),
        rm(item.metadataPath, { force: true }).catch(() => {}),
      ]))

      const args = [
        workerEntry,
        '--worker',
        '--project-root', project,
        '--workspace', selectedWorkspace,
        '--state-file', statePath,
        '--task-file', taskPath,
        '--provider-id', providerId,
        ...(staged.length === 0 ? [] : ['--attachments-manifest', attachmentsManifestPath]),
        '--stdout-file', stdoutPath,
        '--stderr-file', stderrPath,
      ]
      let child
      try {
        child = launchDetached(process.execPath, args, {
          cwd: project,
          detached: true,
          windowsHide: true,
          stdio: 'ignore',
        })
        child.unref?.()
      }
      catch (error) {
        const failed = {
          ...initial,
          status: 'failed',
          phase: 'stopped',
          finishedAt: now(),
          heartbeatAt: now(),
          detail: `Não foi possível iniciar o executor: ${error instanceof Error ? error.message : String(error)}`,
        }
        await writeJsonAtomic(statePath, failed)
        throw error
      }
      return { ...initial, runnerPid: child.pid }
    }
    finally {
      starting = false
    }
  }

  return Object.freeze({
    snapshot,
    stageAttachment,
    discardAttachment,
    start,
    statePath,
    workspaceRoot: workspaceBoundary,
  })
}

function parseWorkerArguments(argv) {
  const values = {}
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--worker') values.worker = true
    else if (argument === '--project-root') values.projectRoot = argv[++index]
    else if (argument === '--workspace') values.workspace = argv[++index]
    else if (argument === '--state-file') values.stateFile = argv[++index]
    else if (argument === '--task-file') values.taskFile = argv[++index]
    else if (argument === '--provider-id') values.providerId = argv[++index]
    else if (argument === '--attachments-manifest') values.attachmentsManifest = argv[++index]
    else if (argument === '--stdout-file') values.stdoutFile = argv[++index]
    else if (argument === '--stderr-file') values.stderrFile = argv[++index]
    else throw new Error(`argumento desconhecido do executor: ${argument}`)
  }
  for (const key of ['projectRoot', 'workspace', 'stateFile', 'taskFile', 'stdoutFile', 'stderrFile']) {
    if (typeof values[key] !== 'string' || values[key].trim() === '') throw new Error(`argumento obrigatório ausente: ${key}`)
  }
  if (typeof values.providerId !== 'string' || !PROVIDER_ID.test(values.providerId)) throw new Error('provedor inválido do executor')
  values.projectRoot = resolve(values.projectRoot)
  values.workspace = resolve(values.workspace)
  for (const key of ['stateFile', 'taskFile', 'stdoutFile', 'stderrFile', 'attachmentsManifest']) {
    if (values[key] === undefined) continue
    values[key] = resolve(values[key])
    if (!isWithin(join(values.projectRoot, '.runtime', 'monitor'), values[key])) {
      throw new Error(`${key} precisa ficar no runtime isolado do monitor`)
    }
  }
  return values
}

function powerShellExecutable(env = process.env) {
  const windowsRoot = env.SystemRoot || 'C:\\Windows'
  return join(windowsRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
}

export async function runTaskWorker(options, { launch = spawn, now = Date.now } = {}) {
  const launcher = join(options.projectRoot, 'bin', 'Open-PemaraHarness.ps1')
  if (!isWithin(options.projectRoot, launcher)) throw new Error('launcher fora do projeto')
  let state = await readJson(options.stateFile)
  if (state?.id === undefined) throw new Error('estado da tarefa ausente')
  const providerId = options.providerId ?? state.providerId ?? 'local-qwen'
  if (!PROVIDER_ID.test(providerId)) throw new Error('provedor inválido do executor')
  normalizeTaskSubmission({
    task: await readFile(options.taskFile, 'utf8'),
    attachmentIds: Array.isArray(state.attachments) ? state.attachments.map(item => item.id) : [],
  })
  let writes = Promise.resolve()
  const persist = patch => {
    state = { ...state, ...patch }
    writes = writes.then(() => writeJsonAtomic(options.stateFile, state))
    return writes
  }

  await persist({
    status: 'running',
    phase: 'preparing',
    runnerPid: process.pid,
    startedAt: now(),
    heartbeatAt: now(),
  })

  const stdoutFd = openSync(options.stdoutFile, 'a')
  const stderrFd = openSync(options.stderrFile, 'a')
  let child
  let heartbeat
  try {
    child = launch(powerShellExecutable(), [
      '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
      '-File', launcher,
      '-Workspace', options.workspace,
      '-TaskFile', options.taskFile,
      '-ProviderId', providerId,
      ...(options.attachmentsManifest === undefined ? [] : ['-AttachmentsManifest', options.attachmentsManifest]),
      '-Once',
    ], {
      cwd: options.workspace,
      windowsHide: true,
      stdio: ['ignore', stdoutFd, stderrFd],
    })
    const completion = new Promise((resolveResult, reject) => {
      child.once('error', reject)
      child.once('close', (code, signal) => resolveResult({ code, signal }))
    })
    await persist({ childPid: child.pid, phase: 'running', heartbeatAt: now() })
    heartbeat = setInterval(() => { void persist({ heartbeatAt: now() }) }, 2500)
    const result = await completion
    await persist({
      status: result.code === 0 ? 'completed' : 'failed',
      phase: 'stopped',
      exitCode: result.code,
      signal: result.signal,
      finishedAt: now(),
      heartbeatAt: now(),
      detail: result.code === 0 ? 'Tarefa encerrada pelo runtime.' : `Runtime encerrado com código ${String(result.code)}.`,
    })
    return result.code ?? 1
  }
  catch (error) {
    await persist({
      status: 'failed',
      phase: 'stopped',
      finishedAt: now(),
      heartbeatAt: now(),
      detail: error instanceof Error ? error.message : String(error),
    })
    return 1
  }
  finally {
    if (heartbeat !== undefined) clearInterval(heartbeat)
    await writes.catch(() => {})
    closeSync(stdoutFd)
    closeSync(stderrFd)
  }
}

async function main() {
  const options = parseWorkerArguments(process.argv.slice(2))
  if (!options.worker) throw new Error('use --worker')
  process.exitCode = await runTaskWorker(options)
}

const invokedPath = process.argv[1] === undefined ? undefined : pathToFileURL(resolve(process.argv[1])).href
if (invokedPath === import.meta.url) {
  main().catch(error => {
    console.error(error instanceof Error ? error.stack : String(error))
    process.exitCode = 1
  })
}
