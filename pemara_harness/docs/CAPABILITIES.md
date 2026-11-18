# Capacidades do Pemara Harness

Snapshot validado em 2026-08-23 para o perfil `pemara`, aberto no workspace `E:\Pemara`.

## Cockpit no estilo Codex

O cockpit web local agora tem uma navegação de primeira classe para conversas
e projetos:

- **Nova conversa** cria um chat persistente para consultas independentes;
- busca filtra o histórico sem misturar tarefas de outros chats;
- projetos são descobertos no workspace e também podem ser vinculados por uma
  pasta escolhida pelo operador;
- cada chat guarda `projectId`, `lastTask`, status e título, enquanto cada job
  grava `chatId`, `projectId` e o workspace efetivamente usado;
- a seleção de projeto é limitada ao workspace raiz `E:\Pemara`, com rejeição
  explícita de caminhos externos;
- a barra lateral é fixa no desktop e vira drawer responsivo no celular;
- a linguagem visual segue o Maestro: navy em camadas, laranja/azul para
  estados e ações, e infinito arco-íris de neurodiversidade em marca-d’água;
  a tipografia e o composer seguem o Codex (Inter/SF Mono, raio 16px);
- os registros de navegação ficam separados do ledger de tarefas em
  `.runtime\monitor\projects.json` e `.runtime\monitor\chats.json`.

As rotas locais correspondentes são `GET/POST /api/projects`,
`GET/POST/PATCH /api/chats` e `POST /api/tasks` com `chatId`/`projectId`.
Todas exigem same-origin e o cabeçalho de intenção do cockpit; não existe
exposição para rede externa.

## Agentes

O perfil atual cria um agente raiz headless por tarefa, usando por padrão
`pemara-qwen38/qwen3.8-27b-uncensored-yarn-524k`. Esse agente pode criar e
controlar filhos no mesmo processo por `subagent` e `subagent_fork`, além de
despachar workflows em worker thread. Goal, plan, todo, compaction, checkpoints
de sessão e Ralph (até 64 rodadas por chamada) também estão compostos.

O DSH traz quatro presets oficiais no checkout — `standard`, `code`, `minimal`
e `cordis` — mas o perfil headless Pemara não seleciona um deles. Eles são
modelos disponíveis para uma composição futura, não quatro agentes atualmente
rodando.

O Qwen local é a rota principal. A interface também mantém um registro explícito
por chat para DeepSeek API e Claude Code: DeepSeek é uma rota remota textual
opt-in e só fica selecionável após `DEEPSEEK_API_KEY` estar no ambiente do
monitor; Claude Code aparece como subagente opcional, mas ainda requer instalar
o bundle oficial no perfil isolado e autenticação nativa antes de poder delegar
trabalho. Nenhuma chave é armazenada no navegador, no registro ou no Git.

## Foto, áudio e vídeo

O cockpit aceita até oito anexos por tarefa. Foto vai ao Qwen 3.8 multimodal;
áudio é transcrito pelo Faster-Whisper local em CPU; vídeo tem oito quadros
temporais lidos pelo Qwen e sua faixa de áudio transcrita. O resultado vira um
contexto host-owned marcado como dado não confiável, limitado a 512 KiB e
injetado no prompt somente depois de conferir caminho, tamanho e SHA-256.

O gate real de 2026-08-21 confirmou a imagem vermelha 640×360, transcreveu
“Pemara confirmou a transcrição número 427” em PT e repetiu ambos no MP4 de
5,955 s. O Qwen e o Whisper permaneceram locais; o áudio usou CPU para não
disputar VRAM com o modelo visual.

## Skills

O provedor filesystem do DSH descobre as skills conforme o workspace. Com o
launcher corrigido para `E:\Pemara`, o snapshot contém 300 bundles locais:

- 296 model-facing, descobertos e carregáveis automaticamente;
- 4 somente para invocação explícita do usuário: `hsb-app`, `hsb-flash`,
  `hsb-setup` e `hsb-test`;
- nenhuma contribuição adicional nas outras raízes padrão deste perfil.

A relação nominal está em [SKILLS_INVENTORY.md](SKILLS_INVENTORY.md). O E2E do
runtime real conferiu a presença das 296 entradas model-facing no pedido enviado
ao agente.

## Plugins e bundles ativos

O plugin próprio `@pemara/harness/dsh-plugin` sempre expõe cinco ferramentas
duráveis ao modelo:

- `harness_task_create`;
- `harness_task_get`;
- `harness_task_begin_round`;
- `harness_task_checkpoint`;
- `harness_task_request_completion`.

Quando o host ativa um pacote válido no perfil `pemara-builder-v2`, o mesmo
plugin registra mais três ferramentas e nenhuma outra:

- `builder_file_read` para arquivos exatos do contrato;
- `builder_file_write` para substituição atômica com baseline e orçamento;
- `builder_test_run` para um id de comando Node fixado pelo host.

O plugin `@pemara/harness/dsh-builder-policy`, presente somente nos perfis
Builder, restringe o catálogo e também bloqueia em tempo de despacho qualquer
ferramenta tardia ou escondida.

