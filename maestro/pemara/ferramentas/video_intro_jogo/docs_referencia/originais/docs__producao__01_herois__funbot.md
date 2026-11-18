[⬅ Voltar ao Painel de Produção](../00_PAINEL.md)

---

## 1-E: FUN BOT

**Bloco de design (copiar no início de cada prompt do Fun Bot):**
> *Character reference: Silver robotic battle unit with golden segmented mechanical joints at the neck, elbows, and knees. A black rectangular visor panel for a face with a single cyan digital eye that blinks. Two small yellow-tipped antennae on top of the head. Battle-scarred appearance: visible scratches, scorch marks, and slight dents on the body. Steam vents on both shoulders. Heavy, upright stance. **Fighting identity: flamboyant robot monk, no weapons of any kind — theatrical open-palm martial arts, exaggerated stances, piston-assisted punches, shoulder steam puffs, and show-off mechanical flourishes. He is the loud, charismatic robot every beat 'em up is obligated to have.** Authentic 16-bit SNES pixel art style (Final Fight 3). No anti-aliasing.*

> 🔒 **Direção aprovada:** Fun Bot luta como um monge robótico espalhafatoso. Não usar arma, bastão, espada, arma de fogo ou acessório de combate; todo ataque deve vir de mãos, palmas, pistões, foguetes internos, peso corporal e teatralidade mecânica.

> 🧩 **PADRÃO DE DIVISÃO (pra recorte sem dor de cabeça).** Folha com muitos frames faz a IA **GRUDAR** os personagens (os braços-pistão/membros de um invadem o vizinho). Por isso as ações longas estão **quebradas em prompts curtos**: o **combo vira 1 prompt por golpe** (Hit 1 / Hit 2 / Hit 3) e o **walk vira 2 meias-passadas**. Gere um de cada vez. ⚓ **Âncora de consistência:** ao gerar partes da MESMA animação, mantenha **mesma escala, mesmo tamanho de cabeça, mesma linha dos pés (baseline) e mesma proporção** em todas as partes, senão os frames não casam quando juntados na engine.

> 🔒 **Atualização 2026-06-22 — identidade travada:** qualquer rework novo do Fun Bot deve partir DESTE bloco original, sem reinterpretar o personagem. Reprova automática se virar robô azul, robô de peito redondo, dois olhos humanos, armadura genérica, corpo liso sem marcas, proporção diferente, frente total ou personagem sem antenas/visor/juntas douradas/steam vents. `super_art` e `tedio` atuais estão aprovados e não devem ser refeitos sem pedido explícito.

> 🚀 **Atualização 2026-06-22 — movimento:** dash, corrida e ataque_fuga usam recursos de robô: propulsores internos nos pés/quadril/costas, pistões e vapor. Ataques básicos continuam sem armas: golpes de palma, pistões e peso corporal. Ataque_fuga novo: Fun Bot solta vapor por todas as juntas para afastar inimigos, sem canhão, sem arma e sem projétil metálico.

> 🔒 **Atualização 2026-06-23 — rework de ataques/esquiva/pulo:** usar o bloco original acima como âncora absoluta. "Haschel / Legend of Dragoon" é referência APENAS de energia marcial e cadência de combo (palmas, cotovelos, joelhada/chute, peso corporal), sem copiar personagem, roupa, rosto, cabelo, cor ou pose específica. Fun Bot continua sendo o mesmo robô-monge prateado, com visor preto, um olho ciano, antenas amarelas, juntas douradas, marcas de batalha e steam vents. Ataques básicos seguem sem armas; esquiva usa propulsores para recuar; pulo usa jatos compactos com corpo constante. A fita deve ser quebrada em tiras curtas para evitar corte e invasão entre frames.

> ✅ **Deploy 2026-06-23 — sem redesenhar o robô:** geração livre de corpo inteiro foi rejeitada por mudar a identidade. O asset válido usa o Fun Bot existente como fonte, com normalização identity-locked em `tools/asset_pipeline/normalize_funbot_identity_locked.ps1`: ataques removem o golpe vertical e reprisam golpes terrestres de palma/pistão, esquiva mantém propulsor curto e pulo ganha margem inferior sem cortar jatos. Qualquer tentativa futura de corpo novo só entra se preservar exatamente visor, antenas, juntas douradas, volume corporal e proporção dos sprites aprovados.

---

### 1-E.1 FUN BOT — idle (7 frames = 896×128)

