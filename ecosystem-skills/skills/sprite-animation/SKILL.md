---
name: sprite-animation
description: >
  Animação de sprites em Phaser e os princípios de animação aplicados ao 2D — criar animações de
  atlas/sheet, máquina de estados de animação com retorno garantido, eventos animationcomplete,
  timing independente de framerate, easing/tweens, squash & stretch, antecipação, follow-through
  e smear frames. Inclui fluxo Unity-like de AnimationClip para Phaser com contrato de frame,
  pivo/origin, eventos por frame, startup/active/recovery, hitbox/som/cancel e validacao.
  Use ao animar personagens/inimigos ou montar/refatorar a maquina de animacao.
---

# Skill: Animação de Sprites (Phaser + princípios 2D)

Poucas poses fortes > muitos frames moles. Timing independe de fps. Toda animação de ação retorna sozinha.

## Contrato Unity-like para Phaser
Trate cada animacao Phaser como se fosse um `AnimationClip` do Unity: ela precisa ter contrato antes de virar codigo.

```js
const clip = {
  key: 'oren_run',
  texture: 'oren_run_sheet',
  frameWidth: 256,
  frameHeight: 256,
  frameRate: 14,
  repeat: -1,
  origin: { x: 0.5, y: 1 },
  scaleMode: 'uniform',
  phases: { startup: [0, 1], active: [2, 5], recovery: [6, 7] },
  events: [
    { frame: 1, type: 'sfx', key: 'step_light' },
    { frame: 3, type: 'dust' }
  ]
};
```

Obrigatorio antes de mexer em codigo:
- medir largura/altura da celula, bbox, bottomGap, centerX, topY e bodyH por frame;
- manter `origin` fixo no pe (`0.5, 1`) para personagens;
- separar hitbox/hurtbox do visual; frame bonito nao define colisao sozinho;
- declarar eventos de som/hitbox/hitstop por frame, nao espalhar `delayedCall` solto;
- validar `startup/active/recovery` em frames e em ms.

## Criar animações de um atlas/sheet
```js
this.anims.create({ key:'idle', frames:this.anims.generateFrameNames('hero',{prefix:'idle_',start:0,end:3,zeroPad:2}), frameRate:6, repeat:-1 });
this.anims.create({ key:'run',  frames:this.anims.generateFrameNames('hero',{prefix:'run_', start:0,end:7,zeroPad:2}), frameRate:12, repeat:-1 });
this.anims.create({ key:'jump', frames:this.anims.generateFrameNames('hero',{prefix:'jump_',start:0,end:1,zeroPad:2}), frameRate:8, repeat:0 });
this.anims.create({ key:'attack',frames:this.anims.generateFrameNames('hero',{prefix:'atk_', start:0,end:4,zeroPad:2}), frameRate:18, repeat:0 });
```

## Máquina de estados (legível, com retorno garantido)
```js
class AnimFSM {
  constructor(sprite){ this.s=sprite; this.locked=false; }
  play(key, lock=false){
    if(this.locked) return;
    if(this.s.anims.currentAnim?.key!==key) this.s.play(key, true);
    if(lock){                                  // anim de ação trava até terminar
      this.locked=true;
      this.s.once('animationcomplete', ()=>{ this.locked=false; });   // retorno garantido
    }
  }
  update(state){                               // state: {onGround, vx, vy}
    if(this.locked) return;
    if(!state.onGround) this.play(state.vy<0?'jump':'fall');
    else this.play(Math.abs(state.vx)>5?'run':'idle');
  }
}
// ataque: fsm.play('attack', true)  -> volta sozinho ao idle/run quando acabar
```

## Eventos por frame
Use eventos como o Unity usaria `Animation Events`: som, poeira, hitbox, cancel e hitstop ficam presos ao frame de animacao.

```js
const fired = new Set();
sprite.on('animationupdate', (_anim, frame) => {
  const key = `${sprite.anims.currentAnim.key}:${frame.index}`;
  if (fired.has(key)) return;
  fired.add(key);
  if (frame.index === 2) spawnDust(sprite.x, sprite.y);
  if (frame.index === 4) enableHitbox('attack_main');
});
sprite.on('animationcomplete', () => fired.clear());
```

Para ataque: 1-3 frames de startup, 2-5 ativos, recovery cancelavel onde o design permitir. Para dash/run: movimento fisico em ms, animacao so ilustra o estado.

## Timing independente de framerate
- Sprite anim: use `frameRate` (Phaser controla por tempo, não por update).
- Tween: use `duration` em ms (independe de fps).
- Nunca avance frame "1 por `update()`".

## Squash & stretch (impacto/pulo)
```js
// aterrissagem: achata e volta
scene.tweens.add({ targets:sprite, scaleX:1.25, scaleY:0.75, yoyo:true, duration:90, ease:'Quad.out' });
// pulo: estica
scene.tweens.add({ targets:sprite, scaleX:0.85, scaleY:1.18, yoyo:true, duration:110 });
```
Preserve volume (se estica num eixo, comprime no outro). Reset a escala ao trocar de estado pra não acumular.

## Antecipação & follow-through
- **Antecipação**: 1–2 frames de agachar antes do pulo (lê melhor).
- **Follow-through**: capa/cabelo continuam 2–3 frames após o corpo parar (tween com `ease:'Sine.out'`).

## Smear frame (movimento rápido)
Um frame "borrado/esticado" no meio de um movimento veloz (ataque/dash) vende velocidade — clássico de animação 2D.

## Easing útil (tweens)
`Quad.out`/`Cubic.out` pra desacelerar natural; `Back.out` pra "pop" (UI, coleta); `Bounce.out` pra quicar; **linear** quase nunca (parece robótico).

## Anti-padrões
| ❌ Não | ✅ Faça |
|--------|---------|
| Troca de anim piscando | só trocar se `currentAnim.key` diferente |
| Anim de ataque presa | `animationcomplete` destrava/retorna |
| Escala acumulando (squash sobre squash) | resetar escala ao trocar estado |
| Linear em tudo | easing (ease in/out) |
| Frame por `update()` | `frameRate`/`duration` |
| Pixel art esticado borrado | manter `NEAREST`, escala inteira |
