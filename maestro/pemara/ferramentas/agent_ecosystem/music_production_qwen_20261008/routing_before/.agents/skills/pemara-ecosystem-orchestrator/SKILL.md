---
name: pemara-ecosystem-orchestrator
description: Orchestrates the Pemara agent/skill ecosystem. Use when deciding which Pemara skills, agents, workflows, or tools should handle tasks across Maestro, Loja, generative image/video, LoRA training, ComfyUI, Phaser games, sprites, music/SFX, automation, QA, deployment, cleanup, or GPU scheduling.
---

# Pemara Ecosystem Orchestrator

## Video production routing

Use `pemara-video-production-lead` for the complete production and quality review. Route acting to `pemara-performance-director`, image design to `pemara-cinematography-director`, and narrative assembly to `pemara-film-editor`. Work in phases with at most three primary skills at a time. These are responsibilities; do not spawn agents merely because profiles exist.

For Maestro, preserve the current H3-only route, Sage + Spectrum, and approved SeedVR2 3B → exact RIFE60 → DLSS 5 finishing with existing audio. Current owner instructions supersede older engine or finishing notes.

## Core Rule

Route first, execute second. Choose the smallest specialist set that can finish the task safely.

Protect the GPU. If GPU is resting or outside an allowed window, do not start training, ComfyUI generation, local video/image inference, or heavy model loading. Work on docs, prompts, JSON, QC, queue prep, research, and code that does not launch GPU jobs.

## Hard Gates

- Do not bypass routing. Always identify the domain and selected specialist skills before changing files or running jobs.
- Do not use more than three primary skills unless the task is explicitly cross-domain.
- Do not load vendor/NVIDIA/TAO/NeMo/VSS skills unless the request explicitly needs that stack.
- Do not start GPU training, ComfyUI generation, image/video inference, or heavy model loading while GPU rest is active.
- A GPU exception is valid only when the user's current request explicitly authorizes GPU use now.
- Do not rely on old chat context to override a newer GPU/rest/scheduling rule.
- Do not run destructive cleanup unless the target path is resolved and confirmed inside the intended directory.
- Do not invent new Pemara paths when a canonical path already exists.
- Route every change to an online route, auth, admin, upload, payment, tenant,
  gateway, tunnel, webhook, agent tool or public release through
  `pemara-online-security-guardian` before publication.
- A passing build or scanner is not a security release. Require negative tests,
  deployed-artifact evidence, rollback and an explicit gate decision.

## Routing

Use these specialists:

- Video direction and motion: `pemara-video-motion-director`.
- Intro/cutscene by takes: `ai-video-intro-pipeline`.
- Image/keyframe creation and QC: `image-production`.
- Sprunki LoRA training and QC: `sprunki-lora-trainer`.
- Video assembly, ffmpeg, contact sheets, codecs: `video-production`.
- Creative brief, prompt, script, shot intent: `creative-director`.
- Expressive narration, voice cloning with consent, engine selection, and voice QC:
  `pemara-voice-performance-director`.
- Music, SFX, audio analysis, reactive audio: `game-audio-designer`, `game-audio-reactive`, `audio-analysis`.
- Phaser sprite animation and scale: `phaser-animation-turbo`, `sprite-animation`, `sprite-image-reading`, `animation-engineer`, `hero-sprite-scaling`.
- Beat-em-up combat, enemies, bosses, hitboxes: `beatemup-combat-designer`, `balance-tuner`.
- Store/marketing automation and scraping: `automation-engineer`, then `qa-automation-engineer` for validation.
- Online security, RLS, IDOR, secrets, XSS/uploads and public exposure:
  `pemara-online-security-guardian`, with `saas-pentest-hardening` for detailed review.
- Legacy code understanding or unknown broken systems: `code-archaeologist`, `debugger`.
- Frontend without framework: `web-frontend-vanilla`, `vanilla-web-patterns`.
- Build/release/performance: `game-build-flow`, `demo-release-engineer`, `performance-optimizer`, `test-engineer`.
- NVIDIA/TAO/NeMo/VSS skills: use only when the task explicitly needs that stack.
- Public agent/MCP/tool discovery: run `scripts/hubmesh_radar.py` as a read-only
  signal source. Never auto-install a repository from a roundup.

## Workflow

1. Identify domain: loja, Maestro, video, image, sprites/game, audio, automation, infra, cleanup, or QA.
2. Check safety: production impact, destructive file changes, credentials, GPU window, running locks.
   If the task changes an online trust boundary, add the security guardian as a primary skill.
3. Pick at most three primary skills. Add support skills only when necessary.
4. Read the selected skills before acting.
5. Prefer existing Pemara paths and docs over inventing new locations.
6. Produce a concrete artifact: code change, doc, queue, QC report, script, config, or verified command result.
7. Validate with `scripts/skill_inventory.ps1` after changing skills.

## Maestro Proof Gates

- Do not claim Maestro access is fixed from a health endpoint or a synthetic POST alone. Validate
  the real browser form, CSRF, Origin/Fetch Metadata path and that a safe disposable credential
  reaches authentication; keep real passwords undisclosed.
- Do not claim a take, approval or final is visible from a manifest write alone. Query the live
  project API, confirm the resolved filename/hash and, when owner review is required, open or play
  that exact artifact.
- Keep only main takes visible during take review. When the owner requests one integral review,
  expose only that film and preserve anchors, microsegments, rejections and older versions as
  rollback rather than catalog clutter.
- Treat cached UI state and chat wording as signals, not authoritative identity. Reconcile project
  id, take id, request id, file path and SHA-256 before applying an approval.
- Before a GPU batch, verify queue, lease/VRAM, process ownership, required plugin/node load status
  and the selected acceleration backend. A running ComfyUI endpoint does not prove its workflow can
  execute, and backend/plugin errors must not trigger a silent CPU or alternate-engine fallback.

For ecosystem scouting, require license, maintainer activity, dependency/secret
scan, overlap analysis, sandbox smoke, and human approval before adoption.

## Canonical Paths

- Skills: `E:/Pemara/.agents/skills`
- Profiles: `E:/Pemara/.agents/profiles`
- Agent audit docs: `E:/Pemara/maestro/pemara/ferramentas/agent_ecosystem`
- Video global engine: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine`
- Intro game project: `E:/Pemara/maestro/pemara/ferramentas/video_intro_jogo`
- Loja: `E:/Pemara/loja`
- Marketing social: `E:/Pemara/marketing_social`
- Online security evidence: `E:/Pemara/security` and `E:/Pemara/logs/security_audit`

## Improvement Rules

When improving skills:

- Keep `SKILL.md` short and procedural.
- Move long examples, project facts, and model tables to `references/`.
- Add scripts only for repeated checks or fragile operations.
- Add `agents/openai.yaml` to important custom skills.
- Validate every changed skill with the system validator.
- Do not duplicate large vendor/NVIDIA skill packs.

See `references/pemara-skill-map.md` for the active skill groups and improvement backlog.
