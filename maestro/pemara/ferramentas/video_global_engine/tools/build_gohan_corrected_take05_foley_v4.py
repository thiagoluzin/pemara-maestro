"""Build the corrected Gohan SSJ2 full-film review candidate.

This V4 is deliberately surgical: it preserves the accepted V3 picture before
and after Take 05, replaces only the rejected Take 05 range with the approved
live-action I2VA replacement, rebuilds Foley only for the changed combat block,
and leaves final promotion behind an owner visual/listening gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from array import array
from pathlib import Path


BASE_SCRIPT = Path(__file__).with_name("build_gohan_transition_accel_foley_v3.py")
SPEC = importlib.util.spec_from_file_location("gohan_v3_builder", BASE_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load base builder: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

PROJECT = base.PROJECT
WORK = PROJECT / "work" / "corrected_take05_foley_v4"
QC = WORK / "qc"
EDIT = PROJECT / "edit"
DELIVERIES = PROJECT / "deliveries"
AUDIO_ROOT = PROJECT / "audio" / "video_sound" / "final_corrected_take05_v4"
ROLLBACK = PROJECT / "archive" / "before_corrected_take05_foley_v4_20260821"

V3_PICTURE = (
    PROJECT
    / "work"
    / "transition_accel_foley_v3"
    / "gohan_ssj2_transition_accel_picture_720p60_v3.mp4"
)
V3_PICTURE_SHA256 = "b5aa8ef5d38258848d949a09c3bdd0b29204dff3ada063c132be11850a32859b"
V3_FINAL = (
    DELIVERIES
    / "GOHAN_SSJ2_ANDROID16_TRANSICOES_RAPIDAS_FOLEY_720P60_APROVACAO_V3.mp4"
)
REPLACEMENT = (
    PROJECT
    / "takes"
    / "maestro_generated"
    / "take_05_i2va_liveaction_long_v2_9p8s_60fps_vejito_speed.mp4"
)
REPLACEMENT_SHA256 = "088335986ea21e623953547add172297e6d14f35bc1e75652779e154f3d83a5a"

PICTURE = WORK / "gohan_ssj2_corrected_take05_picture_720p60_v4.mp4"
PICTURE_MANIFEST = EDIT / "GOHAN_SSJ2_ANDROID16_TAKE05_CORRIGIDO_PICTURE_V4.json"
PICTURE_QC = QC / "picture_director_qc_v4.json"
PICTURE_CONTACT = QC / "picture_contact_24frames_v4.jpg"
PICTURE_JOINS = QC / "take05_splice_boundaries_2x12frames_v4.jpg"
FOLEY_RAW_BUS = WORK / "foley_bus_raw_48k_s24_v4.wav"
FOLEY_BUS = WORK / "foley_bus_loudness_48k_s24_v4.wav"
FINAL = (
    DELIVERIES
    / "GOHAN_SSJ2_ANDROID16_TAKE05_CORRIGIDO_FOLEY_720P60_APROVACAO_V4.mp4"
)
FINAL_MANIFEST = EDIT / "GOHAN_SSJ2_ANDROID16_TAKE05_CORRIGIDO_FOLEY_720P60_V4.json"
FINAL_AUDIO = WORK / "final_mix_analysis_48k_s24_v4.wav"

FPS = 60
V3_FRAMES = 2434
V3_TAKE05_START = 1496
V3_TAKE05_END = 2024
REPLACEMENT_FRAMES = 588
EDGE_SOURCE_FRAMES = 18
EDGE_OUTPUT_FRAMES = 12
REPLACEMENT_OUTPUT_FRAMES = (
    REPLACEMENT_FRAMES - 2 * (EDGE_SOURCE_FRAMES - EDGE_OUTPUT_FRAMES)
)
OUTPUT_FRAMES = V3_TAKE05_START + REPLACEMENT_OUTPUT_FRAMES + (V3_FRAMES - V3_TAKE05_END)
OUTPUT_DURATION = OUTPUT_FRAMES / FPS
JOIN_BOUNDARIES = [V3_TAKE05_START, V3_TAKE05_START + REPLACEMENT_OUTPUT_FRAMES]
CHUNK_CUTS = [0, 334, 668, 1184, 1496, JOIN_BOUNDARIES[1], OUTPUT_FRAMES]

PROMPTS = {item["id"]: item["prompt"] for item in base.CHUNKS}
CHUNKS = [
    {"id": "01_android16_dialogue", "start": CHUNK_CUTS[0], "end": CHUNK_CUTS[1], "prompt": PROMPTS["01_android16_dialogue"]},
    {"id": "02_crush_and_transformation", "start": CHUNK_CUTS[1], "end": CHUNK_CUTS[2], "prompt": PROMPTS["02_crush_and_transformation"]},
    {"id": "03_cell_juniors", "start": CHUNK_CUTS[2], "end": CHUNK_CUTS[3], "prompt": PROMPTS["03_cell_juniors"]},
    {"id": "04_energy_slap", "start": CHUNK_CUTS[3], "end": CHUNK_CUTS[4], "prompt": PROMPTS["04_energy_slap"]},
    {"id": "05_close_combat", "start": CHUNK_CUTS[4], "end": CHUNK_CUTS[5], "prompt": PROMPTS["05_close_combat"]},
    {"id": "06_kamehameha_mountain", "start": CHUNK_CUTS[5], "end": CHUNK_CUTS[6], "prompt": PROMPTS["06_kamehameha_mountain"]},
]
REUSE_CHUNKS = {
    "01_android16_dialogue",
    "02_crush_and_transformation",
    "03_cell_juniors",
    "04_energy_slap",
    "06_kamehameha_mountain",
}
V3_AUDIO_ROOT = PROJECT / "audio" / "video_sound" / "final_transition_v3"


def configure_base() -> None:
    base.WORK = WORK
    base.QC = QC
    base.EDIT = EDIT
    base.DELIVERIES = DELIVERIES
    base.AUDIO_ROOT = AUDIO_ROOT
    base.ROLLBACK = ROLLBACK
    base.SOURCE = V3_PICTURE
    base.SOURCE_SHA256 = V3_PICTURE_SHA256
    base.SOURCE_FRAMES = V3_FRAMES
    base.PICTURE = PICTURE
    base.PICTURE_MANIFEST = PICTURE_MANIFEST
    base.PICTURE_QC = PICTURE_QC
    base.PICTURE_CONTACT = PICTURE_CONTACT
    base.PICTURE_JOINS = PICTURE_JOINS
    base.PICTURE_JOINS_2 = PICTURE_JOINS
    base.FOLEY_RAW_BUS = FOLEY_RAW_BUS
    base.FOLEY_BUS = FOLEY_BUS
    base.FINAL = FINAL
    base.FINAL_MANIFEST = FINAL_MANIFEST
    base.FINAL_AUDIO = FINAL_AUDIO
    base.FPS = FPS
    base.OUTPUT_FRAMES = OUTPUT_FRAMES
    base.OUTPUT_DURATION = OUTPUT_DURATION
    base.SOURCE_BOUNDARIES = JOIN_BOUNDARIES
    base.OUTPUT_BOUNDARIES = JOIN_BOUNDARIES
    base.CHUNK_CUTS = CHUNK_CUTS
    base.CHUNKS = CHUNKS


def preserve_rollback() -> dict:
    ROLLBACK.mkdir(parents=True, exist_ok=True)
    items = [
        PROJECT / "project_manifest.json",
        PROJECT / "production_manifest.json",
        PROJECT / "take_queue.json",
        base.FINAL_MANIFEST.with_name(
            "GOHAN_SSJ2_ANDROID16_TRANSICOES_RAPIDAS_FOLEY_720P60_V3.json"
        ),
    ]
    copied = []
    for source in items:
        if not source.is_file():
            continue
        target = ROLLBACK / source.name
        if not target.exists():
            shutil.copy2(source, target)
        copied.append(str(target))
    payload = {
        "created_at": base.now_local(),
        "reason": "Preserve V3 and replace only the owner-rejected Take 05 range.",
        "v3_picture": str(V3_PICTURE),
        "v3_picture_sha256": base.sha256(V3_PICTURE),
        "v3_final": str(V3_FINAL),
        "v3_final_preserved_in_place": V3_FINAL.is_file(),
        "replacement": str(REPLACEMENT),
        "replacement_sha256": base.sha256(REPLACEMENT),
        "copied_manifests": copied,
        "media_deleted": False,
    }
    base.atomic_json(ROLLBACK / "rollback_record_v4.json", payload)
    return payload


def update_take05_candidate_state() -> dict:
    """Register internal passes without claiming owner approval of the video."""
    contact = PROJECT / "qc" / "take05_i2va_liveaction_long_v2" / "delivery60_contact_16frames.jpg"
    tail_sheet = PROJECT / "qc" / "take05_i2va_liveaction_long_v2" / "delivery60_tail_24frames.jpg"
    pipeline = Path(str(REPLACEMENT) + ".review_pipeline.json")
    for required in (contact, tail_sheet, pipeline):
        if not required.is_file():
            raise RuntimeError(f"Missing corrected Take 05 QC artifact: {required}")
    rel_video = str(REPLACEMENT.relative_to(PROJECT)).replace("\\", "/")
    rel_contact = str(contact.relative_to(PROJECT)).replace("\\", "/")
    rel_tail = str(tail_sheet.relative_to(PROJECT)).replace("\\", "/")
    rel_pipeline = str(pipeline.relative_to(PROJECT)).replace("\\", "/")
    candidate = {
        "take_id": "05",
        "engine": "MiniMax H3 I2VA + Vejito Practical-RIFE 4.25",
        "status": "OWNER_DIRECT_FULL_FILM_REVIEW_AUTHORIZED",
        "output": rel_video,
        "sha256": REPLACEMENT_SHA256,
        "fps": 60,
        "frames": REPLACEMENT_FRAMES,
        "duration_seconds": REPLACEMENT_FRAMES / FPS,
        "source_duration_seconds": 12.25,
        "speed_factor": 1.25,
        "contact_sheet": rel_contact,
        "tail_contact_sheet": rel_tail,
        "pipeline_sidecar": rel_pipeline,
        "registered_at": base.now_local(),
        "owner_final_video_approval": False,
        "assembly_scope": "candidate_full_film_review_only",
    }
    touched = []
    for name in ("production_manifest.json", "take_queue.json"):
        path = PROJECT / name
        manifest = base.load(path)
        take = next(
            (
                item
                for item in manifest.get("takes", [])
                if str(item.get("id") or item.get("take_id") or "") == "05"
            ),
            None,
        )
        if not isinstance(take, dict):
            raise RuntimeError(f"Take 05 missing from {name}")
        take["status"] = "CORRECTED_VIDEO_INTERNAL_PASS_DIRECT_FULL_FILM_REVIEW"
        take["maestro_status"] = "REVIEW_PENDING"
        take["native_duration_seconds"] = 12.25
        take["release_gates"] = {
            "art_direction": "PASS",
            "cinematic": "PASS",
            "motion": "PASS",
            "technical": "PASS",
            "human": "OWNER_AUTHORIZED_DIRECT_FULL_FILM_REVIEW",
            "video_contact_sheet": rel_contact,
        }
        art_gate = take.setdefault("art_direction_gate", {})
        art_gate["video_style_status"] = "PASS_PHOTOREALISTIC_LIVE_ACTION"
        art_gate["forbidden_style_detected"] = False
        video = take.setdefault("video", {})
        history = video.setdefault("output_history", [])
        if not any(str(item.get("sha256") or "") == REPLACEMENT_SHA256 for item in history):
            history.append(
                {
                    "path": str(REPLACEMENT),
                    "sha256": REPLACEMENT_SHA256,
                    "role": "corrected_take05_candidate_for_direct_full_film_review",
                    "fps": 60,
                    "frames": REPLACEMENT_FRAMES,
                    "duration_seconds": REPLACEMENT_FRAMES / FPS,
                    "owner_approval": False,
                    "assembly_scope": "candidate_review_only",
                }
            )
        video.update(
            {
                "status": "internal_qc_pass_owner_direct_full_film_review_authorized",
                "file": str(REPLACEMENT),
                "output_active": str(REPLACEMENT),
                "output_review_candidate": str(REPLACEMENT),
                "sha256": REPLACEMENT_SHA256,
                "preview_model": candidate["engine"],
                "width": 1280,
                "height": 720,
                "fps": 60,
                "frames": REPLACEMENT_FRAMES,
                "duration_seconds": REPLACEMENT_FRAMES / FPS,
                "speed_factor": 1.25,
                "pipeline_sidecar": str(pipeline),
                "crossfade_frames": 0,
                "freeze_frames_added": 0,
                "static_hold_frames_added": 0,
                "owner_final_video_approval": False,
            }
        )
        qc = take.setdefault("qc", {})
        qc.update(
            {
                "status": "INTERNAL_PASS_PENDING_EXACT_FULL_FILM_OWNER_REVIEW",
                "auto_approved": False,
                "technical_delivery": "PASS_1280X720_60FPS_588F_9.8S_PRACTICAL_RIFE425_NVENC",
                "human_visual_approval": "PENDING_EXACT_V4_FULL_FILM_PLAYBACK",
                "director_visual_review": "PASS",
                "art_direction_review": "PASS_PHOTOREALISTIC_ZERO_TAIL_TWO_DORSAL_WINGS",
                "motion_review": "PASS_CONTINUOUS_ACTIVE_ACTION",
                "contact_sheet": rel_contact,
                "tail_contact_sheet": rel_tail,
                "owner_direct_full_film_review_authorized": True,
                "owner_instruction": "gerar o take e devolver video completo com foley",
                "updated_at": base.now_local(),
            }
        )
        generation = take.setdefault("generation", {})
        generation.update(
            {
                "status": "RENDERED_INTERNAL_PASS_OWNER_DIRECT_FULL_FILM_REVIEW_AUTHORIZED",
                "native_output": str(
                    PROJECT
                    / "work"
                    / "take05_i2va_liveaction_long_v2"
                    / "native"
                    / "take05_i2va_liveaction_long_v2_294f_24fps.mp4"
                ),
                "output": str(REPLACEMENT),
                "output_sha256": REPLACEMENT_SHA256,
                "speed_factor": 1.25,
                "owner_approval": False,
            }
        )
        take["qc_status"] = "internal_pass_pending_exact_full_film_owner_review"
        take["maestro_notes"] = (
            "Take 05 corrigido em live action: Cell adulto, sem rabo e com duas asas dorsais. "
            "Passou QC interno; proprietário autorizou revisão direta no filme completo; "
            "aprovação humana do vídeo continua pendente."
        )
        manifest["updated_at"] = base.now_local()
        assembly = manifest.setdefault("assembly", {})
        assembly["candidate_review_override"] = {
            "status": "OWNER_AUTHORIZED_DIRECT_FULL_FILM_REVIEW",
            "take_id": "05",
            "take_sha256": REPLACEMENT_SHA256,
            "final_promotion_allowed": False,
            "owner_approval_claimed": False,
        }
        base.atomic_json(path, manifest)
        touched.append(str(path))
    project_path = PROJECT / "project_manifest.json"
    project = base.load(project_path)
    candidates = [
        item
        for item in project.get("take_review_candidates", [])
        if str(item.get("take_id") or "") != "05"
    ]
    candidates.append(candidate)
    project["take_review_candidates"] = candidates
    project["status"] = "TAKE05_CORRECTED_VIDEO_DIRECT_FULL_FILM_REVIEW_AUTHORIZED"
    project["maestro_status"] = "IN_PROGRESS"
    project["updated_at"] = base.now_local()
    project["direct_full_film_review"] = {
        "authorized": True,
        "take_id": "05",
        "take_sha256": REPLACEMENT_SHA256,
        "owner_instruction": "gerar o take e devolver video completo com foley",
        "owner_final_approval": False,
    }
    base.atomic_json(project_path, project)
    touched.append(str(project_path))
    record = {
        "created_at": base.now_local(),
        "status": "REGISTERED_PENDING_EXACT_FULL_FILM_OWNER_REVIEW",
        "candidate": candidate,
        "manifests": touched,
        "owner_approval_claimed": False,
    }
    base.atomic_json(QC / "take05_candidate_registration_v4.json", record)
    return record


def validate_candidate_assembly_gate() -> dict:
    """Allow only the owner's explicit direct-full-film review exception."""
    completed = subprocess.run(
        [
            sys.executable,
            str(base.GATE),
            str(PROJECT / "production_manifest.json"),
            "--stage",
            "assembly",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse sequence gate output: {completed.stdout} {completed.stderr}"
        ) from exc
    if completed.returncode == 0 and payload.get("status") == "PASS":
        payload["candidate_review_exception_used"] = False
        return payload
    errors = [str(item) for item in payload.get("errors", [])]
    allowed = (
        "take[05] não tem aprovação visual final no Maestro",
        "take[05].release_gates.human não está APPROVED",
    )
    unexpected = [item for item in errors if item not in allowed]
    production = base.load(PROJECT / "production_manifest.json")
    take = next(
        item for item in production.get("takes", []) if str(item.get("id") or "") == "05"
    )
    direct_authorized = (
        (take.get("release_gates") or {}).get("human")
        == "OWNER_AUTHORIZED_DIRECT_FULL_FILM_REVIEW"
        and (take.get("qc") or {}).get("owner_direct_full_film_review_authorized") is True
        and (take.get("qc") or {}).get("owner_instruction")
        == "gerar o take e devolver video completo com foley"
    )
    if unexpected or not direct_authorized or not errors:
        raise RuntimeError(
            json.dumps(
                {
                    "gate": payload,
                    "unexpected_errors": unexpected,
                    "direct_full_film_review_authorized": direct_authorized,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    result = {
        **payload,
        "status": "PASS_FOR_CANDIDATE_FULL_FILM_REVIEW_ONLY",
        "candidate_review_exception_used": True,
        "owner_approval_claimed": False,
        "final_promotion_allowed": False,
        "accepted_human_pending_errors": errors,
    }
    base.atomic_json(QC / "sequence_gate_candidate_review_v4.json", result)
    return result


def make_splice_sheet() -> None:
    terms = []
    for boundary in JOIN_BOUNDARIES:
        terms.extend(f"eq(n\\,{frame})" for frame in range(boundary - 6, boundary + 6))
    base.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(PICTURE),
            "-vf",
            f"select='{'+'.join(terms)}',scale=320:180,tile=12x2:nb_frames=24",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(PICTURE_JOINS),
        ],
        timeout=180,
    )


def build_picture() -> dict:
    configure_base()
    if base.sha256(V3_PICTURE) != V3_PICTURE_SHA256:
        raise RuntimeError("Accepted V3 picture hash drift.")
    if base.sha256(REPLACEMENT) != REPLACEMENT_SHA256:
        raise RuntimeError("Approved corrected Take 05 hash drift.")
    if base.sha256(base.VOICE) != base.VOICE_SHA256:
        raise RuntimeError("Approved Android 16 voice hash drift.")
    v3_info = base.validate_video(V3_PICTURE, frames=V3_FRAMES, audio=True)
    replacement_info = base.validate_video(
        REPLACEMENT, frames=REPLACEMENT_FRAMES, audio=False
    )
    voice_info = base.probe_audio(base.VOICE)
    if voice_info["sample_rate"] != 48000 or voice_info["channels"] != 2:
        raise RuntimeError(f"Unexpected approved voice format: {voice_info}")
    rollback = preserve_rollback()
    for folder in (WORK, QC, EDIT, DELIVERIES, AUDIO_ROOT):
        folder.mkdir(parents=True, exist_ok=True)
    take_registration = update_take05_candidate_state()
    sequence_gate = validate_candidate_assembly_gate()
    graph = (
        f"[0:v]trim=start_frame=0:end_frame={V3_TAKE05_START},"
        "setpts=PTS-STARTPTS[pre];"
        f"[1:v]trim=start_frame=0:end_frame={EDGE_SOURCE_FRAMES},"
        "select='not(eq(mod(n\\,3)\\,2))',setpts=N/(60*TB)[head];"
        f"[1:v]trim=start_frame={EDGE_SOURCE_FRAMES}:"
        f"end_frame={REPLACEMENT_FRAMES-EDGE_SOURCE_FRAMES},"
        "setpts=PTS-STARTPTS[mid];"
        f"[1:v]trim=start_frame={REPLACEMENT_FRAMES-EDGE_SOURCE_FRAMES}:"
        f"end_frame={REPLACEMENT_FRAMES},"
        "select='not(eq(mod(n\\,3)\\,2))',setpts=N/(60*TB)[tail];"
        "[head][mid][tail]concat=n=3:v=1:a=0[replacement];"
        f"[0:v]trim=start_frame={V3_TAKE05_END}:end_frame={V3_FRAMES},"
        "setpts=PTS-STARTPTS[post];"
        "[pre][replacement][post]concat=n=3:v=1:a=0,format=yuv420p[v];"
        f"[2:a]apad,atrim=duration={OUTPUT_DURATION:.9f},"
        "asetpts=PTS-STARTPTS[a]"
    )
    if not PICTURE.is_file():
        part = PICTURE.with_name(f".{PICTURE.stem}.{os.getpid()}.part.mp4")
        try:
            base.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(V3_PICTURE),
                    "-i",
                    str(REPLACEMENT),
                    "-i",
                    str(base.VOICE),
                    "-filter_complex",
                    graph,
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                    "-r",
                    str(FPS),
                    "-fps_mode",
                    "cfr",
                    "-frames:v",
                    str(OUTPUT_FRAMES),
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "p7",
                    "-tune",
                    "hq",
                    "-profile:v",
                    "high",
                    "-pix_fmt",
                    "yuv420p",
                    "-rc",
                    "vbr",
                    "-cq",
                    "15",
                    "-b:v",
                    "0",
                    "-maxrate",
                    "24M",
                    "-bufsize",
                    "48M",
                    "-g",
                    "120",
                    "-bf",
                    "2",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "320k",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-metadata",
                    "title=Gohan SSJ2 - Take 05 corrected - picture 720p60 V4",
                    "-metadata",
                    "comment=Surgical Take 05 replacement; no crossfade; pending owner review",
                    "-movflags",
                    "+faststart",
                    str(part),
                ],
                timeout=1200,
            )
            base.validate_video(part, frames=OUTPUT_FRAMES, audio=True)
            os.replace(part, PICTURE)
        finally:
            part.unlink(missing_ok=True)
    picture_info = base.validate_video(PICTURE, frames=OUTPUT_FRAMES, audio=True)
    base.make_contact(PICTURE, PICTURE_CONTACT)
    make_splice_sheet()
    freezes = base.freeze_events(PICTURE, OUTPUT_DURATION)
    black = base.black_events(PICTURE)
    long_freezes = [item for item in freezes if float(item.get("duration") or 0) >= 0.15]
    if long_freezes:
        raise RuntimeError(f"Corrected picture contains freeze events: {long_freezes}")
    if black:
        raise RuntimeError(f"Corrected picture contains black events: {black}")
    edit_contract = {
        "method": "surgical_take05_picture_replacement",
        "accepted_v3_preserved_before_frame": V3_TAKE05_START,
        "accepted_v3_resumes_from_source_frame": V3_TAKE05_END,
        "replacement_source_frames": REPLACEMENT_FRAMES,
        "replacement_output_frames": REPLACEMENT_OUTPUT_FRAMES,
        "boundary_cadence": {
            "source_frames_each_edge": EDGE_SOURCE_FRAMES,
            "output_frames_each_edge": EDGE_OUTPUT_FRAMES,
            "speed_factor": 1.5,
        },
        "dialogue_and_lipsync_untouched_until_frame": 334,
        "crossfade_frames": 0,
        "freeze_frames_added": 0,
        "static_hold_frames_added": 0,
        "rejected_ref2va_used": False,
        "new_take05_internal_cuts": 0,
        "join_boundaries": JOIN_BOUNDARIES,
    }
    payload = {
        "schema_version": "1.0",
        "project_id": base.PROJECT_ID,
        "display_name": "FILME COMPLETO - TAKE 05 CORRIGIDO - PICTURE 720P60 V4",
        "status": "DIRECTOR_PASS_FOR_FOLEY_CANDIDATE",
        "created_at": base.now_local(),
        "owner_request": "Generate corrected Take 05 and return full video with Foley.",
        "owner_review": "PENDING_EXACT_V4_PLAYBACK",
        "owner_anchor_approval_inherited": True,
        "owner_final_video_approval": False,
        "sources": {
            "accepted_v3": v3_info,
            "corrected_take05": replacement_info,
            "approved_android16_voice": voice_info,
        },
        "picture_v4": picture_info,
        "edit_contract": edit_contract,
        "technical_qc": {
            "decode": "PASS",
            "constant_fps": True,
            "freeze_events_at_least_0p15_seconds": freezes,
            "black_events": black,
            "contact_sheet": str(PICTURE_CONTACT),
            "splice_sheet": str(PICTURE_JOINS),
            "sequence_regression_gate": sequence_gate,
        },
        "take05_candidate_registration": take_registration,
        "rollback": rollback,
        "next_gate": "FOLEY_REBUILD_FOR_CHANGED_TAKE05_THEN_OWNER_REVIEW",
    }
    base.atomic_json(PICTURE_MANIFEST, payload)
    base.atomic_json(
        PICTURE_QC,
        {
            "schema_version": "1.0",
            "project_id": base.PROJECT_ID,
            "status": "DIRECTOR_PASS_FOR_FOLEY_CANDIDATE",
            "created_at": base.now_local(),
            "picture": str(PICTURE),
            "picture_sha256": picture_info["sha256"],
            "technical_visual_qc": "PASS",
            "owner_approval": False,
            "owner_review": "PENDING_EXACT_V4_PLAYBACK",
            "contact_sheet": str(PICTURE_CONTACT),
            "splice_sheet": str(PICTURE_JOINS),
        },
    )
    return payload


