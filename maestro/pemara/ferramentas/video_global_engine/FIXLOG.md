# FIXLOG do video_global_engine

## 2026-08-16 - MiniMax H3 Ref2VA recebe ancoras e driver aprovados

- Corrigida uma falha de contrato em que projetos com ancoras intermediarias e motion driver podiam
  cair no `MiniMaxH3ImageToVideo`; nesse grafo apenas inicio/fim chegavam ao modelo e o prompt era
  indevidamente tratado como controle de coreografia.
- `video_projects.py` agora vincula o job ao manifesto aprovado, recalcula hashes de imagens e driver,
  rejeita selecao obsoleta e compila o contrato oficial `REF2VA` com labels `<Picture>`/`<Video>`.
- `main.py` ganhou workflow local `MiniMaxH3ReferenceToVideo`, ate nove imagens e um video driver,
  carregado a 24 fps. MiniMax continua sendo o unico motor desta rota; nenhum fallback Wan/LTX foi
  reativado.
- Regressao: suite de projetos 78/78, cinco testes focados do grafo H3 5/5 e `py_compile` aprovados.
  A mudanca foi validada sem enfileirar inferencia.

## 2026-08-16 - Contrato global MiniMax H3 substitui defaults LTX/Wan

- Templates de projeto e take agora nascem com MiniMax H3, Qwen3-VL-32B, 24 fps, 20 steps,
  guidance 1.0 e prompt oficial local.
- O workflow global proibe crossfade, freeze, hold, reset e cauda estatica, e separa aprovacao
  visual, RIFE/RealESRGAN/NVENC, Foley e aprovacao de audio.
- Projetos historicos permanecem preservados e legiveis; nenhum motor antigo recebe fallback.

## 2026-08-15 - Maestro ganhou revisao humana da segunda ancora

- O fluxo de fotos agora preserva separadamente a ancora inicial aprovada e a candidata final de
  takes first/last-frame. O player mostra o quadro final pendente e o mesmo botao de revisao pode
  aprovar ou rejeitar sem trocar silenciosamente a imagem inicial.
- Quatro candidatos 1536x864 do projeto `vejito_super_boo_minimax_h3_8x8s` foram registrados em
  M05-M08 e respondem HTTP 200 `image/png` pelo Studio.
- QC visual e hashes foram preservados no manifesto; suite `test_video_projects.py`: 70/70 PASS.

## 2026-08-15 - Vegetto x Super Boo migrou de LTX-2.5 para MiniMax H3

- O proprietario abortou o plano LTX-2.5 por alucinacao visual. Os seis MP4 de teste foram
  removidos da aprovacao ativa, preservados somente como evidencia/rollback e nenhuma aprovacao
  de video foi transportada para o novo motor.
- O projeto inteiro passou ao perfil `minimax_h3_fl2va_int8_ltx_contract_720p24`: MiniMax H3
  FL2VA, 1280x720, 24 fps, 124 quadros, first/last-frame, visual-only e GPU estritamente serial.
  Audio nativo H3 continua desautorizado e o Foley permanece bloqueado ate o picture lock.
- Corrigida a visualizacao do Maestro que escondia a ancora final dos takes H3. A regressao
  fechou em 69 testes e 11 subtestes aprovados.
- O piloto antigo T01, de 5,166667 s, foi formalmente `REJECTED`: alem de nao cumprir os 8 s
  solicitados, o raio de Boo atravessava os lutadores sem uma resposta fisica coerente.
- Foi criado um projeto limpo com oito takes principais H3 de 8 s nativos (192 quadros a 24 fps),
  totalizando 64 s brutos para uma montagem editorial de 60 s. Todo candidato de aprovacao passa
  por RIFE 4.6 e so pode ser publicado com 480 quadros a 60 fps e 8,000 s exatos.
