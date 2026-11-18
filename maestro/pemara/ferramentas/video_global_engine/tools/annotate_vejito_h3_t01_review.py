from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projetos" / "vejito_super_boo_ltx25_60s"
TAKE_ID = "T01"
OUTPUT = "takes/maestro_generated/take_T01_1749c0e3299c4e5b_minimax_h3_preview.mp4"
CONTACT = "qc/T01_minimax_h3_seed_35081501/contact_sheet_9frames.jpg"
SHA256 = "D8DBADB6041E76FA98B34BAFB042230A25A3B6E52B42A06521B0EC92C4153A81"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(name: str) -> dict:
    return json.loads((PROJECT / name).read_text(encoding="utf-8"))


def save(name: str, value: dict) -> None:
    (PROJECT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    timestamp = now()
    queue = load("take_queue.json")
    production = load("production_manifest.json")
    project = load("project_manifest.json")
    queue_take = next(item for item in queue["takes"] if item.get("id") == TAKE_ID)
    prod_take = next(item for item in production["takes"] if item.get("id") == TAKE_ID)
    for item in production["takes"]:
        item["pilot"] = item.get("id") == TAKE_ID

    visual_qc = {
        "status": "AGENT_CONTACT_SHEET_PASS_PENDING_OWNER_PLAYBACK",
        "reviewed_at": timestamp,
        "contact_sheet": CONTACT,
        "identity_and_cast": (
            "Goku, Vegeta and Super Boo remain legible across the sampled frames; "
            "no coarse body replacement or duplicate fighter observed."
        ),
        "story_progression": (
            "Potara reveal advances into both fighters bringing earrings toward their ears "
            "while Boo's pink blast crosses the battlefield."
        ),
        "motion": "Material camera/action change is visible; full-speed owner playback remains mandatory.",
        "automatic_approval": False,
    }
    queue_take["status"] = "RENDERED_PENDING_HUMAN_VISUAL_QC"
    queue_take["qc_status"] = "video_pending_human_review"
    queue_take["maestro_status"] = "READY"
    queue_take["maestro_notes"] = (
        "NOVO CANDIDATO MINIMAX H3. O LTX-2.5 foi arquivado e nao deve ser aprovado. "
        "A amostragem H3 preserva Goku, Vegeta e Super Boo e mostra os brincos indo as orelhas; "
        "reproduza o take completo e aprove ou rejeite somente este H3."
    )
    queue_take.setdefault("qc", {})["status"] = "video_pending_human_review"
    queue_take["qc"]["human_visual_approval"] = "pending_owner_playback"
    queue_take["qc"]["agent_visual_qc"] = visual_qc
    queue_take.setdefault("video", {})["preview_model"] = "MiniMax H3 FL2VA INT8"
    queue_take["video"]["sha256"] = SHA256
    queue_take["video"]["width"] = 1280
    queue_take["video"]["height"] = 720
    queue_take["video"]["fps"] = 24
    queue_take["video"]["frames"] = 124
    queue_take["video"]["duration_seconds"] = 5.166667

    prod_take["generation"]["status"] = "RENDERED_PENDING_HUMAN_VISUAL_QC"
    prod_take["generation"]["output_preview"] = OUTPUT
    prod_take["generation"]["output_sha256"] = SHA256
    prod_take.setdefault("qc", {})["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    prod_take["qc"]["human_visual_approval"] = "pending_owner_playback"
    prod_take["qc"]["agent_visual_qc"] = visual_qc

    queue["status"] = "MINIMAX_H3_T01_PENDING_HUMAN_VISUAL_QC"
    queue["updated_at"] = timestamp
    production["updated_at"] = timestamp
    project["status"] = "WAITING_T01_MINIMAX_H3_HUMAN_VISUAL_QC"
    project["updated_at"] = timestamp
    project["take_review_candidates"] = [
        {
            "take_id": TAKE_ID,
            "engine": "MiniMax H3 FL2VA INT8",
            "status": "PENDING_HUMAN_VISUAL_QC",
            "output": OUTPUT,
            "sha256": SHA256,
            "contact_sheet": CONTACT,
            "registered_at": timestamp,
        }
    ]
    save("take_queue.json", queue)
    save("production_manifest.json", production)
    save("project_manifest.json", project)
    print(json.dumps(project["take_review_candidates"][0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
