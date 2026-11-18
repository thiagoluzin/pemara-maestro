[⬅ Voltar ao Painel de Produção](../00_PAINEL.md)

---

## 1-A: SIMON

> ⛔ **REFERÊNCIA DIRETA — simplifica TUDO (resolve o tamanho de uma vez).** Simon = **o HAGGAR do
> Final Fight, versão alienígena.** Desenhe o **físico e o porte IDÊNTICOS ao Haggar**: brutamontes
> ENORME e ALTO, ombros larguíssimos, peito e braços maciços, pescoço grosso, mandíbula quadrada,
> **bigode grosso**, **careca no topo com cabelo curto nas laterais**. Alto e musculoso — **NUNCA um
> anão**. As 3 features alien que o diferenciam do Haggar: **pele AMARELO-GEMA**, **orelhas de ELFO
> pontudas** e **antenas** (SEM chifres). Roupa = **armadura saiyajin** (estilo Dragon Ball).
> Arma = **machado medieval de duas lâminas**. Só isso — repita esse físico-Haggar em TODO frame.

**Bloco de design (copiar no início de cada prompt do Simon):**
> *Character reference: a HUGE muscular alien brawler whose **body and face are IDENTICAL to Haggar
> from Final Fight** — enormous, tall, heavily-muscled physique, very broad shoulders, massive chest
> and arms, thick neck, square jaw, a **big bushy moustache**, **bald on top with short hair on the
> sides**. Alien traits added on top of Haggar: **skin is bright EGG-YOLK YELLOW** (saturated postal-
> worker yellow), **two long pointed ELF EARS**, and **two straight thin antennae** rising from the
> head — **NO horns**. He wears **Saiyan-style battle armor (Dragon Ball style): a sleeveless armored
> chest plate with raised shoulder guards**, in **gunmetal / steel gray with white plating**, plus
> **white armored gloves and white armored boots**. **Signature weapon: a large two-bladed MEDIEVAL
> battle axe — a long dark haft topped with a big heavy double-crescent steel head (a wide curved
> blade on BOTH sides), worn and battle-scarred, big and heavy; carried in his hand or slung over one
> shoulder.** Mature, tough, confident expression. Authentic 16-bit SNES pixel-art style (Final Fight
> 3), same craft/shading as the Oren sprites. No anti-aliasing.*
>
> **NEGATIVES:** *NOT a dwarf, NOT chibi, NOT short or stubby-legged — he is as TALL and MASSIVE as
> Haggar. **NO horns** (use elf ears + antennae). Skin is egg-yolk YELLOW — NOT pale, NOT brown, NOT
> orange, NOT pink/magenta; no warm/red global color cast. Armor is **Saiyan/Dragon-Ball style, NOT a
> medieval knight suit** — but the AXE stays medieval. The body must NEVER read as a small big-headed
> gnome.*
>
> 🖼️ **TAMANHO NO FRAME:** the character FILLS the cell — feet near the bottom edge, head near the top edge, only a small uniform margin. He occupies ~85–90% of the 128px height. NOT a small figure floating in empty space.

> 🧩 **PADRÃO DE DIVISÃO (pra recorte sem dor de cabeça).** Folha com muitos frames faz a IA **GRUDAR** os personagens (o machado de um invade o vizinho — foi o que aconteceu no idle). Por isso as ações longas estão **quebradas em prompts curtos**: o **combo vira 1 prompt por golpe** (Hit 1 / Hit 2 / Hit 3) e o **walk vira 2 meias-passadas**. Gere um de cada vez. ⚓ **Âncora de consistência:** ao gerar partes da MESMA animação, mantenha **mesma escala, mesmo tamanho de cabeça, mesma linha dos pés (baseline) e mesma proporção** em todas as partes, senão os frames não casam quando juntados na engine.

---

### 1-A.1 SIMON — idle (7 frames = 896×128)

> 16-bit pixel art horizontal sprite sheet, 7 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Standing breathing idle cycle — **alive, NOT a stiff statue**. The axe rests over his right shoulder, gripped loosely — the natural stance of someone who has been carrying it for a long time. **The whole torso bobs gently up and down with the breath, shoulders rising and settling, the head drifting a touch, the axe head dipping slightly with the shoulder.** Weight shifts subtly foot to foot. There is squash-and-stretch in the breathing (chest expands then relaxes) — never a rigid frozen pose. The power and mass of the character must be felt even at rest, but he must read as a living body with weight, not a mannequin.
>
> ⛔ Haggar-from-Final-Fight build in EVERY frame: enormous, TALL, heavily muscled — NOT a dwarf, NOT chibi, NOT stubby-legged. Elf ears + antennae (NO horns), Saiyan armor, egg-yolk-yellow skin, medieval axe.
>
> Total: 896×128. No anti-aliasing.

