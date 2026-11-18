"""NVENC delivery adapter for the canonical Maestro neural FHD upscaler.

The frame extraction, RealESRGAN reconstruction, 75/25 blend, resumability,
audio packet-copy validation and schema-v2 sidecar remain owned by
``postprocess_review_candidate_hd.py``.  This adapter changes only the final
H.264 encoder from the legacy CPU CRF profile to the current GPU/NVENC policy.
"""

from __future__ import annotations

import copy
import importlib.util
from fractions import Fraction
from pathlib import Path
from typing import Any


BASE_PATH = Path(__file__).with_name("postprocess_review_candidate_hd.py")
SPEC = importlib.util.spec_from_file_location("maestro_hd_upscale_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load canonical upscaler: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

ORIGINAL_VALIDATE_PROFILE = base.validate_profile


def validate_profile(profile: dict[str, Any]) -> None:
    encode = base.profile_section(profile, "encode")
    if encode.get("codec") != "h264_nvenc":
        ORIGINAL_VALIDATE_PROFILE(profile)
        return
    # Reuse every canonical structural/model/cadence/audio check.  Only the
    # final encoder contract differs from the legacy libx264 profile.
    canonical = copy.deepcopy(profile)
    canonical["encode"] = {
        "codec": "libx264",
        "preset": "slow",
        "crf": 10,
        "profile": "high",
        "pixel_format": "yuv420p",
        "color_range": "limited",
        "color_space": "bt709",
        "movflags": "+faststart",
    }
    ORIGINAL_VALIDATE_PROFILE(canonical)
    required = {
        "preset": "p7",
        "tune": "hq",
        "rate_control": "vbr",
        "profile": "high",
        "pixel_format": "yuv420p",
        "color_range": "limited",
        "color_space": "bt709",
        "movflags": "+faststart",
    }
    mismatches = {
        key: {"expected": expected, "actual": encode.get(key)}
        for key, expected in required.items()
        if encode.get(key) != expected
    }
    if int(encode.get("cq") or 0) not in range(12, 19):
        mismatches["cq"] = {"expected": "12..18", "actual": encode.get("cq")}
    if int(encode.get("gop") or 0) < 1:
        mismatches["gop"] = {"expected": ">=1", "actual": encode.get("gop")}
    if int(encode.get("bf") or -1) not in range(0, 5):
        mismatches["bf"] = {"expected": "0..4", "actual": encode.get("bf")}
    for key in ("bitrate", "maxrate", "bufsize"):
        if not str(encode.get(key) or "").strip():
            mismatches[key] = {"expected": "non-empty", "actual": encode.get(key)}
    if mismatches:
        raise RuntimeError(f"Invalid NVENC upscale profile: {mismatches}")


def encode_candidate(
    ffmpeg: str,
    source: Path,
    processed_dir: Path,
    destination: Path,
    *,
    fps: Fraction,
    frames: int,
    source_dimensions: tuple[int, int],
    neural_dimensions: tuple[int, int],
    target_dimensions: tuple[int, int],
    profile: dict[str, Any],
    log_handle: Any,
) -> None:
    encode = base.profile_section(profile, "encode")
    fps_value = f"{fps.numerator}/{fps.denominator}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(
        "[4/4] encoding H.264 NVENC HQ and stream-copying source audio",
        flush=True,
    )
    base.run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            fps_value,
            "-start_number",
            "0",
            "-i",
            str(processed_dir / "frame_%06d.png"),
            "-i",
            str(source),
            "-filter_complex",
            base.blend_filter(
                source_dimensions,
                neural_dimensions,
                target_dimensions,
                profile,
            ),
            "-map",
            "[v]",
            "-map",
            "1:a?",
            "-map_metadata",
            "1",
            "-frames:v",
            str(frames),
            "-r",
            fps_value,
            "-fps_mode",
            "cfr",
            "-c:v",
            "h264_nvenc",
            "-preset",
            str(encode["preset"]),
            "-tune",
            str(encode["tune"]),
            "-rc",
            str(encode["rate_control"]),
            "-cq",
            str(encode["cq"]),
            "-b:v",
            str(encode["bitrate"]),
            "-maxrate",
            str(encode["maxrate"]),
            "-bufsize",
            str(encode["bufsize"]),
            "-g",
            str(encode["gop"]),
            "-bf",
            str(encode["bf"]),
            "-profile:v",
            str(encode["profile"]),
            "-pix_fmt",
            str(encode["pixel_format"]),
            "-color_range",
            "tv",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-c:a",
            "copy",
            "-metadata",
            "comment=RealESRGAN 75 percent plus Lanczos 25 percent; H264 NVENC HQ; pending owner review",
            "-movflags",
            str(encode["movflags"]),
            str(destination),
        ],
        "Encode transactional NVENC review candidate",
        log_handle=log_handle,
    )


base.validate_profile = validate_profile
base.encode_candidate = encode_candidate


if __name__ == "__main__":
    try:
        raise SystemExit(base.main())
    except Exception as exc:
        print(f"[error] {exc}", file=base.sys.stderr, flush=True)
        raise SystemExit(1)
