import tempfile
import unittest
from pathlib import Path

import security_release_gate as gate


class SecurityReleaseGateTests(unittest.TestCase):
    def test_template_requires_review(self):
        receipt = gate.template("Loja", "local")
        decision, diagnostics = gate.validate(receipt)
        self.assertEqual(decision, "BLOCKED")
        self.assertTrue(diagnostics)

    def test_complete_receipt_passes(self):
        receipt = gate.template("Loja", "local")
        receipt["scope_owned_or_authorized"] = True
        receipt["inventory_evidence"] = ["inventario.json"]
        for group in (receipt["controls"], receipt["validation"]):
            for item in group.values():
                item.update(status="pass", evidence=["teste comprovado"])
        receipt["data_integrity"] = {"status": "pass", "evidence": ["restore-compare.json"]}
        receipt["rollback"] = {"status": "pass", "evidence": ["backup.sha256"]}
        decision, diagnostics = gate.validate(receipt)
        self.assertEqual(decision, "PASS")
        self.assertEqual(diagnostics, [])

    def test_quarantine_is_not_pass(self):
        receipt = gate.template("Jornada", "local")
        receipt["scope_owned_or_authorized"] = True
        receipt["inventory_evidence"] = ["surface.json"]
        for group in (receipt["controls"], receipt["validation"]):
            for item in group.values():
                item.update(status="not_applicable", evidence=["justificativa registrada"])
        receipt["validation"]["web_baseline"] = {"status": "quarantined", "evidence": ["HTTP 530 esperado"]}
        receipt["data_integrity"] = {"status": "not_applicable", "evidence": ["sem mutacao de dados"]}
        receipt["rollback"] = {"status": "not_applicable", "evidence": ["sem mutacao"]}
        decision, _ = gate.validate(receipt)
        self.assertEqual(decision, "QUARANTINE")

    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "receipt.json"
            original = gate.template("Studio", "local")
            gate.write_json(path, original)
            self.assertEqual(gate.load_json(path)["target"], "Studio")


if __name__ == "__main__":
    unittest.main()
