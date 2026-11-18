import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent


class MaestroOperatorRestartContractTests(unittest.TestCase):
    def test_restart_requests_are_delegated_to_radar_not_direct_process_kills(self):
        source = (ROOT / "solicitar_reinicio_maestro.ps1").read_text(encoding="utf-8-sig")

        self.assertIn("studio_restart_requested.flag", source)
        self.assertIn("maestro_frontend_restart_requested.flag", source)
        self.assertIn("supervisor administrativo Radar", source)
        self.assertIn("Test-Http", source)
        self.assertIn("pidfile.lock", source)
        self.assertIn("Get-Process -Id", source)
        self.assertNotIn("Stop-Process", source)

    def test_windows_shortcuts_have_distinct_start_and_restart_actions(self):
        start = (WORKSPACE / "INICIAR_MAESTRO.bat").read_text(encoding="utf-8-sig")
        restart = (WORKSPACE / "REINICIAR_MAESTRO.bat").read_text(encoding="utf-8-sig")
        stop = (WORKSPACE / "PARAR_MAESTRO.bat").read_text(encoding="utf-8-sig")

        self.assertIn("pemara_boot_watchdog.ps1 -Once", start)
        self.assertIn("solicitar_reinicio_maestro.ps1 -Componente all", restart)
        self.assertIn("sem acao destrutiva", stop)
        for shortcut in (start, restart, stop):
            self.assertNotIn("pause", shortcut.lower())


if __name__ == "__main__":
    unittest.main()
