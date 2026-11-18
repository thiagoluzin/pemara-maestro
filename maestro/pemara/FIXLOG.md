# FIXLOG

## 2026-11-02 - Pesquisa pública com fontes integrada ao Maestro

- Novo painel Pesquisa com fontes e API autenticada reutilizam o Harness/Firecrawl MCP/TypeSafe. Histórico, fontes com data/cache/hash, dossiê e revisão factual por afirmação; versão de personagem obrigatória quando aplicável. Vínculo opcional fica no registro da pesquisa sem reescrever projetos, referências ou aprovações.
- Servidor impõe dados públicos/domínios, limites, idempotência e trava de concorrência; comando Node fixo sem shell, fontes exibidas como texto e evidências alteradas bloqueadas. Reinício reconcilia resultados sem replay de chamadas externas.
- Corrigido o helper de reinício: sockets locais cujo estado vem nulo agora identificam o dono da porta; saúde exige que o novo processo detenha a porta. Implantação pelo Radar confirmada no Studio real, preservando ComfyUI e histórico de geração.
- 12 testes passaram, incluindo navegador em 1440/390/320 pixels, com repetição do navegador após ajuste final de layout. Piloto real pela interface autenticada: uma fonte, duas afirmações, uma sustentada e outra incerta; dossiê pronto e revisão humana pendente. Nenhum render, aprovação de mídia ou alteração no PEMARA EDU, mantido por último.
- Documentação: `docs/PESQUISA_COM_FONTES.md`; evidências e recibo restrito ao componente em `dados/validation/maestro_research_20261102/`; relatório em `E:/Pemara/auditorias/maestro_research_20261102/RELATORIO.md`.

## 2026-10-03 - RE2 Leon/Licker: revisão em três takes autorizada

- Proprietário confirmou Leon e Licker e pediu trabalho autônomo enquanto dorme: três takes de 10s, dois conectores, disparo seguido de grito e perseguição pelo teto. Corredor e qualidade sonora preservados como direção; original e Full HD60 anteriores conferidos por SHA-256 e mantidos.
- Revisão isolada em `ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1/revisions/three_takes_ceiling_chase_v2`. Fonte visual da edição original pesquisada e inspecionada; novas referências/âncoras geradas por ImageGen permanecem candidatas, sem aprovação artística herdada.
- Corrigidas as primeiras âncoras com membros/apoios ambíguos; tentativas preservadas. Uma correção de perseguição foi bloqueada pelo gerador de imagens; enquadramento aberto e menos gráfico gerado como alternativa. Limitações de anatomia traseira/vistas originais registradas.
- Referências canônicas históricas aprovadas usadas apenas como comparação de identidade; imagens novas não marcadas como canônicas aprovadas. Revisão visual de âncoras pelo Codex e contratos de continuidade passaram para render candidato, não para aprovação do proprietário. Três preflights MCP passaram, 20 passos Master/Sage/áudio nativo preservados, Face Refine ausente.
- Primeiro render representativo T02 enviado via MCP: `bcd14da1-5a79-4825-acd9-da344ca719db`. Novos renders, montagem e acabamento ainda em andamento; nenhum vídeo final novo ou ganho de qualidade certificado neste registro.

## 2026-10-03 - Remocao do Face Refine e original RE2 restaurado

- Ordem explicita do proprietario: remover Face Refine dos workflows e mostrar o original. Verificados 291 arquivos, 58 workflows alterados; remocao do passe automatico, da etapa no Maestro e da exportacao do no no runtime. Sage corrigido preservado.
- ComfyUI reiniciado via MCP com fila ociosa; Studio recarregado pelo Radar. No facial ausente no inventario vivo; grafo RE2 sem Face Refine passou no preflight. 148 testes passaram.
- Original preservado e trimado a 720 quadros/30s com frames decodificados identicos e pacotes de audio nativo intactos. Maestro serve o original, versao rejeitada preservada no historico.
- Proprietario aprovou o original: "Ja vi ficou otimo. 60fps e fullhad agora". Acabamento Full HD60 autorizado sobre essa fonte exata; derivado segue para revisao separada.

## 2026-10-03 - Face Refine em novos workflows H3

- Pedido do proprietario: incorporar o passe facial em todos os workflows H3.
- Plugin local rastreia YuNet/anime ONNX, usa H3 Base FL2VA + SageAttention, 12 passos, denoise 0,45 e canvas 512. Preserva MP4 original, audio e pixels fora da mascara antes da codificacao; sem rosto passa os frames originais, falha de detector e erro.
- 34 workflows recebem a etapa; novos envios de grafos antigos tambem passam pelo handler idempotente. Maestro inclui o no no grafo antes de registrar a submissao. Historicos, medias aprovadas e fila anterior permanecem preservados.
- Fontes T8 fixadas, detectores verificados por hash, backups e recibos em `ferramentas/h3_face_refine_20261003`. Corrigida a entrada `format.codec` nos antigos templates H3 para o schema ativo do SaveVideo.
- Diagnostico real de cinco quadros passou com Sage conectado e `mask_outside_bit_exact=true`; isso nao aprova identidade, consistencia longa ou qualidade artistica. Templates experimentais com dependencias ausentes continuam identificados no preflight.
- Cena RE2 1998 Leon/Licker: as duas ancoras foram aprovadas pela mensagem direta Aprovado. O primeiro render de 30 segundos foi rejeitado pelo QC tecnico por ruido cinza e preservado; nao houve aprovacao de video.
- SageAttention: reproduzido overflow de stride CUDA uint32 em Q/K/V de sequencia longa. Plugin local compacta grupos de cabecas antes de RMSNorm/RoPE e quantizacao; contexto completo, motor, precisao, resolucao, steps e audio preservados. Diagnostico GPU 050a0433-c1ee-474f-9ab7-df3806c536ef: erro zero no caminho corrigido, forward finito com valor esperado. Oito contratos CPU passaram; 28 preflights MCP: 20 passaram, oito falhas anteriores persistem.
- Segunda tentativa MCP 2ae78cb0-1284-4306-9d7b-3dceea4da644 em geracao: 1344x768, 20 steps, 736 quadros nativos, Face Refine e audio nativo. Latentes tambem sao preservados. Correcoes numericas nao aprovam o video; aguarda resultado e revisao visual/sonora.

## 2026-09-07 - Creative OS V0.1 integrado ao Maestro

- Após o Discovery e a autorização de implantação: Creative IR, SQLite/eventos, adapters H3/LTX, seleção explícita, asset hashes, lineage/idempotência, critic técnico/temporal, revisão humana, reparos com orçamento, bibles, benchmark ledger, direção e montagem pelo assembler existente.
- Painel adicional `Creative OS · Revisão e acabamento`, com vínculo de jobs existentes e acabamento neural separado somente para masters aprovados. Novos endpoints herdam a segurança do Studio. Maestro continua direto/autônomo; coordenação do Codex continua MCP-only.
- SaveVideo adapta apenas o codec ao schema DynamicCombo do runtime ativo; grafo efetivo é arquivado. Parâmetros de sampling/perfis existentes preservados.
- GPU lease compartilhada com geração local, prioridade da geração sobre HQ, processo filho de HQ assume a reserva, jobs incertos não têm replay automático, incidentes pausam a fila persistentemente.
- Verificação: 35 testes Creative OS + 127 testes relacionados passaram; JS syntax passou; dois smokes H3/LTX reais por MCP; critic CPU/decode passou nos dois MP4s. Fixture de UI comprovou que PASS técnico não aprova e reprovação retira a opção de acabamento. Nenhuma aprovação humana de produção foi fabricada.
- Studio reiniciado pelo supervisor existente, ComfyUI preservado. Health HTTP 200/build hash coincide, IR inválido 422, forwarded host não confiável 403; asset servido coincide com disco. Evidência em `dados/creative_os/deployment_verification_20260907.json`.
- Escopo remanescente explícito: plugins H3 avançados, Retake/DFR e novos motores não foram instalados/qualificados. MCP ainda seleciona checkout histórico e não dispõe de Manager/gestão do alvo necessários. Roadmap completo NÃO declarado concluído.
- Relatórios: `docs/CREATIVE_OS_IMPLEMENTATION_20260907.md`, `docs/CREATIVE_OS_API_20260907.md`, `docs/CREATIVE_OS_PERFORMANCE_20260907.md`. Backup em `backups/creative_os_20260907/`.

## 2026-09-07 - Discovery Creative OS e regra de coordenação MCP

- Entrega: `docs/CREATIVE_OS_DISCOVERY_20260907.md`, com seções A–N, leitura do ZIP, inventário local, distinção entre ComfyUI ativo 0.34.2 e checkout histórico 0.30.2, capacidades e lacunas.
- Regra expressa do proprietário registrada em `E:/Pemara/AGENTS.md`: Codex opera ComfyUI exclusivamente via MCP; Maestro mantém geração direta e autônoma, sem depender do Codex ou exigir monitor adicional.
- Preservada como regra a escolha explícita do proprietário entre H3 e LTX 2.5, sem fallback/troca automática; seletor e validação existentes confirmados por leitura do frontend e registry.
- Testes existentes `test_video_engine_selection`: 3/3 passaram, sem GPU, com fixtures temporárias.
- Verificação: consultas MCP server_info/system_stats/job; validação do template LTX via MCP passou com zero erros e um aviso de tipagem. Sem render, instalação, refatoração, alteração de workflows, cleanup ou reinício. Mudanças apenas documentais.

## 2026-09-03 - Buffer persistente no player de takes

- Sintoma: ao revisar takes remotamente, o player descartava o vídeo já carregado sempre que o mesmo card era aberto novamente; a instância ativa também respondia `Cache-Control: no-store`, apesar de aceitar `Range`/HTTP 206.
- Correção: o player agora usa `preload=auto`, preserva a mesma fonte e o buffer quando o take não mudou, aguarda `canplay` antes do autoplay e informa progresso, espera, conexão lenta e erro. A API expõe uma versão derivada de mtime/tamanho, permite cache privado imutável para URLs versionadas e transmite em blocos de 512 KiB mantendo suporte a byte ranges. O middleware de segurança continua aplicando `no-store` por padrão aos JSONs, mas deixa de sobrescrever a política privada declarada pelas rotas de mídia.
- Verificação: `node --check`, 83 testes de projetos e 41 contratos da interface passaram. Após recarga seletiva pelo Radar, a rota viva respondeu HTTP 206 com `Accept-Ranges`, `Content-Range` e cache privado imutável; Chromium carregou o T08 inteiro, reportou `readyState=4`, 1088x608, 10 s, buffer 0-10 s, reprodução ativa e nenhum erro. O build `20260903-video-buffer1` também foi confirmado no domínio público.

## 2026-08-27 - Gate contra bateria e baixo com pulso de maquina

- Sintoma: o candidato 1 do lote `89baf38bd44d4c2991c7095d7611372d`, embora sem o timbre de serra anterior, foi rejeitado pelo proprietario por soar como uma maquina de lavar velha pulando.
- Diagnostico medido: a faixa abaixo de 180 Hz continha 3,167 ataques por segundo, 65,923% dos intervalos abaixo de 220 ms e pouca respiracao dinamica (`P95/mediana=1,45959`), contra 1,166 ataques por segundo, zero intervalos curtos e `P95/mediana=3,466` na fonte. O novo `mechanicalPulseRisk` marcou `0,69499`.
- Correcao: o critico neural passou a medir densidade de ataques graves, intervalos curtos, variacao de RMS e rigidez do grid; `mechanicalPulseRisk >= 0,40` reprova o mix quando baixo e bateria foram solicitados. O prompt automatico agora exige secao ritmica humana com respiracao e evita double-kick continuo, baixo bombeando e pulso grave repetitivo. Rejeitar o unico candidato que passou o gate tambem rejeita e esconde o lote inteiro, sem rotular os demais candidatos tecnicamente falhos como rejeitados pelo proprietario.
- Resultado: o master reclamado ficou `OWNER_REJECTED`, fora de `Arquivos`, sem aprovacao e preservado pelo SHA-256 `a00eeb98423a9fd66078d626c55aeec1885805241930ec7bf24fd658df5c1f99`. A correcao `5b16b60a172542bcbb8c2898f7b25305` gerou quatro variacoes; somente o candidato 3 passou todos os gates, com `mechanicalPulseRisk=0`, `buzzsawRisk=0,10085`, balanco orquestra-metal `0,08681`, piano/cordas/baixo/bateria detectados, zero clipping e revisao humana ainda pendente.
- Verificacao: 20/20 testes de producao/API, 4/4 contratos da interface, `py_compile`, `node --check` e `git diff --check` passaram. Os quatro WAVs tiveram SHA-256 conferido e decodificacao integral via FFmpeg; somente o novo candidato 3 aparece em `Arquivos`.

## 2026-08-27 - Rejeicao integral coerente do lote musical

- Sintoma: o lote de Tifa's Theme soava como serra/serraria e fabrica; o ranking neural ignorava o balanco orquestra-metal e ainda chamava uma mistura com piano/cordas fracos de recomendada. Ao rejeitar o ultimo candidato, o estado passava corretamente para `OWNER_REJECTED`, mas a mensagem ainda dizia que os demais continuavam pendentes.
- Correcao: a direcao automatica deixou de transformar intensidade alta em guitarra agressiva; agora pede guitarra valvulada quente e recuada, protege os instrumentos realmente selecionados e evita parede de distorcao. O critico mede energia aguda persistente, flatness e cruzamentos por zero para formar `buzzsawRisk`; o ranking exige presenca minima de baixo, bateria, piano e cordas, balanco contra `guitarWall` e risco baixo de serra. Lotes que falham ficam `INTERNAL_QC_REJECTED`, preservados e fora de `Arquivos`. A revisao integral tambem passou a informar corretamente que o lote inteiro foi rejeitado.
- Resultado: o lote original `f8cba34de35f475f8147b4b09d71b413` ficou 3/3 `OWNER_REJECTED`, sem candidato aprovado e sem entrada em `Arquivos`. A primeira correcao `6f291f7ff24c4c4d8f4f6b25dd0b0f01` falhou por cordas insuficientes e ficou somente como diagnostico. A segunda, `89baf38bd44d4c2991c7095d7611372d`, entregou o candidato 1 com `creativeMixPass=true`, `buzzsawRisk=0.06211`, balanco `0.07603`, zero clipping e revisao humana ainda pendente; somente esse lote aparece em `Arquivos`.
- Verificacao: 18/18 testes de producao/API e 4/4 contratos da interface passaram; `py_compile`, `node --check` e `git diff --check` passaram. Os tres WAVs da substituicao tiveram hashes conferidos e decodificacao integral via FFmpeg. O Studio 8029 foi recarregado pelo Radar somente com fila ComfyUI e jobs musicais vazios.

## 2026-08-24 - Musica nativa do MiniMax H3 para takes do Maestro

- Sintoma: o fluxo de takes do Maestro somente liberava o decodificador de audio nativo do MiniMax H3 para narracao pt-BR, embora o H3 local ja possuisse VAE de audio e campos oficiais de ambiente/musica.
- Correcao: adicionada a estrategia `minimax_h3_native_music`, que exige autorizacao explicita do proprietario e direcao musical declarada. Ela preserva os quadros gerados, recusa MP4 sem audio e mantem a musica como candidata com escuta humana obrigatoria.

## 2026-08-24 - Saida FHD vertical para projetos de preview

- Sintoma: um take vertical aprovado em 720x1280 nao podia iniciar o upscale porque a resolucao final herdada do preview nao era um alvo FHD valido.
- Correcao: `finalResolution` passou a aceitar somente `1920x1080` ou `1080x1920` na atualizacao validada do projeto. A troca altera apenas o destino do candidato; o video original permanece preservado como rollback e o FHD continua exigindo revisao humana.

## 2026-08-24 - Reconexao do Cloudflare Tunnel do Maestro

- Sintoma: `maestro.pemaratech.com.br` retornava Cloudflare Error 1033, embora o gateway local autenticado em `127.0.0.1:9501` e o Studio em `127.0.0.1:8029` respondessem normalmente.
- Causa raiz: o tunel `maestro-tunnel` (`940443cd-a1cc-472c-85c7-6f2c572179d8`) estava sem conectores; o servico `Cloudflared` ativo apontava somente para o tunel da loja e nao possuia a rota do Maestro.
- Correcao: criada a configuracao isolada `C:\Users\admin_remoto\.cloudflared\maestro-tunnel.yml`, limitada a `maestro.pemaratech.com.br -> http://127.0.0.1:9501` e fallback 404. O iniciador de logon do usuario so sobe esse conector quando ele estiver ausente e o executa oculto.
- Verificacao: `tunnel ingress validate` passou; o tunel registrou quatro conexoes Cloudflare; `https://maestro.pemaratech.com.br/` voltou HTTP 200 com formulario de login e CSRF. A criacao de servico/tarefa agendada foi recusada por falta de elevacao, sem alterar o servico existente.

## 2026-08-22 - Galeria de semente única para END dinâmico do H3

- Sintoma: a candidata `M08_START` estava registrada e pendente de revisão, mas a rota viva `preanalysis-gallery` respondia HTTP 422 porque o contrato legado aceitava somente galerias estáticas com START/END.
- Correção fail-closed: uma galeria com somente START passa exclusivamente quando o take declara liberdade coreográfica H3, o candidato é exatamente `<take>_START` e o END proíbe imagem estática e exige o último quadro ainda em movimento do take H3 aprovado. Qualquer semente única sem esse conjunto exato continua rejeitada.
- Implantação: fila generativa e reserva de GPU estavam vazias; apenas o Studio 8029 foi recarregado pelo supervisor administrativo Radar. Frontend, ComfyUI e renders não foram tocados.
- Verificação: `test_video_projects` passou 88/88 casos; os 3 testes do contrato FFVIII passaram; auditoria Scale V5 e gate de contrato passaram. A galeria M08 agora responde HTTP 200, permanece `PENDING`, `canGenerate=false`, e o projeto continua com zero vídeo.

## 2026-08-22 - Redefinicao local e segura da senha administrativa do Maestro

- Sintoma: o proprietario recebia `Usuario ou senha invalidos`; a configuracao ativa possuia somente `MAESTRO_ADMIN_PASSWORD_HASH` em `scrypt`, sem senha legivel ou procedimento local de redefinicao.
- Correcao: `TROCAR_SENHA_MAESTRO.bat` agora oferece fluxo elevado por duplo clique, pede a nova senha duas vezes sem eco, preserva o usuario existente, grava somente um hash `scrypt` com salt aleatorio e mantem `MAESTRO_ADMIN_PASSWORD` vazio.
- Seguranca e rollback: nenhum segredo entra na linha de comando ou nos logs; `.env` e sessoes recebem backup com ACL restrita; sessoes anteriores sao revogadas; qualquer falha de gravacao, reinicio ou login restaura os artefatos anteriores.
- Validacao: o BAT passou seu `--self-test`; o hash novo foi aceito pelo validador real de `MASTER.py` e recusou senha divergente; `test_master_auth.py` passou 19/19 casos; o PowerShell passou no parser e o auxiliar Python passou em `py_compile`.
- Correcao operacional: a primeira execucao real revelou que o verificador procurava `csrf`, enquanto o formulario vivo usa `csrf_token`. O parser agora aceita aspas simples/duplas e atributos reordenados, o autoteste consulta o formulario vivo, e um POST descartavel comprovou chegada ao gate de credencial (`401`) sem rejeicao de CSRF. O rollback da tentativa falha foi confirmado por SHA-256 identico para `.env` e sessoes.

## 2026-08-21 - Login publico aceita origem opaca somente quando o navegador prova mesma origem

- Sintoma: ao enviar o formulario em dois navegadores, o endereco publico do Maestro respondia HTTP 403 com `Origem da requisicao nao permitida`, antes de validar CSRF, usuario ou senha.
- Causa raiz: os requests reais registrados pelo gateway traziam `Origin: null` e `Sec-Fetch-Site: same-origin`. A validacao tentava interpretar o valor opaco `null` como URL e recusava uma navegacao que o Fetch Metadata protegido do navegador confirmava ter partido da propria origem.
- Correcao: `Origin: null` passa somente na combinacao exata com `Sec-Fetch-Site: same-origin`. `null` sem metadata, `same-site` ou `cross-site`, origem estrangeira, porta divergente e variantes como `NULL` continuam bloqueados; o CSRF assinado e a verificacao `scrypt` permanecem independentes e obrigatorios.
- Implantacao: somente o gateway loopback `127.0.0.1:9501` foi recarregado pelo supervisor, do PID 48620 para o PID 13164. Studio, fila de video, ComfyUI e GPU nao foram reiniciados ou alterados.
- Prova publica: GET em `https://maestro.pemaratech.com.br/login` emitiu CSRF; `Origin: null + same-origin` chegou a autenticacao e retornou 401 para uma credencial descartavel; `null + cross-site` retornou 403 por origem; CSRF invalido retornou 403 pelo gate de CSRF. Um Edge headless em contexto isolado confirmou formulario visivel, CSRF presente, POST chegando a autenticacao e ausencia da rejeicao de origem.
- Verificacao automatizada: `test_master_auth.py` passou 19/19 casos, incluindo quatro contratos novos da origem opaca. `py_compile` e `git diff --check` passaram. A senha e o hash protegidos nao foram exibidos nem redefinidos.
- Rollback: snapshot anterior verificado em `archive/auth_origin_opaque_same_origin_20260821_065551`, preservando `MASTER.py`, `test_master_auth.py` e este log antes da alteracao.

## 2026-08-19 - Take reprovado permanece visivel na revisao do Maestro

- Sintoma: o take 01 de `gohan_ssj2_android16_cell_6x10s_liveaction_v1` existia na API e possuia MP4, mas desaparecia da aba `Revisar` assim que o QC interno o marcava como `REJECTED`.
- Causa: `filmTakeNeedsReview` aceitava video produzido somente no estado `READY`, embora a propria interface ofereca player e fluxo de correcao para `REJECTED`.
- Correcao: candidatos com `hasPreview` nos estados `READY` ou `REJECTED` permanecem na revisao humana; o build do front-end passou para `20260819-rejected-review1` para provocar recarga controlada.
- Verificacao: os dois testes focados passaram, `node --check app/assets/maestro.js` passou, e o servidor ativo em `127.0.0.1:9501` entrega o novo build e o filtro corrigido.
- Observacao: a suite completa de contratos de UI ainda possui uma falha anterior e independente, pois um teste procura `selected == MINIMAX_H3_MODEL_NAME` enquanto o backend atual usa `_is_minimax_h3_model(selected)`.

## 2026-08-16 - Workflow MiniMax H3 unificado, auditavel e portavel

- Sintoma: o gerador ja usava MiniMax H3, mas API, templates e documentacao ainda misturavam
  contratos Wan/LTX. Agentes, skills, modelos, gates humanos e restauracao em outro PC nao tinham
  uma unica fonte de verdade visivel no Maestro.
- Causa raiz: a integracao H3 cresceu por partes (gerador, prompt oficial, projetos, RIFE e Foley)
  sem um contrato de orquestracao transversal e sem snapshot que incluisse os pesos necessarios.
- Correcao: `h3_workflow.py` passou a inventariar o catalogo instalado, rotear apenas especialistas
  relevantes e descrever dez gates do roteiro ao master. O Studio expoe o diagnostico somente para
  origem interna, o painel mostra o workflow, e cada take pode rodar o preflight real sem criar job.
  Templates novos usam H3, prompt oficial, acao continua e pos-producao apenas apos aprovacao.
- Portabilidade: foram adicionados backup, validacao e restauracao do sistema em pasta vazia, com
  codigo, agentes, skills, configuracoes publicas, inventario e SHA-256. Pesos de modelos, `.env`,
  segredos, projetos e renders permanecem excluidos por decisao do proprietario.
- Seguranca: as rotas novas sao somente leitura e fail-closed por `_is_internal_request`; output de
  agentes/modelos continua sem poder de aprovar, publicar, iniciar GPU ou operar paths arbitrarios.
- Verificacao: `py_compile`, `node --check` e testes H3/UI passaram antes da implantacao. Nenhuma
  inferencia pesada foi iniciada durante o debug.
- Debug de restauracao: a primeira copia limpa passou 42 testes, mas revelou falso negativo no gate
  NVENC porque o PowerShell aplicava `-notmatch` linha a linha. O validador agora junta a saida do
  FFmpeg antes da busca e a restauracao completa e repetida faz parte do aceite do backup.

## 2026-08-07 - Aprovacao de ancora libera corretamente o render sem apresentador

- Sintoma: `03A`, `03B`, `16A`, `16B`, `23A` e `23B` apareciam com imagem aprovada e `canGenerate=true`, mas iniciar o render devolvia HTTP 422 `CAST_ANCHOR_UNVERIFIED` antes de criar um job.
- Causa raiz: a revisao humana marcava a ancora como `approved_for_video`, mas nao persistia `visual_qc.actual_visible_characters`. A migracao sem apresentador tambem havia colocado nomes de objetos cientificos em `allowed_non_humans` e mantido descricoes antigas do apresentador em `motion_layers`.
- Correcao: o Maestro agora envia e valida `actualVisibleCharacters` ao aprovar uma ancora, grava a verificacao no sidecar e permite complementar de forma idempotente aprovacoes antigas. Os seis contratos foram reparados para elenco visivel vazio, zero pessoas e movimento exclusivamente cientifico; o utilitario de migracao deixou de transformar objetos de cena em elenco.
- Prova de producao: o lote real de seis takes foi aceito sem nenhum erro de preflight. O job `56f39455774d49b28993f6bf68453b50` concluiu o `03A` em 100%, H.264 1280x720/24 fps por 6,583 s com AAC 48 kHz estereo e voz pt-BR. Tres amostras visuais confirmaram zero pessoas; o `03B` iniciou automaticamente e os quatro seguintes permanecem na fila serial.
- Verificacao: `py_compile` e `node --check` passaram; a suite conjunta de projetos de video e contratos da interface executou 80 testes sem falha. O preflight real dos seis takes resolveu `anchorVisibleCast=[]`, `expectedHumanCast=[]` e `expectedNonHumanCast=[]`.

