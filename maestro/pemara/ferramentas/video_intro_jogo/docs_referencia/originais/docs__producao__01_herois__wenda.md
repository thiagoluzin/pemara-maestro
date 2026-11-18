[⬅ Voltar ao Painel de Produção](../00_PAINEL.md)

---

## 1-C: WENDA

**Bloco de design (copiar no início de cada prompt da Wenda):**
> *Character reference: White-skinned female fighter with cat-like features — soft fur tufts on cheeks, two long pointed cat ears, a long tail. Sharp mischievous eyes with distinct eyelashes, cool knowing smirk (mature, confident, not childish). Outfit: sleek black leather jacket over a graphic tee, ripped dark jeans, heavy combat boots. Her tail is always in motion. **Signature weapon: heavy iron chains — thick dark grey links, worn and slightly rusted, wrapped loosely around her right forearm with the rest hanging free. The chain can extend to full length as a whip or wrap around enemies.** Authentic 16-bit SNES pixel art style (Final Fight 3). No anti-aliasing.*

---

### 1-C.1 WENDA — idle (7 frames = 896×128)

> 16-bit pixel art horizontal sprite sheet, 7 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE IN EVERY FRAME — head to toe. Both feet on the baseline. Character facing right (side-view). Chain: thick dark grey iron links wrapped around the right forearm, excess hanging loose from the forearm downward. The chain is NOT a whip, NOT a rope — it is heavy metal links.
>
> Frame 1: Standing. Both feet flat on ground, hip-width apart. Left hip raised slightly (weight on left leg). Right arm at side, chain wrapped on forearm and hanging free. Left arm loose at side. Cat tail curved to the left. Head facing right, smirk expression.
> Frame 2: Weight shifting to center. Both feet flat. Chain swaying slightly right from the shift. Tail moving slightly right. Same arm positions.
> Frame 3: Weight on right leg, left hip raised. Chain hanging slightly to the right side, links swaying. Tail curving right. Head still facing right.
> Frame 4: Weight shifting back to center. Chain hanging straight down. Tail centered.
> Frame 5: Weight back on left leg. Chain swaying left. Tail curving left. Same as frame 1 but slightly more pronounced sway.
> Frame 6: Centering again. Right hand moves slightly, chain links shifting. Tail centered.
> Frame 7: Back to frame 1 pose — completing the loop. Weight on left leg, chain hanging, tail curved left.
>
> Total: 896×128. No anti-aliasing.

---

### 1-C.2 WENDA — walk (8 frames = 1024×128)

> 16-bit pixel art horizontal sprite sheet, 8 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY VISIBLE — head to toe. Feet touching the baseline in every frame. Character walking toward the right. Chain on right forearm — thick iron links, heavy, some links scraping lightly on the ground as she walks.
>
> Frame 1: Left foot forward, right foot back. Right arm (chain arm) low at side, chain links hanging and touching the ground slightly. Left arm swung slightly back. Tail extended backward for balance. Head facing right.
> Frame 2: Feet shifting — both feet closer to center, mid-stride. Chain swinging slightly forward. Tail moving right.
> Frame 3: Right foot forward, left foot back. Left arm swung forward. Right arm (chain) swung slightly back, chain lifting off the ground slightly. Tail extended forward.
> Frame 4: Mid-stride again, weight transferring. Chain hanging center.
> Frame 5: Left foot forward again (repeat of frame 1 but opposite arm phase). Chain scraping ground slightly.
> Frame 6: Mid-stride, chain swinging.
> Frame 7: Right foot forward. Left arm forward, right chain arm back.
> Frame 8: Completing the cycle, both feet near center, returning to frame 1 start position.
>
> Total: 1024×128. No anti-aliasing.

---

### 1-C.3 WENDA — ataques / combo (8 frames = 1024×128)

> 16-bit pixel art horizontal sprite sheet, 8 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on the baseline. Chain = thick iron metal links, heavy. NOT a rope, NOT a thin wire.
>
> **Hit 1 — Chain Whip (frames 1-2):**
> Frame 1: Right foot stepping forward. Right arm pulling back at shoulder level, chain gathered on forearm. Left hand raised for balance. Head facing right. Chain links bunched on the right forearm.
> Frame 2: Right arm snapping forward fully extended to the right — chain uncoiling from the forearm and extending outward horizontally to the right. Chain links TAUT and straight in a horizontal line. Left arm back for counterbalance. Tail whipping left. This is the strike frame.
>
> **Hit 2 — Overhead Slam (frames 3-5):**
> Frame 3: Both feet planted. Right arm raising upward, chain gathering and lifting overhead. Chain links rising above her head.
> Frame 4: Right arm raised straight above her head, chain hanging above fully extended upward. Body coiled for the downswing. Left arm out for balance.
> Frame 5: Right arm slamming downward — chain crashing down in front of her feet. Chain links hitting the floor, a small dust/impact cloud at the ground. Body leaning forward from the force.
>
> **Hit 3 — Chain Hook Arc (frames 6-8):**
> Frame 6: Right arm sweeping from low-left, chain looping outward to the right in a wide arc.
> Frame 7: Chain at full arc, extended in a wide circle in front of her body. Tail whipping right for balance. Body twisting into the swing.
> Frame 8: Follow-through — right arm finishing the swing, chain recoiling back toward the forearm. Body returning to upright stance, facing right.
>
> Total: 1024×128. No anti-aliasing.

