"""Omni must preserve references/audio and fail closed without its exact weights."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import main
from h3_omni import VARIANT, MODEL
from h3_workflow import validate_h3_comfy_graph
from video_engines.h3 import H3VideoEngine
from pathlib import Path


def build(**changes):
    args = dict(prompt="A red wooden toy rotates slowly on a table.", negative="",
        width=1088, height=608, frames=124, steps=8, seed=981,
        prefix="validation/fasth3_omni", base_image_name="",
        include_native_audio=True, h3_quality_profile="h3_production", h3_model_variant=VARIANT)
    args.update(changes)
    return main._build_minimax_h3_fl2va_workflow(**args)


class OmniTests(unittest.TestCase):
    def test_worker_dispatch_preserves_all_omni_inputs(self):
        queued = {}
        def queue(graph, **kwargs):
            queued.update(graph=graph)
            return "mock-omni", [{"kind": "video"}]
        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_h3_workflow_status_live", return_value={"capabilities": {"fastH3OmniReady": True}}),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(main, "_video_model_files", return_value=[main.MINIMAX_H3_MODEL_NAME]),
            patch.object(main, "_save_comfy_input_image", side_effect=lambda data, name, size, **kwargs: name),
            patch.object(main, "_save_comfy_input_video", return_value="motion.mp4"),
            patch.object(main, "_save_comfy_input_audio", return_value="voice.wav"),
            patch.object(main, "_queue_comfy_workflow", side_effect=queue),
            patch.object(main, "_finalize_video_mp4", side_effect=lambda outputs, **kw: outputs),
        ):
            result = main._run_generative(prompt="<Picture 1> moves like <Video 1>.",
                negative="", lora="", lora_strength=0, guidance=1, seed=981,
                mode="video", engine_id="minimax_h3", model=main.MINIMAX_H3_MODEL_NAME,
                h3_model_variant=VARIANT, h3_quality_profile="h3_production",
                width=1088, height=608, frames=124, fps=24, steps=8,
                base_image_bytes=b"image", base_image_name="hero.png",
                minimax_reference_images=[(b"image2", "prop.png")],
                minimax_reference_video_bytes=b"video", audio_conditioning_bytes=b"audio",
                enable_minimax_h3_native_audio=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["h3_model_variant"], VARIANT)
        self.assertEqual(queued["graph"]["1"]["inputs"]["unet_name"], MODEL)
        self.assertIn("ref_images.ref_image_2", queued["graph"]["6"]["inputs"])
        self.assertIn("ref_audios.ref_audio_1", queued["graph"]["6"]["inputs"])

    def test_text_and_image_routes_use_omni_ref_conditioning_with_audio(self):
        for name in ("", "reference.png"):
            g = build(base_image_name=name)
            self.assertEqual(g["1"]["inputs"]["unet_name"], MODEL)
            self.assertEqual(g["8"]["inputs"]["steps"], 8)
            self.assertEqual(g["2"]["inputs"]["shift_video"], 12)
            self.assertEqual(g["6"]["class_type"], "MiniMaxH3ReferenceToVideo")
            self.assertEqual(g["15"]["inputs"]["audio"], ["18", 0])
            self.assertNotIn("first_frame", g["6"]["inputs"])
            self.assertTrue(validate_h3_comfy_graph(g, mode="REF2VA", model_variant=VARIANT)["ok"])
            if name:
                self.assertEqual(g["omni_image_1"]["inputs"]["image"], name)
                self.assertIn("<Picture 1>", g["6"]["inputs"]["prompt"])

    def test_exact_endpoints_and_non_eight_steps_fail(self):
        for args in ({"end_image_name": "end.png"}, {"guide_image_name": "guide.png"},
                     {"allow_owner_long_window": True}, {"steps": 20}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                build(**args)

    def test_refs_are_connected_including_video_soundtrack_and_audio(self):
        g = main._build_minimax_h3_ref2va_workflow(
            prompt="<Picture 1> moves like <Video 1>, with <Audio 2>.", negative="",
            width=1088, height=608, frames=124, steps=8, seed=1, prefix="test/omni",
            reference_image_names=["ref.png"], reference_video_name="ref.mp4",
            reference_audio_names=["voice.wav"], include_native_audio=True,
            h3_quality_profile="h3_production", h3_model_variant=VARIANT)
        inputs = g["6"]["inputs"]
        self.assertEqual(inputs["ref_images.ref_image_1"], ["omni_image_1", 0])
        self.assertEqual(inputs["ref_videos.ref_video_1"], ["omni_video", 0])
        self.assertEqual(inputs["ref_video_audios.ref_video_audio_1"], ["omni_video", 2])
        self.assertEqual(inputs["ref_audios.ref_audio_1"], ["omni_audio_1", 0])

    def test_changed_checkpoint_shift_steps_and_sage_are_rejected(self):
        original = build()
        for defect in ("model", "shift", "steps", "sage"):
            g = deepcopy(original)
            if defect == "model": g["1"]["inputs"]["unet_name"] = main._FAST_H3_MODEL_NAME
            if defect == "shift": g["2"]["inputs"]["shift_video"] = 10
            if defect == "steps": g["8"]["inputs"]["steps"] = 20
            if defect == "sage":
                g["7"]["inputs"]["model"] = ["1", 0]
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                validate_h3_comfy_graph(g, mode="REF2VA", model_variant=VARIANT)

    def test_normalization_and_engine_keep_explicit_audio(self):
        spec = dict(prompt="test", mode="video", engine_id="minimax_h3",
            model=main.MINIMAX_H3_MODEL_NAME, h3_model_variant=VARIANT,
            h3_quality_profile="h3_production", steps=8, enable_minimax_h3_native_audio=True)
        out = main._normalize_generative_job_spec(spec)
        self.assertEqual(out["h3_model_variant"], VARIANT)
        self.assertEqual(out["steps"], 8)
        self.assertTrue(out["enable_minimax_h3_native_audio"])
        engine = H3VideoEngine(Path(main.BASE_DIR), comfy_online=False)
        self.assertTrue(engine.validate_request(spec)["enable_minimax_h3_native_audio"])
        self.assertEqual(engine.build_workflow(spec)["model"], MODEL)

    def test_live_readiness_requires_model_hash_nodes_and_acceleration(self):
        for missing in (None, "UNETLoader", "MiniMaxH3ReferenceToVideo", "SpectrumApplyMiniMaxH3"):
            def request(path, **kwargs):
                name = path.rsplit("/", 1)[-1]
                if name == missing: return {}
                if name == "UNETLoader":
                    return {name: {"input": {"required": {"unet_name": [[MODEL]]}}}}
                return {name: {}}
            with patch.object(main, "_h3_workflow_status", side_effect=lambda *a, **k: {
                    "capabilities": {"fastH3OmniFileReady": True}}), patch.object(main, "_comfy_request", side_effect=request):
                status = main._h3_workflow_status_live(comfy_online=True)
            self.assertEqual(status["capabilities"]["fastH3OmniReady"], missing is None)


if __name__ == "__main__":
    unittest.main()
