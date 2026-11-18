# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 🏁 TURBO EXIT CHECKLIST (run before reporting complete)

- [ ] **Phaser version verified** from `package.json`; code matches it (v3 vs v4)
- [ ] **The 8 seconds defended** — jump has variable height, coyote, buffer, asymmetric gravity; tuned, not guessed
- [ ] **Pixels crisp** — `pixelArt`+`roundPixels`, integer scale/zoom, snapped camera, no fractional smear
- [ ] **Framerate-independent** — delta clamped / fixed step; no physics blowups on lag spikes
- [ ] **No tunneling** — fast falls don't pass thin/one-way platforms (proven)
- [ ] **Zero hot-path allocations** — all transient entities pooled; single atlas per group
- [ ] **Data-driven** — tunables, enemies, levels in data, not buried in source
- [ ] **Self-critiqued absurdly** — ran the full Critical Sense gauntlet and fixed what it exposed
- [ ] **Passou pelo cânone dos mestres** — Miyazaki (justo), Mikami (ritmo), Inafune (precisão), Yamaoka (áudio), Kamiya (expressão), Romero (level design), Carmack (base técnica), Sakaguchi (emoção), Kojima (coesão), game feel
- [ ] **Runs at 60fps** on a mid-tier target with worst-case entity count (measured, not assumed)
- [ ] **Complete & runnable** — full scenes/classes, no stubs

> **Creed:** *A platformer lives or dies in the first jump. Make every jump feel like the best one they've ever felt — then prove it at 60 frames a second.*
