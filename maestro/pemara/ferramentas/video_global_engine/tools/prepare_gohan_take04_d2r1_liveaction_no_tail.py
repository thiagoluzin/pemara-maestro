from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT_ID = "gohan_ssj2_take04_cells_jr_multi_anchor_v2"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
SOURCE_ID = "04D2"
REPLACEMENT_ID = "04D2R1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_frame(take: dict, side: str) -> tuple[str, str]:
    refs = take.get("shot_contract", {}).get("visual_references", {})
    if refs.get(f"{side}_frame_approved") is not True:
        raise ValueError(f"{SOURCE_ID} {side} frame nao aprovado.")
    value = str(refs.get(f"{side}_frame_file") or "")
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    declared = str(refs.get(f"{side}_frame_sha256") or "").lower()
    if declared and declared != actual:
        raise ValueError(f"{SOURCE_ID} {side} hash divergente.")
    return path.as_posix(), actual


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(take.get("id") or ""): take for take in takes if isinstance(take, dict)}
    if REPLACEMENT_ID in by_id:
        print(json.dumps({"ok": True, "existingReplacement": REPLACEMENT_ID}, indent=2))
        return

    source = by_id.get(SOURCE_ID)
    if not isinstance(source, dict) or str(source.get("maestro_status") or "").upper() != "REJECTED":
        raise ValueError("04D2 precisa permanecer REJECTED antes do substituto.")
    start_file, start_hash = approved_frame(source, "start")
    end_file, end_hash = approved_frame(source, "end")
    now = utc_now()

    replacement = deepcopy(source)
    replacement.update({
        "id": REPLACEMENT_ID,
        "slug": "residuo_azul_vira_giro_liveaction_sem_rabo_r1",
        "name": "residuo_azul_vira_giro_liveaction_sem_rabo_r1",
        "sequence": 7.1,
        "objective": (
            "Completar a desintegracao do ultimo Cell Junior azul mantendo live action fotorealista e ausencia "
            "absoluta de rabo em todos os quadros."
        ),
        "editorial_use_seconds": 3.5,
        "animation_prompt": (
            "ONE UNBROKEN PHOTOREALISTIC LIVE-ACTION CINEMATIC SHOT between the exact supplied first and last frames. "
            "Every frame must look like practical live-action photography with real lens depth, natural skin pores, "
            "torn woven fabric, physically lit dust, volumetric atmosphere and realistic motion blur. Begin with one "
            "teenage Gohan SSJ2 and one compact child-sized saturated cobalt-blue Cell Junior already partially "
            "breaking into blue armor fragments. The Cell Junior is completely TAILLESS for its entire remaining "
            "existence: no tail, stinger, tentacle, cable, rear extension, curled silhouette or ambiguous appendage. "
            "At 0-30%, the same small blue Junior loses its remaining shoulder and torso into cobalt fragments while "
            "Gohan continues the inherited kick vector. At 30-70%, the last recognizable blue anatomy dissolves into "
            "non-humanoid particles; it never reforms and never changes species, color or scale. At 70-100%, only Gohan "
            "remains as a body and carries the same momentum into an airborne half-turn while blue debris trails exit "
            "behind him. Camera performs one physical lateral orbit with a crane rise, strong foreground debris crossing, "
            "midground character displacement and background ruin parallax. End exactly at the supplied live-action Gohan "
            "frame with no Cell body. FORBIDDEN: anime appearance, cel shading, illustration, drawn outlines, game render, "
            "plastic CGI skin, adult Cell, Perfect Cell, green armor, body growth, morphing, tail, stinger, tentacle, rear "
            "appendage, reappearing Junior, duplicate body, extra limb, reset, reversal, crossfade, freeze, hold, static "
            "tail, text, logo, watermark, blood or gore."
        ),
        "cast_transition_contract": {
            "start": ["Gohan SSJ2", "Cell Junior blue 2 partially disintegrated"],
            "end": ["Gohan SSJ2"],
            "rule": (
                "Only the same small blue tailless Junior disappears into non-anatomical fragments; Gohan remains one "
                "continuous live-action body and no new character enters."
            ),
        },
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_last_job_id": "",
        "maestro_last_error": "",
        "maestro_last_result": None,
        "maestro_director_requests": [],
        "maestro_notes": "Substituto automatico de 04D2 conforme regra do proprietario para toda rejeicao.",
        "render_authorized": True,
        "render_block_reason": "",
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {
            "status": "pending_generation",
            "human_visual_approval": "pending",
            "transition_motion_gate": {"status": "contract_ready_pending_artifact_qc"},
        },
        "owner_approvals": [{
            "scope": "automatic_replacement_after_rejection",
            "source": "explicit_owner_standing_rule",
            "rejected_take": SOURCE_ID,
            "authorized_at": now,
        }],
    })
    replacement.pop("characters", None)
    replacement.pop("end_anchor_candidate", None)
    refs = replacement.setdefault("shot_contract", {}).setdefault("visual_references", {})
    refs.update({
        "start_frame_file": start_file,
        "start_frame_approved": True,
        "start_frame_sha256": start_hash,
        "end_frame_file": end_file,
        "end_frame_approved": True,
        "end_frame_sha256": end_hash,
    })
    replacement["shot_contract"].update({
        "story_change": "Junior azul parcialmente desintegrado -> somente Gohan live action em giro e residuos azuis abstratos.",
        "motion_beats": {
            "start": "Junior azul sem rabo perde torso e ombro no vetor herdado.",
            "middle": "A ultima anatomia azul desaparece sem mudar de estilo, cor, especie ou escala.",
            "end": "Somente Gohan live action permanece e continua o giro com camera em orbita fisica.",
        },
    })

    source["render_authorized"] = False
    source["render_block_reason"] = "Reprovado; substituido por 04D2R1 conforme regra automatica do proprietario."
    insert_at = next(index for index, item in enumerate(takes) if item is source) + 1
    takes.insert(insert_at, replacement)
    queue.update({
        "status": "READY_FOR_04D2R1_AUTOMATIC_REPLACEMENT",
        "render_authorized": True,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "take04_d2r1_liveaction_no_tail_v1",
            "batch_size": 1,
            "render_order": [REPLACEMENT_ID],
            "strict_contiguous": True,
            "require_all_base_images_ready": True,
            "fill_eligible_across_batches": False,
            "require_full_batch": True,
            "allow_incomplete_correction_batch": False,
            "control_surface": "automatic_replacement_after_owner_rejection",
            "configured_at": now,
        },
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "READY_FOR_04D2R1_AUTOMATIC_REPLACEMENT",
        "render_authorized": True,
        "updated_at": now,
        "automatic_replacement": {
            "source_rejected_take": SOURCE_ID,
            "replacement_take": REPLACEMENT_ID,
            "reason": "04D2 became partially anime and created a tail.",
            "standing_rule": "owner rejection automatically authorizes a corrected candidate in the same scope",
            "anchor_lineage": {
                "start": start_file,
                "start_sha256": start_hash,
                "end": end_file,
                "end_sha256": end_hash,
            },
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = True
    _atomic_json_write(production_path, production)

    print(json.dumps({
        "ok": True,
        "rejectedPreserved": SOURCE_ID,
        "replacement": REPLACEMENT_ID,
        "anchorsApproved": True,
        "renderAuthorized": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
