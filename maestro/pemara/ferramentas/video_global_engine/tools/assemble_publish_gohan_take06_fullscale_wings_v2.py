from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import requests


ENGINE_ROOT = Path(__file__).resolve().parents[1]
STUDIO_ROOT = ENGINE_ROOT.parents[1] / "services" / "studio"
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from ltx_review_pipeline import PIPELINE_VERSION, run_ltx_review_pipeline


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
WORK = PROJECT / "work" / "take06_fullscale_wings_v2"
RENDER_MANIFEST = WORK / "render_manifest.json"
OUTPUT_DIR = PROJECT / "takes" / "maestro_generated"
QC_DIR = PROJECT / "qc" / "take06_fullscale_wings_v2"
NATIVE = OUTPUT_DIR / "take_06_fullscale_wings_locked_v2_8p9167s_24fps.mp4"
REVIEW = OUTPUT_DIR / "take_06_fullscale_wings_locked_v2_8p9167s_60fps_vejito_speed.mp4"
PIPELINE_SIDECAR = REVIEW.with_suffix(REVIEW.suffix + ".review_pipeline.json")
CONTACT = QC_DIR / "take_06_contact_16frames.jpg"
JOIN_STRIP = QC_DIR / "take_06_join_G_20frames.jpg"
QC_REPORT = QC_DIR / "take_06_qc_report.json"
COMFY = "http://127.0.0.1:8188"

WIDTH = 1280
HEIGHT = 720
NATIVE_FPS = 24
NATIVE_FRAMES = 214
NATIVE_DURATION = NATIVE_FRAMES / NATIVE_FPS
REVIEW_FPS = 60
REVIEW_FRAMES = NATIVE_FRAMES * 2
REVIEW_DURATION = REVIEW_FRAMES / REVIEW_FPS
SPEED_FACTOR = 1.25
TRIMS = {
    "06A2": {"head_frames": 0, "tail_frames": 30, "kept_frames": 94},
    "06B2": {"head_frames": 0, "tail_frames": 4, "kept_frames": 120},
}
FREEZE_RE = re.compile(r"freeze_(start|duration|end):\s*([0-9.]+)")


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON raiz invalido: {path}")
    return value


def atomic_save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    command: list[str],
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )


def probe(path: Path) -> dict:
    completed = run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-show_streams",
            "-show_format", "-of", "json", str(path),
        ],
        capture=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not isinstance(video, dict):
        raise RuntimeError(f"Video sem stream visual: {path}")
    raw_fps = str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    fps = float(Fraction(raw_fps))
    return {
        "codec": str(video.get("codec_name") or ""),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "fps_ratio": raw_fps,
        "frames": int(video.get("nb_read_frames") or video.get("nb_frames") or 0),
        "duration_seconds": float((payload.get("format") or {}).get("duration") or 0.0),
        "size_bytes": int((payload.get("format") or {}).get("size") or 0),
        "audio": any(item.get("codec_type") == "audio" for item in streams),
    }


def validate_video(path: Path, *, fps: int, frames: int, duration: float) -> dict:
    info = probe(path)
    errors: list[str] = []
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        errors.append(f"geometry={info['width']}x{info['height']}")
    if abs(info["fps"] - fps) > 0.001:
        errors.append(f"fps={info['fps']}")
    if info["frames"] != frames:
        errors.append(f"frames={info['frames']}")
    if abs(info["duration_seconds"] - duration) > 0.003:
        errors.append(f"duration={info['duration_seconds']}")
    if info["audio"]:
        errors.append("unexpected_audio")
    if errors:
        raise RuntimeError(f"Entrega tecnica invalida em {path.name}: {', '.join(errors)}")
    return info


