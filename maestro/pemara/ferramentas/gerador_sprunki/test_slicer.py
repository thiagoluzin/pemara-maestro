import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

def analyze_image(img_path):
    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    
    # Bounding box visível
    visible_rows = np.any(alpha > 20, axis=1)
    if not visible_rows.any():
        return None
    y0, y1 = np.where(visible_rows)[0][[0, -1]]
    
    visible_cols = np.any(alpha > 20, axis=0)
    x0, x1 = np.where(visible_cols)[0][[0, -1]]
    
    # Largura da silhueta por linha
    widths = np.sum(alpha > 20, axis=1)
    
    # Suaviza a curva de larguras para evitar ruídos
    kernel_size = max(5, int((y1 - y0) * 0.05))
    if kernel_size % 2 == 0:
        kernel_size += 1
    smoothed = np.convolve(widths, np.ones(kernel_size)/kernel_size, mode='same')
    
    # Encontra picos e vales na região visível
    # Queremos achar o pescoço (vale) e o centro da cabeça (pico)
    # Procuramos o pico máximo na metade superior
    mid_y = y0 + (y1 - y0) // 2
    head_region_smoothed = smoothed[y0:mid_y]
    if len(head_region_smoothed) == 0:
        return None
    
    # Pico da cabeça (maior largura na metade superior)
    y_head_center = y0 + np.argmax(head_region_smoothed)
    
    # O pescoço é o vale (mínimo local) abaixo do centro da cabeça
    # Procuramos entre y_head_center e y_head_center + 40% da altura total
    search_end = min(y1, y_head_center + int((y1 - y0) * 0.4))
    neck_region = smoothed[y_head_center:search_end]
    if len(neck_region) > 0:
        y_neck = y_head_center + np.argmin(neck_region)
    else:
        y_neck = y_head_center + int((y1 - y0) * 0.2) # fallback
        
    # Estimativa da altura da cabeça baseada na simetria do centro ao pescoço
    head_half_height = y_neck - y_head_center
    y_head_top = max(y0, y_head_center - head_half_height)
    
    # Zonas dinâmicas:
    # 1. Hat: de y0 até y_head_top (com alguma tolerância)
    # 2. Eyes: centralizados ao redor do terço superior da cabeça
    # 3. Mouth: na metade inferior da cabeça (acima do pescoço)
    # 4. Body: do pescoço até y1
    
    # Vamos projetar em coordenadas absolutas
    hat_zone = (y0, max(y0 + 5, y_head_top + int(head_half_height * 0.2)))
    
    # Olhos: ficam tipicamente entre y_head_top e y_head_center (ou um pouco abaixo)
    eyes_y0 = max(y0, y_head_top - int(head_half_height * 0.1))
    eyes_y1 = min(y1, y_head_center + int(head_half_height * 0.3))
    
    # Boca: fica entre y_head_center e y_neck
    mouth_y0 = max(y0, y_head_center - int(head_half_height * 0.1))
    mouth_y1 = min(y1, y_neck + int(head_half_height * 0.1))
    
    # Acessório / Braços: geralmente na lateral e abaixo do pescoço
    acc_y0 = y_neck - int(head_half_height * 0.2)
    acc_y1 = y1
    
    # Corpo: do pescoço até o pé
    body_y0 = y_neck
    body_y1 = y1
    
    return {
        "bbox": (x0, y0, x1, y1),
        "y_head_center": y_head_center,
        "y_neck": y_neck,
        "y_head_top": y_head_top,
        "zones": {
            "hat": (hat_zone[0], hat_zone[1]),
            "eyes": (eyes_y0, eyes_y1),
            "mouth": (mouth_y0, mouth_y1),
            "body": (body_y0, body_y1),
            "accessory": (acc_y0, acc_y1)
        }
    }

def main():
    ref_dir = Path("static/referencias")
    out_preview = Path("static/icons/_previews_test")
    out_preview.mkdir(parents=True, exist_ok=True)
    
    # Filtra por PNG e WebP
    images = [p for p in ref_dir.glob("*") if p.suffix.lower() in [".png", ".webp"]]
    
    print(f"Analisando {len(images)} imagens de referência...")
    for img_path in images:
        res = analyze_image(img_path)
        if not res:
            print(f"  [PULADO] {img_path.name}")
            continue
            
        # Desenha preview
        img = Image.open(img_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Cores para cada zona
        colors = {
            "hat": (255, 200, 0, 80),
            "eyes": (0, 180, 255, 80),
            "mouth": (255, 80, 80, 80),
            "body": (0, 255, 100, 50),
            "accessory": (200, 0, 255, 60)
        }
        
        x0, y0, x1, y1 = res["bbox"]
        
        # Desenha retângulos translúcidos
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        
        for cat, (zy0, zy1) in res["zones"].items():
            color = colors.get(cat, (200, 200, 200, 80))
            draw_ov.rectangle([x0, zy0, x1, zy1], fill=color, outline=color[:3] + (255,))
            
        # Linhas guia para head center e neck
        draw_ov.line([0, res["y_head_center"], img.width, res["y_head_center"]], fill=(255, 255, 255, 255), width=2)
        draw_ov.line([0, res["y_neck"], img.width, res["y_neck"]], fill=(255, 0, 0, 255), width=2)
        draw_ov.line([0, res["y_head_top"], img.width, res["y_head_top"]], fill=(0, 255, 0, 255), width=2)
        
        # Mescla
        merged = Image.alpha_composite(img, overlay)
        merged.save(out_preview / f"test_{img_path.stem}.png")
        print(f"  [OK] {img_path.name} -> test_{img_path.stem}.png")

if __name__ == "__main__":
    main()
