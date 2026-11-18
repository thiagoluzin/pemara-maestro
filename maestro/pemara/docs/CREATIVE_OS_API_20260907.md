# Creative OS API V0.1

Prefixo interno Studio: `/api/creative`; pelo frontend autenticado: `/api/studio/api/creative`. As rotas herdam a fronteira de segurança existente. Estes endpoints são do backend Maestro. O Codex deve usar MCP para qualquer operação de ComfyUI, inclusive saúde viva, geração e cancelamento; consultar metadados locais não autoriza enviar render via HTTP.

## Contrato básico

`POST /shots` recebe `{"ir": {...}}`; atualização recebe também `expected_revision`. O ID retornado é composto por projeto/plano. Campos mínimos de IR:

```json
{"version":"0.2","project_id":"filme","shot_id":"SH01","duration_seconds":5,"content":{"description":"Descreva o plano"},"generation":{"preferred_engine":"h3","quality_mode":"balanced","max_repairs":2,"max_same_model_retries":1}}
```

`preferred_engine`: `h3`/`minimax_h3`, `ltx25`/`ltx_2_5`; `auto` só recomenda. Quality mode registra intenção; perfil de execução H3 é explícito em bindings ou usa Production existente. Não há perfil de aceleração promovido automaticamente.

| Operação | Rota e payload |
|---|---|
| Saúde de integração | `GET /health` |
| Capacidades vivas pelo backend | `GET /capabilities` |
| Listar/ler planos | `GET /shots`, `GET /shots/{id}` |
| Analisar/recomendar | `POST /shots/{id}/analyze` ou `/route` |
| Gerar pelo Maestro | `POST /shots/{id}/generate`: `idempotency_key`, `bindings` |
| Indexar job existente | `POST /jobs/{job_id}/attach`: `project_id` opcional; não envia render |
| Acompanhar geração | `GET /generations/{id}`, `/lineage` |
| Cancelar job próprio | `POST /generations/{id}/cancel` |
| Vídeo preservado | `GET /generations/{id}/artifacts/{index}` |
| Critic | `POST /generations/{id}/evaluate`: `observations` opcional |
| Veredito humano | `POST /generations/{id}/verdict`: `decision=approved/rejected`, `artifact_sha256`, `notes` |
| Registrar asset existente | `POST /assets`: `project_id`, `relative_path`, `role` |
| Reference sheet interno | `GET /projects/{id}/reference-sheet` |
| Bibles | `GET /projects/{id}/bibles`; `POST /projects/{id}/bibles/{character|scene|prop}/{item_id}` com `content` e revisão em updates |
| Planejar reparo | `POST /generations/{id}/repairs`: `reason`, `strategy`, `ir`/`bindings` opcionais |
| Executar reparo revisável | `POST /repairs/{id}/execute` |
| Avaliar fronteira | `POST /continuity`: `left`, `right`, `observations` por dimensão com `state` e `evidence` |
| Plano de direção | `POST /projects/{id}/direction`: `shot_ids` ordenados |
| Estado/avanço | `GET /directions/{id}`; `POST /directions/{id}/advance` com `idempotency_key`, `bindings` |
| Montagem | `POST /directions/{id}/assemble` com `idempotency_key`; `GET /assemblies/{id}` |
| Revisão da montagem | `POST /assemblies/{id}/verdict`: `decision`, `artifact_sha256`; mídia em `/artifacts/{index}` |
| Benchmark | `GET /benchmarks`; `POST /generations/{id}/benchmark` com `class=B01…B13` |
| Masters | `GET /masters` |
| Metadata latent | `POST /generations/{id}/latents`; exige latent capturado, hash e proveniência da geração |
| Preparar Motion | `POST /motion-plans`: `shot_ids`, `seed`, `profile=h3_production`, `selected` opcional, `motion_context` booleano |
| Gerar Motion | `POST /motion-plans/{id}/generate`: `idempotency_key`; fila autônoma do Maestro |
| Estado/cancelamento Motion | `GET /motion-batches/{id}` cria registros separados para os segmentos concluídos; `POST /motion-batches/{id}/cancel` cancela o batch inteiro |
| Proposta de prompt | `POST /shots/{id}/prompt-proposals`: `text`, `provenance`; mantém original e exige revisão |
| Revisão/aplicação de prompt | `POST /prompt-proposals/{id}/verdict`: `decision`, `suggestion_hash`; `POST /prompt-proposals/{id}/apply` aplica somente proposta aprovada e IR ainda vigente |
| HQ | `GET /hq`; `POST /hq` com `master_id`, `profile_id`, `idempotency_key` |
| Pausa/retomada | `POST /hq/{id}/cancel` só aguardando; `POST /hq/resume` não reenvia jobs incertos |
| Revisão HQ | `POST /hq/{id}/verdict`: `decision`, `artifact_sha256`; mídia em `/hq/{id}/artifacts/{index}` |

