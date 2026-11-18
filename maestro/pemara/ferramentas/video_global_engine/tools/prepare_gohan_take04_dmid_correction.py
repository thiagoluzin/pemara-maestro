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
DMID = PROJECT / "keyframes" / "anchor_Dmid_second_junior_blue_disintegration_v1_1664x936.png"
DMID_ORIGINAL = PROJECT / "keyframes" / "anchor_Dmid_second_junior_blue_disintegration_v1.png"


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
        "status": "waiting_dmid_anchor_owner_review",
        "human_visual_approval": "pending",
        "transition_motion_gate": {"status": "pending_generation"},
    }


def main() -> None:
    if not DMID.is_file() or not DMID_ORIGINAL.is_file():
        raise FileNotFoundError("Ancora Dmid ausente.")
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(take.get("id") or ""): take for take in takes if isinstance(take, dict)}
    if "04D1" in by_id or "04D2" in by_id:
        raise FileExistsError("Os reparos 04D1/04D2 ja existem e nao serao sobrescritos.")
    source = by_id.get("04D")
    if not isinstance(source, dict) or str(source.get("maestro_status") or "").upper() != "REJECTED":
        raise ValueError("O 04D reprovado deve permanecer registrado antes da correcao.")

    now = utc_now()
    dmid_request = uuid.uuid4().hex
    d1 = deepcopy(source)
    d1.update({
        "id": "04D1",
        "slug": "segundo_junior_desintegracao_azul",
        "name": "segundo_junior_desintegracao_azul",
        "sequence": 5,
        "objective": "Manter o ultimo Junior pequeno e azul enquanto o impacto inicia sua desintegracao em fragmentos.",
        "editorial_use_seconds": 1.0,
        "characters": ["Gohan SSJ2", "Cell Junior blue 2"],
        "animation_prompt": (
            "ONE CONTINUOUS PHOTOREALISTIC LIVE-ACTION IMPACT-TO-DISINTEGRATION CONNECTOR between the exact supplied "
            "frames. Preserve one teenage Gohan SSJ2 and one small child-sized saturated cobalt-blue Cell Junior as "
            "two continuous bodies. Gohan knee remains committed and drives through exactly once. The Junior stays "
            "blue and child-sized while its struck torso progressively breaks into cobalt armor shards, blue electric "
            "particles and a directional wake. It never grows, never turns green and never resembles Perfect Cell. "
            "Camera continues one physical lateral orbit with slight crane rise and three-plane parallax. Useful body, "
            "debris, lightning and camera motion occupy 0-30%, 30-70% and 70-100%. End during the breakup, exactly at "
            "the supplied Dmid frame. FORBIDDEN: adult Cell, green armor, growth, morphing, second impact, reset, pose, "
            "crossfade, freeze, hold, static tail, duplicate body, extra limb, anime, game render, text, blood or gore."
        ),
        "cast_transition_contract": {
            "start": ["Gohan SSJ2", "Cell Junior blue 2"],
            "end": ["Gohan SSJ2", "Cell Junior blue 2 partially disintegrated"],
            "rule": "The same small blue Junior loses material into abstract fragments without changing identity, color or scale.",
        },
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana da ancora Dmid.",
        "maestro_director_requests": [{
            "id": dmid_request,
            "status": "PENDING",
            "category": "ANCHOR",
            "anchor_side": "end",
            "reason": "Revisar a ancora Dmid: segundo Junior ainda pequeno e azul, parcialmente desintegrado, sem verde, crescimento ou Perfect Cell.",
            "created_at": now,
            "updated_at": now,
        }],
    })
    d1.pop("end_anchor_candidate", None)
    reset_runtime(d1, now)
    d1_shot = d1.setdefault("shot_contract", {})
    d1_refs = d1_shot.setdefault("visual_references", {})
    d1_refs.update({"end_frame_file": "", "end_frame_approved": False, "end_frame_sha256": ""})
    d1_shot["story_change"] = "Segundo Junior azul inteiro sob o joelho -> o mesmo Junior azul quebrando em fragmentos no meio do impacto."
    d1_shot["motion_beats"] = {
        "start": "Joelho ja conectado; Junior pequeno e azul ainda inteiro.",
        "middle": "Armadura azul racha e perde fragmentos ao longo do mesmo vetor.",
        "end": "Desintegracao azul em curso; Gohan ainda gira e o Junior nao cresceu nem mudou de cor.",
    }

    d2 = deepcopy(source)
    d2.update({
        "id": "04D2",
        "slug": "residuo_azul_vira_giro",
        "name": "residuo_azul_vira_giro",
        "sequence": 6,
        "objective": "Completar a desintegracao azul do ultimo Junior e entregar o giro de Gohan para a entrada de Cell.",
        "editorial_use_seconds": 1.0,
        "base_image": {"status": "waiting_derived_anchor"},
        "animation_prompt": (
            "ONE CONTINUOUS PHOTOREALISTIC LIVE-ACTION DISINTEGRATION-TO-TURN CONNECTOR between the exact supplied "
            "frames. Begin with one teenage Gohan SSJ2 and the remaining small cobalt-blue Cell Junior already "
            "partially broken into fragments. Complete only that same blue disintegration: the remaining head and "
            "shoulder become abstract cobalt shards and electric particles while Gohan carries the knee follow-through "
            "into one airborne half-turn. No body grows, turns green or becomes Perfect Cell. Camera continues the same "
            "lateral orbit and crane rise with full three-plane parallax. End with only Gohan as a body and two abstract "
            "blue residue trails, exactly matching the supplied final frame. FORBIDDEN: adult Cell, green armor, growth, "
            "morphing, reappearing Junior, reset, pose, crossfade, freeze, hold, static tail, duplicate, anime, game "
            "render, text, blood or gore."
        ),
        "cast_transition_contract": {
            "start": ["Gohan SSJ2", "Cell Junior blue 2 partially disintegrated"],
            "end": ["Gohan SSJ2"],
            "rule": "Only the remaining blue fragments disappear; Gohan stays one continuous body and no new character enters.",
        },
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana e heranca da ancora Dmid.",
        "maestro_director_requests": [],
    })
    d2.pop("characters", None)
    d2.pop("end_anchor_candidate", None)
    reset_runtime(d2, now)
    d2_shot = d2.setdefault("shot_contract", {})
    d2_refs = d2_shot.setdefault("visual_references", {})
    # Keep the owner-approved D anchor already referenced by the rejected source.
    d2_refs["start_frame_file"] = "inherited from approved Dmid end anchor"
    d2_refs["start_frame_approved"] = False
    d2_refs["end_frame_approved"] = True
    d2_shot["story_change"] = "Junior azul parcialmente desintegrado -> somente Gohan em giro e residuos azuis abstratos."
    d2_shot["motion_beats"] = {
        "start": "Fragmentos azuis ainda carregam parte do Junior no vetor do joelho.",
        "middle": "A ultima anatomia azul se desfaz sem mudar de cor ou escala.",
        "end": "So Gohan permanece como corpo e continua o meio-giro.",
    }

    source["render_authorized"] = False
    source["render_block_reason"] = "Candidato rejeitado por morphing verde; substituido por 04D1/04D2 apos nova aprovacao."
    insert_at = next(index for index, item in enumerate(takes) if item is source) + 1
    takes[insert_at:insert_at] = [d1, d2]
    queue.update({
        "status": "WAITING_DMID_ANCHOR_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "take04_dmid_two_microtakes_v1",
            "batch_size": 2,
            "render_order": ["04D1", "04D2"],
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
        "status": "WAITING_DMID_ANCHOR_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
        "dmid_correction": {
            "rejected_take": "04D",
            "rejection": "Cell Junior grew and morphed into a green adult Cell-like body.",
            "replacement_takes": ["04D1", "04D2"],
            "editorial_seconds_each": 1.0,
            "anchor_status": "pending_human_qc",
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = False
    _atomic_json_write(production_path, production)

    metadata = {
        "prompt": "Ancora Dmid: Gohan mantem o joelho; o ultimo Cell Junior permanece pequeno e azul enquanto se desintegra em fragmentos cobalt-blue.",
        "model": "OpenAI built-in image generation",
        "negative": "no green, no growth, no adult Cell, no Perfect Cell, no morphing, no duplicate, no text, no blood, no gore",
        "sourceOutput": DMID_ORIGINAL.as_posix(),
        "sourceGeneratedAt": now,
        "sourceSha256": sha256(DMID),
        "generator": "OpenAI built-in image generation",
        "workflow": "Codex imagegen precise-object-edit Dmid anti-morph anchor plus exact 16:9 crop",
        "objective": d1["objective"],
        "requiredObjects": {
            "anchorSide": "end",
            "ownerReviewRequired": True,
            "blueCellJuniorRequired": True,
            "adultPerfectCellForbidden": True,
            "expectedVisibleCharacters": ["Gohan SSJ2", "Cell Junior blue 2 partially disintegrated"],
        },
    }
    view = register_end_anchor_candidate(
        PROJECTS_ROOT,
        PROJECT_ID,
        "04D1",
        request_id=dmid_request,
        image_bytes=DMID.read_bytes(),
        original_filename=DMID.name,
        metadata=metadata,
    )
    print(json.dumps({
        "ok": True,
        "projectId": PROJECT_ID,
        "rejectedPreserved": "04D",
        "correctionTakes": ["04D1", "04D2"],
        "dmidCandidate": view.get("endAnchorCandidate"),
        "renderAuthorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
