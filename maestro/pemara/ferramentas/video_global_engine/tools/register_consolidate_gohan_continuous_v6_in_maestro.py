from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE = PROJECT / "take_queue.json"
MANIFEST = PROJECT / "project_manifest.json"
TECHNICAL = PROJECT / "edit" / "gohan_ssj2_cell_filme_continuo_v6_720p60.json"
VIDEO = PROJECT / "deliveries" / "gohan_ssj2_cell_filme_continuo_v6_720p60.mp4"
FULL_BOUNDARIES = PROJECT / "qc" / "gohan_ssj2_cell_filme_continuo_v6_720p60_boundaries_full_65.jpg"
EXPECTED_SHA256 = "004a6aa27dae5401e4fba3b834a3c9120b6745b6f3b8f5518b3cfc60fef0a6f8"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(PROJECT).as_posix()


def main() -> None:
    for path in (QUEUE, MANIFEST, TECHNICAL, VIDEO, FULL_BOUNDARIES):
        if not path.is_file():
            raise SystemExit(f"arquivo obrigatório ausente: {path}")

    video_sha = sha256(VIDEO)
    if video_sha != EXPECTED_SHA256:
        raise SystemExit(f"SHA256 inesperado: {video_sha}")

    queue = read_json(QUEUE)
    manifest = read_json(MANIFEST)
    technical = read_json(TECHNICAL)
    if technical.get("status") != "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK":
        raise SystemExit("manifesto técnico não está liberado para playback do proprietário")
    if technical.get("outputSha256") != video_sha:
        raise SystemExit("SHA256 diverge do manifesto técnico")

    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    archive = PROJECT / "archive" / f"before_maestro_single_film_v6_{stamp}"
    archive.mkdir(parents=True, exist_ok=False)
    shutil.copy2(QUEUE, archive / "take_queue.json")
    shutil.copy2(MANIFEST, archive / "project_manifest.json")
    atomic_json(
        archive / "archive_inventory.json",
        {
            "archived_at": datetime.now().astimezone().isoformat(),
            "reason": "Consolidar o catálogo visível do Maestro em um único filme contínuo V6.",
            "original_take_count": len(queue.get("takes", [])),
            "original_take_ids": [take.get("id") for take in queue.get("takes", [])],
            "media_deleted": False,
            "source_and_rejected_media_preserved_in_place": True,
        },
    )

    now = datetime.now().astimezone().isoformat()
    technical["boundarySheet"] = str(FULL_BOUNDARIES)
    technical["maestroRegistration"] = {
        "registered_at": now,
        "visible_take_id": "FILME_V6",
        "human_review": "PENDING",
    }
    atomic_json(TECHNICAL, technical)

    final_take = {
        "id": "FILME_V6",
        "slug": "GOHAN_SSJ2_FILME_CONTINUO_V6_60FPS",
        "title": "GOHAN SSJ2 — FILME CONTÍNUO V6 — 60 FPS",
        "sequence": 1,
        "role": "complete_continuous_film_owner_review",
        "stage": "FINAL_CONTINUOUS_FILM_REVIEW",
        "status": "VIDEO_PENDING_HUMAN_REVIEW",
        "maestro_status": "NEEDS_REVIEW",
        "render_authorized": False,
        "target_duration_seconds": 60.2,
        "native_duration_seconds": 60.2,
        "duration_seconds": 60.2,
        "objective": "Revisar o filme contínuo completo antes da criação do Foley.",
        "maestro_notes": "Único item visível. QC técnico aprovado; aprovação visual do proprietário ainda pendente. Sem áudio por enquanto.",
        "video": {
            "status": "ready",
            "output_active": str(VIDEO),
            "output_preview": str(VIDEO),
            "output_review_candidate": str(VIDEO),
            "candidate_status": "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK",
            "upscale_status": "",
        },
        "qc": {
            "status": "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK",
            "human_visual_approval": "pending",
            "full_decode": "pass",
            "freeze_events_at_least_0_4_seconds": 0,
            "boundary_sheet": rel(FULL_BOUNDARIES),
            "technical_manifest": rel(TECHNICAL),
        },
        "audio_direction": {
            "status": "BLOCKED_UNTIL_OWNER_PICTURE_APPROVAL",
            "audio_present": False,
            "next_stage": "Foley após aprovação visual",
        },
    }

    archive_rel = rel(archive)
    queue["status"] = "V6_SINGLE_FILM_PENDING_OWNER_REVIEW"
    queue["maestro_status"] = "NEEDS_REVIEW"
    queue["render_authorized"] = False
    queue["updated_at"] = now
    queue["takes"] = [final_take]
    queue["assembly_order_v6"] = ["FILME_V6"]
    queue["story_batch_policy"] = {"enabled": False, "reason": "filme completo já montado"}
    queue["catalog_consolidation"] = {
        "status": "SINGLE_VISIBLE_FILM",
        "active_take_ids": ["FILME_V6"],
        "archived_catalog": f"{archive_rel}/take_queue.json",
        "archived_take_count": len(read_json(archive / "take_queue.json").get("takes", [])),
        "media_deleted": False,
        "negative_candidates_visible": False,
        "consolidated_at": now,
    }

    previous_final = manifest.get("final_output")
    if previous_final:
        atomic_json(archive / "previous_final_output.json", previous_final)
    final_output = {
        "file": rel(VIDEO),
        "review_file": rel(VIDEO),
        "duration_seconds": 60.2,
        "width": 1280,
        "height": 720,
        "fps": 60,
        "frames": 3612,
        "video_codec": "h264_nvenc",
        "audio_codec": "none",
        "sha256": video_sha,
        "qc_status": "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK",
        "purpose": "filme contínuo completo para revisão do proprietário antes do Foley",
        "technical_manifest": rel(TECHNICAL),
        "boundary_sheet": rel(FULL_BOUNDARIES),
        "registered_at": now,
        "human_review": {"status": "PENDING", "decision": "PENDING", "required": True},
    }
    manifest["status"] = "V6_SINGLE_FILM_PENDING_OWNER_REVIEW"
    manifest["maestro_status"] = "NEEDS_REVIEW"
    manifest["render_authorized"] = False
    manifest["updated_at"] = now
    manifest["final_output"] = final_output
    manifest["final_output_history"] = []
    manifest["picture_lock_candidate"] = final_output
    manifest["catalog_consolidation"] = queue["catalog_consolidation"]
    manifest["take_queue"] = rel(QUEUE)

    audit = {
        "status": "PASS",
        "created_at": now,
        "visible_take_ids": ["FILME_V6"],
        "visible_take_count": 1,
        "video": str(VIDEO),
        "sha256": video_sha,
        "duration_seconds": 60.2,
        "fps": 60,
        "technical_status": technical["status"],
        "human_review": "PENDING",
        "archived_catalog": str(archive),
        "media_deleted": False,
    }

    atomic_json(QUEUE, queue)
    atomic_json(MANIFEST, manifest)
    atomic_json(PROJECT / "qc" / "maestro_single_film_v6.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
