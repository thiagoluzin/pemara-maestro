"""Pacote seguro de interoperabilidade para o editor local CapCut Local/LLM.

Este modulo nao acessa nem automatiza o produto oficial CapCut. Ele transforma
somente os assets referenciados por um projeto do Maestro em um ZIP portavel,
com um manifesto minimo e verificacao SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Sequence


SCHEMA_NAME = "pemara.capcut-local-llm-handoff"
SCHEMA_VERSION = 1
HANDOFF_MODES = {"quick", "editable"}

VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"})
AUDIO_SUFFIXES = frozenset(
    {".wav", ".mp3", ".aac", ".flac", ".wma", ".m4a", ".ogg", ".opus"}
)
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})

_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_ARCHIVE_DIRECTORIES = (
    "00_reference/",
    "01_video/",
    "02_audio/",
    "03_images/",
    "04_captions/",
)
_TRACK_ORDER = {"video": 0, "voice": 1, "music": 2, "sfx": 3, "text": 4, "caption": 4}
_SENSITIVE_TOKENS = frozenset(
    {
        "apikey",
        "api-key",
        "api_key",
        "credential",
        "credentials",
        "private-key",
        "private_key",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
)


class CapCutHandoffError(ValueError):
    """Erro de contrato/seguranca ao montar o pacote local."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class HandoffLimits:
    """Limites conservadores para impedir pacotes acidentais ou abusivos."""

    max_files: int = 512
    max_file_bytes: int = 8 * 1024 * 1024 * 1024
    max_total_bytes: int = 20 * 1024 * 1024 * 1024
    max_caption_cues: int = 10_000
    max_caption_chars_per_cue: int = 4_000
    max_timeline_seconds: float = 86_400.0

    def __post_init__(self) -> None:
        integer_fields = (
            self.max_files,
            self.max_file_bytes,
            self.max_total_bytes,
            self.max_caption_cues,
            self.max_caption_chars_per_cue,
        )
        if any(value <= 0 for value in integer_fields) or self.max_timeline_seconds <= 0:
            raise ValueError("Todos os limites do handoff devem ser positivos.")


@dataclass(frozen=True)
class CapCutHandoffResult:
    """Resultado serializavel da criacao do handoff."""

    path: Path
    mode: str
    package_sha256: str
    package_size: int
    file_count: int
    source_bytes: int
    manifest: Mapping[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "mode": self.mode,
            "packageSha256": self.package_sha256,
            "packageSize": self.package_size,
            "fileCount": self.file_count,
            "sourceBytes": self.source_bytes,
            "manifest": dict(self.manifest),
        }


@dataclass
class _PlannedFile:
    source: Path
    archive_path: str
    role: str
    size: int
    asset_id: Optional[str] = None
    export_id: Optional[str] = None
    source_name: str = ""
    clips: List[Dict[str, Any]] = field(default_factory=list)
    sha256: str = ""


