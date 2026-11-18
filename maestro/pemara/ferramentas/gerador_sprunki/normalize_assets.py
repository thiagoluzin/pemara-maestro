#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
normalize_assets.py
Normaliza todos os sprites de personagens (assets_map.json e static/referencias)
para PNGs transparentes de 512x512 pixels, com o personagem centralizado e margem segura.
"""

import os
import json
import subprocess
import io
import shutil
from pathlib import Path
import numpy as np
from PIL import Image

# Configuração de diretórios
BASE_DIR = Path(__file__).parent.resolve()
ASSETS_MAP_PATH = BASE_DIR / "assets_map.json"
REFERENCIAS_DIR = BASE_DIR / "static" / "referencias"

TARGET_SIZE = 512
MARGIN = 32

def load_and_render_svg_via_node(svg_path: Path) -> Image.Image:
    """Renderiza um arquivo SVG para um buffer PNG usando sharp (Node.js) e abre como PIL Image."""
    node_cmd = (
        f"const sharp = require('sharp'); "
        f"sharp({json.dumps(str(svg_path))})"
        f".png()"
        f".toBuffer()"
        f".then(b => process.stdout.write(b))"
        f".catch(err => {{ console.error(err); process.exit(1); }})"
    )
    cmd = ["node", "-e", node_cmd]
    res = subprocess.run(cmd, capture_output=True, check=True)
    return Image.open(io.BytesIO(res.stdout)).convert("RGBA")

def get_visible_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Calcula o bounding box visível dos pixels não transparentes (alpha > 20)."""
    arr = np.array(img)
    mask = arr[:, :, 3] > 20
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return None
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return int(x0), int(y0), int(x1), int(y1)

def normalize_character_image(img: Image.Image) -> Image.Image:
    """Corta para o bbox visível, redimensiona mantendo proporção e centraliza em 512x512 com margem."""
    bbox = get_visible_bbox(img)
    if bbox is None:
        # Se for totalmente transparente, retorna vazia de 512x512
        return Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), (0, 0, 0, 0))
    
    x0, y0, x1, y1 = bbox
    cropped = img.crop((x0, y0, x1, y1))
    
    max_dim = TARGET_SIZE - 2 * MARGIN
    w, h = cropped.size
    
    ratio = min(max_dim / w, max_dim / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), (0, 0, 0, 0))
    offset_x = (TARGET_SIZE - new_w) // 2
    offset_y = (TARGET_SIZE - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    
    return canvas

def process_file(file_path: Path) -> Path | None:
    """Processa e normaliza um arquivo de imagem in-place, retornando o novo caminho do PNG."""
    if not file_path.exists():
        print(f"  [AVISO] Arquivo não encontrado: {file_path}")
        return None
    
    ext = file_path.suffix.lower()
    if ext not in [".svg", ".png", ".webp", ".jpg", ".jpeg"]:
        return None
    
    try:
        # 1. Carrega a imagem original
        if ext == ".svg":
            img = load_and_render_svg_via_node(file_path)
        else:
            img = Image.open(file_path).convert("RGBA")
            
        # 2. Normaliza para canvas 512x512 transparente e alinhado
        normalized = normalize_character_image(img)
        
        # 3. Determina o caminho de saída (sempre PNG)
        out_path = file_path.with_suffix(".png")
        
        # Salva o arquivo normalizado
        normalized.save(out_path, "PNG")
        
        # Se mudou de extensão (ex: .svg ou .webp para .png), deleta o original antigo
        if out_path != file_path:
            file_path.unlink()
            
        return out_path
        
    except Exception as e:
        print(f"  [ERRO] Falha ao processar {file_path.name}: {e}")
        return None

def normalize_assets_map():
    """Normaliza todos os sprites de personagens apontados no assets_map.json."""
    if not ASSETS_MAP_PATH.exists():
        print(f"[ERRO] assets_map.json não encontrado em {ASSETS_MAP_PATH}")
        return
        
    print("\n>>> Carregando assets_map.json...")
    with open(ASSETS_MAP_PATH, "r", encoding="utf-8") as f:
        assets = json.load(f)
        
    updated_count = 0
    
    for game_name, game_data in assets.items():
        chars = game_data.get("characters", [])
        print(f"  [{game_name}] Processando {len(chars)} personagens...")
        
        for sprite in chars:
            image_rel = sprite.get("image")
            if not image_rel:
                continue
                
            # Evita UI/backdrops/achievements
            name = sprite.get("name", "")
            lower_name = name.lower()
            if any(kw in lower_name for kw in ["button", "bar", "settings", "close", "stage", "gallery", "leftarrow", "backdrop"]):
                continue
                
            original_path = BASE_DIR / image_rel
            new_path = process_file(original_path)
            
            if new_path:
                # Atualiza o caminho relativo no assets_map.json
                rel_path = new_path.relative_to(BASE_DIR)
                sprite["image"] = str(rel_path).replace("\\", "/")
                updated_count += 1
                
    # Salva o assets_map.json atualizado
    with open(ASSETS_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(assets, f, indent=2, ensure_ascii=False)
        
    print(f"[OK] assets_map.json atualizado. {updated_count} sprites normalizados.")

def normalize_referencias():
    """Normaliza todas as referências oficiais em static/referencias/."""
    if not REFERENCIAS_DIR.exists():
        print(f"[ERRO] Diretório de referências não existe: {REFERENCIAS_DIR}")
        return
        
    print("\n>>> Processando diretório de referências: static/referencias/...")
    files = sorted([p for p in REFERENCIAS_DIR.iterdir() if p.is_file()])
    
    updated_count = 0
    for p in files:
        # Pula visualizações e backups
        if p.name.startswith("_") or p.name.startswith("test_") or p.suffix.lower() not in [".svg", ".png", ".webp", ".jpg", ".jpeg"]:
            continue
            
        new_path = process_file(p)
        if new_path:
            updated_count += 1
            
    print(f"[OK] Referências normalizadas. {updated_count} arquivos convertidos para PNG 512x512.")

def main():
    print("="*60)
    print("  NORMALIZADOR DE IMAGENS E SPRITES SPRUNKI")
    print("="*60)
    
    normalize_referencias()
    normalize_assets_map()
    
    print("\nNormalização concluída com sucesso!\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
