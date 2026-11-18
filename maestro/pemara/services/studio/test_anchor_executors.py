from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from anchor_executors import AnchorExecutorManager


class AnchorExecutorManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "tools").mkdir()
        (self.root / "tools" / "execute_anchor_queue.py").write_text("# executor", encoding="utf-8")
        self.project = self.root / "projetos" / "filme"
        (self.project / "tools").mkdir(parents=True)
        (self.project / "take_queue.json").write_text('{"takes":[]}', encoding="utf-8")
        self.manager = AnchorExecutorManager(self.root, python_executable="python-test")

    def tearDown(self):
        self.temporary.cleanup()

    @patch("anchor_executors.subprocess.Popen")
    def test_starts_canonical_executor_with_project_and_take_filter(self, popen):
        process = Mock()
        process.pid = 321
        process.poll.return_value = None
        popen.return_value = process

        result = self.manager.start("filme", take_ids=["S01B", "S01B", "S02C"])

        command = popen.call_args.args[0]
        self.assertEqual(result["pid"], 321)
        self.assertFalse(result["alreadyRunning"])
        self.assertIn(str(self.project.resolve()), command)
        self.assertEqual(command.count("--take-id"), 2)
        self.assertIn("--intent-path", command)
        intent = json.loads(
            (self.project / "tools" / "anchor_executor_intent.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(intent["projectId"], "filme")
        self.assertEqual(intent["takeIds"], ["S01B", "S02C"])

    @patch("anchor_executors.subprocess.Popen")
    def test_second_start_is_idempotent_while_process_is_running(self, popen):
        process = Mock()
        process.pid = 321
        process.poll.return_value = None
        popen.return_value = process

        self.manager.start("filme")
        replay = self.manager.start("filme")

        self.assertTrue(replay["alreadyRunning"])
        self.assertEqual(popen.call_count, 1)

    @patch.object(AnchorExecutorManager, "_pid_is_running", return_value=True)
    @patch("anchor_executors.subprocess.Popen")
    def test_survives_studio_restart_by_honoring_persisted_lock(self, popen, _pid_running):
        lock_path = self.project / "tools" / "anchor_executor.lock"
        lock_path.write_text(
            json.dumps({"pid": 987, "project_id": "filme", "started_at": "2026-07-27T08:00:00Z"}),
            encoding="utf-8",
        )

        result = self.manager.start("filme")

        self.assertTrue(result["alreadyRunning"])
        self.assertEqual(result["pid"], 987)
        popen.assert_not_called()

    def test_rejects_project_path_escape(self):
        with self.assertRaises(ValueError):
            self.manager.start("../fora")

    @patch("anchor_executors.subprocess.Popen")
    def test_resumes_only_a_previously_authorized_batch(self, popen):
        process = Mock()
        process.pid = 654
        process.poll.return_value = None
        popen.return_value = process
        intent_path = self.project / "tools" / "anchor_executor_intent.json"
        intent_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "projectId": "filme",
                    "takeIds": ["S03B", "S03C"],
                    "authorizedAt": "2026-07-27T12:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

        resumed = self.manager.resume_authorized()

        self.assertEqual(len(resumed), 1)
        self.assertEqual(resumed[0]["pid"], 654)
        command = popen.call_args.args[0]
        self.assertEqual(command.count("--take-id"), 2)
        self.assertIn("S03B", command)
        self.assertIn("S03C", command)


if __name__ == "__main__":
    unittest.main()
