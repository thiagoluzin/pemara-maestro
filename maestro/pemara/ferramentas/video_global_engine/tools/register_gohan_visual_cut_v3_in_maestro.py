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
VIDEO = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60.mp4"
EDIT_MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not VIDEO.is_file() or not EDIT_MANIFEST.is_file():
        raise FileNotFoundError("Entrega V3 ou manifesto editorial ausente.")
    technical = json.loads(EDIT_MANIFEST.read_text(encoding="utf-8-sig"))
    if technical.get("status") != "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK":
        raise ValueError("O V3 não passou pelo gate técnico.")
    actual_sha = sha256(VIDEO)
    if actual_sha != str(technical.get("outputSha256") or ""):
        raise ValueError("O hash do V3 divergiu do manifesto técnico.")

    root_manifest = json.loads((PROJECT / "project_manifest.json").read_text(encoding="utf-8-sig"))
    previous = root_manifest.get("final_output") if isinstance(root_manifest.get("final_output"), dict) else {}
    previous_review = previous.get("human_review") if isinstance(previous.get("human_review"), dict) else {}
    previous_file = str(previous.get("file") or "").replace("/", "\\")
    if previous_file.endswith("deliveries\\gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4"):
        if str(previous_review.get("status") or "") != "REJECTED_BY_OWNER":
            raise ValueError("O V2 precisa estar formalmente rejeitado antes de registrar o V3.")

    if str(STUDIO) not in sys.path:
        sys.path.insert(0, str(STUDIO))
    from video_projects import get_project_assembly_readiness, register_project_final_output

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
            "qc_status": "NEW_TAKE02_V3_RIFE60_TECHNICAL_PASS_PENDING_OWNER_PLAYBACK_AND_FOLEY",
            "purpose": "new visual cut with owner-approved Take 02 V3 for playback before Foley",
            "supersedes": "deliveries/gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4",
            "motion_edit": {
                "take02_replacement": "take_02_microtake_v3_motion_cut_4s.mp4",
                "take02_new_generated_footage": True,
                "freeze_events_at_least_0_4_seconds": 0,
                "speed_factor": 1.25,
            },
            "interpolation": technical["interpolation"],
            "technical_manifest": str(EDIT_MANIFEST.relative_to(PROJECT)).replace("\\", "/"),
        },
    )
    print(json.dumps({
        "ok": True,
        "assemblyReadiness": readiness,
        "finalOutput": project.get("finalOutput", {}),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
