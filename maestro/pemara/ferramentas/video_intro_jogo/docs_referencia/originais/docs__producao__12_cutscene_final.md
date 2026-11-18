# Cutscene Final Pos-Tenebra

Fonte canonica: `docs/Novos/roteiro_v2.md`, `docs/Novos/A LORE COMPLETA.md` e `docs/producao/07_tenebra.md`.

## Direcao

Tenebra nao termina como vitoria simples. O final e uma tragedia libertada: Maestro estava preso, tentou proteger Gray e Pinki do jeito errado, e o ultimo ato dele e pedir perdao sem virar desculpa barata. A emocao central nao e "derrotamos o chefe"; e "chegamos tarde, mas ainda ouvimos a parte dele que resistiu".

Regras de cena:

- Slides finais sao ambientais: sem atores, personagens, herois, chefes, monstros, corpos, rostos ou silhuetas humanoides dentro da imagem.
- Sem texto dentro das imagens. Legendas e falas ficam no codigo (`FINAL_CUTSCENE`).
- Maestro e representado por luz quente fragil, particulas, objetos de palco e vazio dramatico, nunca por uma figura.
- Tenebra some como sombra cansada, nao explode como monstro comum.
- Gray e Pinki seguem como centro emocional nas falas, nao como sprites nos slides.
- O Chapeu do Espectro pode aparecer como objeto; ele estilhaca em silencio, como uma prisao quebrando.
- As cores voltam aos poucos; nao virar final feliz imediato.

## Assets Implantados

- Slides finais: `assets/transicoes/FINAL/final_s1.png` a `assets/transicoes/FINAL/final_s12.png`.
- Preview de validacao atual: `tests/previews/final_cutscene_contact_selected_environmental.png`.
- Config do jogo: `FINAL_CUTSCENE` em `js/config/index.js`.
- Trilha-guia de timing: `assets/sounds/music/ending_inst.mp3` com 180s. Quando a musica definitiva sair do Lyria, substitua este arquivo mantendo o mesmo nome.
- `tools/asset_pipeline/build_final_cutscene.py` e um guard obsoleto: ele aborta de proposito porque a regra atual proibe gerar arte de transicao/cutscene por Python/Pillow.

## Roteiro em 12 Slides

| Slide | Tempo | Visual ambiental do slide | Texto / fala | Direcao musical |
| --- | --- | --- | --- | --- |
| 1 | 0:00-0:15 | Arena final vazia, circulo rachado no chao, trono ao fundo, static roxa morrendo e um spotlight frio sobre o centro. | A ultima nota de Tenebra morreu antes de tocar o chao. | Quase silencio. Subgrave baixo, ar parado, cauda da batalha sumindo. |
| 2 | 0:15-0:30 | O Chapeu do Espectro flutua sozinho sobre o circulo vazio; rachaduras douradas aparecem no objeto. | O Chapeu do Espectro perdeu o dominio sobre a sombra. | Textura metalica fria, pulso distante, sem bateria. |
| 3 | 0:30-0:45 | Uma fenda vertical de particulas douradas abre no escuro, abstrata e sem forma humana. | Dentro da escuridao, alguem ainda lembrava o nome das filhas. | Primeiro motivo de piano/Rhodes, pequeno, hesitante. |
| 4 | 0:45-1:00 | Baton de maestro caido, duas marcas de luz vazias no piso e um feixe dourado curvado entre elas. | Maestro: "Gray... Pinki... me perdoem..." | Harmonia quente entra sem resolver, cordas/synth pad discreto. |
| 5 | 1:00-1:15 | Um rastro rosa atravessa o chao em direcao a coluna dourada; so movimento e luz, sem corpo. | Pinki: "Pai!" | Pulso emocional cresce, ainda contido. Sem fanfarra. |
| 6 | 1:15-1:30 | Uma linha de sinal prata-azulada cruza o piso e encontra a luz dourada, como resposta ouvida no silencio. | Gray: "Nos ouvimos voce." | Grave abre, melodia respira; pequena suspensao. |
| 7 | 1:30-1:45 | Vidros de protecao quebrados, cabos em circulo aberto e o baton no centro, mostrando uma prisao emocional que falhou. | Maestro: "Eu tentei proteger voces... e esqueci de escutar." | Melodia principal aparece completa, mas quebrada no final. |
| 8 | 1:45-2:00 | Particulas douradas sobem do centro vazio para uma abertura quente ao fundo; a presenca se desfaz. | Maestro: "Vivam. Facam o mundo cantar sem mim." | Batida muito leve entra como coracao lento; timbres quentes. |
| 9 | 2:00-2:15 | O Chapeu do Espectro estilhaca no ar; fragmentos dourados e violetas ficam suspensos antes de virar poeira clara. | O Chapeu do Espectro se estilhacou em silencio. | Impacto harmonico cristalino, sem explosao; silencio curto depois. |
| 10 | 2:15-2:30 | A cor volta em detalhes pequenos: luz de palco, flor no piso rachado, cabo reparado, poeira dourada. | A cor voltou primeiro as pequenas coisas. | Harmonia sai do menor para maior suspenso; menos peso, mais ar. |
| 11 | 2:30-2:45 | Montagem de ambientes vazios: rua, estudio, floresta, fabrica, caverna e torre, todos feridos mas vivos. | Gray: "Entao vamos fazer o mundo cantar de novo." | Tema agridoce de creditos com piano, analog synth e guitarra suave. |
| 12 | 2:45-3:00 | Palco final vazio, static sumiu, circulo limpo refletindo particulas douradas onde a memoria desapareceu. | O ritmo nunca morre. Apenas espera para ser ouvido novamente. | Cadencia calma, esperancosa e incompleta para continuar nos creditos. |