## 2026-08-07 - MiniMax H3 recupera automaticamente falha VBAR no Maestro

- Sintoma: o take 22A caiu no Maestro com `Erro no take` e `Fault failed: 2`, embora a fila do ComfyUI estivesse vazia; a RTX 5090 permanecia com cerca de 31 GB ocupados e apenas 1 GB livre.
- Causa raiz: o `comfy-aimdo 0.4.11` manteve um VBAR do DynamicVRAM em estado inválido durante o encoder Qwen3-VL do `MiniMaxH3ImageToVideo`. A API do Studio ainda truncava o status bruto e escondia a origem da falha.
- Correção: erros `Fault failed: 2` cuja pilha confirma `comfy_aimdo` agora recebem tipo próprio. Para MiniMax H3, o worker confirma que a fila está vazia, chama `/free`, espera a 5090 devolver pelo menos 8 GiB e repete o mesmo take uma única vez com a mesma seed; fila ocupada ou segunda falha continuam fechando com erro, sem loop cego. Outros erros do ComfyUI passam a preservar nó, tipo e mensagem de exceção de forma legível.
- Recuperação operacional: com zero jobs ativos, `/free` reduziu o uso de VRAM de aproximadamente 31 GB para 1 GB. Um workflow diagnóstico executou com sucesso `CLIPLoader`, `VAELoader`, `LoadImage` e `MiniMaxH3ImageToVideo`; o erro posterior do `SaveLatent` foi esperado porque esse nó não aceita o `NestedTensor` audiovisual e não invalida o encoder.
- Prova de produção: após o Radar recarregar o Studio do PID `22708` para `61924`, o job real `d8fcd75665e7471c965c52732762f00b` refez o 22A e terminou `done` sem recuperação adicional. O Maestro publicou preview H.264 1280×720/24 fps de 9,416 s com AAC 48 kHz estéreo, lettering pt-BR e áudio pt-BR; o take ficou `READY`, sem `lastError`, e as duas filas voltaram a zero.
- Verificação: `py_compile` passou e seis testes dirigidos passaram, cobrindo classificação da falha AIMDO, recusa de descarga com fila ativa, espera real por VRAM, uma única recuperação e preservação da seed. A bateria ampliada executou 162 testes; 161 passaram e permaneceu uma falha anterior e não relacionada em `test_audio_qc_failure_preserves_completed_video_candidate`.

## 2026-08-06 - Prompts 017/020-040 fechados, botão destravado e bases 020-022 entregues

- Sintoma: após o aceite do 019, o botão ainda parecia preso; a correção 017 iniciou, mas caiu antes da GPU porque a fala natural de Pedro durou 4,00 s e a janela contratada tinha apenas 3,89 s. Os takes 020-040 ainda dependiam de fotos-base e tinham elencos narrativos excessivos em vários prompts.
- Correção dos prompts: 017 e 020-040 agora usam inventário fechado por slots, contagem humana/não humana exata, uma instância física por identidade, eixo de tela fixo, três batidas temporais, movimento natural e bloqueios de entrada, duplicação, transformação de prop em personagem, texto visível, pt-PT e upscale antecipado. Takes já aprovados não foram alterados.
- Áudio: todas as janelas pt-BR de 017-040 foram ampliadas até o limite seguro do take, sem sobreposição, corte ou aceleração. No 017, Pedro passou a ter 4,29 s; a falha antiga foi limpa e uma correção isolada voltou a ficar elegível.
- Botão: a política exposta pelo Studio entra em `correctionMode`, desativa temporariamente a exigência de trinca completa somente para `REJECTED/ERROR` e volta à regra de três assim que a correção termina. O processo foi reiniciado sem jobs ativos; a API confirma 017 `REJECTED`, `canGenerate=true`, `generationBlocked=false` e request `AUDIO_SYNC/DELIVERED`.
- Fotos-base: o Imagegen integrado criou 020, 021 e 022 com identidade referenciada e elenco exato. A primeira versão do 021 foi descartada por conter figuras de animais nos cartões; a substituta usa cartões lisos. As três foram recortadas somente na borda para 1664×936 exatos, passaram no QC visual do Codex e estão `pending_human_qc` no Maestro; nenhuma foi aprovada automaticamente.
- Verificação: refatoração dry-run/aplicada em `PASS`, scripts compilados, registro de candidatos idempotente, hashes e dimensões validados, zero jobs de GPU ativos durante o reinício. A suíte Studio completa já permanecia verde com `259` testes após as correções sistêmicas deste ciclo.

## 2026-08-06 - Correção isolada não fica presa à próxima trinca; take 019 gerado

- Sintoma: o take 019 estava reprovado, com foto e preflight válidos, mas o botão principal permanecia travado. A produção não havia sido iniciada após a correção anterior.
- Causa raiz: a política de trincas completas tentava preencher o lote com as correções pendentes 017/019 e, ao alcançar o 020 sem foto-base, mantinha o conjunto incompleto e bloqueado. A regra correta para três takes novos estava sendo aplicada indevidamente a rerenders já tentados.
- Correção sistêmica: `allow_incomplete_correction_batch` libera somente blocos contíguos de takes `REJECTED/ERROR` já tentados, sem atravessar uma foto-base ausente. Takes novos continuam exigindo três fotos prontas e três reservas; backend e painel usam a mesma decisão e o botão identifica `Corrigir take`.
- Produção: o 019 corrigido foi iniciado explicitamente pelo job `737a735fcf4d48d18c04f4d8aea316c5` e terminou em 1280×720, 193 quadros/8,041 s nativos, com preview RIFE 60 fps no Maestro e upscale bloqueado. O contrato enviado continha exatamente um humano (`Pedro`) e uma criatura (`Lira`).
- QC visual: a folha de contato de oito amostras mostra somente Pedro e Lira do início ao fim; nenhum humano extra surgiu. O gate automático de surto de elenco também passou com limite de duas entidades. Áudio ambiente permanece pendente de escuta humana, e o preview anterior continua preservado no histórico.
- Verificação: `node --check`, `py_compile`, quatro testes direcionados e a suíte Studio completa (`258` testes) passaram. O teste antigo de trinca completa continua bloqueando dois takes novos; dois novos testes provam que uma correção pode iniciar sozinha sem 020/021.

## 2026-08-06 - Elenco visual verificado bloqueia humanos não autorizados no take 019

- Sintoma: o take 019 começava coerente com a foto-base e depois materializava crianças/humanoides não autorizados. A inspeção quadro a quadro confirmou que a âncora contém somente Lira e Pedro, enquanto o contrato enviado ao LTX exigia três crianças e cinco criaturas.
- Causa raiz: o preflight aceitava `required_objects.characters`, que registra o que o gerador de imagem foi solicitado a criar, como se fosse prova dos pixels. Isso inflou também o limite do QC pós-render para oito entidades com face, escondendo a multiplicação posterior.
- Correção do take: o 019 foi reprovado sem apagar nenhum preview e refatorado para exatamente `Lira + Pedro`, oito segundos, três notas baixas, um único sinal de mão e pausa legível. Entradas, revelações laterais, transformação de cartões em corpos, humanoização, duplicação e qualquer terceiro personagem foram proibidos; nenhuma nova geração foi iniciada.
- Correção sistêmica: o projeto agora exige `visual_qc.cast_verification_status=VERIFIED` e `actual_visible_characters` antes da GPU. As 19 âncoras aprovadas foram conferidas numa folha de contato e receberam o elenco realmente visível; intenção textual não serve mais como prova visual neste projeto.
- Evidência: o arquivo ruim, reavaliado com o contrato correto de duas entidades, falha com `QC_CAST_SURGE`: até quatro rostos detectados para um máximo de dois. O novo preflight falha fechado com `CAST_ANCHOR_UNVERIFIED` quando o registro visual estiver ausente.
- Verificação: os 19 specs reais aprovados passaram com igualdade entre elenco visual e prompt; o 019 resolve `Pedro + Lira = Lira + Pedro`, permanece `REJECTED`, está disponível para nova geração e conserva o preview reprovado. `py_compile`, quatro testes direcionados e a suíte Studio completa (`256` testes) passaram. Fila GPU não acionada.

## 2026-08-01 - Curta de Pyramix dirigido e preparado para LTX-2.3 no Maestro

- O roteiro-fonte de 91 takes narrativos foi reestruturado em uma montagem de
  diretor com 68 takes, dez sequencias e 332 segundos, preservando os arcos,
  viradas e falas essenciais; os quatro extras musicais ficaram fora do curta.
- Cada take ganhou contrato de acao, camera, continuidade, fala pt-BR, duracao
  de 3 a 6 segundos e perfil LTX-2.3 distilled FP8 em 1280x720, 24 fps, 8 steps
  e guidance 1. O take 004 ja aprovado foi incorporado com base e preview.
- O backend e o painel de projetos passaram a reconhecer LTX-2.3 sem rotular ou
  iniciar Wan. Saidas LTX sao copiadas atomicamente para o projeto, com QC
  temporal e upscale bloqueado ate aprovacao humana. O prompt dirigido, falante
  e fala pt-BR agora aparecem no take; o prompt pode ser editado e salvo pelo
  painel, com bloqueio de termos que ativariam texto/interface no quadro.
- Gates: nenhum prompt positivo contem texto visivel, legenda, interface, logo,
  marca-d'agua, pt-PT ou Portugal; 65 takes aguardam ancora propria, tres bases
  exatas estao aprovadas e nenhuma geracao/upscale foi iniciada.
- Verificacao: `py_compile` e `node --check` passaram; 68 testes dirigidos
  passaram; a auditoria do projeto confirmou 68/68 contratos, timeline continua,
  todos os arquivos presentes e zero violacoes de geometria, duracao ou prompt.

## 2026-08-01 - Legenda e interface visivel barradas em MOVA e LTX-2.3

- Sintoma: um take LTX de boa qualidade gerou legenda falsa; uma nova tentativa,
  ao receber a lista negativa dentro do unico canal textual do runner de
  referencia, alucinou uma interface branca com letras.
- Causa: o backend Python oficial usado localmente nao oferece um canal negativo
  separado. A integracao anexava a lista proibida ao prompt positivo e acabava
  ativando os conceitos de tipografia e interface que deveria evitar.
- Correcao: o runner de referencia deixou de injetar o negative prompt no canal
  positivo. MOVA e LTX-2.3 agora executam tambem o gate
  `temporal_visible_text_v1`, que rejeita glifos persistentes de legenda e
  grandes paineis neutros de UI antes da revisao ou de qualquer upscale.
- Auditoria retroativa: o job `ff2582ea` foi barrado por
  `PERSISTENT_VISIBLE_GLYPHS`; `4720c886` por `HALLUCINATED_UI_PANEL`; e
  `ea9519ed` passou no gate visual, mas continua reprovado por movimento final.
- Verificacao: 17 testes dirigidos passaram, incluindo regressao sintetica de
  legenda; `py_compile` passou; Studio recarregado no PID `7444`; API e preview
  persistido continuaram acessiveis. Wan nao foi usado e nenhum upscale iniciou.

## 2026-07-28 - Watchdog do ComfyUI volta a recuperar a porta 8188

- Sintoma: o ComfyUI ficou offline por horas enquanto `Pemara ComfyUI Watchdog`
  registrava um reinicio por minuto, sem criar processo nem listener.
- Causa: dentro de `Invoke-Check`, a variavel local `$port` recebia uma hashtable
  de diagnostico. Como PowerShell nao diferencia maiusculas de minusculas, ela
  sobrescrevia o parametro numerico `$Port`; o launcher recebia
  `System.Collections.Hashtable` em vez de `8188`. O erro do subprocesso ainda
  era descartado por `Out-Null`.
- Correcao: o estado da porta passou a usar `$portState`; o launcher agora nasce
  em subprocesso assincrono com stdout/stderr proprios, enquanto o watchdog
  consulta `/system_stats` ate o cold start terminar. Isso elimina tanto o erro
  de tipo quanto o bloqueio por handles herdados do processo Python.
- Regressao: `ferramentas/gerador_sprunki/test_watchdog_comfyui.ps1` valida o
  parse, proibe atribuicao a `$Port` dentro de `Invoke-Check` e confirma o
  encaminhamento da porta canonica.
- Verificacao operacional: com a fila vazia, o processo da porta 8188 foi
  encerrado de forma controlada e somente a tarefa agendada foi acionada. Ela
  iniciou o PID `8576`, publicou `127.0.0.1:8188` e passou em `/system_stats`
  em 16,7 s; a tarefa voltou para `Ready` com resultado `0` e zerou as falhas
  consecutivas. Nenhuma geracao foi iniciada.

## 2026-07-27 - Fotos-base emolduradas no Maestro

- Sintoma: uma candidata ANCHOR podia vir como uma cena dentro de porta-retrato,
  borda decorativa ou letterbox, em vez de preencher o quadro 16:9.
- Causa: o prompt global exigia 16:9, mas não proibia explicitamente molduras,
  bordas, cartões, imagens inseridas ou barras pretas.
- Correção: o executor global agora exige composição `full-bleed, edge-to-edge`
  e veta picture/photo frame, decorative border, matte, card, poster, inset,
  screenshot, letterbox e pillarbox no prompt positivo e no negativo.
- Regressão: `test_anchor_prompt_requires_full_bleed_without_picture_frame`.

## 2026-07-27 - Retomada automática de lote ANCHOR após queda de energia

- A autorização explícita do lote GPU agora é persistida em
  `tools/anchor_executor_intent.json` antes de iniciar o subprocesso.
- Em reinício do Studio, somente lotes com essa autorização persistida são
  retomados; pedidos apenas registrados continuam sem consumir GPU.
- O executor remove a autorização somente após concluir com sucesso. Falha,
  queda ou reinício preserva o lote para nova retomada.
- O lock por projeto continua impedindo dois executores simultâneos.

## 2026-07-26 - ElevenLabs cloud integrado ao contrato local do Editor

- Corrigido o caminho de execucao que validava `elevenlabs_cloud`, mas caia no
  ramo de voz Windows em vez de chamar o provider ElevenLabs.
- As capacidades do provider passaram a aparecer em `/capabilities` e `/voices`,
  sem ativar cloud automaticamente; o recurso continua condicionado a
  `MAESTRO_VOICE_CLOUD_ENABLED` e a credencial no servidor.
- ElevenLabs, Chatterbox e SAPI agora terminam no mesmo WAV PCM 48 kHz/estereo,
  com ajuste de velocidade preservado e provenance sem texto/chave. Isso torna o
  asset indistinguivel para timeline, render e handoff CapCut Local.
- Adicionados testes de job cloud simulado, capacidades e normalizacao; a suite
  dirigida `test_voice_providers`, `test_capcut_handoff` e `test_editor_suite`
  passou com 36/36.

## 2026-07-23 - Fila de video reconciliada a partir do S10A

- Confirmado que os 11 jobs persistidos haviam perdido seus workers depois de `ENOSPC`: o S10A parou em 71/105 frames, mas permaneceu falsamente em `running` porque a gravacao do erro e a reconciliacao do take tambem ficaram sem espaco.
- A recuperacao de restart agora reivindica todos os jobs atomicamente, mantem os upscales em ordem FIFO persistida e segura o gate do Wan durante toda a fila de upscales. S10A passa primeiro; S10B-S12C e depois 06B/07B preservam a ordem.
- Falhas e cancelamentos terminalizam o job mesmo quando a persistencia do take falha. Cancelar um job sem worker tambem reconcilia o estado canonico do take, em vez de deixar `UPSCALING` ou `GENERATING` preso.
- O import do modulo deixou de executar recovery sobre a base real; a reconciliacao ocorre somente no startup FastAPI. Isso impede que testes ou ferramentas de diagnostico alterem jobs de producao ao importar `main.py`.
- Workspaces de frames sao removidos somente depois de o MP4 FHD ser validado, registrado no take e marcado `done`, evitando novo acumulo de scratch sem apagar fontes ou entregas.
- Verificacao: 49 testes passaram. O Radar elevado recarregou o Studio no PID 28288. S10A concluiu em 1920x1080, 24 fps, 105 frames e 4,375 s; seu scratch foi limpo e S10B assumiu automaticamente a GPU. Os dois pedidos ao diretor (06B e 07B) permaneceram `IN_PROGRESS`, sem mudanca de aprovacao.

## 2026-07-23 - Editor IA local: vídeo, voz, legendas e copiloto

- Implantado o Editor IA privado dentro do Maestro, com projetos, assets, timeline nas trilhas `video`, `voice`, `music`, `sfx` e `text`, revisões otimistas e jobs persistentes com estado, porcentagem, cancelamento, erro e resultado.
- O render usa FFmpeg com CPU como padrão e `h264_nvenc` como opção explícita quando detectado. Exports concluídos são registrados na pasta do projeto e podem ser exibidos ou baixados pela API, sem depender de nome solto no backend.
- Narração local ganhou fallback imediato por SAPI/Microsoft Maria pt-BR e Chatterbox Multilingual V3 isolado em `C:\PemaraAI\chatterbox`, com perfis de clonagem condicionados a consentimento explícito.
- Legendas automáticas usam Faster Whisper local com `device=cpu`, `compute_type=int8` e `local_files_only=true`; a transcrição entra como clipes de texto e respeita a revisão do projeto para não gravar resultado obsoleto.
- O copiloto usa Ollama somente em loopback e o modelo `qwen3.5:4b`, limita a saída a ações editoriais tipadas e separa revisão de execução. `POST /api/editor/projects/{projectId}/assistant` produz o preview; `POST /api/editor/projects/{projectId}/assistant/apply` revalida e aplica todas as ações em uma única revisão atômica. O raciocínio longo fica desligado neste fluxo, a resposta tem teto de tokens e o modelo é descarregado rapidamente para não reter VRAM da produção. Também foi publicada `POST /api/editor/projects/{projectId}/captions`.
- A instalação incompleta do Ollama foi reparada com o pacote oficial assinado. A instância isolada do Maestro fica em `C:\PemaraAI\ollama`, responde em `127.0.0.1:11435` e é monitorada pelo Radar; as bibliotecas oficiais também completaram a instalação antiga em uso, sem expor nenhuma porta na rede. O nome operacional `qwen3.5:4b` aponta para a variante instruct sem raciocínio longo, enquanto o modelo original foi preservado como `qwen3.5:4b-thinking`.
- Adicionado `ferramentas/ollama/INSTALAR_OLLAMA_MAESTRO.ps1` para reproduzir ou reparar essa instalação: ele exige espaço seguro, baixa apenas de `ollama.com`, valida Authenticode e a organização Ollama Inc., preserva os pesos existentes, fixa o endpoint em loopback e reaproveita o Radar em vez de criar outro watchdog. O parse PowerShell e o `-DryRun` passaram sem download nem alteração.
- Verificação concluída: `15/15` testes dirigidos do Editor e `23/23` no conjunto Editor + persistência generativa; smoke neural real do Chatterbox na RTX 5090; render CPU com MP4 H.264/AAC; legendas Faster Whisper CPU/int8; e copiloto real com `qwen3.5:4b`. A rota do Studio que já estava aberta respondeu em 9,3 s, produziu uma ação tipada e o `assistant/apply` a aplicou atomicamente da revisão 1 para a 2; a nova instância isolada produziu duas ações em 5,4 s e também passou no apply atômico. O teste mobile passou em 320 px sem overflow e com navegação das abas por setas. Os artefatos de smoke foram enviados à Lixeira e a fila real de vídeo continuou ativa.
- O E: chegou a 0 bytes livres durante a implantação; foi removido somente um fragmento `.incomplete` de 5.231.535.706 bytes, abandonado no cache do Hugging Face desde 18/07 e que nunca constituiu um modelo válido. Nenhum take, mídia ou modelo completo foi apagado; o volume voltou a ter 4,87 GB livres.

## 2026-07-22 - Maestro mobile em fluxo simples

- O app agora abre diretamente em `Takes` no celular e mostra quatro destinos no rodape: Inicio, Criar, Takes e Produzir. `Produzir` abre diretamente a fila e os comandos em lote; as outras areas continuam disponiveis no desktop.
- O projeto foi separado em quatro tarefas claras: `Para decidir`, `Producao`, `Todos` e `Aprovados`. A fila e os comandos em lote aparecem somente em Producao; o player concentra Aprovar e Reprovar, e as opcoes menos usadas ficam recolhidas.
- Cartoes deixaram de repetir o seletor tecnico de status. Gerar outra versao e enviar uma correcao ao diretor continuam disponiveis em `Opcoes deste take`.
- Takes bloqueados por `waiting_derived_anchor` deixaram de exibir apenas `Base pendente`: agora identificam a foto como referencia, explicam que falta uma imagem-ancora propria e impedem que a mesma foto seja repetida como slideshow.
- Adicionados `Preparar imagem-ancora` em cada take bloqueado e `Preparar todas as imagens-ancora` na fila de producao. Esses comandos criam pedidos canonicos da categoria `ANCHOR` para o diretor, sem reprovar o take, sem alterar aprovacoes e sem iniciar a GPU; depois da entrega e aprovacao da base, a geracao de video fica liberada.
- No celular, selecao de projeto virou uma faixa horizontal compacta, os contadores repetidos foram removidos e o player passou a aparecer na primeira tela. A atualizacao nao reconstrói a interface quando a fila nao mudou.
- Verificacao: 14 testes do contrato de projetos, `node --check` e Playwright em 320/768/1440 px, sem erro de pagina nem overflow; navegacao mobile limitada a quatro itens e botoes de ancora/producao/upscale validados sem tocar na GPU. Studio e ComfyUI foram recarregados administrativamente; a fila real permaneceu vazia.

## 2026-07-22 - Envio em lote e upscale FHD real

- Adicionados `Enviar tudo para producao` e `Enviar tudo para upscale 1080p`. A selecao em lote pula automaticamente itens ocupados, prontos ou sem base aprovada.
- O upscale agora usa o pipeline real Real-ESRGAN AnimeVideoV3 + NVENC, somente em videos aprovados, e devolve um candidato FHD para nova revisao. O job e persistente, retoma apos reinicio e impede novos Wan de disputar a GPU durante o passe.
- A fila unificada mostra Wan e upscale, progresso e posicao. Atualizacoes de job deixaram de reconstruir o player inteiro. O layout usa uma coluna no celular e duas em telas maiores, sem barra horizontal.
- Verificacao: 53 testes Studio e 15 gateway, `node --check` e `py_compile`. Playwright passou em 320/768/1440 px sem overflow. Dry-run real confirmou fonte 24 fps, Real-ESRGAN, 1920x1080 e `h264_nvenc` sem criar arquivo nem usar GPU. Studio recarregado pelo Radar no PID `32140`; fila vazia e 14 takes aprovados elegiveis para upscale.

## 2026-07-21 - Senha administrativa migrada para scrypt

- O login agora prefere `MAESTRO_ADMIN_PASSWORD_HASH` no formato `scrypt`, valida limites seguros de custo e compara o digest em tempo constante.
- A senha existente foi migrada com salt aleatorio, `N=32768`, `r=8`, `p=1`, sem mudar o que o proprietario digita. O campo de texto puro ficou vazio.
- A copia `.env.backup_20260704_nvidia` tambem foi saneada. A auditoria recursiva terminou com `0` arquivos `.env*` contendo `MAESTRO_ADMIN_PASSWORD` configurada em texto puro.
- Antes de apagar a ultima copia legada, a senha original foi verificada com sucesso contra o novo hash. Hash malformado, esquema diferente ou custo inseguro sao recusados.
- Verificacao: suite do gateway passou com 13 testes; o gateway foi recarregado pelo Radar e manteve as sessoes revogaveis existentes.

## 2026-07-21 - Sprunki mantido aberto 24/7

- A tarefa `Pemara Sprunki Watchdog` passou de uma verificacao dependente do usuario para `SYSTEM`, nivel alto, gatilho no boot e repeticao a cada minuto por dez anos.
- A tarefa pode rodar em bateria, nao e interrompida ao mudar para bateria, inicia assim que disponivel, ignora instancias duplicadas e limita cada verificacao a cinco minutos.
- O watchdog valida `127.0.0.1:5005/api/health`, religa o backend se necessario e tambem confirma `https://sprunki.pemaratech.com.br/`; o acesso publico continua protegido pelo login do Maestro.
- O instalador e reaplicado pelo reset elevado do Maestro. Execucao manual terminou com resultado `0`; health local retornou `status=ok` e o endereco publico respondeu HTTP 200 com login obrigatorio.

## 2026-07-21 - ACLs privadas e health sem falso positivo

- `.env`, backup saneado, credencial do Cloudflare e `dados/auth_sessions.json` passaram a aceitar somente o proprietario, SYSTEM e Administradores; a area `dados/studio` recebeu ACL privada herdavel para fotos-ancora e historico.
- A gravacao atomica de sessoes reaplica a ACL ao arquivo temporario e ao destino. O reset elevado corrige essas permissoes a cada inicializacao.
- `.gitignore` agora cobre backup de `.env` e `dados/studio/job_inputs`, alem das credenciais, sessoes e historico que ja estavam protegidos.
- O health consolidado deixou de considerar o ecossistema saudavel quando apenas um componente respondia. O estado e `online` somente com todos os servicos, `degraded` com falha parcial e `offline` se nenhum responder; o indicador visual segue a mesma regra.
- Verificacao final: 14 testes do gateway e 33 do Studio, health `12/12`, quatro hostnames publicos exigindo login, fluxo autenticado das tres ferramentas e edicao publica de um PNG `8x6`. O tunel reiniciou com a credencial protegida e nenhuma inferencia foi executada.

## 2026-07-21 - Cancelar e repetir trabalhos sem intervencao tecnica

