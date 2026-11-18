from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE_PATH = PROJECT / "take_queue.json"
PROJECT_MANIFEST_PATH = PROJECT / "project_manifest.json"
PILOT_MANIFEST_PATH = PROJECT / "work" / "v5_sequential_pilot" / "production_manifest_v5_pilot.json"
ARCHIVE_DIR = PROJECT / "archive" / "before_v5_sequential_pilot"

POLICY = {
    "required": True,
    "generated_connector_required_between_takes": True,
    "crossfade_forbidden": True,
    "freeze_frame_forbidden": True,
    "static_tail_forbidden": True,
    "motion_handoff_required": True,
    "full_duration_motion_required": True,
    "three_interval_motion_required": True,
    "moving_transition_anchors_required": True,
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def qc_pending() -> dict:
    return {
        "status": "v5_pilot_pending_generation",
        "human_visual_approval": "pending",
        "transition_motion_gate": {
            "status": "pending",
            "evident_camera": False,
            "real_depth": False,
            "internal_action": False,
            "clear_progression": False,
            "continuous_action": False,
            "motion_across_all_intervals": False,
            "moving_anchor_context": False,
            "no_crossfade": False,
            "no_freeze": False,
            "no_static_tail": False,
            "no_reset": False,
            "evidence": "pending generated MP4 and visual boundary review",
        },
    }


def apply_take_01(take: dict, now: str) -> None:
    start_file = str((take.get("base_image") or {}).get("file") or "")
    end_file = str((((take.get("shot_contract") or {}).get("visual_references") or {}).get("end_frame_file")) or "")
    entry = "Android 16 is already finishing his final calm words on the arena floor while teenage Super Saiyan Gohan watches and tailless Perfect Cell stands behind the mechanical head."
    middle = "Android 16 closes his mouth on the final word; Gohan takes one urgent step and Cell silently transfers weight, raises exactly one boot and begins the same irreversible downward motion without resetting."
    exit_motion = "Cell's single boot remains airborne with a clear gap above the intact mechanical head and has just begun descending; Gohan, dust, cloth, armor and the low camera still carry forward velocity into Take 02."
    prompt = (
        "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION CINEMATIC TAKE between the exact approved frames. "
        "Preserve one teenage ordinary Super Saiyan Gohan, one completely tailless full-size Perfect Cell, Android 16 as a purely mechanical head and the established destroyed Cell Games arena. "
        "0-30%: Android 16 is already speaking his final calm words; only Android 16 lips articulate. Cell remains silent with lips sealed while a low physical dolly travels beside the mechanical head, changing foreground overlap and revealing Gohan advancing behind him. "
        "30-70%: Android 16 finishes and closes his mouth. Gohan takes one urgent step without resetting. Cell silently transfers body weight and raises exactly one boot as dust, cloth, hair, back plates and loose stones move independently. "
        "70-100%: the same boot reaches its peak only late and immediately begins descending; Gohan keeps lunging, the camera drops physically beside the boot and the perspective continues changing. Reach the supplied final composition only in the last 0.10 seconds and cut while the boot, Gohan, debris and camera still have visible velocity. "
        "FORBIDDEN: static hold, living photo, early final pose, frozen tail, repeated boot lift, stomp contact, crushing, Cell dialogue or lip motion, Cell tail or rear appendage, tear effect, SSJ2 transformation, crossfade, zoom-only camera, blood, gore, duplicate character, anime drawing, game render, text, logo or watermark."
    )
    take.update({
        "slug": "V5_PILOTO_01_FALA_AMEACA_BOTA_EM_MOVIMENTO",
        "title": "V5 PILOTO 01 — Fala do Android 16 → bota em movimento",
        "sequence": 1,
        "role": "v5_sequential_pilot_entry",
        "is_transition": True,
        "transition": {"is_transition": True, "connects_from": "opening moving state", "connects_to": "02 exact descending boot"},
        "objective": "Fechar a fala e iniciar a descida da bota no mesmo plano, sem pose parada na fronteira.",
        "target_duration_seconds": 5.166667,
        "native_duration_seconds": 5.166667,
        "animation_prompt": prompt,
        "status": "VIDEO_PENDING_GENERATION",
        "maestro_status": "READY",
        "render_authorized": True,
        "maestro_notes": "V5 sequencial do zero. O arquivo V3 anterior permanece no histórico. Gerar Take 01 primeiro e bloquear Take 02 até o QC da fronteira.",
        "qc": qc_pending(),
    })
    generation = take.setdefault("video_generation", {})
    generation.update({
        "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot", "profile": "minimax_h3_fl2va_int8_720p24",
        "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0,
        "start_end_frame_enabled": True, "require_approved_start_frame": True, "require_approved_end_frame": True,
        "render_authorized": True, "visual_only_pass": True, "native_audio_authorized": False, "prompt": prompt,
    })
    contract = take.setdefault("shot_contract", {})
    contract.update({
        "story_purpose": "Encerrar a fala de Android 16 e converter a ameaça de Cell em movimento físico irreversível.",
        "dramatic_question": "Gohan alcançará Android 16 antes de a bota completar a descida?",
        "story_change": "Android 16 ainda fala com a bota no chão → a fala termina e a mesma bota já desce enquanto Gohan avança.",
        "distinct_story_events": 3,
        "reaction": "Gohan abandona a imobilidade e dá um passo urgente enquanto Cell permanece silencioso.",
        "cut_motivation": "Cortar durante a descida ativa da bota, entregando o mesmo vetor ao Take 02.",
        "duration_reason": "5,166667 s comportam a última frase, a reação de Gohan e o início da descida sem preenchimento.",
        "motion_beats": {"start": entry, "middle": middle, "end": exit_motion},
        "environment_state_before": "Cabeça mecânica intacta; bota de Cell apoiada; poeira baixa.",
        "environment_state_after": "Cabeça ainda intacta; bota já descendente; poeira e pedras levantadas pelo deslocamento.",
        "environment_damage": "Nenhum dano novo antes do impacto; apenas pressão e deslocamento preparatório.",
        "scale_evidence": {"foreground": "cabeça mecânica, cascalho e bota cruzam escalas", "midground": "Cell transfere peso e levanta uma única perna", "background": "Gohan avança e a arena muda de perspectiva"},
    })
    refs = contract.setdefault("visual_references", {})
    refs.update({"start_frame_file": start_file, "start_frame_approved": True, "end_frame_file": end_file, "end_frame_approved": True})
    contract["transition_motion_contract"] = {
        "camera_evidence": {"movement": "One low physical dolly beside Android 16 becomes a diagonal drop beside Cell's descending boot.", "physical_translation": True, "perspective_change": "Mechanical foreground, Cell, Gohan and ruined arena continuously change overlap and relative scale."},
        "real_depth": {"foreground": "Android 16 mechanical head, boot, stones and dust cross close to lens.", "midground": middle, "background": "Gohan and ruined arena shift slowest while the camera advances.", "differential_motion": "Foreground rubble is fastest, Cell and Gohan move at different medium rates, distant ruins are slowest.", "occlusion_or_scale_change": "Physical dolly changes boot and head scale without blackout or flat parallax."},
        "internal_action": {"primary_event": middle, "independent_elements": ["Gohan body, hair and clothing continue advancing", "dust, stones and Cell back plates retain separate inertia"], "camera_independent": True},
        "progression": {"start": entry, "middle": middle, "end": exit_motion, "end_state_change": "The silent threat becomes one active irreversible boot descent.", "exit_or_cut": "hard action handoff on the still-descending boot"},
        "continuity": {
            "editorial_method": "single_continuous_take", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True,
            "entry_motion": entry, "exit_motion": exit_motion,
            "interval_motion": {"early_0_30": "speech, Gohan advance and low dolly already moving", "middle_30_70": "speech ends while weight transfer and boot lift progress", "late_70_100": "boot peaks late and begins descending while camera and Gohan continue"},
            "moving_anchor_context": {"start_source": "owner-approved opening frame with explicit entry performance", "start_has_motion_before_and_after": True, "end_source": "owner-approved shared pre-stomp frame directed as an active descending handoff", "end_has_motion_before_and_after": True},
            "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0,
        },
    }
    take["maestro_updated_at"] = now


def apply_take_02(take: dict, now: str) -> None:
    start_file = str((take.get("base_image") or {}).get("file") or "")
    end_file = str((((take.get("shot_contract") or {}).get("visual_references") or {}).get("end_frame_file")) or "")
    entry = "The exact same Cell boot, Gohan lunge, dust and low camera velocity continue immediately from Take 01 with no pose reset."
    middle = "The single boot completes one mechanical stomp, fragments burst, the floor crack races toward Gohan and the camera accelerates along the same crack."
    exit_motion = "The crack reaches Gohan once; he plants into rising anger as gold pressure and the first blue-white arc expand while tailless Cell, debris and camera still move."
    prompt = (
        "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION CONTINUATION from the exact supplied moving frames. "
        "Continue the identical teenage ordinary Super Saiyan Gohan, completely tailless full-size Perfect Cell, purely mechanical Android 16 remains, costumes, destroyed arena, storm light and spatial geography. "
        "0-30%: inherit the exact descending boot, Gohan lunge, dust and low camera vector from Take 01. The same boot keeps descending and contacts once; never raise it again. "
        "30-70%: the one impact crushes only metal, ceramic and circuits. Mechanical fragments burst sideways, a circular dust shockwave expands and one deep crack races toward Gohan while the camera physically overtakes it at floor level. Cell's body recoils from the same impact. "
        "70-100%: the crack reaches Gohan once; he plants through the force, anger rises, gold aura punches outward and the first blue-white electrical arc lashes across the arena. Cell slides backward while shielding his face. Reach the supplied final frame only in the last 0.10 seconds and cut while Gohan, Cell, lightning, debris, dust and camera retain velocity. "
        "FORBIDDEN: static hold, living photo, repeated stomp, boot reset, early final pose, tear or liquid effect, blood, gore, organic injury, Cell tail or rear appendage, completed SSJ2 hero pose, dialogue, crossfade, zoom-only camera, duplicate character, anime drawing, game render, text, logo or watermark."
    )
    take.update({
        "slug": "V5_PILOTO_02_DESCIDA_IMPACTO_RUPTURA_CONTINUA",
        "title": "V5 PILOTO 02 — Descida → impacto → ruptura contínua",
        "sequence": 2,
        "role": "v5_sequential_pilot_consequence",
        "is_transition": True,
        "transition": {"is_transition": True, "connects_from": "01 exact descending boot", "connects_to": "future SSJ2 continuation"},
        "objective": "Continuar a mesma descida, executar o impacto e entregar a raiva de Gohan ainda em movimento.",
        "target_duration_seconds": 5.166667,
        "native_duration_seconds": 5.166667,
        "animation_prompt": prompt,
        "status": "BLOCKED_UNTIL_TAKE01_INTERNAL_QC",
        "maestro_status": "BLOCKED",
        "render_authorized": False,
        "maestro_notes": "V5 sequencial. Não gerar antes de o Take 01 provar movimento útil e handoff visual na bota descendente.",
        "qc": qc_pending(),
    })
    generation = take.setdefault("video_generation", {})
    generation.update({
        "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot", "profile": "minimax_h3_fl2va_int8_720p24",
        "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0,
        "start_end_frame_enabled": True, "require_approved_start_frame": True, "require_approved_end_frame": True,
        "render_authorized": False, "visual_only_pass": True, "native_audio_authorized": False, "prompt": prompt,
    })
    contract = take.setdefault("shot_contract", {})
    contract.update({
        "story_purpose": "Converter a ameaça em impacto e o impacto na primeira ruptura emocional de Gohan.",
        "dramatic_question": "A consequência do esmagamento romperá o controle de Gohan antes de Cell se recompor?",
        "story_change": "Bota ainda descendo sobre cabeça intacta → restos mecânicos, fissura propagada e primeira descarga de raiva.",
        "distinct_story_events": 3,
        "reaction": "Gohan planta contra a onda de choque e Cell é empurrado pela resposta energética.",
        "cut_motivation": "Cortar durante a expansão da aura e do primeiro raio para continuar a transformação.",
        "duration_reason": "5,166667 s são o mínimo para descida herdada, um impacto e uma reação energética sem pausa.",
        "motion_beats": {"start": entry, "middle": middle, "end": exit_motion},
        "environment_state_before": "Cabeça mecânica intacta; bota descendente; fissura ainda curta.",
        "environment_state_after": "Restos mecânicos dispersos; fissura alcança Gohan; poeira e pedras ainda suspensas.",
        "environment_damage": "Cabeça mecânica destruída e nova fissura profunda persistente atravessando a arena.",
        "scale_evidence": {"foreground": "fragmentos e fissura correm rente à lente", "midground": "Cell sofre recuo e Gohan planta contra a pressão", "background": "arena e nuvens reagem à onda expansiva"},
    })
    refs = contract.setdefault("visual_references", {})
    refs.update({"start_frame_file": start_file, "start_frame_approved": True, "end_frame_file": end_file, "end_frame_approved": True})
    contract["transition_motion_contract"] = {
        "camera_evidence": {"movement": "The inherited low boot-side dolly absorbs the impact, races along the crack and rises physically toward Gohan.", "physical_translation": True, "perspective_change": "Boot, fragments, crack, fighters and arena continuously reorder and change relative scale."},
        "real_depth": {"foreground": "Mechanical fragments and the floor crack cross closest and fastest.", "midground": middle, "background": "Gohan, Cell, ruined arena and clouds react at separate depths.", "differential_motion": "Fragments and crack are fastest, bodies carry medium inertia, distant arena and storm shift slowest.", "occlusion_or_scale_change": "The floor chase and physical rise change scale without blackout or flat parallax."},
        "internal_action": {"primary_event": middle, "independent_elements": ["Cell recoil and Gohan planting follow separate force vectors", "debris, dust, lightning and clothing continue independently"], "camera_independent": True},
        "progression": {"start": entry, "middle": middle, "end": exit_motion, "end_state_change": "An intact mechanical head becomes debris and Gohan's contained anger becomes an expanding electrical rupture.", "exit_or_cut": "hard action handoff on expanding aura, lightning and moving debris"},
        "continuity": {
            "editorial_method": "single_continuous_take", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True,
            "entry_motion": entry, "exit_motion": exit_motion,
            "interval_motion": {"early_0_30": "same boot and camera continue descending into one impact", "middle_30_70": "impact becomes fragments, shockwave and racing crack", "late_70_100": "crack becomes Gohan reaction, aura pressure and first lightning"},
            "moving_anchor_context": {"start_source": "shared owner-approved pre-stomp frame used as the active moving handoff from Take 01", "start_has_motion_before_and_after": True, "end_source": "owner-approved impact consequence frame directed with active aura and debris", "end_has_motion_before_and_after": True},
            "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0,
        },
    }
    take["maestro_updated_at"] = now


def main() -> None:
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    queue = read_json(QUEUE_PATH)
    manifest = read_json(PROJECT_MANIFEST_PATH)
    takes = {str(item.get("id")): item for item in queue.get("takes", []) if isinstance(item, dict)}
    if "01" not in takes or "02" not in takes:
        raise RuntimeError("Takes 01 e 02 não encontrados.")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, PROJECT_MANIFEST_PATH):
        backup = ARCHIVE_DIR / source.name
        if not backup.exists():
            shutil.copy2(source, backup)

    apply_take_01(takes["01"], now)
    apply_take_02(takes["02"], now)
    queue["status"] = "V5_SEQUENTIAL_PILOT_TAKE01_READY"
    queue["render_authorized"] = True
    queue["render_authority"] = "Owner explicitly ordered the corrected sequential V5 pilot on 2026-08-20."
    queue["continuous_action_contract"] = POLICY
    queue["universal_transition_motion_gate"] = {"required": True}
    queue["story_batch_policy"] = {
        "enabled": True, "version": "gohan_v5_sequential_pilot_v1", "batch_size": 1,
        "render_order": ["01", "02"], "strict_contiguous": True,
        "require_all_base_images_ready": True, "fill_eligible_across_batches": False,
        "require_full_batch": True, "allow_incomplete_correction_batch": False,
        "control_surface": "take01_internal_qc_then_take02", "configured_at": now,
    }
    queue["updated_at"] = now

    manifest["status"] = "V5_SEQUENTIAL_PILOT_IN_PRODUCTION"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["render_authorized"] = True
    manifest["render_authority"] = queue["render_authority"]
    manifest["updated_at"] = now
    manifest["directed_correction_v5"] = {
        "reason": "V3 rejected for bad dry cuts and fragmented direction; V4 connector route abandoned before execution.",
        "method": "regenerate core takes sequentially with one shared active boundary, matching the successful Vejito construction method",
        "pilot_take_ids": ["01", "02"], "generate_serially": True,
        "take02_blocked_until_take01_internal_qc": True,
        "previous_master": "deliveries/gohan_ssj2_cell_visual_cut_v3_new_take02_720p60.mp4",
        "previous_master_status": "REJECTED_BY_OWNER_ROLLBACK_ONLY",
        "rife_before_picture_lock": False, "retime_before_picture_lock": False,
        "foley_status": "BLOCKED_UNTIL_NEW_PICTURE_LOCK",
    }

    pilot_manifest = {
        "schema_version": "gohan_ssj2_v5_sequential_pilot",
        "project_id": manifest.get("project_id"),
        "title": "Gohan SSJ2 — V5 — piloto sequencial Takes 01 e 02",
        "objective": "Provar uma fronteira invisível com bota descendente, impacto e reação sem remendo editorial.",
        "updated_at": now,
        "universal_transition_motion_gate": {"required": True},
        "continuous_action_contract": POLICY,
        "takes": [takes["01"], takes["02"]],
        "gpu_policy": {"serial_only": True, "max_concurrent_video_jobs": 1},
        "audio": {"status": "BLOCKED_UNTIL_PICTURE_LOCK"},
    }
    atomic_json(QUEUE_PATH, queue)
    atomic_json(PROJECT_MANIFEST_PATH, manifest)
    atomic_json(PILOT_MANIFEST_PATH, pilot_manifest)
    print(json.dumps({
        "ok": True, "pilotManifest": str(PILOT_MANIFEST_PATH),
        "take01": {"title": takes["01"]["title"], "status": takes["01"]["maestro_status"], "frames": takes["01"]["video_generation"]["frames"]},
        "take02": {"title": takes["02"]["title"], "status": takes["02"]["maestro_status"], "authorized": takes["02"]["render_authorized"]},
        "archive": str(ARCHIVE_DIR),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
