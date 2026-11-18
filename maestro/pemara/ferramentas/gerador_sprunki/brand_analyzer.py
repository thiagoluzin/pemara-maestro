"""
brand_analyzer.py
Analisa uma imagem de marca e extrai informações para geração de Sprunki.

Dependências:
    pip install Pillow colorthief numpy transformers torch open-clip-torch

Uso:
    python brand_analyzer.py --image nescau.png --name Nescau
    python brand_analyzer.py --image coca.png --name "Coca-Cola" --db sprunki.db
"""

import json
import argparse
import sqlite3
from pathlib import Path

from PIL import Image
import numpy as np

# ─── Imports opcionais ────────────────────────────────────────────────────────
try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import torch
    import open_clip
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False
    print("[AVISO] open_clip não encontrado. Análise de estilo limitada.")
    print("        pip install open-clip-torch")


# ─── Paleta de cores ──────────────────────────────────────────────────────────

def extract_dominant_colors(image_path: str, n: int = 6) -> list[dict]:
    """
    Retorna as N cores dominantes com: hex, rgb, hsl, nome aproximado, percentual.
    Ignora pixels transparentes.
    """
    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)

    # Remove transparência
    mask = arr[:, :, 3] >= 128
    visible = arr[mask][:, :3].astype(float)

    if len(visible) == 0:
        return []

    # Reduz amostra para performance (máx 10k pixels)
    if len(visible) > 10_000:
        idx = np.random.choice(len(visible), 10_000, replace=False)
        visible = visible[idx]

    if HAS_SKLEARN:
        km = KMeans(n_clusters=n, n_init=10, random_state=42)
        labels = km.fit_predict(visible)
        centers = km.cluster_centers_.astype(int)
        counts = np.bincount(labels)
        total = counts.sum()
        order = np.argsort(-counts)
    else:
        # Fallback simples: divide em blocos de cor
        from collections import Counter
        quantized = (visible // 32 * 32).astype(int)
        counter = Counter(map(tuple, quantized))
        top = counter.most_common(n)
        centers = np.array([list(c) for c, _ in top])
        counts = np.array([cnt for _, cnt in top])
        total = counts.sum()
        order = range(n)

    result = []
    for i in order:
        r, g, b = int(centers[i][0]), int(centers[i][1]), int(centers[i][2])
        pct = round(counts[i] / total * 100, 1)
        h, s, l = _rgb_to_hsl(r, g, b)
        result.append({
            "hex":  f"#{r:02X}{g:02X}{b:02X}",
            "rgb":  [r, g, b],
            "hsl":  [h, s, l],
            "name": _color_name(h, s, l),
            "pct":  pct,
        })

    return result


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    r_, g_, b_ = r / 255, g / 255, b / 255
    cmax, cmin = max(r_, g_, b_), min(r_, g_, b_)
    delta = cmax - cmin
    l = (cmax + cmin) / 2
    s = 0 if delta == 0 else delta / (1 - abs(2 * l - 1))
    if delta == 0:
        h = 0.0
    elif cmax == r_:
        h = 60 * (((g_ - b_) / delta) % 6)
    elif cmax == g_:
        h = 60 * ((b_ - r_) / delta + 2)
    else:
        h = 60 * ((r_ - g_) / delta + 4)
    return round(h, 1), round(s, 3), round(l, 3)


def _color_name(h: float, s: float, l: float) -> str:
    """Nomeia a cor aproximadamente em português."""
    if l < 0.1:  return "preto"
    if l > 0.92: return "branco"
    if s < 0.12: return "cinza"
    if   h < 15 or h >= 345: return "vermelho"
    elif h < 40:  return "laranja"
    elif h < 70:  return "amarelo"
    elif h < 150: return "verde"
    elif h < 195: return "ciano"
    elif h < 260: return "azul"
    elif h < 290: return "roxo"
    elif h < 330: return "rosa"
    else:         return "vermelho"


# ─── Análise de estilo via CLIP ───────────────────────────────────────────────

# Descritores candidatos que o CLIP vai ranquear
STYLE_TAGS = [
    # Energia / vibe
    "energetic", "calm", "playful", "serious", "fun", "aggressive", "cute",
    # Visual
    "colorful", "monochrome", "minimalist", "bold", "retro", "futuristic",
    # Mascote / personagem
    "has mascot", "no mascot", "animal mascot", "human mascot", "cartoon",
    # Produto
    "food brand", "drink brand", "tech brand", "sport brand", "toy brand",
    # Forma
    "round shapes", "angular shapes", "organic shapes", "geometric",
]

SPRUNKI_STYLE_DESCRIPTORS = [
    "round body", "pill shaped", "big round eyes", "small arms", "no legs",
    "floating", "cartoon character", "simple silhouette", "thick outline",
]


def analyze_style_with_clip(image_path: str) -> dict:
    """
    Usa CLIP para ranquear os tags de estilo na imagem da marca.
    Retorna os top tags e similaridade com estilo Sprunki.
    """
    if not HAS_CLIP:
        return {"error": "open_clip não instalado"}

    device = "cuda" if hasattr(torch, "cuda") and torch.cuda.is_available() else "cpu"
    print(f"  CLIP rodando em: {device}")

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai"
    )
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer("ViT-B-32")

    img = preprocess(Image.open(image_path)).unsqueeze(0).to(device)

    with torch.no_grad():
        img_feat = model.encode_image(img)
        img_feat /= img_feat.norm(dim=-1, keepdim=True)

        # Ranqueia tags de estilo
        txt_tokens = tokenizer(STYLE_TAGS).to(device)
        txt_feat = model.encode_text(txt_tokens)
        txt_feat /= txt_feat.norm(dim=-1, keepdim=True)
        sims = (img_feat @ txt_feat.T).squeeze(0).cpu().numpy()

        style_scores = sorted(
            zip(STYLE_TAGS, sims.tolist()),
            key=lambda x: -x[1]
        )

        # Similaridade com estilo Sprunki
        sprunki_tokens = tokenizer(SPRUNKI_STYLE_DESCRIPTORS).to(device)
        sprunki_feat = model.encode_text(sprunki_tokens)
        sprunki_feat /= sprunki_feat.norm(dim=-1, keepdim=True)
        sprunki_sims = (img_feat @ sprunki_feat.T).squeeze(0).cpu().numpy()
        sprunki_score = float(sprunki_sims.mean())

    return {
        "top_style_tags": [t for t, s in style_scores[:8] if s > 0.2],
        "all_scores":     [(t, round(float(s), 4)) for t, s in style_scores],
        "sprunki_affinity": round(sprunki_score, 4),
    }