- Novos jobs guardam todos os parametros repetiveis e copias privadas das imagens inicial/final em `dados/studio/job_inputs`, com limite de 64 MB e bloqueio de path traversal.
- O painel atualiza o historico ativo a cada cinco segundos e oferece `Cancelar`, `Tentar novamente` ou `Repetir` conforme o estado real do trabalho.
- O cancelamento e cooperativo e identificado por job: remove um prompt pendente do ComfyUI ou envia `interrupt` somente quando o `prompt_id` cancelado e o que esta executando. Jobs de providers externos confirmam o cancelamento antes de publicar o resultado.
- Repetir cria um novo job auditavel, ligado ao anterior por `source_job_id`, reutilizando parametros e arquivos persistidos. Nao foi implementada uma falsa retomada de latente; jobs interrompidos recomecam de forma explicita.
- Verificacao sem inferencia: seis testes novos cobrem persistencia de entrada, traversal, conclusao, cancelamento vivo, recuperacao apos reinicio, cancelamento Comfy por `prompt_id` e repeticao; a suite do Studio passou com 33 testes.

## 2026-07-21 - Ferramentas publicas pelo login, sem expor motores

- ComfyUI, Sprunki e Perplexica passaram a abrir pelo Maestro em subdominios autenticados. Todos apontam para o gateway `9501`; as portas reais continuam somente em `127.0.0.1`.
- A entrada de um clique usa codigo aleatorio de 60 segundos, vinculado ao hostname e consumido uma unica vez. Cada subdominio recebe cookie host-only proprio; a sessao central e removida antes do salto para o motor.
- O proxy de ferramentas usa allowlist fixa, suporta upload/download em streaming, cookies proprios da ferramenta e WebSocket bidirecional. Ollama, Studio e APIs auxiliares continuam sem superficie publica direta.
- O backlog TCP do gateway subiu de 5 para 128 depois que a carga paralela do ComfyUI revelou recusas de conexao pelo tunel. A validacao final carregou `45/45` assets com HTTP 200.
- WebSockets do ComfyUI e do Perplexica foram validados com status 101. O proxy reescreve Host/Origin somente no salto WebSocket interno, preservando o hostname publico em `X-Forwarded-*`.
- Verificacao: 11 testes do gateway e 27 do Studio passaram; os tres subdominios exigiram login sem sessao, abriram pelo handoff e exibiram suas interfaces reais. O ComfyUI publico terminou com 56 botoes e 2 canvases, igual ao acesso local. Nenhuma inferencia de GPU foi executada.

## 2026-07-21 - Gateway unico, sessao segura e historico persistente

- Superficie publica consolidada em `https://maestro.pemaratech.com.br/`; os subdominios diretos de ComfyUI, Sprunki, Perplexica, Studio e APIs auxiliares foram removidos do tunel e passaram a retornar `404`.
- Todos os processos gerenciados agora escutam apenas em `127.0.0.1`, inclusive Maestro, Studio, microservicos, Perplexica, Sprunki e Ollama. O reiniciador administrativo recarrega o conjunto de forma controlada com os mesmos binds.
- O login deixou de colocar o token interno no cookie e passou a usar sessoes aleatorias persistentes e revogaveis, cookies `HttpOnly`, `Secure` no acesso publico e `SameSite=Strict`, logout por `POST`, bloqueio temporario por falhas repetidas e respostas `401` para APIs sem sessao. O acesso por token na URL foi removido.
- O gateway recebeu cabecalhos de seguranca, erros externos genericos e suporte a `PATCH`, necessario para alterar os estados dos takes.
- Jobs generativos passaram a sobreviver a reinicios em `dados/studio/generative_jobs.json`; trabalhos interrompidos sao identificados e o Studio Criativo mostra o historico recente.
- A navegacao foi organizada em Criar, Projetos, Arquivos e Editar midia. A nova biblioteca indexa ate mil imagens/videos/audios existentes, transmite arquivos em streaming com suporte a `Range` e so carrega previews pesados quando solicitados.
- O proxy deixou de manter uploads e downloads inteiros na RAM: agora transmite em blocos de 1 MiB, preserva cabecalhos de `Range`, limita o tamanho maximo configuravel e remove cookies/identidade antes do salto para servicos internos.
- Verificacao: 7 testes de gateway/sessao e 24 testes do Studio passaram; acesso local e publico, logout, isolamento da LAN, nove hostnames fechados e interface desktop/mobile foram validados. O navegador terminou sem erros de console, respostas HTTP de erro ou overflow. Nenhuma inferencia de GPU foi executada.

## 2026-07-21 - Studio Criativo utilizavel pelo painel publico

- Arquivos alterados: `MASTER.py`, `services/studio/main.py`, `services/studio/video_workflows.py`, `app/index.html`, `app/assets/maestro.js`, `app/assets/maestro.css`, `reset_maestro_frontend.ps1`, `radar/radar_monitor.py` e testes de regressao.
- Problema: no painel autenticado `maestro.pemaratech.com.br`, o Studio informava ComfyUI online, mas nao carregava modelos; geracao e edicao retornavam 403. Mesmo localmente, o formulario de video podia ser bloqueado silenciosamente pelo navegador porque `720` nao era valido com `step=32`.
- Causa raiz: o proxy autenticado nao acrescentava a credencial interna ao encaminhar `/api/studio`; o backend 8029 nao lia a credencial do `.env`; e a geometria HTML divergia do contrato de multiplos de 16 dos workflows.
- Correcao: o proxy agora injeta o token somente no salto local e remove qualquer token enviado pelo navegador; o Studio le a credencial do `.env`; a API publica direta continua sanitizada. A bancada foi reorganizada como `Studio Criativo`, com criar imagem, editar imagem, animar foto e criar card, nomes amigaveis de motores, preview de quadro inicial/final, camera, intensidade, preservacao e ajustes tecnicos recolhidos.
- Verificacao: painel remoto exibiu 4 motores de imagem, 1 de edicao e 5 rotas de video selecionaveis; formulario image-to-video ficou valido em 1280x720 e enviou imagem inicial/final, camera, intensidade e perfil de preservacao; desktop e mobile passaram sem erros de console nem overflow; proxy/Studio/workflows passaram 22 testes; `node --check`, `py_compile` e parse PowerShell passaram; API publica direta permaneceu sem lista de modelos e recusou POST com 403. Nenhuma inferencia de GPU foi executada nesta correcao.

## 2026-07-09 - Studio generativo: timeout falso em renders de video

- Arquivo alterado: `services/studio/main.py`.
- Problema: renders de video Wan longos podiam continuar rodando no ComfyUI, mas o Studio marcava o job como erro `timed out` quando a consulta `/history` demorava a responder.
- Causa raiz: o polling do ComfyUI usava timeout curto e nao tolerava indisponibilidade momentanea durante render pesado.
- Correcao: `_queue_comfy_workflow` agora captura falhas temporarias de polling, atualiza progresso com mensagem de espera e continua tentando ate o timeout real do render.
- Verificacao: gerado preview `intro_preview_20260709_071533.mp4` com 2 takes, 12.07s, 1280x720, 30fps, 362 frames.

## 2026-07-09 - Video Global Engine: JSON obrigatorio para imagens e takes

- Arquivos alterados: `ferramentas/video_intro_jogo/run_intro_take_queue.py`, `ferramentas/video_global_engine/tools/enforce_take_image_json.py`, docs do `video_global_engine` e docs da intro.
- Problema: a regra de criar `.json` para imagens-base e takes ainda dependia de disciplina operacional e podia ser esquecida em testes futuros.
- Causa raiz: o runner validava status de imagem-base, mas nao bloqueava tecnicamente a ausencia de JSON lateral nem gravava metadata lateral para cada MP4 gerado.
- Correcao: o runner agora bloqueia imagem-base sem `.json` lateral aprovado, valida `image_file`, `prompt` e `validation_status`, grava JSON ao lado de cada take MP4 e grava JSON da montagem. Tambem foi criado auditor de sidecars para projetos por takes.
- Verificacao: `py_compile` passou; auditor registrou 25 imagens, 0 faltando e 0 invalidas; os 9 takes da fila validaram contra seus JSONs laterais.

## 2026-07-11 - Video Global Engine: metodo Veo/Kling por shot contract

- Arquivos alterados: `services/studio/main.py`, `app/assets/maestro.js`, `GERADORES_STUDIO.md`, templates e docs do `video_global_engine`, skill `pemara-video-motion-director`.
- Problema: o fluxo local de video ainda podia ser interpretado como prompt solto ou treino cego do Wan 5B, apesar dos resultados ruins e da pausa de GPU.
- Causa raiz: faltava um contrato de take semelhante aos motores fortes Veo/Kling: start frame, end frame, referencias visuais, camera, motion beats, variantes curtas e QC antes do final.
- Correcao: criado `docs/09_metodo_veo_kling_para_motor_local.md`, templates `prompt_templates.json` e `take_queue.template.json` agora incluem `veo_kling_shot_contract`, o registry registra perfis Veo/Kling e o Studio expõe `defaults.video_method_profile` e `providers.video_method_profiles`.
- Verificacao: JSONs validados, `py_compile` do Studio OK, `node --check` do frontend OK, Studio reiniciado na porta 8029 e `/api/generative/status` retornou `method=veo_kling_shot_contract` com video ainda pausado.

## 2026-07-16 - Maestro Filmes & Takes e primeiro HunyuanVideo-1.5 local

- Criada a area remota `Filmes & Takes`, com projetos reais, estados, QC e job de geracao 720p/30 por take.
- Instalado e carregado o HunyuanVideo-1.5 I2V FP16 com encoder e VAE em `D:\PemaraModels`.
- Criados workflows nativos para I2V 720p e super-resolucao temporal por latente 1080p, ambos sem EasyCache.
- Primeiro take real concluido: 121 frames, 1280x720, 30 fps, seed `24681357`.
- QC tecnico aprovou movimento/luz; QC narrativo reprovou a troca indevida da nota por cubo. O take nao foi promovido para upscale.
- Testes: 8 testes Python, `py_compile`, `node --check`, API ao vivo e interface movel sem rolagem horizontal da pagina.

## 2026-07-16 - Reversao do Hunyuan e restauracao do Wan A14B

- HunyuanVideo-1.5 foi removido da lista de producao apos reprovar comparacao direta contra os takes anteriores.
- O padrao do Maestro voltou para Wan2.2 A14B I2V Q4 HighNoise + LowNoise.
- O contrato de prompt cinematografico completo foi restaurado, incluindo identidade, camera, parallax, motion beats, camadas de movimento e negatives anti-substituicao.
- Nova variante Wan do take 01 preservou a nota e recuperou cabos, profundidade e explosao luminosa.

## 2026-07-16 - Preview de 15,6 s pelo metodo Manus

- O inicio deixou de ser um unico I2V e passou a usar seis microtakes de 2,7 s.
- Keyframes densas foram criadas com Qwen-Image-2512 e limpas com Qwen-Image-Edit.
- Animacao executada com Wan2.2 A14B Q4 HighNoise + LowNoise.
- Montagem final: 1280x720, 30 fps, 468 frames e 15,6 s.
- QC tecnico: zero eventos pretos e zero congelamentos acima de 0,5 s.
- Nenhum upscale/interpolacao final foi feito antes da avaliacao humana.

## 2026-07-16 - Watchdogs do Windows executam sem janelas de console

- Arquivos/tarefas: watchdogs ComfyUI, Sprunki, Studio Generative, Marketing e treino LoRA.
- Problema: tarefas interativas abriam janelas de PowerShell a cada 1-5 minutos.
- Causa raiz: as acoes agendadas e os instaladores chamavam `powershell.exe` sem `-WindowStyle Hidden`; alguns watchdogs repetiam o mesmo erro ao iniciar processos filhos.
- Correcao: oito tarefas existentes, onze scripts/instaladores e todas as chamadas filhas relevantes passaram a usar `-WindowStyle Hidden`, mantendo logs e supervisao ativos.
- Verificacao: parse PowerShell OK em 11 arquivos; execucao real de `Pemara ComfyUI Watchdog` terminou com `LastTaskResult=0`; auditoria encontrou zero watchdog PowerShell agendado sem modo oculto.

## 2026-07-16 - Eliminadas as chamadas interativas restantes do PowerShell

- Arquivos/tarefas: Marketing Fotos Reais, Marketing Card LoRA, Voice Operator, Video Studio Nightly e instaladores de treinos diarios/semanais.
- Problema: mesmo com os watchdogs principais corrigidos, tarefas interativas menos frequentes ainda podiam piscar uma janela na execucao diaria/semanal.
- Causa raiz: nove acoes agendadas e oito chamadas/instaladores ainda nao declaravam `-WindowStyle Hidden`.
- Correcao: todas as acoes PowerShell interativas existentes e seus instaladores/callsites passaram a executar em modo oculto; o watchdog de marketing antigo em memoria foi reiniciado pela tarefa corrigida.
- Verificacao: parse PowerShell OK nos oito arquivos alterados; auditoria global do Task Scheduler encontrou `0` acao PowerShell interativa sem `WindowStyle Hidden`; tarefa reiniciada terminou com `LastTaskResult=0`.

## 2026-07-20 - Wan A14B I2V: contrato de VAE e perfil 40anos restaurados

- Arquivos alterados: `services/studio/main.py`, `services/studio/watchdog_studio_generative.ps1` e `services/studio/test_wan_video_workflows.py`.
- Problema: os workflows A14B e Fun Camera falhavam com incompatibilidade de tensor `48 vs 16`; em um relancamento pelo watchdog, o perfil `pemara_estudio_40anos` tambem podia ser perdido e o Studio substituia `832x480/16fps` por `1280x720/30fps`.
- Causa raiz: os dois builders A14B carregavam `wan2.2_vae.safetensors` (latente WAN22 de 48 canais) embora o ComfyUI detectasse os modelos como WAN21 de 16 canais; a ativacao do perfil dependia somente de variavel de ambiente do processo.
- Correcao: A14B I2V e Fun Camera passaram a usar explicitamente `wan_2.1_vae.safetensors`; o caminho WAN22 nativo manteve `wan2.2_vae.safetensors`; o Studio agora consulta tambem a flag persistente `dados/flags/pemara_estudio_40anos.flag`, e o watchdog exporta a variavel correspondente ao relancar o servico.
- Verificacao: `py_compile` passou; 4 testes direcionados passaram; a fila ao vivo confirmou FP16 High/Low, VAE WAN21, `832x480`, `81f`, `16fps`, `20 steps`, CFG `5` e seed `5172401`; o Take 01 concluiu sem erro de tensor.

2026-07-20 | `E:/Pemara/novo_plano.md` + `ferramentas/video_global_engine/projetos/intro_ritmos_revolta/{README.md,take_queue_novo_plano_20260720.json,direction/*.json}` | A documentacao superior ainda permitia interpretar 5 segundos como padrao para os takes futuros da abertura | A decisao de produtividade de 4 segundos ainda nao estava consolidada numa regra operacional unica | Registrado override para Take 06 em diante: bruto exato 97 quadros/24 fps e revisao HD exata 121 quadros/30 fps; Take 05 e as sete imagens aprovadas foram preservados | JSONs validados e valores cruzados entre fila, gate, manifests e documentacao; nenhuma GPU ou transferencia externa executada.
2026-07-21 | `E:/Pemara/novo_plano.md` + `ferramentas/video_global_engine/projetos/intro_ritmos_revolta/{take_queue_novo_plano_20260720.json,direction/*.json,review/REVIEW_INDEX_20260720.md}` | O Take 05 antigo seguia reprovado como slideshow e a segunda metade LTX da nova tentativa voltou na direcao errada, formou parede violeta e reacendeu luz quente | A mascara VFX inicial preservava 50% da frente na posicao original; a tentativa seguinte com inpainting removeu a frente mas deformou a fachada | Mantido o 05A LTX aprovado, refeito somente o 05B quadro a quadro com profundidade, neutralizacao de emissao e parallax, montado em 121f/30, tratado com Real-ESRGAN x4plus e NVENC; historico de descartes preservado e estado marcado como candidato pendente do usuario | QC independente passou 121/121 quadros, frente 52,2%->fora sem regressao, seam SSIM 0,992, luz quente -99,38%, SHA HD `522A0CED...`; MP4/JSON/relatorio copiados ao Google Drive com hash identico; treino continua pausado e Takes 06+ continuam 4 s.
2026-07-21 | `E:/Pemara/novo_plano.md` + `ferramentas/video_global_engine/projetos/intro_ritmos_revolta/{direction,takes,qc,conditioning_guides,review,FIXLOG.md}` | Correcao de estado: o usuario rejeitou o Take 05 SHA `522A0CED...` mesmo apos o PASS tecnico | O arquivo era um hibrido `LTXV13B + VFX deterministico + xfade`, mas a regra exigia um unico video continuo em Wan | Preservado o registro anterior como historia; candidato, bruto, microtake 05A, precheck e guias receberam estado `user_rejected`/`release_allowed=false`; `novo_plano.md`, indice e relatorio passaram a exibir a rejeicao inequivoca | JSONs alterados parseados; imagem 5 preservada; refacao Wan em andamento sob contrato dedicado; nenhuma GPU, treino ou transferencia externa executada nesta correcao documental.
2026-07-21 | `ferramentas/video_global_engine/projetos/intro_ritmos_revolta/qc/take05_wan22_fp16_startonly_clip_identity_20260721` | O Take 05 precisava ser refeito na rota correta, sem reutilizar o hibrido rejeitado | Gerado um unico video continuo Wan2.2 A14B FP16 start-only com CLIP Vision sobre a imagem aprovada | Bruto `97f/24 fps`, SHA `74F166BA25B09C21A800DBD7F793D11A982CF10FB69379F455BECC0D314ABFE1`, tratado para `121f/30 fps` em `1920x1080`, SHA HD `83902A4D11FC42E1F16A94DC36F54B76393928C7F1040FEBDC05BCBDF4C1FC83` | QC tecnico e visual passou; revisao humana permanece pendente; candidato nao e master; o hibrido SHA `522A0CED...` continua rejeitado.

## 2026-07-21 - Takes 06/07 WAN e reprodução de candidatos no Studio

- Takes: o Take 06 foi refeito em um único passe Wan2.2 A14B FP16 start-only sobre a imagem `6.png`, com prompt visual isolado. O bruto `97f/24 fps` passou identidade, movimento e extinção da janela; o HD `121f/30 fps` tem SHA `A39DA4C24192EFEE3583974D4013388BFEFDE85E2839503CF948526D6AB9BA60`. O Take 07 FP16 V07 foi tratado em HD com SHA `FF50405EE167FB024F4130A48BB6BDD86BE8A7D46A51BA1700DE43EF1839802E`.
- QC: ambos são vídeos generativos contínuos, não compositores 2.5D. Passaram decodificação integral, inspeção visual e medição de movimento/profundidade; permanecem `review_candidate_not_master` até decisão explícita do usuário.
- Studio: `project_manifest.json` passou a selecionar a fila vigente `take_queue_novo_plano_20260720.json`; a resolução da fila é confinada à raiz do projeto; prompts aprovados deixaram de receber um bloco genérico concatenado; candidatos registrados ganharam endpoint seguro com suporte a byte range e botão `Assistir` na tela Projetos.
- Verificação: 35 testes Studio e 7 testes dirigidos passaram, `py_compile`, `json.tool` e `node --check` passaram. Edge/Playwright abriu 7/7 candidatos, confirmou Takes 06 e 07 em `1920x1080`, `4,033 s`, reprodução ativa e console limpo. O Studio público foi reiniciado pelo supervisor autorizado no PID `32244`; `maestro.pemaratech.com.br` mantém login obrigatório e a API direta externa continua fechada.

## 2026-07-21 - Auditoria operacional, concorrencia e uploads do Studio

- O historico generativo recebeu lock entre processos, releitura antes de cada mutacao, temporario exclusivo, `fsync` e troca atomica. Duas instancias nao apagam mais os jobs uma da outra e jobs de um `worker_pid` vivo nao viram `interrupted` por engano.
- Uploads de imagem criativa agora sao lidos em blocos com teto de 25 MB por padrao. O editor tecnico sanitiza o nome do navegador, usa arquivo temporario exclusivo, limita cada midia e valida acao, formato, codec, corte e dimensoes antes de executar ferramentas.
- O painel de audio separa TXT/SRT/VTT de MP3/WAV. Sem provider configurado, as opcoes e o botao de geracao ficam bloqueados com explicacao e o manipulador recusa alteracao manual do formulario.
- O gateway passou a devolver `308` de HTTP para HTTPS. O reiniciador de frontend foi corrigido para trocar somente a porta `9501`, preservando Studio, Sprunki, Ollama e demais motores.
- A recuperacao automatica do Radar deixou de relancar o Studio em `0.0.0.0` e passou a usar `127.0.0.1`. A tarefa `Pemara_Radar` foi recarregada sem alterar os PIDs do Studio, gateway ou Sprunki.
- Saidas tecnicas agora recebem caminho unico mesmo quando operacoes simultaneas usam o mesmo nome. O isolamento de voz acompanha corretamente o nome temporario entregue ao Demucs.
- Verificacao: 41 testes do Studio e 15 do gateway passaram; `py_compile` e `node --check` passaram; browser em 320/768/1440 px terminou sem overflow nem texto corrompido. Provas reais leves concluíram ajuste PNG, WAV para MP3 e edicao H.264 por CPU. O Studio ativo e o PID `30956`, o gateway `34740` e o Sprunki permaneceu aberto no PID `36856`.

## 2026-07-22 - Rolagem unica e refacao clara de takes no Maestro

2026-07-22 | `app/assets/maestro.css:1258,1455,1465,1652` + `app/assets/maestro.js:1301,1317,1391,1448` + `app/index.html` | A lista de takes prendia o gesto, rolava devagar e misturava decisao humana com estados internos | Playlist/projetos tinham scroll vertical aninhado e overscroll contido; abrir um take reconstruia toda a lista; o seletor expunha QUEUED/GENERATING como opcoes manuais | Pagina virou a unica rolagem vertical, cards fora da tela usam content-visibility, abertura do player preserva o DOM/scroll, seletor mostra apenas decisoes revisaveis e REJECTED oferece `Gerar substituto` com explicacao de fila | `node --check` passou; Playwright mediu overflow visivel e zero overflow horizontal em 1024/390/320 px; logica retornou `Gerar substituto` e `Na fila...` nos estados corretos.

2026-07-22 | `apps/maestro_android/app/src/main/java/com/pemaratech/maestrostudio/MainActivity.java:217` + `apps/maestro_android/app/build.gradle:13` + `services/studio/main.py:1294,1370` | O Android comprimia a pagina desktop e jobs pendentes pareciam estar todos renderizando | WebView usava overview zoom-out e o poll do ComfyUI nao distinguia prompt pendente de prompt ativo | Overview desativado mantendo viewport responsivo; APK beta.2 gerado; backend agora informa `Na fila do ComfyUI — posicao N` a partir da fila real | 19 testes Studio passaram; Gradle `test lintBeta assembleBeta` passou; APK SHA-256 `9A8C9739D1D32C7EB6DAD68ADA6E2C86AC76ECCAC8BCB471FC9C6198933BF522`.

## 2026-07-22 - Envio ao diretor e download de takes no Android

2026-07-22 | `services/studio/video_projects.py:180,385,523,604` + `services/studio/main.py:3055,3154` | A reprovação registrava somente `REJECTED`, sem motivo estruturado nem fila consultável pelo diretor; qualquer candidato com URL conhecida podia solicitar `download=true` | O modelo de take não possuía solicitação de correção nem regra de liberação de arquivo no servidor | Cada reprovação pode criar um pedido obrigatório com categoria, motivo, histórico e estados `PENDING/IN_PROGRESS/DELIVERED`; a API ganhou inbox canônico `/api/video-projects/director-requests`; o download é autorizado no backend somente em `READY/APPROVED/UPSCALING/FINAL` | 21 testes Studio passaram; API ativa retornou inbox vazio, bloqueou S04A reprovado com HTTP 409 e serviu S03A aprovado com HTTP 206, `Content-Disposition: attachment` e byte range.

2026-07-22 | `app/assets/maestro.js:1281,1435,1458,1662` + `app/assets/maestro.css:1320,1428,1660` + `app/index.html:277,482` | No celular não havia caminho claro para explicar uma reprovação nem salvar um take liberado sem acesso remoto | A interface misturava a mudança de estado com regeneração e oferecia apenas reprodução/abertura do arquivo | `Reprovado` agora abre formulário acessível `Enviar ao diretor`, exige problema e correção desejada, preserva o vídeo anterior e bloqueia substituição sem pedido ativo; o player mostra `Baixar vídeo` apenas quando `canDownload=true` | `node --check` passou; Playwright validou 320/390/1024 px sem overflow, foco inicial no formulário, geração bloqueada sem motivo, payload estruturado e URL de download correta; assets novos foram confirmados no domínio público.

2026-07-22 | `apps/maestro_android/app/build.gradle:13` + `apps/maestro_android/app/src/main/java/com/pemaratech/maestrostudio/MainActivity.java:220` + `apps/maestro_android/README.md` | Era necessário entregar o fluxo de revisão/download num instalador identificável para o celular | A beta.2 já continha o downloader HTTPS autenticado, mas não identificava esta entrega conjunta | Versão elevada para `1.0.0-beta.3`; downloader existente continua usando cookie da sessão, origem HTTPS confiável e seletor nativo de destino, sem permissão ampla de armazenamento | Gradle `testBetaUnitTest lintBeta assembleBeta` passou; APK v2 assinado, pacote `com.pemaratech.maestrostudio.beta`, versionCode 3, SHA-256 `BF24529B6083932E943E780298CB6538CF59522EB4B253B26154CDAC3AF1A3ED`.

2026-07-22 | Automação Codex `maestro-pedidos-ao-diretor` | A caixa do diretor era consultável, mas não acordava esta tarefa quando surgia um pedido novo | Não existia monitor ligado à conversa nem deduplicação por `requestId` | Criado heartbeat local a cada 5 minutos, preso a esta tarefa, que consulta a inbox, registra IDs já avisados e notifica somente pedidos novos sem iniciar GPU | Automação criada pelo aplicativo em estado `ACTIVE`; inbox inicial confirmou 0 pedidos.

