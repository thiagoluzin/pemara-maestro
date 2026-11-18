# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 3. Input abstraction (keyboard + gamepad + buffer)

```js
export class InputLayer {
  constructor(scene) {
    this.scene = scene;
    this.k = scene.input.keyboard.addKeys('LEFT,RIGHT,UP,Z,X,SPACE');
    this.intent = { moveX: 0, jumpPressed: false, jumpHeld: false, attackPressed: false };
    this._prevJump = false;
  }
  update() {
    const k = this.k;
    const pad = this.scene.input.gamepad?.getPad(0);
    const padX = pad ? pad.axes[0].getValue() : 0;
    const left  = k.LEFT.isDown  || padX < -0.3 || pad?.left;
    const right = k.RIGHT.isDown || padX >  0.3 || pad?.right;
    const jump  = k.Z.isDown || k.SPACE.isDown || k.UP.isDown || pad?.A;

    this.intent.moveX = (right ? 1 : 0) - (left ? 1 : 0);
    this.intent.jumpHeld = jump;
    this.intent.jumpPressed = jump && !this._prevJump; // edge-detect = "pressed this frame"
    this.intent.attackPressed = (k.X.isDown || pad?.X);
    this._prevJump = jump;
  }
}
```

Read `intent.*` everywhere. Never sprinkle `cursors.left.isDown` across game logic.

---

