"""
auto_train.py
Script de treino automático LoRA para o Agente de Evolução Sprunki.

Permite treinar/fine-tune LoRA independentemente do agente de evolução.

Uso:
    python auto_train.py
    python auto_train.py --dataset lora_dataset/img/20_sprunki_char --steps 1500
    python auto_train.py --fine-tune --checkpoint path/to/existing_lora.safetensors
"""

import os
import sys
import subprocess
from pathlib import Path

# ─── Configurações ───────────────────────────────────────────────────────────

DEFAULT_DATASET_DIR = Path("lora_dataset/img")
DEFAULT_OUTPUT_DIR = Path("lora_dataset/model")
DEFAULT_KOHYA_PATH = Path("tools/kohya_ss")
DEFAULT_FLUX_MODEL = Path("flux1-dev.safetensors")

# Caminhos alternativos para o modelo
FLUX_MODEL_SEARCH_PATHS = [
    Path(r"E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\unet\\flux1-dev.safetensors"),
    Path(r"C:\\AI\\models\\flux1-dev.safetensors"),
    Path(r"C:\\ComfyUI\\models\\unet\\flux1-dev.safetensors"),
    Path(r"C:\\kohya_ss\\models\\flux1-dev.safetensors"),
    Path("flux1-dev.safetensors"),
]

# ─── Funções de Utilidade ────────────────────────────────────────────────────

def find_flux_model():
    """Procura o modelo Flux.1-dev em vários caminhos."""
    for path in FLUX_MODEL_SEARCH_PATHS:
        if path.exists():
            return str(path.resolve())
    return None


def check_kohya_ss(kohya_path):
    """Verifica se Kohya SS está instalado."""
    if not kohya_path.exists():
        return False
    # Prefer flux_train_network, fallback to train_network
    train_script = kohya_path / "sd-scripts" / "flux_train_network.py"
    if not train_script.exists():
        train_script = kohya_path / "sd-scripts" / "train_network.py"
    return train_script.exists()


