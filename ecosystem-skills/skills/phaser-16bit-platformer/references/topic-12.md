# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## Gotchas that bite everyone

1. **Tileset name mismatch** — `addTilesetImage('A','B')`: first arg must equal the tileset name *inside Tiled*, second is the loaded image key. Mismatch = invisible map.
2. **Body size vs frame** — default body = full frame → floaty/unfair collisions. Always `setSize/setOffset`.
3. **Sub-pixel camera smear** — following a float position without `setRoundPixels(true)` shimmers pixels.
4. **Mobile audio** — Web Audio is locked until first user gesture; unlock on first tap.
5. **`blocked` vs `touching`** — `body.blocked.down` is world/tile contact; `touching.down` is object-object. Check both for "grounded".
6. **One-way fall-through** — without a process callback, players collide from below too. Use the velocity/position check.
