from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
STUDIO = ENGINE_ROOT.parents[1] / "services" / "studio"
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))

from ltx_review_pipeline import PIPELINE_VERSION, run_ltx_review_pipeline


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
TAKE_SOURCE_DURATIONS = {
    "01": 7.5,
    "02": 3.5,
    "03": 12.0,
    "04": 7.0,
    "05": 12.0,
    "06": 8.5,
}
NATIVE_FPS = 24
TARGET_FPS = 60
WIDTH = 1280
HEIGHT = 720
SPEED_FACTOR = 1.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert all six assembled Gohan candidates through the locked Vejito "
            "Practical-RIFE 4.25 midpoint/CFR60 route."
        )
    )
    parser.add_argument("--gpu", type=int, default=0)
    return parser.parse_args()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_save(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path, *, count_frames: bool = False) -> dict:
    command = ["ffprobe", "-v", "error"]
    if count_frames:
        command.append("-count_frames")
    command += ["-show_streams", "-show_format", "-of", "json", str(path)]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def validate_video(path: Path, *, fps: int, frames: int, duration: float) -> dict:
    data = probe(path, count_frames=True)
    stream = next(item for item in data["streams"] if item.get("codec_type") == "video")
    actual_fps = float(Fraction(stream.get("avg_frame_rate") or stream["r_frame_rate"]))
    actual_frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    actual_duration = float(data["format"]["duration"])
    if (int(stream["width"]), int(stream["height"])) != (WIDTH, HEIGHT):
        raise RuntimeError(f"{path.name}: unexpected geometry {stream['width']}x{stream['height']}")
    if abs(actual_fps - fps) > 0.001 or actual_frames != frames:
        raise RuntimeError(
            f"{path.name}: unexpected cadence {actual_fps:.6f} fps / {actual_frames} frames"
        )
    if abs(actual_duration - duration) > 0.002:
        raise RuntimeError(f"{path.name}: unexpected duration {actual_duration:.6f} seconds")
    if any(item.get("codec_type") == "audio" for item in data["streams"]):
        raise RuntimeError(f"{path.name}: picture review candidate must remain silent")
    return data


def source_for_take(take: dict) -> Path:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    native = video.get("native_24fps_source")
    if isinstance(native, dict):
        raw = str(native.get("file") or "").strip()
        if raw and Path(raw).is_file():
            return Path(raw).resolve()
    for key in ("output_active", "output_preview", "output_review_candidate"):
        raw = str(video.get(key) or "").strip()
        if raw and Path(raw).is_file():
            return Path(raw).resolve()
    raise FileNotFoundError(f"Take {take.get('id')} has no local review source")


def destination_for(source: Path) -> Path:
    stem = source.stem
    if "_24fps_" in stem:
        stem = stem.replace("_24fps_", "_60fps_vejito_speed_", 1)
    else:
        stem += "_60fps_vejito_speed"
    return source.with_name(stem + ".mp4")


def make_contact(video: Path, destination: Path, duration: float) -> None:
    sample_fps = 12.0 / duration
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            (
                f"fps={sample_fps:.8f},"
                "scale=320:180:force_original_aspect_ratio=decrease,"
                "pad=320:180:(ow-iw)/2:(oh-ih)/2:black,tile=4x3"
            ),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(destination),
        ]
    )


def append_history(video: dict, source: Path, source_digest: str, frames: int, duration: float) -> None:
    history = video.setdefault("output_history", [])
    if not any(
        isinstance(item, dict)
        and str(item.get("path") or item.get("file") or "").lower() == str(source).lower()
        for item in history
    ):
        history.append(
            {
                "path": str(source),
                "sha256": source_digest,
                "role": "assembled_24fps_source_preserved_for_rollback",
                "fps": 24,
                "frames": frames,
                "duration_seconds": duration,
            }
        )


