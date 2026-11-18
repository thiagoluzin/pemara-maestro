const dom = {
  sidebar: document.querySelector('#sidebar'),
  sidebarToggle: document.querySelector('#sidebar-toggle'),
  sidebarClose: document.querySelector('#sidebar-close'),
  sidebarBackdrop: document.querySelector('#sidebar-backdrop'),
  newChat: document.querySelector('#new-chat'),
  chatSearch: document.querySelector('#chat-search'),
  chatCount: document.querySelector('#chat-count'),
  chatList: document.querySelector('#chat-list'),
  projectList: document.querySelector('#project-list'),
  addProject: document.querySelector('#add-project'),
  conversationProject: document.querySelector('#conversation-project'),
  conversationProjectName: document.querySelector('#conversation-project-name'),
  composerProject: document.querySelector('#composer-project'),
  composerProjectName: document.querySelector('#composer-project-name'),
  conversationProvider: document.querySelector('#conversation-provider'),
  conversationProviderName: document.querySelector('#conversation-provider-name'),
  topbarProject: document.querySelector('#topbar-project'),
  sidebarFooterStatus: document.querySelector('#sidebar-footer-status'),
  projectDialog: document.querySelector('#project-dialog'),
  projectForm: document.querySelector('#project-form'),
  projectPath: document.querySelector('#project-path'),
  projectName: document.querySelector('#project-name'),
  projectSuggestions: document.querySelector('#project-suggestions'),
  projectFeedback: document.querySelector('#project-feedback'),
  closeProjectDialog: document.querySelector('#close-project-dialog'),
  cancelProject: document.querySelector('#cancel-project'),
  providerDialog: document.querySelector('#provider-dialog'),
  providerList: document.querySelector('#provider-list'),
  providerFeedback: document.querySelector('#provider-feedback'),
  closeProviderDialog: document.querySelector('#close-provider-dialog'),
  closeProvider: document.querySelector('#close-provider'),
  qwenHealth: document.querySelector('#qwen-health'),
  comfyHealth: document.querySelector('#comfy-health'),
  connectionHealth: document.querySelector('#connection-health'),
  connectionCopy: document.querySelector('#connection-copy'),
  lastUpdate: document.querySelector('#last-update'),
  taskForm: document.querySelector('#task-form'),
  taskInput: document.querySelector('#task-input'),
  runTask: document.querySelector('#run-task'),
  attachmentInput: document.querySelector('#attachment-input'),
  attachFiles: document.querySelector('#attach-files'),
  recordAudio: document.querySelector('#record-audio'),
  attachmentTray: document.querySelector('#attachment-tray'),
  composerWrap: document.querySelector('.composer-wrap'),
  taskHint: document.querySelector('#task-hint'),
  formFeedback: document.querySelector('#form-feedback'),
  runStatus: document.querySelector('#run-status'),
  runTitle: document.querySelector('#run-title'),
  runDetail: document.querySelector('#run-detail'),
  runBadge: document.querySelector('#run-badge'),
  activityTitle: document.querySelector('#activity-title'),
  activitySubtitle: document.querySelector('#activity-subtitle'),
  sessionState: document.querySelector('#session-state'),
  activityFeed: document.querySelector('#activity-feed'),
  progressValue: document.querySelector('#progress-value'),
  progressBar: document.querySelector('#progress-bar'),
  progressNext: document.querySelector('#progress-next'),
  contractGate: document.querySelector('#contract-gate'),
  todoList: document.querySelector('#todo-list'),
  sessionCount: document.querySelector('#session-count'),
  sessionList: document.querySelector('#session-list'),
  taskCount: document.querySelector('#task-count'),
  taskList: document.querySelector('#task-list'),
  fileCount: document.querySelector('#file-count'),
  fileList: document.querySelector('#file-list'),
  systemDetails: document.querySelector('#system-details'),
  runnerLog: document.querySelector('#runner-log'),
  repositoryStatus: document.querySelector('#repository-status'),
}

const state = {
  snapshot: null,
  selectedSessionId: null,
  selectedChatId: null,
  selectedProjectId: null,
  selectedByUser: false,
  observedJobId: null,
  connected: false,
  submitting: false,
  lastReceivedAt: 0,
  fallbackTimer: null,
  attachments: [],
  recording: null,
  followConversation: false,
}
try { state.selectedProjectId = localStorage.getItem('pemara.selectedProjectId') || null } catch {}

const attachmentLimits = Object.freeze({ count: 8, bytes: 2 * 1024 ** 3, totalBytes: 4 * 1024 ** 3 })
const mediaExtensions = Object.freeze({
  image: ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'avif'],
  audio: ['wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg', 'opus', 'webm'],
  video: ['mp4', 'mkv', 'mov', 'webm', 'avi', 'm4v', 'mpeg', 'mpg'],
})

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function replaceChildren(target, children) {
  target.replaceChildren(...children.filter(Boolean))
}

