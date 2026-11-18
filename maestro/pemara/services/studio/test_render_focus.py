from pathlib import Path
import unittest
from unittest.mock import patch

import render_focus


class RenderFocusTests(unittest.TestCase):
    def test_only_project_owned_secondary_comfy_matches(self):
        root = Path(r"E:\Pemara\maestro\pemara")
        valid = (
            r'C:\Python311\python.exe E:\Pemara\maestro\pemara\ferramentas\ComfyUI\main.py '
            r'--listen 127.0.0.1 --port 8190'
        )
        self.assertTrue(render_focus._is_managed_secondary_comfy(valid, 8190, root))
        self.assertFalse(render_focus._is_managed_secondary_comfy(valid, 8188, root))
        self.assertFalse(
            render_focus._is_managed_secondary_comfy(
                r'C:\other\ComfyUI\main.py --port 8190', 8190, root
            )
        )

    @patch.object(render_focus, "_system_snapshot")
    @patch.object(render_focus, "_stop_idle_secondary_comfy")
    def test_dry_run_never_unloads_or_prioritizes(self, stop_secondary, snapshot):
        snapshot.return_value = {
            "ramAvailableGb": 40.0,
            "gpu": {"available": True, "utilizationPercent": 0},
        }
        stop_secondary.return_value = [{"action": "stop_idle_secondary_comfy", "dryRun": True}]
        with patch.object(render_focus, "_unload_ollama_models") as unload, patch.object(
            render_focus, "_prioritize_primary_comfy"
        ) as prioritize, patch.object(Path, "write_text"):
            receipt = render_focus.prepare_render_focus(Path.cwd(), job_id="dry", dry_run=True)
        unload.assert_not_called()
        prioritize.assert_not_called()
        self.assertTrue(receipt["ready"])


if __name__ == "__main__":
    unittest.main()
