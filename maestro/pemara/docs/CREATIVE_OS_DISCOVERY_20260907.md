# Creative OS V3 — Discovery

Data: 2026-09-07. Escopo: Maestro existente em `E:/Pemara/maestro/pemara`, runtime ativo, diretórios de modelos configurados em E: e D:, plugins, builders e metadados locais. Não é uma varredura de todos os backups/discos do computador. “Não encontrado” significa não encontrado neste escopo, não inexistência universal.

Leitura integral de `prompts/CODEX_FIRST_PROMPT.md`, README, AGENTS, changelogs, todos os documentos de `docs/creative_os`, schemas e exemplos do ZIP. ZIP SHA256: `982ccab13bf4170172f3b9fbd0c26b50cadc7cd46730c987749248d204dcd3b0`. O pacote foi lido diretamente, sem extração sobre o projeto. Suas instruções de implementação são propostas para fases futuras; esta etapa não as executou.

Até a conclusão deste relatório: nenhuma instalação, clone, refatoração, alteração de workflow, geração, benchmark GPU, limpeza ou reinício. Conforme esclarecimento do proprietário, **a coordenação pelo Codex usa ComfyUI 100% via MCP; o uso manual pelo Maestro mantém o backend direto e autônomo**. As consultas diretas iniciais ocorreram antes dessa instrução; as consultas posteriores ao serviço foram via `comfyui-local`. A regra foi registrada em `E:/Pemara/AGENTS.md`, após concluir o Discovery. Não há migração interna do Maestro neste escopo.

## A. Current Architecture

Fluxo existente: frontend HTML/JavaScript → gateway Maestro → Studio FastAPI → seleção explícita de engine → compilador/builder → fila Studio → ComfyUI → recuperação de outputs → revisão por take → finalização/exportação.

Escolha do motor confirmada no código da interface: `app/index.html:226` apresenta “Escolha o motor deste vídeo”, cards em radiogroup e seleção inicial vazia. `app/assets/maestro.js` implementa `selectVideoEngine`; `video_engines/registry.py` exige seleção e bloqueia fallback. O proprietário confirmou que esse direito de escolher H3 ou LTX 2.5 deve permanecer. Inspeção de código não equivale a teste visual da sessão autenticada.

Verificação adicional sem GPU: `python -B -m unittest test_video_engine_selection -v` passou 3/3 testes em diretórios temporários: ausência de seleção não assume H3, proprietário pode selecionar H3/LTX sem fallback, engine desconhecida é rejeitada. Nenhum projeto real foi alterado pelos testes.

| Item | Evidência atual |
|---|---|
| Frontend | `app/index.html`, `app/assets/maestro.js`; `MASTER.py` serve `APP_DIR=BASE/app`; existe shell desktop pywebview |
| Gateway/backend | `MASTER.py`, listener local 9501; Studio `services/studio/main.py`, FastAPI, listener local 8029 |
| Banco compartilhado | SQLite em `database/pemara.db`, arquivo de 16.384 bytes; `shared/database.py` e `shared/config.py`. Isso não é o store principal de jobs de vídeo |
| Jobs | `dados/studio/generative_jobs.json`, `GenerativeJobStore`, locks de thread/processo, escrita atômica, recuperação de interrupções e retenção de até 500 jobs |
| Queue | Lista/Condition em memória no Studio, registros JSON persistidos, fila ComfyUI e lease GPU em `dados/studio/gpu_lease.json`; não foi encontrado broker dedicado neste fluxo |
| Storage | Filesystem; input/output/temp ComfyUI preservados na árvore histórica; modelos também em `D:/PemaraModels/offloaded/ComfyUI` |
| Projetos | `video_projects.py`: manifest, take queue, refs, keyframes, takes, edit, qc, audio, output e logs; estados PLANNED/GENERATING/READY/APPROVED/REJECTED/UPSCALING/FINAL |
| Assets | `media_assets.py`: descoberta de arquivos, tipo, tamanho, caminho relativo e URLs de entrega; sidecars e hashes nos fluxos de aprovação/upscale |
| Geração atual | Snapshot HTTP anterior à exigência MCP: `queue_running=[]`, `queue_pending=[]`. Store Studio: 467 done, 19 error, 11 canceled, 3 interrupted; nenhum queued/running nos 500 registros |
| Progresso | `_queue_comfy_workflow` consulta history/queue a cada 5 s; percentual intermediário é estimado por tempo/timeout, não medida real de steps; registra prompt_id para retomada |
| Outputs | `CreateVideo`/`SaveVideo`, MP4 H.264; normalização por `_extract_comfy_outputs`; entrega por `/api/generative/comfy-view` e `/api/generative/output`; revisão/proxies/assembly separados |