function formatAge(timestamp) {
  if (!Number.isFinite(timestamp)) return 'sem horário'
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000))
  if (seconds < 5) return 'agora'
  if (seconds < 60) return `há ${seconds}s`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `há ${minutes}min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `há ${hours}h`
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' }).format(timestamp)
}

function formatClock(timestamp) {
  if (!Number.isFinite(timestamp)) return ''
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(timestamp)
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

function activeProject() {
  const projects = state.snapshot?.projects ?? []
  return projects.find(project => project.id === state.selectedProjectId) ?? projects[0]
}

function selectedChat() {
  return (state.snapshot?.chats ?? []).find(chat => chat.id === state.selectedChatId)
}

function selectedProvider() {
  const id = selectedChat()?.providerId ?? 'local-qwen'
  return (state.snapshot?.providers ?? []).find(provider => provider.id === id)
    ?? { id: 'local-qwen', displayName: 'Qwen local', status: 'ready', selectable: true }
}

function shortPath(path) {
  const value = String(path ?? '')
  if (value.length <= 34) return value
  return `…${value.slice(-31)}`
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.message ?? `Falha HTTP ${response.status}`)
  return payload
}

function setProjectFeedback(copy, stateName = '') {
  dom.projectFeedback.hidden = !copy
  dom.projectFeedback.textContent = copy
  dom.projectFeedback.dataset.state = stateName
}

function setProviderFeedback(copy, stateName = '') {
  dom.providerFeedback.hidden = !copy
  dom.providerFeedback.textContent = copy
  dom.providerFeedback.dataset.state = stateName
}

function setSidebarOpen(open) {
  dom.sidebar.classList.toggle('is-open', open)
  dom.sidebarBackdrop.hidden = !open
  dom.sidebarToggle.setAttribute('aria-expanded', String(open))
}

function classifyMedia(file) {
  const prefix = String(file.type || '').split('/')[0]
  if (prefix === 'image' || prefix === 'audio' || prefix === 'video') return prefix
  const extension = String(file.name || '').split('.').pop().toLowerCase()
  return Object.entries(mediaExtensions).find(([, values]) => values.includes(extension))?.[0] ?? null
}

function renderAttachments() {
  const cards = state.attachments.map(attachment => {
    const card = element('article', 'attachment-preview')
    card.setAttribute('role', 'listitem')
    card.dataset.kind = attachment.kind

    let preview
    if (attachment.kind === 'image') {
      preview = element('img')
      preview.src = attachment.url
      preview.alt = ''
    }
    else if (attachment.kind === 'audio') {
      preview = element('audio')
      preview.src = attachment.url
      preview.controls = true
      preview.preload = 'metadata'
    }
    else {
      preview = element('video')
      preview.src = attachment.url
      preview.controls = true
      preview.preload = 'metadata'
    }

    const copy = element('span', 'attachment-preview-copy')
    copy.append(element('strong', '', attachment.file.name), element('span', '', `${attachment.kind} · ${formatBytes(attachment.file.size)}`))
    const remove = element('button', 'attachment-remove', '×')
    remove.type = 'button'
    remove.setAttribute('aria-label', `Remover ${attachment.file.name}`)
    remove.addEventListener('click', () => removeAttachment(attachment.id))
    card.append(preview, copy, remove)
    return card
  })
  replaceChildren(dom.attachmentTray, cards)
  dom.attachmentTray.hidden = cards.length === 0
}

function removeAttachment(id) {
  const index = state.attachments.findIndex(item => item.id === id)
  if (index < 0) return
  URL.revokeObjectURL(state.attachments[index].url)
  state.attachments.splice(index, 1)
  renderAttachments()
}

function clearAttachments() {
  for (const attachment of state.attachments) URL.revokeObjectURL(attachment.url)
  state.attachments = []
  renderAttachments()
}

function addFiles(files) {
  const candidates = Array.from(files || [])
  if (!candidates.length) return
  if (state.attachments.length + candidates.length > attachmentLimits.count) {
    showFeedback(`Você pode enviar até ${attachmentLimits.count} arquivos por mensagem.`, 'error')
    return
  }
  const currentBytes = state.attachments.reduce((total, item) => total + item.file.size, 0)
  let incomingBytes = 0
  for (const file of candidates) {
    const kind = classifyMedia(file)
    if (!kind) {
      showFeedback(`Formato não aceito: ${file.name}. Use foto, áudio ou vídeo.`, 'error')
      return
    }
    if (file.size <= 0 || file.size > attachmentLimits.bytes) {
      showFeedback(`${file.name} excede o limite de 2 GB ou está vazio.`, 'error')
      return
    }
    incomingBytes += file.size
  }
  if (currentBytes + incomingBytes > attachmentLimits.totalBytes) {
    showFeedback('Os anexos desta mensagem excedem 4 GB.', 'error')
    return
  }
  for (const file of candidates) {
    state.attachments.push({
      id: crypto.randomUUID(),
      file,
      kind: classifyMedia(file),
      url: URL.createObjectURL(file),
    })
  }
  showFeedback(`${state.attachments.length} anexo${state.attachments.length === 1 ? '' : 's'} pronto${state.attachments.length === 1 ? '' : 's'} para enviar.`, 'success')
  renderAttachments()
}

function shortSessionId(id) {
  return String(id ?? 'sem-id').replace(/^session-/u, '').slice(0, 10)
}

function firstUserMessage(session) {
  return (session?.activities ?? []).find(item => item.kind === 'user' && item.text)?.text
}

function sessionLabel(session) {
  const user = firstUserMessage(session)
  if (user) return user.split(/\r?\n/u)[0].slice(0, 88)
  return `${session.kind === 'builder' ? 'Builder' : 'Qwen'} · ${shortSessionId(session.session?.id)}`
}

function statusCopy(status) {
  return ({
    completed: 'Concluída',
    error: 'Com erro',
    failed: 'Falhou',
    idle: 'Ociosa',
    interrupted: 'Interrompida',
    queued: 'Preparando',
    running: 'Executando',
  })[status] ?? status ?? 'Desconhecido'
}

function setHealthCard(card, stateName, title, detail) {
  card.dataset.state = stateName
  card.querySelector('strong').textContent = title
  card.querySelector('.health-copy > span').textContent = detail
}

function setConnection(stateName, copy) {
  dom.connectionHealth.dataset.state = stateName
  dom.connectionCopy.textContent = copy
}

function currentJob() {
  return state.snapshot?.control?.job ?? { status: 'idle' }
}

function jobIsActive(job = currentJob()) {
  return job.status === 'queued' || job.status === 'running'
}

function renderHealth(snapshot) {
  const qwen = snapshot.health?.qwen ?? { state: 'offline' }
  if (qwen.state === 'ready') {
    const generating = qwen.generation?.active
    setHealthCard(
      dom.qwenHealth,
      generating ? 'busy' : 'ready',
      generating ? 'Trabalhando' : 'Pronto',
      generating ? `${qwen.generation.decodedTokens ?? 0} tokens gerados` : 'Modelo carregado',
    )
  }
  else {
    setHealthCard(dom.qwenHealth, 'offline', 'Descarregado', 'Inicia ao executar')
  }

  const comfy = snapshot.health?.comfy ?? { state: 'offline' }
  if (comfy.state === 'busy') {
    setHealthCard(dom.comfyHealth, 'busy', 'Em uso', `${comfy.running ?? 0} rodando · ${comfy.pending ?? 0} na fila`)
  }
  else if (comfy.state === 'idle') {
    setHealthCard(dom.comfyHealth, 'ready', 'Livre', 'Fila vazia')
  }
  else {
    setHealthCard(dom.comfyHealth, 'unknown', 'Sem leitura', 'O Harness não interrompe o serviço')
  }

  const active = jobIsActive()
  dom.taskInput.disabled = active || state.submitting
  dom.runTask.disabled = active || state.submitting
  dom.attachFiles.disabled = active || state.submitting || Boolean(state.recording)
  dom.recordAudio.disabled = active || state.submitting
  dom.runTask.querySelector('span').textContent = state.submitting
    ? 'Enviando…'
    : active ? 'Tarefa em andamento' : 'Executar tarefa'
  dom.runTask.setAttribute('aria-label', state.submitting
    ? 'Enviando mensagem'
    : active ? 'Tarefa em andamento' : 'Enviar mensagem')
  dom.taskHint.textContent = active
    ? 'O Pemara está trabalhando nesta conversa'
    : `Enter envia · Shift+Enter quebra a linha · Qwen ${qwen.state === 'ready' ? 'pronto' : 'inicia sozinho'}`
}

function chooseSession(snapshot) {
  const sessions = snapshot.sessions ?? []
  const chats = snapshot.chats ?? []
  const job = snapshot.control?.job
  const currentChat = chats.find(chat => chat.id === state.selectedChatId)
  if (state.selectedByUser && currentChat !== undefined) {
    state.selectedSessionId = currentChat.sessionId ?? null
    return
  }
  if (job?.id && state.observedJobId !== job.id) {
    state.observedJobId = job.id
    if (job.chatId) state.selectedChatId = job.chatId
    state.selectedSessionId = null
    state.selectedByUser = false
  }

  if (state.selectedChatId && currentChat !== undefined && currentChat.sessionId) {
    state.selectedSessionId = currentChat.sessionId
    return
  }

  if (!job?.id) {
    if (!state.selectedByUser) state.selectedSessionId = null
    return
  }

  let candidate
  if (job?.id && Number.isFinite(job.createdAt)) {
    candidate = sessions.find(session => session.kind === 'pemara'
      && Number(session.session?.createdAt ?? session.updatedAt) >= job.createdAt - 10_000)
  }
  candidate ??= sessions.find(session => session.kind === 'pemara')
  state.selectedSessionId = candidate?.session?.id ?? null
  state.selectedChatId = chats.find(chat => chat.sessionId === state.selectedSessionId)?.id ?? state.selectedChatId
}

function selectedSession() {
  const sessions = state.snapshot?.sessions ?? []
  const chat = selectedChat()
  const sessionId = chat?.sessionId ?? state.selectedSessionId
  return sessions.find(session => session.session?.id === sessionId)
}

function renderRunStatus(snapshot) {
  const job = snapshot.control?.job ?? { status: 'idle' }
  const qwen = snapshot.health?.qwen ?? { state: 'offline' }
  let title = 'Pronto para receber uma tarefa'
  let detail = qwen.state === 'ready'
    ? 'O Qwen está carregado e aguardando sua instrução.'
    : 'O Qwen está descarregado para deixar a GPU livre. Ele inicia sozinho quando necessário.'
  let badge = 'Pronto'
  let status = 'idle'

  if (job.status === 'queued' || job.status === 'running') {
    status = 'running'
    if (qwen.state !== 'ready') {
      title = 'Preparando o Qwen com segurança'
      detail = 'O Harness está conferindo fila, uso da GPU e VRAM. Nenhum outro trabalho será encerrado.'
      badge = 'Preparando'
    }
    else {
      title = 'Qwen executando a tarefa'
      detail = job.task ?? 'A execução está em andamento.'
      badge = 'Ao vivo'
    }
  }
  else if (job.status === 'completed') {
    status = 'completed'
    title = 'Tarefa encerrada pelo runtime'
    detail = 'O resultado e as ferramentas usadas estão registrados logo abaixo.'
    badge = 'Concluída'
  }
  else if (job.status === 'failed') {
    status = 'error'
    title = 'A execução parou com erro'
    detail = job.detail ?? 'Abra os detalhes técnicos para consultar o log preservado.'
    badge = 'Atenção'
  }
  else if (job.status === 'interrupted') {
    status = 'warning'
    title = 'A execução anterior foi interrompida'
    detail = job.detail ?? 'Os registros foram preservados. Você pode iniciar outra tarefa.'
    badge = 'Interrompida'
  }

  dom.runStatus.dataset.state = status
  dom.runTitle.textContent = title
  dom.runDetail.textContent = detail
  dom.runBadge.textContent = badge
}

function toolStatusText(status) {
  return ({ error: 'Falhou', running: 'Em execução', success: 'Concluiu' })[status] ?? status
}

function friendlyToolName(name) {
  const value = String(name ?? '').toLowerCase()
  if (value.includes('checkpoint')) return 'Salvando o progresso'
  if (value.includes('begin_round')) return 'Iniciando uma etapa'
  if (value.includes('completion')) return 'Conferindo a conclusão'
  if (value.includes('test') || value.includes('check')) return 'Executando uma verificação'
  if (value.includes('write') || value.includes('edit') || value.includes('patch')) return 'Alterando um arquivo'
  if (value.includes('read') || value.includes('view') || value.includes('search')) return 'Consultando informações'
  if (value.includes('shell') || value.includes('command') || value.includes('process')) return 'Executando uma ação'
  return 'Trabalhando'
}

function renderActivityRow(activity) {
  const row = element('article', `activity-row activity-${activity.kind}`)
  const glyph = element('span', 'activity-glyph')
  glyph.textContent = activity.kind === 'tool'
    ? activity.status === 'success' ? '✓' : activity.status === 'error' ? '!' : '›'
    : activity.kind === 'user' ? 'Você' : 'Q'
  row.append(glyph)

  const card = element('div', 'activity-card')
  if (activity.kind === 'message' || activity.kind === 'user') {
    card.classList.add(activity.kind === 'user' ? 'user-card' : 'message-card')
    card.append(element('p', '', activity.text))
    card.append(element('time', 'activity-time', formatClock(activity.time)))
    row.append(card)
    return row
  }

  card.classList.add('tool-card')
  const header = element('div', 'tool-header')
  const copy = element('div', 'tool-copy')
  copy.append(element('strong', '', friendlyToolName(activity.name)))
  copy.append(element('span', '', activity.summary || 'Executando uma etapa'))
  header.append(copy)
  const badge = element('span', 'tool-badge', toolStatusText(activity.status))
  badge.dataset.state = activity.status
  header.append(badge)
  card.append(header)

  if (activity.detail || activity.result) {
    const details = element('details', 'tool-details')
    details.append(element('summary', '', activity.result ? 'Ver entrada e resultado' : 'Ver entrada'))
    const output = [
      activity.name && `Ação técnica\n${activity.name}`,
      activity.detail && `Entrada\n${activity.detail}`,
      activity.result && `Resultado\n${activity.result}`,
    ].filter(Boolean).join('\n\n')
    details.append(element('pre', '', output))
    card.append(details)
  }
  if (activity.files?.length) {
    const files = element('div', 'file-chips')
    for (const file of activity.files) files.append(element('span', 'file-chip', file))
    card.append(files)
  }
  row.append(card)
  return row
}

function renderActivity(snapshot) {
  const session = selectedSession()
  const job = snapshot.control?.job ?? { status: 'idle' }
  const chat = selectedChat()
  const rows = []
  if (session) rows.push(...(session.activities ?? []).map(renderActivityRow))
  else if (Array.isArray(chat?.messages)) {
    rows.push(...chat.messages.map(message => renderActivityRow({
      kind: message.role === 'assistant' ? 'message' : message.role,
      text: message.text,
      time: message.createdAt,
    })))
  }

  if (rows.length === 0 && jobIsActive(job) && (!chat || !job.chatId || job.chatId === chat.id)) {
    rows.push(renderActivityRow({ kind: 'user', text: job.task, time: job.createdAt }))
    const waiting = element('article', 'activity-row activity-system')
    waiting.append(element('span', 'activity-glyph', '…'))
    const card = element('div', 'activity-card system-card')
    card.append(element('strong', '', snapshot.health?.qwen?.state === 'ready' ? 'Preparando a execução' : 'Aguardando condição segura da GPU'))
    card.append(element('p', '', 'Esta tela será atualizada automaticamente. Você não precisa acompanhar um terminal.'))
    waiting.append(card)
    rows.push(waiting)
  }

  if (rows.length === 0) {
    const empty = element('div', 'empty-state')
    const mark = element('span', 'empty-mark', 'P')
    mark.setAttribute('aria-hidden', 'true')
    empty.append(mark)
    empty.append(element('h2', '', 'Como posso ajudar?'))
    empty.append(element('p', '', 'Escreva como falaria com o GPT ou com o Codex. O Pemara cuida do modelo, da GPU e do histórico.'))
    const starters = element('div', 'starter-prompts')
    for (const prompt of [
      'Revise este projeto e corrija os problemas encontrados',
      'Implemente a próxima tarefa do plano e rode os testes',
      'Explique o estado atual e diga o que ainda falta',
    ]) {
      const button = element('button', 'starter-button', prompt)
      button.type = 'button'
      button.addEventListener('click', () => {
        dom.taskInput.value = prompt
        resizeTaskInput()
        dom.taskInput.focus()
      })
      starters.append(button)
    }
    empty.append(starters)
    rows.push(empty)
  }

  replaceChildren(dom.activityFeed, rows)
  if (state.followConversation) {
    requestAnimationFrame(() => dom.activityFeed.lastElementChild?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }))
  }
  dom.activityFeed.dataset.rendered = 'true'

  if (session) {
    dom.activityTitle.textContent = chat?.title ?? sessionLabel(session)
    dom.activitySubtitle.textContent = `${session.kind === 'builder' ? 'Builder isolado' : 'Sessão principal'} · turno ${session.currentTurn ?? 0} · etapa ${session.currentStep ?? 0}`
    dom.sessionState.textContent = statusCopy(session.status)
    dom.sessionState.dataset.state = session.status
  }
  else {
    dom.activityTitle.textContent = chat?.title ?? 'Nova conversa'
    dom.activitySubtitle.textContent = chat?.projectPath ? `${shortPath(chat.projectPath)} · pronto para conversar` : 'Diga o que você quer fazer.'
    dom.sessionState.textContent = jobIsActive(job) ? 'Preparando' : 'Pronto'
    dom.sessionState.dataset.state = job.status
  }
}

function renderProgress(snapshot) {
  const todo = snapshot.todo ?? { completed: 0, total: 0, items: [] }
  dom.progressValue.textContent = `${todo.completed} / ${todo.total}`
  const percent = todo.total > 0 ? Math.round((todo.completed / todo.total) * 100) : 0
  dom.progressBar.style.width = `${percent}%`
  const next = todo.items?.find(item => !item.done)
  dom.progressNext.textContent = next ? `Próximo: ${next.text}` : (todo.total ? 'Plano marcado como concluído.' : 'Nenhum item registrado.')
  const visibleItems = (todo.items ?? []).slice(0, 10).map(item => {
    const row = element('div', `compact-row${item.done ? ' is-done' : ''}`)
    row.append(element('span', 'row-mark', item.done ? '✓' : '·'))
    row.append(element('span', '', item.text))
    return row
  })
  replaceChildren(dom.todoList, visibleItems)
}

function renderContract(snapshot) {
  const contract = snapshot.contract ?? { state: 'inactive' }
  dom.contractGate.hidden = contract.state === 'inactive'
  if (contract.state === 'inactive') return
  dom.contractGate.dataset.state = contract.state
  const title = contract.state === 'clean'
    ? `${contract.taskId}: dentro do pacote`
    : contract.state === 'violated' ? `${contract.taskId}: promoção bloqueada` : `${contract.taskId}: gate indisponível`
  const detail = contract.state === 'violated'
    ? `${contract.violations?.length ?? 0} caminho(s) fora do escopo`
    : contract.state === 'clean' ? `${contract.touchedCount ?? 0}/${contract.maxFiles ?? '—'} arquivos tocados` : (contract.detail ?? '')
  replaceChildren(dom.contractGate, [element('strong', '', title), element('span', '', detail)])
}

function renderProjectContext(snapshot) {
  const project = activeProject()
  const name = project?.name ?? 'Pemara'
  dom.conversationProjectName.textContent = name
  dom.composerProjectName.textContent = name
  dom.composerProject.title = project?.path ?? name
  dom.topbarProject.textContent = name
  dom.topbarProject.title = project?.path ?? name
  dom.sidebarFooterStatus.textContent = project?.path ? `${shortPath(project.path)} · local` : 'Loopback local · histórico preservado'
}

function providerStatusCopy(provider) {
  const labels = {
    ready: 'Pronto',
    disabled: 'Desativado',
    needs_credential: 'Falta credencial',
    needs_install: 'Falta instalar',
    needs_authentication: 'Falta autenticar',
  }
  return labels[provider?.status] ?? 'Indisponível'
}

function renderProviderContext() {
  const provider = selectedProvider()
  dom.conversationProviderName.textContent = provider.displayName
  dom.conversationProvider.title = `${provider.displayName} · ${providerStatusCopy(provider)}`
  dom.conversationProvider.dataset.state = provider.status
}

function renderChats(snapshot) {
  const chats = snapshot.chats ?? []
  const query = dom.chatSearch.value.trim().toLocaleLowerCase('pt-BR')
  const filtered = query === '' ? chats : chats.filter(chat => [chat.title, chat.preview, chat.lastTask, chat.projectPath].some(value => String(value ?? '').toLocaleLowerCase('pt-BR').includes(query)))
  dom.chatCount.textContent = String(chats.length)
  const rows = filtered.map(chat => {
    const wrapper = element('div', 'chat-row')
    wrapper.setAttribute('role', 'listitem')
    const button = element('button', 'chat-item')
    button.type = 'button'
    button.setAttribute('aria-current', String(chat.id === state.selectedChatId))
    const status = element('span', 'chat-item-status')
    status.dataset.state = chat.status ?? 'idle'
    status.setAttribute('aria-hidden', 'true')
    const copy = element('span', 'chat-item-copy')
    copy.append(element('strong', '', chat.title || 'Nova conversa'))
    copy.append(element('span', '', chat.preview || `${chat.projectPath ? shortPath(chat.projectPath) : 'Pemara'} · ${formatAge(chat.updatedAt)}`))
    button.append(status, copy)
    button.addEventListener('click', () => {
      state.selectedChatId = chat.id
      state.selectedSessionId = chat.sessionId ?? null
      state.selectedProjectId = chat.projectId ?? state.selectedProjectId
      state.selectedByUser = true
      setSidebarOpen(false)
      renderAll()
      dom.activityFeed.focus({ preventScroll: true })
    })
    wrapper.append(button)
    return wrapper
  })
  if (rows.length === 0) {
    const empty = element('p', 'sidebar-empty', query ? 'Nenhuma conversa encontrada.' : 'Nenhuma conversa ainda.')
    replaceChildren(dom.chatList, [empty])
  }
  else replaceChildren(dom.chatList, rows)
}

function renderProjects(snapshot) {
  const projects = snapshot.projects ?? []
  const rows = projects.map(project => {
    const wrapper = element('div', 'project-row')
    wrapper.setAttribute('role', 'listitem')
    const button = element('button', 'project-item')
    button.type = 'button'
    button.setAttribute('aria-current', String(project.id === state.selectedProjectId))
    const icon = element('span', 'project-item-icon', project.isDefault ? 'P' : '⌂')
    icon.setAttribute('aria-hidden', 'true')
    const copy = element('span', 'project-item-copy')
    copy.append(element('strong', '', project.name))
    copy.append(element('span', '', shortPath(project.path)))
    button.append(icon, copy)
    button.addEventListener('click', () => void selectProject(project.id))
    wrapper.append(button)
    return wrapper
  })
  replaceChildren(dom.projectList, rows.length ? rows : [element('p', 'sidebar-empty', 'Vincule seu primeiro projeto.')])
}

function renderSessions(snapshot) {
  const sessions = snapshot.sessions ?? []
  dom.sessionCount.textContent = String(sessions.length)
  const buttons = sessions.map(session => {
    const button = element('button', 'session-button')
    button.type = 'button'
    button.dataset.state = session.status
    button.setAttribute('aria-current', String(session.session?.id === state.selectedSessionId))
    const copy = element('span', 'session-copy')
    copy.append(element('strong', '', sessionLabel(session)))
    copy.append(element('span', '', `${session.kind === 'builder' ? 'Builder' : 'Principal'} · ${statusCopy(session.status)}`))
    button.append(copy)
    button.append(element('span', 'session-age', formatAge(session.updatedAt)))
    button.addEventListener('click', () => {
      state.selectedSessionId = session.session?.id
      state.selectedChatId = (state.snapshot?.chats ?? []).find(chat => chat.sessionId === state.selectedSessionId)?.id ?? state.selectedChatId
      state.selectedByUser = true
      renderAll()
      dom.activityFeed.focus({ preventScroll: true })
    })
    return button
  })
  replaceChildren(dom.sessionList, buttons.length ? buttons : [element('p', 'empty-copy', 'Nenhuma sessão persistida.')])
}

function renderTasks(snapshot) {
  const tasks = snapshot.tasks ?? []
  dom.taskCount.textContent = String(tasks.length)
  const rows = tasks.slice(0, 10).map(task => {
    const row = element('div', 'compact-row durable-row')
    const copy = element('span')
    copy.append(element('strong', '', task.objective ?? task.id))
    copy.append(element('small', '', `${task.status} · ${task.roundsStarted ?? 0}/${task.maxRounds ?? 0} rodadas`))
    row.append(copy)
    return row
  })
  replaceChildren(dom.taskList, rows.length ? rows : [element('p', 'empty-copy', 'Sem tarefa durável recente.')])
}

function renderFiles(snapshot) {
  const files = snapshot.files ?? []
  dom.fileCount.textContent = String(files.length)
  const rows = files.slice(0, 12).map(file => {
    const row = element('div', 'compact-row file-row')
    row.append(element('strong', '', file.path))
    row.append(element('small', '', `${formatAge(file.updatedAt)} · ${formatBytes(file.size)}`))
    return row
  })
  replaceChildren(dom.fileList, rows.length ? rows : [element('p', 'empty-copy', 'Nenhum arquivo recente.')])
}

function renderSystem(snapshot) {
  const qwen = snapshot.health?.qwen ?? {}
  const comfy = snapshot.health?.comfy ?? {}
  const job = snapshot.control?.job ?? { status: 'idle' }
  const cards = [
    ['Qwen', `${qwen.state ?? 'desconhecido'} · ${qwen.model ?? 'modelo descarregado'}`],
    ['ComfyUI', `${comfy.state ?? 'desconhecido'} · ${comfy.running ?? 0} rodando · ${comfy.pending ?? 0} na fila`],
    ['Executor visual', job.id ? `${statusCopy(job.status)} · ${job.id}` : 'Nenhuma tarefa iniciada'],
    ['Workspace', snapshot.projectRoot ?? 'indisponível'],
  ].map(([title, detail]) => {
    const card = element('div', 'system-row')
    card.append(element('strong', '', title))
    card.append(element('span', '', detail))
    return card
  })
  replaceChildren(dom.systemDetails, cards)
  const logs = [job.stdout, job.stderr && `ERROS\n${job.stderr}`].filter(Boolean).join('\n\n')
  dom.runnerLog.textContent = logs || 'Nenhuma saída registrada por esta interface.'
  dom.repositoryStatus.textContent = (snapshot.repository ?? []).join('\n') || 'Worktree limpo.'
}

function renderAll() {
  const snapshot = state.snapshot
  if (!snapshot) return
  if (!state.selectedProjectId || !(snapshot.projects ?? []).some(project => project.id === state.selectedProjectId)) {
    state.selectedProjectId = snapshot.projects?.[0]?.id ?? null
  }
  try { if (state.selectedProjectId) localStorage.setItem('pemara.selectedProjectId', state.selectedProjectId) } catch {}
  chooseSession(snapshot)
  renderProjectContext(snapshot)
  renderProviderContext()
  renderChats(snapshot)
  renderProjects(snapshot)
  renderHealth(snapshot)
  renderRunStatus(snapshot)
  renderActivity(snapshot)
  renderProgress(snapshot)
  renderContract(snapshot)
  renderSessions(snapshot)
  renderTasks(snapshot)
  renderFiles(snapshot)
  renderSystem(snapshot)
  dom.lastUpdate.textContent = `Atualizado ${formatAge(snapshot.generatedAt)}`
}

function receiveSnapshot(snapshot) {
  state.snapshot = snapshot
  state.lastReceivedAt = Date.now()
  state.connected = true
  setConnection('connected', 'Ao vivo')
  renderAll()
}

async function fetchSnapshot() {
  try {
    const response = await fetch('/api/snapshot', { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    receiveSnapshot(await response.json())
  }
  catch {
    state.connected = false
    setConnection('disconnected', 'Reconectando')
  }
}

function showFeedback(copy, stateName) {
  dom.formFeedback.hidden = !copy
  dom.formFeedback.textContent = copy
  dom.formFeedback.dataset.state = stateName
}

async function createChatForProject(projectId = state.selectedProjectId) {
  const payload = await apiJson('/api/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Pemara-Request': 'chat' },
    body: JSON.stringify(projectId ? { projectId } : {}),
  })
  state.selectedChatId = payload.chat.id
  state.selectedSessionId = null
  state.selectedProjectId = payload.chat.projectId
  state.selectedByUser = true
  await fetchSnapshot()
  return payload.chat
}

async function startNewChat() {
  try {
    await createChatForProject()
    dom.taskInput.value = ''
    clearAttachments()
    resizeTaskInput()
    dom.taskInput.focus()
    setSidebarOpen(false)
  }
  catch (error) {
    showFeedback(error instanceof Error ? error.message : 'Não foi possível abrir uma nova conversa.', 'error')
  }
}

async function selectProject(projectId) {
  const project = (state.snapshot?.projects ?? []).find(item => item.id === projectId)
  if (project === undefined) return
  state.selectedProjectId = project.id
  try { localStorage.setItem('pemara.selectedProjectId', project.id) } catch {}
  const chat = selectedChat()
  if (chat?.projectId !== project.id) {
    state.selectedChatId = null
    state.selectedSessionId = null
    state.selectedByUser = false
    try { await createChatForProject(project.id) }
    catch (error) { showFeedback(error instanceof Error ? error.message : 'Não foi possível trocar de projeto.', 'error') }
  }
  else renderAll()
  setSidebarOpen(false)
}

function renderProjectSuggestions() {
  const projects = (state.snapshot?.projects ?? []).filter(project => !project.isRegistered)
  const buttons = projects.slice(0, 12).map(project => {
    const button = element('button', 'project-suggestion')
    button.type = 'button'
    button.append(element('span', '', project.name), element('small', '', shortPath(project.path)))
    button.addEventListener('click', () => {
      dom.projectPath.value = project.path
      if (!dom.projectName.value) dom.projectName.value = project.name
      dom.projectPath.focus()
    })
    return button
  })
  replaceChildren(dom.projectSuggestions, buttons)
}

function openProjectDialog() {
  setProjectFeedback('')
  dom.projectPath.value = ''
  dom.projectName.value = ''
  renderProjectSuggestions()
  if (typeof dom.projectDialog.showModal === 'function') dom.projectDialog.showModal()
  else dom.projectDialog.setAttribute('open', '')
  requestAnimationFrame(() => dom.projectPath.focus())
}

function closeProjectDialog() {
  if (typeof dom.projectDialog.close === 'function' && dom.projectDialog.open) dom.projectDialog.close()
  else dom.projectDialog.removeAttribute('open')
}

function closeProviderDialog() {
  if (typeof dom.providerDialog.close === 'function' && dom.providerDialog.open) dom.providerDialog.close()
  else dom.providerDialog.removeAttribute('open')
}

function renderProviders() {
  const current = selectedProvider().id
  const rows = (state.snapshot?.providers ?? []).map(provider => {
    const card = element('article', 'provider-card')
    card.dataset.status = provider.status
    const copy = element('div', 'provider-copy')
    const heading = element('div', 'provider-heading')
    heading.append(element('strong', '', provider.displayName), element('span', 'provider-status', providerStatusCopy(provider)))
    copy.append(heading, element('p', '', provider.detail || provider.description), element('small', '', provider.egress || ''))
    const actions = element('div', 'provider-actions')
    if (provider.id !== 'local-qwen') {
      const toggle = element('button', 'dialog-button secondary', provider.enabled ? 'Desativar' : 'Ativar')
      toggle.type = 'button'
      toggle.addEventListener('click', () => void toggleProvider(provider))
      actions.append(toggle)
    }
    if (provider.kind === 'model') {
      const choose = element('button', 'dialog-button primary', provider.id === current ? 'Em uso' : 'Usar neste chat')
      choose.type = 'button'
      choose.disabled = !provider.selectable || provider.id === current
      choose.addEventListener('click', () => void chooseProvider(provider))
      actions.append(choose)
    }
    card.append(copy, actions)
    return card
  })
  replaceChildren(dom.providerList, rows)
}

function openProviderDialog() {
  setProviderFeedback('')
  renderProviders()
  if (typeof dom.providerDialog.showModal === 'function') dom.providerDialog.showModal()
  else dom.providerDialog.setAttribute('open', '')
}

async function toggleProvider(provider) {
  setProviderFeedback(`${provider.enabled ? 'Desativando' : 'Ativando'} ${provider.displayName}…`)
  try {
    await apiJson(`/api/providers/${encodeURIComponent(provider.id)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-Pemara-Request': 'provider' },
      body: JSON.stringify({ enabled: !provider.enabled }),
    })
    await fetchSnapshot()
    renderProviders()
    const updated = (state.snapshot?.providers ?? []).find(item => item.id === provider.id)
    setProviderFeedback(updated?.detail ?? 'Provedor atualizado.', updated?.selectable ? 'success' : '')
  }
  catch (error) {
    setProviderFeedback(error instanceof Error ? error.message : 'Não foi possível atualizar o provedor.', 'error')
  }
}

