from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT_ID = "gohan_ssj2_take04_cells_jr_multi_anchor_v2"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
TAKE_ID = "04D2R1"


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    take = next(
        (item for item in queue.get("takes", []) if isinstance(item, dict) and str(item.get("id")) == TAKE_ID),
        None,
    )
    if not isinstance(take, dict) or str(take.get("maestro_status") or "").upper() != "READY":
        raise ValueError("04D2R1 ainda nao esta READY.")
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    preview = Path(str(video.get("output_preview") or video.get("output_active") or ""))
    if not preview.is_absolute():
        preview = PROJECT / preview
    if not preview.is_file():
        raise FileNotFoundError(preview)
    fingerprint = hashlib.sha256(preview.read_bytes()).hexdigest()
    now = utc_now()

    take["render_authorized"] = False
    take["render_block_reason"] = "Substituto gerado; aguardando revisao visual do proprietario no Maestro."
    take["maestro_updated_at"] = now
    qc = take.setdefault("qc", {})
    qc.update({
        "status": "video_pending_human_review",
        "human_visual_approval": "pending",
        "internal_visual_qc": {
            "status": "candidate_passes_rejected_defects_pending_owner",
            "checked_at": now,
            "live_action_preserved_in_sampled_frames": True,
            "no_tail_visible_in_sampled_frames": True,
            "no_green_or_adult_cell": True,
            "preview_sha256": fingerprint,
        },
        "transition_motion_gate": {
            "status": "pending_owner_full_motion_review",
            "useful_motion_end_seconds": 3.875,
            "freeze_intervals": [
                {"start": 3.875, "end": 4.25},
                {"start": 4.416667, "end": 5.166667},
            ],
            "maximum_editorial_use_seconds": 3.5,
            "editorial_rule": "hard cut by 3.5 s; crossfade, hold and frozen tail forbidden",
        },
    })
    queue.update({
        "status": "WAITING_04D2R1_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "WAITING_04D2R1_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
        "automatic_replacement_qc": {
            "take": TAKE_ID,
            "preview": preview.as_posix(),
            "sha256": fingerprint,
            "result": "requested defects absent in sampled frames; pending owner review",
            "maximum_editorial_use_seconds": 3.5,
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = False
    _atomic_json_write(production_path, production)
    print(json.dumps({
        "ok": True,
        "take": TAKE_ID,
        "preview": preview.as_posix(),
        "sha256": fingerprint,
        "renderAuthorized": False,
        "status": "pending_owner_review",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