Bindings: `seed`, `h3_quality_profile`, `base_asset_id`, `end_asset_id`. I2V usa o receipt de análise/compilação já existente no Maestro: `anchor_contract_id`, `prompt_compiler_version`, `compiled_prompt`, `compiled_negative`. O backend verifica imagem, motor e textos exatos; não produz receipt fictício. Texto compilado é a configuração efetiva preservada no lineage. Reanálise é necessária após expiração do receipt.

Erros retornam `error.code` e `error.message`. Status comuns: 422 contrato inválido; 409 conflito, recurso não integrado, orçamento, gate ou configuração divergente; 404 registro ausente. Um mesmo idempotency key com outra configuração não inicia segundo job. Em estado incerto, preservar o registro e investigar antes de novo envio.

Benchmarks exigem seed real e workflow hash; dados sem proveniência não influenciam o roteador. Scores sem evidência não são aceitos. Revisões humanas nunca são inferidas de PASS técnico.

Motion Director é opcional e experimental: T2V H3 Production sem áudio. A grade temporal usa 17k+5 e mínimo 124 frames. Rerun seletivo que depende de predecessor não selecionado é bloqueado enquanto source bridge salvo não estiver integrado; `motion_context=false` permite regenerar isoladamente. Cada segmento tem aprovação própria. A base seed está no workflow; não se inventa seed efetiva por segmento.

HQ `h3_latent_2stage_v1` é manual/experimental: master H3 T2V Production 1088×608/124 frames/24 fps sem áudio, latent capturado e fingerprints de modelos antes do envio. Produz candidato 1536×864 com upscale 3D + 4 steps/denoise 0,25, preservando master original. Perfis e arquivos precisam corresponder à qualificação; não habilita finishing retroativo para vídeos antigos sem proveniência. Os perfis pixel FHD existentes continuam disponíveis.

## Rewriter H3 opcional

POST `/api/creative/shots/{shot_id}/rewrite` com `idempotency_key` e `seed` explícita cria job Maestro. GET `/api/creative/rewriter-jobs/{id}` acompanha e vincula proposta sem aplicação; POST `/api/creative/rewriter-jobs/{id}/cancel` cancela. GET `/api/creative/prompt-proposals/{id}` consulta texto e proveniência. Revisão/aplicação seguem os gates existentes. Somente brief textual H3 qualificado; pesos em cache, sem download automático.

## Timeline contínua H3

POST `/api/creative/shots/{shot_id}/timeline-plan` com `seed` e `segment_count` prepara sem enviar. POST `/api/creative/shots/{shot_id}/timeline-generate` acrescenta `idempotency_key` e cria geração na fila existente. Acompanhamento, cancelamento e revisão usam `/generations/{id}` e rotas existentes. Qualificação inicial: dois segmentos de 124 frames, 22 de overlap, saída 226 frames sem áudio. Plano não equivale a aprovação ou geração.

## Fun Control

POST `/api/creative/control-assets` multipart campo `file` registra vídeo pré-processado no projeto `maestro_control` após checagens de formato e geometria. POST `/api/creative/shots/{shot_id}/control-generate`: `asset_id`, `control_kind`, `strength`, `seed` e `idempotency_key`. Geração, acompanhamento, cancelamento e revisão usam a fila e `/generations/{id}` existentes. Tipo de controle é declarado pelo usuário; não há detecção/preprocessamento silencioso.

## All-In-One H3

A rota existente `/shots/{shot_id}/generate` aceita `bindings.h3_adapter="all_in_one"`, seed e bindings de imagem existentes. A expansão é T2V sem bindings de imagem ou I2V com first/last; recibos de âncora continuam obrigatórios. Adapter `native` permanece default. Somente Production horizontal sem áudio; templates externos avançados não são implicitamente executados.


### Consulta visual local (experimental)
POST /api/creative/generations/{id}/semantic-review: artifact_sha256 e idempotency_key. Exige vídeo concluído de até 30 s; extrai seis quadros e agenda Gemma local, consumindo GPU. GET /api/creative/semantic-jobs e /semantic-jobs/{id}; POST /semantic-jobs/{id}/cancel. Resultado advisory_only, semantic_quality_proven=false, human_verdict=null; não alimenta aprovação, ranking ou reparo automático.
