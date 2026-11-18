import { createHash, randomUUID } from 'node:crypto'
import { mkdir, readFile, readdir, realpath, rename, stat, writeFile } from 'node:fs/promises'
import { basename, join, relative, resolve, sep } from 'node:path'

const REGISTRY_VERSION = 1
const CHAT_ID = /^chat-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u
const PROJECT_ID = /^project-[0-9a-f]{12}$/u
const CHAT_MESSAGE_ROLES = new Set(['user', 'assistant', 'system'])
const MAX_CHAT_MESSAGES = 160
const MAX_CHAT_MESSAGE_CHARS = 24_000
const HIDDEN_PROJECT_DIRS = new Set([
  '.git', '.runtime', 'node_modules', '__pycache__', '.pnpm-store', '.pytest_cache', '.trash',
  '_downloads', '_Quarentena_Agentes_20260816', '_take2_work', '_video_work', 'backups',
  'cache', 'deliveries', 'logs', 'model_downloads', 'scratch', 'third_party', 'worktrees',
])
const PROJECT_MARKERS = new Set([
  '.git', 'AGENTS.md', 'README.md', 'package.json', 'pyproject.toml', 'pubspec.yaml',
  'Cargo.toml', 'docker-compose.yml', 'index.html', 'app.py', 'src', 'android',
])

function storeError(message, code = 'INVALID_COCKPIT_RESOURCE') {
  const error = new Error(message)
  error.code = code
  return error
}

function isWithin(root, candidate) {
  const rel = relative(resolve(root), resolve(candidate))
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !rel.startsWith('..\/') && !rel.startsWith('../'))
}

function projectIdForPath(path) {
  return `project-${createHash('sha256').update(path.toLowerCase()).digest('hex').slice(0, 12)}`
}

function cleanName(value, fallback) {
  const name = String(value ?? '').replaceAll(/\s+/gu, ' ').trim()
  if (name.length === 0) return fallback
  return name.slice(0, 100)
}

function cleanMessageText(value) {
  if (typeof value !== 'string') throw storeError('O texto da mensagem é obrigatório.', 'INVALID_CHAT_MESSAGE')
  const text = value.replaceAll('\u0000', '').trim()
  if (text.length === 0) throw storeError('A mensagem não pode ficar vazia.', 'INVALID_CHAT_MESSAGE')
  return text.slice(0, MAX_CHAT_MESSAGE_CHARS)
}

async function readRegistry(path, fallback) {
  try {
    const parsed = JSON.parse(await readFile(path, 'utf8'))
    if (parsed?.version !== REGISTRY_VERSION || !Array.isArray(parsed.items)) return fallback
    return parsed.items
  }
  catch (error) {
    if (error?.code === 'ENOENT') return fallback
    throw error
  }
}

