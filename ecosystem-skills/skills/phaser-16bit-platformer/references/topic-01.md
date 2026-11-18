# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## Tunable reference (start here, then playtest)

Assuming internal resolution ~384×216, tile = 16px, gravity downward:

| Tunable | Value | Note |
|---------|-------|------|
| Run speed | 100–120 px/s | brisk but controllable |
| Ground accel | ~1200 px/s² | snappy start |
| Decel | ~1500 px/s² | crisp stop, no ice |
| Air accel | ~700 px/s² | reduced air control |
| Jump velocity | −230 to −260 | ~3–3.5 tiles high |
| Rising gravity | ~700 | |
| Falling gravity | ~1100 | fall faster than rise |
| Jump-cut multiplier | 0.4–0.5 | variable height |
| Coyote time | 80–100 ms | forgive late jumps |
| Jump buffer | 90–120 ms | forgive early presses |
| Max fall speed | ~320 px/s | terminal velocity |

These are *starting points*. The difference between mushy and magic is ±10% tuning while holding the controller.

---