Limitação de estado: MCP `job(action="queue")` retornou dez registros de 31/08 como queued, sem posição ou tamanho do workflow. Isso diverge da fila viva consultada anteriormente; não interpretar esses registros persistidos como dez execuções reais, nem apagá-los neste Discovery.

## B. H3 Current Path

`video_engines/h3.py` → compilador `anchor_intelligence/compiler_h3.py` e `h3_prompt_writing.py` → builders FL2VA/Ref2VA em `main.py` → validação de grafo em `h3_workflow.py` → ComfyUI.

Modelos encontrados como arquivos e opções dos loaders:

- FL2VA e Ref2VA `minimax_h3_*_pruned_int8_convrot.safetensors`: 20.970.379.616 bytes cada.
- Encoder `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`: 15.687.142.551 bytes.
- VAE vídeo FP16: 5.207.808.496 bytes; VAE áudio FP32: 605.254.808 bytes.
- LoRA `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors`: 1.956.193.000 bytes. Presença não significa ativação ou qualificação.

Perfil padrão confirmado em código: Production 1088×608 / 10 steps / 24 fps. Draft 1024×576 / 6 steps força áudio desligado; Hero 1344×768 / 12–14; Master 1344×768 / 20; perfis legados continuam resolvíveis. Áudio depende do campo do job/caller; não inferir política global apenas de `nativeAudio=True` no catálogo.

FL2VA usa `MiniMaxH3ImageToVideo`, `MiniMaxH3SigmaShift`, `BasicGuider`, scheduler simple, sampler res_multistep, decode tiled, scale e SaveVideo. First/last e guia intermediário possuem ligação explícita. O builder impõe grade temporal 17k+5 e limites próprios; o intervalo declarado no adapter não substitui essa validação.

O validador rejeita mistura dos condicionadores FL2VA e Ref2VA (`H3_GRAPH_MIXED_MODES`) e rejeita alegação de pose exata. Referência de vídeo não equivale a DWPose conectado a controle estrutural. Nenhum All-In-One externo ou Hybrid FL+REF foi comprovado.

## C. LTX Current Path

`video_engines/ltx25.py` → `anchor_intelligence/compiler_ltx25.py` → `ltx25_workflow.py` → template API fixado → runtime ComfyUI.

Template: `ferramentas/video_global_engine/workflows/ltx25/LTX-2.5_T2V_I2V_Two_Stage_Distilled.api.json`. SHA256 verificado: `01d1d5c4d2a28fe5fef4fef405fcce98e41a68c081d8e65e311a8d55b0b2652c`, igual à constante do builder. O builder remove o enhancer opcional e liga o prompt compilado; existe first/last via LTXVAddGuide.

Modelos encontrados em D:, expostos ao runtime: transformer distilled NVFP4 (18.721.548.408 bytes) e BF16 (42.018.190.584), encoder Gemma4 BF16 e INT8 ConvRot, VAEs de áudio/vídeo, duration head, upscalers latentes espacial e temporal x2. Encoder INT8 também existe em E:. Há LoRAs IC de **2.3**: sua existência não comprova compatibilidade com 2.5.

Adapter declara T2V/I2V/A2V/T2A, áudio, two-stage, IC-LoRA, 24 fps, grade 8n+1 e saída base 960×544/544×960. Declarações amplas do catálogo exigem validação por modo; apenas o template citado foi validado nesta sessão.

MCP validate_workflow: valid=true, zero erros, um aviso `edge_type_mismatch` no frame_rate (`FLOAT,INT` versus `INT`); sem partner nodes e sem créditos. Sem execução GPU. Retake/DFR não possuem rota integrada comprovada; masks, inpaint, guias, latent upsample e conditioning save/load presentes são primitivas, não prova de um RetakePipeline/DFR pronto. Há arquivos `.latent` e workflows de save/decode em projetos LTX anteriores, sem prova de pacote latente versionado uniforme.

