from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
TAKE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class AnchorExecutorManager:
    """Launch one resilient ANCHOR executor per canonical video project."""

    def __init__(self, video_engine_root: Path, *, python_executable: str | None = None):
        self.video_engine_root = Path(video_engine_root).resolve()
        self.projects_root = (self.video_engine_root / "projetos").resolve()
        self.tool_path = (self.video_engine_root / "tools" / "execute_anchor_queue.py").resolve()
        self.python_executable = str(python_executable or sys.executable)
        self._lock = threading.Lock()
        self._processes: dict[str, subprocess.Popen[Any]] = {}

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _pid_is_running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        return True

    def _project_dir(self, project_id: str) -> Path:
        project_id = str(project_id or "").strip()
        if not PROJECT_ID_RE.fullmatch(project_id):
            raise ValueError("projectId invalido para o executor de fotos-base.")
        project_dir = (self.projects_root / project_id).resolve()
        if project_dir.parent != self.projects_root or not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        if not (project_dir / "take_queue.json").is_file():
            raise FileNotFoundError(f"Fila canonica ausente para {project_id}.")
        if not self.tool_path.is_file():
            raise FileNotFoundError("Executor canonico de fotos-base nao encontrado.")
        return project_dir

    @staticmethod
    def _normalize_take_ids(take_ids: list[str] | None) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_take_id in take_ids or []:
            take_id = str(raw_take_id or "").strip()
            if not TAKE_ID_RE.fullmatch(take_id):
                raise ValueError(f"takeId invalido: {take_id or '(vazio)'}")
            canonical = take_id.upper()
            if canonical not in seen:
                seen.add(canonical)
                normalized.append(take_id)
        if len(normalized) > 100:
            raise ValueError("O executor aceita no maximo 100 takes por chamada.")
        return normalized

    def _persisted_lock_status(self, project_dir: Path) -> dict[str, Any] | None:
        lock_path = project_dir / "tools" / "anchor_executor.lock"
        if not lock_path.is_file():
            return None
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        pid = int(payload.get("pid", 0) or 0)
        if not self._pid_is_running(pid):
            lock_path.unlink(missing_ok=True)
            return None
        return {
            "status": "running",
            "pid": pid,
            "projectId": project_dir.name,
            "startedAt": str(payload.get("started_at") or ""),
            "alreadyRunning": True,
        }

    @staticmethod
    def _intent_path(project_dir: Path) -> Path:
        return project_dir / "tools" / "anchor_executor_intent.json"

    def _write_intent(self, project_dir: Path, take_ids: list[str]) -> Path:
        intent_path = self._intent_path(project_dir)
        intent_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = intent_path.with_suffix(".json.tmp")
        payload = {
            "schemaVersion": 1,
            "projectId": project_dir.name,
            "takeIds": list(take_ids),
            "authorizedAt": self._utc_now(),
        }
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, intent_path)
        return intent_path

    def _read_intent(self, project_dir: Path) -> list[str] | None:
        intent_path = self._intent_path(project_dir)
        if not intent_path.is_file():
            return None
        try:
            payload = json.loads(intent_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if str(payload.get("projectId") or "") != project_dir.name:
            return None
        raw_take_ids = payload.get("takeIds")
        if not isinstance(raw_take_ids, list):
            return None
        return self._normalize_take_ids([str(item) for item in raw_take_ids])

    def status(self, project_id: str) -> dict[str, Any]:
        project_dir = self._project_dir(project_id)
        with self._lock:
            process = self._processes.get(project_dir.name)
            if process is not None and process.poll() is None:
                return {
                    "status": "running",
                    "pid": int(process.pid),
                    "projectId": project_dir.name,
                    "alreadyRunning": True,
                }
            if process is not None:
                self._processes.pop(project_dir.name, None)
            persisted = self._persisted_lock_status(project_dir)
            if persisted is not None:
                return persisted
            return {
                "status": "idle",
                "pid": None,
                "projectId": project_dir.name,
                "alreadyRunning": False,
            }

    def start(
        self,
        project_id: str,
        *,
        take_ids: list[str] | None = None,
        persist_intent: bool = True,
    ) -> dict[str, Any]:
        project_dir = self._project_dir(project_id)
        normalized_take_ids = self._normalize_take_ids(take_ids)
        with self._lock:
            process = self._processes.get(project_dir.name)
            if process is not None and process.poll() is None:
                return {
                    "status": "running",
                    "pid": int(process.pid),
                    "projectId": project_dir.name,
                    "takeIds": normalized_take_ids,
                    "alreadyRunning": True,
                }
            if process is not None:
                self._processes.pop(project_dir.name, None)
            persisted = self._persisted_lock_status(project_dir)
            if persisted is not None:
                return {**persisted, "takeIds": normalized_take_ids}

            intent_path = (
                self._write_intent(project_dir, normalized_take_ids)
                if persist_intent
                else self._intent_path(project_dir)
            )
            command = [
                self.python_executable,
                str(self.tool_path),
                "--project-dir",
                str(project_dir),
                "--poll-seconds",
                "5",
                "--intent-path",
                str(intent_path),
            ]
            for take_id in normalized_take_ids:
                command.extend(["--take-id", take_id])
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            process = subprocess.Popen(
                command,
                cwd=str(project_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            self._processes[project_dir.name] = process
            return {
                "status": "running",
                "pid": int(process.pid),
                "projectId": project_dir.name,
                "takeIds": normalized_take_ids,
                "alreadyRunning": False,
            }

    def resume_authorized(self) -> list[dict[str, Any]]:
        """Resume only GPU batches that were explicitly authorized before a restart."""

        resumed: list[dict[str, Any]] = []
        if not self.projects_root.is_dir():
            return resumed
        for project_dir in sorted(self.projects_root.iterdir()):
            if not project_dir.is_dir():
                continue
            take_ids = self._read_intent(project_dir)
            if take_ids is None:
                continue
            try:
                resumed.append(
                    self.start(
                        project_dir.name,
                        take_ids=take_ids,
                        persist_intent=False,
                    )
                )
            except (FileNotFoundError, ValueError, OSError):
                continue
        return resumed
