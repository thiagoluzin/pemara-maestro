from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parents[1]
sys.path.insert(0, str(REPO / "services" / "studio"))

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT_ID = "gohan_ssj2_take06_magic_slap_multi_anchor_v1"
PROJECT = ENGINE / "projetos" / PROJECT_ID


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    queue = _queue(PROJECT)
    if any(str(item.get("id")) == "06B2R1" for item in queue.get("takes", [])):
        raise FileExistsError("06B2R1 ja existe.")
    source = next(item for item in queue["takes"] if str(item.get("id")) == "06B2")
    take = deepcopy(source)
    now = utc_now()
    take.update(
        {
            "id": "06B2R1",
            "slug": "gohan_retoma_pressao_lanca_cell_sem_cauda_r1",
            "name": "gohan_retoma_pressao_lanca_cell_sem_cauda_r1",
            "sequence": 3,
            "objective": "Retomar do tapa e lançar Cell com combo rápido, mantendo-o completamente sem cauda.",
            "animation_prompt": (
                "ONE UNBROKEN 5.125-SECOND PHOTOREALISTIC LIVE-ACTION DRAGON BALL COMBAT CONNECTOR between the exact "
                "approved slap-deflection first frame and approved flying-Cell last frame. Preserve exactly one teenage "
                "SSJ2 Gohan and exactly one adult Perfect Cell. CRITICAL EVERY-FRAME SILHOUETTE LOCK: PERFECT CELL IS "
                "COMPLETELY TAILLESS. His anatomy ends cleanly at the pelvis. No tail, stinger, tentacle, cable, rear tube, "
                "curved rear limb, third blade or ambiguous black appendage may appear, including during blur. Only two SHORT, "
                "RIGID, SYMMETRICAL UPPER-BACK WING PLATES are allowed; they never lengthen, curl or connect to the hips. "
                "Keep Cell front-facing or three-quarter front throughout so his clean pelvis remains readable. Opening 0-30%: "
                "the already-deflected golden projectile exits sideways and detonates in distant empty ruins while Gohan instantly "
                "closes distance; no reset and no new projectile. Middle 30-70%: Cell attempts one short counter; Gohan slips it, "
                "lands a separate elbow and knee with immediate heavy displacement. Final 70-100%: Gohan converts the same momentum "
                "into one rising body blow that launches the tailless Cell through debris toward the exact end anchor. First contact "
                "begins before 0.7 seconds and a new defense or impact occurs every 0.7-1.0 seconds. Camera performs a fast frontal "
                "lateral arc with height change, foreground rubble whip-occlusion and strong differential parallax. Heavy gold-white "
                "pressure bursts, blue-white lightning, armor compression, dust and stones move through the cut. FORBIDDEN: any tail "
                "or rear appendage, rear camera angle, slow circling, empty travel, soft hit, hold, freeze, crossfade, reset, duplicate, "
                "extra fighter, extra limb, anime drawing, cel shading, game render, plastic CGI skin, text, blood or gore."
            ),
            "render_authorized": True,
            "maestro_status": "PLANNED",
            "maestro_updated_at": now,
            "maestro_last_job_id": "",
            "maestro_last_error": "",
            "maestro_notes": "Substituto automático do 06B2 reprovado por cauda em Perfect Cell.",
            "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
            "qc": {"status": "anchors_approved_ready_for_serial_generation", "human_visual_approval": "anchors_approved_video_pending"},
            "maestro_director_requests": [],
        }
    )
    queue["takes"].append(take)
    queue.update(
        {
            "updated_at": now,
            "status": "READY_FOR_SERIAL_GENERATION",
            "render_authorized": True,
            "story_batch_policy": {
                "enabled": True,
                "version": "take06_b2r1_no_tail_serial_v1",
                "batch_size": 1,
                "render_order": ["06B2R1", "06A2", "06B2"],
                "strict_contiguous": True,
                "require_all_base_images_ready": True,
                "fill_eligible_across_batches": False,
                "require_full_batch": True,
                "allow_incomplete_correction_batch": False,
                "control_surface": "automatic_targeted_replacement_after_qc_rejection",
                "configured_at": now,
            },
        }
    )
    _atomic_json_write(queue_path, queue)
    print(json.dumps({"ok": True, "projectId": PROJECT_ID, "takeId": "06B2R1", "renderAuthorized": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
