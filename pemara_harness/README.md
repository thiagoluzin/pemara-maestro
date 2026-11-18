# Pemara Harness

Licença do projeto: [MIT](LICENSE). Avisos e licenças de componentes incluídos
estão em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Primeiro núcleo executável de um harness Pemara para trabalho longo com LLM. Ele usa o DeepSeek Harness como motor componível, mas mantém a continuidade crítica em um ledger SQLite próprio. Assim, sessão, tarefa, lease, checkpoint, efeito externo e aprovação final não dependem de um único processo continuar vivo.

## Estado atual

O corte `0.1.0` já possui:

- núcleo SQLite durável e event-sourced;
- recuperação de lease e queda de processo;
- proteção contra repetição cega de efeitos;
- limite de rodadas persistente;
- gate de conclusão independente;
- plugin externo com cinco ferramentas para DSH;
- perfil headless local e reversível;
- perfil `pemara-builder` isolado e fail-closed;
- perfil `pemara-builder-v2` isolado, com três ferramentas de obra estreitas;
- rota padrão `pemara-qwen38` para o llama-server local em `127.0.0.1:11436`;
- launcher interativo seguro e atalho validado para a Área de Trabalho;
- cockpit visual local e responsivo em `127.0.0.1:3080`, com envio seguro de
  uma tarefa por vez e acompanhamento ao vivo;
- navegação estilo Codex, com nova conversa, busca e histórico persistente;
- projetos vinculáveis dentro de `E:\Pemara`, com cada conversa associada a um
  workspace e tarefas encaminhadas para a pasta selecionada;
- anexos locais de foto, áudio e vídeo, com prévia, arrastar/colar e gravação
  de voz; visão usa o Qwen 3.8 e fala usa Faster-Whisper CPU;
- supervisor host-owned com journal, exclusão cross-process, `--once`,
  três restarts e backoff persistido de 5/15/45 s;
- adaptadores reconciliáveis de filesystem, Git local e subprocesso permitido;
- CLI de operador;
- testes unitários, multiprocesso, kill/restart real e smoke no runtime real.

O supervisor retoma a mesma tarefa Pemara a partir do checkpoint em uma nova
sessão headless DSH. Ele não inventa suporte a `--resume`: o upstream fixado
sempre cria uma sessão aleatória nesse perfil. A decisão e suas consequências
estão no [ADR-001](docs/decisions/ADR-001-checkpoint-rehydrated-supervisor.md).
O supervisor é deliberadamente limitado, não um daemon infinito.

## Testes

```powershell
Set-Location E:\Pemara\pemara_harness
npm test
npm run test:qwen:e2e
npm run test:builder:e2e
```

Gate adicional contra os serviços reais do commit fixado do DeepSeek Harness:

```powershell
npm run test:dsh:compat
```

## Pesquisa pública com fontes

`npm run research:plan -- --spec docs/research-pilot.json` valida uma pesquisa sem rede. `npm run research -- --spec <public-spec.json> --output <pasta-nova>` coleta fontes com Firecrawl, verifica afirmações com Gemini Decision e salva um dossiê com hashes, recibos e fila de revisão no ledger do Harness. [Procedimento e limites](docs/public-research.md). A tarefa fica pendente de revisão independente; não há publicação automática.

## Avaliação com critérios fixos

`npm run evaluate:freeze -- --output .runtime/evaluations/nome-antes` congela a suíte e executa a referência. `npm run evaluate:compare -- --contract <contract.json> --sha <hash>` compara um candidato com os mesmos critérios. O gate preserva logs/hashes, bloqueia critérios alterados e mantém revisão humana mesmo quando todos os testes passam. Procedimento e limites em [docs/fixed-evaluation.md](docs/fixed-evaluation.md).

## Perfil DeepSeek local

O launcher usa `E:\Pemara\pemara_harness\.runtime\dsh-home` como `DSH_HOME`. Ele não altera o home global do DSH e não toca no OpenCode.

## Provedores externos (opt-in)

A tela de conversa permite escolher o provedor por chat. `Qwen local` continua
privado e multimodal. `DeepSeek API` é textual e não sobe o Qwen nem reserva
GPU; para liberá-lo, defina `DEEPSEEK_API_KEY` no ambiente do usuário e reinicie
o monitor, então ative-o na tela. A chave não é gravada pelo Harness nem enviada
pelo navegador. `Claude Code` já aparece como subagente preparado, mas a
instalação do bundle oficial e a autenticação nativa permanecem uma etapa
separada antes de qualquer delegação externa.

```powershell
& E:\Pemara\pemara_harness\bin\start-pemara-dsh.ps1 --dump-config
& E:\Pemara\pemara_harness\bin\start-pemara-dsh.ps1 --help
```

