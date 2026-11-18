# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 1. Pixel-perfect boot config

```js
export const GameConfig = {
  type: Phaser.AUTO,
  pixelArt: true,
  roundPixels: true,
  backgroundColor: '#1a1c2c',
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: 384,
    height: 216,
  },
  physics: {
    default: 'arcade',
    arcade: { gravity: { y: 0 }, fixedStep: true, fps: 60, debug: false },
  },
  render: { antialias: false, roundPixels: true },
};
```

**Why:** `pixelArt` + `roundPixels` kill blur; `Scale.FIT` letterboxes while preserving the retro aspect; Arcade `fixedStep:true` makes physics deterministic regardless of render fps.

---

