from __future__ import annotations

import unittest
from pathlib import Path

from video_engines.base import EngineError
from video_engines.ltx25 import Ltx25VideoEngine, OFFICIAL_WORKFLOWS


WORKSPACE = Path(__file__).resolve().parents[2]


class Ltx25AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = Ltx25VideoEngine(WORKSPACE, comfy_online=True)

    def test_dimensions_are_fail_closed(self) -> None:
        with self.assertRaises(EngineError) as raised:
            self.engine.validate_request({"width": 1280, "height": 720, "duration_seconds": 6})
        self.assertEqual(raised.exception.code, "LTX25_DIMENSIONS_INVALID")

    def test_valid_request_uses_8n_plus_1_frames(self) -> None:
        value = self.engine.validate_request({"width": 960, "height": 544, "duration_seconds": 6, "fps": 24})
        self.assertEqual(value["num_frames"] % 8, 1)

    def test_only_pinned_official_workflows_are_accepted(self) -> None:
        built = self.engine.build_workflow({"width": 960, "height": 544, "workflow_id": OFFICIAL_WORKFLOWS[0]})
        self.assertEqual(built["workflow_id"], OFFICIAL_WORKFLOWS[0])
        with self.assertRaises(EngineError) as raised:
            self.engine.build_workflow({"width": 960, "height": 544, "workflow_id": "legacy-2.3.json"})
        self.assertEqual(raised.exception.code, "LTX25_WORKFLOW_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
