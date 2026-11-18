from __future__ import annotations

import unittest

from ltx25_workflow import (
    LTX25_TEXT_ENCODER,
    LTX25_TRANSFORMER,
    build_ltx25_i2v_workflow,
)


class Ltx25WorkflowTests(unittest.TestCase):
    def build(self, *, end: str = "") -> dict:
        return build_ltx25_i2v_workflow(
            prompt="The approved subject crosses the set with coherent physical motion.",
            negative="identity drift, duplicate subject",
            base_image_name="start.png",
            end_image_name=end,
            width=960,
            height=544,
            frames=145,
            fps=24,
            seed=20260902,
        )

    def test_one_anchor_uses_pinned_performance_assets_without_prompt_enhancer(self) -> None:
        workflow = self.build()
        self.assertEqual(workflow["5575:5569"]["inputs"]["unet_name"], LTX25_TRANSFORMER)
        self.assertEqual(workflow["5575:5574"]["inputs"]["clip_name"], LTX25_TEXT_ENCODER)
        self.assertEqual(workflow["5014:2483"]["inputs"]["text"], ["5508", 0])
        self.assertNotIn("audio", workflow["5518:4849"]["inputs"])
        self.assertNotIn(
            "TextGenerateLTX2Prompt",
            {node["class_type"] for node in workflow.values()},
        )

    def test_two_anchor_route_binds_final_frame_and_crops_guides(self) -> None:
        workflow = self.build(end="end.png")
        self.assertEqual(workflow["9101"]["inputs"]["frame_idx"], 0)
        self.assertEqual(workflow["9102"]["inputs"]["frame_idx"], -1)
        self.assertEqual(workflow["9102"]["inputs"]["strength"], 0.9)
        self.assertEqual(workflow["5517:4975"]["inputs"]["samples"], ["9201", 2])
        self.assertEqual(workflow["5518:5538"]["inputs"]["samples"], ["9202", 2])
        self.assertEqual(
            [node["class_type"] for node in workflow.values()].count("LoadImage"),
            2,
        )

    def test_invalid_frame_rule_fails_before_queue(self) -> None:
        with self.assertRaisesRegex(ValueError, "8n\+1"):
            build_ltx25_i2v_workflow(
                prompt="A valid long enough prompt for the workflow.",
                negative="",
                base_image_name="start.png",
                frames=144,
            )


if __name__ == "__main__":
    unittest.main()
