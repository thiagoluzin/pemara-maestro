# Regras para Sprites dos Inimigos da Fase 2 (assets/sprites/inimigos_f2/)

> **ATENÇÃO AGENTE:** As spritesheets de inimigos sprunki nesta pasta seguem grades de fatiamento específicas no Phaser.

## Regras de Resoluções e Grades
1. **Alta Resolução (2752x1536 | 8 colunas de 344x384px | 4 linhas):**
   - **Sprites:** `tunner_f2.png`, `sky_f2.png`, `mrfuncomputer_f2.png`.
   - **Lógica:** NUNCA reduza a resolução destes arquivos nem altere suas animações de 8 colunas no Phaser. A largura extra do frame impede que o personagem duplique ao cair na animação de `hurt`.
2. **Média Resolução - 8 Colunas (1584x672 | 8 colunas de 198x224px | 3 linhas):**
   - **Sprites:** `brud_f2.png`.
3. **Média Resolução - 6 Colunas (1584x672 | 6 colunas de 264x224px | 3 linhas):**
   - **Sprites:** `clukr_f2.png`, `funbot_f2.png`, `gray_f2.png`, `jevin_f2.png`, `oren_f2.png`.
   - **Lógica:** Estes inimigos devem ser fatiados em 6 colunas no `BootScene.js`. Mapear como 8 colunas causará deformidades gráficas.
