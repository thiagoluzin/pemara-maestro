# Metodologia Oficial por Takes

## Decisao

A metodologia por takes e regra do ecossistema Pemara para videos profissionais.

Motivo: takes curtos dao mais fidelidade, permitem QC real, reduzem desperdicio e deixam a montagem parecida com producao de cinema/anuncio.

## Papel de cada etapa

### Ideia

Entrada simples do usuario. Exemplo:

```text
Quero um video de 60 segundos para abertura de jogo, urbano, musical, sombrio e cinematografico.
```

### Roteiro

O sistema transforma a ideia em estrutura narrativa:

- abertura;
- apresentacao de mundo;
- tensao;
- virada;
- climax;
- encerramento;
- branding/titulo quando permitido.

### Take Queue

O roteiro vira `take_queue.json`.

Cada take define:

- id;
- slug;
- tempo na timeline;
- duracao;
- objetivo visual;
- imagem-base;
- modelo de imagem recomendado;
- modelo de video recomendado;
- prompt de imagem;
- prompt de animacao;
- movimentos obrigatorios;
- restricoes de identidade;
- criterios de aprovacao;
- criterios de rejeicao.

### Imagem-base

A imagem-base e o contrato visual do take. Sem imagem-base aprovada, o video vira loteria.

Regra:

- gerar keyframes com FLUX/Krea ou Qwen;
- criar um `.json` lateral com o mesmo nome da imagem antes de qualquer uso;
- aprovar antes de animar;
- manter resolucao e composicao consistentes.

### Regra inquebravel de JSON

Sem JSON = ativo invalido.

Essa regra vale para:

- imagem-base gerada por IA;
- imagem recebida como referencia e escolhida para virar take;
- imagem que ja virou take em teste anterior;
- clipe de video por take;
- montagem parcial ou final.

Toda imagem que virar take precisa ter um `.json` lateral no mesmo diretorio, com no minimo:

- `schema_version`;
- `project_id`;
- `type`;
- `image_file`;
- `take_id` e `take_slug`;
- `model`;
- `prompt`;
- `negative` quando houver;
- `width`, `height`;
- `validation_status`;
- `approval_required_before_video`;
- `qc_checklist`;
- `rejection_reasons`.

O status `approved_for_video` so pode existir depois de QC humano/visual. Se o JSON estiver ausente,
invalido, apontando para outro arquivo ou sem prompt, o take deve ser bloqueado antes de chamar o
gerador de video.

### Video por take

Cada imagem-base vira um clipe curto.

Padrao:

- 1280x720 para preview;
- 1920x1080 para final quando possivel;
- 24fps ou 30fps;
- sem audio nativo;
- sem texto nativo;
- sem logo nativo, salvo take de branding controlado.

Cada MP4 de take tambem precisa gerar um `.json` lateral com imagem-base usada, JSON da imagem-base,
prompt de animacao, modelo, LoRA, seed, steps, fps, frames solicitados, status do job e QC pendente.

### QC

Antes da montagem:

- extrair primeiro/meio/final;
- gerar contact sheet;
- verificar identidade;
- verificar movimento;
- verificar artefatos;
- aprovar/refazer.

### Montagem

So montar takes aprovados.

Audio, cortes, fades, branding e loudness ficam na etapa de montagem, nao no modelo de video.

## Formula de prompt de animacao

```text
Animate this approved image as a polished cinematic clip.
Use controlled motion only: [camera], [environment], [particles], [character micro-motions], [light].
Preserve all identities, outfits, objects, composition and style exactly.
Do not add new characters, text, logos, watermarks, captions or native audio.
Avoid face morphing, warped hands, unstable eyes, extra limbs, sudden cuts and exaggerated motion.
```

## Proibicoes globais

- prompt unico como render final;
- take longo sem motivo;
- animar imagem ruim;
- montar take sem QC;
- aceitar rosto mudando;
- aceitar texto falso;
- aceitar marca d'agua;
- aceitar personagem extra;
- aceitar video estatico quando a cena exige movimento.
