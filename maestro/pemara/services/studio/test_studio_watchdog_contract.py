import unittest
from pathlib import Path


class StudioWatchdogContractTests(unittest.TestCase):
    def test_limited_watchdog_never_consumes_administrative_restart_flag(self):
        source = Path(__file__).with_name("watchdog_studio_generative.ps1").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("supervisor administrativo Radar", source)
        self.assertNotIn("Remove-Item -LiteralPath $RestartRequest", source)
        self.assertNotIn("Stop-Process -Id $ownerPid", source)


if __name__ == "__main__":
    unittest.main()
