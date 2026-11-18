"""Preserve the failed P02 preview and authorize one no-tail directed correction."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
PILOT_MANIFEST = PROJECT / "work" / "v5_p02_impact_axis" / "production_manifest_v5_p02_impact_axis.json"
TAKE_ID = "P02"
PREVIOUS = PROJECT / "takes" / "maestro_generated" / "take_P02_5dbd449c340c4b00_minimax_h3_preview.mp4"
PREVIOUS_SHA256 = "bd37097cc02865de68203a8e9e4306222cbbc9760d764b384411f9cf0b9ec5ac"
SEED = 3125717376079737788

PROMPT = (
    "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION ACTION TAKE FROM THE EXACT APPROVED START FRAME. "
    "Preserve the exact approved Gohan, Android 16 mechanical head, one cropped Perfect Cell lower leg and boot, ruined arena, storm lighting and P01-matched impact axis. "
    "0-30%: from frame one the same boot moves STRAIGHT DOWN with zero lateral drift and completes exactly one hard mechanical impact at the center crown of Android 16. Gohan keeps sprinting. The low camera is physically knocked left while metal, ceramic, circuits, dust and stones burst laterally. "
    "Immediately after contact, the SAME recognizable boot and lower leg retract vertically through the TOP edge while retaining shin, ankle, heel, sole and boot silhouette. The leg never bends, stretches, curves, tapers, sprouts a tip or changes into another anatomy. "
    "30-70%: by 1.30 seconds every part of Cell is completely outside the image and never returns. The entire upper-right and right edge show ONLY empty storm sky, airborne dust and ordinary rocks: no green, yellow, black or spotted body shape. The camera races left along the new floor crack, overtakes foreground fragments and passes the approaching Gohan with strong perspective change. "
    "70-100%: Gohan never poses. He plants through the shockwave, one gold pressure surge expands, one blue-white electrical rupture travels across the arena, and he immediately launches forward past the moving camera. Cut mid-launch with camera, Gohan, dust, stones and electricity still moving. "
    "ABSOLUTE CHARACTER LIMIT: Cell exists only as the original single boot and straight lower leg during the opening impact, then is fully absent after 25% of the take. "
    "FORBIDDEN: tail; pointed tail tip; curved appendage; whip shape; green arc; stinger; cable; tentacle; snake shape; rear appendage; boot-to-tail morph; leg-to-tail morph; any Cell body after 1.30 seconds; pelvis; hips; back; rear silhouette; wings; second leg; repeated stomp; missed impact; lateral boot slide; static hold; freeze; reset; crossfade; tear; liquid; blood; gore; duplicate character; anime; game render; text; logo; watermark."
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not PREVIOUS.is_file() or digest(PREVIOUS) != PREVIOUS_SHA256:
        raise RuntimeError("O candidato P02 rejeitado nao corresponde ao arquivo inspecionado.")
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    queue = read_json(QUEUE_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if str(base.get("status") or "").lower() != "approved_for_video":
        raise RuntimeError("A ancora P02 aprovada deixou de estar valida.")

    previous_record = {
        "file": PREVIOUS.as_posix(),
        "sha256": PREVIOUS_SHA256,
        "job_id": "5dbd449c340c4b0086d6907a1c4dabe0",
        "seed": SEED,
        "status": "REJECTED_INTERNAL_QC",
        "reason": (
            "Impacto alinhado e movimento forte, mas o H3 inventou uma cauda verde com ponta preta "
            "no alto a direita por volta de 2.5 s."
        ),
        "qc_contact_sheet": (
            PROJECT / "qc" / "p02_impact_axis_5dbd449c" / "contact_2fps.png"
        ).as_posix(),
        "rejected_at": now,
    }

    take["animation_prompt"] = PROMPT
    take["status"] = "VIDEO_PENDING_GENERATION"
    take["maestro_status"] = "READY"
    take["render_authorized"] = True
    take["role"] = "v5_p02_single_directed_no_tail_correction"
    take["maestro_notes"] = (
        "Candidato anterior preservado e reprovado no QC interno por cauda. "
        "Executar uma unica correcao com a mesma ancora e semente, preservando o impacto alinhado."
    )
    generation = take.setdefault("video_generation", {})
    generation.update({
        "render_authorized": True,
        "prompt": PROMPT,
        "fps": 24,
        "frames": 124,
        "start_end_frame_enabled": False,
        "require_approved_start_frame": True,
        "require_approved_end_frame": False,
        "visual_only_pass": True,
        "native_audio_authorized": False,
        "directed_correction_seed": SEED,
    })
    take["video"] = {
        "status": "not_generated",
        "previous_candidates": [previous_record],
    }
    qc = take.setdefault("qc", {})
    qc["status"] = "p02_no_tail_correction_pending_generation"
    qc["human_visual_approval"] = "pending_video_review"
    qc["directed_correction_attempt"] = 1
    qc["previous_candidate"] = previous_record
    qc["transition_motion_gate"] = {
        "status": "contract_pass_pending_generated_video_qc",
        "evident_camera": False,
        "real_depth": False,
        "internal_action": False,
        "clear_progression": False,
        "continuous_action": False,
        "motion_across_all_intervals": False,
        "no_crossfade": True,
        "no_freeze": False,
        "no_static_tail": False,
        "no_reset": False,
        "evidence": "Previous candidate rejected for visible tail; directed correction pending.",
    }
    contract = take.setdefault("shot_contract", {})
    contract["story_change"] = "Aligned impact destroys the mechanical head, Cell exits completely, and Gohan converts the shock into forward energy."
    contract["cut_motivation"] = "Cut during Gohan's renewed launch with camera, debris and electricity retaining velocity."
    transition = contract.setdefault("transition_motion_contract", {})
    transition["progression"] = {
        "start": "one aligned boot impact while Gohan and the low camera move",
        "middle": "the boot exits vertically and Cell disappears while the camera chases the crack",
        "end": "Gohan launches through the moving camera path with one electrical rupture",
        "end_state_change": "intact head becomes debris and pursuit becomes active attack",
        "exit_or_cut": "mid-launch directional handoff",
    }
    continuity = transition.setdefault("continuity", {})
    continuity.update({
        "editorial_method": "single_continuous_take",
        "continuous_action": True,
        "motion_handoff": True,
        "action_occupies_full_duration": True,
        "entry_motion": "straight boot downstroke, Gohan sprint, dust and low camera",
        "exit_motion": "Gohan, debris, electricity and camera retain velocity",
        "interval_motion": {
            "early_0_30": "aligned impact and physical lateral camera displacement",
            "middle_30_70": "Cell absent; crack chase and Gohan reaction",
            "late_70_100": "one electrical rupture and renewed Gohan launch",
        },
        "crossfade_frames": 0,
        "freeze_frames": 0,
        "static_hold_frames": 0,
    })

    queue["status"] = "V5_P02_NO_TAIL_CORRECTION_READY"
    queue["render_authorized"] = True
    queue["route_revision"] = {
        "take_id": TAKE_ID,
        "attempt": "P02C1",
        "method": "same approved anchor and seed; remove generated tail after impact",
        "previous_candidate": previous_record,
    }
    atomic_json(QUEUE_PATH, queue)

    manifest = read_json(MANIFEST_PATH)
    manifest["status"] = "V5_P02_NO_TAIL_CORRECTION_IN_PRODUCTION"
    manifest["render_authorized"] = True
    manifest["p02_directed_video_correction"] = {
        "attempt": 1,
        "same_anchor": True,
        "same_seed": SEED,
        "previous_candidate": previous_record,
        "video_generation_authorized": True,
    }
    atomic_json(MANIFEST_PATH, manifest)

    pilot = read_json(PILOT_MANIFEST)
    pilot["takes"] = [take]
    pilot["route_revision"] = {
        "attempt": "P02C1",
        "method": "same approved anchor and seed; Cell absent after opening impact",
        "previous_candidate": previous_record,
    }
    atomic_json(PILOT_MANIFEST, pilot)
    print(json.dumps({
        "ok": True,
        "takeId": TAKE_ID,
        "attempt": "P02C1",
        "sameSeed": SEED,
        "previousCandidatePreserved": PREVIOUS.as_posix(),
        "renderAuthorized": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
