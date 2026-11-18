# PROMPTS DE SPRITES — regerar o time no estilo do OREN

> **Para que serve:** regerar os sprites dos heróis (e do NPC Gray) para casar 100% com o
> **estilo e qualidade do OREN** (a referência), sem mudar a identidade de cada um. Estes prompts
> são para colar num gerador de imagem (Gemini "Nano Banana" / Copilot).
>
> **Cobertura:** Simon (**refeito** — identidade travada na arte real), Pinki (revisado), Wenda, Garnold,
> FunBot e Gray (NPC). Cada um deriva da ARTE EXISTENTE do projeto — não inventei aparência;
> reescrevi a forma para casar com o tratamento do Oren mantendo a identidade Sprunki de cada um.
>
> **Idioma:** os prompts estão em **inglês de propósito** (os modelos rendem melhor). Os
> nomes/identidade estão corretos. Converse em português, gere em inglês.
>
> **Antes de aceitar qualquer sprite:** rode `npm run check:sprites`. Se não passar (código 0),
> o sprite não está pronto. O validador mede o PNG real — não é no olho.

---

## 0. Por que Simon e Pinki destoam hoje (o que CORRIGIR)

Medi o Oren e comparei com o que existe. Os problemas são **estruturais**, não de cor:

| Eixo | OREN (alvo) | SIMON hoje (errado) | PINKI hoje (errado) |
|------|-------------|---------------------|---------------------|
| Proporção | **~2.5–3 cabeças** de altura, heroico-estilizado, cabeça GRANDE (~1/3 do corpo) | **Simon é EXCEÇÃO: o "heavy" alto/largo, ~3,5–4 cabeças, pernas LONGAS, cabeça ~1/4** (nem anão chibi, nem hobbit realista de 4,5–5) | mais esguia/alta que o Oren |
| Ângulo | **3/4 de lado, virado p/ a DIREITA** | de frente, encarando a câmera | de frente |
| Luz | sombreamento volumétrico macio + **rim light laranja quente** no contorno | flat retro de fliperama, sem rim light | sombreado chapado, sem rim light |
| Lineart | escuro, coeso, espesso | fino estilo sprite 90s | fino |
| Acabamento | pixel art **HD moderno** (nítido mas pintado) | retro 16-bit chapado | semi-flat |

Ou seja: o erro não é a cor amarela do Simon nem o rosa da Pinki — é **proporção, ângulo, luz e
acabamento**. O STYLE BLOCK abaixo trava isso.

---

## 1. STYLE BLOCK (prefixe em TODA geração)

Copie este bloco como **abertura de qualquer prompt** abaixo. Ele carrega o "DNA Oren".

```
STYLE — match this exactly (reference: the Oren character):
Modern HD pixel art, NOT flat retro 8-bit. Crisp hard pixels (nearest-neighbor look,
image-rendering pixelated) BUT with soft volumetric shading and a warm orange rim light
tracing the contour of the body. Bold dark cohesive outline (thick, deliberate), painterly
internal shading with clear light direction from the upper-front. High craft, clean,
game-ready sprite quality.

PROPORTION — heroic stylized, NOT realistic: head is large, body is about 2.5 to 3 heads
tall (athletic-chibi hero proportions, like a 16-bit beat-em-up hero). DO NOT draw a
realistic 6-head bodybuilder. DO NOT slim it into a tall anime figure.

VIEW — strict 3/4 side view, character FACING RIGHT, full body, standing on the ground,
feet flat at the very bottom of the frame, small headroom margin at the top.

FRAMING — single character only, one per frame, dead-centered horizontally, occupying the
SAME vertical fraction of the frame as a 16-bit hero sprite (fills most of the height).
Background MUST be 100% transparent (alpha), no ground shadow, no border, no box, no text,
no UI, no extra props.

OUTPUT — clean transparent PNG sprite. Target a MODEST frame size, ~256px tall at most
(character content ~200px tall), matching the Oren reference. This is a walking beat-em-up —
sprites render around 173px tall on screen, so there is NO need for giant 512px frames.
```

> **Tamanho: nada de sprite gigante.** O jogo renderiza o herói a ~173px de altura. O Oren
> vive em frames de **~90–250px** (idle 90×201, walk 188×342, dash 148×185). Os sheets atuais de
> Simon/Pinki são **366–516px** e são esmagados pra ~166px — desperdício de memória e fonte de
> inconsistência. **Alvo de armazenamento: frame com ~200–256px de altura.** Se quiser gerar
> grande só para ganhar detalhe, tudo bem — mas **faça downscale nearest-neighbor para ~tamanho
> do Oren antes de salvar no jogo**. O que entra no `assets/` é no tamanho do Oren, não gigante.

**Regra de ouro de fidelidade:** o que está no STYLE BLOCK é **inegociável** — proporção,
ângulo (3/4 right), rim light laranja, fundo transparente, 1 personagem por frame. Tudo o que
muda por personagem está na seção de identidade de cada um.

---

## 1B. COR — paleta travada (corrige o cast vermelho/magenta/marrom)

> **Diagnóstico medido (2026-06-04):** o tom "vermelho/magenta/marrom" que aparecia no jogo era
> de **DUAS fontes distintas** — só uma é de arte:
> 1. **Tint de dano preso (era código, JÁ CORRIGIDO):** ao tomar dano o herói recebia um tint
>    vermelho SÓLIDO por 500ms; andava/recuperava "vermelho" a tela toda. Virou um flash de 130ms.
> 2. **Variação de paleta na ARTE FONTE da IA:** comparando fonte × processado o delta de cor é
>    **R+0 G+0 B+0** — o `process_heroes.py` NÃO descolore (o despill está inocente). Logo as
>    pernas/cintura marrom-avermelhadas em alguns sheets vêm da **própria geração** — a IA variou a
>    paleta entre uma animação e outra. **Isso só some regerando com a paleta travada abaixo.**

Cole este **COLOR LOCK** logo após o bloco de identidade do personagem, em TODA geração. Ele
impede o cast quente/magenta e mantém a paleta consistente entre TODAS as animações:

