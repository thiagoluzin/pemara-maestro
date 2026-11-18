# Creative OS — implantação de 07/09/2026

## Estado real

O núcleo V0.1 está integrado ao Studio e ao Maestro. **Isso não significa que todo o roadmap do ZIP esteja concluído.** Integrações externas, avaliação semântica automática e qualificação de novos motores continuam pendentes. A tabela abaixo separa código operacional, diagnóstico e dependências indisponíveis.

O Discovery foi concluído antes das alterações. A autorização posterior do proprietário ampliou o escopo para implantação por fases. As regras explícitas do proprietário prevalecem sobre os documentos do ZIP, inclusive sobre exemplos de aprovação automática e troca de motor.

## Operação preservada

- Codex opera ComfyUI exclusivamente pelo MCP `comfyui-local`. Todos os benchmarks GPU deste trabalho foram enviados, acompanhados e obtidos por MCP.
- O usuário gera pelo Maestro diretamente, com acompanhamento pelo próprio backend. Não depende de sessão ou monitor do Codex.
- MiniMax H3 e LTX 2.5 continuam sendo escolhas explícitas. `auto` no Creative IR só recomenda; não gera nem troca o motor.
- H3 Production continua 1088×608, 10 steps, 24 fps. Os perfis existentes, áudio opt-in e seleção LTX foram preservados.
- Geração local e acabamento compartilham a reserva existente da GPU. Geração tem prioridade sobre HQ diferido. Não há interrupção de outro trabalho para conseguir GPU.
- SaveVideo é adaptado ao schema efetivo: `codec` torna-se `format.codec` quando DynamicCombo. Novos grafos H3 nativos também preservam o latent de vídeo separado, sem mudar sampling e sem duplicar SaveLatent existente. O template original não é modificado. O grafo enviado é arquivado com hash.

## Cobertura por fase

| Fase do ZIP | Implementado ou verificado | Limite atual |
|---|---|---|
| 0 Discovery | Relatório A–N, runtime, discos/modelos, filas, arquitetura | Concluído; ver relatório separado |
| 0.5 Performance | Um smoke H3 e um LTX, MP4s reais, hashes, decode e diagnóstico temporal | Não são ranking/A-B; menos de três seeds; tempos internos por estágio indisponíveis |
| 1 Núcleo | IR 0.2, validação, features, registry, recomendação explicável, adapters, bridge, idempotência, SQLite, lineage, assets, API | Adapter Creative cobre H3 T2V/I2V/first-last e LTX I2V; controles e múltiplas referências não são descartados: bloqueiam este adapter e exigem o fluxo nativo apropriado |
| 2 Critic | Decodificação, diagnóstico temporal CPU, revisão por dimensões e consulta visual Gemma local integrada à fila/UI | Consulta de seis quadros é experimental; confiabilidade semântica geral não qualificada. Não aprova, não ranqueia nem dispara reparos |
| 3 Repair | Plano auditável, child generation, mesmo motor, rerun do plano escolhido, first-last H3, orçamento e bloqueio concorrente | LTX Retake/local inpaint e H3 Source Bridge externos não integrados; orçamento GPU usa tempos disponíveis e estimativa de admissão, não um limite rígido por step |
| 4 H3 avançado | Seis plugins instalados em commits fixos; Rewriter executado, revisão de propostas; Motion Director integrado à fila Maestro com qualificação técnica e flag experimental | Motion: Production T2V sem áudio, saídas por segmento; rerun isolado sem predecessor salvo. All-In-One T2V/I2V headless integrado; Fun Control integrado experimentalmente; Timeline contínua qualificada em dois segmentos; Rewriter não aplica texto automaticamente |
| 4.5 Proxy/HQ | Approved Master, metadata de latent, captura nativa, fila durável, perfis, prioridade, health, checksum, roundtrip de vídeo e upscale/refine 1536×864 comparados com geração direta | `h3_latent_2stage_v1` experimental, manual, H3 T2V Production/124 frames/sem áudio, exige fingerprints pré-envio. AV e referências I2V não qualificados; qualidade visual ainda sem vencedor |
| 5 Wan | Mantido fora do registry de produção | Sem instalação/promoção ou benchmark comparativo novo |
| 6 Memória | Character/Scene/Prop Bible versionadas e assets por projeto | A referência precisa ser vinculada explicitamente ao IR; não há aprendizado oculto |
| 7 Router adaptativo | Histórico local revisado, seed/config hash, mínimo de três seeds distintas, revogação de aprovação refletida | Base local atual insuficiente para promover motor/perfil; recomendação nunca substitui seleção |
| 8 Motores candidatos | Não promovidos | Hunyuan/SkyReels dependem de benchmark e decisão explícita |
| 9 Continuidade | Doze dimensões, evidências e hashes das duas fontes, bloqueio de montagem sem revisão | Comparação semântica é revisão declarada; técnicas externas de bridge/extension não integradas |
| 10 Direção | Plano ordenado, execução por etapa, gates humanos, snapshots de IR/bibles, montagem pelo assembler existente | Não equivale a um diretor artístico autônomo; assembly final também exige revisão humana |

