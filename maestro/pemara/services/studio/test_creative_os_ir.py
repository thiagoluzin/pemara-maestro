import unittest
from creative_os.ir import CreativeError, digest, features, validate_ir


def sample():
    return {"version": "0.2", "project_id": "audit", "shot_id": "SH01", "duration_seconds": 5,
            "content": {"action": {"primary": "leaves sway", "sequence": ["leaves sway"]}},
            "generation": {"preferred_engine": "h3", "quality_mode": "balanced"}}


class IRTests(unittest.TestCase):
    def test_valid_and_copy(self):
        value = sample()
        result = validate_ir(value)
        result["content"]["action"]["primary"] = "changed"
        self.assertEqual(value["content"]["action"]["primary"], "leaves sway")
        self.assertEqual(features(value)["action_count"], 1)

    def test_invalid_contracts(self):
        for key, value in [("duration_seconds", float("nan")), ("duration_seconds", True), ("shot_id", "../x"), ("version", "1")]:
            p = sample(); p[key] = value
            with self.assertRaises(CreativeError): validate_ir(p)

    def test_no_runtime_in_ir(self):
        p = sample(); p["content"]["node_id"] = "11"
        with self.assertRaisesRegex(CreativeError, "runtime"): validate_ir(p)

    def test_asset_escape(self):
        p = sample(); p["content"]["reference"] = "asset://hero/../secret"
        with self.assertRaises(CreativeError): validate_ir(p)

    def test_digest_stable(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))
