# Formula de Modelos

## Decisao

O ecossistema local ja tem modelos suficientes para operar o motor por takes.

## Imagem-base

### FLUX.1 Krea dev FP8

Uso:

- keyframes bonitos;
- visual cinematico;
- cenas 3D/cartoon/premium;
- composicao de ambiente.

### FLUX.1-dev

Uso:

- treino LoRA principal;
- identidade/estilo com mais controle;
- base comparativa contra Krea.

### Qwen Image

Uso:

- texto e layout;
- cards;
- logos;
- composicao grafica;
- correcao/edicao quando fidelidade textual importa.

Nao usar Qwen como primeira opcao para cena cinematografica pura se FLUX/Krea estiver entregando melhor acabamento.

## Video

### Wan2.2 TI2V/I2V 5B

Uso:

- treino LoRA;
- preview;
- iteracao diaria;
- geracao de takes curtos.

Padrao para rotina.

### Wan2.2 A14B GGUF HighNoise + LowNoise

Uso:

- render final pesado;
- takes importantes ja aprovados no 5B;
- cenas que precisam de mais estabilidade/detalhe.

Nao usar como treino local principal agora.

Regra de pesquisa:

- HighNoise deve ser tratado como etapa de estrutura, composicao e movimento amplo.
- LowNoise deve ser tratado como etapa de detalhe, textura, cor e acabamento.
- Prioridade tecnica: criar workflow dedicado HighNoise + LowNoise para I2V final.

### LTXV 13B

Uso:

- teste rapido de movimento;
- comparacao;
- alternativa quando Wan travar ou ficar estatico.

Regra de prompt:

- LTX responde melhor a prompts longos e explicitos.
- Usar como comparativo quando Wan 5B virar imagem viva.

### FramePack

Uso:

- pesquisa para long shots;
- anti-drift;
- possivel motor separado para videos longos no futuro.

Nao usar como pipeline padrao ate existir instalacao isolada e teste controlado.

## NVIDIA NIM

Uso permitido:

- analisar logs de treino;
- comparar checkpoints;
- revisar prompts;
- gerar relatorio de QC;
- sugerir ajustes tecnicos.

Uso proibido:

- agente autonomo;
- tomar decisao sem aprovacao;
- substituir treino local.

## Formula oficial

```text
Imagem-base aprovada: FLUX/Krea ou Qwen
Preview animado: Wan2.2 5B
Comparativo de movimento: LTXV 13B
Treino LoRA: Wan2.2 5B
Render final: Wan2.2 A14B HighNoise + LowNoise quando necessario
QC: frames + contact sheet + analise visual
Montagem: FFmpeg/Maestro
```