## 2026-07-22 - Direção completa da abertura por 20 microtakes

2026-07-22 | `ferramentas/video_global_engine/projetos/intro_ritmos_revolta/direction/intro_full_editorial_plan.json` + `project_manifest.json` + `take_queue_novo_plano_20260720.json` | Os sete takes de 4,033333 s cobriam somente 28,233331 s e não podiam sustentar a abertura musical de 67,369796 s nem três progressões visuais por legenda | O projeto ainda declarava 60 s, mantinha um take por arte e não possuía mapa de cortes internos ligado aos ataques reais da música | Medida a faixa e a legibilidade das seis legendas; travado plano de 20 microtakes, sendo 7 reaproveitáveis após revisão e 13 complementares, com cortes secos em ataques, câmera física, três planos, ação interna e saídas conectadas; duração canônica corrigida para 67,369796 s | JSON validado; soma dos 20 slots confirmada contra a duração integral; nenhuma geração, interrupção de job ou uso adicional de GPU foi iniciado por esta alteração.

2026-07-22 | `services/studio/video_projects.py` + `services/studio/test_video_projects.py` + fila da intro | Os 13 microtakes complementares precisavam aparecer no Maestro sem poder iniciar Wan antes da criação de novos enquadramentos aprovados | A aprovação de imagem era detectada por substring, portanto um estado como `not_approved` podia ser interpretado incorretamente como aprovado | Os takes 01B–07B foram intercalados na ordem editorial como `PLANNED`, com prompts e horários, e ficaram em `needs_derived_anchor`; o backend agora aceita somente estados afirmativos iniciados por `approved`, `aprovado` ou `aprovada` | API ativa exibiu 20 takes, os 13 novos com `keyframeApproved=false` e `canGenerate=false`; 12 testes passaram e `py_compile` passou; os cinco jobs já existentes permaneceram intactos e nenhuma nova geração foi iniciada.

## 2026-07-22 - Retomada automática dos takes após reinício

2026-07-22 | `services/studio/{main.py,generative_jobs.py,video_projects.py,test_generative_jobs.py,test_generative_control.py,test_video_projects.py}` + `app/assets/maestro.js` + `E:/Pemara/radar/radar_monitor.py` | Os Takes 03–07 ficaram interrompidos em 9%, os cartões continuaram em `GENERATING` e a tela recarregava em ciclo depois que um timeout isolado do ComfyUI fez o Radar reiniciar o Maestro inteiro | O histórico persistente detectava o worker morto, mas não possuía claim atômico nem retomada do take; a interface consultava repetidamente o mesmo job terminal; o Radar tratava uma falha única de quatro segundos como motivo para relançar todo o ecossistema | Jobs atuais de take agora são reclamados atomicamente pelo mesmo `jobId`, reconciliados para `QUEUED`, aguardam Comfy/Wan sem sumir e reutilizam o `prompt_id` quando ele ainda existe; se o Comfy perdeu fila e histórico, o job lógico é reenviado uma vez. O player bloqueia o ciclo de polling terminal. O Radar mantém Maestro/Studio ativos quando somente o Comfy falha e delega sua recuperação ao watchdog dedicado | `py_compile` e `node --check` passaram; 50 testes Studio e 15 testes de gateway passaram. Reinício administrativo real carregou Studio PID `37676`; Takes 03–07 mantiveram os cinco IDs originais com `resume_count=1`, fila Comfy confirmada em `1 running + 4 pending` e cartões reconciliados sem alterar aprovações.

## 2026-07-22 - Decisão no player e fila de produção visível

2026-07-22 | `app/{index.html,assets/maestro.js,assets/maestro.css}` + `services/studio/{main.py,video_projects.py,test_generative_control.py,test_video_projects.py}` + `scratch/test_player_review_ui.py` | No Android, abrir um vídeo separava o player das ações de revisão e obrigava localizar novamente o take numa lista longa; o menu ainda oferecia `Upscale 1080p` apesar de não existir job de upscale | O player mostrava apenas abrir/baixar, a fila real do ComfyUI não possuía visualização própria e `UPSCALING` era aceito como decisão manual | O take em exibição ganhou ações acessíveis `Manter em QC`, `Aprovar`, `Reprovar` e `Finalizar`, mantendo o vídeo carregado ao salvar; `Finalizar` exige aprovação e reprovação continua exigindo motivo ao diretor. A tela Projetos ganhou fila Wan real com item renderizando e posições pendentes. `UPSCALING` saiu das opções e o backend recusa esse estado até haver pipeline verdadeiro | 51 testes Studio e 15 testes de gateway passaram; `py_compile` e `node --check` passaram. Playwright em 390 px e 1024 px confirmou quatro decisões, `1 gerando · 2 aguardando`, PATCH de aprovação sem trocar o `src` do vídeo, zero overflow horizontal e zero erros de página. Studio ativo recarregado no PID `28260`; fila real estava livre e nenhuma GPU foi acionada por esta alteração.

## 2026-07-22 - Revisão segura de imagens-âncora no Maestro

2026-07-22 | `app/assets/maestro.js` + `app/index.html` + `scratch/test_anchor_review_ui.py` | A candidata entregue precisava aparecer como decisão humana no celular sem confundir a imagem nova com a foto de referência; uma tela antiga também não poderia aprovar silenciosamente outra candidata | O player usava `/anchor-image` para toda keyframe, inclusive imagens legadas sem registro de candidata, e os POSTs de aprovação/reprovação não carregavam o `requestId` visto pelo usuário | O player agora usa a imagem original registrada somente para candidatas/âncoras aprovadas e mantém `/thumbnail` para referências legadas; a foto de referência recebe rótulo de vídeo bloqueado; aprovar/reprovar envia o `requestId` como guarda contra tela obsoleta; cache dos assets avançou para `anchor-review2` | `node --check` passou; Playwright dedicado validou badge e card, abertura full-resolution, atalho `Revisar 1 imagem-âncora`, aprovação liberando `Produzir 1 take pendente`, rejeição com motivo obrigatório e novo pedido `PENDING`, além da regressão de imagem legada; teste responsivo existente passou em 320/768/1440 px sem overflow. Nenhum backend, serviço ou GPU foi alterado.

## 2026-07-23 - Worker de upscale UltraSharp com cache verificável e tentativa isolada

- Arquivos alterados: `services/studio/main.py` e `services/studio/test_generative_control.py`.
- Problema: o worker registrava AnimeVideoV3 em hardcode, aceitava o MP4 mais recente por nome/mtime e podia entregar o resultado de um job antigo depois de troca de tentativa ou reprovação; também iniciava o pós-processamento sem uma barreira própria de espaço livre.
- Causa raiz: o orquestrador não possuía contrato com o perfil canônico, fingerprint determinístico, validação criptográfica do sidecar/candidato, identidade de tentativa nem preflight de volume.
- Correção: o Studio agora usa `ultrasharp_balanced_75_25_v1`, executa dry-run sem GPU para obter fingerprint e bytes exigidos, mede o espaço livre real por filesystem, reutiliza apenas sidecar `2.0` com fingerprint/fonte/perfil/SHA do candidato exatos e `technical_pass`, bloqueia qualquer marca de rejeição, revalida `jobId`/attempt/fonte antes e depois da ferramenta, conserva falhas de infraestrutura como repetíveis e mantém o candidato como revisão humana pendente. Foi criado o endpoint separado `/upscale-preview`; `/preview` continua apontando ao ativo canônico.
- Verificação: `py_compile` passou; 28 testes de controle generativo passaram sem lançar processo de GPU, incluindo cache válido sem `Popen`, cache legado/rejeitado, falta de disco, limpeza do workspace fingerprintado, attempt obsoleto, perfil/CLI e rota de revisão separada.
- Ferramenta canônica: `ferramentas/video_global_engine/tools/postprocess_review_candidate_hd.py` aplica `4x-UltraSharp.pth` com blend neural/Lanczos `75/25`, conserva FPS e quantidade de quadros, copia todos os streams de áudio sem recodificação, publica H.264 CRF 10 em transação e mantém checkpoints por bloco para retomada segura.
- Aprovação: `services/studio/video_projects.py` grava o candidato como `PENDING_HUMAN_REVIEW`; somente `APPROVED` promove `output_active`, enquanto `REJECTED` preserva o ativo anterior e marca o sidecar de forma irrevogável para o cache. Um FHD pendente bloqueia nova geração e qualquer decisão diferente de aprovar ou rejeitar.
- Interface: `app/assets/maestro.js` reproduz o candidato pela rota dedicada, mostra `FHD para aprovar`, mantém a mídia correta após atualizar a tela e impede novo job enquanto a decisão humana estiver pendente.
- Verificação consolidada: 70 testes de upscale/estado/worker passaram, mais 11 subtests e 13 testes de workflows; `py_compile`, `node --check`, decodificação integral e teste real de cópia exata de áudio passaram. Nenhuma GPU foi acionada pela bateria de regressão.

## 2026-07-24 - Pedido de correção passa a criar o job de vídeo

- Arquivos alterados: `app/assets/maestro.js`, `app/index.html`, `docs/VIDEO_PROJECTS_API.md` e `services/studio/test_maestro_ui_contracts.py`.
- Problema: “Enviar pedido ao diretor” persistia o motivo na caixa canônica, mas não chamava a rota de jobs; por isso a solicitação existia enquanto a fila continuava mostrando zero. Ao recuperar o pedido existente, a duração fracionada ainda produzia automaticamente 122 quadros, valor inválido para Wan.
- Causa raiz: registro editorial e execução eram duas ações separadas na interface, embora o usuário concluísse o fluxo de correção em um único formulário; além disso, o cálculo padrão arredondava `duração × FPS` sem quantizar o resultado para `4n+1`.
- Correção: correções de vídeo agora registram o `directorRequest` e, após sucesso, iniciam o job substituto em `/takes/{takeId}/jobs`; pedidos `ANCHOR` permanecem somente editoriais e não acionam GPU. Se o segundo passo falhar, o pedido já registrado é preservado e a tela informa que ele não entrou na fila. Quadros inferidos passam a usar o múltiplo de quatro mais próximo mais um, mantendo valores explícitos sob validação estrita.
- Verificação: `node --check` passou; os 2 testes do contrato da interface e os 27 testes de projetos de vídeo passaram. A bateria de validação não iniciou jobs.
- Recuperação operacional: como o Studio elevado recusou reinício por acesso negado, o manifesto ativo de `intro_ritmos_revolta` recebeu `video_generation.frames=121` somente no take 02, permitindo recuperar o pedido atual sem alterar aprovação ou os demais takes.

## 2026-07-31 - MOVA deixa de cair em 10% por falta do compilador CUDA

- Problema: a primeira producao MOVA chegou a 10% e terminou com `torch._inductor.exc.TritonMissing`; uma segunda tentativa permaneceu carregando o mesmo modelo sem chance de concluir.
- Causa raiz: o preflight validava imports, CUDA e NVENC, mas nao exercitava os dois kernels `torch.compile` do codigo oficial. O ambiente isolado tinha PyTorch 2.12/CUDA 12.8, mas nao tinha o Triton 3.7 correspondente.
- Correcao: `triton-windows 3.7.1.post27` foi fixado somente no ambiente MOVA; o preflight agora compila e executa um kernel real na RTX 5090, e o Studio recusa o marcador de runtime se Triton, compilacao, NVENC ou capacidade Blackwell nao estiverem validados.
- Operacao: a tentativa presa foi cancelada pelo proprio endpoint do Maestro, sem duplicar job nem tocar na fila do ComfyUI.
- Segunda falha observada: depois de vencer a compilacao, a primeira difusao pediu um bloco de 6,73 GiB enquanto o PyTorch mantinha 6,90 GiB reservados e fragmentados. `expandable_segments` foi descartado porque o proprio PyTorch informou que nao e suportado nesta plataforma; o processo isolado agora usa o backend oficial `cudaMallocAsync`, validado em CUDA antes de liberar o painel.
- Exclusividade de GPU: antes de iniciar MOVA, o Studio exige fila Comfy vazia e chama `/free` para descarregar modelos/cache ociosos. Assim o painel nao inicia dois produtores de video concorrentes na unica RTX 5090.

## 2026-07-31 - Inicializacao unica do ComfyUI apos o boot

- Problema: apos a expansao para 128 GB, o ComfyUI ficou indisponivel na porta 8188 e o watchdog registrou varias tentativas de recuperacao.
- Causa raiz: as tarefas `PemaraComfyUI` e `Pemara ComfyUI Watchdog` estavam habilitadas simultaneamente e iniciavam o mesmo `main.py`; durante o boot frio, as instancias disputaram o banco SQLite, a GPU e a porta 8188.
- Correcao: o watchdog passou a ser a unica autoridade de inicializacao. O instalador e o reiniciador administrativo desativam a tarefa legada, e a auditoria do ecossistema alerta se as duas voltarem a ficar habilitadas.
- Regressao: `test_comfyui_task_contract.py` fixa o nome da tarefa canonica e exige a desativacao explicita de `PemaraComfyUI`.

## 2026-07-31 - MOVA-720p oficial preparado para RTX 5090 e 128 GB

- Modelo: `OpenMOSS-Team/MOVA-720p`, revisão fixa `8462bea9a317a3591279faeedfd3ca01b055cb59`, instalado em `D:\PemaraModels\mova\MOVA-720p`.
- Validação: 30/30 arquivos conferidos contra os metadados oficiais, 77.689.755.302 bytes, sem ausências nem tamanhos divergentes; código Apache-2.0 oficial fixado em `9b39667838a7c7ff2c367f5c5189d35c422878bd`.
- Isolamento: criado runtime próprio em `ferramentas/video_global_engine/engines/mova/.venv`, sem trocar as versões globais do Maestro/ComfyUI. Preflight confirmou RTX 5090, CUDA 12.8, BF16 e `h264_nvenc`.
- Painel: `Criar > Vídeo` ganhou modelo/preset MOVA, prompt direto, quadro inicial opcional, status de instalação, progresso, cancelamento e retorno do MP4 com áudio nativo sincronizado.
- Perfil: 1280x720, 193 quadros, 24 FPS, 50 passos, BF16, SDPA, group offload para RAM e codificação H.264 NVENC sem fallback CPU.
- Proteção: o backend exige pelo menos 112 GiB detectados; com 63,1 GiB atuais o modelo aparece instalado, mas a inferência fica bloqueada até a instalação física dos 128 GB.
- Verificação: `py_compile`, `node --check`, preflight real sem carregar pesos e 141 testes Studio passaram. O supervisor recarregou somente o Studio na porta 8029; ComfyUI permaneceu com fila vazia e nenhuma inferência MOVA foi iniciada.

## 2026-07-24 - Lote de seis takes aceita durações fracionadas

- Projeto afetado: `transicao_f1_f2_cold_iron_wan`, takes `S01A` a `S02C`.
- Problema: o painel informava `0 take(s) enviados` e `6 não entraram`, sem apresentar a razão de cada recusa.
- Causa raiz: o Studio ainda estava com a versão anterior carregada e inferia `156/151/144/150/151/150` quadros para as seis durações fracionadas; nenhum valor atende ao contrato Wan `4n+1`.
- Correção operacional: o supervisor Radar autorizado recarregou o backend, substituindo o PID `31244` pelo PID `14716`, com Studio e ComfyUI saudáveis.
- Resultado real: o mesmo lote entrou `6/6`, sem erros, com `157/149/145/149/153/149` quadros; a fila confirmou `1 executando + 5 aguardando`, sem alterar aprovação.
- Observabilidade: falhas futuras do lote exibem até dois pares `takeId: motivo do servidor` no aviso, em vez de mostrar apenas a contagem; o cache do JavaScript avançou para `batch-errors1`.
- Verificação: `node --check` passou e os 30 testes de contrato da interface/projetos de vídeo passaram.

2026-07-27 | `ferramentas/video_global_engine/projetos/transicao_f2_f3_raizes_ferro_wan/tools/execute_anchor_queue.py:36,65,149,176,265,293,357` + `tools/test_execute_anchor_queue.py` | O executor de fotos-base parou no take S05C e deixou 16 pedidos `ANCHOR` em `PENDING`, embora o job já tivesse concluído a imagem | Uma desconexão transitória `WinError 10053` durante o polling encerrava todo o processo; ao reiniciar, o script não reconhecia jobs já aceitos/concluídos e poderia gastar GPU repetindo a mesma imagem | Polling e entrega agora repetem falhas transitórias de rede, o início procura e retoma um job compatível criado depois do pedido atual, e `--recover-only` publica somente trabalhos já concluídos sem iniciar GPU; o job órfão `c08772ca34d84db0a686380df8919300` foi recuperado para S05C | `py_compile` e 4 testes de regressão passaram; a API confirmou S05C `DELIVERED`/`anchor_delivered_pending_user_approval` e a caixa caiu de 16 para 15 pedidos, sem alterar aprovação e sem iniciar geração.

2026-07-27 | `services/studio/{main.py,anchor_executors.py,test_anchor_executors.py,test_maestro_ui_contracts.py}` + `ferramentas/video_global_engine/tools/{execute_anchor_queue.py,tests/test_execute_anchor_queue.py}` + `app/{index.html,assets/maestro.js}` + `docs/VIDEO_PROJECTS_API.md` | Pedidos de foto-base ficavam registrados indefinidamente quando o executor avulso encerrava; após uma queda de energia, o lote também precisava ser reenviado manualmente | O Maestro não possuía rota canônica para iniciar/supervisionar ANCHOR, lock por projeto nem ação de retomada na interface; o motivo de rejeição humana não entrava no prompt de regeneração | Criada rota idempotente `/anchor-jobs`, gerenciador com validação de caminho/PID/lock persistente, executor global com retomada de job e rede, botões explícitos de GPU por take/lote e inclusão do motivo humano no prompt; S04C e S06B foram preservados e as 13 fotos restantes retomadas após a queda | A candidata-piloto S04C foi inspecionada em 1536x864, sem composição de porta-retrato; aprovação permaneceu humana. O JavaScript zerado durante a queda foi recuperado dos diffs persistidos do Codex e recebeu cópia forense fora da aplicação.

2026-07-27 | `app/{index.html,assets/maestro.js}` + `MASTER.py` + `services/studio/test_maestro_ui_contracts.py` | A tela falhava ao listar projetos porque chamava diretamente `https://api-studio.pemaratech.com.br/api/video-projects`, hostname deliberadamente removido do túnel seguro | Uma regressão restaurou o endpoint público antigo e ainda manteve a porta local obsoleta 8027, ignorando o proxy autenticado e o token interno injetado somente pelo Maestro | O Studio voltou a usar exclusivamente o caminho same-origin `/api/studio`, o fallback do gateway foi alinhado a 8029, o cache do JavaScript avançou e foi adicionado contrato que proíbe o hostname público e a porta antiga no frontend | `node --check`, `py_compile` e testes de contrato executados; validação HTTP confirmou o asset atualizado e a API local saudável, sem alterar fila, aprovação ou GPU.

2026-07-27 | `apps/maestro_android/app/{build.gradle,src/main/java/com/pemaratech/maestrostudio/{MainActivity.java,WebAppRefreshPolicy.java},src/test/java/com/pemaratech/maestrostudio/WebAppRefreshPolicyTest.java}` + `apps/maestro_android/{README.md,INSTALAR_NO_ANDROID.bat,docs/RELEASE_CHECKLIST.md,dist/MaestroStudio-1.0.0-beta.5.apk}` | O computador carregava os projetos depois da correção do proxy, mas o APK Android continuava exibindo a falha antiga | A WebView restaurava indefinidamente um snapshot completo da interface e mantinha o JavaScript anterior em memória mesmo depois da publicação do frontend corrigido | A beta.5 invalida somente o cache web quando o APK muda, recusa snapshots com mais de cinco minutos, atualiza ao voltar de segundo plano e faz a reconexão abrir uma URL nova; cookies e login são preservados | `testBetaUnitTest`, `lintBeta` e `assembleBeta` passaram; APK `versionCode=5`, pacote `com.pemaratech.maestrostudio.beta`, assinatura v2 compatível com beta.4 e SHA-256 `4A0393D8E11C37B1A4F8487A647EE655F2B6C57EF5EB1786749A915C5D5BD411`; nenhum celular estava conectado para instalação automática.

2026-07-27 | `app/{index.html,assets/maestro.js}` + `services/studio/test_maestro_ui_contracts.py` | No navegador móvel, entrar em `Takes` deixava `Carregando projetos...` para sempre; o único botão de atualização específico estava oculto pelo layout compacto e o botão do topo também não consultava projetos | A navegação apenas mostrava a seção, sem chamar `loadFilmProjects`, e `refreshAll` atualizava somente telemetria, saúde e status generativo | Entrar em `Takes` agora inicia a consulta automaticamente, `Atualizar` recarrega projetos quando essa seção está visível, chamadas simultâneas compartilham uma única Promise e o asset recebeu nova versão de cache | Os 7 testes de contrato e `node --check` passaram; Edge/Playwright autenticado no domínio público confirmou em viewport móvel e desktop `4 projetos`, detalhes/takes HTTP 200, `12 aguardando sua decisão`, zero alerta/erro de página e uma única consulta da lista no botão global; fila, aprovações e GPU não foram alteradas.

2026-07-30 | `apps/maestro_android/app/src/main/java/com/pemaratech/maestrostudio/{MainActivity.java,OpenCodeCredentialVault.java,TrustedUrlPolicy.java}` + `apps/maestro_android/app/src/test/java/com/pemaratech/maestrostudio/TrustedUrlPolicyTest.java` + `apps/maestro_android/{README.md,docs,INSTALAR_NO_ANDROID.bat,dist/MaestroStudio-1.0.0-beta.6.apk}` + `../../local_ai_qwen/{mobile/server.py,scripts/Use-MaestroPasswordForOpenCode.ps1,UNIFICAR-SENHA-MAESTRO.bat}` | O aplicativo móvel abria somente o Maestro; OpenCode, ComfyUI, liberação da VRAM e a senha separada do agente exigiam navegador/painel externo | Faltavam navegação nativa para os serviços privados e um fluxo seguro que validasse a senha já conhecida do Maestro antes de alinhar o Basic Auth do OpenCode | A beta.6 adiciona barra nativa Maestro/OpenCode/ComfyUI/Liberar GPU, confirmação da liberação, senha única validada pelo Maestro em loopback, cofre DPAPI no servidor e AES-GCM/Android Keystore no aparelho; a senha segue por HTTPS Tailscale e `stdin`, nunca por URL, argumento, APK ou log | `testBetaUnitTest`, `lintBeta`, `assembleBeta`, `py_compile`, verificações HTTP negativas/positiva, manifesto, zipalign e assinatura v2 passaram; APK `versionCode=6`, pacote `com.pemaratech.maestrostudio.beta`, 78.299 bytes e SHA-256 `D67FEDF4B19851808D5486CE60CD0301874684E57044DCFEFD9989768CDF499A`; nenhum Android estava conectado para o teste físico.

2026-07-30 | `services/dashboard/{main.py,test_dashboard_sensors.py}` + `services/studio/{main.py,hardware_status.py,restart_studio.ps1}` + `app/{index.html,assets/maestro.js}` + `frontend/app.py` + `reset_maestro_frontend.ps1` + `../../radar/radar_monitor.py` | O app móvel mostrava GPU `0%`, VRAM fictícia `0 / 16 GB` e temperatura/fan ausentes, embora a RTX 5090 estivesse sob carga; disco e rede também permaneciam em zero, e o endpoint duplicado do Studio devolvia todos os sensores zerados | Os processos residentes mantinham uma sessão/handle NVML invalidada após indisponibilidade/reset do driver e nunca tentavam reinicializá-la; a UI ocultava a falha com defaults numéricos, disco/rede chamavam `t.sleep` inexistente e o Studio mantinha outra sessão NVML além de consultar o CUDA do PyTorch em sua rota de health | O Dashboard agora serializa o acesso NVML, reinicializa a sessão e repete a leitura após handle inválido, recupera quando o driver carrega depois do serviço, distingue sensor opcional de zero real e mede disco/rede com `time.sleep`; a UI mostra indisponibilidade em vez de inventar hardware; o Studio passou a consumir somente o snapshot canônico por loopback e sua prontidão usa a rota leve `/api/status`; o reset supervisionado ganhou recarga explícita da porta 8007 | `py_compile`, parser PowerShell, `node --check` e 23 testes passaram; após reload supervisionado, Dashboard e Studio reportaram `NVIDIA GeForce RTX 5090`, `sm_120`, `31.84 GB`, temperatura/fan/potência reais coerentes com `nvidia-smi`, o asset HTTP 200 não contém mais o fallback de 16 GB, nenhuma flag de restart ficou pendente e o ComfyUI permaneceu no mesmo PID `21028`.

2026-07-30 | `apps/maestro_android/{app/build.gradle,app/src/main/res,branding,README.md,INSTALAR_NO_ANDROID.bat,docs,dist/MaestroStudio-1.0.0-beta.7.apk}` | O aplicativo ainda usava no launcher um desenho genérico de notebook com gráfico, sem a identidade oficial da Pemara | Os recursos `ic_launcher` eram vetores provisórios e não existia um mestre de marca preparado para as máscaras do Android | A beta.7 substitui o desenho pelo mascote oficial Pemara, com arte mestre de 1024 px, foreground adaptativo, variantes redonda/por densidade e glifo monocromático; a composição mantém antenas e fones na área segura | `testBetaUnitTest`, `lintBeta`, `assembleBeta`, manifesto, tabela de recursos, zipalign e assinatura v2 passaram; APK `versionCode=7`, pacote `com.pemaratech.maestrostudio.beta`, 1.454.983 bytes e SHA-256 `D49EE0F8DD1AAB5E93C505701DF4A8BB410E6FA86EEB7E19F179B102C09F0FCD`.

