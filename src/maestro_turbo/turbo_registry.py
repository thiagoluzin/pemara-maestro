"""Schema checks for Messenger Turbo aliases and specialized profiles."""

from __future__ import annotations

from pathlib import PurePath
from typing import Any


class TurboRegistryError(ValueError):
    pass


def _relative_path(value: Any, field: str) -> str:
    text = str(value or "").replace("\\", "/").strip("/")
    if not text or PurePath(text).is_absolute() or ":" in text.split("/", 1)[0]:
        raise TurboRegistryError(f"{field} must be a repository-relative path")
    return text


def validate_turbo_registry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise TurboRegistryError("unsupported turbo registry")
    aliases = [str(item).strip() for item in payload.get("aliases") or []]
    specialized = [str(item).strip() for item in payload.get("specialized_profiles") or []]
    if not aliases or len(aliases) != len(set(aliases)) or any(not item for item in aliases):
        raise TurboRegistryError("aliases must be non-empty and unique")
    if len(specialized) != len(set(specialized)) or any(not item for item in specialized):
        raise TurboRegistryError("specialized_profiles must be unique")
    overlap = sorted(set(aliases) & set(specialized))
    if overlap:
        raise TurboRegistryError(f"aliases cannot replace specializations: {', '.join(overlap)}")
    dispatcher = str(payload.get("dispatcher_profile") or "").strip()
    if not dispatcher:
        raise TurboRegistryError("dispatcher_profile is required")
    return {
        "schema_version": 1,
        "dispatcher_profile": dispatcher,
        "canonical_skill_root": _relative_path(payload.get("canonical_skill_root"), "canonical_skill_root"),
        "profile_root": _relative_path(payload.get("profile_root"), "profile_root"),
        "aliases": aliases,
        "specialized_profiles": specialized,
    }
