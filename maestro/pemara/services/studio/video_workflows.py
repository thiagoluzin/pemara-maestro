"""Workflows ComfyUI usados pelo Studio para video local de alta qualidade."""

from __future__ import annotations

from typing import Any
from retired_models import require_model_allowed


HUNYUAN15_I2V_MODEL = "hunyuanvideo1.5_720p_i2v_fp16.safetensors"
HUNYUAN15_VAE = "hunyuanvideo15_vae_fp16.safetensors"
HUNYUAN15_TEXT_ENCODER = "byt5_small_glyphxl_fp16.safetensors"
HUNYUAN15_VISION_ENCODER = "sigclip_vision_patch14_384.safetensors"
QWEN25_VL_ENCODER = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
HUNYUAN15_SR_MODEL = "hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors"
HUNYUAN15_LATENT_UPSCALER = "hunyuanvideo15_latent_upsampler_1080p.safetensors"

# Regra editorial global do Pemara (atura a partir de 2026-07-20 com pemara_estudio_40anos).
#
# Dois contratos coexistem:
#
# 1) Contrato historico (Manus/720p30): preview, intermediario revisavel e master
#    em >= 24 fps. Nenhum preview/intermediario pode estar abaixo desse valor.
#
# 2) Contrato novo (pemara_estudio_40anos / 2026-07-20): Wan 2.2 I2V A14B no
#    sweet-spot oficial do fabricante (81 frames, 480p, 16 fps). A conversao para
#    30/60 fps finais e feita em pos-processamento (RIFE + Real-ESRGAN + ffmpeg).
#    Este contrato e' opt-in atraves de pemara_estudio_40anos=true. O Studio so
#    aceita 16 fps com Wan 2.2 I2V A14B e apenas quando:
#       * pemara_estudio_40anos=true no runner
#       * o modelo selecionado e variante I2V A14B (high+low noise GGUF)
#    Labs soltos (smoke, preview rapido, etc.) permanecem no contrato 1.

MIN_VIDEO_FPS = 16.0     # pemara_estudio_40anos (Sweet-spot Wan A14B)
MIN_VIDEO_FPS_CLASSIC = 24.0
MAX_VIDEO_FPS = 60.0


def validate_video_fps(fps: float, *, classic_only: bool = False) -> float:
    """Valida a cadencia de qualquer video produzido pelo Maestro.

    Por padrao (pemara_estudio_40anos) aceita 16-60 fps. Para fluxo historico
    (Manus, labs, smoke) passe classic_only=True para exigir >= 24 fps.
    """

    try:
        rate = float(fps)
    except (TypeError, ValueError) as exc:
        raise ValueError("fps deve ser numerico") from exc
    lower_bound = MIN_VIDEO_FPS_CLASSIC if classic_only else MIN_VIDEO_FPS
    if rate < lower_bound:
        if classic_only:
            raise ValueError(
                f"FPS abaixo de {int(MIN_VIDEO_FPS_CLASSIC)} e proibido no Pemara (contrato classico); "
                f"recebido: {rate:g}. Use 24, 30 ou 60 FPS."
            )
        raise ValueError(
            f"FPS abaixo de {int(MIN_VIDEO_FPS)} e proibido no Pemara (pemara_estudio_40anos); "
            f"recebido: {rate:g}. Use 16 (sweet-spot Wan), 24, 30 ou 60 FPS."
        )
    if rate > MAX_VIDEO_FPS:
        raise ValueError(f"fps deve ficar entre {int(MIN_VIDEO_FPS)} e {int(MAX_VIDEO_FPS)}")
    return rate


def _node(class_type: str, **inputs: Any) -> dict[str, Any]:
    return {"class_type": class_type, "inputs": inputs}


