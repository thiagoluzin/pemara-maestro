# Plano de implantação — Maestro H3 + LTX 2.5 e ecossistema Turbo

**Estado:** `DEPLOYED — H3_AND_LTX25_PRODUCTION_READY`  
**Data do inventário:** 2026-09-01  
**Implantação:** 2026-09-02  
**Escopo executado:** backup verificado, runtime, código, UI, testes, smoke GPU mínimo autorizado, hardening e consolidação Turbo. A publicação sanitizada do código permanece um gate separado.

## 0. Resultado da implantação

| Frente | Estado em 2026-09-02 | Evidência principal |
|---|---|---|
| Backup anterior às mudanças | `VERIFIED_LEAN_OWNER_SCOPED` | `G:/Pemara_Backups/PRE_CHANGE_FULL_SYSTEM_20260901_204707` |
| ComfyUI | `RUNNING` | v0.34.2 em `127.0.0.1:8188`, runtime isolado |
| PyTorch/CUDA | `RUNNING` | PyTorch 2.14.0+cu130, CUDA runtime 13.0; driver 610.88/toolkit 13.3 |
| MiniMax H3 | `AVAILABLE_WHEN_EXPLICITLY_SELECTED` | adapter preservado, sem prioridade automática |
| LTX 2.5 core | `READY` | assets/revisões presos, workflow API validado no ComfyUI vivo |
| LTX 2.5 produção | `PRODUCTION_READY` | smoke real PASS: 25 quadros, H.264 1920x1088, 24 fps, sem fallback; recibo hash-bound |
| LTX 2.3 engine/runtime | `REMOVED_FROM_ACTIVE_PATH` | sem engine, checkpoint, workflow ou fallback 2.3 ativo |
| IC-LoRAs 2.3 permitidos | `2 VERIFIED / 3 OPTIONAL UNAVAILABLE` | apenas compatibilidade allowlisted de workflows 2.5; três downloads oficiais retornaram 403 |
| Seleção de motor | `REQUIRED` | somente `minimax_h3` e `ltx_2_5`, sem default/fallback |
| Anchor Intelligence | `IMPLEMENTED` | contrato `pemara-anchor-intelligence@1`, compiladores e recibos vinculados a hash |
| Messenger/Agents Turbo | `IMPLEMENTED` | 22 aliases, 13 especializações preservadas, auditor determinístico verde |
| Segurança Maestro × Loja | `PASS` | `E:/Pemara/logs/security_audit/maestro-ltx25-turbo-20260902/release-receipt.json` |
| Regressão consolidada | `PASS` | 233 Maestro + 33 engines/âncoras/auth + 19 gateway + 8 Loja |

O inventário histórico das seções seguintes permanece como trilha de decisão. Quando ele divergir desta seção, o resultado de implantação acima e os receipts atuais prevalecem.

## 1. Overview

Este plano transforma o Maestro em uma plataforma de vídeo com dois motores de primeira classe:

- `MiniMax H3`;
- `LTX 2.5`.

O motor será escolhido explicitamente pelo proprietário em cada nova geração. Não haverá prioridade implícita, seleção automática, fallback silencioso nem troca de motor quando o escolhido estiver indisponível.

O plano também:

1. completa o runtime operacional do LTX 2.5;
2. substitui e remove os consumidores ativos do LTX 2.3;
3. profissionaliza leitura de âncoras, compilação de prompts e validação pré-render;
4. cria o `Pemara Messenger Turbo` como roteador fino de skills;
5. converte agentes duplicados em wrappers de `Agentes Turbo`, sem fundir especialidades apenas parecidas;
6. preserva segurança, rastreabilidade, rollback e aprovação humana.

### 1.1 Decisões já determinadas pelo proprietário

| ID | Decisão imutável para a implantação |
|---|---|
| D-01 | H3 e LTX 2.5 terão o mesmo nível de disponibilidade na interface. |
| D-02 | O proprietário escolhe o motor antes de gerar. |
| D-03 | `engine_id` será obrigatório; não existe motor padrão ou fallback automático. |
| D-04 | LTX 2.3 não poderá permanecer como motor-base, checkpoint, encoder, runtime independente, configuração ou rota de produção. |
| D-05 | O LTX 2.5 será concluído e validado antes da remoção destrutiva final do LTX 2.3. |
| D-06 | Skills realmente idênticas serão canonicamente unificadas pelo Messenger Turbo. |
| D-07 | Agentes realmente idênticos serão convertidos em Agentes Turbo. |
| D-08 | Este documento não autoriza implementação; ela começa apenas após `OK PARA IMPLEMENTAR`. |
| D-09 | IC-LoRAs da linhagem 2.3 exigidos por workflows oficiais LTX 2.5 estão autorizados como assets de compatibilidade, sob allowlist fechada. |

### 1.2 Interpretação segura de “remover tudo do LTX 2.3”

Após aprovação e passagem dos gates, serão removidos do ambiente ativo:

- pesos e artefatos de modelo comprovadamente pertencentes ao LTX 2.3;
- workflows, presets, policies, filas e manifests exclusivos do 2.3;
- código morto e rotas de runtime exclusivas do 2.3;
- opções, labels e documentação ativa que ofereçam o 2.3;
- caches comprovadamente exclusivos do 2.3;
- referências de teste que legitimem o 2.3 como motor disponível.

Não serão apagados por simples correspondência textual:

- vídeos, imagens, projetos ou masters criativos já produzidos;
- backups e recibos de auditoria;
- histórico Git/ADRs históricos;
- bibliotecas genéricas que apenas contenham módulos chamados `ltx`;
- arquivos sem prova de propriedade pelo 2.3;
- artefatos fora dos roots autorizados.

Esses itens só entram numa exclusão adicional mediante inventário de caminhos exatos e autorização explícita. O resultado de produção terá **zero consumidor ativo do motor LTX 2.3**, com a única exceção dos IC-LoRAs de compatibilidade autorizados abaixo.

#### Exceção autorizada: IC-LoRAs 2.3 dentro do LTX 2.5

O proprietário autorizou expressamente o uso dos IC-LoRAs 2.3 necessários aos workflows avançados oficiais LTX 2.5. Cada asset permitido deverá cumprir simultaneamente:

- ser referenciado por um workflow oficial LTX 2.5 selecionado para implantação;
- ter origem oficial, revisão, tamanho e SHA-256 presos no manifest;
- ser classificado como `LTX25_COMPATIBILITY_ASSET`, nunca como engine 2.3;
- ser carregado exclusivamente pelo adapter `ltx_2_5`;
- não instalar checkpoint, encoder, VAE, runtime, rota ou seletor LTX 2.3;
- registrar no receipt qual workflow 2.5 consumiu o asset;
- permanecer removível individualmente sem afetar H3 nem o núcleo LTX 2.5.

