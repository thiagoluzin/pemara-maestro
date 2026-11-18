from __future__ import annotations

import hashlib
import json
import shutil
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
    create_project,
    register_end_anchor_candidate,
    utc_now,
)


PROJECTS_ROOT = ENGINE_ROOT / "projetos"
SOURCE_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT_ID = "gohan_ssj2_take04_cells_jr_multi_anchor_v2"
SOURCE = PROJECTS_ROOT / SOURCE_ID
TARGET = PROJECTS_ROOT / PROJECT_ID


ANCHORS = {
    "A": SOURCE / "keyframes" / "take04_multi_anchor_A_two_blue_juniors_entry_v1_1664x936.png",
    "B": SOURCE / "keyframes" / "take04_multi_anchor_B_first_junior_impact_v1_1664x936.png",
    "C": SOURCE / "keyframes" / "take04_multi_anchor_C_second_junior_impact_v1_1664x936.png",
    "D": SOURCE / "keyframes" / "take04_multi_anchor_D_both_juniors_gone_pivot_v1_1664x936.png",
}
SOURCE_ORIGINALS = {
    "A": SOURCE / "keyframes" / "take04_multi_anchor_A_two_blue_juniors_entry_v1.png",
    "B": SOURCE / "keyframes" / "take04_multi_anchor_B_first_junior_impact_v1.png",
    "C": SOURCE / "keyframes" / "take04_multi_anchor_C_second_junior_impact_v1.png",
    "D": SOURCE / "keyframes" / "take04_multi_anchor_D_both_juniors_gone_pivot_v1.png",
}
ANCHOR_0 = SOURCE / "base_images" / "take03_gohan_super_saiyajin_2_anchor_d8724f626c47.png"
ANCHOR_E = SOURCE / "base_images" / "take04_cell_juniors_em_um_golpe_anchor_1d0a20158ca8.png"
IDENTITY = SOURCE / "refs" / "gohan_ssj2_identity_reference_approved.png"
CONTACT = SOURCE / "qc" / "take04_multi_anchor_v2_contact_5states.jpg"


