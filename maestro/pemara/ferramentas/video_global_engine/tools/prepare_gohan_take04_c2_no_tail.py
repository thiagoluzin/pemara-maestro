from __future__ import annotations

import hashlib
import json
import sys
import uuid
from copy import deepcopy
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import (  # noqa: E402
    _atomic_json_write,
    _queue,
    register_end_anchor_candidate,
    utc_now,
)


PROJECT_ID = "gohan_ssj2_take04_cells_jr_multi_anchor_v2"
PROJECTS_ROOT = ENGINE_ROOT / "projetos"
PROJECT = PROJECTS_ROOT / PROJECT_ID
ANCHOR = PROJECT / "keyframes" / "anchor_C2_cell_junior_no_tail_v1_1664x936.png"
ANCHOR_ORIGINAL = PROJECT / "keyframes" / "anchor_C2_cell_junior_no_tail_v1.png"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reset_runtime(take: dict, now: str) -> None:
    take["maestro_status"] = "PLANNED"
    take["maestro_updated_at"] = now
    take["maestro_last_job_id"] = ""
    take["maestro_last_error"] = ""
    take["maestro_last_result"] = None
    take["video"] = {"status": "pending_generation", "output_preview": "", "output_active": ""}
    take["qc"] = {
        "status": "anchor_delivered_pending_user_approval",
        "human_visual_approval": "pending",
        "transition_motion_gate": {"status": "pending_generation"},
    }


