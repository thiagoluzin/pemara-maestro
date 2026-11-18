# Resumo Geral — Abertura "RITMOS DA REVOLTA"

## Acesso do Studio - regra vigente desde 2026-07-21

- Endereco publico unico: `https://maestro.pemaratech.com.br/`.
- ComfyUI, Studio, Sprunki, Perplexica e APIs auxiliares nao possuem mais acesso publico direto.
- Os servicos internos escutam somente em `127.0.0.1` e o painel os acessa pelo gateway autenticado.
- Token em URL foi desativado. O acesso e feito pela tela de login e sessao revogavel.
- Referencias abaixo a subdominios diretos ou token de emergencia sao historicas e nao devem ser usadas operacionalmente.

## Atualizacao Maestro NVIDIA - 2026-07-04

- Chave NVIDIA implantada em `E:\Pemara\maestro\pemara\.env` sem expor segredo nos documentos.
- Studio oficial migrado para `127.0.0.1:8029` porque `8027` ficou presa por processo Python protegido.
- O antigo tunel direto do Studio foi removido; o Studio e acessado por `/api/studio` no Maestro.
- Rotas novas validadas local e publicamente:
  - `GET /api/nvidia/status`
  - `GET /api/nvidia/models`
  - `POST /api/nvidia/chat`
- Modelos NVIDIA recomendados:
  - `meta/llama-3.1-8b-instruct`: rapido para prompts, resumos e validacao curta.
  - `nvidia/llama-3.3-nemotron-super-49b-v1.5`: raciocinio, auditoria e planejamento de treino.
  - `meta/llama-3.2-90b-vision-instruct`: analise de imagens e frames sem usar GPU local.
  - Alternativas: `moonshotai/kimi-k2.6`, `minimaxai/minimax-m3`, `meta/llama-3.3-70b-instruct`, `mistralai/mistral-large-3-675b-instruct-2512`.
- Regra operacional: NVIDIA acelera planejamento, prompts, revisao e auditoria; os treinos LoRA, FLUX, Qwen e Wan continuam locais no ComfyUI.

## Regra oficial de videos por takes - 2026-07-04

- Decisao: video profissional no ecossistema Pemara deve ser feito por takes curtos, nao por prompt unico longo.
- Fluxo oficial: `ideia -> roteiro -> take_queue -> imagens-base -> videos curtos -> QC -> montagem -> dataset de treino`.
- Prompt unico longo fica permitido apenas como rascunho conceitual.
- Formula de modelos:
  - imagem-base: `FLUX.1 Krea dev FP8`, `FLUX.1-dev` ou `Qwen Image`;
  - preview/treino: `Wan2.2 TI2V/I2V 5B`;
  - render final pesado: `Wan2.2 A14B GGUF HighNoise + LowNoise`;
  - teste rapido: `LTXV 13B`;
  - montagem: FFmpeg/Maestro.
- Base implantada: `E:\Pemara\maestro\pemara\ferramentas\video_global_engine`.
- Referencia ouro: `E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\pre_parabens_referencia`.

## Regra global de GPU - 2026-06-29

Regra em vigor ate segunda ordem:

- Treinos e rotinas automaticas pesadas que usam GPU ficam bloqueados de `05:00` ate `00:30`.
- Treinos automaticos que usam GPU so podem rodar de `00:31` ate `04:59`.
- Uso rotineiro/manual fica liberado: ComfyUI, Gerador IA do Maestro, cards, videos, edicao e testes sob demanda.
- Guard central para treinos: `E:\Pemara\gpu_window_guard.ps1` e `E:\Pemara\gpu_window_guard.py`.
- Treinos Sprunki e LoRA de video/Ritmos foram ajustados para respeitar essa janela.
- Raspagem de fotos reais da loja nao usa GPU e pode seguir 24h.

## Benchmark de Video Cinematico - 2026-06-29

- Prompt aprovado: cavaleiro cavalgando em campo aberto, castelo no horizonte, estilo fantasia medieval.
- Arquivo gerado analisado: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output\maestro_generative\video_00003__720p30.mp4`.
- Copia de benchmark: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\benchmarks\cavaleiro_campo_aberto_20260629\baseline_video_00003_720p30.mp4`.
- Leitura tecnica: MP4 H.264, `1280x720`, `30fps`, `121 frames`, `4.03s`.
- Acertos: campo aberto convincente, castelo legivel, composicao medieval/fantasia boa.
- Pontos a melhorar: pedido era `20s`; cavalo/cavaleiro precisam manter anatomia e consistencia em sequencias longas.
- Direcao: evoluir video por segmentos coerentes de 4-5s e costurar em MP4 720p/30fps, em vez de tentar 600 frames diretos em 16GB VRAM.

## Objetivo
Gerar video animado de abertura (15 cenas, ~64s) usando ComfyUI + Wan 2.2 TI2V 5B + LoRA para fidelidade pixel art. Pipeline: keyframe → I2V → repixel (nearest-neighbor) → overlay texto/logo → final.