```
COLOR LOCK — keep the palette IDENTICAL across every frame and every animation of this
character. Flat, clean color regions with deliberate shading; NO random hue drift between
frames. Do NOT wash the whole sprite in a warm/red/orange/brown/magenta tint — the warm
orange RIM LIGHT must stay a THIN edge highlight on the contour only, it must NOT bleed into
the body fills. Skin, clothes and metal keep their OWN local color; the legs/pants must NOT
turn reddish-brown or pink/magenta. Saturated, readable 16-bit colors, consistent across the
whole sheet.
```

**Paleta exata por personagem** (acrescente a linha do seu personagem ao COLOR LOCK):

| Personagem | Paleta travada (use exatamente estas cores locais) |
|------------|-----------------------------------------------------|
| **Simon** | Pele **amarelo-dourado** (não laranja, não marrom). Armadura **cinza-aço/gunmetal neutro** (NÃO marrom, NÃO avermelhada). Luvas e botas **brancas**. Cabelo **amarelo**. Pernas/calça por baixo da armadura = **cinza-escuro neutro**, NUNCA marrom/rosa. |
| **Pinki** | Pelo **rosa**, laço e regata **magenta**, calça **preta neutra** (NÃO marrom), wraps **roxas**. |
| **Wenda** | Pelo/cabelo **branco/prata**, jaqueta e calça **preto neutro**, corrente **cinza-aço**. |
| **Garnold** | Traje **amarelo**, visor **preto/escuro**, eletricidade **azul-ciano**. |
| **FunBot** | Corpo **prata/aço escovado neutro**, visor **ciano**, pontas de antena **amarelas**. |
| **Gray** | **Tons de cinza monocromáticos** — sem nenhuma cor viva (o rim light é o único acento quente). |

> Termine o prompt repetindo: `STRICT PALETTE: <paleta do personagem>. No global warm/red/magenta
> color cast. Same palette in every frame.`

**Tamanho decente do personagem dentro do frame:** o erro comum da IA é gerar a figura PEQUENA
no meio de um frame grande e vazio. Force o preenchimento — acrescente ao prompt:

```
FRAMING SIZE — the character FILLS the frame: feet near the bottom edge, head near the top
edge, only a small uniform margin all around. The character occupies ~85-90% of the frame
height. Do NOT render a small figure floating in a large empty canvas.
```

---

## 2. Formato de SPRITESHEET (todos os prompts de animação dependem disso)

O jogo lê cada animação como **uma tira horizontal** com células de tamanho **idêntico** (grid
exato — o validador reprova se a imagem não dividir certinho pelo frame declarado).

Trave SEMPRE, em todo prompt de animação:
- **Horizontal strip**, N frames lado a lado, esquerda → direita.
- **Identical cell size** para todos os frames (mesma largura e altura de célula).
- **Same anchor in every cell:** os PÉS alinhados na MESMA linha de base em todos os frames; o
  personagem centralizado dentro da própria célula.
- **No gaps, no grid lines, no numbers, no labels** entre os frames.
- Transparent background em toda a tira.

Frames por animação (o que o jogo espera):

| Animação | Frames | Observação |
|----------|:------:|------------|
| idle | 7 | parado, respiração sutil |
| walk | 8 | ciclo de caminhada |
| ataque (attack) | 8 | combo numa tira só |
| dash | 4 | arranque pra frente |
| esquiva / backflip | 4 | recuo/giro pra trás |
| pulo (jump) | 5 | agacha → sobe → ápice → desce → pousa |
| dano (hurt) | 4 | recuo de impacto |
| morte (death) | 6 | cambaleia → cai → deitado |
| tédio (idle_special) | 6 | animação de ociosidade com personalidade |
| super / special | 4–6 | golpe especial |

> Dica: idle costuma sair melhor gerando os **7 frames individuais** e montando a tira depois
> (foi assim que o Oren ficou bom). Para as demais, peça a tira direto, mas se o modelo
> "inventar", gere frame a frame e monte.

---

## 3. SIMON — o tank blindado do machado (brutamontes amarelo de armadura)

**Identidade DEFINITIVA (travada na ARTE existente — não no config):** o config antigo dizia
"Haggar humano com pé-de-cabra", mas a arte real (`simon_idle_1.png`) é **outra coisa** e é ela
que manda. Simon é um **brutamontes de pele amarela/dourada vestindo uma armadura de batalha
segmentada cinza-escura com ombreiras de ESPINHOS** (vibe guerreiro alienígena / armadura tipo
saiyajin), **cabelo amarelo em topete espetado**, **luvas e botas brancas blindadas**, físico
gigante e musculoso. É o **TANK** do time: o maior, mais largo, mais forte e mais lento; **empunha um grande MACHADO MEDIEVAL DE DUAS LÂMINAS** (cabo longo +
cabeça em crescente duplo, lâmina curva dos dois lados) — o pé-de-cabra foi descartado. Mantém os
**atributos do Haggar** (tank lento, forte, muito HP, maior alcance). Mantenha a
**paleta própria do Simon** (amarelo/dourado + armadura cinza-aço + branco), **nunca o laranja
do Oren**, mas com o tratamento de luz/contraste do STYLE BLOCK.

> **Por que travei nessa identidade:** (1) é o que a arte JÁ é e o que o jogador reconhece — forçar
> um Haggar humano com crowbar jogaria fora o asset e criaria um terceiro Simon; (2) "tank blindado
> que soca" é 100% coerente com o papel de TANK (maior HP, encaixa golpe, bate de perto); (3) trava
> o gerador num alvo único — sem oscilar entre "lutador de rua humano" e "guerreiro alienígena
> amarelo". A partir de agora Simon = **brutamontes amarelo de armadura com espinhos empunhando um grande
> machado medieval de duas lâminas**, com os atributos de tank do Haggar. Pé-de-cabra APOSENTADO.

