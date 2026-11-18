from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
PROJECTS = BASE / "ferramentas" / "video_global_engine" / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
VIDEO = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4"
EDIT_MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not VIDEO.is_file() or not EDIT_MANIFEST.is_file():
        raise FileNotFoundError("Entrega V2 ou manifesto editorial ausente.")
    technical = json.loads(EDIT_MANIFEST.read_text(encoding="utf-8-sig"))
    if technical.get("status") != "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK":
        raise ValueError("O V2 nao passou pelo gate tecnico.")
    actual_sha = sha256(VIDEO)
    if actual_sha != str(technical.get("outputSha256") or ""):
        raise ValueError("O hash do V2 divergiu do manifesto tecnico.")
    if str(STUDIO) not in sys.path:
        sys.path.insert(0, str(STUDIO))
    from video_projects import (
        get_project_assembly_readiness,
        register_project_final_output,
        review_project_final_output,
    )

    root_manifest_path = PROJECT / "project_manifest.json"
    root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8-sig"))
    previous = root_manifest.get("final_output")
    rejection_recorded = False
    if isinstance(previous, dict):
        previous_file = str(previous.get("file") or "").replace("/", "\\")
        previous_status = str((previous.get("human_review") or {}).get("status") or "")
        if previous_file.endswith("deliveries\\gohan_ssj2_cell_visual_cut_v1_720p24.mp4") and previous_status != "REJECTED_BY_OWNER":
            review_project_final_output(
                PROJECTS,
                PROJECT_ID,
                decision="reject",
                reason="Pausas longas nas transicoes e movimentos lentos; proprietario pediu remontagem sem caudas congeladas e entrega 60 fps.",
            )
            rejection_recorded = True

    readiness = get_project_assembly_readiness(PROJECTS, PROJECT_ID)
    if not readiness.get("ready"):
        raise RuntimeError(json.dumps(readiness, ensure_ascii=False, indent=2))
    project = register_project_final_output(
        PROJECTS,
        PROJECT_ID,
        expected_source_fingerprint=str(readiness["sourceFingerprint"]),
        record={
            "file": str(VIDEO),
            "review_file": str(VIDEO),
            "duration_seconds": float(technical["durationSeconds"]),
            "width": int(technical["width"]),
            "height": int(technical["height"]),
            "fps": int(technical["fps"]),
            "frames": int(technical["frames"]),
            "video_codec": "h264_nvenc",
            "audio_codec": "none",
            "sha256": actual_sha,
            "qc_status": "TRANSITION_PAUSES_REMOVED_RIFE60_TECHNICAL_PASS_PENDING_OWNER_PLAYBACK_AND_FOLEY",
            "purpose": "corrected fast visual cut for owner review before Foley",
            "supersedes": "deliveries/gohan_ssj2_cell_visual_cut_v1_720p24.mp4",
            "motion_edit": {
                "static_tails_removed": 4,
                "frozen_openings_removed": 1,
                "freeze_events_at_least_0_4_seconds": 0,
                "speed_factor": 1.25,
            },
            "interpolation": technical["interpolation"],
            "technical_manifest": str(EDIT_MANIFEST.relative_to(PROJECT)).replace("\\", "/"),
        },
    )
    print(
        json.dumps(
            {
                "ok": True,
                "previousV1RejectionRecorded": rejection_recorded,
                "assemblyReadiness": readiness,
                "finalOutput": project.get("finalOutput", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
