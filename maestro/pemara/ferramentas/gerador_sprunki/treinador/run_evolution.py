"""
run_evolution.py
Script principal de automação completa do Agente de Evolução Sprunki.

Rodando este script, você inicia o ciclo completo de evolução automática:
1. Verifica pré-requisitos
2. Gera dataset inicial (se necessário)
3. Treina LoRA base (se necessário)
4. Inicia evolução automática
5. Monitora progresso e salva resultados

Uso:
    python run_evolution.py
    python run_evolution.py --target-score 85 --max-epochs 20
    python run_evolution.py --dry-run  # teste sem treinar
"""

import os
import sys
import io

# FIX: UTF-8 no console Windows (evita UnicodeEncodeError com simbolos)
# Usa reconfigure() que mantém o unbuffered mode necessário para logs em tempo real
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass  # Python < 3.7 fallback

import json
import time
import shutil
import subprocess
import requests
from pathlib import Path
from datetime import datetime

# ─── Paths absolutos (executável de qualquer diretório) ─────────────────────
# Raiz da pasta treinador/
TRAINER_DIR = Path(__file__).parent.resolve()
# Raiz da pasta gerador_sprunki/
PROJECT_ROOT = TRAINER_DIR.parent.resolve()

# Adiciona os dois diretórios ao sys.path
sys.path.insert(0, str(TRAINER_DIR))   # quality_evaluator.py
sys.path.insert(0, str(PROJECT_ROOT))  # prompt_builder.py

# Muda o CWD para PROJECT_ROOT para que paths relativos funcionem em sub-módulos
os.chdir(str(PROJECT_ROOT))

from quality_evaluator import evaluate_sprunki
from prompt_builder import (
    EYE_PROMPTS, MOUTH_PROMPTS, HAT_PROMPTS,
    ACCESSORY_PROMPTS, THEME_EXTRA, REFERENCE_DESCRIPTIONS
)
import random

# ─── Configurações Globais ───────────────────────────────────────────────────

API_URL = "http://localhost:5005"
COMFYUI_URL = "http://localhost:8188"
DATASET_BASE_DIR = PROJECT_ROOT / "lora_dataset"
DATASET_DIR = DATASET_BASE_DIR / "img" / "20_sprunki_char"
MODEL_OUTPUT_DIR = DATASET_BASE_DIR / "model"
REFERENCIAS_DIR = PROJECT_ROOT / "static" / "referencias"
TEMP_DIR = PROJECT_ROOT / "temp_evolution"

# Configurações do Kohya SS
KOHYA_PATH = PROJECT_ROOT / "tools" / "kohya_ss"
FLUX_MODEL_PATH = PROJECT_ROOT / "flux1-dev.safetensors"

# Configurações de evolução
DEFAULT_TARGET_SCORE = 85.0
DEFAULT_MAX_EPOCHS = 20
DEFAULT_GENERATIONS_PER_EPOCH = 15
DEFAULT_TOP_K = 5


# ─── Verificações de Pré-requisitos ──────────────────────────────────────────

def check_comfyui():
    """Verifica se ComfyUI está rodando."""
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        if resp.status_code == 200:
            print("  ✓ ComfyUI está rodando")
            return True
    except:
        pass
    print("  ✗ ComfyUI não detectado em", COMFYUI_URL)
    print("  → Inicie ComfyUI antes de continuar:")
    print("    cd ComfyUI && python main.py")
    return False


def check_flask_api():
    """Verifica se a API Flask está rodando."""
    try:
        resp = requests.get(f"{API_URL}/", timeout=5)
        if resp.status_code == 200:
            print("  ✓ API Flask está rodando")
            return True
    except:
        pass
    print("  ✗ API Flask não detectada em", API_URL)
    print("  → Inicie o servidor antes de continuar:")
    print("    python app.py")
    return False


