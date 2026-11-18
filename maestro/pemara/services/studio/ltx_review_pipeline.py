"""Locked 24-to-60 FPS review post-processing for Maestro.

The approved paths are intentionally narrow: native 24 FPS video,
Practical-RIFE 4.25 with one midpoint per source-frame pair, then a locked CFR
60 FPS NVENC delivery. The horizontal H3/LTX 2.5 review contract keeps its
approved 1.25x cadence retime; the vertical H3 contract preserves source duration.
Neither path interpolates directly by factor 5 or performs spatial upscale.
"""

from __future__ import annotations

import hashlib
import copy
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable


PIPELINE_VERSION = "h3_ltx25_rife425_midpoint48_retime60_v1"
H3_VERTICAL_PIPELINE_VERSION = "h3_vertical_rife425_midpoint48_cfr60_duration_v1"
EXPECTED_RIFE_REVISION = "17d8c7a1005b37f4c97bfee04e316aaec7fdc536"
EXPECTED_RIFE_MODEL_SHA256 = "6615790efd627772917205db291f51cd392528a157ecbb2ecaeec3bff8eb6de2"

RIFE_ROOT = Path(
    os.environ.get("MAESTRO_RIFE_ROOT", r"E:\Pemara\third_party\Practical-RIFE")
)
RIFE_PYTHON = Path(
    os.environ.get(
        "MAESTRO_RIFE_PYTHON",
        str(RIFE_ROOT / ".venv" / "Scripts" / "python.exe"),
    )
)
RIFE_SCRIPT = Path(
    os.environ.get("MAESTRO_RIFE_SCRIPT", str(RIFE_ROOT / "inference_video.py"))
)
RIFE_MODEL_DIR = Path(
    os.environ.get("MAESTRO_RIFE_MODEL_DIR", str(RIFE_ROOT / "train_log"))
)

_ProgressCallback = Callable[[int, str], None]
_ProcessCallback = Callable[[subprocess.Popen[str] | None], None]


class LtxReviewPipelineError(RuntimeError):
    """Raised when the locked review pipeline cannot be proven end-to-end."""


def _locked_source_resolution(policy: dict[str, Any]) -> tuple[int, int]:
    source_resolution = policy.get("source_resolution")
    if not isinstance(source_resolution, dict):
        raise LtxReviewPipelineError("Contrato source_resolution esta ausente.")
    try:
        width = int(source_resolution.get("width") or 0)
        height = int(source_resolution.get("height") or 0)
    except (TypeError, ValueError) as exc:
        raise LtxReviewPipelineError("Contrato source_resolution e invalido.") from exc
    if (width, height) not in {(1280, 720), (960, 544), (720, 1280)}:
        raise LtxReviewPipelineError(
            "Contrato source_resolution deve ser 1280x720, 960x544 ou 720x1280."
        )
    return width, height


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise LtxReviewPipelineError(f"JSON invalido no contrato de review: {path}") from exc
    return payload if isinstance(payload, dict) else {}


def _queue_path(project_dir: Path) -> Path:
    project_dir = project_dir.resolve()
    manifest = _read_json(project_dir / "project_manifest.json")
    configured = str(manifest.get("take_queue") or "take_queue.json").strip()
    candidate = (project_dir / configured).resolve()
    if candidate.parent != project_dir or candidate.suffix.lower() != ".json":
        raise LtxReviewPipelineError("take_queue do projeto saiu da raiz autorizada.")
    return candidate


