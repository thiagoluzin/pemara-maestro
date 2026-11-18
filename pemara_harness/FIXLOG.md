# FIXLOG

# 2026-11-02 — pesquisa pública integrada ao Harness

- adicionados comandos `research-plan`, `research` e `research-status`, além da exportação `./research`;
- Firecrawl MCP faz pesquisa/coleta com allowlist e orçamento; TypeSafe verifica relações afirmação/fonte num lote, com respostas validadas e sem retries automáticos;
- fontes e recibos preservados com SHA-256, cache/data, consumo e fila explícita de revisão; fontes longas não são truncadas silenciosamente;
- ledger existente registra checkpoints/efeitos; exceções externas não persistem mensagens sensíveis e não são repetidas;
- dependências oficiais fixadas com lockfile, incluído no manifesto; `node_modules` ignorado;
- piloto público executou o fluxo completo, incluindo sustentação, contradição, falta de evidência e citação inexistente; evidência em `.runtime/research/public-pilot-20261102`;
- EDU fica por último; nenhum serviço ativo, motor de geração, projeto de mídia ou dado escolar foi alterado.

# 2026-11-02 — avaliação com critérios fixos

- adicionados `evaluate:freeze` e `evaluate:compare`, inspirados no método Self-evolve, sem dependência de seu runtime;
- congelamento por hash da suíte, configuração, versão do Node e avaliador; referência e logs vinculados ao contrato;
- bloqueio de testes alterados/adicionados, referência adulterada, população diferente, suíte vazia, omissões e regressões;
- recibos locais em `.runtime`, sem merge/publicação automática e com revisão humana mesmo em execução sem regressões;
- correção do marcador `NODE_TEST_CONTEXT` herdado: testes do gate agora executam suítes filhas reais, em vez de aceitar execução suprimida pelo Node;
- instruções, limites e escopo em `docs/fixed-evaluation.md`.

# 2026-08-24 — cockpit: tipografia e shape Codex, paleta Maestro preservada

- fonte de interface trocada para Inter/SF Pro (fallback Segoe UI) e código
  para SF Mono/ui-monospace, alinhando a tipografia ao Codex;
- Inter Variable 4.001 (rsms/inter, wght 100–900 + opsz 14–32) embutido em
  `web-monitor/fonts/InterVariable.woff2` (SHA-256
  `693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3`) com
  `@font-face` local: tipografia garantida offline; monitor serve `.woff2`
  com `font/woff2` (CSP já cobre via `default-src 'self'`);
- composer virou retângulo de raio 16px (antes pílula de 28px);
- paleta de cores mantida no padrão Maestro (navy/laranja/azul + infinito
  arco-íris de neurodiversidade), conforme decisão do operador;
- cache-bust `codex-visual-20260824` aplicado ao HTML; estrutura e
  comportamento inalterados, `test/monitor.test.mjs` continua o guardião.

# 2026-08-23 — roteamento externo opt-in por chat

- criado registro local de provedores sem segredos, exposto apenas em loopback;
- Qwen permanece o padrão multimodal privado; DeepSeek API é texto-only e não
  executa o gate/partida de GPU;
- seleção fica persistida no chat e é validada pelo host antes do worker;
- Claude Code é mostrado como subagente opcional com estados reais de instalação
  e autenticação, sem alegar que já está conectado;
- nenhum endpoint aceita chave, URL arbitrária ou header de API pelo navegador.

# 2026-08-23 — cockpit Codex: conversas e projetos

O monitor deixou de ser somente uma tela de acompanhamento e ganhou uma
camada de navegação compatível com o fluxo Codex/GPT:

- sidebar fixa com **Nova conversa**, busca, histórico e lista de projetos;
- chats persistentes em `.runtime/monitor/chats.json`, com títulos, status,
  último objetivo e associação ao projeto;
- projetos descobertos no workspace e vínculo manual por pasta em
  `.runtime/monitor/projects.json`;
- fronteira de workspace `E:\Pemara` aplicada no servidor e no runner, com
  rejeição de caminhos externos;
- `POST /api/tasks` agora transporta `chatId`/`projectId` e grava o workspace
  selecionado no estado durável;
- drawer móvel responsivo, diálogo de vínculo e seletor de projeto no topo da
  conversa;
