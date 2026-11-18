"""Explicit local image engine selection. No cross-engine fallback."""
from pathlib import Path
from retired_models import RETIRED_IMAGE_ENGINE_IDS, require_model_allowed

from qwen21_workflow import MODEL as QWEN_MODEL, CLIP as QWEN_CLIP, VAE as QWEN_VAE
from qwen21_workflow import build_workflow as build_qwen

FIX_LORA = "qwen2.1-detail-fix-2.0.safetensors"
FLUX_MODEL = "flux3-image-klein-int8-convrot.safetensors"
FLUX_CLIP = "qwen3vl_4b_int8_convrot.safetensors"
FLUX_UPSAMPLER = "qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors"
FLUX_VAE = "flux2-vae.safetensors"
LLADA_BASE = "LLaDA-Image-Base-BF16-AIO.safetensors"
LLADA_TURBO = "LLaDA-Image-Turbo-BF16-AIO.safetensors"
HIDREAM_MODEL = "hidream_o1_image_bf16.safetensors"

ENGINES = (
    {"id": "qwen21", "display_name": "Qwen Image 2.1", "model": QWEN_MODEL,
     "modes": ["image", "edit"], "steps": 40, "guidance": 1.0,
     "description": "Geração e edição local de imagens.",
     "requirements": (("diffusion_models", QWEN_MODEL), ("text_encoders", QWEN_CLIP), ("vae", QWEN_VAE))},
    {"id": "qwen21_fix", "display_name": "Qwen Image 2.1 + Fix comunitário", "model": QWEN_MODEL,
     "modes": ["image"], "steps": 40, "guidance": 1.0,
     "description": "Experimental: Qwen com LoRA de detalhe, força 1.0. Compare com o original.",
     "requirements": (("diffusion_models", QWEN_MODEL), ("text_encoders", QWEN_CLIP),
                      ("vae", QWEN_VAE), ("loras", FIX_LORA))},
    {"id": "flux3_klein", "display_name": "FLUX 3 Image Klein", "model": FLUX_MODEL,
     "modes": ["image"], "steps": 16, "guidance": 1.0,
     "description": "Geração local com expansão de prompt local. Acesso aos pesos exige liberação no Hugging Face.",
     "requirements": (("diffusion_models", FLUX_MODEL), ("text_encoders", FLUX_CLIP),
                      ("text_encoders", FLUX_UPSAMPLER), ("vae", FLUX_VAE))},
    {"id": "llada_base", "display_name": "LLaDA-Image Base", "model": LLADA_BASE,
     "modes": ["image"], "steps": 50, "guidance": 5.0,
     "description": "Geração local de imagens com LLaDA Base. Modelo grande; o carregamento pode demorar.",
     "requirements": (("checkpoints", LLADA_BASE),)},
    {"id": "llada_turbo", "display_name": "LLaDA-Image Turbo", "model": LLADA_TURBO,
     "modes": ["image"], "steps": 4, "guidance": 1.0,
     "min_steps": 2, "max_steps": 4,
     "description": "Geração local com quatro passos de difusão. Modelo grande; o carregamento pode demorar.",
     "requirements": (("checkpoints", LLADA_TURBO),)},
    {"id": "hidream_o1", "display_name": "HiDream-O1 Image", "model": HIDREAM_MODEL,
     "modes": ["image"], "steps": 40, "guidance": 5.0, "width": 2048, "height": 2048,
     "description": "Geração local de imagens. Resolução recomendada: 2048 × 2048; resoluções menores podem perder qualidade.",
     "requirements": (("checkpoints", HIDREAM_MODEL),)},
)

# Keep the historical builders below for provenance; retired choices are not selectable.
ENGINES = tuple(engine for engine in ENGINES if engine["id"] not in RETIRED_IMAGE_ENGINE_IDS)


def describe(model_files, *, online, shared_root=None, additional_roots=()):
    inventory = {folder: set(model_files(folder)) for folder in {f for e in ENGINES for f, _ in e["requirements"]}}
    # The active Comfy runtime also loads this shared model tree. Maestro's legacy
    # inventory only scans its E: tree; do not duplicate multi-GB weights there.
    sizes = {FIX_LORA: 54800124, FLUX_MODEL: 5827874779,
             FLUX_CLIP: 4858559240, FLUX_UPSAMPLER: 6724090780,
             LLADA_BASE: 49259978134, LLADA_TURBO: 49259978182, HIDREAM_MODEL: 16365209824}
    for root in ([shared_root] if shared_root is not None else []) + list(additional_roots):
        for engine in ENGINES:
            for folder, name in engine["requirements"]:
                path = Path(root) / folder / name
                if path.is_file() and path.stat().st_size == sizes.get(name, path.stat().st_size):
                    inventory[folder].add(name)
    result = []
    for engine in ENGINES:
        missing = [f"{folder}/{name}" for folder, name in engine["requirements"] if name not in inventory[folder]]
        result.append({k: v for k, v in engine.items() if k != "requirements"} | {
            "installed": not missing, "ready": bool(online and not missing), "missing": missing,
            "message": "Faltam arquivos do modelo." if missing else "Pronto para gerar." if online else "ComfyUI offline.",
        })
    return result


