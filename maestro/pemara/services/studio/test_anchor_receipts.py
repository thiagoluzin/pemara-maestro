from __future__ import annotations

import hashlib
import unittest

import main
from anchor_intelligence.compiler_h3 import compile_h3_prompt
from anchor_intelligence.schema import build_anchor_contract


IMAGE_BYTES = b"owner-approved-anchor-pixels"


def _contract():
    return build_anchor_contract(
        evidence={
            "subjects": [{"id": "subject_1", "count": 1, "pose": "standing"}],
            "environment": {"location": "courtyard"},
            "composition": {"shot_size": "medium"},
            "objects": ["one crate"],
            "visible_text": [],
        },
        intent={"action": "take one step forward"},
        invariants=["preserve subject identity", "exactly one subject"],
        allowed_transformations=["one forward step"],
        negative_constraints=["no extra people"],
        source={
            "filename": "anchor.png",
            "mime_type": "image/png",
            "sha256": hashlib.sha256(IMAGE_BYTES).hexdigest(),
            "pixel_storage": "transient_memory_only",
        },
    )


class AnchorReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        with main._ANCHOR_RECEIPT_LOCK:
            main._ANCHOR_ANALYSIS_RECEIPTS.clear()
            main._ANCHOR_COMPILED_RECEIPTS.clear()

    def tearDown(self) -> None:
        with main._ANCHOR_RECEIPT_LOCK:
            main._ANCHOR_ANALYSIS_RECEIPTS.clear()
            main._ANCHOR_COMPILED_RECEIPTS.clear()

    def test_compiled_receipt_binds_image_engine_and_exact_prompt(self) -> None:
        contract = _contract()
        main._register_anchor_analysis_receipt(contract)
        compiled = compile_h3_prompt(contract, duration_seconds=6)
        main._register_compiled_anchor_receipt(contract, compiled)

        receipt = main._require_compiled_anchor_receipt(
            engine_id="minimax_h3",
            anchor_contract_id=contract["contract_id"],
            prompt_compiler_version=compiled["compiler_version"],
            prompt=compiled["prompt"],
            negative=compiled["negative_prompt"],
            image_bytes=IMAGE_BYTES,
        )

        self.assertEqual(receipt["engine_id"], "minimax_h3")
        self.assertEqual(receipt["source_sha256"], hashlib.sha256(IMAGE_BYTES).hexdigest())

    def test_tampered_prompt_or_image_fails_closed(self) -> None:
        contract = _contract()
        main._register_anchor_analysis_receipt(contract)
        compiled = compile_h3_prompt(contract, duration_seconds=6)
        main._register_compiled_anchor_receipt(contract, compiled)

        for prompt, pixels, mismatch in (
            (compiled["prompt"] + " invent something", IMAGE_BYTES, "prompt_sha256"),
            (compiled["prompt"], b"different-anchor", "source_sha256"),
        ):
            with self.subTest(mismatch=mismatch), self.assertRaises(main._VideoEngineError) as raised:
                main._require_compiled_anchor_receipt(
                    engine_id="minimax_h3",
                    anchor_contract_id=contract["contract_id"],
                    prompt_compiler_version=compiled["compiler_version"],
                    prompt=prompt,
                    negative=compiled["negative_prompt"],
                    image_bytes=pixels,
                )
            self.assertEqual(raised.exception.code, "ANCHOR_COMPILED_RECEIPT_MISMATCH")
            self.assertIn(mismatch, raised.exception.details["mismatches"])

    def test_unregistered_contract_cannot_be_compiled(self) -> None:
        with self.assertRaises(main._VideoEngineError) as raised:
            main._require_anchor_analysis_receipt(_contract())
        self.assertEqual(raised.exception.code, "ANCHOR_ANALYSIS_RECEIPT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
