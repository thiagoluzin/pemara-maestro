# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 4. Full game-feel player controller

See the agent file's `PlayerController` for the annotated reference (coyote + buffer + variable height + asymmetric gravity + accel curves + animation intent). Key invariants this skill enforces:

- **Edge-detected jump** (`jumpPressed`), not level-triggered.
- **Coyote** counts down from a timer reset only when grounded.
- **Buffer** counts down from a timer reset only on press.
- Jump fires when `buffer > 0 && coyote > 0`, then **both reset to 0** (prevents double-fire).
- **Release-to-cut**: `if (!jumpHeld && vy < 0) vy *= JUMP_CUT;`
- **Tight hitbox** decoupled from the visual frame via `body.setSize(...).setOffset(...)`.

---

