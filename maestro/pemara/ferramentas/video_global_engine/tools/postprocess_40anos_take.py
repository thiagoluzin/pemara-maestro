#!/usr/bin/env python3
"""Post-process one approved Pemara 40anos take into a traceable FHD30 master."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
BIN_ROOT = ENGINE_ROOT / "tools" / "bin"
RIFE_ROOT = BIN_ROOT / "rife-ncnn-vulkan-20221029-windows" / "rife-ncnn-vulkan-20221029-windows"
RIFE_EXE = RIFE_ROOT / "rife-ncnn-vulkan.exe"
REALESRGAN_ROOT = BIN_ROOT / "realesrgan-ncnn-vulkan-20220424-windows"
REALESRGAN_EXE = REALESRGAN_ROOT / "realesrgan-ncnn-vulkan.exe"

EXPECTED_WIDTH = 832
EXPECTED_HEIGHT = 480
EXPECTED_FPS = 16
EXPECTED_FRAMES = 81
TARGET_FPS = 30
TARGET_FRAMES = 152
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
UPSCALED_WIDTH = 3328
UPSCALED_HEIGHT = 1920
CROP_HEIGHT = 1872
CROP_Y = 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RIFE 16->30 + Real-ESRGAN x4 + FHD30 NVENC for an approved 40anos take."
    )
    parser.add_argument("input", type=Path, help="Approved raw 832x480/16fps/81f MP4.")
    parser.add_argument("output_dir", type=Path, help="Destination for treated videos, log and JSON.")
    parser.add_argument("--work-dir", type=Path, default=Path(r"D:\PemaraVideoWork\40anos_takes"))
    parser.add_argument("--name", default=None, help="Stable output basename.")
    parser.add_argument("--gpu", type=int, default=0, help="Vulkan/NVENC GPU index.")
    parser.add_argument("--rife-model", default="rife-v4.6")
    parser.add_argument(
        "--upscale-model",
        choices=("realesrgan-x4plus", "realesrgan-x4plus-anime", "realesr-animevideov3"),
        default="realesrgan-x4plus",
    )
    parser.add_argument("--expected-sha256", default="", help="Optional approved-source hash gate.")
    parser.add_argument("--approved", action="store_true", help="Confirms the human visual gate was passed.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the plan without writes or GPU use.")
    parser.add_argument("--force", action="store_true", help="Replace only this take's stages and outputs.")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")


def resolve_program(name: str) -> str:
    value = shutil.which(name)
    if not value:
        raise FileNotFoundError(f"Required executable is not in PATH: {name}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def probe(ffprobe: str, path: Path, count_frames: bool = False) -> dict:
    command = [ffprobe, "-v", "error"]
    if count_frames:
        command.append("-count_frames")
    command += ["-show_streams", "-show_format", "-of", "json", str(path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def video_stream(data: dict) -> dict:
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    raise RuntimeError("Input has no video stream.")


def audio_streams(data: dict) -> list[dict]:
    return [stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"]


def png_count(directory: Path) -> int:
    return sum(1 for path in directory.glob("*.png") if path.is_file())


def stage_marker(directory: Path) -> Path:
    # ncnn scans every item inside frame folders; markers must stay beside them.
    return directory.parent / f".{directory.name}.stage.json"


def clear_stage(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.glob("*.png"):
        if path.is_file():
            path.unlink()
    stage_marker(directory).unlink(missing_ok=True)


def stage_ready(directory: Path, expected: int, signature: dict, force: bool) -> bool:
    marker = stage_marker(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if force:
        clear_stage(directory)
        return False
    saved = None
    if marker.is_file():
        try:
            saved = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            saved = None
    count = png_count(directory)
    if count == expected and saved == signature:
        print(f"[resume] {directory.name}: {count} frames", flush=True)
        return True
    if count or marker.exists():
        print(f"[resume] invalidating partial stage {directory.name}: {count}/{expected}", flush=True)
        clear_stage(directory)
    return False


def mark_stage(directory: Path, signature: dict) -> None:
    stage_marker(directory).write_text(json.dumps(signature, ensure_ascii=False, indent=2), encoding="utf-8")


def run(command: list[str], log, cwd: Path | None = None) -> None:
    printable = subprocess.list2cmdline(command)
    print(f"[run] {printable}", flush=True)
    log.write(f"\n$ {printable}\n")
    log.flush()
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)


def validate_source(ffprobe: str, source: Path) -> tuple[dict, dict, float]:
    data = probe(ffprobe, source, count_frames=True)
    stream = video_stream(data)
    width = int(stream["width"])
    height = int(stream["height"])
    fps = float(Fraction(stream["avg_frame_rate"]))
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    duration = float(data["format"]["duration"])
    if (width, height, frames) != (EXPECTED_WIDTH, EXPECTED_HEIGHT, EXPECTED_FRAMES):
        raise RuntimeError(
            f"Expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}/{EXPECTED_FRAMES}f; got {width}x{height}/{frames}f."
        )
    if abs(fps - EXPECTED_FPS) > 0.001:
        raise RuntimeError(f"Expected {EXPECTED_FPS} fps; got {fps}.")
    if audio_streams(data):
        raise RuntimeError("This visual-treatment stage expects a video-only raw take.")
    return data, stream, duration


def validate_delivery(ffprobe: str, path: Path, width: int, height: int, frames: int) -> dict:
    require_file(path, "Delivery")
    data = probe(ffprobe, path, count_frames=True)
    stream = video_stream(data)
    actual_fps = float(Fraction(stream["avg_frame_rate"]))
    actual_frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    if (int(stream["width"]), int(stream["height"])) != (width, height):
        raise RuntimeError(f"Unexpected delivery geometry: {stream['width']}x{stream['height']}")
    if abs(actual_fps - TARGET_FPS) > 0.001 or actual_frames != frames:
        raise RuntimeError(f"Unexpected cadence: {actual_fps} fps / {actual_frames} frames")
    if stream.get("codec_name") != "h264" or stream.get("pix_fmt") != "yuv420p":
        raise RuntimeError(f"Unexpected codec/pixel format: {stream.get('codec_name')}/{stream.get('pix_fmt')}")
    if audio_streams(data):
        raise RuntimeError("Unexpected audio stream in visual-treatment delivery.")
    return data


def ensure_nvenc(ffmpeg: str) -> None:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if "h264_nvenc" not in result.stdout:
        raise RuntimeError("h264_nvenc is unavailable; CPU encoding fallback is forbidden.")


def encode_command(
    ffmpeg: str,
    frames_dir: Path,
    destination: Path,
    gpu: int,
    vf: str | None = None,
) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-framerate",
        str(TARGET_FPS),
        "-start_number",
        "0",
        "-i",
        str(frames_dir / "%08d.png"),
    ]
    if vf:
        command += ["-vf", vf]
    command += [
        "-frames:v",
        str(TARGET_FRAMES),
        "-r",
        str(TARGET_FPS),
        "-fps_mode",
        "cfr",
        "-an",
        "-c:v",
        "h264_nvenc",
        "-gpu",
        str(gpu),
        "-preset",
        "p7",
        "-tune",
        "hq",
        "-rc:v",
        "vbr",
        "-cq:v",
        "10",
        "-b:v",
        "0",
        "-maxrate:v",
        "32M",
        "-bufsize:v",
        "64M",
        "-multipass",
        "fullres",
        "-spatial-aq",
        "1",
        "-temporal-aq",
        "1",
        "-aq-strength",
        "8",
        "-rc-lookahead",
        "20",
        "-bf",
        "3",
        "-b_ref_mode",
        "middle",
        "-g",
        "60",
        "-profile:v",
        "high",
        "-level:v",
        "4.1",
        "-pix_fmt",
        "yuv420p",
        "-color_range",
        "tv",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    return command


def main() -> int:
    args = parse_args()
    source = args.input.resolve()
    require_file(source, "Approved raw take")
    require_file(RIFE_EXE, "RIFE ncnn Vulkan")
    require_file(REALESRGAN_EXE, "Real-ESRGAN ncnn Vulkan")
    ffmpeg = resolve_program("ffmpeg")
    ffprobe = resolve_program("ffprobe")
    ensure_nvenc(ffmpeg)

    if not args.approved and not args.dry_run:
        raise RuntimeError("Human approval gate is closed. Pass --approved only after explicit approval.")

    source_probe, source_video, source_duration = validate_source(ffprobe, source)
    source_hash = sha256(source)
    expected_hash = args.expected_sha256.strip().upper()
    if expected_hash and source_hash != expected_hash:
        raise RuntimeError(f"Approved-source hash mismatch: {source_hash} != {expected_hash}")

    base_name = args.name or source.stem.removesuffix("_preview_480p_16fps_81f")
    output_dir = args.output_dir.resolve()
    work_root = args.work_dir.resolve() / base_name
    raw_frames = work_root / "01_raw16"
    rife_frames = work_root / "02_rife30"
    upscaled_frames = work_root / "03_x4plus"
    intermediate = output_dir / f"{base_name}_rife_832x480_30fps.mp4"
    master = output_dir / f"{base_name}_treated_1920x1080_30fps.mp4"
    report_path = master.with_suffix(".json")
    log_path = output_dir / f"{base_name}_treatment.log"
    final_duration = TARGET_FRAMES / TARGET_FPS

    source_stat = source.stat()
    source_signature = {
        "source": source.as_posix(),
        "sha256": source_hash,
        "size": source_stat.st_size,
        "mtime_ns": source_stat.st_mtime_ns,
        "width": EXPECTED_WIDTH,
        "height": EXPECTED_HEIGHT,
        "fps": EXPECTED_FPS,
        "frames": EXPECTED_FRAMES,
    }
    plan = {
        "schema_version": "1.0",
        "type": "pemara_40anos_postprocess_plan",
        "source": source.as_posix(),
        "source_sha256": source_hash,
        "source_probe": source_probe,
        "human_approval": bool(args.approved),
        "interpolation": {
            "engine": f"RIFE ncnn Vulkan {args.rife_model}",
            "gpu": args.gpu,
            "source_frames": EXPECTED_FRAMES,
            "target_frames": TARGET_FRAMES,
            "source_fps": EXPECTED_FPS,
            "target_fps": TARGET_FPS,
        },
        "upscale": {
            "engine": "Real-ESRGAN ncnn Vulkan",
            "model": args.upscale_model,
            "scale": 4,
            "gpu": args.gpu,
            "frame_geometry": f"{UPSCALED_WIDTH}x{UPSCALED_HEIGHT}",
        },
        "geometry": {
            "policy": "full_bleed_no_stretch",
            "crop": f"{UPSCALED_WIDTH}:{CROP_HEIGHT}:0:{CROP_Y}",
            "crop_equivalent_at_source": "832:468:0:6",
            "final": f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
            "color_grade": "preserved; no eq or unsharp",
        },
        "encode": "H.264 NVENC p7 HQ VBR CQ10, maxrate 32M, bufsize 64M, BT.709 limited, yuv420p, no audio",
        "intermediate": intermediate.as_posix(),
        "master": master.as_posix(),
        "work_root": work_root.as_posix(),
        "expected_duration_seconds": final_duration,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        print("[dry-run] validation passed; no directories, frames or videos were written.", flush=True)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)
    if args.force:
        for path in (intermediate, master, report_path):
            if path.is_file():
                path.unlink()
    elif any(path.exists() for path in (intermediate, master, report_path)):
        raise FileExistsError("Treatment output already exists. Validate it or use --force for this exact take.")

    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        log.write(f"\n=== treatment {datetime.now().astimezone().isoformat()} ===\n")
        log.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")

        raw_signature = {**source_signature, "stage": "lossless_png_extract"}
        if not stage_ready(raw_frames, EXPECTED_FRAMES, raw_signature, args.force):
            print("[1/5] extracting 81 lossless source frames", flush=True)
            run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-i",
                    str(source),
                    "-map",
                    "0:v:0",
                    "-vsync",
                    "0",
                    "-start_number",
                    "0",
                    str(raw_frames / "%08d.png"),
                ],
                log,
            )
            if png_count(raw_frames) != EXPECTED_FRAMES:
                raise RuntimeError("Lossless extraction did not produce 81 frames.")
            mark_stage(raw_frames, raw_signature)

        rife_signature = {
            **source_signature,
            "stage": f"RIFE {args.rife_model}",
            "target_fps": TARGET_FPS,
            "target_frames": TARGET_FRAMES,
        }
        if not stage_ready(rife_frames, TARGET_FRAMES, rife_signature, args.force):
            print("[2/5] interpolating 81 -> 152 frames with RIFE on GPU 0", flush=True)
            run(
                [
                    str(RIFE_EXE),
                    "-i",
                    str(raw_frames),
                    "-o",
                    str(rife_frames),
                    "-m",
                    args.rife_model,
                    "-n",
                    str(TARGET_FRAMES),
                    "-g",
                    str(args.gpu),
                    "-j",
                    "2:4:2",
                    "-f",
                    "%08d.png",
                ],
                log,
                RIFE_ROOT,
            )
            if png_count(rife_frames) != TARGET_FRAMES:
                raise RuntimeError("RIFE did not produce 152 frames.")
            mark_stage(rife_frames, rife_signature)

        intermediate_partial = intermediate.with_name(intermediate.stem + ".partial.mp4")
        intermediate_partial.unlink(missing_ok=True)
        print("[3/5] encoding the traceable 832x480/30fps RIFE intermediate with NVENC", flush=True)
        run(encode_command(ffmpeg, rife_frames, intermediate_partial, args.gpu), log)
        validate_delivery(ffprobe, intermediate_partial, EXPECTED_WIDTH, EXPECTED_HEIGHT, TARGET_FRAMES)
        intermediate_partial.replace(intermediate)

        upscale_signature = {
            **rife_signature,
            "stage": f"Real-ESRGAN {args.upscale_model} x4",
            "width": UPSCALED_WIDTH,
            "height": UPSCALED_HEIGHT,
        }
        if not stage_ready(upscaled_frames, TARGET_FRAMES, upscale_signature, args.force):
            print(f"[4/5] reconstructing 152 frames with {args.upscale_model} x4 on GPU 0", flush=True)
            run(
                [
                    str(REALESRGAN_EXE),
                    "-i",
                    str(rife_frames),
                    "-o",
                    str(upscaled_frames),
                    "-n",
                    args.upscale_model,
                    "-s",
                    "4",
                    "-g",
                    str(args.gpu),
                    "-j",
                    "2:4:2",
                    "-f",
                    "png",
                ],
                log,
                REALESRGAN_ROOT,
            )
            if png_count(upscaled_frames) != TARGET_FRAMES:
                raise RuntimeError("Real-ESRGAN did not produce 152 frames.")
            first_upscaled = sorted(upscaled_frames.glob("*.png"))[0]
            upscaled_probe = video_stream(probe(ffprobe, first_upscaled))
            if (int(upscaled_probe["width"]), int(upscaled_probe["height"])) != (
                UPSCALED_WIDTH,
                UPSCALED_HEIGHT,
            ):
                raise RuntimeError(
                    f"Unexpected Real-ESRGAN geometry: {upscaled_probe['width']}x{upscaled_probe['height']}"
                )
            mark_stage(upscaled_frames, upscale_signature)

        final_filter = (
            f"crop={UPSCALED_WIDTH}:{CROP_HEIGHT}:0:{CROP_Y},"
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos+accurate_rnd+full_chroma_int,"
            "setsar=1,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
        )
        master_partial = master.with_name(master.stem + ".partial.mp4")
        master_partial.unlink(missing_ok=True)
        print("[5/5] encoding full-bleed 1920x1080/30fps master with NVENC", flush=True)
        run(encode_command(ffmpeg, upscaled_frames, master_partial, args.gpu, final_filter), log)
        master_probe = validate_delivery(
            ffprobe, master_partial, TARGET_WIDTH, TARGET_HEIGHT, TARGET_FRAMES
        )
        master_partial.replace(master)

        print("[verify] decoding the complete master", flush=True)
        run([ffmpeg, "-v", "error", "-i", str(master), "-f", "null", "NUL"], log)

    intermediate_probe = validate_delivery(
        ffprobe, intermediate, EXPECTED_WIDTH, EXPECTED_HEIGHT, TARGET_FRAMES
    )
    master_probe = validate_delivery(ffprobe, master, TARGET_WIDTH, TARGET_HEIGHT, TARGET_FRAMES)
    report = {
        **plan,
        "type": "pemara_40anos_postprocess_result",
        "completed_at": datetime.now().astimezone().isoformat(),
        "source_duration_seconds": source_duration,
        "duration_delta_seconds": final_duration - source_duration,
        "intermediate_sha256": sha256(intermediate),
        "master_sha256": sha256(master),
        "intermediate_probe": intermediate_probe,
        "master_probe": master_probe,
        "qc_status": "technical_pass_visual_qc_pending",
        "next_gate": "Inspect RIFE light trails and Real-ESRGAN detail before game integration.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] INTERMEDIATE={intermediate}", flush=True)
    print(f"[done] MASTER={master}", flush=True)
    print(f"[done] REPORT={report_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr, flush=True)
        raise
