from __future__ import annotations

import json
import unittest
from pathlib import Path

from maestro_turbo.turbo_registry import TurboRegistryError, validate_turbo_registry


ROOT = Path(__file__).resolve().parents[1]


class TurboRegistryTests(unittest.TestCase):
    def test_public_registry_is_relative_and_disjoint(self):
        path = ROOT / "skills" / "pemara-messenger-turbo" / "references" / "turbo_registry.json"
        result = validate_turbo_registry(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(result["canonical_skill_root"], "skills")
        self.assertFalse(set(result["aliases"]) & set(result["specialized_profiles"]))

    def test_specialization_cannot_be_collapsed_into_alias(self):
        payload = {
            "schema_version": 1,
            "dispatcher_profile": "agents-turbo",
            "canonical_skill_root": "skills",
            "profile_root": "agents",
            "aliases": ["director"],
            "specialized_profiles": ["director"],
        }
        with self.assertRaises(TurboRegistryError):
            validate_turbo_registry(payload)


if __name__ == "__main__":
    unittest.main()
