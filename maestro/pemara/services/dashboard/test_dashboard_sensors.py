import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODULE_PATH = Path(__file__).resolve().with_name("main.py")
SPEC = importlib.util.spec_from_file_location("maestro_dashboard_main", MODULE_PATH)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)

STUDIO_HARDWARE_PATH = PROJECT_ROOT / "services" / "studio" / "hardware_status.py"
STUDIO_HARDWARE_SPEC = importlib.util.spec_from_file_location(
    "maestro_studio_hardware_status",
    STUDIO_HARDWARE_PATH,
)
studio_hardware = importlib.util.module_from_spec(STUDIO_HARDWARE_SPEC)
STUDIO_HARDWARE_SPEC.loader.exec_module(studio_hardware)


class FakeNvml:
    NVML_TEMPERATURE_GPU = 0
    NVML_CLOCK_GRAPHICS = 0
    NVML_CLOCK_MEM = 1

    def __init__(self, unsupported_optional=False):
        self.unsupported_optional = unsupported_optional
        self.init_calls = 0
        self.shutdown_calls = 0
        self.handle_calls = 0

    def nvmlInit(self):
        self.init_calls += 1

    def nvmlShutdown(self):
        self.shutdown_calls += 1

    def nvmlDeviceGetHandleByIndex(self, index):
        self.handle_calls += 1
        return f"fresh-{self.handle_calls}"

    def nvmlDeviceGetTemperature(self, handle, sensor):
        if handle == "stale":
            raise OSError("exception: access violation")
        return 79

    def nvmlDeviceGetUtilizationRates(self, handle):
        return SimpleNamespace(gpu=95, memory=73)

    def nvmlDeviceGetMemoryInfo(self, handle):
        return SimpleNamespace(used=25 * 1024**3, total=32 * 1024**3)

    def nvmlDeviceGetName(self, handle):
        return b"NVIDIA GeForce RTX 5090"

    def nvmlDeviceGetFanSpeed(self, handle):
        if self.unsupported_optional:
            raise RuntimeError("Not Supported")
        return 82

    def nvmlDeviceGetPowerUsage(self, handle):
        if self.unsupported_optional:
            raise RuntimeError("Not Supported")
        return 575_150

    def nvmlDeviceGetEnforcedPowerLimit(self, handle):
        return 575_000

    def nvmlDeviceGetClockInfo(self, handle, clock):
        if self.unsupported_optional:
            raise RuntimeError("Not Supported")
        return 2782 if clock == self.NVML_CLOCK_GRAPHICS else 13801

    def nvmlDeviceGetCudaComputeCapability(self, handle):
        return (12, 0)


class DashboardGpuSensorTests(unittest.TestCase):
    def setUp(self):
        self.original_gpu_state = (
            dashboard._pynvml,
            dashboard._HAS_GPU,
            dashboard._gpu_handle,
            dashboard._gpu_last_error,
        )

    def tearDown(self):
        (
            dashboard._pynvml,
            dashboard._HAS_GPU,
            dashboard._gpu_handle,
            dashboard._gpu_last_error,
        ) = self.original_gpu_state

    def test_stale_nvml_handle_is_reinitialized_and_retried(self):
        fake = FakeNvml()
        dashboard._pynvml = fake
        dashboard._HAS_GPU = True
        dashboard._gpu_handle = "stale"
        dashboard._gpu_last_error = None

        result = dashboard._gpu_dados()

        self.assertNotIn("erro", result)
        self.assertEqual(result["nome"], "NVIDIA GeForce RTX 5090")
        self.assertEqual(result["load"], 95)
        self.assertEqual(result["vram_t"], 32.0)
        self.assertEqual(result["fan"], 82)
        self.assertEqual(result["compute"], "sm_120")
        self.assertEqual(fake.shutdown_calls, 1)
        self.assertEqual(fake.init_calls, 1)
        self.assertEqual(dashboard._gpu_handle, "fresh-1")
        self.assertTrue(dashboard._HAS_GPU)

    def test_gpu_recovers_when_driver_becomes_available_after_startup(self):
        fake = FakeNvml()
        dashboard._pynvml = fake
        dashboard._HAS_GPU = False
        dashboard._gpu_handle = None
        dashboard._gpu_last_error = "Driver Not Loaded"

        result = dashboard._gpu_dados()

        self.assertNotIn("erro", result)
        self.assertEqual(result["temp"], 79)
        self.assertIsNone(dashboard._gpu_last_error)
        self.assertTrue(dashboard._HAS_GPU)

    def test_unsupported_optional_sensors_are_not_reported_as_zero(self):
        fake = FakeNvml(unsupported_optional=True)
        dashboard._pynvml = fake
        dashboard._HAS_GPU = True
        dashboard._gpu_handle = "fresh"
        dashboard._gpu_last_error = None

        result = dashboard._gpu_dados()

        self.assertIsNone(result["fan"])
        self.assertIsNone(result["power_w"])
        self.assertIsNone(result["power_pct"])
        self.assertIsNone(result["clock_gpu"])