> ⚠️ **CORREÇÃO CRÍTICA — leia antes de regerar.** O Simon já oscilou entre dois erros opostos:
> (a) **realista alto/magro** (~4,5–5 cabeças, "hobbit") e (b) **chibi atarracado de pernas curtas
> = ANÃO do Senhor dos Anéis**. O alvo é o **MEIO-TERMO: o PESO-PESADO do time — ALTO, LARGO e
> musculoso, tipo Haggar (Final Fight)**: **~3,5–4 cabeças**, **PERNAS LONGAS e fortes**, ombros
> muito largos com espinhos, tronco e braços grossos, cabeça **levemente grande (~1/4 da altura, NÃO
> 1/3)** mas sem dominar. ⚠️ Simon é o ÚNICO do time que **NÃO** segue as 2,5–3 cabeças do STYLE
> BLOCK — ele é mais alto (arquétipo "heavy/brutamontes"). Mantenha do Oren só o **estilo**: 3/4
> virado pra DIREITA + rim light quente + sombreamento volumétrico HD + lineart espesso. A causa do
> "anão" era **perna curta** — pernas longas resolvem. Veja os NEGATIVES no bloco CHARACTER.

**Bloco de identidade do Simon** (cole logo após o STYLE BLOCK em todos os prompts dele):

```
CHARACTER — Simon, the armored heavy tank of the team: the biggest, widest, strongest and
slowest hero. His body and face are IDENTICAL to HAGGAR from Final Fight — a massive, tall,
heavily-muscled brawler with a square jaw, a BIG BUSHY MOUSTACHE, and BALD on top with short
hair on the sides. Alien traits on top of Haggar: bright EGG-YOLK YELLOW skin, two long pointed
ELF EARS, and two straight thin ANTENNAE on the head (NO horns). He is clad in SAIYAN-STYLE
(Dragon Ball) battle armor: a sleeveless gunmetal-gray chest plate with large raised/spiked
shoulder guards and white plating, plus white armored gloves and white armored boots. He WIELDS
a large two-bladed MEDIEVAL battle axe (a long haft topped with a big heavy double-crescent steel
head — a wide curved blade on BOTH sides), carried in his hands or slung over one shoulder. Stern
tough face.

PROPORTION — THIS IS NON-NEGOTIABLE AND IS THE #1 THING TO GET RIGHT. Simon is the TALL, broad
HEAVY-HITTER of the team — imposing like a Final Fight brawler (Haggar). Draw him about 3.5 to 4
heads tall, with LONG strong legs, a thick muscular torso, and very broad blocky shoulders. His
head is slightly large for a heroic look (about ONE QUARTER of the total height) but it does NOT
dominate the figure. He is the biggest and widest hero — the bulk comes from height + width +
thick muscle. Keep the SAME art STYLE as the Oren reference (line work, warm rim light, HD
shading, 3/4 view facing right) but TALLER and broader — Simon is the one hero who is bigger
than Oren's chibi scale.

NEGATIVES (proportion — forbidden): NOT a dwarf, NOT a Lord-of-the-Rings dwarf, NOT chibi, NOT
stubby/short legs, NOT a squat compact body, NOT a gnome, NOT big-headed (head must NOT be 1/3
or more of the body). ALSO NOT the opposite error: NOT a skinny realistic 6-heads bodybuilder
and NOT a tall thin "hobbit". He is the TALL BROAD heavy: ~3.5–4 heads tall, LONG legs, head
~1/4 of height. Any frame that reads as a short stocky big-headed dwarf is WRONG — redraw it
TALLER with LONGER legs and a smaller relative head.

Use HIS OWN palette: yellow/gold skin, gunmetal-gray spiked armor, white gloves and boots
(NEVER orange tones — those belong to Oren), but with the exact same warm rim light, volumetric
shading and contrast treatment described in STYLE.
```

### Prompts por animação (Simon)

> Em cada um: **STYLE BLOCK + bloco de identidade do Simon + a linha abaixo**.

- **idle (7 frames)**
  `ANIMATION: idle, 7 frames as a horizontal strip. Heavy planted standing stance, weight on
  both legs, the big two-bladed axe resting over one shoulder. ALIVE, NOT a stiff statue: slow
  powerful breathing where the whole torso bobs up and down, the shoulders rise and settle, the
  head drifts a touch and the axe head dips slightly with the shoulder; weight shifts subtly
  foot to foot. Gentle squash-and-stretch on the breath. Identical cell size, feet aligned on
  the same baseline in every frame, transparent bg, no gaps/labels.`

- **walk (8 frames)**
  `ANIMATION: walk cycle, 8 frames horizontal strip, moving to the right. Slow, heavy, weighty
  stomp — LOOSE and alive, NOT a rigid puppet. The HIPS and TORSO swing/rock side to side and
  the shoulders counter-rotate against the hips (natural torso rotation of a heavy walk), with a
  clear up-and-down body bounce (rise on the passing pose, drop on each footfall). Each footfall
  lands with weight — the knee bends to absorb it, the mass settles, then pushes off. Big stride;
  the armor, spiked pauldrons and slung axe swing a beat late behind the body (follow-through/drag),
  body leaning slightly forward into the walk. Same cell size and same feet baseline in every
  frame. Transparent bg, no gaps/labels.`

- **ataque / attack (8 frames)**
  `ANIMATION: attack combo, 8 frames horizontal strip. Heavy two-bladed-axe combo — a crushing
  horizontal swing, an overhead smash into the ground, then a diagonal cleave. ALIVE, NOT stiff:
  every swing has ANTICIPATION (the body coils/loads back before it strikes), a fast snappy hit
  frame, and FOLLOW-THROUGH + overshoot (body and axe carry past the impact, then settle). Show
  weight transfer between the feet (push off the back foot into the strike, plant the front foot
  on impact) and let the torso TWIST into each swing; the heavy axe drags a frame behind the hands.
  Powerful and impactful, poses dynamic and off-balance during the action — never a row of upright
  statues holding an axe. Same cell size, feet baseline consistent, transparent bg, no gaps/labels.`

- **dash (4 frames)**
  `ANIMATION: dash, 4 frames horizontal strip, lunging to the right. Heavy shoulder-first charge
  leading with a spiked pauldron, low to the ground — DRIVE and momentum, NOT a stiff figure
  scooting sideways. The body leans HARD forward into the charge (~30°), weight thrown ahead of
  the feet so he reads as launching; strong push-off the back leg, big forward stride, torso
  committed and off-balance toward the right, the axe and arms lagging a beat behind from the
  speed. Slight speed-stretch of the body along the direction of motion. Same cell size,
  transparent bg, no gaps/labels.`

