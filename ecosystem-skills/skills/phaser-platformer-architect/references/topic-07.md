# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## ⚡ 60FPS BUDGET ENFORCEMENT

- **One texture atlas** per logical group → minimize draw calls/texture swaps.
- **Zero `new` in `update()`** — pool everything transient. Reuse vectors.
- **Cull** off-screen entities; pause AI/anim outside camera + margin.
- **Clamp delta**: `dt = Math.min(delta/1000, 1/30)` so a tab-refocus spike can't launch the player into orbit. (With Arcade `fixedStep` the physics is already deterministic; still clamp your own logic.)
- **Profile, don't guess**: Chrome Performance tab, Phaser's `game.loop.actualFps`. Find the real hotspot before optimizing.
- **Static where possible**: backgrounds as `tileSprite` or static layers, not per-tile sprites.

---