2026-07-30 | `MASTER.py` + `reset_maestro_frontend.ps1` + `app/{index.html,assets/{maestro.js,maestro.css}}` + `apps/maestro_android/{app/build.gradle,app/src/main/java/com/pemaratech/maestrostudio/{MainActivity.java,QwenReleasePolicy.java},app/src/test/java/com/pemaratech/maestrostudio/QwenReleasePolicyTest.java,README.md,docs,dist/MaestroStudio-1.0.0-beta.8.apk}` + `../../local_ai_qwen/{mobile/{server.py,qwen_activity.py,index.html,test_qwen_activity.py},scripts/{Start-MobilePanel.ps1,Restart-MobilePanel.ps1}}` | O Maestro mostrava carga geral da GPU, mas não respondia se o Qwen estava codificando nem em qual projeto; o botão podia solicitar `ollama stop` baseado apenas em modelo carregado | O painel consultava somente `/api/ps` e a consulta global do OpenCode ignorava que `/session/status` exige o diretório da sessão | O dashboard agora mostra estado ao vivo, quantidade/título das tarefas, pasta e origem OpenCode/Ollama; a liberação é fail-closed, exige ociosidade contínua e o APK beta.8 faz preflight nativo; o reset do frontend ganhou modo isolado que não inicia motores ausentes | Seis testes Python, quatro testes de política Android, `node --check`, `py_compile`, `testBetaUnitTest`, `lintBeta`, `assembleBeta`, revisão Chrome em 390 px e validação HTTP autenticada passaram; no estado real oito sessões em `D:\plataforma_multidiscilinar_logitudinal` produziram `409 qwen_active`, botão “Não mexer” desativado, OpenCode PID `7008` e runner PID `22384` preservados; APK `versionCode=8`, 1.483.355 bytes, assinatura v2 compatível e SHA-256 `C30F378A6B2A198B2FEEFB4B9F65283927A6EBA493F6AAC1430E27A543B4B673`.
## 2026-07-31 - MOVA 720p protegido contra pico de VRAM no offload

- Sintoma: um take MOVA em 1280x720, 193 quadros e 24 FPS caiu no primeiro passo ao solicitar mais 6,73 GiB com a RTX 5090 sem VRAM livre.
- Causa: o `group offload` em modo `leaf_level` usava prefetch por stream também no master 720p, mantendo a próxima camada na GPU durante a execução da camada atual e elevando o pico de memória.
- Correção: o runner mantém prefetch assíncrono somente no preview 640x352 e usa offload sequencial de baixa VRAM no master 1280x720, aproveitando os 128 GB de RAM instalados.
- Validação: teste de contrato garante que o perfil 720p não volte a ativar `use_stream`; a duração do TAKE-005 foi corrigida de 193 para 145 quadros, equivalentes aos 6 segundos especificados no arquivo do projeto.

## 2026-07-31 - Produtor MOVA e candidatos 480p antes do upscale

- Sintoma: um candidato de seis segundos em 720p/50 passos estimou seis a sete horas, tornando uma rejeição criativa cara demais.
- Correção: o Maestro passou a usar 832x480, 24 FPS e 25 passos para revisão, com presets de 4 s/97 quadros, 5 s/121 quadros e 6 s/145 quadros.
- Produtor backend: `mova_producer.py` analisa duração explícita, quantidade de fala, ação, reação e estado final; recomenda o menor take viável e bloqueia fala comprimida em duração insuficiente.
- Gate humano: candidatos 360p/480p retornam `PENDING_HUMAN_REVIEW` e `upscale_started=false`. O upscale permanece proibido até a aprovação explícita do proprietário.
- Medição real: no TAKE-005 de 6 s, os passos estabilizaram em cerca de 80 s e o pico ficou em aproximadamente 12,1 GB de VRAM; o orçamento do Produtor foi calibrado para 20–28 min (4 s), 26–34 min (5 s) e 33–42 min (6 s).

## 2026-08-01 - LTX-2.3 open-weight preparado para masters-base 720p

- Problema: era necessário preparar o LTX-2.3 para a RTX 5090/128 GB sem repetir o OOM do MOVA, sem retomar Wan e sem liberar enhancement antes da aprovação.
- Causa: o Studio não possuía runtime LTX isolado, gates de RAM/VRAM/disco, fluxo FP8 para Blackwell nem bloqueio server-side dos motores antigos; a instalação Windows oficial também resolveu inicialmente para PyTorch CPU.
- Correção: fonte e revisões oficiais foram pinadas, o PyTorch foi substituído pela roda CUDA 13.0, checkpoint FP8 e upsampler foram instalados, e o Maestro ganhou runner isolado 1280x720/24 FPS com áudio, offload CPU, NVENC, QC e aprovação humana. Wan agora é recusado no backend e a retomada automática de takes antigos fica desligada.
- Verificação inicial: CUDA/FP8/NVENC, tamanhos e SHA-256 dos dois pesos foram conferidos; `node --check`, parser PowerShell, `py_compile` e 165 testes Studio passaram. O runner Python de referência ainda depende do Gemma 3 gated (cinco shards, 24.374.793.024 bytes), que exige aceite e login local do proprietário na Hugging Face.

## 2026-08-01 - Primeiro teste real LTX-2.3 no Maestro, sem Wan e sem upscale

- Objetivo: repetir o TAKE-005 com exatamente o mesmo prompt, imagem-base e seed do teste MOVA, produzindo diretamente em 720p com áudio nativo.
- Backend: o Maestro passou a usar os nós oficiais LTX-2.3 do ComfyUI e o encoder local `gemma_3_12B_it_fp4_mixed.safetensors`; o checkpoint FP8 e o upsampler oficiais são expostos ao ComfyUI por junctions, sem duplicar cerca de 30 GB. Como o checkpoint já é destilado, a LoRA de destilação do workflow de desenvolvimento é ignorada. Nenhum modelo ou nó Wan entra no grafo.
- Resultado técnico: 145 quadros, 1280x720, 24 FPS, H.264/AAC 48 kHz estéreo, 6,041 s e 8.852.901 bytes. A renderização terminou em cerca de um minuto, sem OOM, com pico aproximado de 28,44 GB de VRAM. O QC de mídia passou (`-24,2 LUFS`, true peak `-10,3 dBTP`).
- Reprovação: o gate automático marcou `AUTO_REJECTED_MOTION`; a contact sheet confirmou deslocamento dos três personagens, reenquadramento/zoom, ausência de pose final estável e texto falso alucinado no canto inferior. A transcrição local ainda detectou um “hmm” indevido e `preferi continuar andando`, omitindo o `ou` e alterando `prefere` da fala solicitada. O arquivo permanece apenas como candidato reprovado no histórico do Maestro e nenhum upscale foi iniciado.
- Verificação: `py_compile` passou; os 137 testes coletados de `services/studio` passaram com código zero após desativar a captura defeituosa do pytest no console Windows. O job canônico é `02f80bcce21441c7b8e5dc9bb5a9e987`, com contact sheet e WAV de auditoria em `dados/logs`.

## 2026-08-01 - Gemma oficial completo e backend Python LTX-2.3 validado

- Instalacao: a autenticacao Hugging Face da conta `thiagoluzin` foi confirmada e os cinco shards do Gemma 3 gated foram completados em `D:\PemaraModels\gemma-3-12b`, totalizando 24.374.793.024 bytes na revisao fixa.
- Runtime: o backend `reference_python_pipeline` passou a usar `fp8-cast` prequant-aware com streaming CPU. O loader pinado foi corrigido para descartar escalas auxiliares do scaled-matmul que nao existem como parametros do modelo fp8-cast; o teste isolado carregou e desmontou o transformer em 30,5 s.
- Empacotamento: o MP4 final agora e preparado na mesma unidade da saida antes de `os.replace`, evitando `WinError 17` entre o temporario de `C:` e o acervo em `E:`.
- Prova real: o job `ff2582eaf9f94c81a089cce65e08ab62` terminou em 93,4 s, 1280x720, 145 quadros, 24 FPS, H.264/AAC, sem OOM e sem Wan. O produtor LTX foi recalibrado para 1,5-3 min em takes de 6 s neste hardware.
- QC: midia e frase passaram; Whisper detectou portugues com 0,9952 e transcreveu exatamente o texto. O take ficou `AUTO_REJECTED_MOTION` por hold instavel, legendas falsas, convergencia dos personagens e variacao de identidade. Sotaque pt-BR continua pendente da escuta humana. Nenhum upscale foi iniciado.

## 2026-08-01 - Segundo candidato TAKE-005 com novo seed e mesmo prompt LTX

- Autenticação: o token Hugging Face foi consumido diretamente da área de transferência sem ser impresso e autenticou a conta `thiagoluzin`. O download do Gemma oficial continua bloqueado por `403 restricted/not in authorized list` até a conta concluir ou receber o gate do Google; o material parcial foi preservado para retomada.
- Geração: o backend ComfyUI LTX já validado produziu o job `57c84197a423481d84b72e4dbb2ba273` com o mesmo prompt SHA-256 `F5DF515E2F69A9F4BA3610D9B36BA6C17160CA8F41B1437828CA201C18EAD507`, a mesma imagem-base e o novo seed `8214021526020102550`. Nenhum nó Wan ou upscale foi usado.
- Resultado técnico: 1280x720, 145 quadros, 24 FPS, 6,041 s, H.264/AAC e QC de mídia aprovado (`-20,7 LUFS`, true peak `-6,2 dBFS`).
- Reprovação: `AUTO_REJECTED_MOTION`, com delta médio final `7,5511` contra máximo `1,75`. A contact sheet confirmou aproximação dos três personagens, reenquadramento e legendas falsas persistentes. A transcrição local retornou `Pedro, quer parar para escutar de novo ou preferir continuar andando?`, alterando `prefere` para `preferir`. O candidato permanece somente no histórico do Maestro e o upscale segue bloqueado.

2026-08-02 | `services/studio/restart_studio.ps1:50` | Reiniciar o Studio preservava os jobs no disco, mas deixava a retomada automática desligada | O script administrativo fixava `STUDIO_AUTO_RESUME_TAKES=0`, contradizendo a fila persistente e obrigando reenvio manual | A retomada foi ativada mantendo o bloqueio dos motores não autorizados | Parser PowerShell aprovado; reinício supervisionado trocou o PID `27176` por `37352` e preservou os estados canônicos sem alterar aprovações.

2026-08-02 | `services/studio/main.py:1464,2833` + `services/studio/test_generative_control.py:117` | Takes LTX recuperados viravam erro `MOVA aguardando GPU` quando o próprio ComfyUI estava renderizando | A preparação exclusiva do backend MOVA era chamada antes da escolha do backend LTX e tratava a fila oficial LTX do Comfy como concorrente | O LTX oficial agora conserva a própria fila/VRAM do Comfy; somente o fallback Python externo solicita liberação da VRAM | 49 testes Studio e `py_compile` passaram; 21 takes afetados voltaram pela rota canônica, com 1 gerando e 20 em FIFO no primeiro check, zero erro de enfileiramento e 15 takes aprovados/prontos preservados.

2026-08-02 | `services/studio/ltx_runtime.py:284` + `services/studio/test_ltx_runtime.py:145` | O status ainda exibia `offload=cpu` mesmo usando os nós oficiais LTX do ComfyUI | O campo do perfil era constante e descrevia apenas o fallback Python | O diagnóstico passou a reportar `comfy_smart_vram` no backend oficial e `cpu` apenas no fallback | A API confirmou `comfy_core_official_ltx_nodes`, `cuda:0 NVIDIA GeForce RTX 5090`, pico observado de 99% de GPU, 25,2 GiB de VRAM e 575 W; o processo LTX avulso de alta RAM deixou de existir.

## 2026-08-03 - LTX-2.3 22B Dev com Two-Stage HQ no Maestro

- Instalacao: checkpoint oficial `ltx-2.3-22b-dev.safetensors` (46.149.344.974 bytes) e LoRA `ltx-2.3-22b-distilled-lora-384-1.1.safetensors` (7.605.507.256 bytes) foram baixados na revisao fixa `7caa482d5cd10a2eae6b34cb48f093ebc45a263e`; os SHA-256 locais coincidiram com o repositorio oficial.
- Perfil: novo motor `LTX-2.3-HQ-720p`, pipeline oficial `ti2vid_two_stages_hq`, Res2S, 15 passos, CFG video 3.0/audio 7.0, FP8 cast, CPU offload, 24 FPS, audio nativo e normalizacao 1280x704 para 1280x720 por NVENC.
- Maestro: HQ aparece com presets de 6 e 10 segundos, vira o default quando pronto, preserva o perfil destilado rapido e continua recusando Wan/Hunyuan. Takes de projeto aceitam o perfil `ltx23_dev_two_stage_hq_720p` com contrato fixo 8k+1.
- Protecao: nenhuma inferencia foi iniciada durante a instalacao. O render HQ fica atras da autorizacao explicita do take, dos gates de RAM/pagefile/VRAM/disco e da fila exclusiva de GPU; upscale permanece somente depois da aprovacao humana.
- Verificacao: `py_compile`, `node --check`, SHA-256 dos pesos e 100 testes direcionados de runtime, projetos, controle generativo e interface passaram.

## 2026-08-05 - Takes LTX com fala deixam de falhar silenciosamente depois da GPU

- Sintoma: o Maestro mostrava os takes 007-009 como liberados e aceitava `Produzir`, mas a fila voltava a ficar vazia sem candidato novo; onze renders foram consumidos e reprovados pelo gate de fala exata.
- Causa raiz: o Studio ainda usava `ltx_native_av_ptbr_sync`, deixando o LTX inventar portugues dentro do render. As transcricoes continham palavras trocadas, repeticoes e trechos alucinados; a rejeicao ocorria somente depois do uso caro da GPU.
- Correcao: criada a rota `ltx_ia2v_qwen_ptbr_sync`. Ela sintetiza primeiro a fala com o perfil local do personagem, exige correspondencia textual exata por ASR e somente depois condiciona o workflow oficial LTX IA2V com o audio aprovado pelo gate. Os takes 007, 008 e 009 foram migrados; dialogo nao entra no prompt visual e nenhum Wan foi habilitado.
- Protecao: se Qwen, referencia de voz ou texto exato falhar, o job encerra antes de iniciar o LTX. O video resultante continua exigindo escuta humana de voz e sincronismo no Maestro.
- Supervisor: o watchdog limitado deixou de consumir a flag administrativa antes do Radar elevado. A flag agora permanece ate o Radar confirmar um novo PID saudavel, evitando porta ocupada com codigo antigo.
- Verificacao: `py_compile` passou; os specs reais 007-009 resolveram os perfis Lira, Pedro e Pim sem vazar a fala no prompt visual; 104 testes direcionados passaram. O Radar substituiu o Studio PID 49892 pelo PID 56340 sem reiniciar o ComfyUI.

## 2026-08-05 - Take 008 bloqueado contra multidão e áudio curto

- Sintoma: o take 008 do Director Cut V2 criou uma sequência de humanos saindo da caverna, embora a foto aprovada mostrasse somente Pedro; o preview também terminava antes da duração planejada.
- Causa raiz visual: a consolidação juntou os takes legados 012 e 013. A âncora inicial registrava exatamente `Pedro`, mas o prompt exigia Pedro, Mariana, Rafaela, Zuno e Lira continuamente e ainda ordenava que o trio entrasse. O LTX inventou corpos para tentar reconciliar dados fisicamente incompatíveis.
- Causa raiz temporal: no workflow IA2V, o WAV Qwen de aproximadamente 5,7 s limitava o latente audiovisual; o take planejado em 10 s virou 4,53 s depois do retime 48→60.
- Correção: o 008 foi reprovado e refatorado para uma única cena de 10 s nativos com somente Pedro, caverna vazia e corte antes da travessia. O áudio condicionante agora recebe silêncio antes/depois até a duração integral do take. A âncora do elenco completo foi reservada exclusivamente para o take seguinte.
- Proteções: o preflight compara o elenco exato do sidecar da foto com o contrato do prompt e falha com `CAST_ANCHOR_MISMATCH` antes da GPU. Depois do render, amostragem facial bloqueia multiplicação ou entrada sequencial de humanos com `QC_CAST_SURGE` antes de publicar no Maestro.
- Evidência: o gate novo reprovou o próprio arquivo ruim, cuja amostragem detectou `1,2,1,2,2,3,2,2,0,0` rostos para um contrato de exatamente um Pedro. Os jobs `9444dfb2b2a047d8b44f46e8d8731112` e `ac99346cdebf4407aefdb41ec746c200` permanecem apenas como diagnóstico reprovado; nenhum upscale foi iniciado.
- Verificação: toda a suíte `services/studio` passou com código zero; o spec real do 008 resolveu 1280x720, 241 quadros, 24 FPS, 10 s, elenco da âncora `Pedro` igual ao elenco do prompt e áudio condicionante de 10 s. Nenhuma geração foi disparada durante a correção.

## 2026-08-05 - Take 007 corrigido na causa do dessincronismo audiovisual

- Sintoma: imagem e qualidade sonora foram aprovadas pelo proprietário, mas boca, ataque do instrumento e reações de Pedro/Zuno não obedeciam ao som; a falha já havia sido reportada e reprovada mais de uma vez.
- Causa temporal: o plano previa 7 s/169 quadros, mas o WAV sem silêncio inicial limitou a fonte LTX a 3,666 s/88 quadros. O retime aprovado de 48 para 60 FPS reduziu a revisão para 2,933 s, antecipando a voz e comprimindo toda a atuação.
- Regressão de estado: uma rejeição `AUDIO_SYNC` na rota condicionada trocava automaticamente o take de volta para `ltx_native_av_ptbr_sync`, descartando a estratégia Qwen/IA2V que deveria ser preservada.
- Correção do take: o 007 permanece `REJECTED`, foi recontratado para 8 s/193 quadros e recebeu relógio causal explícito: silêncio até 1,10 s, somente Lira articula, exatamente uma nota entre 2,75–3,60 s, reação de Pedro/Zuno somente depois de 4,20 s e hold final. O áudio aprovado foi preservado em WAV PCM 48 kHz estéreo de 8 s, SHA-256 `DD9A3F3F9996D4C3771F8F85FAA5B63DD427371233427031AABFB1FD988300C5`; nenhuma nova voz foi autorizada.
- Proteções: rejeições de sincronismo agora preservam rotas `ltx_ia2v_approved_ptbr_sync`/`ltx_ia2v_qwen_ptbr_sync`; o condicionamento remove silêncio residual antes de alinhar o onset; o prompt recebe a linha de tempo derivada do áudio; e o QC bloqueia `QC_AV_DURATION_MISMATCH` quando a fonte audiovisual não cobre a duração contratada.
- Verificação: `py_compile`, três regressões direcionadas e toda a suíte `services/studio` passaram com código zero. A âncora aprovada contém exatamente Lira, Pedro e Zuno. Nenhuma geração, upscale ou reinício do ComfyUI foi disparado durante a correção.

## 2026-08-05 - Take 007 dirigido publicado sem repetir geração rejeitada

- Primeira tentativa: o render `c9d16c6896ae4138900c176975695c6c` foi bloqueado antes do Maestro por `QC_MOTION_INSUFFICIENT`; a imagem inicial era reutilizada pelo workflow IA2V como guia no quadro final, puxando Pedro de volta para a mão no ouvido e anulando a mudança dramática.
- Correção estrutural: a rota IA2V usa a imagem aprovada somente como âncora inicial e conserva os 193 quadros/8 s completos. Sem uma imagem final separadamente aprovada, nenhum `LTXVAddGuide` pode reutilizar o quadro inicial em `frame_idx=-1`.
- Tentativa dirigida: o job `66b635bae57e433d893f75664e7f036e` produziu uma atuação nova com nota, reação de Pedro e estabilização de Zuno em sequência causal. Não foi feita terceira geração LTX.
- QC recalibrado: `freezedetect=-35 dB` marcava movimento estilizado sutil como congelamento; `-45 dB` preserva o bloqueio de vídeo realmente parado e aprovou o arquivo real com `freeze_ratio=0,2589`. O gate Haar passou a contar os dois rostos não humanos nomeados na linha de base, sem afrouxar a proteção contra excedente sustentado ou multidão.
- Publicação: o segundo render foi reaproveitado pelo job de recuperação `b2f5a08cf0454bf681a21f3d40441021`, interpolado com RIFE 4.25 e entregue em 1280x720, 60 FPS, 384 quadros e 6,4 s por NVENC, sem upscale. O áudio aprovado condicionou o LTX e permanece pendente apenas da revisão humana de pronúncia/sincronismo no Maestro.
- Evidência temporal: no nativo, voz ativa em aproximadamente 1,08–4,11 s; movimento dominante de Lira durante a fala/nota; Pedro reage em 5,25 s e Zuno depois do fim da fala. Duração, movimento, elenco e mídia passaram; a suíte completa `services/studio` passou com código zero.

## 2026-08-05 - Toque de violão sincronizado no take 007 aprovado

- Pedido: preservar integralmente vídeo, movimento e voz aprovados e acrescentar somente o som ausente do gesto de Lira no violão.
- Sincronismo: análise do ROI do instrumento em 60 FPS localizou o ataque dominante em `1,950 s`, quadro `117`. Foi sintetizada uma única nota baixa `E2`/82,4069 Hz por Karplus–Strong, com transiente de dedo, ressonância de corpo e cauda de 1,45 s.
- Mix: SFX PCM 24-bit/48 kHz estéreo, −28,1 LUFS e −11,8 dBFS de pico. Inserção com `adelay=1950`, `amix normalize=0` e limiter apenas de proteção; o primeiro ensaio com normalização automática foi descartado porque abaixava a voz.
- Preservação: o vídeo foi copiado sem recodificação; o SHA-256 do stream H.264 permaneceu `E777B74CCF3D2562748CDFFE1A4BE8BC332BA7B038AC2EBFA62D2A3AC8EE3144`, com 1280x720, 60 FPS, 384 quadros e 6,4 s. O ASR antes/depois permaneceu idêntico.
- QC: loudness total passou de −19,7 para −19,3 LUFS; true peak permaneceu −4,5 dBFS, sem clipping. O preview SHA-256 `1440F579A050560B55732A917FD0FE3AD9ADCE93039430D115ACFE1336E420C0` foi registrado pelo job `8581d98fb83b4b0a9743d5d1af33bc4d` no Maestro, sem upscale e pendente de escuta humana final.

## 2026-08-05 - Take 007 com toque de violão mais grave, tardio e longo

- Pedido do proprietário: a primeira nota soava aguda demais; deslocar o ataque para perto de `2,5 s` e prolongar a sustentação, preservando vídeo e voz aprovados.
- Correção: a revisão anterior `E2`/82,4069 Hz foi substituída por uma única nota `D2`/73,4162 Hz, ataque exatamente em `2,500 s` (quadro 150 a 60 FPS) e cauda de `2,60 s`. O transiente foi suavizado e a ressonância de corpo escurecida.
- Medição do SFX: WAV PCM 24-bit/48 kHz estéreo, `−26,3 LUFS`, true peak `−12,0 dBFS`, centroide espectral `387,48 Hz` e somente `1,158%` da energia acima de 2 kHz; a versão anterior media `875,34 Hz` e `13,207%`, confirmando timbre substancialmente menos agudo. SHA-256 `ED111A29E966CD66F642D1B643B4BAB4D143B33C539FBF116DE617C452246727`.
- Mix: o arquivo foi reconstruído a partir do preview original sem violão, impedindo acumulação das duas notas. `adelay=2500`, `amix normalize=0` e limiter apenas de segurança; a voz não foi editada.
- Preservação e QC: stream H.264 idêntico, SHA-256 `E777B74CCF3D2562748CDFFE1A4BE8BC332BA7B038AC2EBFA62D2A3AC8EE3144`, 1280x720, 60 FPS, 384 quadros e 6,4 s. Mix final `−19,8 LUFS`, true peak `−4,5 dBFS`, sem clipping e sem upscale. Preview SHA-256 `DE65D303AA20B404398D37279E1491555EEF4D9353CE223D8604738B88B8D94A` registrado no Maestro pelo job `4c7f57d8cae94aa981e104ba02ec0df9`, pendente de escuta humana final; o ASR apresentou variação fonética perto da palavra coberta pela nota e não substitui essa revisão auditiva.

## 2026-08-05 - Lote 010–012 desbloqueado sem permitir personagens surgindo da âncora

- Sintoma: o lote não enviava os takes 011 e 012 e o Maestro reportava `CAST_ANCHOR_MISMATCH`. A âncora do 011 continha somente Miro, mas a consolidação exigia Miro, Zuno e Lira; a âncora do 012 continha somente Pedro, mas o prompt exigia as três crianças e cinco criaturas.
- Causa: o Director Cut V2 havia fundido os legados 017+018 e 019+020 em planos contínuos, embora cada par possuísse fotos aprovadas com elencos mutuamente incompatíveis. Animar a fusão faria os personagens ausentes materializarem, duplicarem ou deformarem.
- Correção de direção: o 011 mantém 10 s e agora mostra somente as folhas girando, desacelerando e apontando o marco enquanto Miro reconhece a direção. O 012 mantém 9 s e agora mostra somente Pedro percebendo os sinais sobrepostos, pedindo uma tentativa por vez e motivando o corte para o plano coletivo seguinte. Os beats incompatíveis foram retirados dessas inferências, não apagados do acervo.
- Proteções: contratos fechados de elenco foram ajustados para exatamente `Miro` no 011 e exatamente `Pedro` no 012; âncoras finais incompatíveis deixaram de condicionar o LTX; duplicação, entrada de extras, materialização, pt-PT, texto visível e upscale pré-aprovação continuam bloqueados.
- Estado: os dois takes voltaram a `PLANNED`, sem erro e disponíveis para produção no Maestro. Nenhuma geração, upscale ou uso de GPU foi iniciado pela correção. Backup reversível e relatório estão em `qc/cast_anchor_refactor_011_012_20260805`.
- Verificação: os dois specs reais passaram o preflight (`011: âncora Miro = contrato Miro`, 241 quadros/10 s; `012: âncora Pedro = contrato Pedro`, 217 quadros/9 s), sem end keyframe. `py_compile` passou e os dois testes direcionados de mismatch/slots passaram; ComfyUI permaneceu com fila vazia.

