from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import h3_scene_profiles as profiles
from h3_pika_flex import build, validate_graph
from h3_workflow import ensure_h3_sage_attention
from h3_acceleration import validate_spectrum


def source(pika=True, refs=()):
    graph = build("Two adults train a block and counterattack.", "", 1088, 608, 192, 6,
        20261106, "validation/combat", references=refs, native_audio=True, content_kind="live_action")
    if not pika:
        graph.pop("2")
        graph["3"]["inputs"]["model"] = ["1", 0]
        graph["10"]["inputs"]["sampler_name"] = "res_multistep"
        graph = ensure_h3_sage_attention(graph)
    return graph


@pytest.mark.parametrize("pika", [True, False])
@pytest.mark.parametrize("people,combat", [(False, False), (True, False), (False, True), (True, True)])
def test_native_paths_keep_engine_sampler_audio_and_acceleration(pika, people, combat):
    original = source(pika)
    graph, receipt = profiles.apply(original, people=people, combat=combat)
    assert original == source(pika)
    assert graph["1"] == original["1"]
    assert graph["10"] == original["10"]
    assert graph["11"] == original["11"]
    assert graph["13"] == original["13"]
    assert graph["15"] == original["15"] and graph["16"] == original["16"]
    assert profiles.validate_adapters(graph, receipt["roles"])
    if pika:
        assert validate_graph(graph)["steps"] == 6
    else:
        assert validate_spectrum(graph)
    again, same_receipt = profiles.apply(graph, people=people, combat=combat)
    assert again == graph and same_receipt == receipt


@pytest.mark.parametrize("defect", ["strength", "bypass", "unknown_lora", "trigger", "missing_physics"])
def test_pika_rejects_changed_profile_without_opening_general_lora_bypass(defect):
    graph, _ = profiles.apply(source(), people=True, combat=True)
    if defect == "strength": graph["pemara_scene_physics"]["inputs"]["strength_model"] = 1.0
    if defect == "bypass": graph["3"]["inputs"]["model"] = ["2", 0]
    if defect == "unknown_lora": graph["pemara_scene_physics"]["inputs"]["lora_name"] = "other.safetensors"
    if defect == "trigger": graph["8"]["inputs"]["prompt"] = "two adults fight"
    if defect == "missing_physics": graph.pop("pemara_scene_physics")
    with pytest.raises((ValueError, KeyError)):
        validate_graph(graph)


def test_animation_preserves_style_and_uses_combat_without_skin_lora(tmp_path):
    with patch.object(profiles, "verify_models"):
        graph, receipt = profiles.prepare(source(), workspace=tmp_path, input_root=tmp_path,
            content_kind="animation", profile=profiles.COMBAT, detector=lambda *_: pytest.fail("animation sends no external request"))
    assert receipt["roles"] == ["combat", "physics"]
    assert "r34l1sm" not in graph["8"]["inputs"]["prompt"]
    graph_without_policy = source()
    graph_without_policy.pop("20")
    with patch.object(profiles, "verify_models"):
        prepared, _ = profiles.prepare(graph_without_policy, workspace=tmp_path, input_root=tmp_path,
            content_kind="animation", profile=profiles.COMBAT)
    assert prepared["pemara_scene_content_policy"]["inputs"] == {"content_kind": "animation", "stage": "native_preview"}


def test_detector_result_is_cached_by_exact_scene_and_automatic_without_combat(tmp_path):
    calls = []
    def detector(state, assets):
        calls.append(state)
        return {"people": True, "probability": 0.99}
    with patch.object(profiles, "verify_models"):
        for _ in range(2):
            graph, receipt = profiles.prepare(source(), workspace=tmp_path, input_root=tmp_path,
                content_kind="live_action", detector=detector)
        changed = source()
        changed["8"]["inputs"]["prompt"] += " in the rain"
        profiles.prepare(changed, workspace=tmp_path, input_root=tmp_path,
            content_kind="live_action", detector=detector)
    assert len(calls) == 2 and receipt["roles"] == ["realism"]
    assert not any("Two adults" in f.read_text() for f in tmp_path.rglob("*.json"))


def test_no_people_leaves_native_visual_prompt_and_no_adapters(tmp_path):
    graph, receipt = profiles.prepare(source(), workspace=tmp_path, input_root=tmp_path,
        content_kind="mixed", detector=lambda *_: {"people": False, "probability": 0.0})
    assert receipt["roles"] == []
    assert graph["8"]["inputs"]["prompt"] == source()["8"]["inputs"]["prompt"]


@pytest.mark.parametrize("name", ["../outside.png", "missing.png"])
def test_reference_evidence_cannot_traverse_or_disappear(tmp_path, name):
    graph = source(refs=[name])
    with pytest.raises(ValueError, match="INPUT"):
        profiles.detection_state(graph, tmp_path)


def test_all_reference_images_are_examined_and_hashed(tmp_path):
    from PIL import Image
    for i in range(4):
        Image.new("RGB", (16, 16), (i * 40, 0, 0)).save(tmp_path / f"ref{i}.png")
    graph = source(refs=[f"ref{i}.png" for i in range(4)])
    state, assets, identity = profiles.detection_state(graph, tmp_path)
    assert len(assets) == len(state["references"]) == 4
    assert len(identity) == 64


def test_independent_profile_context_is_restored_even_on_error():
    @profiles.with_profile
    def scoped(**kwargs):
        assert profiles.PROFILE.get() == profiles.COMBAT
        raise RuntimeError("expected")
    with pytest.raises(RuntimeError): scoped(h3_scene_profile=profiles.COMBAT)
    assert profiles.PROFILE.get() == "auto" and profiles.receipts() == []


