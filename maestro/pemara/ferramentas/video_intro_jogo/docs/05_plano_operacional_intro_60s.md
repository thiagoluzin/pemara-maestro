# Plano Operacional - Intro 60s

Projeto prioritario do gerador de videos do Maestro.

## Objetivo

Gerar uma abertura animada de 60 segundos para Ritmos da Revolta, em 16:9, 1280x720, 30 fps,
com visual de jogo PS1/SNES elevado: pixel art HD, parallax 2.5D, camera lenta, clima urbano
musical sombrio e acabamento cinematografico.

## Regra principal

O video final deve ser ambiental. Nao mostrar herois, chefes, monstros, humanos, corpos, rostos,
olhos ou silhuetas. A historia deve ser contada por rua, estudio, instrumentos, cabos, piano,
velas, chapeu, fissuras roxas, luz, static e reflexos.

## Regra global de producao

A intro tambem segue a regra oficial do Video Global Engine:

- nunca gerar a intro final em prompt unico longo;
- gerar por takes curtos;
- aprovar imagem-base antes de animar;
- toda imagem-base precisa ter `.json` lateral antes de virar take;
- todo take MP4 precisa gerar `.json` lateral com origem, prompt, modelo, LoRA, parametros e QC;
- animar com Wan2.2 5B para preview/treino;
- usar Wan2.2 A14B somente em takes finais aprovados;
- fazer QC por frames/contact sheet;
- montar o final por FFmpeg/Maestro.

Regra inquebravel: sem JSON lateral = ativo invalido. Isso inclui as imagens que ja viraram takes
em testes anteriores. Se a imagem nao tiver JSON, o executor deve bloquear antes de acionar o Studio.

## Versao 60s

| Cena | Tempo | Duracao | Modelo preferido | Referencia base | Saida |
| --- | --- | ---: | --- | --- | --- |
| 01_pulso | 00:00-00:05 | 5s | LTXV ou Wan2.2 T2V | abertura/1.png | pulso dourado no escuro |
| 02_cidade_ritmo | 00:05-00:13 | 8s | Wan2.2 I2V | abertura/1.png | rua musical viva |
| 03_estudio_maestro | 00:13-00:21 | 8s | Wan2.2 I2V | abertura/2.png | piano, velas, cadeiras vazias |
| 04_chapeu | 00:21-00:28 | 7s | Wan2.2 I2V | abertura/3.png | chapeu drenando cor |
| 05_tenebra | 00:28-00:36 | 8s | Wan2.2 I2V | abertura/4.png | energia roxa e coroa abstrata |
| 06_onda_silencio | 00:36-00:44 | 8s | Wan2.2 I2V | abertura/5.png | onda roxa apagando a rua |
| 07_cidade_calada | 00:44-00:51 | 7s | Wan2.2 I2V | abertura/6.png | instrumentos quebrados |
| 08_resposta | 00:51-00:57 | 6s | Wan2.2 T2V/I2V | transicoes + sprites como paleta | seis reflexos abstratos |
| 09_titulo | 00:57-01:00 | 3s | Qwen/Composicao final | abertura/7.png | RITMOS DA REVOLTA |

## Estrategia tecnica

1. Gerar clipes curtos por cena.
2. Usar imagem base quando houver referencia clara.
3. Usar Wan2.2 I2V para cenas ambientais com imagem base.
4. Usar LTXV para iteracoes rapidas e teste de movimento.
5. Montar clipes em MP4 720p/30fps.
6. Aplicar audio depois, sem forcar audio no modelo de video.

## Modelos instalados para esse projeto

- Wan2.2 T2V HighNoise/LowNoise GGUF.
- Wan2.2 I2V HighNoise/LowNoise GGUF.
- LTXV 13B 0.9.8 Distilled GGUF.
- LTXV VAE.

## Observacao importante

Wan2.2 A14B trabalha melhor com fluxo HighNoise + LowNoise em dois estagios. O Studio ja enxerga
os modelos GGUF, mas o workflow dedicado para usar os pares High/Low juntos ainda e a proxima
etapa antes de gerar a versao final de maior qualidade.

## Escada de qualidade e uso de memoria

Regra atual:

- manter o treino LoRA no Wan2.2 5B, porque cabe melhor na RTX 5080 16GB e permite iterar;
- nao tentar treinar A14B localmente agora, porque a VRAM vira gargalo e o ganho nao compensa;
- usar os checkpoints LoRA do 5B como direcao visual e de estilo;
- para previews rapidos, gerar cenas curtas com Wan2.2 5B + LoRA fraco;
- para renders finais aprovados, testar Wan2.2 A14B GGUF HighNoise + LowNoise;
- permitir offload para RAM nos renders A14B: a RAM de 64GB ajuda a carregar/rodar modelo maior,
  mas deixa a geracao mais lenta; isso e aceitavel para render final, nao para iteracao rapida;