## 2026-08-05 - Auditoria integral elimina o CAST_ANCHOR_MISMATCH recorrente no take 016

- Reincidência: depois da correção de 011/012, o botão avançou para o lote 016–017–018 e mostrou o mesmo erro. Nenhum job novo do 016 foi criado, provando que a falha permanecia no preflight anterior à GPU.
- Causa real: a âncora aprovada do 016 contém exatamente Mariana e Pedro, mas a consolidação dos legados 025+026 exigia também Rafaela, Zuno, Lira, Pim, Ticô e Miro. A âncora final do legado 026 tinha outro elenco e não poderia integrar um take contínuo sem materialização ou deformação.
- Correção: o 016 permanece com 10 s e agora contém somente Mariana e Pedro. As luzes/sons revelam fisicamente o padrão `três pulsos → pausa escura → dois pulsos`; Pedro identifica o silêncio e Mariana reage sem fala. A reorganização coletiva do legado 026 foi retirada desta inferência e preservada apenas como referência editorial para o corte seguinte.
- Contratos: elenco fechado em exatamente `Mariana, Pedro`, eixo esquerda→direita fixo, uma instância física por identidade, nenhuma criatura ou extra, end keyframe incompatível desativada, pt-PT/texto visível/duplicação/morphing/upscale pré-aprovação bloqueados.
- Auditoria da classe inteira: todos os 40 takes ativos foram testados pelo mesmo `get_take_generation_spec` usado pelo backend. Os 19 takes com foto-base aprovada passaram com igualdade de elenco; os 21 restantes foram classificados somente como aguardando foto-base. Restaram zero `CAST_ANCHOR_MISMATCH`.
- Verificação: 016 passou com âncora `Mariana, Pedro` igual ao contrato `Mariana, Pedro`, 241 quadros/10 s e nenhuma imagem final condicionante. `py_compile` e dois testes direcionados de mismatch/entity slots passaram. Nenhuma geração, upscale ou uso de GPU foi iniciado pela correção; backup e relatório estão em `qc/cast_anchor_refactor_016_20260805`.

## 2026-08-05 - Preflight passa a confiar no elenco visto nos pixels; take 018 corrigido

- Falha oculta: a âncora aprovada do 018 mostra visualmente somente Rafaela diante de três controles e cinco cartões, mas o sidecar registrava o elenco pretendido `Rafaela, Miro, Ticô, Pim`. O preflight antigo confiava em `required_objects.characters`, aprovava a inconsistência e mandava o LTX inventar as três criaturas ausentes. O job `dcc14e2b43404e84ad91a6f3a025c00e` foi então bloqueado por `QC_CAST_SURGE`, com até nove faces detectadas.
- Correção de backend: `_anchor_visible_cast` agora dá precedência a `visual_qc.actual_visible_characters` somente quando `cast_verification_status=VERIFIED`; um registro verificado sem lista válida falha fechado. O intento original do gerador continua preservado no sidecar para proveniência, sem ser tratado como prova dos pixels.
- Correção do take: o 018 permanece com 9 s e agora contém somente Rafaela. Ela afasta as mãos dos controles, espera o sinal fora de quadro, entrega sua fala pt-BR e termina sem pressionar botões. Miro, Ticô e Pim foram retirados do prompt, dos slots e do contrato; ninguém entra no quadro.
- Preservação: os previews anteriores foram removidos apenas da posição ativa e registrados no histórico como substituídos pelo contrato visual; nenhum arquivo foi apagado. A âncora recebeu um bloco `visual_qc` verificável com elenco real `Rafaela`.
- Verificação: o novo teste de regressão prova que o elenco visual verificado prevalece sobre o elenco pretendido e que divergência continua bloqueada. Três testes direcionados passaram, além de `py_compile`. A auditoria final retornou 19 specs aprovados, 21 aguardando futuras âncoras e zero erros; 016 resolve `Mariana, Pedro = Mariana, Pedro` e 018 resolve `Rafaela = Rafaela`.
- Runtime: a fila GPU/ComfyUI estava vazia. O reinício direto encontrou acesso negado ao processo elevado; a flag administrativa foi consumida pelo Radar, que trocou o Studio PID `53888` por `53068` e confirmou a porta 8029 saudável. Nenhuma geração ou upscale foi iniciado.

## 2026-08-05 - Recusa por pt-PT governa a próxima produção do take 017

- Sintoma: o proprietário reprovou o 017 por “Português de Portugal”, mas a tentativa seguinte repetiu o mesmo sotaque; o texto digitado na recusa parecia não produzir efeito.
- Causa raiz: o painel enviou a recusa na categoria `AUDIO_SYNC`, cuja precedência ocultava o motivo semântico. O backend então preservava `ltx_native_av_ptbr_sync` e pedia ao mesmo gerador nativo que repetisse a fala. Em cenas com dois falantes, o gate ainda incluía os rótulos `Mariana:`/`Pedro:` entre as palavras esperadas e resolvia somente o primeiro perfil de voz.
- Correção: motivos explícitos de pt-PT/português europeu agora são sempre `AUDIO_VOICE`; depois dessa falha o LTX nativo fica proibido e a rota muda para `ltx_ia2v_qwen_ptbr_sync`. Cada turno resolve seu próprio perfil local, passa separadamente pelo ASR e é montado na janela aprovada antes de condicionar imagem e lábios. Rótulos de falante permanecem apenas para exibição, fora do texto falado.
- Estado do 017: reprovado e preparado com Mariana em `0,70–5,36 s` e Pedro em `5,61–9,50 s`, usando os perfis distintos já registrados. A tentativa automática criada pelo monitor durante a correção foi cancelada ainda na fila, antes do LTX/GPU; o pedido automático foi cancelado e uma nova geração depende do botão do proprietário.
- Verificação: `py_compile` passou; a suíte completa do Studio passou com 242 testes; o spec real resolveu as duas vozes e `visualOnlyPass=false`; um smoke FFmpeg real montou dois turnos em um WAV de exatamente 4,0 s sem GPU.
- Runtime: depois de o job legítimo do 018 sair da GPU, o Radar recarregou o Studio do PID `53068` para `47188`. A API devolveu o 017 como `REJECTED`, `canGenerate=true` e informou explicitamente que a voz nativa foi bloqueada; Studio e ComfyUI terminaram sem jobs ativos.

## 2026-08-05 - MOVA desinstalado; LTX exclusivo e Wan em reserva

- Escopo autorizado: remover integralmente o MOVA, manter somente o LTX atual como motor de vídeo ativo e conservar o Wan instalado como banco de reservas.
- Remoção física: foram apagados o modelo `D:\PemaraModels\mova\MOVA-720p`, o código-fonte de terceiros, o ambiente/runtime de integração e os diretórios exclusivos de auditoria, logs, scratch e lixo rejeitado do MOVA. Total inventariado removido: `78.068.368.608` bytes (aproximadamente `72,70 GiB`).
- Preservação: projetos e resultados não rejeitados permaneceram intocados. O LTX-2.3 atual foi preservado e validado; os pesos Wan, incluindo o par I2V high/low noise, permaneceram no disco.
- Política: o backend autoriza LTX por padrão, rejeita MOVA e somente autoriza Wan quando a chave administrativa `STUDIO_ENABLE_WAN_RESERVE=1` for ativada explicitamente. O reinício normal fixa essa chave em `0`.
- Painel: controles e presets MOVA/Wan foram retirados da operação normal; o cache do JavaScript recebeu nova versão. O status MOVA permanece apenas como tombstone compatível (`removed=true`, `ready=false`) para clientes antigos.
- Segurança: antes da exclusão, todos os caminhos foram resolvidos e comparados literalmente com alvos permitidos. Nenhuma geração, upscale ou inferência GPU foi iniciada durante a desinstalação.

## 2026-08-05 - Clipe completo registrado e reproduzível no Maestro

- Entrega: o master oficial `The_Smoking_Snake_Smoking_Snakes_Official_Clip_1920x1080_60fps.mp4` foi registrado no projeto `the_smoking_snake_18_takes`, com 1920x1080, 60 FPS, 186,096 s, H.264/AAC, 628.894.428 bytes e SHA-256 `95715670AC3E7750096476F8B6206C631777B4EB10CDBE0F4A5DAB1B8DEF1307`.
- Player: foi criado um proxy local de revisão de 53.292.701 bytes em `qc/review_proxies`, mantendo o master intacto. O endpoint de reprodução devolve o proxy e o download devolve o arquivo oficial, confirmado por respostas HTTP 206 e pelos cabeçalhos `proxy`/`master-download`.
- Painel: a tela de Takes ganhou uma área dedicada `Clipe completo`, com os botões `Assistir clipe completo` e `Baixar master FHD`. A entrega não é contabilizada como 19º take: o painel continua mostrando os 18 takes de produção e abre o master pelo player do projeto.
- Compatibilidade sem interrupção: como o Studio executava o lote de upscale dos Takes 05–18, o filme foi exposto imediatamente por um registro compatível `MASTER`; a interface o promove para a área dedicada e o backend novo o oculta da lista normal no próximo reinício seguro. Nenhum job ativo foi cancelado ou reiniciado.
- Verificação: 52 testes de projetos e 17 contratos de UI passaram, além de `node --check`, `py_compile` e validação dos dois JSONs. O navegador real confirmou a área dedicada visível, contagem `18`, player e download corretos, revisão indevida oculta, zero erros de console e zero respostas HTTP com falha. Evidência: `dados/logs/maestro_full_clip_dedicated_final_20260805.png`.

## 2026-08-06 - Take 018 recuperado e produção corrigida para lotes rolantes de três

- Sintoma: seis gerações consecutivas do take 018 foram ocultadas por `QC_CAST_SURGE`; o botão de produção mostrava apenas um take em vez de três.
- Causa visual: o Haar frontal classificava flores do vestido, grafismos dos cartões e arquitetura como rostos. Inspeção integral confirmou somente Rafaela; a contagem bruta chegou a quatro, mas a confirmação de olhos/óculos encontrou no máximo um rosto real.
- Proteção preservada: o detector `opencv_haar_eye_verified_sampled_face_surge_v2` aprovou o 018 de uma Rafaela e continuou bloqueando o candidato histórico que realmente criou uma multidão.
- Recuperação sem nova inferência: o prompt ComfyUI já concluído `11074ab6-2ecd-4dd1-903f-8e1ba56f830c` foi reaproveitado com submissão de `/prompt` explicitamente proibida. O preview final 1280x720/60 FPS/434 quadros apareceu no Maestro como `READY`; apenas a fala aguarda escuta, pois o ASR não confirmou a palavra inicial `Combinado`.
- Causa do lote unitário: o agrupamento fixo 016–017–018 continha 016 já pronto e 017 com tentativa cancelada, restando somente 018 elegível. A política passou a preencher três slots rolantes com os próximos takes aptos, aceita `rerender_required` após cancelamento e continua sem saltar fotos-base ausentes.
- Segurança de GPU: três jobs entram por lote no Maestro, mas a RTX 5090 continua executando um workflow LTX por vez em FIFO; três modelos simultâneos excederiam a VRAM e repetiriam os travamentos anteriores.
- Verificação: `py_compile`, `node --check`, QC A/B sobre o 018 correto e o crowd histórico, e toda a suíte Studio com 252 testes passaram. Studio/Frontend foram recarregados; a fila ComfyUI terminou vazia. Relatório em `dados/qc/take018_cast_surge_20260806/report.md`.

## 2026-08-06 - Produção do Maestro passa a reservar trincas indivisíveis

- Sintoma: o botão de produção podia reduzir o lote dinamicamente e iniciar somente um take elegível, obrigando o proprietário a voltar ao painel entre renders e confundindo conclusão de geração com aprovação humana.
- Causa raiz: a política definia `batchSize=3`, mas não exigia lote completo, não registrava identidade/posição da trinca nos jobs e confiava apenas no estado momentâneo dos takes. Uma mudança de `READY`, `REJECTED` ou `ERROR` encolhia a seleção sem bloquear a autorização parcial.
- Correção de backend: `require_full_batch=true` tornou os três slots indivisíveis; cada autorização recebe `productionBatchId`, índices `1/3`, `2/3`, `3/3` e metadados persistidos. Um lock impede dois cliques concorrentes, um lote ativo bloqueia o seguinte e o preflight dos três ocorre antes da primeira reserva. Foto-base ausente ou apenas dois elegíveis devolvem `409` sem iniciar job isolado.
- Correção do painel: o botão distingue `Trinca bloqueada`, `Trinca incompleta`, `Produzir 3 takes` e `Trinca em produção`. Ele permanece desativado enquanto qualquer job da trinca estiver ativo e libera automaticamente, em até um ciclo de atualização de cinco segundos, quando os três chegam a estado terminal; aprovação/reprovação humana pode ocorrer depois.
- Proteção da RTX 5090: três jobs ficam comprometidos pelo mesmo clique, mas os workflows LTX continuam em FIFO com um único render por vez, evitando três cargas simultâneas e estouro de VRAM.
- Estado real: Studio PID `35456` e frontend PID `37832` saudáveis; API confirma `batchSize=3`, `requireFullBatch=true` e fila vazia. O próximo lote tem 017 e 019 elegíveis e aguarda a foto-base obrigatória do 020; o 018 já está preservado para validação e não será regenerado só para completar a contagem.
- Verificação: `py_compile`, `node --check`, sete regressões direcionadas, 92 testes de controle/interface e a suíte completa do Studio com 255 testes passaram. Nenhuma geração, upscale ou inferência GPU foi iniciada durante a correção.

## 2026-08-08 - Qwen ocioso deixa de prender a GPU e passa a ser liberado pelo Maestro

- Sintoma: depois de terminar no OpenCode, o painel continuava mostrando “EM USO NO OLLAMA” e o
  Qwen podia manter aproximadamente 26–27 GB da RTX 5090 ocupados.
- Causa raiz: o OpenCode podia preservar uma sessão em `busy` mesmo sem cálculo; o monitor tratava
  essa marca como uso físico e até reportava `active` quando o modelo já estava descarregado.
- Backend local: atividade real agora é comprovada pelo runner NVIDIA, com fail-closed se o sensor
  falhar. Um watchdog do serviço libera o modelo após 30 segundos ociosos e funciona com o Maestro
  fechado; cálculo ativo continua bloqueando qualquer stop.
- Painel: o cartão Qwen ganhou chave **Liberação automática**, seletor de 15 segundos a 5 minutos,
  contagem regressiva e fallback **Liberar agora**. Sessão antiga do OpenCode aparece como sessão
  marcada, sem ser apresentada como consumo atual de VRAM.
- Arquivos: `app/{index.html,assets/{maestro.js,maestro.css}}`,
  `test_qwen_auto_release_ui.py` e `../../local_ai_qwen/{mobile,config,scripts,OPERATIONS.md}`.
- Verificação: `node --check`, 3 contratos do painel e 17 testes do serviço passaram. Edge headless
  confirmou a chave ligada, contagem regressiva, POST protegido e zero overflow em 390 e 1024 px.
  No teste real com `keep_alive=10m`, o watchdog descarregou automaticamente 31.366 MiB em cerca de
  30 segundos; `ollama ps` terminou vazio e a GPU voltou a 3.476/32.607 MiB.

## 2026-08-08 - Atalhos do Maestro passam a pedir reinicio ao supervisor correto

- Sintoma: `INICIAR_MAESTRO.bat` e `REINICIAR_MAESTRO.bat` executavam o mesmo boot watchdog,
  terminavam em `pause` e o segundo nao solicitava o reinicio do Studio. Isso induzia cliques
  repetidos e, quando o reinicio era tentado diretamente, podia falhar por acesso negado ao processo
  administrativo.
- Correcao: `REINICIAR_MAESTRO.bat` agora chama `solicitar_reinicio_maestro.ps1`, que apenas cria
  as flags fixas de frontend e Studio, aguarda sua remocao pelo Radar administrativo e valida HTTP
  das portas oficiais. O script nao mata processos. `INICIAR_MAESTRO.bat` preserva a funcao de boot,
  mas sem pausa. O atalho `PARAR` permanece explicitamente sem acao destrutiva, evitando derrubar
  o servico para todos sem uma janela administrativa.
- Verificacao: o contrato `test_maestro_operator_restart_contract.py` cobre as flags, a delegacao
  ao Radar, a remocao de `pause` e a distincao entre iniciar e reiniciar. Nenhum job de imagem ou
  video foi iniciado por esta correcao.

## 2026-08-08 - Gauntlet passa a renderizar somente pelo LTX-2.3 local

- Causa raiz: o piloto herdava o perfil Wan bloqueado; depois da migracao para LTX, o template
  oficial 2.3 ainda assumia nomes e ordem de widgets de uma versao mais nova do ComfyUI.
- Correcao: o padrao sem perfil passou a LTX-2.3 720p/24 fps; os tres takes do Gauntlet receberam
  o contrato LTX explicito. O adaptador usa os nomes compativeis do Comfy local, fixa o audio em
  lote 1/24 fps e informa explicitamente MP4/H.264 ao SaveVideo.
- Protecao operacional: o status do Studio consulta os nos LTX carregados pelo Comfy antes de
  anunciar o motor como pronto. O atalho de reinicio tambem reconhece o Radar elevado pelo pidfile,
  sem matar processos diretamente.
- Resultado: takes 01, 02 e 03 finalizaram READY em 1280x720, 24 fps e 4 segundos; fila vazia,
  sem fallback Wan. A aprovacao continua humana no Maestro.
- Verificacao: 86 testes direcionados passaram; o primeiro job real percorreu fila, sampler e
  SaveVideo. Os tres MP4s foram gerados e validados pelo pipeline LTX.

## 2026-08-10 - `manus_motion` deixa de exigir Wan2.2 A14B HighNoise/LowNoise

- Sintoma: selecionar `Mais movimento interno` bloqueava qualquer workflow que nao resolvesse
  exatamente para o par Wan2.2 A14B I2V HighNoise/LowNoise, inclusive MiniMax H3.
- Causa: uma validacao global vinculava uma preferencia de condicionamento a uma familia de
  checkpoints antes do despacho para o workflow especifico.
- Correcao: `manus_motion` agora e aceito independentemente do modelo. O A14B preserva seu caminho
  especializado sem CLIP Vision; os demais modelos seguem com seu condicionamento nativo.
- Verificacao: regressao cobre MiniMax H3, Wan sem par A14B e o comportamento especializado do
  A14B. Compilacao Python e suite Studio tambem foram executadas antes da recarga do servico.

## 2026-08-10 - Duracao e FPS passam a controlar automaticamente a grade temporal MiniMax H3

- Sintoma: o painel expunha `Frames` e enviava valores comuns como 241, que o H3 recusava porque
  aceita somente 124-362 quadros no formato `17k+5`.
- Causa: duracao era um campo exclusivo de audio; o backend de video ignorava esse valor, mantinha
  FPS H3 fixo em 24 e delegava ao proprietario a contagem tecnica de quadros.
- Correcao: o painel agora mostra somente duracao e FPS para o tempo do video. `Frames` virou campo
  interno e e alinhado automaticamente por modelo; o backend recalcula o H3 na grade `17k+5`,
  aplica o FPS escolhido ao `CreateVideo` e informa quadros e duracao efetivos no resultado.
- Limites automaticos: a interface ajusta a duracao ao intervalo possivel para o FPS selecionado;
  H3 usa 124-362, LTX usa 49-241 em `8k+1` e os demais workflows usam `4k+1` no painel.
- Verificacao: `py_compile`, `node --check`, 12 regressoes H3/Minimax, 20 contratos de interface e
  7 testes Wan passaram; nenhuma geracao GPU foi iniciada.

## 2026-08-11 - MiniMax H3 ganha texto para video direto no Maestro

- Sintoma: o painel dizia criar video por prompt, mas oferecia apenas `Animar foto`; o construtor
  H3 recusava qualquer workflow sem `base_image_name`, apesar de o no oficial aceitar T2VA com
  `first_frame` e `last_frame` opcionais.
- Correcao: o painel ganhou o modo separado `Texto para video`, limitado ao checkpoint MiniMax H3.
  Nesse modo nenhum upload oculto e enviado, duracao/FPS continuam automaticos e a orientacao do
  prompt descreve a construcao integral da cena, sem as restricoes usadas para preservar uma foto.
- Workflow: `_build_minimax_h3_fl2va_workflow` agora adiciona `LoadImage` e `first_frame` somente
  quando existe uma ancora. O caminho antigo de animacao por imagem foi preservado sem mudanca de
  contrato.
- Correcao descoberta no navegador: o minimo dinamico H3 de `5.13` segundos tornava `10` segundos
  invalido quando o input usava `step=0.1`. O campo passou a `step=any`; a grade `17k+5` continua
  sendo a unica responsavel pelo alinhamento tecnico.
- Ativacao segura: o frontend consulta a capacidade `minimax_h3_text_to_video`; enquanto o processo
  antigo termina um render, o envio mostra espera de atualizacao em vez de cair no contrato antigo.
  Um watcher temporario exige fila e jobs vazios por 45 segundos, reinicia apenas o Studio, confirma
  a capacidade na API e remove a si proprio.
- Verificacao: `py_compile`, `node --check`, 22 contratos da interface e todas as regressoes H3
  novas passaram. Chrome isolado confirmou o botao, o H3 selecionado, upload oculto e o multipart
  com `mode=video`, duracao e modelo, sem `base_image`/`end_image`. Nenhuma geracao GPU foi iniciada
  pelos testes. A suite completa ficou em 314/315 por uma falha anterior sem relacao: o teste de
  QC de audio procura o take inexistente `006`.
- Robustez do acompanhamento: uma falha temporaria no proxy encerrava o polling do navegador e
  mostrava `ERRO` mesmo com o job ainda rodando no ComfyUI. O painel agora tenta se reconectar por
  90 segundos e, se a conexao continuar indisponivel, orienta usar `Atualizar` sem declarar falha
  da geracao; `Atualizar` recarrega imediatamente `Trabalhos recentes`, onde o job persistente
  permanece visivel. Chrome isolado simulou duas recusas de conexao, observou a mensagem de
  reconexao e concluiu no quarto polling sem inserir `ERRO` no chat.

## 2026-08-11 - MiniMax H3 libera duracao visivel de ate 15 segundos

- Causa: o H3 usa uma linha temporal nativa fixa de 24 FPS, mas o painel recalculava a grade
  `17k+5` usando o FPS escolhido como se ele fosse nativo. Em 60 FPS, os 362 quadros treinados
  eram comprimidos para 6,02 segundos em vez de representar aproximadamente 15 segundos.
- Correcao: no H3, o FPS nativo agora fica automaticamente em 24 e a duracao solicitada e
  convertida para a grade treinada de 124-362 quadros. O limite visivel ficou em 15 segundos;
  `15 s` produz 362 quadros e duracao efetiva de 15,04 s.
- Interface: o painel ganhou botoes grandes de `5 s`, `6 s`, `10 s` e `15 s`, mantendo tambem o
  campo numerico de segundos para ajuste direto. Opcoes fora do alcance do motor selecionado sao
  desabilitadas automaticamente.
- Verificacao: `node --check`, `py_compile`, 22 contratos da interface e 6 regressoes H3 passaram.
  Chrome isolado em viewport de celular confirmou `15 s -> 362 quadros -> 24 FPS`, o multipart
  enviado ao Studio e zero erros no console. Nenhuma geracao GPU foi iniciada pela validacao.

## 2026-08-11 - ComfyUI preserva o listener HTTP durante renders longos no Windows

- Sintoma: o Maestro mostrava novamente falha ao acessar `/api/studio/api/generative/job/...`
  enquanto o MiniMax H3 continuava usando a GPU. A porta local `8188` desaparecia, mas o processo
  ComfyUI permanecia vivo e o sampler continuava avancando.
- Causa raiz: o `ProactorEventLoop` padrao do Python 3.11 recebeu `WinError 64` no `AcceptEx` e
  fechou permanentemente o socket de escuta. O log registrou `Accept failed on a socket` em
  `127.0.0.1:8188`; portanto a falha era da camada HTTP do Windows, nao do checkpoint H3.
- Correcao: o ComfyUI local passa a criar `SelectorEventLoop` no Windows. O Studio reduziu o
  polling de historico/fila de um para cinco segundos, diminuindo em 80% as conexoes curtas.
  O watchdog registra o PID real do ComfyUI e adia qualquer reinicio quando esse processo ainda
  apresenta utilizacao de compute na GPU, mesmo se o listener tiver desaparecido.
- Recuperacao: um monitor isolado aguarda o MP4 atual ficar estavel, valida-o com `ffprobe`, encerra
  apenas o worker de acompanhamento, registra a saida no trabalho original e depois permite o
  reinicio do ComfyUI e do Studio. Assim o render em andamento nao e descartado pela correcao.
- Verificacao: `py_compile`, regressao de polling H3, teste do recuperador persistente e validacao
  estrutural do watchdog passaram. Em estado real de 100% de GPU e porta ausente, o watchdog
  registrou `Restart adiado` e preservou o sampler ativo.

## 2026-08-11 - Aplicativo Android recupera a permissao de microfone negada

- Sintoma: ao negar o microfone no telefone, o WebView devolvia `NotAllowedError` e a pagina
  mostrava apenas uma mensagem sem nova tentativa guiada. Depois de negativas repetidas, o
  Android podia deixar de mostrar a pergunta, prendendo o usuario na mesma mensagem.
- Causa raiz: o aplicativo tratava a permissao somente enquanto o pedido WebRTC estava aberto;
  nao diferenciava primeira solicitacao, negativa recuperavel e bloqueio permanente do Android.
- Correcao: a beta 10 registra o pedido em contexto, explica o uso local e o descarte do audio,
  permite tentar novamente e, quando necessario, abre diretamente as permissoes do pacote.
  Ao voltar das configuracoes, concede apenas `AUDIO_CAPTURE` ao host exato do Maestro. Cancelar
  mantem **Enviar audio** disponivel e encerra corretamente o pedido pendente.
