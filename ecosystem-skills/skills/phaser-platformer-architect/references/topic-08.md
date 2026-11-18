# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 🚫 PHASER-PLATFORMER ANTI-PATTERNS

| ❌ Don't | ✅ Do |
|----------|-------|
| `setVelocityX(speed)` with no accel and call it "tight" | Acceleration curve (or deliberate stiff control, stated) |
| Fixed-height jump only | Variable height + coyote + buffer |
| Symmetric gravity | Fall faster than you rise |
| Hitbox = full sprite frame | Tight body via `setSize/Offset` |
| Hardcode tile IDs for collision | Tiled custom properties |
| Fractional camera zoom / scroll | Integer zoom + `roundPixels` + snapped camera |
| `create()` enemies/bullets per spawn | Pool with `Group(maxSize)` |
| Logic on raw `delta` | Clamp delta / fixed step |
| One mega-scene | Boot/Preload/Game/UI split |
| Matter physics "just in case" | Arcade unless physics is the gameplay |

---

