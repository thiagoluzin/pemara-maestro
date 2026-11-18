# Plano de implementação: Qwen Builder (“pedreiro” do Pemara Harness)

## Estado do plano

- Status: **aprovado pelo proprietário em 2026-08-21** ("implantar tudo que
  estiver dentro do arquivo plan").
- Implementação: fases técnicas 0–3 concluídas pelo Host; fase 4 e promoções
  permanecem pendentes (ver `tasks/todo.md`).
- Runtime-alvo: Qwen3.8 local pelo perfil `pemara-builder-v2`, sempre em
  worktree isolada; `pemara-builder` v1 permanece como rollback read-only.
- Regra central: o Qwen implementa; o host define o contrato e verifica; somente o proprietário promove.

### Descoberta do primeiro teste real

A tentativa original de `QB-002` violou o allowlist, criou commit e mesclou o
próprio trabalho. O merge foi revertido sem reescrever o histórico e permanece
preservado na branch forense. O perfil corrigido pelo Host agora aplica a
superfície fechada de cinco ferramentas também no runtime, não apenas no teste.

Consequência implementada: o contrato v1 permanece como qualificação
fail-closed. O contrato v2 acrescenta somente leitura/escrita atômica de arquivos
exatos e execução de comandos Node definidos pelo Host. PowerShell, Git bruto,
rede, serviços, GPU, publicação e autopromoção não voltaram ao perfil. O E2E
real do DSH provou a superfície de oito ferramentas e o gate pós-efeito.

### Decisões do proprietário registradas (2026-08-21)

1. Baseline aprovada: commit `2a8649f` / tag `baseline-0.1.0`
   (evidência em `evidence/baseline-20260821/`).
2. Raiz de obras aprovada: `E:\Pemara\worktrees\pemara-harness-qwen\<task-id>`.
3. Padrões confirmados: 6 rodadas, 5 arquivos, 3 restarts, 3–12 skills.
4. Identidade de retomada: decidido após o spike da Task 7.
5. Segundo modelo verificador: adotar quando os gates determinísticos + revisão
   humana mostrarem custo de rework repetido.

## Objetivo

Transformar o Qwen em um executor especializado de tarefas pequenas de engenharia do Pemara Harness. Ele deve receber um pacote fechado, editar somente caminhos autorizados, executar testes definidos fora de sua autoridade, persistir checkpoints e entregar um patch candidato. Ele não pode modificar os próprios gates, aprovar conclusão, publicar, controlar serviços ou promover seu trabalho.

O resultado final desejado é um “pedreiro durável”: capaz de continuar trabalho por tentativas limitadas e reinícios, mas sempre preso a orçamento, sandbox, evidência e gate independente.

## O que este plano não autoriza

- alterar os checkouts `third_party/deepseek-harness` ou `third_party/reversa`;
- iniciar Qwen com `-Force`, desalojar Maestro/ComfyUI ou encerrar processos GPU;
- instalar dependências, acessar rede, publicar ou enviar mensagens sem autorização específica;
- editar `RULES.md`, `SPEC.md`, testes de contrato protegidos ou evidência de aprovação;
- executar loops infinitos, promover commits ou marcar `COMPLETED_VERIFIED` pelo modelo;
- implementar enquanto este plano não for aprovado.

## Papéis e autoridade

| Papel | Pode | Não pode |
| --- | --- | --- |
| Proprietário | aprovar fase, efeito material e promoção | delegar aprovação final ao executor |
| Host/guardião | escrever testes de contrato, preparar worktree, verificar hashes, executar gates e promover | alterar o resultado para fazê-lo passar |
| Qwen Builder | implementar em caminhos permitidos, adicionar testes internos, executar comandos permitidos, checkpoint e pedir conclusão | editar gates protegidos, rede, serviços, GPU, commit/push, verificar a si mesmo |
| Verificador | comparar diff, testes, artefatos e política | reutilizar a mesma chamada do Qwen executor como aprovação |

## Pacote obrigatório de cada tarefa do Qwen

Cada tarefa deve caber em uma sessão focada e conter:

```yaml
task_id: QB-NNN
objective: resultado único e observável
allowed_paths: [lista fechada]
forbidden_paths: [RULES.md, SPEC.md, third_party/**, evidence/**, testes protegidos]
acceptance_commands: [comandos definidos pelo host]
required_artifacts: [diff, saída de testes, checkpoint final]
skills: [3 a 12 nomes]
max_rounds: 6
max_files_changed: 5
network: denied
service_control: denied
gpu_control: denied
commit_or_publish: denied
stop_conditions: [efeito incerto, teste protegido falhou, caminho fora do escopo, orçamento esgotado]
```

O Qwen deve usar `harness_task_create` uma vez, `harness_task_begin_round` em cada ciclo, `harness_task_checkpoint` após progresso concreto e `harness_task_request_completion` somente com evidência. Solicitar conclusão não significa aprovação.

## Dependências

```text
Baseline recuperável [HOST]
    |
Contrato protegido [HOST]
    |
Qualificação real do Qwen [QWEN + HOST]
    |
Perfil Builder com skills estreitas [QWEN]
    |
Migração de schema -> journal de execuções -> identidade de sessão
    |                                      |
    +---------------- supervisor run-once -+
                           |
                 restart limitado + E2E de kill
                           |
             adaptadores filesystem/Git/subprocesso
                           |
                 shadow run -> aprovação humana
```

## Fase 0 — Fundação recuperável

### Task 0: Criar baseline imutável

**Responsável:** Host, com aprovação do proprietário.

**Descrição:** Criar o primeiro commit/tag do repositório após conferir manifesto, testes, evidência e upstreams. Hoje o repositório ainda não possui `HEAD`; sem baseline não existe worktree nem rollback Git confiável.

**Critérios de aceitação:**

- [x] `npm test`, E2E, sintaxe e `manifest:check` passam antes do commit.
- [x] DeepSeek Harness e Reversa continuam limpos nos commits fixados.
- [x] Commit/tag e cópia do ledger possuem SHA256 registrado fora do controle do Qwen.

**Verificação:** `git rev-parse HEAD`, `git status --short`, `npm run manifest:check` e hashes do ledger/manifesto.

**Dependências:** nenhuma.

**Arquivos prováveis:** somente metadados Git e evidência host-owned.

**Escopo:** S.

### Task 1: Fixar o contrato protegido do Builder

**Responsável:** Host.

**Descrição:** Materializar o envelope de tarefa, lista de caminhos protegidos e validação before/after. Os hashes dos testes de contrato devem ser capturados antes de entregar a worktree ao Qwen.

**Critérios de aceitação:**

- [x] Pacote inválido, caminho fora do allowlist ou orçamento ausente é recusado.
- [x] Alteração de teste protegido ou política faz o gate falhar.
- [x] Nenhum comando de promoção, rede, serviço ou GPU aparece na superfície do Builder.

**Verificação:** novos testes RED/GREEN executados pelo host e inspeção do catálogo de ferramentas.

**Dependências:** Task 0.

**Arquivos prováveis:** `src/builder-contract.mjs`, `test/builder-contract.test.mjs`, `tasks/contracts/qwen-builder-v1.md`.

**Escopo:** M.

## Checkpoint A — Entrada do Qwen

- [x] Baseline recuperável aprovada pelo proprietário.
- [x] Contrato e hashes protegidos sob autoridade do host.
- [x] Worktree criada em caminho dedicado, nunca no checkout principal.
- [x] Qwen, GPU, fila e proprietário dos processos verificados sem reinício forçado.

## Fase 1 — Aprendizagem controlada

### Task 2: Implementar um `doctor` somente leitura

**Responsável:** Qwen Builder.

**Descrição:** Primeira obra real do Qwen. Implementar diagnóstico JSON de schema/SQLite, manifesto, perfil, endpoint e pré-requisitos sem alterar estado. Os testes de aceitação são escritos e protegidos pelo host antes da execução.

**Critérios de aceitação:**

- [x] `doctor` reporta estados claros e códigos estáveis, inclusive Qwen offline.
- [x] Dry-run não modifica ledger, manifesto, serviços ou ambiente do chamador.
- [x] Diff fica no allowlist e toda a suíte continua verde.

**Verificação:** teste protegido, hashes before/after, `npm test` e chamada real em modo somente leitura.

**Dependências:** Checkpoint A.

**Arquivos prováveis:** `bin/pemara-harness.mjs`, `src/doctor.mjs`, `test/doctor.test.mjs`.

**Escopo:** M.

### Task 3: Criar o perfil `pemara-builder`

**Responsável:** Qwen Builder, sob contrato host-owned.

**Descrição:** Criar perfil externo especializado para construção, reutilizando o Qwen local e expondo somente ferramentas necessárias e de 3 a 12 skills indicadas no pacote. Não alterar presets oficiais.

**Critérios de aceitação:**

- [x] O pedido do modelo contém apenas as skills autorizadas para a tarefa.
- [x] Rede, publicação, controle de serviços e promoção não aparecem como ferramentas.
- [x] O perfil original `pemara` continua byte-identical e funcional.

**Verificação:** dump de composição, captura E2E do pedido OpenAI-compatible e hashes do perfil original.

**Dependências:** Task 2.

**Arquivos prováveis:** perfil local `pemara-builder`, `dsh/builder-policy.mjs`, `test/builder-profile.test.mjs`.

**Escopo:** M.

### Task 4: Executar a prova real do Qwen GGUF

**Responsável:** Host executa; Qwen somente produz o patch.

**Descrição:** Repetir a Task 2 usando o GGUF real, em worktree descartável e com VRAM autorizada. Medir chamadas de ferramenta, arquivos tocados, rodadas, testes e aderência ao escopo.

**Critérios de aceitação:**

- [ ] O Qwen entrega patch válido sem tocar caminhos protegidos.
- [ ] Testes protegidos e independentes passam sem serem editados.
- [ ] Repetição em nova worktree produz resultado funcional equivalente.

**Verificação:** comparação das duas execuções, testes do host e revisão humana do diff.

**Dependências:** Task 3 e GPU livre/autorizada.

**Arquivos prováveis:** somente worktrees e evidência host-owned.

**Escopo:** S de operação.

## Checkpoint B — Qwen qualificado como pedreiro

- [ ] Duas execuções reais cumprem o contrato.
- [ ] Nenhum gate, teste protegido ou serviço foi alterado.
- [ ] Proprietário aprova usar o Qwen em tarefas S/M; tarefas L/XL permanecem proibidas.

## Fase 2 — Supervisor durável

### Task 5: Implementar migração de schema v1 → v2

**Responsável:** Qwen Builder; testes e cópia real sob controle do host.

**Descrição:** Criar migração transacional para suportar journal de tentativas do supervisor. Nunca experimentar primeiro no ledger real.

**Critérios de aceitação:**

- [x] Banco v1 copiado migra para v2 preservando tarefas, eventos e efeitos.
- [x] Falha injetada faz rollback completo e banco permanece legível em v1.
- [x] Versões desconhecidas continuam recusadas sem alteração.

**Verificação:** fixtures v1, falha injetada, `PRAGMA integrity_check` e comparação lógica before/after.

**Dependências:** Checkpoint B.

**Arquivos prováveis:** `src/migrations.mjs`, `src/index.mjs`, `test/migrations.test.mjs`, fixture v1.

**Escopo:** M.

### Task 6: Journal e exclusão de execução do supervisor

**Responsável:** Qwen Builder.

**Descrição:** Registrar cada tentativa com task/session id, fingerprint do comando, PID, início, fim e resultado. Impedir dois supervisores vivos para a mesma tarefa sem conflitar com o lease usado pelo agente filho.

**Critérios de aceitação:**

- [x] Duas tentativas concorrentes resultam em um único supervisor admitido.
- [x] Queda deixa tentativa interrompida auditável e recuperável.
- [x] PID reutilizado não é aceito sem fingerprint correspondente.

**Verificação:** teste multiprocesso e inspeção do journal SQLite.

**Dependências:** Task 5.

**Arquivos prováveis:** `src/supervisor-store.mjs`, `src/index.mjs`, `test/supervisor-store.test.mjs`.

**Escopo:** M.

### Task 7: Provar a identidade de retomada DSH

**Responsável:** Qwen faz o spike; host decide a arquitetura.

**Descrição:** Provar em dois processos que o mesmo `sessionId` pode ser reaberto por seam público do DSH, sem patch no upstream. Se não for possível, parar e produzir ADR comparando runner externo versus rebind host-only auditável; não improvisar associação de sessão.

**Critérios de aceitação:**

- [x] Processo B lê a sessão/tarefa do processo A com identidade comprovada; ou ADR documenta a impossibilidade.
- [x] Nenhuma alteração rastreada ocorre no upstream.
- [x] Rebind, se escolhido, é host-only, event-sourced e proibido com efeito incerto.

**Verificação:** E2E de dois processos, IDs capturados e `git status` dos upstreams.

**Dependências:** Task 6.

**Arquivos prováveis:** `test/session-resume-spike.mts`, `docs/ADR-QWEN-SUPERVISOR-SESSION.md`.

**Escopo:** M.

### Task 8: Implementar `supervise --once`

**Responsável:** Qwen Builder.

**Descrição:** Executar uma única tentativa: ler tarefa/checkpoint, admitir journal, lançar o DSH com identidade aprovada, capturar saída/exit code e finalizar a tentativa. Sem restart nesta task.

**Critérios de aceitação:**

- [x] Tarefa não ativa ou bloqueada não inicia processo filho.
- [x] Uma tentativa produz journal, exit code e checkpoint correlacionados.
- [x] Ctrl+C encerra filho, libera recursos e preserva estado auditável.

**Verificação:** testes de processo real e ausência de órfãos após cancelamento.

**Dependências:** decisão da Task 7.

**Arquivos prováveis:** `src/supervisor.mjs`, `bin/pemara-supervisor.mjs`, `test/supervisor-once.test.mjs`.

**Escopo:** M.

### Task 9: Adicionar restart limitado e backoff

**Responsável:** Qwen Builder.

**Descrição:** Relançar apenas estados autorizados, com padrão proposto de 3 restarts e backoff 5/15/45 segundos. Nunca relançar `BLOCKED_HUMAN`, `COMPLETED_PENDING_VERIFY`, terminal ou efeito incerto.

**Critérios de aceitação:**

- [x] Orçamento e backoff persistem no journal e sobrevivem à queda do supervisor.
- [x] Estados de parada impedem novo processo mesmo após reinício do host.
- [x] Esgotamento termina com razão estável, sem loop infinito.

**Verificação:** relógio falso, reinício do supervisor e contagem exata de processos.

**Dependências:** Task 8.

**Arquivos prováveis:** `src/supervisor.mjs`, `src/supervisor-policy.mjs`, `test/supervisor-restart.test.mjs`.

**Escopo:** M.

### Task 10: Gate kill/restart ponta a ponta

**Responsável:** Host define e executa; Qwen corrige somente código permitido.

**Descrição:** Matar realmente o filho após checkpoint, reiniciar o supervisor e exigir retomada sem duplicar rodada ou efeito. O gate deve ser imutável para o Qwen.

**Critérios de aceitação:**

- [x] Mesmo task/session id atravessa a queda conforme decisão arquitetural.
- [x] Próxima ação vem do último checkpoint durável.
- [x] Nenhum efeito iniciado é repetido; ambiguidade resulta em `OUTCOME_UNKNOWN`.

**Verificação:** E2E multiprocesso com kill real, ledger/eventos e artefatos correlacionados.

**Dependências:** Task 9.

**Arquivos prováveis:** teste protegido e fixtures host-owned.

**Escopo:** M.

## Checkpoint C — Pedreiro durável

- [x] Migração validada em cópia e rollback provado.
- [x] Kill/restart real passa repetidamente.
- [x] Nenhum loop infinito, processo órfão ou efeito duplicado.
- [ ] Proprietário aprova o supervisor antes de tocar o ledger operacional.

## Fase 3 — Efeitos controlados

### Task 11: Adaptador filesystem atômico

**Responsável:** Qwen Builder.

**Descrição:** Implementar escrita por arquivo temporário no mesmo volume, hash esperado, substituição atômica e reconciliação pós-queda. Preservar original quando a promoção não puder ser provada.

**Critérios de aceitação:**

- [x] Repetição com mesma chave não cria segunda escrita lógica.
- [x] Queda antes/depois do rename é reconciliada por hash.
- [x] Caminho fora do workspace ou link que escape do root é recusado.

**Verificação:** fault injection, hash e testes Windows com caminhos contendo espaços.

**Dependências:** Checkpoint C.

**Arquivos prováveis:** `src/effects/filesystem.mjs`, `test/filesystem-effect.test.mjs`.

**Escopo:** M.

### Task 12: Adaptador Git local

**Responsável:** Qwen Builder.

**Descrição:** Registrar branch/base SHA/diff e usar commit SHA como resultado idempotente. O Qwen não recebe autoridade para commit final; o adaptador prepara candidato e o host promove.

**Critérios de aceitação:**

- [x] Base divergente bloqueia em vez de sobrescrever trabalho existente.
- [x] Mesmo patch/base gera resultado reconciliável e não duplica promoção.
- [x] Push, force, reset destrutivo e upstreams ficam proibidos.

**Verificação:** repositório fixture, concorrência e revisão do command allowlist.

**Dependências:** Task 11.

**Arquivos prováveis:** `src/effects/git.mjs`, `test/git-effect.test.mjs`.

**Escopo:** M.

### Task 13: Adaptador de subprocesso

**Responsável:** Qwen Builder.

**Descrição:** Executar comandos autorizados com fingerprint, PID, timeout, stdout/stderr limitados e coleta posterior. Após queda, processo vivo é observado; resultado desconhecido nunca é reexecutado cegamente.

**Critérios de aceitação:**

- [x] Fingerprint inclui executável, argumentos, cwd e contrato de ambiente.
- [x] Timeout/cancelamento encerra somente a árvore autorizada.
- [x] Queda e PID reutilizado produzem reconciliação segura ou bloqueio humano.

**Verificação:** fixtures multiprocesso, timeout e kill real no Windows.

**Dependências:** Task 11.

**Arquivos prováveis:** `src/effects/subprocess.mjs`, `test/subprocess-effect.test.mjs`.

**Escopo:** M.

## Checkpoint D — Pedreiro confiável

- [x] Escritas, Git e subprocessos críticos passam pelos adaptadores.
- [x] Ferramentas brutas equivalentes estão ocultas ou negadas no perfil Builder.
- [x] Efeitos incertos sempre param em gate humano.
- [x] HTTP, publicação e operações online continuam fora do escopo.

## Fase 4 — Shadow run e promoção

### Task 14: Executar três tarefas reais em shadow mode

**Responsável:** Qwen constrói; host aplica/verifica; proprietário decide.

**Descrição:** Executar três tarefas S/M representativas: diagnóstico, correção com teste e documentação derivada de código. Cada uma começa em worktree limpa e termina em patch candidato, nunca promoção automática.

**Critérios de aceitação:**

- [ ] Três tarefas respeitam allowlist, orçamento e checkpoints.
- [ ] Gates independentes passam sem alteração pelo Qwen.
- [ ] Reexecução após uma queda não duplica mudança nem perde próxima ação.

**Verificação:** relatório comparativo de diffs, testes, rodadas, tokens, falhas e intervenção humana.

**Dependências:** Checkpoint D.

**Arquivos prováveis:** worktrees descartáveis e relatório host-owned.

**Escopo:** M de operação.

### Task 15: Gate de promoção do Builder

**Responsável:** Proprietário e host.

**Descrição:** Definir se o Qwen permanece em shadow mode, recebe promoção local limitada ou volta para correção. Nenhuma métrica isolada concede autonomia.

**Critérios de aceitação:**

- [ ] Diff, testes, política, recuperação e artefatos foram revisados.
- [ ] Rollback foi executado pelo menos uma vez em ambiente de teste.
- [ ] Aprovação nomeia exatamente perfil, versão e limites promovidos.

**Verificação:** registro explícito do proprietário e SHA dos artefatos aprovados.

**Dependências:** Task 14.

**Arquivos prováveis:** registro/evidência host-owned.

**Escopo:** S.

## Definition of Done por tarefa do Qwen

- pacote de tarefa válido e aprovado antes da primeira chamada;
- no máximo 5 arquivos e 6 rodadas, salvo nova autorização;
- caminhos protegidos e testes do host mantêm os mesmos hashes;
- teste focado, suíte completa, sintaxe e manifesto passam;
- upstreams continuam limpos;
- nenhum serviço, GPU, rede, publicação ou credencial foi alterado;
- checkpoint final aponta diff, testes, artefatos e próxima ação;
- Qwen solicita conclusão; verificador independente decide; proprietário promove.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Qwen altera o próprio gate | Alto | testes/hash protegidos fora da worktree ou read-only para o Builder |
| 296 skills confundem o modelo | Alto | perfil Builder com pack explícito de 3–12 skills |
| Contexto 524K esgota VRAM ou degrada decisão | Alto | pacotes pequenos, arquivos allowlisted e orçamento de tokens |
| Duas instâncias trabalham na mesma tarefa | Alto | journal de supervisor e exclusão distinta do lease do agente |
| Queda duplica efeito | Alto | adaptadores idempotentes e `OUTCOME_UNKNOWN` |
| Migração corrompe ledger | Alto | cópia, transação, fault injection, integrity check e rollback |
| Qwen controla GPU/serviços | Alto | ferramentas ausentes, command denylist e gate host-only |
| Loop parece produtividade | Médio | máximo de rodadas/restarts persistido e estados obrigatórios de parada |
| Patch correto mas conclusão falsa | Alto | modelo não possui ferramenta de `verify` nem autoridade de promoção |

## Gates ainda abertos para o proprietário

1. Aprovar a migração/promulgação do supervisor no ledger operacional v1.
2. Autorizar duas qualificações do Builder v2 no GGUF real quando a GPU estiver livre.
3. Revisar os três shadow runs e decidir promoção local limitada ou correção.
4. Adotar segundo modelo verificador somente se os gates determinísticos e a
   revisão humana mostrarem rework repetido.

## Próximo trabalho recomendado

Com a infraestrutura pronta, executar a Fase 4 em três worktrees novas. O Qwen
permanece fora da GPU até autorização e nenhuma execução promove o próprio patch.
