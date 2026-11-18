# Maestro Pro

## Workflow completo, arquitetura e inventário demonstrativo

**Pemara Tech · Documento técnico-executivo · 18 de agosto de 2026**

> Retrato verificável do sistema Maestro instalado em `E:\Pemara\maestro`, preparado para demonstração. O documento descreve o fluxo vigente, separa componentes ativos de alternativas e histórico, e não contém senhas, tokens ou chaves privadas.

[[PAGEBREAK]]

# 1. Sumário executivo

O Maestro Pro é uma plataforma local de produção multimodal que reúne direção criativa, geração de imagens, edição visual, produção de vídeo por takes, áudio sincronizado, revisão humana, montagem e rastreabilidade. A experiência principal acontece no painel Maestro; a execução é distribuída entre o Studio, o ComfyUI, os modelos locais e ferramentas de acabamento.

O princípio central é simples: **a inteligência artificial produz candidatos; o proprietário aprova o que entra no filme**. Nenhuma imagem, take, faixa de Foley ou master recebe aprovação automática. O sistema preserva originais, bloqueia atalhos que reduzam fidelidade e registra o estado de cada etapa.

No estado verificado em 18/08/2026, o ambiente apresenta:

- build do painel `20260818-hybrid-takes1`;
- Studio ativo em `127.0.0.1:8029`;
- ComfyUI ativo em `127.0.0.1:8188`, sem exposição em `0.0.0.0`;
- MiniMax H3 como motor autorizado de produção de vídeo;
- Qwen Image e Qwen Image Edit para criação e correção de imagens-âncora;
- HunyuanVideo-Foley XXL configurado para Foley sincronizado;
- RIFE 4.6, RealESRGAN x2plus e FFmpeg/NVENC para acabamento após aprovação;
- 300 skills e 35 perfis instalados, com roteamento seletivo por etapa;
- GPU NVIDIA GeForce RTX 5090 com 32.607 MiB de VRAM;
- backup de sistema manifestado em `G:\Pemara_Backups`, com cópia ZIP no Google Drive autenticado.

## O diferencial do workflow

O sistema não tenta gerar um filme inteiro com um prompt longo. A produção é decomposta em takes curtos, cada um com intenção, âncoras, continuidade, movimento e critérios de aprovação. Os takes são classificados como `PRECISION`, `ACTION` ou `PAYOFF`, permitindo que o prompt e o QC cobrem comportamentos diferentes conforme a cena.

O fluxo atual nasceu de problemas reais observados em produção: congelamentos usados como ponte, gestos imprecisos em cenas de fusão, anatomia deformada, impactos fracos e finais sem energia. Essas falhas foram convertidas em regras permanentes: zero crossfade para esconder erro, zero freeze, zero cauda estática, contato físico legível e aprovação explícita antes da montagem.

# 2. Visão geral da arquitetura

[[DIAGRAM:ARCHITECTURE]]

## Camadas do sistema

| Camada | Componente | Responsabilidade |
|---|---|---|
| Experiência | Maestro Web | Login, navegação, projetos, geradores, revisão e aprovação. |
| Orquestração | Studio FastAPI | Jobs assíncronos, contratos de take, filas, persistência, QC e APIs. |
| Inferência | ComfyUI principal | Execução única de workflows de imagem e vídeo na GPU local. |
| Modelos | MiniMax H3, Qwen e auxiliares | Geração de vídeo, âncoras, edição e codificação multimodal. |
| Áudio | HunyuanVideo-Foley e LeVo 2 | Foley sincronizado e pilotos musicais sob revisão humana. |
| Acabamento | FFmpeg, ffprobe, NVENC, RIFE, RealESRGAN | Codec, inspeção, interpolação, upscale e master técnico. |
| Governança | Skills, contratos e aprovação humana | Direção, continuidade, testes, acessibilidade e decisão do proprietário. |
| Continuidade | Manifestos e backups | Hashes, procedência, restauração, rollback e preservação dos originais. |

## Fluxo de acesso

O usuário acessa o Maestro pelo painel autenticado. O frontend chama o Studio pelo proxy interno do próprio Maestro. O Studio conversa com o ComfyUI pela interface local `127.0.0.1:8188`; modelos e arquivos de produção permanecem no computador. O ComfyUI não é um painel público e não deve escutar em todas as interfaces de rede.

