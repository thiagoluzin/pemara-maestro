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

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
BASE_IMAGES = PROJECT / "base_images"
START_07 = BASE_IMAGES / "take06_cell_lancado_pela_arena_anchor_bdd4b9b79e35.png"
END_07 = BASE_IMAGES / "take07_gohan_pressiona_cell_anchor_v1.png"
END_08 = BASE_IMAGES / "take08_kamehameha_cell_montanha_anchor_v1.png"


PROMPT_07_ANCHOR = (
    "Same Gohan SSJ2 and tailless Perfect Cell in photoreal live action. Gohan drives one compact body punch into "
    "Cell's compressed guard while Cell skids backward; low physical orbit, deep rubble parallax and active debris."
)
PROMPT_08_ANCHOR = (
    "Same Gohan SSJ2 fires one enormous blue-white Kamehameha across deep space, visibly pinning tailless Perfect "
    "Cell into a newly fracturing mountain crater while beam, rocks and dust continue moving."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_contract(path: Path, status: str, metadata: Path) -> dict:
    return {
        "file": path.as_posix(),
        "status": status,
        "metadata": metadata.as_posix(),
        "source_sha256": sha256(path),
    }


def write_anchor_metadata(path: Path, prompt: str, role: str, now: str) -> Path:
    metadata = path.with_suffix(".json")
    payload = {
        "schema_version": "maestro_imagegen_anchor_v1",
        "project_id": PROJECT_ID,
        "role": role,
        "file": path.name,
        "sha256": sha256(path),
        "width": 1672,
        "height": 941,
        "mode": "RGB",
        "provider": "openai_builtin_imagegen",
        "prompt": prompt,
        "status": "pending_human_review",
        "created_at": now,
        "human_review_required": True,
    }
    _atomic_json_write(metadata, payload)
    return metadata


def anchor_request(path: Path, metadata: Path, prompt: str, side: str, now: str) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "status": "DELIVERED",
        "category": "ANCHOR",
        "reason": prompt,
        "created_at": now,
        "updated_at": now,
        "anchor_side": side,
        "delivered_at": now,
        "candidate_file": path.name,
        "candidate_metadata_file": metadata.name,
        "candidate_sha256": sha256(path),
    }


def reset_generated_state(take: dict, now: str) -> None:
    take.update({
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_last_job_id": "",
        "maestro_last_error": "",
        "maestro_last_result": None,
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana das novas ancoras 07 e 08.",
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {
            "status": "anchor_pending_human_review",
            "human_visual_approval": "pending",
            "transition_motion_gate": {"status": "contract_ready_anchor_pending"},
            "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK",
        },
        "audio_direction": {
            "strategy": "model_independent_foley_after_picture_lock",
            "status": "BLOCKED_UNTIL_PICTURE_LOCK",
            "dialogue_generation_authorized": False,
            "human_listening_required": False,
            "delivery_required": False,
        },
    })


