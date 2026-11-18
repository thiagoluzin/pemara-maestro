"""Build idempotent CPU-only review proxies for selected Maestro projects."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from review_proxies import (
    REVIEW_PROXY_PROFILE,
    build_review_proxy,
    review_proxy_paths,
    resolve_review_proxy,
)
from video_projects import _queue, _take_output_path, _take_status


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECTS_ROOT = (
    REPO_ROOT / "ferramentas" / "video_global_engine" / "projetos"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
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


def _project_path(projects_root: Path, project_id: str) -> Path:
    projects_root = projects_root.resolve()
    project = (projects_root / str(project_id or "").strip()).resolve()
    if project.parent != projects_root or not project.is_dir():
        raise ValueError(f"Projeto invalido ou ausente: {project_id}")
    return project


def _discover(
    projects_root: Path,
    project_ids: list[str],
    statuses: set[str],
) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for project_id in project_ids:
        project = _project_path(projects_root, project_id)
        queue = _queue(project)
        for take in queue.get("takes", []):
            if not isinstance(take, dict):
                continue
            status = _take_status(take)
            if status not in statuses:
                continue
            take_id = str(take.get("id") or take.get("take_id") or "")
            source = _take_output_path(project, take)
            if source is None:
                raise FileNotFoundError(
                    f"{project_id}/{take_id}: aprovado sem master local valido"
                )
            proxy, sidecar, identity = review_proxy_paths(
                project,
                take_id,
                source,
            )
            existing = resolve_review_proxy(project, take_id, source)
            discovered.append(
                {
                    "projectId": project_id,
                    "project": project,
                    "takeId": take_id,
                    "status": status,
                    "source": source,
                    "sourceBytes": source.stat().st_size,
                    "proxy": proxy,
                    "sidecar": sidecar,
                    "version": identity["version"],
                    "ready": existing is not None,
                }
            )
    return discovered


def _public_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: str(value) if isinstance(value, Path) else value
        for key, value in item.items()
        if key not in {"project"}
    }


def _write_project_manifests(
    projects_root: Path,
    project_ids: list[str],
    results: list[dict[str, Any]],
    started_at: str,
    elapsed_seconds: float,
) -> None:
    for project_id in project_ids:
        project_results = [
            result for result in results if result["projectId"] == project_id
        ]
        source_bytes = sum(int(result.get("sourceBytes") or 0) for result in project_results)
        proxy_bytes = sum(int(result.get("proxyBytes") or 0) for result in project_results)
        manifest = {
            "schema_version": "1.0",
            "profile": REVIEW_PROXY_PROFILE,
            "project_id": project_id,
            "started_at": started_at,
            "completed_at": _utc_now(),
            "elapsed_seconds": round(elapsed_seconds, 3),
            "master_policy": "preserved_untouched",
            "approval_state_changed": False,
            "gpu_used": False,
            "take_count": len(project_results),
            "source_bytes": source_bytes,
            "proxy_bytes": proxy_bytes,
            "reduction_percent": (
                round((1 - proxy_bytes / source_bytes) * 100, 2)
                if source_bytes
                else 0
            ),
            "results": project_results,
        }
        manifest_path = (
            _project_path(projects_root, project_id)
            / "qc"
            / "review_proxies"
            / "manifest.json"
        )
        _atomic_json_write(manifest_path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gera proxies H.264 720p para revisao sem alterar masters, "
            "fila ou aprovacoes."
        )
    )
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=DEFAULT_PROJECTS_ROOT,
    )
    parser.add_argument(
        "--project",
        action="append",
        dest="projects",
        required=True,
        help="projectId; repita para mais de um projeto",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        default=None,
        help="status de take elegivel; padrao APPROVED",
    )
    parser.add_argument("--expect-count", type=int)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()

    projects_root = args.projects_root.resolve()
    statuses = {
        str(status).strip().upper()
        for status in (args.statuses or ["APPROVED"])
        if str(status).strip()
    }
    discovered = _discover(projects_root, args.projects, statuses)
    if args.expect_count is not None and len(discovered) != args.expect_count:
        raise SystemExit(
            f"Escopo divergente: encontrados {len(discovered)} takes; "
            f"esperados {args.expect_count}."
        )

    if not args.execute:
        payload = {
            "mode": "dry-run",
            "profile": REVIEW_PROXY_PROFILE,
            "projects": args.projects,
            "statuses": sorted(statuses),
            "count": len(discovered),
            "ready": sum(1 for item in discovered if item["ready"]),
            "pending": sum(1 for item in discovered if not item["ready"]),
            "sourceBytes": sum(item["sourceBytes"] for item in discovered),
            "items": [_public_row(item) for item in discovered],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    started = time.perf_counter()
    started_at = _utc_now()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for index, item in enumerate(discovered, start=1):
        label = f"{item['projectId']}/{item['takeId']}"
        print(f"[{index}/{len(discovered)}] {label}", flush=True)
        try:
            result = build_review_proxy(
                item["project"],
                item["takeId"],
                item["source"],
                ffmpeg=args.ffmpeg,
                ffprobe=args.ffprobe,
                force=args.force,
            )
            results.append({"projectId": item["projectId"], **result})
        except Exception as exc:
            failures.append({"item": label, "error": str(exc)})
            print(f"ERRO {label}: {exc}", flush=True)

    elapsed = time.perf_counter() - started
    if failures:
        print(
            json.dumps(
                {
                    "mode": "execute",
                    "profile": REVIEW_PROXY_PROFILE,
                    "completed": len(results),
                    "failed": failures,
                    "elapsedSeconds": round(elapsed, 3),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    _write_project_manifests(
        projects_root,
        args.projects,
        results,
        started_at,
        elapsed,
    )
    summary = {
        "mode": "execute",
        "profile": REVIEW_PROXY_PROFILE,
        "completed": len(results),
        "generated": sum(1 for result in results if not result["skipped"]),
        "skipped": sum(1 for result in results if result["skipped"]),
        "sourceBytes": sum(result["sourceBytes"] for result in results),
        "proxyBytes": sum(result["proxyBytes"] for result in results),
        "durationSeconds": sum(result["durationSeconds"] for result in results),
        "elapsedSeconds": round(elapsed, 3),
        "mastersPreserved": True,
        "approvalStateChanged": False,
        "gpuUsed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