def build_hunyuan15_i2v_workflow(
    *,
    prompt: str,
    negative: str,
    input_image: str,
    width: int = 1280,
    height: int = 720,
    frames: int = 121,
    fps: float = 24.0,
    steps: int = 50,
    cfg: float = 6.0,
    seed: int = 42,
    filename_prefix: str = "maestro_video/hunyuan15_take",
    latent_prefix: str = "",
    weight_dtype: str = "default",
    content_kind: str = "unknown",
) -> dict[str, Any]:
    """Monta I2V 720p com Sage2 seguro, MODEL nao dinamico e EasyCache.

    O comprimento temporal do HunyuanVideo-1.5 segue ``4n + 1``. O latente
    opcional permite aprovar o MP4 720p e executar super-resolucao depois sem
    regerar o movimento.
    """

    require_model_allowed(HUNYUAN15_I2V_MODEL, "hunyuan_video_15")
    if not prompt.strip():
        raise ValueError("prompt vazio")
    if not input_image.strip():
        raise ValueError("input_image vazio")
    if width % 16 or height % 16:
        raise ValueError("width e height devem ser multiplos de 16")
    if min(width, height) < 288 or max(width, height) > 1920:
        raise ValueError("resolucao fora do intervalo operacional")
    if frames < 25 or (frames - 1) % 4:
        raise ValueError("frames deve seguir 4n + 1 e ser pelo menos 25")
    if not 1 <= steps <= 60:
        raise ValueError("steps deve ficar entre 1 e 60")
    if not 1.0 <= cfg <= 12.0:
        raise ValueError("cfg deve ficar entre 1 e 12")
    fps = validate_video_fps(fps, classic_only=True)
    if weight_dtype not in {"default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"}:
        raise ValueError("weight_dtype invalido")

    # O valor oficial para HunyuanVideo-1.5 I2V 720p e shift=7.
    shift = 7.0  # 720p checkpoint, including portrait; not inferred from height.
    workflow: dict[str, Any] = {
        "1": _node("UNETLoader", unet_name=HUNYUAN15_I2V_MODEL, weight_dtype=weight_dtype),
        "2": _node(
            "DualCLIPLoader",
            clip_name1=QWEN25_VL_ENCODER,
            clip_name2=HUNYUAN15_TEXT_ENCODER,
            type="hunyuan_video_15",
            device="default",
        ),
        "3": _node("CLIPTextEncode", text=prompt.strip(), clip=["2", 0]),
        "4": _node("CLIPTextEncode", text=negative.strip(), clip=["2", 0]),
        "5": _node("VAELoader", vae_name=HUNYUAN15_VAE),
        "6": _node("LoadImage", image=input_image),
        "7": _node("CLIPVisionLoader", clip_name=HUNYUAN15_VISION_ENCODER),
        "8": _node(
            "CLIPVisionEncode",
            clip_vision=["7", 0],
            image=["6", 0],
            crop="center",
        ),
        "9": _node(
            "HunyuanVideo15ImageToVideo",
            positive=["3", 0],
            negative=["4", 0],
            vae=["5", 0],
            width=width,
            height=height,
            length=frames,
            batch_size=1,
            start_image=["6", 0],
            clip_vision_output=["8", 0],
        ),
        "10": _node("ModelSamplingSD3", model=["1", 0], shift=shift),
        "11": _node(
            "BasicScheduler",
            model=["1", 0],
            scheduler="simple",
            steps=steps,
            denoise=1.0,
        ),
        "12": _node("RandomNoise", noise_seed=int(seed)),
        "13": _node("KSamplerSelect", sampler_name="euler"),
        "14": _node(
            "CFGGuider",
            model=["10", 0],
            positive=["9", 0],
            negative=["9", 1],
            cfg=float(cfg),
        ),
        "15": _node(
            "SamplerCustomAdvanced",
            noise=["12", 0],
            guider=["14", 0],
            sampler=["13", 0],
            sigmas=["11", 0],
            latent_image=["9", 2],
        ),
        "16": _node("VAEDecodeTiled", samples=["15", 0], vae=["5", 0], tile_size=512, overlap=64, temporal_size=4096, temporal_overlap=8),
        "17": _node("CreateVideo", images=["16", 0], fps=float(fps)),
        "18": _node(
            "SaveVideo",
            video=["17", 0],
            filename_prefix=filename_prefix,
            format="mp4",
            codec="h264",
            **{"format.codec": "h264"},
        ),
    }
    if latent_prefix.strip():
        workflow["19"] = _node(
            "SaveLatent",
            samples=["15", 0],
            filename_prefix=latent_prefix.strip(),
        )
    # Hunyuan-only acceleration, verified in the owner-authorized pilot.
    # Do not transplant H3 Spectrum/audio-replay or stack feature caches.
    # Compile is excluded after the observed comfy_kitchen.adaln stride failure.
    workflow["hunyuan_safe_acceleration"] = _node(
        "PemaraHunyuan15SafeAcceleration", model=["1", 0],
        sage_mode="fp8_fp32_accum", disable_dynamic_vram=True,
        metrics_prefix=filename_prefix,
    )
    workflow["10"]["inputs"]["model"] = ["hunyuan_safe_acceleration", 0]
    workflow["11"]["inputs"]["model"] = ["10", 0]
    workflow["hunyuan_easycache"] = _node(
        "EasyCache", model=["10", 0], reuse_threshold=0.2,
        start_percent=0.15, end_percent=0.95, verbose=True,
    )
    workflow["14"]["inputs"]["model"] = ["hunyuan_easycache", 0]
    if content_kind in {"animation", "live_action", "mixed"}:
        workflow["hunyuan_content_policy"] = _node(
            "PemaraDLSS5ContentPolicy", content_kind=content_kind, stage="native_preview")
    return workflow


