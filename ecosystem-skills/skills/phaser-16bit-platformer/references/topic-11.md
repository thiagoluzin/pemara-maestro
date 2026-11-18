# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 10. 60fps checklist (paste into PR description)

- [ ] Single texture atlas per logical group (min draw calls)
- [ ] No `new` / object literals created inside `update()` loops
- [ ] All transient entities pooled (`Group maxSize`), none `destroy()`-ed in hot path
- [ ] Off-screen entities culled / AI paused beyond camera margin
- [ ] Delta clamped; physics deterministic (`fixedStep`)
- [ ] Camera `roundPixels` on; integer zoom; no fractional scale
- [ ] `game.loop.actualFps` holds ≥ 60 with worst-case entity count (measured)
- [ ] Profiled the real hotspot (Chrome Performance) before any micro-opt

---


