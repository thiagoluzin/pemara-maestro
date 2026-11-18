"""
agent_evolution.py
Agente de evolução automática do LoRA Sprunki.

Ciclo de evolução:
1. Gera N Sprunkis via OC Maker
2. Avalia cada um com quality_evaluator
3. Seleciona top-K melhores
4. Adiciona ao dataset LoRA
5. Retreina LoRA
6. Repete até atingir threshold de qualidade

Uso:
    python agent_evolution.py --generations 10 --top-k 5 --target-score 85
"""

import os
import sys
import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from quality_evaluator import evaluate_sprunki
from prompt_builder import (
    EYE_PROMPTS, MOUTH_PROMPTS, HAT_PROMPTS,
    ACCESSORY_PROMPTS, THEME_EXTRA, REFERENCE_DESCRIPTIONS
)

API_URL = "http://localhost:5005"
DATASET_DIR = Path("lora_dataset/img/20_sprunki_char")
REFERENCIAS_DIR = Path("static/referencias")
MODEL_OUTPUT_DIR = Path("lora_dataset/model")

BODY_COLORS = [
    "red", "blue", "green", "yellow", "purple", "pink", "orange",
    "cyan", "brown", "black", "white", "gray", "pastel blue",
    "vibrant red", "neon yellow", "coral", "indigo", "lime green",
    "magenta", "teal", "gold", "silver", "dark purple", "pastel pink"
]


def generate_random_oc_config():
    """Gera configuração aleatória de OC Sprunki."""
    body_color = random.choice(BODY_COLORS)
    eyes = random.choice(list(EYE_PROMPTS.keys()))
    mouth = random.choice(list(MOUTH_PROMPTS.keys()))
    hat = random.choice(list(HAT_PROMPTS.keys()))
    accessory = random.choice(list(ACCESSORY_PROMPTS.keys()))
    theme = random.choice(list(THEME_EXTRA.keys()))
    
    extra_desc = "high quality illustration, clean outlines, flat vector design"
    
    return {
        "body_color": body_color,
        "eyes": eyes,
        "mouth": mouth,
        "hat": hat,
        "accessory": accessory,
        "theme": theme,
        "extra_desc": extra_desc,
        "body_character": "none",
        "eyes_character": "none",
        "mouth_character": "none",
        "hat_character": "none",
        "accessory_character": "none"
    }


def generate_oc_and_wait(params, timeout=300):
    """
    Envia pedido de geração e aguarda conclusão.
    Retorna caminho da imagem gerada ou None se falhar.
    """
    try:
        resp = requests.post(f"{API_URL}/api/generate_oc", json=params, timeout=30)
        if resp.status_code != 200:
            print(f"  [ERRO] HTTP {resp.status_code}")
            return None
        
        job_data = resp.json()
        if job_data.get("status") != "queued":
            print(f"  [ERRO] Job não enfileirado: {job_data}")
            return None
        
        prompt_id = job_data.get("prompt_id")
        print(f"  → Job enfileirado: {prompt_id}")
        
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(3)
            
            status_resp = requests.get(f"{API_URL}/api/status/{prompt_id}", timeout=10)
            if status_resp.status_code != 200:
                continue
            
            status_data = status_resp.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            
            if status == "done":
                output_url = status_data.get("output")
                return f"{API_URL}{output_url}"
            elif status == "error":
                print(f"  [ERRO] Geração falhou: {status_data.get('error')}")
                return None
            else:
                print(f"    Gerando... {progress}%", end="\r")
        
        print(f"  [ERRO] Timeout")
        return None
        
    except Exception as e:
        print(f"  [ERRO] {e}")
        return None


def train_lora(dataset_dir: str, output_dir: str, steps: int = 1000, kohya_path: str = None):
    """
    Treina LoRA usando kohya_ss.
    Retorna True se sucesso, False se falha.
    """
    import subprocess
    
    if kohya_path is None:
        kohya_path = "tools/kohya_ss"

    
    if not Path(kohya_path).exists():
        print(f"  [AVISO] Kohya_ss não encontrado em {kohya_path}")
        print(f"          Treino LoRA pulado.")
        return False
    
    cmd = [
        sys.executable, "sd-scripts/flux_train_network.py",
        "--pretrained_model_name_or_path", "flux1-dev.safetensors",
        "--train_data_dir", str(dataset_dir),
        "--output_dir", str(output_dir),
        "--output_name", "sprunki_lora",
        "--network_module", "networks.lora_flux",
        "--network_dim", "16",
        "--network_alpha", "16",
        "--max_train_steps", str(steps),
        "--learning_rate", "1e-4",
        "--resolution", "512,512",
        "--train_batch_size", "2",
        "--mixed_precision", "bf16",
    ]
    
    print(f"  → Iniciando treino LoRA ({steps} steps)...")
    result = subprocess.run(
        cmd, 
        cwd=kohya_path,
        capture_output=False
    )
    
    return result.returncode == 0


