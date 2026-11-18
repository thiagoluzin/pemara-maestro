"""Maestro Editor IA: timeline local, voz privada e copiloto por Ollama.

O modulo e deliberadamente isolado do pipeline generativo. Ele nao carrega
modelos na importacao e nao usa a GPU ate uma acao explicita do usuario.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
import dlss5_finishing as _dlss5

from capcut_handoff import CapCutHandoffError, create_capcut_local_handoff
from voice_providers import (
    ElevenLabsVoiceProvider,
    PERFORMANCE_DIRECTIONS,
    VoiceProviderError,
    VoiceSettings,
    resolve_chatterbox_settings,
)


SCHEMA_VERSION = 1
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MEDIA_SUFFIXES = VIDEO_SUFFIXES | AUDIO_SUFFIXES | IMAGE_SUFFIXES
TRACKS = {"video", "voice", "music", "sfx", "text"}
ASSISTANT_ACTIONS = {
    "rename_project",
    "trim_clip",
    "move_clip",
    "set_volume",
    "delete_clip",
    "add_text",
}
TERMINAL_JOB_STATES = {"completed", "failed", "canceled", "interrupted"}
VOICE_PREVIEW_MAX_CHARS = 320
CHATTERBOX_MIN_FREE_VRAM_GB = 8.0


class EditorSuiteError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 422, details: Any = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Novo projeto", min_length=1, max_length=120)
    width: int = Field(default=1920, ge=320, le=7680)
    height: int = Field(default=1080, ge=240, le=4320)
    fps: float = Field(default=30.0, ge=1.0, le=120.0)


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    width: Optional[int] = Field(default=None, ge=320, le=7680)
    height: Optional[int] = Field(default=None, ge=240, le=4320)
    fps: Optional[float] = Field(default=None, ge=1.0, le=120.0)


class ClipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    track: Literal["video", "voice", "music", "sfx", "text"]
    assetId: Optional[str] = Field(default=None, max_length=80)
    text: Optional[str] = Field(default=None, max_length=2000)
    sourceStart: float = Field(default=0.0, ge=0.0, le=86400.0)
    sourceEnd: Optional[float] = Field(default=None, gt=0.0, le=86400.0)
    timelineStart: Optional[float] = Field(default=None, ge=0.0, le=86400.0)
    duration: Optional[float] = Field(default=None, gt=0.04, le=86400.0)
    volume: float = Field(default=1.0, ge=0.0, le=4.0)
    label: Optional[str] = Field(default=None, max_length=160)


class ClipPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    sourceStart: Optional[float] = Field(default=None, ge=0.0, le=86400.0)
    sourceEnd: Optional[float] = Field(default=None, gt=0.0, le=86400.0)
    timelineStart: Optional[float] = Field(default=None, ge=0.0, le=86400.0)
    duration: Optional[float] = Field(default=None, gt=0.04, le=86400.0)
    volume: Optional[float] = Field(default=None, ge=0.0, le=4.0)
    muted: Optional[bool] = None
    order: Optional[int] = Field(default=None, ge=0, le=10000)
    label: Optional[str] = Field(default=None, max_length=160)
    text: Optional[str] = Field(default=None, max_length=2000)


class ClipDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)


class RenderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    profile: Literal["preview", "quality"] = "quality"
    encoder: Literal["cpu", "nvenc"] = "cpu"


class VoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=5000)
    engine: Literal["auto", "chatterbox", "system", "elevenlabs_cloud"] = "auto"
    voiceProfileId: Optional[str] = Field(default=None, max_length=80)
    systemVoice: Optional[str] = Field(default=None, max_length=160)
    language: str = Field(default="pt", min_length=2, max_length=12)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    preset: Literal[
        "natural",
        "intense",
        "dramatic",
        "whisper",
        "joyful",
        "sad",
        "angry",
    ] = "natural"
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    exaggeration: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cfgWeight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    temperature: Optional[float] = Field(default=None, ge=0.05, le=2.0)
    repetitionPenalty: Optional[float] = Field(default=None, ge=1.0, le=3.0)
    minP: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    topP: Optional[float] = Field(default=None, ge=0.05, le=1.0)
    providerVoiceId: Optional[str] = Field(default=None, max_length=160)
    modelId: Optional[str] = Field(default=None, max_length=160)
    performanceDirection: Optional[str] = Field(default=None, max_length=500)
    stability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    similarityBoost: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    style: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    speakerBoost: Optional[bool] = None
    mode: Literal["preview", "final"] = "final"
    timelineStart: float = Field(default=0.0, ge=0.0, le=86400.0)
    addToTimeline: bool = True


class AssistantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    instruction: str = Field(min_length=2, max_length=4000)
    apply: bool = False
    model: Optional[str] = Field(default=None, max_length=160)


class AssistantAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "rename_project",
        "trim_clip",
        "move_clip",
        "set_volume",
        "delete_clip",
        "add_text",
    ]
    clipId: Optional[str] = Field(default=None, max_length=80)
    name: Optional[str] = Field(default=None, max_length=120)
    text: Optional[str] = Field(default=None, max_length=2000)
    start: Optional[float] = Field(default=None, ge=0.0, le=86400.0)
    end: Optional[float] = Field(default=None, gt=0.0, le=86400.0)
    duration: Optional[float] = Field(default=None, gt=0.04, le=86400.0)
    volume: Optional[float] = Field(default=None, ge=0.0, le=4.0)
    order: Optional[int] = Field(default=None, ge=0, le=10000)


class AssistantApply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    actions: List[AssistantAction] = Field(min_length=1, max_length=20)


class CaptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRevision: int = Field(ge=1)
    source: Literal["asset", "project"] = "asset"
    assetId: Optional[str] = Field(default=None, max_length=80)
    language: Optional[str] = Field(default="pt", min_length=2, max_length=12)
    timelineStart: float = Field(default=0.0, ge=0.0, le=86400.0)
    replaceExisting: bool = False


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _safe_leaf(value: str, fallback: str = "arquivo") -> str:
    leaf = (value or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    leaf = "".join(
        char if char.isalnum() or char in {" ", ".", "-", "_", "(", ")"} else "_"
        for char in leaf
    ).strip(" .")
    return (leaf or fallback)[:160]


def _safe_project_name(value: str) -> str:
    clean = " ".join((value or "").split()).strip()
    if not clean:
        raise EditorSuiteError("INVALID_PROJECT_NAME", "Informe um nome para o projeto.")
    return clean[:120]


def _safe_id(value: str, label: str) -> str:
    clean = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", clean):
        raise EditorSuiteError("INVALID_ID", f"{label} invalido.", 400)
    return clean


def _float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or result in {float("inf"), float("-inf")}:
        return default
    return result


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _local_voice_controls(spec: Dict[str, Any]) -> Dict[str, float]:
    """Resolve controles expressivos sem carregar ou executar o modelo neural."""

    aliases = {
        "exaggeration": "exaggeration",
        "cfgWeight": "cfgWeight",
        "temperature": "temperature",
        "repetitionPenalty": "repetitionPenalty",
        "minP": "minP",
        "topP": "topP",
    }
    overrides = {
        output_name: spec[input_name]
        for input_name, output_name in aliases.items()
        if spec.get(input_name) is not None
    }
    return resolve_chatterbox_settings(
        str(spec.get("preset") or "natural"),
        _float(spec.get("intensity"), 0.5),
        overrides or None,
    )


_ELEVENLABS_EDITOR_PRESETS = {
    "natural": "stable_longform",
    "intense": "expressive_v3",
    "dramatic": "expressive_v3",
    "whisper": "expressive_v3",
    "joyful": "expressive_v3",
    "sad": "expressive_v3",
    "angry": "expressive_v3",
}
_ELEVENLABS_MODEL_PRESETS = {
    "eleven_v3": "expressive_v3",
    "eleven_multilingual_v2": "stable_longform",
    "eleven_flash_v2_5": "preview",
}


def _elevenlabs_direction(spec: Dict[str, Any]) -> str:
    """Map the editor's free direction field to the provider allowlist."""

    preset = str(spec.get("preset") or "natural").strip().lower()
    direction = str(spec.get("performanceDirection") or "").strip().lower()
    for candidate in PERFORMANCE_DIRECTIONS:
        if candidate in direction:
            return candidate
    for keyword, candidate in (
        ("sussur", "whisper"),
        ("íntim", "intimate"),
        ("intim", "intimate"),
        ("suspense", "suspenseful"),
        ("sarcast", "sarcastic"),
        ("alegr", "joyful"),
        ("triste", "sad"),
        ("raiva", "angry"),
        ("furios", "angry"),
        ("dramát", "dramatic"),
        ("dramat", "dramatic"),
        ("intens", "intense"),
    ):
        if keyword in direction:
            return candidate
    return preset if preset in PERFORMANCE_DIRECTIONS else "neutral"