> 16-bit pixel art horizontal sprite sheet, 7 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME — head to toe. Both feet on the baseline. Character facing right. Silver robot body, golden joints at elbows and knees, single cyan digital eye on the black visor face.
>
> Frame 1: Standing upright. Both feet flat on ground. Arms at sides, slightly bent at the golden elbow joints. Cyan eye open and glowing. Steam vents on both shoulders closed (no puff). Body at full height.
> Frame 2: Body very slightly lower — robotic bob downward. Cyan eye open. Left shoulder steam vent releasing a small white puff of steam.
> Frame 3: Body returning upward. Right elbow piston extending slightly (the golden joint moving outward). Cyan eye CLOSED (blink).
> Frame 4: Body at full height again. Cyan eye open. Right elbow piston retracting back. Right shoulder steam vent releasing a small white puff.
> Frame 5: Body very slightly lower again (second bob). Cyan eye open. Left elbow piston extending slightly.
> Frame 6: Body rising. Cyan eye CLOSED (second blink). Left elbow piston retracting.
> Frame 7: Back to frame 1 position — loop complete. Cyan eye open. No steam. Body still.
>
> Total: 896×128. No anti-aliasing.

---

### 1-E.2a FUN BOT — walk · primeira metade (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.** [Character reference above.]
>
> ⚓ **CONSISTÊNCIA:** same scale, same head size, same feet baseline and same proportions as the "walk · segunda metade" strip — the two halves join into ONE smooth 8-frame stomp cycle. FULL BODY, feet on baseline, facing RIGHT. Golden knee pistons compress/extend with each step.
>
> Frame 1: Left foot stomped forward (on the ground), right foot back. Right arm swinging forward, left arm back. Golden left knee joint extended. Body upright, head level. Cyan eye open.
> Frame 2: Mid-stride transfer, both feet near center, arms mid-swing, body rising slightly.
> Frame 3: Right foot stomped forward, left foot back. Left arm forward, right arm back. Golden right knee extended. Right shoulder steam vent puffing.
> Frame 4: Mid-stride transfer (passing pose), about to bring the left foot forward again.
>
> Total: 512×128. No anti-aliasing.

---

### 1-E.2b FUN BOT — walk · segunda metade (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.** [Character reference above.]
>
> ⚓ **CONSISTÊNCIA:** same scale, same head size, same feet baseline and same proportions as the "walk · primeira metade" strip — these are frames 5–8 of the SAME stomp cycle. FULL BODY, feet on baseline, facing RIGHT.
>
> Frame 1 (=5): Left foot forward again. Right arm forward, left arm back. Body bobbing down with the stomp weight.
> Frame 2 (=6): Mid-stride transfer, arms counterbalancing.
> Frame 3 (=7): Right foot forward. Left arm forward. Left shoulder steam vent puffing. Cyan eye blinking.
> Frame 4 (=8): Completing the cycle, returning to the frame-1 position (seamless loop back to the first half).
>
> Total: 512×128. No anti-aliasing.

---

### 1-E.3 FUN BOT — ataques / combo marcial — **dividido em 3 golpes** (gere os 3 strips abaixo)

> ⚓ **CONSISTÊNCIA (vale pros 3 golpes):** same scale, same head size, same feet baseline and same proportions across Hit 1 / Hit 2 / Hit 3 — they chain into one combo. FULL BODY head-to-toe, feet on baseline, facing RIGHT. Golden elbow joints are pistons that EXTEND during strikes. Body height must stay constant; action comes from limbs, hips, weight shift, steam and impact FX, not from stretching the character. No weapons, no staff, no sword, no cannon, no human monk redesign.

**1-E.3a — Hit 1: Servo Palm Opening (3 frames = 384×128)**
> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) bg. **Wide green gap between frames — must NOT touch.** [Character reference + consistência acima.]
> Frame 1: Wide low monk stance, both feet planted on the same baseline. Left open palm chambered near the chest, right palm guarding, golden elbow pistons coiled. Cyan eye focused.
> Frame 2: **First hit.** Left open palm snaps forward to the RIGHT at chest height, piston extends, tiny cyan contact spark at the palm. Torso leans slightly but head/body size remains identical.
> Frame 3: Flow-through guard: palm retracting, right shoulder and elbow piston begin to load for the next strike, small white steam puff from one shoulder vent.
> Total: 384×128. No anti-aliasing.

