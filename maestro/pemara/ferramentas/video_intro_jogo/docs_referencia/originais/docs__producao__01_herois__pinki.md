[⬅ Voltar ao Painel de Produção](../00_PAINEL.md)

---

## 1-B: PINKI

**Bloco de design (copiar no início de cada prompt da Pinki):**
> *Character reference: Pink-skinned female fighter. Long upright bunny-like ears standing straight up tall from the top of her head, erect and alert (**NOT floppy, NOT lop, NOT hanging down** — the ears point UP in every frame). **⚠️ OBRIGATÓRIO: a very large, prominent magenta bow tied at the top center of her head — this bow is a defining feature and must be visible in every single frame, even during fast movement.** The bow is wide and puffy, magenta/hot-pink color, and sits on top of her head between her ears.*
>
> *Face: pretty feminine features with distinct eyelashes. Expression is **confident and cool — a relaxed, slightly cocky smirk**, not angry or aggressive. She looks like she's having fun. Mature and attractive, not childish, but also NOT a scowl or war face. Think "street fighter who knows she'll win."*
>
> *Outfit: sleeveless fighting top (magenta/dark pink), flexible dark pants, athletic fabric hand wraps on hands and feet (purple/dark). Agile build — she is the fastest and most acrobatic of the group.*
>
> *⚠️ **NUNCHAKU — DESCRIÇÃO TÉCNICA OBRIGATÓRIA:** Two separate short cylindrical wooden batons (each baton is a slim elongated rod, approximately forearm-length, roughly the size of a thick marker pen). The two batons are connected at their tips by a very short 3-link metal chain. **NOT oval rings. NOT circles. NOT loops. NOT a lasso. NOT a whip with a round end.** When held: one baton gripped in her fist, the other baton hanging below connected by the short chain. When spinning: one baton gripped, the other baton flies in an arc — both batons always look like two distinct slim cylindrical rods with a connecting chain between them. The batons are off-white/ivory colored. The connecting chain is small and metallic grey.* Authentic 16-bit SNES pixel art style (Final Fight 3). No anti-aliasing.*
>
> *📐 **ESPAÇAMENTO:** deixe um espaço (gap) largo de verde neon entre cada frame — frames bem separados, sem encostar. Os valores "Total" abaixo são o tamanho de CONTEÚDO nominal de cada frame; com os gaps a largura final fica maior, tudo bem (o sheet é remontado/recortado depois).*

---

### 1-B.1 PINKI — idle (7 frames = 896×128)

> 16-bit pixel art horizontal sprite sheet, 7 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Bouncing idle with nunchaku spin. Weight shifts foot to foot with a light bounce — she can't stay still. One hand grips one baton; the other baton swings in a slow lazy figure-8 arc below it, connected by the short chain. At all times both batons are visible as two separate slim cylindrical rods — never rings, never loops. Chain stretches taut during the arc. Her tall upright ears bob slightly with the bounce but stay standing straight up.
>
> Total: 896×128. No anti-aliasing.

---

### 1-B.2 PINKI — walk (8 frames = 1024×128)

> 16-bit pixel art horizontal sprite sheet, 8 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Full walking cycle, side-view. Quick precise steps. One hand swings freely, the other hand grips one nunchaku baton — the second baton swings in a controlled forward-and-back pendulum arc matching her stride rhythm, chain taut on each swing. Both batons are always visible as two distinct slim cylindrical rods; never rings or loops. Her upright ears bob gently while staying erect and pointing up. The walk has energy and intent.
>
> Total: 1024×128. No anti-aliasing.

---

### 1-B.3 PINKI — ataques / combo (8 frames = 1024×128)