## D. ComfyUI Capabilities

Runtime **ativo**: `E:/Pemara/maestro/runtimes/ComfyUI-v0.34.2`, commit `169fcf35a2fc163fec31338b816503ddac0d3fcf`, local 127.0.0.1:8188. Frontend 1.49.6; templates 0.11.50. User state em `maestro/runtimes/state/ComfyUI-v0.34.2/user`, com SQLite `comfyui.db`.

Checkout **histórico**: `ferramentas/ComfyUI`, versão 0.30.2, commit `f4e9ef55695b62c76292f1386fdecd6cec285e88`. O MCP/comfy-cli ainda usa esse workspace para inventário de disco; `system_stats` MCP confirma o servidor ativo 0.34.2. Não atualizar o checkout antigo supondo que seja o processo ativo.

Custom node packs no runtime: AIGODLIKE translation, controlnet_aux, essentials, GGUF, IPAdapter, KJNodes, LTXVideo, SAM2, VideoHelperSuite, pemara_minimax_h3_nodes e x-flux. A maioria é junction para a árvore histórica; LTXVideo é diretório próprio. Pack presente não implica sucesso de todas as importações; nós citados abaixo foram observados no object_info vivo.

| Capacidade solicitada | Resultado |
|---|---|
| H3 Motion Director | Não encontrado nos packs/grafos examinados |
| H3 Timeline Director | Não encontrado |
| H3 Prompt Rewriter Omni | Plugin/LoRA específico não encontrado; compilador próprio existe e não é equivalente |
| H3 Fun Control | Não encontrado; controlnet_aux sozinho não fornece o condicionador H3 |
| H3 Latent Upscaler / split | Plugin e pesos não encontrados nos diretórios ativos/configurados |
| H3 All-In-One | Workflow externo específico não encontrado; builders próprios FL/Ref existentes |
| H3 Reference Sheets | Plugin/adapter específico não encontrado |
| Hybrid FL+REF | Não comprovado; mistura atual explicitamente rejeitada pelo validador |
| Sol-Attn / Sol-Engine | Não encontrados no caminho de geração/packs examinados |
| H3 Turbo/cache | LoRA 4-step presente; EasyCache/LazyCache e patches KJ presentes; FirstBlockCache/Spectrum não encontrados como integração H3; não qualificados |
| LTX 2.5 Director | Não encontrado |
| LTX Retake | Primitivas de máscara/inpaint presentes; modo integrado não comprovado |
| LTX DFR | Upscalers e two-stage presentes; DFR completo não comprovado |
| LTX keyframes | LTXVAddGuide e ligação first/last no builder; multiguide no runtime |
| Persistência latente | SaveLatent/LoadLatent presentes; exemplos LTX persistidos; não existe contrato H3 Latent Package comprovado |
| Wan | Animate 2.2 BF16 + VAE presentes; nós nativos Wan e builder legado existem; registry público atual não permite engine Wan |
| Hunyuan | Nós nativos 1.5 e builders legados I2V/SR presentes; checkpoints 1.5 não encontrados nas raízes de modelos configuradas |
| SkyReels | Pesos/plugin/adapter não encontrados no escopo |

Não confundir nós API Hailuo/LTX/Wan com geração local instalada. Não houve uso de API paga.

## E. 5090 Performance Stack

RTX 5090, driver 616.64, 32.607 MiB de VRAM no nvidia-smi; snapshot 2.364 MiB usados/0% utilização. MCP: 34.162.016.256 bytes totais de VRAM e 32.496.418.816 livres; diferenças refletem contabilidade/fontes. RAM visível: 100.455.010.304 bytes (~93,6 GiB), ~75,5 GB livres no snapshot MCP.

Python runtime 3.11.9, venv `D:/PemaraRuntimes/comfyui-v0342-py311`; PyTorch 2.14.0+cu130; build CUDA 13.0. Isso não estabelece versão de toolkit nvcc instalado. Allocator cudaMallocAsync. `comfy-kitchen` 0.2.31 e `comfy-aimdo` 0.4.15.