O hostname direto da API não é a interface de operação. Rotas sensíveis permanecem protegidas, e o caminho de uso é o painel principal. Essa separação reduz a superfície exposta e mantém decisões de produção dentro da camada autenticada.

# 3. Infraestrutura e versões verificadas

| Item | Estado verificado |
|---|---|
| Sistema de inferência | ComfyUI `0.30.2` |
| Frontend ComfyUI | `1.47.12` |
| Python do ambiente principal | `3.11.9` |
| PyTorch do ComfyUI | `2.13.0+cu130` |
| FFmpeg | `8.1.1 essentials build` |
| GPU | NVIDIA GeForce RTX 5090 |
| VRAM total reportada | 32.607 MiB |
| Driver NVIDIA | `610.88` |
| RAM reportada pelo ComfyUI | aproximadamente 93,6 GiB |
| Build Maestro | `20260818-hybrid-takes1` |
| Política de vídeo | `maestro-minimax-h3-production@2026-08-16` |

Esses números representam o ambiente observado na data do documento. Capacidade livre de RAM e VRAM varia conforme processos ativos; por isso todo job pesado passa por preflight e reserva cooperativa de GPU.

# 4. Inventário funcional do Maestro

## 4.1 Imagem e edição

| Componente | Papel | Estado |
|---|---|---|
| Qwen Image 2512 FP8 | Criação de imagens e frames iniciais | Instalado e padrão para imagem |
| Qwen Image Edit 2511 | Correção de âncoras e edição com referência | Instalado |
| LoRAs locais | Especialização visual e materiais de marketing | 20 arquivos listados pelo Studio |
| Qwen Image VAE e encoder visual | Decodificação e compreensão da referência | Instalados no ComfyUI |

As imagens-âncora são tratadas como elementos de continuidade, não como decoração. Uma âncora aprovada define personagens, roupa, acessórios, estado de poder, iluminação, câmera e composição que o take deve respeitar.

## 4.2 Vídeo

| Componente | Função | Estado de produção |
|---|---|---|
| MiniMax H3 FL2VA pruned INT8 ConvRot | Geração entre primeiro e último frame | Ativo e obrigatório |
| MiniMax H3 Ref2VA pruned INT8 ConvRot | Geração baseada em referências | Instalado; uso depende do contrato do take |
| Qwen3-VL-32B NVFP4/AWQ | Encoder textual e multimodal do H3 | Ativo e obrigatório |
| MiniMax H3 Video VAE FP16 | Decodificação de vídeo | Ativo e obrigatório |
| MiniMax H3 Audio VAE FP32 | Decodificação de áudio nativo | Instalado |
| Wan 2.2 Animate 14B BF16 | Workflow especializado de animação | Instalado, não é o motor primário do contrato atual |

O contrato atual usa H3 com cadência nativa de 24 FPS, 20 steps e guidance 1.0. A entrega em 60 FPS acontece apenas depois da aprovação visual, usando interpolação. Otimizações capazes de alterar fidelidade ficam isoladas em laboratório.

## 4.3 Áudio

| Provider | Uso | Situação |
|---|---|---|
| HunyuanVideo-Foley XXL | Ambiente e impactos sincronizados ao vídeo | Configurado e pronto para piloto |
| LeVo 2 v2-large | Piloto musical local de 5 a 15 segundos | Instalado; runtime sob demanda |
| Google Lyria/Vertex | Música premium em nuvem | Alternativa não configurada no snapshot |
| Stable Audio | Música/SFX | Alvo preferido, depende de endpoint ou chave |
| AudioCraft AudioGen | SFX local experimental | Adaptador preparado, não configurado |
| ElevenLabs Music/SFX | Fallback em nuvem | Adaptador preparado, não configurado |

LeVo 2 é tratado como piloto interno sujeito à licença própria. O runtime sobe somente quando necessário, verifica a GPU e descarrega ao terminar. Foley, música e SFX permanecem candidatos até escuta humana explícita.

## 4.4 Acabamento e inspeção

- `ffprobe`: duração, codec, dimensões, FPS, frames e presença de áudio;
- FFmpeg: concatenação segura, proxy, master, H.264 NVENC, AAC e loudness;
- RIFE 4.6 NCNN Vulkan: interpolação do take aprovado para 60 FPS;
- RealESRGAN x2plus: candidato de upscale somente após aprovação visual;
- contact sheets: inspeção temporal de identidade, física e continuidade;
- EBU R128: medição de loudness do master.

