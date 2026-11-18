import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mova_runtime


class MovaRuntimeTests(unittest.TestCase):
    def test_progress_protocol_is_bounded_and_rejects_noise(self):
        self.assertEqual(
            mova_runtime._parse_progress("MAESTRO_PROGRESS\t105\tCodificando.\n"),
            (99, "Codificando."),
        )
        self.assertEqual(
            mova_runtime._parse_progress("MAESTRO_PROGRESS\t0\tPreparando.\n"),
            (1, "Preparando."),
        )
        self.assertIsNone(mova_runtime._parse_progress("download 72%\n"))
        self.assertIsNone(mova_runtime._parse_progress("MAESTRO_PROGRESS\tx\terro\n"))

    def test_complete_install_waits_for_128gb_profile(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            model = root / "model"
            source = root / "source"
            engine = root / "engine"
            python = engine / "Scripts" / "python.exe"
            runner = engine / "runner.py"
            marker = engine / "runtime-ready.json"
            (source / "mova").mkdir(parents=True)
            model.mkdir()
            python.parent.mkdir(parents=True)
            (source / "mova" / "__init__.py").write_text("", encoding="utf-8")
            (model / "model_index.json").write_text("{}", encoding="utf-8")
            python.write_text("", encoding="utf-8")
            runner.write_text("", encoding="utf-8")
            marker.write_text(
                json.dumps({
                    "ok": True,
                    "torch_compile": True,
                    "triton": "3.7.1",
                    "cuda_allocator": "cudaMallocAsync",
                    "nvenc": "h264_nvenc",
                    "capability": [12, 0],
                }),
                encoding="utf-8",
            )

            targets = {
                "MOVA_MODEL_DIR": model,
                "MOVA_SOURCE_DIR": source,
                "MOVA_PYTHON": python,
                "MOVA_RUNNER": runner,
                "MOVA_RUNTIME_MARKER": marker,
            }
            with patch.multiple(mova_runtime, **targets), patch.object(
                mova_runtime, "_model_progress", return_value=(100, 100, [])
            ), patch.object(mova_runtime, "_physical_ram_gb", return_value=63.1), patch.object(
                mova_runtime, "_available_ram_gb", return_value=48.0
            ), patch.object(mova_runtime, "_free_vram_gb", return_value=30.0), patch.object(
                mova_runtime, "_free_disk_gb", return_value=100.0
            ):
                status = mova_runtime.mova_status()
                self.assertTrue(status["model_complete"])
                self.assertTrue(status["runtime_ready"])
                self.assertFalse(status["enough_ram"])
                self.assertFalse(status["ready"])
                self.assertIn("128 GB", status["message"])

            with patch.multiple(mova_runtime, **targets), patch.object(
                mova_runtime, "_model_progress", return_value=(100, 100, [])
            ), patch.object(mova_runtime, "_physical_ram_gb", return_value=127.8), patch.object(
                mova_runtime, "_available_ram_gb", return_value=104.0
            ), patch.object(mova_runtime, "_free_vram_gb", return_value=30.0), patch.object(
                mova_runtime, "_free_disk_gb", return_value=100.0
            ):
                status = mova_runtime.mova_status()
                self.assertTrue(status["ready"])
                self.assertEqual(status["profile"]["resolution"], "832x480")
                self.assertEqual(status["profile"]["steps"], 25)
                self.assertTrue(status["profile"]["approval_gate_before_upscale"])
                self.assertEqual(status["profile"]["fps"], 24)
                self.assertEqual(status["profile"]["encoder"], "h264_nvenc")
                self.assertEqual(status["profile"]["triton"], "3.7.1")
                self.assertEqual(
                    status["profile"]["cuda_allocator"],
                    "cudaMallocAsync",
                )
                self.assertEqual(status["available_ram_gb"], 104.0)
                self.assertEqual(status["free_vram_gb"], 30.0)
                self.assertEqual(
                    status["available_profiles"]["master_720p"]["status"],
                    "blocked_until_final_take_approval",
                )

            marker.write_text("{}", encoding="utf-8")
            with patch.multiple(mova_runtime, **targets), patch.object(
                mova_runtime, "_model_progress", return_value=(100, 100, [])
            ), patch.object(mova_runtime, "_physical_ram_gb", return_value=127.8), patch.object(
                mova_runtime, "_available_ram_gb", return_value=104.0
            ), patch.object(mova_runtime, "_free_vram_gb", return_value=30.0), patch.object(
                mova_runtime, "_free_disk_gb", return_value=100.0
            ):
                status = mova_runtime.mova_status()
                self.assertFalse(status["runtime_ready"])
                self.assertFalse(status["ready"])

    def test_generation_never_accepts_sub_24fps(self):
        with patch.object(mova_runtime, "mova_status", return_value={"ready": True}):
            with self.assertRaisesRegex(ValueError, "24 FPS"):
                mova_runtime.run_mova_generation(
                    prompt="cinematic scene",
                    negative_prompt="",
                    seed=7,
                    width=1280,
                    height=720,
                    frames=193,
                    fps=16,
                    steps=50,
                    guidance=5,
                    base_image_bytes=None,
                    base_image_name="",
                    output_root=Path(tempfile.gettempdir()),
                    ffmpeg="ffmpeg",
                )

    def test_generation_rejects_unknown_geometry(self):
        with patch.object(mova_runtime, "mova_status", return_value={"ready": True}):
            with self.assertRaisesRegex(ValueError, "candidato 832x480"):
                mova_runtime.run_mova_generation(
                    prompt="cinematic scene",
                    negative_prompt="",
                    seed=7,
                    width=960,
                    height=540,
                    frames=49,
                    fps=24,
                    steps=25,
                    guidance=5,
                    base_image_bytes=None,
                    base_image_name="",
                    output_root=Path(tempfile.gettempdir()),
                    ffmpeg="ffmpeg",
                )

    def test_runtime_uses_python_without_roaming_user_packages(self):
        source = Path(mova_runtime.__file__).read_text(encoding="utf-8")

        self.assertIn('str(MOVA_PYTHON),\n            "-s",', source)
        self.assertIn('process_env["PYTORCH_ALLOC_CONF"] = "backend:cudaMallocAsync"', source)
        self.assertIn('process_env["CUDA_MODULE_LOADING"] = "LAZY"', source)
        self.assertIn('process_env["HF_HUB_OFFLINE"] = "1"', source)

    def test_canonical_mova_runner_stays_absent_after_uninstall(self):
        self.assertFalse(Path(mova_runtime.MOVA_RUNNER).exists())

    def test_resource_preflight_stops_before_model_load(self):
        with patch.object(mova_runtime, "mova_status", return_value={"ready": True}), patch.object(
            mova_runtime, "_available_ram_gb", return_value=40.0
        ), patch.object(mova_runtime, "_free_vram_gb", return_value=30.0), patch.object(
            mova_runtime, "_free_disk_gb", return_value=100.0
        ):
            with self.assertRaisesRegex(RuntimeError, "Preflight MOVA"):
                mova_runtime.run_mova_generation(
                    prompt="cinematic scene",
                    negative_prompt="",
                    seed=7,
                    width=832,
                    height=480,
                    frames=97,
                    fps=24,
                    steps=25,
                    guidance=5,
                    base_image_bytes=None,
                    base_image_name="",
                    output_root=Path(tempfile.gettempdir()),
                    ffmpeg="ffmpeg",
                )


if __name__ == "__main__":
    unittest.main()