def main() -> None:
    for image in (START_07, END_07, END_08):
        if not image.is_file():
            raise FileNotFoundError(image)

    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    project_manifest_path = PROJECT / "project_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(item.get("id") or ""): item for item in takes if isinstance(item, dict)}
    if "07" in by_id or "08" in by_id:
        print(json.dumps({"ok": True, "existing": [key for key in ("07", "08") if key in by_id]}, indent=2))
        return
    source = by_id.get("06R1")
    if not isinstance(source, dict) or str(source.get("maestro_status") or "").upper() != "APPROVED":
        raise ValueError("06R1 precisa estar APPROVED antes da extensao 07/08.")

    now = utc_now()
    end07_meta = write_anchor_metadata(END_07, PROMPT_07_ANCHOR, "take07_end_take08_start", now)
    end08_meta = write_anchor_metadata(END_08, PROMPT_08_ANCHOR, "take08_end", now)
    start07_meta = START_07.with_suffix(".json")
    if not start07_meta.is_file():
        raise FileNotFoundError(start07_meta)

    take07 = deepcopy(source)
    reset_generated_state(take07, now)
    take07.update({
        "id": "07",
        "sequence": 7,
        "slug": "gohan_cell_trocacao_pressao",
        "name": "gohan_cell_trocacao_pressao",
        "title": "Gohan troca golpes e pressiona Cell",
        "objective": "Continuar a perseguicao em trocacao legivel e terminar com Gohan forçando Cell a recuar.",
        "target_duration_seconds": 10.0,
        "native_duration_seconds": 10.083333,
        "editorial_use_seconds": 10.0,
        "status": "WAITING_APPROVED_ANCHORS",
        "maestro_notes": "Nova extensao solicitada pelo proprietario; ancora final pendente de aprovacao humana.",
        "animation_prompt": (
            "ONE UNBROKEN 10.083333-SECOND PHOTOREALISTIC LIVE-ACTION CLOSE-COMBAT TAKE between the exact approved "
            "first frame and the candidate final frame. Preserve exactly one teenage Gohan SSJ2 and exactly one "
            "full-size adult green-and-black Perfect Cell as the same continuous bodies. Perfect Cell is completely "
            "TAILLESS in every frame: no tail, stinger, tentacle, cable or rear extension; only two rigid symmetrical "
            "upper-back wing plates. At 0-30%, inherit the wall-breach velocity: Cell twists into one committed counter "
            "right while Gohan closes real distance, parries it and both descend through moving debris. At 30-70%, Cell "
            "adds one knee; Gohan blocks, answers with one body punch and one separate short straight, each with readable "
            "anticipation, contact and consequence. At 70-100%, Gohan turns the exchange decisively with one compact "
            "driving blow into Cell's guard; Cell skids backward continuously while Gohan advances without resetting. "
            "Camera performs a physical descending orbit, crosses behind one foreground slab, changes height at the body "
            "punch and arcs around the final pressure with strong differential parallax. Reach the final composition only "
            "in the last 0.10 seconds and cut while both bodies, camera, hair, cloth, armor, lightning, dust and rubble "
            "still carry velocity. FORBIDDEN: static tail, early final pose, reset, repeated loop, teleportation, extra "
            "fighter, duplicate body, extra limb, body substitution, tail, Cell Junior, energy beam, Kamehameha, anime "
            "drawing, cel shading, illustration, game render, plastic CGI skin, text, logo, watermark, blood or gore."
        ),
    })
    take07["base_image"] = image_contract(START_07, "approved_for_video", start07_meta)
    take07["end_image"] = image_contract(END_07, "candidate_pending_owner_review", end07_meta)
    request07 = anchor_request(END_07, end07_meta, PROMPT_07_ANCHOR, "end", now)
    take07["maestro_director_requests"] = [request07]
    take07["end_anchor_candidate"] = {
        "status": "candidate_pending_owner_review",
        "file": END_07.as_posix(),
        "metadata": end07_meta.as_posix(),
        "model": "OpenAI built-in image generation",
        "prompt": PROMPT_07_ANCHOR,
        "candidate_request_id": request07["id"],
        "image_sha256": sha256(END_07),
        "delivered_at": now,
    }
    take07["shot_contract"] = {
        "story_purpose": "Mostrar que Cell ainda consegue trocar golpes, mas Gohan passa a controlar cada resposta.",
        "dramatic_question": "Cell consegue recuperar iniciativa antes que Gohan feche sua guarda?",
        "story_change": "Perseguicao aerea apos a parede -> Cell no chao recuando sob pressao direta de Gohan.",
        "reaction": "A agressividade de Cell vira defesa tensa; Gohan percebe a abertura e avanca.",
        "cut_motivation": "Cortar no instante em que a guarda comprimida de Cell abre caminho para o golpe de lancamento.",
        "duration_reason": "Dez segundos comportam contra-ataque, bloqueio, duas respostas distintas e inversao definitiva da vantagem.",
        "distinct_story_events": 4,
        "motion_beats": {
            "start": "Cell contra-ataca durante a queda e Gohan intercepta.",
            "middle": "Joelho, bloqueio, golpe no corpo e direto curto mudam a vantagem.",
            "end": "Gohan comprime a guarda; Cell recua em velocidade para o corte.",
        },
        "visual_references": {
            "start_frame_file": START_07.as_posix(),
            "start_frame_approved": True,
            "start_frame_sha256": sha256(START_07),
            "end_frame_file": END_07.as_posix(),
            "end_frame_approved": False,
            "end_frame_sha256": sha256(END_07),
        },
        "transition_motion_contract": {
            "camera_evidence": {"physical_translation": True, "movement": "descending orbit with height and axis change"},
            "real_depth": {"differential_motion": "foreground slabs, fighters and ruins move at distinct speeds"},
            "internal_action": {"primary_event": "exchange reverses into Gohan pressure", "camera_independent": True},
            "progression": {"start": "Cell counter", "middle": "blocked exchange", "end": "Cell forced backward"},
            "continuity": {"continuous_action": True, "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0},
        },
    }

    take08 = deepcopy(take07)
    reset_generated_state(take08, now)
    take08.update({
        "id": "08",
        "sequence": 8,
        "slug": "gohan_kamehameha_cell_montanha",
        "name": "gohan_kamehameha_cell_montanha",
        "title": "Gohan lança Cell e dispara o Kamehameha",
        "objective": "Continuar a pressão, lançar Cell por longa distância e esmagá-lo contra a montanha com um Kamehameha.",
        "status": "WAITING_APPROVED_ANCHORS",
        "maestro_notes": "Nova extensao solicitada pelo proprietario; ancoras inicial e final pendentes de aprovacao humana.",
        "animation_prompt": (
            "ONE UNBROKEN 10.083333-SECOND PHOTOREALISTIC LIVE-ACTION FINISHING TAKE between the exact candidate first "
            "and last frames. Preserve exactly one teenage Gohan SSJ2 and exactly one full-size adult green-and-black "
            "Perfect Cell as continuous bodies. Perfect Cell is completely TAILLESS in every frame, with only two rigid "
            "symmetrical upper-back wing plates. At 0-30%, inherit Gohan's pressure: he completes one heavy body strike "
            "and one separate rising blow while Cell's guard progressively collapses. At 30-65%, Gohan plants and lands "
            "exactly one launch kick; Cell crosses a long readable distance through the ruined valley toward the mountain "
            "with weight, rotation and no teleportation while camera races laterally through foreground rocks. At 65-100%, "
            "Gohan lands, braces both feet, draws both hands together and fires exactly one enormous coherent blue-white "
            "Kamehameha after 7.4 seconds. The beam catches the same airborne Cell, drives him visibly into the mountain "
            "face and creates a new radial crater with outward-flying slabs. Cell remains recognizable and is not hidden "
            "by an energy sphere. Camera translates from close pursuit into a wide low beam corridor with strong foreground, "
            "midground and distant-mountain depth. Reach the final composition only in the last 0.10 seconds and cut while "
            "beam, Cell, mountain fracture, camera, lightning, clothing, dust and boulders still carry velocity. FORBIDDEN: "
            "static tail, early beam, early mountain impact, hold, reset, repeated strike, multiple beams, teleportation, "
            "extra fighter, duplicate body, extra limb, body substitution, tail, Cell Junior, yellow beam, Cell fully "
            "obscured, disintegration, anime drawing, cel shading, illustration, game render, plastic CGI skin, text, logo, "
            "watermark, blood or gore."
        ),
    })
    take08["base_image"] = image_contract(END_07, "candidate_pending_owner_review", end07_meta)
    take08["end_image"] = image_contract(END_08, "candidate_pending_owner_review", end08_meta)
    request08_start = anchor_request(END_07, end07_meta, PROMPT_07_ANCHOR, "start", now)
    request08_end = anchor_request(END_08, end08_meta, PROMPT_08_ANCHOR, "end", now)
    take08["maestro_director_requests"] = [request08_start, request08_end]
    take08["end_anchor_candidate"] = {
        "status": "candidate_pending_owner_review",
        "file": END_08.as_posix(),
        "metadata": end08_meta.as_posix(),
        "model": "OpenAI built-in image generation",
        "prompt": PROMPT_08_ANCHOR,
        "candidate_request_id": request08_end["id"],
        "image_sha256": sha256(END_08),
        "delivered_at": now,
    }
    take08["shot_contract"] = {
        "story_purpose": "Dar payoff fisico a superioridade de Gohan com lancamento, perseguicao e dano irreversivel na montanha.",
        "dramatic_question": "Cell consegue escapar antes que Gohan converta a abertura no Kamehameha?",
        "story_change": "Cell recua sob guarda comprimida -> Cell preso por um Kamehameha dentro de nova cratera na montanha.",
        "reaction": "Cell perde a guarda, tenta estabilizar o voo e percebe tarde demais o feixe; Gohan finca os pes e conclui o ataque.",
        "cut_motivation": "Cortar durante a fratura crescente, antes de qualquer pose de vitoria.",
        "duration_reason": "Dez segundos sao necessarios para golpe, lancamento por distancia legivel, preparacao e impacto do feixe.",
        "distinct_story_events": 5,
        "motion_beats": {
            "start": "Dois golpes pesados quebram progressivamente a guarda.",
            "middle": "Um chute lanca Cell atraves do vale ate a montanha.",
            "end": "Um Kamehameha unico captura Cell e abre a cratera enquanto tudo continua movendo.",
        },
        "environment_state_before": "Vale e ruinas acumulam os danos anteriores; montanha ainda integra.",
        "environment_state_after": "Montanha com grande cratera radial, lajes expulsas e corredor do feixe aberto.",
        "environment_damage": "Nova cratera profunda e fraturas radiais persistentes na montanha.",
        "scale_evidence": {
            "foreground": "Rochas cruzam a lente durante a perseguicao.",
            "midground": "Gohan prepara e dispara o feixe.",
            "background": "Cell percorre o vale e impacta a montanha distante.",
        },
        "visual_references": {
            "start_frame_file": END_07.as_posix(),
            "start_frame_approved": False,
            "start_frame_sha256": sha256(END_07),
            "end_frame_file": END_08.as_posix(),
            "end_frame_approved": False,
            "end_frame_sha256": sha256(END_08),
        },
        "transition_motion_contract": {
            "camera_evidence": {"physical_translation": True, "movement": "close pursuit to wide lateral beam corridor"},
            "real_depth": {"differential_motion": "foreground rocks, Gohan, airborne Cell and mountain carry distinct scale and speed"},
            "internal_action": {"primary_event": "launch followed by one mountain-driving Kamehameha", "camera_independent": True},
            "progression": {"start": "guard collapsing", "middle": "long-distance launch", "end": "mountain crater under active beam"},
            "continuity": {"continuous_action": True, "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0},
        },
    }

    takes.extend([take07, take08])
    queue.update({
        "status": "WAITING_OWNER_REVIEW_TAKES_07_08_ANCHORS",
        "render_authorized": False,
        "updated_at": now,
        "story_batch_policy": {
            "enabled": True,
            "version": "gohan_takes07_08_extension_v1",
            "batch_size": 1,
            "render_order": ["07", "08"],
            "strict_contiguous": True,
            "require_all_base_images_ready": True,
            "fill_eligible_across_batches": False,
            "require_full_batch": True,
            "allow_incomplete_correction_batch": False,
            "control_surface": "owner_requested_two_more_takes",
            "configured_at": now,
        },
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "WAITING_OWNER_REVIEW_TAKES_07_08_ANCHORS",
        "render_authorized": False,
        "updated_at": now,
        "editorial_target_seconds": 80.0,
        "extension_07_08": {
            "owner_scope": "two additional 10-second visual takes",
            "takes": ["07", "08"],
            "anchor_status": "pending_human_review",
            "render_order": ["07", "08"],
            "serial_gpu_only": True,
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = False
    _atomic_json_write(production_path, production)

    manifest = json.loads(project_manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update({
        "title": "Gohan SSJ2 - Android 16 e Cell - live action cinematografico 80s",
        "duration_target_seconds": 80.0,
        "updated_at": now,
        "maestro_status": "WAITING_OWNER_REVIEW_TAKES_07_08_ANCHORS",
        "render_authorized": False,
    })
    _atomic_json_write(project_manifest_path, manifest)

    print(json.dumps({
        "ok": True,
        "takes": ["07", "08"],
        "duration_target_seconds": 80.0,
        "anchor07": {"file": str(END_07), "sha256": sha256(END_07)},
        "anchor08": {"file": str(END_08), "sha256": sha256(END_08)},
        "render_authorized": False,
        "human_review_required": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