## Interface

No Studio do Maestro, abrir **Creative OS · Revisão e acabamento**. Atualizar vídeos, escolher um trabalho existente e adicionar à revisão. A ação indexa o job; não gera novamente.

Depois da conclusão: verificar o arquivo, assistir e aprovar/reprovar o vídeo exato. Só um vídeo aprovado oferece acabamento FHD horizontal/vertical. O resultado é um candidato separado, com nova aprovação necessária. Uma reprovação revoga a elegibilidade do master. A interface e o backend mantêm esse bloqueio.

A sessão usada para inspeção encontrou o login do Maestro. Não houve alteração da autenticação. O JavaScript foi servido pelo frontend real; os botões foram exercitados em fixture loopback isolada com dados fictícios. Vincular → verificar → aprovar fixture → exibir acabamento → reprovar fixture → remover acabamento funcionou. Nenhum vídeo de produção foi aprovado nesse teste.

## Persistência e recuperação

Estado novo: `dados/creative_os/creative_os.sqlite`, tabelas de entidades e eventos append-only. Artefatos: `dados/creative_os/artifacts`, `hq`, `assemblies`, `workflows`. O estado legado dos jobs continua em seu armazenamento existente.

Updates usam revisão esperada e transações SQLite. A chave idempotente vincula configuração, referências e parent. Envios incertos não são refeitos automaticamente. Um reparo cria um filho e conserva seu parent. Consultas por plano não perdem jobs quando existem mais de 500 registros de outros projetos.

HQ verifica aprovação e hash antes e depois da execução. O processo filho assume a reserva da GPU antes de carregar o pipeline existente, preservando a exclusão caso o Studio termine antes do filho. Reinício marca execuções incertas como interrompidas e não as reenvia. Incidentes pausam o lote persistentemente; retomada é explícita. Crescimento de RAM acima de 2 GiB ou duração acima de 2× a média das três execuções anteriores do perfil gera revisão. Isso é diagnóstico, não prova de causalidade nem medição de tempo/step. Unload condicionado à fila vazia ocorre pelo backend; não há restart automático do ComfyUI nem limpeza destrutiva de mídias.

## Verificação

- 35 testes Creative OS passaram: IR, path/hash, idempotência, concorrência, lineage, revisão, revogação, reparo, orçamento, direção, histórico acima de 500 entidades, HQ, recuperação, propriedade do processo filho e autenticação.
- 127 testes relacionados passaram: controle de jobs, H3, LTX, escolha de motor, GPU lease e montagem existente.
- Sintaxe JavaScript validada com `node --check`.
- Benchmarks reais: H3 1088×608/124 frames/24 fps/5,166667 s; LTX 1920×1088/121 frames/24 fps/5,041667 s. Ambos decodificam. Diagnóstico temporal CPU guardado em `benchmarks/20260907/critic_measurements.json`. Nenhuma aprovação artística atribuída.
- A fixture antiga de teste de jobs foi isolada da reserva de GPU e do preparo de runtime reais. Antes da correção ela também falhava contra o backup original; a suite passou após isolamento, sem afrouxar assertions de FIFO.
- Evidências de workflows e lease produzidas pelos testes foram preservadas no backup e retiradas dos registros operacionais. Não se alteraram mídias do proprietário.
- Build em execução e respostas HTTP finais constam de `dados/creative_os/deployment_verification_20260907.json`.