> 16-bit pixel art horizontal sprite sheet, 8 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: 3-hit nunchaku combo. The nunchaku consists of TWO slim cylindrical batons connected by a short chain — never rings, never oval loops.
> Frames 1-2: Quick horizontal strike — gripping one baton, she swings the free baton outward horizontally at mid-range, chain pulled taut, the flying baton is a slim rod moving fast with a motion blur streak.
> Frames 3-5: Overhead smash — raises the gripped baton high, the free baton falls from above in a downward arc, chain snap on impact; pink impact star where the free baton hits. Both batons visible as slim rods.
> Frames 6-8: Finishing spinning side-strike — body pivots, she swings the free baton in a wide horizontal arc from behind into the forward direction, chain fully extended taut, the free baton flies like a striking rod toward the enemy. Her upright ears whip from the spin momentum but stay standing up at the base.
>
> Total: 1024×128. No anti-aliasing.

---

### 1-B.4 PINKI — ataque_fuga / escape attack (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: **Spinning nunchaku tornado** — style reference: Haggar's spinning lariat (Final Fight) and Zangief's spinning lariat (Street Fighter). Pinki grips one baton and spins her entire body in place like a top, the free baton flying outward horizontally from centrifugal force, sweeping everything around her in a 360° horizontal arc.
>
> Frame 1: Wind-up — feet planted wide, body coiling into the spin. Both arms pulling inward toward her chest, nunchaku gathered. Expression: determined smirk.
>
> Frame 2: Spin begins — body rotating, one arm extended outward with the gripped baton, the free baton starting to fly outward horizontally — chain taut from centrifugal force. Both batons visible as two slim rods at opposite ends of the taut chain. Pink motion streak begins around her.
>
> Frame 3: **Full tornado spin** — body fully rotating, both arms extended wide. The free baton flies outward horizontally at full speed, chain completely taut and straight, the baton is a horizontal slim rod at the end. A full circular pink speed trail wraps around her entire body — the silhouette reads as a spinning top. This frame is the hit frame: the flying baton is at maximum reach.
>
> Frame 4: Spin ending — body slowing, stepping one foot back into escape stance. The free baton swings back toward her grip, chain relaxing. She faces the opposite direction from frame 1 — the spin carried her backward away from the enemy.
>
> Total: 512×128. No anti-aliasing.

---

### 1-B.5 PINKI — dash / dash attack (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Spinning nunchaku buzzsaw dash. The nunchaku is two slim cylindrical batons connected by a short chain. Frame 1: low forward crouch, one baton gripped and raised, the free baton coiled back in wind-up — both batons clearly two separate slim rods. Frame 2: launching forward, the free baton already spinning in a rapid vertical circle around the gripped baton — a circular blur of two slim sticks. Frame 3: full-speed dash, both batons spinning in a tight vertical circle like a buzzsaw, pink energy trail following the arc of the chain; the motion blur makes it look like a spinning disc but the two slim rod shapes are visible at opposite ends of the spin. Frame 4: landing, the free baton snapping back to a controlled hanging grip.
>
> Total: 512×128. No anti-aliasing.

---

### 1-B.6 PINKI — esquiva / dodge (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Low-profile duck dodge. Frame 1: bending knees, ducking under a high attack. Frame 2: low crouch, one hand touching ground, upright ears swept back slightly by the motion but still standing up. Frame 3: sliding slightly backward while crouched. Frame 4: springing back up to ready stance.
>
> Total: 512×128. No anti-aliasing.

---

### 1-B.7 PINKI — dano / hurt (3 frames = 384×128)

> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Hit reaction. Frame 1: impact — head snapping to the side, her upright ears whipping from the impact (still erect at the base), one hand instinctively raised. Frame 2: spinning backward from the force, one hand on ground. Frame 3: recovering, eyes fierce, dropping back into stance.
>
> Total: 384×128. No anti-aliasing.

---

