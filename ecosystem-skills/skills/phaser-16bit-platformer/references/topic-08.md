# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 7. Pooled projectiles / particles

```js
this.bullets = this.physics.add.group({ classType: Bullet, maxSize: 64, runChildUpdate: true });

spawnBullet(x, y, vx) {
  const b = this.bullets.get(x, y, 'fx', 'bullet_0');
  if (!b) return;                 // pool full → drop (never grow unbounded in hot path)
  b.enableBody(true, x, y, true, true);
  b.body.setAllowGravity(false).setVelocityX(vx);
}

class Bullet extends Phaser.Physics.Arcade.Sprite {
  update() { if (this.x < this.scene.cameras.main.scrollX - 16) this.disableBody(true, true); }
}
```

`disableBody(true,true)` returns it to the pool — **no `destroy()` in gameplay**, so no GC stutter.

---

