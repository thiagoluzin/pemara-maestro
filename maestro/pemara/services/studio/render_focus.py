"""Safe, measurable system preparation for long local GPU renders.

The focus pass only stops explicitly recognised, idle secondary ComfyUI
runtimes. Unknown processes are reported and preserved. Every pass writes a
receipt so performance changes can be compared instead of guessed.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import psutil


class RenderFocusBlocked(RuntimeError):
    """The machine is not in a safe state to submit another GPU workflow."""


def _enabled(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "sim", "on"}


def _secondary_ports() -> set[int]:
    raw = os.environ.get("MAESTRO_RENDER_FOCUS_SECONDARY_COMFY_PORTS", "8190")
    ports: set[int] = set()
    for value in raw.split(","):
        try:
            port = int(value.strip())
        except ValueError:
            continue
        if 1024 <= port <= 65535 and port not in {8029, 8188}:
            ports.add(port)
    return ports


def _json_request(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 3.0) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    return decoded if isinstance(decoded, dict) else {}


def _comfy_queue_is_idle(port: int) -> bool:
    try:
        queue = _json_request(f"http://127.0.0.1:{port}/queue")
    except (OSError, ValueError, urllib.error.URLError):
        return False
    return not queue.get("queue_running") and not queue.get("queue_pending")


def _command_line(process: psutil.Process) -> str:
    try:
        return " ".join(process.cmdline())
    except (psutil.Error, OSError):
        return ""


def _is_managed_secondary_comfy(command_line: str, port: int, workspace_root: Path) -> bool:
    normalized = command_line.casefold().replace("/", "\\")
    root = str(workspace_root.resolve()).casefold().replace("/", "\\")
    return (
        root in normalized
        and "comfyui" in normalized
        and "main.py" in normalized
        and (f"--port {port}" in normalized or f"--port={port}" in normalized)
    )


def _gpu_snapshot() -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,power.draw,power.limit,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc)}
    if result.returncode != 0:
        return {"available": False, "error": (result.stderr or result.stdout).strip()[-500:]}
    values = [item.strip() for item in result.stdout.strip().split(",")]
    if len(values) != 8:
        return {"available": False, "error": "nvidia-smi returned an unexpected shape"}
    numeric = []
    for value in values[1:]:
        try:
            numeric.append(float(value))
        except ValueError:
            numeric.append(None)
    return {
        "available": True,
        "name": values[0],
        "memoryTotalMb": numeric[0],
        "memoryUsedMb": numeric[1],
        "memoryFreeMb": numeric[2],
        "utilizationPercent": numeric[3],
        "powerDrawW": numeric[4],
        "powerLimitW": numeric[5],
        "temperatureC": numeric[6],
    }


def _system_snapshot() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    processes: list[dict[str, Any]] = []
    for process in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            rss = int(process.info["memory_info"].rss)
            processes.append({
                "pid": process.pid,
                "name": str(process.info.get("name") or ""),
                "rssMb": round(rss / 1024**2, 1),
            })
        except (psutil.Error, AttributeError, OSError):
            continue
    processes.sort(key=lambda item: item["rssMb"], reverse=True)
    return {
        "capturedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "cpuPercent": psutil.cpu_percent(interval=None),
        "ramTotalGb": round(memory.total / 1024**3, 2),
        "ramAvailableGb": round(memory.available / 1024**3, 2),
        "ramPercent": float(memory.percent),
        "gpu": _gpu_snapshot(),
        "topMemoryProcesses": processes[:12],
    }


def _stop_idle_secondary_comfy(workspace_root: Path, *, dry_run: bool) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for port in sorted(_secondary_ports()):
        matches: list[psutil.Process] = []
        for process in psutil.process_iter(["pid"]):
            command_line = _command_line(process)
            if _is_managed_secondary_comfy(command_line, port, workspace_root):
                matches.append(process)
        if not matches:
            continue
        if not _comfy_queue_is_idle(port):
            raise RenderFocusBlocked(
                f"O ComfyUI secundario da porta {port} possui trabalho ativo ou nao respondeu; processo preservado."
            )
        pids = sorted({process.pid for process in matches})
        action = {"action": "stop_idle_secondary_comfy", "port": port, "pids": pids, "dryRun": dry_run}
        if not dry_run:
            for process in matches:
                try:
                    process.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            _gone, alive = psutil.wait_procs(matches, timeout=8)
            for process in alive:
                # The target was proved to be the exact idle, project-owned
                # secondary runtime. Force is bounded to those exact PIDs.
                try:
                    process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            action["stopped"] = not any(psutil.pid_exists(pid) for pid in pids)
        actions.append(action)
    return actions


def _unload_ollama_models() -> list[dict[str, Any]]:
    if not _enabled("MAESTRO_RENDER_FOCUS_UNLOAD_OLLAMA", "1"):
        return []
    base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11435").rstrip("/")
    try:
        payload = _json_request(f"{base}/api/ps")
    except (OSError, ValueError, urllib.error.URLError):
        return []
    actions: list[dict[str, Any]] = []
    for item in payload.get("models", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("model") or "").strip()
        if not name:
            continue
        try:
            _json_request(
                f"{base}/api/generate",
                method="POST",
                payload={"model": name, "keep_alive": 0},
                timeout=15,
            )
            actions.append({"action": "unload_ollama_model", "model": name, "ok": True})
        except (OSError, ValueError, urllib.error.URLError) as exc:
            actions.append({"action": "unload_ollama_model", "model": name, "ok": False, "error": str(exc)})
    return actions


def _prioritize_primary_comfy() -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    try:
        listeners = psutil.net_connections(kind="tcp")
    except (psutil.Error, OSError):
        return actions
    pids = {item.pid for item in listeners if item.laddr and item.laddr.port == 8188 and item.pid}
    for pid in sorted(pids):
        try:
            process = psutil.Process(pid)
            previous = process.nice()
            if os.name == "nt":
                process.nice(psutil.HIGH_PRIORITY_CLASS)
            actions.append({"action": "prioritize_primary_comfy", "pid": pid, "previous": int(previous), "ok": True})
        except (psutil.Error, OSError) as exc:
            actions.append({"action": "prioritize_primary_comfy", "pid": pid, "ok": False, "error": str(exc)})
    return actions


def prepare_render_focus(
    workspace_root: Path,
    *,
    job_id: str,
    dry_run: bool = False,
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """Prepare the host immediately before a serial video job is submitted."""

    workspace_root = Path(workspace_root).resolve()
    before = _system_snapshot()
    actions: list[dict[str, Any]] = []
    enabled = _enabled("MAESTRO_RENDER_FOCUS_ENABLED", "1")
    if enabled:
        if progress_cb:
            progress_cb(3, "Modo render: varrendo GPU, RAM e runtimes concorrentes.")
        actions.extend(_stop_idle_secondary_comfy(workspace_root, dry_run=dry_run))
        if not dry_run:
            actions.extend(_unload_ollama_models())
            actions.extend(_prioritize_primary_comfy())
    after = _system_snapshot()
    blockers: list[str] = []
    warnings: list[str] = []
    if after["ramAvailableGb"] < float(os.environ.get("MAESTRO_RENDER_FOCUS_MIN_FREE_RAM_GB", "16")):
        blockers.append(f"RAM livre insuficiente: {after['ramAvailableGb']} GiB")
    gpu = after.get("gpu") or {}
    if gpu.get("available") and float(gpu.get("utilizationPercent") or 0) >= 95:
        # A single nvidia-smi sample can catch Desktop Window Manager or a
        # transient preview spike. The exclusive Maestro/Comfy queue gates are
        # authoritative; preserve this sample as evidence without a false stop.
        warnings.append(f"GPU estava a {gpu.get('utilizationPercent')}% na amostra instantanea")
    receipt = {
        "version": "maestro-render-focus-v1",
        "jobId": str(job_id),
        "enabled": enabled,
        "dryRun": bool(dry_run),
        "ready": not blockers,
        "before": before,
        "after": after,
        "actions": actions,
        "blockers": blockers,
        "warnings": warnings,
        "preservationPolicy": "unknown processes, Windows, Maestro, Codex and primary ComfyUI are never terminated",
    }
    receipt_dir = workspace_root / "dados" / "logs" / "render_focus"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{str(job_id)}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt["receiptPath"] = str(receipt_path)
    if blockers:
        raise RenderFocusBlocked("; ".join(blockers))
    if progress_cb:
        progress_cb(4, "Modo render pronto; recursos concorrentes seguros foram liberados.")
    return receipt