- paleta e superfícies alinhadas ao Maestro, com laranja/azul nos estados e
  infinito arco-íris de neurodiversidade como marca-d’água gigante não
  interativa.

Validação: `npm test` inclui o novo `cockpit-store.test.mjs`; smoke real no
Edge confirmou sidebar desktop, nova conversa, diálogo de projeto e drawer
móvel sem erros de console ou overflow. As capturas ficam em
`evidence/codex-sidebar-*-20260823.png`. O Qwen permaneceu descarregado durante
a validação; a interface não inicia modelo ao abrir um chat.

O smoke visual do corte Maestro foi executado em 1440×900 e 390×844: conteúdo
sem overflow, símbolo presente nos dois breakpoints e nenhum erro de console.
As capturas ficam em `evidence/maestro-autism-watermark-*-20260823.png`.

## 2026-08-21 — multimodal completo no cockpit

### Implementação

- foto, áudio e vídeo podem ser selecionados, arrastados ou colados; voz pode
  ser gravada pelo microfone, com prévia removível antes do envio;
- upload é streaming loopback, same-origin, limitado a oito arquivos, 2 GiB por
  arquivo e 4 GiB por tarefa, com ids opacos e SHA-256 durável;
- imagem usa visão do Qwen 3.8, áudio usa Faster-Whisper CPU e vídeo combina
  oito quadros com transcrição da faixa sonora;
- contexto de mídia é host-owned, limitado a 512 KiB e injetado como evidência
  não confiável, nunca como instrução;
- tarefas originadas no cockpit atravessam os processos por arquivo durável,
  sem expor o texto em `argv`;
- CSP foi ajustado somente para prévias locais `blob:` de imagem/mídia.

### Gate real

Imagem, WAV e MP4 fixtures passaram nos runtimes reais Qwen/Whisper. Capturas
desktop 1440×900 e mobile 390×844 ficaram sem erro de console, sem overflow e
com alvos de envio de 44×44. O microfone também foi exercitado no Edge com
MediaRecorder real; erro de gravação agora libera a trilha e restaura o botão.

## 2026-08-21 — interface GPT/Codex

### Correção

- a tela principal agora é uma conversa, sem dashboard de três colunas;
- caixa de mensagem fixa embaixo, Enter envia e Shift+Enter quebra a linha;
- prompts iniciais explicam tarefas comuns sem exigir comandos;
- ferramentas usam nomes humanos e deixam argumentos/resultados em detalhes;
- Qwen, GPU, execução e conteúdo técnico continuam disponíveis de forma
  compacta e recolhida;
- desktop e layout estreito foram registrados em
  `evidence/ui-chat-v2-desktop-20260821.png` e
  `evidence/ui-chat-v2-mobile500-20260821.png`.

### Segurança e rollback

O browser continua loopback-only e a API aceita somente uma tarefa same-origin
por vez. A mudança é apenas de apresentação; worker, ledger, logs, gates de GPU
e launcher persistente não foram removidos.

## 2026-08-21 — Builder v2, adaptadores de efeito e E2E DSH

### Implementação

- criado contrato v2 com arquivos exatos, baseline SHA256, comandos Node fixos
  e superfície de oito ferramentas;
- criado perfil isolado `pemara-builder-v2`; o v1 permanece intacto como
  rollback somente leitura;
- filesystem usa escrita atômica/reconciliação, Git prepara candidato local sem
  mover `HEAD` e subprocesso usa fingerprint, PID, timeout e saída limitada;
- ambiente de subprocesso é saneado, credenciais não são herdadas, rede é
  bloqueada inclusive em HTTP/2, Resolver DNS e bindings internos, e o
  permission model impede escrita lateral;
- cada comando protegido recebe scratch temporário próprio; a suíte provou
  escrita ali e negação simultânea de escrita lateral na worktree;
- caminhos Windows com ADS, nomes de dispositivo, alias de caixa ou final
  ambíguo são recusados; `--no-permission` também é proibido;
- Git ignora variáveis `GIT_*` do chamador, configuração global, hooks,
  assinatura, fsmonitor e prompts interativos;
- reinícios recompõem o hash atual pela cadeia causal de efeitos confirmados;
  efeitos incertos continuam bloqueando e os perfis Builder consomem o rebind
  host-only do supervisor;
