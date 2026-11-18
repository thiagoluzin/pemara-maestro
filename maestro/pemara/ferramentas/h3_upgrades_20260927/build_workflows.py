"""Build separate local H3 upgrade graphs; never submit jobs."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def node(kind, **inputs):
    return {"class_type": kind, "inputs": inputs}


def common(trunk, prompt):
    return {
        "1": node("UNETLoader", unet_name=f"minimax_h3_{trunk}_pruned_int8_convrot.safetensors", weight_dtype="default"),
        "2": node("CLIPLoader", clip_name="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", type="minimax", device="default"),
        "3": node("VAELoader", vae_name="minimax_h3_video_vae_int8_convrot.safetensors"),
        "4": node("MiniMaxH3MemoryEfficientSageAttentionPatch", model=["1", 0]),
        "5": node("MiniMaxH3SigmaShift", model=["4", 0], shift_video=12.0, shift_audio=3.0),
        "6": node("MiniMaxH3PDDAccApply", model=["5", 0], pdd_file=f"MiniMax-H3-{'FL2VA' if trunk == 'fl2va' else 'Ref2VA'}-Acc-8Step.safetensors",
                  nfe="8", lora_strength=1.0, head_strength=1.0, on_off_grid="error", partition_check="error"),
        "7": node("MiniMaxH3ImageToVideo", clip=["2", 0], vae=["3", 0], prompt=prompt, width=1088, height=608, length=124),
        "8": node("BasicGuider", model=["6", 0], conditioning=["7", 0]),
        "9": node("KSamplerSelect", sampler_name="euler"),
        "10": node("RandomNoise", noise_seed=27092026),
        "11": node("SamplerCustomAdvanced", noise=["10", 0], guider=["8", 0], sampler=["9", 0], sigmas=["6", 1], latent_image=["7", 1]),
        "12": node("VAEDecode", samples=["11", 0], vae=["3", 0]),
        "13": node("CreateVideo", images=["12", 0], fps=24.0, bit_depth=8),
        "14": node("SaveVideo", video=["13", 0], filename_prefix=f"PEMARA_H3_UPGRADES_20260927/{trunk}", format="mp4", **{"format.codec": "h264"}),
        "15": node("LoadImage", image="h3_upgrade_robot_hand.png"),
        "16": node("PreviewAny", source=["6", 2], label="PDD pairing and head bank"),
    }


prompt = "summary: A silver robotic hand slowly curls its fingers on a wooden table.\ndetailed_description: Single continuous close shot, the silver robot hand shown in the input, subtle smooth finger movement, fixed camera, stable metal materials and lighting.\noverall_soundscape: Quiet room.\nnon_diegetic_music: None."
fl = common("fl2va", prompt)
fl["7"]["inputs"]["first_frame"] = ["15", 0]
ref = common("ref2va", prompt.replace("the input", "<Picture 1>"))
ref["7"] = node("MiniMaxH3ReferenceToVideo", clip=["2", 0], vae=["3", 0], prompt=prompt.replace("the input", "<Picture 1>"),
                width=1088, height=608, length=124, ref_image_size="match", **{"ref_images.ref_image_0": ["15", 0]})
base = copy.deepcopy(fl)
base.pop("6")
base.pop("16")
base["8"]["inputs"]["model"] = ["5", 0]
base["9"]["inputs"]["sampler_name"] = "res_multistep"
base["17"] = node("BasicScheduler", model=["5", 0], scheduler="simple", steps=10, denoise=1.0)
base["11"]["inputs"]["sigmas"] = ["17", 0]
base["14"]["inputs"]["filename_prefix"] = "PEMARA_H3_UPGRADES_20260927/base10"
cn = copy.deepcopy(base)
cn.pop("15")
cn["7"]["inputs"].pop("first_frame")
cn["7"]["inputs"]["prompt"] = "summary: A dancer moving in an open field.\ndetailed_description: Single continuous wide shot, a person dancing outdoors, follow the pose control video's body motion, stable anatomy, natural daylight, fixed camera.\noverall_soundscape: Quiet outdoors.\nnon_diegetic_music: None."
cn["18"] = node("ModelPatchLoader", name="minimax_h3_fun_controlnet_union_2.0_pruned_int8_convrot.safetensors")
cn["19"] = node("LoadVideo", file="h3_upgrade_dancer_pose.mp4")
cn["20"] = node("GetVideoComponents", video=["19", 0])
cn["21"] = node("MiniMaxH3FunControlNetApply", model=["5", 0], model_patch=["18", 0], vae=["3", 0], strength=1.0,
                start_percent=0.0, end_percent=1.0, control_video=["20", 0])
cn["8"]["inputs"]["model"] = ["21", 0]
cn["17"]["inputs"].update(model=["21", 0], steps=40)
cn["9"]["inputs"]["sampler_name"] = "euler"
cn["14"]["inputs"]["filename_prefix"] = "PEMARA_H3_UPGRADES_20260927/controlnet2_pose"

for name, graph in (("01_H3_BASE_INT8_VAE", base), ("02_H3_PDD_FL2VA_8STEP", fl),
                    ("03_H3_PDD_REF2VA_8STEP", ref), ("04_H3_CONTROLNET2_POSE", cn)):
    (ROOT / "workflows" / (name + ".api.json")).write_text(json.dumps(graph, indent=2), encoding="utf-8")
    if graph is not cn:
        smoke = copy.deepcopy(graph)
        smoke["7"]["inputs"]["length"] = 73
        smoke["14"]["inputs"]["filename_prefix"] += "_smoke"
        (ROOT / "workflows" / (name + "_smoke.api.json")).write_text(json.dumps(smoke, indent=2), encoding="utf-8")