## Arquitetura do Sistema

### ComfyUI Principal
- **Local:** `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\`
- **Python:** `C:\Program Files\Python311\python.exe`
- **Porta:** 8188
- **Modelos instalados:** Flux (1-dev, krea-dev), Wan 2.2 TI2V 5B, Sprunki LoRA, Ritmos Pixel LoRA v1/v2
- **Custom nodes:** AIGODLIKE-Translation, ComfyUI-Manager

### ComfyUI do Kit (legado)
- **Local:** `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\ritmos_animacao_kit\kit\ComfyUI\`
- **Python:** venv (`venv\Scripts\python.exe`)
- **Uso:** geracao via API headless (gerar.py, 2_gerar_tudo.bat)

### Treino LoRA
- **Local:** `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\`
- **Framework:** ai-toolkit
- **Modelo base:** Wan2.2-TI2V-5B-Diffusers
- **Dataset:** keyframes (135 originais → 648 train + 162 val)
- **Cenas:** 15 cenas (05_funbot, 10_raddy, 15_titulo_ritmos → val; resto → train)

## Historico de LoRAs

### v1 — rank 32, 2000 steps, single-frame
- Resultado: Fidelidade baixa, personagens borrados/fuzzy
- Causa: Muito pouco treino, rank baixo
- Checkpoint: `output_ritmos_pixel_v1_backup/` (original, pre-v2)

### v2 — rank 64, 8000 steps, single-frame
- Dataset: 648 train + 162 val (com augmentacoes flip + crop)
- Config: lr 5e-5, grad_accum 2, bf16, cache_text_embeddings
- Resultado: Personagens reconheciveis, mas estilo "rendered" em vez de pixel art
- Checkpoint final: `*_000008000.safetensors` (8k steps)
- Backup: `output_ritmos_pixel_v2_backup/`

### v3 — rank 96, 16000 steps, multi-frame (2 frames)
- Dataset: 390 clips MP4 de 5 frames (512x288 + 768x432)
- Config: lr 3e-5, num_frames: 2, shrink_video_to_frames: true
- Resultado: **DIVERGIU** — from step 1000 as amostras sao ruido total
- Causa provavel: Video dataloader nao carrega clips corretamente, ou rank alto + multi-frame desestabilizou
- Interrompido em 9562/16000 steps

## Pipeline de Geracao

### Scripts em `ritmos_animacao_kit/kit/`
| Script | Funcao |
|--------|--------|
| `gerar.py` | Orquestra 15 cenas via API ComfyUI → coleta MP4s |
| `repixelar.py` | Pos-processamento nearest-neighbor (426x240 → 1280x720) |
| `juntar.py` | Junta 15 cenas em `abertura_animada.mp4` |
| `2_gerar_tudo.bat` | Batch launcher |
| `workflow_wan22_i2v.json` | Workflow ComfyUI (UNETLoader + LoRA + Wan22 I2V + VHS_VideoCombine) |
| `cenas.json` | Config das 15 cenas (prompt, frames, seed) |

### Parametros de Geracao
- Resolucao: 768x432 (geracao) → 426x240 (repixel grid) → 1280x720 (final)
- FPS: 16
- Steps: 30
- CFG: 6.0
- Sampler: euler, scheduler simple
- LoRA trigger: `ritmospx`
- Prompt prefix: `ritmospx style, 16-bit pixel art, classic arcade beat em up cutscene, hard pixel edges...`

### Problemas Conhecidos
1. **VHS_VideoCombine** — node ausente; fallback: SaveImage + ffmpeg image sequence
2. **Texto/logo destruido** — modelo Wan nao preserva texto; re-overlay manual necessario
3. **Estilo pixel art vs rendered** — LoRAs tendem a deslocar estilo para digital painting/rendered; repixel nearest-neighbor é mitigacao mas nao solucao

## Estrutura de Diretorios
```
E:\Pemara\maestro\pemara\ferramentas\
├── ComfyUI\                          # ComfyUI principal (Flux + Wan + Sprunki)
│   └── models\
│       ├── diffusion_models\         # wan2.2_ti2v_5B_fp16, flux modelos
│       ├── vae\                      # ae (flux), wan2.2_vae, wan_2.1_vae
│       ├── text_encoders\            # umt5_xxl_fp8
│       └── loras\                    # ritmos_pixel_v1, v2_8k, sprunki_loras
│
├── ComfyUI\lora_videos\             # Projeto da abertura animada
│   ├── wan_lora_trainer\             # Treino LoRA
│   │   ├── ai-toolkit\              # Framework de treino
│   │   ├── build_dataset_v3.py       # Construtor de dataset (multi-frame)
│   │   ├── config_ritmos_pixel_5b.yaml  # Config atual (v3)
│   │   ├── dataset_v3\              # Dataset multi-frame (390 clips)
│   │   ├── models\                  # Wan2.2-TI2V-5B-Diffusers (base model)
│   │   ├── treino_v3.log            # Log do treino v3
│   │   └── output_ritmos_pixel_v2_backup\  # Backup do LoRA v2
│   │
│   └── ritmos_animacao_kit\kit\     # Pipeline de geracao
│       ├── gerar.py                 # Orquestrador
│       ├── repixelar.py             # Repixelizacao
│       ├── juntar.py                # Juncao final
│       ├── 2_gerar_tudo.bat         # Batch launcher
│       ├── workflow_wan22_i2v.json  # Workflow ComfyUI
│       ├── cenas.json               # Config das cenas
│       ├── keyframes/               # 15 PNGs fonte (1280x720)
│       ├── clips/                   # 15 MP4s exportados
│       ├── animado/                 # Output: 15 MP4s gerados
│       ├── repix/                   # Output: 15 MP4s repixelizados
│       └── abertura_animada.mp4     # Video final (64s, 29MB)
```

## Arquivos de Configuracao Relevantes
- `config_ritmos_pixel_5b.yaml` — config do LoRA trainer (v3)
- `build_dataset_v3.py` — construtor de dataset multi-frame
- `workflow_wan22_i2v.json` — workflow ComfyUI
- `cenas.json` — 15 cenas com prompts/seeds/frames
- `FIXLOG.md` — log de erros e correcoes
- `PLANO_ORQUESTRACAO.md` — plano mestre

## Proximos Passos (v4)
1. Corrigir estilo pixel art: voltar a treino single-frame (num_frames: 1) que funciona
2. Rank 32 (conservador), lr 1e-5, 12k steps
3. Captions ultra-detalhadas com foco em pixel art (hard pixel edges, no anti-aliasing, etc.)
4. Dataset maior: usar keyframes + frames dos clips como imagens individuais
5. Testar LoRA v2 strength 0.3-0.4 no ComfyUI — pode ser suficiente com repixelizacao

## Agendamento Treino
- Dias: Segunda a Sexta
- Horario: 07:00 — 11:30
- Watchdog: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\scripts\watchdog_treino.ps1`
- Log: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\logs\watchdog.log`

## Correcao ComfyUI 8188
- Regra atual: ComfyUI principal deve rodar somente em `http://127.0.0.1:8188`.
- Nunca iniciar ComfyUI com `--listen 0.0.0.0`; isso agora e tratado como falha.
- Validado em 2026-06-25: porta `127.0.0.1:8188`, argv `--listen 127.0.0.1 --port 8188 --cuda-device 0`, fila vazia.
- `MASTER.py`, `radar_monitor.py`, watchdogs do Sprunki e startadores da loja foram ajustados para local-only.
- Leia detalhes em:
  - `E:\Pemara\maestro\pemara\ferramentas\gerador_sprunki\COMFYUI_8188_CORRECAO.md`
  - `E:\Pemara\maestro\pemara\ferramentas\gerador_sprunki\COMFYUI_WATCHDOG.md`
  - `E:\Pemara\maestro\pemara\ferramentas\ECOSSISTEMA_COMFYUI.md`