def _elevenlabs_request(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Build one safe, shared cloud contract from the editor controls."""

    requested_model = str(spec.get("modelId") or "").strip()
    preset = _ELEVENLABS_MODEL_PRESETS.get(
        requested_model,
        _ELEVENLABS_EDITOR_PRESETS.get(str(spec.get("preset") or "natural"), "stable_longform"),
    )
    direction = _elevenlabs_direction(spec)
    speed = max(0.5, min(2.0, _float(spec.get("speed"), 1.0)))
    model_id = requested_model or {
        "expressive_v3": "eleven_v3",
        "stable_longform": "eleven_multilingual_v2",
        "preview": "eleven_flash_v2_5",
    }[preset]
    is_v3 = model_id.startswith("eleven_v3")
    provider_speed = 1.0 if is_v3 else max(0.7, min(1.2, speed))
    if not is_v3:
        # v2/Flash do not accept v3 performance tags; preserve the request by
        # using their stable provider contract instead of failing late upstream.
        direction = "neutral"
    voice_settings = None
    if not is_v3 and any(
        spec.get(key) is not None
        for key in ("stability", "similarityBoost", "style", "speakerBoost")
    ):
        voice_settings = VoiceSettings(
            stability=max(0.0, min(1.0, _float(spec.get("stability"), 0.62))),
            similarity_boost=max(0.0, min(1.0, _float(spec.get("similarityBoost"), 0.78))),
            style=max(0.0, min(1.0, _float(spec.get("style"), 0.08))),
            use_speaker_boost=(
                bool(spec.get("speakerBoost"))
                if spec.get("speakerBoost") is not None
                else True
            ),
            speed=provider_speed,
        )
    return {
        "preset": preset,
        "model_id": model_id,
        "language_code": str(spec.get("language") or "pt").replace("_", "-"),
        "direction": direction,
        "audio_tags": list(PERFORMANCE_DIRECTIONS.get(direction, ())) if is_v3 else [],
        "voice_settings": voice_settings,
        "requested_speed": speed,
        "provider_speed": provider_speed,
    }


def _atomic_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EditorSuiteError("NOT_FOUND", "Registro nao encontrado.", 404) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorSuiteError("CORRUPT_STATE", "O estado salvo esta corrompido.", 500) from exc
    if not isinstance(data, dict):
        raise EditorSuiteError("CORRUPT_STATE", "O estado salvo e invalido.", 500)
    return data


def _bounded_copy(upload: UploadFile, target: Path, max_bytes: int) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.upload")
    total = 0
    try:
        upload.file.seek(0)
        with temp.open("xb") as handle:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise EditorSuiteError(
                        "UPLOAD_TOO_LARGE",
                        f"O arquivo excede o limite de {max_bytes // (1024 * 1024)} MB.",
                        413,
                    )
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
        return total
    finally:
        temp.unlink(missing_ok=True)
        try:
            upload.file.close()
        except Exception:
            pass


def _powershell_encoded(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _error_response(exc: EditorSuiteError) -> JSONResponse:
    body: Dict[str, Any] = {
        "ok": False,
        "error": {"code": exc.code, "message": str(exc)},
    }
    if exc.details is not None:
        body["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status, content=body)


class EditorSuite:
    def __init__(
        self,
        root: Path,
        *,
        ffmpeg: str = "ffmpeg",
        ffprobe: str = "ffprobe",
        ollama_url: str = "http://127.0.0.1:11434",
        max_upload_bytes: int = 2 * 1024 * 1024 * 1024,
        finish_media: Callable | None = None,
        recover_jobs: bool = True,
    ):
        self.root = Path(root).resolve()
        self.projects_root = self.root / "projects"
        self.jobs_root = self.root / "jobs"
        self.voices_root = self.root / "voices"
        self.runtime_root = self.root / "runtime"
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.finish_media = finish_media or _dlss5.finish_file
        self.ollama_url = ollama_url.rstrip("/")
        self.max_upload_bytes = max(1024 * 1024, int(max_upload_bytes))
        self.lock = threading.RLock()
        self.process_lock = threading.RLock()
        self.processes: Dict[str, subprocess.Popen[str]] = {}
        self.voice_gpu_lock = threading.RLock()
        self._voice_gpu_job_id = ""
        self.asr_lock = threading.RLock()
        self._asr_model: Any = None
        self._asr_model_path = ""
        self.voice_provider_lock = threading.RLock()
        self._elevenlabs_capability_cache: Dict[str, Any] = {
            "expiresAt": 0.0,
            "value": None,
        }
        for folder in (
            self.projects_root,
            self.jobs_root,
            self.voices_root,
            self.runtime_root,
        ):
            folder.mkdir(parents=True, exist_ok=True)
        if recover_jobs:
            self._mark_interrupted_jobs()

    # ---------- caminhos e persistencia ----------

    def _project_dir(self, project_id: str) -> Path:
        project_id = _safe_id(project_id, "Projeto")
        path = (self.projects_root / project_id).resolve()
        if path.parent != self.projects_root:
            raise EditorSuiteError("INVALID_ID", "Projeto invalido.", 400)
        return path

    def _project_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def _load_project(self, project_id: str) -> Dict[str, Any]:
        project = _read_json(self._project_path(project_id))
        if project.get("projectId") != project_id:
            raise EditorSuiteError("CORRUPT_STATE", "Identidade do projeto inconsistente.", 500)
        return project

    def _check_revision(self, project: Dict[str, Any], expected: int) -> None:
        actual = int(project.get("revision") or 0)
        if actual != int(expected):
            raise EditorSuiteError(
                "REVISION_CONFLICT",
                "O projeto mudou em outra tela. Atualize antes de salvar.",
                409,
                {"expectedRevision": int(expected), "actualRevision": actual},
            )

    def _save_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        project["revision"] = int(project.get("revision") or 0) + 1
        project["updatedAt"] = _now_iso()
        self._reflow_video(project)
        _atomic_json(self._project_path(project["projectId"]), project)
        return _clone(project)

    def _decorate_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        result = _clone(project)
        project_id = result["projectId"]
        for asset in result.get("assets", []):
            asset["url"] = (
                f"/api/editor/projects/{urllib.parse.quote(project_id)}/assets/"
                f"{urllib.parse.quote(asset['assetId'])}/content"
            )
        exports = []
        for export in result.get("exports", []):
            item = _clone(export)
            item["url"] = (
                f"/api/editor/projects/{urllib.parse.quote(project_id)}/exports/"
                f"{urllib.parse.quote(item['exportId'])}"
            )
            exports.append(item)
        result["exports"] = exports
        result["duration"] = self._timeline_duration(result)
        return result

    def create_project(self, spec: ProjectCreate) -> Dict[str, Any]:
        project_id = uuid.uuid4().hex
        now = _now_iso()
        project = {
            "schemaVersion": SCHEMA_VERSION,
            "projectId": project_id,
            "name": _safe_project_name(spec.name),
            "revision": 1,
            "createdAt": now,
            "updatedAt": now,
            "settings": {
                "width": int(spec.width),
                "height": int(spec.height),
                "fps": float(spec.fps),
                "sampleRate": 48000,
            },
            "assets": [],
            "clips": [],
            "exports": [],
        }
        project_dir = self._project_dir(project_id)
        for folder in ("media", "exports", "work"):
            (project_dir / folder).mkdir(parents=True, exist_ok=True)
        _atomic_json(self._project_path(project_id), project)
        return self._decorate_project(project)

    def list_projects(self, page: int, page_size: int) -> Dict[str, Any]:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        items = []
        with self.lock:
            for project_path in self.projects_root.glob("*/project.json"):
                try:
                    project = _read_json(project_path)
                    items.append(
                        {
                            "projectId": project.get("projectId"),
                            "name": project.get("name"),
                            "revision": project.get("revision"),
                            "updatedAt": project.get("updatedAt"),
                            "assetCount": len(project.get("assets", [])),
                            "clipCount": len(project.get("clips", [])),
                            "duration": self._timeline_duration(project),
                        }
                    )
                except EditorSuiteError:
                    continue
        items.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
        start = (page - 1) * page_size
        return {
            "ok": True,
            "items": items[start : start + page_size],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": len(items),
                "totalPages": max(1, (len(items) + page_size - 1) // page_size),
            },
        }

    def get_project(self, project_id: str) -> Dict[str, Any]:
        with self.lock:
            return self._decorate_project(self._load_project(project_id))

    def patch_project(self, project_id: str, patch: ProjectPatch) -> Dict[str, Any]:
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, patch.expectedRevision)
            if patch.name is not None:
                project["name"] = _safe_project_name(patch.name)
            settings = project["settings"]
            for field in ("width", "height", "fps"):
                value = getattr(patch, field)
                if value is not None:
                    settings[field] = value
            return self._decorate_project(self._save_project(project))

    # ---------- midia e timeline ----------

    def _probe(self, path: Path) -> Dict[str, Any]:
        cmd = [
            self.ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,duration",
            "-of",
            "json",
            str(path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise EditorSuiteError("FFPROBE_UNAVAILABLE", "FFprobe nao esta disponivel.", 503) from exc
        if proc.returncode != 0:
            raise EditorSuiteError(
                "INVALID_MEDIA",
                "O arquivo nao e uma midia valida ou esta corrompido.",
                422,
                proc.stderr[-1000:],
            )
        try:
            data = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise EditorSuiteError("INVALID_MEDIA", "FFprobe retornou dados invalidos.", 422) from exc
        streams = data.get("streams") if isinstance(data.get("streams"), list) else []
        duration = _float((data.get("format") or {}).get("duration"), 0.0)
        video = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
        if duration <= 0:
            duration = max((_float(s.get("duration"), 0.0) for s in streams), default=0.0)
        return {
            "duration": max(0.0, round(duration, 6)),
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "hasVideo": bool(video),
            "hasAudio": bool(audio),
            "videoCodec": str(video.get("codec_name") or ""),
            "audioCodec": str(audio.get("codec_name") or ""),
        }

    def _kind_for_suffix(self, suffix: str) -> str:
        suffix = suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            return "image"
        if suffix in VIDEO_SUFFIXES:
            return "video"
        if suffix in AUDIO_SUFFIXES:
            return "audio"
        return ""

    def add_upload(self, project_id: str, upload: UploadFile) -> Dict[str, Any]:
        safe_name = _safe_leaf(upload.filename or "midia.bin", "midia.bin")
        suffix = Path(safe_name).suffix.lower()
        kind = self._kind_for_suffix(suffix)
        if not kind:
            try:
                upload.file.close()
            except Exception:
                pass
            raise EditorSuiteError(
                "UNSUPPORTED_MEDIA",
                "Use um arquivo de video, audio ou imagem compativel.",
                415,
            )
        asset_id = uuid.uuid4().hex
        with self.lock:
            project = self._load_project(project_id)
            project_dir = self._project_dir(project_id)
            target = (project_dir / "media" / f"{asset_id}_{safe_name}").resolve()
            if project_dir not in target.parents:
                raise EditorSuiteError("INVALID_MEDIA_PATH", "Destino de midia invalido.", 400)
            try:
                size = _bounded_copy(upload, target, self.max_upload_bytes)
                probe = self._probe(target)
                if kind == "video" and not probe["hasVideo"]:
                    raise EditorSuiteError("INVALID_MEDIA", "O arquivo nao contem video.", 422)
                if kind == "audio" and not probe["hasAudio"]:
                    raise EditorSuiteError("INVALID_MEDIA", "O arquivo nao contem audio.", 422)
                asset = {
                    "assetId": asset_id,
                    "name": safe_name,
                    "kind": kind,
                    "relativePath": target.relative_to(project_dir).as_posix(),
                    "mediaType": upload.content_type
                    or mimetypes.guess_type(safe_name)[0]
                    or "application/octet-stream",
                    "size": size,
                    "duration": probe["duration"],
                    "width": probe["width"],
                    "height": probe["height"],
                    "hasAudio": probe["hasAudio"],
                    "createdAt": _now_iso(),
                    "source": "upload",
                }
                project.setdefault("assets", []).append(asset)
                saved = self._save_project(project)
                return next(
                    item
                    for item in self._decorate_project(saved)["assets"]
                    if item["assetId"] == asset_id
                )
            except Exception:
                target.unlink(missing_ok=True)
                raise

    def _asset(self, project: Dict[str, Any], asset_id: str) -> Dict[str, Any]:
        asset_id = _safe_id(asset_id, "Arquivo")
        asset = next((a for a in project.get("assets", []) if a.get("assetId") == asset_id), None)
        if not asset:
            raise EditorSuiteError("ASSET_NOT_FOUND", "Arquivo nao encontrado.", 404)
        return asset

    def asset_path(self, project_id: str, asset_id: str) -> tuple[Path, Dict[str, Any]]:
        with self.lock:
            project = self._load_project(project_id)
            asset = self._asset(project, asset_id)
            project_dir = self._project_dir(project_id)
            path = (project_dir / str(asset.get("relativePath") or "")).resolve(strict=True)
            if project_dir not in path.parents or not path.is_file():
                raise EditorSuiteError("ASSET_NOT_FOUND", "Arquivo nao encontrado.", 404)
            return path, _clone(asset)

    def _normalize_clip(
        self,
        project: Dict[str, Any],
        payload: Dict[str, Any],
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clip = _clone(existing) if existing else {}
        clip.update({key: value for key, value in payload.items() if value is not None})
        track = str(clip.get("track") or "")
        if track not in TRACKS:
            raise EditorSuiteError("INVALID_TRACK", "Trilha invalida.")
        if track == "text":
            text = str(clip.get("text") or "").strip()
            if not text:
                raise EditorSuiteError("TEXT_REQUIRED", "Informe o texto do cartao.")
            clip["text"] = text[:2000]
            clip["assetId"] = None
            duration = _float(clip.get("duration"), 3.0)
            if duration <= 0.04:
                raise EditorSuiteError("INVALID_DURATION", "Duracao invalida.")
            clip["duration"] = round(duration, 6)
            clip["sourceStart"] = 0.0
            clip["sourceEnd"] = duration
        else:
            asset = self._asset(project, str(clip.get("assetId") or ""))
            expected_kind = "video" if track == "video" else "audio"
            if track == "video" and asset["kind"] not in {"video", "image"}:
                raise EditorSuiteError("INVALID_ASSET_KIND", "Use imagem ou video nesta trilha.")
            if track != "video" and asset["kind"] != expected_kind:
                raise EditorSuiteError("INVALID_ASSET_KIND", "Use um arquivo de audio nesta trilha.")
            source_start = max(0.0, _float(clip.get("sourceStart"), 0.0))
            asset_duration = _float(asset.get("duration"), 0.0)
            if asset["kind"] == "image":
                duration = _float(clip.get("duration"), 4.0)
                source_end = duration
            else:
                requested_end = clip.get("sourceEnd")
                source_end = (
                    _float(requested_end, asset_duration)
                    if requested_end is not None
                    else asset_duration
                )
                if source_end <= source_start:
                    requested_duration = _float(clip.get("duration"), 0.0)
                    source_end = source_start + requested_duration
                if asset_duration > 0 and source_end > asset_duration + 0.05:
                    raise EditorSuiteError(
                        "TRIM_OUT_OF_RANGE",
                        "O corte ultrapassa a duracao do arquivo.",
                    )
                duration = source_end - source_start
            if duration <= 0.04:
                raise EditorSuiteError("INVALID_DURATION", "O clipe precisa ter duracao positiva.")
            clip["sourceStart"] = round(source_start, 6)
            clip["sourceEnd"] = round(source_end, 6)
            clip["duration"] = round(duration, 6)
        clip["timelineStart"] = round(max(0.0, _float(clip.get("timelineStart"), 0.0)), 6)
        clip["volume"] = round(max(0.0, min(4.0, _float(clip.get("volume"), 1.0))), 4)
        clip["muted"] = bool(clip.get("muted", False))
        clip["label"] = str(clip.get("label") or "").strip()[:160]
        return clip

    def _reflow_video(self, project: Dict[str, Any]) -> None:
        video = sorted(
            (clip for clip in project.get("clips", []) if clip.get("track") == "video"),
            key=lambda clip: (int(clip.get("order") or 0), str(clip.get("clipId") or "")),
        )
        cursor = 0.0
        for order, clip in enumerate(video):
            clip["order"] = order
            clip["timelineStart"] = round(cursor, 6)
            cursor += _float(clip.get("duration"), 0.0)
        track_order = {"video": 0, "voice": 1, "music": 2, "sfx": 3, "text": 4}
        project["clips"] = sorted(
            project.get("clips", []),
            key=lambda clip: (
                track_order.get(str(clip.get("track") or ""), 99),
                int(clip.get("order") or 0)
                if clip.get("track") == "video"
                else _float(clip.get("timelineStart"), 0.0),
                int(clip.get("order") or 0),
                str(clip.get("clipId") or ""),
            ),
        )

    def _timeline_duration(self, project: Dict[str, Any]) -> float:
        return round(
            max(
                (
                    _float(clip.get("timelineStart"), 0.0)
                    + _float(clip.get("duration"), 0.0)
                    for clip in project.get("clips", [])
                ),
                default=0.0,
            ),
            6,
        )

    def add_clip(self, project_id: str, spec: ClipCreate) -> Dict[str, Any]:
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, spec.expectedRevision)
            payload = spec.model_dump()
            payload.pop("expectedRevision", None)
            same_track = [c for c in project.get("clips", []) if c.get("track") == spec.track]
            payload["clipId"] = uuid.uuid4().hex
            payload["order"] = len(same_track)
            payload["createdAt"] = _now_iso()
            clip = self._normalize_clip(project, payload)
            project.setdefault("clips", []).append(clip)
            return self._decorate_project(self._save_project(project))

    def patch_clip(self, project_id: str, clip_id: str, patch: ClipPatch) -> Dict[str, Any]:
        clip_id = _safe_id(clip_id, "Clipe")
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, patch.expectedRevision)
            index = next(
                (i for i, item in enumerate(project.get("clips", [])) if item.get("clipId") == clip_id),
                -1,
            )
            if index < 0:
                raise EditorSuiteError("CLIP_NOT_FOUND", "Clipe nao encontrado.", 404)
            payload = patch.model_dump(exclude_none=True)
            payload.pop("expectedRevision", None)
            updated_clip = self._normalize_clip(project, payload, project["clips"][index])
            project["clips"][index] = updated_clip
            if "order" in payload:
                same_track = sorted(
                    (
                        item
                        for item in project["clips"]
                        if item.get("track") == updated_clip.get("track")
                        and item.get("clipId") != clip_id
                    ),
                    key=lambda item: (int(item.get("order") or 0), str(item.get("clipId") or "")),
                )
                destination = max(0, min(len(same_track), int(payload["order"])))
                same_track.insert(destination, updated_clip)
                for order, item in enumerate(same_track):
                    item["order"] = order
            return self._decorate_project(self._save_project(project))

    def delete_clip(self, project_id: str, clip_id: str, expected_revision: int) -> Dict[str, Any]:
        clip_id = _safe_id(clip_id, "Clipe")
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, expected_revision)
            before = len(project.get("clips", []))
            project["clips"] = [
                item for item in project.get("clips", []) if item.get("clipId") != clip_id
            ]
            if len(project["clips"]) == before:
                raise EditorSuiteError("CLIP_NOT_FOUND", "Clipe nao encontrado.", 404)
            return self._decorate_project(self._save_project(project))

    # ---------- jobs ----------

    def _job_path(self, job_id: str) -> Path:
        return self.jobs_root / f"{_safe_id(job_id, 'Job')}.json"

    def _mark_interrupted_jobs(self) -> None:
        with self.lock:
            for path in self.jobs_root.glob("*.json"):
                try:
                    job = _read_json(path)
                except EditorSuiteError:
                    continue
                if job.get("status") in {"queued", "running", "canceling"}:
                    job["status"] = "interrupted"
                    job["message"] = "Interrompido por reinicio; o projeto foi preservado."
                    job["updatedAt"] = _now_iso()
                    _atomic_json(path, job)

    def _create_job(self, project_id: str, kind: str, message: str) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex
        now = _now_iso()
        job = {
            "jobId": job_id,
            "projectId": project_id,
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "message": message,
            "createdAt": now,
            "updatedAt": now,
            "error": None,
            "result": None,
        }
        _atomic_json(self._job_path(job_id), job)
        return job

    def _update_job(self, job_id: str, **changes: Any) -> Dict[str, Any]:
        with self.lock:
            job = _read_json(self._job_path(job_id))
            job.update(changes)
            job["updatedAt"] = _now_iso()
            _atomic_json(self._job_path(job_id), job)
            return _clone(job)

    def get_job(self, job_id: str) -> Dict[str, Any]:
        with self.lock:
            return _read_json(self._job_path(job_id))

    def list_jobs(self, project_id: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        items = []
        with self.lock:
            for path in self.jobs_root.glob("*.json"):
                try:
                    job = _read_json(path)
                except EditorSuiteError:
                    continue
                if project_id and job.get("projectId") != project_id:
                    continue
                items.append(job)
        items.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
        return items[:limit]

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        job = self.get_job(job_id)
        if job.get("status") in TERMINAL_JOB_STATES:
            return job
        self._update_job(job_id, status="canceling", message="Cancelando...")
        with self.process_lock:
            process = self.processes.get(job_id)
            if process and process.poll() is None:
                process.terminate()
        return self.get_job(job_id)

    # ---------- legendas offline (CPU) ----------

    @staticmethod
    def _valid_whisper_model_dir(path: Path) -> bool:
        return (
            path.is_dir()
            and (path / "model.bin").is_file()
            and (path / "config.json").is_file()
        )

    def _offline_whisper_models(self) -> List[Dict[str, str]]:
        candidates: List[tuple[str, Path]] = []
        configured = os.environ.get("MAESTRO_EDITOR_WHISPER_MODEL", "").strip()
        if configured:
            configured_path = Path(configured).expanduser()
            if configured_path.is_absolute():
                candidates.append(("configured", configured_path))
                candidates.extend(
                    ("configured", item)
                    for item in configured_path.glob("snapshots/*")
                    if item.is_dir()
                )

        cache_roots: List[Path] = []
        for raw_root in (
            os.environ.get("HUGGINGFACE_HUB_CACHE", ""),
            (
                str(Path(os.environ["HF_HOME"]).expanduser() / "hub")
                if os.environ.get("HF_HOME")
                else ""
            ),
            str(Path.home() / ".cache" / "huggingface" / "hub"),
        ):
            if raw_root:
                root = Path(raw_root).expanduser()
                if root not in cache_roots:
                    cache_roots.append(root)

        requested_size = os.environ.get("MAESTRO_EDITOR_WHISPER_SIZE", "base").strip().lower()
        sizes = [requested_size, "base", "tiny"]
        for root in cache_roots:
            for size in dict.fromkeys(item for item in sizes if item):
                repo = root / f"models--Systran--faster-whisper-{size}"
                candidates.extend(
                    (size, item)
                    for item in repo.glob("snapshots/*")
                    if item.is_dir()
                )

        result: List[Dict[str, str]] = []
        seen: set[str] = set()
        for name, candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            key = os.path.normcase(str(resolved))
            if key in seen or not self._valid_whisper_model_dir(resolved):
                continue
            seen.add(key)
            detected_name = name
            repo_name = resolved.parent.parent.name
            prefix = "models--Systran--faster-whisper-"
            if repo_name.startswith(prefix):
                detected_name = repo_name[len(prefix) :]
            result.append({"name": detected_name, "path": str(resolved)})
        return result

    def _resolve_offline_whisper_model(self) -> Path:
        try:
            package_ready = importlib.util.find_spec("faster_whisper") is not None
        except (ImportError, ValueError):
            package_ready = False
        models = self._offline_whisper_models()
        if not package_ready or not models:
            raise EditorSuiteError(
                "OFFLINE_ASR_UNAVAILABLE",
                "O modelo local de legendas nao esta instalado nesta maquina.",
                503,
            )
        return Path(models[0]["path"])

    def _caption_audio_clips(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for clip in project.get("clips", []):
            if clip.get("track") not in {"video", "voice", "music", "sfx"}:
                continue
            if clip.get("muted") or _float(clip.get("volume"), 1.0) <= 0:
                continue
            asset = self._asset(project, str(clip.get("assetId") or ""))
            if not asset.get("hasAudio"):
                continue
            items.append({"clip": clip, "asset": asset})
        return items

    def _prepare_caption_audio(
        self,
        job_id: str,
        project: Dict[str, Any],
        spec: Dict[str, Any],
        output: Path,
    ) -> bool:
        source = str(spec.get("source") or "asset")
        command = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        filters: List[str] = []
        if source == "asset":
            asset = self._asset(project, str(spec.get("assetId") or ""))
            if not asset.get("hasAudio"):
                raise EditorSuiteError(
                    "CAPTION_SOURCE_HAS_NO_AUDIO",
                    "O arquivo escolhido nao contem audio.",
                )
            command.extend(["-i", str(self._asset_local_path(project, asset["assetId"]))])
            filters.append("[0:a]aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[mix]")
        else:
            audio_clips = self._caption_audio_clips(project)
            if not audio_clips:
                raise EditorSuiteError(
                    "CAPTION_SOURCE_HAS_NO_AUDIO",
                    "A timeline ainda nao contem audio para transcrever.",
                )
            labels: List[str] = []
            for index, item in enumerate(audio_clips):
                clip = item["clip"]
                command.extend(
                    ["-i", str(self._asset_local_path(project, item["asset"]["assetId"]))]
                )
                source_start = max(0.0, _float(clip.get("sourceStart"), 0.0))
                source_end = source_start + max(0.04, _float(clip.get("duration"), 0.0))
                delay_ms = max(0, int(round(_float(clip.get("timelineStart"), 0.0) * 1000)))
                volume = max(0.0, min(4.0, _float(clip.get("volume"), 1.0)))
                label = f"a{index}"
                filters.append(
                    f"[{index}:a]"
                    f"atrim=start={source_start:.6f}:end={source_end:.6f},"
                    "asetpts=PTS-STARTPTS,"
                    f"volume={volume:.4f},"
                    f"adelay={delay_ms}:all=1"
                    f"[{label}]"
                )
                labels.append(f"[{label}]")
            if len(labels) == 1:
                filters.append(f"{labels[0]}aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[mix]")
            else:
                filters.append(
                    "".join(labels)
                    + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:"
                    "normalize=0,alimiter=limit=0.95,"
                    "aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[mix]"
                )
        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[mix]",
                "-vn",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        with self.process_lock:
            self.processes[job_id] = process
        stdout, stderr = process.communicate()
        current = self.get_job(job_id)
        if current.get("status") == "canceling":
            self._update_job(
                job_id,
                status="canceled",
                progress=100,
                message="Geracao de legendas cancelada.",
            )
            return False
        if process.returncode != 0 or not output.is_file():
            raise EditorSuiteError(
                "CAPTION_AUDIO_PREP_FAILED",
                "Nao foi possivel preparar o audio para as legendas.",
                500,
                (stderr or stdout)[-3000:],
            )
        return True

    def _transcribe_cpu(
        self,
        model_path: Path,
        audio_path: Path,
        *,
        language: Optional[str],
        duration: float,
        on_progress: Callable[[int], None],
    ) -> Dict[str, Any]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise EditorSuiteError(
                "OFFLINE_ASR_UNAVAILABLE",
                "Faster Whisper nao esta instalado.",
                503,
            ) from exc
        try:
            with self.asr_lock:
                resolved_model = str(model_path.resolve())
                if self._asr_model is None or self._asr_model_path != resolved_model:
                    self._asr_model = WhisperModel(
                        resolved_model,
                        device="cpu",
                        compute_type="int8",
                        local_files_only=True,
                        cpu_threads=max(1, min(8, (os.cpu_count() or 4) // 2)),
                        num_workers=1,
                    )
                    self._asr_model_path = resolved_model
                segments_iter, info = self._asr_model.transcribe(
                    str(audio_path),
                    language=(language or None),
                    beam_size=3,
                    vad_filter=True,
                    word_timestamps=False,
                    condition_on_previous_text=True,
                )
                segments: List[Dict[str, Any]] = []
                for segment in segments_iter:
                    text = " ".join(str(segment.text or "").split()).strip()
                    if not text:
                        continue
                    start = max(0.0, _float(segment.start, 0.0))
                    end = max(start + 0.04, _float(segment.end, start + 0.04))
                    segments.append(
                        {
                            "start": round(start, 3),
                            "end": round(end, 3),
                            "text": text[:2000],
                        }
                    )
                    ratio = min(1.0, end / max(0.1, duration))
                    on_progress(45 + int(ratio * 40))
                return {
                    "language": str(getattr(info, "language", "") or language or ""),
                    "segments": segments,
                }
        except EditorSuiteError:
            raise
        except Exception as exc:
            raise EditorSuiteError(
                "CAPTION_TRANSCRIPTION_FAILED",
                "O Faster Whisper local nao conseguiu transcrever o audio.",
                500,
                str(exc)[:2000],
            ) from exc

    def transcribe_short_audio(
        self,
        audio_path: Path,
        *,
        language: Optional[str] = "pt",
        max_duration_seconds: float = 120.0,
    ) -> Dict[str, Any]:
        """Transcreve um ditado curto sem persistir o audio nem usar a GPU."""

        source = Path(audio_path).resolve()
        if not source.is_file():
            raise EditorSuiteError(
                "INVALID_AUDIO",
                "O audio enviado nao foi encontrado.",
                422,
            )
        normalized_language = (language or "").strip().lower() or None
        if normalized_language not in {None, "pt", "en"}:
            raise EditorSuiteError(
                "INVALID_LANGUAGE",
                "Use portugues, ingles ou deteccao automatica.",
                422,
            )
        max_duration = max(1.0, min(300.0, float(max_duration_seconds)))
        source_probe = self._probe(source)
        if not source_probe.get("hasAudio"):
            raise EditorSuiteError(
                "INVALID_AUDIO",
                "O arquivo enviado nao contem uma faixa de audio.",
                422,
            )

        model_path = self._resolve_offline_whisper_model()
        with tempfile.TemporaryDirectory(prefix="maestro-dictation-") as work_dir:
            normalized = Path(work_dir) / "dictation.wav"
            command = [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-vn",
                "-t",
                f"{max_duration + 1.0:.3f}",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(normalized),
            ]
            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise EditorSuiteError(
                    "AUDIO_PREPARATION_FAILED",
                    "Nao foi possivel preparar o audio para transcricao.",
                    503,
                ) from exc
            if process.returncode != 0 or not normalized.is_file():
                raise EditorSuiteError(
                    "INVALID_AUDIO",
                    "O arquivo de audio esta corrompido ou usa um formato nao suportado.",
                    422,
                )

            probe = self._probe(normalized)
            duration = _float(probe.get("duration"), 0.0)
            if duration <= 0:
                raise EditorSuiteError(
                    "INVALID_AUDIO",
                    "Nao foi possivel medir a duracao do audio.",
                    422,
                )
            if duration > max_duration + 0.25:
                raise EditorSuiteError(
                    "AUDIO_TOO_LONG",
                    f"O ditado pode ter no maximo {int(max_duration)} segundos.",
                    413,
                )

            transcription = self._transcribe_cpu(
                model_path,
                normalized,
                language=normalized_language,
                duration=duration,
                on_progress=lambda _progress: None,
            )
            segments = transcription.get("segments")
            if not isinstance(segments, list):
                segments = []
            text = " ".join(
                str(segment.get("text") or "").strip()
                for segment in segments
                if isinstance(segment, dict) and str(segment.get("text") or "").strip()
            ).strip()
            if not text:
                raise EditorSuiteError(
                    "NO_SPEECH_DETECTED",
                    "Nenhuma fala foi detectada no audio.",
                    422,
                )
            model_name = next(
                (
                    item["name"]
                    for item in self._offline_whisper_models()
                    if Path(item["path"]).resolve() == model_path.resolve()
                ),
                model_path.name,
            )
            return {
                "text": text[:12000],
                "language": str(transcription.get("language") or normalized_language or ""),
                "durationSeconds": round(duration, 3),
                "segmentCount": len(segments),
                "engine": "faster-whisper",
                "model": model_name,
                "device": "cpu",
                "computeType": "int8",
            }

    def start_captions(self, project_id: str, spec: CaptionCreate) -> Dict[str, Any]:
        model_path = self._resolve_offline_whisper_model()
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, spec.expectedRevision)
            if spec.source == "asset":
                if not spec.assetId:
                    raise EditorSuiteError(
                        "CAPTION_ASSET_REQUIRED",
                        "Escolha um arquivo de audio ou video para transcrever.",
                    )
                asset = self._asset(project, spec.assetId)
                if not asset.get("hasAudio"):
                    raise EditorSuiteError(
                        "CAPTION_SOURCE_HAS_NO_AUDIO",
                        "O arquivo escolhido nao contem audio.",
                    )
            elif spec.assetId:
                raise EditorSuiteError(
                    "AMBIGUOUS_CAPTION_SOURCE",
                    "Para transcrever a timeline, nao envie assetId.",
                )
            elif not self._caption_audio_clips(project):
                raise EditorSuiteError(
                    "CAPTION_SOURCE_HAS_NO_AUDIO",
                    "A timeline ainda nao contem audio para transcrever.",
                )
            job = self._create_job(project_id, "captions", "Legendas offline na fila.")
            job = self._update_job(
                job["jobId"],
                sourceRevision=int(project["revision"]),
                source=spec.source,
                sourceAssetId=spec.assetId,
                engine="faster-whisper",
                device="cpu",
                computeType="int8",
            )
            project_snapshot = _clone(project)
        thread = threading.Thread(
            target=self._captions_worker,
            args=(
                job["jobId"],
                project_id,
                spec.model_dump(),
                project_snapshot,
                str(model_path),
            ),
            name=f"maestro-editor-captions-{job['jobId'][:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def _captions_worker(
        self,
        job_id: str,
        project_id: str,
        spec: Dict[str, Any],
        project_snapshot: Dict[str, Any],
        model_path: str,
    ) -> None:
        work_dir = self.runtime_root / job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            audio_path = work_dir / "caption_source.wav"
            self._update_job(
                job_id,
                status="running",
                progress=5,
                message="Preparando audio localmente.",
            )
            if not self._prepare_caption_audio(
                job_id,
                project_snapshot,
                spec,
                audio_path,
            ):
                return
            probe = self._probe(audio_path)
            self._update_job(
                job_id,
                progress=40,
                message="Transcrevendo em CPU, sem enviar arquivos para a nuvem.",
            )
            transcription = self._transcribe_cpu(
                Path(model_path),
                audio_path,
                language=spec.get("language"),
                duration=max(0.1, _float(probe.get("duration"), 0.0)),
                on_progress=lambda progress: self._update_job(
                    job_id,
                    progress=max(40, min(88, int(progress))),
                    message="Transcrevendo em CPU, sem enviar arquivos para a nuvem.",
                ),
            )
            segments = transcription.get("segments")
            if not isinstance(segments, list) or not segments:
                raise EditorSuiteError(
                    "NO_SPEECH_DETECTED",
                    "Nenhuma fala foi detectada no audio escolhido.",
                )
            if self.get_job(job_id).get("status") == "canceling":
                self._update_job(
                    job_id,
                    status="canceled",
                    progress=100,
                    message="Geracao de legendas cancelada.",
                )
                return
            self._update_job(
                job_id,
                progress=92,
                message="Aplicando legendas ao projeto de forma atomica.",
            )
            with self.lock:
                project = self._load_project(project_id)
                self._check_revision(project, int(spec["expectedRevision"]))
                if spec.get("replaceExisting"):
                    project["clips"] = [
                        clip
                        for clip in project.get("clips", [])
                        if clip.get("generatedBy") != "offline_cpu_asr"
                    ]
                source_offset = (
                    _float(spec.get("timelineStart"), 0.0)
                    if spec.get("source") == "asset"
                    else 0.0
                )
                base_order = len(
                    [clip for clip in project.get("clips", []) if clip.get("track") == "text"]
                )
                caption_ids: List[str] = []
                for index, segment in enumerate(segments):
                    text = " ".join(str(segment.get("text") or "").split()).strip()
                    if not text:
                        continue
                    start = source_offset + max(0.0, _float(segment.get("start"), 0.0))
                    end = source_offset + max(
                        _float(segment.get("end"), start + 0.04),
                        start + 0.04,
                    )
                    clip_id = uuid.uuid4().hex
                    clip = self._normalize_clip(
                        project,
                        {
                            "clipId": clip_id,
                            "track": "text",
                            "assetId": None,
                            "text": text[:2000],
                            "timelineStart": start,
                            "duration": end - start,
                            "sourceStart": 0.0,
                            "sourceEnd": end - start,
                            "volume": 1.0,
                            "muted": False,
                            "order": base_order + index,
                            "label": "Legenda automatica",
                            "createdAt": _now_iso(),
                            "generatedBy": "offline_cpu_asr",
                            "captionJobId": job_id,
                            "captionSource": spec.get("source"),
                            "captionSourceAssetId": spec.get("assetId"),
                            "language": transcription.get("language") or spec.get("language") or "",
                        },
                    )
                    project.setdefault("clips", []).append(clip)
                    caption_ids.append(clip_id)
                if not caption_ids:
                    raise EditorSuiteError(
                        "NO_SPEECH_DETECTED",
                        "Nenhuma fala utilizavel foi detectada no audio escolhido.",
                    )
                saved = self._save_project(project)
            decorated = self._decorate_project(saved)
            self._update_job(
                job_id,
                status="completed",
                progress=100,
                message=f"{len(caption_ids)} legendas adicionadas ao projeto.",
                result={
                    "captionCount": len(caption_ids),
                    "captionClipIds": caption_ids,
                    "language": transcription.get("language") or spec.get("language") or "",
                    "project": decorated,
                },
            )
        except EditorSuiteError as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                message=str(exc),
                error={"code": exc.code, "message": str(exc), "details": exc.details},
            )
        except Exception as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                message="Falha inesperada ao gerar legendas.",
                error={"code": "CAPTION_GENERATION_FAILED", "message": str(exc)},
            )
        finally:
            with self.process_lock:
                self.processes.pop(job_id, None)
            shutil.rmtree(work_dir, ignore_errors=True)

    # ---------- render ----------

    def _asset_local_path(self, project: Dict[str, Any], asset_id: str) -> Path:
        asset = self._asset(project, asset_id)
        project_dir = self._project_dir(project["projectId"])
        path = (project_dir / asset["relativePath"]).resolve(strict=True)
        if project_dir not in path.parents or not path.is_file():
            raise EditorSuiteError("ASSET_NOT_FOUND", "Arquivo do clipe nao foi encontrado.", 404)
        return path

    @staticmethod
    def _filter_path(path: Path) -> str:
        value = path.resolve().as_posix().replace("\\", "/")
        value = value.replace(":", r"\:").replace("'", r"\'")
        return value

    def _render_command(
        self,
        project: Dict[str, Any],
        output: Path,
        *,
        profile: str,
        encoder: str,
        work_dir: Path,
    ) -> tuple[List[str], float]:
        video_clips = sorted(
            (clip for clip in project.get("clips", []) if clip.get("track") == "video"),
            key=lambda clip: int(clip.get("order") or 0),
        )
        if not video_clips:
            raise EditorSuiteError("EMPTY_TIMELINE", "Adicione imagem ou video na timeline.")
        settings = project["settings"]
        width = int(settings["width"])
        height = int(settings["height"])
        fps = float(settings["fps"])
        total = sum(_float(clip.get("duration"), 0.0) for clip in video_clips)
        if total <= 0.04:
            raise EditorSuiteError("EMPTY_TIMELINE", "A timeline nao possui duracao.")

        cmd: List[str] = [self.ffmpeg, "-hide_banner", "-y"]
        input_map: List[tuple[Dict[str, Any], Dict[str, Any], int]] = []
        input_index = 0
        for clip in video_clips:
            asset = self._asset(project, clip["assetId"])
            path = self._asset_local_path(project, clip["assetId"])
            if asset["kind"] == "image":
                cmd.extend(["-loop", "1", "-t", f"{clip['duration']:.6f}"])
            cmd.extend(["-i", str(path)])
            input_map.append((clip, asset, input_index))
            input_index += 1

        audio_clips = sorted(
            (
                clip
                for clip in project.get("clips", [])
                if clip.get("track") in {"voice", "music", "sfx"} and not clip.get("muted")
            ),
            key=lambda clip: (_float(clip.get("timelineStart"), 0.0), int(clip.get("order") or 0)),
        )
        audio_inputs: List[tuple[Dict[str, Any], Dict[str, Any], int]] = []
        for clip in audio_clips:
            asset = self._asset(project, clip["assetId"])
            path = self._asset_local_path(project, clip["assetId"])
            cmd.extend(["-i", str(path)])
            audio_inputs.append((clip, asset, input_index))
            input_index += 1

        filters: List[str] = []
        video_labels = []
        for number, (clip, asset, index) in enumerate(input_map):
            label = f"v{number}"
            if asset["kind"] == "image":
                trim = f"trim=duration={clip['duration']:.6f}"
            else:
                trim = (
                    f"trim=start={clip['sourceStart']:.6f}:"
                    f"duration={clip['duration']:.6f}"
                )
            filters.append(
                f"[{index}:v]{trim},setpts=PTS-STARTPTS,"
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,fps={fps:.6f},format=yuv420p[{label}]"
            )
            video_labels.append(f"[{label}]")
        filters.append(
            "".join(video_labels)
            + f"concat=n={len(video_labels)}:v=1:a=0[vbase]"
        )

        current_video = "vbase"
        text_clips = [
            clip
            for clip in project.get("clips", [])
            if clip.get("track") == "text" and str(clip.get("text") or "").strip()
        ]
        for number, clip in enumerate(text_clips):
            text_path = work_dir / f"text_{number:03d}.txt"
            text_path.write_text(str(clip["text"]), encoding="utf-8")
            next_video = f"vtext{number}"
            start = _float(clip.get("timelineStart"), 0.0)
            end = start + _float(clip.get("duration"), 0.0)
            filters.append(
                f"[{current_video}]drawtext=textfile='{self._filter_path(text_path)}':"
                "fontcolor=white:fontsize=h/18:borderw=3:bordercolor=black@0.8:"
                "x=(w-text_w)/2:y=h*0.82:"
                f"enable='between(t,{start:.6f},{end:.6f})'[{next_video}]"
            )
            current_video = next_video

        audio_labels = []
        audio_number = 0
        for clip, asset, index in input_map:
            if not asset.get("hasAudio") or clip.get("muted"):
                continue
            label = f"a{audio_number}"
            delay = max(0, int(round(_float(clip.get("timelineStart"), 0.0) * 1000)))
            filters.append(
                f"[{index}:a]atrim=start={clip['sourceStart']:.6f}:"
                f"duration={clip['duration']:.6f},asetpts=PTS-STARTPTS,"
                f"volume={clip.get('volume', 1.0):.4f},adelay={delay}|{delay}[{label}]"
            )
            audio_labels.append(f"[{label}]")
            audio_number += 1
        for clip, _asset, index in audio_inputs:
            label = f"a{audio_number}"
            delay = max(0, int(round(_float(clip.get("timelineStart"), 0.0) * 1000)))
            filters.append(
                f"[{index}:a]atrim=start={clip['sourceStart']:.6f}:"
                f"duration={clip['duration']:.6f},asetpts=PTS-STARTPTS,"
                f"volume={clip.get('volume', 1.0):.4f},adelay={delay}|{delay}[{label}]"
            )
            audio_labels.append(f"[{label}]")
            audio_number += 1
        if audio_labels:
            filters.append(
                "".join(audio_labels)
                + f"amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0,"
                "aresample=48000,alimiter=limit=0.95[aout]"
            )

        cmd.extend(["-filter_complex", ";".join(filters), "-map", f"[{current_video}]"])
        if audio_labels:
            cmd.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.append("-an")
        if encoder == "nvenc":
            cmd.extend(["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18"])
        else:
            preset = "veryfast" if profile == "preview" else "medium"
            crf = "23" if profile == "preview" else "18"
            cmd.extend(["-c:v", "libx264", "-preset", preset, "-crf", crf])
        cmd.extend(
            [
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-t",
                f"{total:.6f}",
                "-progress",
                "pipe:1",
                "-nostats",
                "-f",
                "mp4",
                str(output),
            ]
        )
        return cmd, total

    def start_render(self, project_id: str, spec: RenderCreate) -> Dict[str, Any]:
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, spec.expectedRevision)
            free = shutil.disk_usage(self.root).free
            if free < 512 * 1024 * 1024:
                raise EditorSuiteError(
                    "LOW_DISK_SPACE",
                    "Ha menos de 512 MB livres; libere espaco antes de exportar.",
                    507,
                )
            if spec.encoder == "nvenc" and not self._ffmpeg_has_encoder("h264_nvenc"):
                raise EditorSuiteError("NVENC_UNAVAILABLE", "NVENC nao esta disponivel.", 422)
            job = self._create_job(project_id, "render", "Exportacao na fila.")
            job = self._update_job(
                job["jobId"],
                sourceRevision=int(project["revision"]),
            )
            project_snapshot = _clone(project)
        thread = threading.Thread(
            target=self._render_worker,
            args=(job["jobId"], project_id, spec.model_dump(), project_snapshot),
            name=f"maestro-editor-render-{job['jobId'][:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def _render_worker(
        self,
        job_id: str,
        project_id: str,
        spec: Dict[str, Any],
        project_snapshot: Dict[str, Any],
    ) -> None:
        process: Optional[subprocess.Popen[str]] = None
        work_dir = self._project_dir(project_id) / "work" / job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._update_job(job_id, status="running", progress=2, message="Preparando timeline.")
            project = _clone(project_snapshot)
            export_id = uuid.uuid4().hex
            export_dir = self._project_dir(project_id) / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            final_path = export_dir / f"{export_id}.mp4"
            partial_path = export_dir / f".{export_id}.partial.mp4"
            command, duration = self._render_command(
                project,
                partial_path,
                profile=str(spec.get("profile") or "quality"),
                encoder=str(spec.get("encoder") or "cpu"),
                work_dir=work_dir,
            )
            self._update_job(job_id, progress=5, message="Renderizando no FFmpeg.")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            with self.process_lock:
                self.processes[job_id] = process
            last_progress = 5
            output_tail: List[str] = []
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.strip()
                if line:
                    output_tail.append(line)
                    output_tail = output_tail[-120:]
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key not in {"out_time_us", "out_time_ms"}:
                    continue
                seconds = _float(value, 0.0) / 1_000_000.0
                progress = max(5, min(97, int((seconds / max(duration, 0.001)) * 92) + 5))
                if progress > last_progress:
                    last_progress = progress
                    self._update_job(
                        job_id,
                        progress=progress,
                        message=f"Renderizando {progress}%.",
                    )
                current = self.get_job(job_id)
                if current.get("status") == "canceling" and process.poll() is None:
                    process.terminate()
            return_code = process.wait()
            current = self.get_job(job_id)
            if current.get("status") == "canceling":
                partial_path.unlink(missing_ok=True)
                self._update_job(
                    job_id,
                    status="canceled",
                    progress=100,
                    message="Exportacao cancelada; projeto preservado.",
                )
                return
            if return_code != 0 or not partial_path.is_file() or partial_path.stat().st_size == 0:
                raise EditorSuiteError(
                    "RENDER_FAILED",
                    "O FFmpeg nao conseguiu exportar a timeline.",
                    500,
                    "\n".join(output_tail)[-4000:],
                )
            os.replace(partial_path, final_path)
            self._update_job(job_id, progress=95, message="Preservando o video sem DLSS.")
            dlss5 = _dlss5.preserve_video_policy(final_path)
            digest = _sha256_file(final_path)
            probe = self._probe(final_path)
            export = {
                "exportId": export_id,
                "filename": f"{_safe_leaf(project['name'], 'projeto')}.mp4",
                "relativePath": final_path.relative_to(self._project_dir(project_id)).as_posix(),
                "size": final_path.stat().st_size,
                "sha256": digest,
                "duration": probe["duration"],
                "createdAt": _now_iso(),
                "profile": spec.get("profile"),
                "encoder": spec.get("encoder"),
                "dlss5": dlss5,
            }
            with self.lock:
                latest = self._load_project(project_id)
                latest.setdefault("exports", []).insert(0, export)
                saved = self._save_project(latest)
            decorated = self._decorate_project(saved)
            result_export = next(
                item for item in decorated["exports"] if item["exportId"] == export_id
            )
            self._update_job(
                job_id,
                status="completed",
                progress=100,
                message="Video pronto para assistir ou baixar.",
                result={"export": result_export},
            )
        except EditorSuiteError as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                message=str(exc),
                error={"code": exc.code, "message": str(exc), "details": exc.details},
            )
        except Exception as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                message="Falha inesperada na exportacao.",
                error={"code": "RENDER_FAILED", "message": str(exc)},
            )
        finally:
            with self.process_lock:
                self.processes.pop(job_id, None)
            if process and process.stdout:
                process.stdout.close()
            shutil.rmtree(work_dir, ignore_errors=True)

    def export_path(self, project_id: str, export_id: str) -> tuple[Path, Dict[str, Any]]:
        export_id = _safe_id(export_id, "Exportacao")
        with self.lock:
            project = self._load_project(project_id)
            export = next(
                (item for item in project.get("exports", []) if item.get("exportId") == export_id),
                None,
            )
            if not export:
                raise EditorSuiteError("EXPORT_NOT_FOUND", "Exportacao nao encontrada.", 404)
            project_dir = self._project_dir(project_id)
            path = (project_dir / export["relativePath"]).resolve(strict=True)
            if project_dir not in path.parents or not path.is_file():
                raise EditorSuiteError("EXPORT_NOT_FOUND", "Arquivo exportado nao encontrado.", 404)
            return path, _clone(export)

    def capcut_local_handoff_path(
        self,
        project_id: str,
        mode: str,
    ) -> tuple[Path, Dict[str, Any]]:
        """Materializa um pacote deterministico para o editor CapCut Local/LLM."""

        normalized_mode = str(mode or "quick").strip().lower()
        if normalized_mode not in {"quick", "editable"}:
            raise EditorSuiteError(
                "INVALID_HANDOFF_MODE",
                "Use o modo quick ou editable.",
                422,
            )
        with self.lock:
            project = _clone(self._load_project(project_id))
            project_dir = self._project_dir(project_id)
            handoff_dir = (project_dir / "handoffs").resolve()
            if handoff_dir.parent != project_dir:
                raise EditorSuiteError(
                    "INVALID_HANDOFF_PATH",
                    "Destino do pacote local invalido.",
                    500,
                )
            handoff_dir.mkdir(parents=True, exist_ok=True)
            revision = max(1, int(project.get("revision") or 1))
            filename = (
                f"capcut-local-{project_id[:12]}-r{revision}-{normalized_mode}.zip"
            )
            target = handoff_dir / filename
            if target.is_file():
                return target, {
                    "mode": normalized_mode,
                    "filename": filename,
                    "cached": True,
                    "revision": revision,
                    "size": target.stat().st_size,
                    "sha256": _sha256_file(target),
                }
            try:
                result = create_capcut_local_handoff(
                    project,
                    project_dir,
                    target,
                    mode=normalized_mode,
                )
            except CapCutHandoffError as exc:
                status = 413 if exc.code in {
                    "FILE_TOO_LARGE",
                    "PACKAGE_TOO_LARGE",
                    "TOO_MANY_FILES",
                } else 422
                raise EditorSuiteError(
                    f"CAPCUT_HANDOFF_{exc.code}",
                    str(exc),
                    status,
                    exc.details,
                ) from exc
            return result.path, {
                "mode": result.mode,
                "filename": filename,
                "cached": False,
                "revision": revision,
                "size": result.package_size,
                "sha256": result.package_sha256,
                "fileCount": result.file_count,
                "sourceBytes": result.source_bytes,
            }

    def _ffmpeg_has_encoder(self, name: str) -> bool:
        try:
            proc = subprocess.run(
                [self.ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return proc.returncode == 0 and name in proc.stdout
        except (OSError, subprocess.SubprocessError):
            return False

    def _ffmpeg_has_filter(self, name: str) -> bool:
        try:
            proc = subprocess.run(
                [self.ffmpeg, "-hide_banner", "-filters"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return proc.returncode == 0 and re.search(rf"\b{re.escape(name)}\b", proc.stdout) is not None
        except (OSError, subprocess.SubprocessError):
            return False

    # ---------- voz ----------

    def _elevenlabs_provider(self) -> ElevenLabsVoiceProvider:
        return ElevenLabsVoiceProvider(
            base_url=os.environ.get(
                "ELEVENLABS_API_BASE_URL",
                "https://api.elevenlabs.io",
            ).strip()
            or "https://api.elevenlabs.io",
            enable_logging=_env_bool("ELEVENLABS_ENABLE_LOGGING", True),
            timeout_seconds=_float(
                os.environ.get("ELEVENLABS_TIMEOUT_SECONDS"),
                60.0,
            ),
            max_retries=max(
                0,
                min(
                    5,
                    int(
                        _float(
                            os.environ.get("ELEVENLABS_MAX_RETRIES"),
                            2.0,
                        )
                    ),
                ),
            ),
        )

    def _elevenlabs_capabilities(self, *, refresh: bool = False) -> Dict[str, Any]:
        now = time.monotonic()
        with self.voice_provider_lock:
            cached = self._elevenlabs_capability_cache
            if (
                not refresh
                and isinstance(cached.get("value"), dict)
                and _float(cached.get("expiresAt"), 0.0) > now
            ):
                return _clone(cached["value"])

        feature_enabled = _env_bool("MAESTRO_VOICE_CLOUD_ENABLED", False)
        key_configured = bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())
        default_voice_id = os.environ.get("ELEVENLABS_DEFAULT_VOICE_ID", "").strip()
        result: Dict[str, Any] = {
            "provider": "elevenlabs",
            "configured": key_configured,
            "enabled": False,
            "featureEnabled": feature_enabled,
            "status": "disabled" if not feature_enabled else "missing_key",
            "defaultVoiceId": default_voice_id,
            "defaultModelId": os.environ.get(
                "ELEVENLABS_TTS_MODEL_ID",
                "eleven_v3",
            ).strip()
            or "eleven_v3",
            "voices": [],
            "models": [
                {"modelId": "eleven_v3", "name": "Eleven v3 expressivo"},
                {
                    "modelId": "eleven_multilingual_v2",
                    "name": "Multilingual v2 estavel",
                },
                {"modelId": "eleven_flash_v2_5", "name": "Flash v2.5 preview"},
            ],
            "presets": [
                "expressive_v3",
                "stable_longform",
                "preview",
            ],
        }
        ttl = 300.0
        if feature_enabled and key_configured:
            try:
                provider = self._elevenlabs_provider()
                contract = provider.capabilities(include_remote=False)
                result["defaultModelId"] = contract["defaultModelId"]
                result["providerPresets"] = contract["presets"]
                voice_page = provider.list_voices(page_size=100)
                result["voices"] = voice_page["items"]
                remote_models = provider.list_models()["items"]
                tts_models = [
                    item
                    for item in remote_models
                    if item.get("canDoTextToSpeech") is not False
                ]
                if tts_models:
                    result["models"] = tts_models
                result["enabled"] = bool(default_voice_id or result["voices"])
                result["status"] = "ready" if result["enabled"] else "voice_required"
            except VoiceProviderError as exc:
                result["enabled"] = bool(default_voice_id)
                result["status"] = (
                    "degraded_default_voice"
                    if result["enabled"]
                    else "provider_unavailable"
                )
                result["error"] = {
                    "code": exc.code,
                    "retryable": exc.retryable,
                }
                ttl = 45.0
        with self.voice_provider_lock:
            self._elevenlabs_capability_cache = {
                "expiresAt": now + ttl,
                "value": _clone(result),
            }
        return result

    def _voice_profile_path(self, profile_id: str) -> Path:
        return self.voices_root / _safe_id(profile_id, "Voz") / "profile.json"

    def list_voice_profiles(self) -> List[Dict[str, Any]]:
        items = []
        with self.lock:
            for path in self.voices_root.glob("*/profile.json"):
                try:
                    profile = _read_json(path)
                except EditorSuiteError:
                    continue
                profile.pop("referenceRelativePath", None)
                items.append(profile)
        items.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
        return items

    def create_voice_profile(
        self,
        name: str,
        consent: bool,
        upload: UploadFile,
    ) -> Dict[str, Any]:
        if not consent:
            try:
                upload.file.close()
            except Exception:
                pass
            raise EditorSuiteError(
                "VOICE_CONSENT_REQUIRED",
                "Confirme que voce tem autorizacao para usar esta voz.",
                422,
            )
        safe_name = _safe_project_name(name)
        suffix = Path(_safe_leaf(upload.filename or "")).suffix.lower()
        if suffix not in AUDIO_SUFFIXES and suffix not in VIDEO_SUFFIXES:
            try:
                upload.file.close()
            except Exception:
                pass
            raise EditorSuiteError("INVALID_VOICE_SAMPLE", "Envie audio ou video com uma voz limpa.", 415)
        profile_id = uuid.uuid4().hex
        profile_dir = self.voices_root / profile_id
        profile_dir.mkdir(parents=True, exist_ok=False)
        raw = profile_dir / f"source{suffix}"
        normalized = profile_dir / "reference.wav"
        try:
            _bounded_copy(upload, raw, min(self.max_upload_bytes, 256 * 1024 * 1024))
            source_probe = self._probe(raw)
            if not source_probe["hasAudio"] or source_probe["duration"] < 3:
                raise EditorSuiteError(
                    "INVALID_VOICE_SAMPLE",
                    "A amostra precisa ter pelo menos 3 segundos de voz.",
                )
            cmd = [
                self.ffmpeg,
                "-hide_banner",
                "-y",
                "-i",
                str(raw),
                "-vn",
                "-t",
                "30",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-af",
                "loudnorm=I=-18:TP=-2:LRA=11",
                "-f",
                "wav",
                str(normalized),
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if proc.returncode != 0 or not normalized.is_file():
                raise EditorSuiteError(
                    "VOICE_NORMALIZE_FAILED",
                    "Nao foi possivel preparar a amostra de voz.",
                    422,
                    proc.stderr[-2000:],
                )
            raw.unlink(missing_ok=True)
            probe = self._probe(normalized)
            profile = {
                "voiceProfileId": profile_id,
                "name": safe_name,
                "consentConfirmed": True,
                "duration": probe["duration"],
                "sha256": _sha256_file(normalized),
                "createdAt": _now_iso(),
                "referenceRelativePath": "reference.wav",
            }
            _atomic_json(profile_dir / "profile.json", profile)
            public = _clone(profile)
            public.pop("referenceRelativePath", None)
            return public
        except Exception:
            shutil.rmtree(profile_dir, ignore_errors=True)
            raise

    def _chatterbox_python(self) -> str:
        candidates = []
        configured = os.environ.get("MAESTRO_CHATTERBOX_PYTHON", "").strip()
        if configured:
            candidates.append(Path(configured))
        base = Path(__file__).resolve().parents[2] / "ferramentas" / "chatterbox"
        candidates.extend(
            [
                base / ".venv" / "Scripts" / "python.exe",
                base / ".venv" / "bin" / "python",
            ]
        )
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                proc = subprocess.run(
                    [
                        str(candidate),
                        "-c",
                        "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('chatterbox') else 1)",
                    ],
                    capture_output=True,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                if proc.returncode == 0:
                    return str(candidate)
            except (OSError, subprocess.SubprocessError):
                continue
        return ""

    def _system_voices(self) -> List[str]:
        if os.name != "nt" or not shutil.which("powershell"):
            return []
        script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
@($s.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo.Name }) |
    ConvertTo-Json -Compress
"""
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle",
                    "Hidden",
                    "-EncodedCommand",
                    _powershell_encoded(script),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if proc.returncode != 0:
                return []
            payload = json.loads(proc.stdout.strip() or "[]")
            if isinstance(payload, str):
                payload = [payload]
            return [str(item) for item in payload if str(item).strip()]
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return []

    def _comfy_voice_request(
        self,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        timeout: float = 3.0,
    ) -> Dict[str, Any]:
        base_url = os.environ.get("PEMARA_COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
        data = None
        headers: Dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{base_url}{path}",
            data=data,
            headers=headers,
            method="POST" if data is not None else "GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _free_vram_gb(self) -> Optional[float]:
        executable = shutil.which("nvidia-smi")
        if not executable:
            return None
        try:
            proc = subprocess.run(
                [
                    executable,
                    "--query-gpu=memory.free",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if proc.returncode != 0:
                return None
            first = next(
                (line.strip() for line in proc.stdout.splitlines() if line.strip()),
                "",
            )
            return round(float(first) / 1024.0, 2) if first else None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    def _chatterbox_gpu_status(self, *, release_idle: bool = False) -> Dict[str, Any]:
        device = os.environ.get("MAESTRO_CHATTERBOX_DEVICE", "cuda").strip().lower() or "cuda"
        minimum_free = max(
            0.0,
            _float(
                os.environ.get("MAESTRO_CHATTERBOX_MIN_FREE_VRAM_GB"),
                CHATTERBOX_MIN_FREE_VRAM_GB,
            ),
        )
        with self.voice_gpu_lock:
            voice_busy = bool(self._voice_gpu_job_id)

        queue_reachable = False
        running = 0
        pending = 0
        released_idle_models = False
        if device == "cuda":
            try:
                queue = self._comfy_voice_request("/queue")
                queue_reachable = True
                running = len(list(queue.get("queue_running") or []))
                pending = len(list(queue.get("queue_pending") or []))
                if release_idle and not voice_busy and not running and not pending:
                    try:
                        self._comfy_voice_request(
                            "/free",
                            {"unload_models": True, "free_memory": True},
                            timeout=10.0,
                        )
                        released_idle_models = True
                    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
                        released_idle_models = False
            except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
                queue_reachable = False

        free_vram = self._free_vram_gb() if device == "cuda" else None
        reason = "ready"
        if voice_busy:
            reason = "voice_busy"
        elif running or pending:
            reason = "comfy_busy"
        elif free_vram is not None and free_vram < minimum_free:
            reason = "low_vram"
        ready = reason == "ready"
        messages = {
            "ready": "GPU pronta para a voz neural local.",
            "voice_busy": "Outra voz neural local ja esta sendo gerada.",
            "comfy_busy": "A RTX 5090 esta ocupada pela fila de imagem ou video.",
            "low_vram": "A RTX 5090 nao possui VRAM livre suficiente para iniciar a voz neural.",
        }
        return {
            "ready": ready,
            "reason": reason,
            "message": messages[reason],
            "device": device,
            "freeVramGb": free_vram,
            "minimumFreeVramGb": minimum_free if device == "cuda" else None,
            "comfy": {
                "reachable": queue_reachable,
                "running": running,
                "pending": pending,
                "releasedIdleModels": released_idle_models,
            },
        }

    @staticmethod
    def _voice_preview_text(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= VOICE_PREVIEW_MAX_CHARS:
            return normalized
        window = normalized[: VOICE_PREVIEW_MAX_CHARS + 1]
        sentence_end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
        if sentence_end >= VOICE_PREVIEW_MAX_CHARS // 2:
            return window[: sentence_end + 1].strip()
        word_end = window.rfind(" ")
        if word_end >= VOICE_PREVIEW_MAX_CHARS // 2:
            return window[:word_end].strip()
        return normalized[:VOICE_PREVIEW_MAX_CHARS].strip()

    @staticmethod
    def _voice_gpu_error(status: Dict[str, Any]) -> EditorSuiteError:
        reason = str(status.get("reason") or "voice_busy")
        code = "VOICE_GPU_MEMORY" if reason == "low_vram" else "VOICE_GPU_BUSY"
        http_status = 503 if reason == "low_vram" else 409
        return EditorSuiteError(
            code,
            str(status.get("message") or "A voz neural local esta temporariamente indisponivel."),
            http_status,
            {
                "reason": reason,
                "freeVramGb": status.get("freeVramGb"),
                "minimumFreeVramGb": status.get("minimumFreeVramGb"),
                "comfy": status.get("comfy"),
                "recovery": "Aguarde a fila da GPU ou escolha Voz do Windows.",
            },
        )

    def _voice_reference(self, profile_id: str) -> Path:
        profile = _read_json(self._voice_profile_path(profile_id))
        root = self._voice_profile_path(profile_id).parent.resolve()
        path = (root / str(profile.get("referenceRelativePath") or "")).resolve(strict=True)
        if root not in path.parents or not path.is_file():
            raise EditorSuiteError("VOICE_PROFILE_NOT_FOUND", "Perfil de voz incompleto.", 404)
        return path

    def start_voice(self, project_id: str, spec: VoiceCreate) -> Dict[str, Any]:
        source_text = str(spec.text).strip()
        if not source_text:
            raise EditorSuiteError("VOICE_TEXT_REQUIRED", "Digite o texto da narracao.", 422)
        payload = spec.model_dump()
        payload["text"] = (
            self._voice_preview_text(source_text) if spec.mode == "preview" else source_text
        )
        payload["addToTimeline"] = bool(spec.addToTimeline and spec.mode == "final")
        payload["sourceTextSha256"] = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        payload["sourceTextCharacters"] = len(source_text)
        payload["synthesizedTextCharacters"] = len(str(payload["text"]))
        payload["previewLimitCharacters"] = (
            VOICE_PREVIEW_MAX_CHARS if spec.mode == "preview" else None
        )
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, spec.expectedRevision)
            requested_engine = spec.engine
            engine = "chatterbox" if spec.voiceProfileId and spec.engine == "auto" else spec.engine
            chatterbox = (
                self._chatterbox_python()
                if engine in {"auto", "chatterbox"} or spec.voiceProfileId
                else ""
            )
            system_voices = (
                self._system_voices() if engine in {"auto", "system"} else []
            )
            if engine == "chatterbox" and not chatterbox:
                raise EditorSuiteError(
                    "CHATTERBOX_NOT_INSTALLED",
                    "A voz neural local ainda nao esta instalada; use Voz do Windows por enquanto.",
                    503,
                )
            if spec.voiceProfileId:
                self._voice_reference(spec.voiceProfileId)
            gpu_status: Optional[Dict[str, Any]] = None
            resolution = "requested"
            if engine in {"auto", "chatterbox"} and chatterbox:
                with self.voice_gpu_lock:
                    gpu_status = self._chatterbox_gpu_status(release_idle=True)
                    if engine == "auto":
                        if gpu_status["ready"]:
                            engine = "chatterbox"
                            resolution = "auto_neural"
                        elif system_voices:
                            engine = "system"
                            resolution = "auto_system_gpu_fallback"
                        else:
                            raise self._voice_gpu_error(gpu_status)
                    elif not gpu_status["ready"]:
                        raise self._voice_gpu_error(gpu_status)
            elif engine == "auto":
                engine = "system"
                resolution = "auto_system_no_neural"
            if engine == "system" and not system_voices:
                raise EditorSuiteError(
                    "SYSTEM_TTS_UNAVAILABLE",
                    "Nenhuma voz local do Windows foi encontrada.",
                    503,
                )
            if engine == "elevenlabs_cloud":
                cloud = self._elevenlabs_capabilities()
                if not cloud.get("featureEnabled"):
                    raise EditorSuiteError(
                        "VOICE_CLOUD_DISABLED",
                        "A geracao de voz em nuvem esta desativada no Maestro.",
                        503,
                    )
                if not cloud.get("configured"):
                    raise EditorSuiteError(
                        "ELEVENLABS_NOT_CONFIGURED",
                        "O provedor de voz em nuvem ainda nao possui credencial no servidor.",
                        503,
                    )
                selected_voice = (
                    str(spec.providerVoiceId or "").strip()
                    or str(cloud.get("defaultVoiceId") or "").strip()
                )
                if not selected_voice:
                    raise EditorSuiteError(
                        "ELEVENLABS_VOICE_REQUIRED",
                        "Selecione uma voz do provedor antes de gerar.",
                        422,
                    )
            if spec.voiceProfileId and engine != "chatterbox":
                raise EditorSuiteError(
                    "VOICE_CLONE_REQUIRES_CHATTERBOX",
                    "Clonagem de voz exige o motor neural Chatterbox.",
                    422,
                )
            job = self._create_job(
                project_id,
                "voice",
                "Previa de voz na fila." if spec.mode == "preview" else "Narracao na fila.",
            )
            job = self._update_job(
                job["jobId"],
                engine=engine,
                requestedEngine=requested_engine,
                engineResolution=resolution,
                mode=spec.mode,
            )
            if engine == "chatterbox":
                with self.voice_gpu_lock:
                    self._voice_gpu_job_id = job["jobId"]
        payload["engine"] = engine
        payload["engineResolution"] = resolution
        if gpu_status is not None:
            payload["gpuAdmission"] = gpu_status
        thread = threading.Thread(
            target=self._voice_worker,
            args=(job["jobId"], project_id, payload),
            name=f"maestro-editor-voice-{job['jobId'][:8]}",
            daemon=True,
        )
        try:
            thread.start()
        except Exception:
            if engine == "chatterbox":
                with self.voice_gpu_lock:
                    if self._voice_gpu_job_id == job["jobId"]:
                        self._voice_gpu_job_id = ""
            raise
        return job

    def _voice_worker(self, job_id: str, project_id: str, spec: Dict[str, Any]) -> None:
        work_dir = self.runtime_root / job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            text_path = work_dir / "text.txt"
            text_path.write_text(str(spec["text"]), encoding="utf-8")
            raw_output = work_dir / "voice_raw.audio"
            final_output = work_dir / "voice.wav"
            engine = str(spec["engine"])
            mode = "preview" if spec.get("mode") == "preview" else "final"
            spec["voiceProvenance"] = {
                "provider": {
                    "chatterbox": "chatterbox",
                    "system": "windows_sapi",
                    "elevenlabs_cloud": "elevenlabs",
                }.get(engine, engine),
                "engine": engine,
                "engineResolution": spec.get("engineResolution"),
                "mode": mode,
                "local": engine != "elevenlabs_cloud",
                "language": spec.get("language") or "pt",
                "preset": spec.get("preset") or "natural",
                "intensity": _float(spec.get("intensity"), 0.5),
                "speed": _float(spec.get("speed"), 1.0),
                "sourceTextSha256": spec.get("sourceTextSha256"),
                "sourceTextCharacters": spec.get("sourceTextCharacters"),
                "synthesizedTextCharacters": spec.get("synthesizedTextCharacters"),
                "previewLimitCharacters": spec.get("previewLimitCharacters"),
            }
            if spec.get("voiceProfileId"):
                spec["voiceProvenance"]["voiceProfileId"] = spec["voiceProfileId"]
            self._update_job(
                job_id,
                status="running",
                progress=8,
                message=(
                    "Preparando síntese ElevenLabs."
                    if engine == "elevenlabs_cloud"
                    else "Preparando voz local."
                ),
            )
            if engine == "chatterbox":
                python = self._chatterbox_python()
                if not python:
                    raise EditorSuiteError(
                        "CHATTERBOX_NOT_INSTALLED",
                        "O motor Chatterbox nao esta disponivel.",
                        503,
                    )
                worker = Path(__file__).with_name("chatterbox_cli.py")
                cmd = [
                    python,
                    str(worker),
                    "--text-file",
                    str(text_path),
                    "--output",
                    str(raw_output),
                    "--language",
                    str(spec.get("language") or "pt"),
                    "--device",
                    os.environ.get("MAESTRO_CHATTERBOX_DEVICE", "cuda"),
                ]
                controls = _local_voice_controls(spec)
                cmd.extend(
                    [
                        "--exaggeration",
                        str(controls["exaggeration"]),
                        "--cfg-weight",
                        str(controls["cfg_weight"]),
                        "--temperature",
                        str(controls["temperature"]),
                        "--repetition-penalty",
                        str(controls["repetition_penalty"]),
                        "--min-p",
                        str(controls["min_p"]),
                        "--top-p",
                        str(controls["top_p"]),
                    ]
                )
                if spec.get("voiceProfileId"):
                    cmd.extend(["--reference", str(self._voice_reference(spec["voiceProfileId"]))])
                self._update_job(job_id, progress=20, message="Sintetizando com Chatterbox local.")
                env = os.environ.copy()
                default_neural_cache = (
                    Path(__file__).resolve().parents[2]
                    / "ferramentas"
                    / "chatterbox"
                    / "model-cache"
                )
                neural_cache_root = Path(
                    env.get("MAESTRO_NEURAL_CACHE", str(default_neural_cache))
                )
                env["HF_HOME"] = str(neural_cache_root / "huggingface")
                env["HF_HUB_CACHE"] = str(neural_cache_root / "huggingface" / "hub")
                env["HUGGINGFACE_HUB_CACHE"] = str(
                    neural_cache_root / "huggingface" / "hub"
                )
                env["TORCH_HOME"] = str(neural_cache_root / "torch")
                proc = subprocess.Popen(
                    cmd,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                with self.process_lock:
                    self.processes[job_id] = proc
                stdout, stderr = proc.communicate()
                current = self.get_job(job_id)
                if current.get("status") == "canceling":
                    self._update_job(
                        job_id,
                        status="canceled",
                        progress=100,
                        message="Narracao cancelada.",
                    )
                    return
                if proc.returncode != 0 or not raw_output.is_file():
                    raise EditorSuiteError(
                        "VOICE_GENERATION_FAILED",
                        "O Chatterbox nao conseguiu gerar a narracao.",
                        500,
                        (stderr or stdout)[-4000:],
                    )
            elif engine == "elevenlabs_cloud":
                provider = self._elevenlabs_provider()
                request = _elevenlabs_request(spec)
                selected_voice = str(spec.get("providerVoiceId") or "").strip()
                if not selected_voice:
                    cloud = self._elevenlabs_capabilities()
                    selected_voice = str(cloud.get("defaultVoiceId") or "").strip()
                if not selected_voice:
                    raise EditorSuiteError(
                        "ELEVENLABS_VOICE_REQUIRED",
                        "Selecione uma voz do ElevenLabs antes de gerar.",
                        422,
                    )
                self._update_job(
                    job_id,
                    progress=20,
                    message="Sintetizando com ElevenLabs cloud.",
                )
                try:
                    result = provider.synthesize(
                        text=str(spec["text"]),
                        voice_id=selected_voice,
                        preset=request["preset"],
                        model_id=request["model_id"],
                        language_code=request["language_code"],
                        direction=request["direction"],
                        audio_tags=request["audio_tags"],
                        voice_settings=request["voice_settings"],
                    )
                except VoiceProviderError as exc:
                    status = exc.status or (503 if exc.retryable else 502)
                    raise EditorSuiteError(
                        f"ELEVENLABS_{exc.code}",
                        "O ElevenLabs não conseguiu gerar a narração.",
                        status,
                        {
                            "providerCode": exc.code,
                            "retryable": exc.retryable,
                        },
                    ) from exc
                raw_output.write_bytes(result.audio_bytes)
                cloud_metadata = dict(result.metadata)
                spec["voiceProvenance"].update({
                    "provider": "elevenlabs",
                    "voiceId": cloud_metadata.get("voiceId") or selected_voice,
                    "modelId": cloud_metadata.get("modelId") or request["model_id"],
                    "preset": cloud_metadata.get("preset") or request["preset"],
                    "outputFormat": cloud_metadata.get("outputFormat"),
                    "languageCode": cloud_metadata.get("languageCode")
                    or request["language_code"],
                    "performance": cloud_metadata.get("performance") or {
                        "direction": request["direction"],
                        "audioTags": request["audio_tags"],
                    },
                    "requestId": cloud_metadata.get("requestId"),
                    "cacheKey": cloud_metadata.get("cacheKey"),
                    "providerSpeed": request["provider_speed"],
                })
            else:
                voices = self._system_voices()
                requested = str(spec.get("systemVoice") or "")
                selected = requested if requested in voices else (voices[0] if voices else "")
                if not selected:
                    raise EditorSuiteError(
                        "SYSTEM_TTS_UNAVAILABLE",
                        "Nenhuma voz local do Windows foi encontrada.",
                        503,
                    )
                speed = _float(spec.get("speed"), 1.0)
                rate = max(-10, min(10, int(round((speed - 1.0) * 10))))
                script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($env:PEMARA_TTS_VOICE)
$s.Rate = [int]$env:PEMARA_TTS_RATE
$s.Volume = 100
$s.SetOutputToWaveFile($env:PEMARA_TTS_OUTPUT)
$text = [IO.File]::ReadAllText($env:PEMARA_TTS_TEXT, [Text.Encoding]::UTF8)
$s.Speak($text)
$s.Dispose()
"""
                env = os.environ.copy()
                env.update(
                    {
                        "PEMARA_TTS_VOICE": selected,
                        "PEMARA_TTS_RATE": str(rate),
                        "PEMARA_TTS_OUTPUT": str(raw_output),
                        "PEMARA_TTS_TEXT": str(text_path),
                    }
                )
                self._update_job(job_id, progress=25, message="Sintetizando com voz do Windows.")
                proc = subprocess.Popen(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-WindowStyle",
                        "Hidden",
                        "-EncodedCommand",
                        _powershell_encoded(script),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                with self.process_lock:
                    self.processes[job_id] = proc
                try:
                    stdout, stderr = proc.communicate(timeout=300)
                except subprocess.TimeoutExpired as exc:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    raise EditorSuiteError(
                        "VOICE_GENERATION_TIMEOUT",
                        "A voz local do Windows excedeu o tempo limite.",
                        504,
                        (stderr or stdout)[-3000:],
                    ) from exc
                current = self.get_job(job_id)
                if current.get("status") == "canceling":
                    self._update_job(
                        job_id,
                        status="canceled",
                        progress=100,
                        message="Narracao cancelada.",
                    )
                    return
                if proc.returncode != 0 or not raw_output.is_file():
                    raise EditorSuiteError(
                        "VOICE_GENERATION_FAILED",
                        "A voz local do Windows falhou.",
                        500,
                        (stderr or stdout)[-3000:],
                    )
            self._update_job(job_id, progress=75, message="Finalizando narracao.")
            requested_speed = _float(spec.get("speed"), 1.0)
            post_speed = 1.0
            if engine == "chatterbox":
                post_speed = requested_speed
            elif engine == "elevenlabs_cloud":
                provider_speed = _float(
                    spec.get("voiceProvenance", {}).get("providerSpeed"),
                    1.0,
                )
                post_speed = requested_speed / provider_speed
            ffmpeg_args = [
                self.ffmpeg,
                "-hide_banner",
                "-y",
                "-i",
                str(raw_output),
            ]
            if abs(post_speed - 1.0) > 0.01:
                ffmpeg_args.extend(["-filter:a", f"atempo={post_speed:.4f}"])
            ffmpeg_args.extend(
                [
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-c:a",
                    "pcm_s16le",
                    "-f",
                    "wav",
                    str(final_output),
                ]
            )
            proc = subprocess.run(
                ffmpeg_args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if proc.returncode != 0:
                raise EditorSuiteError(
                    "VOICE_POSTPROCESS_FAILED",
                    "A voz foi gerada, mas a normalização de áudio falhou.",
                    500,
                    proc.stderr[-3000:],
                )
            if self.get_job(job_id).get("status") == "canceling":
                self._update_job(
                    job_id,
                    status="canceled",
                    progress=100,
                    message="Narracao cancelada.",
                )
                return
            probe = self._probe(final_output)
            with self.lock:
                project = self._load_project(project_id)
                project_dir = self._project_dir(project_id)
                asset_id = uuid.uuid4().hex
                target = project_dir / "media" / f"{asset_id}_narracao.wav"
                shutil.copy2(final_output, target)
                asset = {
                    "assetId": asset_id,
                    "name": "Previa de voz IA.wav" if mode == "preview" else "Narracao IA.wav",
                    "kind": "audio",
                    "relativePath": target.relative_to(project_dir).as_posix(),
                    "mediaType": "audio/wav",
                    "size": target.stat().st_size,
                    "duration": probe["duration"],
                    "width": 0,
                    "height": 0,
                    "hasAudio": True,
                    "createdAt": _now_iso(),
                    "source": f"tts:{engine}",
                }
                if spec.get("voiceProvenance"):
                    asset["provenance"] = _clone(spec["voiceProvenance"])
                project.setdefault("assets", []).append(asset)
                if spec.get("addToTimeline"):
                    clip = self._normalize_clip(
                        project,
                        {
                            "clipId": uuid.uuid4().hex,
                            "assetId": asset_id,
                            "track": "voice",
                            "timelineStart": _float(spec.get("timelineStart"), 0.0),
                            "sourceStart": 0.0,
                            "sourceEnd": probe["duration"],
                            "duration": probe["duration"],
                            "volume": 1.0,
                            "muted": False,
                            "order": len(
                                [c for c in project.get("clips", []) if c.get("track") == "voice"]
                            ),
                            "label": "Narracao IA",
                            "createdAt": _now_iso(),
                        },
                    )
                    project.setdefault("clips", []).append(clip)
                saved = self._save_project(project)
            decorated = self._decorate_project(saved)
            output_asset = next(a for a in decorated["assets"] if a["assetId"] == asset_id)
            self._update_job(
                job_id,
                status="completed",
                progress=100,
                message=(
                    "Previa de voz pronta na biblioteca; a timeline nao foi alterada."
                    if mode == "preview"
                    else (
                        "Narracao pronta e adicionada ao projeto."
                        if spec.get("addToTimeline")
                        else "Narracao pronta na biblioteca."
                    )
                ),
                result={"asset": output_asset, "project": decorated},
            )
        except EditorSuiteError as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                message=str(exc),
                error={"code": exc.code, "message": str(exc), "details": exc.details},
            )
        except Exception as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                message="Falha inesperada ao gerar voz.",
                error={"code": "VOICE_GENERATION_FAILED", "message": str(exc)},
            )
        finally:
            with self.process_lock:
                self.processes.pop(job_id, None)
            if str(spec.get("engine") or "") == "chatterbox":
                with self.voice_gpu_lock:
                    if self._voice_gpu_job_id == job_id:
                        self._voice_gpu_job_id = ""
            shutil.rmtree(work_dir, ignore_errors=True)

    # ---------- copiloto ----------

    def _ollama_models(self) -> List[str]:
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return [
                str(item.get("name") or item.get("model") or "")
                for item in payload.get("models", [])
                if str(item.get("name") or item.get("model") or "").strip()
            ]
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return []

    @staticmethod
    def _assistant_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "summary": {"type": "string"},
                "actions": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": sorted(ASSISTANT_ACTIONS)},
                            "clipId": {"type": ["string", "null"]},
                            "name": {"type": ["string", "null"]},
                            "text": {"type": ["string", "null"]},
                            "start": {"type": ["number", "null"]},
                            "end": {"type": ["number", "null"]},
                            "duration": {"type": ["number", "null"]},
                            "volume": {"type": ["number", "null"]},
                            "order": {"type": ["integer", "null"]},
                        },
                        "required": ["type"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["reply", "summary", "actions"],
            "additionalProperties": False,
        }

    def _project_context(self, project: Dict[str, Any]) -> Dict[str, Any]:
        assets = {
            asset["assetId"]: {
                "name": asset["name"],
                "kind": asset["kind"],
                "duration": asset.get("duration", 0),
            }
            for asset in project.get("assets", [])
        }
        clips = [
            {
                "clipId": clip["clipId"],
                "track": clip["track"],
                "asset": assets.get(clip.get("assetId"), {}).get("name"),
                "timelineStart": clip.get("timelineStart"),
                "duration": clip.get("duration"),
                "sourceStart": clip.get("sourceStart"),
                "sourceEnd": clip.get("sourceEnd"),
                "volume": clip.get("volume"),
                "text": clip.get("text"),
                "order": clip.get("order"),
            }
            for clip in project.get("clips", [])
        ]
        return {
            "projectId": project["projectId"],
            "name": project["name"],
            "settings": project["settings"],
            "duration": self._timeline_duration(project),
            "clips": clips,
        }

    def _validate_assistant_actions(self, payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise EditorSuiteError("LLM_INVALID_RESPONSE", "O copiloto retornou resposta invalida.", 502)
        raw_actions = payload.get("actions")
        if not isinstance(raw_actions, list) or len(raw_actions) > 20:
            raise EditorSuiteError("LLM_INVALID_RESPONSE", "A lista de acoes do copiloto e invalida.", 502)
        actions = []
        for raw in raw_actions:
            if not isinstance(raw, dict) or raw.get("type") not in ASSISTANT_ACTIONS:
                continue
            action = {"type": raw["type"]}
            for key in ("clipId", "name", "text", "start", "end", "duration", "volume", "order"):
                if key in raw and raw[key] is not None:
                    action[key] = raw[key]
            actions.append(action)
        return {
            "reply": str(payload.get("reply") or "")[:4000],
            "summary": str(payload.get("summary") or "")[:1000],
            "actions": actions,
        }

    def _apply_assistant_actions(
        self,
        project: Dict[str, Any],
        actions: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        for action in actions:
            kind = action["type"]
            if kind == "rename_project":
                project["name"] = _safe_project_name(str(action.get("name") or ""))
                continue
            if kind == "add_text":
                text = str(action.get("text") or "").strip()
                if not text:
                    continue
                clip = self._normalize_clip(
                    project,
                    {
                        "clipId": uuid.uuid4().hex,
                        "track": "text",
                        "assetId": None,
                        "text": text,
                        "timelineStart": max(0.0, _float(action.get("start"), 0.0)),
                        "duration": max(0.5, _float(action.get("duration"), 3.0)),
                        "order": len(
                            [c for c in project.get("clips", []) if c.get("track") == "text"]
                        ),
                        "createdAt": _now_iso(),
                    },
                )
                project.setdefault("clips", []).append(clip)
                continue
            clip_id = str(action.get("clipId") or "")
            clip = next(
                (item for item in project.get("clips", []) if item.get("clipId") == clip_id),
                None,
            )
            if not clip:
                continue
            if kind == "delete_clip":
                project["clips"] = [
                    item for item in project.get("clips", []) if item.get("clipId") != clip_id
                ]
            elif kind == "set_volume":
                clip["volume"] = max(0.0, min(4.0, _float(action.get("volume"), 1.0)))
            elif kind == "move_clip":
                if clip.get("track") == "video":
                    clip["order"] = max(0, min(10000, int(action.get("order") or 0)))
                else:
                    clip["timelineStart"] = max(0.0, _float(action.get("start"), 0.0))
            elif kind == "trim_clip" and clip.get("track") != "text":
                payload: Dict[str, Any] = {}
                if "start" in action:
                    payload["sourceStart"] = max(0.0, _float(action["start"], 0.0))
                if "end" in action:
                    payload["sourceEnd"] = max(0.05, _float(action["end"], 0.05))
                normalized = self._normalize_clip(project, payload, clip)
                clip.clear()
                clip.update(normalized)
        return project

    def assist(self, project_id: str, spec: AssistantCreate) -> Dict[str, Any]:
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, spec.expectedRevision)
            context = self._project_context(project)
        models = self._ollama_models()
        model = spec.model if spec.model in models else ""
        if not model:
            preferred = os.environ.get("MAESTRO_EDITOR_LLM_MODEL", "").strip()
            default_order = (
                preferred,
                "qwen3.5:4b",
                "qwen3:4b",
                "gemma3:4b",
            )
            model = next((item for item in default_order if item and item in models), "")
            if not model:
                model = models[0] if models else ""
        if not model:
            raise EditorSuiteError(
                "OLLAMA_UNAVAILABLE",
                "Ollama esta offline ou nao possui um modelo instalado.",
                503,
            )
        schema = self._assistant_schema()
        system = (
            "Voce e o editor assistente do Pemara Maestro. Proponha apenas acoes do schema. "
            "Nunca invente clipId, arquivo, pessoa, caminho ou comando de sistema. "
            "O CapCut Local recebe o mesmo projeto, assets e timeline por manifesto; "
            "nao invente um formato paralelo. Voz cloud e Chatterbox so podem ser "
            "iniciados por uma acao explicita do usuario, nunca pelo copiloto. "
            "A trilha video e sequencial; move_clip nela usa order. "
            "Nas trilhas de audio/texto, move_clip usa start em segundos. "
            "Responda em portugues brasileiro, de forma curta e concreta."
        )
        user = (
            f"Projeto atual:\n{json.dumps(context, ensure_ascii=False)}\n\n"
            f"Pedido do usuario:\n{spec.instruction}\n\n"
            f"Schema obrigatorio:\n{json.dumps(schema, ensure_ascii=False)}"
        )
        request_payload = {
            "model": model,
            "stream": False,
            "think": False,
            "keep_alive": "90s",
            "format": schema,
            "options": {
                "temperature": 0,
                "num_ctx": 8192,
                "num_predict": 768,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = ((result.get("message") or {}).get("content") or "").strip()
            proposal = self._validate_assistant_actions(json.loads(content))
        except urllib.error.HTTPError as exc:
            try:
                raw_error = exc.read().decode("utf-8", errors="replace")
                parsed_error = json.loads(raw_error)
                upstream_error = str(parsed_error.get("error") or raw_error).strip()
            except (OSError, json.JSONDecodeError, AttributeError):
                upstream_error = ""
            details = f"HTTP {exc.code}"
            if upstream_error:
                details = f"{details}: {upstream_error[:1800]}"
            raise EditorSuiteError(
                "OLLAMA_REQUEST_FAILED",
                "O modelo local recusou o pedido.",
                502,
                details,
            ) from exc
        except urllib.error.URLError as exc:
            raise EditorSuiteError("OLLAMA_UNAVAILABLE", "Ollama nao respondeu.", 503) from exc
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise EditorSuiteError(
                "LLM_INVALID_RESPONSE",
                "O copiloto retornou uma resposta que nao passou na validacao.",
                502,
            ) from exc
        response: Dict[str, Any] = {
            "ok": True,
            "model": model,
            "applied": False,
            "proposal": proposal,
        }
        if spec.apply and proposal["actions"]:
            with self.lock:
                latest = self._load_project(project_id)
                self._check_revision(latest, spec.expectedRevision)
                updated = self._apply_assistant_actions(latest, proposal["actions"])
                response["project"] = self._decorate_project(self._save_project(updated))
                response["applied"] = True
        return response

    def apply_assistant_proposal(
        self,
        project_id: str,
        spec: AssistantApply,
    ) -> Dict[str, Any]:
        """Apply exactly the reviewed actions with one atomic revision."""

        proposal = self._validate_assistant_actions(
            {
                "reply": "",
                "summary": "",
                "actions": [
                    action.model_dump(exclude_none=True)
                    for action in spec.actions
                ],
            }
        )
        if not proposal["actions"]:
            raise EditorSuiteError(
                "EMPTY_ASSISTANT_PROPOSAL",
                "A proposta revisada nao possui acoes aplicaveis.",
                422,
            )
        with self.lock:
            project = self._load_project(project_id)
            self._check_revision(project, spec.expectedRevision)
            updated = self._apply_assistant_actions(project, proposal["actions"])
            saved = self._save_project(updated)
        return {
            "ok": True,
            "applied": True,
            "actions": proposal["actions"],
            "project": self._decorate_project(saved),
        }

    # ---------- status ----------

    def capabilities(self) -> Dict[str, Any]:
        chatterbox_python = self._chatterbox_python()
        chatterbox_readiness = (
            self._chatterbox_gpu_status(release_idle=False)
            if chatterbox_python
            else None
        )
        system_voices = self._system_voices()
        models = self._ollama_models()
        whisper_models = self._offline_whisper_models()
        try:
            faster_whisper_installed = (
                importlib.util.find_spec("faster_whisper") is not None
            )
        except (ImportError, ValueError):
            faster_whisper_installed = False
        configured_model = os.environ.get("MAESTRO_EDITOR_LLM_MODEL", "").strip()
        default_model = next(
            (
                item
                for item in (
                    configured_model,
                    "qwen3.5:4b",
                    "qwen3:4b",
                    "gemma3:4b",
                )
                if item and item in models
            ),
            models[0] if models else "",
        )
        disk = shutil.disk_usage(self.root)
        return {
            "ok": True,
            "editor": {
                "ffmpeg": bool(shutil.which(self.ffmpeg) or Path(self.ffmpeg).is_file()),
                "ffprobe": bool(shutil.which(self.ffprobe) or Path(self.ffprobe).is_file()),
                "drawtext": self._ffmpeg_has_filter("drawtext"),
                "nvenc": self._ffmpeg_has_encoder("h264_nvenc"),
                "defaultEncoder": "cpu",
            },
            "voice": {
                "recommended": "chatterbox_multilingual_v3",
                "chatterbox": {
                    "installed": bool(chatterbox_python),
                    "supportsVoiceClone": bool(chatterbox_python),
                    "languages": ["pt", "en", "es", "fr", "de", "it"],
                    "previewMaxCharacters": VOICE_PREVIEW_MAX_CHARS,
                    "readiness": chatterbox_readiness,
                },
                "system": {
                    "installed": bool(system_voices),
                    "voices": system_voices,
                    "supportsVoiceClone": False,
                },
                "elevenlabs": self._elevenlabs_capabilities(),
                "profiles": self.list_voice_profiles(),
            },
            "assistant": {
                "ollama": bool(models),
                "models": models,
                "defaultModel": default_model,
            },
            "captions": {
                "offlineCpuAsr": bool(faster_whisper_installed and whisper_models),
                "engine": "faster-whisper",
                "device": "cpu",
                "computeType": "int8",
                "model": whisper_models[0]["name"] if whisper_models else "",
                "models": [item["name"] for item in whisper_models],
                "downloadsDisabled": True,
            },
            "storage": {
                "freeBytes": disk.free,
                "totalBytes": disk.total,
                "lowSpace": disk.free < 15 * 1024 * 1024 * 1024,
                "neuralVoiceInstallRecommended": disk.free >= 15 * 1024 * 1024 * 1024,
            },
        }


def create_editor_router(
    suite: EditorSuite,
    *,
    is_internal_request: Callable[[Request], bool],
    forbidden_response: Callable[[], JSONResponse],
) -> APIRouter:
    router = APIRouter(prefix="/api/editor", tags=["editor"])

    def protected(request: Request) -> Optional[JSONResponse]:
        return None if is_internal_request(request) else forbidden_response()

    @router.get("/capabilities")
    async def editor_capabilities(request: Request):
        denied = protected(request)
        if denied:
            return denied
        return suite.capabilities()

    @router.get("/projects")
    async def editor_projects(request: Request, page: int = 1, pageSize: int = 20):
        denied = protected(request)
        if denied:
            return denied
        return suite.list_projects(page, pageSize)

    @router.post("/projects", status_code=201)
    async def editor_project_create(request: Request, spec: ProjectCreate):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "project": suite.create_project(spec)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/projects/{project_id}")
    async def editor_project_get(request: Request, project_id: str):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "project": suite.get_project(project_id)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.patch("/projects/{project_id}")
    async def editor_project_patch(request: Request, project_id: str, patch: ProjectPatch):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "project": suite.patch_project(project_id, patch)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/assets", status_code=201)
    async def editor_assets_upload(
        request: Request,
        project_id: str,
        files: List[UploadFile] = File(...),
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            if not files or len(files) > 50:
                raise EditorSuiteError(
                    "INVALID_UPLOAD_COUNT",
                    "Envie de 1 a 50 arquivos por vez.",
                )
            assets = [suite.add_upload(project_id, upload) for upload in files]
            return {
                "ok": True,
                "assets": assets,
                "project": suite.get_project(project_id),
            }
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/projects/{project_id}/assets/{asset_id}/content")
    async def editor_asset_content(
        request: Request,
        project_id: str,
        asset_id: str,
        download: bool = False,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            path, asset = suite.asset_path(project_id, asset_id)
            return FileResponse(
                path,
                media_type=asset.get("mediaType")
                or mimetypes.guess_type(path.name)[0]
                or "application/octet-stream",
                filename=asset["name"] if download else None,
            )
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/clips", status_code=201)
    async def editor_clip_create(request: Request, project_id: str, spec: ClipCreate):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "project": suite.add_clip(project_id, spec)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.patch("/projects/{project_id}/clips/{clip_id}")
    async def editor_clip_patch(
        request: Request,
        project_id: str,
        clip_id: str,
        patch: ClipPatch,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "project": suite.patch_clip(project_id, clip_id, patch)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.delete("/projects/{project_id}/clips/{clip_id}")
    async def editor_clip_delete(
        request: Request,
        project_id: str,
        clip_id: str,
        spec: ClipDelete,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {
                "ok": True,
                "project": suite.delete_clip(project_id, clip_id, spec.expectedRevision),
            }
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/renders", status_code=202)
    async def editor_render_start(request: Request, project_id: str, spec: RenderCreate):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "job": suite.start_render(project_id, spec)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/captions", status_code=202)
    async def editor_captions_start(
        request: Request,
        project_id: str,
        spec: CaptionCreate,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "job": suite.start_captions(project_id, spec)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/jobs")
    async def editor_jobs(
        request: Request,
        projectId: str = "",
        limit: int = 50,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "items": suite.list_jobs(projectId, limit)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/jobs/{job_id}")
    async def editor_job_get(request: Request, job_id: str):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "job": suite.get_job(job_id)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/jobs/{job_id}/cancel")
    async def editor_job_cancel(request: Request, job_id: str):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "job": suite.cancel_job(job_id)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/projects/{project_id}/exports/{export_id}")
    async def editor_export_get(
        request: Request,
        project_id: str,
        export_id: str,
        download: bool = False,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            path, export = suite.export_path(project_id, export_id)
            return FileResponse(
                path,
                media_type="video/mp4",
                filename=export["filename"] if download else None,
            )
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/projects/{project_id}/handoffs/capcut-local")
    async def editor_capcut_local_handoff(
        request: Request,
        project_id: str,
        mode: Literal["quick", "editable"] = "quick",
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            path, metadata = suite.capcut_local_handoff_path(project_id, mode)
            return FileResponse(
                path,
                media_type="application/zip",
                filename=metadata["filename"],
                headers={
                    "X-Pemara-Handoff-Mode": metadata["mode"],
                    "X-Pemara-Handoff-SHA256": metadata["sha256"],
                },
            )
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.get("/voices")
    async def editor_voices(request: Request):
        denied = protected(request)
        if denied:
            return denied
        capabilities = suite.capabilities()["voice"]
        return {"ok": True, **capabilities}

    @router.post("/voices", status_code=201)
    async def editor_voice_profile_create(
        request: Request,
        name: str = Form(...),
        consent: str = Form(...),
        file: UploadFile = File(...),
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            accepted = consent.strip().lower() in {"1", "true", "yes", "sim", "on"}
            return {
                "ok": True,
                "voiceProfile": suite.create_voice_profile(name, accepted, file),
            }
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/voices", status_code=202)
    async def editor_voice_create(request: Request, project_id: str, spec: VoiceCreate):
        denied = protected(request)
        if denied:
            return denied
        try:
            return {"ok": True, "job": suite.start_voice(project_id, spec)}
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/assistant")
    async def editor_assistant(request: Request, project_id: str, spec: AssistantCreate):
        denied = protected(request)
        if denied:
            return denied
        try:
            return suite.assist(project_id, spec)
        except EditorSuiteError as exc:
            return _error_response(exc)

    @router.post("/projects/{project_id}/assistant/apply")
    async def editor_assistant_apply(
        request: Request,
        project_id: str,
        spec: AssistantApply,
    ):
        denied = protected(request)
        if denied:
            return denied
        try:
            return suite.apply_assistant_proposal(project_id, spec)
        except EditorSuiteError as exc:
            return _error_response(exc)

    return router
