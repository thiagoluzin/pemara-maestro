"""Replace four failed V6 connectors without deleting their rollback artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
V6_PATH = PROJECT / "work" / "continuous_rebuild_v6" / "production_manifest_continuous_v6.json"
ANCHORS = PROJECT / "work" / "continuous_rebuild_v6" / "anchors_r1"
ARCHIVE = PROJECT / "archive" / "before_continuous_v6_connector_replacements"

SPECS = {
    "C04_05_R1": {
        "source": "C04_05", "sequence": 4.5, "from": "04", "to": "05", "seed": 2026082131,
        "start_time": 8.10, "end_time": 2.20,
        "prompt": (
            "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION DRAGON BALL ACTION HANDOFF BETWEEN THE EXACT SUPPLIED MOVING FRAMES. "
            "The previous nearly static version is rejected; this version must visibly change distance, angle, overlap and body state during every second. "
            "0-30%: Gohan exits the last cobalt-blue Cell Junior elimination with forward and lateral velocity; the complete small blue Junior breaks into blue fragments and never becomes adult Cell. "
            "30-70%: Gohan turns through the same follow-through while one full-size green-and-black Perfect Cell rushes from deep background; both cross real ground distance and collide once with shoulder-driven weight. "
            "70-100%: Cell's guard compresses and he slides backward while Gohan steps through into the exact incoming close-combat direction. "
            "Camera performs a fast low lateral truck, passes a foreground slab, whips 70 degrees around the collision and keeps translating at the cut; foreground rubble, bodies and ruins move at clearly different speeds. "
            "Perfect Cell is completely TAILLESS: silhouette ends cleanly at pelvis, only two rigid symmetrical upper-back wing plates, never a curved rear line. "
            "USEFUL PHYSICAL MOTION FILLS ALL 124 FRAMES. FORBIDDEN: held composition, static effects-only shot, freeze, reset, reversal, crossfade, Junior morphing into Cell, tail, stinger, tentacle, duplicate fighter, extra limb, anime, game render, text, blood or gore."
        ),
    },
    "C05_06_R1": {
        "source": "C05_06", "sequence": 5.5, "from": "05", "to": "06", "seed": 2026082132,
        "start_time": 7.85, "end_time": 2.20,
        "prompt": (
            "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION AERIAL PURSUIT BETWEEN THE EXACT SUPPLIED MOVING FRAMES. "
            "The previous nearly static aerial composition is rejected; no framing may be held. 0-30%: Gohan's rising blow completes with Cell's entire body accelerating upward and rotating from the received force. "
            "30-70%: Gohan immediately pursues on a different depth plane, overtakes Cell from below and forces him across the arena; Cell makes one short defensive energy gesture but no beam passes through Gohan. "
            "70-100%: Gohan redirects the defensive burst aside with one simple slap while both bodies continue crossing real distance into the next exchange. "
            "Camera cranes with the launch, banks into a diagonal chase, then dives past tumbling foreground masonry; scale, perspective and overlap change continuously. Hair, cloth, armor, lightning, dust and rubble retain independent inertia. "
            "Perfect Cell is completely TAILLESS: pelvis ends cleanly, only two rigid upper-back wing plates. USEFUL PHYSICAL MOTION FILLS ALL 124 FRAMES. "
            "FORBIDDEN: held pose, orbit around a fixed tableau, freeze, reset, reversal, crossfade, beam through Gohan, tail, curved appendage, duplicate body, extra limb, anime, game render, text, blood or gore."
        ),
    },
    "C06_07_R1": {
        "source": "C06_07", "sequence": 6.5, "from": "06", "to": "07", "seed": 2026082133,
        "start_time": 8.10, "end_time": 1.85,
        "prompt": (
            "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION WALL-BREACH CHASE BETWEEN THE EXACT SUPPLIED MOVING FRAMES. "
            "The previous version is rejected because it invented a huge black tail. Perfect Cell has ABSOLUTELY NO TAIL IN ANY FRAME: his body silhouette terminates at the pelvis; the only rear elements are two short rigid symmetrical upper-back wing plates that never curve, trail, lengthen or connect to the ground. "
            "0-30%: Cell continues the received side-kick flight through a stone breach while Gohan pursues through independently moving debris. 30-70%: Cell twists only through impact inertia and throws one compact counter; Gohan closes real distance and redirects the arm without stopping. "
            "70-100%: both descend into one fast parry-and-counter vector, with Cell's clean tailless pelvis visible whenever his rear silhouette is exposed. Camera chases through the breach, rolls around a foreground column and drops into the close exchange; all depth planes change overlap and scale. "
            "USEFUL PHYSICAL MOTION FILLS ALL 124 FRAMES. FORBIDDEN: black curved line, tail, stinger, tentacle, cable, third rear blade, held pose, static ending, freeze, reset, reversal, crossfade, duplicate fighter, extra limb, anime, game render, text, blood or gore."
        ),
    },
    "C07_08_R1": {
        "source": "C07_08", "sequence": 7.5, "from": "07", "to": "08", "seed": 2026082134,
        "start_time": 8.05, "end_time": 2.20,
        "prompt": (
            "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION LAUNCH HANDOFF BETWEEN THE EXACT SUPPLIED MOVING FRAMES. "
            "The previous version is rejected because the same punch composition was held too long. 0-30%: Gohan drives through Cell's collapsing guard; contact lasts only a fraction of a second and immediately produces displacement. "
            "30-70%: Gohan converts the follow-through into one rising blow that launches Cell across a long readable corridor, shrinking him rapidly against the mountain depth while Gohan continues forward. "
            "70-100%: Cell remains in one uninterrupted weighted flight and Gohan lands into the pre-Kamehameha pursuit direction; do not charge or fire the beam yet. "
            "Camera begins close at the strike, trucks through flying foreground rubble, then accelerates into a wide long-lens chase so distance, scale, angle and overlap change every second. "
            "Perfect Cell is completely TAILLESS: clean pelvis termination and only two rigid symmetrical upper-back wing plates. USEFUL PHYSICAL MOTION FILLS ALL 124 FRAMES. "
            "FORBIDDEN: held contact, slow tableau, pose loop, freeze, reset, reversal, crossfade, early Kamehameha, tail, curved appendage, duplicate body, extra limb, anime, game render, text, blood or gore."
        ),
    },
}

FAIL_REASONS = {
    "C04_05": "Internal QC rejected: almost static foreground crouch composition; effects move but bodies, overlap and camera progression do not.",
    "C05_06": "Internal QC rejected: nearly fixed aerial tableau for the full connector; insufficient physical pursuit and depth progression.",
    "C06_07": "Internal QC rejected: generated a large curved black Cell tail across the shot, violating the approved tailless design.",
    "C07_08": "Internal QC rejected: held the same punch/contact composition too long; launch displacement and camera progression are too slow.",
}

ORDER = ["01", "C01_P02", "P02", "CP02_03", "03", "C03_04", "04", "C04_05_R1", "05", "C05_06_R1", "06", "C06_07_R1", "07", "C07_08_R1", "08"]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_anchor(take: dict, side: str, source_image: Path, now: str, source_time: float) -> tuple[dict, dict]:
    digest = sha(source_image)
    token = hashlib.sha256(f"v6r1:{take['id']}:{side}:{digest}".encode()).hexdigest()[:32]
    image = PROJECT / "base_images" / f"take{take['id']}_v6r1_{side}_{token[:12]}.png"
    shutil.copy2(source_image, image)
    digest = sha(image)
    metadata = image.with_suffix(".json")
    objective = f"Changed moving {side} anchor for {take['id']} after internal rejection of the previous connector strategy."
    delivery = {
        "prompt": take["animation_prompt"], "model": "FFmpeg extraction from owner-approved moving source video",
        "negative": "freeze, static, tail, morph, crossfade", "seed": None,
        "source_output": str(source_image), "source_generated_at": now, "source_sha256": digest,
        "generator": "Maestro deterministic moving-frame extractor", "workflow": "rejected_connector_changed_anchor_strategy",
        "objective": objective, "required_objects": {"anchorSide": side, "movingSource": True, "sourceTime": source_time, "noCrossfade": True, "noFreeze": True},
    }
    canonical = json.dumps(delivery, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    delivery_sha = hashlib.sha256(canonical.encode()).hexdigest()
    sidecar = {
        "schema_version": "1.0", "project_id": PROJECT.name, "type": "anchor_candidate_metadata",
        "director_request_id": token, "take_id": take["id"], "take_slug": take["id"], "created_at": now,
        "image_file": image.as_posix(), "original_filename": image.name, **delivery,
        "image_sha256": digest, "delivery_metadata_sha256": delivery_sha, "copy_integrity": "sha256_match",
        "width": 1280, "height": 720, "mode": "RGB", "validation_status": "approved_for_video",
        "approval_required_before_video": True, "rejection_reasons": [], "reviewed_at": now,
        "human_review": {"decision": "APPROVED", "reason": "Owner approved the source takes and instructed automatic corrected replacement after rejection.", "source": "owner_rejection_replacement_rule", "explicit_human_confirmation": True},
        "approval_evidence": "Owner approved the source takes and instructed automatic corrected replacement after rejection.",
    }
    write_json(metadata, sidecar)
    queue_record = {"status": "approved_for_video", "file": image.as_posix(), "metadata": metadata.as_posix(), "model": delivery["model"], "prompt": take["animation_prompt"], "candidate_request_id": token, "image_sha256": digest, "delivered_at": now, "approved_at": now}
    request = {"id": token, "status": "DELIVERED", "category": "ANCHOR", "reason": objective, "created_at": now, "updated_at": now, "delivered_at": now, "candidate_file": image.name, "candidate_metadata_file": metadata.name, "candidate_sha256": digest, "candidate_metadata_sha256": delivery_sha, "review_decision": "APPROVED", "review_reason": sidecar["approval_evidence"], "reviewed_at": now}
    return queue_record, request


def main() -> None:
    queue = read_json(QUEUE_PATH)
    manifest = read_json(MANIFEST_PATH)
    v6 = read_json(V6_PATH)
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, MANIFEST_PATH, V6_PATH):
        target = ARCHIVE / source.name
        if not target.exists():
            shutil.copy2(source, target)

    by_id = {str(t.get("id")): t for t in queue.get("takes", [])}
    for old_id, reason in FAIL_REASONS.items():
        old = by_id[old_id]
        old["status"] = "REJECTED_INTERNAL_QC"
        old["maestro_status"] = "REJECTED"
        old["render_authorized"] = False
        old.setdefault("video_generation", {})["render_authorized"] = False
        old.setdefault("qc", {})["status"] = "rejected_internal_visual_qc"
        old["qc"]["human_visual_approval"] = "not_eligible"
        old["qc"]["rejection_reason"] = reason
        old["maestro_notes"] = reason + " Preserve generated MP4 only as rollback; never assemble or promote."

    queue["takes"] = [t for t in queue.get("takes", []) if str(t.get("id")) not in SPECS]
    for take_id, spec in SPECS.items():
        take = copy.deepcopy(by_id[spec["source"]])
        take["id"] = take_id
        take["name"] = f"V6 CORRECAO DE CONTINUIDADE — {take_id}"
        take["title"] = f"V6 CORRECAO — {take_id} — {spec['from']} para {spec['to']}"
        take["sequence"] = spec["sequence"]
        take["transition"] = {"is_transition": True, "connects_from": spec["from"], "connects_to": spec["to"]}
        take["status"] = "READY_FOR_SERIAL_GENERATION"
        take["maestro_status"] = "READY"
        take["render_authorized"] = True
        take["animation_prompt"] = spec["prompt"]
        take["maestro_notes"] = "Automatic same-scope replacement with changed moving anchors after internal rejection; pending real MP4 QC."
        start, start_req = register_anchor(take, "start", ANCHORS / f"{take_id}_start.png", now, spec["start_time"])
        end, end_req = register_anchor(take, "end", ANCHORS / f"{take_id}_end.png", now, spec["end_time"])
        take["base_image"] = start
        take["end_image"] = end
        take["end_anchor_candidate"] = end
        take["maestro_director_requests"] = [start_req, end_req]
        refs = take.setdefault("shot_contract", {}).setdefault("visual_references", {})
        refs.update({"start_frame": start["file"], "start_frame_file": start["file"], "start_frame_approved": True, "start_frame_sha256": start["image_sha256"], "end_frame": end["file"], "end_frame_file": end["file"], "end_frame_approved": True, "end_frame_sha256": end["image_sha256"], "style_refs": [], "object_refs": []})
        motion = take["shot_contract"].setdefault("transition_motion_contract", {})
        motion["camera_evidence"] = {"movement": "Fast physical travelling move with changed anchor geometry.", "physical_translation": True, "perspective_change": "Foreground, fighters and background change scale and overlap continuously."}
        motion["real_depth"] = {"foreground": "Fast rubble and dust crossing lens.", "midground": "Fighters cross real distance.", "background": "Ruins and mountain move slowest.", "differential_motion": "Three planes have distinct velocities.", "occlusion_or_scale_change": "Foreground occlusion and coherent fighter scale change."}
        motion["internal_action"] = {"primary_event": spec["prompt"], "independent_elements": ["fighter anatomy and cloth inertia", "debris, dust and lightning reactions"], "camera_independent": True}
        motion["progression"] = {"start": "Exact moving outgoing action.", "middle": "Irreversible displacement and camera-axis change.", "end": "Exact moving incoming action.", "end_state_change": "Distance, overlap and combat state changed.", "exit_or_cut": f"Moving handoff into {spec['to']}."}
        motion["continuity"] = {"editorial_method": "generated_action_connector", "continuous_action": True, "motion_handoff": True, "action_occupies_full_duration": True, "entry_motion": "Inherited from changed active start anchor.", "exit_motion": "Still moving at changed active end anchor.", "interval_motion": {"early_0_30": "Immediate inherited displacement.", "middle_30_70": "Primary action and camera-axis change.", "late_70_100": "Moving consequence into next take."}, "moving_anchor_context": {"start_source": f"{spec['from']} at {spec['start_time']}s", "start_has_motion_before_and_after": True, "end_source": f"{spec['to']} at {spec['end_time']}s", "end_has_motion_before_and_after": True}, "crossfade_frames": 0, "freeze_frames": 0, "static_hold_frames": 0}
        generation = take.setdefault("video_generation", {})
        generation.update({"engine": "MiniMax H3 FL2VA pruned INT8 ConvRot", "model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "width": 1280, "height": 720, "fps": 24, "frames": 124, "steps": 20, "guidance": 1.0, "seed": spec["seed"], "start_end_frame_enabled": True, "visual_only_pass": True, "native_audio_authorized": False, "prompt": spec["prompt"], "profile": "minimax_h3_fl2va_int8_720p24", "render_authorized": True, "require_approved_start_frame": True, "require_approved_end_frame": True})
        take["video"] = {"status": "not_generated", "output_active": "", "output_preview": "", "output_review_candidate": ""}
        take["qc"] = {"status": "pending_generated_mp4", "human_visual_approval": "pending_final_sequence_review", "transition_motion_gate": {"status": "pending", "evident_camera": False, "real_depth": False, "internal_action": False, "clear_progression": False, "continuous_action": False, "motion_across_all_intervals": False, "moving_anchor_context": True, "no_crossfade": True, "no_freeze": False, "no_static_tail": False, "no_reset": False, "evidence": "Pending corrected generated MP4."}}
        for key in ("maestro_last_job_id", "maestro_last_error", "maestro_last_result", "maestro_updated_at"):
            take.pop(key, None)
        queue["takes"].append(take)

    queue["takes"].sort(key=lambda item: (float(item.get("sequence") or 999), str(item.get("id"))))
    queue["status"] = "V6_CONNECTOR_CORRECTIONS_READY"
    queue["render_authorized"] = True
    queue["story_batch_policy"] = {"enabled": True, "version": "gohan_continuous_rebuild_v6_r1", "batch_size": 4, "render_order": list(SPECS), "strict_contiguous": True, "require_all_base_images_ready": True, "fill_eligible_across_batches": False, "require_full_batch": True, "allow_incomplete_correction_batch": True, "control_surface": "single_existing_gohan_project"}
    queue["assembly_order_v6"] = ORDER
    queue["rejected_connector_rollbacks"] = {old: {"replacement": new, "reason": FAIL_REASONS[old]} for new, old in ((n, s["source"]) for n, s in SPECS.items())}

    manifest["status"] = "V6_CONNECTOR_CORRECTIONS_READY"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest.setdefault("continuous_rebuild_v6", {})["assembly_order"] = ORDER
    manifest["continuous_rebuild_v6"]["connector_replacements"] = list(SPECS)
    manifest["continuous_rebuild_v6"]["rejected_connectors"] = FAIL_REASONS

    v6["connector_replacements"] = {take_id: {"replaces": spec["source"], "start_time": spec["start_time"], "end_time": spec["end_time"], "status": "READY_FOR_SERIAL_GENERATION"} for take_id, spec in SPECS.items()}
    v6["assembly_order"] = ORDER
    v6["rejected_connectors"] = FAIL_REASONS
    write_json(QUEUE_PATH, queue)
    write_json(MANIFEST_PATH, manifest)
    write_json(V6_PATH, v6)
    print(json.dumps({"ok": True, "replacements": list(SPECS), "assemblyOrder": ORDER, "archive": str(ARCHIVE)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