## Maestro Flux Chat / Studio Generative
- Implementado em 2026-06-26 no Maestro web: nova janela `Gerar IA` (`app/index.html`).
- Backend novo: `E:\Pemara\maestro\pemara\services\studio\main.py`
  - `GET /api/generative/status`
  - `POST /api/generative/chat`
  - `GET /api/generative/comfy-view`
- Porta operacional atual: `8029` desde 2026-07-11.
  - Historico: houve uso temporario de `8015` quando o Studio antigo em `8005` estava preso por processo protegido.
  - Historico adicional: `8025`, `8026` e `8027` ficaram como legado; o Studio atual foi movido para `8029`.
  - O backend atual `8029` roda `services/studio/main.py`, com as novas rotas generativas.
- Tunel Cloudflare atualizado:
  - `api-studio.pemaratech.com.br -> http://host.docker.internal:8029`
  - Arquivo: `E:\Pemara\maestro\.cloudflared\config.yml`
- Modelos expostos:
  - Imagem: `flux1-krea-dev_fp8_scaled.safetensors` padrao, tambem lista `flux1-dev` e `flux1-krea-dev`.
  - Video: `wan2.2_ti2v_5B_fp16.safetensors`, exportando WEBM via `SaveWEBM`.
  - LoRAs listadas automaticamente de `ComfyUI\models\loras`.
- Auto-recuperacao:
  - Watchdog: `E:\Pemara\maestro\pemara\services\studio\watchdog_studio_generative.ps1`
  - Tarefa recorrente: `Pemara Studio Generative Watchdog` a cada 5 minutos.
  - Radar/health devem checar `http://127.0.0.1:8029/api/generative/status` no boot/ciclo.
