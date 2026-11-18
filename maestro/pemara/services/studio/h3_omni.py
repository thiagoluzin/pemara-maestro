"""Pinned FastH3 Omni Comfy release; no automatic migration or engine fallback."""
from pathlib import Path
import json

VARIANT = "fasth3_omni_8step_v1"
MODEL = "fasth3_omniref_8step_pruned_int8_convrot.safetensors"
STEPS = 8
EXPECTED_BYTES = 22_213_723_064
SHA256 = "851b2dc9670ed864b7f1e951ac9da047d83b1c04ded9bfcc1a9e5bba0ee33f80"
SOURCE = "https://huggingface.co/FastVideo/FastH3-Omni-Comfy"


def inventory(directories):
    """Require an installation hash receipt tied to the current file stat."""
    for root in directories:
        path = Path(root) / MODEL
        if not path.is_file():
            continue
        stat = path.stat()
        try:
            receipt = json.loads(path.with_suffix(path.suffix + ".pemara.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            receipt = {}
        verified = (stat.st_size == EXPECTED_BYTES and receipt.get("sha256") == SHA256
                    and receipt.get("size") == stat.st_size
                    and receipt.get("mtime_ns") == stat.st_mtime_ns)
        return {"fastH3OmniFileReady": verified, "fastH3OmniReady": False,
                "fastH3OmniModel": MODEL, "fastH3OmniBytes": stat.st_size,
                "fastH3OmniExpectedBytes": EXPECTED_BYTES, "fastH3OmniSource": SOURCE}
    return {"fastH3OmniFileReady": False, "fastH3OmniReady": False,
            "fastH3OmniModel": MODEL, "fastH3OmniBytes": 0,
            "fastH3OmniExpectedBytes": EXPECTED_BYTES, "fastH3OmniSource": SOURCE}


def use_reference_conditioning(graph, *, prompt, images=(), video="", audios=(), audio_vae):
    """Use native Ref2VA ports. An image reference is not an exact first frame."""
    if len(images) > 9 or len(audios) > 3:
        raise ValueError("H3_OMNI_REFERENCE_LIMIT: maximo nove imagens e tres audios.")
    graph["1"]["inputs"]["unet_name"] = MODEL
    graph["2"]["inputs"].update(shift_video=12.0, shift_audio=3.0)
    if "17" not in graph:
        graph["17"] = {"class_type": "VAELoader", "inputs": {"vae_name": audio_vae}}
    old = graph["6"]["inputs"]
    inputs = {"clip": ["3", 0], "vae": ["4", 0], "audio_vae": ["17", 0],
              "prompt": prompt.strip(), "width": old["width"], "height": old["height"],
              "length": old["length"], "ref_image_size": "max"}
    for i, name in enumerate(images, 1):
        key = f"omni_image_{i}"
        graph[key] = {"class_type": "LoadImage", "inputs": {"image": name}}
        inputs[f"ref_images.ref_image_{i}"] = [key, 0]
    if video:
        graph["omni_video"] = {"class_type": "VHS_LoadVideo", "inputs": {
            "video": video, "force_rate": 24, "custom_width": 0, "custom_height": 0,
            "frame_load_cap": old["length"], "skip_first_frames": 0, "select_every_nth": 1}}
        inputs["ref_videos.ref_video_1"] = ["omni_video", 0]
        inputs["ref_video_audios.ref_video_audio_1"] = ["omni_video", 2]
    for i, name in enumerate(audios, 1):
        key = f"omni_audio_{i}"
        graph[key] = {"class_type": "LoadAudio", "inputs": {"audio": name}}
        inputs[f"ref_audios.ref_audio_{i}"] = [key, 0]
    graph["6"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": inputs}
    return graph


def validate_graph(graph):
    nodes = list(graph.values())
    shifts = [n["inputs"] for n in nodes if n.get("class_type") == "MiniMaxH3SigmaShift"]
    if len(shifts) != 1 or shifts[0].get("shift_video") != 12.0 or shifts[0].get("shift_audio") != 3.0:
        raise ValueError("H3_OMNI_SHIFT_REQUIRED: Omni exige video 12 e audio 3.")
    conditions = [n for n in nodes if n.get("class_type") == "MiniMaxH3ReferenceToVideo"]
    if len(conditions) != 1 or not conditions[0]["inputs"].get("audio_vae"):
        raise ValueError("H3_OMNI_CONDITIONING_REQUIRED: Ref2VA e audio VAE obrigatorios.")
    if any(n.get("class_type") == "CFGGuider" for n in nodes):
        raise ValueError("H3_OMNI_GUIDANCE_REQUIRED: use BasicGuider, guidance 1.")