O perfil já seleciona `pemara-qwen38/qwen3.8-27b-uncensored-yarn-524k`, com contexto 524K, entrada texto/imagem e protocolo OpenAI-compatible. O launcher fornece apenas o placeholder local `llama-local` ao processo filho e restaura o ambiente ao sair; nenhuma credencial externa é criada ou copiada.

O launcher técnico do DSH continua sem administrar a GPU. Já o launcher visual
`bin\Open-PemaraHarness.ps1`, usado pelo atalho da Área de Trabalho, inicia o
Qwen automaticamente quando o modelo está offline. Antes da partida ele exige
pelo menos 12 GB de VRAM livre e fila ComfyUI vazia. Quando a fila está vazia,
mas o ComfyUI reteve apenas cache, o launcher exige cinco amostras consecutivas
de GPU em até 5% e revalida a fila antes de chamar a API local `/free`. Isso
descarrega somente modelos/cache ociosos; nenhum prompt, processo ou resultado
é removido. Se houver atividade real, apenas aguarda sem usar `-Force`.

Para iniciar manualmente, o caminho continua disponível:

```powershell
& E:\Pemara\local_ai_qwen\scripts\Start-Qwen38-Yarn524K.ps1
& E:\Pemara\pemara_harness\bin\start-pemara-dsh.ps1 `
  'Crie uma tarefa durável, faça checkpoint e responda com o resultado.'
```

Não use `-Force` para contornar o gate de VRAM: o Qwen só deve entrar quando não houver trabalho GPU a preservar.

## Cockpit visual

O atalho `C:\Users\admin_remoto\Desktop\Pemara Harness Visual.lnk` abre a
interface em modo aplicativo do Edge. O servidor escuta somente em
`127.0.0.1:3080`. A tela segue o fluxo GPT/Codex: conversa no centro, caixa de
mensagem fixa embaixo, Enter para enviar e Shift+Enter para quebrar linha. O
clipe anexa fotos, áudios e vídeos; o microfone grava voz no próprio browser.
Arquivos também podem ser arrastados ou colados. Até oito anexos ficam apenas
na prévia local até o envio.
Eventos técnicos aparecem como linhas curtas e seus argumentos/resultados ficam
recolhidos. Ao enviar uma tarefa, um worker separado e persistido chama o
launcher oficial, que espera fila/VRAM seguras e inicia o Qwen automaticamente
quando necessário. Somente uma tarefa pode ficar ativa por vez.

O cockpit mostra ao vivo:

- sessões operacionais e Builder, chamadas de ferramenta e resultados finais;
- tarefas, rodadas, checkpoints e estados dos dois ledgers;
- progresso de geração do Qwen, fila ComfyUI, repositório e gate do contrato;
- arquivos tocados, testes e violações de allowlist;
- fase do launcher antes de existir uma sessão DSH, inclusive espera segura
  pela GPU, saída final e falha preservada.

### Conversas e projetos

A barra lateral esquerda é a entrada principal, no mesmo modelo mental do
Codex: **Nova conversa** abre um chat independente para perguntas aleatórias,
o campo de busca filtra o histórico e a lista de projetos troca o contexto de
trabalho. O botão **Vincular projeto** aceita uma pasta existente dentro de
`E:\Pemara`; o servidor normaliza o caminho, gera um id estável e recusa
qualquer tentativa de sair desse limite. O seletor no topo de cada conversa
mostra o projeto ativo, e o runner grava `projectId`, `chatId` e o workspace
escolhido no estado durável da tarefa.

O estado da navegação fica em `.runtime\monitor\projects.json` e
`.runtime\monitor\chats.json`, separado do ledger SQLite operacional. Assim,
abrir um chat novo não apaga sessões antigas e a seleção sobrevive ao reload.
No celular, a mesma barra vira um drawer com backdrop e pode ser aberta pelo
ícone no topo.

O cockpit usa agora a linguagem visual do Maestro: fundo azul-marinho com
superfícies em camadas, laranja para ações, azul para foco e o símbolo de
infinito arco-íris de neurodiversidade como marca-d’água gigante, com baixa
opacidade e sem capturar cliques.

Raciocínio intermediário não é publicado. Segredos são redigidos no servidor,
antes de qualquer resposta ao browser. O endpoint de tarefa aceita somente JSON
same-origin com `task` e ids opacos de anexo; cada arquivo entra antes por
streaming loopback, recebe SHA-256 e é copiado para o job durável. Não recebe
executável, argumentos ou shell do browser. A tarefa segue por arquivo durável
e não aparece em `argv` dos processos filhos. Plano, histórico, ledger, Git e logs ficam recolhidos em **Ver detalhes
técnicos**. Para abrir sem criar outra janela:

```powershell
& E:\Pemara\pemara_harness\bin\Open-PemaraMonitor.ps1 -NoBrowser
```

## Perfil Qwen Builder

O Builder possui duas rotas separadas. `pemara-builder` mantém o contrato v1 de
cinco ferramentas duráveis como rollback somente leitura. `pemara-builder-v2`
acrescenta exatamente `builder_file_read`, `builder_file_write` e
`builder_test_run`. Ele pode trabalhar de verdade, mas somente em arquivos
exatos, com hashes baseline e comandos Node previamente definidos pelo host.

O v2 não recebe PowerShell, shell, Git bruto, rede, serviços, GPU, commit,
publicação nem aprovação final. Escritas são atômicas e idempotentes; testes
rodam em subprocesso com ambiente saneado, rede negada, workspace somente
leitura, timeout e limite de saída. O E2E atravessou o DeepSeek Harness real com
as oito ferramentas exatas, alterou um único arquivo permitido, negou rede e
escrita lateral e deixou a tarefa em `COMPLETED_PENDING_VERIFY`.

Preflight do pacote atual:

```powershell
& E:\Pemara\pemara_harness\bin\start-pemara-builder-dsh.ps1 `
  -Workspace E:\Pemara\worktrees\pemara-harness-qwen\QB-002 `
  -Package E:\Pemara\pemara_harness\evidence\packages\QB-002.json `
  -CheckOnly
```