- Validacoes feitas:
  - Status local e remoto OK.
  - Imagem FLUX gerada: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output\maestro_generative\image_00001_.png`
  - Video WEBM gerado: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output\maestro_generative\video_00001_.webm`
  - Arquivos e jobs devem ser acessados pelo painel Maestro via `/api/studio`; `api-studio.pemaratech.com.br` direto bloqueia rotas sensiveis.

## Auditoria Maestro Pro / Hermes / Ollama - 2026-06-26
- Relatorio completo: `E:\Pemara\maestro\pemara\ferramentas\AUDITORIA_MAESTRO_PRO_20260626.md`
- Ollama reinstalado/validado em `127.0.0.1:11434`.
- Modelos locais antigos aposentados:
  - Gemma/Gemma4 e aliases antigos do Hermes foram removidos do uso principal.
  - Qwen 2.5 continua apenas como reserva/turbo, nao como agente principal.
- Modelo local atual do Hermes/Maestro:
  - Principal agente/desktop: `qwen-pemara-agent`
  - Base: `qwen2.5-pemara-balanced64`, Q4_K_M; Hermes declara 64k para passar na trava interna, Ollama roda quente em 32k para uso leve.
  - Turbo/reserva texto: `qwen2.5-pemara-fast64`
  - Reserva texto/cards: `qwen2.5-pemara-balanced64`
  - Visao auxiliar: `qwen2.5vl:3b-q4_K_M`
- Skill local obrigatoria: `C:\Users\admin_remoto\AppData\Local\hermes\hermes-agent\skills\pemara-local-operator\SKILL.md`.
- Bootstrap operacional inicial: `E:\Pemara\PEMARA_BOOTSTRAP_HERMES.md`.
- Mapa operacional inicial: `E:\Pemara\PEMARA_PROJECT_MAP.md`.
- Entrada recomendada: atalho `Hermes.lnk` em modo leve sem terminal; `Hermes Web.lnk` fica separado para quando precisar da interface no navegador.
- Ajuste de 2026-06-28: `agent.tool_use_enforcement=true`, `clarify` removido do modo leve, regra anti-ferramenta-falsa reforcada e Llama rebaixado por baixa confiabilidade operacional.
- Correcao Hermes CLI 2026-06-28: `platform_toolsets.cli` agora usa lista leve; `read_file` em pasta retorna listagem; `search_files('*.md')` sem target vira busca de arquivos para evitar erro regex.
- Hermes separado em dois modos: `Hermes.lnk` sem terminal para leitura/auditoria; `Hermes Operador GPU.lnk` com terminal para scripts/treinos aprovados. Limites documentados em `E:\Pemara\HERMES_TREINADOR_LIMITES.md`.
- Estabilidade Hermes 2026-06-28: modo normal com 80 turnos, Operador GPU com 120 turnos, `gateway_timeout=3600`, `terminal.timeout=600`, saida de ferramentas reduzida, compressao antecipada e auto-restart dos atalhos CLI para evitar parada sozinha.
- Operador GPU 2026-06-28: atalho enxuto com `file,terminal,skills` e `--ignore-rules`, para nao carregar `AGENTS.md` automatico e melhorar chamadas reais de terminal.
- Status oficial 2026-06-28: `E:\Pemara\HERMES_OPERATOR_STATUS.ps1`; no terminal do Hermes usar `powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:/Pemara/HERMES_OPERATOR_STATUS.ps1 -Summary`.
- Hermes ganhou parser LLM local via Ollama, com confirmacao obrigatoria antes de baixa real de estoque.
- Radar agora monitora e recupera Ollama e Hermes no ciclo principal.
- `MASTER.py` agora evita duplicar servicos quando as portas ja estao ocupadas.
- Conversor teve o bug de `/status` no Windows corrigido no codigo, mas o processo antigo na porta 8003 esta protegido e so troca com PowerShell administrativo ou reboot.
- Hermes Telegram esta pronto, mas o `.env` atual tem token dummy/invalido; trocar por token real para o watchdog subir o bot.

## Marketing Social / Cards Premium ComfyUI - 2026-06-26
- Rodada documentada em `E:\Pemara\marketing_social\RODADA_COMFY_CARDS_20260626.md`.
- Saida publicavel: `E:\Pemara\marketing_social\saida_cards_premium`.
- Manifest atual: 52 produtos com foto real, 50 cards publicaveis.
- Bloqueados por seguranca: produtos 255 e 261, por suspeita de imagem/cadastro incompativel.
- Regra operacional: produto real preservado; ComfyUI/FLUX gera fundo/luz; texto, preco, site e specs ficam deterministicos para evitar alucinacao.
- Nao usar `E:\Pemara\marketing_social\saida_real` para publicacao.
- Rotina antiga de LoRA restaurada: Sprunki diario e comparativos semanais habilitados; video LoRA continua com watchdog ativo.
- Watchdog extra da loja: `Pemara Marketing Fotos Reais Watchdog` a cada 15 minutos, chamando `E:\Pemara\marketing_social\watchdog_loja_fotos_reais.ps1`; tarefa como SYSTEM foi negada pelo Windows, ficou interativa em `admin_remoto`.

