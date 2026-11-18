"""Indice central de videos aprovados do Video Global Engine.

Os arquivos canonicos continuam dentro de cada projeto. A pasta PRONTOS recebe
hard links (sem duplicar espaco em disco) e nunca mistura candidatos pendentes
ou takes rejeitados.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any


READY_DIR_NAME = "PRONTOS"
MANIFEST_NAME = ".ready_exports.json"
STATUS_NAME = "STATUS.md"
INDEX_NAME = "LEIA_ME_PRIMEIRO.md"
APPROVED_TAKE_STATUSES = {"APPROVED", "FINAL"}
APPROVED_MASTER_STATUSES = {
    "approved",
    "final",
    "passed",
    "ready",
    "technical_and_visual_pass",
}


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON invalido: {path}")
    return data


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def _safe_project_file(project_dir: Path, raw: Any, suffix: str) -> Path | None:
    value = str(raw or "").strip()
    if not value:
        return None
    candidate = Path(value).resolve()
    project_dir = project_dir.resolve()
    if (
        not candidate.is_relative_to(project_dir)
        or not candidate.is_file()
        or candidate.suffix.lower() != suffix
    ):
        return None
    return candidate


def _active_queue_path(project_dir: Path) -> Path:
    manifest_path = project_dir / "project_manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    configured = str(manifest.get("take_queue") or "take_queue.json").strip()
    candidate = Path(configured)
    if candidate.name != configured or candidate.suffix.lower() != ".json":
        raise ValueError(f"take_queue deve ser um JSON na raiz do projeto: {configured}")
    resolved = (project_dir / candidate).resolve()
    if resolved.parent != project_dir.resolve():
        raise ValueError(f"take_queue fora da raiz do projeto: {configured}")
    return resolved


def _project_export_name(project_id: str) -> str:
    transition = re.match(r"^transicao_f(\d+)_f(\d+)_", project_id)
    if transition:
        return (
            f"TRANSICAO_F{transition.group(1)}-F{transition.group(2)}"
            f"__{project_id}"
        )
    if "cutscene_final" in project_id:
        return f"FINAL__{project_id}"
    if project_id.startswith("intro_"):
        return f"INTRO__{project_id}"
    return project_id.upper()


def _ensure_hardlink(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            if os.path.samefile(source, destination):
                return "hardlink"
        except OSError:
            pass
        destination.unlink()
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        # Mantem o recurso funcional caso o volume/antivirus nao permita link.
        shutil.copy2(source, destination)
        return "copy"


def _take_video_source(project_dir: Path, take: dict[str, Any]) -> Path | None:
    if str(take.get("maestro_status") or "").upper() not in APPROVED_TAKE_STATUSES:
        return None
    video = take.get("video")
    if not isinstance(video, dict):
        return None
    for field in (
        "output_final",
        "output_master",
        "output_active",
        "output_upscaled",
        "output_upscale_candidate",
        "output_review_candidate",
        "output_intermediate",
        "output_preview",
    ):
        candidate = _safe_project_file(project_dir, video.get(field), ".mp4")
        if candidate is not None:
            return candidate
    return None


def _take_metadata_source(project_dir: Path, take: dict[str, Any]) -> Path | None:
    video = take.get("video")
    if not isinstance(video, dict):
        return None
    for field in (
        "treatment_result",
        "upscale_metadata",
        "upscale_candidate_metadata",
        "metadata",
    ):
        candidate = _safe_project_file(project_dir, video.get(field), ".json")
        if candidate is not None:
            return candidate
    return None


def _approved_masters(project_dir: Path) -> list[Path]:
    output_dir = project_dir / "output"
    if not output_dir.is_dir():
        return []
    approved: list[Path] = []
    for video_path in sorted(output_dir.rglob("*.mp4")):
        sidecar = video_path.with_suffix(".json")
        if not sidecar.is_file():
            continue
        try:
            status = str(_read_json(sidecar).get("validation_status") or "").lower()
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if status in APPROVED_MASTER_STATUSES:
            approved.append(video_path.resolve())
    return approved


def rebuild_ready_index(ready_root: Path) -> dict[str, Any]:
    ready_root = ready_root.resolve()
    ready_root.mkdir(parents=True, exist_ok=True)
    projects: list[dict[str, Any]] = []
    for manifest_path in sorted(ready_root.glob(f"*/{MANIFEST_NAME}")):
        try:
            payload = _read_json(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        folder = manifest_path.parent
        ready_takes = [
            row
            for row in payload.get("readyTakes", [])
            if isinstance(row, dict)
            and (folder / str(row.get("central") or "")).is_file()
        ]
        ready_masters = [
            row
            for row in payload.get("readyMasters", [])
            if isinstance(row, dict)
            and (folder / str(row.get("central") or "")).is_file()
        ]
        if not ready_takes and not ready_masters:
            continue
        projects.append(
            {
                "projectId": str(payload.get("projectId") or folder.name),
                "folder": str(folder),
                "readyTakes": len(ready_takes),
                "readyMasters": len(ready_masters),
            }
        )

    lines = [
        "# VÍDEOS PRONTOS",
        "",
        "Esta é a pasta central para encontrar entregas prontas do Video Global Engine.",
        "Ela contém somente takes aprovados e masters com sidecar técnico aprovado.",
        "Previews, tentativas antigas, QC pendente e takes rejeitados ficam fora daqui.",
        "",
    ]
    for item in projects:
        folder = Path(str(item["folder"])).name
        lines.append(
            f"- `{folder}` — {item['readyTakes']} takes aprovados; "
            f"{item['readyMasters']} master(s)."
        )
    if not projects:
        lines.append("- Nenhum vídeo aprovado disponível no momento.")
    lines.extend(
        [
            "",
            "Os MP4 são hard links dos arquivos canônicos: aparecem como arquivos normais ",
            "sem ocupar outra cópia do espaço em disco.",
            "",
        ]
    )
    (ready_root / INDEX_NAME).write_text("\n".join(lines), encoding="utf-8")
    return {
        "readyRoot": str(ready_root),
        "projects": projects,
        "projectCount": len(projects),
        "readyTakeCount": sum(int(item["readyTakes"]) for item in projects),
        "readyMasterCount": sum(int(item["readyMasters"]) for item in projects),
    }


def _safe_managed_target(export_dir: Path, relative: str) -> Path:
    target = (export_dir / relative).resolve()
    export_dir = export_dir.resolve()
    if not target.is_relative_to(export_dir):
        raise ValueError(f"Caminho gerenciado fora de PRONTOS: {relative}")
    return target


def sync_project_ready_exports(
    project_dir: Path,
    *,
    queue_path: Path | None = None,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    queue_path = (queue_path or _active_queue_path(project_dir)).resolve()
    if not queue_path.is_relative_to(project_dir) or not queue_path.is_file() or queue_path.suffix.lower() != ".json":
        raise ValueError(f"take_queue invalida para exportacao: {queue_path}")
    if not queue_path.is_file():
        return {
            "projectId": project_dir.name,
            "readyTakes": 0,
            "readyMasters": 0,
            "skipped": True,
        }

    projects_root = project_dir.parent
    ready_root = projects_root.parent / READY_DIR_NAME
    export_dir = ready_root / _project_export_name(project_dir.name)
    queue = _read_json(queue_path)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError(f"take_queue sem takes: {queue_path}")

    desired: dict[str, Path] = {}
    take_rows: list[dict[str, str]] = []
    for take in takes:
        if not isinstance(take, dict):
            continue
        source = _take_video_source(project_dir, take)
        if source is None:
            continue
        take_id = str(take.get("id") or "").strip()
        if not take_id:
            continue
        relative_video = f"takes_aprovados/{take_id}.mp4"
        desired[relative_video] = source
        metadata = _take_metadata_source(project_dir, take)
        if metadata is not None:
            desired[f"takes_aprovados/{take_id}.json"] = metadata
        take_rows.append(
            {
                "takeId": take_id,
                "source": str(source),
                "central": relative_video,
            }
        )

    master_rows: list[dict[str, str]] = []
    for master in _approved_masters(project_dir):
        relative_video = f"masters/{master.name}"
        desired[relative_video] = master
        for suffix in (".json", ".srt", ".ass", ".jpg", ".png"):
            sidecar = master.with_suffix(suffix)
            if sidecar.is_file():
                desired[f"masters/{sidecar.name}"] = sidecar.resolve()
        master_rows.append(
            {
                "source": str(master),
                "central": relative_video,
            }
        )

    manifest_path = export_dir / MANIFEST_NAME
    previous_files: set[str] = set()
    if manifest_path.is_file():
        try:
            previous = _read_json(manifest_path)
            previous_files = {
                str(item)
                for item in previous.get("managedFiles", [])
                if isinstance(item, str)
            }
        except (OSError, ValueError, json.JSONDecodeError):
            previous_files = set()

    if not desired:
        for relative in sorted(previous_files):
            target = _safe_managed_target(export_dir, relative)
            if target.is_file():
                target.unlink()
        if manifest_path.is_file():
            manifest_path.unlink()
        status_path = export_dir / STATUS_NAME
        if status_path.is_file():
            status_path.unlink()
        for child_name in ("takes_aprovados", "masters"):
            child = export_dir / child_name
            if child.is_dir() and not any(child.iterdir()):
                child.rmdir()
        if export_dir.is_dir() and not any(export_dir.iterdir()):
            export_dir.rmdir()
        rebuild_ready_index(ready_root)
        return {
            "projectId": project_dir.name,
            "readyTakes": 0,
            "readyMasters": 0,
            "skipped": False,
        }

    export_dir.mkdir(parents=True, exist_ok=True)
    methods: dict[str, str] = {}
    for relative, source in sorted(desired.items()):
        destination = _safe_managed_target(export_dir, relative)
        methods[relative] = _ensure_hardlink(source, destination)

    for relative in sorted(previous_files - set(desired)):
        target = _safe_managed_target(export_dir, relative)
        if target.is_file():
            target.unlink()

    status_lines = [
        f"# {project_dir.name}",
        "",
        f"- Takes aprovados disponíveis aqui: {len(take_rows)}",
        f"- Masters técnicos/finais disponíveis aqui: {len(master_rows)}",
        "- Arquivos pendentes ou rejeitados não entram nesta pasta.",
        "- Os originais continuam preservados dentro do projeto.",
        "",
    ]
    (export_dir / STATUS_NAME).write_text(
        "\n".join(status_lines),
        encoding="utf-8",
    )
    _atomic_json_write(
        manifest_path,
        {
            "schemaVersion": 1,
            "projectId": project_dir.name,
            "projectDir": str(project_dir),
            "readyTakes": take_rows,
            "readyMasters": master_rows,
            "managedFiles": sorted(desired),
            "materialization": methods,
        },
    )
    rebuild_ready_index(ready_root)
    return {
        "projectId": project_dir.name,
        "folder": str(export_dir),
        "readyTakes": len(take_rows),
        "readyMasters": len(master_rows),
        "skipped": False,
    }


def sync_all_ready_exports(projects_root: Path) -> dict[str, Any]:
    projects_root = projects_root.resolve()
    if not projects_root.is_dir():
        raise FileNotFoundError(projects_root)
    ready_root = projects_root.parent / READY_DIR_NAME
    for project_dir in sorted(projects_root.iterdir()):
        if project_dir.is_dir() and (project_dir / "take_queue.json").is_file():
            sync_project_ready_exports(project_dir)
    return rebuild_ready_index(ready_root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza videos aprovados para a pasta central PRONTOS."
    )
    parser.add_argument("--projects-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            sync_all_ready_exports(args.projects_root),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
