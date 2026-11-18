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

DEFAULT_DATASET_DIR = Path("lora_dataset/img/20_sprunki_char")
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


def enforce_gpu_window(name: str = "sprunki-auto-train"):
    guard_root = Path(r"E:\Pemara")
    if str(guard_root) not in sys.path:
        sys.path.insert(0, str(guard_root))
    try:
        from gpu_window_guard import enforce

        enforce(name=name, kind="training")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[GPU-GUARD] Falha ao validar janela GPU; bloqueando por seguranca: {exc}", flush=True)
        raise SystemExit(20)

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
    
    train_script = kohya_path / "sd-scripts" / "flux_train_network.py"
    if train_script.exists():
        return True
    train_script_alt = kohya_path / "sd-scripts" / "train_network.py"
    return train_script_alt.exists()


def print_banner(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


# ─── Treino LoRA ─────────────────────────────────────────────────────────────

def find_encoder_paths(flux_model_path):
    """Retorna caminhos para clip_l, t5xxl e ae."""
    if flux_model_path:
        flux_path = Path(flux_model_path).resolve()
        if flux_path.parent.name == "unet":
            models_dir = flux_path.parent.parent
            clip_l = models_dir / "clip" / "clip_l.safetensors"
            t5xxl = models_dir / "clip" / "t5xxl_fp16.safetensors"
            ae = models_dir / "vae" / "ae.safetensors"
            if clip_l.exists() and t5xxl.exists() and ae.exists():
                return str(clip_l), str(t5xxl), str(ae)
                
    search_roots = [
        Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models"),
        Path(r"C:\ComfyUI\models"),
        Path(r"C:\kohya_ss\models"),
    ]
    for root in search_roots:
        clip_l = root / "clip" / "clip_l.safetensors"
        t5xxl = root / "clip" / "t5xxl_fp16.safetensors"
        ae = root / "vae" / "ae.safetensors"
        if clip_l.exists() and t5xxl.exists() and ae.exists():
            return str(clip_l), str(t5xxl), str(ae)
            
    return None, None, None


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
    clip_l: str = None,
    t5xxl: str = None,
    ae: str = None,
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
        clip_l: Caminho do CLIP-L (auto-detect se None)
        t5xxl: Caminho do T5XXL (auto-detect se None)
        ae: Caminho do VAE ae.safetensors (auto-detect se None)
    """
    
    print_banner("TREINO LoRA SPRUNKI")
    
    # Verificações e resolução de caminhos absolutos
    abs_dataset_dir = Path(dataset_dir).resolve()
    if not abs_dataset_dir.exists():
        print(f"[ERRO] Dataset não encontrado: {dataset_dir}")
        return False
    
    # Se a pasta contiver imagens diretamente, passamos o pai para o Kohya
    has_images = (
        any(abs_dataset_dir.glob("*.png")) or 
        any(abs_dataset_dir.glob("*.jpg")) or 
        any(abs_dataset_dir.glob("*.jpeg")) or 
        any(abs_dataset_dir.glob("*.webp"))
    )
    if has_images:
        kohya_train_data_dir = abs_dataset_dir.parent
        print(f"-> Pasta contem imagens diretamente. Usando pasta pai para o Kohya: {kohya_train_data_dir}")
    else:
        kohya_train_data_dir = abs_dataset_dir
        print(f"-> Usando pasta de dataset: {kohya_train_data_dir}")

    abs_output_dir = Path(output_dir).resolve()
    if not abs_output_dir.exists():
        abs_output_dir.mkdir(parents=True)
        print(f"-> Criado diretorio: {abs_output_dir}")
    
    kohya_path = Path(kohya_path).resolve()
    if not check_kohya_ss(kohya_path):
        print(f"[ERRO] Kohya SS não encontrado em: {kohya_path}")
        return False
    
    abs_flux_model_path = Path(flux_model_path).resolve()
    if not abs_flux_model_path.exists():
        print(f"[ERRO] Modelo Flux.1 não encontrado em: {abs_flux_model_path}")
        return False
        
    # Auto-detecta encoders se necessário
    if not clip_l or not t5xxl or not ae:
        det_clip_l, det_t5xxl, det_ae = find_encoder_paths(abs_flux_model_path)
        clip_l = clip_l or det_clip_l
        t5xxl = t5xxl or det_t5xxl
        ae = ae or det_ae

    if not clip_l or not Path(clip_l).exists():
        print(f"[ERRO] CLIP-L não encontrado: {clip_l}")
        return False
    if not t5xxl or not Path(t5xxl).exists():
        print(f"[ERRO] T5XXL não encontrado: {t5xxl}")
        return False
    if not ae or not Path(ae).exists():
        print(f"[ERRO] VAE (ae) não encontrado: {ae}")
        return False
        
    print(f"-> CLIP-L detectado: {clip_l}")
    print(f"-> T5XXL detectado: {t5xxl}")
    print(f"-> AE detectado: {ae}")
    
    # Determina o script de treino correto
    sd_scripts_dir = kohya_path / "sd-scripts"
    train_script = sd_scripts_dir / "flux_train_network.py"
    if not train_script.exists():
        train_script = sd_scripts_dir / "train_network.py"

    # Monta comando com caminhos absolutos e otimizações de VRAM
    cmd = [
        sys.executable, str(train_script.resolve()),
        "--pretrained_model_name_or_path", str(abs_flux_model_path),
        "--clip_l", str(Path(clip_l).resolve()),
        "--t5xxl", str(Path(t5xxl).resolve()),
        "--ae", str(Path(ae).resolve()),
        "--train_data_dir", str(kohya_train_data_dir),
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
        "--fp8_base",
        "--cache_text_encoder_outputs",
        "--cache_latents",
        "--gradient_checkpointing",
        "--optimizer_type", "Adafactor",
        "--optimizer_args", "relative_step=False", "scale_parameter=False", "warmup_init=False",
    ]
    
    # Se for fine-tune
    if fine_tune and checkpoint:
        if Path(checkpoint).exists():
            cmd.extend([
                "--v_parameterization",
                "--prior_loss_weight", "0.5",
            ])
            print(f"-> Fine-tune com checkpoint: {checkpoint}")
    
    # Exibe configurações
    print("Configurações:")
    print(f"  Dataset: {kohya_train_data_dir}")
    print(f"  Output: {abs_output_dir}")
    print(f"  Modelo: {abs_flux_model_path}")
    print(f"  Steps: {steps}")
    print(f"  LoRA Dim/Alpha: {dim}/{alpha}")
    print(f"  Batch Size: {batch_size}")
    print(f"  Learning Rate: {learning_rate}")
    print(f"  Seed: {seed}")
    print()
    
    # Executa treino com encoding UTF-8 no ambiente
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    print("Iniciando treino...")
    print(f"  cd {sd_scripts_dir}")
    print(f"  {' '.join(cmd)}\n")
    print("-"*60 + "\n")
    
    result = subprocess.run(
        cmd,
        cwd=sd_scripts_dir,
        env=env,
        capture_output=False
    )
    
    print("\n" + "-"*60)
    
    if result.returncode == 0:
        print("\n[OK] Treino concluido com sucesso!")
        
        # Copia para ComfyUI
        lora_src = abs_output_dir / "sprunki_lora.safetensors"
        comfyui_lora = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\loras\sprunki_lora.safetensors")
        
        if lora_src.exists() and comfyui_lora.parent.exists():
            import shutil
            try:
                shutil.copy2(lora_src, comfyui_lora)
                print(f"[OK] LoRA copiada para ComfyUI: {comfyui_lora}")
            except PermissionError as exc:
                fallback = comfyui_lora.with_name(f"{comfyui_lora.stem}_pending.safetensors")
                shutil.copy2(lora_src, fallback)
                print(f"[AVISO] ComfyUI bloqueou a LoRA ativa: {exc}")
                print(f"[OK] LoRA salva para promocao manual/automatica depois: {fallback}")
        
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
    enforce_gpu_window()
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
        "--clip-l",
        default=None,
        help="Caminho do CLIP-L"
    )
    parser.add_argument(
        "--t5xxl",
        default=None,
        help="Caminho do T5XXL"
    )
    parser.add_argument(
        "--ae",
        default=None,
        help="Caminho do VAE (ae.safetensors)"
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
            clip_l=args.clip_l,
            t5xxl=args.t5xxl,
            ae=args.ae,
        )
        
        if result:
            print("\n[OK] Treino concluido!")
        else:
            print("\n[ERRO] Treino falhou")
            sys.exit(1)


if __name__ == "__main__":
    main()
