#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gerar_e_selecionar.py
Script para gerar 3.000 imagens sintéticas de OCs Sprunki via API local Flask,
avaliar a qualidade delas em tempo real, manter apenas as 50 melhores
e salvá-las formatadas na pasta do dataset.
"""

import os
import sys
import json
import random
import time
import requests
import argparse
from pathlib import Path
from PIL import Image

# Configuração de paths
TRAINER_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TRAINER_DIR.parent.resolve()

sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(TRAINER_DIR))

try:
    from quality_evaluator import evaluate_sprunki
except ImportError:
    print("[WARN] Nao foi possivel importar quality_evaluator.py diretamente. Usando fallback.")
    evaluate_sprunki = None

from prompt_builder import (
    EYE_PROMPTS, MOUTH_PROMPTS, HAT_PROMPTS, 
    ACCESSORY_PROMPTS, THEME_EXTRA, REFERENCE_DESCRIPTIONS
)

API_URL = "http://localhost:5005"
DATASET_DIR = PROJECT_ROOT / "lora_dataset" / "img" / "20_sprunki_char"
CHECKPOINT_FILE = TRAINER_DIR / "checkpoint_evolucao.json"

BODY_COLORS = [
    "red", "blue", "green", "yellow", "purple", "pink", "orange", "cyan", 
    "lime green", "brown", "magenta", "teal", "gold", "silver", "black", 
    "white", "gray", "pastel blue", "pastel green", "vibrant red", "dark purple", 
    "neon yellow", "neon orange", "neon green", "coral", "indigo", "violet"
]

def make_pure_random_oc():
    """Gera uma configuracao de OC puramente estetica."""
    body_color = random.choice(BODY_COLORS)
    eyes = random.choice(list(EYE_PROMPTS.keys()))
    mouth = random.choice(list(MOUTH_PROMPTS.keys()))
    hat = random.choice(list(HAT_PROMPTS.keys()))
    accessory = random.choice(list(ACCESSORY_PROMPTS.keys()))
    theme = random.choice(list(THEME_EXTRA.keys()))
    
    tags = ["sprunki_char", "official Incredibox music game character sprite", "slender body shape"]
    tags.append(f"{body_color} skin")
    tags.append(f"{eyes} eyes")
    tags.append(f"{mouth} mouth")
    if hat != "none":
        tags.append(f"wearing {hat}")
    if accessory != "none":
        tags.append(f"holding {accessory}")
    if theme != "default":
        tags.append(f"{theme} theme")
    
    extra_tags = "high quality illustration, clean outlines, flat vector design"
    
    return {
        "params": {
            "body_color": body_color,
            "eyes": eyes,
            "mouth": mouth,
            "hat": hat,
            "accessory": accessory,
            "theme": theme,
            "extra_desc": extra_tags,
            "body_character": "none",
            "eyes_character": "none",
            "mouth_character": "none",
            "hat_character": "none",
            "accessory_character": "none"
        },
        "tags": ", ".join(tags)
    }

def make_composite_oc():
    """Gera uma configuracao de OC hibrida baseada em personagens de referencia."""
    ref_list = list(REFERENCE_DESCRIPTIONS.keys())
    
    body_char = random.choice(ref_list) if random.random() > 0.3 else "none"
    eyes_char = random.choice(ref_list) if random.random() > 0.3 else "none"
    mouth_char = random.choice(ref_list) if random.random() > 0.3 else "none"
    hat_char = random.choice(ref_list) if random.random() > 0.5 else "none"
    acc_char = random.choice(ref_list) if random.random() > 0.5 else "none"
    
    if all(c == "none" for c in [body_char, eyes_char, mouth_char, hat_char, acc_char]):
        body_char = random.choice(ref_list)
        eyes_char = random.choice(ref_list)

    body_color = random.choice(BODY_COLORS)
    eyes = random.choice(list(EYE_PROMPTS.keys()))
    mouth = random.choice(list(MOUTH_PROMPTS.keys()))
    hat = random.choice(list(HAT_PROMPTS.keys()))
    accessory = random.choice(list(ACCESSORY_PROMPTS.keys()))
    theme = random.choice(list(THEME_EXTRA.keys()))
    
    tags = ["sprunki_char", "official Incredibox music game character sprite", "slender body shape"]
    if body_char != "none":
        tags.append(f"body structure like {body_char}")
    else:
        tags.append(f"{body_color} skin")
        
    if eyes_char != "none":
        tags.append(f"eyes style like {eyes_char}")
    else:
        tags.append(f"{eyes} eyes")
        
    if mouth_char != "none":
        tags.append(f"mouth shape like {mouth_char}")
    else:
        tags.append(f"{mouth} mouth")
        
    if hat_char != "none":
        tags.append(f"head accessory like {hat_char}")
    elif hat != "none":
        tags.append(f"wearing {hat}")
        
    if acc_char != "none":
        tags.append(f"holding item like {acc_char}")
    elif accessory != "none":
        tags.append(f"holding {accessory}")
        
    if theme != "default":
        tags.append(f"{theme} theme")
        
    extra_tags = "high quality illustration, clean outlines, flat vector design"
    
    return {
        "params": {
            "body_color": body_color,
            "eyes": eyes,
            "mouth": mouth,
            "hat": hat,
            "accessory": accessory,
            "theme": theme,
            "extra_desc": extra_tags,
            "body_character": body_char,
            "eyes_character": eyes_char,
            "mouth_character": mouth_char,
            "hat_character": hat_char,
            "accessory_character": acc_char
        },
        "tags": ", ".join(tags)
    }

import numpy as np

def get_visible_bbox_generic(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Calcula o bounding box visível excluindo pixels transparentes ou brancos."""
    arr = np.array(img)
    if arr.shape[2] == 4:
        mask = (arr[:, :, 3] > 20) & ~((arr[:, :, 0] > 240) & (arr[:, :, 1] > 240) & (arr[:, :, 2] > 240))
    else:
        mask = ~((arr[:, :, 0] > 240) & (arr[:, :, 1] > 240) & (arr[:, :, 2] > 240))
        
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return None
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return int(x0), int(y0), int(x1), int(y1)