## Instalações avançadas e qualificação

### All-In-One headless integrado às 09:52

Expansão dos templates upstream fixados T2V/I2V para workflow ComfyUI real. O painel `H3OneNode` não é enviado como se fosse sampler. O adapter preserva Production 1088×608/10 steps, seed e prompt, exporta sem áudio e mantém o fluxo existente de assets/recibo de âncora para I2V. Seleção por `bindings.h3_adapter=all_in_one`; default permanece native. A UI oferece T2V All-In-One explicitamente.

Benchmarks MCP: T2V `b785b846-51d3-40b3-8cb3-bda77b5dda5f` e I2V com imagem inicial `bd0dc2e9-c6f5-40e5-8b69-954c676b6b3d`; ambos 1088×608/124 frames/24 fps, sem áudio, decode completo passou. First/last tem mapeamento e testes CPU; demais templates upstream (mask, extend, chain, R2V, audio-drive, image, character sheet) não foram portados para este adapter headless. Nenhuma aprovação artística atribuída.

179 testes passaram, 8 subtests; fixture UI e JavaScript passaram. Detectada e corrigida antes da implantação uma regressão de default None na nova opção booleana. Studio reiniciado às 09:52:33, build `e569cdb472c92f949fb57064b9b64784e43016fbea5d5372479cfa049fd78bb3` e asset v6 verificados. Seis plugins H3 possuem agora pelo menos um caminho integrado e qualificado, com escopos explícitos; isto não significa que todos os modos externos ou todo o roadmap estejam concluídos.


### Fun Control integrado às 09:41

Pesos BF16 curve-form baixados por MCP, revisão HF `f4cac997f880e93cf6940af61ee8d58ef31ff7f3`, checksum SHA256 `57fe1e64928a63a55e3cd4586b55cd5d0eb4980648b6f31e5d9dac16fe7f1c48`. Não foi instalado o checkpoint full-width incompatível. O metadata do espelho não declara licença dos pesos; isto não é uma qualificação de uso comercial.

Benchmarks MCP força 1 `b2cab0ff-87b3-4f8d-ac44-88a722dba01b` e força 0 `9336a194-83c7-4c5c-84e0-95af32f86067`, mesma seed 20260912, 1088×608/124 frames/24 fps, sem áudio, decode completo passou. Fixture de cubo claro em fundo escuro: erro horizontal médio 1,82 px com controle e 147,32 px sem controle, em seis amostras. Métrica limitada à fixture sintética, não é um critic semântico geral. Nenhuma aprovação humana atribuída.

API/UI de upload de controle pré-processado, seleção de tipo e geração explícita. Entrada limitada a 512 MB, escopo do projeto, checksum conferido no registro e imediatamente antes da cópia, geometria/FPS/frames verificados. Worker usa grafo H3 existente com patch ControlNet; mesma fila/lease/cancelamento/revisão. Workflow e origem são arquivados e conferidos antes de aceitar resultados. Envio incerto não é repetido.

175 testes passaram, 8 subtests; fixture UI conferiu bloqueio sem arquivo e envio de controle sintético, zero geração/aprovação de produção. Factory validado por MCP. Studio reiniciado, build `3bf5aedeba92c2b34c2f2b838555d74d01a616331ac14b4d6c9cd97abdbedeed` e asset v5 conferidos. All-In-One headless ainda pendente.


### Timeline contínua integrada às 09:23

Material Planner + Finite Segment Expansion + Finite Segment Sampler integrados com IR tipado. O Maestro prepara e informa duração efetiva; geração usa fila, lease GPU e cancelamento existentes. A entrada é um plano contínuo, sem referências externas, com mesmo prompt/seed nos segmentos; resultado é uma geração única revisável. Workflow e IR são conferidos antes de vincular a saída. Não há replay de envio incerto.

Benchmark MCP `3fc0c435-78d4-422f-91f4-df34a867e977` passou: 1088×608, 226 frames, 24 fps, sem áudio, decode completo. Dois segmentos de 124 frames com sobreposição de 22 frames. Fidelidade e continuidade visual ainda sem aprovação humana. Flag experimental habilita apenas esta geometria/contagem; planejador pode descrever outros tamanhos, mas não os envia sem qualificação.