def load_ltx_review_pipeline_policy(
    project_dir: Path,
    selected_model: str,
) -> dict[str, Any] | None:
    """Return the exact locked policy or fail closed when it was altered."""

    queue = _read_json(_queue_path(Path(project_dir)))
    engine_policy = queue.get("engine_policy")
    if not isinstance(engine_policy, dict):
        return None
    policy = engine_policy.get("review_motion_pipeline")
    if not isinstance(policy, dict) or not bool(policy.get("enabled")):
        return None
    applies_to_models = policy.get("applies_to_models")
    applies_to_engines = policy.get("applies_to_engines")
    selected_model_key = str(selected_model or "").strip()
    selected_model_lower = selected_model_key.casefold()
    selected_engine = (
        "ltx_2_5"
        if "ltx-2.5" in selected_model_lower or "ltx_2_5" in selected_model_lower
        else "minimax_h3"
        if "minimax_h3" in selected_model_lower or "minimax h3" in selected_model_lower
        else ""
    )
    model_allowed = isinstance(applies_to_models, list) and selected_model_key in {
        str(item).strip() for item in applies_to_models
    }
    engine_allowed = isinstance(applies_to_engines, list) and selected_engine in {
        str(item).strip() for item in applies_to_engines
    }
    if not model_allowed and not engine_allowed:
        return None

    policy = copy.deepcopy(policy)
    source_resolutions = policy.get("source_resolutions")
    if isinstance(source_resolutions, dict) and selected_engine:
        selected_resolution = source_resolutions.get(selected_engine)
        if isinstance(selected_resolution, dict):
            policy["source_resolution"] = selected_resolution

    version = str(policy.get("version") or "")
    source_resolution = _locked_source_resolution(policy)
    if version == PIPELINE_VERSION:
        expected_resolution = (960, 544) if selected_engine == "ltx_2_5" else (1280, 720)
        expected_frame_completion = "clone_terminal_frame_once"
        expected_retime_method = "setpts_preserve_every_frame"
    elif version == H3_VERTICAL_PIPELINE_VERSION:
        expected_resolution = (720, 1280)
        expected_frame_completion = "fps_cadence_duration_preserving"
        expected_retime_method = "fps_filter_preserve_source_duration"
    else:
        raise LtxReviewPipelineError("Contrato fixo RIFE possui version desconhecida.")
    if source_resolution != expected_resolution:
        raise LtxReviewPipelineError(
            "Contrato source_resolution divergiu da versao aprovada."
        )

    interpolation = policy.get("interpolation")
    delivery = policy.get("delivery")
    qc = policy.get("qc")
    if not all(isinstance(item, dict) for item in (interpolation, delivery, qc)):
        raise LtxReviewPipelineError("Contrato fixo de video/RIFE esta incompleto.")

    exact_checks = {
        "status": (str(policy.get("status") or ""), "LOCKED_APPROVED"),
        "source_fps": (int(policy.get("source_fps") or 0), 24),
        "rife_engine": (str(interpolation.get("engine") or ""), "Practical-RIFE"),
        "rife_model": (str(interpolation.get("model") or ""), "4.25"),
        "rife_revision": (
            str(interpolation.get("revision") or "").lower(),
            EXPECTED_RIFE_REVISION,
        ),
        "rife_model_sha256": (
            str(interpolation.get("model_sha256") or "").lower(),
            EXPECTED_RIFE_MODEL_SHA256,
        ),
        "rife_factor": (int(interpolation.get("factor") or 0), 2),
        "rife_fps": (int(interpolation.get("output_fps") or 0), 48),
        "rife_mode": (
            str(interpolation.get("mode") or ""),
            "single_midpoint_between_adjacent_source_frames",
        ),
        "working_format": (str(interpolation.get("working_format") or ""), "png"),
        "delivery_fps": (int(delivery.get("fps") or 0), 60),
        "delivery_encoder": (str(delivery.get("encoder") or ""), "h264_nvenc"),
        "frame_completion": (
            str(delivery.get("frame_completion") or ""),
            expected_frame_completion,
        ),
        "retime_method": (
            str(delivery.get("retime_method") or ""),
            expected_retime_method,
        ),
    }
    mismatches = [
        name for name, (actual, expected) in exact_checks.items() if actual != expected
    ]
    if mismatches:
        raise LtxReviewPipelineError(
            "Contrato fixo de video/RIFE foi alterado: " + ", ".join(mismatches) + "."
        )
    if not bool(interpolation.get("preserve_all_source_frames")):
        raise LtxReviewPipelineError("RIFE deve preservar todos os quadros de origem.")
    if not bool(interpolation.get("forbid_direct_factor5")):
        raise LtxReviewPipelineError("A trava contra interpolacao direta fator 5 foi removida.")
    if bool(delivery.get("upscale")) or bool(policy.get("upscale_allowed_before_human_approval")):
        raise LtxReviewPipelineError("Upscale foi habilitado antes da aprovacao humana.")
    if not bool(qc.get("require_exact_frame_count")) or not bool(
        qc.get("require_constant_timestamps")
    ):
        raise LtxReviewPipelineError("Gates temporais obrigatorios foram desabilitados.")
    return policy


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_executable(raw: str | Path, label: str) -> str:
    candidate = shutil.which(str(raw))
    if candidate:
        return str(Path(candidate).resolve())
    path = Path(raw).expanduser().resolve()
    if path.is_file():
        return str(path)
    raise LtxReviewPipelineError(f"{label} indisponivel: {raw}")