- usar interpolacao 60fps depois da geracao quando o movimento visual parecer travado.
- plano futuro com RTX 5090: seguir `E:/Pemara/maestro/pemara/PLANO_RTX5090_QUALIDADE_MAXIMA.md`.
- com RTX 5090, o alvo de qualidade maxima para final passa a ser Wan2.2 A14B I2V `Q8_0`
  HighNoise + LowNoise, usando RAM por offload/mmap se necessario.

## Perfil ativo RTX 5090 - 14/07/2026

Ambiente validado com RTX 5090 de 32GB:

- Driver/KMD: `610.74`.
- CUDA UMD: `13.3`.
- ComfyUI: `0.19.3`, PyTorch `2.12.0.dev20260408+cu128`, device `cuda:0 NVIDIA GeForce RTX 5090 : cudaMallocAsync`.
- Treino ativo: `config_intro_60s_5090.yaml`.
- Base: `Wan2.2-TI2V-5B-Diffusers`.
- LoRA: rank `160`, alpha `160`.
- Dataset: `13` frames por amostra, `resolution: [640]`.
- Treino: `bf16`, `adamw8bit`, `gradient_accumulation: 1`, `lr: 6e-6`, `low_vram: false`.
- Modelo: `qfloat8` para transformer e text encoder, `low_vram: false`.
- Log: `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/lora_videos/wan_lora_trainer/logs/training.err.err`.
- Saida: `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/lora_videos/wan_lora_trainer/ai-toolkit/output_intro_60s_5090`.

Primeira validacao:

- iniciou sem OOM;
- passou de 200 steps;
- uso observado: aproximadamente `17.5GB` de VRAM, `55-70%` de GPU, `258-314W`, `52-54C`;
- velocidade observada: perto de `1.1s/it`.

Regra operacional: enquanto este perfil estiver estavel, ele substitui o perfil antigo de 16GB para
treino serio da intro. Se ocorrer OOM, recuar para `num_frames: 9`, `resolution: [576]`, rank `128`.

Modelos locais candidatos para render final pesado:

- `Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf`;
- `Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf`;
- `wan2.2_t2v_high_noise_14B_Q5_K_M.gguf`;
- `wan2.2_t2v_low_noise_14B_Q5_K_M.gguf`;
- `LTXV-13B-0.9.8-distilled-Q5_K_M.gguf`.

Prioridade tecnica:

1. Continuar treinando o LoRA 5B ate estabilizar identidade, paleta, objetos e composicao.
2. Gerar previews multicena a cada marco de checkpoint.
3. Quando uma cena estiver boa no 5B, renderizar a mesma cena no A14B GGUF com offload para RAM.
4. Montar final em clipes curtos, 720p, 30fps/60fps interpolado, nunca em prompt unico longo.

## Regra apos teste 20s de 30/06/2026

O teste de 20s em prompt unico com Wan 5B + LoRA `intro_ritmos_60s_v1_000024000`
ficou praticamente estatico. Nao usar prompt unico longo como criterio de qualidade.

Fluxo correto ate segunda ordem:

- gerar a intro em cenas curtas de 5s a 8s;
- cada cena deve ter movimento explicito obrigatorio: camera, parallax, particulas,
  luz, objeto se movendo ou transformacao visivel;
- usar LoRA fraco no primeiro passe (`0.10` a `0.18`) para evitar congelar a composicao;
- costurar os clipes aprovados em MP4 final;
- somente depois testar a versao A14B HighNoise + LowNoise.

## Teste manual 12s de 09/07/2026

Treino interrompido por ordem do usuario e flags de treino continuo removidas para impedir religamento
automatico pelo watchdog durante o teste.

- Checkpoint testado: `intro_ritmos_60s_v1_000076500.safetensors`.
- Modelo: `wan2.2_ti2v_5B_fp16.safetensors`.
- Takes: `02_cidade_ritmo` e `04_chapeu`.
- Parametros: 6s por take, 30fps, 30 steps, guidance 7, LoRA strength 0.10.
- Saida: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_preview_20260709_071533.mp4`.
- QC tecnico: 12.07s, 1280x720, 30fps, 362 frames, sem audio.
- Contact sheet: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_preview_20260709_071533_contact.jpg`.

Leitura visual rapida: o take da rua mostrou melhor vida visual e deslocamento; o take do chapeu
ainda ficou mais contido do que o ideal. Proximo ajuste deve aumentar evento/camera no chapeu sem
subir demais a forca do LoRA.

## Analise de fidelidade VEO x preview local de 09/07/2026