### 1-B.8 PINKI — morte / death (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> Animation: Death sequence — emotional, not brutal. Eyes open throughout (not grimacing, not hit-reaction face) — expression shifts from exhausted disbelief to peaceful surrender.
>
> Frame 1: **Standing stagger** — weight shifting sideways, one foot dragging, eyes half-open and glassy (NOT squinting in pain — she looks exhausted and surprised). One baton loosely gripped at her side, the free baton swinging weakly by the chain below. Bow still in place.
>
> Frame 2: **Knees bending** — slowly sinking, both knees beginning to buckle. Sad soft expression, eyes still open and glassy. The grip on the baton loosening, the free baton starting to drag on the floor.
>
> Frame 3: **One knee on the ground** — right knee touches the floor, left foot still flat on the ground behind her (NOT all fours — hands are NOT on the ground). She looks at the nunchaku as both batons slip from her open hand onto the floor, chain going slack between them.
>
> Frame 4: **Collapsing sideways** — body falling slowly to her left side, one arm reaching out to slow the fall. The nunchaku already fully on the floor beside her, both batons lying with slack chain.
>
> Frame 5: **Lying still on her side** — fully on the ground, eyes closed, bow slightly askew. The nunchaku rests on the floor nearby. Body completely relaxed — visibly different silhouette from frame 4 (she has settled flat, no arm reaching out anymore).
>
> Frame 6: **Fade out moment** — same pose as frame 5 but a single small pink musical note rises slowly from her chest and floats upward, beginning to fade. This is the ONLY difference from frame 5 — the note must be clearly visible, not just a tiny dot.
>
> Total: 768×128. No anti-aliasing.

---

### 1-B.9 PINKI — pulo / jump (5 frames = 640×128)

> 16-bit pixel art horizontal sprite sheet, 5 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE IN EVERY FRAME — head to toe. Feet must be visible. Character facing right (side-view). Large magenta bow visible on top of head in every frame.
>
> Frame 1: **Pre-jump crouch.** Both feet flat on the ground. Knees bent deep — legs crouching. Arms bent at sides, fists at hip level. Head facing right. Nunchaku in right hand, free baton hanging down by the short chain. Body low.
>
> Frame 2: **Launching upward.** Body is now in the air, rising fast. Legs still bent, feet leaving the ground, toes pointing downward. Arms push out and upward for momentum. Head facing right, upright ears trailing slightly behind from speed but still pointing up. Nunchaku in right hand, free baton pulled upward by momentum.
>
> Frame 3: **Peak of jump — highest point.** Body fully airborne, no ground contact. Legs tucked upward, knees bent high near the chest. Arms spread wide outward. Head facing right. Upright ears pointing up. Magenta bow clearly visible. Nunchaku in right hand.
>
> Frame 4: **Descending.** Body angling slightly forward while falling. Legs beginning to extend downward for landing. Arms angling down for balance. Head looking downward-right at the ground. Both feet visible below her.
>
> Frame 5: **Landing.** Both feet flat on the ground. Knees bent deep absorbing impact. Arms outstretched to the sides for balance. Head facing right. Light dust puff at feet. Nunchaku in right hand swinging slightly from the landing impact.
>
> Total: 640×128. No anti-aliasing.

---

### 1-B.10a PINKI — super_art / Kikou Ho — POSES (6 frames = 768×128)

