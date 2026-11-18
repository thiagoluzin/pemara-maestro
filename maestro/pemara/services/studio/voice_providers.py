"""Secure, dependency-free voice provider contracts for Pemara Studio.

This module deliberately contains no web-framework or editor-suite coupling.  It
can therefore be imported by any local editor while keeping provider credentials
on the server.  It never logs requests, response bodies, or credentials.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


PROVIDER_NAME = "elevenlabs"
DEFAULT_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_MAX_AUDIO_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_JSON_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_TEXT_CHARACTERS = 10_000

_SAFE_DETAIL_KEYS = frozenset({"field", "limit", "providerCode"})
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_VOICE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_OUTPUT_FORMAT_RE = re.compile(
    r"^(?:mp3|pcm|ulaw|alaw|opus|wav)_[0-9]{4,5}(?:_[0-9]{2,3})?$"
)
_LANGUAGE_CODE_RE = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z]{2,4})?$")
_SSML_RE = re.compile(
    r"<\s*/?\s*(?:speak|break|prosody|phoneme|say-as|voice|audio|emphasis)\b",
    re.IGNORECASE,
)
_BRACKET_TAG_RE = re.compile(r"\[([A-Za-z][A-Za-z ]{0,39})\]")


class VoiceProviderError(RuntimeError):
    """Stable, non-sensitive error returned by a voice provider boundary."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        safe_code = code if re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code) else "VOICE_ERROR"
        safe_details: dict[str, Any] = {}
        for key, value in (details or {}).items():
            if key not in _SAFE_DETAIL_KEYS:
                continue
            if isinstance(value, bool):
                safe_details[key] = value
            elif isinstance(value, int):
                safe_details[key] = value
            elif isinstance(value, str):
                safe_details[key] = value[:128]
        super().__init__(message)
        self.code = safe_code
        self.message = message
        self.status = int(status) if status is not None else None
        self.retryable = bool(retryable)
        self.details = MappingProxyType(safe_details)

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "provider": PROVIDER_NAME,
            "retryable": self.retryable,
        }
        if self.status is not None:
            error["status"] = self.status
        if self.details:
            error["details"] = dict(self.details)
        return {"error": error}


def _validation_error(
    message: str,
    *,
    field: str,
    code: str = "VALIDATION_ERROR",
    limit: int | None = None,
) -> VoiceProviderError:
    details: dict[str, Any] = {"field": field}
    if limit is not None:
        details["limit"] = limit
    return VoiceProviderError(code, message, details=details)


def _number_in_range(value: Any, *, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _validation_error("Parâmetro de voz inválido.", field=field)
    number = float(value)
    if not minimum <= number <= maximum:
        raise _validation_error(
            f"Parâmetro de voz deve ficar entre {minimum:g} e {maximum:g}.",
            field=field,
        )
    return number


@dataclass(frozen=True)
class VoiceSettings:
    """Provider settings supported by ElevenLabs v2/Flash/Turbo models."""

    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    speed: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stability",
            _number_in_range(self.stability, field="stability", minimum=0.0, maximum=1.0),
        )
        object.__setattr__(
            self,
            "similarity_boost",
            _number_in_range(
                self.similarity_boost,
                field="similarityBoost",
                minimum=0.0,
                maximum=1.0,
            ),
        )
        object.__setattr__(
            self,
            "style",
            _number_in_range(self.style, field="style", minimum=0.0, maximum=1.0),
        )
        if not isinstance(self.use_speaker_boost, bool):
            raise _validation_error(
                "useSpeakerBoost deve ser booleano.",
                field="useSpeakerBoost",
            )
        object.__setattr__(
            self,
            "speed",
            _number_in_range(self.speed, field="speed", minimum=0.7, maximum=1.2),
        )

    def provider_payload(self) -> dict[str, Any]:
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
            "speed": self.speed,
        }


@dataclass(frozen=True)
class VoicePreset:
    name: str
    model_id: str
    output_format: str
    voice_settings: VoiceSettings | None
    supports_audio_tags: bool
    description: str


VOICE_PRESETS: Mapping[str, VoicePreset] = MappingProxyType(
    {
        "expressive_v3": VoicePreset(
            name="expressive_v3",
            model_id="eleven_v3",
            output_format="mp3_44100_128",
            voice_settings=None,
            supports_audio_tags=True,
            description="Interpretação dramática com tags de performance.",
        ),
        "stable_longform": VoicePreset(
            name="stable_longform",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.62,
                similarity_boost=0.78,
                style=0.08,
                use_speaker_boost=True,
                speed=1.0,
            ),
            supports_audio_tags=False,
            description="Identidade vocal estável para narração longa.",
        ),
        "preview": VoicePreset(
            name="preview",
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True,
                speed=1.0,
            ),
            supports_audio_tags=False,
            description="Prévia rápida e econômica.",
        ),
    }
)

