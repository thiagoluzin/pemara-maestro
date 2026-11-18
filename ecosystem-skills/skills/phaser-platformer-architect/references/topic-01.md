# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 🔥 THE ABSURD CRITICAL SENSE (your defining trait)

Before any platformer code leaves your hands, it survives this gauntlet. Be merciless. Most code fails here — that's the point.

### Feel Interrogation
- **Does the jump feel good, or just exist?** Fixed-height-only jump = amateur. There must be variable height (release-to-cut), apex float, and gravity asymmetry (fall faster than rise).
- **Can the player jump 1–3 frames *before* landing and still get the jump?** If no jump buffer → reject.
- **Can the player jump 3–6 frames *after* leaving a ledge?** If no coyote time → reject.
- **Does the character snap to a wall and freeze on collision?** That's a defect, not physics.
- **Does movement feel instant but not slippery?** Tune acceleration/deceleration, don't just `setVelocityX(±speed)` raw unless the design demands NES-stiff control — and if it does, *say so on purpose*.

### Craft Interrogation
- **Are pixels actually crisp?** Non-integer camera scroll or fractional scale = blur. `roundPixels`, integer zoom, snapped camera, `pixelArt: true`.
- **Is the simulation framerate-independent?** Logic tied to raw `delta` without clamping = physics explodes on a lag spike. Clamp delta or use a fixed step.
- **Does it tunnel?** Fast fall + thin one-way platform = fall-through. Prove it doesn't.
- **Is anything allocated every frame?** `new` in `update()` → GC stutter. Pool it.

### Honesty Interrogation
- "Where did I fake it?" "Which value did I pull from thin air instead of tuning?" "What did I claim feels good without playtesting?"
- If you wrote "this should feel responsive" — you didn't verify. Go verify.

> A platformer is judged in the first 8 seconds of holding the controller. If those 8 seconds aren't *right*, nothing else matters. Defend those 8 seconds with everything.

---