def main() -> None:
    if not ANCHOR.is_file() or not ANCHOR_ORIGINAL.is_file():
        raise FileNotFoundError("Ancora C2 sem rabo ausente.")

    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(take.get("id") or ""): take for take in takes if isinstance(take, dict)}
    if "04C2" in by_id:
        source = by_id.get("04C")
        if isinstance(source, dict):
            source["render_authorized"] = False
            source["render_block_reason"] = (
                "Ancora com rabo reprovada pelo proprietario; substituida por 04C2 apos nova aprovacao."
            )
            _atomic_json_write(queue_path, queue)
        print(json.dumps({
            "ok": True,
            "idempotentRepair": True,
            "rejectedTakeBlocked": "04C",
            "existingCorrection": "04C2",
        }, ensure_ascii=False, indent=2))
        return

    source = by_id.get("04C")
    d1 = by_id.get("04D1")
    d2 = by_id.get("04D2")
    if not isinstance(source, dict) or str(source.get("maestro_status") or "").upper() != "REJECTED":
        raise ValueError("O 04C com rabo deve permanecer reprovado antes da correcao.")
    if not isinstance(d1, dict) or not isinstance(d2, dict):
        raise ValueError("Os reparos 04D1/04D2 precisam existir.")

    now = utc_now()
    request_id = uuid.uuid4().hex
    c2 = deepcopy(source)
    c2.update({
        "id": "04C2",
        "slug": "segundo_junior_impacto_sem_rabo",
        "name": "segundo_junior_impacto_sem_rabo",
        "sequence": 4.5,
        "objective": "Entregar o impacto em um Cell Junior azul pequeno e completamente sem rabo.",
        "editorial_use_seconds": 2.0,
        "animation_prompt": (
            "ONE CONTINUOUS PHOTOREALISTIC LIVE-ACTION IMPACT CONNECTOR between the exact supplied frames. "
            "Begin with exactly one teenage Gohan SSJ2 and exactly two compact child-sized saturated cobalt-blue "
            "Cell Juniors inherited from the approved first frame. Cell Junior 1 completes its existing breakup into "
            "non-anatomical blue fragments and never becomes another body. Gohan redirects the same momentum into one "
            "knee impact on Cell Junior 2. End with exactly Gohan and that one remaining small blue Junior. Both Cell "
            "Juniors are completely TAILLESS in every frame: no tail, stinger, tentacle, cable, rear extension or "
            "ambiguous appendage. The remaining Junior stays blue and child-sized. Camera continues one "
            "physical lateral orbit with slight crane rise and three-plane parallax. Useful body, debris, lightning "
            "and camera motion occupy 0-30%, 30-70% and 70-100%. End exactly at the supplied tailless C2 frame. "
            "FORBIDDEN: adult Cell, Perfect Cell, green armor, body growth, species change, morphing, tail, stinger, "
            "rear appendage, duplicate body, extra fighter, extra limb, reset, repeated impact, crossfade, freeze, "
            "hold, anime, game render, text, blood or gore."
        ),
        "cast_transition_contract": {
            "start": ["Gohan SSJ2", "Cell Junior blue 1", "Cell Junior blue 2"],
            "end": ["Gohan SSJ2", "Cell Junior blue 2"],
            "rule": "Junior 1 exits only as abstract blue fragments; Junior 2 remains the same small cobalt-blue tailless body, species and scale.",
        },
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana da ancora C2 sem rabo.",
        "maestro_director_requests": [{
            "id": request_id,
            "status": "PENDING",
            "category": "ANCHOR",
            "anchor_side": "end",
            "reason": (
                "Revisar a ancora C2: Cell Junior azul pequeno e completamente sem rabo, ferrao, tentaculo ou "
                "extensao traseira; nenhum Cell verde ou adulto."
            ),
            "created_at": now,
            "updated_at": now,
        }],
    })
    c2.pop("end_anchor_candidate", None)
    reset_runtime(c2, now)
    c2_shot = c2.setdefault("shot_contract", {})
    c2_refs = c2_shot.setdefault("visual_references", {})
    c2_refs.update({"end_frame_file": "", "end_frame_approved": False, "end_frame_sha256": ""})
    c2_shot["story_change"] = "Segundo Junior azul se aproxima -> o mesmo Junior azul e sem rabo recebe um unico joelho."
    c2_shot["motion_beats"] = {
        "start": "Gohan redireciona o impulso; o Junior azul pequeno continua entrando sem rabo.",
        "middle": "Um unico joelho conecta e desloca o Junior no mesmo vetor.",
        "end": "Junior azul permanece pequeno, sem rabo e dobrado sob o impacto; Gohan continua o follow-through.",
    }

    d1["base_image"] = {"status": "waiting_derived_anchor"}
    d1["render_authorized"] = False
    d1["render_block_reason"] = "Aguardando aprovacao e heranca da ancora C2 sem rabo."
    d1_refs = d1.setdefault("shot_contract", {}).setdefault("visual_references", {})
    d1_refs.update({
        "start_frame_file": "inherited from corrected C2 end anchor",
        "start_frame_approved": False,
        "start_frame_sha256": "",
    })

    source["render_authorized"] = False
    source["render_block_reason"] = (
        "Ancora com rabo reprovada pelo proprietario; substituida por 04C2 apos nova aprovacao."
    )

    insert_at = next(index for index, item in enumerate(takes) if item is d1)
    takes.insert(insert_at, c2)
    queue.update({
        "status": "WAITING_C2_ANCHOR_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "take04_c2_dmid_three_microtakes_v1",
            "batch_size": 3,
            "render_order": ["04C2", "04D1", "04D2"],
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
        "status": "WAITING_C2_ANCHOR_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
        "c2_no_tail_correction": {
            "rejected_take": "04C",
            "rejection": "Approved anchor contained a tail or ambiguous rear appendage on the Cell Junior.",
            "replacement_take": "04C2",
            "downstream_replacements": ["04D1", "04D2"],
            "anchor_status": "pending_human_qc",
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = False
    _atomic_json_write(production_path, production)

    metadata = {
        "prompt": "Remove every tail, stinger, tentacle and ambiguous rear appendage from the small blue Cell Junior while preserving Gohan, impact, camera, arena and effects.",
        "model": "OpenAI built-in image generation",
        "negative": "tail, stinger, rear appendage, adult Cell, green Cell, growth, morphing, duplicate, extra limb, text, blood, gore",
        "sourceOutput": ANCHOR_ORIGINAL.as_posix(),
        "sourceGeneratedAt": now,
        "sourceSha256": sha256(ANCHOR),
        "generator": "OpenAI built-in image generation",
        "workflow": "Codex imagegen precise-object-edit anti-tail anchor plus exact 16:9 normalization",
        "objective": c2["objective"],
        "requiredObjects": {
            "anchorSide": "end",
            "ownerReviewRequired": True,
            "blueCellJuniorRequired": True,
            "cellJuniorTail": False,
            "adultCellForbidden": True,
            "expectedVisibleCharacters": ["Gohan SSJ2", "Cell Junior blue 2"],
        },
    }
    view = register_end_anchor_candidate(
        PROJECTS_ROOT,
        PROJECT_ID,
        "04C2",
        request_id=request_id,
        image_bytes=ANCHOR.read_bytes(),
        original_filename=ANCHOR.name,
        metadata=metadata,
    )
    print(json.dumps({
        "ok": True,
        "projectId": PROJECT_ID,
        "rejectedPreserved": "04C",
        "correctionTakes": ["04C2", "04D1", "04D2"],
        "c2Candidate": view.get("endAnchorCandidate"),
        "renderAuthorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