# These are documented v3 performance cues. Unknown bracketed directions are
# rejected instead of being forwarded as uncontrolled provider instructions.
ALLOWED_AUDIO_TAGS = frozenset(
    {
        "whispers",
        "sighs",
        "excited",
        "crying",
        "sarcastic",
        "laughs",
        "chuckles",
    }
)

PERFORMANCE_DIRECTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "neutral": (),
        "natural": (),
        "intimate": ("whispers",),
        "whisper": ("whispers",),
        "intense": ("excited",),
        "dramatic": ("sighs", "excited"),
        "joyful": ("excited",),
        "sad": ("crying",),
        "angry": ("excited",),
        "sarcastic": ("sarcastic",),
        "suspenseful": ("whispers",),
    }
)

_CHATTERBOX_DEFAULTS: Mapping[str, float] = MappingProxyType(
    {
        "exaggeration": 0.50,
        "cfg_weight": 0.50,
        "temperature": 0.80,
        "repetition_penalty": 2.00,
        "min_p": 0.05,
        "top_p": 1.00,
    }
)

_CHATTERBOX_PRESET_TARGETS: Mapping[str, Mapping[str, float]] = MappingProxyType(
    {
        "natural": _CHATTERBOX_DEFAULTS,
        "intense": MappingProxyType(
            {
                "exaggeration": 0.92,
                "cfg_weight": 0.34,
                "temperature": 0.98,
                "repetition_penalty": 2.10,
                "min_p": 0.03,
                "top_p": 0.95,
            }
        ),
        "dramatic": MappingProxyType(
            {
                "exaggeration": 0.82,
                "cfg_weight": 0.40,
                "temperature": 0.92,
                "repetition_penalty": 2.05,
                "min_p": 0.04,
                "top_p": 0.97,
            }
        ),
        "whisper": MappingProxyType(
            {
                "exaggeration": 0.38,
                "cfg_weight": 0.58,
                "temperature": 0.72,
                "repetition_penalty": 2.10,
                "min_p": 0.06,
                "top_p": 0.90,
            }
        ),
        "joyful": MappingProxyType(
            {
                "exaggeration": 0.76,
                "cfg_weight": 0.40,
                "temperature": 0.94,
                "repetition_penalty": 1.90,
                "min_p": 0.04,
                "top_p": 0.98,
            }
        ),
        "sad": MappingProxyType(
            {
                "exaggeration": 0.60,
                "cfg_weight": 0.52,
                "temperature": 0.76,
                "repetition_penalty": 2.10,
                "min_p": 0.06,
                "top_p": 0.93,
            }
        ),
        "angry": MappingProxyType(
            {
                "exaggeration": 0.96,
                "cfg_weight": 0.28,
                "temperature": 1.00,
                "repetition_penalty": 2.20,
                "min_p": 0.03,
                "top_p": 0.92,
            }
        ),
    }
)

_CHATTERBOX_RANGES: Mapping[str, tuple[float, float]] = MappingProxyType(
    {
        "exaggeration": (0.0, 1.0),
        "cfg_weight": (0.0, 1.0),
        "temperature": (0.05, 2.0),
        "repetition_penalty": (1.0, 3.0),
        "min_p": (0.0, 1.0),
        "top_p": (0.05, 1.0),
    }
)

_CHATTERBOX_OVERRIDE_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "exaggeration": "exaggeration",
        "cfg_weight": "cfg_weight",
        "cfgWeight": "cfg_weight",
        "temperature": "temperature",
        "repetition_penalty": "repetition_penalty",
        "repetitionPenalty": "repetition_penalty",
        "min_p": "min_p",
        "minP": "min_p",
        "top_p": "top_p",
        "topP": "top_p",
    }
)


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class _HttpResult:
    body: bytes
    content_type: str
    request_id: str | None


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise _validation_error("Texto de voz deve ser uma string.", field="text")
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise _validation_error("Texto de voz não pode ficar vazio.", field="text")
    if "\x00" in normalized:
        raise _validation_error("Texto de voz contém caractere inválido.", field="text")
    if _SSML_RE.search(normalized):
        raise _validation_error(
            "SSML não é aceito neste contrato de voz.",
            field="text",
            code="SSML_NOT_ALLOWED",
        )
    return normalized


