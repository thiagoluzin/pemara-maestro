# Plano RTX 5090 - Qualidade Maxima

Data: 2026-07-06

Objetivo: definir o perfil futuro de qualidade maxima do ecossistema Pemara quando houver uma
RTX 5090 32GB, usando tambem RAM do sistema por offload/mmap quando valer a pena.

Este plano nao altera a rotina atual da RTX 5080. Ele cria a meta de upgrade para video, imagem,
anuncios, musica e SFX.

## Regra principal

Quando a RTX 5090 estiver instalada, o perfil padrao de entrega final deixa de ser economico.
O sistema deve priorizar qualidade, fidelidade e consistencia, aceitando mais tempo de render.

Regra operacional:

- preview e exploracao ainda podem usar modelos leves;
- entrega final aprovada usa o maior preset local estavel;
- RAM pode ser usada para offload se isso permitir quantizacao superior;
- nunca sacrificar fidelidade de produto, texto ou identidade visual para ganhar velocidade.

## Video

### Motor local principal

Preset maximo Wan para a 5090:

- `Wan2.2-I2V-A14B-HighNoise-Q8_0.gguf`
- `Wan2.2-I2V-A14B-LowNoise-Q8_0.gguf`

Uso:

- videos por takes;
- imagem-base aprovada antes do video;
- 1280x720 como alvo inicial;
- 24 ou 30 fps na geracao;
- interpolacao para 60 fps somente depois do take aprovado;
- takes de 5s a 8s;
- steps entre 24 e 32 para final;
- LoRA fraco quando necessario, normalmente `0.05` a `0.15`.

Fallback forte se Q8_0 ficar lento demais:

- `Wan2.2-I2V-A14B-HighNoise-Q6_K.gguf`
- `Wan2.2-I2V-A14B-LowNoise-Q6_K.gguf`

Preset atual a manter como producao rapida:

- `Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf`
- `Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf`

### Pesquisa pesada acima do A14B

Para explorar a 5090 sem medo:

- Step-Video-TI2V 30B: candidato pesado para texto+imagem->video;
- LTX-2 19B: candidato para video com audio sincronizado e testes de continuidade;
- FramePack: candidato para tomadas longas e anti-drift.

Esses modelos entram como pesquisa isolada antes de virar producao. Nao substituir Wan A14B Q8
sem teste comparativo em takes iguais.

## Imagem e keyframes

### Keyframes cinematograficos

Prioridade:

1. FLUX.1 Krea/dev em maior precisao disponivel para imagem cinematografica, keyframes e produto.
2. Qwen Image em maior precisao disponivel para layout, tipografia e composicao grafica.
3. FP8 fica como preset rapido, nao como preset final quando a 5090 estiver disponivel.

Regra:

- gerar imagem-base em alta qualidade;
- salvar JSON de prompt, modelo, seed e parametros;
- validar visualmente antes de animar;
- nao animar imagem rejeitada.

## Anuncios e cards da loja

Perfil 5090 para marketing:

- produto real sempre vem de foto real raspada/curada;
- IA pode melhorar cenario, luz, acabamento e composicao;
- IA nao deve inventar modelo, marca, ficha tecnica, preco ou caracteristica;
- texto comercial critico vem do sistema/HTML/dados da loja;
- logo Pemara Tech e simbolo do infinito do autismo entram como assets oficiais, nao como desenho alucinado;
- Qwen Image deve ser usado para layout/tipografia quando houver texto dentro da imagem;
- FLUX/Krea deve ser usado para fundos, key visuals e acabamento fotografico;
- composicao final precisa parecer anuncio profissional, nunca colagem tipo Paint.

Fluxo obrigatorio:

1. selecionar produto com foto real aprovada;
2. validar nome, preco, parcelas e especificacoes no banco;
3. gerar/editar arte em qualidade maxima;
4. fazer QC visual e de texto;
5. exportar em formatos sociais responsivos.

## Musica

Padrao premium:

- Google Lyria/Vertex para musica completa quando o custo compensar;
- audio gerado deve ser medido antes de aprovar: duracao, sample rate, canais, loudness, clipping.

Uso local/experimental:

- LTX-2 se o objetivo for video+audio sincronizado;
- modelos locais de musica entram como pesquisa, nao como padrao enquanto Lyria for barato e melhor.

## SFX

Padrao de qualidade:

- Stable Audio como alvo preferido para SFX e ambientes;
- AudioCraft/AudioGen local como experimental;
- ElevenLabs SFX como fallback quando entregar melhor em um caso especifico.

Regra de SFX:

- gerar 3 a 5 variacoes por prompt;
- medir loudness, pico, duracao e clipping;
- normalizar para o mix do projeto;
- criar variacao de pitch/detune para SFX repetivel;
- salvar prompt e parametros junto do asset.

## Memoria e desempenho

Perfil 5090:

- VRAM: usar 32GB como alvo de qualidade, nao como limite para economizar;
- RAM: usar 64GB para offload/mmap quando permitir Q8_0, 30B ou cenas mais longas;
- se Step-Video 30B virar rotina, avaliar upgrade para 128GB RAM;
- aceitar render lento para final, mas manter preset rapido para iteracao.

Escada pratica:

1. Rascunho: modelos leves/rapidos.
2. Preview aprovado: Wan A14B Q5/Q6 ou FLUX/Qwen FP8 conforme tipo.
3. Final 5090: Wan A14B Q8_0, FLUX/Qwen em maior precisao, audio premium.
4. Final especial: Step-Video 30B ou LTX-2 quando superar Wan em teste comparativo.

## Criterio de entrada em producao

Um preset 5090 so vira padrao se passar por:

- teste em pelo menos 3 takes diferentes;
- contact sheet;
- ffprobe/metadata;
- verificacao visual manual;
- comparacao com preset anterior;
- registro em QC.

Sem QC, nao vira regra.
