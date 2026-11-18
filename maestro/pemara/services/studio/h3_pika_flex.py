"""Pika Flex experiment authorized by the owner on 2026-11-01.

LCM six-step sampling, Sage + four-group guard, no Spectrum. Admission is
explicit at the Maestro queue boundary; the normal H3 gate stays unchanged.
An optional staged-WAV guide uses the installed official AddGuide node.
An independently explicit frozen-target pilot can also preserve that guide in
the target audio latent. Graph admission is not audiovisual qualification.
"""
import hashlib
import json
import math
import struct
from pathlib import Path

VARIANT = "pika_flex_v1"
STEPS = 6
SIGMAS = "1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0.0"
LORAS = {kind: f"pika_h3_flex_{kind}_v1_bf16.safetensors" for kind in ("fl2va", "ref2va")}
EXPECTED_BYTES = 1956172304
REQUIRED_NODES = ("LoraLoaderModelOnly", "MiniMaxH3MemoryEfficientSageAttentionPatch",
                  "PemaraH3SageLongSequencePatch", "MiniMaxH3ImageToVideo",
                  "MiniMaxH3ReferenceToVideo", "BasicGuider", "ManualSigmas",
                  "KSamplerSelect", "SamplerCustomAdvanced", "CreateVideo", "SaveVideo")
FROZEN_AUDIO_NODES = frozenset(("VAEEncodeAudio", "SolidMask", "SetLatentNoiseMask",
                                "LTXVConcatAVLatent"))


def _pcm_wav_coverage(data):
    """Read PCM/PCM-extensible RIFF headers without decoding or conversion."""
    invalid = "Frozen audio exige WAV PCM estéreo legível, completo e sem conversão silenciosa."
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError(invalid)
    end = struct.unpack_from("<I", data, 4)[0] + 8
    if end > len(data):
        raise ValueError("Frozen audio guide WAV truncado.")
    offset, fmt, payload_size = 12, None, None
    while offset + 8 <= end:
        tag, size = data[offset:offset + 4], struct.unpack_from("<I", data, offset + 4)[0]
        offset += 8
        if offset + size > end:
            raise ValueError("Frozen audio guide WAV truncado.")
        if tag == b"fmt ":
            if fmt is not None:
                raise ValueError(invalid)
            fmt = data[offset:offset + size]
        elif tag == b"data":
            if payload_size is not None:
                raise ValueError(invalid)
            payload_size = size
        offset += size + (size & 1)
    if fmt is None or len(fmt) < 16 or payload_size is None:
        raise ValueError(invalid)
    kind, channels, rate, byte_rate, align, bits = struct.unpack_from("<HHIIHH", fmt)
    if kind == 0xFFFE:
        if (len(fmt) < 40 or struct.unpack_from("<H", fmt, 16)[0] < 22
                or fmt[24:40] != bytes.fromhex("0100000000001000800000aa00389b71")):
            raise ValueError(invalid)
    elif kind != 1:
        raise ValueError(invalid)
    if (channels != 2 or rate <= 0 or bits not in (8, 16, 24, 32)
            or align != channels * (bits // 8) or byte_rate != rate * align
            or not payload_size or payload_size % align):
        raise ValueError(invalid)
    return rate, payload_size // align, channels


def verify_frozen_audio_guide(path, *, frames, expected_sha256=None):
    """CPU-only WAV coverage proof; verify the exact staged bytes before queueing.

    A graph basename cannot prove file coverage. The installed H3 VAE pads to
    800 samples at 32 kHz. A short encoded guide would make ConcatAV generate
    an unmasked tail, so require full waveform coverage and no latent padding.
    No VAE, model, audio mix or inference is run here.
    """
    if type(frames) is not int or not 124 <= frames <= 362 or (frames - 5) % 17:
        raise ValueError("Frozen audio exige a grade nativa Pika 17k+5, 124..362 quadros.")
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Frozen audio guide SHA256 difere da fonte definitiva.")
    rate, count, channels = _pcm_wav_coverage(data)
    if count * 24 < frames * rate:
        raise ValueError("Frozen audio guide não cobre toda a duração nativa.")
    # comfy.audio.resample uses ceil(float32(new_rate * length / source_rate)).
    resampled = count if rate == 32000 else math.ceil(struct.unpack("f", struct.pack("f", 32000 * count / rate))[0])
    encoded = (resampled + 799) // 800
    target = round(frames / 24 * 40)
    if encoded < target:
        raise ValueError("Frozen audio guide criaria uma cauda latente não congelada.")
    return {"protocol": "pika-frozen-audio-coverage-v1", "path": str(path), "sha256": digest,
            "sample_rate": rate, "samples": count, "channels": channels, "frames": frames,
            "native_fps": 24, "resampled_samples_32000": resampled,
            "encoded_audio_latent_length": encoded, "target_audio_latent_length": target,
            "concat_crop_latent_frames": encoded - target, "concat_padded_latent_frames": 0,
            "full_waveform_coverage": True, "basis": "installed H3 VAE pad-to-800 formula; no VAE execution"}


def _audio_guide_name(value):
    """The opt-in pilot accepts one staged WAV basename, never a runtime path."""
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(char in value for char in ("/", "\\", ":", "\x00", "\n", "\r", "[", "]"))
            or Path(value).name != value or Path(value).suffix.lower() != ".wav"):
        raise ValueError("Pika Flex audio guide exige um nome WAV local previamente carregado, sem caminho.")
    return value


