from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE_PATH = PROJECT / "take_queue.json"
PROJECT_MANIFEST_PATH = PROJECT / "project_manifest.json"
BRIDGE_MANIFEST_PATH = PROJECT / "work" / "transition_rebuild_v4" / "production_manifest_bridges_v4.json"
KEYFRAME_DIR = PROJECT / "keyframes" / "bridges_v4"
QC_DIR = PROJECT / "qc" / "transition_rebuild_v4"
ARCHIVE_DIR = PROJECT / "archive" / "gohan_v3_owner_rejected_dry_cuts"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")


BOUNDARIES = [
    {
        "id": "C01_02", "from": "01", "to": "02", "start": 203, "end": 12,
        "title": "A ameaça vira esmagamento",
        "purpose": "Transformar a ameaça final de Cell na mesma descida brutal da bota, sem corte de pose.",
        "entry": "Perfect Cell's tailless body is already shifting forward and the same raised boot is already descending over Android 16's mechanical head while Gohan moves behind him.",
        "action": "The same boot continues one uninterrupted descent; Cell transfers body weight forward, the camera drops beside the boot and the first stones jump before contact.",
        "reaction": "Gohan lunges one urgent step while Android 16 remains purely mechanical and Cell never resets the leg.",
        "exit": "The boot is still descending with visible weight and the low camera is still accelerating directly into Take 02.",
        "change": "A ameaça estática torna-se uma descida física irreversível que já carrega o impacto seguinte.",
        "camera": "One low physical diagonal drop beside Cell's descending boot, with foreground rubble crossing faster than Cell, Gohan and the arena background.",
        "forbidden": "no completed stomp before the end, no repeated boot lift, no tail, no Cell dialogue, no blood, no organic Android 16 injury",
    },
    {
        "id": "C02_03", "from": "02", "to": "03", "start": 84, "end": 24,
        "title": "O impacto vira ruptura Super Saiyajin 2",
        "purpose": "Carregar a fissura e a onda de choque do esmagamento diretamente para a transformação de Gohan.",
        "entry": "The mechanical stomp consequence, racing floor crack, debris and camera velocity are already travelling toward ordinary Super Saiyan Gohan.",
        "action": "The same crack reaches Gohan's boots once; he plants without resetting, the pressure climbs through his body and blue-white electricity multiplies while the camera rises around him.",
        "reaction": "Tailless Perfect Cell slides backward under the same expanding pressure wave as Gohan's hair, clothes and aura sharpen progressively.",
        "exit": "Gohan's Super Saiyan 2 rupture and physical camera orbit are still accelerating into Take 03.",
        "change": "A consequência do esmagamento torna-se a primeira ruptura inequívoca de SSJ2 sem pausa contemplativa.",
        "camera": "The low crack-following dolly becomes one physical rising orbit around Gohan, preserving perspective change and three-plane debris motion.",
        "forbidden": "no second stomp, no tear effect, no instant body swap, no held transformation pose, no tail, no duplicate Gohan or Cell",
    },
    {
        "id": "C03_04", "from": "03", "to": "04", "start": 214, "end": 12,
        "title": "A transformação vira ataque aos Cell Juniors",
        "purpose": "Converter o auge móvel do SSJ2 na primeira arrancada contra exatamente dois Cell Juniors azuis.",
        "entry": "The same teenage Gohan has just completed Super Saiyan 2 and is still moving inside dense lightning, rising debris and an expanding crater pressure wave.",
        "action": "Gohan leans through the same forward pressure, launches once out of the crater and closes distance as exactly two small blue Cell Juniors converge from separate depths.",
        "reaction": "Both blue Juniors brace and separate under Gohan's approach while tailless Perfect Cell remains distant and does not replace them.",
        "exit": "Gohan and both blue Juniors are still converging at combat speed directly into Take 04.",
        "change": "A energia da transformação torna-se deslocamento ofensivo e estabelece os dois Juniors corretos no mesmo eixo de ação.",
        "camera": "One physical orbit exit becomes a fast forward chase through foreground slabs toward the two blue Juniors, never reversing the axis.",
        "forbidden": "no green Cell replacing a Junior, no more or fewer than two blue Juniors, no tail, no static hero pose, no teleport reset",
    },
    {
        "id": "C04_05", "from": "04", "to": "05", "start": 228, "end": 12,
        "title": "O último Junior vira confronto com Cell",
        "purpose": "Transformar o follow-through da eliminação dos Juniors no primeiro confronto direto com Perfect Cell.",
        "entry": "Gohan is still carrying forward velocity from eliminating the final small blue Cell Junior while fragments, lightning and the camera continue along the same direction.",
        "action": "Gohan completes that follow-through once, turns through the existing momentum and meets one full-size tailless Perfect Cell rushing into the opened corridor.",
        "reaction": "Perfect Cell raises one guard while sliding into range; no Junior grows into Cell and no body swaps identity.",
        "exit": "Gohan and full-size Perfect Cell remain inside one closing combat vector handed directly into Take 05.",
        "change": "A luta contra Juniors termina e a mesma trajetória abre o duelo principal sem salto de escala ou personagem.",
        "camera": "One lateral chase continues past the last blue fragments and arcs physically toward full-size Cell, retaining foreground occlusion and changing fighter scale.",
        "forbidden": "no green Cell Junior, no Junior morphing into Cell, no tail, no idle face-off, no duplicate fighter, no camera reversal",
    },
    {
        "id": "C05_06", "from": "05", "to": "06", "start": 215, "end": 12,
        "title": "O uppercut vira perseguição",
        "purpose": "Continuar o lançamento de Cell e transformar o follow-through de Gohan em perseguição física.",
        "entry": "Tailless Perfect Cell is already being launched by Gohan's connected uppercut while both bodies, lightning, dust and camera still rise.",
        "action": "The same launch arc continues once; Gohan never returns to guard and converts his rising follow-through into a forward aerial pursuit below Cell.",
        "reaction": "Cell rotates only along the received force and begins one defensive energy gesture without firing through Gohan.",
        "exit": "Gohan is still overtaking the airborne Cell as the camera accelerates through debris into Take 06.",
        "change": "O golpe conectado torna-se perseguição contínua, preservando a geografia e preparando a defesa de Cell.",
        "camera": "One rising physical crane becomes a forward chase under Cell's launch path, with nearby fragments, bodies and distant ruins moving at different rates.",
        "forbidden": "no repeated uppercut, no return to idle, no teleport, no tail, no energy crossing Gohan's body, no duplicate fighter",
    },
    {
        "id": "C06_07", "from": "06", "to": "07", "start": 228, "end": 12,
        "title": "O lançamento vira trocação",
        "purpose": "Carregar Cell através dos escombros e iniciar a trocação sem reposicionar os lutadores por corte.",
        "entry": "Perfect Cell and Gohan are still travelling through the wall breach with directional debris, camera velocity and SSJ2 lightning inherited from Take 06.",
        "action": "Cell twists through the same flight and commits one counter while Gohan closes continuously, redirects the arm and enters striking distance without stopping.",
        "reaction": "Cell's guard compresses and both bodies descend through the same rubble corridor under readable inertia.",
        "exit": "The counter and parry remain in active contact as the descending camera hands them into Take 07.",
        "change": "O lançamento através da arena torna-se combate corporal no mesmo corredor e no mesmo vetor.",
        "camera": "One fast physical chase through the breach becomes a descending side orbit around the live counter, with slabs crossing at different depths.",
        "forbidden": "no static face-off, no repeated counter, no teleport reset, no tail, no duplicate body, no anime or game rendering",
    },
    {
        "id": "C07_08", "from": "07", "to": "08", "start": 228, "end": 12,
        "title": "A pressão vira golpe de lançamento",
        "purpose": "Converter a pressão final de Gohan no golpe que lança Cell para o corredor do Kamehameha.",
        "entry": "Gohan is already advancing through Cell's collapsing guard while both bodies, dust, lightning and the orbiting camera retain forward velocity.",
        "action": "Gohan completes the same driving pressure once, steps through without resetting and turns the follow-through into one rising launch blow that lifts tailless Cell away.",
        "reaction": "Cell's guard breaks progressively and his full-size body begins one long readable flight toward the mountain corridor.",
        "exit": "Cell is still being launched and Gohan is still following through directly into Take 08 before the Kamehameha charge.",
        "change": "A trocação deixa de ser troca equilibrada e produz o lançamento irreversível que motiva o ataque final.",
        "camera": "One descending combat orbit becomes a low forward track along the launch vector, revealing the mountain corridor through changing foreground rubble.",
        "forbidden": "no early Kamehameha, no repeated launch, no idle charge pose, no tail, no teleport, no duplicate fighter, no yellow beam",
    },
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_frame(source: Path, frame: int, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-vf", f"select=eq(n\\,{frame})", "-vsync", "0", "-frames:v", "1", str(output),
    ], check=True)