---

### 1-A.2a SIMON — walk · primeira metade (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.** [Character reference above.]
>
> ⚓ **CONSISTÊNCIA:** same scale, same head size, same feet baseline and same body proportions as the "walk · segunda metade" strip — the two halves must join into ONE smooth 8-frame walk cycle.
>
> Animation: **FIRST half of a heavy walk cycle**, side-view facing right — loose and weighty, NEVER a rigid puppet. The axe is slung over his right shoulder, swinging slightly. The HIPS and TORSO rock side to side and the shoulders counter-rotate against the hips. Clear up-and-down bounce. Frame 1: **left-foot contact** (left foot forward planted, weight landing, knee absorbing). Frame 2: **down/passing** (back foot passing under the body, lowest bounce). Frame 3: **push-off rise** (rising onto the ball of the back foot). Frame 4: **right-foot reach** (right foot swinging forward to plant). Axe/arms drag a frame behind the body.
>
> ⛔ Haggar-from-Final-Fight build in EVERY frame: enormous, TALL, heavily muscled — NOT a dwarf, NOT chibi, NOT stubby-legged. Elf ears + antennae (NO horns), Saiyan armor, egg-yolk-yellow skin, medieval axe.
>
> Total: 512×128. No anti-aliasing.

---

### 1-A.2b SIMON — walk · segunda metade (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.** [Character reference above.]
>
> ⚓ **CONSISTÊNCIA:** same scale, same head size, same feet baseline and same body proportions as the "walk · primeira metade" strip — these are frames 5–8 of the SAME cycle (mirror of the first half).
>
> Animation: **SECOND half of the heavy walk cycle** (mirror of the first), side-view facing right. Frame 1 (=frame 5): **right-foot contact** (right foot forward planted, weight landing). Frame 2 (=6): **down/passing** (lowest bounce). Frame 3 (=7): **push-off rise**. Frame 4 (=8): **left-foot reach** (swinging forward to plant, returning to the start of the cycle). Same hip/torso rock, same bounce height, axe/arms dragging a frame behind.
>
> ⛔ Haggar-from-Final-Fight build in EVERY frame: enormous, TALL, heavily muscled — NOT a dwarf, NOT chibi, NOT stubby-legged. Elf ears + antennae (NO horns), Saiyan armor, egg-yolk-yellow skin, medieval axe.
>
> Total: 512×128. No anti-aliasing.

---

### 1-A.3 SIMON — ataques / combo — **dividido em 3 golpes** (gere os 3 strips abaixo)

> ⚓ **CONSISTÊNCIA (vale pros 3 golpes):** same scale, same head size, same feet baseline and same body proportions across Hit 1 / Hit 2 / Hit 3 — they chain into one combo in the engine. Axe = large two-bladed MEDIEVAL battle axe (double-crescent steel head), visible in EVERY frame. FULL BODY head-to-toe, both feet on the baseline, facing right.
> ⛔ Haggar (Final Fight) build em todos: enorme, ALTO, musculoso, pernas longas — NOT dwarf/chibi/stubby. Elf ears + antennae (NO horns), Saiyan armor, egg-yolk-yellow skin.
> 🌀 **MAKE IT ALIVE:** anticipation (coil back) → fast snappy hit frame → follow-through/overshoot. Weight transfer between the feet, torso TWIST into the swing, heavy axe dragging a frame behind. NOT stiff statues.

**1-A.3a — Hit 1: Horizontal Swing (2 frames = 256×128)**
> 16-bit pixel art horizontal sprite sheet, 2 frames, 128×128 each, solid neon green (#00FF00) bg. **Wide green gap between frames — must NOT touch.** [Character reference above.] [Consistência + proporção acima.]
> Frame 1: **Wind-up.** Right foot stepping forward to the right. Right hand gripping the axe haft, pulling it BACK and to the left — axe raised behind his left shoulder, pointing backward-left. Left arm forward for counterbalance. Body coiling right. Both feet down.
> Frame 2: **Swing — hit frame.** Right arm swinging the axe horizontally LEFT→RIGHT at waist/chest height — axe fully extended RIGHT, haft horizontal, heavy double blade leading, short motion-blur streak behind it. Left arm pulled back. Right foot planted forward. Torso twisting right.
> Total: 256×128. No anti-aliasing.

**1-A.3b — Hit 2: Overhead Smash (3 frames = 384×128)**
> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) bg. **Wide green gap between frames — must NOT touch.** [Character reference above.] [Consistência + proporção acima.]
> Frame 1: **Lift.** Both feet planted wide. Both hands on the axe (right on the shaft, left on the lower grip). Axe rising from chest height upward. Body straightening.
> Frame 2: **Peak.** Both hands holding the axe fully ABOVE his head — axe pointing straight up, arms overhead. Body tensing, knees slightly bent loading the downswing. Head facing right.
> Frame 3: **Smash — hit frame.** Both hands swinging the axe STRAIGHT DOWN, crashing into the ground in front of his feet — axe pointing straight DOWN, arms extended downward, heavy double blade biting the floor. Dust/shockwave burst at impact. Body leaning forward from the force.
> Total: 384×128. No anti-aliasing.

