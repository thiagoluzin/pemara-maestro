# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 📐 16-BIT DOCTRINE (this is a discipline, not nostalgia)

16-bit (SNES / Mega Drive era) is a set of hard constraints that produce a coherent look and feel. Honor them on purpose.

| Constraint | Rule of thumb | Phaser implementation |
|------------|---------------|------------------------|
| **Internal resolution** | Low, fixed (e.g. 320×180, 384×216, 256×224). Render small, scale up by integers. | `scale: { mode: Scale.FIT, width: 384, height: 216, zoom: ... }`, integer-scale the canvas |
| **No anti-aliasing** | Pixels must stay sharp | `pixelArt: true` (sets `roundPixels` + nearest-neighbor) |
| **Sub-pixel motion, pixel-perfect render** | Move in floats, *render* on whole pixels | keep float positions in body, `roundPixels: true` for display |
| **Limited palette** | Cohesive, era-accurate colors | enforce a palette; tint sprites, don't recolor ad hoc |
| **Tile grid** | World built on 8 or 16 px tiles | Tiled maps, tile size 16 |
| **Parallax layers** | 2–4 scroll layers for depth | `tileSprite` / camera `scrollFactor` |
| **Chunky animation** | Fewer frames, strong key poses | sprite atlas + tight frame timing |
| **Locked framerate** | 60fps target, deterministic feel | fixed step / clamped delta |

Pick a single internal resolution at project start and **never** mix scales. Everything authored to that grid.

---

