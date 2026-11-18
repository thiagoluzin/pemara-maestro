"""Persistencia segura de projetos e takes para a interface do Maestro."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import tempfile
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import internet_publication
from h3_prompt_writing import compile_base_prompt, compile_ref_prompt, detect_base_mode
from h3_workflow import resolve_h3_quality_profile
from review_proxies import review_proxy_info, resolve_review_proxy
from ready_exports import sync_project_ready_exports
from ready_exports_sync import request_ready_exports_sync
from wan_animate_workflow import (
    WAN_ANIMATE_DEFAULT_CFG,
    WAN_ANIMATE_DEFAULT_STEPS,
    WAN22_ANIMATE_PROFILE,
)


PROJECT_DIRS = ("input", "refs", "keyframes", "takes", "edit", "qc", "audio", "output", "logs")
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
TAKE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")
PROJECT_STATUSES = {"PLANNED", "IN_PROGRESS", "PAUSED", "COMPLETED", "ERROR"}
TAKE_STATUSES = {
    "PLANNED", "IN_PRODUCTION", "QUEUED", "GENERATING", "READY", "APPROVED", "REJECTED",
    "UPSCALING", "FINAL", "ERROR",
}
TAKE_MODES = {"PRECISION", "ACTION", "PAYOFF"}
CONTINUITY_FIELD_MAP = {
    "characterTopology": "character_topology",
    "wardrobeLock": "wardrobe_lock",
    "powerState": "power_state",
    "entryMotion": "entry_motion",
    "exitMotion": "exit_motion",
    "impactLanguage": "impact_language",
    "forbiddenTransitions": "forbidden_transitions",
}
DOWNLOADABLE_TAKE_STATUSES = {"READY", "APPROVED", "UPSCALING", "FINAL"}
DIRECTOR_REQUEST_STATUSES = {"PENDING", "IN_PROGRESS", "DELIVERED", "CANCELLED", "SUPERSEDED"}
DIRECTOR_REQUEST_CATEGORIES = {
    "ANCHOR", "CAMERA", "DEPTH", "INTERNAL_ACTION", "MORPHING", "AESTHETIC", "PROGRESSION",
    "AUDIO_SYNC", "AUDIO_VOICE", "OTHER",
}
MAX_ANCHOR_IMAGE_BYTES = 32 * 1024 * 1024
ANCHOR_PENDING_REVIEW_STATUS = "pending_human_qc"
ANCHOR_APPROVED_STATUS = "approved_for_video"
ANCHOR_REJECTED_STATUS = "rejected_human_qc"
ANCHOR_REQUEST_ID_RE = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)
REMOVED_LTX23_GENERATION_PROFILES = frozenset({
    "ltx23_distilled_fp8_720p",
    "ltx23_dev_two_stage_hq_720p",
})
LTX25_TWO_ANCHOR_PROFILE = "ltx25_two_stage_distilled_960x544p24"
MINIMAX_H3_PROFILE = "minimax_h3_fl2va_int8_720p24"
REMOVED_MINIMAX_H3_LEGACY_PROFILE = "minimax_h3_fl2va_int8_ltx_contract_720p24"
MINIMAX_H3_VERTICAL_PROFILE = "minimax_h3_fl2va_int8_vertical_720x1280p24"
MINIMAX_H3_OWNER_30S_NATIVE_AV_PROFILE = (
    "minimax_h3_fl2va_int8_owner_30s_native_av_720p24"
)
MINIMAX_H3_GENERATION_PROFILES = {
    MINIMAX_H3_PROFILE,
    MINIMAX_H3_VERTICAL_PROFILE,
    MINIMAX_H3_OWNER_30S_NATIVE_AV_PROFILE,
}
ENGINE_SELECTION_REQUIRED_PROFILE = "owner_selection_required"

_QUEUE_MUTATION_LOCK = threading.RLock()


class AnchorConflictError(RuntimeError):
    """The requested anchor mutation no longer matches the current take state."""


class AnchorRequestNotFoundError(LookupError):
    """The requested director request does not exist for this take."""


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")[:64]
    if not slug or not PROJECT_ID_RE.fullmatch(slug):
        raise ValueError("Nome nao produz um projectId valido.")
    return slug


def _normalized_words(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def _is_ptpt_voice_rejection(reason: str) -> bool:
    """Recognize an explicit European-Portuguese voice/accent rejection."""

    words = _normalized_words(reason)
    return any(
        marker in words
        for marker in (
            "portugues de portugal",
            "portugues europeu",
            "portuguese de portugal",
            "european portuguese",
            "sotaque de portugal",
            "sotaque portugues",
            "pt pt",
        )
    )


def _director_audio_category(category: str, reason: str) -> str:
    category = str(category or "").strip().upper()
    words = _normalized_words(reason)
    sync_terms = (
        "sincron", "fora de tempo", "nao condiz com o video", "nao combina com o video",
        "boca", "labial", "lip sync", "audio atrasado", "audio adiantado",
        "voz atrasada", "voz adiantada",
    )
    voice_terms = {
        "audio", "som", "voz", "fala", "volume", "sotaque", "pronuncia", "portugal",
    }
    tokens = set(words.split())
    # A locale/accent rejection is a voice failure even when the owner used the
    # AUDIO_SYNC button.  Treating it as timing used to retain native LTX speech
    # and reproduce the exact pt-PT failure on the next render.
    if _is_ptpt_voice_rejection(reason):
        return "AUDIO_VOICE"
    if category == "AUDIO_SYNC" or any(term in words for term in sync_terms):
        return "AUDIO_SYNC"
    audio_token_count = len(tokens & voice_terms)
    if (
        category == "AUDIO_VOICE"
        or (category in {"", "OTHER"} and audio_token_count >= 1)
        or audio_token_count >= 2
    ):
        return "AUDIO_VOICE"
    return category


def _ordered_dialogue_tracks(dialogue_tracks: list[Any]) -> list[dict[str, Any]]:
    """Return only complete dialogue turns, preserving the written turn order."""

    tracks: list[dict[str, Any]] = []
    for item in dialogue_tracks:
        if not isinstance(item, dict):
            continue
        speaker = str(item.get("speaker") or "").strip()
        spoken_text = str(item.get("text") or "").strip()
        if speaker and spoken_text:
            tracks.append(item)
    return tracks


def _dialogue_delivery_text(dialogue_tracks: list[Any]) -> str:
    tracks = _ordered_dialogue_tracks(dialogue_tracks)
    # This value is consumed by ASR and synthesis.  Speaker labels are metadata,
    # not spoken words; including "Mariana:" / "Pedro:" made every multi-turn
    # delivery fail exact-text QC even when the dialogue itself was correct.
    return " ".join(str(item.get("text")).strip() for item in tracks)


def _dialogue_display_text(dialogue_tracks: list[Any]) -> str:
    return "\n".join(
        f"{str(item.get('speaker')).strip()}: {str(item.get('text')).strip()}"
        for item in _ordered_dialogue_tracks(dialogue_tracks)
    )


def _dialogue_speaker_label(dialogue_tracks: list[Any]) -> str:
    return ", ".join(dict.fromkeys(
        str(item.get("speaker")).strip()
        for item in _ordered_dialogue_tracks(dialogue_tracks)
    ))


def _strip_legacy_silent_dialogue_contract(prompt: str) -> str:
    cleaned = str(prompt or "")
    patterns = (
        r"Silent visual-performance pass:[^.]*\.",
        r"Mouths remain naturally closed during the visual pass\.",
        r"Environmental ambience, footsteps and physical action sounds are handled as synchronized sound design after visual approval\.",
        r"Generate no dialogue[^.]*\.",
        r"Dialogue (?:will be|is) (?:created|added|handled)[^.]*\.",
        r"(?:External )?ADR[^.]*\.",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _minimax_h3_native_ptbr_narration_prompt(
    prompt: str,
    narration_tracks: list[Any],
    audio_direction: dict[str, Any],
) -> str:
    """Direct H3's joint AV latent to create one invisible pt-BR narrator."""

    tracks = _ordered_dialogue_tracks(narration_tracks)
    if not tracks:
        raise ValueError("Narracao nativa MiniMax H3 exige o texto pt-BR exato.")
    voice = (
        audio_direction.get("narrator_voice")
        if isinstance(audio_direction.get("narrator_voice"), dict)
        else {}
    )
    gender = str(voice.get("gender") or "male").strip()
    age = str(voice.get("age") or "adult").strip()
    accent = str(voice.get("accent") or "neutral Sao Paulo Brazilian").strip()
    tone = str(voice.get("tone") or "warm, sincere and respectful").strip()
    pace = str(voice.get("pace") or "measured natural pace").strip()
    lines: list[str] = []
    for index, track in enumerate(tracks, start=1):
        spoken_text = str(track.get("text") or "").strip()
        timing = ""
        try:
            start_seconds = float(track.get("start_seconds"))
            end_seconds = float(track.get("end_seconds"))
            if 0 <= start_seconds < end_seconds:
                timing = f" between {start_seconds:.2f} and {end_seconds:.2f} seconds"
        except (TypeError, ValueError):
            pass
        lines.append(
            f'The narrator speaks segment {index}{timing}, saying exactly once: "{spoken_text}". '
            "Do not add, omit, repeat, translate or paraphrase any word."
        )
    cleaned = re.sub(
        r"the emotional message is delivered (?:only )?by (?:the )?(?:native )?invisible "
        r"off-screen narrator[^.]*\.?",
        "",
        str(prompt or ""),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (
        f"{cleaned} Create the picture and its native soundtrack together in one continuous MiniMax H3 "
        "audiovisual generation. The only spoken voice is an invisible off-screen narrator and never comes "
        "from the father or any child. All four visible family members stay silent for the whole video, with "
        "naturally relaxed closed lips, no jaw articulation, no lip sync, no whispering and no singing. Use a "
        "clean close-miked adult narrator voice, centered outside the pictured space: "
        f"gender {gender}; age {age}; accent {accent}; tone {tone}; pace {pace}. The narration language is "
        "Brazilian Portuguese from Brazil with a neutral Sao Paulo accent, never European Portuguese or a "
        "caricatured regional accent. Keep a human, calm, emotionally present delivery, restrained breathing, "
        "medium-low pitch and no booming commercial-announcer style. "
        + " ".join(lines)
        + " Keep natural quiet porch ambience under the voice. Show no subtitles, captions, labels, logos, "
        "watermarks or any other visible text."
    )


def _validate_project_id(project_id: str) -> str:
    project_id = (project_id or "").strip().lower()
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("projectId invalido.")
    return project_id


def _validate_take_id(take_id: str) -> str:
    take_id = (take_id or "").strip()
    if not TAKE_ID_RE.fullmatch(take_id):
        raise ValueError("takeId invalido.")
    return take_id


def _project_path(root: Path, project_id: str) -> Path:
    root = root.resolve()
    candidate = (root / _validate_project_id(project_id)).resolve()
    if candidate.parent != root:
        raise ValueError("projectId fora da raiz permitida.")
    return candidate


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON raiz deve ser objeto: {path.name}")
    return data


def _anchor_visible_cast(
    project_dir: Path,
    keyframe: Path,
    base: dict[str, Any],
    *,
    require_verified: bool = False,
) -> list[str] | None:
    """Read the exact visible cast recorded by the approved image generator.

    ``None`` means that the legacy anchor has no machine-readable cast contract;
    an empty list is a real, explicit contract for a character-free frame.
    """

    project_root = project_dir.resolve()
    metadata_candidates: list[Path] = []
    metadata_raw = str(base.get("metadata") or "").strip()
    if metadata_raw:
        metadata_candidates.append(Path(metadata_raw).resolve())
    metadata_candidates.append(keyframe.with_suffix(".json").resolve())
    seen: set[Path] = set()
    for metadata_path in metadata_candidates:
        if metadata_path in seen:
            continue
        seen.add(metadata_path)
        if not metadata_path.is_relative_to(project_root) or not metadata_path.is_file():
            continue
        metadata = _read_json(metadata_path)
        visual_qc = (
            metadata.get("visual_qc")
            if isinstance(metadata.get("visual_qc"), dict)
            else {}
        )
        if str(visual_qc.get("cast_verification_status") or "").upper() == "VERIFIED":
            actual_characters = visual_qc.get("actual_visible_characters")
            if not isinstance(actual_characters, list):
                raise ValueError(
                    f"QC visual verificado sem elenco visivel valido: {metadata_path.name}"
                )
            return [
                str(item).strip()
                for item in actual_characters
                if str(item).strip()
            ]
        if require_verified:
            # ``required_objects`` describes what the image generator was asked
            # to draw. It is not evidence of what actually reached the pixels.
            # Strict projects must therefore fail closed until a visual review
            # records the cast that is genuinely visible in the approved anchor.
            continue
        required_objects = (
            metadata.get("required_objects")
            if isinstance(metadata.get("required_objects"), dict)
            else {}
        )
        characters = required_objects.get("characters")
        if isinstance(characters, list):
            return [str(item).strip() for item in characters if str(item).strip()]
    return None


def _take_visible_cast_contract(
    take: dict[str, Any],
) -> tuple[bool, list[str], list[str], list[str]]:
    shot = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
    human_visibility = (
        shot.get("human_visibility_contract")
        if isinstance(shot.get("human_visibility_contract"), dict)
        else {}
    )
    contract_known = bool(human_visibility) or "characters" in take
    humans = human_visibility.get("allowed_humans")
    if not isinstance(humans, list):
        humans = take.get("characters")
    if not isinstance(humans, list):
        humans = []
    non_humans = human_visibility.get("allowed_non_humans")
    if not isinstance(non_humans, list):
        human_keys = {str(item).strip().casefold() for item in humans}
        characters = take.get("characters") if isinstance(take.get("characters"), list) else []
        non_humans = [
            item for item in characters
            if str(item).strip().casefold() not in human_keys
        ]
    normalized_humans = [str(item).strip() for item in humans if str(item).strip()]
    normalized_non_humans = [
        str(item).strip() for item in non_humans if str(item).strip()
    ]
    visible = list(dict.fromkeys([*normalized_humans, *normalized_non_humans]))
    return contract_known, normalized_humans, normalized_non_humans, visible


def _normalize_visible_cast_review(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("actualVisibleCharacters deve ser uma lista.")
    if len(value) > 50:
        raise ValueError("actualVisibleCharacters aceita no maximo 50 nomes.")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("actualVisibleCharacters deve conter apenas strings.")
        name = item.strip()
        if not name or len(name) > 120:
            raise ValueError("actualVisibleCharacters contem um nome vazio ou muito longo.")
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(name)
    return normalized


def _video_generation_policy(project_dir: Path) -> dict[str, Any]:
    manifest = _read_json(project_dir / "production_manifest.json")
    policy = manifest.get("video_generation")
    return policy if isinstance(policy, dict) else {}


def _full_frame_wan_block(project_dir: Path) -> tuple[bool, str]:
    policy = _video_generation_policy(project_dir)
    blocked = bool(policy.get("full_frame_wan_blocked"))
    reason = str(
        policy.get("full_frame_wan_block_reason")
        or "Rota Wan de quadro inteiro bloqueada para correcao com mascara mecanica."
    ).strip()
    return blocked, reason


def _base_status_is_approved(value: Any) -> bool:
    """Accept only the canonical approval state used by the video gate."""

    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii").lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return normalized == ANCHOR_APPROVED_STATUS


def _atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _atomic_bytes_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _queue_path(project_dir: Path) -> Path:
    """Resolve the queue selected by the project manifest without escaping the project."""

    project_dir = project_dir.resolve()
    manifest = _read_json(project_dir / "project_manifest.json")
    configured = str(manifest.get("take_queue") or "take_queue.json").strip()
    if not configured:
        configured = "take_queue.json"
    candidate = (project_dir / configured).resolve()
    if candidate.parent != project_dir or candidate.suffix.lower() != ".json":
        raise ValueError("take_queue do projeto deve ser um JSON na raiz do projeto.")
    return candidate


def _queue(project_dir: Path) -> dict[str, Any]:
    queue_path = _queue_path(project_dir)
    queue = _read_json(queue_path)
    if not queue:
        queue = {
            "schema_version": "1.1",
            "project_id": project_dir.name,
            "methodology": "pemara_takes_qc_assembly",
            "status": "ready",
            "assembly": {
                "preview": {"width": 1280, "height": 720, "fps": 30, "format": "mp4"},
                "final": {
                    "width": 1920,
                    "height": 1080,
                    "fps": 60,
                    "format": "mp4",
                    "fps_rule": "interpolate_only_after_take_is_approved",
                },
                "rule": "never_render_full_movie_as_one_prompt",
            },
            "takes": [],
        }
    if not isinstance(queue.get("takes", []), list):
        raise ValueError(f"{queue_path.name} possui campo takes invalido.")
    return queue


def _take_status(take: dict[str, Any]) -> str:
    explicit = str(take.get("maestro_status") or "").upper()
    if explicit in TAKE_STATUSES:
        return explicit
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    qc = take.get("qc") if isinstance(take.get("qc"), dict) else {}
    qc_status = str(qc.get("status") or "").lower()
    video_status = str(video.get("status") or "").lower()
    # A rejected anchor can legitimately return to the art-direction queue.
    # In that state the take is planned for a replacement image, not rejected
    # as a production take.  Check this before the generic "reject" marker so
    # statuses such as ``waiting_derived_anchor_after_global_rejection`` remain
    # deliverable through the anchor-candidate endpoint.
    if qc_status.startswith("waiting_derived_anchor"):
        return "PLANNED"
    if "reject" in qc_status or "reprov" in qc_status or "needs_regeneration" in qc_status:
        return "REJECTED"
    if "approv" in qc_status or "aprov" in qc_status:
        return "APPROVED"
    if video.get("output_final"):
        return "FINAL"
    if video.get("output_preview"):
        return "READY"
    if video_status in {"running", "generating"}:
        return "GENERATING"
    if video_status == "error":
        return "ERROR"
    return "PLANNED"


def _take_mode(take: dict[str, Any]) -> str:
    mode = str(take.get("take_mode") or "").strip().upper()
    return mode if mode in TAKE_MODES else "UNSPECIFIED"


def _normalize_continuity_contract(raw: Any) -> dict[str, Any]:
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise ValueError("continuityContract deve ser um objeto.")
    aliases = {**CONTINUITY_FIELD_MAP, **{value: value for value in CONTINUITY_FIELD_MAP.values()}}
    unknown = set(raw) - set(aliases)
    if unknown:
        raise ValueError(
            f"Campos de continuityContract nao permitidos: {', '.join(sorted(unknown))}"
        )
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        persisted_key = aliases[key]
        if persisted_key == "forbidden_transitions":
            if not isinstance(value, list):
                raise ValueError("continuityContract.forbiddenTransitions deve ser uma lista.")
            items = [str(item or "").strip()[:120] for item in value]
            normalized[persisted_key] = [item for item in items if item][:20]
            continue
        text = str(value or "").strip()
        if text:
            normalized[persisted_key] = text[:4000]
    return normalized


def _continuity_contract_view(take: dict[str, Any]) -> dict[str, Any]:
    raw = take.get("continuity_contract")
    try:
        normalized = _normalize_continuity_contract(raw)
    except ValueError:
        return {}
    public_names = {value: key for key, value in CONTINUITY_FIELD_MAP.items()}
    return {
        public_names[key]: value
        for key, value in normalized.items()
        if key in public_names
    }


def _take_mode_prompt(take: dict[str, Any]) -> str:
    mode = _take_mode(take)
    if mode == "UNSPECIFIED":
        return ""
    direction = {
        "PRECISION": (
            "Follow ordered micro-beats literally. Keep hands, props and bodies spatially "
            "separate and readable until the written contact or transformation; preserve anatomy "
            "and make the intended final state unmistakable."
        ),
        "ACTION": (
            "Sustain forceful physical action. Every strike has visible contact, reaction, recoil "
            "and displacement, with cloth, dust, debris or environment responding; forbid soft, "
            "weightless punches and carry useful motion through the cut."
        ),
        "PAYOFF": (
            "Escalate toward one decisive readable event, then show its physical and environmental "
            "consequence. End with continuing motion or natural energy dissipation, never a frozen tail."
        ),
    }[mode]
    contract = _normalize_continuity_contract(take.get("continuity_contract"))
    details: list[str] = []
    for key, label in (
        ("character_topology", "Character topology"),
        ("wardrobe_lock", "Wardrobe lock"),
        ("power_state", "Power state"),
        ("entry_motion", "Entry motion"),
        ("exit_motion", "Exit motion"),
        ("impact_language", "Impact language"),
    ):
        if contract.get(key):
            details.append(f"{label}: {contract[key]}.")
    forbidden = contract.get("forbidden_transitions")
    if forbidden:
        details.append(f"Forbidden transitions: {', '.join(forbidden)}.")
    return " ".join([f"MANDATORY {mode} TAKE CONTRACT: {direction}", *details])


def _take_output_path(project_dir: Path, take: dict[str, Any]) -> Path | None:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    project_dir = project_dir.resolve()
    # output_active is the version the user must see now.  Legacy projects do
    # not have it, so keep the former fallback order for backwards compatibility.
    for field in (
        "output_active",
        "output_final",
        "output_upscaled",
        "output_review_candidate",
        "output_preview",
    ):
        raw = str(video.get(field) or "").strip()
        if not raw:
            continue
        candidate = Path(raw).resolve()
        if (
            candidate.is_relative_to(project_dir)
            and candidate.is_file()
            and candidate.suffix.lower() in {".mp4", ".mov", ".webm"}
        ):
            return candidate
    return None


def _valid_project_video_path(project_dir: Path, raw_path: Any) -> Path | None:
    raw = str(raw_path or "").strip()
    if not raw:
        return None
    project_dir = project_dir.resolve()
    candidate = Path(raw).resolve()
    if (
        candidate.is_relative_to(project_dir)
        and candidate.is_file()
        and candidate.suffix.lower() in {".mp4", ".mov", ".webm"}
    ):
        return candidate
    return None


def _valid_project_final_video_path(project_dir: Path, raw_path: Any) -> Path | None:
    """Resolve a project-level final or review video without allowing path escape."""

    raw = str(raw_path or "").strip()
    if not raw:
        return None
    project_dir = project_dir.resolve()
    configured = Path(raw)
    candidate = (
        configured.resolve()
        if configured.is_absolute()
        else (project_dir / configured).resolve()
    )
    if (
        candidate.is_relative_to(project_dir)
        and candidate.is_file()
        and candidate.suffix.lower() in {".mp4", ".mov", ".webm"}
    ):
        return candidate
    return None


def _candidate_file_token(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _project_candidate_output_view(project_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    candidate = manifest.get("candidate_output")
    if not isinstance(candidate, dict):
        return {"ready": False}
    sha256 = str(candidate.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        return {"ready": False}
    media = _valid_project_final_video_path(project_dir, candidate.get("file"))
    if media is None or _candidate_file_token(media) != candidate.get("file_token"):
        return {"ready": False}
    return {
        "ready": True,
        "file": media.name,
        "bytes": media.stat().st_size,
        "sha256": sha256,
        "durationSeconds": candidate.get("duration_seconds", 0),
        "width": candidate.get("width", 0),
        "height": candidate.get("height", 0),
        "fps": candidate.get("fps", 0),
        "status": "CANDIDATE_PENDING_REVIEW",
        "sourceFingerprint": candidate.get("source_fingerprint", ""),
        "humanApproved": False,
    }


def get_project_candidate_output_path(root: Path, project_id: str) -> Path:
    project_dir = _project_path(root, project_id)
    manifest = _read_json(project_dir / "project_manifest.json")
    if not _project_candidate_output_view(project_dir, manifest).get("ready"):
        raise FileNotFoundError(f"candidate_output:{project_id}")
    return _valid_project_final_video_path(project_dir, manifest["candidate_output"]["file"])


def register_project_candidate_output(
    root: Path,
    project_id: str,
    *,
    expected_source_fingerprint: str,
    expected_manifest_sha256: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Attach a review-only chapter. Never grant take, audio or final approval."""
    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        manifest_path = project_dir / "project_manifest.json"
        original = manifest_path.read_bytes()
        if hashlib.sha256(original).hexdigest() != expected_manifest_sha256:
            raise ValueError("Project manifest changed; candidate was not registered.")
        readiness = _assembly_readiness(project_dir, _queue(project_dir))
        if not expected_source_fingerprint or readiness["sourceFingerprint"] != expected_source_fingerprint:
            raise ValueError("Project sources changed; candidate was not registered.")
        allowed = {"file", "sha256", "duration_seconds", "width", "height", "fps", "technical_review"}
        if not isinstance(record, dict) or set(record) - allowed:
            raise ValueError("Unsupported candidate record field.")
        media = _valid_project_final_video_path(project_dir, record.get("file"))
        if media is None:
            raise ValueError("Candidate video must exist inside this project.")
        expected = str(record.get("sha256") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Candidate SHA256 required.")
        before = _candidate_file_token(media)
        digest = hashlib.sha256()
        with media.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected or before != _candidate_file_token(media):
            raise ValueError("Candidate bytes changed or hash mismatch.")
        manifest = json.loads(original)
        previous = manifest.get("candidate_output")
        if isinstance(previous, dict):
            history = manifest.setdefault("candidate_output_history", [])
            if not isinstance(history, list):
                raise ValueError("Invalid candidate history; preserve it for reconciliation.")
            history.append({**previous, "superseded_at": utc_now()})
        candidate = dict(record)
        candidate.update(file=_project_relative_file(project_dir, media), sha256=expected,
                         file_token=before, source_fingerprint=expected_source_fingerprint,
                         status="CANDIDATE_PENDING_REVIEW", human_approved=False,
                         registered_at=utc_now())
        manifest["candidate_output"] = candidate
        # Recheck immediately before the existing atomic writer. Lock has the same
        # process scope as other Maestro registrations; it is not an OS-wide CAS.
        if manifest_path.read_bytes() != original or _assembly_readiness(project_dir, _queue(project_dir))["sourceFingerprint"] != expected_source_fingerprint:
            raise ValueError("Project changed before candidate commit.")
        _atomic_json_write(manifest_path, manifest)
        return _project_candidate_output_view(project_dir, manifest)


def _project_final_output_view(
    project_dir: Path,
    manifest: dict[str, Any],
    *,
    source_fingerprint: str = "",
    assembly_ready: bool = False,
) -> dict[str, Any]:
    final = manifest.get("final_output")
    if not isinstance(final, dict):
        return {"ready": False}
    master = _valid_project_final_video_path(project_dir, final.get("file"))
    if master is None:
        return {"ready": False}
    review = _valid_project_final_video_path(project_dir, final.get("review_file")) or master
    try:
        duration = float(final.get("duration_seconds") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    saved_fingerprint = str(final.get("source_fingerprint") or "").strip().lower()
    stale = bool(saved_fingerprint) and (
        not assembly_ready or saved_fingerprint != source_fingerprint
    )
    human_review = (
        final.get("human_review") if isinstance(final.get("human_review"), dict) else {}
    )
    review_status = str(human_review.get("status") or "PENDING_OWNER_REVIEW").upper()
    return {
        "ready": True,
        "masterFile": master.name,
        "masterBytes": master.stat().st_size,
        "reviewFile": review.name,
        "reviewBytes": review.stat().st_size,
        "hasReviewProxy": review != master,
        "durationSeconds": duration,
        "width": int(final.get("width") or 0),
        "height": int(final.get("height") or 0),
        "fps": int(final.get("fps") or 0),
        "videoCodec": str(final.get("video_codec") or ""),
        "audioCodec": str(final.get("audio_codec") or ""),
        "sha256": str(final.get("sha256") or ""),
        "qcStatus": str(final.get("qc_status") or ""),
        "sourceFingerprint": saved_fingerprint,
        "stale": stale,
        "reviewStatus": review_status,
        "reviewReason": str(human_review.get("reason") or ""),
        "canReview": not stale and review_status == "PENDING_OWNER_REVIEW",
    }


def get_project_final_output_path(
    root: Path,
    project_id: str,
    *,
    download: bool = False,
) -> Path:
    """Return the registered full movie (download) or its lighter player proxy."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    manifest = _read_json(project_dir / "project_manifest.json")
    final = manifest.get("final_output")
    if not isinstance(final, dict):
        raise FileNotFoundError(f"final_output:{project_id}")
    master = _valid_project_final_video_path(project_dir, final.get("file"))
    if master is None:
        raise FileNotFoundError(f"final_output:{project_id}")
    if download:
        return master
    return _valid_project_final_video_path(project_dir, final.get("review_file")) or master


def _project_relative_file(project_dir: Path, path: Path | None) -> str:
    if path is None:
        return ""
    return path.resolve().relative_to(project_dir.resolve()).as_posix()


def _source_file_token(project_dir: Path, path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    stat = path.stat()
    return {
        "file": _project_relative_file(project_dir, path),
        "bytes": stat.st_size,
        "mtimeNs": stat.st_mtime_ns,
    }


def _assembly_readiness(
    project_dir: Path,
    queue: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    sources: list[dict[str, Any]] = []
    fingerprint_sources: list[dict[str, Any]] = []
    takes = [
        item
        for item in queue.get("takes", [])
        if isinstance(item, dict)
        and str(item.get("role") or "").strip().lower() != "project_final_output"
    ]
    if not takes:
        blockers.append({
            "code": "NO_TAKES",
            "takeId": "",
            "message": "O projeto nao possui takes de producao para montar.",
        })
    for take in takes:
        take_id = str(take.get("id") or take.get("take_id") or "").strip()
        status = _take_status(take)
        if status not in {"APPROVED", "FINAL"}:
            blockers.append({
                "code": "TAKE_NOT_APPROVED",
                "takeId": take_id,
                "message": f"Take {take_id} ainda nao tem aprovacao visual final.",
            })
        video_path = _take_output_path(project_dir, take)
        if video_path is None:
            blockers.append({
                "code": "VIDEO_MISSING",
                "takeId": take_id,
                "message": f"Take {take_id} nao possui video ativo local.",
            })
        upscale = _upscale_candidate_record(take)
        if (
            isinstance(upscale, dict)
            and str(upscale.get("status") or "").upper() == "PENDING_HUMAN_REVIEW"
        ):
            blockers.append({
                "code": "UPSCALE_REVIEW_PENDING",
                "takeId": take_id,
                "message": f"Take {take_id} possui FHD aguardando decisao humana.",
            })

        audio_direction = (
            take.get("audio_direction")
            if isinstance(take.get("audio_direction"), dict)
            else {}
        )
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        delivery = (
            video.get("audio_delivery")
            if isinstance(video.get("audio_delivery"), dict)
            else {}
        )
        candidate_record = (
            audio_direction.get("salvage_candidate")
            if isinstance(audio_direction.get("salvage_candidate"), dict)
            else {}
        )
        candidate_status = str(candidate_record.get("status") or "").strip().lower()
        candidate_path = _take_audio_candidate_path(project_dir, take)
        candidate_approved = bool(
            candidate_path is not None
            and candidate_status == "approved_human_listening"
        )
        delivery_status = str(delivery.get("status") or "").upper()
        embedded_audio_approved = bool(
            delivery.get("ready")
            or delivery_status.startswith("APPROVED_")
            or delivery_status.startswith("NATIVE_")
            or delivery_status.startswith("ATTACHED_")
        )
        audio_required = bool(
            audio_direction.get("delivery_required")
            or (
                isinstance(take.get("dialogue_tracks"), list)
                and any(isinstance(item, dict) for item in take.get("dialogue_tracks", []))
            )
        )
        listening_pending = bool(
            candidate_status == "candidate_pending_human_listening"
            or audio_direction.get("human_listening_required")
        )
        if listening_pending or (
            audio_required and not (candidate_approved or embedded_audio_approved)
        ):
            blockers.append({
                "code": "AUDIO_NOT_APPROVED",
                "takeId": take_id,
                "message": f"Take {take_id} ainda nao possui audio aprovado por escuta humana.",
            })

        if video_path is not None:
            source = {
                "takeId": take_id,
                "durationSeconds": float(take.get("target_duration_seconds") or 0),
                "videoFile": _project_relative_file(project_dir, video_path),
                "videoBytes": video_path.stat().st_size,
                "audioFile": (
                    _project_relative_file(project_dir, candidate_path)
                    if candidate_approved
                    else ""
                ),
                "audioEmbedded": bool(embedded_audio_approved and not candidate_approved),
                "takeMode": _take_mode(take),
            }
            sources.append(source)
            fingerprint_sources.append({
                "takeId": take_id,
                "status": status,
                "video": _source_file_token(project_dir, video_path),
                "audio": _source_file_token(
                    project_dir, candidate_path if candidate_approved else None
                ),
                "audioEmbedded": source["audioEmbedded"],
                "approvalRevision": int(take.get("approval_revision") or 0),
            })
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_sources,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "ready": not blockers,
        "blockers": blockers,
        "sources": sources,
        "sourceFingerprint": fingerprint,
    }


def get_project_assembly_readiness(root: Path, project_id: str) -> dict[str, Any]:
    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    return _assembly_readiness(project_dir, _queue(project_dir))


def register_project_final_output(
    root: Path,
    project_id: str,
    *,
    expected_source_fingerprint: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Register a technically validated master without granting owner approval."""

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        if not isinstance(record, dict):
            raise ValueError("Registro do master deve ser um objeto.")
        readiness = _assembly_readiness(project_dir, _queue(project_dir))
        if not readiness["ready"]:
            raise ValueError("A sequencia aprovada mudou ou possui bloqueios de montagem.")
        expected = str(expected_source_fingerprint or "").strip().lower()
        if not expected or expected != readiness["sourceFingerprint"]:
            raise ValueError("A sequencia aprovada mudou durante a montagem; o master nao foi registrado.")
        master = _valid_project_final_video_path(project_dir, record.get("file"))
        if master is None:
            raise ValueError("Master final ausente ou fora do projeto.")
        review_raw = record.get("review_file")
        if review_raw and _valid_project_final_video_path(project_dir, review_raw) is None:
            raise ValueError("Proxy de revisao ausente ou fora do projeto.")
        manifest_path = project_dir / "project_manifest.json"
        manifest = _read_json(manifest_path)
        previous = manifest.get("final_output")
        if isinstance(previous, dict):
            history = manifest.setdefault("final_output_history", [])
            if not isinstance(history, list):
                history = []
                manifest["final_output_history"] = history
            history.append({**previous, "superseded_at": utc_now()})
            del history[:-20]
        final = dict(record)
        final["file"] = _project_relative_file(project_dir, master)
        if review_raw:
            final["review_file"] = _project_relative_file(
                project_dir,
                _valid_project_final_video_path(project_dir, review_raw),
            )
        final["source_fingerprint"] = readiness["sourceFingerprint"]
        final["sources"] = readiness["sources"]
        final["registered_at"] = utc_now()
        final["qc_status"] = str(
            final.get("qc_status") or "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING"
        )
        final["human_review"] = {
            "status": "PENDING_OWNER_REVIEW",
            "required": True,
        }
        manifest["final_output"] = final
        manifest["maestro_status"] = "IN_PROGRESS"
        manifest["updated_at"] = utc_now()
        _atomic_json_write(manifest_path, manifest)
        return project_view(project_dir)


def attach_project_final_review_proxy(
    root: Path,
    project_id: str,
    *,
    expected_master_sha256: str,
    review_file: str | Path,
) -> dict[str, Any]:
    """Attach a player proxy to the active master without changing its review gate."""

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        expected = str(expected_master_sha256 or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("SHA-256 esperado do master final e invalido.")
        manifest_path = project_dir / "project_manifest.json"
        manifest = _read_json(manifest_path)
        final = manifest.get("final_output")
        if not isinstance(final, dict):
            raise FileNotFoundError(f"final_output:{project_id}")
        master = _valid_project_final_video_path(project_dir, final.get("file"))
        if master is None:
            raise FileNotFoundError(f"final_output:{project_id}")
        recorded_sha256 = str(final.get("sha256") or "").strip().lower()
        if recorded_sha256 != expected:
            raise ValueError("O master ativo mudou antes da anexacao do proxy de revisao.")
        digest = hashlib.sha256()
        with master.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError("O arquivo do master ativo diverge do SHA-256 registrado.")
        review = _valid_project_final_video_path(project_dir, review_file)
        if review is None:
            raise ValueError("Proxy de revisao ausente ou fora do projeto.")
        if review == master:
            raise ValueError("O proxy de revisao deve ser separado do master final.")

        relative_review = _project_relative_file(project_dir, review)
        if final.get("review_file") == relative_review:
            return project_view(project_dir)
        now = utc_now()
        final["review_file"] = relative_review
        final["review_proxy_attached_at"] = now
        manifest["final_output"] = final
        manifest["updated_at"] = now
        _atomic_json_write(manifest_path, manifest)
        return project_view(project_dir)


def review_project_final_output(
    root: Path,
    project_id: str,
    *,
    decision: str,
    reason: str = "",
) -> dict[str, Any]:
    """Persist the owner's final viewing decision separately from technical QC."""

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        normalized = str(decision or "").strip().lower()
        if normalized not in {"approve", "reject"}:
            raise ValueError("decision deve ser approve ou reject.")
        reason = str(reason or "").strip()
        if normalized == "reject" and not 3 <= len(reason) <= 2000:
            raise ValueError("A reprovacao do master exige um motivo entre 3 e 2000 caracteres.")
        manifest_path = project_dir / "project_manifest.json"
        manifest = _read_json(manifest_path)
        final = manifest.get("final_output")
        if not isinstance(final, dict) or _valid_project_final_video_path(
            project_dir, final.get("file")
        ) is None:
            raise FileNotFoundError(f"final_output:{project_id}")
        readiness = _assembly_readiness(project_dir, _queue(project_dir))
        saved_fingerprint = str(final.get("source_fingerprint") or "").strip().lower()
        stale = bool(saved_fingerprint) and (
            not readiness["ready"]
            or saved_fingerprint != readiness["sourceFingerprint"]
        )
        if normalized == "approve" and stale:
            raise ValueError(
                "O master esta desatualizado em relacao aos takes aprovados; monte uma nova versao."
            )
        now = utc_now()
        if normalized == "approve":
            final["human_review"] = {
                "status": "APPROVED_BY_OWNER",
                "required": False,
                "decided_at": now,
            }
            final["qc_status"] = "OWNER_APPROVED_FINAL"
            manifest["maestro_status"] = "COMPLETED"
        else:
            final["human_review"] = {
                "status": "REJECTED_BY_OWNER",
                "required": True,
                "reason": reason,
                "decided_at": now,
            }
            final["qc_status"] = "OWNER_REJECTED_FINAL_REASSEMBLY_REQUIRED"
            manifest["maestro_status"] = "IN_PROGRESS"
        manifest["final_output"] = final
        manifest["updated_at"] = now
        _atomic_json_write(manifest_path, manifest)
        return project_view(project_dir)


def _upscale_candidate_record(take: dict[str, Any]) -> dict[str, Any] | None:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    candidate = video.get("upscale_candidate")
    return candidate if isinstance(candidate, dict) else None


def _upscale_candidate_path(
    project_dir: Path,
    take: dict[str, Any],
    *,
    pending_only: bool = False,
) -> Path | None:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    record = _upscale_candidate_record(take)
    if record is not None:
        candidate_status = str(record.get("status") or "").upper()
        if pending_only and candidate_status != "PENDING_HUMAN_REVIEW":
            return None
        return _valid_project_video_path(project_dir, record.get("path"))
    if pending_only:
        return None
    return _valid_project_video_path(project_dir, video.get("output_upscale_candidate"))


def _append_upscale_history(
    video: dict[str, Any],
    candidate: dict[str, Any],
    *,
    decision: str,
    reason: str,
    decided_at: str,
) -> None:
    history = video.setdefault("upscale_history", [])
    if not isinstance(history, list):
        history = []
        video["upscale_history"] = history
    job_id = str(candidate.get("job_id") or "")
    attempt = int(candidate.get("attempt") or 0)
    path = str(candidate.get("path") or "")
    already_recorded = any(
        isinstance(item, dict)
        and str(item.get("job_id") or "") == job_id
        and int(item.get("attempt") or 0) == attempt
        and str(item.get("decision") or "").upper() == decision
        and str(item.get("path") or "") == path
        for item in history
    )
    if not already_recorded:
        history.append({
            "path": path,
            "metadata": str(candidate.get("metadata") or ""),
            "job_id": job_id,
            "attempt": attempt,
            "decision": decision,
            "reason": reason,
            "technical_ready_at": str(candidate.get("technical_ready_at") or ""),
            "decided_at": decided_at,
        })
        del history[:-50]


def _append_replaced_output_history(
    video: dict[str, Any],
    *,
    previous_path: str,
    replacement: dict[str, Any],
    replaced_at: str,
) -> None:
    if not previous_path or previous_path == str(replacement.get("path") or ""):
        return
    history = video.setdefault("output_history", [])
    if not isinstance(history, list):
        history = []
        video["output_history"] = history
    if any(
        isinstance(item, dict)
        and str(item.get("path") or "") == previous_path
        and str(item.get("replaced_by_job_id") or "") == str(replacement.get("job_id") or "")
        for item in history
    ):
        return
    history.append({
        "path": previous_path,
        "role": "output_active",
        "replaced_at": replaced_at,
        "replaced_by_job_id": str(replacement.get("job_id") or ""),
        "replaced_by_upscale_attempt": int(replacement.get("attempt") or 0),
    })
    del history[:-50]


def _persist_upscale_candidate_human_decision(
    project_dir: Path,
    candidate: dict[str, Any],
) -> None:
    """Persist the queue's human decision in the canonical v2 sidecar."""

    metadata_raw = str(candidate.get("metadata") or "").strip()
    if not metadata_raw:
        return
    metadata_path = Path(metadata_raw).resolve()
    if (
        not metadata_path.is_relative_to(project_dir.resolve())
        or not metadata_path.is_file()
    ):
        raise ValueError("Sidecar do upscale pendente esta ausente ou fora do projeto.")

    sidecar = _read_json(metadata_path)
    # Legacy sidecars are never reusable by the v2 cache and should not make an
    # otherwise valid human review impossible.
    if str(sidecar.get("schema_version") or "") != "2.0":
        return

    decision = str(candidate.get("status") or "").strip().upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("Decisao humana do candidato de upscale e invalida.")
    decided_at = str(candidate.get("decided_at") or "").strip() or utc_now()
    reason = str(candidate.get("decision_reason") or "").strip()
    normalized_decision = decision.lower()

    human_approval = sidecar.get("human_approval")
    if not isinstance(human_approval, dict):
        human_approval = {}
        sidecar["human_approval"] = human_approval
    human_approval["status"] = normalized_decision
    human_approval["decided_at"] = decided_at
    if reason:
        human_approval["reason"] = reason
    sidecar["human_review_status"] = normalized_decision

    if decision == "REJECTED":
        sidecar["rejected_at"] = decided_at
        sidecar["rejection"] = {
            "status": normalized_decision,
            "reason": reason,
            "decided_at": decided_at,
        }

    _atomic_json_write(metadata_path, sidecar)


def _project_final_geometry(project_dir: Path) -> tuple[int, int]:
    """Return the project's declared final geometry with the legacy FHD default."""

    manifest = _read_json(project_dir / "project_manifest.json")
    final_resolution = str(manifest.get("final_resolution") or "").strip().lower()
    final_match = re.fullmatch(r"(\d{2,5})x(\d{2,5})", final_resolution)
    if final_match:
        target_width = int(final_match.group(1))
        target_height = int(final_match.group(2))
        if target_width > 0 and target_height > 0:
            return target_width, target_height
    return 1920, 1080


def _review_pending_upscale_candidate(
    project_dir: Path,
    take: dict[str, Any],
    *,
    decision: str,
    reason: str,
) -> bool:
    """Apply a human decision to the current upscale candidate, if one exists."""

    decision = str(decision or "").upper()
    if decision not in {"APPROVED", "REJECTED"}:
        return False
    candidate = _upscale_candidate_record(take)
    if candidate is None:
        return False
    candidate_status = str(candidate.get("status") or "").upper()
    if candidate_status == decision:
        # PATCH may be retried by the client. Keep the already persisted human
        # decision idempotent instead of applying it to the underlying raw take.
        # Also repair geometry written by the former horizontal-only approval
        # path so a vertical project can be healed with the same PATCH.
        if decision == "APPROVED":
            video = take.setdefault("video", {})
            if not isinstance(video, dict):
                raise ValueError("Contrato de video do take e invalido.")
            target_width, target_height = _project_final_geometry(project_dir)
            video["width"] = target_width
            video["height"] = target_height
        return True
    if candidate_status != "PENDING_HUMAN_REVIEW":
        return False
    candidate_path = _valid_project_video_path(project_dir, candidate.get("path"))
    if candidate_path is None:
        raise ValueError("Candidato de upscale pendente esta ausente ou fora do projeto.")
    metadata_raw = str(candidate.get("metadata") or "").strip()
    if metadata_raw:
        metadata_path = Path(metadata_raw).resolve()
        if (
            not metadata_path.is_relative_to(project_dir.resolve())
            or not metadata_path.is_file()
        ):
            raise ValueError("Sidecar do upscale pendente esta ausente ou fora do projeto.")

    now = utc_now()
    video = take.setdefault("video", {})
    if not isinstance(video, dict):
        raise ValueError("Contrato de video do take e invalido.")
    candidate["status"] = decision
    candidate["decision_reason"] = reason
    candidate["decided_at"] = now
    _append_upscale_history(
        video,
        candidate,
        decision=decision,
        reason=reason,
        decided_at=now,
    )

    qc = take.setdefault("qc", {})
    if decision == "APPROVED":
        target_width, target_height = _project_final_geometry(project_dir)
        import upscaling_required as required_upscale
        proof = required_upscale.valid_receipt(candidate_path)
        if required_upscale.receipt_path(candidate_path).exists() and not proof:
            raise ValueError("Recibo do acabamento obrigatório diverge do arquivo revisado.")
        if proof:
            if (proof.get('width'), proof.get('height')) != (target_width,target_height):
                raise ValueError("A resolução do candidato difere da seleção atual do projeto.")
            video['fps'] = 60
            video['frames'] = proof['frames']
            video['duration_seconds'] = proof['duration_seconds']
            video['upscaling_required'] = proof['pipeline_version']
        previous_active = str(video.get("output_active") or "").strip()
        _append_replaced_output_history(
            video,
            previous_path=previous_active,
            replacement=candidate,
            replaced_at=now,
        )
        video["output_active"] = str(candidate_path)
        video["output_upscaled"] = str(candidate_path)
        video["upscale_metadata"] = metadata_raw
        video["upscale_status"] = "approved"
        video["width"] = target_width
        video["height"] = target_height
        video["status"] = "ready"
        take["maestro_status"] = "APPROVED"
        take["maestro_upscale_status"] = "APPROVED"
        if isinstance(qc, dict):
            qc["status"] = "upscale_approved_human_qc"
    else:
        # Reject only the derived candidate. The previously approved active
        # file remains authoritative and the raw take can be upscaled again.
        video["upscale_status"] = "rejected"
        restored_status = str(take.get("maestro_pre_upscale_status") or "APPROVED").upper()
        take["maestro_status"] = (
            restored_status
            if restored_status in TAKE_STATUSES and restored_status != "UPSCALING"
            else "APPROVED"
        )
        take["maestro_upscale_status"] = "REJECTED"
        if isinstance(qc, dict):
            qc["status"] = "upscale_rejected_human_qc_retry_available"
    take["maestro_upscale_error"] = ""
    return True


def _take_keyframe_path(project_dir: Path, take: dict[str, Any]) -> Path | None:
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    raw = str(base.get("file") or "").strip()
    if not raw:
        return None
    project_dir = project_dir.resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = project_dir / candidate
    candidate = candidate.resolve()
    if (
        candidate.is_relative_to(project_dir)
        and candidate.is_file()
        and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ):
        return candidate
    return None


def _take_end_keyframe_path(project_dir: Path, take: dict[str, Any]) -> Path | None:
    """Resolve an explicitly approved project-local end frame for LTX long takes."""

    shot = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
    refs = shot.get("visual_references") if isinstance(shot.get("visual_references"), dict) else {}
    end_image = take.get("end_image") if isinstance(take.get("end_image"), dict) else {}
    if bool(refs.get("end_frame_approved")):
        raw = str(refs.get("end_frame_file") or "").strip()
    elif _base_status_is_approved(end_image.get("status")):
        # Older cinematic manifests store the equally explicit approved end
        # anchor beside base_image instead of under shot_contract.
        raw = str(end_image.get("file") or "").strip()
    else:
        return None
    if not raw:
        return None
    project_dir = project_dir.resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = project_dir / candidate
    candidate = candidate.resolve()
    if (
        candidate.is_relative_to(project_dir)
        and candidate.is_file()
        and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ):
        return candidate
    return None


def _take_audio_candidate_path(project_dir: Path, take: dict[str, Any]) -> Path | None:
    """Resolve only a project-local audio candidate explicitly registered for listening."""

    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    candidate_record = (
        audio_direction.get("salvage_candidate")
        if isinstance(audio_direction.get("salvage_candidate"), dict)
        else {}
    )
    raw = str(candidate_record.get("file") or "").strip()
    if not raw:
        return None
    project_dir = project_dir.resolve()
    candidate = Path(raw).resolve()
    if (
        candidate.is_relative_to(project_dir)
        and candidate.is_file()
        and candidate.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
    ):
        return candidate
    return None


def _take_audio_candidate_variants(
    project_dir: Path,
    take: dict[str, Any],
) -> list[tuple[dict[str, Any], Path]]:
    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    records = audio_direction.get("candidate_variants")
    if not isinstance(records, list):
        return []
    project_dir = project_dir.resolve()
    resolved: list[tuple[dict[str, Any], Path]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        candidate_id = str(record.get("id") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", candidate_id) or candidate_id in seen:
            continue
        path = Path(str(record.get("file") or "")).resolve()
        if (
            path.is_relative_to(project_dir)
            and path.is_file()
            and path.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
        ):
            seen.add(candidate_id)
            resolved.append((record, path))
    return resolved


def _qwen_voice_profile(
    project_dir: Path,
    take: dict[str, Any],
    first_track: dict[str, Any],
) -> dict[str, Any]:
    """Resolve one project-local Qwen voice reference without loading the model."""

    cast = _read_json(project_dir / "audio" / "voice_cast_qwen3_tts.json")
    profiles = cast.get("profiles") if isinstance(cast.get("profiles"), dict) else {}
    speaker_key = str(first_track.get("speaker") or take.get("speaker") or "").casefold()
    candidate_profile = profiles.get(speaker_key)
    if not isinstance(candidate_profile, dict):
        return {}
    reference_raw = str(candidate_profile.get("reference_audio") or "").strip()
    reference = Path(reference_raw).resolve() if reference_raw else None
    project_root = project_dir.resolve()
    if (
        reference is None
        or not reference.is_relative_to(project_root)
        or not reference.is_file()
        or reference.suffix.lower() not in {".wav", ".flac", ".mp3", ".m4a"}
        or not str(candidate_profile.get("reference_text") or "").strip()
    ):
        return {}
    return {
        "speaker": str(candidate_profile.get("speaker") or ""),
        "referenceAudio": str(reference),
        "referenceText": str(candidate_profile.get("reference_text") or "").strip(),
        "referenceTake": str(candidate_profile.get("reference_take") or ""),
        "status": str(candidate_profile.get("status") or ""),
        "modelDir": str(cast.get("model_dir") or ""),
        "python": str(cast.get("python") or ""),
    }


def get_take_audio_delivery_spec(
    root: Path,
    project_id: str,
    take_id: str,
) -> dict[str, Any]:
    """Resolve a controlled project-local audio source for the review preview.

    Dialogue never falls back to newly generated LTX speech.  We first use an
    explicitly registered audio candidate and then a preserved legacy video
    reference from the same project.  If neither exists, the caller must keep
    the visual candidate in an audio-pending state.
    """

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = _take_record(queue, take_id)
    dialogue_tracks = (
        take.get("dialogue_tracks")
        if isinstance(take.get("dialogue_tracks"), list)
        else []
    )
    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    audio_directive = (
        take.get("audio_directive")
        if isinstance(take.get("audio_directive"), dict)
        else {}
    )
    audio_strategy = str(audio_direction.get("strategy") or "").strip().lower()
    removed_ltx23_audio_strategies = {
        "ltx_native_av_ptbr_sync",
        "ltx_native_narration_ptbr",
        "ltx_ia2v_approved_ptbr_sync",
        "ltx_ia2v_qwen_ptbr_sync",
    }
    if audio_strategy in removed_ltx23_audio_strategies:
        raise ValueError(
            "A estrategia audiovisual LTX 2.3 foi removida; selecione uma estrategia H3 "
            "ou um workflow LTX 2.5 nativo aprovado."
        )
    narration_tracks = (
        take.get("narration_tracks")
        if isinstance(take.get("narration_tracks"), list)
        else []
    )
    if audio_strategy == "minimax_h3_native_scene":
        if not bool(audio_directive.get("usage_authorized", False)):
            raise ValueError("Audio nativo da cena MiniMax H3 exige diretiva explicita do proprietario.")
        ordered_dialogue = _ordered_dialogue_tracks(dialogue_tracks)
        text = _dialogue_delivery_text(ordered_dialogue) if ordered_dialogue else str(audio_direction.get("dialogue") or "").strip()
        return {
            "required": True, "dialogueRequired": bool(text),
            "narrationRequired": False, "musicRequired": False,
            "strategy": audio_strategy, "source": "",
            "sourceKind": "minimax_h3_native_scene",
            "sourceReviewStatus": "generated_pending_asr_and_human_listening" if text else "generated_pending_human_listening",
            "text": text, "language": "pt-BR" if text else "none",
        }
    if audio_strategy == "minimax_h3_native_music":
        if not bool(audio_directive.get("usage_authorized", False)):
            raise ValueError(
                "Musica nativa MiniMax H3 exige diretiva explicita do proprietario."
            )
        prompt_audio = (
            take.get("h3_prompt_audio")
            if isinstance(take.get("h3_prompt_audio"), dict)
            else {}
        )
        music = str(prompt_audio.get("non_diegetic_music") or "").strip()
        if not music or music.upper() == "N/A":
            raise ValueError(
                "Musica nativa MiniMax H3 exige direcao musical explicita."
            )
        ordered_dialogue = _ordered_dialogue_tracks(dialogue_tracks)
        dialogue_required = bool(ordered_dialogue)
        first_dialogue = ordered_dialogue[0] if ordered_dialogue else {}
        return {
            "required": True,
            "dialogueRequired": dialogue_required,
            "narrationRequired": False,
            "musicRequired": True,
            "strategy": audio_strategy,
            "source": "",
            "sourceKind": "minimax_h3_native_music",
            "sourceReviewStatus": (
                "generated_pending_asr_and_human_listening"
                if dialogue_required
                else "generated_pending_human_listening"
            ),
            "speaker": _dialogue_speaker_label(ordered_dialogue) if dialogue_required else "",
            "text": _dialogue_delivery_text(ordered_dialogue) if dialogue_required else "",
            "displayText": _dialogue_display_text(ordered_dialogue) if dialogue_required else "",
            "language": str(first_dialogue.get("language") or "en") if dialogue_required else "none",
            "musicDirection": music,
        }
    if audio_strategy == "minimax_h3_native_narration_ptbr":
        ordered_narration = _ordered_dialogue_tracks(narration_tracks)
        if not ordered_narration:
            raise ValueError("Narracao nativa MiniMax H3 exige ao menos um trecho pt-BR.")
        first_narration = ordered_narration[0]
        voice = (
            audio_direction.get("narrator_voice")
            if isinstance(audio_direction.get("narrator_voice"), dict)
            else {}
        )
        return {
            "required": True,
            "dialogueRequired": False,
            "narrationRequired": True,
            "strategy": audio_strategy,
            "source": "",
            "sourceKind": "minimax_h3_native_offscreen_narration",
            "sourceReviewStatus": "generated_pending_asr_and_human_listening",
            "speaker": str(first_narration.get("speaker") or "Narrador em off"),
            "text": _dialogue_delivery_text(ordered_narration),
            "displayText": "",
            "language": str(first_narration.get("language") or "pt-BR"),
            "narratorVoice": voice,
        }
    if not dialogue_tracks:
        return {
            "required": bool(audio_direction.get("delivery_required")),
            "dialogueRequired": False,
            "strategy": "native_ambient_and_physical_events",
            "source": "",
            "sourceKind": "engine_native_ambient",
            "sourceReviewStatus": "not_applicable",
            "speaker": "",
            "text": "",
            "language": "",
        }

    first_track = next((item for item in dialogue_tracks if isinstance(item, dict)), {})
    try:
        dialogue_start_seconds = max(0.0, float(first_track.get("start_seconds") or 0.0))
    except (TypeError, ValueError):
        dialogue_start_seconds = 0.0
    try:
        dialogue_end_seconds = max(
            dialogue_start_seconds,
            float(first_track.get("end_seconds") or 0.0),
        )
    except (TypeError, ValueError):
        dialogue_end_seconds = 0.0
    try:
        take_duration_seconds = max(0.0, float(take.get("target_duration_seconds") or 0.0))
    except (TypeError, ValueError):
        take_duration_seconds = 0.0
    dialogue_timing = {
        "dialogueStartSeconds": dialogue_start_seconds,
        "dialogueEndSeconds": dialogue_end_seconds,
        "takeDurationSeconds": take_duration_seconds,
    }
    source: Path | None = _take_audio_candidate_path(project_dir, take)
    source_kind = "registered_audio_candidate" if source is not None else ""
    source_status = "pending_human_listening"
    candidate = (
        audio_direction.get("salvage_candidate")
        if isinstance(audio_direction.get("salvage_candidate"), dict)
        else {}
    )
    if source is not None and str(candidate.get("status") or "") == "approved_human_listening":
        source_status = "human_confirmed_pt_br"

    if source is None:
        reuse = take.get("reuse_assets") if isinstance(take.get("reuse_assets"), dict) else {}
        legacy_files = reuse.get("legacy_video_files")
        if not isinstance(legacy_files, list):
            legacy_files = []
        project_root = project_dir.resolve()
        for raw in legacy_files:
            candidate_path = Path(str(raw or "")).resolve()
            if (
                candidate_path.is_relative_to(project_root)
                and candidate_path.is_file()
                and candidate_path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
            ):
                source = candidate_path
                source_kind = "preserved_legacy_native_audio"
                if "approved" in candidate_path.name.casefold():
                    source_status = "human_confirmed_pt_br"
                break

    voice_profile: dict[str, Any] = {}
    if source is None:
        voice_profile = _qwen_voice_profile(project_dir, take, first_track)
        if voice_profile:
            source_kind = "qwen3_tts_ptbr_voice_clone"
            source_status = "generated_pending_human_listening"
    return {
        "required": True,
        "dialogueRequired": True,
        "strategy": "external_pt_br_adr_after_visual_qc",
        "source": str(source) if source is not None else "",
        "sourceKind": source_kind or "missing_voice_cast",
        "sourceReviewStatus": source_status if source is not None or voice_profile else "missing",
        "speaker": _dialogue_speaker_label(dialogue_tracks),
        "text": _dialogue_delivery_text(dialogue_tracks),
        "displayText": _dialogue_display_text(dialogue_tracks),
        "language": str(first_track.get("language") or "pt-BR"),
        "voiceProfile": voice_profile,
    }


def _take_can_request_anchor(project_dir: Path, take: dict[str, Any]) -> bool:
    """Allow a director request only for a planned take that still lacks an approved base."""

    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    end_record = _end_anchor_candidate_record(take)
    if str(end_record.get("status") or "").strip().lower() == ANCHOR_PENDING_REVIEW_STATUS:
        # A delivered end anchor must be decided before the same one-dimensional
        # UI workflow can request a different start anchor. Otherwise the newer
        # request hides the delivered candidate and makes its review conflict.
        return False
    qc = take.get("qc") if isinstance(take.get("qc"), dict) else {}
    qc_status = str(qc.get("status") or "").lower()
    if _take_status(take) != "PLANNED" or _base_status_is_approved(base.get("status")):
        return False
    if _take_output_path(project_dir, take) is not None:
        return False
    return (
        _take_keyframe_path(project_dir, take) is None
        or qc_status.startswith("waiting_derived_anchor")
    )


def _latest_director_request(take: dict[str, Any]) -> dict[str, Any] | None:
    requests = take.get("maestro_director_requests")
    if not isinstance(requests, list):
        return None
    return next((item for item in reversed(requests) if isinstance(item, dict)), None)


def _latest_anchor_request_for_side(
    take: dict[str, Any],
    anchor_side: str,
) -> dict[str, Any] | None:
    requests = take.get("maestro_director_requests")
    if not isinstance(requests, list):
        return None
    wanted = str(anchor_side or "start").strip().lower()
    for item in reversed(requests):
        if not isinstance(item, dict):
            continue
        if str(item.get("category") or "").upper() != "ANCHOR":
            continue
        item_side = str(item.get("anchor_side") or "start").strip().lower()
        if item_side == wanted:
            return item
    return None


def _director_request_view(request: dict[str, Any] | None) -> dict[str, Any] | None:
    if not request:
        return None
    return {
        "requestId": str(request.get("id") or ""),
        "status": str(request.get("status") or "PENDING").upper(),
        "category": str(request.get("category") or "OTHER").upper(),
        "reason": str(request.get("reason") or ""),
        "renderInstruction": str(request.get("render_instruction") or ""),
        "createdAt": str(request.get("created_at") or ""),
        "updatedAt": str(request.get("updated_at") or request.get("created_at") or ""),
    }


def _set_latest_director_request_status(take: dict[str, Any], status: str) -> None:
    request = _latest_director_request(take)
    status = str(status or "").upper()
    if request is None or status not in DIRECTOR_REQUEST_STATUSES:
        return
    if str(request.get("status") or "PENDING").upper() == status:
        return
    request["status"] = status
    request["updated_at"] = utc_now()


def _validate_anchor_request_id(request_id: str) -> str:
    request_id = str(request_id or "").strip().lower()
    if not ANCHOR_REQUEST_ID_RE.fullmatch(request_id):
        raise ValueError("requestId de imagem-ancora invalido.")
    return request_id


def _take_record(queue: dict[str, Any], take_id: str) -> dict[str, Any]:
    take = next(
        (item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id),
        None,
    )
    if take is None:
        raise FileNotFoundError(take_id)
    return take


def _anchor_request(take: dict[str, Any], request_id: str) -> dict[str, Any]:
    requests = take.get("maestro_director_requests")
    if not isinstance(requests, list):
        raise AnchorRequestNotFoundError(request_id)
    request = next(
        (
            item
            for item in requests
            if isinstance(item, dict) and str(item.get("id") or "").lower() == request_id
        ),
        None,
    )
    if request is None:
        raise AnchorRequestNotFoundError(request_id)
    if str(request.get("category") or "").upper() != "ANCHOR":
        raise AnchorConflictError("O requestId informado nao pertence a um pedido de imagem-ancora.")
    return request


def _anchor_candidate_paths(
    project_dir: Path,
    take: dict[str, Any],
    request_id: str,
) -> tuple[Path, Path]:
    take_id = _validate_take_id(str(take.get("id") or ""))
    slug = slugify(str(take.get("slug") or take.get("name") or f"take_{take_id}"))
    base_dir = (project_dir / "base_images").resolve()
    if not base_dir.is_relative_to(project_dir.resolve()):
        raise ValueError("Diretorio de imagens-ancora fora do projeto.")
    stem = f"take{take_id}_{slug}_anchor_{request_id[:12]}"
    image_path = (base_dir / f"{stem}.png").resolve()
    metadata_path = image_path.with_suffix(".json")
    if image_path.parent != base_dir or metadata_path.parent != base_dir:
        raise ValueError("Destino da imagem-ancora fora do projeto.")
    return image_path, metadata_path


def _validate_anchor_png(image_bytes: bytes) -> dict[str, Any]:
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ValueError("Arquivo PNG da imagem-ancora esta vazio.")
    if len(image_bytes) > MAX_ANCHOR_IMAGE_BYTES:
        raise ValueError("Imagem-ancora excede o limite de 32 MB.")

    from PIL import Image

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if str(image.format or "").upper() != "PNG":
                raise ValueError("Imagem-ancora deve ser um PNG valido.")
            width, height = image.size
            mode = str(image.mode or "")
            frames = int(getattr(image, "n_frames", 1) or 1)
            image.verify()
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Imagem-ancora deve ser um PNG valido.") from exc

    minimum_width = 720 if height > width else 1024
    if width < minimum_width:
        raise ValueError(
            f"Imagem-ancora deve ter largura minima de {minimum_width} pixels."
        )
    if width > 8192 or height > 8192 or width * height > 40_000_000:
        raise ValueError("Imagem-ancora excede o limite seguro de dimensoes.")
    # ImageGen rounds fractional dimensions to whole pixels (e.g.1672x941).
    # Accept at most one pixel of rounding without modifying approved pixels.
    landscape = abs(height - width * 9 / 16) <= 1
    portrait = abs(width - height * 9 / 16) <= 1
    if not landscape and not portrait:
        raise ValueError("Imagem-ancora deve usar proporcao 16:9 ou 9:16, com no maximo 1 pixel de arredondamento.")
    if frames != 1:
        raise ValueError("Imagem-ancora deve ser um PNG estatico de um unico quadro.")
    if mode not in {"RGB", "RGBA"}:
        raise ValueError("Imagem-ancora deve usar modo RGB ou RGBA.")
    return {"width": width, "height": height, "mode": mode}


def _normalize_anchor_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise ValueError("metadata da imagem-ancora deve ser um objeto JSON.")
    aliases = {
        "prompt": "prompt",
        "model": "model",
        "negative": "negative",
        "seed": "seed",
        "sourceOutput": "source_output",
        "source_output": "source_output",
        "sourceGeneratedAt": "source_generated_at",
        "source_generated_at": "source_generated_at",
        "sourceSha256": "source_sha256",
        "source_sha256": "source_sha256",
        "generator": "generator",
        "workflow": "workflow",
        "objective": "objective",
        "requiredObjects": "required_objects",
        "required_objects": "required_objects",
    }
    unknown = set(metadata) - set(aliases)
    if unknown:
        raise ValueError(f"Campos de metadata nao permitidos: {', '.join(sorted(unknown))}")

    normalized: dict[str, Any] = {}
    for source_name, target_name in aliases.items():
        if source_name in metadata:
            if target_name in normalized and normalized[target_name] != metadata[source_name]:
                raise ValueError(f"Campo de metadata duplicado: {target_name}")
            normalized[target_name] = metadata[source_name]

    for field, limit in {
        "prompt": 16000,
        "model": 256,
        "negative": 16000,
        "source_output": 2000,
        "source_generated_at": 128,
        "source_sha256": 64,
        "generator": 256,
        "workflow": 512,
        "objective": 4000,
    }.items():
        normalized[field] = str(normalized.get(field) or "").strip()
        if len(normalized[field]) > limit:
            raise ValueError(f"Campo de metadata muito longo: {field}")
    if len(normalized["prompt"]) < 3:
        raise ValueError("metadata.prompt deve ter pelo menos 3 caracteres.")
    if len(normalized["model"]) < 2:
        raise ValueError("metadata.model deve identificar o modelo usado.")
    if normalized["source_sha256"] and not re.fullmatch(r"[a-fA-F0-9]{64}", normalized["source_sha256"]):
        raise ValueError("metadata.sourceSha256 deve ser um SHA256 hexadecimal.")

    seed = normalized.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("metadata.seed deve ser um inteiro.")
    normalized["seed"] = seed
    required_objects = normalized.get("required_objects", {})
    if not isinstance(required_objects, dict):
        raise ValueError("metadata.requiredObjects deve ser um objeto.")
    normalized["required_objects"] = required_objects
    try:
        encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata da imagem-ancora deve conter apenas valores JSON validos.") from exc
    if len(encoded.encode("utf-8")) > 64 * 1024:
        raise ValueError("metadata da imagem-ancora excede o limite de 64 KB.")
    return normalized


def _anchor_delivery_metadata_payload(
    normalized_metadata: dict[str, Any],
    take: dict[str, Any],
    image_sha256: str,
) -> dict[str, Any]:
    return {
        "prompt": normalized_metadata["prompt"],
        "model": normalized_metadata["model"],
        "negative": normalized_metadata.get("negative") or "",
        "seed": normalized_metadata.get("seed"),
        "source_output": normalized_metadata.get("source_output") or "",
        "source_generated_at": normalized_metadata.get("source_generated_at") or "",
        "source_sha256": image_sha256,
        "generator": normalized_metadata.get("generator") or "",
        "workflow": normalized_metadata.get("workflow") or "",
        "objective": normalized_metadata.get("objective") or str(take.get("objective") or ""),
        "required_objects": normalized_metadata.get("required_objects") or {},
    }


def _anchor_delivery_metadata_sha256(
    normalized_metadata: dict[str, Any],
    take: dict[str, Any],
    image_sha256: str,
) -> str:
    payload = _anchor_delivery_metadata_payload(normalized_metadata, take, image_sha256)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _registered_anchor_paths(
    project_dir: Path,
    take: dict[str, Any],
    *,
    allow_rejected: bool = False,
) -> tuple[Path, Path, dict[str, Any]]:
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    request_id = str(base.get("candidate_request_id") or "").strip().lower()
    if not ANCHOR_REQUEST_ID_RE.fullmatch(request_id):
        raise FileNotFoundError("anchor_candidate")
    status = str(base.get("status") or "").strip().lower()
    allowed_statuses = {ANCHOR_PENDING_REVIEW_STATUS, ANCHOR_APPROVED_STATUS}
    if allow_rejected:
        allowed_statuses.add(ANCHOR_REJECTED_STATUS)
    if status not in allowed_statuses:
        raise FileNotFoundError("anchor_candidate")

    base_dir = (project_dir / "base_images").resolve()
    if not base_dir.is_relative_to(project_dir.resolve()):
        raise ValueError("Diretorio de imagens-ancora fora do projeto.")
    image_path = Path(str(base.get("file") or "")).resolve()
    metadata_path = Path(str(base.get("metadata") or "")).resolve()
    if (
        image_path.parent != base_dir
        or image_path.suffix.lower() != ".png"
        or not image_path.is_file()
        or metadata_path.parent != base_dir
        or metadata_path != image_path.with_suffix(".json")
        or not metadata_path.is_file()
    ):
        raise FileNotFoundError("anchor_candidate")
    return image_path, metadata_path, base


def _validated_registered_anchor(
    project_dir: Path,
    take: dict[str, Any],
    *,
    allowed_statuses: set[str],
) -> tuple[Path, Path, dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """Resolve a candidate and verify its queue, sidecar and file agree exactly."""

    image_path, metadata_path, base = _registered_anchor_paths(project_dir, take)
    base_status = str(base.get("status") or "").strip().lower()
    if base_status not in allowed_statuses:
        raise FileNotFoundError("anchor_candidate")
    request_id = _validate_anchor_request_id(str(base.get("candidate_request_id") or ""))
    request = _anchor_request(take, request_id)
    sidecar = _read_json(metadata_path)
    if not sidecar:
        raise ValueError("Sidecar da imagem-ancora ausente ou invalido.")
    if str(sidecar.get("type") or "") != "anchor_candidate_metadata":
        raise ValueError("Sidecar nao identifica um candidato de imagem-ancora.")
    if str(sidecar.get("project_id") or "") != project_dir.name:
        raise ValueError("Sidecar pertence a outro projeto.")
    if str(sidecar.get("take_id") or "") != str(take.get("id") or ""):
        raise ValueError("Sidecar pertence a outro take.")
    if str(sidecar.get("director_request_id") or "").lower() != request_id:
        raise ValueError("Sidecar pertence a outro pedido ao diretor.")
    if Path(str(sidecar.get("image_file") or "")).resolve() != image_path:
        raise ValueError("Sidecar aponta para outra imagem-ancora.")
    if str(sidecar.get("validation_status") or "").strip().lower() != base_status:
        raise ValueError("Status do sidecar nao corresponde ao status da fila.")
    if str(request.get("status") or "").upper() != "DELIVERED":
        raise ValueError("Pedido da imagem-ancora nao esta marcado como DELIVERED.")
    request_decision = str(request.get("review_decision") or "").upper()
    human_review = sidecar.get("human_review") if isinstance(sidecar.get("human_review"), dict) else {}
    sidecar_decision = str(human_review.get("decision") or "").upper()
    if base_status == ANCHOR_APPROVED_STATUS:
        if request_decision != "APPROVED" or sidecar_decision != "APPROVED":
            raise ValueError("Imagem-ancora nao possui evidencia de aprovacao humana.")
    elif request_decision or sidecar_decision:
        raise ValueError("Imagem-ancora pendente contem uma decisao humana inconsistente.")

    image_bytes = image_path.read_bytes()
    image_info = _validate_anchor_png(image_bytes)
    image_sha256 = hashlib.sha256(image_bytes).hexdigest()
    if str(sidecar.get("image_sha256") or "").lower() != image_sha256:
        raise ValueError("SHA256 do sidecar nao corresponde a imagem-ancora.")
    if str(sidecar.get("source_sha256") or "").lower() != image_sha256:
        raise ValueError("SHA256 de origem do sidecar nao corresponde a imagem-ancora.")
    if str(base.get("image_sha256") or "").lower() != image_sha256:
        raise ValueError("SHA256 da fila nao corresponde a imagem-ancora.")
    if str(request.get("candidate_sha256") or "").lower() != image_sha256:
        raise ValueError("SHA256 do pedido nao corresponde a imagem-ancora.")
    for field in ("width", "height", "mode"):
        if sidecar.get(field) != image_info[field]:
            raise ValueError("Dimensoes ou modo do sidecar nao correspondem a imagem-ancora.")
    delivery_payload = {
        "prompt": str(sidecar.get("prompt") or ""),
        "model": str(sidecar.get("model") or ""),
        "negative": str(sidecar.get("negative") or ""),
        "seed": sidecar.get("seed"),
        "source_output": str(sidecar.get("source_output") or ""),
        "source_generated_at": str(sidecar.get("source_generated_at") or ""),
        "source_sha256": str(sidecar.get("source_sha256") or "").lower(),
        "generator": str(sidecar.get("generator") or ""),
        "workflow": str(sidecar.get("workflow") or ""),
        "objective": str(sidecar.get("objective") or ""),
        "required_objects": sidecar.get("required_objects") or {},
    }
    try:
        canonical = json.dumps(
            delivery_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Metadados do sidecar nao sao JSON valido.") from exc
    delivery_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if str(sidecar.get("delivery_metadata_sha256") or "").lower() != delivery_sha256:
        raise ValueError("Hash dos metadados do sidecar nao corresponde ao conteudo registrado.")
    if str(request.get("candidate_metadata_sha256") or "").lower() != delivery_sha256:
        raise ValueError("Hash dos metadados do pedido nao corresponde ao sidecar.")
    return image_path, metadata_path, base, sidecar, image_info, image_sha256


def _end_anchor_candidate_record(take: dict[str, Any]) -> dict[str, Any]:
    record = take.get("end_anchor_candidate")
    return record if isinstance(record, dict) else {}


def _validated_registered_end_anchor(
    project_dir: Path,
    take: dict[str, Any],
    *,
    allowed_statuses: set[str],
) -> tuple[Path, Path, dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """Validate a pending/final boundary candidate without replacing the start anchor."""

    record = _end_anchor_candidate_record(take)
    if not record:
        raise FileNotFoundError("end_anchor_candidate")
    shadow = dict(take)
    shadow["base_image"] = record
    return _validated_registered_anchor(
        project_dir,
        shadow,
        allowed_statuses=allowed_statuses,
    )


def _invalidate_take_thumbnail(project_dir: Path, take_id: str) -> None:
    cached = (project_dir / "qc" / "maestro_thumbnails" / f"take_{take_id}.jpg").resolve()
    if cached.is_relative_to(project_dir.resolve()):
        cached.unlink(missing_ok=True)


def _validated_preanalysis_gallery(
    project_dir: Path,
    take: dict[str, Any],
) -> tuple[Path, dict[str, Any], str]:
    """Resolve one immutable per-take static-seed review sheet."""

    record = (
        take.get("preanalysis_anchor_gallery")
        if isinstance(take.get("preanalysis_anchor_gallery"), dict)
        else {}
    )
    if str(record.get("status") or "") != "READY_HUMAN_REVIEW_PENDING":
        raise FileNotFoundError("preanalysis_anchor_gallery")
    raw = str(record.get("contact_sheet") or "").strip()
    expected_sha256 = str(record.get("contact_sheet_sha256") or "").strip().lower()
    candidate_ids = record.get("candidate_ids")
    if not raw or not expected_sha256 or not isinstance(candidate_ids, list):
        raise ValueError("Galeria de pre-analise possui contrato incompleto.")
    normalized_candidate_ids = [str(candidate_id) for candidate_id in candidate_ids]
    has_unique_candidate_ids = (
        len(set(normalized_candidate_ids)) == len(normalized_candidate_ids)
    )
    standard_static_gallery = len(normalized_candidate_ids) in {2, 3}

    take_id = str(take.get("id") or take.get("take_id") or "").strip()
    end_image = take.get("end_image") if isinstance(take.get("end_image"), dict) else {}
    h3_dynamic_end_gallery = (
        record.get("h3_choreography_freedom") is True
        and normalized_candidate_ids == [f"{take_id}_START"]
        and str(end_image.get("status") or "")
        == "DYNAMIC_END_FROM_H3_TAKE_NOT_PRECOMPUTED"
        and end_image.get("static_image_generation_forbidden") is True
        and str(end_image.get("source_policy") or "")
        == "LAST_STILL_MOVING_FRAME_OF_HUMAN_APPROVED_H3_TAKE"
    )
    if not has_unique_candidate_ids or not (
        standard_static_gallery or h3_dynamic_end_gallery
    ):
        raise ValueError(
            "Galeria de pre-analise deve conter START/END e no maximo um "
            "checkpoint, ou somente START quando o END dinamico H3 estiver "
            "explicitamente contratado."
        )
    gallery = (project_dir / raw).resolve()
    if (
        not gallery.is_relative_to(project_dir.resolve())
        or gallery.suffix.lower() != ".png"
        or not gallery.is_file()
    ):
        raise FileNotFoundError("preanalysis_anchor_gallery")
    actual_sha256 = hashlib.sha256(gallery.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError("SHA256 da galeria de pre-analise diverge do manifesto.")
    return gallery, record, actual_sha256


def _take_view(take: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    take_id = str(take.get("id") or take.get("take_id") or "")
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    qc = take.get("qc") if isinstance(take.get("qc"), dict) else {}
    generation = (
        take.get("video_generation")
        if isinstance(take.get("video_generation"), dict)
        else {}
    )
    generation_profile = str(
        generation.get("profile") or ENGINE_SELECTION_REQUIRED_PROFILE
    ).strip().lower()
    is_removed_engine = generation_profile in {
        *REMOVED_LTX23_GENERATION_PROFILES,
        LTX25_TWO_ANCHOR_PROFILE,
        REMOVED_MINIMAX_H3_LEGACY_PROFILE,
        WAN22_ANIMATE_PROFILE,
        "wan22_a14b_identity_v1",
        "wan22_a14b_motion_v1",
        "wan22_fun_camera_v1",
    }
    is_ltx25 = False  # LTX removed; historical files and profiles remain readable.
    is_minimax_h3 = generation_profile in MINIMAX_H3_GENERATION_PROFILES
    is_minimax_h3_vertical = generation_profile == MINIMAX_H3_VERTICAL_PROFILE
    is_wan_animate = generation_profile == WAN22_ANIMATE_PROFILE
    keyframe_approved = _base_status_is_approved(base.get("status"))
    if keyframe_approved and base.get("candidate_request_id"):
        if project_dir is None:
            keyframe_approved = False
        else:
            try:
                _validated_registered_anchor(
                    project_dir,
                    take,
                    allowed_statuses={ANCHOR_APPROVED_STATUS},
                )
            except (FileNotFoundError, ValueError, AnchorConflictError, AnchorRequestNotFoundError):
                keyframe_approved = False
    status = _take_status(take)
    preview = _take_output_path(project_dir, take) if project_dir is not None else None
    preview_stat = preview.stat() if preview is not None else None
    review_proxy = (
        review_proxy_info(project_dir, take_id, preview)
        if project_dir is not None and preview is not None
        else None
    )
    keyframe = _take_keyframe_path(project_dir, take) if project_dir is not None else None
    # Newer project contracts can keep an approved end anchor for editorial
    # reference while explicitly disabling start/end interpolation.  Respect
    # that switch; feeding incompatible casts or camera geometry to LTX makes
    # subjects dissolve, duplicate and re-form between the anchors.
    end_frame_enabled = bool(
        generation.get("start_end_frame_enabled", True)
    )
    end_keyframe = (
        _take_end_keyframe_path(project_dir, take)
        if project_dir is not None
        and (is_ltx25 or is_minimax_h3)
        and end_frame_enabled
        else None
    )
    require_approved_end_frame = bool(
        generation.get("require_approved_end_frame", False)
    )
    end_frame_blocked = require_approved_end_frame and end_keyframe is None
    end_anchor_candidate_view: dict[str, Any] | None = None
    start_anchor_candidate_view: dict[str, Any] | None = None
    preanalysis_gallery_view: dict[str, Any] | None = None
    if project_dir is not None:
        start_status = str(base.get("status") or "").strip().lower()
        if (
            base.get("candidate_request_id")
            and start_status in {ANCHOR_PENDING_REVIEW_STATUS, ANCHOR_APPROVED_STATUS}
        ):
            try:
                (
                    start_image,
                    start_metadata,
                    _start_base,
                    _start_sidecar,
                    start_image_info,
                    start_image_sha256,
                ) = _validated_registered_anchor(
                    project_dir,
                    take,
                    allowed_statuses={start_status},
                )
                start_anchor_candidate_view = {
                    "requestId": str(base.get("candidate_request_id") or ""),
                    "status": start_status,
                    "file": start_image.name,
                    "metadataFile": start_metadata.name,
                    "sha256": start_image_sha256,
                    "anchorSide": "start",
                    **start_image_info,
                    "deliveredAt": str(base.get("delivered_at") or ""),
                }
            except (FileNotFoundError, ValueError, AnchorConflictError, AnchorRequestNotFoundError):
                start_anchor_candidate_view = None
        end_record = _end_anchor_candidate_record(take)
        end_status = str(end_record.get("status") or "").strip().lower()
        if end_status in {ANCHOR_PENDING_REVIEW_STATUS, ANCHOR_APPROVED_STATUS}:
            try:
                (
                    end_image,
                    end_metadata,
                    _end_base,
                    _end_sidecar,
                    end_image_info,
                    end_image_sha256,
                ) = _validated_registered_end_anchor(
                    project_dir,
                    take,
                    allowed_statuses={end_status},
                )
                end_anchor_candidate_view = {
                    "requestId": str(end_record.get("candidate_request_id") or ""),
                    "status": end_status,
                    "file": end_image.name,
                    "metadataFile": end_metadata.name,
                    "sha256": end_image_sha256,
                    "anchorSide": "end",
                    **end_image_info,
                    "deliveredAt": str(end_record.get("delivered_at") or ""),
                }
            except (FileNotFoundError, ValueError, AnchorConflictError, AnchorRequestNotFoundError):
                end_anchor_candidate_view = None
        try:
            gallery_path, gallery_record, gallery_sha256 = _validated_preanalysis_gallery(
                project_dir,
                take,
            )
            preanalysis_gallery_view = {
                "status": "READY_HUMAN_REVIEW_PENDING",
                "file": gallery_path.name,
                "sha256": gallery_sha256,
                "candidateIds": list(map(str, gallery_record.get("candidate_ids") or [])),
                "candidateCount": len(gallery_record.get("candidate_ids") or []),
                "humanApproval": "PENDING",
            }
        except (FileNotFoundError, ValueError):
            preanalysis_gallery_view = None
    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    audio_delivery = (
        video.get("audio_delivery")
        if isinstance(video.get("audio_delivery"), dict)
        else {}
    )
    audio_delivery_status = str(audio_delivery.get("status") or "").upper()
    audio_required = bool(
        audio_direction.get("delivery_required")
        or (
            isinstance(take.get("dialogue_tracks"), list)
            and any(isinstance(item, dict) for item in take.get("dialogue_tracks", []))
        )
    )
    inferred_audio_ready = bool(
        audio_delivery_status.startswith("ATTACHED_")
        or audio_delivery_status.startswith("NATIVE_")
        or audio_delivery_status.startswith("APPROVED_")
    )
    audio_ready = bool(audio_delivery.get("ready", inferred_audio_ready))
    audio_candidate_record = (
        audio_direction.get("salvage_candidate")
        if isinstance(audio_direction.get("salvage_candidate"), dict)
        else {}
    )
    audio_candidate = (
        _take_audio_candidate_path(project_dir, take)
        if project_dir is not None
        else None
    )
    audio_candidate_variants = (
        _take_audio_candidate_variants(project_dir, take)
        if project_dir is not None
        else []
    )
    audio_candidate_status = str(audio_candidate_record.get("status") or "")
    audio_candidates_view = [
        {
            "candidateId": str(record.get("id") or ""),
            "label": str(record.get("label") or "Opcao de voz"),
            "file": path.name,
            "status": str(record.get("status") or ""),
            "source": str(record.get("source_take") or ""),
            "transcription": str(record.get("cpu_asr_transcription") or ""),
            "durationSeconds": float(record.get("duration_seconds") or 0),
        }
        for record, path in audio_candidate_variants
    ]
    variants_need_review = any(
        item["status"] == "candidate_pending_human_listening"
        for item in audio_candidates_view
    )
    can_request_anchor = bool(
        project_dir is not None and _take_can_request_anchor(project_dir, take)
    )
    cast_contract_known, _expected_humans, _expected_non_humans, expected_visible_cast = (
        _take_visible_cast_contract(take)
    )
    director_request = _director_request_view(_latest_director_request(take))
    output_upscaled = str(video.get("output_upscaled") or "").strip()
    pending_upscale = (
        _upscale_candidate_path(project_dir, take, pending_only=True)
        if project_dir is not None
        else None
    )
    upscale_candidate = _upscale_candidate_record(take)
    upscale_candidate_status = (
        str(upscale_candidate.get("status") or "").upper()
        if upscale_candidate is not None
        else ""
    )
    upscale_status = str(take.get("maestro_upscale_status") or "").upper()
    full_frame_wan_blocked = False
    full_frame_wan_block_reason = ""
    if project_dir is not None:
        full_frame_wan_blocked, full_frame_wan_block_reason = _full_frame_wan_block(
            project_dir
        )
        if is_minimax_h3:
            full_frame_wan_blocked = False
            full_frame_wan_block_reason = ""
        if is_ltx25:
            full_frame_wan_blocked = not bool(generation.get("maestro_job_enabled", False))
            full_frame_wan_block_reason = str(
                generation.get("generation_block_reason")
                or "LTX-2.5 sera produzido pelo pipeline serial do projeto apos a aprovacao das duas ancoras."
            ).strip()
    review_only_generation_blocked = bool(
        take.get("video_generation_forbidden")
    )
    if review_only_generation_blocked:
        full_frame_wan_blocked = True
        full_frame_wan_block_reason = str(
            take.get("video_generation_block_reason")
            or "Projeto reservado para revisao de imagens; geracao de video desativada."
        ).strip()
    render_authorization_declared = "render_authorized" in take
    render_authorization_blocked = (
        render_authorization_declared and take.get("render_authorized") is not True
    )
    wan_pose_review_blocked = False
    wan_pose_review_reason = ""
    if is_wan_animate and project_dir is not None:
        wan_control = (
            take.get("wan_animate_control")
            if isinstance(take.get("wan_animate_control"), dict)
            else {}
        )
        pose_manifest_raw = str(wan_control.get("pose_manifest") or "").strip()
        if not pose_manifest_raw:
            wan_pose_review_blocked = True
            wan_pose_review_reason = (
                "Aguardando video de performance humana real e previa DWPose aprovada."
            )
        else:
            pose_manifest = (project_dir / pose_manifest_raw).resolve()
            if (
                not pose_manifest.is_relative_to(project_dir.resolve())
                or not pose_manifest.is_file()
            ):
                wan_pose_review_blocked = True
                wan_pose_review_reason = "Manifesto da previa DWPose ausente ou fora do projeto."
            else:
                try:
                    pose_record = _read_json(pose_manifest)
                except (OSError, ValueError, json.JSONDecodeError):
                    pose_record = {}
                if str(pose_record.get("status") or "").strip().upper() != "APPROVED_BY_OWNER":
                    wan_pose_review_blocked = True
                    wan_pose_review_reason = "A previa DWPose aguarda aprovacao humana."
    has_upscaled = False
    upscaled_path: Path | None = None
    if project_dir is not None and output_upscaled:
        upscaled_path = Path(output_upscaled).resolve()
        has_upscaled = (
            upscaled_path.is_relative_to(project_dir.resolve())
            and upscaled_path.is_file()
            and upscaled_path.suffix.lower() in {".mp4", ".mov", ".webm"}
        )
    approved_current_upscale = bool(
        upscale_status == "APPROVED"
        and upscale_candidate_status == "APPROVED"
        and has_upscaled
        and preview is not None
        and upscaled_path is not None
        and preview == upscaled_path
    )
    return {
        "takeId": take_id,
        "name": str(take.get("slug") or take.get("name") or f"Take {take_id}"),
        "status": status,
        "takeMode": _take_mode(take),
        "continuityContract": _continuity_contract_view(take),
        "objective": str(take.get("objective") or ""),
        "animationPrompt": str(take.get("animation_prompt") or ""),
        "speaker": str(take.get("speaker") or ""),
        "dialoguePtBr": str(take.get("dialogue_pt_br") or ""),
        "audioRequired": audio_required,
        "audioReady": audio_ready,
        "audioStatus": audio_delivery_status,
        "audioMessage": str(audio_delivery.get("message") or ""),
        "audioSourceKind": str(audio_delivery.get("source_kind") or ""),
        "audioHumanReviewRequired": bool(audio_delivery.get("human_listening_required")),
        "hasAudioCandidate": audio_candidate is not None,
        "audioCandidates": audio_candidates_view,
        "audioCandidateFile": audio_candidate.name if audio_candidate is not None else "",
        "audioCandidateStatus": audio_candidate_status if audio_candidate is not None else "",
        "audioCandidateNeedsReview": bool(
            variants_need_review
            or (
                audio_candidate is not None
                and audio_candidate_status == "candidate_pending_human_listening"
            )
        ),
        "audioCandidateApproved": bool(
            audio_candidate is not None
            and audio_candidate_status == "approved_human_listening"
        ),
        "audioCandidateSource": (
            str(audio_candidate_record.get("source_take") or "")
            if audio_candidate is not None
            else ""
        ),
        "audioCandidateTranscription": (
            str(audio_candidate_record.get("cpu_asr_transcription") or "")
            if audio_candidate is not None
            else ""
        ),
        "audioHumanListeningRequired": bool(
            audio_candidate is not None and audio_direction.get("human_listening_required")
        ),
        "durationSeconds": float(take.get("target_duration_seconds") or 0),
        "engine": (
            "LTX 2.5 Two-Stage 960x544"
            if is_ltx25
            else "MiniMax H3 FL2VA INT8 + Qwen3-VL-32B"
            if is_minimax_h3
            else "Motor legado removido - selecione H3"
            if is_removed_engine
            else "Selecione MiniMax H3"
        ),
        "legacyEngine": str(video.get("final_model") or video.get("preview_model") or ""),
        "generationProfile": generation_profile,
        "stage": (
            "LTX25_TWO_ANCHOR_APPROVAL_GATE"
            if is_ltx25
            else "MINIMAX_H3_OWNER_LOCKED_BASE"
            if is_minimax_h3
            else "ENGINE_SELECTION_REQUIRED"
        ),
        "width": int(
            generation.get("width")
            or (720 if is_minimax_h3_vertical else 960 if is_ltx25 else 1280 if is_minimax_h3 else 0)
        ),
        "height": int(
            generation.get("height")
            or (1280 if is_minimax_h3_vertical else 544 if is_ltx25 else 720 if is_minimax_h3 else 0)
        ),
        "fps": float(generation.get("fps") or (24 if is_ltx25 or is_minimax_h3 else 0)),
        "hasKeyframe": keyframe is not None,
        "hasEndKeyframe": end_keyframe is not None,
        "endKeyframeFile": end_keyframe.name if end_keyframe is not None else "",
        "hasEndKeyframeCandidate": end_anchor_candidate_view is not None,
        "endAnchorCandidate": end_anchor_candidate_view,
        "anchorCandidate": end_anchor_candidate_view or start_anchor_candidate_view,
        "hasPreanalysisGallery": preanalysis_gallery_view is not None,
        "preanalysisGallery": preanalysis_gallery_view,
        "keyframeApproved": keyframe_approved,
        "anchorCastContractKnown": cast_contract_known,
        "anchorExpectedVisibleCharacters": expected_visible_cast,
        "canRequestAnchor": can_request_anchor,
        "canGenerate": (
            bool(base.get("file"))
            and keyframe_approved
            and not is_removed_engine
            and (is_ltx25 or is_minimax_h3)
            and not full_frame_wan_blocked
            and not end_frame_blocked
            and not render_authorization_blocked
            and not wan_pose_review_blocked
        ),
        "generationBlocked": (
            full_frame_wan_blocked
            or is_removed_engine
            or not (is_ltx25 or is_minimax_h3)
            or end_frame_blocked
            or render_authorization_blocked
            or wan_pose_review_blocked
        ),
        "generationBlockedReason": (
            "O motor legado deste take foi removido; escolha MiniMax H3."
            if is_removed_engine
            else "Escolha explicitamente MiniMax H3 para este take."
            if not (is_ltx25 or is_minimax_h3)
            else "Aguardando a segunda ancora aprovada para o take first/last-frame."
            if end_frame_blocked
            else wan_pose_review_reason
            if wan_pose_review_blocked
            else "Render bloqueado ate aprovacao explicita do proprietario."
            if render_authorization_blocked
            else full_frame_wan_block_reason
        ),
        "hasLatent": bool(video.get("latent_file")),
        "keyframeFile": keyframe.name if keyframe is not None else "",
        "qcStatus": str(qc.get("status") or ""),
        "notes": str(take.get("maestro_notes") or ""),
        "lastJobId": str(take.get("maestro_last_job_id") or ""),
        "lastError": str(take.get("maestro_last_error") or "") if status == "ERROR" else "",
        "hasPreview": preview is not None,
        "previewFile": preview.name if preview is not None else "",
        "previewVersion": (
            f"{preview_stat.st_mtime_ns:x}-{preview_stat.st_size:x}"
            if preview_stat is not None
            else ""
        ),
        "masterBytes": preview_stat.st_size if preview_stat is not None else 0,
        "hasReviewProxy": review_proxy is not None,
        "reviewProxyFile": str((review_proxy or {}).get("file") or ""),
        "reviewProxyVersion": str((review_proxy or {}).get("version") or ""),
        "reviewProxyBytes": int((review_proxy or {}).get("sizeBytes") or 0),
        "reviewDurationSeconds": float((review_proxy or {}).get("durationSeconds") or 0),
        "reviewWidth": int((review_proxy or {}).get("width") or 0),
        "reviewHeight": int((review_proxy or {}).get("height") or 0),
        "reviewFps": float((review_proxy or {}).get("fps") or 0),
        "canDownload": preview is not None and status in DOWNLOADABLE_TAKE_STATUSES,
        "isUpscaled": has_upscaled,
        "canUpscale": (
            preview is not None
            and status == "APPROVED"
            and upscale_status not in {"QUEUED", "UPSCALING"}
            and pending_upscale is None
            and not approved_current_upscale
        ),
        "hasUpscalePreview": pending_upscale is not None,
        "upscalePreviewFile": pending_upscale.name if pending_upscale is not None else "",
        "upscaleCandidateStatus": upscale_candidate_status,
        "upscaleJobId": str(
            take.get("maestro_upscale_job_id")
            or (take.get("maestro_last_job_id") if upscale_status else "")
            or ""
        ),
        "upscaleAttempt": int(take.get("maestro_upscale_attempt") or 0),
        "upscaleStatus": upscale_status,
        "upscaleError": str(take.get("maestro_upscale_error") or ""),
        "directorRequest": director_request,
    }


def _production_motion_prompt(take: dict[str, Any], shot: dict[str, Any]) -> str:
    approved_prompt = str(take.get("animation_prompt") or "").strip()
    if approved_prompt:
        return approved_prompt
    camera = shot.get("camera") if isinstance(shot.get("camera"), dict) else {}
    beats = shot.get("motion_beats") if isinstance(shot.get("motion_beats"), dict) else {}
    refs = shot.get("visual_references") if isinstance(shot.get("visual_references"), dict) else {}
    layers = take.get("motion_layers") if isinstance(take.get("motion_layers"), dict) else {}
    parts = [
        "Use strict cinematic shot discipline. The approved start frame defines composition, geography, objects, style and identity.",
        "Animate a real video take with a visible beginning, middle and end. Preserve every subject identity; never replace the subject with another object.",
        "Use explicit camera motion, foreground and background parallax, particles or atmosphere, object motion and animated lighting. Do not make a slideshow, living photo or simple digital zoom.",
        f"Subject: {shot.get('subject', '')}.",
        f"Action: {shot.get('action', '')}.",
        f"Scene: {shot.get('scene', '')}.",
        f"Camera: {camera.get('movement', '')}; angle {camera.get('angle', '')}; lens {camera.get('lens', '')}; focus {camera.get('focus', '')}.",
        f"Lighting: {shot.get('lighting', '')}. Mood: {shot.get('mood', '')}.",
        f"Motion beats: start {beats.get('start', '')}; middle {beats.get('middle', '')}; end {beats.get('end', '')}.",
        f"End-frame target: {refs.get('end_frame_note', '')}.",
        f"Motion layers: camera {layers.get('camera', '')}; environment {layers.get('environment', '')}; particles {layers.get('particles', '')}; objects {layers.get('objects', '')}; lighting {layers.get('lighting', '')}.",
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _director_correction_prompt(take: dict[str, Any]) -> str:
    """Turn the latest rejection into a render-safe mandatory instruction."""

    if _take_status(take) not in {"REJECTED", "ERROR"}:
        return ""
    request = _latest_director_request(take)
    if not isinstance(request, dict):
        return ""
    if str(request.get("category") or "").upper() == "ANCHOR":
        return ""
    if str(request.get("status") or "").upper() not in {
        "PENDING", "IN_PROGRESS", "DELIVERED"
    }:
        return ""
    reason = str(request.get("reason") or "").strip()
    if not reason:
        return ""
    render_instruction = str(request.get("render_instruction") or "").strip()
    instruction = render_instruction or reason
    category = str(request.get("category") or "OTHER").upper()
    return (
        "MANDATORY DIRECTOR CORRECTION FOR THIS REPLACEMENT RENDER "
        f"({category}): {instruction} The prior preview was explicitly rejected; "
        "apply this corrected visual specification consistently in every frame."
    )


def _h3_prompt_audio_sections(
    take: dict[str, Any],
    shot: dict[str, Any],
    *,
    visual_only_pass: bool,
) -> tuple[str, str]:
    """Resolve the two official H3 audio fields without using a cloud optimizer."""

    if visual_only_pass:
        return "N/A", "N/A"
    prompt_audio = (
        take.get("h3_prompt_audio")
        if isinstance(take.get("h3_prompt_audio"), dict)
        else {}
    )
    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    soundscape = str(prompt_audio.get("overall_soundscape") or "").strip()
    if not soundscape:
        scene = str(shot.get("scene") or "the established environment").strip()
        soundscape = (
            f"Physical ambience in {scene} remains synchronized with cloth movement, "
            "debris, impacts and non-verbal exertion throughout the visible action."
        )
    music = str(prompt_audio.get("non_diegetic_music") or "").strip()
    if not music and audio_direction.get("music") is False:
        music = "N/A"
    elif not music:
        music = "N/A"
    return soundscape, music


def _h3_photographic_reference_role(value: Any) -> str:
    """Keep anchor semantics while removing franchise tokens that bias H3 toward animation."""

    role = str(value or "").strip()
    replacements = (
        (r"(?i)dragon[ _-]*ball", "paired_martial_arts"),
        (r"(?i)super[ _-]*saiy(?:a|e)n", "golden_energy_state"),
        (r"(?i)gogeta", "single_fused_performer"),
        (r"(?i)goku", "left_performer"),
        (r"(?i)vegeta", "right_performer"),
    )
    for pattern, replacement in replacements:
        role = re.sub(pattern, replacement, role)
    return role


def _transition_camera_pose(shot: dict[str, Any], prompt: str) -> str:
    camera = shot.get("camera") if isinstance(shot.get("camera"), dict) else {}
    direction = f"{camera.get('movement', '')} {prompt}".casefold()
    if "anti clockwise" in direction or "counterclockwise" in direction:
        return "Anti Clockwise (ACW)"
    if "clockwise" in direction or "orbit" in direction:
        return "ClockWise (CW)"
    if any(token in direction for token in ("pull back", "backward", "backwards", "recede")):
        return "Zoom Out"
    if any(token in direction for token in ("forward", "inward", "into the", "toward", "push in")):
        return "Zoom In"
    if any(token in direction for token in ("upward", "crane up", "rise")):
        return "Pan Up"
    if any(token in direction for token in ("downward", "crane down", "descend")):
        return "Pan Down"
    if "left" in direction:
        return "Pan Left"
    if "right" in direction:
        return "Pan Right"
    return "Pan Right"


def _story_batch_policy_view(queue: dict[str, Any]) -> dict[str, Any]:
    raw = queue.get("story_batch_policy")
    if not isinstance(raw, dict) or not bool(raw.get("enabled")):
        return {"enabled": False}

    try:
        batch_size = int(raw.get("batch_size") or 3)
    except (TypeError, ValueError):
        batch_size = 3
    batch_size = max(1, min(20, batch_size))

    available_ids = [
        str(take.get("id") or "").strip()
        for take in queue.get("takes", [])
        if isinstance(take, dict) and str(take.get("id") or "").strip()
    ]
    available = set(available_ids)
    requested_order = raw.get("render_order")
    if not isinstance(requested_order, list):
        requested_order = []
    render_order: list[str] = []
    for value in requested_order:
        take_id = str(value or "").strip()
        if take_id in available and take_id not in render_order:
            render_order.append(take_id)
    render_order.extend(take_id for take_id in available_ids if take_id not in render_order)

    correction_mode = bool(raw.get("allow_incomplete_correction_batch", False)) and any(
        _take_status(take) in {"ERROR", "REJECTED"}
        for take in queue.get("takes", [])
        if isinstance(take, dict)
    )

    return {
        "enabled": True,
        "version": str(raw.get("version") or "story_batches_v1"),
        "batchSize": batch_size,
        "renderOrder": render_order,
        "strictContiguous": bool(raw.get("strict_contiguous", True)),
        "requireAllBaseImagesReady": bool(raw.get("require_all_base_images_ready", True)),
        # Compatibility for Maestro pages that were already open before the
        # correction-aware JavaScript shipped: while a rejected/error retry
        # exists, expose a one-correction window. New story takes immediately
        # return to the strict trio policy after the retry leaves that state.
        "fillEligibleAcrossBatches": False if correction_mode else bool(
            raw.get("fill_eligible_across_batches", False)
        ),
        "requireFullBatch": False if correction_mode else bool(
            raw.get("require_full_batch", False)
        ),
        "allowIncompleteCorrectionBatch": bool(
            raw.get("allow_incomplete_correction_batch", False)
        ),
        "correctionMode": correction_mode,
        "controlSurface": str(raw.get("control_surface") or "maestro_production_button"),
        "configuredAt": str(raw.get("configured_at") or ""),
        "batches": [
            render_order[index:index + batch_size]
            for index in range(0, len(render_order), batch_size)
        ],
    }


def _anchor_generation_policy_view(queue: dict[str, Any]) -> dict[str, Any]:
    raw = queue.get("anchor_generation_policy")
    if not isinstance(raw, dict):
        return {
            "provider": "maestro_local_executor",
            "localExecutorAllowed": True,
            "requireVisualCastVerificationForVideo": False,
        }
    provider = str(raw.get("provider") or "maestro_local_executor").strip()
    return {
        "version": str(raw.get("version") or "anchor_generation_policy_v1"),
        "revision": str(raw.get("revision") or ""),
        "status": str(raw.get("status") or ""),
        "provider": provider,
        "localExecutorAllowed": not bool(raw.get("local_executor_forbidden")),
        "requiredGenerator": str(raw.get("required_generator") or provider),
        "requireGeneratorProvenance": bool(raw.get("require_generator_provenance", False)),
        "requireVisualCastVerificationForVideo": bool(
            raw.get("require_visual_cast_verification_for_video", False)
        ),
        "humanReviewRequired": bool(raw.get("human_review_required", True)),
        "pilotFirst": bool(raw.get("pilot_first", False)),
        "pilotTakeIds": [
            str(item).strip()
            for item in raw.get("pilot_takes", [])
            if str(item).strip()
        ] if isinstance(raw.get("pilot_takes"), list) else [],
        "remainingBatchRequiresPilotHumanApproval": bool(
            raw.get("remaining_batch_requires_pilot_human_approval", False)
        ),
        "directionDocument": str(raw.get("direction_document") or ""),
        "controlSurface": str(raw.get("control_surface") or "maestro_anchor_executor"),
        "configuredAt": str(raw.get("configured_at") or ""),
    }


def project_view(project_dir: Path) -> dict[str, Any]:
    manifest = _read_json(project_dir / "project_manifest.json")
    queue = _queue(project_dir)
    takes = [
        item
        for item in queue.get("takes", [])
        if isinstance(item, dict)
        and str(item.get("role") or "").strip().lower() != "project_final_output"
    ]
    counts = {
        "planned": len(takes), "inProduction": 0, "approved": 0, "rejected": 0, "final": 0,
        "upscaling": 0, "directorPending": 0,
    }
    for take in takes:
        # The catalog only needs persisted status and the latest request. Full
        # take views validate anchors and inspect preview files; doing that for
        # every project delayed the catalog beyond the browser's timeout.
        status = _take_status(take)
        if status == "APPROVED":
            counts["approved"] += 1
        elif status in {"IN_PRODUCTION", "QUEUED", "GENERATING"}:
            counts["inProduction"] += 1
        elif status == "UPSCALING":
            counts["upscaling"] += 1
        elif status == "REJECTED":
            counts["rejected"] += 1
        elif status == "FINAL":
            counts["final"] += 1
        request = _director_request_view(_latest_director_request(take))
        if isinstance(request, dict) and request.get("status") in {"PENDING", "IN_PROGRESS"}:
            counts["directorPending"] += 1
    manifest_path = project_dir / "project_manifest.json"
    queue_path = project_dir / "take_queue.json"
    stat = manifest_path.stat() if manifest_path.exists() else project_dir.stat()
    created = str(manifest.get("created_at") or datetime.fromtimestamp(stat.st_ctime, timezone.utc).astimezone().isoformat(timespec="seconds"))
    updated_mtime = max(
        stat.st_mtime,
        queue_path.stat().st_mtime if queue_path.exists() else stat.st_mtime,
    )
    updated = datetime.fromtimestamp(updated_mtime, timezone.utc).astimezone().isoformat(timespec="seconds")
    status = str(manifest.get("maestro_status") or manifest.get("status") or "IN_PROGRESS").upper()
    if status not in PROJECT_STATUSES:
        status = "IN_PROGRESS"
    def _video_profile(resolution_key: str, fps_key: str, default_width: int, default_height: int, default_fps: int) -> dict[str, Any]:
        width, height = default_width, default_height
        resolution = str(manifest.get(resolution_key) or "").strip().lower()
        match = re.fullmatch(r"(\d{2,5})x(\d{2,5})", resolution)
        if match:
            parsed_width, parsed_height = int(match.group(1)), int(match.group(2))
            if parsed_width > 0 and parsed_height > 0:
                width, height = parsed_width, parsed_height
        try:
            fps = int(manifest.get(fps_key) or default_fps)
        except (TypeError, ValueError):
            fps = default_fps
        if fps <= 0 or fps > 240:
            fps = default_fps
        return {"width": width, "height": height, "fps": fps}

    assembly_readiness = _assembly_readiness(project_dir, queue)
    return {
        "projectId": project_dir.name,
        "name": str(manifest.get("title") or manifest.get("name") or project_dir.name.replace("_", " ").title()),
        "objective": str(manifest.get("objective") or ""),
        "distributionIntent": internet_publication.intent_view(manifest.get("distribution_intent")),
        "status": status,
        "createdAt": created,
        "updatedAt": updated,
        "durationSeconds": float(manifest.get("duration_target_seconds") or 0),
        "preview": _video_profile("preview_resolution", "fps_preview", 1280, 720, 30),
        "final": _video_profile("final_resolution", "fps_final", 1920, 1080, 60),
        "finalOutput": _project_final_output_view(
            project_dir,
            manifest,
            source_fingerprint=assembly_readiness["sourceFingerprint"],
            assembly_ready=assembly_readiness["ready"],
        ),
        "candidateOutput": _project_candidate_output_view(project_dir, manifest),
        "assemblyReadiness": assembly_readiness,
        "takeCounts": counts,
        "audio": {
            "musicProvider": (manifest.get("audio") or {}).get("music_provider") if isinstance(manifest.get("audio"), dict) else None,
            "voiceProvider": (manifest.get("audio") or {}).get("voice_provider") if isinstance(manifest.get("audio"), dict) else None,
        },
        "productionBatch": _story_batch_policy_view(queue),
        "anchorGeneration": _anchor_generation_policy_view(queue),
    }


def list_projects(root: Path, *, page: int = 1, page_size: int = 20, status: str = "") -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    wanted = status.strip().upper()
    if wanted and wanted not in PROJECT_STATUSES:
        raise ValueError("status de projeto invalido.")
    projects = []
    for project_dir in root.iterdir():
        if not project_dir.is_dir() or not PROJECT_ID_RE.fullmatch(project_dir.name):
            continue
        if not (project_dir / "project_manifest.json").exists() and not (project_dir / "take_queue.json").exists():
            continue
        view = project_view(project_dir)
        if not wanted or view["status"] == wanted:
            projects.append(view)
    projects.sort(key=lambda item: item["updatedAt"], reverse=True)
    total = len(projects)
    start = (page - 1) * page_size
    return {
        "data": projects[start:start + page_size],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": max(1, (total + page_size - 1) // page_size),
        },
    }


def get_project(root: Path, project_id: str) -> dict[str, Any]:
    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    return project_view(project_dir)


def list_takes(root: Path, project_id: str, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    data = [
        _take_view(item, project_dir)
        for item in _queue(project_dir).get("takes", [])
        if isinstance(item, dict)
        and str(item.get("role") or "").strip().lower() != "project_final_output"
        and item.get("visible_in_maestro", True) is not False
    ]
    start = (page - 1) * page_size
    return {
        "data": data[start:start + page_size],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": len(data),
            "totalPages": max(1, (len(data) + page_size - 1) // page_size),
        },
    }


def list_director_requests(
    root: Path,
    *,
    page: int = 1,
    page_size: int = 50,
    status: str = "",
) -> dict[str, Any]:
    """List the latest take requests so a director process can poll one canonical inbox."""

    root.mkdir(parents=True, exist_ok=True)
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    wanted = str(status or "").strip().upper()
    if wanted and wanted != "ALL" and wanted not in DIRECTOR_REQUEST_STATUSES:
        raise ValueError("status de solicitacao ao diretor invalido.")
    active_statuses = {"PENDING", "IN_PROGRESS"}
    requests: list[dict[str, Any]] = []
    for project_dir in root.iterdir():
        if not project_dir.is_dir() or not PROJECT_ID_RE.fullmatch(project_dir.name):
            continue
        if not (project_dir / "project_manifest.json").exists() and not (project_dir / "take_queue.json").exists():
            continue
        manifest = _read_json(project_dir / "project_manifest.json")
        project_name = str(manifest.get("title") or manifest.get("name") or project_dir.name.replace("_", " ").title())
        for take in _queue(project_dir).get("takes", []):
            if not isinstance(take, dict):
                continue
            request = _director_request_view(_latest_director_request(take))
            if request is None:
                continue
            request_status = request["status"]
            if wanted == "ALL":
                pass
            elif wanted:
                if request_status != wanted:
                    continue
            elif request_status not in active_statuses:
                continue
            take_view = _take_view(take, project_dir)
            requests.append({
                **request,
                "projectId": project_dir.name,
                "projectName": project_name,
                "takeId": take_view["takeId"],
                "takeName": take_view["name"],
                "takeStatus": take_view["status"],
                "hasPreview": take_view["hasPreview"],
                "previewFile": take_view["previewFile"],
            })
    requests.sort(key=lambda item: item.get("updatedAt") or item.get("createdAt") or "", reverse=True)
    total = len(requests)
    start = (page - 1) * page_size
    return {
        "data": requests[start:start + page_size],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": max(1, (total + page_size - 1) // page_size),
        },
    }


def create_project(
    root: Path,
    *,
    name: str,
    project_id: str = "",
    objective: str = "",
    duration_seconds: float = 60,
    distribution_mode: str = "auto",
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    name = (name or "").strip()
    if not 3 <= len(name) <= 120:
        raise ValueError("name deve ter entre 3 e 120 caracteres.")
    project_id = _validate_project_id(project_id) if project_id else slugify(name)
    duration = float(duration_seconds)
    if not 1 <= duration <= 7200:
        raise ValueError("durationSeconds deve ficar entre 1 e 7200.")
    objective = internet_publication._text(objective, "objective", 2000)
    distribution_intent = internet_publication.detect_intent(
        name + "\n" + objective, mode=distribution_mode, platforms=platforms,
    )
    project_dir = _project_path(root, project_id)
    if project_dir.exists():
        raise FileExistsError(project_id)
    project_dir.mkdir(parents=True)
    for folder in PROJECT_DIRS:
        (project_dir / folder).mkdir()
    now = utc_now()
    manifest = {
        "schema_version": "1.1",
        "project_id": project_id,
        "title": name,
        "objective": (objective or "").strip(),
        "distribution_intent": distribution_intent,
        "duration_target_seconds": duration,
        "preview_resolution": "1280x720",
        "final_resolution": "1920x1080",
        "fps_preview": 30,
        "fps_final": 60,
        "created_at": now,
        "updated_at": now,
        "maestro_status": "PLANNED",
        "audio": {"music_provider": None, "voice_provider": None},
        "take_queue": "take_queue.json",
    }
    _atomic_json_write(project_dir / "project_manifest.json", manifest)
    _atomic_json_write(project_dir / "take_queue.json", _queue(project_dir))
    return project_view(project_dir)


def patch_project(root: Path, project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    with _QUEUE_MUTATION_LOCK:
        return _patch_project_locked(root, project_id, updates)


def _patch_project_locked(root: Path, project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    allowed = {"name", "objective", "status", "finalResolution", "distributionMode", "platforms", "publicationBrief"}
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
    manifest_path = project_dir / "project_manifest.json"
    manifest = _read_json(manifest_path)
    if "name" in updates:
        name = str(updates["name"] or "").strip()
        if not 3 <= len(name) <= 120:
            raise ValueError("name deve ter entre 3 e 120 caracteres.")
        manifest["title"] = name
    if "objective" in updates:
        manifest["objective"] = str(updates["objective"] or "").strip()[:2000]
    if {"objective", "distributionMode", "platforms", "publicationBrief"} & set(updates):
        previous_intent = manifest.get("distribution_intent") or {}
        detection = internet_publication.detect_intent(
            internet_publication._text(updates["publicationBrief"], "publicationBrief", 8000)
            if "publicationBrief" in updates else manifest.get("objective") or "",
            mode=updates.get("distributionMode", "auto"),
            platforms=updates.get("platforms", previous_intent.get("platforms", [])),
        )
        if "distributionMode" in updates or detection["reason"] != "no_explicit_intent" or not previous_intent:
            manifest["distribution_intent"] = detection
        elif "platforms" in updates:
            previous_intent["platforms"] = detection["platforms"]
            manifest["distribution_intent"] = previous_intent
    if "status" in updates:
        status = str(updates["status"] or "").upper()
        if status not in PROJECT_STATUSES:
            raise ValueError("status de projeto invalido.")
        manifest["maestro_status"] = status
    if "finalResolution" in updates:
        final_resolution = str(updates["finalResolution"] or "").strip().lower()
        if final_resolution not in {"1920x1080", "1080x1920", "2560x1440", "1440x2560", "3840x2160", "2160x3840"}:
            raise ValueError(
                "finalResolution deve selecionar FHD, QHD ou UHD, em paisagem ou retrato."
            )
        manifest["final_resolution"] = final_resolution
        manifest["fps_final"] = 60
    manifest["updated_at"] = utc_now()
    _atomic_json_write(manifest_path, manifest)
    return project_view(project_dir)


def patch_take(root: Path, project_id: str, take_id: str, updates: dict[str, Any], *, defer_exports: bool = False) -> dict[str, Any]:
    with _QUEUE_MUTATION_LOCK:
        return _patch_take_locked(root, project_id, take_id, updates, defer_exports=defer_exports)


def _patch_take_locked(root: Path, project_id: str, take_id: str, updates: dict[str, Any], *, defer_exports: bool = False) -> dict[str, Any]:
    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    allowed = {
        "status", "notes", "animationPrompt", "directorRequest", "h3LivePreview",
        "takeMode", "continuityContract", "generationProfile",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Campos nao permitidos: {', '.join(sorted(unknown))}")
    queue_path = _queue_path(project_dir)
    queue = _queue(project_dir)
    take = next((item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id), None)
    if take is None:
        raise FileNotFoundError(take_id)
    if "generationProfile" in updates:
        if _take_status(take) in {"QUEUED", "GENERATING", "UPSCALING"}:
            raise ValueError("Nao altere o motor enquanto o take esta em execucao.")
        profile = str(updates["generationProfile"] or "").strip().lower()
        if profile not in {MINIMAX_H3_PROFILE}:
            raise ValueError("generationProfile deve selecionar MiniMax H3.")
        duration = float(take.get("target_duration_seconds") or 6.0)
        generation = (
            take.get("video_generation")
            if isinstance(take.get("video_generation"), dict)
            else {}
        )
        if profile == LTX25_TWO_ANCHOR_PROFILE:
            frames = max(25, min(721, int(round((min(30.0, duration) * 24) / 8)) * 8 + 1))
            generation.update({
                "profile": profile,
                "engine_selection_required": False,
                "fallback_allowed": False,
                "backend": "comfy_ltxvideo_official_2_5",
                "text_encoder": "gemma_3_12B_it_fp4_mixed.safetensors",
                "conditioning_profile": "identity_locked",
                "width": 960,
                "height": 544,
                "fps": 24,
                "frames": frames,
                "steps": 8,
                "guidance": 1.0,
                "maestro_job_enabled": True,
            })
        else:
            frames = max(124, min(362, int(round((min(15.0, duration) * 24 - 5) / 17)) * 17 + 5))
            generation.update({
                "profile": profile,
                "engine_selection_required": False,
                "fallback_allowed": False,
                "backend": "comfy_core_minimax_h3_nodes",
                "text_encoder": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
                "conditioning_profile": "identity_locked",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": frames,
                "steps": 20,
                "guidance": 1.0,
                "maestro_job_enabled": True,
            })
        take["video_generation"] = generation
    requested_status = None
    if "status" in updates:
        status = str(updates["status"] or "").upper()
        if status not in TAKE_STATUSES:
            raise ValueError("status de take invalido.")
        if status == "UPSCALING":
            raise ValueError("Use o botao de upscale para iniciar o pipeline 1080p.")
        requested_status = status
    director_payload = updates.get("directorRequest")
    director_reason = (
        str(director_payload.get("reason") or "").strip()
        if isinstance(director_payload, dict)
        else ""
    )
    director_category = _director_audio_category(
        str(director_payload.get("category") or "") if isinstance(director_payload, dict) else "",
        director_reason,
    )
    audio_sync_rejection = bool(
        requested_status == "REJECTED" and director_category == "AUDIO_SYNC"
    )
    audio_voice_rejection = bool(
        requested_status == "REJECTED" and director_category == "AUDIO_VOICE"
    )
    ptpt_voice_rejection = bool(
        audio_voice_rejection and _is_ptpt_voice_rejection(director_reason)
    )
    video_contract = take.get("video") if isinstance(take.get("video"), dict) else {}
    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    audio_delivery = (
        video_contract.get("audio_delivery")
        if isinstance(video_contract.get("audio_delivery"), dict)
        else {}
    )
    audio_delivery_status = str(audio_delivery.get("status") or "").upper()
    audio_required = bool(
        audio_direction.get("delivery_required")
        or (
            isinstance(take.get("dialogue_tracks"), list)
            and any(isinstance(item, dict) for item in take.get("dialogue_tracks", []))
        )
    )
    audio_attached = bool(
        audio_delivery_status.startswith("ATTACHED_")
        or audio_delivery_status.startswith("NATIVE_")
        or audio_delivery_status.startswith("APPROVED_")
    )
    if audio_sync_rejection or audio_voice_rejection:
        now = utc_now()
        rejected_deliveries = audio_direction.setdefault("rejected_deliveries", [])
        if not isinstance(rejected_deliveries, list):
            rejected_deliveries = []
            audio_direction["rejected_deliveries"] = rejected_deliveries
        rejection = {
            "id": uuid.uuid4().hex,
            "category": director_category,
            "reason": director_reason,
            "status": "REJECTED_HUMAN_QC",
            "rejected_at": now,
            "source": str(audio_delivery.get("source") or ""),
            "source_sha256": str(audio_delivery.get("source_sha256") or ""),
            "source_kind": str(audio_delivery.get("source_kind") or ""),
            "output": str(audio_delivery.get("output") or video_contract.get("output_active") or ""),
            "output_sha256": str(audio_delivery.get("output_sha256") or ""),
        }
        rejected_deliveries.append(rejection)
        del rejected_deliveries[:-20]
        audio_direction["delivery_required"] = True
        audio_direction["human_listening_required"] = True
        audio_direction["human_listening_completed"] = False
        audio_direction["voice_qc_status"] = "rejected_human_sync" if audio_sync_rejection else "rejected_human_voice"
        if audio_sync_rejection:
            generation_contract = (
                take.get("video_generation")
                if isinstance(take.get("video_generation"), dict)
                else {}
            )
            generation_profile = str(
                generation_contract.get("profile") or ""
            ).strip().lower()
            is_minimax_h3 = generation_profile in MINIMAX_H3_GENERATION_PROFILES
            is_ltx25 = False  # LTX removed; historical files and profiles remain readable.
            if is_minimax_h3 or is_ltx25:
                # Keep the selected visual engine. Lip/voice repair is a
                # project-local post-picture pass until an explicitly tested
                # native-audio workflow for that engine is selected.
                audio_direction["strategy"] = "external_pt_br_mix_after_video_qc"
                audio_direction["dialogue_generation_authorized"] = False
                audio_direction["visual_pass_mouths"] = (
                    "preserve_selected_engine_picture; approved_ptbr_audio_is_muxed_after_visual_qc"
                )
                audio_direction["native_visual_audio"] = (
                    "forbidden_preserve_approved_project_mix_and_natural_voice_timing"
                )
            else:
                audio_direction["strategy"] = "external_adr_after_visual_qc"
                audio_direction["dialogue_generation_authorized"] = False
            audio_direction["audio_sync_revision"] = int(audio_direction.get("audio_sync_revision") or 0) + 1
            audio_direction["spoken_language_policy"] = (
                "EXTERNAL_PTBR_REPAIR_AFTER_VISUAL_QC; preserve the selected engine and approved picture; "
                "exact Brazilian Portuguese pt-BR; pt-PT, added words and off-sync delivery are forbidden"
            )
        else:
            audio_direction["strategy"] = "external_adr_after_visual_qc"
            audio_direction["dialogue_generation_authorized"] = False
            if ptpt_voice_rejection:
                audio_direction["voice_locale_revision"] = int(
                    audio_direction.get("voice_locale_revision") or 0
                ) + 1
                audio_direction["spoken_language_policy"] = (
                    "EXTERNAL_QWEN_PTBR_AFTER_VISUAL_QC; use registered voice profiles; "
                    "exact Brazilian Portuguese pt-BR; native retry and pt-PT are forbidden"
                )
            audio_direction["audio_voice_revision"] = int(audio_direction.get("audio_voice_revision") or 0) + 1
        audio_delivery["status"] = (
            "REJECTED_HUMAN_AUDIO_SYNC" if audio_sync_rejection else "REJECTED_HUMAN_VOICE_QC"
        )
        audio_delivery["human_listening_required"] = True
        audio_delivery["rejected_at"] = now
        audio_delivery["rejection_reason"] = director_reason
        audio_delivery["message"] = (
            "Sincronismo reprovado; preservar o motor e o video selecionados e reconstruir a faixa pt-BR na duracao editorial."
            if audio_sync_rejection
            and str(audio_direction.get("strategy") or "")
            == "external_pt_br_mix_after_video_qc"
            else "Sincronismo audiovisual reprovado; corrigir a faixa externa sem trocar de motor."
            if audio_sync_rejection
            else "Voz pt-PT reprovada; a proxima faixa externa usara vozes Qwen pt-BR por personagem."
            if ptpt_voice_rejection
            else "Voz/som reprovado; a faixa rejeitada nao pode ser reutilizada."
        )
        video_contract["audio_delivery"] = audio_delivery
        video_contract["route_status"] = (
            "AUDIO_SYNC_REJECTED_H3_EXTERNAL_MIX_REPAIR_REQUIRED"
            if audio_sync_rejection
            and str(audio_direction.get("strategy") or "")
            == "external_pt_br_mix_after_video_qc"
            else "AUDIO_SYNC_REJECTED_EXTERNAL_MIX_REPAIR_REQUIRED"
            if audio_sync_rejection
            else "AUDIO_LOCALE_REJECTED_EXTERNAL_QWEN_REPAIR_REQUIRED"
            if ptpt_voice_rejection
            else "AUDIO_VOICE_REJECTED_REPLACEMENT_REQUIRED"
        )
        take["audio_direction"] = audio_direction
        qc = take.setdefault("qc", {})
        if isinstance(qc, dict):
            qc["status"] = (
                "audio_sync_rejected_h3_external_mix_repair_required"
                if audio_sync_rejection
                and str(audio_direction.get("strategy") or "")
                == "external_pt_br_mix_after_video_qc"
                else "audio_sync_rejected_external_mix_repair_required"
                if audio_sync_rejection
                else "audio_locale_rejected_external_qwen_repair_required"
                if ptpt_voice_rejection
                else "audio_voice_rejected_replacement_required"
            )
            qc["audio_rejection"] = rejection
    if requested_status == "APPROVED" and audio_required and not audio_attached:
        # A decisao do proprietario sobre a imagem nunca deve ser recusada so
        # porque a pos-producao sonora ainda nao terminou.  Registre a
        # aprovacao como visual e mantenha o audio explicitamente pendente; a
        # faixa, quando anexada, continua exigindo sua propria escuta humana.
        now = utc_now()
        audio_delivery.update({
            "status": "VISUAL_APPROVED_AUDIO_PENDING",
            "required": True,
            "ready": False,
            "human_listening_required": True,
            "visual_approved_at": now,
            "message": (
                "Imagem aprovada pelo proprietario; ambiente/efeitos e voz pt-BR "
                "continuam pendentes para a montagem audiovisual."
            ),
        })
        video_contract["audio_delivery"] = audio_delivery
        audio_direction["delivery_required"] = True
        audio_direction["human_listening_required"] = True
        audio_direction["human_listening_completed"] = False
        audio_direction["voice_qc_status"] = "visual_approved_audio_pending"
        take["audio_direction"] = audio_direction
        take["video"] = video_contract
        qc = take.setdefault("qc", {})
        if isinstance(qc, dict):
            qc["status"] = "approved_visual_audio_pending"
    pending_upscale_candidate = _upscale_candidate_record(take)
    pending_upscale_review = bool(
        pending_upscale_candidate is not None
        and str(pending_upscale_candidate.get("status") or "").upper()
        == "PENDING_HUMAN_REVIEW"
    )
    if (
        pending_upscale_review
        and requested_status is not None
        and requested_status not in {"APPROVED", "REJECTED"}
    ):
        raise ValueError(
            "Decida o candidato FHD pendente antes de alterar o status do take."
        )
    if "notes" in updates:
        take["maestro_notes"] = str(updates["notes"] or "").strip()[:4000]
    if "takeMode" in updates:
        take_mode = str(updates["takeMode"] or "").strip().upper()
        if take_mode not in TAKE_MODES:
            raise ValueError("takeMode deve ser PRECISION, ACTION ou PAYOFF.")
        take["take_mode"] = take_mode.lower()
    if "continuityContract" in updates:
        take["continuity_contract"] = _normalize_continuity_contract(
            updates["continuityContract"]
        )
    if "animationPrompt" in updates:
        animation_prompt = str(updates["animationPrompt"] or "").strip()
        if not 20 <= len(animation_prompt) <= 6000:
            raise ValueError("animationPrompt deve ter entre 20 e 6000 caracteres.")
        prohibited_positive_terms = {
            "visible text": "texto visivel",
            "subtitle": "legenda",
            "caption": "legenda",
            "watermark": "marca-d'agua",
            " logo": "logo",
            "interface": "interface",
            "pt-pt": "portugues de Portugal",
            "portugal": "portugues de Portugal",
        }
        normalized_prompt = f" {animation_prompt.casefold()} "
        violation = next(
            (
                label
                for term, label in prohibited_positive_terms.items()
                if term in normalized_prompt
            ),
            "",
        )
        if re.search(r"(?<![a-z0-9])ui(?![a-z0-9])", normalized_prompt):
            violation = violation or "interface"
        if violation:
            raise ValueError(
                f"Prompt positivo bloqueado: mencao a {violation}. "
                "Esses conceitos ficam somente no gate automatico, nunca no prompt do LTX."
            )
        take["animation_prompt"] = animation_prompt
    if "h3LivePreview" in updates:
        if _take_status(take) in {"QUEUED", "GENERATING", "UPSCALING"}:
            raise ValueError("Nao altere o preview H3 enquanto o take esta em execucao.")
        generation = (
            take.get("video_generation")
            if isinstance(take.get("video_generation"), dict)
            else {}
        )
        profile = str(generation.get("profile") or "").strip().lower()
        if profile not in MINIMAX_H3_GENERATION_PROFILES:
            raise ValueError("Preview ao vivo KJNodes e exclusivo dos perfis MiniMax H3.")
        generation["h3_live_preview"] = bool(updates["h3LivePreview"])
        take["video_generation"] = generation
    upscale_review_handled = False
    if requested_status in {"APPROVED", "REJECTED"}:
        decision_reason = (
            str(updates.get("notes") or "").strip()
            or director_reason
            or f"Decisao humana {requested_status.lower()} no Maestro."
        )[:2000]
        upscale_review_handled = _review_pending_upscale_candidate(
            project_dir,
            take,
            decision=requested_status,
            reason=decision_reason,
        )
    if requested_status and not (upscale_review_handled and requested_status == "REJECTED"):
        take["maestro_status"] = requested_status
        if requested_status == "APPROVED":
            now = utc_now()
            qc = take.setdefault("qc", {})
            if isinstance(qc, dict):
                qc["human_visual_approval"] = "approved"
                qc["visual_approved_at"] = now
                if audio_attached:
                    qc["status"] = "approved_human_listening"
                elif not audio_required:
                    qc["status"] = "approved_by_owner"
                motion_gate = qc.get("transition_motion_gate")
                if isinstance(motion_gate, dict):
                    motion_gate["status"] = "approved_by_owner"
        if requested_status == "APPROVED" and audio_attached:
            now = utc_now()
            audio_delivery["status"] = "APPROVED_HUMAN_LISTENING"
            audio_delivery["human_listening_required"] = False
            audio_delivery["approved_at"] = now
            audio_delivery["message"] = "Audio e imagem aprovados na revisao humana do Maestro."
            video_contract["audio_delivery"] = audio_delivery
            audio_direction["human_listening_required"] = False
            audio_direction["human_listening_completed"] = True
            audio_direction["voice_qc_status"] = "approved_human_listening"
    if "directorRequest" in updates:
        payload = updates["directorRequest"]
        if not isinstance(payload, dict):
            raise ValueError("directorRequest deve ser um objeto.")
        unknown_request_fields = set(payload) - {"category", "reason", "renderInstruction"}
        if unknown_request_fields:
            raise ValueError(f"Campos de directorRequest nao permitidos: {', '.join(sorted(unknown_request_fields))}")
        category = director_category
        reason = str(payload.get("reason") or "").strip()
        render_instruction = str(payload.get("renderInstruction") or "").strip()
        if category not in DIRECTOR_REQUEST_CATEGORIES:
            raise ValueError("Categoria de correcao invalida.")
        if not 3 <= len(reason) <= 2000:
            raise ValueError("O motivo deve ter entre 3 e 2000 caracteres.")
        if render_instruction and not 20 <= len(render_instruction) <= 2000:
            raise ValueError("renderInstruction deve ter entre 20 e 2000 caracteres.")
        is_anchor_request = category == "ANCHOR"
        if is_anchor_request:
            take_view = _take_view(take, project_dir)
            if requested_status is not None:
                raise ValueError("Pedido de imagem-ancora nao altera o status do take.")
            if not take_view.get("canRequestAnchor"):
                raise ValueError("Pedido de foto-base exige um take planejado sem base aprovada.")
        elif requested_status not in {None, "REJECTED"} or (requested_status is None and _take_status(take) != "REJECTED"):
            raise ValueError("Enviar ao diretor exige que o take esteja reprovado.")
        previous_request = _latest_director_request(take)
        if previous_request is not None and str(previous_request.get("status") or "").upper() in {"PENDING", "IN_PROGRESS"}:
            _set_latest_director_request_status(take, "SUPERSEDED")
        now = utc_now()
        director_requests = take.setdefault("maestro_director_requests", [])
        if not isinstance(director_requests, list):
            director_requests = []
            take["maestro_director_requests"] = director_requests
        director_request_record = {
            "id": uuid.uuid4().hex,
            "status": "PENDING",
            "category": category,
            "reason": reason,
            "created_at": now,
            "updated_at": now,
        }
        if render_instruction:
            director_request_record["render_instruction"] = render_instruction
        director_requests.append(director_request_record)
        if not is_anchor_request:
            take["maestro_status"] = "REJECTED"
            qc = take.setdefault("qc", {})
            if isinstance(qc, dict) and not (audio_sync_rejection or audio_voice_rejection):
                qc["status"] = "user_rejected_director_pending"
    elif requested_status and requested_status != "REJECTED":
        latest_request = _latest_director_request(take)
        if latest_request is not None and str(latest_request.get("status") or "").upper() in {"PENDING", "IN_PROGRESS"}:
            _set_latest_director_request_status(take, "CANCELLED")
    take["maestro_updated_at"] = utc_now()
    if upscale_review_handled:
        reviewed_candidate = _upscale_candidate_record(take)
        if reviewed_candidate is None:
            raise ValueError("Candidato de upscale revisado nao foi preservado no contrato.")
        _persist_upscale_candidate_human_decision(project_dir, reviewed_candidate)
    _atomic_json_write(queue_path, queue)
    if requested_status is not None:
        try:
            if defer_exports:
                request_ready_exports_sync(project_dir, queue_path=queue_path)
            else:
                sync_project_ready_exports(project_dir, queue_path=queue_path)
        except Exception:
            logging.exception(
                "Falha ao sincronizar a pasta central PRONTOS apos atualizar %s/%s.",
                project_id,
                take_id,
            )
    return _take_view(take, project_dir)


def register_anchor_candidate(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    request_id: str,
    image_bytes: bytes,
    original_filename: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Persist one director-delivered anchor without granting video approval."""

    required_objects = (
        metadata.get("requiredObjects")
        if isinstance(metadata.get("requiredObjects"), dict)
        else metadata.get("required_objects")
        if isinstance(metadata.get("required_objects"), dict)
        else {}
    )
    if str(required_objects.get("anchorSide") or required_objects.get("anchor_side") or "").strip().lower() == "end":
        return register_end_anchor_candidate(
            root,
            project_id,
            take_id,
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename=original_filename,
            metadata=metadata,
        )

    request_id = _validate_anchor_request_id(request_id)
    take_id = _validate_take_id(take_id)
    original_name = str(original_filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_name or Path(original_name).suffix.lower() != ".png":
        raise ValueError("O candidato de imagem-ancora deve usar nome de arquivo .png.")
    original_name = original_name[:240]
    image_info = _validate_anchor_png(image_bytes)
    normalized_metadata = _normalize_anchor_metadata(metadata)
    image_sha256 = hashlib.sha256(image_bytes).hexdigest()
    source_sha256 = normalized_metadata.get("source_sha256") or image_sha256
    if source_sha256.lower() != image_sha256:
        raise ValueError("metadata.sourceSha256 nao corresponde ao PNG enviado.")

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        queue_path = _queue_path(project_dir)
        queue = _queue(project_dir)
        take = _take_record(queue, take_id)
        request = _anchor_request(take, request_id)
        latest_request = _latest_director_request(take)
        base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
        request_status = str(request.get("status") or "PENDING").upper()
        image_path, metadata_path = _anchor_candidate_paths(project_dir, take, request_id)
        metadata_sha256 = _anchor_delivery_metadata_sha256(
            normalized_metadata,
            take,
            image_sha256,
        )

        if request_status == "DELIVERED":
            existing_sidecar = _read_json(metadata_path)
            existing_decision = str(request.get("review_decision") or "").upper()
            queue_candidate_matches = (
                str(base.get("candidate_request_id") or "").lower() == request_id
                and str(base.get("image_sha256") or "").lower() == image_sha256
                and Path(str(base.get("file") or "")).resolve() == image_path
                and Path(str(base.get("metadata") or "")).resolve() == metadata_path
            )
            rejected_and_restored = existing_decision == "REJECTED"
            if (
                (queue_candidate_matches or rejected_and_restored)
                and str(request.get("candidate_sha256") or "").lower() == image_sha256
                and str(request.get("candidate_metadata_sha256") or "").lower() == metadata_sha256
                and image_path.is_file()
                and metadata_path.is_file()
                and hashlib.sha256(image_path.read_bytes()).hexdigest() == image_sha256
                and str(existing_sidecar.get("director_request_id") or "").lower() == request_id
                and str(existing_sidecar.get("image_sha256") or "").lower() == image_sha256
                and str(existing_sidecar.get("delivery_metadata_sha256") or "").lower() == metadata_sha256
            ):
                view = _take_view(take, project_dir)
                view["anchorCandidate"] = {
                    "requestId": request_id,
                    "status": str(existing_sidecar.get("validation_status") or ""),
                    "file": image_path.name,
                    "metadataFile": metadata_path.name,
                    "sha256": image_sha256,
                    "anchorSide": "start",
                    **image_info,
                    "deliveredAt": str(request.get("delivered_at") or request.get("updated_at") or ""),
                }
                return view
            raise AnchorConflictError("Este pedido ja possui outra entrega registrada.")
        if request_status not in {"PENDING", "IN_PROGRESS"}:
            raise AnchorConflictError("O pedido de imagem-ancora nao esta ativo para entrega.")
        if latest_request is not request:
            raise AnchorConflictError("O requestId nao corresponde ao pedido mais recente deste take.")
        if not _take_can_request_anchor(project_dir, take):
            raise AnchorConflictError(
                "O take nao esta mais planejado sem uma foto-base aprovada."
            )
        if image_path.is_file() and hashlib.sha256(image_path.read_bytes()).hexdigest() != image_sha256:
            raise AnchorConflictError("O destino canonico ja contem outro candidato para este pedido.")
        if metadata_path.is_file():
            existing_metadata = _read_json(metadata_path)
            existing_status = str(existing_metadata.get("validation_status") or "").lower()
            if existing_status and existing_status != ANCHOR_PENDING_REVIEW_STATUS:
                raise AnchorConflictError("O sidecar canonico ja contem uma decisao humana.")

        now = utc_now()
        source_base_state = {
            field: base[field]
            for field in ("status", "file", "metadata", "model", "prompt")
            if field in base
        }
        source_approved_image = str(base.get("source_approved_image") or base.get("file") or "")
        source_approved_metadata = str(base.get("source_approved_metadata") or base.get("metadata") or "")
        sidecar: dict[str, Any] = {
            "schema_version": "1.0",
            "project_id": project_dir.name,
            "type": "anchor_candidate_metadata",
            "director_request_id": request_id,
            "take_id": take_id,
            "take_slug": str(take.get("slug") or take.get("name") or f"take_{take_id}"),
            "created_at": now,
            "image_file": image_path.as_posix(),
            "original_filename": original_name,
            "source_output": normalized_metadata.get("source_output") or "",
            "source_generated_at": normalized_metadata.get("source_generated_at") or "",
            "source_approved_image": source_approved_image,
            "source_sha256": image_sha256,
            "image_sha256": image_sha256,
            "delivery_metadata_sha256": metadata_sha256,
            "copy_integrity": "sha256_match",
            "model": normalized_metadata["model"],
            "seed": normalized_metadata.get("seed"),
            "generator": normalized_metadata.get("generator") or "",
            "workflow": normalized_metadata.get("workflow") or "",
            **image_info,
            "prompt": normalized_metadata["prompt"],
            "negative": normalized_metadata.get("negative") or "",
            "objective": normalized_metadata.get("objective") or str(take.get("objective") or ""),
            "required_objects": normalized_metadata.get("required_objects") or {},
            "validation_status": ANCHOR_PENDING_REVIEW_STATUS,
            "approval_required_before_video": True,
            "qc_checklist": [
                "imagem aberta e inspecionada em tamanho real",
                "proporcao 16:9 e largura minima de 1024 pixels",
                "prompt, modelo, dimensoes e hash registrados",
                "identidade, composicao e objetos conferidos",
                "sem texto, rosto, silhueta ou artefato proibido",
                "marcar approved_for_video somente apos decisao humana",
            ],
            "rejection_reasons": [],
        }

        _atomic_bytes_write(image_path, image_bytes)
        copied_sha256 = hashlib.sha256(image_path.read_bytes()).hexdigest()
        if copied_sha256 != image_sha256:
            image_path.unlink(missing_ok=True)
            raise OSError("Falha na verificacao SHA256 da copia da imagem-ancora.")
        _atomic_json_write(metadata_path, sidecar)

        base = take.setdefault("base_image", {})
        if not isinstance(base, dict):
            base = {}
            take["base_image"] = base
        base.update({
            "status": ANCHOR_PENDING_REVIEW_STATUS,
            "source_approved_image": source_approved_image,
            "source_approved_metadata": source_approved_metadata,
            "source_base_state": source_base_state,
            "file": image_path.as_posix(),
            "metadata": metadata_path.as_posix(),
            "model": normalized_metadata["model"],
            "prompt": normalized_metadata["prompt"],
            "candidate_request_id": request_id,
            "image_sha256": image_sha256,
            "delivered_at": now,
        })
        qc = take.setdefault("qc", {})
        if not isinstance(qc, dict):
            qc = {}
            take["qc"] = qc
        qc["status"] = "anchor_delivered_pending_user_approval"
        request["status"] = "DELIVERED"
        request["updated_at"] = now
        request["delivered_at"] = now
        request["candidate_file"] = image_path.name
        request["candidate_metadata_file"] = metadata_path.name
        request["candidate_sha256"] = image_sha256
        request["candidate_metadata_sha256"] = metadata_sha256
        take["maestro_updated_at"] = now
        queue["updated_at"] = now
        _invalidate_take_thumbnail(project_dir, take_id)
        _atomic_json_write(queue_path, queue)

        view = _take_view(take, project_dir)
        view["anchorCandidate"] = {
            "requestId": request_id,
            "status": ANCHOR_PENDING_REVIEW_STATUS,
            "file": image_path.name,
            "metadataFile": metadata_path.name,
            "sha256": image_sha256,
            "anchorSide": "start",
            **image_info,
            "deliveredAt": now,
        }
        return view


def register_end_anchor_candidate(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    request_id: str,
    image_bytes: bytes,
    original_filename: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Persist a final-frame candidate while preserving the approved start frame."""

    request_id = _validate_anchor_request_id(request_id)
    take_id = _validate_take_id(take_id)
    original_name = str(original_filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_name or Path(original_name).suffix.lower() != ".png":
        raise ValueError("O candidato de imagem-ancora deve usar nome de arquivo .png.")
    image_info = _validate_anchor_png(image_bytes)
    normalized_metadata = _normalize_anchor_metadata(metadata)
    image_sha256 = hashlib.sha256(image_bytes).hexdigest()
    source_sha256 = normalized_metadata.get("source_sha256") or image_sha256
    if source_sha256.lower() != image_sha256:
        raise ValueError("metadata.sourceSha256 nao corresponde ao PNG enviado.")

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        queue_path = _queue_path(project_dir)
        queue = _queue(project_dir)
        take = _take_record(queue, take_id)
        request = _anchor_request(take, request_id)
        if _latest_director_request(take) is not request:
            raise AnchorConflictError("O requestId nao corresponde ao pedido mais recente deste take.")
        if str(request.get("status") or "PENDING").upper() not in {"PENDING", "IN_PROGRESS"}:
            raise AnchorConflictError("O pedido de imagem-ancora nao esta ativo para entrega.")
        if _take_status(take) != "PLANNED" or _take_output_path(project_dir, take) is not None:
            raise AnchorConflictError("A segunda ancora so pode ser entregue antes da producao do take.")
        if _take_end_keyframe_path(project_dir, take) is not None:
            raise AnchorConflictError("Este take ja possui uma segunda ancora aprovada.")
        if _end_anchor_candidate_record(take):
            raise AnchorConflictError("Este take ja possui uma segunda ancora candidata.")

        image_path, metadata_path = _anchor_candidate_paths(project_dir, take, request_id)
        if image_path.is_file() or metadata_path.is_file():
            raise AnchorConflictError("O destino canonico ja contem outro candidato para este pedido.")
        metadata_sha256 = _anchor_delivery_metadata_sha256(
            normalized_metadata,
            take,
            image_sha256,
        )
        now = utc_now()
        sidecar: dict[str, Any] = {
            "schema_version": "1.0",
            "project_id": project_dir.name,
            "type": "anchor_candidate_metadata",
            "anchor_side": "end",
            "director_request_id": request_id,
            "take_id": take_id,
            "take_slug": str(take.get("slug") or take.get("name") or f"take_{take_id}"),
            "created_at": now,
            "image_file": image_path.as_posix(),
            "original_filename": original_name[:240],
            "source_output": normalized_metadata.get("source_output") or "",
            "source_generated_at": normalized_metadata.get("source_generated_at") or "",
            "source_approved_image": str(
                (take.get("base_image") or {}).get("file")
                if isinstance(take.get("base_image"), dict)
                else ""
            ),
            "source_sha256": image_sha256,
            "image_sha256": image_sha256,
            "delivery_metadata_sha256": metadata_sha256,
            "copy_integrity": "sha256_match",
            "model": normalized_metadata["model"],
            "seed": normalized_metadata.get("seed"),
            "generator": normalized_metadata.get("generator") or "",
            "workflow": normalized_metadata.get("workflow") or "",
            **image_info,
            "prompt": normalized_metadata["prompt"],
            "negative": normalized_metadata.get("negative") or "",
            "objective": normalized_metadata.get("objective") or str(take.get("objective") or ""),
            "required_objects": normalized_metadata.get("required_objects") or {},
            "validation_status": ANCHOR_PENDING_REVIEW_STATUS,
            "approval_required_before_video": True,
            "qc_checklist": [
                "imagem aberta e inspecionada em tamanho real",
                "proporcao 16:9 e largura minima de 1024 pixels",
                "identidade, composicao, Potara e objetos conferidos",
                "segunda ancora so ativa apos decisao humana",
            ],
            "rejection_reasons": [],
        }
        _atomic_bytes_write(image_path, image_bytes)
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != image_sha256:
            image_path.unlink(missing_ok=True)
            raise OSError("Falha na verificacao SHA256 da segunda ancora.")
        _atomic_json_write(metadata_path, sidecar)
        take["end_anchor_candidate"] = {
            "status": ANCHOR_PENDING_REVIEW_STATUS,
            "file": image_path.as_posix(),
            "metadata": metadata_path.as_posix(),
            "model": normalized_metadata["model"],
            "prompt": normalized_metadata["prompt"],
            "candidate_request_id": request_id,
            "image_sha256": image_sha256,
            "delivered_at": now,
        }
        qc = take.setdefault("qc", {})
        if not isinstance(qc, dict):
            qc = {}
            take["qc"] = qc
        qc["status"] = "anchor_delivered_pending_user_approval"
        request.update({
            "status": "DELIVERED",
            "updated_at": now,
            "delivered_at": now,
            "candidate_file": image_path.name,
            "candidate_metadata_file": metadata_path.name,
            "candidate_sha256": image_sha256,
            "candidate_metadata_sha256": metadata_sha256,
            "anchor_side": "end",
        })
        take["maestro_updated_at"] = now
        queue["updated_at"] = now
        _invalidate_take_thumbnail(project_dir, take_id)
        _atomic_json_write(queue_path, queue)
        return _take_view(take, project_dir)


def _inherit_approved_end_as_next_start(
    project_dir: Path,
    queue: dict[str, Any],
    source_take: dict[str, Any],
    *,
    image_path: Path,
    metadata_path: Path,
    image_sha256: str,
    inherited_at: str,
) -> str:
    policy = (
        queue.get("anchor_generation_policy")
        if isinstance(queue.get("anchor_generation_policy"), dict)
        else {}
    )
    if not bool(policy.get("inherit_approved_end_as_next_start", False)):
        return ""
    takes = queue.get("takes")
    if not isinstance(takes, list):
        return ""
    source_index = next(
        (index for index, item in enumerate(takes) if item is source_take),
        -1,
    )
    if source_index < 0 or source_index + 1 >= len(takes):
        return ""
    next_take = takes[source_index + 1]
    if not isinstance(next_take, dict):
        return ""
    next_take_id = str(next_take.get("id") or "").strip()
    if not next_take_id or _take_output_path(project_dir, next_take) is not None:
        return ""

    existing_base = (
        next_take.get("base_image")
        if isinstance(next_take.get("base_image"), dict)
        else {}
    )
    existing_path = _take_keyframe_path(project_dir, next_take)
    if _base_status_is_approved(existing_base.get("status")) and existing_path is not None:
        if existing_path != image_path.resolve():
            raise AnchorConflictError(
                f"O take {next_take_id} ja possui outra ancora inicial aprovada."
            )
        return next_take_id

    base = next_take.setdefault("base_image", {})
    if not isinstance(base, dict):
        base = {}
        next_take["base_image"] = base
    source_take_id = str(source_take.get("id") or "").strip()
    base.update({
        "status": ANCHOR_APPROVED_STATUS,
        "file": image_path.as_posix(),
        "metadata": metadata_path.as_posix(),
        "source_approved_image": image_path.as_posix(),
        "source_approved_metadata": metadata_path.as_posix(),
        "source_sha256": image_sha256,
        "model": "approved shared boundary from previous take",
        "inherited_from_take_id": source_take_id,
        "inherited_from_anchor_side": "end",
        "inherited_at": inherited_at,
        "approval_evidence": "Exact approved end anchor inherited as the next take start boundary.",
    })
    base.pop("candidate_request_id", None)

    shot = next_take.setdefault("shot_contract", {})
    if not isinstance(shot, dict):
        shot = {}
        next_take["shot_contract"] = shot
    refs = shot.setdefault("visual_references", {})
    if not isinstance(refs, dict):
        refs = {}
        shot["visual_references"] = refs
    refs.update({
        "start_frame_file": image_path.as_posix(),
        "start_frame_approved": True,
        "start_frame_approved_at": inherited_at,
        "start_frame_approval_source": "previous_take_approved_end_anchor",
        "start_frame_source_take_id": source_take_id,
    })
    keyframes = shot.setdefault("keyframes", {})
    if not isinstance(keyframes, dict):
        keyframes = {}
        shot["keyframes"] = keyframes
    keyframes["start"] = image_path.as_posix()
    keyframes["approved"] = bool(_take_end_keyframe_path(project_dir, next_take))

    requests = next_take.get("maestro_director_requests")
    if isinstance(requests, list):
        for request in requests:
            if not isinstance(request, dict):
                continue
            if str(request.get("category") or "").upper() != "ANCHOR":
                continue
            if str(request.get("anchor_side") or "start").strip().lower() == "end":
                continue
            if str(request.get("status") or "").upper() in {"PENDING", "IN_PROGRESS"}:
                request["status"] = "SUPERSEDED"
                request["updated_at"] = inherited_at
                request["superseded_by_shared_boundary_take_id"] = source_take_id

    next_take["maestro_updated_at"] = inherited_at
    _invalidate_take_thumbnail(project_dir, next_take_id)
    return next_take_id


def reconcile_shared_anchor_chain(root: Path, project_id: str) -> dict[str, Any]:
    """Repair opt-in take chains without changing any human anchor decision."""

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        queue_path = _queue_path(project_dir)
        queue = _queue(project_dir)
        inherited: list[dict[str, str]] = []
        now = utc_now()
        for take in queue.get("takes", []):
            if not isinstance(take, dict):
                continue
            record = _end_anchor_candidate_record(take)
            if str(record.get("status") or "").strip().lower() != ANCHOR_APPROVED_STATUS:
                continue
            image_path, metadata_path, _base, _sidecar, _info, image_sha256 = (
                _validated_registered_end_anchor(
                    project_dir,
                    take,
                    allowed_statuses={ANCHOR_APPROVED_STATUS},
                )
            )
            next_take_id = _inherit_approved_end_as_next_start(
                project_dir,
                queue,
                take,
                image_path=image_path,
                metadata_path=metadata_path,
                image_sha256=image_sha256,
                inherited_at=now,
            )
            if next_take_id:
                inherited.append({
                    "sourceTakeId": str(take.get("id") or ""),
                    "nextTakeId": next_take_id,
                    "sha256": image_sha256,
                })
        if inherited:
            queue["updated_at"] = now
            _atomic_json_write(queue_path, queue)
        return {"projectId": project_id, "inherited": inherited, "updatedAt": now}


def _review_end_anchor_candidate(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    decision: str,
    reason: str,
    request_id: str,
    actual_visible_characters: list[str] | None,
    human_confirmed: bool,
) -> dict[str, Any]:
    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        queue_path = _queue_path(project_dir)
        queue = _queue(project_dir)
        take = _take_record(queue, take_id)
        record = _end_anchor_candidate_record(take)
        candidate_request_id = _validate_anchor_request_id(
            str(record.get("candidate_request_id") or "")
        )
        if request_id != candidate_request_id:
            raise AnchorConflictError("requestId nao corresponde a segunda ancora registrada.")
        request = _anchor_request(take, request_id)
        if _latest_anchor_request_for_side(take, "end") is not request:
            raise AnchorConflictError(
                "O candidato nao pertence ao pedido final mais recente deste take."
            )
        if str(request.get("status") or "").upper() != "DELIVERED":
            raise AnchorConflictError("O pedido precisa estar DELIVERED antes da revisao humana.")
        existing_decision = str(request.get("review_decision") or "").upper()
        existing_reason = str(request.get("review_reason") or "")
        if existing_decision:
            if existing_decision != decision or existing_reason != reason:
                raise AnchorConflictError("Este candidato ja recebeu outra decisao humana.")
            view = _take_view(take, project_dir)
            view["anchorReview"] = {
                "requestId": request_id,
                "decision": existing_decision,
                "reason": existing_reason,
                "reviewedAt": str(request.get("reviewed_at") or ""),
            }
            return view
        if decision == "APPROVED" and not human_confirmed:
            anchor_policy = (
                queue.get("anchor_generation_policy")
                if isinstance(queue.get("anchor_generation_policy"), dict)
                else {}
            )
            if bool(anchor_policy.get("require_explicit_human_confirmation", False)):
                raise ValueError("Esta imagem exige confirmacao explicita da revisao humana.")

        image_path, metadata_path, _base, sidecar, image_info, image_sha256 = (
            _validated_registered_end_anchor(
                project_dir,
                take,
                allowed_statuses={ANCHOR_PENDING_REVIEW_STATUS},
            )
        )
        now = utc_now()
        validation_status = (
            ANCHOR_APPROVED_STATUS if decision == "APPROVED" else ANCHOR_REJECTED_STATUS
        )
        sidecar["validation_status"] = validation_status
        sidecar["reviewed_at"] = now
        sidecar["human_review"] = {
            "decision": decision,
            "reason": reason,
            "source": "maestro_anchor_review",
            "explicit_human_confirmation": bool(human_confirmed),
        }
        next_request_id = ""
        inherited_next_take_id = ""
        if decision == "APPROVED":
            sidecar["approval_evidence"] = reason or "Aprovado pela revisao humana do Maestro."
            if actual_visible_characters is not None:
                sidecar["visual_qc"] = {
                    "cast_verification_status": "VERIFIED",
                    "actual_visible_characters": actual_visible_characters,
                    "verified_at": now,
                    "source": "maestro_anchor_review",
                }
            record["status"] = ANCHOR_APPROVED_STATUS
            record["approved_at"] = now
            shot = take.setdefault("shot_contract", {})
            if not isinstance(shot, dict):
                shot = {}
                take["shot_contract"] = shot
            refs = shot.setdefault("visual_references", {})
            if not isinstance(refs, dict):
                refs = {}
                shot["visual_references"] = refs
            refs["end_frame_file"] = image_path.as_posix()
            refs["end_frame_approved"] = True
            refs["end_frame_approved_at"] = now
            refs["end_frame_approval_source"] = "maestro_anchor_review"
            keyframes = shot.setdefault("keyframes", {})
            if isinstance(keyframes, dict):
                keyframes["end"] = image_path.as_posix()
                keyframes["approved"] = bool(
                    _base_status_is_approved(
                        (take.get("base_image") or {}).get("status")
                        if isinstance(take.get("base_image"), dict)
                        else ""
                    )
                )
            inherited_next_take_id = _inherit_approved_end_as_next_start(
                project_dir,
                queue,
                take,
                image_path=image_path,
                metadata_path=metadata_path,
                image_sha256=image_sha256,
                inherited_at=now,
            )
            qc_status = "anchor_approved_for_video"
        else:
            sidecar.setdefault("rejection_reasons", []).append(reason)
            record["status"] = ANCHOR_REJECTED_STATUS
            record["rejected_at"] = now
            record["reason"] = reason
            next_request_id = uuid.uuid4().hex
            requests = take.setdefault("maestro_director_requests", [])
            if not isinstance(requests, list):
                requests = []
                take["maestro_director_requests"] = requests
            requests.append({
                "id": next_request_id,
                "status": "PENDING",
                "category": "ANCHOR",
                "reason": reason,
                "created_at": now,
                "updated_at": now,
                "supersedes_request_id": request_id,
                "anchor_side": "end",
            })
            qc_status = "waiting_derived_anchor_after_rejection"
        request["review_decision"] = decision
        request["review_reason"] = reason
        request["reviewed_at"] = now
        if next_request_id:
            request["next_request_id"] = next_request_id
        qc = take.setdefault("qc", {})
        if not isinstance(qc, dict):
            qc = {}
            take["qc"] = qc
        qc["status"] = qc_status
        take["maestro_updated_at"] = now
        queue["updated_at"] = now
        _atomic_json_write(metadata_path, sidecar)
        _atomic_json_write(queue_path, queue)
        view = _take_view(take, project_dir)
        view["anchorReview"] = {
            "requestId": request_id,
            "decision": decision,
            "reason": reason,
            "reviewedAt": now,
            "nextRequestId": next_request_id,
            "actualVisibleCharacters": actual_visible_characters,
            "castVerifiedAt": now if actual_visible_characters is not None else "",
            "anchorSide": "end",
            "inheritedAsNextStartTakeId": inherited_next_take_id,
            "sha256": image_sha256,
            **image_info,
        }
        return view


def review_anchor_candidate(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    decision: str,
    reason: str = "",
    request_id: str = "",
    actual_visible_characters: list[str] | None = None,
    human_confirmed: bool = False,
    supersede: bool = False,
) -> dict[str, Any]:
    """Apply an explicit human decision to the currently registered anchor candidate."""

    take_id = _validate_take_id(take_id)
    decision = str(decision or "").strip().upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision deve ser APPROVED ou REJECTED.")
    reason = str(reason or "").strip()
    if len(reason) > 2000:
        raise ValueError("reason deve ter no maximo 2000 caracteres.")
    if decision == "REJECTED" and len(reason) < 3:
        raise ValueError("reason e obrigatorio ao rejeitar uma imagem-ancora.")
    actual_visible_characters = _normalize_visible_cast_review(
        actual_visible_characters
    )

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take = _take_record(_queue(project_dir), take_id)
    end_record = _end_anchor_candidate_record(take)
    end_request_id = str(end_record.get("candidate_request_id") or "").strip().lower()
    requested_id = str(request_id or end_request_id).strip().lower()
    if end_request_id and requested_id == end_request_id:
        return _review_end_anchor_candidate(
            root,
            project_id,
            take_id,
            decision=decision,
            reason=reason,
            request_id=_validate_anchor_request_id(requested_id),
            actual_visible_characters=actual_visible_characters,
            human_confirmed=human_confirmed,
        )

    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        queue_path = _queue_path(project_dir)
        queue = _queue(project_dir)
        take = _take_record(queue, take_id)
        base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
        last_rejected = (
            base.get("last_rejected_candidate")
            if isinstance(base.get("last_rejected_candidate"), dict)
            else {}
        )
        candidate_request_id = str(
            base.get("candidate_request_id") or last_rejected.get("request_id") or ""
        ).strip().lower()
        if request_id:
            request_id = _validate_anchor_request_id(request_id)
        else:
            request_id = _validate_anchor_request_id(candidate_request_id)
        request = _anchor_request(take, request_id)

        existing_decision = str(request.get("review_decision") or "").upper()
        existing_reason = str(request.get("review_reason") or "")
        superseding_approval = bool(
            supersede
            and existing_decision == "APPROVED"
            and decision == "REJECTED"
        )
        supplementing_cast_review = False
        if existing_decision:
            if superseding_approval:
                pass
            elif existing_decision != decision or existing_reason != reason:
                raise AnchorConflictError("Este candidato ja recebeu outra decisao humana.")
            elif decision == "APPROVED" and actual_visible_characters is not None:
                supplementing_cast_review = True
            else:
                view = _take_view(take, project_dir)
                view["anchorReview"] = {
                    "requestId": request_id,
                    "decision": existing_decision,
                    "reason": existing_reason,
                    "reviewedAt": str(request.get("reviewed_at") or ""),
                    "nextRequestId": str(request.get("next_request_id") or ""),
                }
                return view

        if request_id != candidate_request_id:
            raise AnchorConflictError("requestId nao corresponde ao candidato registrado.")
        latest_request = _latest_director_request(take)
        if latest_request is not request:
            raise AnchorConflictError("O candidato nao pertence ao pedido mais recente deste take.")
        if str(request.get("status") or "").upper() != "DELIVERED":
            raise AnchorConflictError("O pedido precisa estar DELIVERED antes da revisao humana.")

        allowed_candidate_statuses = {ANCHOR_PENDING_REVIEW_STATUS}
        if superseding_approval or supplementing_cast_review:
            allowed_candidate_statuses.add(ANCHOR_APPROVED_STATUS)
        image_path, metadata_path, base, sidecar, image_info, image_sha256 = (
            _validated_registered_anchor(
                project_dir,
                take,
                allowed_statuses=allowed_candidate_statuses,
            )
        )

        now = utc_now()
        if supplementing_cast_review:
            visual_qc = (
                sidecar.get("visual_qc")
                if isinstance(sidecar.get("visual_qc"), dict)
                else {}
            )
            if str(visual_qc.get("cast_verification_status") or "").upper() == "VERIFIED":
                registered_cast = _normalize_visible_cast_review(
                    visual_qc.get("actual_visible_characters")
                )
                if registered_cast != actual_visible_characters:
                    raise AnchorConflictError(
                        "A conferencia visual deste candidato ja registrou outro elenco."
                    )
                view = _take_view(take, project_dir)
                view["anchorReview"] = {
                    "requestId": request_id,
                    "decision": existing_decision,
                    "reason": existing_reason,
                    "reviewedAt": str(request.get("reviewed_at") or ""),
                    "nextRequestId": str(request.get("next_request_id") or ""),
                    "actualVisibleCharacters": registered_cast,
                    "castVerifiedAt": str(visual_qc.get("verified_at") or ""),
                }
                return view
            sidecar["visual_qc"] = {
                **visual_qc,
                "cast_verification_status": "VERIFIED",
                "actual_visible_characters": actual_visible_characters,
                "verified_at": now,
                "source": "maestro_anchor_review",
            }
            qc = take.setdefault("qc", {})
            if not isinstance(qc, dict):
                qc = {}
                take["qc"] = qc
            human_gate = (
                qc.get("human_visibility_gate")
                if isinstance(qc.get("human_visibility_gate"), dict)
                else {}
            )
            human_gate.update({
                "status": "verified",
                "actual_visible_characters": actual_visible_characters,
                "verified_at": now,
            })
            qc["human_visibility_gate"] = human_gate
            take["maestro_updated_at"] = now
            queue["updated_at"] = now
            _atomic_json_write(metadata_path, sidecar)
            _atomic_json_write(queue_path, queue)
            view = _take_view(take, project_dir)
            view["anchorReview"] = {
                "requestId": request_id,
                "decision": existing_decision,
                "reason": existing_reason,
                "reviewedAt": str(request.get("reviewed_at") or ""),
                "nextRequestId": str(request.get("next_request_id") or ""),
                "actualVisibleCharacters": actual_visible_characters,
                "castVerifiedAt": now,
                **image_info,
            }
            return view

        if decision == "APPROVED":
            anchor_policy = (
                queue.get("anchor_generation_policy")
                if isinstance(queue.get("anchor_generation_policy"), dict)
                else {}
            )
            if (
                bool(anchor_policy.get("require_explicit_human_confirmation", False))
                and not human_confirmed
            ):
                raise ValueError(
                    "Esta imagem exige confirmação explícita da revisão humana antes da aprovação."
                )
            cast_contract_known, _humans, _non_humans, _expected_cast = (
                _take_visible_cast_contract(take)
            )
            if (
                cast_contract_known
                and bool(anchor_policy.get("require_visual_cast_verification_for_video", False))
                and actual_visible_characters is None
            ):
                raise ValueError(
                    "actualVisibleCharacters e obrigatorio ao aprovar a ancora deste projeto."
                )
        sidecar["validation_status"] = (
            ANCHOR_APPROVED_STATUS if decision == "APPROVED" else ANCHOR_REJECTED_STATUS
        )
        sidecar["reviewed_at"] = now
        sidecar["human_review"] = {
            "decision": decision,
            "reason": reason,
            "source": "maestro_anchor_review",
            "explicit_human_confirmation": bool(human_confirmed),
        }
        next_request_id = ""
        if decision == "APPROVED":
            sidecar["approval_evidence"] = reason or "Aprovado pela revisao humana do Maestro."
            if actual_visible_characters is not None:
                visual_qc = (
                    sidecar.get("visual_qc")
                    if isinstance(sidecar.get("visual_qc"), dict)
                    else {}
                )
                sidecar["visual_qc"] = {
                    **visual_qc,
                    "cast_verification_status": "VERIFIED",
                    "actual_visible_characters": actual_visible_characters,
                    "verified_at": now,
                    "source": "maestro_anchor_review",
                }
            base["status"] = ANCHOR_APPROVED_STATUS
            base["approved_at"] = now
            qc_status = "anchor_approved_for_video"
        else:
            rejection_reasons = sidecar.get("rejection_reasons")
            if not isinstance(rejection_reasons, list):
                rejection_reasons = []
            if reason not in rejection_reasons:
                rejection_reasons.append(reason)
            sidecar["rejection_reasons"] = rejection_reasons
            source_base_state = (
                base.get("source_base_state")
                if isinstance(base.get("source_base_state"), dict)
                else {}
            )
            rejected_candidate = {
                "request_id": request_id,
                "status": ANCHOR_REJECTED_STATUS,
                "file": image_path.as_posix(),
                "metadata": metadata_path.as_posix(),
                "image_sha256": image_sha256,
                "rejected_at": now,
                "reason": reason,
            }
            for field in (
                "file", "metadata", "model", "prompt", "candidate_request_id",
                "image_sha256", "delivered_at", "approved_at", "source_base_state",
            ):
                base.pop(field, None)
            for field in ("file", "metadata", "model", "prompt"):
                if field in source_base_state:
                    base[field] = source_base_state[field]
            base["status"] = "needs_derived_anchor"
            base["last_rejected_candidate"] = rejected_candidate
            qc_status = "waiting_derived_anchor_after_rejection"
            next_request_id = uuid.uuid4().hex
            requests = take.setdefault("maestro_director_requests", [])
            if not isinstance(requests, list):
                requests = []
                take["maestro_director_requests"] = requests
            requests.append({
                "id": next_request_id,
                "status": "PENDING",
                "category": "ANCHOR",
                "reason": reason,
                "created_at": now,
                "updated_at": now,
                "supersedes_request_id": request_id,
            })

        replacement = (
            take.get("imagegen_replacement")
            if isinstance(take.get("imagegen_replacement"), dict)
            else None
        )
        if replacement is not None and str(replacement.get("request_id") or "") == request_id:
            replacement["updated_at"] = now
            if decision == "APPROVED":
                replacement.update({
                    "status": ANCHOR_APPROVED_STATUS,
                    "human_approval_required": False,
                    "approved_at": now,
                })
            else:
                replacement.update({
                    "status": "awaiting_imagegen",
                    "request_id": next_request_id,
                    "human_approval_required": True,
                    "rejected_at": now,
                    "rejection_reason": reason,
                })

        if superseding_approval:
            review_history = request.get("review_history")
            if not isinstance(review_history, list):
                review_history = []
                request["review_history"] = review_history
            review_history.append({
                "decision": existing_decision,
                "reason": existing_reason,
                "reviewed_at": str(request.get("reviewed_at") or ""),
                "superseded_at": now,
                "superseded_by": "owner_batch_anchor_rejection",
            })
            request["approval_revoked_at"] = now
        request["review_decision"] = decision
        request["review_reason"] = reason
        request["reviewed_at"] = now
        if next_request_id:
            request["next_request_id"] = next_request_id
        qc = take.setdefault("qc", {})
        if not isinstance(qc, dict):
            qc = {}
            take["qc"] = qc
        qc["status"] = qc_status
        if decision == "APPROVED" and actual_visible_characters is not None:
            human_gate = (
                qc.get("human_visibility_gate")
                if isinstance(qc.get("human_visibility_gate"), dict)
                else {}
            )
            human_gate.update({
                "status": "verified",
                "actual_visible_characters": actual_visible_characters,
                "verified_at": now,
            })
            qc["human_visibility_gate"] = human_gate
        take["maestro_updated_at"] = now
        queue["updated_at"] = now

        _atomic_json_write(metadata_path, sidecar)
        _invalidate_take_thumbnail(project_dir, take_id)
        _atomic_json_write(queue_path, queue)
        view = _take_view(take, project_dir)
        view["anchorReview"] = {
            "requestId": request_id,
            "decision": decision,
            "reason": reason,
            "reviewedAt": now,
            "nextRequestId": next_request_id,
            "actualVisibleCharacters": actual_visible_characters,
            "castVerifiedAt": now if actual_visible_characters is not None else "",
            **image_info,
        }
        return view


def get_take_anchor_image_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return the full-resolution registered anchor candidate, never a reference placeholder."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = _take_record(queue, take_id)
    end_record = _end_anchor_candidate_record(take)
    if str(end_record.get("status") or "").strip().lower() in {
        ANCHOR_PENDING_REVIEW_STATUS,
        ANCHOR_APPROVED_STATUS,
    }:
        image_path, _metadata_path, _base, _sidecar, _image_info, _image_sha256 = (
            _validated_registered_end_anchor(
                project_dir,
                take,
                allowed_statuses={str(end_record.get("status") or "").strip().lower()},
            )
        )
        return image_path
    image_path, _metadata_path, _base, _sidecar, _image_info, _image_sha256 = (
        _validated_registered_anchor(
            project_dir,
            take,
            allowed_statuses={ANCHOR_PENDING_REVIEW_STATUS, ANCHOR_APPROVED_STATUS},
        )
    )
    return image_path


def get_take_preanalysis_gallery_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return the exact project-local START/checkpoint/END sheet for human viewing."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    take = _take_record(_queue(project_dir), take_id)
    gallery, _record, _sha256 = _validated_preanalysis_gallery(project_dir, take)
    return gallery


def get_take_preview_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return the best registered local review file for a take."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = next((item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id), None)
    if take is None:
        raise FileNotFoundError(take_id)
    master = _take_output_path(project_dir, take)
    if master is None:
        raise FileNotFoundError(f"preview:{take_id}")
    return resolve_review_proxy(project_dir, take_id, master) or master


def get_take_status(root: Path, project_id: str, take_id: str) -> str:
    """Return the canonical Maestro status without mutating the take queue."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    take = _take_record(_queue(project_dir), take_id)
    return _take_status(take)


def get_take_audio_candidate_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return a registered project-local audio candidate for human listening."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    take = _take_record(_queue(project_dir), take_id)
    candidate = _take_audio_candidate_path(project_dir, take)
    if candidate is None:
        raise FileNotFoundError(f"audio-candidate:{take_id}")
    return candidate


def get_take_audio_candidate_variant_path(
    root: Path,
    project_id: str,
    take_id: str,
    candidate_id: str,
) -> Path:
    """Return one named project-local ADR variant for explicit human listening."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    candidate_id = str(candidate_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", candidate_id):
        raise ValueError("candidateId de audio invalido.")
    take = _take_record(_queue(project_dir), take_id)
    candidate = next(
        (
            path
            for record, path in _take_audio_candidate_variants(project_dir, take)
            if str(record.get("id") or "") == candidate_id
        ),
        None,
    )
    if candidate is None:
        raise FileNotFoundError(f"audio-candidate:{take_id}:{candidate_id}")
    return candidate


def register_take_audio_candidate(
    root: Path,
    project_id: str,
    take_id: str,
    candidate_path: Path,
    *,
    provider_id: str,
    model: str,
    source_video_sha256: str = "",
    qc: dict[str, Any] | None = None,
    generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Register a project-local generated candidate without approving or attaching it."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    candidate = Path(candidate_path).resolve()
    project_dir = project_dir.resolve()
    if (
        not candidate.is_relative_to(project_dir)
        or not candidate.is_file()
        or candidate.suffix.lower() not in {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}
    ):
        raise ValueError("Candidato video-to-sound deve ser um audio dentro do projeto.")
    provider_id = str(provider_id or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,63}", provider_id):
        raise ValueError("providerId video-to-sound invalido.")
    model = str(model or "").strip()
    if not model:
        raise ValueError("Modelo video-to-sound nao informado.")
    qc = qc if isinstance(qc, dict) else {}
    generation = generation if isinstance(generation, dict) else {}
    candidate_id = uuid.uuid4().hex
    now = utc_now()
    record = {
        "id": candidate_id,
        "label": f"Som pelo video - {provider_id}",
        "file": str(candidate),
        "status": "candidate_pending_human_listening",
        "provider_id": provider_id,
        "model": model,
        "source_take": f"video-to-sound {provider_id} sincronizado ao take {take_id}",
        "source_video_sha256": str(source_video_sha256 or ""),
        "cpu_asr_transcription": "sem transcricao; candidato de ambiente e efeitos",
        "duration_seconds": float(qc.get("durationSeconds") or 0),
        "sample_rate": int(qc.get("sampleRate") or 0),
        "channels": int(qc.get("channels") or 0),
        "sha256": str(qc.get("sha256") or hashlib.sha256(candidate.read_bytes()).hexdigest()),
        "qc": dict(qc),
        "generation": dict(generation),
        "created_at": now,
    }
    with _QUEUE_MUTATION_LOCK:
        queue = _queue(project_dir)
        take = _take_record(queue, take_id)
        audio_direction = (
            take.get("audio_direction")
            if isinstance(take.get("audio_direction"), dict)
            else {}
        )
        previous = audio_direction.get("salvage_candidate")
        if isinstance(previous, dict) and previous.get("file"):
            history = audio_direction.setdefault("candidate_history", [])
            if not isinstance(history, list):
                history = []
                audio_direction["candidate_history"] = history
            history.append(dict(previous))
            del history[:-20]
        variants = audio_direction.setdefault("candidate_variants", [])
        if not isinstance(variants, list):
            variants = []
            audio_direction["candidate_variants"] = variants
        variants.append(dict(record))
        del variants[:-20]
        audio_direction["strategy"] = "model_independent_video_to_sound_after_visual_qc"
        audio_direction["delivery_required"] = False
        audio_direction["post_mix_required"] = True
        audio_direction["dialogue_generation_authorized"] = False
        audio_direction["human_listening_required"] = True
        audio_direction["human_listening_completed"] = False
        audio_direction["salvage_candidate"] = dict(record)
        take["audio_direction"] = audio_direction
        queue["updated_at"] = now
        _atomic_json_write(_queue_path(project_dir), queue)
        return _take_view(take, project_dir)


def review_take_audio_candidate(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    decision: str,
    reason: str = "",
) -> dict[str, Any]:
    """Apply an explicit human decision to the active video-to-sound candidate."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    decision = str(decision or "").strip().upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision deve ser APPROVED ou REJECTED.")
    reason = str(reason or "").strip()
    if decision == "REJECTED" and len(reason) < 3:
        raise ValueError("Informe o motivo da rejeicao do audio.")
    with _QUEUE_MUTATION_LOCK:
        queue = _queue(project_dir)
        take = _take_record(queue, take_id)
        audio_direction = (
            take.get("audio_direction")
            if isinstance(take.get("audio_direction"), dict)
            else {}
        )
        candidate = audio_direction.get("salvage_candidate")
        if not isinstance(candidate, dict) or not candidate.get("file"):
            raise FileNotFoundError(f"audio-candidate:{take_id}")
        now = utc_now()
        candidate_id = str(candidate.get("id") or "")
        variants = audio_direction.get("candidate_variants")
        if not isinstance(variants, list):
            variants = []
        if decision == "APPROVED":
            candidate["status"] = "approved_human_listening"
            candidate["approved_at"] = now
            audio_direction["human_listening_required"] = False
            audio_direction["human_listening_completed"] = True
            audio_direction["voice_qc_status"] = "approved_human_listening"
            for variant in variants:
                if isinstance(variant, dict) and str(variant.get("id") or "") == candidate_id:
                    variant.update({"status": "approved_human_listening", "approved_at": now})
        else:
            rejected = dict(candidate)
            rejected.update({
                "status": "rejected_human_listening",
                "reason": reason,
                "rejected_at": now,
            })
            rejected_candidates = audio_direction.setdefault("rejected_candidates", [])
            if not isinstance(rejected_candidates, list):
                rejected_candidates = []
                audio_direction["rejected_candidates"] = rejected_candidates
            rejected_candidates.append(rejected)
            del rejected_candidates[:-20]
            for variant in variants:
                if isinstance(variant, dict) and str(variant.get("id") or "") == candidate_id:
                    variant.update({
                        "status": "rejected_human_listening",
                        "reason": reason,
                        "rejected_at": now,
                    })
            audio_direction.pop("salvage_candidate", None)
            audio_direction["human_listening_required"] = False
            audio_direction["human_listening_completed"] = True
            audio_direction["voice_qc_status"] = "rejected_human_listening"
        take["audio_direction"] = audio_direction
        queue["updated_at"] = now
        _atomic_json_write(_queue_path(project_dir), queue)
        return _take_view(take, project_dir)


def get_take_upscale_preview_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return only the technically ready upscale candidate under human review."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = next(
        (item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id),
        None,
    )
    if take is None:
        raise FileNotFoundError(take_id)
    preview = _upscale_candidate_path(project_dir, take, pending_only=True)
    if preview is None:
        raise FileNotFoundError(f"upscale-preview:{take_id}")
    return preview


def get_take_download_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return a video only after it reached a user-downloadable review state."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = next((item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id), None)
    if take is None:
        raise FileNotFoundError(take_id)
    if _take_status(take) not in DOWNLOADABLE_TAKE_STATUSES:
        raise PermissionError("O video ainda nao foi liberado para download.")
    preview = _take_output_path(project_dir, take)
    if preview is None:
        raise FileNotFoundError(f"preview:{take_id}")
    return preview


def get_take_thumbnail_path(root: Path, project_id: str, take_id: str) -> Path:
    """Return the approved anchor image used as the take thumbnail."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = next((item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id), None)
    if take is None:
        raise FileNotFoundError(take_id)
    thumbnail = _take_keyframe_path(project_dir, take)
    if thumbnail is None:
        raise FileNotFoundError(f"thumbnail:{take_id}")
    cache_dir = (project_dir / "qc" / "maestro_thumbnails").resolve()
    if not cache_dir.is_relative_to(project_dir):
        raise ValueError("Cache de miniaturas fora do projeto.")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"take_{take_id}.jpg"
    if cached.is_file() and cached.stat().st_mtime_ns >= thumbnail.stat().st_mtime_ns:
        return cached

    from PIL import Image, ImageOps

    with Image.open(thumbnail) as source:
        source = ImageOps.exif_transpose(source)
        preview = ImageOps.fit(source, (480, 270), method=Image.Resampling.LANCZOS)
        if preview.mode != "RGB":
            preview = preview.convert("RGB")
        fd, temp_name = tempfile.mkstemp(prefix=f".{cached.name}.", suffix=".tmp", dir=cache_dir)
        os.close(fd)
        try:
            preview.save(temp_name, format="JPEG", quality=82, optimize=True, progressive=True)
            os.replace(temp_name, cached)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
    return cached


def _validate_continuous_action_generation_contract(
    queue: dict[str, Any], take: dict[str, Any]
) -> None:
    """Fail closed before GPU when a project opts into continuous action."""

    policy = queue.get("continuous_action_contract")
    if not isinstance(policy, dict) or policy.get("required") is not True:
        return
    required_policy = (
        "generated_connector_required_between_takes",
        "crossfade_forbidden",
        "freeze_frame_forbidden",
        "static_tail_forbidden",
        "motion_handoff_required",
        "full_duration_motion_required",
        "three_interval_motion_required",
        "moving_transition_anchors_required",
    )
    missing_policy = [field for field in required_policy if policy.get(field) is not True]
    if missing_policy:
        raise ValueError(
            "Contrato global de acao continua incompleto: " + ", ".join(missing_policy)
        )

    direct = take.get("transition_motion_contract")
    shot = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
    contract = direct if isinstance(direct, dict) else shot.get("transition_motion_contract")
    if not isinstance(contract, dict):
        raise ValueError("Take bloqueado: falta transition_motion_contract de acao continua.")
    continuity = contract.get("continuity")
    if not isinstance(continuity, dict):
        raise ValueError("Take bloqueado: falta continuity no contrato de acao continua.")
    for field in ("continuous_action", "motion_handoff", "action_occupies_full_duration"):
        if continuity.get(field) is not True:
            raise ValueError(f"Take bloqueado: continuity.{field} deve ser true.")
    intervals = continuity.get("interval_motion")
    if not isinstance(intervals, dict):
        intervals = {}
    for field in ("early_0_30", "middle_30_70", "late_70_100"):
        if not isinstance(intervals.get(field), str) or len(intervals[field].strip()) < 8:
            raise ValueError(
                f"Take bloqueado: movimento descritivo obrigatorio em continuity.interval_motion.{field}."
            )
    for field in ("crossfade_frames", "freeze_frames", "static_hold_frames"):
        value = continuity.get(field)
        if isinstance(value, bool) or value != 0:
            raise ValueError(f"Take bloqueado: continuity.{field} deve ser exatamente 0.")
    transition = take.get("transition")
    is_transition = take.get("is_transition") is True or (
        isinstance(transition, dict) and transition.get("is_transition") is True
    )
    if is_transition:
        anchors = continuity.get("moving_anchor_context")
        if not isinstance(anchors, dict):
            anchors = {}
        for side in ("start", "end"):
            if anchors.get(f"{side}_has_motion_before_and_after") is not True:
                raise ValueError(
                    f"Take bloqueado: ancora {side} precisa vir de trecho com movimento antes e depois."
                )
            source = anchors.get(f"{side}_source")
            if not isinstance(source, str) or len(source.strip()) < 8:
                raise ValueError(f"Take bloqueado: falta evidencia da ancora {side} em movimento.")


def _validate_take_execution_contract(
    queue: dict[str, Any],
    take: dict[str, Any],
    *,
    generation_profile: str,
) -> dict[str, Any]:
    """Reject declared production controls that the selected graph cannot enforce."""

    policy = queue.get("take_execution_contract")
    if not isinstance(policy, dict) or policy.get("required") is not True:
        return {}
    required_policy = (
        "declared_controls_must_exist_in_graph",
        "reference_is_not_anchor",
        "reference_video_is_not_pose_control",
        "model_mode_must_match_conditioning_node",
    )
    missing_policy = [field for field in required_policy if policy.get(field) is not True]
    if missing_policy:
        raise ValueError(
            "TAKE_EXECUTION_POLICY_INCOMPLETE: " + ", ".join(missing_policy)
        )
    claims = take.get("control_claims")
    if not isinstance(claims, dict):
        raise ValueError(
            "TAKE_CONTROL_CLAIMS_MISSING: declare anchor_binding e motion_binding antes da GPU."
        )
    anchor_binding = str(claims.get("anchor_binding") or "").strip().lower()
    motion_binding = str(claims.get("motion_binding") or "").strip().lower()
    if anchor_binding not in {
        "none",
        "first_frame_exact",
        "first_last_exact",
        "timeline_exact",
        "references_only",
    }:
        raise ValueError("TAKE_ANCHOR_BINDING_INVALID: contrato de ancoras desconhecido.")
    if motion_binding not in {"prompt_guided", "reference_video", "exact_pose"}:
        raise ValueError("TAKE_MOTION_BINDING_INVALID: contrato de movimento desconhecido.")
    minimax_control = (
        take.get("minimax_anchor_control")
        if isinstance(take.get("minimax_anchor_control"), dict)
        else {}
    )
    control_mode = str(minimax_control.get("mode") or "").strip().lower()
    failures: list[str] = []
    if generation_profile in MINIMAX_H3_GENERATION_PROFILES:
        generation = (
            take.get("video_generation")
            if isinstance(take.get("video_generation"), dict)
            else {}
        )
        if anchor_binding == "first_frame_exact":
            if generation.get("start_end_frame_enabled") is not False:
                failures.append(
                    "first_frame_exact exige start_end_frame_enabled=false"
                )
            if bool(generation.get("require_approved_end_frame")):
                failures.append(
                    "first_frame_exact nao pode exigir quadro final aprovado"
                )
            if control_mode:
                failures.append(
                    "first_frame_exact nao pode declarar controle multi-anchor ou Ref2VA"
                )
        if anchor_binding == "timeline_exact" and control_mode != "multi_anchor_segment":
            failures.append(
                "timeline_exact exige segmentos first/last entre ancoras adjacentes; Ref2VA so cria referencias"
            )
        if anchor_binding == "references_only" and (
            control_mode != "ref2va_motion"
            or str(minimax_control.get("anchor_semantics") or "").strip().lower()
            != "appearance_reference_only"
        ):
            failures.append(
                "references_only exige Ref2VA com anchor_semantics=appearance_reference_only"
            )
        if motion_binding == "reference_video" and control_mode != "ref2va_motion":
            failures.append("reference_video exige o modo Ref2VA")
        if motion_binding == "exact_pose":
            failures.append(
                "MiniMaxH3ReferenceToVideo nao possui entrada de pose e nao pode garantir articulacoes"
            )
    elif generation_profile == WAN22_ANIMATE_PROFILE:
        wan_control = (
            take.get("wan_animate_control")
            if isinstance(take.get("wan_animate_control"), dict)
            else {}
        )
        if anchor_binding != "references_only":
            failures.append(
                "Wan Animate Move usa uma imagem como referencia de aparencia; nao implementa timeline de ancoras"
            )
        if motion_binding != "exact_pose":
            failures.append("Wan Animate Move exige motion_binding=exact_pose")
        if str(wan_control.get("mode") or "").strip().lower() != "move":
            failures.append("Wan Animate exato exige wan_animate_control.mode=move")
    if failures:
        raise ValueError("TAKE_CONTROL_CONTRACT_UNSATISFIED: " + "; ".join(failures) + ".")
    return {
        "enabled": True,
        "anchorBinding": anchor_binding,
        "motionBinding": motion_binding,
        "declaredControlsVerified": True,
    }


def _validate_wan_animate_pose_control(
    project_dir: Path,
    take: dict[str, Any],
) -> dict[str, Any]:
    """Require a real performer -> DWPose -> owner approval chain."""

    control = (
        take.get("wan_animate_control")
        if isinstance(take.get("wan_animate_control"), dict)
        else {}
    )
    if str(control.get("mode") or "").strip().lower() != "move":
        raise ValueError("WAN_ANIMATE_MOVE_REQUIRED: o take deve usar o modo Move.")
    manifest_raw = str(control.get("pose_manifest") or "").strip()
    if not manifest_raw:
        raise ValueError("WAN_ANIMATE_POSE_MISSING: falta o manifesto DWPose aprovado.")
    manifest_path = (project_dir / manifest_raw).resolve()
    if (
        not manifest_path.is_relative_to(project_dir.resolve())
        or not manifest_path.is_file()
    ):
        raise ValueError("WAN_ANIMATE_POSE_INVALID: manifesto DWPose ausente ou fora do projeto.")
    manifest = _read_json(manifest_path)
    if str(manifest.get("asset_type") or "").strip().lower() != "dwpose_pose_video":
        raise ValueError(
            "WAN_ANIMATE_POSE_NOT_DWPOSE: desenho procedural ou video RGB nao e controle DWPose."
        )
    if str(manifest.get("status") or "").strip().upper() != "APPROVED_BY_OWNER":
        raise ValueError("WAN_ANIMATE_POSE_NOT_APPROVED: a previa DWPose aguarda aprovacao humana.")
    if manifest.get("is_dwpose") is not True or manifest.get("is_exact_pose_control") is not True:
        raise ValueError("WAN_ANIMATE_POSE_CLAIMS_INVALID: o manifesto nao prova controle articular.")
    if str(manifest.get("face_transfer") or "").strip().lower() not in {
        "disabled", "off", "false",
    }:
        raise ValueError("WAN_ANIMATE_FACE_FORBIDDEN: transferencia facial nao foi autorizada.")
    source_driver_kind = str(manifest.get("source_driver_kind") or "").strip().lower()
    if source_driver_kind not in {
        "real_human_performance_video",
        "synthetic_kinematic_pose_sequence",
    }:
        raise ValueError(
            "WAN_ANIMATE_DRIVER_KIND_INVALID: use performance humana real ou pose cinematica sintetica aprovada."
        )
    if (
        source_driver_kind == "synthetic_kinematic_pose_sequence"
        and manifest.get("is_synthetic_pose") is not True
    ):
        raise ValueError(
            "WAN_ANIMATE_SYNTHETIC_POSE_CLAIM_INVALID: a origem sintetica precisa estar declarada."
        )
    try:
        fps = float(manifest.get("fps") or 0)
        width = int(manifest.get("width") or 0)
        height = int(manifest.get("height") or 0)
        frames = int(manifest.get("frames") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("WAN_ANIMATE_POSE_MEDIA_INVALID: geometria/timing ausentes.") from exc
    if abs(fps - 30.0) > 0.001 or width % 16 or height % 16 or frames < 25:
        raise ValueError(
            "WAN_ANIMATE_POSE_MEDIA_INVALID: pose deve ter 30 FPS, dimensoes 16-aligned e ao menos 25 quadros."
        )

    def checked_file(file_key: str, hash_key: str, label: str) -> Path:
        raw = str(manifest.get(file_key) or "").strip()
        candidate = Path(raw).resolve() if raw else None
        if (
            candidate is None
            or not candidate.is_relative_to(project_dir.resolve())
            or not candidate.is_file()
        ):
            raise ValueError(f"WAN_ANIMATE_{label}_INVALID: arquivo ausente ou fora do projeto.")
        expected = str(manifest.get(hash_key) or "").strip().lower()
        if not expected or hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
            raise ValueError(f"WAN_ANIMATE_{label}_TAMPERED: SHA256 divergiu.")
        return candidate

    if source_driver_kind == "real_human_performance_video":
        source_driver = checked_file(
            "source_driver_file", "source_driver_sha256", "SOURCE_DRIVER"
        )
    else:
        source_driver = checked_file(
            "reference_storyboard", "reference_storyboard_sha256", "POSE_REFERENCE"
        )
    pose_video = checked_file("file", "sha256", "POSE")
    return {
        "enabled": True,
        "mode": "move",
        "profile": WAN22_ANIMATE_PROFILE,
        "poseVideo": pose_video,
        "poseVideoName": pose_video.name,
        "poseManifest": manifest_path,
        "sourceDriver": source_driver,
        "sourceDriverKind": source_driver_kind,
        "fps": fps,
        "width": width,
        "height": height,
        "frames": frames,
        "faceTransfer": False,
        "ownerApproved": True,
    }


def _validate_minimax_h3_anchor_control(
    project_dir: Path,
    take: dict[str, Any],
    *,
    keyframe: Path,
    end_keyframe: Path | None,
) -> dict[str, Any]:
    """Bind H3 endpoints to the exact owner-approved anchor manifest.

    MiniMax H3 FL2VA only receives a first and a last frame. Projects that
    declare a stronger multi-anchor or motion-driver contract must therefore
    fail closed instead of silently replacing those controls with prose.
    """

    control = take.get("minimax_anchor_control")
    if not isinstance(control, dict) or not control:
        return {}

    manifest_raw = str(control.get("manifest") or "").strip()
    if not manifest_raw:
        raise ValueError("MINIMAX_ANCHOR_MANIFEST_MISSING: falta o manifesto de ancoras aprovado.")
    manifest_path = (project_dir / manifest_raw).resolve()
    if (
        not manifest_path.is_relative_to(project_dir.resolve())
        or not manifest_path.is_file()
        or manifest_path.suffix.lower() != ".json"
    ):
        raise ValueError("MINIMAX_ANCHOR_MANIFEST_INVALID: manifesto ausente ou fora do projeto.")
    manifest = _read_json(manifest_path)
    if str(manifest.get("status") or "").strip().upper() != "APPROVED_BY_OWNER":
        raise ValueError("MINIMAX_ANCHOR_MANIFEST_NOT_APPROVED: conjunto sem aprovacao do proprietario.")
    anchors = [item for item in manifest.get("anchors", []) if isinstance(item, dict)]
    by_id = {str(item.get("id") or "").strip(): item for item in anchors}
    start_id = str(control.get("start_anchor_id") or "").strip()
    end_id = str(control.get("end_anchor_id") or "").strip()
    if not start_id or not end_id or start_id not in by_id or end_id not in by_id:
        raise ValueError("MINIMAX_ANCHOR_ID_INVALID: inicio/fim nao existem no conjunto aprovado.")
    if end_keyframe is None:
        raise ValueError("MINIMAX_END_ANCHOR_MISSING: o segmento exige quadro final aprovado.")

    def _approved_path_and_hash(anchor: dict[str, Any]) -> tuple[Path, str]:
        relative = str(anchor.get("normalized_file") or anchor.get("file") or "").strip()
        expected_hash = str(
            anchor.get("normalized_sha256") or anchor.get("sha256") or ""
        ).strip().lower()
        candidate = (manifest_path.parent / relative).resolve()
        if (
            not relative
            or not expected_hash
            or not candidate.is_relative_to(project_dir.resolve())
            or not candidate.is_file()
        ):
            raise ValueError("MINIMAX_APPROVED_ANCHOR_INVALID: arquivo ou hash aprovado indisponivel.")
        actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("MINIMAX_APPROVED_ANCHOR_TAMPERED: hash da ancora aprovada divergiu.")
        return candidate, actual_hash

    def _approved_reference_path_and_hash(anchor: dict[str, Any]) -> tuple[Path, str]:
        """Prefer the owner-approved source pixels for Ref2VA identity fidelity."""

        relative = str(anchor.get("file") or anchor.get("normalized_file") or "").strip()
        expected_hash = str(
            anchor.get("sha256") or anchor.get("normalized_sha256") or ""
        ).strip().lower()
        candidate = (manifest_path.parent / relative).resolve()
        if (
            not relative
            or not expected_hash
            or not candidate.is_relative_to(project_dir.resolve())
            or not candidate.is_file()
        ):
            raise ValueError(
                "MINIMAX_APPROVED_REFERENCE_INVALID: imagem-fonte ou hash aprovado indisponivel."
            )
        actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                "MINIMAX_APPROVED_REFERENCE_TAMPERED: hash da imagem-fonte divergiu."
            )
        return candidate, actual_hash

    approved_start, start_hash = _approved_path_and_hash(by_id[start_id])
    approved_end, end_hash = _approved_path_and_hash(by_id[end_id])
    if keyframe.resolve() != approved_start or end_keyframe.resolve() != approved_end:
        raise ValueError(
            "MINIMAX_STALE_ANCHOR_SELECTION: o job nao aponta para as ancoras live action aprovadas."
        )

    hard_gates = manifest.get("hard_gates") if isinstance(manifest.get("hard_gates"), dict) else {}
    mode = str(control.get("mode") or "single_pass").strip().lower()
    anchor_semantics = str(
        control.get("anchor_semantics")
        or ("temporal_exact" if len(anchors) > 2 else "endpoint_exact")
    ).strip().lower()
    if bool(hard_gates.get("prompt_only_rerender_forbidden")):
        if mode not in {"multi_anchor_segment", "ref2va_motion"}:
            raise ValueError(
                "MINIMAX_H3_PROMPT_ONLY_FORBIDDEN: o projeto exige ancoras intermediarias; "
                "um passe H3 com somente primeiro/ultimo quadro nao e autorizado."
            )
        ordered_ids = [str(item.get("id") or "").strip() for item in anchors]
        if (
            mode == "multi_anchor_segment"
            and ordered_ids.index(end_id) - ordered_ids.index(start_id) != 1
        ):
            raise ValueError(
                "MINIMAX_NON_ADJACENT_ANCHORS: cada segmento H3 deve ligar ancoras aprovadas adjacentes."
            )
    if mode == "ref2va_motion" and len(anchors) > 2 and anchor_semantics != "appearance_reference_only":
        raise ValueError(
            "MINIMAX_MULTI_ANCHOR_TIMELINE_UNSUPPORTED: Ref2VA recebe imagens como referencias, "
            "nao como keyframes temporais. Um projeto que exige todas as ancoras na ordem deve "
            "usar segmentos first/last entre ancoras adjacentes ou outro motor com timeline real."
        )

    reference_subjects: list[dict[str, Any]] = []
    if mode == "ref2va_motion":
        raw_subjects = control.get("reference_subjects")
        if not isinstance(raw_subjects, list) or not raw_subjects:
            raise ValueError(
                "MINIMAX_REF2VA_SUBJECTS_MISSING: referencias multiplas exigem sujeitos "
                "persistentes explicitos para impedir mistura de identidade e figurino."
            )
        allowed_sources = {
            *(f"<Picture {index}>" for index in range(1, len(anchors) + 1)),
            "<Video 1>",
        }
        allowed_relations = {
            "fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference",
        }
        for index, item in enumerate(raw_subjects, start=1):
            if not isinstance(item, dict):
                raise ValueError("MINIMAX_REF2VA_SUBJECT_INVALID: sujeito deve ser um objeto.")
            description = str(item.get("description") or "").strip()
            sources = [str(value).strip() for value in item.get("sources", []) if str(value).strip()]
            retention = str(item.get("retention") or "").strip()
            relation = str(item.get("relation") or "fully_preserved").strip().lower()
            if not description or not sources or not retention:
                raise ValueError(
                    "MINIMAX_REF2VA_SUBJECT_INVALID: description, sources e retention sao obrigatorios."
                )
            unknown_sources = [value for value in sources if value not in allowed_sources]
            if unknown_sources:
                raise ValueError(
                    "MINIMAX_REF2VA_SUBJECT_SOURCE_INVALID: " + ", ".join(unknown_sources)
                )
            if relation not in allowed_relations:
                raise ValueError("MINIMAX_REF2VA_SUBJECT_RELATION_INVALID: relacao desconhecida.")
            reference_subjects.append({
                "label": f"<Subject {index}>",
                "description": description,
                "sources": sources,
                "retention": retention,
                "relation": relation,
            })
        used_sources = {
            source
            for subject in reference_subjects
            for source in subject["sources"]
        }
        missing_pictures = [
            f"<Picture {index}>"
            for index in range(1, len(anchors) + 1)
            if f"<Picture {index}>" not in used_sources
        ]
        if missing_pictures:
            raise ValueError(
                "MINIMAX_REF2VA_ORPHAN_REFERENCES: imagens sem sujeito definido: "
                + ", ".join(missing_pictures)
            )

    roles = " ".join(
        str(by_id[anchor_id].get("role") or "").casefold()
        for anchor_id in (start_id, end_id)
    )
    reference_video: Path | None = None
    driver_asset_type = ""
    if mode == "ref2va_motion":
        driver_raw = str(control.get("motion_driver_manifest") or "").strip()
        if driver_raw:
            driver_manifest_path = (project_dir / driver_raw).resolve()
            if (
                not driver_manifest_path.is_relative_to(project_dir.resolve())
                or not driver_manifest_path.is_file()
            ):
                raise ValueError("MINIMAX_DANCE_CONTROL_INVALID: manifesto de video fora do projeto.")
            driver = _read_json(driver_manifest_path)
            if str(driver.get("status") or "").strip().upper() != "APPROVED_BY_OWNER":
                raise ValueError("MINIMAX_DANCE_CONTROL_NOT_APPROVED: video sem aprovacao do proprietario.")
            driver_asset_type = str(driver.get("asset_type") or "").strip().lower()
            driver_file_raw = str(driver.get("file") or "").strip()
            reference_video = Path(driver_file_raw).resolve() if driver_file_raw else None
            if (
                reference_video is None
                or not reference_video.is_relative_to(project_dir.resolve())
                or not reference_video.is_file()
            ):
                raise ValueError("MINIMAX_DANCE_CONTROL_INVALID: video ausente ou fora do projeto.")
            driver_sha = str(driver.get("sha256") or "").strip().lower()
            if not driver_sha or hashlib.sha256(reference_video.read_bytes()).hexdigest() != driver_sha:
                raise ValueError("MINIMAX_DANCE_CONTROL_TAMPERED: hash do video divergiu.")

    exact_dance_control = "canonical_" in roles and any(
        hard_gates.get(field) is True
        for field in (
            "canonical_dance_requires_approved_motion_driver",
            "two_distinct_fingertip_contacts",
            "exact_pose_guarantee",
        )
    )
    if exact_dance_control:
        if mode == "ref2va_motion":
            if reference_video is None:
                raise ValueError("MINIMAX_DANCE_CONTROL_MISSING: falta o driver aprovado para Ref2VA.")
            if driver_asset_type not in {"dwpose_pose_video", "openpose_pose_video"}:
                raise ValueError(
                    "MINIMAX_DANCE_DRIVER_NOT_POSE_CONTROL: o arquivo aprovado e apenas referencia "
                    "visual/procedural; nao e uma sequencia DWPose ou OpenPose."
                )
            raise ValueError(
                "MINIMAX_REF2VA_NOT_EXACT_POSE_CONTROL: o no MiniMaxH3ReferenceToVideo nao possui "
                "entrada de pose. Uma sequencia DWPose conectada como ref_videos continua sendo "
                "referencia, nao controle articular obrigatorio."
            )
        else:
            translation_raw = str(control.get("motion_translation_manifest") or "").strip()
            if not translation_raw:
                raise ValueError(
                    "MINIMAX_DANCE_CONTROL_MISSING: o segmento exige um manifesto aprovado "
                    "que traduza o driver em ancoras live action intermediarias."
                )
            translation_path = (project_dir / translation_raw).resolve()
            if (
                not translation_path.is_relative_to(project_dir.resolve())
                or not translation_path.is_file()
            ):
                raise ValueError("MINIMAX_DANCE_CONTROL_INVALID: traducao do driver ausente ou fora do projeto.")
            translation = _read_json(translation_path)
            if str(translation.get("status") or "").strip().upper() != "APPROVED_BY_OWNER":
                raise ValueError("MINIMAX_DANCE_CONTROL_NOT_APPROVED: traducao visual da danca sem aprovacao.")

    return {
        "enabled": True,
        "manifest": manifest_path,
        "candidateSet": str(manifest.get("candidate_set") or ""),
        "mode": mode,
        "anchorSemantics": anchor_semantics,
        "temporalAnchorBinding": mode == "multi_anchor_segment",
        "startAnchorId": start_id,
        "endAnchorId": end_id,
        "startSha256": start_hash,
        "endSha256": end_hash,
        "referenceImages": [
            _approved_reference_path_and_hash(anchor)[0]
            for anchor in anchors
        ] if mode == "ref2va_motion" else [],
        "referenceVideo": reference_video,
        "referenceVideoAssetType": driver_asset_type,
        "referenceDefinitions": [
            {
                "label": f"<Picture {index}>",
                "anchorId": str(anchor.get("id") or ""),
                "role": str(anchor.get("role") or ""),
            }
            for index, anchor in enumerate(anchors, start=1)
        ] if mode == "ref2va_motion" else [],
        "referenceSubjects": reference_subjects,
    }


def get_take_generation_spec(root: Path, project_id: str, take_id: str) -> dict[str, Any]:
    """Resolve somente os dados locais aprovados necessarios para um passe I2V."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = next((item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id), None)
    if take is None:
        raise FileNotFoundError(take_id)
    if bool(take.get("video_generation_forbidden") or queue.get("video_generation_forbidden")):
        raise ValueError(
            str(
                take.get("video_generation_block_reason")
                or queue.get("video_generation_block_reason")
                or "Projeto reservado para revisao de imagens; geracao de video desativada."
            ).strip()
        )
    generation = take.get("video_generation") if isinstance(take.get("video_generation"), dict) else {}
    generation_profile = str(
        generation.get("profile") or ENGINE_SELECTION_REQUIRED_PROFILE
    ).strip().lower()
    if generation_profile in {
        *REMOVED_LTX23_GENERATION_PROFILES,
        LTX25_TWO_ANCHOR_PROFILE,
        REMOVED_MINIMAX_H3_LEGACY_PROFILE,
    }:
        raise ValueError(
            "O perfil legado foi removido. Escolha explicitamente MiniMax H3."
        )
    allowed_generation_profiles = {
        *MINIMAX_H3_GENERATION_PROFILES,
    }
    if generation_profile not in allowed_generation_profiles:
        raise ValueError(
            "video_generation.profile deve selecionar MiniMax H3."
        )
    full_frame_wan_blocked, full_frame_wan_block_reason = _full_frame_wan_block(
        project_dir
    )
    if (
        full_frame_wan_blocked
        and generation_profile not in MINIMAX_H3_GENERATION_PROFILES
        and generation_profile != LTX25_TWO_ANCHOR_PROFILE
    ):
        raise ValueError(full_frame_wan_block_reason)
    if _upscale_candidate_path(project_dir, take, pending_only=True) is not None:
        raise ValueError(
            "Decida o candidato FHD pendente antes de gerar outra versao do take."
        )

    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if not _base_status_is_approved(base.get("status")):
        raise ValueError("A imagem-base precisa estar aprovada para video.")
    if base.get("candidate_request_id"):
        try:
            keyframe, _metadata_path, _base, _sidecar, _image_info, _image_sha256 = (
                _validated_registered_anchor(
                    project_dir,
                    take,
                    allowed_statuses={ANCHOR_APPROVED_STATUS},
                )
            )
        except FileNotFoundError as exc:
            raise ValueError("Imagem-ancora aprovada ausente ou fora do projeto.") from exc
    else:
        keyframe_raw = str(base.get("file") or "").strip()
        if not keyframe_raw:
            raise ValueError("Take sem imagem-base.")
        keyframe = Path(keyframe_raw)
        if not keyframe.is_absolute():
            keyframe = project_dir / keyframe
        keyframe = keyframe.resolve()
        if not keyframe.is_relative_to(project_dir.resolve()) or not keyframe.is_file():
            raise ValueError("Imagem-base ausente ou fora do projeto.")

    shot = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
    _validate_continuous_action_generation_contract(queue, take)
    take_execution_contract = _validate_take_execution_contract(
        queue,
        take,
        generation_profile=generation_profile,
    )
    end_frame_enabled = bool(
        generation.get("start_end_frame_enabled", True)
    )
    end_keyframe = (
        _take_end_keyframe_path(project_dir, take)
        if (
            generation_profile == LTX25_TWO_ANCHOR_PROFILE
            or generation_profile in MINIMAX_H3_GENERATION_PROFILES
        )
        and end_frame_enabled
        else None
    )
    if bool(generation.get("require_approved_end_frame", False)) and end_keyframe is None:
        raise ValueError(
            "Este take exige duas ancoras aprovadas; a ancora final ainda nao esta disponivel."
        )
    minimax_anchor_control: dict[str, Any] = {}
    wan_animate_control: dict[str, Any] = {}
    if generation_profile in MINIMAX_H3_GENERATION_PROFILES:
        minimax_anchor_control = _validate_minimax_h3_anchor_control(
            project_dir,
            take,
            keyframe=keyframe,
            end_keyframe=end_keyframe,
        )
    prompt = _production_motion_prompt(take, shot)
    if minimax_anchor_control.get("mode") == "ref2va_motion":
        ref2va_override = str(take.get("minimax_ref2va_prompt_override") or "").strip()
        if ref2va_override:
            prompt = ref2va_override
    if not prompt:
        raise ValueError("Take sem animation_prompt.")
    internet_direction = internet_publication.generation_direction(
        project_dir, take_id,
        [str(item.get("id") or "") for item in queue.get("takes", [])
         if isinstance(item, dict) and item.get("role") != "project_final_output"],
    )
    if internet_direction:
        prompt = f"{prompt}\n{internet_direction}"
    mode_prompt = _take_mode_prompt(take)
    if mode_prompt:
        prompt = f"{prompt} {mode_prompt}"
    correction_prompt = _director_correction_prompt(take)
    if correction_prompt:
        prompt = f"{prompt} {correction_prompt}"
    negatives = [
        "static hold", "simple zoom only", "living photo", "subject replacement",
        "identity drift", "intrusive geometric object", "cube", "box", "block",
        "fake text", "watermark", "camera rig", "camera operator", "sudden cut",
    ]
    negatives.extend(queue.get("global_negative_rules") or [])
    negatives.extend(shot.get("negative_rules") or [])
    negative = ", ".join(dict.fromkeys(str(item).strip() for item in negatives if str(item).strip()))
    variants = shot.get("variants") if isinstance(shot.get("variants"), dict) else {}
    duration = float(variants.get("duration_seconds") or take.get("target_duration_seconds") or 4)
    is_minimax_h3 = generation_profile in MINIMAX_H3_GENERATION_PROFILES
    is_ltx25 = False  # LTX removed; historical files and profiles remain readable.
    is_minimax_h3_vertical = generation_profile == MINIMAX_H3_VERTICAL_PROFILE
    is_minimax_h3_owner_30s = (
        generation_profile == MINIMAX_H3_OWNER_30S_NATIVE_AV_PROFILE
    )
    h3_quality_profile_id = ""
    h3_quality_profile: dict[str, Any] = {}
    if is_minimax_h3:
        requested_h3_profile = str(generation.get("quality_profile") or "").strip()
        if requested_h3_profile:
            h3_quality_profile_id, h3_quality_profile, is_minimax_h3_vertical = (
                resolve_h3_quality_profile(
                    requested_h3_profile,
                    width=generation.get("width"),
                    height=generation.get("height"),
                    steps=generation.get("steps"),
                )
            )
        else:
            # Persisted projects without a quality profile retain the exact
            # former 720p/20-step contract.
            h3_quality_profile_id, h3_quality_profile, _ = resolve_h3_quality_profile(
                "h3_legacy_720p"
            )
    if is_minimax_h3_owner_30s:
        engine_policy = (
            queue.get("engine_policy")
            if isinstance(queue.get("engine_policy"), dict)
            else {}
        )
        owner_override = (
            engine_policy.get("minimax_h3_owner_long_av")
            if isinstance(engine_policy.get("minimax_h3_owner_long_av"), dict)
            else {}
        )
        if not (
            bool(owner_override.get("enabled"))
            and bool(owner_override.get("native_audio_authorized"))
            and int(owner_override.get("frames") or 0) == 736
            and str(owner_override.get("owner_directive") or "").strip()
        ):
            raise ValueError(
                "O perfil MiniMax H3 longo exige override audiovisual explicito do proprietario no projeto."
            )
    duration_limit = (
        30.625
        if is_minimax_h3_owner_30s
        else 15.0
        if is_minimax_h3
        else 30.0
        if is_ltx25
        else 6.0
    )
    duration = max(2.0, min(duration_limit, duration))
    try:
        fps = float(
            generation.get(
                "fps",
                24
                if is_ltx25 or is_minimax_h3
                else 30,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("video_generation.fps invalido.") from exc
    if not 1 <= fps <= 60:
        raise ValueError("video_generation.fps deve ficar entre 1 e 60.")
    try:
        if is_minimax_h3:
            default_frames = max(
                124,
                int(round((duration * fps - 5) / 17)) * 17 + 5,
            )
        else:
            frame_multiple = 8 if is_ltx25 else 4
            default_frames = int(round((duration * fps) / frame_multiple)) * frame_multiple + 1
        frames = int(generation.get("frames") or default_frames)
    except (TypeError, ValueError) as exc:
        raise ValueError("video_generation.frames invalido.") from exc
    if is_minimax_h3_owner_30s:
        if frames != 736 or (frames - 5) % 17:
            raise ValueError(
                "O perfil MiniMax H3 direto de 30 segundos exige exatamente 736 quadros (17k+5)."
            )
    elif is_minimax_h3:
        if not 124 <= frames <= 362 or (frames - 5) % 17:
            raise ValueError(
                "O perfil MiniMax H3 FL2VA exige 17k+5 entre 124 e 362 quadros."
            )
    elif is_ltx25:
        if not 25 <= frames <= 721 or (frames - 1) % 8:
            raise ValueError("O perfil LTX 2.5 exige 8n+1 entre 25 e 721 quadros.")
    elif not 25 <= frames <= 601 or (frames - 1) % 4:
        raise ValueError("video_generation.frames deve ser 4n+1 entre 25 e 601.")

    try:
        width = int(
            generation.get(
                "width",
                h3_quality_profile["verticalWidth"]
                if is_minimax_h3 and is_minimax_h3_vertical
                else h3_quality_profile["width"] if is_minimax_h3
                else 960 if is_ltx25
                else 768,
            )
        )
        height = int(
            generation.get(
                "height",
                h3_quality_profile["verticalHeight"]
                if is_minimax_h3 and is_minimax_h3_vertical
                else h3_quality_profile["height"] if is_minimax_h3
                else 544 if is_ltx25
                else 432,
            )
        )
        steps = int(
            generation.get(
                "steps",
                8
                if is_ltx25
                else int(h3_quality_profile["steps"][0]) if is_minimax_h3 else 16,
            )
        )
        guidance = float(
            generation.get(
                "guidance",
                1.0 if is_ltx25 or is_minimax_h3 else 6.0,
            )
        )
        camera_speed = float(generation.get("camera_speed", 0.8))
    except (TypeError, ValueError) as exc:
        raise ValueError("video_generation contem parametro numerico invalido.") from exc
    if not 512 <= width <= 2048 or width % 16:
        raise ValueError("video_generation.width deve ser multiplo de 16 entre 512 e 2048.")
    maximum_height = (
        1280
        if is_minimax_h3_vertical
        else 1152
    )
    if not 288 <= height <= maximum_height or height % 16:
        raise ValueError(
            "video_generation.height deve ser multiplo de 16 entre 288 e "
            f"{maximum_height}."
        )
    if not 6 <= steps <= 60:
        raise ValueError("video_generation.steps deve ficar entre 6 e 60.")
    if not 1.0 <= guidance <= 12.0:
        raise ValueError("video_generation.guidance deve ficar entre 1 e 12.")
    if not 0.0 <= camera_speed <= 10.0:
        raise ValueError("video_generation.camera_speed deve ficar entre 0 e 10.")

    camera_pose = str(generation.get("camera_pose") or "").strip()
    allowed_camera_poses = {
        "", "Static", "Pan Up", "Pan Down", "Pan Left", "Pan Right",
        "Zoom In", "Zoom Out", "Anti Clockwise (ACW)", "ClockWise (CW)",
    }
    if camera_pose not in allowed_camera_poses:
        raise ValueError("video_generation.camera_pose invalido.")
    if is_ltx25:
        if (width, height) != (960, 544):
            raise ValueError("O perfil LTX 2.5 Two-Stage exige 960x544 na primeira etapa.")
        if fps != 24:
            raise ValueError("O perfil LTX 2.5 exige 24 FPS.")
        if steps != 8:
            raise ValueError("O perfil LTX 2.5 destilado exige 8 steps na primeira etapa.")
        if guidance != 1.0:
            raise ValueError("O perfil LTX 2.5 destilado exige guidance 1.0.")
    elif is_minimax_h3:
        expected_geometry = (
            (h3_quality_profile["verticalWidth"], h3_quality_profile["verticalHeight"])
            if is_minimax_h3_vertical
            else (h3_quality_profile["width"], h3_quality_profile["height"])
        )
        if (width, height) != expected_geometry:
            raise ValueError(
                "O perfil MiniMax H3 FL2VA selecionado exige "
                f"{expected_geometry[0]}x{expected_geometry[1]}."
            )
        if fps != 24:
            raise ValueError("O perfil MiniMax H3 FL2VA exige 24 FPS nativos.")
        if steps not in h3_quality_profile["steps"]:
            allowed = "-".join(
                map(str, (min(h3_quality_profile["steps"]), max(h3_quality_profile["steps"])))
            )
            raise ValueError(
                f"O perfil {h3_quality_profile['label']} exige {allowed} steps."
            )
        if guidance != 1.0:
            raise ValueError("O perfil MiniMax H3 FL2VA exige guidance contratual 1.0.")
    production_manifest = _read_json(project_dir / "production_manifest.json")
    transition_gate = (
        production_manifest.get("universal_transition_motion_gate")
        if isinstance(production_manifest.get("universal_transition_motion_gate"), dict)
        else {}
    )
    # A transicao exige deslocamento fisico evidente. O condicionamento visual
    # identity_locked pode dominar o latente e colapsar o Wan em uma living
    # photo; nesses projetos, o gate editorial tem precedencia sobre o perfil
    # legado copiado para cada take.
    if (
        bool(transition_gate.get("required"))
        and generation_profile in {
            "wan22_a14b_identity_v1",
            "wan22_a14b_motion_v1",
        }
    ):
        generation_profile = "wan22_fun_camera_v1"
        camera_pose = _transition_camera_pose(shot, prompt)
    if bool(transition_gate.get("required")) and is_minimax_h3:
        camera_contract = (
            shot.get("camera") if isinstance(shot.get("camera"), dict) else {}
        )
        camera_movement = str(camera_contract.get("movement") or "").strip().casefold()
        fixed_camera = (
            camera_contract.get("physical_translation") is False
            and any(token in camera_movement for token in ("fixed", "locked", "tripod"))
        )
        if fixed_camera:
            prompt = (
                f"{prompt} "
                "Keep the approved physical camera fixed on its tripod with no pan, "
                "tilt, dolly, orbit or digital zoom. Prove continuous action through "
                "full-body performer displacement and at least two independently moving "
                "physical elements such as cloth, hair, dust or air pressure; the midpoint "
                "and ending must have visibly changed body geometry and physical state. "
                "Do not introduce typography, labels, interface copy or overlays."
            )
        else:
            prompt = (
                f"{prompt} "
                "Use unmistakable physical camera translation through the set, with "
                "foreground occlusion changing against the midground and background "
                "during the first second. At least two existing environmental elements "
                "move independently, and the midpoint and ending have visibly changed "
                "geometry and physical state. Keep reserved caption bands, document "
                "surfaces and graphic panels exactly as established by the reference; "
                "do not introduce any new typography, labels, interface copy or overlay."
            )
    elif bool(transition_gate.get("required")):
        prompt = (
            f"{prompt} "
            "TRANSITION MOTION COMPLIANCE IS MANDATORY: execute the stated "
            "physical camera translation with unmistakable displacement through "
            "the set, never a pan, digital zoom or nearly locked frame. Within "
            "the first second, foreground occlusion must visibly change against "
            "the midground and background. Amplify at least two named existing "
            "environmental actions so they move independently of the camera. "
            "The midpoint and final frame must have clearly different geometry, "
            "overlap and physical state from the first frame. Preserve every "
            "approved object and the 16:9 composition, but never preserve "
            "stillness; a living photo is a failed render."
        )
    conditioning_profile = (
        "manus_motion"
        if generation_profile == "wan22_a14b_motion_v1"
        else "wan_animate_exact_pose"
        if generation_profile == WAN22_ANIMATE_PROFILE
        else "identity_locked"
    )
    audio_direction = (
        take.get("audio_direction")
        if isinstance(take.get("audio_direction"), dict)
        else {}
    )
    audio_directive = (
        take.get("audio_directive")
        if isinstance(take.get("audio_directive"), dict)
        else {}
    )
    audio_strategy = str(audio_direction.get("strategy") or "").strip().lower()
    dialogue_tracks = (
        take.get("dialogue_tracks")
        if isinstance(take.get("dialogue_tracks"), list)
        else []
    )
    narration_tracks = (
        take.get("narration_tracks")
        if isinstance(take.get("narration_tracks"), list)
        else []
    )
    has_dialogue = any(isinstance(item, dict) for item in dialogue_tracks)
    if audio_strategy == "minimax_h3_native_scene":
        if not is_minimax_h3:
            raise ValueError("Audio nativo da cena exige o motor MiniMax H3 autorizado.")
        if not bool(audio_directive.get("usage_authorized", False)):
            raise ValueError("Audio nativo da cena MiniMax H3 exige diretiva explicita do proprietario.")
    if audio_strategy == "minimax_h3_native_narration_ptbr":
        if not is_minimax_h3:
            raise ValueError("Narracao nativa MiniMax H3 exige o motor H3 autorizado.")
        if not bool(audio_directive.get("usage_authorized", False)):
            raise ValueError("O audio nativo MiniMax H3 exige diretiva explicita do proprietario.")
        prompt = _minimax_h3_native_ptbr_narration_prompt(
            prompt,
            narration_tracks,
            audio_direction,
        )
    elif audio_strategy == "minimax_h3_native_music":
        if not is_minimax_h3:
            raise ValueError("Musica nativa exige o motor MiniMax H3 autorizado.")
        if not bool(audio_directive.get("usage_authorized", False)):
            raise ValueError("O audio nativo MiniMax H3 exige diretiva explicita do proprietario.")
        music_direction = str(
            audio_directive.get("music_direction")
            or audio_directive.get("music")
            or ""
        ).strip()
        prompt_music = (
            take.get("h3_prompt_audio")
            if isinstance(take.get("h3_prompt_audio"), dict)
            else {}
        )
        if not music_direction:
            music_direction = str(
                prompt_music.get("non_diegetic_music") or ""
            ).strip()
        if not music_direction or music_direction.upper() == "N/A":
            raise ValueError("Musica nativa MiniMax H3 exige direcao musical explicita.")
    visual_only_pass = bool(
        (
            is_minimax_h3
            and not bool(audio_directive.get("usage_authorized", False))
        )
        or
        audio_strategy in {"visual_pass_adr", "visual_only", "external_adr_after_visual_qc"}
        or (
            has_dialogue
            and audio_direction.get("dialogue_generation_authorized") is False
        )
    )
    h3_prompt_contract: dict[str, Any] = {}
    if is_minimax_h3:
        soundscape, music = _h3_prompt_audio_sections(
            take,
            shot,
            visual_only_pass=visual_only_pass,
        )
        if minimax_anchor_control.get("mode") == "ref2va_motion":
            definitions = [
                f"{item['label']} is {item['description']} Its approved sources are "
                f"{', '.join(item['sources'])}."
                for item in minimax_anchor_control.get("referenceSubjects", [])
            ]
            if minimax_anchor_control.get("referenceVideo") is not None:
                asset_type = str(
                    minimax_anchor_control.get("referenceVideoAssetType") or ""
                ).strip().lower()
                if asset_type in {"dwpose_pose_video", "openpose_pose_video"}:
                    definitions.append(
                        "<Video 1> is a pose visualization used only as a motion reference; "
                        "Ref2VA does not provide exact joint control, and all photographic appearance comes from the pictures."
                    )
                else:
                    definitions.append(
                        "<Video 1> is an approved RGB motion reference, not DWPose and not an appearance source; "
                        "it may guide approximate timing only, while all photographic appearance comes from the pictures."
                    )
            subject_labels = ", ".join(
                item["label"] for item in minimax_anchor_control.get("referenceSubjects", [])
            )
            document = compile_ref_prompt(
                subject_definitions="\n".join(definitions),
                summary=(
                    f"[reference generation] Create a strictly photographic live-action video using {subject_labels}. "
                    "The pictures define the subjects' appearance. "
                    + (
                        "<Video 1> provides approximate temporal structure only and is not exact pose control."
                        if minimax_anchor_control.get("referenceVideo") is not None
                        else "No reference video is supplied; motion remains prompt-guided."
                    )
                ),
                retention_analysis=(
                    "\n".join(
                        f"{item['label']} (appears in [Shot 1]): {item['relation']} - {item['retention']}"
                        for item in minimax_anchor_control.get("referenceSubjects", [])
                    )
                ),
                detailed_description=(
                    prompt if "[Shot 1]" in prompt else f"[Shot 1] {prompt}"
                ),
                overall_soundscape=soundscape,
                non_diegetic_music=music,
                duration_seconds=(frames - 1) / fps,
            )
        else:
            h3_mode = detect_base_mode(
                has_first_frame=keyframe is not None,
                has_last_frame=end_keyframe is not None,
            )
            shot_indexes = [
                int(value)
                for value in re.findall(r"\[Shot\s+(\d+)\]", prompt, flags=re.IGNORECASE)
            ]
            document = compile_base_prompt(
                prompt,
                mode=h3_mode,
                duration_seconds=(frames - 1) / fps,
                overall_soundscape=soundscape,
                non_diegetic_music=music,
                final_shot=max(shot_indexes or [1]),
            )
        prompt = document.prompt
        h3_prompt_contract = {
            "enabled": True,
            "mode": document.mode,
            "contractVersion": document.contract_version,
            "officialCommit": document.official_commit,
            "localOnly": True,
            "externalApi": False,
        }
    audio_conditioning: Path | None = None
    audio_synthesis_spec: dict[str, Any] = {}
    (
        cast_contract_known,
        expected_human_cast,
        expected_non_human_cast,
        expected_visible_cast,
    ) = _take_visible_cast_contract(take)
    anchor_policy = (
        queue.get("anchor_generation_policy")
        if isinstance(queue.get("anchor_generation_policy"), dict)
        else {}
    )
    require_verified_anchor_cast = bool(
        anchor_policy.get("require_visual_cast_verification_for_video", False)
    )
    anchor_visible_cast = _anchor_visible_cast(
        project_dir,
        keyframe,
        base,
        require_verified=require_verified_anchor_cast,
    )
    if cast_contract_known and require_verified_anchor_cast and anchor_visible_cast is None:
        raise ValueError(
            "CAST_ANCHOR_UNVERIFIED: a imagem-base aprovada ainda nao possui "
            "conferencia visual do elenco presente nos pixels. Verifique a ancora "
            "e registre visual_qc.actual_visible_characters antes de usar a GPU."
        )
    if cast_contract_known and anchor_visible_cast is not None:
        expected_keys = {item.casefold() for item in expected_visible_cast}
        anchor_keys = {item.casefold() for item in anchor_visible_cast}
        if expected_keys != anchor_keys:
            anchor_label = ", ".join(anchor_visible_cast) or "nenhum personagem"
            expected_label = ", ".join(expected_visible_cast) or "nenhum personagem"
            raise ValueError(
                "CAST_ANCHOR_MISMATCH: a imagem-base aprovada mostra exatamente "
                f"{anchor_label}, mas o prompt exige {expected_label}. "
                "Refatore o take ou aprove uma ancora com o mesmo elenco antes de gerar."
            )
    editorial_lettering_raw = (
        take.get("editorial_lettering")
        if isinstance(take.get("editorial_lettering"), dict)
        else {}
    )
    editorial_lettering: dict[str, Any] = {}
    if bool(editorial_lettering_raw.get("enabled")):
        language = str(editorial_lettering_raw.get("language") or "").strip()
        source_raw = str(editorial_lettering_raw.get("ass_file") or "").strip()
        source = Path(source_raw).resolve() if source_raw else None
        if language != "pt-BR":
            raise ValueError("Lettering editorial obrigatorio deve usar portugues do Brasil.")
        if (
            source is None
            or not source.is_relative_to(project_dir.resolve())
            or not source.is_file()
            or source.suffix.lower() != ".ass"
        ):
            raise ValueError("Arquivo ASS pt-BR do lettering editorial esta indisponivel.")
        expected_sha256 = str(
            editorial_lettering_raw.get("ass_sha256") or ""
        ).strip().lower()
        actual_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        if expected_sha256 and expected_sha256 != actual_sha256:
            raise ValueError("Arquivo ASS pt-BR do lettering editorial foi alterado.")
        editorial_lettering = {
            "enabled": True,
            "required": bool(editorial_lettering_raw.get("required", True)),
            "language": language,
            "assFile": source,
            "assFileName": source.name,
            "assSha256": actual_sha256,
        }
    camera_contract = project_dir / "sequence_camera_contract.json"
    if camera_contract.is_file():
        from sequence_camera_contract import load_and_validate
        load_and_validate(camera_contract, take_id=take_id, stage='generation')
    return {
        "projectId": project_dir.name,
        "takeId": take_id,
        "status": _take_status(take),
        "sequenceCameraRequired": camera_contract.is_file(),
        "sequenceCameraContract": str(camera_contract) if camera_contract.is_file() else None,
        "lastJobId": str(take.get("maestro_last_job_id") or ""),
        "prompt": prompt,
        "negative": negative,
        "keyframe": keyframe,
        "keyframeName": keyframe.name,
        "endKeyframe": end_keyframe,
        "endKeyframeName": end_keyframe.name if end_keyframe is not None else "",
        "generationProfile": generation_profile,
        "h3QualityProfile": h3_quality_profile_id,
        "width": width,
        "height": height,
        "fps": fps,
        "frames": frames,
        "steps": steps,
        "guidance": guidance,
        "cameraPose": camera_pose,
        "cameraSpeed": camera_speed,
        "videoConditioningProfile": conditioning_profile,
        "durationSeconds": (frames - 1) / fps,
        "visualOnlyPass": visual_only_pass,
        "audioStrategy": audio_strategy,
        "h3PromptContract": h3_prompt_contract,
        "internetDirection": {
            "enabled": bool(internet_direction),
            "profile": internet_publication.PROFILE if internet_direction else None,
            "sha256": hashlib.sha256(internet_direction.encode("utf-8")).hexdigest() if internet_direction else None,
        },
        "minimaxAnchorControl": minimax_anchor_control,
        "wanAnimateControl": wan_animate_control,
        "takeExecutionContract": take_execution_contract,
        "h3LivePreview": bool(generation.get("h3_live_preview", False)),
        "audioConditioning": audio_conditioning,
        "audioConditioningName": audio_conditioning.name if audio_conditioning else "",
        "audioSynthesisSpec": audio_synthesis_spec,
        "castContractKnown": cast_contract_known,
        "expectedHumanCast": [
            str(item).strip() for item in expected_human_cast if str(item).strip()
        ],
        "expectedNonHumanCast": [
            str(item).strip() for item in expected_non_human_cast if str(item).strip()
        ],
        "anchorVisibleCast": anchor_visible_cast,
        "editorialLettering": editorial_lettering,
        "distinctStoryEvents": max(1, int(shot.get("distinct_story_events") or 1)),
    }


def get_take_upscale_spec(root: Path, project_id: str, take_id: str) -> dict[str, Any]:
    """Resolve o candidato aprovado que pode entrar no passe FHD real."""

    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue = _queue(project_dir)
    take = next(
        (item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id),
        None,
    )
    if take is None:
        raise FileNotFoundError(take_id)
    status = _take_status(take)
    if status not in {"APPROVED", "UPSCALING"}:
        raise ValueError("Somente take aprovado pode entrar no upscale 1080p.")
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    pending_candidate = _upscale_candidate_path(project_dir, take, pending_only=True)
    if pending_candidate is not None:
        raise ValueError("Este take possui candidato de upscale aguardando revisao humana.")

    # A previous approved FHD output is not a lock. A new profile may be run
    # from the preserved review/raw source without recursively upscaling the
    # former FHD active output.
    source = None
    active = _valid_project_video_path(project_dir, video.get("output_active"))
    approved_upscaled = _valid_project_video_path(project_dir, video.get("output_upscaled"))
    source_fields = [
        "output_active",
        "output_review_candidate",
        "output_preview",
        "output_upscaled",
    ]
    if active is not None and approved_upscaled is not None and active == approved_upscaled:
        source_fields = [
            "output_review_candidate",
            "output_preview",
            "output_active",
            "output_upscaled",
        ]
    for field in source_fields:
        raw = str(video.get(field) or "").strip()
        if not raw:
            continue
        candidate = _valid_project_video_path(project_dir, raw)
        if candidate is not None:
            source = candidate
            break
    if source is None:
        raise ValueError("Take aprovado sem video bruto valido para upscale.")
    target_width, target_height = _project_final_geometry(project_dir)
    current_upscale_status = str(take.get("maestro_upscale_status") or "").upper()
    current_attempt = int(take.get("maestro_upscale_attempt") or 0)
    if (
        status == "UPSCALING"
        and current_upscale_status in {"QUEUED", "UPSCALING"}
        and current_attempt <= 0
    ):
        # Legacy in-flight jobs predate explicit attempts; expose them as the
        # first attempt so recovery can migrate the state safely.
        current_attempt = 1
    next_attempt = (
        current_attempt
        if status == "UPSCALING" and current_upscale_status in {"QUEUED", "UPSCALING"}
        else current_attempt + 1
    )
    return {
        "projectId": project_dir.name,
        "takeId": take_id,
        "status": status,
        "lastJobId": str(
            take.get("maestro_upscale_job_id")
            or (
                take.get("maestro_last_job_id")
                if current_upscale_status
                else ""
            )
            or ""
        ),
        "upscaleAttempt": current_attempt,
        "nextUpscaleAttempt": next_attempt,
        "source": source,
        "outputDir": (project_dir / "qc" / "upscaled").resolve(),
        "workDir": (project_dir / "qc" / "maestro_upscale_work").resolve(),
        "name": f"take_{take_id}",
        "targetWidth": target_width,
        "targetHeight": target_height,
    }


def set_take_upscale_state(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    status: str,
    job_id: str = "",
    attempt: int | None = None,
    error: str = "",
    output_path: Path | None = None,
    sidecar_path: Path | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist an upscale worker transition without granting human approval."""

    status = str(status or "").upper()
    if status not in {"QUEUED", "UPSCALING", "READY", "ERROR", "CANCELED"}:
        raise ValueError("estado de upscale invalido.")
    job_id = str(job_id or "").strip()[:64]
    if not job_id:
        raise ValueError("jobId do upscale e obrigatorio.")
    if attempt is not None:
        if isinstance(attempt, bool) or int(attempt) <= 0:
            raise ValueError("attempt do upscale deve ser um inteiro positivo.")
        attempt = int(attempt)
    with _QUEUE_MUTATION_LOCK:
        project_dir = _project_path(root, project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(project_id)
        take_id = _validate_take_id(take_id)
        queue_path = _queue_path(project_dir)
        queue = _queue(project_dir)
        take = next(
            (item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id),
            None,
        )
        if take is None:
            raise FileNotFoundError(take_id)

        current_upscale_status = str(take.get("maestro_upscale_status") or "").upper()
        current_job_id = str(
            take.get("maestro_upscale_job_id")
            or (
                take.get("maestro_last_job_id")
                if current_upscale_status
                else ""
            )
            or ""
        )
        current_attempt = int(take.get("maestro_upscale_attempt") or 0)
        candidate_record = _upscale_candidate_record(take)
        candidate_status = (
            str(candidate_record.get("status") or "").upper()
            if candidate_record is not None
            else ""
        )

        if status == "QUEUED":
            same_job = bool(
                current_upscale_status in {"QUEUED", "UPSCALING"}
                and current_job_id
                and current_job_id == job_id
            )
            if not same_job:
                if current_upscale_status in {"QUEUED", "UPSCALING"}:
                    raise ValueError("Este take ja possui outro job de upscale em andamento.")
                if candidate_status == "PENDING_HUMAN_REVIEW":
                    raise ValueError("Candidato de upscale ainda aguarda revisao humana.")
                if _take_status(take) != "APPROVED":
                    raise ValueError("Somente take aprovado pode entrar no upscale 1080p.")
                expected_attempt = current_attempt + 1
                if attempt is not None and attempt != expected_attempt:
                    raise ValueError("Tentativa de upscale nao corresponde a proxima tentativa.")
                current_attempt = expected_attempt
                take["maestro_pre_upscale_status"] = _take_status(take)
                video = take.get("video") if isinstance(take.get("video"), dict) else {}
                if isinstance(video, dict):
                    video.pop("upscale_candidate", None)
                    video.pop("output_upscale_candidate", None)
                    video.pop("upscale_candidate_metadata", None)
            else:
                if current_attempt <= 0:
                    current_attempt = 1
                if attempt is not None and attempt != current_attempt:
                    raise ValueError("Resultado pertence a uma tentativa antiga de upscale.")
        else:
            if not current_job_id or current_job_id != job_id:
                raise ValueError("Resultado pertence a um job antigo e nao pode substituir o job atual.")
            if attempt is not None and attempt != current_attempt:
                raise ValueError("Resultado pertence a uma tentativa antiga de upscale.")
            if current_upscale_status in {"APPROVED", "REJECTED"}:
                raise ValueError("Resultado de worker nao pode sobrescrever a decisao humana do upscale.")
            allowed_current_states = {
                "UPSCALING": {"QUEUED", "UPSCALING"},
                "READY": {"QUEUED", "UPSCALING", "READY"},
                "ERROR": {"QUEUED", "UPSCALING"},
                "CANCELED": {"QUEUED", "UPSCALING"},
            }
            if current_upscale_status not in allowed_current_states[status]:
                raise ValueError("Transicao de upscale nao corresponde ao estado atual do job.")

        if status == "READY" and output_path is None:
            raise ValueError("Saida de upscale e obrigatoria no estado READY.")

        restored_status = str(take.get("maestro_pre_upscale_status") or "APPROVED").upper()
        if restored_status not in TAKE_STATUSES or restored_status == "UPSCALING":
            restored_status = "APPROVED"
        take["maestro_status"] = "READY" if status == "READY" else (
            restored_status if status in {"ERROR", "CANCELED"} else "UPSCALING"
        )
        take["maestro_upscale_status"] = status
        take["maestro_upscale_error"] = str(error or "")[:4000]
        take["maestro_upscale_job_id"] = job_id
        take["maestro_upscale_attempt"] = current_attempt
        # Keep the legacy field synchronized while callers migrate to the
        # dedicated upscale job identity.
        take["maestro_last_job_id"] = job_id
        take["maestro_updated_at"] = utc_now()
        if result is not None:
            take["maestro_last_result"] = result
        video = take.setdefault("video", {})
        if isinstance(video, dict):
            video["upscale_status"] = status.lower()
            if status == "READY" and output_path is not None:
                candidate = _valid_project_video_path(project_dir, output_path)
                if candidate is None:
                    raise ValueError("Saida de upscale ausente ou fora do projeto.")
                metadata = ""
                if sidecar_path is not None:
                    sidecar = sidecar_path.resolve()
                    if (
                        not sidecar.is_relative_to(project_dir.resolve())
                        or not sidecar.is_file()
                    ):
                        raise ValueError("Sidecar do upscale ausente ou fora do projeto.")
                    metadata = str(sidecar)
                technical_ready_at = utc_now()
                pending_record = {
                    "path": str(candidate),
                    "metadata": metadata,
                    "status": "PENDING_HUMAN_REVIEW",
                    "job_id": job_id,
                    "attempt": current_attempt,
                    "technical_ready_at": technical_ready_at,
                }
                video["upscale_candidate"] = pending_record
                video["output_upscale_candidate"] = str(candidate)
                video["upscale_candidate_metadata"] = metadata
                video["upscale_status"] = "pending_human_review"
                video["status"] = "ready"
        qc = take.setdefault("qc", {})
        if isinstance(qc, dict):
            if status == "READY":
                qc["status"] = "upscale_ready_for_user_review"
            elif status in {"ERROR", "CANCELED"}:
                qc["status"] = "approved_raw_upscale_pending"
            elif status in {"QUEUED", "UPSCALING"}:
                qc["status"] = "upscale_in_progress"
        _atomic_json_write(queue_path, queue)
        return _take_view(take, project_dir)


def set_take_generation_state(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    status: str,
    job_id: str = "",
    error: str = "",
    result: dict[str, Any] | None = None,
    preview_path: Path | None = None,
) -> dict[str, Any]:
    with _QUEUE_MUTATION_LOCK:
        return _set_take_generation_state_locked(
            root,
            project_id,
            take_id,
            status=status,
            job_id=job_id,
            error=error,
            result=result,
            preview_path=preview_path,
        )


def _set_take_generation_state_locked(
    root: Path,
    project_id: str,
    take_id: str,
    *,
    status: str,
    job_id: str = "",
    error: str = "",
    result: dict[str, Any] | None = None,
    preview_path: Path | None = None,
) -> dict[str, Any]:
    """Persiste a fase do job sem permitir alteracoes arbitrarias no contrato do take."""

    status = str(status or "").upper()
    if status not in {"QUEUED", "GENERATING", "READY", "ERROR"}:
        raise ValueError("estado de geracao invalido.")
    project_dir = _project_path(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(project_id)
    take_id = _validate_take_id(take_id)
    queue_path = _queue_path(project_dir)
    queue = _queue(project_dir)
    take = next((item for item in queue["takes"] if isinstance(item, dict) and str(item.get("id")) == take_id), None)
    if take is None:
        raise FileNotFoundError(take_id)
    pending_upscale_candidate = _upscale_candidate_record(take)
    if (
        pending_upscale_candidate is not None
        and str(pending_upscale_candidate.get("status") or "").upper()
        == "PENDING_HUMAN_REVIEW"
    ):
        raise ValueError(
            "Decida o candidato FHD pendente antes de gerar outra versao do take."
        )
    current_job_id = str(take.get("maestro_last_job_id") or "")
    if (
        status in {"GENERATING", "READY", "ERROR"}
        and job_id
        and current_job_id
        and current_job_id != str(job_id)
    ):
        raise ValueError("Resultado pertence a um job antigo e nao pode substituir o job atual.")
    take["maestro_status"] = status
    take["maestro_last_job_id"] = str(job_id or take.get("maestro_last_job_id") or "")[:64]
    take["maestro_last_error"] = str(error or "")[:4000]
    take["maestro_updated_at"] = utc_now()
    latest_director_request = _latest_director_request(take)
    latest_director_status = str((latest_director_request or {}).get("status") or "").upper()
    latest_director_category = str((latest_director_request or {}).get("category") or "").upper()
    # Pedidos ANCHOR só mudam de estado quando uma foto-base é entregue pela
    # rota própria. Um job de vídeo não é evidência de executor trabalhando
    # nessa foto e nunca deve transformar o pedido em "em andamento".
    if latest_director_category != "ANCHOR":
        if status in {"QUEUED", "GENERATING"} and latest_director_status in {"PENDING", "IN_PROGRESS"}:
            _set_latest_director_request_status(take, "IN_PROGRESS")
        elif status == "READY" and latest_director_status == "IN_PROGRESS":
            _set_latest_director_request_status(take, "DELIVERED")
        elif status == "ERROR" and latest_director_status == "IN_PROGRESS":
            _set_latest_director_request_status(take, "PENDING")
    if result is not None:
        take["maestro_last_result"] = result
        video = take.setdefault("video", {})
        if isinstance(video, dict):
            video["status"] = "ready" if status == "READY" else status.lower()
            outputs = result.get("outputs") if isinstance(result, dict) else None
            if isinstance(outputs, list) and outputs:
                latent_output = next(
                    (item for item in outputs if isinstance(item, dict) and item.get("kind") == "latent"),
                    {},
                )
                video["latent_file"] = str(latent_output.get("filename") or "")
            audio_delivery = (
                result.get("audio_delivery")
                if isinstance(result, dict) and isinstance(result.get("audio_delivery"), dict)
                else None
            )
            if audio_delivery is not None:
                video["audio_delivery"] = audio_delivery
                audio_direction = (
                    take.get("audio_direction")
                    if isinstance(take.get("audio_direction"), dict)
                    else {}
                )
                audio_direction["delivery_required"] = bool(
                    audio_delivery.get("required", True)
                )
                audio_direction["human_listening_required"] = bool(
                    audio_delivery.get("human_listening_required")
                )
                take["audio_direction"] = audio_direction
                qc = take.setdefault("qc", {})
                if isinstance(qc, dict) and status == "READY":
                    audio_status = str(audio_delivery.get("status") or "").upper()
                    audio_blocked = bool(
                        audio_delivery.get("approval_blocked")
                        or audio_delivery.get("approval_blocked_by_audio_text")
                        or audio_delivery.get("ready") is False
                    )
                    audio_required = bool(audio_delivery.get("required", True))
                    if not audio_required or audio_status == "NOT_REQUIRED":
                        qc["status"] = "video_pending_human_review"
                    elif audio_blocked:
                        qc["status"] = "video_preserved_audio_blocked_pending_human_review"
                    elif audio_status.startswith(("ATTACHED_", "NATIVE_")):
                        qc["status"] = "audio_attached_pending_human_review"
                    else:
                        qc["status"] = "audio_pending_voice_cast"
            review_pipeline = result.get("review_pipeline") if isinstance(result, dict) else None
            if isinstance(review_pipeline, dict) and review_pipeline.get("locked_approved") is True:
                video["review_pipeline"] = review_pipeline
                interpolation = review_pipeline.get("interpolation")
                delivery = review_pipeline.get("delivery")
                source = review_pipeline.get("source")
                if all(isinstance(item, dict) for item in (interpolation, delivery, source)):
                    video["interpolation"] = {
                        "status": "pending_human_review",
                        "pipeline_version": str(review_pipeline.get("pipeline_version") or ""),
                        "model": f"{interpolation.get('engine')} {interpolation.get('model')}",
                        "model_revision": str(interpolation.get("revision") or ""),
                        "source_fps": 24,
                        "review_fps": int(delivery.get("fps") or 60),
                        "source_frames": int(source.get("frames") or 0),
                        "review_frames": int(delivery.get("frames") or 0),
                        "duration_seconds": float(delivery.get("duration_seconds") or 0.0),
                        "width": int(delivery.get("width") or 0),
                        "height": int(delivery.get("height") or 0),
                        "encoder": str(delivery.get("encoder") or ""),
                        "upscale": False,
                        "method": str(interpolation.get("mode") or ""),
                        "playback_speed_factor": float(
                            delivery.get("speed_factor_from_midpoint_48fps") or 1.25
                        ),
                        "direct_factor5_forbidden": bool(
                            interpolation.get("direct_factor5_forbidden")
                        ),
                    }
                video["route_status"] = "RIFE425_RETIME60_PENDING_HUMAN_REVIEW"
                video["upscale_started"] = False
                video["upscale_allowed"] = False
                native_path = _valid_project_video_path(
                    project_dir,
                    review_pipeline.get("native_preview_path"),
                )
                if native_path is not None and native_path.is_file():
                    history = video.setdefault("output_history", [])
                    if not isinstance(history, list):
                        history = []
                        video["output_history"] = history
                    native_value = str(native_path)
                    if not any(
                        isinstance(item, dict) and str(item.get("path") or "") == native_value
                        for item in history
                    ):
                        history.append({
                            "path": native_value,
                            "role": "engine_native_source_24fps",
                            "replaced_at": utc_now(),
                            "replaced_by_job_id": str(job_id or ""),
                        })
                        del history[:-50]
    if preview_path is not None:
        if status != "READY":
            raise ValueError("Preview somente pode ser registrado quando o take esta READY.")
        candidate = preview_path.resolve()
        if (
            not candidate.is_relative_to(project_dir.resolve())
            or not candidate.is_file()
            or candidate.suffix.lower() not in {".mp4", ".mov", ".webm"}
        ):
            raise ValueError("Preview do take ausente ou fora do projeto.")
        video = take.setdefault("video", {})
        if not isinstance(video, dict):
            raise ValueError("Contrato de video do take e invalido.")
        previous_paths: list[tuple[str, str]] = []
        for field in (
            "output_active",
            "output_review_candidate",
            "output_preview",
            "output_upscaled",
            "output_final",
        ):
            previous = str(video.get(field) or "").strip()
            if previous and previous != str(candidate) and all(path != previous for _role, path in previous_paths):
                previous_paths.append((field, previous))
        if previous_paths:
            history = video.setdefault("output_history", [])
            if not isinstance(history, list):
                history = []
                video["output_history"] = history
            known = {
                str(item.get("path") or "")
                for item in history
                if isinstance(item, dict)
            }
            for role, previous in previous_paths:
                if previous in known:
                    continue
                history.append({
                    "path": previous,
                    "role": role,
                    "replaced_at": utc_now(),
                    "replaced_by_job_id": str(job_id or ""),
                })
                known.add(previous)
            del history[:-50]
        # The newest candidate wins in the player without deleting or
        # overwriting older approved/final files.
        video["output_active"] = str(candidate)
        video["output_preview"] = str(candidate)
        video["output_review_candidate"] = str(candidate)
        # A replacement under review supersedes the former final pointer, but
        # its file and provenance stay preserved in output_history.
        video.pop("output_final", None)
        video.pop("output_upscaled", None)
        video.pop("upscale_metadata", None)
        video["upscale_status"] = ""
        take["maestro_upscale_status"] = ""
        take["maestro_upscale_error"] = ""
    _atomic_json_write(queue_path, queue)
    return _take_view(take, project_dir)
