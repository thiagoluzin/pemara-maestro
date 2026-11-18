---
name: sprite-image-reading
description: >
  Leitura, análise e visualização de imagens e sprites em Python (Pillow/numpy): inspecionar
  dimensões e canais, fatiar spritesheet em frames (grid fixo ou auto-detecção por transparência),
  extrair paleta de cores, recortar/trim por bounding box, ler/gerar atlas JSON (formato Phaser),
  e montar contact sheet de preview. Use ao trabalhar com sprites, spritesheets, paletas ou
  extrair/inspecionar assets de jogo. Inclui auditoria Unity-like de Sprite Editor para medir
  cellW/cellH, bbox, bottomGap, centerX, topY, bodyH, pivo/origin, variacao de escala e corte.
---

# Skill: Leitura & Visualização de Sprites/Imagens

Ferramentas: `Pillow` (PIL) e `numpy`. Instale de uma vez: `pip install pillow numpy`.

## Auditoria estilo Sprite Editor
Copie o que o Unity ajuda a enxergar no `Sprite Editor`, mas faca no pipeline Phaser:

- `cellW/cellH`: tamanho fixo da celula usada no sheet;
- `bbox`: caixa real do conteudo nao transparente;
- `bottomGap`: distancia do ultimo pixel visivel ate a base da celula;
- `centerX`: centro visual do conteudo; pulo grande entre frames = personagem patinando;
- `topY/bodyH`: topo e altura do corpo; variacao alta = cresce/encolhe;
- `pivot`: para personagem, contrato padrao e `origin (0.5, 1)` no Phaser.

Regra: trim/bbox e ferramenta de medicao, nao formato final automatico. Se o runtime usa grid fixo,
preserve celulas fixas e reancore o conteudo dentro delas. Para armas, sabres, correntes e ataques
largos, divida em mais de uma fita/sheet para dar margem real e evitar corte.

## 1. Inspecionar (antes de processar — Evidence Gate)
```python
from PIL import Image
im = Image.open("sheet.png")
print(im.format, im.size, im.mode)        # ex: PNG (512, 256) RGBA
print("tem alpha:", "A" in im.mode)
```

## 2. Fatiar spritesheet — grid fixo
```python
def slice_grid(path, fw, fh, out="frames"):
    import os; os.makedirs(out, exist_ok=True)
    im = Image.open(path).convert("RGBA")
    W, H = im.size; i = 0
    for y in range(0, H, fh):
        for x in range(0, W, fw):
            im.crop((x, y, x+fw, y+fh)).save(f"{out}/frame_{i:03}.png"); i += 1
    return i
```

## 3. Auto-detectar tamanho do frame (por colunas/linhas transparentes)
```python
import numpy as np
def autodetect_frames(path):
    a = np.array(Image.open(path).convert("RGBA"))
    alpha = a[:, :, 3]
    col_empty = np.where(alpha.sum(axis=0) == 0)[0]   # colunas 100% transparentes = separadores
    row_empty = np.where(alpha.sum(axis=1) == 0)[0]
    return {"colunas_separadoras": col_empty.tolist()[:20],
            "linhas_separadoras": row_empty.tolist()[:20]}
# use os gaps pra inferir largura/altura do frame
```

## 4. Trim / bounding box (recorta o vazio em volta)
```python
im = Image.open("sprite.png").convert("RGBA")
bbox = im.getbbox()          # caixa do conteúdo não-transparente
trimmed = im.crop(bbox) if bbox else im
```

## 5. Extrair paleta (cores dominantes)
```python
def palette(path, n=8):
    im = Image.open(path).convert("RGB").quantize(colors=n)
    pal = im.getpalette()[: n*3]
    cores = [tuple(pal[i:i+3]) for i in range(0, len(pal), 3)]
    hexes = ["#%02x%02x%02x" % c for c in cores]
    return hexes
```

## 6. Ler atlas existente (formato Phaser / TexturePacker JSON Hash)
```python
import json
data = json.load(open("atlas.json", encoding="utf-8"))
frames = data["frames"]                      # {nome: {frame:{x,y,w,h}, ...}}
for nome, f in list(frames.items())[:5]:
    print(nome, f["frame"])
```

## 7. Gerar atlas JSON simples a partir de frames soltos (empacotamento em linha)
```python
def build_atlas(frame_paths, sheet_out="atlas.png", json_out="atlas.json", pad=2):
    imgs = [(p, Image.open(p).convert("RGBA")) for p in frame_paths]
    h = max(im.height for _, im in imgs)
    W = sum(im.width + pad for _, im in imgs) + pad
    sheet = Image.new("RGBA", (W, h + pad*2), (0,0,0,0))
    frames, x = {}, pad
    for p, im in imgs:
        sheet.paste(im, (x, pad))
        frames[p.split("/")[-1]] = {"frame": {"x": x, "y": pad, "w": im.width, "h": im.height}}
        x += im.width + pad
    sheet.save(sheet_out)
    json.dump({"frames": frames, "meta": {"image": sheet_out}}, open(json_out,"w"), indent=1)
```

## 8. Visualização — contact sheet (preview em grade)
```python
def contact_sheet(frame_paths, cols=8, cell=64, out="preview.png"):
    n = len(frame_paths); rows = (n + cols - 1)//cols
    sheet = Image.new("RGBA", (cols*cell, rows*cell), (30,30,40,255))
    for i, p in enumerate(frame_paths):
        im = Image.open(p).convert("RGBA"); im.thumbnail((cell, cell))
        sheet.paste(im, ((i%cols)*cell, (i//cols)*cell), im)
    sheet.save(out)
```

## Notas
- Pixel art: ao redimensionar use `Image.NEAREST` (nunca borre): `im.resize((w,h), Image.NEAREST)`.
- Confirme `mode` (RGBA vs P/paletizado) antes de mexer em alpha — converta com `.convert("RGBA")`.
- Para inspecionar visualmente no chat/relatório, gere a contact sheet e abra a imagem.
- Sprite sem alpha (fundo chroma): remova a cor-chave antes (`Image.getcolors()` pra achar o fundo).