Fixture UI comprovou preparo sem geração, duração efetiva visível, bloqueio ao editar o prompt e envio explícito. 169 testes passaram, 8 subtests. Studio reiniciado às 09:23:17, build `ec3169e140670bbd0aeedef8e3880be649cb326fa4e1d46c8b632fe0d4ce7a8f`; asset v4 e verificação viva passaram. All-In-One e Fun Control ainda pendentes de adapters.


### Rewriter integrado e verificado às 09:12

Rewriter H3 agora possui fila durável no Maestro, lease GPU compartilhado, cancelamento e retomada de acompanhamento pela interface. Texto original, hash do IR e workflow são preservados; edição concorrente, proveniência ausente e envio incerto bloqueiam aplicação/replay. A sugestão exige revisão explícita, nunca dispara vídeo.

Execução MCP com pesos em cache e auto_download=false: `79a4c18e-fc1e-4987-834b-dad8cbeacd37`, concluída. O texto acrescentou pássaros apesar da restrição contra animais: execução técnica passou, fidelidade semântica não foi aprovada. Qualificação local permanece experimental e invalidada por mudança dos arquivos fixados.

Fixture UI verificou preservação de edição concorrente, aplicação explícita e rejeição, com zero geração/aprovação de mídia de produção. Suite atual: 164 testes passaram, 8 subtests; JavaScript válido. Studio reiniciado às 09:12:22, build `4c3e969cff833bee4c3f76b3a0a62fad8d22516cf82ccaff3b769e646d37714d`; HTTP, hash vivo e asset v3 passaram. All-In-One/Timeline/Fun Control ainda aguardam adapters.


### Refinamento por latent e grade temporal H3

Motion Director agora compila usando a grade H3 `17k+5`, mínimo Production 124 frames. O benchmark `4c74b759-be49-4b09-809b-bb76c40a9188` entregou dois MP4s 1088×608/124 frames/24 fps, sem áudio, decodificação integral passou; 210,55 s para ambos. Testes anteriores de 100 frames ficam como histórico de exportação, não como perfil temporal atual.

Latent upscale + 4 steps de refinamento, denoise 0,25: job `c0281eed-0160-429d-9875-407e7963f674`, 116,57 s, saída 1536×864/124 frames/24 fps, sem áudio, decode passou. Geração direta com mesma seed/prompt/alvo e 10 steps: `9141e6e6-b51c-46df-a7f9-f6c194deb9e0`, 213,83 s. Somando a geração-base (80,82 s), o pipeline em duas etapas ficou em 197,39 s, redução de 7,7% neste ensaio. Uma seed e cache não isolado; nenhum vencedor visual declarado. Relatório em `benchmarks/20260907/h3_two_stage_comparison.json`.

Implementado `h3_latent_finishing.py`: fingerprints de checkpoint/CLIP/VAE antes do envio de novas gerações nativas elegíveis; conferência de modelos, workflow e latent; tensor `[1,24,37,38,68]`; cópia de entrada gerenciada; refinamento sob a reserva HQ existente; prompt persistido antes de polling; nenhum replay se já há prompt/candidato; saída separada com checksums e checagem de dimensão/frames/FPS/áudio. Registros antigos sem fingerprints pré-envio são bloqueados, sem atribuição retroativa.

UI oferece refinamento H3 1536×864 experimental somente em master aprovado com latent elegível. O perfil não é default, não troca engine, e resultado exige nova revisão humana. A qualificação é invalidada se adapter/plugins/pesos divergem. Graphs gerados pelo factory passaram na validação MCP, além dos benchmarks GPU e testes CPU do worker. Não houve aprovação humana fictícia para testar uma fila HQ real.

Testes: suite Creative OS passou com 50 testes; teste adicional de executor HQ também passou, total atual 51. Controle de geração: 107 testes passaram. Reinício/checagem do build final desta etapa em andamento; consultar `deployment_verification_20260907.json` para o estado vivo.

### Estado após liberação da GPU