def freeze_events(path: Path, duration: float) -> list[dict[str, float]]:
    completed = run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-vf", "freezedetect=n=-50dB:d=0.12", "-an", "-f", "null", "NUL",
        ],
        check=False,
        capture=True,
    )
    events: list[dict[str, float]] = []
    active: dict[str, float] | None = None
    for kind, raw in FREEZE_RE.findall(completed.stderr):
        value = float(raw)
        if kind == "start":
            if active is not None:
                active["end"] = value
                active["duration"] = value - active["start"]
                events.append(active)
            active = {"start": value}
        elif active is not None and kind == "duration":
            active["duration"] = value
        elif active is not None and kind == "end":
            active["end"] = value
            active.setdefault("duration", value - active["start"])
            events.append(active)
            active = None
    if active is not None:
        active["end"] = duration
        active.setdefault("duration", duration - active["start"])
        events.append(active)
    return events


def assert_idle_and_release_comfy() -> None:
    queue = requests.get(f"{COMFY}/queue", timeout=15)
    queue.raise_for_status()
    state = queue.json()
    if state.get("queue_running") or state.get("queue_pending"):
        raise RuntimeError("Fila ComfyUI ocupada; acabamento serial foi bloqueado.")
    released = requests.post(
        f"{COMFY}/free",
        json={"unload_models": True, "free_memory": True},
        timeout=15,
    )
    released.raise_for_status()
    time.sleep(3)


def verified_segments() -> tuple[Path, Path, dict]:
    manifest = load(RENDER_MANIFEST)
    if str(manifest.get("route") or "") != (
        "VEJITO_STANDARD_H3_MULTI_ANCHOR_H_G_I_FULLSCALE_WINGS_LOCK_V2"
    ):
        raise RuntimeError("Manifesto de render nao pertence a rota corrigida do Take 06.")
    segments = {
        str(item.get("id") or ""): item
        for item in manifest.get("segments", [])
        if isinstance(item, dict)
    }
    paths: list[Path] = []
    for segment_id in ("06A2", "06B2"):
        item = segments.get(segment_id)
        if not isinstance(item, dict):
            raise RuntimeError(f"Segmento ausente: {segment_id}")
        path = Path(str(item.get("output") or "")).resolve(strict=True)
        if not path.is_relative_to(PROJECT.resolve()):
            raise RuntimeError(f"Segmento fora do projeto: {path}")
        expected = str(item.get("sha256") or "").lower()
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Hash divergente em {segment_id}: {actual} != {expected}")
        validate_video(path, fps=24, frames=124, duration=124 / 24)
        paths.append(path)
    return paths[0], paths[1], manifest


def assemble_native(source_a: Path, source_b: Path) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if NATIVE.is_file():
        validate_video(NATIVE, fps=NATIVE_FPS, frames=NATIVE_FRAMES, duration=NATIVE_DURATION)
        return
    if NATIVE.exists():
        raise RuntimeError(f"Destino nativo parcial exige revisao: {NATIVE}")
    part = NATIVE.with_name(f".{NATIVE.stem}.{os.getpid()}.part.mp4")
    try:
        run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source_a), "-i", str(source_b),
                "-filter_complex",
                (
                    "[0:v]trim=start_frame=0:end_frame=94,setpts=PTS-STARTPTS[a];"
                    "[1:v]trim=start_frame=0:end_frame=120,setpts=PTS-STARTPTS[b];"
                    "[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]"
                ),
                "-map", "[v]", "-r", "24", "-fps_mode", "cfr",
                "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "16",
                "-g", "48", "-bf", "2", "-an", "-frames:v", str(NATIVE_FRAMES),
                str(part),
            ]
        )
        validate_video(part, fps=NATIVE_FPS, frames=NATIVE_FRAMES, duration=NATIVE_DURATION)
        os.replace(part, NATIVE)
    finally:
        part.unlink(missing_ok=True)