## Prompt Lyria - Musica Final

```text
Create a 180 second instrumental ending cutscene track for a dark 2D beat-em-up game called Ritmos da Revolta.

Instrumental only. No vocals, no lyrics, no spoken words, no voice, no choir, no humming.

Narrative arc: after the final boss Tenebra is defeated, the scene begins with near silence and emotional shock. Tenebra's control fades; the Spectral Hat loosens and breaks its hold. A fragile warm Maestro motif emerges from darkness. He asks forgiveness from Gray and Pinki. Pinki cries out for her father. Gray answers with quiet grief. Maestro says goodbye. The Spectral Hat shatters like a prison breaking. The world slowly regains its colors. The final section becomes bittersweet credits music: grief, relief, forgiveness, and fragile hope.

Timeline and pacing:
0:00-0:15 almost silent aftermath, low sub drone, dying battle resonance, empty theater air.
0:15-0:30 cold metallic texture as the Spectral Hat separates, very sparse pulses.
0:30-0:45 first fragile Maestro motif appears, soft felt piano or Rhodes-like keys, warm but weak.
0:45-1:00 forgiveness moment for Gray and Pinki, suspended minor harmony, intimate and painful.
1:00-1:15 Pinki's grief rises, emotional swell, restrained percussion still distant.
1:15-1:30 Gray answers with quiet grief, melody breathes, no heroic fanfare.
1:30-1:45 Maestro farewell, main motif becomes clear but unfinished.
1:45-2:00 light dissolves, slow heartbeat-like low percussion, soft analog synth pad.
2:00-2:15 Spectral Hat shatters with a crystalline harmonic impact, followed by a short silence.
2:15-2:30 color returns to the world, harmony opens from minor into suspended major.
2:30-2:45 bittersweet credits theme begins, warm synths, gentle piano, subtle guitar swells.
2:45-3:00 calm unresolved cadence, hopeful but still grieving, suitable to continue under credits.

Style: cinematic game ending, dark ambient synth, melancholic industrial texture, soft felt piano, Rhodes-like electric keys, bowed metal drones, warm analog pads, subtle low percussion, distant electric guitar volume swells, long reverb tails, wide stereo image, clean game mix with headroom, no clipping. Around 62-68 BPM, D minor moving gradually toward F Lydian or suspended major colors. Emotional references: tragic liberation, forgiveness, color returning after corruption, not a victory anthem.

Avoid: trailer drums, triumphant fanfare, bright pop hook, dance beat, comedy tone, horror jump scares, vocals, voice, lyrics, choir, chanting, spoken words.
```

## Prompt Curto Alternativo

```text
180s instrumental ending cutscene music for Ritmos da Revolta. Near-silent fall of Tenebra's control, fragile warm Maestro motif emerging from darkness, apology to Gray and Pinki, unreachable farewell, Spectral Hat shattering, world slowly regaining color, bittersweet credits. Dark ambient synth, soft felt piano, Rhodes-like keys, bowed metal, warm analog pads, subtle low percussion, restrained guitar swells, 62-68 BPM, D minor toward suspended major hope. Emotional, tragic, forgiving, not triumphant. No vocals, no lyrics, no voice, no choir, no humming, no spoken words.
```