def create_capcut_local_handoff(
    project: Mapping[str, Any],
    project_dir: os.PathLike[str] | str,
    output_path: os.PathLike[str] | str,
    *,
    mode: Literal["quick", "editable"] = "editable",
    limits: Optional[HandoffLimits] = None,
    overwrite: bool = False,
) -> CapCutHandoffResult:
    """Cria um ZIP deterministico para o editor local CapCut Local/LLM.

    ``quick`` leva o ultimo MP4 exportado (quando houver), voz e legendas.
    ``editable`` acrescenta clipes de video, imagens, musica e efeitos.

    Nenhum arquivo e descoberto por varredura de diretorio. Somente o ultimo
    export explicitamente registrado e assets explicitamente referenciados por
    clipes elegiveis podem entrar no pacote.
    """

    if not isinstance(project, Mapping):
        raise CapCutHandoffError("INVALID_PROJECT", "O projeto deve ser um objeto.")
    mode = str(mode).strip().lower()
    if mode not in HANDOFF_MODES:
        raise CapCutHandoffError(
            "INVALID_MODE",
            "Use o modo quick ou editable.",
            details={"mode": mode},
        )
    effective_limits = limits or HandoffLimits()
    root = _resolve_project_root(project_dir)
    target = Path(output_path)
    if target.suffix.lower() != ".zip":
        raise CapCutHandoffError(
            "INVALID_OUTPUT",
            "O pacote de interoperabilidade deve terminar em .zip.",
        )
    if target.exists() and not overwrite:
        raise CapCutHandoffError(
            "OUTPUT_EXISTS",
            "O arquivo de saida ja existe.",
            details={"path": str(target)},
        )
    if target.exists() and not target.is_file():
        raise CapCutHandoffError("INVALID_OUTPUT", "O destino nao e um arquivo.")

    plan = _plan_files(project, root, mode, effective_limits)
    captions = _build_srt(project, effective_limits)
    source_bytes = sum(item.size for item in plan)
    if captions:
        source_bytes += len(captions)
    if source_bytes > effective_limits.max_total_bytes:
        raise CapCutHandoffError(
            "PACKAGE_TOO_LARGE",
            "O pacote excede o limite total configurado.",
            details={
                "actualBytes": source_bytes,
                "maxBytes": effective_limits.max_total_bytes,
            },
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}.",
        suffix=".partial.zip",
        dir=str(target.parent),
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    manifest: Dict[str, Any] = {}
    regular_hashes: Dict[str, str] = {}
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
            strict_timestamps=True,
        ) as archive:
            for directory in _ARCHIVE_DIRECTORIES:
                _write_directory(archive, directory)

            for item in sorted(plan, key=lambda entry: entry.archive_path):
                digest, written = _write_source_file(archive, item, root)
                if written != item.size:
                    raise CapCutHandoffError(
                        "SOURCE_CHANGED",
                        "Um asset mudou enquanto o pacote era criado.",
                        details={"path": item.archive_path},
                    )
                item.sha256 = digest
                regular_hashes[item.archive_path] = digest

            caption_path = ""
            caption_count = _caption_count(project)
            if captions:
                caption_path = "04_captions/pt-BR.srt"
                _write_bytes(archive, caption_path, captions)
                regular_hashes[caption_path] = _sha256_bytes(captions)

            manifest = _make_manifest(
                project,
                plan,
                mode,
                caption_path,
                caption_count,
                source_bytes,
                effective_limits,
            )
            manifest_bytes = _json_bytes(manifest)
            _write_bytes(archive, "manifest.json", manifest_bytes)
            regular_hashes["manifest.json"] = _sha256_bytes(manifest_bytes)

            instructions = _instructions_bytes(mode, plan, caption_count)
            _write_bytes(archive, "IMPORTAR_NO_CAPCUT_LOCAL.md", instructions)
            regular_hashes["IMPORTAR_NO_CAPCUT_LOCAL.md"] = _sha256_bytes(instructions)

            checksum_bytes = _checksum_bytes(regular_hashes)
            _write_bytes(archive, "SHA256SUMS", checksum_bytes)

        if target.exists() and not overwrite:
            raise CapCutHandoffError(
                "OUTPUT_EXISTS",
                "O arquivo de saida passou a existir durante a criacao.",
                details={"path": str(target)},
            )
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return CapCutHandoffResult(
        path=target,
        mode=mode,
        package_sha256=_sha256_file(target),
        package_size=target.stat().st_size,
        file_count=len(plan) + (1 if captions else 0),
        source_bytes=source_bytes,
        manifest=manifest,
    )


def _resolve_project_root(project_dir: os.PathLike[str] | str) -> Path:
    try:
        root = Path(project_dir).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CapCutHandoffError(
            "PROJECT_DIR_NOT_FOUND",
            "A pasta do projeto nao existe.",
        ) from exc
    if not root.is_dir():
        raise CapCutHandoffError("INVALID_PROJECT_DIR", "A raiz do projeto nao e uma pasta.")
    return root