## Hermes Estoque / Estagiario do Computador - 2026-06-26
- Documento operacional: `E:\Pemara\maestro\pemara\ferramentas\hermes\HERMES_ESTAGIARIO_LOJA.md`.
- Loja ganhou API interna para o Hermes:
  - `GET /api/v1/produtos`
  - `GET /api/v1/produtos/buscar?q=...`
  - `POST /api/v1/produtos/baixa`
- Deploy Docker da loja feito com rebuild de `pemara-loja`; validado em `http://127.0.0.1:5000`.
- Validacoes: 276 produtos listados, busca `rtx` com 24 resultados, `rtx 5080` encontrado na linha 140.
- Hermes ganhou `pc_tools.py` para status do PC/GPU/servicos, leitura de logs seguros, tarefas agendadas e disparo de watchdogs permitidos com confirmacao.
- Comandos novos no Telegram: `/pc`, `/tarefas`, `/logs`, `/acoes`, `/acao`.
- Parser Ollama atualizado para priorizar baixa de estoque em frases de venda e para reconhecer pedidos de PC/tarefas/acoes locais.
- Guarda de chat adicionada: se `TELEGRAM_CHAT_ID` tiver um ID real, qualquer outro chat e bloqueado antes dos comandos.
- Pendente para operar via Telegram: trocar `TELEGRAM_BOT_TOKEN` dummy e `TELEGRAM_CHAT_ID=0` em `E:\Pemara\maestro\pemara\ferramentas\hermes\.env` por dados reais do BotFather/chat autorizado.

## Qwen Image / Cards e Anuncios - 2026-06-27
- Documento operacional: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\QWEN_IMAGE_PEMARA.md`.
- Instalados no ComfyUI:
  - `models\diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors`
  - `models\diffusion_models\qwen_image_edit_2511_fp8mixed.safetensors`
  - `models\text_encoders\qwen_2.5_vl_7b_fp8_scaled.safetensors`
  - `models\vae\qwen_image_vae.safetensors`
  - `models\loras\Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors`
- Corrigido tokenizer Qwen do ComfyUI com `merges.txt` e `tokenizer.json` em `comfy\text_encoders\qwen25_tokenizer`.
- Instalador atualizado: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\install_qwen_image_models.ps1`.
- Studio atualizado em `services\studio\main.py` para listar Qwen, separar Qwen Edit e gerar workflow Qwen dedicado.
- Porta operacional atual do Studio: `8029`. Desde 2026-07-11 o painel chama `/api/studio` pelo proxy autenticado do Maestro; nao chamar `https://api-studio.pemaratech.com.br` diretamente para geracao.
- ComfyUI antigo protegido em `8188` nao precisou reiniciar; passou a listar Qwen dinamicamente.
- Smoke test: Qwen 512x512 executou e gerou `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output\maestro_generative\image_00002_.png`.
- Decisao de qualidade: Lightning 4 steps funciona, mas errou texto no smoke test; para cards/anuncios usar Qwen sem Lightning como padrao (`40` steps, CFG `4.0`). Lightning fica so para rascunho rapido.

## Maestro Video / Gerador IA - 2026-06-27
- Video ruim analisado em:
  - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output\maestro_generative\video_00002_.webm`
  - Problema tecnico: `768x416`, `16fps`, `2.81s`, `VP9/WebM`; o anterior estava ainda pior em `256x256`, `8fps`.
- Backend atualizado:
  - `E:\Pemara\maestro\pemara\services\studio\main.py`
  - Novo padrao de video no Gerador IA: saida final `MP4`, `1280x720`, `30fps`, H.264.
  - O Comfy ainda renderiza o video bruto via Wan/SaveWEBM, mas o Studio converte automaticamente para MP4 720p com SAR 1:1.
  - Novo endpoint assíncrono com progresso:
    - `POST /api/generative/job`
    - `GET /api/generative/job/{job_id}`
  - Endpoint antigo `POST /api/generative/chat` mantido para compatibilidade.
- Interface atualizada:
  - `E:\Pemara\maestro\pemara\app\index.html`
  - `E:\Pemara\maestro\pemara\app\assets\maestro.js`
  - `E:\Pemara\maestro\pemara\app\assets\maestro.css`
  - Modos: `Imagem`, `Editar foto`, `Video Wan`.
  - Campo `Imagem base` adicionado para foto, edicao e video.
  - Barra de porcentagem adicionada no Gerador IA.
  - Campos avancados de resolucao/steps/fps foram escondidos; o sistema aplica o padrao aceitavel automaticamente.
- Qwen Edit:
  - Modo `Editar foto` usa `qwen_image_edit_2511_fp8mixed.safetensors`.
  - A imagem anexada entra como referencia e latent inicial para preservar o produto.
- Porta operacional validada:
  - `8029`: `http://127.0.0.1:8029/api/generative/status`
  - Remoto direto: `https://api-studio.pemaratech.com.br/api/generative/status` retorna apenas status minimo.
  - Painel remoto: usar `https://maestro.pemaratech.com.br/` e proxy `/api/studio`.
