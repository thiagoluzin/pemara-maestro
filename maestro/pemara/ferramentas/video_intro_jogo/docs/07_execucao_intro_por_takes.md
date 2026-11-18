# Execucao da Intro por Takes

Este documento conecta a intro de `Ritmos da Revolta` ao motor global de video.

## Pacote oficial

- Manifesto: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/project_manifest.json`
- Fila de takes: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/take_queue.json`

## Ordem de producao

1. Takes 01 a 04: primeiro bloco narrativo, do pulso ate o chapeu.
2. Takes 05 a 07: Tenebra, onda do silencio e cidade calada.
3. Take 08: resposta abstrata por reflexos, sem personagens.
4. Take 09: titulo unico `RITMOS DA REVOLTA`.

## Regra obrigatoria antes dos takes

Nova ordem oficial:

1. Gerar imagens-base novas em anime atual para cada take.
2. Criar um `.json` ao lado de cada imagem com prompt, modelo, objetivo, objetos obrigatorios e checklist.
3. Validar imagem por imagem.
4. Marcar no JSON/fila apenas as aprovadas como `approved_for_video`.
5. So depois gerar os takes I2V.

Proibido montar preview com imagem antiga, pixelada, referencia bruta ou imagem sem JSON de validacao.

Regra inquebravel: sem JSON lateral = ativo invalido. A trava tecnica fica no
`run_intro_take_queue.py`: antes de chamar o Studio/Comfy, ele exige o `.json` lateral da imagem,
confere `image_file`, `prompt` e `validation_status`. Depois de gerar o MP4 do take, grava outro
`.json` lateral do take com imagem-base, prompt de animacao, modelo, LoRA e parametros.

## Configuracao de primeiro passe

- Imagem-base: FLUX.1 Krea dev FP8 em anime cinematografico atual.
- Modelo de video: Wan2.2 TI2V/I2V 5B.
- LoRA: `intro_ritmos_60s_v1_000056250.safetensors`.
- Forca LoRA: `0.12`.
- Resolucao: 1280x720.
- FPS: 30.
- Duracao: respeitar a duracao de cada take.

## Regra de movimento

Todo take precisa ter movimento visivel em pelo menos tres camadas:

- camera;
- luz;
- particulas;
- objeto;
- parallax de fundo/primeiro plano.

Se o take parecer foto animada, ele esta reprovado.

## Regra v3 - movimento cinematografico

Depois do preview `intro_anime_takes_preview_20260704_140045.mp4`, a qualidade visual das imagens
foi considerada muito melhor, mas o video foi reprovado por estar estatico demais.

Nova exigencia para cada take:

- ter começo, meio e fim visual;
- ter um evento claro: objeto muda, luz atravessa, onda passa, particulas convergem, algo acende/apaga;
- usar camera visivel, nao apenas zoom leve;
- usar parallax de primeiro plano e fundo;
- evitar take contemplativo sem acao;
- baixar a forca do LoRA para cerca de `0.06` quando o movimento congelar.

Movimentos aceitos:

- dolly-in/dolly-out;
- truck lateral;
- crane up/down;
- tilt/pan com parallax;
- orbit de 20 a 45 graus;
- rack focus;
- foreground crossing frame;
- transformacao visivel de luz, objeto ou particulas.

## Regra v4 - escalada obrigatoria quando o 5B fica fraco

Se um take aprovado por imagem-base sair como foto viva, movimento pobre, zoom leve, cortina/filtro
sem acao fisica ou ambiente parado, nao continuar treinando/gerando em massa no mesmo caminho.

Ordem obrigatoria:

1. Rodar comparacao curta do mesmo take com `run_motion_escalation.py`.
2. Comparar pelo menos:
   - Wan 5B sem LoRA;
   - Wan 5B com LoRA de estilo em forca minima;
   - Wan A14B Q4 I2V High/Low sem LoRA.
3. Usar LoRA de estilo apenas se ela nao congelar camera e objetos.
4. Se o A14B Q4 mover melhor, ele vira caminho padrao do take dificil.
5. So testar Motion LoRA pronta de camera depois do A14B sem LoRA, nunca como primeira saida.
6. Todo teste precisa gerar MP4, JSON lateral, ffprobe e contact sheet.

Comando base:

```powershell
cd E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo
$env:MAESTRO_STUDIO_URL="http://127.0.0.1:8029"
python .\run_motion_escalation.py --take 06 --seconds 4
```

