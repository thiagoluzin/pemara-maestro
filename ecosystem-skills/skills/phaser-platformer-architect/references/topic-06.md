# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 🏗️ COMPLEX-GAME ARCHITECTURE (this scales past one screen)

| Concern | Approach |
|---------|----------|
| **Scenes** | `Boot → Preload → Game → UI(overlay) → Pause`. UI runs as a parallel scene, not baked into gameplay. |
| **Entities** | Thin sprite + behavior classes (Player, Enemy types, Projectile). Avoid god-objects. |
| **State** | Explicit state machines for player (idle/run/jump/fall/dash/hurt) and enemies. No `if`-soup of booleans. |
| **Data-driven** | Enemy stats, level lists, dialogue, tunables in JSON. Designers edit data, not code. |
| **Pooling** | `Phaser.GameObjects.Group` with `maxSize` for bullets/particles/pickups. `get()`/`killAndHide()`, never destroy in hot path. |
| **Events** | `scene.events` / a global `EventEmitter` for decoupled SFX, score, achievements. |
| **Save** | Versioned JSON (`{v:1,...}`) to `localStorage`/file with migration on load. Never trust old saves blindly. |
| **Levels** | Tiled `.tmj`, object layer for spawns/triggers/exits parsed by type. New level = new data file, zero code. |
| **Audio** | Web Audio via Phaser sound; preload sprites; duck music on SFX; mind mobile autoplay unlock. |

### Object pool (correct pattern)
```js
this.bullets = this.physics.add.group({ classType: Bullet, maxSize: 64, runChildUpdate: true });
fire(x, y, vx) {
  const b = this.bullets.get(x, y, 'bullet');   // reuses dead instance
  if (!b) return;                                // pool exhausted → drop, don't grow unbounded
  b.enableBody(true, x, y, true, true);
  b.body.setVelocityX(vx);
}
// on expire/hit: b.disableBody(true, true);  // back to pool, no GC
```

---

