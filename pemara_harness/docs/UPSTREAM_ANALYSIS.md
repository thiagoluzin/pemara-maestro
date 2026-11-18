# Análise dos upstreams

## Fontes fixadas

| Projeto | Commit | Licença | Uso |
| --- | --- | --- | --- |
| DeepSeek Harness | `141eb6fef83422698aef7a981029e843e8161534` | MIT | runtime componível e perfil externo |
| Sandeco Reversa | `f3c36892e8aefa44f020f7ad74917089e67ddaa3` | MIT | reconhecimento e arqueologia do código |

Os checkouts em `E:\Pemara\third_party` permanecem sem alterações rastreadas. O projeto Pemara é externo aos dois.

## O que o DeepSeek Harness já resolve bem

- sessão event-sourced append-only;
- flush durável e reparo de turno interrompido;
- sequência contígua e detecção de corrupção;
- compactação por pressão de tokens com retenção de cauda;
- metas persistidas na mesma sessão;
- checkpoints antes de pedido de modelo e efeito de ferramenta;
- perfis e plugins fora da árvore oficial.

## Lacuna que motivou o Pemara Harness

- ativação de goal é intencionalmente process-local;
- o goal driver continua apenas na mesma vida de processo;
- workflows não possuem journal/resume após reinício;
- `jobs-local` perde os jobs quando o processo morre;
- schedules são vinculados à sessão viva;
- o checkpoint do DSH registra intenção, mas não oferece exactly-once genérico para efeitos externos.

Logo, aumentar `maxGoalRounds` ou o número de recuperações não cria continuidade real. É necessário um ledger de trabalho fora do ciclo de vida da sessão.

## Observações da Reversa

A instalação completa da Reversa encontrou `EEXIST` em Windows porque `.claude/skills` no checkout do DSH é um arquivo de compatibilidade, não um diretório. A instalação restrita ao alvo Codex funcionou e produziu o inventário na worktree isolada `E:\Pemara\scratch\pemara-harness-reversa-deepseek`.

O Scout classificou 5.561 arquivos rastreáveis, 1.886 arquivos de teste/fixture e 12 módulos lógicos. A arquitetura sugerida foi híbrida: especificações por feature para domínios e documentos transversais para persistência, segurança e operação.

## Decisão de derivação

Nenhum loop interno do DSH foi modificado. O Pemara Harness usa os seams públicos: profile patch, function plugin, tool registry e system prompt. Isso reduz conflito de atualização e mantém rollback simples: remover a linha do perfil desativa o plugin sem reescrever o upstream.
