# Fila visual - Pemara Harness Web Cockpit

Status: **cockpit simples com envio de tarefas implantado; aprovacao host-only e dogfood real continuam pendentes**.

## Gate previo

- [ ] `[OWNER]` Aprovar `tasks/ui-plan.md`.
- [ ] `[OWNER]` Aprovar baseline Git/rollback antes de qualquer obra do Qwen.
- [x] `[HOST]` Confirmar que a execucao headless atual terminou ou trabalha em paths sem conflito.
- [ ] `[HOST]` Capturar hashes do perfil `pemara` e estado limpo dos upstreams.

## Fase 0 - Fundacao Web

- [ ] `UI-00 [HOST/QWEN]` Provar perfil isolado sobre `@deepseek-ai/dsh-web-app`.
- [ ] `UI-00 [HOST]` Provar chat, streaming, ferramenta e plugin duravel em browser.
- [ ] `UI-00 [HOST]` Documentar o limite de sessoes headless cross-process.
- [x] `UI-01 [HOST]` Criar corte read-only de loopback, autoridade, redacao e replay.

### Gate A

- [ ] Web oficial e extensivel sem patch no upstream.
- [ ] Perfil `pemara` headless continua funcional e byte-identical.
- [ ] Nenhum servico/Qwen/ComfyUI foi interrompido pelo spike.
- [ ] Catalogo do modelo nao contem aprovacao/promocao host-only.

## Fase 1 - Interface utilizavel

- [ ] `UI-02 [QWEN]` Criar perfil permanente `pemara-web`.
- [x] `UI-02 [HOST]` Criar launcher silencioso, instancia unica e Edge app-mode para o monitor.
- [x] `UI-02 [HOST]` Ligar o envio Web ao launcher seguro por worker separado e persistido.
- [x] `UI-02 [HOST]` Validar deterministicamente espera/execucao sem expor shell ao browser.
- [x] `UI-03 [HOST]` Implementar marca, tema e casca Pemara no monitor independente.
- [x] `UI-03 [HOST]` Implementar estados vazio/loading/offline/reconectando/erro/bloqueado.
- [x] `UI-03 [HOST]` Validar desktop/mobile, controles nomeados e ausencia de overflow horizontal.

### Gate B

- [ ] Tarefa criada pela Web transmite resposta e tool calls sem refresh.
- [ ] Recarregar reconstroi a conversa sem duplicacao.
- [ ] Desktop e celular aprovados visualmente pelo proprietario.
- [x] Console nao e a interface principal.

## Fase 2 - Cockpit duravel

- [x] `UI-04 [HOST]` Expor read model seguro dos dois ledgers.
- [x] `UI-04 [HOST]` Validar redacao, SSE e leitura sem mutacao.
- [x] `UI-05 [HOST]` Implementar inspetor e timeline duravel de sessoes Pemara/Builder.
- [x] `UI-05 [HOST]` Marcar a origem de sessoes e tarefas como `pemara` ou `builder`.
- [x] `UI-06 [HOST]` Implementar barra Qwen/DSH/GPU/ComfyUI somente leitura.
- [x] `UI-06 [HOST]` Provar que falha de sonda nao derruba sessoes/ledger.

### Gate C1

- [x] Objetivo, rodada, checkpoint, proxima acao, lease e efeitos batem com SQLite.
- [x] Offline, ocioso, executando, bloqueado e pendente de verificacao sao distintos.
- [x] Nenhum raciocinio privado ou status inventado e exibido nos testes automatizados.

## Fase 3 - Revisao humana

- [ ] `UI-07 [HOST/QWEN]` Implementar centro de aprovacoes host-only.
- [ ] `UI-07 [HOST]` Testar clique duplicado, aba atrasada e versao divergente.
- [ ] `UI-08 [QWEN]` Implementar diff, arquivos, testes e evidencias read-only.
- [ ] `UI-08 [HOST]` Testar repo sujo, path com espaco, junction e output truncado.

### Gate C2

- [ ] Modelo nao descobre nem chama endpoints de aprovacao.
- [ ] Nenhum `Aprovar tudo` ou promocao automatica existe.
- [ ] Diff preserva e identifica mudancas preexistentes do usuario.
- [ ] `OUTCOME_UNKNOWN` sempre para em decisao humana.

## Fase 4 - Qualidade e promocao

- [ ] `UI-09 [QWEN]` Implementar reconexao por sequencia sem duplicacao.
- [ ] `UI-09 [HOST]` Rodar axe, teclado, zoom 200%, viewports e 1.000 eventos.
- [ ] `UI-10 [HOST/QWEN]` Executar uma tarefa S real inteiramente pelo cockpit.
- [ ] `UI-10 [OWNER]` Revisar conversa, ferramentas, checkpoint, diff e evidencias.
- [ ] `UI-10 [OWNER]` Aprovar ou rejeitar a promocao do novo atalho.

### Gate final

- [ ] Build Web, testes focados, suite completa e manifesto passam.
- [ ] Upstreams continuam limpos.
- [ ] Perfil/launcher headless permanece como rollback.
- [ ] Atalho visual aprovado aponta para versao e hashes exatos.

## Stop imediato

- [ ] Upstream rastreado foi alterado.
- [ ] Porta deixou de ser loopback sem revisao de seguranca.
- [ ] Browser recebeu segredo, SQL bruto ou shell sem contrato.
- [ ] Modelo ganhou ferramenta de aprovacao, reconciliacao ou promocao.
- [ ] Reconexao duplicou evento, prompt, tool call ou acao humana.
- [ ] Launcher tentou encerrar Qwen, ComfyUI ou outro processo nao possuido.
- [ ] Obra colidiu com a execucao headless atual ou com mudanca preexistente do usuario.