def evolution_cycle(
    num_generations: int = 10,
    top_k: int = 5,
    target_score: float = 85.0,
    max_epochs: int = 20,
    dry_run: bool = False,
    kohya_path: str = None
):
    """
    Executa ciclo de evolução automática.
    """
    print("\n" + "="*60)
    print("  AGENTE DE EVOLUÇÃO SPRUNKI")
    print("="*60 + "\n")
    
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    epoch = 0
    best_score = 0.0
    consecutive_improvements = 0
    best_sprunkis = []
    
    while epoch < max_epochs:
        epoch += 1
        print(f"\n{'─'*60}")
        print(f"  EPOCH {epoch}/{max_epochs}")
        print(f"{'─'*60}\n")
        
        print(f"[1/4] Gerando {num_generations} Sprunkis...")
        generated = []
        
        for i in range(num_generations):
            print(f"\n  [{i+1}/{num_generations}]")
            params = generate_random_oc_config()
            image_url = generate_oc_and_wait(params)
            
            if image_url:
                temp_path = Path(f"temp_sprunki_{i}.png")
                try:
                    img_resp = requests.get(image_url, timeout=30)
                    temp_path.write_bytes(img_resp.content)
                    
                    eval_results = evaluate_sprunki(
                        image_path=str(temp_path),
                        reference_dir=str(REFERENCIAS_DIR)
                    )
                    
                    generated.append({
                        "path": str(temp_path),
                        "url": image_url,
                        "params": params,
                        "score": eval_results["total_score"],
                        "details": eval_results
                    })
                    
                    print(f"  → Score: {eval_results['total_score']:.2f}")
                except Exception as e:
                    print(f"  [ERRO] {e}")
        
        if not generated:
            print(f"  [ERRO] Nenhuma imagem gerada nesta epoch")
            break
        
        print(f"\n[2/4] Selecionando top-{top_k} melhores...")
        generated.sort(key=lambda x: x["score"], reverse=True)
        top_sprunkis = generated[:top_k]
        
        print(f"  Melhores scores:")
        for spr in top_sprunkis:
            print(f"    {spr['score']:.2f} — {spr['params']['body_color']} {spr['params']['eyes']} {spr['params']['mouth']}")
        
        current_best = top_sprunkis[0]["score"]
        if current_best > best_score:
            best_score = current_best
            consecutive_improvements += 1
        else:
            consecutive_improvements = 0
        
        print(f"\n[3/4] Verificando target...")
        print(f"  Melhor score: {best_score:.2f} | Target: {target_score:.2f}")
        print(f"  Melhor histórico: {best_sprunkis[-1]['score']:.2f}" if best_sprunkis else "")
        
        if best_score >= target_score:
            print(f"\n  ✓ TARGET ALCANÇADO! Sprunkis perfeitos gerados.")
            best_sprunkis = top_sprunkis
            break
        
        if consecutive_improvements >= 5:
            print(f"\n  ✓ Estabilidade atingida após 5 ciclos de melhoria.")
            break
        
        if not dry_run:
            print(f"\n[4/4] Retreinando LoRA...")
            
            for idx, spr in enumerate(top_sprunkis):
                dest = DATASET_DIR / f"evolved_{epoch}_{idx:02d}.jpg"
                try:
                    img = Path(spr["path"])
                    if img.exists():
                        import shutil
                        shutil.copy2(img, dest)
                        print(f"  → Adicionado: {dest.name}")
                except Exception as e:
                    print(f"  [ERRO] Falha ao adicionar {spr['path']}: {e}")
            
            success = train_lora(
                dataset_dir=str(DATASET_DIR),
                output_dir=str(MODEL_OUTPUT_DIR),
                steps=1000,
                kohya_path=kohya_path
            )
            
            if success:
                print(f"  ✓ LoRA retreinada com sucesso!")
                
                best_sprunkis.extend(top_sprunkis)
            else:
                print(f"  [AVISO] Treino falhou ou não configurado. Continuando sem retreino.")
                best_sprunkis.extend(top_sprunkis)
        else:
            print(f"\n[4/4] DRY RUN — Pulando treino LoRA")
            best_sprunkis.extend(top_sprunkis)
        
        print(f"\n  Aguardando 5s antes da próxima epoch...")
        time.sleep(5)
    
    print("\n" + "="*60)
    print("  RESUMO FINAL")
    print("="*60)
    print(f"  Epochs executadas: {epoch}")
    print(f"  Melhor score: {best_score:.2f}")
    print(f"  Target: {target_score:.2f}")
    print(f"  Sprunkis gerados: {len(best_sprunkis)}")
    print(f"  Status: {'✓ SUCESSO' if best_score >= target_score else '○ INCOMPLETO'}")
    print("="*60)
    
    if best_sprunkis:
        print(f"\n  TOP 5 SPRUNKIS:")
        best_sprunkis.sort(key=lambda x: x["score"], reverse=True)
        for i, spr in enumerate(best_sprunkis[:5], 1):
            print(f"    {i}. Score {spr['score']:.2f} — {spr['params']['body_color']}")
            print(f"       {spr['params']['eyes']} eyes, {spr['params']['mouth']} mouth")
            print(f"       {spr['params']['hat']}, {spr['params']['accessory']}")
    
    print()
    
    return {
        "epochs": epoch,
        "best_score": best_score,
        "target_score": target_score,
        "success": best_score >= target_score,
        "best_sprunkis": best_sprunkis
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agente de evolução LoRA Sprunki")
    parser.add_argument("--generations", type=int, default=10, help="Sprunkis por epoch")
    parser.add_argument("--top-k", type=int, default=5, help="Melhores para dataset")
    parser.add_argument("--target-score", type=float, default=85.0, help="Score alvo")
    parser.add_argument("--max-epochs", type=int, default=20, help="Máximo de ciclos")
    parser.add_argument("--dry-run", action="store_true", help="Só gera, não treina")
    parser.add_argument("--kohya-path", type=str, default=None, help="Caminho do kohya_ss")
    
    args = parser.parse_args()
    
    evolution_cycle(
        num_generations=args.generations,
        top_k=args.top_k,
        target_score=args.target_score,
        max_epochs=args.max_epochs,
        dry_run=args.dry_run,
        kohya_path=args.kohya_path
    )