def print_banner(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


# ─── Treino LoRA ─────────────────────────────────────────────────────────────

def train_lora(
    dataset_dir: str,
    output_dir: str,
    kohya_path: str,
    flux_model_path: str,
    steps: int = 1500,
    dim: int = 16,
    alpha: int = 16,
    batch_size: int = 2,
    learning_rate: float = 1e-4,
    seed: int = 42,
    fine_tune: bool = False,
    checkpoint: str = None,
):
    """
    Executa treino LoRA usando Kohya SS.
    
    Args:
        dataset_dir: Diretório com imagens e captions
        output_dir: Diretório de saída do modelo
        kohya_path: Caminho da instalação do Kohya SS
        flux_model_path: Caminho do modelo Flux.1-dev
        steps: Número de steps de treino
        dim: Dimensão da LoRA
        alpha: Alpha da LoRA
        batch_size: Batch size de treino
        learning_rate: Taxa de aprendizado
        seed: Seed para reprodutibilidade
        fine_tune: Se True, faz fine-tune em vez de treino do zero
        checkpoint: Caminho de checkpoint para fine-tune
    """
    
    print_banner("TREINO LoRA SPRUNKI")
    
    # Verificações
    if not Path(dataset_dir).exists():
        print(f"[ERRO] Dataset não encontrado: {dataset_dir}")
        return False
    
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True)
        print(f"[OK] Criado diretorio: {output_dir}")
    
    if not check_kohya_ss(Path(kohya_path)):
        print(f"[ERRO] Kohya SS nao encontrado em: {kohya_path}")
        return False
    
    if not flux_model_path or not Path(flux_model_path).exists():
        print(f"[ERRO] Modelo Flux.1 nao encontrado")
        return False
    
    # Determinar script correto
    train_script = "sd-scripts/flux_train_network.py"
    is_flux = True
    if not (Path(kohya_path) / train_script).exists():
        train_script = "sd-scripts/train_network.py"
        is_flux = False
        
    abs_dataset_dir = Path(dataset_dir).resolve()
    abs_output_dir = Path(output_dir).resolve()
        
    # Monta comando
    cmd = [
        sys.executable, train_script,
        "--pretrained_model_name_or_path", flux_model_path,
        "--train_data_dir", str(abs_dataset_dir),
        "--output_dir", str(abs_output_dir),
        "--output_name", "sprunki_lora",
        "--network_module", "networks.lora_flux",
        "--network_dim", str(dim),
        "--network_alpha", str(alpha),
        "--max_train_steps", str(steps),
        "--learning_rate", str(learning_rate),
        "--resolution", "512,512",
        "--train_batch_size", str(batch_size),
        "--mixed_precision", "bf16",
        "--seed", str(seed),
        "--save_every_n_epochs", "5",
        "--min_snr_gamma", "5",
    ]
    
    if is_flux:
        comfy_models = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models")
        clip_l_path = comfy_models / "clip" / "clip_l.safetensors"
        t5xxl_path = comfy_models / "clip" / "t5xxl_fp16.safetensors"
        ae_path = comfy_models / "vae" / "ae.safetensors"
        
        if clip_l_path.exists() and t5xxl_path.exists() and ae_path.exists():
            cmd.extend([
                "--clip_l", str(clip_l_path.resolve()),
                "--t5xxl", str(t5xxl_path.resolve()),
                "--ae", str(ae_path.resolve()),
            ])
            print("[INFO] Adicionados argumentos do modelo Flux (CLIP-L, T5XXL, AE).")
        
        # Otimizacoes para economizar VRAM na RTX 5080 (16GB)
        cmd.extend([
            "--gradient_checkpointing",
            "--cache_text_encoder_outputs",
            "--cache_latents",
            "--optimizer_type", "Adafactor",
            "--fp8_base",
        ])
        print("[INFO] Adicionados argumentos de economia de memoria (Adafactor, gradient checkpointing, caches, FP8 Base).")
    
    # Se for fine-tune
    if fine_tune and checkpoint:
        if Path(checkpoint).exists():
            cmd.extend([
                "--v_parameterization",
                "--prior_loss_weight", "0.5",
            ])
            print(f"[INFO] Fine-tune com checkpoint: {checkpoint}")
    
    # Exibe configurações
    print("Configuracoes:")
    print(f"  Dataset: {dataset_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Modelo: {flux_model_path}")
    print(f"  Steps: {steps}")
    print(f"  LoRA Dim/Alpha: {dim}/{alpha}")
    print(f"  Batch Size: {batch_size}")
    print(f"  Learning Rate: {learning_rate}")
    print(f"  Seed: {seed}")
    print()
    
    # Executa treino
    print("Iniciando treino...")
    
    # Tenta liberar VRAM do ComfyUI antes de treinar
    try:
        import requests
        print("[INFO] Solicitando descarregamento de modelos do ComfyUI para liberar VRAM...")
        free_resp = requests.post("http://localhost:8188/free", json={"unload_models": True}, timeout=5)
        if free_resp.status_code == 200:
            print("[OK] ComfyUI liberou os modelos da VRAM.")
        else:
            print(f"[AVISO] ComfyUI retornou status {free_resp.status_code} ao tentar liberar VRAM.")
    except Exception as e:
        print(f"[AVISO] Nao foi possivel comunicar com ComfyUI para liberar VRAM: {e}")
        
    print(f"  cd {kohya_path}")
    print(f"  {' '.join(cmd)}\n")
    print("-"*60 + "\n")
    
    # Configura variaveis de ambiente para evitar erros de codificacao do console no Windows (cp1252 vs utf-8)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    
    result = subprocess.run(
        cmd,
        cwd=kohya_path,
        capture_output=False,
        env=env
    )
    
    print("\n" + "-"*60)
    
    if result.returncode == 0:
        lora_src = Path(output_dir) / "sprunki_lora.safetensors"
        if not lora_src.exists():
            print(f"[ERRO] Arquivo do modelo treinado nao foi gerado em: {lora_src}")
            return False
            
        print("\n[OK] Treino concluido com sucesso!")
        
        # Copia para ComfyUI
        comfyui_lora = Path(r"E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\loras\\sprunki_lora_v1.safetensors")
        if comfyui_lora.parent.exists():
            import shutil
            try:
                shutil.copy2(lora_src, comfyui_lora)
                print(f"[OK] LoRA copiada para ComfyUI: {comfyui_lora}")
            except Exception as e:
                print(f"[AVISO] Falha ao copiar LoRA para ComfyUI (arquivo travado pelo ComfyUI ou sem permissao): {e}")
                print(f"[INFO] Voce pode copiar manualmente o arquivo {lora_src} para {comfyui_lora} apos fechar o ComfyUI.")
        
        return True
    else:
        print("\n[ERRO] Treino falhou")
        return False