## Atalho da Área de Trabalho

O atalho `C:\Users\admin_remoto\Desktop\Pemara Harness Qwen.lnk` abre
`bin\Open-PemaraHarness.ps1` com workspace `E:\Pemara`. O launcher verifica o
modelo exato, inicia o Qwen em um PowerShell filho quando necessário, espera a
prontidão e então oferece a fila interativa de tarefas. Ele nunca remove
processos GPU. Cache ocioso do ComfyUI pode ser devolvido pela API oficial após
os gates acima; trabalho ativo continua protegido.
Duas janelas simultâneas compartilham um lock local para não carregar o GGUF em
duplicidade.

## CLI do ledger

```powershell
$db = 'E:\Pemara\pemara_harness\.runtime\dsh-home\pemara\ledger.sqlite'

node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db list
node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db status --id TASK_ID
node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db events --id TASK_ID
node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db recover
node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db resolve-effect `
  --effect-id EFFECT_ID --resolver owner --outcome committed `
  --evidence 'operacao remota confirmada' --result-json '{"remoteId":"42"}'
node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db resume `
  --id TASK_ID --resolver owner --reason 'correcao autorizada' --evidence 'gate rejeitado registrado'
node E:\Pemara\pemara_harness\bin\pemara-harness.mjs --db $db verify `
  --id TASK_ID --verifier owner-gate --evidence 'gate executado com sucesso'
```

## Supervisor durável

Em um banco v2 preparado pelo host, configure o comando fixo uma vez e execute
uma tentativa ou o ciclo limitado. `{{PEMARA_TASK}}` recebe objetivo e último
checkpoint; se omitido, o prompt é acrescentado ao final dos argumentos.

```powershell
node E:\Pemara\pemara_harness\bin\pemara-supervisor.mjs --db BANCO_V2 configure `
  --task-id TASK_ID --executable C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe `
  --workspace E:\Pemara --arg -NoProfile --arg -File `
  --arg E:\Pemara\pemara_harness\bin\start-pemara-dsh.ps1 `
  --arg '{{PEMARA_TASK}}'

node E:\Pemara\pemara_harness\bin\pemara-supervisor.mjs --db BANCO_V2 run `
  --task-id TASK_ID --once
node E:\Pemara\pemara_harness\bin\pemara-supervisor.mjs --db BANCO_V2 status `
  --task-id TASK_ID
```

O ledger operacional v1 não é migrado implicitamente. A ativação nele depende
de cópia validada e aprovação do proprietário.

## Ferramentas visíveis ao modelo

No perfil operacional e no Builder v1:

- `harness_task_create`
- `harness_task_get`
- `harness_task_begin_round`
- `harness_task_checkpoint`
- `harness_task_request_completion`

Somente no Builder v2:

- `builder_file_read`
- `builder_file_write`
- `builder_test_run`

Não existe ferramenta model-facing para aprovar conclusão. A promoção para `COMPLETED_VERIFIED` pertence à CLI/host.
Da mesma forma, somente o host pode reconciliar efeitos incertos ou reabrir tarefas bloqueadas.

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Capacidades, agentes e plugins](docs/CAPABILITIES.md)
- [Inventário completo de skills](docs/SKILLS_INVENTORY.md)
- [Análise dos upstreams](docs/UPSTREAM_ANALYSIS.md)
- [Roadmap](docs/ROADMAP.md)
- [ADR-001: retomada por checkpoint](docs/decisions/ADR-001-checkpoint-rehydrated-supervisor.md)
- [ADR-002: Builder v2 com ferramentas estreitas](docs/decisions/ADR-002-builder-v2-protected-tools.md)
- [FIXLOG](FIXLOG.md)
- [Regras](RULES.md)
