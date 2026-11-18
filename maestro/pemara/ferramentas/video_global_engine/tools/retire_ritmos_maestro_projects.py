"""Retire completed Ritmos da Revolta video projects from Maestro safely.

The command first materializes approved/FINAL media in PRONTOS, removes only
rejected or disposable generation/QC artifacts, and moves the two Maestro root
registries into a local retirement archive.  The project directories and final
media remain in place.  Use --dry-run before --apply.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BASE = Path(r"E:\Pemara\maestro\pemara")
ENGINE_ROOT = BASE / "ferramentas" / "video_global_engine"
PROJECTS_ROOT = ENGINE_ROOT / "projetos"
STUDIO_ROOT = BASE / "services" / "studio"
PROJECT_IDS = (
    "cutscene_final_maestro_qwen",
    "intro_ritmos_revolta",
    "transicao_f1_f2_cold_iron_wan",
    "transicao_f2_f3_raizes_ferro_wan",
    "transicao_f3_f4_fabrica_ritmos_qwen",
    "transicao_f4_f5_cavernas_amaldicoadas_qwen",
    "transicao_f5_f6_torre_tenebra_qwen",
    "transicao_f6_f7_trono_tenebra_qwen",
)
APPROVED_STATUSES = {"APPROVED", "FINAL"}
APPROVED_SIDECAR_STATUSES = {
    "approved",
    "final",
    "passed",
    "ready",
    "technical_and_visual_pass",
}
VIDEO_AUDIO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".wav", ".flac", ".aac", ".m4a"}
QC_MEDIA_SUFFIXES = VIDEO_AUDIO_SUFFIXES | {".png", ".jpg", ".jpeg", ".webp"}
CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
TEMP_DIR_NAMES = {"tmp", "temp", "temporary"}
TEMP_SUFFIXES = {".tmp", ".part", ".crdownload"}
REJECTED_TOKENS = ("reject", "reprov", "discard", "failed", "falhou", "trash", "lixo", "superseded")
REJECTED_NAME_RE = re.compile(
    r"(?:^|[_\-.])(reject(?:ed|ion)?|reprov(?:ado|ada|ados|adas)?|discard(?:ed)?|failed|falhou|trash|lixo|superseded)(?:[_\-.]|$)",
    re.IGNORECASE,
)
KEEP_NAME_TOKENS = ("master", "final", "approved", "aprovado")
DISPOSABLE_OUTPUT_TOKENS = ("candidate", "review", "preview", "draft", "smoke", "retry", "test", "temp")
RETIRE_DIR = ".maestro_retired"
REPORT_NAME = "retirement_report.json"


def configure_logging(log_path: Path | None) -> logging.Logger:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.insert(0, logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("retire_ritmos")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON raiz invalido: {path}")
    return value


def active_queue_path(project_dir: Path, manifest: dict[str, Any]) -> Path:
    configured = str(manifest.get("take_queue") or "take_queue.json").strip()
    candidate = Path(configured)
    if candidate.name != configured or candidate.suffix.casefold() != ".json":
        raise ValueError(f"take_queue invalida em {project_dir.name}: {configured}")
    resolved = (project_dir / candidate).resolve()
    if resolved.parent != project_dir.resolve() or not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def assert_project_path(project_dir: Path) -> Path:
    projects_root = PROJECTS_ROOT.resolve()
    resolved = project_dir.resolve()
    if resolved.parent != projects_root or resolved.name not in PROJECT_IDS or not resolved.is_dir():
        raise RuntimeError(f"Projeto fora do escopo autorizado: {resolved}")
    return resolved


def safe_project_file(project_dir: Path, raw: Any) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    path = Path(text).resolve()
    if path.is_relative_to(project_dir.resolve()) and path.is_file():
        return path
    return None


def existing_paths(project_dir: Path, node: Any, *, skip_history: bool = True) -> set[Path]:
    found: set[Path] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).casefold()
            if skip_history and ("history" in lowered or "rejected" in lowered or "archived" in lowered):
                continue
            found.update(existing_paths(project_dir, value, skip_history=skip_history))
    elif isinstance(node, list):
        for value in node:
            found.update(existing_paths(project_dir, value, skip_history=skip_history))
    elif isinstance(node, str):
        path = safe_project_file(project_dir, node)
        if path is not None:
            found.add(path)
    return found


def direct_video_paths(project_dir: Path, video: dict[str, Any]) -> set[Path]:
    found: set[Path] = set()
    for key, value in video.items():
        if "history" in str(key).casefold():
            continue
        path = safe_project_file(project_dir, value)
        if path is not None:
            found.add(path)
    return found


def history_paths(project_dir: Path, node: Any) -> set[Path]:
    found: set[Path] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if "history" in str(key).casefold() or "rejected" in str(key).casefold() or "archived" in str(key).casefold():
                found.update(existing_paths(project_dir, value, skip_history=False))
            else:
                found.update(history_paths(project_dir, value))
    elif isinstance(node, list):
        for value in node:
            found.update(history_paths(project_dir, value))
    return found


def sidecar_status(path: Path) -> str:
    sidecar = path.with_suffix(".json")
    if not sidecar.is_file():
        return ""
    try:
        payload = read_json(sidecar)
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    for key in ("validation_status", "status", "qc_status", "maestro_status"):
        value = str(payload.get(key) or "").strip().casefold()
        if value:
            return value
    return ""


def approved_masters(project_dir: Path) -> set[Path]:
    output = project_dir / "output"
    protected: set[Path] = set()
    if not output.is_dir():
        return protected
    for path in output.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.casefold()
        status = sidecar_status(path) if path.suffix.casefold() in VIDEO_AUDIO_SUFFIXES else ""
        if any(token in lowered for token in KEEP_NAME_TOKENS) or status in APPROVED_SIDECAR_STATUSES:
            protected.add(path.resolve())
            for suffix in (".json", ".srt", ".ass", ".jpg", ".png"):
                sidecar = path.with_suffix(suffix)
                if sidecar.is_file():
                    protected.add(sidecar.resolve())
    return protected


def protected_files(project_dir: Path, queue: dict[str, Any]) -> set[Path]:
    protected = approved_masters(project_dir)
    for take in queue.get("takes", []):
        if not isinstance(take, dict):
            continue
        if str(take.get("maestro_status") or "").upper() not in APPROVED_STATUSES:
            continue
        protected.update(existing_paths(project_dir, take.get("base_image"), skip_history=True))
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        protected.update(direct_video_paths(project_dir, video))
    return protected


def rejected_files(project_dir: Path, queue: dict[str, Any]) -> set[Path]:
    rejected = history_paths(project_dir, queue)
    for take in queue.get("takes", []):
        if not isinstance(take, dict):
            continue
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        if str(take.get("maestro_status") or "").upper() == "REJECTED":
            rejected.update(direct_video_paths(project_dir, video))
        base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
        base_status = str(base.get("status") or "").casefold()
        if any(token in base_status for token in REJECTED_TOKENS):
            rejected.update(existing_paths(project_dir, base, skip_history=False))
    asset_roots = {"base_images", "takes", "microtakes", "qc", "review", "output", "direction"}
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_dir)
        top = relative.parts[0].casefold() if relative.parts else ""
        if (
            top in asset_roots
            and path.suffix.casefold() in QC_MEDIA_SUFFIXES | {".json", ".lock"}
            and REJECTED_NAME_RE.search(path.name)
        ):
            rejected.add(path.resolve())
    return rejected


def disposable_files(project_dir: Path, protected: set[Path], rejected: set[Path]) -> set[Path]:
    disposable = set(rejected)
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in protected:
            continue
        suffix = path.suffix.casefold()
        relative = path.relative_to(project_dir)
        top = relative.parts[0].casefold() if relative.parts else ""
        lowered = path.name.casefold()
        if suffix in TEMP_SUFFIXES or lowered.endswith("~"):
            disposable.add(resolved)
            continue
        if top in {"qc", "review"} and suffix in QC_MEDIA_SUFFIXES:
            disposable.add(resolved)
            continue
        if top in {"takes", "microtakes"} and suffix in VIDEO_AUDIO_SUFFIXES:
            if any(token in lowered for token in KEEP_NAME_TOKENS):
                continue
            disposable.add(resolved)
            continue
        if top == "output" and suffix in VIDEO_AUDIO_SUFFIXES:
            if any(token in lowered for token in DISPOSABLE_OUTPUT_TOKENS):
                disposable.add(resolved)

    expanded = set(disposable)
    for media in list(disposable):
        if media.suffix.casefold() not in QC_MEDIA_SUFFIXES:
            continue
        sidecar = media.with_suffix(".json")
        if sidecar.is_file() and sidecar.resolve() not in protected:
            if sidecar_status(media) not in APPROVED_SIDECAR_STATUSES:
                expanded.add(sidecar.resolve())
    return {path for path in expanded if path.is_file() and path not in protected}


def cache_directories(project_dir: Path) -> list[Path]:
    directories: list[Path] = []
    for path in project_dir.rglob("*"):
        if not path.is_dir():
            continue
        if path.name.casefold() in CACHE_DIR_NAMES | TEMP_DIR_NAMES:
            resolved = path.resolve()
            if resolved.is_relative_to(project_dir.resolve()):
                directories.append(resolved)
    directories.sort(key=lambda item: len(item.parts), reverse=True)
    return directories


def total_bytes(paths: Iterable[Path]) -> int:
    total = 0
    for path in paths:
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


def readiness(project_dir: Path, queue: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for take in queue.get("takes", []):
        if not isinstance(take, dict):
            continue
        status = str(take.get("maestro_status") or "PLANNED").upper()
        counts[status] = counts.get(status, 0) + 1
    return {
        "take_statuses": counts,
        "approved_or_final": sum(counts.get(item, 0) for item in APPROVED_STATUSES),
        "rejected": counts.get("REJECTED", 0),
        "planned": counts.get("PLANNED", 0),
    }


def build_plan() -> dict[str, Any]:
    if PROJECTS_ROOT.resolve() != Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos").resolve():
        raise RuntimeError("Raiz de projetos inesperada")
    projects: list[dict[str, Any]] = []
    for project_id in PROJECT_IDS:
        project_dir = assert_project_path(PROJECTS_ROOT / project_id)
        manifest_path = project_dir / "project_manifest.json"
        retired_root = project_dir / RETIRE_DIR
        default_queue_path = project_dir / "take_queue.json"
        if not default_queue_path.is_file() or not manifest_path.is_file():
            projects.append(
                {
                    "project_id": project_id,
                    "project_dir": str(project_dir),
                    "already_retired": retired_root.is_dir(),
                    "files": [],
                    "cache_directories": [],
                    "bytes": 0,
                }
            )
            continue
        manifest = read_json(manifest_path)
        queue_path = active_queue_path(project_dir, manifest)
        queue = read_json(queue_path)
        protected = protected_files(project_dir, queue)
        rejected = rejected_files(project_dir, queue)
        files = sorted(disposable_files(project_dir, protected, rejected), key=str)
        caches = cache_directories(project_dir)
        projects.append(
            {
                "project_id": project_id,
                "project_dir": str(project_dir),
                "already_retired": False,
                "active_queue": str(queue_path),
                "readiness": readiness(project_dir, queue),
                "protected_files": len(protected),
                "explicit_rejected_files": len([item for item in rejected if item.is_file()]),
                "files": [str(path) for path in files],
                "cache_directories": [str(path) for path in caches],
                "bytes": total_bytes(files) + sum(total_bytes(path.rglob("*")) for path in caches if path.is_dir()),
            }
        )
    return {
        "schema_version": 1,
        "projects_root": str(PROJECTS_ROOT.resolve()),
        "project_count": len(projects),
        "projects": projects,
        "file_count": sum(len(item["files"]) for item in projects),
        "cache_directory_count": sum(len(item["cache_directories"]) for item in projects),
        "bytes": sum(int(item["bytes"]) for item in projects),
        "generation_started": False,
    }


def sync_ready_exports(project_dirs: list[Path]) -> list[dict[str, Any]]:
    if str(STUDIO_ROOT) not in sys.path:
        sys.path.insert(0, str(STUDIO_ROOT))
    from ready_exports import sync_project_ready_exports

    return [sync_project_ready_exports(path) for path in project_dirs]


def remove_empty_directories(project_dir: Path) -> None:
    candidates = sorted(
        [path for path in project_dir.rglob("*") if path.is_dir()],
        key=lambda item: len(item.parts),
        reverse=True,
    )
    for path in candidates:
        if path.name == RETIRE_DIR or RETIRE_DIR in path.parts:
            continue
        try:
            path.rmdir()
        except OSError:
            continue


def retire_project(project_dir: Path, now: str) -> Path:
    project_dir = assert_project_path(project_dir)
    manifest = project_dir / "project_manifest.json"
    retired_root = project_dir / RETIRE_DIR
    retired_root.mkdir(parents=True, exist_ok=True)
    destination_manifest = retired_root / "project_manifest.json"
    for queue in sorted(project_dir.glob("take_queue*.json")):
        if not queue.is_file():
            continue
        destination_queue = retired_root / queue.name
        if destination_queue.exists():
            raise FileExistsError(destination_queue)
        os.replace(queue, destination_queue)
    if manifest.is_file():
        if destination_manifest.exists():
            raise FileExistsError(destination_manifest)
        payload = read_json(manifest)
        payload["maestro_status"] = "COMPLETED"
        payload["retired_from_maestro_at"] = now
        atomic_json(destination_manifest, payload)
        manifest.unlink()
    return retired_root


def apply_plan(plan: dict[str, Any], log: logging.Logger) -> dict[str, Any]:
    project_dirs = [assert_project_path(Path(item["project_dir"])) for item in plan["projects"] if not item["already_retired"]]
    ready = sync_ready_exports(project_dirs)
    now = datetime.now(timezone.utc).isoformat()
    deleted_files = 0
    deleted_bytes = 0
    retired: list[str] = []

    for item in plan["projects"]:
        project_dir = assert_project_path(Path(item["project_dir"]))
        if item["already_retired"]:
            log.info("ja retirado do Maestro: %s", item["project_id"])
            retired.append(item["project_id"])
            continue
        for raw in item["files"]:
            path = Path(raw).resolve()
            if not path.is_relative_to(project_dir) or not path.is_file():
                continue
            size = path.stat().st_size
            path.unlink()
            deleted_files += 1
            deleted_bytes += size
        for raw in item["cache_directories"]:
            path = Path(raw).resolve()
            if (
                path.is_dir()
                and path.is_relative_to(project_dir)
                and path.name.casefold() in CACHE_DIR_NAMES | TEMP_DIR_NAMES
            ):
                deleted_bytes += total_bytes(path.rglob("*"))
                shutil.rmtree(path)
        remove_empty_directories(project_dir)
        retired_root = retire_project(project_dir, now)
        retired.append(item["project_id"])
        log.info("retirado do Maestro: %s", item["project_id"])
        atomic_json(
            retired_root / REPORT_NAME,
            {
                "project_id": item["project_id"],
                "retired_at": now,
                "readiness_at_retirement": item.get("readiness", {}),
                "deleted_file_count": len(item["files"]),
                "planned_deleted_bytes": item["bytes"],
                "approved_exports_preserved_in": str((ENGINE_ROOT / "PRONTOS").resolve()),
                "generation_started": False,
            },
        )

    result = {
        "ok": True,
        "retired_projects": retired,
        "retired_count": len(retired),
        "deleted_files": deleted_files,
        "deleted_bytes": deleted_bytes,
        "ready_exports": ready,
        "generation_started": False,
    }
    log.info("concluido: projetos=%d arquivos=%d bytes=%d", len(retired), deleted_files, deleted_bytes)
    return result


def audit() -> dict[str, Any]:
    visible: list[str] = []
    retired: list[str] = []
    missing_archives: list[str] = []
    for project_id in PROJECT_IDS:
        project_dir = assert_project_path(PROJECTS_ROOT / project_id)
        if (project_dir / "project_manifest.json").exists() or (project_dir / "take_queue.json").exists():
            visible.append(project_id)
        archive = project_dir / RETIRE_DIR
        if (archive / "project_manifest.json").is_file() and any(archive.glob("take_queue*.json")):
            retired.append(project_id)
        else:
            missing_archives.append(project_id)
    return {
        "ok": not visible and not missing_archives and len(retired) == len(PROJECT_IDS),
        "visible_in_maestro": visible,
        "retired_projects": retired,
        "missing_archives": missing_archives,
        "generation_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--audit", action="store_true")
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    log = configure_logging(args.log if args.apply else None)
    if args.audit:
        result = audit()
    else:
        plan = build_plan()
        if args.dry_run:
            result = {"ok": True, "dry_run": True, **plan}
        else:
            result = apply_plan(plan, log)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
