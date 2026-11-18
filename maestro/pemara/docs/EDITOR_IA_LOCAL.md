# Editor IA local do Maestro

O Editor IA reúne, dentro do Maestro, o fluxo que antes exigia um editor de
vídeo, um serviço de voz e um copiloto separados. Arquivos, projetos,
referências de voz, jobs e exports ficam sob controle do Studio local.

## O que já funciona

- Projetos persistentes com revisão otimista para impedir que uma aba antiga
  sobrescreva alterações recentes.
- Upload de vídeos, imagens e áudios com validação, limite de tamanho e caminhos
  confinados à pasta de cada projeto.
- Timeline com trilhas de vídeo, voz, música, efeitos e textos.
- Corte, ordem, posição, volume, mute, duração e exclusão de clipes.
- Preview dos arquivos e export MP4 por FFmpeg.
- Export seguro em CPU por padrão e NVENC somente quando o usuário escolher.
- Jobs persistentes com porcentagem, estado, cancelamento, erro e download.
- Legendas automáticas pelo Faster Whisper local, em CPU/int8 e sem download.
- Narração privada com a voz pt-BR do Windows como fallback imediato.
- Perfis de voz clonada protegidos por confirmação explícita de consentimento.
- Copiloto local via Ollama com ações estruturadas e allowlist. A proposta pode
  ser revisada antes de ser aplicada.

## Onde os dados ficam

```text
dados/studio/editor_suite/
  projects/       projetos e mídias importadas
  jobs/           estado persistente das tarefas
  voices/         referências de voz normalizadas e consentidas
```

Arquivos temporários usam extensão `.partial` e só viram exports definitivos
depois que o FFmpeg termina com sucesso.

## Modelo do projeto e concorrência

Cada projeto persiste sua própria configuração, biblioteca de assets, timeline,
exports e número de revisão. A timeline aceita cinco trilhas:

- `video`: sequência principal; a posição é definida por `order`.
- `voice`, `music` e `sfx`: áudio posicionado por `timelineStart`.
- `text`: títulos e legendas temporizados.

Toda mutação recebe `expectedRevision`. O Studio só grava quando esse valor é
igual à revisão atual e incrementa a revisão uma única vez por operação. Se duas
abas tentarem editar a mesma versão, a segunda recebe `REVISION_CONFLICT` e deve
recarregar o projeto antes de tentar novamente.

Render, voz e legendas são executados como jobs persistentes. Cada job registra
projeto, revisão de origem, estado, porcentagem, etapa, cancelamento, erro e
resultado. Isso permite mostrar a fila real no Maestro e torna uma interrupção
visível, sem transformar trabalho perdido em sucesso aparente.

## Voz

O modo `Sistema` usa a Microsoft Maria pt-BR e não envia áudio para terceiros.
Ele serve para trabalhar imediatamente, mas não clona timbre.

O modo recomendado para clonagem é o Chatterbox Multilingual V3. A instalação,
os temporários e os caches neurais ficam isolados em
`E:\Pemara\maestro\pemara\ferramentas\chatterbox`, e o Studio detecta
automaticamente o `.venv` local. Também é possível indicar outro ambiente com
`MAESTRO_CHATTERBOX_PYTHON`. O cadastro de perfil exige consentimento e
normaliza até 30 segundos da referência em WAV mono.

Instalação:

```powershell
powershell -ExecutionPolicy Bypass -File `
  E:\Pemara\maestro\pemara\ferramentas\chatterbox\INSTALAR_CHATTERBOX.ps1