def old_candidate_record(chunk_id: str) -> tuple[dict, Path]:
    sidecars = list((V3_AUDIO_ROOT / chunk_id).glob("*/candidate.json"))
    if len(sidecars) != 1:
        raise RuntimeError(f"Expected one V3 Foley sidecar for {chunk_id}: {sidecars}")
    record = base.load(sidecars[0])
    audio = Path(str(record["audio"])).resolve(strict=True)
    if base.sha256(audio) != str(record.get("audio_sha256") or ""):
        raise RuntimeError(f"V3 Foley hash drift for {chunk_id}")
    return record, audio


def generate_foley_chunks() -> list[dict]:
    configure_base()
    picture_qc = base.load(PICTURE_QC)
    if picture_qc.get("status") != "DIRECTOR_PASS_FOR_FOLEY_CANDIDATE":
        raise RuntimeError("Picture gate has not released Foley.")
    if base.sha256(PICTURE) != str(picture_qc.get("picture_sha256") or ""):
        raise RuntimeError("Picture changed after technical/director QC.")
    studio_root = base.ROOT / "services" / "studio"
    if str(studio_root) not in sys.path:
        sys.path.insert(0, str(studio_root))
    from video_sound import VideoSoundRequest, build_default_registry

    provider = build_default_registry(base.ROOT).get("hunyuan_video_foley_xxl")
    status = provider.status()
    if not status.get("configured"):
        raise RuntimeError(json.dumps(status, ensure_ascii=False))
    results = []
    for index, spec in enumerate(CHUNKS, start=1):
        video, video_info = base.extract_chunk(spec)
        duration = (int(spec["end"]) - int(spec["start"])) / FPS
        if spec["id"] in REUSE_CHUNKS:
            old, audio = old_candidate_record(str(spec["id"]))
            audio_info = base.probe_audio(audio)
            if abs(float(audio_info["duration_seconds"]) - duration) > 0.03:
                raise RuntimeError(
                    f"Reusable Foley duration mismatch for {spec['id']}: {audio_info}"
                )
            record = {
                **old,
                "schema_version": "1.0",
                "status": "PENDING_HUMAN_LISTENING",
                "created_at": base.now_local(),
                "job_id": f"gohan-v4-reuse-{index:02d}-{spec['id']}",
                "timeline_frames": [spec["start"], spec["end"]],
                "timeline_seconds": [spec["start"] / FPS, spec["end"] / FPS],
                "source_video": str(video),
                "source_video_sha256": video_info["sha256"],
                "audio": str(audio),
                "audio_sha256": audio_info["sha256"],
                "audio_qc": audio_info,
                "reuse": {
                    "reason": "Picture frames and timing for this story block are unchanged from V3.",
                    "v3_sidecar": str(
                        next((V3_AUDIO_ROOT / str(spec["id"])).glob("*/candidate.json"))
                    ),
                    "v3_audio_sha256": audio_info["sha256"],
                },
                "auto_attach": False,
                "auto_approval": False,
            }
            output_dir = AUDIO_ROOT / str(spec["id"]) / str(record["job_id"])
            base.atomic_json(output_dir / "candidate.json", record)
            print(f"FOLEY chunk {index}/6 reused unchanged: {spec['id']}", flush=True)
            results.append(record)
            continue
        job_id = f"gohan-v4-{index:02d}-{spec['id']}"
        output_dir = AUDIO_ROOT / str(spec["id"]) / job_id
        sidecar = output_dir / "candidate.json"
        candidate = output_dir / "candidate.wav"
        if candidate.is_file() and sidecar.is_file():
            recorded = base.load(sidecar)
            if (
                str(recorded.get("source_video_sha256") or "") == video_info["sha256"]
                and str(recorded.get("audio_sha256") or "") == base.sha256(candidate)
            ):
                print(f"FOLEY chunk {index}/6 resumed: {spec['id']}", flush=True)
                results.append(recorded)
                continue
            raise RuntimeError(f"Existing V4 Foley checkpoint drift: {output_dir}")
        print(f"FOLEY chunk {index}/6 generating: {spec['id']} ({duration:.3f}s)", flush=True)
        result = provider.generate(
            VideoSoundRequest(
                job_id=job_id,
                source_video=video,
                output_dir=output_dir,
                prompt=str(spec["prompt"]),
                negative_prompt=base.NEGATIVE_PROMPT,
                duration_seconds=duration,
                seed=2026082145,
            ),
            progress_cb=lambda percent, message: print(
                f"FOLEY chunk 5/6 {percent}% {message}", flush=True
            ),
            cancel_event=threading.Event(),
        )
        audio_info = base.probe_audio(result.audio_path)
        if audio_info["sample_rate"] != 48000 or audio_info["channels"] != 2:
            raise RuntimeError(f"Unexpected generated Foley format: {audio_info}")
        record = {
            "schema_version": "1.0",
            "status": "PENDING_HUMAN_LISTENING",
            "created_at": base.now_local(),
            "job_id": job_id,
            "chunk_id": spec["id"],
            "timeline_frames": [spec["start"], spec["end"]],
            "timeline_seconds": [spec["start"] / FPS, spec["end"] / FPS],
            "prompt": spec["prompt"],
            "negative_prompt": base.NEGATIVE_PROMPT,
            "provider_id": result.provider_id,
            "model": result.model,
            "source_video": str(video),
            "source_video_sha256": result.source_video_sha256,
            "audio": str(result.audio_path),
            "audio_sha256": audio_info["sha256"],
            "audio_qc": audio_info,
            "generation": result.generation,
            "auto_attach": False,
            "auto_approval": False,
        }
        base.atomic_json(sidecar, record)
        results.append(record)
        print("FOLEY chunk 5/6 done", flush=True)
    return results