def extract_context(source: Path, frame: int, output: Path) -> None:
    selected = [max(0, frame - 6), frame, frame + 6]
    expression = "+".join(f"eq(n\\,{value})" for value in selected)
    subprocess.run([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-vf", f"select={expression},scale=426:-2,tile=3x1", "-vsync", "0", "-frames:v", "1", str(output),
    ], check=True)


def connector_contract(item: dict, start_file: Path, end_file: Path, now: str) -> dict:
    start_sha = sha256(start_file)
    end_sha = sha256(end_file)
    intervals = {
        "early_0_30": "0-30%: inherit the exact outgoing body, object, effect and camera velocity; distance and force keep advancing without reset",
        "middle_30_70": f"30-70%: {item['action']}",
        "late_70_100": f"70-100%: {item['exit']}",
    }
    prompt = (
        f"ONE UNINTERRUPTED PHOTOREALISTIC LIVE-ACTION ACTION HANDOFF between the exact supplied moving frames. {item['entry']} "
        f"{item['action']} {item['reaction']} {item['exit']} Camera: {item['camera']} Preserve the exact teenage Gohan, tailless "
        "full-size Perfect Cell, established blue Cell Juniors only when present in the supplied frames, costumes, destroyed Cell Games arena, storm light, anatomy and spatial geography. "
        "Motion must remain useful through 0-30%, 30-70% and 70-100%; foreground, fighters, debris, cloth, hair, lightning and background must carry independent velocity. "
        f"FORBIDDEN: crossfade, freeze, hold, static tail, pose reset, motion reversal, full-frame occlusion hiding a swap, {item['forbidden']}, blood, gore, text, logo or watermark."
    )
    return {
        "id": item["id"],
        "slug": "V4_CONTINUO_" + item["id"] + "_" + item["title"].upper().replace(" ", "_"),
        "title": "V4 CONTÍNUO — " + item["id"] + " — " + item["title"],
        "sequence": float(item["from"]) + 0.5,
        "role": "continuous_action_connector",
        "is_transition": True,
        "transition": {"is_transition": True, "connects_from": item["from"], "connects_to": item["to"]},
        "objective": item["purpose"],
        "target_duration_seconds": 5.125,
        "editorial_use_seconds": 2.0,
        "status": "VIDEO_PENDING_GENERATION",
        "maestro_status": "READY",
        "render_authorized": True,
        "animation_prompt": prompt,
        "base_image": {
            "status": "approved_for_video",
            "file": str(start_file),
            "image_sha256": start_sha,
            "source": f"owner-approved Take {item['from']} moving frame {item['start']}",
            "approved_at": now,
        },
        "end_image": {"status": "approved_for_video", "file": str(end_file), "image_sha256": end_sha},
        "shot_contract": {
            "story_purpose": item["purpose"],
            "dramatic_question": "Como a ação já em movimento produz a próxima mudança sem parar na fronteira?",
            "story_change": item["change"],
            "distinct_story_events": 1,
            "reaction": item["reaction"],
            "cut_motivation": f"Handoff de movimento direto para o Take {item['to']}.",
            "duration_reason": "MiniMax H3 gera 124 quadros; a edição usará apenas o intervalo contínuo mais forte, como no master de Vejito.",
            "motion_beats": {"start": item["entry"], "middle": item["action"], "end": item["exit"]},
            "subject": "Exact established live-action Gohan SSJ state, tailless Perfect Cell and blue Cell Juniors required by this boundary.",
            "action": item["action"],
            "scene": "Exact established destroyed Cell Games arena with persistent damage, storm, dust and energy continuity.",
            "camera": {"movement": item["camera"], "angle": "continuity-driven dynamic angle", "lens": "cinematic 24-35 mm equivalent", "focus": "readable cause, contact and reaction across three-plane depth"},
            "lighting": "physical storm daylight with gold aura and blue-white lightning spill inherited from both moving anchors",
            "mood": "massive, fast, flamboyant, brutal and continuous",
            "visual_references": {
                "start_frame": str(start_file), "start_frame_file": str(start_file), "start_frame_approved": True, "start_frame_sha256": start_sha,
                "end_frame": str(end_file), "end_frame_file": str(end_file), "end_frame_approved": True, "end_frame_sha256": end_sha,
                "style_refs": [], "object_refs": [],
            },
            "transition_motion_contract": {
                "camera_evidence": {"movement": item["camera"], "physical_translation": True, "perspective_change": "Foreground rubble crosses fastest, bodies change overlap and scale at medium speed, and the ruined arena shifts slowest throughout the same vector."},
                "real_depth": {"foreground": "Fast rubble, dust and mechanical or energy fragments cross near the lens without hiding a pose swap.", "midground": item["action"], "background": "The destroyed arena, crater, mountains and storm retain geography and move at the slowest differential rate.", "differential_motion": "Foreground, fighters and distant environment maintain three separately readable velocities.", "occlusion_or_scale_change": "Physical camera translation changes overlap and scale without blackout, flash wipe or flat 2D parallax."},
                "internal_action": {"primary_event": item["action"], "independent_elements": ["body, hair, costume and armor keep inherited inertia", "debris, dust, lightning and persistent arena damage react independently"], "camera_independent": True},
                "progression": {"start": item["entry"], "middle": item["action"], "end": item["exit"], "end_state_change": item["change"], "exit_or_cut": f"direct moving-state handoff into Take {item['to']}"},
                "continuity": {
                    "editorial_method": "generated_action_connector", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True,
                    "entry_motion": item["entry"], "exit_motion": item["exit"], "interval_motion": intervals,
                    "moving_anchor_context": {
                        "start_source": f"Take {item['from']} native 24 fps frame {item['start']}, with visible frames before and after",
                        "start_has_motion_before_and_after": True,
                        "end_source": f"Take {item['to']} native 24 fps frame {item['end']}, with visible frames before and after",
                        "end_has_motion_before_and_after": True,
                    },
                    "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0,
                },
            },
            "negative_rules": [
                "no crossfade, xfade, freeze frame, hold or static tail",
                "no rollback, vector reversal, pose reset, guard reset or return to idle",
                "no repeated wind-up, repeated strike, repeated firing or repeated contact",
                "no tail, duplicate body, extra limb, identity drift, anime drawing, game render or plastic costume",
            ],
        },
        "video_generation": {
            "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot", "profile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0,
            "start_end_frame_enabled": True, "require_approved_start_frame": True, "require_approved_end_frame": True,
            "render_authorized": True, "visual_only_pass": True, "native_audio_authorized": False, "prompt": prompt,
        },
        "audio_direction": {"strategy": "model_independent_foley_after_picture_lock", "status": "BLOCKED_UNTIL_PICTURE_LOCK", "dialogue_generation_authorized": False},
        "qc": {
            "status": "pending_generated_connector_qc",
            "human_visual_approval": "pending",
            "transition_motion_gate": {
                "status": "pending", "evident_camera": False, "real_depth": False, "internal_action": False, "clear_progression": False,
                "continuous_action": False, "motion_across_all_intervals": False, "moving_anchor_context": False,
                "no_crossfade": False, "no_freeze": False, "no_static_tail": False, "no_reset": False,
                "evidence": "pending generated MP4 and frame-by-frame interval review",
            },
        },
    }


