from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = ROOT / "projetos" / "intro_ritmos_revolta"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def image_size(path: Path) -> dict[str, int | str]:
    try:
        from PIL import Image

        with Image.open(path) as img:
            return {"width": img.width, "height": img.height, "mode": img.mode}
    except Exception as exc:
        return {"width": 0, "height": 0, "mode": f"unreadable: {exc}"}


def normalize_path(value: str) -> Path:
    return Path(value).expanduser()


def queued_images(queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for take in queue.get("takes", []):
        base = take.get("base_image") or {}
        file_value = (base.get("file") or "").strip()
        if not file_value:
            continue
        image_path = normalize_path(file_value)
        indexed[str(image_path.resolve()).lower()] = {"take": take, "base": base}
    return indexed


def metadata_from_take(image_path: Path, take_info: dict[str, Any] | None) -> dict[str, Any]:
    created_at = datetime.now().isoformat(timespec="seconds")
    size = image_size(image_path)
    if take_info:
        take = take_info["take"]
        base = take_info["base"]
        prompt = base.get("prompt") or take.get("image_prompt") or take.get("animation_prompt") or ""
        status = base.get("status") or "needs_human_qc"
        model = base.get("model") or "unknown"
        take_id = take.get("id", "")
        take_slug = take.get("slug", "")
        objective = take.get("objective", "")
        motion_layers = take.get("motion_layers", {})
    else:
        prompt = "Legacy base image without original prompt; not approved for video. Regenerate or attach the real prompt before use."
        status = "needs_human_qc"
        model = "unknown"
        take_id = ""
        take_slug = ""
        objective = ""
        motion_layers = {}

    return {
        "schema_version": "1.0",
        "project_id": "intro_ritmos_revolta",
        "type": "take_base_image_metadata",
        "created_at": created_at,
        "image_file": image_path.as_posix(),
        "take_id": take_id,
        "take_slug": take_slug,
        "model": model,
        "width": size.get("width", 0),
        "height": size.get("height", 0),
        "mode": size.get("mode", ""),
        "prompt": prompt,
        "objective": objective,
        "required_objects": motion_layers,
        "validation_status": status if status in {"approved", "approved_keyframe", "approved_for_video"} else "needs_human_qc",
        "approval_required_before_video": True,
        "qc_checklist": [
            "imagem aberta e inspecionada",
            "prompt e modelo registrados",
            "dimensoes conferidas",
            "sem texto/rosto/silhueta/artefato proibido",
            "marcar approved_for_video somente apos QC humano",
        ],
        "rejection_reasons": [],
        "generated_by": "tools/enforce_take_image_json.py",
    }


def validate_sidecar(sidecar: Path, image_path: Path, queued: bool) -> list[str]:
    errors: list[str] = []
    try:
        data = read_json(sidecar)
    except Exception as exc:
        return [f"invalid_json: {exc}"]

    for field in ["schema_version", "image_file", "prompt", "validation_status"]:
        if not data.get(field):
            errors.append(f"missing_{field}")

    image_file = data.get("image_file")
    if image_file:
        try:
            if Path(str(image_file)).resolve() != image_path.resolve():
                errors.append("image_file_mismatch")
        except Exception as exc:
            errors.append(f"image_file_unresolvable: {exc}")

    status = (data.get("validation_status") or "").lower()
    if queued and status not in {"approved", "approved_keyframe", "approved_for_video"}:
        errors.append(f"queued_image_not_approved: {status}")

    return errors


def repair_sidecar(sidecar: Path, image_path: Path, take_info: dict[str, Any] | None) -> bool:
    try:
        data = read_json(sidecar)
    except Exception:
        data = {}

    defaults = metadata_from_take(image_path, take_info)
    changed = False
    for field in ["schema_version", "project_id", "type", "image_file", "prompt", "validation_status"]:
        if not data.get(field):
            data[field] = defaults[field]
            changed = True

    if not data.get("approval_required_before_video"):
        data["approval_required_before_video"] = True
        changed = True
    if not data.get("qc_checklist"):
        data["qc_checklist"] = defaults["qc_checklist"]
        changed = True
    if "rejection_reasons" not in data:
        data["rejection_reasons"] = []
        changed = True

    if take_info is None and (data.get("validation_status") or "").lower() in {"approved", "approved_keyframe", "approved_for_video"}:
        data["validation_status"] = "needs_human_qc"
        changed = True

    if changed:
        data["repaired_at"] = datetime.now().isoformat(timespec="seconds")
        data["repaired_by"] = "tools/enforce_take_image_json.py"
        write_json(sidecar, data)
    return changed


def audit_project(project_dir: Path, write_missing: bool) -> dict[str, Any]:
    queue_path = project_dir / "take_queue.json"
    queue = read_json(queue_path)
    indexed = queued_images(queue)
    base_dir = project_dir / "base_images"
    images = sorted(
        [
            path
            for path in base_dir.rglob("*")
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ]
    )

    entries = []
    created = []
    repaired = []
    missing = []
    invalid = []

    for image_path in images:
        key = str(image_path.resolve()).lower()
        take_info = indexed.get(key)
        sidecar = image_path.with_suffix(".json")
        if not sidecar.exists():
            missing.append(sidecar.as_posix())
            if write_missing:
                write_json(sidecar, metadata_from_take(image_path, take_info))
                created.append(sidecar.as_posix())

        errors = validate_sidecar(sidecar, image_path, queued=take_info is not None) if sidecar.exists() else ["missing_sidecar"]
        if write_missing and sidecar.exists() and errors:
            if repair_sidecar(sidecar, image_path, take_info):
                repaired.append(sidecar.as_posix())
                errors = validate_sidecar(sidecar, image_path, queued=take_info is not None)
        if errors:
            invalid.append({"image": image_path.as_posix(), "sidecar": sidecar.as_posix(), "errors": errors})

        entries.append(
            {
                "image": image_path.as_posix(),
                "sidecar": sidecar.as_posix(),
                "queued": take_info is not None,
                "exists": sidecar.exists(),
                "errors": errors,
            }
        )

    return {
        "schema_version": "1.0",
        "type": "take_image_json_audit",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_dir": project_dir.as_posix(),
        "queue": queue_path.as_posix(),
        "images_total": len(images),
        "queued_images_total": len(indexed),
        "missing_sidecars_total": len(missing),
        "created_sidecars_total": len(created),
        "repaired_sidecars_total": len(repaired),
        "invalid_sidecars_total": len(invalid),
        "missing_sidecars": missing,
        "created_sidecars": created,
        "repaired_sidecars": repaired,
        "invalid_sidecars": invalid,
        "entries": entries,
        "rule": "Sem JSON = ativo invalido. Toda imagem que virar take precisa de sidecar aprovado.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita e impõe JSON lateral para imagens-base de takes.")
    parser.add_argument("--project", default=str(DEFAULT_PROJECT), help="Pasta do projeto com take_queue.json.")
    parser.add_argument("--write-missing", action="store_true", help="Cria JSON faltante como needs_human_qc.")
    args = parser.parse_args()

    project_dir = Path(args.project)
    report = audit_project(project_dir, write_missing=args.write_missing)

    out_dir = project_dir / "qc" / "json_sidecar_audits"
    out_path = out_dir / f"json_sidecar_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json(out_path, report)

    print(f"AUDIT_JSON={out_path}")
    print(f"IMAGES={report['images_total']}")
    print(f"MISSING={report['missing_sidecars_total']}")
    print(f"CREATED={report['created_sidecars_total']}")
    print(f"REPAIRED={report['repaired_sidecars_total']}")
    print(f"INVALID={report['invalid_sidecars_total']}")

    if report["invalid_sidecars_total"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
