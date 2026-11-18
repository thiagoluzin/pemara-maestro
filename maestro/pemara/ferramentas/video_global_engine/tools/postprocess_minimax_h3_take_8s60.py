from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from fractions import Fraction
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
RIFE_ROOT = (
    ENGINE_ROOT
    / "tools"
    / "bin"
    / "rife-ncnn-vulkan-20221029-windows"
    / "rife-ncnn-vulkan-20221029-windows"
)
RIFE_EXE = RIFE_ROOT / "rife-ncnn-vulkan.exe"
RIFE_MODEL = RIFE_ROOT / "rife-v4.6"
EXPECTED_WIDTH = 1280
EXPECTED_HEIGHT = 720
EXPECTED_NATIVE_FPS = 24
EXPECTED_NATIVE_FRAMES = 192
TARGET_FPS = 60
TARGET_FRAMES = 480
TARGET_DURATION = 8.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Legacy ncnn/Vulkan MiniMax post-process. Disabled by default on the current "
            "RTX 5090 workstation; use the locked Practical-RIFE 4.25 route instead."
        )
    )
    parser.add_argument("project_id")
    parser.add_argument("take_id")
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument(
        "--allow-legacy-vulkan",
        action="store_true",
        help="Explicit rollback-only override. May reproduce the Vulkan plugin failure.",
    )
    return parser.parse_args()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe(path: Path, *, count_frames: bool = False) -> dict:
    command = ["ffprobe", "-v", "error"]
    if count_frames:
        command.append("-count_frames")
    command += ["-show_streams", "-show_format", "-of", "json", str(path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def video_stream(data: dict) -> dict:
    return next(stream for stream in data["streams"] if stream.get("codec_type") == "video")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate(path: Path, *, fps: int, frames: int, profile: str = "") -> dict:
    data = probe(path, count_frames=True)
    stream = video_stream(data)
    actual_fps = float(Fraction(stream.get("avg_frame_rate") or stream["r_frame_rate"]))
    actual_frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    duration = float(data["format"]["duration"])
    if (int(stream["width"]), int(stream["height"])) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise RuntimeError(f"Unexpected geometry: {stream['width']}x{stream['height']}")
    if abs(actual_fps - fps) > 0.001 or actual_frames != frames:
        raise RuntimeError(f"Unexpected cadence: {actual_fps} fps / {actual_frames} frames")
    if abs(duration - TARGET_DURATION) > 0.002:
        raise RuntimeError(f"Unexpected duration: {duration:.6f} seconds")
    if [item for item in data["streams"] if item.get("codec_type") == "audio"]:
        raise RuntimeError("Visual review candidate must not contain audio before picture lock.")
    if profile and str(stream.get("profile") or "") != profile:
        raise RuntimeError(f"Unexpected H.264 profile: {stream.get('profile')}")
    return data


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if not args.allow_legacy_vulkan:
        raise RuntimeError(
            "Legacy rife-ncnn-vulkan 2022 was blocked before plugin initialization because it "
            "stalls/fails on this RTX 5090 workstation. Use "
            "postprocess_gohan_overnight_batch_practical_rife60.py or the shared "
            "ltx_review_pipeline Practical-RIFE 4.25 route."
        )
    project = (ENGINE_ROOT / "projetos" / args.project_id).resolve(strict=True)
    queue_path = project / "take_queue.json"
    production_path = project / "production_manifest.json"
    manifest_path = project / "project_manifest.json"
    queue = load(queue_path)
    take = next(item for item in queue["takes"] if str(item.get("id")) == args.take_id)
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    source_raw = str(video.get("output_preview") or video.get("output_active") or "").strip()
    if not source_raw:
        raise RuntimeError(f"{args.take_id} has no native H3 preview registered.")
    source = Path(source_raw).resolve(strict=True)
    if not source.is_relative_to(project):
        raise RuntimeError("Native source is outside the selected project.")
    if not RIFE_EXE.is_file() or not RIFE_MODEL.is_dir():
        raise FileNotFoundError("RIFE 4.6 runtime is incomplete.")
    validate(source, fps=EXPECTED_NATIVE_FPS, frames=EXPECTED_NATIVE_FRAMES)

    output_dir = project / "takes" / "maestro_generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{source.stem}_rife46_60fps.mp4"
    qc_dir = project / "qc" / f"{args.take_id}_8s60_rife46"
    qc_dir.mkdir(parents=True, exist_ok=True)
    work_root = (project / "qc" / "rife60_work").resolve()
    work = (work_root / args.take_id).resolve()
    if not work.is_relative_to(work_root) or work == work_root:
        raise RuntimeError("Unsafe RIFE work path.")
    native_frames = work / "native"
    interpolated_frames = work / "interpolated"
    if work.exists():
        shutil.rmtree(work)
    native_frames.mkdir(parents=True)
    interpolated_frames.mkdir(parents=True)
    try:
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
            "-start_number", "0", str(native_frames / "%08d.png"),
        ])
        if len(list(native_frames.glob("*.png"))) != EXPECTED_NATIVE_FRAMES:
            raise RuntimeError("Native frame extraction did not produce 192 frames.")
        run([
            str(RIFE_EXE), "-i", str(native_frames), "-o", str(interpolated_frames),
            "-n", str(TARGET_FRAMES), "-m", str(RIFE_MODEL), "-g", str(args.gpu),
            "-j", "2:4:2", "-f", "%08d.png",
        ])
        if len(list(interpolated_frames.glob("*.png"))) != TARGET_FRAMES:
            raise RuntimeError("RIFE did not produce exactly 480 frames.")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(TARGET_FPS), "-start_number", "0",
            "-i", str(interpolated_frames / "%08d.png"),
            "-frames:v", str(TARGET_FRAMES), "-r", str(TARGET_FPS), "-fps_mode", "cfr",
            "-an", "-c:v", "h264_nvenc", "-gpu", str(args.gpu), "-preset", "p7",
            "-tune", "hq", "-profile:v", "main", "-rc:v", "vbr", "-cq:v", "12",
            "-b:v", "0", "-maxrate:v", "32M", "-bufsize:v", "64M",
            "-spatial-aq", "1", "-temporal-aq", "1", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(destination),
        ])
        delivery_probe = validate(destination, fps=TARGET_FPS, frames=TARGET_FRAMES, profile="Main")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(destination), "-f", "null", "NUL"])
        contact = qc_dir / "contact_sheet_12frames.jpg"
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(destination),
            "-vf", "fps=1.5,scale=640:-1,tile=4x3", "-frames:v", "1", str(contact),
        ])
    finally:
        if work.exists() and work.is_relative_to(work_root) and work != work_root:
            shutil.rmtree(work)

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    digest = sha256(destination)
    source_digest = sha256(source)
    queue = load(queue_path)
    take = next(item for item in queue["takes"] if str(item.get("id")) == args.take_id)
    video = take.setdefault("video", {})
    video["native_24fps_source"] = {
        "file": str(source), "sha256": source_digest,
        "fps": 24, "frames": 192, "duration_seconds": 8.0,
    }
    video.update({
        "status": "ready", "output_active": str(destination), "output_preview": str(destination),
        "output_review_candidate": str(destination),
        "preview_model": "MiniMax H3 FL2VA + RIFE 4.6",
        "width": 1280, "height": 720, "fps": 60, "frames": 480,
        "duration_seconds": 8.0, "sha256": digest, "audio_delivery": {
            "status": "NOT_REQUIRED", "required": False, "source_kind": "none",
            "message": "Picture review remains silent until picture lock.",
        },
    })
    take["maestro_status"] = "READY"
    take["status"] = "RENDERED_PENDING_HUMAN_VISUAL_QC"
    take["qc_status"] = "video_8s60_pending_human_review"
    take.setdefault("qc", {}).update({
        "status": "video_8s60_pending_human_review",
        "technical_delivery": "PASS_1280X720_60FPS_480F_8S_RIFE46_NVENC",
        "human_visual_approval": "pending_owner_playback",
        "contact_sheet": str(contact.relative_to(project)).replace("\\", "/"),
    })
    take["maestro_notes"] = (
        "CANDIDATO PRINCIPAL: exatamente 8,000 s, 60 fps e 480 quadros por RIFE 4.6. "
        "Reprovar se qualquer raio atravessar um corpo sem colisao, recuo e dano fisico persistente."
    )
    queue["status"] = f"{args.take_id}_8S60_PENDING_HUMAN_VISUAL_QC"
    queue["updated_at"] = timestamp
    save(queue_path, queue)

    production = load(production_path)
    prod = next(item for item in production["takes"] if str(item.get("id")) == args.take_id)
    prod["generation"].update({
        "status": "RENDERED_8S60_PENDING_HUMAN_VISUAL_QC",
        "native_output": str(source.relative_to(project)).replace("\\", "/"),
        "output_preview": str(destination.relative_to(project)).replace("\\", "/"),
        "output_sha256": digest,
    })
    prod.setdefault("qc", {}).update({
        "status": "VIDEO_8S60_PENDING_HUMAN_REVIEW",
        "human_visual_approval": "pending_owner_playback",
        "technical_delivery": "PASS_1280X720_60FPS_480F_8S_RIFE46_NVENC",
    })
    production["updated_at"] = timestamp
    save(production_path, production)

    manifest = load(manifest_path)
    manifest["status"] = f"WAITING_{args.take_id}_8S60_HUMAN_VISUAL_QC"
    manifest["updated_at"] = timestamp
    manifest["take_review_candidates"] = [{
        "take_id": args.take_id, "engine": "MiniMax H3 FL2VA + RIFE 4.6",
        "status": "PENDING_HUMAN_VISUAL_QC", "output": str(destination.relative_to(project)).replace("\\", "/"),
        "sha256": digest, "fps": 60, "frames": 480, "duration_seconds": 8.0,
        "contact_sheet": str(contact.relative_to(project)).replace("\\", "/"), "registered_at": timestamp,
    }]
    save(manifest_path, manifest)
    sidecar = destination.with_suffix(".mp4.json")
    save(sidecar, {
        "source": str(source), "source_sha256": source_digest, "output": str(destination),
        "output_sha256": digest, "interpolator": "RIFE 4.6", "encoder": "h264_nvenc",
        "probe": delivery_probe, "registered_at": timestamp,
    })
    print(json.dumps({
        "take_id": args.take_id, "output": str(destination), "sha256": digest,
        "fps": 60, "frames": 480, "duration_seconds": 8.0,
        "contact_sheet": str(contact), "human_visual_qc": "pending",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
