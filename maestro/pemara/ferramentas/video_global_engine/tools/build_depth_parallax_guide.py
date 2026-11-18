#!/usr/bin/env python3
"""Build a depth-warped technical end guide for measurable camera parallax."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("depth", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--expected-depth-sha256", required=True)
    parser.add_argument("--far-shift-px", type=float, default=-4.0)
    parser.add_argument("--near-shift-px", type=float, default=-24.0)
    parser.add_argument("--sharpen", type=float, default=0.16)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    depth_path = args.depth.resolve()
    output = args.output.resolve()
    for path in (source, depth_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_sha = sha256_file(source)
    depth_sha = sha256_file(depth_path)
    if source_sha != args.expected_source_sha256.strip().upper():
        raise RuntimeError(f"Source hash mismatch: {source_sha}")
    if depth_sha != args.expected_depth_sha256.strip().upper():
        raise RuntimeError(f"Depth hash mismatch: {depth_sha}")
    if output.exists() and not args.force:
        raise FileExistsError(output)
    if args.near_shift_px >= args.far_shift_px:
        raise ValueError("For a rightward camera move, near shift must be more negative than far shift.")

    source_rgb = np.asarray(Image.open(source).convert("RGB"))
    height, width = source_rgb.shape[:2]
    depth = np.asarray(Image.open(depth_path).convert("L"), dtype=np.float32)
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_CUBIC)
    low, high = np.percentile(depth, [1.0, 99.0])
    if high <= low:
        raise RuntimeError("Depth map has no usable range.")
    depth = np.clip((depth - low) / (high - low), 0.0, 1.0).astype(np.float32)
    depth = cv2.bilateralFilter(depth, d=9, sigmaColor=0.08, sigmaSpace=9)

    shift = args.far_shift_px + depth * (args.near_shift_px - args.far_shift_px)
    xx, yy = np.meshgrid(
        np.arange(width, dtype=np.float32),
        np.arange(height, dtype=np.float32),
    )
    # Inverse mapping: a negative scene shift samples from a larger source x.
    map_x = xx - shift.astype(np.float32)
    warped = cv2.remap(
        source_rgb,
        map_x,
        yy,
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    if args.sharpen > 0.0:
        blurred = cv2.GaussianBlur(warped, (0, 0), 1.0)
        warped = cv2.addWeighted(
            warped, 1.0 + args.sharpen, blurred, -args.sharpen, 0.0
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(warped, "RGB").save(output)
    payload = {
        "schema_version": "1.0",
        "type": "conditioning_guide_not_game_asset",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "source_sha256": source_sha,
        "depth_source": str(depth_path),
        "depth_sha256": depth_sha,
        "output": str(output),
        "output_sha256": sha256_file(output),
        "dimensions": [width, height],
        "mode": "RGB",
        "method": "depth_anything_v2_relative_horizontal_camera_warp",
        "far_shift_px": args.far_shift_px,
        "near_shift_px": args.near_shift_px,
        "predicted_768px_far_shift": args.far_shift_px * 768.0 / width,
        "predicted_768px_near_shift": args.near_shift_px * 768.0 / width,
        "sharpen": args.sharpen,
        "validation_status": "pending_visual_qc",
        "integration_policy": "conditioning only; never replaces an approved slideshow image",
    }
    output.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OUTPUT={output}")
    print(f"SHA256={payload['output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
