# Geradores Studio - Maestro Pro

Data: 2026-08-16

## Estado atual

- O Hermes fica fora do fluxo por enquanto.
- O Maestro Studio assume imagem, edicao de foto, video, musica e SFX.
- Video esta ativo com MiniMax H3 como unico motor autorizado de producao.
- Videos profissionais seguem a metodologia oficial por takes: ideia -> roteiro -> take queue -> imagens-base -> clipes curtos -> QC -> montagem.
- O metodo de video agora copia a logica Veo/Kling: start frame, end frame quando necessario, referencias visuais, shot contract, camera control, variantes curtas e QC antes de qualquer final.
- Backend principal: `services/studio/main.py`
- Frontend principal: `app/index.html`, `app/assets/maestro.js`, `app/assets/maestro.css`
- Porta publica do Studio via Maestro: `https://maestro.pemaratech.com.br/`
- API Studio local: `http://127.0.0.1:8029`

## Modos do Gerador IA

- `image`: FLUX/Qwen via ComfyUI.
- `edit`: Qwen Image Edit com imagem base obrigatoria.
- `video`: MiniMax H3 via ComfyUI, take nativo 1280x720 ou 720x1280 a 24 fps; entrega aprovada em 60 fps.
- `music`: LeVo 2 v2-large segue como compositor de musica nova; na aba `Reinstrumentar`, ACE-Step 1.5 XL Base + MuQ e o produtor neural padrao para audio de referencia autorizado.
- `sfx`: Stable Audio como alvo preferido; AudioCraft/AudioGen local como experimental; ElevenLabs SFX como fallback.
- `nvidia_nim`: LLM externo para planejamento, prompts, revisao, auditoria e analise sem ocupar a GPU local.

## Variaveis no `.env`

Arquivo: `E:\Pemara\maestro\pemara\.env`

```env
ELEVENLABS_API_KEY=
ELEVENLABS_SFX_MODEL_ID=eleven_text_to_sound_v2
ELEVENLABS_SFX_OUTPUT_FORMAT=mp3_44100_128
ELEVENLABS_MUSIC_MODEL_ID=music_v2
ELEVENLABS_MUSIC_OUTPUT_FORMAT=mp3_44100_128
ELEVENLABS_MUSIC_FORCE_INSTRUMENTAL=false
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-central1
LYRIA_MODEL_ID=lyria-002
GOOGLE_OAUTH_ACCESS_TOKEN=
STABLE_AUDIO_LOCAL_URL=
STABILITY_API_KEY=
AUDIOGEN_LOCAL_URL=
LEVO2_ENABLED=true
LEVO2_PORT=8190
LEVO2_MIN_FREE_VRAM_MB=20000
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_DEFAULT_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
NVIDIA_FAST_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_REASONING_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
NVIDIA_VISION_MODEL=meta/llama-3.2-90b-vision-instruct
```

## Rotas

- `GET /api/generative/status`: modelos, defaults e providers disponiveis.
- `GET /api/generative/status`: tambem retorna `defaults.video_method_profile` e `providers.video_method_profiles`.
- `POST /api/generative/job`: inicia job async para imagem/video/audio.
- `GET /api/generative/job/{job_id}`: progresso e resultado.
- `GET /api/generative/comfy-view`: arquivos gerados pelo ComfyUI.
- `GET /api/generative/output`: arquivos gerados pelo Studio, como musica e SFX.
- `GET /api/nvidia/status`: status seguro do provider NVIDIA, sem expor chave.
- `GET /api/nvidia/models`: lista modelos liberados na conta NVIDIA.
- `POST /api/nvidia/chat`: chamada OpenAI-compatible para LLM NVIDIA.

## Audio manual no frontend

O Studio possui uma bancada manual em `Studio > Gerador de Musica e SFX`.

Padrao recomendado:

- Musica local instalada: `levo2_local`.
- Musica premium cloud: `lyria`.
- SFX preferido: `stable_audio`.
- SFX local experimental: `audiogen`.
- Fallback antigo: `eleven_music` e `eleven_sfx`.

O frontend mostra quando um provider precisa de configuracao. Se o usuario tentar gerar antes de
configurar, o backend retorna uma mensagem objetiva com a variavel necessaria.

## Reinstrumentacao por IA

A aba `Reinstrumentar` possui um fluxo independente para audio autorizado: ACE-Step XL cria de dois
a quatro candidatos, MuQ-Eval/MuQ-MuLan os ordenam, FFmpeg entrega masters WAV 24-bit e nenhum
candidato e aprovado automaticamente. O MIDI deterministico anterior permanece como fallback
`legacy_midi`. Manual completo: `docs/MUSIC_AI_STUDIO.md`.

