from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
PROJECT = BASE / "ferramentas" / "video_global_engine" / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
SOURCE = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_motion_source_720p24.mp4"
SOURCE_MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_motion_source.json"
OUTPUT = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4"
MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.json"
CONTACT_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60_contact_32.jpg"
BOUNDARY_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60_boundaries_35.jpg"
SCHEMA_VERSION = "gohan_ssj2_cell_visual_cut_v2_fast_720p60"
SUPERSEDES_CANDIDATE = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v1_720p24.mp4"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    if not SOURCE.is_file() or not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError("A montagem-base V2 precisa existir antes do acabamento RIFE.")
    if OUTPUT.exists() or OUTPUT.with_suffix(OUTPUT.suffix + ".review_pipeline.json").exists():
        raise FileExistsError("O destino V2 ja existe; revisao manual obrigatoria antes de substituir.")
    if str(STUDIO) not in sys.path:
        sys.path.insert(0, str(STUDIO))
    from ltx_review_pipeline import (
        EXPECTED_RIFE_MODEL_SHA256,
        EXPECTED_RIFE_REVISION,
        PIPELINE_VERSION,
        run_ltx_review_pipeline,
    )

    # Exact landscape contract already enforced by Maestro's locked RIFE runner.
    # Its 48->60 cadence keeps every source and midpoint frame and produces the
    # requested 1.25x action speed without frame duplication.
    policy = {
        "version": PIPELINE_VERSION,
        "source_resolution": {"width": 1280, "height": 720},
        "delivery": {"retime_method": "setpts_preserve_every_frame"},
    }
    pipeline = run_ltx_review_pipeline(
        source=SOURCE,
        output=OUTPUT,
        project_dir=PROJECT,
        policy=policy,
        ffmpeg=str(FFMPEG),
        progress_cb=lambda percent, message: print(f"[{percent}%] {message}", flush=True),
    )

    delivery = pipeline["delivery"]
    duration = float(delivery["duration_seconds"])
    frames = int(delivery["frames"])
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8-sig"))
    expected_frames = int(source_manifest["frames"]) * 2
    if frames != expected_frames or abs(duration - (expected_frames / 60.0)) > 0.01:
        raise ValueError(f"Entrega temporal inesperada: frames={frames}, duration={duration}")

    decode = subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(OUTPUT), "-f", "null", "NUL"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if decode.returncode != 0:
        raise ValueError("Falha de decodificacao: " + decode.stderr[-2000:])

    freeze = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(OUTPUT), "-vf", "freezedetect=n=0.003:d=0.4", "-an", "-f", "null", "NUL"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    freeze_events = [line.strip() for line in freeze.stderr.splitlines() if "freeze_" in line]
    if freeze_events:
        raise ValueError("O acabamento 60fps ainda possui congelamentos >=0.4s: " + " | ".join(freeze_events))

    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT), "-vf",
            f"fps={32 / duration:.12f},scale=240:-1,tile=8x4", "-frames:v", "1", str(CONTACT_SHEET),
        ],
        check=True,
    )
    cumulative = 0
    boundary_frames: list[int] = []
    for item in source_manifest["timeline"][:-1]:
        cumulative += int(item["editFrames"])
        center = cumulative * 2
        boundary_frames.extend([center - 2, center - 1, center, center + 1, center + 2])
    selection = "+".join(f"eq(n\\,{frame})" for frame in boundary_frames)
    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT), "-vf",
            f"select={selection},scale=320:-1,tile=5x7", "-fps_mode", "passthrough",
            "-frames:v", "1", str(BOUNDARY_SHEET),
        ],
        check=True,
    )

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "TECHNICAL_PASS_PENDING_OWNER_PLAYBACK",
        "supersedesRejectedCandidate": str(SUPERSEDES_CANDIDATE),
        "source": str(SOURCE),
        "sourceSha256": sha256(SOURCE),
        "output": str(OUTPUT),
        "outputSha256": sha256(OUTPUT),
        "width": int(delivery["width"]),
        "height": int(delivery["height"]),
        "fps": int(delivery["fps"]),
        "frames": frames,
        "durationSeconds": duration,
        "videoCodec": "h264_nvenc",
        "audio": "none; Foley pending owner picture approval",
        "speedFactor": 1.25,
        "transitions": "hard cuts; static tails removed before interpolation",
        "freezeEventsAtLeast0_4Seconds": [],
        "interpolation": {
            "engine": "Practical-RIFE",
            "model": "4.25",
            "revision": EXPECTED_RIFE_REVISION,
            "modelSha256": EXPECTED_RIFE_MODEL_SHA256,
            "method": "one midpoint per adjacent source frame; 48fps sequence retimed to CFR60 preserving all frames",
            "directFactor5": False,
        },
        "pipelineSidecar": str(OUTPUT.with_suffix(OUTPUT.suffix + ".review_pipeline.json")),
        "contactSheet": str(CONTACT_SHEET),
        "boundarySheet": str(BOUNDARY_SHEET),
        "humanPlaybackRequired": True,
    }
    atomic_json(MANIFEST, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
