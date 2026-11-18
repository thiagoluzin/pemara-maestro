from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


MODULE_PATH = Path(__file__).resolve().parents[1] / "execute_anchor_queue.py"
SPEC = importlib.util.spec_from_file_location("execute_anchor_queue", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
executor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(executor)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class AnchorExecutorRecoveryTests(unittest.TestCase):
    def test_poll_retries_transient_disconnect_without_losing_job(self):
        class Session:
            calls = 0

            def get(self, url, timeout):
                self.calls += 1
                if self.calls == 1:
                    raise requests.ConnectionError("studio reiniciando")
                return FakeResponse({"job_id": "job-1", "status": "done", "result": {"outputs": []}})

        session = Session()
        with patch.object(executor.time, "sleep"):
            job = executor.wait_job(session, "http://studio", "job-1", 1)

        self.assertEqual(job["job_id"], "job-1")
        self.assertEqual(session.calls, 2)

    def test_matching_job_must_belong_to_current_request_window(self):
        source = Path("f2_s5.png")
        payload = {
            "items": [
                {
                    "job_id": "old",
                    "status": "done",
                    "prompt": "same prompt",
                    "base_image_name": source.name,
                    "model": executor.EDIT_MODEL,
                    "created_at": 100,
                },
                {
                    "job_id": "current",
                    "status": "done",
                    "prompt": "same prompt",
                    "base_image_name": source.name,
                    "model": executor.EDIT_MODEL,
                    "created_at": 201,
                },
            ]
        }

        class Session:
            def get(self, url, timeout):
                return FakeResponse(payload)

        matched = executor.find_matching_job(
            Session(),
            "http://studio",
            prompt="same prompt",
            source=source,
            mode="edit",
            model=executor.EDIT_MODEL,
            not_before=200,
        )

        self.assertIsNotNone(matched)
        self.assertEqual(matched["job_id"], "current")

    def test_matching_job_excludes_terminal_failure(self):
        source = Path("f2_s5.png")
        payload = {
            "items": [
                {
                    "job_id": "failed",
                    "status": "error",
                    "prompt": "same prompt",
                    "base_image_name": source.name,
                    "model": executor.EDIT_MODEL,
                    "created_at": 201,
                }
            ]
        }

        class Session:
            def get(self, url, timeout):
                return FakeResponse(payload)

        matched = executor.find_matching_job(
            Session(),
            "http://studio",
            prompt="same prompt",
            source=source,
            mode="edit",
            model=executor.EDIT_MODEL,
            not_before=200,
        )

        self.assertIsNone(matched)

    def test_recover_only_never_starts_a_new_job(self):
        take = {"id": "S06B"}
        request = {"id": "request-1", "created_at": "2026-07-27T07:00:00-03:00"}
        argv = [
            "execute_anchor_queue.py",
            "--project-dir",
            str(executor.PROJECTS_ROOT / "dummy"),
            "--recover-only",
            "--log-file",
            "unused-test-executor.log",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(executor, "pending_requests", return_value=[(take, request)]),
            patch.object(executor, "configure_project"),
            patch.object(executor, "acquire_executor_lock", return_value=Path("unused-test.lock")),
            patch.object(executor, "anchor_source", return_value=Path("f2_s6.png")),
            patch.object(executor, "build_prompt", return_value="prompt"),
            patch.object(executor, "find_matching_job", return_value=None),
            patch.object(executor, "start_job") as start_job,
            patch.object(executor.logging, "basicConfig"),
        ):
            result = executor.main()

        self.assertEqual(result, 0)
        start_job.assert_not_called()

    def test_human_rejection_reason_is_added_to_regeneration_prompt(self):
        prompt = executor.build_prompt(
            {"id": "S04C", "objective": "Forest commitment"},
            {"reason": "me fez um porta retrato, nada haver"},
        )

        self.assertIn("me fez um porta retrato, nada haver", prompt)
        self.assertIn("Do not repeat that rejected composition", prompt)

    def test_automatic_request_metadata_is_not_added_to_visual_prompt(self):
        prompt = executor.build_prompt(
            {"id": "S06B", "objective": "Mud reflection"},
            {"reason": "Preparar uma imagem-âncora própria e aprovada para o take S06B."},
        )

        self.assertNotIn("Director correction", prompt)

    def test_anchor_prompt_requires_full_bleed_without_picture_frame(self):
        prompt = executor.build_prompt(
            {"id": "S07C", "objective": "Chain draw"},
            {"reason": "Preparar uma imagem-âncora própria para o take S07C."},
        )

        self.assertIn("full-bleed, edge-to-edge", prompt)
        self.assertIn("never place it inside a picture frame", prompt)
        self.assertIn("picture frame", executor.NEGATIVE)
        self.assertIn("letterbox", executor.NEGATIVE)

    def test_project_prompt_overrides_environmental_image_edit_fallback(self):
        prompt = executor.build_prompt(
            {
                "id": "04",
                "base_image": {
                    "generation_mode": "image_edit",
                    "prompt": "Preserve the cobra commander and create a refinery close-up.",
                },
            }
        )

        self.assertEqual(
            prompt,
            "Preserve the cobra commander and create a refinery close-up.",
        )
        self.assertNotIn("empty environment only", prompt.lower())

    def test_project_image_edit_prompt_includes_directed_rejection_correction(self):
        prompt = executor.build_prompt(
            {
                "id": "04",
                "base_image": {
                    "generation_mode": "image_edit",
                    "prompt": "Preserve the cobra commander.",
                },
            },
            {
                "reason": "Keep the mouth closed around one lit cigarette; no visible tongue.",
            },
        )

        self.assertIn("Preserve the cobra commander.", prompt)
        self.assertIn("Constructive revision:", prompt)
        self.assertIn("one lit cigarette", prompt)

    def test_project_negative_prompt_overrides_character_forbidden_legacy_default(self):
        take = {
            "base_image": {
                "negative_prompt": "human head, lizard head, duplicate cobra soldiers",
            }
        }

        self.assertEqual(
            executor.negative_prompt(take),
            "human head, lizard head, duplicate cobra soldiers",
        )
        self.assertNotIn("humanoid silhouette", executor.negative_prompt(take))


if __name__ == "__main__":
    unittest.main()
