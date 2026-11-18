from __future__ import annotations

import json
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

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


PROJECT_ID = "gohan_ssj2_take07_tailless_multi_anchor_v1"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
REVIEWED_IDS = ("07A", "07B")
ALL_IDS = (*REVIEWED_IDS, "07C")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    manifest_path = PROJECT / "project_manifest.json"
    if not queue_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(f"Projeto incompleto: {PROJECT}")

    queue = _queue(PROJECT)
    by_id = {str(take.get("id") or ""): take for take in queue.get("takes", []) if isinstance(take, dict)}
    if set(ALL_IDS) - set(by_id):
        raise ValueError("A cadeia 07A-07C nao esta completa.")

    validated = []
    for take_id in REVIEWED_IDS:
        image, _metadata, _record, _sidecar, _info, image_hash = _validated_registered_end_anchor(
            PROJECT,
            by_id[take_id],
            allowed_statuses={ANCHOR_APPROVED_STATUS},
        )
        validated.append({"takeId": take_id, "endAnchor": image.name, "sha256": image_hash})

    for take_id in ALL_IDS:
        take = by_id[take_id]
        base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
        if not _base_status_is_approved(base.get("status")):
            raise ValueError(f"{take_id}: ancora inicial nao aprovada.")
        if _take_keyframe_path(PROJECT, take) is None:
            raise FileNotFoundError(f"{take_id}: arquivo da ancora inicial ausente.")
        if _take_end_keyframe_path(PROJECT, take) is None:
            raise FileNotFoundError(f"{take_id}: ancora final aprovada ausente.")

    now = utc_now()
    queue.update(
        {
            "status": "READY_FOR_SERIAL_GENERATION",
            "render_authorized": True,
            "render_authority": "Owner approved intermediate anchors A-B in Maestro; confirmed by live Maestro API.",
            "owner_anchor_approval_confirmed_at": now,
            "updated_at": now,
            "story_batch_policy": {
                "enabled": True,
                "version": "take07_three_tailless_microtakes_v1",
                "batch_size": 1,
                "render_order": list(ALL_IDS),
                "strict_contiguous": True,
                "require_all_base_images_ready": True,
                "fill_eligible_across_batches": False,
                "require_full_batch": True,
                "allow_incomplete_correction_batch": False,
                "control_surface": "maestro_production_button_serial_qc",
                "configured_at": now,
            },
        }
    )
    for take_id in ALL_IDS:
        take = by_id[take_id]
        take["render_authorized"] = True
        take.pop("render_block_reason", None)
        take["maestro_status"] = "PLANNED"
        take["maestro_updated_at"] = now
        qc = take.setdefault("qc", {})
        qc["status"] = "anchors_approved_ready_for_serial_generation"
        qc["human_visual_approval"] = "anchors_approved_video_pending"

    manifest = read_json(manifest_path)
    manifest.update(
        {
            "status": "READY_FOR_SERIAL_GENERATION",
            "maestro_status": "IN_PROGRESS",
            "render_authorized": True,
            "owner_anchor_approval_confirmed_at": now,
            "updated_at": now,
        }
    )
    _atomic_json_write(queue_path, queue)
    _atomic_json_write(manifest_path, manifest)
    print(
        json.dumps(
            {
                "ok": True,
                "projectId": PROJECT_ID,
                "approvedChain": list(ALL_IDS),
                "validatedReviewedAnchors": validated,
                "renderAuthorized": True,
                "batchSize": 1,
                "activatedAt": now,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