---

### 1-C.4 WENDA — ataque_fuga / escape attack (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Chain = thick heavy iron links. Character moves toward the LEFT (retreating away from enemy on the right).
>
> Frame 1: Right foot stepping backward (toward the left). Body turning slightly away. Right arm letting the chain uncoil — links beginning to fall free from the forearm. Left arm forward for balance. Head looking back over right shoulder toward the right (she's watching the enemy while retreating). Tail forward.
>
> Frame 2: Both feet off balance, mid-retreat step. Right arm swinging backward (toward the left) — chain flying outward behind her body in a wide horizontal arc to the LEFT. Chain links spread out horizontally in the air to the left. Body leaning left. Head still looking right over shoulder.
>
> Frame 3: **Full extension — hit frame.** Chain at maximum reach to the left — thick iron links fully extended horizontally in a taut line pointing left. This hits anything chasing her. Left arm extended right for counterbalance. Body facing mostly left, head still looking right.
>
> Frame 4: Chain recoiling, links snapping back toward her right arm. Both feet landing on the ground, knees slightly bent. Body facing right again, back in stance. Chain gathering back onto the right forearm. Tail settling.
>
> Total: 512×128. No anti-aliasing.

---

### 1-C.5 WENDA — dash / dash attack (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet visible. Character dashing toward the RIGHT. Chain = thick iron links.
>
> Frame 1: **Wind-up.** Both feet on the ground, right foot back. Body coiled low. Right arm pulled all the way back behind her body — chain gathered in right hand/forearm, coiled and ready to throw. Left arm forward. Head facing right. Knees bent, ready to launch.
>
> Frame 2: **Launching forward.** Body in the air, leaning hard right. Right arm swinging forward from behind, releasing the chain — links beginning to uncoil and fly forward to the right ahead of her body. Left arm back for momentum. Feet off ground, body horizontal.
>
> Frame 3: **Full dash, chain extended — hit frame.** Body moving fast to the right. Chain fully extended forward in a horizontal line to the right — thick iron links taut and straight, the end of the chain leading forward as the strike point. Small spark/impact burst at the chain's leading end. Speed lines behind her body. Feet off ground.
>
> Frame 4: **Landing.** Both feet hitting the ground on the right side. Knees bent absorbing impact. Chain snapping back, links recoiling toward her right arm. Tail sweeping right for balance. Body upright, back in stance.
>
> Total: 512×128. No anti-aliasing.

---

### 1-C.6 WENDA — esquiva / dodge (4 frames = 512×128)

> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right.
>
> Frame 1: **Reacting.** Standing, both feet on ground. Eyes wide open, pupils visible — she sees the incoming attack. Both arms raising slightly in a defensive reflex. Head facing right. Chain on right forearm. Body upright.
>
> Frame 2: **Ducking into roll.** Body dropping low and forward — knees bending very deep, body leaning right. Left shoulder dipping toward the ground to initiate a forward roll. Chain links hanging from right arm. Tail tucking close to her body. Head low.
>
> Frame 3: **Mid-roll / low crouch.** Body crouched at its lowest — knees near the ground, back nearly horizontal. Both hands near the floor. She has passed under the attack. Chain hanging loose below her right arm. Tail flat behind her.
>
> Frame 4: **Springing back up.** Body rising fast from the crouch. Both feet planting on the ground, legs pushing upward. Body returning to upright stance. Arms rising back to guard position. Chain settling back against right arm. Tail rising. Eyes sharp and alert again.
>
> Total: 512×128. No anti-aliasing.

---

### 1-C.7 WENDA — dano / hurt (3 frames = 384×128)

> 16-bit pixel art horizontal sprite sheet, 3 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline.
>
> Frame 1: **Impact.** Standing, feet on ground. Head snapping backward to the left (hit from the right). Both cat ears flying back from the force. Right arm instinctively rising to the hit location on her torso. Left arm swinging out. Chain links on right forearm swinging from the sudden movement. Expression: pain/shock — eyes squeezed, mouth open.
>
> Frame 2: **Staggering back.** Left foot sliding backward (to the left). Body tilting backward. Head still displaced to the left. Tail lashing hard to the right from the shock. Both arms out wide for balance. Chain swinging from the stagger. Expression: surprise and irritation.
>
> Frame 3: **Recovering.** Both feet planting back on the ground. Body straightening up, facing right again. Arms returning to guard position. Chain settling. Cat ears back in normal position. Tail straight back. Expression: NOT pain — pure anger. Eyes sharp and burning. Jaw set. She's angrier than she is hurt.
>
> Total: 384×128. No anti-aliasing.

---

### 1-C.8 WENDA — morte / death (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Chain = thick iron links. Each frame has a clearly different body position from the previous one.
>
> Frame 1: **Standing stagger.** Both feet on the ground, one foot sliding sideways to the left. Body leaning hard to the left. Head still facing right — eyes open, expression defiant even in pain. Right arm out to the side, chain links on forearm swinging. Left arm reaching out for balance. Tail lashing left.
>
> Frame 2: **One hand on knee.** Left knee bending, left hand bracing on the left knee. Right foot still on the ground. Head still up — eyes open, refusing to give in. Chain hanging loose from right forearm. Body bent forward at 45 degrees. Tail dragging downward.
>
> Frame 3: **Crumpling forward.** Both knees now on the ground. Body bent forward, head dropping toward the ground. Right arm falling outward — chain links beginning to unwrap from the forearm and slide off onto the floor. Tail flat on the ground behind her.
>
> Frame 4: **Hitting the ground.** Body falling forward to the left, landing on her left side. Left arm outstretched on the floor. Right arm extending outward, chain links scattering on the floor around her arm. Head hitting the ground, eyes closing. Tail flat.
>
> Frame 5: **Lying on side.** Fully on the floor, lying on her left side. Left arm stretched out forward on the floor. Chain links lying in a loose heap on the floor in front of her right arm. Jacket open and splayed. Eyes closed. Tail flat on the floor behind her. Body completely still — visibly different pose from frame 4 (she has settled, arm pulled in).
>
> Frame 6: **Completely still.** Same position as frame 5 with one difference: tail is fully flat and motionless. Chain lies still on the floor. No movement anywhere. Eyes closed. Expression peaceful but defiant.
>
> Total: 768×128. No anti-aliasing.

---

### 1-C.9 WENDA — pulo / jump (5 frames = 640×128)

> 16-bit pixel art horizontal sprite sheet, 5 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet visible. Character facing right.
>
> Frame 1: **Crouch.** Both feet flat on the ground, knees bent deep. Body crouched low. Arms at sides, slightly raised. Chain on right forearm hanging. Tail curling upward in anticipation. Head facing right.
>
> Frame 2: **Launching.** Body airborne, rising fast. Legs extended downward, feet leaving the ground, toes pointing. Arms spreading outward. Tail trailing below and behind her body. Chain links flying upward from momentum. Head facing right.
>
> Frame 3: **Peak of jump.** Body at maximum height, fully airborne. Legs tucked — knees raised toward chest. Arms outstretched. Cat ears and tail floating upward. Chain hanging loosely from right forearm. Head facing right.
>
> Frame 4: **Descending.** Body falling downward. Legs beginning to extend downward for landing. Arms angling down. Tail angling upward behind her. Head looking down-right. Chain hanging from right arm.
>
> Frame 5: **Landing.** Both feet hitting the ground flat. Knees bent deep absorbing the impact. Arms spreading for balance. Tail stretching out straight behind her. Chain settling against right forearm. Dust puff at both feet. Head facing right.
>
> Total: 640×128. No anti-aliasing.

---

### 1-C.10a WENDA — super_art / Onda de Fogo — POSES (6 frames = 768×128)

> ⚠️ **GERAÇÃO SEPARADA — sem a grande onda de fogo neste strip.** Gere apenas as poses da Wenda erguendo e batendo a corrente no chão (a onda de fogo que varre o ambiente é um sprite separado, §10b). Apenas faíscas/brasa pequena no ponto de impacto da corrente é permitido.
>
> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right. Chain = thick heavy iron links. Animation: "Fire Wave" — she raises the chain overhead and SLAMS it into the ground, which unleashes a fire wave that sweeps the ground to the RIGHT. The big sweeping fire wave is a SEPARATE sprite — do NOT draw the large fire wave in these pose frames.
>
> Frame 1: **Gathering the chain.** Standing braced, both feet planted wide. Right arm gathering the heavy iron chain, links bunching up. Body lowering its center, coiling. Head facing right, fierce focused expression. Tail low and tense.
>
> Frame 2: **Raising overhead.** Right arm swinging the chain UP — the heavy iron links rising overhead, lifted high above her head. Body straightening tall, stretching upward, loading the slam. The chain glowing faintly hot orange/red along the links (heating up). Eyes burning. Tail whipping up.
>
> Frame 3: **Peak — chain fully raised.** Right arm fully extended straight above her head, the chain hanging at its highest point overhead, links now glowing bright orange-hot. Body tensed, knees bending, weight loaded for the downward slam. Head facing right. Left arm out for balance.
>
> Frame 4: **Slam — hit frame.** Right arm crashing the chain STRAIGHT DOWN onto the ground in front of her feet, links smashing into the floor to the right. A bright burst of orange embers, sparks, and a small ignition flash at the floor impact point (the large fire wave itself is a separate sprite leaving along the ground to the right). Body leaning hard forward from the force, hair and tail thrown forward. Cat ears pinned back.
>
> Frame 5: **Follow-through.** Body still leaning forward over the impact point, chain links resting on the ground where they struck, small flames and embers flickering up around the chain. She watches the wave travel right. Tail settling. Determined expression.
>
> Frame 6: **Reset.** Standing back upright, facing right. Chain recoiling back, gathering onto her right forearm. Last embers dying at her feet. Eyes sharp, confident smirk returning. Tail back to neutral motion.
>
> Total: 768×128. No anti-aliasing.

---

### 1-C.10b WENDA — super_art / Onda de Fogo — ONDA (sprite separado, 4 frames = 512×128)

> ⚠️ **GERAÇÃO SEPARADA — apenas a onda de fogo, sem o personagem.** A onda varre rasteira pelo chão, da esquerda para a direita.
>
> 16-bit pixel art horizontal sprite sheet, 4 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it.**
>
> A ground-hugging wave of fire sweeping LEFT to RIGHT (a low fire wall that travels along the floor, NOT a fireball in the air). The wave sits at the BOTTOM of each frame on the baseline, with flames licking upward. NO character body visible. Fire colors: bright white-yellow base, orange body, red outer tips, dark smoke rising above. The wave's leading edge always faces RIGHT.
>
> Frame 1: **Ignition.** A small-to-medium burst of fire erupting at the ground, leading edge starting to push right. Bright and compact.
> Frame 2: **Full wave — peak.** A tall, wide wall of fire spanning the ground, leading edge surging to the right, tallest flames in the center, embers and sparks thrown up. The most intense frame.
> Frame 3: **Rolling forward.** The fire wave stretched out wider and lower, the leading edge pushed further right, the trailing left side beginning to die down into embers and smoke.
> Frame 4: **Dissipating.** The fire mostly burned out — scattered low flames, glowing embers on the ground, and grey smoke rising. Fading to almost nothing.
>
> Total: 512×128. No anti-aliasing.

---

### 1-C.11 WENDA — tedio / boredom idle (6 frames = 768×128)

> 16-bit pixel art horizontal sprite sheet, 6 frames, 128×128 each, solid neon green (#00FF00) background. **Leave a generous wide gap of solid neon green between every frame — clear, considerable spacing separating each frame; frames must NOT touch or overlap, each frame fully isolated with padding around it (CRITICAL for Wenda: the chain must stay fully inside its own frame and never bleed into the neighboring frame).** [Character reference above.]
>
> ⚠️ FULL BODY IN EVERY FRAME. Feet on baseline. Character facing right.
>
> Frame 1: **Taking out the can.** Standing, both feet flat on ground. Left hand reaching into the left jacket pocket and pulling out a bright red soda can (cylindrical metal can, clearly a soda/drink can). Right arm at side, chain on right forearm. Bored expression — mouth slightly open, eyes half-lidded. Head facing right. Tail hanging behind her.
>
> Frame 2: **Examining it.** Standing. Left hand raised, holding the red soda can at face level — looking at it sideways with a bored/tired expression. Right arm at side, chain hanging. Tail swishing slowly to the right. Head facing right with eyes on the can.
>
> Frame 3: **Popping the tab.** Standing. Left hand holds the can, right thumb (from the right hand) pressing down on the pull tab on top of the can — a tiny pop effect (small burst lines) at the tab. Both feet flat on ground. Chain on right forearm. Tail straight.
>
> Frame 4: **Drinking.** Standing, head tilted back looking upward. Left hand holding the red soda can tilted up to her mouth — drinking. Eyes closed. Right arm at side, chain hanging. Tail relaxed, hanging still. Throat visible as she drinks.
>
> Frame 5: **Wiping mouth.** Head returning forward, facing right. Left hand lowering the can from her mouth. Right hand rising — back of the right hand wiping across her mouth. Chain on right forearm moving with the arm. Bored-satisfied expression.
>
> Frame 6: **Tossing the can.** Left hand swinging and releasing the can to the right — the can is visibly mid-air, flying to the right and downward (she's tossing it away carelessly). She is not looking at where it goes — head facing right, eyes forward. Right arm back at side, chain on forearm. Back in relaxed stance. Tail neutral.
>
> Total: 768×128. No anti-aliasing.

---