- **esquiva / backflip (4 frames)**
  `ANIMATION: backstep/dodge, 4 frames horizontal strip. A grounded heavy hop/roll backward
  (he is too massive for a flashy flip) — quick recoil away from danger. Same cell size,
  transparent bg, no gaps/labels.`

- **pulo / jump (5 frames)**
  `ANIMATION: jump, 5 frames horizontal strip: crouch, heavy push-off, apex, descend, land.
  Heavy arc, knees absorbing the landing. Same cell size, transparent bg, no gaps/labels.`

- **dano / hurt (4 frames)**
  `ANIMATION: hurt/recoil, 4 frames horizontal strip. Takes a hit and staggers back, but stays
  standing (he is the tank), armor taking the blow. Same cell size, transparent bg, no
  gaps/labels.`

- **morte / death (6 frames)**
  `ANIMATION: death, 6 frames horizontal strip: take final blow, stagger, drop to one knee,
  fall, collapse, lie defeated. Same cell size, transparent bg, no gaps/labels.`

- **tédio / idle_special (6 frames)**
  `ANIMATION: idle-special (bored taunt), 6 frames horizontal strip. He cracks his neck and
  knuckles, slams a fist into his open palm, and rolls his spiked shoulders with tough-guy
  attitude. Same cell size, feet baseline consistent, transparent bg, no gaps/labels.`

- **super / special (4–6 frames)**
  `ANIMATION: special super move "Galick Ho", 6 frames horizontal strip. He pulls both hands
  back cupped together at his side, charging a blinding yellow-electric energy orb (big windup),
  then thrusts both palms forward firing a massive horizontal yellow energy beam to the right
  (the beam is a SEPARATE sprite — here show only the charge, thrust and recoil poses). Same
  cell size, transparent bg, no gaps/labels.`

---

## 4. PINKI — a veloz (arquétipo Guy / Final Fight)

**Identidade (NÃO mude — derivada de `assets/sprites/herois/pinki/idle/pinki_idle_1.png`):** a
mais rápida do time, **glass cannon** (frágil, dano alto, ágil). É uma **coelha rosa** com **duas
orelhas longas CAÍDAS** (uma cai pra frente do ombro, a outra pra trás) e um **grande laço/fita
magenta no topo da cabeça** (detalhe icônico — não esquecer). Veste **regata magenta**, **calça
preta larga de luta**, **faixas/wraps roxas nos pulsos e tornozelos**, sapatilhas. Expressão
confiante/atrevida. Arma = **nunchaku** (cabos de madeira com corrente). Magra e atlética, mas na
MESMA proporção heroica do Oren (não esticar pra anime alto).

> ⚠️ Correção da Pinki: a arte atual está de **frente** e com tratamento mais flat. Vire pra **3/4
> direita** e aplique o **rim light laranja quente + sombreamento volumétrico** do STYLE BLOCK.
> A identidade (coelha rosa, laço magenta, orelhas caídas, regata + calça preta + wraps roxas,
> nunchaku) já está certa — o que muda é ângulo + luz + acabamento HD.

**Bloco de identidade da Pinki** (cole logo após o STYLE BLOCK em todos os prompts dela):

```
CHARACTER — Pinki, the fastest hero, an agile glass-cannon brawler. A stylized pink bunny-girl
fighter: pink fur, a confident smirk, and TWO LONG FLOPPY rabbit ears (one draping forward over
a shoulder, one back). She wears a BIG magenta BOW on top of her head (iconic — always present).
Outfit: magenta tank top, loose black martial-arts pants, purple wrist wraps and purple ankle
wraps, light shoes. Lean and athletic, light on her feet — but STILL in the same 2.5-3 head
heroic proportion as the rest of the team (NOT a tall slim anime figure). She wields a pair of
NUNCHAKU (wooden handles joined by a chain). Keep HER OWN pink/magenta + purple palette, but
apply the exact same warm rim light, volumetric shading and contrast treatment described in STYLE.
```

### Prompts por animação (Pinki)

> Em cada um: **STYLE BLOCK + bloco de identidade da Pinki + a linha abaixo**.

- **idle (7 frames)**
  `ANIMATION: idle, 7 frames horizontal strip. Light bouncy fighting stance, ready and alert,
  nunchaku resting, subtle weight shift, the floppy ears and the magenta bow bobbing slightly.
  Identical cell size, feet on the same baseline every frame, transparent bg, no gaps/labels.`

- **walk (8 frames)**
  `ANIMATION: walk cycle, 8 frames horizontal strip, moving right. Quick, light, agile steps,
  springy gait. Same cell size and same feet baseline in every frame. Transparent bg,
  no gaps/labels.`

- **ataque / attack (8 frames)**
  `ANIMATION: attack combo, 8 frames horizontal strip. Fast flurry of nunchaku strikes — quick
  successive hits, agile and snappy, short reach but rapid. Same cell size, feet baseline
  consistent, transparent bg, no gaps/labels.`

- **dash (4 frames)**
  `ANIMATION: dash, 4 frames horizontal strip, darting to the right. Fast low sprint-dash, the
  long floppy ears and bow ribbons streaming back from the speed. Same cell size, transparent bg,
  no gaps/labels.`

- **esquiva / backflip (4 frames)**
  `ANIMATION: backflip dodge, 4 frames horizontal strip. Agile acrobatic backflip away from
  danger (she IS nimble). Same cell size, transparent bg, no gaps/labels.`

- **pulo / jump (5 frames)**
  `ANIMATION: jump, 5 frames horizontal strip: crouch, spring up, apex, descend, light land.
  High nimble arc. Same cell size, transparent bg, no gaps/labels.`

- **dano / hurt (4 frames)**
  `ANIMATION: hurt/recoil, 4 frames horizontal strip. Takes a hit and reels back hard (she is
  fragile, big recoil). Same cell size, transparent bg, no gaps/labels.`

