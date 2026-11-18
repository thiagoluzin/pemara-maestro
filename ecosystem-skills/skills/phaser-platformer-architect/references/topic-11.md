# Referência de phaser-platformer-architect

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## ✨ MODERN PIXEL ART / HD REMIX (16-bit → HD-2D)

Você opera em dois modos — escolha de propósito e **nunca misture os dois sem querer** (é a causa nº1 de pixel art "sujo"):

| Modo | Quando | Regra de ouro |
|------|--------|----------------|
| **16-bit puro** | estética retro fiel | resolução interna baixa, escala inteira, sem luz dinâmica |
| **HD Remix / HD-2D** | pixel art "elevado" (estilo Octopath/Sea of Stars) | sprite pixel nítido + luz/FX em **alta resolução** por cima |

### Princípio HD-2D
Sprite/tilemap continuam **pixel-perfect**; o que vem por cima (luz, bloom, partículas, profundidade) roda em **resolução nativa alta**. O charme é o contraste: pixel chunky + iluminação cinematográfica. **Nunca** borre o sprite pra "modernizar".

### Técnicas (Phaser — confirme a versão; FX pipelines mudaram no 3.6+/v4)
- **Iluminação dinâmica 2D**: `this.lights.enable()` + `sprite.setPipeline('Light2D')` com **normal maps** por sprite (canal de normal no atlas) → luz reage ao relevo do pixel.
- **Post-FX cinematográfico**: bloom/glow/vignette via FX pipeline (`sprite.postFX.addBloom(...)` / `camera.postFX`) — confirme API na sua versão antes de usar.
- **Profundidade/HD-2D**: camadas de parallax com blur de profundidade (tilt-shift) no fundo, sprite nítido no plano de ação.
- **Hi-res FX sobre pixel base**: partículas, fumaça, luz volumétrica em alta resolução por cima de sprites low-res.
- **Palette cycling** (truque clássico 16-bit que ainda encanta): animar cores da paleta (água, lava, brilho) sem novos frames.
- **Sub-pixel/smear**: movimento em float, render pixel-snap; smear frames em ação rápida (ver skill `sprite-animation`).

### Régua de qualidade (pixel art não pode "vazar")
- Sprite nítido: `pixelArt:true`, `roundPixels`, escala/zoom **inteiros**, câmera snap.
- Luz/bloom em alta resolução **não** devem pixelizar junto com o sprite — são camadas separadas.
- Mantenha o frame budget de 60fps **mesmo com luz/FX** (FX custa; meça).

> Receitas concretas (lighting, normal map, bloom, palette cycling, HD-2D layering) → skill `modern-pixel-art-hd`.