def build_hunyuan15_sr_workflow(
    *,
    prompt: str,
    negative: str,
    input_latent: str,
    input_image: str,
    fps: float = 30.0,
    seed: int = 42,
    filename_prefix: str = "maestro_video/hunyuan15_take_1080p",
    width: int = 1920,
    height: int = 1080,
    noise_augmentation: float = 0.7,
) -> dict[str, Any]:
    """Super-resolucao temporal oficial a partir do latente 720p aprovado.

    Mantem os oito passos e a divisao 4+4 do template oficial do ComfyUI. O
    passe nao usa EasyCache, pois qualidade visual tem prioridade sobre tempo.
    """

    require_model_allowed(HUNYUAN15_SR_MODEL, "hunyuan_video_15")
    if not prompt.strip():
        raise ValueError("prompt vazio")
    if not input_latent.strip():
        raise ValueError("input_latent vazio")
    if not input_image.strip():
        raise ValueError("input_image vazio")
    if (width, height) != (1920, 1080):
        raise ValueError("o passe SR oficial deve produzir 1920x1080")
    fps = validate_video_fps(fps, classic_only=True)
    if not 0.0 <= noise_augmentation <= 1.0:
        raise ValueError("noise_augmentation deve ficar entre 0 e 1")

    return {
        "1": _node("UNETLoader", unet_name=HUNYUAN15_SR_MODEL, weight_dtype="default"),
        "2": _node("LatentUpscaleModelLoader", model_name=HUNYUAN15_LATENT_UPSCALER),
        "3": _node("LoadLatent", latent=input_latent),
        "4": _node(
            "HunyuanVideo15LatentUpscaleWithModel",
            model=["2", 0],
            samples=["3", 0],
            upscale_method="bilinear",
            width=width,
            height=height,
            crop="disabled",
        ),
        "5": _node(
            "DualCLIPLoader",
            clip_name1=QWEN25_VL_ENCODER,
            clip_name2=HUNYUAN15_TEXT_ENCODER,
            type="hunyuan_video_15",
            device="default",
        ),
        "6": _node("CLIPTextEncode", text=prompt.strip(), clip=["5", 0]),
        "7": _node("CLIPTextEncode", text=negative.strip(), clip=["5", 0]),
        "8": _node("VAELoader", vae_name=HUNYUAN15_VAE),
        "9": _node("LoadImage", image=input_image),
        "10": _node("CLIPVisionLoader", clip_name=HUNYUAN15_VISION_ENCODER),
        "11": _node("CLIPVisionEncode", clip_vision=["10", 0], image=["9", 0], crop="center"),
        "12": _node(
            "HunyuanVideo15SuperResolution",
            positive=["6", 0],
            negative=["7", 0],
            latent=["4", 0],
            noise_augmentation=float(noise_augmentation),
            vae=["8", 0],
            start_image=["9", 0],
            clip_vision_output=["11", 0],
        ),
        "13": _node("ModelSamplingSD3", model=["1", 0], shift=2.0),
        "14": _node("BasicScheduler", model=["1", 0], scheduler="simple", steps=8, denoise=1.0),
        "15": _node("SplitSigmas", sigmas=["14", 0], step=4),
        "16": _node("RandomNoise", noise_seed=int(seed)),
        "17": _node("KSamplerSelect", sampler_name="euler"),
        "18": _node(
            "CFGGuider",
            model=["13", 0],
            positive=["12", 0],
            negative=["12", 1],
            cfg=1.0,
        ),
        "19": _node(
            "SamplerCustomAdvanced",
            noise=["16", 0],
            guider=["18", 0],
            sampler=["17", 0],
            sigmas=["15", 0],
            latent_image=["12", 2],
        ),
        "20": _node("DisableNoise"),
        "21": _node(
            "CFGGuider",
            model=["1", 0],
            positive=["6", 0],
            negative=["7", 0],
            cfg=1.0,
        ),
        "22": _node(
            "SamplerCustomAdvanced",
            noise=["20", 0],
            guider=["21", 0],
            sampler=["17", 0],
            sigmas=["15", 1],
            latent_image=["19", 0],
        ),
        "23": _node("VAEDecode", samples=["22", 0], vae=["8", 0]),
        "24": _node("CreateVideo", images=["23", 0], fps=float(fps)),
        "25": _node(
            "SaveVideo",
            video=["24", 0],
            filename_prefix=filename_prefix,
            format="mp4",
            codec="h264",
        ),
    }
