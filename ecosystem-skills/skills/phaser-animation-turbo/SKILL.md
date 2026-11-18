---
name: phaser-animation-turbo
description: >
  Agente turbo para corrigir sprites, spritesheets, escala, proporcao e animacoes em Ritmos da
  Revolta/Phaser. Use quando houver frame cortado, personagem crescendo/encolhendo, idle/run/dash
  patinando, ataque ruim, pulo/hurt/esquiva fora de porte, hitbox/evento fora de timing, ou quando
  precisar aplicar fluxo Unity-like de Sprite Editor/AnimationClip dentro do pipeline Phaser.
---

# Phaser Animation Turbo

Use esta skill como entrada principal para trabalho de sprites e animacao 2D do projeto. Ela combina:
`sprite-image-reading`, `hero-sprite-scaling`, `sprite-animation` e `animation-engineer`.

## Regra central

Nao altere sprite ou codigo por impressao visual solta. Primeiro medir, depois corrigir a causa raiz, depois validar no runtime.

REGRA DE OURO: o tamanho real e o do RUNTIME. `npm run audit:size` MENTE (mede com correcoes
aplicadas) — nunca decida escala por ele. Use `npm run measure:hero <hero>` (com `npm run serve`) ou um
snippet lendo `window.game.scene.getScene('StageScene').player`. E "body fixo != tamanho consistente":
o porte se trava pela ESCALA-DE-PERSONAGEM (cabeca/proporcao), nao pela altura de corpo unica.

## Fluxo obrigatorio

1. **Ler o contrato real**
   - `js/scenes/BootScene.js`: como texturas/anims sao carregadas.
   - `js/config/index.js`: `CHARACTERS.<hero>.hitbox.animScales`.
   - `js/config/heroFrameScaleCorrections.json`: correcoes por frame.
   - `tools/check_sprites.py` e `tools/asset_pipeline/*`: gates existentes.

2. **Medir como Sprite Editor**
   - Para cada frame: `cellW`, `cellH`, `bbox`, `bottomGap`, `centerX`, `topY`, `bodyH`.
   - Para personagem: origem padrao no pe, equivalente a Phaser `origin(0.5, 1)`.
   - Para armas/sabres/correntes/FX largos: se o frame encosta na borda, dividir a fita em PNGs ou sheets maiores.

3. **Definir contrato de AnimationClip**
   - `key`, `texture`, `frameWidth`, `frameHeight`, `frameRate`, `repeat`, `origin`, `scaleMode`.
   - Fases: `startup`, `active`, `recovery`.
   - Eventos: SFX, hitbox, dust, invulnerabilidade, hitstop e cancel por frame.

4. **Separar visual de mecanica**
   - Animacao ilustra o estado; fisica/dash/ataque usam tempo real em ms.
   - Hitbox/hurtbox nao devem depender do tamanho visual do frame.
   - Nunca usar `displaySize` ou escala X/Y diferente para esconder sprite ruim.

5. **Corrigir na raiz**
   - Frame cortado: aumentar canvas/reempacotar/dividir sheet; nao encolher o personagem.
   - Personagem variando tamanho: corrigir asset/anchor/animScale/correcao uniforme conforme a causa.
   - Personagem patinando: corrigir centerX/base/foot lock e timing, nao só velocidade.
   - Ataque ruim: remontar poses fortes e eventos; nao colocar recovery como impacto.

6. **Validar**
   - `npm run check:sprites`   (herois)
   - `npm run check:bosses`    (chefes/sub-chefes — escala em `js/config/visualScaleTargets.js`)
   - `npm run audit:runtime-manifest`
   - `npm run audit:frame-sizes`
   - `npm run audit:motion`
   - `npm run audit:escape`
   - `npm run audit:quality`
   - Medir runtime com `npm run measure:hero <hero>` quando o problema for tamanho percebido.
   - Chefe: a escala vem de `BOSS_SOURCE_BODY_HEIGHTS[animKey]` (via `_syncRaddyF2Scale`/`_syncVineriaScale`
     no preUpdate). Confirme variacao entre formas pela ALTURA-TOTAL, nao so o solido; alguns chefes so
     dao pra medir no playtest (anim depende do preUpdate vivo).

## Criterios de aceite

- Nenhum frame vivo importante toca a borda do canvas.
- `bottomGap` e pe visual estaveis dentro do estado.
- `centerX` nao salta sem intencao.
- `scaleX` e `scaleY` ficam uniformes, salvo excecao documentada.
- Idle tem micro movimento, sem andar para tras.
- Run/dash tem leitura de deslocamento, sem parecer dash reciclado em loop.
- Ataque tem startup, contato claro, recovery e evento de som/hitbox no frame correto.
- O FIXLOG registra problema, causa raiz, correcao e verificacao.
