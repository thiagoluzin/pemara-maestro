from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE = PROJECT / "take_queue.json"
MANIFEST = PROJECT / "project_manifest.json"
ARCHIVE = PROJECT / "archive" / "gohan_visual_cut_v2_owner_rejected_motion_v3"


PROMPT = (
    "Create one uninterrupted 5.166667-second photorealistic live-action 16:9 cinematic microtake between the exact approved first and last pictures. "
    "Preserve the same teenage Gohan, tailless Perfect Cell, mechanical Android 16 remains, costumes, destroyed Cell Games arena, storm lighting and spatial geography. "
    "Perfect Cell has absolutely no tail, stinger, rear appendage, tentacle or cable; his silhouette ends cleanly at the pelvis with only the two rigid upper-back wing plates. "
    "The action must fill every frame and never become a living photo. Camera: begin with a fast low physical dolly descending beside Cell's already-moving boot, absorb the impact with a short lateral displacement, then accelerate along the newly propagating ground crack and rise physically toward Gohan; maintain strong changing perspective, foreground occlusion and differential parallax, never zoom-only. "
    "Timeline 0-30% (0.0-1.55s): Cell's raised boot is already descending with body weight and armor inertia; Gohan lunges one urgent step from the background; loose stones, dust, cloth, hair and Cell's back plates move independently. The mechanical head remains intact until contact. "
    "Timeline 30-70% (1.55-3.62s): exactly one heavy stomp crushes only metal, ceramic casing and circuits, never flesh or blood. Mechanical fragments burst sideways, a circular dust shockwave crosses the arena and a deep crack races toward Gohan. Cell's boot rebounds and his torso recoils continuously without repeating or resetting. Gohan plants his foot and converts shock into visible anger. "
    "Timeline 70-100% (3.62-5.166667s): the camera overtakes the moving crack and rises toward Gohan as he snaps into a stronger stance; wind violently lifts his hair and clothing, stones spiral upward, his golden aura punches outward, and the first blue-white electrical arc lashes across the arena. The pressure wave forces Cell to slide backward while shielding his face. Reach the approved final picture only in the last 0.10 seconds and cut while Gohan, Cell, lightning, debris, dust and camera still have visible velocity. "
    "Three distinct irreversible events: stomp impact, crack propagation, anger shockwave. Make the physics massive, fast, flamboyant and cinematic, with readable cause and reaction. "
    "Forbidden: static hold, frozen tail, early final pose, idle stance, repeated stomp, pose reset, simple pan or zoom, crossfade, tear or liquid effect, dialogue, Cell lip movement, anime drawing, cel shading, game render, plastic costume, blood, gore, organic Android 16 injury, duplicate character, extra fighter, extra limb, Goku apparition, Kamehameha, typography, logo, watermark or interface."
)


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE, MANIFEST):
        destination = ARCHIVE / f"{source.stem}.before_take02_microtake_v3{source.suffix}"
        if not destination.exists():
            shutil.copy2(source, destination)

    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    take = next(item for item in queue["takes"] if str(item.get("id")) == "02")
    video_generation = take.setdefault("video_generation", {})
    video_generation.update(
        {
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
            "render_authorized": True,
            "visual_only_pass": True,
            "native_audio_authorized": False,
            "prompt": PROMPT,
        }
    )
    take.update(
        {
            "status": "PLANNED",
            "maestro_status": "PLANNED",
            "render_authorized": True,
            "target_duration_seconds": 5.0,
            "native_duration_seconds": 5.166667,
            "animation_prompt": PROMPT,
            "maestro_last_error": "",
            "maestro_updated_at": now,
            "directed_correction": {
                "attempt": 1,
                "authorized_at": now,
                "reason": "Owner rejected the full cut because the interval near 14 seconds and the overall early sequence were too static.",
                "editorial_method": "short_dense_microtake_between_same_owner_approved_anchors",
                "previous_approved_video_preserved_in_output_history_on_candidate_registration": True,
                "previous_final_cut": "deliveries/gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4",
                "previous_final_cut_status": "REJECTED_BY_OWNER",
                "result": "PENDING_SERIAL_GPU_GENERATION_AND_HUMAN_REVIEW",
            },
        }
    )
    shot = take.setdefault("shot_contract", {})
    shot.update(
        {
            "story_purpose": "Turn Android 16's mechanical destruction into Gohan's immediate irreversible anger without a static aftermath.",
            "dramatic_question": "Will Gohan's contained grief explode before Cell can regain balance?",
            "story_change": "Cell's boot is descending over the intact mechanical head -> the head is mechanical debris, the arena is split and Gohan's first SSJ2 arc drives Cell backward.",
            "reaction": "Gohan converts shock into a violent forward stance while Cell recoils and shields his face.",
            "cut_motivation": "Cut on the still-expanding aura shockwave and moving lightning into the transformation microtake.",
            "duration_reason": "5.166667 seconds is the minimum interval for one stomp, one propagating crack and one anger shockwave without padding.",
            "distinct_story_events": 3,
            "motion_beats": {
                "start": "Boot descends and Gohan lunges.",
                "middle": "Mechanical stomp impact and ground crack propagate.",
                "end": "Gohan's anger shockwave and first electrical arc force Cell backward.",
            },
        }
    )
    qc = take.setdefault("qc", {})
    qc.update(
        {
            "status": "corrected_microtake_ready_for_serial_generation",
            "human_visual_approval": "replacement_video_pending",
            "transition_motion_gate": {
                "status": "contract_pass_pending_generation",
                "duration_seconds": 5.166667,
                "frames": 124,
                "required_motion_intervals": ["0-30%", "30-70%", "70-100%"],
                "evident_camera": True,
                "real_depth": True,
                "internal_action": True,
                "clear_progression": True,
                "crossfade_frames": 0,
                "freeze_frames_allowed": 0,
                "static_hold_frames_allowed": 0,
            },
            "audio_gate": "BLOCKED_UNTIL_REPLACEMENT_PICTURE_APPROVAL",
        }
    )
    queue.update(
        {
            "status": "TAKE02_MICROTAKE_V3_READY_FOR_SERIAL_GENERATION",
            "render_authorized": True,
            "render_authority": "Owner rejected V2 motion and standing correction rule authorizes a same-scope replacement; anchors remain the exact owner-approved start/end images.",
            "updated_at": now,
        }
    )
    atomic_json(QUEUE, queue)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    manifest.update(
        {
            "status": "TAKE02_MICROTAKE_V3_READY_FOR_SERIAL_GENERATION",
            "maestro_status": "IN_PROGRESS",
            "render_authorized": True,
            "updated_at": now,
        }
    )
    atomic_json(MANIFEST, manifest)
    print(
        json.dumps(
            {
                "ok": True,
                "projectId": PROJECT.name,
                "takeId": "02",
                "frames": 124,
                "fps": 24,
                "nativeDurationSeconds": 5.166667,
                "anchors": {
                    "start": take.get("base_image", {}).get("file"),
                    "end": shot.get("visual_references", {}).get("end_frame_file"),
                    "approval": "reused exact owner-approved anchors",
                },
                "archive": str(ARCHIVE),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
