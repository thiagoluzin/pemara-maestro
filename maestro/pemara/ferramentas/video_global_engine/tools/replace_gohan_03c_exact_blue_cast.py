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
QC_PATH = PROJECT / "qc" / "take_03C_v1_director_rejection.json"
TZ = ZoneInfo("America/Sao_Paulo")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    now = datetime.now(TZ).isoformat()
    queue = read(QUEUE_PATH)
    production = read(PRODUCTION_PATH)
    project = read(PROJECT_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == "03C")
    video = copy.deepcopy(take.get("video") or {})
    rejected_path = str(
        video.get("output_active")
        or video.get("output_preview")
        or video.get("output_review_candidate")
        or ""
    )
    if not rejected_path or not Path(rejected_path).is_file():
        raise RuntimeError("O candidato 03C v1 nao esta preservado localmente.")

    rejected = {
        "path": rejected_path,
        "status": "DIRECTOR_REJECTED_CAST_IDENTITY",
        "reason": (
            "A full-size green adult Cell appears between owner-approved J2 and J3. "
            "The shot contract permits only Gohan and exactly two compact cyan-blue Juniors."
        ),
        "preserved": True,
        "owner_reviewed": False,
        "rejected_at": now,
        "job_id": str(take.get("maestro_last_job_id") or ""),
    }
    history = list(video.get("output_history") or [])
    history.append({
        "path": rejected_path,
        "role": "director_rejected_cast_identity_candidate",
        "replaced_at": now,
        "replaced_by_job_id": "overnight-03C-v2-exact-blue-cast",
    })
    rejected_candidates = list(video.get("rejected_candidates") or [])
    rejected_candidates.append(rejected)

    take["animation_prompt"] = (
        "One uninterrupted photorealistic live-action 5.125-second transfer between the exact approved J2 and J3 frames. "
        "The cast is locked to exactly three bodies for the entire shot: one purple-clad golden-haired SSJ2 Gohan and the same two small child-sized cyan-blue winged bio-android opponents visible in both approved frames. "
        "Both small blue opponents retain identical compact height, cyan-blue spotted skin, black chest armor, small black head crest, white face and short limbs from first frame to last frame; neither changes size, color, silhouette, age or identity. "
        "The already-hit blue opponent exits laterally through dust while Gohan continues the same body rotation and intercepts the other still-small blue opponent with one fast contact. "
        "A low camera crosses behind one foreground rock, changes height and exposes new background ruins; clothing, hair, aura, dust and both blue bodies remain in independent motion. "
        "Maintain exactly those three bodies, live-action skin and practical armor throughout. No fourth character, no adult antagonist, no character transformation, no body enlargement, no color change, no duplicated fighter, no tail, no anime, no cel shading, no game render, no plastic CGI, no pause, no freeze and no internal cut."
    )
    take["motion_beats"] = {
        "early_0_30": "Exactly three bodies remain visible as the already-hit small blue opponent exits laterally and Gohan keeps rotating.",
        "middle_30_70": "Gohan crosses real ground toward the other unchanged child-sized blue opponent while the camera changes height behind foreground debris.",
        "late_70_100": "The second small blue opponent receives one fast contact and all three locked identities continue moving into J3.",
    }
    take["shot_contract"]["motion_beats"] = copy.deepcopy(take["motion_beats"])
    continuity = take["shot_contract"]["transition_motion_contract"]["continuity"]
    continuity["entry_motion"] = take["motion_beats"]["early_0_30"]
    continuity["exit_motion"] = take["motion_beats"]["late_70_100"]
    continuity["interval_motion"] = copy.deepcopy(take["motion_beats"])
    progression = take["shot_contract"]["transition_motion_contract"]["progression"]
    progression["middle"] = take["motion_beats"]["middle_30_70"]

    take["video"] = {
        "status": "pending_generation",
        "output_active": "",
        "output_preview": "",
        "output_review_candidate": "",
        "output_history": history,
        "rejected_candidates": rejected_candidates,
    }
    take["status"] = "READY_FOR_VIDEO_GENERATION"
    take["maestro_status"] = "READY"
    take["maestro_last_job_id"] = ""
    take["maestro_last_error"] = ""
    take["render_authorized"] = True
    take["video_generation"]["render_authorized"] = True
    take["release_gates"]["art_direction"] = "FAIL_V1_CAST_IDENTITY"
    take["release_gates"]["cinematic"] = "PENDING"
    take["release_gates"]["motion"] = "PENDING"
    take["release_gates"]["technical"] = "PENDING"

    queue["updated_at"] = now
    overnight = queue.setdefault("overnight_generation", {})
    overnight["take03C_v1_rejected"] = rejected
    overnight["take03C_replacement_version"] = 2
    production["updated_at"] = now
    production["overnight_generation"] = copy.deepcopy(overnight)
    project["updated_at"] = now
    project["overnight_generation"] = copy.deepcopy(overnight)
    write(QC_PATH, rejected)
    write(QUEUE_PATH, queue)
    write(PRODUCTION_PATH, production)
    write(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "take_id": "03C",
        "rejected_candidate": rejected_path,
        "replacement_version": 2,
        "preserved": True,
        "auto_approved": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
