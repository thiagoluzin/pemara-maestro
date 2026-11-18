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
QC_PATH = PROJECT / "qc" / "take_04_direct_v1_director_rejection.json"
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

    queue["takes"] = [take for take in queue["takes"] if str(take.get("id")) != "04A"]
    main_take = next(take for take in queue["takes"] if str(take.get("id")) == "04")
    original_video = copy.deepcopy(main_take.get("video") or {})
    rejected_path = str(
        original_video.get("output_active")
        or original_video.get("output_preview")
        or original_video.get("output_review_candidate")
        or ""
    )
    if not rejected_path or not Path(rejected_path).is_file():
        raise RuntimeError("O candidato direto do Take 04 nao esta preservado localmente.")

    rejected = {
        "path": rejected_path,
        "status": "DIRECTOR_REJECTED_MOTION_CONTRACT",
        "reason": (
            "The long pass turns the requested one-beat lateral slap into a prolonged palm block, "
            "then holds the final impact for several seconds. Art direction is photographic and Cell "
            "remains tailless, but the required deflection vector and full-duration progression fail."
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
        "replaced_by_job_id": "overnight-04A-short-deflection",
    })
    rejected_candidates = list(original_video.get("rejected_candidates") or [])
    rejected_candidates.append(rejected)
    main_take["video"] = {
        "status": "pending_internal_microsegment",
        "output_active": "",
        "output_preview": "",
        "output_review_candidate": "",
        "output_history": history,
        "rejected_candidates": rejected_candidates,
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
        "04A",
        "INTERNAL 04A — tapa lateral e avanço E-F",
        clean_anchor(anchors["E"]),
        clean_anchor(anchors["F"]),
        "E",
        "F",
        (
            "One uninterrupted photorealistic live-action 5.125-second action shot between the exact approved frames. "
            "Completely tailless Perfect Cell instantly fires one compact blue-white energy sphere at SSJ2 Gohan. "
            "Gohan performs one sharp open-hand lateral slap across the sphere, visibly redirecting it at a steep side angle past his body and into distant rubble; the energy never touches or crosses his torso. "
            "There is no guard, no beam struggle and no prolonged palm block: hand contact lasts a single beat and the sphere immediately changes direction. "
            "Gohan uses the same momentum to dash through the opening and deliver one heavy rising strike that sends Cell upward into the approved end frame. "
            "The side-tracking camera crosses foreground debris and accelerates into a close orbit while dust, cloth, hair, aura and displaced energy remain in continuous motion. "
            "No animation, anime, cel shading, game render, plastic CGI, tail, energy through Gohan, straight beam, sustained block, duplicated limbs, fused anatomy, slow motion, pause, static ending or internal cut."
        ),
        "Cell releases one compact sphere immediately while Gohan rotates his open hand into the lateral intercept and the camera trucks sideways.",
        "One brief slap changes the sphere's trajectory away from Gohan; redirected energy crosses depth and explodes in distant rubble as Gohan dashes forward.",
        "Gohan converts the dash into one rising heavy contact that sends tailless Cell upward, with camera, debris and bodies still accelerating into boundary F.",
    )
    queue["takes"].append(micro)
    queue["updated_at"] = now
    overnight = queue.setdefault("overnight_generation", {})
    overnight["take04_direct_v1_rejected"] = rejected
    overnight["take04_replacement"] = "04A"
    internal = list(overnight.get("internal_microsegments") or [])
    if "04A" not in internal:
        internal.append("04A")
    overnight["internal_microsegments"] = internal

    production["takes"] = copy.deepcopy(
        [take for take in queue["takes"] if not take.get("internal_microsegment")]
    )
    production["updated_at"] = now
    production["overnight_generation"] = copy.deepcopy(overnight)
    project["updated_at"] = now
    project["overnight_generation"] = copy.deepcopy(overnight)
    QC_PATH.parent.mkdir(parents=True, exist_ok=True)
    write(QC_PATH, rejected)
    write(QUEUE_PATH, queue)
    write(PRODUCTION_PATH, production)
    write(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "rejected_candidate": rejected_path,
        "preserved": True,
        "replacement_take_id": "04A",
        "owner_reviewed": False,
        "auto_approved": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
