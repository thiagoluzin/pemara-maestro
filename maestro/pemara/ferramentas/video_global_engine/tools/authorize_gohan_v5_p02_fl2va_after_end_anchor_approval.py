"""Authorize the exact owner-approved P02 start/end anchors for one serial FL2VA render."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
PILOT_PATH = PROJECT / "work" / "v5_p02_impact_axis" / "production_manifest_v5_p02_impact_axis.json"
TAKE_ID = "P02"
START_REQUEST = "b84f8e2ad53440479de35e248d6e538a"
START_SHA = "8454829586e9770c4f52e2236769d41366b4c9f653a2fba043267a70386b71d8"
END_REQUEST = "3924fa874b034f6c8ad112d6642f3eba"
END_SHA = "5d934a3ff9e6bfc0fbe0127df71e7132302a54931b2d5599f5c1c05747621a2d"
SEED = 2026082022

PROMPT = """ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION ACTION TAKE, USING THE EXACT OWNER-APPROVED START FRAME AND ARRIVING AT THE EXACT OWNER-APPROVED END FRAME. Preserve the approved Gohan, Android 16 materials, Cell boot, ruined arena, storm lighting and P01-matched impact axis. 0-25%: from frame one the same boot moves STRAIGHT DOWN with zero lateral drift, strikes the exact center crown and visibly crushes the mechanical head into broken ceramic-metal plates, bent frame parts, circuits, wires and harmless sparks. This is one decisive mechanical impact, with no blood or gore. The boot and straight lower leg immediately retract vertically through the top edge; Cell is then completely absent. 25-70%: the low camera physically trucks left along the fresh floor crack, overtakes foreground fragments and crosses dust and stones moving at different depths. Gohan closes distance continuously while the intact head is gone and only crushed mechanical debris remains. 70-100%: Gohan converts shock into an active forward launch, gold pressure expands and one blue-white electrical arc crosses the arena. He reaches the exact approved end-frame composition with clothing, hair, debris, camera and electricity still moving at the cut. ABSOLUTE LOCKS: no intact Android 16 face or head after the impact; no Cell after the first quarter; no tail, pointed tip, curved appendage, stinger, cable, tentacle, green arc, boot-to-tail morph or leg-to-tail morph; no repeated stomp, missed impact, lateral boot slide, pose, static hold, freeze, reset, crossfade, anime, game render, text, logo or watermark."""

CONTINUOUS_POLICY = {
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_anchor(anchor: dict, request_id: str, expected_sha: str, label: str) -> tuple[Path, Path]:
    if str(anchor.get("status", "")).lower() != "approved_for_video":
        raise RuntimeError(f"Ancora {label} nao esta aprovada para video.")
    if str(anchor.get("candidate_request_id", "")) != request_id:
        raise RuntimeError(f"Request ID da ancora {label} divergiu.")
    image = Path(str(anchor.get("file", "")))
    metadata = Path(str(anchor.get("metadata", "")))
    if not image.is_file() or not metadata.is_file():
        raise FileNotFoundError(f"Arquivo ou sidecar da ancora {label} ausente.")
    actual = sha256(image)
    if actual != expected_sha or actual != str(anchor.get("image_sha256", "")).lower():
        raise RuntimeError(f"SHA256 da ancora {label} divergiu.")
    sidecar = read_json(metadata)
    review = sidecar.get("human_review") if isinstance(sidecar.get("human_review"), dict) else {}
    if (str(sidecar.get("validation_status", "")).lower() != "approved_for_video"
            or str(review.get("decision", "")).upper() != "APPROVED"
            or review.get("explicit_human_confirmation") is not True):
        raise RuntimeError(f"Evidencia de aprovacao humana da ancora {label} incompleta.")
    return image, metadata


def main() -> None:
    queue = read_json(QUEUE_PATH)
    manifest = read_json(MANIFEST_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    start = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    end = take.get("end_anchor_candidate") if isinstance(take.get("end_anchor_candidate"), dict) else {}
    start_file, _ = verify_anchor(start, START_REQUEST, START_SHA, "inicial")
    end_file, _ = verify_anchor(end, END_REQUEST, END_SHA, "final")
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    if video.get("output_active") or video.get("output_preview"):
        raise RuntimeError("P02 ja possui video ativo; recusando sobreposicao.")

    take["animation_prompt"] = PROMPT
    take["status"] = "VIDEO_PENDING_GENERATION"
    take["maestro_status"] = "READY"
    take["render_authorized"] = True
    take["role"] = "v5_p02_two_anchor_fl2va_video_authorized"
    take["maestro_notes"] = "Gerar uma vez em serie usando exatamente as ancoras inicial e final aprovadas; preservar candidatos reprovados como rollback."
    generation = take.setdefault("video_generation", {})
    generation.update({
        "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot",
        "profile": "minimax_h3_fl2va_int8_720p24",
        "width": 1280,
        "height": 720,
        "fps": 24,
        "frames": 124,
        "steps": 20,
        "guidance": 1.0,
        "start_end_frame_enabled": True,
        "require_approved_start_frame": True,
        "require_approved_end_frame": True,
        "render_authorized": True,
        "visual_only_pass": True,
        "native_audio_authorized": False,
        "directed_correction_seed": SEED,
        "prompt": PROMPT,
    })
    take.setdefault("direction_contract", {}).update({
        "direction_status": "approved_for_video",
        "evident_camera": "physical left truck with foreground parallax",
        "real_depth": "crack fragments dust and Gohan move at distinct depths",
        "internal_action": "impact crush retraction reaction and forward launch",
        "clear_progression": "aligned impact to debris to advancing Gohan",
    })
    qc = take.setdefault("qc", {})
    qc["status"] = "two_anchors_approved_pending_serial_generation"
    qc["human_visual_approval"] = "pending_video_review"
    qc["end_anchor_human_approval"] = {
        "status": "approved", "request_id": END_REQUEST, "image_sha256": END_SHA
    }
    qc["transition_motion_gate"] = {
        "status": "contract_pass_pending_generated_video_qc",
        "evident_camera": False, "real_depth": False, "internal_action": False,
        "clear_progression": False, "continuous_action": False,
        "motion_across_all_intervals": False, "no_crossfade": True,
        "no_freeze": False, "no_static_tail": False, "no_reset": False,
        "evidence": "Two exact owner-approved anchors locked; generated MP4 still required."
    }

    queue["status"] = "V5_P02_TWO_ANCHOR_FL2VA_READY"
    queue["render_authorized"] = True
    queue["render_authority"] = "Owner approved the exact P02 start and end anchors and ordered video generation."
    queue["continuous_action_contract"] = CONTINUOUS_POLICY
    queue["universal_transition_motion_gate"] = {"required": True}
    queue["story_batch_policy"] = {
        "enabled": True, "version": "gohan_v5_p02_two_anchor_v1", "batch_size": 1,
        "render_order": [TAKE_ID], "strict_contiguous": True,
        "require_all_base_images_ready": True, "fill_eligible_across_batches": False,
        "require_full_batch": True, "allow_incomplete_correction_batch": False,
        "control_surface": "P02_QC_before_any_following_work",
    }

    manifest["status"] = "V5_P02_TWO_ANCHOR_FL2VA_IN_PRODUCTION"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["render_authorized"] = True
    manifest["render_authority"] = queue["render_authority"]
    manifest["directed_correction_v5_p02_impact_axis"] = {
        "reason": "Prompt-only attempts failed either tail anatomy or visible mechanical destruction.",
        "method": "one exact-start/exact-end 5.166667-second MiniMax H3 FL2VA visual take",
        "start_anchor": str(start_file), "start_sha256": START_SHA,
        "end_anchor": str(end_file), "end_sha256": END_SHA,
        "pilot_take_ids": [TAKE_ID], "generate_serially": True,
        "other_takes_blocked_until_p02_qc": True, "foley_status": "BLOCKED_UNTIL_PICTURE_LOCK",
    }

    pilot = {
        "schema_version": "gohan_ssj2_v5_p02_two_anchor_fl2va",
        "project_id": PROJECT.name,
        "title": "Gohan SSJ2 - P02 two-anchor impact correction",
        "objective": "Destroy the mechanical head on the aligned axis and carry Gohan into uninterrupted forward motion.",
        "sequence_stakes": "Android 16 is reduced to mechanical debris and Gohan's contained anger breaks into action.",
        "universal_transition_motion_gate": {"required": True},
        "continuous_action_contract": CONTINUOUS_POLICY,
        "generation": {"profile": generation["profile"], "fps": 24, "frames": 124, "seed": SEED,
                       "start_anchor_sha256": START_SHA, "end_anchor_sha256": END_SHA},
        "takes": [take],
        "gpu_policy": {"serial_only": True, "max_concurrent_video_jobs": 1},
        "audio": {"status": "BLOCKED_UNTIL_PICTURE_LOCK"},
    }
    atomic_json(QUEUE_PATH, queue)
    atomic_json(MANIFEST_PATH, manifest)
    atomic_json(PILOT_PATH, pilot)
    print(json.dumps({"ok": True, "takeId": TAKE_ID, "seed": SEED,
                      "startSha256": START_SHA.upper(), "endSha256": END_SHA.upper(),
                      "pilotManifest": str(PILOT_PATH), "renderAuthorized": True}, indent=2))


if __name__ == "__main__":
    main()
