[â¬… Voltar ao Painel de ProduÃ§Ã£o](../00_PAINEL.md)

---

## 1-D: GARNOLD

**Bloco de design (copiar no inÃ­cio de cada prompt do Garnold):**
> *Character reference: Gold-skinned male fighter in a sharp formal gold suit with a black tie and polished black dress shoes. A dark visor covers his eyes, glowing faintly cyan (#00FFFF). A sleek black mouth guard covers his lower face. Slim but powerful build. Enigmatic, stylish, composed presence â€” every movement is deliberate. **Signature weapon: an elegant cyan plasma saber / energy saber â€” matte black hilt, bright cyan blade when active, clean sci-fi glow, handled like a precise duelist weapon rather than a heavy sword. When inactive, only the black hilt is clipped at his left hip; when attacking, the cyan blade ignites instantly and leaves sharp light trails.** Authentic 16-bit SNES pixel art style (Final Fight 3). No anti-aliasing.*

> ðŸ”’ **DireÃ§Ã£o aprovada:** Garnold Ã© o duelista tÃ©cnico do elenco. Qualquer menÃ§Ã£o antiga a "short sword", "straight blade" ou "sword" neste documento deve ser interpretada como **sabre de energia ciano**: cabo preto quando desligado, lÃ¢mina ciano quando ativo, elegante e preciso.

> ðŸ”¥ **REWORK OBRIGATORIO 2026-06-22 â€” usar este bloco antes de qualquer prompt antigo.**
> Garnold nao e corredor pesado nem trator: ele e um cyborg jedi elegante, tecnico, preciso, alto e controlado. A arte nova deve preservar o terno dourado, visor preto/ciano, sapatos pretos e corpo esguio/poderoso, mas corrigir o movimento. Cada folha deve ter frames claramente separados, escala identica, mesma altura de cabeca, mesma linha dos pes e generosa margem para sabre/efeitos. O sabre nao pode parecer faca, pao, canivete ou espada grossa: deve ser uma lamina longa de energia ciano, reta quando em estocada, curva apenas no rastro do golpe, com cabo preto pequeno e brilho limpo. Proibido corpo duplicado no idle, corrida com patinacao, dash reaproveitado como run, frame cortado na borda, sabre fora do quadro, personagem mudando proporcao, arma rigida sem arco, ou acao ilegivel.
>
> **Contrato novo de prompts imagegen:** gerar em strips separados sobre fundo chroma puro `#00FF00`, sem sombra, sem grid desenhado, sem texto, sem watermark. O fundo precisa ser uma cor chapada para remocao local. A imagem pode ser maior que o contrato final, mas cada frame precisa estar isolado com vao verde largo. Depois do imagegen, apenas recortar/remover chroma/medir/empacotar; nao desenhar arte nova por script.
>
> **Estados obrigatorios do rework completo:** `idle` 8f respiracao sutil sem drift; `walk` 8f pode manter linguagem atual, mas com baseline estavel; `run` 6f corrida leve e precisa, sem patinar; `dash` 6f impulso tecnico com antecipacao, corte/slide e freio; `ataques` 8f combo de duelista com sabre longo; `ataque_fuga` 6f com bola de energia ciano explodindo a curta distancia; `special` 6f visor laser sem cortar corpo; `pulo` 5f; `dano` 3f; `morte` 6f; `tedio` 6f olhando relogio/holograma.
> **Ataques 2026-06-22:** usar a logica de um duelista de action-platformer classico: forca vem do pe no chao, quadril, velocidade do avanco e gravidade. Proibido ataque gratuito para cima. O combo deve ler como saque rapido, corte horizontal, dash slash baixo, corte descendente e estocada, sempre com o sabre ciano longo visivel e sem copiar outro personagem.
> **Ataque fuga 2026-06-22:** nao e mais fuga com sabre. Garnold recua meio passo, comprime energia no punho/visor e detona uma bola de energia ciano a curta distancia. Sao 6 frames: carga, esfera formando, disparo curto, impacto, explosao circular, recuperacao elegante.
>
> **Prompt base refatorado para cada strip:** 16-bit SNES / Final Fight 3 pixel art horizontal sprite strip, side-view beat'em up character facing right, full body head-to-toe in every frame, same exact Garnold identity in all frames: tall slim powerful male cyborg in polished gold suit, black tie, black dress shoes, dark wraparound visor with cyan glow, sleek black lower face guard, matte black plasma saber hilt clipped at left hip. Cyan plasma saber only active during attacks, as a long elegant energy blade with clean glow. Solid pure #00FF00 chroma background, no shadows, no floor, no gradients, no text, no watermark. Keep wide green padding between frames, no overlapping silhouettes, no cropped blade/body, same scale/head size/baseline across every frame.

> ðŸ§© **PADRÃƒO DE DIVISÃƒO (pra recorte sem dor de cabeÃ§a).** Folha com muitos frames faz a IA **GRUDAR** os personagens (a arma/membros de um invadem o vizinho). Por isso as aÃ§Ãµes longas estÃ£o **quebradas em prompts curtos**: o **combo vira 1 prompt por golpe** (Hit 1 / Hit 2 / Hit 3) e o **walk vira 2 meias-passadas**. Gere um de cada vez. âš“ **Ã‚ncora de consistÃªncia:** ao gerar partes da MESMA animaÃ§Ã£o, mantenha **mesma escala, mesmo tamanho de cabeÃ§a, mesma linha dos pÃ©s (baseline) e mesma proporÃ§Ã£o** em todas as partes, senÃ£o os frames nÃ£o casam quando juntados na engine.

---

### 1-D.1 GARNOLD â€” idle (7 frames = 896Ã—128)

> 16-bit pixel art horizontal sprite sheet, 7 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME â€” head to toe. Both feet on the baseline. Character facing right. Plasma saber inactive at his left hip â€” only the matte black hilt visible, cyan blade OFF.
>
> Frame 1: Standing perfectly upright. Both feet flat on ground, shoulder-width apart. Arms folded across his chest (right arm over left arm). Left hand resting near (but NOT gripping) the inactive plasma saber hilt at his left hip. Gold suit jacket neat and flat. Visor glowing faint steady cyan. Head facing right.
> Frames 2â€“6: Nearly identical to frame 1 with micro-variations: slight chest rise/fall (breathing), visor flickering brighter on frame 4 then dimming back (one flicker cycle). Body does NOT move significantly â€” this is a minimal breath-only idle.
> Frame 7: Identical to frame 1 â€” loop returns to start.
>
> Total: 896Ã—128. No anti-aliasing.

---

### 1-D.2a GARNOLD â€” walk Â· primeira metade (4 frames = 512Ã—128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” frames must NOT touch or overlap.** [Character reference above.]
>
> âš“ **CONSISTÃŠNCIA:** same scale, same head size, same feet baseline and same proportions as the "walk Â· segunda metade" strip â€” the two halves join into ONE smooth 8-frame walk cycle. Plasma saber inactive at left hip (black hilt visible, cyan blade OFF). FULL BODY, feet on baseline, facing RIGHT.
>
> Frame 1: Left foot forward, right foot back. Right arm swinging forward, left hand resting near the plasma saber hilt (not gripping). Suit jacket slightly swaying. Visor steady cyan. Head level facing right.
> Frame 2: Mid-stride, feet shifting under the body. Arms in counterbalance.
> Frame 3: Right foot forward, left foot back. Left arm swinging forward, right arm back. Left hand momentarily away from the hilt.
> Frame 4: Mid-stride (passing pose), about to bring the left foot forward again.
>
> Total: 512Ã—128. No anti-aliasing.

---

### 1-D.2b GARNOLD â€” walk Â· segunda metade (4 frames = 512Ã—128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” frames must NOT touch or overlap.** [Character reference above.]
>
> âš“ **CONSISTÃŠNCIA:** same scale, same head size, same feet baseline and same proportions as the "walk Â· primeira metade" strip â€” these are frames 5â€“8 of the SAME cycle. Plasma saber inactive at left hip (black hilt visible, cyan blade OFF). FULL BODY, feet on baseline, facing RIGHT.
>
> Frame 1 (=5): Left foot forward again (mirror of the first contact). Right arm forward, left hand back near hilt.
> Frame 2 (=6): Mid-stride, feet shifting. Arms counterbalancing.
> Frame 3 (=7): Right foot forward. Left arm forward. Suit jacket swaying. Left hand near plasma saber hilt.
> Frame 4 (=8): Completing the cycle, returning to the frame-1 position (seamless loop back to the first half).
>
> Total: 512Ã—128. No anti-aliasing.

---

### 1-D.3 GARNOLD - ataques / combo - dividido em 3 blocos curtos (gere os 3 strips abaixo)

> CONSISTENCIA (vale pros 3 blocos): same scale, same head size, same feet baseline and same proportions across the 8 frames. FULL BODY head-to-toe, feet on baseline, facing RIGHT. Weapon = cyan plasma saber / energy saber: matte black hilt, bright cyan blade only when active, clean sci-fi glow and sharp light trails; when inactive only the hilt shows at the left hip.

**1-D.3a - Frames 1-3: Plasma Quick Draw (3 frames)**
> 16-bit pixel art horizontal sprite strip, exactly 3 separated full-body frames on solid neon green (#00FF00) bg. Wide green gap between frames; frames must NOT touch. [Character reference + consistencia acima.]
> Frame 1: Left hand grips the black hilt at the left hip; right foot plants forward; torso coils from the hips; cyan blade just begins igniting downward.
> Frame 2: **Hit frame.** Saber fully active, long cyan blade cutting horizontally left-to-right at chest/waist height; feet grounded; clean cyan trail.
> Frame 3: Recovery into a compact guard, blade still active but lowered, shoulders squared, feet on baseline.

**1-D.3b - Frames 4-6: Low Dash Slash + Descending Cut (3 frames)**
> 16-bit pixel art horizontal sprite strip, exactly 3 separated full-body frames on solid neon green (#00FF00) bg. Wide green gap between frames; frames must NOT touch. [Character reference + consistencia acima.]
> Frame 4: Low forward drive, front knee bent, back foot pushing off, long cyan saber sweeping low and forward, coat trailing behind.
> Frame 5: **Hit frame.** Grounded dash slash at waist height, blade extended far to the RIGHT, long cyan trail, no upward attack.
> Frame 6: Heavy descending cut from shoulder to lower-right, using gravity and hip rotation, both feet visible and planted, blade long and bright.

**1-D.3c - Frames 7-8: Precision Thrust + Reset (2 frames)**
> 16-bit pixel art horizontal sprite strip, exactly 2 separated full-body frames on solid neon green (#00FF00) bg. Wide green gap between frames; frames must NOT touch. [Character reference + consistencia acima.]
> Frame 7: **Hit frame.** Precise forward thrust, saber straight to the RIGHT with a concentrated cyan burst at the tip; torso leaned forward but feet grounded.
> Frame 8: Elegant reset, saber deactivating back to the black hilt at left hip, right hand adjusting the black tie, visor returning to calm cyan.

---

### 1-D.4 GARNOLD - ataque_fuga / energy-ball burst (6 frames)

> 16-bit pixel art horizontal sprite strip, exactly 6 separated full-body frames on solid neon green (#00FF00) background. Leave a generous wide gap of solid neon green between every frame; frames must NOT touch or overlap. [Character reference above.]
>
> FULL BODY IN EVERY FRAME. Feet on baseline. Character facing RIGHT. Saber stays OFF at the left hip; only the matte black hilt is visible. The action is a short-range cyan energy sphere that explodes, not a sword move.
>
> Frame 1: **Brace + charge.** Garnold steps half a foot back, left hand near the hip hilt but not drawing it, right palm opening forward. Cyan light begins gathering in the palm and visor.
>
> Frame 2: **Sphere forming.** Right palm forward at chest height; a compact cyan energy ball appears in front of the hand. Feet grounded, suit and tie controlled.
>
> Frame 3: **Release.** The cyan energy ball launches a short distance to the RIGHT from his palm. Arm extended, body leaning slightly into the release.
>
> Frame 4: **Impact.** Ball reaches enemy range and compresses into a bright cyan-white core. Garnold holds the pose, visor flaring.
>
> Frame 5: **Explosion.** The energy ball bursts into a circular cyan shock ring with small pixel sparks. Garnold recoils minimally but remains elegant and balanced.
>
> Frame 6: **Reset.** Explosion fades; right hand lowers, left hand adjusts the tie, visor returns to calm cyan. Saber remains inactive.

---

### 1-D.5 GARNOLD â€” dash / dash attack (4 frames = 512Ã—128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME. Feet visible. Character dashing toward the RIGHT.
>
> Frame 1: **Wind-up.** Both feet on the ground, right foot slightly back. Left hand gripping sword hilt at left hip. Body leaning forward to the right â€” weight on front foot. Head facing right. Knees slightly bent, ready to launch.
>
> Frame 2: **Mid-dash.** Body airborne, moving fast to the right â€” body nearly horizontal, leaning hard right. Left hand pulling the sword OUT of the scabbard mid-dash â€” blade half-drawn. Suit jacket trailing dramatically to the LEFT from the speed. Speed lines behind his body.
>
> Frame 3: **Slash â€” hit frame.** Both feet landing on the right side. Right arm fully extended to the right â€” sword blade sweeping horizontally to the right at chest/waist height. Blade at full extension, pointing right. A long cyan energy trail behind the full blade arc. Suit jacket still flaring from the motion. Visor glowing bright cyan.
>
> Frame 4: **Stop.** Both feet planted on the ground, sliding slightly. Sword arm lowering. Left hand moving to resheathe â€” blade going back into scabbard at the left hip. Right hand rising to adjust the black tie neatly. Visor returning to normal pulse. Standing upright.
>
> Total: 512Ã—128. No anti-aliasing.

---

### 1-D.6 GARNOLD - esquiva / phase-step dodge (6 frames)

> 16-bit pixel art horizontal sprite strip, exactly 6 separated full-body frames on solid neon green (#00FF00) background. Leave a generous wide gap of solid neon green between every frame; frames must NOT touch or overlap. [Character reference above.]
>
> FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right. Saber remains sheathed throughout. This is not dash and not backflip: it is an elegant cyborg jedi phase-step with a cyan afterimage.
>
> Frame 1: Reading the attack, upright and composed, right palm slightly raised, visor scanning brighter cyan.
>
> Frame 2: Micro-crouch and weight shift, left foot slides back half a step, shoulders narrow, coat pulled tight by motion.
>
> Frame 3: Phase-step left, body offset with a transparent cyan afterimage left behind at the original position, feet still visible.
>
> Frame 4: Low guarded clear pose, one knee bent, one hand near the saber hilt but not drawing it, visor tracking the enemy.
>
> Frame 5: Return step, afterimage fading, suit coat settling, body rising back to full height.
>
> Frame 6: Back to composed stance, arms crossing, visor calm cyan, same baseline and scale as frame 1.

---

### 1-D.7 GARNOLD â€” dano / hurt (3 frames = 384Ã—128)

> 16-bit pixel art horizontal sprite sheet, 3 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME. Feet on baseline.
>
> Frame 1: **Impact.** Both feet on the ground. Head snapping backward to the left from a hit coming from the right. Visor flickering with small electrical sparks. Right arm flying up instinctively toward the hit zone. Left arm thrown out for balance. Suit jacket displaced â€” collar pushed left. Sword still sheathed at left hip.
>
> Frame 2: **Recoiling.** Left foot sliding backward to the left, right foot staying. Body leaning backward to the left â€” the composed posture broken. Suit jacket open and displaced. Head still snapped backward. Visor sparking more. Both arms thrown outward.
>
> Frame 3: **Recovering.** Both feet planting back on ground. Body straightening upright. Right hand rising to smooth down the suit jacket lapel. Visor powering back up â€” cycling from dim back to normal cyan glow. Head returning to face right. Expression: controlled composure returning, jaw tight. Sword still at left hip.
>
> Total: 384Ã—128. No anti-aliasing.

---

### 1-D.8 GARNOLD â€” morte / death (6 frames = 768Ã—128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME. Each frame has a clearly different body position. Sword = straight blade, matte black handle, visible cyan energy line. Visor glows less in each frame until dark.
>
> Frame 1: **Standing stagger.** Both feet on ground, right foot sliding sideways. Body leaning right. Sword drawn and in right hand â€” sword tip touching/dragging on the ground to his right (supporting himself). Visor flickering erratically (not a steady glow â€” broken flicker). Head still facing right. Expression: controlled but strained. Left hand bracing on his thigh.
>
> Frame 2: **Right knee down.** Right knee hitting the floor. Left foot still flat on the ground. Right hand gripping the sword â€” sword tip planted on the ground in front of him, using it like a cane to support himself. Head still up and facing right. Visor dimming but still on. Body at about 45 degrees.
>
> Frame 3: **Both knees down.** Both knees on the floor. Grip on sword loosening â€” fingers opening. Sword beginning to tilt and fall to the right. Visor very dim, barely glowing. Head dropping forward, chin toward chest. Left hand bracing on the floor.
>
> Frame 4: **Sword falling.** Body falling sideways to the right. The sword clattering onto the floor to his right â€” blade lying flat on the ground, separate from his hand. Body hitting the ground on the right side, arm outstretched. Suit jacket splaying open. Visor dark except one tiny flicker.
>
> Frame 5: **On the ground.** Lying on his right side, fully on the floor. Right arm outstretched on the ground. Sword lying beside him on the floor, blade flat, NOT in his hand. Visor has one very faint dim pulse â€” almost completely dark. Legs straight. Suit jacket open.
>
> Frame 6: **Completely still.** Same position as frame 5. Visor completely dark â€” zero glow. Sword motionless on the floor where it fell. No movement. Eyes closed behind the dark visor.
>
> Total: 768Ã—128. No anti-aliasing.

---

### 1-D.9 GARNOLD â€” pulo / jump (5 frames = 640Ã—128)

> 16-bit pixel art horizontal sprite sheet, 5 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME. Feet visible. Character facing right. Sword sheathed at left hip throughout.
>
> Frame 1: **Crouch.** Both feet flat on the ground, knees bent deep. Body crouching low. Arms at sides, slightly bent. Left hand near sword hilt. Head facing right. Gold suit jacket hanging straight down.
>
> Frame 2: **Launching.** Body airborne, rising. Legs extending downward, feet leaving the ground, toes pointing down. Arms spreading slightly outward. Suit jacket flaring open and upward from the launch force. Visor scanning forward. Head facing right.
>
> Frame 3: **Peak.** Body at highest point, fully airborne. Legs tucked upward â€” knees raised toward the chest. Arms slightly extended. Suit jacket floating/flaring outward. Visor glowing and scanning downward (head angled slightly down-right). Sword hilt visible at left hip.
>
> Frame 4: **Controlled descent.** Body falling downward. Legs beginning to extend downward for landing. Arms angling down for control. Suit jacket pressing back from the downward speed. Head facing right.
>
> Frame 5: **Landing.** Both feet hitting the ground flat. Knees bent absorbing impact. Left hand briefly touching the ground for balance. Right arm slightly raised. Head facing right. Suit jacket settling. Visor at normal cyan pulse.
>
> Total: 640Ã—128. No anti-aliasing.

---

### 1-D.10a GARNOLD â€” super_art / Visor Laser â€” POSES (6 frames = 768Ã—128)

> âš ï¸ **GERAÃ‡ÃƒO SEPARADA â€” sem o feixe de laser grande neste strip.** Gere apenas as poses do personagem (o feixe largo Ã© um sprite separado, Â§10b). Apenas brilho/acÃºmulo de luz no visor Ã© permitido nas poses.
>
> 16-bit pixel art horizontal sprite sheet, 6 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right. Animation: "Visor Laser" â€” a WIDE cyan optic beam fired horizontally from his visor to the RIGHT (style reference: X-Men's Cyclops optic blast, but a THICK/WIDE beam, not a thin line). The big beam is a SEPARATE sprite â€” do NOT draw the large laser in these pose frames; only the visor charging up is allowed.
>
> Frame 1: **Bracing.** Standing, both feet planted, right foot stepping back into a stable braced stance. Head facing right, chin level, locking onto the target. The dark visor beginning to glow brighter cyan. Both hands rising toward the sides of the visor (as if steadying/aiming it). Suit neat.
>
> Frame 2: **Charging the visor.** Both feet braced wide. Hands at the temples beside the visor. The visor now glowing intense bright cyan, light leaking from its edges â€” energy building up. Body leaning slightly forward, head tilted down a fraction to aim. Small cyan light particles gathering in front of the visor.
>
> Frame 3: **Firing â€” hit frame.** Both feet braced hard against the recoil, body pushed slightly back. Head locked forward to the RIGHT, chin level. The visor at maximum blinding cyan brightness â€” a burst of cyan light erupting from the FULL WIDTH of the visor slit. NO large beam drawn in this frame (separate sprite) â€” just the intense wide flash at the visor as the source. Hands clenched at his sides bracing.
>
> Frame 4: **Sustained beam.** Same braced firing posture, head locked right. Visor still erupting wide cyan light at full intensity. Suit jacket pressed back from the energy wash. Body holding steady against the continuous output.
>
> Frame 5: **Beam ending.** Head still facing right, visor light dimming from blinding back toward bright. Body straightening up from the braced stance. Wisps of cyan light fading from the visor edges.
>
> Frame 6: **Finishing.** Right hand rising to adjust the black tie neatly. Visor fading back to normal steady cyan pulse. Feet returning to a relaxed stance, body upright and composed again. Head facing right.
>
> Total: 768Ã—128. No anti-aliasing.

---

### 1-D.10b GARNOLD â€” super_art / Visor Laser â€” FEIXE LARGO (1 frame largo = 512Ã—128)

> âš ï¸ **GERAÃ‡ÃƒO SEPARADA â€” apenas o feixe, sem o personagem.**
>
> 16-bit pixel art, single frame, 512Ã—128 pixels, solid neon green (#00FF00) background.
>
> Image: a massive WIDE horizontal laser beam firing from LEFT to RIGHT, filling the full width of the image. âš ï¸ The beam must be THICK and WIDE â€” a broad slab of energy occupying a large portion of the 128px height (roughly 60â€“80px tall at the core), NOT a thin pencil line. The beam originates from the left edge (a wide burst of cyan-white light at the source, as if from a visor slit) and extends all the way to the right edge with a bright impact flare. Structure: a brilliant white-cyan core down the center, surrounded by a thick cyan (#00FFFF) energy body, with a softer cyan glow halo on the top and bottom edges; a few horizontal energy striations running along its length. Style reference: Cyclops's optic blast (X-Men) but noticeably WIDER and thicker. No character body visible. Pure beam effect.
>
> Total: 512Ã—128. No anti-aliasing.

---

### 1-D.11 GARNOLD â€” tedio / boredom idle (6 frames = 768Ã—128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128Ã—128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame â€” clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> âš ï¸ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right.
>
> Frame 1: **Checking watch.** Standing upright, both feet on ground. Left arm raising, wrist turning upward â€” a sleek high-tech smartwatch on the left wrist is now visible (rectangular or round screen, metallic band). Right arm at side. Head tilting slightly down to look at the watch. Sword at left hip. Expression: neutral/bored.
>
> Frame 2: **Hologram appearing.** Left arm still raised. A small cyan holographic display screen (rectangle of light, translucent, floating above the watch) projects upward from the watch face. Right arm at side. Head tilting to read the hologram. Visor flickering with extra cyan light from the hologram.
>
> Frame 3: **Reading hologram.** Left arm still raised, hologram floating above watch. Head tilted slightly right to read. Expression: scanning/analyzing. Right arm at side.
>
> Frame 4: **Typing.** Left arm raised with hologram. Right hand raised â€” right index finger extended and pressing/tapping on the holographic display with precise single-finger inputs. Expression: focused. Body still upright.
>
> Frame 5: **Slight nod.** Both arms still in same position (left raised with hologram, right finger still near hologram). Head nodding slightly downward once â€” he read something of note. Visor flickering once.
>
> Frame 6: **Closing hologram.** Left hand pressing or swiping â€” hologram disappearing (no more cyan floating screen). Left arm lowering back to crossed position. Right arm crossing over left arm on the chest â€” returning to arms-crossed idle pose. Visor back to normal steady cyan pulse. Expression: back to composed neutral.
>
> Total: 768Ã—128. No anti-aliasing.

---

