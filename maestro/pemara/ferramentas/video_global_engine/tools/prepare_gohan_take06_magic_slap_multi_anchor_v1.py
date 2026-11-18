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
PROJECT_ID = "gohan_ssj2_take06_magic_slap_multi_anchor_v1"
SOURCE = ROOT / SOURCE_ID
TARGET = ROOT / PROJECT_ID
START = SOURCE / "base_images" / "take05_gohan_domina_cell_corpo_a_corpo_anchor_7bc8888ef1d6.png"
SLAP = SOURCE / "keyframes" / "take06_magic_slap_deflection_anchor_v1_1664x936.png"
END = SOURCE / "base_images" / "take06_cell_lancado_pela_arena_anchor_bdd4b9b79e35.png"

SPECS = (
    {
        "id": "06A2",
        "slug": "gohan_desvia_magia_com_tapa",
        "objective": "Cell dispara um projetil e Gohan o desvia com um tapa simples sem atravessamento.",
        "start": "Cell sem cauda e Gohan SSJ2 ainda carregam o impulso do take 05.",
        "action": "Cell cria e dispara um unico projetil dourado compacto; Gohan espera ate o ultimo instante e bate de lado com uma mao aberta.",
        "end": "A palma toca apenas a lateral do projetil, que dobra noventa graus para as ruinas sem sobrepor o corpo de Gohan.",
    },
    {
        "id": "06B2",
        "slug": "gohan_retoma_pressao_lanca_cell",
        "objective": "Converter o desvio casual em uma sequencia corporal forte que lanca Cell pela arena.",
        "start": "O projetil ja sai do eixo e Gohan recolhe a mao do tapa sem pausa.",
        "action": "A energia explode longe; Gohan fecha a distancia, bloqueia um contra-golpe, conecta um cotovelo e uma joelhada separados.",
        "end": "Gohan completa um golpe ascendente massivo e Cell sem cauda continua voando pela arena.",
    },
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt(spec: dict[str, str]) -> str:
    return (
        "ONE UNBROKEN 5.125-SECOND PHOTOREALISTIC LIVE-ACTION DRAGON BALL ACTION CONNECTOR between the exact supplied "
        "moving first and last frames. Preserve exactly one teenage SSJ2 Gohan and exactly one adult Perfect Cell. "
        "Perfect Cell is completely tailless in every frame; clean pelvis silhouette, no tail, stinger, tentacle, cable, "
        "rear tube or curved appendage; only two rigid upper-back wing plates. "
        f"ENTRY: {spec['start']} ACTION: {spec['action']} EXIT: {spec['end']} "
        "The golden projectile must remain a compact object with a readable trajectory. It may contact only Gohan's open "
        "palm and must never overlap, enter, pass through or hide his head, torso, arms or legs. The slap sharply redirects "
        "it off-axis; no shield bubble and no beam struggle. Physical camera performs a fast low arc with height change and "
        "strong three-layer parallax. Use rapid readable anticipation-contact-consequence, heavy shockwaves, independent "
        "hair, cloth, armor, lightning, dust and stone motion through the cut. FORBIDDEN: body intersection, projectile "
        "through Gohan, slow pose, held ending, freeze, crossfade, reset, repeated loop, teleportation, duplicate body, extra "
        "fighter, extra limb, Cell Junior, anime drawing, cel shading, game render, plastic CGI skin, text, blood or gore."
    )


def take_record(index: int, now: str) -> dict:
    spec = SPECS[index]
    first = index == 0
    last = index == 1
    start_file = TARGET / "keyframes" / "anchor_0_take05_exit_approved.png" if first else None
    end_file = TARGET / "keyframes" / "anchor_E_take06_exit_approved.png" if last else None
    request_id = uuid.uuid4().hex if first else ""
    base = (
        {"status": "approved_for_video", "file": start_file.as_posix(), "image_sha256": digest(start_file), "approved_at": now}
        if first
        else {"status": "waiting_derived_anchor"}
    )
    requests = []
    if request_id:
        requests.append({"id": request_id, "status": "PENDING", "category": "ANCHOR", "anchor_side": "end", "reason": spec["objective"], "created_at": now, "updated_at": now})
    return {
        "id": spec["id"],
        "slug": spec["slug"],
        "name": spec["slug"],
        "sequence": index + 1,
        "role": "take06_magic_slap_correction_connector",
        "is_transition": True,
        "objective": spec["objective"],
        "target_duration_seconds": 5.125,
        "editorial_use_seconds": 5.0,
        "animation_prompt": prompt(spec),
        "base_image": base,
        "shot_contract": {
            "story_purpose": spec["objective"],
            "story_change": f"{spec['start']} -> {spec['end']}",
            "distinct_story_events": 1,
            "motion_beats": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
            "camera": {"movement": "fast low physical arc with crane height change", "angle": "low three-quarter", "lens": "24-35 mm", "focus": "palm contact, projectile trajectory and body impact"},
            "visual_references": {
                "start_frame_file": start_file.as_posix() if start_file else "inherited from previous approved end anchor",
                "start_frame_approved": bool(start_file),
                "end_frame_file": end_file.as_posix() if end_file else "",
                "end_frame_approved": last,
                "end_frame_sha256": digest(end_file) if end_file else "",
            },
            "transition_motion_contract": {
                "camera_evidence": {"physical_translation": True},
                "real_depth": {"differential_motion": "foreground fastest, fighters midground, ruins slowest"},
                "internal_action": {"primary_event": spec["action"], "camera_independent": True},
                "progression": {"start": spec["start"], "middle": spec["action"], "end": spec["end"]},
                "continuity": {"editorial_method": "two_microtakes_hard_cut_on_motion", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True, "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0},
            },
        },
        "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24", "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0, "start_end_frame_enabled": True, "require_approved_start_frame": True, "require_approved_end_frame": True, "visual_only_pass": True, "native_audio_authorized": False},
        "render_authorized": False,
        "render_block_reason": "Aguardando aprovacao humana da ancora do tapa.",
        "audio_direction": {"status": "blocked_until_picture_lock", "music": False, "dialogue": False},
        "video": {"status": "pending_generation", "output_preview": "", "output_active": ""},
        "qc": {"status": "waiting_anchor_owner_review", "human_visual_approval": "pending"},
        "maestro_status": "PLANNED",
        "maestro_updated_at": now,
        "maestro_director_requests": requests,
    }


def main() -> None:
    for path in (START, SLAP, END):
        if not path.is_file():
            raise FileNotFoundError(path)
    if TARGET.exists():
        raise FileExistsError(f"Projeto ja existe: {TARGET}")
    now = utc_now()
    create_project(ROOT, name="Gohan SSJ2 - Take 06 tapa na magia V1", project_id=PROJECT_ID, objective="Corrigir o projetil que atravessava Gohan usando uma ancora de tapa lateral e dois microtakes.", duration_seconds=10)
    shutil.copy2(START, TARGET / "keyframes" / "anchor_0_take05_exit_approved.png")
    shutil.copy2(END, TARGET / "keyframes" / "anchor_E_take06_exit_approved.png")
    queue = {
        "schema_version": "gohan_take06_magic_slap_multi_anchor_v1",
        "project_id": PROJECT_ID,
        "status": "WAITING_OWNER_ANCHOR_REVIEW",
        "updated_at": now,
        "render_authorized": False,
        "anchor_generation_policy": {"provider": "openai_builtin_image_generation_registered_in_maestro", "inherit_approved_end_as_next_start": True, "require_explicit_human_confirmation": True, "human_review_required": True},
        "continuous_action_contract": {"generated_connector_required_between_anchors": True, "crossfade_forbidden": True, "freeze_frame_forbidden": True, "motion_handoff_required": True, "full_duration_motion_required": True},
        "takes": [take_record(0, now), take_record(1, now)],
    }
    manifest_path = TARGET / "project_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update({"schema_version": "gohan_take06_magic_slap_project_v1", "status": "WAITING_OWNER_ANCHOR_REVIEW", "maestro_status": "IN_PROGRESS", "updated_at": now, "source_project_id": SOURCE_ID, "source_take_id": "06R1", "render_authorized": False})
    _atomic_json_write(TARGET / "take_queue.json", queue)
    _atomic_json_write(manifest_path, manifest)
    request_id = queue["takes"][0]["maestro_director_requests"][0]["id"]
    view = register_end_anchor_candidate(
        ROOT,
        PROJECT_ID,
        "06A2",
        request_id=request_id,
        image_bytes=SLAP.read_bytes(),
        original_filename=SLAP.name,
        metadata={"prompt": "Gohan SSJ2 desvia projetil dourado com tapa simples de mao aberta", "model": "OpenAI built-in image generation", "generator": "OpenAI built-in image generation", "sourceOutput": SLAP.as_posix(), "sourceSha256": digest(SLAP), "requiredObjects": {"anchorSide": "end", "ownerReviewRequired": True, "projectileOutsideGohanBody": True, "perfectCellTail": False, "expectedVisibleCharacters": ["Gohan SSJ2", "Perfect Cell no tail"]}},
    )
    print(json.dumps({"ok": True, "projectId": PROJECT_ID, "requestId": request_id, "candidate": view.get("endAnchorCandidate"), "renderAuthorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