Qualquer LoRA/IC-LoRA 2.3 fora dessa allowlist continua proibido.

## 2. Project Type

Projeto híbrido de:

- migração de runtime de IA local;
- arquitetura backend orientada a adapters;
- evolução de frontend e contratos de API;
- engenharia de prompts multimodais;
- hardening e observabilidade;
- refatoração de skills e agentes;
- remoção controlada de tecnologia legada.

## 3. Estado real encontrado

### 3.1 Motores e runtime

| Componente | Estado observado | Classificação de implantação |
|---|---|---|
| MiniMax H3 | Runtime/documentação ativa e fluxo já estabelecido | `READY`, a ser preservado |
| LTX 2.5 transformer NVFP4 | Presente e hash compatível com metadados oficiais | `READY_ASSET` |
| LTX 2.5 Gemma 4 INT8 | Presente e hash compatível | `READY_ASSET` |
| LTX 2.5 video VAE BF16 | Presente e hash compatível | `READY_ASSET` |
| LTX 2.5 audio VAE BF16 | Presente e hash compatível | `READY_ASSET` |
| LTX 2.5 spatial upscaler | Presente e hash compatível | `READY_ASSET` |
| LTX 2.5 duration head | Ausente | `MISSING_REQUIRED` |
| LTX 2.5 temporal upscaler | Ausente | `MISSING_REQUIRED` |
| LTX 2.5 convolutional video VAE | Ausente | `MISSING_RECOMMENDED` |
| ComfyUI-LTXVideo oficial | Ausente no custom_nodes ativo | `MISSING_REQUIRED` |
| Modelos principais LTX 2.3 | Não encontrados nos roots ativos conhecidos | `REMOVED_OR_ABSENT` |
| Código/configuração LTX 2.3 | Referências e ramos legados ainda existem | `LEGACY_CONSUMERS_PRESENT` |

Classificação global atual do LTX 2.5: **`PARTIAL_READY`**. Ele não deve ser anunciado como completo antes dos gates deste plano.

### 3.2 Ambiente observado

- ComfyUI: `0.30.2`, fork local na branch `pemara-v0.30.2-h3` e worktree com alterações;
- Python: `3.11.9`;
- PyTorch: `2.13.0+cu130`;
- GPU: RTX 5090 com aproximadamente 32 GB de VRAM;
- armazenamento: espaço suficiente no root offloaded em `D:` para o perfil planejado;
- fila ComfyUI: vazia no instante do inventário;
- roots de modelos: ComfyUI ativo em `E:` com modelos offloaded em `D:`.

Consequência: nenhuma atualização cega de ComfyUI, `git pull` ou troca de branch será usada. O custom node será instalado separadamente e preso a commit validado.

### 3.3 Inventário de skills e agentes

| Métrica | Resultado |
|---|---:|
| SKILL.md encontrados em `E:\\Pemara\\.agents\\skills` | 302 |
| Perfis em `E:\\Pemara\\.agents\\profiles` | 35 |
| Duplicatas byte a byte entre skills | 0 |
| Duplicatas byte a byte entre perfis | 0 |
| Perfil com skill homônima | 35 |
| Perfil idêntico à skill homônima | 22 |
| Perfil homônimo com conteúdo diferente | 13 |

Conclusão: **não existem hoje skills idênticas entre si nem agentes idênticos entre si que possam ser apagados automaticamente**. Existem 22 cópias exatas entre as camadas `profile` e `skill`; elas são o primeiro alvo seguro para eliminar duplicação de conteúdo, mantendo o nome compatível.

### 3.4 Compatibilidade autorizada para workflows avançados LTX 2.5

Os workflows centrais do LTX 2.5 — T2V/I2V, A2V, T2A e two-stage — podem operar sem o runtime LTX 2.3. Alguns workflows avançados publicados no pacote 2.5 referenciam IC-LoRAs com nome/linhagem 2.3, incluindo controles do tipo Union, V2V/deblur, Ingredients, Motion Track, inpaint e outpaint.

A autorização do proprietário altera a política desta forma:

- os IC-LoRAs exatos exigidos por workflows oficiais 2.5 selecionados **poderão ser instalados**;
- cada um entrará numa allowlist verificável como `LTX25_COMPATIBILITY_ASSET`;
- os modos avançados só serão anunciados depois de asset, workflow, licença e smoke test passarem;
- qualquer outro componente 2.3 continuará `UNAVAILABLE_POLICY_BLOCKED`;
- o Maestro exibirá a dependência de compatibilidade no receipt, sem oferecer um motor LTX 2.3.

Isso permite o conjunto avançado do LTX 2.5 sem reintroduzir o LTX 2.3 como motor escondido.

## 4. Success Criteria

### 4.1 LTX 2.5 completo para produção

O LTX 2.5 só receberá estado `READY` quando todos os itens abaixo passarem:

- manifest oficial com versão, origem, tamanho, SHA-256, licença e root de destino;
- assets obrigatórios íntegros e visíveis pelos loaders reais do ComfyUI;
- `ComfyUI-LTXVideo` instalado em commit preso e compatível com o fork atual;
- workflows centrais oficiais importados e workflows avançados autorizados com IC-LoRAs presos na allowlist de compatibilidade;
- prompt compiler LTX 2.5 e validação de dimensões/frames/duração;
- preflight de RAM, VRAM, armazenamento e fila;
- execução de testes sem GPU;
- smoke tests reais, quando autorizados, com I2V por âncora e ao menos um fluxo de áudio suportado;
- QC técnico e comparação de fidelidade contra o contrato da âncora;
- recibo de versão reproduzível.

Para cada workflow avançado, o estado `READY_WITH_COMPATIBILITY_ASSET` exige que todos os IC-LoRAs consumidos estejam presentes, íntegros, allowlisted e explícitos no receipt.

### 4.2 Paridade H3/LTX 2.5

- ambos aparecem lado a lado no seletor;
- nenhum vem pré-selecionado em projeto novo;
- ambos expõem readiness, capacidades, limites e motivo de bloqueio;
- o job persiste o motor escolhido e sua versão;
- falha do motor escolhido bloqueia o job, sem redirecionamento;
- H3 continua funcional durante toda a migração;
- projetos legados abrem sem serem renderizados automaticamente.

### 4.3 Fidelidade da imagem-âncora

- a âncora passa por leitura visual estruturada antes do prompt;
- intenção do proprietário e evidência visual são confrontadas campo a campo;
- identidade, geometria, cenário, câmera, iluminação e elementos imutáveis viram constraints explícitas;
- contradições geram aviso/solicitação de decisão, não invenção;
- o prompt é compilado para o dialeto do motor escolhido;
- há negative constraints e lista `DO_NOT_INVENT`;
- o render é comparado à âncora por gates técnicos e continua pendente de aprovação humana;
- nenhuma análise técnica equivale a aprovação do proprietário.