## Som sincronizado por leitura do video

Takes visuais `APPROVED` ou `FINAL` agora exibem **Gerar som pelo video**. O controle consulta um
registro de providers independente do modelo, cria um job persistente e registra o resultado como
candidato pendente de escuta. Nenhuma faixa e anexada ou aprovada automaticamente.

Provider instalado: `hunyuan_video_foley_xxl`. Novos modelos podem ser adicionados por adaptador
Python do contrato ou por lista de argumentos confiavel em
`ferramentas/audio_neural/video_sound/providers.json`, sem mudar API ou frontend.

Manual completo: `docs/VIDEO_TO_SOUND.md`.

Variaveis novas:

- `LEVO2_ENABLED`: habilita o provider neural local ja instalado.
- `LEVO2_PORT`: porta loopback exclusiva do runtime isolado; padrao `8190`.
- `LEVO2_MIN_FREE_VRAM_MB`: gate minimo antes de reservar a RTX 5090; padrao `20000`.
- `STABLE_AUDIO_LOCAL_URL`: endpoint local futuro para Stable Audio.
- `STABILITY_API_KEY`: alternativa cloud/API para Stable Audio.
- `AUDIOGEN_LOCAL_URL`: endpoint local futuro para AudioCraft/AudioGen.

## Uso recomendado da NVIDIA

- `NVIDIA_FAST_MODEL`: prompts, nomes, resumos, validacao rapida de cards e comandos.
- `NVIDIA_REASONING_MODEL`: auditoria de plano, revisao de treino, diagnostico e orquestracao.
- `NVIDIA_VISION_MODEL`: analise de imagens quando for preciso poupar a GPU local.

Nao substituir os motores locais: Qwen/FLUX fazem imagem; MiniMax H3 e o unico gerador de video.
A NVIDIA entra como cerebro externo para acelerar decisao, revisao e preparacao dos jobs.

## Saidas

- ComfyUI: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output\maestro_generative`
- Studio audio: `E:\Pemara\maestro\pemara\dados\outputs\generative`

## LeVo 2 local

- O Maestro inicia o ComfyUI isolado do LeVo 2 somente quando um job musical entra em execucao.
- A fila principal do ComfyUI precisa estar vazia e a GPU precisa passar o gate de VRAM.
- A primeira saida e sempre um piloto instrumental de 5 a 15 segundos em FLAC.
- O player e o download aparecem no proprio historico do gerador.
- Toda saida recebe `PENDING_HUMAN_REVIEW`; o gerador nunca aprova nem adiciona musica a um take.
- Ao terminar ou cancelar, o runtime descarrega os pesos e encerra o processo que ele mesmo abriu.
- O modelo esta limitado a uso interno, nao comercial, academico/pesquisa/educacao; publicacao comercial exige revisao de direitos e licenca separada.

## Ativacao

O codigo novo esta ativo na porta oficial atual `127.0.0.1:8029`.

Historico: as portas antigas `8025`, `8026` e `8027` ficaram presas por processos Python protegidos. O Windows negou `Stop-Process` e `taskkill`, entao elas foram mantidas como legado e o Studio novo foi movido para `8029`.

Para verificar/subir o Studio atual:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\services\studio\watchdog_studio_generative.ps1 -Once
```

## NVIDIA no Maestro

Ativo no Studio local `127.0.0.1:8029`. Desde 2026-07-21 somente o Maestro e publico; o painel usa `/api/studio` pelo proxy autenticado e o antigo hostname direto do Studio retorna `404`.

Modelos uteis detectados na conta:

- `meta/llama-3.1-8b-instruct`: rapido para prompts, titulos, resumos e validacao simples.
- `nvidia/llama-3.3-nemotron-super-49b-v1.5`: padrao de raciocinio para planejar treinos, revisar logs e montar jobs.
- `meta/llama-3.2-90b-vision-instruct`: analise de imagem/frame quando for util poupar a GPU local.
- `moonshotai/kimi-k2.6`, `minimaxai/minimax-m3`, `meta/llama-3.3-70b-instruct` e `mistralai/mistral-large-3-675b-instruct-2512`: alternativas para revisao longa.

Regra: usar NVIDIA para acelerar cerebro, auditoria e texto; manter render, ComfyUI e LoRA locais.

## Regras de qualidade

- Video final profissional nao deve ser gerado em prompt unico longo. Prompt unico e apenas rascunho.
- Enquanto existir `dados/flags/video_generation_paused.flag`, o Studio deve bloquear `mode=video`
  e ferramentas de editor/remaster de video.
