# Pesquisa Comunidade - Animacao, Video, Treino e LoRA

Data: 2026-07-05

## Resumo

Existe material util em GitHub, Hugging Face e comunidade para melhorar o ecossistema Pemara de animacao/video. O caminho mais promissor nao e gerar um video longo em prompt unico. A comunidade converge para:

- imagem/keyframe aprovado antes do video;
- clipes curtos por takes;
- LoRA fraco para estilo/identidade;
- controle de movimento por prompt explicito, camera e parallax;
- modelos diferentes para iteracao e finalizacao;
- QC visual e tecnico a cada checkpoint;
- montagem final fora do modelo.

## Fontes e o que aproveitar

### Wan2.2

Fonte principal: https://github.com/Wan-Video/Wan2.2

Uso Pemara:

- manter como base principal para previews e takes locais;
- usar 5B para iteracao;
- usar A14B com offload/DRAM para render final de takes aprovados;
- nao usar prompt unico longo como avaliacao de qualidade.

Observacao de comunidade: Wan2.2 tem workflows oficiais/nativos no ComfyUI, incluindo 5B e 14B.

Fonte: https://docs.comfy.org/tutorials/video/wan/wan2_2

### Musubi Tuner

Fonte: https://github.com/kohya-ss/musubi-tuner

Uso Pemara:

- candidato principal para treino LoRA de video;
- suporta Wan2.1/2.2, HunyuanVideo, FramePack, Qwen-Image, Flux e outros;
- serve para padronizar treino e comparacao de checkpoints.

Regra:

- testar primeiro com LoRA pequeno e dataset curto;
- rank 16/alpha 16 aparece como ponto comum em discussoes de Wan, mas deve ser validado por take e objetivo.

### DiffSynth Studio

Fonte: https://github.com/modelscope/DiffSynth-Studio

Uso Pemara:

- alternativa forte para treino/inferencia Wan e experimentos;
- bom para comparar treinamento Wan quando Musubi falhar ou nao aplicar o efeito;
- tambem tem sinal de expansao para imagem, musica e low VRAM.

Regra:

- tratar como laboratorio paralelo, nao substituir o pipeline principal sem teste A/B.

### LTX Video / LTX-2

Fontes:

- https://github.com/Lightricks/ltx-video
- https://github.com/Lightricks/LTX-2
- https://github.com/Lightricks/ComfyUI-LTXVideo/

Uso Pemara:

- candidato para iteracoes rapidas e LoRA/IC-LoRA;
- interessante para controle por depth/canny/edge e consistencia;
- testar quando Wan ficar estatico ou pesado demais.

Regra:

- LTX pode ser bom para movimento e controle, mas deve passar pelo mesmo QC por takes.

### FramePack

Fontes:

- https://github.com/lllyasviel/framepack
- https://github.com/kijai/ComfyUI-FramePackWrapper

Uso Pemara:

- candidato para videos mais longos e reducao de drift;
- bom para pesquisa de continuidade temporal;
- nao virar default ate integrar e comparar com Wan/LTX.

Regra:

- usar para testes de continuidade, nao para substituir a metodologia por takes.

### HunyuanVideo / HunyuanVideo-I2V

Fontes:

- https://github.com/Tencent-Hunyuan/HunyuanVideo
- https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V

Uso Pemara:

- alternativa de base I2V/T2V;
- possui ecossistema de LoRA e fine-tuning;
- util para comparacao quando Wan falhar em movimento ou quando precisar de outro vies visual.

Regra:

- instalar/testar apenas se houver janela de GPU e objetivo claro.

## Regras Praticas Para Pemara

1. Nunca avaliar qualidade por video longo unico.
2. Criar keyframes em imagem primeiro.
3. Validar cada keyframe com JSON/descritivo fiel.
4. Gerar takes de 4s a 8s.
5. Cada take precisa ter:
   - camera;
   - parallax;
   - evento com inicio/meio/fim;
   - movimento de luz, particula ou objeto;
   - proibicao clara de slideshow/zoom simples.
6. Usar LoRA baixo no primeiro passe: `0.10` a `0.25`.
7. Aumentar LoRA somente quando identidade/estilo estiver escapando.
8. Para render final, comparar:
   - Wan2.2 5B + LoRA;
   - Wan2.2 A14B high/low noise;
   - LTX;
   - FramePack se a prioridade for duracao/continuidade.
9. Sempre montar o video final fora do modelo.
10. Gerar contact sheet e QC antes de aprovar.

## Treinos Prontos Para Testar Antes de Treinar do Zero

Existem LoRAs/modelos prontos que podem ser testados no ecossistema Pemara antes de gastar GPU treinando do zero. Eles nao substituem treino proprio, mas servem como aceleradores, controle de camera/movimento e referencia de configuracao.

### LTX 2.x - controle de movimento/camera

Fontes:

