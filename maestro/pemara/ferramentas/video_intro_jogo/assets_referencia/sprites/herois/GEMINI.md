# Regras para Sprites de Heróis (assets/sprites/herois/)

> **ATENÇÃO AGENTE:** Esta pasta contém os sprites dos personagens controláveis (simon, pinki, wenda, garnold, funbot) e as novas spritesheets avançadas de Oren localizadas em `herois/oren/`.

## Diretrizes de Heróis
1. **Heróis Clássicos:**
   - Simon, Pinki, Wenda, Garnold e Funbot usam spritesheets transparentes de `frameWidth: 320` e `frameHeight: 360` no carregador do Phaser.
2. **Spritesheets Avançadas de Oren (Pasta `oren/`):**
   - Oren utiliza múltiplos spritesheets divididos por estado/animação (ex: pulos, attacks, hurt, walk, super) sob a pasta `herois/oren/`.
   - Cada estado possui sua própria resolução e contagem de frames. Mantenha os valores de `frameWidth` e `frameHeight` definidos no [BootScene.js](file:///d:/usuario/Documents/Ritmos%20da%20Revolta/js/scenes/BootScene.js) sincronizados perfeitamente com os tamanhos físicos dos arquivos correspondentes sob `herois/oren/{estado}/`.
3. **Escala e Colisão:**
   - Heróis clássicos usam escala de colisão e offset fixos. Oren lê dimensões diferenciadas por spritesheet avançada. O ajuste fino do pé (`setOffset`) deve ser verificado em `Player.js` após qualquer alteração visual.
