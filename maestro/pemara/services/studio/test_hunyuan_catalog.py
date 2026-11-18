"""Catalog visibility and timing for a take already running through MCP."""
import json
import tempfile
import unittest
from pathlib import Path

from video_projects import create_project, list_takes, get_take_generation_spec


class HunyuanCatalogTests(unittest.TestCase):
    def test_mcp_take_has_correct_engine_elapsed_time_and_no_duplicate_submit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_project(root, name="Hunyuan catalog", project_id="hunyuan_catalog", content_kind="live_action", duration_seconds=8)
            path = root / "hunyuan_catalog/take_queue.json"
            queue = json.loads(path.read_text())
            queue["takes"] = [{"id": "T01", "maestro_status": "GENERATING", "target_duration_seconds": 8,
                "video_generation": {"profile": "hunyuan15_i2v_720p24_mcp", "width": 1280, "height": 720, "fps": 24},
                "video": {"mcp_execution": {"status": "completed", "started_at": "2026-11-10T14:00:00+00:00", "finished_at": "2026-11-10T14:02:03+00:00"}}}]
            path.write_text(json.dumps(queue))
            take = list_takes(root, "hunyuan_catalog")["data"][0]
            self.assertIn("HunyuanVideo 1.5", take["engine"])
            self.assertEqual(take["stage"], "HUNYUAN15_MCP_MANAGED")
            self.assertEqual(take["mcpExecution"]["elapsed_seconds"], 123)
            self.assertFalse(take["canGenerate"])
            self.assertIn("MCP", take["generationBlockedReason"])
            with self.assertRaises(ValueError):
                get_take_generation_spec(root, "hunyuan_catalog", "T01")
