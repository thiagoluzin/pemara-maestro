"""
lora_prep.py
Prepara o dataset de treinamento da LoRA Sprunki a partir dos sprites extraídos.

Lê o assets_map.json, seleciona os melhores sprites de personagens,
redimensiona para 512x512, remove fundos ruins, e organiza no formato
esperado pelo kohya_ss para treinar Flux.1-dev LoRA.

Saída esperada pelo kohya_ss:
  lora_dataset/
  └── img/
      └── {repeats}_sprunki_char/   ← ex: 20_sprunki_char
          ├── oren_idle.png
          ├── paddy_idle.png
          └── ...                   ← um arquivo por personagem

  lora_dataset/
  └── log/
  └── model/

Dependências:
    pip install Pillow numpy rembg

Uso:
    python lora_prep.py --map assets_map.json --out lora_dataset
    python lora_prep.py --map assets_map.json --out lora_dataset --repeats 20 --min-size 80
"""

import json
import argparse
import shutil
import re
from pathlib import Path
import numpy as np

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    raise SystemExit("[ERRO] pip install Pillow")

try:
    from rembg import remove as rembg_remove
    import io
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("[AVISO] rembg não instalado — sprites com fundo não serão limpados.")
    print("        pip install rembg")

# ─── Filtros ──────────────────────────────────────────────────────────────────

UI_KEYWORDS = {
    'button','buttons','bar','bars','settings','reset','close','more',
    'preview','stage','gallery','polo','dark mode','accent color','icons',
    'sprite2','sprite10','sprite1','leftarrow','backdrop','achievement',
    'credit','galleryimages','old gallery','mute buttons',
}

def is_character(name: str) -> bool:
    n = name.lower().strip()
    return not any(kw in n for kw in UI_KEYWORDS)

# Palavras-chave de personagens conhecidos
CHARACTER_HINTS = re.compile(
    r'\b(beat|melody|voice|effect|acid|tox|sulfur|broker|moch|coka|peppi|'
    r'thysto|animus|penz|skymon|paxo|medio|glix|oren|paddy|gray|funbot|'
    r'simon|clukr|jevin|vineria|tunner|wenda|raddy|brud|mr\s*fun|'
    r'character|char|sprunki)\b',
    re.IGNORECASE
)

# ─── Análise de qualidade do sprite ───────────────────────────────────────────

