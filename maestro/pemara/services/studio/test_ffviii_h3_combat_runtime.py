from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import video_projects


MAESTRO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_ROOT = MAESTRO_ROOT / "ferramentas" / "video_global_engine"
PROJECTS_ROOT = VIDEO_ROOT / "projetos"
PROJECT_ID = "ffviii_clones_liveaction_intro_faithful_v1"
PROJECT_DIR = PROJECTS_ROOT / PROJECT_ID


class FfviiiH3CombatRuntimeTests(unittest.TestCase):
    def test_m08_resolves_first_frame_only_h3_after_exact_human_gate(self) -> None:
        queue = json.loads(
            (PROJECT_DIR / "take_queue.json").read_text(encoding="utf-8-sig")
        )
        take = next(item for item in queue["takes"] if item["id"] == "M08")
        take = copy.deepcopy(take)
        take["video_generation_forbidden"] = False
        take["base_image"]["status"] = video_projects.ANCHOR_APPROVED_STATUS
        take["base_image"]["human_approval"] = "APPROVED"
        take["base_image"]["may_feed_video"] = True
        queue["takes"] = [
            take if item["id"] == "M08" else item for item in queue["takes"]
        ]

        keyframe = Path(take["base_image"]["file"]).resolve()
        metadata = Path(take["base_image"]["metadata"]).resolve()
        validated_anchor = (
            keyframe,
            metadata,
            take["base_image"],
            {"validation_status": video_projects.ANCHOR_APPROVED_STATUS},
            {"width": 1664, "height": 936},
            str(take["base_image"]["image_sha256"]),
        )

        with (
            patch.object(video_projects, "_queue", return_value=queue),
            patch.object(
                video_projects,
                "_validated_registered_anchor",
                return_value=validated_anchor,
            ),
            patch.object(
                video_projects,
                "_anchor_visible_cast",
                return_value=["Squall", "Seifer"],
            ),
        ):
            spec = video_projects.get_take_generation_spec(
                PROJECTS_ROOT,
                PROJECT_ID,
                "M08",
            )

        self.assertEqual(spec["generationProfile"], "minimax_h3_fl2va_int8_720p24")
        self.assertEqual((spec["width"], spec["height"], spec["fps"]), (1280, 720, 24))
        self.assertEqual(spec["frames"], 243)
        self.assertAlmostEqual(spec["durationSeconds"], 10.083333333333334)
        self.assertIsNone(spec["endKeyframe"])
        self.assertTrue(spec["visualOnlyPass"])
        self.assertEqual(spec["expectedHumanCast"], ["Squall", "Seifer"])
        self.assertEqual(spec["anchorVisibleCast"], ["Squall", "Seifer"])
        self.assertEqual(spec["takeExecutionContract"]["anchorBinding"], "first_frame_exact")
        self.assertEqual(spec["takeExecutionContract"]["motionBinding"], "prompt_guided")
        self.assertIn("1.35 to 1.50 metre", spec["prompt"])
        self.assertIn("Action, camera, rain, spray", spec["prompt"])


if __name__ == "__main__":
    unittest.main()
