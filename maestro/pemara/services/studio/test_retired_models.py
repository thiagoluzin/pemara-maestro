"""Retired choices cannot enqueue graphs or silently change the chosen engine."""
import ast
from pathlib import Path
from unittest.mock import Mock

import pytest
from retired_models import ModelRetiredError, require_model_allowed, require_workflow_allowed
from image_engines import ENGINES, QWEN_MODEL, describe, resolve, build_workflow


@pytest.mark.parametrize("engine,model", [
    ("llada_base", "LLaDA-Image-Base-BF16-AIO.safetensors"),
    ("llada_turbo", "LLaDA-Image-Turbo-BF16-AIO.safetensors"),
    ("flux3_klein", "flux3-image-klein-int8-convrot.safetensors"),
    ("z_image", "Z-Image.safetensors"),
    ("hunyuan_video_15", "hunyuanvideo1.5_720p_i2v_fp16.safetensors"),
])
def test_retired_requests_fail_even_with_stale_ready_catalog(engine, model):
    stale = [{"id": engine, "model": model, "modes": ["image"], "ready": True}]
    with pytest.raises(ModelRetiredError):
        resolve(engine, model, "image", stale)
    with pytest.raises(ModelRetiredError):
        build_workflow(engine, "teapot", "", 1024, 1024, 40, 1, 42, "qa")


def test_remaining_image_catalog_and_explicit_selection():
    assert [e["id"] for e in ENGINES] == ["qwen21", "qwen21_fix", "hidream_o1"]
    files = lambda folder: [name for e in ENGINES for group, name in e["requirements"] if group == folder]
    selected = resolve("qwen21", QWEN_MODEL, "image", describe(files, online=True))
    assert selected["model"] == QWEN_MODEL


def test_imported_retired_model_graph_is_blocked_before_comfy_or_gpu_calls():
    source = ast.parse(Path(__file__).with_name("main.py").read_text(encoding="utf-8-sig"))
    fn = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "_comfy_request")
    dlss = Mock();upscale = Mock()
    scope = {"Dict": dict, "Any": object, "_require_workflow_allowed": require_workflow_allowed,
             "_dlss5": dlss, "_required_upscale": upscale}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<maestro-comfy-gate>", "exec"), scope)
    graph = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev.safetensors"}}}
    with pytest.raises(ModelRetiredError):
        scope["_comfy_request"]("/prompt", {"prompt": graph})
    assert not dlss.mock_calls and not upscale.mock_calls


def test_graph_guard_keeps_shared_assets_and_does_not_parse_prompt_prose():
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "A poster saying flux1-dev.safetensors"}},
    }
    require_workflow_allowed(graph)
    require_model_allowed("HunyuanVideo-Foley", "audio_foley")
    require_model_allowed("hunyuan3d-dit-v2-1/model.fp16.ckpt", "hunyuan_3d")
    graph["4"] = {"class_type": "subgraph", "inputs": {}, "children": [
        {"class_type": "VAELoader", "inputs": {"vae_name": "hunyuanvideo15_vae_fp16.safetensors"}}
    ]}
    with pytest.raises(ModelRetiredError):
        require_workflow_allowed(graph)
