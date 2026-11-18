from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECTS = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos")
MAIN_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
HELPER_IDS = (
    "gohan_ssj2_take04_cells_jr_multi_anchor_v2",
    "gohan_ssj2_take06_magic_slap_multi_anchor_v1",
    "gohan_ssj2_take07_frenetic_multi_anchor_v2",
    "gohan_ssj2_take07_tailless_multi_anchor_v1",
)
PICTURE_LOCK = "deliveries/gohan_ssj2_cell_visual_cut_v1_720p24.mp4"
PICTURE_LOCK_SHA256 = "955190b4eed7b0272d23f4e325c4da8bfb5fec16d00148a964ef88953a1820ae"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON raiz invalido: {path}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exact_project(project_id: str) -> Path:
    candidate = (PROJECTS / project_id).resolve()
    if candidate.parent != PROJECTS.resolve() or candidate.name != project_id or not candidate.is_dir():
        raise RuntimeError(f"Projeto fora do escopo: {candidate}")
    return candidate


def tree_inventory(project: Path) -> dict[str, Any]:
    files = []
    total = 0
    for path in sorted((item for item in project.rglob("*") if item.is_file()), key=str):
        relative = path.relative_to(project).as_posix()
        size = path.stat().st_size
        total += size
        files.append({"path": relative, "bytes": size, "sha256": sha256(path)})
    return {"fileCount": len(files), "bytes": total, "files": files}


def build_plan() -> dict[str, Any]:
    if PROJECTS.resolve() != Path(
        r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    ).resolve():
        raise RuntimeError("Raiz de projetos inesperada")
    main = exact_project(MAIN_ID)
    queue = read_json(main / "take_queue.json")
    takes = {str(item.get("id")): item for item in queue.get("takes", []) if isinstance(item, dict)}
    required = {"01", "02", "03", "04", "05", "06", "06R1", "07", "07R1", "08"}
    missing = sorted(required - set(takes))
    if missing:
        raise RuntimeError(f"Fila principal incompleta: {missing}")
    if str(takes["06R1"].get("maestro_status") or "").upper() != "APPROVED":
        raise RuntimeError("Substituto 06R1 nao esta aprovado")
    if str(takes["07"].get("maestro_status") or "").upper() != "APPROVED":
        raise RuntimeError("Take 07 corrigido nao esta aprovado")
    picture = (main / PICTURE_LOCK).resolve()
    if not picture.is_file() or sha256(picture) != PICTURE_LOCK_SHA256:
        raise RuntimeError("Picture lock candidato ausente ou com hash divergente")
    helpers = []
    for project_id in HELPER_IDS:
        project = exact_project(project_id)
        helpers.append(
            {
                "projectId": project_id,
                "path": str(project),
                "projectManifest": str(project / "project_manifest.json"),
                "takeQueue": str(project / "take_queue.json"),
                "visible": (project / "project_manifest.json").is_file()
                or (project / "take_queue.json").is_file(),
            }
        )
    return {
        "schemaVersion": 1,
        "mainProject": MAIN_ID,
        "activeTakeIdsBefore": [str(item.get("id")) for item in queue.get("takes", []) if isinstance(item, dict)],
        "activeTakeIdsAfter": ["01", "02", "03", "04", "05", "06", "07", "08"],
        "archivedTakeIds": ["06", "07R1"],
        "replacementRename": {"06R1": "06"},
        "pictureLock": str(picture),
        "pictureLockSha256": PICTURE_LOCK_SHA256,
        "helperProjects": helpers,
        "deletesMedia": False,
        "generationStarted": False,
    }


