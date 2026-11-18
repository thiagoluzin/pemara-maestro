#!/usr/bin/env python3
"""Create a traceable neural FHD review candidate without approving it.

The pipeline preserves the source cadence and every audio stream, reconstructs
each video frame with the model selected by the canonical profile, blends 75% of that reconstruction
with 25% of a Lanczos source reconstruction, and publishes only a technically
validated review candidate plus a schema-v2 sidecar.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator


PIPELINE_VERSION = "maestro_ultrasharp_review_candidate_v2"
SIDECAR_SCHEMA_VERSION = "2.0"
ENGINE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = (
    ENGINE_ROOT
    / "upscale_profiles"
    / "realesrgan_x2_balanced_75_25_v1.json"
)
COMFY_ROOT = ENGINE_ROOT.parent / "ComfyUI"
COMFY_OUTPUT_ROOT = COMFY_ROOT / "output"
DEFAULT_WORK_ROOT = Path(r"D:\PemaraVideoWork\review_candidates")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SAVE_NODE_ID = "4"
TECHNICAL_PASS = "technical_pass"
TECHNICAL_PENDING = "technical_pass_visual_qc_pending"
MIN_SOURCE_FPS = Fraction(24, 1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Source MP4/MOV take.")
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Destination for the review candidate, sidecar and log.",
    )
    parser.add_argument("--name", default="", help="Stable candidate name prefix.")
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="Canonical JSON profile path.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_ROOT,
        help="Scratch root for resumable source and neural-upscale frames.",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=0,
        help="Recorded scheduling GPU index. ComfyUI owns device selection.",
    )
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Frames per ComfyUI prompt; bounded by the canonical profile.",
    )
    parser.add_argument(
        "--per-batch",
        type=int,
        default=None,
        help="Frames per model sub-batch; bounded by the canonical profile.",
    )
    parser.add_argument(
        "--comfy-timeout",
        type=float,
        default=None,
        help="Maximum seconds to wait for one ComfyUI prompt.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Seconds between ComfyUI history checks.",
    )
    parser.add_argument(
        "--expected-sha256",
        default="",
        help="Optional source SHA-256 safety gate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform full read-only preflight; never submit a ComfyUI prompt.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild resumable work for this exact fingerprint.",
    )
    return parser.parse_args(argv)


def log(message: str) -> None:
    print(f"[maestro-ultrasharp-v2] {message}", flush=True)


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")


def resolve_program(name: str) -> str:
    result = shutil.which(name)
    if not result:
        raise FileNotFoundError(f"Required executable is not in PATH: {name}")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def safe_stem(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._-")
    if not normalized:
        raise ValueError("Candidate name becomes empty after sanitization.")
    return normalized[:120]


def run_command(
    command: list[str],
    label: str,
    *,
    capture: bool = False,
    log_handle: Any | None = None,
) -> subprocess.CompletedProcess[str]:
    printable = subprocess.list2cmdline(command)
    log(label)
    if log_handle is not None:
        log_handle.write(f"\n$ {printable}\n")
        log_handle.flush()
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE if capture or log_handle is not None else None,
            stderr=subprocess.STDOUT if log_handle is not None else (
                subprocess.PIPE if capture else None
            ),
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stdout or exc.stderr or "").strip()
        if log_handle is not None and details:
            log_handle.write(details + "\n")
            log_handle.flush()
        raise RuntimeError(
            f"{label} failed: {details or f'exit {exc.returncode}'}"
        ) from exc
    if log_handle is not None and completed.stdout:
        log_handle.write(completed.stdout)
        if not completed.stdout.endswith("\n"):
            log_handle.write("\n")
        log_handle.flush()
    return completed


def probe_media(ffprobe: str, path: Path) -> dict[str, Any]:
    completed = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            (
                "stream=index,codec_type,codec_name,profile,width,height,pix_fmt,"
                "r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,duration,"
                "color_range,color_space,color_transfer,color_primaries,"
                "sample_rate,channels,channel_layout,bit_rate:"
                "format=duration,size,bit_rate,format_name"
            ),
            "-of",
            "json",
            str(path),
        ],
        f"ffprobe {path.name}",
        capture=True,
    )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON for {path}") from exc
    if not isinstance(value, dict) or not value.get("streams"):
        raise RuntimeError(f"ffprobe found no streams in {path}")
    return value


def video_stream(probe: dict[str, Any]) -> dict[str, Any]:
    streams = [
        item
        for item in probe.get("streams", [])
        if item.get("codec_type") == "video"
    ]
    if len(streams) != 1:
        raise RuntimeError(f"Expected one video stream, found {len(streams)}")
    return streams[0]


def audio_streams(probe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in probe.get("streams", [])
        if item.get("codec_type") == "audio"
    ]


def parse_rate(raw: Any) -> Fraction:
    try:
        value = Fraction(str(raw or "0/1"))
    except (ValueError, ZeroDivisionError) as exc:
        raise RuntimeError(f"Invalid frame rate: {raw!r}") from exc
    if value < MIN_SOURCE_FPS:
        raise RuntimeError(f"Source frame rate is invalid or too low: {raw!r}")
    return value


def counted_frames(stream: dict[str, Any]) -> int:
    for key in ("nb_read_frames", "nb_frames"):
        raw = str(stream.get(key) or "")
        if raw and raw.upper() != "N/A":
            try:
                value = int(raw)
            except ValueError:
                continue
            if value > 0:
                return value
    raise RuntimeError("ffprobe did not report a decoded video frame count")


def load_profile(path: Path) -> dict[str, Any]:
    require_file(path, "Upscale profile")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid profile JSON: {path}: {exc}") from exc
    if not isinstance(profile, dict):
        raise RuntimeError("Upscale profile must be a JSON object")
    validate_profile(profile)
    return profile


def profile_section(profile: dict[str, Any], name: str) -> dict[str, Any]:
    value = profile.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"Profile section is missing or invalid: {name}")
    return value


def validate_profile(profile: dict[str, Any]) -> None:
    required_top = {
        "schema_version",
        "profile_id",
        "pipeline_version",
        "target",
        "cadence",
        "audio",
        "upscale",
        "comfy",
        "http",
        "encode",
        "disk",
    }
    missing = sorted(required_top - set(profile))
    if missing:
        raise RuntimeError("Profile is missing fields: " + ", ".join(missing))
    if profile.get("pipeline_version") != PIPELINE_VERSION:
        raise RuntimeError(
            f"Profile pipeline_version must be {PIPELINE_VERSION!r}"
        )
    target = profile_section(profile, "target")
    width = int(target.get("width") or 0)
    height = int(target.get("height") or 0)
    if width < 2 or height < 2 or width % 2 or height % 2:
        raise RuntimeError("Profile target dimensions must be positive even integers")
    if (
        target.get("pixel_format") != "yuv420p"
        or target.get("color_range") != "limited"
        or target.get("color_space") != "bt709"
    ):
        raise RuntimeError("Profile target must be yuv420p BT.709 limited")
    cadence = profile_section(profile, "cadence")
    if cadence.get("policy") != "preserve_native_fps_and_frame_count":
        raise RuntimeError("Profile cadence must preserve native FPS and frame count")
    audio = profile_section(profile, "audio")
    if audio.get("policy") != "stream_copy_all":
        raise RuntimeError("Profile audio policy must be stream_copy_all")
    upscale = profile_section(profile, "upscale")
    if upscale.get("engine") != "ComfyUI":
        raise RuntimeError("Profile upscale engine must be ComfyUI")
    if int(upscale.get("model_scale") or 0) not in {2, 4}:
        raise RuntimeError("Profile model_scale must be 2 or 4")
    neural = float(upscale.get("neural_blend") or 0.0)
    source = float(upscale.get("source_lanczos_blend") or 0.0)
    if not math.isclose(neural, 0.75) or not math.isclose(source, 0.25):
        raise RuntimeError("Profile blend must be 75% neural reconstruction and 25% Lanczos")
    if not math.isclose(neural + source, 1.0, abs_tol=1e-9):
        raise RuntimeError("Profile blend weights must sum to one")
    if upscale.get("downscale_method") != "lanczos":
        raise RuntimeError("Profile downscale_method must be lanczos")
    if upscale.get("precision") not in {"float16", "float32", "bfloat16"}:
        raise RuntimeError("Profile precision is unsupported")
    expected_model_hash = str(upscale.get("model_sha256") or "").upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_model_hash):
        raise RuntimeError("Profile model_sha256 must be a SHA-256 hex digest")
    comfy = profile_section(profile, "comfy")
    for key in ("chunk_size_min", "chunk_size", "chunk_size_max"):
        if int(comfy.get(key) or 0) < 1:
            raise RuntimeError(f"Profile {key} must be positive")
    if not (
        int(comfy["chunk_size_min"])
        <= int(comfy["chunk_size"])
        <= int(comfy["chunk_size_max"])
        <= 24
    ):
        raise RuntimeError("Profile chunk-size range exceeds the safe limit of 24")
    if not (
        int(comfy.get("per_batch_min") or 0)
        <= int(comfy.get("per_batch") or 0)
        <= int(comfy.get("per_batch_max") or 0)
        <= 4
    ):
        raise RuntimeError("Profile per-batch range exceeds the safe limit of 4")
    nodes = comfy.get("required_nodes")
    if not isinstance(nodes, list) or not all(
        isinstance(node, str) and node for node in nodes
    ):
        raise RuntimeError("Profile required_nodes must be a non-empty string list")
    http = profile_section(profile, "http")
    if not 1 <= int(http.get("attempts") or 0) <= 8:
        raise RuntimeError("Profile HTTP attempts must be between 1 and 8")
    encode = profile_section(profile, "encode")
    if (
        encode.get("codec") != "libx264"
        or int(encode.get("crf") or -1) != 10
        or encode.get("pixel_format") != "yuv420p"
        or encode.get("color_range") != "limited"
        or encode.get("color_space") != "bt709"
    ):
        raise RuntimeError("Profile encode must be libx264 CRF10 yuv420p BT.709 limited")


def effective_settings(
    args: argparse.Namespace,
    profile: dict[str, Any],
) -> dict[str, Any]:
    comfy = profile_section(profile, "comfy")
    http = profile_section(profile, "http")
    chunk_size = int(
        args.chunk_size if args.chunk_size is not None else comfy["chunk_size"]
    )
    per_batch = int(
        args.per_batch if args.per_batch is not None else comfy["per_batch"]
    )
    if not int(comfy["chunk_size_min"]) <= chunk_size <= int(
        comfy["chunk_size_max"]
    ):
        raise RuntimeError(
            f"--chunk-size must be {comfy['chunk_size_min']}.."
            f"{comfy['chunk_size_max']}"
        )
    if not int(comfy["per_batch_min"]) <= per_batch <= int(
        comfy["per_batch_max"]
    ):
        raise RuntimeError(
            f"--per-batch must be {comfy['per_batch_min']}.."
            f"{comfy['per_batch_max']}"
        )
    prompt_timeout = float(
        args.comfy_timeout
        if args.comfy_timeout is not None
        else http["prompt_timeout_seconds"]
    )
    poll_interval = float(
        args.poll_interval
        if args.poll_interval is not None
        else http["poll_interval_seconds"]
    )
    if prompt_timeout <= 0 or poll_interval <= 0:
        raise RuntimeError("ComfyUI timeout and poll interval must be positive")
    return {
        "comfy_url": str(args.comfy_url).rstrip("/"),
        "chunk_size": chunk_size,
        "per_batch": per_batch,
        "prompt_timeout_seconds": prompt_timeout,
        "poll_interval_seconds": poll_interval,
        "gpu": int(args.gpu),
    }


def resolve_model(profile: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    upscale = profile_section(profile, "upscale")
    relative = Path(str(upscale.get("model_relative_path") or ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("Profile model_relative_path must stay inside ComfyUI")
    model_path = (COMFY_ROOT / relative).resolve()
    comfy_root = COMFY_ROOT.resolve()
    if comfy_root not in model_path.parents:
        raise RuntimeError("Resolved model path escapes the ComfyUI root")
    require_file(model_path, "neural upscale model")
    actual_hash = sha256(model_path)
    expected_hash = str(upscale["model_sha256"]).upper()
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"Neural upscale model hash mismatch: {actual_hash} != {expected_hash}"
        )
    return model_path, {
        "name": str(upscale["model"]),
        "path": model_path.as_posix(),
        "sha256": actual_hash,
        "size": model_path.stat().st_size,
    }


def validate_source_probe(
    probe: dict[str, Any],
) -> tuple[dict[str, Any], Fraction, int, int, int]:
    video = video_stream(probe)
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if width < 2 or height < 2:
        raise RuntimeError(f"Source geometry is invalid: {width}x{height}")
    fps = parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    nominal_fps = parse_rate(video.get("r_frame_rate") or video.get("avg_frame_rate"))
    if fps != nominal_fps:
        raise RuntimeError(
            "Variable-frame-rate sources are not accepted by the native-CFR "
            f"review profile: avg={fps}, nominal={nominal_fps}"
        )
    frames = counted_frames(video)
    if frames < 2:
        raise RuntimeError(f"Source frame count is invalid: {frames}")
    return video, fps, frames, width, height


def neural_ratio(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
    model_scale: int,
) -> tuple[float, tuple[int, int]]:
    full_width = source_width * model_scale
    full_height = source_height * model_scale
    ratio = max(target_width / full_width, target_height / full_height)
    if ratio > 1.0 + 1e-12:
        raise RuntimeError(
            "Source is too small for a native 4x reconstruction to cover "
            f"{target_width}x{target_height}: {source_width}x{source_height}"
        )
    ratio = min(1.0, ratio)
    for _ in range(8):
        width = int(full_width * ratio)
        height = int(full_height * ratio)
        if width >= target_width and height >= target_height:
            return ratio, (width, height)
        ratio = math.nextafter(ratio, 1.0)
    raise RuntimeError("Could not derive a safe UltraSharp downscale ratio")


def center_crop(
    width: int,
    height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int, int, int]:
    target_ratio = target_width / target_height
    if width / height >= target_ratio:
        crop_height = height - (height % 2)
        crop_width = int(crop_height * target_ratio) // 2 * 2
    else:
        crop_width = width - (width % 2)
        crop_height = int(crop_width / target_ratio) // 2 * 2
    x = ((width - crop_width) // 2) // 2 * 2
    y = ((height - crop_height) // 2) // 2 * 2
    return crop_width, crop_height, x, y


def fps_tag(fps: Fraction) -> str:
    value = float(fps)
    if abs(value - round(value)) < 0.000001:
        return str(round(value))
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if (
        len(header) < 24
        or header[:8] != PNG_SIGNATURE
        or header[12:16] != b"IHDR"
    ):
        raise RuntimeError(f"Invalid PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def validate_sequence_range(
    folder: Path,
    start: int,
    count: int,
    dimensions: tuple[int, int],
) -> None:
    for index in range(start, start + count):
        frame = folder / f"frame_{index:06d}.png"
        if not frame.is_file():
            raise RuntimeError(f"Missing frame: {frame}")
        if png_dimensions(frame) != dimensions:
            raise RuntimeError(f"Unexpected frame dimensions: {frame}")


def sequence_range_valid(
    folder: Path,
    start: int,
    count: int,
    dimensions: tuple[int, int],
) -> bool:
    try:
        validate_sequence_range(folder, start, count, dimensions)
    except (OSError, RuntimeError):
        return False
    return True


def clear_frame_range(folder: Path, start: int, count: int) -> None:
    for index in range(start, start + count):
        (folder / f"frame_{index:06d}.png").unlink(missing_ok=True)


def marker_matches(path: Path, signature: dict[str, Any]) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")) == signature
    except (OSError, json.JSONDecodeError):
        return False


def existing_ancestor(path: Path) -> Path:
    candidate = path.resolve()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise RuntimeError(f"No existing ancestor for disk check: {path}")
        candidate = parent
    return candidate


def disk_requirements(
    source_width: int,
    source_height: int,
    neural_width: int,
    neural_height: int,
    frames: int,
    chunk_size: int,
    profile: dict[str, Any],
) -> dict[str, int]:
    disk = profile_section(profile, "disk")
    bytes_per_pixel = float(disk["png_working_bytes_per_pixel"])
    headroom = int(disk["headroom_bytes"])
    output_reserve = int(disk["output_reserve_bytes"])
    work = math.ceil(
        frames
        * (
            source_width * source_height
            + neural_width * neural_height
        )
        * bytes_per_pixel
    ) + headroom
    comfy = math.ceil(
        chunk_size * neural_width * neural_height * bytes_per_pixel
    ) + headroom
    output = output_reserve + headroom
    return {"work": work, "comfy": comfy, "output": output}


def check_disk_space(
    work_dir: Path,
    output_dir: Path,
    requirements: dict[str, int],
) -> dict[str, dict[str, int | str]]:
    locations = {
        "work": work_dir,
        "comfy": COMFY_OUTPUT_ROOT,
        "output": output_dir,
    }
    volumes: dict[str, dict[str, Any]] = {}
    for label, path in locations.items():
        ancestor = existing_ancestor(path)
        key = ancestor.anchor.lower() or str(ancestor)
        entry = volumes.setdefault(
            key,
            {
                "path": str(ancestor),
                "required_bytes": 0,
                "labels": [],
            },
        )
        entry["required_bytes"] += requirements[label]
        entry["labels"].append(label)
    report: dict[str, dict[str, int | str]] = {}
    for key, entry in volumes.items():
        free = shutil.disk_usage(entry["path"]).free
        required = int(entry["required_bytes"])
        if free < required:
            raise RuntimeError(
                f"Insufficient free space on {key}: {free} bytes free, "
                f"{required} required for {','.join(entry['labels'])}"
            )
        report[key] = {
            "path": entry["path"],
            "free_bytes": free,
            "required_bytes": required,
            "labels": ",".join(entry["labels"]),
        }
    return report


def _retryable_http_status(status: int) -> bool:
    return status in {408, 425, 429} or 500 <= status <= 599


def http_bytes(
    url: str,
    profile: dict[str, Any],
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float | None = None,
    retry: bool = True,
) -> bytes:
    http = profile_section(profile, "http")
    attempts = int(http["attempts"]) if retry else 1
    initial = float(http["initial_backoff_seconds"])
    maximum = float(http["max_backoff_seconds"])
    request_timeout = float(timeout or http["request_timeout_seconds"])
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if attempt >= attempts or not _retryable_http_status(exc.code):
                raise RuntimeError(
                    f"ComfyUI HTTP {exc.code} for {url}: {body}"
                ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt >= attempts:
                raise RuntimeError(f"Cannot reach ComfyUI at {url}: {exc}") from exc
        delay = min(maximum, initial * (2 ** (attempt - 1)))
        time.sleep(delay)
    raise AssertionError("unreachable HTTP retry state")


def http_json(
    url: str,
    profile: dict[str, Any],
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float | None = None,
    retry: bool = True,
) -> Any:
    raw = http_bytes(
        url,
        profile,
        method=method,
        payload=payload,
        timeout=timeout,
        retry=retry,
    )
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ComfyUI returned invalid JSON for {url}") from exc


def assert_comfy_idle(base_url: str, profile: dict[str, Any]) -> None:
    queue = http_json(f"{base_url}/queue", profile)
    if not isinstance(queue, dict):
        raise RuntimeError("ComfyUI queue response is invalid")
    running = queue.get("queue_running") or []
    pending = queue.get("queue_pending") or []
    if running or pending:
        raise RuntimeError(
            f"ComfyUI is not idle ({len(running)} running, "
            f"{len(pending)} pending); refusing to compete for the GPU"
        )


def preflight_comfy(base_url: str, profile: dict[str, Any]) -> None:
    stats = http_json(f"{base_url}/system_stats", profile)
    if not isinstance(stats, dict):
        raise RuntimeError("ComfyUI system_stats response is invalid")
    assert_comfy_idle(base_url, profile)
    comfy = profile_section(profile, "comfy")
    for node in comfy["required_nodes"]:
        info = http_json(
            f"{base_url}/object_info/{urllib.parse.quote(node)}",
            profile,
        )
        if not isinstance(info, dict) or node not in info:
            raise RuntimeError(f"Required ComfyUI node is unavailable: {node}")


def build_workflow(
    frames_dir: Path,
    *,
    start_index: int,
    count: int,
    per_batch: int,
    downscale_ratio: float,
    filename_prefix: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    upscale = profile_section(profile, "upscale")
    return {
        "1": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": upscale["model"]},
        },
        "2": {
            "class_type": "LoadImagesFromFolderKJ",
            "inputs": {
                "folder": str(frames_dir.resolve()),
                "width": -1,
                "height": -1,
                "keep_aspect_ratio": "stretch",
                "image_load_cap": count,
                "start_index": start_index,
                "include_subfolders": False,
            },
        },
        "3": {
            "class_type": "ImageUpscaleWithModelBatched",
            "inputs": {
                "upscale_model": ["1", 0],
                "images": ["2", 0],
                "per_batch": per_batch,
                "downscale_ratio": downscale_ratio,
                "downscale_method": upscale["downscale_method"],
                "precision": upscale["precision"],
            },
        },
        SAVE_NODE_ID: {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["3", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }


def submit_prompt(
    base_url: str,
    workflow: dict[str, Any],
    client_id: str,
    profile: dict[str, Any],
) -> str:
    # POST is deliberately not retried: a lost response could otherwise enqueue
    # the same GPU work twice. All idempotent reads/downloads do retry.
    response = http_json(
        f"{base_url}/prompt",
        profile,
        method="POST",
        payload={"prompt": workflow, "client_id": client_id},
        timeout=60.0,
        retry=False,
    )
    if not isinstance(response, dict):
        raise RuntimeError("Unexpected ComfyUI /prompt response")
    if response.get("error") or response.get("node_errors"):
        raise RuntimeError(
            "ComfyUI rejected workflow: "
            + json.dumps(response, ensure_ascii=False)
        )
    prompt_id = str(response.get("prompt_id") or "").strip()
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return prompt_id")
    return prompt_id


def history_errors(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = entry.get("status") or {}
    for message in status.get("messages") or []:
        if not isinstance(message, (list, tuple)) or len(message) < 2:
            continue
        if str(message[0]).lower() in {
            "execution_error",
            "execution_interrupted",
        }:
            errors.append(json.dumps(message[1], ensure_ascii=False))
    return errors


def wait_for_history(
    base_url: str,
    prompt_id: str,
    profile: dict[str, Any],
    *,
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = http_json(
            f"{base_url}/history/{urllib.parse.quote(prompt_id)}",
            profile,
        )
        entry = history.get(prompt_id) if isinstance(history, dict) else None
        if isinstance(entry, dict):
            errors = history_errors(entry)
            if errors:
                raise RuntimeError(
                    f"ComfyUI prompt {prompt_id} failed: " + " | ".join(errors)
                )
            if bool((entry.get("status") or {}).get("completed")):
                return entry
        time.sleep(poll_interval)
    raise RuntimeError(f"Timed out waiting for ComfyUI prompt {prompt_id}")


def history_images(entry: dict[str, Any]) -> list[dict[str, str]]:
    images = (
        ((entry.get("outputs") or {}).get(SAVE_NODE_ID) or {}).get("images")
        or []
    )
    result = [
        {
            "filename": str(item.get("filename") or ""),
            "subfolder": str(item.get("subfolder") or ""),
            "type": str(item.get("type") or "output"),
        }
        for item in images
        if isinstance(item, dict) and item.get("filename")
    ]

    def order(item: dict[str, str]) -> tuple[int, str]:
        match = re.search(r"_(\d{5})_\.png$", item["filename"], re.IGNORECASE)
        return (int(match.group(1)) if match else sys.maxsize, item["filename"])

    return sorted(result, key=order)


def download_image(
    base_url: str,
    image: dict[str, str],
    destination: Path,
    profile: dict[str, Any],
) -> None:
    query = urllib.parse.urlencode(image)
    timeout = float(profile_section(profile, "http")["download_timeout_seconds"])
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        payload = http_bytes(
            f"{base_url}/view?{query}",
            profile,
            timeout=timeout,
        )
        temporary.write_bytes(payload)
        if temporary.stat().st_size < 24:
            raise RuntimeError(f"ComfyUI returned an empty image: {image}")
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def safe_remove_tree(path: Path, allowed_parent: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    parent = allowed_parent.resolve()
    if resolved.parent != parent:
        raise RuntimeError(f"Refusing unsafe recursive cleanup: {path}")
    shutil.rmtree(resolved)


def cleanup_comfy_chunk(path: Path, allowed_run_root: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    allowed = allowed_run_root.resolve()
    if allowed not in resolved.parents:
        raise RuntimeError(f"Refusing unsafe ComfyUI cleanup: {path}")
    shutil.rmtree(resolved)


@contextlib.contextmanager
def execution_lock(work_base: Path) -> Iterator[None]:
    work_base.mkdir(parents=True, exist_ok=True)
    lock_path = work_base / ".maestro_ultrasharp_review_v2.lock"
    handle = lock_path.open("a+b")
    try:
        handle.seek(0)
        if not handle.read(1):
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(
                "Another Maestro UltraSharp review process is running"
            ) from exc
        yield
    finally:
        handle.seek(0)
        with contextlib.suppress(OSError):
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


@contextlib.contextmanager
def cleanup_staging_files(*paths: Path) -> Iterator[None]:
    try:
        yield
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


def extract_source_frames(
    ffmpeg: str,
    source: Path,
    destination: Path,
    frames: int,
    dimensions: tuple[int, int],
    signature: dict[str, Any],
    *,
    force: bool,
    log_handle: Any,
) -> None:
    marker = destination.parent / ".source_frames.stage.json"
    if (
        not force
        and marker_matches(marker, signature)
        and sequence_range_valid(destination, 0, frames, dimensions)
    ):
        log(f"[resume] source frames: {frames}/{frames}")
        return
    destination.mkdir(parents=True, exist_ok=True)
    for frame in destination.glob("frame_*.png"):
        frame.unlink()
    marker.unlink(missing_ok=True)
    print(f"[1/4] extracting {frames} source frames one-to-one", flush=True)
    run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-an",
            "-sn",
            "-dn",
            "-start_number",
            "0",
            "-fps_mode",
            "passthrough",
            str(destination / "frame_%06d.png"),
        ],
        "Extract source frames",
        log_handle=log_handle,
    )
    validate_sequence_range(destination, 0, frames, dimensions)
    write_json_atomic(marker, signature)


def upscale_frames(
    frames_dir: Path,
    processed_dir: Path,
    work_root: Path,
    *,
    frames: int,
    neural_dimensions: tuple[int, int],
    downscale_ratio: float,
    fingerprint: str,
    settings: dict[str, Any],
    profile: dict[str, Any],
    force: bool,
) -> list[str]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = work_root / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    prompt_ids: list[str] = []
    client_id = str(uuid.uuid4())
    run_id = f"{fingerprint[:16].lower()}_{os.getpid()}"
    comfy_run_root = COMFY_OUTPUT_ROOT / "maestro_ultrasharp_v2" / run_id
    chunk_size = int(settings["chunk_size"])
    print(
        f"[2/4] preserving native cadence ({frames} frames; no interpolation)",
        flush=True,
    )
    model_name = str(profile_section(profile, "upscale").get("model") or "neural model")
    print(
        f"[3/4] reconstructing with ComfyUI {model_name} "
        "(75% neural + 25% Lanczos)",
        flush=True,
    )
    for start in range(0, frames, chunk_size):
        count = min(chunk_size, frames - start)
        chunk_name = f"chunk_{start:06d}"
        checkpoint = checkpoint_dir / f"{chunk_name}.json"
        signature = {
            "pipeline_version": PIPELINE_VERSION,
            "processing_fingerprint": fingerprint,
            "start": start,
            "count": count,
            "dimensions": list(neural_dimensions),
        }
        if (
            not force
            and marker_matches(checkpoint, signature)
            and sequence_range_valid(
                processed_dir,
                start,
                count,
                neural_dimensions,
            )
        ):
            log(f"[resume] {chunk_name}: {count} frames")
            continue
        clear_frame_range(processed_dir, start, count)
        checkpoint.unlink(missing_ok=True)
        # Recheck before every prompt; another producer may have acquired the GPU
        # after the initial preflight.
        assert_comfy_idle(str(settings["comfy_url"]), profile)
        prefix = f"maestro_ultrasharp_v2/{run_id}/{chunk_name}/frame"
        workflow = build_workflow(
            frames_dir,
            start_index=start,
            count=count,
            per_batch=int(settings["per_batch"]),
            downscale_ratio=downscale_ratio,
            filename_prefix=prefix,
            profile=profile,
        )
        prompt_id = submit_prompt(
            str(settings["comfy_url"]),
            workflow,
            client_id,
            profile,
        )
        prompt_ids.append(prompt_id)
        entry = wait_for_history(
            str(settings["comfy_url"]),
            prompt_id,
            profile,
            timeout=float(settings["prompt_timeout_seconds"]),
            poll_interval=float(settings["poll_interval_seconds"]),
        )
        images = history_images(entry)
        if len(images) != count:
            raise RuntimeError(
                f"{chunk_name}: ComfyUI returned {len(images)} images; "
                f"expected {count}"
            )
        for offset, image in enumerate(images):
            destination = processed_dir / f"frame_{start + offset:06d}.png"
            download_image(
                str(settings["comfy_url"]),
                image,
                destination,
                profile,
            )
            if png_dimensions(destination) != neural_dimensions:
                raise RuntimeError(
                    f"{destination.name}: unexpected neural-upscale dimensions"
                )
        validate_sequence_range(
            processed_dir,
            start,
            count,
            neural_dimensions,
        )
        write_json_atomic(checkpoint, signature)
        cleanup_comfy_chunk(comfy_run_root / chunk_name, comfy_run_root)
        log(f"collected {start + count}/{frames} neural-upscale frames")
    validate_sequence_range(processed_dir, 0, frames, neural_dimensions)
    if comfy_run_root.exists() and not any(comfy_run_root.iterdir()):
        comfy_run_root.rmdir()
    return prompt_ids


def blend_filter(
    source_dimensions: tuple[int, int],
    neural_dimensions: tuple[int, int],
    target_dimensions: tuple[int, int],
    profile: dict[str, Any],
) -> str:
    source_crop = center_crop(
        source_dimensions[0],
        source_dimensions[1],
        target_dimensions[0],
        target_dimensions[1],
    )
    neural_crop = center_crop(
        neural_dimensions[0],
        neural_dimensions[1],
        target_dimensions[0],
        target_dimensions[1],
    )
    upscale = profile_section(profile, "upscale")
    target_width, target_height = target_dimensions
    return (
        f"[0:v]crop={neural_crop[0]}:{neural_crop[1]}:"
        f"{neural_crop[2]}:{neural_crop[3]},"
        f"scale={target_width}:{target_height}:flags=lanczos,"
        "setpts=PTS-STARTPTS,format=gbrp[sharp];"
        f"[1:v]crop={source_crop[0]}:{source_crop[1]}:"
        f"{source_crop[2]}:{source_crop[3]},"
        f"scale={target_width}:{target_height}:flags=lanczos,"
        "setpts=PTS-STARTPTS,format=gbrp[base];"
        f"[base][sharp]blend=all_expr='A*"
        f"{float(upscale['source_lanczos_blend']):.8f}+B*"
        f"{float(upscale['neural_blend']):.8f}',"
        "setsar=1,"
        "setparams=range=limited:color_primaries=bt709:"
        "color_trc=bt709:colorspace=bt709,"
        "format=yuv420p[v]"
    )


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
    encode = profile_section(profile, "encode")
    fps_value = f"{fps.numerator}/{fps.denominator}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    print("[4/4] encoding H.264 CRF10 and stream-copying source audio", flush=True)
    run_command(
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
            blend_filter(
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
            str(encode["codec"]),
            "-preset",
            str(encode["preset"]),
            "-crf",
            str(encode["crf"]),
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
            "-movflags",
            str(encode["movflags"]),
            str(destination),
        ],
        "Encode transactional review candidate",
        log_handle=log_handle,
    )


def audio_packet_hashes(
    ffprobe: str,
    path: Path,
    stream_ordinal: int,
) -> list[str]:
    completed = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            f"a:{stream_ordinal}",
            "-show_packets",
            "-show_entries",
            "packet=data_hash",
            "-show_data_hash",
            "sha256",
            "-of",
            "json",
            str(path),
        ],
        f"Hash copied audio packets for {path.name} stream a:{stream_ordinal}",
        capture=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"ffprobe returned invalid audio packet JSON for {path}"
        ) from exc
    packets = payload.get("packets") if isinstance(payload, dict) else None
    if not isinstance(packets, list):
        return []
    hashes: list[str] = []
    for packet in packets:
        value = str(packet.get("data_hash") or "") if isinstance(packet, dict) else ""
        match = re.fullmatch(r"SHA256:([0-9a-fA-F]{64})", value)
        if not match:
            raise RuntimeError(
                f"Missing SHA256 packet hash in {path} stream a:{stream_ordinal}"
            )
        hashes.append(match.group(1).upper())
    return hashes


def validate_stream_copied_audio(
    ffprobe: str,
    source: Path,
    candidate: Path,
    source_audio: list[dict[str, Any]],
    candidate_audio: list[dict[str, Any]],
    *,
    target_duration: float,
) -> str | None:
    if not source_audio:
        return None
    retained_packet_fingerprint = hashlib.sha256()
    for stream_ordinal, (before, after) in enumerate(
        zip(source_audio, candidate_audio)
    ):
        source_hashes = audio_packet_hashes(ffprobe, source, stream_ordinal)
        candidate_hashes = audio_packet_hashes(ffprobe, candidate, stream_ordinal)
        if not candidate_hashes:
            raise RuntimeError(
                f"Candidate audio stream a:{stream_ordinal} contains no packets."
            )
        if (
            len(candidate_hashes) > len(source_hashes)
            or source_hashes[: len(candidate_hashes)] != candidate_hashes
        ):
            raise RuntimeError(
                "Audio packet payload changed despite stream-copy policy in "
                f"stream a:{stream_ordinal}."
            )

        source_duration = float(before.get("duration") or 0.0)
        candidate_duration = float(after.get("duration") or 0.0)
        expected_duration = min(source_duration, target_duration)
        sample_rate = int(after.get("sample_rate") or 0)
        packet_tolerance = max(0.05, 2048 / sample_rate) if sample_rate else 0.05
        if candidate_duration + packet_tolerance < expected_duration:
            raise RuntimeError(
                f"Candidate audio stream a:{stream_ordinal} ended early: "
                f"{candidate_duration:.6f}s < {expected_duration:.6f}s."
            )

        retained_packet_fingerprint.update(f"a:{stream_ordinal}\n".encode("ascii"))
        for packet_hash in candidate_hashes:
            retained_packet_fingerprint.update(packet_hash.encode("ascii"))
            retained_packet_fingerprint.update(b"\n")
    return retained_packet_fingerprint.hexdigest().upper()


def validate_candidate(
    ffprobe: str,
    ffmpeg: str,
    source: Path,
    candidate: Path,
    source_probe: dict[str, Any],
    *,
    fps: Fraction,
    frames: int,
    target_dimensions: tuple[int, int],
    full_decode: bool,
    log_handle: Any | None = None,
) -> tuple[dict[str, Any], str | None]:
    require_file(candidate, "Review candidate")
    probe = probe_media(ffprobe, candidate)
    video = video_stream(probe)
    problems: list[str] = []
    if str(video.get("codec_name") or "").lower() != "h264":
        problems.append(f"codec={video.get('codec_name')}")
    if (
        int(video.get("width") or 0),
        int(video.get("height") or 0),
    ) != target_dimensions:
        problems.append(
            f"dimensions={video.get('width')}x{video.get('height')}"
        )
    if parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate")) != fps:
        problems.append(f"fps={video.get('avg_frame_rate')}")
    if counted_frames(video) != frames:
        problems.append(f"frames={counted_frames(video)}")
    if str(video.get("pix_fmt") or "").lower() != "yuv420p":
        problems.append(f"pix_fmt={video.get('pix_fmt')}")
    if str(video.get("color_range") or "").lower() not in {"tv", "limited"}:
        problems.append(f"color_range={video.get('color_range')}")
    for field in ("color_space", "color_transfer", "color_primaries"):
        if str(video.get(field) or "").lower() != "bt709":
            problems.append(f"{field}={video.get(field)}")
    source_audio = audio_streams(source_probe)
    candidate_audio = audio_streams(probe)
    if len(source_audio) != len(candidate_audio):
        problems.append(
            f"audio_streams={len(candidate_audio)} expected={len(source_audio)}"
        )
    for index, (before, after) in enumerate(zip(source_audio, candidate_audio)):
        for field in (
            "codec_name",
            "sample_rate",
            "channels",
            "channel_layout",
        ):
            if str(before.get(field) or "") != str(after.get(field) or ""):
                problems.append(
                    f"audio[{index}].{field}={after.get(field)} "
                    f"expected={before.get(field)}"
                )
    if problems:
        raise RuntimeError("Candidate validation failed: " + "; ".join(problems))
    source_audio_hash = validate_stream_copied_audio(
        ffprobe,
        source,
        candidate,
        source_audio,
        candidate_audio,
        target_duration=frames / float(fps),
    )
    if full_decode:
        print("[verify] decoding the complete review candidate", flush=True)
        run_command(
            [
                ffmpeg,
                "-hide_banner",
                "-v",
                "error",
                "-xerror",
                "-i",
                str(candidate),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-f",
                "null",
                os.devnull,
            ],
            "Full candidate decode",
            log_handle=log_handle,
        )
    return probe, source_audio_hash


def sidecar_rejected(sidecar: dict[str, Any]) -> bool:
    statuses = [
        sidecar.get("validation_status"),
        sidecar.get("qc_status"),
        sidecar.get("human_review_status"),
        sidecar.get("approval_status"),
        (sidecar.get("human_approval") or {}).get("status")
        if isinstance(sidecar.get("human_approval"), dict)
        else None,
    ]
    return (
        any("reject" in str(value or "").lower() for value in statuses)
        or bool(sidecar.get("rejected_at"))
        or bool(sidecar.get("rejection"))
    )


def sidecar_technically_reusable(
    sidecar: dict[str, Any],
    fingerprint: str,
) -> bool:
    technical = sidecar.get("technical_validation")
    technical_status = (
        str(technical.get("status") or "").lower()
        if isinstance(technical, dict)
        else ""
    )
    return (
        str(sidecar.get("schema_version") or "") == SIDECAR_SCHEMA_VERSION
        and str(sidecar.get("processing_fingerprint") or "").upper()
        == fingerprint
        and technical_status == TECHNICAL_PASS
        and str(sidecar.get("validation_status") or "").startswith(
            TECHNICAL_PASS
        )
        and str(sidecar.get("qc_status") or "").startswith(TECHNICAL_PASS)
        and not sidecar_rejected(sidecar)
    )


def find_reusable_candidate(
    output_dir: Path,
    stem_prefix: str,
    fingerprint: str,
    ffprobe: str,
    ffmpeg: str,
    source: Path,
    source_probe: dict[str, Any],
    *,
    fps: Fraction,
    frames: int,
    target_dimensions: tuple[int, int],
) -> tuple[Path, Path] | None:
    if not output_dir.is_dir():
        return None
    for sidecar_path in sorted(
        output_dir.glob(f"{stem_prefix}*.json"),
        key=lambda item: item.stat().st_mtime_ns,
        reverse=True,
    ):
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            if not sidecar_technically_reusable(sidecar, fingerprint):
                continue
            candidate = Path(str(sidecar.get("candidate") or "")).resolve()
            if candidate.parent != output_dir.resolve() or not candidate.is_file():
                continue
            if str(sidecar.get("candidate_sha256") or "").upper() != sha256(
                candidate
            ):
                continue
            validate_candidate(
                ffprobe,
                ffmpeg,
                source,
                candidate,
                source_probe,
                fps=fps,
                frames=frames,
                target_dimensions=target_dimensions,
                full_decode=False,
            )
            return candidate, sidecar_path.resolve()
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            continue
    return None


def choose_publication_paths(
    output_dir: Path,
    base_stem: str,
) -> tuple[Path, Path, Path]:
    for attempt in range(1, 1000):
        suffix = "" if attempt == 1 else f"_attempt{attempt:02d}"
        candidate = output_dir / f"{base_stem}{suffix}.mp4"
        sidecar = candidate.with_suffix(".json")
        log_path = candidate.with_suffix(".log")
        if not candidate.exists() and not sidecar.exists():
            return candidate, sidecar, log_path
    raise RuntimeError("No free review-candidate attempt name is available")


def emit_done(
    candidate: Path,
    sidecar: Path,
    fingerprint: str,
    *,
    reused: bool,
) -> None:
    print(f"[done] REVIEW_CANDIDATE={candidate.resolve()}", flush=True)
    print(f"[done] SIDECAR={sidecar.resolve()}", flush=True)
    print(f"[done] PROCESSING_FINGERPRINT={fingerprint}", flush=True)
    print(f"[done] REUSED={str(reused).lower()}", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.input.resolve()
    output_dir = args.output_dir.resolve()
    work_base = args.work_dir.resolve()
    profile_path = args.profile.resolve()
    require_file(source, "Source take")
    ffmpeg = resolve_program("ffmpeg")
    ffprobe = resolve_program("ffprobe")
    profile = load_profile(profile_path)
    settings = effective_settings(args, profile)
    _model_path, model_descriptor = resolve_model(profile)
    source_probe = probe_media(ffprobe, source)
    source_video, source_fps, source_frames, source_width, source_height = (
        validate_source_probe(source_probe)
    )
    source_hash = sha256(source)
    expected_hash = str(args.expected_sha256 or "").strip().upper()
    if expected_hash and source_hash != expected_hash:
        raise RuntimeError(
            f"Source hash mismatch: {source_hash} != {expected_hash}"
        )
    target = profile_section(profile, "target")
    target_dimensions = (int(target["width"]), int(target["height"]))
    upscale = profile_section(profile, "upscale")
    downscale_ratio, neural_dimensions = neural_ratio(
        source_width,
        source_height,
        target_dimensions[0],
        target_dimensions[1],
        int(upscale["model_scale"]),
    )
    source_descriptor = {
        "path": source.as_posix(),
        "sha256": source_hash,
        "size": source.stat().st_size,
        "probe": source_probe,
    }
    processing_inputs = {
        "pipeline_version": PIPELINE_VERSION,
        "source": source_descriptor,
        "source_sha256": source_hash,
        "source_probe": source_probe,
        "profile": profile,
        "model": model_descriptor,
        "effective_processing": {
            "target_dimensions": list(target_dimensions),
            "source_dimensions": [source_width, source_height],
            "source_fps": (
                f"{source_fps.numerator}/{source_fps.denominator}"
            ),
            "source_frames": source_frames,
            "downscale_ratio": downscale_ratio,
            "neural_dimensions": list(neural_dimensions),
            "downscale_method": upscale["downscale_method"],
            "precision": upscale["precision"],
            "chunk_size": settings["chunk_size"],
            "per_batch": settings["per_batch"],
        },
    }
    fingerprint = json_fingerprint(processing_inputs)
    raw_name = safe_stem(args.name or source.stem)
    base_stem = (
        f"{raw_name}_review_candidate_{target_dimensions[0]}x"
        f"{target_dimensions[1]}_{fps_tag(source_fps)}fps_"
        f"{fingerprint[:12].lower()}"
    )
    requirements = disk_requirements(
        source_width,
        source_height,
        neural_dimensions[0],
        neural_dimensions[1],
        source_frames,
        int(settings["chunk_size"]),
        profile,
    )
    plan = {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "type": "pemara_hd_review_candidate_plan",
        "pipeline_version": PIPELINE_VERSION,
        "delivery_class": "review_candidate_not_master",
        "profile_path": profile_path.as_posix(),
        "profile": profile,
        "source": source_descriptor,
        "source_sha256": source_hash,
        "source_probe": source_probe,
        "model": model_descriptor,
        "processing_fingerprint": fingerprint,
        "fingerprint": {
            "algorithm": "SHA-256",
            "value": fingerprint,
            "inputs": processing_inputs,
        },
        "processing": {
            **processing_inputs["effective_processing"],
            "cadence_policy": "preserve_native_fps_and_frame_count",
            "audio_policy": "stream_copy_all",
            "blend": {
                "neural": upscale["neural_blend"],
                "source_lanczos": upscale["source_lanczos_blend"],
            },
            "encode": profile["encode"],
        },
        "candidate_stem": base_stem,
        "output_dir": output_dir.as_posix(),
        "work_dir": work_base.as_posix(),
        "disk_required_bytes": requirements,
        "validation_status": "plan_only",
        "qc_status": "plan_only",
        "human_review_status": "pending",
        "human_approval": {
            "status": "pending",
            "claimed_by_postprocessor": False,
        },
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    print(f"[plan] PROCESSING_FINGERPRINT={fingerprint}", flush=True)
    print(f"[plan] REQUIRED_WORK_BYTES={requirements['work']}", flush=True)

    reusable = None if args.force else find_reusable_candidate(
        output_dir,
        base_stem,
        fingerprint,
        ffprobe,
        ffmpeg,
        source,
        source_probe,
        fps=source_fps,
        frames=source_frames,
        target_dimensions=target_dimensions,
    )
    if reusable is not None:
        candidate, sidecar = reusable
        if args.dry_run:
            print("[dry-run] REUSABLE=true", flush=True)
        emit_done(candidate, sidecar, fingerprint, reused=True)
        return 0

    disk_report = check_disk_space(
        work_base,
        output_dir,
        requirements,
    )
    preflight_comfy(str(settings["comfy_url"]), profile)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": "strong_preflight_pass",
                    "disk": disk_report,
                    "comfy_url": settings["comfy_url"],
                    "gpu_prompt_submitted": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        print(
            "[dry-run] validation passed; no directories, frames, prompts "
            "or videos were written.",
            flush=True,
        )
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    work_base.mkdir(parents=True, exist_ok=True)
    candidate, sidecar, log_path = choose_publication_paths(
        output_dir,
        base_stem,
    )
    work_root = work_base / base_stem
    if args.force:
        safe_remove_tree(work_root, work_base)
    frames_dir = work_root / "01_source_frames"
    processed_dir = work_root / "02_ultrasharp_frames"
    staging_dir = output_dir / ".ultrasharp_staging"
    staging_candidate = staging_dir / f"{candidate.stem}.{uuid.uuid4().hex}.mp4"
    staging_sidecar = staging_candidate.with_suffix(".json")
    prompt_ids: list[str] = []

    with execution_lock(work_base), cleanup_staging_files(
        staging_candidate,
        staging_sidecar,
    ):
        work_root.mkdir(parents=True, exist_ok=True)
        staging_dir.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", buffering=1) as log_handle:
            log_handle.write(
                f"\n=== Maestro UltraSharp v2 "
                f"{datetime.now().astimezone().isoformat()} ===\n"
            )
            log_handle.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
            source_stage_signature = {
                "pipeline_version": PIPELINE_VERSION,
                "processing_fingerprint": fingerprint,
                "source_sha256": source_hash,
                "frames": source_frames,
                "dimensions": [source_width, source_height],
            }
            extract_source_frames(
                ffmpeg,
                source,
                frames_dir,
                source_frames,
                (source_width, source_height),
                source_stage_signature,
                force=bool(args.force),
                log_handle=log_handle,
            )
            prompt_ids = upscale_frames(
                frames_dir,
                processed_dir,
                work_root,
                frames=source_frames,
                neural_dimensions=neural_dimensions,
                downscale_ratio=downscale_ratio,
                fingerprint=fingerprint,
                settings=settings,
                profile=profile,
                force=bool(args.force),
            )
            staging_candidate.unlink(missing_ok=True)
            encode_candidate(
                ffmpeg,
                source,
                processed_dir,
                staging_candidate,
                fps=source_fps,
                frames=source_frames,
                source_dimensions=(source_width, source_height),
                neural_dimensions=neural_dimensions,
                target_dimensions=target_dimensions,
                profile=profile,
                log_handle=log_handle,
            )
            candidate_probe, audio_hash = validate_candidate(
                ffprobe,
                ffmpeg,
                source,
                staging_candidate,
                source_probe,
                fps=source_fps,
                frames=source_frames,
                target_dimensions=target_dimensions,
                full_decode=True,
                log_handle=log_handle,
            )
            completed_at = datetime.now().astimezone().isoformat()
            report = {
                **plan,
                "type": "pemara_hd_review_candidate_result",
                "candidate": candidate.as_posix(),
                "sidecar": sidecar.as_posix(),
                "candidate_sha256": sha256(staging_candidate),
                "candidate_probe": candidate_probe,
                "source_audio_packet_sha256": audio_hash,
                "candidate_audio_packet_sha256": audio_hash,
                "comfy_prompt_ids": prompt_ids,
                "completed_at": completed_at,
                "validation_status": TECHNICAL_PENDING,
                "qc_status": TECHNICAL_PENDING,
                "technical_validation": {
                    "status": TECHNICAL_PASS,
                    "completed_at": completed_at,
                    "full_decode": "pass",
                    "frame_count": "pass",
                    "fps": "pass",
                    "geometry": "pass",
                    "codec_color": "pass",
                    "audio_stream_copy": "pass",
                },
                "human_review_status": "pending",
                "human_approval": {
                    "status": "pending",
                    "claimed_by_postprocessor": False,
                },
                "next_gate": (
                    "Human visual review is required before approval, active "
                    "output selection or runtime integration."
                ),
            }
            write_json_atomic(staging_sidecar, report)
            os.replace(staging_candidate, candidate)
            os.replace(staging_sidecar, sidecar)

    emit_done(candidate, sidecar, fingerprint, reused=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