Critério de avanço: escolher o modelo que entrega camera/parallax/evento fisico real, mesmo que a
imagem fique um pouco menos estavel. Estabilidade sem movimento esta reprovada.

## Regra v5 - A14B sem bravata, primeiro smoke test

Teste de 2026-07-11 no take `06_onda_silencio`:

- Wan 5B sem LoRA gerou MP4 valido, mas continuou visualmente fraco e com artefato/cortina.
- Wan A14B Q4 I2V em 1280x720, 4s, 22 steps entrou no workflow High/Low, mas ficou lento demais
  para a iteracao pratica e foi interrompido antes de entregar saida.
- Portanto, nao usar A14B 720p direto como primeiro teste de take dificil.

Nova ordem para take fraco:

1. Usar `motion-profile controlled` como padrao para preservar imagem-base.
2. Fazer A14B Q4 primeiro em `512x288`, 2s, 16 steps.
3. Se mover e nao alucinar, subir para `768x432`, 3s, 18 steps.
4. Se o segundo degrau for aprovado visualmente, renderizar 720p do take.
5. Motion LoRA pronta so entra depois do A14B sem LoRA, e precisa do trigger correto no prompt.
6. Prompt agressivo de cinco camadas so pode ser usado como experimento, pois aumentou risco de
   triangulos, blocos, camera rig, atores e objetos sem relacao entrando na cena.

Comando atualizado:

```powershell
cd E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo
$env:MAESTRO_STUDIO_URL="http://127.0.0.1:8029"
python .\run_motion_escalation.py --take 06 --variants wan5b_no_lora wan_a14b_q4_smoke_512 wan_a14b_q4_smoke_768
```

## Regra v6 - congelamento do fluxo local Wan 5B

Decisao de 2026-07-11 apos a rodada `four_takes_6s_20260711_0157`:

- o fluxo local Wan 5B I2V continua pobre para producao;
- alguns takes ficam praticamente como foto viva;
- quando ha movimento, ainda aparecem artefatos e alucinacoes;
- o custo em tempo/GPU nao esta justificando a evolucao;
- nao continuar treinando ou gerando em massa nesse mesmo caminho.

Estado operacional:

- a flag `E:\Pemara\maestro\pemara\dados\flags\video_generation_paused.flag` pausa a geracao de video no Studio;
- `run_intro_take_queue.py` tambem respeita essa flag e bloqueia video local;
- so usar `--ignore-video-pause` em teste deliberado e documentado.

Nova regra de avanço:

1. Wan 5B local fica reprovado como motor de producao para intro/cutscene profissional.
2. Treino LoRA de video fica pausado ate existir novo workflow base validado.
3. A proxima evolucao deve ser um motor diferente, nao mais prompt/LoRA cego no mesmo 5B.
4. Para entrega profissional agora, usar motor externo aprovado e tratar o local apenas como laboratorio.
5. O local so volta a produzir se um teste curto provar movimento real, fidelidade e ausencia de alucinacao.

Plano tecnico que rege a proxima retomada:

- `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/08_plano_antiperda_gpu_video_local.md`

Enquanto essa regra estiver ativa, nao rodar treino LoRA de video nem lote de takes no fluxo antigo.

## Regra v7 - JSON obrigatorio antes de treino

Decisao de 2026-07-11 apos o lote `veo_kling_smoke_4s`:

- a animacao melhorou quando o take passou a ter contrato de cena mais rigido;
- os numeros de movimento sozinhos nao bastam, porque take ruim tambem pode ter muito movimento;
- todo video/take usado para estudo ou treino precisa ter JSON tecnico e leitura humana.

Pacote de estudo gerado:

- `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/qc/video_study_20260711_veo_kling_smoke`

Regra obrigatoria:

1. Extrair `ffprobe`, timeline de frames, metricas de frames e perfil de movimento.
2. Preservar ou gerar sidecar JSON com prompt, negativo, modelo, seed e contrato do take.
3. Gerar contact sheet e olhar visualmente.
4. Criar label humano: `positive`, `positive_weak`, `diagnostic` ou `negative`.
5. Nao treinar nenhum video como positivo sem `07_HUMAN_VIDEO_READING.json` ou equivalente.
6. Takes com texto deformado, fragmentos coloridos, efeito frontal dominante ou camera que perde a cena entram como negativo/diagnostico.

Labels do lote 2026-07-11:

