# ADR-002 — Builder v2 usa ferramentas estreitas protegidas

- Status: aceito para shadow mode técnico; promoção operacional pendente
- Data: 2026-08-21
- Decisor: proprietário define limites; Host implementa e verifica

## Contexto

O Builder v1 provou contenção, mas suas cinco ferramentas de ledger não
permitiam editar ou testar. Expor PowerShell, shell, editor genérico ou Git ao
Qwen repetiria a violação observada em `QB-002`: saída do allowlist e
autopromoção. O pedreiro precisa executar trabalho real sem controlar o próprio
gate.

## Decisão

Manter o v1 intacto como rollback e criar `pemara-builder-v2` com exatamente
oito ferramentas. Além das cinco ferramentas duráveis, o modelo recebe:

- `builder_file_read`, limitado a arquivos exatos do pacote;
- `builder_file_write`, atômico, com baseline SHA256 e orçamento de arquivos;
- `builder_test_run`, limitado a ids de comandos Node definidos pelo Host.

O pacote, a identidade da tarefa, os caminhos, os comandos, as skills e os
limites são host-owned. Rede, shell, Git bruto, serviços, GPU, commit/publicação
e `COMPLETED_VERIFIED` permanecem indisponíveis. O checkpoint posterior ao
último efeito continua obrigatório para pedir conclusão.

## Consequências

- O Qwen consegue editar e testar dentro de uma obra pequena e auditável.
- Git local candidato existe como adaptador host-only; não é ferramenta do modelo.
- Um comando permitido herda apenas ambiente saneado, Node permission model,
  bloqueio explícito de rede, timeout, limite de saída e rastreamento de PID.
- Cada comando recebe scratch temporário próprio, com leitura/escrita limitada
  àquele diretório; a worktree permanece somente leitura para o subprocesso.
- Baseline divergente, caminho lateral, comando desconhecido, efeito ambíguo ou
  orçamento excedido falham fechados.
- Qualidade equivalente a Codex/Claude Code não é presumida; exige shadow runs.

## Evidência

Testes unitários, fault injection e o E2E com o DeepSeek Harness real provaram
a superfície exata de oito ferramentas, escrita atômica, rede e escrita lateral
negadas, scratch temporário permitido, teste bem-sucedido e estado final
`COMPLETED_PENDING_VERIFY`. O GGUF Qwen permaneceu descarregado; sua
qualificação v2 real é um gate posterior do proprietário.

## Rollback

Selecionar `pemara-builder` restaura o perfil v1 somente leitura. Nenhum ledger
operacional é migrado e nenhuma branch/ref candidata é promovida automaticamente.
