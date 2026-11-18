import hashlib
import json
import tempfile
from pathlib import Path
import unittest

from video_projects import (
    _take_view,
    _validate_take_execution_contract,
    _validate_wan_animate_pose_control,
)
from wan_animate_workflow import WAN22_ANIMATE_PROFILE


class WanAnimateProjectContractTests(unittest.TestCase):
    def setUp(self):
        self.queue = {
            "take_execution_contract": {
                "required": True,
                "declared_controls_must_exist_in_graph": True,
                "reference_is_not_anchor": True,
                "reference_video_is_not_pose_control": True,
                "model_mode_must_match_conditioning_node": True,
            }
        }

    def test_execution_contract_rejects_timeline_claim_for_single_reference_model(self):
        take = {
            "control_claims": {
                "anchor_binding": "timeline_exact",
                "motion_binding": "exact_pose",
            },
            "wan_animate_control": {"mode": "move"},
        }
        with self.assertRaisesRegex(ValueError, "nao implementa timeline de ancoras"):
            _validate_take_execution_contract(
                self.queue, take, generation_profile=WAN22_ANIMATE_PROFILE
            )

    def test_pose_control_rejects_procedural_driver(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "pose.json"
            manifest.write_text(json.dumps({
                "asset_type": "procedural_pose_blocking_preview",
                "status": "APPROVED_BY_OWNER",
            }), encoding="utf-8")
            take = {"wan_animate_control": {"mode": "move", "pose_manifest": "pose.json"}}
            with self.assertRaisesRegex(ValueError, "WAN_ANIMATE_POSE_NOT_DWPOSE"):
                _validate_wan_animate_pose_control(root, take)

    def test_pose_control_accepts_hashed_real_driver_and_owner_approved_dwpose(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            driver = root / "driver.mp4"
            pose = root / "pose.mp4"
            driver.write_bytes(b"real-driver")
            pose.write_bytes(b"dwpose")
            manifest = root / "pose.json"
            manifest.write_text(json.dumps({
                "asset_type": "dwpose_pose_video",
                "status": "APPROVED_BY_OWNER",
                "is_dwpose": True,
                "is_exact_pose_control": True,
                "face_transfer": "disabled",
                "source_driver_kind": "real_human_performance_video",
                "source_driver_file": str(driver),
                "source_driver_sha256": hashlib.sha256(driver.read_bytes()).hexdigest(),
                "file": str(pose),
                "sha256": hashlib.sha256(pose.read_bytes()).hexdigest(),
                "fps": 30,
                "width": 720,
                "height": 1280,
                "frames": 451,
            }), encoding="utf-8")
            take = {"wan_animate_control": {"mode": "move", "pose_manifest": "pose.json"}}
            result = _validate_wan_animate_pose_control(root, take)
            self.assertTrue(result["ownerApproved"])
            self.assertEqual(result["poseVideo"], pose.resolve())

    def test_take_view_blocks_unapproved_wan_pose_before_render(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            anchor = root / "anchor.png"
            anchor.write_bytes(b"anchor")
            take = {
                "id": "S01",
                "render_authorized": False,
                "base_image": {"status": "approved_for_video", "file": str(anchor)},
                "video_generation": {
                    "profile": WAN22_ANIMATE_PROFILE,
                    "width": 720,
                    "height": 1280,
                    "fps": 30,
                },
                "wan_animate_control": {"mode": "move"},
            }
            view = _take_view(take, root)
            self.assertFalse(view["canGenerate"])
            self.assertTrue(view["generationBlocked"])
            self.assertIn("performance humana real", view["generationBlockedReason"])
            self.assertEqual(view["engine"], "Wan2.2 Animate 14B BF16 + DWPose")
            self.assertEqual(view["stage"], "WAN_ANIMATE_DWPOSE_APPROVAL_GATE")

    def test_pose_control_accepts_owner_approved_synthetic_kinematic_pose(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            storyboard = root / "storyboard.jpg"
            pose = root / "pose.mp4"
            storyboard.write_bytes(b"owner-storyboard")
            pose.write_bytes(b"synthetic-dwpose")
            manifest = root / "pose.json"
            manifest.write_text(json.dumps({
                "asset_type": "dwpose_pose_video",
                "status": "APPROVED_BY_OWNER",
                "is_dwpose": True,
                "is_exact_pose_control": True,
                "is_synthetic_pose": True,
                "face_transfer": "disabled",
                "source_driver_kind": "synthetic_kinematic_pose_sequence",
                "reference_storyboard": str(storyboard),
                "reference_storyboard_sha256": hashlib.sha256(storyboard.read_bytes()).hexdigest(),
                "file": str(pose),
                "sha256": hashlib.sha256(pose.read_bytes()).hexdigest(),
                "fps": 30,
                "width": 720,
                "height": 1280,
                "frames": 109,
            }), encoding="utf-8")
            take = {"wan_animate_control": {"mode": "move", "pose_manifest": "pose.json"}}
            result = _validate_wan_animate_pose_control(root, take)
            self.assertTrue(result["ownerApproved"])
            self.assertEqual(result["sourceDriverKind"], "synthetic_kinematic_pose_sequence")


if __name__ == "__main__":
    unittest.main()
