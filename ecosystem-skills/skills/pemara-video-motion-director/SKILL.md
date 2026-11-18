---
name: pemara-video-motion-director
description: "Direção de movimento, beats, controles, âncoras e QC temporal de vídeos Pemara. Use para takes MiniMax H3 no Maestro, ação física, câmera, cauda estática, continuidade cinética e correção de movimento; preservar motor e regras vigentes."
---

## Câmera e preservação dos atores — 2026-10-09

Para novas sequências live action, use mapa/câmeras/estados compartilhados e teste uma fronteira do bloco piloto. Câmera fixa motivada pode demonstrar a ação interna e a causalidade; não confundir esse caso com freeze, hold ou pose gerada sem progressão. Esta atualização prevalece sobre exigência genérica de translação em todo plano, mantendo contratos específicos de movimento já aprovados. Sem revisão temporal, não emitir parecer positivo de movimento.

Para o mapa, as evidências temporais e os reparos, consulte o [contrato de câmera](../pemara-video-production-lead/references/camera-evidence-and-actor-protection.md). Preserve o motor e o escopo já autorizados.


# Pemara Video Motion Director

## Production handoff

Receive the sequence and take brief from `pemara-video-production-lead`, acting from
`pemara-performance-director` and geography/camera from `pemara-cinematography-director`.
Translate those decisions to controls and motion; do not invent additional actions, change
identity or hide poor performance with camera movement. Record stimulus, contact, response,
support and useful exit intervals in the actual MP4. See the shared production-quality-contract
for independent review dimensions. A detector score never establishes artistic quality.


No duelo M08–M16 do projeto FFVIII, leia primeiro `ffviii-gunblade-duel-production`; seu contrato
V8 específico prevalece sobre permissões genéricas de RIFE, trim, retime e conectores.

## Core Rule

Protect the GPU first. If the user says the GPU should rest, do not launch ComfyUI jobs, training, inference, or video generation. Work only on research, docs, prompts, JSON, QC notes, and scripts.

FPS policy is permanent: never generate, save, approve, register, remaster, or deliver a video below 24 FPS. In particular, 16 FPS is forbidden even for Wan native previews and smoke tests. Keep the model's native temporal window when useful, but encode reviewable intermediates at 24 or 30 FPS and masters at 60 FPS. Reject a workflow or imported asset below 24 FPS instead of silently accepting it.

GPU render policy is permanent: use the available GPU path for video generation, compatible interpolation/upscale, and final encoding. For FFmpeg delivery files, prefer NVIDIA NVENC and record the encoder in QC. Never silently fall back to software encoding such as `libx264`; if the GPU codec is unavailable, stop and report it. CPU work is acceptable only for orchestration, timestamps, lightweight filters, and muxing that do not replace GPU encoding.

If `E:/Pemara/maestro/pemara/dados/flags/video_generation_paused.flag` exists, video generation is paused. Do not bypass it unless the user explicitly orders a GPU video test.

Honor the current owner authorization, pause flags and actual GPU/queue state. Do not treat an old scheduling note as a permanent ban or assume that an empty queue means free VRAM. This skill does not authorize generation by itself.

## Workflow

1. Check the project status and current queue.
2. Read `take_queue.json`, recent QC reports, and the latest preview path.
3. Invoke `pemara-cinematic-take-director` and approve art direction, duration, story change, event, reaction and cut motivation before writing a motion prompt. For Maestro live action, read `E:/Pemara/.agents/skills/pemara-cinematic-take-director/references/vejito-liveaction-standard.md`; Vejito is the owner-declared canonical production pattern.
4. Never generate takes from unapproved images.
5. For each take, require:
   - approved keyframe JSON;
   - one visible event with beginning, middle, and end;
   - camera move beyond simple zoom;
   - foreground and background parallax;
   - a visible response from the environment or another scene element, without forcing particles, flashes or transformation into every scene.
6. Choose duration from the directed beats and qualified frame grid. The specific continuous-combat eight-second contract takes precedence over a generic 3–5 second suggestion; do not shorten or extend an approved route automatically.
7. Prefer a short test block before a full render.
8. Mark weak previews as rejected in QC docs before regenerating.

## Live-action release order and antiregression

The source itself must pass, in order, art direction, cinematic direction, motion and technical QC,
then explicit human review. Do not infer an art pass from FPS, decode, freeze detection or a motion
score. If a humanoid, creature or environment changes from physical live action into animation,
cel shading, game render, clean plastic CGI or cosplay, reject the whole take.

For a sequence using the canonical Vejito pattern:

- plan all shared moving boundaries before video generation;
- keep control microsegments internal and expose only main takes in Maestro;
- render and review main takes serially;
- never assemble a take not explicitly approved by the owner;
- never mix visual routes, anchor generations or rejected fragments in one final timeline;
- use hard cuts only on approved action handoffs.

RIFE, retiming, trimming and upscale are downstream cadence/resolution operations. They are allowed
only after the native source passes art, cinematic and motion review. They cannot repair a bad
performance, mismatched camera vectors, identity drift or animated-looking material. If several
takes or boundaries regress, archive the active route and rebuild from the visual bible instead of
adding connectors.

Run the deterministic gate supplied by `pemara-cinematic-take-director` at contract, anchor and
assembly stages. A technical pass with an art or cinematic failure remains a rejected artifact.

