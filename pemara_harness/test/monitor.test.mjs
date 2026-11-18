import assert from 'node:assert/strict'
import { mkdtemp, mkdir, readFile, realpath, writeFile } from 'node:fs/promises'
import { get as httpGet } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import { constants, zstdCompressSync } from 'node:zlib'

import {
  createMonitorServer,
  decodeSessionArtifact,
  evaluateTaskContract,
  normalizeSessionLiveness,
  parseTodoProgress,
  parseQwenSlotProgress,
  redactSensitive,
  resolveGitExecutable,
} from '../src/monitor.mjs'

const ZSTD_OPTIONS = { params: { [constants.ZSTD_c_checksumFlag]: 1 } }

function frame(lines) {
  return zstdCompressSync(Buffer.from(`${lines.map(line => JSON.stringify(line)).join('\n')}\n`), ZSTD_OPTIONS)
}

function fixtureArtifact() {
  const header = {
    type: 'session',
    version: 1,
    id: 'session-monitor-test',
    createdAt: 1_787_320_000_000,
    cwd: 'E:\\Pemara',
    delegationDepth: 0,
  }
  const records = [
    { type: 'turn/start', seq: 0, time: 1_787_320_000_100, data: { turn: 1 } },
    {
      type: 'user/message',
      seq: 0.5,
      time: 1_787_320_000_105,
      data: { turn: 1, message: { role: 'user', content: [{ type: 'text', text: 'Implantar o pacote seguro' }] } },
    },
    { type: 'step/start', seq: 1, time: 1_787_320_000_110, data: { turn: 1, step: 1 } },
    {
      type: 'reasoning-chunks',
      seq0: 2,
      time0: 1_787_320_000_120,
      data: { turn: 1, step: 1, index: 0, dt: [1], texts: ['NAO EXIBIR RACIOCINIO PRIVADO'] },
    },
    {
      type: 'text-chunks',
      seq0: 3,
      time0: 1_787_320_000_130,
      data: { turn: 1, step: 1, index: 1, dt: [1], texts: ['PENSAMENTO INTERMEDIARIO SEM MARCADOR'] },
    },
    {
      type: 'assistant/message',
      seq: 5,
      time: 1_787_320_000_150,
      data: {
        turn: 1,
        step: 1,
        message: {
          role: 'assistant',
          content: [
            { type: 'reasoning', text: 'NAO EXIBIR RACIOCINIO PRIVADO' },
            { type: 'text', text: 'PENSAMENTO INTERMEDIARIO SEM MARCADOR' },
          ],
        },
      },
    },
    {
      type: 'tool/call',
      seq: 6,
      time: 1_787_320_000_160,
      data: {
        turn: 1,
        step: 1,
        callId: 'call-1',
        name: 'pwsh',
        arguments: JSON.stringify({ command: 'npm test', apiKey: 'segredo-local' }),
      },
    },
    {
      type: 'tool/result',
      seq: 7,
      time: 1_787_320_000_200,
      data: {
        turn: 1,
        step: 1,
        message: {
          source: { kind: 'tool', callId: 'call-1' },
          content: [{
            type: 'tool-result',
            toolCallId: 'call-1',
            content: [{ type: 'text', text: '23 testes passaram' }],
            isError: false,
          }],
          role: 'user',
        },
        meta: { diffs: [{ path: 'src/example.mjs' }] },
      },
    },
    { type: 'step/end', seq: 8, time: 1_787_320_000_210, data: { turn: 1, step: 1 } },
  ]
  return Buffer.concat([frame([header]), frame(records)])
}

test('decodeSessionArtifact exposes visible work and tool results without private reasoning', () => {
  const decoded = decodeSessionArtifact(fixtureArtifact(), { sourcePath: 'fixture.jsonl.zstd' })

  assert.equal(decoded.session.id, 'session-monitor-test')
  assert.equal(decoded.status, 'running')
  assert.equal(decoded.currentStep, 1)
  assert.equal(decoded.activities.find(item => item.kind === 'message'), undefined)
  assert.equal(decoded.activities.find(item => item.kind === 'user')?.text, 'Implantar o pacote seguro')

  const tool = decoded.activities.find(item => item.kind === 'tool')
  assert.equal(tool.name, 'pwsh')
  assert.equal(tool.status, 'success')
  assert.match(tool.summary, /npm test/)
  assert.match(tool.result, /23 testes passaram/)
  assert.deepEqual(tool.files, ['src/example.mjs'])

  const serialized = JSON.stringify(decoded)
  assert.doesNotMatch(serialized, /NAO EXIBIR RACIOCINIO PRIVADO/)
  assert.doesNotMatch(serialized, /PENSAMENTO INTERMEDIARIO SEM MARCADOR/)
  assert.doesNotMatch(serialized, /segredo-local/)
})

