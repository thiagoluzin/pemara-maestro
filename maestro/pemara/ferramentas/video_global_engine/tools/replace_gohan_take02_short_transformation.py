from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import prepare_gohan_overnight_vejito_batch as base


PROJECT = base.PROJECT
QUEUE_PATH = PROJECT / "take_queue.json"
PRODUCTION_PATH = PROJECT / "production_manifest.json"
PROJECT_PATH = PROJECT / "project_manifest.json"
REGISTRY_PATH = PROJECT / "qc" / "approved_anchor_registry.json"
QC_PATH = PROJECT / "qc" / "take_02_direct_v1_director_rejection.json"
TZ = ZoneInfo("America/Sao_Paulo")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_anchor(raw: dict) -> dict:
    return {
        "file": raw["file"],
        "metadata": raw["metadata"],
        "sha256": raw["sha256"],
        "status": "approved_for_video",
    }


def main() -> None:
    now = datetime.now(TZ).isoformat()
    queue = read(QUEUE_PATH)
    production = read(PRODUCTION_PATH)
    project = read(PROJECT_PATH)
    anchors = read(REGISTRY_PATH)["anchors"]
    queue["takes"] = [take for take in queue["takes"] if str(take.get("id")) != "02A"]
    main_take = next(take for take in queue["takes"] if str(take.get("id")) == "02")
    original_video = copy.deepcopy(main_take.get("video") or {})
    rejected_path = str(
        original_video.get("output_active")
        or original_video.get("output_preview")
        or original_video.get("output_review_candidate")
        or ""
    )
    if not rejected_path or not Path(rejected_path).is_file():
        raise RuntimeError("O candidato direto do Take 02 nao esta preservado localmente.")
    rejected = {
        "path": rejected_path,
        "status": "DIRECTOR_REJECTED_MOTION_CONTRACT",
        "reason": (
            "The 10-second pass repeats the transformation aura and never performs the promised launch. "
            "Art direction remains photographic, but full-duration progression and action contract fail."
        ),
        "preserved": True,
        "owner_reviewed": False,
        "rejected_at": now,
        "job_id": str(main_take.get("maestro_last_job_id") or ""),
    }
    history = list(original_video.get("output_history") or [])
    history.append({
        "path": rejected_path,
        "role": "director_rejected_motion_candidate",
        "replaced_at": now,
        "replaced_by_job_id": "overnight-02A-short-transformation",
    })
    main_take["video"] = {
        "status": "pending_internal_microsegment",
        "output_active": "",
        "output_preview": "",
        "output_review_candidate": "",
        "output_history": history,
        "rejected_candidates": [rejected],
    }
    main_take["status"] = "INTERNAL_SEGMENT_PENDING"
    main_take["maestro_status"] = "READY"
    main_take["maestro_last_job_id"] = ""
    main_take["maestro_last_error"] = ""
    main_take["render_authorized"] = False
    main_take["video_generation"]["render_authorized"] = False
    main_take.setdefault("release_gates", {})["motion"] = "FAIL_DIRECT_V1"
    main_take["release_gates"]["human"] = "PENDING"

    micro = base.micro_take(
        main_take,
        "02A",
        "INTERNAL 02A — transformação SSJ2 curta C-D",
        clean_anchor(anchors["C"]),
        clean_anchor(anchors["D"]),
        "C", "D",
        (
            "One uninterrupted photorealistic live-action 5.125-second transformation shot between the exact approved frames. "
            "Gohan's shock becomes an irreversible Super Saiyan 2 transformation in one accelerating progression: grounded rage, explosive golden energy, blue-white lightning and a final forward weight shift ready to launch. "
            "Completely tailless Perfect Cell recoils and braces while foreground rubble, clothing, hair, aura and a short physical crane-orbit all keep moving. "
            "Do not repeat the same aura tableau; every second must change body geometry, debris height, camera perspective and Cell's reaction. "
            "No animation, anime, cel shading, game render, plastic CGI, tail, Cell clone, long power-up loop, victory pose, freeze, static ending or internal cut."
        ),
        "Gohan absorbs the mechanical destruction and his body, cloth, dust and camera begin accelerating immediately.",
        "Golden energy erupts once, hair completes SSJ2 and blue-white lightning changes the terrain while Cell physically recoils.",
        "Gohan finishes with a forward weight shift and rising debris that hands active motion to the D-J1 launch segment.",
    )
    queue["takes"].append(micro)
    queue["updated_at"] = now
    queue["overnight_generation"]["take02_direct_v1_rejected"] = rejected
    queue["overnight_generation"]["take02_replacement"] = "02A"
    production["takes"] = copy.deepcopy(
        [take for take in queue["takes"] if not take.get("internal_microsegment")]
    )
    production["updated_at"] = now
    production["overnight_generation"] = copy.deepcopy(queue["overnight_generation"])
    project["updated_at"] = now
    project["overnight_generation"] = copy.deepcopy(queue["overnight_generation"])
    QC_PATH.parent.mkdir(parents=True, exist_ok=True)
    write(QC_PATH, rejected)
    write(QUEUE_PATH, queue)
    write(PRODUCTION_PATH, production)
    write(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "rejected_candidate": rejected_path,
        "preserved": True,
        "replacement_take_id": "02A",
        "owner_reviewed": False,
        "auto_approved": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
