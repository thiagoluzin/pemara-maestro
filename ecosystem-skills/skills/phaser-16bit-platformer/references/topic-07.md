# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 6. Camera + parallax

```js
// Parallax background layers (scrollFactor < 1 = further away)
this.add.tileSprite(0, 0, 384, 216, 'bg_far').setOrigin(0).setScrollFactor(0.2);
this.add.tileSprite(0, 0, 384, 216, 'bg_near').setOrigin(0).setScrollFactor(0.5);

const cam = this.cameras.main;
cam.setBounds(0, 0, map.widthInPixels, map.heightInPixels);
cam.startFollow(player.s, true, 0.12, 0.12);
cam.setDeadzone(50, 30);
cam.setRoundPixels(true);   // <-- critical: prevents sub-pixel smear while following
```

---