async function chooseProvider(provider) {
  const chat = await ensureActiveChat()
  setProviderFeedback(`Selecionando ${provider.displayName}…`)
  try {
    await apiJson(`/api/chats/${encodeURIComponent(chat.id)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-Pemara-Request': 'chat' },
      body: JSON.stringify({ providerId: provider.id }),
    })
    await fetchSnapshot()
    closeProviderDialog()
    showFeedback(`${provider.displayName} selecionado para este chat.`, 'success')
  }
  catch (error) {
    setProviderFeedback(error instanceof Error ? error.message : 'Não foi possível trocar o modelo.', 'error')
  }
}

async function submitProject(event) {
  event.preventDefault()
  setProjectFeedback('Vinculando pasta…')
  try {
    const payload = await apiJson('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Pemara-Request': 'project' },
      body: JSON.stringify({ path: dom.projectPath.value.trim(), name: dom.projectName.value.trim() || undefined }),
    })
    closeProjectDialog()
    await fetchSnapshot()
    state.selectedProjectId = payload.project.id
    state.selectedChatId = null
    state.selectedSessionId = null
    state.selectedByUser = false
    await createChatForProject(payload.project.id)
    dom.taskInput.focus()
  }
  catch (error) {
    setProjectFeedback(error instanceof Error ? error.message : 'Não foi possível vincular o projeto.', 'error')
  }
}

async function ensureActiveChat() {
  const project = activeProject()
  const chat = selectedChat()
  if (chat !== undefined && !chat.legacy && chat.projectId === project?.id) return chat
  return createChatForProject(project?.id)
}

async function submitTask(event) {
  event.preventDefault()
  const task = dom.taskInput.value.trim()
  if (task.length < 3 && state.attachments.length === 0) {
    showFeedback('Descreva a tarefa com pelo menos 3 caracteres.', 'error')
    dom.taskInput.focus()
    return
  }
  state.submitting = true
  showFeedback('', '')
  renderHealth(state.snapshot ?? {})
  const uploadedIds = []
  try {
    const chat = await ensureActiveChat()
    for (const [index, attachment] of state.attachments.entries()) {
      showFeedback(`Enviando anexo ${index + 1} de ${state.attachments.length}…`, '')
      const upload = await fetch('/api/attachments', {
        method: 'POST',
        headers: {
          'Content-Type': attachment.file.type || `${attachment.kind}/octet-stream`,
          'X-Pemara-Request': 'attachment',
          'X-Pemara-Filename': encodeURIComponent(attachment.file.name),
        },
        body: attachment.file,
      })
      const uploadPayload = await upload.json().catch(() => ({}))
      if (!upload.ok) throw new Error(uploadPayload.message ?? `Falha ao enviar ${attachment.file.name}`)
      uploadedIds.push(uploadPayload.attachment.id)
    }
    const response = await fetch('/api/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Pemara-Request': 'task',
      },
      body: JSON.stringify({ task, attachmentIds: uploadedIds, chatId: chat.id, projectId: chat.projectId }),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.message ?? `Falha HTTP ${response.status}`)
    state.observedJobId = payload.job?.id ?? null
    state.selectedSessionId = null
    state.selectedByUser = false
    state.followConversation = true
    dom.taskInput.value = ''
    clearAttachments()
    resizeTaskInput()
    showFeedback('Mensagem enviada.', 'success')
    await fetchSnapshot()
  }
  catch (error) {
    await Promise.allSettled(uploadedIds.map(id => fetch(`/api/attachments/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { 'X-Pemara-Request': 'attachment' },
    })))
    showFeedback(error instanceof Error ? error.message : 'Não foi possível iniciar a tarefa.', 'error')
  }
  finally {
    state.submitting = false
    renderHealth(state.snapshot ?? {})
  }
}