**1-A.3c — Hit 3: Diagonal Cleave (3 frames = 384×128)**
> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) bg. **Wide green gap between frames — must NOT touch.** [Character reference above.] [Consistência + proporção acima.]
> Frame 1: **Re-grip.** Both hands gripping the axe, raising it high over the right shoulder — heavy double blade cocked up and behind him, loading a diagonal downward swing. Body turning slightly.
> Frame 2: **Cleave — hit frame.** Both arms swinging the axe diagonally down-forward to the RIGHT — heavy double blade leading, cleaving toward the enemy. Yellow electrical spark burst where the blade bites. Body twisting hard into the swing.
> Frame 3: **Follow-through.** Arms completing the diagonal arc, axe passing the hit point. Body returning to upright stance, facing right. Axe swinging back toward the shoulder-carry position.
> Total: 384×128. No anti-aliasing.

---

### 1-A.4 SIMON — ataque_fuga / escape attack (3 frames = 384×128)

> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ **CORPO COMPLETO OBRIGATÓRIO:** Full body head to toe in every frame. Feet on the bottom baseline. All 3 frames share the same vertical scale and baseline alignment.
>
> Animation: ONE single sweeping **180° axe slash — ONLY the cut** (NO wind-up, NO recovery, NO guard frames). The two-bladed axe travels a full half-circle arc and **each frame advances the blade exactly 60° along that arc** (frame-to-frame rotation = 60°, so the 3 frames span the whole 180°). A bright motion-smear trail traces the swept path in every frame. Frame 1: blade entering the arc HIGH on his front side (~0°, overhead/front), body torqued into the swing. Frame 2: blade at the HORIZONTAL mid-point (~60–90°, level with his chest, full reach to the side), strongest smear. Frame 3: blade completing the sweep LOW and BEHIND on the opposite side (~120–180°), full follow-through carried across the body. The three blade positions together must read as one continuous **180° horizontal cut**, not three small swings.
>
> Total: 384×128. No anti-aliasing.

---

### 1-A.5 SIMON — dash / dash attack (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE HEAD TO TOE IN EVERY FRAME. Both feet visible. Character dashing toward the RIGHT. Axe = large heavy two-bladed medieval battle axe (double-crescent steel head), must be visible in every frame.
>
> ⛔ **PROPORTION:** every frame is the Haggar (Final Fight) build — enormous, TALL, heavily muscled, long legs. NOT a dwarf, NOT chibi, NOT stubby. Elf ears + antennae (NO horns), Saiyan armor, egg-yolk-yellow skin, medieval axe.
>
> 🌀 **MAKE IT ALIVE — drive and momentum:** the body **leans HARD forward into the charge (~30°)**, weight thrown ahead of the feet so he reads as launching, not posing. Strong push-off the back leg, big forward stride, the torso committed and off-balance toward the right. The axe and arms lag a beat behind from the speed. Stretch the body slightly along the direction of motion (smear/speed-stretch). NOT a stiff upright figure scooting sideways.
>
> Frame 1: **Wind-up — raising axe.** Both feet flat on the ground, left foot slightly back. Both hands gripping the axe — lifting it ABOVE his head, arms fully extended upward. Axe pointing straight up above his head. Body leaning slightly backward (loading the forward charge). Head facing right. Knees slightly bent ready to launch.
>
> Frame 2: **Mid-charge — running with axe raised.** Body moving fast to the RIGHT — right foot forward in a running stride, left foot pushing off behind. Both arms still raised overhead gripping the axe, axe pointing up and slightly back from the forward momentum. Body leaning forward at 30 degrees. Speed lines behind his body and the axe.
>
> Frame 3: **Overhead slam — hit frame.** Both feet planting hard on the ground on the right side (landing from the charge). Both arms swinging the axe DOWN with full force — axe crashing straight down in front of him, arms now fully extended DOWNWARD, axe pointing down, the heavy double blade biting into the ground. A large impact burst at the floor: visible ground crack lines radiating outward from the impact point, dust explosion cloud. Body leaning far forward from the downswing force.
>
> Frame 4: **Recovering.** Both feet planted on the ground. Arms lowering from the downswing, axe returning to the right side. Body straightening back upright. Right hand gripping the axe at his side, axe resting vertically beside him. Head facing right. Small dust settling at his feet.
>
> Total: 512×128. No anti-aliasing.

