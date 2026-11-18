# Pesquisa Comunidade - Modelos de Video e Imagem

Data: 2026-07-14

Objetivo: consolidar o que existe de util na comunidade/open source para o estudio Pemara gerar
animacoes, videos por takes, imagens-base, cards e anuncios sem voltar ao ciclo de treino cego.

## Decisao executiva

Nao existe um unico "LoRA universal" que transforme qualquer prompt em animacao profissional. O
caminho correto e modular:

1. modelo base forte;
2. keyframes aprovados;
3. JSON lateral de imagem e take;
4. controle de camera/movimento quando houver;
5. LoRAs pequenos por funcao;
6. validacao com prompts fixos;
7. promocao somente quando superar baseline sem LoRA.

Ritmos da Revolta continua sendo bancada de validacao, mas o objetivo e um estudio global de
animacoes. Portanto os treinos devem aprender capacidades reutilizaveis, nao decorar um unico video.

## Regra anti-perda

Nenhum treino local de video ou imagem deve ser iniciado so porque existe GPU disponivel.

Antes de treinar, o workflow base precisa passar:

- keyframe aprovado e com `.json`;
- take curto com movimento real;
- contact sheet inspecionado;
- relatorio de falhas;
- baseline sem LoRA salvo;
- criterio de ganho definido.

Se o modelo base gera imagem viva, triangulos, camera/ator intruso, faixa colorida ou objeto
aleatorio, o problema e workflow/base/controle, nao falta de mais treino.

## Video - o que aproveitar

### Wan2.2 A14B / TI2V / Animate / S2V

Uso no ecossistema:

- `Wan2.2 A14B I2V/T2V`: render final pesado por takes aprovados;
- `Wan2.2 TI2V 5B`: rascunho e comparativo, nao motor final quando a qualidade importa;
- `Wan2.2-Animate-14B`: pesquisar para personagem/pose quando o estudio sair do modo ambiental;
- `Wan2.2-S2V-14B`: candidato futuro para audio-driven/speech-to-video.

Regra local:

- para 5090, priorizar A14B Q8/Q5 em 720p real, 20 steps, takes curtos;
- nunca renderizar 60s em prompt unico;
- manter HighNoise/LowNoise pareados;
- usar offload/DRAM somente quando o ganho for medido.

Fonte primaria: Wan2.2 oficial descreve MoE, foco cinematografico, motion mais forte que versoes
anteriores, modelos A14B/TI2V/S2V/Animate e suporte 720p no TI2V 5B.

### Wan Fun Camera / Fun Control

Uso no ecossistema:

- controlar camera quando o take fica parado;
- gerar parallax e movimento com condicionamento externo;
- reduzir "imagem viva" usando camera path, depth/canny/pose/trajectory.

Regra local:

- criar workflow isolado antes de plugar no Studio principal;
- usar camera control em takes que exigem dolly, pan, orbit, zoom, crane;
- nao usar LoRA de 4 steps como padrao de qualidade, porque pode reduzir dinamismo.

Fonte primaria: docs ComfyUI Wan2.2 Fun Camera e Fun Control.

### LTX-Video / LTX-2

Uso no ecossistema:

- segunda opiniao de movimento quando Wan congela;
- keyframe-based animation;
- multi-keyframe e extensao de video;
- no futuro, testar LTX-2 para audio+video e controle fino.

Regra local:

- LTXV 13B/2B distilled para iteracao e comparativo;
- LTX-2/LTX-2.3 ficam em pesquisa pesada porque exigem mais stack e validacao;
- usar prompts longos com camera, evento, parallax e negativo explicito.

Fonte primaria: Lightricks/LTX-Video oficial.

### FramePack

Uso no ecossistema:

- pesquisa de continuidade e anti-drift;
- candidato para takes mais longos quando o motor por take estiver maduro;
- bom para laboratorio isolado, nao substituir o pipeline principal sem smoke test.

Regra local:

- instalar/rodar separado;
- primeiro smoke 2s-4s;
- se falhar duas vezes, reprovar rota sem insistir.

Fonte primaria: FramePack oficial.

### HunyuanVideo

Uso no ecossistema:

- referencia de modelo open forte;
- pesquisa para motion quality e I2V;
- nao e prioridade local direta sem ambiente adequado, porque requisitos oficiais de VRAM para
  720p/129 frames ficam acima de uma unica GPU gamer.

