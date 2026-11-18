from __future__ import annotations

import hashlib
import json
import shutil
import sys
import uuid
from pathlib import Path


ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parents[1]
sys.path.insert(0, str(REPO / "services" / "studio"))

from video_projects import _atomic_json_write, create_project, register_end_anchor_candidate, utc_now  # noqa: E402


ROOT = ENGINE / "projetos"
SOURCE_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT_ID = "gohan_ssj2_take07_frenetic_multi_anchor_v2"
SOURCE = ROOT / SOURCE_ID
TARGET = ROOT / PROJECT_ID
START = SOURCE / "base_images" / "take06_cell_lancado_pela_arena_anchor_bdd4b9b79e35.png"
ANCHOR_A = SOURCE / "keyframes" / "take07_multi_anchor_A_parry_tailless_v1_1664x936.png"
ANCHOR_B = SOURCE / "keyframes" / "take07_multi_anchor_B_body_punch_tailless_v1_1664x936.png"
ANCHOR_C = SOURCE / "keyframes" / "take07_frenetic_C_rising_knee_anchor_v2_1664x936.png"
END = SOURCE / "base_images" / "take07_gohan_cell_trocacao_pressao_anchor_4dbdaabe7124.png"
ANCHORS = (START, ANCHOR_A, ANCHOR_B, ANCHOR_C, END)