O proprietário liberou a GPU explicitamente. O job cancelado foi preservado, e os testes usaram novos prompt IDs via MCP. A retomada H3 `c68b7787-cf13-4ee4-88cb-23ed27a8ac36` concluiu em 1088×608, 124 frames, 24 fps, 10 steps, seed 20260908, sem áudio. Vídeo e latent de vídeo foram recuperados pelo MCP; decodificação integral CPU passou.

Roundtrip `db8c52a3-54d9-4dc5-b391-a76582847a27`: recarga do latent separado `[1,24,37,38,68]`, mesmo VAE e exportador. Comparação decodificada com o original teve SSIM Y/U/V/All 1,000000. Escopo: vídeo sem áudio, configuração exata e uma seed; não qualifica roundtrip audiovisual genérico.

Upscale 3D aprendido `f68d1ab0-f879-46c3-923d-3ca7f9b3c89e`: saída 1536×864, 124 frames, decodificação integral passou. Este teste fez upscale + decode, sem segunda passagem de difusão. O perfil `h3_latent_2stage_v1` continua desabilitado até integração/refinamento/qualificação. Todos os resultados permanecem candidatos sem aprovação humana.

Studio reiniciado seletivamente às 07:54:58. A verificação viva passou com build `e8783143322c532ddc04f9a0580fece6901d2f8ec9fa265649f881256a059e0d`, incluindo propostas do Rewriter e catálogo. Alterações posteriores precisam de nova verificação de build.

Motion Director: compilador IR→timeline e fila Maestro integrados. Patch local `creative_os_native_audio_opt_out_v1` respeita `output.creativeOsNativeAudio=false`, preservando comportamento upstream quando ausente; 7 casos CPU passaram. O patch atua no executor e na exportação. Corrigida interoperabilidade: All-In-One usa `functools.wraps`, e Motion Director inspeciona `inspect.unwrap`, mantendo o self-test e a cadeia de wrappers.

Benchmark `e6287315-e665-4138-a9bb-03040e419884` entregou dois MP4s 1088×608, 100 frames cada, 24 fps, sem áudio; decodificação integral passou. Rerun `e0aedb21-4225-44c3-ad8e-bdd0478d9649` selecionou somente SH02, sem contexto anterior, e entregou exatamente um MP4 nas mesmas dimensões. Nenhuma aprovação artística atribuída. A falha anterior `ddd84d9c-f25b-46d5-aeef-deb226b61cd8` permanece registrada.

APIs `/motion-plans`, `/motion-plans/{id}/generate`, `/motion-batches/{id}` e `/motion-batches/{id}/cancel`, sob `/api/creative`, usam a fila existente e não dependem de Codex ativo. Cada segmento é vinculado a uma geração própria para revisão; cancelar um batch cancela seus segmentos. A qualificação é invalidada quando os arquivos fixados mudam. Perfil habilitado: H3 Production T2V sem áudio, experimental, sem boost automático do router. Seed efetiva de cada segmento não é inventada; base seed está no workflow.

Verificação atual: 45 testes Creative OS e 107 de controle de geração passaram. Studio reiniciado às 08:23:43, build vivo `7e98cfe74674bfced3b6bc1489181d32f8725301ac9b4e6b31c9610e8280a360` confirmado. Recuperação de prompt com fila/histórico ausentes agora falha como estado desconhecido, preservando o job sem resubmissão automática.

### Histórico: autorização de terminal e pausa durante o jogo

Restrição posterior do proprietário: **não usar GPU enquanto ele joga**. O benchmark de regressão `4680c104-7a5b-41b5-b620-76ff37b5ada7` foi cancelado via MCP, sem saída concluída. Unload solicitado e confirmado por estatísticas (32.255.246.336 bytes livres). Não foi concluído o roundtrip de latent, e não haverá replay automático nem novo uso de GPU até liberação explícita.

Trabalho posterior somente CPU: propostas do Rewriter com hash exato, revisão humana, aplicação transacional/idempotente, bloqueio de IR desatualizado e preservação de engine/constraints/histórico. Endpoints adicionados em código: `/shots/{shot_id}/prompt-proposals`, `/prompt-proposals/{proposal_id}/verdict`, `/prompt-proposals/{proposal_id}/apply`, sob `/api/creative`. Nenhum desses métodos envia trabalho à GPU. Suite Creative OS: 38 testes passaram. Alterações de API e catálogo aguardam reinício do Studio para entrar no processo vivo; a verificação de build anterior não valida esse código novo.