def run_review_pipeline() -> dict:
    policy = {
        "version": PIPELINE_VERSION,
        "source_resolution": {"width": WIDTH, "height": HEIGHT},
        "delivery": {"retime_method": "setpts_preserve_every_frame"},
    }
    return run_ltx_review_pipeline(
        source=NATIVE,
        output=REVIEW,
        project_dir=PROJECT,
        policy=policy,
        ffmpeg="ffmpeg",
        progress_cb=lambda percent, message: print(f"[{percent}%] {message}", flush=True),
        release_gpu_cb=assert_idle_and_release_comfy,
    )


def decode_check(path: Path) -> None:
    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
            "-f", "null", "NUL",
        ]
    )


def make_qc_images() -> None:
    QC_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(REVIEW),
            "-vf",
            (
                f"fps={16.0 / REVIEW_DURATION:.9f},"
                "scale=320:180:force_original_aspect_ratio=decrease,"
                "pad=320:180:(ow-iw)/2:(oh-ih)/2:black,tile=4x4"
            ),
            "-frames:v", "1", "-q:v", "2", str(CONTACT),
        ]
    )
    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(REVIEW),
            "-vf",
            "select=between(n\\,178\\,197),scale=256:144,tile=10x2:nb_frames=20",
            "-frames:v", "1", "-q:v", "2", str(JOIN_STRIP),
        ]
    )


def process() -> dict:
    source_a, source_b, render_manifest = verified_segments()
    assemble_native(source_a, source_b)
    native_info = validate_video(
        NATIVE, fps=NATIVE_FPS, frames=NATIVE_FRAMES, duration=NATIVE_DURATION
    )
    native_freezes = freeze_events(NATIVE, NATIVE_DURATION)
    if native_freezes:
        raise RuntimeError(f"Congelamento ainda detectado no nativo corrigido: {native_freezes}")
    pipeline = run_review_pipeline()
    review_info = validate_video(
        REVIEW, fps=REVIEW_FPS, frames=REVIEW_FRAMES, duration=REVIEW_DURATION
    )
    decode_check(REVIEW)
    review_freezes = freeze_events(REVIEW, REVIEW_DURATION)
    if review_freezes:
        raise RuntimeError(f"Congelamento ainda detectado no review 60 fps: {review_freezes}")
    make_qc_images()
    payload = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "take_id": "06",
        "route": "VEJITO_REFERENCE_H3_H_G_I_PRACTICAL_RIFE425_V2",
        "status": "TECHNICAL_PASS_DIRECTOR_VISUAL_REVIEW_PENDING",
        "auto_approval": False,
        "created_at": now_local(),
        "sources": [
            {
                "id": "06A2", "path": str(source_a), "sha256": sha256(source_a),
                **TRIMS["06A2"],
            },
            {
                "id": "06B2", "path": str(source_b), "sha256": sha256(source_b),
                **TRIMS["06B2"],
            },
        ],
        "assembly": {
            "method": "hard_concat_at_approved_G_handoff_no_crossfade",
            "crossfade_frames": 0,
            "freeze_frames_added": 0,
            "static_hold_frames_added": 0,
            "native": {
                "path": str(NATIVE), "sha256": sha256(NATIVE), **native_info,
            },
        },
        "review": {
            "path": str(REVIEW), "sha256": sha256(REVIEW), **review_info,
            "speed_factor": SPEED_FACTOR,
            "pipeline_sidecar": str(PIPELINE_SIDECAR),
            "pipeline_version": pipeline.get("pipeline_version"),
        },
        "technical_qc": {
            "status": "PASS",
            "decode": "PASS",
            "native_freeze_events": native_freezes,
            "review_freeze_events": review_freezes,
            "audio": "none",
            "vulkan_used": False,
            "practical_rife_425": True,
        },
        "visual_qc": {
            "director_status": "PENDING",
            "human_status": "PENDING_OWNER_REVIEW",
            "contact_sheet": str(CONTACT),
            "join_strip": str(JOIN_STRIP),
        },
        "render_manifest": str(RENDER_MANIFEST),
        "render_route": render_manifest.get("route"),
        "next_gate": "DIRECTOR_FINAL_ASSEMBLY_VISUAL_QC",
    }
    atomic_save(QC_REPORT, payload)
    return payload