- O primeiro M01 de 8 s tambem foi recusado automaticamente por transformar um lutador em Super
  Saiyan antes da fusao. O mapa foi corrigido: M01 termina com Goku e Vegeta separados, de cabelo
  preto, colocando os Potara; M02 ficou responsavel pela fusao em Vegetto base.
- Novo M01 gerado com seed `38081503` e publicado como `READY` para aprovacao humana no Maestro.
  O raio passa atras de Vegeta com folga, sem atravessar corpos, e produz pressao, recuo e detritos.
  O candidato tem 8,000 s, 480 quadros, 60 fps e SHA-256
  `84B4B44FC387648B4722F452116FCD941C081AE2D4552E0D21EE5789F49DA404`.

## 2026-08-15 - Correcao de diretor chegou ao H3 e Foley dos oito takes entrou no Maestro

- Rejeicoes de video agora podem preservar o motivo literal para auditoria e fornecer uma
  `renderInstruction` positiva separada ao gerador. Isso evita tanto ignorar o feedback humano
  quanto induzir artefatos ao repetir no canal positivo o objeto proibido.
- `video_projects.py` e a regressao dedicada passaram em 72/72 testes, `py_compile` e
  `git diff --check`.
- O M06 corrigido foi interpolado por RIFE 4.6 para 60 fps/480 quadros/8,000 s e aprovado pelo
  proprietario junto com os outros sete takes.
- HunyuanVideo-Foley XXL gerou oito WAVs 48 kHz/24-bit/estereo, todos entregues pelo Maestro como
  candidatos independentes. Nenhum foi anexado, mixado ou aprovado automaticamente; escuta humana
  continua obrigatoria.

## 2026-08-15 - Vegetto x Super Boo final FHD60

- O proprietario aprovou 8/8 takes MiniMax H3 e 8/8 candidatos HunyuanVideo-Foley XXL no Maestro.
- O master final foi montado em 60,000 s, 1920x1080, 60 fps e 3.600 quadros, preservando o
  encerramento completo do Kamehameha e removendo apenas repeticoes nas fronteiras compartilhadas.
- Audio final AAC-LC estereo 48 kHz: -16,21 LUFS, -1,11 dBTP e LRA 10,40 LU; sem musica, dialogo,
  narracao ou sintese procedural.
- Decodificacao integral: PASS. SHA-256
  `7B05F309B0A1BE192BEE2719347033F2F21CE614AAC30626DD644BED0E73BDAA`.
- O projeto `vejito_super_boo_minimax_h3_8x8s` agora esta registrado como
  `FINAL_MASTER_READY` / `final_output.qc_status=technical_pass`.

## 2026-08-13 - Bridge editorial Unimedia v1_1 falha fechado em integridade e tipo de midia

- Sintomas reproduzidos: um review alterado depois da emissao ainda era aceito pelo objeto em
  memoria; um projeto com `take_queue.json` removido era declarado identico; trocar o revisor no
  `approved.json` nao invalidava a repeticao; MP4 importado aparecia como candidato de
  `base_image`; e `NaN` no JSON de entrada atravessava o parser.
- Causas raiz: confianca no SHA armazenado sem reler o manifest, idempotencia baseada somente nos
  metadados do projeto, ausencia de vinculo com aprovacao/autorizacao atuais, agrupamento de todos
  os assets por take sem separar familia de midia e permissividade padrao de `json.loads`.
- Correcao: o bridge recalcula o review contra o bundle; cria `import-integrity.json` com SHA-256 de
  todo arquivo original do import; compara review, aprovacao e autorizacao nas repeticoes; permite
  somente imagens em `base_image.candidate_assets`; registra video em `video_file`; e rejeita
  constantes numericas JSON nao finitas.
- Compatibilidade: a versao passou para `maestro_unimedia_editorial_bridge_v1_1`. O novo SHA exige
  reemitir e reaprovar reviews v1; projeto v1 sem manifesto de integridade nao e tratado como
  identico.
