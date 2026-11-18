from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
TAKE_IDS = ("01", "02", "03", "04", "05", "06")
QC_DIR = PROJECT / "qc" / "rife60_candidates"
TECHNICAL_REPORT = QC_DIR / "rife60_candidates_qc_report.json"
INTERNAL_REPORT = QC_DIR / "rife60_internal_boundaries_report.json"
CROSS_REPORT = QC_DIR / "rife60_cross_take_boundaries_report.json"
DIRECTOR_REPORT = QC_DIR / "director_visual_qc_report.json"

TAKE_NOTES = {
    "01": (
        "Photorealistic live-action materials remain coherent. Android 16 stays mechanical and non-green; "
        "Perfect Cell is tailless; the foot placement and crush progression remain readable without a static tail."
    ),
    "02": (
        "SSJ2 transformation energy, lightning and debris remain photographic. The Vejito cadence removes the "
        "slow repeated hold while preserving the approved C-to-D handoff."
    ),
    "03": (
        "The attack passage contains the intended two compact blue Cell Juniors. No replacement adult green Cell "
        "or red silhouette appears in the corrected Junior action chain."
    ),
    "04": (
        "Gohan redirects the incoming energy laterally into a visible curved path and immediately advances. "
        "Perfect Cell remains tailless and the shot does not settle into the rejected prolonged block."
    ),
    "05": (
        "Close combat keeps forward pressure, physical camera travel, changing depth and distinct impacts. "
        "Perfect Cell remains tailless and live-action through the pursuit handoff."
    ),
    "06": (
        "The chase, heavy impacts, launch and blue-white Kamehameha progress continuously into the mountain hit. "
        "No static aftermath, tail or animation-style regression was observed."
    ),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_save(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    technical = load(TECHNICAL_REPORT)
    if technical.get("status") not in {
        "TECHNICAL_PASS_VISUAL_QC_PENDING",
        "TECHNICAL_AND_DIRECTOR_PASS_PENDING_OWNER_REVIEW",
    }:
        raise RuntimeError("RIFE60 technical report is not ready for director review")
    reports = {str(item.get("take_id")): item for item in technical.get("takes", [])}
    if set(reports) != set(TAKE_IDS):
        raise RuntimeError("RIFE60 technical report does not contain exactly the six main takes")
    if any(item.get("technical_status") != "PASS" for item in reports.values()):
        raise RuntimeError("At least one RIFE60 take failed technical QC")
    if any(item.get("freeze_violations") for item in reports.values()):
        raise RuntimeError("At least one RIFE60 take contains a freeze violation")

    internal = load(INTERNAL_REPORT)
    cross = load(CROSS_REPORT)
    if len(internal.get("joins", [])) != 10 or len(cross.get("joins", [])) != 5:
        raise RuntimeError("Boundary reports are incomplete")

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    manifest_path = PROJECT / "project_manifest.json"
    overnight_path = PROJECT / "qc" / "overnight_job_manifest.json"
    backup = PROJECT / "qc" / "before_director_rife60_qc_registration" / timestamp_slug
    backup.mkdir(parents=True, exist_ok=False)
    for source in (
        queue_path,
        production_path,
        manifest_path,
        overnight_path,
        TECHNICAL_REPORT,
        INTERNAL_REPORT,
        CROSS_REPORT,
    ):
        if source.is_file():
            shutil.copy2(source, backup / source.name)

    technical["status"] = "TECHNICAL_AND_DIRECTOR_PASS_PENDING_OWNER_REVIEW"
    technical["director_reviewed_at"] = timestamp
    technical["human_approval"] = "PENDING_OWNER_PLAYBACK"
    for take_id, item in reports.items():
        item["art_direction_status"] = "DIRECTOR_PASS"
        item["cinematic_status"] = "DIRECTOR_PASS"
        item["motion_status"] = "DIRECTOR_PASS"
        item["human_status"] = "PENDING_OWNER_REVIEW"
        item["director_note"] = TAKE_NOTES[take_id]
    atomic_save(TECHNICAL_REPORT, technical)

    for boundary_report, label in (
        (internal, "ten internal microassembly joins"),
        (cross, "five main-take handoffs"),
    ):
        boundary_report["status"] = "DIRECTOR_PASS_PENDING_OWNER_REVIEW"
        boundary_report["director_reviewed_at"] = timestamp
        boundary_report["manual_review"] = (
            f"PASS: {label} preserve pose, direction, scale, scene geography and active motion at CFR60."
        )
    atomic_save(INTERNAL_REPORT, internal)
    atomic_save(CROSS_REPORT, cross)

    queue = load(queue_path)
    production = load(production_path)
    manifest = load(manifest_path)
    queue_by_id = {str(item.get("id")): item for item in queue.get("takes", [])}
    production_by_id = {str(item.get("id")): item for item in production.get("takes", [])}
    for take_id in TAKE_IDS:
        contact = reports[take_id]["contact_sheet"]
        for take in (queue_by_id[take_id], production_by_id[take_id]):
            release = take.setdefault("release_gates", {})
            release.update(
                {
                    "art_direction": "PASS",
                    "cinematic": "PASS",
                    "motion": "PASS",
                    "technical": "PASS",
                    "human": "PENDING",
                    "video_contact_sheet": contact,
                }
            )
            art = take.setdefault("art_direction_gate", {})
            art["video_style_status"] = "DIRECTOR_PASS_PENDING_OWNER_REVIEW"
            art["forbidden_style_detected"] = "NONE_OBSERVED_IN_DIRECTOR_QC"
            qc = take.setdefault("qc", {})
            qc["director_visual_review"] = "PASS_PENDING_OWNER_APPROVAL"
            qc["director_reviewed_at"] = timestamp
            qc["human_visual_approval"] = "pending_owner_playback"
            qc["auto_approved"] = False
            qc["status"] = "director_pass_60fps_pending_human_review"
            take["status"] = "READY_PENDING_OWNER_REVIEW"
            take["maestro_status"] = "READY"
            take["qc_status"] = "director_pass_60fps_pending_human_review"
            take["maestro_notes"] = (
                "VEJITO STANDARD 60 FPS: Practical-RIFE 4.25 at 1.25x. Technical and director QC passed; "
                "owner playback approval is still required. No Foley or final assembly has been authorized."
            )

    queue["status"] = "DIRECTOR_PASS_ALL_SIX_60FPS_PENDING_OWNER_REVIEW"
    queue["updated_at"] = timestamp
    production["status"] = "DIRECTOR_PASS_ALL_SIX_60FPS_PENDING_OWNER_REVIEW"
    production["updated_at"] = timestamp
    manifest["status"] = "WAITING_OWNER_REVIEW_OF_SIX_DIRECTOR_PASSED_60FPS_TAKES"
    manifest["updated_at"] = timestamp
    atomic_save(queue_path, queue)
    atomic_save(production_path, production)
    atomic_save(manifest_path, manifest)

    if overnight_path.is_file():
        overnight = load(overnight_path)
        overnight.update(
            {
                "status": "DIRECTOR_AND_TECHNICAL_PASS_PENDING_OWNER_REVIEW",
                "director_qc_completed_at": timestamp,
                "auto_approved": False,
                "final_master_created": False,
                "foley_started": False,
                "next_gate": "OWNER_VISUAL_REVIEW_OF_ALL_SIX_TAKES",
            }
        )
        atomic_save(overnight_path, overnight)

    director = {
        "project_id": PROJECT.name,
        "status": "DIRECTOR_PASS_PENDING_OWNER_REVIEW",
        "reviewed_at": timestamp,
        "auto_approval": False,
        "human_approval": "PENDING_OWNER_PLAYBACK",
        "route": "VEJITO_REFERENCE_PRACTICAL_RIFE425_MIDPOINT48_RETIME60_1P25X",
        "technical_report": str(TECHNICAL_REPORT),
        "combined_contact_sheet": technical["combined_contact_sheet"],
        "internal_boundaries": {
            "status": internal["status"],
            "joins": len(internal["joins"]),
            "sheet": internal["sheet"],
        },
        "cross_take_boundaries": {
            "status": cross["status"],
            "joins": len(cross["joins"]),
            "sheet": cross["sheet"],
        },
        "takes": [
            {
                "take_id": take_id,
                "status": "DIRECTOR_PASS_PENDING_OWNER_REVIEW",
                "technical_status": reports[take_id]["technical_status"],
                "freeze_violations": reports[take_id]["freeze_violations"],
                "contact_sheet": reports[take_id]["contact_sheet"],
                "note": TAKE_NOTES[take_id],
            }
            for take_id in TAKE_IDS
        ],
        "final_master_created": False,
        "foley_started": False,
        "next_gate": "Owner reviews and approves or rejects each visible take in Maestro.",
        "backup": str(backup),
    }
    atomic_save(DIRECTOR_REPORT, director)
    print(
        json.dumps(
            {
                "ok": True,
                "status": director["status"],
                "takes": len(director["takes"]),
                "internal_joins": director["internal_boundaries"]["joins"],
                "cross_take_joins": director["cross_take_boundaries"]["joins"],
                "report": str(DIRECTOR_REPORT),
                "human_approval": director["human_approval"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