Regra local:

- usar como pesquisa, nao como promessa imediata;
- considerar apenas variantes/quantizacoes/wrappers quando houver smoke test reproduzivel.

Fonte primaria: Tencent-Hunyuan/HunyuanVideo oficial.

## Treino de video - ferramentas uteis

### Musubi Tuner

Uso:

- LoRA de Wan2.1/2.2;
- LoRA de FramePack;
- LoRA de HunyuanVideo;
- tambem cobre Qwen-Image, FLUX e outros modelos de imagem.

Condicao:

- ferramenta comunitaria, nao oficial dos modelos;
- recomenda 24GB+ VRAM para video training e 64GB+ RAM;
- encaixa bem na 5090 para LoRA, com cuidado em resolucao, block swap, fp8 e grad metrics.

### FineTrainers

Uso:

- alternativa Hugging Face para LoRA/full finetune em Wan;
- util para validar LoRA em Diffusers;
- bom para experimentos pequenos e control LoRA.

Condicao:

- Windows pode exigir adaptacao de scripts;
- usar como rota de pesquisa/validacao, nao misturar no pipeline principal sem projeto isolado.

### DiffSynth-Studio

Uso:

- suporte amplo a Wan2.2, Qwen-Image, FLUX, LTX-2 e outros;
- CPU offload training e low-VRAM/offload podem aproveitar 5090 + RAM;
- forte candidato para experimentar treino grande com offload.

Condicao:

- instalar em ambiente separado;
- medir tempo/VRAM/RAM antes de qualquer rotina diaria;
- usar primeiro em dataset pequeno.

### SimpleTuner

Uso:

- forte para imagem e tambem cobre video;
- suporta FLUX, Qwen Image, HiDream, Wan, LTX Video e outros;
- tem opcoes modernas: quantizacao, offload, validation sweeps, CREPA/video alignment.

Condicao:

- bom candidato para padronizar treinos de imagem e validar LoRAs;
- antes de adotar, criar um projeto pequeno com 10-20 imagens e golden prompts.

### ai-toolkit

Uso:

- suite pratica para LoRA de imagem/video;
- cobre FLUX, Qwen-Image, HiDream, Wan2.2, LTX-2 e ACE-Step;
- tem UI/CLI, util para acelerar experimentos.

Condicao:

- bom para laboratorio, mas nao substituir guardrails do Pemara;
- toda saida precisa passar nosso QC e JSON.

## Imagem - o que aproveitar

### Qwen-Image / Qwen-Image-Edit

Uso no ecossistema:

- cards e anuncios com texto;
- layout grafico;
- edicao de imagem com preservacao de produto;
- slogans curtos, portugues correto, tags de preco e informacoes do produto.

Regra local:

- Qwen deve ser o motor preferido para `Cards Reais` e `Cards IA`;
- produto real deve entrar como referencia/edicao, nao ser inventado;
- todo anuncio precisa de JSON com produto, preco, fonte da foto, modelo, prompt, negativo e QC;
- nada de composicao por script como arte final.

Fonte primaria: Qwen-Image oficial destaca texto complexo, layout e edicao precisa.

### FLUX.1 Krea dev / FLUX.1-dev

Uso no ecossistema:

- imagem bonita, fotorealista e cinematografica;
- background premium;
- produto em ambiente editorial;
- Sprunki e estilo visual quando texto nao for o foco.

Regra local:

- FLUX/Krea nao deve ser o motor principal de card com texto;
- usar para fundo, mood, fotografia e material visual;
- se houver texto/preco/logo, mandar para Qwen/Edit ou composicao controlada por workflow validado.

Fonte primaria: model card FLUX.1 Krea dev descreve 12B e foco em fotografia estetica.

### Stable Diffusion 3.5 Large

Uso no ecossistema:

- alternativa text-to-image de alta qualidade;
- bom candidato para comparativo de prompt adherence e tipografia;
- manter como rota de backup, respeitando licenca.

Regra local:

- testar em golden set de imagem, nao instalar por impulso;
- se nao superar Qwen/FLUX em cards/produto, nao vira padrao.

### HiDream-I1 Full

Uso no ecossistema:

- candidato open de 17B para imagem geral de alta qualidade;
- bom para testar fotografia, anime atual e concept art;
- pode virar comparativo contra FLUX/Krea.