- **morte / death (6 frames)**
  `ANIMATION: death, 6 frames horizontal strip: hit, stagger, knees buckle, fall, collapse,
  lie defeated. Same cell size, transparent bg, no gaps/labels.`

- **tédio / idle_special (6 frames)**
  `ANIMATION: idle-special (bored taunt), 6 frames horizontal strip. She twirls the nunchaku
  with flair, flicks an ear and adjusts the magenta bow, cocky confident smirk. Same cell size,
  feet baseline consistent, transparent bg, no gaps/labels.`

- **super / special (4–6 frames)**
  `ANIMATION: special super move, 6 frames horizontal strip. A rapid spinning nunchaku flurry
  finisher (multi-hit whirl pose), her signature fast combo. Same cell size, transparent bg,
  no gaps/labels.`

---

## 5. WENDA — a equilibrada (arquétipo Blaze / Streets of Rage 4)

**Identidade (NÃO mude — derivada de `assets/sprites/herois/wenda/wenda_idle.png`):** lutadora
**equilibrada e especialista em combo**, ágil. É uma **gata branca** — orelhas felinas brancas no
topo da cabeça, **cauda branca** longa, **cabelo branco/prateado bagunçado** caindo sobre o rosto.
Vibe **punk-rock de rua**: **jaqueta de couro preta** (estilo motoqueira, gola larga), camiseta
escura com pequena estampa no peito, **corrente metálica enrolada num braço** (do ombro à mão —
parte do visual e que ela usa em golpes), **calça preta rasgada/desgastada**, **cinto largo**,
**coturnos pretos**. Sorriso confiante. Atlética e equilibrada, na MESMA proporção heroica do Oren.

> ⚠️ A arte WIP da Wenda está de **frente** (folha de poses em fundo verde, lineart limpo). Vire
> pra **3/4 direita** e aplique o **rim light laranja quente + sombreamento volumétrico** do
> STYLE BLOCK. A corrente no braço e a cauda são identidade — sempre presentes.

**Bloco de identidade da Wenda** (cole logo após o STYLE BLOCK em todos os prompts dela):

```
CHARACTER — Wenda, the balanced combo-specialist hero, agile and well-rounded. A stylized white
CAT-girl fighter: white cat ears on top of her head, a long white tail, messy white/silver hair
falling over one eye, confident smirk. Punk street-rocker outfit: black leather biker jacket with
a wide collar, dark t-shirt with a small chest print, a metal CHAIN wrapped around one arm from
shoulder to hand (her signature, also used in strikes), distressed ripped black pants, a wide
belt, black combat boots. Athletic and balanced, in the same 2.5-3 head heroic proportion as the
team. Keep HER OWN monochrome white-and-black palette with steel chain accents, but apply the
exact same warm rim light, volumetric shading and contrast treatment described in STYLE.
```

### Prompts por animação (Wenda)

> Em cada um: **STYLE BLOCK + bloco de identidade da Wenda + a linha abaixo**.

- **idle (7 frames)**
  `ANIMATION: idle, 7 frames horizontal strip. Loose confident fighting stance, weight shifting,
  the chain on her arm swaying slightly, tail and hair moving subtly. Identical cell size, feet on
  the same baseline every frame, transparent bg, no gaps/labels.`

- **walk (8 frames)**
  `ANIMATION: walk cycle, 8 frames horizontal strip, moving right. Smooth confident stride, tail
  counter-balancing, easygoing rhythm. Same cell size and same feet baseline in every frame.
  Transparent bg, no gaps/labels.`

- **ataque / attack (8 frames)**
  `ANIMATION: attack combo, 8 frames horizontal strip. A flowing martial-arts combo mixing fast
  punches/kicks and a chain-whip swing — fluid linked hits, combo specialist. Same cell size, feet
  baseline consistent, transparent bg, no gaps/labels.`

- **dash (4 frames)**
  `ANIMATION: dash, 4 frames horizontal strip, darting right. Quick agile forward dash, hair and
  tail streaming back. Same cell size, transparent bg, no gaps/labels.`

- **esquiva / backflip (4 frames)**
  `ANIMATION: backflip dodge, 4 frames horizontal strip. Agile acrobatic backflip away from danger,
  cat-like landing. Same cell size, transparent bg, no gaps/labels.`

- **pulo / jump (5 frames)**
  `ANIMATION: jump, 5 frames horizontal strip: crouch, spring up, apex, descend, light cat landing.
  Same cell size, transparent bg, no gaps/labels.`

- **dano / hurt (4 frames)**
  `ANIMATION: hurt/recoil, 4 frames horizontal strip. Takes a hit and reels back, then recovers her
  stance. Same cell size, transparent bg, no gaps/labels.`

- **morte / death (6 frames)**
  `ANIMATION: death, 6 frames horizontal strip: hit, stagger, knees buckle, fall, collapse, lie
  defeated. Same cell size, transparent bg, no gaps/labels.`

- **tédio / idle_special (6 frames)**
  `ANIMATION: idle-special (bored taunt), 6 frames horizontal strip. She uncoils and spins the arm
  chain, flicks her hair, the tail flicks with attitude, cool confident smirk. Same cell size,
  feet baseline consistent, transparent bg, no gaps/labels.`

- **super / special (4–6 frames)**
  `ANIMATION: special super move, 6 frames horizontal strip. A whirling chain-and-kick flurry
  finisher (multi-hit spinning combo pose), her signature combo. Same cell size, transparent bg,
  no gaps/labels.`

---

## 6. GARNOLD — o alcance elétrico (arquétipo Dr. Zan / SoR2)

**Identidade (NÃO mude — derivada de `assets/sprites/inimigos_f2/garnold_f2.png` e
`assets/sprites/herois/OLD/garnold.png`):** o de **maior alcance** do time via **ataques
elétricos**, **lento**, com **braços que se estendem** — vibe **ciborgue**. Visual: figura humanoide
num **traje pesado amarelo** integral (tipo macacão de proteção / traje espacial-industrial
acolchoado, com vincos e juntas marcadas), **cabeça coberta por capacete/visor escuro** (rosto não
aparece, só o visor). Dos braços/punhos saem **descargas elétricas azul-ciano** brilhantes (raios /
plasma) — é o efeito-assinatura. Pesadão, ombros largos, andar arrastado. Proporção heroica do Oren.