### 4.4 Skills e agentes Turbo

- uma fonte canônica por comportamento realmente equivalente;
- `Pemara Messenger Turbo` funciona como roteador fino, não como skill monolítica;
- perfis duplicados viram wrappers mínimos que apontam para skills canônicas;
- especialidades diferentes continuam separadas;
- aliases antigos continuam resolvendo durante a migração;
- nenhum consumidor ativo permanece antes da remoção de um alias;
- todas as skills alteradas passam em `quick_validate` e nos testes comportamentais;
- cada Agent Turbo tem escopo, permissões e skill routing explícitos.

## 5. Tech Stack

### Runtime e modelos

- ComfyUI local, mantendo o fork atual;
- Python 3.11;
- PyTorch/CUDA atuais do ambiente, sem upgrade oportunista;
- LTX 2.5 oficial da Lightricks;
- MiniMax H3 existente;
- armazenamento offloaded em `D:\\PemaraModels\\offloaded\\ComfyUI`;
- instalador canônico existente em `tools/model_installers`.

### Aplicação

- backend Python/FastAPI do Studio/Maestro;
- frontend atual do Maestro em JavaScript/CSS/HTML;
- manifests JSON para engines, modelos e workflows;
- testes Python e contratos de interface existentes;
- logs estruturados e recibos JSON.

### Skills/agentes

- formato `SKILL.md` com progressive disclosure;
- `agents/openai.yaml` para metadata e apresentação;
- profiles mínimos para compatibilidade;
- scripts de auditoria/validação determinísticos;
- skill `Pemara Messenger Turbo` como registro e roteador.

## 6. Arquitetura-alvo

### 6.1 Fluxo de vídeo

```text
Proprietário
   |
   v
Seletor obrigatório: H3 | LTX 2.5
   |
   v
Anchor Intelligence Contract
   |-- leitura visual estruturada
   |-- confronto imagem x intenção
   |-- invariantes e proibições
   |-- plano temporal/câmera/movimento
   v
Prompt Compiler específico do motor
   |
   v
Readiness + Security + Resource Preflight
   |
   +-- falhou -> bloqueio explicado, sem fallback
   |
   v
Adapter H3 ou Adapter LTX 2.5
   |
   v
Candidate -> QC técnico -> PENDING_HUMAN_REVIEW
```

### 6.2 Contrato de engine

Cada adapter implementará, no mínimo:

```text
id
display_name
version_receipt
capabilities
readiness()
validate_request()
compile_prompt()
build_workflow()
estimate_resources()
submit()
inspect_result()
```

Estados canônicos:

```text
READY
PARTIAL
MISSING
REMOVED
QUARANTINED
CATALOG_ONLY
UNAVAILABLE_POLICY_BLOCKED
READY_WITH_COMPATIBILITY_ASSET
```

### 6.3 Contrato de job

Todo job novo terá:

```json
{
  "engine_id": "minimax_h3 | ltx_2_5",
  "engine_version": "resolved-at-submit",
  "anchor_contract_id": "immutable-id",
  "prompt_compiler_version": "version",
  "workflow_id": "versioned-id",
  "resource_profile": "selected-profile",
  "owner_approval_state": "PENDING_HUMAN_REVIEW"
}
```

`engine_id` ausente resulta em `422 ENGINE_SELECTION_REQUIRED`.

### 6.4 Anchor Intelligence Contract

O contrato estruturado deverá separar:

1. **Evidência visível:** personagens, roupas, proporções, pose, objetos, geografia, iluminação, lente aparente, paleta e profundidade.
2. **Intenção declarada:** o que deve acontecer durante o vídeo.
3. **Invariantes:** o que não pode mudar.
4. **Transformações permitidas:** movimentos e mudanças autorizadas.
5. **Restrições negativas:** itens que o motor não pode criar, duplicar, trocar ou estilizar.
6. **Plano temporal:** estado inicial, microações, clímax e estado final.
7. **Plano de câmera:** movimento físico, eixo, lente, enquadramento e continuidade.
8. **Divergências:** conflitos imagem × pedido que exigem decisão.

O prompt final será uma compilação desse contrato, nunca uma descrição livre solta.

### 6.5 Messenger Turbo e Agentes Turbo

```text
Pedido do Maestro/Codex
   |
   v
Pemara Messenger Turbo
   |-- resolve intenção
   |-- consulta mapa canônico
   |-- aplica política Turbo compartilhada
   |-- seleciona a menor combinação de skills
   v
Agente Turbo especializado
   |-- profile mínimo
   |-- permissões explícitas
   |-- skills canônicas
   |-- receipts e validação
```

O Messenger Turbo não incorporará centenas de skills em um arquivo gigante. Ele conterá roteamento, regras compartilhadas e links para módulos especialistas.

## 7. File Structure implantada

Esta estrutura foi criada/atualizada após a autorização de implantação do proprietário.

```text
E:\Pemara\maestro\pemara\
|-- services\studio\
|   |-- video_engines\
|   |   |-- __init__.py
|   |   |-- base.py
|   |   |-- registry.py
|   |   |-- h3.py
|   |   `-- ltx25.py
|   |-- anchor_intelligence\
|   |   |-- schema.py
|   |   |-- analyzer.py
|   |   |-- reconciler.py
|   |   |-- compiler_h3.py
|   |   `-- compiler_ltx25.py
|   |-- video_finishing\
|   |   `-- ...engine-neutral modules...
|   `-- model_readiness.py
|-- ferramentas\video_global_engine\
|   |-- docs\decisions\ADR-006-h3-ltx25-dual-engine.md
|   |-- templates\video_engine_registry.json
|   `-- workflows\ltx25\...pinned official workflows...
|-- tools\model_installers\
|   |-- models.lock.json
|   |-- install_models.py
|   `-- receipts\
|-- tests\
|   |-- test_video_engine_registry.py
|   |-- test_ltx25_adapter.py
|   |-- test_h3_adapter.py
|   |-- test_anchor_intelligence.py
|   |-- test_engine_selection_contract.py
|   `-- test_no_ltx23_engine_consumers.py
`-- app\assets\maestro.js

E:\Pemara\.agents\
|-- skills\pemara-messenger-turbo\
|   |-- SKILL.md
|   |-- agents\openai.yaml
|   |-- references\domain-map.md
|   |-- references\compatibility-map.md
|   `-- scripts\audit_equivalence.py
|-- profiles\...minimal Turbo wrappers...
`-- reports\turbo-consolidation\...receipts...
```

## 8. Manifest LTX 2.5 planejado

### 8.1 Assets já presentes a reaproveitar após nova verificação