- o gate de conclusão exige checkpoint depois do último efeito;
- launcher DSH ganhou fallback mínimo para `uv_os_get_passwd ENOMEM` no Windows,
  ativado somente nessa falha e sem alterar o upstream.

### Gate real

O E2E chamou a CLI TypeScript real do DeepSeek Harness contra um endpoint
OpenAI-compatible local determinístico. O request continha somente as oito
ferramentas autorizadas; escrita, teste e checkpoints foram persistidos, rede e
arquivo lateral foram negados e a tarefa terminou em
`COMPLETED_PENDING_VERIFY`. O Qwen GGUF permaneceu fora da GPU.

### Rollback

Usar `pemara-builder` retorna ao contrato v1. HTTP, publicação, shell, Git bruto,
controle de serviços/GPU e promoção continuam fora da superfície do modelo.

## 2026-08-21 — supervisor durável e kill/restart real

### Implementação

- journal v2 registra job, tentativa, comando, PID, início, heartbeat, saída e
  resultado;
- lock independente admite somente um supervisor por tarefa, inclusive entre
  processos reais;
- `pemara-supervisor` oferece configuração host-only, status, `run --once` e
  ciclo com três restarts e backoffs 5/15/45 s;
- cada tentativa relê objetivo e checkpoint; tarefas bloqueadas, pendentes de
  verificação, terminais ou com efeito incerto não são iniciadas;
- PID sem início e fingerprint correspondentes nunca autoriza retomada.

### Gate real

O teste multiprocesso matou o supervisor e seu filho fixture, esperou o lease
expirar e abriu outro supervisor. O mesmo `task_id` retomou do único checkpoint,
registrou `INTERRUPTED → SUCCEEDED`, não duplicou efeito e não deixou órfão.
Outro teste com dois processos admitiu exatamente um lock.

### Decisão de sessão

O headless fixado sempre usa `agents.create(session-${randomUUID()})` e não
aceita `--resume`. O ADR-001 adota nova sessão DSH por tentativa, correlacionada
pela tarefa Pemara e reidratada pelo checkpoint, sem alterar upstream.

### Rollback

O supervisor é aditivo e pode ser parado sem tocar o launcher direto. O ledger
operacional v1 permanece sem migração automática e depende do gate do dono.

## 2026-08-21 — schema v2 transacional

### Implementação

- novos ledgers nascem em v2 com `supervisor_jobs` e
  `supervisor_attempts`;
- ledgers v1 continuam abrindo sem qualquer migração implícita;
- a migração v1 → v2 exige opt-in do host, preserva tarefas, eventos e efeitos
  e recusa versões desconhecidas sem alteração;
- o `doctor` trata v1 como saudável com aviso de migração disponível.

### TDD e segurança

Fixtures independentes provaram preservação lógica, `integrity_check=ok` e
rollback total após falha injetada entre as duas tabelas. O ledger operacional
não foi migrado; essa promoção continua dependente do gate do proprietário.

## 2026-08-21 — cockpit simples e executor visual persistente

### Correção

- a tela de três colunas e somente leitura foi substituída por um fluxo único:
  escrever a tarefa, executar e acompanhar mensagens/ferramentas/resultados;
- plano, histórico, ledger, arquivos, Git e logs continuam disponíveis, mas
  recolhidos por padrão em `Ver detalhes técnicos`;
- criado `src/task-runner.mjs`: worker Node separado, estado atômico, heartbeat,
  stdout/stderr persistidos e chamada por array de argumentos ao launcher fixo;
- `POST /api/tasks` aceita somente JSON same-origin, header explícito e o campo
  `task`; comandos, executáveis e campos extras são recusados;
- uma segunda tarefa simultânea recebe conflito e sessão antiga sem eventos é
  marcada como interrompida quando o Qwen está offline;
- launcher visual permanece loopback-only, oculto e abre Edge em modo app.

### TDD e validação

1. RED: interface sem compositor, servidor read-only e launcher declarando
   `readOnly=true` falharam no novo contrato.
2. GREEN: testes de API provaram aceitação única, bloqueio concorrente, recusa
   de origem forjada/campo extra e ausência do texto da tarefa na command line.
