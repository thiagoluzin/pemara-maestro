# MiniMax H3: prompts oficiais e preview local

## Escopo ativo

O Maestro compila prompts MiniMax H3 localmente antes de montar o workflow do
ComfyUI. A fonte e a skill `h3-prompt-writing` do repositorio oficial MiniMax-H3,
fixada no commit `d21241f0a4b3acbb34c97dae47fa417b7065e438` em
`third_party/MiniMax-H3-official`.

Nenhuma API externa participa do pre-processamento. O compilador e deterministico,
preserva a direcao criativa original e apenas acrescenta o contrato estrutural H3:

- T2VA, I2VA, L2VA e FL2VA: alinhamento temporal aplicavel,
  `integrated_multimodal_description`, `overall_soundscape` e
  `non_diegetic_music`;
- Ref2VA: `subject_definitions`, `summary`, `retention_analysis`,
  `detailed_description`, `overall_soundscape` e `non_diegetic_music`.

O modo e inferido pelas referencias entregues ao H3. Em FL2VA, a primeira imagem
fica em `0.00` segundo e a segunda usa a duracao efetiva arredondada para duas casas,
com `ROUND_HALF_UP`. Um prompt ja compilado e validado e reutilizado sem duplicar as
secoes.

## API local

`POST /api/generative/h3/compile-prompt` compila e valida sem reservar GPU. A rota e
somente interna e retorna modo, versao do contrato, commit oficial, privacidade e
integridade SHA-256 dos tres arquivos oficiais fixados.

## Preview ao vivo

O controle **Preview ao vivo do H3** e opt-in. Quando marcado, o workflow insere
`ModelPreviewOverrideKJ` entre o modelo H3 e os consumidores de model do guider e do
scheduler. O sampler, o encoder, os 20 passos, guidance, seed, resolucao, FPS e saida
final nao sao alterados.

Parametros de preview: resolucao maxima 640, JPEG 72, um quadro de preview a 12 FPS e
supressao do preview padrao. Desmarcar o controle restaura o grafo anterior.

## Gates posteriores

Ref2VA possui compilacao de prompt pronta, mas o runtime e os pesos nao foram
ativados. Isso exige uma integracao separada e um piloto humano.

SageAttention nao pertence ao runtime de producao. Qualquer teste deve usar ambiente
isolado, GPU ociosa, comparacao numerica com SDPA e A/B visual com mesma seed. Falha
de instalacao, erro numerico ou artefato visual encerra o teste sem promover nada ao
Maestro. O H3 atual continua no full attention original.

## Verificacao e rollback

- `python -m unittest test_h3_prompt_writing test_generative_control test_video_projects test_maestro_ui_contracts`
- `python -m py_compile services/studio/h3_prompt_writing.py services/studio/video_projects.py services/studio/main.py`
- `node --check app/assets/maestro.js`

Rollback do prompt: remover a chamada ao compilador no spec/runner e o endpoint
local. Rollback do preview: remover o node 20 e o campo
`enable_minimax_h3_live_preview`; nenhum checkpoint ou parametro do H3 foi alterado.