def check_kohya_ss():
    """Verifica se Kohya SS está configurado."""
    if not KOHYA_PATH.exists():
        print(f"  ✗ Kohya SS não encontrado em {KOHYA_PATH}")
        return False
    
    # Preferir script específico de Flux, mas aceita train_network.py como fallback
    train_script = KOHYA_PATH / "sd-scripts" / "flux_train_network.py"
    if not train_script.exists():
        train_script = KOHYA_PATH / "sd-scripts" / "train_network.py"
    if not train_script.exists():
        print(f"  ✗ Nenhum script de treinamento encontrado em {KOHYA_PATH / 'sd-scripts'}")
        return False
    
    print(f"  ✓ Kohya SS encontrado em {KOHYA_PATH}")
    return True


def check_flux_model():
    """Verifica se o modelo Flux.1-dev está disponível."""
    # Procura em vários locais
    search_paths = [
        Path(r"E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\unet\\flux1-dev.safetensors"),
        FLUX_MODEL_PATH,
        Path(r"C:\\AI\\models\\flux1-dev.safetensors"),
        Path(r"C:\\ComfyUI\\models\\unet\\flux1-dev.safetensors"),
    ]
    
    for path in search_paths:
        if path.exists():
            print(f"  ✓ Modelo Flux.1 encontrado: {path}")
            return str(path)
    
    print("  ✗ Modelo Flux.1-dev não encontrado")
    return None


def check_existing_lora():
    """Verifica se já existe uma LoRA treinada."""
    lora_paths = [
        Path(r"E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\loras\\sprunki_lora.safetensors"),
        MODEL_OUTPUT_DIR / "sprunki_lora.safetensors",
    ]
    
    for path in lora_paths:
        if path.exists():
            print(f"  ✓ LoRA existente encontrada: {path}")
            return str(path)
    
    print("  ⚠ Nenhuma LoRA existente encontrada")
    return None


# ─── Geração de Dataset Inicial ──────────────────────────────────────────────

def generate_initial_dataset(count=50):
    """Gera dataset inicial de samples sintéticos."""
    print(f"\n{'='*60}")
    print(f"  GERANDO DATASET INICIAL ({count} samples)")
    print(f"{'='*60}\n")
    
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    
    BODY_COLORS = [
        "red", "blue", "green", "yellow", "purple", "pink", "orange",
        "cyan", "brown", "black", "white", "gray", "pastel blue",
        "vibrant red", "neon yellow", "coral", "indigo"
    ]
    
    generated = []
    
    for i in range(count):
        print(f"[{i+1}/{count}] Gerando sample...")
        
        params = {
            "body_color": random.choice(BODY_COLORS),
            "eyes": random.choice(list(EYE_PROMPTS.keys())),
            "mouth": random.choice(list(MOUTH_PROMPTS.keys())),
            "hat": random.choice(list(HAT_PROMPTS.keys())),
            "accessory": random.choice(list(ACCESSORY_PROMPTS.keys())),
            "theme": random.choice(list(THEME_EXTRA.keys())),
            "extra_desc": "high quality illustration, clean outlines, flat vector design",
            "body_character": "none",
            "eyes_character": "none",
            "mouth_character": "none",
            "hat_character": "none",
            "accessory_character": "none"
        }
        
        try:
            resp = requests.post(f"{API_URL}/api/generate_oc", json=params, timeout=30)
            if resp.status_code != 200:
                print(f"  [ERRO] HTTP {resp.status_code}")
                continue
            
            job_data = resp.json()
            prompt_id = job_data.get("prompt_id")
            
            # Polling
            start = time.time()
            while time.time() - start < 300:
                time.sleep(3)
                status_resp = requests.get(f"{API_URL}/api/status/{prompt_id}", timeout=10)
                if status_resp.status_code != 200:
                    continue
                
                status = status_resp.json().get("status")
                if status == "done":
                    output_url = status_resp.json().get("output")
                    
                    # Salva imagem
                    img_resp = requests.get(f"{API_URL}{output_url}", timeout=30)
                    img_path = DATASET_DIR / f"initial_{i:03d}.jpg"
                    img_path.write_bytes(img_resp.content)
                    
                    # Cria caption
                    caption = f"sprunki_char, {params['body_color']} skin, {params['eyes']} eyes, {params['mouth']} mouth"
                    caption_path = DATASET_DIR / f"initial_{i:03d}.txt"
                    caption_path.write_text(caption)
                    
                    generated.append(str(img_path))
                    print(f"  → Salvo: {img_path.name}")
                    break
                elif status == "error":
                    print(f"  [ERRO] Geração falhou")
                    break
            else:
                print(f"  [ERRO] Timeout")
        
        except Exception as e:
            print(f"  [ERRO] {e}")
    
    print(f"\n  Dataset inicial gerado: {len(generated)} imagens")
    return generated


