"""
setup_evolution.py
Script de setup automático para o Agente de Evolução Sprunki.

Configura tudo o que é necessário para rodar a evolução:
1. Instala dependências Python
2. Clona Kohya SS (se não existir)
3. Cria estrutura de diretórios
4. Verifica modelos necessários

Uso:
    python setup_evolution.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ─── Configurações ───────────────────────────────────────────────────────────

REQUIREMENTS = [
    "flask",
    "flask-cors",
    "requests",
    "websocket-client",
    "numpy",
    "Pillow",
    "scikit-learn",
    "torch",
    "torchvision",
    "transformers",
    "diffusers",
    "accelerate",
    "sentencepiece",
    "protobuf",
]

KOHYA_GITHUB_URL = "https://github.com/bmaltais/kohya_ss"
KOHYA_PATH = Path("tools/kohya_ss")

FLUX_MODEL_URL = "https://huggingface.co/black-forest-labs/FLUX.1-dev"

# ─── Funções de Utilidade ────────────────────────────────────────────────────

def print_banner(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def run_command(cmd, cwd=None, check=True):
    """Executa comando e mostra output em tempo real."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=False,
        text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Comando falhou: {' '.join(cmd)}")
    return result.returncode == 0


def check_python():
    """Verifica versão do Python."""
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("  [ERRO] Python 3.10+ necessário")
        return False
    
    print("  ✓ Versão compatível")
    return True


def install_requirements():
    """Instala dependências Python."""
    print_banner("INSTALANDO DEPENDÊNCIAS")
    
    req_file = Path("requirements.txt")
    if req_file.exists():
        print("  Instalando do requirements.txt...")
        run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("  Instalando pacotes individuais...")
        for pkg in REQUIREMENTS:
            print(f"    {pkg}...")
            run_command([sys.executable, "-m", "pip", "install", pkg])
    
    print("  ✓ Dependências instaladas")


def setup_kohya_ss():
    """Configura Kohya SS."""
    print_banner("CONFIGURANDO KOHYA SS")
    
    if KOHYA_PATH.exists():
        print(f"  Kohya SS já existe em {KOHYA_PATH}")
        
        # Atualiza
        print("  Atualizando...")
        run_command(["git", "pull"], cwd=KOHYA_PATH)
        
        # Instala dependencies
        req_file = KOHYA_PATH / "requirements.txt"
        if req_file.exists():
            print("  Instalando dependencies...")
            run_command([
                sys.executable, "-m", "pip", "install", "-r", str(req_file)
            ])
    else:
        print(f"  Clonando Kohya SS em {KOHYA_PATH}...")
        run_command([
            "git", "clone", KOHYA_GITHUB_URL, str(KOHYA_PATH)
        ])
        
        print("  Instalando dependencies...")
        req_file = KOHYA_PATH / "requirements.txt"
        run_command([
            sys.executable, "-m", "pip", "install", "-r", str(req_file)
        ])
    
    # Inicializa submodules (sd-scripts)
    print("  Inicializando submodules...")
    run_command(["git", "submodule", "update", "--init", "--recursive"], cwd=KOHYA_PATH)
    
    # Instala sd-scripts requirements
    sd_req = KOHYA_PATH / "sd-scripts" / "requirements.txt"
    if sd_req.exists():
        print("  Instalando sd-scripts dependencies...")
        run_command([
            sys.executable, "-m", "pip", "install", "-r", str(sd_req)
        ], cwd=KOHYA_PATH / "sd-scripts")
    
    print(f"  ✓ Kohya SS configurado em {KOHYA_PATH}")


def create_directories():
    """Cria estrutura de diretórios necessária."""
    print_banner("CRIANDO DIRETÓRIOS")
    
    dirs = [
        "lora_dataset/img",
        "lora_dataset/model",
        "lora_dataset/log",
        "static/generated",
        "static/referencias",
        "temp_evolution",
        "organized",
        "sb3_files",
    ]
    
    for d in dirs:
        path = Path(d)
        if not path.exists():
            path.mkdir(parents=True)
            print(f"  → Criado: {d}")
        else:
            print(f"  ✓ Existe: {d}")
    
    print("  ✓ Diretórios prontos")