O perfil também compõe os bundles oficiais `@deepseek-ai/dsh-base` e
`@deepseek-ai/dsh-headless`. Eles fornecem, entre outros componentes:

- agente, sessão JSONL, título de sessão e retry de LLM;
- rota OpenAI-compatible local por `dsh-llm-pi-ai`;
- sandbox `workspace-write`, PowerShell, filesystem, busca local e jobs;
- skills, instruções, goal, plan, todo, compaction e checkpoints;
- subagentes in-process, workflow worker e Ralph;
- ledger Pemara externo com verificação final independente.

O plugin oficial de busca web DeepSeek continua independente da rota de modelo.
Já a rota `pemara-deepseek` está declarada no perfil e usa
`https://api.deepseek.com/v1` apenas quando um chat a seleciona, está ativada e
o processo possui `DEEPSEEK_API_KEY`. A tarefa padrão do Qwen não sai para a
internet.

## Perfis `pemara-builder` e `pemara-builder-v2`

O Builder não reutiliza a autoridade do perfil operacional. Ele possui
`DSH_HOME`, sessões e ledger próprios, incorpora somente as 3–12 skills do
pacote host-owned e opera com `DSH_PERMISSION_MODE=read-only`.

A política aplica duas barreiras:

- `restrict({ allow })` deixa visíveis somente as cinco ferramentas do v1 ou as
  oito ferramentas do v2;
- um guard monotônico recusa qualquer ferramenta fora dessa lista mesmo que
  ela seja registrada depois ou chamada sem aparecer no catálogo.

O E2E capturou a requisição real do DSH e confirmou cinco ferramentas, quatro
skills autorizadas e ausência de PowerShell, editor, web, `run_code` e
subagentes. Uma execução no GGUF real repetiu o fluxo em uma rodada e deixou
`QB-002` em `COMPLETED_PENDING_VERIFY`, sem comando nem alteração de arquivo.

O v1 continua deliberadamente somente leitura e serve como rollback. O v2 é o
“pedreiro” executável: contrato host-owned com arquivos exatos, hashes baseline,
orçamento de mudanças e ids de teste fixos. Escrita usa temporário no mesmo
diretório, fsync e rename; o subprocesso recebe ambiente saneado, sem credenciais,
rede negada pelo preload, workspace sem permissão de escrita, timeout e limite
de saída. Testes podem escrever apenas em um scratch temporário próprio e
endereçado pelo estado; isso preserva caches/arquivos temporários sem abrir a
worktree. Git existe apenas como adaptador host-only para preparar commit/ref
local candidato sem alterar `HEAD`, worktree ou remoto.

O E2E com o DeepSeek Harness real confirmou a superfície de oito ferramentas,
alteração atômica permitida, bloqueio de rede/escrita lateral, teste protegido e
checkpoint obrigatório depois do último efeito. A qualificação com o GGUF Qwen
real e os três shadow runs continuam pendentes porque o modelo foi mantido fora
da GPU nesta entrega.

## Nível Codex ou Claude Code

O harness já oferece a classe de ferramentas esperada de um agente de código:
ler, procurar, editar, executar PowerShell, acompanhar jobs, planejar, delegar,
compactar contexto e manter estado durável. Portanto ele pode executar tarefas
reais de engenharia no workspace.

Isso não torna o Qwen 27B automaticamente equivalente aos modelos frontier do
Codex ou Claude Code em raciocínio, confiabilidade e qualidade de decisão. A
capacidade operacional existe; a equivalência de qualidade não foi demonstrada.

O upstream suporta os provedores opcionais
`@deepseek-ai/dsh-subagent-codex` e
`@deepseek-ai/dsh-subagent-claude-code`, inclusive com ferramentas condicionais
nos presets oficiais. No perfil Pemara, ambos estão **não instalados, não
configurados e não autenticados**. O host possui Claude Code `2.1.237`; o
executável do aplicativo Codex foi localizado, mas sua execução direta recebeu
`Access denied` nesta auditoria. Isso não conta como integração pronta.

Para ligar qualquer um deles depois, o gate correto é: instalar o pacote
opcional no perfil, configurar a linha de agente sem alterar preset oficial,
validar autenticação e permissões, e executar um E2E independente. Nada disso foi
feito nesta entrega.

## Limites atuais

- o supervisor cross-process existe, mas ainda não foi promovido ao ledger
  operacional v1 sem aprovação do proprietário;
- busca web não está operacional sem credencial própria;
- Claude Code ainda não está instalado/autenticado como subagente; Codex também
  continua não conectado como subagente;
- a inferência no GGUF Qwen real continua sujeita ao gate de VRAM e não deve
  desalojar trabalhos GPU existentes;
- somente o host ou o proprietário promove uma tarefa para
  `COMPLETED_VERIFIED`.
- o Builder v2 edita e testa apenas pelo contrato estreito; não possui shell,
  Git bruto, rede ou autopromoção;
- equivalência de qualidade com Codex/Claude Code e qualificação ampla em shadow
  mode ainda não foram demonstradas.
