# Regra Estrita de Organização dos Backgrounds

> **ATENÇÃO AGENTE:** Esta pasta possui uma estrutura estritamente organizada que não deve ser alterada sob hipótese alguma.

## Regras de Organização

1. **Estrutura de Pastas Individual por Fase:**
   - Cada fase possui sua própria pasta sob `assets/backgrounds/fase{phaseIndex}/`.
   - Proibido misturar ou juntar arquivos de fases diferentes em pastas comuns ou na raiz.
   
2. **Fase 1 (fase1):**
   - Possui 4 camadas (Layers 1 a 4). A Layer 5 está banida e foi completamente deletada.
   - Nomes e formatos dos arquivos:
     - `1.jpg` (Layer 1 - Sky - Opaco)
     - `2.png` (Layer 2 - Transparent PNG)
     - `3.png` (Layer 3 - Fallback para arena do Boss)
     - `3.1.png` a `3.4.png` (Sequência especial de Parallax - Transparent PNG)
     - `4.png` (Layer 4 - Ground/Foreground - Transparent PNG)
     - `boss_layer3.png` (Cenário do Boss)
   - Todas as imagens PNG (`2.png`, `3.png`, `4.png`, `3.1.png` a `3.4.png`) tiveram seus fundos brancos removidos para transparência. **NUNCA substitua estes arquivos por JPGs opacos.**

3. **Fases 2 a 7 (fase2 a fase7):**
   - Possuem 5 camadas (Layers 1 a 5).
   - Nomeadas exatamente como `{layerIndex}.png` (ex: `1.png`, `2.png`, `3.png`, `4.png`, `5.png`).
   - Boss Arena (se houver): nomeada exatamente como `boss_layer3.png`.

## Regra de Código Relacionada
Qualquer modificador de carregador (`BootScene.js` ou `BackgroundManager.js`) deve carregar as texturas respeitando os caminhos específicos definidos acima.