# ─── Treino LoRA Base ────────────────────────────────────────────────────────

def train_base_lora(dataset_dir: str, flux_model_path: str, kohya_path: str):
    """Treina LoRA base do zero."""
    print(f"\n{'='*60}")
    print(f"  TREINANDO LoRA BASE")
    print(f"{'='*60}\n")
    
    if not check_kohya_ss():
        print("  [SKIP] Kohya SS não configurado. Pule esta etapa.")
        return False
    
    if not flux_model_path:
        print("  [SKIP] Modelo Flux.1 não encontrado. Pule esta etapa.")
        return False
    
    output_dir = MODEL_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable, "sd-scripts/flux_train_network.py",
        "--pretrained_model_name_or_path", flux_model_path,
        "--train_data_dir", str(dataset_dir),
        "--output_dir", str(output_dir),
        "--output_name", "sprunki_lora",
        "--network_module", "networks.lora_flux",
        "--network_dim", "16",
        "--network_alpha", "16",
        "--max_train_steps", "1500",
        "--learning_rate", "1e-4",
        "--resolution", "512,512",
        "--train_batch_size", "2",
        "--mixed_precision", "bf16",
        "--seed", "42",
        "--save_every_n_epochs", "5",
    ]
    
    print(f"  Comando:")
    print(f"    cd {kohya_path}")
    print(f"    {' '.join(cmd)}\n")
    
    print("  Iniciando treino... (isso pode levar 20-30 minutos)")
    result = subprocess.run(
        cmd,
        cwd=kohya_path,
        capture_output=False
    )
    
    if result.returncode == 0:
        print(f"  ✓ Treino concluído com sucesso!")
        
        # Copia LoRA para ComfyUI
        lora_src = output_dir / "sprunki_lora.safetensors"
        lora_dst = Path("ComfyUI/models/loras/sprunki_lora.safetensors")
        
        if lora_src.exists() and lora_dst.parent.exists():
            shutil.copy2(lora_src, lora_dst)
            print(f"  ✓ LoRA copiada para ComfyUI")
        
        return True
    else:
        print(f"  [ERRO] Treino falhou")
        return False


# ─── Evolução Automática ─────────────────────────────────────────────────────

def generate_random_oc_config():
    """Gera configuração aleatória de OC Sprunki."""
    body_color = random.choice([
        "red", "blue", "green", "yellow", "purple", "pink", "orange",
        "cyan", "brown", "black", "white", "gray", "pastel blue",
        "vibrant red", "neon yellow", "coral", "indigo", "lime green"
    ])
    
    return {
        "body_color": body_color,
        "eyes": random.choice(list(EYE_PROMPTS.keys())),
        "mouth": random.choice(list(MOUTH_PROMPTS.keys())),
        "hat": random.choice(list(HAT_PROMPTS.keys())),
        "accessory": random.choice(list(ACCESSORY_PROMPTS.keys())),
        "theme": random.choice(list(THEME_EXTRA.keys())),
        "extra_desc": "high quality illustration, clean outlines, flat vector design",
        "body_character": "none",
        "eyes_character": "none",
        "mouth_character": "none",
        "hat_character": "none",
        "accessory_character": "none"
    }


