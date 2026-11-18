from __future__ import annotations

import unittest

from maestro_turbo.video_engines.base import EngineError, EngineSelectionRequired
from maestro_turbo.video_engines.ltx25 import LTX25_NODE_COMMIT, LTX25_VERSION
from maestro_turbo.video_engines.registry import build_video_engine_registry


class EngineRegistryTests(unittest.TestCase):
    def test_exact_engine_set_and_no_automatic_choice(self):
        registry = build_video_engine_registry()
        self.assertEqual(registry.ids, ("minimax_h3", "ltx_2_5"))
        public = registry.describe()
        self.assertTrue(public["selection_required"])
        self.assertIsNone(public["default_engine_id"])
        self.assertFalse(public["fallback_allowed"])

    def test_missing_and_removed_engine_fail_closed(self):
        registry = build_video_engine_registry()
        with self.assertRaises(EngineSelectionRequired):
            registry.get("")
        for engine_id in ("ltx_2_3", "automatic", "wan"):
            with self.subTest(engine_id=engine_id), self.assertRaises(EngineError):
                registry.get(engine_id)

    def test_ltx_readiness_requires_real_smoke(self):
        attestation = {
            "ltx_2_5": {
                "model_version": LTX25_VERSION,
                "node_commit": LTX25_NODE_COMMIT,
                "core_assets_verified": True,
                "workflows_verified": True,
                "gpu_smoke_pass": False,
            }
        }
        readiness = build_video_engine_registry(attestation).get("ltx_2_5").readiness()
        self.assertEqual(readiness["state"], "READY_FOR_GPU_SMOKE")
        self.assertFalse(readiness["production_ready"])
        attestation["ltx_2_5"]["gpu_smoke_pass"] = True
        readiness = build_video_engine_registry(attestation).get("ltx_2_5").readiness()
        self.assertEqual(readiness["state"], "READY")
        self.assertTrue(readiness["production_ready"])


if __name__ == "__main__":
    unittest.main()
