# -*- coding: utf-8 -*-
"""
servidor.py  Inicia TODOS os serviaos do Pemara v4.0
- 7 microserviaos FastAPI
- ComfyUI (se instalado)
- Perplexica (se instalado)
- TripoSG (se instalado)
- Abre janela desktop nativa via pywebview
"""
import sys, os, subprocess, threading, time, shutil, platform, psutil, io, json, base64, urllib.request, urllib.parse, urllib.error, socket, select, hmac, html, posixpath, hashlib, secrets, http.client
import ipaddress
import re
from http.cookies import SimpleCookie
from pathlib import Path

#  FIX: Unicode no Console Windows. Reconfigure in place so importing MASTER
#  cannot close a pytest/caller-owned capture buffer during module teardown.
if os.name == 'nt':
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

BASE     = Path(__file__).parent
APP_DIR  = BASE / "app"
IS_WIN   = platform.system() == "Windows"

def _read_env_file_value(chave):
    for arquivo in (BASE / ".env", BASE.parent / ".env"):
        try:
            if not arquivo.exists():
                continue
            for linha in arquivo.read_text(encoding="utf-8", errors="ignore").splitlines():
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                nome, valor = linha.split("=", 1)
                if nome.strip() == chave:
                    return valor.strip().strip('"').strip("'")
        except Exception:
            continue
    return ""

def _env_value(chave, padrao=""):
    return os.environ.get(chave, "").strip() or _read_env_file_value(chave) or padrao


# The production ComfyUI runtime is versioned and isolated from the historical
# checkout.  Model/input/output paths remain explicit so Studio receipts and
# existing media URLs do not silently move when the runtime is upgraded.
COMFY_RUNTIME_ROOT = Path(
    _env_value(
        "PEMARA_COMFY_RUNTIME_ROOT",
        'D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara',
    )
).resolve()
COMFY_RUNTIME_PYTHON = Path(
    _env_value(
        "PEMARA_COMFY_RUNTIME_PYTHON",
        r"D:\PemaraRuntimes\comfyui-v0360-py311\Scripts\python.exe",
    )
).resolve()
COMFY_EXPECTED_VERSION = _env_value("PEMARA_COMFY_EXPECTED_VERSION", "0.37.0")
COMFY_EXPECTED_TORCH = _env_value("PEMARA_COMFY_EXPECTED_TORCH", "2.14.0+cu130")
COMFY_IO_ROOT = (BASE / "ferramentas" / "ComfyUI").resolve()
COMFY_USER_DIRECTORY = Path(
    _env_value(
        "PEMARA_COMFY_USER_DIRECTORY",
        'D:/PemaraRuntimes/state/ComfyUI-v0.36.0-pemara/user',
    )
).resolve()

def _parse_gateway_hosts(raw_value):
    """Parse an explicit comma-separated hostname allowlist."""
    hosts = set()
    valid_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-.")
    for raw_host in str(raw_value or "").split(","):
        host = raw_host.strip().lower().rstrip(".")
        labels = host.split(".") if host else []
        if (
            not host
            or len(host) > 253
            or any(char not in valid_chars for char in host)
            or any(
                not label
                or len(label) > 63
                or label.startswith("-")
                or label.endswith("-")
                for label in labels
            )
        ):
            continue
        hosts.add(host)
    return hosts

PORT_APP = int(_env_value("MAESTRO_FRONTEND_PORT", "9501"))
STUDIO_PORT = int(_env_value("MAESTRO_STUDIO_PORT", "8029"))
SESSION_COOKIE_NAME = "maestro_session"
CSRF_COOKIE_NAME = "maestro_csrf"
SESSION_MAX_AGE = int(_env_value("MAESTRO_SESSION_MAX_AGE", "2592000"))
SESSION_FILE = BASE / "dados" / "auth_sessions.json"
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5
LOGIN_MAX_CLIENTS = 2048
LOGIN_CSRF_MAX_AGE = 600
_AUTH_LOCK = threading.RLock()
_LOGIN_FAILURES = {}
_TOOL_HANDOFFS = {}
_LOGIN_CSRF_PROCESS_SECRET = secrets.token_bytes(32)

# Somente estas origens publicas podem virar proxy. A porta nunca vem da URL
# nem do navegador, o que evita transformar o Maestro em um proxy aberto/SSRF.
PUBLIC_TOOL_ROUTES = {
    "comfy": {"host": "comfy.pemaratech.com.br", "port": 8188},
    "sprunki": {"host": "sprunki.pemaratech.com.br", "port": 5005},
    "perplexica": {"host": "perplexica.pemaratech.com.br", "port": 3002},
    "hyperframes": {"host": "hyperframes.pemaratech.com.br", "port": 8032},
}
HYPERFRAMES_FALLBACK_AUTHORITY = "maestro.pemaratech.com.br:8443"
HYPERFRAMES_FALLBACK_ROUTE = {
    "name": "hyperframes",
    "host": HYPERFRAMES_FALLBACK_AUTHORITY,
    "port": 8032,
}
PUBLIC_TOOL_HOSTS = {
    config["host"]: {"name": name, **config}
    for name, config in PUBLIC_TOOL_ROUTES.items()
}
PUBLIC_GATEWAY_HOSTS = {"maestro.pemaratech.com.br", *PUBLIC_TOOL_HOSTS.keys()}
LOCAL_GATEWAY_HOSTS = {"127.0.0.1", "localhost"}
PRIVATE_GATEWAY_HOSTS = _parse_gateway_hosts(_env_value("MAESTRO_PRIVATE_GATEWAY_HOSTS"))
ALLOWED_GATEWAY_HOSTS = PUBLIC_GATEWAY_HOSTS | PRIVATE_GATEWAY_HOSTS | LOCAL_GATEWAY_HOSTS
TOOL_HANDOFF_MAX_AGE = 60

def _https_redirect_target(host, forwarded_proto, request_target):
    """Return a safe HTTPS target only for an explicitly HTTP public request."""
    clean_host = (host or "").strip().lower().split(":", 1)[0]
    proto = (forwarded_proto or "").split(",", 1)[0].strip().lower()
    if clean_host not in PUBLIC_GATEWAY_HOSTS or proto != "http":
        return ""
    target = request_target if isinstance(request_target, str) else "/"
    if not target.startswith("/") or "\r" in target or "\n" in target:
        target = "/"
    return f"https://{clean_host}{target}"

def _ler_env_local(chave):
    return _read_env_file_value(chave)

def token_frontend():
    return (
        os.environ.get("MAESTRO_FRONTEND_TOKEN", "").strip()
        or _ler_env_local("MAESTRO_FRONTEND_TOKEN")
    )

def studio_internal_token():
    return _env_value("STUDIO_INTERNAL_TOKEN") or token_frontend()

def maestro_admin_user():
    return _env_value("MAESTRO_ADMIN_USER", "admin")

def maestro_admin_password():
    return _env_value("MAESTRO_ADMIN_PASSWORD", "")

def maestro_admin_password_hash():
    return _env_value("MAESTRO_ADMIN_PASSWORD_HASH", "")

def _senha_scrypt_valida(senha, encoded):
    try:
        scheme, n_raw, r_raw, p_raw, salt_raw, digest_raw = encoded.split("$", 5)
        if scheme != "scrypt":
            return False
        n_value, r_value, p_value = int(n_raw), int(r_raw), int(p_raw)
        if n_value < 2**14 or n_value > 2**20 or n_value & (n_value - 1):
            return False
        if not 1 <= r_value <= 32 or not 1 <= p_value <= 16:
            return False
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
        if len(salt) < 16 or len(expected) != 32:
            return False
        calculated = hashlib.scrypt(
            (senha or "").encode("utf-8"),
            salt=salt,
            n=n_value,
            r=r_value,
            p=p_value,
            dklen=len(expected),
            maxmem=128 * 1024 * 1024,
        )
        return hmac.compare_digest(calculated, expected)
    except (ValueError, TypeError, UnicodeError):
        return False

