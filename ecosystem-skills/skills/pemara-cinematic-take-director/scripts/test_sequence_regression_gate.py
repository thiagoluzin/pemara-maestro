from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sequence_regression_gate as gate


def dynamic_take() -> dict:
    return {
        "id": "M08",
        "visual_route_id": "route-live-action",
        "story_purpose": "Reveal the duel geography.",
        "story_change": "Both fighters close distance while the coast remains legible.",
        "reaction": "Each fighter reads the other's advance.",
        "cut_motivation": "Cut on continuing forward momentum.",
        "duration_reason": "The reveal and first advance need distinct beats.",
        "motion_beats": {
            "early_0_30": "Circle while the camera translates.",
            "middle_30_70": "Accelerate into the shared lane.",
            "late_70_100": "Continue advancing through the cut.",
        },
        "identity_contract": {
            "expected_characters": ["SQUALL", "SEIFER"],
            "forbidden_characters": ["RINOA"],
            "required_traits": ["one full Gunblade per fighter"],
            "forbidden_traits": ["duplicate weapons"],
            "identity_risk": "critical",
        },
        "video_generation": {
            "engine": "MiniMax H3",
            "input_mode": gate.DYNAMIC_CHAIN_INPUT_MODE,
            "choreography_freedom": True,
        },
        "internal_anchors": [],
        "end_image": {
            "status": gate.DYNAMIC_END_STATUS,
            "source_policy": gate.DYNAMIC_END_SOURCE_POLICY,
            "static_image_generation_forbidden": True,
            "exact_hash_registration_required": True,
            "strategy_decision_id": "OWNER_DIRECTED_H3_FREE_DUEL",
        },
        "art_direction_gate": {
            "precomputed_internal_anchors_required": False,
            "precomputed_end_anchor_required": False,
        },
    }


def manifest(take: dict) -> dict:
    return {
        "canonical_reference": {
            "project_id": gate.CANONICAL_PROJECT,
            "owner_declared_standard": True,
            "audited_artifacts": ["production_manifest.json"],
        },
        "art_direction_bible": {
            "style_mode": "photorealistic_live_action",
            "character_materials": {"SQUALL": "physical"},
            "character_anatomy": {"SQUALL": "two arms"},
            "environment": "rocky coast",
            "lens_language": "physical translation",
            "lighting": "storm daylight",
            "palette": "steel and blue",
            "forbidden_render_modes": ["anime"],
            "anchor_source_policy": "reuse_exact_owner_approved_images_no_regeneration",
        },
        "approval_policy": {
            "human_anchor_approval_required": True,
            "human_take_art_approval_required": True,
            "human_take_motion_approval_required": True,
            "human_final_playback_required": True,
            "auto_promote": False,
            "owner_rejection_auto_creates_same_scope_replacement": True,
            "preserve_rejected_artifacts": True,
            "block_rejected_from_assembly": True,
            "replacement_requires_separate_human_approval": True,
        },
        "generation_engine_policy": {
            "owner_selected_engine": "MiniMax H3",
            "allow_substitution_without_owner_approval": False,
        },
        "maestro_catalog_policy": {
            "visible_items": "main_takes_only",
            "internal_microsegments_visible": False,
        },
        "visual_route_id": "route-live-action",
        "h3_free_duel_strategy": {
            "decision_id": "OWNER_DIRECTED_H3_FREE_DUEL",
            "duel_take_ids": ["M08"],
            "serial_chain_rule": gate.DYNAMIC_SERIAL_CHAIN_RULE,
            "no_freeze_hold_crossfade_or_rife": True,
        },
        "takes": [take],
    }


class SequenceRegressionGateTests(unittest.TestCase):
    def test_dynamic_h3_chain_is_valid_high_risk_alternative_to_static_internal_anchors(self):
        data = manifest(dynamic_take())
        errors: list[str] = []

        gate.check_contract(data, errors)

        self.assertEqual(errors, [])

    def test_partial_dynamic_contract_does_not_bypass_internal_anchor_requirement(self):
        take = dynamic_take()
        take["end_image"]["source_policy"] = "ANY_FRAME"
        errors: list[str] = []

        gate.check_contract(manifest(take), errors)

        self.assertTrue(any("internal_anchors" in error for error in errors))
        self.assertTrue(any("h3_dynamic_chain" in error for error in errors))

    def test_maestro_sidecar_schema_is_accepted_only_with_explicit_human_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "M08.png"
            image.write_bytes(b"exact-anchor")
            image_sha256 = hashlib.sha256(image.read_bytes()).hexdigest()
            metadata = root / "M08.json"
            metadata.write_text(
                json.dumps(
                    {
                        "image_sha256": image_sha256,
                        "validation_status": "approved_for_video",
                        "human_review": {
                            "decision": "APPROVED",
                            "explicit_human_confirmation": True,
                        },
                        "approval_evidence": "Aprovado no Maestro.",
                    }
                ),
                encoding="utf-8",
            )
            asset = {
                "status": "approved_for_video",
                "file": str(image),
                "metadata": str(metadata),
                "sha256": image_sha256,
            }
            errors: list[str] = []

            gate.check_approved_asset(asset, "take[M08].base_image", root, errors)

            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