- Interface web: a mensagem agora orienta tocar novamente em **Falar**; os dois botoes permanecem
  ativos depois da negativa. O asset versionado ja e servido pelo processo atual.
- Verificacao: teste de politica cobre os quatro estados de permissao; `testBetaUnitTest`,
  `lintBeta` e `assembleBeta` passaram. O teste Chrome confirmou nove caixas, cinco viewports,
  fluxo completo de Faster Whisper e regressao de negativa. APK v2: versionCode 10,
  SHA-256 `61319CAC131131DDBD724104E7622C5730E44B7FB00D74FA3AFADCD55FDA654B`.
  O teste final da permissao do sistema permanece pendente porque nenhum aparelho apareceu no ADB.

## 2026-08-12 - Gateway aceita o hostname privado exato do Tailscale

- Sintoma: o Maestro estava saudavel em `127.0.0.1:9501`, mas a rota privada `:8443` devolvia
  HTTP 421 porque o hostname MagicDNS nao fazia parte da allowlist do gateway.
- Correcao: `MAESTRO_PRIVATE_GATEWAY_HOSTS` passou a declarar hostnames privados adicionais. O
  parser aceita somente nomes DNS exatos e mantem essa lista separada dos dominios publicos.
- Reinicio: somente o frontend/proxy foi reiniciado pelo fluxo administrativo supervisionado
  pelo Radar; Studio, ComfyUI, OpenCode e Ollama permaneceram ativos.
- Verificacao: 13 testes de autenticacao passaram; o hostname Tailscale retornou HTTP 200 e um
  host arbitrario continuou bloqueado com HTTP 421. A bateria integrada fechou em 34/34.

## 2026-08-13 - Takes MiniMax H3 usam prontidao do proprio motor

- Sintoma: o projeto `mortal_kombat_irmaos_h3_8x8s` tinha oito imagens aprovadas e oito takes
  elegiveis, mas o painel mantinha a producao desabilitada porque o status global refletia apenas
  o LTX-2.3, indisponivel por seu gate especifico de RAM.
- Causa raiz: o endpoint interno publicava um unico `engine_ready` derivado do LTX, e a interface
  reutilizava esse valor para projetos MiniMax H3. A disponibilidade de motores diferentes ficou
  indevidamente acoplada.
- Correcao: o Studio agora publica `engine_readiness` separado para LTX-2.3, LTX HQ, MiniMax H3 e
  Wan de reserva. O painel mapeia `generationProfile`/motor de cada take e falha fechado para um
  motor desconhecido. O cache do `maestro.js` foi versionado; autenticação, proxy, aprovacao humana,
  integridade H3 e preflight do backend permaneceram inalterados.
- Verificacao: 3/3 regressões novas, 33/33 contratos Studio/UI/autenticacao e 19/19 testes do
  gateway passaram; `py_compile`, `node --check` e `git diff --check` passaram. O Studio foi
  reiniciado isoladamente pelo Radar. Ao vivo: `minimax_h3=true`, 8/8 takes aprovados/elegiveis e
  preflight 8/8 sem submissao. Studio e ComfyUI continuam em `127.0.0.1`; proxy encaminhado sem
  token recebeu HTTP 403. Gitleaks, Semgrep e Bandit nao estavam instalados localmente; foi feita
  revisao estatica focada sem achado novo nas linhas alteradas.
- Estado posterior: depois da validacao sem jobs, um lote externo de tamanho 8 apareceu com
  `batchId=d8243f1a1e70424f9cc69c9f41160d51`; o lote serial foi preservado, sem cancelamento nem
  duplicacao pelo diagnostico.

## 2026-08-14 - Tela aberta do Maestro atualiza a propria versao

- Sintoma: a interface deixada aberta continuava mostrando estado antigo depois da aprovacao
  humana do Take 07, embora o Studio ja registrasse `APPROVED` e
  `APPROVED_HUMAN_LISTENING`.
- Causa raiz: o backend, o proxy e o asset publicado estavam atuais, mas um WebView ja carregado
  podia manter a instancia anterior do JavaScript ate a navegacao ser recarregada.
- Correcao: o frontend ganhou manifesto de build sem cache, verificacao a cada 30 segundos e
  recarga unica quando encontra uma versao publicada diferente. O cache key do `maestro.js` foi
  atualizado e somente o frontend foi reiniciado pelo fluxo supervisionado.
- Verificacao: `node --check`, 5 testes de navegacao/atualizacao e `git diff --check` passaram.
  O asset local e o publico apresentaram o mesmo SHA-256
  `E649242B066BC246CC52B9DC40FB775DA12C4F8C59FB6B30532C8112070061D6`. O Take 07 permaneceu
  aprovado; o Take 08 permaneceu `READY`, aguardando escuta humana do audio.

## 2026-08-14 - Gerador musical LeVo 2 integrado ao Maestro

- Objetivo: transformar o Tencent SongGeneration LeVo 2 v2-large ja instalado em um gerador
  musical nativo, sem usar Python para sintese/DSP e sem deixar outro motor pesado residente na
  RTX 5090.
- Backend: `services/studio/levo_music.py` orquestra exclusivamente os pesos neurais pelo ComfyUI
  isolado em `127.0.0.1:8190`. O provider `levo2_local` entra na fila generativa existente, espera
  serialmente, recusa a reserva se a fila principal estiver ocupada ou houver menos de 20 GB de
  VRAM livre, suporta cancelamento e encerra apenas o processo que ele mesmo abriu.
- Gate humano: a primeira saida e obrigatoriamente instrumental, FLAC e limitada a 5-15 segundos.
  O resultado recebe `PENDING_HUMAN_REVIEW`, nunca e aprovado nem anexado automaticamente a um
  take e preserva o escopo de licenca `internal_noncommercial_research_only`.
- Interface: **Criar musica** e **Criar efeito sonoro** agora sao modos visiveis. O LeVo 2 aparece
  como motor padrao instalado, com ajuda acessivel, limites de duracao, progresso, player nativo e
  botoes separados para abrir e baixar o audio. O manifesto de build avancou para
  `20260814-levo2-music1` para atualizar telas ja abertas.
- Verificacao: 3/3 contratos do backend LeVo 2 e 6/6 contratos de interface/navegacao passaram;
  `py_compile`, `node --check` e `git diff --check` passaram. A regressao ampla fechou 132/134;
  os dois erros reproduzidos isoladamente pertencem a fixtures de video preexistentes
  (`Take 006` ausente e `LTX-2.3-720p` indisponivel), sem passagem pelo provider musical.
- Estado real antes da publicacao: Studio e ComfyUI com zero jobs, runtime 8190 desligado,
  RTX 5090 com aproximadamente 30,7 GB livres. Nenhuma musica foi gerada durante a validacao e
  nenhum take, audio aprovado ou estado de revisao foi alterado.

## 2026-08-14 - Conectores Mortal Kombat refeitos com progressao temporal

- Sintoma: os conectores anteriores reiniciavam golpes, recuavam personagens e, no limite entre
  os Takes 06 e 07, faziam o imperador levantar e voltar a sentar. Um candidato B04 tambem foi
  reprovado pelo proprietario por parecer danca e usar um corte seco.
- Correcao visual: sete conectores foram refeitos no projeto
  `mortal_kombat_irmaos_transicoes_progressao_v2`, com uma unica acao irreversivel por ponte,
  proibicao de rollback e destinos extraidos dos takes aprovados. O B05 foi refeito sem
  cambalhota; o B06 passou a terminar no primeiro quadro real do Take 07, com o imperador sentado.
- Audio: depois da aprovacao visual, o HunyuanVideo-Foley XXL leu os sete videos de 2 segundos na
  RTX 5090 e gerou somente ambiente/impactos. Os WAVs foram conformados em 48 kHz, 24-bit,
  estereo, com reforco grave e headroom; nenhum audio foi sintetizado por Python.
- Verificacao: cada conector editorial tem 48 quadros, 24 fps e 2,000 s. O piloto audiovisual
  concatenado tem 14,000 s, 336 quadros, media de -16,7 dB e pico de -1,6 dBFS. Os sete endpoints
  de audio candidato responderam HTTP 200. Os sete candidatos FHD terminaram e aguardam decisao
  humana; os Foleys permanecem `candidate_pending_human_listening` e nao foram anexados ao master.
- Rollback: os masters anteriores e o projeto de conectores anterior permanecem intactos ate a
  aprovacao humana dos FHDs e da nova faixa de Foley.

## 2026-08-14 - Gerador video-to-sound independente de modelo no Maestro

- Causa raiz: o Maestro ja servia e revisava candidatos de audio, mas a geracao por leitura do
  video dependia de scripts Hunyuan especificos de cada projeto, sem API, fila persistente ou
  contrato para outros modelos.
- Arquitetura: `services/studio/video_sound.py` define request/result, registro de providers,
  capacidades publicas e adaptadores. HunyuanVideo-Foley XXL virou o primeiro provider; um adaptador
  externo por argv permite adicionar runners futuros sem alterar API ou interface e nunca usa shell.
- Integracao: takes aprovados ganharam **Gerar som pelo video**, selecao de provider, direcao com
  ditado, piloto de ate 15 s, progresso e player. A API adicionou status, criacao, consulta,
  cancelamento e decisao humana do candidato.
- Gates: take visual aprovado, caminhos confinados ao projeto, fila ComfyUI vazia, 24 GB de VRAM
  livre, GPU exclusiva, nenhum fallback para CPU, nenhuma aprovacao/anexacao automatica e rejeicao
  removida do slot ativo com historico preservado.
- Audio: Python apenas orquestra pesos treinados e mede arquivos. O Hunyuan roda offline em Docker
  na RTX 5090; FFmpeg prepara o proxy NVENC e conforma tecnicamente o WAV 48 kHz estereo.
- Documentacao: `docs/VIDEO_TO_SOUND.md`, `docs/VIDEO_PROJECTS_API.md` e
  `ferramentas/audio_neural/video_sound/providers.json`.
- Testes: contratos de registro/provider, executor sem shell, confinamento de saida, job persistente,
  aprovacao/rejeicao humana e interface acessivel foram adicionados. Nenhum teste carrega o modelo.
- Implantacao: Radar reiniciou apenas Studio e frontend. A API ao vivo publicou contrato 1.0 com
  Hunyuan XXL `configured=true` em `cuda:0`; imagem Docker local confirmada, interface atualizada,
  listeners 8029/9501/8188 restritos a loopback e Host forjado bloqueado com HTTP 403. Os 17 testes
  focados passaram, incluindo prompt hostil tratado como argumento literal e autenticacao do proxy.

## 2026-08-14 - Master Mortal Kombat com progressao aprovada em FHD 60 FPS

- Aprovacao: o proprietario aprovou os sete conectores FHD e os sete Foley neurais do projeto
  `mortal_kombat_irmaos_transicoes_progressao_v2`. O Maestro registra os sete FHDs como
  `APPROVED` e os sete audios como `approved_human_listening`.
- Montagem: os oito takes FHD aprovados foram remontados com sete conectores de 2,000 s. O master
  preserva o ambiente/impactos HunyuanVideo-Foley XXL e as vozes fornecidas pelo proprietario nos
  Takes 07 e 08. Nenhuma musica ou sintese procedural por Python foi acrescentada.
- GPU: os conectores editoriais e o master intermediario foram codificados por NVENC. A versao
  final foi interpolada por RIFE 4.6 na RTX 5090, enumerada nesta execucao como dispositivo
  Vulkan 0; os quinze segmentos passaram em suas contagens individuais.
- Verificacao: entrega final com 1920x1080, 60/1 fps, 3.600 quadros e 60,000 s; H.264 Main com
  AAC-LC estereo 48 kHz. A decodificacao integral passou. O audio decodificado do master FHD24 e
  do FHD60 tem o mesmo SHA-256
  `3321fecc635bf920fa72f322232c2afa13392339cfd7ec0451a67edbb5ebc560`; loudness de -16,9 LUFS e
  pico verdadeiro de -1,0 dBFS. SHA-256 do MP4 final:
  `923475C3D095E3BFACACC216EFFCC01C74FD46F46CFBFC63931270292A24C65F`.
- Rollback: os masters anteriores permanecem intactos. A nova entrega e
  `deliveries/mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd60_rife46.mp4`.

## 2026-08-15 - Vegetto x Super Boo LTX-2.5 integrado ao QC humano do Maestro

- Projeto: `vejito_super_boo_ltx25_60s` passou a usar o contrato canonico de projetos/takes do
  Maestro sem perder os manifests cinematograficos, a continuidade Potara/SSJ ou o rollback do
  master Mortal Kombat.
- Imagens: as ancoras 00-04 foram entregues pela API de candidatos, aprovadas explicitamente pelo
  proprietario no Maestro, conferidas por elenco e promovidas com SHA-256. A ancora 07 foi criada
  com `anchor_06.png` como referencia, aberta/inspecionada, normalizada para 1536x864 e entregue ao
  T08 como candidata; permanece pendente de decisao humana.
- Video: o T01 foi gerado isoladamente no LTX-2.5 local com duas guias e `LTXVCropGuides` nas duas
  etapas. O review NVENC tem 1024x576, 24 FPS, 121 quadros, 5,041016 s, sem audio e decodificacao
  integral aprovada; SHA-256 `58E4B681EC84724BF0D45FE7DABC95351870263B13474B20C4A2AF4135C20B90`.
- QC: o T01 foi publicado no player do Maestro como `READY`/`video_pending_human_review`, com aviso
  explicito para conferir a baixa de movimento no ultimo segundo. Nenhum T02 foi iniciado. Audio
  Hunyuan permanece bloqueado ate picture lock.
- Runtime: filas Studio e ComfyUI estavam vazias antes do job; a GPU foi usada serialmente. O Radar
  recarregou apenas o Studio na porta loopback 8029 para reconhecer o perfil de exibicao
  `ltx25_two_anchor_distilled_1024x576p24` sem expor um botao que chamaria motor legado.

## 2026-08-15 - Correcao da revisao de ancoras finais no Maestro

- Causa: M06-M08 tinham candidata de quadro final entregue, mas o frontend habilitava o player e a
  miniatura somente quando tambem existia um quadro inicial. O cartao anunciava revisao pendente e
  simultaneamente ficava sem imagem e bloqueado.
- Correcao: candidatas finais registradas agora usam `anchor-image`, habilitam miniatura/player e
  continuam exigindo aprovacao humana. O build `20260815-end-anchor1` força atualizacao segura da
  sessao aberta sem reiniciar os motores.
- Verificacao: 70 testes de projetos de video e 30 contratos de interface passaram; JavaScript
  passou no parse, `git diff --check` passou e as imagens M06-M08 responderam HTTP 200 `image/png`.

## 2026-08-15 - Encadeamento de fronteiras para takes first/last-frame

- Causa raiz: uma segunda ancora pendente nao impedia um novo pedido de foto inicial; esse pedido
  mais recente ocultava a candidata entregue. Alem disso, o fim aprovado nao era propagado como
  inicio do take seguinte em projetos de continuidade explicita.
- Correcao: pedidos sao resolvidos por lado (`start`/`end`), a revisao final tem prioridade visual e
  projetos opt-in herdam a fronteira aprovada com arquivo, sidecar e SHA-256 preservados.
- Verificacao: 71 testes de projetos de video e 31 contratos de interface passaram. O build
  `20260815-anchor-chain1` foi publicado e o Studio voltou saudavel na porta loopback 8029.

## 2026-08-15 - Gate fail-closed de acao continua em toda a duracao

- Causa: proibir `crossfade` e quadros identicos nao impedia o modelo de concluir o evento nos
  primeiros frames e sustentar uma pose quase estatica no restante.
- Correcao: projetos opt-in agora precisam declarar movimento util em `0-30%`, `30-70%` e
  `70-100%`, alem de `action_occupies_full_duration=true` e zero frames de crossfade, freeze e
  hold. Conectores tambem exigem ancoras vindas de trechos com movimento antes e depois do quadro.
  `get_take_generation_spec` valida o contrato de todo take e bloqueia o job antes da GPU.
- Verificacao: 11/11 testes do gate universal, 75/75 testes de projetos de video, `py_compile`,
  parse dos JSON e preflight real do conector B04 passaram.

## 2026-08-15 - Skill oficial h3-prompt-writing e preview H3 opt-in

- Fonte: a skill `h3-prompt-writing` do repositorio oficial MiniMax-H3 foi preservada
  em `third_party/MiniMax-H3-official`, fixada no commit
  `d21241f0a4b3acbb34c97dae47fa417b7065e438` e verificada por SHA-256. O processamento
  e privado/local e nao chama API externa.
- Prompt: o Maestro agora compila T2VA, I2VA, L2VA e FL2VA com alinhamento temporal,
  `integrated_multimodal_description`, `overall_soundscape` e
  `non_diegetic_music`. O contrato Ref2VA de seis secoes tambem e validado localmente,
  mas seu runtime permanece para uma etapa posterior.
- Preview: `ModelPreviewOverrideKJ` pode ser ligado explicitamente somente no H3. O
  node fica entre o modelo e guider/scheduler; sampler, encoder, 20 passos, guidance,
  seed, resolucao, FPS e MP4 final permanecem iguais. O padrao continua desligado.
- Verificacao: `py_compile` e `node --check` passaram; 224/224 testes focados passaram.
  A API local ao vivo confirmou FL2VA de 0,00 a 5,13 s, integridade dos tres arquivos
  oficiais e `externalApi=false`. O Studio foi reiniciado seletivamente pelo Radar,
  sem reiniciar o ComfyUI.
- Piloto real: o B05_06 foi enfileirado isoladamente com a correcao de crista, contrato
  oficial FL2VA e preview opt-in. Ele continua candidato e exige aprovacao humana no
  Maestro; nenhum upscale ou master e automatico.
- SageAttention: permanece fora da producao. O teste sera isolado quando a GPU estiver
  livre e so podera avancar apos equivalencia numerica e A/B visual com a mesma seed.

## 2026-08-16 - Instaladores pesados separados do backup do sistema

- Causa: o backup portatil nao deve carregar dezenas de gigabytes de pesos, mas o PC novo precisa
  conseguir reconstruir H3, Qwen, RIFE/RealESRGAN e Foley sem copia manual fragil.
- Correcao: `tools/model_installers` ganhou BATs individuais e completo, downloader com retomada,
  retry, preflight de disco/GPU/Docker, allowlist de fontes, revisoes fixadas, tamanho e SHA-256.
  Arquivo divergente e preservado em quarentena; rerun pula o que ja foi verificado.
- Qualidade: o perfil mantem FL2VA pruned INT8 ConvRot, Qwen3-VL-32B NVFP4/AWQ, 20 passos e
  Foley XXL. Nenhuma LoRA Turbo ou reducao de qualidade entra no instalador.
- Backup: o pacote continua sem pesos e agora inclui a pasta pequena `INSTALAR_MODELOS`. A
  validacao rejeita `.env` e qualquer extensao de peso encontrada no payload.
- Verificacao: oito testes unitarios, Ruff, compilacao Python e dry-run real por BAT passaram sem
  download ou inferencia; todos os artefatos existentes foram localizados com tamanho correto.

## 2026-08-17 - Controles reais para danca multiator no MiniMax H3

- Causa raiz: o Maestro tratava fotos Ref2VA como estados temporais e o DWPose como se fosse
  controle articular. O node `MiniMaxH3ReferenceToVideo` nao possui entrada de pose; o video de
  referencia e apenas latente de referencia. O compilador tambem misturava identidades por nao
  declarar sujeitos persistentes e aplicava movimento de camera mesmo a um take de camera fixa.
- Correcao: Ref2VA agora exige `<Subject N>`, bloqueia alegacoes `exact_pose`, usa as imagens-fonte
  aprovadas em tamanho maximo e respeita contratos explicitos de camera fixa. O perfil Wan vertical
  passou a falhar antes da GPU se nao for 720x1280, eliminando o clamp silencioso para 720x720.
- Evidencia: Wan falhou com o mesmo movimento generico em 109 quadros/two-chunk e 77 quadros/chunk
  unico, produzindo zero dos dois contatos. O smoke MiniMax de 124 quadros passou live action,
  identidade e figurino, mas falhou a danca canonica e os dois contatos; foi preservado somente
  para QC com SHA-256 `C0C35CFA5B8DC27F36B218A05FA730803D873A9C967B185608674DD7CA785B52`.
- Verificacao: 213/213 testes focados passaram; o grafo ao vivo confirmou duas imagens, video de
  referencia, Subjects explicitos, `ref_image_size=max`, 24 FPS, 20 passos e camera fixa sem a
  instrucao contraditoria de translacao. Decodificacao integral do MP4 passou.
- Proxima rota: dois novos quadros live action intermediarios aprovados pelo proprietario e seis
  segmentos MiniMax FL2VA com fronteiras exatas; nenhum novo render, upscale, audio ou master e
  autorizado antes dessa aprovacao.

## 2026-08-17 - Cadeia FL2VA live action de 15 segundos

- Autorizacao: o proprietario autorizou a correcao, quatro renders MiniMax adjacentes e a montagem
  de um candidato visual de 15 segundos; audio, aprovacao e upscale permaneceram bloqueados.
- Correcao de contrato: todos os trechos coreograficos passaram a carregar o manifesto aprovado
  de traducao das ancoras. Os quatro preflights retornaram `FL2VA ready`; 88 testes focados passaram.
- Renders: LA01->LA02, LA02->LA03, LA03->LA04 e LA04->LA05 foram executados serialmente no H3
  pruned INT8 ConvRot, 720x1280, 24 fps, 124 quadros e 20 passos, sem audio.
- QC: os quatro MP4s passaram em decodificacao integral. A danca manteve dois atores e chegou aos
  dois contatos; a fusao terminou em um unico guerreiro preto; a carga preservou cabelo preto; a
  transformacao mudou para dourado antes/junto da explosao. Uma faixa branca dominante da fusao foi
  removida na montagem.
- Master: `gogeta_fusion_live_action_fl2va_chain_15s_candidate_720x1280p24.mp4`, H.264/yuv420p,
  720x1280, 24 fps, 360 quadros, 15,000 s, sem audio, SHA-256
  `703FE4DE32E8D7B60B39C2AA9D4DC4F006627778121E15048B6BAF1F6D3391D0`.
- Estado: exposto no Maestro como `MASTER15_FL2VA_CHAIN`, pendente de revisao visual humana;
  nenhum upscale ou som foi iniciado. O plano alternativo de dois takes de 8 s foi documentado.

## 2026-08-17 - Refatoracao para MiniMax nativo longo sem danca

- Decisao editorial: a danca foi retirada; o novo take parte do quadro 48 aos 2,000 s do candidato
  atual, aprovado pelo proprietario como ponto de inicio visual.
- Causa raiz: o backend H3 ja aceitava 362 quadros na grade `17k+5`. As transicoes congeladas vieram
  de contratos fixados em 124 quadros e da montagem de quatro inferencias independentes, nao de um
  limite real de cinco segundos do modelo.
- Correcao: criado `PROD15_NATIVE_NO_DANCE`, um unico FL2VA vertical de 362 quadros/24 fps/20 passos,
  com ancoras first/last exatas, sem Ref2VA, Wan, montagem, crossfade, dissolucao, audio ou upscale.
- Direcao: contato ja iniciado -> fusao legivel -> guerreiro base preto -> carga de Ki preta ->
  progressao dourada e explosao simultaneas, com uma unica trajetoria fisica de camera.
- Verificacao: o preflight real retornou `ready=true`, modo FL2VA e todos os gates verdes; 89/89
  testes focados passaram. Depois do preflight, a geracao voltou a ficar bloqueada aguardando ordem
  explicita do proprietario; nenhuma inferencia GPU foi iniciada.
- Autorizacao: em 2026-08-17T06:02:45-03:00, o proprietario ordenou `Renderizar`; o gate foi aberto
  somente para uma inferencia nativa de `PROD15_NATIVE_NO_DANCE`. Audio, montagem e upscale seguem
  nao autorizados.
- Resultado: job `3077e4aeb0f1429aba8dd3f22bc899af` concluiu sem retry ou recuperacao, produzindo
  720x1280, 24 fps e 362 quadros. A decodificacao integral passou e o SHA-256 e
  `B75D45A1AF240EA8DC1AB1EB0D2C82CF750F286C007C9FB3ACD84D68DC8A0D8B`.
- QC: a progressao e uma unica geracao sem emenda congelada, mas ha um clarão branco curto de
  aproximadamente 0,3-0,4 s durante a fusao. O candidato permanece pendente de revisao humana;
  a autorizacao de uso unico foi consumida e nova geracao, audio e upscale voltaram a ficar bloqueados.
- Audio: o proprietario autorizou um unico candidato de Foley para o take nativo. O escopo usa
  HunyuanVideo-Foley XXL por 15 s, sem musica, dialogo, auto-attach, mix, aprovacao automatica ou
  upscale; a saida permanece sujeita a escuta humana.
- Foley: job `432e3b825ab9448a857e814b3897e254` concluiu com WAV PCM 24-bit/48 kHz/15 s,
  pico -3,02 dBFS, -14,34 LUFS e zero clipping. Os dois canais sao dual mono; essa limitacao foi
  registrada sem representar o candidato como estereo espacial. SHA-256
  `E7283D426CC41BE62793A871961BDB9B52048095C5369A48179504493700DC33`.
- Operacao: o Qwen 27B comprovadamente ocioso foi temporariamente liberado para cumprir o piso de
  24 GB de VRAM do Foley e o supervisor o restaurou depois; `health=200` e modelo correto foram
  verificados. O candidato continua separado do video e pendente de escuta humana no Maestro.

## 2026-08-20 - Piloto musical FFVIII live action rejeitado e redirecionado

- Problema: o primeiro piloto LeVo 2 do projeto `ffviii_clones_liveaction_intro_faithful_v1` foi
  rejeitado pelo proprietario por soar como uma balada barata, sem intensidade para o combate.
