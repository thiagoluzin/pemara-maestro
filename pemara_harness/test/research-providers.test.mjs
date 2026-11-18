import test from 'node:test'
import assert from 'node:assert/strict'
import { createResearchProviders } from '../src/research-providers.mjs'

test('Decision adapter uses the official endpoint, converts shared state and never retries', async () => {
  const oldKey = process.env.GEMINI_API_KEY
  process.env.GEMINI_API_KEY = 'unit-test-placeholder'
  let calls = 0
  try {
    const adapter = createResearchProviders({ decisionFetch: async (url, init) => {
      calls++
      assert.equal(url, 'https://generativelanguage.googleapis.com/v1beta/decisions')
      assert.equal(init.method, 'POST')
      const body = JSON.parse(init.body)
      assert.equal(body.input, '"Public fixture"')
      assert.equal(body.model, 'gemini-decision-1')
      assert.equal(init.redirect, 'error')
      return new Response('{"error":"unavailable"}', { status: 503, headers: { 'content-type': 'application/json' } })
    } })
    await assert.rejects(adapter.verify({ model: 'gemini-decision-1', state: 'Public fixture',
      questions: { check: { type: 'choice', instructions: 'Choose a relation.', criteria: { supports: 'Supported', unsupported: 'Unsupported' } } } }))
    assert.equal(calls, 1)
  } finally {
    if (oldKey === undefined) delete process.env.GEMINI_API_KEY; else process.env.GEMINI_API_KEY = oldKey
  }
})
