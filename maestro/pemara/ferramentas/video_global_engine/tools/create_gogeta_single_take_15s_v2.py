#!/usr/bin/env python3
"""Create the reversible one-take Gogeta MiniMax H3 project."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "gogeta_fusao_danca_reels_vertical_15s"
PROJECT_ID = "gogeta_fusao_single_take_15s_v2"
SOURCE = ROOT / "projetos" / SOURCE_ID
PROJECT = ROOT / "projetos" / PROJECT_ID
NOW = datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def copy_anchor(anchor_id: str) -> dict:
    source_image = SOURCE / "keyframes" / f"{anchor_id}.png"
    source_meta = SOURCE / "keyframes" / f"{anchor_id}.json"
    target_image = PROJECT / "keyframes" / source_image.name
    target_meta = PROJECT / "keyframes" / source_meta.name
    shutil.copy2(source_image, target_image)
    metadata = read_json(source_meta)
    metadata["project_id"] = PROJECT_ID
    metadata["image_file"] = str(target_image)
    metadata["image_sha256"] = sha256(target_image)
    metadata["reuse_context"] = {
        "source_project": SOURCE_ID,
        "reason": "owner-approved anchors reused for one continuous 15-second variant",
        "copied_at": NOW,
    }
    write_json(target_meta, metadata)
    return metadata


def main() -> None:
    if PROJECT.exists():
        raise SystemExit(f"Refusing to overwrite existing project: {PROJECT}")
    for directory in (
        "audio",
        "edit",
        "input",
        "keyframes",
        "logs",
        "output",
        "prompts",
        "qc",
        "refs",
        "takes",
        "takes/maestro_generated",
        "training_exports",
    ):
        (PROJECT / directory).mkdir(parents=True, exist_ok=True)

    start_meta = copy_anchor("anchor_01")
    end_meta = copy_anchor("anchor_04")
    start_file = PROJECT / "keyframes" / "anchor_01.png"
    end_file = PROJECT / "keyframes" / "anchor_04.png"

    source_manifest = read_json(SOURCE / "project_manifest.json")
    project_manifest = deepcopy(source_manifest)
    project_manifest.update(
        {
            "project_id": PROJECT_ID,
            "title": "Gogeta Fusão — single take explosivo 15s v2",
            "idea": "Uma tomada contínua e acelerada: dança canônica, fusão em Gogeta base e transformação Super Saiyajin tradicional sem corte perceptível.",
            "objective": "Eliminar a sensação de montagem entre fases com uma única geração FL2VA de 15 segundos, ação contínua e energia crescente.",
            "duration_target_seconds": 15.0,
            "created_at": NOW,
            "updated_at": NOW,
            "maestro_status": "IN_PROGRESS",
            "status": "IN_PROGRESS",
            "render_authorized": True,
            "approved_anchors": [
                {
                    "id": "anchor_01",
                    "role": "start_frame",
                    "file": str(start_file),
                    "sha256": start_meta["image_sha256"],
                    "status": "APPROVED",
                },
                {
                    "id": "anchor_04",
                    "role": "end_frame",
                    "file": str(end_file),
                    "sha256": end_meta["image_sha256"],
                    "status": "APPROVED",
                },
            ],
            "owner_approval": {
                "status": "AUTHORIZED_FOR_SINGLE_VISUAL_CANDIDATE",
                "directive": "Gerar um clipe único de 15 segundos, mais rápido, mais ação, mais explosivo e sem transição perceptível.",
                "source": "owner_message_in_codex",
                "recorded_at": NOW,
            },
            "replacement_candidates": [],
            "final_output": {
                "status": "PENDING_HUMAN_VISUAL_REVIEW",
                "source_project_preserved": str(SOURCE),
            },
        }
    )
    project_manifest["audio"] = {
        "strategy": "visual_only_until_picture_lock",
        "native_audio_authorized": False,
        "sound_follow_deferred": True,
    }

    continuous_policy = {
        "required": True,
        "generated_connector_required_between_takes": True,
        "crossfade_forbidden": True,
        "freeze_frame_forbidden": True,
        "static_tail_forbidden": True,
        "motion_handoff_required": True,
        "full_duration_motion_required": True,
        "three_interval_motion_required": True,
        "moving_transition_anchors_required": True,
    }
    gate_policy = {
        "required": True,
        "policy_version": "2.0",
        "pillars": [
            "evident_camera",
            "real_depth",
            "internal_action",
            "clear_progression",
        ],
    }
    prompt = (
        "[Shot 1] One uninterrupted fifteen-second vertical 9:16 ultra-photorealistic live-action cinematic take, "
        "starting exactly from the supplied approved first frame and ending exactly on the supplied approved final frame. "
        "Preserve Goku on screen-left and Vegeta on screen-right, their faces, black hair, costumes, anatomy, scale, crater, "
        "moon and orange-blue night palette until the fusion physically resolves. The tempo is urgent and athletic, never slow motion. "
        "The camera is one continuous low 35 mm physical steadicam-orbit: it trucks rapidly forward through foreground rocks during the dance, "
        "curves clockwise around the fingertip contact and fusion vortex, then cranes upward and pulls back under the final shockwave; real position, "
        "perspective, overlap and parallax change continuously, with no digital zoom and no hidden camera reset. "
        "From 0.00 to 3.20 seconds, execute the canonical Dragon Ball FU-SION-HAH choreography literally and quickly: exactly three synchronized "
        "lateral steps toward center while all four arms sweep in a 180-degree arc over their heads; both pairs of arms then cross the body and point "
        "outward while each outer knee rises briefly to 90 degrees; without holding, both torsos lean inward, both outer legs extend straight away, "
        "the upper arms arc overhead and the lower arms bend at chest height, and exactly two separate pairs of index fingertips meet simultaneously, "
        "one upper pair and one lower pair. From 3.20 to 6.30 seconds, that visible double contact ignites one continuous orange-blue spiral; both bodies, "
        "hands and faces remain readable while the same energy pulls them through a tightening vortex, crater cracks race outward, layered boulders lift and "
        "the cloud ring twists. From 6.30 to 9.60 seconds, the two readable silhouettes orbit once inside the translucent energy and compress visibly, never "
        "vanishing behind a white screen; exactly one black-haired base-form Gogeta emerges from the same center already moving, drops hard, lands and rises in "
        "one fluid action, retaining the correct fusion vest, sash, face and anatomy. From 9.60 to 12.50 seconds, the same Gogeta drives one foot forward and "
        "powers up from the ground: pressure rings ripple, the crater ruptures, his black hair progressively stiffens and changes black to bronze to gold while "
        "his same face, body and costume remain continuous. From 12.50 to 15.04 seconds, traditional Super Saiyan Gogeta is fully formed with golden hair and "
        "teal eyes; blue-white lightning, a colossal golden aura and a violent expanding shockwave split the cloud ring and blast foreground boulders past the "
        "lens as the camera rapidly pulls back and cranes up, arriving at the supplied final frame only at the last instant while aura, dust, cloth and lightning "
        "are still moving. Make the transformation spectacular, picturesque and physically legible rather than abstract. No cut, no transition, no dissolve, "
        "no wipe, no crossfade, no flash-only substitution, no static hold, no slow motion, no repeated pose, no generic dance, no breakdance, no crossed-fist "
        "ending, no single fingertip contact, no face morph, no body melting, no duplicate character, no extra body, limbs or fingers, no golden hair before base "
        "Gogeta emerges, no costume replacement, no environment reset, no text, no logo, no watermark and no native audio."
    )
    motion_contract = {
        "camera_evidence": {
            "movement": "A low 35 mm camera trucks forward, performs one clockwise physical orbit, then cranes up and pulls back without interruption.",
            "physical_translation": True,
            "perspective_change": "Foreground rocks cross the lens while fighter overlap, crater horizon, moon position and subject scale change continuously.",
        },
        "real_depth": {
            "foreground": "Jagged rocks, dust and shockwave debris repeatedly pass close to the lens.",
            "midground": "The dance, fingertip contact, fusion, landing and transformation unfold on the crater floor.",
            "background": "Crater walls, mountains, moon and cloud ring move at slower differential rates.",
            "differential_motion": "Foreground debris moves fastest, bodies and energy occupy the middle rate, and distant terrain drifts slowest.",
            "occlusion_or_scale_change": "The orbit changes body overlap and fingertip geometry; the pullback visibly reduces Gogeta's scale after the shockwave.",
        },
        "internal_action": {
            "primary_event": "Canonical dance becomes double fingertip contact, one fusion, base Gogeta and then traditional Super Saiyan Gogeta.",
            "independent_elements": [
                "Both fighters execute synchronized full-body choreography before their bodies fuse into one.",
                "Cracks, dust, boulders, cloud ring, aura and lightning evolve independently of camera motion.",
            ],
            "camera_independent": True,
        },
        "progression": {
            "start": "Two black-haired fighters rush through the canonical dance toward double fingertip contact.",
            "middle": "Orange-blue energy compresses two visible silhouettes and releases one black-haired base Gogeta into a hard landing.",
            "end": "The same Gogeta completes a traditional golden Super Saiyan transformation inside a landscape-splitting shockwave.",
            "end_state_change": "Two separate fighters have irreversibly become one fully transformed Super Saiyan Gogeta and the crater is heavily ruptured.",
            "exit_or_cut": "End externally only on the active shockwave peak after reaching the supplied final frame; there is no internal edit.",
        },
        "continuity": {
            "editorial_method": "single_continuous_take",
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "entry_motion": "Camera, clothing, hair and dust accelerate immediately from the approved opening frame.",
            "exit_motion": "Aura, lightning, debris and the physical camera pullback remain active through the final frame.",
            "interval_motion": {
                "early_0_30": "Rapid canonical dance, double fingertip contact and ignition occur while the camera trucks and begins its orbit.",
                "middle_30_70": "The vortex tightens, two silhouettes visibly compress, and base Gogeta emerges, lands and rises without a visual curtain.",
                "late_70_100": "The power-up changes black hair to gold as crater, aura, lightning and camera pullback accelerate into the final frame.",
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        },
    }
    negative_rules = [
        "no cut",
        "no transition",
        "no dissolve",
        "no crossfade",
        "no flash-only substitution",
        "no freeze frame",
        "no static tail",
        "no slow motion",
        "no generic dance",
        "no breakdance",
        "no crossed finishing fists",
        "no single fingertip contact",
        "no face morphing",
        "no body melting",
        "no duplicate character",
        "no extra limbs or fingers",
        "no identity drift",
        "no early golden hair",
        "no costume morphing",
        "no environment reset",
        "no generated text",
        "no watermark",
        "no native audio",
    ]
    shot_contract = {
        "story_purpose": "Transformar rivalidade, sincronização e poder em uma única escalada visual sem costura editorial.",
        "dramatic_question": "A dança canônica conseguirá fundir os dois e liberar o Super Saiyajin antes que a energia destrua o vale?",
        "story_change": "Dois guerreiros separados tornam-se um Gogeta base e então um Super Saiyajin tradicional em movimento contínuo.",
        "motion_beats": {
            "start": "Dança FU-SION-HAH canônica em alta velocidade e contato duplo dos indicadores.",
            "middle": "Vórtice laranja-azul comprime duas silhuetas e lança Gogeta base ao chão.",
            "end": "Gogeta transforma cabelo preto em dourado e rompe céu e cratera com a onda final.",
        },
        "reaction": "Goku e Vegeta absorvem a pressão da sincronia; Gogeta aterrissa e responde transformando essa pressão em poder crescente.",
        "cut_motivation": "Nenhum corte interno; encerramento externo somente no ápice móvel da onda de choque dourada.",
        "duration_reason": "Quinze segundos acomodam três mudanças irreversíveis — dança, fusão e transformação — dentro de uma única trajetória contínua.",
        "distinct_story_events": 6,
        "camera": {
            "movement": "Fast low physical truck-in, one clockwise orbit, then a rapid crane-up pullback.",
            "physical_translation": True,
            "lens": "35 mm live-action vertical framing",
            "focus": "full-body choreography, readable hands, transparent fusion energy and deep layered destruction",
        },
        "keyframes": {
            "start": "keyframes/anchor_01.png",
            "end": "keyframes/anchor_04.png",
            "approved": True,
            "approval_source": "explicit owner approval of replacement anchors in Codex",
        },
        "visual_references": {
            "start_frame_file": str(start_file),
            "start_frame_approved": True,
            "end_frame_file": str(end_file),
            "end_frame_approved": True,
            "shared_boundary_contract": "One FL2VA generation connects the approved start and end frames without editorial transition.",
        },
        "variants": {"duration_seconds": 15.0},
        "negative_rules": negative_rules,
        "transition_motion_contract": motion_contract,
    }
    take = {
        "id": "S01",
        "slug": "single_take_danca_fusao_super_saiyajin",
        "title": "Single take — dança, fusão e Super Saiyajin",
        "objective": "Executar toda a progressão aprovada em uma geração contínua, rápida e explosiva.",
        "status": "PLANNED",
        "maestro_status": "PLANNED",
        "timeline_start_seconds": 0.0,
        "target_duration_seconds": 15.0,
        "animation_prompt": prompt,
        "render_authorized": True,
        "video_generation": {
            "profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
            "width": 720,
            "height": 1280,
            "fps": 24,
            "frames": 362,
            "steps": 20,
            "guidance": 1.0,
            "camera_speed": 1.15,
            "start_end_frame_enabled": True,
            "require_approved_end_frame": True,
            "maestro_job_enabled": True,
            "visual_only_pass": True,
            "native_audio_authorized": False,
            "review_fps": 60,
            "review_duration_seconds": 15.0,
            "review_interpolator": "RIFE 4.6",
            "review_encoder": "h264_nvenc",
            "review_delivery_required_before_ready": True,
        },
        "shot_contract": shot_contract,
        "transition": {"is_transition": False},
        "base_image": {
            "status": "approved_for_video",
            "file": str(start_file),
            "metadata": str(PROJECT / "keyframes" / "anchor_01.json"),
            "model": start_meta.get("model", "OpenAI built-in image generation"),
            "image_sha256": start_meta["image_sha256"],
            "approved_at": start_meta.get("approved_at"),
            "approval_source": start_meta.get("approval_source", "owner_message_in_codex"),
            "prompt": start_meta.get("prompt", ""),
        },
        "qc": {
            "status": "pending_video_generation",
            "human_anchor_approval": "approved_by_owner",
            "human_visual_approval": "pending_single_take_playback",
            "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK_AND_OWNER_DIRECTIVE",
            "transition_motion_gate": {
                "status": "pending_video_generation",
                "evident_camera": False,
                "real_depth": False,
                "internal_action": False,
                "clear_progression": False,
                "continuous_action": False,
                "motion_across_all_intervals": False,
                "moving_anchor_context": False,
                "no_crossfade": True,
                "no_freeze": True,
                "no_static_tail": True,
                "no_reset": False,
                "evidence": "Awaiting the generated single-take MP4 and human visual review.",
            },
        },
        "audio_direction": {
            "delivery_required": False,
            "strategy": "visual_only",
            "status": "deferred_until_picture_lock",
            "native_audio_authorized": False,
            "human_listening_required": False,
            "dialogue_generation_authorized": False,
        },
        "audio_directive": {
            "usage_authorized": False,
            "source": "visual_revision_only",
        },
        "video": {
            "status": "planned",
            "audio_delivery": {
                "status": "NOT_REQUIRED",
                "required": False,
                "dialogue_required": False,
                "source_kind": "none",
                "human_listening_required": False,
                "language": "none",
                "message": "Passe visual; o novo follow de som depende da aprovação deste take.",
            },
        },
        "maestro_last_job_id": "",
        "maestro_last_error": "",
        "maestro_updated_at": NOW,
        "maestro_director_requests": [],
        "maestro_upscale_status": "",
        "maestro_upscale_error": "",
        "maestro_upscale_job_id": "",
        "maestro_upscale_attempt": 0,
    }
    take_queue = {
        "schema_version": "1.1",
        "project_id": PROJECT_ID,
        "methodology": "pemara_single_take_continuous_action_v2",
        "status": "ready_for_authorized_generation",
        "updated_at": NOW,
        "render_authorized": True,
        "primary_orchestration_policy": "minimax_h3_take_contract@2026-08-16",
        "engine_policy": {
            "primary_take_orchestration": {
                "status": "ACTIVE_UNTIL_OWNER_OVERRIDE",
                "generation_profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
                "backend": "ComfyUI MiniMax H3 official local workflow",
                "text_encoder": "Qwen3-VL-32B MiniMax H3 NVFP4 AWQ",
                "conditioning_profile": "identity_locked_first_last_frame",
            },
            "audio_directive": {
                "authority": "owner_only",
                "default_without_explicit_directive": "visual_only",
                "native_generation_without_directive": "forbidden",
            },
        },
        "assembly": {
            "preview": {"width": 720, "height": 1280, "fps": 24, "format": "mp4"},
            "final": {"width": 1080, "height": 1920, "fps": 60, "format": "mp4"},
            "target_duration_seconds": 15.0,
            "native_h3_frames": 362,
            "native_h3_effective_seconds": 361 / 24,
            "edit_rule": "after approval, trim only the still-moving tail to exact 15.000 seconds",
        },
        "universal_transition_motion_gate": gate_policy,
        "continuous_action_contract": continuous_policy,
        "global_negative_rules": negative_rules,
        "takes": [take],
        "final_output": {"status": "PENDING_HUMAN_VISUAL_REVIEW"},
    }
    production_take = {
        "id": "S01",
        "slug": take["slug"],
        "is_transition": False,
        "shot_contract": deepcopy(shot_contract),
        "qc": deepcopy(take["qc"]),
    }
    production_manifest = {
        "schema_version": "2.0",
        "project_id": PROJECT_ID,
        "sequence_id": "gogeta_single_take_15s_v2",
        "status": "READY_FOR_AUTHORIZED_GENERATION",
        "created_at": NOW,
        "updated_at": NOW,
        "render_authorized": True,
        "universal_transition_motion_gate": gate_policy,
        "continuous_action_contract": continuous_policy,
        "takes": [production_take],
        "final_output": {"status": "PENDING_HUMAN_VISUAL_REVIEW"},
    }

    write_json(PROJECT / "project_manifest.json", project_manifest)
    write_json(PROJECT / "take_queue.json", take_queue)
    write_json(PROJECT / "production_manifest.json", production_manifest)
    (PROJECT / "prompts" / "S01_single_take_prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    (PROJECT / "FIXLOG.md").write_text(
        "# Gogeta single take v2\n\n"
        f"Created: {NOW}\n\n"
        "- Original approved three-take project preserved untouched.\n"
        "- Reuses only owner-approved anchor_01 and anchor_04 with SHA-256 verification.\n"
        "- One MiniMax H3 FL2VA shot, 362 native frames at 24 fps (15.041667 s effective).\n"
        "- No cut, crossfade, dissolve, freeze, static tail or native audio.\n"
        "- Candidate remains pending technical QC and human visual review.\n",
        encoding="utf-8",
    )
    print(PROJECT)
    print(f"start_sha256={sha256(start_file)}")
    print(f"end_sha256={sha256(end_file)}")


if __name__ == "__main__":
    main()