def _resolve_ffprobe(ffmpeg: str | Path) -> str:
    ffmpeg_path = Path(_resolve_executable(ffmpeg, "FFmpeg"))
    sibling = ffmpeg_path.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if sibling.is_file():
        return str(sibling)
    return _resolve_executable("ffprobe", "FFprobe")


def _run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "")[-2000:]
        raise LtxReviewPipelineError(f"Falha no FFprobe: {detail}")
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise LtxReviewPipelineError("FFprobe retornou JSON invalido.") from exc
    return payload if isinstance(payload, dict) else {}


def probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    payload = _run_json([
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-count_frames",
        "-show_entries",
        "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,duration",
        "-of", "json",
        str(path),
    ])
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    if not streams or not isinstance(streams[0], dict):
        raise LtxReviewPipelineError("Video sem stream visual detectavel.")
    stream = streams[0]
    raw_frames = stream.get("nb_read_frames") or stream.get("nb_frames") or 0
    try:
        frame_count = int(raw_frames)
    except (TypeError, ValueError) as exc:
        raise LtxReviewPipelineError("FFprobe nao conseguiu contar os quadros.") from exc
    return {
        "codec": str(stream.get("codec_name") or ""),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or ""),
        "frames": frame_count,
        "duration_seconds": float(stream.get("duration") or 0.0),
    }


def _has_audio(path: Path, ffprobe: str) -> bool:
    payload = _run_json([
        ffprobe,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "json",
        str(path),
    ])
    return bool(payload.get("streams"))


def _constant_timestamps(path: Path, ffprobe: str, target_fps: int) -> bool:
    payload = _run_json([
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "frame=best_effort_timestamp_time",
        "-of", "json",
        str(path),
    ])
    frames = payload.get("frames") if isinstance(payload.get("frames"), list) else []
    values: list[float] = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        try:
            values.append(float(frame["best_effort_timestamp_time"]))
        except (KeyError, TypeError, ValueError):
            return False
    if len(values) < 2:
        return False
    expected = 1.0 / float(target_fps)
    return all(abs((values[index] - values[index - 1]) - expected) <= 0.000002 for index in range(1, len(values)))


def build_rife_command(source: Path) -> list[str]:
    return [
        str(RIFE_PYTHON.resolve()),
        str(RIFE_SCRIPT.resolve()),
        "--video", str(source.resolve()),
        "--model", str(RIFE_MODEL_DIR.resolve()),
        "--exp", "1",
        "--png",
        "--preserve-all-frames",
        "--fp16",
    ]