# ─── Construtor de prompt ─────────────────────────────────────────────────────

SPRUNKI_BASE_PROMPT = (
    "sprunki character, cartoon music game character, "
    "round pill-shaped body, big circular eyes, small stub arms, "
    "thick black outline, flat 2d style, transparent background, "
    "idle pose, centered composition"
)

COLOR_INTENSITY_WORDS = {
    "bright":   lambda s, l: s > 0.7 and 0.4 < l < 0.7,
    "pastel":   lambda s, l: s < 0.4 and l > 0.6,
    "dark":     lambda s, l: l < 0.3,
    "vivid":    lambda s, l: s > 0.8,
    "muted":    lambda s, l: s < 0.3,
    "neon":     lambda s, l: s > 0.9 and l > 0.5,
}


def build_generation_prompt(brand_name: str, palette: list[dict], style: dict) -> str:
    """
    Constrói o prompt de geração baseado na análise da marca.
    """
    # Cores principais
    color_names = [c["name"] for c in palette[:3]]
    color_hexes = [c["hex"] for c in palette[:3]]
    color_str = ", ".join(color_names)

    # Intensidade da paleta
    h, s, l = palette[0]["hsl"]
    intensity_words = [w for w, fn in COLOR_INTENSITY_WORDS.items() if fn(s, l)]
    intensity = intensity_words[0] if intensity_words else "vibrant"

    # Tags de estilo
    style_tags = style.get("top_style_tags", [])[:4]
    style_str = ", ".join(style_tags) if style_tags else ""

    # Prompt final
    prompt = (
        f"{SPRUNKI_BASE_PROMPT}, "
        f"inspired by {brand_name} brand, "
        f"{intensity} {color_str} color scheme, "
        f"body color {color_hexes[0]}, "
        f"accent color {color_hexes[1] if len(color_hexes) > 1 else color_hexes[0]}, "
    )

    if style_str:
        prompt += f"{style_str} aesthetic, "

    # Elementos de mascote da marca se detectado
    if "has mascot" in style_tags:
        prompt += f"character inspired by {brand_name} mascot, "

    if "food brand" in style_tags or "drink brand" in style_tags:
        prompt += f"wearing {brand_name} themed accessories, "

    prompt += "high quality illustration, game ready sprite"

    return prompt.strip().rstrip(",")