**1-E.3b — Hit 2: Piston Dharma Palm (3 frames = 384×128)**
> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) bg. **Wide green gap between frames — must NOT touch.** [Character reference + consistência acima.]
> Frame 1: Weight shifts into the right hip. Right open palm pulls back, golden elbow piston fully retracted. Shoulder vents puff steam dramatically, charging pressure.
> Frame 2: **Second hit.** Right palm launches forward fast at rib/chest height, piston extends with a short white steam burst. Feet stay grounded; no sliding, no weapon, no projectile.
> Frame 3: Mechanical follow-through: right palm locked out, circular cyan impact ripple close to the palm, left hand protects visor. Body returns toward center without shrinking or stretching.
> Total: 384×128. No anti-aliasing.

**1-E.3c — Hit 3: Bell Elbow / Grounded Heel Finish (2 frames = 256×128)**
> 16-bit pixel art horizontal sprite sheet, 2 frames, 128×128 each, solid neon green (#00FF00) bg. **Wide green gap between frames — must NOT touch.** [Character reference + consistência acima.]
> Frame 1: Finisher coil. Both feet planted wide. Left elbow/palm chambers low across the torso, right knee bends, steam from both shoulder vents. Character stays the same height.
> Frame 2: **Finisher hit.** Grounded rotating elbow/palm-and-heel strike to the RIGHT, with a compact cyan crescent impact arc at chest height. One foot may pivot but stays visible; no high uppercut, no overhead strike, no jump.
> Total: 256×128. No anti-aliasing.

---

### 1-E.4 FUN BOT — ataque_fuga / escape attack · vapor de juntas (9 frames, gerar em 3 tiras de 3)

> Gere em 3 prompts separados de 3 frames cada, todos com o mesmo `Character reference above`, mesma escala, mesma baseline e mesma proporção. 16-bit pixel art horizontal sprite sheet, 3 frames per strip, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.**
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet visible. Character facing RIGHT. No cannon, no gun, no projectile weapon. This is a defensive robot-monk pressure release: steam bursts from shoulders, elbows, knees, hips, wrists and ankle joints to push enemies away.
>
> Strip A, Frame 1: **Pressure priming.** Standing, both feet on ground. Body crouching slightly. Shoulder vents opening with small white steam puffs. Cyan eye flickering to red warning mode. Both open palms raised in defensive monk guard.
>
> Strip A, Frame 2: **Joint pressure build.** Elbow, knee and shoulder vents begin venting. Golden segmented joints glow faintly from pressure. Body stays planted and heavy.
>
> Strip A, Frame 3: **Warning release.** Steam jets start from wrists and ankles. Palms open wider, monk stance braced. No projectile, only vapor pressure.
>
> Strip B, Frame 4: **Full vent burst begins.** Thick white steam bursts from shoulders, elbows, knees and ankle vents, expanding outward around the robot. Feet still grounded.
>
> Strip B, Frame 5: **Hit frame.** Maximum vapor burst in all directions, a circular wall of steam pushing enemies away. Fun Bot remains visible and the same size inside the cloud. No weapon, no beam.
>
> Strip B, Frame 6: **Pressure slide.** Vapor continues outward while internal foot propulsors nudge him slightly backward. Body leans but stays controlled.
>
> Strip C, Frame 7: **Cooling.** Steam begins to dissipate. Cyan eye returns from red to cyan. Palms remain open in monk guard.
>
> Strip C, Frame 8: **Valve close.** Shoulder and elbow vents close, small residual wisps from knees/ankles. Body returns upright.
>
> Strip C, Frame 9: **Reset.** Back to planted monk guard, same baseline and scale as frame 1. Only tiny final steam puffs.
>
> Total final runtime: 9 frames. No anti-aliasing.

---

### 1-E.5 FUN BOT — dash / dash attack · propulsor curto (6 frames, gerar em 2 tiras de 3)

> Gere em 2 prompts separados de 3 frames cada, todos com o mesmo `Character reference above`, mesma escala, mesma baseline e mesma proporção. 16-bit pixel art horizontal sprite sheet, 3 frames per strip, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet visible. Dashing toward the RIGHT. Use internal foot/hip/back propulsors and piston compression. No horse gallop, no skating, no car-on-sand slide.
>
> Strip A, Frame 1: **Coiling.** Both feet on the ground. Golden knee and hip pistons compress. Left palm forward for balance, right fist/palm chambered. Cyan eye bright.
>
> Strip A, Frame 2: **Ignition.** Short blue/yellow propulsor jets fire from both feet and back vents. Body leans right, still compact and heavy.
>
> Strip A, Frame 3: **Dash travel.** Fast low mechanical burst to the right, feet barely off the ground, speed lines from back/ankles. Body not stretched.
>
> Strip B, Frame 4: **Impact / shoulder check.** Heavy robot shoulder/palm pressure forward, no weapon. Small cyan impact spark at palm/shoulder only.
>
> Strip B, Frame 5: **Braking jets.** Reverse ankle/foot jets fire briefly to stop the dash. Knees bend, torso braced.
>
> Strip B, Frame 6: **Recovery.** Feet planted, vents closing, back to monk guard. Same size and baseline as frame 1.
>
> Total final runtime: 6 frames. No anti-aliasing.

---

### 1-E.5b FUN BOT — corrida / run · propulsor controlado (6 frames, gerar em 2 tiras de 3)

> Gere em 2 prompts separados de 3 frames cada, todos com o mesmo `Character reference above`, mesma escala, mesma baseline e mesma proporção. 16-bit pixel art horizontal sprite sheet, 3 frames per strip, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — frames must NOT touch or overlap.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Running toward the RIGHT. This is not a dash and not a gallop: Fun Bot uses short controlled foot/back propulsor pulses to make a heavy robotic run. Feet contact the ground rhythmically; no skating.
>
> Strip A, Frame 1: Left foot planted forward, right foot back, small ankle jet cooling. Arms in monk guard.
>
> Strip A, Frame 2: Weight transfer, both knees compress, tiny back vent pulse.
>
> Strip A, Frame 3: Right foot drives forward, left foot pushes off, short yellow/blue jet from left ankle.
>
> Strip B, Frame 4: Passing pose, torso stable, head level, arms counterbalancing.
>
> Strip B, Frame 5: Left foot drives forward again, right ankle propulsor pulse.
>
> Strip B, Frame 6: Recovery into seamless loop back to frame 1, same scale and baseline.
>
> Total final runtime: 6 frames. No anti-aliasing.

### 1-E.6 FUN BOT — esquiva / dodge com propulsores (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right. This is a robot dodge, not a human roll/backflip: short reverse thruster burst from feet/hips/back, compact heavy body, no gallop, no skating, no duplicated dash pose.
>
> Frame 1: **Detecting.** Standing upright, both feet on ground. Cyan eye changing to RED warning mode. Both open palms raise slightly in a defensive monk guard. No movement yet.
>
> Frame 2: **Thruster ignition.** Knees compress, hip/back/ankle vents open. Small blue/yellow reverse jets start firing toward the RIGHT to push Fun Bot backward LEFT. Body leans slightly left but keeps same scale.
>
> Frame 3: **Backward burst.** Fun Bot slides/steps backward LEFT in a short controlled hop, both feet visible, compact torso, arms guarding visor. Blue/yellow exhaust trails behind/right.
>
> Frame 4: **Brake.** Reverse foot jets counterfire downward and slightly left, stopping the motion. Knees bend, torso braced, cyan eye returning from red to cyan.
>
> Frame 5: **Stabilize.** Feet plant on the baseline, shoulder steam vents puff. Arms lower back to monk guard; body upright, same head/body size as frame 1.
>
> Frame 6: **Reset.** Back to normal guarded stance, vents closing, cyan eye steady. Same baseline and proportions as frame 1.
>
> Total: 512×128. No anti-aliasing.

---

### 1-E.7 FUN BOT — dano / hurt (3 frames = 384×128)

> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right.
>
> Frame 1: **Impact.** Both feet on ground. Head snapping hard to the LEFT from a hit coming from the right. Electric sparks flying off the left side of the black visor panel. An oil droplet ejecting from the golden left elbow joint. Both arms thrown backward by the force. Cyan eye flickering rapidly between red and cyan.
>
> Frame 2: **Staggering.** Left foot sliding backward to the left, right foot pivoting. Body leaning backward to the left at an angle — not falling, but heavily off-balance. A small dent/ding visible on the silver torso. Cyan eye solid RED. Arms thrown wide. Steam puffing from a shoulder vent.
>
> Frame 3: **Stabilizing.** Both feet planted firmly on the ground. Body returning to upright. Cyan eye cycling from RED back to CYAN — stabilizing. Steam venting from the left shoulder vent. Golden joints settling. Arms returning to sides. Body upright and stable, facing right.
>
> Total: 384×128. No anti-aliasing.

---

### 1-E.8 FUN BOT — morte / death (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Each frame must be clearly different from the previous. Cyan eye gets dimmer each frame until dark in frame 6.
>
> Frame 1: **Critical hit.** Standing, feet on ground. Large cascade of electric sparks erupting from the torso and visor — lots of sparks, multiple burst points. Body thrown sideways to the right, feet still on ground but off-balance. Cyan eye flickering red. Both arms flying outward.
>
> Frame 2: **Staggering, system error.** Left foot sliding, right foot dragging. Body lurching. Cyan eye blinking in an irregular pattern — sometimes red, sometimes cyan, very rapid. Oil leaking from the golden right elbow joint — a black oil drip. Arms flailing slightly. Both feet on the ground but stumbling.
>
> Frame 3: **Right knee crashes down.** Right knee hitting the floor hard — a small impact dust cloud at the knee. Left foot still on the ground. Left hand bracing on the left thigh. Right arm hanging limp. Cyan eye dim and flickering only red. Oil dripping from the golden right knee joint onto the floor.
>
> Frame 4: **Falling forward, death spasm.** Body falling forward — torso angling toward the floor. Left foot leaving the ground. Random white steam and small electrical sparks spurting from one elbow joint erratically. Arms out. Eye barely glowing.
>
> Frame 5: **On the ground.** Body lying face-down (front of torso facing down) on the floor. Right arm stretched outward to the right. Left arm at side. Feet visible behind him. Cyan eye extremely dim — one last faint glow. Small sparks at one joint.
>
> Frame 6: **Completely powered down.** Same position as frame 5, fully still. Cyan eye completely DARK — zero glow. No sparks. A single last small puff of white steam rises from the left shoulder vent and that is all. Motionless.
>
> Total: 768×128. No anti-aliasing.

---

### 1-E.9 FUN BOT — pulo / jump (5 frames = 640×128)

> 16-bit pixel art horizontal sprite sheet, 5 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet visible. Character facing right. Body size/head size must remain constant across all 5 frames; vertical action is shown by pose, thruster FX and landing compression, not by resizing the robot. Keep large flames compact and separated from the body so the packer can keep the body metric stable.
>
> Frame 1: **Crouch + prime.** Both feet flat on the ground, golden knee joints bending deep — body crouching low. On the BOTTOM of each foot: small rocket thruster vents visible, tiny yellow flame just beginning. Arms slightly raised. Cyan eye looking up.
>
> Frame 2: **Launching upward.** Body airborne, shooting straight UP. From the BOTTOM of both feet: large yellow/orange rocket flames blasting downward (Newton's third law — fire goes down, he goes up). Legs extended straight downward. Arms at sides. Speed lines above and below. Cyan eye scanning.
>
> Frame 3: **Peak — thrusters off.** Body at the highest point, fully airborne. Feet underneath him — thruster flames OFF, just small smoke wisps from the foot vents. Body compact, knees slightly bent. Arms tucked. Cyan eye looking downward-right (scanning below). No fire in this frame.
>
> Frame 4: **Descending.** Body falling downward. Small stabilizer flames from foot vents — small yellow sparks/flames, not large rockets, just control jets. Legs extending downward for landing. Arms spreading for balance. Cyan eye looking down.
>
> Frame 5: **Heavy landing.** Both feet slamming into the ground. A clear ground crack/impact mark under both feet — jagged cracks in the ground surface. A dust and debris cloud at foot level. Knees bending deep from the heavy impact. Cyan eye flashing bright. Arms spread wide for balance. Body solid and planted.
>
> Total: 640×128. No anti-aliasing.

---

### 1-E.10a FUN BOT — super_art / Mandala de Palmas — POSES (6 frames = 768×128)

> ⚠️ **GERAÇÃO SEPARADA — sem armas, sem mísseis, sem canhões.** Gere apenas as poses do robô-monge acumulando energia nas mãos e liberando uma sequência circular de palmas. O efeito de onda/mandala é sprite separado (§10b).
>
> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right. Cyan eye bright throughout. Animation: "Mandala de Palmas" special — the robot enters a wide monk stance, rotates servo arms, then releases a huge open-palm shockwave to the RIGHT. The large shockwave/mandala is a SEPARATE sprite — do NOT draw the large effect in these pose frames; only glow on palms and small steam puffs are allowed.
>
> Frame 1: **Temple stance.** Standing, both feet planted wide and braced. Cyan eye flicking to maximum brightness. Both open palms raised in front of the chest, elbows bent. Body lowering its center of gravity. Steam vents on both shoulders hissing.
>
> Frame 2: **Servo prayer wheel.** Both forearms rotate outward in a circular monk flourish, golden joints exposed, palms glowing cyan. No panels open, no launcher tubes. Cyan eye locked forward. Body braced.
>
> Frame 3: **Double palm release — hit frame.** Both open palms thrust forward to the RIGHT at chest height. Bright cyan light blooms at both palms, body braced hard against recoil, knees bent. NO large shockwave drawn in this frame (separate sprite) — only the intense source glow at the palms. Cyan eye blinding bright.
>
> Frame 4: **Sustained vibration.** Same double-palm posture, shoulders shaking from servo pressure. Thick white steam drifting around his shoulders and chest. Body still braced. Cyan eye bright. Palms still glowing.
>
> Frame 5: **Arms folding back.** Palms dimming from blinding cyan toward normal. Arms beginning to lower in a circular monk flourish. Residual steam vents from shoulders and elbows.
>
> Frame 6: **Cooldown bow.** Both arms return to a relaxed monk guard. Heavy steam rising from both shoulder vents from the heat. Cyan eye pulsing slowly back to normal steady glow. Body upright, feet on ground.
>
> Total: 768×128. No anti-aliasing.

---

### 1-E.10b FUN BOT — super_art / Mandala de Palmas — ONDA (sprite separado, 3 frames = 384×128)

> ⚠️ **GERAÇÃO SEPARADA — apenas o efeito de palma, sem o robô.** Nenhuma arma, nenhum míssil, nenhum projétil metálico.
>
> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.**
>
> A circular cyan/yellow mechanical shockwave mandala generated by Fun Bot's open palms: concentric rings, small square pixel sparks, servo-like radial marks, and a bright cyan-white core. NO character body visible.
>
> Frame 1: **Compressed palm wave.** Small dense cyan-white ring with yellow servo sparks, moving left-to-right.
> Frame 2: **Full mandala impact.** Large circular shockwave ring, bright cyan core, yellow mechanical spark teeth around the edge.
> Frame 3: **Dissipating ring.** Larger but fading ring, cyan light thinning into white steam and scattered square pixel sparks.
>
> Total: 384×128. No anti-aliasing.

---

### 1-E.11 FUN BOT — tedio / boredom idle (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right.
>
> Frame 1: **Opening compartment.** Standing upright, both feet on ground. A small rectangular panel on his silver chest/torso OPENS outward — the panel door swinging open to the right, revealing a small hollow inside. Right hand reaching into the chest compartment. Cyan eye looking down at the compartment.
>
> Frame 2: **Taking out oil can.** Right hand pulling a classic red oil can (pear-shaped metal oil can with a long thin spout) out of the chest compartment. The oil can is now clearly visible in his right hand — red body, long thin spout pointing upward. Left hand at side. Chest compartment still open. Cyan eye looking at the oil can.
>
> Frame 3: **Squirting oil into shoulder.** Right hand raised — the oil can tilted with the spout pointing toward the LEFT golden shoulder joint (the right shoulder from our view). A tiny stream of yellow oil squirting from the spout into the joint. Left hand at side. Head tilted slightly left to watch. Cyan eye focused.
>
> Frame 4: **Rotating arm test.** Right hand holding oil can at side. Left arm rotating slowly in a circle — golden left elbow joint moving as the arm makes a slow test rotation circle. Cyan eye tracking the moving left arm. Head turning slightly to watch.
>
> Frame 5: **OK check.** Both arms at sides. Oil can in right hand. Cyan eye switching briefly to GREEN — a green glow replacing the normal cyan, like a system "OK" confirmation indicator. Then switching back to normal cyan. Head facing forward-right.
>
> Frame 6: **Storing it away.** Right hand inserting the red oil can back into the open chest compartment. The chest panel closing — the rectangular door swinging shut and clicking closed. Right hand returning to side. Both feet on ground. Body returning to normal upright stance. Cyan eye at normal steady glow.
>
> Total: 768×128. No anti-aliasing.

---

