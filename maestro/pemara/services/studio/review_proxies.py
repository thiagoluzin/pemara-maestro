"""CPU-only review proxies for responsive Maestro video playback.

The canonical project video is never modified.  A proxy is valid only while
its source path, size and nanosecond mtime still match the sidecar written at
build time.  Replacing a master therefore invalidates the proxy immediately
without mutating the project's approval state or take queue.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REVIEW_PROXY_PROFILE = "maestro_mobile_review_720p_v1"
REVIEW_PROXY_MAX_WIDTH = 1280
REVIEW_PROXY_MAX_HEIGHT = 720
REVIEW_PROXY_MAX_FPS = 30.0
REVIEW_PROXY_CRF = 23
REVIEW_PROXY_MAX_RATE = "2500k"
REVIEW_PROXY_BUFFER_SIZE = "5000k"
REVIEW_PROXY_AUDIO_RATE = "96k"
REVIEW_PROXY_DIR = Path("qc") / "review_proxies"
REVIEW_PROXY_SETTINGS = {
    "max_width": REVIEW_PROXY_MAX_WIDTH,
    "max_height": REVIEW_PROXY_MAX_HEIGHT,
    "max_fps": REVIEW_PROXY_MAX_FPS,
    "scale_flags": "lanczos",
    "video_codec": "libx264",
    "video_preset": "veryfast",
    "video_crf": REVIEW_PROXY_CRF,
    "video_max_rate": REVIEW_PROXY_MAX_RATE,
    "video_buffer_size": REVIEW_PROXY_BUFFER_SIZE,
    "video_profile": "main",
    "video_level": "3.1",
    "pixel_format": "yuv420p",
    "video_tag": "avc1",
    "video_tune": "fastdecode",
    "gop_seconds": 2,
    "minimum_gop_seconds": 1,
    "scene_cut": False,
    "audio_codec": "aac",
    "audio_profile": "aac_low",
    "audio_rate": REVIEW_PROXY_AUDIO_RATE,
    "audio_sample_rate": 48000,
    "audio_channels": 2,
    "silent_audio_when_missing": True,
    "faststart": True,
}
_SAFE_TAKE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")


class ReviewProxyError(RuntimeError):
    """Raised when a review proxy cannot be built or validated."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _validate_take_id(take_id: str) -> str:
    take_id = str(take_id or "").strip()
    if not _SAFE_TAKE_ID.fullmatch(take_id):
        raise ValueError("takeId invalido para proxy de revisao.")
    return take_id


def _validated_source(project_dir: Path, source_path: Path) -> tuple[Path, str, os.stat_result]:
    project_dir = Path(project_dir).resolve()
    source_path = Path(source_path).resolve()
    if not source_path.is_relative_to(project_dir):
        raise ValueError("Master de revisao fora do projeto.")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise ValueError("Formato de master nao suportado para proxy de revisao.")
    relative = source_path.relative_to(project_dir).as_posix()
    return source_path, relative, source_path.stat()