Regra local:

- instalar/testar apenas se houver espaco e workflow claro;
- passar pelo mesmo golden set de cards, produto, anime e background.

## LoRAs recomendados por familia

Nao treinar um LoRA monolitico. Treinar familias:

1. `pemara_video_camera_motion`: camera, dolly, orbit, parallax, crane, rack focus.
2. `pemara_video_environment_fx`: luz, particulas, static, reflexos, energia, clima.
3. `pemara_video_anime_moderno`: acabamento anime/cinematico reutilizavel.
4. `pemara_video_game_intro`: ritmo de abertura de jogo, mas sem decorar Ritmos da Revolta.
5. `pemara_card_layout_real`: layout de anuncio profissional com produto real preservado.
6. `pemara_brand_logo_text`: uso correto de logo, infinito do autismo, Pemara Tech e textos.
7. `pemara_product_photo_edit`: limpeza, fundo, iluminacao e preservacao de objeto real.

Cada LoRA precisa ter:

- dataset proprio;
- fonte dos assets;
- `.json` por amostra;
- golden set fixo;
- baseline sem LoRA;
- comparativo com 2-3 pesos;
- criterio de promocao.

## Golden sets obrigatorios

### Video

Manter 12 prompts/takes fixos:

- 4 ambientais com camera forte;
- 3 anime/game intro;
- 2 produto/propaganda em movimento;
- 1 personagem/pose;
- 1 transicao/titulo;
- 1 take de stress contra alucinacao.

Metrica minima:

- movimento de camera visivel;
- evento com inicio/meio/fim;
- parallax;
- sem intrusos;
- sem texto falso;
- duracao/fps/resolucao corretos;
- tempo, VRAM e RAM registrados.

### Imagem

Manter 20 prompts/produtos fixos:

- 8 cards reais de loja com foto original;
- 4 cards IA com texto;
- 4 anuncios sem texto pesado;
- 2 logos/branding;
- 2 imagens anime/cinematicas.

Metrica minima:

- produto correto;
- sem trocar tipo de item;
- texto legivel em portugues;
- preco e parcelas fiéis;
- logo correto;
- especificacoes sem invencao;
- dimensoes sociais corretas.

## Ordem pratica de implantacao

1. Atualizar model registry com `Qwen-Image/Edit`, `FLUX Krea`, `HiDream`, `SD3.5`, `Wan Fun`, `LTX`, `FramePack`, `DiffSynth`, `SimpleTuner`, `ai-toolkit`.
2. Criar `training_recipes/` com receitas por familia, mas sem rodar treino automatico.
3. Criar golden set e avaliador visual/JSON.
4. Testar Qwen-Image/Edit em 5 cards reais com fotos originais.
5. Testar Wan Fun Camera em 1 take dificil.
6. Testar LTXV como comparativo no mesmo take.
7. Somente depois liberar treino LoRA de video.

## Fontes verificadas

- Wan2.2 oficial: https://github.com/Wan-Video/Wan2.2
- ComfyUI Wan Fun Camera: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-camera
- ComfyUI Wan Fun Control: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control
- LTX-Video oficial: https://github.com/Lightricks/LTX-Video
- FramePack oficial: https://github.com/lllyasviel/FramePack
- HunyuanVideo oficial: https://github.com/Tencent-Hunyuan/HunyuanVideo
- Musubi Tuner: https://github.com/kohya-ss/musubi-tuner
- FineTrainers Wan: https://github.com/huggingface/finetrainers/blob/main/docs/models/wan.md
- DiffSynth-Studio: https://github.com/modelscope/DiffSynth-Studio
- SimpleTuner: https://github.com/bghira/SimpleTuner
- ai-toolkit: https://github.com/ostris/ai-toolkit
- Qwen-Image: https://huggingface.co/Qwen/Qwen-Image
- Qwen-Image blog: https://qwenlm.github.io/blog/qwen-image/
- FLUX.1 Krea dev: https://huggingface.co/black-forest-labs/FLUX.1-Krea-dev
- Stable Diffusion 3.5 Large: https://huggingface.co/stabilityai/stable-diffusion-3.5-large
- HiDream-I1 Full: https://huggingface.co/HiDream-ai/HiDream-I1-Full