def check_comfyui():
    """Verifica instalação do ComfyUI."""
    print_banner("VERIFICANDO COMFYUI")
    
    comfyui_path = Path(r"E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI")
    
    if comfyui_path.exists() and (comfyui_path / "main.py").exists():
        print(f"  ✓ ComfyUI encontrado: {comfyui_path}")
        
        # Verifica modelos
        unet = comfyui_path / "models" / "unet" / "flux1-dev.safetensors"
        if unet.exists():
            print(f"  ✓ Flux.1-dev presente")
        else:
            print(f"  ⚠ Flux.1-dev não encontrado em {unet}")
        
        lora_dir = comfyui_path / "models" / "loras"
        lora_dir.mkdir(parents=True, exist_ok=True)
        print(f"  → Pasta LoRA pronta: {lora_dir}")
        
        return True
    
    print("  ⚠ ComfyUI não encontrado")
    return False


def check_nvidia_gpu():
    """Verifica GPU NVIDIA."""
    print_banner("VERIFICANDO GPU NVIDIA")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            
            print(f"  GPU: {gpu_name}")
            print(f"  VRAM: {gpu_memory:.1f}GB")
            
            if gpu_memory >= 8:
                print(f"  ✓ GPU adequada para Flux.1")
                return True
            else:
                print(f"  ⚠ VRAM baixa. Flux.1 recomenda 12GB+")
                return False
        else:
            print(f"  ⚠ CUDA não disponível")
            print(f"    Instale PyTorch com CUDA:")
            print(f"    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128")
            return False
    
    except ImportError:
        print(f"  ⚠ PyTorch não instalado")
        print(f"    Instale:")
        print(f"    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128")
        return False


def create_run_script():
    """Cria script de execução rápida."""
    print_banner("CRIANDO SCRIPTS DE EXECUÇÃO")
    
    # Batch file para Windows
    batch_content = """@echo off
echo ========================================
echo  AGENTE DE EVOLUÇÃO SPRUNKI
echo ========================================
echo.

python run_evolution.py --target-score 85 --max-epochs 20

pause
"""
    
    batch_path = Path("run_evolution.bat")
    with open(batch_path, "w") as f:
        f.write(batch_content)
    
    print(f"  → Criado: {batch_path}")
    
    # Config file
    config_content = """# Configuração do Agente de Evolução

# Caminho do Kohya SS (relativo ao projeto)
KOHYA_PATH=tools\\kohya_ss

# Caminho do modelo Flux.1
FLUX_MODEL_PATH=E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\unet\\flux1-dev.safetensors

# Configurações de evolução
TARGET_SCORE=85
MAX_EPOCHS=20
GENERATIONS_PER_EPOCH=15
TOP_K=5
"""
    
    config_path = Path("evolution_config.ini")
    if not config_path.exists():
        with open(config_path, "w") as f:
            f.write(config_content)
        
        print(f"  → Criado: {config_path}")
    
    print("  ✓ Scripts prontos")


def main():
    print("\n" + "="*60)
    print("  SETUP DO AGENTE DE EVOLUÇÃO SPRUNKI")
    print("="*60)
    
    # 1. Verifica Python
    if not check_python():
        sys.exit(1)
    
    # 2. Verifica GPU
    check_nvidia_gpu()
    
    # 3. Instala dependências
    install_requirements()
    
    # 4. Configura Kohya SS
    setup_kohya_ss()
    
    # 5. Cria diretórios
    create_directories()
    
    # 6. Verifica ComfyUI
    check_comfyui()
    
    # 7. Cria scripts
    create_run_script()
    
    print("\n" + "="*60)
    print("  SETUP CONCLUÍDO!")
    print("="*60)
    print("""
Próximos passos:

1. Baixe o modelo Flux.1-dev (se ainda não tem):
   https://huggingface.co/black-forest-labs/FLUX.1-dev
   Coloque em: E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\unet\\flux1-dev.safetensors

2. Configure o ComfyUI:
   - Coloque flux1-dev.safetensors em: E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\unet\
   - Coloque CLIP models em: E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\clip\
   - Coloque VAE em: E:\\Pemara\\maestro\\pemara\\ferramentas\\ComfyUI\\models\\vae\

3. Inicie os serviços:
   - ComfyUI: cd ComfyUI && python main.py
   - API Flask: python app.py

4. Execute a evolução:
   - run_evolution.bat
   - Ou: python run_evolution.py --target-score 85 --max-epochs 20

Para mais opções, veja EVOLUTION_README.md
""")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()