def resolve(engine_id, model, mode, catalog):
    engine_id, model = str(engine_id or "").strip(), str(model or "").strip()
    require_model_allowed(model, engine_id)
    # Legacy internal anchor callers retain their Qwen model; explicit bad choices fail.
    if not engine_id:
        engine_id = "qwen21" if not model or model == QWEN_MODEL else next(
            (e["id"] for e in catalog if e["model"] == model), "")
    engine = next((e for e in catalog if e["id"] == engine_id), None)
    if engine is None or mode not in engine["modes"]:
        raise ValueError("Motor de imagem inválido para este modo. Escolha um motor disponível.")
    if model and model != engine["model"]:
        raise ValueError("O modelo não corresponde ao motor de imagem escolhido.")
    if not engine["ready"]:
        raise ValueError(f'{engine["display_name"]}: {engine["message"]} Nenhum outro motor foi selecionado.')
    return engine


def build_workflow(engine_id, prompt, negative, width, height, steps, cfg, seed, prefix, base_image_name=None):
    require_model_allowed(engine_id=engine_id)
    if engine_id in {"llada_base", "llada_turbo", "hidream_o1"}:
        if base_image_name:
            raise ValueError("Este motor está integrado somente para gerar imagens a partir de texto.")
        if engine_id == "hidream_o1":
            return _build_hidream(prompt, negative, width, height, steps, cfg, seed, prefix)
        return _build_llada(engine_id, prompt, negative, width, height, steps, cfg, seed, prefix)
    if engine_id in {"qwen21", "qwen21_fix"}:
        if engine_id == "qwen21_fix" and base_image_name:
            raise ValueError("O Fix comunitário está disponível somente para gerar imagens.")
        graph = build_qwen(prompt, negative, QWEN_MODEL, width, height, steps, cfg, seed, prefix, base_image_name)
        if engine_id == "qwen21_fix":
            graph["11"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
                "model": ["1", 0], "lora_name": FIX_LORA, "strength_model": 1.0}}
            graph["6"]["inputs"]["model"] = ["11", 0]
        return graph
    if engine_id != "flux3_klein" or base_image_name:
        raise ValueError("Motor de imagem ou modo não integrado.")
    full_prompt = prompt if not negative else f"{prompt}\nAvoid these elements: {negative}"
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": FLUX_MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": FLUX_CLIP, "type": "flux3", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": FLUX_VAE}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": FLUX_UPSAMPLER, "type": "flux3", "device": "default"}},
        "5": {"class_type": "TextGenerate", "inputs": {
            "clip": ["4", 0], "prompt": full_prompt, "max_length": 3584, "sampling_mode": "on",
            "sampling_mode.temperature": 1.0, "sampling_mode.top_k": 1, "sampling_mode.top_p": 0.95,
            "sampling_mode.min_p": 0.0, "sampling_mode.repetition_penalty": 1.05,
            "sampling_mode.seed": seed, "sampling_mode.presence_penalty": 1.5,
            "thinking": False, "use_default_template": True, "mtp": "off",
            "system_prompt": Path(__file__).with_name("flux3_t2i_system_prompt.txt").read_text(encoding="utf-8")}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ["5", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
        "8": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["8", 0],
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
    }


def _build_llada(engine_id, prompt, negative, width, height, steps, cfg, seed, prefix):
    require_model_allowed(engine_id=engine_id)
    # T8's Base/Turbo text workflows: the AIO provides model, encoder and VAE.
    turbo = engine_id == "llada_turbo"
    if turbo and not 2 <= steps <= 4:
        raise ValueError("LLaDA Turbo requer de dois a quatro passos de difusão.")
    return {
        "1": {"class_type": "T8LLaDAImageCheckpointLoader", "inputs": {"ckpt_name": LLADA_TURBO if turbo else LLADA_BASE}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}},
        "4": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "cfg": 1.0 if turbo else cfg}},
        "5": {"class_type": "T8SamplerLLaDAImageTurbo", "inputs": {}} if turbo else {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "6": {"class_type": "T8LLaDAImageScheduler", "inputs": {"model": ["1", 0], "steps": steps}},
        "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "8": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "9": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["7", 0], "guider": ["4", 0], "sampler": ["5", 0], "sigmas": ["6", 0], "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
    }


def _build_hidream(prompt, negative, width, height, steps, cfg, seed, prefix):
    # Official O1 Full text path: pixel-space latent, noise scale 8 and seam smoothing.
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": HIDREAM_MODEL}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}},
        "4": {"class_type": "ModelNoiseScale", "inputs": {"model": ["1", 0], "noise_scale": 8.0}},
        "5": {"class_type": "HiDreamO1PatchSeamSmoothing", "inputs": {"model": ["4", 0], "start_percent": 0.8, "end_percent": 1.0, "pattern": "single_shift", "passes": "ramp_2_4", "blend": "median", "strength": 1.0}},
        "6": {"class_type": "BasicScheduler", "inputs": {"model": ["4", 0], "scheduler": "normal", "steps": steps, "denoise": 1.0}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "dpmpp_2m_sde_gpu"}},
        "8": {"class_type": "EmptyHiDreamO1LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "9": {"class_type": "SamplerCustom", "inputs": {"model": ["5", 0], "positive": ["2", 0], "negative": ["3", 0], "sampler": ["7", 0], "sigmas": ["6", 0], "latent_image": ["8", 0], "add_noise": True, "noise_seed": seed, "cfg": cfg}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
    }
