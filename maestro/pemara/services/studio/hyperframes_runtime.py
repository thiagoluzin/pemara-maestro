"""Runtime local e controlado do HyperFrames dentro do Maestro."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


MAESTRO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = (
    MAESTRO_ROOT
    / "ferramentas"
    / "video_global_engine"
    / "engines"
    / "hyperframes"
)
PROJECT_ID = os.environ.get("HYPERFRAMES_PROJECT", "maestro-pilot").strip() or "maestro-pilot"
PROJECT_ROOT = ENGINE_ROOT / "projects" / PROJECT_ID
PREVIEW_PORT = int(os.environ.get("HYPERFRAMES_PORT", "8032"))
PUBLIC_URL = os.environ.get(
    "HYPERFRAMES_PUBLIC_URL",
    "https://hyperframes.pemaratech.com.br/",
).strip()
CLI = ENGINE_ROOT / "node_modules" / ".bin" / (
    "hyperframes.cmd" if os.name == "nt" else "hyperframes"
)
PACKAGE_JSON = ENGINE_ROOT / "node_modules" / "hyperframes" / "package.json"
OUTPUT_PATH = PROJECT_ROOT / "renders" / "maestro-hyperframes-pilot.mp4"
RUNTIME_DIR = MAESTRO_ROOT / "dados" / "studio" / "hyperframes"
JOB_FILE = RUNTIME_DIR / "render_job.json"
RENDER_LOG = RUNTIME_DIR / "render.log"

_preview_lock = threading.Lock()
_render_lock = threading.Lock()
_last_preview_error = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hidden_creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _port_open(port: int = PREVIEW_PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.75):
            return True
    except OSError:
        return False


def preview_online(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{PREVIEW_PORT}/",
            timeout=timeout,
        ) as response:
            return 200 <= int(response.status) < 500
    except (OSError, urllib.error.URLError, ValueError):
        return False


def _version() -> str:
    try:
        data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
        return str(data.get("version") or "")
    except (OSError, json.JSONDecodeError, TypeError):
        return ""


def _load_job() -> Dict[str, Any]:
    try:
        data = json.loads(JOB_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_job(job: Dict[str, Any]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    temp = JOB_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, JOB_FILE)


def status() -> Dict[str, Any]:
    job = _load_job()
    online = preview_online()
    output_exists = OUTPUT_PATH.is_file()
    output_size = OUTPUT_PATH.stat().st_size if output_exists else 0
    return {
        "ok": online,
        "installed": CLI.is_file() and PROJECT_ROOT.is_dir(),
        "online": online,
        "portOpen": _port_open(),
        "port": PREVIEW_PORT,
        "bind": "127.0.0.1",
        "publicUrl": PUBLIC_URL,
        "version": _version(),
        "project": PROJECT_ID,
        "projectRoot": str(PROJECT_ROOT),
        "output": {
            "available": output_exists,
            "name": OUTPUT_PATH.name,
            "bytes": output_size,
        },
        "render": job,
        "lastPreviewError": _last_preview_error,
        "rules": {
            "autoStartWithMaestro": True,
            "watchdogEveryMinutes": 5,
            "localOnlyOrigin": True,
            "authenticatedGateway": True,
            "browserGpu": False,
            "humanQcRequired": True,
        },
    }


def ensure_preview() -> Dict[str, Any]:
    global _last_preview_error
    with _preview_lock:
        if preview_online():
            _last_preview_error = ""
            return status()
        if _port_open():
            _last_preview_error = (
                f"A porta {PREVIEW_PORT} esta ocupada por um processo que nao respondeu como HyperFrames."
            )
            return status()
        if not CLI.is_file() or not PROJECT_ROOT.is_dir():
            _last_preview_error = "Instalacao ou projeto HyperFrames nao encontrado."
            return status()

        command = [
            str(CLI),
            "preview",
            str(PROJECT_ROOT),
            "--port",
            str(PREVIEW_PORT),
            "--no-open",
            "--no-browser-gpu",
            "--background",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(ENGINE_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
                check=False,
                creationflags=_hidden_creationflags(),
            )
            if completed.returncode != 0:
                _last_preview_error = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or f"HyperFrames encerrou com codigo {completed.returncode}."
                )[-1200:]
                return status()
            for _ in range(30):
                if preview_online(timeout=1.0):
                    _last_preview_error = ""
                    return status()
                time.sleep(0.5)
            _last_preview_error = "HyperFrames iniciou, mas nao respondeu dentro de 15 segundos."
        except (OSError, subprocess.SubprocessError) as exc:
            _last_preview_error = str(exc)[-1200:]
        return status()


def ensure_preview_async() -> None:
    threading.Thread(
        target=ensure_preview,
        daemon=True,
        name="studio-hyperframes-startup",
    ).start()


def _render_worker(job_id: str) -> None:
    with _render_lock:
        job = {
            "id": job_id,
            "status": "checking",
            "progress": 10,
            "message": "Validando composicao antes do render.",
            "startedAt": _utc_now(),
        }
        _save_job(job)
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        commands = [
            [
                str(CLI),
                "check",
                str(PROJECT_ROOT),
                "--snapshots",
                "--no-browser-gpu",
                "--json",
            ],
            [
                str(CLI),
                "render",
                str(PROJECT_ROOT),
                "--output",
                str(OUTPUT_PATH),
                "--fps",
                "30",
                "--quality",
                "high",
                "--workers",
                "1",
                "--no-browser-gpu",
                "--strict",
            ],
        ]
        try:
            with RENDER_LOG.open("a", encoding="utf-8") as log_handle:
                for index, command in enumerate(commands):
                    if index == 1:
                        job.update(
                            status="rendering",
                            progress=35,
                            message="Renderizando por software, sem disputar a GPU do ComfyUI.",
                        )
                        _save_job(job)
                    completed = subprocess.run(
                        command,
                        cwd=str(ENGINE_ROOT),
                        stdout=log_handle,
                        stderr=subprocess.STDOUT,
                        timeout=60 * 45,
                        check=False,
                        creationflags=_hidden_creationflags(),
                    )
                    if completed.returncode != 0:
                        stage = "validacao" if index == 0 else "renderizacao"
                        raise RuntimeError(f"Falha na {stage}; consulte {RENDER_LOG.name}.")
            if not OUTPUT_PATH.is_file() or OUTPUT_PATH.stat().st_size <= 0:
                raise RuntimeError("O render terminou sem produzir o MP4 esperado.")
            job.update(
                status="ready_pending_human_qc",
                progress=100,
                message="MP4 pronto. Aprovacao visual humana ainda e obrigatoria.",
                finishedAt=_utc_now(),
                outputName=OUTPUT_PATH.name,
                outputBytes=OUTPUT_PATH.stat().st_size,
            )
        except Exception as exc:
            job.update(
                status="error",
                progress=100,
                message=str(exc),
                finishedAt=_utc_now(),
            )
        _save_job(job)


def start_render() -> Dict[str, Any]:
    installed = CLI.is_file() and PROJECT_ROOT.is_dir()
    if not installed:
        raise RuntimeError("HyperFrames nao esta instalado corretamente.")
    current = _load_job()
    if current.get("status") in {"queued", "checking", "rendering"}:
        return current
    job_id = uuid.uuid4().hex
    queued = {
        "id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Render reservado.",
        "createdAt": _utc_now(),
    }
    _save_job(queued)
    threading.Thread(
        target=_render_worker,
        args=(job_id,),
        daemon=True,
        name=f"studio-hyperframes-render-{job_id[:8]}",
    ).start()
    return queued
