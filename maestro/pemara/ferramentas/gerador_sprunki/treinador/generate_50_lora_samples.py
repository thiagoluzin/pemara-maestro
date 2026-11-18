#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_50_lora_samples.py
Script autônomo para gerar 50 imagens sintéticas de OCs Sprunki via API local Flask
e formatá-las corretamente para o dataset de treino LoRA do Kohya_ss.
"""

import os
import sys
import json
import random
import time
import requests
from pathlib import Path
from PIL import Image

sys.path.append(str(Path(__file__).parent))

try:
    from quality_evaluator import evaluate_sprunki
except ImportError:
    evaluate_sprunki = None

from prompt_builder import (
    EYE_PROMPTS, MOUTH_PROMPTS, HAT_PROMPTS, 
    ACCESSORY_PROMPTS, THEME_EXTRA, REFERENCE_DESCRIPTIONS
)

API_URL = "http://localhost:5005"
DATASET_DIR = Path("lora_dataset/img/20_sprunki_char")
REFERENCIAS_DIR = Path("static/referencias")

# Cores de pele variadas
BODY_COLORS = [
    "red", "blue", "green", "yellow", "purple", "pink", "orange", "cyan", 
    "lime green", "brown", "magenta", "teal", "gold", "silver", "black", 
    "white", "gray", "pastel blue", "pastel green", "vibrant red", "dark purple", 
    "neon yellow", "neon orange", "neon green", "coral", "indigo", "violet"
]

def make_pure_random_oc():
    """Gera uma configuração de OC puramente estética."""
    body_color = random.choice(BODY_COLORS)
    eyes = random.choice(list(EYE_PROMPTS.keys()))
    mouth = random.choice(list(MOUTH_PROMPTS.keys()))
    hat = random.choice(list(HAT_PROMPTS.keys()))
    accessory = random.choice(list(ACCESSORY_PROMPTS.keys()))
    theme = random.choice(list(THEME_EXTRA.keys()))
    
    # Tags de legenda
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
    """Gera uma configuração de OC híbrida baseada em personagens de referência."""
    ref_list = list(REFERENCE_DESCRIPTIONS.keys())
    
    # Sorteia quais partes usarão referências de personagens (pelo menos duas partes)
    body_char = random.choice(ref_list) if random.random() > 0.3 else "none"
    eyes_char = random.choice(ref_list) if random.random() > 0.3 else "none"
    mouth_char = random.choice(ref_list) if random.random() > 0.3 else "none"
    hat_char = random.choice(ref_list) if random.random() > 0.5 else "none"
    acc_char = random.choice(ref_list) if random.random() > 0.5 else "none"
    
    # Garante que pelo menos um é de referência
    if all(c == "none" for c in [body_char, eyes_char, mouth_char, hat_char, acc_char]):
        body_char = random.choice(ref_list)
        eyes_char = random.choice(ref_list)

    body_color = random.choice(BODY_COLORS)
    eyes = random.choice(list(EYE_PROMPTS.keys()))
    mouth = random.choice(list(MOUTH_PROMPTS.keys()))
    hat = random.choice(list(HAT_PROMPTS.keys()))
    accessory = random.choice(list(ACCESSORY_PROMPTS.keys()))
    theme = random.choice(list(THEME_EXTRA.keys()))
    
    # Monta tags explicativas para o captioning
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

def process_and_save_image(raw_img_path: Path, output_img_path: Path, size=512):
    """
    Centraliza a imagem de entrada e redimensiona para size x size em fundo branco sólido.
    """
    img = Image.open(raw_img_path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
        
    # Como o fundo gerado é cinza claro sólido, podemos substituí-lo por transparente ou branco.
    # Vamos criar um canvas branco de size x size.
    canvas = Image.new('RGB', (size, size), (255, 255, 255))
    
    # Redimensiona mantendo a proporção
    img.thumbnail((size - 20, size - 20), Image.Resampling.LANCZOS)
    
    # Cola a imagem centralizada (usa o próprio canal alfa de transparência se houver,
    # senão, o ComfyUI gera fundo opaco, então apenas colamos no centro)
    offset = ((size - img.width) // 2, (size - img.height) // 2)
    canvas.paste(img, offset)
    
    canvas.save(output_img_path, 'JPEG', quality=95)
    print(f" -> Imagem processada e salva em: {output_img_path}")

def generate_lora_dataset(count=50):
    print(f"=== Iniciando Geração de Dataset LoRA (Alvo: {count} imagens) ===")
    
    # Cria a lista de OCs
    configs = []
    # Metade pura, metade composta
    for i in range(count // 2):
        configs.append(make_pure_random_oc())
    for i in range(count - (count // 2)):
        configs.append(make_composite_oc())
        
    # Embaralha para alternar os estilos
    random.shuffle(configs)
    
    success_count = 0
    temp_dir = Path("static/generated")
    
    for idx, cfg in enumerate(configs):
        index_str = f"{idx + 1:02d}"
        print(f"\n[{index_str}/{count}] Solicitando OC: {cfg['params']}")
        
        # Faz o POST para gerar
        try:
            resp = requests.post(f"{API_URL}/api/generate_oc", json=cfg["params"], timeout=30)
            if resp.status_code != 200:
                print(f" [!] Erro ao solicitar geração: HTTP {resp.status_code} - {resp.text}")
                continue
            
            job_data = resp.json()
            if job_data.get("status") != "queued":
                print(f" [!] Erro no retorno do job: {job_data}")
                continue
                
            prompt_id = job_data.get("prompt_id")
            print(f" -> Job enfileirado no ComfyUI. Prompt ID: {prompt_id}")
            
            # Polling de status
            start_time = time.time()
            done = False
            error = False
            
            while not done and not error:
                # Evita timeout infinito
                if time.time() - start_time > 300: # 5 minutos max por imagem
                    print(" [!] Timeout de 5 minutos atingido para este job.")
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
                        print(f" -> Concluído! Imagem gerada em {time.time() - start_time:.1f} segundos.")
                    elif status == "error":
                        print(f" [!] Erro no ComfyUI: {status_data.get('error')}")
                        error = True
                    else:
                        print(f"    Status: {status} ({progress}%)", end="\r")
                except Exception as ex:
                    print(f"    [!] Erro de conexão durante polling: {ex}")
                    time.sleep(2)
                    
            if error or not done:
                print(" [!] Pulando para o próximo devido a falha.")
                continue
                
            # Download da imagem
            img_filename = output_url.split("/")[-1]
            local_raw_path = temp_dir / img_filename
            
            # Garante que o arquivo físico existe no disco (o backend copia no polling,
            # mas vamos baixar direto para garantir caso haja problemas de cache)
            img_url = f"{API_URL}{output_url}"
            img_data_resp = requests.get(img_url, timeout=30)
            if img_data_resp.status_code == 200:
                local_raw_path.write_bytes(img_data_resp.content)
            else:
                print(f" [!] Falha ao baixar imagem final de {img_url}")
                continue
                
            # Processa e salva no dataset
            out_img_path = DATASET_DIR / f"sprunki_{index_str}.jpg"
            process_and_save_image(local_raw_path, out_img_path)
            
            # Salva o arquivo de tags .txt
            out_txt_path = DATASET_DIR / f"sprunki_{index_str}.txt"
            out_txt_path.write_text(cfg["tags"], encoding="utf-8")
            print(f" -> Tags salvas em: {out_txt_path} ({cfg['tags']})")
            
            success_count += 1
            
        except Exception as e:
            print(f" [!] Erro inesperado na imagem {index_str}: {e}")
            
    print(f"\n{'='*60}")
    print(f" Processo concluído!")
    print(f" Sprunkis gerados com sucesso: {success_count}/{count}")
    print(f" Pasta do dataset: {DATASET_DIR.absolute()}")
    print(f"{'='*60}\n")

def generate_for_evolution(count=50):
    """
    Versão otimizada para uso com o agente de evolução.
    Gera samples e já os avalia, retornando os melhores.
    """
    results = generate_lora_dataset(count)
    
    evaluated = []
    for img_path in DATASET_DIR.glob("sprunki_*.jpg"):
        txt_path = img_path.with_suffix('.txt')
        if txt_path.exists():
            tags = txt_path.read_text()
            eval_results = evaluate_sprunki(
                image_path=str(img_path),
                prompt=tags,
                reference_dir=str(REFERENCIAS_DIR)
            )
            evaluated.append({
                "image": str(img_path),
                "tags": tags,
                "score": eval_results["total_score"],
                "details": eval_results
            })
    
    evaluated.sort(key=lambda x: x["score"], reverse=True)
    
    return evaluated


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerador de samples LoRA Sprunki")
    parser.add_argument("count", type=int, nargs="?", default=50, help="Quantidade de samples")
    parser.add_argument("--evolution", action="store_true", help="Modo para agente de evolução")
    
    args = parser.parse_args()
    
    if args.evolution:
        print("\n=== MODO EVOLUÇÃO ===")
        results = generate_for_evolution(args.count)
        print(f"\nTop 10 Sprunkis:")
        for i, r in enumerate(results[:10], 1):
            print(f"  {i}. Score {r['score']:.2f} — {r['image']}")
        print()
    else:
        generate_lora_dataset(args.count)
