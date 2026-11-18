"""Authorize only the owner-approved P02 impact-axis anchor for serial H3 video."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
WORK = PROJECT / "work" / "v5_p02_impact_axis"
PILOT_MANIFEST = WORK / "production_manifest_v5_p02_impact_axis.json"
ARCHIVE = PROJECT / "archive" / "before_v5_p02_video_authorization"
TAKE_ID = "P02"
REQUEST_ID = "b84f8e2ad53440479de35e248d6e538a"
ANCHOR_SHA256 = "8454829586e9770c4f52e2236769d41366b4c9f653a2fba043267a70386b71d8"

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

ALIGNMENT_LOCK = (
    " The boot moves straight down along the exact P01-matched screen axis and strikes "
    "the crown of Android 16; no lateral slide, no sideways dodge and no missed impact."
)
MALFORMED_ALIGNMENT = (
    "5. The boot moves straight down along the exact P01-matched screen axis and strikes "
    "the crown of Android 16; no lateral slide, no sideways dodge and no missed impact.166667-SECOND"
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    queue = read_json(QUEUE_PATH)
    manifest = read_json(MANIFEST_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}

    if str(base.get("status") or "").lower() != "approved_for_video":
        raise RuntimeError("P02 ainda nao possui ancora aprovada para video.")
    if str(base.get("candidate_request_id") or "") != REQUEST_ID:
        raise RuntimeError("A aprovacao nao corresponde ao candidato P02 revisado pelo proprietario.")
    image = Path(str(base.get("file") or ""))
    sidecar_path = Path(str(base.get("metadata") or ""))
    if not image.is_file() or not sidecar_path.is_file():
        raise FileNotFoundError("Imagem ou sidecar aprovado do P02 ausente.")
    if not image.resolve().is_relative_to(PROJECT.resolve()):
        raise RuntimeError("Ancora P02 fora do projeto.")
    if digest(image) != ANCHOR_SHA256 or digest(image) != str(base.get("image_sha256") or "").lower():
        raise RuntimeError("SHA256 da ancora P02 divergiu da aprovacao.")
    sidecar = read_json(sidecar_path)
    human = sidecar.get("human_review") if isinstance(sidecar.get("human_review"), dict) else {}
    if (
        str(sidecar.get("validation_status") or "").lower() != "approved_for_video"
        or str(human.get("decision") or "").upper() != "APPROVED"
        or human.get("explicit_human_confirmation") is not True
    ):
        raise RuntimeError("P02 nao possui evidencia completa de aprovacao humana.")
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    if video.get("output_active") or video.get("output_preview"):
        raise RuntimeError("P02 ja possui video ativo; nova geracao recusada.")

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, MANIFEST_PATH):
        target = ARCHIVE / source.name
        if not target.exists():
            shutil.copy2(source, target)

    prompt = str(take.get("animation_prompt") or "")
    prompt = prompt.replace(MALFORMED_ALIGNMENT, "5.166667-SECOND")
    if ALIGNMENT_LOCK.strip() not in prompt:
        anchor_sentence = "THE EXACT APPROVED TIGHT START FRAME."
        if anchor_sentence not in prompt:
            raise RuntimeError("Sentenca de entrada do prompt P02 nao foi encontrada.")
        prompt = prompt.replace(anchor_sentence, anchor_sentence + ALIGNMENT_LOCK, 1)
    take["animation_prompt"] = prompt
    take["status"] = "VIDEO_PENDING_GENERATION"
    take["maestro_status"] = "READY"
    take["render_authorized"] = True
    take["role"] = "v5_p02_impact_axis_video_authorized"
    take["maestro_notes"] = (
        "Ancora P02 aprovada pelo proprietario. Gerar somente este take em serie, "
        "preservando o eixo P01 da bota sobre a cabeca e bloqueando rabo/traseira."
    )
    generation = take.get("video_generation") if isinstance(take.get("video_generation"), dict) else {}
    generation.update({
        "render_authorized": True,
        "fps": 24,
        "frames": 124,
        "steps": 20,
        "guidance": 1.0,
        "start_end_frame_enabled": False,
        "require_approved_start_frame": True,
        "require_approved_end_frame": False,
        "visual_only_pass": True,
        "native_audio_authorized": False,
        "prompt": prompt,
    })
    take["video_generation"] = generation
    direction = take.get("direction_contract") if isinstance(take.get("direction_contract"), dict) else {}
    direction["direction_status"] = "approved_for_video"
    take["direction_contract"] = direction
    qc = take.setdefault("qc", {})
    qc["status"] = "video_authorized_pending_serial_generation"
    qc["human_visual_approval"] = "pending_video_review"
    qc["anchor_human_approval"] = {
        "status": "approved",
        "request_id": REQUEST_ID,
        "reason": str(human.get("reason") or ""),
        "image_sha256": ANCHOR_SHA256,
    }
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
        "evidence": "Contract ready; generated MP4 still required.",
    }

    queue["status"] = "V5_P02_IMPACT_AXIS_READY"
    queue["render_authorized"] = True
    queue["render_authority"] = (
        "Owner approved the corrected P02 anchor and previously ordered video generation."
    )
    queue["continuous_action_contract"] = CONTINUOUS_POLICY
    queue["universal_transition_motion_gate"] = {"required": True}
    queue["story_batch_policy"] = {
        "enabled": True,
        "version": "gohan_v5_p02_impact_axis_v1",
        "batch_size": 1,
        "render_order": [TAKE_ID],
        "strict_contiguous": True,
        "require_all_base_images_ready": True,
        "fill_eligible_across_batches": False,
        "require_full_batch": True,
        "allow_incomplete_correction_batch": False,
        "control_surface": "P02_QC_before_any_following_work",
    }

    manifest["status"] = "V5_P02_IMPACT_AXIS_IN_PRODUCTION"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["render_authorized"] = True
    manifest["render_authority"] = queue["render_authority"]
    batches = manifest.setdefault("anchor_candidate_batches", {})
    record = batches.setdefault("v5_p02_reframed", {})
    record.update({
        "status": "APPROVED_BY_OWNER_FOR_VIDEO",
        "take_id": TAKE_ID,
        "request_id": REQUEST_ID,
        "sha256": ANCHOR_SHA256.upper(),
        "video_generation_authorized": True,
    })
    manifest["directed_correction_v5_p02_impact_axis"] = {
        "reason": "Previous anchor missed Android 16's head; approved replacement restores P01 impact axis.",
        "method": "single 5.166667-second start-only MiniMax H3 visual take",
        "pilot_take_ids": [TAKE_ID],
        "generate_serially": True,
        "other_takes_blocked_until_p02_qc": True,
        "foley_status": "BLOCKED_UNTIL_PICTURE_LOCK",
    }

    pilot = {
        "schema_version": "gohan_ssj2_v5_p02_impact_axis",
        "project_id": PROJECT.name,
        "title": "Gohan SSJ2 - P02 impact-axis correction",
        "objective": "Complete one aligned mechanical impact and carry Gohan into active reaction without a static tail.",
        "sequence_stakes": "Android 16's mechanical head is destroyed and Gohan's contained anger begins to rupture.",
        "universal_transition_motion_gate": {"required": True},
        "continuous_action_contract": CONTINUOUS_POLICY,
        "generation": {"profile": "minimax_h3_fl2va_int8_720p24", "fps": 24, "frames": 124},
        "takes": [take],
        "gpu_policy": {"serial_only": True, "max_concurrent_video_jobs": 1},
        "audio": {"status": "BLOCKED_UNTIL_PICTURE_LOCK"},
    }
    atomic_json(QUEUE_PATH, queue)
    atomic_json(MANIFEST_PATH, manifest)
    atomic_json(PILOT_MANIFEST, pilot)
    print(json.dumps({
        "ok": True,
        "takeId": TAKE_ID,
        "pilotManifest": str(PILOT_MANIFEST),
        "anchorSha256": ANCHOR_SHA256.upper(),
        "renderAuthorized": True,
        "serialOnly": True,
        "fps": 24,
        "frames": 124,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
