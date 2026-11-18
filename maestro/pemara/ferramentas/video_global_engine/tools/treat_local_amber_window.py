#!/usr/bin/env python3
"""Extingue uma única janela âmbar em dois estágios sem alterar o restante do vídeo."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def schedule(frame: int, start: int, first_end: int, hold_end: int, final_end: int) -> float:
    if frame < start:
        return 0.0
    if frame <= first_end:
        return 0.55 * (frame - start + 1) / max(1, first_end - start + 1)
    if frame <= hold_end:
        return 0.55
    if frame <= final_end:
        return 0.55 + 0.45 * (frame - hold_end) / max(1, final_end - hold_end)
    return 1.0


def amber_mask(frame: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = roi
    crop = frame[y0:y1, x0:x1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    blue, green, red = cv2.split(crop)
    candidate = (
        (hsv[:, :, 0] <= 35)
        & (hsv[:, :, 1] >= 55)
        & (hsv[:, :, 2] >= 48)
        & (red.astype(np.float32) > green.astype(np.float32) * 1.03)
        & (green.astype(np.float32) > blue.astype(np.float32) * 1.08)
    ).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(candidate, 8)
    chosen = np.zeros_like(candidate)
    if count > 1:
        target = np.array([(x1 - x0) * 0.5, (y1 - y0) * 0.5], np.float32)
        choices: list[tuple[float, int]] = []
        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area < 2:
                continue
            distance = float(np.linalg.norm(centroids[label] - target))
            choices.append((distance - min(area, 24) * 0.25, label))
        if choices:
            chosen[labels == min(choices)[1]] = 255
    full = np.zeros(frame.shape[:2], np.uint8)
    full[y0:y1, x0:x1] = chosen
    if cv2.countNonZero(full):
        full = cv2.dilate(full, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)
    return full


def run(args: argparse.Namespace) -> dict[str, object]:
    source = args.input.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() and not args.force:
        raise FileExistsError(f"Saída já existe: {output}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg não encontrado")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Não foi possível abrir {source}")
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

    scale_x = width / 768.0
    scale_y = height / 432.0
    roi = (
        round(398 * scale_x),
        round(217 * scale_y),
        round(421 * scale_x),
        round(245 * scale_y),
    )
    masks: list[np.ndarray] = []
    last_valid: np.ndarray | None = None
    for frame in frames:
        mask = amber_mask(frame, roi)
        if cv2.countNonZero(mask) >= 3:
            last_valid = mask
        elif last_valid is not None:
            mask = last_valid.copy()
        masks.append(mask)
    if not any(cv2.countNonZero(mask) >= 3 for mask in masks):
        raise RuntimeError("Núcleo âmbar não encontrado na ROI esperada")

    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s:v",
        f"{width}x{height}",
        "-r",
        f"{fps:.8f}",
        "-i",
        "-",
        "-an",
        "-frames:v",
        str(len(frames)),
        "-r",
        f"{fps:.8f}",
        "-fps_mode",
        "cfr",
        "-c:v",
        "h264_nvenc",
        "-gpu",
        str(args.gpu),
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
        str(max(1, round(fps * 2))),
        "-profile:v",
        "high",
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
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    changed_pixels: list[int] = []
    for index, (frame, mask) in enumerate(zip(frames, masks)):
        amount = schedule(index, args.start, args.first_end, args.hold_end, args.final_end)
        if amount > 0 and cv2.countNonZero(mask):
            target = cv2.inpaint(frame, mask, 2.0, cv2.INPAINT_TELEA)
            feather = cv2.GaussianBlur(mask, (0, 0), 2.0).astype(np.float32) / 255.0
            alpha = np.clip(feather * amount, 0.0, 1.0)[:, :, None]
            treated = np.clip(frame.astype(np.float32) * (1.0 - alpha) + target.astype(np.float32) * alpha, 0, 255).astype(np.uint8)
            changed_pixels.append(int(np.count_nonzero(feather > 0.01)))
        else:
            treated = frame
            changed_pixels.append(0)
        process.stdin.write(treated.tobytes())
    process.stdin.close()
    status = process.wait()
    if status:
        raise RuntimeError(f"ffmpeg encerrou com código {status}")

    report: dict[str, object] = {
        "schema_version": "1.0",
        "type": "localized_video_treatment",
        "created_at": datetime.now().astimezone().isoformat(),
        "input": str(source),
        "input_sha256": sha256(source),
        "output": str(output),
        "output_sha256": sha256(output),
        "frames": len(frames),
        "fps": fps,
        "width": width,
        "height": height,
        "roi": {"x0": roi[0], "y0": roi[1], "x1": roi[2], "y1": roi[3]},
        "schedule": {
            "start": args.start,
            "first_end": args.first_end,
            "hold_end": args.hold_end,
            "final_end": args.final_end,
        },
        "maximum_changed_pixel_area": max(changed_pixels),
        "maximum_changed_frame_fraction": max(changed_pixels) / float(width * height),
        "encoder": "h264_nvenc",
        "validation_status": "pending_local_window_qc",
    }
    sidecar = output.with_suffix(".json")
    sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=int, default=90)
    parser.add_argument("--first-end", type=int, default=99)
    parser.add_argument("--hold-end", type=int, default=103)
    parser.add_argument("--final-end", type=int, default=113)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    report = run(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
