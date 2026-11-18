import unittest
from creative_os.adapters import H3Adapter, adapter_for
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class AdapterTests(unittest.TestCase):
    def test_h3_preserves_profile_and_audio(self):
        p=sample(); a=H3Adapter()
        job=a.build_job(p, {})
        self.assertEqual((job["width"], job["height"], job["steps"]), (1088,608,10))
        self.assertIn("[Shot 1]", job["prompt"])
        p["generation"]["native_audio"]=True
        self.assertFalse(a.build_job(p, {"h3_quality_profile":"h3_draft"})["enable_minimax_h3_native_audio"])

    def test_wrong_engine_and_unsupported_control_fail(self):
        with self.assertRaises(CreativeError): adapter_for("ltx_2_5")
        p=sample(); p["control_source"]={"pose_video":"asset://motion/pose"}
        with self.assertRaises(CreativeError): H3Adapter().build_job(p, {})

    def test_removed_ltx_adapter_fails_closed(self):
        with self.assertRaises(CreativeError): adapter_for("ltx_2_5")
