from __future__ import annotations

import json
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT = ENGINE_ROOT / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"


def reset_request(request: dict, status: str) -> None:
    request["status"] = status
    request["updated_at"] = utc_now()
    for key in (
        "delivered_at", "candidate_file", "candidate_metadata_file",
        "candidate_sha256", "candidate_metadata_sha256", "review_decision",
        "review_reason", "reviewed_at",
    ):
        request.pop(key, None)


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    queue = _queue(PROJECT)
    by_id = {str(item.get("id") or ""): item for item in queue.get("takes", []) if isinstance(item, dict)}
    take07 = by_id["07"]
    take08 = by_id["08"]

    take07.pop("end_anchor_candidate", None)
    request07 = take07["maestro_director_requests"][-1]
    reset_request(request07, "PENDING")
    take07["qc"]["status"] = "anchor_request_pending_delivery"

    take08.pop("end_anchor_candidate", None)
    requests08 = take08["maestro_director_requests"]
    reset_request(requests08[0], "CANCELLED")
    reset_request(requests08[-1], "PENDING")
    take08["qc"]["status"] = "anchor_request_pending_delivery"

    now = utc_now()
    take07["maestro_updated_at"] = now
    take08["maestro_updated_at"] = now
    queue["updated_at"] = now
    _atomic_json_write(queue_path, queue)
    print(json.dumps({
        "ok": True,
        "take07EndRequest": request07["id"],
        "take08EndRequest": requests08[-1]["id"],
    }, indent=2))


if __name__ == "__main__":
    main()