function recorderMimeType() {
  const supported = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm']
  return supported.find(type => MediaRecorder.isTypeSupported?.(type)) ?? ''
}

async function toggleRecording() {
  if (state.recording) {
    const { recorder } = state.recording
    if (recorder.state === 'recording') {
      try {
        recorder.requestData()
      }
      catch {}
      recorder.stop()
    }
    return
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    showFeedback('Este navegador não disponibiliza gravação de áudio.', 'error')
    return
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = recorderMimeType()
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    const chunks = []
    const resetRecorder = () => {
      stream.getTracks().forEach(track => track.stop())
      state.recording = null
      dom.recordAudio.dataset.recording = 'false'
      dom.recordAudio.setAttribute('aria-label', 'Gravar áudio')
      dom.recordAudio.title = 'Gravar áudio'
      renderHealth(state.snapshot ?? {})
    }
    recorder.addEventListener('dataavailable', event => {
      if (event.data.size) chunks.push(event.data)
    })
    recorder.addEventListener('stop', () => {
      const type = recorder.mimeType || mimeType || 'audio/webm'
      const extension = type.includes('ogg') ? 'ogg' : 'webm'
      const stamp = new Date().toISOString().replace(/[:.]/gu, '-')
      const file = new File(chunks, `voz-${stamp}.${extension}`, { type })
      resetRecorder()
      addFiles([file])
    }, { once: true })
    recorder.addEventListener('error', event => {
      resetRecorder()
      const detail = event.error?.message ? `: ${event.error.message}` : ''
      showFeedback(`A gravação de áudio foi interrompida${detail}.`, 'error')
    }, { once: true })
    recorder.start(500)
    state.recording = { recorder, stream }
    dom.recordAudio.dataset.recording = 'true'
    dom.recordAudio.setAttribute('aria-label', 'Parar gravação de áudio')
    dom.recordAudio.title = 'Parar gravação'
    showFeedback('Gravando áudio… toque novamente no microfone para parar.', '')
    renderHealth(state.snapshot ?? {})
  }
  catch (error) {
    showFeedback(error instanceof Error ? `Não foi possível usar o microfone: ${error.message}` : 'Não foi possível usar o microfone.', 'error')
  }
}

