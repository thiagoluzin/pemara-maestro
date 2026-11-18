"""Cooperative local GPU ownership without process termination."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class GpuLeaseBusy(RuntimeError):
    def __init__(self, current: dict[str, Any]):
        self.current = current
        owner = str(current.get("owner") or "outro trabalho")
        operation = str(current.get("operation") or "GPU")
        super().__init__(f"GPU reservada por {owner} para {operation}.")


class GpuLeaseRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()

    @contextmanager
    def _process_lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                deadline = time.monotonic() + 10
                while True:
                    try:
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Tempo esgotado ao reservar o registro da GPU.")
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _pid_is_running(pid: Any) -> bool:
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return False
        if pid <= 0:
            return False
        if pid == os.getpid():
            return True
        if os.name == "nt":
            import ctypes

            query = 0x1000
            still_active = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(query, False, pid)
            if not handle:
                return ctypes.get_last_error() == 5
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return True
                return code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _read(self) -> dict[str, Any] | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        lease = payload.get("lease") if isinstance(payload, dict) else None
        return lease if isinstance(lease, dict) else None

    def _write(self, lease: dict[str, Any] | None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump({"version": 1, "lease": lease}, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def acquire(
        self,
        *,
        owner: str,
        operation: str,
        job_id: str,
        project_id: str = "",
        take_id: str = "",
    ) -> dict[str, Any]:
        job_id = str(job_id or "").strip()
        if not job_id:
            raise ValueError("job_id obrigatorio para reservar a GPU.")
        with self._lock, self._process_lock():
            current = self._read()
            if current and str(current.get("jobId") or "") == job_id:
                current["heartbeatAt"] = time.time()
                self._write(current)
                return dict(current)
            if current and self._pid_is_running(current.get("pid")):
                raise GpuLeaseBusy(dict(current))
            now = time.time()
            lease = {
                "active": True,
                "owner": str(owner or "studio"),
                "operation": str(operation or "gpu_job"),
                "jobId": job_id,
                "projectId": str(project_id or ""),
                "takeId": str(take_id or ""),
                "pid": os.getpid(),
                "acquiredAt": now,
                "heartbeatAt": now,
            }
            self._write(lease)
            return dict(lease)

    def heartbeat(self, job_id: str) -> dict[str, Any]:
        with self._lock, self._process_lock():
            current = self._read()
            if not current or str(current.get("jobId") or "") != str(job_id or ""):
                raise GpuLeaseBusy(dict(current or {}))
            current["heartbeatAt"] = time.time()
            self._write(current)
            return dict(current)

    def adopt_child_process(self, job_id: str, *, expected_parent_pid: int) -> dict[str, Any]:
        """A finishing child assumes its parent's lease before doing GPU work.

        This keeps the GPU reserved if Studio exits while the child still runs.
        A different owner cannot be displaced by a delayed child startup.
        """
        with self._lock, self._process_lock():
            current = self._read()
            if not current or current.get("jobId") != job_id or current.get("pid") != expected_parent_pid:
                raise GpuLeaseBusy(dict(current or {}))
            current.update(pid=os.getpid(), parentPid=expected_parent_pid, heartbeatAt=time.time())
            self._write(current)
            return dict(current)

    def release(self, job_id: str) -> bool:
        with self._lock, self._process_lock():
            current = self._read()
            if not current or str(current.get("jobId") or "") != str(job_id or ""):
                return False
            self._write(None)
            return True

    def status(self) -> dict[str, Any]:
        with self._lock, self._process_lock():
            current = self._read()
            if not current:
                return {"active": False}
            active = self._pid_is_running(current.get("pid"))
            return {**current, "active": active, "stale": not active}