| Asset | Bytes | SHA-256 observado |
|---|---:|---|
| `ltx-2.5-22b-distilled-transformer-nvfp4.safetensors` | 18,721,548,408 | `4B94231E734C1950F8F6826CB8BD8715D94BE5B3E04F8256EE060C5BC3886C30` |
| `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors` | 15,372,969,374 | `6CE688A0AA98A5FA36A9F1E6C3F42152A498CC2B53EE8C15674C64244F91487F` |
| video VAE BF16 | 1,472,223,346 | `847E14CA7F3355DEBCA0CEA4EAA24AC0FBCDF0061DA054AC89CA638A869DDBA3` |
| audio VAE BF16 | 364,866,540 | `C52733D37F6A7FB7949C3DC0FB468C6CB2169E4D836983A73BABB9F0D54837A5` |
| spatial upscaler | 995,778,752 | `EB5A71FE4068EE87CCDB1C3AA635E547CA76BD2D30AE20AE889F2C325C0677E8` |

### 8.2 Assets faltantes obrigatórios/recomendados

| Asset | Bytes | SHA-256 oficial levantado | Tratamento |
|---|---:|---|---|
| duration head | 3,843,690 | `2ec71e4206ed365d015f00c05a48caccfb0ee862986809d06ae376c09f5d9190` | obrigatório |
| temporal upscaler | 261,944,000 | `2bc3300f2b3c3c1834d72164fbf13a3b9fd73e5a741e8a2c3f4035f89a75c3fe` | obrigatório para two-stage completo |
| convolutional video VAE | 1,452,269,922 | `685b06ee3d9b2039647698fc4ea33175112462fc374e2777312c907897dfce8d` | recomendado/perfil de VRAM |

### 8.3 Perfis de execução

| Perfil | Uso | Política |
|---|---|---|
| `quality-reference-bf16` | baseline oficial de qualidade e comparação | instalar somente assets oficiais previstos no manifest; pode exigir mais armazenamento/tempo |
| `rtx5090-performance-nvfp4-int8` | operação otimizada na RTX 5090 | usa assets já presentes; só recebe selo de produção após A/B contra baseline |

O perfil otimizado não será promovido apenas por ser mais rápido. A comparação deverá medir fidelidade de identidade, geometria, cor, detalhe e movimento.

### 8.4 Revisions a prender no receipt

- modelo Hugging Face observado: `e8dc69fd26150afbfa20351f6bc9ac384257f9fd`;
- `ComfyUI-LTXVideo`: `15d09abb5a187a8dcaea2fc31fe51ee96e6c9d0d`;
- repositório `LTX-2`: `a95ab856bf29407b6b066ede0abe1846050db56c`.

Antes de implementar, as revisions serão reconfirmadas oficialmente e permanecerão presas durante toda a rodada. Mudança posterior será outro change request.

### 8.5 Allowlist de IC-LoRAs de compatibilidade

A allowlist será derivada dos workflows oficiais LTX 2.5 efetivamente implantados. Para cada IC-LoRA, o lock deverá registrar:

```text
asset_id
classification = LTX25_COMPATIBILITY_ASSET
official_source
source_revision
filename
size_bytes
sha256
consuming_ltx25_workflows[]
license_receipt
install_root
```

O instalador recusará qualquer IC-LoRA 2.3 não presente nessa allowlist e nenhum desses assets poderá registrar `engine_id = ltx_2_3`.

## 9. API e interface

### 9.1 Endpoints planejados

```text
GET  /api/generative/video-engines
GET  /api/generative/video-engines/{engine_id}/readiness
POST /api/generative/video-engines/{engine_id}/compile-prompt
POST /api/generative/video-engines/{engine_id}/preflight
POST /api/generative/video-jobs
GET  /api/generative/video-jobs/{job_id}/receipt
```

### 9.2 Seletor no Maestro

Na área `Criar > Vídeo`:

- cards equivalentes para `MiniMax H3` e `LTX 2.5`;
- nenhum card selecionado ao abrir projeto novo;
- readiness atualizado e causa legível de bloqueio;
- capacidades visíveis: I2V/T2V/áudio/resolução/duração/perfil;
- o botão de gerar fica bloqueado até escolha explícita;
- troca de motor recompila o prompt e invalida o preflight anterior;
- o recibo do job mostra motor, versão, workflow, prompt compiler e hashes.

Projetos legados sem `engine_id` abrirão em modo compatível/read-only. O sistema poderá sugerir o motor com base nos metadados, mas exigirá confirmação do proprietário antes de qualquer novo render.

## 10. Consolidação Turbo

### 10.1 Regra de equivalência

Uma fusão automática só é permitida quando todos os itens forem verdadeiros:

- mesma finalidade operacional;
- mesmas entradas e saídas;
- mesmas permissões e riscos;
- mesmos gates de aprovação;
- comportamento equivalente nos testes;
- ausência de dependência/licença que exija isolamento;
- compatibilidade reversível para consumidores antigos.

Sem isso, os itens são apenas relacionados e continuam separados.

### 10.2 Classes de achado

| Classe | Ação |
|---|---|
| Byte a byte idêntico na mesma camada | escolher canônico, criar alias, migrar consumidores, remover cópia após zero uso |
| Profile idêntico à skill homônima | substituir profile por wrapper Turbo mínimo apontando à skill |
| Similaridade semântica alta | forward test + revisão; fundir apenas se comportamento e riscos forem equivalentes |
| Boilerplate Turbo repetido | extrair política compartilhada e referenciar, mantendo lógica de domínio local |
| Vendor/NVIDIA/TAO/NeMo | manter isolado do first-party Pemara por versão, licença e atualização |

### 10.3 Clusters candidatos a auditoria, não a fusão automática

- QA: `test-engineer`, `qa-automation-engineer`, `test-driven-development`, `code-review-and-quality`;
- performance/diagnóstico: `performance-optimizer`, `performance-optimization`, `debugger`, `debugging-and-error-recovery`;
- planejamento: `project-planner`, `planning-and-task-breakdown`, `spec-driven-development`;
- imagem: `image-production`, `sprite-image-reading`, `modern-pixel-art-hd`;
- vídeo: `video-production`, `animation-engineer`, `pemara-video-motion-director`, `ai-video-intro-pipeline`;
- segurança: `pemara-online-security-guardian`, `security-and-hardening`, `saas-pentest-hardening`;
- Phaser/animação: skills Phaser e sprite associadas.

Esses clusters provavelmente contêm funções complementares. O nome parecido não autoriza apagamento.

### 10.4 Os 22 profiles que podem virar wrappers mínimos

```text
animation-engineer
audio-analysis
automation-engineer
balance-tuner
beatemup-combat-designer
claude-context-audit
code-archaeologist
debugger
demo-release-engineer
game-audio-designer
game-audio-reactive
game-build-flow
gamepad-input-specialist
level-designer
modern-pixel-art-hd
pack-doctor
performance-optimizer
project-planner
qa-automation-engineer
test-engineer
vanilla-web-patterns
web-frontend-vanilla
```