def validate_controls(request):
    if request.get("engine_id", "minimax_h3") != "minimax_h3":
        raise ValueError("Pika Flex pertence ao motor MiniMax H3.")
    unsupported = ("creative_all_in_one", "creative_motion_request", "creative_timeline_request",
        "creative_fun_control_request", "minimax_reference_video_bytes", "reference_video_name",
        "audio_conditioning_bytes", "reference_audio_names", "minimax_h3_guide_image_bytes",
        "guide_image_name", "allow_minimax_h3_owner_long_window", "allow_owner_long_window",
        "enable_minimax_h3_live_preview", "enable_live_preview", "lora")
    if any(request.get(key) for key in unsupported) or any(request.get(key) is not None for key in
            ("minimax_h3_last_frame_index", "minimax_h3_guide_frame_index", "last_frame_index", "guide_frame_index")):
        raise ValueError("Pika Flex experimental aceita texto, primeiro/último quadro e referências de imagem; remova guias, áudio/vídeo de referência, LoRAs extras e controles criativos.")


def inventory(workspace, *, models=(), loras=(), nodes=(), online=False):
    roots = (Path(workspace) / "ferramentas/ComfyUI/models/loras",
             Path("D:/PemaraModels/comfy-shared/loras"))
    missing = [name for name in LORAS.values() if name not in loras or not any(
        (root / name).is_file() and (root / name).stat().st_size == EXPECTED_BYTES for root in roots)]
    missing += [kind for kind in REQUIRED_NODES if kind not in nodes]
    missing += [f"minimax_h3_{kind}_pruned_int8_convrot.safetensors" for kind in LORAS
                if f"minimax_h3_{kind}_pruned_int8_convrot.safetensors" not in models]
    return {"ready": bool(online and not missing), "missing": missing, "experimental": True,
            "steps": STEPS, "sage_required": True, "spectrum_enabled": False,
            "message": "Pika Flex disponível, experimental." if online and not missing else "Pika Flex requer os componentes listados."}