def _source_identity(
    project_dir: Path,
    take_id: str,
    source_path: Path,
) -> dict[str, Any]:
    take_id = _validate_take_id(take_id)
    source_path, relative, stat = _validated_source(project_dir, source_path)
    identity = {
        "profile": REVIEW_PROXY_PROFILE,
        "profile_settings": REVIEW_PROXY_SETTINGS,
        "take_id": take_id,
        "source_path": relative,
        "source_size": int(stat.st_size),
        "source_mtime_ns": int(stat.st_mtime_ns),
    }
    token_source = json.dumps(
        identity,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    identity["version"] = hashlib.sha256(token_source).hexdigest()[:16]
    identity["source"] = source_path
    return identity


def review_proxy_paths(
    project_dir: Path,
    take_id: str,
    source_path: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    """Return deterministic proxy/sidecar paths for the current master version."""

    project_dir = Path(project_dir).resolve()
    identity = _source_identity(project_dir, take_id, source_path)
    proxy_root = (project_dir / REVIEW_PROXY_DIR).resolve()
    if not proxy_root.is_relative_to(project_dir):
        raise ValueError("Diretorio de proxies fora do projeto.")
    safe_take = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(take_id))
    stem = f"take_{safe_take}_review_720p_{identity['version']}"
    proxy = (proxy_root / f"{stem}.mp4").resolve()
    sidecar = (proxy_root / f"{stem}.json").resolve()
    if not proxy.is_relative_to(proxy_root) or not sidecar.is_relative_to(proxy_root):
        raise ValueError("Caminho de proxy invalido.")
    return proxy, sidecar, identity


def _sidecar_matches(
    sidecar: dict[str, Any],
    proxy: Path,
    identity: dict[str, Any],
) -> bool:
    source = sidecar.get("source") if isinstance(sidecar.get("source"), dict) else {}
    output = sidecar.get("proxy") if isinstance(sidecar.get("proxy"), dict) else {}
    validation = (
        sidecar.get("validation")
        if isinstance(sidecar.get("validation"), dict)
        else {}
    )
    return bool(
        sidecar.get("schema_version") == "1.0"
        and sidecar.get("profile") == REVIEW_PROXY_PROFILE
        and sidecar.get("profile_settings") == REVIEW_PROXY_SETTINGS
        and sidecar.get("take_id") == identity["take_id"]
        and sidecar.get("version") == identity["version"]
        and source.get("path") == identity["source_path"]
        and int(source.get("size_bytes") or -1) == identity["source_size"]
        and int(source.get("mtime_ns") or -1) == identity["source_mtime_ns"]
        and output.get("file") == proxy.name
        and validation.get("status") == "passed"
    )


def resolve_review_proxy(
    project_dir: Path,
    take_id: str,
    source_path: Path,
) -> Path | None:
    """Return a validated, current review proxy or ``None`` for master fallback."""

    proxy, sidecar_path, identity = review_proxy_paths(
        project_dir,
        take_id,
        source_path,
    )
    if not proxy.is_file() or proxy.stat().st_size <= 0:
        return None
    sidecar = _read_json(sidecar_path)
    if not _sidecar_matches(sidecar, proxy, identity):
        return None
    output = sidecar.get("proxy") if isinstance(sidecar.get("proxy"), dict) else {}
    if int(output.get("size_bytes") or -1) != proxy.stat().st_size:
        return None
    return proxy


def review_proxy_info(
    project_dir: Path,
    take_id: str,
    source_path: Path,
) -> dict[str, Any] | None:
    proxy, sidecar_path, identity = review_proxy_paths(
        project_dir,
        take_id,
        source_path,
    )
    if not proxy.is_file() or proxy.stat().st_size <= 0:
        return None
    sidecar = _read_json(sidecar_path)
    if not _sidecar_matches(sidecar, proxy, identity):
        return None
    output = sidecar.get("proxy") if isinstance(sidecar.get("proxy"), dict) else {}
    if int(output.get("size_bytes") or -1) != proxy.stat().st_size:
        return None
    return {
        "path": proxy,
        "file": proxy.name,
        "version": identity["version"],
        "sizeBytes": proxy.stat().st_size,
        "durationSeconds": float(output.get("duration_seconds") or 0),
        "width": int(output.get("width") or 0),
        "height": int(output.get("height") or 0),
        "fps": float(output.get("fps") or 0),
        "profile": REVIEW_PROXY_PROFILE,
        "sidecar": sidecar,
    }


def is_review_proxy_path(project_dir: Path, candidate: Path) -> bool:
    project_dir = Path(project_dir).resolve()
    proxy_root = (project_dir / REVIEW_PROXY_DIR).resolve()
    candidate = Path(candidate).resolve()
    return candidate.is_file() and candidate.is_relative_to(proxy_root)


def _executable(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise ReviewProxyError(f"Executavel nao encontrado: {command}")
    return resolved


def _probe(path: Path, ffprobe: str) -> dict[str, Any]:
    command = [
        _executable(ffprobe),
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise ReviewProxyError(
            f"ffprobe falhou para {path.name}: {completed.stderr.strip()[-1000:]}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ReviewProxyError(f"ffprobe retornou JSON invalido para {path.name}.") from exc
    if not isinstance(payload, dict):
        raise ReviewProxyError(f"ffprobe nao descreveu {path.name}.")
    return payload


def _rate(value: Any) -> float:
    raw = str(value or "0/1")
    try:
        numerator, denominator = raw.split("/", 1)
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0


def _probe_summary(payload: dict[str, Any]) -> dict[str, Any]:
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    video = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"),
        None,
    )
    audio = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"),
        None,
    )
    if not isinstance(video, dict):
        raise ReviewProxyError("Arquivo de origem nao possui stream de video.")
    file_format = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration = float(file_format.get("duration") or video.get("duration") or 0)
    fps = _rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    return {
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "duration": duration,
        "video_codec": str(video.get("codec_name") or ""),
        "video_profile": str(video.get("profile") or ""),
        "video_level": int(video.get("level") or 0),
        "pixel_format": str(video.get("pix_fmt") or ""),
        "audio_codec": str((audio or {}).get("codec_name") or ""),
        "has_audio": audio is not None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _target_dimensions(width: int, height: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ReviewProxyError("Dimensoes invalidas no master.")
    factor = min(
        1.0,
        REVIEW_PROXY_MAX_WIDTH / width,
        REVIEW_PROXY_MAX_HEIGHT / height,
    )
    target_width = max(2, int(width * factor) // 2 * 2)
    target_height = max(2, int(height * factor) // 2 * 2)
    return target_width, target_height


def _faststart_ok(path: Path) -> bool:
    with path.open("rb") as handle:
        prefix = handle.read(min(path.stat().st_size, 2 * 1024 * 1024))
    moov = prefix.find(b"moov")
    mdat = prefix.find(b"mdat")
    return moov >= 0 and (mdat < 0 or moov < mdat)


def _validate_proxy(
    source: dict[str, Any],
    proxy: dict[str, Any],
    proxy_path: Path,
) -> list[str]:
    errors: list[str] = []
    if proxy["video_codec"] != "h264":
        errors.append(f"codec de video {proxy['video_codec']!r}, esperado h264")
    if proxy["pixel_format"] != "yuv420p":
        errors.append(f"pixel format {proxy['pixel_format']!r}, esperado yuv420p")
    if proxy["width"] > REVIEW_PROXY_MAX_WIDTH or proxy["height"] > REVIEW_PROXY_MAX_HEIGHT:
        errors.append(
            f"resolucao {proxy['width']}x{proxy['height']} excede "
            f"{REVIEW_PROXY_MAX_WIDTH}x{REVIEW_PROXY_MAX_HEIGHT}"
        )
    if proxy["fps"] > REVIEW_PROXY_MAX_FPS + 0.05:
        errors.append(f"fps {proxy['fps']:.3f} excede {REVIEW_PROXY_MAX_FPS:.0f}")
    duration_tolerance = max(0.25, 2.0 / max(source["fps"], 1.0))
    if abs(proxy["duration"] - source["duration"]) > duration_tolerance:
        errors.append(
            f"duracao mudou de {source['duration']:.3f}s para "
            f"{proxy['duration']:.3f}s"
        )
    if proxy["audio_codec"] != "aac":
        errors.append(f"audio {proxy['audio_codec']!r}, esperado AAC-LC")
    if not _faststart_ok(proxy_path):
        errors.append("atom moov nao esta antes do mdat (faststart ausente)")
    return errors


def build_review_proxy(
    project_dir: Path,
    take_id: str,
    source_path: Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    force: bool = False,
) -> dict[str, Any]:
    """Build one validated CPU/libx264 proxy without touching the master."""

    project_dir = Path(project_dir).resolve()
    proxy, sidecar_path, identity = review_proxy_paths(
        project_dir,
        take_id,
        source_path,
    )
    existing = resolve_review_proxy(project_dir, take_id, source_path)
    if existing is not None and not force:
        sidecar = _read_json(sidecar_path)
        return {
            "takeId": take_id,
            "source": str(identity["source"]),
            "proxy": str(existing),
            "sidecar": str(sidecar_path),
            "version": identity["version"],
            "sourceBytes": identity["source_size"],
            "proxyBytes": existing.stat().st_size,
            "durationSeconds": float(
                ((sidecar.get("proxy") or {}).get("duration_seconds") or 0)
            ),
            "skipped": True,
        }

    source_path = Path(identity["source"])
    source_probe = _probe_summary(_probe(source_path, ffprobe))
    target_width, target_height = _target_dimensions(
        source_probe["width"],
        source_probe["height"],
    )
    target_fps = min(
        source_probe["fps"] or REVIEW_PROXY_MAX_FPS,
        REVIEW_PROXY_MAX_FPS,
    )
    filters = [
        f"scale={target_width}:{target_height}:flags=lanczos",
    ]
    if source_probe["fps"] > REVIEW_PROXY_MAX_FPS + 0.05:
        filters.append(f"fps={REVIEW_PROXY_MAX_FPS:g}")
    filters.append("format=yuv420p")

    proxy.parent.mkdir(parents=True, exist_ok=True)
    temp_proxy = proxy.parent / f".{proxy.stem}.tmp.{uuid.uuid4().hex}.mp4"
    keyframe_interval = max(12, round(target_fps * 2))
    minimum_keyframe_interval = max(6, round(target_fps))
    command = [
        _executable(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
    ]
    if not source_probe["has_audio"]:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
            ]
        )
    command.extend(
        [
        "-map",
        "0:v:0",
        "-map",
        "0:a:0" if source_probe["has_audio"] else "1:a:0",
        "-sn",
        "-dn",
        "-vf",
        ",".join(filters),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(REVIEW_PROXY_CRF),
        "-maxrate",
        REVIEW_PROXY_MAX_RATE,
        "-bufsize",
        REVIEW_PROXY_BUFFER_SIZE,
        "-profile:v",
        "main",
        "-level:v",
        "3.1",
        "-pix_fmt",
        "yuv420p",
        "-tag:v",
        "avc1",
        "-tune",
        "fastdecode",
        "-g",
        str(keyframe_interval),
        "-keyint_min",
        str(minimum_keyframe_interval),
        "-sc_threshold",
        "0",
        "-force_key_frames",
        "expr:gte(t,n_forced*2)",
        "-c:a",
        "aac",
        "-b:a",
        REVIEW_PROXY_AUDIO_RATE,
        "-ac",
        "2",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-map_metadata",
        "-1",
        "-avoid_negative_ts",
        "make_zero",
        ]
    )
    if not source_probe["has_audio"]:
        command.append("-shortest")
    command.append(str(temp_proxy))
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=max(300, int(source_probe["duration"] * 30) + 120),
        )
        if completed.returncode != 0:
            raise ReviewProxyError(
                f"ffmpeg falhou para {take_id}: {completed.stderr.strip()[-2000:]}"
            )
        if not temp_proxy.is_file() or temp_proxy.stat().st_size <= 0:
            raise ReviewProxyError(f"ffmpeg nao criou proxy para {take_id}.")
        proxy_probe = _probe_summary(_probe(temp_proxy, ffprobe))
        validation_errors = _validate_proxy(
            source_probe,
            proxy_probe,
            temp_proxy,
        )
        if validation_errors:
            raise ReviewProxyError(
                f"Proxy {take_id} invalido: {'; '.join(validation_errors)}"
            )
        proxy_sha256 = _sha256(temp_proxy)
        source_sha256 = _sha256(source_path)
        os.replace(temp_proxy, proxy)
    finally:
        try:
            temp_proxy.unlink()
        except FileNotFoundError:
            pass

    sidecar = {
        "schema_version": "1.0",
        "profile": REVIEW_PROXY_PROFILE,
        "profile_settings": REVIEW_PROXY_SETTINGS,
        "take_id": take_id,
        "version": identity["version"],
        "created_at": _utc_now(),
        "source": {
            "path": identity["source_path"],
            "size_bytes": identity["source_size"],
            "mtime_ns": identity["source_mtime_ns"],
            "sha256": source_sha256,
            "duration_seconds": source_probe["duration"],
            "width": source_probe["width"],
            "height": source_probe["height"],
            "fps": source_probe["fps"],
            "video_codec": source_probe["video_codec"],
            "audio_codec": source_probe["audio_codec"],
        },
        "proxy": {
            "file": proxy.name,
            "size_bytes": proxy.stat().st_size,
            "sha256": proxy_sha256,
            "duration_seconds": proxy_probe["duration"],
            "width": proxy_probe["width"],
            "height": proxy_probe["height"],
            "fps": proxy_probe["fps"],
            "video_codec": proxy_probe["video_codec"],
            "video_profile": proxy_probe["video_profile"],
            "video_level": proxy_probe["video_level"],
            "pixel_format": proxy_probe["pixel_format"],
            "audio_codec": proxy_probe["audio_codec"],
            "faststart": True,
        },
        "validation": {
            "status": "passed",
            "master_preserved": True,
            "approval_state_unchanged": True,
            "gpu_used": False,
        },
    }
    _atomic_json_write(sidecar_path, sidecar)
    return {
        "takeId": take_id,
        "source": str(source_path),
        "proxy": str(proxy),
        "sidecar": str(sidecar_path),
        "version": identity["version"],
        "sourceBytes": identity["source_size"],
        "proxyBytes": proxy.stat().st_size,
        "durationSeconds": proxy_probe["duration"],
        "skipped": False,
    }