def _plan_files(
    project: Mapping[str, Any],
    root: Path,
    mode: str,
    limits: HandoffLimits,
) -> List[_PlannedFile]:
    plan: List[_PlannedFile] = []
    latest_export = _latest_mp4_export(project)
    if latest_export is not None:
        source, size = _validate_source(
            root,
            latest_export.get("relativePath"),
            VIDEO_SUFFIXES,
            limits,
            expected_suffix=".mp4",
        )
        plan.append(
            _PlannedFile(
                source=source,
                archive_path="00_reference/final-reference.mp4",
                role="reference",
                size=size,
                export_id=_safe_identifier(latest_export.get("exportId"), "exportId"),
                source_name=_safe_display_name(source.name, fallback="final-reference.mp4"),
            )
        )

    assets = _asset_index(project)
    eligible_tracks = {"voice"} if mode == "quick" else {"video", "voice", "music", "sfx"}
    grouped: Dict[tuple[str, str], Dict[str, Any]] = {}
    for clip in sorted(_iter_clips(project), key=_clip_sort_key):
        track = str(clip.get("track") or "").strip().lower()
        if track not in eligible_tracks:
            continue
        asset_id = _safe_identifier(clip.get("assetId"), "assetId")
        if not asset_id or asset_id not in assets:
            raise CapCutHandoffError(
                "ASSET_NOT_FOUND",
                "Um clipe referencia um asset ausente.",
                details={"assetId": asset_id, "track": track},
            )
        asset = assets[asset_id]
        role, allowed = _role_and_suffixes(track, asset)
        key = (role, asset_id)
        if key not in grouped:
            grouped[key] = {"asset": asset, "track": track, "clips": []}
        grouped[key]["clips"].append(_clip_manifest_entry(clip, limits))

    counters: Dict[str, int] = {}
    used_archive_paths = {entry.archive_path for entry in plan}
    grouped_items = sorted(
        grouped.items(),
        key=lambda item: (
            _TRACK_ORDER.get(item[1]["track"], 99),
            item[1]["clips"][0].get("timelineStart", 0.0),
            item[0][1],
        ),
    )
    for (role, asset_id), item in grouped_items:
        asset = item["asset"]
        _role, allowed = _role_and_suffixes(item["track"], asset)
        source, size = _validate_source(
            root,
            asset.get("relativePath"),
            allowed,
            limits,
        )
        counters[role] = counters.get(role, 0) + 1
        archive_path = _media_archive_path(
            role,
            counters[role],
            asset_id,
            source.name,
            source.suffix.lower(),
        )
        if archive_path in used_archive_paths:
            raise CapCutHandoffError(
                "ARCHIVE_NAME_COLLISION",
                "Dois assets produziram o mesmo nome no pacote.",
                details={"path": archive_path},
            )
        used_archive_paths.add(archive_path)
        plan.append(
            _PlannedFile(
                source=source,
                archive_path=archive_path,
                role=role,
                size=size,
                asset_id=asset_id,
                source_name=_safe_display_name(source.name),
                clips=item["clips"],
            )
        )

    if len(plan) > limits.max_files:
        raise CapCutHandoffError(
            "TOO_MANY_FILES",
            "O projeto excede o limite de arquivos do handoff.",
            details={"actual": len(plan), "max": limits.max_files},
        )
    total = sum(item.size for item in plan)
    if total > limits.max_total_bytes:
        raise CapCutHandoffError(
            "PACKAGE_TOO_LARGE",
            "Os assets excedem o limite total configurado.",
            details={"actualBytes": total, "maxBytes": limits.max_total_bytes},
        )
    return plan