---

### 1-A.6 SIMON — esquiva / dodge (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE HEAD TO TOE IN EVERY FRAME. Both feet on the baseline. Character facing right. Axe visible in every frame. This is a deliberate tactical sidestep — NOT a stumble, NOT a fall.
>
> Frame 1: **Reading the attack.** Standing upright, both feet flat on the ground shoulder-width apart. Right hand gripping the axe at his right side, axe resting vertically. Left arm raising slightly in a defensive guard. Head facing right. Body still — he has just detected the incoming attack. Expression: focused, not alarmed.
>
> Frame 2: **Stepping left.** Left foot taking a fast step to the LEFT — left foot landing to the left of its original position. Right foot beginning to follow, lifting off the ground. Body dropping lower — knees bending, body becoming compact. Both arms pulling in close to the torso. Axe pulled in tight to his right side. Body tilting slightly left. Head still facing right.
>
> Frame 3: **Deepest dodge position.** Both feet on the ground, now shifted to the LEFT of starting position. Knees bent deep — body at its lowest point, crouching sideways. Body leaning to the left, head tucked slightly. Left arm raised across the chest in guard. Right hand holding axe tight against the right side. Head turned to watch the attack pass on the right. This is the frame where the attack misses above/beside him.
>
> Frame 4: **Returning to stance.** Both feet planting firmly. Body rising back upright. Right foot stepping back to original width. Arms returning to ready positions — right hand bringing the axe back up to shoulder carry position on the right shoulder. Left hand at side. Head facing right. Standing tall and stable.
>
> Total: 512×128. No anti-aliasing.

---

### 1-A.7 SIMON — dano / hurt (3 frames = 384×128)

> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Hit reaction. Frame 1: impact moment — head snapping back, arms flying outward, sparks off armor. Frame 2: recoiling backward, leaning away from the hit direction. Frame 3: recovering, returning to guard, gritting teeth.
>
> Total: 384×128. No anti-aliasing.

---

### 1-A.8 SIMON — morte / death (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE HEAD TO TOE IN EVERY FRAME. Each frame must show a clearly different body position from the previous one — NOT two nearly identical frames. Axe = large heavy two-bladed medieval battle axe. It is in his hand until frame 3, then on the ground from frame 3 onward.
>
> Frame 1: **Standing stagger.** Both feet on the ground, right foot sliding forward from the final hit impact. Body lurching forward to the right, off-balance. Head drooping slightly forward, chin toward chest. Right hand still loosely gripping the axe — axe dragging on the ground in front of him, not raised. Left arm hanging limp at the side. Shoulder armor cracked, small sparks flickering off the cracks. Expression: eyes half-closed, completely spent.
>
> Frame 2: **Knees buckling.** Both knees beginning to bend — body sinking downward. Right knee nearly touching the ground. Left foot still flat on the floor. Right hand grip on the axe loosening — fingers opening. Axe beginning to tilt and slide out of the grip, still partially in contact with his hand. Body slumping forward. Head hanging down. Sparks still flickering on armor.
>
> Frame 3: **One knee down + axe falls.** Right knee fully on the floor. Left foot still flat on the ground behind him. Right hand fully open — axe released, falling free. The axe is NOW on the ground to his right side, lying flat and horizontal, separate from his hand. Left arm bracing on the left thigh. Head hanging low, facing the floor. Sparks fading on armor.
>
> Frame 4: **Collapsing sideways.** Body falling to the RIGHT — torso tilting right, right arm no longer bracing, body going down. Left foot leaving the ground. Body is mid-fall, not yet on the floor. Axe is already on the floor to his right (it fell in frame 3), body falling toward it. Head turning sideways. Last sparks dying on the armor.
>
> Frame 5: **On the ground.** Body lying on its RIGHT SIDE on the floor. Right arm stretched out along the floor forward-right. Right hand open and relaxed on the floor — the axe is lying on the floor directly beside the open right hand, about one hand-length away. Left arm resting over the torso. Legs extended. Head resting on the floor, facing right. Eyes closed. Armor cracked and dim — no sparks.
>
> Frame 6: **Completely still.** Same position as frame 5 — body on right side, axe on the floor beside the open right hand. Zero movement. Zero sparks. Eyes closed. The only visual difference from frame 5: the body has fully settled (no limb at a mid-fall angle), everything is completely flat and at rest.
>
> Total: 768×128. No anti-aliasing.

