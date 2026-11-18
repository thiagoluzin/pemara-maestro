"""Isolated MOVA runtime orchestration for Maestro Studio.

This module intentionally does not import torch or MOVA.  The Studio service
must remain lightweight while the 72 GB model is loaded in a dedicated child
process that can be canceled without taking the API down.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable


MOVA_MODEL_NAME = "MOVA-720p"
MOVA_MODEL_REPO = "OpenMOSS-Team/MOVA-720p"
MOVA_MODEL_REVISION = "8462bea9a317a3591279faeedfd3ca01b055cb59"
MOVA_SOURCE_REVISION = "9b39667838a7c7ff2c367f5c5189d35c422878bd"
MOVA_EXPECTED_BYTES = 77_689_755_302
MOVA_MIN_RAM_GB = 112.0
MOVA_MIN_FREE_RAM_GB = 82.0
MOVA_MIN_FREE_VRAM_GB = 28.0
MOVA_MIN_FREE_DISK_GB = 20.0
MOVA_TRITON_VERSION = "3.7.1"

_BASE_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_ENGINE_ROOT = (
    _BASE_DIR / "ferramentas" / "video_global_engine" / "engines" / "mova"
)

MOVA_MODEL_DIR = Path(
    os.environ.get("MAESTRO_MOVA_MODEL_DIR", r"D:\PemaraModels\mova\MOVA-720p")
)
MOVA_SOURCE_DIR = Path(
    os.environ.get("MAESTRO_MOVA_SOURCE_DIR", r"E:\Pemara\third_party\MOVA")
)
MOVA_ENGINE_ROOT = Path(os.environ.get("MAESTRO_MOVA_ENGINE_ROOT", str(_DEFAULT_ENGINE_ROOT)))
MOVA_PYTHON = Path(
    os.environ.get(
        "MAESTRO_MOVA_PYTHON",
        str(MOVA_ENGINE_ROOT / ".venv" / "Scripts" / "python.exe"),
    )
)
MOVA_RUNNER = Path(
    os.environ.get(
        "MAESTRO_MOVA_RUNNER",
        str(MOVA_ENGINE_ROOT / "maestro_mova_runner.py"),
    )
)
MOVA_RUNTIME_MARKER = MOVA_ENGINE_ROOT / "runtime-ready.json"

# Size checks catch partial/resumed downloads without hashing 72 GB on every
# Studio status refresh. Hugging Face validates the LFS object hashes while it
# downloads the pinned revision.
MOVA_WEIGHT_FILES = {
    "audio_dit/diffusion_pytorch_model.safetensors": 2_838_470_672,
    "audio_vae/diffusion_pytorch_model.safetensors": 743_102_794,
    "dual_tower_bridge/diffusion_pytorch_model.safetensors": 5_319_561_560,
    "text_encoder/model-00001-of-00003.safetensors": 4_935_812_536,
    "text_encoder/model-00002-of-00003.safetensors": 4_983_103_192,
    "text_encoder/model-00003-of-00003.safetensors": 1_442_935_480,
    "video_dit/diffusion_pytorch_model-00001-of-00003.safetensors": 9_969_027_888,
    "video_dit/diffusion_pytorch_model-00002-of-00003.safetensors": 9_891_559_912,
    "video_dit/diffusion_pytorch_model-00003-of-00003.safetensors": 8_717_326_600,
    "video_dit_2/diffusion_pytorch_model-00001-of-00003.safetensors": 9_969_027_888,
    "video_dit_2/diffusion_pytorch_model-00002-of-00003.safetensors": 9_891_559_912,
    "video_dit_2/diffusion_pytorch_model-00003-of-00003.safetensors": 8_717_326_600,
    "video_vae/diffusion_pytorch_model.safetensors": 253_806_966,
}

_ProgressCallback = Callable[[int, str], None]
_ProcessCallback = Callable[[subprocess.Popen[str] | None], None]


def _physical_ram_gb() -> float:
    try:
        import psutil

        return round(float(psutil.virtual_memory().total) / (1024**3), 1)
    except Exception:
        return 0.0


def _available_ram_gb() -> float:
    try:
        import psutil

        return round(float(psutil.virtual_memory().available) / (1024**3), 1)
    except Exception:
        return 0.0


def _free_disk_gb(path: Path) -> float:
    try:
        return round(float(shutil.disk_usage(Path(path).resolve().anchor).free) / (1024**3), 1)
    except (OSError, ValueError):
        return 0.0


def _free_vram_gb() -> float:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        free_mib = float((completed.stdout or "").splitlines()[0].strip())
        return round(free_mib / 1024.0, 1)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return 0.0


def _model_progress() -> tuple[int, int, list[str]]:
    present = 0
    missing: list[str] = []
    for relative, expected_size in MOVA_WEIGHT_FILES.items():
        candidate = MOVA_MODEL_DIR / Path(relative)
        try:
            size = candidate.stat().st_size
        except OSError:
            size = 0
        present += min(size, expected_size)
        if size != expected_size:
            missing.append(relative)
    expected = sum(MOVA_WEIGHT_FILES.values())
    return present, expected, missing


def _runtime_marker_valid() -> bool:
    try:
        payload = json.loads(MOVA_RUNTIME_MARKER.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        payload.get("ok") is True
        and payload.get("torch_compile") is True
        and str(payload.get("triton") or "") == MOVA_TRITON_VERSION
        and payload.get("cuda_allocator") == "cudaMallocAsync"
        and payload.get("nvenc") == "h264_nvenc"
        and list(payload.get("capability") or []) == [12, 0]
    )


def mova_status() -> dict[str, Any]:
    present, expected_weights, missing = _model_progress()
    model_complete = not missing and (MOVA_MODEL_DIR / "model_index.json").is_file()
    source_ready = (MOVA_SOURCE_DIR / "mova" / "__init__.py").is_file()
    runtime_ready = bool(
        MOVA_PYTHON.is_file()
        and MOVA_RUNNER.is_file()
        and MOVA_RUNTIME_MARKER.is_file()
        and _runtime_marker_valid()
    )
    ram_gb = _physical_ram_gb()
    available_ram_gb = _available_ram_gb()
    free_vram_gb = _free_vram_gb()
    output_free_disk_gb = _free_disk_gb(_BASE_DIR / "dados" / "outputs" / "generative")
    enough_ram = ram_gb >= MOVA_MIN_RAM_GB
    ready = bool(model_complete and source_ready and runtime_ready and enough_ram)

    if ready:
        message = "Pronto para candidatos 480p com audio sincronizado; upscale somente apos aprovacao."
    elif not model_complete:
        pct = int((present / expected_weights) * 100) if expected_weights else 0
        message = f"Pesos MOVA-720p em download ({pct}%)."
    elif not source_ready or not runtime_ready:
        message = "Pesos instalados; ambiente MOVA ainda nao esta pronto."
    elif not enough_ram:
        message = f"Instalado; aguardando 128 GB de RAM (detectado: {ram_gb:.1f} GB)."
    else:
        message = "MOVA indisponivel."

    return {
        "model": MOVA_MODEL_NAME,
        "repo": MOVA_MODEL_REPO,
        "model_revision": MOVA_MODEL_REVISION,
        "source_revision": MOVA_SOURCE_REVISION,
        "model_dir": str(MOVA_MODEL_DIR),
        "source_dir": str(MOVA_SOURCE_DIR),
        "python": str(MOVA_PYTHON),
        "runner": str(MOVA_RUNNER),
        "model_complete": model_complete,
        "source_ready": source_ready,
        "runtime_ready": runtime_ready,
        "ram_gb": ram_gb,
        "available_ram_gb": available_ram_gb,
        "free_vram_gb": free_vram_gb,
        "output_free_disk_gb": output_free_disk_gb,
        "minimum_ram_gb": MOVA_MIN_RAM_GB,
        "enough_ram": enough_ram,
        "ready": ready,
        "downloaded_weight_bytes": present,
        "expected_weight_bytes": expected_weights,
        "expected_repository_bytes": MOVA_EXPECTED_BYTES,
        "missing_weight_files": missing[:6],
        "profile": {
            "resolution": "832x480",
            "frames": 121,
            "fps": 24,
            "steps": 25,
            "dtype": "bf16",
            "offload": "group",
            "offload_stream": "auto_preview_with_sequential_oom_retry",
            "attention": "sdpa",
            "triton": MOVA_TRITON_VERSION,
            "torch_compile": True,
            "cuda_allocator": "cudaMallocAsync",
            "encoder": "h264_nvenc",
            "native_audio": True,
            "approval_gate_before_upscale": True,
            "resource_gates": {
                "minimum_free_ram_gb": MOVA_MIN_FREE_RAM_GB,
                "minimum_free_vram_gb": MOVA_MIN_FREE_VRAM_GB,
                "minimum_free_disk_gb": MOVA_MIN_FREE_DISK_GB,
            },
        },
        "available_profiles": {
            "review_480p": {"resolution": "832x480", "frames": [97, 121, 145], "steps": 25},
            "preview_360p": {"resolution": "640x352", "frames": [97, 121, 145], "steps": 25},
            "master_720p": {
                "resolution": "1280x720",
                "frames": 193,
                "steps": 50,
                "status": "blocked_until_final_take_approval",
            },
        },
        "message": message,
    }


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass


def _parse_progress(line: str) -> tuple[int, str] | None:
    if not line.startswith("MAESTRO_PROGRESS\t"):
        return None
    parts = line.rstrip("\r\n").split("\t", 2)
    if len(parts) != 3:
        return None
    try:
        percent = max(1, min(99, int(parts[1])))
    except ValueError:
        return None
    return percent, parts[2].strip() or "MOVA em execucao."


def _output_item(
    path: Path,
    output_root: Path,
    *,
    fps: float,
    width: int,
    height: int,
) -> dict[str, Any]:
    resolved_root = output_root.resolve()
    resolved_path = path.resolve(strict=True)
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise RuntimeError("Saida MOVA ficou fora da pasta autorizada do Studio.")
    relative = resolved_path.relative_to(resolved_root).as_posix()
    query = urllib.parse.urlencode({"path": relative})
    return {
        "kind": "video",
        "filename": resolved_path.name,
        "path": relative,
        "url": f"/api/generative/output?{query}",
        "media_type": "video/mp4",
        "fps": float(fps),
        "width": int(width),
        "height": int(height),
        "audio": "aac",
        "encoder": "h264_nvenc",
    }


def run_mova_generation(
    *,
    prompt: str,
    negative_prompt: str,
    seed: int,
    width: int,
    height: int,
    frames: int,
    fps: float,
    steps: int,
    guidance: float,
    base_image_bytes: bytes | None,
    base_image_name: str,
    output_root: Path,
    ffmpeg: str,
    progress_cb: _ProgressCallback | None = None,
    cancel_event: Any = None,
    process_cb: _ProcessCallback | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    status = mova_status()
    if not status["ready"]:
        raise RuntimeError(status["message"])
    if not prompt.strip():
        raise ValueError("Prompt MOVA vazio.")
    if float(fps) < 24:
        raise ValueError("MOVA no Maestro exige pelo menos 24 FPS.")
    if int(frames) < 17:
        raise ValueError("MOVA exige ao menos 17 quadros.")
    width = int(width)
    height = int(height)
    if (width, height) not in {(640, 352), (832, 480), (1280, 720)}:
        raise ValueError("MOVA aceita preview 640x352, candidato 832x480 ou master 1280x720.")
    frames = ((int(frames) - 1) // 4) * 4 + 1
    fps = max(24.0, min(60.0, float(fps)))
    steps = max(25, min(80, int(steps)))
    guidance = max(1.0, min(12.0, float(guidance)))

    output_root = Path(output_root)
    available_ram_gb = _available_ram_gb()
    free_vram_gb = _free_vram_gb()
    free_disk_gb = _free_disk_gb(output_root)
    resource_failures: list[str] = []
    if available_ram_gb < MOVA_MIN_FREE_RAM_GB:
        resource_failures.append(
            f"RAM livre {available_ram_gb:.1f} GB; minimo {MOVA_MIN_FREE_RAM_GB:.0f} GB"
        )
    if free_vram_gb < MOVA_MIN_FREE_VRAM_GB:
        resource_failures.append(
            f"VRAM livre {free_vram_gb:.1f} GB; minimo {MOVA_MIN_FREE_VRAM_GB:.0f} GB"
        )
    if free_disk_gb < MOVA_MIN_FREE_DISK_GB:
        resource_failures.append(
            f"disco livre {free_disk_gb:.1f} GB; minimo {MOVA_MIN_FREE_DISK_GB:.0f} GB"
        )
    if resource_failures:
        raise RuntimeError(
            "Preflight MOVA bloqueou a geracao para evitar falha/OOM: " + "; ".join(resource_failures) + "."
        )
    output_dir = output_root / "video" / time.strftime("%Y%m%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"mova_{width}x{height}_{time.strftime('%H%M%S')}_{seed}.mp4"
    log_dir = Path(r"E:\Pemara\logs\mova")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"inference_{time.strftime('%Y%m%d_%H%M%S')}_{seed}.log"

    if progress_cb:
        progress_cb(4, "Validando MOVA-720p e preparando o processo isolado.")

    with tempfile.TemporaryDirectory(prefix="maestro_mova_") as temp_name:
        temp_dir = Path(temp_name)
        prompt_path = temp_dir / "prompt.txt"
        negative_path = temp_dir / "negative.txt"
        prompt_path.write_text(prompt.strip(), encoding="utf-8")
        negative_path.write_text((negative_prompt or "").strip(), encoding="utf-8")

        command = [
            str(MOVA_PYTHON),
            "-s",
            str(MOVA_RUNNER),
            "--source-dir", str(MOVA_SOURCE_DIR),
            "--model-dir", str(MOVA_MODEL_DIR),
            "--prompt-file", str(prompt_path),
            "--negative-file", str(negative_path),
            "--output", str(output_path),
            "--ffmpeg", str(ffmpeg),
            "--seed", str(int(seed)),
            "--frames", str(frames),
            "--fps", str(fps),
            "--steps", str(steps),
            "--guidance", str(guidance),
            "--width", str(width),
            "--height", str(height),
            "--offload", "group",
            "--offload-stream", "auto",
            "--attention", "sdpa",
            "--remove-video-dit",
        ]
        if base_image_bytes:
            suffix = Path(base_image_name or "reference.png").suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
                suffix = ".png"
            reference_path = temp_dir / f"reference{suffix}"
            reference_path.write_bytes(base_image_bytes)
            command.extend(["--reference", str(reference_path)])

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        process_env = os.environ.copy()
        process_env["PYTHONNOUSERSITE"] = "1"
        process_env["PYTORCH_ALLOC_CONF"] = "backend:cudaMallocAsync"
        process_env["CUDA_MODULE_LOADING"] = "LAZY"
        process_env["TOKENIZERS_PARALLELISM"] = "false"
        process_env["HF_HUB_OFFLINE"] = "1"
        process_env["TRANSFORMERS_OFFLINE"] = "1"
        process_env["OMP_NUM_THREADS"] = "16"
        prompt_id = ""
        highest_progress = 4
        stream_modes = ["auto", "off"] if width <= 832 and height <= 480 else ["off"]
        with log_path.open("w", encoding="utf-8", newline="\n") as log_handle:
            for attempt_index, stream_mode in enumerate(stream_modes):
                attempt_command = list(command)
                attempt_command[attempt_command.index("--offload-stream") + 1] = stream_mode
                if attempt_index:
                    retry_message = (
                        "OOM detectado no prefetch; reiniciando automaticamente com offload sequencial seguro."
                    )
                    log_handle.write(f"MAESTRO_RETRY\t{retry_message}\n")
                    log_handle.flush()
                    if progress_cb:
                        progress_cb(max(18, highest_progress), retry_message)
                process = subprocess.Popen(
                    attempt_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creationflags,
                    env=process_env,
                )
                if process_cb:
                    process_cb(process)
                prompt_id = f"mova:{process.pid}"
                tail: list[str] = []
                try:
                    assert process.stdout is not None
                    log_handle.write(f"MAESTRO_ATTEMPT\t{attempt_index + 1}\toffload_stream={stream_mode}\n")
                    log_handle.flush()
                    for line in process.stdout:
                        log_handle.write(line)
                        log_handle.flush()
                        clean = line.strip()
                        if clean:
                            tail.append(clean)
                            tail = tail[-40:]
                        parsed = _parse_progress(line)
                        if parsed and progress_cb:
                            highest_progress = max(highest_progress, parsed[0])
                            progress_cb(highest_progress, parsed[1])
                        if cancel_event is not None and cancel_event.is_set():
                            _terminate_process(process)
                            raise RuntimeError("Geracao MOVA cancelada pelo proprietario.")
                    return_code = process.wait()
                finally:
                    if process_cb:
                        process_cb(None)

                if return_code == 0:
                    break
                detail = " | ".join(tail[-8:])[-1800:]
                is_oom = bool(
                    re.search(
                        r"outofmemory|out of memory|allocation on device .* exceed|cuda error: memory",
                        detail,
                        flags=re.IGNORECASE,
                    )
                )
                if attempt_index == 0 and len(stream_modes) > 1 and is_oom:
                    continue
                raise RuntimeError(f"MOVA terminou com codigo {return_code}: {detail}")
            else:
                raise RuntimeError("MOVA esgotou as tentativas de offload sem concluir.")
        if not output_path.is_file() or output_path.stat().st_size < 1024:
            raise RuntimeError("MOVA terminou sem produzir um MP4 valido.")
        if progress_cb:
            if (width, height) == (832, 480):
                progress_cb(99, "Candidato MP4 480p pronto para aprovacao; upscale nao iniciado.")
            else:
                progress_cb(99, f"MP4 {width}x{height} com audio sincronizado pronto.")
        return prompt_id, [
            _output_item(
                output_path,
                output_root,
                fps=fps,
                width=width,
                height=height,
            )
        ]


def write_runtime_marker(payload: dict[str, Any]) -> None:
    """Used by the setup script/tests after dependency preflight succeeds."""

    MOVA_ENGINE_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = MOVA_RUNTIME_MARKER.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, MOVA_RUNTIME_MARKER)