NEGATIVE_PROMPT = (
    "realistic, photograph, 3d render, text, watermark, blurry, "
    "extra limbs, deformed, nsfw, ugly, low quality, "
    "background, shadow, multiple characters"
)


# ─── Pipeline principal ───────────────────────────────────────────────────────

def analyze_brand(image_path: str, brand_name: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  Analisando marca: {brand_name}")
    print(f"  Imagem: {image_path}")
    print(f"{'='*60}\n")

    result = {
        "brand_name": brand_name,
        "image_path": image_path,
        "palette":    [],
        "style":      {},
        "prompt":     "",
        "negative_prompt": NEGATIVE_PROMPT,
    }

    # 1. Extração de cores
    print("  [1/3] Extraindo paleta de cores...")
    palette = extract_dominant_colors(image_path, n=6)
    result["palette"] = palette
    print(f"        Cores: {[c['hex'] for c in palette]}")

    # 2. Análise de estilo
    print("  [2/3] Analisando estilo com CLIP...")
    style = analyze_style_with_clip(image_path)
    result["style"] = style
    if "top_style_tags" in style:
        print(f"        Tags: {style['top_style_tags']}")
    if "sprunki_affinity" in style:
        print(f"        Afinidade Sprunki: {style['sprunki_affinity']:.3f}")

    # 3. Construção de prompt
    print("  [3/3] Construindo prompt de geração...")
    prompt = build_generation_prompt(brand_name, palette, style)
    result["prompt"] = prompt
    print(f"\n  PROMPT GERADO:\n  {prompt}\n")

    return result


def save_to_db(analysis: dict, db_path: str) -> None:
    """Salva a análise de marca no banco de dados."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO brand_analyses (brand_name, image_path, palette_json, style_tags_json, prompt_used)
        VALUES (?, ?, ?, ?, ?)
    """, (
        analysis["brand_name"],
        analysis["image_path"],
        json.dumps(analysis["palette"]),
        json.dumps(analysis["style"].get("top_style_tags", [])),
        analysis["prompt"],
    ))
    conn.commit()
    conn.close()
    print(f"  Análise salva no DB: {db_path}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analisa marca para geração de Sprunki")
    parser.add_argument("--image", required=True, help="Caminho da imagem da marca")
    parser.add_argument("--name",  required=True, help="Nome da marca")
    parser.add_argument("--db",    default=None,  help="Salvar no banco SQLite")
    parser.add_argument("--out",   default=None,  help="Salvar análise em JSON")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"[ERRO] Imagem não encontrada: {args.image}")
        return

    result = analyze_brand(args.image, args.name)

    # Salva resultado
    out_path = args.out or f"{args.name.lower().replace(' ', '_')}_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  JSON salvo: {out_path}")

    if args.db and Path(args.db).exists():
        save_to_db(result, args.db)


if __name__ == "__main__":
    main()
