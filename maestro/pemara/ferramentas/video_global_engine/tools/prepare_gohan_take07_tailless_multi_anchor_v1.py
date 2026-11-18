from __future__ import annotations

import hashlib
import json
import shutil
import sys
import uuid
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
PROJECT_ID = "gohan_ssj2_take07_tailless_multi_anchor_v1"
SOURCE = PROJECTS_ROOT / SOURCE_ID
TARGET = PROJECTS_ROOT / PROJECT_ID

ANCHOR_0 = SOURCE / "base_images" / "take06_cell_lancado_pela_arena_anchor_bdd4b9b79e35.png"
ANCHOR_A = SOURCE / "keyframes" / "take07_multi_anchor_A_parry_tailless_v1_1664x936.png"
ANCHOR_B = SOURCE / "keyframes" / "take07_multi_anchor_B_body_punch_tailless_v1_1664x936.png"
ANCHOR_E = SOURCE / "base_images" / "take07_gohan_cell_trocacao_pressao_anchor_4dbdaabe7124.png"

SPECS = [
    {
        "id": "07A",
        "slug": "cell_contra_ataca_gohan_apara",
        "objective": "Herdar a perseguicao e converter o contra-ataque de Cell em uma defesa progressiva de Gohan.",
        "start": "Cell sem cauda ainda cruza os destrocos em velocidade e Gohan SSJ2 o alcanca.",
        "action": "Cell sem cauda gira o torso para um unico direto; Gohan fecha distancia e apara sem reset.",
        "end": "As maos se encontram no bloqueio e os dois corpos continuam atravessando o quadro.",
        "end_anchor": ANCHOR_A,
    },
    {
        "id": "07B",
        "slug": "gohan_rompe_guarda_cell",
        "objective": "Transformar o bloqueio em dois impactos separados e legiveis que quebram a guarda de Cell.",
        "start": "Gohan ainda desvia o direto de Cell e conserva o avanco.",
        "action": "Cell tenta um joelho; Gohan bloqueia e responde com um golpe curto no corpo.",
        "end": "O golpe entra na guarda e Cell sem cauda torce para tras, ainda em movimento.",
        "end_anchor": ANCHOR_B,
    },
    {
        "id": "07C",
        "slug": "gohan_pressiona_cell_recuo",
        "objective": "Completar a dominacao com Gohan avancando e Cell recuando continuamente ate a fronteira aprovada.",
        "start": "Cell sem cauda ainda absorve o golpe no corpo e sua guarda desaba.",
        "action": "Gohan conecta um unico golpe compacto na guarda e continua ocupando o espaco.",
        "end": "Cell sem cauda derrapa para tras enquanto Gohan o pressiona, ambos ainda com velocidade.",
        "end_anchor": ANCHOR_E,
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def animation_prompt(spec: dict[str, object]) -> str:
    return (
        "ONE CONTINUOUS 5.125-SECOND PHOTOREALISTIC LIVE-ACTION DRAGON BALL COMBAT CONNECTOR between the exact "
        "supplied moving first and last frames. Preserve exactly one teenage SSJ2 Gohan and exactly one adult "
        "Perfect Cell as continuous bodies. CRITICAL EVERY-FRAME SILHOUETTE LOCK: Perfect Cell is completely "
        "tailless; his anatomy ends cleanly at the pelvis. No tail, stinger, tentacle, cable, curved rear limb, "
        "rear tube, third rear blade or ambiguous appendage may appear, including in motion blur. Only two short "
        "rigid symmetrical upper-back wing plates are allowed. "
        f"ENTRY: {spec['start']} ACTION: {spec['action']} EXIT: {spec['end']} "
        "Camera performs a physical lateral-descending orbit with a new axis, strong foreground/midground/background "
        "parallax and no zoom-only move. Bodies, hair, cloth, armor, lightning, dust and rubble retain useful directional "
        "motion through 0-30%, 30-70% and 70-100%. Reach the supplied final frame only at the cut. FORBIDDEN: any tail "
        "or rear appendage, pose reset, repeated strike, return to idle, held ending, freeze, crossfade, teleportation, "
        "duplicate body, extra fighter, extra limb, Cell Junior, energy beam, anime drawing, cel shading, game render, "
        "plastic CGI skin, subtitles, logo, watermark, blood or gore."
    )


def take_record(spec: dict[str, object], index: int, now: str) -> dict[str, object]:
    start_file = TARGET / "keyframes" / "anchor_0_take06_exit_approved.png" if index == 0 else None
    end_is_final = index == len(SPECS) - 1
    end_file = TARGET / "keyframes" / "anchor_E_take07_exit_approved.png" if end_is_final else None
    request_id = "" if end_is_final else uuid.uuid4().hex
    base_image = (
        {
            "status": "approved_for_video",
            "file": start_file.as_posix(),
            "source": "approved take06 moving boundary",
            "image_sha256": sha256(start_file),
            "approved_at": now,
        }
        if start_file
        else {"status": "waiting_derived_anchor"}
    )
    requests = []
    if request_id:
        requests.append(
            {
                "id": request_id,
                "status": "PENDING",
                "category": "ANCHOR",
                "anchor_side": "end",
                "reason": f"Revisar ancora intermediaria sem cauda: {spec['objective']}",
                "created_at": now,
                "updated_at": now,
            }
        )
    return {
        "id": spec["id"],
        "slug": spec["slug"],
        "name": spec["slug"],
        "sequence": index + 1,
        "role": "take07_tailless_multi_anchor_connector",
        "is_transition": True,
        "objective": spec["objective"],
        "target_duration_seconds": 5.125,
        "editorial_use_seconds": 10.0 / 3.0,
        "animation_prompt": animation_prompt(spec),
        "base_image": base_image,
        "shot_contract": {
            "story_purpose": spec["objective"],
            "dramatic_question": "Como Gohan transforma a perseguicao em dominacao sem Cell ganhar cauda?",
            "story_change": f"{spec['start']} -> {spec['end']}",
            "distinct_story_events": 1,
            "motion_beats": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
            "camera": {
                "movement": "orbita lateral-descendente fisica com troca de eixo",
                "angle": "baixo tres-quartos em progressao",
                "lens": "24-35 mm equivalente",
                "focus": "impacto corporal e silhueta limpa do Cell",
            },
            "visual_references": {
                "start_frame_file": start_file.as_posix() if start_file else "inherited from previous approved end anchor",
                "start_frame_approved": bool(start_file),
                "end_frame_file": end_file.as_posix() if end_file else "",
                "end_frame_approved": end_is_final,
                "end_frame_sha256": sha256(end_file) if end_file else "",
            },
            "transition_motion_contract": {
                "camera_evidence": {"physical_translation": True, "movement": "lateral descending orbit"},
                "real_depth": {"differential_motion": "foreground fastest, fighters midground, ruins slowest"},
                "internal_action": {"primary_event": spec["action"], "camera_independent": True},
                "progression": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
                "continuity": {
                    "editorial_method": "three_generated_action_microtakes_hard_cut_on_motion",
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
        "render_block_reason": "Aguardando aprovacao humana das duas novas ancoras intermediarias.",
        "audio_direction": {"status": "blocked_until_picture_lock", "music": False, "dialogue": False},
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {"status": "waiting_multi_anchor_owner_review", "human_visual_approval": "pending"},
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_director_requests": requests,
    }


def main() -> None:
    required = [ANCHOR_0, ANCHOR_A, ANCHOR_B, ANCHOR_E]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Arquivos obrigatorios ausentes:\n" + "\n".join(missing))
    if TARGET.exists():
        raise FileExistsError(f"Projeto ja existe e nao sera sobrescrito: {TARGET}")

    now = utc_now()
    create_project(
        PROJECTS_ROOT,
        name="Gohan SSJ2 - Take 07 sem cauda Multi-Ancora V1",
        project_id=PROJECT_ID,
        objective="Refazer o take 07 em tres microtakes H3 com quatro fronteiras sem cauda verificaveis.",
        duration_seconds=10,
    )
    shutil.copy2(ANCHOR_0, TARGET / "keyframes" / "anchor_0_take06_exit_approved.png")
    shutil.copy2(ANCHOR_E, TARGET / "keyframes" / "anchor_E_take07_exit_approved.png")

    queue = {
        "schema_version": "gohan_take07_tailless_multi_anchor_queue_v1",
        "project_id": PROJECT_ID,
        "status": "WAITING_OWNER_ANCHOR_REVIEW",
        "updated_at": now,
        "render_authorized": False,
        "methodology": "three_minimax_h3_microtakes_four_moving_anchors",
        "anchor_generation_policy": {
            "version": "take07_tailless_multi_anchor_v1",
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
    manifest_path = TARGET / "project_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update(
        {
            "schema_version": "gohan_take07_tailless_multi_anchor_project_v1",
            "status": "WAITING_OWNER_ANCHOR_REVIEW",
            "maestro_status": "IN_PROGRESS",
            "updated_at": now,
            "source_project_id": SOURCE_ID,
            "source_take_id": "07",
            "render_authorized": False,
            "methodology": "moving-anchor chain 0-A-B-E, three H3 microtakes, hard cuts on motion",
        }
    )
    _atomic_json_write(TARGET / "take_queue.json", queue)
    _atomic_json_write(manifest_path, manifest)

    registered = []
    for index, (label, image) in enumerate((("A", ANCHOR_A), ("B", ANCHOR_B))):
        take = queue["takes"][index]
        request_id = take["maestro_director_requests"][0]["id"]
        view = register_end_anchor_candidate(
            PROJECTS_ROOT,
            PROJECT_ID,
            str(take["id"]),
            request_id=request_id,
            image_bytes=image.read_bytes(),
            original_filename=image.name,
            metadata={
                "prompt": f"Take 07 multi-anchor {label}: {SPECS[index]['objective']}",
                "model": "OpenAI built-in image generation",
                "sourceOutput": image.as_posix(),
                "sourceGeneratedAt": now,
                "sourceSha256": sha256(image),
                "generator": "OpenAI built-in image generation",
                "workflow": "Codex imagegen identity-preserving tailless anchor plus exact 16:9 crop",
                "objective": SPECS[index]["objective"],
                "requiredObjects": {
                    "anchorSide": "end",
                    "ownerReviewRequired": True,
                    "expectedVisibleCharacters": ["Gohan SSJ2", "Perfect Cell no tail"],
                    "perfectCellTail": False,
                },
            },
        )
        registered.append({"takeId": take["id"], "anchor": label, "requestId": request_id, "candidate": view.get("endAnchorCandidate")})

    print(
        json.dumps(
            {"ok": True, "projectId": PROJECT_ID, "projectRoot": str(TARGET), "registered": registered, "renderAuthorized": False},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
