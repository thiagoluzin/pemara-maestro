import assert from 'node:assert/strict'
import { mkdtemp, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { createProviderStore } from '../src/provider-store.mjs'

test('provider registry is opt-in and never persists or returns credential values', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-provider-store-'))
  const secret = 'deepseek-secret-must-not-leak'
  const store = createProviderStore({ projectRoot: root, env: { DEEPSEEK_API_KEY: secret } })

  const initial = await store.listProviders()
  const deepseek = initial.find(item => item.id === 'deepseek-api')
  assert.equal(deepseek.enabled, false)
  assert.equal(deepseek.credentialConfigured, true)
  assert.equal(JSON.stringify(initial).includes(secret), false)

  const enabled = await store.setEnabled('deepseek-api', true)
  assert.equal(enabled.selectable, true)
  const registry = await readFile(store.registryPath, 'utf8')
  assert.doesNotMatch(registry, new RegExp(secret))
  assert.equal((await store.requireRunnableModel('deepseek-api')).id, 'deepseek-api')
})

test('provider registry refuses unready remote routes and subagents as root models', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-provider-ready-'))
  const store = createProviderStore({ projectRoot: root, env: {} })

  await assert.rejects(() => store.requireRunnableModel('deepseek-api'), /desativado/i)
  await store.setEnabled('deepseek-api', true)
  await assert.rejects(() => store.requireRunnableModel('deepseek-api'), /credencial/i)
  await assert.rejects(() => store.requireRunnableModel('claude-code'), /subagente/i)
})
