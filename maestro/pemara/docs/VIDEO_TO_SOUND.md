# Maestro Video-to-Sound

Data de implantacao: 2026-08-14

## Objetivo

Gerar ambiente e efeitos sincronizados a um take de video aprovado sem acoplar o Maestro a um
modelo especifico. O backend conhece um contrato de provider; HunyuanVideo-Foley XXL e apenas o
primeiro adaptador instalado.

O sistema nao gera musica, nao cria dialogo e nao anexa o resultado ao filme automaticamente.
Todo resultado entra como piloto e exige escuta humana explicita.

## Arquitetura

1. O take visual precisa estar `APPROVED` ou `FINAL`.
2. A interface consulta `GET /api/video-sound/providers`.
3. O proprietario escolhe provider, duracao e direcao sonora.
4. `POST .../video-sound-jobs` cria um job persistente no historico do Studio.
5. O provider recebe `VideoSoundRequest` e devolve `VideoSoundResult`.
6. O backend mede o arquivo e registra um candidato dentro do proprio projeto.
7. O player aparece no take com estado `candidate_pending_human_listening`.
8. Somente `audio-candidate-review` pode aprovar ou reprovar o candidato.

Arquivos principais:

- `services/studio/video_sound.py`: contrato, registro e adaptadores.
- `services/studio/main.py`: API, job persistente, cancelamento e integracao.
- `services/studio/video_projects.py`: registro e decisao humana do candidato.
- `app/assets/maestro.js`: controles acessiveis dentro de cada take aprovado.
- `ferramentas/audio_neural/video_sound/providers.json`: providers externos declarativos.

## Contrato do provider

Cada provider publica identificador, rotulo, modelo, estado, duracao, formatos, dispositivo e
necessidade de GPU exclusiva. A entrada comum contem job, video, pasta de saida, prompts, duracao e
seed. A saida comum contem provider/modelo, arquivo, hash do video, QC e metadados de geracao.

Nenhum provider pode escrever fora de `project/audio/video_sound/<take>/<job>/`.

## Provider instalado: HunyuanVideo-Foley XXL

- Pesos: `G:\Pemara_AI_Models\HunyuanVideo-Foley`.
- Runtime: imagem Docker `pemara/hunyuanvideo-foley:cuda128`.
- Dispositivo: `cuda:0`, RTX 5090.
- Proxy visual: 512x288, 24 FPS, H.264 por NVENC.
- Saida de revisao: WAV PCM 24-bit, 48 kHz, estereo.
- Duracao de piloto: 0,5 a 15 segundos.
- Inferencia: 50 passos, modelo XXL, offline.

Antes de iniciar, o adaptador confirma pesos, Docker, FFmpeg/FFprobe, fila principal da ComfyUI
vazia, pelo menos 24 GB de VRAM livre e exclusividade do processo Hunyuan dentro do Studio. O
cancelamento para somente o container nomeado pelo proprio job.

## Adicionar outro modelo sem alterar API ou interface

Edite `ferramentas/audio_neural/video_sound/providers.json`. O comando e uma lista de argumentos;
strings shell, pipes e redirecionamentos nao sao aceitos.

Placeholders liberados:

- `{input_video}`
- `{output_audio}`
- `{prompt}`
- `{negative_prompt}`
- `{duration_seconds}`
- `{seed}`
- `{job_id}`

O arquivo acompanha um exemplo desativado. Instale e valide o runner, garanta que ele grave em
`{output_audio}`, ative `enabled`, reinicie somente o Studio e gere um unico piloto curto. Se o
modelo precisar de outro protocolo, implemente `VideoSoundProvider` e registre-o em
`build_default_registry`; API, fila, player, QC e aprovacao continuam inalterados.

## API

- `GET /api/video-sound/providers`: lista providers/capacidades.
- `POST /api/video-projects/{projectId}/takes/{takeId}/video-sound-jobs`: gera o piloto.
- `GET /api/video-sound/jobs/{jobId}`: acompanha o job.
- `POST /api/video-sound/jobs/{jobId}/cancel`: cancela o job.
- `POST /api/video-projects/{projectId}/takes/{takeId}/audio-candidate-review`: decisao humana.

Exemplo de geracao:

```json
{
  "providerId": "hunyuan_video_foley_xxl",
  "prompt": "Ambiente e impactos fisicos sincronizados ao movimento visivel.",
  "negativePrompt": "music, speech, clipping",
  "durationSeconds": 5,
  "seed": -1
}
```

Exemplo de decisao:

```json
{"decision": "REJECTED", "reason": "Impactos sem peso"}
```

## Estados e seguranca

- `queued`, `running`, `done`, `canceling`, `canceled`, `error`, `interrupted`.
- Nenhuma geracao em take visual nao aprovado.
- Nenhum comando arbitrario vindo da requisicao e nenhum `shell=True`.
- Nenhum caminho fora do projeto e nenhum fallback silencioso para CPU.
- Nenhum auto-attach, auto-mix ou auto-approve.
- Candidato reprovado sai do slot ativo e permanece no historico de auditoria.

## Variaveis

```env
VIDEO_SOUND_HUNYUAN_MODEL_ROOT=G:\Pemara_AI_Models\HunyuanVideo-Foley
VIDEO_SOUND_HUNYUAN_DOCKER_IMAGE=pemara/hunyuanvideo-foley:cuda128
VIDEO_SOUND_GPU_ID=0
VIDEO_SOUND_MIN_FREE_VRAM_MB=24000
VIDEO_SOUND_COMFY_QUEUE_URL=http://127.0.0.1:8188/queue
```

## Validacao

```powershell
cd E:\Pemara\maestro\pemara\services\studio
python -m unittest test_video_sound.py
python -m unittest test_video_projects.VideoProjectsTests.test_video_sound_candidate_requires_explicit_human_review
python -m unittest test_generative_control.GenerativeControlTest.test_video_sound_job_uses_selected_provider_and_stops_at_human_review
python -m unittest test_maestro_ui_contracts.MaestroDirectorQueueUiContractTests.test_take_exposes_model_independent_video_to_sound_controls
```

Os testes nao carregam modelos nem iniciam a GPU.

## Implantacao verificada em 2026-08-14

- Studio e frontend reiniciados pelo supervisor Radar, sem reiniciar a ComfyUI.
- `GET /api/video-sound/providers`: HTTP 200, contrato 1.0.
- Provider padrao: `hunyuan_video_foley_xxl`, `configured=true`, `device=cuda:0`.
- Imagem local confirmada: `pemara/hunyuanvideo-foley:cuda128`.
- Fila ComfyUI vazia e RTX 5090 com VRAM acima do piso de 24 GB no preflight.
- Studio `127.0.0.1:8029`, frontend `127.0.0.1:9501` e ComfyUI
  `127.0.0.1:8188` permaneceram em loopback.
- Host forjado contra a nova API recebeu HTTP 403.
- A interface servida contem o build `20260814-video-sound1` e os controles video-to-sound.

Esta verificacao prova a implantacao tecnica local. Um audio novo ainda continua sendo um piloto e
so pode ser promovido depois de escuta humana explicita.