Metadados desse venv: Triton, triton-windows, SageAttention e flash-attn não encontrados. Nós de patch Sage no catálogo não comprovam dependência utilizável. Código H3 chama optimized_attention; backend concreto escolhido por sessão, timings de load/conditioning/sample/decode, offload efetivo e compile efetivo não foram medidos. O grafo FL atual não liga cache/compile/Turbo. Não há evidência nova de vantagem de desempenho; não ativar otimizações a partir desse inventário.

## F. Reusable Components

Reaproveitar BaseVideoEngine, adapters H3/LTX, registry explícito, compiladores de prompts, validadores de grafo, model_readiness, store de jobs, GPU lease, project manifests/take queue, sidecars/hashes, revisão humana, review_proxies, project_assembly, ready_exports e workers de upscale. O ponto de integração é uma camada fina sobre esses contratos; não recriar UI, timeline, storage ou filas do zero.

## G. Missing Components

Faltam contrato Creative IR 0.2 validado em execução, resolvedor uniforme asset://, reason_codes de routing, benchmark store com config hash, lineage uniforme entre motores, critic multidimensional formal, repair planner, contratos versionados de Latent Package e finishing profiles. Directors e otimizações ausentes não são dependências da fase 1 mínima.

| V3 | Suporte existente / trabalho necessário |
|---|---|
| Proxy/LQ | Parcial: Draft H3 e proxies de revisão existem. Proxy de reprodução não equivale a geração LQ com estado refinável |
| Approved Master | Parcial: aprovação por take e sidecars/hash; criar entidade explícita e ligação imutável à geração |
| Deferred HQ | Parcial: jobs/workers de upscale, recuperação e guarda de source hash; falta contrato geral de HQ por engine/latent |
| HQ worker separado | Viável arquiteturalmente, já há subprocessos de upscale; não comprovado worker geral H3 refine/DFR com telemetria de degradação. Uma GPU requer lease/serialização, não paralelismo irrestrito |

## H. Conflicts

1. Pacote propõe AUTO/escalation; registry atual exige escolha explícita H3/LTX, default=None e fallback=False. Não mudar por simples leitura da especificação.
2. Pacote inclui Wan/Hunyuan/SkyReels; registry fecha em dois motores. Presença de arquivos legados não autoriza reativá-los.
3. MCP aponta disco antigo e servidor novo; caminhos, commits e capabilities precisam distinguir essas duas autoridades.
4. Histórico MCP queued diverge de estado vivo anterior; reconciliar por prompt_id/estado de servidor, sem replay automático.
5. Templates LTX avançados/catalogados não são prova de cada modo operacional; LoRAs 2.3 não devem ser presumidas 2.5.
6. Grafo H3 atual proíbe Hybrid; mudanças exigem adapter/validação específica, fora do Discovery.
7. PASS técnico não é aprovação humana. O diagrama PASS→Approved Master do pacote precisa de gate humano explícito.
8. `main.py`, media handling e scripts de restart usam HTTP ComfyUI direto. Isso é permitido para o fluxo autônomo do Maestro, conforme esclarecimento do proprietário. O Codex não deve utilizar esses clientes como atalho para contornar o MCP em sua própria coordenação.
9. Schemas fornecidos são permissivos (`additionalProperties`, subobjetos livres), e não formalizam todas as adições V3: não garantem integridade de asset roles, lineage/latent, limits ou compatibilidade.
10. Builders têm paths/modelos/node IDs fixados internamente. Creative IR pode permanecer neutro sem remover pins de segurança dos adapters.

## I. License Risks

Inventário documental, sem conclusão jurídica de autorização: LICENSE do runtime ativo identifica GPL v3; LICENSE de LTXVideo ativo identifica LTX-2 Community License Agreement, 05/01/2026. Não presumir licença permissiva pelo nome do repositório. O ZIP relata condições próprias H3 e de terceiros; a licença individual de cada checkpoint/LoRA não foi validada integralmente nesta auditoria.

Pendências para futura distribuição: registrar origem, commit, hash, license ID/texto e termos dos pesos e dependências; manter plugins externos e não copiar código/pesos para o core. Não houve distribuição. Links e avaliações externas contidos no ZIP são fontes propostas pelo autor, não pesquisa independente confirmada nesta sessão.

## J. Minimal Integration

Fluxo proposto da aplicação: UI atual → Creative IR validado → seleção explícita/reason_codes → adapter existente → bridge direto atual → ComfyUI → output normalizado → lineage → revisão humana → finalização autorizada. Fluxo de coordenação do Codex: Codex → **MCP obrigatório** → ComfyUI.

