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
ORDER = ["04C2", "04D1", "04D2"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_project_file(value: str) -> Path:
    path = Path(str(value or ""))
    if not path.is_absolute():
        path = PROJECT / path
    return path.resolve()


def approved_frame(take: dict, side: str) -> tuple[Path, str]:
    refs = take.get("shot_contract", {}).get("visual_references", {})
    if refs.get(f"{side}_frame_approved") is not True:
        raise ValueError(f"{take.get('id')} {side} frame nao aprovado.")
    path = resolve_project_file(str(refs.get(f"{side}_frame_file") or ""))
    if not path.is_file():
        raise FileNotFoundError(f"{take.get('id')} {side} frame ausente: {path}")
    actual = digest(path)
    declared = str(refs.get(f"{side}_frame_sha256") or "").lower()
    if declared and declared != actual:
        raise ValueError(f"{take.get('id')} {side} hash divergente.")
    return path, actual


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(take.get("id") or ""): take for take in takes if isinstance(take, dict)}

    for rejected_id in ("04C", "04D"):
        rejected = by_id.get(rejected_id)
        if not isinstance(rejected, dict) or str(rejected.get("maestro_status") or "").upper() != "REJECTED":
            raise ValueError(f"{rejected_id} precisa permanecer REJECTED.")
        rejected["render_authorized"] = False
        rejected["render_block_reason"] = "Original reprovado pelo proprietario; proibido regenerar ou montar."

    lineage: dict[str, dict[str, str]] = {}
    for take_id in ORDER:
        take = by_id.get(take_id)
        if not isinstance(take, dict):
            raise ValueError(f"Take corretivo ausente: {take_id}")
        start_path, start_hash = approved_frame(take, "start")
        end_path, end_hash = approved_frame(take, "end")
        lineage[take_id] = {
            "start": start_path.as_posix(),
            "start_sha256": start_hash,
            "end": end_path.as_posix(),
            "end_sha256": end_hash,
        }

    if lineage["04C2"]["end_sha256"] != lineage["04D1"]["start_sha256"]:
        raise ValueError("04C2 -> 04D1 nao compartilha a mesma ancora aprovada.")
    if lineage["04D1"]["end_sha256"] != lineage["04D2"]["start_sha256"]:
        raise ValueError("04D1 -> 04D2 nao compartilha a mesma ancora Dmid aprovada.")

    prompt_rules = {
        "04C2": ["TAILLESS", "adult Cell", "green armor"],
        "04D1": ["never turns green", "adult Cell", "morphing"],
        "04D2": ["No body grows", "adult Cell", "green armor"],
    }
    for take_id, needles in prompt_rules.items():
        prompt = str(by_id[take_id].get("animation_prompt") or "")
        missing = [needle for needle in needles if needle.casefold() not in prompt.casefold()]
        if missing:
            raise ValueError(f"{take_id} prompt sem trava obrigatoria: {missing}")

    c2 = by_id["04C2"]
    c2.pop("characters", None)
    c2["animation_prompt"] = (
        "ONE CONTINUOUS PHOTOREALISTIC LIVE-ACTION IMPACT CONNECTOR between the exact supplied frames. "
        "Begin with exactly one teenage Gohan SSJ2 and exactly two compact child-sized saturated cobalt-blue Cell "
        "Juniors inherited from the approved first frame. Cell Junior 1 completes its existing breakup into "
        "non-anatomical blue fragments and never becomes another body. Gohan redirects the same momentum into one "
        "knee impact on Cell Junior 2. End with exactly Gohan and that one remaining small blue Junior. Both Juniors "
        "are completely TAILLESS in every frame: no tail, stinger, tentacle, cable, rear extension or ambiguous "
        "appendage. The remaining Junior stays blue and child-sized. Camera continues one physical lateral orbit with "
        "slight crane rise and three-plane parallax. Useful body, debris, lightning and camera motion occupy 0-30%, "
        "30-70% and 70-100%. FORBIDDEN: adult Cell, Perfect Cell, green armor, body growth, species change, morphing, "
        "tail, stinger, rear appendage, duplicate body, extra fighter, extra limb, reset, repeated impact, crossfade, "
        "freeze, hold, anime, game render, text, blood or gore."
    )
    c2["cast_transition_contract"] = {
        "start": ["Gohan SSJ2", "Cell Junior blue 1", "Cell Junior blue 2"],
        "end": ["Gohan SSJ2", "Cell Junior blue 2"],
        "rule": (
            "Junior 1 exits only as abstract blue fragments; Junior 2 remains the same small cobalt-blue tailless "
            "body, species and scale."
        ),
    }

    now = utc_now()
    for take_id in ORDER:
        take = by_id[take_id]
        take["render_authorized"] = True
        take["render_block_reason"] = ""
        take["maestro_updated_at"] = now
        take.setdefault("owner_approvals", []).append({
            "scope": "single_corrective_render",
            "source": "explicit_user_approval_after_anchor_review",
            "approved_at": now,
            "anchor_lineage": lineage[take_id],
        })

    queue.update({
        "status": "READY_FOR_C2_D_CORRECTION_BATCH",
        "render_authorized": True,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "take04_c2_dmid_three_microtakes_v1",
            "batch_size": 3,
            "render_order": ORDER,
            "strict_contiguous": True,
            "require_all_base_images_ready": True,
            "fill_eligible_across_batches": False,
            "require_full_batch": True,
            "allow_incomplete_correction_batch": False,
            "control_surface": "maestro_production_button",
            "configured_at": now,
        },
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "READY_FOR_C2_D_CORRECTION_BATCH",
        "render_authorized": True,
        "updated_at": now,
        "active_correction_batch": {
            "takes": ORDER,
            "lineage": lineage,
            "forbidden": [
                "Cell verde/adulto no lugar do Junior",
                "rabo, ferrao ou apendice traseiro no Cell Junior",
                "morphing, crossfade, freeze ou hold",
            ],
            "owner_gate": "approved",
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = True
    _atomic_json_write(production_path, production)

    print(json.dumps({
        "ok": True,
        "projectId": PROJECT_ID,
        "renderOrder": ORDER,
        "lineage": lineage,
        "renderAuthorized": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