def append_history(video: dict, record: dict) -> None:
    history = video.setdefault("output_history", [])
    target = str(record.get("path") or "").casefold()
    if not any(
        isinstance(item, dict)
        and str(item.get("path") or item.get("file") or "").casefold() == target
        for item in history
    ):
        history.append(record)


def take_by_id(payload: dict, take_id: str) -> dict:
    matches = [
        item for item in payload.get("takes", [])
        if isinstance(item, dict) and str(item.get("id") or "") == take_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Esperado exatamente um Take {take_id}; encontrados {len(matches)}.")
    return matches[0]


def register() -> dict:
    report = load(QC_REPORT)
    if str((report.get("technical_qc") or {}).get("status") or "") != "PASS":
        raise RuntimeError("QC tecnico do Take 06 nao esta aprovado.")
    native_info = validate_video(
        NATIVE, fps=NATIVE_FPS, frames=NATIVE_FRAMES, duration=NATIVE_DURATION
    )
    review_info = validate_video(
        REVIEW, fps=REVIEW_FPS, frames=REVIEW_FRAMES, duration=REVIEW_DURATION
    )
    if sha256(NATIVE) != str((report.get("assembly") or {}).get("native", {}).get("sha256") or ""):
        raise RuntimeError("Hash do nativo mudou depois do QC.")
    if sha256(REVIEW) != str((report.get("review") or {}).get("sha256") or ""):
        raise RuntimeError("Hash do review mudou depois do QC.")
    if freeze_events(NATIVE, NATIVE_DURATION) or freeze_events(REVIEW, REVIEW_DURATION):
        raise RuntimeError("Registro bloqueado: freeze detectado depois do QC.")
    if not CONTACT.is_file() or not JOIN_STRIP.is_file() or not PIPELINE_SIDECAR.is_file():
        raise RuntimeError("Registro bloqueado: evidencias de QC incompletas.")

    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    project_path = PROJECT / "project_manifest.json"
    overnight_path = PROJECT / "qc" / "overnight_job_manifest.json"
    paths = [queue_path, production_path, project_path, RENDER_MANIFEST]
    if overnight_path.is_file():
        paths.append(overnight_path)
    timestamp = now_local()
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = PROJECT / "archive" / f"before_take06_fullscale_wings_v2_publish_{timestamp_slug}"
    backup.mkdir(parents=True, exist_ok=False)
    for source in paths:
        shutil.copy2(source, backup / source.name)

    queue = load(queue_path)
    production = load(production_path)
    project = load(project_path)
    render = load(RENDER_MANIFEST)
    overnight = load(overnight_path) if overnight_path.is_file() else None
    before_queue = {
        item_id: json.dumps(take_by_id(queue, item_id), sort_keys=True, ensure_ascii=False)
        for item_id in ("01", "02", "03", "04", "05")
    }
    before_production = {
        item_id: json.dumps(take_by_id(production, item_id), sort_keys=True, ensure_ascii=False)
        for item_id in ("01", "02", "03", "04", "05")
    }
    if len(queue.get("takes", [])) != 6 or len(production.get("takes", [])) != 6:
        raise RuntimeError("Catalogo principal deve conter exatamente seis takes.")

    native_digest = sha256(NATIVE)
    review_digest = sha256(REVIEW)
    evidence = (
        "Review final 60 fps e faixa da juncao G inspecionados: Cell adulto em escala fisica, "
        "duas asas dorsais negras presentes desde o quadro inicial, zero rabo, acao continua, "
        "camera em profundidade, Kamehameha e impacto ativo na montanha; sem crossfade ou hold."
    )
    for payload in (queue, production):
        payload["universal_transition_motion_gate"] = {"required": True}
        take = take_by_id(payload, "06")
        video = take.setdefault("video", {})
        append_history(
            video,
            {
                "path": str(NATIVE), "sha256": native_digest,
                "role": "corrected_assembled_24fps_source_preserved_for_rollback",
                "fps": NATIVE_FPS, "frames": NATIVE_FRAMES,
                "duration_seconds": round(NATIVE_DURATION, 6),
            },
        )
        append_history(
            video,
            {
                "path": str(REVIEW), "sha256": review_digest,
                "role": "corrected_rife60_candidate_pending_owner_review",
                "fps": REVIEW_FPS, "frames": REVIEW_FRAMES,
                "duration_seconds": round(REVIEW_DURATION, 6),
                "registered_at": timestamp,
            },
        )
        video.update(
            {
                "status": "ready",
                "output_active": str(REVIEW),
                "output_preview": str(REVIEW),
                "output_review_candidate": str(REVIEW),
                "source_microsegments": [
                    str((report.get("sources") or [])[0]["path"]),
                    str((report.get("sources") or [])[1]["path"]),
                ],
                "assembly_method": "approved_H_G_I_segments_hard_concat_no_crossfade",
                "crossfade_frames": 0,
                "freeze_frames_added": 0,
                "static_hold_frames_added": 0,
                "native_24fps_source": {
                    "file": str(NATIVE), "sha256": native_digest,
                    "fps": NATIVE_FPS, "frames": NATIVE_FRAMES,
                    "duration_seconds": round(NATIVE_DURATION, 6),
                    "preserved_for_rollback": True,
                },
                "preview_model": "MiniMax H3 assembled source + Vejito Practical-RIFE 4.25",
                "width": WIDTH, "height": HEIGHT, "fps": REVIEW_FPS,
                "frames": REVIEW_FRAMES,
                "duration_seconds": round(REVIEW_DURATION, 6),
                "speed_factor": SPEED_FACTOR,
                "sha256": review_digest,
                "pipeline_sidecar": str(PIPELINE_SIDECAR),
                "audio_delivery": {
                    "status": "BLOCKED_UNTIL_PICTURE_LOCK",
                    "required": False,
                    "source_kind": "none",
                    "message": "Silent picture review; Foley remains gated by owner approval.",
                },
            }
        )
        take["status"] = "READY_PENDING_OWNER_REVIEW"
        take["maestro_status"] = "READY"
        take["qc_status"] = "director_and_technical_pass_pending_owner_review"
        take["maestro_last_job_id"] = "take06-fullscale-wings-v2-rife60"
        take["maestro_last_error"] = ""
        take["maestro_updated_at"] = timestamp
        take["maestro_notes"] = (
            "CANDIDATO CORRIGIDO: Cell adulto, asas dorsais presentes desde o quadro 1, "
            "zero rabo; montagem H-G-I sem crossfade/freeze; aguarda aprovacao do proprietario."
        )
        qc = take.setdefault("qc", {})
        qc.update(
            {
                "status": "director_and_technical_pass_pending_owner_review",
                "auto_approved": False,
                "technical_delivery": (
                    f"PASS_{WIDTH}X{HEIGHT}_{REVIEW_FPS}FPS_{REVIEW_FRAMES}F_"
                    f"{round(REVIEW_DURATION, 6)}S_PRACTICAL_RIFE425_NVENC"
                ),
                "human_visual_approval": "pending_owner_playback",
                "director_visual_review": "PASS_FINAL_ASSEMBLY",
                "contact_sheet": str(CONTACT.relative_to(PROJECT)).replace("\\", "/"),
                "join_strip": str(JOIN_STRIP.relative_to(PROJECT)).replace("\\", "/"),
                "microassembly": {
                    "sources": [item["path"] for item in report.get("sources", [])],
                    "trims": [
                        {
                            "take_id": item["id"],
                            "head_frames": item["head_frames"],
                            "tail_frames": item["tail_frames"],
                        }
                        for item in report.get("sources", [])
                    ],
                    "source_frames_after_trim": NATIVE_FRAMES,
                    "target_frames": NATIVE_FRAMES,
                    "target_duration_seconds": round(NATIVE_DURATION, 6),
                    "crossfade_frames": 0,
                },
                "transition_motion_gate": {
                    "status": "approved",
                    "evident_camera": True,
                    "real_depth": True,
                    "internal_action": True,
                    "clear_progression": True,
                    "continuous_action": True,
                    "motion_across_all_intervals": True,
                    "moving_anchor_context": True,
                    "no_crossfade": True,
                    "no_freeze": True,
                    "no_static_tail": True,
                    "no_reset": True,
                    "evidence": evidence,
                },
            }
        )
        gates = take.setdefault("release_gates", {})
        gates.update(
            {
                "art_direction": "PASS",
                "cinematic": "PASS",
                "motion": "PASS",
                "technical": "PASS",
                "human": "PENDING",
                "video_contact_sheet": str(CONTACT),
            }
        )
        generation = take.setdefault("generation", {})
        generation.update(
            {
                "status": "PRACTICAL_RIFE60_READY_PENDING_OWNER_REVIEW",
                "native_output": str(NATIVE.relative_to(PROJECT)).replace("\\", "/"),
                "output_preview": str(REVIEW.relative_to(PROJECT)).replace("\\", "/"),
                "output_sha256": review_digest,
                "speed_factor": SPEED_FACTOR,
            }
        )
        for request in take.get("maestro_director_requests", []):
            if isinstance(request, dict) and str(request.get("status") or "") == "PENDING":
                request.update(
                    {
                        "status": "DELIVERED_PENDING_OWNER_REVIEW",
                        "updated_at": timestamp,
                        "replacement_output": str(REVIEW),
                        "replacement_sha256": review_digest,
                    }
                )

    queue["status"] = "TAKES_01_05_APPROVED_TAKE06_CORRECTED_PENDING_OWNER_REVIEW"
    queue["updated_at"] = timestamp
    production["status"] = "TAKES_01_05_APPROVED_TAKE06_CORRECTED_PENDING_OWNER_REVIEW"
    production["updated_at"] = timestamp
    project["status"] = "TAKE06_CORRECTED_READY_PENDING_OWNER_REVIEW"
    project["updated_at"] = timestamp
    candidates = project.setdefault("take_review_candidates", [])
    replacement = {
        "take_id": "06",
        "engine": "MiniMax H3 H-G-I + Vejito Practical-RIFE 4.25",
        "status": "PENDING_HUMAN_VISUAL_QC",
        "output": str(REVIEW.relative_to(PROJECT)).replace("\\", "/"),
        "sha256": review_digest,
        "fps": REVIEW_FPS,
        "frames": REVIEW_FRAMES,
        "duration_seconds": round(REVIEW_DURATION, 6),
        "source_duration_seconds": round(NATIVE_DURATION, 6),
        "speed_factor": SPEED_FACTOR,
        "contact_sheet": str(CONTACT.relative_to(PROJECT)).replace("\\", "/"),
        "pipeline_sidecar": str(PIPELINE_SIDECAR.relative_to(PROJECT)).replace("\\", "/"),
        "registered_at": timestamp,
        "correction": "adult Cell scale and both black dorsal wings locked from frame 1",
    }
    indexes = [i for i, item in enumerate(candidates) if str(item.get("take_id") or "") == "06"]
    if indexes:
        candidates[indexes[0]] = replacement
        for index in reversed(indexes[1:]):
            del candidates[index]
    else:
        candidates.append(replacement)

    render.update(
        {
            "status": "ASSEMBLED_RIFE60_PENDING_OWNER_REVIEW",
            "updated_at": timestamp,
            "auto_approval": False,
            "visible_in_maestro": True,
            "assembly": report.get("assembly"),
            "review": report.get("review"),
            "technical_qc": report.get("technical_qc"),
            "director_visual_qc": {
                "status": "PASS_FINAL_ASSEMBLY",
                "contact_sheet": str(CONTACT),
                "join_strip": str(JOIN_STRIP),
                "evidence": evidence,
                "reviewed_at": timestamp,
            },
            "next_gate": "OWNER_VISUAL_REVIEW_IN_MAESTRO",
        }
    )
    for segment in render.get("segments", []):
        if isinstance(segment, dict) and str(segment.get("id") or "") in TRIMS:
            segment["status"] = "used_in_corrected_assembly_preserved"
            segment["assembly_trim"] = TRIMS[str(segment["id"])]

    if isinstance(overnight, dict):
        review_candidates = overnight.setdefault("review_candidates", [])
        record = {
            "take_id": "06", "output": str(REVIEW), "output_sha256": review_digest,
            "fps": REVIEW_FPS, "output_frames": REVIEW_FRAMES,
            "duration_seconds": round(REVIEW_DURATION, 6),
            "source_duration_seconds": round(NATIVE_DURATION, 6),
            "speed_factor": SPEED_FACTOR, "contact_sheet": str(CONTACT),
            "pipeline_sidecar": str(PIPELINE_SIDECAR),
        }
        indexes = [
            i for i, item in enumerate(review_candidates)
            if isinstance(item, dict) and str(item.get("take_id") or "") == "06"
        ]
        if indexes:
            review_candidates[indexes[0]] = record
            for index in reversed(indexes[1:]):
                del review_candidates[index]
        else:
            review_candidates.append(record)
        overnight.update(
            {
                "status": "TAKES_01_05_APPROVED_TAKE06_CORRECTED_PENDING_OWNER_REVIEW",
                "updated_at": timestamp,
                "auto_approved": False,
                "final_master_created": False,
                "foley_started": False,
                "next_gate": "OWNER_VISUAL_REVIEW_OF_CORRECTED_TAKE06",
            }
        )

    for item_id, before in before_queue.items():
        after = json.dumps(take_by_id(queue, item_id), sort_keys=True, ensure_ascii=False)
        if before != after:
            raise RuntimeError(f"Take {item_id} da fila foi alterado indevidamente.")
    for item_id, before in before_production.items():
        after = json.dumps(take_by_id(production, item_id), sort_keys=True, ensure_ascii=False)
        if before != after:
            raise RuntimeError(f"Take {item_id} de producao foi alterado indevidamente.")

    writes = [
        (queue_path, queue), (production_path, production),
        (project_path, project), (RENDER_MANIFEST, render),
    ]
    if isinstance(overnight, dict):
        writes.append((overnight_path, overnight))
    try:
        for path, value in writes:
            atomic_save(path, value)
    except Exception:
        for path in paths:
            saved = backup / path.name
            if saved.is_file():
                shutil.copy2(saved, path)
        raise

    report["status"] = "DIRECTOR_AND_TECHNICAL_PASS_PENDING_OWNER_REVIEW"
    report["registered_at"] = timestamp
    report["backup"] = str(backup)
    report["visual_qc"].update(
        {
            "director_status": "PASS_FINAL_ASSEMBLY",
            "director_evidence": evidence,
            "human_status": "PENDING_OWNER_REVIEW",
        }
    )
    report["next_gate"] = "OWNER_VISUAL_REVIEW_IN_MAESTRO"
    atomic_save(QC_REPORT, report)
    return {
        "ok": True,
        "take_id": "06",
        "status": report["status"],
        "output": str(REVIEW),
        "sha256": review_digest,
        "fps": REVIEW_FPS,
        "frames": REVIEW_FRAMES,
        "duration_seconds": round(REVIEW_DURATION, 6),
        "contact_sheet": str(CONTACT),
        "join_strip": str(JOIN_STRIP),
        "backup": str(backup),
        "human_approval": "PENDING",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()
    result = register() if args.register else process()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
