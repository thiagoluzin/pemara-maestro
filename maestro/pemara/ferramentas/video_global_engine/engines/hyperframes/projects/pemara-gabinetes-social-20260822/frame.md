---
colors:
  background: "#07111F"
  surface: "#101C2D"
  foreground: "#F7FBFF"
  muted: "#8EA3B8"
  orange: "#FF6A00"
  green: "#37E887"
typography:
  display_family: "Pemara Inter"
  display_weight: 900
  data_family: "Pemara Inter"
  data_weight: 850
  body_family: "Pemara Inter"
  body_weight: 750
spacing:
  safe_x: 64
  safe_y: 90
components:
  card_radius: 42
  border_width: 3
  accent_rule: 8
---

# Pemara Gabinetes — frame system

## Overview

Vitrine tecnológica vertical, direta e verificável. O card Qwen aprovado é sempre o protagonista; o HyperFrames organiza ritmo, profundidade e passagem entre produtos sem redesenhar o conteúdo comercial.

## Concept angle

Uma esteira premium de gabinetes reais sobe pela tela: cada produto aterrissa com peso, permanece legível e entrega movimento ao próximo como uma vitrine física em rotação.

## Composition rules

- Fundo azul-petróleo quase preto, com glows localizados laranja e verde.
- O card ocupa a maior área útil e nunca é recortado.
- Dois pontos focais: card/preço e contador de posição no topo.
- Âncoras de borda: contador superior esquerdo, categoria superior direita, progresso inferior.
- Tipos grandes para feed vertical; sem texto menor que 28 px.
- Sem gradiente linear de tela cheia, sem efeito sobre os pixels dos cards, sem claim extra.
- Pemara Inter local em toda a peça: peso 900 na abertura/encerramento, 850 nos contadores e 750 no chrome. O arquivo WOFF2 acompanha o projeto para renderização determinística.

## Motion rules

- Cards: `spring-pop-entrance` com settle `power3.out`, sem bounce.
- Presença: `ambient-glow-bloom` atrás do card, opacidade máxima 0,28.
- Abertura/fechamento: `waterfall-entry` com chegada binária, sem fade frouxo.
- Fronteiras: `vertical-push` de 0,20 s; sem crossfade, hold congelado ou reset de pose.