- Regra oficial: takes curtos de 5s a 12s, imagem-base aprovada, QC por contact sheet e montagem final.
- Formula local: Qwen/FLUX para imagem-base; MiniMax H3 para takes e conectores; RIFE/RealESRGAN/NVENC somente apos aprovacao visual; HunyuanVideo-Foley apos picture lock.
- Plano futuro RTX 5090: `PLANO_RTX5090_QUALIDADE_MAXIMA.md`.
- Com RTX 5090, qualidade maxima preserva 20 steps, guidance 1.0, encoder Qwen3-VL-32B e pesos H3 atuais; atalhos com risco de fidelidade ficam em laboratorio.
- Cards e anuncios finais nao devem ser montados com compositor simples tipo Paint.
- Produto real deve permanecer fiel; IA pode melhorar composicao, fundo, luz e acabamento.
- Texto comercial critico deve vir do sistema, com verificacao, para evitar alucinacao.
- Videos padrao: HD 720p, MP4, 30fps.
- MOVA-720p e a excecao nativa validada: 1280x720, 193 quadros a 24 FPS, MP4 H.264
  por NVENC e audio AAC sincronizado. O Studio nunca reduz esse perfil para 16 FPS nem usa CPU
  como fallback de codificacao.
- Video manual/local deve seguir `veo_kling_shot_contract`; prompt solto fica apenas como rascunho conceitual.
- Musicas e SFX devem sair com preview de audio e download direto no Maestro.

## Video Global Engine

Base oficial:

`E:\Pemara\maestro\pemara\ferramentas\video_global_engine`

Referencia ouro inicial:

`E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\pre_parabens_referencia`

Metodo Veo/Kling implantado:

`E:\Pemara\maestro\pemara\ferramentas\video_global_engine\docs\09_metodo_veo_kling_para_motor_local.md`

## MOVA-720p no painel Maestro

O modelo oficial `OpenMOSS-Team/MOVA-720p` fica em
`D:\PemaraModels\mova\MOVA-720p`, separado dos modelos do ComfyUI. O codigo oficial pinado fica
em `E:\Pemara\third_party\MOVA`, e as dependencias vivem no ambiente isolado do motor em
`ferramentas\video_global_engine\engines\mova\.venv`.

Fluxo do proprietario:

1. Abra `Criar`, selecione `Video` e o preset `MOVA 720p - RTX 5090 + 128 GB`.
2. Escreva o prompt diretamente no painel. O quadro inicial e opcional; quadro final nao se aplica.
3. Inicie o job e acompanhe o progresso/cancelamento no proprio Maestro.
4. O resultado volta ao painel como MP4 720p com audio nativo sincronizado.

O perfil usa BF16, group offload para a RAM, SDPA e uma unica RTX 5090. A verificacao de status
exige pesos completos, fonte/runtime pinados, NVENC e pelo menos 112 GiB detectados. Assim a
instalacao atual pode terminar com 64 GB, mas nenhuma inferencia pesada sera iniciada antes da
troca fisica para 128 GB.

## Motores de video vigentes: MiniMax H3 e LTX 2.5

O Maestro exige que o proprietario selecione `minimax_h3` ou `ltx_2_5` para cada video ou
take. Nao existe motor padrao, troca automatica nem fallback entre eles. Um perfil ausente,
desconhecido ou historico falha antes da copia da ancora e antes da fila GPU.

O LTX 2.5 usa o modelo e os workflows oficiais fixados no manifesto
`tools/model_installers/models.lock.json`. O workflow API deriva do grafo oficial Two-Stage,
usa 960x544/24 FPS no primeiro estagio e exige `8n+1` quadros. O aprimorador opcional de prompt
do workflow oficial fica desligado: o prompt compilado pelo contrato de inteligencia de ancora
e ligado diretamente ao encoder para evitar uma segunda reescrita nao auditada.

Para verificar ou reinstalar somente o componente LTX 2.5:

```powershell
python E:\Pemara\maestro\pemara\tools\model_installers\install_models.py --action verify --component ltx25
python E:\Pemara\maestro\pemara\tools\model_installers\install_models.py --action install --component ltx25 --accept-licenses
```

Somente as cinco IC-LoRAs historicas consumidas pelos workflows oficiais 2.5 sao aceitas como
ativos de compatibilidade. Elas nao constituem um motor antigo, nao podem registrar checkpoint
antigo e nao habilitam fallback. Os modos opcionais permanecem bloqueados quando sua IC-LoRA
exata nao estiver acessivel.

Gates permanentes: selecao explicita do motor, recibo SHA-256 da ancora e do prompt, prontidao
do motor, admissao serial de GPU, QC tecnico e revisao humana. Upscale so produz um candidato
separado depois da aprovacao do video original.
