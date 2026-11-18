"""
sprunki_generator.py
Gera um novo personagem Sprunki baseado na análise de marca.
Roda localmente na RTX 5080 via diffusers + Flux.1-dev.

Dependências:
    pip install diffusers transformers accelerate sentencepiece protobuf
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

Primeira execução baixa o modelo (~24GB):
    Flux.1-dev: black-forest-labs/FLUX.1-dev

Uso:
    python sprunki_generator.py --analysis nescau_analysis.json --out sprunki_nescau.png
    python sprunki_generator.py --prompt "sprunki character, brown chocolate..." --out test.png
"""

import json
import argparse
import os
from pathlib import Path
from datetime import datetime

import torch
from PIL import Image


# ─── Modelo ───────────────────────────────────────────────────────────────────

MODEL_ID = "black-forest-labs/FLUX.1-dev"      # melhor qualidade
# MODEL_ID = "black-forest-labs/FLUX.1-schnell"  # mais rápido (~4 steps)

# Parâmetros padrão para geração de personagens
DEFAULT_PARAMS = {
    "width":             1024,
    "height":            1024,
    "num_inference_steps": 28,   # Flux.1-dev recomenda 20-50
    "guidance_scale":    3.5,    # Flux.1 usa guidance mais baixo
    "max_sequence_length": 512,
}

# Parâmetros para modo rápido (testes)
FAST_PARAMS = {
    "width":             768,
    "height":            768,
    "num_inference_steps": 15,
    "guidance_scale":    3.5,
    "max_sequence_length": 256,
}


def load_pipeline(model_id: str = MODEL_ID, use_lora: str = None):
    """
    Carrega o pipeline Flux.1 com otimizações para RTX 5080.
    
    RTX 5080 (16GB VRAM) → roda Flux.1-dev em bf16 sem problemas.
    """
    from diffusers import FluxPipeline

    print(f"  Carregando modelo: {model_id}")
    print(f"  VRAM disponível: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")

    pipe = FluxPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,   # bf16 ideal para RTX 50xx
    )

    # Otimizações de memória
    pipe.enable_attention_slicing()

    # Move para GPU
    pipe = pipe.to("cuda")

    # LoRA Sprunki (se treinada)
    if use_lora and Path(use_lora).exists():
        print(f"  Carregando LoRA: {use_lora}")
        pipe.load_lora_weights(use_lora)
        print(f"  LoRA carregada.")

    print("  Pipeline pronto.\n")
    return pipe


# ─── Geração ──────────────────────────────────────────────────────────────────

def generate_sprunki(
    pipe,
    prompt: str,
    negative_prompt: str = "",
    seed: int = None,
    fast: bool = False,
    **override_params,
) -> Image.Image:
    """
    Gera a imagem do Sprunki.
    
    Flux.1-dev não usa negative_prompt nativamente,
    mas mantemos para compatibilidade com SDXL.
    """
    params = FAST_PARAMS.copy() if fast else DEFAULT_PARAMS.copy()
    params.update(override_params)

    generator = None
    if seed is not None:
        generator = torch.Generator("cuda").manual_seed(seed)

    print(f"  Gerando: {params['width']}x{params['height']}, "
          f"{params['num_inference_steps']} steps, seed={seed}")
    print(f"  Prompt: {prompt[:120]}...\n")

    result = pipe(
        prompt=prompt,
        generator=generator,
        **{k: v for k, v in params.items()},
    )

    return result.images[0]


def remove_background(image: Image.Image) -> Image.Image:
    """
    Remove o fundo da imagem gerada para obter PNG transparente.
    Usa rembg se disponível, fallback simples caso contrário.
    """
    try:
        from rembg import remove
        print("  Removendo fundo com rembg...")
        img_bytes = image.tobytes()

        import io
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        output = remove(buf.read())
        return Image.open(io.BytesIO(output)).convert("RGBA")
    except ImportError:
        print("  [AVISO] rembg não instalado. PNG com fundo branco.")
        print("          pip install rembg")
        return image


def post_process(image: Image.Image, target_size: int = 512) -> Image.Image:
    """
    Redimensiona para o tamanho padrão dos sprites Sprunki (512x512).
    """
    img = image.convert("RGBA")
    img = img.resize((target_size, target_size), Image.LANCZOS)
    return img


# ─── Pipeline completo ────────────────────────────────────────────────────────

def run_generation(
    analysis_path: str = None,
    prompt: str = None,
    out_path: str = None,
    lora_path: str = None,
    seed: int = 42,
    fast: bool = False,
    no_rembg: bool = False,
    db_path: str = None,
) -> str:
    """
    Pipeline completo: análise → geração → pós-processamento → salvamento.
    """
    # 1. Carrega análise ou usa prompt direto
    if analysis_path:
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        prompt = analysis["prompt"]
        brand_name = analysis["brand_name"]
        negative = analysis.get("negative_prompt", "")
    else:
        brand_name = "custom"
        negative = (
            "realistic, photograph, 3d render, text, watermark, blurry, "
            "extra limbs, deformed, nsfw, low quality, background"
        )

    # 2. Define nome de saída
    if out_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = brand_name.lower().replace(" ", "_")
        out_path = f"sprunki_{safe_name}_{ts}.png"

    # 3. Carrega pipeline
    pipe = load_pipeline(MODEL_ID, use_lora=lora_path)

    # 4. Gera
    image = generate_sprunki(
        pipe=pipe,
        prompt=prompt,
        negative_prompt=negative,
        seed=seed,
        fast=fast,
    )

    # 5. Remove fundo
    if not no_rembg:
        image = remove_background(image)

    # 6. Redimensiona
    image = post_process(image, target_size=512)

    # 7. Salva
    image.save(out_path, "PNG")
    print(f"\n  Sprunki salvo: {out_path}")

    # 8. Registra no DB
    if db_path and Path(db_path).exists() and analysis_path:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("""
            INSERT INTO characters
                (game_id, name, char_type, image_path, palette_json)
            VALUES (
                (SELECT id FROM games WHERE name='Generated' LIMIT 1),
                ?, 'Generated', ?, ?
            )
        """, (
            f"Sprunki_{brand_name}",
            out_path,
            json.dumps([c["hex"] for c in analysis.get("palette", [])]),
        ))
        conn.commit()
        conn.close()
        print(f"  Registrado no DB: {db_path}")

    return out_path


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gerador de Sprunkis via Flux.1")
    parser.add_argument("--analysis", default=None,    help="JSON de análise de marca")
    parser.add_argument("--prompt",   default=None,    help="Prompt direto (alternativa ao --analysis)")
    parser.add_argument("--out",      default=None,    help="Caminho do PNG de saída")
    parser.add_argument("--lora",     default=None,    help="Caminho do arquivo LoRA (.safetensors)")
    parser.add_argument("--seed",     type=int, default=42, help="Seed para reprodutibilidade")
    parser.add_argument("--fast",     action="store_true",  help="Modo rápido (menos steps)")
    parser.add_argument("--no-rembg", action="store_true",  help="Não remover fundo")
    parser.add_argument("--db",       default=None,    help="Banco SQLite para registrar resultado")
    args = parser.parse_args()

    if not args.analysis and not args.prompt:
        parser.error("Forneça --analysis ou --prompt")

    run_generation(
        analysis_path=args.analysis,
        prompt=args.prompt,
        out_path=args.out,
        lora_path=args.lora,
        seed=args.seed,
        fast=args.fast,
        no_rembg=args.no_rembg,
        db_path=args.db,
    )


if __name__ == "__main__":
    main()
