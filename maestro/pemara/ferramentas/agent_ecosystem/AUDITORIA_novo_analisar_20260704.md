# Auditoria - novo_analisar - 2026-07-04

Origem analisada: `E:/Pemara/novo_analisar`

Destino operacional: `E:/Pemara/.agents`

## Resultado curto

O pacote `novo_analisar` contem uma copia grande do ecossistema de skills NVIDIA ja instalado e uma camada customizada muito util para a Pemara: video por takes, intro de jogo, sprites Phaser, audio de jogo, imagem, QA, performance, automacao e direcao criativa.

Nao foi usado GPU. Esta auditoria mexeu somente em arquivos de agentes, skills e documentacao.

## O que foi importado

As skills customizadas foram copiadas para `E:/Pemara/.agents/skills`:

- `ai-video-intro-pipeline`
- `animation-engineer`
- `audio-analysis`
- `automation-engineer`
- `balance-tuner`
- `beatemup-combat-designer`
- `claude-context-audit`
- `code-archaeologist`
- `creative-director`
- `debugger`
- `demo-release-engineer`
- `game-audio-designer`
- `game-audio-reactive`
- `game-build-flow`
- `game-developer`
- `gamepad-input-specialist`
- `hero-sprite-scaling`
- `image-production`
- `level-designer`
- `modern-pixel-art-hd`
- `pack-doctor`
- `performance-optimizer`
- `phaser-16bit-platformer`
- `phaser-animation-turbo`
- `phaser-platformer-architect`
- `project-planner`
- `qa-automation-engineer`
- `sprite-animation`
- `sprite-image-reading`
- `test-engineer`
- `vanilla-web-patterns`
- `video-production`
- `web-frontend-vanilla`

Os perfis `.md` de agentes foram copiados para:

`E:/Pemara/.agents/profiles`

## O que nao foi duplicado

As skills NVIDIA, NeMo, TAO, VSS, cuOpt, Jetson, Omniverse e similares ja existiam em `E:/Pemara/.agents/skills`. Elas foram mantidas como estavam. O pacote original em `novo_analisar` fica como backup/fonte.

## Validacao

Todas as 33 skills customizadas importadas passaram no validador:

`C:/Users/admin_remoto/.codex/skills/.system/skill-creator/scripts/quick_validate.py`

Observacao: no PowerShell 5.1 e necessario usar `PYTHONUTF8=1`, senao o validador pode falhar por encoding ao ler acentos.

## Fusao com o ecossistema atual

A skill existente `pemara-video-motion-director` foi atualizada para trabalhar junto com as novas skills:

- `ai-video-intro-pipeline`: intro/cutscene por takes, QC, montagem, audio, logo, upscale e pacote de registro.
- `video-production`: montagem, ffmpeg, codecs, contact sheet e formatos.
- `image-production`: imagens-base, keyframes, recorte, alpha, upscale e QC antes de gerar video.
- `creative-director`: roteiro, conceito, prompt e especificacao de takes.
- `game-audio-designer`, `game-audio-reactive`, `audio-analysis`: musica, SFX, audio reativo, BPM, tom e loudness.
- `animation-engineer`, `phaser-animation-turbo`, `sprite-animation`, `sprite-image-reading`, `hero-sprite-scaling`: sprites Phaser, frames, timing, escala runtime e movimento mais humano.
- `qa-automation-engineer`, `test-engineer`, `performance-optimizer`: testes, regressao, navegador, build e performance.

## Regras operacionais novas

1. Video profissional deve seguir metodologia por takes.
2. Antes de gerar video, criar ou aprovar imagens-base/keyframes.
3. Cada imagem-base precisa ter descricao/JSON de cena para manter fidelidade.
4. Cada take precisa ter movimento visivel: camera, parallax, particulas, luz ou acao com inicio/meio/fim.
5. Nao avaliar qualidade por prompt unico longo.
6. Para o jogo, sprite alterado precisa manter escala runtime e padrao dos sprites nao mexidos.
7. Audio entra como etapa separada: direcao, SFX, musica, loudness e sincronismo.
8. GPU em descanso significa trabalhar somente com pesquisa, docs, prompts, JSON, QC e organizacao.

## Aplicacao imediata

Para a intro de `Ritmos da Revolta`, a ordem correta agora e:

1. `creative-director` fecha intencao e ritmo de cada take.
2. `image-production` gera/valida keyframe em anime atual.
3. `pemara-video-motion-director` transforma keyframe aprovado em prompt de movimento.
4. `ai-video-intro-pipeline` organiza takes, QC, montagem e pacote final.
5. `game-audio-designer` cria plano de musica/SFX.
6. `video-production` monta MP4 final, contact sheet e formatos.

## Arquivos principais

- Skill diretora: `E:/Pemara/.agents/skills/pemara-video-motion-director/SKILL.md`
- Pipeline importado: `E:/Pemara/.agents/skills/ai-video-intro-pipeline/SKILL.md`
- Perfis importados: `E:/Pemara/.agents/profiles`
- Fonte original preservada: `E:/Pemara/novo_analisar`