test('decodeSessionArtifact releases only the final assistant message after turn completion', () => {
  const completed = Buffer.concat([
    fixtureArtifact(),
    frame([
      {
        type: 'assistant/message',
        seq: 9,
        time: 1_787_320_000_220,
        data: {
          turn: 1,
          step: 2,
          message: { role: 'assistant', content: [{ type: 'text', text: 'Pacote implantado e testes aprovados.' }] },
        },
      },
      { type: 'turn/end', seq: 10, time: 1_787_320_000_230, data: { turn: 1 } },
    ]),
  ])
  const decoded = decodeSessionArtifact(completed, { sourcePath: 'fixture.jsonl.zstd' })

  assert.equal(decoded.status, 'completed')
  assert.equal(decoded.activities.find(item => item.kind === 'message')?.text, 'Pacote implantado e testes aprovados.')
})

test('redactSensitive masks credential-like fields and bearer tokens', () => {
  const value = redactSensitive({
    password: 'minha-senha',
    nested: { authorization: 'Bearer abcdef', safe: 'visivel' },
  })

  assert.deepEqual(value, {
    password: '[redigido]',
    nested: { authorization: '[redigido]', safe: 'visivel' },
  })
})

test('parseTodoProgress reports checked and pending work with headings', () => {
  const progress = parseTodoProgress(`# Plano\n\n## Fase 1\n- [x] Feito\n- [ ] Agora\n\n## Fase 2\n- [ ] Depois\n`)

  assert.equal(progress.completed, 1)
  assert.equal(progress.total, 3)
  assert.deepEqual(progress.items.map(item => [item.section, item.done, item.text]), [
    ['Fase 1', true, 'Feito'],
    ['Fase 1', false, 'Agora'],
    ['Fase 2', false, 'Depois'],
  ])
})

test('evaluateTaskContract rejects every touched path outside the immutable package', () => {
  const contract = evaluateTaskContract({
    task_id: 'QB-002',
    allowed_paths: ['dsh/builder-policy.mjs', 'test/builder-profile.test.mjs'],
    max_files_changed: 3,
  }, [
    ' M dsh/builder-policy.mjs',
    ' M src/manifest.mjs',
    '?? bin/start-builder.ps1',
  ])

  assert.equal(contract.state, 'violated')
  assert.equal(contract.stopRequired, true)
  assert.deepEqual(contract.touched, [
    'bin/start-builder.ps1',
    'dsh/builder-policy.mjs',
    'src/manifest.mjs',
  ])
  assert.deepEqual(contract.violations, ['bin/start-builder.ps1', 'src/manifest.mjs'])
})

test('parseQwenSlotProgress reports generation counters without response content', () => {
  const progress = parseQwenSlotProgress([{
    id: 0,
    is_processing: true,
    id_task: 175024,
    n_ctx: 524288,
    n_prompt_tokens: 333321,
    next_token: [{ n_decoded: 262, n_remain: 16122 }],
    params: { n_predict: 16384 },
  }])

  assert.deepEqual(progress, {
    active: true,
    slot: 0,
    taskId: 175024,
    contextTokens: 524288,
    promptTokens: 333321,
    decodedTokens: 262,
    remainingTokens: 16122,
    maxOutputTokens: 16384,
  })
  assert.doesNotMatch(JSON.stringify(progress), /content|prompt_text|reasoning/iu)
})

test('stale running sessions become interrupted only after the local model is offline', () => {
  const sessions = [{ status: 'running', updatedAt: 1_000, session: { id: 'session-stale' } }]
  const offline = normalizeSessionLiveness(sessions, { qwen: { state: 'offline' } }, 20_000)
  assert.equal(offline[0].status, 'interrupted')

  const ready = normalizeSessionLiveness(sessions, { qwen: { state: 'ready' } }, 20_000)
  assert.equal(ready[0].status, 'running')

  const recent = normalizeSessionLiveness(sessions, { qwen: { state: 'offline' } }, 10_000)
  assert.equal(recent[0].status, 'running')
})