- Regressao: cinco cenarios antes falharam de forma reproduzivel e passaram depois da correcao.
  A suite dedicada fechou em 18/18, `ruff` e `py_compile` passaram. Nenhuma GPU, geracao de audio,
  rede ou publicacao foi iniciada.

## 2026-08-17 - Take 01 Vejito sem congelamentos nas fronteiras

- Sintoma confirmado no candidato de 10 s: holds em 2,125-2,500 s, 4,750-5,000 s e
  7,292-7,583 s, alem de cauda estatica. O filtro visual nao era a causa.
- Causa raiz: cabecas e caudas quase estaticas impostas pelas ancoras FL2VA foram preservadas na
  retimagem uniforme dos quatro microtakes e ficaram concentradas exatamente nas emendas.
- Correcao: somente intervalos com movimento util foram retimados para 2,5 s; os quatro blocos
  foram concatenados sem crossfade; RIFE 4.6 NCNN Vulkan produziu a revisao de 600 quadros/60 fps;
  a codificacao final usou `h264_nvenc`.
- Verificacao: 10,000 s, 1280x720, 600 quadros, SHA-256
  `C785BBF0F099C3A656DA5A3C87D8C075D3274BB0858C6887F922A62FCBD311F9`; zero congelamentos
  intermediarios e zero caudas estaticas. O antigo candidato permaneceu no historico e o novo
  preview ativo respondeu HTTP 200 no Maestro.
- Regressao: `tools/validate_take_no_holds.py` falha no candidato antigo e passa no corrigido.

## 2026-08-17 - Take 02 pancadaria continua sem holds

- O MiniMax H3 recebeu apenas as ancoras de continuidade, Vejito normal e o figurino de Gohan em
  Super Boo; a coreografia da pancadaria permaneceu livre em um unico plano de 10 s.
- O preview nativo preservou 0,5 s quase estatico na abertura e uma cauda estatica de 0,917 s,
  causados pelo condicionamento first/last-frame, embora o movimento central estivesse aprovado
  no QC visual tecnico.
- Correcao: o intervalo util foi retimado, interpolado com RIFE 4.6 NCNN Vulkan e refinado sem
  crossfade; a codificacao final usou `h264_nvenc`.
- Verificacao: 10,000 s, 1280x720, 600 quadros, 60 fps e SHA-256
  `5E1AFFA719F711E569F0C2236BFF5F651291034BB8331B884AB8679010E69AFE`; zero eventos e zero
  violacoes no gate de congelamento. O preview ativo respondeu HTTP 200 no Maestro e permanece
  pendente de aprovacao do proprietario.

## 2026-08-17 - Take 02 reprovado por anatomia e falta de impacto

- A aprovacao do Take 02 foi acidental e imediatamente substituida pela decisao humana final de
  reprovacao: Super Boo assumiu forma semelhante a um polvo e os golpes pareceram fofos, sem peso.
- O Take 3, iniciado durante a janela da aprovacao acidental, foi cancelado pelo endpoint do
  Maestro; o job `9aae48d9433d464ebf3ececb1548006d` terminou como `canceled`.
- O candidato tecnicamente sem holds permanece somente no historico e foi bloqueado para montagem,
  upscale, Foley e master. O gate tecnico nao substitui o QC humano de anatomia e impacto.
- A reposicao `49d9e9b10df44c988ef7c990b30fc268` exige Boo humanoide, regeneracao compacta e golpes com
  aceleracao, contato seco, recuo corporal, resposta de roupa, poeira, rocha e camera.
- O replacement concluiu com Boo humanoide e contatos fisicos mais fortes. O H3 nativo ainda
  produziu 0,417 s estatico na abertura e cauda condicionada a partir de 8,125 s.
- Somente os 185 quadros nativos uteis foram enviados diretamente ao RIFE 4.6 para formar 600
  quadros distintos; NVENC gerou 10,000 s/60 fps sem crossfade e com zero eventos de freeze.
