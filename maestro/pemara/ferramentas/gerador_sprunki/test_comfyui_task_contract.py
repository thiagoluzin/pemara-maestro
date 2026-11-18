from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
INSTALLER = HERE / "install_comfyui_watchdog_task.ps1"
RESTART = HERE.parent / "ComfyUI" / "restart_comfy.ps1"


class ComfyTaskContractTests(unittest.TestCase):
    def test_installer_disables_legacy_direct_start_task(self):
        source = INSTALLER.read_text(encoding="utf-8-sig")

        self.assertIn('[string]$LegacyTaskName = "PemaraComfyUI"', source)
        self.assertIn("Disable-ScheduledTask -TaskName $LegacyTaskName", source)

    def test_admin_restart_uses_watchdog_as_only_start_authority(self):
        source = RESTART.read_text(encoding="utf-8-sig")

        self.assertIn('[string]$TaskName = "Pemara ComfyUI Watchdog"', source)
        self.assertIn("Disable-ScheduledTask -TaskName $LegacyTaskName", source)
        self.assertNotIn('[string]$TaskName = "PemaraComfyUI"', source)


if __name__ == "__main__":
    unittest.main()
