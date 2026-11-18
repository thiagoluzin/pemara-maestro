#!/usr/bin/env python3
"""Build pixel-registered conditioning guides for Ritmos da Revolta Take 05.

These files are technical video controls, never slideshow assets.  Every
structural pixel comes from the exact approved Take 05 plate; only colour,
emission and an extracted copy of the existing violet energy are changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


EXPECTED_SOURCE_SHA256 = (
    "12C758A6EB719789083BC5B96795A469B9578E44D1A76479731C942CAD995255"
)
WIDTH = 1920
HEIGHT = 1080


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("mid", type=Path)
    parser.add_argument("end", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    amount = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return amount * amount * (3.0 - 2.0 * amount)


def cold_silence_plate(rgb: np.ndarray) -> np.ndarray:
    """Extinguish warm/violet emission without changing geometry."""
    image = rgb.astype(np.float32) / 255.0
    luminance = (
        image[..., 0] * 0.2126
        + image[..., 1] * 0.7152
        + image[..., 2] * 0.0722
    )
    cold_luma = np.stack(
        (luminance * 0.62, luminance * 0.68, luminance * 0.82), axis=-1
    )
    cold = cold_luma * 0.70 + image * 0.30

    purple = np.clip(
        (image[..., 2] - image[..., 1]) * 2.7
        + (image[..., 0] - image[..., 1]) * 0.65,
        0.0,
        1.0,
    )
    amber = np.clip((image[..., 0] - image[..., 2]) * 2.0, 0.0, 1.0)
    bright = smoothstep(0.22, 0.92, np.max(image, axis=-1))
    emission = np.clip(np.maximum(purple, amber) * bright, 0.0, 1.0)
    # The original boundary also contains near-white electricity that is not
    # detected by a purple-only mask.  Extinguish that glow inside its narrow
    # registered band while retaining the dark physical crack as a scar.
    x_normalized = np.linspace(0.0, 1.0, image.shape[1], dtype=np.float32)[None, :]
    center_band = smoothstep(0.43, 0.48, x_normalized) * (
        1.0 - smoothstep(0.57, 0.62, x_normalized)
    )
    center_band = np.repeat(center_band, image.shape[0], axis=0)
    white_front = smoothstep(0.28, 0.76, np.max(image, axis=-1)) * center_band
    emission = np.clip(np.maximum(emission, white_front), 0.0, 1.0)[..., None]
    neutral_dark = np.stack(
        (luminance * 0.40, luminance * 0.46, luminance * 0.58), axis=-1
    )
    cold = cold * (1.0 - emission * 0.55) + neutral_dark * (emission * 0.55)
    cold *= 1.0 - white_front[..., None] * 0.78
    return np.clip(cold * 255.0, 0, 255).astype(np.uint8)


def build_mid(source: np.ndarray, silent: np.ndarray) -> np.ndarray:
    height, width = source.shape[:2]
    source_front_x = width * 0.525
    target_front_x = width * 0.22
    half_width = width * 0.05
    xx = np.arange(width, dtype=np.float32)[None, :]

    # Left of the front remains alive; right of it uses the exact same pixels
    # with emission extinguished.  The soft edge avoids a synthetic wipe.
    alive = 1.0 - smoothstep(
        target_front_x - half_width,
        target_front_x + half_width,
        xx,
    )
    alive = np.repeat(alive[..., None], height, axis=0)
    mid = source.astype(np.float32) * alive + silent.astype(np.float32) * (1.0 - alive)

    # Extract only violet emissive filaments from the approved central front,
    # then translate those same pixels to the requested registered position.
    normalized = source.astype(np.float32) / 255.0
    intensity = np.max(normalized, axis=-1)
    violet = np.clip(
        (normalized[..., 2] - normalized[..., 1]) * 2.6
        + (normalized[..., 0] - normalized[..., 1]) * 0.8,
        0.0,
        1.0,
    )
    violet *= smoothstep(0.18, 0.88, intensity)
    region = np.zeros_like(violet)
    region[:, int(width * 0.43):int(width * 0.60)] = 1.0
    energy_alpha = cv2.GaussianBlur(violet * region, (0, 0), 1.8)

    translation = target_front_x - source_front_x
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
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    curtain_distance = np.abs(xx - target_front_x)
    curtain = np.clip(1.0 - curtain_distance / half_width, 0.0, 1.0) ** 2.0
    curtain = np.repeat(curtain[..., None], height, axis=0)
    violet_black = np.zeros_like(mid)
    violet_black[..., 0] = 24.0
    violet_black[..., 1] = 11.0
    violet_black[..., 2] = 39.0
    mid = mid * (1.0 - curtain * 0.22) + violet_black * (curtain * 0.22)

    moved_alpha = np.clip(moved_alpha * 1.15, 0.0, 0.92)[..., None]
    mid = mid * (1.0 - moved_alpha) + moved_energy.astype(np.float32) * moved_alpha
    return np.clip(mid, 0, 255).astype(np.uint8)


def write_sidecar(target: Path, source: Path, state: str) -> None:
    payload = {
        "schema_version": "1.0",
        "type": "conditioning_guide_not_game_asset",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "output": str(target),
        "output_sha256": sha256_file(target),
        "dimensions": [WIDTH, HEIGHT],
        "mode": "RGB",
        "method": "deterministic_vfx_from_approved_geometry_plate",
        "state": state,
        "lora": "",
        "validation_status": "pending_visual_qc",
        "integration_policy": (
            "conditioning only; never replaces an approved slideshow image"
        ),
        "continuity_rule": (
            "All structural pixels derive from the approved Take 05 source; "
            "only colour, emission and extracted source-energy layers change."
        ),
    }
    target.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    mid_path = args.mid.resolve()
    end_path = args.end.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_sha = sha256_file(source)
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(
            f"Approved source hash mismatch: expected {EXPECTED_SOURCE_SHA256}, got {source_sha}."
        )
    for target in (mid_path, end_path):
        if target.exists() and not args.force:
            raise FileExistsError(f"Output exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as image:
        registered = image.convert("RGB")
        if registered.size != (WIDTH, HEIGHT):
            raise RuntimeError(
                f"Approved source must remain {(WIDTH, HEIGHT)}, got {registered.size}."
            )
    source_rgb = np.asarray(registered)
    silent = cold_silence_plate(source_rgb)
    mid = build_mid(source_rgb, silent)
    Image.fromarray(mid, "RGB").save(mid_path)
    Image.fromarray(silent, "RGB").save(end_path)
    write_sidecar(mid_path, source, "front_at_x22_percent")
    write_sidecar(end_path, source, "front_exited_left_total_cold_silence")
    print(f"MID={mid_path}")
    print(f"MID_SHA256={sha256_file(mid_path)}")
    print(f"END={end_path}")
    print(f"END_SHA256={sha256_file(end_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
