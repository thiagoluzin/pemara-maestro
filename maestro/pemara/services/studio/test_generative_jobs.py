import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from generative_jobs import GenerativeJobStore


class GenerativeJobStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "jobs.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_jobs_survive_process_restart(self):
        store = GenerativeJobStore(self.path)
        store.update("job-1", status="done", mode="image", progress=100)

        restored = GenerativeJobStore(self.path)
        self.assertEqual(restored.get("job-1")["status"], "done")
        self.assertEqual(restored.get("job-1")["mode"], "image")
        self.assertIsInstance(restored.get("job-1")["finished_at"], float)

    def test_terminal_timestamp_is_cleared_when_a_job_is_requeued(self):
        store = GenerativeJobStore(self.path)
        finished = store.update("job-1", status="error", mode="video", progress=100)
        self.assertIsInstance(finished["finished_at"], float)

        requeued = store.update("job-1", status="queued", progress=1)
        self.assertNotIn("finished_at", requeued)

    def test_running_job_becomes_interrupted_after_restart(self):
        store = GenerativeJobStore(self.path)
        store.update("job-1", status="running", mode="video", progress=47)

        restored = GenerativeJobStore(self.path)
        job = restored.get("job-1")
        self.assertEqual(job["status"], "interrupted")
        self.assertEqual(job["progress"], 47)
        self.assertEqual(restored.interrupted_on_startup(), ("job-1",))

    def test_recovery_can_be_deferred_until_service_startup(self):
        store = GenerativeJobStore(self.path)
        store.update("job-1", status="running", mode="video", progress=47)

        imported = GenerativeJobStore(self.path, recover_on_init=False)
        self.assertEqual(imported.get("job-1")["status"], "running")

        imported.recover_interrupted()
        self.assertEqual(imported.get("job-1")["status"], "interrupted")

    def test_interrupted_job_can_be_claimed_only_once_for_resume(self):
        store = GenerativeJobStore(self.path)
        store.update(
            "job-1",
            status="interrupted",
            mode="video",
            progress=9,
            prompt_id="prompt-existing",
        )

        claimed = store.claim_interrupted(
            "job-1",
            worker_pid=os.getpid(),
            message="Recuperando.",
        )
        duplicate = store.claim_interrupted(
            "job-1",
            worker_pid=os.getpid(),
            message="Duplicado.",
        )

        self.assertEqual(claimed["status"], "queued")
        self.assertEqual(claimed["resume_count"], 1)
        self.assertEqual(claimed["prompt_id"], "prompt-existing")
        self.assertIsNone(duplicate)

    def test_canceling_job_becomes_canceled_after_restart(self):
        store = GenerativeJobStore(self.path)
        store.update("job-1", status="canceling", mode="image", progress=21)

        restored = GenerativeJobStore(self.path)
        job = restored.get("job-1")
        self.assertEqual(job["status"], "canceled")
        self.assertEqual(job["progress"], 21)

    def test_list_filters_and_paginates(self):
        store = GenerativeJobStore(self.path)
        store.update("image-1", status="done", mode="image")
        store.update("video-1", status="error", mode="video")
        store.update("video-2", status="done", mode="video")

        page = store.list(page=1, page_size=1, mode="video")
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)

    def test_invalid_file_stops_mutation_and_keeps_previous_snapshot(self):
        store = GenerativeJobStore(self.path)
        store.update("first", status="done")
        store.update("second", status="done")
        previous = self.path.with_suffix(".json.previous")
        saved = previous.read_bytes()
        self.path.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "historico"):
            store.update("third", status="done")
        with self.assertRaisesRegex(RuntimeError, "historico"):
            GenerativeJobStore(self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "not-json")
        self.assertEqual(previous.read_bytes(), saved)
        self.assertIn(b'"first"', saved)

    def test_two_store_instances_do_not_erase_each_others_jobs(self):
        first = GenerativeJobStore(self.path)
        second = GenerativeJobStore(self.path)

        first.update("image-1", status="done", mode="image")
        second.update("video-1", status="done", mode="video")

        self.assertEqual(first.list()["total"], 2)
        self.assertEqual(second.list()["total"], 2)
        restored = GenerativeJobStore(self.path)
        self.assertEqual({item["job_id"] for item in restored.list()["items"]}, {"image-1", "video-1"})

    def test_live_worker_job_is_not_interrupted_by_second_instance(self):
        first = GenerativeJobStore(self.path)
        first.update(
            "job-live",
            status="running",
            mode="video",
            progress=23,
            worker_pid=os.getpid(),
        )

        second = GenerativeJobStore(self.path)
        self.assertEqual(second.get("job-live")["status"], "running")

    def test_transient_windows_replace_lock_is_retried(self):
        store = GenerativeJobStore(self.path)
        real_replace = os.replace
        attempts = 0

        def transient_replace(source, destination):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise PermissionError(5, "access denied")
            return real_replace(source, destination)

        with mock.patch("generative_jobs.os.replace", side_effect=transient_replace):
            store.update("video-locked", status="done", mode="video")

        self.assertEqual(attempts, 3)
        self.assertEqual(store.get("video-locked")["status"], "done")


if __name__ == "__main__":
    unittest.main()