# 5. Workflow de produção em 10 etapas

[[DIAGRAM:WORKFLOW]]

## 5.1 Etapas 1 a 5 — da ideia ao candidato técnico

### 1. Roteiro e contrato de takes

A ideia é convertida em roteiro, sequência e beats de movimento. Cada take recebe intenção, duração, modo, personagens, estado inicial/final e conexão com o próximo. A aprovação do roteiro é um gate do proprietário.

### 2. Fotos-âncora perfeitas

Qwen Image cria a âncora; Qwen Image Edit corrige o que for necessário. O sistema confere elenco, anatomia, roupa, acessórios, pose, cenário e enquadramento. Quando há transformação ou revelação, um end frame aprovado pode ser obrigatório.

### 3. Compilação oficial do prompt H3

A skill oficial local `h3-prompt-writing`, fixada em commit conhecido, transforma a direção criativa em estrutura H3. Ela organiza descrição multimodal, timeline, som e música sem chamar API externa e sem duplicar seções já compiladas.

### 4. Preflight sem GPU

Antes de ocupar a RTX 5090, o Maestro verifica contrato, referências, identidade, câmera, profundidade, progressão e claims de controle. Promessas que o grafo não consegue cumprir são recusadas. Um vídeo de referência não é apresentado como controle articular exato.

### 5. Geração serial MiniMax H3

O job adquire uma lease cooperativa de GPU, confirma fila, memória e arquivos, e produz um candidato nativo. O resultado técnico não é automaticamente aprovado. Preview ao vivo é opcional e não altera sampler, steps, encoder ou saída final.

## 5.2 Etapas 6 a 10 — revisão, áudio e master

### 6. QC visual e aprovação humana

O take passa por ffprobe, contact sheet e revisão integral. São avaliados identidade, roupa, anatomia, peso dos impactos, deslocamento, câmera, movimento interno, começo, meio e final. O proprietário aprova ou reprova.

### 7. Conectores de ação contínua

Quando a ação atravessa cortes, conectores H3 carregam velocidade, direção, posição e consequência física. Crossfade, freeze, hold estático e reset de movimento são proibidos como forma de esconder falha.

### 8. Picture lock e acabamento FHD60

Somente a sequência visual aprovada entra em picture lock. RIFE e RealESRGAN criam candidatos de acabamento; o master nativo aprovado permanece preservado. A codificação usa FFmpeg/NVENC quando o perfil é compatível.

### 9. Foley após picture lock

HunyuanVideo-Foley lê o vídeo e gera ambiente/impactos em WAV 24-bit, 48 kHz, estéreo. O arquivo entra como `candidate_pending_human_listening`; não é anexado nem aprovado automaticamente.

### 10. Master final, hashes e rollback

O sistema concatena somente fontes locais aprovadas, mede o master, registra hashes, proveniência e fingerprint da sequência. O resultado técnico recebe o estado `TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING`. A aprovação final continua sendo do proprietário.

# 6. Modos de take e continuidade

| Modo | Quando usar | O que o prompt prioriza | Falhas que reprovam |
|---|---|---|---|
| `PRECISION` | Gesto icônico, objeto na mão, fusão, coreografia literal | Micro-beats ordenados, posse do objeto, separação dos corpos, anatomia e estado final legível | Objeto flutuando, personagens se aproximando sem motivo, gesto trocado, fusão sem clímax |
| `ACTION` | Pancadaria, perseguição, combate sustentado | Contato forte, recoil, deslocamento, roupa, poeira, detritos e energia atravessando o corte | Socos “fofos”, contato sem reação, corpos colados, anatomia mutante, movimento que zera |
| `PAYOFF` | Transformação, golpe final, revelação, consequência | Escalada, evento decisivo, resposta do ambiente e final ainda em movimento | Transformação sem êxtase, golpe sem consequência, cauda congelada, encerramento anticlimático |

## Contrato de continuidade

Cada take pode carregar:

