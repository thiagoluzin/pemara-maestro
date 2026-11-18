# Transicoes de Fase

Contrato usado por `CutsceneScene`:

- Imagens em `assets/transicoes/F{N}-F{N+1}/f{N}_s{M}.png`.
- Tamanho padrao: `1672x941` RGB, widescreen 16:9.
- Texto nao vai dentro da imagem; as legendas ficam em `PHASE_TRANSITIONS`.
- Regra visual: slides de transicao nao exibem atores, personagens, herois, bosses, monstros, corpos, rostos ou silhuetas. A historia visual deve vir do ambiente.
- Regra de producao: nao gerar arte final de transicao/cutscene com Python/Pillow/procedural scripts. Use o gerador interno GPT, valide visualmente e copie para esta pasta. FFmpeg/CLI pode ser usado apenas para resize/crop/prancha tecnica.
- Cada transicao tem 12 slides planejados com `dur: 15000`.
- Musica ideal: cerca de 175 a 180 segundos. A cena reescala os slides para a duracao real do audio carregado.

## Status

| Transicao | musicKey | Arquivo de musica atual | Duracao atual | Imagens |
| --- | --- | --- | --- | --- |
| F1 -> F2 | `stage2_inst` | `assets/sounds/music/stage2_inst.mp3` | 179.44s | 12/12 prontas |
| F2 -> F3 | `stage3_inst` | `assets/sounds/music/The_Grind_Beneath.mp3` | 175.93s | 12/12 prontas |
| F3 -> F4 | `stage4_inst` | `assets/sounds/music/Cold_Steel_Exhale.mp3` | 177.35s | 12/12 prontas |
| F4 -> F5 | `stage5_inst` | `assets/sounds/music/Weight_of_the_Iron_Pulse.mp3` | 176.25s | 12/12 prontas |
| F5 -> F6 | `stage6_inst` | `assets/sounds/music/Water_Under_The_Server.mp3` | 173.61s | 12/12 prontas |
| F6 -> F7 | `boss_inst` | `assets/sounds/music/Trono_do_Tenebra.mp3` | 177.45s | 12/12 prontas |

Todas as transicoes F1->F7 estao com musica final (sem stubs). `boss_inst` ("Trono do Tenebra")
tambem toca na tela de vitoria parcial (`VictoryScene`, ending nao-completo).
Os MP3 ficam em `assets/sounds/music/` (a pasta `assets/transicoes/` so guarda os slides
`fN_sM.png`; o build da demo trata qualquer outro arquivo la como fonte e nao o empacota).
Preferencia para novas faixas: ~175 a 180s, stereo 44.1/48 kHz, pico abaixo de -1 dB.

## Prompt Base Lyria

Use este bloco em todos os prompts, adicionando o bloco especifico de cada transicao:

```text
Instrumental game cutscene track for a dark 2D beat-em-up. No vocals, no lyrics, no voice, no choir, no spoken words. Loop-friendly ending, cinematic but not trailer music, strong narrative arc over about 180 seconds, dark industrial metal, cyberpunk synth textures, heavy low-end, minor key, gritty urban atmosphere, clean stereo mix with headroom.
```

## Prompts Lyria por Transicao

### `stage2_inst` - F1 -> F2

Cena: bairro vencido depois de BRUD, caminho ate o estudio tomado por Vineria.

```text
Create a 180 second instrumental track. Starts with silent post-battle urban ambience, distant low bass drone and broken streetlamp hum. Slowly introduces cold industrial pulse, metallic reverb, detuned minor-key synth pads, and faint studio-equipment noise. The middle grows oppressive with slow distorted bass and suspended tension, as if a recording studio is breathing behind a locked door. Final third reveals a feminine plant-monster presence through eerie organic synth swells and dark pink neon harmonics. 65 BPM, no vocals, no voice, no lyrics, no drums dominating the mix, loop-friendly unresolved ending.
```

### `stage3_inst` ("The Grind Beneath") - F2 -> F3

Cena: Vineria livre, alivio curto no estudio, caminho ate a Floresta Corrompida e as Raizes de Ferro acordando sob a terra.

