"""Fail-closed hard-cut assembly for owner-approved Studio takes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable
import dlss5_finishing as _dlss5
from sequence_camera_contract import load_and_validate as _validate_camera_sequence
import upscaling_required as _required_upscale


class AssemblyError(RuntimeError):
    pass


def _run(command: list[str], *, error: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        raise AssemblyError(f"{error}: {detail or 'processo sem detalhe'}")
    return completed


def _require_h264_nvenc(ffmpeg: str) -> None:
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0 or "h264_nvenc" not in completed.stdout:
        raise AssemblyError(
            "Proxy de revisao exige h264_nvenc; fallback silencioso para encoder CPU e proibido."
        )


def _detect_freezes(path: Path, ffmpeg: str) -> list[dict[str, float]]:
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            "freezedetect=n=-45dB:d=0.50",
            "-an",
            "-f",
            "null",
            os.devnull,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise AssemblyError(f"Detector de congelamento nao conseguiu ler {path.name}.")
    starts = [
        float(value)
        for value in re.findall(r"freeze_start:\s*([0-9.]+)", completed.stderr)
    ]
    durations = [
        float(value)
        for value in re.findall(r"freeze_duration:\s*([0-9.]+)", completed.stderr)
    ]
    ends = [
        float(value)
        for value in re.findall(r"freeze_end:\s*([0-9.]+)", completed.stderr)
    ]
    events: list[dict[str, float]] = []
    for index, duration in enumerate(durations):
        start = starts[index] if index < len(starts) else 0.0
        end = ends[index] if index < len(ends) else start + duration
        events.append({"start": start, "duration": duration, "end": end})
    return events


def _project_file(project_dir: Path, raw: Any, suffixes: set[str]) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise AssemblyError("Fonte aprovada nao informada.")
    root = project_dir.resolve()
    candidate = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    if (
        not candidate.is_relative_to(root)
        or not candidate.is_file()
        or candidate.suffix.lower() not in suffixes
    ):
        raise AssemblyError("Fonte aprovada ausente ou fora do projeto.")
    return candidate


def _probe(path: Path, ffprobe: str) -> dict[str, Any]:
    completed = _run([
        ffprobe,
        "-v", "error",
        "-count_frames",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,sample_rate,channels",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ], error=f"FFprobe falhou em {path.name}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssemblyError(f"FFprobe retornou JSON invalido para {path.name}.") from exc
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    try:
        duration = float((payload.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {"video": video, "audio": audio, "duration": duration, "streams": streams}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fps_value(raw: Any) -> float:
    value = str(raw or "0").strip()
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            divisor = float(denominator)
            return float(numerator) / divisor if divisor else 0.0
        except ValueError:
            return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def _progress(callback: Callable[[int, str], None] | None, value: int, message: str) -> None:
    if callback is not None:
        callback(value, message)


def assemble_project(
    project_dir: Path,
    *,
    sources: list[dict[str, Any]],
    source_fingerprint: str,
    job_id: str,
    ffmpeg: str,
    ffprobe: str,
    progress: Callable[[int, str], None] | None = None,
    finish_media: Callable | None = None,
) -> dict[str, Any]:
    """Create a hard-cut master with required DLSS finishing and a review proxy."""

    project_dir = project_dir.resolve()
    if not project_dir.is_dir() or not sources:
        raise AssemblyError("Sequencia aprovada vazia ou projeto inexistente.")
    manifest_path = project_dir / 'project_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path.is_file() else {}
    content_kind = _dlss5.content_policy.normalize(manifest.get('content_kind',manifest.get('contentKind','unknown')))
    try:
        _required_upscale.pipeline_for(content_kind)
    except ValueError as exc:
        raise AssemblyError(str(exc)) from exc
    camera_contract = project_dir / 'sequence_camera_contract.json'
    if camera_contract.is_file():
        try:
            _validate_camera_sequence(camera_contract, stage='assembly')
            contract = json.loads(camera_contract.read_text(encoding='utf-8'))
            planned = contract['takes']
            if [t['id'] for t in planned] != [s.get('takeId') for s in sources]:
                raise ValueError('Ordem/fontes da montagem divergem do contrato de camera.')
            for take, source in zip(planned, sources):
                path = _project_file(project_dir, source.get('videoFile'), {'.mp4', '.mov', '.webm'})
                if _dlss5.sha(path) != take['review']['artifact']['sha256']:
                    raise ValueError('Revisao de camera nao pertence aos bytes selecionados para montagem.')
        except (ValueError, OSError, KeyError) as exc:
            raise AssemblyError('Contrato de camera bloqueou montagem: ' + str(exc)) from exc
    safe_job = re.sub(r"[^A-Za-z0-9_-]+", "", str(job_id or ""))[:32]
    if not safe_job:
        raise AssemblyError("job_id de montagem invalido.")
    output_dir = project_dir / "output"
    qc_dir = project_dir / "qc"
    output_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    resolved: list[dict[str, Any]] = []
    _progress(progress, 5, "Validando fontes aprovadas.")
    for source in sources:
        if not isinstance(source, dict):
            raise AssemblyError("Registro de fonte aprovado invalido.")
        video = _project_file(project_dir, source.get("videoFile"), {".mp4", ".mov", ".webm"})
        video_probe = _probe(video, ffprobe)
        if not isinstance(video_probe.get("video"), dict):
            raise AssemblyError(f"Take {source.get('takeId') or ''} nao possui stream de video.")
        audio_file = None
        if str(source.get("audioFile") or "").strip():
            audio_file = _project_file(
                project_dir,
                source.get("audioFile"),
                {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"},
            )
        embedded = bool(source.get("audioEmbedded"))
        if embedded and not isinstance(video_probe.get("audio"), dict):
            raise AssemblyError(f"Take {source.get('takeId') or ''} declara audio embutido ausente.")
        resolved.append({
            "takeId": str(source.get("takeId") or ""),
            "video": video,
            "audio": audio_file,
            "embedded": embedded,
            "probe": video_probe,
        })

    signatures = {
        (
            str(item["probe"]["video"].get("codec_name") or ""),
            int(item["probe"]["video"].get("width") or 0),
            int(item["probe"]["video"].get("height") or 0),
            str(item["probe"]["video"].get("r_frame_rate") or ""),
        )
        for item in resolved
    }
    if len(signatures) != 1:
        raise AssemblyError(
            "Fontes aprovadas incompativeis em codec, geometria ou FPS; nenhuma reducao de qualidade foi aplicada."
        )
    audio_presence = [bool(item["audio"] or item["embedded"]) for item in resolved]
    try:
        _required_upscale.assert_finished_sources([item['video'] for item in resolved],content_kind)
    except ValueError as exc:
        raise AssemblyError('Acabamento obrigatório por tipo de produção pendente: '+str(exc)) from exc
    if any(audio_presence) and not all(audio_presence):
        raise AssemblyError(
            "A sequencia mistura takes com e sem audio aprovado; complete a escuta antes da montagem."
        )

    master = output_dir / f"{project_dir.name}_master_{safe_job}.mp4"
    review = output_dir / f"{project_dir.name}_review_{safe_job}.mp4"
    qc_file = qc_dir / f"assembly_{safe_job}_qc.json"
    with tempfile.TemporaryDirectory(prefix=f"assembly_{safe_job}_", dir=qc_dir) as temp_raw:
        temp_dir = Path(temp_raw)
        concat_file = temp_dir / "video_concat.txt"
        concat_file.write_text(
            "".join(
                f"file '{item['video'].as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n"
                for item in resolved
            ),
            encoding="utf-8",
        )
        video_only = temp_dir / "video_only.mp4"
        _progress(progress, 20, "Unindo video com cortes secos e sem recodificar.")
        _run([
            ffmpeg, "-v", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-map", "0:v:0", "-c:v", "copy", "-an", str(video_only),
        ], error="Falha na concatenacao visual sem recodificacao")

        if all(audio_presence):
            audio_mix = temp_dir / "approved_audio.m4a"
            audio_inputs: list[str] = []
            filters: list[str] = []
            labels: list[str] = []
            for index, item in enumerate(resolved):
                source_path = item["audio"] or item["video"]
                audio_inputs.extend(["-i", str(source_path)])
                duration = float(item["probe"]["duration"] or 0)
                if duration <= 0:
                    raise AssemblyError(f"Duracao invalida no take {item['takeId']}.")
                label = f"a{index}"
                filters.append(
                    f"[{index}:a:0]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"atrim=0:{duration:.6f},apad=pad_dur={duration:.6f},atrim=0:{duration:.6f},"
                    f"asetpts=PTS-STARTPTS[{label}]"
                )
                labels.append(f"[{label}]")
            filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[outa]")
            _progress(progress, 42, "Unindo somente as faixas aprovadas.")
            _run([
                ffmpeg, "-v", "error", "-y", *audio_inputs,
                "-filter_complex", ";".join(filters),
                "-map", "[outa]", "-c:a", "aac", "-b:a", "256k", str(audio_mix),
            ], error="Falha na concatenacao do audio aprovado")
            _run([
                ffmpeg, "-v", "error", "-y",
                "-i", str(video_only), "-i", str(audio_mix),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", str(master),
            ], error="Falha ao multiplexar master")
        else:
            shutil.copy2(video_only, master)

    _progress(progress,60,'Preservando o master sem DLSS de video.')
    dlss5 = _dlss5.preserve_video_policy(master)
    _progress(progress, 62, "Decodificando o master completo.")
    _run([
        ffmpeg, "-v", "error", "-i", str(master), "-f", "null", os.devnull,
    ], error="QC de decodificacao do master falhou")
    master_probe = _probe(master, ffprobe)
    expected_duration = sum(float(item["probe"]["duration"] or 0) for item in resolved)
    actual_duration = float(master_probe.get("duration") or 0)
    if abs(actual_duration - expected_duration) > max(0.12, len(resolved) / 120):
        raise AssemblyError(
            f"Duracao do master divergiu: esperado {expected_duration:.3f}s, obtido {actual_duration:.3f}s."
        )
    inherited_freezes: list[dict[str, Any]] = []
    source_cursor = 0.0
    for item in resolved:
        for event in _detect_freezes(item["video"], ffmpeg):
            inherited_freezes.append({
                "take_id": item["takeId"],
                "source_start": event["start"],
                "master_start": source_cursor + event["start"],
                "duration": event["duration"],
                "master_end": source_cursor + event["end"],
            })
        source_cursor += float(item["probe"]["duration"] or 0)
    master_freezes = _detect_freezes(master, ffmpeg)
    unmatched_freezes = [
        event
        for event in master_freezes
        if not any(
            abs(event["start"] - inherited["master_start"]) <= 0.05
            and abs(event["duration"] - inherited["duration"]) <= 0.05
            for inherited in inherited_freezes
        )
    ]
    if unmatched_freezes:
        raise AssemblyError(
            "QC detectou congelamento novo no master que nao existe nos bitstreams aprovados; "
            "a montagem nao foi registrada."
        )

    boundary_frames: list[dict[str, str]] = []
    cursor = 0.0
    for index, item in enumerate(resolved[:-1], start=1):
        cursor += float(item["probe"]["duration"] or 0)
        before = qc_dir / f"assembly_{safe_job}_boundary_{index:02d}_before.jpg"
        after = qc_dir / f"assembly_{safe_job}_boundary_{index:02d}_after.jpg"
        for timestamp, target in ((max(0, cursor - 0.05), before), (cursor + 0.05, after)):
            _run([
                ffmpeg, "-v", "error", "-y", "-ss", f"{timestamp:.6f}",
                "-i", str(master), "-frames:v", "1", "-q:v", "2", str(target),
            ], error="Falha ao extrair evidencia de fronteira")
        boundary_frames.append({
            "before": before.relative_to(project_dir).as_posix(),
            "after": after.relative_to(project_dir).as_posix(),
        })

    _progress(progress, 82, "Criando proxy separado para revisao humana.")
    _require_h264_nvenc(ffmpeg)
    _run([
        ffmpeg, "-v", "error", "-y", "-i", str(master),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", "scale=1280:-2:flags=lanczos",
        "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "22", "-b:v", "0",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(review),
    ], error="Falha ao criar proxy de revisao")
    _dlss5.preserve_video_policy(review)
    upscaling = _required_upscale.inherit_assembly([item['video'] for item in resolved], master,content_kind=content_kind)
    final_video = master_probe["video"]
    final_audio = master_probe.get("audio") or {}
    record = {
        "file": master.relative_to(project_dir).as_posix(),
        "review_file": review.relative_to(project_dir).as_posix(),
        "qc_file": qc_file.relative_to(project_dir).as_posix(),
        "duration_seconds": actual_duration,
        "width": int(final_video.get("width") or 0),
        "height": int(final_video.get("height") or 0),
        "fps": _fps_value(final_video.get("r_frame_rate")),
        "video_codec": str(final_video.get("codec_name") or ""),
        "audio_codec": str(final_audio.get("codec_name") or ""),
        "sha256": _sha256(master),
        "source_fingerprint": source_fingerprint,
        "dlss5": dlss5,
        "upscaling_required": upscaling,
        "qc_status": "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING",
        "boundary_frames": boundary_frames,
        "qc": {
            "full_decode": "PASS",
            "duration": "PASS",
            "freeze_events": 0,
            "assembly_introduced_freeze_events": 0,
            "inherited_owner_approved_near_static_intervals": inherited_freezes,
            "static_tail": "PASS_NO_NEW_ASSEMBLY_FREEZE",
            "hard_cuts": True,
            "video_stream_copy": inherited_dlss,
            "review_video_encoder": "h264_nvenc",
            "audio_source_policy": "approved_only" if all(audio_presence) else "silent_sequence",
        },
    }
    _atomic_json(qc_file, record)
    _progress(progress, 100, "Master tecnico pronto para a revisao final do proprietario.")
    return record