---

### 1-A.9 SIMON — pulo / jump (5 frames = 640×128)

> 16-bit pixel art horizontal sprite sheet, 5 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Jump arc. Frame 1: crouch before takeoff, legs coiling. Frame 2: launching upward, arms pumping, feet leaving ground. Frame 3: peak of jump — knees tucked, fists ready. Frame 4: descending, body angling down. Frame 5: landing impact, knees bending, ground cracks under boot.
>
> Total: 640×128. No anti-aliasing.

---

### 1-A.10a SIMON — super_art / Galick Ho — CARGA E RECUPERAÇÃO (5 frames = 640×128)

> ⚠️ **GERAÇÃO SEPARADA — sem beam neste strip.** Gere apenas as poses do personagem.
>
> 16-bit pixel art horizontal sprite sheet, 5 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: "Galick Ho" special attack (style reference: Vegeta's Galick Ho two-handed beam pose, but yellow electric) — charge and recovery sequence only, NO BEAM in any frame (the beam is a separate sprite). Frame 1: Simon steps back into a wide braced fighting stance, both hands pulled back together to ONE side of his body (cupped together near the right hip), fingers curled around a forming energy core, yellow sparks jumping between the cupped palms — charging pose, body low, eyes intense. Frame 2: electricity converges into both cupped hands held together at his side, forming a blinding white-yellow energy orb between the two palms; whole body straining, teeth clenched, massive yellow electric aura flaring around him. Frame 3: Simon in full firing pose — BOTH hands thrust forward TOGETHER, palms cupped side by side facing outward to the RIGHT, arms extended in a single unified two-handed push, body leaning forward braced against the recoil — NO BEAM in this frame, just the character pose with concentrated yellow energy radiating from the joined hands (beam is a separate sprite). Frame 4: recoil pose — feet sliding back from the blast force, hands still extended together, yellow lightning crawling up both arms to the shoulders, eyes glowing solid yellow, body strained. Frame 5: Simon drops his arms, breathing hard, residual sparks drifting from the palms, smoke rising, body still faintly crackling.
>
> Total: 640×128. No anti-aliasing.

---

### 1-A.10b SIMON — super_art / Galick Ho — BEAM (1 frame largo = 512×128)

> ⚠️ **GERAÇÃO SEPARADA — apenas o beam, sem o personagem.**
>
> 16-bit pixel art, single frame, 512×128 pixels, solid neon green (#00FF00) background.
>
> Image: a massive horizontal electric energy beam firing from LEFT to RIGHT, filling the full width of the image. The beam originates from the left edge (a burst of yellow-white energy at the source point, as if launched from two cupped hands) and extends all the way to the right edge with an explosive impact. Beam structure: thick bright white-yellow core in the center, surrounded by jagged yellow lightning tendrils spiraling outward along the beam length, outer fringe of electric arcs in yellow and gold. The beam should look dense and powerful — style reference: Vegeta's Galick Ho but yellow electric. No character body visible. Pure beam effect.
>
> Total: 512×128. No anti-aliasing.

---

### 1-A.11 SIMON — tedio / boredom idle (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ **CORPO COMPLETO OBRIGATÓRIO:** Full body visible head to toe in every frame. Feet and legs MUST touch the bottom baseline. Character occupies the full 128px height — do NOT crop below the waist. All 6 frames share the same vertical scale and baseline alignment.
>
> Animation: Idle boredom sequence. Frame 1: full-body shot, Simon pulling a thick power cable from a compartment on his armor, looking down at it, legs planted wide in relaxed stance. Frame 2: full-body shot, lifting the cable end up to eye level to examine it, other hand on hip, legs visible and grounded. Frame 3: full-body shot, plugging the cable into a port on his chest plate, leaning slightly forward, both legs and feet clearly visible. Frame 4: full-body shot, absorbing bright yellow electric current — arcs of lightning crackling all over his body including legs and arms, eyes wide and glowing, intense expression, feet planted firm on the ground. Frame 5: full-body shot, fully charged — yellow electricity arcs fading, body upright, arms slightly raised, legs strong and visible, satisfied grin. Frame 6: full-body shot, unplugging and coiling the cable, exhaling (small breath puff), storing cable back in armor, legs relaxed, looking energized.
>
> Total: 768×128. No anti-aliasing.

---

