import unittest
from unittest.mock import patch
from retired_models import ModelRetiredError

from video_workflows import (
    build_hunyuan15_i2v_workflow,
    build_hunyuan15_sr_workflow,
    validate_video_fps,
)


class Hunyuan15WorkflowTests(unittest.TestCase):
    """Historical graph topology; active engine retirement is tested separately."""

    def setUp(self):
        policy = patch("video_workflows.require_model_allowed")
        policy.start()
        self.addCleanup(policy.stop)
    def test_global_policy_accepts_16_fps_for_wan_native_contract(self):
        self.assertEqual(validate_video_fps(16), 16)

    def test_global_policy_accepts_24_30_and_60_fps(self):
        self.assertEqual(validate_video_fps(24), 24)
        self.assertEqual(validate_video_fps(30), 30)
        self.assertEqual(validate_video_fps(60), 60)

    def test_builds_official_720p_i2v_topology(self):
        workflow = build_hunyuan15_i2v_workflow(
            prompt="A physical event unfolds while the camera pushes forward.",
            negative="static, frozen, text, watermark",
            input_image="approved_take.png",
            width=1280,
            height=720,
            frames=121,
            fps=24,
            steps=20,
            seed=123,
            latent_prefix="maestro_video/latents/take_01",
        )

        self.assertEqual(workflow["1"]["class_type"], "UNETLoader")
        self.assertEqual(workflow["9"]["inputs"]["length"], 121)
        self.assertEqual(workflow["10"]["inputs"]["shift"], 7.0)
        self.assertEqual(workflow["14"]["inputs"]["model"], ["hunyuan_easycache", 0])
        self.assertEqual(workflow["hunyuan_easycache"]["inputs"]["model"], ["10", 0])
        self.assertEqual(workflow["10"]["inputs"]["model"], ["hunyuan_safe_acceleration", 0])
        self.assertEqual(workflow["18"]["inputs"]["format"], "mp4")
        self.assertEqual(workflow["19"]["class_type"], "SaveLatent")
        self.assertEqual(workflow["hunyuan_easycache"]["class_type"], "EasyCache")

    def test_rejects_invalid_temporal_length(self):
        with self.assertRaisesRegex(ValueError, "4n \\+ 1"):
            build_hunyuan15_i2v_workflow(
                prompt="motion",
                negative="",
                input_image="approved.png",
                frames=120,
            )

    def test_i2v_workflow_rejects_16_fps(self):
        with self.assertRaisesRegex(ValueError, "proibido"):
            build_hunyuan15_i2v_workflow(
                prompt="motion",
                negative="",
                input_image="approved.png",
                frames=121,
                fps=16,
            )

    def test_builds_official_1080p_super_resolution_topology(self):
        workflow = build_hunyuan15_sr_workflow(
            prompt="Camera pushes through moving particles.",
            negative="static, text",
            input_latent="take_01.latent",
            input_image="take_01.png",
            fps=30,
            seed=321,
        )
        self.assertEqual(workflow["4"]["inputs"]["width"], 1920)
        self.assertEqual(workflow["4"]["inputs"]["height"], 1080)
        self.assertEqual(workflow["14"]["inputs"]["steps"], 8)
        self.assertEqual(workflow["15"]["inputs"]["step"], 4)
        self.assertEqual(workflow["18"]["inputs"]["cfg"], 1.0)
        self.assertEqual(workflow["25"]["inputs"]["format"], "mp4")
        self.assertNotIn("EasyCache", {node["class_type"] for node in workflow.values()})


class RetiredHunyuanWorkflowTests(unittest.TestCase):
    def test_both_old_builders_reject_before_constructing_an_unusable_workflow(self):
        with self.assertRaises(ModelRetiredError):
            build_hunyuan15_i2v_workflow(prompt="motion", negative="", input_image="approved.png")
        with self.assertRaises(ModelRetiredError):
            build_hunyuan15_sr_workflow(prompt="motion", negative="", input_latent="take.latent", input_image="approved.png")


if __name__ == "__main__":
    unittest.main()