3. Um worker fake que encerrava imediatamente revelou uma corrida de evento
   `close`; o listener passou a ser registrado antes da primeira escrita.
4. Edge real validou 1440×900 e 390×844 sem overflow, detalhes fechados, botão
   nomeado e zero erro de console, exceção ou requisição HTTP ruim.
5. O endpoint real recusou payload com `command` sem criar job, iniciar Qwen ou
   alterar a GPU; o Qwen permaneceu offline com cerca de 31 GB livres.

### Rollback

O launcher headless e o atalho `Pemara Harness Qwen.lnk` continuam intactos.
Reverter este corte restaura o monitor read-only sem tocar sessões ou ledgers.

## 2026-08-21 — contrato protegido do Builder (plano Qwen Builder, Task 1)

### Implementação

- criado `src/builder-contract.mjs`: validador de pacote fechado do Builder
  (QB-NNN, allowlist, conjunto mínimo de caminhos protegidos, orçamento
  6 rodadas / 5 arquivos, 3–12 skills, controles `denied`, campos fechados);
- criado `scripts/check-protected.mjs`: gate executável do host para captura
  e revalidação de hashes, validação de pacote e inspeção da superfície de
  ferramentas (exit 0/1 com códigos estáveis);
- criado `tasks/contracts/qwen-builder-v1.md`: contrato legível pelo Builder;
- capturados os hashes protegidos em
  `evidence/protected-hashes-qwen-builder-v1.json` (8 arquivos).

### TDD

1. RED: `ERR_MODULE_NOT_FOUND` para `src/builder-contract.mjs` nos 13 testes.
2. GREEN: 13/13 passando; um RED residual na superfície de ferramentas
   (ferramenta proibida não era reportada como inesperada) foi corrigido no
   módulo, não no teste.
3. Ciclo real do gate: captura → verificação verde → tampering →
   `PROTECTED_FILE_CHANGED` com hashes esperado/real → restauração → verde.
4. Gate de pacote rejeita BOM e aceita o pacote `QB-001` completo.

### Rollback

Remover os três arquivos novos, o teste da suíte e a captura de hashes
restaura o estado da baseline; nenhum arquivo anterior foi reescrito, exceto
`package.json` (nova suíte `test:contract`) e `tasks/`.

## 2026-08-21 — baseline recuperável (plano Qwen Builder, Task 0)

### Implementação

- criado o primeiro `HEAD` do repositório (`2a8649f`) com a tag anotada
  `baseline-0.1.0`, permitindo worktrees e rollback Git confiáveis;
- registrado em `evidence/baseline-20260821/`: commit/tag, upstreams fixados
  (deepseek-harness `141eb6f`, reversa `f3c3689`), resultado das verificações
  e cópia do ledger operacional com SHA256
  `C4CE90817C2C3A6AFBE418C715BAF1937A245C99B323FE1DC154AE8FAA5E3196`;
- manifest atualizado para 39 arquivos e `manifest:check` verde.

### Verificação

- `node --check` passa em todos os `.mjs`/`.mts` de `src`, `bin`, `dsh`,
  `scripts` e `test`;
- suítes em memória passam: durable-task-store 8/8, dsh-plugin 1/1,
  qwen-profile 3/3; os arquivos cli, crash-recovery e launcher falham apenas
  pelo `spawn EPERM` documentado do sandbox Windows da sessão (limite
  ambiental, não código);
- smoke manual da CLI (create/status/list) passa contra banco temporário;
- `git status --short` limpo após o commit; upstreams sem alteração rastreada.

### Rollback

`git reset --hard baseline-0.1.0` restaura o estado exato; a cópia do ledger
permite reconstruir o banco mesmo sem Git.

## 2026-08-21 — auto-start seguro do Qwen pelo atalho

### Correção

- o launcher visual agora inicia `Start-Qwen38-Yarn524K.ps1` automaticamente em
  um PowerShell filho oculto quando o endpoint 11436 está offline;
- aguarda o modelo exato ficar disponível antes de aceitar uma tarefa;
- bloqueia a partida enquanto a fila ComfyUI tiver itens ou houver menos de
  12 GB de VRAM livre, verificando novamente sem intervenção manual;