O smoke Rewriter `91ad2bb3-83b5-44ff-aefe-242497b56489` concluiu anteriormente via MCP, com texto persistido em `benchmarks/20260907/rewriter_omni_result.json`. Acrescentou canto de pássaros ao soundscape apesar da restrição do brief; isso impede aceitar a sugestão automaticamente. Todos os seis plugins foram carregados pelo supervisor; o catálogo vivo confirmou Motion Director e latent upscaler. O peso do upscaler 3D BF16 foi baixado via MCP, revisão HF `13ccf95d85d120bdbc92c05b1247a6e147bf54bf`, 690.592.992 bytes; download não significa qualificação de geração.

O proprietário autorizou explicitamente terminal para configuração/instalação, mantendo geração do Codex via MCP. O bloqueio de configuração descrito abaixo foi resolvido: o MCP agora seleciona ComfyUI 0.34.2 e detecta Manager 4.2.2 como `venv-package`. A junction `.venv` aponta ao Python efetivo em `D:/PemaraRuntimes/comfyui-v0342-py311`; os diretórios de entrada/saída/user e o log registrado foram alinhados. Backup anterior: `backups/creative_os_runtime_20260907/`.

O Rewriter foi instalado em commit fixo e carregado por reinício pelo supervisor Radar. O script administrativo direto recebeu acesso negado; a solicitação fixa de manutenção existente foi consumida com sucesso. O MCP confirmou o nó `MiniMaxH3PromptWriterOmni` disponível e validou o smoke sem erros ou warnings. Job de qualificação iniciado por MCP: `91ad2bb3-83b5-44ff-aefe-242497b56489`; não tratar envio como conclusão.

Seis fontes estão isoladas em `E:/Pemara/maestro/runtimes/creative-os-lab-20260907/sources`, com manifest e probes CPU em `evidence`. Importação/schema passou para Rewriter (16 nós), All-In-One (10), Motion Director (3), Timeline Director (13), Fun Control (2) e Latent Upscaler (5). A fixture de rotas é apenas um registro em memória; esses probes não comprovam execução GPU.

Testes adicionais: 152 do Rewriter; 215 do All-In-One após corrigir no laboratório uma fixture desatualizada de quatro para seis argumentos; 13 testes de paths/máscaras/áudio do Motion Director com contexto CPU do ComfyUI. Código de produção do All-In-One não foi alterado. Os componentes restantes ainda precisam de integração e benchmarks antes de habilitação no Maestro.

O Manager adicionou somente os pacotes registrados no relatório pip; `scenedetect==0.7.1` também foi instalado. `pip check` identificou conflitos Pillow/Gradio e protobuf em pacotes compartilhados, não corrigidos por atualização indiscriminada. Preservados os perfis H3 e o seletor H3/LTX.

### Diagnóstico anterior, preservado para histórico

O `server_info` continua selecionando o checkout antigo `ferramentas/ComfyUI`, v0.30.2. O serviço vivo é `E:/Pemara/maestro/runtimes/ComfyUI-v0.34.2`. A inspeção viva por MCP funciona, mas isso não muda automaticamente o alvo do instalador.

Além disso, o MCP informa `manager_mode: not-installed`. A ferramenta `install_node` exige um ComfyUI-Manager compatível, só aceita IDs do registry e não oferece parâmetro de workspace. `which` apenas lê o alvo; `project` governa projetos/comfy.yaml, não escolhe a instalação. Não há ferramenta exposta para bootstrap do Manager ou troca do workspace de instalação.

Por isso não se executou um instalador contra o checkout errado nem se contornou MCP por terminal. Concluir as integrações avançadas requer primeiro disponibilizar a gestão do runtime correto pelo MCP, depois instalar em ambiente isolado e executar os benchmarks de compatibilidade/qualidade. Flags falsas não contam como integração concluída.

## Fontes das integrações opcionais

