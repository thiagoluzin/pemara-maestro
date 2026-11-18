# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 2. Framerate-independent delta (clamp the spike)

```js
update(time, delta) {
  // tab refocus / GC can hand you a 500ms delta → clamp it
  const dt = Math.min(delta, 1000 / 30) / 1000; // seconds, capped at ~33ms
  this.input.update();            // refresh buffered input first
  this.player.update(dt, this.input.intent);
}
```

Never feed raw `delta` into hand-rolled motion. A single spike with raw delta launches entities through walls.

---