def process_and_save_image(raw_img_path: Path, output_img_path: Path, size=512):
    """Redimensiona, normaliza escala e centraliza a imagem no fundo branco sólido."""
    img = Image.open(raw_img_path).convert('RGBA')
    bbox = get_visible_bbox_generic(img)
    if bbox:
        x0, y0, x1, y1 = bbox
        cropped = img.crop((x0, y0, x1, y1))
    else:
        cropped = img
        
    margin = 32
    max_dim = size - 2 * margin
    w, h = cropped.size
    
    ratio = min(max_dim / w, max_dim / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new('RGB', (size, size), (255, 255, 255))
    offset_x = (size - new_w) // 2
    offset_y = (size - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    canvas.save(output_img_path, 'JPEG', quality=95)

def save_checkpoint(completed, top_50):
    """Salva checkpoint de evolucao."""
    checkpoint_data = {
        "completed": completed,
        "top_50": top_50
    }
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, indent=2)

def load_checkpoint():
    """Carrega checkpoint se existir e for valido."""
    if not CHECKPOINT_FILE.exists():
        return 0, []
    
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        completed = data.get("completed", 0)
        top_50 = data.get("top_50", [])
        
        # Validacao física de existencia dos arquivos no dataset
        valid_top_50 = []
        for idx, spr in enumerate(top_50):
            img_path = Path(spr["image_path"])
            txt_path = Path(spr["txt_path"])
            
            # Se os arquivos sumiram do disco, removemos da lista para regenerar
            if img_path.exists() and txt_path.exists():
                valid_top_50.append(spr)
            else:
                print(f"[WARN] Arquivo {img_path.name} listado no checkpoint nao existe. Removendo.")
        
        print(f"[OK] Checkpoint carregado. Progresso: {completed} geracoes concluidas. {len(valid_top_50)} imagens validas no top-50.")
        return completed, valid_top_50
    except Exception as e:
        print(f"[WARN] Erro ao carregar checkpoint ({e}). Iniciando do zero.")
        return 0, []

def main():
    parser = argparse.ArgumentParser(description="Gerador e Seletor de OCs Sprunki")
    parser.add_argument("--test-run", action="store_true", help="Executa apenas 5 geracoes para teste")
    args = parser.parse_args()

    # Total de imagens a gerar
    total_generations = 5 if args.test_run else 3000
    print("============================================================")
    print(f"  AGENTE GERADOR E SELETOR - ALVO: {total_generations} GERACOES")
    print("============================================================")

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = PROJECT_ROOT / "static" / "generated"
    temp_dir.mkdir(parents=True, exist_ok=True)

    completed_count, top_50 = load_checkpoint()

    # Se a execucao anterior terminou ou mudou de escala, redefine
    if completed_count >= total_generations:
        print("[OK] As geracoes anteriores ja atingiram o alvo. Deseja reiniciar? (Limpe o checkpoint ou execute sem checkpoint)")
        completed_count = 0
        top_50 = []

    consecutive_failures = 0

    while completed_count < total_generations:
        completed_count += 1
        pct = (completed_count / total_generations) * 100
        print(f"\n[{completed_count}/{total_generations}] ({pct:.2f}%) Iniciando geracao...")

        # 50% de chance para OC puro ou composto
        cfg = make_composite_oc() if random.random() > 0.5 else make_pure_random_oc()

        try:
            # Envia requisicao POST
            resp = requests.post(f"{API_URL}/api/generate_oc", json=cfg["params"], timeout=30)
            if resp.status_code != 200:
                print(f"  [ERRO] HTTP {resp.status_code} - {resp.text}")
                consecutive_failures += 1
                if consecutive_failures > 5:
                    print("  [ERRO] Muitas falhas consecutivas de conexao API. Abortando.")
                    sys.exit(1)
                completed_count -= 1
                time.sleep(5)
                continue
            
            consecutive_failures = 0
            job_data = resp.json()
            prompt_id = job_data.get("prompt_id")
            print(f"  -> Job enfileirado: {prompt_id}")

            # Polling
            start_time = time.time()
            done = False
            error = False
            output_url = None

            while not done and not error:
                if time.time() - start_time > 300: # 5 minutos maximo
                    print("  [ERRO] Timeout de 5 minutos atingido.")
                    error = True
                    break

                time.sleep(3)

                try:
                    status_resp = requests.get(f"{API_URL}/api/status/{prompt_id}", timeout=10)
                    if status_resp.status_code != 200:
                        continue

                    status_data = status_resp.json()
                    status = status_data.get("status")
                    progress = status_data.get("progress", 0)

                    if status == "done":
                        output_url = status_data.get("output")
                        done = True
                    elif status == "error":
                        print(f"  [ERRO] Falha no ComfyUI: {status_data.get('error')}")
                        error = True
                    else:
                        # Log limpo em ASCII
                        print(f"     Gerando... {progress}%", end="\r")
                except Exception as ex:
                    print(f"     [!] Erro temporario de conexao: {ex}")
                    time.sleep(2)

            if error or not done or not output_url:
                print("  [WARN] Geracao falhou. Pulando.")
                continue

            # Baixa imagem gerada para pasta temporaria
            img_filename = output_url.split("/")[-1]
            local_raw_path = temp_dir / img_filename
            
            img_url = f"{API_URL}{output_url}"
            img_data_resp = requests.get(img_url, timeout=30)
            if img_data_resp.status_code == 200:
                local_raw_path.write_bytes(img_data_resp.content)
            else:
                print(f"  [ERRO] Falha ao baixar imagem de {img_url}")
                continue

            # Avalia a qualidade da imagem
            print("  -> Avaliando qualidade...")
            if evaluate_sprunki:
                eval_results = evaluate_sprunki(
                    image_path=str(local_raw_path),
                    prompt=cfg["tags"],
                    reference_dir=str(DATASET_DIR)
                )
                score = eval_results["total_score"]
                print(f"  -> Score obtido: {score:.2f} (CLIP: {eval_results.get('clip_score',0):.1f}, Color: {eval_results.get('color_score',0):.1f}, Anatomy: {eval_results.get('anatomy_score',0):.1f}, Style: {eval_results.get('style_score',0):.1f})")
            else:
                score = random.uniform(50, 95)
                print(f"  -> Score simulado (quality_evaluator indisponivel): {score:.2f}")

            # Lógica de insercao no top-50
            is_top = False
            inserted_idx = -1

            if len(top_50) < 50:
                # Ainda nao temos 50 itens. Adiciona direto.
                inserted_idx = len(top_50) + 1
                img_name = f"sprunki_synth_{inserted_idx:02d}.jpg"
                txt_name = f"sprunki_synth_{inserted_idx:02d}.txt"
                
                out_img_path = DATASET_DIR / img_name
                out_txt_path = DATASET_DIR / txt_name
                
                # Salva
                process_and_save_image(local_raw_path, out_img_path)
                out_txt_path.write_text(cfg["tags"], encoding="utf-8")
                
                new_item = {
                    "score": score,
                    "image_path": str(out_img_path.resolve()),
                    "txt_path": str(out_txt_path.resolve()),
                    "filename": img_name,
                    "params": cfg["params"],
                    "tags": cfg["tags"]
                }
                top_50.append(new_item)
                top_50.sort(key=lambda x: x["score"], reverse=True)
                is_top = True
                print(f"  [NOVO] Adicionado ao top-50 inicial. Index: {inserted_idx}")
            else:
                # Ja temos 50. Compara com o pior (ultimo item apos ordenacao decrescente)
                worst_item = top_50[-1]
                if score > worst_item["score"]:
                    # Substitui o pior item físico no disco
                    out_img_path = Path(worst_item["image_path"])
                    out_txt_path = Path(worst_item["txt_path"])
                    
                    # Sobrescreve
                    process_and_save_image(local_raw_path, out_img_path)
                    out_txt_path.write_text(cfg["tags"], encoding="utf-8")
                    
                    # Atualiza a lista na memoria
                    worst_item["score"] = score
                    worst_item["params"] = cfg["params"]
                    worst_item["tags"] = cfg["tags"]
                    
                    # Re-ordena decrescente
                    top_50.sort(key=lambda x: x["score"], reverse=True)
                    is_top = True
                    print(f"  [UPGRADE] Substituiu o pior OC do top-50 (Nota antiga: {worst_item['score']:.2f} -> Nova: {score:.2f})")
                else:
                    print(f"  [DESCARTADO] Nota {score:.2f} menor ou igual a pior do top-50 ({worst_item['score']:.2f})")

            # Remove arquivo temporario da geracao
            if local_raw_path.exists():
                try:
                    os.unlink(local_raw_path)
                except Exception:
                    pass

            # Salva o checkpoint a cada 10 iteracoes ou a cada novo top
            if completed_count % 10 == 0 or is_top:
                save_checkpoint(completed_count, top_50)
                print("  [CHECKPOINT] Progresso e top-50 salvos.")

        except Exception as e:
            print(f"  [ERRO] Ocorreu uma excecao inesperada: {e}")
            completed_count -= 1
            time.sleep(5)

    # Conclusao
    save_checkpoint(completed_count, top_50)
    print("\n============================================================")
    print("  PROCESSO DE GERACAO E SELECAO CONCLUIDO!")
    print(f"  Total gerado: {completed_count}")
    print(f"  Top-50 OCs salvos em: {DATASET_DIR.absolute()}")
    if top_50:
        print("  Melhores scores obtidos:")
        for idx, spr in enumerate(top_50[:10], 1):
            print(f"    {idx}. Score {spr['score']:.2f} - {spr['filename']} ({spr['params']['body_color']})")
    print("============================================================\n")

if __name__ == "__main__":
    main()
