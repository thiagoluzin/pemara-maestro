# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 👊 2.5D BEAT 'EM UP DOCTRINE (Golden Rules for Brawlers)
When building games with a 2.5D perspective (like Final Fight, Streets of Rage, or Sprunki Beat Up):

1. **NEVER use Arcade Physics Colliders for character bodies (Player vs Enemy).** In a 2.5D perspective, the Y-axis represents Z-depth. A physical Arcade collision resolution will push entities along the Y-axis, making them visually "fly" into the sky. Use pure mathematical distance checks (cylinder collision) inside `update()` instead of `physics.add.collider`.
2. **Strict Visual Floor Mapping.** The walkable area constraints (e.g. `floorTopY`, `floorBottomY`) MUST accurately map to the visual street/ground drawn in the background layers. Never use arbitrary percentages (like `h * 0.65`) without visually confirming it aligns with the background. For a narrow street at the bottom, `0.85` or `0.9` is required. If players hover above the road, you failed the mapping.
3. **Cinematic Walk-in Transitions.** Cutscenes (like Boss entrances) must not lazily teleport the player into the scene standing still. The player must physically walk into the scene from out-of-bounds (e.g. `cam.scrollX - 100` with velocity applied) while the screen fades in, only returning control when they reach the fighting area.

---

