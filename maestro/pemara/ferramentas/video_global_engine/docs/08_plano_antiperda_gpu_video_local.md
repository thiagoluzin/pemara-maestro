# Plano Anti-Perda de GPU - Video Local

Data: 2026-07-11

Objetivo: parar de gastar GPU em treino/render que nao esta evoluindo e transformar o estudio local
em laboratorio com criterio de corte. A geracao local de video fica pausada ate um novo workflow base
provar movimento real, fidelidade e ausencia de alucinacao em teste curto.

## Decisao operacional

O caminho "Wan 5B I2V + LoRA + mais treino" esta congelado para producao.

Motivo:

- o fluxo gerou muitas imagens vivas, nao animacao;
- quando mexeu mais, alucinou triangulos, faixas, camera/ator e objetos intrusos;
- treino em cima de base fraca nao resolveu o problema estrutural;
- custo em tempo/GPU ficou maior que o ganho.

Estado atual:

- flag ativa: `E:/Pemara/maestro/pemara/dados/flags/video_generation_paused.flag`;
- `run_intro_take_queue.py` bloqueia video local enquanto a flag existir;
- usar `--ignore-video-pause` somente em teste deliberado, curto e documentado;
- sem treino LoRA de video ate um workflow base passar no gate.

## Achado de comunidade

As rotas uteis nao apontam para "treinar mais o mesmo preview 5B". Elas apontam para:

1. controle de camera/estrutura;
2. workflows dedicados HighNoise + LowNoise;
3. modelos ou wrappers com melhor continuidade temporal;
4. geracao por takes curtos com reprova rapida;
5. QC antes de qualquer lote.

Atualizacao complementar: `docs/09_metodo_veo_kling_para_motor_local.md` virou o contrato de como
copiar a forma de trabalho de Veo/Kling dentro do motor local: start/end frame, referencias,
shot contract, variantes curtas e QC antes de treino.

Fontes verificadas:

- Wan2.2 oficial: https://github.com/Wan-Video/Wan2.2
- ComfyUI Wan2.2: https://docs.comfy.org/tutorials/video/wan/wan2_2
- ComfyUI Wan2.2 Fun Camera: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-camera
- ComfyUI Wan2.2 Fun Control: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control
- LTX-Video oficial: https://github.com/Lightricks/LTX-Video
- ComfyUI-LTXVideo: https://github.com/Lightricks/ComfyUI-LTXVideo
- ComfyUI exemplos LTXV: https://comfyanonymous.github.io/ComfyUI_examples/ltxv/
- FramePack oficial: https://github.com/lllyasviel/FramePack
- HunyuanVideo oficial: https://github.com/Tencent-Hunyuan/HunyuanVideo
- SkyReels V2 oficial: https://github.com/SkyworkAI/SkyReels-V2

## Nova matriz de decisao

### Entrega profissional agora

Usar motor externo aprovado quando o objetivo for resultado final profissional.

O local entra como:

- roteiro por takes;
- imagem-base e JSON;
- montagem;
- QC;
- audio;
- upscale;
- registro de assets;
- dataset de aprendizado.

### Laboratorio local 1 - LTX-Video

Prioridade mais alta para proximo teste local porque:

- `ComfyUI-LTXVideo` ja esta instalado;
- ha blueprints LTX 2.0 e LTX 2.3 locais;
- a rota e diferente do Wan 5B puro;
- pode testar prompt-following, motion control e camera sem treinar.

Regra: nao gerar lote. Primeiro teste deve ser um take de 2s a 4s, baixa resolucao, sem LoRA de estilo.

### Laboratorio local 2 - Wan2.2 Fun Camera / Fun Control

Rota candidata se o objetivo for camera mais controlada.

Uso esperado:

- camera path;
- parallax dirigido;
- controle por imagem/condicao;
- reduzir "imagem viva".

Regra: antes de instalar/usar, mapear nodes exigidos e criar workflow isolado. Sem misturar no Studio principal
sem passar smoke test.

### Laboratorio local 3 - FramePack

Candidato para continuidade e takes mais longos, mas ainda nao esta instalado no ComfyUI principal.

Regra:

- instalar somente em pasta isolada ou ambiente de teste;
- primeiro rodar import/check sem GPU;
- depois um smoke de 2s a 4s;
- se alucinar ou travar, encerrar a rota.

### Laboratorio local 4 - Wan A14B GGUF

Nao abandonar, mas tambem nao romantizar.

Uso:

- somente depois de imagem-base aprovada;
- somente smoke pequeno primeiro;
- aceitar offload para RAM apenas quando houver indicio real de ganho.

Escada obrigatoria:

1. 512x288, 2s, poucos steps;
2. 768x432, 3s, se o primeiro passar;
3. 1280x720 somente se o segundo passar visualmente.

## Gate anti-desperdicio

Nenhum modelo/workflow local pode receber treino, lote ou render longo antes de passar:

1. `ffprobe` valido;
2. contact sheet inspecionado;
3. movimento visivel em camera, parallax e evento;
4. sem personagens/silhuetas quando o take e ambiental;
5. sem objetos intrusos;
6. sem faixas/triangulos/blocos coloridos;
7. sem simples zoom;
8. tempo de geracao registrado;
9. VRAM/RAM registrada;
10. JSON lateral do take atualizado.

Se falhar em 2 tentativas curtas, a rota fica reprovada e nao recebe treino.

## Ordem de proxima retomada quando a GPU for liberada

1. Manter pausa global ate ordem explicita.
2. Escolher um unico take dificil: `05_tenebra` ou `06_onda_silencio`.
3. Rodar LTX-Video local em 2s a 4s, sem LoRA de estilo.
4. Se LTX passar, repetir com controle/motion blueprint.
5. Se LTX falhar, testar Wan Fun Camera/Fun Control em smoke isolado.
6. Se controle Wan falhar, testar FramePack isolado.
7. Somente depois decidir se vale treinar.

## Regra de treino

Treino de video so volta quando existir uma base que ja entrega:

- movimento real sem LoRA;
- identidade visual aceitavel;
- baixa taxa de alucinacao;
- tempo por take previsivel;
- workflow reproduzivel.

Treinar antes disso e jogar GPU em cima de problema errado.

## Consequencia pratica

Ritmos da Revolta deixa de ser "vamos ver se o Wan aprende".

Ele vira bancada de validacao:

- cada engine precisa provar um take;
- cada take precisa provar movimento;
- cada movimento precisa passar QC;
- so depois entra treino ou lote.