- SHA-256 final: `FB91728EF2F97F2B43A7A18F32E5302C34922CAF91B2896BBE6F7D2E30EDD95C`.
  O novo preview ativo esta `READY` no Maestro e o Take 3 permanece bloqueado ate aprovacao humana.
- O proprietario aprovou explicitamente o replacement do Take 02. O Maestro registrou `APPROVED`
  e o Take 03 foi autorizado com o job `58667db6a3f343debc24536f32e57d33`.

## 2026-08-17 - Take 03 SSJ e Final Kamehameha sem holds

- O MiniMax H3 entregou os tres eventos do climax: transformacao visivel em Super Saiyan, combo
  com impacto e Final Kamehameha realmente disparada, com Boo humanoide e roupa de Gohan.
- O preview nativo reteve a ancora na abertura e congelou o feixe a partir de 8,708 s. Somente o
  intervalo util de 189 quadros foi interpolado diretamente para 600 quadros pelo RIFE 4.6.
- A primeira enumeracao Vulkan apontou a GPU integrada AMD como dispositivo 0 e falhou sem alterar
  o MP4 nativo. A repeticao explicita no dispositivo 1 usou a RTX 5090 e concluiu normalmente.
- NVENC gerou 10,000 s, 1280x720, 60 fps e zero eventos de freeze. SHA-256:
  `CDEF1269E4504270937A296297879C55C6694A36607ACF570601890F1D176248`.
- O preview ativo esta `READY` no Maestro e permanece pendente de aprovacao humana antes de
  upscale, montagem ou Foley.

## 2026-08-18 - Take 04 curto conclui o payoff da Final Kamehameha

- O proprietario aprovou o Take 03 e solicitou um Take 04 mais curto para finalizar. O projeto
  passou de 30,000 s/3 takes para 36,000 s/4 takes; o novo take entrega 6,000 s.
- A fronteira inicial foi extraida do Take 03 FHD aprovado em 9,75 s. A fronteira final foi criada
  por edicao de imagem preservando Vejito e o eixo do crater, mas mostrando o impacto expandido,
  dano irreversivel e ausencia de um corpo intacto de Boo.
- O preflight H3 rejeitou 147 quadros porque o perfil exige `17k+5`; o contrato foi corrigido para
  141 quadros nativos/5,875 s, sem reduzir os 20 steps ou a qualidade.
- O preview nativo entregou continuidade do feixe, explosao e reacao, mas reteve a ancora apos
  5,083 s. Somente 119 quadros uteis foram interpolados diretamente para 360 quadros pelo RIFE 4.6.
- A ordem Vulkan mudou apos o ComfyUI: uma tentativa do RIFE apontou a AMD integrada e falhou sem
  alterar os MP4s; a repeticao na RTX 5090 concluiu normalmente.
- NVENC gerou 6,000 s, 1280x720, 60 fps e zero eventos de freeze. SHA-256:
  `13AE22A18495D50F6D60C17BB68B90E5C7F8CBEC766AE64E6B5B5C84B669CD43`.
- O Take 04 esta `READY` no Maestro e aguarda aprovacao humana antes de upscale, montagem e Foley.

## 2026-09-02 - Rota de video consolidada em H3 + LTX 2.5

- O registry ativo passou a conter somente `minimax_h3` e `ltx_2_5`, com escolha obrigatoria,
  persistida por take e sem default ou fallback.
- O LTX 2.5 usa node/model revision fixos e o workflow API two-stage oficial validado; o prompt
  enhancer foi desativado para preservar o contrato compilado da ancora.
- Engine, checkpoints, workflows e codigo executavel exclusivos do LTX 2.3 foram retirados da rota
  ativa. Permanecem apenas IC-LoRAs exatos classificados como compatibilidade LTX 2.5.
- O contrato `pemara-anchor-intelligence@1` transforma a imagem aprovada e a intencao do diretor em
  constraints verificaveis, prompt especifico por motor e recibo hash-bound antes do job.