def _latest_mp4_export(project: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    exports = project.get("exports")
    if not isinstance(exports, Sequence) or isinstance(exports, (str, bytes, bytearray)):
        return None
    candidates: List[tuple[str, int, Mapping[str, Any]]] = []
    for index, item in enumerate(exports):
        if not isinstance(item, Mapping):
            continue
        relative = str(item.get("relativePath") or "")
        if _portable_suffix(relative) != ".mp4":
            continue
        created_at = str(item.get("createdAt") or "")[:80]
        candidates.append((created_at, -index, item))
    if not candidates:
        return None
    return max(candidates, key=lambda entry: (entry[0], entry[1]))[2]


def _asset_index(project: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    raw_assets = project.get("assets")
    if not isinstance(raw_assets, Sequence) or isinstance(
        raw_assets, (str, bytes, bytearray)
    ):
        return {}
    result: Dict[str, Mapping[str, Any]] = {}
    for raw in raw_assets:
        if not isinstance(raw, Mapping):
            continue
        asset_id = _safe_identifier(raw.get("assetId"), "assetId")
        if not asset_id:
            continue
        if asset_id in result:
            raise CapCutHandoffError(
                "DUPLICATE_ASSET_ID",
                "O projeto possui IDs de asset duplicados.",
                details={"assetId": asset_id},
            )
        result[asset_id] = raw
    return result


def _iter_clips(project: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    clips = project.get("clips")
    if not isinstance(clips, Sequence) or isinstance(clips, (str, bytes, bytearray)):
        return ()
    return (clip for clip in clips if isinstance(clip, Mapping))


def _clip_sort_key(clip: Mapping[str, Any]) -> tuple[Any, ...]:
    track = str(clip.get("track") or "").strip().lower()
    return (
        _TRACK_ORDER.get(track, 99),
        _safe_float(clip.get("timelineStart"), 0.0),
        _safe_int(clip.get("order"), 0),
        str(clip.get("clipId") or ""),
    )


def _role_and_suffixes(
    track: str,
    asset: Mapping[str, Any],
) -> tuple[str, frozenset[str]]:
    if track == "video":
        declared = str(asset.get("kind") or "").strip().lower()
        suffix = _portable_suffix(str(asset.get("relativePath") or ""))
        if declared == "image" or suffix in IMAGE_SUFFIXES:
            return "image", IMAGE_SUFFIXES
        return "video", VIDEO_SUFFIXES
    if track in {"voice", "music", "sfx"}:
        return track, AUDIO_SUFFIXES
    raise CapCutHandoffError(
        "INVALID_TRACK",
        "A trilha nao e exportavel para o handoff.",
        details={"track": track},
    )


def _validate_source(
    root: Path,
    relative_value: Any,
    allowed_suffixes: frozenset[str],
    limits: HandoffLimits,
    *,
    expected_suffix: Optional[str] = None,
) -> tuple[Path, int]:
    parts = _safe_relative_parts(relative_value)
    _reject_sensitive_path(parts)
    raw_path = root.joinpath(*parts)
    current = root
    try:
        for part in parts:
            current = current / part
            metadata = os.lstat(current)
            attributes = int(getattr(metadata, "st_file_attributes", 0))
            is_reparse_point = bool(attributes & 0x400)
            if stat.S_ISLNK(metadata.st_mode) or is_reparse_point:
                raise CapCutHandoffError(
                    "SYMLINK_FORBIDDEN",
                    "Links simbolicos e pontos de nova analise nao entram no pacote.",
                    details={"relativePath": "/".join(parts)},
                )
        resolved = raw_path.resolve(strict=True)
    except CapCutHandoffError:
        raise
    except (OSError, RuntimeError) as exc:
        raise CapCutHandoffError(
            "SOURCE_NOT_FOUND",
            "Um asset referenciado nao foi encontrado.",
            details={"relativePath": "/".join(parts)},
        ) from exc
    if resolved != root and root not in resolved.parents:
        raise CapCutHandoffError(
            "PATH_OUTSIDE_PROJECT",
            "Um asset aponta para fora da pasta do projeto.",
            details={"relativePath": "/".join(parts)},
        )
    try:
        metadata = resolved.stat()
    except OSError as exc:
        raise CapCutHandoffError(
            "SOURCE_NOT_FOUND",
            "Um asset referenciado nao esta acessivel.",
        ) from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise CapCutHandoffError("SOURCE_NOT_FILE", "O asset referenciado nao e um arquivo.")
    suffix = resolved.suffix.lower()
    if expected_suffix and suffix != expected_suffix:
        raise CapCutHandoffError(
            "UNSUPPORTED_FORMAT",
            "A referencia final precisa ser um MP4.",
            details={"suffix": suffix},
        )
    if suffix not in allowed_suffixes:
        raise CapCutHandoffError(
            "UNSUPPORTED_FORMAT",
            "O formato do asset nao e aceito no handoff.",
            details={"suffix": suffix, "allowed": sorted(allowed_suffixes)},
        )
    size = int(metadata.st_size)
    if size <= 0:
        raise CapCutHandoffError("EMPTY_ASSET", "Assets vazios nao entram no handoff.")
    if size > limits.max_file_bytes:
        raise CapCutHandoffError(
            "FILE_TOO_LARGE",
            "Um asset excede o limite individual configurado.",
            details={"actualBytes": size, "maxBytes": limits.max_file_bytes},
        )
    return resolved, size


def _safe_relative_parts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise CapCutHandoffError("INVALID_SOURCE_PATH", "O asset nao possui caminho relativo.")
    raw = value.strip()
    if not raw or "\x00" in raw or len(raw) > 1_024:
        raise CapCutHandoffError("INVALID_SOURCE_PATH", "O caminho do asset e invalido.")
    windows = PureWindowsPath(raw)
    posix = PurePosixPath(raw)
    if windows.is_absolute() or windows.drive or posix.is_absolute():
        raise CapCutHandoffError(
            "ABSOLUTE_PATH_FORBIDDEN",
            "Caminhos absolutos nao entram no handoff.",
        )
    normalized = raw.replace("\\", "/")
    parts = tuple(part for part in normalized.split("/") if part not in {"", "."})
    if not parts or any(part == ".." for part in parts):
        raise CapCutHandoffError(
            "PATH_TRAVERSAL",
            "O caminho do asset tenta sair da pasta do projeto.",
        )
    if any(len(part) > 255 for part in parts):
        raise CapCutHandoffError("INVALID_SOURCE_PATH", "O caminho do asset e muito longo.")
    return parts


def _reject_sensitive_path(parts: Sequence[str]) -> None:
    lowered = [part.casefold() for part in parts]
    joined = "/".join(lowered)
    for part in lowered:
        if part == ".env" or part.startswith(".env."):
            raise CapCutHandoffError(
                "SENSITIVE_SOURCE_FORBIDDEN",
                "Arquivos de ambiente nunca entram no handoff.",
            )
        if part in {".git", "__pycache__", "node_modules"}:
            raise CapCutHandoffError(
                "SENSITIVE_SOURCE_FORBIDDEN",
                "Pastas de codigo e configuracao nao entram no handoff.",
            )
        tokens = {token for token in re.split(r"[^a-z0-9_-]+", part) if token}
        if tokens & _SENSITIVE_TOKENS:
            raise CapCutHandoffError(
                "SENSITIVE_SOURCE_FORBIDDEN",
                "Um caminho com indicio de segredo foi bloqueado.",
            )
    if "prompt_history" in joined or "migrated_prompt_history" in joined:
        raise CapCutHandoffError(
            "PROMPT_HISTORY_FORBIDDEN",
            "Historicos de prompts nunca entram no handoff.",
        )


def _safe_identifier(value: Any, field_name: str) -> str:
    if value is None or value == "":
        return ""
    text = str(value).strip()
    if len(text) > 128 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", text):
        raise CapCutHandoffError(
            "INVALID_IDENTIFIER",
            f"O campo {field_name} e invalido.",
        )
    return text


def _safe_display_name(value: Any, fallback: str = "asset") -> str:
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    text = "".join(char for char in text if char >= " " and char != "\x7f")
    return text[:180] or fallback


def _slug_stem(value: Any) -> str:
    display = _safe_display_name(value)
    stem = Path(display).stem
    folded = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", folded).strip("-").lower()
    return (slug[:64] or "asset").rstrip("-")


def _media_archive_path(
    role: str,
    index: int,
    asset_id: str,
    source_name: Any,
    suffix: str,
) -> str:
    folder = {
        "video": "01_video",
        "voice": "02_audio",
        "music": "02_audio",
        "sfx": "02_audio",
        "image": "03_images",
    }[role]
    id_fragment = re.sub(r"[^A-Za-z0-9]", "", asset_id)[:10].lower() or "asset"
    return (
        f"{folder}/{role}_{index:03d}_{id_fragment}_"
        f"{_slug_stem(source_name)}{suffix.lower()}"
    )


def _clip_manifest_entry(
    clip: Mapping[str, Any],
    limits: HandoffLimits,
) -> Dict[str, Any]:
    start = _bounded_time(clip.get("timelineStart"), 0.0, limits)
    duration = _bounded_time(clip.get("duration"), 0.0, limits)
    source_start = _bounded_time(clip.get("sourceStart"), 0.0, limits)
    source_end = _bounded_time(
        clip.get("sourceEnd"),
        source_start + max(0.0, duration),
        limits,
    )
    result: Dict[str, Any] = {
        "timelineStart": start,
        "duration": duration,
        "sourceStart": source_start,
        "sourceEnd": source_end,
        "volume": round(max(0.0, min(4.0, _safe_float(clip.get("volume"), 1.0))), 4),
        "muted": bool(clip.get("muted", False)),
        "order": max(0, _safe_int(clip.get("order"), 0)),
    }
    clip_id = _safe_identifier(clip.get("clipId"), "clipId")
    if clip_id:
        result["clipId"] = clip_id
    return result


def _bounded_time(value: Any, default: float, limits: HandoffLimits) -> float:
    number = _safe_float(value, default)
    if number < 0 or number > limits.max_timeline_seconds:
        raise CapCutHandoffError(
            "INVALID_TIMELINE",
            "Um valor da timeline esta fora do limite.",
            details={"value": number, "max": limits.max_timeline_seconds},
        )
    return round(number, 6)


def _build_srt(project: Mapping[str, Any], limits: HandoffLimits) -> bytes:
    cues: List[tuple[float, float, str, str]] = []
    for clip in _iter_clips(project):
        track = str(clip.get("track") or "").strip().lower()
        if track not in {"text", "caption"}:
            continue
        text = _clean_text(clip.get("text"), limits.max_caption_chars_per_cue)
        if not text:
            continue
        start = _bounded_time(clip.get("timelineStart"), 0.0, limits)
        duration = _safe_float(clip.get("duration"), 0.0)
        if duration <= 0:
            source_start = _safe_float(clip.get("sourceStart"), 0.0)
            source_end = _safe_float(clip.get("sourceEnd"), 0.0)
            duration = source_end - source_start
        if duration <= 0:
            raise CapCutHandoffError(
                "INVALID_CAPTION",
                "Uma legenda nao possui duracao positiva.",
            )
        end = start + duration
        if end > limits.max_timeline_seconds:
            raise CapCutHandoffError(
                "INVALID_CAPTION",
                "Uma legenda ultrapassa o limite da timeline.",
            )
        clip_id = _safe_identifier(clip.get("clipId"), "clipId")
        cues.append((start, end, clip_id, text))
    cues.sort(key=lambda cue: (cue[0], cue[1], cue[2], cue[3]))
    if len(cues) > limits.max_caption_cues:
        raise CapCutHandoffError(
            "TOO_MANY_CAPTIONS",
            "O projeto excede o limite de legendas.",
            details={"actual": len(cues), "max": limits.max_caption_cues},
        )
    if not cues:
        return b""
    blocks = []
    for index, (start, end, _clip_id, text) in enumerate(cues, start=1):
        blocks.append(
            f"{index}\r\n{_srt_time(start)} --> {_srt_time(end)}\r\n"
            f"{text.replace(chr(10), chr(13) + chr(10))}\r\n"
        )
    return ("\r\n".join(blocks)).encode("utf-8")


def _caption_count(project: Mapping[str, Any]) -> int:
    count = 0
    for clip in _iter_clips(project):
        if str(clip.get("track") or "").strip().lower() in {"text", "caption"}:
            if _clean_text(clip.get("text"), 4_000):
                count += 1
    return count


def _clean_text(value: Any, max_length: int) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(char for char in text if char in {"\n", "\t"} or char >= " ")
    text = "\n".join(line.strip() for line in text.split("\n")).strip()
    if len(text) > max_length:
        raise CapCutHandoffError(
            "TEXT_TOO_LONG",
            "Um texto excede o limite configurado.",
            details={"actual": len(text), "max": max_length},
        )
    return text


def _srt_time(seconds: float) -> str:
    milliseconds = int((max(0.0, seconds) * 1000.0) + 0.5)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def _make_manifest(
    project: Mapping[str, Any],
    plan: Sequence[_PlannedFile],
    mode: str,
    caption_path: str,
    caption_count: int,
    source_bytes: int,
    limits: HandoffLimits,
) -> Dict[str, Any]:
    reference: Optional[Dict[str, Any]] = None
    media: List[Dict[str, Any]] = []
    for item in sorted(plan, key=lambda entry: entry.archive_path):
        base = {
            "path": item.archive_path,
            "sha256": item.sha256,
            "size": item.size,
            "sourceName": item.source_name,
        }
        if item.role == "reference":
            reference = {
                **base,
                "exportId": item.export_id or None,
            }
        else:
            media.append(
                {
                    **base,
                    "assetId": item.asset_id,
                    "role": item.role,
                    "clips": item.clips,
                }
            )
    settings = project.get("settings")
    safe_settings: Dict[str, Any] = {}
    if isinstance(settings, Mapping):
        for key in ("width", "height", "fps", "sampleRate"):
            value = settings.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                safe_settings[key] = value
    return {
        "schema": SCHEMA_NAME,
        "schemaVersion": SCHEMA_VERSION,
        "target": {
            "name": "CapCut Local/LLM",
            "type": "local-llm-video-editor",
            "officialServiceAutomation": False,
        },
        "llm": {
            "provider": "ollama",
            "endpoint": "loopback-only",
            "contract": "reviewed-timeline-actions",
            "requiresHumanApproval": True,
            "canStartCloudVoice": False,
        },
        "mode": mode,
        "project": {
            "projectId": _safe_identifier(project.get("projectId"), "projectId") or None,
            "name": _clean_text(project.get("name"), 120) or "Projeto",
            "revision": max(0, _safe_int(project.get("revision"), 0)),
            "settings": safe_settings,
        },
        "reference": reference,
        "media": media,
        "captions": {
            "path": caption_path or None,
            "format": "srt" if caption_path else None,
            "encoding": "utf-8" if caption_path else None,
            "language": "pt-BR" if caption_path else None,
            "cueCount": caption_count,
        },
        "summary": {
            "mediaFileCount": len(media),
            "hasReference": reference is not None,
            "sourceBytes": source_bytes,
        },
        "integrity": {
            "algorithm": "sha256",
            "checksumFile": "SHA256SUMS",
            "coverage": "all regular entries except SHA256SUMS",
        },
        "limitsApplied": {
            "maxFiles": limits.max_files,
            "maxFileBytes": limits.max_file_bytes,
            "maxTotalBytes": limits.max_total_bytes,
            "maxCaptionCues": limits.max_caption_cues,
            "maxCaptionCharsPerCue": limits.max_caption_chars_per_cue,
            "maxTimelineSeconds": limits.max_timeline_seconds,
        },
    }


def _instructions_bytes(
    mode: str,
    plan: Sequence[_PlannedFile],
    caption_count: int,
) -> bytes:
    has_reference = any(item.role == "reference" for item in plan)
    media_count = sum(1 for item in plan if item.role != "reference")
    text = f"""# Importar no CapCut Local/LLM

Este e um pacote de interoperabilidade de arquivos para o editor local com LLM
chamado **CapCut Local/LLM**. Ele nao acessa, controla nem automatiza o produto
ou servico oficial CapCut.

Modo do pacote: `{mode}`

1. Confira a integridade com `SHA256SUMS`.
2. Use `00_reference/final-reference.mp4` como referencia visual, quando presente.
3. Importe videos de `01_video`, audios de `02_audio` e imagens de `03_images`.
4. Importe `04_captions/pt-BR.srt` como legenda UTF-8, quando presente.
5. Consulte `manifest.json` para tempos, cortes, volumes, papeis e IDs dos assets.

Resumo: referencia={"sim" if has_reference else "nao"}; assets={media_count};
legendas={caption_count}.

O pacote nao contem projeto proprietario, credenciais, historico de prompts,
codigo ou arquivos descobertos por varredura. A montagem da timeline permanece
uma acao local e explicita.
"""
    return text.replace("\r\n", "\n").encode("utf-8")


def _write_directory(archive: zipfile.ZipFile, name: str) -> None:
    info = _zip_info(name, directory=True)
    archive.writestr(info, b"")


def _write_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = _zip_info(name)
    archive.writestr(info, payload)


def _write_source_file(
    archive: zipfile.ZipFile,
    item: _PlannedFile,
    root: Path,
) -> tuple[str, int]:
    if item.source != root and root not in item.source.parents:
        raise CapCutHandoffError(
            "PATH_OUTSIDE_PROJECT",
            "Um asset resolveu para fora da pasta do projeto.",
        )
    if item.source.is_symlink():
        raise CapCutHandoffError("SYMLINK_FORBIDDEN", "Links simbolicos nao entram no pacote.")
    digest = hashlib.sha256()
    written = 0
    info = _zip_info(item.archive_path)
    try:
        with item.source.open("rb") as source, archive.open(
            info,
            mode="w",
            force_zip64=True,
        ) as destination:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise CapCutHandoffError(
                    "SOURCE_NOT_FILE",
                    "O asset referenciado nao e um arquivo regular.",
                )
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                destination.write(chunk)
                digest.update(chunk)
                written += len(chunk)
    except CapCutHandoffError:
        raise
    except OSError as exc:
        raise CapCutHandoffError(
            "SOURCE_READ_FAILED",
            "Nao foi possivel ler um asset referenciado.",
            details={"path": item.archive_path},
        ) from exc
    return digest.hexdigest(), written


def _zip_info(name: str, *, directory: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED if directory else zipfile.ZIP_DEFLATED
    if directory:
        info.external_attr = (0o40755 << 16) | 0x10
    else:
        info.external_attr = 0o100644 << 16
    return info


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _checksum_bytes(hashes: Mapping[str, str]) -> bytes:
    return "".join(f"{hashes[name]}  {name}\n" for name in sorted(hashes)).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _portable_suffix(value: str) -> str:
    leaf = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    return Path(leaf).suffix.lower()


def _safe_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if number != number or number in {float("inf"), float("-inf")}:
        return float(default)
    return number


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return int(default)


__all__ = [
    "AUDIO_SUFFIXES",
    "CapCutHandoffError",
    "CapCutHandoffResult",
    "HANDOFF_MODES",
    "HandoffLimits",
    "IMAGE_SUFFIXES",
    "SCHEMA_NAME",
    "SCHEMA_VERSION",
    "VIDEO_SUFFIXES",
    "create_capcut_local_handoff",
]