```text
Create a 180 second instrumental track. Opens with warm relieved analog synths and soft studio room tone for 25 seconds, then the room tone is swallowed by outdoor night ambience, low purple-fog drones, creaking dead trees, distant wooden cracks, and faint metallic chain scrapes under the soil. Add dark organic synth pads, deep sub-bass, sparse tribal-industrial pulses around 72 BPM, toxic green shimmer textures, and wet forest percussion made from leaves, mud, roots, and rusted iron links. The final minute grows heavier and more threatening, as if iron roots are waking beneath a corrupted forest clearing. No vocals, no voice, no lyrics, loop-friendly unresolved ending.
```

### F2 -> F3

| Slide | Arquivo | Legenda |
| --- | --- | --- |
| 1 | `assets/transicoes/F2-F3/f2_s1.png` | O estudio enfim respirou fundo. |
| 2 | `assets/transicoes/F2-F3/f2_s2.png` | Pelas rachaduras, a nevoa roxa entrou em silencio. |
| 3 | `assets/transicoes/F2-F3/f2_s3.png` | Atras do estudio, cabos e raizes ja se misturavam. |
| 4 | `assets/transicoes/F2-F3/f2_s4.png` | A cidade terminava onde as arvores mortas comecavam. |
| 5 | `assets/transicoes/F2-F3/f2_s5.png` | A Floresta Corrompida abriu uma trilha sem canto. |
| 6 | `assets/transicoes/F2-F3/f2_s6.png` | Fungos frios iluminavam a lama e as folhas mortas. |
| 7 | `assets/transicoes/F2-F3/f2_s7.png` | Raizes finas puxavam antigos elos de ferro para fora da terra. |
| 8 | `assets/transicoes/F2-F3/f2_s8.png` | Olhos vermelhos piscavam entre troncos vazios. |
| 9 | `assets/transicoes/F2-F3/f2_s9.png` | A nevoa se fechou atras deles como uma porta. |
| 10 | `assets/transicoes/F2-F3/f2_s10.png` | A clareira surgiu sem musica, limpa demais para ser paz. |
| 11 | `assets/transicoes/F2-F3/f2_s11.png` | Nas bordas, raizes e correntes dormiam juntas. |
| 12 | `assets/transicoes/F2-F3/f2_s12.png` | A natureza distorcida chamava: as Raizes de Ferro estavam vivas. |

### `stage4_inst` ("Cold Steel Exhale") - F3 -> F4

Cena: a Floresta Corrompida fica para tras e a Fábrica de Ritmos acorda em aco azul, vapor e alto-falantes industriais.

```text
Create a 180 second instrumental track. Begins with corrupted forest ambience: low purple fog drones, dead branches creaking, damp earth and faint teal bioluminescent shimmer. Gradually introduce distant metal resonance, rusted gate groans, conveyor hum, hydraulic pressure and cold steel percussion. Around 70 BPM, industrial metal texture with precise machine rhythm, speaker-cone pulses, blue electrical arcs and orange warning-light accents. The final minute becomes the abandoned rhythm factory waking up around the listener, ominous and controlled. No vocals, no voice, no lyrics, loop-friendly unresolved ending.
```

### `stage5_inst` ("Weight of the Iron Pulse") - F4 -> F5

Cena: a fabrica desliga e revela tuneis subterraneos ate as Cavernas Amaldicoadas.

```text
Create a 180 second instrumental track. Starts with factory machinery powering down: conveyor motors dying, metal ticks, air pressure leaking and distant speaker hum collapsing into silence. Then a lower underground world appears: water drips, damp stone resonance, cave sub-bass, teal crystal shimmer, small ruins echoing in the dark. 62 BPM, minor key, dark ambient industrial turning into cavern horror, with low drums made from stone impacts and rusted pipes. Final minute feels ancient, wet and heavy, like cursed underground ruins opening under the factory. No vocals, no voice, no lyrics, no occult chanting, loop-friendly unresolved ending.
```

### `stage6_inst` ("Water Under The Server") - F5 -> F6

Cena: cristais da caverna entram em estatica e o caminho sobe pelas fundacoes ate a Torre do Tenebra.

