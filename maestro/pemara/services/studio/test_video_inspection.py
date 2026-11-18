import copy
import json
import math
import subprocess
import tempfile
import unittest
import uuid
import threading
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from decision_provider import DecisionClient, ProviderError
from editor_suite import EditorSuite, ClipPatch
from video_inspection import InspectionService, InspectionSpec, Explanations, validate_answer, windows, create_inspection_router


def answer(choice="clear"):
    return {"type": "choice", "choice": choice, "confidence": .96,
            "probabilities": {c: .96 if c == choice else .02 for c in ("clear", "defect", "unknown")}}


class FakeDecision:
    def __init__(self, fail=False): self.calls = 0; self.fail = fail; self.contents = []
    def ready(self): return True
    def evaluate(self, content, questions):
        self.calls += 1; self.contents.append(content)
        if self.fail: raise ProviderError("PROVIDER_HTTP_503")
        return {"answers": {c: answer("defect" if c == "continuity" else "unknown" if c == "identity" else "clear") for c in questions},
                "usage": {"total_input_tokens": 120, "total_output_tokens": 0}}


class InspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.source = Path(cls.fixture.name) / "source.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=320x240:rate=24:duration=2.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.source)], check=True)

    @classmethod
    def tearDownClass(cls): cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.suite = EditorSuite(Path(self.temp.name) / "editor_suite")
        self.fake = FakeDecision()
        self.service = InspectionService(self.suite, decision=self.fake)
        self.prepared = self.service.prepare(SimpleNamespace(filename="test.mp4", content_type="video/mp4", file=BytesIO(self.source.read_bytes())))
        self.spec = InspectionSpec(requestId=uuid.uuid4().hex, **{k: self.prepared[k] for k in ("projectId", "clipId", "expectedRevision", "referenceAssetIds")}, contentKind="animation")

    def tearDown(self): self.temp.cleanup()

    def test_timestamps_markers_no_source_mutation_and_idempotent_billing(self):
        original = self.source.read_bytes()
        record = self.service.start(self.spec, synchronous=True)
        self.assertEqual(record["status"], "AWAITING_CODEX")
        self.assertEqual(len(record["windows"]), 2)
        self.assertTrue(record["markers"])
        self.assertTrue(all(m["visible"] for m in record["markers"]))
        times = [f["sourceTime"] for f in record["frames"]]
        self.assertEqual(times[0], 0)
        self.assertTrue(all(b > a for a, b in zip(times, times[1:])))
        self.assertEqual(original, self.source.read_bytes())
        self.assertFalse(record["automaticRegeneration"])
        self.assertFalse(record["approved"])
        self.assertNotIn("synchronization", record["windows"][0]["answers"])
        self.service.start(self.spec, synchronous=True)
        self.assertEqual(self.fake.calls, 2)
        changed = self.spec.model_copy(update={"expectedState": "changed"})
        with self.assertRaises(HTTPException) as cm: self.service.start(changed)
        self.assertEqual(cm.exception.status_code, 409)

    def test_budget_and_revision_fail_before_provider(self):
        with self.assertRaises(HTTPException): self.service.start(self.spec.model_copy(update={"maxDecisionCalls": 1}))
        self.assertEqual(self.fake.calls, 0)
        from editor_suite import EditorSuiteError
        with self.assertRaises(EditorSuiteError): self.service.start(self.spec.model_copy(update={"expectedRevision": 99}))

    def test_trim_projection_and_real_source_times(self):
        project = self.suite.get_project(self.spec.projectId)
        self.suite.patch_clip(self.spec.projectId, self.spec.clipId, ClipPatch(expectedRevision=project["revision"], sourceStart=.5, sourceEnd=2.0))
        spec = self.spec.model_copy(update={"expectedRevision": project["revision"]+1})
        record = self.service.start(spec, synchronous=True)
        self.assertEqual(record["frames"][0]["sourceTime"], .5)
        self.assertEqual(record["markers"][0]["sourceStart"], .5)
        self.assertEqual(record["markers"][0]["timelineStart"], 0)

    def test_codex_explanations_validate_evidence_and_keep_history(self):
        record = self.service.start(self.spec, synchronous=True)
        marker = record["markers"][0]
        payload = {"sourceSha256": record["sourceSha256"], "evidenceSha256": record["evidenceSha256"], "origin": "codex",
                   "explanations": [{"markerId": marker["id"], "verdict": "uncertain", "observed": "Referência visual insuficiente.",
                    "hypothesis": "", "correction": "Fornecer referência canônica.", "frameIndices": marker["frameIndices"][:2]}]}
        self.service.explain(record["id"], Explanations(**payload))
        explained = self.service.get(record["id"])["markers"][0]
        self.assertEqual(explained["status"], "uncertain")
        self.assertEqual(explained["explanation"]["observed"], "Referência visual insuficiente.")
        bad = copy.deepcopy(payload); bad["explanations"][0]["frameIndices"] = [100000]
        with self.assertRaises(HTTPException): self.service.explain(record["id"], Explanations(**bad))
        Path(record["frames"][0]["path"]).write_bytes(b"changed")
        with self.assertRaises(HTTPException) as cm: self.service.explain(record["id"], Explanations(**payload))
        self.assertEqual(cm.exception.status_code, 409)
        self.assertEqual(len(list(self.service.folder(record["id"]).glob("codex_explanations_*.json"))), 1)

    def test_failures_no_retry_and_cancel_before_external_call(self):
        self.fake.fail = True
        record = self.service.start(self.spec, synchronous=True)
        self.assertEqual(record["status"], "FAILED")
        self.assertEqual(self.fake.calls, 1)
        self.assertEqual(record["error"], "PROVIDER_HTTP_503")
        self.service.start(self.spec, synchronous=True)
        self.assertEqual(self.fake.calls, 1)

    def test_http_routes_require_authentication(self):
        app = FastAPI(); app.include_router(create_inspection_router(self.service, lambda r: r.headers.get("x-test-auth") == "yes"))
        client = TestClient(app)
        self.assertEqual(client.get("/api/video-inspection/jobs").status_code, 403)
        self.assertEqual(client.post("/api/video-inspection/jobs", json=self.spec.model_dump()).status_code, 403)
        r = client.get("/api/video-inspection/capabilities", headers={"x-test-auth": "yes"})
        self.assertFalse(r.json()["openaiApiRequired"])
        self.assertFalse(r.json()["automaticRegeneration"])

    def test_invalid_distribution_never_becomes_a_finding(self):
        for bad in [{}, {**answer(), "confidence": float("nan")}, {**answer(), "probabilities": {"clear": 1.0}}]:
            with self.assertRaises(ProviderError): validate_answer(bad)

    def test_window_overlap_covers_partition_contact(self):
        intervals = windows(.5, 8.2, 2)
        self.assertEqual(intervals[0][0], .5)
        self.assertEqual(intervals[-1][1], 8.2)
        self.assertTrue(all(b[0] < a[1] for a,b in zip(intervals, intervals[1:])))

    def test_provider_uses_fixed_endpoint_and_does_not_retry(self):
        calls = []
        def transport(url, body, headers):
            calls.append((url, body)); raise ProviderError("PROVIDER_HTTP_503")
        with patch("decision_provider.private_setting", return_value="unit-placeholder"):
            with self.assertRaises(ProviderError): DecisionClient(transport).evaluate("fixture", {"q": {"type": "choice"}})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "https://generativelanguage.googleapis.com/v1beta/decisions")
        self.assertEqual(calls[0][1]["model"], "gemini-decision-1")

    def test_concurrent_polling_preserves_atomic_report(self):
        record = self.service.start(self.spec, synchronous=True)
        errors = []
        def write():
            try:
                for i in range(40): self.service.update(record["id"], pollTest=i)
            except Exception as exc: errors.append(type(exc).__name__)
        worker = threading.Thread(target=write); worker.start()
        for _ in range(80):
            self.assertEqual(self.service.get(record["id"])["id"], record["id"])
            self.assertEqual(len(self.service.list()), 1)
        worker.join()
        self.assertFalse(errors)
        self.assertEqual(self.service.read(record["id"])["pollTest"], 39)

    def test_transient_local_disk_failure_does_not_repeat_inference(self):
        from video_inspection import _atomic_json, _editor_atomic_json
        target = Path(self.temp.name) / "atomic_fixture.json"
        attempts = []
        def save(path, data):
            attempts.append(1)
            if len(attempts) == 1: raise PermissionError("Temporary Windows sharing conflict")
            return _editor_atomic_json(path, data)
        with patch("video_inspection._editor_atomic_json", side_effect=save): _atomic_json(target, {"ok": True})
        self.assertTrue(json.loads(target.read_text())["ok"])
        self.assertEqual(self.fake.calls, 0)


if __name__ == "__main__": unittest.main()