- `character_topology`: personagens visíveis e proibição de duplicações/mutações;
- `wardrobe_lock`: roupa e acessórios imutáveis;
- `power_state`: estado de entrada e saída;
- `entry_motion` e `exit_motion`: direção, velocidade, objeto e câmera transferidos pelo corte;
- `impact_language`: contato, recoil, deslocamento, roupa, poeira e ambiente;
- `forbidden_transitions`: freeze, crossfade, cauda estática e reset quando houver ação contínua.

O contrato é aditivo e local ao projeto. Aprovações antigas e arquivos existentes não são reescritos destrutivamente.

[[DIAGRAM:APPROVAL]]

# 7. Prompt, controle e limites reais

O compilador local suporta estruturas T2VA, I2VA, L2VA, FL2VA e Ref2VA conforme as referências fornecidas. Em FL2VA, o primeiro frame é posicionado no início e o último frame na duração efetiva. Referências visuais de aparência não devem ser apresentadas como múltiplas âncoras temporais exatas.

Limites declarados:

- o workflow atual não oferece controle de pose articular exato;
- vídeo de referência orienta movimento, mas não equivale a uma entrada formal de pose;
- FL2VA e Ref2VA exigem checkpoints e condicionadores coerentes;
- uma coreografia extremamente precisa deve ser dividida em segmentos adjacentes;
- prompt e seed não substituem um mecanismo de controle inexistente;
- falha de preflight fecha o fluxo antes da GPU, em vez de prometer o impossível.

Essa honestidade de contrato é parte da qualidade: o sistema diferencia o que está instalado, o que está ativo e o que apenas existe como alternativa ou referência histórica.

# 8. Aprovação, montagem e rastreabilidade

## Readiness de montagem

Um take só entra na montagem quando:

1. o visual está `APPROVED` ou `FINAL`;
2. existe vídeo ativo dentro do próprio projeto;
3. não há candidato FHD aguardando revisão;
4. o áudio exigido existe e foi escutado/aprovado;
5. nenhum take está rejeitado, gerando ou aguardando decisão obrigatória.

O endpoint de readiness devolve bloqueios em linguagem estável. Se a sequência aprovada muda, um master anterior é marcado como `stale`, mas seu arquivo continua preservado e disponível para comparação.

## Montagem segura

A montagem utiliza hard cuts e fontes aprovadas. Se streams não forem tecnicamente compatíveis, o job falha de forma fechada, em vez de reduzir resolução, FPS ou qualidade silenciosamente. Um proxy de revisão é separado do master preservado.

As verificações incluem:

- decode integral;
- duração e contagem de frames;
- presença de áudio;
- freeze e cauda estática;
- contato de movimento nas bordas;
- hash e fingerprint das fontes;
- estado técnico separado da aprovação final do proprietário.

# 9. Foley e política de áudio

O contrato Video-to-Sound é independente de modelo. O Studio conhece uma interface de provider, e o HunyuanVideo-Foley XXL é o primeiro adaptador em produção. Novos providers podem ser registrados sem mudar a API ou o frontend.

O provider atual usa:

- pesos em armazenamento dedicado no disco `G:`;
- runtime Docker isolado;
- GPU `cuda:0` com gate mínimo de 24 GB livres;
- proxy visual 512×288 a 24 FPS por NVENC;
- saída WAV PCM 24-bit, 48 kHz, estéreo;
- duração de piloto entre 0,5 e 15 segundos;
- 50 passos no modelo XXL, offline.

O sistema não gera diálogo por este fluxo e não mistura o áudio automaticamente. Reprovação remove o candidato do slot ativo, mas mantém o histórico para auditoria.

# 10. Operação da GPU e segurança de execução

## Lease cooperativa

Jobs pesados registram proprietário, operação, projeto, take, job, horário e heartbeat. A lease não encerra processos arbitrários. Um adaptador pode liberar somente o recurso que ele próprio abriu e confirmou como ocioso. Trabalho ativo ou desconhecido gera bloqueio claro.

## Regras permanentes

- uma única fila principal do ComfyUI;
- ComfyUI em loopback (`127.0.0.1:8188`);
- sem render pesado quando há fila, lease ou janela de GPU restrita;
- sem fallback silencioso para CPU em workflows que exigem GPU;
- sem redução de resolução, FPS, steps ou encoder para “fazer passar”;
- otimizações com risco visual somente em laboratório e com comparação controlada;
- cancelamento limitado ao processo/container do próprio job;
- resultados multimodais sempre pendentes de revisão humana.

## Serviços

