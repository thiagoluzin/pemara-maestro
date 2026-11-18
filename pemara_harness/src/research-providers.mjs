import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import { readFileSync } from 'node:fs'

const FIRECRAWL_ENDPOINT = 'https://mcp.firecrawl.dev/v2/mcp'

function unpack(result) {
  if (result.isError) throw new Error('FIRECRAWL_TOOL_ERROR')
  if (result.structuredContent) return result.structuredContent
  for (const block of result.content ?? []) {
    if (block.type === 'text') {
      try { return JSON.parse(block.text) } catch { /* Not structured data. */ }
    }
  }
  throw new Error('FIRECRAWL_INVALID_RESPONSE')
}

async function firecrawl(name, args) {
  const client = new Client({ name: 'pemara-harness-public-research', version: '1.0.0' })
  const transport = new StreamableHTTPClientTransport(new URL(FIRECRAWL_ENDPOINT))
  try {
    await client.connect(transport, { timeout: 20000 })
    return unpack(await client.callTool({ name, arguments: args }, undefined, { timeout: 60000 }))
  } finally { await client.close() }
}

function processKey() {
  const configured = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY
  if (configured) return configured
  const env = readFileSync('C:/Users/admin_remoto/.codex/secrets/gemini.env', 'utf8')
  const value = /^\s*(?:export\s+)?(?:GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*(.+?)\s*$/m.exec(env)?.[1]
  if (!value) throw new Error('GEMINI_KEY_UNAVAILABLE')
  return value.replace(/^["']|["']$/g, '')
}

export function createResearchProviders({ decisionFetch = fetch } = {}) {
  return {
    search: (query, limit, domains) => firecrawl('firecrawl_search', {
      query: `${query} (${domains.map(domain => `site:${domain}`).join(' OR ')})`, limit,
      objective: 'Reunir fontes públicas de documentação para um dossiê de pesquisa do PEMARA; preservar URLs e evidência para verificar afirmações.',
      sources: ['web'],
    }),
    scrape: url => firecrawl('firecrawl_scrape', { url, formats: ['markdown'], onlyMainContent: true }),
    verify: async request => {
      if (request.model !== 'gemini-decision-1') throw new Error('INVALID_DECISION_MODEL')
      const questions = Object.fromEntries(Object.entries(request.questions).map(([id, question]) => [id, {
        ...question, instructions: typeof question.instructions === 'string' ? question.instructions : JSON.stringify(question.instructions),
      }]))
      const response = await decisionFetch('https://generativelanguage.googleapis.com/v1beta/decisions', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': processKey() },
        body: JSON.stringify({ model: request.model, input: JSON.stringify(request.state), questions }),
        signal: AbortSignal.timeout(60000), redirect: 'error',
      })
      if (!response.ok) throw new Error(`DECISION_HTTP_${response.status}`)
      const result = await response.json()
      return { ...result, model: result.model ?? request.model, modelProvenance: result.model ? 'provider_response' : 'requested_model' }
    },
  }
}
