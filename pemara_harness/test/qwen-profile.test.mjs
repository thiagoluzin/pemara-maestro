import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const profilePatchUrl = new URL(
  '../.runtime/dsh-home/profiles/pemara/cordis.patch.yml',
  import.meta.url,
)
const launcherUrl = new URL('../bin/start-pemara-dsh.ps1', import.meta.url)

test('Pemara profile selects the local Qwen route as its safe default model', async () => {
  const source = await readFile(profilePatchUrl, 'utf8')

  assert.match(
    source,
    /- id: agent-default-model\s+config:\s+provider: !!js process\.env\.PEMARA_MODEL_PROVIDER \|\| 'pemara-qwen38'\s+model: !!js process\.env\.PEMARA_MODEL_ID \|\| 'qwen3\.8-27b-uncensored-yarn-524k'/,
  )
})

test('Pemara profile declares the loopback Qwen endpoint through OpenAI completions', async () => {
  const source = await readFile(profilePatchUrl, 'utf8')

  assert.match(source, /- id: llm-pi-ai\s+config:\s+providers:\s+pemara-qwen38:/)
  assert.match(source, /apiKeyEnv: PEMARA_QWEN_API_KEY/)
  assert.match(source, /api: openai-completions/)
  assert.match(source, /baseURL: http:\/\/127\.0\.0\.1:11436\/v1/)
  assert.match(source, /models:\s+- id: qwen3\.8-27b-uncensored-yarn-524k/)
  assert.match(source, /contextWindow: 524288/)
  assert.match(source, /input: \[text, image\]/)
  assert.match(source, /supportsDeveloperRole: false/)
  assert.match(source, /maxTokensField: max_tokens/)
})

test('Pemara profile exposes DeepSeek only as an opt-in environment-backed route', async () => {
  const source = await readFile(profilePatchUrl, 'utf8')
  const launcher = await readFile(launcherUrl, 'utf8')

  assert.match(source, /pemara-deepseek:/)
  assert.match(source, /apiKeyEnv: DEEPSEEK_API_KEY/)
  assert.match(source, /baseURL: https:\/\/api\.deepseek\.com\/v1/)
  assert.match(source, /- id: deepseek-chat/)
  assert.match(launcher, /\[ValidateSet\('local-qwen', 'deepseek-api'\)\]/)
  assert.match(launcher, /\$env:PEMARA_MODEL_PROVIDER = 'pemara-deepseek'/)
  assert.doesNotMatch(launcher, /DEEPSEEK_API_KEY\s*=\s*['\"][^'\"]+/)
})

test('Pemara profile accepts only host-prepared multimodal evidence', async () => {
  const source = await readFile(profilePatchUrl, 'utf8')
  assert.match(source, /mediaContextPath: !!js process\.env\.PEMARA_MEDIA_CONTEXT_PATH/)
  assert.match(source, /@pemara\/harness\/dsh-task-file-startup/)
})

test('launcher supplies only a local placeholder credential and restores the caller environment', async () => {
  const source = await readFile(launcherUrl, 'utf8')

  assert.match(source, /\$previousQwenApiKey = \$env:PEMARA_QWEN_API_KEY/)
  assert.match(source, /\$env:PEMARA_QWEN_API_KEY = 'llama-local'/)
  assert.match(source, /Remove-Item Env:PEMARA_QWEN_API_KEY/)
})