def process_take(take_id: str, take: dict) -> dict:
    source_duration = TAKE_SOURCE_DURATIONS[take_id]
    source_frames = round(source_duration * NATIVE_FPS)
    delivery_frames = source_frames * 2
    delivery_duration = delivery_frames / TARGET_FPS
    source = source_for_take(take)
    if not source.is_relative_to(PROJECT.resolve()):
        raise RuntimeError(f"Take {take_id}: source is outside the project")
    validate_video(
        source,
        fps=NATIVE_FPS,
        frames=source_frames,
        duration=source_duration,
    )
    destination = destination_for(source)
    source_digest = sha256(source)
    marker = destination.with_suffix(destination.suffix + ".review_pipeline.json")
    reused = destination.is_file() and marker.is_file()
    policy = {
        "version": PIPELINE_VERSION,
        "source_resolution": {"width": WIDTH, "height": HEIGHT},
        "delivery": {"retime_method": "setpts_preserve_every_frame"},
    }
    pipeline = run_ltx_review_pipeline(
        source=source,
        output=destination,
        project_dir=PROJECT,
        policy=policy,
        ffmpeg="ffmpeg",
        progress_cb=lambda percent, message: print(
            f"[{take_id}] {percent}% {message}", flush=True
        ),
    )
    output_probe = validate_video(
        destination,
        fps=TARGET_FPS,
        frames=delivery_frames,
        duration=delivery_duration,
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(destination),
            "-f",
            "null",
            "NUL",
        ]
    )
    qc_dir = PROJECT / "qc" / "rife60_candidates"
    qc_dir.mkdir(parents=True, exist_ok=True)
    contact = qc_dir / f"take_{take_id}_contact_12frames.jpg"
    make_contact(destination, contact, delivery_duration)
    return {
        "take_id": take_id,
        "source": str(source),
        "source_sha256": source_digest,
        "source_frames": source_frames,
        "source_duration_seconds": source_duration,
        "output": str(destination),
        "output_sha256": sha256(destination),
        "output_frames": delivery_frames,
        "duration_seconds": delivery_duration,
        "fps": TARGET_FPS,
        "speed_factor": SPEED_FACTOR,
        "contact_sheet": str(contact),
        "pipeline_sidecar": str(marker),
        "pipeline": pipeline,
        "probe": output_probe,
        "reused": reused,
    }


def register(results: list[dict]) -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    manifest_path = PROJECT / "project_manifest.json"
    overnight_path = PROJECT / "qc" / "overnight_job_manifest.json"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = PROJECT / "qc" / "before_practical_rife60_registration" / timestamp_slug
    backup.mkdir(parents=True, exist_ok=False)
    for source in (queue_path, production_path, manifest_path, overnight_path):
        if source.is_file():
            shutil.copy2(source, backup / source.name)

    queue = load(queue_path)
    production = load(production_path)
    manifest = load(manifest_path)
    queue_by_id = {str(item.get("id")): item for item in queue.get("takes", [])}
    production_by_id = {str(item.get("id")): item for item in production.get("takes", [])}
    for result in results:
        take_id = result["take_id"]
        for take in (queue_by_id[take_id], production_by_id[take_id]):
            video = take.setdefault("video", {})
            source = Path(result["source"])
            append_history(
                video,
                source,
                result["source_sha256"],
                result["source_frames"],
                result["source_duration_seconds"],
            )
            video["native_24fps_source"] = {
                "file": result["source"],
                "sha256": result["source_sha256"],
                "fps": NATIVE_FPS,
                "frames": result["source_frames"],
                "duration_seconds": result["source_duration_seconds"],
                "preserved_for_rollback": True,
            }
            video.update(
                {
                    "status": "ready",
                    "output_active": result["output"],
                    "output_preview": result["output"],
                    "output_review_candidate": result["output"],
                    "preview_model": "MiniMax H3 assembled source + Vejito Practical-RIFE 4.25",
                    "width": WIDTH,
                    "height": HEIGHT,
                    "fps": TARGET_FPS,
                    "frames": result["output_frames"],
                    "duration_seconds": result["duration_seconds"],
                    "speed_factor": result["speed_factor"],
                    "sha256": result["output_sha256"],
                    "pipeline_sidecar": result["pipeline_sidecar"],
                    "audio_delivery": {
                        "status": "BLOCKED_UNTIL_PICTURE_LOCK",
                        "required": False,
                        "source_kind": "none",
                        "message": "Silent picture review; dialogue and Foley remain gated by owner approval.",
                    },
                }
            )
            take["status"] = "READY_PENDING_OWNER_REVIEW"
            take["maestro_status"] = "READY"
            take["qc_status"] = "video_60fps_vejito_speed_pending_human_review"
            qc = take.setdefault("qc", {})
            qc.update(
                {
                    "status": "video_60fps_vejito_speed_pending_human_review",
                    "auto_approved": False,
                    "technical_delivery": (
                        f"PASS_{WIDTH}X{HEIGHT}_{TARGET_FPS}FPS_"
                        f"{result['output_frames']}F_{result['duration_seconds']}S_"
                        "PRACTICAL_RIFE425_NVENC"
                    ),
                    "human_visual_approval": "pending_owner_playback",
                    "director_visual_review": "PENDING_RIFE60_PLAYBACK",
                    "contact_sheet": str(
                        Path(result["contact_sheet"]).relative_to(PROJECT)
                    ).replace("\\", "/"),
                }
            )
            release_gates = take.setdefault("release_gates", {})
            release_gates["technical"] = "PASS"
            release_gates["art_direction"] = "PENDING_DIRECTOR_RIFE60_REVIEW"
            release_gates["cinematic"] = "PENDING_DIRECTOR_RIFE60_REVIEW"
            release_gates["motion"] = "PENDING_DIRECTOR_RIFE60_REVIEW"
            release_gates["human"] = "PENDING"
            release_gates["video_contact_sheet"] = str(result["contact_sheet"])

        generation = production_by_id[take_id].setdefault("generation", {})
        generation.update(
            {
                "status": "PRACTICAL_RIFE60_READY_PENDING_OWNER_REVIEW",
                "native_output": str(
                    Path(result["source"]).relative_to(PROJECT)
                ).replace("\\", "/"),
                "output_preview": str(
                    Path(result["output"]).relative_to(PROJECT)
                ).replace("\\", "/"),
                "output_sha256": result["output_sha256"],
                "speed_factor": result["speed_factor"],
            }
        )

    queue["status"] = "ALL_VEJITO_STANDARD_60FPS_CANDIDATES_READY_PENDING_OWNER_REVIEW"
    queue["updated_at"] = timestamp
    production["status"] = "ALL_VEJITO_STANDARD_60FPS_CANDIDATES_READY_PENDING_OWNER_REVIEW"
    production["updated_at"] = timestamp
    manifest["status"] = "WAITING_ALL_SIX_VEJITO_STANDARD_60FPS_OWNER_REVIEWS"
    manifest["updated_at"] = timestamp
    manifest["take_review_candidates"] = [
        {
            "take_id": result["take_id"],
            "engine": "MiniMax H3 assembled source + Vejito Practical-RIFE 4.25",
            "status": "PENDING_HUMAN_VISUAL_QC",
            "output": str(Path(result["output"]).relative_to(PROJECT)).replace("\\", "/"),
            "sha256": result["output_sha256"],
            "fps": TARGET_FPS,
            "frames": result["output_frames"],
            "duration_seconds": result["duration_seconds"],
            "source_duration_seconds": result["source_duration_seconds"],
            "speed_factor": result["speed_factor"],
            "contact_sheet": str(
                Path(result["contact_sheet"]).relative_to(PROJECT)
            ).replace("\\", "/"),
            "pipeline_sidecar": str(
                Path(result["pipeline_sidecar"]).relative_to(PROJECT)
            ).replace("\\", "/"),
            "registered_at": timestamp,
        }
        for result in results
    ]
    atomic_save(queue_path, queue)
    atomic_save(production_path, production)
    atomic_save(manifest_path, manifest)

    if overnight_path.is_file():
        overnight = load(overnight_path)
        overnight.update(
            {
                "status": "BATCH_RENDER_COMPLETE_VEJITO_STANDARD_RIFE60_PENDING_OWNER_REVIEW",
                "completed_at": timestamp,
                "auto_approved": False,
                "final_master_created": False,
                "foley_started": False,
                "review_candidates": [
                    {
                        key: result[key]
                        for key in (
                            "take_id",
                            "output",
                            "output_sha256",
                            "fps",
                            "output_frames",
                            "duration_seconds",
                            "source_duration_seconds",
                            "speed_factor",
                            "contact_sheet",
                            "pipeline_sidecar",
                        )
                    }
                    for result in results
                ],
                "next_gate": "OWNER_VISUAL_REVIEW_OF_ALL_SIX_TAKES",
            }
        )
        atomic_save(overnight_path, overnight)

    report = {
        "project_id": PROJECT_ID,
        "status": "TECHNICAL_PASS_DIRECTOR_RIFE60_REVIEW_PENDING",
        "route": "VEJITO_REFERENCE_PRACTICAL_RIFE425_MIDPOINT48_RETIME60_1P25X",
        "auto_approval": False,
        "registered_at": timestamp,
        "backup": str(backup),
        "assembled_source_total_seconds": sum(
            item["source_duration_seconds"] for item in results
        ),
        "review_total_seconds": sum(item["duration_seconds"] for item in results),
        "takes": results,
        "next_gate": "Director RIFE60 visual QC, then owner playback in Maestro.",
    }
    atomic_save(PROJECT / "qc" / "rife60_candidates" / "rife60_batch_report.json", report)


