#!/usr/bin/env python3
"""Estabiliza deriva global de exposição preservando brilhos coloridos e todo o movimento."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

from treat_local_amber_window import sha256


def metric(frame: np.ndarray, spatial_mask: np.ndarray) -> float:
    y = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)[:, :, 0].astype(np.float64)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gold = (hsv[:, :, 0] <= 35) & (hsv[:, :, 1] >= 70) & (hsv[:, :, 2] >= 45)
    values = y[(spatial_mask > 0) & (~gold) & (y > 2)]
    if not values.size:
        raise RuntimeError("Máscara de exposição sem pixels válidos")
    return float(np.exp(np.mean(np.log(values + 1.0))) - 1.0)


def correct(frame: np.ndarray, gain: float) -> np.ndarray:
    rgb = frame.astype(np.float32) / 255.0
    luminance = 0.114 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.299 * rgb[:, :, 2]
    mapped = luminance * gain / np.maximum(1.0 + luminance * (gain - 1.0), 1e-6)
    scale = mapped / np.maximum(luminance, 1.0 / 255.0)
    adjusted = np.clip(rgb * scale[:, :, None], 0.0, 1.0)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gold = ((hsv[:, :, 0] <= 35) & (hsv[:, :, 1] >= 60) & (hsv[:, :, 2] >= 42)).astype(np.uint8) * 255
    gold = cv2.dilate(gold, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)
    protection = cv2.GaussianBlur(gold, (0, 0), 3.0).astype(np.float32) / 255.0
    protection = np.clip(protection * 0.82, 0.0, 0.82)[:, :, None]
    result = adjusted * (1.0 - protection) + rgb * protection
    return np.clip(result * 255.0, 0, 255).astype(np.uint8)


def command(ffmpeg: str, output: Path, width: int, height: int, fps: float, count: int, gpu: int) -> list[str]:
    return [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s:v", f"{width}x{height}", "-r", f"{fps:.8f}", "-i", "-",
        "-an", "-frames:v", str(count), "-r", f"{fps:.8f}", "-fps_mode", "cfr",
        "-c:v", "h264_nvenc", "-gpu", str(gpu), "-preset", "p7", "-tune", "hq",
        "-rc:v", "vbr", "-cq:v", "10", "-b:v", "0", "-maxrate:v", "32M", "-bufsize:v", "64M",
        "-multipass", "fullres", "-spatial-aq", "1", "-temporal-aq", "1", "-aq-strength", "8",
        "-rc-lookahead", "20", "-bf", "3", "-b_ref_mode", "middle", "-g", str(max(1, round(fps * 2))),
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", str(output),
    ]


def run(args: argparse.Namespace) -> dict[str, object]:
    source = args.input.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() and not args.force:
        raise FileExistsError(output)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg não encontrado")
    capture = cv2.VideoCapture(str(source))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    expected = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frames: list[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames or len(frames) != expected:
        raise RuntimeError(f"Decode incompleto: {len(frames)}/{expected}")

    spatial = np.zeros((height, width), np.uint8)
    cv2.rectangle(spatial, (round(width * 0.20), round(height * 0.05)), (round(width * 0.80), round(height * 0.97)), 255, -1)
    measured = np.array([metric(frame, spatial) for frame in frames], np.float64)
    raw_gain = np.clip(measured[0] / np.maximum(measured, 1e-6), args.min_gain, args.max_gain)
    gains = gaussian_filter1d(raw_gain, args.sigma, mode="nearest")
    gains /= max(gains[0], 1e-6)
    gains = np.clip(gains, args.min_gain, args.max_gain)

    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(command(ffmpeg, output, width, height, fps, len(frames), args.gpu), stdin=subprocess.PIPE)
    assert process.stdin is not None
    for frame, gain in zip(frames, gains):
        process.stdin.write(correct(frame, float(gain)).tobytes())
    process.stdin.close()
    status = process.wait()
    if status:
        raise RuntimeError(f"ffmpeg encerrou com código {status}")

    report: dict[str, object] = {
        "schema_version": "1.0",
        "type": "exposure_stabilization_with_highlight_protection",
        "created_at": datetime.now().astimezone().isoformat(),
        "input": str(source),
        "input_sha256": sha256(source),
        "output": str(output),
        "output_sha256": sha256(output),
        "frames": len(frames),
        "fps": fps,
        "width": width,
        "height": height,
        "reference_metric": float(measured[0]),
        "input_metric_min": float(np.min(measured)),
        "input_metric_final": float(measured[-1]),
        "gain_min": float(np.min(gains)),
        "gain_max": float(np.max(gains)),
        "gain_final": float(gains[-1]),
        "highlight_protection": 0.82,
        "pixel_geometry_changed": False,
        "encoder": "h264_nvenc",
        "validation_status": "pending_exposure_and_structure_qc",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--min-gain", type=float, default=0.8)
    parser.add_argument("--max-gain", type=float, default=3.0)
    parser.add_argument("--sigma", type=float, default=2.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    print(json.dumps(run(parse_args()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