> ⚠️ A arte de referência do Garnold está em **3/4 já virada (boa base)** mas em estilo mais flat e
> em paleta de inimigo. Como HERÓI ele mantém o traje amarelo + visor + raios ciano, mas com o
> **rim light laranja + sombreamento volumétrico HD** do STYLE BLOCK. Os **raios azul-ciano** são
> identidade — sempre nos ataques/super.

**Bloco de identidade do Garnold** (cole logo após o STYLE BLOCK em todos os prompts dele):

```
CHARACTER — Garnold, the long-range electric cyborg of the team: slow but huge reach, with arms
that extend and crackle with electricity. A humanoid figure in a heavy full-body YELLOW suit
(padded industrial / spacesuit-like coverall with visible seams and joints), broad shoulders, and
a HELMET with a dark visor instead of a visible face. His fists and forearms emit bright blue-cyan
ELECTRIC arcs / plasma (his signature). Bulky and heavy, in the same 2.5-3 head heroic proportion
as the team. Keep HIS OWN yellow suit + dark visor + cyan electricity palette, but apply the exact
same warm rim light, volumetric shading and contrast treatment described in STYLE.
```

### Prompts por animação (Garnold)

> Em cada um: **STYLE BLOCK + bloco de identidade do Garnold + a linha abaixo**.

- **idle (7 frames)**
  `ANIMATION: idle, 7 frames horizontal strip. Heavy grounded stance, slow mechanical breathing,
  faint cyan sparks flickering around the fists. Identical cell size, feet on the same baseline
  every frame, transparent bg, no gaps/labels.`

- **walk (8 frames)**
  `ANIMATION: walk cycle, 8 frames horizontal strip, moving right. Slow heavy trudging steps, the
  bulky suit swaying with the mass. Same cell size and same feet baseline in every frame.
  Transparent bg, no gaps/labels.`

- **ataque / attack (8 frames)**
  `ANIMATION: attack combo, 8 frames horizontal strip. He EXTENDS an arm forward releasing a long
  blue-cyan electric blast/whip with extreme reach — windup, extended electric strike, recoil.
  Slow but huge range. Same cell size, feet baseline consistent, transparent bg, no gaps/labels.`

- **dash (4 frames)**
  `ANIMATION: dash, 4 frames horizontal strip, lunging right. A short heavy mechanical lunge,
  cyan sparks trailing. Same cell size, transparent bg, no gaps/labels.`

- **esquiva / backflip (4 frames)**
  `ANIMATION: backstep/dodge, 4 frames horizontal strip. A grounded heavy hop backward (too bulky
  for a flip), sparks crackling. Same cell size, transparent bg, no gaps/labels.`

- **pulo / jump (5 frames)**
  `ANIMATION: jump, 5 frames horizontal strip: crouch, heavy push-off, apex, descend, heavy land.
  Same cell size, transparent bg, no gaps/labels.`

- **dano / hurt (4 frames)**
  `ANIMATION: hurt/recoil, 4 frames horizontal strip. Takes a hit and staggers, the suit and visor
  flickering, but stays standing. Same cell size, transparent bg, no gaps/labels.`

- **morte / death (6 frames)**
  `ANIMATION: death, 6 frames horizontal strip: take final blow, electric short-circuit sparks,
  stagger, drop, collapse, lie defeated with fading cyan sparks. Same cell size, transparent bg,
  no gaps/labels.`

- **tédio / idle_special (6 frames)**
  `ANIMATION: idle-special (bored taunt), 6 frames horizontal strip. He flexes his arms and arcs
  electricity between his two fists, the visor glowing brighter for a beat. Same cell size, feet
  baseline consistent, transparent bg, no gaps/labels.`

- **super / special (4–6 frames)**
  `ANIMATION: special super move, 6 frames horizontal strip. Both arms extend and unleash a massive
  forked blue-cyan lightning discharge across a wide range (charge, full extension, blast, recoil),
  his signature long-range electric super. Same cell size, transparent bg, no gaps/labels.`

---

## 7. FUNBOT — o grappler robô (arquétipo Floyd / SoR3)

**Identidade (NÃO mude — derivada de `assets/sprites/inimigos_f2/funbot_f2.png` e
`assets/sprites/herois/OLD/funbot.png`):** **o mais lento e o maior HP** do time, **pancada pesada**
e **GRAPPLER** (agarra e arremessa). É literalmente um **robô** ("Fun Bot"). Visual: corpo de
**metal prateado/aço** robusto e arredondado, ombros e antebraços grandes (braços de agarrar), uma
**cabeça redonda com visor horizontal ciano brilhante** (a "cara" do robô), **duas pequenas antenas
de ponta amarela** no topo. Sem rosto orgânico — expressão vem do brilho do visor. Pés/juntas
mecânicas. Pesadão, na MESMA proporção heroica do Oren (não um humano — um robô atarracado e forte).

> ⚠️ Existem duas referências: a OLD (aço escovado, super maciça, ótima massa) e a f2 (prata mais
> limpa, visor ciano marcante, antenas amarelas). Funda as duas: a **massa/peso da OLD** + o **visor
> ciano e antenas da f2**. Como herói, aplique o **rim light laranja + sombreamento volumétrico HD**.

**Bloco de identidade do FunBot** (cole logo após o STYLE BLOCK em todos os prompts dele):

```
CHARACTER — FunBot, a heavy grappler ROBOT: the slowest hero with the highest HP, huge powerful
punches, grabs and throws. A bulky rounded silver/steel robot body with big shoulders and large
gripping forearms, a round head with a glowing horizontal CYAN visor as its face, and two small
antennas with yellow tips on top. No organic face — its expression comes from the cyan visor glow.
Mechanical joints and feet. Heavy and stocky, in the same 2.5-3 head heroic proportion as the team
(a stout strong robot, not a human). Keep HIS OWN brushed-steel/silver body + cyan visor + yellow
antenna-tip palette, but apply the exact same warm rim light, volumetric shading and contrast
treatment described in STYLE.
```

