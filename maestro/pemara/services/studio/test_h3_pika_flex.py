from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import main
from h3_pika_flex import VARIANT, build, validate_graph
from h3_workflow import ensure_h3_sage_attention, resolve_h3_quality_profile
from video_engines.h3 import H3VideoEngine


def graph(**changes):
    args = dict(prompt="A small orange toy robot waves once.", negative="", width=1088,
                height=608, frames=124, steps=6, seed=20261102, prefix="validation/pika_flex",
                native_audio=True, content_kind="animation")
    args.update(changes)
    return build(**args)


@pytest.mark.parametrize("inputs,mode", [({}, "T2VA"), ({"first": "first.png"}, "I2VA"),
    ({"first": "first.png", "last": "last.png"}, "FL2VA"),
    ({"references": ["subject.png", "scene.png"]}, "REF2VA")])
def test_connected_official_modes(inputs, mode):
    candidate = graph(**inputs)
    assert validate_graph(candidate)["mode"] == mode
    assert candidate["16"]["inputs"]["audio"] == ["15", 0]
    assert not any("Spectrum" in node["class_type"] for node in candidate.values())


@pytest.mark.parametrize("defect", ["lora", "sage", "guard", "sampler", "sigmas", "spectrum", "audio"])
def test_modified_experiment_is_rejected(defect):
    candidate = graph()
    if defect == "lora": candidate["2"]["inputs"]["lora_name"] = "other.safetensors"
    if defect == "sage": candidate["4"]["inputs"]["model"] = ["2", 0]
    if defect == "guard": candidate["4"]["inputs"]["head_chunks"] = 2
    if defect == "sampler": candidate["10"]["inputs"]["sampler_name"] = "res_multistep"
    if defect == "sigmas": candidate["11"]["inputs"]["sigmas"] = "1, 0.5, 0"
    if defect == "spectrum": candidate["extra"] = {"class_type": "SpectrumApplyMiniMaxH3", "inputs": {}}
    if defect == "audio": candidate["15"]["inputs"]["samples"] = ["8", 1]
    with pytest.raises(ValueError): validate_graph(candidate)


def test_pika_requires_explicit_queue_variant_and_does_not_relax_base():
    with pytest.raises(ValueError, match="SAMPLER_UNSUPPORTED"):
        ensure_h3_sage_attention(deepcopy(graph()))
    for variant in ("base", VARIANT):
        sent = []
        def request(path, *args, **kwargs):
            if path == "/object_info/SaveVideo": return {}
            if path == "/prompt":
                sent.append(args[0]["prompt"])
                raise RuntimeError("captured before network send")
            raise AssertionError(path)
        with patch.object(main, "_comfy_request", side_effect=request):
            with pytest.raises((RuntimeError, ValueError)):
                main._queue_comfy_workflow(graph(), timeout=1, h3_model_variant=variant)
        assert bool(sent) == (variant == VARIANT)


def test_six_steps_are_variant_specific_and_adapter_keeps_them():
    assert resolve_h3_quality_profile("h3_production", steps=6, model_variant=VARIANT)[0] == "h3_production"
    with pytest.raises(ValueError): resolve_h3_quality_profile("h3_production", steps=6, model_variant="base")
    engine = H3VideoEngine(workspace_root=Path(main.BASE_DIR), comfy_online=True)
    spec = engine.validate_request({"engine_id": "minimax_h3", "mode": "text_video", "h3_model_variant": VARIANT,
        "h3_quality_profile": "h3_production", "steps": 6, "video_duration": 6})
    assert spec["steps"] == 6


@pytest.mark.parametrize("photo", [False, True])
def test_worker_and_persisted_job_keep_pika_and_native_audio(photo):
    captured = {}
    def enqueue(candidate, **kwargs):
        captured.update(graph=candidate, kwargs=kwargs)
        return "pika-test", [{"kind": "video"}]
    engine = SimpleNamespace(id="minimax_h3", readiness=lambda: {"production_ready": True})
    with (
        patch.object(main, "_resolve_video_engine", return_value=(engine, main.MINIMAX_H3_MODEL_NAME)),
        patch.object(main, "_require_authorized_video_engine"),
        patch.object(main, "_comfy_online", return_value=(True, {})),
        patch.object(main, "_comfy_request", side_effect=AssertionError("unit test must not contact Comfy")),
        patch.object(main, "_h3_workflow_status_live", return_value={"capabilities": {"pikaFlexReady": True}}),
        patch.object(main, "_model_files", return_value=[]),
        patch.object(main, "_video_model_files", return_value=[main.MINIMAX_H3_MODEL_NAME]),
        patch.object(main, "_queue_comfy_workflow", side_effect=enqueue),
        patch.object(main, "_save_comfy_input_image", side_effect=lambda data, name, size, **kw: name),
        patch.object(main, "_finalize_video_mp4", side_effect=lambda outputs, **kw: outputs),
    ):
        spec = main._normalize_generative_job_spec({"mode": "video", "engine_id": "minimax_h3",
            "h3_model_variant": VARIANT, "h3_quality_profile": "h3_production", "steps": 6,
            "prompt": 'The robot says "Olá".', "video_duration": 6, "content_kind": "animation"})
        assert spec["h3_model_variant"] == VARIANT and spec["steps"] == 6
        result = main._run_generative(prompt=spec["prompt"], mode="video", engine_id="minimax_h3",
            model=main.MINIMAX_H3_MODEL_NAME, h3_model_variant=VARIANT, h3_quality_profile="h3_production",
            negative="", lora="", lora_strength=0, width=1088, height=608, frames=124, steps=6,
            guidance=1, seed=20261102, fps=24, video_duration=6, content_kind="animation",
            base_image_bytes=b"photo" if photo else None, base_image_name="photo.png" if photo else "")
    assert result["h3_model_variant"] == VARIANT
    assert captured["kwargs"]["h3_model_variant"] == VARIANT
    assert validate_graph(captured["graph"])["ok"]
    assert "audio" in captured["graph"]["16"]["inputs"]
    assert ("first_frame" in captured["graph"]["8"]["inputs"]) == photo


def test_unqualified_controls_fail_before_queue():
    with pytest.raises(ValueError, match="experimental aceita"):
        main._build_minimax_h3_fl2va_workflow("test", "", 1088, 608, 124, 6, 1, "qa", "",
            h3_model_variant=VARIANT, enable_live_preview=True)
