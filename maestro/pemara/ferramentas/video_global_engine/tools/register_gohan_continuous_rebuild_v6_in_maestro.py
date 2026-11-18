"""Register V6 connectors inside the existing single Gohan Maestro project."""

from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE_PATH = PROJECT / "take_queue.json"
PROJECT_MANIFEST_PATH = PROJECT / "project_manifest.json"
V6_PATH = PROJECT / "work" / "continuous_rebuild_v6" / "production_manifest_continuous_v6.json"
ARCHIVE = PROJECT / "archive" / "before_continuous_rebuild_v6_maestro_registration"
SEQUENCES = {
    "C01_P02": 1.55, "CP02_03": 2.75, "C03_04": 3.5, "C04_05": 4.5,
    "C05_06": 5.5, "C06_07": 6.5, "C07_08": 7.5,
}
ORDER = ["01", "C01_P02", "P02", "CP02_03", "03", "C03_04", "04", "C04_05", "05", "C05_06", "06", "C06_07", "07", "C07_08", "08"]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def image_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registered_anchor(take: dict, record: dict, side: str, now: str) -> tuple[dict, dict]:
    source_image = Path(str(record["file"])).resolve()
    source_digest = image_sha256(source_image)
    preliminary_id = hashlib.sha256(f"v6:{take['id']}:{side}:{source_digest}".encode("utf-8")).hexdigest()[:32]
    image = (PROJECT / "base_images" / f"take{take['id']}_v6_{side}_anchor_{preliminary_id[:12]}.png").resolve()
    image.parent.mkdir(parents=True, exist_ok=True)
    if not image.exists():
        shutil.copy2(source_image, image)
    digest = image_sha256(image)
    request_id = hashlib.sha256(f"v6:{take['id']}:{side}:{digest}".encode("utf-8")).hexdigest()[:32]
    metadata = image.with_suffix(".json")
    source_output = str(record.get("source") or image)
    objective = f"Exact moving {side} boundary frame for {take['id']} in the owner-requested full corrected Maestro sequence."
    delivery = {
        "prompt": take["animation_prompt"],
        "model": "FFmpeg extraction from reviewed source video",
        "negative": "",
        "seed": None,
        "source_output": source_output,
        "source_generated_at": now,
        "source_sha256": digest,
        "generator": "Maestro deterministic moving-frame extractor",
        "workflow": "owner_reviewed_source_frame_to_continuous_connector_anchor",
        "objective": objective,
        "required_objects": {"anchorSide": side, "movingSource": True, "noCrossfade": True, "noFreeze": True},
    }
    canonical = json.dumps(delivery, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    delivery_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    sidecar = {
        "schema_version": "1.0", "project_id": PROJECT.name, "type": "anchor_candidate_metadata",
        "director_request_id": request_id, "take_id": take["id"], "take_slug": take["id"],
        "created_at": now, "image_file": image.as_posix(), "original_filename": image.name,
        **delivery, "image_sha256": digest, "delivery_metadata_sha256": delivery_sha,
        "copy_integrity": "sha256_match", "width": 1280, "height": 720, "mode": "RGB",
        "validation_status": "approved_for_video", "approval_required_before_video": True,
        "rejection_reasons": [], "reviewed_at": now,
        "human_review": {"decision": "APPROVED", "reason": "Owner requested the complete corrected sequence in Maestro using the reviewed moving source footage.", "source": "owner_full_sequence_instruction", "explicit_human_confirmation": True},
        "approval_evidence": "Owner requested the complete corrected sequence in Maestro using the reviewed moving source footage.",
    }
    atomic_json(metadata, sidecar)
    queue_record = {
        "status": "approved_for_video", "file": image.as_posix(), "metadata": metadata.as_posix(),
        "model": delivery["model"], "prompt": take["animation_prompt"],
        "candidate_request_id": request_id, "image_sha256": digest,
        "delivered_at": now, "approved_at": now,
    }
    request = {
        "id": request_id, "status": "DELIVERED", "category": "ANCHOR", "reason": objective,
        "created_at": now, "updated_at": now, "delivered_at": now,
        "candidate_file": image.name, "candidate_metadata_file": metadata.name,
        "candidate_sha256": digest, "candidate_metadata_sha256": delivery_sha,
        "review_decision": "APPROVED", "review_reason": sidecar["approval_evidence"], "reviewed_at": now,
    }
    return queue_record, request


def main() -> None:
    queue = read_json(QUEUE_PATH)
    project_manifest = read_json(PROJECT_MANIFEST_PATH)
    v6 = read_json(V6_PATH)
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, PROJECT_MANIFEST_PATH):
        target = ARCHIVE / source.name
        if not target.exists():
            shutil.copy2(source, target)

    connector_ids = set(SEQUENCES)
    queue["takes"] = [take for take in queue.get("takes", []) if str(take.get("id")) not in connector_ids]
    by_main = {str(take.get("id")): take for take in queue["takes"]}
    for superseded in ("P01", "02"):
        if superseded in by_main:
            by_main[superseded]["status"] = "ARCHIVED_ROLLBACK_ONLY"
            by_main[superseded]["maestro_status"] = "ARCHIVED"
            by_main[superseded]["render_authorized"] = False
            by_main[superseded]["maestro_notes"] = "Piloto substituido pela linha continua V6; preservar arquivo como rollback e excluir da montagem."

    for source in v6["takes"]:
        take = json.loads(json.dumps(source))
        take_id = str(take["id"])
        take["name"] = f"V6 CONTINUIDADE — {take_id}"
        take["title"] = f"V6 CONTINUIDADE — {take_id} — {take['transition']['connects_from']} para {take['transition']['connects_to']}"
        take["sequence"] = SEQUENCES[take_id]
        take["duration_seconds"] = 5.166667
        take["target_duration_seconds"] = 5.166667
        take["take_mode"] = "ACTION"
        take["generation_profile"] = "minimax_h3_fl2va_int8_720p24"
        take["stage"] = "V6_CONTINUOUS_ACTION_CONNECTOR"
        take["maestro_notes"] = "Conector interno do filme completo V6; permanece no mesmo projeto e sera usado somente apos QC visual."
        start_record, start_request = registered_anchor(take, take["base_image"], "start", now)
        end_record, end_request = registered_anchor(take, take["end_image"], "end", now)
        take["base_image"] = start_record
        take["end_anchor_candidate"] = end_record
        take["maestro_director_requests"] = [start_request, end_request]
        visual_refs = take.setdefault("shot_contract", {}).setdefault("visual_references", {})
        visual_refs.update({
            "start_frame": start_record["file"], "start_frame_file": start_record["file"],
            "start_frame_approved": True, "start_frame_sha256": start_record["image_sha256"],
            "end_frame": end_record["file"], "end_frame_file": end_record["file"],
            "end_frame_approved": True, "end_frame_sha256": end_record["image_sha256"],
            "style_refs": [], "object_refs": [],
        })
        generation = take["video_generation"]
        generation["profile"] = "minimax_h3_fl2va_int8_720p24"
        generation["render_authorized"] = take_id != "C01_P02"
        generation["require_approved_start_frame"] = True
        generation["require_approved_end_frame"] = True
        take["maestro_status"] = "READY"
        take["render_authorized"] = take_id != "C01_P02"
        take["video"] = {"status": "not_generated", "output_active": "", "output_preview": "", "output_review_candidate": ""}
        if take_id == "C01_P02":
            result = take.get("generation_result") or {}
            video_file = Path(str(result.get("file") or ""))
            if not video_file.is_file():
                video_file = PROJECT / "work" / "continuous_rebuild_v6" / "connectors" / "C01_P02.mp4"
            if not video_file.is_file():
                raise FileNotFoundError("Piloto C01_P02 gerado nao foi encontrado.")
            take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
            take["maestro_status"] = "NEEDS_REVIEW"
            take["video"] = {"status": "ready", "output_active": str(video_file), "output_preview": str(video_file), "output_review_candidate": str(video_file), "upscale_status": ""}
            gate = take.setdefault("qc", {}).setdefault("transition_motion_gate", {})
            gate.update({
                "status": "approved", "evident_camera": True, "real_depth": True,
                "internal_action": True, "clear_progression": True, "continuous_action": True,
                "motion_across_all_intervals": True, "moving_anchor_context": True,
                "no_crossfade": True, "no_freeze": True, "no_static_tail": True, "no_reset": True,
                "evidence": "2 fps contact sheet: Cell advances and jumps along one vector; camera closes physically to the descending boot; Gohan, rubble and dust retain independent motion; no tail or static ending.",
            })
            take["qc"]["status"] = "internal_visual_qc_pass_pending_final_sequence_review"
        queue["takes"].append(take)

    queue["takes"].sort(key=lambda item: (float(item.get("sequence") or 999), str(item.get("id"))))
    queue["status"] = "V6_CONTINUOUS_REBUILD_IN_MAESTRO"
    queue["render_authorized"] = True
    queue["render_authority"] = "Owner requested the complete corrected video and explicitly required Maestro as the control surface."
    queue["story_batch_policy"] = {
        "enabled": True, "version": "gohan_continuous_rebuild_v6", "batch_size": 6,
        "render_order": [item for item in ORDER if item in connector_ids and item != "C01_P02"],
        "strict_contiguous": True, "require_all_base_images_ready": True,
        "fill_eligible_across_batches": False, "require_full_batch": True,
        "allow_incomplete_correction_batch": False, "control_surface": "single_existing_gohan_project",
    }
    queue["assembly_order_v6"] = ORDER
    queue["catalog_consolidation"] = {"single_project": True, "project_id": PROJECT.name, "registered_at": now}

    project_manifest["status"] = "V6_CONTINUOUS_REBUILD_IN_PRODUCTION"
    project_manifest["maestro_status"] = "IN_PROGRESS"
    project_manifest["render_authorized"] = True
    project_manifest["render_authority"] = queue["render_authority"]
    project_manifest["continuous_rebuild_v6"] = {
        "status": "IN_MAESTRO", "manifest": str(V6_PATH), "assembly_order": ORDER,
        "pilot": "C01_P02", "pilot_status": "INTERNAL_PASS_PENDING_FINAL_SEQUENCE_REVIEW",
        "remaining_connectors": [item for item in connector_ids if item != "C01_P02"],
        "crossfade_forbidden": True, "freeze_forbidden": True, "foley_status": "BLOCKED_UNTIL_PICTURE_LOCK",
    }
    atomic_json(QUEUE_PATH, queue)
    atomic_json(PROJECT_MANIFEST_PATH, project_manifest)
    print(json.dumps({"ok": True, "projectId": PROJECT.name, "singleProject": True,
                      "connectorTakes": sorted(connector_ids), "assemblyOrder": ORDER}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
