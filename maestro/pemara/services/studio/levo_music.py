"""Runtime isolado do Tencent SongGeneration LeVo 2 para o Maestro.

Este modulo apenas orquestra pesos neurais treinados. Ele nao sintetiza,
mistura ou processa audio por DSP procedural.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Tuple


LEVO2_PROVIDER_ID = "levo2_local"
LEVO2_MODEL_LABEL = "Tencent SongGeneration LeVo 2 v2-large"
LEVO2_MIN_PILOT_SECONDS = 5
LEVO2_MAX_PILOT_SECONDS = 15
LEVO2_DEFAULT_PILOT_SECONDS = 15
LEVO2_LICENSE_SCOPE = "internal_noncommercial_research_only"

_LEVO2_LOCK = threading.Lock()


def _app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runtime_paths(app_root: Path | None = None) -> Dict[str, Path]:
    root = (app_root or _app_root()).resolve()
    neural = root / "ferramentas" / "audio_neural"
    base = neural / "LeVo2_comfy"
    return {
        "root": root,
        "python": neural / "venv_songgen" / "Scripts" / "python.exe",
        "comfy_main": neural / "ComfyUI_official" / "main.py",
        "base": base,
        "output": base / "output",
        "logs": base / "logs" / "maestro",
        "weight": base / "models" / "SongGeneration" / "large_model_v2.pt",
        "prompt": base / "models" / "SongGeneration" / "new_prompt.pt",
        "vae": base / "models" / "vae" / "autoencoder_music_1320k.ckpt",
        "stage1": base / "models" / "SongGeneration" / "ckpt" / "model_septoken" / "model_2.safetensors",
        "stage1_fixed": base / "models" / "SongGeneration" / "ckpt" / "model_1rvq" / "model_2_fixed.safetensors",
        "custom_node": base / "custom_nodes" / "ComfyUI_SongGeneration" / "SongGeneration_node.py",
    }


def _enabled() -> bool:
    return os.environ.get("LEVO2_ENABLED", "1").strip().lower() in {"1", "true", "yes", "sim", "on"}


def _port() -> int:
    try:
        return max(1024, min(65535, int(os.environ.get("LEVO2_PORT", "8190"))))
    except ValueError:
        return 8190


def _base_url() -> str:
    return f"http://127.0.0.1:{_port()}"


def _required_files_present(paths: Dict[str, Path]) -> Tuple[bool, list[str]]:
    requirements = {
        "runtime Python": (paths["python"], 1),
        "runtime ComfyUI": (paths["comfy_main"], 1),
        "modelo LeVo 2": (paths["weight"], 12_000_000_000),
        "condicionador": (paths["prompt"], 10_000_000),
        "autoencoder": (paths["vae"], 600_000_000),
        "tokenizador principal": (paths["stage1"], 4_000_000_000),
        "tokenizador auxiliar": (paths["stage1_fixed"], 4_000_000_000),
        "node SongGeneration": (paths["custom_node"], 1),
    }
    missing = []
    for label, (path, minimum_size) in requirements.items():
        try:
            valid = path.is_file() and path.stat().st_size >= minimum_size
        except OSError:
            valid = False
        if not valid:
            missing.append(label)
    return not missing, missing


def _request(path: str, payload: Dict[str, Any] | None = None, *, timeout: float = 10.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(f"{_base_url()}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LeVo 2 HTTP {exc.code}: {body[:800]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Runtime local do LeVo 2 indisponivel.") from exc
    return json.loads(raw.decode("utf-8")) if raw else {}


def _runtime_online() -> bool:
    try:
        return bool(_request("/system_stats", timeout=1.5))
    except Exception:
        return False


def _gpu_snapshot() -> Dict[str, int | None]:
    command = [
        "nvidia-smi",
        "--query-gpu=memory.free,memory.used,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=True)
        values = [int(part.strip()) for part in result.stdout.splitlines()[0].split(",")[:3]]
        return {"free_vram_mb": values[0], "used_vram_mb": values[1], "utilization_percent": values[2]}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return {"free_vram_mb": None, "used_vram_mb": None, "utilization_percent": None}


def levo2_status(app_root: Path | None = None) -> Dict[str, Any]:
    paths = _runtime_paths(app_root)
    installed, missing = _required_files_present(paths)
    enabled = _enabled()
    online = _runtime_online() if installed and app_root is None else False
    gpu = _gpu_snapshot() if installed and app_root is None else {
        "free_vram_mb": None,
        "used_vram_mb": None,
        "utilization_percent": None,
    }
    minimum_vram = int(os.environ.get("LEVO2_MIN_FREE_VRAM_MB", "20000"))
    free_vram = gpu.get("free_vram_mb")
    ready = bool(enabled and installed)
    if not enabled:
        message = "LeVo 2 local foi desativado na configuracao do Maestro."
    elif not installed:
        message = "Instalacao LeVo 2 incompleta: " + ", ".join(missing) + "."
    elif free_vram is not None and int(free_vram) < minimum_vram and not online:
        message = "Modelo instalado; a GPU esta ocupada e sera verificada novamente ao gerar."
    else:
        message = "Modelo local instalado; pronto para gerar um piloto neural."
    return {
        "label": "LeVo 2 local (RTX 5090)",
        "configured": ready,
        "installed": installed,
        "runtime_online": online,
        "role": "music_local_neural_pilot",
        "modes": ["music"],
        "needs": [] if ready else (["LEVO2_ENABLED=1"] if installed else missing),
        "formats": ["flac"],
        "min_duration_seconds": LEVO2_MIN_PILOT_SECONDS,
        "max_duration_seconds": LEVO2_MAX_PILOT_SECONDS,
        "default_duration_seconds": LEVO2_DEFAULT_PILOT_SECONDS,
        "pilot_only": True,
        "requires_human_listening": True,
        "license_scope": LEVO2_LICENSE_SCOPE,
        "model": LEVO2_MODEL_LABEL,
        "message": message,
        "gpu": {
            "free_vram_mb": free_vram,
            "minimum_free_vram_mb": minimum_vram,
            "utilization_percent": gpu.get("utilization_percent"),
        },
    }


def _bounded_duration(value: float) -> int:
    try:
        duration = int(round(float(value)))
    except (TypeError, ValueError):
        duration = LEVO2_DEFAULT_PILOT_SECONDS
    if duration < LEVO2_MIN_PILOT_SECONDS or duration > LEVO2_MAX_PILOT_SECONDS:
        raise ValueError(
            f"O primeiro LeVo 2 deve ser um piloto de {LEVO2_MIN_PILOT_SECONDS} a "
            f"{LEVO2_MAX_PILOT_SECONDS} segundos para escuta humana."
        )
    return duration


def build_levo2_workflow(prompt: str, negative: str, duration: float, filename_prefix: str,
                        *, lyrics: str = "", instrumental: bool = True) -> Dict[str, Any]:
    description = " ".join(str(prompt or "").split())[:1800]
    avoid = " ".join(str(negative or "").split())[:500]
    if not description:
        raise ValueError("Descreva a musica que o LeVo 2 deve compor.")
    if avoid:
        description = f"{description}. Avoid these elements: {avoid}"
    seconds = _bounded_duration(duration)
    if not instrumental and not lyrics.strip():
        raise ValueError("LeVo 2 vocal exige uma letra.")
    lyric = "[intro-short] ; [inst-medium] ; [inst-medium] ; [outro-short]" if instrumental else "; ".join(
        part.strip() for part in re.split(r"(?=\[)", re.sub(r"\[([^]]+)\]", lambda m: m[0].lower(), lyrics)) if part.strip())
    return {
        "1": {
            "class_type": "SongGeneration_Loader",
            "inputs": {
                "infer_model": "large_model_v2.pt",
                "gguf": "none",
                "version": "v2",
                "use_flash_attn": False,
                "offload_audiolm": True,
            },
        },
        "2": {
            "class_type": "SongGeneration_Stage1",
            "inputs": {
                "vae": "autoencoder_music_1320k.ckpt",
                "seperate_model": "ckpt\\model_septoken\\model_2.safetensors",
                "prompt_pt": "new_prompt.pt",
                "auto_prompt_audio_type": "Soundtrack",
                "model_1rvq": "ckpt\\model_1rvq\\model_2_fixed.safetensors",
                "demucs_pt": "none",
                "lyric": lyric,
            },
        },
        "3": {
            "class_type": "SongGeneration_Stage2",
            "inputs": {
                "model": ["1", 0],
                "cfg": ["1", 1],
                "cond": ["2", 0],
                "gen_type": "bgm" if instrumental else "mixed",
                "description": description,
                "duration_seconds": seconds,
                "cfg_coef": 1.5,
                "temp": 0.9,
                "top_k": 50,
                "top_p": 0.0,
                "record_tokens": True,
                "record_window": 50,
            },
        },
        "4": {
            "class_type": "SongGeneration_Sampler",
            "inputs": {"cond": ["3", 0], "save_separate": False},
        },
        "5": {
            "class_type": "SaveAudio",
            "inputs": {"audio": ["4", 0], "filename_prefix": filename_prefix},
        },
    }


def _check_main_comfy_idle(main_comfy_url: str) -> None:
    url = f"{main_comfy_url.rstrip('/')}/queue"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            queue = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        return
    if list(queue.get("queue_running") or []) or list(queue.get("queue_pending") or []):
        raise RuntimeError("LeVo 2 aguardando GPU: finalize ou cancele a fila atual do ComfyUI.")


def _check_gpu_headroom() -> None:
    gpu = _gpu_snapshot()
    free_vram = gpu.get("free_vram_mb")
    minimum = int(os.environ.get("LEVO2_MIN_FREE_VRAM_MB", "20000"))
    if free_vram is None:
        raise RuntimeError("Nao foi possivel medir a VRAM antes de iniciar o LeVo 2.")
    if int(free_vram) < minimum:
        raise RuntimeError(
            f"LeVo 2 aguardando GPU: {int(free_vram)} MB livres; minimo seguro {minimum} MB."
        )


def _start_runtime(paths: Dict[str, Path], process_cb=None) -> subprocess.Popen:
    paths["logs"].mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stdout_path = paths["logs"] / f"levo2_{stamp}.stdout.log"
    stderr_path = paths["logs"] / f"levo2_{stamp}.stderr.log"
    stdout_handle = open(stdout_path, "ab", buffering=0)
    stderr_handle = open(stderr_path, "ab", buffering=0)
    command = [
        str(paths["python"]),
        str(paths["comfy_main"]),
        "--base-directory", str(paths["base"]),
        "--listen", "127.0.0.1",
        "--port", str(_port()),
        "--disable-auto-launch",
        "--disable-metadata",
        "--preview-method", "none",
    ]
    environment = os.environ.copy()
    environment["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    environment["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            command,
            cwd=str(paths["comfy_main"].parent),
            env=environment,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creation_flags,
        )
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        raise
    process._maestro_log_handles = (stdout_handle, stderr_handle)  # type: ignore[attr-defined]
    if process_cb:
        process_cb(process)
    return process


def _wait_runtime(process: subprocess.Popen, cancel_event: threading.Event | None, progress_cb=None) -> None:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("Geracao LeVo 2 cancelada pelo proprietario.")
        if process.poll() is not None:
            raise RuntimeError("O runtime isolado do LeVo 2 encerrou durante a inicializacao.")
        if _runtime_online():
            return
        if progress_cb:
            elapsed = 180 - max(0, int(deadline - time.monotonic()))
            progress_cb(min(12, 3 + elapsed // 20), "Carregando o runtime neural LeVo 2.")
        time.sleep(2)
    raise TimeoutError("LeVo 2 nao ficou pronto dentro de 180 segundos.")


def _stop_runtime(process: subprocess.Popen | None, *, owned: bool, process_cb=None) -> None:
    try:
        if _runtime_online():
            try:
                _request("/free", {"unload_models": True, "free_memory": True}, timeout=12)
            except Exception:
                pass
        if owned and process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    finally:
        if process_cb:
            process_cb(None)
        if process is not None:
            for handle in getattr(process, "_maestro_log_handles", ()):
                try:
                    handle.close()
                except OSError:
                    pass


def _history_audio(prompt_id: str) -> Dict[str, str] | None:
    history = _request(f"/history/{urllib.parse.quote(prompt_id)}", timeout=20)
    item = history.get(prompt_id) or {}
    for node in (item.get("outputs") or {}).values():
        for output in list(node.get("audio") or []) + list(node.get("audios") or []):
            if output.get("filename"):
                return {
                    "filename": str(output["filename"]),
                    "subfolder": str(output.get("subfolder") or ""),
                    "type": str(output.get("type") or "output"),
                }
    status = item.get("status") or {}
    if status.get("status_str") == "error":
        raise RuntimeError("LeVo 2 falhou ao executar o workflow neural; consulte o log local do runtime.")
    if status.get("completed"):
        raise RuntimeError("LeVo 2 concluiu o workflow sem entregar um arquivo de audio.")
    return None


def _safe_output_path(paths: Dict[str, Path], item: Dict[str, str]) -> Path:
    if item.get("type") != "output":
        raise RuntimeError("LeVo 2 retornou um tipo de saida inesperado.")
    root = paths["output"].resolve()
    candidate = (root / item.get("subfolder", "") / item["filename"]).resolve()
    if root != candidate and root not in candidate.parents:
        raise RuntimeError("LeVo 2 retornou uma saida fora do diretorio permitido.")
    if not candidate.is_file() or candidate.stat().st_size < 1024:
        raise RuntimeError("LeVo 2 concluiu sem entregar um arquivo de audio valido.")
    return candidate


def run_levo2_music(
    *,
    prompt: str,
    negative: str,
    duration: float,
    main_comfy_url: str,
    lyrics: str = "",
    instrumental: bool = True,
    progress_cb: Callable[[int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
    process_cb=None,
) -> Dict[str, Any]:
    """Gera um piloto vocal ou instrumental e devolve seus bytes ao Studio."""

    paths = _runtime_paths()
    installed, missing = _required_files_present(paths)
    if not _enabled():
        raise RuntimeError("LeVo 2 local esta desativado no Maestro.")
    if not installed:
        raise RuntimeError("Instalacao LeVo 2 incompleta: " + ", ".join(missing) + ".")
    seconds = _bounded_duration(duration)
    acquired = False
    while not acquired:
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("Geracao LeVo 2 cancelada enquanto aguardava a fila serial.")
        acquired = _LEVO2_LOCK.acquire(timeout=0.5)
        if not acquired and progress_cb:
            progress_cb(1, "Na fila serial; aguardando o piloto LeVo 2 anterior.")
    process = None
    owned_runtime = False
    try:
        if progress_cb:
            progress_cb(2, "Validando fila e memoria da RTX 5090.")
        _check_main_comfy_idle(main_comfy_url)
        _check_gpu_headroom()
        if not _runtime_online():
            process = _start_runtime(paths, process_cb=process_cb)
            owned_runtime = True
            _wait_runtime(process, cancel_event, progress_cb=progress_cb)
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("Geracao LeVo 2 cancelada pelo proprietario.")
        token = uuid.uuid4().hex[:12]
        prefix = f"maestro_generative/music/levo2_pilot_{token}"
        workflow = build_levo2_workflow(prompt, negative, seconds, prefix, lyrics=lyrics, instrumental=instrumental)
        if progress_cb:
            progress_cb(14, "Enviando o piloto ao LeVo 2.")
        queued = _request(
            "/prompt",
            {"prompt": workflow, "client_id": f"maestro-levo2-{token}"},
            timeout=30,
        )
        prompt_id = str(queued.get("prompt_id") or "")
        if not prompt_id:
            raise RuntimeError("LeVo 2 nao retornou o identificador da geracao.")
        deadline = time.monotonic() + 900
        audio_item = None
        while time.monotonic() < deadline:
            if cancel_event is not None and cancel_event.is_set():
                try:
                    _request("/interrupt", {}, timeout=5)
                except Exception:
                    pass
                raise RuntimeError("Geracao LeVo 2 cancelada pelo proprietario.")
            audio_item = _history_audio(prompt_id)
            if audio_item:
                break
            if owned_runtime and process is not None and process.poll() is not None:
                raise RuntimeError("O runtime LeVo 2 encerrou antes de entregar o audio.")
            if progress_cb:
                elapsed = 900 - max(0, int(deadline - time.monotonic()))
                progress_cb(min(94, 16 + elapsed // 11), "Compondo o piloto neural no LeVo 2.")
            time.sleep(3)
        if not audio_item:
            raise TimeoutError("LeVo 2 excedeu 15 minutos sem entregar o piloto.")
        source = _safe_output_path(paths, audio_item)
        media_type = mimetypes.guess_type(source.name)[0] or "audio/flac"
        if progress_cb:
            progress_cb(96, "Piloto pronto; preparando o player para escuta humana.")
        return {
            "data": source.read_bytes(),
            "extension": source.suffix.lower() or ".flac",
            "media_type": media_type,
            "duration_seconds": seconds,
            "model": LEVO2_MODEL_LABEL,
        }
    finally:
        try:
            _stop_runtime(process, owned=owned_runtime, process_cb=process_cb)
        finally:
            _LEVO2_LOCK.release()