### Prompts por animação (FunBot)

> Em cada um: **STYLE BLOCK + bloco de identidade do FunBot + a linha abaixo**.

- **idle (7 frames)**
  `ANIMATION: idle, 7 frames horizontal strip. Heavy planted robot stance, very slow servo idle
  motion, the cyan visor pulsing faintly. Identical cell size, feet on the same baseline every
  frame, transparent bg, no gaps/labels.`

- **walk (8 frames)**
  `ANIMATION: walk cycle, 8 frames horizontal strip, moving right. Very slow heavy mechanical stomp,
  big metal strides, body swaying from the weight. Same cell size and same feet baseline in every
  frame. Transparent bg, no gaps/labels.`

- **ataque / attack (8 frames)**
  `ANIMATION: attack combo, 8 frames horizontal strip. Heavy slow piston-punch combo with the big
  forearms — windup, massive impact punch, follow-through. Powerful and weighty. Same cell size,
  feet baseline consistent, transparent bg, no gaps/labels.`

- **dash (4 frames)**
  `ANIMATION: dash, 4 frames horizontal strip, charging right. A heavy shoulder-first mechanical
  charge, low to the ground. Same cell size, transparent bg, no gaps/labels.`

- **esquiva / backflip (4 frames)**
  `ANIMATION: backstep/dodge, 4 frames horizontal strip. A heavy mechanical hop backward (too heavy
  for a flip), servos compensating. Same cell size, transparent bg, no gaps/labels.`

- **pulo / jump (5 frames)**
  `ANIMATION: jump, 5 frames horizontal strip: crouch with servo compression, heavy push-off, apex,
  descend, heavy metal land. Same cell size, transparent bg, no gaps/labels.`

- **dano / hurt (4 frames)**
  `ANIMATION: hurt/recoil, 4 frames horizontal strip. Takes a hit, sparks fly and the visor flickers,
  staggers but stays standing (high HP tank). Same cell size, transparent bg, no gaps/labels.`

- **morte / death (6 frames)**
  `ANIMATION: death, 6 frames horizontal strip: take final blow, sparks and short-circuit, stagger,
  power down, collapse, lie inert with the visor going dark. Same cell size, transparent bg,
  no gaps/labels.`

- **agarrar / grapple (extra — grappler)**
  `ANIMATION: grab/throw, 6 frames horizontal strip: lunge and clamp both forearms onto the target,
  lift it, then slam/throw it forward. His signature grappler move. Same cell size, feet baseline
  consistent, transparent bg, no gaps/labels.`

- **tédio / idle_special (6 frames)**
  `ANIMATION: idle-special (bored taunt), 6 frames horizontal strip. It cracks its mechanical
  knuckles, the visor flashes a cheerful pattern, antennas wiggle. Same cell size, feet baseline
  consistent, transparent bg, no gaps/labels.`

- **super / special (4–6 frames)**
  `ANIMATION: special super move, 6 frames horizontal strip. A massive two-fisted ground-slam
  (huge windup, overhead, impact shockwave pose), its signature heavy grappler finisher. Same cell
  size, transparent bg, no gaps/labels.`

---

## 8. GRAY — o NPC (lento, passivo, cabeçada)

**Identidade (NÃO mude — derivada de `assets/sprites/herois/gray/gray_idle.png` e
`gray_portrait.png`):** **NPC** (não-jogável), **lento e passivo**, só reage com uma **cabeçada**
quando algo chega perto. É uma **personagem coelha/cachorro cinza melancólica**: **orelhas longas
caídas** (penduradas dos lados da cabeça, estilo lop), **franja/cabelo cinza-claro** sobre os olhos,
**focinho pequeno**, **expressão triste/apática** (olhos pesados, boca neutra). Veste **moletom/hoodie
cinza folgado com bolso canguru e cordões**, **leggings/calça escura**, **botas escuras**. **Paleta
monocromática em tons de cinza** (sem cores vivas — é deliberadamente apagada). Postura encolhida.

> ⚠️ Diferenças vs herói: (1) o Gray tem um **conjunto de animação MENOR** — só o mínimo coerente
> pra um NPC passivo; (2) o estilo da arte dele é **cartoon-anime de lineart preto limpo** (mais
> simples que os heróis). Ainda assim, **aplique o STYLE BLOCK** (3/4 direita, rim light, fundo
> transparente, proporção do Oron) para casar com o time em tela — mantendo a paleta cinza e a vibe
> melancólica. A cabeçada é o único ataque.

**Conjunto de animações do Gray (reduzido — NPC):**

| Animação | Frames | Por quê |
|----------|:------:|---------|
| idle | 7 | parado, melancólico, respiração mínima |
| walk | 8 | andar lento e arrastado |
| ataque (cabeçada / headbutt) | 6 | o único ataque — recua a cabeça e dá a cabeçada |
| dano (hurt) | 4 | recuo de impacto |
| morte (death) | 6 | cambaleia → cai → deitado |

> Sem dash, sem backflip, sem pulo, sem super: ele é passivo e lento. Se o jogo precisar de um
> "react/flinch" ele já é coberto pelo hurt.

**Bloco de identidade do Gray** (cole logo após o STYLE BLOCK em todos os prompts dele):

```
CHARACTER — Gray, a slow passive NPC (non-playable). A melancholic gray bunny/dog character: long
floppy lop ears hanging down the sides of the head, light-gray bangs over the eyes, a small muzzle,
heavy tired eyes and a neutral sad mouth (apathetic, gloomy expression). Outfit: an oversized gray
hoodie with a kangaroo pocket and drawstrings, dark leggings/pants, dark boots. Slightly hunched,
low-energy posture. Entirely MONOCHROME grayscale palette — no bright colors, deliberately muted.
In the same 2.5-3 head heroic proportion as the team so he reads at the same on-screen scale.
Apply the warm rim light, volumetric shading and contrast treatment from STYLE (keep the gray
palette — the rim light is the only warm accent).
```

### Prompts por animação (Gray)

> Em cada um: **STYLE BLOCK + bloco de identidade do Gray + a linha abaixo**.