def generate_and_evaluate(num_generations, temp_dir):
    """Gera e avalia Sprunkis, retorna lista com scores."""
    generated = []
    
    for i in range(num_generations):
        print(f"\n  [{i+1}/{num_generations}]")
        
        params = generate_random_oc_config()
        
        try:
            resp = requests.post(f"{API_URL}/api/generate_oc", json=params, timeout=30)
            if resp.status_code != 200:
                print(f"  [ERRO] HTTP {resp.status_code}")
                continue
            
            job_data = resp.json()
            prompt_id = job_data.get("prompt_id")
            
            # Polling
            start = time.time()
            while time.time() - start < 300:
                time.sleep(3)
                status_resp = requests.get(f"{API_URL}/api/status/{prompt_id}", timeout=10)
                if status_resp.status_code != 200:
                    continue
                
                status = status_resp.json().get("status")
                progress = status_resp.json().get("progress", 0)
                
                if status == "done":
                    output_url = status_resp.json().get("output")
                    
                    # Salva temporariamente
                    temp_path = temp_dir / f"temp_{i}.png"
                    img_resp = requests.get(f"{API_URL}{output_url}", timeout=30)
                    temp_path.write_bytes(img_resp.content)
                    
                    # Avalia
                    eval_results = evaluate_sprunki(
                        image_path=str(temp_path),
                        reference_dir=str(REFERENCIAS_DIR)
                    )
                    
                    generated.append({
                        "path": str(temp_path),
                        "url": f"{API_URL}{output_url}",
                        "params": params,
                        "score": eval_results["total_score"],
                        "details": eval_results
                    })
                    
                    print(f"  → Score: {eval_results['total_score']:.2f}")
                    break
                elif status == "error":
                    print(f"  [ERRO] Geração falhou")
                    break
            else:
                print(f"  [ERRO] Timeout")
        
        except Exception as e:
            print(f"  [ERRO] {e}")
    
    return generated