| Serviço | Endereço local | Papel |
|---|---|---|
| Maestro Web | `127.0.0.1:9501` | Painel autenticado e proxy |
| Studio | `127.0.0.1:8029` | API e orquestração |
| ComfyUI | `127.0.0.1:8188` | Inferência local |
| LeVo 2 | `127.0.0.1:8190` quando necessário | Música local sob demanda |

Watchdogs mantêm os serviços essenciais e evitam duplicidade. Reinícios devem ser pontuais: não se reinicia ComfyUI para uma mudança exclusiva do Studio quando isso colocaria um job em risco.

# 11. API demonstrativa

| Rota | Demonstração |
|---|---|
| `GET /api/generative/status` | ComfyUI, modelos, providers, defaults e perfil ativo |
| `GET /api/generative/h3/workflow` | Componentes, skills, etapas e prontidão H3 |
| `POST /api/generative/h3/compile-prompt` | Compilação oficial local sem GPU |
| `GET /api/video-projects/{id}/takes/{take}/h3-workflow` | Preflight real do take |
| `GET /api/video-sound/providers` | Providers e capacidades de Foley |
| `POST .../video-sound-jobs` | Criação de piloto de áudio persistente |
| `GET .../assembly-readiness` | Bloqueios e fontes elegíveis para montagem |
| `POST .../assembly-jobs` | Montagem assíncrona de fontes aprovadas |
| `POST .../final-review` | Aprovação ou reprovação explícita do master |

O acesso operacional deve ocorrer pelo painel. Rotas internas não são um convite à exposição pública direta.

# 12. Estudo de caso: Vejito contra Super Boo

O projeto piloto mostrou como a revisão humana melhora o sistema:

## Take de precisão — brincos Potara e fusão

O primeiro problema foi uma sequência gestual confusa: o brinco parava no ar, Vegeta corria para pegá-lo, Goku se aproximava sem necessidade e a fusão surgia sem clímax. O aprendizado foi transformar a cena em `PRECISION`, com micro-beats ordenados, posse explícita do objeto, corpos separados e um payoff de fusão legível.

Microtrechos podem ser usados para preservar fidelidade quando a coreografia literal é mais importante que liberdade de movimento. Eles não devem aparecer como congelamentos acidentais; a transição precisa continuar viva.

## Take de ação — combate

Uma versão foi reprovada porque Super Boo perdeu a topologia e virou uma forma semelhante a um polvo, enquanto os golpes pareciam leves. O modo `ACTION` passou a cobrar contato, recoil, deslocamento, roupa, detritos, consequência ambiental e anatomia estável.

## Take de payoff — transformação e golpe final

O clímax exige escalada: Vejito transforma-se, o ambiente responde e o golpe final ocupa a cena com consequência. O final não pode simplesmente congelar; energia, poeira e câmera devem dissipar naturalmente e deixar margem editorial para o corte.

## Resultado metodológico

As observações foram convertidas no workflow híbrido v1. Em vez de corrigir apenas um vídeo, o Maestro ganhou tipos de take, contratos de continuidade, readiness, montagem segura, detecção de master stale e aprovação final explícita.

# 13. Agentes e skills

O catálogo instalado possui 300 skills e 35 perfis, mas o sistema não executa tudo ao mesmo tempo. Ele roteia o menor grupo competente:

| Área | Skills principais |
|---|---|
| Planejamento e direção | `project-planner`, `creative-director`, `pemara-cinematic-take-director` |
| Âncoras | `image-production` |
| Movimento | `pemara-video-motion-director` |
| Prompt H3 | `h3-prompt-writing` oficial local |
| Vídeo e master | `video-production` |
| Foley e áudio | `game-audio-designer`, `audio-analysis` |
| Qualidade | `test-engineer`, `debugger`, `performance-optimizer` |
| Operação | `automation-engineer`, `documentation-and-adrs` |

Essa seleção reduz conflitos e torna cada saída auditável. Skills aconselham e validam; nenhuma delas substitui os gates humanos.

# 14. Backup, restauração e continuidade

O snapshot mais recente do sistema foi criado em 18/08/2026:

