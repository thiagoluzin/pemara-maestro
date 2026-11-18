from pathlib import Path
import unittest

from wan_animate_workflow import (
    WAN22_ANIMATE_MODEL_NAME,
    build_dwpose_preview_workflow,
    build_move_workflow,
    kit_status,
    validate_dwpose_preview_graph,
    validate_move_graph,
)


class WanAnimateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[2]

    def test_lock_has_complete_pinned_wan_animate_kit(self):
        status = kit_status(self.workspace)
        self.assertEqual(len(status["artifacts"]), 6)
        self.assertEqual(status["model"], WAN22_ANIMATE_MODEL_NAME)

    def test_dwpose_preview_enforces_body_hands_and_face_off(self):
        workflow = build_dwpose_preview_workflow(
            driver_video_name="driver.mp4",
            prefix="preview/dwpose",
        )
        self.assertTrue(validate_dwpose_preview_graph(workflow)["ok"])
        workflow["2"]["inputs"]["detect_face"] = "enable"
        with self.assertRaisesRegex(ValueError, "DWPOSE_FACE_FORBIDDEN"):
            validate_dwpose_preview_graph(workflow)

    def test_move_graph_binds_pose_to_every_chunk_without_speed_lora(self):
        workflow = build_move_workflow(
            prompt="live-action performers execute the approved motion",
            negative="animation, illustration",
            reference_image_name="approved.png",
            approved_pose_video_name="approved_dwpose.mp4",
            prefix="wan_animate/take",
            frames=451,
            seed=7,
        )
        result = validate_move_graph(workflow)
        self.assertEqual(result["chunks"], 7)
        self.assertTrue(result["poseConnected"])
        self.assertNotIn("LoraLoaderModelOnly", {node["class_type"] for node in workflow.values()})

    def test_move_graph_rejects_prompt_only_or_mix_mode(self):
        workflow = build_move_workflow(
            prompt="live action",
            negative="animation",
            reference_image_name="approved.png",
            approved_pose_video_name="approved_dwpose.mp4",
            prefix="wan_animate/take",
        )
        wan_id = next(key for key, node in workflow.items() if node["class_type"] == "WanAnimateToVideo")
        workflow[wan_id]["inputs"].pop("pose_video")
        with self.assertRaisesRegex(ValueError, "WAN_ANIMATE_POSE_DISCONNECTED"):
            validate_move_graph(workflow)

    def test_move_workflow_rejects_square_geometry(self):
        with self.assertRaisesRegex(ValueError, "WAN_ANIMATE_VERTICAL_GEOMETRY_REQUIRED"):
            build_move_workflow(
                prompt="live action",
                negative="animation",
                reference_image_name="approved.png",
                approved_pose_video_name="approved_dwpose.mp4",
                prefix="wan_animate/take",
                width=720,
                height=720,
                frames=109,
            )


if __name__ == "__main__":
    unittest.main()