def evolution_loop(
    target_score=DEFAULT_TARGET_SCORE,
    max_epochs=DEFAULT_MAX_EPOCHS,
    generations_per_epoch=DEFAULT_GENERATIONS_PER_EPOCH,
    top_k=DEFAULT_TOP_K,
    dry_run=False,
    flux_model_path=None,
    kohya_path=None
):
    """Loop principal de evolução automática."""
    
    print("\n" + "="*70)
    print("  AGENTE DE EVOLUÇÃO SPRUNKI - INICIANDO")
    print("="*70)
    print(f"  Target Score: {target_score}")
    print(f"  Máximo Epochs: {max_epochs}")
    print(f"  Gerações/Epoch: {generations_per_epoch}")
    print(f"  Top-K: {top_k}")
    print(f"  Dry Run: {dry_run}")
    print("="*70 + "\n")
    
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    
    epoch = 0
    best_score = 0.0
    best_sprunkis = []
    history = []
    
    while epoch < max_epochs:
        epoch += 1
        
        print(f"\n{'─'*70}")
        print(f"  EPOCH {epoch}/{max_epochs}")
        print(f"{'─'*70}\n")
        
        # 1. Gerar e avaliar
        print(f"[1/4] Gerando {generations_per_epoch} Sprunkis...")
        generated = generate_and_evaluate(generations_per_epoch, TEMP_DIR)
        
        if not generated:
            print(f"  [ERRO] Nenhuma imagem gerada")
            break
        
        # 2. Selecionar melhores
        print(f"\n[2/4] Selecionando top-{top_k}...")
        generated.sort(key=lambda x: x["score"], reverse=True)
        top_sprunkis = generated[:top_k]
        
        print(f"  Melhores:")
        for spr in top_sprunkis:
            print(f"    {spr['score']:.2f} — {spr['params']['body_color']} {spr['params']['eyes']}")
        
        current_best = top_sprunkis[0]["score"]
        
        if current_best > best_score:
            best_score = current_best
            best_sprunkis = top_sprunkis.copy()
        
        history.append({
            "epoch": epoch,
            "best_score": current_best,
            "best_overall": best_score,
            "generated_count": len(generated)
        })
        
        # 3. Verificar target
        print(f"\n[3/4] Verificando target...")
        print(f"  Melhor epoch: {current_best:.2f} | Melhor histórico: {best_score:.2f} | Target: {target_score}")
        
        if best_score >= target_score:
            print(f"\n  ✓✓✓ TARGET ALCANÇADO! Sprunkis perfeitos! ✓✓✓")
            break
        
        # 4. Treinar (se não for dry_run)
        if not dry_run:
            print(f"\n[4/4] Retreinando LoRA...")
            
            # Adiciona ao dataset
            for idx, spr in enumerate(top_sprunkis):
                dest = DATASET_DIR / f"evolved_{epoch}_{idx:02d}.jpg"
                try:
                    shutil.copy2(spr["path"], dest)
                    
                    # Cria caption
                    caption = f"sprunki_char, {spr['params']['body_color']} skin, {spr['params']['eyes']} eyes, {spr['params']['mouth']} mouth"
                    caption_path = DATASET_DIR / f"evolved_{epoch}_{idx:02d}.txt"
                    caption_path.write_text(caption)
                    
                    print(f"  → Adicionado: {dest.name}")
                except Exception as e:
                    print(f"  [ERRO] {e}")
            
            # Treina LoRA
            if flux_model_path and kohya_path and check_kohya_ss():
                print(f"\n  Iniciando fine-tuning LoRA...")
                
                cmd = [
                    sys.executable, "train_network.py",
                    "--pretrained_model_name_or_path", flux_model_path,
                    "--train_data_dir", str(DATASET_DIR),
                    "--output_dir", str(MODEL_OUTPUT_DIR),
                    "--output_name", "sprunki_lora",
                    "--network_module", "networks.lora_flux",
                    "--network_dim", "16",
                    "--network_alpha", "16",
                    "--max_train_steps", "1000",
                    "--learning_rate", "1e-4",
                    "--resolution", "512,512",
                    "--train_batch_size", "2",
                    "--mixed_precision", "bf16",
                    "--seed", "42",
                ]
                
                result = subprocess.run(cmd, cwd=kohya_path, capture_output=True)
                
                if result.returncode == 0:
                    print(f"  ✓ Fine-tuning concluído!")
                    
                    # Copia para ComfyUI
                    lora_src = MODEL_OUTPUT_DIR / "sprunki_lora.safetensors"
                    lora_dst = Path(r"E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\loras\\sprunki_lora.safetensors")
                    if lora_src.exists() and lora_dst.parent.exists():
                        shutil.copy2(lora_src, lora_dst)
                        print(f"  ✓ LoRA atualizada no ComfyUI")
                else:
                    print(f"  [AVISO] Fine-tuning falhou, continuando...")
            else:
                print(f"  [AVISO] Kohya SS não configurado, pulando treino")
        else:
            print(f"\n[4/4] DRY RUN — pulando treino")
        
        # Pausa
        print(f"\n  Aguardando 5s...")
        time.sleep(5)
    
    # Resumo final
    print("\n" + "="*70)
    print("  RESUMO FINAL DA EVOLUÇÃO")
    print("="*70)
    print(f"  Epochs executadas: {epoch}")
    print(f"  Melhor score: {best_score:.2f}")
    print(f"  Target: {target_score}")
    print(f"  Status: {'✓ SUCESSO' if best_score >= target_score else '○ INCOMPLETO'}")
    print(f"  Sprunkis perfeitos: {len(best_sprunkis)}")
    print("="*70)
    
    # Salva histórico
    history_path = Path("evolution_history.json")
    with open(history_path, "w") as f:
        json.dump({
            "history": history,
            "best_score": best_score,
            "target_score": target_score,
            "success": best_score >= target_score,
            "best_sprunkis": [
                {
                    "score": s["score"],
                    "params": s["params"]
                }
                for s in best_sprunkis
            ]
        }, f, indent=2)
    print(f"\n  Histórico salvo: {history_path}")
    
    # Top 5 Sprunkis
    if best_sprunkis:
        print(f"\n  TOP 5 SPRUNKIS PERFEITOS:")
        best_sprunkis.sort(key=lambda x: x["score"], reverse=True)
        for i, spr in enumerate(best_sprunkis[:5], 1):
            print(f"\n    {i}. Score {spr['score']:.2f}")
            print(f"       Cor: {spr['params']['body_color']}")
            print(f"       Olhos: {spr['params']['eyes']}")
            print(f"       Boca: {spr['params']['mouth']}")
            print(f"       Chapéu: {spr['params']['hat']}")
            print(f"       Acessório: {spr['params']['accessory']}")
    
    print()
    
    return {
        "epochs": epoch,
        "best_score": best_score,
        "target_score": target_score,
        "success": best_score >= target_score,
        "best_sprunkis": best_sprunkis,
        "history": history
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Automação completa do Agente de Evolução Sprunki"
    )
    parser.add_argument("--target-score", type=float, default=DEFAULT_TARGET_SCORE,
                        help="Score alvo para Sprunkis perfeitos")
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS,
                        help="Máximo de ciclos de evolução")
    parser.add_argument("--generations", type=int, default=DEFAULT_GENERATIONS_PER_EPOCH,
                        help="Gerações por epoch")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help="Melhores selecionados por epoch")
    parser.add_argument("--dry-run", action="store_true",
                        help="Só gera/avalia, não treina")
    parser.add_argument("--skip-initial-dataset", action="store_true",
                        help="Pula geração de dataset inicial")
    parser.add_argument("--kohya-path", type=str, default=None,
                        help="Caminho do Kohya SS")
    
    args = parser.parse_args()
    
    # Atualiza caminhos se fornecidos
    global KOHYA_PATH
    if args.kohya_path:
        KOHYA_PATH = Path(args.kohya_path)
    
    print("\n" + "="*70)
    print("  AGENTE DE EVOLUÇÃO SPRUNKI - SETUP")
    print("="*70 + "\n")
    
    # 1. Verifica pré-requisitos
    print("1. Verificando pré-requisitos...\n")
    
    comfyui_ok = check_comfyui()
    flask_ok = check_flask_api()
    
    if not comfyui_ok or not flask_ok:
        print("\n  [ERRO] Pré-requisitos não atendidos.")
        print("  Inicie ComfyUI e a API Flask antes de continuar.")
        sys.exit(1)
    
    flux_model = check_flux_model()
    kohya_ok = check_kohya_ss()
    existing_lora = check_existing_lora()
    
    # 2. Gera dataset inicial (se necessário)
    if not args.skip_initial_dataset and not existing_lora:
        generate_initial_dataset(50)
    elif existing_lora:
        print(f"\n  → Usando LoRA existente: {existing_lora}")
    
    # 3. Treina LoRA base (se necessário e possível)
    if not existing_lora and flux_model and kohya_ok and not args.dry_run:
        train_base_lora(str(DATASET_DIR), flux_model, str(KOHYA_PATH))
    
    # 4. Inicia evolução
    result = evolution_loop(
        target_score=args.target_score,
        max_epochs=args.max_epochs,
        generations_per_epoch=args.generations,
        top_k=args.top_k,
        dry_run=args.dry_run,
        flux_model_path=flux_model,
        kohya_path=str(KOHYA_PATH) if kohya_ok else None
    )
    
    # 5. Relatório final
    print("\n" + "="*70)
    if result["success"]:
        print("  ✓✓✓ EVOLUÇÃO CONCLUÍDA COM SUCESSO! ✓✓✓")
        print(f"  Sprunkis perfeitos gerados: {len(result['best_sprunkis'])}")
    else:
        print("  ○ Evolução incompleta (máximo de epochs atingido)")
    print("="*70 + "\n")
    
    return result


if __name__ == "__main__":
    main()