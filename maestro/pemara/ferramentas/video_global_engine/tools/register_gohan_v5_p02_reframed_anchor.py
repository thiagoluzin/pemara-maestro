"""Close the failed prompt-only P01 route and register the reframed P02 anchor."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import uuid
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
ENGINE = BASE / "ferramentas" / "video_global_engine"
PROJECTS = ENGINE / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
SOURCE = (
    PROJECT / "base_images" / "v5_p02_tight_boot_downstroke_no_rear_candidate_v1_1536x864.png"
)
ARCHIVE = PROJECT / "archive" / "before_v5_p02_reframed_anchor"
PILOT_ID = "P02"

sys.path.insert(0, str(STUDIO))

from video_projects import (  # noqa: E402
    _atomic_json_write,
    list_takes,
    patch_take,
    register_anchor_candidate,
    utc_now,
)


REJECTION_REASON = (
    "P01C1 reprovado no QC interno: a camera e o movimento melhoraram, mas Perfect "
    "Cell ainda cria uma cauda visivel ao sair do quadro. A unica correcao prompt-only "
    "foi consumida; mudar para enquadramento fechado que exclui quadril e traseira."
)

REJECTION_INSTRUCTION = (
    "Preservar P01 e P01C1 como rollback. Encerrar novas tentativas prompt-only com "
    "a composicao aberta. A proxima rota usa uma ancora fechada na bota, sem quadril, "
    "traseira ou raiz das asas visiveis, e exige nova aprovacao humana."
)

PROMPT = (
    "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION ACTION TAKE FROM "
    "THE EXACT APPROVED TIGHT START FRAME. Preserve the exact ordinary Super Saiyan "
    "teenage Gohan, the exact cropped bio-android legs and descending boot, Android "
    "16's purely mechanical head, ruined arena and storm lighting. Never expand the "
    "bio-android upward or backward beyond what the reference shows. 0-30%: motion "
    "continues on frame one; the huge descending boot completes exactly one mechanical "
    "impact within the first second while Gohan keeps sprinting and the ground-level "
    "camera is physically thrown sideways. Metal, ceramic and circuits burst laterally. "
    "30-70%: the cropped legs and boot leave completely through the top-right edge and "
    "never return. The camera races left along the new floor crack, overtakes foreground "
    "fragments and passes the approaching Gohan with strong perspective change. Gohan "
    "plants through the shockwave while hair, clothing, dust and stones retain separate "
    "velocities. 70-100%: Gohan never poses. Gold pressure expands once, the first "
    "blue-white arc travels across the arena, and Gohan immediately launches forward "
    "past the moving camera. Cut mid-launch with camera, Gohan, lightning, dust and debris "
    "still moving. FORBIDDEN: reveal or reconstruct the bio-android pelvis, hips, back, "
    "rear silhouette or wing roots; tail, stinger, cable, tentacle, snake shape or rear "
    "appendage; static hold; living photo; freeze tail; centered final pose; boot reset; "
    "repeated stomp; tear or liquid; blood; gore; duplicate character; anime; game render; "
    "crossfade; zoom-only camera; text; logo; watermark."
)

ANCHOR_PROMPT = (
    "Photorealistic live-action tight action anchor: extreme low camera beside Android "
    "16's intact mechanical head; exactly one huge bio-android boot descends with an air "
    "gap; only cropped legs/chest fragments are visible at the top edge and all pelvis, "
    "hips, back and rear anatomy remain outside frame; ordinary Super Saiyan teenage "
    "Gohan sprints through dust and airborne stones in the midground."
)

NEGATIVE = (
    "tail, stinger, tentacle, cable, snake shape, rear appendage, visible pelvis, visible "
    "hips, visible lower back, visible rear silhouette, visible wing roots, contact, "
    "crushed head, tear, liquid, blood, gore, lightning, duplicate character, anime, "
    "cel shading, game render, text, logo, watermark"
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_take(now: str) -> dict:
    return {
        "id": PILOT_ID,
        "slug": "V5_P02_PLANO_FECHADO_SEM_TRASEIRA_APROVAR_ANCORA",
        "title": "V5 P02 — PLANO FECHADO SEM TRASEIRA — APROVAR ÂNCORA",
        "sequence": 1.6,
        "role": "v5_reframed_anchor_pending_human_review",
        "status": "PLANNED",
        "maestro_status": "PLANNED",
        "render_authorized": False,
        "target_duration_seconds": 5.166667,
        "native_duration_seconds": 5.166667,
        "duration_seconds": 5.166667,
        "frames": 124,
        "objective": (
            "Executar impacto e reacao sem permitir que o motor reconstrua a traseira de Cell."
        ),
        "animation_prompt": PROMPT,
        "base_image": {"status": "waiting_anchor_generation", "file": ""},
        "video_generation": {
            "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot",
            "profile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "fps": 24,
            "frames": 124,
            "steps": 20,
            "guidance": 1.0,
            "start_end_frame_enabled": False,
            "require_approved_start_frame": True,
            "require_approved_end_frame": False,
            "render_authorized": False,
            "visual_only_pass": True,
            "native_audio_authorized": False,
            "prompt": PROMPT,
        },
        "take_mode": "action",
        "direction_contract": {
            "story_purpose": "Mudar a composicao para eliminar a causa visual da cauda.",
            "dramatic_question": "Gohan atravessa a consequencia do impacto e volta ao ataque?",
            "story_change": "Bota descendente vira impacto, fissura, reacao e novo avanco de Gohan.",
            "reaction": "Gohan planta contra a onda e imediatamente volta a avancar.",
            "cut_motivation": "Cortar no meio do avanco de Gohan.",
            "duration_reason": "A janela concentra impacto, perseguicao da fissura e reacao sem pausa.",
            "distinct_story_events": 3,
            "performance_only": False,
            "beats": [
                {"start": 0.0, "end": 1.55, "action": "Impacto e camera expulsa lateralmente."},
                {"start": 1.55, "end": 3.62, "action": "Pernas saem; camera persegue a fissura e passa Gohan."},
                {"start": 3.62, "end": 5.166667, "action": "Primeiro arco e novo avanco atraves do corte."},
            ],
            "direction_status": "approved_for_end_frame_generation",
        },
        "shot_contract": {
            "story_purpose": "Eliminar a causa visual da cauda e preservar a acao continua.",
            "dramatic_question": "Gohan atravessa a consequencia do impacto e volta ao ataque?",
            "story_change": "Bota descendente vira impacto, fissura, reacao e novo avanco de Gohan.",
            "reaction": "Gohan planta contra a onda e imediatamente volta a avancar.",
            "cut_motivation": "Cortar no meio do avanco de Gohan.",
            "duration_reason": "5,166667 s para impacto, camera pela fissura e reacao ativa.",
            "distinct_story_events": 3,
            "motion_beats": {
                "start": "Impacto unico e camera expulsa lateralmente.",
                "middle": "Pernas saem do quadro; camera corre pela fissura e passa Gohan.",
                "end": "Primeiro arco e Gohan avanca atraves da camera movel.",
            },
            "environment_state_before": "Cabeca mecanica intacta; bota descendente; poeira em voo.",
            "environment_state_after": "Restos mecanicos; fissura ativa; primeira ruptura de energia.",
            "environment_damage": "Cabeca mecanica destruida e fissura persistente na arena.",
            "escalation_level": 2,
            "scale_evidence": {
                "foreground": "bota, cabeca, fragmentos e fissura junto da lente",
                "midground": "Gohan cruza distancia real",
                "background": "paredes e nuvens mudam lentamente de perspectiva",
            },
            "negative_rules": [
                "no visible Cell pelvis, hips, back, rear silhouette or wing roots",
                "no tail, stinger, cable, tentacle or rear appendage",
                "no living photo, static hold, crossfade, freeze or reset",
                "no blood, gore, tear, liquid, duplicate, anime, game render or text",
            ],
            "transition_motion_contract": {
                "camera_evidence": {
                    "movement": "Impact knocks the low camera left; it races along the crack and passes Gohan.",
                    "physical_translation": True,
                    "perspective_change": "Boot, fragments, Gohan and ruins continuously reorder and change scale.",
                },
                "real_depth": {
                    "foreground": "boot, head, fragments, stones and crack",
                    "midground": "Gohan crosses the camera path",
                    "background": "arena walls and storm clouds",
                    "differential_motion": "fragments fastest, Gohan medium, distant ruins slowest",
                    "occlusion_or_scale_change": "camera passes foreground debris and Gohan",
                },
                "internal_action": {
                    "primary_event": "One impact becomes one crack chase and one renewed Gohan launch.",
                    "independent_elements": [
                        "Gohan body, hair and clothes cross the camera path",
                        "fragments, dust, crack and lightning retain separate vectors",
                    ],
                    "camera_independent": True,
                },
                "progression": {
                    "start": "active downstroke completes one impact",
                    "middle": "impact propagates into a crack chase while cropped legs exit",
                    "end": "Gohan converts anger into a renewed forward launch",
                    "end_state_change": "intact mechanical head becomes debris and pursuit becomes attack",
                    "exit_or_cut": "mid-launch directional handoff",
                },
                "continuity": {
                    "editorial_method": "single_continuous_take",
                    "continuous_action": True,
                    "motion_handoff": True,
                    "action_occupies_full_duration": True,
                    "entry_motion": "downstroke, sprint, debris and low camera on frame one",
                    "exit_motion": "Gohan, lightning, debris and camera retain velocity",
                    "interval_motion": {
                        "early_0_30": "impact and lateral camera displacement",
                        "middle_30_70": "ground-level crack chase away from the cropped legs",
                        "late_70_100": "first lightning and Gohan launch through the moving camera path",
                    },
                    "crossfade_frames": 0,
                    "freeze_frames": 0,
                    "static_hold_frames": 0,
                },
            },
        },
        "qc": {
            "status": "waiting_derived_anchor_v5_p02_reframed",
            "human_visual_approval": "pending",
            "transition_motion_gate": {
                "status": "pending_anchor_then_video",
                "evident_camera": False,
                "real_depth": False,
                "internal_action": False,
                "clear_progression": False,
                "continuous_action": False,
                "motion_across_all_intervals": False,
                "no_crossfade": False,
                "no_freeze": False,
                "no_static_tail": False,
                "no_reset": False,
                "evidence": "blocked until owner approves the reframed anchor",
            },
        },
        "audio_direction": {
            "strategy": "model_independent_foley_after_picture_lock",
            "status": "BLOCKED_UNTIL_PICTURE_LOCK",
            "dialogue_generation_authorized": False,
            "human_listening_required": False,
            "delivery_required": False,
        },
        "video": {"status": "not_generated"},
        "maestro_notes": (
            "Nova rota apos duas falhas P01. Aprovar somente a ancora; nenhum video P02 "
            "sera gerado antes da decisao humana."
        ),
        "maestro_created_at": now,
        "maestro_updated_at": now,
    }


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    image_hash = digest(SOURCE)
    now = utc_now()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, MANIFEST_PATH):
        target = ARCHIVE / source.name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)

    queue = read_json(QUEUE_PATH)
    p01 = next(item for item in queue["takes"] if str(item.get("id")) == "P01")
    requests = p01.get("maestro_director_requests")
    latest = requests[-1] if isinstance(requests, list) and requests else {}
    if not (
        str(p01.get("maestro_status") or "").upper() == "REJECTED"
        and str(latest.get("reason") or "") == REJECTION_REASON
    ):
        patch_take(
            PROJECTS,
            PROJECT_ID,
            "P01",
            {
                "status": "REJECTED",
                "notes": (
                    "P01 e P01C1 reprovados e preservados. Rota prompt-only encerrada; "
                    "substituicao passa ao P02 com enquadramento fechado."
                ),
                "directorRequest": {
                    "category": "PROGRESSION",
                    "reason": REJECTION_REASON,
                    "renderInstruction": REJECTION_INSTRUCTION,
                },
            },
        )

    queue = read_json(QUEUE_PATH)
    p01 = next(item for item in queue["takes"] if str(item.get("id")) == "P01")
    generation_01 = p01.get("video_generation") if isinstance(p01.get("video_generation"), dict) else {}
    p01["render_authorized"] = False
    generation_01["render_authorized"] = False
    p01["video_generation"] = generation_01
    p01["qc"]["status"] = "route_closed_after_single_directed_correction"
    p01["qc"]["route_decision"] = "CHANGE_ANCHOR_COMPOSITION_AND_CONTROL"
    p01["maestro_updated_at"] = now

    by_id = {str(item.get("id")): item for item in queue["takes"] if isinstance(item, dict)}
    if PILOT_ID not in by_id:
        insert_at = next(
            (index + 1 for index, item in enumerate(queue["takes"]) if str(item.get("id")) == "P01"),
            len(queue["takes"]),
        )
        queue["takes"].insert(insert_at, make_take(now))
    p02 = next(item for item in queue["takes"] if str(item.get("id")) == PILOT_ID)
    if (p02.get("video") or {}).get("output_active"):
        raise RuntimeError("P02 ja possui video; registro interrompido.")
    queue["status"] = "V5_P02_REFRAMED_ANCHOR_PENDING_OWNER_APPROVAL"
    queue["render_authorized"] = False
    queue["story_batch_policy"] = {
        "enabled": True,
        "version": "gohan_v5_p02_reframed_anchor_v1",
        "batch_size": 1,
        "render_order": [PILOT_ID],
        "strict_contiguous": True,
        "require_all_base_images_ready": True,
        "fill_eligible_across_batches": False,
        "require_full_batch": True,
        "allow_incomplete_correction_batch": False,
        "control_surface": "P02_anchor_approval_then_QC",
    }
    queue["updated_at"] = now
    _atomic_json_write(QUEUE_PATH, queue)

    queue = read_json(QUEUE_PATH)
    p02 = next(item for item in queue["takes"] if str(item.get("id")) == PILOT_ID)
    base = p02.get("base_image") if isinstance(p02.get("base_image"), dict) else {}
    requests = p02.get("maestro_director_requests")
    latest = requests[-1] if isinstance(requests, list) and requests else None
    if not base.get("candidate_request_id"):
        if latest is None or str(latest.get("status") or "").upper() not in {"PENDING", "IN_PROGRESS", "DELIVERED"}:
            patch_take(
                PROJECTS,
                PROJECT_ID,
                PILOT_ID,
                {
                    "directorRequest": {
                        "category": "ANCHOR",
                        "reason": (
                            "Registrar a ancora P02 reenquadrada que exclui fisicamente quadril, "
                            "traseira e raiz das asas para impedir a cauda no video."
                        ),
                        "renderInstruction": (
                            "Manter apenas pernas/bota cortadas pelas bordas, cabeca mecanica intacta, "
                            "Gohan correndo e vetores de poeira; aguardar aprovacao humana."
                        ),
                    }
                },
            )
        queue = read_json(QUEUE_PATH)
        p02 = next(item for item in queue["takes"] if str(item.get("id")) == PILOT_ID)
        latest = p02["maestro_director_requests"][-1]
        base = p02.get("base_image") if isinstance(p02.get("base_image"), dict) else {}

    request_id = str(base.get("candidate_request_id") or (latest or {}).get("id") or "")
    registered = Path(str(base.get("file") or ""))
    if base.get("candidate_request_id"):
        if not registered.is_file() or digest(registered) != image_hash:
            raise RuntimeError("P02 ja possui outro candidato registrado.")
        result = next(
            item for item in list_takes(PROJECTS, PROJECT_ID)["data"]
            if str(item.get("takeId")) == PILOT_ID
        )
    else:
        result = register_anchor_candidate(
            PROJECTS,
            PROJECT_ID,
            PILOT_ID,
            request_id=request_id,
            image_bytes=SOURCE.read_bytes(),
            original_filename=SOURCE.name,
            metadata={
                "prompt": ANCHOR_PROMPT,
                "model": "OpenAI built-in image generation",
                "negative": NEGATIVE,
                "sourceOutput": str(SOURCE.resolve()),
                "sourceGeneratedAt": now,
                "sourceSha256": image_hash,
                "generator": "OpenAI built-in image generation",
                "workflow": "identity_preserving_reframe_then_exact_1536x864_normalization",
                "objective": "Excluir fisicamente a anatomia traseira que o H3 vinha reconstruindo.",
                "requiredObjects": {
                    "anchorSide": "start",
                    "characters": [
                        "ordinary Super Saiyan teenage Gohan",
                        "cropped bio-android legs and one descending boot",
                        "Android 16 intact mechanical head",
                    ],
                    "excludedFromFrame": [
                        "bio-android pelvis", "hips", "back", "rear silhouette", "wing roots"
                    ],
                    "forbidden": ["tail", "stinger", "tentacle", "cable", "contact", "gore"],
                },
            },
        )

    manifest = read_json(MANIFEST_PATH)
    batches = manifest.setdefault("anchor_candidate_batches", {})
    if not isinstance(batches, dict):
        batches = {}
        manifest["anchor_candidate_batches"] = batches
    batches["v5_p02_reframed"] = {
        "status": "PENDING_HUMAN_APPROVAL_IN_MAESTRO",
        "take_id": PILOT_ID,
        "request_id": request_id,
        "source": str(SOURCE.resolve()),
        "sha256": image_hash.upper(),
        "width": 1536,
        "height": 864,
        "video_generation_authorized": False,
        "replaces_failed_route": ["P01", "P01C1"],
    }
    manifest["status"] = "V5_P02_REFRAMED_ANCHOR_PENDING_OWNER_APPROVAL"
    manifest["render_authorized"] = False
    manifest["updated_at"] = utc_now()
    _atomic_json_write(MANIFEST_PATH, manifest)
    print(json.dumps({
        "ok": True,
        "closedRoute": ["P01", "P01C1"],
        "pilotTake": PILOT_ID,
        "status": result.get("status"),
        "qcStatus": result.get("qcStatus"),
        "canGenerate": result.get("canGenerate"),
        "anchorCandidate": result.get("anchorCandidate"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