Na coordenação pelo Codex, MCP cobre saúde/capabilities, validação, submissão, queue/status, cancelamento, inputs/outputs e cleanup autorizado. Sem fallback silencioso para HTTP/CLI/browser pelo Codex. HTTP interno ao servidor MCP é transporte de implementação. Falha do MCP deve bloquear com erro claro; não transformar falha de consulta em fila vazia. Preservar prompt_id/idempotência, escopo local e gates de aprovação. O backend Maestro já envia e acompanha jobs sem depender do Codex; não é necessário criar um monitor do Codex para a geração manual funcionar. Não houve criação de automação nem restart/cleanup.

## K. Files to add — proposta, não implementada

Sob `services/studio/creative_os/`: `ir.py`, `capabilities.py`, `routing.py`, `lineage.py` e `service.py`, com escopo mínimo. `tests`/fixtures de contrato IR e adapter; schema de generation lineage. Não criar bridge MCP interno para o Maestro por causa da regra operacional do Codex. Latent/HQ schemas completos ficam para fase posterior, após contrato de aprovação estabilizado. A regra operacional foi adicionada separadamente a `E:/Pemara/AGENTS.md` por solicitação explícita.

## L. Files to modify — proposta, não implementada

`services/studio/main.py`: conectar camada Creative OS sem reescrever builders. `video_engines/base.py`: complementar normalização quando necessária. `video_engines/h3.py` e `ltx25.py`: tradução IR mantendo pins/perfis. `video_projects.py`: ligação generation/parent/human verdict. `media_assets.py`: resolver de assets/saídas. `MASTER.py` e scripts operacionais mantêm seu transporte atual. UI somente depois dos contratos; registry não ganha AUTO/fallback implicitamente. `FIXLOG.md` registra a entrega documental desta sessão.

## M. Benchmark Plan — não executado

Baseline dos caminhos atuais, com autorização própria para GPU: B01 cenário, B02 produto, B03 humano, B04 interação, B05 combate, B06 pose, B07 fala, B08 first/last, B09 repair, B10 extensão, B11 FL/Ref/Hybrid, B12 direct HQ versus LQ/refine, B13 estabilidade de fila HQ. Marcar SKIPPED_UNAVAILABLE onde faltar modo, em vez de instalar ou substituir engine.

Mínimo três seeds por classe comparável, mesmas referências e duração, configuração hash/versionada, engine/profile explícitos. Capturar cold load, conditioning, warm sampling, decode, mux, total, VRAM/RAM pico e residual. Avaliar identidade, temporal/início-meio-fim, causalidade, contato, props/armas, câmera, áudio e voto humano separado. H3 Production é baseline de 10 steps; Turbo/caches somente A/B isolado posterior. Fila serial, lease GPU, sem liberar outro processo. Critérios sugeridos do pacote: investigar regressão >20% de tempo ou >10% VRAM; qualidade sempre avaliada junto, sem ranking inventado.

## N. Phase 1 Plan — não executado

1. Para a coordenação Codex, resolver a distinção MCP entre estado vivo/histórico e workspace/runtime antes de novas gerações, mantendo pesos/workflows.
2. Preservar a autonomia do backend Maestro e seu transporte direto. Caracterizar contratos existentes de timeout, retomada, cancelamento com alvo, inputs/outputs e isolamento antes da camada Creative OS.
3. Introduzir IR mínimo e tradução determinística para os dois adapters existentes; validar asset IDs, budgets e campos obrigatórios.
4. Persistir generation/parent/engine/workflow hash/prompt_id/output hash/veredito; preservar registros e aprovação existentes.
5. Adicionar analyze/route em modo explícito e somente então conexão da geração autorizada. Não qualificar AUTO por exemplo YAML.
6. Testar contratos sem GPU e executar benchmark real apenas em fase autorizada. Critic/repair e deferred latent HQ vêm depois.

Discovery concluído. STOP para implantação da arquitetura Creative OS. A instrução adicional MCP foi implantada como regra operacional do Codex em AGENTS.md, preservando o envio direto pelo Maestro; não autoriza instalar motores, alterar workflows ou executar benchmarks.