- pasta: `G:\Pemara_Backups\Maestro_Studio_Sistema_20260818_111627`;
- ZIP: `G:\Pemara_Backups\Maestro_Studio_Sistema_20260818_111627.zip`;
- arquivos de payload: 681;
- arquivos verificados pelo manifesto: 686;
- SHA-256: `404B4B0A693ACE82E9F1A608083CEE9A7F1BFE76AA1B75E9D1455A62158519AE`;
- divergências origem/cópia/restauração: zero;
- ZIP enviado ao Google Drive real e baixado novamente para comparação do hash.

O backup de sistema inclui código, configurações públicas, testes, documentação e alterações locais. Por segurança e tamanho, não inclui `.env`, chaves, modelos, projetos, takes, renders, bancos, caches ou ambientes instalados. Pesos possuem instaladores e lockfile separados com origem, revisão, tamanho e SHA-256.

## Restauração segura

1. validar o SHA-256 do ZIP;
2. extrair em pasta vazia;
3. executar `VALIDAR_BACKUP.ps1`;
4. comparar com o Maestro ativo;
5. reinstalar dependências e modelos pelos instaladores travados;
6. restaurar segredos somente por fonte privada autorizada;
7. validar Studio, ComfyUI, APIs e testes;
8. promover somente após aprovação do proprietário.

# 15. Roteiro de demonstração

## Demonstração curta — 8 a 12 minutos

1. Abrir o Maestro e mostrar login/painel.
2. Abrir um projeto de vídeo e explicar a fila de takes.
3. Mostrar os três modos: `PRECISION`, `ACTION` e `PAYOFF`.
4. Abrir o contrato de continuidade de um take.
5. Mostrar âncoras aprovadas e o preflight H3 sem usar GPU.
6. Exibir um take candidato, contact sheet e decisão humana.
7. Mostrar readiness e os bloqueios objetivos da montagem.
8. Exibir Foley como candidato pendente de escuta.
9. Mostrar master técnico separado da aprovação final.
10. Encerrar com manifesto, hash e backup no disco G/Google Drive.

## Mensagem central para o público

> O Maestro não é apenas um botão de geração. É um sistema de produção local que transforma direção criativa em takes controlados, exige evidência técnica, preserva qualidade e mantém o ser humano responsável pela decisão final.

# 16. Escopo, limites e estado atual

## Pronto e demonstrável

- produção por takes com modos e continuidade;
- MiniMax H3 e componentes obrigatórios presentes;
- compilador de prompt oficial local íntegro;
- geração de âncoras com Qwen;
- QC visual e aprovação humana;
- conectores contínuos sem freeze/crossfade/reset;
- montagem segura e master pending owner review;
- HunyuanVideo-Foley configurado;
- backup local e cloud verificado.

## Exige decisão ou condição adicional

- qualquer geração pesada depende de fila e VRAM disponíveis;
- música LeVo 2 permanece piloto interno e sujeita à licença;
- providers em nuvem dependem de configuração própria;
- pose articular exata não é capacidade do contrato H3 atual;
- acabamento FHD60 só ocorre após aprovação visual;
- sucesso técnico não equivale a aprovação artística, comercial ou do proprietário.

## Componentes históricos

Métodos Veo/Kling permanecem como referência de linguagem cinematográfica, não como motores locais. LTX e outros experimentos antigos não são fallback silencioso. O endpoint vivo e o contrato H3 atual são a fonte de verdade operacional.

# 17. Fontes técnicas do documento

- `docs/specs/MAESTRO_HYBRID_TAKE_WORKFLOW_V1.md`
- `docs/MAESTRO_MINIMAX_H3_WORKFLOW.md`
- `docs/MINIMAX_H3_PROMPT_PIPELINE.md`
- `docs/VIDEO_TO_SOUND.md`
- `GERADORES_STUDIO.md`
- `services/studio/h3_workflow.py`
- `services/studio/video_projects.py`
- `services/studio/video_sound.py`
- `tools/model_installers/models.lock.json`
- `app/assets/maestro-build.json`
- APIs locais consultadas em `127.0.0.1:8029` e `127.0.0.1:8188`
- `G:\Pemara_Backups\Maestro_Studio_Sistema_20260818_111627\SNAPSHOT_METADATA.json`

## Nota de confidencialidade

Este PDF é adequado para demonstração técnica controlada. Caminhos locais aparecem para demonstrar rastreabilidade, mas senhas, tokens, cookies, chaves privadas e conteúdos de `.env` foram deliberadamente excluídos.