- **idle (7 frames)**
  `ANIMATION: idle, 7 frames horizontal strip. Hunched passive standing, slow tired breathing,
  ears drooping, gloomy. Subtle motion only. Identical cell size, feet on the same baseline every
  frame, transparent bg, no gaps/labels.`

- **walk (8 frames)**
  `ANIMATION: walk cycle, 8 frames horizontal strip, moving right. Slow shuffling reluctant steps,
  low energy, ears swaying. Same cell size and same feet baseline in every frame. Transparent bg,
  no gaps/labels.`

- **ataque / cabeçada / headbutt (6 frames)**
  `ANIMATION: headbutt attack, 6 frames horizontal strip. He leans his head back then thrusts a
  short forward HEADBUTT (his only attack — close range), then returns to stance. Slow and clumsy.
  Same cell size, feet baseline consistent, transparent bg, no gaps/labels.`

- **dano / hurt (4 frames)**
  `ANIMATION: hurt/recoil, 4 frames horizontal strip. Takes a hit and flinches back, ears flapping
  from the impact. Same cell size, transparent bg, no gaps/labels.`

- **morte / death (6 frames)**
  `ANIMATION: death, 6 frames horizontal strip: hit, stagger, knees buckle, fall, collapse, lie
  down defeated. Same cell size, transparent bg, no gaps/labels.`

---

## 9. MOLDE reaproveitável (para os demais heróis)

Para qualquer herói novo, monte o prompt assim:

```
[ STYLE BLOCK da seção 1 — copiado igual, sem mudar nada ]

CHARACTER — <nome>, <arquétipo em 1 frase>. <silhueta/roupa/arma em 1-2 frases>.
Keep HIS/HER OWN <paleta> palette, but apply the exact same warm rim light, volumetric
shading and contrast treatment described in STYLE. Same 2.5-3 head heroic proportion as Oren.

ANIMATION: <nome da anim>, <N> frames horizontal strip, <descrição do movimento>.
Identical cell size, feet on the same baseline every frame, transparent bg, no gaps/labels.
```

Só troca o bloco CHARACTER e a linha ANIMATION. STYLE BLOCK e regras de spritesheet ficam fixos.

---

## 10. Dicas de FIDELIDADE (Gemini infiel × Copilot fiel-mas-fraco)

**Gemini "Nano Banana" (qualidade alta, anda infiel):**
- Repita o que NÃO pode mudar no fim do prompt: termine com
  `STRICT: 3/4 side view facing right, transparent background, single character, 2.5-3 head
  heroic proportion, warm orange rim light. Do not change these.`
- Se ele inventar fundo/sombra/ângulo: gere **frame a frame** em vez da tira inteira (menos
  liberdade = mais fidelidade) e monte a spritesheet depois.
- Dê o Oren como **imagem de referência** quando a ferramenta permitir ("match this style **and
  this proportion**"). **Para o Simon, anexe `assets/sprites/herois/oren/idle/idle_01.png` como
  âncora de proporção** e escreva `match the head-to-body proportion of this reference exactly`.
- Negative-ish (escreva como proibição): `NO flat retro look, NO realistic anatomy, NO small head,
  NO 4/5/6-head proportion, NO tall adult body, NO long legs, NO front view, NO background,
  NO ground shadow, NO text/numbers, NO multiple characters.`

**Copilot (fiel, mas qualidade menor):**
- Puxe a qualidade explicitamente: prefixe com `high quality, highly detailed, polished
  game-ready sprite, crisp clean pixels, professional pixel art`.
- Peça **resolução grande** (gera mais detalhe; reduz/limpa depois). Ex: pessoa pede o frame
  grande e faz downscale nearest-neighbor.
- Use o Copilot quando a fidelidade for crítica (ângulo/proporção) e o Gemini quando quiser o
  acabamento — depois padronize tudo pra casar.

**Pós-geração (sempre):**
- Fundo 100% transparente (remover qualquer fundo que escapou).
- Recortar/alinhar pés na mesma linha de base; mesmo tamanho de célula na tira.
- Aplicar a mesma "limpeza" de pixel (nearest-neighbor) que o Oren tem.

---

## 11. CHECKLIST FINAL (gate — não pule)

- [ ] Cada animação é **tira horizontal**, células de **tamanho idêntico**, divide exato pelo frame.
- [ ] **3/4 virado pra direita**, fundo **transparente**, **1 personagem** por frame.
- [ ] **Proporção do Oren** (2.5–3 cabeças, cabeça ≈ 1/3 do corpo) — ninguém realista, ninguém
      esticado/adulto-alto. **SIMON em especial:** lado a lado com `oren/idle/idle_01.png` a cabeça
      tem o MESMO tamanho relativo e a altura total é a MESMA escala. Cabeça pequena / corpo alto = REPROVADO, regere.
- [ ] **Rim light laranja + sombreamento volumétrico** presentes (casa com o Oren).
- [ ] Identidade preservada por personagem: **Simon = tank brutamontes amarelo de armadura cinza
      com ombreiras de espinhos, punhos blindados (SEM pé-de-cabra)**; **Pinki = coelha rosa, laço
      magenta, orelhas caídas, nunchaku**; **Wenda = gata branca, jaqueta de couro, corrente no
      braço, cauda**; **Garnold = traje amarelo + visor escuro + raios ciano**; **FunBot = robô
      prata, visor ciano, antenas amarelas, grappler**; **Gray = coelha cinza melancólica de
      hoodie, cabeçada, paleta monocromática**.
- [ ] Pés alinhados na mesma base em todos os frames de cada animação.
- [ ] Contagem de frames bate com a tabela da seção 2 (Gray usa o conjunto REDUZIDO da seção 8).
- [ ] **Frame em tamanho do Oren (~200–256px de altura), NÃO gigante.** Gerou grande? Downscale nearest antes de salvar.
- [ ] **Rodou `npm run check:sprites` e passou (código 0).** ← obrigatório antes de aceitar.

> Se o validador reprovar tamanho/encolher/duplicar: ajuste o asset (ou o `animScales` em
> `js/config/index.js`, fonte única) e rode de novo. Sprite só está "pronto" com o validador verde.
