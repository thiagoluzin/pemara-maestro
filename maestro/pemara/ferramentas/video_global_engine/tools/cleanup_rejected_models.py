"""Remove only model weights explicitly rejected by recorded production QC."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path


REJECTED = {
    # Quantized Wan pairs are redundant on the RTX 5090: FP16 is now the
    # production default and Q8 is retained as the only memory fallback.
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet"
         r"\Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf"): 10_792_055_296,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet"
         r"\Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf"): 10_792_055_296,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\diffusion_models"
         r"\flux1-fill-dev.safetensors"): 23_804_922_408,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\diffusion_models"
         r"\flux1-dev-kontext_fp8_scaled.safetensors"): 11_904_640_136,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\diffusion_models"
         r"\hunyuanvideo1.5_720p_i2v_fp16.safetensors"): 16_653_368_128,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\text_encoders"
         r"\byt5_small_glyphxl_fp16.safetensors"): 438_643_184,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\vae"
         r"\hunyuanvideo15_vae_fp16.safetensors"): 2_521_292_758,
}

COMPATIBILITY_ALIASES = {
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet"
         r"\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf"):
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet"
         r"\Wan2.2-I2V-A14B-HighNoise-Q8_0.gguf"),
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet"
         r"\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf"):
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet"
         r"\Wan2.2-I2V-A14B-LowNoise-Q8_0.gguf"),
}

# Owner-pinned production assets. Cleanup must fail closed before touching any
# rejected file if the active H3/LTX 2.5 shared kit is missing or replaced.
OWNER_PROTECTED = {
    # Gemma 3 is shared by the supported LTX 2.5 workflows. No legacy engine
    # checkpoint is protected or restorable by this cleanup tool.
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\text_encoders"
         r"\gemma_3_12B_it_fp4_mixed.safetensors"): 9_447_702_218,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\diffusion_models"
         r"\minimax_h3_fl2va_pruned_int8_convrot.safetensors"): 20_970_379_616,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\text_encoders"
         r"\qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"): 15_687_142_551,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\vae"
         r"\minimax_h3_video_vae_fp16.safetensors"): 5_207_808_496,
    Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\vae"
         r"\minimax_h3_audio_vae_fp32.safetensors"): 605_254_808,
}


def validate_owner_protected(log: logging.Logger) -> None:
    destructive_targets = set(REJECTED) | set(COMPATIBILITY_ALIASES)
    overlap = destructive_targets & set(OWNER_PROTECTED)
    if overlap:
        raise RuntimeError(
            "Arquivo protegido tambem registrado para remocao: "
            + ", ".join(str(path) for path in sorted(overlap, key=str))
        )
    for path, expected_size in OWNER_PROTECTED.items():
        if not path.is_file():
            raise RuntimeError(f"Modelo protegido ausente; limpeza bloqueada: {path}")
        actual = path.stat().st_size
        if actual != expected_size:
            raise RuntimeError(
                f"Modelo protegido alterado; limpeza bloqueada: {path}: {actual}"
            )
        log.info("PROTEGIDO: %s (%d bytes)", path, actual)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--log",
        type=Path,
        default=Path(__file__).with_name("cleanup_rejected_models.log"),
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(args.log, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    log = logging.getLogger("cleanup-rejected-models")
    validate_owner_protected(log)
    removed = 0
    for alias, target in COMPATIBILITY_ALIASES.items():
        if not alias.exists():
            log.info("ALIAS JA AUSENTE: %s", alias)
            continue
        if not target.exists() or not alias.samefile(target):
            raise RuntimeError(f"Alias nao aponta para o Q8 esperado: {alias}")
        log.info("ALIAS TEMPORARIO: %s -> %s", alias, target)
        if args.apply:
            alias.unlink()
    for path, expected_size in REJECTED.items():
        if not path.exists():
            log.info("JA AUSENTE: %s", path)
            continue
        actual = path.stat().st_size
        if actual != expected_size:
            raise RuntimeError(f"Tamanho inesperado; recusando remover {path}: {actual}")
        if args.apply:
            path.unlink()
            if path.exists():
                raise RuntimeError(f"Falha ao remover {path}")
            removed += actual
            log.info("REMOVIDO: %s (%d bytes)", path, actual)
        else:
            log.info("DRY-RUN removeria: %s (%d bytes)", path, actual)
    log.info("%s bytes=%d", "APLICADO" if args.apply else "DRY-RUN OK", removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