def apply(plan: dict[str, Any]) -> dict[str, Any]:
    main = exact_project(MAIN_ID)
    now = datetime.now(timezone.utc).isoformat()
    archive = main / "archive" / "maestro_catalog_consolidation_v1"
    if archive.exists():
        raise FileExistsError(f"Consolidacao ja existe: {archive}")
    archive.mkdir(parents=True)

    shutil.copy2(main / "take_queue.json", archive / "take_queue.before.json")
    shutil.copy2(main / "project_manifest.json", archive / "project_manifest.before.json")

    queue_path = main / "take_queue.json"
    queue = read_json(queue_path)
    original_takes = [item for item in queue.get("takes", []) if isinstance(item, dict)]
    by_id = {str(item.get("id")): item for item in original_takes}
    archived = queue.setdefault("archived_take_history", [])
    if not isinstance(archived, list):
        archived = []
        queue["archived_take_history"] = archived
    for take_id, reason in (
        ("06", "rejected original superseded by owner-approved 06R1 magic-slap V2"),
        ("07R1", "rejected no-tail full-take attempt superseded by owner-approved 07 frenetic V3"),
    ):
        record = dict(by_id[take_id])
        record["archived_from_active_queue_at"] = now
        record["archive_reason"] = reason
        archived.append(record)

    replacement_06 = by_id["06R1"]
    replacement_06["id"] = "06"
    replacement_06["sequence"] = 6
    replacement_06["slug"] = "cell_lancado_pela_arena_magic_slap_corrected_v2"
    replacement_06["name"] = "cell_lancado_pela_arena_magic_slap_corrected_v2"
    replacement_06["title"] = "Gohan rebate a magia e lanca Cell pela arena"
    replacement_06["maestro_notes"] = (
        str(replacement_06.get("maestro_notes") or "")
        + " Consolidado no take 06 canonico; o 06 rejeitado permanece no historico."
    ).strip()
    canonical = [by_id[take_id] for take_id in ("01", "02", "03", "04", "05")]
    canonical.append(replacement_06)
    canonical.extend([by_id["07"], by_id["08"]])
    for sequence, take in enumerate(canonical, start=1):
        take["sequence"] = sequence
    queue["takes"] = canonical
    queue["catalog_consolidation"] = {
        "status": "ACTIVE_PROJECT_CONSOLIDATED",
        "consolidatedAt": now,
        "activeTakeIds": ["01", "02", "03", "04", "05", "06", "07", "08"],
        "archivedRejectedTakeIds": ["06", "07R1"],
        "helperProjectsRetiredFromCatalog": list(HELPER_IDS),
        "rollback": "archive/maestro_catalog_consolidation_v1/take_queue.before.json",
    }
    atomic_json(queue_path, queue)

    helper_reports = []
    for project_id in HELPER_IDS:
        helper = exact_project(project_id)
        inventory = tree_inventory(helper)
        snapshot = archive / project_id
        snapshot.mkdir(parents=True)
        for filename in ("project_manifest.json", "take_queue.json", "production_manifest.json"):
            source = helper / filename
            if source.is_file():
                shutil.copy2(source, snapshot / filename)
        atomic_json(snapshot / "tree_inventory.json", inventory)
        retired = helper / ".maestro_retired"
        retired.mkdir(parents=True, exist_ok=False)
        moved = []
        for filename in ("project_manifest.json", "take_queue.json"):
            source = helper / filename
            if source.is_file():
                destination = retired / filename
                os.replace(source, destination)
                moved.append(filename)
        report = {
            "projectId": project_id,
            "retiredFromMaestroAt": now,
            "reason": "auxiliary generation project consolidated into the canonical Gohan SSJ2 project",
            "movedCatalogRegistries": moved,
            "mediaDeleted": False,
            "treeInventoryInMainProject": str((snapshot / "tree_inventory.json").relative_to(main)),
            "restore": "move project_manifest.json and take_queue.json from .maestro_retired back to the project root",
        }
        atomic_json(retired / "retirement_report.json", report)
        helper_reports.append(report)

    manifest_path = main / "project_manifest.json"
    manifest = read_json(manifest_path)
    manifest["updated_at"] = now
    manifest["maestro_status"] = "PICTURE_LOCK_CANDIDATE_READY"
    manifest["catalog_consolidation"] = {
        "status": "CONSOLIDATED_SINGLE_MAESTRO_PROJECT",
        "consolidatedAt": now,
        "canonicalProjectId": MAIN_ID,
        "activeTakeIds": ["01", "02", "03", "04", "05", "06", "07", "08"],
        "retiredHelperProjectIds": list(HELPER_IDS),
        "archive": "archive/maestro_catalog_consolidation_v1",
        "mediaDeleted": False,
    }
    atomic_json(manifest_path, manifest)

    result = {
        "ok": True,
        "consolidatedAt": now,
        "mainProject": MAIN_ID,
        "activeTakeIds": ["01", "02", "03", "04", "05", "06", "07", "08"],
        "retiredHelperProjects": list(HELPER_IDS),
        "helperReports": helper_reports,
        "archive": str(archive),
        "pictureLock": plan["pictureLock"],
        "pictureLockSha256": plan["pictureLockSha256"],
        "mediaDeleted": False,
    }
    atomic_json(main / "qc" / "maestro_catalog_consolidation_v1.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = build_plan()
    print(json.dumps(apply(plan) if args.apply else plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
