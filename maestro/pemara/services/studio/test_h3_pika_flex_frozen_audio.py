"""Offline graph/coverage contract; never load a VAE, GPU or service."""
from copy import deepcopy
import hashlib
import json
import struct
import wave

import pytest

from h3_pika_flex import build, validate_graph, verify_frozen_audio_guide


def candidate(**changes):
    args = dict(prompt="The father speaks, then listens in silence.", negative="",
                width=1088, height=608, frames=362, steps=6, seed=20261116,
                prefix="qa/frozen_audio", first="approved.png", native_audio=True,
                content_kind="animation", audio_guide="definitive_mix.wav")
    args.update(changes)
    return build(**args)


def test_explicit_false_is_byte_identical_to_existing_soft_guide():
    a, b = candidate(), candidate(freeze_audio_target=False)
    assert json.dumps(a, separators=(",", ":")) == json.dumps(b, separators=(",", ":"))
    assert hashlib.sha256(json.dumps(a, separators=(",", ":")).encode()).hexdigest() == \
        "f61633665e7cf24e39cee9d11348a297891ecf56583f38afa6984e79705d5b47"
    assert validate_graph(a)["audio_target_frozen"] is False


@pytest.mark.parametrize("changes", [{"native_audio": False}, {"native_audio": 1},
    {"audio_guide": ""}, {"freeze_audio_target": "true"}, {"freeze_audio_target": 1}])
def test_freeze_requires_explicit_native_audio_guide_and_boolean(changes):
    kwargs = {"freeze_audio_target": True, **changes}
    with pytest.raises(ValueError):
        candidate(**kwargs)