def silence_events(path: Path) -> list[dict]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-50dB:d=0.25",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", completed.stderr)]
    ends = [
        (float(a), float(b))
        for a, b in re.findall(
            r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)",
            completed.stderr,
        )
    ]
    events = []
    for index, start in enumerate(starts):
        if index < len(ends):
            end, duration = ends[index]
            events.append({"start": start, "end": end, "duration": duration})
        else:
            events.append({"start": start, "end": OUTPUT_DURATION, "duration": OUTPUT_DURATION - start})
    return events


def transient_analysis(path: Path) -> dict:
    def decode_float(sample_rate: int, channels: int) -> array:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-vn",
                "-ac",
                str(channels),
                "-ar",
                str(sample_rate),
                "-f",
                "f32le",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
            shell=False,
        )
        decoded = array("f")
        decoded.frombytes(completed.stdout)
        if sys.byteorder != "little":
            decoded.byteswap()
        return decoded

    # Peak and clipping must be measured before sample-rate conversion.  The
    # 12 kHz analysis proxy can overshoot during resampling and is valid only
    # for coarse transient timing.
    native_samples = decode_float(48000, 2)
    peak = max((abs(value) for value in native_samples), default=0.0)
    clipping_samples = sum(1 for value in native_samples if abs(value) >= 0.999)
    samples = decode_float(12000, 1)
    window = 120
    envelope = []
    for start in range(0, len(samples) - window + 1, window):
        block = samples[start : start + window]
        envelope.append(sum(abs(value) for value in block) / window)
    onsets = []
    refractory = 8
    last = -refractory
    for index in range(1, len(envelope)):
        previous = max(envelope[index - 1], 1e-6)
        current = envelope[index]
        if current >= 0.035 and current / previous >= 2.2 and index - last >= refractory:
            onsets.append(round(index * 0.01, 3))
            last = index
    return {
        "decoded_peak_linear": peak,
        "native_48k_clipping_sample_count_at_0p999": clipping_samples,
        "native_48k_sample_count": len(native_samples),
        "measured_transient_onsets_seconds": onsets[:120],
        "onset_count": len(onsets),
        "analysis_sample_rate": 12000,
        "analysis_window_seconds": 0.01,
    }


