# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 5. Tiled tilemap + solid + one-way platforms

```js
// Preload: this.load.tilemapTiledJSON('level1', 'levels/level1.tmj');
const map = this.make.tilemap({ key: 'level1' });
const tiles = map.addTilesetImage('world-tiles', 'tiles');   // name = Tiled tileset name
const solid = map.createLayer('Solid', tiles, 0, 0);
solid.setCollisionByProperty({ collides: true });            // set 'collides' in Tiled
this.physics.add.collider(player.s, solid);

// One-way platforms (collide only when falling onto them):
const oneway = map.createLayer('OneWay', tiles, 0, 0);
oneway.setCollisionByProperty({ oneway: true });
this.physics.add.collider(player.s, oneway, null, (sprite, tile) => {
  // process callback: only collide if moving down and feet above the tile top
  return sprite.body.velocity.y >= 0 && (sprite.body.bottom <= tile.pixelY + 4);
});

// Object layer → spawns/triggers, parsed by type, zero hardcoding:
map.getObjectLayer('Objects').objects.forEach(o => {
  switch (o.type) {
    case 'player_spawn': player.s.setPosition(o.x, o.y); break;
    case 'enemy':        this.spawnEnemy(o.name, o.x, o.y); break;
    case 'exit':         this.makeExit(o.x, o.y, o.properties); break;
  }
});
```

---

