---
name: modern-pixel-art-hd
description: >
  Pixel art moderno / HD-2D ("HD remix", estilo Octopath/Sea of Stars) em Phaser — sprite pixel
  nítido elevado por iluminação dinâmica 2D com normal maps, post-FX (bloom/glow/vignette),
  camadas de profundidade/parallax com tilt-shift, palette cycling e hi-res FX sobre base low-res.
  Use ao dar visual moderno a pixel art sem borrar o sprite. Confirme a versão do Phaser (FX mudou).
---

# Skill: Pixel Art Moderno / HD Remix (HD-2D)

**Regra de ouro:** o sprite/tilemap continua **pixel-perfect**; luz, bloom, profundidade e partículas vêm por cima em **alta resolução**. O charme é o contraste — pixel chunky + luz cinematográfica. **Nunca borre o sprite.**

> ⚠️ As APIs de FX/pipeline do Phaser mudaram (3.6+ ganhou os FX pipelines; v4 mexe no renderer). **Confirme no `package.json` e no `phaser.d.ts`** antes de usar os nomes abaixo.

## 1. Base nítida (pré-requisito)
```js
const config = { type: Phaser.AUTO, pixelArt: true, roundPixels: true,
  scale: { mode: Phaser.Scale.FIT, width: 480, height: 270 },   // base "HD" porém pixel
  render: { antialias: false, roundPixels: true } };
```
Escala/zoom **inteiros**, câmera com `setRoundPixels(true)`. Pixel nunca borra.

## 2. Iluminação dinâmica 2D + normal maps
Luz que reage ao relevo do pixel (dá volume sem repintar):
```js
// no preload: textura + normal map (mesma arte, canal de normais)
this.load.image('tiles', 'tiles.png');
this.load.image('tiles_n', 'tiles_normal.png');   // gerado (ex.: Laigter/SpriteIlluminator)
// na cena:
this.lights.enable().setAmbientColor(0x333344);
const spr = this.add.sprite(x, y, 'hero').setPipeline('Light2D');
// se o asset tem normal map, carregue como atlas com normal e o Light2D usa automaticamente
const lamp = this.lights.addLight(x, y, 200).setColor(0xffd9a0).setIntensity(2);
// mova a luz com o jogador/tochas pra dar vida
```

## 3. Post-FX cinematográfico (bloom / glow / vignette)
```js
// Phaser 3.6+: FX por objeto ou por câmera (confirme na sua versão)
spr.postFX.addGlow(0xffffff, 4, 0, false, 0.1, 8);
this.cameras.main.postFX.addBloom(0xffffff, 1, 1, 1, 1.2);
this.cameras.main.postFX.addVignette(0.5, 0.5, 0.9, 0.4);
```
Bloom vende neon/luz mágica; **use com parcimônia** (custa frame e pode lavar a arte).

## 4. Profundidade / HD-2D layering
- Fundo distante com leve blur/tilt-shift (`postFX.addBlur` no layer de fundo), plano de ação **nítido**.
- Parallax por `scrollFactor`; sombra de chão (blob shadow) sob personagens dá assentamento 3D.

## 5. Palette cycling (clássico que ainda encanta)
Anima cores da paleta (água, lava, brilho) sem novos frames:
```js
// troque entradas de cor ao longo do tempo via tint animado ou shader simples
this.tweens.addCounter({ from:0, to:1, duration:1200, loop:-1, yoyo:true,
  onUpdate: t => water.setTint(Phaser.Display.Color.GetColor(0, 120+80*t.getValue(), 200)) });
```

## 6. Hi-res FX sobre base low-res
Partículas, fumaça, faíscas e luz volumétrica em **resolução alta** por cima de sprites low-res — é o "remix": o contraste cria o look moderno.

## Régua de qualidade
- [ ] Sprite/tilemap nítidos (sem antialias/borrão), escala inteira
- [ ] Luz/bloom em alta resolução, em camada separada (não pixelizam com o sprite)
- [ ] 60fps mantido **com** luz/FX ligados (FX custa — meça `actualFps`)
- [ ] Normal maps batem com a arte (luz coerente)
- [ ] Bloom/vignette sutis (não lavam a paleta)
- [ ] Modo escolhido de propósito (16-bit puro **ou** HD remix), sem mistura acidental

## Legibilidade (arte serve ao gameplay)
- **Silhueta primeiro**: personagem/inimigo legível em preto chapado, à distância de gameplay. Se a silhueta confunde, nenhum detalhe salva.
- **Contraste de VALOR acima de matiz**: o que importa (player, inimigo, item) pinta acima do fundo; fundo detalhado demais rouba o olho da área de jogo.
- **Consistência**: mesmo objeto = mesma família de cor em todas as fases.
- Nomenclatura de asset: `[tipo]_[objeto]_[variante]_[estado].png` (ex.: `spr_oren_walk_01.png`) — nunca `_v2`/`_final`.


## ⚡ Phaser 4 (lançado abril/2026) — fatos verificados
Este projeto roda **Phaser 3.60**. O v4 substituiu TODO o pipeline WebGL por **render nodes**; FX+Masks viraram um sistema único de **Filters** (funciona em qualquer game object/câmera, empilhável: bloom, glow, blur, shadow, color grading, wipe); **SpriteGPULayer** renderiza ~1M sprites em 1 draw call; luz virou `sprite.setLighting(true)` com self-shadow; novos objects: Gradient, Noise, CaptureFrame, Stamp. Migração de API padrão = horas; **quebra**: pipelines/shaders custom, sistema de tint, FX/Masks antigos, e classes removidas (Point, Mesh, BitmapMask). Antes de sugerir upgrade ou API de FX, confirme a versão no `package.json` — receitas 3.x de `postFX` NÃO valem no v4.

## Ferramentas de normal map / arte
Laigter, SpriteIlluminator (normal maps); Aseprite (pixel art + export de sheet); TexturePacker (atlas).