- positivo principal: `take_05_tenebra`;
- positivo de fidelidade: `take_03_estudio_maestro`;
- positivos fracos/diagnosticos: `take_02_cidade_ritmo`, `take_07_cidade_calada`;
- negativos/diagnosticos: `take_04_chapeu`, `take_06_onda_silencio`, `take_09_titulo`.

## Regra de montagem

Nao montar final enquanto houver take reprovado. A montagem so acontece depois de:

- extrair primeiro/meio/ultimo frame;
- conferir ausencia de personagens/silhuetas;
- conferir movimento real;
- conferir continuidade visual;
- registrar aprovacao no QC.

## Render final

Quando os takes estiverem bons no 5B:

1. repetir os takes aprovados no Wan2.2 A14B GGUF HighNoise + LowNoise;
2. aceitar offload para RAM quando necessario;
3. interpolar para 60fps somente apos aprovacao visual;
4. adicionar audio por ultimo.

## Janela especial de GPU historica

Registro historico, nao e janela ativa em 2026-07-11. Regra informada pelo Thiago:

- no domingo, 2026-07-05, o PC sera usado durante o dia;
- GPU liberada somente de 2026-07-05 17:00 ate 2026-07-06 06:00;
- antes dessa janela, nao disparar treino, ComfyUI pesado, Wan, LTXV ou render I2V;
- durante a janela, prioridade para teste pequeno e comparativo, nao render em massa.

Plano que foi recomendado para essa janela:

1. Rodar um take dificil, preferencialmente `05_tenebra` ou `06_onda_silencio`.
2. Comparar Wan 5B LoRA `0.06` contra Wan2.2 A14B HighNoise + LowNoise com offload para RAM.
3. Se houver tempo, testar LTXV 13B no mesmo keyframe.
4. Medir tempo, VRAM/RAM, estabilidade, movimento real e fidelidade.
5. Parar tudo as 06:00 de 2026-07-06.

## Preview atual de trabalho

Em 2026-07-04 foi gerada a V2, mas ela foi reprovada:

- `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_full_preview_v2_20260704.mp4`
- `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_full_preview_v2_20260704_60fps_light.mp4`

Motivos:

- usou imagens pixeladas/retro;
- parecia slideshow, nao animacao real;
- pulou a etapa de imagem-base anime atual com JSON de validacao.

Proxima execucao deve comecar por:

```powershell
cd E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo
$env:MAESTRO_STUDIO_URL="http://127.0.0.1:8029"
python .\run_intro_take_queue.py --all --generate-keyframes --keyframes-only
```

## Regra v8 - RTX 5090, Q8 e render util

Decisao de 2026-07-14 apos os testes com Wan2.2 A14B Q8:

- a RTX 5090 aguenta o Wan2.2 A14B I2V Q8 local com folga de VRAM para takes curtos;
- o Studio foi corrigido para manter `1280x720` real, usando alinhamento 16;
- o teste `1280x720`, Q8, 24 steps, take 02, saturou a GPU por mais de 40 minutos sem
  entregar arquivo final e foi interrompido;
- aumentar steps no escuro nao e evolucao. O ganho agora vem de take bom, contrato de cena,
  seed/prompt controlado, QC e pos-processamento.

Preset aprovado para nova rodada curta:

```powershell
cd E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo
$env:MAESTRO_STUDIO_URL="http://127.0.0.1:8029"
python .\run_intro_take_queue.py --takes 02 03 05 --max-take-seconds 5 --width 1280 --height 720 --fps 30 --steps 20 --guidance 6.0 --model Wan2.2-I2V-A14B-HighNoise-Q8_0.gguf --lora __none__ --lora-strength 0 --motion-profile aggressive --ignore-video-pause --run-label a14b_q8_5090_720p20_controlado
```

Regras para usar esse preset:

1. So rodar com ordem explicita do usuario para liberar GPU.
2. Conferir que o take tem imagem-base aprovada e JSON de contrato.
3. Gerar contact sheet e ffprobe antes de chamar de bom.
4. Se o take aprovado parecer travado, aplicar interpolacao/upscale depois, nao aumentar
   steps automaticamente.
5. Nao repetir Q8 24 steps como padrao. Usar apenas para comparativo tecnico isolado.

Referencia atual:

- bruto bom em 720p/30: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_preview_a14b_q8_5090_4takes_5s_native720_cfr_20260714_123318.mp4`;
- FHD60 para avaliacao: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/intro_preview_a14b_q8_native720_to_fhd60_interp_20260714_151315.mp4`;
- FIXLOG tecnico: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/FIXLOG.md`.