> ⚠️ **GERAÇÃO SEPARADA — sem a esfera/feixe grande neste strip.** Gere apenas as poses do personagem (o efeito de energia é um sprite separado, §10b).
>
> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE IN EVERY FRAME — head to toe. Feet visible and touching the baseline. Large magenta bow visible in every frame. Character facing RIGHT. Animation: "Kikou Ho" energy projectile (style reference: Chun-Li's Kikoken — hands cupped together at the hip, then thrust forward to fire an energy ball to the right). The big energy ball/beam is a SEPARATE sprite — do NOT draw the large projectile attached to her hands in these pose frames; only small glow at the hands is allowed.
>
> Frame 1: **Wind-up stance.** Standing braced, feet wide apart, left foot forward, right foot back. Both hands pulled back together to her RIGHT side near the hip, palms cupped facing each other forming a small hollow. Knees bent low. Head facing right. Eyes focused with a cocky smirk. A faint pink-magenta glow beginning between the cupped palms. Bow visible.
>
> Frame 2: **Concentrating energy.** Same wide braced stance, hands still cupped together at the right hip. A small magenta energy orb forming between the palms — a compact glowing sphere held between her two hands. Her body leaning slightly back, gathering power. Pink light reflecting on her face. A couple of tiny pink musical notes (♪) drifting up from the orb (her musical signature). Bow visible.
>
> Frame 3: **Thrust — firing pose.** Both arms thrust FORWARD together to the RIGHT, palms open and pushed outward side by side (the classic two-handed palm-push). Body lunging forward onto the front foot, back leg extended for the push. Head facing right, determined smirk. Concentrated magenta energy radiating from the joined palms — NO large projectile in this frame (the energy ball is a separate sprite that leaves her hands). Bow visible.
>
> Frame 4: **Follow-through.** Arms still extended forward to the right, hands open, body fully committed forward on the front foot. Residual magenta glow at the palms. A small recoil shimmer of pink energy around her hands. Bow visible.
>
> Frame 5: **Recovering.** Arms beginning to draw back toward her body, body straightening from the lunge. Faint pink sparkles dispersing from her palms. One small pink musical note (♪) floating up. Head facing right.
>
> Frame 6: **Reset.** Standing upright again, facing right, both feet flat on the ground. Arms relaxed back toward her sides. Bow perfectly straight and in place. Confident smirk. A last tiny pink musical note (♪) drifting upward from her hand.
>
> Total: 768×128. No anti-aliasing.

---

### 1-B.10b PINKI — super_art / Kikou Ho — ESFERA/FEIXE (1 frame largo = 512×128)

> ⚠️ **GERAÇÃO SEPARADA — apenas o projétil de energia, sem o personagem.**
>
> 16-bit pixel art, single frame, 512×128 pixels, solid neon green (#00FF00) background.
>
> Image: a magenta/hot-pink energy projectile traveling from LEFT to RIGHT. The shape is a bright concentrated energy ball/orb at the LEADING (right) end, trailing a tapering energy beam/streak behind it to the left edge of the image (where it was launched from her hands). Structure: a dense white-pink core inside the leading orb, wrapped in swirling magenta energy, with a glowing pink comet-like tail streaking back to the left. A few small pink musical note symbols (♪ ♫) embedded in the energy trail as her signature touch — subtle, not overpowering the projectile read. Style reference: Chun-Li's Kikoken fireball, but magenta/pink. No character body visible. Pure projectile effect.
>
> Total: 512×128. No anti-aliasing.

---

### 1-B.11 PINKI — tedio / boredom idle (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE IN EVERY FRAME — head to toe. Both feet on the baseline. Character facing right. Large magenta bow on top of head visible every frame.
>
> Frame 1: **Reaching for mirror.** Standing upright, both feet flat on ground. Right hand reaching down and to the right side of her outfit — fingers closing around a small circular hand mirror (round face, short handle). Left hand resting on her left hip. Bored expression — mouth slightly open, one eyebrow raised. Head facing right.
>
> Frame 2: **Holding mirror up.** Right hand raised, holding the round hand mirror at face level. Mirror face pointing toward the viewer (we can see the shiny reflective circle). Left hand still on hip. Eyes looking at the mirror. Head facing right. Feet still flat on ground.
>
> Frame 3: **Fixing the bow.** Right hand still holds mirror at face level. Left hand raised to the top of her head, fingers adjusting the large magenta bow. Head tilted slightly toward the left hand. Feet flat on ground.
>
> Frame 4: **Satisfied check.** Right hand still holds mirror. Left hand back at hip. Head slightly tilted, eyes looking at the mirror. Expression: content smirk — she likes what she sees. Feet flat on ground.
>
> Frame 5: **Final approval look.** Right hand holds mirror at eye level. Left hand at hip. Eyes directed at the mirror, expression is a clear approving smile. Head facing right. Feet flat on ground.
>
> Frame 6: **Putting it away.** Right hand lowering, tucking the mirror back into the outfit. Left hand at hip. Both feet flat on ground, standing upright. Expression: confident smirk. Head facing right. Back in ready standing pose.
>
> Total: 768×128. No anti-aliasing.

---

