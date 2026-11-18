#!/usr/bin/env python3
"""Regression tests for the universal transition motion gate."""

from __future__ import annotations

import copy
import unittest

from transition_motion_gate import validate_manifest


def approved_manifest() -> dict:
    return {
        "project_id": "test_transition",
        "universal_transition_motion_gate": {"required": True},
        "continuous_action_contract": {
            "required": True,
            "generated_connector_required_between_takes": True,
            "crossfade_forbidden": True,
            "freeze_frame_forbidden": True,
            "static_tail_forbidden": True,
            "motion_handoff_required": True,
            "full_duration_motion_required": True,
            "three_interval_motion_required": True,
            "moving_transition_anchors_required": True,
        },
        "takes": [
            {
                "id": "T01",
                "transition": {"is_transition": True},
                "transition_motion_contract": {
                    "camera_evidence": {
                        "movement": "physical dolly backward with a left orbit",
                        "physical_translation": True,
                        "perspective_change": "foreground crosses the frame faster than the background",
                    },
                    "real_depth": {
                        "foreground": "broken headphones and cable",
                        "midground": "wet road and moving reflections",
                        "background": "studio entrance and distant fog",
                        "differential_motion": "foreground moves fastest and background moves slowest",
                        "occlusion_or_scale_change": "the cable reveals more road as the camera retreats",
                    },
                    "internal_action": {
                        "primary_event": "a signal ignites and escapes from the broken headphones",
                        "independent_elements": [
                            "the loose cable snaps and settles",
                            "two steam plumes cross separate depth planes",
                        ],
                        "camera_independent": True,
                    },
                    "progression": {
                        "start": "the headphones lie dark in the alley",
                        "middle": "the signal ignites and travels through the cable",
                        "end": "the signal leaves toward the distant studio",
                        "end_state_change": "the signal is now separated from the headphones",
                        "exit_or_cut": "cut on the signal direction toward the next take",
                    },
                    "continuity": {
                        "editorial_method": "generated_action_connector",
                        "continuous_action": True,
                        "motion_handoff": True,
                        "action_occupies_full_duration": True,
                        "entry_motion": "inherit the moving cable and forward camera velocity",
                        "exit_motion": "hand the moving signal direction into the next take",
                        "interval_motion": {
                            "early_0_30": "the cable keeps snapping while the camera advances",
                            "middle_30_70": "the signal crosses the cable as steam moves in depth",
                            "late_70_100": "the signal exits while camera and debris remain in motion",
                        },
                        "moving_anchor_context": {
                            "start_source": "take N00 frame 48 with motion before and after",
                            "start_has_motion_before_and_after": True,
                            "end_source": "take N02 frame 24 with motion before and after",
                            "end_has_motion_before_and_after": True,
                        },
                        "crossfade_frames": 0,
                        "freeze_frames": 0,
                        "static_hold_frames": 0,
                    },
                },
                "qc": {
                    "transition_motion_gate": {
                        "status": "approved",
                        "evident_camera": True,
                        "real_depth": True,
                        "internal_action": True,
                        "clear_progression": True,
                        "continuous_action": True,
                        "motion_across_all_intervals": True,
                        "moving_anchor_context": True,
                        "no_crossfade": True,
                        "no_freeze": True,
                        "no_static_tail": True,
                        "no_reset": True,
                        "evidence": "reviewed MP4 and first-middle-last contact sheet",
                    }
                },
            }
        ],
    }


class TransitionMotionGateTests(unittest.TestCase):
    def test_complete_contract_and_visual_qc_pass(self) -> None:
        errors, count = validate_manifest(approved_manifest(), "approval")
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])

    def test_missing_camera_translation_is_rejected(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        manifest["takes"][0]["transition_motion_contract"]["camera_evidence"][
            "physical_translation"
        ] = False
        errors, _ = validate_manifest(manifest, "contract")
        self.assertTrue(any("physical_translation" in error for error in errors))

    def test_missing_visual_pillar_is_rejected_at_approval(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        manifest["takes"][0]["qc"]["transition_motion_gate"]["real_depth"] = False
        errors, _ = validate_manifest(manifest, "approval")
        self.assertTrue(any("real_depth" in error for error in errors))

    def test_global_contract_forces_non_transition_take_through_gate(self) -> None:
        manifest = approved_manifest()
        manifest["project_id"] = "mixed_video_project"
        manifest["takes"].append({"id": "N01", "role": "dialogue"})
        errors, count = validate_manifest(manifest, "approval")
        self.assertEqual(count, 2)
        self.assertTrue(any("N01: missing transition_motion_contract" in error for error in errors))

    def test_crossfade_is_rejected_by_contract(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        continuity = manifest["takes"][0]["transition_motion_contract"]["continuity"]
        continuity["editorial_method"] = "crossfade"
        continuity["crossfade_frames"] = 12
        errors, _ = validate_manifest(manifest, "contract")
        self.assertTrue(any("editorial_method" in error for error in errors))
        self.assertTrue(any("crossfade_frames" in error for error in errors))

    def test_freeze_or_static_hold_is_rejected_by_contract(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        continuity = manifest["takes"][0]["transition_motion_contract"]["continuity"]
        continuity["freeze_frames"] = 3
        continuity["static_hold_frames"] = 6
        errors, _ = validate_manifest(manifest, "contract")
        self.assertTrue(any("freeze_frames" in error for error in errors))
        self.assertTrue(any("static_hold_frames" in error for error in errors))

    def test_continuity_qc_is_required_before_approval(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        manifest["takes"][0]["qc"]["transition_motion_gate"]["no_freeze"] = False
        errors, _ = validate_manifest(manifest, "approval")
        self.assertTrue(any("no_freeze" in error for error in errors))

    def test_global_continuous_action_policy_is_fail_closed(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        del manifest["continuous_action_contract"]["crossfade_forbidden"]
        errors, _ = validate_manifest(manifest, "contract")
        self.assertTrue(any("crossfade_forbidden" in error for error in errors))

    def test_full_duration_interval_motion_is_required(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        continuity = manifest["takes"][0]["transition_motion_contract"]["continuity"]
        continuity["action_occupies_full_duration"] = False
        continuity["interval_motion"]["late_70_100"] = ""
        errors, _ = validate_manifest(manifest, "contract")
        self.assertTrue(any("action_occupies_full_duration" in error for error in errors))
        self.assertTrue(any("late_70_100" in error for error in errors))

    def test_interval_motion_qc_is_required_before_approval(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        manifest["takes"][0]["qc"]["transition_motion_gate"][
            "motion_across_all_intervals"
        ] = False
        errors, _ = validate_manifest(manifest, "approval")
        self.assertTrue(any("motion_across_all_intervals" in error for error in errors))

    def test_transition_anchor_cannot_come_from_frozen_tail(self) -> None:
        manifest = copy.deepcopy(approved_manifest())
        continuity = manifest["takes"][0]["transition_motion_contract"]["continuity"]
        continuity["moving_anchor_context"]["start_has_motion_before_and_after"] = False
        errors, _ = validate_manifest(manifest, "contract")
        self.assertTrue(any("start_has_motion_before_and_after" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