def build_delivery_command(
    *,
    ffmpeg: str,
    png_pattern: Path,
    source: Path,
    output: Path,
    expected_frames: int,
    include_audio: bool,
    retime_method: str = "setpts_preserve_every_frame",
) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "48",
        "-start_number", "0",
        "-i", str(png_pattern),
    ]
    if retime_method == "setpts_preserve_every_frame":
        video_filter = "tpad=stop_mode=clone:stop=1,setpts=N/(60*TB)"
        audio_speed_filter = "atempo=1.25,"
    elif retime_method == "fps_filter_preserve_source_duration":
        video_filter = "fps=60:round=near,setpts=PTS-STARTPTS"
        audio_speed_filter = ""
    else:
        raise LtxReviewPipelineError("retime_method nao pertence a um contrato aprovado.")
    if include_audio:
        # The retimed native LTX audio can finish a few milliseconds before the
        # terminal video clone.  ``-shortest`` used to cut that last frame and
        # made otherwise valid 193-frame takes fail as 385/386.  Pad only the
        # missing tail and trim both streams to the exact delivery cadence.
        delivery_duration = int(expected_frames) / 60.0
        audio_filter = (
            f"{audio_speed_filter}apad,"
            f"atrim=duration={delivery_duration:.9f},asetpts=PTS-STARTPTS"
        )
        command.extend([
            "-i", str(source),
            "-filter_complex", f"[0:v]{video_filter}[v];[1:a:0]{audio_filter}[a]",
            "-map", "[v]",
            "-map", "[a]",
        ])
    else:
        command.extend(["-vf", video_filter, "-an"])
    command.extend([
        "-r", "60",
        "-fps_mode", "cfr",
        "-frames:v", str(int(expected_frames)),
        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-tune", "hq",
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-rc", "vbr",
        "-cq", "15",
        "-b:v", "0",
        "-maxrate", "24M",
        "-bufsize", "48M",
    ])
    if include_audio:
        command.extend(["-c:a", "aac", "-b:a", "192k", "-ar", "48000"])
    command.extend([
        "-metadata", "title=Maestro RIFE 4.25 midpoint review",
        "-metadata", "comment=24fps native -> RIFE x2 midpoint 48fps -> locked CFR 60fps; no upscale",
        "-movflags", "+faststart",
        str(output),
    ])
    return command


