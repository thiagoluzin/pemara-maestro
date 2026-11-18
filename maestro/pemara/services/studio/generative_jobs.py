import copy
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class GenerativeJobStore:
    """Persistent, thread-safe history for Studio generation jobs."""

    def __init__(
        self,
        path: Path,
        *,
        max_jobs: int = 500,
        recover_on_init: bool = True,
    ):
        self.path = Path(path)
        self.max_jobs = max(20, int(max_jobs))
        self._lock = threading.RLock()
        self._interrupted_on_startup: list[str] = []
        self._loaded_signature: tuple[int, ...] | None = None
        self._backup = self.path.with_suffix(self.path.suffix + ".previous")
        self._jobs = self._load()
        if recover_on_init:
            self.recover_interrupted()

    @contextmanager
    def _process_lock(self):
        """Serialize read-modify-write cycles across Studio processes."""

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

                deadline = time.monotonic() + 10.0
                while True:
                    try:
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Tempo esgotado ao bloquear o historico de jobs.")
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
    def _stat_signature(stat: os.stat_result) -> tuple[int, ...]:
        # Include identity as well as timestamps: atomic replacement can preserve
        # file size and mtime while supplying a completely different snapshot.
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)

    def _file_signature(self) -> tuple[int, ...] | None:
        try:
            return self._stat_signature(self.path.stat())
        except OSError:
            return None

    def _load(self, *, force: bool = False) -> dict[str, dict[str, Any]]:
        signature = self._file_signature()
        if not force and signature is not None and signature == self._loaded_signature:
            return self._jobs
        self._loaded_signature = None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                opened = self._stat_signature(os.fstat(handle.fileno()))
                payload = json.load(handle)
                finished = self._stat_signature(os.fstat(handle.fileno()))
        except FileNotFoundError:
            if self._backup.exists() or getattr(self, "_jobs", {}):
                raise RuntimeError("Historico de jobs ausente. Restaure a ultima copia valida.")
            return {}
        except (ValueError, OSError) as exc:
            raise RuntimeError("Erro ao ler o historico de jobs. Gravacao interrompida.") from exc
        if isinstance(payload, dict) and ("version" in payload or isinstance(payload.get("jobs"), dict)):
            payload = payload.get("jobs")
        if not isinstance(payload, dict) or any(not isinstance(job, dict) for job in payload.values()):
            raise RuntimeError("Formato invalido do historico de jobs. Gravacao interrompida.")
        if opened != finished or finished != self._file_signature():
            raise RuntimeError("Historico de jobs alterado durante a leitura. Tente novamente.")
        if not force:
            self._loaded_signature = opened
        return payload

    def _persist_snapshot_locked(self) -> None:
        self._loaded_signature = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "jobs": self._jobs}
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if self.path.is_file():
                # The caller has validated this snapshot under the process lock.
                self._write_previous(self.path.read_bytes())
            # On Windows a concurrent status reader can briefly hold the JSON
            # without delete sharing.  Retrying the atomic replace keeps that
            # transient WinError 5/32 from killing a completed video worker.
            deadline = time.monotonic() + 3.0
            while True:
                try:
                    os.replace(temp_name, self.path)
                    break
                except PermissionError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    def _write_previous(self, snapshot: bytes) -> None:
        fd, name = tempfile.mkstemp(prefix=f".{self._backup.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(snapshot)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self._backup)
        finally:
            Path(name).unlink(missing_ok=True)

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
            # ``os.kill(pid, 0)`` is not a reliable existence probe on Windows:
            # protected processes can raise PermissionError and some Python
            # builds surface that as SystemError during module startup. Query a
            # process handle instead so a stale worker PID can never prevent the
            # Studio from booting.
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                process_query_limited_information,
                False,
                pid,
            )
            if not handle:
                # Access denied means the PID exists but cannot be inspected.
                return ctypes.get_last_error() == 5
            try:
                exit_code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return True
                return exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(pid, 0)
        except (OSError, SystemError):
            return False
        return True

    def _trim_locked(self) -> None:
        ordered = sorted(
            self._jobs.items(),
            key=lambda item: float(item[1].get("updated_at", 0) or 0),
            reverse=True,
        )[: self.max_jobs]
        self._jobs = dict(ordered)

    def recover_interrupted(self) -> tuple[str, ...]:
        """Reconcile stale persisted workers when the owning service actually starts."""

        changed = False
        now = time.time()
        with self._lock, self._process_lock():
            self._jobs = self._load(force=True)
            for job_id, job in self._jobs.items():
                if job.get("status") in {"queued", "running"}:
                    worker_pid = job.get("worker_pid")
                    if worker_pid and self._pid_is_running(worker_pid):
                        continue
                    job.update({
                        "status": "interrupted",
                        "progress": int(job.get("progress", 0) or 0),
                        "message": "Interrompido por reinicio do Studio.",
                        "updated_at": now,
                    })
                    self._interrupted_on_startup.append(job_id)
                    changed = True
                elif job.get("status") == "canceling":
                    job.update({
                        "status": "canceled",
                        "progress": int(job.get("progress", 0) or 0),
                        "message": "Cancelamento confirmado durante reinicio do Studio.",
                        "finished_at": now,
                        "updated_at": now,
                    })
                    changed = True
            if changed:
                self._trim_locked()
                self._persist_snapshot_locked()
        return self.interrupted_on_startup()

    def interrupted_on_startup(self) -> tuple[str, ...]:
        """Return only jobs interrupted while this store instance was opening."""

        with self._lock:
            return tuple(self._interrupted_on_startup)

    def claim_interrupted(self, job_id: str, *, worker_pid: int, message: str) -> dict[str, Any] | None:
        """Atomically claim one interrupted job so two Studio processes cannot resume it twice."""

        now = time.time()
        with self._lock, self._process_lock():
            self._jobs = self._load(force=True)
            job = self._jobs.get(job_id)
            if not job or job.get("status") != "interrupted":
                return None
            job.update({
                "status": "queued",
                "progress": max(1, int(job.get("progress", 0) or 0)),
                "message": str(message),
                "error": None,
                "worker_pid": int(worker_pid),
                "resume_count": int(job.get("resume_count", 0) or 0) + 1,
                "resumed_at": now,
                "updated_at": now,
            })
            job.pop("finished_at", None)
            self._trim_locked()
            self._persist_snapshot_locked()
            return copy.deepcopy(job)

    def update(self, job_id: str, *, expected_updated_at: float | None = None, **updates: Any) -> dict[str, Any]:
        now = time.time()
        with self._lock, self._process_lock():
            self._jobs = self._load(force=True)
            if expected_updated_at is not None:
                current = self._jobs.get(job_id, {})
                if current.get("updated_at") != expected_updated_at:
                    raise RuntimeError("O job mudou durante a recuperacao.")
            job = self._jobs.setdefault(job_id, {"job_id": job_id, "created_at": now})
            job.update(updates)
            job["job_id"] = job_id
            job["updated_at"] = now
            status = str(job.get("status") or "")
            if status in {"done", "error", "canceled"}:
                job.setdefault("finished_at", now)
            elif status in {"queued", "running", "canceling"}:
                job.pop("finished_at", None)
            self._trim_locked()
            self._persist_snapshot_locked()
            return copy.deepcopy(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._jobs = self._load()
            job = self._jobs.get(job_id)
            return copy.deepcopy(job) if job else None

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str = "",
        mode: str = "",
    ) -> dict[str, Any]:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        with self._lock:
            self._jobs = self._load()
            items = [
                job for job in self._jobs.values()
                if (not status or job.get("status") == status)
                and (not mode or job.get("mode") == mode)
            ]
            items.sort(key=lambda job: float(job.get("updated_at", 0) or 0), reverse=True)
            total = len(items)
            start = (page - 1) * page_size
            selected = copy.deepcopy(items[start : start + page_size])
        return {
            "ok": True,
            "items": selected,
            "page": page,
            "page_size": page_size,
            "total": total,
        }
