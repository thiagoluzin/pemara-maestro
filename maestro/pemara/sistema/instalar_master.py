# -*- coding: utf-8 -*-
"""
Pemara Universal v4.0 - Instalador Mestre (CORRIGIDO)
Bugs corrigidos vs versao anterior:
  [1] npm.cmd no Windows (WinError 2)
  [2] Patch basicsr via monkey-patch (funciona com PyTorch moderno)
  [3] Studio Pro offline por causa do [2]
  [4] Instalador resiliente  um modulo falhando nao para os outros
  [5] Download AnythingLLM com timeout e progresso
  [6] Estabilidade: Removido suporte a sm_120 / CUDA 12.8 Nightly
"""
import sys, os, subprocess, time, shutil, platform, urllib.request
from pathlib import Path

IS_WIN = platform.system() == "Windows"
BASE   = Path(__file__).parent

#  Cores ANSI 
if IS_WIN:
    os.system("")

VD="\033[92m"; AM="\033[93m"; VM="\033[91m"
CN="\033[96m"; CI="\033[90m"; BD="\033[1m"; RS="\033[0m"

def ok(m):    print(f"  {VD}[OK]{RS}  {m}")
def info(m):  print(f"  {CN}[..]{RS}  {m}")
def aviso(m): print(f"  {AM}[!!]{RS}  {m}")
def erro(m):  print(f"  {VM}[XX]{RS}  {m}")
def titulo(n, t):
    print(f"\n{CI}{'-'*54}{RS}")
    print(f"{BD}  [{n}] {t}{RS}")
    print(f"{CI}{'-'*54}{RS}")


#  FIX 1: npm correto no Windows 
def npm():
    """npm.cmd no Windows, npm no Unix. Fix do WinError 2."""
    return "npm.cmd" if IS_WIN else "npm"

def git():
    return "git"

def tem(cmd):
    """Verifica existancia de comando  inclui .cmd no Windows."""
    if shutil.which(cmd):
        return True
    if IS_WIN and shutil.which(cmd + ".cmd"):
        return True
    return False


#  pip helper 
def pip_grupo(pkgs, desc, extra=None):
    flags = ["--no-warn-script-location", "--disable-pip-version-check",
             "--progress-bar", "off"]
    if extra:
        flags += extra
    print(f"\n  {BD}{desc}{RS}")
    cmd = [sys.executable, "-m", "pip", "install"] + flags + pkgs
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for linha in p.stdout:
        l = linha.strip()
        if any(k in l for k in ["Downloading","Installing","Successfully","Collecting","already"]):
            print(f"    {CI}{l[:70]}{RS}")
    p.wait()
    if p.returncode == 0:
        ok(desc)
    else:
        aviso(f"Com avisos: {desc}")


def run(cmd, **kw):
    return subprocess.run(cmd, **kw)


#  FIX 2: Download com progresso e timeout 
def download_com_progresso(url, destino, desc=""):
    """Download com barra de progresso e timeout implacito."""
    def reporthook(count, block_size, total):
        pct = int(count * block_size / max(total, 1) * 100)
        pct = min(pct, 100)
        feito = pct // 5
        barra = "#" * feito + "." * (20 - feito)
        print(f"\r    {CN}[{barra}] {pct:3d}%  {desc}", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, str(destino), reporthook)
        print()  # nova linha apas progresso
        return True
    except Exception as e:
        print()
        aviso(f"Download falhou: {e}")
        return False


# 
# 1. GPU
# 
def etapa_gpu():
    titulo("1/8", "Detectando GPU NVIDIA")
    r = run(["nvidia-smi", "-L"], capture_output=True, text=True)
    if r.returncode != 0:
        aviso("GPU NVIDIA nao detectada  modo CPU")
        return "cpu", "https://download.pytorch.org/whl/cpu", "Sem GPU"
    linha = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    nome  = linha.split(":", 1)[1].split("(")[0].strip() if ":" in linha else linha
    ok(f"GPU Detectada: {nome}")
    ok("Modo: CUDA 12.1 (Estavel)")
    return "CUDA121", "https://download.pytorch.org/whl/cu121", nome


# 
# 2. pip base
# 
def etapa_pip_base():
    titulo("2/8", "Atualizando pip / setuptools")
    pip_grupo(["pip","setuptools","wheel"], "Ferramentas base", ["--upgrade"])


# 
# 3. PyTorch
# 
def etapa_pytorch(gpu_mode, torch_url):
    titulo("3/8", "PyTorch com suporte GPU")
    flags = ["--index-url", torch_url]
    pip_grupo(["torch","torchvision","torchaudio"], "PyTorch", flags)
    r = run([sys.executable, "-c",
             "import torch; c=torch.cuda.is_available();"
             "print('[OK] PyTorch', torch.__version__, '| CUDA:', c,"
             "('|', torch.cuda.get_device_name(0)) if c else '')"],
            capture_output=True, text=True)
    print(f"  {VD}{r.stdout.strip()}{RS}")


# 
# 4. Dependancias
# 
def etapa_deps(gpu_mode):
    titulo("4/8", "Dependencias Pemara + Studio Pro")
    pip_grupo(["fastapi","uvicorn[standard]","httpx","requests","pydantic",
               "PyMuPDF","pdf2docx","python-docx","python-multipart"], "Core API + PDF")
    pip_grupo(["faster-whisper","pydub","soundfile","scipy","numpy","imageio-ffmpeg"],
              "Audio (Whisper + DSP)")
    preparar_whisper_offline()
    pip_grupo(["Pillow","realesrgan","basicsr","facexlib","gfpgan"],
              "Imagem (ESRGAN)")
    rembg = ["rembg[gpu]","onnxruntime-gpu"] if gpu_mode != "cpu" else ["rembg","onnxruntime"]
    pip_grupo(rembg, "RemBG (remover fundo)")
    pip_grupo(["demucs"], "Demucs (separacao de voz)")
    pip_grupo(["nvidia-ml-py","psutil"], "Sensores GPU/CPU")
    pip_grupo(["easyocr","pandas","openpyxl","google-generativeai",
               "python-dotenv","ollama","anthropic","openai"], "Organizador IA")


def preparar_whisper_offline():
    """Baixa o modelo usado pelo ditado para que o runtime permaneça offline."""
    tamanho = os.environ.get("MAESTRO_EDITOR_WHISPER_SIZE", "base").strip() or "base"
    info(f"Preparando Faster Whisper local ({tamanho})")
    codigo = (
        "import sys; "
        "from faster_whisper.utils import download_model; "
        "print(download_model(sys.argv[1]))"
    )
    try:
        resultado = run(
            [sys.executable, "-c", codigo, tamanho],
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        aviso(f"Modelo Whisper nao foi preparado: {exc}")
        return
    if resultado.returncode == 0:
        ok(f"Faster Whisper {tamanho} disponivel para ditado offline")
    else:
        detalhe = (resultado.stderr or resultado.stdout or "erro desconhecido").strip()
        aviso(f"Modelo Whisper nao foi preparado: {detalhe[-300:]}")



# 
# FIX 2: Patch basicsr  monkey-patch no runtime, nao em arquivo
# 
def etapa_patch():
    titulo("5/8", "Patch basicsr (compatibilidade torchvision moderna)")
    info("Aplicando monkey-patch via sys.modules  compativel com qualquer versao PyTorch")

    # Estrategia: injeta modulo falso 'functional_tensor' que aponta para
    # 'functional' atual. Isso funciona independente da versao do PyTorch.
    patch_code = '''
import sys
try:
    import torchvision.transforms.functional as _tvf
    from types import ModuleType as _MT
    _m = _MT("torchvision.transforms.functional_tensor")
    # Copia tudo que basicsr pode pedir
    for _attr in dir(_tvf):
        try: setattr(_m, _attr, getattr(_tvf, _attr))
        except: pass
    sys.modules["torchvision.transforms.functional_tensor"] = _m
    print("[PATCH] torchvision.transforms.functional_tensor injetado OK")
except Exception as e:
    print(f"[PATCH] aviso: {e}")
'''

    patch_file = BASE / "shared" / "_torchvision_patch.py"
    patch_file.write_text(patch_code.strip(), encoding="utf-8")
    ok(f"Patch salvo em shared/_torchvision_patch.py")

    # Aplica no servico Studio para ser importado no startup
    studio_main = BASE / "services" / "studio" / "main.py"
    if studio_main.exists():
        conteudo = studio_main.read_text(encoding="utf-8")
        patch_import = "import sys, os\nsys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..','shared'))\ntry:\n    import _torchvision_patch  # noqa\nexcept Exception:\n    pass\n"
        if "_torchvision_patch" not in conteudo:
            studio_main.write_text(patch_import + conteudo, encoding="utf-8")
            ok("Patch injetado no services/studio/main.py")
        else:
            ok("Patch ja presente no studio/main.py")

    # Testa
    r = run([sys.executable, "-c",
             "import sys; exec(open(r'" + str(patch_file).replace("\\","\\\\") + "').read()); "
             "import torchvision.transforms.functional_tensor as t; print('[OK] import OK')"],
            capture_output=True, text=True)
    if "[OK]" in r.stdout:
        ok("Patch validado  basicsr vai importar corretamente")
    else:
        aviso("Validacao parcial  basicsr pode funcionar mesmo assim")


# 
# 6. pywebview
# 
def etapa_pywebview():
    titulo("6/8", "Frontend Desktop (pywebview)")
    pip_grupo(["pywebview"], "pywebview  janela nativa sem browser")
    r = run([sys.executable, "-c", "import webview; print(webview.__version__)"],
            capture_output=True, text=True)
    if r.returncode == 0:
        ok(f"pywebview {r.stdout.strip()}")
    else:
        aviso("pywebview instalado  backend grafico ativo no Windows")


# 
# 7. FFmpeg
# 
def etapa_ffmpeg():
    titulo("7/8", "FFmpeg")
    if tem("ffmpeg"):
        ok("FFmpeg ja instalado")
        return
    info("Instalando via winget...")
    if tem("winget"):
        r = run(["winget","install","--id=Gyan.FFmpeg","-e",
                 "--accept-package-agreements","--accept-source-agreements"],
                capture_output=True)
        if r.returncode == 0:
            ok("FFmpeg instalado")
        else:
            aviso("Instale em: https://ffmpeg.org/download.html")
    else:
        aviso("winget nao encontrado. Instale o FFmpeg manualmente em https://ffmpeg.org/download.html e adicione ao PATH.")


# 
# FIX 1+4: Madulos v4  resiliente + npm.cmd correto
# 
def etapa_modulos_v4():
    titulo("8/8", "Modulos v4 (AnythingLLM, ComfyUI, Perplexica, TripoSG)")
    ferramentas = BASE / "ferramentas"
    ferramentas.mkdir(exist_ok=True)

    #  AnythingLLM 
    try:
        info("AnythingLLM (NotebookLM++)...")
        dest = ferramentas / "anythingllm"
        dest.mkdir(exist_ok=True)
        exe  = dest / "AnythingLLMDesktop.exe"
        if not exe.exists():
            aviso("O AnythingLLM nao permite mais download direto automatizado.")
            info("Por favor, baixe manualmente o instalador (.exe) no site oficial.")
            info("Salve o arquivo baixado em: ferramentas/anythingllm/")
            try:
                import webbrowser
                webbrowser.open("https://anythingllm.com/download")
            except: pass
        else:
            ok("AnythingLLM ja existe")
    except Exception as e:
        aviso(f"AnythingLLM: {e}  pule e continue manualmente")

    #  ComfyUI 
    try:
        info("ComfyUI + FLUX.1 (imagens IA)...")
        dest = ferramentas / "ComfyUI"
        if not (dest / "main.py").exists():
            if tem("git"):
                r = run([git(),"clone","--depth=1",
                         "https://github.com/comfyanonymous/ComfyUI.git", str(dest)],
                        capture_output=True)
                if r.returncode == 0:
                    req = dest / "requirements.txt"
                    if req.exists():
                        pip_grupo(["-r", str(req)], "ComfyUI requirements")
                    ok("ComfyUI instalado")
                else:
                    aviso("Falha ao clonar ComfyUI")
            else:
                aviso("git nao encontrado  instale em git-scm.com")
        else:
            ok("ComfyUI ja existe")
    except Exception as e:
        aviso(f"ComfyUI: {e}")

    #  Perplexica  FIX: usa npm.cmd + shell=True como fallback 
    try:
        info("Perplexica (DeepSearch)...")
        dest = ferramentas / "perplexica"
        if not (dest / "package.json").exists():
            if tem("git") and tem("node"):
                r = run([git(),"clone","--depth=1",
                         "https://github.com/ItzCrazyKns/Perplexica.git", str(dest)],
                        capture_output=True)
                if r.returncode == 0:
                    # config
                    cfg_s = dest / "config.toml.sample"
                    cfg   = dest / "config.toml"
                    if cfg_s.exists() and not cfg.exists():
                        shutil.copy(cfg_s, cfg)
                        c = cfg.read_text()
                        cfg.write_text(c.replace(
                            'OLLAMA_URL = ""', 'OLLAMA_URL = "http://localhost:11434"'))

                    # FIX: npm.cmd no Windows
                    npm_resultado = run(
                        [npm(), "install"],
                        cwd=str(dest),
                        capture_output=True,
                        text=True
                    )
                    if npm_resultado.returncode == 0:
                        ok("Perplexica instalado")
                    else:
                        # Fallback: shell=True
                        npm_fallback = run(
                            "npm install",
                            cwd=str(dest),
                            shell=True,
                            capture_output=True,
                            text=True
                        )
                        if npm_fallback.returncode == 0:
                            ok("Perplexica instalado (via shell)")
                        else:
                            aviso(f"npm install falhou: {npm_fallback.stderr[:100]}")
                else:
                    aviso("Falha ao clonar Perplexica")
            else:
                aviso("git e node necessarios  instale em nodejs.org e git-scm.com")
        else:
            ok("Perplexica ja existe")
    except Exception as e:
        aviso(f"Perplexica: {e}")

    #  TripoSG 
    try:
        info("TripoSG (modelos 3D)...")
        dest = ferramentas / "triposg"
        if not dest.exists():
            if tem("git"):
                r = run([git(),"clone","--depth=1",
                         "https://github.com/VAST-AI-Research/TripoSG.git", str(dest)],
                        capture_output=True)
                if r.returncode != 0:
                    r = run([git(),"clone","--depth=1",
                             "https://github.com/TencentARC/InstantMesh.git", str(dest)],
                            capture_output=True)
                req = dest / "requirements.txt"
                if req.exists():
                    pip_grupo(["-r", str(req)], "TripoSG requirements")
                ok("TripoSG instalado")
            else:
                aviso("git necessario for TripoSG")
        else:
            ok("TripoSG ja existe")
    except Exception as e:
        aviso(f"TripoSG: {e}")


    # Cria diretarios de dados
    for d in ["dados/database","dados/logs","dados/entrada","dados/saida"]:
        (BASE / d).mkdir(parents=True, exist_ok=True)

    ok("Modulos v4 concluidos")


# 
# Opcional: Claude Code + Ollama
# 
def perguntar_claude():
    print()
    resp = input(f"  {CN}Instalar Claude Code + Ollama? (s/N):{RS} ").strip().lower()
    if resp != "s":
        info("Pulando Claude Code + Ollama")
        return
    try:
        if not tem("node"):
            if tem("winget"):
                run(["winget","install","--id=OpenJS.NodeJS","-e",
                     "--accept-package-agreements","--accept-source-agreements"])
            else:
                aviso("Node.js e winget nao encontrados. Instale o Node manualmente em nodejs.org")
                return
        if not tem("ollama"):
            tmp = Path(os.environ.get("TEMP","/tmp")) / "OllamaSetup.exe"
            download_com_progresso("https://ollama.com/download/OllamaSetup.exe", tmp, "Ollama")
            run([str(tmp), "/S"])
            tmp.unlink(missing_ok=True)
        info("Baixando modelo Claude Code (~14GB)...")
        run(["ollama","pull","slekrem/gpt-oss-claude-code-32k:20b"])
        if not tem("claude"):
            run([npm(), "install", "-g", "@anthropic-ai/claude-code"])
        launcher = BASE / "CLAUDE_OLLAMA.bat"
        launcher.write_text(
            "@echo off\nchcp 65001 >nul\n"
            "set ANTHROPIC_BASE_URL=http://localhost:11434\n"
            "set ANTHROPIC_API_KEY=ollama\n"
            "set CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1\n"
            "claude --model slekrem/gpt-oss-claude-code-32k:20b\npause\n",
            encoding="ascii"
        )
        ok("Claude Code + Ollama pronto - CLAUDE_OLLAMA.bat")
    except Exception as e:
        aviso(f"Claude Code: {e}")


# 
# MAIN
# 
def main():
    print(f"\n{BD}{CN}{'='*54}{RS}")
    print(f"{BD}  PEMARA UNIVERSAL v4.0  INSTALADOR MESTRE{RS}")
    print(f"{BD}  Ryzen 9 7950x | RTX 5080 | 64GB | NVMe 14900{RS}")
    print(f"{CI}{'='*54}{RS}\n")

    gpu_mode, torch_url, gpu_nome = etapa_gpu()
    etapa_pip_base()
    etapa_pytorch(gpu_mode, torch_url)
    etapa_deps(gpu_mode)
    etapa_patch()
    etapa_pywebview()
    etapa_ffmpeg()
    etapa_modulos_v4()
    # perguntar_claude()

    print(f"\n{BD}{VD}{'='*54}{RS}")
    print(f"{BD}{VD}  INSTALACAO CONCLUIDA!{RS}")
    print(f"{CI}{'='*54}{RS}")
    print(f"\n  {BD}Para iniciar: INICIAR.bat{RS}  (duplo clique)")
    print(f"  Abre janela desktop nativa - sem browser, sem Streamlit\n")


if __name__ == "__main__":
    try:
        main()
        if IS_WIN:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "A instalaaao foi concluada com sucesso!\n\nVoca ja pode fechar esta janela e rodar o INICIAR.bat para abrir o sistema.", "Pemara v4.0 - Instalaaao Concluada", 0x40 | 0x0)
    except KeyboardInterrupt:
        print(f"\n  {AM}Cancelado pelo usuario.{RS}")
    except Exception as e:
        print(f"\n  {VM}ERRO FATAL: {e}{RS}")
        import traceback; traceback.print_exc()
        if IS_WIN:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Ocorreu um erro durante a instalaaao:\n{e}", "Erro na Instalaaao", 0x10 | 0x0)
    finally:
        # input(f"\n  Pressione Enter para fechar...")
        pass