def main() -> int:
    del parse_args().gpu  # The locked Practical-RIFE runtime selects the only local GPU.
    if not PROJECT.is_dir():
        raise FileNotFoundError(PROJECT)
    queue = load(PROJECT / "take_queue.json")
    by_id = {str(item.get("id")): item for item in queue.get("takes", [])}
    results: list[dict] = []
    for take_id in TAKE_SOURCE_DURATIONS:
        print(f"=== TAKE {take_id} / VEJITO PRACTICAL-RIFE STANDARD ===", flush=True)
        results.append(process_take(take_id, by_id[take_id]))
    register(results)
    print(
        json.dumps(
            {
                "ok": True,
                "status": "ALL_SIX_VEJITO_STANDARD_RIFE60_READY_PENDING_OWNER_REVIEW",
                "assembled_source_total_seconds": sum(
                    item["source_duration_seconds"] for item in results
                ),
                "review_total_seconds": sum(item["duration_seconds"] for item in results),
                "takes": [
                    {
                        key: item[key]
                        for key in (
                            "take_id",
                            "output",
                            "output_sha256",
                            "fps",
                            "output_frames",
                            "duration_seconds",
                            "source_duration_seconds",
                            "speed_factor",
                            "contact_sheet",
                            "pipeline_sidecar",
                            "reused",
                        )
                    }
                    for item in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
