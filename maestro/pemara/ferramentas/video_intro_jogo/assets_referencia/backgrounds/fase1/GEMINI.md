# Regras dos Cenários da Fase 1 (assets/backgrounds/fase1/)

> **ATENÇÃO AGENTE:** A Fase 1 possui uma composição única de layers que difere das fases padrão.

## Regras de Composição
1. **Quantidade de Layers:**
   - Possui exatamente 4 camadas de cenário (Layers 1 a 4). A Layer 5 está banida e foi completamente deletada.
2. **Nomes e Extensões dos Arquivos:**
   - `1.jpg` (Layer 1 - Céu Noturno - Opaco)
   - `2.png` (Layer 2 - Transparent PNG)
   - `3.png` (Layer 3 - Fallback para arena do Boss)
   - `3.1.png` a `3.4.png` (Sequência especial de Parallax - Transparent PNG)
   - `4.png` (Layer 4 - Rua/Asfalto - Transparent PNG)
   - `fase1_boss_layer3.png` (Imagem da Arena do Boss)
3. **Parâmetros Físicos e Visuais:**
   - A Layer 4 (rua) é encolhida no `background_config.json` com escala de `0.8` e posicionamento vertical `offsetY: 465` para permitir a visão do céu/montanhas por trás.
   - O chão físico da calçada está configurado em `floorY: 830`.
4. **Sem Fundo Branco:**
   - Todos os arquivos `.png` desta pasta (incluindo a sequência `3.1` a `3.4`) tiveram seus fundos brancos removidos. NUNCA os substitua por imagens com fundos opacos.
