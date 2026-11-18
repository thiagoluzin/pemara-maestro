import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from video_projects import get_take_generation_spec


PROJECTS_ROOT = (
    Path(__file__).resolve().parents[2]
    / "ferramentas"
    / "video_global_engine"
    / "projetos"
)


class GogetaNativeLongTakeContractTests(unittest.TestCase):
    def test_no_dance_take_is_one_native_15_second_h3_graph(self):
        project_dir = PROJECTS_ROOT / "gogeta_fusao_single_take_15s_v2"
        queue = json.loads((project_dir / "take_queue.json").read_text(encoding="utf-8"))
        take = next(item for item in queue["takes"] if item["id"] == "PROD15_NATIVE_NO_DANCE")
        self.assertTrue(take["video_generation_forbidden"])
        self.assertFalse(take["render_authorized"])
        self.assertEqual(
            take["render_authorization_consumed_by_job_id"],
            "3077e4aeb0f1429aba8dd3f22bc899af",
        )

        test_queue = copy.deepcopy(queue)
        test_take = next(
            item for item in test_queue["takes"] if item["id"] == "PROD15_NATIVE_NO_DANCE"
        )
        test_take["video_generation_forbidden"] = False
        with patch("video_projects._queue", return_value=test_queue):
            spec = get_take_generation_spec(
                PROJECTS_ROOT,
                "gogeta_fusao_single_take_15s_v2",
                "PROD15_NATIVE_NO_DANCE",
            )

        self.assertEqual(
            spec["generationProfile"],
            "minimax_h3_fl2va_int8_vertical_720x1280p24",
        )
        self.assertEqual((spec["width"], spec["height"]), (720, 1280))
        self.assertEqual(spec["fps"], 24.0)
        self.assertEqual(spec["frames"], 362)
        self.assertAlmostEqual(spec["durationSeconds"], 361 / 24, places=6)
        self.assertEqual(spec["steps"], 20)
        self.assertEqual(spec["guidance"], 1.0)
        self.assertTrue(spec["visualOnlyPass"])

        anchors = spec["minimaxAnchorControl"]
        self.assertEqual(anchors["mode"], "single_pass")
        self.assertEqual(anchors["anchorSemantics"], "endpoint_exact")
        self.assertEqual(anchors["startAnchorId"], "NL01")
        self.assertEqual(anchors["endAnchorId"], "NL02")
        self.assertEqual(anchors["referenceImages"], [])
        self.assertIsNone(anchors["referenceVideo"])

        controls = spec["takeExecutionContract"]
        self.assertEqual(controls["anchorBinding"], "first_last_exact")
        self.assertEqual(controls["motionBinding"], "prompt_guided")
        self.assertTrue(controls["declaredControlsVerified"])

        prompt = spec["prompt"].casefold()
        self.assertIn("one continuous minimax h3 fl2va inference", prompt)
        self.assertIn("do not perform or restart any dance", prompt)
        self.assertIn("without a white screen", prompt)
        self.assertIn("hair remains natural black", prompt)
        self.assertIn("exact instant the hair completes gold", prompt)


if __name__ == "__main__":
    unittest.main()