- mantém `-Force` proibido e nunca encerra ou substitui processos GPU existentes;
- usa mutex local para impedir duas janelas de carregarem o mesmo GGUF ao mesmo
  tempo;
- diferencia carga ativa de cache ComfyUI ocioso: exige fila vazia antes e
  depois de cinco amostras de GPU em até 5%, então chama `/free` para descarregar
  somente modelos/cache;
- continua esperando `/v1/models` mesmo depois que o script inicializador
  termina e a porta ainda responde `503 Loading model`;
- preserva stdout/stderr de cada tentativa em `.runtime/launcher/`.

### TDD e validação

1. RED: o contrato ainda declarava `autoStartsModel=false`, não possuía processo
   filho e rejeitava os parâmetros de um launcher Qwen de teste.
2. GREEN: teste de integração local comprovou `offline → processo filho → modelo
   esperado pronto → prompt`, sem tocar na GPU real.
3. Outro teste comprovou que trabalho ativo na fila ComfyUI impede a partida.
4. O dry-run passou a expor admissão, VRAM mínima e estado da fila ComfyUI.
5. Na verificação viva, a carga GPU mudou para cerca de 31 GB usados e 96% de
   utilização; o gate recusou corretamente o GGUF real e nada foi desalojado.
6. RED: com fila vazia e GPU ociosa, o cache ComfyUI retido mantinha o launcher
   em espera indefinida; outro teste reproduziu a corrida `starter exit 0 → 503`.
7. GREEN: cache ocioso foi descarregado sem encerrar o ComfyUI, e a espera
   continuou até o modelo exato aparecer em `/v1/models`.
8. Suíte final: 23/23. Validação real: modelo com `n_ctx=524288` e resposta
   `PEMARA_QWEN_OK`, enquanto ComfyUI permaneceu vivo e com fila vazia.

### Rollback

Reverter somente `bin/Open-PemaraHarness.ps1`, o teste e esta documentação
restaura o fluxo manual. Nenhum upstream ou script do Qwen foi alterado.

## 2026-08-21 — launcher da Área de Trabalho e catálogo do workspace

### Implementação

- criado `bin/Open-PemaraHarness.ps1`, com status do modelo, prompt interativo,
  dry-run e política explícita de não iniciar ou desalojar trabalho GPU;
- criado e validado `C:\Users\admin_remoto\Desktop\Pemara Harness Qwen.lnk`;
- adicionado `-Workspace` ao launcher do motor;
- fixado `process.cwd()` em `E:\Pemara`, ativando sandbox, instruções e skills do
  workspace correto;
- inventariados 300 bundles: 296 model-facing e 4 somente para usuário;
- documentado o estado real dos provedores opcionais Codex e Claude Code.

### TDD e falhas reveladas

1. RED: três testes provaram a ausência do launcher interativo e o cwd incorreto.
2. GREEN inicial: contrato e dry-run passaram no Windows PowerShell 5.1.
3. O primeiro E2E revelou que o binário compilado não encontrava dois artefatos
   Host locais (`dsh-typert-registry` e `dsh-api-gateway`).
4. A entrada TypeScript oficial preservou a resolução de fontes, mas revelou que
   TSX buscava `tsconfig` pelo novo cwd e carregava um Cordis compilado obsoleto.
5. Fixado `TSX_TSCONFIG_PATH` no `tsconfig.json` do upstream, com restauração do
   ambiente ao sair.
6. E2E final: runtime real, cwd `E:\Pemara`, 296 skills model-facing, rota Qwen
   mock local, três ferramentas Pemara, host gate e exit `0`.

### Segurança e rollback

O atalho aponta apenas para o script versionado no projeto. Nenhum serviço foi
reiniciado, nenhuma GPU foi liberada à força e os upstreams não foram editados.
Para desativar a entrada visual, remova somente o arquivo `.lnk`; o ledger e o
projeto permanecem preservados.

## 2026-08-21 — vínculo Qwen3.8 local

### Implementação

- configurada a rota `pemara-qwen38` no `llm-pi-ai` oficial;
- selecionado `qwen3.8-27b-uncensored-yarn-524k` como padrão do perfil Pemara;
- preservados contexto 524K, saída 16K, texto/imagem e `reasoning_content`;
- adicionado placeholder de autenticação somente no processo filho do launcher;
- mantidos endpoint loopback, upstreams e OpenCode sem alteração.

