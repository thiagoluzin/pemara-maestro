"""Non-invasive model/readiness inventory shared by Studio engine adapters."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


OFFLOADED_COMFY_ROOT = Path("D:/PemaraModels/offloaded/ComfyUI")


def load_model_lock(workspace_root: Path) -> dict[str, Any]:
    path = Path(workspace_root) / "tools" / "model_installers" / "models.lock.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"schema_version": 0, "artifacts": []}
    return payload if isinstance(payload, dict) else {"schema_version": 0, "artifacts": []}


def load_resolved_integrity(workspace_root: Path) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    target_root = root.parents[1] if len(root.parents) > 1 else root
    path = target_root / "logs" / "model_installers" / "resolved_integrity.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    return artifacts if isinstance(artifacts, dict) else {}


def comfy_model_roots(workspace_root: Path) -> tuple[Path, ...]:
    primary = Path(workspace_root) / "ferramentas" / "ComfyUI" / "models"
    roots = [primary]
    if OFFLOADED_COMFY_ROOT.exists():
        roots.append(OFFLOADED_COMFY_ROOT)
    return tuple(roots)


def resolve_artifact_path(workspace_root: Path, artifact: dict[str, Any]) -> Path:
    explicit = artifact.get("installed_path")
    if explicit:
        return Path(str(explicit))
    destination = str(artifact.get("destination_filename") or artifact.get("filename") or "").replace("\\", "/")
    if destination.startswith("split_files/"):
        destination = destination[len("split_files/") :]
    root_kind = str(artifact.get("destination_root") or "comfy_models")
    if root_kind == "comfy_custom_nodes":
        return Path(workspace_root) / "ferramentas" / "ComfyUI" / "custom_nodes" / destination
    if root_kind == "video_workflows":
        return Path(workspace_root) / "ferramentas" / "video_global_engine" / "workflows" / destination
    candidates = [root / destination for root in comfy_model_roots(workspace_root)]
    return next((path for path in candidates if path.is_file()), candidates[0])


def artifact_status(workspace_root: Path, artifact: dict[str, Any], *, verify_hash: bool = False) -> dict[str, Any]:
    path = resolve_artifact_path(workspace_root, artifact)
    exists = path.is_file() or (artifact.get("kind") == "git_checkout" and path.is_dir())
    expected_bytes = int(artifact.get("expected_bytes") or 0)
    actual_bytes = path.stat().st_size if path.is_file() else 0
    size_ok = bool(exists and (expected_bytes <= 0 or actual_bytes == expected_bytes))
    expected_hash = str(artifact.get("sha256") or "").lower()
    if not expected_hash and artifact.get("integrity_source") == "hf_lfs_oid":
        resolved = load_resolved_integrity(workspace_root).get(str(artifact.get("id") or ""), {})
        if (
            resolved.get("repo_id") == artifact.get("repo_id")
            and resolved.get("revision") == artifact.get("revision")
            and resolved.get("filename") == artifact.get("filename")
            and int(resolved.get("expected_bytes") or 0) == expected_bytes
        ):
            expected_hash = str(resolved.get("sha256") or "").lower()
    hash_ok: bool | None = None
    if verify_hash and path.is_file() and size_ok and expected_hash:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(block)
        hash_ok = digest.hexdigest().lower() == expected_hash
    return {
        "id": str(artifact.get("id") or path.name),
        "classification": str(artifact.get("classification") or "MODEL_ASSET"),
        "required": artifact.get("required", True) is not False,
        "path": str(path),
        "exists": exists,
        "expected_bytes": expected_bytes,
        "actual_bytes": actual_bytes,
        "size_ok": size_ok,
        "hash_checked": bool(verify_hash and expected_hash),
        "integrity_resolved": bool(expected_hash),
        "hash_ok": hash_ok,
        "ok": bool(size_ok and hash_ok is not False),
    }


def component_status(workspace_root: Path, component: str, *, verify_hash: bool = False) -> list[dict[str, Any]]:
    lock = load_model_lock(workspace_root)
    return [
        artifact_status(workspace_root, item, verify_hash=verify_hash)
        for item in lock.get("artifacts", [])
        if isinstance(item, dict) and item.get("component") == component
    ]
