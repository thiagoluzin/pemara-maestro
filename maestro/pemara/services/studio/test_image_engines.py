import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import patch

import pytest
import h3_scene_profiles
from retired_models import ModelRetiredError, require_model_allowed

from image_engines import ENGINES, QWEN_MODEL, FIX_LORA, FLUX_MODEL, LLADA_BASE, LLADA_TURBO, HIDREAM_MODEL, describe, resolve, build_workflow


def inventory(*, missing=()):
    return lambda folder: [name for engine in ENGINES for group, name in engine["requirements"]
                           if group == folder and name not in missing]


@pytest.mark.parametrize("engine_id,model,mode", [
    ("not-an-engine", "", "image"), ("qwen21", FLUX_MODEL, "image"),
    ("flux3_klein", "", "edit"), ("", "flux-2-klein-4b.safetensors", "image"),
])
def test_explicit_invalid_choices_never_fall_back(engine_id, model, mode):
    with pytest.raises(ValueError):
        resolve(engine_id, model, mode, describe(inventory(), online=True))


def test_missing_flux_or_fix_does_not_block_original_qwen():
    catalog = describe(inventory(missing=(FLUX_MODEL, FIX_LORA)), online=True)
    assert resolve("qwen21", QWEN_MODEL, "image", catalog)["id"] == "qwen21"
    for engine in ("qwen21_fix", "flux3_klein"):
        with pytest.raises(ValueError):
            resolve(engine, "", "image", catalog)


def test_offline_blocks_every_engine():
    for engine in describe(inventory(), online=False):
        with pytest.raises(ValueError):
            resolve(engine["id"], "", "image", [engine])


def test_partial_shared_download_is_not_advertised_as_ready(tmp_path):
    path = tmp_path / "loras" / FIX_LORA
    path.parent.mkdir()
    path.write_bytes(b"incomplete")
    catalog = describe(inventory(missing=(FIX_LORA,)), online=True, shared_root=tmp_path)
    assert not next(e for e in catalog if e["id"] == "qwen21_fix")["ready"]


def test_fix_reaches_sampler_and_leaves_original_unmodified():
    args = ("Blue teapot", "", 1024, 1024, 40, 1, 42, "qa")
    original = build_workflow("qwen21", *args)
    fixed = build_workflow("qwen21_fix", *args)
    assert original["6"]["inputs"]["model"] == ["1", 0]
    assert fixed["6"]["inputs"]["model"] == ["11", 0]
    assert fixed["11"]["inputs"]["lora_name"] == FIX_LORA
    assert fixed["11"]["inputs"]["model"] == ["1", 0]


def test_historical_flux_topology_remains_readable_without_reactivating_the_engine():
    with patch("image_engines.require_model_allowed"):
        graph = build_workflow("flux3_klein", "Blue teapot", "letters", 1024, 768, 16, 1, 42, "qa")
    assert graph["2"]["inputs"]["type"] == "flux3"
    assert graph["8"]["class_type"] == "EmptyFlux2LatentImage"
    assert graph["6"]["inputs"]["text"] == ["5", 0]
    assert graph["5"]["class_type"] == "TextGenerate"
    assert "letters" in graph["5"]["inputs"]["prompt"]
    assert graph["9"]["inputs"]["positive"] == ["6", 0]
    assert graph["5"]["inputs"]["sampling_mode.seed"] == 42


@pytest.mark.parametrize("engine_id,model", [
    ("hidream_o1", HIDREAM_MODEL),
])
def test_new_image_choices_are_explicit_and_fail_when_their_own_weights_are_missing(engine_id, model):
    assert resolve(engine_id, model, "image", describe(inventory(), online=True))["model"] == model
    with pytest.raises(ValueError):
        resolve(engine_id, model, "image", describe(inventory(missing=(model,)), online=True))
    with pytest.raises(ValueError):
        resolve(engine_id, model, "edit", describe(inventory(), online=True))


@pytest.mark.parametrize("engine_id,model,steps,sampler", [
    ("llada_base", LLADA_BASE, 50, "KSamplerSelect"),
    ("llada_turbo", LLADA_TURBO, 4, "T8SamplerLLaDAImageTurbo"),
])
def test_llada_uses_its_aio_and_native_sampler_path(engine_id, model, steps, sampler):
    with patch("image_engines.require_model_allowed"):
        graph = build_workflow(engine_id, "teapot", "letters", 1024, 768, steps, 5, 42, "qa")
    assert graph["1"]["inputs"]["ckpt_name"] == model
    assert graph["5"]["class_type"] == sampler
    assert graph["6"]["inputs"]["steps"] == steps
    assert graph["10"]["inputs"]["vae"] == ["1", 2]
    assert graph["9"]["inputs"]["sigmas"] == ["6", 0]
    if engine_id == "llada_turbo":
        assert graph["4"]["inputs"]["cfg"] == 1
        with pytest.raises(ValueError):
            build_workflow(engine_id, "teapot", "", 1024, 1024, 28, 1, 42, "qa")


def test_hidream_preserves_official_pixel_space_sampling_and_noise_scale():
    graph = build_workflow("hidream_o1", "teapot", "letters", 2048, 2048, 40, 5, 42, "qa")
    assert graph["1"]["inputs"]["ckpt_name"] == HIDREAM_MODEL
    assert graph["8"]["class_type"] == "EmptyHiDreamO1LatentImage"
    assert graph["4"]["inputs"]["noise_scale"] == 8
    assert graph["9"]["inputs"]["model"] == ["5", 0]
    assert graph["5"]["inputs"]["model"] == ["4", 0]
    assert graph["6"]["inputs"]["model"] == ["4", 0]


def test_job_normalization_keeps_fix_choice_and_rejects_missing_engine():
    tree = ast.parse(Path(__file__).with_name("main.py").read_text(encoding="utf-8-sig"))
    fields = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "_GEN_JOB_SPEC_FIELDS" for target in node.targets))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_normalize_generative_job_spec")
    scope = {"Dict": Dict, "Any": Any, "_GEN_JOB_SPEC_FIELDS": ast.literal_eval(fields),
             "_require_model_allowed": require_model_allowed,
             "_h3_scene_profiles": h3_scene_profiles,
             "_dlss5": SimpleNamespace(content_policy=SimpleNamespace(normalize=lambda value: value or "unknown")),
             "_resolve_image_engine": resolve, "_describe_image_engines": describe,
             "_model_files": inventory(missing=(FLUX_MODEL,)), "_IMAGE_SHARED_MODELS_DIR": None, "_IMAGE_EXTRA_MODEL_ROOTS": ()}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<studio-image-job>", "exec"), scope)
    normalize = scope[fn.name]
    spec = normalize({"mode": "image", "engine_id": "qwen21_fix", "model": QWEN_MODEL, "content_kind": "animation"})
    assert spec["engine_id"] == "qwen21_fix"
    assert spec["content_kind"] == "animation"
    with pytest.raises(ValueError):
        normalize({"mode": "image", "engine_id": "flux3_klein"})
