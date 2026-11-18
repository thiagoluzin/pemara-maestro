"""Prepare the single-project V6 continuous rebuild without promoting any review candidate."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
WORK = PROJECT / "work" / "continuous_rebuild_v6"
ANCHORS = WORK / "anchors"
MANIFEST = WORK / "production_manifest_continuous_v6.json"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")

SOURCES = {
    "01": PROJECT / "takes" / "maestro_generated" / "take_01_6ce4a308ecd04870_minimax_h3_preview.mp4",
    "P02": PROJECT / "takes" / "maestro_generated" / "take_P02_0efeb200cef748e4_minimax_h3_preview.mp4",
    "03": PROJECT / "takes" / "maestro_generated" / "take_03_35326e8f0f95479f_minimax_h3_preview.mp4",
    "04": PROJECT / "takes" / "maestro_generated" / "take_04_multi_anchor_motion_retimed_v2.mp4",
    "05": PROJECT / "takes" / "maestro_generated" / "take_05_bc8cfbb387724791_minimax_h3_preview.mp4",
    "06": PROJECT / "takes" / "maestro_generated" / "take_06R1_magic_slap_corrected_v2.mp4",
    "07": PROJECT / "takes" / "maestro_generated" / "take_07_frenetic_multi_anchor_v3.mp4",
    "08": PROJECT / "takes" / "maestro_generated" / "take_08_motion_retimed_v2.mp4",
}

SOURCE_TRIMS = {
    "01": [0.0, 4.75], "P02": [0.08, 4.92], "03": [0.85, 8.70], "04": [0.15, 9.65],
    "05": [0.20, 9.10], "06": [0.15, 9.45], "07": [0.10, 9.55], "08": [0.15, 9.45],
}

BOUNDARIES = [
    {
        "id": "C01_P02", "from": "01", "to": "P02", "start_time": 4.55, "end_time": 0.10,
        "purpose": "Convert Android 16's final warning and Cell's looming threat into the same boot descending on the mechanical head.",
        "action": "Cell transfers weight forward and the same tailless lower leg drives one boot straight down while Gohan accelerates and the low camera drops toward the impact axis.",
        "reaction": "Android 16 remains purely mechanical and Gohan lunges in alarm; stones jump before contact.",
        "exit": "The boot is still descending directly over the crown and the camera is still dropping into P02.",
    },
    {
        "id": "CP02_03", "from": "P02", "to": "03", "start_time": 4.70, "end_time": 0.90,
        "purpose": "Carry the crushed mechanical debris and Gohan's forward launch directly into the Super Saiyan 2 rupture.",
        "action": "The same crack reaches Gohan, who plants without stopping; forward momentum compresses into a violent gold pressure surge and multiplying blue-white lightning.",
        "reaction": "Dust, broken circuitry, cloth, hair and arena slabs recoil independently while the camera rises around Gohan.",
        "exit": "Gohan's transformation and the rising physical orbit are still accelerating into Take 03.",
    },
    {
        "id": "C03_04", "from": "03", "to": "04", "start_time": 8.45, "end_time": 0.30,
        "purpose": "Turn the moving SSJ2 climax into the first attack on exactly two small blue Cell Juniors.",
        "action": "Gohan leans through the existing pressure wave, launches from the crater and closes on exactly two separate cobalt-blue Cell Juniors at different depths.",
        "reaction": "Both Juniors brace and separate while tailless full-size Perfect Cell remains distant and distinct.",
        "exit": "Gohan and both blue Juniors remain converging at combat speed into Take 04.",
    },
    {
        "id": "C04_05", "from": "04", "to": "05", "start_time": 9.35, "end_time": 0.35,
        "purpose": "Turn the final Junior elimination into the first direct clash with full-size Perfect Cell.",
        "action": "Gohan completes the same follow-through, turns through its momentum and meets one tailless full-size Perfect Cell rushing through the opened corridor.",
        "reaction": "Cell raises one guard while sliding into range; no Junior grows or morphs into Cell.",
        "exit": "Gohan and Cell remain inside one closing combat vector into Take 05.",
    },
    {
        "id": "C05_06", "from": "05", "to": "06", "start_time": 8.85, "end_time": 0.30,
        "purpose": "Continue Cell's uppercut launch as Gohan converts his follow-through into aerial pursuit.",
        "action": "The same launch arc continues; Gohan never resets guard and overtakes Cell from below while Cell begins one defensive energy gesture.",
        "reaction": "Cell rotates only along the received force as armor, dust, lightning and rubble retain inertia.",
        "exit": "Gohan is still overtaking airborne Cell as the camera accelerates into Take 06.",
    },
    {
        "id": "C06_07", "from": "06", "to": "07", "start_time": 9.15, "end_time": 0.25,
        "purpose": "Carry both fighters through the wall breach and enter the fast exchange without repositioning them by cut.",
        "action": "Cell twists through the same flight and commits one counter; Gohan closes continuously, redirects the arm and enters striking distance.",
        "reaction": "Cell's guard compresses as both bodies descend through the same moving rubble corridor.",
        "exit": "Counter and parry remain in active contact as the camera descends into Take 07.",
    },
    {
        "id": "C07_08", "from": "07", "to": "08", "start_time": 9.25, "end_time": 0.30,
        "purpose": "Convert Gohan's final pressure into the launch blow that opens the Kamehameha corridor.",
        "action": "Gohan steps through Cell's collapsing guard without reset and turns the follow-through into one rising blow that launches tailless Cell toward the mountain.",
        "reaction": "Cell's guard breaks progressively and his full-size body begins one long readable flight.",
        "exit": "Cell is still being launched and Gohan is still following through into Take 08 before the beam charge.",
    },
]

CONTINUOUS_POLICY = {
    "required": True, "generated_connector_required_between_takes": True,
    "crossfade_forbidden": True, "freeze_frame_forbidden": True,
    "static_tail_forbidden": True, "motion_handoff_required": True,
    "full_duration_motion_required": True, "three_interval_motion_required": True,
    "moving_transition_anchors_required": True,
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(source: Path, at: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at:.3f}",
        "-i", str(source), "-frames:v", "1", "-vf", "scale=1280:720:flags=lanczos", str(output),
    ], check=True)


def connector(item: dict, now: str) -> dict:
    start = ANCHORS / f"{item['id']}_start.png"
    end = ANCHORS / f"{item['id']}_end.png"
    extract(SOURCES[item["from"]], item["start_time"], start)
    extract(SOURCES[item["to"]], item["end_time"], end)
    prompt = (
        "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION ACTION HANDOFF BETWEEN THE EXACT SUPPLIED MOVING FRAMES. "
        f"Purpose: {item['purpose']} 0-30%: inherit every visible body, object, effect and camera velocity without reset. "
        f"30-70%: {item['action']} Reaction: {item['reaction']} 70-100%: {item['exit']} "
        "Camera physically translates through the ruined arena; foreground rubble crosses fastest, fighters change overlap and scale at medium speed, and distant ruins move slowest. "
        "Useful motion fills the complete duration. Preserve the exact teenage Gohan, established costume and SSJ state, purely mechanical Android 16 only where present, exactly two small cobalt-blue Cell Juniors only where present, and one full-size tailless Perfect Cell only where present. "
        "FORBIDDEN: crossfade, freeze, hold, pose reset, reversal, flash wipe hiding a swap, tail, pointed tip, curved appendage, duplicate fighter, extra limb, character morph, static ending, anime, game render, blood, gore, text, logo or watermark."
    )
    contract = {
        "camera_evidence": {"movement": "Physical travelling move continuing the source velocity through foreground rubble and fighter space.", "physical_translation": True, "perspective_change": "Foreground, fighters and ruined background change overlap and scale at distinct rates."},
        "real_depth": {"foreground": "Rubble and dust cross close to lens.", "midground": item["action"], "background": "Ruined arena and storm move at the slowest rate.", "differential_motion": "Three depth planes retain different velocities.", "occlusion_or_scale_change": "Physical translation changes overlap and coherent scale without blackout."},
        "internal_action": {"primary_event": item["action"], "independent_elements": ["fighters, hair, costume and armor retain physical inertia", "debris, dust, lightning and persistent arena damage react independently"], "camera_independent": True},
        "progression": {"start": "Inherited outgoing motion from the exact source frame.", "middle": item["action"], "end": item["exit"], "end_state_change": item["purpose"], "exit_or_cut": f"Moving handoff into {item['to']}."},
        "continuity": {"editorial_method": "generated_action_connector", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True,
            "entry_motion": "Exact visible outgoing velocities continue from frame one.", "exit_motion": item["exit"],
            "interval_motion": {"early_0_30": "Source motion continues and distance closes.", "middle_30_70": item["action"], "late_70_100": item["exit"]},
            "moving_anchor_context": {"start_source": f"{item['from']} at {item['start_time']:.2f}s with visible motion around it", "start_has_motion_before_and_after": True, "end_source": f"{item['to']} at {item['end_time']:.2f}s with visible motion around it", "end_has_motion_before_and_after": True},
            "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0},
    }
    return {
        "id": item["id"], "sequence": float(len(item["id"])), "role": "continuous_action_connector", "is_transition": True,
        "transition": {"is_transition": True, "connects_from": item["from"], "connects_to": item["to"]},
        "status": "READY_FOR_SERIAL_GENERATION", "render_authorized": True,
        "animation_prompt": prompt,
        "base_image": {"status": "approved_for_video", "file": str(start), "image_sha256": digest(start), "source": str(SOURCES[item["from"]]), "source_time": item["start_time"], "approved_at": now},
        "end_image": {"status": "approved_for_video", "file": str(end), "image_sha256": digest(end), "source": str(SOURCES[item["to"]]), "source_time": item["end_time"], "approved_at": now},
        "shot_contract": {"story_purpose": item["purpose"], "dramatic_question": "How does existing motion cause the next irreversible change?", "story_change": item["purpose"], "distinct_story_events": 1, "reaction": item["reaction"], "cut_motivation": f"Moving handoff into {item['to']}", "duration_reason": "H3 native window; editorial uses only its strongest continuous 1.25-2.0 seconds.", "transition_motion_contract": contract},
        "video_generation": {"engine": "MiniMax H3 FL2VA pruned INT8 ConvRot", "model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0, "seed": 2026082100 + len(item["id"]), "start_end_frame_enabled": True, "visual_only_pass": True, "native_audio_authorized": False, "prompt": prompt},
        "qc": {"status": "pending_generated_connector_qc", "human_visual_approval": "pending_final_sequence_review", "transition_motion_gate": {"status": "pending", "evident_camera": False, "real_depth": False, "internal_action": False, "clear_progression": False, "continuous_action": False, "motion_across_all_intervals": False, "moving_anchor_context": False, "no_crossfade": False, "no_freeze": False, "no_static_tail": False, "no_reset": False, "evidence": "Pending generated MP4."}},
    }


def main() -> None:
    for name, source in SOURCES.items():
        if not source.is_file():
            raise FileNotFoundError(f"Missing source {name}: {source}")
    if digest(SOURCES["01"]) != "213a2122e04668b2eea2b6bf7a144cf8143ef6942371219bf0a02ac23b677750":
        raise RuntimeError("Owner-approved Take 01 source changed.")
    if digest(SOURCES["P02"]) != "36d87f72d283c37cff5d3d31279cc41c7ec8e90372606fcd11c31061af977836":
        raise RuntimeError("Inspected P02 source changed.")
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    takes = [connector(item, now) for item in BOUNDARIES]
    payload = {
        "schema_version": "gohan_ssj2_continuous_rebuild_v6", "project_id": PROJECT.name,
        "status": "CONNECTOR_PILOT_READY", "render_authorized": True,
        "sequence_stakes": "Android 16's destruction irreversibly triggers Gohan's SSJ2 transformation and domination of Cell.",
        "universal_transition_motion_gate": {"required": True}, "continuous_action_contract": CONTINUOUS_POLICY,
        "source_order": list(SOURCES), "source_files": {k: str(v) for k, v in SOURCES.items()},
        "source_sha256": {k: digest(v) for k, v in SOURCES.items()}, "source_trims": SOURCE_TRIMS,
        "takes": takes, "gpu_policy": {"serial_only": True, "pilot_first": "C01_P02", "max_concurrent_video_jobs": 1},
        "assembly": {"status": "BLOCKED_UNTIL_ALL_CONNECTORS_QC", "crossfade_frames": 0, "freeze_frames": 0, "audio": "none; Foley after picture lock"},
    }
    WORK.mkdir(parents=True, exist_ok=True)
    temp = MANIFEST.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(MANIFEST)
    print(json.dumps({"ok": True, "manifest": str(MANIFEST), "connectors": [t["id"] for t in takes], "pilot": "C01_P02"}, indent=2))


if __name__ == "__main__":
    main()