- Configuracoes ajustadas para 8029:
  - `E:\Pemara\maestro\.cloudflared\config.yml`
  - `E:\Pemara\maestro\pemara\services\studio\watchdog_studio_generative.ps1`
  - `E:\Pemara\radar\radar_monitor.py`
  - `E:\Pemara\maestro\pemara\ferramentas\hermes\pc_tools.py`
- Observacao: as portas antigas `8015`, `8025`, `8026` e `8027` sao legado; o Studio atual opera em `8029`.

## Acesso Web Maestro / Login - 2026-06-27
- Endereco correto via internet:
  - `https://maestro.pemaratech.com.br/`
- Nao usar como painel principal:
  - `https://api-studio.pemaratech.com.br/` e apenas API do Studio.
- Cloudflare:
  - `E:\Pemara\maestro\.cloudflared\config.yml`
  - `maestro.pemaratech.com.br -> http://host.docker.internal:9501`
  - `api-studio.pemaratech.com.br -> http://host.docker.internal:8029`
  - `maestro-cloudflared` roda em Docker com restart policy `always` e sem porta Docker publicada.
- Login:
  - `E:\Pemara\maestro\pemara\MASTER.py` agora tem tela `/login`.
  - Credenciais em `E:\Pemara\maestro\pemara\.env`.
  - Variaveis: `MAESTRO_ADMIN_USER`, `MAESTRO_ADMIN_PASSWORD`, `MAESTRO_FRONTEND_TOKEN`, `MAESTRO_FRONTEND_PORT=9501`, `MAESTRO_STUDIO_PORT=8029`.
  - Token por URL ainda funciona como emergencia: `https://maestro.pemaratech.com.br/?token=...`.
- Validado:
  - `https://maestro.pemaratech.com.br/` retorna tela de login.
  - Login local e remoto testados; remoto retornou `302` no login e `200` autenticado.
  - Proxy `/api/studio/api/generative/status` respondeu `200`.
- Seguranca:
  - `.gitignore` criado em `E:\Pemara\maestro\.gitignore` para nao versionar `.env` e credenciais `.cloudflared/*.json`.
  - O painel Maestro tem login de aplicacao.
  - Auditoria/hardening em 2026-07-11: `api-studio.pemaratech.com.br` ainda responde pelo tunel, mas rotas sensiveis do Studio retornam 403 e o status publico nao lista modelos, logs, ComfyUI interno ou caminhos.
  - Para dupla protecao no Cloudflare, habilitar Cloudflare Access/Zero Trust nos hostnames publicos ou remover a exposicao direta das APIs/Comfy.

## Maestro Studio como gerador central - 2026-06-29
- Hermes fica fora do fluxo operacional por enquanto; o Maestro Studio assume a geracao direta.
- Documento novo: `E:\Pemara\maestro\pemara\GERADORES_STUDIO.md`.
- Backend atualizado em `E:\Pemara\maestro\pemara\services\studio\main.py`.
- Frontend atualizado em:
  - `E:\Pemara\maestro\pemara\app\index.html`
  - `E:\Pemara\maestro\pemara\app\assets\maestro.js`
  - `E:\Pemara\maestro\pemara\app\assets\maestro.css`
- Modos atuais do Gerador IA: `Imagem`, `Editar foto`, `Video Wan`, `Musica`, `SFX`.
- Audio generativo:
  - `music`: ElevenLabs Music ou Google Lyria/Vertex.
  - `sfx`: ElevenLabs Sound Effects.
  - Saidas em `E:\Pemara\maestro\pemara\dados\outputs\generative`.
  - Preview de audio no chat do Gerador IA.
- Variaveis adicionadas ao `.env` do Maestro:
  - `ELEVENLABS_API_KEY`
  - `ELEVENLABS_SFX_MODEL_ID`
  - `ELEVENLABS_MUSIC_MODEL_ID`
  - `GOOGLE_CLOUD_PROJECT`
  - `GOOGLE_CLOUD_LOCATION`
  - `LYRIA_MODEL_ID`
  - `GOOGLE_OAUTH_ACCESS_TOKEN`
- Rotas novas/alteradas:
  - `GET /api/generative/status` agora lista `providers.audio`.
  - `POST /api/generative/job` aceita `mode=music` e `mode=sfx`.
  - `GET /api/generative/output` serve musicas/SFX gerados pelo Studio.
- Validacao feita na porta atual:
  - Python compile OK.
  - JavaScript `node --check` OK.
  - `127.0.0.1:8029/api/generative/status` respondeu OK, ComfyUI online, providers `stable_audio`, `lyria`, `eleven_sfx`, `eleven_music`.
- Ativacao publica: `api-studio.pemaratech.com.br` aponta para `8029`, mas desde 2026-07-11 expõe somente status minimo e bloqueia rotas sensiveis. Geracao real deve passar pelo Maestro.