def build(prompt, negative, width, height, frames, steps, seed, prefix, *, first="", last="",
          references=(), native_audio=False, fps=24, content_kind="unknown", audio_guide="",
          freeze_audio_target=False):
    if type(freeze_audio_target) is not bool:
        raise ValueError("Pika Flex freeze_audio_target exige bool explícito.")
    if freeze_audio_target and (native_audio is not True or not audio_guide):
        raise ValueError("Pika Flex frozen audio exige guia WAV completo e áudio nativo explícito.")
    if not isinstance(audio_guide, str):
        raise ValueError("Pika Flex audio guide exige nome WAV ou string vazia para manter o modo anterior.")
    if steps != STEPS or float(fps) != 24 or not 124 <= int(frames) <= 362 or (int(frames) - 5) % 17:
        raise ValueError("Pika Flex exige seis passos, 24 FPS e grade H3 17k+5 entre 124 e 362 quadros.")
    if any(int(v) != v or int(v) < 256 or int(v) > 4096 or int(v) % 32 for v in (width, height)):
        raise ValueError("Pika Flex exige dimensões múltiplas de 32, entre 256 e 4096.")
    if references and (first or last) or len(references) > 9:
        raise ValueError("Pika Flex: use primeiro/último quadro ou até nove referências de imagem, separadamente.")
    if audio_guide:
        audio_guide = _audio_guide_name(audio_guide)
        if native_audio is not True:
            raise ValueError("Pika Flex audio guide exige saída de áudio nativo habilitada explicitamente.")
    kind = "ref2va" if references else "fl2va"
    def node(cls, **inputs):
        return {"class_type": cls, "inputs": inputs}
    graph = {
        "1": node("UNETLoader", unet_name=f"minimax_h3_{kind}_pruned_int8_convrot.safetensors", weight_dtype="default"),
        "2": node("LoraLoaderModelOnly", model=["1", 0], lora_name=LORAS[kind], strength_model=1.0),
        "3": node("MiniMaxH3MemoryEfficientSageAttentionPatch", model=["2", 0]),
        "4": node("PemaraH3SageLongSequencePatch", model=["3", 0], head_chunks=4),
        "5": node("CLIPLoader", clip_name="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", type="minimax", device="default"),
        "6": node("VAELoader", vae_name="minimax_h3_video_vae_int8_convrot.safetensors"),
        "7": node("VAELoader", vae_name="minimax_h3_audio_vae_fp32.safetensors"),
        "9": node("BasicGuider", model=["4", 0], conditioning=["8", 0]),
        "10": node("KSamplerSelect", sampler_name="lcm"),
        "11": node("ManualSigmas", sigmas=SIGMAS),
        "12": node("RandomNoise", noise_seed=int(seed)),
        "13": node("SamplerCustomAdvanced", noise=["12", 0], guider=["9", 0], sampler=["10", 0], sigmas=["11", 0], latent_image=["8", 1]),
        "14": node("VAEDecode", samples=["13", 0], vae=["6", 0]),
        "16": node("CreateVideo", images=["14", 0], fps=24.0, bit_depth=8, color_space="sRGB", codec="none"),
        "17": node("SaveVideo", video=["16", 0], filename_prefix=prefix, format="mp4", **{"format.codec": "auto"}),
        "20": node("PemaraDLSS5ContentPolicy", content_kind=content_kind, stage="native_preview"),
    }
    prompt = prompt if not negative else f"{prompt}\n\nExclude these visual elements: {negative}"
    conditioning = dict(clip=["5", 0], vae=["6", 0], prompt=prompt, width=int(width), height=int(height), length=int(frames))
    if references:
        conditioning.update(audio_vae=["7", 0], ref_image_size="match")
        for index, name in enumerate(references):
            key = str(30 + index)
            graph[key] = node("LoadImage", image=name)
            conditioning[f"ref_images.ref_image_{index}"] = [key, 0]
        graph["8"] = node("MiniMaxH3ReferenceToVideo", **conditioning)
    else:
        for field, name, key in (("first_frame", first, "18"), ("last_frame", last, "19")):
            if name:
                graph[key] = node("LoadImage", image=name)
                conditioning[field] = [key, 0]
        graph["8"] = node("MiniMaxH3ImageToVideo", **conditioning)
    if native_audio:
        graph["15"] = node("VAEDecodeAudio", samples=["13", 0], vae=["7", 0])
        graph["16"]["inputs"]["audio"] = ["15", 0]
    if audio_guide:
        # Official node: anchor the verified soundtrack on the same AV time axis.
        # It changes conditioning only; the sampler keeps the original AV latent.
        graph["21"] = node("LoadAudio", audio=audio_guide)
        graph["22"] = node("MiniMaxH3AddGuide", positive=["8", 0], latent=["8", 1],
                           audio_vae=["7", 0], audio=["21", 0], frame_idx=0)
        graph["9"]["inputs"]["conditioning"] = ["22", 0]
    if freeze_audio_target:
        # Generic official AV packing, not the LTX engine. Preserve node 8's
        # video stream and first-frame conditioning; only pin target audio.
        # The exact staged WAV must separately pass verify_frozen_audio_guide.
        graph["23"] = node("VAEEncodeAudio", audio=["21", 0], vae=["7", 0])
        graph["24"] = node("SolidMask", value=0.0, width=1, height=1)
        graph["25"] = node("SetLatentNoiseMask", samples=["23", 0], mask=["24", 0])
        graph["26"] = node("LTXVConcatAVLatent", video_latent=["8", 1], audio_latent=["25", 0])
        graph["13"]["inputs"]["latent_image"] = ["26", 0]
    validate_graph(graph, freeze_audio_target=freeze_audio_target)
    return graph