SPECS = [
    {
        "id": "04A",
        "slug": "cell_sai_juniors_entram",
        "objective": "Retirar Cell adulto do eixo e introduzir exatamente dois Cell Juniors azuis sem morphing.",
        "start": "Gohan SSJ2 e Cell adulto ainda carregam o movimento herdado do take 03.",
        "action": "Cell adulto cruza e sai pelo fundo enquanto dois Cell Juniors azuis entram por planos opostos; nenhum corpo se transforma em outro.",
        "end": "Os dois Juniors azuis cercam Gohan e os tres continuam convergindo em velocidade.",
        "end_key": "A",
        "cast": ["Gohan SSJ2", "Perfect Cell exits", "Cell Junior blue 1", "Cell Junior blue 2"],
    },
    {
        "id": "04B",
        "slug": "primeiro_junior_impacto",
        "objective": "Fazer Gohan contra-atacar o primeiro Junior enquanto o segundo permanece azul, separado e legivel.",
        "start": "Dois Cell Juniors azuis convergem sobre Gohan de planos diferentes.",
        "action": "Gohan completa um unico contra-ataque curto no Junior 1; o Junior 2 continua intacto e atacando.",
        "end": "O primeiro Junior dobra sob o impacto e o segundo ainda fecha a distancia.",
        "end_key": "B",
        "cast": ["Gohan SSJ2", "Cell Junior blue 1", "Cell Junior blue 2"],
    },
    {
        "id": "04C",
        "slug": "segundo_junior_impacto",
        "objective": "Eliminar o primeiro Junior e redirecionar o mesmo impulso para atingir o segundo.",
        "start": "O primeiro Junior ainda recebe o impacto; o segundo continua entrando.",
        "action": "O Junior 1 desaparece em residuos azuis nao humanoides e Gohan redireciona sem pausa para um unico joelho no Junior 2.",
        "end": "Somente Gohan e o segundo Junior azul permanecem como corpos; o joelho ainda atravessa o contato.",
        "end_key": "C",
        "cast": ["Gohan SSJ2", "Cell Junior blue 2"],
    },
    {
        "id": "04D",
        "slug": "dois_juniors_eliminados",
        "objective": "Completar a eliminacao do segundo Junior e manter Gohan girando para a proxima ameaca.",
        "start": "Gohan ainda atravessa o segundo Junior com o joelho em movimento.",
        "action": "O Junior 2 desaparece em residuos azuis e Gohan carrega o follow-through para um meio-giro aereo.",
        "end": "Gohan continua girando; os dois Juniors existem apenas como duas trilhas azuis abstratas.",
        "end_key": "D",
        "cast": ["Gohan SSJ2"],
    },
    {
        "id": "04E",
        "slug": "cell_adulto_entra_no_eixo",
        "objective": "Converter o giro de Gohan na entrada separada de Perfect Cell, sem cauda e sem morphing.",
        "start": "Gohan ainda gira entre duas trilhas residuais azuis; nao ha outro corpo em quadro.",
        "action": "Perfect Cell entra fisicamente pelo espaco aberto enquanto Gohan termina o giro em deslocamento; nenhum residuo azul vira personagem.",
        "end": "Gohan e Perfect Cell sem cauda continuam fechando a distancia no eixo aprovado do take 05.",
        "end_key": "E",
        "cast": ["Gohan SSJ2", "Perfect Cell no tail"],
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt(spec: dict[str, object]) -> str:
    return (
        "ONE CONTINUOUS PHOTOREALISTIC LIVE-ACTION DRAGON BALL ACTION CONNECTOR between the exact supplied moving "
        "first and last frames. Preserve teenage Gohan SSJ2 identity, torn dark-purple gi, stormy ruined Cell Games "
        "arena, extravagant gold-white aura, dense blue-white lightning and irreversible debris continuity. "
        f"ENTRY: {spec['start']} ACTION: {spec['action']} EXIT: {spec['end']} "
        "Camera performs one physical lateral orbit with a slight crane rise, visible foreground/midground/background "
        "parallax and no reversal. Bodies, cloth, armor, lightning, dust and rocks keep independent useful motion in "
        "0-30%, 30-70% and 70-100%. Cell Juniors are compact child-sized bio-androids with saturated cobalt-blue spotted "
        "exoskeleton and black armor, never green or gray. Perfect Cell is a distinct adult body with no tail, stinger, "
        "rear appendage or tentacle. FORBIDDEN: morphing one character into another, duplicate body, extra fighter, extra "
        "limb, pose reset, repeated strike, return to idle, static lineup, simple zoom, crossfade, freeze, hold, static "
        "tail, anime drawing, cel shading, game render, subtitles, logo, watermark, blood or gore."
    )


def take_record(spec: dict[str, object], index: int, now: str) -> dict[str, object]:
    start_file = TARGET / "keyframes" / "anchor_0_take03_exit_approved.png" if index == 0 else None
    end_is_approved = str(spec["end_key"]) == "E"
    end_file = TARGET / "keyframes" / "anchor_E_cell_enters_approved.png" if end_is_approved else None
    request_id = uuid.uuid4().hex if not end_is_approved else ""
    base = {
        "status": "approved_for_video",
        "file": start_file.as_posix(),
        "source": "approved take03 moving boundary",
        "image_sha256": sha256(start_file),
        "approved_at": now,
    } if start_file else {"status": "waiting_derived_anchor"}
    requests = []
    if request_id:
        requests.append({
            "id": request_id,
            "status": "PENDING",
            "category": "ANCHOR",
            "anchor_side": "end",
            "reason": f"Revisar ancora {spec['end_key']} da cadeia multi-ancora do take 04: {spec['objective']}",
            "created_at": now,
            "updated_at": now,
        })
    return {
        "id": spec["id"],
        "slug": spec["slug"],
        "name": spec["slug"],
        "sequence": index + 1,
        "role": "take04_multi_anchor_continuous_action_connector",
        "is_transition": True,
        "objective": spec["objective"],
        "target_duration_seconds": 5.125,
        "editorial_use_seconds": 2.0,
        "characters": spec["cast"],
        "animation_prompt": prompt(spec),
        "base_image": base,
        "shot_contract": {
            "story_purpose": spec["objective"],
            "dramatic_question": "Como uma acao em curso produz exatamente uma consequencia irreversivel sem reset?",
            "story_change": f"{spec['start']} -> {spec['end']}",
            "distinct_story_events": 1,
            "motion_beats": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
            "camera": {
                "movement": "orbita lateral fisica com leve crane ascendente, mantendo o eixo da forca",
                "angle": "baixo tres-quartos em progressao",
                "lens": "24-35 mm equivalente",
                "focus": "corpos em acao com tres planos de profundidade",
            },
            "visual_references": {
                "start_frame_file": start_file.as_posix() if start_file else "inherited from previous approved end anchor",
                "start_frame_approved": bool(start_file),
                "end_frame_file": end_file.as_posix() if end_file else "",
                "end_frame_approved": end_is_approved,
                "end_frame_sha256": sha256(end_file) if end_file else "",
                "gohan_identity": (TARGET / "refs" / "gohan_ssj2_identity_reference_approved.png").as_posix(),
            },
            "transition_motion_contract": {
                "camera_evidence": {"physical_translation": True, "movement": "lateral orbit plus crane rise"},
                "real_depth": {"differential_motion": "foreground fastest, bodies midground, arena slowest"},
                "internal_action": {"primary_event": spec["action"], "camera_independent": True},
                "progression": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
                "continuity": {
                    "editorial_method": "five_generated_action_microtakes_hard_cut_on_motion",
                    "continuous_action": True,
                    "motion_handoff": True,
                    "action_occupies_full_duration": True,
                    "crossfade_frames": 0,
                    "freeze_frames": 0,
                    "static_hold_frames": 0,
                },
            },
        },
        "video_generation": {
            "profile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "fps": 24,
            "frames": 124,
            "steps": 20,
            "guidance": 1.0,
            "start_end_frame_enabled": True,
            "require_approved_start_frame": True,
            "require_approved_end_frame": True,
            "visual_only_pass": True,
            "native_audio_authorized": False,
        },
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana das quatro novas ancoras A-D.",
        "audio_direction": {"status": "blocked_until_picture_lock", "music": False, "dialogue": False},
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {
            "status": "waiting_multi_anchor_owner_review",
            "human_visual_approval": "pending",
            "transition_motion_gate": {"status": "pending_generation"},
        },
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_director_requests": requests,
    }


def main() -> None:
    required = [*ANCHORS.values(), *SOURCE_ORIGINALS.values(), ANCHOR_0, ANCHOR_E, IDENTITY, CONTACT]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Arquivos obrigatorios ausentes:\n" + "\n".join(missing))
    if TARGET.exists():
        raise FileExistsError(f"Projeto ja existe e nao sera sobrescrito: {TARGET}")

    now = utc_now()
    create_project(
        PROJECTS_ROOT,
        name="Gohan SSJ2 - Take 04 Cells Jr Multi-Ancora V2",
        project_id=PROJECT_ID,
        objective="Refazer o take 04 com cinco microtakes H3, seis fronteiras moveis e nenhum morphing de personagem.",
        duration_seconds=10,
    )
    (TARGET / "base_images").mkdir(exist_ok=True)
    shutil.copy2(ANCHOR_0, TARGET / "keyframes" / "anchor_0_take03_exit_approved.png")
    shutil.copy2(ANCHOR_E, TARGET / "keyframes" / "anchor_E_cell_enters_approved.png")
    shutil.copy2(IDENTITY, TARGET / "refs" / IDENTITY.name)
    shutil.copy2(CONTACT, TARGET / "qc" / CONTACT.name)

    queue = {
        "schema_version": "gohan_take04_multi_anchor_queue_v2",
        "project_id": PROJECT_ID,
        "status": "WAITING_OWNER_ANCHOR_REVIEW",
        "updated_at": now,
        "render_authorized": False,
        "methodology": "five_minimax_h3_microtakes_six_moving_anchors_exactly_two_seconds_each",
        "anchor_generation_policy": {
            "version": "take04_multi_anchor_v2",
            "provider": "openai_builtin_image_generation_registered_in_maestro",
            "inherit_approved_end_as_next_start": True,
            "require_explicit_human_confirmation": True,
            "human_review_required": True,
            "require_visual_cast_verification_for_video": True,
        },
        "continuous_action_contract": {
            "generated_connector_required_between_anchors": True,
            "crossfade_forbidden": True,
            "freeze_frame_forbidden": True,
            "static_tail_forbidden": True,
            "motion_handoff_required": True,
            "full_duration_motion_required": True,
            "moving_transition_anchors_required": True,
        },
        "takes": [take_record(spec, index, now) for index, spec in enumerate(SPECS)],
    }
    production = {
        "schema_version": "gohan_take04_multi_anchor_production_v2",
        "project_id": PROJECT_ID,
        "source_project_id": SOURCE_ID,
        "role": "take04_correction_multi_anchor_connectors",
        "status": "WAITING_OWNER_ANCHOR_REVIEW",
        "updated_at": now,
        "editorial_target_seconds": 10.0,
        "native_source_plan_seconds": 25.625,
        "editorial_plan": "Selecionar exatamente 2.000 s continuos de cada um dos cinco microtakes e montar por hard cuts em movimento.",
        "video_generation": {
            "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot",
            "profile": "minimax_h3_fl2va_int8_720p24",
            "serial_gpu_only": True,
            "visual_only_pass": True,
            "native_audio_authorized": False,
            "render_authorized": False,
        },
        "forbidden": [
            "crossfade, freeze frame, hold or static tail",
            "morphing between Perfect Cell and Cell Juniors",
            "green or gray Cell Juniors",
            "tail, stinger or rear appendage on Perfect Cell",
            "single straight camera line or zoom-only movement",
        ],
        "takes": [
            {
                "id": spec["id"],
                "objective": spec["objective"],
                "start": spec["start"],
                "action": spec["action"],
                "end": spec["end"],
                "editorial_use_seconds": 2.0,
            }
            for spec in SPECS
        ],
    }
    manifest_path = TARGET / "project_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update({
        "schema_version": "gohan_take04_multi_anchor_project_v2",
        "status": "WAITING_OWNER_ANCHOR_REVIEW",
        "maestro_status": "IN_PROGRESS",
        "updated_at": now,
        "source_project_id": SOURCE_ID,
        "source_take_id": "04",
        "render_authorized": False,
        "contact_sheet": f"qc/{CONTACT.name}",
        "methodology": "Vegito-style moving-anchor chain: 0-A-B-C-D-E, five H3 microtakes, no xfade or freeze.",
    })
    _atomic_json_write(TARGET / "take_queue.json", queue)
    _atomic_json_write(TARGET / "production_manifest.json", production)
    _atomic_json_write(manifest_path, manifest)

    registered: list[dict[str, object]] = []
    for index, key in enumerate(("A", "B", "C", "D")):
        take = queue["takes"][index]
        request_id = take["maestro_director_requests"][0]["id"]
        image = ANCHORS[key]
        metadata = {
            "prompt": f"Take 04 multi-anchor {key}: {SPECS[index]['objective']}",
            "model": "OpenAI built-in image generation",
            "negative": "no morphing, no extra character, no green Cell Junior, no adult Cell tail, no text, no blood, no gore",
            "sourceOutput": SOURCE_ORIGINALS[key].as_posix(),
            "sourceGeneratedAt": now,
            "sourceSha256": sha256(image),
            "generator": "OpenAI built-in image generation",
            "workflow": "Codex imagegen sequential identity-preserving multi-anchor chain plus exact 16:9 crop",
            "objective": SPECS[index]["objective"],
            "requiredObjects": {
                "anchorSide": "end",
                "ownerReviewRequired": True,
                "blueCellJuniorsRequired": key in {"A", "B", "C"},
                "perfectCellTail": False,
                "expectedVisibleCharacters": SPECS[index]["cast"],
            },
        }
        view = register_end_anchor_candidate(
            PROJECTS_ROOT,
            PROJECT_ID,
            str(take["id"]),
            request_id=request_id,
            image_bytes=image.read_bytes(),
            original_filename=image.name,
            metadata=metadata,
        )
        registered.append({
            "takeId": take["id"],
            "anchor": key,
            "requestId": request_id,
            "candidate": view.get("endAnchorCandidate"),
        })

    status = (
        "# STATUS - Take 04 Cells Jr Multi-Ancora V2\n\n"
        "- Estado: aguardando revisao humana das ancoras A-D no Maestro.\n"
        "- Motor: MiniMax H3 FL2VA INT8, cinco microtakes de 5,125 s gerados em serie.\n"
        "- Montagem planejada: 2,000 s uteis de cada microtake = 10,000 s, hard cuts em movimento.\n"
        "- Proibido: crossfade, freeze, hold, morphing, Juniors verdes/cinzas e cauda no Perfect Cell.\n"
        "- O take 04 anterior permanece preservado no projeto de origem e nao foi substituido.\n"
    )
    (TARGET / "STATUS.md").write_text(status, encoding="utf-8", newline="\n")
    print(json.dumps({
        "ok": True,
        "projectId": PROJECT_ID,
        "projectRoot": str(TARGET),
        "registered": registered,
        "renderAuthorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
