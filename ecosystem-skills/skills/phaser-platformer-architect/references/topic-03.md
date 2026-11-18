# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 🎮 PHASER MASTERY (verify version first — patterns below are Phaser 3)

### Boot config that doesn't betray your pixels
```js
const config = {
  type: Phaser.AUTO,
  pixelArt: true,            // nearest-neighbour, no blur
  roundPixels: true,         // snap draw positions to whole pixels
  backgroundColor: '#1a1c2c',
  scale: {
    mode: Phaser.Scale.FIT,  // letterbox, preserve aspect
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: 384, height: 216, // INTERNAL resolution (16:9-ish 16-bit canvas)
  },
  physics: {
    default: 'arcade',
    arcade: { gravity: { y: 0 }, fps: 60, fixedStep: true, debug: false },
    // fixedStep:true → deterministic physics independent of render fps
  },
  render: { antialias: false, roundPixels: true },
  scene: [BootScene, PreloadScene, GameScene, UIScene],
};
```

### Physics: Arcade vs Matter — choose deliberately
| | **Arcade** | **Matter** |
|--|-----------|-----------|
| Best for | Platformers, run-and-gun, most 16-bit games | Physics puzzles, ragdolls, slopes-heavy |
| Cost | Cheap, AABB only | Heavier, full rigid body |
| Default | **Yes — start here** | Only if you genuinely need real physics |

For slopes in Arcade, use a tile-based slope solution or sensor tricks; don't reach for Matter just for ramps unless the design is physics-driven.

### Tilemap pipeline (Tiled → Phaser)
```js
const map = this.make.tilemap({ key: 'level1' });               // Tiled JSON
const tiles = map.addTilesetImage('tileset-name', 'tiles-img'); // names MUST match Tiled
const ground = map.createLayer('Ground', tiles, 0, 0);
ground.setCollisionByProperty({ collides: true });              // set in Tiled per-tile
this.physics.add.collider(this.player.sprite, ground);
// One-way platforms: tile property + checkCollision.down only, or process callback
```
Author collision/oneway/hazard as **custom properties in Tiled**, never hardcode tile IDs in source.

### Camera that doesn't smear
```js
const cam = this.cameras.main;
cam.startFollow(this.player.sprite, true, 0.12, 0.12); // lerp = smooth but...
cam.setRoundPixels(true);                              // ...keep it pixel-snapped
cam.setBounds(0, 0, map.widthInPixels, map.heightInPixels);
// Deadzone so small movements don't jiggle the whole screen:
cam.setDeadzone(60, 40);
```

### Input — abstract it on day one
Never scatter `cursors.left.isDown` across the codebase. Build one input layer that merges keyboard + gamepad + buffered actions, expose intent (`moveX`, `jumpPressed`, `jumpHeld`), and read *that* everywhere.

---

