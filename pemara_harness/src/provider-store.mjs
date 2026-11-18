import { access, mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { constants as fsConstants } from 'node:fs'
import { randomUUID } from 'node:crypto'
import { join, resolve } from 'node:path'

const VERSION = 1
const PROVIDER_ID = /^[a-z0-9-]{3,64}$/u

const CATALOG = Object.freeze([
  Object.freeze({
    id: 'local-qwen',
    kind: 'model',
    displayName: 'Qwen local',
    model: 'qwen3.8-27b-uncensored-yarn-524k',
    description: 'Modelo privado no seu computador; aceita texto, foto, áudio e vídeo.',
    capabilities: ['text', 'image', 'audio', 'video'],
    egress: 'Nenhum dado sai do computador.',
    defaultEnabled: true,
  }),
  Object.freeze({
    id: 'deepseek-api',
    kind: 'model',
    displayName: 'DeepSeek API',
    model: 'deepseek-chat',
    description: 'Modelo remoto por API. Neste corte, recebe tarefas de texto.',
    capabilities: ['text'],
    egress: 'O texto da tarefa é enviado à API DeepSeek quando você selecioná-la.',
    credentialEnv: 'DEEPSEEK_API_KEY',
    defaultEnabled: false,
  }),
  Object.freeze({
    id: 'claude-code',
    kind: 'subagent',
    displayName: 'Claude Code',
    description: 'Subagente externo para delegar trechos de trabalho no mesmo projeto.',
    capabilities: ['code'],
    egress: 'O contexto delegado será enviado ao serviço Anthropic quando o subagente for ativado.',
    credentialEnv: 'ANTHROPIC_API_KEY',
    defaultEnabled: false,
  }),
])

function providerError(message, code = 'INVALID_PROVIDER') {
  const error = new Error(message)
  error.code = code
  return error
}

function configured(env, name) {
  return typeof name === 'string' && typeof env?.[name] === 'string' && env[name].trim() !== ''
}

async function readRegistry(path) {
  try {
    const parsed = JSON.parse(await readFile(path, 'utf8'))
    if (parsed?.version !== VERSION || !Array.isArray(parsed.items)) return []
    return parsed.items
  }
  catch (error) {
    if (error?.code === 'ENOENT') return []
    throw error
  }
}

async function writeRegistry(path, items) {
  await mkdir(resolve(path, '..'), { recursive: true })
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  await writeFile(temporary, `${JSON.stringify({ version: VERSION, items }, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  await rename(temporary, path)
}

function publicProvider(definition, item, { env, claudeBundleInstalled }) {
  const enabled = item?.enabled ?? definition.defaultEnabled
  const credentialConfigured = configured(env, definition.credentialEnv)
  let status = 'ready'
  let selectable = definition.kind === 'model'
  let detail = definition.description
  if (!enabled) {
    status = 'disabled'
    selectable = false
    detail = 'Desativado. Ative conscientemente antes de usar.'
  }
  else if (definition.kind === 'subagent' && !claudeBundleInstalled) {
    status = 'needs_install'
    selectable = false
    detail = 'Pronto para instalar: ainda falta adicionar o conector Claude Code ao perfil isolado.'
  }
  else if (definition.kind === 'subagent' && !credentialConfigured) {
    status = 'needs_authentication'
    selectable = false
    detail = 'Conector instalado; falta autenticar o Claude Code neste computador.'
  }
  else if (definition.credentialEnv !== undefined && !credentialConfigured) {
    status = 'needs_credential'
    selectable = false
    detail = `Falta a credencial local ${definition.credentialEnv}. Ela nunca é enviada pelo navegador.`
  }
  return {
    id: definition.id,
    kind: definition.kind,
    displayName: definition.displayName,
    model: definition.model,
    description: definition.description,
    capabilities: definition.capabilities,
    egress: definition.egress,
    enabled: Boolean(enabled),
    selectable,
    status,
    detail,
    credentialConfigured,
  }
}

export function createProviderStore({ projectRoot, env = process.env } = {}) {
  if (typeof projectRoot !== 'string' || projectRoot.trim() === '') throw new TypeError('projectRoot is required')
  const project = resolve(projectRoot)
  const registryPath = join(project, '.runtime', 'monitor', 'providers.json')
  const claudeBundlePath = join(project, '.runtime', 'dsh-home', 'profiles', 'pemara', 'node_modules', '@deepseek-ai', 'dsh-subagent-claude-code', 'package.json')
  let writes = Promise.resolve()

  async function listProviders() {
    const [items, claudeBundleInstalled] = await Promise.all([
      readRegistry(registryPath),
      access(claudeBundlePath, fsConstants.F_OK).then(() => true).catch(() => false),
    ])
    return CATALOG.map(definition => publicProvider(
      definition,
      items.find(item => item?.id === definition.id),
      { env, claudeBundleInstalled },
    ))
  }

  async function getProvider(id) {
    if (typeof id !== 'string' || !PROVIDER_ID.test(id)) throw providerError('Identificador de provedor inválido.', 'INVALID_PROVIDER_ID')
    const provider = (await listProviders()).find(item => item.id === id)
    if (provider === undefined) throw providerError('Provedor não encontrado.', 'PROVIDER_NOT_FOUND')
    return provider
  }

  async function setEnabled(id, enabled) {
    if (typeof enabled !== 'boolean') throw providerError('O estado do provedor precisa ser verdadeiro ou falso.', 'INVALID_PROVIDER_ENABLED')
    const definition = CATALOG.find(item => item.id === id)
    if (definition === undefined) throw providerError('Provedor não encontrado.', 'PROVIDER_NOT_FOUND')
    const next = writes.then(async () => {
      const existing = await readRegistry(registryPath)
      const items = CATALOG.map(item => {
        const current = existing.find(entry => entry?.id === item.id)
        return { id: item.id, enabled: item.id === id ? enabled : (current?.enabled ?? item.defaultEnabled) }
      })
      await writeRegistry(registryPath, items)
      return getProvider(id)
    })
    writes = next.catch(() => {})
    return next
  }

  async function requireRunnableModel(id) {
    const provider = await getProvider(id ?? 'local-qwen')
    if (provider.kind !== 'model') throw providerError('Este conector é um subagente, não um modelo principal.', 'PROVIDER_NOT_MODEL')
    if (!provider.selectable) throw providerError(provider.detail, provider.status === 'disabled' ? 'PROVIDER_DISABLED' : 'PROVIDER_NOT_READY')
    return provider
  }

  return Object.freeze({ listProviders, getProvider, setEnabled, requireRunnableModel, registryPath })
}

export { PROVIDER_ID }
