import type { Context } from '../../../third_party/deepseek-harness/vendor/cordis/src/index.ts'
import {
  CallId,
  LlmAdapter,
  ReasoningEffortId,
  type GenerateOptions,
  type LlmResolvedModelInfo,
  type StreamChunk,
} from '../../../third_party/deepseek-harness/packages/llm/llm/src/index.ts'

const OFF = ReasoningEffortId('off')

function taskId(): string {
  const value = process.env.PEMARA_SMOKE_TASK_ID
  if (value === undefined || value.trim() === '') throw new Error('PEMARA_SMOKE_TASK_ID is required')
  return value.trim()
}

const SCRIPT = [
  () => ({
    name: 'harness_task_create',
    args: { task_id: taskId(), objective: 'Provar o perfil Pemara ponta a ponta', max_rounds: 8 },
  }),
  () => ({ name: 'harness_task_get', args: { task_id: taskId() } }),
  () => ({
    name: 'harness_task_begin_round',
    args: { task_id: taskId(), provider: 'pemara-mock', model: 'pemara-mock' },
  }),
  () => ({
    name: 'harness_task_checkpoint',
    args: {
      task_id: taskId(),
      summary: 'Perfil, agente e ferramentas duraveis executaram no runtime real.',
      next_action: 'Submeter a evidencia ao verificador independente.',
      artifacts: ['dsh-profile-smoke'],
    },
  }),
  () => ({
    name: 'harness_task_request_completion',
    args: {
      task_id: taskId(),
      summary: 'Smoke end-to-end concluido.',
      evidence: ['DSH headless executou cinco ferramentas Pemara em sequencia'],
    },
  }),
]

class PemaraLedgerMockAdapter extends LlmAdapter {
  override async resolveModel(provider: string, model: string): Promise<LlmResolvedModelInfo> {
    return {
      provider,
      id: model,
      name: model,
      reasoning: { efforts: [{ id: OFF, name: 'Off' }], defaultEffort: OFF },
    }
  }

  async * stream(options: GenerateOptions): AsyncIterable<StreamChunk> {
    const completedCalls = options.messages.flatMap(message => message.content)
      .filter(block => block.type === 'tool-result').length
    const next = SCRIPT[completedCalls]?.()
    if (next !== undefined) {
      const id = CallId(`pemara-smoke-${completedCalls + 1}`)
      const args = JSON.stringify(next.args)
      yield { type: 'block-start', index: 0, blockType: 'tool-call' }
      yield { type: 'tool-call-delta', index: 0, id, name: next.name, argumentsDelta: args }
      yield { type: 'block-end', index: 0, block: { type: 'tool-call', id, name: next.name, arguments: args } }
      yield { type: 'finish', reason: { kind: 'tool-calls' } }
      return
    }
    const text = `PEMARA_DSH_SMOKE_OK task=${taskId()}`
    yield { type: 'block-start', index: 0, blockType: 'text' }
    yield { type: 'text-delta', index: 0, text }
    yield { type: 'block-end', index: 0, block: { type: 'text', text } }
    yield { type: 'finish', reason: { kind: 'stop' } }
  }
}

export const name = 'pemara-ledger-mock'
export const inject = ['llm']

export function apply(ctx: Context): void {
  ctx.llm.registerAdapter(['pemara-mock'], new PemaraLedgerMockAdapter())
}