def register_full_film_review_candidate(payload: dict) -> dict:
    """Expose one full-film candidate without bypassing Take 05 owner approval."""
    studio_root = base.ROOT / "services" / "studio"
    if str(studio_root) not in sys.path:
        sys.path.insert(0, str(studio_root))
    from video_projects import get_project_assembly_readiness, project_view

    readiness = get_project_assembly_readiness(base.PROJECTS, base.PROJECT_ID)
    blockers = readiness.get("blockers") or []
    allowed = all(
        str(item.get("code") or "") == "TAKE_NOT_APPROVED"
        and str(item.get("takeId") or "") == "05"
        for item in blockers
    )
    if not blockers or not allowed:
        raise RuntimeError(
            json.dumps(
                {
                    "message": "Unexpected readiness state for direct full-film review.",
                    "readiness": readiness,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    project_path = PROJECT / "project_manifest.json"
    manifest = base.load(project_path)
    direct = manifest.get("direct_full_film_review")
    if not isinstance(direct, dict) or not direct.get("authorized"):
        raise RuntimeError("Direct full-film review is not authorized in project manifest.")
    if str(direct.get("take_sha256") or "") != REPLACEMENT_SHA256:
        raise RuntimeError("Direct-review authorization points to another Take 05 hash.")
    previous = manifest.get("final_output")
    if isinstance(previous, dict) and str(previous.get("sha256") or "") != str(
        payload["final"]["sha256"]
    ):
        history = manifest.setdefault("final_output_history", [])
        if not isinstance(history, list):
            history = []
            manifest["final_output_history"] = history
        history.append({**previous, "superseded_at": base.now_local()})
        del history[:-20]
    final = {
        "file": str(FINAL.relative_to(PROJECT)).replace("\\", "/"),
        "review_file": str(FINAL.relative_to(PROJECT)).replace("\\", "/"),
        "display_name": payload["display_name"],
        "title": "GOHAN SSJ2 - FILME COMPLETO CORRIGIDO + FALA DO 16 + FOLEY - 720P60",
        "duration_seconds": OUTPUT_DURATION,
        "width": 1280,
        "height": 720,
        "fps": 60,
        "frames": OUTPUT_FRAMES,
        "video_codec": "h264_nvenc_picture_bitstream_copy",
        "audio_codec": "aac_320k_android16_dialogue_plus_hunyuan_foley",
        "sha256": payload["final"]["sha256"],
        "qc_status": "TECHNICAL_PASS_CANDIDATE_REVIEW_ONLY_TAKE05_HUMAN_PENDING",
        "purpose": "single corrected 720p60 full-film candidate for direct owner review",
        "foley_status": "CANDIDATE_PENDING_HUMAN_LISTENING",
        "human_review_required": True,
        "auto_approval": False,
        "candidate_review_only": True,
        "final_promotion_allowed": False,
        "owner_direct_full_film_review_authorized": True,
        "take05_owner_approval_claimed": False,
        "take05_sha256": REPLACEMENT_SHA256,
        "crossfade_frames": 0,
        "freeze_frames_added": 0,
        "static_hold_frames_added": 0,
        "approved_dialogue_source": str(base.VOICE),
        "approved_dialogue_source_sha256": base.sha256(base.VOICE),
        "technical_manifest": str(FINAL_MANIFEST.relative_to(PROJECT)).replace("\\", "/"),
        "picture_director_qc": str(PICTURE_QC.relative_to(PROJECT)).replace("\\", "/"),
        "source_fingerprint": str(readiness.get("sourceFingerprint") or ""),
        "sources": readiness.get("sources") or [],
        "registered_at": base.now_local(),
        "human_review": {
            "status": "PENDING_OWNER_REVIEW",
            "required": True,
            "approval_blocked_until_take05_exact_playback": True,
        },
        "readiness_exception": {
            "scope": "DIRECT_FULL_FILM_REVIEW_CANDIDATE_ONLY",
            "accepted_blockers": blockers,
            "final_promotion_allowed": False,
        },
        "previous_review_candidate": {
            "file": previous.get("file") if isinstance(previous, dict) else "",
            "sha256": previous.get("sha256") if isinstance(previous, dict) else "",
            "preserved": True,
        },
    }
    manifest["final_output"] = final
    # The Maestro project card must expose only the integral movie.  Historical
    # take candidates remain in rollback/manifests and are not deleted.
    manifest["take_review_candidates"] = []
    catalog = manifest.setdefault("maestro_catalog_policy", {})
    catalog["visible_review_item"] = "final_output_only"
    catalog["take_review_candidates_hidden"] = True
    catalog["media_deleted"] = False
    manifest["status"] = "FULL_FILM_V4_PENDING_OWNER_VISUAL_AND_LISTENING_REVIEW"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["updated_at"] = base.now_local()
    base.atomic_json(project_path, manifest)
    view = project_view(PROJECT)
    final_view = view.get("finalOutput") or {}
    if not final_view.get("ready"):
        raise RuntimeError(f"Maestro did not resolve registered candidate: {final_view}")
    result = {
        "ok": True,
        "registered_at": base.now_local(),
        "project_id": base.PROJECT_ID,
        "video": str(FINAL),
        "sha256": payload["final"]["sha256"],
        "maestro_final_output": final_view,
        "owner_review": "PENDING_EXACT_V4_PLAYBACK",
        "candidate_review_only": True,
        "final_promotion_allowed": False,
        "previous_v3_preserved": True,
    }
    base.atomic_json(QC / "maestro_registration_v4.json", result)
    return result


def mix_register() -> dict:
    configure_base()
    update_take05_candidate_state()
    chunks = generate_foley_chunks()
    foley_info = base.build_foley_bus(chunks)
    payload = base.mix_final(foley_info, chunks)
    payload["display_name"] = (
        "FILME COMPLETO - TAKE 05 CORRIGIDO + FALA DO 16 + FOLEY - "
        "720P60 - PARA APROVACAO"
    )
    payload["status"] = "PENDING_OWNER_VISUAL_AND_LISTENING_REVIEW"
    payload["owner_review"] = "PENDING_EXACT_V4_PLAYBACK"
    payload["picture_repair"] = {
        "replaced_only_take05": True,
        "rejected_ref2va_used": False,
        "corrected_take05": str(REPLACEMENT),
        "corrected_take05_sha256": base.sha256(REPLACEMENT),
        "cell_tail": "ABSENT_IN_INTERNAL_VISUAL_QC",
        "cell_wings": "TWO_DORSAL_WINGS_PRESENT_IN_INTERNAL_VISUAL_QC",
        "owner_final_video_approval": False,
    }
    payload["mix_qc"]["silence_events_below_minus50db_0p25s"] = silence_events(FINAL_AUDIO)
    payload["mix_qc"]["transient_and_clipping_analysis"] = transient_analysis(FINAL_AUDIO)
    if payload["mix_qc"]["transient_and_clipping_analysis"]["native_48k_clipping_sample_count_at_0p999"]:
        raise RuntimeError("Decoded final mix contains clipping samples.")
    payload["next_gate"] = "OWNER_REVIEWS_EXACT_V4_IN_MAESTRO"
    base.atomic_json(FINAL_MANIFEST, payload)
    registration = register_full_film_review_candidate(payload)
    return {
        "status": "READY_IN_MAESTRO_PENDING_OWNER_REVIEW",
        "final": payload["final"],
        "final_loudness": payload["mix_qc"]["loudness"],
        "transient_and_clipping_analysis": payload["mix_qc"]["transient_and_clipping_analysis"],
        "silence_events": payload["mix_qc"]["silence_events_below_minus50db_0p25s"],
        "foley_bus": foley_info,
        "registration": registration,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("picture", "foley-mix-register", "all"))
    args = parser.parse_args()
    if args.stage == "picture":
        result = build_picture()
    elif args.stage == "foley-mix-register":
        result = mix_register()
    else:
        build_picture()
        result = mix_register()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
