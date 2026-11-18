# Fila de execução — Qwen Builder

Status: **fases técnicas 0–3 implementadas; qualificação GGUF, shadow run e
promoções do proprietário continuam pendentes**.

Legenda: `[OWNER]` proprietário, `[HOST]` guardião/verificador, `[QWEN]` executor.

## Fase 0 — Fundação

- [x] `[OWNER]` Aprovar baseline, raiz de worktrees e limites iniciais.
- [x] `[HOST]` Rodar testes/E2E/sintaxe/manifesto e confirmar upstreams limpos.
- [x] `[HOST]` Criar primeiro commit/tag e hash de rollback do ledger.
- [x] `[HOST]` Criar contrato protegido, allowlist e testes imutáveis.

### Gate A

- [x] Existe `HEAD` recuperável (`baseline-0.1.0`) e raiz de worktree aprovada.
- [x] Testes protegidos têm hashes capturados em `evidence/protected-hashes-qwen-builder-v1.json`.
- [x] GPU, fila, processos e endpoint Qwen foram verificados sem `-Force`; o
  Qwen foi descarregado depois por solicitação do proprietário e segue offline.

## Fase 1 — Qualificação

- [x] `QB-001 [QWEN]` Implementar `doctor` read-only em até 5 arquivos/6 rodadas.
- [x] `[HOST]` Validar diff, dry-run, testes protegidos e ambiente inalterado.
- [x] `QB-002 [HOST RECOVERY]` Criar perfil `pemara-builder` fail-closed; a tentativa original do Qwen foi rejeitada por violação de escopo e autopromoção.
- [x] `[HOST]` Capturar E2E e provar catálogo exato, ausência de rede, promoção, serviço, GPU, shell e edição.
- [ ] `[HOST]` Executar `QB-001` duas vezes com GGUF real em worktrees novas.

### Gate B

- [ ] Duas execuções reais entregaram resultado funcional equivalente.
- [ ] Qwen não alterou gates, upstreams, serviços ou caminhos proibidos.
- [ ] `[OWNER]` Aprovou Qwen para tarefas S/M em shadow mode.

## Fase 2 — Supervisor

- [x] `QB-003 [HOST]` Implementar migração transacional v1 → v2 com rollback.
- [x] `QB-004 [HOST]` Implementar journal e exclusão do supervisor.
- [x] `QB-005 [HOST]` Provar a ausência de resume no headless e registrar ADR-001.
- [x] `[HOST]` Adotar tarefa estável + checkpoint + nova sessão por tentativa.
- [x] `QB-006 [HOST]` Implementar `supervise --once`.
- [x] `QB-007 [HOST]` Implementar restart limitado e backoff persistido.
- [x] `[HOST]` Executar gate protegido de kill/restart real.

### Gate C

- [x] Mesmo `task_id` atravessa a queda; nova sessão por tentativa segue ADR-001.
- [x] Checkpoint e próxima ação sobrevivem.
- [x] Nenhum efeito ou checkpoint é duplicado no gate multiprocesso.
- [ ] `[OWNER]` Aprovou o supervisor antes do ledger operacional.

## Fase 3 — Efeitos

- [x] `QB-008 [HOST RECOVERY]` Implementar adaptador filesystem atômico e reconciliável.
- [x] `QB-009 [HOST RECOVERY]` Implementar adaptador Git local sem push/promoção.
- [x] `QB-010 [HOST RECOVERY]` Implementar adaptador de subprocesso com fingerprint.
- [x] `[HOST]` Criar contrato/perfil Builder v2 com exatamente oito ferramentas
  e manter o v1 como rollback somente leitura.
- [x] `[HOST]` Ocultar e negar shell, Git bruto, rede, serviço, GPU e promoção.
- [x] `[HOST]` Executar fault injection, timeout/kill real e E2E pelo DSH real.

### Gate D

- [x] Efeitos críticos são idempotentes ou param em `OUTCOME_UNKNOWN`.
- [x] HTTP, publicação e operações online continuam desabilitados.
- [x] Rollback local foi demonstrado em fixtures; promoção operacional continua bloqueada.

## Fase 4 — Shadow run

- [ ] `[QWEN]` Concluir tarefa real de diagnóstico.
- [ ] `[QWEN]` Concluir correção real acompanhada de teste.
- [ ] `[QWEN]` Concluir documentação derivada do código.
- [ ] `[HOST]` Comparar aderência, rodadas, tokens, falhas e intervenção humana.
- [ ] `[OWNER]` Decidir manter shadow mode, promover limites específicos ou rejeitar.

## Stop imediato

- [ ] Caminho fora do allowlist tocado.
- [ ] Teste protegido ou política alterada.
- [ ] Rede, serviço, GPU, publicação ou credencial solicitada sem autorização.
- [ ] Efeito incerto, processo órfão, lease conflitante ou schema inconsistente.
- [ ] Orçamento de rodadas/restarts esgotado.