def _run_process(
    command: list[str],
    *,
    cwd: Path,
    label: str,
    cancel_event: Any = None,
    process_cb: _ProcessCallback | None = None,
) -> None:
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        env=os.environ.copy(),
    )
    if process_cb:
        process_cb(process)
    try:
        stdout, _ = process.communicate()
    finally:
        if process_cb:
            process_cb(None)
    if cancel_event is not None and cancel_event.is_set():
        raise LtxReviewPipelineError(f"{label} cancelado pelo proprietario.")
    if process.returncode != 0:
        raise LtxReviewPipelineError(
            f"{label} terminou com codigo {process.returncode}: {(stdout or '')[-2200:]}"
        )


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_runtime(policy: dict[str, Any], ffmpeg: str) -> tuple[str, str]:
    for path, label in (
        (RIFE_PYTHON, "Python isolado do RIFE"),
        (RIFE_SCRIPT, "inference_video.py"),
        (RIFE_MODEL_DIR / "flownet.pkl", "modelo RIFE 4.25"),
    ):
        if not path.is_file():
            raise LtxReviewPipelineError(f"{label} ausente: {path}")
    if _sha256(RIFE_MODEL_DIR / "flownet.pkl") != EXPECTED_RIFE_MODEL_SHA256:
        raise LtxReviewPipelineError("Hash do modelo RIFE 4.25 divergiu do perfil aprovado.")
    revision = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={RIFE_ROOT.as_posix()}",
            "-C",
            str(RIFE_ROOT),
            "rev-parse",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    actual_revision = revision.stdout.strip().lower()
    if revision.returncode != 0 or actual_revision != EXPECTED_RIFE_REVISION:
        raise LtxReviewPipelineError(
            "Revisao do Practical-RIFE divergiu do perfil aprovado: "
            f"returncode={revision.returncode}, actual={actual_revision!r}, "
            f"expected={EXPECTED_RIFE_REVISION!r}, stderr={revision.stderr.strip()!r}."
        )
    ffmpeg_resolved = _resolve_executable(ffmpeg, "FFmpeg")
    ffprobe_resolved = _resolve_ffprobe(ffmpeg_resolved)
    encoders = subprocess.run(
        [ffmpeg_resolved, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    if encoders.returncode != 0 or "h264_nvenc" not in (encoders.stdout + encoders.stderr):
        raise LtxReviewPipelineError("h264_nvenc indisponivel; fallback por CPU e proibido.")
    del policy
    return ffmpeg_resolved, ffprobe_resolved


def run_ltx_review_pipeline(
    *,
    source: Path,
    output: Path,
    project_dir: Path,
    policy: dict[str, Any],
    ffmpeg: str,
    progress_cb: _ProgressCallback | None = None,
    cancel_event: Any = None,
    process_cb: _ProcessCallback | None = None,
    release_gpu_cb: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Run and prove the locked midpoint/retime path, or publish nothing."""

    source = source.resolve(strict=True)
    output = output.resolve()
    project_dir = project_dir.resolve(strict=True)
    if not source.is_relative_to(project_dir) or not output.is_relative_to(project_dir):
        raise LtxReviewPipelineError("Fonte ou destino do review ficou fora do projeto.")
    pipeline_version = str(policy.get("version") or "")
    source_width, source_height = _locked_source_resolution(policy)
    retime_method = str((policy.get("delivery") or {}).get("retime_method") or "")
    marker = output.with_suffix(f"{output.suffix}.review_pipeline.json")
    source_sha256 = _sha256(source)
    existing = _read_json(marker)
    if output.is_file() and existing:
        if (
            existing.get("pipeline_version") == pipeline_version
            and str((existing.get("source") or {}).get("sha256") or "") == source_sha256
            and str((existing.get("delivery") or {}).get("sha256") or "") == _sha256(output)
        ):
            return existing
        raise LtxReviewPipelineError("Destino existente nao corresponde ao pipeline aprovado.")
    if output.exists() or marker.exists():
        raise LtxReviewPipelineError("Destino parcial do pipeline aprovado exige revisao manual.")

    ffmpeg_resolved, ffprobe = _validate_runtime(policy, ffmpeg)
    source_probe = probe_video(source, ffprobe)
    if (source_probe["width"], source_probe["height"]) != (source_width, source_height):
        raise LtxReviewPipelineError(
            f"Fonte deve ser exatamente {source_width}x{source_height}."
        )
    if source_probe["fps"] not in {"24/1", "24"}:
        raise LtxReviewPipelineError("Fonte deve ser exatamente 24 FPS.")
    source_frames = int(source_probe["frames"])
    if source_frames < 49:
        raise LtxReviewPipelineError("Fonte de video curta demais para o pipeline aprovado.")
    expected_rife_frames = source_frames * 2 - 1
    if retime_method == "setpts_preserve_every_frame":
        expected_delivery_frames = source_frames * 2
        delivery_speed_factor = 1.25
    elif retime_method == "fps_filter_preserve_source_duration":
        expected_delivery_frames = round((source_frames - 1) * 60 / 24)
        delivery_speed_factor = 1.0
    else:
        raise LtxReviewPipelineError("retime_method nao pertence a um contrato aprovado.")
    include_audio = _has_audio(source, ffprobe)

    if release_gpu_cb:
        release_gpu_cb()
    if progress_cb:
        progress_cb(99, "Video nativo pronto; aplicando RIFE 4.25 x2 com um unico midpoint por intervalo.")

    work_root = project_dir / "qc" / ".ltx_review_work"
    work_root.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    final_part = output.with_name(f".{output.stem}.{uuid.uuid4().hex}.part.mp4")
    started = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="rife425_midpoint_", dir=str(work_root)) as temp_name:
            temp_dir = Path(temp_name)
            _run_process(
                build_rife_command(source),
                cwd=temp_dir,
                label="RIFE 4.25 midpoint",
                cancel_event=cancel_event,
                process_cb=process_cb,
            )
            frame_dir = temp_dir / "vid_out"
            png_files = sorted(frame_dir.glob("*.png"))
            if len(png_files) != expected_rife_frames:
                raise LtxReviewPipelineError(
                    f"RIFE produziu {len(png_files)} quadros; esperado {expected_rife_frames}."
                )
            expected_names = [f"{index:07d}.png" for index in range(expected_rife_frames)]
            if [item.name for item in png_files] != expected_names:
                raise LtxReviewPipelineError("Sequencia PNG do RIFE possui lacunas ou ordem invalida.")
            if progress_cb:
                progress_cb(99, "RIFE x2 validado; fechando em CFR 60 FPS com NVENC, sem upscale.")
            _run_process(
                build_delivery_command(
                    ffmpeg=ffmpeg_resolved,
                    png_pattern=frame_dir / "%07d.png",
                    source=source,
                    output=final_part,
                    expected_frames=expected_delivery_frames,
                    include_audio=include_audio,
                    retime_method=retime_method,
                ),
                cwd=temp_dir,
                label="Entrega NVENC 60 FPS",
                cancel_event=cancel_event,
                process_cb=process_cb,
            )
            if not final_part.is_file() or final_part.stat().st_size < 1024:
                raise LtxReviewPipelineError("NVENC nao produziu um MP4 valido.")
            delivery_probe = probe_video(final_part, ffprobe)
            if (delivery_probe["width"], delivery_probe["height"]) != (source_width, source_height):
                raise LtxReviewPipelineError(
                    f"Entrega temporal alterou a resolucao {source_width}x{source_height}."
                )
            if delivery_probe["fps"] not in {"60/1", "60"}:
                raise LtxReviewPipelineError("Entrega temporal nao ficou CFR 60 FPS.")
            if int(delivery_probe["frames"]) != expected_delivery_frames:
                raise LtxReviewPipelineError(
                    f"Entrega possui {delivery_probe['frames']} quadros; esperado {expected_delivery_frames}."
                )
            timestamps_constant = _constant_timestamps(final_part, ffprobe, 60)
            if not timestamps_constant:
                raise LtxReviewPipelineError("Entrega 60 FPS possui timestamps irregulares.")
            os.replace(final_part, output)
    finally:
        final_part.unlink(missing_ok=True)

    delivery_sha256 = _sha256(output)
    payload = {
        "schema_version": "1.0",
        "status": "PENDING_HUMAN_REVIEW",
        "pipeline_version": pipeline_version,
        "locked_approved": True,
        "source": {
            "path": str(source),
            "sha256": source_sha256,
            **source_probe,
        },
        "interpolation": {
            "engine": "Practical-RIFE",
            "model": "4.25",
            "revision": EXPECTED_RIFE_REVISION,
            "model_sha256": EXPECTED_RIFE_MODEL_SHA256,
            "factor": 2,
            "mode": "single_midpoint_between_adjacent_source_frames",
            "fps": 48,
            "frames_before_terminal_clone": expected_rife_frames,
            "preserve_all_source_frames": True,
            "direct_factor5_forbidden": True,
        },
        "delivery": {
            "path": str(output),
            "sha256": delivery_sha256,
            "width": source_width,
            "height": source_height,
            "fps": 60,
            "frames": expected_delivery_frames,
            "duration_seconds": float(delivery_probe["duration_seconds"]),
            "speed_factor_from_midpoint_48fps": delivery_speed_factor,
            "retime_method": retime_method,
            "encoder": "h264_nvenc",
            "audio": (
                "aac_atempo_1.25x"
                if include_audio and delivery_speed_factor != 1.0
                else "aac_native_duration_preserved"
                if include_audio
                else "none"
            ),
            "upscale": False,
        },
        "qc": {
            "exact_frame_count": True,
            "timestamps_constant": True,
            "terminal_frame_clones": 1,
            "temporary_png_frames_removed": True,
            "human_visual_review_required": True,
        },
        "elapsed_seconds": round(time.time() - started, 3),
        "created_at_epoch": time.time(),
    }
    _atomic_json_write(marker, payload)
    return payload
