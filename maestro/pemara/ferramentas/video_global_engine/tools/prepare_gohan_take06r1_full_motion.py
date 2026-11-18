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


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
SOURCE_ID = "06"
REPLACEMENT_ID = "06R1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_frame(take: dict, side: str) -> tuple[str, str]:
    refs = take.get("shot_contract", {}).get("visual_references", {})
    if refs.get(f"{side}_frame_approved") is not True:
        raise ValueError(f"{SOURCE_ID} {side} frame nao aprovado.")
    path = Path(str(refs.get(f"{side}_frame_file") or ""))
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
        raise ValueError("Take 06 precisa permanecer REJECTED antes do substituto.")

    start_file, start_hash = approved_frame(source, "start")
    end_file, end_hash = approved_frame(source, "end")
    now = utc_now()
    replacement = deepcopy(source)
    replacement.update({
        "id": REPLACEMENT_ID,
        "slug": "cell_lancado_pela_arena_full_motion_r1",
        "name": "cell_lancado_pela_arena_full_motion_r1",
        "sequence": 6.1,
        "objective": (
            "Fechar o minuto com Gohan perseguindo e lancando Perfect Cell sem cauda atraves da arena, mantendo "
            "movimento fisico util ate o ultimo quadro."
        ),
        "editorial_use_seconds": 10.0,
        "animation_prompt": (
            "ONE UNBROKEN 10.083333-SECOND PHOTOREALISTIC LIVE-ACTION CINEMATIC PURSUIT between the exact approved "
            "first and last frames. Preserve exactly one teenage Gohan SSJ2 and exactly one full-size adult green-and-"
            "black Perfect Cell as continuous live-action bodies. Perfect Cell is completely TAILLESS in every frame: "
            "no tail, stinger, tentacle, cable, rear extension or ambiguous appendage; his silhouette ends cleanly at "
            "the pelvis, with only two rigid symmetrical upper-back wing plates. Every frame has realistic skin, torn "
            "woven fabric, practical creature armor, real lens depth, physically lit dust and cinematic motion blur. "
            "At 0-30%, Cell is still rising from the approved uppercut while Gohan immediately pursues; Cell fires one "
            "short defensive burst and Gohan redirects it past the moving camera while both cross real distance. At "
            "30-70%, Cell makes one two-forearm swing; Gohan completes one block and one knee to the torso, forcing Cell "
            "downward through a new arc without reset or repeated strike. At 70-100%, Gohan converts that same momentum "
            "into exactly one side kick after 8.3 seconds; Cell flies through the remaining space and breaks outward "
            "through a stone wall while Gohan continues pursuit. Camera performs a continuous physical crane rise, dives "
            "with the knee, accelerates laterally through broken architecture and exits with both perspective and arena "
            "geometry still changing. Foreground slabs, midground bodies and background ruins maintain different speeds; "
            "hair, clothing, armor, lightning, dust and wall fragments move independently. Do not approach the approved "
            "final composition before the last 0.10 seconds. At the final frame, Cell, Gohan, camera, lightning, dust and "
            "stone fragments must still carry visible directional velocity. FORBIDDEN: held pose, frozen ending, near-"
            "static tail, early final composition, early wall breach, reset, reversal, teleportation, repeated kick, "
            "duplicate body, extra fighter, extra limb, body substitution, anime appearance, cel shading, illustration, "
            "game render, plastic CGI skin, tail, stinger, rear appendage, dialogue, text, logo, watermark, blood or gore."
        ),
        "cast_transition_contract": {
            "start": ["Gohan SSJ2", "Perfect Cell"],
            "end": ["Gohan SSJ2", "Perfect Cell"],
            "rule": (
                "The same Gohan and the same full-size tailless Perfect Cell remain continuous live-action bodies; no "
                "new fighter, duplicate or species change is allowed."
            ),
        },
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_last_job_id": "",
        "maestro_last_error": "",
        "maestro_last_result": None,
        "maestro_director_requests": [],
        "maestro_notes": "Substituto autorizado pelo pedido de gerar todos os takes restantes.",
        "render_authorized": True,
        "render_block_reason": "",
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {
            "status": "pending_generation",
            "human_visual_approval": "pending",
            "transition_motion_gate": {"status": "contract_ready_pending_artifact_qc"},
        },
        "owner_approvals": [{
            "scope": "generate_all_remaining_visual_takes",
            "source": "explicit_owner_message",
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
        "story_change": "Cell sobe do uppercut sob perseguicao -> Cell atravessa a parede enquanto Gohan continua avancando.",
        "motion_beats": {
            "start": "Perseguicao imediata e rajada curta desviada com camera subindo.",
            "middle": "Bloqueio e joelho completos forcam Cell para baixo sem reset.",
            "end": "Chute unico rompe a parede; Cell, Gohan, camera e destrocos continuam em velocidade no corte.",
        },
    })

    source["render_authorized"] = False
    source["render_block_reason"] = "Candidato com cauda estatica preservado; substituido por 06R1."
    insert_at = next(index for index, item in enumerate(takes) if item is source) + 1
    takes.insert(insert_at, replacement)
    queue.update({
        "status": "READY_FOR_TAKE06R1_REMAINING_BATCH",
        "render_authorized": True,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "gohan_take06r1_full_motion_v1",
            "batch_size": 1,
            "render_order": [REPLACEMENT_ID],
            "strict_contiguous": True,
            "require_all_base_images_ready": True,
            "fill_eligible_across_batches": False,
            "require_full_batch": True,
            "allow_incomplete_correction_batch": False,
            "control_surface": "owner_generate_all_remaining_takes",
            "configured_at": now,
        },
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "READY_FOR_TAKE06R1_REMAINING_BATCH",
        "render_authorized": True,
        "updated_at": now,
        "remaining_visual_generation": {
            "source_rejected_take": SOURCE_ID,
            "replacement_take": REPLACEMENT_ID,
            "reason": "Take 06 original ended with a near-static tail.",
            "owner_scope": "generate all remaining visual takes",
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