class DashboardSystemSensorTests(unittest.TestCase):
    def test_disk_and_network_rates_use_the_real_time_module(self):
        disk_samples = iter(
            [
                SimpleNamespace(read_bytes=0, write_bytes=0),
                SimpleNamespace(read_bytes=1024**2, write_bytes=512 * 1024),
            ]
        )
        network_samples = iter(
            [
                SimpleNamespace(bytes_sent=0, bytes_recv=0),
                SimpleNamespace(bytes_sent=1024, bytes_recv=2048),
            ]
        )
        fake_psutil = SimpleNamespace(
            cpu_percent=lambda interval: 42.5,
            cpu_freq=lambda: SimpleNamespace(current=4201),
            virtual_memory=lambda: SimpleNamespace(
                total=64 * 1024**3,
                used=32 * 1024**3,
                percent=50.0,
            ),
            sensors_temperatures=lambda: {
                "coretemp": [SimpleNamespace(current=56.5)]
            },
            disk_io_counters=lambda: next(disk_samples),
            net_io_counters=lambda: next(network_samples),
            cpu_count=lambda logical: 8 if logical else 4,
        )

        with patch.dict(sys.modules, {"psutil": fake_psutil}):
            with patch.object(dashboard.time, "sleep") as sleep, patch.object(
                dashboard.time, "monotonic", side_effect=[10.0, 10.0, 10.2, 10.2]
            ):
                result = dashboard._sistema_dados()

        self.assertEqual(result["nvme_leit_mbs"], 5.0)
        self.assertEqual(result["nvme_esc_mbs"], 2.5)
        self.assertEqual(result["net_sent_kbs"], 5.0)
        self.assertEqual(result["net_recv_kbs"], 10.0)
        self.assertEqual(result["cpu_temp"], 56.5)
        sleep.assert_not_called()


class FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class StudioHardwareStatusTests(unittest.TestCase):
    def test_studio_reads_gpu_metrics_from_the_canonical_dashboard(self):
        payload = {
            "gpu_disponivel": True,
            "gpu": {
                "nome": "NVIDIA GeForce RTX 5090",
                "load": 96,
                "temp": 79,
                "vram_u": 25.59,
                "vram_t": 31.84,
                "fan": 82,
                "compute": "sm_120",
            },
        }
        with patch.object(
            studio_hardware.urllib.request,
            "urlopen",
            return_value=FakeHttpResponse(payload),
        ) as urlopen:
            gpu, error = studio_hardware.dashboard_gpu_snapshot(timeout=0.5)

        self.assertIsNone(error)
        self.assertEqual(gpu["load"], 96)
        self.assertEqual(gpu["vram_t"], 31.84)
        urlopen.assert_called_once_with(
            studio_hardware.DASHBOARD_SNAPSHOT_URL,
            timeout=0.5,
        )

    def test_studio_propagates_sensor_failure_instead_of_inventing_zeroes(self):
        payload = {
            "gpu_disponivel": False,
            "gpu": {"erro": "Driver Not Loaded"},
        }
        with patch.object(
            studio_hardware.urllib.request,
            "urlopen",
            return_value=FakeHttpResponse(payload),
        ):
            gpu, error = studio_hardware.dashboard_gpu_snapshot()

        self.assertEqual(gpu, {})
        self.assertEqual(error, "Driver Not Loaded")


class DashboardTelemetryUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javascript = (
            PROJECT_ROOT / "app" / "assets" / "maestro.js"
        ).read_text(encoding="utf-8")
        cls.html = (PROJECT_ROOT / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        cls.restart_script = (
            PROJECT_ROOT / "reset_maestro_frontend.ps1"
        ).read_text(encoding="utf-8")
        cls.studio_source = (
            PROJECT_ROOT / "services" / "studio" / "main.py"
        ).read_text(encoding="utf-8")
        cls.studio_restart_script = (
            PROJECT_ROOT / "services" / "studio" / "restart_studio.ps1"
        ).read_text(encoding="utf-8")
        cls.radar_source = (
            PROJECT_ROOT.parents[1] / "radar" / "radar_monitor.py"
        ).read_text(encoding="utf-8")

    def test_ui_never_invents_a_16_gb_gpu_when_collection_fails(self):
        self.assertNotIn("gpu.vram_t ?? 16", self.javascript)
        self.assertIn("data.gpu_disponivel !== false", self.javascript)
        self.assertIn('$("#gpu-vram").textContent = "-- / -- GB";', self.javascript)

    def test_sensor_fix_has_a_new_browser_cache_version(self):
        self.assertIn("maestro.js?v=20260730-sensor-recovery1", self.html)

    def test_supervised_frontend_reset_can_reload_only_the_dashboard_sidecar(self):
        self.assertIn("dashboard_restart_requested.flag", self.restart_script)
        self.assertIn("$managedPorts += 8007", self.restart_script)
        self.assertIn("Test-DashboardSensors", self.restart_script)

    def test_studio_does_not_keep_a_second_nvml_session(self):
        self.assertIn("from hardware_status import dashboard_gpu_snapshot", self.studio_source)
        self.assertNotIn("nvmlDeviceGetHandleByIndex", self.studio_source)
        self.assertNotIn("HAS_SENSORS", self.studio_source)
        status_source = self.studio_source[
            self.studio_source.index('@app.get("/api/status")'):
            self.studio_source.index('@app.get("/api/generative/status")')
        ]
        self.assertNotIn("torch.cuda", status_source)

    def test_studio_restart_uses_the_lightweight_readiness_route(self):
        self.assertIn(
            'Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status"',
            self.studio_restart_script,
        )
        self.assertIn('STUDIO_READINESS_URL = "http://127.0.0.1:8029/api/status"', self.radar_source)
        self.assertIn(
            "http_health(STUDIO_READINESS_URL",
            self.radar_source,
        )


if __name__ == "__main__":
    unittest.main()