- Causa raiz: o prompt combinava piano intimo, romantismo e crescimento suave, orientando o modelo
  para linguagem sentimental/pop em vez de ameaca ritual e guerra sinfonica.
- Correcao: o v1 foi preservado como `USER_REJECTED` e proibido de montagem; o substituto remove
  piano e balada e exige requiem de guerra, coro macico, metais hostis, timpani, ostinato rapido e
  impacto final de Gunblades.
- Gate: a nova saida continua candidata, exige escuta humana e nao autoriza composicao completa,
  video, Foley ou mix final.
- Verificacao do substituto: o job `33315c2104eb4819a3de1415c7ed2746` entregou FLAC estereo de
  15 s. O bruto ficou em -28,19 LUFS e -6,40 dBTP; o proxy de escuta ficou em -18,25 LUFS e
  -1,50 dBTP. A forma de onda possui pulsos ritmicos do inicio ao fim, mas o bloco central recua;
  somente a escuta do proprietario decide se a linguagem de balada foi eliminada.

## 2026-08-20 - Contrato eliminatorio de continuidade FFVIII live action

- Determinacao do proprietario: congelar quadro, segurar cauda, disfarcar ruptura com RIFE ou
  aceitar qualquer pausa perceptivel sao violacoes inadmissiveis.
- Correcao: o manifesto, a fila, o roteiro, o inventario de ancoras e o QC agora reprovam
  automaticamente essas ocorrencias. RIFE ficou limitado a FPS depois de a continuidade nativa
  estar aprovada.
- Reparo obrigatorio: toda fronteira quebrada exige microtake gerado com velocidade herdada,
  acao irreversivel, movimento integral e entrega visivel ao take seguinte.
- Verificacao: os contratos JSON foram mantidos parseaveis; nenhum video, interpolacao ou montagem
  foi iniciado por esta alteracao documental.

## 2026-08-20 - Cadeia propria de fronteiras moveis FFVIII baseada no precedente Vejito

- Determinacao do proprietario: o projeto deve repetir a arquitetura que funcionou no Vejito,
  mantendo takes fechados sem hold e uma cadeia separada de conectores que herda posicao, vetor
  corporal, camera e cenario.
- Precedente verificado: os projetos `vejito_super_boo_transicoes_progressao_v2` e
  `vejito_super_boo_3x10_continuo_liveaction_foley_v1` registram conectores dedicados, ancoras
  retiradas de movimento nativo, progressao 0-30/30-70/70-100, hard concat e master com zero
  crossfade, freeze ou static hold.
- Correcao: a intro agora possui duas trilhas formais: `M01-M13` para os takes principais e
  `B01_02-B12_13` para doze fronteiras moveis dedicadas. Cada B registra `position_state`,
  `body_vector`, `camera_vector`, `scenario_state` e uma unica acao irreversivel.
- Situacoes: a cadeia cobre espuma para petala, petala para pena, relampago para Gunblade, aco para
  camara de Edea, fogo para faiscas, toda a progressao fisica do duelo, sangue para petala e corrida
  ate o corte final no movimento.
- Verificacao: `tools/validate_continuity_spec.py` retornou PASS com 13 takes, 12 fronteiras, quatro
  campos de estado em todas as fronteiras e zero erros. O gate musical permaneceu pendente; nenhuma
  geracao de imagem, video, RIFE ou montagem foi iniciada.

## 2026-08-20 - Piloto musical FFVIII v2 publicado na Biblioteca Maestro

- Pedido: disponibilizar no Maestro o mesmo proxy normalizado apresentado para escuta no projeto.
- Acao: o FLAC `levo2_pilot_v2_review_normalized.flac` foi copiado para a biblioteca gerativa com o
  nome `ffviii_intro_music_pilot_v2_review_normalized.flac`, sem substituir o bruto do job LeVo 2.
- Integridade: origem e copia conferem pelo SHA-256
  `82B22D3485EF9F363AD3CAE39FF70E3848C85E9FA044147DB059611659DFD54B`.
- Verificacao real: `/api/generative/assets?kind=audio` encontrou o arquivo e publicou uma URL de
  player. O candidato continua `PENDING_HUMAN_LISTENING`; nenhuma aprovacao ou montagem ocorreu.

## 2026-08-26 - Master visivel dentro do cartao em qualquer aba

- Sintoma reproduzido no Chrome: ao clicar em `Assistir clipe completo` com a aba `Acoes` ativa, o video decodificava em segundo plano, mas o painel compartilhado de takes permanecia oculto com geometria `0x0`.
- Correcao: o cartao `Clipe completo` agora possui seu proprio player HTML5 e nao depende do painel de takes, portanto permanece visivel nas abas `Acoes`, `Para decidir`, `Todos` e `Aprovados`.
- O gate de decisao so registra a visualizacao depois de o player estar visivel, com dimensoes validas e reproducao real; clicar em um player oculto nao libera mais `Aprovar master`.
- O scroll considera a altura da barra fixa `Acoes principais`, evitando cobrir o master ao iniciar a reproducao.
- Verificacao real: Chrome 151 isolado, aba `Acoes`, HTTP `206`, `readyState=4`, 1280x720, 156 quadros decodificados, zero perdidos, sem erro de midia e sem erro relevante no console.
- Evidencia: `ferramentas/video_global_engine/projetos/athena_exclamation_santuario_liveaction_v1/qc/rife_final_foley_fhd60/independent_qc/maestro_master_inline_player_after_fix.png` e sidecar JSON homonimo.

## 2026-08-27 - Reinstrumentacao local de musica no Maestro

- Pedido: importar um audio autorizado e receber, pelo proprio Maestro, um novo candidato com piano,
  violino, cello e banda heavy metal, preservando o original e sem depender de servico externo.
- Implementacao: criada a aba `Reinstrumentar`, com upload, presets, selecao de instrumentos,
  intensidade do metal, voz opcional, progresso, cancelamento, player, downloads e revisao humana.
- Pipeline: FFmpeg normaliza uma copia; Demucs 4 separa stems em CPU; Basic Pitch 0.4.0 extrai
  notas; o arranjador Pemara escreve MIDI; FluidSynth 2.4.7 e GeneralUser GS 2.0.3 renderizam; o
  master sai em WAV PCM 24-bit/44,1 kHz, acompanhado de MP3, MIDI, relatorio e ZIP.
- Compatibilidade: `torchaudio` 2.11 exigia TorchCodec ao salvar stems do Demucs 4.0.1. Um adaptador
  local passou a gravar WAV PCM 24-bit diretamente, sem alterar o modelo nem instalar codec global.
- Seguranca editorial: o envio exige confirmacao de direitos; nenhum caminho absoluto e exposto; o
  original recebe SHA-256 e nunca e sobrescrito. Todo resultado fica `PENDING_HUMAN_REVIEW`; somente
  a aprovacao explicita daquele master o marca `OWNER_APPROVED_FINAL`, sem rerender.
- Verificacao: 27 testes focados de pipeline, jobs, autenticacao e reinicio e nove testes da UI passaram;
  JS e Python passaram em verificacao de sintaxe. O ensaio ponta a ponta e o upload pela API viva
  produziram 6,000 s, PCM 24-bit/44,1 kHz estereo, -13,6 LUFS, -0,7 dBTP, zero clipping, duracao
  correspondente e decode integral aprovado. O download do master conferiu pelo SHA-256
  `C6214AF09557081AA7C4C724F7C417B83112EB9CF621E0737E188E81FB13E238`.
- Implantacao: o supervisor Radar reiniciou somente o Studio; a rota ao vivo respondeu
  `configured=true`, `localOnly=true`, `gpuRequired=false` e todas as dependencias verdes. Os assets
  novos responderam HTTP 200 no frontend. O candidato sintetico continua sem aprovacao humana.
- Observacao fora de escopo: a suite ampla manteve uma falha preexistente no contrato textual de
  selecao H3/WAN em `test_maestro_ui_contracts.py`; nenhum codigo desse fluxo de video foi alterado.

## 2026-08-27 - Orquestrador por prompt, stems separados e Tifa rebalanceada

- Sintoma confirmado pelo proprietario: no primeiro teste de `Tifa's Theme`, a guitarra encobria a
  banda e bateria/contrabaixo nao eram perceptiveis. O arranjo pendente `f1a95e02f82b4a8f840cc333ed823c1b`
  tinha 2.589 eventos de guitarra contra 274 de baixo; o feedback foi registrado como
  `OWNER_REJECTED`, mantendo o master somente para rollback e removendo-o da biblioteca ativa.
- Causa raiz: todos os instrumentos eram renderizados juntos em um unico MIDI, sem ganho isolado por
  stem, e a guitarra criava quatro subdivisoes com power chords de tres notas. O volume final nao
  conseguia corrigir a mascara causada por essa densidade.
- Correcao: criado `Pemara Local Orchestrator v1`, inteiramente local e deterministico. O campo livre
  de direcao converte frases em papel, ganho, densidade e velocidade MIDI por instrumento. O arranjo
  agora entrega seis MIDIs, o FluidSynth renderiza seis WAVs separados e o FFmpeg aplica os ganhos
  antes do master. `contrabaixo` e `baixo` sao aliases reconhecidos.
- Biblioteca: masters concluidos pendentes ou aprovados agora aparecem automaticamente em `Arquivos`;
  rejeitados permanecem no job para rollback, mas ficam fora da lista ativa. A interface atualiza a
  biblioteca ao concluir ou revisar o job e identifica `Aguardando sua escuta`/`Master aprovado`.
- Ensaio sintetico: 6,000 s, seis stems reais e plano com guitarra a -14 dB, baixo a -0,5 dB e bateria
  a 0 dB. O stem de bateria mediu pico -5,2 dBFS e o de baixo -14,2 dBFS antes da mixagem; o master
  passou PCM 24-bit/44,1 kHz, -13,6 LUFS, -0,7 dBTP, zero clipping e decode integral.
- Substituto da Tifa: job `b4d68638e45442f9828a26879debffbf`, 156,033 s. Piano/violino ficaram
  principais (+3/+2 dB), cello forte (0 dB), baixo forte (-0,5 dB), bateria forte (0 dB) e guitarra
  de apoio (-14 dB). A guitarra caiu para 432 eventos, enquanto a bateria ficou com 986 e o baixo
  com 281. Depois do ganho do plano, as medias medidas foram bateria -24,5 dB, baixo -33,8 dB e
  guitarra -52,5 dB.
- QC do substituto: WAV PCM 24-bit/44,1 kHz estereo, 156,033 s, -13,7 LUFS, -0,6 dBTP, zero clipping,
  duracao correspondente e decode integral aprovado. SHA-256 do master:
  `DD118FE47E27CA4775B6C3242F7D5F9E4D56DFD9CC0DBD6C1D240CCF1C7D7D5E`.
- Verificacao: 160 testes focados passaram, alem do ensaio ponta a ponta; sintaxe Python/JavaScript
  passou. O Studio foi reiniciado pelo Radar, e a API viva confirmou o orquestrador, a mixagem por
  stems e apenas o novo master da Tifa na biblioteca de reinstrumentacao.
- Estado editorial: o substituto continua `PENDING_HUMAN_REVIEW`. Medidas e QC tecnico comprovam
  sinal e integridade, mas nao substituem a escuta nem aprovam a qualidade musical.

## 2026-08-27 - Produtor neural ACE-Step XL com critico musical MuQ

- Problema: o pipeline MIDI anterior podia preservar notas, mas a musica virava uma colagem de
  timbres; a guitarra ainda podia dominar e o sistema nao possuia um modelo que ouvisse o lote e
  comparasse musicalidade, prompt e coerencia antes de apresenta-lo.
- Correcao: `ACE-Step 1.5 XL Base` passou a ser o produtor padrao da aba `Reinstrumentar`. Cada job
  gera de dois a quatro covers/arranjos completos condicionados pelo audio autorizado e pelo prompt.
  O fluxo MIDI foi preservado como fallback explicito `legacy_midi`.
- Critico: `MuQ-Eval A1` mede impressao musical, `MuQ-MuLan` mede aderencia ao prompt e analises
  deterministicas comparam cromas e ritmo ao original. O ranking 45/30/25 recomenda a ordem de
  escuta, mas nunca aprova, promove ou declara originalidade.
- Mix e integridade: cada bruto FLAC permanece intacto. Um master separado recebe apenas ganho
  linear limitado, PCM 24-bit/48 kHz, MP3 320 kbps, decode integral, loudness, pico, clipping e
  duracao. O ZIP elimina aliases duplicados e inclui os relatorios auditaveis.
- Studio: o formulario ganhou prompt livre, 2-4 variacoes e fidelidade estrutural. O player alterna
  candidatos e a revisao registra `candidateIndex`; candidatos rejeitados ficam preservados e os
  demais continuam pendentes. O master elegivel aparece em `Arquivos` sem copia adicional.
- Operacao: ACE-Step e MuQ rodam em ambientes isolados e subprocessos cancelaveis. O worker usa a
  reserva cooperativa da RTX 5090, aguarda a fila do ComfyUI e nao encerra processo alheio. O cache
  MuQ trabalha offline com revisoes fixas.
- Instalacao: commits e snapshots oficiais foram fixados em `runtime_manifest.json`; o ambiente ACE
  usa `uv sync --frozen`, o critico possui lock proprio e o instalador oferece `-DryRun`/`-RunSmoke`.
  `installation_receipt.json` foi emitido como `VERIFIED` depois de imports CUDA e hashes dos pesos.
- Armazenamento: 23,01 GB de cache temporario duplicado de `uv`/Xet foram movidos, sem exclusao,
  para `D:\PemaraAI\cache_quarantine\music_ai_runtime_cache_20260827`. O runtime permaneceu
  `VERIFIED` e o espaco livre de `E:` subiu para 206,8 GB. Novos caches ficam centralizados em `D:`.
- Prova real sintetica: o ACE-Step XL gerou dois candidatos com 50 passos; ambos passaram decode,
  duracao, PCM 24-bit/48 kHz e zero clipping. O critico carregou pesos locais, pontuou os dois e o
  lote terminou `PENDING_HUMAN_REVIEW`, com bruto, dois WAVs, dois MP3s, tres relatorios e ZIP.
- Seguranca: API local/protegida, allowlists de engine/modelo/instrumentos, limites 10-600 s,
  upload limitado, campos desconhecidos rejeitados, argumentos sem shell e artefatos confinados ao
  job. Pedidos externos foram recusados antes do processamento em teste focado.
- Verificacao final: 48 testes focados do Studio e quatro contratos da UI passaram, alem de
  `py_compile`, `node --check`, JSON, `git diff --check`, prova GPU completa e gate de seguranca
  `PASS`. Uma falha textual preexistente e fora do escopo permanece em um contrato de video H3/Wan;
  nenhum arquivo desse fluxo de video foi alterado por esta correcao.
- Licenca: os pesos MuQ/MuQ-MuLan usam CC-BY-NC 4.0. O pipeline com esse critico fica restrito a
  testes, pesquisa e uso nao comercial; a interface e o relatorio deixam esse bloqueio explicito.

## 2026-08-27 - Stem Producer v2 apos falso positivo do critico neural

- Rejeicao do proprietario: o candidato ACE-Step `5b16b60a172542bcbb8c2898f7b25305`, indice 3,
  passou os indicadores automaticos, mas foi ouvido como musicalmente incoerente. Ele foi registrado
  `OWNER_REJECTED`, removido de `Arquivos` e preservado pelo SHA-256
  `EC7EF987CEC119D60F7A3E2E90400DE550EC3CC2216861B7E57536B43E7C141D`.
- Causa: o MuQ recebia tres janelas mono de dez segundos e estimava instrumentos por afinidade
  texto-audio. Nao havia stems, correcao de notas, controle por instrumento nem iteracao de mix; o
  ranking era uma triagem estatistica, nao uma decisao de producao musical.
- Novo padrao: `stem_producer_v2` separa com Demucs na GPU reservada, transcreve com Basic Pitch,
  escreve uma parte por instrumento e renderiza seis WAVs independentes com MS Basic do MuseScore.
  ACE-Step permanece opcional/experimental e `legacy_midi` preserva o arranjador anterior.
- Arranjo: piano e violino revezam a melodia; cello e baixo usam notas sustentadas; guitarra usa o
  patch overdrive e no maximo dois ataques por compasso; bateria omite o intro, usa backbeat/half-time
  e limita bumbos por compasso. Humanizacao e deterministica para permitir reproducao e rollback.
- Mix: cada stem recebe EQ, compressao, ganho e limiter proprios antes da soma. A guitarra possui
  low-pass, corte de aspereza em 3,2 kHz e soft clipping suave, evitando a parede de serra do patch
  de distorcao anterior. Uma calibracao fixa do MS Basic corrige a diferenca real de nivel entre seus
  programas; no ensaio de seis segundos, guitarra discreta passou de inaudivel para `-22,773 dB` em
  relacao a soma, enquanto piano/violino ficaram em torno de `-8 dB` e baixo/bateria entre `-6` e
  `-7 dB`, sem clipping.
- Gate: o novo critico le integralmente cada WAV, mede audibilidade, cobertura, contribuicao na soma,
  clipping, serra e pulso mecanico, e verifica densidade MIDI. Ele declara explicitamente
  `musicalCoherenceAssessed=false`; passar o gate nunca equivale a aprovacao humana.
- Fila: um teste real revelou que a mensagem `aguardando GPU` abortava quando havia uma tarefa direta
  no ComfyUI. O worker agora espera de forma cancelavel, envia heartbeat da reserva, nao descarrega
  modelos durante uma fila ativa e mantem jobs em processamento/erro fora de `Arquivos`.
- Verificacao: 36 testes de producao/API, tres contratos direcionados de coexistencia com ComfyUI,
  cinco contratos da interface e quatro testes do runtime passaram. O self-test ponta a ponta gerou
  seis stems PCM 24-bit, passou o QC tecnico e permaneceu `PENDING_HUMAN_REVIEW`.
- Prova real: o job `9e29ad586eeb4a8ea685acc74e9f2f75` esperou um render MiniMax ativo sem
  interrompe-lo e depois produziu 156,033 s com seis stems PCM 24-bit/44,1 kHz. A guitarra ficou
  `-15,441 dB` abaixo da soma, baixo `-4,824 dB`, bateria `-8,435 dB`, piano `-9,143 dB`, violino
  `-5,500 dB` e cello `-10,283 dB`; `buzzsawRisk=0,11510` na guitarra e
  `mechanicalPulseRisk=0,00955` na bateria. O master passou decode integral, zero clipping,
  `-13,3 LUFS`, `-0,6 dBTP` e SHA-256
  `E02A20EDF5EE891ACD7A62BCDBA5FD742ED9C78B8DB1CD237D13AF318C6384B0`. Ele aparece uma unica vez
  em `Arquivos`, marcado `PENDING_HUMAN_REVIEW`; nao foi aprovado nem enviado ao Google Drive.

## 2026-09-02 - Maestro H3/LTX 2.5, Anchor Intelligence e ecossistema Turbo

- Antes de qualquer alteracao foi concluido e verificado o backup
  `G:\Pemara_Backups\PRE_CHANGE_FULL_SYSTEM_20260901_204707`; pesos de LLM/modelos foram excluidos
  do payload e substituidos por catalogo de reinstalacao. Backups antigos/incompletos foram removidos.
- ComfyUI foi promovido em runtime isolado para 0.34.2 com PyTorch 2.14.0+cu130; o runtime 0.30.2
  permaneceu intacto para rollback. O serviço ativo continua somente em `127.0.0.1:8188`.
- LTX 2.5 foi instalado com model revision e custom-node commit fixos, 11 assets centrais/de referencia,
  dez workflows oficiais e um workflow API two-stage validado no ComfyUI vivo. O engine LTX 2.3,
  checkpoints e consumidores ativos foram removidos; somente IC-LoRAs 2.3 allowlisted como
  `LTX25_COMPATIBILITY_ASSET` podem ser consumidos pelo adapter 2.5.
- O registro e a interface oferecem exatamente MiniMax H3 e LTX 2.5. A escolha e obrigatoria por
  take; motor ausente/indisponivel falha fechado, sem default, fallback ou reautorizacao de Wan.
- Foi implantado `pemara-anchor-intelligence@1`: leitura visual estruturada, confronto da imagem com
  a intencao, invariantes, `DO_NOT_INVENT`, compiladores H3/LTX 2.5 e recibos ligados aos hashes de
  ancora, contrato, engine, compilador e prompt. Processamento visual externo exige consentimento.
- `Pemara Messenger Turbo` passou a rotear fontes canonicas; 22 copias exatas profile/skill viraram
  aliases `AGENTS_TURBO_ALIAS_V1`, enquanto 13 especializacoes semanticamente distintas foram mantidas.
- O Studio recebeu CORS allowlisted e bloqueio de Origins de navegador estrangeiras/nulas. Depois do
  reinicio pelo Radar, Origin estrangeiro retornou 403, Origin Maestro retornou 200 com header exato,
  Host invalido retornou 403 e a superficie local/publica inteira passou.
- Verificacao: 233 testes de projetos/controlador/gauntlet/UI, 33 de engines/LTX 2.5/Anchor
  Intelligence/auth, 19 do gateway e 8 regressões da Loja passaram. `py_compile`, `node --check`,
  JSON e whitespace gate passaram. O recibo de seguranca resultou `PASS`.
- Limite deliberado: nenhum render GPU foi disparado. H3 esta `READY`; LTX 2.5 esta
  `READY_FOR_GPU_SMOKE` e so se torna `production_ready` apos autorizacao e recibo do smoke real.


## 2026-09-07 — Creative OS: Motion Director e H3 latent HQ

- Codex permanece MCP-only para geração; Maestro usa sua fila/backend autônomos com seleção H3/LTX preservada.
- Motion Director recebeu compilação IR, batch idempotente, lineage por segmento, rerun selecionado e opt-out real de áudio. Corrigida interoperabilidade de wrappers All-In-One/Motion Director sem remover self-tests.
- H3 nativo preserva latent separado e fingerprints dos modelos antes do envio quando elegível. HQ experimental 1536×864 usa master aprovado, pesos exatos, upscale + refinamento, sem sobrescrita/replay/autoaprovação.
- Prompt ausente após restart não dispara mais resubmissão automática.
- Benchmarks GPU exclusivamente MCP; 124-frame Motion passou; HQ vs. direto: 197,39 s vs. 213,83 s incluindo base, uma seed/cache não isolado/qualidade pendente.
- Testes: 107 controle de geração; 50 Creative OS mais teste adicional do executor HQ passaram. Ver docs/CREATIVE_OS_IMPLEMENTATION_20260907.md e dados/creative_os/deployment_verification_20260907.json. Roadmap completo ainda em implantação.

2026-09-07 09:12 — Creative OS Rewriter integrado: job durável, lease GPU, cancelamento, proposta imutável, proteção de edição e revisão explícita. Benchmark MCP cache passou; fidelidade semântica requer revisão. 164 testes/8 subtests e fixture UI passaram. Build e asset v3 vivos verificados.

2026-09-07 09:23 — Timeline H3 contínua integrada e qualificada via MCP em 226 frames, sem áudio. UI de preparo/envio explícito com proteção de edição; fila e revisão existentes. 169 testes/8 subtests passaram; build e asset v4 vivos verificados. Continuidade artística permanece pendente de revisão humana.

2026-09-07 09:41 — Fun Control H3 integrado à UI/API/fila com assets e checksum; dois benchmarks MCP passaram e seguiram o controle sintético. 175 testes/8 subtests, upload fixture e factory MCP passaram. Build vivo/asset v5 verificados; aprovação artística continua humana.

2026-09-07 09:52 — All-In-One H3 T2V/I2V headless integrado, sem enviar nó visual no-op. Benchmarks MCP e decode passaram; preservados default nativo, H3/LTX e recibos de âncora. 179 testes/8 subtests e fixture UI passaram; build/asset v6 vivos verificados.

2026-09-07: Creative OS semantic_review experimental: Gemma local, seis quadros, proveniência, worker/pausa/cancelamento, UI v7. Contradição inicial de classificação preservada; sem aprovação ou reparo automático. LTX inpainting bloqueado por acesso HF 403.

2026-09-07 11:09 — Correção do vídeo básico manual: removida exigência universal de análise/compilação de âncora no frontend e nas duas entradas Studio (síncrona/fila). Recibo explicitamente fornecido continua conferindo hash da foto, motor e prompt. H3/LTX preservados. 118 testes passaram, 10 subtestes; runGen real exercitado em VM com formulário simulado para os dois motores, sem rede/GPU. Cache maestro.js 20260907-basic-video1; backup backups/maestro_basic_video_20260907.

## 2026-09-26 — foto aprovada sem análise NVIDIA
Removida análise externa de âncora do painel, rotas de geração/Creative OS, políticas/templates e skill. Endpoint antigo410 sem upload; foto aprovada rege referência visual. SageAttention, identidade, motor explícito e avaliação do vídeo preservados.18 testes direcionados passaram;2 falhas UI ampliadas comprovadamente anteriores. Frontend atualizado e Studio recarregado via Radar. Evidência em backups/remove_nim_video_gate_20260926/RESULTADO.md.


## 2026-10-04 — SageAttention + Spectrum obrigatorios em todos os H3

Ordem expressa do proprietario aplicada aos builders H3, adapters e envio final do Maestro. Configuracao audio-replay aprovada com protecao Sage de quatro grupos; FBC aposentado nas novas geracoes, IDs persistidos preservados. Bloqueio explicito para nos ausentes ou sampler/cache incompatível. Sem alteracao da midia existente ou novo render. Corrigida colisao de ID Sage/audio VAE em Ref2VA.

Verificacao: 204 testes de backend, um teste de navegador, sete grafos aceitos via MCP; Studio recarregado e status vivo productionReady=true com os tres componentes ativos. Evidencia completa e aviso Autogrow Ref2VA em `dados/validation/h3_sage_spectrum_required_20261004/RESULTADO.md`. Backup: `dados/backups/h3_sage_spectrum_20261004_083536`. Instrucao duravel: `E:/Pemara/AGENTS.md`.