Os 13 pares homônimos diferentes serão revisados manualmente; não serão sobrescritos.

## 11. Task Breakdown

Cada tarefa é pequena, verificável e reversível. `Agent` indica o papel recomendado para execução, não autorização para criar um agente externo.

### Phase 0 — Congelamento, inventário e proteção

#### Task P0-01 — Receipt do estado inicial

- **task_id:** `P0-01`
- **name:** congelar versões e hashes do ambiente
- **agent:** code-archaeologist
- **skills:** code-archaeologist, git-workflow-and-versioning
- **priority:** P0
- **dependencies:** nenhuma
- **INPUT:** worktrees, roots ComfyUI/modelos, services, UI, skills e profiles
- **OUTPUT:** receipt JSON/Markdown com commits, dirty state, hashes, espaço, GPU, fila e processos
- **VERIFY:** receipt reproduz os caminhos e não altera arquivos/runtimes

#### Task P0-02 — Backup e rollback exatos

- **task_id:** `P0-02`
- **name:** criar backup pré-migração com manifest
- **agent:** pemara-online-security-guardian
- **skills:** pemara-online-security-guardian, security-and-hardening
- **priority:** P0
- **dependencies:** P0-01, `OK PARA IMPLEMENTAR`
- **INPUT:** lista exata de arquivos que serão alterados/removidos
- **OUTPUT:** backup versionado em root aprovado, manifest SHA-256 e instrução de restore
- **VERIFY:** restore de amostra em diretório temporário e comparação de hashes

#### Task P0-03 — Gate de segurança/licença

- **task_id:** `P0-03`
- **name:** validar origem, licença e superfície local
- **agent:** pemara-online-security-guardian
- **skills:** pemara-online-security-guardian, source-driven-development
- **priority:** P0
- **dependencies:** P0-01
- **INPUT:** URLs oficiais, commits, licença LTX, bindings do Maestro/ComfyUI
- **OUTPUT:** allowlist, receipt de licença e mapa de bindings/autenticação
- **VERIFY:** nenhum endpoint novo público; todos os downloads têm origem e revisão presas

**Phase 0 verification:** nenhum arquivo de produção removido; backup restaurável; escopo destrutivo fechado por paths exatos.

### Phase 1 — Arquitetura dual sem mudar comportamento H3

#### Task E1-01 — ADR dual-engine

- **task_id:** `E1-01`
- **name:** registrar ADR-006
- **agent:** project-planner
- **skills:** documentation-and-adrs, api-and-interface-design
- **priority:** P0
- **dependencies:** P0-01
- **INPUT:** ADR-004, decisões D-01 a D-08
- **OUTPUT:** ADR-006 que substitui a decisão de motor único sem apagar a história
- **VERIFY:** ADR explicita seleção obrigatória, ausência de fallback e gates

#### Task E1-02 — Contrato e registro de engines

- **task_id:** `E1-02`
- **name:** criar interface de adapter e registry
- **agent:** code-archaeologist
- **skills:** api-and-interface-design, incremental-implementation
- **priority:** P0
- **dependencies:** E1-01
- **INPUT:** fluxos H3 e LTX legados
- **OUTPUT:** `base.py`, `registry.py`, estados e schemas canônicos
- **VERIFY:** unit tests provam que `engine_id` é obrigatório e fallback é impossível

#### Task E1-03 — Encapsular H3

- **task_id:** `E1-03`
- **name:** adaptar H3 ao novo contrato sem regressão
- **agent:** debugger
- **skills:** debugging-and-error-recovery, test-driven-development
- **priority:** P0
- **dependencies:** E1-02
- **INPUT:** fluxo H3 atual
- **OUTPUT:** adapter H3 e testes de compatibilidade
- **VERIFY:** mesmos requests válidos produzem workflow/receipt equivalente; nenhum render necessário

**Phase 1 verification:** H3 continua disponível; LTX 2.5 ainda não é anunciado como pronto; APIs recusam job sem escolha.

### Phase 2 — Instalação completa e reproduzível do LTX 2.5

#### Task L2-01 — Expandir o instalador canônico

- **task_id:** `L2-01`
- **name:** adicionar componente `ltx25` ao model installer
- **agent:** automation-engineer
- **skills:** automation-engineer, security-and-hardening
- **priority:** P0
- **dependencies:** P0-02, P0-03
- **INPUT:** `install_models.py`, `models.lock.json`, manifest da seção 8
- **OUTPUT:** preflight/install/verify/dry-run com allowlist, hashes e quarantine
- **VERIFY:** dry-run não baixa nada; arquivos existentes são verificados e não duplicados

#### Task L2-02 — Instalar assets faltantes

- **task_id:** `L2-02`
- **name:** concluir o manifest LTX 2.5
- **agent:** automation-engineer
- **skills:** automation-engineer, deprecation-and-migration
- **priority:** P0
- **dependencies:** L2-01, `OK PARA IMPLEMENTAR`
- **INPUT:** manifest preso e storage preflight
- **OUTPUT:** duration head, temporal upscaler, conv VAE e baseline aprovado
- **VERIFY:** tamanho + SHA-256 + leitura pelos loaders reais; inválidos vão para quarantine

#### Task L2-03 — Instalar custom node preso

- **task_id:** `L2-03`
- **name:** instalar ComfyUI-LTXVideo isoladamente
- **agent:** automation-engineer
- **skills:** source-driven-development, debugging-and-error-recovery
- **priority:** P0
- **dependencies:** P0-02, P0-03
- **INPUT:** commit oficial preso e fork ComfyUI atual
- **OUTPUT:** custom node + lock/receipt sem atualizar o ComfyUI inteiro
- **VERIFY:** import em processo de teste, node list esperada e nenhuma alteração fora do diretório autorizado

#### Task L2-03A — Fechar allowlist de IC-LoRAs de compatibilidade

- **task_id:** `L2-03A`
- **name:** catalogar IC-LoRAs 2.3 exigidos pelo LTX 2.5
- **agent:** code-archaeologist
- **skills:** source-driven-development, security-and-hardening
- **priority:** P0
- **dependencies:** P0-03, L2-03
- **INPUT:** workflows oficiais LTX 2.5 selecionados e repositórios oficiais presos
- **OUTPUT:** allowlist com origem, revisão, licença, tamanho, SHA-256 e workflows consumidores
- **VERIFY:** cada asset é necessário a um workflow 2.5, não registra engine 2.3 e qualquer arquivo fora da lista é recusado

#### Task L2-04 — Importar workflows LTX 2.5 autorizados

