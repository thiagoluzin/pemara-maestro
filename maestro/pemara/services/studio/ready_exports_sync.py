"""Durable, serialized PRONTOS synchronization outside the review request."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from pathlib import Path

from ready_exports import _atomic_json_write, sync_project_ready_exports

PENDING_NAME = '.ready_exports_pending.json'


class ReadyExportsSync:
    def __init__(self, sync=None):
        self._sync = sync or sync_project_ready_exports
        self._condition = threading.Condition()
        self._pending = {}
        self._thread = None
        self._closed = False

    def request(self, project_dir: Path, *, queue_path: Path) -> None:
        project_dir, queue_path = project_dir.resolve(), queue_path.resolve()
        if queue_path.parent != project_dir or queue_path.suffix != '.json':
            raise ValueError('Ready export queue must be inside the project root.')
        with self._condition:
            record = {'id': uuid.uuid4().hex, 'queue': queue_path.name}
            _atomic_json_write(project_dir / PENDING_NAME, record)
            self._pending[project_dir] = (record, 0.0)
            self._start_locked()

    def resume(self, projects_root: Path) -> None:
        with self._condition:
            for marker in projects_root.glob('*/' + PENDING_NAME):
                try:
                    record = json.loads(marker.read_text(encoding='utf-8'))
                    queue = marker.parent / record['queue']
                    if queue.resolve().parent != marker.parent.resolve() or queue.suffix != '.json':
                        raise ValueError('Invalid pending export queue.')
                    uuid.UUID(record['id'])
                    self._pending[marker.parent.resolve()] = (record, 0.0)
                except (OSError, ValueError, KeyError, TypeError):
                    logging.exception('Invalid pending ready export: %s', marker)
            if self._pending:
                self._start_locked()

    def _start_locked(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True, name='studio-ready-exports')
            self._thread.start()
        self._condition.notify_all()

    def _run(self):
        while True:
            with self._condition:
                while not self._closed:
                    now = time.monotonic()
                    eligible = [(p, record) for p, (record, due) in self._pending.items() if due <= now]
                    if eligible:
                        project, record = eligible[0]
                        break
                    delay = min((due - now for _, due in self._pending.values()), default=None)
                    self._condition.wait(timeout=delay)
                if self._closed:
                    return
            error = None
            try:
                if project.is_dir():
                    self._sync(project, queue_path=project / record['queue'])
            except Exception as exc:
                error = exc
                logging.exception('Ready export synchronization will retry: %s', project)
            with self._condition:
                current = self._pending.get(project)
                if not current or current[0]['id'] != record['id']:
                    continue  # Another review arrived while the worker was busy.
                if error is not None:
                    self._pending[project] = (record, time.monotonic() + 5.0)
                    continue
                try:
                    (project / PENDING_NAME).unlink(missing_ok=True)
                except OSError:
                    logging.exception('Unable to clear ready export marker: %s', project)
                    self._pending[project] = (record, time.monotonic() + 5.0)
                    continue
                del self._pending[project]
                self._condition.notify_all()

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        if self._thread:
            self._thread.join(timeout=2)


_WORKER = ReadyExportsSync()
request_ready_exports_sync = _WORKER.request
resume_ready_exports_sync = _WORKER.resume
