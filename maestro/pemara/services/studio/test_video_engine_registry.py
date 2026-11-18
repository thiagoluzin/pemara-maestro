from __future__ import annotations

import unittest
from pathlib import Path

from video_engines.base import EngineError, EngineSelectionRequired
from video_engines.registry import build_video_engine_registry


WORKSPACE = Path(__file__).resolve().parents[2]


class VideoEngineRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_video_engine_registry(WORKSPACE, comfy_online=True)

    def test_only_owner_authorized_engines_are_registered(self) -> None:
        self.assertEqual(self.registry.ids, ("minimax_h3",))

    def test_missing_selection_fails_closed(self) -> None:
        with self.assertRaises(EngineSelectionRequired) as raised:
            self.registry.get("")
        self.assertEqual(raised.exception.code, "ENGINE_SELECTION_REQUIRED")

    def test_removed_or_unknown_engine_never_falls_back(self) -> None:
        for engine_id in ("ltx_2_5", "ltx_2_3", "LTX-2.3", "wan", "automatic"):
            with self.subTest(engine_id=engine_id), self.assertRaises(EngineError) as raised:
                self.registry.get(engine_id)
            self.assertEqual(raised.exception.code, "ENGINE_NOT_ALLOWED")

    def test_public_contract_has_no_default_or_fallback(self) -> None:
        public = self.registry.describe()
        self.assertTrue(public["selection_required"])
        self.assertIsNone(public["default_engine_id"])
        self.assertFalse(public["fallback_allowed"])
        self.assertEqual([item["id"] for item in public["engines"]], ["minimax_h3"])

    def test_owner_removed_hunyuan_fails_without_engine_replacement(self) -> None:
        with self.assertRaises(EngineError) as raised:
            self.registry.get("hunyuan_video_15")
        self.assertEqual(raised.exception.code, "ENGINE_REMOVED_BY_OWNER")
        self.assertEqual(raised.exception.status_code, 410)

    def test_fast_h3_engine_preflight_is_t2v_only_and_fixes_steps(self) -> None:
        engine = self.registry.get("minimax_h3")
        validated = engine.validate_request({
            "mode": "text_video",
            "h3_model_variant": "fasth3_8step_v2",
            "h3_quality_profile": "h3_production",
            "h3_orientation": "portrait",
            "width": 1088,
            "height": 608,
            "steps": 8,
            "enable_minimax_h3_native_audio": True,
            "duration_seconds": 10,
        })
        self.assertEqual((validated["width"], validated["height"]), (608, 1088))
        self.assertEqual(validated["steps"], 8)
        self.assertFalse(validated["enable_minimax_h3_native_audio"])
        self.assertEqual(engine.build_workflow(validated)["model"], "fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors")
        with self.assertRaisesRegex(EngineError, "somente texto para vídeo"):
            engine.validate_request({
                "mode": "video",
                "h3_model_variant": "fasth3_8step_v2",
                "h3_quality_profile": "h3_production",
                "steps": 8,
            })


if __name__ == "__main__":
    unittest.main()