Inventário local vivo: 1475 nós, com primitives H3/LTX necessárias presentes; evidência em `live_capability_evidence_20260907.json`.

Metadados públicos foram lidos sem executar código dos plugins e fixados em `optional_upstream_audit_20260907.json`. Licença do plugin não substitui a licença dos pesos:

- Prompt Rewriter: código reportado MIT; requer modelo/LoRA próprio conforme o modo. [Repositório](https://github.com/pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI).
- Motion Director: código reportado GPL-3.0. [Repositório](https://github.com/j955229/ComfyUI-MiniMax-H3-Motion-Director).
- Timeline Director: código reportado GPL-3.0. [Repositório](https://github.com/Songssx/ComfyUI-MiniMaxH3-TimelineDirector).
- Fun Control: código reportado Apache-2.0; controle usa pesos adicionais. [Repositório](https://github.com/wyzborrero/ComfyUI-H3-FunControl).
- H3 latent upscaler: licença não identificada pelo metadata consultado; exige pesos próprios. O autor distingue economia de tempo de economia de pico de VRAM. [Repositório](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler).

## Rollback

Backup anterior em `backups/creative_os_20260907/`: `main.py`, `gpu_lease.py`, `test_generative_control.py`, `app/index.html`, `app/assets/maestro.js`, `FIXLOG.md`. O JavaScript principal Maestro não foi alterado nesta integração.

Com Studio sem jobs ativos, restaurar os arquivos correspondentes do backup e pedir reinício somente do Studio pelo supervisor existente. Remover a referência a `creative-os.js` restaurando o HTML original. Manter módulos novos, banco, artefatos e relatórios preservados para auditoria; não é necessário apagá-los para rollback. Não restaurar ou reiniciar ComfyUI por causa desse rollback.


## Avaliação visual consultiva local — 07/09, continuação
Gemma 4 E2B IT já instalado, core TextGenerate e folha de seis quadros CPU. Codex testou exclusivamente por MCP; o botão do Maestro usa o worker durável com a mesma GPU lease, pausa, cancelamento e não reenvio cego. Registros são ligados ao hash do vídeo, folha de quadros, brief e workflow arquivado. A consulta não modifica avaliações humanas, masters, ranking ou reparos.
O primeiro teste de seis quadros marcou persistência correta como defeito; foi preservado. Definições explícitas corrigiram esse caso na segunda tentativa, sem comprovar confiabilidade geral. Identidade sem referência, física de contato e movimento contínuo permanecem incertos. Fase 2 tem agora consulta visual experimental integrada; crítico semântico autônomo ainda não qualificado.
Validação: 197 testes + 8 subtestes no conjunto completo; após acrescentar teste de despacho/pausa, 120 testes + 8 subtestes de revisão/controle passaram. Interface verificada em fixture sem submissão ou aprovação de produção. Frontend v7.

## Dependência externa de reparo LTX
Template oficial instalado LTX-2.5_ICLoRA_Inpaint_Two_Stage_Distilled usa ltx-2.3-22b-ic-lora-in-outpainting-0.9.safetensors. Modelo ausente; download MCP retornou falta de autenticação e HEAD autenticado com credencial existente retornou HTTP 403. Repositório oficial Lightricks/LTX-2.3-22b-IC-LoRA-In-Outpainting requer aceite de acesso e compartilhamento de contato. Nenhum aceite foi realizado e nenhuma credencial foi copiada para configuração. Reparos locais permanecem bloqueados até acesso autorizado e qualificação GPU. Geração LTX nativa preservada.

Implantação consultiva verificada às 10:12:22: build c78180bc98f2a881eaec0c4ed6c7e93ae967486b30d5cc7c2935fb383fe6eec6, asset v7, health/auth/IR/HQ/frontend hashes PASS. GPU de teste liberada via MCP após conclusão. Nenhum job de benchmark pendente.

Correção de 11:09: o teste manual do proprietário expôs exigência indevida de recibo de âncora no caminho básico de foto para vídeo. Análise agora opcional na tela e no backend; recibos explicitamente usados continuam validados. Testes de fila e formulário confirmam preservação da foto/prompt/motor H3/LTX sem análise obrigatória. Não foi feito novo render do material do proprietário.