def quick_train():
    """Treino rápido com configurações padrão."""
    print_banner("TREINO RÁPIDO LoRA")
    
    # Procura caminhos
    flux_model = find_flux_model()
    kohya_path = DEFAULT_KOHYA_PATH
    
    if not flux_model:
        print("[ERRO] Modelo Flux.1-dev não encontrado")
        print("Baixe de: https://huggingface.co/black-forest-labs/FLUX.1-dev")
        return False
    
    if not check_kohya_ss(kohya_path):
        print(f"[ERRO] Kohya SS não encontrado em {kohya_path}")
        print("Instale de: https://github.com/bmaltais/kohya_ss")
        return False
    
    # Executa treino
    return train_lora(
        dataset_dir=str(DEFAULT_DATASET_DIR),
        output_dir=str(DEFAULT_OUTPUT_DIR),
        kohya_path=str(kohya_path),
        flux_model_path=flux_model,
        steps=1500,
        dim=16,
        alpha=16,
        batch_size=2,
        learning_rate=1e-4,
        seed=42,
    )


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Treino LoRA Sprunki via Kohya SS"
    )
    
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_DIR),
        help="Diretório do dataset de treino"
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Diretório de saída do modelo"
    )
    parser.add_argument(
        "--kohya-path",
        default=str(DEFAULT_KOHYA_PATH),
        help="Caminho do Kohya SS"
    )
    parser.add_argument(
        "--flux-model",
        default=None,
        help="Caminho do modelo Flux.1-dev (auto-detect se não fornecido)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1500,
        help="Número de steps de treino"
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=16,
        help="Dimensão da LoRA"
    )
    parser.add_argument(
        "--alpha",
        type=int,
        default=16,
        help="Alpha da LoRA"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Batch size"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-4,
        help="Taxa de aprendizado"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed para reprodutibilidade"
    )
    parser.add_argument(
        "--fine-tune",
        action="store_true",
        help="Modo fine-tune"
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Checkpoint para fine-tune"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Treino rápido com configurações padrão"
    )
    
    args = parser.parse_args()
    
    if args.quick:
        quick_train()
    else:
        # Procura modelo Flux se não fornecido
        flux_model = args.flux_model
        if not flux_model:
            flux_model = find_flux_model()
        
        result = train_lora(
            dataset_dir=args.dataset,
            output_dir=args.output,
            kohya_path=args.kohya_path,
            flux_model_path=flux_model,
            steps=args.steps,
            dim=args.dim,
            alpha=args.alpha,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            seed=args.seed,
            fine_tune=args.fine_tune,
            checkpoint=args.checkpoint,
        )
        
        if result:
            print("\n[OK] Treino concluido!")
        else:
            print("\n[ERRO] Treino falhou")
            sys.exit(1)


if __name__ == "__main__":
    main()