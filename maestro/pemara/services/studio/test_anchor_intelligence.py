from __future__ import annotations

import unittest

from anchor_intelligence.compiler_h3 import compile_h3_prompt
from anchor_intelligence.compiler_ltx25 import compile_ltx25_prompt, ltx25_frame_count
from anchor_intelligence.reconciler import AnchorConflictError, reconcile_anchor_contract
from anchor_intelligence.schema import AnchorContractError, build_anchor_contract, validate_anchor_contract


def sample_contract(**overrides):
    values = {
        "evidence": {
            "subjects": [
                {
                    "id": "subject_1",
                    "count": 1,
                    "visible_identity_markers": ["black swept hair", "blue jacket"],
                    "pose": "standing in left third, facing right",
                    "confidence": 0.96,
                }
            ],
            "environment": {"location": "stone courtyard", "weather": "clear"},
            "composition": {"shot_size": "medium wide", "subject_count": 1},
            "objects": ["one wooden crate behind subject"],
            "visible_text": [],
            "uncertainties": [],
        },
        "intent": {
            "action": "the subject takes two steps forward and raises the right hand",
            "preserve": ["subject_1 identity", "blue jacket", "one wooden crate"],
            "explicit_changes": [],
            "new_elements_allowed": [],
            "sound": "two footsteps on stone and cloth movement",
        },
        "invariants": [
            {"target": "subject_1 identity", "rule": "preserve face, hair, body proportions and blue jacket"},
            {"target": "subject count", "rule": "exactly one"},
            {"target": "screen geography", "rule": "courtyard and crate remain fixed"},
        ],
        "allowed_transformations": ["two forward steps", "right hand raises", "subtle cloth response"],
        "negative_constraints": ["no extra people", "no wardrobe change"],
        "temporal_plan": [
            {"phase": "0-30%", "action": "weight shifts and first step begins"},
            {"phase": "30-70%", "action": "second step completes"},
            {"phase": "70-100%", "action": "right hand raises and settles"},
        ],
        "camera_plan": {"movement": "slow physical dolly in", "axis": "keep left-to-right axis"},
    }
    values.update(overrides)
    return build_anchor_contract(**values)


class AnchorIntelligenceTests(unittest.TestCase):
    def test_contract_is_deterministic_and_tamper_evident(self) -> None:
        contract = sample_contract()
        self.assertEqual(contract["contract_id"], sample_contract()["contract_id"])
        validate_anchor_contract(contract)
        contract["intent"]["action"] = "a different action"
        with self.assertRaises(AnchorContractError) as raised:
            validate_anchor_contract(contract)
        self.assertEqual(raised.exception.code, "ANCHOR_CONTRACT_ID_MISMATCH")

    def test_reconciliation_builds_do_not_invent_constraints(self) -> None:
        result = reconcile_anchor_contract(sample_contract())
        self.assertTrue(result["ready"])
        combined = " ".join(result["do_not_invent"]).casefold()
        self.assertIn("do not add subjects", combined)
        self.assertIn("subject_1 identity", combined)

    def test_change_against_invariant_requires_owner_decision(self) -> None:
        contract = sample_contract(
            intent={
                "action": "replace the visible person while walking",
                "preserve": [],
                "explicit_changes": [{"target": "subject_1 identity", "change": "replace face"}],
            }
        )
        with self.assertRaises(AnchorConflictError):
            reconcile_anchor_contract(contract, raise_on_blocker=True)

    def test_engine_compilers_keep_same_contract_id(self) -> None:
        contract = sample_contract()
        h3 = compile_h3_prompt(contract, duration_seconds=6)
        ltx = compile_ltx25_prompt(contract, duration_seconds=6, width=960, height=544)
        self.assertEqual(h3["anchor_contract_id"], contract["contract_id"])
        self.assertEqual(ltx["anchor_contract_id"], contract["contract_id"])
        self.assertEqual(ltx["parameters"]["num_frames"] % 8, 1)
        self.assertNotEqual(h3["prompt"], ltx["prompt"])
        self.assertIn("no extra people", h3["negative_prompt"])
        self.assertIn("no extra people", ltx["negative_prompt"])

    def test_ltx_frame_rule_rounds_to_nearest_8n_plus_1(self) -> None:
        for duration in (1, 5, 6, 10, 15, 30):
            frames = ltx25_frame_count(duration, 24)
            self.assertEqual(frames % 8, 1)


if __name__ == "__main__":
    unittest.main()
