#!/usr/bin/env python3
"""Render Take 05B as deterministic depth-aware VFX from the approved 05A endpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def smoothstep(edge0: float, edge1: float, value: np.ndarray | float):
    amount = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return amount * amount * (3.0 - 2.0 * amount)


def smootherstep(value: float) -> float:
    value = float(np.clip(value, 0.0, 1.0))
    return value ** 3 * (value * (value * 6.0 - 15.0) + 10.0)


def detect_front(source_rgb: np.ndarray) -> tuple[float, np.ndarray]:
    image = source_rgb.astype(np.float32) / 255.0
    red, green, blue = image[..., 0], image[..., 1], image[..., 2]
    intensity = np.max(image, axis=-1)
    violet = np.clip((blue - green) * 2.8 + (red - green) * 0.9, 0.0, 1.0)
    violet *= smoothstep(0.18, 0.86, intensity)
    width = source_rgb.shape[1]
    search = np.zeros_like(violet)
    search[:, int(width * 0.10):int(width * 0.34)] = 1.0
    density = cv2.GaussianBlur((violet * search).mean(axis=0), (0, 0), 2.0)
    front_x = float(np.argmax(density))
    region = np.zeros_like(violet)
    radius = max(16, int(width * 0.055))
    left = max(0, int(front_x) - radius)
    right = min(width, int(front_x) + radius + 1)
    region[:, left:right] = 1.0
    alpha = cv2.GaussianBlur(violet * region, (0, 0), 1.4)
    return front_x, np.clip(alpha * 1.18, 0.0, 0.94)


def cold_plate(source_rgb: np.ndarray, front_x: float, front_alpha: np.ndarray) -> np.ndarray:
    # Remove the *active* violet seam before grading the already-crossed plate.
    # v01 left it active, while an inpaint experiment distorted the building.
    # Color-neutralizing only the measured emission preserves every edge and
    # texture sample from the approved endpoint without leaving violet light.
    image = source_rgb.astype(np.float32) / 255.0
    luminance = (
        image[..., 0] * 0.2126
        + image[..., 1] * 0.7152
        + image[..., 2] * 0.0722
    )
    cold_luma = np.stack(
        (luminance * 0.62, luminance * 0.68, luminance * 0.82), axis=-1
    )
    cold = cold_luma * 0.70 + image * 0.30
    red, green, blue = image[..., 0], image[..., 1], image[..., 2]
    purple = np.clip((blue - green) * 2.7 + (red - green) * 0.65, 0.0, 1.0)
    amber = np.clip((red - blue) * 2.0, 0.0, 1.0)
    bright = smoothstep(0.22, 0.92, np.max(image, axis=-1))
    emission = np.clip(np.maximum(purple, amber) * bright, 0.0, 1.0)
    emission = np.maximum(emission, cv2.GaussianBlur(front_alpha, (0, 0), 2.4))
    neutral = np.stack(
        (luminance * 0.40, luminance * 0.46, luminance * 0.58), axis=-1
    )
    cold = cold * (1.0 - emission[..., None] * 0.62) + neutral * (
        emission[..., None] * 0.62
    )
    width = source_rgb.shape[1]
    xx = np.arange(width, dtype=np.float32)[None, :]
    old_front_band = np.exp(-0.5 * ((xx - front_x) / (width * 0.035)) ** 2)
    old_front_band = np.repeat(old_front_band, source_rgb.shape[0], axis=0)
    residual_seam = np.clip(
        cv2.GaussianBlur(front_alpha, (0, 0), 2.8) * 3.8,
        0.0,
        1.0,
    )
    seam_neutral = np.stack(
        (luminance * 0.25, luminance * 0.29, luminance * 0.36), axis=-1
    )
    seam_mix = np.clip(old_front_band * residual_seam * 0.96, 0.0, 0.96)
    cold = cold * (1.0 - seam_mix[..., None]) + seam_neutral * seam_mix[..., None]
    return np.clip(cold * 255.0, 0, 255).astype(np.uint8)


def build_frame(
    source: np.ndarray,
    silent: np.ndarray,
    depth: np.ndarray,
    energy_alpha: np.ndarray,
    start_front_x: float,
    index: int,
    total_frames: int,
) -> np.ndarray:
    if index == 0:
        return source.copy()
    height, width = source.shape[:2]
    timeline = index / (total_frames - 1)
    move = smootherstep(min(timeline / 0.72, 1.0))
    camera = smootherstep(timeline)
    target_x = -width * 0.075
    current_x = start_front_x + (target_x - start_front_x) * move
    half_width = width * 0.035
    xx = np.arange(width, dtype=np.float32)[None, :]
    yy = np.arange(height, dtype=np.float32)[:, None]
    separation = abs(current_x - start_front_x)
    replacement_progress = smootherstep(
        min(separation / max(half_width * 0.72, 1.0), 1.0)
    )

    # Only the originally warm region is converted.  The already-corrupted
    # right side remains pixel-stable, which prevents a global grading wipe.
    crossed_right_of_front = smoothstep(
        current_x - half_width, current_x + half_width, xx
    )
    # Include the whole original seam in the crossed region.  v01 ended this
    # mask at 50% exactly on the old front and therefore left it glowing in
    # place.  replacement_progress keeps frame 0/1 continuous while the moving
    # front separates from that original position.
    originally_warm = 1.0 - smoothstep(
        start_front_x + half_width * 0.55,
        start_front_x + half_width * 1.45,
        xx,
    )
    crossed = crossed_right_of_front * originally_warm * replacement_progress
    crossed = np.repeat(crossed[..., None], height, axis=0)
    base = source.astype(np.float32) * (1.0 - crossed) + silent.astype(np.float32) * crossed

    # Belt-and-braces removal of the old emissive seam once it has separated
    # from the traveling front.  A dark inert scar may remain, but no active
    # violet edge is allowed to remain at start_front_x.
    old_band = np.exp(
        -0.5 * ((xx - start_front_x) / (width * 0.026)) ** 2
    )
    old_energy = np.clip(
        cv2.GaussianBlur(energy_alpha, (0, 0), 2.6) * 3.0
        + np.repeat(old_band, height, axis=0) * 0.18,
        0.0,
        1.0,
    )
    old_erase = (
        old_energy * replacement_progress * crossed_right_of_front
    )[..., None]
    base = base * (1.0 - old_erase) + silent.astype(np.float32) * old_erase

    translation = current_x - start_front_x
    matrix = np.float32([[1.0, 0.0, translation], [0.0, 1.0, 0.0]])
    moved_alpha = cv2.warpAffine(
        energy_alpha,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    moved_energy = cv2.warpAffine(
        source,
        matrix,
        (width, height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    energy_fade = 1.0 - float(smoothstep(0.58, 0.80, timeline))
    moved_alpha = np.clip(
        moved_alpha * energy_fade * replacement_progress * 1.45,
        0.0,
        0.92,
    )

    # Reconstruct a narrow, translucent and vertically coherent traveling
    # front from the measured seam profile.  The original alpha is fragmented
    # by windows and instruments; using its row profile preserves that organic
    # variation while preventing the front from collapsing into a small blob.
    seam_left = max(0, int(start_front_x - half_width * 1.6))
    seam_right = min(width, int(start_front_x + half_width * 1.6) + 1)
    row_profile = energy_alpha[:, seam_left:seam_right].max(axis=1)
    row_profile = cv2.GaussianBlur(
        row_profile.reshape(-1, 1), (1, 31), 0
    ).reshape(-1)
    profile_peak = float(row_profile.max())
    if profile_peak > 1e-6:
        row_profile /= profile_peak
    source_extent = 1.0 - smoothstep(height * 0.67, height * 0.82, yy)
    row_profile_2d = np.maximum(
        row_profile[:, None] ** 0.72,
        source_extent * 0.24,
    )
    irregular_center = (
        current_x
        + np.sin(yy * 0.038 + timeline * 1.7) * 2.8
        + np.sin(yy * 0.103 - timeline * 1.1) * 1.2
    )
    coherent_front = np.exp(
        -0.5 * ((xx - irregular_center) / (width * 0.0086)) ** 2
    )
    coherent_alpha = np.clip(
        coherent_front
        * row_profile_2d
        * 0.64
        * energy_fade
        * replacement_progress,
        0.0,
        0.66,
    )

    curtain = np.clip(1.0 - np.abs(xx - current_x) / half_width, 0.0, 1.0) ** 2
    curtain = np.repeat(curtain[..., None], height, axis=0)
    violet_black = np.zeros_like(base)
    violet_black[..., 0] = 22.0
    violet_black[..., 1] = 9.0
    violet_black[..., 2] = 38.0
    curtain_strength = 0.18 * energy_fade * replacement_progress
    base = base * (1.0 - curtain * curtain_strength) + violet_black * (
        curtain * curtain_strength
    )

    combined_front_alpha = np.clip(moved_alpha + coherent_alpha, 0.0, 0.94)
    fog = cv2.GaussianBlur(combined_front_alpha, (0, 0), 12.0)
    fog_alpha = np.clip(fog * 0.14 * energy_fade, 0.0, 0.12)[..., None]
    fog_color = np.zeros_like(base)
    fog_color[..., 0] = 62.0
    fog_color[..., 1] = 42.0
    fog_color[..., 2] = 82.0
    base = base * (1.0 - fog_alpha) + fog_color * fog_alpha
    base = base * (1.0 - moved_alpha[..., None]) + moved_energy.astype(np.float32) * (
        moved_alpha[..., None]
    )
    front_color = np.empty_like(base)
    front_color[..., 0] = 116.0
    front_color[..., 1] = 46.0
    front_color[..., 2] = 174.0
    base = base * (1.0 - coherent_alpha[..., None]) + front_color * (
        coherent_alpha[..., None]
    )

    # Continue the rightward camera move established by 05A.  In 768px space
    # the far background moves only 1.6px while the nearest layer moves 9.6px.
    far_shift = -1.6 * camera
    near_shift = -9.6 * camera
    shift = far_shift + depth * (near_shift - far_shift)
    map_x, map_y = np.meshgrid(
        np.arange(width, dtype=np.float32),
        np.arange(height, dtype=np.float32),
    )
    map_x = map_x - shift.astype(np.float32)
    warped = cv2.remap(
        np.clip(base, 0, 255).astype(np.uint8),
        map_x,
        map_y,
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    # Subtle deterministic sharpening counters resampling softness without
    # inventing edges or creating a temporal halo.
    blurred = cv2.GaussianBlur(warped, (0, 0), 0.85)
    return cv2.addWeighted(warped, 1.10, blurred, -0.10, 0.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("depth", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--expected-depth-sha256", required=True)
    parser.add_argument("--frames", type=int, default=65)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source_path = args.source.resolve()
    depth_path = args.depth.resolve()
    output = args.output.resolve()
    for path in (source_path, depth_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_sha = sha256_file(source_path)
    depth_sha = sha256_file(depth_path)
    if source_sha != args.expected_source_sha256.strip().upper():
        raise RuntimeError(f"Source hash mismatch: {source_sha}")
    if depth_sha != args.expected_depth_sha256.strip().upper():
        raise RuntimeError(f"Depth hash mismatch: {depth_sha}")
    if args.frames < 17 or args.fps < 24:
        raise ValueError("Animation requires at least 17 frames and 24 fps.")
    if output.exists() and not args.force:
        raise FileExistsError(output)
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required.")
    encoders = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if "h264_nvenc" not in encoders:
        raise RuntimeError("h264_nvenc is mandatory and unavailable.")

    source = np.asarray(Image.open(source_path).convert("RGB"))
    height, width = source.shape[:2]
    if (width, height) != (768, 432):
        raise RuntimeError(f"Expected 768x432 approved 05A endpoint, got {(width, height)}")
    depth = np.asarray(Image.open(depth_path).convert("L"), dtype=np.float32)
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_CUBIC)
    low, high = np.percentile(depth, [1.0, 99.0])
    depth = np.clip((depth - low) / (high - low), 0.0, 1.0).astype(np.float32)
    depth = cv2.bilateralFilter(depth, d=9, sigmaColor=0.08, sigmaSpace=9)
    front_x, energy_alpha = detect_front(source)
    silent = cold_plate(source, front_x, energy_alpha)

    output.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = output.parent / f"{output.stem}_frames"
    if frames_dir.exists():
        raise FileExistsError(frames_dir)
    frames_dir.mkdir(parents=True)
    started = time.perf_counter()
    for index in range(args.frames):
        frame = build_frame(
            source, silent, depth, energy_alpha, front_x, index, args.frames
        )
        Image.fromarray(frame, "RGB").save(frames_dir / f"frame_{index:03d}.png")

    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(args.fps),
        "-i", str(frames_dir / "frame_%03d.png"),
        "-frames:v", str(args.frames),
        "-c:v", "h264_nvenc", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-b:v", "10M", "-maxrate", "14M",
        "-bufsize", "20M", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True)
    probe = json.loads(subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames,nb_read_frames",
            "-show_entries", "format=duration,size", "-of", "json", str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout)
    stream = probe["streams"][0]
    if int(stream.get("nb_read_frames") or 0) != args.frames:
        raise RuntimeError(f"Decoded frame count mismatch: {stream}")
    elapsed = time.perf_counter() - started
    payload = {
        "schema_version": "1.0",
        "type": "depth_aware_environment_vfx_microtake",
        "algorithm_version": "take05b_depth_vfx_v03_color_neutralized_moving_front",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(source_path),
        "source_sha256": source_sha,
        "depth_source": str(depth_path),
        "depth_sha256": depth_sha,
        "output": str(output),
        "output_sha256": sha256_file(output),
        "frames": args.frames,
        "fps": args.fps,
        "duration_seconds": args.frames / args.fps,
        "timeline_span_seconds": (args.frames - 1) / args.fps,
        "dimensions": [width, height],
        "encoder": "h264_nvenc",
        "lora": "",
        "front_start_x": front_x,
        "front_start_percent": front_x / width * 100.0,
        "front_target_x": -width * 0.075,
        "front_exit_timeline_fraction": 0.72,
        "camera_far_shift_px": -1.6,
        "camera_near_shift_px": -9.6,
        "easing": "smootherstep; timing independent of wall-clock frame rate",
        "render_seconds": elapsed,
        "probe": probe,
        "validation_status": "pending_visual_qc",
        "integration_policy": "video microtake only; approved slideshow images remain unchanged",
    }
    output.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OUTPUT={output}")
    print(f"SHA256={payload['output_sha256']}")
    print(f"FRONT_START_PERCENT={payload['front_start_percent']:.3f}")
    print(f"ELAPSED_SECONDS={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