Foi criado um pacote de JSONs para o pipeline local usar o VEO 3.1 como contrato de fidelidade:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/qc/fidelity_analysis_20260709`

Arquivos principais:

- `07_golden_take_contracts_from_veo.json`: contratos por take extraidos do golden.
- `13_preview_hallucination_report.json`: defeitos do preview local.
- `14_comparison_preview_vs_golden.json`: comparativo numerico de movimento.
- `15_training_fidelity_dataset_index.json`: indice para treino/geracao consultar antes de renderizar.

Conclusoes:

- o preview local teve movimento medio bem menor que o VEO;
- o take `02_cidade_ritmo` gerou uma mancha/obstrucao preta sem funcao narrativa entre ~3s e ~4.5s;
- o take `04_chapeu` ficou contido demais, com movimento principalmente de brilho/escala;
- o proximo prompt do take 02 deve proibir `undefined black blob`, `opaque black foreground smear`
  e exigir foreground legivel;
- o proximo prompt do take 04 deve ter milestones temporais obrigatorios:
  segundo 0 camera baixa, segundo 2 anel/rachaduras, segundo 4 chapeu levita/rotaciona,
  segundo 5 particulas vindo para a lente, final com estado visual alterado.

Regra operacional: antes de gerar novo take da intro, consultar o JSON de contratos do golden e
o JSON de defeitos do preview. Take sem evento claro ate metade da duracao deve ser rejeitado.

## Pacote oficial no motor global

A intro agora tambem existe como projeto oficial do `video_global_engine`, usando a metodologia
universal por takes:

- Manifesto: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/project_manifest.json`
- Fila de takes: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/take_queue.json`
- Execucao: `E:/Pemara/maestro/pemara/ferramentas/video_intro_jogo/docs/07_execucao_intro_por_takes.md`

Esses arquivos sao a fonte operacional para novos previews. O `intro_60s_jobs.json` antigo
continua como referencia historica, mas a producao nova deve seguir a fila do motor global.

Teste multi-cena gerado:

`outputs/clips/intro_preview_20s_multiscene_step24000_lora012_20260630.mp4`

## Regra RTX 5090 + Wan2.2 A14B Q8 - 14/07/2026

O ambiente com RTX 5090 validou o uso local do Wan2.2 A14B Q8 como melhor caminho atual
para previews fortes, mas nao como render cego em steps altos.

Modelos validados:

- `Wan2.2-I2V-A14B-HighNoise-Q8_0.gguf`;
- `Wan2.2-I2V-A14B-LowNoise-Q8_0.gguf`.

Correcao aplicada no Studio:

- videos agora usam alinhamento de dimensoes em multiplo de 16;
- `1280x720` nao deve mais virar `1280x704`;
- arquivos finais passam a registrar a resolucao real no nome.

Melhor preset atual:

- Wan2.2 A14B I2V Q8;
- 1280x720;
- 30 fps;
- 5s por take;
- 20 steps;
- sem LoRA no render de comparacao pesada, salvo teste deliberado;
- depois aplicar upscale/interpolacao para 1920x1080/60fps somente em takes aprovados.

Teste rejeitado:

- take 02 em `1280x720`, Q8, 24 steps;
- ficou mais de 40 minutos sem gerar arquivo final;
- GPU ficou em 96-100%, pico aproximado de 23039 MiB VRAM, 78 C e 583 W;
- conclusao: 24 steps Q8 nao vira preset padrao agora. So repetir se houver motivo tecnico
  especifico e janela de GPU autorizada.

Arquivos de referencia:

- preview nativo 720p bom: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_preview_a14b_q8_5090_4takes_5s_native720_cfr_20260714_123318.mp4`;
- versao FHD60 interpolada: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_preview_a14b_q8_native720_to_fhd60_interp_20260714_151315.mp4`;
- QC visual: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/qc/a14b_q8_native720_to_fhd60_interp_20260714_151315/intro_preview_contact_1fps_full.jpg`.

## QC take by take - 14/07/2026

Workprint analisado:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_workprint_all_takes_mixed_fhd60_20260714_175419.mp4`

Relatorio completo:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/qc/take_by_take_20260714_175419/TAKE_BY_TAKE_QC.md`

Veredito:

- `02`, `03`, `04` e `05` sao a base atual de qualidade, com destaque para `02` e `05`;
- `01`, `08` e `09` sao placeholders ou composicoes travadas, nao takes animados completos;
- `06` e `07` tem movimento tecnico, mas sao fracos como direcao de cena e devem ser refeitos;
- fade, brilho, fumaca e zoom simples nao contam como movimento suficiente.

Regra de aprovacao:

1. cada take precisa ter evento visivel de inicio, meio e fim;
2. precisa ter camera real ou parallax claro;
3. precisa mover pelo menos dois elementos da cena;
4. nao pode depender apenas de fade, brilho, fumaca ou zoom;
5. nao pode inserir humano, silhueta, rosto, olho, corpo ou texto falso;
6. precisa ter JSON de descricao e QC antes de entrar no workprint oficial.
