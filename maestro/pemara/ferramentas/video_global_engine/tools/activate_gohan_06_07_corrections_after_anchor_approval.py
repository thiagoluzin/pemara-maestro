from __future__ import annotations

import json
import sys
from pathlib import Path


ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parents[1]
sys.path.insert(0, str(REPO / "services" / "studio"))

from video_projects import (  # noqa: E402
    ANCHOR_APPROVED_STATUS,
    _atomic_json_write,
    _base_status_is_approved,
    _queue,
    _take_end_keyframe_path,
    _take_keyframe_path,
    _validated_registered_end_anchor,
    utc_now,
)


ROOT = ENGINE / "projetos"
PROJECTS = (
    {
        "id": "gohan_ssj2_take06_magic_slap_multi_anchor_v1",
        "reviewed": ("06A2",),
        "all": ("06A2", "06B2"),
        "version": "take06_magic_slap_two_microtakes_v1",
    },
    {
        "id": "gohan_ssj2_take07_frenetic_multi_anchor_v2",
        "reviewed": ("07C2",),
        "all": ("07A2", "07B2", "07C2", "07D2"),
        "version": "take07_frenetic_four_microtakes_v2",
    },
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def activate(spec: dict, now: str) -> dict:
    project = ROOT / spec["id"]
    queue_path = project / "take_queue.json"
    manifest_path = project / "project_manifest.json"
    queue = _queue(project)
    by_id = {str(take.get("id") or ""): take for take in queue.get("takes", []) if isinstance(take, dict)}
    if set(spec["all"]) - set(by_id):
        raise ValueError(f"Cadeia incompleta: {spec['id']}")
    validated = []
    for take_id in spec["reviewed"]:
        image, _metadata, _record, _sidecar, _info, image_hash = _validated_registered_end_anchor(
            project, by_id[take_id], allowed_statuses={ANCHOR_APPROVED_STATUS}
        )
        validated.append({"takeId": take_id, "endAnchor": image.name, "sha256": image_hash})
    for take_id in spec["all"]:
        take = by_id[take_id]
        base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
        if not _base_status_is_approved(base.get("status")):
            raise ValueError(f"{spec['id']}/{take_id}: ancora inicial nao aprovada.")
        if _take_keyframe_path(project, take) is None:
            raise FileNotFoundError(f"{spec['id']}/{take_id}: ancora inicial ausente.")
        if _take_end_keyframe_path(project, take) is None:
            raise FileNotFoundError(f"{spec['id']}/{take_id}: ancora final ausente.")
    queue.update(
        {
            "status": "READY_FOR_SERIAL_GENERATION",
            "render_authorized": True,
            "render_authority": "Owner approved new correction anchor in Maestro; confirmed by live API.",
            "owner_anchor_approval_confirmed_at": now,
            "updated_at": now,
            "story_batch_policy": {
                "enabled": True,
                "version": spec["version"],
                "batch_size": 1,
                "render_order": list(spec["all"]),
                "strict_contiguous": True,
                "require_all_base_images_ready": True,
                "fill_eligible_across_batches": False,
                "require_full_batch": True,
                "allow_incomplete_correction_batch": False,
                "control_surface": "maestro_serial_gpu_per_take_qc",
                "configured_at": now,
            },
        }
    )
    for take_id in spec["all"]:
        take = by_id[take_id]
        take["render_authorized"] = True
        take.pop("render_block_reason", None)
        take["maestro_status"] = "PLANNED"
        take["maestro_updated_at"] = now
        qc = take.setdefault("qc", {})
        qc["status"] = "anchors_approved_ready_for_serial_generation"
        qc["human_visual_approval"] = "anchors_approved_video_pending"
    manifest = read_json(manifest_path)
    manifest.update({"status": "READY_FOR_SERIAL_GENERATION", "maestro_status": "IN_PROGRESS", "render_authorized": True, "owner_anchor_approval_confirmed_at": now, "updated_at": now})
    _atomic_json_write(queue_path, queue)
    _atomic_json_write(manifest_path, manifest)
    return {"projectId": spec["id"], "approvedChain": list(spec["all"]), "validated": validated}


def main() -> None:
    now = utc_now()
    results = [activate(spec, now) for spec in PROJECTS]
    print(json.dumps({"ok": True, "activatedAt": now, "projects": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
