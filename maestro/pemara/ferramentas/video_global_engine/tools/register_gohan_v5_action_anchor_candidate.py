"""Reject the failed V5 Take 01B and register one action-first pilot anchor.

The rejected videos remain in the original take history.  The new image is
registered on one clearly named PLANNED pilot take so Maestro can apply its
normal human anchor-review gate before any further GPU generation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
PROJECTS = BASE / "ferramentas" / "video_global_engine" / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
SOURCE = (
    PROJECT
    / "base_images"
    / "v5_boundary_cell_boot_mid_downstroke_candidate_v1_1536x864.png"
)
PILOT_ID = "P01"

sys.path.insert(0, str(STUDIO))

from video_projects import (  # noqa: E402
    _atomic_json_write,
    list_takes,
    patch_take,
    register_anchor_candidate,
    utc_now,
)


REJECTION_REASON = (
    "O V5 Take 01B foi reprovado no controle interno: apesar de nao congelar "
    "formalmente, Cell apenas caminha, a bota nao entra na descida prometida e "
    "o plano conserva aparencia de fotografia viva com direcao fraca."
)

REJECTION_INSTRUCTION = (
    "Preservar integralmente o MP4 01B como rollback e encerrar esta rota. "
    "Nao repetir o mesmo start frame. A substituicao deve partir de uma ancora "
    "ja comprometida com a acao: Cell em downstroke, Gohan correndo, camera baixa "
    "e detritos com vetor, sem cauda e antes do contato."
)

ANIMATION_PROMPT = (
    "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION ACTION TAKE "
    "FROM THE EXACT APPROVED START FRAME. Motion continues on frame one: the "
    "same completely tailless Perfect Cell boot is already descending, the same "
    "ordinary Super Saiyan teenage Gohan is already sprinting, loose stones and "
    "dust keep their established vectors, and a low physical camera keeps driving "
    "forward. The boot completes exactly one mechanical impact on Android 16's "
    "purely mechanical head; metal, ceramic and circuits burst sideways without "
    "blood or organic matter. The camera physically overtakes the expanding floor "
    "crack while Cell recoils from the same impact and Gohan plants against the "
    "shockwave. End during an expanding gold pressure wave and the first blue-white "
    "electrical arc, with Gohan, Cell, debris, dust and camera all retaining velocity. "
    "Cell remains silent with sealed lips. FORBIDDEN: living photo, static hold, "
    "freeze tail, boot reset, repeated stomp, early completed pose, Cell tail or rear "
    "appendage, tear or liquid effect, blood, gore, duplicate character, anime, game "
    "render, crossfade, zoom-only camera, text, logo or watermark."
)

ANCHOR_PROMPT = (
    "Photorealistic live-action Dragon Ball action anchor: exact tailless Perfect "
    "Cell is physically committed to a single boot downstroke above Android 16's "
    "intact purely mechanical head; ordinary Super Saiyan teenage Gohan runs toward "
    "them; low ground camera, airborne stones and dust establish continuing velocity; "
    "cut before contact, no gore."
)

NEGATIVE = (
    "Cell tail, rear appendage, static pose, raised boot hold, stomp contact, blood, "
    "gore, organic injury, tear, liquid, SSJ2 lightning, duplicate character, extra "
    "fighter, anime, cel shading, manga, cartoon, game render, text, logo, watermark"
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pilot_take(now: str) -> dict:
    return {
        "id": PILOT_ID,
        "slug": "V5_ACAO_CONTINUA_DESCIDA_IMPACTO_APROVAR_ANCORA",
        "title": "V5 PILOTO P01 — AÇÃO CONTÍNUA — APROVAR ÂNCORA",
        "sequence": 1.5,
        "role": "v5_action_first_pilot_pending_anchor_review",
        "status": "PLANNED",
        "maestro_status": "PLANNED",
        "render_authorized": False,
        "target_duration_seconds": 5.166667,
        "native_duration_seconds": 5.166667,
        "objective": (
            "Provar descida, impacto e reacao em movimento continuo antes de "
            "reconstruir os demais takes."
        ),
        "animation_prompt": ANIMATION_PROMPT,
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
            "prompt": ANIMATION_PROMPT,
        },
        "take_mode": "action",
        "shot_contract": {
            "story_purpose": (
                "Substituir a rota de fotografia viva por uma entrada ja dentro da acao."
            ),
            "dramatic_question": (
                "Gohan alcanca Android 16 antes de a unica descida terminar?"
            ),
            "story_change": (
                "Bota descendente e perseguicao ativa viram um impacto mecanico e "
                "a primeira ruptura energetica de Gohan."
            ),
            "reaction": "Gohan planta contra a onda de choque; Cell recua do proprio impacto.",
            "cut_motivation": (
                "Cortar durante aura, raio, detritos e camera ainda em deslocamento."
            ),
            "duration_reason": (
                "A janela curta concentra uma descida, um impacto e uma reacao sem pausa."
            ),
            "distinct_story_events": 3,
            "motion_beats": {
                "start": "Downstroke, corrida, detritos e camera continuam no primeiro quadro.",
                "middle": "Um impacto mecanico gera fragmentos, onda e fissura em propagacao.",
                "end": "Gohan planta; aura e primeiro arco crescem enquanto todos mantem velocidade.",
            },
            "environment_state_before": (
                "Cabeca mecanica intacta; bota no downstroke; poeira e pedras ja em voo."
            ),
            "environment_state_after": (
                "Restos mecanicos dispersos; fissura ativa; aura inicial em expansao."
            ),
            "environment_damage": (
                "Cabeca mecanica destruida e uma nova fissura persistente na arena."
            ),
            "escalation_level": 2,
            "scale_evidence": {
                "foreground": "bota, cabeca mecanica, pedras e fissura cruzam junto da lente",
                "midground": "Cell transfere impacto e Gohan corre/planta",
                "background": "paredes e nuvens mudam de perspectiva mais lentamente",
            },
            "negative_rules": [
                "no Cell tail or rear appendage",
                "no living photo, static hold, crossfade, freeze frame or zoom-only camera",
                "no repeated stomp, pose reset or return to idle",
                "no blood, gore or organic Android 16 injury",
                "no duplicate fighter, anime drawing, game render, text, logo or watermark",
            ],
            "transition_motion_contract": {
                "camera_evidence": {
                    "movement": (
                        "Low physical drive under the downstroke becomes a floor-level crack chase."
                    ),
                    "physical_translation": True,
                    "perspective_change": (
                        "Boot, head, fighters and ruins continuously change overlap and scale."
                    ),
                },
                "real_depth": {
                    "foreground": "boot, mechanical head, stones, dust and crack",
                    "midground": "tailless Cell impact/recoil and running Gohan",
                    "background": "ruined arena and storm clouds",
                    "differential_motion": (
                        "foreground debris is fastest, bodies are medium, distant ruins are slowest"
                    ),
                    "occlusion_or_scale_change": (
                        "physical camera travel changes scale without blackout or flat parallax"
                    ),
                },
                "internal_action": {
                    "primary_event": (
                        "One irreversible boot descent becomes one mechanical impact and one reaction."
                    ),
                    "independent_elements": [
                        "Gohan body, hair and clothing keep separate inertia",
                        "Cell armor, debris, dust and lightning move independently",
                    ],
                    "camera_independent": True,
                },
                "progression": {
                    "start": "active downstroke and pursuit",
                    "middle": "mechanical impact, shockwave and racing crack",
                    "end": "Gohan reaction, expanding aura and first lightning",
                    "end_state_change": (
                        "intact mechanical head becomes debris and contained anger becomes rupture"
                    ),
                    "exit_or_cut": "hard action handoff while every major layer still moves",
                },
                "continuity": {
                    "editorial_method": "single_continuous_take",
                    "continuous_action": True,
                    "motion_handoff": True,
                    "action_occupies_full_duration": True,
                    "entry_motion": "downstroke, sprint, debris and physical camera on frame one",
                    "exit_motion": "aura, lightning, Cell, debris and camera retain velocity",
                    "interval_motion": {
                        "early_0_30": "downstroke and pursuit continue without setup hold",
                        "middle_30_70": "impact propagates through fragments, shockwave and crack",
                        "late_70_100": "reaction expands without completed pose or static tail",
                    },
                    "crossfade_frames": 0,
                    "freeze_frames": 0,
                    "static_hold_frames": 0,
                },
            },
        },
        "qc": {
            "status": "waiting_derived_anchor_v5_action_first",
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
                "evidence": "blocked until owner approves the action-first anchor",
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
            "Piloto unico da rota V5. Aprovar somente a ancora nesta etapa; "
            "nenhum video sera gerado antes da decisao humana."
        ),
        "maestro_created_at": now,
        "maestro_updated_at": now,
    }


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source_hash = sha256(SOURCE)
    now = utc_now()

    backup = PROJECT / "archive" / "before_v5_action_anchor_registration"
    backup.mkdir(parents=True, exist_ok=True)
    for path in (QUEUE_PATH, MANIFEST_PATH):
        target = backup / path.name
        if path.is_file() and not target.exists():
            shutil.copy2(path, target)

    queue = read_json(QUEUE_PATH)
    take_01 = next(
        item for item in queue.get("takes", [])
        if isinstance(item, dict) and str(item.get("id")) == "01"
    )
    requests_01 = take_01.get("maestro_director_requests")
    latest_01 = (
        requests_01[-1]
        if isinstance(requests_01, list) and requests_01 and isinstance(requests_01[-1], dict)
        else {}
    )
    if not (
        str(take_01.get("maestro_status") or "").upper() == "REJECTED"
        and str(latest_01.get("reason") or "") == REJECTION_REASON
    ):
        patch_take(
            PROJECTS,
            PROJECT_ID,
            "01",
            {
                "status": "REJECTED",
                "notes": (
                    "01B reprovado no QC interno e preservado no historico. "
                    "A rota start-only foi encerrada; substituicao segue no piloto P01."
                ),
                "directorRequest": {
                    "category": "PROGRESSION",
                    "reason": REJECTION_REASON,
                    "renderInstruction": REJECTION_INSTRUCTION,
                },
            },
        )

    # This route is closed.  Keep its artifacts visible as rollback, but do not
    # let an old READY authorization accidentally enqueue another 01B render.
    queue = read_json(QUEUE_PATH)
    take_01 = next(
        item for item in queue.get("takes", [])
        if isinstance(item, dict) and str(item.get("id")) == "01"
    )
    generation_01 = (
        take_01.get("video_generation")
        if isinstance(take_01.get("video_generation"), dict)
        else {}
    )
    if take_01.get("render_authorized") or generation_01.get("render_authorized"):
        take_01["render_authorized"] = False
        generation_01["render_authorized"] = False
        take_01["video_generation"] = generation_01
        take_01["maestro_updated_at"] = utc_now()
        queue["updated_at"] = utc_now()
        _atomic_json_write(QUEUE_PATH, queue)

    queue = read_json(QUEUE_PATH)
    by_id = {
        str(item.get("id")): item
        for item in queue.get("takes", [])
        if isinstance(item, dict)
    }
    if PILOT_ID not in by_id:
        new_take = pilot_take(now)
        insert_at = next(
            (
                index + 1
                for index, item in enumerate(queue["takes"])
                if isinstance(item, dict) and str(item.get("id")) == "01"
            ),
            len(queue["takes"]),
        )
        queue["takes"].insert(insert_at, new_take)
        queue["status"] = "V5_ACTION_ANCHOR_PENDING_OWNER_APPROVAL"
        queue["updated_at"] = now
        _atomic_json_write(QUEUE_PATH, queue)
    else:
        existing = by_id[PILOT_ID]
        output = (
            existing.get("video", {}).get("output_active")
            if isinstance(existing.get("video"), dict)
            else ""
        )
        if output:
            raise RuntimeError("P01 ja possui video; registro automatico interrompido.")

    queue = read_json(QUEUE_PATH)
    pilot = next(item for item in queue["takes"] if str(item.get("id")) == PILOT_ID)
    requests = pilot.get("maestro_director_requests")
    latest = (
        requests[-1]
        if isinstance(requests, list) and requests and isinstance(requests[-1], dict)
        else None
    )
    candidate = pilot.get("base_image") if isinstance(pilot.get("base_image"), dict) else {}
    if not candidate.get("candidate_request_id"):
        if latest is None or str(latest.get("status") or "").upper() not in {
            "PENDING", "IN_PROGRESS", "DELIVERED"
        }:
            patch_take(
                PROJECTS,
                PROJECT_ID,
                PILOT_ID,
                {
                    "directorRequest": {
                        "category": "ANCHOR",
                        "reason": (
                            "Registrar a nova ancora V5 ja dentro da acao para substituir "
                            "a rota estatica dos Takes 01A e 01B."
                        ),
                        "renderInstruction": (
                            "Usar exatamente Cell sem cauda em downstroke, Gohan correndo, "
                            "cabeca mecanica intacta, camera baixa e detritos em movimento; "
                            "parar antes do contato e aguardar aprovacao humana."
                        ),
                    }
                },
            )
        queue = read_json(QUEUE_PATH)
        pilot = next(item for item in queue["takes"] if str(item.get("id")) == PILOT_ID)
        requests = pilot.get("maestro_director_requests")
        latest = requests[-1]

    request_id = str(
        candidate.get("candidate_request_id")
        or (latest.get("id") if isinstance(latest, dict) else "")
        or ""
    )
    metadata = {
            "prompt": ANCHOR_PROMPT,
            "model": "OpenAI built-in image generation",
            "negative": NEGATIVE,
            "sourceOutput": str(SOURCE.resolve()),
            "sourceGeneratedAt": now,
            "sourceSha256": source_hash,
            "generator": "OpenAI built-in image generation",
            "workflow": "identity_preserving_action_anchor_edit_then_exact_1536x864_normalization",
            "objective": (
                "Comecar o novo piloto dentro do movimento para impedir fotografia viva e "
                "construir um handoff fisico real."
            ),
            "requiredObjects": {
                "anchorSide": "start",
                "characters": [
                    "ordinary Super Saiyan teenage Gohan",
                    "completely tailless Perfect Cell",
                    "Android 16 intact mechanical head",
                ],
                "action": "Cell single boot already descending before contact",
                "camera": "low physical ground camera with debris velocity",
                "forbidden": ["Cell tail", "contact", "gore", "static pose"],
            },
        }
    registered_file = Path(str(candidate.get("file") or ""))
    if candidate.get("candidate_request_id"):
        if not registered_file.is_file() or sha256(registered_file) != source_hash:
            raise RuntimeError("P01 ja possui outro candidato registrado.")
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
            metadata=metadata,
        )

    manifest = read_json(MANIFEST_PATH)
    batches = manifest.setdefault("anchor_candidate_batches", {})
    if not isinstance(batches, dict):
        batches = {}
        manifest["anchor_candidate_batches"] = batches
    batches["v5_action_first_pilot"] = {
        "status": "PENDING_HUMAN_APPROVAL_IN_MAESTRO",
        "updated_at": utc_now(),
        "take_id": PILOT_ID,
        "request_id": request_id,
        "source": str(SOURCE.resolve()),
        "sha256": source_hash.upper(),
        "width": 1536,
        "height": 864,
        "video_generation_authorized": False,
        "failed_routes_preserved": ["01A", "01B"],
    }
    manifest["updated_at"] = utc_now()
    _atomic_json_write(MANIFEST_PATH, manifest)

    print(json.dumps({
        "rejectedTake": "01B",
        "rejectedOutputPreserved": True,
        "pilotTake": PILOT_ID,
        "pilotTitle": result.get("title"),
        "pilotStatus": result.get("status"),
        "canGenerate": result.get("canGenerate"),
        "qcStatus": result.get("qcStatus"),
        "anchorCandidate": result.get("anchorCandidate"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