- https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Motion-Track-Control
- https://huggingface.co/Lightricks/LTX-2-19b-IC-LoRA-Pose-Control
- https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Right
- https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Static

Uso Pemara:

- testar controle de camera e trajetoria antes de treinar motion LoRA propria;
- bom candidato para tirar o aspecto de imagem parada;
- especialmente util em takes com personagem/objeto ou camera definida.

Risco:

- precisa workflow LTX bem encaixado;
- pode controlar melhor a camera do que preservar identidade/estilo.

### Wan / LightX2V - distill, lightning e movimento

Fontes:

- https://huggingface.co/lightx2v/Wan2.2-Lightning
- https://huggingface.co/lightx2v/Wan2.2-Distill-Loras
- https://huggingface.co/lovis93/Motion-Lora-Camera-Push-In-Wan-14B-720p-I2V
- https://huggingface.co/Rob1221rib/wan21-fp8-loras

Uso Pemara:

- testar LoRAs de camera em Wan antes de treinar camera/motion propria;
- testar lightning/distill para previews rapidos, nao como qualidade final automatica.

Risco:

- relatos de comunidade indicam que alguns LoRAs aceleradores podem reduzir movimento ou deixar tudo em slow motion;
- precisa comparar contra base sem LoRA e contra 40/50 steps.

### Hunyuan / FramePack

Fontes:

- https://huggingface.co/tencent/HunyuanVideo-I2V
- https://huggingface.co/blog/neph1/framepack-lora-experiment

Uso Pemara:

- testar como alternativa para continuidade temporal e efeitos;
- aproveitar LoRA/training code do ecossistema Hunyuan.

Risco:

- compatibilidade e workflow podem exigir mais ajuste que Wan/LTX.

### Regra de Compra de Tempo

Antes de treinar LoRA propria para movimento:

1. escolher um unico take dificil;
2. gerar baseline sem LoRA;
3. testar 1 LoRA pronta de camera/motion;
4. testar 1 LoRA pronta de aceleracao apenas para preview;
5. medir com contact sheet e diferenca entre frames;
6. so treinar do zero se o ganho pronto for insuficiente.

Prioridade pratica:

1. LTX Motion Track / Pose / Camera Control;
2. Wan camera LoRAs;
3. Wan LightX2V/Distill para preview;
4. Hunyuan/FramePack como pesquisa de continuidade.

## Pesquisa Que Vira Skill/Agente

Adicionar ao ecossistema:

- `video-research-miner`: monitora GitHub/Hugging Face/ComfyUI para novos workflows e trainers.
- `video-lora-trainer-qc`: padroniza treino, checkpoints, previews e comparacao.
- `motion-qc-reviewer`: mede diferenca entre frames e gera contact sheet.
- `take-director`: transforma roteiro em takes com camera, evento, parallax e negativos.

## Prioridade de Teste

Quando a GPU estiver liberada:

1. Um take dificil da intro `Ritmos da Revolta`.
2. Wan2.2 5B atual como baseline.
3. Wan2.2 A14B high/low noise com offload DRAM.
4. LTX como alternativa de movimento.
5. FramePack como teste de continuidade.
6. Comparar lado a lado com contact sheet, nao pelo feeling isolado.

## Fontes Consultadas

- Wan2.2 GitHub: https://github.com/Wan-Video/Wan2.2
- ComfyUI Wan2.2 docs: https://docs.comfy.org/tutorials/video/wan/wan2_2
- Musubi Tuner: https://github.com/kohya-ss/musubi-tuner
- Musubi Wan discussion: https://github.com/kohya-ss/musubi-tuner/discussions/455
- DiffSynth Studio: https://github.com/modelscope/DiffSynth-Studio
- LTX-Video: https://github.com/Lightricks/ltx-video
- LTX-2: https://github.com/Lightricks/LTX-2
- ComfyUI LTXVideo: https://github.com/Lightricks/ComfyUI-LTXVideo/
- FramePack: https://github.com/lllyasviel/framepack
- ComfyUI FramePack Wrapper: https://github.com/kijai/ComfyUI-FramePackWrapper
- HunyuanVideo: https://github.com/Tencent-Hunyuan/HunyuanVideo
- HunyuanVideo-I2V: https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V
- LTX Motion Track IC-LoRA: https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Motion-Track-Control
- LTX Pose IC-LoRA: https://huggingface.co/Lightricks/LTX-2-19b-IC-LoRA-Pose-Control
- LTX Camera Control Dolly Right: https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Right
- Wan2.2 Lightning: https://huggingface.co/lightx2v/Wan2.2-Lightning
- Wan2.2 Distill LoRAs: https://huggingface.co/lightx2v/Wan2.2-Distill-Loras
- Wan camera push-in LoRA: https://huggingface.co/lovis93/Motion-Lora-Camera-Push-In-Wan-14B-720p-I2V
- Wan FP8 camera LoRAs: https://huggingface.co/Rob1221rib/wan21-fp8-loras