def sprite_quality_score(img: Image.Image) -> float:
    """
    Pontuação 0–1 de qualidade para seleção do dataset.
    Penaliza sprites pequenos, sem transparência, ou quase vazios.
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    arr  = np.array(img)
    alpha = arr[:, :, 3]

    # Percentual de pixels visíveis
    visible_pct = (alpha > 30).sum() / alpha.size

    if visible_pct < 0.03:   # quase vazio
        return 0.0
    if visible_pct > 0.97:   # fundo sólido (sem transparência)
        return 0.1

    # Bounding box do conteúdo visível
    rows = np.any(alpha > 30, axis=1)
    cols = np.any(alpha > 30, axis=0)
    if not rows.any():
        return 0.0

    h_span = np.where(rows)[0][-1] - np.where(rows)[0][0]
    w_span = np.where(cols)[0][-1] - np.where(cols)[0][0]
    min_dim = min(h_span, w_span)

    # Penaliza sprites muito pequenos
    size_score = min(1.0, min_dim / 80)

    # Bônus para sprites mais quadrados (personagens tendem a ser ≈ quadrados)
    aspect = min(h_span, w_span) / max(h_span, w_span) if max(h_span, w_span) > 0 else 0
    aspect_score = 0.5 + aspect * 0.5

    return (size_score * 0.6 + aspect_score * 0.2 + visible_pct * 0.2)


def remove_background(img: Image.Image) -> Image.Image:
    """Remove fundo usando rembg se disponível."""
    if not HAS_REMBG:
        return img
    try:
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        out = rembg_remove(buf.getvalue())
        return Image.open(io.BytesIO(out)).convert('RGBA')
    except Exception:
        return img


def process_for_lora(img: Image.Image, size: int = 512) -> Image.Image:
    """
    Prepara sprite para treino LoRA:
    - Converte para RGBA
    - Remove fundo se necessário
    - Centraliza e redimensiona para size×size em fundo branco
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    arr   = np.array(img)
    alpha = arr[:, :, 3]

    # Se fundo não é transparente, tenta rembg
    bg_pixels = (alpha[:5, :].mean() + alpha[-5:, :].mean() +
                 alpha[:, :5].mean() + alpha[:, -5:].mean()) / 4
    if bg_pixels > 200:  # fundo opaco
        img = remove_background(img)
        arr   = np.array(img)
        alpha = arr[:, :, 3]

    # Recorta bounding box visível
    rows = np.any(alpha > 20, axis=1)
    cols = np.any(alpha > 20, axis=0)
    if not rows.any():
        return None
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]

    margin = int(min(img.width, img.height) * 0.06)
    y0 = max(0, y0 - margin)
    y1 = min(img.height - 1, y1 + margin)
    x0 = max(0, x0 - margin)
    x1 = min(img.width - 1, x1 + margin)

    img = img.crop((x0, y0, x1 + 1, y1 + 1))

    # Fundo branco canvas quadrado
    canvas = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    img.thumbnail((size - 20, size - 20), Image.LANCZOS)
    offset = ((size - img.width) // 2, (size - img.height) // 2)
    canvas.paste(img, offset, img)

    return canvas.convert('RGB')  # kohya_ss usa RGB/JPG


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def prepare_lora_dataset(
    map_path: str,
    out_dir: str,
    repeats: int = 20,
    min_size: int = 60,
    max_per_game: int = 30,
    quality_threshold: float = 0.25,
) -> None:

    map_path = Path(map_path)
    out_dir  = Path(out_dir)

    with open(map_path, 'r', encoding='utf-8') as f:
        assets = json.load(f)

    # Estrutura kohya_ss
    img_dir = out_dir / 'img' / f'{repeats}_sprunki_char'
    img_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'log').mkdir(exist_ok=True)
    (out_dir / 'model').mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  LoRA Dataset Prep")
    print(f"  Jogos      : {len(assets)}")
    print(f"  Saída      : {img_dir}")
    print(f"  Repeats    : {repeats}")
    print(f"{'='*60}\n")

    total_ok = 0
    total_skip = 0
    seen_names = set()  # evita duplicatas entre jogos

    for game_name, game_data in assets.items():
        chars      = game_data.get('characters', [])
        game_count = 0

        for char in chars:
            name  = char.get('name', '').strip()
            image = char.get('image')

            if not is_character(name):
                total_skip += 1
                continue

            if not image or not Path(image).exists():
                total_skip += 1
                continue

            # Evita duplicar o mesmo personagem de jogos diferentes
            key = name.lower().strip()
            if key in seen_names:
                continue

            if game_count >= max_per_game:
                break

            try:
                img = Image.open(image)
            except Exception:
                total_skip += 1
                continue

            # Checa tamanho mínimo
            if min(img.width, img.height) < min_size:
                total_skip += 1
                continue

            # Score de qualidade
            score = sprite_quality_score(img)
            if score < quality_threshold:
                total_skip += 1
                continue

            # Processa
            processed = process_for_lora(img)
            if processed is None:
                total_skip += 1
                continue

            # Nome de arquivo seguro e descritivo
            safe = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_').lower()
            game_safe = re.sub(r'[^\w]', '', game_name[:20]).lower()
            fname = f"{game_safe}_{safe}.jpg"

            # Evita colisões de nome
            dest = img_dir / fname
            if dest.exists():
                fname = f"{game_safe}_{safe}_{game_count}.jpg"
                dest  = img_dir / fname

            processed.save(dest, 'JPEG', quality=95)
            seen_names.add(key)
            game_count += 1
            total_ok   += 1

        print(f"  {game_name[:45]}  →  {game_count} sprites")

    # Relatório final
    print(f"\n{'─'*60}")
    print(f"  Sprites no dataset  : {total_ok}")
    print(f"  Pulados             : {total_skip}")
    print(f"  Dataset pronto em   : {img_dir}")
    print(f"\n  Para treinar (kohya_ss):")
    print(f"  python train_network.py \\")
    print(f"    --pretrained_model_name_or_path flux1-dev.safetensors \\")
    print(f"    --train_data_dir {out_dir}/img \\")
    print(f"    --output_dir {out_dir}/model \\")
    print(f"    --output_name sprunki_lora \\")
    print(f"    --network_module networks.lora_flux \\")
    print(f"    --network_dim 16 --network_alpha 16 \\")
    print(f"    --max_train_steps 1500 \\")
    print(f"    --learning_rate 1e-4 \\")
    print(f"    --resolution 512,512 \\")
    print(f"    --train_batch_size 2 \\")
    print(f"    --mixed_precision bf16")
    print(f"{'─'*60}\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Prepara dataset LoRA Sprunki")
    p.add_argument('--map',       default='assets_map.json')
    p.add_argument('--out',       default='lora_dataset')
    p.add_argument('--repeats',   type=int,   default=20,   help='Repetições kohya_ss')
    p.add_argument('--min-size',  type=int,   default=60,   help='Tamanho mínimo do sprite (px)')
    p.add_argument('--max-game',  type=int,   default=30,   help='Max sprites por jogo')
    p.add_argument('--quality',   type=float, default=0.25, help='Threshold de qualidade 0-1')
    p.add_argument('--incremental', help="Adiciona novas imagens ao dataset existente")
    args = p.parse_args()

    if args.incremental:
        add_to_existing_dataset(args.incremental, args.out)
    else:
        prepare_lora_dataset(
            map_path=args.map,
            out_dir=args.out,
            repeats=args.repeats,
            min_size=args.min_size,
            max_per_game=args.max_game,
            quality_threshold=args.quality,
        )


def add_to_existing_dataset(new_images_dir: str, existing_dataset: str, repeats: int = 20):
    """
    Adiciona novas imagens ao dataset existente sem reprocessar tudo.
    Modo incremental para evolução automática.
    """
    import shutil
    
    existing = Path(existing_dataset)
    new = Path(new_images_dir)
    
    if not existing.exists():
        print(f"  [ERRO] Dataset existente não encontrado: {existing}")
        return 0
    
    if not new.exists():
        print(f"  [ERRO] Diretório novo não encontrado: {new}")
        return 0
    
    img_dir = existing / 'img' / f'{repeats}_sprunki_char'
    img_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for img in new.glob("*.png"):
        dest = img_dir / img.name
        if not dest.exists():
            shutil.copy2(img, dest)
            count += 1
    
    for img in new.glob("*.jpg"):
        dest = img_dir / img.name
        if not dest.exists():
            shutil.copy2(img, dest)
            count += 1
    
    print(f"  → {count} imagens adicionadas ao dataset")
    print(f"  → Dataset atualizado em: {img_dir}")
    return count


if __name__ == '__main__':
    main()