test('resolveGitExecutable survives a hidden launcher PATH without inventing a failure', () => {
  const configured = resolveGitExecutable({
    env: { PEMARA_GIT_PATH: 'X:\\PortableGit\\git.exe', ProgramFiles: 'C:\\Program Files' },
    fileExists: path => path === 'X:\\PortableGit\\git.exe',
  })
  assert.equal(configured, 'X:\\PortableGit\\git.exe')

  const installed = resolveGitExecutable({
    env: { ProgramFiles: 'C:\\Program Files' },
    fileExists: path => path === 'C:\\Program Files\\Git\\cmd\\git.exe',
  })
  assert.equal(installed, 'C:\\Program Files\\Git\\cmd\\git.exe')

  assert.equal(resolveGitExecutable({ env: {}, fileExists: () => false }), 'git')
})

test('monitor web shell is conversation-first and keeps technical detail collapsed', async () => {
  const root = new URL('../web-monitor/', import.meta.url)
  const [html, css, javascript, favicon] = await Promise.all([
    readFile(new URL('index.html', root), 'utf8'),
    readFile(new URL('styles.css', root), 'utf8'),
    readFile(new URL('app.js', root), 'utf8'),
    readFile(new URL('favicon.svg', root), 'utf8'),
  ])

  assert.match(html, /id="task-form"/)
  assert.match(html, /id="task-input"/)
  assert.match(html, /id="sidebar"/)
  assert.match(html, /class="brand-watermark"/)
  assert.match(html, /id="new-chat"/)
  assert.match(html, /id="chat-list"/)
  assert.match(html, /id="project-list"/)
  assert.match(html, /id="project-dialog"/)
  assert.match(html, /id="provider-dialog"/)
  assert.match(html, /id="conversation-provider"/)
  assert.match(html, /id="run-task"/)
  assert.match(html, /id="attachment-input"[^>]*accept="image\/\*,audio\/\*,video\/\*"/s)
  assert.match(html, /id="attach-files"/)
  assert.match(html, /id="record-audio"/)
  assert.match(html, /id="attachment-tray"/)
  assert.match(html, /id="run-status"/)
  assert.match(html, /id="activity-feed"/)
  assert.match(html, /id="technical-details"/)
  assert.match(html, /class="composer-dock"/)
  assert.match(html, /placeholder="Mensagem para o Pemara"/)
  assert.match(html, /Enter envia/)
  assert.doesNotMatch(html, /class="workspace-grid"/)
  assert.doesNotMatch(html, /class="mobile-nav"/)
  assert.doesNotMatch(html, />Inspetor</)
  assert.doesNotMatch(html, /class="hero"/)
  assert.match(html, /rel="icon" href="\/favicon\.svg"/)
  assert.match(favicon, /<svg/)
  assert.match(css, /\.composer-dock\s*{[^}]*position:\s*fixed/s)
  assert.match(css, /\.activity-user/)
  assert.match(css, /\.starter-prompts/)
  assert.match(css, /\.attachment-tray/)
  assert.match(css, /\.attachment-preview/)
  assert.match(css, /\.sidebar\s*{/)
  assert.match(css, /\.brand-watermark::before/)
  assert.match(css, /#e53935.*#ffb300.*#43a047.*#1e88e5.*#8e24aa/s)
  assert.match(css, /\.chat-item/)
  assert.match(css, /\.project-item/)
  assert.match(css, /\.provider-card/)
  assert.match(css, /@media \(max-width: 720px\)/)
  assert.match(css, /prefers-reduced-motion/)
  assert.match(javascript, /function friendlyToolName\(/)
  assert.match(javascript, /event\.shiftKey/)
  assert.match(javascript, /function resizeTaskInput\(/)
  assert.match(javascript, /new EventSource\('/)
  assert.match(javascript, /fetch\('\/api\/tasks'/)
  assert.match(javascript, /fetch\('\/api\/attachments'/)
  assert.match(javascript, /apiJson\('\/api\/chats'/)
  assert.match(javascript, /apiJson\('\/api\/projects'/)
  assert.match(javascript, /\/api\/providers\//)
  assert.match(javascript, /selectedChatId/)
  assert.match(javascript, /new MediaRecorder\(/)
  assert.match(javascript, /recorder\.addEventListener\('error'/)
  assert.match(javascript, /recorder\.requestData\(\)/)
  assert.match(javascript, /addEventListener\('drop'/)
  assert.match(javascript, /addEventListener\('paste'/)
  assert.match(javascript, /X-Pemara-Request/)
  assert.doesNotMatch(javascript, /\.innerHTML\s*=/)
})

test('monitor server serves a loopback snapshot and static application', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-monitor-test-'))
  const linkedProject = join(root, 'linked-project')
  const sessionDir = join(root, '.runtime', 'dsh-home', 'sessions', '--fixture--', 'session-monitor-test')
  await mkdir(sessionDir, { recursive: true })
  await mkdir(linkedProject, { recursive: true })
  const linkedProjectCanonical = await realpath(linkedProject)
  await writeFile(join(linkedProject, 'README.md'), '# Projeto vinculado\n')
  await mkdir(join(root, 'tasks'), { recursive: true })
  await writeFile(join(sessionDir, 'session.jsonl.zstd'), fixtureArtifact())
  await writeFile(join(root, 'tasks', 'todo.md'), [
    '- [x] Base',
    '- [ ] `[HOST]` Executar QB-001 duas vezes',
    '- [ ] `QB-003 [QWEN]` Preparar a proxima tarefa',
    '',
  ].join('\n'))

  const staticRoot = join(root, 'web-monitor')
  await mkdir(staticRoot, { recursive: true })
  await writeFile(join(staticRoot, 'index.html'), '<!doctype html><title>Pemara Monitor</title>')

  let activeJob
  const submitted = []
  const uploaded = []
  const taskRunner = {
    async snapshot() {
      return activeJob ?? { status: 'idle' }
    },
    async stageAttachment({ stream, filename, mediaType, contentLength }) {
      const chunks = []
      for await (const chunk of stream) chunks.push(chunk)
      const attachment = {
        id: 'att-00000000-0000-4000-8000-000000000001',
        name: filename,
        kind: 'image',
        mediaType,
        bytes: Buffer.concat(chunks).length,
        sha256: 'a'.repeat(64),
      }
      uploaded.push({ attachment, contentLength })
      return attachment
    },
    async discardAttachment() {},
    async start({ task, attachmentIds, workspace, chatId, projectId }) {
      if (activeJob?.status === 'running') {
        const error = new Error('uma tarefa ja esta em execucao')
        error.code = 'TASK_ACTIVE'
        throw error
      }
      submitted.push({ task, attachmentIds, workspace })
      activeJob = { id: 'job-fixture', task, status: 'running', startedAt: Date.now(), chatId, projectId }
      return activeJob
    },
  }
  const server = createMonitorServer({
    projectRoot: root,
    workspaceRoot: root,
    staticRoot,
    probeHealth: false,
    refreshMs: 50,
    taskRunner,
  })
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  t.after(() => server.close())

  const address = server.address()
  assert.notEqual(address, null)
  const base = `http://127.0.0.1:${address.port}`

  const page = await fetch(base)
  assert.equal(page.status, 200)
  assert.match(page.headers.get('content-security-policy'), /img-src 'self' data: blob:/)
  assert.match(page.headers.get('content-security-policy'), /media-src 'self' blob:/)
  assert.match(await page.text(), /Pemara Monitor/)

  const snapshotResponse = await fetch(`${base}/api/snapshot`)
  assert.equal(snapshotResponse.status, 200)
  const snapshot = await snapshotResponse.json()
  assert.equal(snapshot.sessions[0].session.id, 'session-monitor-test')
  assert.equal(snapshot.todo.completed, 1)
  assert.equal(snapshot.todo.total, 3)
  assert.equal(snapshot.contract.taskId, 'QB-003')
  assert.equal(snapshot.contract.state, 'inactive')
  assert.equal(snapshot.contract.stopRequired, false)
  assert.equal(snapshot.control.job.status, 'idle')
  assert.equal(Array.isArray(snapshot.projects), true)
  assert.equal(snapshot.providers.find(item => item.id === 'local-qwen')?.selectable, true)
  assert.equal(snapshot.projects[0].isDefault, true)

  const projectsResponse = await fetch(`${base}/api/projects`)
  assert.equal(projectsResponse.status, 200)
  const projectsBody = await projectsResponse.json()
  assert.equal(projectsBody.projects[0].id, snapshot.projects[0].id)

  const providersResponse = await fetch(`${base}/api/providers`)
  assert.equal(providersResponse.status, 200)
  const providersBody = await providersResponse.json()
  assert.equal(providersBody.providers.find(item => item.id === 'deepseek-api')?.enabled, false)

  const linkedProjectResponse = await fetch(`${base}/api/projects`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': base,
      'X-Pemara-Request': 'project',
    },
    body: JSON.stringify({ path: linkedProject, name: 'Projeto vinculado' }),
  })
  assert.equal(linkedProjectResponse.status, 201)
  const linkedProjectBody = await linkedProjectResponse.json()
  assert.equal(linkedProjectBody.project.name, 'Projeto vinculado')
  assert.equal(linkedProjectBody.project.path, linkedProjectCanonical)

  const chatResponse = await fetch(`${base}/api/chats`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': base,
      'X-Pemara-Request': 'chat',
    },
    body: JSON.stringify({ projectId: linkedProjectBody.project.id }),
  })
  assert.equal(chatResponse.status, 201)
  const chatBody = await chatResponse.json()
  assert.equal(chatBody.chat.projectId, linkedProjectBody.project.id)

  const uploadResponse = await fetch(`${base}/api/attachments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'image/png',
      'Content-Length': '8',
      'Origin': base,
      'X-Pemara-Request': 'attachment',
      'X-Pemara-Filename': encodeURIComponent('foto clínica.png'),
    },
    body: Buffer.from('imagem!!'),
  })
  assert.equal(uploadResponse.status, 201)
  const uploadBody = await uploadResponse.json()
  assert.equal(uploadBody.attachment.name, 'foto clínica.png')
  assert.equal(uploaded[0].attachment.bytes, 8)

  const taskResponse = await fetch(`${base}/api/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': base,
      'X-Pemara-Request': 'task',
    },
    body: JSON.stringify({
      task: 'Conferir e corrigir o harness',
      attachmentIds: [uploadBody.attachment.id],
      chatId: chatBody.chat.id,
      projectId: linkedProjectBody.project.id,
    }),
  })
  assert.equal(taskResponse.status, 202)
  const accepted = await taskResponse.json()
  assert.equal(accepted.job.id, 'job-fixture')
  assert.deepEqual(submitted, [{
    task: 'Conferir e corrigir o harness',
    attachmentIds: [uploadBody.attachment.id],
    workspace: linkedProjectCanonical,
  }])

  const duplicateResponse = await fetch(`${base}/api/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': base,
      'X-Pemara-Request': 'task',
    },
    body: JSON.stringify({ task: 'Executar outra tarefa ao mesmo tempo' }),
  })
  assert.equal(duplicateResponse.status, 409)

  const forgedResponse = await fetch(`${base}/api/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Origin': 'http://attacker.invalid' },
    body: JSON.stringify({ task: 'comando externo' }),
  })
  assert.equal(forgedResponse.status, 403)

  const unknownFieldResponse = await fetch(`${base}/api/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': base,
      'X-Pemara-Request': 'task',
    },
    body: JSON.stringify({ task: 'tarefa', command: 'Remove-Item C:\\\\*' }),
  })
  assert.equal(unknownFieldResponse.status, 400)

  await new Promise(resolve => setTimeout(resolve, 20))
  const cachedSnapshot = await fetch(`${base}/api/snapshot`).then(response => response.json())
  assert.equal(cachedSnapshot.control.job.id, 'job-fixture')

  activeJob = {
    ...activeJob,
    status: 'completed',
    finishedAt: Date.now(),
    stdout: 'PEMARA HARNESS\n\nExecutando tarefa...\nA correção foi concluída.\nTarefa encerrada pelo runtime com codigo 0.',
  }
  await new Promise(resolve => setTimeout(resolve, 260))
  const completedSnapshot = await fetch(`${base}/api/snapshot`).then(response => response.json())
  const completedChat = completedSnapshot.chats.find(chat => chat.id === chatBody.chat.id)
  assert.equal(completedChat.status, 'completed')
  assert.deepEqual(completedChat.messages.map(message => message.role), ['user', 'assistant'])
  assert.equal(completedChat.messages[1].text, 'A correção foi concluída.')

  const rejectedStatus = await new Promise((resolve, reject) => {
    const request = httpGet(`${base}/api/snapshot`, { headers: { Host: 'attacker.invalid' } }, (response) => {
      response.resume()
      response.once('end', () => resolve(response.statusCode))
    })
    request.once('error', reject)
  })
  assert.equal(rejectedStatus, 403)
})
