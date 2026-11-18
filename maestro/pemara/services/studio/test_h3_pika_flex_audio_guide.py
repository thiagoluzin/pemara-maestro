"""Offline opt-in audio-guide contract: no server, model or inference calls."""
from copy import deepcopy
import hashlib
import json

import pytest

from h3_pika_flex import build, validate_controls, validate_graph


def candidate(**changes):
    args = dict(prompt="A quiet animated family scene.", negative="", width=1088,
                height=608, frames=362, steps=6, seed=20261116, prefix="qa/pika",
                native_audio=True, content_kind="animation")
    args.update(changes)
    return build(**args)


@pytest.mark.parametrize("native,extra,expected", [
    (False, {}, "540308b4a4eac06967a83b1ae84ec37c79bee6fca3adacf3b18b17395a889547"),
    (False, {"first": "first.png"}, "a815581c5f4e8842f2062a6965cd25db577571730bb054f482a8c740ebd8e1e7"),
    (False, {"first": "first.png", "last": "last.png"}, "7b4129a071a65ce95e6806d157a727d74c087411c2da92e559ad9d016171fe12"),
    (False, {"references": ["ana.png", "rafael.png"]}, "a19315dcd569575d05649c965017431f9ea8c10aafc93c20aa12bc363ecc0ba5"),
    (True, {}, "ce404f6d29a6eda7e9cc2dd5f181cfc341d319db757ba8d30c38419b4b291d51"),
    (True, {"first": "first.png"}, "c091d55dd8d13f7f1d50aaf96e91540c9106b4ec88ee5f7cdbc29e6ac1d10237"),
    (True, {"first": "first.png", "last": "last.png"}, "5ffda6098c2d2b42227e6dccf4a9d57a52e1f40863e12a63d3a60b64a3837101"),
    (True, {"references": ["ana.png", "rafael.png"]}, "d5d57589554fa556c0be2ffe71dd3ce607c00d29cb5102c74978012861bcf727"),
])
def test_default_graph_matches_exact_pre_extension_fingerprint(native, extra, expected):
    graph = candidate(native_audio=native, **extra)
    actual = hashlib.sha256(json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert actual == expected
    assert not any(n["class_type"] in {"LoadAudio", "MiniMaxH3AddGuide"} for n in graph.values())


@pytest.mark.parametrize("extra,mode", [({}, "T2VA"), ({"first": "first.png"}, "I2VA"),
    ({"first": "first.png", "last": "last.png"}, "FL2VA"),
    ({"references": ["ana.png", "rafael.png"]}, "REF2VA")])
def test_opt_in_guide_is_only_conditioning_on_existing_av_time_axis(extra, mode):
    graph = candidate(audio_guide="verified_scene_48k.wav", **extra)
    checked = validate_graph(graph)
    assert checked["mode"] == mode
    assert checked["audio_guide"]["frame_idx"] == 0
    assert checked["audio_guide"]["runtime_qualification"] == "pending_actual_av_pilot"
    assert graph["22"]["inputs"] == {"positive": ["8", 0], "latent": ["8", 1],
        "audio_vae": ["7", 0], "audio": ["21", 0], "frame_idx": 0}
    assert graph["9"]["inputs"]["conditioning"] == ["22", 0]
    assert graph["13"]["inputs"]["latent_image"] == ["8", 1]
    assert graph["16"]["inputs"]["audio"] == ["15", 0]
    assert graph["11"]["inputs"]["sigmas"] == "1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0.0"


@pytest.mark.parametrize("value", [None, False, 7, "../guide.wav", "x/guide.wav", "x\\guide.wav",
    "C:guide.wav", "guide.wav [input]", "guide.mp3", " guide.wav", "guide.wav\n"])
def test_guide_requires_staged_wav_basename(value):
    with pytest.raises(ValueError):
        candidate(audio_guide=value)


def test_guide_requires_explicit_native_audio():
    with pytest.raises(ValueError):
        candidate(audio_guide="guide.wav", native_audio=False)


@pytest.mark.parametrize("defect", [
    "guide_offset", "guide_negative_offset", "guide_bool_offset", "guide_image", "guide_video_vae",
    "guide_latent", "guide_positive", "guide_audio", "guide_audio_vae", "guider_bypass", "sampler_guide_latent",
    "audio_path", "audio_loader_extra", "missing_guide", "orphan_audio", "orphan_image", "extra_guide",
    "no_output_audio", "audio_decoder_vae", "audio_decoder_samples", "video_decoder_vae", "audio_vae_name",
    "clip_model", "dimensions", "bad_length", "noise_wire", "lora", "sage", "guard", "sampler", "sigmas", "spectrum",
    "unknown_conditioning_input", "orphan_connected_to_unknown_input",
])
def test_optional_guide_does_not_relax_connected_pika_contract(defect):
    graph = candidate(first="first.png", audio_guide="guide.wav")
    if defect == "guide_offset": graph["22"]["inputs"]["frame_idx"] = 1
    elif defect == "guide_negative_offset": graph["22"]["inputs"]["frame_idx"] = -1
    elif defect == "guide_bool_offset": graph["22"]["inputs"]["frame_idx"] = False
    elif defect == "guide_image": graph["22"]["inputs"]["image"] = ["18", 0]
    elif defect == "guide_video_vae": graph["22"]["inputs"]["vae"] = ["6", 0]
    elif defect == "guide_latent": graph["22"]["inputs"]["latent"] = ["8", 0]
    elif defect == "guide_positive": graph["22"]["inputs"]["positive"] = ["8", 1]
    elif defect == "guide_audio": graph["22"]["inputs"]["audio"] = ["18", 0]
    elif defect == "guide_audio_vae": graph["22"]["inputs"]["audio_vae"] = ["6", 0]
    elif defect == "guider_bypass": graph["9"]["inputs"]["conditioning"] = ["8", 0]
    elif defect == "sampler_guide_latent": graph["13"]["inputs"]["latent_image"] = ["22", 0]
    elif defect == "audio_path": graph["21"]["inputs"]["audio"] = "../guide.wav"
    elif defect == "audio_loader_extra": graph["21"]["inputs"]["voice_engine"] = "other"
    elif defect == "missing_guide": del graph["22"]
    elif defect == "orphan_audio": graph["99"] = deepcopy(graph["21"])
    elif defect == "orphan_image": graph["99"] = {"class_type": "LoadImage", "inputs": {"image": "unrelated.png"}}
    elif defect == "extra_guide": graph["99"] = deepcopy(graph["22"])
    elif defect == "no_output_audio": del graph["16"]["inputs"]["audio"]
    elif defect == "audio_decoder_vae": graph["15"]["inputs"]["vae"] = ["6", 0]
    elif defect == "audio_decoder_samples": graph["15"]["inputs"]["samples"] = ["8", 1]
    elif defect == "video_decoder_vae": graph["14"]["inputs"]["vae"] = ["7", 0]
    elif defect == "audio_vae_name": graph["7"]["inputs"]["vae_name"] = "other_audio_vae.safetensors"
    elif defect == "clip_model": graph["5"]["inputs"]["clip_name"] = "other_encoder.safetensors"
    elif defect == "dimensions": graph["8"]["inputs"]["height"] = 607
    elif defect == "bad_length": graph["8"]["inputs"]["length"] = 363
    elif defect == "noise_wire": graph["13"]["inputs"]["noise"] = ["21", 0]
    elif defect == "lora": graph["2"]["inputs"]["lora_name"] = "other_lora.safetensors"
    elif defect == "sage": graph["4"]["inputs"]["model"] = ["2", 0]
    elif defect == "guard": graph["4"]["inputs"]["head_chunks"] = 2
    elif defect == "sampler": graph["10"]["inputs"]["sampler_name"] = "euler"
    elif defect == "sigmas": graph["11"]["inputs"]["sigmas"] = "1,0.5,0"
    elif defect == "spectrum": graph["99"] = {"class_type": "SpectrumApplyMiniMaxH3", "inputs": {}}
    elif defect == "unknown_conditioning_input": graph["8"]["inputs"]["voice_engine"] = "other"
    elif defect == "orphan_connected_to_unknown_input":
        graph["99"] = {"class_type": "LoadImage", "inputs": {"image": "unrelated.png"}}
        graph["8"]["inputs"]["unknown_guide"] = ["99", 0]
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_reference_mode_still_cannot_mix_first_frame_or_foreign_conditioner():
    with pytest.raises(ValueError):
        candidate(first="first.png", references=["ana.png"], audio_guide="guide.wav")
    graph = candidate(references=["ana.png"], audio_guide="guide.wav")
    graph["8"]["inputs"]["first_frame"] = ["30", 0]
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_raw_audio_and_image_guide_controls_remain_unqualified():
    for forbidden in ({"audio_conditioning_bytes": b"wave"}, {"minimax_h3_guide_image_bytes": b"png"}):
        with pytest.raises(ValueError):
            validate_controls({"engine_id": "minimax_h3", **forbidden})