def login_valido(usuario, senha):
    usuario_ok = hmac.compare_digest((usuario or "").strip(), maestro_admin_user())
    senha_hash = maestro_admin_password_hash()
    if senha_hash:
        return usuario_ok and _senha_scrypt_valida(senha, senha_hash)
    senha_env = maestro_admin_password()
    if not senha_env:
        return False
    return usuario_ok and hmac.compare_digest(senha or "", senha_env)

def _session_hash(token):
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()

def _load_sessions(now=None):
    current = int(now if now is not None else time.time())
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    if not isinstance(data, dict):
        return {}
    active = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        try:
            expires_at = int(value.get("expires_at", 0) or 0)
        except (TypeError, ValueError):
            continue
        if expires_at > current:
            active[key] = value
    return active

def _protect_session_file_windows(path):
    """Remove ACLs herdadas dos arquivos de autenticacao gerenciados."""
    if not IS_WIN:
        return True
    try:
        candidate = Path(path).resolve()
        managed_dir = (BASE / "dados").resolve()
        managed_names = {SESSION_FILE.name, SESSION_FILE.with_suffix(".tmp").name}
        # Testes usam arquivos temporarios fora do Studio; nunca altere a ACL
        # deles nem de um caminho que tenha sido injetado acidentalmente.
        if candidate.parent != managed_dir or candidate.name not in managed_names:
            return True
        domain = os.environ.get("USERDOMAIN", "").strip()
        username = os.environ.get("USERNAME", "").strip()
        owner = f"{domain}\\{username}" if domain and username else username
        if not owner:
            return False
        completed = subprocess.run(
            [
                "icacls.exe",
                str(candidate),
                "/inheritance:r",
                "/grant:r",
                f"{owner}:(F)",
                "*S-1-5-18:(F)",
                "*S-1-5-32-544:(F)",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return completed.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False

def _save_sessions(sessions):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = SESSION_FILE.with_suffix(".tmp")
    temp.touch(exist_ok=True)
    if not _protect_session_file_windows(temp):
        print("[AUTH] AVISO: nao foi possivel restringir o arquivo temporario de sessoes.")
    temp.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, SESSION_FILE)
    if not _protect_session_file_windows(SESSION_FILE):
        print("[AUTH] AVISO: nao foi possivel restringir o arquivo de sessoes.")

def criar_sessao(usuario, now=None):
    current = int(now if now is not None else time.time())
    token = secrets.token_urlsafe(32)
    with _AUTH_LOCK:
        sessions = _load_sessions(current)
        sessions[_session_hash(token)] = {
            "usuario": usuario,
            "created_at": current,
            "expires_at": current + SESSION_MAX_AGE,
        }
        # O Studio e de um unico proprietario. Limitar sessoes tambem limita o
        # impacto de cookies antigos esquecidos em outros dispositivos.
        ordered = sorted(
            sessions.items(),
            key=lambda item: int(item[1].get("created_at", 0) or 0),
            reverse=True,
        )[:20]
        _save_sessions(dict(ordered))
    return token

def sessao_valida(token, now=None):
    if not token:
        return False
    current = int(now if now is not None else time.time())
    with _AUTH_LOCK:
        sessions = _load_sessions(current)
        record = sessions.get(_session_hash(token))
    if not record:
        return False
    return hmac.compare_digest(str(record.get("usuario", "")), maestro_admin_user())

def revogar_sessao(token, now=None):
    if not token:
        return
    current = int(now if now is not None else time.time())
    with _AUTH_LOCK:
        sessions = _load_sessions(current)
        sessions.pop(_session_hash(token), None)
        _save_sessions(sessions)

def criar_handoff_ferramenta(tool_name, now=None):
    """Cria um codigo de uso unico para entrar numa ferramenta sem compartilhar cookies."""
    config = PUBLIC_TOOL_ROUTES.get((tool_name or "").strip().lower())
    if not config:
        return None
    current = int(now if now is not None else time.time())
    code = secrets.token_urlsafe(32)
    code_hash = _session_hash(code)
    with _AUTH_LOCK:
        expired = [
            key for key, record in _TOOL_HANDOFFS.items()
            if int(record.get("expires_at", 0) or 0) <= current
        ]
        for key in expired:
            _TOOL_HANDOFFS.pop(key, None)
        _TOOL_HANDOFFS[code_hash] = {
            "host": config["host"],
            "tool": tool_name,
            "expires_at": current + TOOL_HANDOFF_MAX_AGE,
        }
    return code, dict(config)

def consumir_handoff_ferramenta(code, request_host, now=None):
    """Consome um handoff uma unica vez e somente no subdominio ao qual foi emitido."""
    if not code or not request_host:
        return None
    current = int(now if now is not None else time.time())
    code_hash = _session_hash(code)
    normalized_host = request_host.strip().lower().split(":", 1)[0]
    with _AUTH_LOCK:
        record = _TOOL_HANDOFFS.get(code_hash)
        if not record:
            return None
        if int(record.get("expires_at", 0) or 0) <= current:
            _TOOL_HANDOFFS.pop(code_hash, None)
            return None
        if not hmac.compare_digest(str(record.get("host", "")), normalized_host):
            return None
        _TOOL_HANDOFFS.pop(code_hash, None)
        return dict(record)

def _cookie_value(cookie_header, name):
    if not cookie_header:
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
        morsel = cookie.get(name)
        return morsel.value if morsel else ""
    except Exception:
        return ""

def _cookie_values(cookie_header, name):
    """Return every exact-name cookie, including duplicates from legacy paths."""
    if not cookie_header:
        return []
    values = []
    for fragment in str(cookie_header).split(";"):
        cookie = SimpleCookie()
        try:
            cookie.load(fragment.strip())
            morsel = cookie.get(name)
            if morsel:
                values.append(morsel.value)
        except Exception:
            continue
    return values

def _cookie_session(cookie_header):
    return _cookie_value(cookie_header, SESSION_COOKIE_NAME)

def _csrf_token_valid(cookie_header, submitted_token):
    submitted = str(submitted_token or "")
    if len(submitted) < 32:
        return False
    return any(
        len(cookie_token) >= 32 and hmac.compare_digest(cookie_token, submitted)
        for cookie_token in _cookie_values(cookie_header, CSRF_COOKIE_NAME)
    )

def _login_csrf_secret():
    """Return a stable signing key without exposing the configured credentials."""
    configured = (
        _env_value("MAESTRO_LOGIN_CSRF_SECRET")
        or token_frontend()
        or maestro_admin_password_hash()
        or maestro_admin_password()
    )
    if not configured:
        return _LOGIN_CSRF_PROCESS_SECRET
    return hashlib.sha256(
        ("maestro-login-csrf-v2\0" + configured).encode("utf-8")
    ).digest()

def _new_login_csrf_token(now=None, nonce=None):
    """Issue a time-limited signed form token independent of browser cookies."""
    issued_at = int(now if now is not None else time.time())
    random_nonce = str(nonce or secrets.token_urlsafe(24))
    payload = f"v2.{issued_at}.{random_nonce}"
    signature = base64.urlsafe_b64encode(
        hmac.new(_login_csrf_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")
    return f"{payload}.{signature}"

def _signed_login_csrf_valid(submitted_token, now=None):
    token = str(submitted_token or "")
    if len(token) < 64 or len(token) > 256:
        return False
    try:
        version, issued_raw, nonce, supplied_signature = token.split(".", 3)
        issued_at = int(issued_raw)
    except (TypeError, ValueError):
        return False
    if version != "v2" or len(nonce) < 20 or len(supplied_signature) != 43:
        return False
    current = int(now if now is not None else time.time())
    if issued_at > current + 30 or current - issued_at > LOGIN_CSRF_MAX_AGE:
        return False
    payload = f"{version}.{issued_at}.{nonce}"
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(_login_csrf_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")
    return hmac.compare_digest(supplied_signature, expected_signature)

def _login_csrf_valid(cookie_header, submitted_token, now=None):
    """Accept the signed form token; retain the old cookie contract for rollout safety."""
    return _signed_login_csrf_valid(submitted_token, now=now) or _csrf_token_valid(
        cookie_header,
        submitted_token,
    )

def _unsafe_request_origin_allowed(authority, origin, fetch_site=""):
    expected = (authority or "").strip().lower()
    supplied_origin = (origin or "").strip()
    normalized_fetch_site = (fetch_site or "").strip().lower()
    if supplied_origin:
        # Chromium can serialize a form's origin as the opaque value ``null``
        # even while its protected Fetch Metadata still proves that the
        # navigation was initiated by this exact origin.  Accept only that
        # browser-authenticated combination.  A sandboxed/file/cross-site page
        # also sends ``Origin: null``, but never with ``Sec-Fetch-Site:
        # same-origin`` for this target, so it remains denied.
        if hmac.compare_digest(supplied_origin, "null"):
            return normalized_fetch_site == "same-origin"
        try:
            parsed = urllib.parse.urlsplit(supplied_origin)
            expected_parsed = urllib.parse.urlsplit(f"//{expected}")
            expected_host = (expected_parsed.hostname or "").lower().rstrip(".")
            origin_host = (parsed.hostname or "").lower().rstrip(".")
            expected_port = expected_parsed.port
            origin_port = parsed.port
        except (TypeError, ValueError):
            return False
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not expected_host
            or not origin_host
            or parsed.username is not None
            or parsed.password is not None
            or expected_parsed.username is not None
            or expected_parsed.password is not None
        ):
            return False
        default_port = 443 if parsed.scheme == "https" else 80
        normalized_expected_port = expected_port or default_port
        normalized_origin_port = origin_port or default_port
        return (
            hmac.compare_digest(origin_host, expected_host)
            and normalized_origin_port == normalized_expected_port
        )
    return normalized_fetch_site != "cross-site"

def _prune_login_failures(current):
    expired = [key for key, times in _LOGIN_FAILURES.items()
               if not times or current - times[-1] >= LOGIN_WINDOW_SECONDS]
    for key in expired:
        del _LOGIN_FAILURES[key]


def _login_retry_after(client_key, now=None):
    current = float(now if now is not None else time.monotonic())
    with _AUTH_LOCK:
        _prune_login_failures(current)
        recent = [stamp for stamp in _LOGIN_FAILURES.get(client_key, [])
                  if current - stamp < LOGIN_WINDOW_SECONDS]
        if client_key not in _LOGIN_FAILURES and len(_LOGIN_FAILURES) >= LOGIN_MAX_CLIENTS:
            return LOGIN_WINDOW_SECONDS
    if len(recent) < LOGIN_MAX_FAILURES:
        return 0
    return max(1, int(LOGIN_WINDOW_SECONDS - (current - recent[0])))


def _record_login_failure(client_key, now=None):
    current = float(now if now is not None else time.monotonic())
    with _AUTH_LOCK:
        _prune_login_failures(current)
        if client_key not in _LOGIN_FAILURES and len(_LOGIN_FAILURES) >= LOGIN_MAX_CLIENTS:
            return
        recent = [stamp for stamp in _LOGIN_FAILURES.get(client_key, [])
                  if current - stamp < LOGIN_WINDOW_SECONDS]
        _LOGIN_FAILURES[client_key] = (recent + [current])[-LOGIN_MAX_FAILURES:]


def _clear_login_failures(client_key):
    with _AUTH_LOCK:
        _LOGIN_FAILURES.pop(client_key, None)

API_PROXY_ROUTES = {
    "cadastro": 8001,
    "cad": 8001,
    "doc": 8002,
    "preenchimento": 8002,
    "conversor": 8003,
    "historico": 8004,
    "hist": 8004,
    "studio": STUDIO_PORT,
    "organizador": 8006,
    "org": 8006,
    "dashboard": 8007,
    "dash": 8007,
    "local-ai": 9740,
}

HEALTH_TARGETS = [
    ("cadastro", "Cadastro", 8001, "/status"),
    ("documental", "Documental", 8002, "/status"),
    ("conversor", "Conversor", 8003, "/status"),
    ("historico", "Historico", 8004, "/status"),
    ("studio", "Studio", STUDIO_PORT, "/api/status"),
    ("generative", "Gerador IA", STUDIO_PORT, "/api/generative/status"),
    ("organizador", "Organizador", 8006, "/status"),
    ("dashboard", "Dashboard", 8007, "/status"),
    ("comfyui", "ComfyUI", 8188, "/system_stats"),
    ("sprunki", "Sprunki", 5005, "/"),
    ("perplexica", "Perplexica", 3002, "/"),
    ("ollama", "Ollama", 11435, "/api/tags"),
    ("hyperframes", "HyperFrames", 8032, "/"),
]

def _json_response(handler, status, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def _proxy_target(api_path):
    for prefix, port in API_PROXY_ROUTES.items():
        base = f"/api/{prefix}"
        if api_path == base or api_path.startswith(base + "/"):
            rest = api_path[len(base):] or "/"
            return f"http://127.0.0.1:{port}{rest}"
    return None

def _proxy_headers(api_path, incoming_headers):
    headers = {}
    blocked = {
        "host",
        "connection",
        "content-length",
        "transfer-encoding",
        "expect",
        "accept-encoding",
        "cookie",
        "authorization",
        "cf-connecting-ip",
        "x-forwarded-for",
        "x-studio-internal-token",
    }
    for key, value in incoming_headers.items():
        if key.lower() not in blocked:
            headers[key] = value

    # O navegador nunca recebe este segredo. Somente o proxy autenticado do
    # Maestro o acrescenta na comunicacao local com o Studio.
    if api_path == "/api/studio" or api_path.startswith("/api/studio/"):
        token = studio_internal_token()
        if token:
            headers["X-Studio-Internal-Token"] = token
    return headers


def _proxy_body_limit(target):
    default_limit = int(_env_value("MAESTRO_MAX_PROXY_BYTES", str(8 * 1024 * 1024 * 1024)))
    path = urllib.parse.unquote(urllib.parse.urlsplit(target).path).rstrip("/")
    if re.fullmatch(r"/api/video-projects/[^/]+/cinema/elements", path):
        return min(default_limit, 8 * 1024**2 + 64 * 1024)
    if re.fullmatch(r"/api/video-projects/[^/]+/cinema/(?:direction|chat(?:/.*)?)", path):
        return min(default_limit, 64 * 1024)
    if path == "/api/dictation/transcriptions":
        dictation_limit = int(_env_value("MAESTRO_DICTATION_MAX_BYTES", str(16 * 1024 * 1024)))
        return min(default_limit, max(1024 * 1024, dictation_limit))
    return default_limit

def _cookie_without_maestro(cookie_header):
    """Mantem cookies da ferramenta, mas nunca entrega a sessao do Maestro ao upstream."""
    if not cookie_header:
        return ""
    kept = []
    for part in cookie_header.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name.strip() and name.strip() != SESSION_COOKIE_NAME:
            kept.append(f"{name.strip()}={value}")
    return "; ".join(kept)

def _tool_proxy_headers(incoming_headers, public_host, secure):
    headers = {}
    blocked = {
        "host",
        "connection",
        "content-length",
        "transfer-encoding",
        "expect",
        "accept-encoding",
        "cookie",
        "cf-connecting-ip",
        "x-forwarded-for",
        "x-forwarded-host",
        "x-forwarded-proto",
        "x-studio-internal-token",
    }
    for key, value in incoming_headers.items():
        if key.lower() not in blocked:
            headers[key] = value
    tool_cookies = _cookie_without_maestro(incoming_headers.get("Cookie", ""))
    if tool_cookies:
        headers["Cookie"] = tool_cookies
    headers["X-Forwarded-Host"] = public_host
    headers["X-Forwarded-Proto"] = "https" if secure else "http"
    return headers

def _request_json(url, timeout=2):
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(4096)
        latency = int((time.time() - started) * 1000)
        detail = ""
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
            if isinstance(parsed, dict):
                detail = parsed.get("status") or parsed.get("servico") or parsed.get("ok") or ""
                if isinstance(detail, bool):
                    detail = "online" if detail else "offline"
        except Exception:
            detail = "online"
        return True, latency, str(detail)
    except Exception as exc:
        latency = int((time.time() - started) * 1000)
        return False, latency, str(exc)[:160]

def maestro_health():
    services = []
    for ident, label, port, path in HEALTH_TARGETS:
        ok, latency, detail = _request_json(f"http://127.0.0.1:{port}{path}", timeout=2)
        services.append({
            "id": ident,
            "label": label,
            "port": port,
            "online": ok,
            "status": "online" if ok else "off",
            "latency_ms": latency,
            "detail": detail,
        })
    online_count = sum(1 for item in services if item["online"])
    all_online = bool(services) and online_count == len(services)
    return {
        "ok": all_online,
        "status": "online" if all_online else ("degraded" if online_count else "offline"),
        "online_count": online_count,
        "total_count": len(services),
        "frontend_port": PORT_APP,
        "services": services,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

def porta_em_uso(porta, host="127.0.0.1", timeout=0.5):
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except Exception:
        return False

#  Servidor HTTP do frontend HTML 
class ServidorFrontend:
    def __init__(self):
        self.httpd = None

    def iniciar(self):
        if porta_em_uso(PORT_APP):
            print(f"  [Frontend        ] 127.0.0.1:{PORT_APP}  ja estava em uso")
            return
        import http.server, socketserver
        os.chdir(str(APP_DIR))
        class Handler(http.server.SimpleHTTPRequestHandler):
            server_version = "PemaraGateway"
            sys_version = ""

            def log_message(self, *a): pass

            def _auth_state(self, parsed_path):
                session_token = _cookie_session(self.headers.get('Cookie', ''))
                return sessao_valida(session_token), session_token

            def _request_host(self):
                return self.headers.get("Host", "").strip().lower().split(":", 1)[0]

            def _request_authority(self):
                return self.headers.get("Host", "").strip().lower()

            def _request_is_secure(self):
                forwarded = self.headers.get("X-Forwarded-Proto", "")
                if forwarded.split(",", 1)[0].strip().lower() == "https":
                    return True
                return self._request_host() in PUBLIC_GATEWAY_HOSTS

            def _session_cookie(self, token, max_age=SESSION_MAX_AGE):
                secure = "; Secure" if self._request_is_secure() else ""
                return (
                    f"{SESSION_COOKIE_NAME}={token}; Path=/; Max-Age={max_age}; "
                    f"HttpOnly; SameSite=Strict{secure}"
                )

            def _csrf_cookie(self, token, max_age=600, path="/"):
                secure = "; Secure" if self._request_is_secure() else ""
                return (
                    f"{CSRF_COOKIE_NAME}={token}; Path={path}; Max-Age={max_age}; "
                    f"HttpOnly; SameSite=Strict{secure}"
                )

            def _client_key(self):
                peer = str(self.client_address[0])
                try:
                    if ipaddress.ip_address(peer).is_loopback and self.headers.get("CF-Ray"):
                        return str(ipaddress.ip_address(self.headers.get("CF-Connecting-IP", "")))
                except ValueError:
                    pass
                return peer

            def _login_page(self, erro="", status=200, retry_after=0):
                csrf_token = _new_login_csrf_token()
                erro_html = (
                    f"<p class='login-error'>{html.escape(erro)}</p>"
                    if erro else ""
                )
                body = (
                    "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
                    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                    "<title>Login Maestro</title>"
                    "<link rel='stylesheet' href='/assets/auth.css'></head>"
                    "<body class='login-body'>"
                    "<div class='login-watermark' aria-hidden='true'></div>"
                    "<header class='login-header'><img src='/assets/brand/pemara-tech-logo.png' alt='Pemara Tech'></header>"
                    "<main class='login-card'>"
                    "<div class='login-kicker'>Maestro Pro</div>"
                    "<h1>Acesso protegido</h1>"
                    "<p>Sistema Pemara protegido.</p>"
                    + erro_html +
                    "<form method='post' action='/login' class='login-form'>"
                    f"<input type='hidden' name='csrf_token' value='{html.escape(csrf_token)}'>"
                    "<label>Usuario"
                    "<input name='usuario' autocomplete='username' autofocus></label>"
                    "<label>Senha"
                    "<input name='senha' type='password' autocomplete='current-password'></label>"
                    "<button type='submit'>Entrar</button>"
                    "</form>"
                    "</main>"
                    "<footer class='login-footer'><img src='/assets/brand/pemara-tech-logo.png' alt='Pemara Tech'><span>Maestro Pro</span></footer>"
                    "</body></html>"
                ).encode("utf-8")
                self._strict_csp_response = True
                self.send_response(status)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                # Instalacoes anteriores criavam o CSRF em /login. Se também
                # existir um cookie homônimo em /, alguns navegadores enviam
                # ambos e o parser pode selecionar o token velho. Apague a
                # variante legada e mantenha uma única origem em /.
                self.send_header(
                    'Set-Cookie',
                    self._csrf_cookie('', max_age=0, path='/login'),
                )
                self.send_header(
                    'Set-Cookie',
                    self._csrf_cookie(csrf_token, path='/'),
                )
                if retry_after:
                    self.send_header('Retry-After', str(retry_after))
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _handle_login(self):
                client_key = self._client_key()
                retry_after = _login_retry_after(client_key)
                if retry_after:
                    self._login_page(
                        "Muitas tentativas. Aguarde alguns minutos e tente novamente.",
                        status=429,
                        retry_after=retry_after,
                    )
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0") or "0")
                except ValueError:
                    length = -1
                if length < 0 or length > 16384:
                    self._login_page("Requisicao de login invalida.", status=413)
                    return
                body = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
                data = urllib.parse.parse_qs(body)
                csrf_token = data.get("csrf_token", [""])[0]
                if not _login_csrf_valid(self.headers.get("Cookie", ""), csrf_token):
                    self._login_page("Requisicao de login invalida.", status=403)
                    return
                usuario = data.get("usuario", [""])[0]
                senha = data.get("senha", [""])[0]
                if login_valido(usuario, senha):
                    _clear_login_failures(client_key)
                    session_token = criar_sessao(maestro_admin_user())
                    self.send_response(302)
                    self.send_header('Set-Cookie', self._session_cookie(session_token))
                    self.send_header('Location', '/?v=maestro-pro-refatorado')
                    self.end_headers()
                    return
                _record_login_failure(client_key)
                self._login_page("Usuario ou senha invalidos.", status=401)

            def _logout(self):
                session_token = _cookie_session(self.headers.get('Cookie', ''))
                revogar_sessao(session_token)
                self.send_response(302)
                self.send_header('Set-Cookie', self._session_cookie('', max_age=0))
                self.send_header('Location', '/login')
                self.end_headers()

            def _tool_handoff(self, parsed_path, tool_route, authenticated=False, session_token=""):
                if self.command != "GET":
                    _json_response(self, 405, {"ok": False, "erro": "Metodo nao permitido"})
                    return
                code = urllib.parse.parse_qs(parsed_path.query).get("code", [""])[0]
                handoff = consumir_handoff_ferramenta(code, self._request_host())
                if not handoff or handoff.get("tool") != tool_route.get("name"):
                    self._login_page(
                        "O acesso rapido expirou ou ja foi usado. Entre novamente.",
                        status=401,
                    )
                    return
                self.send_response(302)
                # Se este navegador ja entrou antes neste subdominio, preserve a
                # sessao existente em vez de consumir vagas com um novo token.
                if not authenticated or not session_token:
                    session_token = criar_sessao(maestro_admin_user())
                    self.send_header("Set-Cookie", self._session_cookie(session_token))
                self.send_header("Location", "/")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()

            def _tool_link(self, parsed_path):
                if self.command != "GET":
                    _json_response(self, 405, {"ok": False, "erro": "Metodo nao permitido"})
                    return
                tool_name = urllib.parse.parse_qs(parsed_path.query).get("tool", [""])[0]
                created = criar_handoff_ferramenta(tool_name)
                if not created:
                    _json_response(self, 404, {"ok": False, "erro": "Ferramenta desconhecida"})
                    return
                code, config = created
                query = urllib.parse.urlencode({"code": code})
                _json_response(self, 200, {
                    "ok": True,
                    "tool": tool_name,
                    "url": f"https://{config['host']}/login/handoff?{query}",
                    "expires_in": TOOL_HANDOFF_MAX_AGE,
                })

            def _rewrite_tool_location(self, value, target_parts, public_host):
                if not value:
                    return value
                parsed = urllib.parse.urlsplit(value)
                if not parsed.scheme or not parsed.netloc:
                    return value
                internal_hosts = {
                    target_parts.netloc.lower(),
                    f"localhost:{target_parts.port}",
                    f"127.0.0.1:{target_parts.port}",
                }
                if parsed.netloc.lower() not in internal_hosts:
                    return value
                scheme = "https" if self._request_is_secure() else "http"
                return urllib.parse.urlunsplit((scheme, public_host, parsed.path, parsed.query, parsed.fragment))

            def _proxy_http(self, target, headers, tool_mode=False, public_host=""):
                self._tool_proxy_response = bool(tool_mode)
                self._preserve_upstream_cache = False
                try:
                    length = int(self.headers.get("Content-Length", "0") or "0")
                except ValueError:
                    _json_response(self, 400, {"ok": False, "erro": "Content-Length invalido"})
                    return
                max_proxy_bytes = _proxy_body_limit(target)
                if length < 0 or length > max_proxy_bytes:
                    _json_response(self, 413, {"ok": False, "erro": "Arquivo maior que o limite do Maestro"})
                    return

                response_started = False
                connection = None
                try:
                    target_parts = urllib.parse.urlsplit(target)
                    connection = http.client.HTTPConnection(
                        target_parts.hostname,
                        target_parts.port,
                        timeout=900,
                    )
                    target_path = target_parts.path or "/"
                    if target_parts.query:
                        target_path += "?" + target_parts.query
                    connection.putrequest(self.command, target_path, skip_host=True)
                    connection.putheader(
                        "Host",
                        public_host if tool_mode else f"{target_parts.hostname}:{target_parts.port}",
                    )
                    for key, value in headers.items():
                        connection.putheader(key, value)
                    if length:
                        connection.putheader("Content-Length", str(length))
                    connection.endheaders()

                    remaining = length
                    while remaining > 0:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ConnectionError("Upload encerrado antes do Content-Length informado")
                        connection.send(chunk)
                        remaining -= len(chunk)

                    response = connection.getresponse()
                    self.send_response(response.status)
                    basic_response_headers = {
                        "content-type", "content-disposition", "x-filename",
                        "content-range", "accept-ranges", "etag", "last-modified",
                        "cache-control", "x-maestro-review-asset",
                    }
                    tool_response_headers = basic_response_headers | {
                        "location", "set-cookie", "cache-control", "expires", "pragma",
                        "vary", "content-language", "content-encoding",
                        "content-security-policy",
                    }
                    allowed_headers = tool_response_headers if tool_mode else basic_response_headers
                    self._preserve_upstream_cache = bool(
                        response.getheader("Cache-Control")
                    )
                    for key, value in response.getheaders():
                        lower_key = key.lower()
                        if lower_key not in allowed_headers:
                            continue
                        if lower_key == "set-cookie":
                            cookie_name = value.split("=", 1)[0].strip()
                            if cookie_name == SESSION_COOKIE_NAME:
                                continue
                        if lower_key == "location" and tool_mode:
                            value = self._rewrite_tool_location(value, target_parts, public_host)
                        self.send_header(key, value)
                    content_length = response.getheader("Content-Length")
                    if content_length:
                        self.send_header("Content-Length", content_length)
                    self.end_headers()
                    response_started = True
                    if self.command != "HEAD":
                        while True:
                            reader = getattr(response, "read1", response.read)
                            chunk = reader(64 * 1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                except Exception as exc:
                    print(f"Falha interna no proxy Maestro para {urllib.parse.urlsplit(target).path}: {exc}")
                    if not response_started:
                        _json_response(self, 502, {"ok": False, "erro": "Servico interno indisponivel"})
                finally:
                    if connection is not None:
                        connection.close()

            def _proxy_tool(self, parsed_path, tool_route):
                self._tool_proxy_name = tool_route.get("name", "")
                target_path = parsed_path.path or "/"
                if parsed_path.query:
                    target_path += "?" + parsed_path.query
                public_host = tool_route["host"]
                headers = _tool_proxy_headers(
                    self.headers,
                    public_host,
                    self._request_is_secure(),
                )
                headers["X-Forwarded-For"] = self._client_key()
                target = f"http://127.0.0.1:{tool_route['port']}{target_path}"
                self._proxy_http(target, headers, tool_mode=True, public_host=public_host)

            def _is_websocket_upgrade(self):
                upgrade = self.headers.get("Upgrade", "").strip().lower()
                connection = self.headers.get("Connection", "").lower()
                return self.command == "GET" and upgrade == "websocket" and "upgrade" in connection

            def _proxy_tool_websocket(self, parsed_path, tool_route):
                upstream = None
                response_started = False
                try:
                    upstream = socket.create_connection(("127.0.0.1", tool_route["port"]), timeout=10)
                    target_path = parsed_path.path or "/"
                    if parsed_path.query:
                        target_path += "?" + parsed_path.query
                    lines = [f"GET {target_path} HTTP/1.1"]
                    blocked = {
                        "host", "cookie", "cf-connecting-ip", "x-forwarded-for",
                        "x-forwarded-host", "x-forwarded-proto", "x-studio-internal-token",
                        "origin",
                    }
                    for key, value in self.headers.items():
                        if key.lower() not in blocked:
                            lines.append(f"{key}: {value}")
                    tool_cookies = _cookie_without_maestro(self.headers.get("Cookie", ""))
                    if tool_cookies:
                        lines.append(f"Cookie: {tool_cookies}")
                    lines.extend([
                        f"Host: 127.0.0.1:{tool_route['port']}",
                        f"Origin: http://127.0.0.1:{tool_route['port']}",
                        f"X-Forwarded-Host: {tool_route['host']}",
                        f"X-Forwarded-Proto: {'https' if self._request_is_secure() else 'http'}",
                        f"X-Forwarded-For: {self._client_key()}",
                        "", "",
                    ])
                    upstream.sendall("\r\n".join(lines).encode("iso-8859-1", errors="replace"))

                    response_header = b""
                    while b"\r\n\r\n" not in response_header:
                        chunk = upstream.recv(4096)
                        if not chunk:
                            raise ConnectionError("WebSocket interno encerrou durante o handshake")
                        response_header += chunk
                        if len(response_header) > 65536:
                            raise ConnectionError("Handshake WebSocket interno excedeu o limite")
                    header_bytes, remainder = response_header.split(b"\r\n\r\n", 1)
                    header_bytes += b"\r\n\r\n"
                    self.connection.sendall(header_bytes)
                    response_started = True
                    if remainder:
                        self.connection.sendall(remainder)

                    status_line = header_bytes.split(b"\r\n", 1)[0]
                    if b" 101 " not in status_line:
                        while True:
                            chunk = upstream.recv(65536)
                            if not chunk:
                                break
                            self.connection.sendall(chunk)
                        return

                    upstream.settimeout(None)
                    self.connection.settimeout(None)
                    while True:
                        readable, _, _ = select.select([self.connection, upstream], [], [], 60)
                        if not readable:
                            continue
                        for source in readable:
                            data = source.recv(65536)
                            if not data:
                                return
                            destination = upstream if source is self.connection else self.connection
                            destination.sendall(data)
                except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                    if not response_started:
                        print(f"Falha interna no WebSocket Maestro para {parsed_path.path}: {exc}")
                        _json_response(self, 502, {"ok": False, "erro": "WebSocket interno indisponivel"})
                finally:
                    if upstream is not None:
                        try:
                            upstream.close()
                        except OSError:
                            pass

            def _proxy_api(self, parsed_path):
                if parsed_path.path == "/api/maestro/health":
                    _json_response(self, 200, maestro_health())
                    return

                if parsed_path.path == "/api/maestro/tool-link":
                    self._tool_link(parsed_path)
                    return

                target = _proxy_target(parsed_path.path)
                if not target:
                    _json_response(self, 404, {"ok": False, "erro": "Rota de API desconhecida"})
                    return
                if parsed_path.query:
                    target += "?" + parsed_path.query
                headers = _proxy_headers(parsed_path.path, self.headers)
                self._proxy_http(target, headers)

            def _handle_request(self):
                self._tool_proxy_response = False
                self._tool_proxy_name = ""
                parsed_path = urllib.parse.urlparse(self.path)
                request_host = self._request_host()
                tool_route = PUBLIC_TOOL_HOSTS.get(request_host)
                if (
                    request_host == "maestro.pemaratech.com.br"
                    and self._request_authority() == HYPERFRAMES_FALLBACK_AUTHORITY
                ):
                    tool_route = HYPERFRAMES_FALLBACK_ROUTE

                if request_host not in ALLOWED_GATEWAY_HOSTS:
                    _json_response(self, 421, {"ok": False, "erro": "Host desconhecido"})
                    return

                origin_allowed = _unsafe_request_origin_allowed(
                    self._request_authority(),
                    self.headers.get("Origin", ""),
                    self.headers.get("Sec-Fetch-Site", ""),
                )
                if (
                    self.command not in {"GET", "HEAD", "OPTIONS"}
                    and not origin_allowed
                ):
                    # Registre apenas metadados de roteamento. Nunca inclua corpo,
                    # usuario, senha, cookies ou tokens neste diagnostico.
                    routing_context = {
                        "authority": self._request_authority()[:200],
                        "origin": self.headers.get("Origin", "")[:200],
                        "sec_fetch_site": self.headers.get("Sec-Fetch-Site", "")[:40],
                        "forwarded_host": self.headers.get("X-Forwarded-Host", "")[:200],
                        "forwarded_proto": self.headers.get("X-Forwarded-Proto", "")[:40],
                    }
                    print(
                        "[Security] Origem de requisicao recusada: "
                        + json.dumps(routing_context, ensure_ascii=True, sort_keys=True)
                    )
                    _json_response(self, 403, {"ok": False, "erro": "Origem da requisicao nao permitida"})
                    return

                https_target = _https_redirect_target(
                    request_host,
                    self.headers.get("X-Forwarded-Proto", ""),
                    self.path,
                )
                if https_target:
                    self.send_response(308)
                    self.send_header("Location", https_target)
                    self.end_headers()
                    return

                authenticated, session_token = self._auth_state(parsed_path)

                if parsed_path.path == "/login/handoff":
                    if not tool_route:
                        _json_response(self, 404, {"ok": False, "erro": "Rota desconhecida"})
                    else:
                        self._tool_handoff(
                            parsed_path,
                            tool_route,
                            authenticated=authenticated,
                            session_token=session_token,
                        )
                    return

                if parsed_path.path == "/login":
                    if self.command == "POST":
                        self._handle_login()
                    else:
                        self._login_page()
                    return

                if parsed_path.path == "/logout":
                    if self.command == "POST":
                        self._logout()
                    else:
                        _json_response(self, 405, {"ok": False, "erro": "Use POST para sair"})
                    return

                safe_asset_path = posixpath.normpath(urllib.parse.unquote(parsed_path.path))
                if (
                    not authenticated
                    and safe_asset_path.startswith("/assets/")
                    and self.command in ("GET", "HEAD")
                ):
                    self._strict_csp_response = True
                    super().do_GET()
                    return

                if not authenticated and parsed_path.path.startswith("/api/"):
                    _json_response(self, 401, {"ok": False, "erro": "Autenticacao necessaria"})
                    return

                if not authenticated:
                    self._login_page()
                    return

                if tool_route:
                    if self._is_websocket_upgrade():
                        self._proxy_tool_websocket(parsed_path, tool_route)
                    else:
                        self._proxy_tool(parsed_path, tool_route)
                    return

                if parsed_path.path.startswith("/api/"):
                    self._proxy_api(parsed_path)
                    return

                if self.command == "GET":
                    super().do_GET()
                else:
                    _json_response(self, 405, {"ok": False, "erro": "Metodo nao permitido"})

            def do_GET(self): self._handle_request()
            def do_POST(self): self._handle_request()
            def do_PUT(self): self._handle_request()
            def do_PATCH(self): self._handle_request()
            def do_DELETE(self): self._handle_request()
            def do_HEAD(self): self._handle_request()

            def end_headers(self):
                if getattr(self, "_tool_proxy_response", False):
                    # As ferramentas possuem bundles e politicas proprias. Aplicar o CSP
                    # do Maestro aqui quebraria scripts, workers e WebSockets delas.
                    if getattr(self, "_tool_proxy_name", "") == "hyperframes":
                        self.send_header(
                            'Content-Security-Policy',
                            "frame-ancestors https://maestro.pemaratech.com.br http://127.0.0.1:9501 http://localhost:9501",
                        )
                    else:
                        self.send_header('X-Frame-Options', 'SAMEORIGIN')
                    self.send_header('Referrer-Policy', 'same-origin')
                else:
                    if not getattr(self, "_preserve_upstream_cache", False):
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.send_header('Pragma', 'no-cache')
                        self.send_header('Expires', '0')
                    if getattr(self, "_strict_csp_response", False):
                        csp = "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; img-src 'self' data:; script-src 'none'; style-src 'self'"
                    else:
                        csp = "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; frame-src https://hyperframes.pemaratech.com.br https://maestro.pemaratech.com.br:8443 http://127.0.0.1:8032 http://localhost:8032; form-action 'self'; object-src 'none'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self' https://cloudflareinsights.com; script-src 'self' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline'"
                    self.send_header('Content-Security-Policy', csp)
                    self.send_header('X-Frame-Options', 'DENY')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
                self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
                if self._request_is_secure():
                    self.send_header('Strict-Transport-Security', 'max-age=31536000')
                super().end_headers()
                
        class GatewayThreadingServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
            # ComfyUI e Perplexica carregam dezenas de modulos em paralelo.
            # O backlog padrao (5) fazia o tunel receber connection refused.
            request_queue_size = 128

        self.httpd = GatewayThreadingServer(("127.0.0.1", PORT_APP), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def parar(self):
        if self.httpd: self.httpd.shutdown()


#  API para o frontend (pywebview) 
class PemaraAPI:
    def abrir_url(self, url):
        import webbrowser
        webbrowser.open(url)
    def get_version(self):
        return "4.0"
    def selecionar_pasta(self):
        import webview
        try:
            if webview.windows:
                resultado = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
                if resultado and isinstance(resultado, tuple) and len(resultado) > 0:
                    return resultado[0]
        except Exception as e:
            print(f"Erro no filedialog: {e}")
        return ""


#  Microserviaos FastAPI 
SERVICOS = [
    ("Cadastro",      8001, "services/cadastro"),
    ("Preenchimento", 8002, "services/preenchimento"),
    ("Conversor",     8003, "services/conversor"),
    ("Historico",     8004, "services/historico"),
    ("Studio",        STUDIO_PORT, "services/studio"),
    ("Organizador",   8006, "services/organizador"),
    ("Dashboard",     8007, "services/dashboard"),
]

_processos = []

def iniciar_servicos():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    logs = BASE / "dados" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    hide = 0x08000000 if IS_WIN else 0

    for nome, porta, app_dir in SERVICOS:
        log_file = logs / f"svc_{nome.lower()}.log"
        if porta_em_uso(porta):
            print(f"  [{nome:15s}] 127.0.0.1:{porta}  ja estava em uso")
            continue
        service_python = sys.executable
        service_env = env.copy()
        if nome == "Studio":
            candidate = _env_value("PEMARA_STUDIO_WEB_PYTHON", "").strip()
            runtime_file = BASE / "sistema" / "studio-web-runtime.json"
            if not candidate and runtime_file.is_file():
                candidate = json.loads(runtime_file.read_text(encoding="utf-8"))["python"]
            if candidate:
                interpreter = Path(candidate)
                if not interpreter.is_absolute() or not interpreter.is_file():
                    raise RuntimeError("Interpretador do Studio configurado incorretamente.")
                service_python = str(interpreter)
                service_env["PEMARA_STUDIO_MEDIA_PYTHON"] = sys.executable
        cmd = [service_python, "-m", "uvicorn", "main:app",
               "--host", "127.0.0.1", "--port", str(porta),
               "--app-dir", str(BASE / app_dir), "--log-level", "warning"]
        with open(log_file, "a", encoding="utf-8") as f:
            p = subprocess.Popen(cmd, env=service_env, stdout=f, stderr=f,
                                 creationflags=hide)
        _processos.append(p)
        print(f"  [{nome:15s}] 127.0.0.1:{porta}  PID {p.pid}")


#  Ferramentas externas 
def npm_cmd():
    return "npm.cmd" if IS_WIN else "npm"

def _comfy_local_only_ok():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=3) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        system = data.get("system", {})
        if system.get("comfyui_version") != COMFY_EXPECTED_VERSION:
            return False
        if system.get("pytorch_version") != COMFY_EXPECTED_TORCH:
            return False
        argv = system.get("argv", [])
        if "--listen" in argv:
            idx = argv.index("--listen")
            if idx + 1 < len(argv) and argv[idx + 1] in ("0.0.0.0", "::"):
                return False
        expected_main = str((COMFY_RUNTIME_ROOT / "main.py").resolve()).casefold()
        actual_main = str(argv[0] if argv else "").replace("/", "\\").casefold()
        if actual_main != expected_main.replace("/", "\\"):
            return False
        return True
    except Exception:
        return False

def iniciar_ferramentas_externas():
    env  = os.environ.copy()
    logs = BASE / "dados" / "logs"
    hide = 0x08000000 if IS_WIN else 0

    # ComfyUI (:8188)
    comfy = COMFY_RUNTIME_ROOT / "main.py"
    if comfy.exists() and COMFY_RUNTIME_PYTHON.is_file():
        if _comfy_local_only_ok():
            print(
                f"  [ComfyUI         ] 127.0.0.1:8188  "
                f"v{COMFY_EXPECTED_VERSION} / torch {COMFY_EXPECTED_TORCH} saudavel"
            )
        elif porta_em_uso(8188):
            print(
                "  [ComfyUI         ] 127.0.0.1:8188  ocupado por runtime "
                "incompativel; use tools/start_comfy_runtime.ps1 apos encerrar o PID exato"
            )
        else:
            COMFY_USER_DIRECTORY.mkdir(parents=True, exist_ok=True)
            for directory in (COMFY_IO_ROOT / "input", COMFY_IO_ROOT / "output", COMFY_IO_ROOT / "temp"):
                directory.mkdir(parents=True, exist_ok=True)
            log = logs / "comfyui.log"
            with open(log, "a") as f:
                p = subprocess.Popen(
                    [
                        str(COMFY_RUNTIME_PYTHON),
                        str(comfy),
                        "--listen", "127.0.0.1",
                        "--port", "8188",
                        "--cuda-device", "0",
                        "--user-directory", str(COMFY_USER_DIRECTORY),
                        "--input-directory", str(COMFY_IO_ROOT / "input"),
                        "--output-directory", str(COMFY_IO_ROOT / "output"),
                        "--temp-directory", str(COMFY_IO_ROOT / "temp"),
                    ],
                    cwd=str(comfy.parent), env=env, stdout=f, stderr=f,
                    creationflags=hide)
            _processos.append(p)
            print(
                f"  [ComfyUI         ] 127.0.0.1:8188  PID {p.pid} "
                f"v{COMFY_EXPECTED_VERSION} / torch {COMFY_EXPECTED_TORCH}"
            )
    else:
        print(
            "  [ComfyUI         ] ::8188  runtime versionado ausente: "
            f"{comfy} / {COMFY_RUNTIME_PYTHON}"
        )

    # HyperFrames Studio (:8032) - composicao e render por software.
    hyperframes_root = (
        BASE / "ferramentas" / "video_global_engine" / "engines" / "hyperframes"
    )
    hyperframes_cli = (
        hyperframes_root / "node_modules" / ".bin" /
        ("hyperframes.cmd" if IS_WIN else "hyperframes")
    )
    hyperframes_project = hyperframes_root / "projects" / "maestro-pilot"
    if hyperframes_cli.exists() and hyperframes_project.exists():
        if porta_em_uso(8032):
            print(f"  [HyperFrames     ] 127.0.0.1:8032  ja estava em uso")
        else:
            log = logs / "hyperframes.log"
            with open(log, "a", encoding="utf-8") as f:
                p = subprocess.Popen(
                    [
                        str(hyperframes_cli),
                        "preview",
                        str(hyperframes_project),
                        "--port", "8032",
                        "--no-open",
                        "--no-browser-gpu",
                    ],
                    cwd=str(hyperframes_root), env=env, stdout=f, stderr=f,
                    creationflags=hide,
                )
            _processos.append(p)
            print(f"  [HyperFrames     ] 127.0.0.1:8032  PID {p.pid}")
    else:
        print(f"  [HyperFrames     ] 127.0.0.1:8032  nao instalado")

    # Perplexica (:3002)
    perp_pkg = BASE / "ferramentas" / "perplexica" / "package.json"
    if perp_pkg.exists() and shutil.which("node"):
        if porta_em_uso(3002):
            print(f"  [Perplexica      ] 127.0.0.1:3002  ja estava em uso")
        else:
            log = logs / "perplexica.log"
            with open(log, "a") as f:
                cmd = [npm_cmd(), "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3002"]
                p = subprocess.Popen(
                    cmd, cwd=str(perp_pkg.parent), env=env,
                    stdout=f, stderr=f, creationflags=hide)
            _processos.append(p)
            print(f"  [Perplexica      ] 127.0.0.1:3002  PID {p.pid}")
    else:
        print(f"  [Perplexica      ] 127.0.0.1:3002  nao instalado")

    # TripoSG (:7860)  inicia app.py ou app_gradio.py
    for app_name in ["app.py", "app_gradio.py", "demo.py"]:
        tripo_app = BASE / "ferramentas" / "triposg" / app_name
        if tripo_app.exists():
            if porta_em_uso(7860):
                print(f"  [TripoSG         ] ::7860  ja estava em uso")
            else:
                log = logs / "triposg.log"
                with open(log, "a") as f:
                    p = subprocess.Popen(
                        [sys.executable, str(tripo_app), "--server-port", "7860"],
                        cwd=str(tripo_app.parent), env=env,
                        stdout=f, stderr=f, creationflags=hide)
                _processos.append(p)
                print(f"  [TripoSG         ] ::7860  PID {p.pid}")
            break
    else:
        print(f"  [TripoSG         ] ::7860  nao instalado")

    # Sprunki Generator (:5005)
    sprunki = BASE / "ferramentas" / "gerador_sprunki" / "app.py"
    if sprunki.exists():
        if porta_em_uso(5005):
            print(f"  [Gerador Sprunki ] 127.0.0.1:5005  ja estava em uso")
        else:
            log = logs / "sprunki.log"
            with open(log, "a", encoding="utf-8") as f:
                sprunki_env = env.copy()
                sprunki_env["SPRUNKI_HOST"] = "127.0.0.1"
                p = subprocess.Popen(
                    [sys.executable, str(sprunki)],
                    cwd=str(sprunki.parent), env=sprunki_env, stdout=f, stderr=f,
                    creationflags=hide)
            _processos.append(p)
            print(f"  [Gerador Sprunki ] 127.0.0.1:5005  PID {p.pid}")
    else:
        print(f"  [Gerador Sprunki ] 127.0.0.1:5005  nao instalado")

    # AnythingLLM  a app desktop, sa abre quando usuario clica
    print(f"  [AnythingLLM     ] app desktop  clique na sidebar para abrir")



    # Ollama  inicia automaticamente em background se instalado
    _iniciar_ollama_background()


def _iniciar_ollama_background():
    """Tenta iniciar o Ollama silenciosamente. Nao falha se nao encontrar."""
    import shutil as _sh
    # Prefere a instalacao isolada e completa usada pelo Editor IA.
    candidatos = [
        r"C:\PemaraAI\ollama\ollama.exe",
        _sh.which("ollama"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Ollama\ollama.exe"),
        os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
    ]
    exe = next((c for c in candidatos if c and os.path.isfile(c)), None)

    if not exe:
        print(f"  [Ollama          ] nao instalado  baixe em https://ollama.com/download")
        return

    # Verifica se ja esta rodando
    try:
        import urllib.request as _ur
        _ur.urlopen("http://127.0.0.1:11435/api/tags", timeout=2)
        print(f"  [Ollama          ] ja estava rodando")
        return
    except Exception:
        pass

    # Inicia sem janela
    hide = 0x08000000 if IS_WIN else 0
    try:
        ollama_env = os.environ.copy()
        ollama_env["OLLAMA_HOST"] = "127.0.0.1:11435"
        ollama_env.setdefault(
            "OLLAMA_MODELS",
            os.path.join(os.path.expanduser("~"), ".ollama", "models"),
        )
        subprocess.Popen(
            [exe, "serve"],
            cwd=os.path.dirname(exe),
            env=ollama_env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=hide
        )
        print(f"  [Ollama          ] iniciado em background  {exe}")
    except Exception as e:
        print(f"  [Ollama          ] erro ao iniciar: {e}")


def _ping(porta):
    import urllib.request, urllib.error
    try:
        urllib.request.urlopen(f"http://localhost:{porta}/status", timeout=1)
        return True
    except Exception:
        return False


def aguardar_servicos():
    print("  Aguardando serviaos craticos (8001, 8007):")
    timeout = 30
    passos = 30
    for i in range(passos + 1):
        if _ping(8001) and _ping(8007):
            barra = "#" * passos
            print(f"\r  [{barra}] 100% :: Prontos!     ", flush=True)
            print()
            return
        
        pct = int((i / passos) * 100)
        feito = i
        vazio = passos - i
        barra = "#" * feito + "." * vazio
        print(f"\r  [{barra}] {pct}%", end="", flush=True)
        time.sleep(1) # Total 30 segundos
    
    # Timeout -> Erro Cratico
    print("\033[91m") # ANSI Vermelho
    print("\n" + "!"*60)
    print("  ERRO CRaTICO: O BACKEND COLAPSOU!")
    print("  Os serviaos (8001, 8007) nao responderam no tempo limite.")
    print("  Leia os arquivos em: dados/logs/")
    print("!"*60 + "\033[0m")
    sys.exit(1)


def main():
    print("\n" + "="*50)
    print("  PEMARA UNIVERSAL v4.0")
    print("="*50)

    for d in ["dados/database","dados/logs","dados/entrada","dados/saida"]:
        (BASE / d).mkdir(parents=True, exist_ok=True)

    frontend_only = _env_value("MAESTRO_FRONTEND_ONLY", "").strip().lower() in {
        "1", "true", "yes", "on",
    }
    if frontend_only:
        print("\n  [Frontend] Reinicio isolado: motores e microservicos preservados.")
    else:
        print("\nMicroserviaos Python:")
        iniciar_servicos()

        print("\nFerramentas externas:")
        iniciar_ferramentas_externas()

    srv = ServidorFrontend()
    srv.iniciar()
    print(f"\n  Frontend em 127.0.0.1:{PORT_APP}")
    if not frontend_only:
        aguardar_servicos()

    url_app = f"http://127.0.0.1:{PORT_APP}/index.html"

    print(f"\n  [SISTEMA] Servidor Master online.")
    print(f"  [SISTEMA] Acesse localmente:  http://localhost:{PORT_APP}")
    
    # Tenta pegar IP da rede para facilitar acesso via Tailscale/LAN
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_rede = s.getsockname()[0]
        s.close()
        print(f"  [SISTEMA] Acesse na rede:    http://{ip_rede}:{PORT_APP}")
    except:
        pass

    print(f"\n  [SISTEMA] Pressione Ctrl+C nesta janela para encerrar todos os motores.")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        pass

    print("\nEncerrando...")
    for p in _processos:
        try:
            parent = psutil.Process(p.pid)
            children = parent.children(recursive=True)
            for child in children:
                try: child.terminate()
                except psutil.NoSuchProcess: pass
            parent.terminate()
            
            # Aguarda encerramento gracioso e mata se resistirem
            procs = children + [parent]
            gone, alive = psutil.wait_procs(procs, timeout=3)
            for p_alive in alive:
                try: p_alive.kill()
                except psutil.NoSuchProcess: pass
        except psutil.NoSuchProcess:
            pass
        except Exception:
            try: p.terminate()
            except: pass
    srv.parar()


if __name__ == "__main__":
    main()