```text
Create a 180 second instrumental track. Begins in a damp cavern with teal crystals flickering, then the crystal glow corrupts into green digital static. A vertical service shaft and elevator machinery rise into a skyscraper tower: concrete resonance, broken cables, server fans, emergency lamps and distant city fires. Build into glitch industrial at 80 BPM with bit-crushed synth bass, failing hardware percussion, relay clicks, broken broadcast tones and smoke-dark ambience. Final third becomes an upper-floor corporate warzone under digital control, green static over orange firelight. No vocals, no voice, no lyrics, loop-friendly unresolved ending.
```

### `boss_inst` ("Trono do Tenebra") - F6 -> F7

Cena: a Torre do Tenebra se desfaz em uma dimensao de broadcast/TV static, revelando o Trono do Tenebra.

```text
Create a 180 second final-boss entrance instrumental. Opens with the burning tower hall losing power, server noise collapsing into white-gray TV static. The room dissolves into a black broadcast void: fractured monoliths, purple signal arcs, red signal tears and a distant empty throne architecture. 70 BPM, fatalistic dark synth metal, massive distorted power chords under cold static bands, industrial percussion, sub-bass pressure and ritual tension without choir. Final minute should feel like reality stabilizing into the Trono do Tenebra, grand and inevitable, but with an unresolved ending that can cut into gameplay. No vocals, no voice, no lyrics, no choir.
```

## Roteiro Visual

### F3 -> F4

| Slide | Arquivo | Legenda |
| --- | --- | --- |
| 1 | `assets/transicoes/F3-F4/f3_s1.png` | A clareira ficou vazia, mas o silencio nao voltou. |
| 2 | `assets/transicoes/F3-F4/f3_s2.png` | Entre raizes mortas, o metal comecou a aparecer. |
| 3 | `assets/transicoes/F3-F4/f3_s3.png` | A trilha terminou diante de um portao industrial. |
| 4 | `assets/transicoes/F3-F4/f3_s4.png` | A floresta ficou do lado de fora da ultima luz roxa. |
| 5 | `assets/transicoes/F3-F4/f3_s5.png` | A Fabrica de Ritmos dormia em aco azul. |
| 6 | `assets/transicoes/F3-F4/f3_s6.png` | Luzes de aviso piscaram como um pulso mecanico. |
| 7 | `assets/transicoes/F3-F4/f3_s7.png` | Paineis rachados acordaram sem tocar musica. |
| 8 | `assets/transicoes/F3-F4/f3_s8.png` | O nucleo da fabrica respirou vapor e ferrugem. |
| 9 | `assets/transicoes/F3-F4/f3_s9.png` | O chao de grade conduzia para o coracao da maquina. |
| 10 | `assets/transicoes/F3-F4/f3_s10.png` | Alto-falantes mudos esperavam uma ordem impossivel. |
| 11 | `assets/transicoes/F3-F4/f3_s11.png` | O corredor abriu espaco para o proximo confronto. |
| 12 | `assets/transicoes/F3-F4/f3_s12.png` | A fabrica inteira pareceu ligar de uma so vez. |

### F4 -> F5

| Slide | Arquivo | Legenda |
| --- | --- | --- |
| 1 | `assets/transicoes/F4-F5/f4_s1.png` | As engrenagens pararam de girar. |
| 2 | `assets/transicoes/F4-F5/f4_s2.png` | Debaixo da fabrica, um corredor descia para a pedra. |
| 3 | `assets/transicoes/F4-F5/f4_s3.png` | O metal terminou onde a caverna comecou. |
| 4 | `assets/transicoes/F4-F5/f4_s4.png` | A agua pingava sobre trilhos que ninguem usava. |
| 5 | `assets/transicoes/F4-F5/f4_s5.png` | Ruinas antigas surgiram entre paredes umidas. |
| 6 | `assets/transicoes/F4-F5/f4_s6.png` | Cristais frios iluminaram o caminho sem canto. |
| 7 | `assets/transicoes/F4-F5/f4_s7.png` | A caverna abriu sua primeira grande garganta. |
| 8 | `assets/transicoes/F4-F5/f4_s8.png` | Pedras quebradas guardavam uma historia sem nome. |
| 9 | `assets/transicoes/F4-F5/f4_s9.png` | A luz verde respirava pelas veias minerais. |
| 10 | `assets/transicoes/F4-F5/f4_s10.png` | A camara principal apareceu atras da nevoa fria. |
| 11 | `assets/transicoes/F4-F5/f4_s11.png` | O chao estava limpo demais para um lugar esquecido. |
| 12 | `assets/transicoes/F4-F5/f4_s12.png` | As Cavernas Amaldicoadas abriram passagem. |