```

O instalador interrompe antes de baixar dependências quando não há espaço livre
seguro. Quando a máquina já possui uma pilha CUDA validada, o ambiente neural a
reutiliza em vez de manter uma segunda cópia CPU do Torch. Isso evita deixar o
Studio ou os modelos Wan sem espaço de trabalho.

### ElevenLabs cloud opcional

ElevenLabs nao e um motor local: exige credencial do servidor e fica desligado por
padrao. Quando habilitado explicitamente, `eleven_v3` recebe direcoes expressivas
com allowlist; `eleven_multilingual_v2` e `eleven_flash_v2_5` recebem o contrato
estavel/preview sem tags incompativeis. A credencial nunca vai para o navegador,
e o backend nunca grava texto ou chave dentro do projeto.

A resposta cloud e normalizada para o mesmo WAV PCM 48 kHz/estereo usado pelo
Chatterbox. Por isso o asset pode seguir para a mesma timeline, render e handoff
CapCut Local, com provenance segura e sem dependencia do provider no editor local.

## Copiloto local

O Studio consulta apenas o Ollama em loopback. A instalação isolada usada pelo
Maestro fica em `C:\PemaraAI\ollama` e escuta em `127.0.0.1:11435`; o Radar
monitora essa porta e religa o processo quando necessário. O modelo padrão é
`qwen3.5:4b`. A resposta precisa obedecer a um schema e somente as ações
editoriais conhecidas são aceitas; comandos de sistema, caminhos e URLs
inventados são descartados.

O nome operacional `qwen3.5:4b` usa a variante instruct sem raciocínio longo. A
variante original permanece disponível como `qwen3.5:4b-thinking`, caso seja
necessária para outro trabalho; o Editor não apaga nem sobrescreve os pesos
originais.

O fluxo normal é deliberadamente dividido em duas chamadas:

1. `POST /projects/{projectId}/assistant` gera uma proposta estruturada para
   revisão humana, sem alterar o projeto.
2. `POST /projects/{projectId}/assistant/apply` recebe exatamente as ações
   revisadas e as aplica atomicamente: ou todas entram em uma única nova revisão,
   ou nenhuma alteração é persistida.

As ações aceitas são renomear projeto, cortar, mover, ajustar volume ou excluir
clipe e adicionar texto. O backend valida novamente a allowlist, os `clipId` e os
limites antes do `apply`; o frontend não é considerado uma fronteira de
segurança.

Variáveis:

```dotenv
OLLAMA_HOST=http://127.0.0.1:11435
MAESTRO_EDITOR_LLM_MODEL=qwen3.5:4b
```

Para reparar ou reproduzir a instalação isolada sem depender da instalação
global do Windows, use primeiro o modo de simulação:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  E:\Pemara\maestro\pemara\ferramentas\ollama\INSTALAR_OLLAMA_MAESTRO.ps1 `
  -DryRun