- 233 regressões amplas e 33 testes focados passaram; o Maestro reiniciado confirmou H3 `READY`.
- Com autorização explícita do proprietário em 2026-09-02, o smoke real mínimo do LTX 2.5 executou
  sozinho na fila: 25 quadros a 24 fps, H.264 1920x1088, 1,041667 s, sem áudio e sem fallback.
  O artefato passou no `ffprobe`, teve SHA-256
  `a2fc40d9cb434898a9daa142b5c477003b83b7d64436c53dce3957d03179ddd8` e o recibo imutável foi
  salvo em `ferramentas/video_global_engine/receipts/ltx25_gpu_smoke.json`.
- A API viva promoveu o motor para `READY`/`production_ready=true`; a fila e a reserva cooperativa
  da GPU terminaram vazias. O clipe técnico continua `PENDING_HUMAN_REVIEW` e não é master criativo.

## 2026-09-02 - Scorpion versus Johnny R2 rejeitada e R3 redesenhada

- O proprietário rejeitou integralmente a rota R2 por falsa aparência live action e estética de
  cópia barata de videogame, abaixo dos padrões Vejito, Gohan, Vejito Blue e Noob/Sub-Zero.
- A geração foi pausada por flag, a fila ComfyUI ficou vazia e T01–T03 passaram a `REJECTED` no
  Maestro sem player ativo. Os três artefatos e hashes permanecem preservados como rollback.
- A auditoria localizou a causa raiz nas âncoras: composição de splash art, cenário simétrico,
  pele/roupa plastificadas, nitidez uniforme e anéis neon sem causalidade física.
- A proposta R3 troca a rota para dez takes H3 nativos de 8 s, sem retime para preencher duração,
  e exige primeiro três provas ImageGen sem poderes para validar pele, tecido, lente e mundo real.
- Nenhuma nova imagem ou vídeo foi liberado; o plano está em
  `projetos/scorpion_johnny_cage_living_forest_h3_80s_liveaction_v1/docs/ROUTE_R3_LIVE_ACTION_REBUILD_PLAN.md`
  e aguarda revisão do proprietário.

## 2026-09-03 - Shadow Kick clássico, montagem e Foley Hunyuan

- A âncora R4 do fatality foi aprovada explicitamente pelo proprietário e registrada somente para
  o T09. A aprovação da imagem não foi convertida em aprovação automática do vídeo.
- O primeiro vídeo do T09 foi rejeitado internamente por uma retenção de 0,375 s no final. A
  segunda geração forneceu o Shadow Kick clássico correto, mas somente os quadros 0-110 eram úteis;
  a consequência foi continuada por um microtake H3 separado e ativo, sem recompor o corpo.
- O T09 montado usa 111 quadros do impacto e 123 quadros da consequência, removendo a duplicata da
  fronteira. Entregou 234 quadros, 9,750 s, 1088x608/24 fps, decodificação integral e zero eventos
  de congelamento acima de 0,20 s. Continua `PENDING_OWNER_REVIEW`.
- O master visual de 80 s aprovado foi preservado e recebeu o T09 sem duplicar o quadro de emenda:
  2.153 quadros e 89,708333 s. Os quatro holds curtos já existentes permanecem somente no trecho
  anterior aprovado; o T09 não introduziu nova regressão de congelamento.
- O Foley foi gerado pelo Tencent HunyuanVideo-Foley XXL em oito blocos visuais seriais. A mixagem
  usou somente ganho e fades de 15 ms nas fronteiras, sem camadas procedurais, música ou voz.
- O master audiovisual tem SHA-256
  `4D0BB2F4A2ACA4CCA50E0BB000DDDCAA0180509A579C49D041D4746A68F7732F`, áudio AAC 48 kHz estéreo,
  -14,3 LUFS integrado, true peak -1,7 dBFS e decodificação integral. Um proxy `faststart` de 25 MB
  com suporte a Range foi registrado no Maestro para revisão remota; ambos aguardam decisão humana.
