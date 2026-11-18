# Metodo Veo/Kling Para o Motor Local

Data: 2026-07-11

Objetivo: copiar a forma correta de trabalho dos motores fortes de video, sem fingir que o motor
local atual vai resolver tudo com mais treino. Veo e Kling funcionam melhor quando recebem direcao
de cena, referencias visuais, frames de inicio/fim, duracao curta, camera clara e multiplas variantes.

## O que Veo/Kling fazem melhor

### 1. Clipe curto, nao filme inteiro

O padrao profissional e gerar clipes curtos e controlaveis. O video longo nasce da montagem de takes.

Regra Pemara:

- take normal: 5s a 8s;
- take especial: ate 10s;
- video longo so por montagem;
- prompt unico longo continua proibido para producao.

### 2. Primeiro frame e ultimo frame

Veo 3.1 e Kling usam primeiro/ultimo frame para guiar a transicao. Isso reduz "imagem viva" porque
o modelo precisa sair de um estado visual e chegar em outro estado visual definido.

Regra Pemara:

- cada take importante deve ter `start_frame` e `end_frame`;
- se nao houver end frame, o JSON deve explicar por que;
- end frame pode ser gerado como imagem separada antes do video;
- video local deve tentar interpolar entre estados, nao apenas animar uma imagem parada.

### 3. Referencias/ingredientes

Veo permite usar imagens de referencia para direcionar conteudo. Kling tambem trabalha bem com
referencias e start/end frames. Isso e exatamente o que precisamos para identidade, objetos,
produto/personagem/cenario e estilo.

Regra Pemara:

- separar imagem-base, referencia de estilo, referencia de objeto/personagem e frame final;
- nunca enfiar tudo no prompt textual;
- todo asset visual precisa de JSON lateral.

### 4. Prompt de cena, nao prompt decorativo

As fontes convergem em um prompt com:

- sujeito;
- acao visivel;
- cena/contexto;
- camera;
- luz;
- atmosfera;
- proibicoes.

Regra Pemara:

- todo take precisa preencher `shot_contract`;
- camera precisa ser nomeada: dolly, truck, crane, arc, pan, tilt, rack focus, drone;
- o evento precisa ter inicio, meio e fim;
- negativo deve bloquear texto falso, personagens intrusos, camera rig, faixas, triangulos e slideshow.

### 5. Variantes curtas antes de final

Motores fortes geram variantes e o humano escolhe. O erro local foi tratar a primeira saida como
caminho de treino.

Regra Pemara:

- gerar 2 a 4 variantes curtas quando a GPU/credito estiver liberado;
- escolher por QC, nao por feeling;
- so regenerar final da variante aprovada;
- custo medido por take aprovado, nao por segundo gerado.

## Como isso vira motor local

### Estrutura obrigatoria por take

```json
{
  "shot_contract": {
    "provider_style": "veo_kling",
    "subject": "",
    "action": "",
    "scene": "",
    "camera": {
      "angle": "",
      "movement": "",
      "lens": "",
      "focus": ""
    },
    "lighting": "",
    "mood": "",
    "motion_beats": {
      "start": "",
      "middle": "",
      "end": ""
    },
    "visual_references": {
      "start_frame": "",
      "end_frame": "",
      "style_refs": [],
      "object_refs": []
    },
    "variants": {
      "count": 4,
      "duration_seconds": 6,
      "select_before_final": true
    },
    "negative_rules": []
  }
}
```

### Rota de producao

1. Escrever roteiro por takes.
2. Criar start frame.
3. Criar end frame quando o take tiver transformacao, travessia, revelacao ou climax.
4. Criar JSON lateral dos frames.
5. Gerar prompt estruturado no formato Veo/Kling.
6. Gerar variante curta.
7. Fazer `ffprobe`, contact sheet e QC.
8. Reprovar rapido se for imagem viva ou alucinar.
9. So entao renderizar final/maior.

## Traducao para nossos modelos locais

### LTX-Video

Usar como primeira rota local porque ja existe no ComfyUI. Deve receber prompt longo, claro, com
camera/evento e referencias. Primeiro teste sem LoRA de estilo.

### Wan Fun Camera / Fun Control

Usar quando a prioridade for camera e movimento dirigido. Copia a logica Kling/Veo de camera control,
mas dentro do ecossistema Wan/Comfy.

### FramePack

Usar para continuidade/anti-drift, mas em ambiente isolado. Nao vira default sem smoke test.

### Wan A14B

Usar como rota pesada quando a cena ja esta desenhada por start/end frame. Nao jogar A14B em prompt
solto.

## Gate novo

Nao gastar GPU se faltar qualquer item:

- start frame aprovado;
- JSON lateral do start frame;
- shot_contract preenchido;
- camera e evento com inicio/meio/fim;
- negativos especificos;
- duracao curta;
- criterio de aprovacao;
- pasta de QC.

Nao treinar LoRA se o workflow base nao consegue mover corretamente sem LoRA.

## Fontes

- Veo Gemini API: https://ai.google.dev/gemini-api/docs/veo
- Veo first/last frames no Google Cloud: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-first-and-last-frames
- Veo prompt guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide
- Kling Image to Video API: https://kling.ai/document-api/api/video/3-0-omni/image-to-video
- Kling Start-End Frame no ComfyUI: https://docs.comfy.org/built-in-nodes/partner-node/video/kwai_vgi/kling-start-end-frame-to-video
- Kling Prompt Guide: https://kling.ai/blog/kling-ai-prompt-guide

