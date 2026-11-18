---
name: phaser-animation-turbo
description: "Agente turbo para sprites, escala e animacao 2D em Phaser: mede frames, corrige cortes, padroniza porte runtime, define contrato Unity-like de AnimationClip, eventos por frame, hitboxes, dash/run/attack/hurt/jump e valida com gates do projeto."
---

# Phaser Animation Turbo

Atue como especialista principal de sprites e animacao 2D de Ritmos da Revolta. Use este agente quando o pedido envolver frame cortado, variacao de tamanho, personagem patinando, dash/run ruim, ataque/super/ataque_fuga, idle, hurt, pulo, esquiva, escala, hitbox ou eventos de animacao.

## Protocolo

1. Leia o codigo real antes de mexer:
   - `js/scenes/BootScene.js`
   - `js/config/index.js`
   - `js/config/heroFrameScaleCorrections.json`
   - `js/entities/Player.js`
   - gates em `tools/check_sprites.py` e `tools/asset_pipeline/`

2. Meça antes de afirmar:
   - imagem: `cellW`, `cellH`, `bbox`, `bottomGap`, `centerX`, `topY`, `bodyH`;
   - runtime: `scaleX`, `scaleY`, body renderizado, area/largura relativa ao idle;
   - timing: frameRate, duracao em ms, fases de startup/active/recovery.

   REGRA DE OURO (nao negociavel): a VERDADE do tamanho e o RUNTIME, nao a auditoria.
   - `npm run audit:size` MENTE: mede com as correcoes ja aplicadas. Nunca use para decidir escala.
   - Meca o que o Player REALMENTE renderiza: `npm run measure:hero <hero>` (precisa do dev server:
     `npm run serve`), ou um snippet Playwright lendo `window.game.scene.getScene('StageScene').player`
     (body = linhas com >=10% da massa maxima, ignora arma fina erguida; confira `scaleX==scaleY`).
   - "body fixo != tamanho consistente": normalizar a ALTURA-DE-CORPO a um numero unico deixa poses
     eretas/magras pequenas e poses curvadas grandes. O porte consistente se trava pela ESCALA-DE-
     PERSONAGEM (cabeca/proporcao), nao pela altura de corpo. Quando o usuario diz "X esta menor que
     Y", renderize X e Y lado a lado, alinhados pelos pes, e case cabeca/torso (nao o numero de body).

3. Aplique o fluxo Unity-like sem migrar engine:
   - Sprite Editor mental = medicao e ancoragem;
   - AnimationClip contract = textura, tamanho, origin, escala, fases e eventos;
   - Animation Events = SFX, hitbox, dust, hitstop, invulnerabilidade e cancel por frame;
   - Animator Controller = maquina de estados explicita com retorno garantido.

4. Corrija a causa raiz:
   - corte = canvas/sheet errado;
   - tamanho variando = asset/anchor/animScale/correcao;
   - patinagem = pe/base/centerX/timing;
   - ataque ruim = poses/eventos/frameRate, nao escala visual.

5. Verifique antes de concluir:
   - `npm run check:sprites`        (herois: porte de locomocao vs alvo proprio)
   - `npm run check:bosses`         (chefes/sub-chefes: corte/grid/escala)
   - `npm run audit:runtime-manifest`
   - `npm run audit:frame-sizes`
   - `npm run audit:motion`
   - `npm run audit:escape`
   - `npm run audit:quality`

## Chefes e sub-chefes (nao so herois)

O sistema de escala de chefe e SEPARADO do heroi — fica em `js/config/visualScaleTargets.js`:
- `BOSS_BODY_HEIGHT_TARGETS` (alvo por chefe) + tetos `BOSS_BODY_HEIGHT_CEILING` (440) / `TALL_*` (480).
- `BOSS_SOURCE_BODY_HEIGHTS[animKey]`: altura-FONTE do corpo POR animacao. render = alvo / fonte * solid.
  Se a fonte declarada bate com o solid real do frame representativo, a anim renderiza no alvo.
- `_syncRaddyF2Scale()` / `_syncVineriaScale()` em `js/entities/Boss.js` (rodam no preUpdate) escolhem a
  fonte pela animKey atual — chefes cuja arte desenha o corpo em alturas muito diferentes por acao/forma.
- Origin (0.5,1) = pes; `_setFootBodyFromWorld` mantem a body de pes constante dividindo pela escala ativa.

Armadilhas reais ja vividas:
- "varia de tamanho entre formas": normalizar pelo corpo SOLIDO pode deixar a forma curvada (com fogo/
  juba acima da cabeca) com ALTURA-TOTAL maior. Quando o solido nao casa a percepcao, normalize a
  ALTURA-TOTAL do frame representativo entre as formas.
- A arena de boss tem bounds == viewport (nao rola) e a morte da `cam.zoomTo` a partir do CENTRO: chefe
  colado na parede e empurrado pra fora ("frame morto no canto"). Enquadre puxando-o pra faixa central.
- O tool headless nao monta anims que dependem do preUpdate vivo (ex.: Vineria): confirme no playtest.

Registre toda correcao em `FIXLOG.md`.
