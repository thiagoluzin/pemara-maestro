"""Authorize only the owner-approved V5 action-first pilot for serial GPU work."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE_PATH = PROJECT / "take_queue.json"
PROJECT_MANIFEST_PATH = PROJECT / "project_manifest.json"
WORK = PROJECT / "work" / "v5_action_first_pilot"
PILOT_MANIFEST_PATH = WORK / "production_manifest_v5_action_first.json"
ARCHIVE = PROJECT / "archive" / "before_v5_p01_video_authorization"
PILOT_ID = "P01"

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
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    queue = read_json(QUEUE_PATH)
    manifest = read_json(PROJECT_MANIFEST_PATH)
    take = next(
        item for item in queue.get("takes", [])
        if isinstance(item, dict) and str(item.get("id")) == PILOT_ID
    )
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if str(base.get("status") or "").lower() != "approved_for_video":
        raise RuntimeError("P01 ainda nao possui ancora aprovada para video.")
    image = Path(str(base.get("file") or ""))
    sidecar_path = Path(str(base.get("metadata") or ""))
    if not image.is_file() or not sidecar_path.is_file():
        raise FileNotFoundError("Imagem ou sidecar aprovado do P01 ausente.")
    if not image.resolve().is_relative_to(PROJECT.resolve()):
        raise RuntimeError("Ancora P01 fora do projeto.")
    if sha256(image) != str(base.get("image_sha256") or "").lower():
        raise RuntimeError("SHA256 da ancora P01 divergiu da fila.")
    sidecar = read_json(sidecar_path)
    human = sidecar.get("human_review") if isinstance(sidecar.get("human_review"), dict) else {}
    if (
        str(sidecar.get("validation_status") or "").lower() != "approved_for_video"
        or str(human.get("decision") or "").upper() != "APPROVED"
        or human.get("explicit_human_confirmation") is not True
    ):
        raise RuntimeError("P01 nao possui evidencia completa de aprovacao humana.")
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    if video.get("output_active") or video.get("output_preview"):
        raise RuntimeError("P01 ja possui video; nenhuma nova geracao foi autorizada.")

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, PROJECT_MANIFEST_PATH):
        target = ARCHIVE / source.name
        if not target.exists():
            shutil.copy2(source, target)

    take["status"] = "VIDEO_PENDING_GENERATION"
    take["maestro_status"] = "READY"
    take["render_authorized"] = True
    take["role"] = "v5_action_first_pilot_video_authorized"
    take["maestro_notes"] = (
        "Ancora P01 aprovada explicitamente pelo proprietario. Gerar somente este "
        "piloto, executar QC completo e nao liberar os demais antes do resultado."
    )
    generation = (
        take.get("video_generation")
        if isinstance(take.get("video_generation"), dict)
        else {}
    )
    generation["render_authorized"] = True
    generation["fps"] = 24
    generation["frames"] = 124
    generation["steps"] = 20
    generation["guidance"] = 1.0
    generation["start_end_frame_enabled"] = False
    generation["require_approved_start_frame"] = True
    generation["require_approved_end_frame"] = False
    generation["visual_only_pass"] = True
    generation["native_audio_authorized"] = False
    take["video_generation"] = generation
    take["duration_seconds"] = 5.166667
    take["frames"] = 124
    take["direction_contract"] = {
        "story_purpose": "Substituir a rota estatica por uma entrada ja dentro da acao.",
        "dramatic_question": "Gohan alcanca Android 16 antes de a unica descida terminar?",
        "story_change": (
            "A bota descendente e a perseguicao ativa viram impacto mecanico, "
            "fissura e a primeira ruptura energetica de Gohan."
        ),
        "reaction": "Gohan planta contra a onda de choque; Cell recua do proprio impacto.",
        "cut_motivation": (
            "Cortar durante aura, raio, detritos e camera ainda em deslocamento."
        ),
        "duration_reason": (
            "5,166667 s concentram uma descida, um impacto e uma reacao sem preenchimento."
        ),
        "distinct_story_events": 3,
        "performance_only": False,
        "beats": [
            {
                "start": 0.0,
                "end": 1.55,
                "action": "Downstroke, corrida, detritos e camera continuam imediatamente.",
            },
            {
                "start": 1.55,
                "end": 3.62,
                "action": "Um impacto mecanico gera fragmentos, onda e fissura em propagacao.",
            },
            {
                "start": 3.62,
                "end": 5.166667,
                "action": "Gohan planta e a primeira descarga cresce sem pose final.",
            },
        ],
        "direction_status": "approved_for_video",
    }
    qc = take.setdefault("qc", {})
    qc["status"] = "video_authorized_pending_serial_generation"
    qc["human_visual_approval"] = "pending_video_review"
    qc["anchor_human_approval"] = {
        "status": "approved",
        "reviewed_at": str(sidecar.get("reviewed_at") or ""),
        "reason": str(human.get("reason") or ""),
        "image_sha256": sha256(image),
    }
    motion_gate = qc.setdefault("transition_motion_gate", {})
    motion_gate.update({
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
        "evidence": "contract is ready; generated MP4 still required",
    })

    queue["status"] = "V5_ACTION_FIRST_PILOT_P01_READY"
    queue["render_authorized"] = True
    queue["render_authority"] = (
        "Owner explicitly approved the P01 anchor and ordered video generation on 2026-08-20."
    )
    queue["continuous_action_contract"] = CONTINUOUS_POLICY
    queue["universal_transition_motion_gate"] = {"required": True}
    queue["story_batch_policy"] = {
        "enabled": True,
        "version": "gohan_v5_action_first_pilot_v1",
        "batch_size": 1,
        "render_order": [PILOT_ID],
        "strict_contiguous": True,
        "require_all_base_images_ready": True,
        "fill_eligible_across_batches": False,
        "require_full_batch": True,
        "allow_incomplete_correction_batch": False,
        "control_surface": "P01_QC_before_any_other_take",
    }

    manifest["status"] = "V5_ACTION_FIRST_PILOT_IN_PRODUCTION"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["render_authorized"] = True
    manifest["render_authority"] = queue["render_authority"]
    anchor_batches = manifest.setdefault("anchor_candidate_batches", {})
    if isinstance(anchor_batches, dict):
        record = anchor_batches.setdefault("v5_action_first_pilot", {})
        if isinstance(record, dict):
            record.update({
                "status": "APPROVED_BY_OWNER_FOR_VIDEO",
                "take_id": PILOT_ID,
                "sha256": sha256(image).upper(),
                "video_generation_authorized": True,
            })
    manifest["directed_correction_v5_action_first"] = {
        "reason": "The static 01A/01B route failed; begin inside irreversible action.",
        "method": "single 5.166667-second start-only MiniMax H3 pilot from the approved action anchor",
        "pilot_take_ids": [PILOT_ID],
        "generate_serially": True,
        "other_takes_blocked_until_p01_qc": True,
        "rife_before_picture_lock": False,
        "retime_before_picture_lock": False,
        "foley_status": "BLOCKED_UNTIL_NEW_PICTURE_LOCK",
    }

    pilot_manifest = {
        "schema_version": "gohan_ssj2_v5_action_first_pilot",
        "project_id": manifest.get("project_id") or PROJECT.name,
        "title": "Gohan SSJ2 — V5 — P01 action-first pilot",
        "objective": (
            "Prove one uninterrupted downstroke, mechanical impact and Gohan reaction "
            "with physical camera translation and no static tail."
        ),
        "sequence_stakes": (
            "Android 16's intact mechanical head is destroyed and Gohan's contained "
            "anger becomes the first visible electrical rupture."
        ),
        "universal_transition_motion_gate": {"required": True},
        "continuous_action_contract": CONTINUOUS_POLICY,
        "generation": {
            "profile": "minimax_h3_fl2va_int8_720p24",
            "fps": 24,
            "frames": 124,
        },
        "takes": [take],
        "gpu_policy": {"serial_only": True, "max_concurrent_video_jobs": 1},
        "audio": {"status": "BLOCKED_UNTIL_PICTURE_LOCK"},
    }
    atomic_json(QUEUE_PATH, queue)
    atomic_json(PROJECT_MANIFEST_PATH, manifest)
    atomic_json(PILOT_MANIFEST_PATH, pilot_manifest)
    print(json.dumps({
        "ok": True,
        "takeId": PILOT_ID,
        "pilotManifest": str(PILOT_MANIFEST_PATH),
        "anchorSha256": sha256(image).upper(),
        "renderAuthorized": True,
        "serialOnly": True,
        "fps": generation["fps"],
        "frames": generation["frames"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
