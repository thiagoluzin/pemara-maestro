from __future__ import annotations

import json
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write, _queue, _take_view, utc_now  # noqa: E402


PROJECT = ENGINE_ROOT / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    project_manifest_path = PROJECT / "project_manifest.json"
    queue = _queue(PROJECT)
    by_id = {str(item.get("id") or ""): item for item in queue.get("takes", []) if isinstance(item, dict)}
    now = utc_now()
    approvals = {}
    for take_id in ("07", "08"):
        take = by_id[take_id]
        view = _take_view(take, PROJECT)
        if not view.get("keyframeApproved") or not view.get("hasEndKeyframe"):
            raise ValueError(f"Take {take_id} ainda nao possui as duas ancoras aprovadas.")
        candidate = view.get("endAnchorCandidate") or {}
        if str(candidate.get("status") or "").lower() != "approved_for_video":
            raise ValueError(f"Take {take_id} ancora final nao esta approved_for_video.")
        take["render_authorized"] = True
        take["render_block_reason"] = ""
        take["maestro_status"] = "PLANNED"
        take["maestro_updated_at"] = now
        take["maestro_notes"] = (
            "Ancoras aprovadas no Maestro pelo proprietario e confirmadas pela API ao vivo; "
            "geracao visual serial 07 depois 08 autorizada."
        )
        owner_approvals = take.setdefault("owner_approvals", [])
        owner_approvals.append({
            "scope": "generate_two_additional_visual_takes_07_08",
            "source": "maestro_anchor_review_plus_explicit_owner_message",
            "authorized_at": now,
        })
        approvals[take_id] = {
            "startApproved": bool(view.get("keyframeApproved")),
            "endApproved": bool(view.get("hasEndKeyframe")),
            "endCandidateStatus": candidate.get("status"),
        }

    queue.update({
        "status": "READY_FOR_TAKES07_08_SERIAL_GENERATION",
        "render_authorized": True,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "gohan_takes07_08_extension_v1",
            "batch_size": 1,
            "render_order": ["07", "08"],
            "strict_contiguous": True,
            "require_all_base_images_ready": True,
            "fill_eligible_across_batches": False,
            "require_full_batch": True,
            "allow_incomplete_correction_batch": False,
            "control_surface": "owner_requested_two_more_takes_anchors_approved_in_maestro",
            "configured_at": now,
        },
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "READY_FOR_TAKES07_08_SERIAL_GENERATION",
        "render_authorized": True,
        "updated_at": now,
    })
    extension = production.setdefault("extension_07_08", {})
    extension.update({
        "anchor_status": "approved_in_maestro",
        "render_authorized": True,
        "render_order": ["07", "08"],
        "serial_gpu_only": True,
        "approved_at": now,
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = True
    _atomic_json_write(production_path, production)

    manifest = json.loads(project_manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update({
        "updated_at": now,
        "maestro_status": "READY_FOR_TAKES07_08_SERIAL_GENERATION",
        "render_authorized": True,
    })
    _atomic_json_write(project_manifest_path, manifest)
    print(json.dumps({
        "ok": True,
        "approvals": approvals,
        "renderOrder": ["07", "08"],
        "serialGpuOnly": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
