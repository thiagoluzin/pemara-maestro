"""
auto_slicer.py
Processa todos os sprites do assets_map.json automaticamente.
Sem trabalho manual — divide cada personagem em partes por zona espacial
e gera parts_index.json que o OC Maker lê diretamente.

Dependências:
    pip install Pillow numpy
"""

import json
import argparse
import shutil
import subprocess
import io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ─── Zonas anatômicas ─────────────────────────────────────────────────────────
# Proporções verticais relativas ao bounding box visível do sprite.
# Ajustadas para a anatomia Sprunki (corpo pill, olhos no topo, boca no meio).
ZONES = {
    "hat":       (0.00, 0.22),   # chapéu / topo da cabeça
    "eyes":      (0.18, 0.50),   # olhos (sobreposição intencional com hat)
    "body":      (0.30, 1.00),   # corpo inteiro (usado como base)
    "mouth":     (0.52, 0.78),   # boca
    "accessory": (0.55, 1.00),   # acessório (braços + base)
}

# Categorias que usam o sprite inteiro (sem corte)
FULL_SPRITE_CATEGORIES = [] # Agora todas as categorias usam recortes dinâmicos específicos

# Margem ao redor do recorte (pixels no espaço original)
CROP_MARGIN = 8

# Tamanho final de cada parte (px)
PART_SIZE = 256

# Filtro de personagens: exclui sprites de UI
UI_KEYWORDS = {
    "button", "buttons", "bar", "bars", "settings", "reset", "close",
    "more", "preview", "stage", "gallery", "polo", "dark mode",
    "accent color", "icons", "sprite2", "sprite10", "sprite1",
    "leftarrow", "leftarrow2", "backdrop", "achievement",
    "credit", "galleryimages", "old gallery", "mute",
}


def is_character(name: str) -> bool:
    n = name.lower()
    return not any(kw in n for kw in UI_KEYWORDS)


# ─── SVG Loader ───────────────────────────────────────────────────────────────

def load_image(img_path: Path) -> Image.Image:
    """Lê um arquivo de imagem (PNG/SVG/WEBP) e retorna como PIL Image RGBA."""
    if img_path.suffix.lower() == ".svg":
        try:
            cmd = [
                "node",
                "-e",
                f"const sharp = require('sharp'); sharp({json.dumps(str(img_path))}).png().toBuffer().then(b => process.stdout.write(b))"
            ]
            res = subprocess.run(cmd, capture_output=True, check=True)
            return Image.open(io.BytesIO(res.stdout)).convert("RGBA")
        except Exception as e:
            print(f"      [AVISO] Falha ao renderizar SVG {img_path.name} via Node-sharp: {e}. Usando PIL fallback.")
            return Image.open(img_path).convert("RGBA")
    else:
        return Image.open(img_path).convert("RGBA")


# ─── Remoção Automática de Fundo ──────────────────────────────────────────────

def remove_background(img: Image.Image) -> Image.Image:
    """
    Detecta e remove fundos sólidos ou quadriculados (fakes) usando floodfill
    de cores de borda dominantes.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
        
    width, height = img.size
    border_pixels = []
    border_coords = []
    
    # Topo e base
    for x in range(width):
        border_coords.append((x, 0))
        border_coords.append((x, height - 1))
    # Esquerda e direita (excluindo cantos já mapeados)
    for y in range(1, height - 1):
        border_coords.append((0, y))
        border_coords.append((width - 1, y))
        
    for x, y in border_coords:
        border_pixels.append(img.getpixel((x, y)))
        
    total_border = len(border_pixels)
    if total_border == 0:
        return img
        
    # Conta frequência de cores opacas na borda
    color_counts = {}
    for color in border_pixels:
        r, g, b, a = color
        if a < 50:
            continue
        rgb = (r, g, b)
        color_counts[rgb] = color_counts.get(rgb, 0) + 1
        
    if not color_counts:
        return img  # Borda já é transparente
        
    # Ordena cores por maior frequência
    sorted_colors = sorted(color_counts.items(), key=lambda item: item[1], reverse=True)
    
    cleaned = img.copy()
    
    for rgb, count in sorted_colors:
        # Se a cor ocupa mais de 10% da borda total, é considerada fundo (ex: solid ou checkerboard square)
        if count > 0.10 * total_border:
            # Varre as bordas e executa floodfill nas áreas conectadas que possuem a cor
            for x, y in border_coords:
                pixel = cleaned.getpixel((x, y))
                if pixel[3] >= 50:
                    dist = sum((pixel[i] - rgb[i])**2 for i in range(3))**0.5
                    if dist <= 15:
                        ImageDraw.floodfill(cleaned, (x, y), (0, 0, 0, 0), thresh=15)
                        
    return cleaned


# ─── Análise Anatômica e Slicing Dinâmico ────────────────────────────────────

def get_visible_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Retorna (x0, y0, x1, y1) dos pixels visíveis na imagem."""
    arr  = np.array(img)
    mask = arr[:, :, 3] > 20          # alpha > 20
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return None
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return int(x0), int(y0), int(x1), int(y1)


