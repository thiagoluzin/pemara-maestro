# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 🕹️ GAME-FEEL BIBLE — the player controller that earns the 8 seconds

A reference Arcade controller wiring the non-negotiables. Tune the numbers to your resolution; these assume ~384×216 and tile=16.

```js
class PlayerController {
  constructor(scene, x, y) {
    this.scene = scene;
    const s = scene.physics.add.sprite(x, y, 'hero', 'idle_0');
    s.setCollideWorldBounds(true);
    s.body.setSize(10, 14).setOffset(3, 2); // tight hitbox, not the full sprite frame
    this.s = s;

    // Tunables — DATA, not magic numbers buried in logic
    this.RUN_SPEED   = 110;
    this.ACCEL       = 1200;   // px/s^2 ground accel  → snappy but not teleporty
    this.DECEL       = 1500;   // stopping friction
    this.AIR_ACCEL   = 700;    // less control in air, but not zero
    this.JUMP_VEL    = -240;
    this.GRAV_UP     = 700;    // rising gravity
    this.GRAV_DOWN   = 1100;   // falling gravity (asymmetry = good feel)
    this.JUMP_CUT    = 0.45;   // velocity multiplier when jump released early
    this.COYOTE_MS   = 90;     // grace after leaving ground
    this.BUFFER_MS   = 100;    // grace pressing jump before landing
    this.MAX_FALL    = 320;

    this._coyote = 0;
    this._buffer = 0;
  }

  update(dt, input) {                // dt in seconds (clamped upstream)
    const b = this.s.body;
    const onGround = b.blocked.down || b.touching.down;

    // timers
    if (onGround) this._coyote = this.COYOTE_MS; else this._coyote -= dt * 1000;
    if (input.jumpPressed) this._buffer = this.BUFFER_MS; else this._buffer -= dt * 1000;

    // horizontal: accelerate toward target, decelerate to stop
    const target = input.moveX * this.RUN_SPEED;
    const accel = (input.moveX !== 0)
      ? (onGround ? this.ACCEL : this.AIR_ACCEL)
      : (onGround ? this.DECEL : this.AIR_ACCEL * 0.5);
    b.velocity.x = approach(b.velocity.x, target, accel * dt);

    // jump: fire if buffered AND within coyote window
    if (this._buffer > 0 && this._coyote > 0) {
      b.velocity.y = this.JUMP_VEL;
      this._buffer = 0; this._coyote = 0;
      this.scene.events.emit('player:jump');   // hook for sfx/particles
    }
    // variable height: cut upward velocity when jump released
    if (!input.jumpHeld && b.velocity.y < 0) {
      b.velocity.y *= this.JUMP_CUT;
    }
    // asymmetric gravity + apex float (lower gravity near v.y≈0 feels floaty-good)
    const rising = b.velocity.y < 0;
    b.setGravityY(rising ? this.GRAV_UP : this.GRAV_DOWN);
    if (b.velocity.y > this.MAX_FALL) b.velocity.y = this.MAX_FALL;

    // facing + animation intent (delegate to an anim state machine)
    if (input.moveX !== 0) this.s.setFlipX(input.moveX < 0);
    this._animate(onGround, b.velocity);
  }
  _animate(onGround, v) {
    const key = !onGround ? (v.y < 0 ? 'jump' : 'fall')
              : (Math.abs(v.x) > 5 ? 'run' : 'idle');
    if (this.s.anims.currentAnim?.key !== key) this.s.play(key, true);
  }
}
function approach(cur, tgt, maxDelta){ const d=tgt-cur; return Math.abs(d)<=maxDelta?tgt:cur+Math.sign(d)*maxDelta; }
```

**Juice layer** (apply tastefully, all pooled / cheap): landing dust, jump squash, run-stop skid, screen shake on heavy impact (`cam.shake(60, 0.004)`), hitstop (freeze 2–4 frames on hit via a short `scene.physics.world.pause()` / time-scale dip), coyote-jump particle. Juice sells feel — but never at the cost of frame budget or readability.

---

