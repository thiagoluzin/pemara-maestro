"""Real FastAPI routes, isolated roots, lifespan disabled (no GPU recovery)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import main as studio
from test_internet_publication import BRIEF, PLAN


class PublicationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pemara-publication-api-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patches = [mock.patch.object(studio, "VIDEO_PROJECTS_ROOT", self.root),
                        mock.patch.object(studio, "_internal_token", return_value="synthetic-test-token-only")]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        # No context manager: TestClient does not run lifespan/startup workers.
        self.client = TestClient(studio.app, base_url="http://127.0.0.1",
                                 headers={"X-Studio-Internal-Token": "synthetic-test-token-only"})
        self.addCleanup(self.client.close)

    def create(self):
        response = self.client.post("/api/video-projects", json={"name": "API Synthetic", "objective": BRIEF})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["projectId"]

    def test_create_preview_plan_and_read_persist_without_starting_a_job(self):
        with mock.patch.object(studio, "_preflight_video_take_job") as preflight:
            preview = self.client.post("/api/video-projects/briefing-preview", json={"brief": BRIEF})
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.json()["intent"]["mode"], "internet")
            self.assertFalse(preview.json()["autoGenerate"])
            project_id = self.create()
            endpoint = f"/api/video-projects/{project_id}/internet-publication"
            saved = self.client.post(endpoint + "/plan", json={"expectedRevision": 0, "plan": PLAN})
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertTrue(saved.json()["readiness"]["readyForExistingGates"])
            fetched = self.client.get(endpoint)
            self.assertEqual(fetched.json()["plan"], PLAN)
            self.assertEqual(fetched.headers["x-content-type-options"], "nosniff")
            self.assertEqual(fetched.headers["cache-control"], "no-store")
            preflight.assert_not_called()

    def test_public_forwarded_fake_role_and_invalid_token_denied(self):
        for headers in ({"Host": "api-studio.pemaratech.com.br"},
                        {"X-Forwarded-Host": "new-public.invalid", "X-User-Role": "owner"},
                        {"Forwarded": "for=127.0.0.1", "X-Studio-Internal-Token": "forged"}):
            with self.subTest(headers=headers):
                client = TestClient(studio.app, base_url="http://127.0.0.1")
                try:
                    response = client.post("/api/video-projects/briefing-preview", headers=headers, json={"brief": BRIEF})
                    self.assertEqual(response.status_code, 403)
                finally:
                    client.close()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_forged_approval_unknown_actions_and_stale_write_rejected(self):
        project_id = self.create()
        endpoint = f"/api/video-projects/{project_id}/internet-publication"
        denied = self.client.post(endpoint + "/plan", json={"expectedRevision": 0, "plan": PLAN, "humanApproved": True})
        self.assertEqual(denied.status_code, 422)
        self.assertEqual(self.client.post(endpoint + "/publish", json={}).status_code, 404)
        self.assertEqual(self.client.post(endpoint + "/plan", json={"expectedRevision": 0, "plan": PLAN}).status_code, 200)
        self.assertEqual(self.client.post(endpoint + "/plan", json={"expectedRevision": 0, "plan": PLAN}).status_code, 409)
        self.assertEqual(self.client.get("/api/video-projects/missing/internet-publication").status_code, 404)
        self.assertEqual(self.client.post(endpoint + "/packages", json={"expectedRevision": 1, "platform": "threads", "title": "Sem aprovação"}).status_code, 422)

    def test_anchor_execution_requires_direction_without_calling_executor(self):
        project_id = self.create()
        with mock.patch.object(studio._ANCHOR_EXECUTOR_MANAGER, "start") as start:
            response = self.client.post(f"/api/video-projects/{project_id}/anchor-jobs", json={})
            self.assertEqual(response.status_code, 422)
            self.assertIn("INTERNET_DIRECTION_REQUIRED", response.text)
            start.assert_not_called()

    def test_bounded_body_and_invalid_json_fail_without_mutation(self):
        plain = self.client.post("/api/video-projects/briefing-preview", content='{"brief":"Para internet"}',
                                 headers={"Content-Type": "text/plain", "Origin": "https://untrusted.invalid"})
        self.assertEqual(plain.status_code, 422)
        for data in (b"[1,2]", b"not JSON", b'{"brief":"' + b"x" * 70000 + b'"}'):
            response = self.client.post("/api/video-projects/briefing-preview", content=data, headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
