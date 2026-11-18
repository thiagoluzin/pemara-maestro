import heapq
import mimetypes
import os
import urllib.parse
from pathlib import Path
from typing import Any, Iterable


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES | AUDIO_SUFFIXES


def _kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    return ""


def _recent_files(root: Path, *, max_scan_files: int, max_assets: int) -> list[tuple[float, Path]]:
    if not root.is_dir():
        return []
    heap: list[tuple[float, str, Path]] = []
    scanned = 0
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        for name in files:
            scanned += 1
            if scanned > max_scan_files:
                break
            path = Path(current) / name
            if path.suffix.lower() not in MEDIA_SUFFIXES:
                continue
            try:
                modified = path.stat().st_mtime
            except OSError:
                continue
            entry = (modified, str(path), path)
            if len(heap) < max_assets:
                heapq.heappush(heap, entry)
            elif entry > heap[0]:
                heapq.heapreplace(heap, entry)
        if scanned > max_scan_files:
            break
    return [(modified, path) for modified, _key, path in sorted(heap, reverse=True)]


def _asset(path: Path, root: Path, source: str, modified: float) -> dict[str, Any]:
    relative = path.relative_to(root)
    rel_posix = relative.as_posix()
    kind = _kind(path)
    if source == "comfy":
        subfolder = relative.parent.as_posix()
        if subfolder == ".":
            subfolder = ""
        query = urllib.parse.urlencode({
            "filename": path.name,
            "subfolder": subfolder,
            "type": "output",
        })
        url = f"/api/generative/comfy-view?{query}"
    else:
        query = urllib.parse.urlencode({"path": rel_posix})
        url = f"/api/generative/output?{query}"
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return {
        "source": source,
        "kind": kind,
        "filename": path.name,
        "relative_path": rel_posix,
        "url": url,
        "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "modified_at": modified,
        "size": size,
    }


def list_media_assets(
    comfy_root: Path,
    studio_root: Path,
    *,
    page: int = 1,
    page_size: int = 24,
    kind: str = "",
    max_scan_files: int = 50000,
    max_assets: int = 1000,
    extra_assets: Iterable[dict[str, Any]] | None = None,
    recent_comfy_files: Iterable[Path] | None = None,
) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    kind = (kind or "").strip().lower()
    if kind not in {"", "image", "video", "audio"}:
        raise ValueError("Tipo de arquivo invalido.")

    roots = ((Path(comfy_root), "comfy"), (Path(studio_root), "studio"))
    assets: list[dict[str, Any]] = []
    # Completed jobs are authoritative recent outputs. Include them even if
    # the bounded directory walk stops in a large frame-export directory.
    comfy_resolved = Path(comfy_root).resolve()
    seen: set[tuple[str, str]] = set()
    for candidate in recent_comfy_files or ():
        path = Path(candidate).resolve()
        if not path.is_relative_to(comfy_resolved) or not path.is_file() or not _kind(path):
            continue
        asset = _asset(path, comfy_resolved, "comfy", path.stat().st_mtime)
        identity = (asset["source"], asset["relative_path"])
        if identity not in seen and (not kind or asset["kind"] == kind):
            assets.append(asset)
            seen.add(identity)
    per_root_limit = max(20, max_assets)
    for root, source in roots:
        for modified, path in _recent_files(
            root,
            max_scan_files=max_scan_files,
            max_assets=per_root_limit,
        ):
            asset = _asset(path, root, source, modified)
            identity = (asset["source"], asset["relative_path"])
            if identity not in seen and (not kind or asset["kind"] == kind):
                assets.append(asset)
                seen.add(identity)
    for raw in extra_assets or ():
        if not isinstance(raw, dict):
            continue
        asset_kind = str(raw.get("kind") or "").strip().lower()
        url = str(raw.get("url") or "")
        if asset_kind not in {"image", "video", "audio"} or not url.startswith("/"):
            continue
        try:
            modified = float(raw.get("modified_at") or 0)
            size = max(0, int(raw.get("size") or 0))
        except (TypeError, ValueError):
            continue
        asset = {
            **raw,
            "source": str(raw.get("source") or "studio"),
            "kind": asset_kind,
            "filename": str(raw.get("filename") or "arquivo"),
            "relative_path": str(raw.get("relative_path") or ""),
            "url": url,
            "media_type": str(raw.get("media_type") or "application/octet-stream"),
            "modified_at": modified,
            "size": size,
        }
        if not kind or asset_kind == kind:
            assets.append(asset)
    assets.sort(key=lambda item: float(item["modified_at"]), reverse=True)
    assets = assets[:max_assets]
    total = len(assets)
    start = (page - 1) * page_size
    return {
        "ok": True,
        "items": assets[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "kind": kind,
        "capped": total >= max_assets,
    }