### TDD e integração

1. RED: três testes falharam porque perfil, rota e ambiente Qwen não existiam.
2. GREEN: os três contratos do perfil passaram.
3. O dump do runtime real confirmou `agent-default-model` e `llm-pi-ai` apontando para Qwen.
4. O primeiro E2E revelou que a chamada auxiliar de título também usa o modelo; o mock passou a separar título e agente.
5. O segundo E2E provou o gate do ledger ao recusar conclusão sem checkpoint.
6. E2E final: `create → checkpoint → completion → host verify`, DSH exit `0`.
7. Suíte: 16 testes aprovados.

### Gate de GPU

O endpoint real `127.0.0.1:11436` estava desligado. A RTX 5090 tinha cerca de 5,8–6,2 GB livres, abaixo dos 12 GB exigidos pelo launcher seguro; nenhum processo ou modelo foi descarregado à força. Esse gate histórico foi concluído posteriormente pela validação real registrada no topo deste arquivo.

## 2026-08-21 — núcleo durável inicial

### Contexto

O OpenCode local possuía limites ampliados de iteração e recuperação, mas isso não resolvia o estado perdido entre processos. A arqueologia do DSH confirmou que goals, jobs, workflows e schedules não formam uma fila durável cross-process.

### Implementação

- criado `DurableTaskStore` sobre `node:sqlite`;
- adicionados estados, event log, leases, rodadas, checkpoints e efeitos idempotentes;
- recuperação converte efeito iniciado sem resultado em `OUTCOME_UNKNOWN`;
- conclusão separada em solicitação e verificação;
- criado plugin externo com cinco ferramentas model-facing;
- criado perfil `pemara` e launcher com `DSH_HOME` isolado;
- criada CLI independente.

### TDD

1. RED: `ERR_MODULE_NOT_FOUND` para `src/index.mjs`.
2. GREEN: 6 testes do núcleo.
3. RED: plugin inexistente e `releaseLease` ausente.
4. GREEN: 8 testes.
5. RED: CLI inexistente.
6. GREEN: 10 testes.
7. RED: export `Config` ausente.
8. GREEN: function plugin completo.
9. Gate adicional: morte real de processo filho, total de 11 testes verdes.
10. RED: estado `BLOCKED_HUMAN` sem reconciliação/retomada.
11. GREEN: `resolveEffect`, `resumeTask` e CLI host-only, total final de 13 testes verdes.

### Integração real

- `ToolRuntime` e `SystemPrompt` reais: `{"compatible":true,"tools":5}`;
- `dsh --profile pemara --dump-config`: linha externa composta com sucesso;
- boot `--help`: exit `0`;
- smoke LLM determinístico final: `PEMARA_DSH_SMOKE_OK task=profile-smoke-20260821-final`;
- antes do gate: `COMPLETED_PENDING_VERIFY`;
- depois do gate: `COMPLETED_VERIFIED`, verifier `codex-final-independent-gate`.
- suíte final: 13 testes aprovados, incluindo processo filho encerrado com código 23 e reconciliação host-only.

### Problemas encontrados e correções

- Reversa completa em Windows: `EEXIST` ao tratar `.claude/skills` como diretório; análise instalada apenas para Codex em worktree isolada.
- Corepack no perfil tentou consultar `pnpm/latest`; fixado `packageManager: pnpm@11.7.0` e bootstrap offline.
- `tsx` sob o usuário de sandbox falhou com `uv_os_get_passwd ... ENOMEM`; gates TypeScript executados sob o usuário real.
- loader ESM recusou caminho Windows `E:/...` como protocolo `e:`; overlay de teste passou a usar `file:///E:/...`.
- boot de desenvolvimento não encontrou `lib/typert.host.js`; executado o build host oficial antes do smoke.

### Rollback

O upstream não tem alteração rastreada. Para desativar o projeto, não iniciar `start-pemara-dsh.ps1`; remover o perfil local é suficiente. O banco em `.runtime/dsh-home/pemara/ledger.sqlite` é preservado como evidência e pode ser copiado antes de qualquer limpeza.
