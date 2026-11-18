from qwen21_workflow import build_workflow as _build_qwen21_workflow
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..','shared'))
try:
    import _torchvision_patch  # noqa
except Exception:
    pass
# =============================================================================
# STUDIO PRO  Backend v2.0 | FastAPI | Porta 9000
# RTX 5080 Blackwell | CUDA 12.8 | Plug & Play
# =============================================================================

#  PATCH torchvision (deve ser o PRIMEIRO bloco) 
import sys
from types import ModuleType as _MT
try:
    import torchvision.transforms.functional as _tvf
    _m = _MT("torchvision.transforms.functional_tensor")
    _m.rgb_to_grayscale = _tvf.rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = _m
except Exception as _e:
    print(f"[PATCH] {_e}")

#  SUPRIMIR aviso HuggingFace token 
import os
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"

#  FIX: Unicode no Console Windows 
if os.name == 'nt':
    import sys
    # Reconfigure in place. Replacing pytest/caller-owned streams with a new
    # TextIOWrapper closes their capture buffer when this module is unloaded.
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

import asyncio, base64, gc, queue as _stdlib_queue, shutil, zipfile, subprocess, logging, warnings, threading
import hashlib, hmac, json, math, mimetypes, random, re, unicodedata, uuid, urllib.error, urllib.parse, urllib.request
from difflib import SequenceMatcher
import numpy as np, torch
import collections as _col, time as _t
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from h3_prompt_writing import (
    compile_base_prompt as _compile_h3_base_prompt,
    compile_ref_prompt as _compile_h3_ref_prompt,
    detect_base_mode as _detect_h3_base_mode,
    official_skill_integrity as _h3_official_skill_integrity,
)
from h3_workflow import (
    DEFAULT_H3_QUALITY_PROFILE as _DEFAULT_H3_QUALITY_PROFILE,
    FAST_H3_MODEL_NAME as _FAST_H3_MODEL_NAME,
    FAST_H3_STEPS as _FAST_H3_STEPS,
    FAST_H3_VARIANT as _FAST_H3_VARIANT,
    H3_FL2VA_MODEL_NAME as _H3_FL2VA_MODEL_NAME,
    H3_REF2VA_MODEL_NAME as _H3_REF2VA_MODEL_NAME,
    ensure_h3_sage_attention as _ensure_h3_sage_attention,
    resolve_h3_quality_profile as _resolve_h3_quality_profile,
    take_readiness as _h3_take_readiness,
    validate_h3_comfy_graph as _validate_h3_comfy_graph,
    workflow_status as _h3_workflow_status,
)
from h3_face_refine import ensure_face_refine as _ensure_h3_face_refine, policy as _h3_face_refine_policy
from h3_acceleration import apply_master_cache as _apply_h3_master_cache, PROFILES as _H3_MASTER_CACHE_PROFILES
from h3_acceleration import REQUIRED_NODES as _H3_REQUIRED_ACCELERATION_NODES
from anchor_intelligence import (
    AnchorConflictError as _AnchorIntelligenceConflictError,
    AnchorContractError as _AnchorIntelligenceContractError,
    AnchorImageError as _AnchorIntelligenceImageError,
    build_anchor_contract as _build_anchor_intelligence_contract,
    build_vision_messages as _build_anchor_vision_messages,
    parse_vision_response as _parse_anchor_vision_response,
    reconcile_anchor_contract as _reconcile_anchor_intelligence_contract,
    validate_anchor_contract as _validate_anchor_intelligence_contract,
    validate_anchor_image as _validate_anchor_intelligence_image,
)
from video_engines import (
    EngineError as _VideoEngineError,
    build_video_engine_registry as _build_video_engine_registry,
)
from video_engines.ltx25 import LTX25_MODEL_NAME as _LTX25_MODEL_NAME
from ltx25_workflow import build_ltx25_i2v_workflow as _build_ltx25_i2v_workflow
from wan_animate_workflow import (
    WAN22_ANIMATE_MODEL_NAME,
    WAN22_ANIMATE_PROFILE,
    WAN_ANIMATE_DEFAULT_STEPS,
    build_move_workflow as _build_wan_animate_move_workflow,
    kit_status as _wan_animate_kit_status,
    validate_move_graph as _validate_wan_animate_move_graph,
)
from video_workflows import (
    HUNYUAN15_I2V_MODEL,
    HUNYUAN15_TEXT_ENCODER,
    HUNYUAN15_VAE,
    HUNYUAN15_VISION_ENCODER,
    MIN_VIDEO_FPS,
    QWEN25_VL_ENCODER,
    build_hunyuan15_i2v_workflow,
    validate_video_fps,
)
import internet_publication
import dlss5_finishing as _dlss5
import upscaling_required as _required_upscale
from video_projects import (
    LTX25_TWO_ANCHOR_PROFILE as _LTX25_TAKE_PROFILE,
    MAX_ANCHOR_IMAGE_BYTES as _MAX_ANCHOR_IMAGE_BYTES,
    AnchorConflictError as _AnchorConflictError,
    AnchorRequestNotFoundError as _AnchorRequestNotFoundError,
    create_project as _create_video_project,
    get_project_assembly_readiness as _get_project_assembly_readiness,
    get_project as _get_video_project,
    get_project_final_output_path as _get_project_final_output_path,
    get_project_candidate_output_path as _get_project_candidate_output_path,
    get_take_anchor_image_path as _get_take_anchor_image_path,
    get_take_audio_candidate_path as _get_take_audio_candidate_path,
    get_take_audio_candidate_variant_path as _get_take_audio_candidate_variant_path,
    get_take_audio_delivery_spec as _get_take_audio_delivery_spec,
    get_take_download_path as _get_take_download_path,
    get_take_generation_spec as _get_take_generation_spec,
    get_take_preview_path as _get_take_preview_path,
    get_take_preanalysis_gallery_path as _get_take_preanalysis_gallery_path,
    get_take_status as _get_take_status,
    get_take_thumbnail_path as _get_take_thumbnail_path,
    get_take_upscale_preview_path as _get_take_upscale_preview_path,
    get_take_upscale_spec as _get_take_upscale_spec,
    list_director_requests as _list_director_requests,
    list_projects as _list_video_projects,
    list_takes as _list_video_takes,
    patch_project as _patch_video_project,
    patch_take as _patch_video_take,
    register_project_final_output as _register_project_final_output,
    register_take_audio_candidate as _register_take_audio_candidate,
    register_anchor_candidate as _register_anchor_candidate,
    review_take_audio_candidate as _review_take_audio_candidate,
    review_project_final_output as _review_project_final_output,
    review_anchor_candidate as _review_anchor_candidate,
    set_take_generation_state as _set_take_generation_state,
    set_take_upscale_state as _set_take_upscale_state,
)
from project_assembly import AssemblyError as _AssemblyError, assemble_project as _assemble_project
from video_gauntlet import (
    critic_brief as _gauntlet_critic_brief,
    create_pilot as _create_gauntlet_pilot,
    get_pilot as _get_gauntlet_pilot,
    register_reference as _register_gauntlet_reference,
    repair_pilot_anchor_contract as _repair_gauntlet_anchor_contract,
    submit_verdict as _submit_gauntlet_verdict,
)
from generative_jobs import GenerativeJobStore
from gpu_lease import GpuLeaseBusy, GpuLeaseRegistry
from render_focus import (
    RenderFocusBlocked as _RenderFocusBlocked,
    prepare_render_focus as _prepare_render_focus,
)
from video_sound import (
    VideoSoundCancelled,
    VideoSoundError,
    VideoSoundRequest,
    build_default_registry as _build_video_sound_registry,
    probe_video_duration as _probe_video_sound_duration,
)
from levo_music import (
    LEVO2_PROVIDER_ID,
    levo2_status as _levo2_status,
    run_levo2_music as _run_levo2_music,
)
from music_reinstrument import (
    PRESETS as _MUSIC_REINSTRUMENT_PRESETS,
    SUPPORTED_EXTENSIONS as _MUSIC_REINSTRUMENT_EXTENSIONS,
    MusicReinstrumentCancelled as _MusicReinstrumentCancelled,
    MusicReinstrumentError as _MusicReinstrumentError,
    MusicReinstrumentRequest as _MusicReinstrumentRequest,
    normalize_instruments as _normalize_music_reinstrument_instruments,
    resolve_artifact as _resolve_music_reinstrument_artifact,
    run_reinstrumentation as _run_music_reinstrumentation,
    runtime_status as _music_reinstrument_runtime_status,
    sha256_file as _sha256_music_file,
)
from music_score_first import (
    ENGINE_ID as _SCORE_FIRST_ENGINE_ID,
    SUPPORTED_SCORE_EXTENSIONS as _SCORE_FIRST_EXTENSIONS,
    LockedScoreOrchestrationRequest as _LockedScoreOrchestrationRequest,
    ScoreTranscriptionRequest as _ScoreTranscriptionRequest,
    choose_transcription_device as _choose_score_first_device,
    run_locked_score_orchestration as _run_locked_score_orchestration,
    run_score_transcription as _run_score_transcription,
    runtime_status as _score_first_runtime_status,
)
from music_orchestrator import sanitize_orchestration_prompt as _sanitize_music_orchestration_prompt
from music_ai_audio import (
    MusicAiAudioError as _MusicAiAudioError,
    probe_audio as _probe_music_ai_audio,
)
from music_ai_production import (
    MusicAiProductionCancelled as _MusicAiProductionCancelled,
    MusicAiProductionError as _MusicAiProductionError,
    MusicAiProductionRequest as _MusicAiProductionRequest,
    resolve_artifact as _resolve_music_ai_artifact,
    run_music_ai_production as _run_music_ai_production,
    runtime_status as _music_ai_runtime_status,
    sanitize_prompt as _sanitize_music_ai_prompt,
)
from mova_runtime import (
    MOVA_MODEL_NAME,
    mova_status as _mova_status,
    run_mova_generation as _run_mova_generation,
)
from ltx_review_pipeline import (
    load_ltx_review_pipeline_policy as _load_ltx_review_pipeline_policy,
    run_ltx_review_pipeline as _run_ltx_review_pipeline,
)
from mova_producer import (
    analyze_mova_take as _analyze_mova_take,
    build_mova_effective_prompt as _build_mova_effective_prompt,
    enforce_dialogue_duration as _enforce_mova_dialogue_duration,
    enforce_mova_policy as _enforce_mova_policy,
    inspect_mova_final_hold as _inspect_mova_final_hold,
    inspect_mova_media as _inspect_mova_media,
    inspect_visible_text as _inspect_visible_text,
)
from anchor_executors import AnchorExecutorManager
from media_assets import list_media_assets
from editor_suite import EditorSuite, EditorSuiteError, create_editor_router
from review_proxies import (
    build_review_proxy as _build_review_proxy,
    is_review_proxy_path as _is_review_proxy_path,
)
from hardware_status import dashboard_gpu_snapshot
from hyperframes_runtime import (
    OUTPUT_PATH as _HYPERFRAMES_OUTPUT_PATH,
    ensure_preview as _ensure_hyperframes_preview,
    ensure_preview_async as _ensure_hyperframes_preview_async,
    start_render as _start_hyperframes_render,
    status as _hyperframes_status,
)

#  INJEaaO DE FFMPEG NO PATH (resolve aviso do pydub e librosa)
import shutil, tempfile

def _setup_ffmpeg():
    # 1. Tenta o sistema primeiro
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        return "ffmpeg"
    except Exception:
        pass

    # 2. Tenta imageio_ffmpeg e cria um SHIM se o nome for diferente de 'ffmpeg.exe'
    try:
        import imageio_ffmpeg as _iff
        _real_exe = _iff.get_ffmpeg_exe()
        _dir = os.path.dirname(_real_exe)
        _name = os.path.basename(_real_exe)
        
        # Se o nome nao for exatamente ffmpeg.exe (ex: ffmpeg-win-x86_64.exe), 
        # criamos um shim em um diretorio temporario para que bibliotecas externas o encontrem.
        if _name.lower() not in ["ffmpeg", "ffmpeg.exe"]:
            _shim_dir = os.path.join(tempfile.gettempdir(), "pemara_ffmpeg_shim")
            os.makedirs(_shim_dir, exist_ok=True)
            _shim_exe = os.path.join(_shim_dir, "ffmpeg.exe")
            
            # Copia apenas se nao existir ou se for diferente
            if not os.path.exists(_shim_exe):
                try:
                    shutil.copy2(_real_exe, _shim_exe)
                except Exception as e:
                    print(f"[FFMPEG] Erro ao criar shim: {e}", flush=True)
            
            if os.path.exists(_shim_exe):
                os.environ["PATH"] = _shim_dir + os.pathsep + os.environ.get("PATH", "")
                print(f"[FFMPEG] Shim criado em: {_shim_exe}", flush=True)
                return _shim_exe
        
        # Fallback: apenas adiciona o dir ao PATH
        os.environ["PATH"] = _dir + os.pathsep + os.environ.get("PATH", "")
        print(f"[FFMPEG] Usando imageio_ffmpeg: {_real_exe}", flush=True)
        return _real_exe
    except Exception as _fe:
        print(f"[FFMPEG] Nao encontrado ({_fe})  instale manualmente.", flush=True)
        return None

_ffmpeg_exe = _setup_ffmpeg()

from pydub import AudioSegment
if _ffmpeg_exe:
    AudioSegment.converter = _ffmpeg_exe
    # Tenta encontrar ffprobe no mesmo local (raro no imageio_ffmpeg)
    _ffp = _ffmpeg_exe.replace("ffmpeg", "ffprobe")
    if os.path.exists(_ffp):
        AudioSegment.ffprobe = _ffp
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
from io import BytesIO
from faster_whisper import WhisperModel
from scipy import signal
from scipy.fft import rfft, irfft

warnings.filterwarnings("ignore")

logging.basicConfig(
    filename="backend_erros.log", level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#  CONFIG 
PASTA     = os.path.join(os.path.dirname(__file__), "resultados_temp")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "modelos")
MODEL_PATH= os.path.join(MODEL_DIR, "RealESRGAN_x4plus.pth")
MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
os.makedirs(PASTA, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

def _allowed_origins() -> List[str]:
    raw = os.environ.get("STUDIO_ALLOWED_ORIGINS", "")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or [
        "https://maestro.pemaratech.com.br",
        "http://127.0.0.1:9501",
        "http://localhost:9501",
    ]


def _canonical_browser_origin(raw: str) -> str:
    value = str(raw or "").strip()
    if not value or value == "null":
        return ""
    try:
        parsed = urllib.parse.urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return ""
        port = parsed.port
    except (TypeError, ValueError):
        return ""
    default_port = 443 if parsed.scheme == "https" else 80
    suffix = "" if port in {None, default_port} else f":{port}"
    return f"{parsed.scheme}://{parsed.hostname.lower().rstrip('.')}{suffix}"


def _browser_origin_allowed(request: Request) -> bool:
    """Reject cross-site browser access while preserving local CLI clients."""
    raw_origin = request.headers.get("origin", "")
    fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
    if raw_origin:
        supplied = _canonical_browser_origin(raw_origin)
        allowed = {
            canonical
            for canonical in (_canonical_browser_origin(item) for item in _allowed_origins())
            if canonical
        }
        return bool(supplied and supplied in allowed)
    # Non-browser local clients normally send neither header. A browser that
    # explicitly reports a cross-site context must never inherit loopback trust.
    return fetch_site != "cross-site"


def _internal_token() -> str:
    return (
        _env_value("STUDIO_INTERNAL_TOKEN")
        or _env_value("MAESTRO_FRONTEND_TOKEN")
    )


def _public_studio_hosts() -> set[str]:
    raw = os.environ.get("STUDIO_PUBLIC_HOSTS", "api-studio.pemaratech.com.br")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _request_hosts(request: Request) -> set[str]:
    hosts: set[str] = set()
    for header in ("host", "x-forwarded-host"):
        raw = request.headers.get(header, "")
        for part in raw.split(","):
            host = part.strip().lower().split(":")[0]
            if host:
                hosts.add(host)
    return hosts


def _is_internal_request(request: Request) -> bool:
    expected = _internal_token()
    provided = request.headers.get("X-Studio-Internal-Token", "").strip()
    if expected and provided and hmac.compare_digest(expected, provided):
        return True

    # Qualquer cabeçalho de proxy torna a origem não confiável sem o token.
    # Isso impede que um túnel novo, com hostname ainda não inventariado,
    # pareça uma chamada local apenas porque termina no loopback.
    if request.headers.get("x-forwarded-host") or request.headers.get("forwarded"):
        return False
    request_hosts = _request_hosts(request)
    if request_hosts & _public_studio_hosts():
        return False
    local_hosts = {"127.0.0.1", "localhost", "::1"}
    if request_hosts and any(host not in local_hosts and not host.startswith("127.") for host in request_hosts):
        return False
    host = (request.client.host if request.client else "").lower()
    if host in {"127.0.0.1", "::1", "localhost"} or host.startswith("127."):
        return True
    return False


def _public_forbidden() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"ok": False, "erro": "Studio API protegida. Use o painel Maestro."},
    )


_DOCS_ENABLED = os.environ.get("STUDIO_ENABLE_DOCS", "0").strip().lower() in {"1", "true", "yes", "on"}
app = FastAPI(
    title="Studio Pro",
    version="2.0",
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["GET", "HEAD", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Range", "X-Requested-With", "X-CSRF-Token"],
    expose_headers=["Content-Disposition", "X-Filename"],
    max_age=600,
)


@app.middleware("http")
async def studio_security_boundary(request: Request, call_next):
    if request.url.path.startswith("/api/") and (
        not _is_internal_request(request) or not _browser_origin_allowed(request)
    ):
        response = _public_forbidden()
    else:
        response = await call_next(request)

    if request.url.path.startswith("/api/"):
        # API JSON remains non-cacheable by default, while media routes may
        # explicitly opt into private versioned caching for HTML5 byte ranges.
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    else:
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'; object-src 'none'",
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    if request.url.scheme == "https" or forwarded_proto == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

#  LOG EM TEMPO REAL 
_log_buf = _col.deque(maxlen=300)

def bk_log(msg: str):
    entry = f"[{_t.strftime('%H:%M:%S')}] {msg}"
    _log_buf.append(entry)
    try:
        print(entry, flush=True)
    except (AttributeError, BrokenPipeError, OSError, ValueError):
        # A detached watchdog/auxiliary console must never keep a completed
        # GPU job in the persistent "running" state. The in-memory log stays
        # available through /api/log even when stdout has no active reader.
        pass

@app.get("/api/log")
async def get_log(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    return {"logs": list(_log_buf)[-100:]}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pemara Studio API</title>
  <style>
    body { margin:0; min-height:100vh; display:grid; place-items:center; background:#070a0e; color:#e5edf5; font-family:Arial,sans-serif; }
    main { width:min(720px, calc(100vw - 32px)); border:1px solid #1f2a36; border-radius:12px; padding:28px; background:#0d131a; box-shadow:0 24px 80px rgba(0,0,0,.35); }
    h1 { margin:0 0 8px; font-size:28px; }
    p { color:#9fb0c3; line-height:1.5; }
    a { color:#ff7a1a; font-weight:700; text-decoration:none; }
    a:hover { text-decoration:underline; }
    ul { padding-left:20px; }
    li { margin:10px 0; }
    code { background:#05080b; border:1px solid #1f2a36; border-radius:6px; padding:3px 6px; color:#c7f9cc; }
  </style>
</head>
<body>
  <main>
    <h1>Pemara Studio API online</h1>
    <p>Este dominio e a API do Studio. Para usar o gerador visual, abra o painel Maestro.</p>
    <ul>
      <li><a href="https://maestro.pemaratech.com.br/">Abrir Maestro</a></li>
    </ul>
    <p>Padrao atual de video: <code>MP4 H.264</code>, <code>1280x720</code>, <code>30fps</code>.</p>
  </main>
</body>
</html>
"""

#  ESTADO GLOBAL 
_whisper_model = None
_whisper_size  = ""
_upsampler     = None
_GEN_JOB_STORE = GenerativeJobStore(
    Path(__file__).resolve().parents[2] / "dados" / "studio" / "generative_jobs.json",
    recover_on_init=False,
)
_GPU_LEASE_REGISTRY = GpuLeaseRegistry(
    Path(__file__).resolve().parents[2] / "dados" / "studio" / "gpu_lease.json"
)
_GEN_JOB_INPUT_ROOT = Path(__file__).resolve().parents[2] / "dados" / "studio" / "job_inputs"
_GEN_JOB_INPUT_MAX_BYTES = int(os.environ.get("STUDIO_JOB_INPUT_MAX_BYTES", str(64 * 1024 * 1024)))
_ACTIVE_GEN_JOBS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_GEN_JOBS_LOCK = threading.RLock()
_ACTIVE_MUSIC_REINSTRUMENT_JOBS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_MUSIC_REINSTRUMENT_LOCK = threading.RLock()
_PROJECT_ASSEMBLY_LOCK = threading.Lock()
_ACTIVE_PROJECT_ASSEMBLIES: set[str] = set()
_VIDEO_TAKE_QUEUE: List[str] = []
_VIDEO_TAKE_QUEUE_CONDITION = threading.Condition()
_VIDEO_TAKE_ACTIVE_JOB_ID = ""
_VIDEO_BATCH_START_LOCK = threading.Lock()
_VIDEO_TAKE_START_LOCK = threading.RLock()
_VIDEO_RESOURCE_RETRY_SECONDS = 15.0
_MINIMAX_H3_RECOVERY_MIN_VRAM_BYTES = 8 * 1024**3
_VIDEO_UPSCALE_LOCK = threading.Lock()
_VIDEO_UPSCALE_START_LOCK = threading.Lock()
_VIDEO_UPSCALE_GATE = threading.Event()
_RECOVERED_UPSCALE_ORDER: List[str] = []
_RECOVERED_UPSCALE_ORDER_CONDITION = threading.Condition()
_VIDEO_UPSCALE_PROFILE_ID = _required_upscale.profile_id(1920, 1080)
_VIDEO_UPSCALE_VERTICAL_PROFILE_ID = _required_upscale.profile_id(1080, 1920)
_VIDEO_UPSCALE_TOOL = (
    Path(__file__).resolve().parents[2]
    / "ferramentas"
    / "video_global_engine"
    / "tools"
    / "postprocess_required_upscale.py"
)
_VIDEO_UPSCALE_PROFILE = (
    Path(__file__).resolve().parents[2]
    / "ferramentas"
    / "video_global_engine"
    / "upscale_profiles"
    / f"{_VIDEO_UPSCALE_PROFILE_ID}.json"
)
_VIDEO_UPSCALE_VERTICAL_PROFILE = (
    Path(__file__).resolve().parents[2]
    / "ferramentas"
    / "video_global_engine"
    / "upscale_profiles"
    / f"{_VIDEO_UPSCALE_VERTICAL_PROFILE_ID}.json"
)
_VIDEO_UPSCALE_CHUNK_SIZE = 17
_VIDEO_UPSCALE_PER_BATCH = 1
_VIDEO_UPSCALE_DISK_RESERVE_BYTES = 2 * 1024**3
_VIDEO_UPSCALE_OUTPUT_MIN_BYTES = 2 * 1024**3


class GenerationCancelled(RuntimeError):
    pass


class ComfyDynamicVramFault(RuntimeError):
    """The ComfyUI DynamicVRAM/VBAR allocator entered a recoverable bad state."""


class UpscaleAttemptObsolete(GenerationCancelled):
    """The persisted take no longer belongs to this worker attempt."""


class RecoverableUpscaleError(RuntimeError):
    """A retryable infrastructure/preflight failure that did not approve output."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = str(code or "UPSCALE_RECOVERABLE_ERROR")


class TakeJobConflict(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _wait_for_gpu_lease(
    job_id: str,
    *,
    operation: str,
    project_id: str,
    take_id: str,
    cancel_event: threading.Event,
) -> dict[str, Any]:
    last_holder = ""
    while True:
        if cancel_event.is_set():
            raise GenerationCancelled("Trabalho cancelado enquanto aguardava a GPU.")
        try:
            lease = _GPU_LEASE_REGISTRY.acquire(
                owner="maestro_studio",
                operation=operation,
                job_id=job_id,
                project_id=project_id,
                take_id=take_id,
            )
            if last_holder:
                _GEN_JOB_STORE.update(
                    job_id,
                    gpu_lease_waiting=False,
                    gpu_lease_holder=None,
                )
            return lease
        except GpuLeaseBusy as exc:
            holder = str(exc.current.get("operation") or "outro trabalho")
            if holder != last_holder:
                _GEN_JOB_STORE.update(
                    job_id,
                    status="queued",
                    message=f"Aguardando a GPU reservada por {holder}; nenhum processo sera interrompido.",
                    gpu_lease_waiting=True,
                    gpu_lease_holder=exc.current,
                )
                last_holder = holder
            cancel_event.wait(2.0)

#  UTILITaRIOS 
def limpar_vram():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()

def get_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except Exception:
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

def nvenc_ok(ff):
    try:
        return "h264_nvenc" in subprocess.run([ff, "-encoders"], capture_output=True, text=True).stdout
    except Exception:
        return False

def get_video_bitrate(ff, path):
    """Retorna o bitrate total do video em bps usando ffprobe ou fallback via ffmpeg."""
    try:
        fp = ff.replace("ffmpeg", "ffprobe")
        # Se fp existe fisicamente ou se ff e o comando global
        if os.path.exists(fp) or ff == "ffmpeg":
            cmd = [fp, "-v", "error", "-select_streams", "v:0", "-show_entries", "format=bit_rate", "-of", "json", path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            data = json.loads(res.stdout)
            return int(data.get("format", {}).get("bit_rate", 0))
    except Exception:
        pass
    
    # Fallback: Parsing do output do ffmpeg -i (bitrate aparece no stderr)
    try:
        cmd = [ff, "-i", path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        for line in res.stderr.splitlines():
            if "bitrate:" in line:
                # Ex: "  Duration: 00:00:10.00, start: 0.000000, bitrate: 2500 kb/s"
                parts = line.split("bitrate:")
                if len(parts) > 1:
                    br_val = parts[1].strip().split()[0]
                    return int(br_val) * 1000
    except Exception:
        pass
    return 0

def garantir_esrgan():
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        bk_log("Baixando RealESRGAN_x4plus.pth (~64MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        bk_log("Download concluido.")
    return MODEL_PATH

def carregar_upsampler():
    global _upsampler
    if _upsampler:
        return _upsampler
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet
    device = "cuda" if torch.cuda.is_available() else "cpu"
    bk_log(f"Carregando Real-ESRGAN em {device.upper()}...")
    m = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    _upsampler = RealESRGANer(
        scale=4, model_path=garantir_esrgan(), model=m,
        tile=512, tile_pad=10, pre_pad=0,
        half=torch.cuda.is_available(), device=device
    )
    return _upsampler

def biquad_peaking(fc, fs, gain_db, Q=0.9):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * Q)
    b = np.array([1 + alpha*A, -2*np.cos(w0), 1 - alpha*A])
    a = np.array([1 + alpha/A, -2*np.cos(w0), 1 - alpha/A])
    return b / a[0], a / a[0]

def dsp_pipeline(audio, sr,
                 nr_intensidade=1.4, nr_floor=0.28, nr_ativo=True,
                 hpf_hz=100.0, box_cut_hz=0.0, box_cut_db=-4.0,
                 eq1_hz=2500.0, eq1_db=5.0,
                 eq2_hz=4000.0, eq2_db=4.0,
                 eq3_hz=7000.0, eq3_db=3.0,
                 volume_target=-8.5):
    audio = audio.astype(np.float64)
    if nr_ativo:
        CHUNK, HOP = 4096, 2048
        win = np.hanning(CHUNK)
        n_r = min(int(sr * 2.0), len(audio) - CHUNK)
        frames = [np.abs(rfft(audio[i:i+CHUNK] * win)) for i in range(0, n_r, HOP)]
        if frames:
            perfil = np.median(frames, axis=0) * nr_intensidade
            buf = np.zeros(len(audio)); norm = np.zeros(len(audio))
            for i in range(0, len(audio) - CHUNK, HOP):
                f   = audio[i:i+CHUNK] * win
                esp = rfft(f)
                ml  = np.maximum(np.abs(esp) - perfil, np.abs(esp) * nr_floor)
                rec = irfft(ml * np.exp(1j * np.angle(esp))).real * win
                buf[i:i+CHUNK]  += rec
                norm[i:i+CHUNK] += win ** 2
            audio = buf / np.where(norm < 1e-8, 1.0, norm)
    audio = audio.astype(np.float32)
    if hpf_hz > 0:
        sos = signal.butter(4, float(hpf_hz) / (sr / 2), btype='high', output='sos')
        audio = signal.sosfilt(sos, audio).astype(np.float32)
    if box_cut_hz > 0 and box_cut_db != 0:
        b, a = biquad_peaking(float(box_cut_hz), sr, float(box_cut_db), Q=0.7)
        audio = signal.lfilter(b, a, audio).astype(np.float32)
    for hz, db in [(eq1_hz, eq1_db), (eq2_hz, eq2_db), (eq3_hz, eq3_db)]:
        if db != 0 and hz > 0:
            b, a = biquad_peaking(float(hz), sr, float(db), Q=0.9)
            audio = signal.lfilter(b, a, audio).astype(np.float32)
    rms = np.sqrt(np.mean(audio ** 2))
    if rms > 0:
        audio = audio * (10 ** (float(volume_target) / 20) / rms)
    t = 0.85
    above = np.abs(audio) > t
    audio[above] = np.sign(audio[above]) * (t + (1-t) * np.tanh((np.abs(audio[above]) - t) / (1-t)))
    return np.clip(audio, -0.97, 0.97).astype(np.float32)

def file_response(path: str, filename: str):
    """FileResponse com Content-Disposition RFC 5987  suporta qualquer caractere Unicode."""
    import urllib.parse
    # Remove caracteres que quebram headers HTTP (latin-1 only)
    safe_ascii = filename.encode("ascii", errors="replace").decode("ascii").replace("?", "_")
    # Versao UTF-8 encoded para clientes modernos (RFC 5987)
    utf8_encoded = urllib.parse.quote(filename, safe=" ()-_.")
    cd = f"attachment; filename=\"{safe_ascii}\"; filename*=UTF-8''{utf8_encoded}"
    return FileResponse(
        path,
        headers={"Content-Disposition": cd, "X-Filename": safe_ascii}
    )


class MediaUploadTooLarge(ValueError):
    pass


def _max_media_upload_bytes() -> int:
    raw = os.environ.get("STUDIO_MAX_MEDIA_UPLOAD_MB", "2048")
    try:
        megabytes = int(raw)
    except (TypeError, ValueError):
        megabytes = 2048
    return max(1, min(8192, megabytes)) * 1024 * 1024


def _safe_upload_filename(filename: str, fallback: str = "arquivo.bin") -> str:
    leaf = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not leaf or leaf in {".", ".."}:
        leaf = fallback
    safe = "".join(
        char if char.isalnum() or char in {" ", ".", "-", "_", "(", ")"} else "_"
        for char in leaf
    ).strip(" .")
    return (safe or fallback)[:160]


def _save_media_upload(
    upload: UploadFile,
    prefix: str,
    max_bytes: int | None = None,
) -> Tuple[str, str]:
    """Persist a media upload under the Studio temp root with a hard size cap."""
    limit = max_bytes if max_bytes is not None else _max_media_upload_bytes()
    safe_name = _safe_upload_filename(upload.filename or "")
    safe_prefix = "".join(char if char.isalnum() or char in "-_" else "_" for char in prefix)[:32]
    root = Path(PASTA).resolve()
    target = (root / f"{safe_prefix}_{uuid.uuid4().hex[:12]}_{safe_name}").resolve()
    if root not in target.parents:
        raise ValueError("Destino temporario de upload invalido.")
    total = 0
    try:
        upload.file.seek(0)
        with target.open("xb") as handle:
            # One authorized command gets one generation attempt. Resource
            # shortage is terminal-but-recoverable and must be retried by the
            # director after the preflight condition is corrected.
            for _resource_attempt in range(1):
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise MediaUploadTooLarge(
                        f"{safe_name} excede o limite de {limit // (1024 * 1024)} MB."
                    )
                handle.write(chunk)
        return str(target), safe_name
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        try:
            upload.file.close()
        except Exception:
            pass


def _unique_media_output(stem: str, extension: str, tag: str = "") -> str:
    safe_stem = _safe_upload_filename(stem or "resultado", "resultado")
    safe_stem = os.path.splitext(safe_stem)[0][:96] or "resultado"
    safe_extension = "".join(char for char in (extension or "") if char.isalnum()).lower()
    if not safe_extension:
        raise ValueError("Extensao de saida invalida.")
    safe_tag = "".join(char if char.isalnum() or char in "-_" else "_" for char in tag)[:32]
    middle = f"_{safe_tag}" if safe_tag else ""
    return os.path.join(PASTA, f"{safe_stem}{middle}_{uuid.uuid4().hex[:12]}.{safe_extension}")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMFY_URL = os.environ.get("PEMARA_COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
COMFY_ROOT = os.path.join(BASE_DIR, "ferramentas", "ComfyUI")
COMFY_MODELS_DIR = os.path.join(BASE_DIR, "ferramentas", "ComfyUI", "models")
COMFY_INPUT_DIR = os.path.join(COMFY_ROOT, "input")
COMFY_OUTPUT_DIR = os.path.join(COMFY_ROOT, "output")
STUDIO_OUTPUT_DIR = os.path.join(BASE_DIR, "dados", "outputs", "generative")
VIDEO_PROJECTS_ROOT = Path(BASE_DIR) / "ferramentas" / "video_global_engine" / "projetos"
_VIDEO_SOUND_REGISTRY = _build_video_sound_registry(Path(BASE_DIR))
_ANCHOR_EXECUTOR_MANAGER = AnchorExecutorManager(
    VIDEO_PROJECTS_ROOT.parent,
    python_executable=sys.executable,
)
_ANCHOR_RECEIPT_LOCK = threading.RLock()
_ANCHOR_ANALYSIS_RECEIPTS: Dict[str, Dict[str, Any]] = {}
_ANCHOR_COMPILED_RECEIPTS: Dict[str, Dict[str, Any]] = {}
_ANCHOR_RECEIPT_TTL_SECONDS = max(
    300,
    min(7200, int(os.environ.get("MAESTRO_ANCHOR_RECEIPT_TTL_SECONDS", "7200"))),
)
_REVIEW_PROXY_QUEUE: _stdlib_queue.Queue[tuple[str, str, Path, str]] = _stdlib_queue.Queue()
_REVIEW_PROXY_KEYS: set[str] = set()
_REVIEW_PROXY_LOCK = threading.Lock()
_REVIEW_PROXY_WORKER_STARTED = False
OPERATION_FLAGS_DIR = os.path.join(BASE_DIR, "dados", "flags")
VIDEO_PAUSE_FLAG = os.path.join(OPERATION_FLAGS_DIR, "video_generation_paused.flag")
PEMARA_ESTUDIO_40ANOS_FLAG = os.path.join(OPERATION_FLAGS_DIR, "pemara_estudio_40anos.flag")
EDITOR_SUITE_ROOT = Path(BASE_DIR) / "dados" / "studio" / "editor_suite"
MUSIC_REINSTRUMENT_ROOT = Path(BASE_DIR) / "dados" / "studio" / "music_reinstrument"


def _review_proxy_auto_enabled() -> bool:
    return os.environ.get("STUDIO_AUTO_REVIEW_PROXIES", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _review_proxy_worker() -> None:
    while True:
        project_id, take_id, source, key = _REVIEW_PROXY_QUEUE.get()
        try:
            project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve()
            if project_dir.parent != VIDEO_PROJECTS_ROOT.resolve():
                raise ValueError("Projeto fora da raiz ao gerar proxy.")
            result = _build_review_proxy(
                project_dir,
                take_id,
                source,
                ffmpeg=get_ffmpeg(),
                ffprobe=shutil.which("ffprobe") or "ffprobe",
            )
            logging.info(
                "Review proxy %s/%s pronto (%s bytes, skipped=%s)",
                project_id,
                take_id,
                result.get("proxyBytes"),
                result.get("skipped"),
            )
        except Exception:
            logging.exception(
                "Falha ao gerar review proxy CPU para %s/%s",
                project_id,
                take_id,
            )
        finally:
            with _REVIEW_PROXY_LOCK:
                _REVIEW_PROXY_KEYS.discard(key)
            _REVIEW_PROXY_QUEUE.task_done()


def _start_review_proxy_worker() -> None:
    global _REVIEW_PROXY_WORKER_STARTED
    if not _review_proxy_auto_enabled():
        return
    with _REVIEW_PROXY_LOCK:
        if _REVIEW_PROXY_WORKER_STARTED:
            return
        _REVIEW_PROXY_WORKER_STARTED = True
    threading.Thread(
        target=_review_proxy_worker,
        daemon=True,
        name="studio-review-proxy-cpu",
    ).start()


def _enqueue_review_proxy(project_id: str, take_id: str, source: Path) -> bool:
    if not _review_proxy_auto_enabled():
        return False
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve()
    source = Path(source).resolve()
    if (
        project_dir.parent != VIDEO_PROJECTS_ROOT.resolve()
        or not source.is_relative_to(project_dir)
        or not source.is_file()
    ):
        return False
    key = f"{project_id}:{take_id}:{source}:{source.stat().st_size}:{source.stat().st_mtime_ns}"
    with _REVIEW_PROXY_LOCK:
        if key in _REVIEW_PROXY_KEYS:
            return False
        _REVIEW_PROXY_KEYS.add(key)
    _start_review_proxy_worker()
    _REVIEW_PROXY_QUEUE.put((project_id, take_id, source, key))
    return True


_EDITOR_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
if not _EDITOR_OLLAMA_URL.startswith(("http://", "https://")):
    _EDITOR_OLLAMA_URL = f"http://{_EDITOR_OLLAMA_URL}"
_EDITOR_SUITE = EditorSuite(
    EDITOR_SUITE_ROOT,
    ffmpeg=get_ffmpeg(),
    ffprobe=shutil.which("ffprobe") or "ffprobe",
    ollama_url=_EDITOR_OLLAMA_URL,
    finish_media=lambda path: _finish_required_media(path),
    max_upload_bytes=_max_media_upload_bytes(),
)
app.include_router(
    create_editor_router(
        _EDITOR_SUITE,
        is_internal_request=_is_internal_request,
        forbidden_response=_public_forbidden,
    )
)

from zico_audio import create_zico_router
app.include_router(create_zico_router(_is_internal_request))
from game_assets import create_game_assets_router
app.include_router(create_game_assets_router(_is_internal_request))
from game_images import create_game_images_router
app.include_router(create_game_images_router(_is_internal_request))
from game_3d import create_game_3d_router
app.include_router(create_game_3d_router(_is_internal_request))

_DICTATION_MEDIA_SUFFIXES = {
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/m4a": ".m4a",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
_DICTATION_MAX_BYTES = max(
    1024 * 1024,
    min(64 * 1024 * 1024, int(os.environ.get("MAESTRO_DICTATION_MAX_BYTES", str(16 * 1024 * 1024)))),
)
_DICTATION_MAX_SECONDS = max(
    10.0,
    min(300.0, float(os.environ.get("MAESTRO_DICTATION_MAX_SECONDS", "120"))),
)


def _dictation_error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": {"code": code, "message": message}},
    )


def _dictation_media_suffix(content_type: str) -> str:
    media_type = str(content_type or "").split(";", 1)[0].strip().lower()
    return _DICTATION_MEDIA_SUFFIXES.get(media_type, "")


async def _save_dictation_body(request: Request, target: Path) -> int:
    raw_length = request.headers.get("content-length", "").strip()
    if raw_length:
        try:
            content_length = int(raw_length)
        except ValueError as exc:
            raise EditorSuiteError(
                "INVALID_CONTENT_LENGTH",
                "O tamanho informado para o audio e invalido.",
                400,
            ) from exc
        if content_length <= 0:
            raise EditorSuiteError("EMPTY_AUDIO", "Envie um audio para transcrever.", 422)
        if content_length > _DICTATION_MAX_BYTES:
            raise EditorSuiteError(
                "AUDIO_TOO_LARGE",
                f"O audio pode ter no maximo {_DICTATION_MAX_BYTES // (1024 * 1024)} MB.",
                413,
            )

    written = 0
    with target.open("wb") as output:
        async for chunk in request.stream():
            if not chunk:
                continue
            written += len(chunk)
            if written > _DICTATION_MAX_BYTES:
                raise EditorSuiteError(
                    "AUDIO_TOO_LARGE",
                    f"O audio pode ter no maximo {_DICTATION_MAX_BYTES // (1024 * 1024)} MB.",
                    413,
                )
            output.write(chunk)
    if written <= 0:
        raise EditorSuiteError("EMPTY_AUDIO", "Envie um audio para transcrever.", 422)
    return written


@app.post("/api/dictation/transcriptions", status_code=201)
async def create_dictation_transcription(
    request: Request,
    language: str = "pt",
):
    if not _is_internal_request(request):
        return _public_forbidden()
    suffix = _dictation_media_suffix(request.headers.get("content-type", ""))
    if not suffix:
        return _dictation_error(
            415,
            "UNSUPPORTED_AUDIO_TYPE",
            "Use audio WAV, MP3, M4A, AAC, OGG, Opus, WebM ou MP4.",
        )
    normalized_language = (language or "pt").strip().lower()
    if normalized_language not in {"pt", "en", "auto"}:
        return _dictation_error(
            422,
            "INVALID_LANGUAGE",
            "Use pt, en ou auto como idioma.",
        )
    try:
        with tempfile.TemporaryDirectory(prefix="maestro-dictation-upload-") as work_dir:
            source = Path(work_dir) / f"source{suffix}"
            await _save_dictation_body(request, source)
            result = await asyncio.to_thread(
                _EDITOR_SUITE.transcribe_short_audio,
                source,
                language=None if normalized_language == "auto" else normalized_language,
                max_duration_seconds=_DICTATION_MAX_SECONDS,
            )
        return {
            "ok": True,
            "transcription": result,
            "privacy": {"stored": False, "cloud": False},
        }
    except EditorSuiteError as exc:
        return _dictation_error(exc.status, exc.code, str(exc))
    except asyncio.CancelledError:
        raise
    except Exception:
        logging.exception("Falha interna na transcricao de ditado")
        return _dictation_error(
            500,
            "DICTATION_FAILED",
            "Nao foi possivel transcrever o audio agora.",
        )

DEFAULT_FLUX_MODEL = "flux1-krea-dev_fp8_scaled.safetensors"
DEFAULT_QWEN_MODEL = "qwen_image_2.1_int8_convrot.safetensors"
DEFAULT_QWEN_EDIT_MODEL = "qwen_image_2.1_int8_convrot.safetensors"
DEFAULT_MARKETING_CARD_MODEL = DEFAULT_QWEN_EDIT_MODEL
DEFAULT_MARKETING_CARD_WIDTH = 1024
DEFAULT_MARKETING_CARD_HEIGHT = 1280
DEFAULT_MARKETING_CARD_STEPS = 40
DEFAULT_MARKETING_CARD_GUIDANCE = 1.0
WAN22_NATIVE_FP16_MODEL = "wan2.2_i2v_high_noise_14B_fp16.safetensors"
# The RTX 5090 completed the native pair smoke at ~31.6 GiB VRAM. Use the
# unquantized weights by default; GGUF variants remain explicit fallbacks.
WAN22_PRODUCTION_MODEL = WAN22_NATIVE_FP16_MODEL
WAN22_FUN_CAMERA_HIGH_MODEL = "wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors"
WAN22_FUN_CAMERA_LOW_MODEL = "wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors"
WAN_RETIRED_MODELS = {
    WAN22_PRODUCTION_MODEL,
    WAN22_FUN_CAMERA_HIGH_MODEL,
    WAN22_FUN_CAMERA_LOW_MODEL,
}
# Compatibility alias for historical jobs and tests. These models are retired
# and can no longer be authorized by any launch-time switch.
WAN_RESERVE_MODELS = WAN_RETIRED_MODELS
MINIMAX_H3_MODEL_NAME = _H3_FL2VA_MODEL_NAME
MINIMAX_H3_REF2VA_MODEL_NAME = _H3_REF2VA_MODEL_NAME
DEFAULT_VIDEO_MODEL = MINIMAX_H3_MODEL_NAME
MINIMAX_H3_PROFILE = "minimax_h3_fl2va_int8_720p24"
MINIMAX_H3_TEXT_ENCODER = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
MINIMAX_H3_VIDEO_VAE = "minimax_h3_video_vae_int8_convrot.safetensors"
MINIMAX_H3_AUDIO_VAE = "minimax_h3_audio_vae_fp32.safetensors"
MINIMAX_H3_WIDTH = 1280
MINIMAX_H3_HEIGHT = 720
MINIMAX_H3_VERTICAL_PROFILE = "minimax_h3_fl2va_int8_vertical_720x1280p24"
MINIMAX_H3_VERTICAL_WIDTH = 720
MINIMAX_H3_VERTICAL_HEIGHT = 1280
# H3 patchifies both spatial axes in groups of two VAE cells, so its sampling
# canvas must be divisible by 32. Horizontal jobs sample at 1344x768 and
# vertical jobs at the transposed 768x1344 canvas; each is center-cropped after
# VAE decode to its project-scoped 16:9 or 9:16 delivery geometry.
MINIMAX_H3_NATIVE_WIDTH = 1344
MINIMAX_H3_NATIVE_HEIGHT = 768
MINIMAX_H3_VERTICAL_NATIVE_WIDTH = 768
MINIMAX_H3_VERTICAL_NATIVE_HEIGHT = 1344
MINIMAX_H3_FPS = 24.0
MINIMAX_H3_STEPS = 20
MINIMAX_H3_MIN_FRAMES = 124
MINIMAX_H3_TRAINED_MAX_FRAMES = 362
MINIMAX_H3_OWNER_LONG_MAX_FRAMES = 736
MINIMAX_H3_TEMPORAL_STRIDE = 17
MINIMAX_H3_TEMPORAL_OFFSET = 5
MINIMAX_H3_COMPONENTS = {
    ("diffusion_models", MINIMAX_H3_MODEL_NAME): (
        20_970_379_616,
        "e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a",
    ),
    ("text_encoders", MINIMAX_H3_TEXT_ENCODER): (
        15_687_142_551,
        "35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6",
    ),
    ("vae", MINIMAX_H3_VIDEO_VAE): (
        2_811_065_184,
        "52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e",
    ),
    ("vae", MINIMAX_H3_AUDIO_VAE): (
        605_254_808,
        "8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48",
    ),
}
_MINIMAX_H3_INTEGRITY_CACHE: Dict[str, Any] = {"signature": None, "ok": False}
_MINIMAX_H3_INTEGRITY_CACHE_PATH = (
    Path(BASE_DIR) / "dados" / "studio" / "minimax_h3_integrity_cache.json"
)
_MINIMAX_H3_INTEGRITY_LOCK = threading.Lock()
_MINIMAX_H3_REF2VA_INTEGRITY_CACHE: Dict[str, Any] = {
    "signature": None,
    "ok": False,
}


def _minimax_h3_kit_ready(*, verify_hash: bool = False) -> bool:
    signature = []
    paths = []
    for (folder, filename), (expected_size, expected_sha256) in MINIMAX_H3_COMPONENTS.items():
        path = Path(COMFY_MODELS_DIR) / folder / filename
        if not path.is_file() or path.stat().st_size != expected_size:
            return False
        stat = path.stat()
        signature.append((str(path), stat.st_size, stat.st_mtime_ns))
        paths.append((path, expected_sha256))
    signature_value = tuple(signature)
    if not verify_hash:
        return True
    with _MINIMAX_H3_INTEGRITY_LOCK:
        if (
            _MINIMAX_H3_INTEGRITY_CACHE.get("signature") == signature_value
            and _MINIMAX_H3_INTEGRITY_CACHE.get("ok") is True
        ):
            return True

        persistent_signature = [list(item) for item in signature_value]
        expected_hashes = {
            str(path): expected_sha256.lower() for path, expected_sha256 in paths
        }
        try:
            persisted = json.loads(
                _MINIMAX_H3_INTEGRITY_CACHE_PATH.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, TypeError):
            persisted = {}
        if (
            persisted.get("version") == 1
            and persisted.get("ok") is True
            and persisted.get("signature") == persistent_signature
            and persisted.get("expected_hashes") == expected_hashes
        ):
            _MINIMAX_H3_INTEGRITY_CACHE.update({"signature": signature_value, "ok": True})
            return True

        for path, expected_sha256 in paths:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest().lower() != expected_sha256:
                _MINIMAX_H3_INTEGRITY_CACHE.update({"signature": signature_value, "ok": False})
                return False

        _MINIMAX_H3_INTEGRITY_CACHE.update({"signature": signature_value, "ok": True})
        try:
            _MINIMAX_H3_INTEGRITY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            temporary = _MINIMAX_H3_INTEGRITY_CACHE_PATH.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "ok": True,
                        "signature": persistent_signature,
                        "expected_hashes": expected_hashes,
                        "verified_at": _t.time(),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, _MINIMAX_H3_INTEGRITY_CACHE_PATH)
        except OSError:
            logging.exception("Falha ao persistir cache de integridade MiniMax H3")
        return True


def _minimax_h3_ref2va_ready(*, verify_hash: bool = False) -> bool:
    """Require a separately pinned Ref2VA checkpoint; never reuse FL2VA."""

    lock_path = Path(BASE_DIR) / "tools" / "model_installers" / "models.lock.json"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    wanted = f"diffusion_models/{MINIMAX_H3_REF2VA_MODEL_NAME}"
    artifact = next(
        (
            item for item in lock.get("artifacts", [])
            if isinstance(item, dict)
            and str(item.get("filename") or "").replace("\\", "/") == wanted
        ),
        None,
    )
    if not artifact:
        return False
    try:
        expected_size = int(artifact.get("expected_bytes") or 0)
    except (TypeError, ValueError):
        return False
    expected_sha256 = str(artifact.get("sha256") or "").strip().lower()
    if expected_size <= 0 or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        return False
    model_path = Path(COMFY_MODELS_DIR) / "diffusion_models" / MINIMAX_H3_REF2VA_MODEL_NAME
    if not model_path.is_file() or model_path.stat().st_size != expected_size:
        return False
    if not verify_hash:
        return True
    stat = model_path.stat()
    signature = (str(model_path), stat.st_size, stat.st_mtime_ns, expected_sha256)
    with _MINIMAX_H3_INTEGRITY_LOCK:
        if (
            _MINIMAX_H3_REF2VA_INTEGRITY_CACHE.get("signature") == signature
            and _MINIMAX_H3_REF2VA_INTEGRITY_CACHE.get("ok") is True
        ):
            return True
        digest = hashlib.sha256()
        with model_path.open("rb") as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(block)
        ok = digest.hexdigest().lower() == expected_sha256
        _MINIMAX_H3_REF2VA_INTEGRITY_CACHE.update({"signature": signature, "ok": ok})
        return ok


def _video_engine_readiness(
    *,
    comfy_online: bool,
    **_legacy: Any,
) -> Dict[str, bool]:
    """Report only the two owner-authorized engines; never imply a fallback."""

    registry = _build_video_engine_registry(Path(BASE_DIR), comfy_online=comfy_online)
    return {
        engine_id: bool(registry.get(engine_id).readiness().get("production_ready"))
        for engine_id in registry.ids
    }


def _video_engine_registry_live(*, comfy_online: bool | None = None):
    if comfy_online is None:
        comfy_online, _ = _comfy_online()
    return _build_video_engine_registry(Path(BASE_DIR), comfy_online=bool(comfy_online))


def _resolve_video_engine(
    engine_id: str,
    *,
    model: str = "",
    allow_explicit_legacy_model: bool = False,
):
    selected = str(engine_id or "").strip()
    selected_model = str(model or "").strip()
    if not selected and allow_explicit_legacy_model:
        if _is_minimax_h3_model(selected_model):
            selected = "minimax_h3"
        elif selected_model == _LTX25_MODEL_NAME:
            selected = "ltx_2_5"
    engine = _video_engine_registry_live().get(selected)
    expected_model = MINIMAX_H3_MODEL_NAME if engine.id == "minimax_h3" else _LTX25_MODEL_NAME
    if selected_model and selected_model != expected_model:
        if not (engine.id == "minimax_h3" and _is_minimax_h3_model(selected_model)):
            raise _VideoEngineError(
                "ENGINE_MODEL_MISMATCH",
                f"O modelo informado nao pertence ao motor {engine.display_name}.",
                details={"engine_id": engine.id, "expected_model": expected_model},
            )
    return engine, expected_model


def _video_engine_error_response(exc: Exception) -> JSONResponse:
    code = str(getattr(exc, "code", "VIDEO_ENGINE_ERROR"))
    status_code = int(getattr(exc, "status_code", 422) or 422)
    content: Dict[str, Any] = {"ok": False, "code": code, "erro": str(exc)}
    details = getattr(exc, "details", None)
    if details is None:
        details = getattr(exc, "blockers", None)
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


def _anchor_contract_digest(contract: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _prune_anchor_receipts(now: float | None = None) -> None:
    cutoff = float(now if now is not None else _t.time()) - _ANCHOR_RECEIPT_TTL_SECONDS
    for store in (_ANCHOR_ANALYSIS_RECEIPTS, _ANCHOR_COMPILED_RECEIPTS):
        expired = [key for key, item in store.items() if float(item.get("created_at") or 0) < cutoff]
        for key in expired:
            store.pop(key, None)
        while len(store) > 256:
            oldest = min(store, key=lambda key: float(store[key].get("created_at") or 0))
            store.pop(oldest, None)


def _register_anchor_analysis_receipt(contract: Dict[str, Any]) -> None:
    validated = _validate_anchor_intelligence_contract(contract)
    contract_id = str(validated.get("contract_id") or "")
    source_sha256 = str((validated.get("source") or {}).get("sha256") or "").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", source_sha256):
        raise _VideoEngineError(
            "ANCHOR_SOURCE_HASH_REQUIRED",
            "A leitura visual nao trouxe o SHA-256 da imagem-ancora.",
            status_code=409,
        )
    with _ANCHOR_RECEIPT_LOCK:
        _prune_anchor_receipts()
        _ANCHOR_ANALYSIS_RECEIPTS[contract_id] = {
            "created_at": _t.time(),
            "source_sha256": source_sha256,
            "contract_digest": _anchor_contract_digest(validated),
        }


def _require_anchor_analysis_receipt(contract: Dict[str, Any]) -> Dict[str, Any]:
    validated = _validate_anchor_intelligence_contract(contract)
    contract_id = str(validated.get("contract_id") or "")
    with _ANCHOR_RECEIPT_LOCK:
        _prune_anchor_receipts()
        receipt = dict(_ANCHOR_ANALYSIS_RECEIPTS.get(contract_id) or {})
    if not receipt:
        raise _VideoEngineError(
            "ANCHOR_ANALYSIS_RECEIPT_REQUIRED",
            "Esta ancora nao possui uma leitura visual valida nesta sessao. Analise-a novamente.",
            status_code=409,
            details={"anchor_contract_id": contract_id},
        )
    if receipt.get("contract_digest") != _anchor_contract_digest(validated):
        raise _VideoEngineError(
            "ANCHOR_ANALYSIS_RECEIPT_MISMATCH",
            "O contrato enviado diverge da leitura visual registrada.",
            status_code=409,
        )
    return receipt


def _register_compiled_anchor_receipt(
    contract: Dict[str, Any],
    compiled: Dict[str, Any],
) -> None:
    analysis_receipt = _require_anchor_analysis_receipt(contract)
    contract_id = str(compiled.get("anchor_contract_id") or "")
    if contract_id != str(contract.get("contract_id") or ""):
        raise _VideoEngineError(
            "ANCHOR_COMPILED_CONTRACT_MISMATCH",
            "O prompt compilado nao pertence ao contrato visual informado.",
            status_code=409,
        )
    engine_id = str(compiled.get("engine_id") or "")
    compiler_version = str(compiled.get("compiler_version") or "")
    prompt = str(compiled.get("prompt") or "")
    negative = str(compiled.get("negative_prompt") or "")
    if not engine_id or not compiler_version or not prompt:
        raise _VideoEngineError(
            "ANCHOR_COMPILED_RECEIPT_INVALID",
            "O compilador nao produziu um recibo completo.",
            status_code=409,
        )
    with _ANCHOR_RECEIPT_LOCK:
        _prune_anchor_receipts()
        _ANCHOR_COMPILED_RECEIPTS[contract_id] = {
            "created_at": _t.time(),
            "source_sha256": analysis_receipt["source_sha256"],
            "engine_id": engine_id,
            "compiler_version": compiler_version,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "negative_sha256": hashlib.sha256(negative.encode("utf-8")).hexdigest(),
        }


def _require_compiled_anchor_receipt(
    *,
    engine_id: str,
    anchor_contract_id: str,
    prompt_compiler_version: str,
    prompt: str,
    negative: str,
    image_bytes: bytes | None,
) -> Dict[str, Any]:
    contract_id = str(anchor_contract_id or "").strip()
    compiler_version = str(prompt_compiler_version or "").strip()
    if not contract_id or not compiler_version or image_bytes is None:
        raise _VideoEngineError(
            "ANCHOR_COMPILED_RECEIPT_REQUIRED",
            "Analise a imagem e aplique o prompt compilado antes de gerar o video.",
            status_code=409,
        )
    with _ANCHOR_RECEIPT_LOCK:
        _prune_anchor_receipts()
        receipt = dict(_ANCHOR_COMPILED_RECEIPTS.get(contract_id) or {})
    if not receipt:
        raise _VideoEngineError(
            "ANCHOR_COMPILED_RECEIPT_EXPIRED",
            "O recibo do prompt expirou ou pertence a outra sessao. Analise a ancora novamente.",
            status_code=409,
        )
    actual = {
        "source_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "engine_id": str(engine_id or ""),
        "compiler_version": compiler_version,
        "prompt_sha256": hashlib.sha256(str(prompt or "").encode("utf-8")).hexdigest(),
        "negative_sha256": hashlib.sha256(str(negative or "").encode("utf-8")).hexdigest(),
    }
    mismatches = [key for key, value in actual.items() if receipt.get(key) != value]
    if mismatches:
        raise _VideoEngineError(
            "ANCHOR_COMPILED_RECEIPT_MISMATCH",
            "Imagem, motor ou prompt divergiu do recibo compilado; faca uma nova analise.",
            status_code=409,
            details={"mismatches": mismatches, "anchor_contract_id": contract_id},
        )
    return receipt


DEFAULT_FLUX_VAE = "ae.safetensors"
# A14B I2V/Fun Camera are detected by ComfyUI as WAN21 and consume 16-channel
# latents. The native WAN22 latent builder below is the separate 48-channel path.
WAN21_I2V_VAE = "wan_2.1_vae.safetensors"
DEFAULT_WAN_VAE = "wan2.2_vae.safetensors"
DEFAULT_FLUX_CLIP_1 = "clip_l.safetensors"
DEFAULT_FLUX_CLIP_2 = "t5xxl_fp16.safetensors"
DEFAULT_WAN_CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
os.makedirs(STUDIO_OUTPUT_DIR, exist_ok=True)
os.makedirs(OPERATION_FLAGS_DIR, exist_ok=True)

def _flag_enabled(path: str) -> bool:
    return os.path.exists(path)

def _video_generation_paused() -> bool:
    value = _env_value("PEMARA_VIDEO_GENERATION_PAUSED", "").lower()
    if value in ("1", "true", "yes", "sim", "on"):
        return True
    return _flag_enabled(VIDEO_PAUSE_FLAG)

def _unauthorized_video_engines_enabled() -> bool:
    """Explicit laboratory escape hatch; disabled in the production launcher."""
    return os.environ.get("STUDIO_ENABLE_UNAUTHORIZED_VIDEO_ENGINES", "0") == "1"

def _wan_reserve_engine_enabled() -> bool:
    """Legacy compatibility hook; Wan was removed by owner decision."""
    return False

def _retired_wan_model(model: str) -> bool:
    selected = str(model or "").strip().lower()
    tokens = re.split(r"[^a-z0-9]+", selected)
    return bool(
        model in WAN_RETIRED_MODELS
        or "lightx2v" in selected
        or any(
            token == "wan"
            or token.startswith("wan2")
            or token.startswith("wanvideo")
            or token.startswith("wananimate")
            for token in tokens
        )
    )


def _is_minimax_h3_model(model: str) -> bool:
    return str(model or "").strip() in {
        MINIMAX_H3_MODEL_NAME,
        MINIMAX_H3_REF2VA_MODEL_NAME,
    }


def _video_engine_authorized(model: str) -> bool:
    selected = str(model or "").strip()
    return bool(_is_minimax_h3_model(selected))

def _require_authorized_video_engine(model: str) -> None:
    if not _video_engine_authorized(model):
        raise RuntimeError(
            "Motor de video nao autorizado. Escolha explicitamente MiniMax H3; "
            "nao existe fallback automatico."
        )

def _pemara_estudio_40anos_enabled() -> bool:
    """Retired Wan-era compatibility profile."""
    return False

def _video_pause_message() -> str:
    return (
        "Geracao e ferramentas de video pausadas ate segunda ordem. "
        "Prioridade atual: loja, fotos originais, cards e anuncios fieis."
    )

def _video_method_profiles() -> Dict[str, Any]:
    return {
        "minimax_h3_take_contract": {
            "label": "Workflow MiniMax H3 por takes",
            "status": "active_production_contract",
            "requires": [
                "roteiro aprovado e continuidade entre takes",
                "start_frame aprovado",
                "JSON lateral do start_frame",
                "end_frame quando houver transformacao ou revelacao",
                "shot_contract com sujeito, acao, cena, camera, luz e motion beats",
                "prompt compilado pela skill oficial h3-prompt-writing",
                "acao util em 0-30%, 30-70% e 70-100%",
                "ffprobe e contact sheet antes de aprovar",
            ],
            "forbidden": [
                "prompt unico longo para producao",
                "imagem viva sem evento fisico",
                "crossfade, freeze frame, cauda estatica ou reset de movimento",
                "upscale, Foley ou montagem final antes da aprovacao visual",
            ],
            "pipeline": [
                "roteiro",
                "fotos ancora",
                "prompt H3 oficial",
                "preflight sem GPU",
                "MiniMax H3 24 fps",
                "QC humano",
                "conectores H3 continuos",
                "RIFE 4.6 + RealESRGAN + NVENC",
                "HunyuanVideo-Foley XXL",
                "master e rollback",
            ],
            "docs": [
                "E:/Pemara/maestro/pemara/docs/MAESTRO_MINIMAX_H3_WORKFLOW.md",
                "E:/Pemara/maestro/pemara/docs/operacao/RESTAURAR_MAESTRO_MINIMAX_H3_PC_NOVO.md",
            ],
        },
        "veo_kling_shot_contract": {
            "label": "Metodo historico Veo/Kling",
            "status": "reference_only_superseded_by_minimax_h3_take_contract",
            "local_use": "referencia de linguagem de camera; nao e motor nem perfil ativo",
        },
        "veo_reference": {
            "label": "Veo reference workflow",
            "supports": ["text-to-video", "image-to-video", "first_last_frame", "visual_references"],
            "local_use": "referencia de metodo; nao consome GPU local",
        },
        "kling_reference": {
            "label": "Kling reference workflow",
            "supports": ["image-to-video", "start_end_frame", "camera_control", "negative_prompt"],
            "local_use": "referencia de metodo; nao consome GPU local",
        },
    }

def _read_env_file_value(chave: str) -> str:
    for arquivo in (
        os.path.join(BASE_DIR, ".env"),
        os.path.join(os.path.dirname(BASE_DIR), ".env"),
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", ".env"),
    ):
        try:
            if not os.path.exists(arquivo):
                continue
            with open(arquivo, "r", encoding="utf-8", errors="ignore") as handle:
                for linha in handle:
                    linha = linha.strip()
                    if not linha or linha.startswith("#") or "=" not in linha:
                        continue
                    nome, valor = linha.split("=", 1)
                    if nome.strip() == chave:
                        return valor.strip().strip('"').strip("'")
        except Exception:
            continue
    return ""

def _env_value(chave: str, padrao: str = "") -> str:
    return os.environ.get(chave, "").strip() or _read_env_file_value(chave) or padrao

NVIDIA_BASE_URL = _env_value("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
NVIDIA_DEFAULT_MODEL = _env_value("NVIDIA_DEFAULT_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1.5")
NVIDIA_FAST_MODEL = _env_value("NVIDIA_FAST_MODEL", "meta/llama-3.1-8b-instruct")
NVIDIA_REASONING_MODEL = _env_value("NVIDIA_REASONING_MODEL", NVIDIA_DEFAULT_MODEL)
NVIDIA_VISION_MODEL = _env_value("NVIDIA_VISION_MODEL", "meta/llama-3.2-90b-vision-instruct")

def _model_files(folder: str, suffixes=(".safetensors", ".ckpt", ".pt")) -> List[str]:
    roots = [os.path.join(COMFY_MODELS_DIR, folder)]
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if name.lower().endswith(suffixes):
                    rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
                    found.append(rel)
    return sorted(dict.fromkeys(found), key=str.lower)

def _video_model_files(diffusion_models: List[str] = None, unet_models: List[str] = None) -> List[str]:
    diffusion_models = diffusion_models if diffusion_models is not None else _model_files("diffusion_models")
    unet_models = unet_models if unet_models is not None else _model_files("unet", suffixes=(".safetensors", ".ckpt", ".pt", ".gguf"))
    video_names = (
        "wan", "ltx", "hunyuan", "video", "t2v", "i2v", "ti2v",
        "minimax", "h3", "fl2va",
    )
    video_models = [
        model for model in diffusion_models
        if any(token in model.lower() for token in video_names)
    ]
    for model in unet_models:
        low = model.lower()
        if low.endswith(".gguf") and any(token in low for token in video_names):
            video_models.append(model)
    return sorted(dict.fromkeys(video_models), key=str.lower)

def _nvidia_headers() -> Dict[str, str]:
    api_key = _env_value("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("NVIDIA API nao configurada. Defina NVIDIA_API_KEY no .env do Maestro.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _nvidia_provider_status() -> Dict[str, Any]:
    configured = bool(_env_value("NVIDIA_API_KEY"))
    return {
        "nvidia_nim": {
            "label": "NVIDIA NIM / Build API",
            "configured": configured,
            "needs": [] if configured else ["NVIDIA_API_KEY"],
            "base_url": NVIDIA_BASE_URL,
            "defaults": {
                "fast": NVIDIA_FAST_MODEL,
                "reasoning": NVIDIA_REASONING_MODEL,
                "vision": NVIDIA_VISION_MODEL,
            },
            "use_cases": [
                "planejamento de treinos sem usar GPU local",
                "geracao e revisao de prompts",
                "auditoria de arquivos, logs e roteiros",
                "analise de imagens via modelo vision quando disponivel",
            ],
        }
    }

def _nvidia_request_json(path: str, payload: Dict[str, Any] | None = None, timeout: int = 60, method: str = "POST") -> Dict[str, Any]:
    url = f"{NVIDIA_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_nvidia_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NVIDIA HTTP {e.code}: {body[:1200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"NVIDIA indisponivel: {e}") from e
    return json.loads(raw.decode("utf-8")) if raw else {}

def _nvidia_chat(
    prompt: str,
    *,
    model: str = "",
    system: str = "",
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    selected_model = model or NVIDIA_DEFAULT_MODEL
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": _safe_float(temperature, 0.2, 0.0, 2.0),
        "max_tokens": _safe_int(max_tokens, 1200, 64, 8192),
        "stream": False,
    }
    data = _nvidia_request_json("/chat/completions", payload, timeout=120)
    choices = data.get("choices") or []
    content = ""
    if choices:
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
    return {
        "ok": True,
        "provider": "nvidia_nim",
        "model": selected_model,
        "content": content,
        "usage": data.get("usage") or {},
    }


def _nvidia_vision(image_bytes: bytes, mime_type: str, intent: str) -> Dict[str, Any]:
    """Analyze one opt-in anchor without persisting or logging its pixels."""

    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": _build_anchor_vision_messages(image_bytes, mime_type, intent),
        "temperature": 0.0,
        "max_tokens": 4096,
        "stream": False,
    }
    data = _nvidia_request_json("/chat/completions", payload, timeout=180)
    choices = data.get("choices") or []
    content = ""
    if choices:
        content = str(((choices[0].get("message") or {}).get("content") or "")).strip()
    return {
        "provider": "nvidia_nim",
        "model": NVIDIA_VISION_MODEL,
        "evidence": _parse_anchor_vision_response(content),
        "usage": data.get("usage") or {},
    }

def _unet_loader_node(model: str, dtype: str = "default") -> Dict[str, Any]:
    if model.lower().endswith(".gguf"):
        return {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model}}
    return {"class_type": "UNETLoader", "inputs": {"unet_name": model, "weight_dtype": dtype}}

def _wan22_i2v_a14b_pair(model: str) -> Tuple[str, str] | None:
    model_name = model or ""
    normalized = model_name.lower()
    is_gguf = normalized.endswith(".gguf")
    is_native = normalized.endswith(".safetensors")
    if not (is_gguf or is_native):
        return None

    if is_gguf:
        if "a14b" not in normalized and not ("i2v" in normalized and "14b" in normalized):
            return None
        if "highnoise" in normalized:
            high = model_name
            low_model = model_name.replace("HighNoise", "LowNoise")
        elif "high_noise" in normalized:
            high = model_name
            low_model = model_name.replace("high_noise", "low_noise")
        elif "lownoise" in normalized:
            low_model = model_name
            high = model_name.replace("LowNoise", "HighNoise")
        elif "low_noise" in normalized:
            low_model = model_name
            high = model_name.replace("low_noise", "high_noise")
        else:
            return None
        model_dir = os.path.join(COMFY_MODELS_DIR, "unet")
    elif "i2v" in normalized and "14b" in normalized:
        if "high_noise" in normalized:
            high = model_name
            low_model = model_name.replace("high_noise", "low_noise")
        elif "low_noise" in normalized:
            low_model = model_name
            high = model_name.replace("low_noise", "high_noise")
        else:
            return None
        model_dir = os.path.join(COMFY_MODELS_DIR, "diffusion_models")
    else:
        return None

    high_path = os.path.join(model_dir, high.replace("/", os.sep))
    low_path = os.path.join(model_dir, low_model.replace("/", os.sep))
    if not os.path.exists(high_path) or not os.path.exists(low_path):
        return None
    return high, low_model

def _wan22_fun_camera_pair(model: str) -> Tuple[str, str] | None:
    if model not in (WAN22_FUN_CAMERA_HIGH_MODEL, WAN22_FUN_CAMERA_LOW_MODEL):
        return None
    root = os.path.join(COMFY_MODELS_DIR, "diffusion_models")
    high_path = os.path.join(root, WAN22_FUN_CAMERA_HIGH_MODEL)
    low_path = os.path.join(root, WAN22_FUN_CAMERA_LOW_MODEL)
    if not os.path.isfile(high_path) or not os.path.isfile(low_path):
        return None
    return WAN22_FUN_CAMERA_HIGH_MODEL, WAN22_FUN_CAMERA_LOW_MODEL

def _safe_int(value: Any, default: int, min_v: int, max_v: int, step: int = 1) -> int:
    try:
        n = int(value)
    except Exception:
        n = default
    n = max(min_v, min(max_v, n))
    if step > 1:
        n = max(min_v, (n // step) * step)
    return n

def _safe_video_dimension(value: Any, default: int, min_v: int, max_v: int) -> int:
    # Wan I2V accepts 16-aligned dimensions; using 32 here turned 720p into 1280x704.
    return _safe_int(value, default, min_v, max_v, 16)

def _safe_float(value: Any, default: float, min_v: float, max_v: float) -> float:
    try:
        n = float(value)
    except Exception:
        n = default
    return max(min_v, min(max_v, n))


def _nearest_temporal_frame_count(
    duration_seconds: float,
    fps: float,
    *,
    stride: int,
    offset: int,
    minimum: int,
    maximum: int,
    extra_valid_frames: Tuple[int, ...] = (),
) -> Tuple[int, float]:
    """Return the closest valid frame count and its effective duration."""
    try:
        requested_duration = float(duration_seconds)
        rate = float(fps)
    except (TypeError, ValueError) as exc:
        raise ValueError("Duracao e FPS do video devem ser numericos.") from exc
    if not math.isfinite(requested_duration) or requested_duration <= 0:
        raise ValueError("A duracao do video deve ser maior que zero.")
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("O FPS do video deve ser maior que zero.")
    if stride <= 0 or minimum > maximum:
        raise ValueError("Grade temporal interna invalida.")

    first = int(offset)
    if first < minimum:
        first += math.ceil((minimum - first) / stride) * stride
    valid_frames = list(range(first, maximum + 1, stride))
    valid_frames.extend(
        int(value)
        for value in extra_valid_frames
        if minimum <= int(value)
    )
    valid_frames = sorted(set(valid_frames))
    if not valid_frames:
        raise ValueError("A grade temporal nao possui quadros validos.")

    target = max(1, int(round(requested_duration * rate)) + 1)
    selected = min(
        valid_frames,
        key=lambda value: (
            abs(value - target),
            0 if value >= target else 1,
            value,
        ),
    )
    return selected, (selected - 1) / rate


def _minimax_h3_timing(
    duration_seconds: float,
    fps: float,
    *,
    allow_owner_long_window: bool = False,
) -> Tuple[int, float, float]:
    # MiniMax H3 trains and constructs its AV latent on a fixed 24 FPS clock.
    # A delivery FPS must never be used to shorten the generated scene.
    validate_video_fps(fps, classic_only=True)
    rate = MINIMAX_H3_FPS
    extras = (MINIMAX_H3_OWNER_LONG_MAX_FRAMES,) if allow_owner_long_window else ()
    frames, effective_duration = _nearest_temporal_frame_count(
        duration_seconds,
        rate,
        stride=MINIMAX_H3_TEMPORAL_STRIDE,
        offset=MINIMAX_H3_TEMPORAL_OFFSET,
        minimum=MINIMAX_H3_MIN_FRAMES,
        maximum=MINIMAX_H3_TRAINED_MAX_FRAMES,
        extra_valid_frames=extras,
    )
    return frames, rate, effective_duration

def _max_upload_image_bytes() -> int:
    return _safe_int(os.environ.get("STUDIO_MAX_UPLOAD_IMAGE_MB", "25"), 25, 1, 80) * 1024 * 1024

async def _read_upload_bounded(
    upload: UploadFile | None,
    label: str,
    max_bytes: int | None = None,
) -> bytes | None:
    """Read an upload without allowing Starlette to materialize an unbounded body."""
    if upload is None:
        return None
    limit = max_bytes if max_bytes is not None else min(
        _GEN_JOB_INPUT_MAX_BYTES,
        _max_upload_image_bytes(),
    )
    chunks: List[bytes] = []
    total = 0
    try:
        while True:
            chunk = await upload.read(min(1024 * 1024, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ValueError(
                    f"{label} excede o limite de {limit // (1024 * 1024)} MB."
                )
        return b"".join(chunks)
    finally:
        try:
            await upload.close()
        except Exception:
            pass

def _open_valid_upload_image(image_bytes: bytes | None, original_name: str = "") -> Image.Image:
    if not image_bytes:
        raise ValueError("Imagem base vazia.")
    if len(image_bytes) > _max_upload_image_bytes():
        raise ValueError("Imagem base excede o limite de tamanho.")
    ext = os.path.splitext(original_name or "")[1].lower()
    if ext in {".svg", ".html", ".htm", ".xml"}:
        raise ValueError("Formato de imagem nao permitido.")
    try:
        with Image.open(BytesIO(image_bytes)) as probe:
            probe.verify()
        with Image.open(BytesIO(image_bytes)) as img:
            if img.width < 8 or img.height < 8:
                raise ValueError("Imagem base pequena demais.")
            if img.width * img.height > 60_000_000:
                raise ValueError("Imagem base grande demais em pixels.")
            return ImageOps.exif_transpose(img).convert("RGB")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Imagem base invalida: {exc}") from exc

def _save_comfy_input_image(image_bytes: bytes | None, original_name: str = "", size: Tuple[int, int] | None = None) -> str:
    if not image_bytes:
        return ""
    uploads_dir = os.path.join(COMFY_INPUT_DIR, "maestro_uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in os.path.splitext(original_name or "base")[0])[:48]
    rel_name = f"maestro_uploads/{safe_stem}_{uuid.uuid4().hex[:10]}.png"
    path = os.path.join(COMFY_INPUT_DIR, *rel_name.split("/"))
    img = _open_valid_upload_image(image_bytes, original_name)
    if size:
        img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    img.save(path, "PNG", optimize=True)
    return rel_name


def _save_comfy_input_audio(audio_bytes: bytes | None, original_name: str = "") -> str:
    """Materialize one already approved audio file inside Comfy's input root."""

    if not audio_bytes:
        return ""
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise ValueError("Audio de condicionamento LTX excede 25 MB.")
    suffix = Path(original_name or "approved.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}:
        raise ValueError("Formato do audio aprovado nao e aceito pelo LTX IA2V.")
    uploads_dir = Path(COMFY_INPUT_DIR) / "maestro_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in Path(original_name or "approved_audio").stem
    )[:48]
    digest = hashlib.sha256(audio_bytes).hexdigest()[:16]
    filename = f"{safe_stem}_{digest}{suffix}"
    destination = (uploads_dir / filename).resolve()
    input_root = Path(COMFY_INPUT_DIR).resolve()
    if not destination.is_relative_to(input_root):
        raise ValueError("Destino do audio LTX IA2V saiu do input autorizado.")
    if destination.is_file():
        if destination.read_bytes() != audio_bytes:
            raise RuntimeError("Audio Comfy existente diverge do arquivo aprovado.")
    else:
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(audio_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return f"maestro_uploads/{filename}"


def _save_comfy_input_video(video_bytes: bytes | None, original_name: str = "") -> str:
    """Materialize an approved motion reference inside Comfy's input root."""

    if not video_bytes:
        return ""
    if len(video_bytes) > 512 * 1024 * 1024:
        raise ValueError("Video aprovado de referencia/pose excede 512 MB.")
    suffix = Path(original_name or "approved_motion.mp4").suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".webm"}:
        raise ValueError("Formato do video aprovado de referencia/pose nao e aceito.")
    uploads_dir = Path(COMFY_INPUT_DIR) / "maestro_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in Path(original_name or "approved_motion").stem
    )[:48]
    digest = hashlib.sha256(video_bytes).hexdigest()[:16]
    filename = f"{safe_stem}_{digest}{suffix}"
    destination = (uploads_dir / filename).resolve()
    input_root = Path(COMFY_INPUT_DIR).resolve()
    if not destination.is_relative_to(input_root):
        raise ValueError("Destino do video aprovado saiu do input autorizado.")
    if destination.is_file():
        if destination.read_bytes() != video_bytes:
            raise RuntimeError("Video Comfy existente diverge do driver/pose aprovado.")
    else:
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(video_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return f"maestro_uploads/{filename}"

def _font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\bahnschrift.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for path in candidates:
        try:
            if path and os.path.exists(path):
                return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 12) -> List[str]:
    lines: List[str] = []
    for paragraph in (text or "").splitlines():
        words = paragraph.split()
        if not words:
            continue
        line = ""
        for word in words:
            trial = (line + " " + word).strip()
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] > max_width and line:
                lines.append(line)
                line = word
            else:
                line = trial
            if len(lines) >= max_lines:
                return lines
        if line:
            lines.append(line)
        if len(lines) >= max_lines:
            return lines
    return lines

def _save_marketing_reference_image(
    image_bytes: bytes | None,
    original_name: str,
    prompt: str,
    size: Tuple[int, int],
) -> str:
    if not image_bytes:
        return ""
    uploads_dir = os.path.join(COMFY_INPUT_DIR, "maestro_marketing")
    os.makedirs(uploads_dir, exist_ok=True)
    safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in os.path.splitext(original_name or "produto")[0])[:48]
    rel_name = f"maestro_marketing/{safe_stem}_{uuid.uuid4().hex[:10]}_reference.png"
    path = os.path.join(COMFY_INPUT_DIR, *rel_name.split("/"))
    width, height = size
    board = Image.new("RGB", (width, height), "#070a0f")
    draw = ImageDraw.Draw(board)
    draw.rectangle((42, 42, width - 42, height - 42), outline="#1b2633", width=3)
    panel = (74, 94, width - 74, min(height - 240, 1040))
    draw.rectangle(panel, fill="#f7f8fa")
    draw.rectangle((74, panel[3], width - 74, height - 94), fill="#0c1118")
    img = _open_valid_upload_image(image_bytes, original_name)
    max_w = panel[2] - panel[0] - 72
    max_h = panel[3] - panel[1] - 72
    scale = min(max_w / max(1, img.width), max_h / max(1, img.height))
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.LANCZOS)
    px = panel[0] + ((panel[2] - panel[0]) - img.width) // 2
    py = panel[1] + ((panel[3] - panel[1]) - img.height) // 2
    board.paste(img, (px, py))
    board.save(path, "PNG", optimize=True)
    return rel_name

def _marketing_card_prompt(prompt: str) -> str:
    return f"""
Create one finished professional 4:5 social media sales ad for Pemara Tech.
Use the uploaded image only as the real product visual source. Preserve the real product identity, category, shape, colors, box, visible brand and model.
Render the final card as one integrated commercial image, not a collage, not a screenshot and not pasted elements.

Render only the exact large readable text requested by the operator:
{prompt}

Mandatory visual rules:
- premium hardware store ad, dark graphite tech background, orange and green accent lights;
- product large, clean, uncropped, with natural shadow/contact light;
- closed panels only, no broken rectangles and no text crossing the product;
- crisp high-contrast typography, straight lines, no misspelled Portuguese;
- clear hierarchy: product name, price, installment, site;
- include PEMARATECH.COM.BR and Rio Preto e Regiao when present in the operator text;
- include a small clean autism infinity symbol as Pemara brand mark.
- never change prices, product model, website or region;
- no extra slogans, no extra small text and no random footer words.

Do not invent technologies, awards, fake specs, fake discounts, people, hands, mouse, laptop or unrelated products.
""".strip()

def _marketing_card_negative(negative: str) -> str:
    base = """
wrong product, changed product category, mouse, notebook, laptop, keyboard, monitor, person, hand, face,
fake logo, fake technology, fake award, fake discount, bad Portuguese, misspelled words, duplicated text,
broken rectangles, open boxes, cheap collage, paint style, pasted logo, text over product, cropped product,
residue around product, watermark, QR code, invented claim, unreadable price, wrong website
91,000, 11,000, pemara rtx, hartinet, wizo, random website, fake footer
""".strip()
    return f"{base}, {negative}" if negative else base

def _safe_comfy_output_path(filename: str, subfolder: str = "", folder_type: str = "output") -> str:
    if folder_type != "output":
        return ""
    if not filename or Path(filename).name != filename or any(x in filename for x in ("..", "/", "\\")):
        return ""
    normalized_subfolder = str(subfolder or "").replace("\\", "/")
    if normalized_subfolder.startswith("/"):
        return ""
    normalized_subfolder = normalized_subfolder.rstrip("/")
    subfolder_path = Path(normalized_subfolder) if normalized_subfolder else Path()
    if (
        subfolder_path.is_absolute()
        or subfolder_path.drive
        or any(part in {"", ".", ".."} for part in subfolder_path.parts)
    ):
        return ""
    try:
        root = Path(COMFY_OUTPUT_DIR).resolve(strict=True)
        path = (root / subfolder_path / filename).resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        return ""
    if not path.is_relative_to(root) or not path.is_file():
        return ""
    return str(path)

def _safe_studio_output_path(rel_path: str) -> str:
    if not rel_path or rel_path.startswith(("/", "\\")) or ".." in rel_path:
        return ""
    root = os.path.abspath(STUDIO_OUTPUT_DIR)
    path = os.path.abspath(os.path.join(root, *rel_path.replace("\\", "/").split("/")))
    if os.path.commonpath([root, path]) != root:
        return ""
    return path

def _mime_to_extension(media_type: str, fallback: str = ".mp3") -> str:
    clean_type = (media_type or "").split(";", 1)[0].strip().lower()
    if clean_type in ("audio/mpeg", "audio/mp3"):
        return ".mp3"
    if clean_type in ("audio/wav", "audio/x-wav", "audio/wave"):
        return ".wav"
    if clean_type == "audio/flac":
        return ".flac"
    if clean_type == "audio/ogg":
        return ".ogg"
    guessed = mimetypes.guess_extension(clean_type) if clean_type else ""
    return guessed or fallback

def _write_studio_output(kind: str, data: bytes, extension: str, media_type: str, prefix: str) -> Dict[str, Any]:
    safe_kind = "".join(c if c.isalnum() or c in "-_" else "_" for c in (kind or "asset"))[:32]
    safe_prefix = "".join(c if c.isalnum() or c in "-_" else "_" for c in (prefix or safe_kind))[:48]
    extension = extension if extension.startswith(".") else f".{extension}"
    folder = os.path.join(STUDIO_OUTPUT_DIR, safe_kind, _t.strftime("%Y%m%d"))
    os.makedirs(folder, exist_ok=True)
    filename = f"{safe_prefix}_{_t.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}{extension}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as handle:
        handle.write(data)
    if kind in {"image", "video"}:
        _finish_required_media(path)
    rel_path = os.path.relpath(path, STUDIO_OUTPUT_DIR).replace(os.sep, "/")
    query = urllib.parse.urlencode({"path": rel_path})
    return {
        "kind": kind,
        "filename": filename,
        "path": rel_path,
        "url": f"/api/generative/output?{query}",
        "media_type": media_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
    }

def _append_prompt_avoid(prompt: str, negative: str) -> str:
    prompt = (prompt or "").strip()
    negative = (negative or "").strip()
    return prompt if not negative else f"{prompt}\nAvoid: {negative}"

def _post_json_binary(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int) -> Tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers.get_content_type()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Provider HTTP {e.code}: {body[:1200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Provider indisponivel: {e}") from e

def _google_access_token() -> str:
    token = _env_value("GOOGLE_OAUTH_ACCESS_TOKEN")
    if token:
        return token
    try:
        proc = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return ""

def _audio_provider_status() -> Dict[str, Any]:
    from music_creation import provider_status
    eleven_key = bool(_env_value("ELEVENLABS_API_KEY"))
    google_project = bool(_env_value("GOOGLE_CLOUD_PROJECT") or _env_value("VERTEX_PROJECT_ID"))
    google_location = bool(_env_value("GOOGLE_CLOUD_LOCATION", "us-central1"))
    google_token = bool(_env_value("GOOGLE_OAUTH_ACCESS_TOKEN")) or bool(shutil.which("gcloud"))
    stable_local = _env_value("STABLE_AUDIO_LOCAL_URL")
    stable_key = bool(_env_value("STABILITY_API_KEY"))
    audiogen_local = _env_value("AUDIOGEN_LOCAL_URL")
    return {
        **provider_status(),
        LEVO2_PROVIDER_ID: _levo2_status(),
        "lyria": {
            "label": "Google Lyria / Vertex",
            "configured": google_project and google_location and google_token,
            "role": "music_premium",
            "needs": [
                item for item, ok in (
                    ("GOOGLE_CLOUD_PROJECT ou VERTEX_PROJECT_ID", google_project),
                    ("GOOGLE_CLOUD_LOCATION", google_location),
                    ("GOOGLE_OAUTH_ACCESS_TOKEN ou gcloud auth", google_token),
                )
                if not ok
            ],
            "formats": ["wav"],
            "max_duration_seconds": 180,
            "modes": ["music"],
        },
        "stable_audio": {
            "label": "Stable Audio SFX/Music",
            "configured": bool(stable_local or stable_key),
            "role": "sfx_preferred",
            "needs": [] if (stable_local or stable_key) else ["STABLE_AUDIO_LOCAL_URL ou STABILITY_API_KEY"],
            "formats": ["wav", "mp3"],
            "max_duration_seconds": 360,
            "modes": ["music", "sfx"],
        },
        "audiogen": {
            "label": "AudioCraft AudioGen Local",
            "configured": bool(audiogen_local),
            "role": "sfx_local_experimental",
            "needs": [] if audiogen_local else ["AUDIOGEN_LOCAL_URL"],
            "formats": ["wav"],
            "max_duration_seconds": 30,
            "modes": ["sfx"],
        },
        "eleven_sfx": {
            "label": "ElevenLabs SFX",
            "configured": eleven_key,
            "role": "sfx_fallback",
            "needs": [] if eleven_key else ["ELEVENLABS_API_KEY"],
            "formats": ["mp3"],
            "modes": ["sfx"],
        },
        "eleven_music": {
            "label": "ElevenLabs Music",
            "configured": eleven_key,
            "role": "music_fallback",
            "needs": [] if eleven_key else ["ELEVENLABS_API_KEY"],
            "formats": ["mp3"],
            "modes": ["music"],
        },
    }

def _finish_required_media(path: str | Path, *, lease_job_id: str = "") -> Dict[str, Any]:
    existing = _dlss5.valid_receipt(path)
    if existing:
        return existing
    reservation = lease_job_id or ("dlss5_" + uuid.uuid4().hex)
    _GPU_LEASE_REGISTRY.acquire(owner="maestro_studio", operation="dlss5_required", job_id=reservation)
    try:
        queue = _comfy_request("/queue", timeout=10)
        if queue.get("queue_running") or queue.get("queue_pending"):
            raise _dlss5.DLSS5RequiredError("DLSS 5 obrigatorio aguardando GPU: ComfyUI ocupado; fonte preservada, sem entrega sem tratamento.")
        _comfy_request("/free", {"unload_models": True, "free_memory": True}, timeout=15)
        return _dlss5.finish_file(path)
    finally:
        if not lease_job_id:
            _GPU_LEASE_REGISTRY.release(reservation)


def _finalize_video_mp4(outputs: List[Dict[str, Any]], fps: int = 30, width: int = 1280, height: int = 720) -> List[Dict[str, Any]]:
    finalized: List[Dict[str, Any]] = []
    ff = get_ffmpeg()
    if not nvenc_ok(ff):
        raise RuntimeError(
            "H.264 NVENC indisponivel: o acabamento de video foi interrompido; "
            "fallback silencioso para encoder CPU e proibido."
        )
    fps = int(round(validate_video_fps(fps or 30)))
    for item in outputs:
        if item.get("kind") != "video":
            finalized.append(item)
            continue
        filename = item.get("filename", "")
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".mp4":
            src = _safe_comfy_output_path(filename, item.get("subfolder", ""), item.get("type", "output"))
            _finish_required_media(src)
            finalized.append(item)
            continue
        src = _safe_comfy_output_path(filename, item.get("subfolder", ""), item.get("type", "output"))
        if not src or not os.path.exists(src):
            finalized.append(item)
            continue
        dst_name = f"{os.path.splitext(filename)[0]}_{width}x{height}_{fps}fps.mp4"
        dst = os.path.join(os.path.dirname(src), dst_name)
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1,format=yuv420p"
        def run_encode() -> None:
            cmd = [ff, "-y", "-i", src, "-vf", vf, "-an", "-c:v", "h264_nvenc"]
            cmd.extend(["-preset", "p5", "-cq", "18", "-b:v", "0"])
            cmd.extend(["-movflags", "+faststart", dst])
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)

        run_encode()
        _dlss5.carry_receipt(src, dst)
        subfolder = item.get("subfolder", "")
        query = urllib.parse.urlencode({"filename": dst_name, "subfolder": subfolder, "type": "output"})
        finalized.append({
            **item,
            "filename": dst_name,
            "kind": "video",
            "type": "output",
            "url": f"/api/generative/comfy-view?{query}",
            "final_format": "mp4",
            "fps": fps,
            "width": width,
            "height": height,
        })
    return finalized

def _set_gen_job(job_id: str, **updates: Any) -> None:
    # A late phase may report a lower local percentage than the renderer. Keep
    # the public progress monotonic so the Maestro never appears to go backwards.
    if "progress" in updates:
        current = _GEN_JOB_STORE.get(job_id) or {}
        current_status = str(current.get("status") or "")
        next_status = str(updates.get("status") or current_status)
        if current_status not in {"done", "error", "canceled"} and next_status not in {
            "done", "error", "canceled"
        }:
            updates["progress"] = max(
                int(current.get("progress", 0) or 0),
                int(updates.get("progress", 0) or 0),
            )
    updates.setdefault("worker_pid", os.getpid())
    _GEN_JOB_STORE.update(job_id, **updates)

def _get_gen_job(job_id: str) -> Dict[str, Any] | None:
    return _GEN_JOB_STORE.get(job_id)

def _comfy_request(path: str, payload: Dict[str, Any] | None = None, timeout: int = 30) -> Dict[str, Any]:
    if path == "/prompt" and payload is not None:
        # The runtime hook covers SaveImage/SaveVideo/SaveWEBM and imported graphs.
        # Refuse submission if that required component failed to load.
        policy = _comfy_request("/object_info/PemaraDLSS5Policy", timeout=15)
        if "PemaraDLSS5Policy" not in policy:
            raise _dlss5.DLSS5RequiredError("DLSS 5 obrigatorio ausente no runtime ativo; envio bloqueado.")
        _dlss5.preflight()
    url = f"{COMFY_URL}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ComfyUI HTTP {e.code}: {body[:800]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"ComfyUI indisponivel em {COMFY_URL}: {e}") from e
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))

def _comfy_online() -> Tuple[bool, Dict[str, Any] | str]:
    try:
        return True, _comfy_request("/system_stats", timeout=5)
    except Exception as e:
        return False, str(e)


def _prepare_comfy_gpu_for_mova(
    *,
    job_id: str = "",
    cancel_event: threading.Event | None = None,
    wait_for_queue: bool = False,
) -> None:
    """Release idle Comfy allocations without ever interrupting its active queue."""

    waiting_announced = False
    while True:
        try:
            queue = _comfy_request("/queue", timeout=10)
        except Exception:
            # ComfyUI offline cannot own an active queue or reserve live CUDA memory.
            return
        running = list(queue.get("queue_running") or [])
        pending = list(queue.get("queue_pending") or [])
        if not running and not pending:
            break
        if not wait_for_queue:
            raise RuntimeError(
                "MOVA aguardando GPU: finalize ou cancele a fila atual do ComfyUI."
            )
        if cancel_event is not None and cancel_event.is_set():
            raise GenerationCancelled("Trabalho cancelado enquanto aguardava a fila do ComfyUI.")
        if job_id:
            _GPU_LEASE_REGISTRY.heartbeat(job_id)
            if not waiting_announced:
                _GEN_JOB_STORE.update(
                    job_id,
                    status="queued",
                    progress=2,
                    message=(
                        "Aguardando a fila ativa do ComfyUI terminar; "
                        "nenhum processo sera interrompido."
                    ),
                    comfy_queue_waiting=True,
                )
                waiting_announced = True
        if cancel_event is not None:
            cancel_event.wait(5.0)
        else:
            _t.sleep(5.0)
    if job_id and waiting_announced:
        _GEN_JOB_STORE.update(job_id, comfy_queue_waiting=False)
    _comfy_request(
        "/free",
        {"unload_models": True, "free_memory": True},
        timeout=10,
    )


def _comfy_loader_has_model(class_type: str, input_name: str, model_name: str) -> bool:
    try:
        info = _comfy_request(f"/object_info/{urllib.parse.quote(class_type)}", timeout=8)
        choices = info[class_type]["input"]["required"][input_name][0]
        return model_name in choices
    except (KeyError, TypeError, RuntimeError, urllib.error.URLError):
        return False


def _hunyuan15_ready_in_comfy() -> bool:
    checks = (
        ("UNETLoader", "unet_name", HUNYUAN15_I2V_MODEL),
        ("VAELoader", "vae_name", HUNYUAN15_VAE),
        ("DualCLIPLoader", "clip_name1", QWEN25_VL_ENCODER),
        ("DualCLIPLoader", "clip_name1", HUNYUAN15_TEXT_ENCODER),
        ("CLIPVisionLoader", "clip_name", HUNYUAN15_VISION_ENCODER),
    )
    return all(_comfy_loader_has_model(*item) for item in checks)


def _wan22_production_ready() -> bool:
    high, low = _wan22_i2v_a14b_pair(WAN22_PRODUCTION_MODEL) or ("", "")
    folder = "unet" if WAN22_PRODUCTION_MODEL.lower().endswith(".gguf") else "diffusion_models"
    available = set(_model_files(folder, suffixes=(".safetensors", ".ckpt", ".pt", ".gguf")))
    return bool(high and low and high in available and low in available)

def _extract_comfy_outputs(history_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    outputs = history_item.get("outputs", {}) if history_item else {}
    for node_id, node_out in outputs.items():
        text_items=node_out.get("text", [])
        if isinstance(text_items,str): text_items=[text_items]
        if isinstance(text_items,list):
            for text_item in text_items:
                if isinstance(text_item,str) and text_item.strip():
                    results.append({"node":str(node_id),"kind":"text","text":text_item})
        for key, media in (
            ("images", "image"),
            ("gifs", "video"),
            ("videos", "video"),
            ("animated", "video"),
            ("audio", "audio"),
            ("latents", "latent"),
        ):
            for item in node_out.get(key, []) or []:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename")
                if not filename:
                    continue
                subfolder = item.get("subfolder", "")
                folder_type = item.get("type", "output")
                if folder_type == "input":
                    continue
                query = urllib.parse.urlencode({
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": folder_type,
                })
                ext = os.path.splitext(filename)[1].lower()
                resolved_media = "video" if ext in (".webm", ".mp4", ".mov", ".mkv", ".gif", ".avi") else media
                if ext in (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus"):
                    resolved_media = "audio"
                if resolved_media in {"image", "video"}:
                    local = _safe_comfy_output_path(filename, subfolder, folder_type)
                    if not local or not _dlss5.valid_receipt(local):
                        raise _dlss5.DLSS5RequiredError("Saida visual sem recibo DLSS 5 valido; nao pode ser entregue como concluida.")
                results.append({
                    "node": node_id,
                    "kind": resolved_media,
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": folder_type,
                    "url": f"/api/generative/comfy-view?{query}",
                })
    return results

def _comfy_queue_prompt_order(queue_payload: Dict[str, Any], key: str) -> list[str]:
    prompt_ids: list[str] = []
    for entry in queue_payload.get(key, []) or []:
        if isinstance(entry, (list, tuple)) and len(entry) > 1:
            prompt_ids.append(str(entry[1]))
        elif isinstance(entry, dict) and entry.get("prompt_id"):
            prompt_ids.append(str(entry["prompt_id"]))
    return prompt_ids


def _comfy_queue_prompt_ids(queue_payload: Dict[str, Any], key: str) -> set[str]:
    return set(_comfy_queue_prompt_order(queue_payload, key))


def _raise_comfy_execution_error(status: Dict[str, Any]) -> None:
    detail: Dict[str, Any] = {}
    for message in reversed(status.get("messages") or []):
        if (
            isinstance(message, (list, tuple))
            and len(message) > 1
            and message[0] == "execution_error"
            and isinstance(message[1], dict)
        ):
            detail = message[1]
            break

    exception_message = str(detail.get("exception_message") or "").strip()
    traceback_text = "\n".join(str(line) for line in detail.get("traceback") or [])
    if "Fault failed: 2" in exception_message and "comfy_aimdo" in traceback_text:
        raise ComfyDynamicVramFault(
            "O DynamicVRAM/VBAR do ComfyUI perdeu o estado durante o encoder; "
            "o Studio vai descarregar o cache e repetir o take uma vez."
        )

    node_type = str(detail.get("node_type") or "ComfyUI")
    exception_type = str(detail.get("exception_type") or "RuntimeError")
    if exception_message:
        raise RuntimeError(f"{node_type}: {exception_type}: {exception_message}")
    raise RuntimeError(json.dumps(status, ensure_ascii=False)[:1000])


def _recover_comfy_dynamic_vram() -> None:
    """Drop an idle broken VBAR cache before one controlled H3 retry."""

    queue = _comfy_request("/queue", timeout=10)
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError(
            "O DynamicVRAM precisa ser recuperado, mas outra tarefa ainda ocupa a fila do ComfyUI."
        )
    _comfy_request(
        "/free",
        {"unload_models": True, "free_memory": True},
        timeout=15,
    )
    deadline = _t.monotonic() + 20.0
    while True:
        system_stats = _comfy_request("/system_stats", timeout=10)
        devices = system_stats.get("devices") or []
        free_vram = max(
            (int(device.get("vram_free") or 0) for device in devices if isinstance(device, dict)),
            default=0,
        )
        if not devices or free_vram >= _MINIMAX_H3_RECOVERY_MIN_VRAM_BYTES:
            return
        if _t.monotonic() >= deadline:
            raise RuntimeError(
                "O ComfyUI descarregou o cache, mas a 5090 nao devolveu VRAM suficiente "
                "para recuperar o MiniMax H3."
            )
        _t.sleep(1.0)


def _cancel_comfy_prompt(prompt_id: str) -> None:
    """Cancela somente o prompt indicado, interrompendo o worker global apenas se ele estiver ativo."""
    if not prompt_id:
        return
    try:
        queue_payload = _comfy_request("/queue", timeout=10)
        pending = _comfy_queue_prompt_ids(queue_payload, "queue_pending")
        running = _comfy_queue_prompt_ids(queue_payload, "queue_running")
        if prompt_id in pending:
            _comfy_request("/queue", {"delete": [prompt_id]}, timeout=10)
        if prompt_id in running:
            _comfy_request("/interrupt", {}, timeout=10)
    except Exception as exc:
        bk_log(f"Aviso ao cancelar prompt ComfyUI {prompt_id}: {exc}")


def _queue_comfy_workflow(
    workflow: Dict[str, Any],
    timeout: int,
    progress_cb=None,
    cancel_event: threading.Event | None = None,
    prompt_id_cb=None,
    resume_prompt_id: str = "",
) -> Tuple[str, List[Dict[str, Any]]]:
    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled("Cancelado antes do envio ao ComfyUI.")
    prompt_id = str(resume_prompt_id or "").strip()
    prompt_is_present = False
    if prompt_id:
        # Reattach after a Studio restart. Missing volatile Comfy history is
        # not proof that the original prompt never executed.
        history = _comfy_request(f"/history/{prompt_id}", timeout=30)
        queue_payload = _comfy_request("/queue", timeout=10)
        prompt_is_present = bool(history.get(prompt_id)) or prompt_id in (
            _comfy_queue_prompt_ids(queue_payload, "queue_running")
            | _comfy_queue_prompt_ids(queue_payload, "queue_pending")
        )
        if not prompt_is_present:
            raise RuntimeError(
                f"COMFY_PROMPT_STATE_UNKNOWN: {prompt_id}; histórico/fila ausentes. "
                "Nenhum reenvio automático; preserve o job e solicite uma nova tentativa explícita."
            )
    if not prompt_is_present:
        from creative_os.integration import export_graph, archive_workflow
        workflow = export_graph(workflow, _comfy_request("/object_info/SaveVideo", timeout=15))
        workflow = _ensure_h3_sage_attention(workflow)
        workflow = _ensure_h3_face_refine(workflow)
        if any(n.get("class_type") == "SpectrumApplyMiniMaxH3" for n in workflow.values()):
            # Imported graphs and all builders share this final admission gate.
            for required_node in _H3_REQUIRED_ACCELERATION_NODES:
                info = _comfy_request(f"/object_info/{required_node}", timeout=15)
                if required_node not in info:
                    raise RuntimeError(f"H3_ACCELERATION_REQUIRED: {required_node} ausente; Sage + Spectrum obrigatorios, sem fallback.")
        model_fingerprints = None
        if any(n.get("class_type") == "MiniMaxH3ImageToVideo" for n in workflow.values()):
            from creative_os.h3_latent_finishing import source_contract, fingerprint_source
            from creative_os.ir import CreativeError
            try:
                source_contract(workflow)
                version = (_comfy_request("/system_stats", timeout=15).get("system") or {}).get("comfyui_version")
                model_fingerprints = fingerprint_source(workflow, COMFY_MODELS_DIR, version)
            except CreativeError:
                pass  # Native generation remains available outside HQ's qualified scope.
            except Exception:
                logging.exception("Creative OS: model fingerprints unavailable; latent HQ will remain blocked")
        client_id = str(uuid.uuid4())
        queued = _comfy_request("/prompt", {"prompt": workflow, "client_id": client_id}, timeout=30)
        prompt_id = str(queued.get("prompt_id") or "")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI nao retornou prompt_id: {queued}")
        # Record prompt identity before archival so an I/O error cannot cause a blind retry.
        if prompt_id_cb:
            prompt_id_cb(prompt_id)
        try:
            archive_workflow(Path(BASE_DIR) / "dados" / "creative_os" / "workflows", prompt_id, workflow,
                             model_fingerprints=model_fingerprints)
        except Exception:
            logging.exception("Creative OS: workflow provenance unavailable for %s", prompt_id)
    if prompt_id_cb:
        prompt_id_cb(str(prompt_id))
    if cancel_event is not None and cancel_event.is_set():
        _cancel_comfy_prompt(str(prompt_id))
        raise GenerationCancelled("Cancelado depois do envio ao ComfyUI.")
    if progress_cb:
        progress_cb(8, "Workflow enviado ao ComfyUI.")
    deadline = _t.time() + timeout
    started = _t.time()
    last_status = ""
    last_poll_error = ""
    # Each urllib poll opens a short-lived Windows socket.  Polling twice every
    # second created needless AcceptEx churn in the long H3 renders and could
    # trigger a fatal Proactor listener failure. Five seconds remains responsive
    # while reducing the connection rate by 80 percent.
    last_progress_reported_at = _t.time()
    last_progress_message = "Workflow enviado ao ComfyUI."
    while _t.time() < deadline:
        if cancel_event is not None and cancel_event.is_set():
            _cancel_comfy_prompt(str(prompt_id))
            raise GenerationCancelled("Geracao cancelada pelo proprietario.")
        try:
            hist = _comfy_request(f"/history/{prompt_id}", timeout=30)
            last_poll_error = ""
        except Exception as e:
            last_poll_error = str(e)
            last_status = f"Aguardando ComfyUI responder: {last_poll_error}"
            if progress_cb and (
                last_status != last_progress_message
                or _t.time() - last_progress_reported_at >= 5.0
            ):
                elapsed = _t.time() - started
                pct = min(94, 8 + int((elapsed / max(timeout, 1)) * 86))
                progress_cb(pct, last_status)
                last_progress_reported_at = _t.time()
                last_progress_message = last_status
            _t.sleep(5.0)
            continue
        item = hist.get(prompt_id)
        if not item:
            try:
                queue_payload = _comfy_request("/queue", timeout=10)
                running = _comfy_queue_prompt_ids(queue_payload, "queue_running")
                pending = _comfy_queue_prompt_order(queue_payload, "queue_pending")
                if str(prompt_id) in pending:
                    last_status = f"Na fila do ComfyUI — posição {pending.index(str(prompt_id)) + 1}."
                elif str(prompt_id) in running:
                    last_status = "Gerando no ComfyUI."
            except Exception:
                pass
        progress_message = last_status or "Gerando no ComfyUI."
        if progress_cb and (
            progress_message != last_progress_message
            or _t.time() - last_progress_reported_at >= 5.0
        ):
            elapsed = _t.time() - started
            pct = min(94, 8 + int((elapsed / max(timeout, 1)) * 86))
            progress_cb(pct, progress_message)
            last_progress_reported_at = _t.time()
            last_progress_message = progress_message
        if item:
            status = item.get("status", {})
            last_status = status.get("status_str", last_status)
            if last_status == "error":
                _raise_comfy_execution_error(status)
            outputs = _extract_comfy_outputs(item)
            if outputs:
                if progress_cb:
                    progress_cb(95, "Render concluido. Preparando saida.")
                return prompt_id, outputs
            if status.get("completed"):
                if progress_cb:
                    progress_cb(95, "Render concluido sem midia detectada.")
                return prompt_id, outputs
        _t.sleep(5.0)
    raise TimeoutError(f"ComfyUI demorou mais que {timeout}s para finalizar ({last_status or 'sem status'}).")

def _available_model(name: str, options: List[str], default: str) -> str:
    if name and name in options:
        return name
    if default in options:
        return default
    return options[0] if options else default

def _run_elevenlabs_sfx(
    *,
    prompt: str,
    negative: str,
    duration: float,
    prompt_influence: float,
    loop: bool,
    progress_cb=None,
) -> Dict[str, Any]:
    api_key = _env_value("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ElevenLabs SFX nao configurado. Defina ELEVENLABS_API_KEY no .env do Maestro.")
    if progress_cb:
        progress_cb(12, "Enviando prompt para ElevenLabs SFX.")
    duration = _safe_float(duration, 4.0, 0.5, 30.0)
    influence = _safe_float(prompt_influence, 0.5, 0.0, 1.0)
    model_id = _env_value("ELEVENLABS_SFX_MODEL_ID", "eleven_text_to_sound_v2")
    output_format = _env_value("ELEVENLABS_SFX_OUTPUT_FORMAT", "mp3_44100_128")
    url = f"https://api.elevenlabs.io/v1/sound-generation?{urllib.parse.urlencode({'output_format': output_format})}"
    payload = {
        "text": _append_prompt_avoid(prompt, negative),
        "duration_seconds": duration,
        "prompt_influence": influence,
        "loop": bool(loop),
    }
    if model_id:
        payload["model_id"] = model_id
    data, media_type = _post_json_binary(
        url,
        payload,
        {"xi-api-key": api_key, "Accept": "audio/mpeg"},
        timeout=180,
    )
    if progress_cb:
        progress_cb(88, "SFX recebido. Salvando MP3.")
    ext = ".mp3" if output_format.startswith("mp3") else _mime_to_extension(media_type, ".mp3")
    output = _write_studio_output("audio", data, ext, media_type or "audio/mpeg", "sfx")
    output.update({"provider": "eleven_sfx", "duration_seconds": duration, "loop": bool(loop)})
    return {
        "ok": True,
        "mode": "sfx",
        "message": "SFX gerado com ElevenLabs.",
        "provider": "eleven_sfx",
        "model": model_id,
        "seed": None,
        "lora": "",
        "outputs": [output],
    }

def _run_elevenlabs_music(
    *,
    prompt: str,
    negative: str,
    duration: float,
    progress_cb=None,
) -> Dict[str, Any]:
    api_key = _env_value("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ElevenLabs Music nao configurado. Defina ELEVENLABS_API_KEY no .env do Maestro.")
    if progress_cb:
        progress_cb(12, "Compondo musica no ElevenLabs.")
    duration_ms = _safe_int(int(float(duration or 30) * 1000), 30000, 3000, 600000)
    output_format = _env_value("ELEVENLABS_MUSIC_OUTPUT_FORMAT", "mp3_44100_128")
    url = f"https://api.elevenlabs.io/v1/music?{urllib.parse.urlencode({'output_format': output_format})}"
    payload = {
        "prompt": _append_prompt_avoid(prompt, negative),
        "music_length_ms": duration_ms,
        "model_id": _env_value("ELEVENLABS_MUSIC_MODEL_ID", "music_v2"),
    }
    if _env_value("ELEVENLABS_MUSIC_FORCE_INSTRUMENTAL", "false").lower() in ("1", "true", "yes", "sim"):
        payload["force_instrumental"] = True
    data, media_type = _post_json_binary(
        url,
        payload,
        {"xi-api-key": api_key, "Accept": "audio/mpeg"},
        timeout=360,
    )
    if progress_cb:
        progress_cb(88, "Musica recebida. Salvando MP3.")
    ext = ".mp3" if output_format.startswith("mp3") else _mime_to_extension(media_type, ".mp3")
    output = _write_studio_output("audio", data, ext, media_type or "audio/mpeg", "music")
    output.update({"provider": "eleven_music", "duration_seconds": round(duration_ms / 1000, 2)})
    return {
        "ok": True,
        "mode": "music",
        "message": "Musica gerada com ElevenLabs.",
        "provider": "eleven_music",
        "model": "elevenlabs_music",
        "seed": None,
        "lora": "",
        "outputs": [output],
    }

def _run_lyria_music(
    *,
    prompt: str,
    negative: str,
    seed: int,
    progress_cb=None,
) -> Dict[str, Any]:
    project_id = _env_value("GOOGLE_CLOUD_PROJECT") or _env_value("VERTEX_PROJECT_ID")
    location = _env_value("GOOGLE_CLOUD_LOCATION", "us-central1")
    model_id = _env_value("LYRIA_MODEL_ID", "lyria-002")
    token = _google_access_token()
    if not project_id or not token:
        raise RuntimeError("Lyria nao configurado. Defina GOOGLE_CLOUD_PROJECT/VERTEX_PROJECT_ID e autentique com GOOGLE_OAUTH_ACCESS_TOKEN ou gcloud auth.")
    if progress_cb:
        progress_cb(12, "Enviando prompt para Lyria/Vertex.")
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{urllib.parse.quote(project_id)}/locations/{urllib.parse.quote(location)}/publishers/google/models/{urllib.parse.quote(model_id)}:predict"
    instance: Dict[str, Any] = {"prompt": prompt}
    if negative:
        instance["negative_prompt"] = negative
    if seed is not None and int(seed) >= 0:
        instance["seed"] = int(seed)
    payload = {"instances": [instance], "parameters": {"sample_count": 1}}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=420) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Lyria HTTP {e.code}: {body[:1200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Lyria indisponivel: {e}") from e
    data = json.loads(raw.decode("utf-8"))
    predictions = data.get("predictions") or []
    if not predictions or not predictions[0].get("audioContent"):
        raise RuntimeError(f"Lyria nao retornou audio: {json.dumps(data, ensure_ascii=False)[:1200]}")
    audio = base64.b64decode(predictions[0]["audioContent"])
    media_type = predictions[0].get("mimeType") or "audio/wav"
    if progress_cb:
        progress_cb(88, "Musica Lyria recebida. Salvando WAV.")
    output = _write_studio_output("audio", audio, _mime_to_extension(media_type, ".wav"), media_type, "lyria")
    output.update({"provider": "lyria", "duration_seconds": 30})
    return {
        "ok": True,
        "mode": "music",
        "message": "Musica instrumental gerada com Lyria.",
        "provider": "lyria",
        "model": model_id,
        "seed": instance.get("seed"),
        "lora": "",
        "outputs": [output],
    }

def _finish_simple_music(result, song=None, *, progress_cb=None, cancel_event=None):
    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled("Música cancelada antes da entrega.")
    from audio_download import resolve_audio_source
    from music_delivery import finish_audio
    song = song or {"title": "Música gerada", "caption": result.get('music_caption', ''),
                    "lyrics": result.get('music_lyrics', ''), "instrumental": result.get('music_instrumental', False)}
    if progress_cb:
        progress_cb(95, "Preservando a fonte e conferindo o master e o MP3 por decode e true peak.")
    for output in result.get("outputs", []):
        if output.get("kind") == "audio":
            source = resolve_audio_source(output["url"], Path(STUDIO_OUTPUT_DIR), _safe_comfy_output_path)
            directory = Path(STUDIO_OUTPUT_DIR) / "audio" / f"production_{uuid.uuid4().hex}"
            delivery = finish_audio(source, directory, get_ffmpeg(), cancel_event=cancel_event)
            native_url = output['url']
            native_filename = output.get('filename')
            def output_url(path):
                return '/api/generative/output?' + urllib.parse.urlencode({
                    'path': path.relative_to(Path(STUDIO_OUTPUT_DIR)).as_posix()})
            output.update({'native_url': native_url, 'url': output_url(delivery['preview']),
                           'native_filename': native_filename,
                           'master_url': output_url(delivery['master']),
                           'production_report_url': output_url(delivery['report']),
                           'filename': delivery['preview'].name, 'media_type': 'audio/mpeg',
                           'technical_qc': delivery['attempts'][-1]['previewQc']})
            plan_path = directory / 'qwen_production_plan.json'
            plan_path.write_text(
                json.dumps(song, ensure_ascii=False, indent=2), encoding='utf-8')
            if song.get('production_plan'):
                output['production_plan_url'] = output_url(plan_path)
            output["title"] = song["title"]
    result.update({"title": song["title"], "music_lyrics": song["lyrics"],
                   "music_caption": song["caption"], "music_instrumental": song["instrumental"],
                   "vocal_language": song.get("vocal_language", ""),
                   "writer_model": song.get("writer_model", ""), "music_action": result.get('music_action', 'auto'),
                   "writer_vram_bytes": song.get("writer_vram_bytes", 0),
                   "writer_unloaded": song.get("writer_unloaded", False),
                   "qwen_production_plan": song.get("production_plan"),
                   "qwen_duration_seconds": song.get("duration_seconds"),
                   "musical_review": {"status": "PENDING_HUMAN_REVIEW",
                       "dimensions": ["lyrics_and_language", "vocal_intelligibility", "melody",
                                      "arrangement", "instrument_timbres", "mix", "ending"]},
                   "message": f'{song["title"]} — música pronta para ouvir e baixar em MP3.'})
    return result


def _run_audio_generative(
    *,
    prompt: str,
    mode: str,
    provider: str,
    negative: str,
    duration: float,
    seed: int,
    prompt_influence: float,
    loop: bool,
    music_lyrics: str = "",
    music_instrumental: bool = True,
    music_model: str = "",
    music_bpm: int = 0,
    music_action: str = "generate",
    music_abc: str = "",
    music_abc_reviewed: bool = False,
    music_duration_auto: bool = False,
    progress_cb=None,
    cancel_event: threading.Event | None = None,
    process_cb=None,
    prompt_id_cb=None,
    gpu_job_id: str = "",
) -> Dict[str, Any]:
    provider = (provider or "").strip().lower()
    mode = (mode or "").strip().lower()
    if type(music_duration_auto) is not bool:
        raise ValueError("A escolha automática de duração deve ser booleana.")
    if music_duration_auto:
        if mode != "music" or provider != "yue2_local":
            raise ValueError("Duração escolhida pelo modelo está disponível para música YuE2.")
        duration = 900.0
    if mode == "sfx":
        if provider == "stable_audio":
            raise RuntimeError("Stable Audio ainda nao esta conectado. Configure STABLE_AUDIO_LOCAL_URL ou STABILITY_API_KEY e instale o conector antes de usar este provider.")
        if provider == "audiogen":
            raise RuntimeError("AudioGen local ainda nao esta conectado. Configure AUDIOGEN_LOCAL_URL depois de instalar o servico AudioCraft/AudioGen.")
        return _run_elevenlabs_sfx(
            prompt=prompt,
            negative=negative,
            duration=duration,
            prompt_influence=prompt_influence,
            loop=loop,
            progress_cb=progress_cb,
        )
    if mode == "music":
        from music_creation import ACE_ID, YUE_ID, validate, yue_workflow, run_ace, run_yue_auto
        song = None
        if provider in {ACE_ID, YUE_ID, LEVO2_PROVIDER_ID} and music_action == "auto":
            from music_writer import write_song
            _comfy_request("/queue", timeout=10)
            _prepare_comfy_gpu_for_mova(job_id=gpu_job_id, cancel_event=cancel_event, wait_for_queue=True)
            devices = _comfy_request("/system_stats", timeout=10).get("devices", [])
            if not any(int(device.get("vram_free") or 0) >= 22 * 1024**3 for device in devices):
                raise RuntimeError("O Qwen 27B precisa de 22 GB livres na GPU. Libere a VRAM antes de gerar a música.")
            song = write_song(prompt, None if music_duration_auto else duration,
                              cancel_event=cancel_event, progress_cb=progress_cb,
                              provided_lyrics=music_lyrics if music_lyrics.strip() else None,
                              instrumental=True if music_instrumental else None,
                              max_duration=600 if provider == ACE_ID else 900,
                              provided_bpm=music_bpm)
            prompt, music_lyrics, music_instrumental = song["caption"], song["lyrics"], song["instrumental"]
            if music_duration_auto and song.get("production_plan"):
                duration = float(song["production_plan"]["duration_seconds"])
            if music_bpm == 0 and song.get("production_plan"):
                music_bpm = int(song["production_plan"]["bpm"])
            if progress_cb:
                progress_cb(16, "Compondo e gerando o áudio no motor escolhido.")
        if provider in {ACE_ID, YUE_ID}:
            if negative.strip():
                raise ValueError("Use a descrição de estilo para ACE-Step/YuE2 e deixe o campo Evitar vazio.")
            validate(provider, prompt, duration, music_lyrics, music_instrumental, music_model,
                     music_bpm, music_action, music_abc, music_abc_reviewed)
            if seed is None or int(seed) < 0:
                seed = random.randrange(1, 2**32)
            else:
                seed = int(seed)
            if provider == ACE_ID:
                # The Maestro operates autonomously through its existing backend channel.
                # Refuse to unload a different active Comfy job when admitting ACE.
                _comfy_request("/queue", timeout=10)  # Unknown queue state must block GPU admission.
                _prepare_comfy_gpu_for_mova()
                candidate = run_ace(prompt=prompt, lyrics=music_lyrics, instrumental=music_instrumental,
                    duration=duration, seed=seed, music_model=music_model, music_bpm=music_bpm,
                    progress_cb=progress_cb, cancel_event=cancel_event, process_cb=process_cb,
                    gpu_job_id=gpu_job_id)
                output = _write_studio_output("audio", candidate["data"], candidate["extension"],
                                              candidate["media_type"], "ace_original")
                output.update({"provider": provider, "duration_seconds": candidate["duration_seconds"],
                               "requires_human_listening": True})
                result = {"ok": True, "mode": "music", "provider": provider, "model": candidate["model"],
                        "music_action": music_action, "music_caption": prompt,
                        "music_lyrics": music_lyrics, "music_instrumental": music_instrumental,
                        "seed": seed, "outputs": [output], "runtime_commit": candidate["runtime_commit"],
                        "message": "Música original ACE-Step gerada. Escute o resultado antes de aprovar.",
                        "approval_status": "PENDING_HUMAN_REVIEW"}
                return _finish_simple_music(result, song, progress_cb=progress_cb, cancel_event=cancel_event)
            def queue_yue(workflow):
                # Actual classes/checkpoint for both score and audio submissions.
                for node in workflow.values():
                    cls = node["class_type"]
                    info = _comfy_request(f"/object_info/{cls}", timeout=15)
                    if cls not in info:
                        raise RuntimeError(f"YuE2 indisponível: nó {cls} ausente; sem fallback.")
                    if cls == "CheckpointLoaderSimple":
                        choices = info[cls]["input"]["required"]["ckpt_name"][0]
                        if node["inputs"]["ckpt_name"] not in choices:
                            raise RuntimeError("Checkpoint YuE2 ausente no runtime ativo; sem fallback.")
                return _queue_comfy_workflow(workflow, timeout=3600, progress_cb=progress_cb,
                    cancel_event=cancel_event, prompt_id_cb=prompt_id_cb)
            ending_details = {}
            if music_action == "auto":
                prompt_id, outputs, ending_details = run_yue_auto(prompt=prompt, lyrics=music_lyrics,
                    instrumental=music_instrumental, duration=duration, seed=seed, music_abc=music_abc,
                    queue=queue_yue, progress_cb=progress_cb,
                    music_duration_auto=music_duration_auto and not bool(song and song.get("production_plan")),
                    production_plan=(song or {}).get("production_plan"))
                music_abc = ending_details["music_abc"]
            else:
                workflow = yue_workflow(prompt=prompt, lyrics=music_lyrics, instrumental=music_instrumental,
                    duration=duration, seed=seed, music_action=music_action, music_abc=music_abc,
                    prefix=f"audio/Maestro_YuE2_{uuid.uuid4().hex[:12]}", music_duration_auto=music_duration_auto)
                prompt_id, outputs = queue_yue(workflow)
            if music_action == "plan":
                abc = "\n".join(item["text"] for item in outputs if item.get("kind") == "text").strip()
                if not abc:
                    raise RuntimeError("YuE2 não retornou a partitura ABC; nenhum áudio foi solicitado.")
                return {"ok": True, "mode": "music", "provider": provider, "model": "YuE2 3B",
                        "seed": seed, "prompt_id": prompt_id, "outputs": [], "music_abc": abc,
                        "message": "Partitura ABC criada. Revise e confirme a revisão para gerar o áudio.",
                        "approval_status": "PENDING_SCORE_REVIEW", "music_duration_auto": music_duration_auto}
            audio_outputs = [item for item in outputs if item.get("kind") == "audio"]
            if not audio_outputs:
                raise RuntimeError("YuE2 concluiu sem áudio; nenhum fallback será usado.")
            result = {"ok": True, "mode": "music", "provider": provider, "model": "YuE2 3B",
                    "music_action": music_action, "music_caption": prompt,
                    "music_lyrics": music_lyrics, "music_instrumental": music_instrumental,
                    "seed": seed, "prompt_id": prompt_id, "outputs": audio_outputs,
                    "message": "Música YuE2 gerada. Escute o encerramento antes de aprovar.",
                    "approval_status": "PENDING_HUMAN_REVIEW", "music_duration_auto": music_duration_auto}
            result.update(ending_details)
            if song:
                result["music_abc"] = music_abc or "\n".join(item["text"] for item in outputs if item.get("kind") == "text").strip()
                return _finish_simple_music(result, song, progress_cb=progress_cb, cancel_event=cancel_event)
            return _finish_simple_music(result, progress_cb=progress_cb, cancel_event=cancel_event)
        if provider == LEVO2_PROVIDER_ID:
            candidate = _run_levo2_music(
                prompt=prompt,
                negative=negative,
                duration=duration,
                main_comfy_url=COMFY_URL,
                lyrics=music_lyrics, instrumental=music_instrumental,
                progress_cb=progress_cb,
                cancel_event=cancel_event,
                process_cb=process_cb,
            )
            output = _write_studio_output(
                "audio",
                candidate["data"],
                candidate["extension"],
                candidate["media_type"],
                "levo2_pilot",
            )
            output.update({
                "provider": LEVO2_PROVIDER_ID,
                "duration_seconds": candidate["duration_seconds"],
                "pilot": True,
                "requires_human_listening": True,
            })
            result = {
                "ok": True,
                "mode": "music",
                "message": "Piloto LeVo 2 gerado. Escute no player antes de qualquer aprovacao.",
                "provider": LEVO2_PROVIDER_ID,
                "model": candidate["model"],
                "seed": None,
                "lora": "",
                "pilot": True,
                "approval_status": "PENDING_HUMAN_REVIEW",
                "outputs": [output],
            }
            result.update(music_action=music_action, music_caption=prompt,
                          music_lyrics=music_lyrics, music_instrumental=music_instrumental)
            return _finish_simple_music(result, song, progress_cb=progress_cb, cancel_event=cancel_event)
        if provider == "lyria":
            return _run_lyria_music(prompt=prompt, negative=negative, seed=seed, progress_cb=progress_cb)
        if provider == "stable_audio":
            raise RuntimeError("Stable Audio ainda nao esta conectado. Configure STABLE_AUDIO_LOCAL_URL ou STABILITY_API_KEY e instale o conector antes de usar este provider.")
        if provider == "eleven_music":
            return _run_elevenlabs_music(prompt=prompt, negative=negative, duration=duration, progress_cb=progress_cb)
        raise ValueError("Motor de música desconhecido; escolha um motor explícito. Nenhum fallback será usado.")
    raise ValueError("Modo de audio invalido. Use music ou sfx.")

def _build_flux_workflow(
    prompt: str,
    model: str,
    lora: str,
    lora_strength: float,
    width: int,
    height: int,
    steps: int,
    guidance: float,
    seed: int,
    prefix: str,
) -> Dict[str, Any]:
    dtype = "fp8_e4m3fn" if "fp8" in model.lower() else "default"
    workflow: Dict[str, Any] = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model, "weight_dtype": dtype}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {
            "clip_name1": DEFAULT_FLUX_CLIP_1,
            "clip_name2": DEFAULT_FLUX_CLIP_2,
            "type": "flux",
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": DEFAULT_FLUX_VAE}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "7": {"class_type": "FluxGuidance", "inputs": {"guidance": guidance, "conditioning": ["6", 0]}},
        "8": {"class_type": "ModelSamplingFlux", "inputs": {
            "model": ["1", 0],
            "max_shift": 1.15,
            "base_shift": 0.5,
            "width": width,
            "height": height,
        }},
        "9": {"class_type": "BasicGuider", "inputs": {"model": ["8", 0], "conditioning": ["7", 0]}},
        "10": {"class_type": "BasicScheduler", "inputs": {
            "model": ["8", 0],
            "scheduler": "simple",
            "steps": steps,
            "denoise": 1.0,
        }},
        "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "12": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "13": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["11", 0],
            "guider": ["9", 0],
            "sampler": ["12", 0],
            "sigmas": ["10", 0],
            "latent_image": ["5", 0],
        }},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
        "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": prefix}},
    }
    if lora:
        workflow["4"] = {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0],
            "clip": ["2", 0],
            "lora_name": lora,
            "strength_model": lora_strength,
            "strength_clip": lora_strength,
        }}
        workflow["6"]["inputs"]["clip"] = ["4", 1]
        workflow["8"]["inputs"]["model"] = ["4", 0]
    return workflow

def _build_qwen_image_workflow(prompt, negative, model, lora, lora_strength,
                               width, height, steps, cfg, seed, prefix):
    if lora:
        raise ValueError("As LoRAs do Qwen antigo não são compatíveis com o Qwen-Image 2.1.")
    return _build_qwen21_workflow(prompt, negative, model, width, height, steps, cfg, seed, prefix)

def _build_qwen_edit_workflow(prompt, negative, model, width, height, steps, cfg,
                              seed, prefix, base_image_name):
    return _build_qwen21_workflow(prompt, negative, model, width, height, steps, cfg,
                                 seed, prefix, base_image_name)


def _build_minimax_h3_fl2va_workflow(
    prompt: str,
    negative: str,
    width: int,
    height: int,
    frames: int,
    steps: int,
    seed: int,
    prefix: str,
    base_image_name: str,
    *,
    end_image_name: str = "",
    include_native_audio: bool = False,
    enable_live_preview: bool = False,
    fps: float = MINIMAX_H3_FPS,
    allow_owner_long_window: bool = False,
    h3_quality_profile: str = "",
    h3_model_variant: str = "base",
    last_frame_index: int | None = None,
    guide_image_name: str = "",
    guide_frame_index: int | None = None,
) -> Dict[str, Any]:
    """Build the MiniMax H3 T2VA/FL2VA graph with optional first/last frames.

    Native audio is opt-in and disabled by default. The long window is likewise
    opt-in because the calibrated range ends at 362 frames.
    """
    output_geometry = (int(width), int(height))
    h3_model_variant = str(h3_model_variant or "base").strip().lower()
    if h3_model_variant not in {"base", _FAST_H3_VARIANT}:
        raise ValueError("Variante H3 invalida. Use H3 Base ou FastH3 8-Step V2.")
    profile_id, profile, vertical = _resolve_h3_quality_profile(
        h3_quality_profile, width=width, height=height, steps=steps,
        model_variant=h3_model_variant,
    )
    expected_geometry = (
        (profile["verticalWidth"], profile["verticalHeight"])
        if vertical else (profile["width"], profile["height"])
    )
    if output_geometry != expected_geometry:
        raise ValueError(f"{profile['label']} exige {expected_geometry[0]}x{expected_geometry[1]}.")
    if profile.get("draftOnly"):
        include_native_audio = False
    if h3_model_variant == _FAST_H3_VARIANT:
        if guide_image_name:
            raise ValueError("H3_FAST_GUIDE_UNSUPPORTED: FastH3 aceita primeiro/ultimo quadro, sem guia intermediario.")
        if int(steps) != _FAST_H3_STEPS:
            raise ValueError(f"FastH3 8-Step V2 exige exatamente {_FAST_H3_STEPS} steps.")
    native_720p_profiles = {"h3_legacy_720p", "h3_approved_action_720p8s"}
    if profile_id in native_720p_profiles and output_geometry == (MINIMAX_H3_WIDTH, MINIMAX_H3_HEIGHT):
        native_width = MINIMAX_H3_NATIVE_WIDTH
        native_height = MINIMAX_H3_NATIVE_HEIGHT
    elif profile_id in native_720p_profiles and output_geometry == (MINIMAX_H3_VERTICAL_WIDTH, MINIMAX_H3_VERTICAL_HEIGHT):
        native_width = MINIMAX_H3_VERTICAL_NATIVE_WIDTH
        native_height = MINIMAX_H3_VERTICAL_NATIVE_HEIGHT
    else:
        native_width, native_height = output_geometry
    maximum_frames = (
        MINIMAX_H3_OWNER_LONG_MAX_FRAMES
        if allow_owner_long_window
        else MINIMAX_H3_TRAINED_MAX_FRAMES
    )
    if int(frames) < 124 or int(frames) > maximum_frames or (int(frames) - 5) % 17 != 0:
        raise ValueError(
            f"MiniMax H3 FL2VA exige 124-{maximum_frames} quadros na grade temporal 17k+5."
        )
    if int(frames) > MINIMAX_H3_TRAINED_MAX_FRAMES and int(frames) != MINIMAX_H3_OWNER_LONG_MAX_FRAMES:
        raise ValueError("A janela MiniMax H3 longa autorizada exige exatamente 736 quadros.")
    requested_rate = validate_video_fps(fps, classic_only=True)
    if abs(requested_rate - MINIMAX_H3_FPS) > 0.001:
        raise ValueError("MiniMax H3 FL2VA gera nativamente em 24 FPS.")
    rate = MINIMAX_H3_FPS
    # MiniMax H3 has no independent negative-conditioning branch in this
    # owner-locked graph.  Feeding policy headings or a raw ``Avoid:`` list
    # into the positive text encoder caused the model to paint those exact
    # English instructions into banners and documents.  Keep the instruction
    # scene-native and free of title-like policy copy.
    effective_prompt = prompt.strip()
    conditioning_inputs: Dict[str, Any] = {
        "clip": ["3", 0],
        "vae": ["4", 0],
        "prompt": effective_prompt,
        "width": native_width,
        "height": native_height,
        "length": int(frames),
    }
    if base_image_name:
        conditioning_inputs["first_frame"] = ["5", 0]
    if end_image_name:
        conditioning_inputs["last_frame"] = ["19", 0]
        if last_frame_index is not None:
            resolved_last = int(last_frame_index)
            if resolved_last <= 0 or resolved_last >= int(frames):
                raise ValueError(
                    f"last_frame_index deve ficar entre 1 e {int(frames) - 1}."
                )
            conditioning_inputs["last_frame_index"] = resolved_last
    if guide_image_name:
        if guide_frame_index is None:
            raise ValueError("guide_frame_index e obrigatorio quando guide_image_name e usado.")
        resolved_guide = int(guide_frame_index)
        if resolved_guide <= 0 or resolved_guide >= int(frames) - 1:
            raise ValueError(
                f"guide_frame_index deve ficar entre 1 e {int(frames) - 2}."
            )
    workflow = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": _FAST_H3_MODEL_NAME if h3_model_variant == _FAST_H3_VARIANT else MINIMAX_H3_MODEL_NAME,
                "weight_dtype": "default",
            },
        },
        "2": {
            "class_type": "MiniMaxH3SigmaShift",
            "inputs": {
                "model": ["1", 0],
                "shift_video": 10.0 if h3_model_variant == _FAST_H3_VARIANT else 12.0,
                "shift_audio": 3.0,
            },
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": MINIMAX_H3_TEXT_ENCODER,
                "type": "minimax",
                "device": "default",
            },
        },
        "4": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": MINIMAX_H3_VIDEO_VAE},
        },
        "6": {
            "class_type": "MiniMaxH3ImageToVideo",
            "inputs": conditioning_inputs,
        },
        "7": {
            "class_type": "BasicGuider",
            "inputs": {"model": ["2", 0], "conditioning": ["6", 0]},
        },
        "8": {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": ["2", 0],
                "scheduler": "simple",
                "steps": int(steps),
                "denoise": 1.0,
            },
        },
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}},
        "10": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "11": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["9", 0],
                "guider": ["7", 0],
                "sampler": ["10", 0],
                "sigmas": ["8", 0],
                "latent_image": ["6", 1],
            },
        },
        "12": {
            "class_type": "LTXVSeparateAVLatent",
            "inputs": {"av_latent": ["11", 0]},
        },
        "13": {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "samples": ["12", 0],
                "vae": ["4", 0],
                "tile_size": 512,
                "overlap": 64,
                "temporal_size": 64,
                "temporal_overlap": 8,
            },
        },
        "14": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["13", 0],
                "upscale_method": "lanczos",
                "width": int(width),
                "height": int(height),
                "crop": "center",
            },
        },
        "15": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["14", 0], "fps": rate, "bit_depth": 8},
        },
        "16": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["15", 0],
                "filename_prefix": prefix,
                "format": "mp4",
                "format.codec": "h264",
            },
        },
    }
    if base_image_name:
        workflow["5"] = {
            "class_type": "LoadImage",
            "inputs": {"image": base_image_name},
        }
    if end_image_name:
        workflow["19"] = {
            "class_type": "LoadImage",
            "inputs": {"image": end_image_name},
        }
    if guide_image_name:
        workflow["21"] = {
            "class_type": "LoadImage",
            "inputs": {"image": guide_image_name},
        }
        workflow["22"] = {
            "class_type": "MiniMaxH3AddGuide",
            "inputs": {
                "positive": ["6", 0],
                "vae": ["4", 0],
                "latent": ["6", 1],
                "image": ["21", 0],
                "frame_idx": resolved_guide,
            },
        }
        workflow["7"]["inputs"]["conditioning"] = ["22", 0]
    if include_native_audio:
        workflow["17"] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": MINIMAX_H3_AUDIO_VAE},
        }
        workflow["18"] = {
            "class_type": "VAEDecodeAudio",
            "inputs": {
                "samples": ["12", 1],
                "vae": ["17", 0],
            },
        }
        workflow["15"]["inputs"]["audio"] = ["18", 0]
    if enable_live_preview:
        workflow["20"] = {
            "class_type": "ModelPreviewOverrideKJ",
            "inputs": {
                "model": ["2", 0],
                "max_resolution": 640,
                "jpeg_quality": 72,
                "suppress_default_preview": True,
                "preview_frames": 1,
                "preview_fps": 12,
            },
        }
        workflow["7"]["inputs"]["model"] = ["20", 0]
        workflow["8"]["inputs"]["model"] = ["20", 0]
    graph_mode = (
        "FL2VA" if base_image_name and end_image_name
        else "I2VA" if base_image_name
        else "L2VA" if end_image_name
        else "T2VA"
    )
    workflow = _ensure_h3_sage_attention(workflow)
    _validate_h3_comfy_graph(workflow, mode=graph_mode, model_variant=h3_model_variant)
    return _apply_h3_master_cache(_ensure_h3_face_refine(workflow), profile_id)


def _build_minimax_h3_ref2va_workflow(
    prompt: str,
    negative: str,
    width: int,
    height: int,
    frames: int,
    steps: int,
    seed: int,
    prefix: str,
    reference_image_names: List[str],
    *,
    reference_video_name: str = "",
    include_native_audio: bool = False,
    enable_live_preview: bool = False,
    fps: float = MINIMAX_H3_FPS,
    allow_owner_long_window: bool = False,
    h3_quality_profile: str = "",
) -> Dict[str, Any]:
    """Build H3 Ref2VA with references, never pretending they are pose control."""

    image_names = [str(name).strip() for name in reference_image_names if str(name).strip()]
    if not image_names and not reference_video_name:
        raise ValueError("MiniMax H3 Ref2VA exige imagem ou video de referencia aprovado.")
    if len(image_names) > 9:
        raise ValueError("MiniMax H3 Ref2VA aceita no maximo nove imagens de referencia.")
    workflow = _build_minimax_h3_fl2va_workflow(
        prompt=prompt,
        negative=negative,
        width=width,
        height=height,
        frames=frames,
        steps=steps,
        seed=seed,
        prefix=prefix,
        base_image_name="",
        end_image_name="",
        include_native_audio=include_native_audio,
        enable_live_preview=enable_live_preview,
        fps=fps,
        allow_owner_long_window=allow_owner_long_window,
        h3_quality_profile=h3_quality_profile,
    )
    # Ref2VA is a separate task-specific checkpoint.  Reusing the FL2VA
    # weights produces a valid-looking graph that runs while ignoring the
    # intended reference conditioning semantics.
    workflow["1"]["inputs"]["unet_name"] = MINIMAX_H3_REF2VA_MODEL_NAME
    if "17" not in workflow:
        workflow["17"] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": MINIMAX_H3_AUDIO_VAE},
        }
    conditioning_inputs: Dict[str, Any] = {
        "clip": ["3", 0],
        "vae": ["4", 0],
        "audio_vae": ["17", 0],
        "prompt": prompt.strip(),
        "width": workflow["6"]["inputs"]["width"],
        "height": workflow["6"]["inputs"]["height"],
        "length": int(frames),
        # Production identity work keeps the owner-approved source pixels.
        # "match" silently discards detail before the reference encoder sees it.
        "ref_image_size": "max",
    }
    if image_names:
        ref_images: Dict[str, Any] = {}
        for index, name in enumerate(image_names, start=1):
            node_id = str(30 + index)
            workflow[node_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": name},
            }
            ref_images[f"ref_image_{index}"] = [node_id, 0]
        conditioning_inputs["ref_images"] = ref_images
    if reference_video_name:
        workflow["50"] = {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": reference_video_name,
                "force_rate": 24,
                "custom_width": int(width),
                "custom_height": int(height),
                "frame_load_cap": int(frames),
                "skip_first_frames": 0,
                "select_every_nth": 1,
            },
        }
        conditioning_inputs["ref_videos"] = {"ref_video_1": ["50", 0]}
    workflow["6"] = {
        "class_type": "MiniMaxH3ReferenceToVideo",
        "inputs": conditioning_inputs,
    }
    _validate_h3_comfy_graph(workflow, mode="REF2VA")
    return workflow


def _build_wan_webm_workflow(
    prompt: str,
    negative: str,
    model: str,
    lora: str,
    lora_strength: float,
    width: int,
    height: int,
    frames: int,
    steps: int,
    cfg: float,
    fps: float,
    seed: int,
    prefix: str,
    base_image_name: str = "",
) -> Dict[str, Any]:
    fps = validate_video_fps(fps)
    workflow: Dict[str, Any] = {
        "1": _unet_loader_node(model),
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "4": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": DEFAULT_WAN_CLIP,
            "type": "wan",
            "device": "default",
        }},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": DEFAULT_WAN_VAE}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 0]}},
        "9": {"class_type": "Wan22ImageToVideoLatent", "inputs": {
            "width": width,
            "height": height,
            "length": frames,
            "batch_size": 1,
            "vae": ["5", 0],
        }},
        "10": {"class_type": "KSamplerAdvanced", "inputs": {
            "model": ["3", 0],
            "positive": ["7", 0],
            "negative": ["8", 0],
            "latent_image": ["9", 0],
            "noise_seed": seed,
            "add_noise": "enable",
            "noise_mask": None,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler",
            "scheduler": "simple",
            "start_at_step": 0,
            "end_at_step": steps,
            "return_with_leftover_noise": "disable",
        }},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["5", 0]}},
        "12": {"class_type": "SaveWEBM", "inputs": {
            "images": ["11", 0],
            "filename_prefix": prefix,
            "codec": "vp9",
            "fps": fps,
            # Preserve fine linework, debris and smoke in the intermediate.
            # The MP4 finalizer encodes again, so CRF 28 here permanently
            # destroyed detail before the delivery encode.
            "crf": 14.0,
        }},
    }
    if base_image_name:
        workflow["13"] = {"class_type": "LoadImage", "inputs": {"image": base_image_name}}
        workflow["9"]["inputs"]["start_image"] = ["13", 0]
    if lora:
        workflow["2"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["1", 0],
            "lora_name": lora,
            "strength_model": lora_strength,
        }}
        workflow["3"]["inputs"]["model"] = ["2", 0]
    return workflow

def _build_wan22_a14b_i2v_webm_workflow(
    prompt: str,
    negative: str,
    high_model: str,
    low_model: str,
    lora: str,
    lora_strength: float,
    width: int,
    height: int,
    frames: int,
    steps: int,
    cfg: float,
    fps: float,
    seed: int,
    prefix: str,
    base_image_name: str,
    end_image_name: str = "",
    conditioning_profile: str = "identity_locked",
) -> Dict[str, Any]:
    fps = validate_video_fps(fps)
    if not base_image_name:
        raise ValueError("Wan2.2 A14B I2V exige imagem base aprovada.")
    if conditioning_profile not in {"identity_locked", "manus_motion"}:
        raise ValueError(f"Perfil de condicionamento Wan invalido: {conditioning_profile}")
    split_step = max(1, min(steps - 1, steps // 2))
    high_model_ref: list[Any] = ["1", 0]
    low_model_ref: list[Any] = ["2", 0]
    workflow: Dict[str, Any] = {
        "1": _unet_loader_node(high_model),
        "2": _unet_loader_node(low_model),
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": high_model_ref, "shift": 5.0}},
        "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": low_model_ref, "shift": 5.0}},
        "5": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": DEFAULT_WAN_CLIP,
            "type": "wan",
            "device": "default",
        }},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": WAN21_I2V_VAE}},
        "7": {"class_type": "LoadImage", "inputs": {"image": base_image_name}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["5", 0]}},

        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "", "clip": ["5", 0]}},
        "10": {"class_type": "WanFirstLastFrameToVideo" if end_image_name else "WanImageToVideo", "inputs": {
            "positive": ["8", 0],
            "negative": ["9", 0],
            "vae": ["6", 0],
            "start_image": ["7", 0],
            "width": width,
            "height": height,
            "length": frames,
            "batch_size": 1,
        }},
        "11": {"class_type": "KSamplerAdvanced", "inputs": {
            "model": ["3", 0],
            "positive": ["10", 0],
            "negative": ["10", 1],
            "latent_image": ["10", 2],
            "noise_seed": seed,
            "add_noise": "enable",
            "noise_mask": None,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler",
            "scheduler": "simple",
            "start_at_step": 0,
            "end_at_step": split_step,
            "return_with_leftover_noise": "enable",
        }},
        "12": {"class_type": "KSamplerAdvanced", "inputs": {
            "model": ["4", 0],
            "positive": ["10", 0],
            "negative": ["10", 1],
            "latent_image": ["11", 0],
            "noise_seed": seed,
            "add_noise": "disable",
            "noise_mask": None,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler",
            "scheduler": "simple",
            "start_at_step": split_step,
            "end_at_step": steps,
            "return_with_leftover_noise": "disable",
        }},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["6", 0]}},
        "14": {"class_type": "SaveWEBM", "inputs": {
            "images": ["13", 0],
            "filename_prefix": prefix,
            "codec": "vp9",
            "fps": fps,
            # Keep the Wan intermediate visually transparent for the later
            # MP4 transcode; catastrophe shots expose VP9 blocking quickly.
            "crf": 14.0,
        }},
    }
    # Wan A14B I2V accepts an independent CLIP Vision identity embedding.
    # Keep the whole 16:9 source (`crop: none`) so both the warm and ruined
    # halves remain represented. This is intentionally start-only: the
    # first/last node exposes differently named CLIP inputs and remains on
    # its previously validated path.
    if not end_image_name and conditioning_profile == "identity_locked":
        workflow["18"] = {"class_type": "CLIPVisionLoader", "inputs": {
            "clip_name": "clip_vision_h.safetensors",
        }}
        workflow["19"] = {"class_type": "CLIPVisionEncode", "inputs": {
            "clip_vision": ["18", 0],
            "image": ["7", 0],
            "crop": "none",
        }}
        workflow["10"]["inputs"]["clip_vision_output"] = ["19", 0]
    if end_image_name:
        workflow["17"] = {"class_type": "LoadImage", "inputs": {"image": end_image_name}}
        workflow["10"]["inputs"]["end_image"] = ["17", 0]
    if lora:
        workflow["15"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["1", 0],
            "lora_name": lora,
            "strength_model": lora_strength,
        }}
        workflow["16"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["2", 0],
            "lora_name": lora,
            "strength_model": lora_strength,
        }}
        workflow["3"]["inputs"]["model"] = ["15", 0]
        workflow["4"]["inputs"]["model"] = ["16", 0]
    return workflow

def _build_wan22_fun_camera_webm_workflow(
    prompt: str,
    negative: str,
    high_model: str,
    low_model: str,
    width: int,
    height: int,
    frames: int,
    steps: int,
    cfg: float,
    fps: float,
    seed: int,
    prefix: str,
    base_image_name: str,
    camera_pose: str,
    camera_speed: float,
) -> Dict[str, Any]:
    """Official Wan2.2 Fun Camera two-expert workflow with explicit trajectory."""
    fps = validate_video_fps(fps)
    if not base_image_name:
        raise ValueError("Wan2.2 Fun Camera exige imagem base aprovada.")
    allowed_poses = {
        "Static", "Pan Up", "Pan Down", "Pan Left", "Pan Right",
        "Zoom In", "Zoom Out", "Anti Clockwise (ACW)", "ClockWise (CW)",
    }
    pose = camera_pose if camera_pose in allowed_poses else "Pan Right"
    speed = _safe_float(camera_speed, 0.8, 0.0, 10.0)
    split_step = max(1, min(steps - 1, steps // 2))
    return {
        "1": _unet_loader_node(high_model),
        "2": _unet_loader_node(low_model),
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "5": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": DEFAULT_WAN_CLIP, "type": "wan", "device": "default",
        }},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": WAN21_I2V_VAE}},
        "7": {"class_type": "LoadImage", "inputs": {"image": base_image_name}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["5", 0]}},

        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "", "clip": ["5", 0]}},
        "10": {"class_type": "WanCameraEmbedding", "inputs": {
            "camera_pose": pose, "width": width, "height": height, "length": frames,
            "speed": speed, "fx": 0.5, "fy": 0.5, "cx": 0.5, "cy": 0.5,
        }},
        "11": {"class_type": "WanCameraImageToVideo", "inputs": {
            "positive": ["8", 0], "negative": ["9", 0], "vae": ["6", 0],
            "start_image": ["7", 0], "camera_conditions": ["10", 0],
            "clip_vision_output": ["17", 0],
            "width": ["10", 1], "height": ["10", 2], "length": ["10", 3],
            "batch_size": 1,
        }},
        "12": {"class_type": "KSamplerAdvanced", "inputs": {
            "model": ["3", 0], "positive": ["11", 0], "negative": ["11", 1],
            "latent_image": ["11", 2], "noise_seed": seed, "add_noise": "enable",
            "noise_mask": None, "steps": steps, "cfg": cfg, "sampler_name": "euler",
            "scheduler": "simple", "start_at_step": 0, "end_at_step": split_step,
            "return_with_leftover_noise": "enable",
        }},
        "13": {"class_type": "KSamplerAdvanced", "inputs": {
            "model": ["4", 0], "positive": ["11", 0], "negative": ["11", 1],
            "latent_image": ["12", 0], "noise_seed": seed, "add_noise": "disable",
            "noise_mask": None, "steps": steps, "cfg": cfg, "sampler_name": "euler",
            "scheduler": "simple", "start_at_step": split_step, "end_at_step": steps,
            "return_with_leftover_noise": "disable",
        }},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["6", 0]}},
        "15": {"class_type": "SaveWEBM", "inputs": {
            "images": ["14", 0], "filename_prefix": prefix, "codec": "vp9",
            "fps": fps, "crf": 14.0,
        }},
        "16": {"class_type": "CLIPVisionLoader", "inputs": {
            "clip_name": "clip_vision_h.safetensors",
        }},
        "17": {"class_type": "CLIPVisionEncode", "inputs": {
            "clip_vision": ["16", 0],
            "image": ["7", 0],
            "crop": "none",
        }},
    }

# 
# ROTAS
# 

@app.get("/api/finishing-policy")
def finishing_policy():
    try:
        return {"ok": True, **_dlss5.preflight(), "stage": "required_visual_export",
                "upscaling": _required_upscale.policy_status(),
                "preserve_original": True, "raw_fallback": False,
                "qualified_formats": ["png", "jpg", "jpeg", "webp", "mp4", "mov", "mkv", "webm"],
                "qualified_depth": "8-bit SDR", "owner_review_required": True}
    except _dlss5.DLSS5RequiredError as exc:
        return JSONResponse(status_code=503, content={"ok": False, "required": True, "error": str(exc)})


@app.get("/api/status")
def status():
    gpu, sensor_error = dashboard_gpu_snapshot()
    if sensor_error:
        bk_log(f"SENSOR Dashboard indisponivel: {sensor_error}")
    return {"status":"GPU" if not sensor_error else "UNKNOWN",
            "device":gpu.get("nome") or "GPU indisponivel",
            "compute":gpu.get("compute") or "",
            "temp":gpu.get("temp"),"load":gpu.get("load"),
            "vram_u":gpu.get("vram_u"),"vram_t":gpu.get("vram_t"),
            "fan":gpu.get("fan"),"power_w":gpu.get("power_w"),
            "power_max":gpu.get("power_max"),"clock_gpu":gpu.get("clock_gpu"),
            "clock_mem":gpu.get("clock_mem"),"sensors_ok":not sensor_error,
            "sensor_error":sensor_error}


@app.get("/api/hyperframes/status")
async def hyperframes_status(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    return _hyperframes_status()


@app.post("/api/hyperframes/start")
async def hyperframes_start(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    result = _ensure_hyperframes_preview()
    if not result.get("online"):
        return JSONResponse(status_code=503, content=result)
    return result


@app.post("/api/hyperframes/render", status_code=202)
async def hyperframes_render(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return {"ok": True, "render": _start_hyperframes_render()}
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"ok": False, "erro": str(exc)})


@app.get("/api/hyperframes/pilot-output")
async def hyperframes_pilot_output(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    if not _HYPERFRAMES_OUTPUT_PATH.is_file():
        return JSONResponse(status_code=404, content={"ok": False, "erro": "Render ainda nao disponivel."})
    return FileResponse(
        _HYPERFRAMES_OUTPUT_PATH,
        media_type="video/mp4",
        filename=_HYPERFRAMES_OUTPUT_PATH.name,
    )

@app.post("/api/generative/h3/compile-prompt")
async def generative_h3_compile_prompt(request: Request):
    """Compile an official H3 prompt locally without starting GPU inference."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("O corpo deve ser um objeto JSON.")
        mode = str(payload.get("mode") or "T2VA").strip().upper()
        duration_seconds = float(payload.get("durationSeconds") or 5.0)
        if not 4.0 <= duration_seconds <= 15.0:
            raise ValueError("A duracao H3 deve ficar entre 4 e 15 segundos.")
        if mode == "REF2VA":
            document = _compile_h3_ref_prompt(
                subject_definitions=str(payload.get("subjectDefinitions") or ""),
                summary=str(payload.get("summary") or ""),
                retention_analysis=str(payload.get("retentionAnalysis") or ""),
                detailed_description=str(payload.get("detailedDescription") or ""),
                overall_soundscape=str(payload.get("overallSoundscape") or "N/A"),
                non_diegetic_music=str(payload.get("nonDiegeticMusic") or "N/A"),
                duration_seconds=duration_seconds,
            )
        else:
            document = _compile_h3_base_prompt(
                str(payload.get("description") or payload.get("prompt") or ""),
                mode=mode,
                duration_seconds=duration_seconds,
                overall_soundscape=str(payload.get("overallSoundscape") or "N/A"),
                non_diegetic_music=str(payload.get("nonDiegeticMusic") or "N/A"),
                final_shot=max(1, int(payload.get("finalShot") or 1)),
            )
        return {
            "ok": True,
            "prompt": document.prompt,
            "mode": document.mode,
            "durationSeconds": document.duration_seconds,
            "contractVersion": document.contract_version,
            "officialCommit": document.official_commit,
            "privacy": {"localOnly": True, "externalApi": False},
            "officialSkill": _h3_official_skill_integrity(Path(BASE_DIR)),
        }
    except (TypeError, ValueError) as exc:
        return JSONResponse(status_code=422, content={"erro": str(exc)})


@app.get("/api/generative/h3/workflow")
async def generative_h3_workflow(request: Request):
    """Expose the canonical H3 pipeline and live local inventory, read-only."""

    if not _is_internal_request(request):
        return _public_forbidden()
    online, _ = _comfy_online()
    return _h3_workflow_status_live(comfy_online=online)


def _h3_workflow_status_live(*, comfy_online: bool) -> Dict[str, Any]:
    """Combine the on-disk FastH3 checkpoint with ComfyUI's live loader enum."""
    status = _h3_workflow_status(Path(BASE_DIR), comfy_online=comfy_online)
    capabilities = status.setdefault("capabilities", {})
    file_ready = bool(capabilities.get("fastH3Ready"))
    model_listed = False
    if comfy_online:
        try:
            object_info = _comfy_request("/object_info/UNETLoader", timeout=15)
            loader = object_info.get("UNETLoader") or {}
            unet_input = (
                (loader.get("input") or {}).get("required") or {}
            ).get("unet_name") or []
            choices = unet_input[0] if isinstance(unet_input, list) and unet_input else []
            model_listed = _FAST_H3_MODEL_NAME in choices
        except Exception:
            model_listed = False
    capabilities["fastH3FileReady"] = file_ready
    capabilities["fastH3NodeListed"] = model_listed
    capabilities["fastH3Ready"] = bool(file_ready and model_listed)
    capabilities["masterCacheReady"] = False  # FBC is retired, not stacked with Spectrum.
    capabilities["masterSpectrumReady"] = False
    capabilities["sageAttentionReady"] = False
    capabilities["sageProtectionReady"] = False
    if comfy_online:
        for required_node, capability in zip(_H3_REQUIRED_ACCELERATION_NODES,
                ("sageAttentionReady", "sageProtectionReady", "masterSpectrumReady")):
            try:
                info = _comfy_request(f"/object_info/{required_node}", timeout=15)
                capabilities[capability] = required_node in info
            except Exception:
                pass
    capabilities["spectrumReady"] = capabilities["masterSpectrumReady"]
    status["productionReady"] = bool(status.get("productionReady") and all(
        capabilities[key] for key in ("sageAttentionReady", "sageProtectionReady", "spectrumReady")))
    face = status.setdefault("faceRefine", _h3_face_refine_policy())
    face["runtimeReady"] = False
    if comfy_online and face.get("enabled"):
        try:
            info = _comfy_request("/object_info/PemaraH3FaceRefine", timeout=15)
            face["runtimeReady"] = "PemaraH3FaceRefine" in info
        except Exception:
            pass
    capabilities["faceRefineReady"] = face["runtimeReady"]
    status["productionReady"] = bool(status.get("productionReady") and (not face.get("enabled") or face["runtimeReady"]))
    return status


@app.get("/api/generative/video-engines")
async def generative_video_engines(request: Request):
    """Return the closed H3 registry with no selected default."""

    if not _is_internal_request(request):
        return _public_forbidden()
    return _video_engine_registry_live().describe()


@app.get("/api/generative/video-engines/{engine_id}/readiness")
async def generative_video_engine_readiness(
    request: Request,
    engine_id: str,
    verify_hash: bool = False,
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        engine = _video_engine_registry_live().get(engine_id)
        return {
            "ok": True,
            "engine_id": engine.id,
            "readiness": engine.readiness(verify_hash=bool(verify_hash)),
            "capabilities": engine.capabilities(),
        }
    except _VideoEngineError as exc:
        return _video_engine_error_response(exc)


@app.post("/api/generative/video-engines/{engine_id}/compile-prompt")
async def generative_video_engine_compile_prompt(request: Request, engine_id: str):
    """Compile one immutable anchor contract into the selected engine dialect."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise _VideoEngineError("REQUEST_BODY_INVALID", "O corpo deve ser um objeto JSON.")
        contract = payload.get("anchor_contract") or payload.get("anchorContract")
        compile_request = payload.get("request") if isinstance(payload.get("request"), dict) else payload
        engine = _video_engine_registry_live().get(engine_id)
        compiled = engine.compile_prompt(contract, compile_request)
        return {
            "ok": True,
            "engine_id": engine.id,
            "compiled": compiled,
            "fallback_used": False,
            "owner_approval_state": "PENDING_HUMAN_REVIEW",
        }
    except _AnchorIntelligenceConflictError as exc:
        exc.status_code = 409
        return _video_engine_error_response(exc)
    except (_VideoEngineError, _AnchorIntelligenceContractError, TypeError, ValueError) as exc:
        return _video_engine_error_response(exc)


@app.post("/api/generative/video-engines/{engine_id}/preflight")
async def generative_video_engine_preflight(request: Request, engine_id: str):
    """Validate parameters and readiness without queueing or touching the GPU."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise _VideoEngineError("REQUEST_BODY_INVALID", "O corpo deve ser um objeto JSON.")
        engine = _video_engine_registry_live().get(engine_id)
        validated = engine.validate_request(payload)
        if engine.id == "minimax_h3" and validated.get("h3_model_variant") == _FAST_H3_VARIANT:
            online, _ = _comfy_online()
            fast_status = _h3_workflow_status_live(comfy_online=online)
            if not fast_status.get("capabilities", {}).get("fastH3Ready"):
                raise _VideoEngineError(
                    "FAST_H3_NOT_READY",
                    "FastH3 está instalado, mas o UNETLoader ativo ainda não o reconhece; nenhum fallback será usado.",
                    status_code=409,
                )
        readiness = engine.readiness()
        workflow = engine.build_workflow(validated)
        return {
            "ok": True,
            "engine_id": engine.id,
            "validated_request": validated,
            "workflow": workflow,
            "resources": engine.estimate_resources(validated),
            "readiness": readiness,
            "can_start_generation": bool(readiness.get("production_ready")),
            "fallback_used": False,
        }
    except (_VideoEngineError, TypeError, ValueError) as exc:
        return _video_engine_error_response(exc)


@app.post("/api/generative/anchor-intelligence/analyze")
async def generative_anchor_intelligence_analyze(request: Request):
    """Retired endpoint: never reads or sends an image to an external provider."""
    if not _is_internal_request(request):
        return _public_forbidden()
    return JSONResponse(status_code=410, content={
        "ok": False, "code": "EXTERNAL_ANCHOR_ANALYSIS_REMOVED",
        "erro": "Analise externa de ancora removida. Use a foto aprovada e a direcao de movimento.",
    })


@app.get("/api/generative/status")
def generative_status(request: Request):
    # Inventário e verificações síncronas não podem bloquear a reprodução dos takes.
    online, comfy = _comfy_online()
    video_paused = _video_generation_paused()
    video_engine_registry = _video_engine_registry_live(comfy_online=online)
    video_engines = video_engine_registry.describe()
    mova = {
        "model": MOVA_MODEL_NAME,
        "installed": False,
        "model_complete": False,
        "runtime_ready": False,
        "ready": False,
        "removed": True,
        "ram_gb": 0.0,
        "minimum_ram_gb": 0.0,
        "message": "MOVA desinstalado por decisao do proprietario.",
    }
    hunyuan_ready = bool(online and _hunyuan15_ready_in_comfy())
    wan_ready = False
    wan_reserve_enabled = False
    wan_animate = _wan_animate_kit_status(Path(BASE_DIR))
    engine_readiness = _video_engine_readiness(comfy_online=online)
    diffusion_models = _model_files("diffusion_models")
    unet_models = _model_files("unet", suffixes=(".safetensors", ".ckpt", ".pt", ".gguf"))
    flux_models = [m for m in unet_models if m.lower().startswith("flux")]
    flux_models += [m for m in diffusion_models if m.lower().startswith("flux")]
    qwen_models = [m for m in diffusion_models if m == DEFAULT_QWEN_MODEL]
    qwen_edit_models = [m for m in diffusion_models if m == DEFAULT_QWEN_EDIT_MODEL]
    marketing_card_models = qwen_edit_models
    image_models = flux_models + qwen_models
    detected_video_models = _video_model_files(diffusion_models, unet_models)
    video_models = []
    if MINIMAX_H3_MODEL_NAME in detected_video_models and _minimax_h3_kit_ready():
        video_models.append(MINIMAX_H3_MODEL_NAME)
    if (
        MINIMAX_H3_REF2VA_MODEL_NAME in detected_video_models
        and _minimax_h3_ref2va_ready()
    ):
        video_models.append(MINIMAX_H3_REF2VA_MODEL_NAME)
    if WAN22_ANIMATE_MODEL_NAME in detected_video_models and wan_animate.get("ready"):
        video_models.append(WAN22_ANIMATE_MODEL_NAME)
    if _unauthorized_video_engines_enabled():
        video_models.extend(
            name for name in detected_video_models
            if name not in video_models and not _retired_wan_model(name)
        )
    if os.environ.get("STUDIO_ENABLE_REJECTED_HUNYUAN", "0") != "1":
        video_models = [name for name in video_models if name != HUNYUAN15_I2V_MODEL]
    if (
        _unauthorized_video_engines_enabled()
        and DEFAULT_VIDEO_MODEL not in video_models
        and os.path.exists(os.path.join(COMFY_MODELS_DIR, "diffusion_models", DEFAULT_VIDEO_MODEL))
    ):
        video_models.append(DEFAULT_VIDEO_MODEL)
    loras = [name for name in _model_files("loras") if not _retired_wan_model(name)]
    audio_providers = _audio_provider_status()
    h3_workflow = _h3_workflow_status_live(comfy_online=online)
    defaults = {
        "image_model": _available_model("", image_models, DEFAULT_FLUX_MODEL),
        "qwen_model": _available_model("", qwen_models, DEFAULT_QWEN_MODEL),
        "qwen_edit_model": _available_model("", qwen_edit_models, DEFAULT_QWEN_EDIT_MODEL),
        "marketing_card_model": _available_model("", marketing_card_models, DEFAULT_MARKETING_CARD_MODEL),
        "video_model": None,
        "video_engine_id": None,
        "width": 1024,
        "height": 1024,
        "marketing_width": DEFAULT_MARKETING_CARD_WIDTH,
        "marketing_height": DEFAULT_MARKETING_CARD_HEIGHT,
        "marketing_steps": DEFAULT_MARKETING_CARD_STEPS,
        "marketing_guidance": DEFAULT_MARKETING_CARD_GUIDANCE,
        "video_width": 1280,
        "video_height": 720,
        # Minimo aprovado pelo usuario: takes com pelo menos 6s (181 frames a 30fps).
        "video_frames": 181,
        "video_fps": 30,
        "video_duration": 6.0,
        "video_min_fps": int(MIN_VIDEO_FPS),
        "minimax_h3_min_frames": MINIMAX_H3_MIN_FRAMES,
        "minimax_h3_max_frames": MINIMAX_H3_TRAINED_MAX_FRAMES,
        "minimax_h3_native_fps": int(MINIMAX_H3_FPS),
        "minimax_h3_max_duration": 15,
        "minimax_h3_temporal_stride": MINIMAX_H3_TEMPORAL_STRIDE,
        "minimax_h3_temporal_offset": MINIMAX_H3_TEMPORAL_OFFSET,
        "minimax_h3_text_to_video": True,
        "minimax_h3_native_audio_default": False,
        "minimax_h3_live_preview_default": False,
        "minimax_h3_prompt_compiler": "official-local-pinned",
        "video_method_profile": "minimax_h3_take_contract",
        "audio_duration": int(
            (audio_providers.get(LEVO2_PROVIDER_ID) or {}).get("default_duration_seconds", 15)
        ),
        "sfx_duration": 4,
        "audio_provider": (
            LEVO2_PROVIDER_ID
            if (audio_providers.get(LEVO2_PROVIDER_ID) or {}).get("configured")
            else "lyria"
        ),
        "sfx_provider": "stable_audio",
    }
    if not _is_internal_request(request):
        return {
            "ok": True,
            "public": True,
            "comfy_online": bool(online),
            "pauses": {
                "video": video_paused,
                "video_reason": _video_pause_message() if video_paused else "",
            },
            "defaults": {
                "width": defaults["width"],
                "height": defaults["height"],
                "marketing_width": defaults["marketing_width"],
                "marketing_height": defaults["marketing_height"],
                "video_width": defaults["video_width"],
                "video_height": defaults["video_height"],
                "video_fps": defaults["video_fps"],
                "video_duration": defaults["video_duration"],
                "video_min_fps": defaults["video_min_fps"],
                "minimax_h3_native_audio_default": defaults["minimax_h3_native_audio_default"],
                "audio_provider": defaults["audio_provider"],
                "sfx_provider": defaults["sfx_provider"],
            },
            "quality": {
                "marketing_card": {
                    "engine": "qwen_image_edit",
                    "requires_base_image": True,
                    "aspect": "4:5",
                    "qc": "ocr + product similarity + dimensions",
                },
                "video_method": {
                    "engine": "Selecao explicita entre MiniMax H3",
                    "engine_ready": any(engine_readiness.values()),
                    "engine_readiness": engine_readiness,
                    "unauthorized_engines": ["HunyuanVideo"],
                    "reserve_engines": [],
                    "hunyuan_experimental_ready": hunyuan_ready,
                    "profile": "owner_selected_no_default_no_fallback",
                    "requires_start_frame": True,
                    "supports_end_frame_contract": True,
                    "requires_variants_before_final": True,
                    "minimum_review_fps": int(MIN_VIDEO_FPS),
                    "forbidden_review_fps": [16],
                    "generation_paused": video_paused,
                    "minimax_h3": {
                        "model": MINIMAX_H3_MODEL_NAME,
                        "installed": _minimax_h3_kit_ready(),
                        "ready": bool(online and _minimax_h3_kit_ready()),
                        "resolution": "1280x720",
                        "native_fps": 24,
                        "delivery_fps": 60,
                        "audio": "VAE FP32 instalado; áudio nativo opcional e desligado por padrão",
                        "trained_duration_seconds": 15,
                        "owner_long_window_seconds": 30.625,
                        "project_scope": "motor global e projetos audiovisuais do proprietario",
                        "ref2va_model": MINIMAX_H3_REF2VA_MODEL_NAME,
                        "ref2va_ready": bool(online and _minimax_h3_ref2va_ready()),
                        "reference_video_is_pose_control": False,
                    },
                    "wan22_animate_move": {
                        "model": WAN22_ANIMATE_MODEL_NAME,
                        "installed": bool(wan_animate.get("ready")),
                        "ready": bool(online and wan_animate.get("ready")),
                        "resolution": "720x1280",
                        "native_fps": 30,
                        "pose_video_input": True,
                        "requires_owner_approved_dwpose": True,
                        "face_transfer_default": False,
                    },
                },
            },
        }
    return {
        "ok": True,
        "comfy_online": online,
        "comfy_url": COMFY_URL,
        "comfy": comfy if online else {"erro": comfy},
        "pauses": {
            "video": video_paused,
            "video_reason": _video_pause_message() if video_paused else "",
        },
        "defaults": defaults,
        "videoEngines": video_engines,
        "models": {
            "image": image_models,
            "qwen": qwen_models,
            "qwen_edit": qwen_edit_models,
            "marketing_card": marketing_card_models,
            "video": video_models,
            "loras": loras,
            "vae": _model_files("vae"),
            "clip": _model_files("clip"),
            "text_encoders": _model_files("text_encoders"),
            "upscale": _model_files("upscale_models", suffixes=(".pth", ".pt", ".safetensors")),
            "controlnet": _model_files("controlnet"),
            "style_models": _model_files("style_models"),
            "clip_vision": _model_files("clip_vision"),
        },
        "mova": mova,
        "wan_animate": wan_animate,
        "wan_reserve": {
            "model": WAN22_PRODUCTION_MODEL,
            "installed": False,
            "enabled": False,
            "removed": True,
            "policy": "removed_by_owner_20260815",
        },
        "quality": {
            "marketing_card": {
                "engine": "qwen_image_edit",
                "requires_base_image": True,
                "final_compositor": "disabled",
                "aspect": "4:5",
                "qc": "ocr + product similarity + dimensions",
            },
            "image_max_stack": {
                "upscale_models": len(_model_files("upscale_models", suffixes=(".pth", ".pt", ".safetensors"))),
                "controlnet_models": len(_model_files("controlnet")),
                "style_models": len(_model_files("style_models")),
                "clip_vision_models": len(_model_files("clip_vision")),
            },
            "video_method": {
                "engine": "Selecao explicita entre MiniMax H3; sem default e sem fallback",
                "engine_ready": any(engine_readiness.values()),
                "engine_readiness": engine_readiness,
                "unauthorized_engines": ["HunyuanVideo"],
                "reserve_engines": [],
                "hunyuan_experimental_ready": hunyuan_ready,
                "profile": "owner_selected_no_default_no_fallback",
                "requires_start_frame": True,
                "supports_end_frame_contract": True,
                "requires_variants_before_final": True,
                "minimum_review_fps": int(MIN_VIDEO_FPS),
                "forbidden_review_fps": [16],
                "generation_paused": video_paused,
            },
        },
        "providers": {
            "audio": audio_providers,
            "llm": _nvidia_provider_status(),
            "video_method_profiles": _video_method_profiles(),
        },
        "h3Workflow": h3_workflow,
    }


@app.get("/api/generative/queue")
def generative_queue(request: Request):
    """Expose ComfyUI plus Maestro-owned video and upscale jobs in one order."""

    if not _is_internal_request(request):
        return _public_forbidden()
    comfy_online = True
    comfy_message = ""
    try:
        queue_payload = _comfy_request("/queue", timeout=10)
    except Exception as exc:
        comfy_online = False
        comfy_message = f"Fila do ComfyUI indisponivel: {exc}"
        queue_payload = {"queue_running": [], "queue_pending": []}

    running_ids = _comfy_queue_prompt_order(queue_payload, "queue_running")
    pending_ids = _comfy_queue_prompt_order(queue_payload, "queue_pending")
    recent = _GEN_JOB_STORE.list(page=1, page_size=100).get("items", [])
    jobs_by_prompt = {
        str(job.get("prompt_id")): job
        for job in recent
        if job.get("prompt_id")
    }

    def queue_item(prompt_id: str, state: str, position: int) -> Dict[str, Any]:
        job = jobs_by_prompt.get(prompt_id, {})
        return {
            "promptId": prompt_id,
            "jobId": str(job.get("job_id") or ""),
            "projectId": str(job.get("project_id") or ""),
            "takeId": str(job.get("take_id") or ""),
            "mode": str(job.get("mode") or ""),
            "jobKind": str(job.get("job_kind") or ""),
            "batchId": str(job.get("batch_id") or ""),
            "batchIndex": int(job.get("batch_index", 0) or 0),
            "batchSize": int(job.get("batch_size", 0) or 0),
            "state": state,
            "position": position,
            "progress": int(job.get("progress", 0) or 0),
            "message": str(job.get("message") or ""),
        }

    items = [queue_item(prompt_id, "RUNNING", 0) for prompt_id in running_ids]
    items.extend(
        queue_item(prompt_id, "PENDING", position)
        for position, prompt_id in enumerate(pending_ids, start=1)
    )

    comfy_ids = set(running_ids) | set(pending_ids)
    local_jobs = [
        job for job in recent
        if str(job.get("job_kind") or "") in {"video_take", "video_upscale"}
        and str(job.get("status") or "") in {"queued", "running", "canceling"}
        and str(job.get("prompt_id") or "") not in comfy_ids
    ]
    local_jobs.sort(key=lambda job: float(job.get("created_at", 0) or 0))
    pending_position = len(pending_ids)
    for job in local_jobs:
        running_now = str(job.get("status") or "") in {"running", "canceling"}
        if not running_now:
            pending_position += 1
        items.append({
            "promptId": str(job.get("prompt_id") or ""),
            "jobId": str(job.get("job_id") or ""),
            "projectId": str(job.get("project_id") or ""),
            "takeId": str(job.get("take_id") or ""),
            "mode": str(job.get("mode") or ""),
            "jobKind": str(job.get("job_kind") or ""),
            "batchId": str(job.get("batch_id") or ""),
            "batchIndex": int(job.get("batch_index", 0) or 0),
            "batchSize": int(job.get("batch_size", 0) or 0),
            "state": "RUNNING" if running_now else "PENDING",
            "position": 0 if running_now else pending_position,
            "progress": int(job.get("progress", 0) or 0),
            "message": str(job.get("message") or ""),
        })

    running_count = sum(1 for item in items if item["state"] == "RUNNING")
    pending_count = sum(1 for item in items if item["state"] == "PENDING")
    return {
        "ok": True,
        "online": comfy_online,
        "running": running_count,
        "pending": pending_count,
        "total": len(items),
        "items": items,
        "message": comfy_message,
    }

@app.get("/api/nvidia/status")
async def nvidia_status(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    return {
        "ok": True,
        "provider": _nvidia_provider_status()["nvidia_nim"],
    }

@app.get("/api/nvidia/models")
async def nvidia_models(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        data = _nvidia_request_json("/models", payload=None, timeout=45, method="GET")
        models = sorted([item.get("id") for item in data.get("data", []) if item.get("id")])
        recommended = [
            model for model in [
                NVIDIA_FAST_MODEL,
                NVIDIA_REASONING_MODEL,
                NVIDIA_VISION_MODEL,
                "minimaxai/minimax-m3",
                "moonshotai/kimi-k2.6",
                "meta/llama-3.3-70b-instruct",
                "mistralai/mistral-large-3-675b-instruct-2512",
            ]
            if model in models
        ]
        return {"ok": True, "count": len(models), "recommended": recommended, "models": models}
    except Exception as e:
        return JSONResponse(status_code=502, content={"ok": False, "erro": str(e)})

@app.post("/api/nvidia/chat")
async def nvidia_chat_route(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"ok": False, "erro": "prompt obrigatorio"})

    model = str(payload.get("model") or "")
    system = str(payload.get("system") or "")
    max_tokens = int(payload.get("max_tokens") or 1200)
    temperature = float(payload.get("temperature") or 0.2)

    try:
        return _nvidia_chat(
            prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as e:
        bk_log(f"ERRO nvidia chat: {e}")
        logging.error(f"nvidia chat: {e}", exc_info=True)
        return JSONResponse(status_code=502, content={"ok": False, "erro": str(e)})

@app.get("/api/generative/comfy-view")
async def generative_comfy_view(request: Request, filename: str, subfolder: str = "", type: str = "output"):
    if not _is_internal_request(request):
        return _public_forbidden()
    if not filename or any(x in filename for x in ("..", "/", "\\")):
        return JSONResponse(status_code=400, content={"erro": "filename invalido"})
    if ".." in subfolder or subfolder.startswith(("/", "\\")):
        return JSONResponse(status_code=400, content={"erro": "subfolder invalido"})
    local_path = _safe_comfy_output_path(filename, subfolder, type)
    if local_path and os.path.isfile(local_path):
        guessed_local = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return FileResponse(local_path, media_type=guessed_local)
    params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": type})
    try:
        with urllib.request.urlopen(f"{COMFY_URL}/view?{params}", timeout=30) as resp:
            data = resp.read()
            media_type = resp.headers.get_content_type()
    except Exception as e:
        return JSONResponse(status_code=502, content={"erro": f"Falha ao ler arquivo do ComfyUI: {e}"})
    guessed = mimetypes.guess_type(filename)[0]
    if filename.lower().endswith(".webm"):
        guessed = "video/webm"
    if filename.lower().endswith(".mp4"):
        guessed = "video/mp4"
    return Response(content=data, media_type=guessed or media_type or "application/octet-stream")

@app.get("/api/generative/output")
async def generative_output(request: Request, path: str, download: bool = False):
    if not _is_internal_request(request):
        return _public_forbidden()
    local_path = _safe_studio_output_path(path)
    if not local_path:
        return JSONResponse(status_code=400, content={"erro": "path invalido"})
    if not os.path.exists(local_path):
        return JSONResponse(status_code=404, content={"erro": "arquivo nao encontrado"})
    media_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    return FileResponse(
        local_path,
        media_type=media_type,
        filename=os.path.basename(local_path) if download else None,
    )

@app.api_route("/api/generative/audio-export/{filename}", methods=["GET", "HEAD"])
def generative_audio_export(request: Request, filename: str, source: str, download: bool = True, archive: bool = False):
    if not _is_internal_request(request):
        return _public_forbidden()
    from audio_download import mp3_disposition, mp3_filename, prepare_mp3, resolve_audio_source
    try:
        original = resolve_audio_source(source, Path(STUDIO_OUTPUT_DIR), _safe_comfy_output_path)
        mp3 = prepare_mp3(original, Path(BASE_DIR) / "dados" / "studio" / "audio_downloads", get_ffmpeg())
        if archive:
            from verified_download import prepare_verified_zip
            package = prepare_verified_zip(mp3, Path(BASE_DIR) / "dados" / "studio" / "verified_downloads", mp3_filename(filename))
            return FileResponse(package, media_type="application/zip", filename=mp3_filename(filename) + ".zip",
                                headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"erro": str(exc)})
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"erro": "Audio local nao encontrado"})
    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=504, content={"erro": "A conversao para MP3 excedeu o tempo limite"})
    except (OSError, RuntimeError):
        return JSONResponse(status_code=503, content={"erro": "Nao foi possivel preparar o MP3"})
    return FileResponse(
        mp3, media_type="audio/mpeg",
        headers={"Content-Disposition": mp3_disposition(filename, download),
                 "Cache-Control": "private, max-age=3600"},
    )

@app.get("/api/generative/assets")
async def generative_assets(
    request: Request,
    page: int = 1,
    page_size: int = 24,
    kind: str = "",
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return list_media_assets(
            Path(COMFY_OUTPUT_DIR),
            Path(STUDIO_OUTPUT_DIR),
            page=page,
            page_size=page_size,
            kind=kind,
            extra_assets=_music_reinstrument_library_assets(),
        )
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"erro": str(exc)})


def _music_reinstrument_library_assets() -> List[Dict[str, Any]]:
    """Expose eligible masters in Arquivos without copying or promoting them."""

    assets: List[Dict[str, Any]] = []
    page = 1
    while page <= 5:
        payload = _GEN_JOB_STORE.list(page=page, page_size=100, mode="music_reinstrument")
        jobs = payload.get("items") or []
        for job in jobs:
            if job.get("status") != "done" or job.get("library_visible", True) is False:
                continue
            review_status = str(job.get("review_status") or "PENDING_HUMAN_REVIEW")
            if review_status in {"OWNER_REJECTED", "INTERNAL_QC_REJECTED"}:
                continue
            result = job.get("result") or {}
            candidates = list(result.get("candidates") or [])
            selected_index = int(
                job.get("approved_candidate")
                or result.get("approvedCandidate")
                or 0
            )
            if not selected_index and candidates:
                eligible = [
                    item
                    for item in candidates
                    if str(item.get("reviewStatus") or "") != "OWNER_REJECTED"
                ]
                if not eligible:
                    continue
                eligible.sort(key=lambda item: (int(item.get("rank") or 999), int(item.get("index") or 999)))
                selected_index = int(eligible[0].get("index") or 0)
            artifact_key = (
                f"candidate{selected_index:02d}MasterWav"
                if selected_index
                else "masterWav"
            )
            artifact = next(
                (
                    item
                    for item in (result.get("artifacts") or [])
                    if str(item.get("key") or "") == artifact_key
                ),
                None,
            )
            if not artifact:
                continue
            try:
                local_path = _resolve_music_reinstrument_artifact(
                    Path(str(job.get("job_dir") or "")),
                    str(artifact.get("relativePath") or ""),
                )
            except FileNotFoundError:
                continue
            job_id = str(job.get("job_id") or "")
            if not job_id:
                continue
            original = Path(str(job.get("original_name") or "musica")).stem.strip() or "musica"
            assets.append(
                {
                    "source": "music_reinstrument",
                    "kind": "audio",
                    "filename": f"{original} - reinstrumentacao {job_id[:8]}.wav",
                    "relative_path": f"{job_id}/outputs/{local_path.name}",
                    "url": f"/api/music-reinstrument/jobs/{job_id}/artifacts/{artifact_key}",
                    "media_type": "audio/wav",
                    "modified_at": float(job.get("finished_at") or job.get("updated_at") or 0),
                    "size": int(artifact.get("sizeBytes") or local_path.stat().st_size),
                    "review_status": review_status,
                    "job_id": job_id,
                    "original_name": str(job.get("original_name") or ""),
                }
            )
        if page * 100 >= int(payload.get("total") or 0):
            break
        page += 1
    return assets

def _run_generative(
    *,
    prompt: str,
    mode: str,
    model: str,
    engine_id: str = "",
    anchor_contract_id: str = "",
    prompt_compiler_version: str = "",
    negative: str,
    lora: str,
    lora_strength: float,
    width: int,
    height: int,
    steps: int,
    guidance: float,
    seed: int,
    frames: int,
    fps: float,
    provider: str = "",
    gpu_job_id: str = "",
    duration: float = 30.0,
    music_lyrics: str = "",
    music_instrumental: bool = True,
    music_model: str = "",
    music_bpm: int = 0,
    music_action: str = "generate",
    music_abc: str = "",
    music_abc_reviewed: bool = False,
    music_duration_auto: bool = False,
    video_duration: float | None = None,
    prompt_influence: float = 0.5,
    loop: bool = False,
    base_image_bytes: bytes | None = None,
    base_image_name: str = "",
    audio_conditioning_bytes: bytes | None = None,
    audio_conditioning_name: str = "",
    end_image_bytes: bytes | None = None,
    end_image_name: str = "",
    minimax_reference_images: List[Tuple[bytes, str]] | None = None,
    minimax_reference_video_bytes: bytes | None = None,
    minimax_reference_video_name: str = "",
    minimax_reference_mode: str = "",
    pose_video_bytes: bytes | None = None,
    pose_video_name: str = "",
    camera_pose: str = "",
    camera_speed: float = 0.8,
    video_conditioning_profile: str = "identity_locked",
    strict_video_model: bool = False,
    allow_validated_video_geometry: bool = False,
    progress_cb=None,
    cancel_event: threading.Event | None = None,
    prompt_id_cb=None,
    resume_prompt_id: str = "",
    process_cb=None,
    visual_only_pass: bool = False,
    allow_minimax_h3_owner_long_window: bool = False,
    enable_minimax_h3_native_audio: bool = False,
    enable_minimax_h3_live_preview: bool = False,
    h3_quality_profile: str = "",
    h3_model_variant: str = "base",
    h3_orientation: str = "",
    minimax_h3_last_frame_index: int | None = None,
    minimax_h3_guide_image_bytes: bytes | None = None,
    minimax_h3_guide_image_name: str = "",
    minimax_h3_guide_frame_index: int | None = None,
    expected_human_cast: List[str] | None = None,
    cast_contract_known: bool = False,
    distinct_story_events: int = 1,
    creative_motion_request: dict | None = None,
    creative_timeline_request: dict | None = None,
    creative_fun_control_request: dict | None = None,
    creative_all_in_one: bool = False,
) -> Dict[str, Any]:
    prompt = (prompt or "").strip()
    negative = (negative or "").strip()
    mode = (mode or "image").lower().strip()
    h3_model_variant = str(h3_model_variant or "base").strip().lower()
    if h3_model_variant not in {"base", _FAST_H3_VARIANT}:
        raise ValueError("Variante H3 invalida. Use H3 Base ou FastH3 8-Step V2.")
    if h3_model_variant == _FAST_H3_VARIANT and mode != "video":
        raise ValueError("FastH3 8-Step V2 exige um job de vídeo H3.")
    if h3_model_variant == _FAST_H3_VARIANT and not _h3_workflow_status_live(
        comfy_online=True
    ).get("capabilities", {}).get("fastH3Ready"):
        raise ValueError("FastH3 ainda não está disponível no UNETLoader ativo; nenhum fallback será usado.")
    all_in_one_contract = None
    if type(creative_all_in_one) is not bool:
        raise ValueError("All-In-One deve ser booleano.")
    if creative_all_in_one and (mode != "video" or engine_id != "minimax_h3" or creative_fun_control_request is not None or creative_timeline_request is not None or creative_motion_request is not None or minimax_reference_images or minimax_reference_video_bytes):
        raise ValueError("All-In-One exige H3 T2V/I2V sem outro adapter ou referências Ref2VA.")
    fun_control_contract = None
    if creative_fun_control_request is not None:
        if creative_timeline_request is not None or creative_motion_request is not None or mode != "video" or base_image_bytes or end_image_bytes or minimax_reference_images or minimax_reference_video_bytes:
            raise ValueError("Fun Control exige H3 T2V sem outro adapter ou referências externas.")
        from creative_os.fun_control import validate_request as validate_control_request
        validate_control_request(creative_fun_control_request,engine_id=engine_id,
            profile=h3_quality_profile or "h3_production",native_audio=enable_minimax_h3_native_audio)
    timeline_contract = None
    if creative_timeline_request is not None:
        if creative_motion_request is not None or mode != "video" or base_image_bytes or end_image_bytes or minimax_reference_images or minimax_reference_video_bytes:
            raise ValueError("Timeline exige somente H3 T2V, sem outro adapter ou referências externas.")
        from creative_os.timeline_director import compile_request as compile_timeline_request
        timeline_contract = compile_timeline_request(creative_timeline_request,engine_id=engine_id,seed=seed,
            profile=h3_quality_profile or "h3_production",native_audio=enable_minimax_h3_native_audio)
    motion_contract = None
    if creative_motion_request is not None:
        if mode != "video" or base_image_bytes or end_image_bytes or minimax_reference_images or minimax_reference_video_bytes:
            raise ValueError("Motion Director integrado aceita somente timelines H3 T2V sem referências externas.")
        from creative_os.motion_director import compile_request
        motion_contract = compile_request(creative_motion_request, engine_id=engine_id,seed=seed,
            profile=h3_quality_profile or "h3_production",native_audio=enable_minimax_h3_native_audio)
    video_conditioning_profile = (video_conditioning_profile or "identity_locked").lower().strip()
    if video_conditioning_profile not in {
        "identity_locked", "manus_motion", "wan_animate_exact_pose",
    }:
        raise ValueError(
            "video_conditioning_profile deve ser identity_locked, manus_motion ou wan_animate_exact_pose."
        )
    # The preservation preference is model-agnostic at the API boundary.
    # Workflows that support a dedicated motion path consume it; the others
    # keep their native conditioning instead of blocking model selection.
    if not prompt:
        raise ValueError("Prompt vazio")
    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled("Geracao cancelada antes de iniciar.")
    if mode in {"video", "prompt_rewrite", "semantic_review"} and _video_generation_paused():
        raise RuntimeError(_video_pause_message())
    if mode == "semantic_review":
        from creative_os.semantic_critic import execute as execute_semantic_review
        return execute_semantic_review(globals(),prompt,base_image_bytes,progress_cb=progress_cb,
            cancel_event=cancel_event,prompt_id_cb=prompt_id_cb,resume_prompt_id=resume_prompt_id)
    if mode == "prompt_rewrite":
        if engine_id != "minimax_h3": raise ValueError("Rewriter H3 exige escolha explícita do motor H3.")
        from creative_os.h3_rewriter import execute as execute_rewriter
        return execute_rewriter(globals(),prompt,video_duration or 5,seed,progress_cb=progress_cb,
            cancel_event=cancel_event,prompt_id_cb=prompt_id_cb,resume_prompt_id=resume_prompt_id)
    if mode == "video":
        requested_video_model = str(model or "").strip()
        selected_engine, selected_engine_model = _resolve_video_engine(
            engine_id,
            model=model,
            # Exact model identifiers used by internal project workers are an
            # explicit choice, not a default or cross-engine fallback.
            allow_explicit_legacy_model=True,
        )
        if h3_model_variant == _FAST_H3_VARIANT and selected_engine.id != "minimax_h3":
            raise ValueError("FastH3 8-Step V2 pertence ao motor MiniMax H3, nao ao LTX 2.5.")
        # MiniMax H3 has two task-specific checkpoints behind the same engine
        # id. The registry default is FL2VA, but an explicitly selected Ref2VA
        # checkpoint must survive engine resolution.
        if (
            selected_engine.id == "minimax_h3"
            and requested_video_model == MINIMAX_H3_REF2VA_MODEL_NAME
        ):
            selected_engine_model = requested_video_model
        readiness = selected_engine.readiness()
        if not readiness.get("production_ready"):
            raise _VideoEngineError(
                "ENGINE_NOT_PRODUCTION_READY",
                str(readiness.get("message") or f"{selected_engine.display_name} ainda nao esta liberado para producao."),
                status_code=409,
                details={
                    "engine_id": selected_engine.id,
                    "state": readiness.get("state"),
                    "gpu_smoke_required": bool(readiness.get("gpu_smoke_required")),
                },
            )
        engine_id = selected_engine.id
        model = selected_engine_model
        _require_authorized_video_engine(model)
    if mode in ("music", "sfx"):
        return _run_audio_generative(
            prompt=prompt,
            mode=mode,
            provider=provider,
            negative=negative,
            duration=duration,
            seed=seed,
            prompt_influence=prompt_influence,
            loop=loop,
            progress_cb=progress_cb,
            cancel_event=cancel_event,
            process_cb=process_cb,
            music_lyrics=music_lyrics, music_instrumental=music_instrumental,
            music_model=music_model, music_bpm=music_bpm, music_action=music_action,
            music_abc=music_abc, music_abc_reviewed=music_abc_reviewed, music_duration_auto=music_duration_auto,
            prompt_id_cb=prompt_id_cb,
            gpu_job_id=gpu_job_id,
        )
    if mode == "video" and str(model or "").strip() == MOVA_MODEL_NAME:
        if end_image_bytes:
            raise ValueError("MOVA-720p aceita somente quadro inicial; remova o quadro final.")
        if (int(width), int(height)) == (1280, 720):
            raise ValueError(
                "Master MOVA 720p bloqueado antes da aprovacao. "
                "Gere o candidato 832x480; o upscale so pode ser iniciado depois da aprovacao final do take."
            )
        producer_plan = _analyze_mova_take(prompt, fps=max(24, int(float(fps))))
        _enforce_mova_policy(producer_plan)
        _enforce_mova_dialogue_duration(producer_plan, frames=int(frames), fps=float(fps))
        effective_prompt = _build_mova_effective_prompt(prompt, producer_plan)
        policy_negative = (
            "European Portuguese, Portugal accent, pt-PT, invented words, paraphrased dialogue, "
            "walking during dialogue, steps during dialogue, foot lift, body translation, "
            "approaching camera, sliding feet, repeated motion, unstable final pose"
        )
        effective_negative = ", ".join(item for item in (negative, policy_negative) if item)
        if seed is None or int(seed) < 0:
            seed = random.randrange(1, 2**63)
        else:
            seed = int(seed)
        ff = get_ffmpeg()
        if not nvenc_ok(ff):
            raise RuntimeError(
                "H.264 NVENC indisponivel: o MOVA nao pode usar fallback silencioso para CPU."
            )
        if progress_cb:
            progress_cb(3, "Reservando a RTX 5090 e liberando a VRAM ociosa do ComfyUI.")
        _prepare_comfy_gpu_for_mova()
        mova_prompt_id, outputs = _run_mova_generation(
            prompt=effective_prompt,
            negative_prompt=effective_negative,
            seed=seed,
            width=width,
            height=height,
            frames=frames,
            fps=fps,
            steps=steps,
            guidance=guidance,
            base_image_bytes=base_image_bytes,
            base_image_name=base_image_name,
            output_root=Path(STUDIO_OUTPUT_DIR),
            ffmpeg=ff,
            progress_cb=progress_cb,
            cancel_event=cancel_event,
            process_cb=process_cb,
        )
        if progress_cb:
            progress_cb(98, "Aplicando gates de voz e pose final.")
        bk_log(f"Generative video MOVA: prompt_id={mova_prompt_id} outputs={len(outputs)}")
        is_review_candidate = (int(width), int(height)) in {(640, 352), (832, 480)}
        final_hold_qc = {
            "status": "UNVERIFIED",
            "passed": False,
            "hold_seconds": float((producer_plan.get("motion_contract") or {}).get("required_final_hold_seconds") or 0.75),
            "method": "ffmpeg_frame_difference_v1",
            "error": "saida de video MOVA nao localizada para QC",
        }
        media_qc = {
            "status": "UNVERIFIED",
            "passed": False,
            "failures": ["OUTPUT_NOT_FOUND"],
            "method": "ffprobe_ebur128_v1",
        }
        visible_text_qc = {
            "status": "UNVERIFIED",
            "passed": False,
            "failures": ["OUTPUT_NOT_FOUND"],
            "method": "temporal_visible_text_v1",
        }
        output_root = Path(STUDIO_OUTPUT_DIR).resolve()
        for output in outputs:
            if output.get("kind") != "video" or not output.get("path"):
                continue
            candidate = (output_root / str(output["path"])).resolve()
            if output_root not in candidate.parents or not candidate.is_file():
                continue
            final_hold_qc = _inspect_mova_final_hold(
                candidate,
                ffmpeg=ff,
                duration_seconds=max(0.0, (int(frames) - 1) / float(fps)),
                hold_seconds=float((producer_plan.get("motion_contract") or {}).get("required_final_hold_seconds") or 0.75),
            )
            media_qc = _inspect_mova_media(
                candidate,
                ffmpeg=ff,
                expected_duration_seconds=max(0.0, (int(frames) - 1) / float(fps)),
            )
            visible_text_qc = _inspect_visible_text(candidate)
            break
        voice_contract = producer_plan.get("voice_contract") or {}
        if not visible_text_qc.get("passed"):
            approval_status = "AUTO_REJECTED_VISIBLE_TEXT"
            message = "Take MOVA reprovado automaticamente: texto, legenda ou interface detectada na imagem. Upscale bloqueado."
        elif not final_hold_qc.get("passed"):
            approval_status = "AUTO_REJECTED_MOTION"
            message = "Take MOVA reprovado automaticamente: a pose final nao ficou estavel. Upscale bloqueado."
        elif not media_qc.get("passed"):
            approval_status = "AUTO_REJECTED_AUDIO"
            message = "Take MOVA reprovado automaticamente: o audio ou o container falhou no QC. Upscale bloqueado."
        elif voice_contract.get("human_pt_br_listening_required"):
            approval_status = "PENDING_PT_BR_VOICE_REVIEW"
            message = "Candidato MOVA pronto, mas bloqueado ate escuta confirmar portugues brasileiro (pt-BR). Upscale nao iniciado."
        else:
            approval_status = "PENDING_HUMAN_REVIEW"
            message = "Candidato MOVA pronto para revisao humana; upscale nao iniciado."
        if progress_cb:
            progress_cb(100, "Concluido com gates de qualidade aplicados.")
        return {
            "ok": True,
            "mode": "video",
            "message": message,
            "prompt_id": mova_prompt_id,
            "seed": seed,
            "model": MOVA_MODEL_NAME,
            "lora": "",
            "video_conditioning_profile": (
                "mova_preview_640x352_rtx5090"
                if (int(width), int(height)) == (640, 352)
                else (
                    "mova_review_832x480_rtx5090"
                    if (int(width), int(height)) == (832, 480)
                    else "mova_720p_rtx5090_128gb"
                )
            ),
            "producer_plan": producer_plan,
            "quality_gate": {
                "policy_version": producer_plan.get("version"),
                "voice": voice_contract,
                "motion": {
                    **(producer_plan.get("motion_contract") or {}),
                    "final_hold_qc": final_hold_qc,
                },
                "media": media_qc,
                "visible_text": visible_text_qc,
                "delivery_allowed": False,
            },
            "approval_status": approval_status,
            "upscale_started": False,
            "upscale_allowed": False,
            "outputs": outputs,
        }
    online, comfy = _comfy_online()
    if not online:
        raise RuntimeError(f"ComfyUI offline: {comfy}")

    diffusion_models = _model_files("diffusion_models")
    unet_models = _model_files("unet", suffixes=(".safetensors", ".ckpt", ".pt", ".gguf"))
    flux_models = [m for m in unet_models if m.lower().startswith("flux")]
    qwen_models = [m for m in diffusion_models if m == DEFAULT_QWEN_MODEL]
    qwen_edit_models = [m for m in diffusion_models if m == DEFAULT_QWEN_EDIT_MODEL]
    image_models = flux_models + qwen_models
    video_models = _video_model_files(diffusion_models, unet_models)
    if os.environ.get("STUDIO_ENABLE_REJECTED_HUNYUAN", "0") != "1":
        video_models = [name for name in video_models if name != HUNYUAN15_I2V_MODEL]
    loras = _model_files("loras")
    selected_lora = lora if lora in loras else ""
    selected_strength = _safe_float(lora_strength, 0.0, -2.0, 2.0)
    if selected_lora and selected_strength == 0:
        selected_strength = 0.7
    if seed is None or int(seed) < 0:
        seed = random.randrange(1, 2**63)
    else:
        seed = int(seed)

    if mode == "video":
        requested_model = str(model or "").strip()
        selected_model = _available_model(model, video_models, DEFAULT_VIDEO_MODEL)
        if strict_video_model and selected_model != requested_model:
            raise RuntimeError(
                f"Modelo de video configurado indisponivel: {requested_model}"
            )
        is_minimax_h3 = _is_minimax_h3_model(selected_model)
        is_ltx25 = selected_model == _LTX25_MODEL_NAME
        is_wan_animate = selected_model == WAN22_ANIMATE_MODEL_NAME
        h3_reference_mode = str(minimax_reference_mode or "").strip().lower()
        if is_minimax_h3 and h3_reference_mode == "ref2va_motion":
            if selected_model != MINIMAX_H3_REF2VA_MODEL_NAME:
                raise RuntimeError(
                    "H3_MODEL_MODE_MISMATCH: Ref2VA exige o checkpoint Ref2VA separado; "
                    "FL2VA nao sera usado como fallback."
                )
        elif selected_model == MINIMAX_H3_REF2VA_MODEL_NAME:
            raise RuntimeError(
                "H3_MODEL_MODE_MISMATCH: o checkpoint Ref2VA exige minimax_reference_mode=ref2va_motion."
            )
        is_minimax_h3_vertical = (
            is_minimax_h3
            and (int(width), int(height))
            == (MINIMAX_H3_VERTICAL_WIDTH, MINIMAX_H3_VERTICAL_HEIGHT)
        )
        # pemara_estudio_40anos: render nativo em 480p/16fps/81f e pos-processamento para 1920x1080@30fps.
        # A regra absoluta 720p30 e' preservada por padrao; este modo e' opt-in via flag.
        pemara_40anos = _pemara_estudio_40anos_enabled()
        if is_minimax_h3:
            if h3_model_variant == _FAST_H3_VARIANT and (
                minimax_reference_images
                or minimax_reference_video_bytes or minimax_h3_guide_image_bytes
                or creative_all_in_one or creative_timeline_request is not None
                or creative_motion_request is not None or creative_fun_control_request is not None
                or str(minimax_reference_mode or "").strip()
            ):
                raise ValueError("H3_FAST_REFERENCE_UNSUPPORTED: FastH3 aceita texto e primeiro/ultimo quadro, sem Ref2VA, guias intermediarios ou adapters.")
            if h3_model_variant == _FAST_H3_VARIANT and selected_model != MINIMAX_H3_MODEL_NAME:
                raise ValueError("FastH3 exige H3 FL2VA explicitamente selecionado; Ref2VA nao e compatível.")
            requested_rate = validate_video_fps(fps, classic_only=True)
            requested_duration = (
                float(video_duration)
                if video_duration is not None
                else max(0.001, (int(frames) - 1) / requested_rate)
            )
            h3_quality_profile, h3_profile, is_minimax_h3_vertical = _resolve_h3_quality_profile(
                h3_quality_profile, width=width, height=height, steps=steps,
                model_variant=h3_model_variant,
            )
            orientation = str(h3_orientation or "").strip().lower()
            if orientation and orientation not in {"landscape", "portrait", "horizontal", "vertical"}:
                raise ValueError("Orientação H3 inválida. Use horizontal ou vertical.")
            if orientation:
                is_minimax_h3_vertical = orientation in {"portrait", "vertical"}
            expected_width = h3_profile["verticalWidth"] if is_minimax_h3_vertical else h3_profile["width"]
            expected_height = h3_profile["verticalHeight"] if is_minimax_h3_vertical else h3_profile["height"]
            w = _safe_video_dimension(width, expected_width, expected_width, expected_width)
            h = _safe_video_dimension(height, expected_height, expected_height, expected_height)
            f, rate, effective_video_duration = _minimax_h3_timing(
                requested_duration,
                requested_rate,
                allow_owner_long_window=allow_minimax_h3_owner_long_window,
            )
            allowed_h3_steps = (_FAST_H3_STEPS,) if h3_model_variant == _FAST_H3_VARIANT else h3_profile["steps"]
            st = _safe_int(steps, allowed_h3_steps[0], min(allowed_h3_steps), max(allowed_h3_steps))
            if st not in allowed_h3_steps:
                raise ValueError(f"{h3_profile['label']} exige {min(allowed_h3_steps)}-{max(allowed_h3_steps)} steps.")
            if h3_profile.get("draftOnly"):
                enable_minimax_h3_native_audio = False
        elif is_ltx25:
            w = _safe_video_dimension(width, 960, 960, 960)
            h = _safe_video_dimension(height, 544, 544, 544)
            f = _safe_int(frames, 145, 25, 721)
            if (f - 1) % 8:
                raise ValueError("LTX 2.5 exige 8n+1 quadros entre 25 e 721.")
            st = _safe_int(steps, 8, 8, 8)
        elif is_wan_animate:
            if (int(width), int(height)) != (720, 1280):
                raise ValueError(
                    "WAN_ANIMATE_VERTICAL_GEOMETRY_REQUIRED: "
                    "o scaffold DWPose fixado exige 720x1280."
                )
            # The generic video limits default to 1280x720 and used to clamp
            # portrait takes to 720x720 before the validated-geometry gate ran.
            # Resolve this pinned portrait profile independently so its height
            # cannot be silently truncated.
            w, h = 720, 1280
            f = _safe_int(frames, 109, 25, 601)
            st = _safe_int(steps, WAN_ANIMATE_DEFAULT_STEPS, WAN_ANIMATE_DEFAULT_STEPS, 60)
        elif pemara_40anos:
            video_max_w = _safe_video_dimension(os.environ.get("STUDIO_VIDEO_MAX_WIDTH", "832"), 832, 512, 2048)
            video_max_h = _safe_video_dimension(os.environ.get("STUDIO_VIDEO_MAX_HEIGHT", "480"), 480, 288, 1152)
            w = _safe_video_dimension(width, 832, 512, video_max_w)
            h = _safe_video_dimension(height, 480, 288, video_max_h)
            f = _safe_int(frames, 81, 25, 161)
            st = _safe_int(steps, 24, 6, 60)
        else:
            video_max_w = _safe_video_dimension(os.environ.get("STUDIO_VIDEO_MAX_WIDTH", "1280"), 1280, 512, 2048)
            video_max_h = _safe_video_dimension(os.environ.get("STUDIO_VIDEO_MAX_HEIGHT", "720"), 720, 288, 1152)
            w = _safe_video_dimension(width, 1280, 512, video_max_w)
            h = _safe_video_dimension(height, 720, 288, video_max_h)
            f = _safe_int(frames, 181, 25, 601)
            st = _safe_int(steps, 28, 16, 60)
        cfg = _safe_float(
            guidance,
            1.0 if is_ltx25 or is_minimax_h3 else 6.0 if not pemara_40anos else 5.0,
            1.0,
            12.0,
        )
        if is_ltx25 and cfg != 1.0:
            raise ValueError("O workflow LTX 2.5 destilado exige guidance 1.0.")
        # Regra ABSOLUTA do usuario (2026-07-19): geracao nativa sempre 1280x720@30fps.
        # Upscale/interpolacao e pos-processamento (RIFE/AnimeVideo), nunca render nativo
        # em outra geometria. Excecoes:
        #   * STUDIO_ALLOW_CUSTOM_VIDEO_GEOMETRY=1  -> laboratorio
        #   * STUDIO_ALLOW_PEMARA_ESTUDIO_40ANOS=1  -> pipeline 40 anos (480p nativo -> upscale+RIFE -> 1080p30)
        #   * allow_validated_video_geometry=True   -> job interno de take com spec local validado
        custom_video_geometry = (
            allow_validated_video_geometry
            or os.environ.get("STUDIO_ALLOW_CUSTOM_VIDEO_GEOMETRY", "0") == "1"
        )
        if not is_minimax_h3 and not is_ltx25 and not custom_video_geometry and not pemara_40anos:
            if (w, h) != (1280, 720):
                print(f"[STUDIO] geometria {w}x{h} substituida pela regra absoluta 1280x720.")
                w, h = 1280, 720
        # A janela temporal nativa do modelo nao autoriza arquivo a 16 FPS.
        # Todo preview/intermediario revisavel do Pemara parte de 24 FPS.
        if not is_minimax_h3:
            rate = validate_video_fps(
                _safe_float(fps, 30.0 if not pemara_40anos else 16.0, 1.0, 60.0)
            )
        if is_ltx25 and float(rate) != 24.0:
            raise ValueError("O workflow LTX 2.5 fixado exige 24 FPS.")
        if not is_minimax_h3 and not is_ltx25 and not custom_video_geometry and not pemara_40anos and int(round(rate)) != 30:
            print(f"[STUDIO] fps {rate} substituido pela regra absoluta 30fps (upscale/interpolacao e pos).")
            rate = 30.0
        base_ref = _save_comfy_input_image(base_image_bytes, base_image_name, (w, h)) if base_image_bytes else ""
        end_ref = _save_comfy_input_image(end_image_bytes, end_image_name, (w, h)) if end_image_bytes else ""
        h3_guide_ref = (
            _save_comfy_input_image(
                minimax_h3_guide_image_bytes,
                minimax_h3_guide_image_name,
                (w, h),
            )
            if minimax_h3_guide_image_bytes
            else ""
        )
        pose_video_ref = (
            _save_comfy_input_video(pose_video_bytes, pose_video_name)
            if pose_video_bytes
            else ""
        )
        if end_ref and not base_ref and not is_minimax_h3:
            raise ValueError("Quadro final exige uma imagem-base aprovada.")
        if is_minimax_h3 and str(minimax_reference_mode).strip().lower() != "ref2va_motion":
            h3_mode = _detect_h3_base_mode(
                has_first_frame=bool(base_ref),
                has_last_frame=bool(end_ref),
            )
            prompt_document = _compile_h3_base_prompt(
                prompt,
                mode=h3_mode,
                duration_seconds=effective_video_duration,
                overall_soundscape=(
                    "Physical ambience and visible action sounds remain synchronized "
                    "with the target video timeline."
                    if enable_minimax_h3_native_audio
                    else "N/A"
                ),
                non_diegetic_music="N/A",
            )
            prompt = prompt_document.prompt
        prefix = "maestro_generative/video"
        if is_minimax_h3:
            if visual_only_pass and enable_minimax_h3_native_audio:
                raise ValueError("Passe visual MiniMax H3 nao pode publicar audio nativo.")
            if creative_all_in_one:
                from creative_os.all_in_one import build as build_all_in_one
                all_in_one_contract=build_all_in_one(prompt=prompt,seed=seed,width=w,height=h,frames=f,steps=st,
                    first_frame=base_ref,last_frame=end_ref,native_audio=enable_minimax_h3_native_audio)
                workflow=all_in_one_contract["graph"]
            elif timeline_contract is not None:
                workflow = timeline_contract["graph"]
            elif motion_contract is not None:
                workflow = motion_contract["graph"]
            elif str(minimax_reference_mode).strip().lower() == "ref2va_motion":
                reference_refs = [
                    _save_comfy_input_image(data, name, (w, h))
                    for data, name in (minimax_reference_images or [])
                ]
                reference_video_ref = _save_comfy_input_video(
                    minimax_reference_video_bytes,
                    minimax_reference_video_name,
                )
                workflow = _build_minimax_h3_ref2va_workflow(
                    prompt=prompt,
                    negative=negative,
                    width=w,
                    height=h,
                    frames=f,
                    steps=st,
                    seed=seed,
                    prefix="maestro_generative/video/minimax_h3_ref2va",
                    reference_image_names=reference_refs,
                    reference_video_name=reference_video_ref,
                    include_native_audio=enable_minimax_h3_native_audio,
                    enable_live_preview=enable_minimax_h3_live_preview,
                    fps=rate,
                    allow_owner_long_window=allow_minimax_h3_owner_long_window,
                    h3_quality_profile=h3_quality_profile,
                )
            else:
                workflow = _build_minimax_h3_fl2va_workflow(
                    prompt=prompt,
                    negative=negative,
                    width=w,
                    height=h,
                    frames=f,
                    steps=st,
                    seed=seed,
                    prefix="maestro_generative/video/minimax_h3_fl2va",
                    base_image_name=base_ref,
                    end_image_name=end_ref,
                    include_native_audio=enable_minimax_h3_native_audio,
                    enable_live_preview=enable_minimax_h3_live_preview,
                    fps=rate,
                    allow_owner_long_window=allow_minimax_h3_owner_long_window,
                    h3_quality_profile=h3_quality_profile,
                    h3_model_variant=h3_model_variant,
                    last_frame_index=minimax_h3_last_frame_index,
                    guide_image_name=h3_guide_ref,
                    guide_frame_index=minimax_h3_guide_frame_index,
                )
            if creative_fun_control_request is not None:
                from creative_os.fun_control import apply_in_worker
                workflow,fun_control_contract=apply_in_worker(globals(),workflow,creative_fun_control_request)
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=21600, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
        elif is_ltx25:
            if not base_ref:
                raise ValueError("LTX 2.5 I2V exige imagem-ancora inicial aprovada.")
            workflow = _build_ltx25_i2v_workflow(
                prompt=prompt,
                negative=negative,
                base_image_name=base_ref,
                end_image_name=end_ref,
                width=w,
                height=h,
                frames=f,
                fps=rate,
                seed=seed,
                filename_prefix="maestro_generative/video/ltx25",
                include_native_audio=False,
            )
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=21600, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
        elif is_wan_animate:
            if not base_ref or not pose_video_ref:
                raise ValueError(
                    "Wan Animate Move exige imagem aprovada e video DWPose aprovado."
                )
            if end_ref:
                raise ValueError(
                    "Wan Animate Move usa referencia de aparencia, nao ancora final temporal."
                )
            if video_conditioning_profile != "wan_animate_exact_pose":
                raise ValueError(
                    "Wan Animate Move exige video_conditioning_profile=wan_animate_exact_pose."
                )
            workflow = _build_wan_animate_move_workflow(
                prompt=prompt,
                negative=negative,
                reference_image_name=base_ref,
                approved_pose_video_name=pose_video_ref,
                prefix="maestro_generative/video/wan22_animate_move",
                width=w,
                height=h,
                frames=f,
                fps=int(round(rate)),
                steps=st,
                cfg=cfg,
                seed=seed,
            )
            _validate_wan_animate_move_graph(workflow)
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=21600, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
        elif selected_model == HUNYUAN15_I2V_MODEL:
            if not base_ref:
                raise ValueError("HunyuanVideo-1.5 I2V exige imagem base aprovada.")
            # HunyuanVideo-1.5 usa comprimento temporal 4n+1.
            f = max(25, ((f - 1) // 4) * 4 + 1)
            run_token = f"{int(_t.time())}_{seed}"
            prefix = f"maestro_generative/video/hunyuan15_{run_token}"
            workflow = build_hunyuan15_i2v_workflow(
                prompt=prompt,
                negative=negative,
                input_image=base_ref,
                width=w,
                height=h,
                frames=f,
                fps=rate,
                steps=st,
                cfg=cfg,
                seed=seed,
                filename_prefix=prefix,
                latent_prefix=f"maestro_generative/latents/hunyuan15_{run_token}",
            )
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=21600, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
        else:
            fun_camera_pair = _wan22_fun_camera_pair(selected_model)
            a14b_pair = _wan22_i2v_a14b_pair(selected_model)
        if not is_minimax_h3 and not is_ltx25 and not is_wan_animate and selected_model != HUNYUAN15_I2V_MODEL and fun_camera_pair:
            if end_ref:
                raise ValueError("Wan2.2 Fun Camera usa somente o quadro inicial aprovado.")
            high_model, low_model = fun_camera_pair
            workflow = _build_wan22_fun_camera_webm_workflow(
                prompt, negative, high_model, low_model, w, h, f, st, cfg, rate, seed,
                prefix, base_ref, camera_pose or "Pan Right", camera_speed,
            )
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=21600, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
            selected_model = f"{high_model} + {low_model} [{camera_pose or 'Pan Right'}]"
        elif not is_minimax_h3 and not is_ltx25 and not is_wan_animate and selected_model != HUNYUAN15_I2V_MODEL and a14b_pair:
            high_model, low_model = a14b_pair
            workflow = _build_wan22_a14b_i2v_webm_workflow(
                prompt, negative, high_model, low_model, selected_lora, selected_strength,
                w, h, f, st, cfg, rate, seed, prefix, base_ref, end_ref,
                video_conditioning_profile,
            )
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=21600, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
            selected_model = f"{high_model} + {low_model}"
        elif not is_minimax_h3 and not is_ltx25 and not is_wan_animate and selected_model != HUNYUAN15_I2V_MODEL:
            if end_ref:
                raise ValueError("Quadro final local esta habilitado somente no Wan2.2 A14B I2V validado.")
            workflow = _build_wan_webm_workflow(
                prompt, negative, selected_model, selected_lora, selected_strength,
                w, h, f, st, cfg, rate, seed, prefix, base_ref,
            )
            prompt_id, outputs = _queue_comfy_workflow(
                workflow, timeout=2400, progress_cb=progress_cb,
                cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
                resume_prompt_id=resume_prompt_id,
            )
        if progress_cb:
            progress_cb(96, f"Convertendo para MP4 {w}x{h}/{int(round(rate))}fps.")
        outputs = _finalize_video_mp4(outputs, fps=int(round(rate)), width=w, height=h)
        text = f"Video MP4 {w}x{h}/{int(round(rate))}fps gerado com {selected_model}."
    elif mode in ("marketing_card", "card", "real_card"):
        if not base_image_bytes:
            raise ValueError("Envie a foto real/base do produto para gerar card real.")
        selected_model = _available_model(model, qwen_edit_models, DEFAULT_MARKETING_CARD_MODEL)
        w = _safe_int(width, DEFAULT_MARKETING_CARD_WIDTH, 768, 1536, 32)
        h = _safe_int(height, DEFAULT_MARKETING_CARD_HEIGHT, 960, 1536, 32)
        st = _safe_int(steps, DEFAULT_MARKETING_CARD_STEPS, 24, 80)
        cfg = _safe_float(guidance, DEFAULT_MARKETING_CARD_GUIDANCE, 1.0, 8.0)
        base_ref = _save_marketing_reference_image(base_image_bytes, base_image_name, prompt, (w, h))
        prefix = "maestro_generative/marketing_card"
        workflow = _build_qwen_edit_workflow(
            _marketing_card_prompt(prompt),
            _marketing_card_negative(negative),
            selected_model,
            w,
            h,
            st,
            cfg,
            seed,
            prefix,
            base_ref,
        )
        prompt_id, outputs = _queue_comfy_workflow(
            workflow, timeout=1800, progress_cb=progress_cb,
            cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
        )
        mode = "marketing_card"
        text = f"Card real gerado com {selected_model}. Valide OCR/produto antes de publicar."
    elif mode == "edit":
        if not base_image_bytes:
            raise ValueError("Envie uma imagem base para editar.")
        selected_model = _available_model(model, qwen_edit_models, DEFAULT_QWEN_EDIT_MODEL)
        w = _safe_int(width, 1024, 512, 4096 if selected_model == DEFAULT_QWEN_MODEL else 1536, 32)
        h = _safe_int(height, 1024, 512, 4096 if selected_model == DEFAULT_QWEN_MODEL else 1536, 32)
        st = _safe_int(steps, 40, 8, 80)
        cfg = _safe_float(guidance, 1.0, 1.0, 8.0)
        base_ref = _save_comfy_input_image(base_image_bytes, base_image_name)
        prefix = "maestro_generative/image_edit"
        workflow = _build_qwen_edit_workflow(
            prompt, negative, selected_model, w, h, st, cfg, seed, prefix, base_ref,
        )
        prompt_id, outputs = _queue_comfy_workflow(
            workflow, timeout=1200, progress_cb=progress_cb,
            cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
        )
        text = f"Foto editada com {selected_model}."
    elif mode == "image":
        selected_model = _available_model(model, image_models, DEFAULT_FLUX_MODEL)
        w = _safe_int(width, 1024, 512, 4096 if selected_model == DEFAULT_QWEN_MODEL else 1536, 32)
        h = _safe_int(height, 1024, 512, 4096 if selected_model == DEFAULT_QWEN_MODEL else 1536, 32)
        st = _safe_int(steps, 40 if selected_model == DEFAULT_QWEN_MODEL else 28, 8, 80)
        cfg = _safe_float(guidance, 1.0 if selected_model == DEFAULT_QWEN_MODEL else 3.5, 1.0, 8.0)
        prefix = "maestro_generative/image"
        if selected_model.lower().startswith("qwen_image"):
            workflow = _build_qwen_image_workflow(
                prompt, negative, selected_model, selected_lora, selected_strength,
                w, h, st, cfg, seed, prefix,
            )
        else:
            final_prompt = prompt if not negative else f"{prompt}\nAvoid: {negative}"
            workflow = _build_flux_workflow(
                final_prompt, selected_model, selected_lora, selected_strength,
                w, h, st, cfg, seed, prefix,
            )
        prompt_id, outputs = _queue_comfy_workflow(
            workflow, timeout=900, progress_cb=progress_cb,
            cancel_event=cancel_event, prompt_id_cb=prompt_id_cb,
        )
        text = f"Imagem gerada com {selected_model}."
    else:
        raise ValueError("Modo invalido. Use image, edit, marketing_card, video, music ou sfx.")

    if progress_cb:
        progress_cb(100, "Concluido.")
    bk_log(f"Generative {mode}: prompt_id={prompt_id} outputs={len(outputs)}")
    return {
        "ok": True,
        "mode": mode,
        "engine_id": engine_id if mode == "video" else None,
        "fallback_used": False if mode == "video" else None,
        "message": text,
        "prompt_id": prompt_id,
        "seed": seed,
        "model": selected_model,
        "lora": selected_lora,
        "video_conditioning_profile": video_conditioning_profile if mode == "video" else "",
        "frames": timeline_contract["output_frames"] if timeline_contract else sum(motion_contract["segment_frames"]) if motion_contract else (int(f) if mode == "video" else None),
        "fps": float(rate) if mode == "video" else None,
        "duration_seconds": (
            timeline_contract["output_frames"] / 24.0 if timeline_contract else sum(motion_contract["segment_frames"]) / 24.0 if motion_contract else float(effective_video_duration)
            if mode == "video" and is_minimax_h3
            else ((int(f) - 1) / float(rate) if mode == "video" else None)
        ),
        "native_audio_enabled": bool(
            mode == "video" and is_minimax_h3 and enable_minimax_h3_native_audio
        ),
        "h3_model_variant": h3_model_variant if mode == "video" and is_minimax_h3 else None,
        "h3_orientation": ("portrait" if is_minimax_h3_vertical else "landscape") if mode == "video" and is_minimax_h3 else None,
        "outputs": outputs,
        "creative_all_in_one": ({k:v for k,v in all_in_one_contract.items() if k!="graph"} if all_in_one_contract else None),
        "creative_fun_control": fun_control_contract,
        "creative_timeline": ({k:v for k,v in timeline_contract.items() if k not in {"graph","base_spec"}} if timeline_contract else None),
        "creative_motion": ({k:v for k,v in motion_contract.items() if k not in {"graph","timeline"}} if motion_contract else None),
    }

@app.post("/api/generative/chat")
async def generative_chat(
    request: Request,
    prompt: str = Form(...),
    mode: str = Form("image"),
    model: str = Form(""),
    engine_id: str = Form(""),
    anchor_contract_id: str = Form(""),
    prompt_compiler_version: str = Form(""),
    negative: str = Form(""),
    lora: str = Form(""),
    lora_strength: float = Form(0.0),
    width: int = Form(1024),
    height: int = Form(1024),
    steps: int = Form(28),
    guidance: float = Form(3.5),
    seed: int = Form(-1),
    frames: int = Form(601),
    fps: float = Form(30.0),
    provider: str = Form(""),
    duration: float = Form(30.0),
    music_lyrics: str = Form(""),
    music_instrumental: bool = Form(False),
    music_model: str = Form(""),
    music_bpm: int = Form(0),
    music_action: str = Form("auto"),
    music_abc: str = Form(""),
    music_abc_reviewed: bool = Form(False),
    music_duration_auto: bool = Form(False),
    video_duration: float | None = Form(None),
    prompt_influence: float = Form(0.5),
    loop: bool = Form(False),
    camera_pose: str = Form(""),
    camera_speed: float = Form(0.8),
    video_conditioning_profile: str = Form("identity_locked"),
    h3_quality_profile: str = Form(""),
    h3_model_variant: str = Form("base"),
    h3_orientation: str = Form("landscape"),
    enable_minimax_h3_native_audio: bool = Form(False),
    enable_minimax_h3_live_preview: bool = Form(False),
    base_image: UploadFile | None = File(None),
    end_image: UploadFile | None = File(None),
):
    if not _is_internal_request(request):
        return _public_forbidden()
    if mode == "music" and provider in {"ace_step_local", "yue2_local", LEVO2_PROVIDER_ID}:
        return JSONResponse(status_code=409, content={"erro": "Música local exige /api/generative/job para reserva da GPU e cancelamento."})
    try:
        base_bytes = await _read_upload_bounded(base_image, "Imagem base")
        end_bytes = await _read_upload_bounded(end_image, "Imagem final")
        return _run_generative(
            prompt=prompt, mode=mode, model=model, engine_id=engine_id,
            anchor_contract_id=anchor_contract_id,
            prompt_compiler_version=prompt_compiler_version,
            negative=negative, lora=lora,
            lora_strength=lora_strength, width=width, height=height, steps=steps,
            guidance=guidance, seed=seed, frames=frames, fps=fps,
            music_lyrics=music_lyrics, music_instrumental=music_instrumental,
            music_model=music_model, music_bpm=music_bpm, music_action=music_action,
            music_abc=music_abc, music_abc_reviewed=music_abc_reviewed, music_duration_auto=music_duration_auto,
            provider=provider, duration=duration, video_duration=video_duration,
            prompt_influence=prompt_influence, loop=loop,
            camera_pose=camera_pose, camera_speed=camera_speed,
            video_conditioning_profile=video_conditioning_profile,
            h3_quality_profile=h3_quality_profile,
            h3_model_variant=h3_model_variant,
            h3_orientation=h3_orientation,
            enable_minimax_h3_native_audio=enable_minimax_h3_native_audio,
            enable_minimax_h3_live_preview=enable_minimax_h3_live_preview,
            base_image_bytes=base_bytes, base_image_name=base_image.filename if base_image else "",
            end_image_bytes=end_bytes, end_image_name=end_image.filename if end_image else "",
        )
    except _VideoEngineError as e:
        return _video_engine_error_response(e)
    except ValueError as e:
        return JSONResponse(status_code=422, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO generative {mode}: {e}")
        logging.error(f"generative {mode}: {e}", exc_info=True)
        if (mode or "").lower().strip() == "video" and _video_generation_paused():
            return JSONResponse(status_code=423, content={"erro": _video_pause_message()})
        return JSONResponse(status_code=500, content={"erro": "Falha interna na geracao."})

_GEN_JOB_SPEC_FIELDS = (
    "prompt", "mode", "model", "engine_id", "negative", "lora", "lora_strength",
    "width", "height", "steps", "guidance", "seed", "frames", "fps",
    "music_lyrics", "music_instrumental", "music_model", "music_bpm",
    "music_action", "music_abc", "music_abc_reviewed", "music_duration_auto",
    "provider", "duration", "video_duration", "prompt_influence", "loop", "camera_pose",
    "camera_speed", "video_conditioning_profile", "h3_quality_profile", "enable_minimax_h3_native_audio",
    "h3_model_variant", "h3_orientation",
    "enable_minimax_h3_live_preview", "anchor_contract_id", "prompt_compiler_version",
    "creative_motion_request",
    "creative_timeline_request",
    "creative_fun_control_request",
    "creative_all_in_one",
)


def _persist_job_input(job_id: str, label: str, data: bytes | None, original_name: str) -> Dict[str, str] | None:
    if data is None:
        return None
    if len(data) > _GEN_JOB_INPUT_MAX_BYTES:
        raise ValueError(
            f"{label} excede o limite de {_GEN_JOB_INPUT_MAX_BYTES // (1024 * 1024)} MB."
        )
    suffix = Path(original_name or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        suffix = ".bin"
    folder = _GEN_JOB_INPUT_ROOT / job_id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{label}{suffix}"
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, target)
    return {
        "path": f"{job_id}/{target.name}",
        "original_name": Path(original_name or target.name).name,
    }


def _load_job_input(metadata: Any) -> Tuple[bytes | None, str]:
    if not metadata:
        return None, ""
    if not isinstance(metadata, dict) or not metadata.get("path"):
        raise ValueError("Referencia de imagem do trabalho e invalida.")
    root = _GEN_JOB_INPUT_ROOT.resolve()
    candidate = (_GEN_JOB_INPUT_ROOT / str(metadata["path"])).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Referencia de imagem fora do repositorio de trabalhos.")
    if not candidate.is_file():
        raise FileNotFoundError("A imagem original deste trabalho nao esta mais disponivel.")
    return candidate.read_bytes(), str(metadata.get("original_name") or candidate.name)


def _job_with_actions(job: Dict[str, Any]) -> Dict[str, Any]:
    status = str(job.get("status") or "")
    with _ACTIVE_GEN_JOBS_LOCK:
        active = job.get("job_id") in _ACTIVE_GEN_JOBS
    job["actions"] = {
        "can_cancel": active and status in {"queued", "running", "canceling"},
        "can_retry": bool(job.get("request_spec")) and status in {"done", "error", "interrupted", "canceled"},
    }
    return job


def _normalize_generative_job_spec(request_spec: Dict[str, Any]) -> Dict[str, Any]:
    engine_field_present = "engine_id" in request_spec
    spec = {field: request_spec.get(field) for field in _GEN_JOB_SPEC_FIELDS}
    spec["mode"] = (str(spec.get("mode") or "image")).lower().strip()
    if spec.get("music_duration_auto") is None:
        spec["music_duration_auto"] = False
    if type(spec["music_duration_auto"]) is not bool:
        raise ValueError("A escolha automática de duração deve ser booleana.")
    if spec["music_duration_auto"]:
        if spec["mode"] != "music" or spec.get("provider") != "yue2_local":
            raise ValueError("Duração escolhida pelo modelo está disponível para música YuE2.")
        spec["duration"] = 900.0
    if spec["mode"] == "music" and spec.get("provider") in {"ace_step_local", "yue2_local", LEVO2_PROVIDER_ID}:
        from music_creation import validate
        for key, value in {"music_lyrics": "", "music_instrumental": False, "music_model": "",
                           "music_bpm": 0, "music_action": "auto", "music_abc": "",
                           "music_abc_reviewed": False}.items():
            if spec.get(key) is None:
                spec[key] = value
        if spec["provider"] != LEVO2_PROVIDER_ID:
            validate(spec["provider"], spec.get("prompt"), spec.get("duration"), spec["music_lyrics"],
                     spec["music_instrumental"], spec["music_model"], spec["music_bpm"],
                     spec["music_action"], spec["music_abc"], spec["music_abc_reviewed"])
        else:
            from levo_music import _bounded_duration
            _bounded_duration(spec.get("duration"))
            if spec["music_action"] not in {"auto", "generate"} or type(spec["music_instrumental"]) is not bool:
                raise ValueError("Pedido musical LeVo 2 inválido.")
            if not isinstance(spec.get("prompt"), str) or not spec["prompt"].strip():
                raise ValueError("Descreva a música que deseja criar.")
            if not isinstance(spec["music_lyrics"], str) or len(spec["music_lyrics"]) > 4096:
                raise ValueError("A letra deve ter até 4096 caracteres.")
            if spec["music_action"] == "generate" and not spec["music_instrumental"] and not spec["music_lyrics"].strip():
                raise ValueError("Informe a letra no modo manual ou use a criação automática.")
    if spec["mode"] == "semantic_review":
        from creative_os.semantic_critic import instruction
        instruction(spec.get("prompt"))
        if spec.get("engine_id") not in {"minimax_h3", "ltx_2_5"}:
            raise ValueError("Avaliação visual exige vídeo H3 ou LTX explícito.")
    if spec["mode"] == "prompt_rewrite":
        if spec.get("engine_id") != "minimax_h3": raise ValueError("Rewriter exige H3 explícito.")
        from creative_os.h3_rewriter import workflow as rewriter_workflow
        rewriter_workflow(spec.get("prompt"),spec.get("video_duration"),spec.get("seed"))
    if spec.get("creative_all_in_one") is None:
        spec["creative_all_in_one"] = False
    if type(spec["creative_all_in_one"]) is not bool:
        raise ValueError("All-In-One deve ser booleano.")
    if spec.get("creative_all_in_one"):
        if spec["mode"] != "video" or spec.get("engine_id") != "minimax_h3" or any(spec.get(k) is not None for k in ("creative_fun_control_request","creative_timeline_request","creative_motion_request")):
            raise ValueError("All-In-One exige um pedido H3 exclusivo.")
    if spec.get("creative_fun_control_request") is not None:
        if spec.get("creative_timeline_request") is not None or spec.get("creative_motion_request") is not None or spec["mode"] != "video" or spec.get("engine_id") != "minimax_h3":
            raise ValueError("Fun Control exige um pedido de vídeo H3 exclusivo.")
    if spec.get("creative_timeline_request") is not None:
        if spec.get("creative_motion_request") is not None or spec["mode"] != "video" or spec.get("engine_id") != "minimax_h3":
            raise ValueError("Timeline exige um pedido de vídeo H3 exclusivo.")
    if spec.get("creative_motion_request") is not None and (spec["mode"] != "video" or spec.get("engine_id") != "minimax_h3"):
        raise ValueError("Motion Director exige modo video e motor minimax_h3 explícitos.")
    if spec["mode"] != "video":
        if str(spec.get("h3_model_variant") or "base").strip().lower() != "base":
            raise ValueError("A variante FastH3 só pode ser usada em vídeo MiniMax H3.")
        spec["enable_minimax_h3_native_audio"] = False
        spec["enable_minimax_h3_live_preview"] = False
        return spec

    engine, expected_model = _resolve_video_engine(
        str(spec.get("engine_id") or ""),
        model=str(spec.get("model") or ""),
        allow_explicit_legacy_model=not engine_field_present,
    )
    spec["engine_id"] = engine.id
    spec["model"] = expected_model
    spec["h3_model_variant"] = str(spec.get("h3_model_variant") or "base").strip().lower()
    if spec["h3_model_variant"] not in {"base", _FAST_H3_VARIANT}:
        raise ValueError("Variante H3 inválida. Use H3 Base ou FastH3 8-Step V2.")
    if spec["h3_model_variant"] == _FAST_H3_VARIANT and engine.id != "minimax_h3":
        raise ValueError("FastH3 8-Step V2 pertence ao motor MiniMax H3, não ao LTX 2.5.")
    if spec["h3_model_variant"] == _FAST_H3_VARIANT and any(
        spec.get(key)
        for key in (
            "creative_motion_request", "creative_timeline_request",
            "creative_fun_control_request", "creative_all_in_one",
        )
    ):
        raise ValueError("FastH3 aceita texto e primeiro/ultimo quadro; controles criativos H3 exigem MiniMax H3 Base.")
    if engine.id == "ltx_2_5":
        spec["enable_minimax_h3_native_audio"] = False
        spec["enable_minimax_h3_live_preview"] = False
        validated = engine.validate_request(spec)
        spec.update(validated)
        spec["frames"] = validated["num_frames"]
        spec["video_duration"] = validated["duration_seconds"]
        return spec

    requested_h3_profile = str(spec.get("h3_quality_profile") or "")
    requested_orientation = str(spec.get("h3_orientation") or "").strip().lower()
    if requested_orientation and requested_orientation not in {"landscape", "portrait", "horizontal", "vertical"}:
        raise ValueError("Orientação H3 inválida. Use horizontal ou vertical.")
    profile_id, profile, _ = _resolve_h3_quality_profile(
        requested_h3_profile,
        width=spec.get("width"), height=spec.get("height"), steps=spec.get("steps"),
        model_variant=spec["h3_model_variant"],
    )
    spec["h3_quality_profile"] = profile_id
    inferred_vertical = (
        int(spec.get("width") or 0) == profile["verticalWidth"]
        and int(spec.get("height") or 0) == profile["verticalHeight"]
    )
    vertical = requested_orientation in {"portrait", "vertical"} if requested_orientation else inferred_vertical
    spec["h3_orientation"] = "portrait" if vertical else "landscape"
    spec["width"] = profile["verticalWidth"] if vertical else profile["width"]
    spec["height"] = profile["verticalHeight"] if vertical else profile["height"]
    allowed_steps = (_FAST_H3_STEPS,) if spec["h3_model_variant"] == _FAST_H3_VARIANT else profile["steps"]
    requested_steps = spec.get("steps")
    if spec["h3_model_variant"] == _FAST_H3_VARIANT and requested_steps is not None and int(requested_steps) != _FAST_H3_STEPS:
        raise ValueError(f"FastH3 8-Step V2 exige exatamente {_FAST_H3_STEPS} steps.")
    spec["steps"] = int(requested_steps or allowed_steps[0]) if requested_h3_profile else allowed_steps[0]
    if spec["steps"] not in allowed_steps:
        raise ValueError(f"{profile['label']} exige {min(allowed_steps)}-{max(allowed_steps)} steps.")
    native_audio = spec.get("enable_minimax_h3_native_audio")
    if native_audio is None:
        spec["enable_minimax_h3_native_audio"] = bool(profile.get("nativeAudio"))
    elif isinstance(native_audio, str):
        spec["enable_minimax_h3_native_audio"] = native_audio.strip().lower() in {
            "1", "true", "yes", "sim", "on",
        }
    else:
        spec["enable_minimax_h3_native_audio"] = bool(native_audio)
    if profile.get("draftOnly"):
        spec["enable_minimax_h3_native_audio"] = False

    live_preview = spec.get("enable_minimax_h3_live_preview")
    if isinstance(live_preview, str):
        spec["enable_minimax_h3_live_preview"] = live_preview.strip().lower() in {
            "1", "true", "yes", "sim", "on",
        }
    else:
        spec["enable_minimax_h3_live_preview"] = bool(live_preview)

    requested_rate = validate_video_fps(spec.get("fps") or MINIMAX_H3_FPS, classic_only=True)
    requested_duration = (
        float(spec["video_duration"])
        if spec.get("video_duration") is not None
        else max(0.001, (int(spec.get("frames") or MINIMAX_H3_MIN_FRAMES) - 1) / requested_rate)
    )
    frames, native_rate, effective_duration = _minimax_h3_timing(
        requested_duration,
        requested_rate,
    )
    spec["frames"] = frames
    spec["fps"] = native_rate
    spec["video_duration"] = effective_duration
    if profile_id in _H3_MASTER_CACHE_PROFILES:
        if vertical or frames != 243:
            raise ValueError("Master20 cache experimental exige take horizontal de 10 segundos.")
        if spec.get("creative_all_in_one") or any(spec.get(key) is not None for key in (
            "creative_fun_control_request", "creative_timeline_request", "creative_motion_request"
        )):
            raise ValueError("Master20 cache experimental aceita FL2VA nativo, sem adapters Creative OS.")
    if spec.get("creative_fun_control_request") is not None:
        from creative_os.fun_control import validate_request as validate_control_request
        validate_control_request(spec["creative_fun_control_request"],engine_id=spec["engine_id"],
            profile=spec["h3_quality_profile"],native_audio=spec["enable_minimax_h3_native_audio"])
    if spec.get("creative_timeline_request") is not None:
        from creative_os.timeline_director import compile_request as compile_timeline_request
        compile_timeline_request(spec["creative_timeline_request"],engine_id=spec["engine_id"],seed=spec["seed"],
            profile=spec["h3_quality_profile"],native_audio=spec["enable_minimax_h3_native_audio"])
    if spec.get("creative_motion_request") is not None:
        from creative_os.motion_director import compile_request
        compile_request(spec["creative_motion_request"],engine_id=spec["engine_id"],seed=spec["seed"],
            profile=spec["h3_quality_profile"],native_audio=spec["enable_minimax_h3_native_audio"])
    return spec


def _start_generative_job(
    request_spec: Dict[str, Any],
    *,
    base_bytes: bytes | None = None,
    base_name: str = "",
    end_bytes: bytes | None = None,
    end_name: str = "",
    source_job_id: str = "",
) -> str:
    spec = _normalize_generative_job_spec(request_spec)
    if spec["mode"] == "video":
        engine = _video_engine_registry_live().get(spec.get("engine_id"))
        if spec.get("h3_model_variant") == _FAST_H3_VARIANT:
            h3_status = _h3_workflow_status_live(comfy_online=True)
            if not h3_status.get("capabilities", {}).get("fastH3Ready"):
                raise _VideoEngineError(
                    "FAST_H3_NOT_READY",
                    "FastH3 não está completo no diretório ativo do ComfyUI; nenhum fallback será usado.",
                    status_code=409,
                )
        readiness = engine.readiness()
        if not readiness.get("production_ready"):
            raise _VideoEngineError(
                "ENGINE_NOT_PRODUCTION_READY",
                str(readiness.get("message") or f"{engine.display_name} ainda nao esta liberado para producao."),
                status_code=409,
                details={
                    "engine_id": engine.id,
                    "state": readiness.get("state"),
                    "gpu_smoke_required": bool(readiness.get("gpu_smoke_required")),
                },
            )
    job_id = uuid.uuid4().hex
    try:
        input_files = {
            "base": _persist_job_input(job_id, "base", base_bytes, base_name),
            "end": _persist_job_input(job_id, "end", end_bytes, end_name),
        }
    except Exception:
        job_folder = (_GEN_JOB_INPUT_ROOT / job_id).resolve()
        root = _GEN_JOB_INPUT_ROOT.resolve()
        if root in job_folder.parents and job_folder.exists():
            shutil.rmtree(job_folder, ignore_errors=True)
        raise

    cancel_event = threading.Event()
    with _ACTIVE_GEN_JOBS_LOCK:
        _ACTIVE_GEN_JOBS[job_id] = {"cancel_event": cancel_event}
    _set_gen_job(
        job_id,
        status="queued",
        progress=1,
        message="Na fila para iniciar.",
        result=None,
        error=None,
        prompt_id=None,
        mode=spec["mode"],
        engine_id=spec.get("engine_id") or None,
        model=spec.get("model") or "",
        prompt=spec.get("prompt") or "",
        base_image_name=base_name,
        end_image_name=end_name,
        width=spec.get("width"),
        height=spec.get("height"),
        frames=spec.get("frames"),
        fps=spec.get("fps"),
        video_duration=spec.get("video_duration"),
        request_spec=spec,
        input_files=input_files,
        source_job_id=source_job_id or None,
    )

    def update(pct: int, msg: str) -> None:
        if cancel_event.is_set():
            raise GenerationCancelled("Geracao cancelada pelo proprietario.")
        _set_gen_job(job_id, progress=max(1, min(100, int(pct))), message=msg)

    def record_prompt_id(prompt_id: str) -> None:
        _set_gen_job(job_id, prompt_id=prompt_id, message="Workflow enviado ao ComfyUI.")

    def record_process(process) -> None:
        with _ACTIVE_GEN_JOBS_LOCK:
            active = _ACTIVE_GEN_JOBS.get(job_id)
            if active is not None:
                if process is None:
                    active.pop("process", None)
                else:
                    active["process"] = process
        if process is not None:
            if spec.get("provider") == "ace_step_local":
                isolated_engine = "ace_step"
                isolated_label = "ACE-Step"
            elif spec.get("provider") == LEVO2_PROVIDER_ID:
                isolated_engine = "levo2"
                isolated_label = "LeVo 2"
            elif spec.get("engine_id") == "ltx_2_5":
                isolated_engine = "ltx25"
                isolated_label = "LTX 2.5"
            else:
                isolated_engine = "mova"
                isolated_label = "MOVA"
            _set_gen_job(
                job_id,
                prompt_id=f"{isolated_engine}:{process.pid}",
                message=f"Processo {isolated_label} isolado iniciado.",
            )

    def worker() -> None:
        creative_lease_acquired = False
        try:
            if cancel_event.is_set():
                raise GenerationCancelled("Geracao cancelada antes de iniciar.")
            if spec["mode"] in {"video", "image", "edit", "prompt_rewrite", "semantic_review"} or (
                spec["mode"] == "music" and spec.get("provider") in {"ace_step_local", "yue2_local", LEVO2_PROVIDER_ID}
            ):
                _wait_for_gpu_lease(job_id, operation="studio_generative", project_id="", take_id="", cancel_event=cancel_event)
                creative_lease_acquired = True
            _set_gen_job(job_id, status="running", message="Iniciando geracao.", started_at=_t.time())
            result = _run_generative(
                **spec,
                gpu_job_id=job_id,
                base_image_bytes=base_bytes,
                base_image_name=base_name,
                end_image_bytes=end_bytes,
                end_image_name=end_name,
                progress_cb=update,
                cancel_event=cancel_event,
                prompt_id_cb=record_prompt_id,
                process_cb=record_process,
            )
            if cancel_event.is_set():
                raise GenerationCancelled("Geracao cancelada pelo proprietario.")
            _set_gen_job(job_id, status="done", progress=100, message="Concluido.", result=result)
        except GenerationCancelled as exc:
            current = _get_gen_job(job_id) or {}
            _set_gen_job(
                job_id,
                status="canceled",
                progress=int(current.get("progress", 0) or 0),
                message="Cancelado pelo proprietario.",
                error=str(exc),
            )
        except Exception as exc:
            if cancel_event.is_set():
                current = _get_gen_job(job_id) or {}
                _set_gen_job(
                    job_id,
                    status="canceled",
                    progress=int(current.get("progress", 0) or 0),
                    message="Cancelado pelo proprietario.",
                    error="Cancelamento confirmado.",
                )
            else:
                bk_log(f"ERRO generative job {job_id}: {exc}")
                logging.error(f"generative job {job_id}: {exc}", exc_info=True)
                _set_gen_job(job_id, status="error", progress=100, message="Erro.", error=str(exc))
        finally:
            if creative_lease_acquired:
                _GPU_LEASE_REGISTRY.release(job_id)
            with _ACTIVE_GEN_JOBS_LOCK:
                _ACTIVE_GEN_JOBS.pop(job_id, None)

    threading.Thread(
        target=worker,
        daemon=True,
        name=f"studio-generative-{job_id[:8]}",
    ).start()
    return job_id


@app.post("/api/generative/mova/producer")
async def generative_mova_producer(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await request.json()
        prompt = str((payload or {}).get("prompt") or "").strip()
        fps = max(24, min(60, int(float((payload or {}).get("fps") or 24))))
        plan = _analyze_mova_take(prompt, fps=fps)
        _enforce_mova_policy(plan)
        return {"ok": True, "plan": plan}
    except (TypeError, ValueError) as exc:
        return JSONResponse(status_code=422, content={"erro": str(exc)})


@app.post("/api/generative/job")
async def generative_job_start(
    request: Request,
    prompt: str = Form(...),
    mode: str = Form("image"),
    model: str = Form(""),
    engine_id: str = Form(""),
    anchor_contract_id: str = Form(""),
    prompt_compiler_version: str = Form(""),
    negative: str = Form(""),
    lora: str = Form(""),
    lora_strength: float = Form(0.0),
    width: int = Form(1024),
    height: int = Form(1024),
    steps: int = Form(28),
    guidance: float = Form(3.5),
    seed: int = Form(-1),
    frames: int = Form(601),
    fps: float = Form(30.0),
    provider: str = Form(""),
    duration: float = Form(30.0),
    music_lyrics: str = Form(""),
    music_instrumental: bool = Form(False),
    music_model: str = Form(""),
    music_bpm: int = Form(0),
    music_action: str = Form("auto"),
    music_abc: str = Form(""),
    music_abc_reviewed: bool = Form(False),
    music_duration_auto: bool = Form(False),
    video_duration: float | None = Form(None),
    prompt_influence: float = Form(0.5),
    loop: bool = Form(False),
    camera_pose: str = Form(""),
    camera_speed: float = Form(0.8),
    video_conditioning_profile: str = Form("identity_locked"),
    h3_quality_profile: str = Form(""),
    h3_model_variant: str = Form("base"),
    h3_orientation: str = Form("landscape"),
    enable_minimax_h3_native_audio: bool = Form(False),
    enable_minimax_h3_live_preview: bool = Form(False),
    base_image: UploadFile | None = File(None),
    end_image: UploadFile | None = File(None),
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        base_bytes = await _read_upload_bounded(base_image, "Imagem base")
        end_bytes = await _read_upload_bounded(end_image, "Imagem final")
    except ValueError as exc:
        return JSONResponse(status_code=413, content={"erro": str(exc)})
    base_name = base_image.filename if base_image else ""
    end_name = end_image.filename if end_image else ""
    if (mode or "").lower().strip() == "video" and _video_generation_paused():
        return JSONResponse(status_code=423, content={"erro": _video_pause_message()})
    request_spec = {
        "prompt": prompt, "mode": mode, "model": model, "engine_id": engine_id, "negative": negative,
        "lora": lora, "lora_strength": lora_strength, "width": width, "height": height,
        "steps": steps, "guidance": guidance, "seed": seed, "frames": frames, "fps": fps,
        "music_lyrics": music_lyrics, "music_instrumental": music_instrumental,
        "music_model": music_model, "music_bpm": music_bpm, "music_action": music_action,
        "music_abc": music_abc, "music_abc_reviewed": music_abc_reviewed, "music_duration_auto": music_duration_auto,
        "provider": provider, "duration": duration, "video_duration": video_duration,
        "prompt_influence": prompt_influence,
        "loop": loop, "camera_pose": camera_pose, "camera_speed": camera_speed,
        "video_conditioning_profile": video_conditioning_profile,
        "h3_quality_profile": h3_quality_profile,
        "h3_model_variant": h3_model_variant,
        "h3_orientation": h3_orientation,
        "enable_minimax_h3_native_audio": enable_minimax_h3_native_audio,
        "enable_minimax_h3_live_preview": enable_minimax_h3_live_preview,
        "anchor_contract_id": anchor_contract_id,
        "prompt_compiler_version": prompt_compiler_version,
    }
    try:
        job_id = _start_generative_job(
            request_spec,
            base_bytes=base_bytes,
            base_name=base_name,
            end_bytes=end_bytes,
            end_name=end_name,
        )
        return {"ok": True, "job_id": job_id}
    except _VideoEngineError as exc:
        return _video_engine_error_response(exc)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"erro": str(exc)})

@app.get("/api/generative/jobs")
async def generative_jobs_list(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    status: str = "",
    mode: str = "",
):
    if not _is_internal_request(request):
        return _public_forbidden()
    payload = _GEN_JOB_STORE.list(page=page, page_size=page_size, status=status, mode=mode)
    payload["items"] = [_job_with_actions(job) for job in payload.get("items", [])]
    return payload

@app.get("/api/generative/job/{job_id}")
async def generative_job_status(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _get_gen_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"erro": "Job nao encontrado"})
    return _job_with_actions(job)


@app.get("/api/generative/video-jobs/{job_id}/receipt")
async def generative_video_job_receipt(request: Request, job_id: str):
    """Return a compact, auditable engine/anchor receipt for one video job."""

    if not _is_internal_request(request):
        return _public_forbidden()
    job = _get_gen_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"ok": False, "code": "JOB_NOT_FOUND", "erro": "Job nao encontrado"})
    if str(job.get("mode") or "") != "video":
        return JSONResponse(
            status_code=409,
            content={"ok": False, "code": "JOB_NOT_VIDEO", "erro": "Este recibo existe somente para jobs de video."},
        )
    spec = job.get("request_spec") if isinstance(job.get("request_spec"), dict) else {}
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    engine_id = str(job.get("engine_id") or spec.get("engine_id") or result.get("engine_id") or "")
    return {
        "ok": True,
        "receipt": {
            "job_id": job_id,
            "status": str(job.get("status") or ""),
            "engine_id": engine_id,
            "model": str(job.get("model") or spec.get("model") or result.get("model") or ""),
            "fallback_used": False,
            "anchor_contract_id": str(spec.get("anchor_contract_id") or ""),
            "prompt_compiler_version": str(spec.get("prompt_compiler_version") or ""),
            "prompt_sha256": hashlib.sha256(str(spec.get("prompt") or job.get("prompt") or "").encode("utf-8")).hexdigest(),
            "owner_approval_state": str(result.get("owner_approval_state") or "PENDING_HUMAN_REVIEW"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        },
    }


def _reconcile_inactive_project_job(job: Dict[str, Any]) -> bool:
    """Move a take out of a busy state when its persisted worker no longer exists."""

    job_id = str(job.get("job_id") or "")
    project_id = str(job.get("project_id") or "")
    take_id = str(job.get("take_id") or "")
    if not job_id or not project_id or not take_id:
        return False
    job_kind = str(job.get("job_kind") or "video_take")
    if job_kind == "video_upscale":
        spec = _get_take_upscale_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
        if str(spec.get("lastJobId") or "") != job_id:
            return False
        _set_take_upscale_state(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            status="CANCELED",
            job_id=job_id,
            attempt=int(spec.get("upscaleAttempt") or 0) or None,
            error="Worker ausente; estado reconciliado pelo Studio.",
        )
        return True
    if job_kind == "video_take":
        spec = _get_take_generation_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
        if str(spec.get("lastJobId") or "") != job_id:
            return False
        _set_take_generation_state(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            status="ERROR",
            job_id=job_id,
            error="Worker ausente; estado reconciliado pelo Studio.",
        )
        return True
    return False


@app.post("/api/generative/job/{job_id}/cancel", status_code=202)
async def generative_job_cancel(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _get_gen_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"erro": "Job nao encontrado"})
    status = str(job.get("status") or "")
    if status in {"done", "error", "canceled"}:
        return JSONResponse(status_code=409, content={"erro": "Este trabalho ja terminou."})
    with _ACTIVE_GEN_JOBS_LOCK:
        active = _ACTIVE_GEN_JOBS.get(job_id)
        cancel_event = active.get("cancel_event") if active else None
        process = active.get("process") if active else None
    if cancel_event is None:
        _set_gen_job(job_id, status="canceled", message="Cancelado; processo nao estava mais ativo.")
        try:
            reconciled = _reconcile_inactive_project_job(job)
        except Exception as exc:
            logging.error("Falha ao reconciliar job inativo %s: %s", job_id, exc, exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "job_id": job_id,
                    "status": "canceled",
                    "erro": "Job cancelado, mas o estado do take nao pode ser reconciliado.",
                },
            )
        return {
            "ok": True,
            "job_id": job_id,
            "status": "canceled",
            "take_reconciled": reconciled,
        }
    cancel_event.set()
    if str(job.get("job_kind") or "") == "video_take":
        _wake_video_take_queue()
    _set_gen_job(job_id, status="canceling", message="Solicitando cancelamento.")
    if process is not None and process.poll() is None:
        try:
            process.terminate()
        except OSError:
            pass
    prompt_id = str(job.get("prompt_id") or "")
    if prompt_id and not prompt_id.startswith(("mova:", "levo2:")):
        threading.Thread(
            target=_cancel_comfy_prompt,
            args=(prompt_id,),
            daemon=True,
            name=f"studio-cancel-{job_id[:8]}",
        ).start()
    return {"ok": True, "job_id": job_id, "status": "canceling"}


@app.post("/api/generative/job/{job_id}/retry", status_code=202)
async def generative_job_retry(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _get_gen_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"erro": "Job nao encontrado"})
    status = str(job.get("status") or "")
    if status not in {"done", "error", "interrupted", "canceled"}:
        return JSONResponse(status_code=409, content={"erro": "Aguarde o trabalho atual terminar ou cancele-o."})
    request_spec = job.get("request_spec")
    if not isinstance(request_spec, dict):
        return JSONResponse(
            status_code=409,
            content={"erro": "Este trabalho antigo nao possui parametros suficientes para repetir."},
        )
    if str(request_spec.get("mode") or "").lower() == "video" and _video_generation_paused():
        return JSONResponse(status_code=423, content={"erro": _video_pause_message()})
    try:
        input_files = job.get("input_files") if isinstance(job.get("input_files"), dict) else {}
        base_bytes, base_name = _load_job_input(input_files.get("base"))
        end_bytes, end_name = _load_job_input(input_files.get("end"))
        new_job_id = _start_generative_job(
            request_spec,
            base_bytes=base_bytes,
            base_name=base_name,
            end_bytes=end_bytes,
            end_name=end_name,
            source_job_id=job_id,
        )
        _set_gen_job(job_id, last_retry_job_id=new_job_id)
        return {"ok": True, "job_id": new_job_id, "source_job_id": job_id}
    except (ValueError, FileNotFoundError) as exc:
        return JSONResponse(status_code=409, content={"erro": str(exc)})


def _video_projects_error(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    error: Dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


async def _video_projects_json_body(request: Request) -> Dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise ValueError("Corpo JSON invalido.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Corpo JSON deve ser um objeto.")
    return payload


@app.get("/api/video-projects")
async def video_projects_list(
    request: Request,
    page: int = 1,
    pageSize: int = 20,
    status: str = "",
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return await run_in_threadpool(_list_video_projects, VIDEO_PROJECTS_ROOT, page=page, page_size=pageSize, status=status)
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video projects list")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao listar projetos.")


@app.get("/api/video-projects/director-requests")
async def video_director_requests_list(
    request: Request,
    page: int = 1,
    pageSize: int = 50,
    status: str = "",
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return _list_director_requests(VIDEO_PROJECTS_ROOT, page=page, page_size=pageSize, status=status)
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video director requests list")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao listar pedidos para a direcao.")


def _pending_anchor_take_ids(project_id: str) -> list[str]:
    takes = _list_video_takes(VIDEO_PROJECTS_ROOT, project_id, page=1, page_size=100).get("data", [])
    pending: list[str] = []
    for take in takes:
        director_request = take.get("directorRequest") if isinstance(take, dict) else None
        if (
            isinstance(director_request, dict)
            and str(director_request.get("category") or "").upper() == "ANCHOR"
            and str(director_request.get("status") or "").upper() in {"PENDING", "IN_PROGRESS"}
        ):
            take_id = str(take.get("takeId") or "").strip()
            if take_id:
                pending.append(take_id)
    return pending


@app.get("/api/video-projects/{project_id}/anchor-jobs")
async def video_anchor_executor_status(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        status = _ANCHOR_EXECUTOR_MANAGER.status(project_id)
        project = _get_video_project(VIDEO_PROJECTS_ROOT, project_id)
        policy = (
            project.get("anchorGeneration")
            if isinstance(project.get("anchorGeneration"), dict)
            else {}
        )
        return {
            "ok": True,
            **status,
            "pendingTakeIds": _pending_anchor_take_ids(project_id),
            "anchorGeneration": policy,
        }
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto ou executor de fotos-base nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("anchor executor status for %s", project_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao consultar o executor de fotos-base.")


def _start_video_anchor_executor(project_id: str, requested: list[str] | None):
    project = _get_video_project(VIDEO_PROJECTS_ROOT, project_id)
    internet_publication.require_direction(VIDEO_PROJECTS_ROOT, project_id)
    policy = (
        project.get("anchorGeneration")
        if isinstance(project.get("anchorGeneration"), dict)
        else {}
    )
    if policy.get("localExecutorAllowed") is False:
        return _video_projects_error(
            409,
            "LOCAL_ANCHOR_EXECUTOR_FORBIDDEN",
            "O executor local de fotos-base esta bloqueado neste projeto; use Codex built-in imagegen.",
            {"requiredGenerator": policy.get("requiredGenerator") or "Codex built-in imagegen"},
        )

    active = _pending_anchor_take_ids(project_id)
    pilot_ids = [
        str(item).strip()
        for item in policy.get("pilotTakeIds", [])
        if str(item).strip()
    ] if isinstance(policy.get("pilotTakeIds"), list) else []
    pilot_gate_active = bool(
        policy.get("pilotFirst")
        and policy.get("remainingBatchRequiresPilotHumanApproval")
        and pilot_ids
    )
    if pilot_gate_active:
        take_views = _list_video_takes(
            VIDEO_PROJECTS_ROOT, project_id, page=1, page_size=100
        ).get("data", [])
        by_id = {
            str(item.get("takeId") or "").upper(): item
            for item in take_views
            if isinstance(item, dict)
        }
        pilots_approved = all(
            bool((by_id.get(take_id.upper()) or {}).get("keyframeApproved"))
            for take_id in pilot_ids
        )
        if not pilots_approved:
            pilot_keys = {take_id.upper() for take_id in pilot_ids}
            active = [take_id for take_id in active if take_id.upper() in pilot_keys]
    if requested:
        active_by_upper = {take_id.upper(): take_id for take_id in active}
        missing = [take_id for take_id in requested if take_id.upper() not in active_by_upper]
        if missing:
            if pilot_gate_active:
                return _video_projects_error(
                    409,
                    "ANCHOR_PILOT_GATE",
                    "A rodada completa esta bloqueada ate a aprovacao humana dos pilotos.",
                    {"pilotTakeIds": pilot_ids, "blockedTakeIds": missing},
                )
            return _video_projects_error(
                409,
                "ANCHOR_NOT_PENDING",
                f"Pedido ANCHOR nao esta pendente para: {', '.join(missing)}.",
            )
        selected = [active_by_upper[take_id.upper()] for take_id in requested]
    else:
        selected = active
    if not selected:
        return _video_projects_error(409, "NO_PENDING_ANCHORS", "Nao ha fotos-base pendentes para executar.")

    result = _ANCHOR_EXECUTOR_MANAGER.start(project_id, take_ids=selected)
    return {
        "ok": True,
        **result,
        "pendingTakeIds": selected,
    }


@app.post("/api/video-projects/{project_id}/anchor-jobs", status_code=202)
async def video_anchor_executor_start(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"takeIds"}
        if unknown:
            raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
        requested = payload.get("takeIds")
        if requested is not None and (
            not isinstance(requested, list) or not all(isinstance(item, str) for item in requested)
        ):
            raise ValueError("takeIds deve ser uma lista de strings.")

        return await run_in_threadpool(_start_video_anchor_executor, project_id, requested)
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto ou executor de fotos-base nao encontrado.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("anchor executor start for %s", project_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao iniciar o executor de fotos-base.")


@app.post("/api/video-projects", status_code=201)
async def video_projects_create(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _internet_publication_body(request)
        unknown = set(payload) - {"projectId", "name", "objective", "durationSeconds", "distributionMode", "platforms"}
        if unknown:
            raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
        return _create_video_project(
            VIDEO_PROJECTS_ROOT,
            project_id=str(payload.get("projectId") or ""),
            name=str(payload.get("name") or ""),
            objective=str(payload.get("objective") or ""),
            duration_seconds=payload.get("durationSeconds", 60),
            distribution_mode=payload.get("distributionMode", "auto"),
            platforms=payload.get("platforms"),
        )
    except FileExistsError:
        return _video_projects_error(409, "PROJECT_EXISTS", "Projeto ja existe.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video project create")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao criar projeto.")


async def _internet_publication_body(request: Request) -> Dict[str, Any]:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise ValueError("Use Content-Type application/json.")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > internet_publication.BODY_LIMIT:
            raise ValueError("O pedido excede o limite de 64 KiB.")
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Corpo JSON inválido.") from exc
    if not isinstance(payload, dict):
        raise ValueError("O pedido deve ser um objeto JSON.")
    return payload


@app.post("/api/video-projects/briefing-preview")
async def video_internet_briefing_preview(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _internet_publication_body(request)
        if set(payload) - {"brief", "distributionMode", "platforms"}:
            raise ValueError("Campos não permitidos no briefing.")
        intent = internet_publication.detect_intent(
            payload.get("brief", ""), mode=payload.get("distributionMode", "auto"),
            platforms=payload.get("platforms"),
        )
        return {"intent": internet_publication.intent_view(intent), "reason": intent["reason"],
                "checklist": internet_publication.CHECKLIST if intent["mode"] == "internet" else [],
                "autoGenerate": False, "autoPublish": False}
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))


@app.get("/api/video-projects/{project_id}/internet-publication")
async def video_internet_publication_get(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(internet_publication.get_publication, VIDEO_PROJECTS_ROOT, project_id)
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto não encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))


@app.post("/api/video-projects/{project_id}/internet-publication/{action}")
async def video_internet_publication_update(request: Request, project_id: str, action: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    operations = {
        "plan": internet_publication.save_plan,
        "packages": internet_publication.create_package,
        "measurements": internet_publication.record_measurement,
    }
    operation = operations.get(action)
    if operation is None:
        return _video_projects_error(404, "ACTION_NOT_FOUND", "Ação não encontrada.")
    try:
        payload = await _internet_publication_body(request)
        # File/CPU work runs outside the event loop; no Studio/GPU job is created.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(operation, VIDEO_PROJECTS_ROOT, project_id, payload)
    except internet_publication.PublicationConflictError as exc:
        return _video_projects_error(409, "REVISION_CONFLICT", str(exc))
    except FileNotFoundError:
        return _video_projects_error(404, "SOURCE_NOT_FOUND", "Projeto ou fonte não encontrado.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("internet publication preparation")
        return _video_projects_error(500, "PREPARATION_ERROR", "A preparação falhou. Fontes e aprovações foram preservadas.")


@app.get("/api/video-projects/{project_id}/internet-publication/packages/{package_id}/download")
async def video_internet_publication_download(request: Request, project_id: str, package_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        from starlette.concurrency import run_in_threadpool
        path = await run_in_threadpool(internet_publication.package_download, VIDEO_PROJECTS_ROOT, project_id, package_id)
        return FileResponse(path, filename=f"{project_id}_{package_id[:8]}_publicacao.zip",
                            media_type="application/zip", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})
    except FileNotFoundError:
        return _video_projects_error(404, "PACKAGE_NOT_FOUND", "Pacote não encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))


@app.post("/api/video-projects/gauntlet-pilot", status_code=201)
async def video_gauntlet_pilot_create(request: Request):
    """Create the bounded three-take Gauntlet pilot without starting GPU work."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        allowed = {"projectId", "name", "objective"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"Campos não permitidos: {', '.join(sorted(unknown))}")
        return _create_gauntlet_pilot(
            VIDEO_PROJECTS_ROOT,
            project_id=str(payload.get("projectId") or "gauntlet_pilot_3_takes"),
            name=str(payload.get("name") or "Piloto Gauntlet — 3 takes"),
            objective=str(
                payload.get("objective")
                or "Validar um ciclo controlado de geração, crítica independente e revisão humana para três takes curtos."
            ),
        )
    except FileExistsError:
        return _video_projects_error(409, "PROJECT_EXISTS", "O piloto Gauntlet já existe.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video gauntlet pilot create")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao criar o piloto Gauntlet.")


@app.get("/api/video-projects/{project_id}/gauntlet")
async def video_gauntlet_get(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return _get_gauntlet_pilot(VIDEO_PROJECTS_ROOT, project_id)
    except FileNotFoundError:
        return _video_projects_error(404, "GAUNTLET_PILOT_NOT_FOUND", "Piloto Gauntlet não encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video gauntlet get for %s", project_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao consultar o piloto Gauntlet.")


@app.post("/api/video-projects/{project_id}/gauntlet/repair-anchor-contract")
async def video_gauntlet_repair_anchor_contract(request: Request, project_id: str):
    """Repair legacy empty-source anchor requests without granting approval."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        if payload:
            raise ValueError("O reparo Gauntlet não aceita campos no corpo da requisição.")
        return _repair_gauntlet_anchor_contract(VIDEO_PROJECTS_ROOT, project_id)
    except FileNotFoundError:
        return _video_projects_error(404, "GAUNTLET_PILOT_NOT_FOUND", "Piloto Gauntlet não encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video gauntlet anchor repair for %s", project_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao reparar a geração de fotos do piloto.")


@app.post("/api/video-projects/{project_id}/takes/{take_id}/gauntlet/reference")
async def video_gauntlet_reference(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        if set(payload) != {"referenceFile"}:
            raise ValueError("O registro de referência aceita somente referenceFile.")
        return _register_gauntlet_reference(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            str(payload.get("referenceFile") or ""),
        )
    except FileNotFoundError:
        return _video_projects_error(404, "REFERENCE_NOT_FOUND", "Referência não encontrada em refs/ do piloto.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video gauntlet reference for %s/%s", project_id, take_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao registrar a referência Gauntlet.")


@app.get("/api/video-projects/{project_id}/takes/{take_id}/gauntlet/brief")
async def video_gauntlet_brief(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return _gauntlet_critic_brief(VIDEO_PROJECTS_ROOT, project_id, take_id)
    except FileNotFoundError as exc:
        code = str(exc) or "artifact"
        return _video_projects_error(409, "GAUNTLET_ARTIFACT_MISSING", "Referência ou candidato não está pronto para crítica.", {"artifact": code})
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video gauntlet brief for %s/%s", project_id, take_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao montar o briefing Gauntlet.")


@app.post("/api/video-projects/{project_id}/takes/{take_id}/gauntlet/verdict", status_code=201)
async def video_gauntlet_verdict(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        return _submit_gauntlet_verdict(VIDEO_PROJECTS_ROOT, project_id, take_id, payload)
    except FileNotFoundError as exc:
        code = str(exc) or "artifact"
        return _video_projects_error(409, "GAUNTLET_ARTIFACT_MISSING", "Referência ou candidato não está pronto para crítica.", {"artifact": code})
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video gauntlet verdict for %s/%s", project_id, take_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao registrar o veredito Gauntlet.")


@app.get("/api/video-projects/{project_id}")
async def video_project_get(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return await run_in_threadpool(_get_video_project, VIDEO_PROJECTS_ROOT, project_id)
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video project get")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao abrir projeto.")


@app.get("/api/video-projects/{project_id}/takes/{take_id}/h3-workflow")
async def video_take_h3_workflow(request: Request, project_id: str, take_id: str):
    """Run the real take preflight without queuing inference and explain its gates."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        spec = _get_take_generation_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
        return _h3_take_readiness(spec)
    except FileNotFoundError:
        return _video_projects_error(404, "TAKE_NOT_FOUND", "Projeto ou take nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(
            422,
            "H3_WORKFLOW_BLOCKED",
            str(exc),
            {"next": "repair_contract", "gpuQueued": False},
        )
    except Exception:
        logging.exception("H3 workflow preflight for %s/%s", project_id, take_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao auditar o workflow H3.")


def _start_take_video_sound_job(
    project_id: str,
    take_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    allowed = {"providerId", "prompt", "negativePrompt", "durationSeconds", "seed"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Campos video-to-sound nao permitidos: {', '.join(sorted(unknown))}")
    take_status = _get_take_status(VIDEO_PROJECTS_ROOT, project_id, take_id)
    if take_status not in {"APPROVED", "FINAL"}:
        raise ValueError("Som pelo video exige take visual aprovado.")
    provider_id = str(payload.get("providerId") or "").strip().lower()
    if not provider_id:
        provider_id = str(_VIDEO_SOUND_REGISTRY.status().get("defaultProviderId") or "")
    provider = _VIDEO_SOUND_REGISTRY.get(provider_id)
    provider_status = provider.status()
    if not provider_status.get("configured"):
        raise VideoSoundError(str(provider_status.get("message") or "Provider indisponivel."))
    source_video = _get_take_preview_path(VIDEO_PROJECTS_ROOT, project_id, take_id).resolve()
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve()
    if project_dir.parent != VIDEO_PROJECTS_ROOT.resolve() or not source_video.is_relative_to(project_dir):
        raise ValueError("Video ativo deve permanecer dentro do projeto.")
    prompt = str(payload.get("prompt") or "").strip()
    negative_prompt = str(payload.get("negativePrompt") or "").strip()
    if len(negative_prompt) > 4000:
        raise ValueError("O campo Evitar aceita no maximo 4000 caracteres.")
    requested_duration = float(payload.get("durationSeconds") or 0)
    source_duration = _probe_video_sound_duration(source_video)
    duration = requested_duration or min(source_duration, float(provider.max_duration_seconds))
    duration = min(duration, source_duration, 15.0)
    seed = int(payload.get("seed") if payload.get("seed") is not None else -1)
    job_id = uuid.uuid4().hex
    output_dir = project_dir / "audio" / "video_sound" / take_id / job_id
    request = VideoSoundRequest(
        job_id=job_id,
        source_video=source_video,
        output_dir=output_dir,
        prompt=prompt,
        negative_prompt=negative_prompt,
        duration_seconds=duration,
        seed=seed,
    )
    provider.validate_request(request)
    cancel_event = threading.Event()
    _GEN_JOB_STORE.update(
        job_id,
        mode="video_sound",
        job_kind="video_sound",
        status="queued",
        progress=1,
        message="Som pelo video enfileirado.",
        project_id=project_id,
        take_id=take_id,
        provider_id=provider.provider_id,
        model=provider.model,
        source_video=str(source_video),
        duration_seconds=duration,
        prompt=prompt,
        human_review_required=True,
        auto_attach=False,
        worker_pid=os.getpid(),
    )
    with _ACTIVE_GEN_JOBS_LOCK:
        _ACTIVE_GEN_JOBS[job_id] = {"cancel_event": cancel_event}

    def progress(value: int, message: str) -> None:
        _GPU_LEASE_REGISTRY.heartbeat(job_id)
        _GEN_JOB_STORE.update(
            job_id,
            status="running",
            progress=max(1, min(99, int(value))),
            message=str(message),
            heartbeat_at=_t.time(),
            worker_pid=os.getpid(),
        )

    def worker() -> None:
        lease_acquired = False
        try:
            _GEN_JOB_STORE.update(
                job_id,
                status="queued",
                progress=3,
                message="Validando fila GPU e provider video-to-sound.",
            )
            _wait_for_gpu_lease(
                job_id,
                operation="video_sound",
                project_id=project_id,
                take_id=take_id,
                cancel_event=cancel_event,
            )
            lease_acquired = True
            progress(4, "GPU reservada cooperativamente para o Foley.")
            result = provider.generate(request, progress, cancel_event)
            if cancel_event.is_set():
                raise VideoSoundCancelled("Geracao cancelada pelo proprietario.")
            take_view = _register_take_audio_candidate(
                VIDEO_PROJECTS_ROOT,
                project_id,
                take_id,
                result.audio_path,
                provider_id=result.provider_id,
                model=result.model,
                source_video_sha256=result.source_video_sha256,
                qc=result.qc,
                generation=result.generation,
            )
            _GEN_JOB_STORE.update(
                job_id,
                status="done",
                progress=100,
                message="Candidato pronto; escuta humana obrigatoria.",
                result={
                    "providerId": result.provider_id,
                    "model": result.model,
                    "audioFile": result.audio_path.name,
                    "candidateUrl": (
                        f"/api/video-projects/{project_id}/takes/{take_id}/audio-candidate"
                    ),
                    "qc": result.qc,
                    "take": take_view,
                    "status": "PENDING_HUMAN_REVIEW",
                },
            )
        except VideoSoundCancelled as exc:
            _GEN_JOB_STORE.update(
                job_id, status="canceled", message="Cancelado pelo proprietario.", error=str(exc)
            )
        except GenerationCancelled as exc:
            _GEN_JOB_STORE.update(
                job_id, status="canceled", message="Cancelado pelo proprietario.", error=str(exc)
            )
        except Exception as exc:
            logging.exception("video-to-sound job %s", job_id)
            _GEN_JOB_STORE.update(
                job_id, status="error", message="Falha no som pelo video.", error=str(exc)
            )
        finally:
            if lease_acquired:
                _GPU_LEASE_REGISTRY.release(job_id)
            with _ACTIVE_GEN_JOBS_LOCK:
                _ACTIVE_GEN_JOBS.pop(job_id, None)

    threading.Thread(target=worker, name=f"video-sound-{job_id[:8]}", daemon=True).start()
    return {
        "ok": True,
        "jobId": job_id,
        "status": "queued",
        "providerId": provider.provider_id,
        "model": provider.model,
        "durationSeconds": duration,
        "humanReviewRequired": True,
        "autoAttach": False,
    }


@app.get("/api/video-sound/providers")
def video_sound_providers(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return _VIDEO_SOUND_REGISTRY.status()
    except Exception:
        logging.exception("video-to-sound providers")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao consultar providers de som.")


@app.get("/api/gpu-lease")
async def gpu_lease_status(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return {"ok": True, "lease": _GPU_LEASE_REGISTRY.status()}
    except Exception:
        logging.exception("gpu lease status")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao consultar a reserva da GPU.")


@app.post(
    "/api/video-projects/{project_id}/takes/{take_id}/video-sound-jobs",
    status_code=202,
)
async def video_take_sound_job(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        return _start_take_video_sound_job(project_id, take_id, payload)
    except FileNotFoundError:
        return _video_projects_error(404, "TAKE_NOT_FOUND", "Take ou video aprovado nao encontrado.")
    except (ValueError, VideoSoundError) as exc:
        return _video_projects_error(422, "VIDEO_SOUND_VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video-to-sound start")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao iniciar som pelo video.")


@app.get("/api/video-sound/jobs/{job_id}")
async def video_sound_job_status(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "video_sound":
        return _video_projects_error(404, "VIDEO_SOUND_JOB_NOT_FOUND", "Job de som nao encontrado.")
    return job


@app.post("/api/video-sound/jobs/{job_id}/cancel", status_code=202)
async def video_sound_job_cancel(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "video_sound":
        return _video_projects_error(404, "VIDEO_SOUND_JOB_NOT_FOUND", "Job de som nao encontrado.")
    if job.get("status") in {"done", "error", "canceled", "interrupted"}:
        return job
    with _ACTIVE_GEN_JOBS_LOCK:
        active = _ACTIVE_GEN_JOBS.get(job_id)
        if active:
            active["cancel_event"].set()
    return _GEN_JOB_STORE.update(
        job_id, status="canceling", message="Cancelamento solicitado pelo proprietario."
    )


def _music_reinstrument_error(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return _video_projects_error(status_code, code, message, details)


def _music_reinstrument_public_job(job: Dict[str, Any]) -> Dict[str, Any]:
    public = {
        key: value
        for key, value in job.items()
        if key not in {"job_dir", "source_path", "worker_pid"}
    }
    result = dict(public.get("result") or {})
    artifacts = []
    for raw in result.get("artifacts") or []:
        artifact = dict(raw)
        artifact.pop("relativePath", None)
        key = str(artifact.get("key") or "")
        if key:
            artifact["url"] = f"/api/music-reinstrument/jobs/{job['job_id']}/artifacts/{key}"
        artifacts.append(artifact)
    if result:
        result["artifacts"] = artifacts
        public["result"] = result
    public["humanReviewRequired"] = True
    public["autoApprove"] = False
    return public


def _max_music_reinstrument_upload_bytes() -> int:
    try:
        megabytes = int(os.environ.get("STUDIO_REINSTRUMENT_MAX_UPLOAD_MB", "512"))
    except (TypeError, ValueError):
        megabytes = 512
    return max(8, min(2048, megabytes)) * 1024 * 1024


async def _save_music_reinstrument_upload(upload: UploadFile, target: Path) -> int:
    limit = _max_music_reinstrument_upload_bytes()
    target.parent.mkdir(parents=True, exist_ok=False)
    total = 0
    try:
        with target.open("xb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise MediaUploadTooLarge(
                        f"O audio excede o limite de {limit // (1024 * 1024)} MB."
                    )
                handle.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        try:
            await upload.close()
        except Exception:
            pass
    if total < 1024:
        target.unlink(missing_ok=True)
        raise ValueError("O arquivo de audio esta vazio ou incompleto.")
    return total


async def _save_music_score_upload(upload: UploadFile, target: Path) -> int:
    limit = 32 * 1024 * 1024
    target.parent.mkdir(parents=True, exist_ok=False)
    total = 0
    try:
        with target.open("xb") as handle:
            while True:
                chunk = await upload.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise MediaUploadTooLarge("A partitura excede o limite de 32 MB.")
                handle.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        try:
            await upload.close()
        except Exception:
            pass
    if total < 20:
        target.unlink(missing_ok=True)
        raise ValueError("O arquivo de partitura esta vazio ou incompleto.")
    return total


def _start_music_reinstrument_worker(
    *,
    job_id: str,
    job_dir: Path,
    source_path: Path,
    original_name: str,
    preset: str,
    instruments: tuple[str, ...],
    intensity: float,
    keep_vocals: bool,
    orchestration_prompt: str,
    engine: str,
    candidate_count: int,
    cover_strength: float,
    supplied_score_path: Path | None = None,
    qwen_enabled: bool = True,
    supplied_vocal_path: Path | None = None,
) -> None:
    cancel_event = threading.Event()
    with _ACTIVE_MUSIC_REINSTRUMENT_LOCK:
        _ACTIVE_MUSIC_REINSTRUMENT_JOBS[job_id] = {"cancel_event": cancel_event}

    def update(progress: int, message: str) -> None:
        _set_gen_job(
            job_id,
            status="running",
            progress=max(1, min(99, int(progress))),
            message=message,
        )

    def worker() -> None:
        lease_acquired = False
        try:
            qwen_plan = None
            if qwen_enabled:
                from music_qwen import plan_reinstrumentation
                from music_ai_audio import sha256_file
                from music_reinstrument import probe_audio as probe_music_source
                _wait_for_gpu_lease(job_id, operation="qwen_music_orchestration",
                    project_id="music_studio", take_id=job_id, cancel_event=cancel_event)
                lease_acquired = True
                _prepare_comfy_gpu_for_mova(job_id=job_id, cancel_event=cancel_event, wait_for_queue=True)
                observed = probe_music_source(source_path, shutil.which("ffprobe") or "ffprobe")
                qwen_plan = plan_reinstrumentation(prompt=orchestration_prompt,
                    duration=float(observed['durationSeconds']), instruments=instruments, preset=preset,
                    source_sha256=sha256_file(source_path), cancel_event=cancel_event, progress_cb=update)
                (job_dir / 'qwen_production_plan.json').write_text(
                    json.dumps(qwen_plan, ensure_ascii=False, indent=2), encoding='utf-8')
                _GEN_JOB_STORE.update(job_id, qwen_plan=qwen_plan)
                # The text model has been unloaded. CPU score/transcription work
                # must not hold the GPU for the rest of a long production.
                _GPU_LEASE_REGISTRY.release(job_id)
                lease_acquired = False
            if engine == _SCORE_FIRST_ENGINE_ID:
                transcription_device = (
                    "cpu" if supplied_score_path is not None else _choose_score_first_device()
                )
                if transcription_device == "cuda":
                    update(2, "Aguardando reserva cooperativa da GPU para o MuScriptor Large.")
                    _wait_for_gpu_lease(
                        job_id,
                        operation="music_score_first_muscriptor",
                        project_id="music_studio",
                        take_id=job_id,
                        cancel_event=cancel_event,
                    )
                    lease_acquired = True
                    update(3, "GPU reservada sem descarregar nem interromper o ComfyUI.")
                result = _run_score_transcription(
                    _ScoreTranscriptionRequest(
                        source_path=source_path,
                        output_dir=job_dir,
                        original_name=original_name,
                        preset=preset,
                        instruments=instruments,
                        intensity=intensity,
                        keep_vocals=keep_vocals,
                        orchestration_prompt=orchestration_prompt,
                        transcription_device=transcription_device,
                        supplied_score_path=supplied_score_path,
                        qwen_plan=qwen_plan,
                        supplied_vocal_path=supplied_vocal_path,
                    ),
                    progress=update,
                    cancel_event=cancel_event,
                    ffmpeg=get_ffmpeg(),
                    ffprobe=shutil.which("ffprobe") or "ffprobe",
                )
            elif engine == "ace_step_xl":
                update(2, "Aguardando uma reserva cooperativa da RTX 5090.")
                _wait_for_gpu_lease(
                    job_id,
                    operation="music_ai_ace_step_xl",
                    project_id="music_studio",
                    take_id=job_id,
                    cancel_event=cancel_event,
                )
                lease_acquired = True
                update(3, "Fila livre; devolvendo apenas a VRAM ociosa do ComfyUI.")
                _prepare_comfy_gpu_for_mova(
                    job_id=job_id,
                    cancel_event=cancel_event,
                    wait_for_queue=True,
                )
                result = _run_music_ai_production(
                    _MusicAiProductionRequest(
                        source_path=source_path,
                        output_dir=job_dir,
                        original_name=original_name,
                        preset=preset,
                        instruments=instruments,
                        intensity=intensity,
                        keep_vocals=keep_vocals,
                        orchestration_prompt=orchestration_prompt,
                        candidate_count=candidate_count,
                        cover_strength=cover_strength,
                        qwen_plan=qwen_plan,
                    ),
                    progress=update,
                    cancel_event=cancel_event,
                    ffmpeg=get_ffmpeg(),
                    ffprobe=shutil.which("ffprobe") or "ffprobe",
                )
            elif engine == "stem_producer_v2":
                update(2, "Aguardando uma reserva cooperativa da RTX 5090 para separar os stems.")
                _wait_for_gpu_lease(
                    job_id,
                    operation="music_stem_producer_v2",
                    project_id="music_studio",
                    take_id=job_id,
                    cancel_event=cancel_event,
                )
                lease_acquired = True
                update(3, "Fila livre; preparando a GPU para a separacao dos instrumentos.")
                _prepare_comfy_gpu_for_mova(
                    job_id=job_id,
                    cancel_event=cancel_event,
                    wait_for_queue=True,
                )
                result = _run_music_reinstrumentation(
                    _MusicReinstrumentRequest(
                        source_path=source_path,
                        output_dir=job_dir,
                        original_name=original_name,
                        preset=preset,
                        instruments=instruments,
                        intensity=intensity,
                        keep_vocals=keep_vocals,
                        orchestration_prompt=orchestration_prompt,
                        arranger_version="v2",
                        demucs_device="cuda",
                        qwen_plan=qwen_plan,
                    ),
                    progress=update,
                    cancel_event=cancel_event,
                    ffmpeg=get_ffmpeg(),
                    ffprobe=shutil.which("ffprobe") or "ffprobe",
                    demucs_python=sys.executable,
                )
            else:
                result = _run_music_reinstrumentation(
                    _MusicReinstrumentRequest(
                        source_path=source_path,
                        output_dir=job_dir,
                        original_name=original_name,
                        preset=preset,
                        instruments=instruments,
                        intensity=intensity,
                        keep_vocals=keep_vocals,
                        orchestration_prompt=orchestration_prompt,
                        arranger_version="v1",
                        demucs_device="cpu",
                        qwen_plan=qwen_plan,
                    ),
                    progress=update,
                    cancel_event=cancel_event,
                    ffmpeg=get_ffmpeg(),
                    ffprobe=shutil.which("ffprobe") or "ffprobe",
                    demucs_python=sys.executable,
                )
            if engine == _SCORE_FIRST_ENGINE_ID:
                internal_pass = bool(result.get("technicalPass"))
            elif engine == "ace_step_xl":
                internal_pass = result.get("recommendedCandidate") is not None
            else:
                internal_pass = bool(
                    (result.get("qc") or {}).get("technicalPass")
                    and (
                        bool(result.get("stemQcPass"))
                        if engine == "stem_producer_v2"
                        else True
                    )
                    and (
                        bool(result.get("finalNeuralQcPass"))
                        if engine == "stem_producer_v2"
                        else True
                    )
                    and (
                        bool(result.get("identityQcPass"))
                        if engine == "stem_producer_v2"
                        else True
                    )
                )
            if engine == _SCORE_FIRST_ENGINE_ID:
                message = (
                    "Partitura candidata e prova A/B prontas; o arranjo segue bloqueado ate sua decisao."
                    if internal_pass
                    else "Partitura preservada, mas bloqueada pelo gate interno."
                )
                review_status = (
                    "PENDING_SCORE_REVIEW" if internal_pass else "INTERNAL_QC_REJECTED"
                )
                library_visible = False
            elif engine == "ace_step_xl":
                message = (
                    "Lote neural classificado; ouca cada candidato antes de aprovar."
                    if internal_pass
                    else "Lote preservado, mas reprovado pelo gate interno de mix; nenhum candidato foi recomendado."
                )
                review_status = (
                    "PENDING_HUMAN_REVIEW" if internal_pass else "INTERNAL_QC_REJECTED"
                )
                library_visible = bool(internal_pass)
            elif engine == "stem_producer_v2":
                message = (
                    "Candidata do Maestro de Identidade v4 validada; ouca o master e cada pista antes de aprovar."
                    if internal_pass
                    else "Candidata preservada, mas bloqueada pelos gates de identidade e coordenacao do maestro."
                )
                review_status = (
                    "PENDING_HUMAN_REVIEW" if internal_pass else "INTERNAL_QC_REJECTED"
                )
                library_visible = bool(internal_pass)
            else:
                message = "Candidato legado pronto; ouca antes de aprovar."
                review_status = (
                    "PENDING_HUMAN_REVIEW" if internal_pass else "INTERNAL_QC_REJECTED"
                )
                library_visible = bool(internal_pass)
            _GEN_JOB_STORE.update(
                job_id,
                status="done",
                progress=100,
                message=message,
                result=result,
                review_status=review_status,
                library_visible=library_visible,
            )
        except (_MusicReinstrumentCancelled, _MusicAiProductionCancelled, GenerationCancelled) as exc:
            _GEN_JOB_STORE.update(
                job_id,
                status="canceled",
                message=str(exc),
                review_status="NOT_REVIEWED",
                library_visible=False,
            )
        except Exception as exc:
            logging.exception("music reinstrumentation failed for %s", job_id)
            _GEN_JOB_STORE.update(
                job_id,
                status="error",
                progress=0,
                message="A reinstrumentacao falhou; o original foi preservado.",
                error=str(exc),
                review_status="NOT_REVIEWED",
                library_visible=False,
            )
        finally:
            if lease_acquired:
                _GPU_LEASE_REGISTRY.release(job_id)
            with _ACTIVE_MUSIC_REINSTRUMENT_LOCK:
                _ACTIVE_MUSIC_REINSTRUMENT_JOBS.pop(job_id, None)

    threading.Thread(
        target=worker,
        name=f"music-reinstrument-{job_id[:8]}",
        daemon=True,
    ).start()


def _start_score_first_orchestration_worker(
    *,
    job_id: str,
    score_path: Path,
    score_sha256: str,
) -> None:
    job = _GEN_JOB_STORE.get(job_id)
    if not job:
        raise ValueError("Job de partitura nao encontrado.")
    cancel_event = threading.Event()
    with _ACTIVE_MUSIC_REINSTRUMENT_LOCK:
        _ACTIVE_MUSIC_REINSTRUMENT_JOBS[job_id] = {"cancel_event": cancel_event}

    def update(progress: int, message: str) -> None:
        _set_gen_job(
            job_id,
            status="running",
            progress=max(1, min(99, int(progress))),
            message=message,
        )

    def worker() -> None:
        try:
            phase_one = dict((job.get("result") or {}))
            result = _run_locked_score_orchestration(
                _LockedScoreOrchestrationRequest(
                    source_path=Path(str(job.get("source_path") or "")),
                    score_path=score_path,
                    output_dir=Path(str(job.get("job_dir") or "")),
                    original_name=str(job.get("original_name") or "musica.wav"),
                    score_sha256=score_sha256,
                    preset=str(job.get("preset") or "symphonic_heavy_metal"),
                    instruments=tuple(job.get("instruments") or ()),
                    intensity=float(job.get("intensity") or 0.9),
                    keep_vocals=bool(job.get("keep_vocals")),
                    orchestration_prompt=str(job.get("orchestration_prompt") or ""),
                    qwen_plan=job.get("qwen_plan"),
                    vocal_path=(Path(job["vocal_lock"]["path"]) if job.get("vocal_lock") else None),
                    vocal_sha256=str((job.get("vocal_lock") or {}).get("sha256") or ""),
                ),
                progress=update,
                cancel_event=cancel_event,
                ffmpeg=get_ffmpeg(),
                ffprobe=shutil.which("ffprobe") or "ffprobe",
            )
            combined_artifacts: Dict[str, Dict[str, Any]] = {}
            for artifact in [
                *(phase_one.get("artifacts") or []),
                *(result.get("artifacts") or []),
            ]:
                key = str(artifact.get("key") or "")
                if key:
                    combined_artifacts[key] = dict(artifact)
            result["artifacts"] = list(combined_artifacts.values())
            result["scoreReview"] = {
                "decision": "APPROVED",
                "sha256": score_sha256,
                "reviewedAt": (job.get("score_lock") or {}).get("approvedAt"),
                "reviewer": "owner",
                "transcriptionOrigin": phase_one.get("transcriptionOrigin"),
                "score": phase_one.get("score"),
            }
            internal_pass = bool((result.get("qc") or {}).get("technicalPass"))
            _GEN_JOB_STORE.update(
                job_id,
                status="done",
                progress=100,
                message=(
                    "Master da partitura bloqueada pronto; ouca cada stem antes da decisao final."
                    if internal_pass
                    else "Master preservado, mas reprovado pelos gates internos; nao sera promovido."
                ),
                result=result,
                review_status=(
                    "PENDING_HUMAN_REVIEW" if internal_pass else "INTERNAL_QC_REJECTED"
                ),
                library_visible=bool(internal_pass),
            )
        except (_MusicReinstrumentCancelled, GenerationCancelled) as exc:
            _GEN_JOB_STORE.update(
                job_id,
                status="canceled",
                message=str(exc),
                review_status="SCORE_LOCKED_CANCELED",
                library_visible=False,
            )
        except Exception as exc:
            logging.exception("score-first orchestration failed for %s", job_id)
            _GEN_JOB_STORE.update(
                job_id,
                status="error",
                progress=0,
                message="A orquestracao falhou; original e partitura aprovada foram preservados.",
                error=str(exc),
                review_status="SCORE_LOCKED_ERROR",
                library_visible=False,
            )
        finally:
            with _ACTIVE_MUSIC_REINSTRUMENT_LOCK:
                _ACTIVE_MUSIC_REINSTRUMENT_JOBS.pop(job_id, None)

    threading.Thread(
        target=worker,
        name=f"score-first-orchestration-{job_id[:8]}",
        daemon=True,
    ).start()


@app.get("/api/music-reinstrument/status")
async def music_reinstrument_status(request: Request):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        legacy = _music_reinstrument_runtime_status(
            ffmpeg=get_ffmpeg(),
            ffprobe=shutil.which("ffprobe") or "ffprobe",
            demucs_python=sys.executable,
        )
        neural = _music_ai_runtime_status()
        score_first = _score_first_runtime_status()
        return {
            **legacy,
            "defaultEngine": _SCORE_FIRST_ENGINE_ID,
            "productionContract": "pemara.qwen-music-production.v1",
            "coordinator": {"model": os.environ.get('MAESTRO_MUSIC_WRITER_MODEL',
                'qwen3.8-27b-uncensored-yarn-524k:latest'), "defaultEnabled": True,
                "localOnly": True, "planValidationRequired": True,
                "musicalIdentityMutationAllowed": False, "approvalIsAutomatic": False},
            "presets": legacy.get("presets") or {},
            "engines": {
                _SCORE_FIRST_ENGINE_ID: score_first,
                "stem_producer_v2": {
                    **legacy,
                    "engine": "stem_producer_v2",
                    "device": "cuda_separation_cpu_arrangement",
                    "gpuRequired": True,
                    "legacy": False,
                    "message": (
                        "Maestro de Identidade v4 pronto: melodia canonica protegida, apoios na mesma grade, "
                        "SoundFont MuseScore, QC por pista, identidade e forma da mix final."
                    ),
                },
                "ace_step_xl": neural,
                "legacy_midi": {**legacy, "legacy": True},
            },
        }
    except Exception:
        logging.exception("music reinstrument status")
        return _music_reinstrument_error(500, "INTERNAL_ERROR", "Falha ao consultar o runtime local.")


@app.get("/api/music-reinstrument/jobs")
async def music_reinstrument_jobs_list(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    status: str = "",
):
    if not _is_internal_request(request):
        return _public_forbidden()
    payload = _GEN_JOB_STORE.list(
        page=page,
        page_size=page_size,
        status=status,
        mode="music_reinstrument",
    )
    payload["items"] = [_music_reinstrument_public_job(job) for job in payload.get("items", [])]
    return payload


@app.post("/api/music-reinstrument/jobs", status_code=202)
async def music_reinstrument_job_start(
    request: Request,
    file: UploadFile = File(...),
    score_file: Optional[UploadFile] = File(None),
    vocal_file: Optional[UploadFile] = File(None),
    rights_confirmed: str = Form("false"),
    preset: str = Form("symphonic_heavy_metal"),
    instruments: str = Form("piano,violin,cello,guitar,bass,drums"),
    intensity: float = Form(0.9),
    keep_vocals: str = Form("false"),
    orchestration_prompt: str = Form(""),
    engine: str = Form(_SCORE_FIRST_ENGINE_ID),
    candidate_count: int = Form(3),
    cover_strength: float = Form(0.55),
    qwen_enabled: str = Form("true"),
):
    if not _is_internal_request(request):
        return _public_forbidden()
    submitted = await request.form()
    unknown = set(submitted.keys()) - {
        "file",
        "score_file",
        "vocal_file",
        "qwen_enabled",
        "rights_confirmed",
        "preset",
        "instruments",
        "intensity",
        "keep_vocals",
        "orchestration_prompt",
        "engine",
        "candidate_count",
        "cover_strength",
    }
    if unknown:
        return _music_reinstrument_error(
            422,
            "VALIDATION_ERROR",
            f"Campos de producao nao permitidos: {', '.join(sorted(unknown))}.",
        )
    if str(qwen_enabled).strip().lower() not in {'1', 'true', 'yes', 'sim', 'on', '0', 'false', 'no', 'nao', 'off'}:
        return _music_reinstrument_error(422, 'VALIDATION_ERROR', 'Escolha do Qwen precisa ser verdadeira ou falsa.')
    if str(rights_confirmed or "").strip().lower() not in {"1", "true", "yes", "sim", "on"}:
        return _music_reinstrument_error(
            422,
            "RIGHTS_CONFIRMATION_REQUIRED",
            "Confirme que voce possui os direitos ou autorizacao para adaptar este audio.",
        )
    preset_id = str(preset or "").strip()
    if preset_id not in _MUSIC_REINSTRUMENT_PRESETS:
        return _music_reinstrument_error(422, "VALIDATION_ERROR", "Preset de reinstrumentacao invalido.")
    try:
        engine_id = str(engine or "").strip().lower()
        if engine_id not in {
            _SCORE_FIRST_ENGINE_ID,
            "stem_producer_v2",
            "ace_step_xl",
            "legacy_midi",
        }:
            raise ValueError("Motor de producao musical invalido.")
        selected_instruments = _normalize_music_reinstrument_instruments(instruments.split(","))
        intensity_value = float(intensity)
        if not 0.35 <= intensity_value <= 1.0:
            raise ValueError("A intensidade deve ficar entre 0,35 e 1,0.")
        candidate_count_value = int(candidate_count)
        if engine_id == "ace_step_xl" and not 2 <= candidate_count_value <= 4:
            raise ValueError("A IA deve gerar entre 2 e 4 candidatos.")
        if engine_id != "ace_step_xl":
            candidate_count_value = 1
        cover_strength_value = float(cover_strength)
        if not 0.3 <= cover_strength_value <= 0.9:
            raise ValueError("A fidelidade estrutural deve ficar entre 0,3 e 0,9.")
        orchestration_prompt_value = (
            _sanitize_music_ai_prompt(orchestration_prompt)
            if engine_id == "ace_step_xl"
            else _sanitize_music_orchestration_prompt(orchestration_prompt)
        )
    except (TypeError, ValueError) as exc:
        return _music_reinstrument_error(422, "VALIDATION_ERROR", str(exc))
    original_name = _safe_upload_filename(file.filename or "musica.wav", "musica.wav")
    extension = Path(original_name).suffix.lower()
    if extension not in _MUSIC_REINSTRUMENT_EXTENSIONS:
        return _music_reinstrument_error(422, "UNSUPPORTED_AUDIO", "Formato de audio nao suportado.")
    score_original_name = ""
    score_extension = ""
    if score_file is not None and score_file.filename:
        score_original_name = _safe_upload_filename(score_file.filename, "partitura.mid")
        score_extension = Path(score_original_name).suffix.lower()
        if score_extension not in _SCORE_FIRST_EXTENSIONS:
            return _music_reinstrument_error(
                422,
                "UNSUPPORTED_SCORE",
                "Partitura precisa ser MIDI, MusicXML ou MXL.",
            )
        if engine_id != _SCORE_FIRST_ENGINE_ID:
            return _music_reinstrument_error(
                422,
                "VALIDATION_ERROR",
                "Partitura fornecida so pode ser usada no modo Partitura Primeiro.",
            )
    if engine_id == _SCORE_FIRST_ENGINE_ID:
        keep_vocals_requested = str(keep_vocals or "").strip().lower() in {
            "1", "true", "yes", "sim", "on"
        }
        score_runtime = _score_first_runtime_status()
        score_runtime_ready = (
            score_runtime.get("scoreImportConfigured")
            if score_file is not None and score_file.filename
            else score_runtime.get("configured")
        )
        if not score_runtime_ready:
            return _music_reinstrument_error(
                503,
                "SCORE_FIRST_RUNTIME_NOT_READY",
                str(score_runtime.get("message") or "Runtime Partitura Primeiro indisponivel."),
                {"model": score_runtime.get("model"), "needs": score_runtime.get("needs")},
            )

    job_id = uuid.uuid4().hex
    job_dir = (MUSIC_REINSTRUMENT_ROOT / job_id).resolve()
    if MUSIC_REINSTRUMENT_ROOT.resolve() not in job_dir.parents:
        return _music_reinstrument_error(500, "INVALID_JOB_PATH", "Destino do job invalido.")
    source_path = job_dir / "source" / f"original{extension}"
    try:
        upload_bytes = await _save_music_reinstrument_upload(file, source_path)
    except MediaUploadTooLarge as exc:
        return _music_reinstrument_error(413, "UPLOAD_TOO_LARGE", str(exc))
    except ValueError as exc:
        return _music_reinstrument_error(422, "INVALID_UPLOAD", str(exc))
    except Exception:
        logging.exception("music reinstrument upload")
        return _music_reinstrument_error(500, "UPLOAD_FAILED", "Falha ao preservar o audio enviado.")

    supplied_score_path: Path | None = None
    score_upload_bytes = 0
    if score_file is not None and score_file.filename:
        supplied_score_path = job_dir / "source_score" / f"supplied{score_extension}"
        try:
            score_upload_bytes = await _save_music_score_upload(score_file, supplied_score_path)
        except MediaUploadTooLarge as exc:
            return _music_reinstrument_error(413, "SCORE_TOO_LARGE", str(exc))
        except ValueError as exc:
            return _music_reinstrument_error(422, "INVALID_SCORE", str(exc))
        except Exception:
            logging.exception("music score upload")
            return _music_reinstrument_error(
                500, "SCORE_UPLOAD_FAILED", "Falha ao preservar a partitura enviada."
            )

    source_probe: Dict[str, Any] = {}
    supplied_vocal_path = None
    if vocal_file is not None and vocal_file.filename:
        vocal_extension = Path(vocal_file.filename).suffix.lower()
        if (engine_id != _SCORE_FIRST_ENGINE_ID or vocal_extension not in _MUSIC_REINSTRUMENT_EXTENSIONS
                or str(keep_vocals).lower() not in {'1', 'true', 'yes', 'sim', 'on'}):
            return _music_reinstrument_error(422, 'INVALID_VOCAL_UPLOAD',
                'Stem vocal requer Partitura Primeiro, preservar voz marcado e formato de audio aceito.')
        supplied_vocal_path = job_dir / 'source_vocal' / f'supplied{vocal_extension}'
        try:
            await _save_music_reinstrument_upload(vocal_file, supplied_vocal_path)
        except (ValueError, MediaUploadTooLarge) as exc:
            return _music_reinstrument_error(422, 'INVALID_VOCAL_UPLOAD', str(exc))
    if engine_id == "ace_step_xl":
        try:
            source_probe = _probe_music_ai_audio(
                source_path,
                shutil.which("ffprobe") or "ffprobe",
            )
        except _MusicAiAudioError as exc:
            return _music_reinstrument_error(422, "INVALID_AUDIO", str(exc))

    keep_vocals_value = str(keep_vocals or "").strip().lower() in {"1", "true", "yes", "sim", "on"}
    _GEN_JOB_STORE.update(
        job_id,
        status="queued",
        progress=1,
        message="Audio preservado; aguardando o worker local.",
        mode="music_reinstrument",
        job_kind="music_reinstrument",
        job_dir=str(job_dir),
        source_path=str(source_path),
        original_name=original_name,
        upload_size_bytes=upload_bytes,
        supplied_score_path=str(supplied_score_path) if supplied_score_path else None,
        supplied_score_name=score_original_name or None,
        supplied_score_size_bytes=score_upload_bytes,
        source_probe=source_probe,
        preset=preset_id,
        instruments=list(selected_instruments),
        intensity=round(intensity_value, 2),
        keep_vocals=keep_vocals_value,
        orchestration_prompt=orchestration_prompt_value,
        engine=engine_id,
        candidate_count=candidate_count_value,
        cover_strength=round(cover_strength_value, 2),
        rights_confirmed=True,
        library_visible=False,
        review_status="PENDING_PROCESSING",
        human_review_required=True,
        auto_approve=False,
        qwen_enabled=str(qwen_enabled).strip().lower() in {'1', 'true', 'yes', 'sim', 'on'},
        supplied_vocal_path=str(supplied_vocal_path) if supplied_vocal_path else None,
    )
    _start_music_reinstrument_worker(
        job_id=job_id,
        job_dir=job_dir,
        source_path=source_path,
        original_name=original_name,
        preset=preset_id,
        instruments=selected_instruments,
        intensity=intensity_value,
        keep_vocals=keep_vocals_value,
        orchestration_prompt=orchestration_prompt_value,
        engine=engine_id,
        candidate_count=candidate_count_value,
        cover_strength=cover_strength_value,
        supplied_score_path=supplied_score_path,
        supplied_vocal_path=supplied_vocal_path,
        qwen_enabled=str(qwen_enabled).strip().lower() in {'1', 'true', 'yes', 'sim', 'on'},
    )
    return {
        "ok": True,
        "jobId": job_id,
        "status": "queued",
        "engine": engine_id,
        "candidateCount": candidate_count_value,
        "humanReviewRequired": True,
        "autoApprove": False,
    }


@app.get("/api/music-reinstrument/jobs/{job_id}")
async def music_reinstrument_job_status(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "music_reinstrument":
        return _music_reinstrument_error(404, "JOB_NOT_FOUND", "Job de reinstrumentacao nao encontrado.")
    return _music_reinstrument_public_job(job)


@app.post("/api/music-reinstrument/jobs/{job_id}/cancel", status_code=202)
async def music_reinstrument_job_cancel(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "music_reinstrument":
        return _music_reinstrument_error(404, "JOB_NOT_FOUND", "Job de reinstrumentacao nao encontrado.")
    if job.get("status") in {"done", "error", "canceled", "interrupted"}:
        return _music_reinstrument_public_job(job)
    with _ACTIVE_MUSIC_REINSTRUMENT_LOCK:
        active = _ACTIVE_MUSIC_REINSTRUMENT_JOBS.get(job_id)
        if active:
            active["cancel_event"].set()
    updated = _GEN_JOB_STORE.update(
        job_id,
        status="canceling",
        message="Cancelamento solicitado; o original sera preservado.",
    )
    return _music_reinstrument_public_job(updated)


@app.get("/api/music-reinstrument/jobs/{job_id}/artifacts/{artifact_key}")
async def music_reinstrument_artifact(request: Request, job_id: str, artifact_key: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "music_reinstrument":
        return _music_reinstrument_error(404, "JOB_NOT_FOUND", "Job de reinstrumentacao nao encontrado.")
    artifact = next(
        (
            item
            for item in (job.get("result") or {}).get("artifacts") or []
            if str(item.get("key") or "") == artifact_key
        ),
        None,
    )
    if not artifact:
        return _music_reinstrument_error(404, "ARTIFACT_NOT_FOUND", "Arquivo de saida nao encontrado.")
    try:
        path = _resolve_music_reinstrument_artifact(
            Path(str(job.get("job_dir") or "")),
            str(artifact.get("relativePath") or ""),
        )
    except FileNotFoundError:
        return _music_reinstrument_error(404, "ARTIFACT_NOT_FOUND", "Arquivo de saida nao encontrado.")
    return FileResponse(
        path,
        media_type=str(artifact.get("mediaType") or "application/octet-stream"),
        headers={"X-Filename": str(artifact.get("filename") or path.name)},
    )


@app.post("/api/music-reinstrument/jobs/{job_id}/score-review", status_code=202)
async def music_reinstrument_score_review(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "music_reinstrument":
        return _music_reinstrument_error(404, "JOB_NOT_FOUND", "Job de reinstrumentacao nao encontrado.")
    result = dict(job.get("result") or {})
    if job.get("engine") != _SCORE_FIRST_ENGINE_ID or result.get("phase") != "score_review":
        return _music_reinstrument_error(
            409, "SCORE_REVIEW_NOT_AVAILABLE", "Este job nao possui uma partitura pendente."
        )
    if job.get("status") != "done" or job.get("review_status") != "PENDING_SCORE_REVIEW":
        return _music_reinstrument_error(
            409, "SCORE_NOT_READY", "A partitura nao esta pendente de revisao."
        )
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"decision", "reason", "scoreSha256", "vocalSha256"}
        if unknown:
            raise ValueError(f"Campos de revisao nao permitidos: {', '.join(sorted(unknown))}.")
        decision = str(payload.get("decision") or "").strip().upper()
        reason = " ".join(str(payload.get("reason") or "").split())[:1000]
        submitted_hash = str(payload.get("scoreSha256") or "").strip().lower()
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValueError("Decisao deve ser APPROVED ou REJECTED.")
        if decision == "REJECTED" and len(reason) < 3:
            raise ValueError("Informe brevemente o motivo da rejeicao da partitura.")
        if len(submitted_hash) != 64:
            raise ValueError("Informe o hash exato da partitura exibida.")
        score_artifact = next(
            (
                item
                for item in result.get("artifacts") or []
                if str(item.get("key") or "") == "scoreMidi"
            ),
            None,
        )
        if not score_artifact:
            raise ValueError("Artefato de partitura nao encontrado.")
        score_path = _resolve_music_reinstrument_artifact(
            Path(str(job.get("job_dir") or "")),
            str(score_artifact.get("relativePath") or ""),
        )
        actual_hash = _sha256_music_file(score_path).lower()
        expected_hash = str(result.get("scoreSha256") or "").lower()
        artifact_hash = str(score_artifact.get("sha256") or "").lower()
        if submitted_hash != expected_hash or actual_hash != expected_hash or artifact_hash != expected_hash:
            return _music_reinstrument_error(
                409,
                "SCORE_HASH_MISMATCH",
                "A partitura exibida mudou ou o hash nao corresponde; nenhuma orquestracao foi iniciada.",
            )
        vocal_lock = None
        vocal = result.get('vocalPreservation')
        if decision == 'APPROVED' and job.get('keep_vocals'):
            if not vocal or payload.get('vocalSha256') != vocal.get('sha256'):
                raise ValueError('Escute a voz preservada e confirme seu hash junto com a partitura.')
            vocal_artifact = next((a for a in result.get('artifacts', []) if a.get('key') == 'preservedVocals'), None)
            if not vocal_artifact:
                raise ValueError('Artefato vocal preservado ausente.')
            vocal_path = _resolve_music_reinstrument_artifact(Path(job['job_dir']), vocal_artifact['relativePath'])
            if _sha256_music_file(vocal_path) != vocal['sha256']:
                raise ValueError('A voz preservada mudou depois da revisao.')
            vocal_lock = {'path': str(vocal_path), 'sha256': vocal['sha256'], 'immutable': True}
        if decision == 'APPROVED' and result.get('technicalPass') is False:
            raise ValueError('A candidata falhou nos controles tecnicos; corrija antes de aprovar.')
    except FileNotFoundError:
        return _music_reinstrument_error(
            409, "SCORE_ARTIFACT_MISSING", "A partitura preservada nao foi encontrada."
        )
    except (TypeError, ValueError) as exc:
        return _music_reinstrument_error(422, "VALIDATION_ERROR", str(exc))

    reviewed_at = _t.time()
    score_review = {
        "decision": decision,
        "reason": reason,
        "scoreSha256": actual_hash,
        "reviewedAt": reviewed_at,
        "reviewer": "owner",
        "phase": "score_review",
    }
    result["scoreReview"] = score_review
    reviews = [*(job.get("reviews") or []), score_review]
    if decision == "REJECTED":
        updated = _GEN_JOB_STORE.update(
            job_id,
            result=result,
            review_status="OWNER_SCORE_REJECTED",
            library_visible=False,
            score_lock=None,
            review=score_review,
            reviews=reviews,
            message="Partitura rejeitada e preservada; nenhum arranjo ou master foi criado.",
        )
        return _music_reinstrument_public_job(updated)

    score_lock = {
        "sha256": actual_hash,
        "approvedAt": reviewed_at,
        "reviewer": "owner",
        "immutable": True,
    }
    updated = _GEN_JOB_STORE.update(
        job_id,
        status="queued",
        progress=1,
        result=result,
        review_status="SCORE_LOCKED_ORCHESTRATING",
        library_visible=False,
        score_lock=score_lock,
        vocal_lock=vocal_lock,
        review=score_review,
        reviews=reviews,
        message="Hash da partitura bloqueado; iniciando apenas a troca deterministica de instrumentos.",
    )
    try:
        _start_score_first_orchestration_worker(
            job_id=job_id,
            score_path=score_path,
            score_sha256=actual_hash,
        )
    except Exception as exc:
        logging.exception("failed to start score-first orchestration for %s", job_id)
        updated = _GEN_JOB_STORE.update(
            job_id,
            status="error",
            progress=0,
            review_status="SCORE_LOCKED_ERROR",
            library_visible=False,
            error=str(exc),
            message="A partitura ficou bloqueada, mas o worker nao iniciou; os arquivos foram preservados.",
        )
    return _music_reinstrument_public_job(updated)


@app.post("/api/music-reinstrument/jobs/{job_id}/review")
async def music_reinstrument_job_review(request: Request, job_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    job = _GEN_JOB_STORE.get(job_id)
    if not job or job.get("mode") != "music_reinstrument":
        return _music_reinstrument_error(404, "JOB_NOT_FOUND", "Job de reinstrumentacao nao encontrado.")
    if job.get("status") != "done":
        return _music_reinstrument_error(409, "JOB_NOT_READY", "O candidato ainda nao esta pronto para revisao.")
    if (job.get("result") or {}).get("phase") == "score_review":
        return _music_reinstrument_error(
            409,
            "SCORE_REVIEW_REQUIRED",
            "Revise e bloqueie a partitura antes de tentar aprovar um master.",
        )
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"decision", "reason", "candidateIndex"}
        if unknown:
            raise ValueError(f"Campos de revisao nao permitidos: {', '.join(sorted(unknown))}.")
        decision = str(payload.get("decision") or "").strip().upper()
        reason = " ".join(str(payload.get("reason") or "").split())[:1000]
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValueError("Decisao deve ser APPROVED ou REJECTED.")
        if decision == "REJECTED" and len(reason) < 3:
            raise ValueError("Informe brevemente o motivo da rejeicao.")
        result = dict(job.get("result") or {})
        candidates = [dict(item) for item in (result.get("candidates") or [])]
        candidate_index = int(
            payload.get("candidateIndex")
            or result.get("recommendedCandidate")
            or 1
        )
        if candidates and candidate_index not in {
            int(item.get("index") or 0) for item in candidates
        }:
            raise ValueError("Candidato musical nao encontrado neste lote.")
        selected = next((c for c in candidates if int(c.get('index') or 0) == candidate_index), result)
        if decision == 'APPROVED' and (
                (selected.get('qc') or {}).get('technicalPass') is False
                or selected.get('technicalPass') is False
                or selected.get('creativeMixPass') is False
                or result.get('status') == 'INTERNAL_QC_REJECTED' and not candidates):
            return _music_reinstrument_error(409, 'TECHNICAL_QC_REJECTED',
                'Este candidato falhou nos controles internos; ele foi preservado e precisa de correcao.')
    except (TypeError, ValueError) as exc:
        return _music_reinstrument_error(422, "VALIDATION_ERROR", str(exc))
    reviewed_at = _t.time()
    for item in candidates:
        if int(item.get("index") or 0) == candidate_index:
            item["reviewStatus"] = (
                "OWNER_APPROVED_FINAL" if decision == "APPROVED" else "OWNER_REJECTED"
            )
            item["reviewReason"] = reason
            item["reviewedAt"] = reviewed_at
    if candidates:
        result["candidates"] = candidates
        if decision == "APPROVED":
            result["approvedCandidate"] = candidate_index
        elif int(result.get("approvedCandidate") or 0) == candidate_index:
            result.pop("approvedCandidate", None)
    all_rejected = bool(candidates) and all(
        str(item.get("reviewStatus") or "") == "OWNER_REJECTED" for item in candidates
    )
    viable_candidates_remaining = [
        item
        for item in candidates
        if str(item.get("reviewStatus") or "") != "OWNER_REJECTED"
        and item.get("creativeMixPass") is not False
        and (item.get('qc') or {}).get('technicalPass') is not False
    ]
    no_viable_candidates = bool(candidates) and not viable_candidates_remaining
    review_status = (
        "OWNER_APPROVED_FINAL"
        if decision == "APPROVED"
        else "OWNER_REJECTED"
        if not candidates or all_rejected or no_viable_candidates
        else "PENDING_HUMAN_REVIEW"
    )
    review_entry = {
        "decision": decision,
        "reason": reason,
        "candidateIndex": candidate_index,
        "reviewedAt": reviewed_at,
        "reviewer": "owner",
    }
    updated = _GEN_JOB_STORE.update(
        job_id,
        review_status=review_status,
        approved_candidate=(
            candidate_index
            if decision == "APPROVED"
            else None
            if int(job.get("approved_candidate") or 0) == candidate_index
            else job.get("approved_candidate")
        ),
        library_visible=(
            False
            if decision == "REJECTED" and review_status == "OWNER_REJECTED"
            else job.get("library_visible", True)
        ),
        result=result,
        review=review_entry,
        reviews=[*(job.get("reviews") or []), review_entry],
        message=(
            f"O candidato {candidate_index} exato foi aprovado; nenhum rerender foi feito."
            if decision == "APPROVED"
            else "Todos os candidatos foram rejeitados e preservados; o lote nao sera promovido."
            if all_rejected
            else (
                f"Candidato {candidate_index} rejeitado e preservado; nenhum outro candidato passou "
                "o gate interno, portanto o lote nao sera promovido."
            )
            if no_viable_candidates
            else f"Candidato {candidate_index} rejeitado e preservado; os demais continuam pendentes."
        ),
    )
    return _music_reinstrument_public_job(updated)


@app.post(
    "/api/video-projects/{project_id}/takes/{take_id}/audio-candidate-review"
)
async def video_take_audio_candidate_review(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"decision", "reason"}
        if unknown:
            raise ValueError(f"Campos de revisao de audio nao permitidos: {', '.join(sorted(unknown))}")
        return await run_in_threadpool(_review_take_audio_candidate,
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            decision=str(payload.get("decision") or ""),
            reason=str(payload.get("reason") or ""),
        )
    except FileNotFoundError:
        return _video_projects_error(404, "AUDIO_CANDIDATE_NOT_FOUND", "Candidato nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video-to-sound human review")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao revisar candidato de audio.")


def _start_project_assembly_job(project_id: str) -> dict[str, Any]:
    readiness = _get_project_assembly_readiness(VIDEO_PROJECTS_ROOT, project_id)
    if not readiness.get("ready"):
        raise ValueError("A sequencia ainda possui bloqueios de aprovacao.")
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve()
    if (
        project_dir.parent != VIDEO_PROJECTS_ROOT.resolve()
        or not project_dir.is_dir()
    ):
        raise FileNotFoundError(project_id)
    with _PROJECT_ASSEMBLY_LOCK:
        if project_id in _ACTIVE_PROJECT_ASSEMBLIES:
            raise TakeJobConflict("ASSEMBLY_ALREADY_RUNNING", "Este projeto ja esta sendo montado.")
        _ACTIVE_PROJECT_ASSEMBLIES.add(project_id)
    job_id = uuid.uuid4().hex
    _GEN_JOB_STORE.update(
        job_id,
        status="queued",
        progress=1,
        message="Montagem aprovada aguardando o worker local.",
        mode="project_assembly",
        job_kind="project_assembly",
        project_id=project_id,
        worker_pid=os.getpid(),
        source_fingerprint=readiness["sourceFingerprint"],
    )

    def worker() -> None:
        def update(progress: int, message: str) -> None:
            _GEN_JOB_STORE.update(
                job_id,
                status="running",
                progress=max(1, min(99, int(progress))),
                message=message,
                worker_pid=os.getpid(),
            )

        try:
            update(2, "Iniciando montagem local das fontes aprovadas.")
            record = _assemble_project(
                project_dir,
                sources=readiness["sources"],
                source_fingerprint=readiness["sourceFingerprint"],
                job_id=job_id,
                ffmpeg=get_ffmpeg(),
                ffprobe=shutil.which("ffprobe") or "ffprobe",
                progress=update,
                finish_media=_finish_required_media,
            )
            project = _register_project_final_output(
                VIDEO_PROJECTS_ROOT,
                project_id,
                expected_source_fingerprint=readiness["sourceFingerprint"],
                record=record,
            )
            _GEN_JOB_STORE.update(
                job_id,
                status="done",
                progress=100,
                message="Master tecnico pronto; assista e decida a aprovacao final.",
                result={"finalOutput": project.get("finalOutput", {})},
            )
        except Exception as exc:
            logging.exception("project assembly failed for %s", project_id)
            _GEN_JOB_STORE.update(
                job_id,
                status="error",
                progress=0,
                message="Montagem nao registrada; as fontes aprovadas foram preservadas.",
                error=str(exc),
            )
        finally:
            with _PROJECT_ASSEMBLY_LOCK:
                _ACTIVE_PROJECT_ASSEMBLIES.discard(project_id)

    threading.Thread(
        target=worker,
        name=f"project-assembly-{job_id[:8]}",
        daemon=True,
    ).start()
    return {
        "ok": True,
        "jobId": job_id,
        "status": "queued",
        "sourceFingerprint": readiness["sourceFingerprint"],
        "humanReviewRequired": True,
    }


@app.post("/api/video-projects/{project_id}/assembly-jobs", status_code=202)
async def video_project_assembly_start(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        if payload:
            raise ValueError("A montagem usa somente a sequencia aprovada; nenhum parametro extra e permitido.")
        return _start_project_assembly_job(project_id)
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto nao encontrado.")
    except TakeJobConflict as exc:
        return _video_projects_error(409, "ASSEMBLY_ALREADY_RUNNING", str(exc))
    except ValueError as exc:
        try:
            details = _get_project_assembly_readiness(VIDEO_PROJECTS_ROOT, project_id)
        except Exception:
            details = None
        return _video_projects_error(422, "ASSEMBLY_BLOCKED", str(exc), details)
    except Exception:
        logging.exception("project assembly start for %s", project_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao iniciar montagem.")


@app.post("/api/video-projects/{project_id}/final-review")
async def video_project_final_review(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"decision", "reason"}
        if unknown:
            raise ValueError(f"Campos de revisao final nao permitidos: {', '.join(sorted(unknown))}")
        return _review_project_final_output(
            VIDEO_PROJECTS_ROOT,
            project_id,
            decision=str(payload.get("decision") or ""),
            reason=str(payload.get("reason") or ""),
        )
    except FileNotFoundError:
        return _video_projects_error(404, "FINAL_OUTPUT_NOT_FOUND", "Master final nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "FINAL_REVIEW_BLOCKED", str(exc))
    except Exception:
        logging.exception("project final review for %s", project_id)
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao registrar revisao final.")


@app.api_route(
    "/api/video-projects/{project_id}/final-preview",
    methods=["GET", "HEAD"],
)
async def video_project_final_preview(
    request: Request,
    project_id: str,
    download: bool = False,
    archive: bool = False,
):
    """Stream the complete registered movie or download its untouched master."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        media = _get_project_final_output_path(
            VIDEO_PROJECTS_ROOT,
            project_id,
            download=download or archive,
        )
        if archive:
            from verified_download import prepare_verified_zip
            package = await run_in_threadpool(prepare_verified_zip, media, Path(BASE_DIR) / "dados" / "studio" / "verified_downloads")
            return FileResponse(package, media_type="application/zip", filename=media.name + ".zip",
                                headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
        range_header = request.headers.get("range", "").strip()
        if "," in range_header:
            return Response(
                status_code=416,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes */{media.stat().st_size}",
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        return FileResponse(
            media,
            media_type=mimetypes.guess_type(media.name)[0] or "video/mp4",
            filename=media.name if download else None,
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Maestro-Project-Asset": "final-master" if download else "final-review",
                "Cache-Control": (
                    "private, no-store"
                    if download
                    else "private, max-age=31536000, immutable"
                    if request.query_params.get("v")
                    else "private, max-age=0, must-revalidate"
                ),
            },
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "FINAL_OUTPUT_NOT_FOUND",
            "O clipe completo ainda nao foi registrado neste projeto.",
        )
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video project final preview")
        return _video_projects_error(
            500,
            "INTERNAL_ERROR",
            "Falha ao abrir o clipe completo do projeto.",
        )



@app.api_route(
    "/api/video-projects/{project_id}/candidate-preview",
    methods=["GET", "HEAD"],
)
async def video_project_candidate_preview(
    request: Request,
    project_id: str,
    download: bool = False,
    archive: bool = False,
):
    """Stream the review-only candidate without granting approval."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        media = _get_project_candidate_output_path(
            VIDEO_PROJECTS_ROOT,
            project_id,
        )
        if archive:
            from verified_download import prepare_verified_zip
            package = await run_in_threadpool(prepare_verified_zip, media, Path(BASE_DIR) / "dados" / "studio" / "verified_downloads")
            return FileResponse(package, media_type="application/zip", filename=media.name + ".zip",
                                headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
        range_header = request.headers.get("range", "").strip()
        if "," in range_header:
            return Response(
                status_code=416,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes */{media.stat().st_size}",
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        return FileResponse(
            media,
            media_type=mimetypes.guess_type(media.name)[0] or "video/mp4",
            filename=media.name if download else None,
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Maestro-Project-Asset": "candidate-download" if download else "candidate-review",
                "Cache-Control": (
                    "private, no-store"
                    if download
                    else "private, max-age=31536000, immutable"
                    if request.query_params.get("v")
                    else "private, max-age=0, must-revalidate"
                ),
            },
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "CANDIDATE_OUTPUT_NOT_FOUND",
            "Nenhum capitulo candidato registrado neste projeto.",
        )
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video project final preview")
        return _video_projects_error(
            500,
            "INTERNAL_ERROR",
            "Falha ao abrir o clipe completo do projeto.",
        )



@app.patch("/api/video-projects/{project_id}")
async def video_project_patch(request: Request, project_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _internet_publication_body(request)
        return _patch_video_project(VIDEO_PROJECTS_ROOT, project_id, payload)
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video project patch")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao atualizar projeto.")


@app.get("/api/video-projects/{project_id}/takes")
async def video_takes_list(
    request: Request,
    project_id: str,
    page: int = 1,
    pageSize: int = 50,
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        return await run_in_threadpool(_list_video_takes, VIDEO_PROJECTS_ROOT, project_id, page=page, page_size=pageSize)
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video takes list")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao listar takes.")


@app.api_route(
    "/api/video-projects/{project_id}/takes/{take_id}/preview",
    methods=["GET", "HEAD"],
)
def video_take_preview(request: Request, project_id: str, take_id: str, download: bool = False, archive: bool = False):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        preview = (
            _get_take_download_path(VIDEO_PROJECTS_ROOT, project_id, take_id)
            if download or archive
            else _get_take_preview_path(VIDEO_PROJECTS_ROOT, project_id, take_id)
        )
        if archive:
            from verified_download import prepare_verified_zip
            package = prepare_verified_zip(preview, Path(BASE_DIR) / "dados" / "studio" / "verified_downloads")
            return FileResponse(package, media_type="application/zip", filename=preview.name + ".zip",
                                headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
        project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve()
        is_proxy = (
            not download
            and project_dir.parent == VIDEO_PROJECTS_ROOT.resolve()
            and _is_review_proxy_path(project_dir, preview)
        )
        if (
            not download
            and not is_proxy
            and _get_take_status(VIDEO_PROJECTS_ROOT, project_id, take_id) == "APPROVED"
        ):
            _enqueue_review_proxy(project_id, take_id, preview)
        range_header = request.headers.get("range", "").strip()
        if "," in range_header:
            return Response(
                status_code=416,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes */{preview.stat().st_size}",
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        versioned_asset = bool(not download and request.query_params.get("v"))
        media_type = mimetypes.guess_type(preview.name)[0] or "video/mp4"
        response = FileResponse(
            preview,
            media_type=media_type,
            filename=preview.name if download else None,
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Maestro-Review-Asset": (
                    "master-download"
                    if download
                    else "proxy"
                    if is_proxy
                    else "master-fallback-proxy-queued"
                ),
                "Cache-Control": (
                    "private, no-store"
                    if download
                    else "private, max-age=86400, immutable"
                    if versioned_asset
                    else "private, max-age=0, must-revalidate"
                ),
                "Vary": "Range",
            },
        )
        response.chunk_size = 512 * 1024
        return response
    except FileNotFoundError:
        return _video_projects_error(404, "PREVIEW_NOT_FOUND", "Candidato de revisao nao encontrado.")
    except PermissionError as exc:
        return _video_projects_error(409, "DOWNLOAD_NOT_RELEASED", str(exc))
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take preview")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao abrir candidato de revisao.")


@app.api_route(
    "/api/video-projects/{project_id}/takes/{take_id}/audio-candidate",
    methods=["GET", "HEAD"],
)
async def video_take_audio_candidate(request: Request, project_id: str, take_id: str):
    """Serve only a registered project-local candidate for explicit human listening."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        candidate = _get_take_audio_candidate_path(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
        )
        media_type = mimetypes.guess_type(candidate.name)[0] or "audio/wav"
        return FileResponse(
            candidate,
            media_type=media_type,
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Maestro-Human-Review": "audio-candidate-pending-listening",
                "Cache-Control": "private, no-store",
            },
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "AUDIO_CANDIDATE_NOT_FOUND",
            "Candidato de audio nao encontrado para este take.",
        )
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take audio candidate")
        return _video_projects_error(
            500,
            "INTERNAL_ERROR",
            "Falha ao abrir candidato de audio.",
        )


@app.api_route(
    "/api/video-projects/{project_id}/takes/{take_id}/audio-candidates/{candidate_id}",
    methods=["GET", "HEAD"],
)
async def video_take_audio_candidate_variant(
    request: Request,
    project_id: str,
    take_id: str,
    candidate_id: str,
):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        candidate = _get_take_audio_candidate_variant_path(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            candidate_id,
        )
        media_type = mimetypes.guess_type(candidate.name)[0] or "audio/wav"
        return FileResponse(
            candidate,
            media_type=media_type,
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Maestro-Human-Review": "audio-candidate-pending-listening",
                "Cache-Control": "private, no-store",
            },
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "AUDIO_CANDIDATE_NOT_FOUND",
            "Variante de audio nao encontrada para este take.",
        )
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take audio candidate variant")
        return _video_projects_error(
            500,
            "INTERNAL_ERROR",
            "Falha ao abrir variante de audio.",
        )


@app.get("/api/video-projects/{project_id}/takes/{take_id}/upscale-preview")
async def video_take_upscale_preview(request: Request, project_id: str, take_id: str):
    """Serve only the pending neural FHD candidate; the canonical preview stays active."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        preview = _get_take_upscale_preview_path(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
        )
        media_type = mimetypes.guess_type(preview.name)[0] or "video/mp4"
        return FileResponse(
            preview,
            media_type=media_type,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "UPSCALE_PREVIEW_NOT_FOUND",
            "Candidato neural FHD pendente nao encontrado.",
        )
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take upscale preview")
        return _video_projects_error(
            500,
            "INTERNAL_ERROR",
            "Falha ao abrir candidato neural FHD pendente.",
        )


@app.get("/api/video-projects/{project_id}/takes/{take_id}/thumbnail")
async def video_take_thumbnail(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        thumbnail = _get_take_thumbnail_path(VIDEO_PROJECTS_ROOT, project_id, take_id)
        media_type = mimetypes.guess_type(thumbnail.name)[0] or "image/png"
        return FileResponse(thumbnail, media_type=media_type)
    except FileNotFoundError:
        return _video_projects_error(404, "THUMBNAIL_NOT_FOUND", "Imagem-base do take nao encontrada.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take thumbnail")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao abrir imagem-base do take.")


@app.get("/api/video-projects/{project_id}/takes/{take_id}/anchor-image")
async def video_take_anchor_image(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        anchor = _get_take_anchor_image_path(VIDEO_PROJECTS_ROOT, project_id, take_id)
        return FileResponse(
            anchor,
            media_type="image/png",
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )
    except (_AnchorRequestNotFoundError, FileNotFoundError):
        return _video_projects_error(
            404,
            "ANCHOR_IMAGE_NOT_FOUND",
            "Imagem-ancora registrada nao encontrada para este take.",
        )
    except _AnchorConflictError as exc:
        return _video_projects_error(409, "ANCHOR_CONFLICT", str(exc))
    except ValueError as exc:
        return _video_projects_error(422, "ANCHOR_INTEGRITY_ERROR", str(exc))
    except Exception:
        logging.exception("video take anchor image")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao abrir imagem-ancora.")


@app.get("/api/video-projects/{project_id}/takes/{take_id}/preanalysis-gallery")
async def video_take_preanalysis_gallery(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        gallery = _get_take_preanalysis_gallery_path(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
        )
        return FileResponse(
            gallery,
            media_type="image/png",
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "PREANALYSIS_GALLERY_NOT_FOUND",
            "Galeria START/checkpoint/END nao encontrada para este take.",
        )
    except ValueError as exc:
        return _video_projects_error(422, "PREANALYSIS_GALLERY_INTEGRITY_ERROR", str(exc))
    except Exception:
        logging.exception("video take preanalysis gallery")
        return _video_projects_error(
            500,
            "INTERNAL_ERROR",
            "Falha ao abrir a galeria de pre-analise.",
        )


@app.post("/api/video-projects/{project_id}/takes/{take_id}/anchor-candidate", status_code=201)
async def video_take_anchor_candidate(
    request: Request,
    project_id: str,
    take_id: str,
    requestId: str = Form(...),
    metadata: str = Form(...),
    image: UploadFile = File(...),
):
    if not _is_internal_request(request):
        try:
            await image.close()
        except Exception:
            pass
        return _public_forbidden()
    try:
        if len(metadata.encode("utf-8")) > 64 * 1024:
            raise ValueError("metadata da imagem-ancora excede o limite de 64 KB.")
        try:
            metadata_payload = json.loads(metadata)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("metadata da imagem-ancora deve ser JSON valido.") from exc
        if not isinstance(metadata_payload, dict):
            raise ValueError("metadata da imagem-ancora deve ser um objeto JSON.")
        original_filename = str(image.filename or "")
        try:
            image_bytes = await _read_upload_bounded(
                image,
                "Imagem-ancora",
                _MAX_ANCHOR_IMAGE_BYTES,
            )
        except ValueError as exc:
            if "excede o limite" in str(exc):
                return _video_projects_error(413, "ANCHOR_IMAGE_TOO_LARGE", str(exc))
            raise
        return _register_anchor_candidate(
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            request_id=requestId,
            image_bytes=image_bytes or b"",
            original_filename=original_filename,
            metadata=metadata_payload,
        )
    except _AnchorRequestNotFoundError:
        return _video_projects_error(
            404,
            "DIRECTOR_REQUEST_NOT_FOUND",
            "Pedido de imagem-ancora nao encontrado para este take.",
        )
    except FileNotFoundError:
        return _video_projects_error(404, "TAKE_NOT_FOUND", "Projeto ou take nao encontrado.")
    except _AnchorConflictError as exc:
        return _video_projects_error(409, "ANCHOR_CONFLICT", str(exc))
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take anchor candidate")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao registrar imagem-ancora.")
    finally:
        try:
            await image.close()
        except Exception:
            pass


@app.post("/api/video-projects/{project_id}/takes/{take_id}/anchor-review")
async def video_take_anchor_review(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {
            "decision", "reason", "requestId", "actualVisibleCharacters", "humanConfirmed",
        }
        if unknown:
            raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
        if not isinstance(payload.get("decision"), str):
            raise ValueError("decision deve ser uma string.")
        if "reason" in payload and not isinstance(payload.get("reason"), str):
            raise ValueError("reason deve ser uma string.")
        if "requestId" in payload and not isinstance(payload.get("requestId"), str):
            raise ValueError("requestId deve ser uma string.")
        if "actualVisibleCharacters" in payload and not isinstance(
            payload.get("actualVisibleCharacters"), list
        ):
            raise ValueError("actualVisibleCharacters deve ser uma lista.")
        if "humanConfirmed" in payload and not isinstance(payload.get("humanConfirmed"), bool):
            raise ValueError("humanConfirmed deve ser booleano.")
        return await run_in_threadpool(_review_anchor_candidate,
            VIDEO_PROJECTS_ROOT,
            project_id,
            take_id,
            decision=payload["decision"],
            reason=payload.get("reason") or "",
            request_id=payload.get("requestId") or "",
            actual_visible_characters=payload.get("actualVisibleCharacters"),
            human_confirmed=bool(payload.get("humanConfirmed", False)),
        )
    except _AnchorRequestNotFoundError:
        return _video_projects_error(
            404,
            "DIRECTOR_REQUEST_NOT_FOUND",
            "Pedido de imagem-ancora nao encontrado para este take.",
        )
    except FileNotFoundError:
        return _video_projects_error(
            404,
            "ANCHOR_CANDIDATE_NOT_FOUND",
            "Candidato de imagem-ancora nao encontrado para este take.",
        )
    except _AnchorConflictError as exc:
        return _video_projects_error(409, "ANCHOR_CONFLICT", str(exc))
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take anchor review")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao revisar imagem-ancora.")


@app.patch("/api/video-projects/{project_id}/takes/{take_id}")
async def video_take_patch(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        return await run_in_threadpool(_patch_video_take, VIDEO_PROJECTS_ROOT, project_id, take_id, payload, defer_exports=True)
    except FileNotFoundError:
        return _video_projects_error(404, "TAKE_NOT_FOUND", "Projeto ou take nao encontrado.")
    except ValueError as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take patch")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao atualizar take.")


def _video_take_model_for_spec(spec: Dict[str, Any]) -> str:
    generation_profile = str(spec.get("generationProfile") or "").strip()
    if generation_profile == _LTX25_TAKE_PROFILE:
        raise _VideoEngineError("ENGINE_NOT_ALLOWED", "LTX removido pelo proprietario; selecione MiniMax H3.", status_code=409)
    if generation_profile in {
        MINIMAX_H3_PROFILE,
        MINIMAX_H3_VERTICAL_PROFILE,
        "minimax_h3_fl2va_int8_owner_30s_native_av_720p24",
    }:
        minimax_control = (
            spec.get("minimaxAnchorControl")
            if isinstance(spec.get("minimaxAnchorControl"), dict)
            else {}
        )
        if str(minimax_control.get("mode") or "").strip().lower() == "ref2va_motion":
            return MINIMAX_H3_REF2VA_MODEL_NAME
        return MINIMAX_H3_MODEL_NAME
    raise _VideoEngineError(
        "ENGINE_NOT_ALLOWED",
        "O take deve selecionar explicitamente MiniMax H3.",
        status_code=409,
        details={"generation_profile": generation_profile},
    )


def _video_take_model_ready(model: str) -> bool:
    if model == MINIMAX_H3_MODEL_NAME:
        return _minimax_h3_kit_ready()
    if model == MINIMAX_H3_REF2VA_MODEL_NAME:
        return _minimax_h3_kit_ready() and _minimax_h3_ref2va_ready()
    return False


def _wait_for_recovered_video_engine(
    job_id: str,
    cancel_event: threading.Event,
    model: str,
) -> None:
    """Keep a recovered take queued until its selected video engine is ready."""

    last_message = ""
    while True:
        if cancel_event.is_set():
            raise GenerationCancelled("Geracao recuperada cancelada pelo proprietario.")
        online, _details = _comfy_online()
        transport_ready = online
        if transport_ready and _video_take_model_ready(model) and not _video_generation_paused():
            return
        if _video_generation_paused():
            message = f"Tarefa recuperada; aguardando liberacao do video. {_video_pause_message()}"
        elif not online:
            message = "Tarefa recuperada; aguardando o ComfyUI voltar."
        else:
            message = f"Tarefa recuperada; aguardando o modelo configurado {model}."
        if message != last_message:
            _set_gen_job(job_id, status="queued", message=message)
            last_message = message
        cancel_event.wait(5.0)


def _enqueue_video_take_turn(job_id: str) -> int:
    """Register one take in the process-local FIFO before its worker starts."""

    job_id = str(job_id or "").strip()
    if not job_id:
        raise ValueError("Job de take sem identificador.")
    with _VIDEO_TAKE_QUEUE_CONDITION:
        if job_id == _VIDEO_TAKE_ACTIVE_JOB_ID or job_id in _VIDEO_TAKE_QUEUE:
            raise RuntimeError(f"Job de take ja esta na fila serial: {job_id}.")
        _VIDEO_TAKE_QUEUE.append(job_id)
        position = len(_VIDEO_TAKE_QUEUE) + (1 if _VIDEO_TAKE_ACTIVE_JOB_ID else 0)
        _VIDEO_TAKE_QUEUE_CONDITION.notify_all()
        return position


def _wake_video_take_queue() -> None:
    """Wake queued workers after cancellation or another external state change."""

    with _VIDEO_TAKE_QUEUE_CONDITION:
        _VIDEO_TAKE_QUEUE_CONDITION.notify_all()


def _wait_for_video_take_turn(job_id: str, cancel_event: threading.Event) -> None:
    """Acquire the single render slot in FIFO order without loading a model early."""

    global _VIDEO_TAKE_ACTIVE_JOB_ID
    with _VIDEO_TAKE_QUEUE_CONDITION:
        while True:
            if cancel_event.is_set():
                if job_id in _VIDEO_TAKE_QUEUE:
                    _VIDEO_TAKE_QUEUE.remove(job_id)
                _VIDEO_TAKE_QUEUE_CONDITION.notify_all()
                raise GenerationCancelled("Geracao cancelada enquanto aguardava na fila de takes.")
            if (
                not _VIDEO_TAKE_ACTIVE_JOB_ID
                and _VIDEO_TAKE_QUEUE
                and _VIDEO_TAKE_QUEUE[0] == job_id
            ):
                _VIDEO_TAKE_QUEUE.pop(0)
                _VIDEO_TAKE_ACTIVE_JOB_ID = job_id
                _VIDEO_TAKE_QUEUE_CONDITION.notify_all()
                return
            if job_id not in _VIDEO_TAKE_QUEUE:
                raise RuntimeError(f"Job de take saiu inesperadamente da fila serial: {job_id}.")
            _VIDEO_TAKE_QUEUE_CONDITION.wait(timeout=0.5)


def _release_video_take_turn(job_id: str) -> None:
    """Release the exclusive render slot and remove any stale queued entry."""

    global _VIDEO_TAKE_ACTIVE_JOB_ID
    with _VIDEO_TAKE_QUEUE_CONDITION:
        if _VIDEO_TAKE_ACTIVE_JOB_ID == job_id:
            _VIDEO_TAKE_ACTIVE_JOB_ID = ""
        if job_id in _VIDEO_TAKE_QUEUE:
            _VIDEO_TAKE_QUEUE.remove(job_id)
        _VIDEO_TAKE_QUEUE_CONDITION.notify_all()


def _wait_for_upscale_gate(job_id: str, cancel_event: threading.Event) -> None:
    """Do not let a video workflow start while Real-ESRGAN owns the GPU."""

    announced = False
    while _VIDEO_UPSCALE_GATE.is_set():
        if cancel_event.is_set():
            raise GenerationCancelled("Geracao cancelada antes de usar a GPU.")
        if not announced:
            _set_gen_job(
                job_id,
                status="queued",
                message="Na fila; aguardando o upscale 1080p liberar a GPU.",
            )
            announced = True
        cancel_event.wait(2.0)


def _inspect_video_temporal_motion(source: Path) -> Dict[str, Any]:
    """Fail closed when the generated file is a frozen first frame."""

    ffmpeg = get_ffmpeg()
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(source),
        "-vf",
        "freezedetect=n=-45dB:d=0.75",
        "-an",
        "-f",
        "null",
        os.devnull,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            f"QC temporal nao conseguiu inspecionar o video: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-800:]
        raise RuntimeError(
            f"QC temporal falhou ao decodificar o video: {detail or 'ffmpeg sem detalhe'}"
        )

    detector_log = f"{completed.stderr or ''}\n{completed.stdout or ''}"
    freeze_starts = [
        float(value)
        for value in re.findall(
            r"lavfi\.freezedetect\.freeze_start:\s*([0-9]+(?:\.[0-9]+)?)",
            detector_log,
        )
    ]
    freeze_ends = [
        float(value)
        for value in re.findall(
            r"lavfi\.freezedetect\.freeze_end:\s*([0-9]+(?:\.[0-9]+)?)",
            detector_log,
        )
    ]
    duration_match = re.search(
        r"Duration:\s*(\d+):(\d+):([0-9]+(?:\.[0-9]+)?)",
        detector_log,
    )
    duration_seconds = 0.0
    if duration_match:
        duration_seconds = (
            int(duration_match.group(1)) * 3600
            + int(duration_match.group(2)) * 60
            + float(duration_match.group(3))
        )
    frozen_from_first_frame = bool(
        freeze_starts
        and freeze_starts[0] <= 0.05
        and len(freeze_ends) < len(freeze_starts)
    )
    if frozen_from_first_frame:
        raise RuntimeError(
            "QC_MOTION_FROZEN: o motor entregou uma foto repetida, sem movimento "
            "temporal verificavel; o take foi bloqueado antes da revisao."
        )
    frozen_seconds = sum(
        max(0.0, end - start)
        for start, end in zip(freeze_starts, freeze_ends)
    )
    if len(freeze_starts) > len(freeze_ends) and duration_seconds > 0:
        frozen_seconds += max(0.0, duration_seconds - freeze_starts[-1])
    freeze_ratio = (
        min(1.0, frozen_seconds / duration_seconds)
        if duration_seconds > 0
        else 0.0
    )
    if freeze_ratio >= 0.70:
        raise RuntimeError(
            "QC_MOTION_INSUFFICIENT: mais de 70% do take ficou temporalmente "
            "congelado; o video foi bloqueado antes da revisao."
        )
    return {
        "status": "PASS",
        "detector": "ffmpeg_freezedetect",
        "noise_threshold_db": -45,
        "minimum_freeze_seconds": 0.75,
        "duration_seconds": duration_seconds,
        "frozen_seconds": frozen_seconds,
        "freeze_ratio": freeze_ratio,
        "freeze_starts": freeze_starts,
        "freeze_ends": freeze_ends,
    }


def _assess_detected_human_face_counts(
    counts: List[int],
    expected_human_count: int,
    expected_non_human_count: int = 0,
    detector_tolerance: int | None = None,
) -> Dict[str, Any]:
    """Reject a sustained face-count surge while tolerating stylized cast faces."""

    if not counts:
        raise RuntimeError("QC_CAST_SURGE: nenhum quadro foi amostrado para conferir o elenco.")
    expected_human_count = max(0, int(expected_human_count))
    expected_non_human_count = max(0, int(expected_non_human_count))
    expected_face_like_count = expected_human_count + expected_non_human_count
    normalized = [max(0, int(value)) for value in counts]
    # Haar detects face-like geometry, not human identity. Named stylized
    # non-human characters therefore belong to the expected baseline. One
    # additional false positive is tolerable; a sustained surplus still blocks
    # duplicate bodies, sequential entrants and actual crowds.
    if detector_tolerance is None:
        tolerance = 1 if expected_face_like_count > 0 else 2
    else:
        tolerance = max(0, int(detector_tolerance))
    threshold = expected_face_like_count + tolerance
    peak = max(normalized)
    frames_at_or_above_threshold = sum(value >= threshold for value in normalized)
    surge_detected = peak > threshold and frames_at_or_above_threshold >= 2
    if surge_detected:
        raise RuntimeError(
            "QC_CAST_SURGE: o video multiplicou o elenco humano; foram detectados "
            f"ate {peak} rostos onde o contrato permite {expected_face_like_count} "
            "entidades nomeadas com face. "
            "O candidato foi bloqueado antes de aparecer no Maestro."
        )
    return {
        "status": "PASS",
        "method": "opencv_haar_sampled_face_surge_v1",
        "expected_human_count": expected_human_count,
        "expected_non_human_count": expected_non_human_count,
        "expected_face_like_count": expected_face_like_count,
        "sampled_face_counts": normalized,
        "peak_detected_faces": peak,
        "surge_threshold": threshold,
        "detector_tolerance": tolerance,
    }


def _inspect_video_human_cast_surge(
    source: Path,
    expected_human_count: int,
    *,
    expected_non_human_count: int = 0,
    sample_count: int = 10,
) -> Dict[str, Any]:
    """Sample the render and fail closed on obvious duplicate/crowd creation."""

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("QC_CAST_SURGE: OpenCV indisponivel para conferir o elenco.") from exc
    capture = cv2.VideoCapture(str(source))
    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if not capture.isOpened() or total_frames <= 0:
            raise RuntimeError("QC_CAST_SURGE: nao foi possivel abrir o video para conferir o elenco.")
        classifier_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        eye_classifier_path = (
            Path(cv2.data.haarcascades) / "haarcascade_eye_tree_eyeglasses.xml"
        )
        classifier = cv2.CascadeClassifier(str(classifier_path))
        eye_classifier = cv2.CascadeClassifier(str(eye_classifier_path))
        if classifier.empty() or eye_classifier.empty():
            raise RuntimeError("QC_CAST_SURGE: detector facial local nao foi carregado.")
        requested_samples = max(3, min(20, int(sample_count)))
        positions = sorted({
            int(round(index * (total_frames - 1) / max(1, requested_samples - 1)))
            for index in range(requested_samples)
        })
        counts: List[int] = []
        raw_counts: List[int] = []
        sampled_positions: List[int] = []
        for position in positions:
            capture.set(cv2.CAP_PROP_POS_FRAMES, position)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            minimum_face = max(36, min(gray.shape[:2]) // 16)
            faces = classifier.detectMultiScale(
                gray,
                scaleFactor=1.08,
                minNeighbors=7,
                minSize=(minimum_face, minimum_face),
            )
            # The frontal Haar cascade alone repeatedly classified the flower
            # print on Rafaela's dress, waveform cards and roof ornaments as
            # faces. Require eye/eyeglass geometry inside the upper part of a
            # candidate face. This keeps actual extra people detectable while
            # removing persistent scene-texture false positives.
            verified_faces = []
            for x, y, face_width, face_height in faces:
                upper_face = gray[
                    int(y):int(y + max(1, round(face_height * 0.68))),
                    int(x):int(x + face_width),
                ]
                minimum_eye = max(8, int(round(min(face_width, face_height) * 0.10)))
                eyes = eye_classifier.detectMultiScale(
                    upper_face,
                    scaleFactor=1.05,
                    minNeighbors=3,
                    minSize=(minimum_eye, minimum_eye),
                )
                if len(eyes) >= 1:
                    verified_faces.append((x, y, face_width, face_height))
            raw_counts.append(len(faces))
            counts.append(len(verified_faces))
            sampled_positions.append(position)
    finally:
        capture.release()
    assessment = _assess_detected_human_face_counts(
        counts,
        expected_human_count,
        expected_non_human_count,
        detector_tolerance=0,
    )
    assessment["sampled_frame_positions"] = sampled_positions
    assessment["raw_haar_face_counts"] = raw_counts
    assessment["method"] = "opencv_haar_eye_verified_sampled_face_surge_v2"
    return assessment


def _probe_audio_delivery_media(path: Path) -> Dict[str, Any]:
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "FFprobe nao conseguiu validar a entrega de audio: "
            f"{(completed.stderr or completed.stdout).strip()[-800:]}"
        )
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    video = next(
        (item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"),
        {},
    )
    audio = next(
        (item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"),
        {},
    )
    return {
        "duration_seconds": float((payload.get("format") or {}).get("duration") or 0.0),
        "video": video,
        "audio": audio,
        "has_audio": bool(audio),
    }


def _ffmpeg_atempo_chain(speed: float) -> str:
    speed = max(0.125, min(8.0, float(speed)))
    factors: List[float] = []
    while speed > 2.0:
        factors.append(2.0)
        speed /= 2.0
    while speed < 0.5:
        factors.append(0.5)
        speed /= 0.5
    factors.append(speed)
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


_PTBR_ASR_LOCK = threading.Lock()
_PTBR_ASR_MODEL = None


def _normalize_spoken_ptbr(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


_PTBR_ASR_NEAR_HOMOPHONES = {
    frozenset({"mais", "mas"}),
}

_PTBR_ASR_PROTECTED_TOKENS = {
    "nao", "nunca", "sem", "nem",
    "zero", "dois", "duas", "tres", "quatro", "cinco",
    "seis", "sete", "oito", "nove", "dez",
}


def _assess_spoken_ptbr_asr(expected: str, transcript: str) -> Dict[str, Any]:
    """Separate a true text mismatch from a narrow Whisper orthography ambiguity.

    A close phonetic transcript never becomes an automatic approval. It only
    preserves an expensive audiovisual render for mandatory human listening.
    Repetition, large length changes and protected semantic-token changes remain
    hard failures.
    """

    expected_normalized = _normalize_spoken_ptbr(expected)
    transcript_normalized = _normalize_spoken_ptbr(transcript)
    if expected_normalized and transcript_normalized == expected_normalized:
        return {
            "accepted_for_human_review": True,
            "exact": True,
            "status": "EXACT_TEXT_MATCH",
            "expected_normalized": expected_normalized,
            "transcript_normalized": transcript_normalized,
            "ambiguous_tokens": [],
        }
    expected_tokens = expected_normalized.split()
    transcript_tokens = transcript_normalized.split()
    ambiguous: List[Dict[str, Any]] = []
    if expected_tokens and len(expected_tokens) == len(transcript_tokens):
        for index, (expected_token, transcript_token) in enumerate(
            zip(expected_tokens, transcript_tokens)
        ):
            if expected_token == transcript_token:
                continue
            if frozenset({expected_token, transcript_token}) in _PTBR_ASR_NEAR_HOMOPHONES:
                ambiguous.append({
                    "index": index,
                    "expected": expected_token,
                    "transcribed": transcript_token,
                })
                continue
            ambiguous = []
            break
    near_match = len(ambiguous) == 1
    if near_match:
        return {
            "accepted_for_human_review": True,
            "exact": False,
            "status": "ASR_NEAR_HOMOPHONE_REQUIRES_HUMAN_LISTENING",
            "expected_normalized": expected_normalized,
            "transcript_normalized": transcript_normalized,
            "ambiguous_tokens": ambiguous,
            "compact_similarity": 1.0,
        }

    expected_compact = expected_normalized.replace(" ", "")
    transcript_compact = transcript_normalized.replace(" ", "")
    compact_similarity = (
        SequenceMatcher(None, expected_compact, transcript_compact).ratio()
        if expected_compact and transcript_compact
        else 0.0
    )
    char_length_ratio = (
        len(transcript_compact) / len(expected_compact)
        if expected_compact
        else 0.0
    )
    expected_protected = [
        token for token in expected_tokens if token in _PTBR_ASR_PROTECTED_TOKENS
    ]
    transcript_protected = [
        token for token in transcript_tokens if token in _PTBR_ASR_PROTECTED_TOKENS
    ]
    token_count_close = abs(len(expected_tokens) - len(transcript_tokens)) <= 2
    phonetic_ambiguity = bool(
        expected_tokens
        and transcript_tokens
        and token_count_close
        and 0.80 <= char_length_ratio <= 1.20
        and compact_similarity >= 0.94
        and expected_protected == transcript_protected
    )
    return {
        "accepted_for_human_review": phonetic_ambiguity,
        "exact": False,
        "status": (
            "ASR_PHONETIC_AMBIGUITY_REQUIRES_HUMAN_LISTENING"
            if phonetic_ambiguity
            else "TEXT_MISMATCH"
        ),
        "expected_normalized": expected_normalized,
        "transcript_normalized": transcript_normalized,
        "ambiguous_tokens": [],
        "compact_similarity": round(compact_similarity, 6),
    }


def _transcribe_ptbr_delivery(path: Path) -> Dict[str, Any]:
    global _PTBR_ASR_MODEL
    with _PTBR_ASR_LOCK:
        if _PTBR_ASR_MODEL is None:
            _PTBR_ASR_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = _PTBR_ASR_MODEL.transcribe(
            str(path),
            language="pt",
            beam_size=5,
            vad_filter=True,
            word_timestamps=True,
        )
        segments = list(segments)
        transcript = " ".join(
            str(segment.text or "").strip() for segment in segments if str(segment.text or "").strip()
        ).strip()
        words = [
            {
                "text": str(word.word or "").strip(),
                "start": round(float(word.start or 0.0), 6),
                "end": round(float(word.end or 0.0), 6),
            }
            for segment in segments
            for word in (segment.words or [])
            if str(word.word or "").strip()
        ]
    return {
        "transcript": transcript,
        "normalized": _normalize_spoken_ptbr(transcript),
        "language": str(info.language or ""),
        "language_probability": round(float(info.language_probability or 0.0), 6),
        "model": "faster-whisper-base-cpu-int8",
        "words": words,
    }


def _ptbr_exact_repetition_boundary(expected: str, asr: Dict[str, Any]) -> float | None:
    """Locate the end of one exact utterance when Qwen repeats it verbatim."""

    expected_tokens = _normalize_spoken_ptbr(expected).split()
    word_items = asr.get("words") if isinstance(asr.get("words"), list) else []
    flattened: List[Tuple[str, float]] = []
    for item in word_items:
        if not isinstance(item, dict):
            continue
        end = float(item.get("end") or 0.0)
        flattened.extend(
            (token, end) for token in _normalize_spoken_ptbr(item.get("text") or "").split()
        )
    transcript_tokens = [token for token, _end in flattened]
    expected_count = len(expected_tokens)
    if (
        expected_count == 0
        or len(transcript_tokens) < expected_count * 2
        or transcript_tokens[:expected_count] != expected_tokens
        or transcript_tokens[expected_count:expected_count * 2] != expected_tokens
    ):
        return None
    boundary = flattened[expected_count - 1][1]
    return boundary if boundary > 0.25 else None


def _trim_ptbr_delivery_at(path: Path, end_seconds: float) -> None:
    """Transactionally remove a verbatim repeated tail from a generated WAV."""

    temporary = path.with_name(f".{path.stem}.{uuid.uuid4().hex}.trim.wav")
    command = [
        get_ffmpeg(),
        "-y",
        "-i",
        str(path),
        "-t",
        f"{float(end_seconds) + 0.08:.6f}",
        "-c:a",
        "pcm_s16le",
        str(temporary),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size < 4096:
            detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(
                "Nao foi possivel remover a repeticao terminal da fala Qwen: "
                f"{detail or 'ffmpeg sem detalhe'}"
            )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _align_ptbr_conditioning_audio(
    path: Path,
    *,
    start_seconds: float,
    duration_seconds: float,
) -> Dict[str, float]:
    """Pad approved speech with silence so IA2V preserves the full take length."""

    start_seconds = max(0.0, float(start_seconds))
    duration_seconds = float(duration_seconds)
    source_probe = _probe_audio_delivery_media(path)
    speech_duration = float(source_probe.get("duration_seconds") or 0.0)
    if duration_seconds <= 0.25 or speech_duration <= 0.1:
        raise RuntimeError("Duracao invalida ao alinhar a fala condicionante do LTX.")
    if start_seconds + speech_duration > duration_seconds + 0.05:
        raise RuntimeError(
            "A fala Qwen nao cabe na duracao do take sem ser cortada: "
            f"inicio {start_seconds:.2f}s + fala {speech_duration:.2f}s > take {duration_seconds:.2f}s."
        )
    temporary = path.with_name(f".{path.stem}.{uuid.uuid4().hex}.aligned.wav")
    delay_ms = int(round(start_seconds * 1000.0))
    command = [
        get_ffmpeg(),
        "-y",
        "-i",
        str(path),
        "-af",
        (
            "silenceremove=start_periods=1:start_duration=0.03:"
            f"start_threshold=-42dB,adelay={delay_ms}:all=1,apad"
        ),
        "-t",
        f"{duration_seconds:.6f}",
        "-c:a",
        "pcm_s16le",
        str(temporary),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size < 4096:
            detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(
                "Nao foi possivel alinhar a fala na duracao completa do take: "
                f"{detail or 'ffmpeg sem detalhe'}"
            )
        aligned_probe = _probe_audio_delivery_media(temporary)
        aligned_duration = float(aligned_probe.get("duration_seconds") or 0.0)
        if abs(aligned_duration - duration_seconds) > 0.08:
            raise RuntimeError(
                "Audio condicionante ficou com duracao diferente do take: "
                f"{aligned_duration:.3f}s != {duration_seconds:.3f}s."
            )
        os.replace(temporary, path)
        return {
            "dialogue_start_seconds": round(start_seconds, 6),
            "speech_duration_seconds": round(speech_duration, 6),
            "conditioning_duration_seconds": round(aligned_duration, 6),
        }
    finally:
        temporary.unlink(missing_ok=True)


def _assemble_ptbr_conditioning_dialogue(
    turns: List[Dict[str, Any]],
    output: Path,
    *,
    duration_seconds: float,
) -> Dict[str, Any]:
    """Place separately validated character voices on one non-overlapping IA2V clock."""

    duration_seconds = float(duration_seconds)
    if duration_seconds <= 0.25 or len(turns) < 2:
        raise RuntimeError("Dialogo Qwen multipersonagem exige dois turnos e duracao valida.")
    normalized_turns: List[Dict[str, Any]] = []
    previous_end = 0.0
    for index, turn in enumerate(turns, start=1):
        source = Path(str(turn.get("output") or "")).resolve(strict=True)
        start = max(0.0, float(turn.get("dialogue_start_seconds") or 0.0))
        contracted_end = float(turn.get("dialogue_end_seconds") or 0.0)
        source_duration = float(_probe_audio_delivery_media(source).get("duration_seconds") or 0.0)
        if source_duration <= 0.1 or contracted_end <= start:
            raise RuntimeError(f"Turno {index} possui audio ou janela de fala invalida.")
        if start < previous_end - 0.02:
            raise RuntimeError("As janelas de dialogo Qwen se sobrepoem; a producao foi bloqueada.")
        actual_end = start + source_duration
        if actual_end > contracted_end + 0.08:
            raise RuntimeError(
                f"A fala de {turn.get('speaker') or 'um personagem'} nao cabe na janela aprovada "
                f"({source_duration:.2f}s > {contracted_end - start:.2f}s) sem corte ou aceleracao."
            )
        if actual_end > duration_seconds + 0.05:
            raise RuntimeError("O ultimo turno de fala ultrapassa a duracao contratada do take.")
        normalized_turns.append({
            **turn,
            "output": source,
            "dialogue_start_seconds": start,
            "dialogue_end_seconds": contracted_end,
            "speech_duration_seconds": source_duration,
            "speech_end_seconds": actual_end,
        })
        previous_end = contracted_end

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.stem}.{uuid.uuid4().hex}.dialogue.wav")
    command = [get_ffmpeg(), "-y"]
    for turn in normalized_turns:
        command.extend(["-i", str(turn["output"])])
    filters: List[str] = []
    mix_labels: List[str] = []
    for index, turn in enumerate(normalized_turns):
        delay_ms = int(round(float(turn["dialogue_start_seconds"]) * 1000.0))
        label = f"voice{index}"
        filters.append(
            f"[{index}:a]silenceremove=start_periods=1:start_duration=0.03:"
            f"start_threshold=-42dB,aresample=24000,"
            f"aformat=sample_fmts=s16:sample_rates=24000:channel_layouts=mono,"
            f"adelay={delay_ms}:all=1[{label}]"
        )
        mix_labels.append(f"[{label}]")
    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=longest:dropout_transition=0:normalize=0,"
        + f"apad,atrim=duration={duration_seconds:.6f}[dialogue]"
    )
    command.extend([
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[dialogue]",
        "-c:a",
        "pcm_s16le",
        str(temporary),
    ])
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size < 4096:
            detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(
                "Nao foi possivel montar as vozes pt-BR na linha temporal do take: "
                f"{detail or 'ffmpeg sem detalhe'}"
            )
        mixed_probe = _probe_audio_delivery_media(temporary)
        mixed_duration = float(mixed_probe.get("duration_seconds") or 0.0)
        if abs(mixed_duration - duration_seconds) > 0.08:
            raise RuntimeError(
                "Audio multipersonagem ficou com duracao diferente do take: "
                f"{mixed_duration:.3f}s != {duration_seconds:.3f}s."
            )
        os.replace(temporary, output)
        return {
            "dialogue_start_seconds": round(float(normalized_turns[0]["dialogue_start_seconds"]), 6),
            "speech_duration_seconds": round(
                float(normalized_turns[-1]["speech_end_seconds"])
                - float(normalized_turns[0]["dialogue_start_seconds"]),
                6,
            ),
            "conditioning_duration_seconds": round(mixed_duration, 6),
            "turns": [
                {
                    "speaker": str(turn.get("speaker") or ""),
                    "dialogue_start_seconds": round(float(turn["dialogue_start_seconds"]), 6),
                    "dialogue_end_seconds": round(float(turn["dialogue_end_seconds"]), 6),
                    "speech_duration_seconds": round(float(turn["speech_duration_seconds"]), 6),
                    "speech_end_seconds": round(float(turn["speech_end_seconds"]), 6),
                }
                for turn in normalized_turns
            ],
        }
    finally:
        temporary.unlink(missing_ok=True)


def _append_ltx_conditioned_audio_timeline(
    prompt: str,
    synthesis_result: Dict[str, Any],
) -> str:
    """Bind character reactions to the measured conditioned-audio window."""

    generation = (
        synthesis_result.get("tts_generation")
        if isinstance(synthesis_result.get("tts_generation"), dict)
        else {}
    )
    alignment = (
        generation.get("conditioning_alignment")
        if isinstance(generation.get("conditioning_alignment"), dict)
        else {}
    )
    gate = generation.get("asr_gate") if isinstance(generation.get("asr_gate"), dict) else {}
    turn_windows = alignment.get("turns") if isinstance(alignment.get("turns"), list) else []
    if turn_windows:
        instructions: List[str] = []
        first_start = max(0.0, float(turn_windows[0].get("dialogue_start_seconds") or 0.0))
        instructions.append(
            f"Native 24fps timeline: 0.00-{first_start:.2f}s is a silent setup; every mouth stays naturally closed."
        )
        previous_speech_end = first_start
        for index, turn in enumerate(turn_windows, start=1):
            start = max(0.0, float(turn.get("dialogue_start_seconds") or 0.0))
            speech_end = max(start, float(turn.get("speech_end_seconds") or start))
            speaker = str(turn.get("speaker") or "the named speaker").strip()
            if start > previous_speech_end + 0.02:
                instructions.append(
                    f"From {previous_speech_end:.2f}-{start:.2f}s every character keeps the mouth closed."
                )
            instructions.append(
                f"TURN {index}, {start:.2f}-{speech_end:.2f}s: only {speaker} articulates to the supplied voice; "
                "every listener keeps relaxed closed lips and reacts without speaking."
            )
            previous_speech_end = speech_end
        instructions.append(
            "Each gesture and reaction begins only after its matching audible cause. The supplied multi-speaker "
            "audio is the immutable clock for mouth, gesture, reaction and picture."
        )
        return (
            f"{prompt} [MAESTRO_CONDITIONED_DIALOGUE_TIMELINE_V2_BEGIN] "
            + " ".join(instructions)
            + " [MAESTRO_CONDITIONED_DIALOGUE_TIMELINE_V2_END]"
        )
    start = float(alignment.get("dialogue_start_seconds") or 0.0)
    words = gate.get("words") if isinstance(gate.get("words"), list) else []
    word_ends = [
        float(item.get("end") or 0.0)
        for item in words
        if isinstance(item, dict) and float(item.get("end") or 0.0) > 0
    ]
    speech_duration = float(alignment.get("speech_duration_seconds") or 0.0)
    end = start + (max(word_ends) if word_ends else speech_duration)
    if end <= start:
        return prompt
    return (
        f"{prompt} "
        "[MAESTRO_CONDITIONED_AUDIO_TIMELINE_V1_BEGIN] "
        f"Native 24fps timeline: 0.00-{start:.2f}s is a silent setup; every mouth stays "
        f"naturally closed. {start:.2f}-{end:.2f}s is the only authorized articulation "
        "window and only the named speaker follows the supplied audio. Listener mouths stay "
        f"closed. Reactions caused by the line begin only after {end:.2f}s, never before the "
        "corresponding audible cause. Requested hand, instrument or object contacts happen "
        "once at their matching audio cue, with no anticipatory cycle and no repeated gesture. "
        "The supplied audio is the immutable clock for mouth, gesture, reaction and picture. "
        "[MAESTRO_CONDITIONED_AUDIO_TIMELINE_V1_END]"
    )


def _synthesize_single_ptbr_adr(
    project_dir: Path,
    take_id: str,
    preview: Path,
    spec: Dict[str, Any],
    result: Dict[str, Any],
    progress_cb=None,
) -> Path:
    """Generate one pt-BR voice turn and reject wording errors before LTX."""

    profile = spec.get("voiceProfile") if isinstance(spec.get("voiceProfile"), dict) else {}
    speaker = str(spec.get("speaker") or profile.get("speaker") or "personagem").strip()
    target_text = str(spec.get("text") or "").strip()
    reference_text = str(profile.get("referenceText") or "").strip()
    if not target_text or not reference_text:
        raise RuntimeError("Perfil Qwen3-TTS nao possui texto exato da fala ou da referencia.")

    trusted_root = Path(
        os.environ.get("MAESTRO_QWEN3_TTS_ROOT", r"C:\PemaraAI\qwen3-tts")
    ).resolve(strict=True)
    python = Path(
        str(profile.get("python") or trusted_root / ".venv" / "Scripts" / "python.exe")
    ).resolve(strict=True)
    model_dir = Path(
        str(profile.get("modelDir") or trusted_root / "models" / "Qwen3-TTS-12Hz-1.7B-Base")
    ).resolve(strict=True)
    reference = Path(str(profile.get("referenceAudio") or "")).resolve(strict=True)
    project_root = project_dir.resolve(strict=True)
    if not python.is_relative_to(trusted_root) or python.name.casefold() != "python.exe":
        raise RuntimeError("Runtime Qwen3-TTS ficou fora da raiz confiavel.")
    if not model_dir.is_relative_to(trusted_root) or not (model_dir / "model.safetensors").is_file():
        raise RuntimeError("Modelo Qwen3-TTS local nao foi validado.")
    if not reference.is_relative_to(project_root):
        raise RuntimeError("Referencia de voz Qwen3-TTS ficou fora do projeto.")

    worker = Path(__file__).with_name("qwen3_tts_ptbr_cli.py").resolve(strict=True)
    scratch = project_root / "audio" / "qwen3_tts_jobs"
    scratch.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    target_text_file = scratch / f".{take_id}_{token}_target.txt"
    reference_text_file = scratch / f".{take_id}_{token}_reference.txt"
    safe_speaker = re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", speaker).encode("ascii", "ignore").decode("ascii").casefold()).strip("_") or "personagem"
    for path, value in (
        (target_text_file, target_text),
        (reference_text_file, reference_text),
    ):
        with path.open("xb") as stream:
            stream.write(value.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    max_attempts = max(1, min(4, int(profile.get("maxSpeechAttempts") or 3)))
    base_seed = int(
        hashlib.sha256(f"{take_id}|{speaker}|{target_text}".encode("utf-8")).hexdigest()[:8],
        16,
    )
    generated_outputs: List[Path] = []
    accepted_candidates: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    selected_output: Path | None = None
    selected: Dict[str, Any] | None = None
    last_failure = "processo sem detalhe"
    try:
        for attempt in range(1, max_attempts + 1):
            if progress_cb is not None:
                progress_cb(
                    2,
                    f"Gerando e conferindo fala pt-BR (tentativa {attempt}/{max_attempts}).",
                )
            output = preview.with_name(
                f"{preview.stem}_qwen3tts_{safe_speaker}_{token[:12]}_a{attempt}.wav"
            )
            generated_outputs.append(output)
            command = [
                str(python),
                str(worker),
                "--model-dir",
                str(model_dir),
                "--reference-audio",
                str(reference),
                "--reference-text-file",
                str(reference_text_file),
                "--text-file",
                str(target_text_file),
                "--output",
                str(output),
                "--seed",
                str(base_seed + attempt - 1),
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=900,
                    check=False,
                    env=environment,
                )
            except subprocess.TimeoutExpired:
                last_failure = f"tentativa {attempt} excedeu 15 minutos"
                attempts.append({"attempt": attempt, "status": "TTS_TIMEOUT"})
                output.unlink(missing_ok=True)
                continue
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size < 4096:
                detail = (completed.stderr or completed.stdout or "").strip()[-1800:]
                last_failure = detail or f"tentativa {attempt} nao produziu audio valido"
                attempts.append({
                    "attempt": attempt,
                    "status": "TTS_PROCESS_ERROR",
                    "detail": last_failure,
                })
                output.unlink(missing_ok=True)
                continue
            generated_probe = _probe_audio_delivery_media(output)
            if not generated_probe["has_audio"]:
                last_failure = f"tentativa {attempt} entregou arquivo sem faixa de audio"
                attempts.append({"attempt": attempt, "status": "TTS_AUDIO_MISSING"})
                output.unlink(missing_ok=True)
                continue
            asr = _transcribe_ptbr_delivery(output)
            assessment = _assess_spoken_ptbr_asr(target_text, asr["transcript"])
            repetition_trimmed = False
            repetition_boundary = _ptbr_exact_repetition_boundary(target_text, asr)
            if not assessment["accepted_for_human_review"] and repetition_boundary is not None:
                _trim_ptbr_delivery_at(output, repetition_boundary)
                asr = _transcribe_ptbr_delivery(output)
                assessment = _assess_spoken_ptbr_asr(target_text, asr["transcript"])
                repetition_trimmed = True
            attempt_result = {
                "attempt": attempt,
                "seed": base_seed + attempt - 1,
                "status": assessment["status"],
                "exact": bool(assessment["exact"]),
                "transcript": asr["transcript"],
                "compact_similarity": float(assessment.get("compact_similarity", 1.0)),
                "repeated_tail_trimmed": repetition_trimmed,
            }
            attempts.append(attempt_result)
            candidate = {
                "output": output,
                "asr": asr,
                "assessment": assessment,
                "completed": completed,
                "attempt": attempt,
            }
            if assessment["exact"]:
                selected = candidate
                break
            if assessment["accepted_for_human_review"]:
                accepted_candidates.append(candidate)
                last_failure = (
                    f"tentativa {attempt} teve ambiguidade fonetica do ASR: "
                    f"{asr['transcript']!r}"
                )
                continue
            last_failure = (
                f"tentativa {attempt} alterou ou repetiu a fala: {asr['transcript']!r}"
            )
            output.unlink(missing_ok=True)

        if selected is None and accepted_candidates:
            selected = max(
                accepted_candidates,
                key=lambda item: float(item["assessment"].get("compact_similarity", 0.0)),
            )
        if selected is None:
            raise RuntimeError(
                "Gate de fala pt-BR reprovou todas as tentativas Qwen3-TTS. "
                f"Esperado: {target_text!r}; ultimo resultado: {last_failure}."
            )

        selected_output = selected["output"].resolve()
        selected_asr = selected["asr"]
        selected_assessment = selected["assessment"]
        selected_completed = selected["completed"]
        result["tts_generation"] = {
            "engine": "Qwen3-TTS-12Hz-1.7B-Base",
            "route": "local_zero_shot_voice_clone",
            "speaker": speaker,
            "text": target_text,
            "language": "Portuguese",
            "locale_required": "pt-BR",
            "locale_forbidden": "pt-PT",
            "reference_audio": str(reference),
            "reference_take": str(profile.get("referenceTake") or ""),
            "output": str(selected_output),
            "output_sha256": _sha256_file(selected_output),
            "asr_gate": {
                **selected_asr,
                "expected_normalized": selected_assessment["expected_normalized"],
                "status": selected_assessment["status"],
                "exact": bool(selected_assessment["exact"]),
                "accepted_for_human_review": True,
                "automatic_approval": False,
                "attempt": int(selected["attempt"]),
            },
            "attempts": attempts,
            "human_listening_required": True,
            "stdout_tail": (selected_completed.stdout or "").strip()[-800:],
        }
        return selected_output
    finally:
        target_text_file.unlink(missing_ok=True)
        reference_text_file.unlink(missing_ok=True)
        for generated_output in generated_outputs:
            if selected_output is None or generated_output.resolve() != selected_output:
                generated_output.unlink(missing_ok=True)


def _synthesize_take_ptbr_adr(
    project_dir: Path,
    take_id: str,
    preview: Path,
    spec: Dict[str, Any],
    result: Dict[str, Any],
    progress_cb=None,
) -> Path:
    """Generate one validated voice per dialogue speaker and assemble the IA2V clock."""

    dialogue_turns = spec.get("dialogueTurns")
    if not isinstance(dialogue_turns, list) or len(dialogue_turns) <= 1:
        return _synthesize_single_ptbr_adr(
            project_dir,
            take_id,
            preview,
            spec,
            result,
            progress_cb=progress_cb,
        )

    take_duration = float(spec.get("takeDurationSeconds") or 0.0)
    if take_duration <= 0.25:
        raise RuntimeError("Dialogo Qwen multipersonagem sem duracao valida do take.")
    generated_turns: List[Dict[str, Any]] = []
    assembly_turns: List[Dict[str, Any]] = []
    for index, turn in enumerate(dialogue_turns, start=1):
        if not isinstance(turn, dict):
            raise RuntimeError(f"Turno de dialogo Qwen {index} e invalido.")
        speaker = str(turn.get("speaker") or "").strip()
        text = str(turn.get("text") or "").strip()
        profile = turn.get("voiceProfile") if isinstance(turn.get("voiceProfile"), dict) else {}
        start = float(turn.get("dialogueStartSeconds") or 0.0)
        end = float(turn.get("dialogueEndSeconds") or 0.0)
        if not speaker or not text or not profile or end <= start:
            raise RuntimeError(f"Turno de dialogo Qwen {index} nao possui voz, texto ou janela completa.")
        if progress_cb is not None:
            progress_cb(
                2,
                f"Gerando e conferindo voz pt-BR de {speaker} ({index}/{len(dialogue_turns)}).",
            )
        turn_result: Dict[str, Any] = {}
        safe_turn_speaker = (
            re.sub(
                r"[^a-z0-9]+",
                "_",
                unicodedata.normalize("NFKD", speaker)
                .encode("ascii", "ignore")
                .decode("ascii")
                .casefold(),
            ).strip("_")
            or "personagem"
        )
        turn_preview = preview.with_name(
            f"{preview.stem}_turn{index:02d}_{safe_turn_speaker}.wav"
        )
        turn_output = _synthesize_single_ptbr_adr(
            project_dir,
            f"{take_id}_turn{index:02d}",
            turn_preview,
            {
                "strategy": "qwen_dialogue_turn",
                "speaker": speaker,
                "text": text,
                "voiceProfile": profile,
            },
            turn_result,
            progress_cb=None,
        )
        generation = (
            turn_result.get("tts_generation")
            if isinstance(turn_result.get("tts_generation"), dict)
            else {}
        )
        if not generation:
            raise RuntimeError(f"A voz pt-BR de {speaker} terminou sem proveniencia de validacao.")
        generated_turns.append(generation)
        assembly_turns.append({
            "speaker": speaker,
            "text": text,
            "dialogue_start_seconds": start,
            "dialogue_end_seconds": end,
            "output": str(turn_output),
        })

    alignment = _assemble_ptbr_conditioning_dialogue(
        assembly_turns,
        preview,
        duration_seconds=take_duration,
    )
    alignment_by_speaker = alignment.get("turns") if isinstance(alignment.get("turns"), list) else []
    for index, generation in enumerate(generated_turns):
        if index < len(alignment_by_speaker):
            generation["conditioning_alignment"] = alignment_by_speaker[index]
    all_exact = all(
        bool((item.get("asr_gate") or {}).get("exact"))
        for item in generated_turns
        if isinstance(item, dict)
    )
    result["tts_generation"] = {
        "engine": "Qwen3-TTS-12Hz-1.7B-Base",
        "route": "local_zero_shot_multispeaker_voice_clone",
        "speaker": ", ".join(str(item.get("speaker") or "") for item in generated_turns),
        "text": " ".join(str(item.get("text") or "") for item in generated_turns),
        "language": "Portuguese",
        "locale_required": "pt-BR",
        "locale_forbidden": "pt-PT",
        "output": str(preview.resolve()),
        "output_sha256": _sha256_file(preview.resolve()),
        "asr_gate": {
            "status": "ALL_TURNS_EXACT_TEXT_MATCH" if all_exact else "ALL_TURNS_ACCEPTED_FOR_HUMAN_REVIEW",
            "exact": all_exact,
            "accepted_for_human_review": True,
            "automatic_approval": False,
        },
        "turns": generated_turns,
        "conditioning_alignment": alignment,
        "human_listening_required": True,
    }
    return preview.resolve()


def _ffmpeg_ass_filter_path(path: Path) -> str:
    normalized = str(path.resolve()).replace("\\", "/")
    normalized = normalized.replace(":", r"\:").replace("'", r"\'")
    return f"ass=filename='{normalized}'"


def _apply_take_editorial_lettering(
    project_id: str,
    take_id: str,
    preview: Path,
    result: Dict[str, Any],
) -> Path:
    """Burn approved pt-BR editorial copy after H3, never through its text encoder."""

    generation_spec = _get_take_generation_spec(
        VIDEO_PROJECTS_ROOT,
        project_id,
        take_id,
    )
    lettering = generation_spec.get("editorialLettering")
    if not isinstance(lettering, dict) or not bool(lettering.get("enabled")):
        return preview.resolve(strict=True)
    if str(lettering.get("language") or "") != "pt-BR":
        raise RuntimeError("Lettering editorial recusado porque o idioma nao e pt-BR.")
    ass_file = Path(str(lettering.get("assFile") or "")).resolve(strict=True)
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve(strict=True)
    if not ass_file.is_relative_to(project_dir) or ass_file.suffix.lower() != ".ass":
        raise RuntimeError("Lettering editorial ficou fora do projeto autorizado.")

    preview = preview.resolve(strict=True)
    source_probe = _probe_audio_delivery_media(preview)
    destination = preview.with_name(f"{preview.stem}_lettering_ptbr_preview.mp4")
    temporary = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp{destination.suffix}"
    )
    ffmpeg = get_ffmpeg()
    if not nvenc_ok(ffmpeg):
        raise RuntimeError("H.264 NVENC indisponivel para compor o lettering pt-BR.")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(preview),
        "-vf",
        _ffmpeg_ass_filter_path(ass_file),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p7",
        "-tune",
        "hq",
        "-cq",
        "16",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size < 1024:
            detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(
                "Falha ao compor lettering editorial pt-BR: "
                f"{detail or 'ffmpeg sem detalhe'}"
            )
        delivery_probe = _probe_audio_delivery_media(temporary)
        if (
            int(delivery_probe["video"].get("width") or 0)
            != int(source_probe["video"].get("width") or 0)
            or int(delivery_probe["video"].get("height") or 0)
            != int(source_probe["video"].get("height") or 0)
            or str(delivery_probe["video"].get("r_frame_rate") or "")
            != str(source_probe["video"].get("r_frame_rate") or "")
        ):
            raise RuntimeError("QC do lettering pt-BR alterou geometria ou FPS do take.")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    result["editorial_lettering"] = {
        "status": "BURNED_PTBR_PENDING_HUMAN_REVIEW",
        "required": bool(lettering.get("required", True)),
        "language": "pt-BR",
        "source": str(ass_file),
        "source_sha256": _sha256_file(ass_file),
        "output": str(destination),
        "output_sha256": _sha256_file(destination),
        "human_review_required": True,
    }
    return destination.resolve()


def _attach_take_audio_delivery(
    project_id: str,
    take_id: str,
    preview: Path,
    result: Dict[str, Any],
) -> Path:
    """Attach controlled ambience/ADR without changing any approved video frame."""

    spec = _get_take_audio_delivery_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
    preview = preview.resolve(strict=True)
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve(strict=True)
    if not preview.is_relative_to(project_dir):
        raise RuntimeError("Preview de audio ficou fora do projeto autorizado.")
    preview_probe = _probe_audio_delivery_media(preview)
    required = bool(spec.get("required"))
    dialogue_required = bool(spec.get("dialogueRequired"))
    audio_strategy = str(spec.get("strategy") or "").strip().lower()

    if audio_strategy == "minimax_h3_native_scene":
        if not preview_probe["has_audio"]:
            raise RuntimeError("MiniMax H3 nao entregou o audio nativo da cena solicitado.")
        result["audio_delivery"] = {
            "status": "NATIVE_MINIMAX_H3_SCENE_ATTACHED_PENDING_HUMAN_REVIEW",
            "required": True, "dialogue_required": dialogue_required,
            "narration_required": False, "music_required": False,
            "source": str(preview), "source_sha256": _sha256_file(preview),
            "source_kind": "minimax_h3_native_scene",
            "source_review_status": spec.get("sourceReviewStatus"),
            "human_listening_required": True, "video_frames_preserved": True,
            "output": str(preview), "output_sha256": _sha256_file(preview),
            "message": "Dialogo e efeitos nativos da cena preservados; ASR e escuta humana pendentes.",
        }
        review_pipeline = result.get("review_pipeline")
        if isinstance(review_pipeline, dict) and isinstance(review_pipeline.get("delivery"), dict):
            review_pipeline["delivery"]["audio"] = "minimax_h3_native_scene_aac"
            review_pipeline.setdefault("qc", {}).update(native_audio_expected=True, human_dialogue_listening_required=dialogue_required)
        return preview

    if audio_strategy == "minimax_h3_native_music":
        if not preview_probe["has_audio"]:
            raise RuntimeError("MiniMax H3 nao entregou a musica nativa solicitada.")
        result["audio_delivery"] = {
            "status": "NATIVE_MINIMAX_H3_MUSIC_ATTACHED_PENDING_HUMAN_REVIEW",
            "required": True,
            "dialogue_required": dialogue_required,
            "narration_required": False,
            "music_required": True,
            "source": str(preview),
            "source_sha256": _sha256_file(preview),
            "source_kind": "minimax_h3_native_music",
            "source_review_status": (
                "generated_pending_asr_and_human_listening"
                if dialogue_required
                else "generated_pending_human_listening"
            ),
            "music_direction": str(spec.get("musicDirection") or ""),
            "human_listening_required": True,
            "video_frames_preserved": True,
            "audio_codec": str(preview_probe["audio"].get("codec_name") or "aac"),
            "sample_rate": int(preview_probe["audio"].get("sample_rate") or 0),
            "channels": int(preview_probe["audio"].get("channels") or 0),
            "output": str(preview),
            "output_sha256": _sha256_file(preview),
            "message": (
                "Musica e dialogo nativos do MiniMax H3 incorporados ao video; ASR e escuta humana obrigatorios."
                if dialogue_required
                else "Musica nativa original do MiniMax H3 incorporada ao video; escuta humana obrigatoria."
            ),
        }
        review_pipeline = result.get("review_pipeline")
        if isinstance(review_pipeline, dict) and isinstance(review_pipeline.get("delivery"), dict):
            review_pipeline["delivery"]["audio"] = "minimax_h3_native_music_aac"
            review_qc = review_pipeline.setdefault("qc", {})
            if isinstance(review_qc, dict):
                review_qc["human_music_listening_required"] = True
                review_qc["native_audio_expected"] = True
                review_qc["human_dialogue_listening_required"] = dialogue_required
        return preview

    if audio_strategy == "minimax_h3_native_narration_ptbr":
        if not preview_probe["has_audio"]:
            raise RuntimeError("MiniMax H3 nao entregou a narracao nativa solicitada.")
        expected_text = str(spec.get("text") or "").strip()
        if not _normalize_spoken_ptbr(expected_text):
            raise RuntimeError("Take MiniMax H3 sem texto pt-BR esperado para o gate de narracao.")
        asr = _transcribe_ptbr_delivery(preview)
        assessment = _assess_spoken_ptbr_asr(expected_text, asr["transcript"])
        expected_normalized = assessment["expected_normalized"]
        exact_match = bool(assessment["exact"])
        near_homophone = bool(assessment["accepted_for_human_review"] and not exact_match)
        hard_text_mismatch = not exact_match and not near_homophone
        result["audio_delivery"] = {
            "status": (
                "NATIVE_MINIMAX_H3_NARRATION_PTBR_ATTACHED_AUDIO_TEXT_MISMATCH_PENDING_HUMAN_REVIEW"
                if hard_text_mismatch
                else "NATIVE_MINIMAX_H3_NARRATION_PTBR_ATTACHED_PENDING_HUMAN_REVIEW"
            ),
            "required": True,
            "dialogue_required": False,
            "narration_required": True,
            "source": str(preview),
            "source_sha256": _sha256_file(preview),
            "source_kind": "minimax_h3_native_offscreen_narration",
            "source_review_status": (
                "generated_exact_asr_pending_human_listening"
                if exact_match
                else "generated_asr_near_homophone_pending_human_listening"
                if near_homophone
                else "generated_asr_text_mismatch_pending_human_review"
            ),
            "speaker": str(spec.get("speaker") or ""),
            "text": expected_text,
            "language": "pt-BR",
            "forbidden_language": "pt-PT",
            "narrator_voice": spec.get("narratorVoice") or {},
            "audio_sync_revision": int(spec.get("audioSyncRevision") or 1),
            "human_listening_required": True,
            "video_frames_preserved": True,
            "audio_codec": str(preview_probe["audio"].get("codec_name") or "aac"),
            "sample_rate": int(preview_probe["audio"].get("sample_rate") or 0),
            "channels": int(preview_probe["audio"].get("channels") or 0),
            "output": str(preview),
            "output_sha256": _sha256_file(preview),
            "asr_gate": {
                **asr,
                "expected_normalized": expected_normalized,
                "status": assessment["status"],
                "exact": exact_match,
                "ambiguous_tokens": assessment["ambiguous_tokens"],
                "automatic_approval": False,
                "preserved_for_human_review": True,
            },
            "approval_blocked_by_audio_text": hard_text_mismatch,
            "message": (
                "Narracao masculina pt-BR nativa do MiniMax H3 incorporada ao video; familia em silencio; "
                + "escuta humana de "
                + (
                    "texto, voz adulta e sotaque paulista neutro pendente."
                    if exact_match
                    else "pronuncia, voz adulta e sotaque paulista neutro obrigatoria por ambiguidade do ASR."
                    if near_homophone
                    else "texto, voz adulta e sotaque paulista neutro obrigatoria porque o ASR encontrou palavras diferentes."
                )
            ),
        }
        review_pipeline = result.get("review_pipeline")
        if isinstance(review_pipeline, dict) and isinstance(review_pipeline.get("delivery"), dict):
            review_pipeline["delivery"]["audio"] = "minimax_h3_native_narration_ptbr_aac"
            review_qc = review_pipeline.setdefault("qc", {})
            if isinstance(review_qc, dict):
                review_qc["human_audio_sync_review_required"] = False
                review_qc["human_narrator_voice_review_required"] = True
                review_qc["visible_family_must_remain_silent"] = True
                review_qc["exact_dialogue_asr_match"] = exact_match
                review_qc["asr_near_homophone_requires_human_listening"] = near_homophone
                review_qc["audio_text_mismatch_requires_human_review"] = hard_text_mismatch
        return preview

    if not dialogue_required:
        if preview_probe["has_audio"]:
            result["audio_delivery"] = {
                "status": "NATIVE_AMBIENT_ATTACHED_PENDING_HUMAN_REVIEW",
                "required": required,
                "dialogue_required": False,
                "source_kind": "engine_native_environment_and_physical_events",
                "human_listening_required": True,
                "language": "none",
                "message": "Ambiente e efeitos nativos sincronizados; escuta humana pendente.",
            }
        elif required:
            result["audio_delivery"] = {
                "status": "MISSING_AMBIENT_AUDIO",
                "required": True,
                "dialogue_required": False,
                "source_kind": "missing",
                "human_listening_required": True,
                "language": "none",
                "message": "Imagem pronta, mas ambiente e efeitos ainda nao foram entregues.",
            }
        else:
            result["audio_delivery"] = {
                "status": "NOT_REQUIRED",
                "required": False,
                "dialogue_required": False,
                "source_kind": "none",
                "human_listening_required": False,
                "language": "none",
                "message": "Este contrato nao exige faixa de audio.",
            }
        return preview

    source_raw = str(spec.get("source") or "").strip()
    if (
        not source_raw
        and str(spec.get("sourceKind") or "") == "qwen3_tts_ptbr_voice_clone"
        and isinstance(spec.get("voiceProfile"), dict)
        and spec.get("voiceProfile")
    ):
        source_raw = str(
            _synthesize_take_ptbr_adr(project_dir, take_id, preview, spec, result)
        )
    if not source_raw:
        result["audio_delivery"] = {
            "status": "PENDING_VOICE_CAST",
            "required": True,
            "dialogue_required": True,
            "source_kind": "missing_voice_cast",
            "speaker": str(spec.get("speaker") or ""),
            "text": str(spec.get("text") or ""),
            "language": "pt-BR",
            "forbidden_language": "pt-PT",
            "human_listening_required": True,
            "message": "Imagem pronta; voz pt-BR ainda precisa ser definida e anexada.",
        }
        return preview

    audio_source = Path(source_raw).resolve(strict=True)
    if not audio_source.is_relative_to(project_dir):
        raise RuntimeError("Fonte ADR ficou fora do projeto autorizado.")
    source_probe = _probe_audio_delivery_media(audio_source)
    if not source_probe["has_audio"]:
        raise RuntimeError("A referencia ADR registrada nao possui faixa de audio.")
    target_duration = float(preview_probe["duration_seconds"] or 0.0)
    source_duration = float(source_probe["duration_seconds"] or 0.0)
    if target_duration <= 0.1 or source_duration <= 0.1:
        raise RuntimeError("Duracao invalida ao sincronizar a voz pt-BR.")
    speed = source_duration / target_duration
    destination = preview.with_name(f"{preview.stem}_audio_ptbr_preview.mp4")
    temporary = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp{destination.suffix}"
    )
    command = [
        get_ffmpeg(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(preview),
        "-i",
        str(audio_source),
        "-filter_complex",
        (
            f"[1:a:0]{_ffmpeg_atempo_chain(speed)},"
            f"loudnorm=I=-17:LRA=7:TP=-2,apad=pad_dur={target_duration:.6f}[a]"
        ),
        "-map",
        "0:v:0",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "256k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-t",
        f"{target_duration:.6f}",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size < 1024:
            detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(
                "Falha ao incorporar a voz pt-BR no preview: "
                f"{detail or 'ffmpeg sem detalhe'}"
            )
        delivery_probe = _probe_audio_delivery_media(temporary)
        original_video = preview_probe["video"]
        delivered_video = delivery_probe["video"]
        if (
            not delivery_probe["has_audio"]
            or int(delivery_probe["audio"].get("sample_rate") or 0) != 48000
            or int(delivery_probe["audio"].get("channels") or 0) != 2
            or int(delivered_video.get("width") or 0) != int(original_video.get("width") or 0)
            or int(delivered_video.get("height") or 0) != int(original_video.get("height") or 0)
            or str(delivered_video.get("r_frame_rate") or "") != str(original_video.get("r_frame_rate") or "")
        ):
            raise RuntimeError("QC do mix ADR alterou o video ou entregou audio invalido.")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    source_review_status = str(spec.get("sourceReviewStatus") or "pending_human_listening")
    delivery_status = (
        "ATTACHED_HUMAN_CONFIRMED_PTBR_SOURCE_PENDING_MIX_REVIEW"
        if source_review_status == "human_confirmed_pt_br"
        else "ATTACHED_PENDING_HUMAN_PTBR_LISTENING"
    )
    audio_delivery = {
        "status": delivery_status,
        "required": True,
        "dialogue_required": True,
        "source": str(audio_source),
        "source_sha256": _sha256_file(audio_source),
        "source_kind": str(spec.get("sourceKind") or ""),
        "source_review_status": source_review_status,
        "speaker": str(spec.get("speaker") or ""),
        "text": str(spec.get("text") or ""),
        "language": "pt-BR",
        "forbidden_language": "pt-PT",
        "speed_factor": round(speed, 6),
        "human_listening_required": True,
        "video_frames_preserved": True,
        "video_encoder": "stream_copy_from_h264_nvenc_delivery",
        "audio_codec": "aac",
        "sample_rate": 48000,
        "channels": 2,
        "output": str(destination),
        "output_sha256": _sha256_file(destination),
        "message": "Voz pt-BR e som incorporados; escuta humana do mix final obrigatoria.",
    }
    result["audio_delivery"] = audio_delivery
    review_pipeline = result.get("review_pipeline")
    if isinstance(review_pipeline, dict) and isinstance(review_pipeline.get("delivery"), dict):
        review_pipeline["delivery"]["path"] = str(destination)
        review_pipeline["delivery"]["sha256"] = audio_delivery["output_sha256"]
        review_pipeline["delivery"]["audio"] = "aac_ptbr_adr_retimed"
    sidecar = destination.with_suffix(f"{destination.suffix}.audio_delivery.json")
    sidecar_payload = {
        "schema_version": "1.0",
        "project_id": project_id,
        "take_id": take_id,
        "visual_source": str(preview),
        "visual_source_sha256": _sha256_file(preview),
        "audio_delivery": audio_delivery,
        "created_at_epoch": _t.time(),
    }
    temporary_sidecar = sidecar.with_name(f".{sidecar.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary_sidecar.open("xb") as stream:
            stream.write(json.dumps(sidecar_payload, ensure_ascii=False, indent=2).encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_sidecar, sidecar)
    finally:
        temporary_sidecar.unlink(missing_ok=True)
    return destination.resolve()


def _materialize_video_take_preview(
    project_id: str,
    take_id: str,
    job_id: str,
    result: Dict[str, Any],
    *,
    progress_cb=None,
    cancel_event=None,
    process_cb=None,
) -> Path:
    """Materialize and, when locked by policy, finish a native-24 preview at 60 FPS."""

    outputs = result.get("outputs") if isinstance(result, dict) else None
    video_output = next(
        (
            item for item in (outputs or [])
            if isinstance(item, dict) and item.get("kind") == "video"
        ),
        None,
    )
    if not video_output:
        raise RuntimeError("O motor terminou sem entregar um arquivo de video.")

    job = _GEN_JOB_STORE.get(job_id) or {}
    selected_model = str(result.get("model") or job.get("model") or "")
    is_ltx25 = selected_model == _LTX25_MODEL_NAME
    is_minimax_h3 = _is_minimax_h3_model(selected_model)
    output_path = str(video_output.get("path") or "").strip()
    if output_path:
        studio_output_root = Path(STUDIO_OUTPUT_DIR).resolve()
        source = (studio_output_root / output_path).resolve()
        if not source.is_relative_to(studio_output_root):
            raise RuntimeError("O caminho entregue pelo motor ficou fora do output autorizado do Studio.")
    else:
        source_raw = _safe_comfy_output_path(
            str(video_output.get("filename") or ""),
            str(video_output.get("subfolder") or ""),
            str(video_output.get("type") or "output"),
        )
        if not source_raw:
            raise RuntimeError("O caminho entregue pelo motor e invalido ou ficou fora do output autorizado.")
        source = Path(source_raw).resolve()
    if not source.is_file() or source.suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise RuntimeError("O arquivo final do motor nao foi encontrado no output autorizado.")
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve()
    projects_root = VIDEO_PROJECTS_ROOT.resolve()
    if not project_dir.is_relative_to(projects_root) or not project_dir.is_dir():
        raise RuntimeError("Projeto de video invalido ao registrar o resultado.")
    review_policy = (
        _load_ltx_review_pipeline_policy(project_dir, selected_model)
        if is_ltx25 or is_minimax_h3
        else None
    )
    source_duration_qc: Dict[str, Any] = {"status": "NOT_APPLICABLE"}
    source_motion_qc = _inspect_video_temporal_motion(source)
    source_cast_qc: Dict[str, Any] = {"status": "NOT_APPLICABLE"}
    if (is_ltx25 or is_minimax_h3) and bool(job.get("cast_contract_known")):
        source_cast_qc = _inspect_video_human_cast_surge(
            source,
            len(list(job.get("expected_human_cast") or [])),
            expected_non_human_count=len(
                list(job.get("expected_non_human_cast") or [])
            ),
        )
        result.setdefault("quality_gate", {})["human_cast_surge"] = source_cast_qc

    safe_take_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(take_id or ""))[:32] or "take"
    safe_job_id = re.sub(r"[^A-Za-z0-9_-]+", "", str(job_id or ""))[:16] or uuid.uuid4().hex[:16]
    destination_dir = (project_dir / "takes" / "maestro_generated").resolve()
    if not destination_dir.is_relative_to(project_dir):
        raise RuntimeError("Destino do preview ficou fora do projeto.")
    destination_dir.mkdir(parents=True, exist_ok=True)
    engine_slug = "ltx25" if is_ltx25 else "minimax_h3"
    if review_policy is not None:
        native_destination = destination_dir / (
            f"take_{safe_take_id}_{safe_job_id}_{engine_slug}_native24.mp4"
        )
        destination = destination_dir / (
            f"take_{safe_take_id}_{safe_job_id}_{engine_slug}_rife425_retime60_preview.mp4"
        )
    else:
        destination = destination_dir / (
            f"take_{safe_take_id}_{safe_job_id}_{engine_slug}_preview{source.suffix.lower()}"
        )
        native_destination = destination

    def file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    source_size = source.stat().st_size
    source_sha256 = file_sha256(source)
    if source_size <= 0:
        raise RuntimeError("O arquivo final do motor esta vazio.")
    native_temporary = native_destination.with_name(
        f".{native_destination.name}.{uuid.uuid4().hex}.tmp"
    )
    if native_destination.exists():
        if not native_destination.is_file() or native_destination.stat().st_size != source_size:
            raise RuntimeError("Ja existe outro arquivo no destino reservado para este job.")
        if file_sha256(native_destination) != source_sha256:
            raise RuntimeError("O destino reservado para este job possui conteudo diferente.")
    else:
        try:
            with source.open("rb") as input_stream, native_temporary.open("xb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
                output_stream.flush()
                os.fsync(output_stream.fileno())
            if (
                native_temporary.stat().st_size != source_size
                or file_sha256(native_temporary) != source_sha256
            ):
                raise RuntimeError("A copia do preview do motor ficou incompleta.")
            os.replace(native_temporary, native_destination)
        finally:
            native_temporary.unlink(missing_ok=True)

    review_pipeline: Dict[str, Any] = {}
    if review_policy is not None:
        review_pipeline = _run_ltx_review_pipeline(
            source=native_destination,
            output=destination,
            project_dir=project_dir,
            policy=review_policy,
            ffmpeg=get_ffmpeg(),
            progress_cb=progress_cb,
            cancel_event=cancel_event,
            process_cb=process_cb,
            release_gpu_cb=_prepare_comfy_gpu_for_mova,
        )
        review_pipeline["native_preview_path"] = str(native_destination.resolve())
        result["review_pipeline"] = review_pipeline
        motion_qc = _inspect_video_temporal_motion(destination)
    else:
        motion_qc = source_motion_qc

    registered_size = destination.stat().st_size
    registered_sha256 = file_sha256(destination)

    sidecar = destination.with_suffix(f"{destination.suffix}.json")
    sidecar_payload = {
        "schema_version": "1.0",
        "project_id": project_id,
        "take_id": take_id,
        "job_id": job_id,
        "source": {
            "filename": str(video_output.get("filename") or ""),
            "path": output_path,
            "subfolder": str(video_output.get("subfolder") or ""),
            "type": str(video_output.get("type") or "output"),
            "sha256": source_sha256,
            "size_bytes": source_size,
        },
        "registered_preview": {
            "path": str(destination.resolve()),
            "sha256": registered_sha256,
            "size_bytes": registered_size,
        },
        "generation": {
            "model": str(result.get("model") or job.get("model") or ""),
            "seed": (
                result.get("seed")
                if result.get("seed") is not None
                else job.get("seed")
            ),
            "prompt_id": str(job.get("prompt_id") or result.get("prompt_id") or ""),
            "width": job.get("width"),
            "height": job.get("height"),
            "frames": job.get("frames"),
            "fps": job.get("fps"),
            "profile": str(job.get("generation_profile") or ""),
            "camera_pose": str(job.get("camera_pose") or ""),
            "camera_speed": job.get("camera_speed"),
            "video_conditioning_profile": str(
                job.get("video_conditioning_profile") or ""
            ),
        },
        "source_motion_qc": source_motion_qc,
        "source_audiovisual_duration_qc": source_duration_qc,
        "source_human_cast_qc": source_cast_qc,
        "motion_qc": motion_qc,
        "review_pipeline": review_pipeline,
        "registered_at_epoch": _t.time(),
    }
    sidecar_temporary = sidecar.with_name(f".{sidecar.name}.{uuid.uuid4().hex}.tmp")
    try:
        encoded = json.dumps(sidecar_payload, ensure_ascii=False, indent=2).encode("utf-8")
        with sidecar_temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(sidecar_temporary, sidecar)
    finally:
        sidecar_temporary.unlink(missing_ok=True)
    return destination.resolve()


def _preserve_video_candidate_after_audio_failure(
    project_id: str,
    take_id: str,
    preview: Path,
    result: Dict[str, Any],
    error: RuntimeError,
) -> Path:
    """Keep a completed MP4 visible while blocking its audio approval."""

    preview = preview.resolve(strict=True)
    project_dir = (VIDEO_PROJECTS_ROOT / project_id).resolve(strict=True)
    if not preview.is_relative_to(project_dir):
        raise RuntimeError("Candidato de video ficou fora do projeto durante a recuperacao de audio.")
    try:
        probe = _probe_audio_delivery_media(preview)
    except Exception:
        probe = {"audio": {}, "has_audio": False}
    audio = probe.get("audio") if isinstance(probe.get("audio"), dict) else {}
    warning = {
        "stage": "audio_delivery",
        "status": "CANDIDATE_PRESERVED_QC_BLOCKED",
        "error": str(error)[:1800],
        "automatic_approval": False,
        "human_review_required": True,
    }
    warnings = result.setdefault("postprocess_warnings", [])
    if isinstance(warnings, list):
        warnings.append(warning)
    result["approval_status"] = "PENDING_HUMAN_REVIEW_AUDIO_BLOCKED"
    result["audio_delivery"] = {
        "status": "NATIVE_LTX_AV_CANDIDATE_PRESERVED_AUDIO_QC_FAILED",
        "ready": False,
        "required": True,
        "dialogue_required": True,
        "source": str(preview),
        "source_sha256": _sha256_file(preview),
        "source_kind": "completed_audiovisual_candidate_with_blocked_audio_qc",
        "source_review_status": "audio_qc_failed_pending_human_review",
        "human_listening_required": True,
        "automatic_approval": False,
        "approval_blocked": True,
        "has_audio": bool(probe.get("has_audio")),
        "audio_codec": str(audio.get("codec_name") or ""),
        "sample_rate": int(audio.get("sample_rate") or 0),
        "channels": int(audio.get("channels") or 0),
        "output": str(preview),
        "output_sha256": _sha256_file(preview),
        "qc_error": str(error)[:1800],
        "message": (
            "O video terminou e foi preservado. O controle de audio falhou; "
            "a aprovacao continua bloqueada ate revisao humana."
        ),
    }
    review_pipeline = result.get("review_pipeline")
    if isinstance(review_pipeline, dict):
        review_pipeline["status"] = "PENDING_HUMAN_REVIEW_AUDIO_BLOCKED"
        review_qc = review_pipeline.setdefault("qc", {})
        if isinstance(review_qc, dict):
            review_qc["human_audio_review_required"] = True
            review_qc["audio_qc_passed"] = False
            review_qc["audio_qc_error"] = str(error)[:1800]
    bk_log(
        f"Candidato preservado apos falha de audio {project_id}/{take_id}: {str(error)[:500]}"
    )
    return preview


def _finalize_video_take_candidate(
    project_id: str,
    take_id: str,
    job_id: str,
    result: Dict[str, Any],
    *,
    progress_cb,
    cancel_event: threading.Event,
    process_cb,
) -> tuple[Path, bool]:
    """Materialize once, then run non-destructive QC around the preserved file."""

    preview = _materialize_video_take_preview(
        project_id,
        take_id,
        job_id,
        result,
        progress_cb=progress_cb,
        cancel_event=cancel_event,
        process_cb=process_cb,
    )
    progress_cb(99, "Render preservado no projeto; compondo lettering pt-BR aprovado.")
    preview = _apply_take_editorial_lettering(project_id, take_id, preview, result)
    progress_cb(99, "Lettering validado; verificando audio e fala.")
    try:
        preview = _attach_take_audio_delivery(project_id, take_id, preview, result)
        audio_blocked = bool(
            (result.get("audio_delivery") or {}).get("approval_blocked_by_audio_text")
        )
    except RuntimeError as exc:
        preview = _preserve_video_candidate_after_audio_failure(
            project_id,
            take_id,
            preview,
            result,
            exc,
        )
        audio_blocked = True
    progress_cb(
        99,
        (
            "Candidato preservado; audio aguarda decisao humana."
            if audio_blocked
            else "Candidato preservado; finalizando registro no Maestro."
        ),
    )
    return preview, audio_blocked


def _video_take_completion_message(result: Dict[str, Any], audio_blocked: bool) -> str:
    if audio_blocked:
        return (
            "Video preservado e pronto para revisao; audio/fala bloqueados para decisao humana."
        )
    audio_delivery = result.get("audio_delivery")
    if not isinstance(audio_delivery, dict):
        return "Take pronto para QC humano; upscale continua bloqueado ate aprovacao."
    audio_status = str(audio_delivery.get("status") or "")
    if audio_status.startswith(("ATTACHED_", "NATIVE_")):
        return "Take com audio pronto para QC humano; upscale continua bloqueado ate aprovacao."
    if bool(audio_delivery.get("required")):
        return "Imagem pronta; audio/voz ainda pendente e aprovacao bloqueada."
    return "Take pronto para QC humano; upscale continua bloqueado ate aprovacao."


def _launch_video_take_worker(
    job_id: str,
    project_id: str,
    take_id: str,
    spec: Dict[str, Any],
    base_bytes: bytes,
    seed: int,
    *,
    audio_conditioning_bytes: bytes | None = None,
    audio_conditioning_name: str = "",
    end_bytes: bytes | None = None,
    recovered: bool = False,
    resume_prompt_id: str = "",
) -> None:
    cancel_event = threading.Event()
    queue_position = _enqueue_video_take_turn(job_id)
    try:
        with _ACTIVE_GEN_JOBS_LOCK:
            _ACTIVE_GEN_JOBS[job_id] = {"cancel_event": cancel_event}
        _set_gen_job(
            job_id,
            status="queued",
            queue_mode="serial",
            queue_position=queue_position,
            worker_pid=os.getpid(),
            message=(
                f"Na fila serial de takes (posicao {queue_position}); "
                "um render de video sera executado por vez."
            ),
        )
    except Exception:
        with _ACTIVE_GEN_JOBS_LOCK:
            _ACTIVE_GEN_JOBS.pop(job_id, None)
        _release_video_take_turn(job_id)
        raise

    def update(pct: int, msg: str) -> None:
        if cancel_event.is_set():
            raise GenerationCancelled("Geracao cancelada pelo proprietario.")
        _set_gen_job(job_id, progress=max(1, min(100, int(pct))), message=msg)

    def record_prompt_id(prompt_id: str) -> None:
        _set_gen_job(job_id, prompt_id=prompt_id, message="Workflow enviado ao motor de video.")

    def record_process(process) -> None:
        with _ACTIVE_GEN_JOBS_LOCK:
            active = _ACTIVE_GEN_JOBS.get(job_id)
            if active is None:
                return
            if process is None:
                active.pop("process", None)
            else:
                active["process"] = process

    def worker() -> None:
        resource_wait_count = 0
        dynamic_vram_recovery_count = 0
        lease_acquired = False
        resolved_audio_conditioning_bytes = audio_conditioning_bytes
        resolved_audio_conditioning_name = audio_conditioning_name
        synthesized_audio_result: Dict[str, Any] = {}
        try:
            _wait_for_video_take_turn(job_id, cancel_event)
            selected_model = _video_take_model_for_spec(spec)
            generation_resume_prompt_id = resume_prompt_id
            generation_seed = (
                random.randrange(1, 2**63)
                if _is_minimax_h3_model(selected_model) and int(seed) < 0
                else seed
            )
            if recovered:
                _wait_for_recovered_video_engine(job_id, cancel_event, selected_model)
            _wait_for_upscale_gate(job_id, cancel_event)
            _wait_for_gpu_lease(
                job_id,
                operation="video_take",
                project_id=project_id,
                take_id=take_id,
                cancel_event=cancel_event,
            )
            lease_acquired = True
            focus_receipt = _prepare_render_focus(
                Path(BASE_DIR),
                job_id=job_id,
                progress_cb=update,
            )
            _set_gen_job(
                job_id,
                render_focus=focus_receipt,
                render_focus_receipt=focus_receipt.get("receiptPath"),
            )
            while True:
                _set_gen_job(
                    job_id,
                    status="running",
                    queue_position=0,
                    resource_wait=False,
                    message="Iniciando geracao do take; slot serial exclusivo adquirido.",
                    started_at=_t.time(),
                )
                _set_take_generation_state(
                    VIDEO_PROJECTS_ROOT, project_id, take_id, status="GENERATING", job_id=job_id
                )
                try:
                    generation_prompt = str(spec["prompt"])
                    minimax_control = (
                        spec.get("minimaxAnchorControl")
                        if isinstance(spec.get("minimaxAnchorControl"), dict)
                        else {}
                    )
                    reference_images = [
                        (Path(path).read_bytes(), Path(path).name)
                        for path in minimax_control.get("referenceImages", [])
                    ]
                    reference_video = minimax_control.get("referenceVideo")
                    reference_video_path = Path(reference_video) if reference_video else None
                    wan_animate_control = (
                        spec.get("wanAnimateControl")
                        if isinstance(spec.get("wanAnimateControl"), dict)
                        else {}
                    )
                    pose_video = wan_animate_control.get("poseVideo")
                    pose_video_path = Path(pose_video) if pose_video else None
                    result = _run_generative(
                        prompt=generation_prompt,
                        mode="video",
                        model=selected_model,
                        negative=spec["negative"],
                        lora="",
                        lora_strength=0.0,
                        width=int(spec.get("width") or 768),
                        height=int(spec.get("height") or 432),
                        steps=int(spec.get("steps") or 16),
                        guidance=float(spec.get("guidance") or 6.0),
                        seed=generation_seed,
                        frames=int(spec["frames"]),
                        fps=spec["fps"],
                        provider="",
                        duration=spec["durationSeconds"],
                        prompt_influence=0.5,
                        loop=False,
                        base_image_bytes=base_bytes,
                        base_image_name=spec["keyframeName"],
                        audio_conditioning_bytes=resolved_audio_conditioning_bytes,
                        audio_conditioning_name=resolved_audio_conditioning_name,
                        end_image_bytes=end_bytes,
                        end_image_name=str(spec.get("endKeyframeName") or ""),
                        minimax_reference_images=reference_images,
                        minimax_reference_video_bytes=(
                            reference_video_path.read_bytes()
                            if reference_video_path is not None
                            else None
                        ),
                        minimax_reference_video_name=(
                            reference_video_path.name
                            if reference_video_path is not None
                            else ""
                        ),
                        minimax_reference_mode=str(minimax_control.get("mode") or ""),
                        pose_video_bytes=(
                            pose_video_path.read_bytes()
                            if pose_video_path is not None
                            else None
                        ),
                        pose_video_name=(
                            pose_video_path.name
                            if pose_video_path is not None
                            else ""
                        ),
                        camera_pose=str(spec.get("cameraPose") or ""),
                        camera_speed=float(spec.get("cameraSpeed") or 0.8),
                        video_conditioning_profile=str(
                            spec.get("videoConditioningProfile") or "identity_locked"
                        ),
                        strict_video_model=True,
                        allow_validated_video_geometry=True,
                        progress_cb=update,
                        cancel_event=cancel_event,
                        prompt_id_cb=record_prompt_id,
                        process_cb=record_process,
                        resume_prompt_id=generation_resume_prompt_id,
                        visual_only_pass=bool(spec.get("visualOnlyPass")),
                        allow_minimax_h3_owner_long_window=(
                            str(spec.get("generationProfile") or "")
                            == "minimax_h3_fl2va_int8_owner_30s_native_av_720p24"
                        ),
                        enable_minimax_h3_native_audio=(
                            str(spec.get("audioStrategy") or "").strip().lower()
                            in {
                                "minimax_h3_native_narration_ptbr",
                                "minimax_h3_native_music",
                                "minimax_h3_native_scene",
                            }
                        ),
                        enable_minimax_h3_live_preview=bool(
                            spec.get("h3LivePreview", False)
                        ),
                        h3_quality_profile=str(spec.get("h3QualityProfile") or ""),
                        expected_human_cast=list(spec.get("expectedHumanCast") or []),
                        cast_contract_known=bool(spec.get("castContractKnown")),
                        distinct_story_events=max(1, int(spec.get("distinctStoryEvents") or 1)),
                    )
                    if isinstance(synthesized_audio_result.get("tts_generation"), dict):
                        result["tts_generation"] = synthesized_audio_result["tts_generation"]
                    break
                except ComfyDynamicVramFault:
                    if (
                        not _is_minimax_h3_model(selected_model)
                        or dynamic_vram_recovery_count >= 1
                    ):
                        raise
                    dynamic_vram_recovery_count += 1
                    _set_gen_job(
                        job_id,
                        progress=8,
                        message=(
                            "Recuperando a memoria do MiniMax H3; o Studio repetira "
                            "o mesmo take automaticamente uma unica vez."
                        ),
                        prompt_id=None,
                        dynamic_vram_recovery_count=dynamic_vram_recovery_count,
                    )
                    _recover_comfy_dynamic_vram()
                    generation_resume_prompt_id = ""
                    continue
            preview_path, audio_blocked = _finalize_video_take_candidate(
                project_id,
                take_id,
                job_id,
                result,
                progress_cb=update,
                cancel_event=cancel_event,
                process_cb=record_process,
            )
            _set_take_generation_state(
                VIDEO_PROJECTS_ROOT,
                project_id,
                take_id,
                status="READY",
                job_id=job_id,
                result=result,
                preview_path=preview_path,
            )
            _set_gen_job(
                job_id,
                status="done",
                progress=100,
                resource_wait=False,
                resource_wait_count=resource_wait_count,
                dynamic_vram_recovery_count=dynamic_vram_recovery_count,
                message=_video_take_completion_message(result, audio_blocked),
                result=result,
            )
        except GenerationCancelled as exc:
            try:
                _set_gen_job(
                    job_id,
                    status="canceled",
                    message="Take cancelado pelo proprietario.",
                    error=str(exc),
                )
            except Exception:
                logging.exception("Falha ao persistir cancelamento do take job=%s", job_id)
            try:
                _set_take_generation_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="ERROR",
                    job_id=job_id,
                    error=str(exc),
                )
            except Exception:
                logging.exception(
                    "Falha ao reconciliar take cancelado %s/%s job=%s",
                    project_id,
                    take_id,
                    job_id,
                )
        except Exception as exc:
            bk_log(f"ERRO take job {project_id}/{take_id} {job_id}: {exc}")
            logging.error(f"take job {project_id}/{take_id} {job_id}: {exc}", exc_info=True)
            try:
                _set_gen_job(job_id, status="error", progress=100, message="Erro no take.", error=str(exc))
            except Exception:
                logging.exception("Falha ao persistir erro terminal do take job=%s", job_id)
            try:
                _set_take_generation_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="ERROR",
                    job_id=job_id,
                    error=str(exc),
                )
            except Exception:
                logging.exception(
                    "Falha ao reconciliar take com erro %s/%s job=%s",
                    project_id,
                    take_id,
                    job_id,
                )
        finally:
            if lease_acquired:
                _GPU_LEASE_REGISTRY.release(job_id)
            with _ACTIVE_GEN_JOBS_LOCK:
                _ACTIVE_GEN_JOBS.pop(job_id, None)
            _release_video_take_turn(job_id)

    thread = threading.Thread(
        target=worker,
        daemon=True,
        name=f"studio-take-{project_id[:16]}-{take_id}-{job_id[:8]}",
    )
    try:
        thread.start()
    except Exception:
        with _ACTIVE_GEN_JOBS_LOCK:
            _ACTIVE_GEN_JOBS.pop(job_id, None)
        _release_video_take_turn(job_id)
        raise


def _wait_for_comfy_idle_before_upscale(job_id: str, cancel_event: threading.Event) -> None:
    """Drain submitted ComfyUI work before the chunked neural FHD pipeline starts."""

    last_message = ""
    while True:
        if cancel_event.is_set():
            raise GenerationCancelled("Upscale cancelado antes de usar a GPU.")
        try:
            queue_payload = _comfy_request("/queue", timeout=10)
            running = _comfy_queue_prompt_order(queue_payload, "queue_running")
            pending = _comfy_queue_prompt_order(queue_payload, "queue_pending")
        except Exception as exc:
            raise RecoverableUpscaleError(
                "UPSCALE_COMFY_UNAVAILABLE",
                f"ComfyUI indisponivel antes do upscale; tentativa pode ser repetida: {exc}",
            ) from exc
        if not running and not pending:
            return
        message = f"Upscale na fila; aguardando {len(running) + len(pending)} take(s) Wan."
        if message != last_message:
            _set_gen_job(job_id, status="queued", message=message)
            last_message = message
        cancel_event.wait(3.0)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _nearest_existing_parent(path: Path) -> Path:
    current = path.resolve()
    while not current.exists():
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(f"Nenhum ancestral existente para medir disco: {path}")
        current = parent
    return current


def _filesystem_key(path: Path) -> Tuple[str, int]:
    anchor = _nearest_existing_parent(path)
    drive = str(anchor.drive or anchor.anchor or "").lower()
    return drive, int(anchor.stat().st_dev)


def _upscale_disk_preflight(
    spec: Dict[str, Any],
    *,
    required_work_bytes: int,
) -> Dict[str, Any]:
    """Measure actual free space on every target filesystem before GPU work."""

    source = Path(spec["source"]).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Fonte do upscale ausente: {source}")
    required_work_bytes = int(required_work_bytes)
    if required_work_bytes <= 0:
        raise RecoverableUpscaleError(
            "UPSCALE_PREFLIGHT_INVALID",
            "A ferramenta nao informou uma estimativa valida de espaco temporario.",
        )
    requirements: Dict[Tuple[str, int], Dict[str, Any]] = {}

    def add_requirement(path: Path, amount: int, label: str) -> None:
        anchor = _nearest_existing_parent(path)
        key = _filesystem_key(anchor)
        item = requirements.setdefault(
            key,
            {"anchor": anchor, "required": 0, "labels": []},
        )
        item["required"] += max(0, int(amount))
        item["labels"].append(label)

    add_requirement(Path(spec["workDir"]), required_work_bytes, "workspace temporario")
    output_required = max(
        _VIDEO_UPSCALE_OUTPUT_MIN_BYTES,
        int(source.stat().st_size) * 3,
    )
    add_requirement(Path(spec["outputDir"]), output_required, "candidato e sidecar")
    for item in requirements.values():
        item["required"] += _VIDEO_UPSCALE_DISK_RESERVE_BYTES

    volumes = []
    for item in requirements.values():
        usage = shutil.disk_usage(item["anchor"])
        required = int(item["required"])
        free = int(usage.free)
        volume = {
            "path": str(item["anchor"]),
            "freeBytes": free,
            "requiredBytes": required,
            "labels": list(item["labels"]),
        }
        volumes.append(volume)
        if free < required:
            free_gib = free / 1024**3
            required_gib = required / 1024**3
            raise RecoverableUpscaleError(
                "UPSCALE_DISK_SPACE",
                (
                    f"Espaco insuficiente para upscale em {item['anchor']}: "
                    f"{free_gib:.2f} GiB livres, {required_gib:.2f} GiB exigidos. "
                    "Libere espaco e repita o job; nenhum candidato foi promovido."
                ),
            )
    return {
        "sourceBytes": int(source.stat().st_size),
        "requiredWorkBytes": required_work_bytes,
        "volumes": volumes,
    }


def _build_upscale_command(
    spec: Dict[str, Any],
    *,
    source_sha256: str,
    dry_run: bool,
) -> List[str]:
    _profile_id, profile_path, _target_width, _target_height = (
        _upscale_profile_for_spec(spec)
    )
    command = [
        sys.executable,
        str(_VIDEO_UPSCALE_TOOL),
        str(Path(spec["source"]).resolve()),
        str(Path(spec["outputDir"]).resolve()),
        "--name",
        str(spec["name"]),
        "--work-dir",
        str(Path(spec["workDir"]).resolve()),
        "--gpu",
        "0",
        "--profile",
        str(profile_path),
        "--comfy-url",
        COMFY_URL,
        "--chunk-size",
        str(_VIDEO_UPSCALE_CHUNK_SIZE),
        "--per-batch",
        str(_VIDEO_UPSCALE_PER_BATCH),
        "--expected-sha256",
        source_sha256,
    ]
    if dry_run:
        command.append("--dry-run")
    return command


def _upscale_profile_for_spec(
    spec: Dict[str, Any],
) -> Tuple[str, Path, int, int]:
    try:
        target_width = int(spec.get("targetWidth") or 1920)
        target_height = int(spec.get("targetHeight") or 1080)
    except (TypeError, ValueError) as exc:
        raise ValueError("Geometria final do upscale e invalida.") from exc
    profile_id = _required_upscale.profile_id(target_width, target_height)
    return (profile_id, _required_upscale.PROFILE_DIR / (profile_id + '.json'),
            target_width, target_height)


def _parse_upscale_plan(output: str) -> Tuple[str, int]:
    fingerprint_match = re.search(
        r"(?m)^\[plan\]\s+PROCESSING_FINGERPRINT=([A-Fa-f0-9]{64})\s*$",
        output,
    )
    work_match = re.search(
        r"(?m)^\[plan\]\s+REQUIRED_WORK_BYTES=(\d+)\s*$",
        output,
    )
    if not fingerprint_match or not work_match:
        raise RecoverableUpscaleError(
            "UPSCALE_PREFLIGHT_PROTOCOL",
            "Dry-run do upscale nao informou fingerprint e espaco exigido no protocolo v2.",
        )
    return fingerprint_match.group(1).upper(), int(work_match.group(1))


def _run_upscale_plan(command: List[str]) -> Tuple[str, int]:
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise RecoverableUpscaleError(
            "UPSCALE_PREFLIGHT_TIMEOUT",
            "Dry-run neural FHD excedeu cinco minutos sem iniciar GPU; a tentativa pode ser repetida.",
        ) from exc
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if completed.returncode:
        details = " | ".join(line.strip() for line in combined.splitlines()[-8:] if line.strip())
        raise RecoverableUpscaleError(
            "UPSCALE_PREFLIGHT_FAILED",
            f"Preflight neural FHD falhou sem iniciar GPU. {details}".strip(),
        )
    return _parse_upscale_plan(combined)


def _upscale_sidecar_is_rejected(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in {"rejected", "rejection", "rejected_at"} and bool(child):
                return True
            if normalized == "status" and str(child).strip().lower() == "rejected":
                return True
            if _upscale_sidecar_is_rejected(child):
                return True
    elif isinstance(value, list):
        return any(_upscale_sidecar_is_rejected(item) for item in value)
    return False


def _sidecar_candidate_path(payload: Dict[str, Any], sidecar: Path) -> Path:
    raw = payload.get("candidate")
    if isinstance(raw, dict):
        raw = raw.get("path") or raw.get("file")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Sidecar v2 sem candidate.")
    candidate = Path(raw.strip())
    if not candidate.is_absolute():
        candidate = sidecar.parent / candidate
    return candidate.resolve()


def _sidecar_source_sha256(payload: Dict[str, Any]) -> str:
    direct = str(payload.get("source_sha256") or "").strip()
    if direct:
        return direct.upper()
    fingerprint = payload.get("fingerprint")
    inputs = fingerprint.get("inputs") if isinstance(fingerprint, dict) else {}
    if not isinstance(inputs, dict):
        return ""
    source = inputs.get("source")
    if isinstance(source, dict):
        return str(source.get("sha256") or source.get("source_sha256") or "").strip().upper()
    return str(inputs.get("source_sha256") or "").strip().upper()


def _sidecar_profile_id(payload: Dict[str, Any]) -> str:
    direct = str(payload.get("profile_id") or "").strip()
    if direct:
        return direct
    fingerprint = payload.get("fingerprint")
    inputs = fingerprint.get("inputs") if isinstance(fingerprint, dict) else {}
    if not isinstance(inputs, dict):
        return ""
    profile = inputs.get("profile")
    if isinstance(profile, dict):
        return str(profile.get("id") or profile.get("profile_id") or "").strip()
    return str(inputs.get("profile_id") or "").strip()


def _validate_upscale_sidecar_v2(
    candidate: Path,
    sidecar: Path,
    *,
    expected_fingerprint: str,
    expected_source_sha256: str,
    expected_profile_id: str,
    output_dir: Path,
) -> Dict[str, Any]:
    output_dir = output_dir.resolve()
    candidate = candidate.resolve()
    sidecar = sidecar.resolve()
    if not candidate.is_relative_to(output_dir) or not sidecar.is_relative_to(output_dir):
        raise ValueError("Candidato ou sidecar saiu do diretorio de upscale.")
    if not candidate.is_file() or not sidecar.is_file():
        raise FileNotFoundError("Candidato ou sidecar v2 ausente.")
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Sidecar v2 invalido.")
    if str(payload.get("schema_version") or "") != "2.0":
        raise ValueError("Cache legado sem schema v2 nao pode ser reutilizado.")
    if str(payload.get("type") or "") != "pemara_hd_review_candidate_result":
        raise ValueError("Sidecar nao descreve candidato de review.")
    if str(payload.get("pipeline_version") or "") != _required_upscale.PIPELINE:
        raise ValueError("Sidecar pertence a pipeline diferente.")
    if _upscale_sidecar_is_rejected(payload):
        raise ValueError("Candidato ja foi rejeitado e nao pode voltar pelo cache.")
    technical = payload.get("technical_validation")
    if not isinstance(technical, dict) or str(technical.get("status") or "") != "technical_pass":
        raise ValueError("Candidato sem technical_pass.")
    if str(payload.get("qc_status") or "") != "technical_pass_visual_qc_pending":
        raise ValueError("Candidato sem gate visual pendente esperado.")
    fingerprint = str(payload.get("processing_fingerprint") or "").strip().upper()
    nested_fingerprint = payload.get("fingerprint")
    nested_value = (
        str(nested_fingerprint.get("value") or "").strip().upper()
        if isinstance(nested_fingerprint, dict)
        else ""
    )
    expected_fingerprint = expected_fingerprint.strip().upper()
    if fingerprint != expected_fingerprint or nested_value != expected_fingerprint:
        raise ValueError("Fingerprint do cache nao corresponde ao plano atual.")
    if _sidecar_source_sha256(payload) != expected_source_sha256.strip().upper():
        raise ValueError("Hash da fonte no sidecar nao corresponde ao take atual.")
    if _sidecar_profile_id(payload) != expected_profile_id:
        raise ValueError("Perfil do sidecar nao e o perfil neural FHD canonico.")
    registered_candidate = _sidecar_candidate_path(payload, sidecar)
    if registered_candidate != candidate:
        raise ValueError("Sidecar aponta para candidato diferente.")
    registered_sha = str(payload.get("candidate_sha256") or "").strip().upper()
    if not re.fullmatch(r"[A-F0-9]{64}", registered_sha):
        raise ValueError("Sidecar sem SHA-256 valido do candidato.")
    if _sha256_file(candidate) != registered_sha:
        raise ValueError("Hash do candidato nao confere com o sidecar.")
    if not _required_upscale.valid_receipt(candidate):
        raise ValueError("Candidato sem comprovação de SeedVR2 3B + RIFE60 + DLSS5.")
    return payload


def _find_reusable_upscale_candidate(
    spec: Dict[str, Any],
    *,
    expected_fingerprint: str,
    expected_source_sha256: str,
) -> Tuple[Path | None, Path | None]:
    """Find by exact v2 fingerprint; filenames and mtimes never grant reuse."""

    output_dir = Path(spec["outputDir"]).resolve()
    expected_profile_id, _profile_path, _target_width, _target_height = (
        _upscale_profile_for_spec(spec)
    )
    if not output_dir.is_dir():
        return None, None
    for sidecar in sorted(output_dir.glob("*.json"), key=lambda item: item.name.lower()):
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            if str(payload.get("processing_fingerprint") or "").strip().upper() != expected_fingerprint:
                continue
            candidate = _sidecar_candidate_path(payload, sidecar)
            _validate_upscale_sidecar_v2(
                candidate,
                sidecar,
                expected_fingerprint=expected_fingerprint,
                expected_source_sha256=expected_source_sha256,
                expected_profile_id=expected_profile_id,
                output_dir=output_dir,
            )
            return candidate, sidecar.resolve()
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            continue
    return None, None


def _assert_upscale_attempt_current(
    job_id: str,
    project_id: str,
    take_id: str,
    attempt: int,
    expected_source: Path,
) -> Dict[str, Any]:
    job = _get_gen_job(job_id) or {}
    job_status = str(job.get("status") or "")
    if job_status == "canceling":
        raise GenerationCancelled("Upscale cancelado pelo proprietario.")
    if job_status not in {"queued", "running"}:
        raise UpscaleAttemptObsolete(
            f"Job {job_id} nao esta mais ativo; resultado desta tentativa foi descartado."
        )
    try:
        current = _get_take_upscale_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
    except Exception as exc:
        raise UpscaleAttemptObsolete(
            f"Take {project_id}/{take_id} nao aceita mais esta tentativa de upscale: {exc}"
        ) from exc
    if str(current.get("lastJobId") or "") != job_id:
        raise UpscaleAttemptObsolete(
            f"Job obsoleto para {project_id}/{take_id}; outro job assumiu o take."
        )
    if int(current.get("upscaleAttempt") or 0) != int(attempt):
        raise UpscaleAttemptObsolete(
            f"Tentativa obsoleta para {project_id}/{take_id}; attempt={attempt}."
        )
    current_source = Path(current["source"]).resolve()
    if current_source != expected_source.resolve():
        raise UpscaleAttemptObsolete(
            f"A fonte canonica de {project_id}/{take_id} mudou durante o upscale."
        )
    return current


def _assert_upscale_source_hash_current(source: Path, expected_sha256: str) -> None:
    if _sha256_file(source) != expected_sha256.strip().upper():
        raise UpscaleAttemptObsolete(
            "A fonte do take mudou durante o upscale; o candidato desta tentativa foi descartado."
        )


def _upscale_frame_progress(line: str) -> Optional[tuple[int, int, float]]:
    match = re.search(
        r"collected\s+(\d+)/(\d+)\s+(?:UltraSharp|neural-upscale)\s+frames",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    completed = int(match.group(1))
    total = max(1, int(match.group(2)))
    value = max(0.0, min(100.0, completed * 100.0 / total))
    return completed, total, value


def _run_take_upscale_process(
    job_id: str,
    project_id: str,
    take_id: str,
    attempt: int,
    spec: Dict[str, Any],
    cancel_event: threading.Event,
) -> Tuple[Path, Path | None]:
    profile_id, profile_path, _target_width, _target_height = (
        _upscale_profile_for_spec(spec)
    )
    if not _VIDEO_UPSCALE_TOOL.is_file():
        raise FileNotFoundError(f"Pipeline de upscale ausente: {_VIDEO_UPSCALE_TOOL}")
    if not profile_path.is_file():
        raise FileNotFoundError(f"Perfil canonico de upscale ausente: {profile_path}")
    source = Path(spec["source"]).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Fonte do upscale ausente: {source}")
    _assert_upscale_attempt_current(job_id, project_id, take_id, attempt, source)
    source_sha256 = _sha256_file(source)
    plan_command = _build_upscale_command(
        spec,
        source_sha256=source_sha256,
        dry_run=True,
    )
    expected_fingerprint, required_work_bytes = _run_upscale_plan(plan_command)
    disk_preflight = _upscale_disk_preflight(
        spec,
        required_work_bytes=required_work_bytes,
    )
    _set_gen_job(
        job_id,
        processing_fingerprint=expected_fingerprint,
        source_sha256=source_sha256,
        upscale_profile=profile_id,
        disk_preflight=disk_preflight,
    )
    _assert_upscale_attempt_current(job_id, project_id, take_id, attempt, source)
    existing, existing_sidecar = _find_reusable_upscale_candidate(
        spec,
        expected_fingerprint=expected_fingerprint,
        expected_source_sha256=source_sha256,
    )
    if existing is not None:
        _assert_upscale_source_hash_current(source, source_sha256)
        _assert_upscale_attempt_current(job_id, project_id, take_id, attempt, source)
        _set_gen_job(
            job_id,
            progress=98,
            message="Candidato neural FHD identico recuperado por fingerprint e SHA-256.",
            upscale_cache_reused=True,
        )
        return existing, existing_sidecar

    _wait_for_comfy_idle_before_upscale(job_id, cancel_event)
    _assert_upscale_attempt_current(job_id, project_id, take_id, attempt, source)
    command = _build_upscale_command(
        spec,
        source_sha256=source_sha256,
        dry_run=False,
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creation_flags,
    )
    with _ACTIVE_GEN_JOBS_LOCK:
        active = _ACTIVE_GEN_JOBS.get(job_id)
        if active is not None:
            active["process"] = process

    candidate = None
    sidecar = None
    completed_fingerprint = ""
    reuse_marker = None
    progress_markers = (
        ("[plan]", 10, "Plano neural FHD validado."),
        ("[1/4]", 15, "Extraindo frames um-a-um, sem mudar a cadencia."),
        ("[2/4]", 25, "Cadencia nativa preservada."),
        ("[3/4]", 30, "Real-ESRGAN reconstruindo microdetalhe em chunks seguros."),
        ("[chunk", 30, "Real-ESRGAN reconstruindo microdetalhe em chunks seguros."),
        ("[4/4]", 88, "Codificando candidato FHD sem alterar a cadencia."),
        ("[encode]", 88, "Codificando candidato FHD sem alterar a cadencia."),
        ("[verify]", 96, "Validando o candidato FHD completo."),
    )
    output_tail = []
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.strip()
        if line:
            output_tail.append(line)
            del output_tail[:-30]
        if cancel_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            raise GenerationCancelled("Upscale cancelado pelo proprietario.")
        if "[chunk" in line.lower():
            try:
                _assert_upscale_attempt_current(
                    job_id,
                    project_id,
                    take_id,
                    attempt,
                    source,
                )
            except UpscaleAttemptObsolete:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise
        for marker, progress, message in progress_markers:
            if marker in line:
                _set_gen_job(job_id, progress=progress, message=message)
                break
        frame_progress = _upscale_frame_progress(line)
        if frame_progress:
            completed, total, value = frame_progress
            _set_gen_job(
                job_id,
                progress=30 + int(value * 0.58),
                message=f"Real-ESRGAN {completed}/{total} frames ({value:.0f}%).",
            )
        if line.startswith("[done] REVIEW_CANDIDATE="):
            candidate = Path(line.split("=", 1)[1].strip()).resolve()
        elif line.startswith("[done] SIDECAR="):
            sidecar = Path(line.split("=", 1)[1].strip()).resolve()
        elif line.startswith("[done] PROCESSING_FINGERPRINT="):
            completed_fingerprint = line.split("=", 1)[1].strip().upper()
        elif line.startswith("[done] REUSED="):
            reuse_marker = line.split("=", 1)[1].strip().lower() == "true"

    return_code = process.wait()
    if cancel_event.is_set():
        raise GenerationCancelled("Upscale cancelado pelo proprietario.")
    if return_code:
        details = " | ".join(output_tail[-5:])
        retryable_tokens = (
            "comfyui",
            "queue",
            "fila",
            "timeout",
            "timed out",
            "temporar",
            "no space",
            "disk full",
            "winerror 112",
            "espaco insuficiente",
        )
        if any(token in details.lower() for token in retryable_tokens):
            raise RecoverableUpscaleError(
                "UPSCALE_PIPELINE_RETRYABLE",
                (
                    f"Pipeline neural FHD foi interrompido por infraestrutura recuperavel "
                    f"(codigo {return_code}); os checkpoints foram preservados. {details}"
                ).strip(),
            )
        raise RuntimeError(f"Pipeline 1080p terminou com codigo {return_code}. {details}".strip())
    _assert_upscale_attempt_current(job_id, project_id, take_id, attempt, source)
    _assert_upscale_source_hash_current(source, source_sha256)
    if candidate is None or sidecar is None:
        raise RuntimeError("Pipeline v2 terminou sem registrar candidato e sidecar.")
    if completed_fingerprint != expected_fingerprint:
        raise RuntimeError("Pipeline v2 concluiu com fingerprint diferente do dry-run.")
    if reuse_marker is None:
        raise RuntimeError("Pipeline v2 nao informou se reutilizou cache.")
    _validate_upscale_sidecar_v2(
        candidate,
        sidecar,
        expected_fingerprint=expected_fingerprint,
        expected_source_sha256=source_sha256,
        expected_profile_id=profile_id,
        output_dir=Path(spec["outputDir"]),
    )
    _set_gen_job(job_id, upscale_cache_reused=bool(reuse_marker))
    return candidate, sidecar


def _install_recovered_upscale_order(job_ids: List[str]) -> None:
    """Keep recovered upscales in their persisted FIFO order across worker threads."""

    ordered = [str(job_id) for job_id in job_ids if str(job_id)]
    with _RECOVERED_UPSCALE_ORDER_CONDITION:
        for job_id in ordered:
            if job_id not in _RECOVERED_UPSCALE_ORDER:
                _RECOVERED_UPSCALE_ORDER.append(job_id)
        if _RECOVERED_UPSCALE_ORDER:
            # Hold Wan submissions for the whole recovered upscale backlog,
            # including the small hand-off gap between two worker threads.
            _VIDEO_UPSCALE_GATE.set()
        _RECOVERED_UPSCALE_ORDER_CONDITION.notify_all()


def _wait_for_recovered_upscale_turn(job_id: str, cancel_event: threading.Event) -> None:
    """Block later/direct upscales until every older recovered upscale has finished."""

    announced = False
    with _RECOVERED_UPSCALE_ORDER_CONDITION:
        while _RECOVERED_UPSCALE_ORDER and _RECOVERED_UPSCALE_ORDER[0] != job_id:
            if cancel_event.is_set():
                raise GenerationCancelled("Upscale cancelado enquanto aguardava sua vez na fila.")
            if not announced:
                _set_gen_job(
                    job_id,
                    status="queued",
                    message="Upscale aguardando sua vez na fila recuperada.",
                )
                announced = True
            _RECOVERED_UPSCALE_ORDER_CONDITION.wait(timeout=1.0)


def _release_recovered_upscale_turn(job_id: str) -> None:
    """Release one FIFO ticket and keep the GPU gate closed while backlog remains."""

    with _RECOVERED_UPSCALE_ORDER_CONDITION:
        try:
            _RECOVERED_UPSCALE_ORDER.remove(job_id)
        except ValueError:
            pass
        backlog_remains = bool(_RECOVERED_UPSCALE_ORDER)
        _RECOVERED_UPSCALE_ORDER_CONDITION.notify_all()
    if not backlog_remains:
        _VIDEO_UPSCALE_GATE.clear()


def _cleanup_completed_upscale_work(
    spec: Dict[str, Any],
    candidate: Path,
    sidecar: Path | None = None,
) -> None:
    """Delete only the verified candidate's disposable frame workspace."""

    work_dir = Path(spec["workDir"]).resolve()
    work_stem = candidate.stem
    if sidecar is not None and sidecar.is_file():
        try:
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            registered_stem = str(metadata.get("candidate_stem") or "").strip()
            if registered_stem and re.fullmatch(r"[A-Za-z0-9._-]{1,240}", registered_stem):
                work_stem = registered_stem
        except (json.JSONDecodeError, OSError):
            pass
    work_root = (work_dir / work_stem).resolve()
    if work_root.parent != work_dir:
        raise RuntimeError("Diretorio temporario de upscale saiu da raiz permitida.")
    if work_root.is_dir():
        shutil.rmtree(work_root)


def _launch_take_upscale_worker(
    job_id: str,
    project_id: str,
    take_id: str,
    spec: Dict[str, Any],
) -> None:
    cancel_event = threading.Event()
    attempt = int(spec.get("upscaleAttempt") or 0)
    profile_id, _profile_path, target_width, target_height = (
        _upscale_profile_for_spec(spec)
    )
    with _ACTIVE_GEN_JOBS_LOCK:
        _ACTIVE_GEN_JOBS[job_id] = {"cancel_event": cancel_event}

    def worker() -> None:
        lease_acquired = False
        try:
            _set_gen_job(
                job_id,
                status="queued",
                progress=2,
                message="Upscaling obrigatório aguardando a GPU.",
            )
            _wait_for_recovered_upscale_turn(job_id, cancel_event)
            _wait_for_gpu_lease(
                job_id,
                operation="video_upscale",
                project_id=project_id,
                take_id=take_id,
                cancel_event=cancel_event,
            )
            lease_acquired = True
            with _VIDEO_UPSCALE_LOCK:
                _VIDEO_UPSCALE_GATE.set()
                _wait_for_comfy_idle_before_upscale(job_id, cancel_event)
                if cancel_event.is_set():
                    raise GenerationCancelled("Upscale cancelado antes de iniciar.")
                _set_gen_job(
                    job_id,
                    status="running",
                    progress=5,
                    message="Iniciando SeedVR2 3B + RIFE60 + DLSS 5 para revisão.",
                    started_at=_t.time(),
                )
                _set_take_upscale_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="UPSCALING",
                    job_id=job_id,
                    attempt=attempt or None,
                )
                candidate, sidecar = _run_take_upscale_process(
                    job_id,
                    project_id,
                    take_id,
                    attempt,
                    spec,
                    cancel_event,
                )
                dlss5 = _finish_required_media(candidate, lease_job_id=job_id)
                sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
                sidecar_backup = Path(str(sidecar) + ".before_dlss5.json")
                if not sidecar_backup.exists():
                    shutil.copy2(sidecar, sidecar_backup)
                sidecar_payload["candidate_sha256"] = _sha256_file(candidate)
                sidecar_payload["dlss5_required"] = dlss5
                _dlss5._atomic_json(sidecar, sidecar_payload)
            result = {
                "ok": True,
                "mode": "video_upscale",
                "profile": profile_id,
                "attempt": attempt,
                "approvalStatus": "PENDING_HUMAN_REVIEW",
                "outputs": [{
                    "kind": "video",
                    "filename": str(candidate),
                    "width": target_width,
                    "height": target_height,
                    "fps": 60,
                }],
                "sidecar": str(sidecar) if sidecar else "",
            }
            _set_take_upscale_state(
                VIDEO_PROJECTS_ROOT,
                project_id,
                take_id,
                status="READY",
                job_id=job_id,
                attempt=attempt or None,
                output_path=candidate,
                sidecar_path=sidecar,
                result=result,
            )
            _set_gen_job(
                job_id,
                status="done",
                progress=100,
                message="Acabamento obrigatório a 60 FPS pronto para revisão; candidato ainda não está ativo.",
                result=result,
            )
            try:
                _cleanup_completed_upscale_work(spec, candidate, sidecar)
            except Exception:
                logging.exception(
                    "Falha ao limpar temporarios do upscale concluido %s/%s job=%s",
                    project_id,
                    take_id,
                    job_id,
                )
        except UpscaleAttemptObsolete as exc:
            try:
                _set_gen_job(
                    job_id,
                    status="canceled",
                    message="Tentativa de upscale obsoleta; candidato nao foi registrado.",
                    error=str(exc),
                    error_code="UPSCALE_ATTEMPT_OBSOLETE",
                    recoverable=False,
                )
            except Exception:
                logging.exception("Falha ao terminalizar tentativa obsoleta de upscale job=%s", job_id)
        except GenerationCancelled as exc:
            try:
                _set_gen_job(job_id, status="canceled", message="Upscale cancelado.", error=str(exc))
            except Exception:
                logging.exception("Falha ao persistir cancelamento do upscale job=%s", job_id)
            try:
                _set_take_upscale_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="CANCELED",
                    job_id=job_id,
                    attempt=attempt or None,
                    error=str(exc),
                )
            except Exception:
                logging.exception(
                    "Falha ao reconciliar take cancelado %s/%s job=%s",
                    project_id,
                    take_id,
                    job_id,
                )
        except RecoverableUpscaleError as exc:
            bk_log(f"BLOQUEIO recuperavel upscale {project_id}/{take_id} {job_id}: {exc}")
            logging.warning(
                "bloqueio recuperavel upscale %s/%s %s: %s",
                project_id,
                take_id,
                job_id,
                exc,
            )
            try:
                _set_gen_job(
                    job_id,
                    status="error",
                    progress=100,
                    message="Upscale bloqueado antes da entrega; pode ser repetido.",
                    error=str(exc),
                    error_code=exc.code,
                    recoverable=True,
                )
            except Exception:
                logging.exception("Falha ao persistir bloqueio recuperavel do upscale job=%s", job_id)
            try:
                _set_take_upscale_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="ERROR",
                    job_id=job_id,
                    attempt=attempt or None,
                    error=f"{exc.code}: {exc}",
                )
            except Exception:
                logging.exception(
                    "Falha ao reconciliar bloqueio recuperavel %s/%s job=%s",
                    project_id,
                    take_id,
                    job_id,
                )
        except Exception as exc:
            bk_log(f"ERRO upscale take {project_id}/{take_id} {job_id}: {exc}")
            logging.error("upscale take %s/%s %s", project_id, take_id, job_id, exc_info=True)
            try:
                _set_gen_job(
                    job_id,
                    status="error",
                    progress=100,
                    message="Erro no upscale 1080p.",
                    error=str(exc),
                    error_code="UPSCALE_PIPELINE_ERROR",
                    recoverable=False,
                )
            except Exception:
                logging.exception("Falha ao persistir erro terminal do upscale job=%s", job_id)
            try:
                _set_take_upscale_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="ERROR",
                    job_id=job_id,
                    attempt=attempt or None,
                    error=str(exc),
                )
            except Exception:
                logging.exception(
                    "Falha ao reconciliar take com erro %s/%s job=%s",
                    project_id,
                    take_id,
                    job_id,
                )
        finally:
            if lease_acquired:
                _GPU_LEASE_REGISTRY.release(job_id)
            with _ACTIVE_GEN_JOBS_LOCK:
                _ACTIVE_GEN_JOBS.pop(job_id, None)
            _release_recovered_upscale_turn(job_id)

    threading.Thread(
        target=worker,
        daemon=True,
        name=f"studio-upscale-{project_id[:16]}-{take_id}-{job_id[:8]}",
    ).start()


def _interrupted_video_take_jobs() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page = 1
    while True:
        payload = _GEN_JOB_STORE.list(page=page, page_size=100, status="interrupted")
        items.extend(
            job for job in payload.get("items", [])
            if job.get("project_id") and job.get("take_id")
            and str(job.get("job_kind") or "video_take") == "video_take"
        )
        if page * 100 >= int(payload.get("total", 0) or 0):
            break
        page += 1
    return sorted(items, key=lambda job: float(job.get("created_at", 0) or 0))


def _recover_interrupted_video_take_jobs() -> List[str]:
    """Resume only one explicitly opted-in interrupted take attempt."""

    resumed: List[str] = []
    for job in _interrupted_video_take_jobs():
        job_id = str(job.get("job_id") or "")
        project_id = str(job.get("project_id") or "")
        take_id = str(job.get("take_id") or "")
        try:
            spec = _get_take_generation_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
            if spec["status"] not in {"QUEUED", "GENERATING"}:
                continue
            if str(spec.get("lastJobId") or "") != job_id:
                continue
            if (
                job.get("auto_resume") is not True
                or int(job.get("resume_count", 0) or 0) >= 1
            ):
                retry_message = (
                    "Render interrompido pelo reinicio do Studio; "
                    "o take foi liberado para uma nova solicitacao."
                )
                _set_take_generation_state(
                    VIDEO_PROJECTS_ROOT,
                    project_id,
                    take_id,
                    status="ERROR",
                    job_id=job_id,
                    error=retry_message,
                )
                _set_gen_job(
                    job_id,
                    message=retry_message,
                    recoverable=True,
                )
                continue
            base_bytes = spec["keyframe"].read_bytes()
            audio_conditioning = spec.get("audioConditioning")
            audio_conditioning_bytes = (
                Path(audio_conditioning).read_bytes()
                if audio_conditioning is not None
                else None
            )
            end_keyframe = spec.get("endKeyframe")
            end_bytes = (
                Path(end_keyframe).read_bytes()
                if end_keyframe is not None
                else None
            )
            claimed = _GEN_JOB_STORE.claim_interrupted(
                job_id,
                worker_pid=os.getpid(),
                message="Tarefa recuperada apos reinicio do Studio.",
            )
            if not claimed:
                continue
            _set_take_generation_state(
                VIDEO_PROJECTS_ROOT, project_id, take_id, status="QUEUED", job_id=job_id
            )
            _launch_video_take_worker(
                job_id,
                project_id,
                take_id,
                spec,
                base_bytes,
                int(job.get("seed", -1) or -1),
                audio_conditioning_bytes=audio_conditioning_bytes,
                audio_conditioning_name=str(spec.get("audioConditioningName") or ""),
                end_bytes=end_bytes,
                recovered=True,
                resume_prompt_id=str(job.get("prompt_id") or ""),
            )
            resumed.append(job_id)
            bk_log(f"Take recuperado apos reinicio: {project_id}/{take_id} job={job_id}")
        except Exception as exc:
            logging.error("Falha ao recuperar take %s/%s job=%s: %s", project_id, take_id, job_id, exc, exc_info=True)
            current = _get_gen_job(job_id) or {}
            if current.get("status") == "queued" and int(current.get("worker_pid", 0) or 0) == os.getpid():
                _set_gen_job(job_id, status="error", progress=100, message="Falha ao recuperar take.", error=str(exc))
                try:
                    _set_take_generation_state(
                        VIDEO_PROJECTS_ROOT, project_id, take_id, status="ERROR", job_id=job_id, error=str(exc)
                    )
                except Exception:
                    logging.exception("Falha ao reconciliar take apos erro de recuperacao")
    return resumed


def _recover_interrupted_video_upscale_jobs() -> List[str]:
    resumed: List[str] = []
    prepared: List[Tuple[str, str, str, Dict[str, Any]]] = []
    page = 1
    interrupted: List[Dict[str, Any]] = []
    while True:
        payload = _GEN_JOB_STORE.list(page=page, page_size=100, status="interrupted")
        interrupted.extend(
            job for job in payload.get("items", [])
            if job.get("project_id") and job.get("take_id")
            and str(job.get("job_kind") or "") == "video_upscale"
        )
        if page * 100 >= int(payload.get("total", 0) or 0):
            break
        page += 1
    for job in sorted(interrupted, key=lambda item: float(item.get("created_at", 0) or 0)):
        job_id = str(job.get("job_id") or "")
        project_id = str(job.get("project_id") or "")
        take_id = str(job.get("take_id") or "")
        claimed = False
        try:
            spec = _get_take_upscale_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
            if spec["status"] != "UPSCALING" or str(spec.get("lastJobId") or "") != job_id:
                continue
            claimed_job = _GEN_JOB_STORE.claim_interrupted(
                job_id,
                worker_pid=os.getpid(),
                message="Upscale recuperado apos reinicio do Studio.",
            )
            if not claimed_job:
                continue
            claimed = True
            _set_take_upscale_state(
                VIDEO_PROJECTS_ROOT,
                project_id,
                take_id,
                status="QUEUED",
                job_id=job_id,
                attempt=int(spec.get("upscaleAttempt") or 0) or None,
            )
            prepared.append((job_id, project_id, take_id, spec))
            resumed.append(job_id)
            bk_log(f"Upscale recuperado apos reinicio: {project_id}/{take_id} job={job_id}")
        except Exception as exc:
            logging.error(
                "Falha ao recuperar upscale %s/%s job=%s: %s",
                project_id,
                take_id,
                job_id,
                exc,
                exc_info=True,
            )
            if claimed:
                try:
                    _set_gen_job(
                        job_id,
                        status="error",
                        progress=100,
                        message="Falha ao preparar recuperacao do upscale.",
                        error=str(exc),
                    )
                except Exception:
                    logging.exception("Falha ao terminalizar recovery do upscale job=%s", job_id)
                try:
                    _set_take_upscale_state(
                        VIDEO_PROJECTS_ROOT,
                        project_id,
                        take_id,
                        status="ERROR",
                        job_id=job_id,
                        attempt=int(spec.get("upscaleAttempt") or 0) or None,
                        error=str(exc),
                    )
                except Exception:
                    logging.exception(
                        "Falha ao reconciliar recovery do upscale %s/%s job=%s",
                        project_id,
                        take_id,
                        job_id,
                    )
    _install_recovered_upscale_order([item[0] for item in prepared])
    for job_id, project_id, take_id, spec in prepared:
        try:
            _launch_take_upscale_worker(job_id, project_id, take_id, spec)
        except Exception as exc:
            _release_recovered_upscale_turn(job_id)
            logging.error(
                "Falha ao iniciar worker recuperado de upscale %s/%s job=%s: %s",
                project_id,
                take_id,
                job_id,
                exc,
                exc_info=True,
            )
            try:
                _set_gen_job(
                    job_id,
                    status="error",
                    progress=100,
                    message="Falha ao iniciar worker recuperado de upscale.",
                    error=str(exc),
                )
            except Exception:
                logging.exception("Falha ao terminalizar worker recuperado job=%s", job_id)
    return resumed


def _recover_interrupted_video_jobs() -> None:
    _recover_interrupted_video_upscale_jobs()
    _recover_interrupted_video_take_jobs()


@app.on_event("startup")
async def _resume_interrupted_video_takes_on_startup() -> None:
    from ready_exports_sync import resume_ready_exports_sync
    resume_ready_exports_sync(VIDEO_PROJECTS_ROOT)
    _GEN_JOB_STORE.recover_interrupted()
    _ensure_hyperframes_preview_async()
    _start_review_proxy_worker()
    threading.Thread(
        target=_ANCHOR_EXECUTOR_MANAGER.resume_authorized,
        daemon=True,
        name="studio-anchor-recovery",
    ).start()
    if os.environ.get("STUDIO_AUTO_RESUME_TAKES", "1").strip().lower() in {"0", "false", "no", "off"}:
        return
    threading.Thread(
        target=_recover_interrupted_video_jobs,
        daemon=True,
        name="studio-take-recovery",
    ).start()


def _preflight_video_take_job(project_id: str, take_id: str) -> Dict[str, Any]:
    spec = _get_take_generation_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
    if spec["status"] in {"QUEUED", "GENERATING", "UPSCALING"}:
        raise TakeJobConflict("TAKE_BUSY", "Este take ja possui trabalho em andamento.")
    selected_model = _video_take_model_for_spec(spec)
    if not _video_engine_authorized(selected_model):
        raise TakeJobConflict(
            "ENGINE_NOT_AUTHORIZED",
            "Este projeto usa um motor removido ou nao autorizado. A unica rota Wan aceita e "
            "Wan2.2 Animate BF16 Move com DWPose aprovado.",
        )
    if (
        selected_model == MINIMAX_H3_REF2VA_MODEL_NAME
        and not _video_take_model_ready(selected_model)
    ):
        raise TakeJobConflict(
            "REF2VA_MODEL_NOT_READY",
            "O take declara Ref2VA, mas o checkpoint Ref2VA separado, fixado por hash, nao esta disponivel. "
            "FL2VA nao pode substituir Ref2VA.",
        )
    if not _video_take_model_ready(selected_model):
        raise TakeJobConflict("MODEL_NOT_READY", f"Modelo configurado para o take nao esta disponivel: {selected_model}.")
    if (
        selected_model == WAN22_ANIMATE_MODEL_NAME
        and not _wan_animate_kit_status(Path(BASE_DIR), verify_hash=True).get("ready")
    ):
        raise TakeJobConflict(
            "WAN_ANIMATE_INTEGRITY_FAILED",
            "O kit Wan Animate/DWPose nao corresponde aos tamanhos e SHA-256 fixados; render bloqueado.",
        )
    if _is_minimax_h3_model(selected_model) and not _minimax_h3_kit_ready(verify_hash=True):
        raise TakeJobConflict(
            "MODEL_INTEGRITY_FAILED",
            "O kit MiniMax H3 FL2VA nao corresponde aos hashes aprovados; render bloqueado sem fallback.",
        )
    if (
        selected_model == MINIMAX_H3_REF2VA_MODEL_NAME
        and not _minimax_h3_ref2va_ready(verify_hash=True)
    ):
        raise TakeJobConflict(
            "REF2VA_MODEL_INTEGRITY_FAILED",
            "O checkpoint MiniMax H3 Ref2VA separado nao esta instalado e fixado no models.lock.json; "
            "o FL2VA nao sera reutilizado como fallback.",
        )
    spec["keyframe"].read_bytes()
    audio_conditioning = spec.get("audioConditioning")
    if audio_conditioning is not None:
        Path(audio_conditioning).read_bytes()
    end_keyframe = spec.get("endKeyframe")
    if end_keyframe is not None:
        Path(end_keyframe).read_bytes()
    minimax_control = (
        spec.get("minimaxAnchorControl")
        if isinstance(spec.get("minimaxAnchorControl"), dict)
        else {}
    )
    for reference_image in minimax_control.get("referenceImages", []):
        Path(reference_image).read_bytes()
    reference_video = minimax_control.get("referenceVideo")
    if reference_video is not None:
        Path(reference_video).read_bytes()
    wan_control = (
        spec.get("wanAnimateControl")
        if isinstance(spec.get("wanAnimateControl"), dict)
        else {}
    )
    pose_video = wan_control.get("poseVideo")
    if pose_video is not None:
        Path(pose_video).read_bytes()
    return spec


def _start_video_take_job(
    project_id: str,
    take_id: str,
    seed: int = -1,
    *,
    batch_id: str = "",
    batch_index: int = 0,
    batch_size: int = 0,
) -> Dict[str, Any]:
    with _VIDEO_TAKE_START_LOCK:
        spec = _preflight_video_take_job(project_id, take_id)
        generation_profile = str(spec.get("generationProfile") or "").strip()
        selected_model = _video_take_model_for_spec(spec)
        base_bytes = spec["keyframe"].read_bytes()
        audio_conditioning = spec.get("audioConditioning")
        audio_conditioning_bytes = (
            Path(audio_conditioning).read_bytes()
            if audio_conditioning is not None
            else None
        )
        end_keyframe = spec.get("endKeyframe")
        end_bytes = Path(end_keyframe).read_bytes() if end_keyframe is not None else None
        job_id = uuid.uuid4().hex
        _set_gen_job(
            job_id,
            status="queued",
            progress=1,
            message=f"Take enfileirado no perfil {selected_model} validado.",
            result=None,
            error=None,
            prompt_id=None,
            job_kind="video_take",
            batch_id=str(batch_id or ""),
            batch_index=max(0, int(batch_index or 0)),
            batch_size=max(0, int(batch_size or 0)),
            auto_resume=False,
            project_id=project_id,
            take_id=take_id,
            mode="video",
            model=selected_model,
            prompt=spec["prompt"],
            base_image_name=spec["keyframeName"],
            end_image_name=str(spec.get("endKeyframeName") or ""),
            width=int(spec.get("width") or 768),
            height=int(spec.get("height") or 432),
            frames=int(spec["frames"]),
            fps=spec["fps"],
            steps=int(spec.get("steps") or 16),
            guidance=float(spec.get("guidance") or 6.0),
            camera_pose=str(spec.get("cameraPose") or ""),
            camera_speed=float(spec.get("cameraSpeed") or 0.8),
            generation_profile=generation_profile,
            h3_quality_profile=str(spec.get("h3QualityProfile") or ""),
            video_conditioning_profile=str(
                spec.get("videoConditioningProfile") or "identity_locked"
            ),
            visual_only_pass=bool(spec.get("visualOnlyPass")),
            h3_prompt_contract=dict(spec.get("h3PromptContract") or {}),
            h3_live_preview=bool(spec.get("h3LivePreview", False)),
            audio_strategy=str(spec.get("audioStrategy") or ""),
            cast_contract_known=bool(spec.get("castContractKnown")),
            expected_human_cast=list(spec.get("expectedHumanCast") or []),
            expected_non_human_cast=list(spec.get("expectedNonHumanCast") or []),
            distinct_story_events=max(1, int(spec.get("distinctStoryEvents") or 1)),
            seed=seed,
        )
        _set_take_generation_state(
            VIDEO_PROJECTS_ROOT, project_id, take_id, status="QUEUED", job_id=job_id
        )
        _launch_video_take_worker(
            job_id,
            project_id,
            take_id,
            spec,
            base_bytes,
            seed,
            audio_conditioning_bytes=audio_conditioning_bytes,
            audio_conditioning_name=str(spec.get("audioConditioningName") or ""),
            end_bytes=end_bytes,
        )
        return {
            "ok": True,
            "jobId": job_id,
            "projectId": project_id,
            "takeId": take_id,
            "batchId": str(batch_id or ""),
            "batchIndex": max(0, int(batch_index or 0)),
            "batchSize": max(0, int(batch_size or 0)),
            "stage": (
                "LTX25_READY_FOR_GPU_GATE"
                if generation_profile == _LTX25_TAKE_PROFILE
                else "MINIMAX_H3_OWNER_LOCKED_PROFILE"
                if generation_profile in {
                    MINIMAX_H3_PROFILE,
                    MINIMAX_H3_VERTICAL_PROFILE,
                }
                else "ENGINE_SELECTION_INVALID"
            ),
            "width": int(spec.get("width") or 768),
            "height": int(spec.get("height") or 432),
            "fps": spec["fps"],
            "frames": int(spec["frames"]),
        }


def _start_take_upscale_job(project_id: str, take_id: str) -> Dict[str, Any]:
    with _VIDEO_UPSCALE_START_LOCK:
        spec = _get_take_upscale_spec(VIDEO_PROJECTS_ROOT, project_id, take_id)
        if spec["status"] == "UPSCALING":
            raise TakeJobConflict("TAKE_BUSY", "Este take ja esta na fila de upscale.")
        attempt = int(
            spec.get("nextUpscaleAttempt")
            or (int(spec.get("upscaleAttempt") or 0) + 1)
        )
        profile_id, _profile_path, target_width, target_height = (
            _upscale_profile_for_spec(spec)
        )
        job_id = uuid.uuid4().hex
        _set_gen_job(
            job_id,
            status="queued",
            progress=1,
            message="Upscaling obrigatório enfileirado.",
            result=None,
            error=None,
            error_code=None,
            recoverable=None,
            prompt_id=None,
            job_kind="video_upscale",
            auto_resume=True,
            project_id=project_id,
            take_id=take_id,
            mode="video_upscale",
            model=(
                f"SeedVR2 3B + RIFE60 + DLSS 5 + H.264 "
                f"{target_width}x{target_height}"
            ),
            upscale_profile=profile_id,
            upscale_attempt=attempt,
            source_file=str(spec["source"]),
            width=target_width,
            height=target_height,
            fps=60,
        )
        try:
            _set_take_upscale_state(
                VIDEO_PROJECTS_ROOT,
                project_id,
                take_id,
                status="QUEUED",
                job_id=job_id,
                attempt=attempt,
            )
        except Exception as exc:
            _set_gen_job(
                job_id,
                status="error",
                progress=100,
                message="Falha ao reservar a tentativa de upscale.",
                error=str(exc),
                error_code="UPSCALE_QUEUE_RESERVATION_FAILED",
                recoverable=True,
            )
            raise
        spec = dict(spec)
        spec["upscaleAttempt"] = attempt
        spec["lastJobId"] = job_id
    _launch_take_upscale_worker(job_id, project_id, take_id, spec)
    return {
        "ok": True,
        "jobId": job_id,
        "projectId": project_id,
        "takeId": take_id,
        "stage": "SEEDVR2_RIFE60_DLSS5_REQUIRED_REVIEW",
        "profile": profile_id,
        "attempt": attempt,
        "width": target_width,
        "height": target_height,
    }


def _production_batch_eligible(take: Dict[str, Any]) -> bool:
    status = str(take.get("status") or "")
    if not take.get("canGenerate") or status in {"QUEUED", "GENERATING", "UPSCALING"}:
        return False
    if not take.get("hasPreview"):
        return True
    if status == "ERROR":
        return True
    if status == "REJECTED":
        request = take.get("directorRequest") if isinstance(take.get("directorRequest"), dict) else {}
        qc_status = str(take.get("qcStatus") or "").strip().lower()
        return (
            str(request.get("status") or "") in {"PENDING", "IN_PROGRESS", "DELIVERED"}
            or "rerender_required" in qc_status
        )
    return False


def _production_correction_retry(take: Dict[str, Any]) -> bool:
    """True when a take is correcting an attempted render, not starting a new story beat."""

    return str(take.get("status") or "").strip().upper() in {"ERROR", "REJECTED"}


def _active_project_video_take_jobs(project_id: str) -> List[Dict[str, Any]]:
    """Return Maestro-owned take jobs that still hold a production-batch slot."""

    project_id = str(project_id or "").strip()
    return [
        job
        for job in _GEN_JOB_STORE.list(page=1, page_size=500).get("items", [])
        if str(job.get("project_id") or "") == project_id
        and str(job.get("job_kind") or "") == "video_take"
        and str(job.get("status") or "") in {"queued", "running", "canceling"}
    ]


def _select_story_production_batch(
    takes: List[Dict[str, Any]],
    eligible: List[Dict[str, Any]],
    policy: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Select one fixed story block without skipping missing anchors."""

    if not bool(policy.get("enabled")):
        return eligible, [str(take.get("takeId") or "") for take in eligible], []

    try:
        batch_size = int(policy.get("batchSize") or 3)
    except (TypeError, ValueError):
        batch_size = 3
    batch_size = max(1, min(20, batch_size))
    by_id = {
        str(take.get("takeId") or ""): take
        for take in takes
        if str(take.get("takeId") or "")
    }
    requested_order = policy.get("renderOrder")
    if not isinstance(requested_order, list):
        requested_order = []
    ordered_ids: List[str] = []
    for value in requested_order:
        take_id = str(value or "").strip()
        if take_id in by_id and take_id not in ordered_ids:
            ordered_ids.append(take_id)
    ordered_ids.extend(take_id for take_id in by_id if take_id not in ordered_ids)

    eligible_by_id = {
        str(take.get("takeId") or ""): take
        for take in eligible
        if str(take.get("takeId") or "")
    }
    first_index = next(
        (index for index, take_id in enumerate(ordered_ids) if take_id in eligible_by_id),
        None,
    )
    if first_index is None:
        return [], [], []

    if (
        bool(policy.get("allowIncompleteCorrectionBatch"))
        and _production_correction_retry(eligible_by_id[ordered_ids[first_index]])
    ):
        # A rejected/error retry already consumed its original story slot. It
        # must not be held hostage by future takes whose anchors do not exist
        # yet. Keep retries contiguous and never skip across the missing anchor.
        corrections: List[Dict[str, Any]] = []
        correction_ids: List[str] = []
        for take_id in ordered_ids[first_index:]:
            candidate = eligible_by_id.get(take_id)
            if candidate is None or not _production_correction_retry(candidate):
                break
            corrections.append(candidate)
            correction_ids.append(take_id)
            if len(corrections) >= batch_size:
                break
        return corrections, correction_ids, []

    if bool(policy.get("fillEligibleAcrossBatches")):
        selected: List[Dict[str, Any]] = []
        batch_ids: List[str] = []
        blocked_ids: List[str] = []
        for take_id in ordered_ids[first_index:]:
            take = by_id[take_id]
            if take_id in eligible_by_id:
                selected.append(eligible_by_id[take_id])
                batch_ids.append(take_id)
                if len(selected) >= batch_size:
                    break
                continue
            if not bool(take.get("canGenerate")) and not bool(take.get("hasPreview")):
                batch_ids.append(take_id)
                blocked_ids.append(take_id)
                if (
                    bool(policy.get("strictContiguous", True))
                    and bool(policy.get("requireAllBaseImagesReady", True))
                ):
                    return selected, batch_ids, blocked_ids
        return selected, batch_ids, blocked_ids

    batch_start = (first_index // batch_size) * batch_size
    batch_ids = ordered_ids[batch_start:batch_start + batch_size]
    blocked_ids = [
        take_id
        for take_id in batch_ids
        if not bool(by_id[take_id].get("canGenerate"))
        and not bool(by_id[take_id].get("hasPreview"))
    ]
    if (
        blocked_ids
        and bool(policy.get("strictContiguous", True))
        and bool(policy.get("requireAllBaseImagesReady", True))
    ):
        return [eligible_by_id[take_id] for take_id in batch_ids if take_id in eligible_by_id], batch_ids, blocked_ids
    return [eligible_by_id[take_id] for take_id in batch_ids if take_id in eligible_by_id], batch_ids, blocked_ids


@app.post("/api/video-projects/{project_id}/takes/{take_id}/jobs", status_code=202)
async def video_take_job_start(request: Request, project_id: str, take_id: str):
    """Inicia o passe do motor H3 ou LTX 2.5 explicitamente escolhido."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"seed"}
        if unknown:
            raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
        return await run_in_threadpool(_start_video_take_job, project_id, take_id, int(payload.get("seed", -1)))
    except TakeJobConflict as exc:
        return _video_projects_error(409, exc.code, str(exc))
    except FileNotFoundError:
        return _video_projects_error(404, "TAKE_NOT_FOUND", "Projeto ou take nao encontrado.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take job prepare")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao preparar geracao do take.")


@app.post("/api/video-projects/{project_id}/takes/{take_id}/upscale-jobs", status_code=202)
async def video_take_upscale_start(request: Request, project_id: str, take_id: str):
    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        if payload:
            raise ValueError("O upscale deste projeto usa o perfil FHD aprovado e nao aceita parametros manuais.")
        return await run_in_threadpool(_start_take_upscale_job, project_id, take_id)
    except TakeJobConflict as exc:
        return _video_projects_error(409, exc.code, str(exc))
    except FileNotFoundError:
        return _video_projects_error(404, "TAKE_NOT_FOUND", "Projeto ou take nao encontrado.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video take upscale prepare")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao preparar upscale 1080p.")


@app.post("/api/video-projects/{project_id}/batch-jobs", status_code=202)
async def video_project_batch_jobs(request: Request, project_id: str):
    """Enfileira todos os takes elegiveis, preservando os ja prontos ou ocupados."""

    if not _is_internal_request(request):
        return _public_forbidden()
    try:
        payload = await _video_projects_json_body(request)
        unknown = set(payload) - {"action"}
        if unknown:
            raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
        action = str(payload.get("action") or "").strip().lower()
        if action not in {"production", "upscale"}:
            raise ValueError("action deve ser production ou upscale.")
        takes = _list_video_takes(VIDEO_PROJECTS_ROOT, project_id, page=1, page_size=100).get("data", [])
        eligible = [
            take for take in takes
            if (_production_batch_eligible(take) if action == "production" else bool(take.get("canUpscale")))
        ]
        batch_ids: List[str] = []
        blocked_ids: List[str] = []
        batch_policy: Dict[str, Any] = {}
        production_batch_id = ""
        incomplete_correction_batch = False
        if action == "production":
            with _VIDEO_BATCH_START_LOCK:
                active_jobs = _active_project_video_take_jobs(project_id)
                if active_jobs:
                    return _video_projects_error(
                        409,
                        "PRODUCTION_BATCH_ACTIVE",
                        "Uma trinca deste projeto ainda esta em producao. O botao libera quando os tres jobs terminarem.",
                        {
                            "activeJobIds": [str(job.get("job_id") or "") for job in active_jobs],
                            "activeTakeIds": [str(job.get("take_id") or "") for job in active_jobs],
                        },
                    )
                project = _get_video_project(VIDEO_PROJECTS_ROOT, project_id)
                batch_policy = (
                    project.get("productionBatch")
                    if isinstance(project.get("productionBatch"), dict)
                    else {}
                )
                eligible, batch_ids, blocked_ids = _select_story_production_batch(
                    takes,
                    eligible,
                    batch_policy,
                )
                try:
                    configured_batch_size = int(batch_policy.get("batchSize") or 3)
                except (TypeError, ValueError):
                    configured_batch_size = 3
                configured_batch_size = max(1, min(20, configured_batch_size))
                incomplete_correction_allowed = bool(
                    batch_policy.get("allowIncompleteCorrectionBatch")
                ) and bool(eligible) and all(
                    _production_correction_retry(take) for take in eligible
                )
                incomplete_correction_batch = bool(
                    incomplete_correction_allowed
                    and len(eligible) < configured_batch_size
                )
                if blocked_ids:
                    return _video_projects_error(
                        409,
                        "STORY_BATCH_ANCHORS_NOT_READY",
                        "A proxima trinca espera todas as fotos-base obrigatorias antes de reservar a GPU.",
                        {
                            "batchTakeIds": batch_ids,
                            "blockedTakeIds": blocked_ids,
                            "readyCount": len(eligible),
                            "requiredCount": configured_batch_size,
                        },
                    )
                if (
                    bool(batch_policy.get("requireFullBatch"))
                    and len(eligible) != configured_batch_size
                    and not incomplete_correction_allowed
                ):
                    return _video_projects_error(
                        409,
                        "PRODUCTION_BATCH_INCOMPLETE",
                        "A producao exige uma trinca completa; nenhum job foi iniciado.",
                        {
                            "batchTakeIds": batch_ids,
                            "readyCount": len(eligible),
                            "requiredCount": configured_batch_size,
                        },
                    )
                for take in eligible:
                    _preflight_video_take_job(project_id, str(take.get("takeId") or ""))
                production_batch_id = uuid.uuid4().hex
                started = []
                errors = []
                for batch_index, take in enumerate(eligible, start=1):
                    take_id = str(take.get("takeId") or "")
                    try:
                        item = _start_video_take_job(
                            project_id,
                            take_id,
                            -1,
                            batch_id=production_batch_id,
                            batch_index=batch_index,
                            batch_size=len(eligible),
                        )
                        started.append({
                            "takeId": take_id,
                            "jobId": item["jobId"],
                            "stage": item["stage"],
                            "batchIndex": batch_index,
                        })
                    except (TakeJobConflict, FileNotFoundError, TypeError, ValueError) as exc:
                        errors.append({"takeId": take_id, "message": str(exc)})
        else:
            started = []
            errors = []
            for take in eligible:
                take_id = str(take.get("takeId") or "")
                try:
                    item = _start_take_upscale_job(project_id, take_id)
                    started.append({"takeId": take_id, "jobId": item["jobId"], "stage": item["stage"]})
                except (TakeJobConflict, FileNotFoundError, TypeError, ValueError) as exc:
                    errors.append({"takeId": take_id, "message": str(exc)})
        return {
            "ok": True,
            "projectId": project_id,
            "action": action,
            "eligible": len(eligible),
            "started": started,
            "startedCount": len(started),
            "skippedCount": max(0, len(takes) - len(eligible)),
            "errors": errors,
            "batchTakeIds": batch_ids,
            "batchSize": int(batch_policy.get("batchSize") or len(eligible) or 0),
            "productionBatchId": production_batch_id,
            "storyBatchEnabled": bool(batch_policy.get("enabled")),
            "incompleteCorrectionBatch": incomplete_correction_batch,
        }
    except FileNotFoundError:
        return _video_projects_error(404, "PROJECT_NOT_FOUND", "Projeto nao encontrado.")
    except (TypeError, ValueError) as exc:
        return _video_projects_error(422, "VALIDATION_ERROR", str(exc))
    except Exception:
        logging.exception("video project batch jobs")
        return _video_projects_error(500, "INTERNAL_ERROR", "Falha ao enfileirar o projeto.")

#  aUDIO: CONVERSOR 
@app.post("/api/audio/converter")
async def audio_converter(
    files: List[UploadFile] = File(...),
    formato_saida: str = Form("mp3"),
    qualidade:     str = Form("320k")
):
    formato_saida = (formato_saida or "mp3").strip().lower()
    qualidade = (qualidade or "320k").strip().lower()
    if not files or len(files) > 20:
        return JSONResponse(status_code=422, content={"erro": "Envie entre 1 e 20 arquivos."})
    if formato_saida not in {"mp3", "wav", "flac"}:
        return JSONResponse(status_code=422, content={"erro": "Formato de audio invalido."})
    if qualidade not in {"128k", "192k", "256k", "320k"}:
        return JSONResponse(status_code=422, content={"erro": "Qualidade de audio invalida."})
    limpar_vram()
    try:
        bk_log(f"Conversor: {len(files)} arquivo(s) -> {formato_saida}")
        ff = get_ffmpeg(); caminhos = []
        for i, f in enumerate(files):
            c_in, safe_name = _save_media_upload(f, f"ac_{i}")
            nome  = os.path.splitext(safe_name)[0]
            download_name = f"{nome}.{formato_saida}"
            c_out = _unique_media_output(nome, formato_saida, "convertido")
            if formato_saida in ("wav", "flac"):
                subprocess.run([ff, "-y", "-i", c_in, c_out], check=True, capture_output=True)
            else:
                subprocess.run([ff, "-y", "-i", c_in, "-b:a", qualidade, c_out], check=True, capture_output=True)
            caminhos.append((c_out, download_name)); os.remove(c_in)
            bk_log(f"  Convertido: {download_name}")
        if len(caminhos) == 1:
            path, fname = caminhos[0]
            return file_response(path, fname)
        cam_zip = _unique_media_output("Audio_Convertido", "zip")
        with zipfile.ZipFile(cam_zip, "w") as z:
            for path, fname in caminhos: z.write(path, fname)
        bk_log("Conversao concluida  ZIP pronto")
        return file_response(cam_zip, "Audio_Convertido.zip")
    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO converter: {e}")
        logging.error(f"converter: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  aUDIO: TRANSCRIaaO 
@app.post("/api/audio/transcrever")
async def audio_transcrever(
    files:          List[UploadFile] = File(...),
    modelo:         str = Form("large-v3"),
    idioma:         str = Form("pt"),
    formato_saida:  str = Form("txt")
):
    global _whisper_model, _whisper_size
    modelo = (modelo or "large-v3").strip().lower()
    idioma = (idioma or "pt").strip().lower()
    formato_saida = (formato_saida or "txt").strip().lower()
    if not files or len(files) > 20:
        return JSONResponse(status_code=422, content={"erro": "Envie entre 1 e 20 arquivos."})
    if modelo not in {"large-v3", "large-v3-turbo"}:
        return JSONResponse(status_code=422, content={"erro": "Modelo de transcricao invalido."})
    if idioma not in {"pt", "en", "auto"}:
        return JSONResponse(status_code=422, content={"erro": "Idioma de transcricao invalido."})
    if formato_saida not in {"txt", "srt", "vtt"}:
        return JSONResponse(status_code=422, content={"erro": "Formato de transcricao invalido."})
    limpar_vram()
    try:
        bk_log(f"Transcricao: {len(files)} arquivo(s) | modelo={modelo} | formato={formato_saida}")
        if _whisper_model is None or modelo != _whisper_size:
            from transformers import pipeline
            device = 0 if torch.cuda.is_available() else -1
            dtype = torch.float16 if device == 0 else torch.float32
            
            # Libera VRAM do modelo anterior se existir
            if _whisper_model is not None:
                bk_log(f"Limpando modelo anterior ({_whisper_size})...")
                del _whisper_model
                limpar_vram()
                
            bk_log(f"Carregando Whisper Nativo (Turbo) na GPU...")
            _whisper_model = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-large-v3-turbo",
                device=device,
                torch_dtype=dtype
            )
            _whisper_size  = modelo
            bk_log("Whisper pronto.")
        lang = "portuguese" if idioma == "pt" else ("english" if idioma == "en" else None)
        caminhos = []; unificado = ""
        for i, f in enumerate(files):
            c_in, safe_name = _save_media_upload(f, f"tr_{i}")
            bk_log(f"  Transcrevendo com aceleracao batch: {safe_name}...")
            
            # Usando batching para torrar a placa de vadeo
            resultado = _whisper_model(
                c_in, 
                generate_kwargs={"language": lang} if lang else {},
                chunk_length_s=30, 
                batch_size=16,
                return_timestamps=True
            )
            
            class _SegMock:
                def __init__(self, txt, st, en):
                    self.text = txt
                    self.start = st
                    self.end = en
                    
            segs = []
            for c in resultado.get("chunks", []):
                ts = c.get("timestamp", (0.0, 0.0))
                end_time = ts[1] if ts[1] is not None else ts[0] + 5.0
                segs.append(_SegMock(c.get("text", ""), ts[0], end_time))
                
            bk_log(f"  {safe_name}: {len(segs)} segmentos extraados")
            nome = os.path.splitext(safe_name)[0]
            if formato_saida == "srt":
                def ts(s):
                    h, m, sec = int(s)//3600, (int(s)%3600)//60, s%60
                    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
                conteudo = "\n".join(
                    f"{j+1}\n{ts(seg.start)} --> {ts(seg.end)}\n{seg.text.strip()}\n"
                    for j, seg in enumerate(segs)
                )
                ext = "srt"
            elif formato_saida == "vtt":
                def ts(s):
                    h, m, sec = int(s)//3600, (int(s)%3600)//60, s%60
                    return f"{h:02d}:{m:02d}:{sec:06.3f}"
                conteudo = "WEBVTT\n\n" + "\n".join(
                    f"{ts(seg.start)} --> {ts(seg.end)}\n{seg.text.strip()}\n"
                    for seg in segs
                )
                ext = "vtt"
            else:
                conteudo = " ".join(seg.text.strip() for seg in segs)
                ext = "txt"
            download_name = f"{nome}.{ext}"
            c_out = _unique_media_output(nome, ext, "transcricao")
            with open(c_out, "w", encoding="utf-8") as tf: tf.write(conteudo)
            caminhos.append((c_out, download_name))
            unificado += f"=== {safe_name} ===\n{conteudo}\n\n"
            os.remove(c_in)
        # 1 arquivo -> retorna o txt/srt/vtt direto
        if len(caminhos) == 1:
            path, fname = caminhos[0]
            bk_log(f"Transcricao concluida: {fname}")
            return file_response(path, fname)
        # multiplos -> ZIP
        c_uni = _unique_media_output("UNIFICADO", "txt")
        with open(c_uni, "w", encoding="utf-8") as uf: uf.write(unificado)
        cam_zip = _unique_media_output("Transcricoes", "zip")
        with zipfile.ZipFile(cam_zip, "w") as z:
            for path, fname in caminhos: z.write(path, fname)
            z.write(c_uni, "UNIFICADO.txt")
        bk_log("Transcricao concluida  ZIP pronto")
        return file_response(cam_zip, "Transcricoes.zip")
    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO transcrever: {e}")
        logging.error(f"transcrever: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  aUDIO: ISOLAMENTO DE VOZ 
@app.post("/api/audio/isolar")
async def audio_isolar(file: UploadFile = File(...)):
    limpar_vram()
    try:
        c_in, safe_name = _save_media_upload(file, "iso")
        bk_log(f"Isolamento de voz: {safe_name}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        bk_log(f"Demucs rodando em {device.upper()}...")
        cmd = [sys.executable, "-m", "demucs", "-n", "htdemucs",
               "--two-stems=vocals", "-d", device, "-o", PASTA, c_in]
        r = subprocess.run(cmd)
        if r.returncode != 0 and device == "cuda":
            bk_log("NVENC falhou  tentando CPU...")
            cmd[7] = "cpu"
            subprocess.run(cmd, check=True)
        nome = os.path.splitext(safe_name)[0]
        demucs_name = os.path.splitext(os.path.basename(c_in))[0]
        res  = os.path.join(PASTA, "htdemucs", demucs_name, "vocals.wav")
        if not os.path.exists(res):
            return JSONResponse(status_code=500, content={"erro": f"Voz nao encontrada: {res}"})
        os.remove(c_in)
        fname = f"VOZ_{nome}.wav"
        bk_log(f"Isolamento concluido: {fname}")
        return file_response(res, fname)
    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO isolar: {e}")
        logging.error(f"isolar: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  aUDIO: PREVIEW DSP 
@app.post("/api/audio/preview")
async def audio_preview(
    file:           UploadFile = File(...),
    nr_intensidade: float = Form(1.4), nr_floor:  float = Form(0.28), nr_ativo: str = Form("true"),
    hpf_hz:         float = Form(100), box_cut_hz: float = Form(0),   box_cut_db: float = Form(-4),
    eq1_hz:         float = Form(2500), eq1_db:    float = Form(5),
    eq2_hz:         float = Form(4000), eq2_db:    float = Form(4),
    eq3_hz:         float = Form(7000), eq3_db:    float = Form(3),
    volume_target:  float = Form(-8.5), preview_seg: int = Form(20)
):
    import soundfile as sf
    limpar_vram()
    try:
        c_in, safe_name = _save_media_upload(file, "prev")
        bk_log(f"Preview DSP: {safe_name} ({preview_seg}s)")
        ff = get_ffmpeg()
        c_wav = c_in + "_raw.wav"
        subprocess.run([ff, "-y", "-i", c_in, "-ar", "16000", "-ac", "1",
                        "-t", str(preview_seg), c_wav], check=True, capture_output=True)
        audio, sr = sf.read(c_wav, dtype="float32")
        audio = dsp_pipeline(audio, sr, nr_intensidade, nr_floor, nr_ativo.lower() == "true",
                              hpf_hz, box_cut_hz, box_cut_db,
                              eq1_hz, eq1_db, eq2_hz, eq2_db, eq3_hz, eq3_db, volume_target)
        buf = BytesIO()
        sf.write(buf, audio, sr, subtype="PCM_16", format="WAV")
        buf.seek(0)
        for p in [c_in, c_wav]:
            if os.path.exists(p): os.remove(p)
        bk_log("Preview pronto.")
        return Response(content=buf.read(), media_type="audio/wav")
    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO preview: {e}")
        logging.error(f"preview: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  aUDIO: EXPORTAaaO DSP COMPLETA 
@app.post("/api/audio/forense_custom")
async def audio_forense_custom(
    file:           UploadFile = File(...),
    nr_intensidade: float = Form(1.4), nr_floor:  float = Form(0.28), nr_ativo: str = Form("true"),
    hpf_hz:         float = Form(100), box_cut_hz: float = Form(0),   box_cut_db: float = Form(-4),
    eq1_hz:         float = Form(2500), eq1_db:    float = Form(5),
    eq2_hz:         float = Form(4000), eq2_db:    float = Form(4),
    eq3_hz:         float = Form(7000), eq3_db:    float = Form(3),
    volume_target:  float = Form(-8.5)
):
    import soundfile as sf
    limpar_vram()
    try:
        c_in, safe_name = _save_media_upload(file, "fc")
        bk_log(f"Tratamento forense completo: {safe_name}")
        ff = get_ffmpeg()
        c_wav = c_in + "_raw.wav"
        subprocess.run([ff, "-y", "-i", c_in, "-ar", "16000", "-ac", "1", c_wav],
                       check=True, capture_output=True)
        audio, sr = sf.read(c_wav, dtype="float32")
        bk_log(f"  Audio: {len(audio)/sr:.1f}s | SR={sr}Hz")
        audio = dsp_pipeline(audio, sr, nr_intensidade, nr_floor, nr_ativo.lower() == "true",
                              hpf_hz, box_cut_hz, box_cut_db,
                              eq1_hz, eq1_db, eq2_hz, eq2_db, eq3_hz, eq3_db, volume_target)
        nome  = os.path.splitext(safe_name)[0]
        c_out = _unique_media_output(nome, "wav", "tratado")
        sf.write(c_out, audio, sr, subtype="PCM_16")
        for p in [c_in, c_wav]:
            if os.path.exists(p): os.remove(p)
        fname = f"TRATADO_{nome}.wav"
        bk_log(f"Tratamento concluido: {fname}")
        return file_response(c_out, fname)
    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO forense_custom: {e}")
        logging.error(f"forense_custom: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  VaDEO: EDITOR 
@app.post("/api/video/editor")
async def video_editor(
    files:         List[UploadFile] = File(...),
    formato_saida: str   = Form("mp4"),
    codec:         str   = Form("auto"),
    crf:           int   = Form(23),
    inicio:        float = Form(0.0),
    fim:           float = Form(0.0),
    extrair_audio: str   = Form("false")
):
    if _video_generation_paused():
        return JSONResponse(status_code=423, content={"erro": _video_pause_message()})
    formato_saida = (formato_saida or "mp4").strip().lower()
    codec = (codec or "auto").strip().lower()
    if not files or len(files) > 20:
        return JSONResponse(status_code=422, content={"erro": "Envie entre 1 e 20 videos."})
    if formato_saida not in {"mp4", "mov", "mkv", "mp3"}:
        return JSONResponse(status_code=422, content={"erro": "Formato de video invalido."})
    if codec not in {"extreme", "auto", "h264", "h265", "nvenc_h264", "nvenc_h265"}:
        return JSONResponse(status_code=422, content={"erro": "Codec de video invalido."})
    crf = _safe_int(crf, 23, 15, 35)
    inicio = _safe_float(inicio, 0.0, 0.0, 86400.0)
    fim = _safe_float(fim, 0.0, 0.0, 86400.0)
    if fim and fim <= inicio:
        return JSONResponse(status_code=422, content={"erro": "O fim do corte deve ser maior que o inicio."})
    limpar_vram()
    try:
        bk_log(f"Video editor: {len(files)} arquivo(s) -> {formato_saida}")
        ff = get_ffmpeg(); caminhos = []
        
        for i, file in enumerate(files):
            c_in, safe_name = _save_media_upload(file, f"ve_{i}")
            nome = os.path.splitext(safe_name)[0]
            
            if extrair_audio.lower() == "true":
                download_name = f"{nome}_audio.mp3"
                c_out = _unique_media_output(nome, "mp3", "audio")
                subprocess.run([ff, "-y", "-i", c_in, "-q:a", "0", "-map", "a", c_out],
                               check=True, capture_output=True)
                os.remove(c_in)
                caminhos.append((c_out, download_name))
                bk_log(f"  Extracao concluida: {download_name}")
                continue

            download_name = f"{nome}_editado.{formato_saida}"
            c_out = _unique_media_output(nome, formato_saida, "editado")
            cmd   = [ff, "-y"]
            if fim > 0:
                cmd += ["-ss", str(inicio), "-to", str(fim)]
            cmd += ["-i", c_in]
            
            if formato_saida == "mp3":
                cmd += ["-q:a", "0", "-map", "a", c_out]
            else:
                vc_map = {"nvenc_h264": "h264_nvenc", "nvenc_h265": "hevc_nvenc",
                          "h265": "libx265", "h264": "libx264"}
                
                # Modo Extreme: Foca em compressao agressiva garantindo reducao de tamanho
                is_extreme = (codec == "extreme")
                if is_extreme:
                    vc = "hevc_nvenc" if nvenc_ok(ff) else "libx265"
                    orig_bitrate = get_video_bitrate(ff, c_in)
                    if orig_bitrate > 0:
                        target_bitrate = int(orig_bitrate * 0.6)
                        br_str = f"{int(target_bitrate / 1000)}k"
                        target_cq = 30 
                    else:
                        br_str = "1500k"
                        target_cq = 28
                else:
                    vc = vc_map.get(codec, "libx264") if codec != "auto" else ("h264_nvenc" if nvenc_ok(ff) else "libx264")
                    target_cq = crf
                    br_str = "6M"

                bk_log(f"  [{safe_name}] Codec: {vc} | CQ/CRF: {target_cq}")
                
                if "nvenc" in vc:
                    cmd += ["-c:v", vc, "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", str(target_cq)]
                    if is_extreme:
                        cmd += ["-b:v", br_str, "-maxrate:v", br_str, "-bufsize:v", f"{int(int(br_str[:-1])*2)}k"]
                    else:
                        cmd += ["-maxrate:v", "6M", "-bufsize:v", "12M"] 
                else:
                    cmd += ["-c:v", vc, "-crf", str(target_cq), "-preset", "slower"]
                    if is_extreme:
                        cmd += ["-b:v", br_str, "-maxrate:v", br_str, "-bufsize:v", f"{int(int(br_str[:-1])*2)}k"]
                
                cmd += ["-c:a", "aac", "-b:a", "128k" if is_extreme else "192k", "-movflags", "+faststart", c_out]
            
            subprocess.run(cmd, check=True)
            os.remove(c_in)
            if formato_saida != "mp3":
                await run_in_threadpool(_finish_required_media, c_out)
            caminhos.append((c_out, download_name))
            bk_log(f"  Video pronto: {download_name}")

        if len(caminhos) == 1:
            path, fname = caminhos[0]
            return file_response(path, fname)
        
        cam_zip = _unique_media_output("Videos_Processados", "zip")
        with zipfile.ZipFile(cam_zip, "w") as z:
            for path, fname in caminhos: z.write(path, fname)
        bk_log("Lote de videos concluido -> ZIP pronto")
        return file_response(cam_zip, "Videos_Processados.zip")

    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO video_editor: {e}")
        logging.error(f"video_editor: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  VaDEO: REMASTERIZAaaO 
@app.post("/api/video/remasterizar")
async def video_remasterizar(
    file:    UploadFile = File(...),
    escala:  int = Form(2),
    modo:    str = Form("rapido"),
    denoise: str = Form("false")
):
    if _video_generation_paused():
        return JSONResponse(status_code=423, content={"erro": _video_pause_message()})
    escala = _safe_int(escala, 2, 1, 4)
    modo = (modo or "rapido").strip().lower()
    if modo not in {"rapido", "ia"}:
        return JSONResponse(status_code=422, content={"erro": "Modo de remasterizacao invalido."})
    limpar_vram()
    try:
        c_in, safe_name = _save_media_upload(file, "rm")
        bk_log(f"Remasterizar: {safe_name} | {escala}x | modo={modo}")
        ff   = get_ffmpeg()
        nome  = os.path.splitext(safe_name)[0]
        c_out = _unique_media_output(nome, "mp4", "remasterizado")
        vc    = "h264_nvenc" if nvenc_ok(ff) else "libx264"
        if modo == "rapido":
            vf = [f"scale=iw*{escala}:ih*{escala}:flags=lanczos"]
            if denoise.lower() == "true":
                vf.insert(0, "hqdn3d=4:3:6:4.5")
            if "nvenc" in vc:
                cmd = [ff, "-y", "-i", c_in, "-vf", ",".join(vf),
                       "-c:v", vc, "-preset", "p7", "-rc", "vbr",
                       "-cq", "18", "-b:v", "0", "-c:a", "copy", c_out]
            else:
                cmd = [ff, "-y", "-i", c_in, "-vf", ",".join(vf),
                       "-c:v", vc, "-crf", "18", "-preset", "slow",
                       "-c:a", "copy", c_out]
            subprocess.run(cmd, check=True)
        else:
            up = carregar_upsampler()
            work_id = os.path.splitext(os.path.basename(c_out))[0]
            fd = os.path.join(PASTA, f"frames_{work_id}")
            fu = os.path.join(PASTA, f"frames_up_{work_id}")
            os.makedirs(fd, exist_ok=True); os.makedirs(fu, exist_ok=True)
            atmp = os.path.join(PASTA, f"{work_id}_atmp.aac")
            subprocess.run([ff, "-y", "-i", c_in, "-vn", "-c:a", "copy", atmp], capture_output=True)
            subprocess.run([ff, "-y", "-i", c_in, os.path.join(fd, "frame_%06d.png")],
                           check=True, capture_output=True)
            frames = sorted(f for f in os.listdir(fd) if f.endswith(".png"))
            bk_log(f"  ESRGAN: {len(frames)} frames...")
            for idx, fn in enumerate(frames):
                img = np.array(Image.open(os.path.join(fd, fn)).convert("RGB"))
                out, _ = up.enhance(img, outscale=escala)
                Image.fromarray(out).save(os.path.join(fu, fn))
                if idx % 50 == 0:
                    bk_log(f"  Frame {idx}/{len(frames)}")
            fps_r = subprocess.run([ff, "-i", c_in], capture_output=True, text=True)
            fps = "30"
            for line in fps_r.stderr.split("\n"):
                if "fps" in line:
                    for part in line.split(","):
                        if "fps" in part: fps = part.strip().split()[0]; break
            if "nvenc" in vc:
                cmd = [ff, "-y", "-framerate", fps,
                       "-i", os.path.join(fu, "frame_%06d.png"),
                       "-i", atmp, "-c:v", vc, "-preset", "p5",
                       "-rc", "vbr", "-cq", "18", "-b:v", "0",
                       "-c:a", "copy", "-shortest", c_out]
            else:
                cmd = [ff, "-y", "-framerate", fps,
                       "-i", os.path.join(fu, "frame_%06d.png"),
                       "-i", atmp, "-c:v", vc, "-crf", "18",
                       "-preset", "slow", "-c:a", "copy", "-shortest", c_out]
            subprocess.run(cmd, check=True)
            import shutil as _sh
            _sh.rmtree(fd); _sh.rmtree(fu)
            if os.path.exists(atmp): os.remove(atmp)
        os.remove(c_in)
        fname = f"{nome}_remasterizado.mp4"
        await run_in_threadpool(_finish_required_media, c_out)
        bk_log(f"Remasterizacao concluida: {fname}")
        return file_response(c_out, fname)
    except MediaUploadTooLarge as e:
        return JSONResponse(status_code=413, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO remasterizar: {e}")
        logging.error(f"remasterizar: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": str(e)})

#  IMAGEM 
@app.post("/api/imagem/processar")
async def imagem_processar(
    file:          UploadFile = File(...),
    acao:          str = Form(...),
    params_json:   str = Form("{}"),
    formato_saida: str = Form("png")
):
    limpar_vram()
    try:
        action = (acao or "").strip().lower()
        output_format = (formato_saida or "png").strip().lower()
        if action not in {"rembg", "upscale", "ajustar", "redimensionar"}:
            raise ValueError("Acao de imagem invalida.")
        if output_format not in {"png", "jpg", "jpeg", "webp"}:
            raise ValueError("Formato de imagem de saida invalido.")
        safe_name = _safe_upload_filename(file.filename or "", "imagem.png")
        image_bytes = await _read_upload_bounded(
            file,
            "Imagem",
            max_bytes=_max_upload_image_bytes(),
        )
        bk_log(f"Imagem: {action} | {safe_name} -> {output_format}")
        img = _open_valid_upload_image(image_bytes, safe_name)
        params = json.loads(params_json) if params_json else {}
        if not isinstance(params, dict):
            raise ValueError("Parametros de imagem invalidos.")
        if action == "rembg":
            from rembg import remove
            img = remove(img.convert("RGBA")); output_format = "png"
        elif action == "upscale":
            up = carregar_upsampler()
            out, _ = up.enhance(np.array(img.convert("RGB")), outscale=4)
            img = Image.fromarray(out)
        elif action == "ajustar":
            for attr, cls in [("brilho", ImageEnhance.Brightness),
                               ("contraste", ImageEnhance.Contrast),
                               ("saturacao", ImageEnhance.Color),
                               ("nitidez",   ImageEnhance.Sharpness)]:
                if params.get(attr, 1.0) != 1.0:
                    img = cls(img).enhance(_safe_float(params[attr], 1.0, 0.0, 3.0))
            if params.get("rotacao", 0) != 0:
                img = img.rotate(_safe_int(params["rotacao"], 0, -360, 360), expand=True)
            if params.get("espelhar_h"):
                from PIL import ImageOps; img = ImageOps.mirror(img)
            if params.get("espelhar_v"):
                from PIL import ImageOps; img = ImageOps.flip(img)
        elif action == "redimensionar":
            target_width = _safe_int(params.get("largura"), img.width, 8, 8192)
            target_height = _safe_int(params.get("altura"), img.height, 8, 8192)
            if target_width * target_height > 60_000_000:
                raise ValueError("Imagem de saida grande demais em pixels.")
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        buf = BytesIO()
        fmt = output_format.upper()
        if fmt == "JPG": fmt = "JPEG"
        if fmt in ("JPEG",) and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buf, format=fmt, quality=95)
        dlss_file = _unique_media_output("imagem_dlss5", output_format)
        Path(dlss_file).write_bytes(buf.getvalue())
        await run_in_threadpool(_finish_required_media, dlss_file)
        buf = BytesIO(Path(dlss_file).read_bytes())
        bk_log(f"Imagem processada: {action} OK")
        media_subtype = "jpeg" if output_format in {"jpg", "jpeg"} else output_format
        return Response(content=buf.getvalue(), media_type=f"image/{media_subtype}")
    except ValueError as e:
        status = 413 if "excede o limite" in str(e) else 422
        return JSONResponse(status_code=status, content={"erro": str(e)})
    except Exception as e:
        bk_log(f"ERRO imagem: {e}")
        logging.error(f"imagem: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"erro": "Falha interna ao processar imagem."})

from creative_os.integration import install as _install_creative_os
_CREATIVE_OS = _install_creative_os(globals())

# 
if __name__ == "__main__":
    import os
    import uvicorn
    bk_log("STUDIO PRO v2.0 iniciando...")
    port = int(os.environ.get("MAESTRO_STUDIO_PORT", "8027"))
    print("=" * 50 + f"\n  STUDIO PRO  http://localhost:{port}\n" + "=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
