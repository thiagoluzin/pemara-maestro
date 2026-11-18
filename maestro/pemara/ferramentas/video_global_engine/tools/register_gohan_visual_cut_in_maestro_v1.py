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
VIDEO = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v1_720p24.mp4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not VIDEO.is_file():
        raise FileNotFoundError(VIDEO)
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
            "duration_seconds": 80.0,
            "width": 1280,
            "height": 720,
            "fps": 24,
            "video_codec": "h264_nvenc",
            "audio_codec": "none",
            "sha256": sha256(VIDEO),
            "qc_status": "PICTURE_LOCK_TECHNICAL_PASS_PENDING_OWNER_PLAYBACK_AND_FOLEY",
            "purpose": "complete visual cut inside Maestro before Foley",
        },
    )
    print(
        json.dumps(
            {
                "ok": True,
                "assemblyReadiness": readiness,
                "finalOutput": project.get("finalOutput", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
