"""Hunyuan integration checks without sending jobs or querying ComfyUI."""
import io
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from video_engines.hunyuan15 import Hunyuan15VideoEngine
from video_workflows import HUNYUAN15_I2V_MODEL


class HunyuanIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = Hunyuan15VideoEngine(self.root, comfy_online=True)

    def test_profile_and_unsupported_controls(self):
        spec = self.engine.validate_request({"video_duration": 10})
        self.assertEqual((spec["frames"], spec["steps"], spec["fps"], spec["guidance"]), (241, 50, 24, 6))
        trial = self.engine.build_workflow({"steps": 25, "video_duration": 8, "content_kind": "live_action",
                                            "prompt": "Directed fight", "input_image": "approved.png"})
        self.assertEqual(trial["11"]["inputs"]["steps"], 25)
        self.assertEqual(trial["9"]["inputs"]["length"], 193)
        fast_trial = self.engine.build_workflow({"steps": 15, "video_duration": 10, "content_kind": "live_action",
                                                 "prompt": "Directed fight", "input_image": "approved.png"})
        self.assertEqual(fast_trial["11"]["inputs"]["steps"], 15)
        self.assertEqual(fast_trial["9"]["inputs"]["length"], 241)
        for extra in ({"steps": 20}, {"guidance": 1}, {"fps": 30}, {"frames": 120},
                      {"enable_minimax_h3_native_audio": True}, {"end_image_name": "end.png"},
                      {"loop": True}, {"mode": "text_video"}, {"video_duration": float("nan")}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.engine.validate_request(extra)

    def test_sampling_path_uses_safe_hunyuan_acceleration_and_single_cache(self):
        graph = self.engine.build_workflow({"prompt": "Directed fight", "input_image": "approved.png",
                                            "video_duration": 8, "content_kind": "live_action"})
        self.assertEqual(graph["10"]["inputs"]["model"], ["hunyuan_safe_acceleration", 0])
        self.assertEqual(graph["hunyuan_safe_acceleration"]["class_type"], "PemaraHunyuan15SafeAcceleration")
        self.assertTrue(graph["hunyuan_safe_acceleration"]["inputs"]["disable_dynamic_vram"])
        self.assertEqual(graph["14"]["inputs"]["model"], ["hunyuan_easycache", 0])
        self.assertEqual(graph["hunyuan_easycache"]["inputs"]["model"], ["10", 0])
        self.assertEqual(graph["11"]["inputs"]["steps"], 50)
        self.assertEqual(graph["9"]["inputs"]["length"], 193)
        self.assertFalse(any("Spectrum" in n["class_type"] or "Compile" in n["class_type"] for n in graph.values()))

    def test_partial_and_changed_asset_never_ready(self):
        self.assertFalse(self.engine.readiness()["production_ready"])
        assets = []
        import hashlib
        for i in range(5):
            path = self.root / f"asset{i}"
            path.write_bytes(b"test")
            digest = hashlib.sha256(b"test").hexdigest()
            assets.append(dict(filename=path.name, path=str(path), expected_bytes=4,
                sha256=digest, verified_sha256=digest, verified_mtime_ns=path.stat().st_mtime_ns))
        self.engine.manifest_path.parent.mkdir(parents=True)
        self.engine.manifest_path.write_text(json.dumps(dict(assets=assets, mcp_workflow_valid=True)))
        self.assertTrue(self.engine.readiness()["production_ready"])
        Path(assets[0]["path"]).write_bytes(b"bad!")
        self.assertFalse(self.engine.readiness()["production_ready"])

    def test_normalization_preserves_hunyuan_without_h3_rewrite(self):
        import main
        with patch.object(main, "_comfy_online", return_value=(False, {})):
            spec = main._normalize_generative_job_spec(dict(mode="video", engine_id=self.engine.id,
                content_kind="animation", prompt="Movimento dirigido", video_duration=5))
        self.assertEqual(spec["model"], HUNYUAN15_I2V_MODEL)
        self.assertEqual(spec["prompt"], "Movimento dirigido")
        self.assertEqual((spec["frames"], spec["fps"], spec["steps"]), (121, 24, 50))
        self.assertIsNone(spec["h3_quality_profile"])
        import inspect
        accepted = set(inspect.signature(main._run_generative).parameters) | {"content_kind"}
        self.assertFalse(set(spec) - accepted, "Normalized job must fit the real worker signature")

    def test_worker_preserves_portrait_timing_and_complete_anchor(self):
        import main
        source = io.BytesIO()
        Image.new("RGB", (100, 100), "red").save(source, format="PNG")
        class StopBeforeGPU(Exception):
            pass
        def capture(graph, **kwargs):
            self.assertEqual(graph["1"]["inputs"]["unet_name"], HUNYUAN15_I2V_MODEL)
            self.assertEqual((graph["9"]["inputs"]["width"], graph["9"]["inputs"]["height"]), (720, 1280))
            self.assertEqual(graph["17"]["inputs"]["fps"], 24)
            self.assertEqual(graph["10"]["inputs"]["shift"], 7)
            self.assertEqual(graph["11"]["inputs"]["steps"], 50)
            self.assertEqual(graph["16"]["inputs"]["temporal_size"], 4096)
            self.assertEqual(graph["3"]["inputs"]["text"], "Movimento dirigido")
            anchor = Image.open(self.root / graph["6"]["inputs"]["image"])
            self.assertEqual(anchor.size, (720, 1280))
            self.assertEqual(anchor.getpixel((360, 640)), (255, 0, 0))
            self.assertEqual(anchor.getpixel((360, 0)), (0, 0, 0))
            raise StopBeforeGPU()
        with ExitStack() as stack:
            for name, value in {"_video_generation_paused": lambda: False,
                    "_resolve_video_engine": lambda *a, **kw: (self.engine, HUNYUAN15_I2V_MODEL),
                    "_comfy_online": lambda: (True, {}), "_model_files": lambda *a, **kw: [HUNYUAN15_I2V_MODEL],
                    "_queue_comfy_workflow": capture}.items():
                stack.enter_context(patch.object(main, name, value))
            stack.enter_context(patch.object(self.engine, "readiness", return_value={"production_ready": True}))
            stack.enter_context(patch.object(main, "COMFY_INPUT_DIR", str(self.root)))
            stack.enter_context(patch.object(main, "_comfy_request", side_effect=AssertionError("No direct network")))
            with self.assertRaises(StopBeforeGPU):
                main._run_generative(prompt="Movimento dirigido", mode="video", engine_id=self.engine.id,
                    content_kind="animation", model=HUNYUAN15_I2V_MODEL, negative="", lora="", lora_strength=0,
                    width=720, height=1280, steps=50, guidance=6, frames=121, fps=24, seed=42,
                    video_duration=5, base_image_bytes=source.getvalue(), base_image_name="anchor.png")
