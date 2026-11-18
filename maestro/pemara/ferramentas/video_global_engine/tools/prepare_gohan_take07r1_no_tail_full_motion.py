from __future__ import annotations

import json
import sys
from copy import deepcopy
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
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    by_id = {str(item.get("id") or ""): item for item in takes if isinstance(item, dict)}
    if "07R1" in by_id:
        print(json.dumps({"ok": True, "existing": "07R1"}, indent=2))
        return
    source = by_id["07"]
    if str(source.get("maestro_status") or "").upper() != "REJECTED":
        raise ValueError("Take 07 precisa permanecer REJECTED antes do 07R1.")
    source_view = _take_view(source, PROJECT)
    if not source_view.get("keyframeApproved") or not source_view.get("hasEndKeyframe"):
        raise ValueError("As duas ancoras aprovadas do 07 nao estao disponiveis.")

    now = utc_now()
    replacement = deepcopy(source)
    replacement.update({
        "id": "07R1",
        "sequence": 7.1,
        "slug": "gohan_cell_trocacao_pressao_no_tail_r1",
        "name": "gohan_cell_trocacao_pressao_no_tail_r1",
        "title": "Gohan pressiona Perfect Cell sem cauda - R1",
        "objective": "Refazer a trocacao preservando Perfect Cell completamente sem cauda e movimento util ate o corte.",
        "status": "PLANNED",
        "maestro_status": "PLANNED",
        "render_authorized": True,
        "render_block_reason": "",
        "maestro_updated_at": now,
        "maestro_last_job_id": "",
        "maestro_last_error": "",
        "maestro_last_result": None,
        "maestro_director_requests": [],
        "maestro_notes": "Substituto automatico do 07 reprovado por cauda em Perfect Cell e final quase estatico.",
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {
            "status": "pending_generation",
            "human_visual_approval": "pending",
            "transition_motion_gate": {"status": "contract_ready_pending_artifact_qc"},
            "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK",
        },
        "animation_prompt": (
            "ONE UNBROKEN 10.083333-SECOND PHOTOREALISTIC LIVE-ACTION CLOSE-COMBAT TAKE between the exact approved "
            "first and last frames. Preserve exactly one teenage Gohan SSJ2 and exactly one full-size adult green-and-"
            "black Perfect Cell as the same continuous bodies. CRITICAL SILHOUETTE LOCK IN EVERY FRAME: PERFECT CELL "
            "HAS NO TAIL. CELL IS COMPLETELY TAILLESS FROM FIRST FRAME TO LAST FRAME. The rear silhouette ends cleanly "
            "at the pelvis. No tail, stinger, tentacle, cable, curved rear limb, rear blade, rear tube or ambiguous "
            "appendage may emerge, even during turns or motion blur. Only two short rigid symmetrical upper-back wing "
            "plates are allowed; they never bend, lengthen or curl. At 0-30%, inherit the wall-breach velocity: tailless "
            "Cell commits one right counter while Gohan closes real distance, parries and both descend through debris. "
            "At 30-70%, tailless Cell adds one knee; Gohan blocks, answers with one body punch and one separate short "
            "straight, each with readable anticipation, contact and consequence. At 70-100%, Gohan drives one compact "
            "blow into Cell's guard; Cell skids backward continuously while Gohan advances. Camera performs a physical "
            "descending orbit, crosses behind one foreground slab, changes height and finishes on a new axis with real "
            "parallax. Delay the approved final composition until the last 0.10 seconds. Cut while bodies, camera, hair, "
            "cloth, armor, lightning, dust and rubble still carry visible directional velocity. FORBIDDEN: any tail or "
            "rear appendage in any frame; static tail; early final pose; held ending; reset; repeated loop; teleportation; "
            "extra fighter; duplicate body; extra limb; body substitution; Cell Junior; energy beam; Kamehameha; anime "
            "drawing; cel shading; illustration; game render; plastic CGI skin; text; logo; watermark; blood or gore."
        ),
    })
    replacement["owner_approvals"] = [{
        "scope": "automatic_corrected_candidate_after_internal_qc_failure",
        "source": "explicit_owner_scope_two_additional_takes_and_project_no_tail_contract",
        "rejected_take": "07",
        "authorized_at": now,
    }]
    source["render_authorized"] = False
    source["render_block_reason"] = "Reprovado por cauda em Perfect Cell e final quase estatico; substituido por 07R1."
    insert_at = next(index for index, item in enumerate(takes) if item is source) + 1
    takes.insert(insert_at, replacement)
    queue.update({
        "status": "READY_FOR_TAKE07R1_SERIAL_GENERATION",
        "render_authorized": True,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "gohan_take07r1_then_take08_v1",
            "batch_size": 1,
            "render_order": ["07R1", "08"],
            "strict_contiguous": True,
            "require_all_base_images_ready": True,
            "fill_eligible_across_batches": False,
            "require_full_batch": True,
            "allow_incomplete_correction_batch": False,
            "control_surface": "automatic_internal_qc_correction_then_owner_requested_take08",
            "configured_at": now,
        },
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "READY_FOR_TAKE07R1_SERIAL_GENERATION",
        "render_authorized": True,
        "updated_at": now,
        "take07_internal_qc_replacement": {
            "rejected_take": "07",
            "replacement_take": "07R1",
            "reason": "Perfect Cell gained a large tail and the final 0.54 seconds were near-static.",
            "original_preserved": True,
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = True
    _atomic_json_write(production_path, production)
    print(json.dumps({
        "ok": True,
        "rejectedPreserved": "07",
        "replacement": "07R1",
        "anchorsApproved": True,
        "renderAuthorized": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
