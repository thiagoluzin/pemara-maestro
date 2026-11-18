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
QC_PATH = PROJECT / "qc" / "take_03D_v1_director_rejection.json"
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
    take = next(item for item in queue["takes"] if str(item.get("id")) == "03D")
    video = copy.deepcopy(take.get("video") or {})
    rejected_path = str(
        video.get("output_active")
        or video.get("output_preview")
        or video.get("output_review_candidate")
        or ""
    )
    if not rejected_path or not Path(rejected_path).is_file():
        raise RuntimeError("O candidato 03D v1 nao esta preservado localmente.")

    rejected = {
        "path": rejected_path,
        "status": "DIRECTOR_REJECTED_IDENTITY_AND_GORE_RISK",
        "reason": (
            "The compact blue Junior becomes a dark red silhouette during the exit, breaking "
            "character identity and creating an unintended blood-like visual."
        ),
        "preserved": True,
        "owner_reviewed": False,
        "rejected_at": now,
        "job_id": str(take.get("maestro_last_job_id") or ""),
    }
    history = list(video.get("output_history") or [])
    history.append({
        "path": rejected_path,
        "role": "director_rejected_identity_candidate",
        "replaced_at": now,
        "replaced_by_job_id": "overnight-03D-v2-blue-exit",
    })
    rejected_candidates = list(video.get("rejected_candidates") or [])
    rejected_candidates.append(rejected)

    take["animation_prompt"] = (
        "One uninterrupted photorealistic live-action 5.125-second second-impact shot between the exact approved J3 and J4 frames. "
        "The cast is locked to exactly two bodies: one purple-clad golden-haired SSJ2 Gohan and the same single compact child-sized cyan-blue winged bio-android opponent shown in J3. "
        "The small opponent retains cyan-blue spotted skin, black chest armor, small black head crest, white face, compact height and short limbs until it leaves the frame; it never changes color, size, silhouette or identity. "
        "Gohan completes one decisive knee-and-forearm follow-through, sending the still-blue opponent rapidly sideways and upward; it exits intact behind blue-white impact particles with no bodily damage shown. "
        "Gohan uses the same momentum to pivot alone through the blue particle trail into the exact J4 pose. The camera swings physically around him while rocks, dust, cloth, aura and blue particles move on separate depth planes. "
        "Maintain exactly those two bodies until the small blue opponent exits, then only Gohan remains. No third character, no adult antagonist, no transformation, no red color, no blood, no gore, no dark silhouette, no tail, no anime, no cel shading, no game render, no plastic CGI, no duplicated limb, no pause, no freeze and no internal cut."
    )
    take["motion_beats"] = {
        "early_0_30": "Exactly two locked bodies continue the J3 contact as the unchanged compact blue opponent accelerates sideways.",
        "middle_30_70": "The intact still-blue opponent exits upward behind blue-white particles while the camera swings through real depth with Gohan.",
        "late_70_100": "Only Gohan remains, completing the same moving pivot through the blue trail into J4 without posing or stopping.",
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
    take["release_gates"]["art_direction"] = "FAIL_V1_IDENTITY"
    take["release_gates"]["cinematic"] = "PENDING"
    take["release_gates"]["motion"] = "PENDING"
    take["release_gates"]["technical"] = "PENDING"

    queue["updated_at"] = now
    overnight = queue.setdefault("overnight_generation", {})
    overnight["take03D_v1_rejected"] = rejected
    overnight["take03D_replacement_version"] = 2
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
        "take_id": "03D",
        "rejected_candidate": rejected_path,
        "replacement_version": 2,
        "preserved": True,
        "auto_approved": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
