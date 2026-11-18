from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from video_projects import create_project, list_takes, patch_take


class VideoEngineSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        create_project(self.root, name="Escolha de Motor")
        queue_path = self.root / "escolha_de_motor" / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [
            {
                "id": "01",
                "target_duration_seconds": 6,
                "maestro_status": "PLANNED",
                "base_image": {"status": "pending", "file": ""},
                "video_generation": {"profile": "owner_selection_required"},
            }
        ]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_selection_never_defaults_to_h3(self) -> None:
        take = list_takes(self.root, "escolha_de_motor")["data"][0]
        self.assertEqual(take["generationProfile"], "owner_selection_required")
        self.assertEqual(take["stage"], "ENGINE_SELECTION_REQUIRED")
        self.assertFalse(take["canGenerate"])
        self.assertIn("Escolha explicitamente", take["generationBlockedReason"])

    def test_owner_can_select_h3_and_ltx25_is_rejected(self) -> None:
        h3 = patch_take(
            self.root,
            "escolha_de_motor",
            "01",
            {"generationProfile": "minimax_h3_fl2va_int8_720p24"},
        )
        self.assertEqual(h3["generationProfile"], "minimax_h3_fl2va_int8_720p24")
        self.assertEqual((h3["width"], h3["height"], h3["fps"]), (1280, 720, 24.0))

        with self.assertRaisesRegex(ValueError, "MiniMax H3"):
            patch_take(self.root, "escolha_de_motor", "01",
                       {"generationProfile": "ltx25_two_stage_distilled_960x544p24"})
        take = list_takes(self.root, "escolha_de_motor")["data"][0]
        self.assertEqual(take["generationProfile"], "minimax_h3_fl2va_int8_720p24")

    def test_unknown_engine_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "MiniMax H3"):
            patch_take(
                self.root,
                "escolha_de_motor",
                "01",
                {"generationProfile": "automatic_fallback"},
            )


if __name__ == "__main__":
    unittest.main()
