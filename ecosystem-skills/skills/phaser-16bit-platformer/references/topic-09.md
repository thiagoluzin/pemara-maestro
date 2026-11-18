# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 8. Juice (cheap, pooled, optional but transformative)

```js
// Landing dust
scene.add.particles(0, 0, 'fx', { frame: 'dust', lifespan: 250, speed: {min:10,max:40},
  quantity: 6, scale: {start:1,end:0}, emitting: false }).explode(6, x, y);
// Screen shake on heavy impact
cam.shake(60, 0.004);
// Hitstop: brief freeze sells weight
scene.time.delayedCall(0, () => { scene.physics.world.pause();
  scene.time.delayedCall(60, () => scene.physics.world.resume()); });
// Jump squash
scene.tweens.add({ targets: sprite, scaleX: 0.8, scaleY: 1.2, yoyo: true, duration: 80 });
```

Rule: juice must be pooled/cheap and never block input. Feel > spectacle.

---

