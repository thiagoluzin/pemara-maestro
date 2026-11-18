# Padrão canônico live action do Maestro: Vejito

## Prioridade atual — 2026-10-08

A referência de Vejito documenta o método artístico e as aprovações daqueles arquivos. Na produção atual, use H3 com Sage + Spectrum e o [contrato de âncoras e acabamento de vídeo](../../pemara-video-production-lead/references/dlss5-full-frame-required.md). Os passes de RIFE, Foley e upscale descritos como histórico abaixo pertencem às versões citadas. Criar Foley requer escopo explícito.

Mais âncoras não são regra universal: em combate contínuo, a rota start-only qualificada prevalece quando controles futuros causaram reação antecipada ou cauda estática. Preservar identidade pela ficha original, bloco fixo e QC temporal.

## Autoridade

O proprietário declarou em 2026-08-20 que o projeto Vejito é a referência e o padrão de produção
live action do Maestro. O resultado publicado superou 20.500 visualizações e chegou perto de
1.000 curtidas no Threads, segundo o proprietário. Os números justificam a escolha, mas o que deve
ser reproduzido é o processo verificável, nunca os personagens ou arquivos criativos do projeto.

Projeto canônico:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/vejito_super_boo_3x10_continuo_liveaction_foley_v1`

Artefatos de auditoria obrigatórios:

- `STATUS.md`: histórico de aprovações, rejeições, picture lock, Foley e master;
- `production_manifest.json`: contratos narrativos, visuais e de transição;
- `take_queue.json`: somente takes principais como itens de revisão;
- `qc/final_master_boundary_contact_12frames_v1.jpg`: consistência visual e fronteiras;
- `output/vejito_vs_super_boo_final_36s_1080p60_foley_approved_v1.mp4`: master de referência.

## Estrutura que deve ser herdada

1. Escrever a sequência inteira e a bíblia visual antes de gerar vídeo.
2. Planejar takes principais completos, normalmente de 6 a 10 segundos, cada um com pelo menos
   duas mudanças dramáticas quando passar de 6 segundos.
3. Definir âncoras compartilhadas de fronteira em movimento. A saída de um take e a entrada do
   próximo carregam o mesmo vetor de corpo, objetos, efeitos e câmera.
4. Manter microtrechos e âncoras intermediárias como implementação interna do take. O Maestro
   mostra apenas os takes principais ao proprietário.
5. Exigir movimento útil em 0-30%, 30-70% e 70-100%; nenhuma ação termina cedo para sustentar pose.
6. Revisar e aprovar cada take principal separadamente antes de considerá-lo fonte de montagem.
7. Montar apenas bitstreams visualmente aprovados. Cortes secos acontecem no handoff de ação;
   crossfade, freeze, hold e oclusão de disfarce são proibidos.
8. Aplicar interpolação ou upscale somente depois dos passes de arte, direção e movimento. Essas
   operações melhoram cadência ou resolução; nunca corrigem coreografia, identidade ou estilo.
9. Preservar o áudio aprovado; quando houver pedido específico de Foley novo, fazê-lo depois do picture lock e exigir escuta humana separada. Acabamento novo segue o AGENTS vigente.

## Travas incorporadas após o projeto Gohan SSJ2

O pós-mortem do projeto Gohan mostrou que copiar apenas a aparência do Vejito não reproduz seu
processo. Toda nova sequência ou rota reaberta deve aplicar também estas travas:

1. **Engine lock:** registrar o motor escolhido pelo proprietário e não substituí-lo sem aprovação.
2. **Matriz de identidade:** quantidade, escala, cor, materiais, anatomia obrigatória e elementos
   proibidos por personagem e por beat.
3. **Âncora por hash:** usar o caminho e SHA-256 exatos aprovados. Não regenerar uma foto aceita nem
   esperar que o vídeo crie depois uma anatomia ausente no primeiro quadro.
4. **Risco alto exige controle e QC reforçados:** transformação e pose técnica podem receber
   keyframes intermediárias aprovadas conforme a rota; combate contínuo start-only não recebe
   guias futuras por uma regra genérica. Conferir ficha, anatomia e estados em todos os beats.
5. **QC do MP4 inteiro:** pranchas ajudam a localizar falhas, mas não aprovam sozinhas. Inspecionar
   todos os beats críticos e reproduzir o arquivo completo; prompt e metadata nunca provam o vídeo.
6. **Rejeição no mesmo escopo:** preservar a tentativa, bloqueá-la da montagem e criar a correção
   automaticamente. A substituta precisa de aprovação separada; após repetição do defeito, mudar a
   estratégia de controle.
7. **Combate com massa e câmera:** um plano longo não pode ser uma trajetória reta ou um contato
   sustentado. Exigir trocas físicas distintas, deslocamento, reação e reorientação motivada da
   câmera, com movimento útil até o corte.
8. **Maestro como prova, não promessa:** mostrar apenas takes principais; na revisão integral,
   somente o filme. Confirmar o item, arquivo e hash pela API viva e pela reprodução real antes de
   declarar aprovação ou correção concluída.
9. **Downstream não altera o picture lock:** Foley, lipsync, RIFE e upscale usam o hash aprovado como
   fonte, preservam rollback e continuam candidatos até a aprovação humana do novo artefato.

O manifesto de uma rota nova ou reaberta deve materializar essas travas:

- `generation_engine_policy.owner_selected_engine` e
  `allow_substitution_without_owner_approval: false`;
- `art_direction_bible.anchor_source_policy: reuse_exact_owner_approved_images_no_regeneration`;
- em `approval_policy`: `owner_rejection_auto_creates_same_scope_replacement`,
  `preserve_rejected_artifacts`, `block_rejected_from_assembly` e
  `replacement_requires_separate_human_approval`, todos `true`;
- `identity_contract` em cada take, com elenco esperado/proibido, traços obrigatórios/proibidos e
  `identity_risk`; controles e `internal_anchors`, quando aplicáveis, seguem a rota qualificada.
  Se um gate antigo exigir guia incompatível com start-only, reportar o conflito e corrigir o
  contrato/gate antes do envio; não falsificar âncora nem bypassar validação;
- caminho, metadata e SHA-256 em todas as âncoras e fontes de montagem.

O `sequence_regression_gate.py` confere esses campos, os hashes reais das âncoras e, no estágio de
montagem, se cada bitstream coincide com `output_active` e com o hash aprovado pelo proprietário.

## Gate de direção de arte live action

Todo projeto precisa declarar uma bíblia visual única para a sequência:

- `style_mode: photorealistic_live_action`;
- materiais físicos por personagem, incluindo pele, cabelo, tecido, metal ou bioarmadura;
- anatomia e elementos proibidos por personagem;
- ambiente, dano persistente, lente, movimento de câmera, luz e paleta;
- modos proibidos: anime, cel shading, ilustração, render de jogo, CGI limpo/plástico e cosplay;
- uma folha de contato das âncoras e outra dos vídeos reais para comparação humana.

Uma aparência de animação, desenho, jogo ou plástico em qualquer personagem reprova o take inteiro.
Não se recorta o trecho defeituoso para misturá-lo com outra rota visual.

## Ordem dos passes

Um take somente pode entrar na montagem quando os cinco estados estiverem evidenciados, nesta ordem:

1. `ART_DIRECTION_PASS`: aparência live action, materiais, anatomia, identidade, luz e cenário;
2. `CINEMATIC_PASS`: história, geografia, reação, escala, câmera e motivo de corte;
3. `MOTION_PASS`: ação contínua, três intervalos ativos e handoff de movimento;
4. `TECHNICAL_PASS`: decodificação, duração, FPS, codec, freezes e integridade;
5. `HUMAN_APPROVED`: aprovação explícita do proprietário para aquele artefato revisado.

Passe técnico nunca compensa falha artística ou cinematográfica.

## Regra antirremendo

Se uma sequência completa for rejeitada por regressão de arte, direção ou continuidade, retirar a
rota da produção ativa, preservar os arquivos como rollback e voltar ao contrato/âncoras. Não criar
uma cadeia de conectores, trims, mudanças de velocidade ou RIFE para salvar fontes incompatíveis.

Uma correção pontual só é válida quando um único take falha dentro de uma rota visual ainda íntegra.
Se a falha aparece em vários takes, nas fronteiras ou na identidade visual, a rota inteira está
reprovada.

## Extensão aprovada: Vejito Blue vs. Goku Black Rose

Em 2026-08-27, o proprietário classificou o R6 do projeto
`vejito_blue_vs_goku_black_rose_3x6s_liveaction_v1` como o melhor projeto até o momento. Herdar os
seguintes aperfeiçoamentos de processo, sem reutilizar personagens, imagens, prompts ou aprovações:

1. **Estados de personagem:** declarar separadamente identidade, roupa, anatomia, cabelo, olhos e
   aura antes, durante e depois de cada fusão ou transformação.
2. **Microsegmentação seletiva:** fusão, transformação, pose técnica e fronteira frágil recebem
   microtakes internos; combate contínuo pode usar liberdade controlada depois que identidade e
   mundo estiverem travados.
3. **Combate bilateral com massa:** cada troca exige contato visível, deslocamento corporal, reação
   ambiental e recuperação. Tremor, clarão e partículas isoladas não contam como impacto.
4. **Câmera ousada com geografia fixa:** órbitas e travessias por destroços devem preservar o mesmo
   mundo, evidenciar profundidade real e entregar movimento ao próximo take.
5. **Ataque icônico por geometria:** mãos, arma, instrumento ou gesto técnico usam âncoras próprias;
   o prompt não pode ser a única fonte da pose.
6. **Foley quando autorizado.** No R6, a equipe trabalhou por blocos coerentes. Para novo Foley solicitado, medir LUFS, RMS, pico, crest factor e
   energia grave, mas exigir escuta humana para peso, sincronismo e equilíbrio.
7. **Ordem histórica do R6.** `picture lock → RIFE → Foley → aprovação audiovisual →
   upscale`. Nesse projeto, o passe FHD começou depois que imagem e som do master de menor resolução foram
   aprovados. Em novas produções, aplicar o [contrato de âncoras e acabamento de vídeo](../../pemara-video-production-lead/references/dlss5-full-frame-required.md) e revisar a candidata exata.

Evidência completa:
`projetos/vejito_blue_vs_goku_black_rose_3x6s_liveaction_v1/docs/LESSONS_LEARNED_OWNER_APPROVED_R6_20260827.md`.