- **task_id:** `L2-04`
- **name:** versionar workflows LTX 2.5 autorizados
- **agent:** animation-engineer
- **skills:** animation-engineer, source-driven-development
- **priority:** P1
- **dependencies:** L2-02, L2-03, L2-03A
- **INPUT:** catálogo oficial 2.5
- **OUTPUT:** T2V/I2V, two-stage, A2V, T2A e modos avançados selecionados com manifest de capabilities
- **VERIFY:** scanner aceita somente IC-LoRAs `LTX25_COMPATIBILITY_ASSET` allowlisted e recusa qualquer outra dependência 2.3

#### Task L2-05 — Adapter e prompt compiler LTX 2.5

- **task_id:** `L2-05`
- **name:** implementar adapter LTX 2.5
- **agent:** animation-engineer
- **skills:** animation-engineer, pemara-video-motion-director
- **priority:** P0
- **dependencies:** E1-02, L2-04
- **INPUT:** contrato de engine, workflows e limites oficiais
- **OUTPUT:** adapter, compiler, resource profiles e receipt
- **VERIFY:** testes de schema, frames `8n+1`, dimensões válidas, áudio e preflight; sem GPU

**Phase 2 verification:** todos os assets obrigatórios verificados; IC-LoRAs permitidos registrados como compatibilidade; qualquer componente 2.3 fora da allowlist permanece bloqueado; readiness pode chegar a `READY_FOR_GPU_SMOKE`, não a `PRODUCTION_READY`.

### Phase 3 — Inteligência de âncora e prompts

#### Task A3-01 — Schema de leitura da âncora

- **task_id:** `A3-01`
- **name:** criar Anchor Intelligence Contract
- **agent:** creative-director
- **skills:** creative-director, image-production, context-engineering
- **priority:** P0
- **dependencies:** E1-02
- **INPUT:** imagem-âncora e intenção textual do proprietário
- **OUTPUT:** JSON versionado com evidências, invariantes, transformações e divergências
- **VERIFY:** fixtures cobrem identidade, pose, cenário, câmera, texto e objetos; campos ausentes não são inventados

#### Task A3-02 — Reconciliação imagem × intenção

- **task_id:** `A3-02`
- **name:** detectar conflitos e montar constraints
- **agent:** creative-director
- **skills:** doubt-driven-development, pemara-cinematic-take-director
- **priority:** P0
- **dependencies:** A3-01
- **INPUT:** anchor contract e pedido do usuário
- **OUTPUT:** briefing reconciliado + `DO_NOT_INVENT` + itens que exigem decisão
- **VERIFY:** pedidos contraditórios bloqueiam compilação em vez de serem resolvidos por suposição

#### Task A3-03 — Compiladores específicos H3/LTX 2.5

- **task_id:** `A3-03`
- **name:** gerar prompts no dialeto de cada motor
- **agent:** pemara-video-motion-director
- **skills:** pemara-video-motion-director, context-engineering
- **priority:** P0
- **dependencies:** A3-02, E1-03, L2-05
- **INPUT:** briefing reconciliado e capabilities do motor
- **OUTPUT:** prompt positivo, constraints negativas, plano temporal e parâmetros estruturais
- **VERIFY:** golden tests; mesmo contrato mantém invariantes e adapta apenas sintaxe/capacidade do motor

#### Task A3-04 — Gate pós-render de fidelidade

- **task_id:** `A3-04`
- **name:** comparar candidato com âncora
- **agent:** qa-automation-engineer
- **skills:** qa-automation-engineer, code-review-and-quality
- **priority:** P1
- **dependencies:** A3-03
- **INPUT:** âncora, contrato, frames amostrados e receipt do job
- **OUTPUT:** relatório por identidade/geometria/paleta/cenário/movimento
- **VERIFY:** falha técnica impede promoção; aprovação final continua exclusivamente humana

**Phase 3 verification:** prompts são rastreáveis ao contrato; contradições não viram alucinação; os dois motores recebem adaptação própria.

### Phase 4 — API, persistência e interface

#### Task U4-01 — API/readiness/jobs

- **task_id:** `U4-01`
- **name:** expor engines e persistir escolha
- **agent:** debugger
- **skills:** api-and-interface-design, test-driven-development
- **priority:** P0
- **dependencies:** E1-03, L2-05, A3-03
- **INPUT:** adapters e schemas
- **OUTPUT:** endpoints da seção 9 e migração de job/project
- **VERIFY:** testes 200/409/422, idempotência e ausência de fallback

#### Task U4-02 — Seletor explícito

- **task_id:** `U4-02`
- **name:** criar cards H3/LTX 2.5
- **agent:** frontend-ui-engineering
- **skills:** frontend-ui-engineering, browser-testing-with-devtools
- **priority:** P0
- **dependencies:** U4-01
- **INPUT:** API de capabilities/readiness
- **OUTPUT:** seletor acessível, sem pré-seleção, com bloqueios explicados
- **VERIFY:** testes DOM/E2E cobrem seleção, troca, indisponibilidade e refresh

#### Task U4-03 — Compatibilidade de projetos antigos

- **task_id:** `U4-03`
- **name:** migrar metadados sem render automático
- **agent:** code-archaeologist
- **skills:** deprecation-and-migration, data-designer
- **priority:** P1
- **dependencies:** U4-01
- **INPUT:** projetos sem `engine_id` e metadados históricos
- **OUTPUT:** sugestão auditável, estado read-only e confirmação requerida
- **VERIFY:** nenhum projeto antigo ganha motor silenciosamente; mídia original preservada

**Phase 4 verification:** usuário escolhe o motor; o job e a UI exibem exatamente o escolhido; estados sobrevivem a reload.

### Phase 5 — Messenger Turbo e Agentes Turbo

#### Task T5-01 — Auditoria determinística de equivalência

- **task_id:** `T5-01`
- **name:** gerar relatório exato, normalizado e semântico
- **agent:** pack-doctor
- **skills:** pack-doctor, code-simplification
- **priority:** P0
- **dependencies:** P0-02
- **INPUT:** todas as skills, profiles, metadata e consumidores
- **OUTPUT:** matriz de hashes, aliases, imports, clusters e riscos
- **VERIFY:** contagens fecham com inventário; nenhuma fusão é aplicada pelo relatório

#### Task T5-02 — Criar Pemara Messenger Turbo

- **task_id:** `T5-02`
- **name:** criar roteador canônico fino
- **agent:** automation-engineer
- **skills:** skill-creator, context-engineering
- **priority:** P0
- **dependencies:** T5-01
- **INPUT:** matriz aprovada e mapa de domínio
- **OUTPUT:** SKILL.md pequeno, references, script de auditoria e `agents/openai.yaml`
- **VERIFY:** roteamento seleciona a menor combinação correta e não vira catchall

#### Task T5-03 — Converter 22 profiles duplicados

- **task_id:** `T5-03`
- **name:** criar wrappers de Agentes Turbo
- **agent:** automation-engineer
- **skills:** skill-creator, deprecation-and-migration
- **priority:** P0
- **dependencies:** T5-02
- **INPUT:** lista da seção 10.4
- **OUTPUT:** profiles mínimos, aliases e mapa de compatibilidade
- **VERIFY:** nomes antigos continuam invocáveis e comportamento passa em forward tests

