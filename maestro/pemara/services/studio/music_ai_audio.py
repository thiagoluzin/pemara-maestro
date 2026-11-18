"""Deterministic audio validation and mastering helpers for AI music candidates."""

from __future__ import annotations

import hashlib
import json
import math
import mimetypes
import os
import re
import subprocess
from pathlib import Path
from typing import Any


class MusicAiAudioError(RuntimeError):
    """Raised when an audio artifact fails validation or decoding."""


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for one regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_audio(path: Path, ffprobe: str) -> dict[str, Any]:
    """Probe an audio file and reject missing, silent-length, or video-only input."""
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels:format=duration,format_name",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise MusicAiAudioError("O arquivo enviado nao contem audio decodificavel.")
    try:
        payload = json.loads(completed.stdout)
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MusicAiAudioError("Nao foi possivel identificar o audio enviado.") from exc
    if not 10.0 <= duration <= 600.0:
        raise MusicAiAudioError("A musica deve ter entre 10 segundos e 10 minutos.")
    return {
        "durationSeconds": round(duration, 3),
        "codec": str(stream.get("codec_name") or ""),
        "sampleRate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "format": str(payload.get("format", {}).get("format_name") or ""),
    }


def sample_metrics(path: Path) -> dict[str, Any]:
    """Measure sample peak, clipping, duration, sample rate, and channel count."""
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise MusicAiAudioError("Dependencias locais de QC estao ausentes.") from exc
    peak = 0.0
    clipping = 0
    non_finite = 0
    frames = 0
    with sf.SoundFile(str(path)) as handle:
        sample_rate = int(handle.samplerate)
        channels = int(handle.channels)
        subtype = str(handle.subtype or "")
        for block in handle.blocks(blocksize=262144, dtype="float32", always_2d=True):
            absolute = np.abs(block)
            non_finite += int(np.count_nonzero(~np.isfinite(block)))
            if absolute.size:
                peak = max(peak, float(np.max(absolute)))
                clipping += int(np.count_nonzero(absolute >= 0.999999))
            frames += int(block.shape[0])
    peak_dbfs = 20.0 * math.log10(peak) if peak > 0 else None
    return {
        "sampleRate": sample_rate,
        "channels": channels,
        "subtype": subtype,
        "durationSeconds": round(frames / sample_rate, 3) if sample_rate else 0.0,
        "samplePeakDbfs": round(peak_dbfs, 3) if peak_dbfs is not None else None,
        "clippingSampleCount": clipping,
        "nonFiniteSampleCount": non_finite,
    }


def loudness_metrics(path: Path, ffmpeg: str) -> dict[str, float | None]:
    """Measure integrated loudness and true peak through FFmpeg ebur128."""
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "NUL" if os.name == "nt" else "/dev/null"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = (completed.stderr or "") + "\n" + (completed.stdout or "")
    if completed.returncode != 0:
        raise MusicAiAudioError("A medicao de loudness/true peak falhou; o candidato foi preservado.")
    integrated = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", output)
    true_peak = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", output)
    return {
        "integratedLufs": round(float(integrated[-1]), 2) if integrated else None,
        "truePeakDbfs": round(float(true_peak[-1]), 2) if true_peak else None,
    }


def gain_for_headroom(path: Path, target_dbfs: float = -1.0, *, ffmpeg: str | None = None) -> float:
    """Return bounded gain-only adjustment toward the target sample peak."""
    peak = sample_metrics(path).get("samplePeakDbfs")
    if peak is None:
        raise MusicAiAudioError("O candidato gerado esta silencioso.")
    if ffmpeg:
        true_peak = loudness_metrics(path, ffmpeg).get("truePeakDbfs")
        if true_peak is None or not math.isfinite(float(true_peak)):
            raise MusicAiAudioError("True peak indisponivel; a masterizacao foi bloqueada.")
        peak = max(float(peak), float(true_peak))
    return round(max(-24.0, min(12.0, float(target_dbfs) - float(peak))), 4)


def qc_report(path: Path, ffmpeg: str, expected_duration: float, *, expected_sample_rate: int = 48000) -> dict[str, Any]:
    """Run full decode and objective QC without claiming a listening decision."""
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "NUL" if os.name == "nt" else "/dev/null"],
        capture_output=True,
        text=True,
        timeout=max(300, int(expected_duration * 3)),
    )
    if completed.returncode != 0:
        raise MusicAiAudioError("O candidato falhou no decode completo.")
    metrics = {**sample_metrics(path), **loudness_metrics(path, ffmpeg)}
    metrics["fullDecodePassed"] = True
    metrics["durationMatchesSource"] = abs(float(metrics["durationSeconds"]) - expected_duration) <= 0.3
    integrated = metrics.get("integratedLufs")
    metrics["loudnessInReviewRange"] = bool(
        integrated is not None and math.isfinite(float(integrated)) and -24.0 <= float(integrated) <= -8.0
    )
    peak = metrics.get("samplePeakDbfs")
    true_peak = metrics.get("truePeakDbfs")
    metrics["truePeakPass"] = bool(
        true_peak is not None and math.isfinite(float(true_peak)) and float(true_peak) <= -1.0
    )
    metrics["technicalPass"] = bool(
        metrics["durationMatchesSource"]
        and int(metrics["sampleRate"]) == expected_sample_rate
        and int(metrics["channels"]) == 2
        and int(metrics["clippingSampleCount"]) == 0
        and int(metrics.get("nonFiniteSampleCount", 0)) == 0
        and peak is not None and math.isfinite(float(peak)) and float(peak) <= -0.75
        and metrics["truePeakPass"]
        and integrated is not None and math.isfinite(float(integrated))
    )
    return metrics


def artifact(job_dir: Path, key: str, path: Path, media_type: str | None = None) -> dict[str, Any]:
    """Describe one confined artifact for authenticated download."""
    root = job_dir.resolve()
    resolved = path.resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise MusicAiAudioError("Artefato saiu do diretorio permitido do job.")
    return {
        "key": key,
        "filename": resolved.name,
        "relativePath": resolved.relative_to(root).as_posix(),
        "mediaType": media_type or mimetypes.guess_type(resolved.name)[0] or "application/octet-stream",
        "sizeBytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }
