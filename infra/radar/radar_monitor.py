import os
import sys
import time
import socket
import subprocess
import logging
import shutil
import atexit
import ctypes
import json
import urllib.request
import urllib.error
from logging.handlers import RotatingFileHandler

# Forçar UTF-8 no stdout/stderr do Windows (resolve "Saudǭvel" no console)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Localizar o executavel do Docker de forma resiliente
DOCKER_EXE = shutil.which("docker")
if not DOCKER_EXE:
    default_docker_path = r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if os.path.exists(default_docker_path):
        DOCKER_EXE = default_docker_path
    else:
        DOCKER_EXE = "docker"

# Caminhos
BASE_DIR = r"E:\Pemara"
LOJA_DIR = os.path.join(BASE_DIR, "loja")
MAESTRO_DIR = os.path.join(BASE_DIR, "maestro")
LOG_DIR = os.path.join(BASE_DIR, "logs")
RADAR_DIR = os.path.join(BASE_DIR, "radar")
PIDFILE = os.path.join(RADAR_DIR, "pidfile.lock")

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "radar_monitor.log")

# Logging
logger = logging.getLogger("RadarMonitor")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Lock de instancia unica via PIDFILE (substitui o lock de porta TCP 49999)
def _acquire_pidfile(path):
    if os.name == 'nt':
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.write(fd, str(os.getpid()).encode())
            return fd
        except FileExistsError:
            try:
                with open(path, 'r') as f:
                    content = f.read().strip()
                if not content:
                    os.remove(path)
                    return _acquire_pidfile(path)
                old_pid = int(content)
                PROCESS_QUERY_LIMITED = 0x1000
                STILL_ACTIVE = 259
                h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, old_pid)
                if h:
                    exit_code = ctypes.c_ulong()
                    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code))
                    ctypes.windll.kernel32.CloseHandle(h)
                    if exit_code.value == STILL_ACTIVE:
                        return None
                os.remove(path)
                return _acquire_pidfile(path)
            except Exception:
                try:
                    os.remove(path)
                except Exception:
                    return None
                return _acquire_pidfile(path)
    return None

_pidfile_fd = _acquire_pidfile(PIDFILE)
if _pidfile_fd is None:
    logger.error("Erro Critico: O Radar Monitor ja esta em execucao (pidfile ativo).")
    sys.exit(0)

def _release_pidfile():
    try:
        if _pidfile_fd is not None:
            os.close(_pidfile_fd)
        if os.path.exists(PIDFILE):
            os.remove(PIDFILE)
    except Exception:
        pass
atexit.register(_release_pidfile)

# Parametros de health check
HEALTH_TIMEOUT = 4.0
HEALTH_RETRIES = 2
HEALTH_RETRY_DELAY = 1.0
COLD_START_TENTATIVAS = 10
COLD_START_INTERVALO = 3

# URLs de health (ajuste aqui se a loja/maestro tiver rota /health)
LOJA_HEALTH_URL = "http://127.0.0.1:5000/"
MAESTRO_HEALTH_URL = "http://127.0.0.1:9501/"
STUDIO_GENERATIVE_URL = "http://127.0.0.1:8029/api/generative/status"
STUDIO_READINESS_URL = "http://127.0.0.1:8029/api/status"
STUDIO_GENERATIVE_PORT = 8029
STUDIO_RESTART_FLAG = os.path.join(MAESTRO_DIR, "pemara", "dados", "flags", "studio_restart_requested.flag")
STUDIO_RESTART_SCRIPT = os.path.join(MAESTRO_DIR, "pemara", "services", "studio", "restart_studio.ps1")
MAESTRO_RESTART_FLAG = os.path.join(MAESTRO_DIR, "pemara", "dados", "flags", "maestro_frontend_restart_requested.flag")
MAESTRO_RESTART_SCRIPT = os.path.join(MAESTRO_DIR, "pemara", "reset_maestro_frontend.ps1")
COMFY_RESTART_FLAG = os.path.join(MAESTRO_DIR, "pemara", "dados", "flags", "comfy_restart_requested.flag")
COMFY_RESTART_SCRIPT = os.path.join(MAESTRO_DIR, "pemara", "ferramentas", "ComfyUI", "restart_comfy.ps1")
COMFY_EXPECTED_ROOT = os.path.normcase(
    os.path.abspath('D:/PemaraRuntimes/ComfyUI-v0.40.0-pemara/main.py')
)
COMFY_EXPECTED_VERSION = "0.41.0"
COMFY_EXPECTED_TORCH = "2.14.0+cu130"
OLLAMA_HOST = os.environ.get("MAESTRO_OLLAMA_HOST", "127.0.0.1:11435").strip()
OLLAMA_CONTEXT_LENGTH = os.environ.get("OLLAMA_CONTEXT_LENGTH", "262144").strip() or "262144"
OLLAMA_KV_CACHE_TYPE = os.environ.get("OLLAMA_KV_CACHE_TYPE", "q8_0").strip() or "q8_0"
OLLAMA_FLASH_ATTENTION = os.environ.get("OLLAMA_FLASH_ATTENTION", "1").strip() or "1"
OLLAMA_HEALTH_URL = f"http://{OLLAMA_HOST}/api/tags"
HERMES_DIR = os.path.join(MAESTRO_DIR, "pemara", "ferramentas", "hermes")

def http_health(url, retries=HEALTH_RETRIES, timeout=HEALTH_TIMEOUT, accept_unauth=False):
    """GET na URL; retorna True se servidor respondeu (2xx/3xx, ou 401/403 se accept_unauth)."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'RadarMonitor/2.0'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 400:
                    return True
                last_err = f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            if accept_unauth and e.code in (401, 403):
                return True  # Servidor respondeu - so esta exigindo auth
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError, ConnectionResetError) as e:
            last_err = str(e)
        if attempt < retries:
            time.sleep(HEALTH_RETRY_DELAY * attempt)
    logger.debug(f"Health check falhou para {url} apos {retries} tentativas: {last_err}")
    return False

def is_port_open(port, host="127.0.0.1", timeout=2.0):
    """Fallback rapido: TCP connect."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.close()
            return True
    except Exception:
        return False

def _hidden_creationflags():
    return 0x08000000 if os.name == 'nt' else 0

def _ollama_exe_path():
    candidatos = [
        r"C:\PemaraAI\ollama\ollama.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
        shutil.which("ollama"),
        r"C:\Program Files\Ollama\ollama.exe",
        r"C:\Program Files (x86)\Ollama\ollama.exe",
    ]
    for candidato in candidatos:
        if candidato and os.path.exists(candidato):
            return candidato
    return None

def _python_process_has_fragment(fragment):
    """Checa processos Python por trecho de command line sem depender de psutil."""
    if os.name == 'nt':
        try:
            powershell = shutil.which("powershell.exe") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            safe_fragment = fragment.replace("'", "''")
            script = (
                "Get-CimInstance Win32_Process "
                "-Filter \"name='python.exe' OR name='pythonw.exe'\" | "
                f"Where-Object {{ $_.CommandLine -like '*{safe_fragment}*' }} | "
                "Select-Object -First 1 -ExpandProperty ProcessId"
            )
            res = subprocess.run(
                [powershell, "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=10,
                creationflags=_hidden_creationflags()
            )
            return bool(res.stdout.strip())
        except Exception as e:
            logger.debug(f"Falha ao checar processo Python ({fragment}): {e}")
            return False
    try:
        res = subprocess.run(["pgrep", "-af", fragment], capture_output=True, text=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False

def hermes_configurado():
    env_path = os.path.join(HERMES_DIR, ".env")
    if not os.path.exists(env_path):
        return False
    try:
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == "TELEGRAM_BOT_TOKEN":
                    token = value.strip().strip('"').strip("'")
                    token_lower = token.lower()
                    invalid_markers = ("seu_token", "seu_bot_token", "change_me", "changeme", "placeholder", "dummy", "testing", "xxx")
                    return bool(token) and not any(marker in token_lower for marker in invalid_markers)
    except Exception as e:
        logger.debug(f"Falha lendo .env do Hermes: {e}")
    return False

def is_comfyui_safe(timeout=4.0):
    """ComfyUI saudavel para o ecossistema Pemara: API local e sem listen 0.0.0.0."""
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/system_stats", headers={'User-Agent': 'RadarMonitor/2.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if not (200 <= resp.status < 300):
                return False
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        system = data.get("system", {})
        if system.get("comfyui_version") != COMFY_EXPECTED_VERSION:
            logger.warning("ComfyUI respondeu com versao divergente: %s", system.get("comfyui_version"))
            return False
        if system.get("pytorch_version") != COMFY_EXPECTED_TORCH:
            logger.warning("ComfyUI respondeu com PyTorch divergente: %s", system.get("pytorch_version"))
            return False
        argv = system.get("argv", [])
        if "--listen" in argv:
            idx = argv.index("--listen")
            if idx + 1 < len(argv) and argv[idx + 1] in ("0.0.0.0", "::"):
                logger.warning("ComfyUI respondeu, mas esta exposto em %s. Marcando para recuperacao.", argv[idx + 1])
                return False
        actual_main = os.path.normcase(os.path.abspath(str(argv[0]))) if argv else ""
        if actual_main != COMFY_EXPECTED_ROOT:
            logger.warning("ComfyUI respondeu de runtime divergente: %s", actual_main)
            return False
        return True
    except Exception as e:
        logger.debug(f"ComfyUI health local falhou: {e}")
        return False

def check_container_running(name):
    try:
        cmd = [DOCKER_EXE, "ps", "--filter", f"name={name}", "--format", "{{.Names}}"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        return name in res.stdout
    except Exception as e:
        logger.error(f"Erro ao checar container {name}: {e}")
        return False

def _wait_http_healthy(url, label, max_tentativas=COLD_START_TENTATIVAS, intervalo=COLD_START_INTERVALO, accept_unauth=False):
    """Aguarda a URL responder 2xx ate max_tentativas. Retorna True se saudavel."""
    for i in range(1, max_tentativas + 1):
        if http_health(url, retries=1, timeout=4.0, accept_unauth=accept_unauth):
            logger.info(f"{label} respondendo HTTP em {url} (tentativa {i}/{max_tentativas}).")
            return True
        time.sleep(intervalo)
    return False

def recuperar_loja():
    logger.warning("Iniciando auto-recuperacao da Loja Online...")
    try:
        if not check_container_running("pemara-loja"):
            logger.info("Container pemara-loja nao esta rodando. Subindo stack...")
            res = subprocess.run(
                [DOCKER_EXE, "compose", "up", "-d"],
                cwd=LOJA_DIR, capture_output=True, text=True, timeout=120
            )
            if res.returncode != 0:
                logger.error(f"docker compose up falhou: {res.stderr.strip()}")
                return False
        # Validacao pos-start com paciencia (cold-start)
        if _wait_http_healthy(LOJA_HEALTH_URL, "Loja Online"):
            logger.info("Loja restaurada com sucesso (HTTP 200 confirmado).")
            return True
        logger.error("Loja NAO respondeu HTTP apos janela de cold-start.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout no docker compose up da Loja.")
        return False
    except Exception as e:
        logger.error(f"Falha critica ao recuperar Loja: {e}")
        return False

def recuperar_maestro():
    logger.warning("Iniciando auto-recuperacao do Maestro Engine...")
    try:
        logger.info("Passo 1/4: Executando desbloquear_ambiente.py...")
        desbloqueador = os.path.join(MAESTRO_DIR, "desbloquear_ambiente.py")
        if os.path.exists(desbloqueador):
            subprocess.run([sys.executable, "desbloquear_ambiente.py"], cwd=MAESTRO_DIR, capture_output=True, text=True, timeout=60)

        logger.info("Passo 2/4: Iniciando MASTER.py em background...")
        cmd = [sys.executable, "MASTER.py"]
        creationflags = 0x08000000 if os.name == 'nt' else 0
        maestro_root = os.path.join(MAESTRO_DIR, "pemara")
        log_dir = os.path.join(maestro_root, "dados", "logs")
        os.makedirs(log_dir, exist_ok=True)
        out_log = os.path.join(log_dir, "master_radar.out.log")
        err_log = os.path.join(log_dir, "master_radar.err.log")
        env = os.environ.copy()
        env["PYTHONPATH"] = maestro_root
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["MAESTRO_FRONTEND_PORT"] = "9501"
        env["MAESTRO_STUDIO_PORT"] = "8029"
        with open(out_log, "a", encoding="utf-8") as out, open(err_log, "a", encoding="utf-8") as err:
            subprocess.Popen(cmd, cwd=maestro_root, env=env, stdout=out, stderr=err, creationflags=creationflags)

        logger.info("Aguardando 10 segundos para inicializacao dos microservicos...")
        time.sleep(10)

        logger.info("Passo 3/4: Garantindo container do tunel Cloudflare...")
        res = subprocess.run(
            [DOCKER_EXE, "compose", "up", "-d"],
            cwd=MAESTRO_DIR, capture_output=True, text=True, timeout=120
        )
        if res.returncode != 0:
            logger.error(f"docker compose up (tunel) falhou: {res.stderr.strip()}")

        logger.info("Passo 4/4: Validando HTTP local.")
        if _wait_http_healthy(MAESTRO_HEALTH_URL, "Maestro Engine", accept_unauth=True):
            logger.info("Maestro restabelecido. Cooldown de 30s.")
            time.sleep(30)
            return True
        logger.error("Maestro NAO respondeu HTTP apos restauracao.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout na recuperacao do Maestro.")
        return False
    except Exception as e:
        logger.error(f"Falha critica ao recuperar Maestro: {e}")
        return False

def recuperar_tunel_maestro():
    logger.warning("Tunel Maestro offline (backend ok). Reiniciando apenas o tunel...")
    try:
        res = subprocess.run(
            [DOCKER_EXE, "compose", "up", "-d"],
            cwd=MAESTRO_DIR, capture_output=True, text=True, timeout=120
        )
        if res.returncode != 0:
            logger.error(f"Falha ao subir tunel: {res.stderr.strip()}")
            return False
        # Verifica se o container do tunel esta rodando (validacao real do tunel
        # exigiria hit externo; aqui validamos o container)
        if check_container_running("maestro-cloudflared"):
            logger.info("Tunel do Maestro restabelecido (container ativo).")
            return True
        logger.error("Tunel subiu mas container nao esta rodando.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout ao subir tunel.")
        return False
    except Exception as e:
        logger.error(f"Falha ao restaurar tunel do Maestro: {e}")
        return False

def garantir_docker_ativo():
    try:
        cmd = [DOCKER_EXE, "info"]
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        return True
    except Exception:
        logger.warning("Docker daemon nao responde. Tentando iniciar Docker Desktop...")
        docker_desktop_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if os.path.exists(docker_desktop_path):
            try:
                creationflags = 0x08000000 if os.name == 'nt' else 0
                subprocess.Popen([docker_desktop_path], creationflags=creationflags)
                logger.info("Docker Desktop lancado. Aguardando 30s para inicializacao...")
                time.sleep(30)
                subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
                logger.info("Docker daemon iniciado com sucesso.")
                return True
            except Exception as ex:
                logger.error(f"Falha ao iniciar Docker Desktop: {ex}")
                return False
        else:
            logger.error(f"Executavel do Docker Desktop nao encontrado em {docker_desktop_path}")
            return False

def recuperar_sprunki():
    logger.warning("Iniciando auto-recuperacao do Gerador Sprunki...")
    try:
        sprunki_path = os.path.join(MAESTRO_DIR, "pemara", "ferramentas", "gerador_sprunki", "app.py")
        if os.path.exists(sprunki_path):
            log_dir = os.path.join(MAESTRO_DIR, "pemara", "dados", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "sprunki.log")

            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(MAESTRO_DIR, "pemara")
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            creationflags = 0x08000000 if os.name == 'nt' else 0
            with open(log_file, "a", encoding="utf-8") as f:
                subprocess.Popen(
                    [sys.executable, sprunki_path],
                    cwd=os.path.dirname(sprunki_path),
                    env=env,
                    stdout=f,
                    stderr=f,
                    creationflags=creationflags
                )
            # Espera porta abrir (cold-start)
            if _wait_http_healthy("http://127.0.0.1:5005/", "Gerador Sprunki", max_tentativas=6, intervalo=2):
                logger.info("Gerador Sprunki iniciado em background (HTTP ok).")
                return True
            logger.warning("Gerador Sprunki foi lancado mas nao respondeu HTTP ainda.")
            return True  # Popen ja foi disparado, considera sucesso
        else:
            logger.error("Caminho do Gerador Sprunki nao encontrado!")
            return False
    except Exception as e:
        logger.error(f"Falha ao recuperar Gerador Sprunki: {e}")
        return False

def recuperar_ollama():
    logger.warning("Iniciando auto-recuperacao do Ollama...")
    try:
        ollama_exe = _ollama_exe_path()
        if not ollama_exe:
            logger.error("Ollama nao encontrado. Reinstale pelo instalador oficial.")
            return False

        log_dir = os.path.join(MAESTRO_DIR, "pemara", "dados", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "ollama_radar.log")
        ollama_env = os.environ.copy()
        ollama_env["OLLAMA_HOST"] = OLLAMA_HOST
        ollama_env["OLLAMA_CONTEXT_LENGTH"] = OLLAMA_CONTEXT_LENGTH
        ollama_env["OLLAMA_KV_CACHE_TYPE"] = OLLAMA_KV_CACHE_TYPE
        ollama_env["OLLAMA_FLASH_ATTENTION"] = OLLAMA_FLASH_ATTENTION
        ollama_env.setdefault(
            "OLLAMA_MODELS",
            os.path.join(os.environ.get("USERPROFILE", ""), ".ollama", "models"),
        )

        with open(log_file, "a", encoding="utf-8") as f:
            subprocess.Popen(
                [ollama_exe, "serve"],
                cwd=os.path.dirname(ollama_exe),
                env=ollama_env,
                stdout=f,
                stderr=f,
                creationflags=_hidden_creationflags()
            )

        if _wait_http_healthy(OLLAMA_HEALTH_URL, "Ollama", max_tentativas=8, intervalo=2):
            logger.info("Ollama iniciado e saudavel.")
            return True
        logger.warning("Ollama foi lancado mas ainda nao respondeu HTTP.")
        return True
    except Exception as e:
        logger.error(f"Falha ao recuperar Ollama: {e}")
        return False

def recuperar_hermes():
    logger.warning("Iniciando auto-recuperacao do Hermes...")
    try:
        bot_py = os.path.join(HERMES_DIR, "hermes_bot.py")
        if not os.path.exists(bot_py):
            logger.error("hermes_bot.py nao encontrado.")
            return False
        if not hermes_configurado():
            logger.warning("Hermes sem TELEGRAM_BOT_TOKEN valido. Nao iniciado.")
            return False
        if _python_process_has_fragment("hermes_bot.py"):
            logger.info("Hermes ja esta rodando.")
            return True

        log_dir = os.path.join(MAESTRO_DIR, "pemara", "dados", "logs")
        os.makedirs(log_dir, exist_ok=True)
        out_log = os.path.join(log_dir, "hermes_bot_radar.out.log")
        err_log = os.path.join(log_dir, "hermes_bot_radar.err.log")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        with open(out_log, "a", encoding="utf-8") as out, open(err_log, "a", encoding="utf-8") as err:
            subprocess.Popen(
                [sys.executable, bot_py],
                cwd=HERMES_DIR,
                env=env,
                stdout=out,
                stderr=err,
                creationflags=_hidden_creationflags()
            )

        time.sleep(5)
        if _python_process_has_fragment("hermes_bot.py"):
            logger.info("Hermes iniciado e processo ativo.")
            return True
        logger.error("Hermes foi lancado mas nao permaneceu ativo. Verifique hermes_bot_radar.err.log.")
        return False
    except Exception as e:
        logger.error(f"Falha ao recuperar Hermes: {e}")
        return False

def recuperar_studio_generative():
    logger.warning("Iniciando auto-recuperacao do Studio Generative...")
    try:
        studio_dir = os.path.join(MAESTRO_DIR, "pemara", "services", "studio")
        main_py = os.path.join(studio_dir, "main.py")
        if not os.path.exists(main_py):
            logger.error("services/studio/main.py nao encontrado.")
            return False

        if is_port_open(STUDIO_GENERATIVE_PORT, timeout=2.0):
            logger.warning("Porta %s ocupada, mas endpoint generative nao respondeu. Nao derrubei processo desconhecido.", STUDIO_GENERATIVE_PORT)
            return False

        log_dir = os.path.join(MAESTRO_DIR, "pemara", "dados", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"studio_generative_{STUDIO_GENERATIVE_PORT}.log")

        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(MAESTRO_DIR, "pemara")
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        creationflags = 0x08000000 if os.name == 'nt' else 0
        media_python = sys.executable
        studio_python = media_python
        runtime = os.path.join(MAESTRO_DIR, "pemara", "sistema", "studio-web-runtime.json")
        if os.path.isfile(runtime):
            with open(runtime, encoding="utf-8") as handle:
                studio_python = json.load(handle)["python"]
            if not os.path.isabs(studio_python) or not os.path.isfile(studio_python):
                raise ValueError("Python configurado do Studio indisponivel.")
            env["PEMARA_STUDIO_MEDIA_PYTHON"] = media_python
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        cmd = [
            studio_python, "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1",
            "--port", str(STUDIO_GENERATIVE_PORT),
            "--app-dir", studio_dir,
            "--log-level", "warning",
        ]
        with open(log_file, "a", encoding="utf-8") as f:
            subprocess.Popen(cmd, cwd=studio_dir, env=env, stdout=f, stderr=f, creationflags=creationflags)

        if _wait_http_healthy(STUDIO_GENERATIVE_URL, "Studio Generative", max_tentativas=8, intervalo=2):
            logger.info("Studio Generative iniciado e saudavel em %s.", STUDIO_GENERATIVE_PORT)
            return True
        logger.warning("Studio Generative foi lancado mas ainda nao respondeu HTTP.")
        return True
    except Exception as e:
        logger.error(f"Falha ao recuperar Studio Generative: {e}")
        return False

def processar_reinicio_solicitado_studio():
    """Consome somente a solicitacao fixa de reinicio do Studio na porta oficial."""
    if not os.path.exists(STUDIO_RESTART_FLAG):
        return False
    logger.warning("Solicitacao administrativa de reinicio do Studio detectada.")
    try:
        if not os.path.isfile(STUDIO_RESTART_SCRIPT):
            logger.error("Reiniciador do Studio nao encontrado: %s", STUDIO_RESTART_SCRIPT)
            return False
        powershell = shutil.which("powershell.exe") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", STUDIO_RESTART_SCRIPT,
                "-Port", str(STUDIO_GENERATIVE_PORT),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            creationflags=_hidden_creationflags(),
        )
        if result.returncode != 0 or not http_health(STUDIO_READINESS_URL, retries=2, timeout=5.0):
            logger.error(
                "Reinicio solicitado do Studio falhou (exit=%s). Consulte restart_studio_admin.log.",
                result.returncode,
            )
            return False
        os.remove(STUDIO_RESTART_FLAG)
        logger.info("Reinicio solicitado do Studio concluido e flag consumida.")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Timeout no reinicio solicitado do Studio.")
        return False
    except Exception as e:
        logger.error("Falha ao processar reinicio solicitado do Studio: %s", e)
        return False


def processar_reinicio_solicitado_maestro():
    """Recarrega somente o frontend/proxy autenticado do Maestro."""
    if not os.path.exists(MAESTRO_RESTART_FLAG):
        return False
    logger.warning("Solicitacao administrativa de reinicio do frontend Maestro detectada.")
    try:
        if not os.path.isfile(MAESTRO_RESTART_SCRIPT):
            logger.error("Reiniciador do frontend Maestro nao encontrado: %s", MAESTRO_RESTART_SCRIPT)
            return False
        powershell = shutil.which("powershell.exe") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", MAESTRO_RESTART_SCRIPT,
                "-Port", "9501",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            creationflags=_hidden_creationflags(),
        )
        if result.returncode != 0 or not http_health(MAESTRO_HEALTH_URL, retries=2, timeout=5.0, accept_unauth=True):
            logger.error(
                "Reinicio solicitado do frontend Maestro falhou (exit=%s). Consulte maestro_frontend_reset.log.",
                result.returncode,
            )
            return False
        os.remove(MAESTRO_RESTART_FLAG)
        logger.info("Reinicio solicitado do frontend Maestro concluido e flag consumida.")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Timeout no reinicio solicitado do frontend Maestro.")
        return False
    except Exception as e:
        logger.error("Falha ao processar reinicio solicitado do frontend Maestro: %s", e)
        return False


def processar_reinicio_solicitado_comfy():
    """Consome somente a solicitacao fixa de reinicio do ComfyUI local."""
    if not os.path.exists(COMFY_RESTART_FLAG):
        return False
    logger.warning("Solicitacao administrativa de reinicio do ComfyUI detectada.")
    try:
        if not os.path.isfile(COMFY_RESTART_SCRIPT):
            logger.error("Reiniciador do ComfyUI nao encontrado: %s", COMFY_RESTART_SCRIPT)
            return False
        powershell = shutil.which("powershell.exe") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", COMFY_RESTART_SCRIPT,
                "-Port", "8188",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=150,
            creationflags=_hidden_creationflags(),
        )
        if result.returncode != 0 or not is_comfyui_safe():
            logger.error(
                "Reinicio solicitado do ComfyUI falhou (exit=%s). Consulte restart_comfy_admin.log.",
                result.returncode,
            )
            return False
        os.remove(COMFY_RESTART_FLAG)
        logger.info("Reinicio solicitado do ComfyUI concluido e flag consumida.")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Timeout no reinicio solicitado do ComfyUI.")
        return False
    except Exception as e:
        logger.error("Falha ao processar reinicio solicitado do ComfyUI: %s", e)
        return False

def main():
    logger.info("=" * 60)
    logger.info("  RADAR MONITOR PEMARA v2.0 - modo resiliente")
    logger.info("  Intervalo base: 30s | Backoff exponencial ativo")
    logger.info("  Health check: HTTP 2xx (com retry)")
    logger.info("  Lock: pidfile em %s", PIDFILE)
    logger.info("=" * 60)

    CHECK_INTERVAL = 30
    BASE_COOLDOWN = 30
    MAX_COOLDOWN = 600
    consecutive_failures = 0

    def next_cooldown():
        nonlocal consecutive_failures
        consecutive_failures += 1
        return min(BASE_COOLDOWN * (2 ** (consecutive_failures - 1)), MAX_COOLDOWN)

    def reset_failures():
        nonlocal consecutive_failures
        consecutive_failures = 0

    while True:
        try:
            logger.info("Checagem periodica de integridade...")
            if os.path.exists(MAESTRO_RESTART_FLAG):
                processar_reinicio_solicitado_maestro()
            if os.path.exists(STUDIO_RESTART_FLAG):
                processar_reinicio_solicitado_studio()
            if os.path.exists(COMFY_RESTART_FLAG):
                processar_reinicio_solicitado_comfy()
            if not garantir_docker_ativo():
                logger.error("Docker daemon indisponivel. Aguardando 60s...")
                time.sleep(60)
                continue

            # --- LOJA ---
            loja_ok = http_health(LOJA_HEALTH_URL, retries=2, timeout=4.0)
            loja_container_ok = check_container_running("pemara-loja")
            loja_saudavel = loja_ok and loja_container_ok

            if not loja_saudavel:
                logger.error(
                    f"Loja Online COM PROBLEMA | HTTP ok: {loja_ok} | Container ok: {loja_container_ok}"
                )
                if recuperar_loja():
                    logger.info(f"Loja restaurada. Cooldown: {BASE_COOLDOWN}s")
                    reset_failures()
                    time.sleep(BASE_COOLDOWN)
                    continue
                cd = next_cooldown()
                logger.error(f"Falha ao recuperar Loja. Backoff: {cd}s")
                time.sleep(cd)
                continue
            else:
                logger.info("Loja Online: Saudavel e operacional.")
                reset_failures()

            # --- MAESTRO ---
            # accept_unauth=True: 401/403 indicam que o servidor esta respondendo
            maestro_ok = http_health(MAESTRO_HEALTH_URL, retries=2, timeout=4.0, accept_unauth=True)
            maestro_container_ok = check_container_running("maestro-cloudflared")

            if not maestro_ok:
                logger.error(f"Maestro Engine (HTTP {MAESTRO_HEALTH_URL}) OFFLINE!")
                if recuperar_maestro():
                    logger.info("Maestro restaurado. Cooldown: 90s")
                    reset_failures()
                    time.sleep(90)
                    continue
                cd = next_cooldown()
                logger.error(f"Falha ao recuperar Maestro. Backoff: {cd}s")
                time.sleep(cd)
                continue
            else:
                logger.info("Maestro Engine: Backend saudavel.")
                reset_failures()

                # --- COMFYUI ---
                comfy_main = os.path.join(MAESTRO_DIR, "pemara", "ferramentas", "ComfyUI", "main.py")
                if os.path.exists(comfy_main) and not is_comfyui_safe():
                    logger.warning(
                        "ComfyUI (8188) nao respondeu nesta checagem. "
                        "Maestro e Studio permanecem ativos; a recuperacao isolada do ComfyUI fica com o watchdog dedicado."
                    )
                else:
                    logger.info("ComfyUI: Saudavel e operacional.")

                # --- STUDIO GENERATIVE ---
                if not http_health(STUDIO_GENERATIVE_URL, retries=1, timeout=4.0):
                    logger.warning("Studio Generative (%s) offline. Reiniciando...", STUDIO_GENERATIVE_PORT)
                    if recuperar_studio_generative():
                        time.sleep(20)
                        continue
                else:
                    logger.info("Studio Generative: Saudavel e operacional.")

                # --- OLLAMA ---
                if not http_health(OLLAMA_HEALTH_URL, retries=1, timeout=3.0):
                    logger.warning(f"Ollama ({OLLAMA_HOST}) offline. Reiniciando...")
                    if recuperar_ollama():
                        time.sleep(10)
                        continue
                else:
                    logger.info("Ollama: Saudavel e operacional.")

                # --- HERMES ---
                hermes_bot = os.path.join(HERMES_DIR, "hermes_bot.py")
                if os.path.exists(hermes_bot) and hermes_configurado() and not _python_process_has_fragment("hermes_bot.py"):
                    logger.warning("Hermes offline. Reiniciando...")
                    if recuperar_hermes():
                        time.sleep(10)
                        continue
                elif os.path.exists(hermes_bot):
                    logger.info("Hermes: Saudavel ou sem credencial configurada.")

                # --- SPRUNKI ---
                sprunki_main = os.path.join(MAESTRO_DIR, "pemara", "ferramentas", "gerador_sprunki", "app.py")
                if os.path.exists(sprunki_main) and not is_port_open(5005, timeout=2.0):
                    logger.warning("Gerador Sprunki (5005) offline. Reiniciando...")
                    if recuperar_sprunki():
                        time.sleep(30)
                        continue
                else:
                    logger.info("Gerador Sprunki: Saudavel e operacional.")

                # --- TUNEL ---
                if not maestro_container_ok:
                    logger.warning("Container maestro-cloudflared offline. Recuperando tunel...")
                    if recuperar_tunel_maestro():
                        time.sleep(30)
                        continue
                else:
                    logger.info("Maestro Tunnel: Ativo e encaminhando trafego.")

        except KeyboardInterrupt:
            logger.info("Encerrado pelo usuario (KeyboardInterrupt).")
            break
        except Exception as e:
            logger.exception(f"Erro inesperado no loop: {e}")
            time.sleep(60)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Monitor radar encerrado pelo usuario.")
        sys.exit(0)