## Modelos novos de video - 2026-06-29
- Hermes foi removido do fluxo operacional; o Maestro Studio assume imagem, video, musica e SFX.
- Custom nodes instalados no ComfyUI:
  - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\custom_nodes\ComfyUI-GGUF`
  - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\custom_nodes\ComfyUI-LTXVideo`
- Backend do Studio atualizado para listar modelos `.gguf` de video em `models\unet` e carregar esses modelos com `UnetLoaderGGUF`.

## Loja / Image Max Stack - 2026-07-06

- Prioridade atual: loja, fotos reais, cards e anuncios fieis. Video continua pausado ate segunda ordem.
- Studio oficial na porta `8029` ganhou modo `Card real loja`.
- Modo `Card real loja` usa Qwen Image Edit com imagem base obrigatoria, 1024x1280, 52 steps e guidance 4.0.
- O backend prepara uma folha de referencia factual para o Qwen, mas essa folha nao e arte final publicavel.
- Card final deve sair como imagem unica do workflow/modelo; compositor HTML/CSS/PIL fica proibido para publicacao.
- Pacote maximo instalado no ComfyUI:
  - `RealESRGAN_x4plus.pth`
  - `RealESRNet_x4plus.pth`
  - `4x-UltraSharp.pth`
  - `4x_NMKD-Superscale-SP_178000_G.pth`
  - `flux-canny-controlnet-v3.safetensors`
  - `flux-depth-controlnet-v3.safetensors`
  - `sigclip_vision_patch14_384.safetensors`
- Custom nodes instalados:
  - `ComfyUI_essentials`
  - `comfyui_controlnet_aux`
  - `comfyui-ipadapter`
  - `x-flux-comfyui`
- Pendente: `flux1-redux-dev.safetensors`, porque o repositorio e gated e exige aceite/licenca + `HF_TOKEN`.
- Novo fluxo em lote:
  - `E:\Pemara\marketing_social\generate_qwen_marketing_cards_max.py`
  - `E:\Pemara\marketing_social\card_quality_qc.py`
  - aprovados em `E:\Pemara\marketing_social\saida_qwen_max_aprovados`
  - revisao em `E:\Pemara\marketing_social\saida_qwen_max_revisar`
- Correcao de rota em 2026-07-06:
  - `E:\Pemara\marketing_social\generate_true_marketing_cards.py` foi bloqueado;
  - motivo: anuncios por script/HTML/CSS/PIL estao proibidos e o resultado ficou com cara de montagem;
  - arquivos gerados por esse caminho foram movidos para `E:\Pemara\marketing_social\old\script_ads_quarantine_20260706_235206`;
  - `run_loja_priority_pipeline.ps1` nao chama mais esse motor automaticamente;
  - scripts ficam permitidos apenas para baixar foto real, preparar referencia, auditar e rodar QC.
- Rota publicavel correta:
  - arte final deve sair do Qwen/ComfyUI/FLUX como imagem unica;
  - aprovados em `E:\Pemara\marketing_social\saida_qwen_max_aprovados`;
  - revisao em `E:\Pemara\marketing_social\saida_qwen_max_revisar`;
  - nada publica sem QC automatico e revisao visual.
- Pilotos reais de 2026-07-06 no produto `139`:
  - Qwen Max melhorou acabamento visual e preservacao do produto;
  - ainda reprovou texto critico em alguns casos: preco/site/modelo;
  - portanto `saida_qwen_max_revisar` nao e publicavel;
  - usar `generate_qwen_marketing_cards_max.py --limit 3 --attempts 3` para tentar seeds diferentes;
  - apenas cards que passarem no QC e forem para `saida_qwen_max_aprovados` podem virar candidatos a postagem.
- Documento principal:
  - `E:\Pemara\marketing_social\IMAGEM_MAX_STACK.md`
- Instalador concluido:
  - `E:\Pemara\install_video_models_curl.ps1`
  - log: `E:\Pemara\logs\install_video_models_curl.log`
- Otimizacao de download:
  - `aria2c` portatil instalado em `E:\Pemara\tools\aria2`
  - o instalador usa aria2 multi-conexao quando disponivel e cai para `curl` se necessario.
- Pacote planejado:
  - Wan2.2 A14B T2V HighNoise Q5_K_M: prompt para video, parte de alta frequencia/detalhe.
  - Wan2.2 A14B T2V LowNoise Q5_K_M: prompt para video, refinamento/estabilidade.
  - Wan2.2 A14B I2V HighNoise Q5_K_M: imagem base para video.
  - Wan2.2 A14B I2V LowNoise Q5_K_M: imagem base para video, refinamento/estabilidade.
  - LTXV 13B 0.9.8 Distilled Q5_K_M: alternativa para clips mais longos/rapidos.
  - LTXV 13B 0.9.8 Distilled VAE.