SPECS = (
    {
        "id": "07A2",
        "slug": "perseguicao_tres_trocas_parry",
        "start": "Cell sem cauda ainda voa entre destrocos e Gohan SSJ2 o alcanca.",
        "action": "Cell tenta um direto e um cotovelo separados; Gohan esquiva, responde com um golpe curto no corpo e imediatamente apara o segundo ataque.",
        "end": "A aparada final ainda carrega velocidade diagonal e os corpos continuam atravessando o quadro.",
        "objective": "Entregar tres trocas rapidas e contato fisico antes da primeira ancora.",
    },
    {
        "id": "07B2",
        "slug": "joelho_bloqueado_golpe_corpo",
        "start": "Gohan ainda controla o punho de Cell na aparada.",
        "action": "Cell puxa o braco e tenta um joelho; Gohan bloqueia com o antebraco, gira por dentro e conecta palma, cotovelo e golpe no corpo em sequencia continua.",
        "end": "O golpe no corpo rompe a guarda e Cell sem cauda torce para tras sem parar.",
        "objective": "Aumentar a cadencia com bloqueio e tres impactos legiveis.",
    },
    {
        "id": "07C2",
        "slug": "contra_golpe_esquiva_joelhada_massiva",
        "start": "Cell ainda absorve o golpe no corpo e tenta recuperar a base.",
        "action": "Cell solta um gancho desesperado; Gohan passa por baixo, acerta um soco curto nas costelas e converte o mesmo impulso em uma joelhada ascendente brutal.",
        "end": "A joelhada levanta Cell sem cauda dentro de uma onda de choque massiva, ambos ainda em movimento.",
        "objective": "Construir massa crescente ate uma joelhada que realmente desloca Cell.",
    },
    {
        "id": "07D2",
        "slug": "combo_aereo_pressao_final",
        "start": "Cell sem cauda ainda sobe dobrado pela joelhada e Gohan acompanha.",
        "action": "Gohan conecta um martelo descendente, cruza o eixo, acerta um chute lateral e fecha com um soco compacto na guarda; cada contato tem antecipacao e consequencia.",
        "end": "Cell derrapa para tras enquanto Gohan ocupa o espaco e continua pressionando na fronteira aprovada.",
        "objective": "Fechar com tres impactos fortes, progressao espacial e dominio claro de Gohan.",
    },
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt(spec: dict[str, str], index: int) -> str:
    axes = ("descending pursuit orbit", "fast lateral whip-arc behind foreground rubble", "low rising arc through the impact ring", "wide-to-close corkscrew chase")
    return (
        "ONE UNBROKEN 5.125-SECOND PHOTOREALISTIC LIVE-ACTION DRAGON BALL COMBAT CONNECTOR between the exact supplied "
        "moving first and last frames. This must be FRENZIED, HEAVY, MASSIVE AND CINEMATIC while every strike remains "
        "readable. Preserve exactly one teenage SSJ2 Gohan and exactly one adult Perfect Cell as continuous bodies. "
        "Perfect Cell is completely tailless in every frame: clean pelvis, no tail, stinger, tentacle, cable, rear tube, "
        "curved rear limb or third rear blade; only two short rigid upper-back wing plates. "
        f"ENTRY: {spec['start']} ACTION: {spec['action']} EXIT: {spec['end']} "
        "No slow circling and no empty travel: first contact begins in the opening 0.6 seconds, a new defense or impact occurs "
        "roughly every 0.7-1.0 seconds, and cause-and-effect never resets. Each hit creates directional body displacement, "
        "armor compression, a brief gold-white pressure burst, blue-white lightning and staggered debris at multiple depths. "
        f"Camera executes a physical {axes[index]} with aggressive height and axis change, real parallax and motivated whip "
        "occlusion, but faces and anatomy remain readable. Bodies, hair, cloth, armor, lightning, dust and rocks carry useful "
        "velocity through the cut. Reach the final anchor only in the last instant. FORBIDDEN: slow pose, empty chase, soft "
        "contact, held ending, freeze, crossfade, reset, repeated loop, teleportation, duplicate body, extra fighter, extra limb, "
        "Cell Junior, energy beam, tail, anime drawing, cel shading, game render, plastic CGI skin, text, blood or gore."
    )


def approved_image(path: Path, now: str, source: str) -> dict:
    return {"status": "approved_for_video", "file": path.as_posix(), "source": source, "image_sha256": digest(path), "approved_at": now}


def take_record(index: int, now: str) -> dict:
    spec = SPECS[index]
    start_file = TARGET / "keyframes" / f"anchor_{index}_{('start','A','B','C')[index]}.png"
    end_file = TARGET / "keyframes" / f"anchor_{index + 1}_{('A','B','C','end')[index]}.png"
    new_anchor = index == 2
    request_id = uuid.uuid4().hex if new_anchor else ""
    requests = []
    if request_id:
        requests.append({"id": request_id, "status": "PENDING", "category": "ANCHOR", "anchor_side": "end", "reason": spec["objective"], "created_at": now, "updated_at": now})
    # 07D2 receives its start from the newly approved end anchor of 07C2.
    base = {"status": "waiting_derived_anchor"} if index == 3 else approved_image(start_file, now, "approved owner anchor inherited into correction v2")
    return {
        "id": spec["id"],
        "slug": spec["slug"],
        "name": spec["slug"],
        "sequence": index + 1,
        "role": "take07_frenetic_massive_connector",
        "is_transition": True,
        "objective": spec["objective"],
        "target_duration_seconds": 5.125,
        "editorial_use_seconds": 2.5,
        "animation_prompt": prompt(spec, index),
        "base_image": base,
        "shot_contract": {
            "story_purpose": spec["objective"],
            "story_change": f"{spec['start']} -> {spec['end']}",
            "distinct_story_events": 3,
            "motion_beats": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
            "camera": {"movement": "aggressive physical orbit with height and axis changes", "angle": "variable low three-quarter", "lens": "20-32 mm", "focus": "readable high-frequency impacts"},
            "visual_references": {"start_frame_file": start_file.as_posix() if index != 3 else "inherited from approved 07C2 end", "start_frame_approved": index != 3, "end_frame_file": end_file.as_posix() if not new_anchor else "", "end_frame_approved": not new_anchor, "end_frame_sha256": digest(end_file) if not new_anchor else ""},
            "transition_motion_contract": {
                "camera_evidence": {"physical_translation": True, "evident_camera": True},
                "real_depth": {"differential_motion": "foreground fastest, fighters midground, ruins slowest"},
                "internal_action": {"primary_event": spec["action"], "camera_independent": True},
                "progression": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
                "continuity": {"editorial_method": "four_microtakes_each_retimed_to_2_5s_hard_cut_on_motion", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True, "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0},
            },
        },
        "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24", "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0, "start_end_frame_enabled": True, "require_approved_start_frame": True, "require_approved_end_frame": True, "visual_only_pass": True, "native_audio_authorized": False},
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana da nova ancora massiva C.",
        "audio_direction": {"status": "blocked_until_picture_lock", "music": False, "dialogue": False},
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {"status": "waiting_anchor_owner_review", "human_visual_approval": "pending"},
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_director_requests": requests,
    }


def main() -> None:
    for path in ANCHORS:
        if not path.is_file():
            raise FileNotFoundError(path)
    if TARGET.exists():
        raise FileExistsError(f"Projeto ja existe: {TARGET}")
    now = utc_now()
    create_project(ROOT, name="Gohan SSJ2 - Take 07 frenético e massivo V2", project_id=PROJECT_ID, objective="Refazer o take 07 em quatro microtakes acelerados, com impactos frequentes, massa e camera cinematografica.", duration_seconds=10)
    names = ("anchor_0_start.png", "anchor_1_A.png", "anchor_2_B.png", "anchor_3_C.png", "anchor_4_end.png")
    for source, name in zip(ANCHORS, names):
        shutil.copy2(source, TARGET / "keyframes" / name)
    queue = {
        "schema_version": "gohan_take07_frenetic_multi_anchor_v2",
        "project_id": PROJECT_ID,
        "status": "WAITING_OWNER_ANCHOR_REVIEW",
        "updated_at": now,
        "render_authorized": False,
        "methodology": "four_minimax_h3_microtakes_retimed_to_2_5_seconds_each",
        "anchor_generation_policy": {"provider": "openai_builtin_image_generation_registered_in_maestro", "inherit_approved_end_as_next_start": True, "require_explicit_human_confirmation": True, "human_review_required": True},
        "continuous_action_contract": {"generated_connector_required_between_anchors": True, "crossfade_forbidden": True, "freeze_frame_forbidden": True, "static_tail_forbidden": True, "motion_handoff_required": True, "full_duration_motion_required": True},
        "takes": [take_record(index, now) for index in range(4)],
    }
    manifest_path = TARGET / "project_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update({"schema_version": "gohan_take07_frenetic_project_v2", "status": "WAITING_OWNER_ANCHOR_REVIEW", "maestro_status": "IN_PROGRESS", "updated_at": now, "source_project_id": SOURCE_ID, "source_take_id": "07", "render_authorized": False})
    _atomic_json_write(TARGET / "take_queue.json", queue)
    _atomic_json_write(manifest_path, manifest)
    request_id = queue["takes"][2]["maestro_director_requests"][0]["id"]
    view = register_end_anchor_candidate(
        ROOT,
        PROJECT_ID,
        "07C2",
        request_id=request_id,
        image_bytes=ANCHOR_C.read_bytes(),
        original_filename=ANCHOR_C.name,
        metadata={"prompt": "Gohan SSJ2 acerta joelhada ascendente massiva em Perfect Cell sem cauda", "model": "OpenAI built-in image generation", "generator": "OpenAI built-in image generation", "sourceOutput": ANCHOR_C.as_posix(), "sourceSha256": digest(ANCHOR_C), "requiredObjects": {"anchorSide": "end", "ownerReviewRequired": True, "perfectCellTail": False, "massiveRisingKneeImpact": True, "expectedVisibleCharacters": ["Gohan SSJ2", "Perfect Cell no tail"]}},
    )
    print(json.dumps({"ok": True, "projectId": PROJECT_ID, "requestId": request_id, "candidate": view.get("endAnchorCandidate"), "renderAuthorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