### F5 -> F6

| Slide | Arquivo | Legenda |
| --- | --- | --- |
| 1 | `assets/transicoes/F5-F6/f5_s1.png` | Os cristais da caverna perderam o brilho. |
| 2 | `assets/transicoes/F5-F6/f5_s2.png` | Uma estatica verde entrou pelas veias da pedra. |
| 3 | `assets/transicoes/F5-F6/f5_s3.png` | Um eixo antigo subia ate as fundacoes da torre. |
| 4 | `assets/transicoes/F5-F6/f5_s4.png` | O elevador inferior abriu para concreto e silencio. |
| 5 | `assets/transicoes/F5-F6/f5_s5.png` | La em cima, a cidade queimava atras dos vidros partidos. |
| 6 | `assets/transicoes/F5-F6/f5_s6.png` | Servidores acesos chiavam sem formar palavras. |
| 7 | `assets/transicoes/F5-F6/f5_s7.png` | O corredor corporativo parecia mais longo a cada passo. |
| 8 | `assets/transicoes/F5-F6/f5_s8.png` | As salas de transmissao piscavam em verde doente. |
| 9 | `assets/transicoes/F5-F6/f5_s9.png` | O fogo refletia em telas que ninguem controlava. |
| 10 | `assets/transicoes/F5-F6/f5_s10.png` | A torre mostrou o andar onde o ruido mandava. |
| 11 | `assets/transicoes/F5-F6/f5_s11.png` | O chao carbonizado abriu uma arena sem aplausos. |
| 12 | `assets/transicoes/F5-F6/f5_s12.png` | A Torre do Tenebra esperava no alto da cidade. |

### F6 -> F7

| Slide | Arquivo | Legenda |
| --- | --- | --- |
| 1 | `assets/transicoes/F6-F7/f6_s1.png` | A sala superior da torre apagou suas ultimas chamas. |
| 2 | `assets/transicoes/F6-F7/f6_s2.png` | As janelas trocaram a cidade por estatica. |
| 3 | `assets/transicoes/F6-F7/f6_s3.png` | Pedacos da torre comecaram a flutuar no vazio. |
| 4 | `assets/transicoes/F6-F7/f6_s4.png` | O chao virou uma plataforma de transmissao quebrada. |
| 5 | `assets/transicoes/F6-F7/f6_s5.png` | Um corredor de ruido abriu caminho no escuro. |
| 6 | `assets/transicoes/F6-F7/f6_s6.png` | Monolitos partidos responderam com energia roxa. |
| 7 | `assets/transicoes/F6-F7/f6_s7.png` | Ao longe, um trono vazio tomou forma. |
| 8 | `assets/transicoes/F6-F7/f6_s8.png` | A estatica se organizou como uma catedral sem voz. |
| 9 | `assets/transicoes/F6-F7/f6_s9.png` | O vazio finalmente parou de se mover. |
| 10 | `assets/transicoes/F6-F7/f6_s10.png` | Cada rachadura roxa parecia escutar. |
| 11 | `assets/transicoes/F6-F7/f6_s11.png` | A plataforma final esperava sem plateia. |
| 12 | `assets/transicoes/F6-F7/f6_s12.png` | O Trono do Tenebra abriu o ultimo compasso. |

## Checklist de Arquivos

| Pasta | Status |
| --- | --- |
| `assets/transicoes/F1-F2/f1_s1.png` ... `f1_s12.png` | pronto |
| `assets/transicoes/F2-F3/f2_s1.png` ... `f2_s12.png` | pronto |
| `assets/transicoes/F3-F4/f3_s1.png` ... `f3_s12.png` | pronto |
| `assets/transicoes/F4-F5/f4_s1.png` ... `f4_s12.png` | pronto |
| `assets/transicoes/F5-F6/f5_s1.png` ... `f5_s12.png` | pronto |
| `assets/transicoes/F6-F7/f6_s1.png` ... `f6_s12.png` | pronto |

Preview geral: `tests/previews/transition_cutscenes_f3_f7_contact.png`.