def test_motion_and_timeline_prompts_receive_directions_without_rewriting_choreography():
    for cls, field, value in [("MiniMaxH3MotionDirector", "global_prompt", ""),
        ("MiniMaxH3FiniteSegmentExpansion", "segment_prompts", json.dumps(["left blocks", "right retreats"]))]:
        graph = source(False)
        graph["8"] = {"class_type": cls, "inputs": {field: value, "model": deepcopy(graph["9"]["inputs"]["model"])}}
        result, receipt = profiles.apply(graph, people=True, combat=True)
        text = result["8"]["inputs"][field]
        assert "r34l1sm" in text
        assert profiles.validate_adapters(result, receipt["roles"])


def test_local_semantic_contract_never_fabricates_probabilities_or_skips_uncertainty():
    for presence, expected in [("yes", True), ("no", False), ("uncertain", None), (True, None), ("maybe", None)]:
        text = json.dumps({"presence": presence, "evidence": "Visible scene evidence."})
        if expected is None:
            with pytest.raises(ValueError): profiles.parse_local_detection(text)
        else:
            result = profiles.parse_local_detection(text)
            assert result["people"] is expected and result["externalDataTransfer"] is False
            assert "probability" not in result
    for invalid in ("not json", '{}', '{"presence":"no","evidence":""}', '{"presence":"no","evidence":"ok","extra":true}'):
        with pytest.raises(ValueError): profiles.parse_local_detection(invalid)


def test_local_detector_graph_uses_only_existing_local_nodes_and_bounded_reference_files(tmp_path):
    from PIL import Image
    import io
    import base64
    out = io.BytesIO()
    Image.new("RGB", (512, 512), "gray").save(out, format="PNG")
    assets = {"one": {"data_base64": base64.b64encode(out.getvalue()).decode()},
              "two": {"data_base64": base64.b64encode(out.getvalue()).decode()}}
    graph = profiles.local_detection_workflow({"scene_descriptions": ["two adults"], "references": ["one", "two"]}, assets, tmp_path)
    assert graph["1"]["inputs"]["clip_name"] == profiles.DETECTOR_MODEL
    assert graph["3"]["inputs"]["image"] == ["batch_1", 0]
    assert set(n["class_type"] for n in graph.values()) == {"CLIPLoader", "TextGenerate", "PreviewAny", "LoadImage", "ImageBatch"}
    assert len(list((tmp_path / "scene_detection").glob("*.jpg"))) == 1


@pytest.mark.parametrize("pika", [True, False])
def test_final_maestro_admission_applies_combat_and_realism_to_actual_sent_graph(pika, tmp_path):
    import main
    original_prepare = profiles.prepare
    sent = []
    def prepare(graph, **kwargs):
        kwargs.update(profile=profiles.COMBAT, detector=lambda *_: {"people": True, "probability": 0.99}, workspace=tmp_path)
        return original_prepare(graph, **kwargs)
    def request(path, *args, **kwargs):
        if path == "/prompt":
            sent.append(args[0]["prompt"])
            raise RuntimeError("captured before actual transport")
        if path.startswith("/object_info/"):
            return {path.split('/')[-1]: {}}
        if path == "/system_stats": return {"system": {"comfyui_version": "unit"}}
        raise AssertionError(path)
    with patch.object(profiles, "prepare", side_effect=prepare), patch.object(profiles, "verify_models"), patch.object(main, "_comfy_request", side_effect=request):
        with pytest.raises(RuntimeError, match="captured before"):
            main._queue_comfy_workflow(source(pika), timeout=1, h3_model_variant="pika_flex_v1" if pika else "base")
    assert len(sent) == 1
    assert profiles.validate_adapters(sent[0], ["combat", "physics", "realism"])
    if pika: assert validate_graph(sent[0])["steps"] == 6
    else: assert validate_spectrum(sent[0])


def test_real_admission_calls_local_analysis_then_patches_the_video_before_submission(tmp_path):
    import main
    sent = []
    def request(path, *args, **kwargs):
        if path.startswith('/object_info/'):
            return {path.split('/')[-1]: {}}
        if path == '/prompt':
            graph = args[0]['prompt']
            sent.append(graph)
            if any(n['class_type'] == 'TextGenerate' for n in graph.values()):
                return {'prompt_id': 'local-scene-analysis-test'}
            raise RuntimeError('video captured before actual transport')
        if path == '/history/local-scene-analysis-test':
            return {'local-scene-analysis-test': {'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'4': {'text': ['{"presence":"yes","evidence":"Two adults train boxing."}']}}}}
        if path == '/system_stats': return {'system': {'comfyui_version': 'unit'}}
        raise AssertionError(path)
    token = profiles.PROFILE.set(profiles.COMBAT)
    try:
        with patch.object(main, 'BASE_DIR', str(tmp_path)), patch.object(profiles, 'verify_models'), patch.object(main, '_comfy_request', side_effect=request):
            with pytest.raises(RuntimeError, match='video captured'):
                main._queue_comfy_workflow(source(), timeout=1, h3_model_variant='pika_flex_v1')
    finally:
        profiles.PROFILE.reset(token)
    assert len(sent) == 2
    assert sent[0]['1']['inputs']['clip_name'] == profiles.DETECTOR_MODEL
    assert validate_graph(sent[1])['steps'] == 6
    decision = sent[1]['8']['_meta']['sceneProfiles']['detection']
    assert decision['provider'] == 'local_comfy' and decision['externalDataTransfer'] is False