## Universal Transition Motion Gate

Before every I2V/T2V take or transition, read the full Universal Transition Motion Gate in
`references/motion-quality-gates.md`. Preserve all four pillars, active beats and compatible
kinetic cuts; generated connectors require permission from the route and scope.

## High-Energy Combat Gate

For combat, long action, transformation or fragile anatomy/count, read the full High-Energy
Combat Gate in `references/motion-quality-gates.md` and use `pemara-live-action-combat-director`.
Specific start-only controls take precedence over generic intermediate-anchor suggestions.

## Engine and Runtime Admission

For Maestro production, preserve MiniMax H3, the current owner-selected route after LTX removal
on 2026-10-08. Do not reinstall LTX, compatibility IC-LoRAs or offer any alternate-engine fallback.
Require SageAttention + Spectrum effectively connected to sampling and preserve the qualified
profile, geometry, frames and audio. See references/model-research.md for the current contract.
Historical research outside Maestro does not change its active production engine.

Before every GPU batch, verify the actual ComfyUI queue, VRAM/process ownership, required node/plugin
load status and selected acceleration backend. A healthy HTTP endpoint is not proof that required
plugins loaded. If the chosen CUDA/Vulkan path reports plugin or driver errors, stop before spending
the batch; do not silently switch backend or fall back to CPU.

## Controlled Character Acting

For human or humanoid acting in the Maestro, keep MiniMax H3 and use approved
anchors plus the engine's supported controls. A driver-video experiment is a separate research
route and cannot silently replace the selected production engine. Any external face/body transfer
requires explicit authorization and its own identity/privacy review.

## Editorial Gate

Before measuring motion, verify narrative scale. If the sequence declares disaster, corruption, war, collapse, or apocalypse, require visible persistent damage in foreground, midground, and background. Camera displacement, particles, flashes, and color wipes do not count as catastrophe by themselves. Reject a high-motion clip when the environment remains structurally unchanged or the next shot forgets the damage.

Prefer two 4n+1 microtakes with distinct approved keyframes for cause and consequence over one overloaded prompt. The video prompt may animate destruction already staged in the keyframe; it must not be expected to invent the entire disaster from a calm image.

Reject a technically clean clip when it repeats one action, adds no story information, has no reaction, or could end two seconds earlier without loss. Camera motion and particles never count as a dramatic event by themselves.

## Related Pemara Skills

Use the imported custom skills as specialist layers instead of stretching this skill into every job:

- `ai-video-intro-pipeline`: full intro/cutscene pipeline, take order, QC, montage, audio, logo, upscale, and registration package.
- `video-production`: general video creation, ffmpeg assembly, contact sheets, codecs, and output formats.
- `image-production`: approved keyframe generation/editing, visual QC, recut, alpha/chroma, and upscale before video.
- `creative-director`: narrative, concept, prompt refinement, and turning an idea into executable shot specs.
- `game-audio-designer`, `game-audio-reactive`, `audio-analysis`: music/SFX direction, reactive audio rules, BPM/key/loudness/stem analysis.
- `animation-engineer`, `phaser-animation-turbo`, `sprite-animation`, `sprite-image-reading`, `hero-sprite-scaling`: Phaser sprite animation, frame timing, runtime scale, sprite sheet inspection, and humanized movement.
- `qa-automation-engineer`, `test-engineer`, `performance-optimizer`: browser/game validation, regression checks, perf profiling, and release confidence.

## Model Strategy

Use `references/model-research.md` when choosing models or workflows.

Maestro uses H3; other engines belong only to separately authorized research. Verify live node/model
support through MCP before any authorized generation. More anchors are not always better: preserve
the start-only combat route when future anchors caused anticipation or static tails. Do not train
or add a video LoRA as an automatic answer to weak direction.

## Motion Prompt Pattern

Use this structure for every take:

```text
Animate this approved keyframe as a real cinematic video, not a living photo.
Preserve composition, objects and style.
Camera: [specific move].
Foreground: [object crossing or parallax].
Background: [separate parallax].
Event: [beginning, middle, end].
Environment/secondary response: [causal visible change, no decorative effect required].
Forbidden: static hold, simple zoom only, slideshow, text drift, new characters.
```

## QC

Use `scripts/qc_motion_probe.py` for quick technical checks. Technical motion is not enough; still inspect contact sheets or the MP4 visually.

Reject if:

- it looks like a still image with breathing;
- only brightness changes;
- only a slow zoom happens;
- object identity drifts;
- text is invented or deformed;
- the take adds unrequested characters, changes cast count, or invents anatomy;
- an environmental-only take adds humans, bodies, faces, eyes or humanoid silhouettes forbidden by its specific brief. These prohibitions do not exclude the approved cast in an acting scene.

## Project Files

For Ritmos da Revolta:

- Project: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta`
- Queue: `take_queue.json`
- Main operational doc: `E:/Pemara/maestro/pemara/ferramentas/video_intro_jogo/docs/07_execucao_intro_por_takes.md`
- Research doc: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/04_pesquisa_movimento_i2v.md`
- Markerless mocap guide: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/11_markerless_motion_capture_wan_animate.md`
- Motion library: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/motion_library`
