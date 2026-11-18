# Plano de Melhoria - Agentes e Skills Pemara

Data: 2026-07-04

## Objetivo

Transformar as skills importadas em um ecossistema operacional confiavel para:

- Maestro Studio;
- Loja e marketing;
- geracao de imagem;
- geracao de video por takes;
- treino LoRA;
- sprites Phaser;
- musica/SFX;
- QA, deploy e watchdogs.

## Estado atual

O ecossistema tem:

- skills NVIDIA/infra ja instaladas;
- 33 skills customizadas importadas de `novo_analisar`;
- 33 perfis de agentes em `E:/Pemara/.agents/profiles`;
- skill diretora `pemara-video-motion-director`;
- nova skill roteadora `pemara-ecosystem-orchestrator`.

Todas as skills customizadas importadas validaram corretamente.

## O que precisa melhorar

### 1. Roteamento

Problema: varias skills podem responder ao mesmo pedido.

Acao:

- usar `pemara-ecosystem-orchestrator` como porta de entrada;
- escolher no maximo 3 skills primarias por tarefa;
- carregar skills NVIDIA/TAO/NeMo/VSS somente quando o pedido exigir essa stack.

### 2. Metadata de UI

Problema: quase todas as custom skills nao tinham `agents/openai.yaml`.

Acao:

- adicionar `agents/openai.yaml` nas skills mais usadas;
- comecar por:
  - `ai-video-intro-pipeline`;
  - `image-production`;
  - `video-production`;
  - `creative-director`;
  - `game-audio-designer`;
  - `phaser-animation-turbo`;
  - `sprite-image-reading`;
  - `automation-engineer`;
  - `qa-automation-engineer`.

### 3. Enxugar skills grandes

Problema: algumas skills tem muito texto no `SKILL.md`, o que pesa contexto e atrapalha uso rapido.

Acao:

- manter no `SKILL.md` apenas regra operacional e roteamento;
- mover detalhes longos para `references/`;
- prioridade:
  - `phaser-platformer-architect`;
  - `project-planner`;
  - `debugger`;
  - `phaser-16bit-platformer`;
  - `performance-optimizer`.

### 4. Scripts reutilizaveis

Problema: varias verificacoes sao repetidas manualmente.

Acao:

- manter `skill_inventory.ps1` em `pemara-ecosystem-orchestrator`;
- criar depois:
  - QC de video por contact sheet e movimento;
  - QC de sprites: escala, frame count e bounding box;
  - QC de cards: texto, logo, produto real e recorte;
  - auditoria de watchdogs/tasks;
  - inventario de GPU/training locks.

### 5. Regras de GPU

Problema: skills podem sugerir treino ou geracao pesada fora da janela.

Acao:

- regra global: se GPU estiver em descanso, so preparar docs, prompts, JSON, filas, QC offline e scripts;
- toda skill de video/imagem/LoRA precisa respeitar essa regra.

### 6. Forward test

Problema: skill boa no papel pode falhar na pratica.

Acao:

- testar cada skill com pedido realista pequeno;
- salvar resultado em docs do ecossistema;
- ajustar trigger, workflow e recursos conforme erro observado.

## Ordem recomendada

1. Consolidar `pemara-ecosystem-orchestrator`.
2. Adicionar metadata UI nas 9 skills mais usadas.
3. Separar referencias das 5 skills maiores.
4. Criar scripts de QC para video, sprites e cards.
5. Criar testes de uso real por dominio.
6. Integrar no Maestro Studio como seletor de fluxo: imagem, video, audio, loja, sprites, treino.

## Arquivos criados

- `E:/Pemara/.agents/skills/pemara-ecosystem-orchestrator/SKILL.md`
- `E:/Pemara/.agents/skills/pemara-ecosystem-orchestrator/references/pemara-skill-map.md`
- `E:/Pemara/.agents/skills/pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1`

## Comando util

Inventario rapido:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\.agents\skills\pemara-ecosystem-orchestrator\scripts\skill_inventory.ps1
```

Inventario focado nas skills Pemara:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\.agents\skills\pemara-ecosystem-orchestrator\scripts\skill_inventory.ps1 -PemaraOnly
```

Validar uma skill:

```powershell
$env:PYTHONUTF8='1'
python C:\Users\admin_remoto\.codex\skills\.system\skill-creator\scripts\quick_validate.py E:\Pemara\.agents\skills\pemara-ecosystem-orchestrator
```
