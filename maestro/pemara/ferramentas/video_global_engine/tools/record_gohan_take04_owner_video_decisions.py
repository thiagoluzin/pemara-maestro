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
APPROVED = ("04C2", "04D1", "04D2R1")
REJECTED = "04D2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preview_path(take: dict) -> Path:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    value = str(video.get("output_preview") or video.get("output_active") or "")
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(take.get("id") or ""): take for take in takes if isinstance(take, dict)}
    now = utc_now()
    approved_records: dict[str, dict[str, str]] = {}

    for take_id in APPROVED:
        take = by_id.get(take_id)
        if not isinstance(take, dict) or str(take.get("maestro_status") or "").upper() != "APPROVED":
            raise ValueError(f"{take_id} nao esta aprovado no Maestro.")
        preview = preview_path(take)
        fingerprint = sha256(preview)
        take["render_authorized"] = False
        take["render_block_reason"] = "Candidato aprovado pelo proprietario; preservar o arquivo revisado e nao rerenderizar."
        qc = take.setdefault("qc", {})
        qc.update({
            "status": "approved_human_visual",
            "human_visual_approval": "approved",
            "owner_video_decision": {
                "decision": "APPROVED",
                "decided_at": now,
                "preview": preview.as_posix(),
                "preview_sha256": fingerprint,
                "source": "explicit_owner_message",
            },
        })
        take["maestro_updated_at"] = now
        approved_records[take_id] = {
            "preview": preview.as_posix(),
            "sha256": fingerprint,
        }

    rejected = by_id.get(REJECTED)
    if not isinstance(rejected, dict) or str(rejected.get("maestro_status") or "").upper() != "REJECTED":
        raise ValueError("04D2 nao esta reprovado no Maestro.")
    rejected_preview = preview_path(rejected)
    rejected["render_authorized"] = False
    rejected["render_block_reason"] = "Reprovado pelo proprietario; proibido montar ou regenerar sem nova autorizacao."
    rejected_qc = rejected.setdefault("qc", {})
    rejected_qc.update({
        "status": "user_rejected_director_pending",
        "human_visual_approval": "rejected",
        "owner_video_decision": {
            "decision": "REJECTED",
            "decided_at": now,
            "preview": rejected_preview.as_posix(),
            "preview_sha256": sha256(rejected_preview),
            "reason": "Perde o live action, fica parcialmente anime e depois cria rabo.",
            "source": "explicit_owner_message",
        },
    })
    rejected["maestro_updated_at"] = now

    queue.update({
        "status": "TAKE04_CORRECTIONS_OWNER_APPROVED",
        "render_authorized": False,
        "updated_at": now,
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "TAKE04_CORRECTIONS_OWNER_APPROVED",
        "render_authorized": False,
        "updated_at": now,
        "owner_video_decisions": {
            "approved": approved_records,
            "rejected": {
                "take": REJECTED,
                "preview": rejected_preview.as_posix(),
                "sha256": sha256(rejected_preview),
                "reason": "Perde o live action, fica parcialmente anime e depois cria rabo.",
            },
            "assembly_allowed": True,
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = False
    _atomic_json_write(production_path, production)

    print(json.dumps({
        "ok": True,
        "approved": approved_records,
        "rejected": REJECTED,
        "assemblyAllowed": True,
        "renderAuthorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