```

O mesmo comando, sem `-DryRun`, baixa somente o instalador oficial, valida a
assinatura da Ollama Inc., preserva o cache de modelos e reaproveita o
`Pemara_Radar`. Os detalhes operacionais ficam em
`ferramentas\ollama\README.md`.

O pedido usa saída estruturada, `temperature=0`, `think=false`, contexto
limitado e teto de resposta. O modelo permanece carregado por apenas 90 segundos
depois do uso, evitando reservar VRAM indefinidamente enquanto os takes usam a
GPU.

## Legendas automáticas

O Editor pode transcrever um arquivo com áudio ou o mix completo da timeline.
Ele usa o modelo Faster Whisper `base` já existente na máquina, fixado em
`device=cpu`, `compute_type=int8` e `local_files_only=true`. Os segmentos entram
como clipes temporizados na trilha de texto. Se o projeto mudar enquanto a
transcrição roda, a proteção de revisão impede qualquer gravação parcial.

## Segurança operacional

- Rotas do editor usam a mesma validação de acesso interno do Studio.
- IDs e nomes de arquivos são saneados e não podem escapar da raiz do projeto.
- Clonagem de voz exige declaração de consentimento.
- Render usa CPU por padrão para não disputar a GPU com o Wan.
- Reinícios transformam jobs interrompidos em estado visível; eles não somem.
- O projeto usado pelo render é uma fotografia exata da revisão enviada.

## API

O prefixo é `/api/editor`. As rotas implantadas são:

| Método | Rota | Finalidade |
|---|---|---|
| `GET` | `/capabilities` | Detecta FFmpeg, NVENC, SAPI, Chatterbox, ElevenLabs cloud, Faster Whisper e Ollama. |
| `GET`, `POST` | `/projects` | Lista ou cria projetos persistentes. |
| `GET`, `PATCH` | `/projects/{projectId}` | Lê ou atualiza o projeto. |
| `POST` | `/projects/{projectId}/assets` | Importa até 50 assets validados por requisição. |
| `GET` | `/projects/{projectId}/assets/{assetId}/content` | Exibe ou baixa um asset do projeto. |
| `POST` | `/projects/{projectId}/clips` | Adiciona clipe a uma das cinco trilhas. |
| `PATCH`, `DELETE` | `/projects/{projectId}/clips/{clipId}` | Edita ou remove um clipe com controle de revisão. |
| `POST` | `/projects/{projectId}/renders` | Cria job de preview/export em CPU ou NVENC. |
| `POST` | `/projects/{projectId}/captions` | Cria job de legenda local a partir de asset ou mix do projeto. |
| `POST` | `/projects/{projectId}/voices` | Cria narração por SAPI, Chatterbox ou ElevenLabs cloud e, opcionalmente, adiciona à timeline. |
| `POST` | `/projects/{projectId}/assistant` | Gera preview estruturado das ações do copiloto. |
| `POST` | `/projects/{projectId}/assistant/apply` | Aplica atomicamente a proposta revisada. |
| `GET` | `/jobs` | Lista jobs, opcionalmente filtrados por `projectId`. |
| `GET` | `/jobs/{jobId}` | Consulta estado, etapa e porcentagem. |
| `POST` | `/jobs/{jobId}/cancel` | Solicita cancelamento cooperativo. |
| `GET` | `/projects/{projectId}/exports/{exportId}` | Exibe ou baixa o MP4 concluído. |
| `GET`, `POST` | `/voices` | Lista capacidades/perfis ou cadastra referência consentida. |

## CapCut Local

O handoff para CapCut Local é um ZIP portátil e determinístico, não uma
automação do produto oficial. Ele reutiliza o projeto canônico, os mesmos assets,
clipes de voz, legendas SRT e revisão; o `manifest.json` e o `SHA256SUMS` permitem
que o editor local/LLM importe e valide o pacote sem procurar arquivos fora do
projeto. Os modos `quick` e `editable` estão disponíveis em
`GET /projects/{projectId}/handoffs/capcut-local?mode=...`.

O frontend deve sempre enviar `expectedRevision` nas operações de edição e
recarregar o projeto quando receber `REVISION_CONFLICT`.

## Render

O render usa FFmpeg e parte de uma fotografia da revisão solicitada. `encoder=cpu`
usa H.264 por software e é o padrão seguro quando o Wan está usando a GPU.
`encoder=nvenc` usa `h264_nvenc` somente quando o encoder foi detectado; ausência
de NVENC gera erro explícito em vez de trocar silenciosamente o perfil. O MP4
concluído é registrado no projeto e servido pela rota de exports.

## Validação da implantação em 2026-07-23

- A suíte dirigida do Editor passou com `15/15` testes e o conjunto Editor +
  persistência generativa passou com `23/23`, cobrindo projetos,
  assets, timeline, revisões, jobs, render, SAPI, cancelamento, legendas,
  aplicação atômica do copiloto e confinamento de caminhos.
- O smoke neural do Chatterbox Multilingual V3 gerou WAV real em português na
  RTX 5090.
- O smoke de render gerou e baixou MP4 H.264/AAC por CPU; o encoder NVENC foi
  detectado e permanece disponível como escolha explícita.
- O smoke de legendas executou Faster Whisper real em CPU/int8, com
  `local_files_only=true`, e gravou o clipe de texto em uma única revisão.
- O Ollama e o modelo `qwen3.5:4b` estão instalados e aparecem em
  `/capabilities`. A rota do Studio já aberta respondeu em 9,3 segundos com uma
  ação `rename_project`, e o `assistant/apply` a aplicou atomicamente da revisão
  1 para a 2. A instância isolada também produziu, em 5,4 segundos, as ações
  `rename_project` e `add_text` e aplicou as duas da revisão 6 para a 7.
- O frontend foi medido em Chromium com 320 px: não houve overflow horizontal.
  As abas ARIA mantiveram foco e seleção corretos com as teclas de seta.