def _validate_audio_tags_in_text(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for match in _BRACKET_TAG_RE.finditer(text):
        tag = " ".join(match.group(1).lower().split())
        if tag not in ALLOWED_AUDIO_TAGS:
            raise _validation_error(
                "O texto contém uma tag de áudio não permitida.",
                field="text",
                code="AUDIO_TAG_NOT_ALLOWED",
            )
        if tag not in found:
            found.append(tag)
    return tuple(found)


def render_performance_text(
    text: str,
    *,
    direction: str = "neutral",
    audio_tags: Sequence[str] | None = None,
    max_characters: int = DEFAULT_MAX_TEXT_CHARACTERS,
) -> tuple[str, tuple[str, ...]]:
    """Validate and prefix a script with a small, explicit v3 tag whitelist."""

    normalized = _normalize_text(text)
    if direction not in PERFORMANCE_DIRECTIONS:
        raise _validation_error(
            "Direção de performance não reconhecida.",
            field="direction",
            code="UNSUPPORTED_DIRECTION",
        )
    if len(normalized) > max_characters:
        raise _validation_error(
            "Texto de voz excede o limite configurado.",
            field="text",
            code="TEXT_TOO_LONG",
            limit=max_characters,
        )

    requested: list[str] = list(PERFORMANCE_DIRECTIONS[direction])
    if isinstance(audio_tags, str):
        raise _validation_error("audioTags deve ser uma lista.", field="audioTags")
    for raw_tag in audio_tags or ():
        if not isinstance(raw_tag, str):
            raise _validation_error("Tag de áudio inválida.", field="audioTags")
        tag = " ".join(raw_tag.lower().split())
        if tag not in ALLOWED_AUDIO_TAGS:
            raise _validation_error(
                "Tag de áudio não permitida.",
                field="audioTags",
                code="AUDIO_TAG_NOT_ALLOWED",
            )
        if tag not in requested:
            requested.append(tag)
    if len(requested) > 4:
        raise _validation_error(
            "Use no máximo quatro tags de áudio por geração.",
            field="audioTags",
            code="TOO_MANY_AUDIO_TAGS",
            limit=4,
        )

    inline_tags = _validate_audio_tags_in_text(normalized)
    effective = list(requested)
    for tag in inline_tags:
        if tag not in effective:
            effective.append(tag)
    if len(effective) > 4:
        raise _validation_error(
            "Use no máximo quatro tags de áudio por geração.",
            field="audioTags",
            code="TOO_MANY_AUDIO_TAGS",
            limit=4,
        )

    prefix = " ".join(f"[{tag}]" for tag in requested)
    rendered = f"{prefix} {normalized}".strip()
    if len(rendered) > max_characters:
        raise _validation_error(
            "Texto com direção de performance excede o limite configurado.",
            field="text",
            code="TEXT_TOO_LONG",
            limit=max_characters,
        )
    return rendered, tuple(effective)


def deterministic_cache_key(
    *,
    text: str,
    voice_id: str,
    model_id: str,
    output_format: str,
    voice_settings: VoiceSettings | Mapping[str, Any] | None = None,
    language_code: str | None = None,
) -> str:
    """Return a deterministic key without exposing the script or credentials."""

    normalized = _normalize_text(text)
    if isinstance(voice_settings, VoiceSettings):
        settings_payload: Mapping[str, Any] | None = voice_settings.provider_payload()
    elif voice_settings is None:
        settings_payload = None
    elif isinstance(voice_settings, Mapping):
        settings_payload = dict(voice_settings)
    else:
        raise _validation_error("Configuração de voz inválida.", field="voiceSettings")
    canonical = json.dumps(
        {
            "schema": 1,
            "provider": PROVIDER_NAME,
            "text": normalized,
            "voiceId": voice_id,
            "modelId": model_id,
            "outputFormat": output_format,
            "voiceSettings": settings_payload,
            "languageCode": language_code or None,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def resolve_chatterbox_settings(
    preset: str = "natural",
    intensity: float = 0.5,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    """Resolve the editor's shared performance contract for Chatterbox.

    This function only calculates settings.  It never loads a model or executes
    a GPU job.  ``intensity=0`` yields Chatterbox multilingual defaults and
    ``intensity=1`` yields the full preset. Explicit, validated overrides win.
    """

    if preset not in _CHATTERBOX_PRESET_TARGETS:
        raise _validation_error(
            "Preset local de performance não reconhecido.",
            field="preset",
            code="UNSUPPORTED_PRESET",
        )
    mix = _number_in_range(intensity, field="intensity", minimum=0.0, maximum=1.0)
    target = _CHATTERBOX_PRESET_TARGETS[preset]
    resolved = {
        key: round(base + ((target[key] - base) * mix), 3)
        for key, base in _CHATTERBOX_DEFAULTS.items()
    }
    if overrides is None:
        return resolved
    if not isinstance(overrides, Mapping):
        raise _validation_error(
            "overrides deve ser um objeto.",
            field="overrides",
        )
    for raw_key, raw_value in overrides.items():
        if raw_key not in _CHATTERBOX_OVERRIDE_ALIASES:
            raise _validation_error(
                "Override local de voz não reconhecido.",
                field="overrides",
                code="UNSUPPORTED_VOICE_SETTING",
            )
        key = _CHATTERBOX_OVERRIDE_ALIASES[raw_key]
        minimum, maximum = _CHATTERBOX_RANGES[key]
        resolved[key] = round(
            _number_in_range(
                raw_value,
                field=raw_key,
                minimum=minimum,
                maximum=maximum,
            ),
            3,
        )
    return resolved


def chatterbox_expression_settings(
    *,
    direction: str = "neutral",
    intensity: float = 0.5,
) -> dict[str, float]:
    """Backward-compatible three-control view of local expression settings."""

    aliases = {
        "neutral": "natural",
        "natural": "natural",
        "intimate": "whisper",
        "whisper": "whisper",
        "intense": "intense",
        "dramatic": "dramatic",
        "joyful": "joyful",
        "sad": "sad",
        "angry": "angry",
        "sarcastic": "dramatic",
        "suspenseful": "whisper",
    }
    if direction not in aliases:
        raise _validation_error(
            "Direção de performance não reconhecida.",
            field="direction",
            code="UNSUPPORTED_DIRECTION",
        )
    resolved = resolve_chatterbox_settings(aliases[direction], intensity, None)
    return {
        "exaggeration": resolved["exaggeration"],
        "cfgWeight": resolved["cfg_weight"],
        "temperature": resolved["temperature"],
    }


class ElevenLabsVoiceProvider:
    """Server-side ElevenLabs client using only Python's standard library."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        default_preset: str | None = None,
        default_model_id: str | None = None,
        default_output_format: str | None = None,
        enable_logging: bool = True,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        retry_base_seconds: float = 0.25,
        max_audio_bytes: int = DEFAULT_MAX_AUDIO_BYTES,
        max_json_bytes: int = DEFAULT_MAX_JSON_BYTES,
        max_text_characters: int = DEFAULT_MAX_TEXT_CHARACTERS,
        opener: Callable[..., Any] | None = None,
        sleeper: Callable[[float], None] | None = None,
        jitter: Callable[[], float] | None = None,
    ) -> None:
        env_key = os.getenv("ELEVENLABS_API_KEY") if api_key is None else api_key
        self._api_key = env_key.strip() if isinstance(env_key, str) else ""
        self.base_url = self._validate_base_url(base_url)

        env_preset = os.getenv("ELEVENLABS_TTS_PRESET", "expressive_v3")
        self.default_preset = default_preset or env_preset
        if self.default_preset not in VOICE_PRESETS:
            raise _validation_error(
                "Preset de voz padrão não reconhecido.",
                field="defaultPreset",
                code="UNSUPPORTED_PRESET",
            )

        model_override = default_model_id
        if model_override is None:
            model_override = os.getenv("ELEVENLABS_TTS_MODEL_ID") or None
        self.default_model_id = (
            self._validate_model_id(model_override) if model_override is not None else None
        )

        output_override = default_output_format
        if output_override is None:
            output_override = os.getenv("ELEVENLABS_OUTPUT_FORMAT") or None
        self.default_output_format = (
            self._validate_output_format(output_override)
            if output_override is not None
            else None
        )

        if not isinstance(enable_logging, bool):
            raise _validation_error("enableLogging deve ser booleano.", field="enableLogging")
        self.enable_logging = enable_logging
        self.timeout_seconds = _number_in_range(
            timeout_seconds,
            field="timeoutSeconds",
            minimum=1.0,
            maximum=600.0,
        )
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise _validation_error("maxRetries deve ser inteiro.", field="maxRetries")
        if not 0 <= max_retries <= 5:
            raise _validation_error(
                "maxRetries deve ficar entre 0 e 5.",
                field="maxRetries",
            )
        self.max_retries = max_retries
        self.retry_base_seconds = _number_in_range(
            retry_base_seconds,
            field="retryBaseSeconds",
            minimum=0.0,
            maximum=10.0,
        )
        self.max_audio_bytes = self._validate_positive_limit(
            max_audio_bytes,
            field="maxAudioBytes",
            maximum=512 * 1024 * 1024,
        )
        self.max_json_bytes = self._validate_positive_limit(
            max_json_bytes,
            field="maxJsonBytes",
            maximum=32 * 1024 * 1024,
        )
        self.max_text_characters = self._validate_positive_limit(
            max_text_characters,
            field="maxTextCharacters",
            maximum=100_000,
        )
        self._opener = opener or urllib.request.urlopen
        self._sleeper = sleeper or time.sleep
        self._jitter = jitter or random.random

    @staticmethod
    def _validate_positive_limit(value: Any, *, field: str, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise _validation_error("Limite de provedor inválido.", field=field)
        return value

    @staticmethod
    def _validate_base_url(value: str) -> str:
        if not isinstance(value, str):
            raise _validation_error("URL do provedor inválida.", field="baseUrl")
        candidate = value.strip().rstrip("/")
        parsed = urllib.parse.urlsplit(candidate)
        is_loopback = parsed.hostname in {"127.0.0.1", "::1", "localhost"}
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback))
        ):
            raise _validation_error(
                "URL do provedor deve usar HTTPS.",
                field="baseUrl",
                code="INSECURE_PROVIDER_URL",
            )
        return candidate

    @staticmethod
    def _validate_model_id(value: str) -> str:
        if not isinstance(value, str) or not _MODEL_ID_RE.fullmatch(value):
            raise _validation_error("modelId inválido.", field="modelId")
        return value

    @staticmethod
    def _validate_voice_id(value: str) -> str:
        if not isinstance(value, str) or not _VOICE_ID_RE.fullmatch(value):
            raise _validation_error("voiceId inválido.", field="voiceId")
        return value

    @staticmethod
    def _validate_output_format(value: str) -> str:
        if not isinstance(value, str) or not _OUTPUT_FORMAT_RE.fullmatch(value):
            raise _validation_error("outputFormat inválido.", field="outputFormat")
        return value

    @staticmethod
    def _validate_language_code(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not _LANGUAGE_CODE_RE.fullmatch(value):
            raise _validation_error("languageCode inválido.", field="languageCode")
        return value.replace("_", "-")

    def _require_api_key(self) -> str:
        if not self._api_key or any(ord(char) < 32 for char in self._api_key):
            raise VoiceProviderError(
                "CONFIGURATION_ERROR",
                "ElevenLabs não está configurado no servidor.",
                details={"field": "ELEVENLABS_API_KEY"},
            )
        return self._api_key

    def _url(self, path: str, query: Mapping[str, Any] | None = None) -> str:
        url = f"{self.base_url}{path}"
        if query:
            encoded = urllib.parse.urlencode(
                {key: value for key, value in query.items() if value is not None}
            )
            if encoded:
                url = f"{url}?{encoded}"
        return url

    @staticmethod
    def _header(headers: Any, name: str) -> str:
        if headers is None:
            return ""
        try:
            value = headers.get(name, "")
        except (AttributeError, TypeError):
            return ""
        return str(value or "").strip()

    @staticmethod
    def _safe_request_id(value: str) -> str | None:
        return value if _SAFE_ID_RE.fullmatch(value) else None

    @staticmethod
    def _error_for_status(status: int) -> VoiceProviderError:
        if status == 401:
            return VoiceProviderError(
                "AUTHENTICATION_FAILED",
                "Credencial do provedor de voz recusada.",
                status=status,
            )
        if status == 403:
            return VoiceProviderError(
                "ACCESS_DENIED",
                "A credencial não possui permissão para esta operação.",
                status=status,
            )
        if status == 404:
            return VoiceProviderError(
                "VOICE_NOT_FOUND",
                "Voz ou recurso do provedor não encontrado.",
                status=status,
            )
        if status == 429:
            return VoiceProviderError(
                "RATE_LIMITED",
                "Limite temporário do provedor de voz atingido.",
                status=status,
                retryable=True,
            )
        if 500 <= status <= 599:
            return VoiceProviderError(
                "PROVIDER_UNAVAILABLE",
                "Provedor de voz temporariamente indisponível.",
                status=status,
                retryable=True,
            )
        if status in {400, 409, 422}:
            return VoiceProviderError(
                "PROVIDER_REJECTED",
                "O provedor recusou a solicitação de voz.",
                status=status,
            )
        return VoiceProviderError(
            "PROVIDER_HTTP_ERROR",
            "O provedor de voz retornou uma falha.",
            status=status,
        )

    def _retry_delay(self, retry_index: int) -> float:
        try:
            random_part = float(self._jitter())
        except (TypeError, ValueError):
            random_part = 0.5
        random_part = min(1.0, max(0.0, random_part))
        return self.retry_base_seconds * (2**retry_index) * (0.75 + (0.5 * random_part))

    def _read_limited(self, response: Any, *, limit: int) -> bytes:
        content_length = self._header(getattr(response, "headers", None), "Content-Length")
        if content_length:
            try:
                declared_length = int(content_length)
            except ValueError as exc:
                raise VoiceProviderError(
                    "INVALID_PROVIDER_RESPONSE",
                    "O provedor retornou tamanho de resposta inválido.",
                ) from exc
            if declared_length < 0 or declared_length > limit:
                raise VoiceProviderError(
                    "PROVIDER_RESPONSE_TOO_LARGE",
                    "A resposta do provedor excede o limite seguro.",
                    details={"limit": limit},
                )
        try:
            body = response.read(limit + 1)
        except (OSError, ValueError) as exc:
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "Não foi possível ler a resposta do provedor.",
            ) from exc
        if not isinstance(body, (bytes, bytearray)):
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou um corpo de resposta inválido.",
            )
        body_bytes = bytes(body)
        if len(body_bytes) > limit:
            raise VoiceProviderError(
                "PROVIDER_RESPONSE_TOO_LARGE",
                "A resposta do provedor excede o limite seguro.",
                details={"limit": limit},
            )
        return body_bytes

    def _request(
        self,
        *,
        method: str,
        path: str,
        query: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        accept: str,
        max_bytes: int,
    ) -> _HttpResult:
        api_key = self._require_api_key()
        data = None
        headers = {
            "Accept": accept,
            "User-Agent": "Pemara-Voice-Gateway/1.0",
            "xi-api-key": api_key,
        }
        if json_body is not None:
            data = json.dumps(
                json_body,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._url(path, query),
            data=data,
            headers=headers,
            method=method,
        )

        for attempt in range(self.max_retries + 1):
            response = None
            try:
                response = self._opener(request, timeout=self.timeout_seconds)
                status = int(
                    getattr(response, "status", None)
                    or getattr(response, "code", None)
                    or response.getcode()
                )
                if status < 200 or status >= 300:
                    error = self._error_for_status(status)
                    if error.retryable and attempt < self.max_retries:
                        self._sleeper(self._retry_delay(attempt))
                        continue
                    raise error
                body = self._read_limited(response, limit=max_bytes)
                response_headers = getattr(response, "headers", None)
                content_type = self._header(response_headers, "Content-Type")
                request_id = self._safe_request_id(
                    self._header(response_headers, "request-id")
                    or self._header(response_headers, "x-request-id")
                )
                return _HttpResult(
                    body=body,
                    content_type=content_type,
                    request_id=request_id,
                )
            except urllib.error.HTTPError as exc:
                status = int(exc.code)
                error = self._error_for_status(status)
                if error.retryable and attempt < self.max_retries:
                    self._sleeper(self._retry_delay(attempt))
                    continue
                raise error from None
            except VoiceProviderError:
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                # The automatic retry contract is intentionally restricted to
                # explicit HTTP 429 and 5xx responses.
                raise VoiceProviderError(
                    "PROVIDER_CONNECTION_ERROR",
                    "Não foi possível conectar ao provedor de voz.",
                    retryable=False,
                ) from exc
            finally:
                if response is not None:
                    try:
                        response.close()
                    except (AttributeError, OSError):
                        pass
        raise VoiceProviderError(
            "PROVIDER_UNAVAILABLE",
            "Provedor de voz temporariamente indisponível.",
            retryable=True,
        )

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        query: Mapping[str, Any] | None = None,
    ) -> Any:
        result = self._request(
            method=method,
            path=path,
            query=query,
            accept="application/json",
            max_bytes=self.max_json_bytes,
        )
        media_type = result.content_type.partition(";")[0].strip().lower()
        if media_type != "application/json" and not media_type.endswith("+json"):
            raise VoiceProviderError(
                "INVALID_PROVIDER_CONTENT_TYPE",
                "O provedor retornou um tipo de conteúdo inesperado.",
            )
        if not result.body:
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou uma resposta vazia.",
            )
        try:
            return json.loads(result.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou JSON inválido.",
            ) from exc

    @staticmethod
    def _safe_text(value: Any, *, limit: int = 500) -> str | None:
        if not isinstance(value, str):
            return None
        clean = "".join(char for char in value.strip() if char >= " " or char in "\t")
        return clean[:limit] or None

    @staticmethod
    def _safe_bool(value: Any) -> bool | None:
        return value if isinstance(value, bool) else None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value

    @staticmethod
    def _safe_https_url(value: Any) -> str | None:
        if not isinstance(value, str) or len(value) > 2_048:
            return None
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        return value

    def list_voices(
        self,
        *,
        page_size: int = 30,
        next_page_token: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100:
            raise _validation_error(
                "pageSize deve ficar entre 1 e 100.",
                field="pageSize",
            )
        if next_page_token is not None and (
            not isinstance(next_page_token, str)
            or not next_page_token
            or len(next_page_token) > 512
            or any(ord(char) < 32 for char in next_page_token)
        ):
            raise _validation_error("nextPageToken inválido.", field="nextPageToken")
        if search is not None and (
            not isinstance(search, str)
            or len(search.strip()) > 100
            or any(ord(char) < 32 for char in search)
        ):
            raise _validation_error("Busca de vozes inválida.", field="search")

        payload = self._request_json(
            method="GET",
            path="/v2/voices",
            query={
                "page_size": page_size,
                "next_page_token": next_page_token,
                "search": search.strip() if isinstance(search, str) else None,
            },
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("voices"), list):
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou uma lista de vozes inválida.",
            )
        items: list[dict[str, Any]] = []
        for raw_voice in payload["voices"]:
            if not isinstance(raw_voice, dict):
                raise VoiceProviderError(
                    "INVALID_PROVIDER_RESPONSE",
                    "O provedor retornou uma voz inválida.",
                )
            voice_id = self._safe_text(raw_voice.get("voice_id"), limit=128)
            name = self._safe_text(raw_voice.get("name"), limit=200)
            if not voice_id or not _VOICE_ID_RE.fullmatch(voice_id) or not name:
                raise VoiceProviderError(
                    "INVALID_PROVIDER_RESPONSE",
                    "O provedor retornou uma voz inválida.",
                )
            raw_labels = raw_voice.get("labels")
            labels: dict[str, str] = {}
            if isinstance(raw_labels, dict):
                for key, value in list(raw_labels.items())[:30]:
                    safe_key = self._safe_text(key, limit=80)
                    safe_value = self._safe_text(value, limit=200)
                    if safe_key and safe_value:
                        labels[safe_key] = safe_value
            items.append(
                {
                    "voiceId": voice_id,
                    "name": name,
                    "category": self._safe_text(raw_voice.get("category"), limit=100),
                    "description": self._safe_text(raw_voice.get("description"), limit=500),
                    "previewUrl": self._safe_https_url(raw_voice.get("preview_url")),
                    "labels": labels,
                }
            )
        return {
            "provider": PROVIDER_NAME,
            "items": items,
            "hasMore": bool(payload.get("has_more"))
            if isinstance(payload.get("has_more"), bool)
            else False,
            "nextPageToken": self._safe_text(payload.get("next_page_token"), limit=512),
            "totalCount": self._safe_int(payload.get("total_count")),
        }

    def get_subscription(self) -> dict[str, Any]:
        payload = self._request_json(method="GET", path="/v1/user/subscription")
        if not isinstance(payload, dict):
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou dados de assinatura inválidos.",
            )
        count = self._safe_int(payload.get("character_count"))
        limit = self._safe_int(payload.get("character_limit"))
        remaining = max(0, limit - count) if count is not None and limit is not None else None
        return {
            "provider": PROVIDER_NAME,
            "tier": self._safe_text(payload.get("tier"), limit=100),
            "characterCount": count,
            "characterLimit": limit,
            "remainingCharacters": remaining,
            "canExtendCharacterLimit": self._safe_bool(
                payload.get("can_extend_character_limit")
            ),
            "nextCharacterCountResetUnix": self._safe_int(
                payload.get("next_character_count_reset_unix")
            ),
            "voiceSlotsUsed": self._safe_int(payload.get("voice_slots_used")),
            "voiceLimit": self._safe_int(payload.get("voice_limit")),
            "professionalVoiceLimit": self._safe_int(
                payload.get("professional_voice_limit")
            ),
        }

    def list_models(self) -> dict[str, Any]:
        payload = self._request_json(method="GET", path="/v1/models")
        raw_models = payload.get("models") if isinstance(payload, dict) else payload
        if not isinstance(raw_models, list):
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou uma lista de modelos inválida.",
            )
        items: list[dict[str, Any]] = []
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                raise VoiceProviderError(
                    "INVALID_PROVIDER_RESPONSE",
                    "O provedor retornou um modelo inválido.",
                )
            model_id = self._safe_text(raw_model.get("model_id"), limit=128)
            if not model_id or not _MODEL_ID_RE.fullmatch(model_id):
                raise VoiceProviderError(
                    "INVALID_PROVIDER_RESPONSE",
                    "O provedor retornou um modelo inválido.",
                )
            languages: list[dict[str, str | None]] = []
            raw_languages = raw_model.get("languages")
            if isinstance(raw_languages, list):
                for raw_language in raw_languages[:200]:
                    if not isinstance(raw_language, dict):
                        continue
                    language_id = self._safe_text(raw_language.get("language_id"), limit=30)
                    if not language_id:
                        continue
                    languages.append(
                        {
                            "languageId": language_id,
                            "name": self._safe_text(raw_language.get("name"), limit=100),
                        }
                    )
            items.append(
                {
                    "modelId": model_id,
                    "name": self._safe_text(raw_model.get("name"), limit=200),
                    "canDoTextToSpeech": self._safe_bool(
                        raw_model.get("can_do_text_to_speech")
                    ),
                    "canDoVoiceConversion": self._safe_bool(
                        raw_model.get("can_do_voice_conversion")
                    ),
                    "maxCharactersRequest": self._safe_int(
                        raw_model.get("max_characters_request")
                    ),
                    "languages": languages,
                }
            )
        return {"provider": PROVIDER_NAME, "items": items}

    def capabilities(self, *, include_remote: bool = False) -> dict[str, Any]:
        preset_contract = {
            name: {
                "modelId": preset.model_id,
                "outputFormat": preset.output_format,
                "supportsAudioTags": preset.supports_audio_tags,
                "description": preset.description,
            }
            for name, preset in VOICE_PRESETS.items()
        }
        default_spec = VOICE_PRESETS[self.default_preset]
        result: dict[str, Any] = {
            "provider": PROVIDER_NAME,
            "isConfigured": bool(self._api_key),
            "operations": [
                "textToSpeech",
                "listVoices",
                "readSubscription",
                "listModels",
            ],
            "defaultPreset": self.default_preset,
            "defaultModelId": self.default_model_id or default_spec.model_id,
            "defaultOutputFormat": self.default_output_format
            or default_spec.output_format,
            "presets": preset_contract,
            "performance": {
                "directions": list(PERFORMANCE_DIRECTIONS),
                "audioTags": sorted(ALLOWED_AUDIO_TAGS),
            },
            "limits": {
                "maxTextCharacters": self.max_text_characters,
                "maxAudioBytes": self.max_audio_bytes,
            },
        }
        if include_remote:
            result["models"] = self.list_models()["items"]
            result["subscription"] = self.get_subscription()
        return result

    @staticmethod
    def _expected_audio_types(output_format: str) -> frozenset[str]:
        if output_format.startswith("mp3_"):
            return frozenset({"audio/mpeg", "audio/mp3", "application/octet-stream"})
        if output_format.startswith("wav_"):
            return frozenset(
                {"audio/wav", "audio/wave", "audio/x-wav", "application/octet-stream"}
            )
        if output_format.startswith("opus_"):
            return frozenset(
                {"audio/ogg", "audio/opus", "application/ogg", "application/octet-stream"}
            )
        return frozenset({"audio/pcm", "audio/basic", "application/octet-stream"})

    def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        preset: str | None = None,
        model_id: str | None = None,
        output_format: str | None = None,
        language_code: str | None = None,
        direction: str = "neutral",
        audio_tags: Sequence[str] | None = None,
        voice_settings: VoiceSettings | None = None,
    ) -> SynthesisResult:
        preset_name = preset or self.default_preset
        if preset_name not in VOICE_PRESETS:
            raise _validation_error(
                "Preset de voz não reconhecido.",
                field="preset",
                code="UNSUPPORTED_PRESET",
            )
        preset_spec = VOICE_PRESETS[preset_name]
        effective_voice_id = self._validate_voice_id(voice_id)
        effective_model_id = self._validate_model_id(
            model_id or self.default_model_id or preset_spec.model_id
        )
        effective_output_format = self._validate_output_format(
            output_format or self.default_output_format or preset_spec.output_format
        )
        effective_language_code = self._validate_language_code(language_code)

        rendered_text, effective_tags = render_performance_text(
            text,
            direction=direction,
            audio_tags=audio_tags,
            max_characters=self.max_text_characters,
        )
        model_supports_tags = effective_model_id.startswith("eleven_v3")
        if effective_tags and not model_supports_tags:
            raise _validation_error(
                "Tags de áudio exigem um modelo Eleven v3.",
                field="audioTags",
                code="AUDIO_TAGS_UNSUPPORTED_BY_MODEL",
            )

        explicit_settings = voice_settings is not None
        settings = voice_settings if explicit_settings else preset_spec.voice_settings
        if settings is not None and not isinstance(settings, VoiceSettings):
            raise _validation_error(
                "voiceSettings deve usar o contrato VoiceSettings.",
                field="voiceSettings",
            )
        if model_supports_tags:
            if explicit_settings:
                raise _validation_error(
                    "Eleven v3 não aceita este conjunto de voiceSettings.",
                    field="voiceSettings",
                    code="VOICE_SETTINGS_UNSUPPORTED_BY_MODEL",
                )
            settings = None

        request_payload: dict[str, Any] = {
            "text": rendered_text,
            "model_id": effective_model_id,
        }
        if effective_language_code is not None:
            request_payload["language_code"] = effective_language_code
        settings_payload = settings.provider_payload() if settings is not None else None
        if settings_payload is not None:
            request_payload["voice_settings"] = settings_payload

        cache_key = deterministic_cache_key(
            text=rendered_text,
            voice_id=effective_voice_id,
            model_id=effective_model_id,
            output_format=effective_output_format,
            voice_settings=settings_payload,
            language_code=effective_language_code,
        )
        result = self._request(
            method="POST",
            path=f"/v1/text-to-speech/{urllib.parse.quote(effective_voice_id, safe='')}",
            query={
                "output_format": effective_output_format,
                "enable_logging": str(self.enable_logging).lower(),
            },
            json_body=request_payload,
            accept="audio/*",
            max_bytes=self.max_audio_bytes,
        )

        media_type = result.content_type.partition(";")[0].strip().lower()
        if media_type not in self._expected_audio_types(effective_output_format):
            raise VoiceProviderError(
                "INVALID_PROVIDER_CONTENT_TYPE",
                "O provedor retornou um tipo de áudio inesperado.",
            )
        if len(result.body) < 16:
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor retornou áudio vazio ou incompleto.",
            )
        prefix = result.body[:64].lstrip().lower()
        if prefix.startswith((b"{", b"[", b"<html", b"<!doctype")):
            raise VoiceProviderError(
                "INVALID_PROVIDER_RESPONSE",
                "O provedor não retornou um arquivo de áudio válido.",
            )

        metadata: dict[str, Any] = {
            "provider": PROVIDER_NAME,
            "preset": preset_name,
            "modelId": effective_model_id,
            "voiceId": effective_voice_id,
            "outputFormat": effective_output_format,
            "contentType": media_type,
            "byteLength": len(result.body),
            "characterCount": len(rendered_text),
            "cacheKey": cache_key,
            "performance": {
                "direction": direction,
                "audioTags": list(effective_tags),
            },
        }
        if effective_language_code is not None:
            metadata["languageCode"] = effective_language_code
        if result.request_id is not None:
            metadata["requestId"] = result.request_id
        return SynthesisResult(
            audio_bytes=result.body,
            metadata=MappingProxyType(metadata),
        )


__all__ = [
    "ALLOWED_AUDIO_TAGS",
    "ElevenLabsVoiceProvider",
    "PERFORMANCE_DIRECTIONS",
    "PROVIDER_NAME",
    "SynthesisResult",
    "VOICE_PRESETS",
    "VoicePreset",
    "VoiceProviderError",
    "VoiceSettings",
    "chatterbox_expression_settings",
    "deterministic_cache_key",
    "render_performance_text",
    "resolve_chatterbox_settings",
]