#### Task T5-04 — Revisar os 13 pares divergentes

- **task_id:** `T5-04`
- **name:** preservar ou consolidar com prova
- **agent:** code-archaeologist
- **skills:** code-archaeologist, doubt-driven-development
- **priority:** P1
- **dependencies:** T5-01
- **INPUT:** diff de cada par homônimo
- **OUTPUT:** decisão `KEEP_SEPARATE`, `MERGE`, `PROFILE_ONLY` ou `DEPRECATE`
- **VERIFY:** cada decisão registra permissões, perdas possíveis e teste comportamental

#### Task T5-05 — Extrair boilerplate e profissionalizar metadata

- **task_id:** `T5-05`
- **name:** reduzir repetição sem apagar domínio
- **agent:** code-simplification
- **skills:** code-simplification, skill-creator
- **priority:** P1
- **dependencies:** T5-02, T5-04
- **INPUT:** políticas Turbo repetidas e skills grandes
- **OUTPUT:** referências compartilhadas, skills menores e `openai.yaml` nas skills canônicas
- **VERIFY:** `quick_validate`, pack-doctor e diff comportamental aprovados

#### Task T5-06 — Remover aliases somente após zero uso

- **task_id:** `T5-06`
- **name:** concluir depreciação Turbo
- **agent:** pack-doctor
- **skills:** deprecation-and-migration, pack-doctor
- **priority:** P2
- **dependencies:** T5-03, T5-04, T5-05
- **INPUT:** telemetria/scan de consumidores e janela de compatibilidade
- **OUTPUT:** remoção apenas de duplicatas provadas e receipt de zero consumidores
- **VERIFY:** chamadas antigas falham apenas quando formalmente retiradas; rollback restaura wrappers

**Phase 5 verification:** nenhum domínio diferente foi fundido; todos os nomes migrados têm compatibilidade; contagem e mapa canônico são reproduzíveis.

### Phase 6 — Retirada do LTX 2.3

#### Task R6-01 — Scanner de consumidores 2.3

- **task_id:** `R6-01`
- **name:** provar zero uso antes de apagar
- **agent:** code-archaeologist
- **skills:** deprecation-and-migration, code-archaeologist
- **priority:** P0
- **dependencies:** L2-05, U4-03
- **INPUT:** código, configs, jobs, UI, registries, roots de modelos e workflows
- **OUTPUT:** manifest `active_engine_23`, `approved_compatibility_asset`, `historical`, `unrelated`, `candidate_for_removal`
- **VERIFY:** cada candidato tem path absoluto, hash, proprietário e consumidor; scan bounded em todos os roots conhecidos

#### Task R6-02 — Remover consumidores ativos

- **task_id:** `R6-02`
- **name:** eliminar código/configuração LTX 2.3
- **agent:** debugger
- **skills:** deprecation-and-migration, test-driven-development
- **priority:** P0
- **dependencies:** R6-01, LTX 2.5 `READY_FOR_GPU_SMOKE`
- **INPUT:** manifest aprovado e adapters novos
- **OUTPUT:** remoção de branches, routes, tests, UI e registries exclusivos do 2.3
- **VERIFY:** suite `test_no_ltx23_engine_consumers.py`, busca estrutural e testes H3/LTX 2.5; IC-LoRAs allowlisted só resolvem via adapter 2.5

#### Task R6-03 — Remover assets comprovados

- **task_id:** `R6-03`
- **name:** excluir assets LTX 2.3 não autorizados
- **agent:** pemara-online-security-guardian
- **skills:** pemara-online-security-guardian, deprecation-and-migration
- **priority:** P0
- **dependencies:** R6-01, R6-02, backup restaurável
- **INPUT:** lista absoluta aprovada e allowlist de compatibilidade; nenhum glob destrutivo
- **OUTPUT:** remoção exata e recibo de paths/hashes, preservando somente os IC-LoRAs allowlisted
- **VERIFY:** roots resolvidos permanecem dentro do escopo; registry não oferece engine 2.3; compatibility assets coincidem com a allowlist; backup continua íntegro

#### Task R6-04 — Atualizar documentação ativa

- **task_id:** `R6-04`
- **name:** declarar somente H3 + LTX 2.5
- **agent:** project-planner
- **skills:** documentation-and-adrs
- **priority:** P1
- **dependencies:** R6-02
- **INPUT:** docs/ADRs/registry atuais
- **OUTPUT:** documentação ativa coerente; ADR histórico marcado como superseded
- **VERIFY:** nenhum guia operacional oferece 2.3; histórico não é falsificado

**Phase 6 verification:** zero consumidor do motor 2.3 e zero asset 2.3 não autorizado; somente IC-LoRAs allowlisted permanecem como dependências explícitas do LTX 2.5; H3 continua íntegro; mídia histórica não foi apagada.

### Phase 7 — Testes, GPU smoke e promoção

#### Task V7-01 — Suite sem GPU

- **task_id:** `V7-01`
- **name:** executar testes unitários, contratos e segurança
- **agent:** test-engineer
- **skills:** test-engineer, security-and-hardening
- **priority:** P0
- **dependencies:** fases 1 a 6
- **INPUT:** código consolidado
- **OUTPUT:** relatório de testes, cobertura de fallback, readiness e zero 2.3
- **VERIFY:** todos os testes críticos verdes e nenhum binding público novo

#### Task V7-02 — Smoke tests GPU controlados

- **task_id:** `V7-02`
- **name:** testar H3 e LTX 2.5 com inputs equivalentes
- **agent:** animation-engineer
- **skills:** amc-run-video-calibration, pemara-video-motion-director
- **priority:** P0
- **dependencies:** V7-01, `OK PARA SMOKE GPU`, preflight GPU ao vivo
- **INPUT:** uma âncora aprovada, mesmo briefing e profiles definidos
- **OUTPUT:** candidatos separados, receipts, métricas e QC
- **VERIFY:** motor correto em cada job; sem fallback; comparação de fidelidade; estado `PENDING_HUMAN_REVIEW`

#### Task V7-03 — Promoção e rollback drill

- **task_id:** `V7-03`
- **name:** promover versão e provar retorno
- **agent:** demo-release-engineer
- **skills:** shipping-and-launch, observability-and-instrumentation
- **priority:** P0
- **dependencies:** V7-02, aprovação humana dos resultados técnicos
- **INPUT:** release candidate e backup
- **OUTPUT:** receipt final, changelog, health checks e procedimento de rollback
- **VERIFY:** restore do registro/config em ambiente controlado; UI/API voltam ao estado anterior sem perder projetos

