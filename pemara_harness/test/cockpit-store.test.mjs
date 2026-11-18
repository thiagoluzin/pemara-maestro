import assert from 'node:assert/strict'
import { mkdir, mkdtemp, readFile, realpath } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { createCockpitStore } from '../src/cockpit-store.mjs'

test('cockpit store persists projects and chats with a project context', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-cockpit-store-'))
  const project = join(root, 'projeto-um')
  await mkdir(project, { recursive: true })
  const store = createCockpitStore({ projectRoot: root, workspaceRoot: root, now: () => 1_787_500_000_000 })

  const projects = await store.listProjects()
  const canonicalRoot = await realpath(root)
  assert.equal(projects.some(item => item.path === canonicalRoot && item.isDefault), true)

  const linked = await store.registerProject({ path: project, name: 'Projeto Um' })
  assert.match(linked.id, /^project-[0-9a-f]{12}$/u)
  assert.equal(linked.name, 'Projeto Um')

  const chat = await store.createChat({ projectId: linked.id })
  assert.match(chat.id, /^chat-[0-9a-f-]{36}$/u)
  assert.equal(chat.projectId, linked.id)
  assert.equal(chat.title, 'Nova conversa')
  assert.equal(chat.providerId, 'local-qwen')

  const updated = await store.updateChat(chat.id, {
    title: 'Revisão do projeto',
    lastTask: 'Revise os testes',
    jobId: 'job-local',
  })
  assert.equal(updated.title, 'Revisão do projeto')
  assert.equal(updated.lastTask, 'Revise os testes')

  const message = await store.appendChatMessage(chat.id, {
    role: 'assistant',
    text: 'Os testes estão verdes.',
    jobId: 'job-local',
  })
  assert.equal(message.messages[0].role, 'assistant')
  assert.equal((await store.getChat(chat.id)).messages[0].text, 'Os testes estão verdes.')

  const reopened = createCockpitStore({ projectRoot: root, workspaceRoot: root, now: () => 1_787_500_000_100 })
  assert.deepEqual((await reopened.getChat(chat.id)).jobId, 'job-local')
  assert.equal((await reopened.getChat(chat.id)).messages[0].jobId, 'job-local')
  const rawChats = JSON.parse(await readFile(join(root, '.runtime', 'monitor', 'chats.json'), 'utf8'))
  assert.equal(rawChats.version, 1)
})

test('cockpit store refuses project paths outside the workspace and runtime internals', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-cockpit-boundary-'))
  const outside = await mkdtemp(join(tmpdir(), 'pemara-outside-'))
  const store = createCockpitStore({ projectRoot: root, workspaceRoot: root })

  await assert.rejects(() => store.registerProject({ path: outside }), /workspace/i)
  await assert.rejects(() => store.registerProject({ path: join(root, '.runtime') }), /runtime/i)
})