def test_expected_freeze_contract_blocks_complete_branch_removal():
    graph = candidate(freeze_audio_target=True)
    checked = validate_graph(graph, freeze_audio_target=True)
    assert checked["audio_target_binding"]["graph_sha256"] == hashlib.sha256(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for key in ("23", "24", "25", "26"):
        del graph[key]
    graph["13"]["inputs"]["latent_image"] = ["8", 1]
    with pytest.raises(ValueError):
        validate_graph(graph, freeze_audio_target=True)


@pytest.mark.parametrize("extra", [{}, {"first": "", "references": ["ana.png", "rafael.png"]},
                                     {"last": "last.png"}, {"first": ""}])
def test_frozen_target_changes_only_four_official_nodes_and_sampler_latent(extra):
    before = candidate(**extra)
    after = candidate(freeze_audio_target=True, **extra)
    expected = deepcopy(before)
    expected["13"]["inputs"]["latent_image"] = ["26", 0]
    for key in ("23", "24", "25", "26"):
        expected[key] = after[key]
    assert after == expected
    assert {after[k]["class_type"] for k in ("23", "24", "25", "26")} == {
        "VAEEncodeAudio", "SolidMask", "SetLatentNoiseMask", "LTXVConcatAVLatent"}
    checked = validate_graph(after)
    assert checked["audio_target_frozen"] is True
    assert checked["audio_target_binding"]["sampler_latent"] == ["26", 0]
    assert checked["audio_target_binding"]["video_latent"] == ["8", 1]
    assert checked["audio_target_binding"]["guide_file"] == "definitive_mix.wav"
    assert checked["audio_target_binding"]["runtime_qualification"] == "pending_frozen_target_av_pilot"
    assert after["1"] == before["1"] and after["2"] == before["2"]
    assert after["4"]["inputs"]["head_chunks"] == 4
    assert after["10"]["inputs"]["sampler_name"] == "lcm"
    assert len(after["11"]["inputs"]["sigmas"].split(",")) == 7
    assert not any("Spectrum" in n["class_type"] for n in after.values())


@pytest.mark.parametrize("changes", [{"audio_guide": ""}, {"native_audio": False},
                                     {"freeze_audio_target": 1}, {"freeze_audio_target": "true"}])
def test_freeze_requires_explicit_bool_native_audio_and_guide(changes):
    with pytest.raises(ValueError):
        candidate(**(dict(freeze_audio_target=True) | changes))


@pytest.mark.parametrize("node,key,value", [
    ("23", "audio", ["18", 0]), ("23", "vae", ["6", 0]),
    ("24", "value", 0.01), ("24", "value", False),
    ("24", "width", 2), ("24", "height", True),
    ("25", "samples", ["8", 1]), ("25", "mask", ["23", 0]),
    ("26", "video_latent", ["8", 0]), ("26", "audio_latent", ["23", 0]),
    ("13", "latent_image", ["8", 1]), ("13", "latent_image", ["26", 1]),
    ("22", "audio", ["23", 0]), ("9", "conditioning", ["8", 0]),
    ("15", "samples", ["8", 1]), ("15", "vae", ["6", 0]),
    ("1", "unet_name", "ltx.safetensors"), ("4", "head_chunks", 2),
    ("10", "sampler_name", "euler"), ("11", "sigmas", "1,0"),
])
def test_frozen_route_tampering_is_blocked(node, key, value):
    graph = candidate(freeze_audio_target=True)
    graph[node]["inputs"][key] = value
    with pytest.raises(ValueError):
        validate_graph(graph)


@pytest.mark.parametrize("key", ["22", "23", "24", "25", "26", "15"])
def test_missing_frozen_or_audio_branch_node_is_blocked(key):
    graph = candidate(freeze_audio_target=True)
    del graph[key]
    with pytest.raises(ValueError):
        validate_graph(graph)


@pytest.mark.parametrize("defect", ["extra_input", "extra_mask", "foreign_node", "missing_output_audio"])
def test_freeze_cannot_admit_orphan_nodes_or_foreign_controls(defect):
    graph = candidate(freeze_audio_target=True)
    if defect == "extra_input": graph["26"]["inputs"]["engine"] = "ltx"
    elif defect == "extra_mask": graph["99"] = deepcopy(graph["24"])
    elif defect == "foreign_node": graph["99"] = {"class_type": "LTXVAudioVAELoader", "inputs": {}}
    else: del graph["16"]["inputs"]["audio"]
    with pytest.raises(ValueError):
        validate_graph(graph)


def write_wav(path, count=724000, rate=48000, channels=2):
    with wave.open(str(path), "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(b"\0" * (count * channels * 2))


def test_full_native_guide_encodes_604_and_concat_crops_to_603_without_padding(tmp_path):
    source = tmp_path / "guide.wav"
    write_wav(source)
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    proof = verify_frozen_audio_guide(source, frames=362, expected_sha256=sha)
    assert proof["samples"] == 724000
    assert proof["resampled_samples_32000"] == 482667
    assert proof["encoded_audio_latent_length"] == 604
    assert proof["target_audio_latent_length"] == 603
    assert proof["concat_crop_latent_frames"] == 1
    assert proof["concat_padded_latent_frames"] == 0


@pytest.mark.parametrize("count,rate,channels", [(723999, 48000, 2), (480000, 48000, 2),
                                                (724000, 48000, 1)])
def test_short_or_nonstereo_guide_is_rejected(tmp_path, count, rate, channels):
    source = tmp_path / "guide.wav"
    write_wav(source, count, rate, channels)
    with pytest.raises(ValueError):
        verify_frozen_audio_guide(source, frames=362)


def test_wrong_file_sha_is_rejected(tmp_path):
    source = tmp_path / "guide.wav"
    write_wav(source)
    with pytest.raises(ValueError, match="SHA256"):
        verify_frozen_audio_guide(source, frames=362, expected_sha256="0" * 64)


def test_truncated_pcm_wav_is_rejected(tmp_path):
    source = tmp_path / "guide.wav"
    write_wav(source)
    source.write_bytes(source.read_bytes()[:-4])
    with pytest.raises(ValueError, match="truncado"):
        verify_frozen_audio_guide(source, frames=362)


@pytest.mark.parametrize("pcm_subformat", [True, False])
def test_wave_extensible_pcm_header_matches_definitive_guides(tmp_path, pcm_subformat):
    path = tmp_path / "extensible.wav"
    write_wav(path)
    data = path.read_bytes()
    fmt = (struct.pack("<HHIIHHHHI", 65534, 2, 48000, 192000, 4, 16, 22, 16, 3)
           + bytes.fromhex("0100000000001000800000aa00389b71"))
    if not pcm_subformat:
        fmt = fmt[:-16] + bytes.fromhex("0300000000001000800000aa00389b71")
    rest = b"fmt " + struct.pack("<I", len(fmt)) + fmt + data[36:]
    path.write_bytes(b"RIFF" + struct.pack("<I", len(rest) + 4) + b"WAVE" + rest)
    if pcm_subformat:
        assert verify_frozen_audio_guide(path, frames=362)["encoded_audio_latent_length"] == 604
    else:
        with pytest.raises(ValueError):
            verify_frozen_audio_guide(path, frames=362)
