"""Regression checks for pagination, snapshot freshness and exact media bytes."""
import hashlib
import ast
import asyncio
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import generative_jobs
import video_projects
from generative_jobs import GenerativeJobStore
from media_io import file_matches_bytes, file_sha256


def main_function(name, namespace):
    path = Path(__file__).with_name("main.py")
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    node = next(item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class PythonPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_unchanged_history_is_not_parsed_for_every_poll(self):
        path = self.root / "jobs.json"
        path.write_text(json.dumps({"jobs": {"one": {"job_id": "one", "status": "done"}}}))
        with mock.patch.object(generative_jobs.json, "load", wraps=json.load) as parse:
            store = GenerativeJobStore(path, recover_on_init=False)
            for _ in range(5):
                self.assertEqual(store.get("one")["status"], "done")
                self.assertEqual(store.list()["total"], 1)
            self.assertEqual(parse.call_count, 1)

    def test_atomic_replacement_with_same_size_and_mtime_invalidates_cache(self):
        path = self.root / "jobs.json"
        path.write_text(json.dumps({"jobs": {"one": {"status": "done"}}}))
        store = GenerativeJobStore(path, recover_on_init=False)
        original = path.stat()
        replacement = self.root / "replacement.json"
        replacement.write_text(json.dumps({"jobs": {"one": {"status": "fail"}}}))
        os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
        os.replace(replacement, path)
        self.assertEqual(store.get("one")["status"], "fail")

    def test_failed_transaction_does_not_leave_dirty_values_in_read_cache(self):
        store = GenerativeJobStore(self.root / "jobs.json", recover_on_init=False)
        store.update("one", status="done")
        self.assertEqual(store.get("one")["status"], "done")
        with mock.patch.object(store, "_persist_snapshot_locked", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                store.update("one", status="error")
        self.assertEqual(store.get("one")["status"], "done")

    def test_list_result_cannot_mutate_cached_nested_history(self):
        store = GenerativeJobStore(self.root / "jobs.json", recover_on_init=False)
        store.update("one", status="done", nested={"values": [1, 2]})
        page = store.list()
        page["items"][0]["nested"]["values"].append(3)
        self.assertEqual(store.get("one")["nested"]["values"], [1, 2])

    def test_catalog_renders_only_the_requested_filtered_page(self):
        for i in range(6):
            folder = self.root / f"project_{i}"
            folder.mkdir()
            manifest = folder / "project_manifest.json"
            manifest.write_text(json.dumps({"status": "PLANNED" if i % 2 == 0 else "COMPLETED"}))
            os.utime(manifest, (1700000000 + i * 10, 1700000000 + i * 10))
        with mock.patch.object(video_projects, "project_view", side_effect=lambda path: {"projectId": path.name}) as render:
            result = video_projects.list_projects(self.root, page=2, page_size=1, status="PLANNED")
        self.assertEqual(result["pagination"]["totalItems"], 3)
        self.assertEqual(result["data"], [{"projectId": "project_2"}])
        self.assertEqual(render.call_count, 1)

    def test_take_pagination_keeps_hidden_items_out_of_count_and_view(self):
        folder = self.root / "project"
        folder.mkdir()
        (folder / "take_queue.json").write_text(json.dumps({"takes": [
            {"id": "hidden", "visible_in_maestro": False},
            {"id": "master", "role": "project_final_output"},
            {"id": "first"}, {"id": "second"}, {"id": "third"},
        ]}))
        with mock.patch.object(video_projects, "_take_view", side_effect=lambda item, _: {"id": item["id"]}) as render:
            result = video_projects.list_takes(self.root, "project", page=2, page_size=1)
        self.assertEqual(result["pagination"]["totalItems"], 3)
        self.assertEqual(result["data"], [{"id": "second"}])
        self.assertEqual(render.call_count, 1)

    def test_media_checks_preserve_exact_content_across_chunk_boundaries(self):
        data = bytes(range(256)) * 12289
        path = self.root / "media.bin"
        path.write_bytes(data)
        self.assertEqual(file_sha256(path), hashlib.sha256(data).hexdigest())
        self.assertTrue(file_matches_bytes(path, data))
        self.assertFalse(file_matches_bytes(path, data[:-1]))
        self.assertFalse(file_matches_bytes(path, data + b"x"))
        self.assertFalse(file_matches_bytes(path, data[:-1] + bytes([data[-1] ^ 1])))
        path.write_bytes(b"")
        self.assertTrue(file_matches_bytes(path, b""))

    def test_upload_preserves_payload_limit_and_closes_on_error(self):
        class Upload:
            def __init__(self, data):
                self.data = io.BytesIO(data)
                self.closed = False

            async def read(self, size):
                return self.data.read(size)

            async def close(self):
                self.closed = True
                self.data.close()

        read_upload = main_function("_read_upload_bounded", {"UploadFile": object, "BytesIO": io.BytesIO})
        payload = bytes(range(256)) * 4096
        upload = Upload(payload)
        self.assertEqual(asyncio.run(read_upload(upload, "image", len(payload))), payload)
        self.assertTrue(upload.closed)
        oversized = Upload(payload + b"x")
        with self.assertRaisesRegex(ValueError, "excede o limite"):
            asyncio.run(read_upload(oversized, "image", len(payload)))
        self.assertTrue(oversized.closed)
        self.assertIsNone(asyncio.run(read_upload(None, "image", len(payload))))

    def test_cleanup_does_not_load_ml_runtime_into_lightweight_api(self):
        from types import SimpleNamespace
        modules = {}
        collect = mock.Mock()
        cleanup = main_function("limpar_vram", {"sys": SimpleNamespace(modules=modules), "gc": SimpleNamespace(collect=collect)})
        cleanup()
        self.assertEqual(modules, {})
        collect.assert_not_called()
        empty_cache = mock.Mock()
        modules["torch"] = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True, empty_cache=empty_cache))
        cleanup()
        empty_cache.assert_called_once_with()
        collect.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