def normalize_image_canvas(img: Image.Image, target_size: int = 512, margin: int = 32) -> Image.Image:
    """Corta a imagem para o seu bbox visível, redimensiona mantendo a proporção e centraliza em canvas 512x512."""
    bbox = get_visible_bbox(img)
    if bbox is None:
        return img
    
    x0, y0, x1, y1 = bbox
    cropped = img.crop((x0, y0, x1, y1))
    
    max_dim = target_size - 2 * margin
    w, h = cropped.size
    
    ratio = min(max_dim / w, max_dim / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    offset_x = (target_size - new_w) // 2
    offset_y = (target_size - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    return canvas


def analyze_silhouette(img: Image.Image) -> dict | None:
    """
    Analisa o perfil de largura por linha da silhueta para determinar a anatomia do personagem
    e definir zonas verticais dinâmicas.
    """
    arr = np.array(img)
    alpha = arr[:, :, 3]
    
    # Bounding box visível
    visible_rows = np.any(alpha > 20, axis=1)
    if not visible_rows.any():
        return None
    y0, y1 = np.where(visible_rows)[0][[0, -1]]
    
    visible_cols = np.any(alpha > 20, axis=0)
    x0, x1 = np.where(visible_cols)[0][[0, -1]]
    
    # Largura em pixels ativos por linha
    widths = np.sum(alpha > 20, axis=1)
    
    height = y1 - y0
    if height <= 15:
        return None
        
    # Kernel de suavização proporcional à altura
    kernel_size = max(5, int(height * 0.05))
    if kernel_size % 2 == 0:
        kernel_size += 1
        
    smoothed = np.convolve(widths, np.ones(kernel_size)/kernel_size, mode='same')
    
    # Pescoço: procurado especificamente na região média-baixa vertical (42% a 78% da altura)
    search_y0 = y0 + int(height * 0.42)
    search_y1 = y0 + int(height * 0.78)
    neck_region = smoothed[search_y0:search_y1]
    if len(neck_region) > 0:
        y_neck = search_y0 + np.argmin(neck_region)
    else:
        y_neck = y0 + int(height * 0.5)
        
    # Centro da cabeça: ponto médio entre y0 e y_neck (região da face)
    y_head_center = y0 + int((y_neck - y0) * 0.55)
    
    # Altura estimada da cabeça
    head_half_height = y_neck - y_head_center
    y_head_top = max(y0, y_head_center - head_half_height)
    
    # Encontra os limites esquerdo/direito na altura do centro da cabeça para estimar largura da face
    row_alpha = alpha[y_head_center, :]
    active_cols = np.where(row_alpha > 20)[0]
    if len(active_cols) > 0:
        hx0, hx1 = active_cols[0], active_cols[-1]
    else:
        hx0, hx1 = x0, x1
        
    cx = (hx0 + hx1) // 2
    w_head = hx1 - hx0
    
    # Margens horizontais seguras para face (evita capturar orelhas/braços nas áreas de olhos/boca)
    face_x0 = max(x0, cx - int(w_head * 0.35))
    face_x1 = min(x1, cx + int(w_head * 0.35))
    
    # Zonas de corte verticais absolutas
    hat_y0 = y0
    hat_y1 = y_head_top + int(head_half_height * 0.25)
    
    eyes_y0 = y_head_top - int(head_half_height * 0.1)
    eyes_y1 = y_head_center + int(head_half_height * 0.20)
    
    mouth_y0 = y_head_center + int(head_half_height * 0.10)
    mouth_y1 = y_neck + int(head_half_height * 0.25)
    
    body_y0 = y_neck
    body_y1 = y1
    
    acc_y0 = y_neck - int(head_half_height * 0.2)
    acc_y1 = y1
    
    # Orelhas: laterais da cabeça (exclusivas horizontais da face)
    ears_l_x0 = x0
    ears_l_x1 = cx - int(w_head * 0.22)
    
    ears_r_x0 = cx + int(w_head * 0.22)
    ears_r_x1 = x1
    
    ears_y0 = y_head_top - int(head_half_height * 0.1)
    ears_y1 = y_neck + int(head_half_height * 0.1)
    
    return {
        "hat": (x0, hat_y0, x1, hat_y1),
        "eyes": (face_x0, eyes_y0, face_x1, eyes_y1),
        "mouth": (face_x0, mouth_y0, face_x1, mouth_y1),
        "body": (x0, body_y0, x1, body_y1),
        "accessory": (x0, acc_y0, x1, acc_y1),
        "ears_L": (ears_l_x0, ears_y0, ears_l_x1, ears_y1),
        "ears_R": (ears_r_x0, ears_y0, ears_r_x1, ears_y1)
    }


def get_fallback_zones(img: Image.Image, bbox: tuple) -> dict:
    """Retorna zonas baseadas nas proporções estáticas clássicas (fallback)."""
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0
    
    zx0 = max(0, x0 - CROP_MARGIN)
    zx1 = min(img.width, x1 + CROP_MARGIN)
    
    zones = {}
    for cat, (z0, z1) in ZONES.items():
        zy0 = max(0, int(y0 + h * z0) - CROP_MARGIN)
        zy1 = min(img.height, int(y0 + h * z1) + CROP_MARGIN)
        zones[cat] = (zx0, zy0, zx1, zy1)
        
    ears_l_x0 = max(0, x0 - CROP_MARGIN)
    ears_l_x1 = min(img.width, x0 + int(w * 0.25) + CROP_MARGIN)
    ears_r_x0 = max(0, x1 - int(w * 0.25) - CROP_MARGIN)
    ears_r_x1 = min(img.width, x1 + CROP_MARGIN)
    
    ears_y0 = max(0, int(y0 + h * 0.18) - CROP_MARGIN)
    ears_y1 = min(img.height, int(y0 + h * 0.55) + CROP_MARGIN)
    
    zones["ears_L"] = (ears_l_x0, ears_y0, ears_l_x1, ears_y1)
    zones["ears_R"] = (ears_r_x0, ears_y0, ears_r_x1, ears_y1)
        
    return zones


def resize_with_padding(img: Image.Image, size: int) -> Image.Image:
    """Redimensiona mantendo proporção e centraliza em canvas quadrado."""
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - img.width) // 2, (size - img.height) // 2)
    canvas.paste(img, offset, img if img.mode == "RGBA" else None)
    return canvas


def make_thumbnail(img: Image.Image, size: int = 64) -> Image.Image:
    """Miniatura para a sidebar do OC Maker."""
    return resize_with_padding(img, size)


# ─── Processador Principal ────────────────────────────────────────────────────

def process_sprite(
    name: str,
    image_path: str,
    game_name: str,
    out_dir: Path,
    categories: list[str],
    preview: bool = False,
) -> dict | None:
    """
    Processa um sprite analisando sua silhueta e recortando suas partes dinamicamente.
    """
    img_path = Path(image_path)
    if not img_path.exists():
        return None

    try:
        # Carrega imagem (Node wrapper para SVG se necessário)
        img = load_image(img_path)
    except Exception as e:
        print(f"    [ERRO] {img_path.name}: {e}")
        return None

    # Remove fundos fakes
    img = remove_background(img)

    # Normaliza imagem em canvas 512x512 para consistência
    img = normalize_image_canvas(img)

    bbox = get_visible_bbox(img)
    if bbox is None:
        return None

    # Análise de silhueta ou fallback
    zones = analyze_silhouette(img)
    if zones is None:
        zones = get_fallback_zones(img, bbox)

    invalid_chars = ['?', '*', ':', '<', '>', '|', '"', '\\', '/']
    safe_name = name.lower()
    for char in invalid_chars:
        safe_name = safe_name.replace(char, "")
    safe_name = safe_name.replace(" ", "_").replace("'", "")
    
    game_safe = game_name[:30].lower()
    for char in invalid_chars:
        game_safe = game_safe.replace(char, "")
    game_safe = game_safe.replace(" ", "_")

    result = {
        "name":  name,
        "game":  game_name,
        "parts": {},
    }

    for cat in categories:
        cat_dir = out_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        thumb_dir = out_dir / "thumbs" / cat
        thumb_dir.mkdir(parents=True, exist_ok=True)

        coords = zones.get(cat)
        if coords is None:
            # Caso a categoria pedida não esteja na análise, usa fallback geral
            fallback = get_fallback_zones(img, bbox)
            coords = fallback.get(cat, (0, 0, img.width, img.height))

        zx0, zy0, zx1, zy1 = coords
        part_img = img.crop((zx0, zy0, zx1, zy1))
        part_img = resize_with_padding(part_img, PART_SIZE)
        thumb_img = make_thumbnail(part_img.copy())

        filename      = f"{game_safe}_{safe_name}.png"
        part_path     = cat_dir / filename
        thumb_path    = thumb_dir / filename

        part_img.save(part_path,  "PNG")
        thumb_img.save(thumb_path, "PNG")

        # Frações normalizadas de corte para o front-end
        crop_fraction = {
            "x0": round(zx0 / img.width, 4),
            "x1": round(zx1 / img.width, 4),
            "y0": round(zy0 / img.height, 4),
            "y1": round(zy1 / img.height, 4)
        }

        result["parts"][cat] = {
            "file":  str(part_path.relative_to(out_dir.parent)),
            "thumb": str(thumb_path.relative_to(out_dir.parent)),
            "crop_zone": crop_fraction
        }

    if preview:
        _save_preview(img, zones, name, out_dir / "_previews")

    return result if result["parts"] else None


def _save_preview(img: Image.Image, zones: dict, name: str, preview_dir: Path):
    """Salva uma imagem sobrepondo as regiões cortadas dinamicamente."""
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    # Criar uma imagem de overlay transparente para desenhar as caixas sem sobrescrever a imagem original
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    ZONE_COLORS = {
        "hat":       (255, 200,   0, 60),
        "eyes":      (  0, 180, 255, 60),
        "body":      (  0, 255, 100, 40),
        "mouth":     (255,  80,  80, 60),
        "accessory": (200,   0, 255, 50),
        "ears_L":    (255, 120,   0, 50),
        "ears_R":    (  0, 200, 200, 50),
    }

    for cat, coords in zones.items():
        zx0, zy0, zx1, zy1 = coords
        color = ZONE_COLORS.get(cat, (200, 200, 200, 40))
        draw.rectangle([zx0, zy0, zx1, zy1], fill=color, outline=color[:3] + (200,))

    # Mesclar a imagem do sprite com o overlay de zonas usando composições alpha
    base_img = img.copy().convert("RGBA")
    combined = Image.alpha_composite(base_img, overlay)

    invalid_chars = ['?', '*', ':', '<', '>', '|', '"', '\\', '/']
    safe = name.lower()
    for char in invalid_chars:
        safe = safe.replace(char, "")
    safe = safe.replace(" ", "_")[:40]
    combined.save(preview_dir / f"{safe}_zones.png", "PNG")



# ─── Pipeline Completo ────────────────────────────────────────────────────────

def run(
    assets_path: str,
    out_dir: str,
    categories: list[str],
    games_filter: list[str] | None,
    preview: bool,
    limit: int | None,
) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(assets_path, "r", encoding="utf-8") as f:
        assets = json.load(f)

    parts_index: dict[str, list] = {cat: [] for cat in categories}
    total = 0
    skipped = 0

    print(f"\n{'='*60}")
    print(f"  Auto Slicer — processando assets_map.json")
    print(f"  Categorias: {categories}")
    print(f"  Saída: {out_dir}")
    print(f"{'='*60}\n")

    count = 0
    for game_name, game_data in assets.items():
        if games_filter and not any(f.lower() in game_name.lower() for f in games_filter):
            continue

        chars = game_data.get("characters", [])
        print(f"  [{game_name[:45]}]  {len(chars)} sprites")

        for sprite in chars:
            if limit and count >= limit:
                break

            name  = sprite.get("name", "").strip()
            image = sprite.get("image", "")

            if not is_character(name):
                skipped += 1
                continue

            if not image:
                skipped += 1
                continue

            result = process_sprite(
                name=name,
                image_path=image,
                game_name=game_name,
                out_dir=out,
                categories=categories,
                preview=preview,
            )

            if result:
                for cat, part_data in result["parts"].items():
                    parts_index[cat].append({
                        "id":    f"{game_name[:20]}_{name}",
                        "name":  name,
                        "game":  game_name,
                        "file":  part_data["file"],
                        "thumb": part_data["thumb"],
                        "crop_zone": part_data["crop_zone"],
                        "src_file": image.replace("\\", "/")
                    })
                total += 1
                count += 1
            else:
                skipped += 1

    # Analisa e gera crop zones dinâmicos para imagens na pasta de referências
    ref_dir = Path("static/referencias")
    ref_crop_zones = {}
    if ref_dir.exists():
        print("\n  [REFERÊNCIAS] Processando crop zones dos personagens...")
        ref_files = sorted([p for p in ref_dir.iterdir() if p.is_file() and p.suffix.lower() in [".png", ".webp", ".svg", ".jpg"]])
        for p in ref_files:
            ref_name = p.stem
            try:
                img = load_image(p)
                img = remove_background(img)
                bbox = get_visible_bbox(img)
                if bbox:
                    zones = analyze_silhouette(img)
                    if not zones:
                        zones = get_fallback_zones(img, bbox)
                    
                    ref_crop_zones[ref_name] = {}
                    for cat, coords in zones.items():
                        zx0, zy0, zx1, zy1 = coords
                        ref_crop_zones[ref_name][cat] = {
                            "x0": round(zx0 / img.width, 4),
                            "x1": round(zx1 / img.width, 4),
                            "y0": round(zy0 / img.height, 4),
                            "y1": round(zy1 / img.height, 4)
                        }
                    print(f"    [OK] {ref_name}")
            except Exception as e:
                print(f"    [AVISO] Erro analisando referência {p.name}: {e}")

    parts_index["reference_crop_zones"] = ref_crop_zones

    index_path = out / "parts_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(parts_index, f, indent=2, ensure_ascii=False)

    print(f"\n{'-'*60}")
    print(f"  Sprites processados : {total}")
    print(f"  Pulados (UI/erro)   : {skipped}")
    for cat in categories:
        print(f"  {cat:15} : {len(parts_index[cat])} partes")
    print(f"  parts_index.json    : {index_path}")
    print(f"{'-'*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Auto-slicer de sprites Sprunki")
    parser.add_argument("--assets",     default="assets_map.json",
                        help="Caminho do assets_map.json")
    parser.add_argument("--out",        default="static/icons",
                        help="Pasta de saída das partes")
    parser.add_argument("--categories", nargs="+",
                        default=["body", "eyes", "mouth", "hat", "accessory", "ears_L", "ears_R"],
                        choices=list(ZONES.keys()) + ["body", "ears_L", "ears_R"],
                        help="Categorias a extrair")
    parser.add_argument("--games",      nargs="+", default=None,
                        help="Filtrar por nome de jogo (parcial)")
    parser.add_argument("--preview",    action="store_true",
                        help="Salvar imagens de debug com zonas coloridas")
    parser.add_argument("--limit",      type=int, default=None,
                        help="Limitar número de sprites (para testes)")
    args = parser.parse_args()

    run(
        assets_path=args.assets,
        out_dir=args.out,
        categories=args.categories,
        games_filter=args.games,
        preview=args.preview,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
