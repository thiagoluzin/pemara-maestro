# Motion and action gates

Required operational reference, loaded by phase. Current AGENTS and route-specific contracts prevail.

## Directed-camera qualification — owner update 2026-10-09

For new multi-shot live-action scenes, apply the shared camera evidence contract in
`E:/Pemara/.agents/skills/pemara-video-production-lead/references/camera-evidence-and-actor-protection.md`.
The generic translation requirement below does not force a move in every shot. A directed locked
camera may preserve impact/reaction readability while physical action progresses. Reject generated
holds/resets and empty duration; do not reject a motivated dramatic pause or stable camera solely
for lacking translation. Preserve already-approved route-specific movement contracts.

## Universal Transition Motion Gate

Use a DIRECT_KINETIC_CUT between approved, compatible moving sources, remain within one
uninterrupted take, or use a generated continuous-action connector only when the route permits
it and the scope authorizes it. generatedConnectorAllowed: false forbids all generated bridges.
Crossfade/xfade, freeze frames, holds, static tails, motion resets and occlusion used to hide a
motion swap are forbidden. A permitted connector must inherit body, object, effect and camera
velocity, execute a causal irreversible action and deliver useful motion to the next take.

The same contract applies inside every generated take, including takes that are not connectors.

Useful subject, environment and camera motion must occupy the full duration. Require explicit
motion beats in `0-30%`, `30-70%` and `70-100%`. If the event finishes early and the remainder is a
held pose or near-static camera, reject it even when no frames are literally identical.

For first/last-frame connectors, both anchors must come from source intervals with visible motion
before and after the selected frame. A frozen tail pose or a static opening frame is not a valid
anchor and must be blocked before GPU work.

Every transition must prove all four pillars in its contract before GPU work and again by visual QC
before approval or assembly:

1. `evident_camera`: physical camera translation with visible perspective change. Zoom, rack focus,
   pan/tilt, shake or drift alone do not pass.
2. `real_depth`: foreground, midground and background with differential motion, occlusion or coherent
   scale change. A flat 2D parallax effect does not pass.
3. `internal_action`: one readable physical event plus at least two scene elements moving
   independently from the camera. Light, smoke and particles may support but never replace it.
4. `clear_progression`: materially different beginning, middle and end states, a changed final state,
   and a motivated hard cut, musical impact or directional exit.

Missing any pillar is an automatic rejection. Also reject reset, gratuitous reversal, static tails
and living-photo motion. This rule applies across every project, model and transition workflow.

## High-Energy Combat Gate

Quando a luta envolve personagens com golpes reconhecíveis, carregue `pemara-live-action-combat-director`. A escolha do golpe, seu proprietário, mecanismo, cor e resultado são direção imutável; frases como “let H3 choose the exact strikes” são proibidas. O modelo só resolve micro-movimento entre âncoras aprovadas.

For a continuous combat take longer than five seconds, require a written energy contract before
GPU work:

- at least two distinct physical exchanges or one exchange plus an irreversible launch/deflection;
- visible anticipation, contact or evasion, displacement and reaction/recovery so impacts have mass;
- at least one motivated camera reorientation or axis change while geography remains readable;
- foreground, fighters and background changing relative position; a single straight-line flight or
  endless lateral track does not pass;
- an explicit outcome for every projectile or strike. It must hit, be blocked, be dodged or be
  redirected with a readable vector; it may not pass through a body without consequence;
- useful motion and a changed state at the end, with the cut occurring before a held pose.

For continuous action, use `freezedetect` as a warning gate with a default maximum near-static
interval of 0.35 seconds and reject a near-static terminal tail over 0.15 seconds. These thresholds
do not replace visual review and may be relaxed only for an intentionally directed dramatic pause,
never to excuse slow combat.

When cast count, body scale, color, wings, tails, limbs or transformation state are fragile, mark
the take `identity_risk: high|critical` and strengthen qualified controls and temporal QC. Use
approved intermediate anchors only where the mode permits; a qualified start-only combat route
must not receive future guides by a generic rule. Inspect the actual
MP4 at every impact/transform beat and at 0%, 25%, 50%, 75% and 100%; an approved input image does
not prove identity continuity in the generated frames.

If the same integral generation strategy repeats an identity, anatomy or static-tail failure twice,
stop repeating it. Revise staging, event density or the qualified control strategy; controlled
microsegments or approved anchors apply only when permitted by the route. Review the resulting
main take as one artifact, with original identity and approved aspects preserved.
