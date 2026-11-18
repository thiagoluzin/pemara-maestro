from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class QwenAutoReleaseUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "app" / "assets" / "maestro.js").read_text(
            encoding="utf-8",
        )

    def test_dashboard_exposes_automatic_release_controls(self):
        self.assertIn('id="qwen-auto-release-enabled"', self.html)
        self.assertIn('id="qwen-auto-release-delay"', self.html)
        self.assertIn('id="qwen-auto-release-status"', self.html)
        self.assertIn('value="30"', self.html)

    def test_controls_use_same_origin_protected_settings_route(self):
        self.assertIn("/api/settings/qwen-auto-release", self.javascript)
        self.assertIn("configure-qwen-auto-release-v1", self.javascript)
        self.assertIn("enabled: toggle.checked", self.javascript)
        self.assertIn("idleSeconds: Number(delay.value)", self.javascript)

    def test_status_renders_countdown_and_manual_fallback(self):
        self.assertIn("remainingSeconds", self.javascript)
        self.assertIn("GPU será liberada em", self.javascript)
        self.assertIn("Liberar agora", self.html)


if __name__ == "__main__":
    unittest.main()