- Primeiro uso recomendado:
  - Prompt puro: Wan2.2 T2V.
  - Video partindo de foto/personagem/produto: Wan2.2 I2V.
  - Quando precisar experimentar duracao maior com menos custo: LTXV.
- Observacao sobre Wan2.2 A14B:
  - Os arquivos HighNoise/LowNoise formam pares; a melhor qualidade exige workflow proprio em dois estagios.
  - O Studio ja lista e carrega `.gguf`, mas o botao atual de video ainda preserva o fluxo Wan unico/legado para nao quebrar uso manual.
  - Proxima etapa tecnica: criar workflow dedicado `Wan2.2 A14B T2V` e `Wan2.2 A14B I2V` usando HighNoise + LowNoise juntos.

## Intro do jogo como prioridade de video - 2026-06-29
- Projeto movido para dentro do Maestro:
  - `E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo`
- Origem antiga removida por movimentacao:
  - `E:\PROJETOS\projeto_animacao_introducao`
- Conteudo do pacote:
  - 714 arquivos, cerca de 0.58 GB.
  - backgrounds, transicoes, sprites de referencia, musicas, SFX, docs, prompts e manifesto.
- Documentos novos:
  - `video_intro_jogo\README_MAESTRO_PRIORIDADE.md`
  - `video_intro_jogo\docs\05_plano_operacional_intro_60s.md`
  - `video_intro_jogo\manifest\intro_60s_jobs.json`
- Saidas padrao:
  - clips: `video_intro_jogo\outputs\clips`
  - trabalho: `video_intro_jogo\outputs\work`
  - final: `video_intro_jogo\outputs\final\ritmos_da_revolta_intro_60s.mp4`
- Regra de prioridade:
  - Geracao de video do jogo prioriza esta intro de 60s sobre testes genericos e cenas nao relacionadas.
- Estrategia:
  - gerar por cenas curtas;
  - usar Wan2.2 I2V quando houver imagem base;
  - usar LTXV para iteracao rapida;
  - montar em MP4 720p/30fps;
  - audio entra depois da montagem visual.
- Painel:
  - Gerador IA recebeu preset `Intro Ritmos 60s`.
  - Arquivos alterados: `app\index.html` e `app\assets\maestro.js`.
- Correcao de tunel:
  - Maestro local estava ativo em `9501`.
  - Cloudflare estava apontando `maestro.pemaratech.com.br` para `9502`, causando `502`.
  - `E:\Pemara\maestro\.cloudflared\config.yml` corrigido para `host.docker.internal:9501`.
  - Container `maestro-cloudflared` reiniciado e dominio voltou com HTTP 200.
- Validacao:
  - `GET /api/generative/status` lista os modelos novos em `models.video`.
  - `GET /object_info/UnetLoaderGGUF` no ComfyUI confirmou o node `Unet Loader (GGUF)` e os cinco modelos `.gguf`.
  - Disco `E:` apos instalacao: cerca de `231 GB` livres.

## Treino prioritario da intro - 2026-06-29
- Prioridade maxima ativa para:
  - `E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo`
- Flag:
  - `E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo\TRAINING_PRIORITY.flag`
- Dataset inicial criado:
  - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\dataset_intro_60s`
  - 102 clips no total, 84 para treino e 18 para validacao.
- Config de treino:
  - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\config_intro_60s_5b.yaml`
  - LoRA `intro_ritmos_60s_v1`, trigger `intro60`.
  - Sampling interno desativado na primeira rodada para nao estourar VRAM no decode do VAE; validacao sera feita pelo Studio/ComfyUI.
- Watchdog ajustado:
  - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\scripts\watchdog_treino.ps1`
  - Quando a flag de prioridade existe, usa a config da intro em vez do treino padrao.
  - Duplicidade de treino foi corrigida com checagem de PID e limpeza de processos filhos/residuais.
- Guards de GPU ajustados:
  - `E:\Pemara\gpu_window_guard.ps1`
  - `E:\Pemara\gpu_window_guard.py`
  - Enquanto a flag existir, outros treinos de GPU ficam bloqueados; uso manual de geracao continua permitido.
- Status documentado em:
  - `E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo\TREINO_STATUS.md`

## Ordem de treino continuo da intro - 2026-06-30
- Usuario aprovou foco forte no treino da intro.
- Inicio agendado para `2026-06-30 13:00`, horario local.
- Tarefa criada:
  - `RitmosIntroTreinoStart1300UntilStop`
- Script:
  - `E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo\start_intro_training_1300_until_stop.ps1`
- Parada automatica antiga desativada:
  - `RitmosTreinoStopUser`
- Watchdog continua ativo a cada 5 minutos:
  - `RitmosTreinoWatchdog`
- Config de refinamento:
  - `steps: 4000000`
  - `lr: 1.2e-5`
  - `save_every: 750`
  - `max_step_saves_to_keep: 12`
- Regra operacional:
  - treino da intro so deve parar com ordem manual explicita do usuario.
