import unittest
from creative_os.routing import capabilities, route
from test_creative_os_ir import sample


class RoutingTests(unittest.TestCase):
    def test_recommendation_never_changes_engine(self):
        p = sample(); p["generation"]["preferred_engine"] = "ltx25"
        p["analysis_hints"] = {"physical_interaction": "high", "weapon_persistence": "critical"}
        caps = {"engines": {"ltx_2_5": {"runnable": True}, "minimax_h3": {"runnable": True}}}
        r = route(p, caps)
        self.assertEqual(r["recommendations"][0]["engine_id"], "minimax_h3")
        self.assertEqual(r["selected_engine"], "ltx_2_5")
        self.assertFalse(r["can_generate"])
        self.assertIn("ENGINE_REMOVED", r["blocked"])
        p["generation"]["preferred_engine"] = "auto"
        self.assertFalse(route(p, caps)["can_generate"])

    def test_nodes_without_weights_not_runnable(self):
        desc = [{"id": "minimax_h3", "readiness": {"production_ready": False}}]
        result = capabilities(desc, {"MiniMaxH3ImageToVideo": {}, "UNETLoader": {}, "SaveVideo": {}})
        self.assertFalse(result["engines"]["minimax_h3"]["runnable"])
        self.assertFalse(result["optional"]["h3_fun_control"]["enabled"])

    def test_pose_is_not_reference_video(self):
        p=sample(); p["control_source"]={"pose_video": "asset://motion/pose"}
        self.assertIn("EXACT_CONTROL_NOT_INTEGRATED", route(p, {})["blocked"])