function resizeTaskInput() {
  dom.taskInput.style.height = 'auto'
  dom.taskInput.style.height = `${Math.min(dom.taskInput.scrollHeight, 190)}px`
}

function connect() {
  setConnection('connecting', 'Conectando')
  const events = new EventSource('/events')
  events.addEventListener('snapshot', event => {
    try {
      receiveSnapshot(JSON.parse(event.data))
    }
    catch {
      setConnection('error', 'Resposta inválida')
    }
  })
  events.addEventListener('monitor-error', () => setConnection('error', 'Falha de leitura'))
  events.onerror = () => {
    state.connected = false
    setConnection('disconnected', 'Reconectando')
    if (!state.fallbackTimer) {
      state.fallbackTimer = setInterval(() => {
        if (Date.now() - state.lastReceivedAt > 3500) void fetchSnapshot()
      }, 4000)
    }
  }
}

dom.taskForm.addEventListener('submit', submitTask)
dom.newChat.addEventListener('click', () => void startNewChat())
dom.chatSearch.addEventListener('input', () => renderChats(state.snapshot ?? {}))
dom.addProject.addEventListener('click', openProjectDialog)
dom.conversationProject.addEventListener('click', openProjectDialog)
dom.composerProject.addEventListener('click', openProjectDialog)
dom.conversationProvider.addEventListener('click', openProviderDialog)
dom.projectForm.addEventListener('submit', submitProject)
dom.closeProjectDialog.addEventListener('click', closeProjectDialog)
dom.cancelProject.addEventListener('click', closeProjectDialog)
dom.closeProviderDialog.addEventListener('click', closeProviderDialog)
dom.closeProvider.addEventListener('click', closeProviderDialog)
dom.sidebarToggle.addEventListener('click', () => setSidebarOpen(true))
dom.sidebarClose.addEventListener('click', () => setSidebarOpen(false))
dom.sidebarBackdrop.addEventListener('click', () => setSidebarOpen(false))
document.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    dom.chatSearch.focus()
    dom.chatSearch.select()
  }
  if (event.key === 'Escape') {
    setSidebarOpen(false)
    if (dom.projectDialog.open) closeProjectDialog()
    if (dom.providerDialog.open) closeProviderDialog()
  }
})
dom.attachFiles.addEventListener('click', () => dom.attachmentInput.click())
dom.attachmentInput.addEventListener('change', () => {
  addFiles(dom.attachmentInput.files)
  dom.attachmentInput.value = ''
})
dom.recordAudio.addEventListener('click', () => void toggleRecording())
dom.composerWrap.addEventListener('dragover', event => {
  if (!event.dataTransfer?.types.includes('Files')) return
  event.preventDefault()
  dom.composerWrap.classList.add('is-dragging')
})
dom.composerWrap.addEventListener('dragleave', event => {
  if (!dom.composerWrap.contains(event.relatedTarget)) dom.composerWrap.classList.remove('is-dragging')
})
dom.composerWrap.addEventListener('drop', event => {
  dom.composerWrap.classList.remove('is-dragging')
  if (!event.dataTransfer?.files.length) return
  event.preventDefault()
  addFiles(event.dataTransfer.files)
})
dom.taskInput.addEventListener('paste', event => {
  const files = Array.from(event.clipboardData?.items ?? []).filter(item => item.kind === 'file').map(item => item.getAsFile()).filter(Boolean)
  if (!files.length) return
  event.preventDefault()
  addFiles(files)
})
dom.taskInput.addEventListener('keydown', event => {
  if (event.key !== 'Enter' || event.isComposing) return
  if (event.shiftKey) return
  event.preventDefault()
  dom.taskForm.requestSubmit()
})
dom.taskInput.addEventListener('input', resizeTaskInput)
window.addEventListener('scroll', () => {
  const distanceFromBottom = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight)
  if (distanceFromBottom > 180) state.followConversation = false
}, { passive: true })
resizeTaskInput()

setInterval(() => {
  if (!state.snapshot) return
  dom.lastUpdate.textContent = `Atualizado ${formatAge(state.snapshot.generatedAt)}`
  if (state.connected && Date.now() - state.lastReceivedAt > 7000) setConnection('disconnected', 'Sem atualização')
}, 1000)

connect()
