from __future__ import annotations

import unittest

from maestro_turbo.anchor_intelligence.analyzer import (
    MAX_ANCHOR_BYTES,
    AnchorImageError,
    parse_vision_response,
    validate_anchor_image,
)
from maestro_turbo.anchor_intelligence.compiler_h3 import compile_h3_prompt
from maestro_turbo.anchor_intelligence.compiler_ltx25 import compile_ltx25_prompt, ltx25_frame_count
from maestro_turbo.anchor_intelligence.reconciler import AnchorConflictError, reconcile_anchor_contract
from maestro_turbo.anchor_intelligence.schema import AnchorContractError, build_anchor_contract, validate_anchor_contract


def sample_contract(**overrides):
    values = {
        "evidence": {
            "subjects": [{"id": "subject_1", "count": 1, "visible_identity_markers": ["blue jacket"], "confidence": 0.96}],
            "environment": {"location": "stone courtyard"},
            "composition": {"shot_size": "medium wide", "subject_count": 1},
            "objects": ["one wooden crate"],
            "visible_text": [],
            "uncertainties": [],
        },
        "intent": {
            "action": "the subject takes two steps forward and raises the right hand",
            "preserve": ["subject_1 identity", "blue jacket", "one wooden crate"],
            "explicit_changes": [],
            "new_elements_allowed": [],
            "sound": "two footsteps on stone",
        },
        "invariants": [
            {"target": "subject_1 identity", "rule": "preserve visible identity and clothing"},
            {"target": "subject count", "rule": "exactly one"},
        ],
        "allowed_transformations": ["two forward steps", "right hand raises"],
        "negative_constraints": ["no extra people", "no wardrobe change"],
        "temporal_plan": [{"phase": "0-100%", "action": "one continuous movement"}],
        "camera_plan": {"movement": "slow dolly", "axis": "unchanged"},
    }
    values.update(overrides)
    return build_anchor_contract(**values)


class AnchorIntelligenceTests(unittest.TestCase):
    def test_anchor_rejects_unknown_bytes_and_mime_mismatch(self):
        with self.assertRaises(AnchorImageError):
            validate_anchor_image(b"not-an-image", "image/png")
        with self.assertRaises(AnchorImageError):
            validate_anchor_image(b"\x89PNG\r\n\x1a\nfixture", "image/jpeg")

    def test_anchor_size_limit_fails_before_model_request(self):
        with self.assertRaises(AnchorImageError) as raised:
            validate_anchor_image(b"\x89PNG\r\n\x1a\n" + b"0" * MAX_ANCHOR_BYTES, "image/png")
        self.assertEqual(raised.exception.code, "ANCHOR_IMAGE_TOO_LARGE")

    def test_vision_response_must_be_structured_evidence(self):
        with self.assertRaises(AnchorImageError):
            parse_vision_response('{"analysis_notes":"unsupported guess"}')

    def test_contract_is_deterministic_and_tamper_evident(self):
        contract = sample_contract()
        self.assertEqual(contract["contract_id"], sample_contract()["contract_id"])
        validate_anchor_contract(contract)
        contract["intent"]["action"] = "different"
        with self.assertRaises(AnchorContractError):
            validate_anchor_contract(contract)

    def test_conflict_fails_closed(self):
        contract = sample_contract(intent={"action": "replace identity", "explicit_changes": [{"target": "subject_1 identity", "change": "replace"}]})
        with self.assertRaises(AnchorConflictError):
            reconcile_anchor_contract(contract, raise_on_blocker=True)

    def test_compilers_share_contract_but_not_prompt(self):
        contract = sample_contract()
        h3 = compile_h3_prompt(contract)
        ltx = compile_ltx25_prompt(contract)
        self.assertEqual(h3["anchor_contract_id"], ltx["anchor_contract_id"])
        self.assertNotEqual(h3["prompt"], ltx["prompt"])
        self.assertEqual(ltx["parameters"]["num_frames"] % 8, 1)

    def test_frame_rule(self):
        for duration in (1, 5, 6, 10, 15, 30):
            self.assertEqual(ltx25_frame_count(duration, 24) % 8, 1)


if __name__ == "__main__":
    unittest.main()
