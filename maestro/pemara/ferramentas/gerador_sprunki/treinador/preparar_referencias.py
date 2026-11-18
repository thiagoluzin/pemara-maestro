#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
preparar_referencias.py
Script para converter todas as 45 figuras oficiais do Sprunki (SVGs, PNGs, WebPs)
para o formato de treino LoRA (JPEG 512x512 fundo branco) e gerar legendas (.txt).
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from PIL import Image

# Adiciona o diretório principal das ferramentas ao PATH para importar prompt_builder
MAIN_DIR = Path(__file__).parent.parent
sys.path.append(str(MAIN_DIR))

from prompt_builder import REFERENCE_DESCRIPTIONS

SRC_DIR = MAIN_DIR / "static" / "referencias"
DEST_DIR = MAIN_DIR / "lora_dataset" / "img" / "20_sprunki_char"

def clear_destination_dir():
    """Limpa a pasta de destino mantendo apenas as imagens sintéticas geradas."""
    # Como não queremos apagar as sprunki_synth_*.jpg já geradas (progresso de 1509),
    # removemos apenas os arquivos de referência antigos sprunki_01.jpg a sprunki_45.jpg e seus .txt correspondentes.
    if DEST_DIR.exists():
        print(f"Limpando referências antigas em: {DEST_DIR}")
        for p in DEST_DIR.iterdir():
            if p.is_file() and p.name.startswith("sprunki_") and not p.name.startswith("sprunki_synth_"):
                p.unlink()
    else:
        DEST_DIR.mkdir(parents=True, exist_ok=True)

def process_raster_to_jpeg(src_path: Path, dest_path: Path):
    """Cola a imagem PNG transparente de 512x512 sobre um fundo branco sólido e salva como JPEG."""
    img = Image.open(src_path).convert('RGBA')
    canvas = Image.new('RGB', (512, 512), (255, 255, 255))
    canvas.paste(img, (0, 0), img)
    canvas.save(dest_path, 'JPEG', quality=95)

def build_caption(char_name: str) -> str:
    """Monta a legenda com base nas descrições de prompt_builder.py."""
    desc = REFERENCE_DESCRIPTIONS.get(char_name, "")
    if not desc:
        # Tenta busca case-insensitive caso os nomes variem ligeiramente
        for key, val in REFERENCE_DESCRIPTIONS.items():
            if key.lower().strip() == char_name.lower().strip():
                desc = val
                break
                
    if not desc:
        print(f"  [AVISO] Descrição não encontrada para o personagem: {char_name}. Usando legenda genérica.")
        desc = f"inspired by {char_name} character, unique music game buddy"
        
    return f"sprunki_char, official Incredibox music game character sprite, slender body shape, {desc}"

def main():
    print("="*60)
    print("  COMPILADOR DE DATASET OFICIAL SPRUNKI (45 PERSONAGENS)")
    print("="*60)
    print(f"Origem  : {SRC_DIR.absolute()}")
    print(f"Destino : {DEST_DIR.absolute()}\n")

    if not SRC_DIR.exists():
        print(f"[ERRO] Pasta de origem não existe: {SRC_DIR}")
        sys.exit(1)

    clear_destination_dir()

    # Filtra arquivos de imagem válidos (apenas as referências PNG normalizadas)
    extensions = [".png"]
    files = sorted([p for p in SRC_DIR.iterdir() if p.is_file() and p.suffix.lower() in extensions])

    success_count = 0
    
    for idx, filepath in enumerate(files, 1):
        char_name = filepath.stem # ex: "ACID", "Mr Sun"
        dest_filename = f"sprunki_{idx:02d}.jpg"
        dest_txt_filename = f"sprunki_{idx:02d}.txt"
        
        dest_img_path = DEST_DIR / dest_filename
        dest_txt_path = DEST_DIR / dest_txt_filename
        
        print(f"[{idx:02d}/{len(files)}] Processando {filepath.name} ({char_name})...")
        
        try:
            # 1. Processa/Converte a imagem (todas agora são PNGs normalizadas)
            process_raster_to_jpeg(filepath, dest_img_path)
                
            # 2. Cria a legenda correspondente
            caption_content = build_caption(char_name)
            dest_txt_path.write_text(caption_content, encoding="utf-8")
            
            success_count += 1
            print(f"  -> Salvo: {dest_filename} | Caption: {caption_content[:80]}...")
            
        except Exception as e:
            print(f"  [FALHA] Erro ao processar {filepath.name}: {e}")

    print("\n" + "="*60)
    print(f"  Dataset compilado com sucesso!")
    print(f"  Total processado: {success_count}/{len(files)} personagens")
    print(f"  Destino: {DEST_DIR.absolute()}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