def main() -> None:
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    queue = read_json(QUEUE_PATH)
    manifest = read_json(PROJECT_MANIFEST_PATH)
    by_id = {str(take.get("id")): take for take in queue.get("takes", []) if isinstance(take, dict)}
    main_ids = {str(number).zfill(2) for number in range(1, 9)}
    if not main_ids.issubset(by_id):
        raise RuntimeError("Os oito takes principais não estão presentes.")
    for take_id in sorted(main_ids):
        if str(by_id[take_id].get("maestro_status") or "").upper() != "APPROVED":
            raise RuntimeError(f"Take principal {take_id} não está aprovado.")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, PROJECT_MANIFEST_PATH):
        backup = ARCHIVE_DIR / source.name
        if not backup.exists():
            shutil.copy2(source, backup)

    connectors = []
    contexts = []
    for item in BOUNDARIES:
        outgoing = by_id[item["from"]]
        incoming = by_id[item["to"]]
        outgoing_video = Path(str((outgoing.get("video") or {}).get("output_active") or ""))
        incoming_video = Path(str((incoming.get("video") or {}).get("output_active") or ""))
        if not outgoing_video.is_file() or not incoming_video.is_file():
            raise FileNotFoundError(f"Fonte ausente para {item['id']}")
        start_file = KEYFRAME_DIR / f"bridge_{item['from']}_{item['to']}_start.png"
        end_file = KEYFRAME_DIR / f"bridge_{item['from']}_{item['to']}_end.png"
        start_context = QC_DIR / f"{item['id']}_start_motion_context.jpg"
        end_context = QC_DIR / f"{item['id']}_end_motion_context.jpg"
        QC_DIR.mkdir(parents=True, exist_ok=True)
        extract_frame(outgoing_video, item["start"], start_file)
        extract_frame(incoming_video, item["end"], end_file)
        extract_context(outgoing_video, item["start"], start_context)
        extract_context(incoming_video, item["end"], end_context)
        connectors.append(connector_contract(item, start_file, end_file, now))
        contexts.append({"id": item["id"], "start": str(start_context), "end": str(end_context)})

    existing = {str(take.get("id")): take for take in queue.get("takes", []) if isinstance(take, dict)}
    for connector in connectors:
        previous = existing.get(connector["id"])
        if previous and isinstance(previous.get("video"), dict):
            connector["video"] = previous["video"]
            connector["maestro_status"] = previous.get("maestro_status", connector["maestro_status"])
            connector["status"] = previous.get("status", connector["status"])
            connector["qc"] = previous.get("qc", connector["qc"])
    queue["takes"] = [take for take in queue.get("takes", []) if str(take.get("id")) not in {item["id"] for item in connectors}] + connectors
    queue["status"] = "V4_CONTINUOUS_BRIDGES_READY_FOR_SERIAL_GENERATION"
    queue["render_authorized"] = True
    queue["render_authority"] = "Owner rejected V3 dry cuts and required the Vejito continuous-action method on 2026-08-20."
    queue["updated_at"] = now
    queue["story_batch_policy"] = {
        "enabled": True, "version": "gohan_v4_continuous_bridges_serial_v1", "batch_size": 1,
        "render_order": [item["id"] for item in connectors], "strict_contiguous": True,
        "require_all_base_images_ready": True, "fill_eligible_across_batches": False,
        "require_full_batch": True, "allow_incomplete_correction_batch": False,
        "control_surface": "owner_rejected_v3_auto_correct_with_vejito_continuity_method", "configured_at": now,
    }
    queue["continuous_action_contract"] = {
        "required": True, "generated_connector_required_between_takes": True, "crossfade_forbidden": True,
        "freeze_frame_forbidden": True, "static_tail_forbidden": True, "motion_handoff_required": True,
        "full_duration_motion_required": True, "three_interval_motion_required": True, "moving_transition_anchors_required": True,
    }
    queue["universal_transition_motion_gate"] = {"required": True}

    manifest["status"] = "V4_CONTINUOUS_BRIDGES_IN_PRODUCTION"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["render_authorized"] = True
    manifest["render_authority"] = queue["render_authority"]
    manifest["updated_at"] = now
    manifest["directed_correction_v4"] = {
        "reason": "Owner rejected V3 because dry cuts and fragmented direction do not match the continuous Vejito master.",
        "method": "seven MiniMax H3 generated action connectors from inherited moving frames, then two-second strongest intervals and RIFE60",
        "previous_master": "deliveries/gohan_ssj2_cell_visual_cut_v3_new_take02_720p60.mp4",
        "previous_master_status": "REJECTED_BY_OWNER_ROLLBACK_ONLY",
        "connector_ids": [item["id"] for item in connectors],
        "crossfade_frames": 0, "static_hold_frames": 0, "foley_status": "BLOCKED_UNTIL_NEW_PICTURE_LOCK",
    }

    bridge_manifest = {
        "schema_version": "gohan_ssj2_continuous_bridges_v4",
        "project_id": manifest.get("project_id"),
        "title": "Gohan SSJ2 — V4 — conectores de ação contínua como Vejito",
        "objective": "Substituir sete fronteiras secas por handoffs H3 que herdam movimento, câmera, profundidade e ação.",
        "updated_at": now,
        "universal_transition_motion_gate": {"required": True},
        "continuous_action_contract": queue["continuous_action_contract"],
        "takes": connectors,
        "anchor_motion_contexts": contexts,
        "gpu_policy": {"serial_only": True, "max_concurrent_video_jobs": 1},
        "audio": {"status": "BLOCKED_UNTIL_7_OF_7_PICTURE_LOCK"},
    }
    atomic_json(QUEUE_PATH, queue)
    atomic_json(PROJECT_MANIFEST_PATH, manifest)
    atomic_json(BRIDGE_MANIFEST_PATH, bridge_manifest)
    print(json.dumps({
        "ok": True, "connectors": [item["id"] for item in connectors],
        "bridgeManifest": str(BRIDGE_MANIFEST_PATH), "contexts": contexts,
        "archive": str(ARCHIVE_DIR),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