async function writeJsonAtomic(path, value) {
  await mkdir(resolve(path, '..'), { recursive: true })
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  await writeFile(temporary, `${JSON.stringify({ version: REGISTRY_VERSION, items: value }, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  await rename(temporary, path)
}

export function createCockpitStore({ projectRoot, workspaceRoot, now = Date.now } = {}) {
  if (typeof projectRoot !== 'string' || projectRoot.trim() === '') throw new TypeError('projectRoot is required')
  if (typeof workspaceRoot !== 'string' || workspaceRoot.trim() === '') throw new TypeError('workspaceRoot is required')
  const project = resolve(projectRoot)
  const workspace = resolve(workspaceRoot)
  const runtimeRoot = join(project, '.runtime', 'monitor')
  const projectsPath = join(runtimeRoot, 'projects.json')
  const chatsPath = join(runtimeRoot, 'chats.json')
  let writeChain = Promise.resolve()
  let canonicalWorkspacePromise

  function canonicalWorkspace() {
    canonicalWorkspacePromise ??= realpath(workspace).catch(() => workspace)
    return canonicalWorkspacePromise
  }

  async function validProjectPath(value) {
    if (typeof value !== 'string' || value.trim() === '') throw storeError('O caminho do projeto é obrigatório.', 'INVALID_PROJECT_PATH')
    const candidate = resolve(value.trim())
    const requestedRelative = relative(workspace, candidate)
    if (requestedRelative === '.runtime' || requestedRelative.startsWith(`.runtime${sep}`)
      || requestedRelative === '.git' || requestedRelative.startsWith(`.git${sep}`)) {
      throw storeError('A pasta interna do runtime do Harness não pode ser vinculada como projeto.', 'PROJECT_RUNTIME_FORBIDDEN')
    }
    let canonical
    try {
      canonical = await realpath(candidate)
    }
    catch {
      throw storeError('A pasta do projeto não existe.', 'PROJECT_NOT_FOUND')
    }
    const details = await stat(canonical).catch(() => undefined)
    if (details === undefined || !details.isDirectory()) throw storeError('O projeto precisa ser uma pasta.', 'INVALID_PROJECT_PATH')
    const boundary = await canonicalWorkspace()
    if (!isWithin(boundary, canonical)) throw storeError('O projeto precisa ficar dentro do workspace Pemara.', 'PROJECT_OUTSIDE_WORKSPACE')
    const rel = relative(boundary, canonical)
    const first = rel.split(/[\\/]/u)[0]
    if (first === '.runtime' || first === '.git' || rel === '.runtime') {
      throw storeError('A pasta interna do runtime do Harness não pode ser vinculada como projeto.', 'PROJECT_RUNTIME_FORBIDDEN')
    }
    return canonical
  }

  async function readProjects() {
    return readRegistry(projectsPath, [])
  }

  async function readChats() {
    return readRegistry(chatsPath, [])
  }

  function mutate(path, operation) {
    const next = writeChain.then(async () => {
      const items = await readRegistry(path, [])
      const result = await operation(items)
      await writeJsonAtomic(path, result.items)
      return result.value
    })
    writeChain = next.catch(() => {})
    return next
  }

  async function listProjects() {
    const registered = await readProjects()
    const discovered = []
    const boundary = await canonicalWorkspace()
    const defaultProject = {
      id: projectIdForPath(boundary),
      name: basename(boundary) || 'Pemara',
      path: boundary,
      isDefault: true,
      isRegistered: true,
      createdAt: 0,
      updatedAt: 0,
    }
    const entries = await readdir(boundary, { withFileTypes: true }).catch(() => [])
    for (const entry of entries) {
      if (!entry.isDirectory() || HIDDEN_PROJECT_DIRS.has(entry.name)) continue
      const path = join(boundary, entry.name)
      const markerEntries = await readdir(path, { withFileTypes: true }).catch(() => [])
      if (!markerEntries.some(marker => PROJECT_MARKERS.has(marker.name))) continue
      discovered.push({
        id: projectIdForPath(path),
        name: entry.name,
        path,
        isDefault: false,
        isRegistered: false,
        createdAt: 0,
        updatedAt: 0,
      })
    }
    const all = [defaultProject, ...discovered, ...registered]
    const unique = new Map()
    for (const item of all) {
      const key = String(item.path).toLowerCase()
      unique.set(key, { ...item, name: cleanName(item.name, basename(item.path) || 'Projeto') })
    }
    return [...unique.values()].sort((left, right) => {
      if (left.isDefault) return -1
      if (right.isDefault) return 1
      return left.name.localeCompare(right.name, 'pt-BR')
    })
  }

  async function getProject(id) {
    if (typeof id !== 'string' || !PROJECT_ID.test(id)) throw storeError('Identificador de projeto inválido.', 'INVALID_PROJECT_ID')
    return (await listProjects()).find(item => item.id === id)
  }

  async function registerProject({ path, name } = {}) {
    const canonical = await validProjectPath(path)
    const id = projectIdForPath(canonical)
    const boundary = await canonicalWorkspace()
    return mutate(projectsPath, items => {
      const timestamp = now()
      const existing = items.find(item => item.id === id)
      const value = {
        id,
        name: cleanName(name, basename(canonical) || 'Projeto'),
        path: canonical,
        isDefault: canonical.toLowerCase() === boundary.toLowerCase(),
        isRegistered: true,
        createdAt: existing?.createdAt ?? timestamp,
        updatedAt: timestamp,
      }
      const next = existing ? items.map(item => item.id === id ? value : item) : [...items, value]
      return { items: next, value }
    })
  }

  async function createChat({ projectId, providerId = 'local-qwen' } = {}) {
    const projectRecord = projectId === undefined ? (await listProjects())[0] : await getProject(projectId)
    if (projectRecord === undefined) throw storeError('Projeto não encontrado.', 'PROJECT_NOT_FOUND')
    const timestamp = now()
    const value = {
      id: `chat-${randomUUID()}`,
      title: 'Nova conversa',
      projectId: projectRecord.id,
      projectPath: projectRecord.path,
      createdAt: timestamp,
      updatedAt: timestamp,
      status: 'idle',
      sessionId: null,
      jobId: null,
      lastTask: null,
      preview: null,
      providerId,
      messages: [],
    }
    return mutate(chatsPath, items => ({ items: [...items, value], value }))
  }

  async function getChat(id) {
    if (typeof id !== 'string' || !CHAT_ID.test(id)) throw storeError('Identificador de chat inválido.', 'INVALID_CHAT_ID')
    return (await readChats()).find(item => item.id === id)
  }

  async function updateChat(id, patch = {}) {
    if (typeof id !== 'string' || !CHAT_ID.test(id)) throw storeError('Identificador de chat inválido.', 'INVALID_CHAT_ID')
    if (patch.projectId !== undefined) {
      const projectRecord = await getProject(patch.projectId)
      if (projectRecord === undefined) throw storeError('Projeto não encontrado.', 'PROJECT_NOT_FOUND')
    }
    return mutate(chatsPath, items => {
      const current = items.find(item => item.id === id)
      if (current === undefined) throw storeError('Chat não encontrado.', 'CHAT_NOT_FOUND')
      const allowed = ['title', 'projectId', 'projectPath', 'status', 'sessionId', 'jobId', 'lastTask', 'preview', 'providerId', 'messages', 'updatedAt']
      const safePatch = Object.fromEntries(Object.entries(patch).filter(([key]) => allowed.includes(key)))
      const value = {
        ...current,
        ...safePatch,
        title: cleanName(safePatch.title ?? current.title, 'Nova conversa'),
        updatedAt: safePatch.updatedAt ?? now(),
      }
      return { items: items.map(item => item.id === id ? value : item), value }
    })
  }

  async function appendChatMessage(id, { role, text, jobId = null, createdAt = now() } = {}) {
    if (typeof id !== 'string' || !CHAT_ID.test(id)) throw storeError('Identificador de chat inválido.', 'INVALID_CHAT_ID')
    if (!CHAT_MESSAGE_ROLES.has(role)) throw storeError('O papel da mensagem é inválido.', 'INVALID_CHAT_MESSAGE')
    const safeText = cleanMessageText(text)
    const timestamp = Number.isFinite(createdAt) ? createdAt : now()
    return mutate(chatsPath, items => {
      const current = items.find(item => item.id === id)
      if (current === undefined) throw storeError('Chat não encontrado.', 'CHAT_NOT_FOUND')
      const messages = Array.isArray(current.messages) ? current.messages : []
      const value = {
        ...current,
        messages: [...messages, {
          id: `message-${randomUUID()}`,
          role,
          text: safeText,
          jobId: typeof jobId === 'string' ? jobId : null,
          createdAt: timestamp,
        }].slice(-MAX_CHAT_MESSAGES),
        updatedAt: timestamp,
      }
      return { items: items.map(item => item.id === id ? value : item), value }
    })
  }

  return Object.freeze({
    listProjects,
    getProject,
    registerProject,
    listChats: readChats,
    getChat,
    createChat,
    updateChat,
    appendChatMessage,
    workspaceRoot: workspace,
    projectRoot: project,
  })
}

export { CHAT_ID, PROJECT_ID, projectIdForPath }