def validate_graph(graph, *, freeze_audio_target=None):
    """Admit only the connected official Pika path, never a general LCM bypass."""
    def require(ok):
        if not ok:
            raise ValueError("H3_PIKA_GRAPH_INVALID: Pika Flex exige LoRA oficial, Sage + proteção, seis sigmas LCM e áudio nativo sem Spectrum.")
    types = {key: node.get("class_type") for key, node in graph.items()}
    allowed = {"UNETLoader", "LoraLoaderModelOnly", "MiniMaxH3MemoryEfficientSageAttentionPatch",
        "PemaraH3SageLongSequencePatch", "CLIPLoader", "VAELoader", "MiniMaxH3ImageToVideo",
        "MiniMaxH3ReferenceToVideo", "BasicGuider", "KSamplerSelect", "ManualSigmas", "RandomNoise",
        "SamplerCustomAdvanced", "VAEDecode", "VAEDecodeAudio", "CreateVideo", "SaveVideo",
        "PemaraDLSS5ContentPolicy", "LoadImage", "LoadAudio", "MiniMaxH3AddGuide"} | FROZEN_AUDIO_NODES
    require(set(types.values()) <= allowed)
    def one(cls):
        keys = [key for key, kind in types.items() if kind == cls]
        require(len(keys) == 1)
        return keys[0], graph[keys[0]]["inputs"]
    load, loader = one("UNETLoader")
    require(not ({"MiniMaxH3ReferenceToVideo", "MiniMaxH3ImageToVideo"} <= set(types.values())))
    kind = "ref2va" if "MiniMaxH3ReferenceToVideo" in types.values() else "fl2va"
    require(loader["unet_name"] == f"minimax_h3_{kind}_pruned_int8_convrot.safetensors")
    from h3_scene_profiles import ADAPTERS, validate_adapters
    lora_nodes = [(key, graph[key]["inputs"]) for key, cls in types.items() if cls == "LoraLoaderModelOnly"]
    official = [(key, inputs) for key, inputs in lora_nodes if inputs.get("lora_name") == LORAS[kind]]
    require(len(official) == 1)
    lora, patch = official[0]
    require(patch == {"model": [load, 0], "lora_name": LORAS[kind], "strength_model": 1.0})
    extras = [(key, inputs) for key, inputs in lora_nodes if key != lora]
    receipts = [n.get("_meta", {}).get("sceneProfiles") for n in graph.values()
                if n.get("class_type") in {"MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo"}]
    roles = receipts[0].get("roles", []) if receipts and receipts[0] else []
    require(roles in ([], ["realism"], ["combat", "physics"], ["combat", "physics", "realism"]))
    require(len(extras) == len(roles))
    previous = [lora, 0]
    for role in roles:
        matching = [(key, inputs) for key, inputs in extras if inputs.get("lora_name") == ADAPTERS[role]["file"]]
        require(len(matching) == 1)
        key, inputs = matching[0]
        require(inputs == {"model": previous, "lora_name": ADAPTERS[role]["file"], "strength_model": ADAPTERS[role]["strength"]})
        previous = [key, 0]
    sage, patch = one("MiniMaxH3MemoryEfficientSageAttentionPatch")
    require(patch["model"] == previous)
    validate_adapters(graph, roles)
    guard, patch = one("PemaraH3SageLongSequencePatch")
    require(patch == {"model": [sage, 0], "head_chunks": 4})
    guide, guider = one("BasicGuider")
    require(guider["model"] == [guard, 0])
    select, sampler = one("KSamplerSelect")
    require(sampler["sampler_name"] == "lcm")
    sigmas, values = one("ManualSigmas")
    require([float(x) for x in values["sigmas"].split(",")] == [float(x) for x in SIGMAS.split(",")])
    condition, condition_inputs = one("MiniMaxH3ReferenceToVideo" if kind == "ref2va" else "MiniMaxH3ImageToVideo")
    require(not (kind == "ref2va" and any(key in condition_inputs for key in ("first_frame", "last_frame"))))
    require(not (kind == "fl2va" and any(key.startswith("ref_images.") for key in condition_inputs)))
    require(124 <= int(condition_inputs["length"]) <= 362 and (int(condition_inputs["length"]) - 5) % 17 == 0)
    audio_guide = None
    if "MiniMaxH3AddGuide" in types.values():
        anchor, anchor_inputs = one("MiniMaxH3AddGuide")
        audio_load, audio_load_inputs = one("LoadAudio")
        require(set(audio_load_inputs) == {"audio"})
        audio_guide = _audio_guide_name(audio_load_inputs["audio"])
        audio_vaes = [(key, graph[key]["inputs"]) for key, cls in types.items()
                      if cls == "VAELoader" and graph[key]["inputs"].get("vae_name") == "minimax_h3_audio_vae_fp32.safetensors"]
        video_vaes = [(key, graph[key]["inputs"]) for key, cls in types.items()
                      if cls == "VAELoader" and graph[key]["inputs"].get("vae_name") == "minimax_h3_video_vae_int8_convrot.safetensors"]
        require(len(audio_vaes) == len(video_vaes) == 1)
        audio_vae, _ = audio_vaes[0]
        video_vae, _ = video_vaes[0]
        require(anchor_inputs == {"positive": [condition, 0], "latent": [condition, 1],
                                  "audio_vae": [audio_vae, 0], "audio": [audio_load, 0], "frame_idx": 0})
        require(type(anchor_inputs["frame_idx"]) is int)
        require(guider["conditioning"] == [anchor, 0])
        require(condition_inputs.get("vae") == [video_vae, 0])
        require(len([cls for cls in types.values() if cls == "VAELoader"]) == 2)
        require(loader.get("weight_dtype") == "default")
        clip, clip_inputs = one("CLIPLoader")
        require(clip_inputs == {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
                                "type": "minimax", "device": "default"})
        require(condition_inputs.get("clip") == [clip, 0])
        common_inputs = {"clip", "vae", "prompt", "width", "height", "length"}
        if kind == "ref2va":
            references = sorted(key for key in condition_inputs if key.startswith("ref_images."))
            require(1 <= len(references) <= 9)
            require(set(references) == {f"ref_images.ref_image_{index}" for index in range(len(references))})
            require(set(condition_inputs) == common_inputs | {"audio_vae", "ref_image_size"} | set(references))
            require(condition_inputs["audio_vae"] == [audio_vae, 0] and condition_inputs["ref_image_size"] == "match")
        else:
            references = [key for key in ("first_frame", "last_frame") if key in condition_inputs]
            require(set(condition_inputs) == common_inputs | set(references))
        for key in references:
            reference = condition_inputs[key]
            require(isinstance(reference, list) and len(reference) == 2 and reference[1] == 0
                    and types.get(reference[0]) == "LoadImage")
        require(type(condition_inputs["length"]) is int)
        require(all(type(condition_inputs.get(axis)) is int and 256 <= condition_inputs[axis] <= 4096
                    and condition_inputs[axis] % 32 == 0 for axis in ("width", "height")))
    else:
        require("LoadAudio" not in types.values())
        require(guider["conditioning"] == [condition, 0])
    frozen = bool(set(types.values()) & FROZEN_AUDIO_NODES)
    require(freeze_audio_target is None or type(freeze_audio_target) is bool)
    if freeze_audio_target is not None:
        require(frozen is freeze_audio_target)
    target_latent = [condition, 1]
    frozen_binding = None
    if frozen:
        require(bool(audio_guide))
        encode, encode_inputs = one("VAEEncodeAudio")
        zero, zero_inputs = one("SolidMask")
        masked, mask_inputs = one("SetLatentNoiseMask")
        combined, combined_inputs = one("LTXVConcatAVLatent")
        require(encode_inputs == {"audio": [audio_load, 0], "vae": [audio_vae, 0]})
        require(zero_inputs == {"value": 0.0, "width": 1, "height": 1})
        require(type(zero_inputs["value"]) in (int, float)
                and type(zero_inputs["width"]) is type(zero_inputs["height"]) is int)
        require(mask_inputs == {"samples": [encode, 0], "mask": [zero, 0]})
        require(combined_inputs == {"video_latent": [condition, 1], "audio_latent": [masked, 0]})
        target_latent = [combined, 0]
        frozen_binding = {"guide_loader": audio_load, "audio_vae": audio_vae,
            "encoder": encode, "zero_mask": zero, "masked_audio": masked,
            "av_pack": combined, "video_latent": [condition, 1],
            "sampler_latent": target_latent, "guide_file": audio_guide,
            "waveform_coverage": "requires_exact_staged_WAV_verification",
            "runtime_qualification": "pending_frozen_target_av_pilot"}
    sample, inputs = one("SamplerCustomAdvanced")
    require(all(inputs[k] == [v, n] for k, v, n in (
        ("guider", guide, 0), ("sampler", select, 0), ("sigmas", sigmas, 0))))
    require(inputs.get("latent_image") == target_latent)
    if audio_guide:
        noise, _ = one("RandomNoise")
        require(inputs.get("noise") == [noise, 0])
    decoder, inputs = one("VAEDecode")
    require(inputs["samples"] == [sample, 0])
    if audio_guide:
        require(inputs.get("vae") == [video_vae, 0])
    video, inputs = one("CreateVideo")
    require(inputs["images"] == [decoder, 0] and float(inputs["fps"]) == 24)
    if "audio" in inputs:
        audio, audio_inputs = one("VAEDecodeAudio")
        require(inputs["audio"] == [audio, 0] and audio_inputs["samples"] == [sample, 0])
        if audio_guide:
            require(audio_inputs.get("vae") == [audio_vae, 0])
    elif audio_guide:
        require(False)
    _, inputs = one("SaveVideo")
    require(inputs["video"] == [video, 0])
    if audio_guide:
        # Guide admission is closed and connected: no orphan control/voice nodes.
        policy, policy_inputs = one("PemaraDLSS5ContentPolicy")
        require(policy_inputs.get("content_kind") in {"animation", "live_action", "mixed"})
        reachable, pending = set(), [one("SaveVideo")[0], policy]
        while pending:
            key = pending.pop()
            if key in reachable:
                continue
            require(key in graph)
            reachable.add(key)
            for value in graph[key]["inputs"].values():
                if (isinstance(value, list) and len(value) == 2 and isinstance(value[0], str)
                        and type(value[1]) is int and value[0] in graph):
                    pending.append(value[0])
        require(reachable == set(graph))
    result = {"ok": True, "variant": VARIANT, "steps": STEPS, "spectrum_enabled": False,
            "audio_target_frozen": frozen,
            "mode": "REF2VA" if kind == "ref2va" else "FL2VA" if "last_frame" in graph[condition]["inputs"] else "I2VA" if "first_frame" in graph[condition]["inputs"] else "T2VA"}
    if audio_guide:
        result["audio_guide"] = {"file": audio_guide, "node": "MiniMaxH3AddGuide", "frame_idx": 0,
                                 "native_audio_required": True, "runtime_qualification": "pending_actual_av_pilot"}
    if frozen:
        frozen_binding["graph_sha256"] = hashlib.sha256(
            json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        result["audio_target_binding"] = frozen_binding
    return result