**Phase 7 verification:** ambos os motores foram acionados explicitamente; resultados permanecem candidatos; produção só recebe a versão após aprovação humana.

## 12. Dependency Graph

```text
P0-01 -> P0-02 -> L2-01 -> L2-02
   |        |          \-> L2-03 -> L2-03A -> L2-04 -> L2-05
   |        \-> T5-01 -> T5-02 -> T5-03/T5-04 -> T5-05 -> T5-06
   \-> E1-01 -> E1-02 -> E1-03
                    \-> A3-01 -> A3-02 -> A3-03 -> A3-04

E1-03 + L2-05 + A3-03 -> U4-01 -> U4-02/U4-03
L2-05 + U4-03 -> R6-01 -> R6-02 -> R6-03/R6-04
Phases 1-6 -> V7-01 -> [OK GPU] -> V7-02 -> V7-03
```

## 13. Test Matrix

| Área | Caso mínimo | Resultado esperado |
|---|---|---|
| Engine selector | nenhum motor selecionado | geração bloqueada |
| Engine selector | H3 selecionado | somente adapter H3 chamado |
| Engine selector | LTX 2.5 selecionado | somente adapter LTX 2.5 chamado |
| Readiness | engine indisponível | erro explicado, zero fallback |
| Anchor | conflito entre imagem e intenção | compilação bloqueada/decisão solicitada |
| Anchor | invariantes válidos | presentes no prompt e QC |
| LTX manifest | hash incorreto | quarantine e estado `QUARANTINED` |
| LTX workflow | IC-LoRA 2.3 allowlisted | aceito como `LTX25_COMPATIBILITY_ASSET` e registrado no receipt |
| LTX workflow | componente 2.3 fora da allowlist | workflow recusado |
| Legacy project | sem engine_id | read-only + confirmação |
| LTX 2.3 | scanner pós-migração | zero engine/runtime 2.3; somente compatibility assets autorizados |
| Skill exact duplicate | mesma semântica | alias + canônico + forward test |
| Skill related-only | domínios diferentes | `KEEP_SEPARATE` |
| Agent wrapper | nome antigo | resolve para Agent Turbo correto |
| Security | binding externo inesperado | gate falha |
| GPU | VRAM insuficiente/fila ocupada | job não é submetido |
| Approval | QC técnico verde | continua `PENDING_HUMAN_REVIEW` |

## 14. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Atualizar o fork ComfyUI e quebrar H3 | alto | não fazer pull global; instalar node preso e testar isolado |
| Remover arquivo “ltx” que não é 2.3 | alto | ownership por manifest, path e consumidor; nenhum delete por nome |
| LTX 2.5 otimizado perder fidelidade | alto | baseline BF16 + A/B antes de promoção |
| IC-LoRA 2.3 reintroduzir dependência escondida | médio/alto | allowlist fechada, hash/receipt, carregamento exclusivo pelo adapter 2.5 e ausência de engine 2.3 |
| Fallback silencioso mascarar erro | alto | engine obrigatório e registry sem fallback |
| Prompt livre inventar detalhes | alto | contrato de âncora + constraints + divergência explícita |
| Fundir skills apenas pelo nome | alto | equivalência comportamental e permissões obrigatórias |
| Messenger Turbo virar catchall | médio/alto | roteador pequeno com progressive disclosure |
| Apagar histórico/artefatos criativos | alto | excluir só runtime ativo; autorização separada para mídia/backups |
| Render competir com GPU em uso | alto | snapshot ao vivo e `OK PARA SMOKE GPU` separado |
| Licença/modelo mudar na origem | médio | revision pin, receipt e nova aprovação para upgrades |

## 15. Gates de autorização

### Gate A — `OK PARA IMPLEMENTAR`

Autoriza:

- backups e receipts;
- alterações de código, testes, documentação e UI descritas neste plano;
- downloads/instalação dos assets exatos do manifest aprovado;
- instalação dos IC-LoRAs 2.3 presentes na allowlist de compatibilidade LTX 2.5;
- criação do Messenger Turbo e wrappers de Agentes Turbo;
- remoção de consumidores/ativos LTX 2.3 somente depois dos gates técnicos e com paths exatos.

Não autoriza:

- render GPU;
- publicação externa;
- apagar mídia criativa, projetos, masters, histórico Git ou backups;
- instalar qualquer checkpoint, encoder, VAE, runtime, workflow independente ou IC-LoRA 2.3 fora da allowlist;
- upgrades gerais de ComfyUI/PyTorch/CUDA fora do escopo.

### Gate B — `OK PARA SMOKE GPU`

Autoriza apenas os renders curtos, inputs, duração, resolução e número de tentativas especificados no preflight apresentado imediatamente antes da execução.

### Gate C — aprovação humana

Promove a configuração/candidato exato revisado. Aprovação de uma âncora, de um motor ou de um teste não transfere aprovação para outro artefato.

## 16. Ordem de rollback

1. bloquear submissões novas sem interromper arquivos em disco;
2. restaurar registry/API/UI anteriores pelo backup manifestado;
3. reativar o adapter H3 conhecido como estável;
4. desabilitar o adapter LTX 2.5 sem apagar seus assets;
5. restaurar wrappers/aliases Turbo;
6. validar projetos, jobs e mídia por hashes;
7. só depois decidir limpeza do release candidate defeituoso.

O rollback não reativa automaticamente o LTX 2.3. Se a nova arquitetura falhar antes da promoção, o estado seguro será H3 isolado e LTX 2.5 desabilitado, preservando os dados.

## 17. Referências oficiais para reconfirmação na implantação

- LTX 2.5 model card e arquivos: https://huggingface.co/Lightricks/LTX-2.5/blob/main/README.md
- ComfyUI-LTXVideo oficial: https://github.com/Lightricks/ComfyUI-LTXVideo
- workflows oficiais 2.5: https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/2.5/README.md
- workflow two-stage oficial: https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/2.5/LTX-2.5_T2V_I2V_Two_Stage_Distilled.json

## 18. Resultado esperado ao final

O Maestro exibirá H3 e LTX 2.5 como escolhas explícitas e equivalentes de produto. Cada motor receberá prompt próprio derivado de uma leitura estruturada da âncora; nenhuma indisponibilidade provocará troca silenciosa. O motor-base LTX 2.3 ficará ausente do runtime ativo e dos consumidores de produção; somente IC-LoRAs allowlisted permanecerão como assets de compatibilidade internos do LTX 2.5. Skills e agentes serão reorganizados em fontes canônicas, Messenger Turbo e Agentes Turbo, com aliases reversíveis e sem sacrificar especialidades distintas.

**Gate concluído:** o proprietário autorizou o smoke GPU curto em 2026-09-02. O recibo técnico promoveu o LTX 2.5 para `READY`/`production_ready=true`; o artefato de smoke não constitui aprovação criativa nem substitui o gate humano de cada take.
