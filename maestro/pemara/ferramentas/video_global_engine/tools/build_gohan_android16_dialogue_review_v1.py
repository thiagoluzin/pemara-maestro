"""Build and register the dialogue-only Gohan SSJ2 full-film review.

Stages are intentionally separated by internal visual QC:

* prepare  - validate the approved A->B bridge and the LatentSync 1.6 result
             driven by the owner-approved Version E voice, then publish
             internal contact sheets only.
* assemble - after director lip-sync QC, use Practical-RIFE 4.25, assemble the
             six-take movie without crossfades/holds, and create technical QC.
* register - after final director playback QC, register one pending-review
             full-film item in Maestro.  It never grants owner approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import requests


ROOT = Path(r"E:\Pemara\maestro\pemara")
ENGINE = ROOT / "ferramentas" / "video_global_engine"
PROJECTS = ENGINE / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
WORK = PROJECT / "work" / "android16_speech_fullfilm_v1"
QC = WORK / "qc"
DELIVERIES = PROJECT / "deliveries"
EDIT = PROJECT / "edit"

SPEECH_RENDER_MANIFEST = WORK / "speech_render_manifest.json"
SPEECH_VISUAL_QC = QC / "speech_visual_qc.json"
LIPSYNC_DIRECTOR_QC = QC / "lipsync_director_qc.json"
FULLFILM_DIRECTOR_QC = QC / "fullfilm_director_qc.json"
VOICE_QC = ROOT / "outputs" / "voice_previews" / "android16_voice_design_qc.json"
VOICE = ROOT / "outputs" / "voice_previews" / "android16_v4_sao_paulo_dublagem.wav"

TRIMMED_VISUAL = WORK / "android16_speech_A_B_active138f_24fps.mp4"
DRIVER_AUDIO = WORK / "android16_version_e_driver_5p75s.wav"
LIPSYNC_NATIVE = WORK / "android16_speech_latentsync_native25_v1.mp4"
LIPSYNC_RIFE_SOURCE = WORK / "android16_speech_latentsync_to24_139f_v1.mp4"
LIPSYNC_60 = WORK / "android16_speech_latentsync_5p75s_60fps_rife425_v1.mp4"
LIPSYNC_CONTACT = QC / "android16_speech_lipsync_contact16.jpg"
LIPSYNC_TIMING = QC / "android16_speech_lipsync_timing12.jpg"
LIPSYNC_TECHNICAL = QC / "android16_speech_lipsync_technical.json"

FULL_VIDEO = DELIVERIES / "GOHAN_SSJ2_ANDROID16_FALA_VIDEO_COMPLETO_SEM_FOLEY_APROVACAO_V2.mp4"
FULL_MANIFEST = EDIT / "GOHAN_SSJ2_ANDROID16_FALA_VIDEO_COMPLETO_SEM_FOLEY_APROVACAO_V2.json"
FULL_CONTACT = QC / "fullfilm_dialogue_review_v2_contact24.jpg"
FULL_JOINS = QC / "fullfilm_dialogue_review_v2_join_boundaries.jpg"

STUDIO = "http://127.0.0.1:8029"
COMFY = "http://127.0.0.1:8188"
GATE = Path(r"E:\Pemara\.agents\skills\pemara-cinematic-take-director\scripts\sequence_regression_gate.py")

WIDTH = 1280
HEIGHT = 720
NATIVE_FPS = 25
DELIVERY_FPS = 60
SOURCE_KEEP_FRAMES = 138
LIPSYNC_NATIVE_FRAMES = 145
RIFE_SOURCE_FRAMES = 139
DRIVER_SAMPLES = 276_000  # 5.75 s at 48 kHz; only rejected trailing silence is removed.
# RIFE preserves the full reviewed bridge, while the assembly excludes its
# final terminal frames.  The full RIFE artifact remains available for audit.
RIFE_60_FRAMES = 345
# The last 11 delivery frames contain the terminal near-static anchor after the
# audible line.  Stop on moving frame 333 and hand directly to Take 01 frame
# 176; the original Version E WAV continues through its own trailing silence.
SPEECH_60_FRAMES = 334
TAKE01_TAIL_START = 176
TAKE01_TAIL_FRAMES = 184

TAKES = [
    PROJECT / "takes" / "maestro_generated" / "take_01_vejito_standard_7p5s_60fps_vejito_speed_v1.mp4",
    PROJECT / "takes" / "maestro_generated" / "take_02_vejito_standard_3p5s_60fps_vejito_speed_v1.mp4",
    PROJECT / "takes" / "maestro_generated" / "take_03_cell_juniors_multianchor_vejito_standard_12p0s_60fps_vejito_speed_v1.mp4",
    PROJECT / "takes" / "maestro_generated" / "take_04_vejito_standard_7p0s_60fps_vejito_speed_v1.mp4",
    PROJECT / "takes" / "maestro_generated" / "take_05_vejito_standard_12p0s_60fps_vejito_speed_v1.mp4",
    PROJECT / "takes" / "maestro_generated" / "take_06_fullscale_wings_locked_v2_8p9167s_60fps_vejito_speed.mp4",
]
TAKE_FRAMES = [360, 168, 576, 336, 576, 428]
FULL_FRAMES = SPEECH_60_FRAMES + TAKE01_TAIL_FRAMES + sum(TAKE_FRAMES[1:])
FULL_DURATION = FULL_FRAMES / DELIVERY_FPS
FREEZE_RE = re.compile(r"freeze_(start|duration|end):\s*([0-9.]+)")


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid JSON root: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )


def probe(path: Path) -> dict:
    completed = run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
            "-of", "json", str(path),
        ],
        capture=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not isinstance(video, dict):
        raise RuntimeError(f"No video stream: {path}")
    fps = float(Fraction(str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")))
    return {
        "path": str(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "video_codec": str(video.get("codec_name") or ""),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "fps_ratio": str(video.get("avg_frame_rate") or ""),
        "frames": int(video.get("nb_read_frames") or video.get("nb_frames") or 0),
        "duration_seconds": float((payload.get("format") or {}).get("duration") or 0),
        "audio": bool(audio),
        "audio_codec": str((audio or {}).get("codec_name") or ""),
        "sample_rate": int((audio or {}).get("sample_rate") or 0),
        "channels": int((audio or {}).get("channels") or 0),
    }


def validate_video(path: Path, *, fps: int, frames: int, audio: bool) -> dict:
    info = probe(path)
    errors = []
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        errors.append(f"geometry={info['width']}x{info['height']}")
    if abs(info["fps"] - fps) > 0.001:
        errors.append(f"fps={info['fps']}")
    if info["frames"] != frames:
        errors.append(f"frames={info['frames']}")
    if info["audio"] is not audio:
        errors.append(f"audio={info['audio']}")
    if errors:
        raise RuntimeError(f"Invalid delivery {path.name}: {', '.join(errors)}")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "null", "NUL"])
    return info


def require_qc(path: Path, status: str) -> dict:
    value = load(path)
    if str(value.get("status") or "") != status:
        raise RuntimeError(f"QC gate {path.name} is not {status}: {value.get('status')}")
    return value


def ensure_gpu_idle(*, unload_comfy: bool = False) -> None:
    state = requests.get(f"{COMFY}/queue", timeout=20)
    state.raise_for_status()
    queue = state.json()
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle; refusing to mix GPU work")
    if unload_comfy:
        response = requests.post(
            f"{COMFY}/free", json={"unload_models": True, "free_memory": True}, timeout=30
        )
        response.raise_for_status()
        time.sleep(3)


def verified_speech_source() -> Path:
    render = load(SPEECH_RENDER_MANIFEST)
    visual = require_qc(SPEECH_VISUAL_QC, "PASS_FOR_INTERNAL_LIPSYNC_WITH_TAIL_TRIM")
    source = Path(str(render.get("output") or "")).resolve(strict=True)
    if not source.is_relative_to(PROJECT.resolve()):
        raise RuntimeError("Speech source left the project")
    expected = str(render.get("sha256") or "").lower()
    actual = sha256(source)
    if actual != expected or actual != str(visual.get("source_sha256") or "").lower():
        raise RuntimeError("Speech source hash differs from the reviewed artifact")
    validate_video(source, fps=24, frames=158, audio=False)
    return source


def verified_voice() -> dict:
    qc = load(VOICE_QC)
    selected = qc.get("selectedCandidate") if isinstance(qc.get("selectedCandidate"), dict) else {}
    if selected.get("status") != "APPROVED_BY_OWNER":
        raise RuntimeError("Android 16 Version E is not owner-approved")
    if Path(str(selected.get("path") or "")).resolve() != VOICE.resolve(strict=True):
        raise RuntimeError("Voice QC points to a different file")
    actual = sha256(VOICE)
    if actual.upper() != str(selected.get("sha256") or "").upper():
        raise RuntimeError("Owner-approved voice hash drift")
    return {"qc": qc, "selected": selected, "sha256": actual}


def create_trimmed_visual(source: Path) -> dict:
    if TRIMMED_VISUAL.is_file():
        return validate_video(TRIMMED_VISUAL, fps=24, frames=SOURCE_KEEP_FRAMES, audio=False)
    TRIMMED_VISUAL.parent.mkdir(parents=True, exist_ok=True)
    part = TRIMMED_VISUAL.with_name(f".{TRIMMED_VISUAL.stem}.{os.getpid()}.part.mp4")
    try:
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
            "-vf", f"trim=start_frame=0:end_frame={SOURCE_KEEP_FRAMES},setpts=PTS-STARTPTS,format=yuv420p",
            "-r", "24", "-fps_mode", "cfr", "-frames:v", str(SOURCE_KEEP_FRAMES),
            "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-cq", "15", "-b:v", "0",
            "-g", "48", "-bf", "2", "-an", str(part),
        ])
        validate_video(part, fps=24, frames=SOURCE_KEEP_FRAMES, audio=False)
        os.replace(part, TRIMMED_VISUAL)
    finally:
        part.unlink(missing_ok=True)
    return validate_video(TRIMMED_VISUAL, fps=24, frames=SOURCE_KEEP_FRAMES, audio=False)


def create_driver_audio() -> dict:
    verified_voice()
    if not DRIVER_AUDIO.is_file():
        with wave.open(str(VOICE), "rb") as source:
            params = source.getparams()
            if (params.framerate, params.nchannels, params.sampwidth) != (48000, 2, 2):
                raise RuntimeError(f"Unexpected approved WAV format: {params}")
            if params.nframes < DRIVER_SAMPLES:
                raise RuntimeError("Approved voice is shorter than the audible line")
            frames = source.readframes(DRIVER_SAMPLES)
        with wave.open(str(DRIVER_AUDIO), "wb") as target:
            target.setparams(params._replace(nframes=0))
            target.writeframes(frames)
    with wave.open(str(VOICE), "rb") as source, wave.open(str(DRIVER_AUDIO), "rb") as driver:
        approved_prefix = source.readframes(DRIVER_SAMPLES)
        driven = driver.readframes(DRIVER_SAMPLES)
        if approved_prefix != driven or driver.getnframes() != DRIVER_SAMPLES:
            raise RuntimeError("Lip-sync driver altered approved speech samples")
        return {
            "path": str(DRIVER_AUDIO),
            "sha256": sha256(DRIVER_AUDIO),
            "frames_per_channel": driver.getnframes(),
            "sample_rate": driver.getframerate(),
            "channels": driver.getnchannels(),
            "duration_seconds": driver.getnframes() / driver.getframerate(),
            "approved_prefix_bit_exact": True,
            "trimmed_content": "0.100 seconds of trailing silence only",
        }


def make_contact(source: Path, output: Path, *, count: int, cols: int, duration: float) -> None:
    rows = (count + cols - 1) // cols
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-vf", f"fps={count / duration:.9f},scale=320:180,tile={cols}x{rows}:nb_frames={count}",
        "-frames:v", "1", "-q:v", "2", str(output),
    ])


def prepare() -> dict:
    source = verified_speech_source()
    voice = verified_voice()
    visual_info = create_trimmed_visual(source)
    audio_info = create_driver_audio()
    if not LIPSYNC_NATIVE.is_file():
        raise FileNotFoundError(LIPSYNC_NATIVE)
    info = validate_video(
        LIPSYNC_NATIVE,
        fps=NATIVE_FPS,
        frames=LIPSYNC_NATIVE_FRAMES,
        audio=True,
    )
    QC.mkdir(parents=True, exist_ok=True)
    make_contact(
        LIPSYNC_NATIVE,
        LIPSYNC_CONTACT,
        count=16,
        cols=4,
        duration=LIPSYNC_NATIVE_FRAMES / NATIVE_FPS,
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(LIPSYNC_NATIVE),
        "-vf", "select='eq(n\\,3)+eq(n\\,18)+eq(n\\,36)+eq(n\\,54)+eq(n\\,60)+eq(n\\,72)+eq(n\\,90)+eq(n\\,108)+eq(n\\,120)+eq(n\\,132)+eq(n\\,139)+eq(n\\,144)',scale=320:180,tile=4x3:nb_frames=12",
        "-frames:v", "1", "-q:v", "2", str(LIPSYNC_TIMING),
    ])
    result = {
        "schema_version": "1.0",
        "status": "TECHNICAL_PASS_PENDING_DIRECTOR_LIPSYNC_REVIEW",
        "created_at": now_local(),
        "auto_approval": False,
        "owner_approval": "PENDING_FULL_FILM_PLAYBACK",
        "engine": "LatentSync 1.6 local",
        "inference": {
            "checkpoint": "latentsync_unet.pt",
            "inference_steps": 20,
            "guidance_scale": 1.2,
            "deepcache": True,
            "face_detector": "InsightFace CPU fallback; UNet inference on NVIDIA GPU",
        },
        "source_visual": visual_info,
        "approved_voice": {
            "path": str(VOICE),
            "sha256": voice["sha256"],
            "variant": voice["selected"].get("variant"),
            "status": voice["selected"].get("status"),
        },
        "driver_audio": audio_info,
        "output": info,
        "contact_sheet": str(LIPSYNC_CONTACT),
        "timing_sheet": str(LIPSYNC_TIMING),
        "next_gate": "DIRECTOR_VISUAL_REVIEW_ONLY_NO_OWNER_APPROVAL",
    }
    atomic_json(LIPSYNC_TECHNICAL, result)
    return result


def make_rife_source() -> dict:
    validate_video(
        LIPSYNC_NATIVE,
        fps=NATIVE_FPS,
        frames=LIPSYNC_NATIVE_FRAMES,
        audio=True,
    )
    if not LIPSYNC_RIFE_SOURCE.is_file():
        part = LIPSYNC_RIFE_SOURCE.with_name(f".{LIPSYNC_RIFE_SOURCE.stem}.{os.getpid()}.part.mp4")
        try:
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(LIPSYNC_NATIVE),
                "-vf", "fps=24:round=near,setpts=PTS-STARTPTS,format=yuv420p",
                "-r", "24", "-fps_mode", "cfr", "-frames:v", str(RIFE_SOURCE_FRAMES),
                "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-cq", "15", "-b:v", "0",
                "-g", "48", "-bf", "2", "-an", str(part),
            ])
            validate_video(part, fps=24, frames=RIFE_SOURCE_FRAMES, audio=False)
            os.replace(part, LIPSYNC_RIFE_SOURCE)
        finally:
            part.unlink(missing_ok=True)
    return validate_video(LIPSYNC_RIFE_SOURCE, fps=24, frames=RIFE_SOURCE_FRAMES, audio=False)


def run_rife() -> dict:
    source_info = make_rife_source()
    studio_root = ROOT / "services" / "studio"
    if str(studio_root) not in sys.path:
        sys.path.insert(0, str(studio_root))
    from ltx_review_pipeline import run_ltx_review_pipeline

    ensure_gpu_idle(unload_comfy=True)
    policy = {
        "version": "h3_horizontal_rife425_midpoint48_cfr60_duration_v1",
        "source_resolution": {"width": WIDTH, "height": HEIGHT},
        "delivery": {"retime_method": "fps_filter_preserve_source_duration"},
    }
    result = run_ltx_review_pipeline(
        source=LIPSYNC_RIFE_SOURCE,
        output=LIPSYNC_60,
        project_dir=PROJECT,
        policy=policy,
        ffmpeg="ffmpeg",
        progress_cb=lambda percent, message: print(f"RIFE {percent}% {message}", flush=True),
    )
    output_info = validate_video(LIPSYNC_60, fps=60, frames=RIFE_60_FRAMES, audio=False)
    return {"source": source_info, "pipeline": result, "output": output_info}


def freeze_events(path: Path) -> list[dict]:
    completed = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-vf", "freezedetect=n=-50dB:d=0.15", "-an", "-f", "null", "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    events = []
    active = None
    for kind, raw in FREEZE_RE.findall(completed.stderr):
        value = float(raw)
        if kind == "start":
            active = {"start": value}
        elif active is not None and kind == "duration":
            active["duration"] = value
        elif active is not None and kind == "end":
            active["end"] = value
            active.setdefault("duration", value - active["start"])
            events.append(active)
            active = None
    if active is not None:
        active["end"] = FULL_DURATION
        active.setdefault("duration", FULL_DURATION - active["start"])
        events.append(active)
    return events


def assemble() -> dict:
    require_qc(LIPSYNC_DIRECTOR_QC, "PASS_FOR_FULL_FILM_ASSEMBLY")
    run([sys.executable, str(GATE), str(PROJECT / "production_manifest.json"), "--stage", "assembly"])
    rife = run_rife()
    for path, frames in zip(TAKES, TAKE_FRAMES):
        validate_video(path, fps=60, frames=frames, audio=False)
    DELIVERIES.mkdir(parents=True, exist_ok=True)
    EDIT.mkdir(parents=True, exist_ok=True)
    if not FULL_VIDEO.is_file():
        part = FULL_VIDEO.with_name(f".{FULL_VIDEO.stem}.{os.getpid()}.part.mp4")
        inputs = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(LIPSYNC_60)]
        for path in TAKES:
            inputs.extend(["-i", str(path)])
        inputs.extend(["-i", str(VOICE)])
        video_filter = (
            f"[0:v]trim=start_frame=0:end_frame={SPEECH_60_FRAMES},setpts=PTS-STARTPTS[v0];"
            f"[1:v]trim=start_frame={TAKE01_TAIL_START}:end_frame={TAKE_FRAMES[0]},setpts=PTS-STARTPTS[v1];"
            "[2:v]setpts=PTS-STARTPTS[v2];[3:v]setpts=PTS-STARTPTS[v3];"
            "[4:v]setpts=PTS-STARTPTS[v4];[5:v]setpts=PTS-STARTPTS[v5];"
            "[6:v]setpts=PTS-STARTPTS[v6];"
            "[v0][v1][v2][v3][v4][v5][v6]concat=n=7:v=1:a=0,format=yuv420p[v];"
            f"[7:a]apad,atrim=duration={FULL_DURATION:.9f},asetpts=PTS-STARTPTS[a]"
        )
        command = inputs + [
            "-filter_complex", video_filter, "-map", "[v]", "-map", "[a]",
            "-r", "60", "-fps_mode", "cfr", "-frames:v", str(FULL_FRAMES),
            "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-profile:v", "high",
            "-pix_fmt", "yuv420p", "-rc", "vbr", "-cq", "15", "-b:v", "0",
            "-maxrate", "24M", "-bufsize", "48M", "-g", "120", "-bf", "2",
            "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
            "-metadata", "title=Gohan SSJ2 - Android 16 - video completo sem Foley - aprovacao",
            "-metadata", "comment=Dialogue-only picture review; no Foley; no crossfade; no freeze/hold added",
            "-movflags", "+faststart", str(part),
        ]
        try:
            run(command)
            validate_video(part, fps=60, frames=FULL_FRAMES, audio=True)
            os.replace(part, FULL_VIDEO)
        finally:
            part.unlink(missing_ok=True)
    full_info = validate_video(FULL_VIDEO, fps=60, frames=FULL_FRAMES, audio=True)
    if full_info["sample_rate"] != 48000 or full_info["channels"] != 2:
        raise RuntimeError(f"Unexpected final audio format: {full_info}")
    make_contact(FULL_VIDEO, FULL_CONTACT, count=24, cols=6, duration=FULL_DURATION)
    boundaries = [SPEECH_60_FRAMES, SPEECH_60_FRAMES + TAKE01_TAIL_FRAMES]
    cursor = boundaries[-1]
    for frames in TAKE_FRAMES[1:-1]:
        cursor += frames
        boundaries.append(cursor)
    select_terms = []
    for boundary in boundaries:
        select_terms.extend([f"eq(n\\,{value})" for value in range(boundary - 2, boundary + 2)])
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(FULL_VIDEO),
        "-vf", f"select='{'+'.join(select_terms)}',scale=256:144,tile=8x3:nb_frames=24",
        "-frames:v", "1", "-q:v", "2", str(FULL_JOINS),
    ])
    freezes = freeze_events(FULL_VIDEO)
    long_freezes = [item for item in freezes if float(item.get("duration") or 0) >= 0.25]
    if long_freezes:
        raise RuntimeError(f"Full film still contains freezes >= 0.25 s: {long_freezes}")
    payload = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "display_name": "FILME COMPLETO - FALA ANDROID 16 - SEM FOLEY - PARA APROVACAO",
        "status": "TECHNICAL_PASS_PENDING_DIRECTOR_FULL_PLAYBACK",
        "created_at": now_local(),
        "auto_approval": False,
        "owner_review": "PENDING",
        "foley": "NOT_PRESENT_BLOCKED_UNTIL_OWNER_APPROVAL",
        "dialogue": {
            "variant": "android16_sao_paulo_dublagem_e",
            "owner_approved_source": str(VOICE),
            "owner_approved_source_sha256": sha256(VOICE),
            "timeline_start_seconds": 0.0,
            "audible_speech_end_seconds": 5.424,
            "source_duration_seconds": 5.85,
            "final_track": "AAC 320 kbps derived from the approved PCM source; no voice redesign or accent change",
        },
        "picture": full_info,
        "rife": rife,
        "assembly": {
            "method": "hard_concat_at_moving_anchor_boundaries_no_crossfade",
            "sources": [str(LIPSYNC_60), *[str(item) for item in TAKES]],
            "take01_tail_start_frame": TAKE01_TAIL_START,
            "crossfade_frames": 0,
            "freeze_frames_added": 0,
            "static_hold_frames_added": 0,
            "frames": FULL_FRAMES,
            "duration_seconds": FULL_DURATION,
        },
        "technical_qc": {
            "decode": "PASS",
            "constant_fps": True,
            "freeze_events_at_least_0p15_seconds": freezes,
            "freeze_events_at_least_0p25_seconds": long_freezes,
            "contact_sheet": str(FULL_CONTACT),
            "join_sheet": str(FULL_JOINS),
            "sequence_regression_gate": "PASS_ASSEMBLY",
        },
        "next_gate": "DIRECTOR_FULL_PLAYBACK_THEN_OWNER_REVIEW_IN_MAESTRO",
    }
    atomic_json(FULL_MANIFEST, payload)
    return payload


def register() -> dict:
    director = require_qc(FULLFILM_DIRECTOR_QC, "PASS_PENDING_OWNER_REVIEW")
    technical = load(FULL_MANIFEST)
    if technical.get("status") != "TECHNICAL_PASS_PENDING_DIRECTOR_FULL_PLAYBACK":
        raise RuntimeError("Full-film technical gate is not ready")
    actual = sha256(FULL_VIDEO)
    if actual != str((technical.get("picture") or {}).get("sha256") or ""):
        raise RuntimeError("Full-film hash drift after director review")
    if str(director.get("video_sha256") or "").lower() != actual.lower():
        raise RuntimeError("Director reviewed a different full-film artifact")
    studio_root = ROOT / "services" / "studio"
    if str(studio_root) not in sys.path:
        sys.path.insert(0, str(studio_root))
    from video_projects import get_project_assembly_readiness, register_project_final_output

    readiness = get_project_assembly_readiness(PROJECTS, PROJECT_ID)
    if not readiness.get("ready"):
        raise RuntimeError(json.dumps(readiness, ensure_ascii=False, indent=2))
    record = {
        "file": str(FULL_VIDEO),
        "review_file": str(FULL_VIDEO),
        "display_name": "FILME COMPLETO - FALA ANDROID 16 - SEM FOLEY - PARA APROVACAO",
        "title": "GOHAN SSJ2 - VIDEO COMPLETO COM FALA DO ANDROID 16 - SEM FOLEY",
        "duration_seconds": FULL_DURATION,
        "width": WIDTH,
        "height": HEIGHT,
        "fps": DELIVERY_FPS,
        "frames": FULL_FRAMES,
        "video_codec": "h264_nvenc",
        "audio_codec": "aac_320k_dialogue_only",
        "sha256": actual,
        "qc_status": "TECHNICAL_AND_DIRECTOR_PASS_DIALOGUE_ONLY_PENDING_OWNER_PLAYBACK_FOR_FOLEY",
        "purpose": "single complete dialogue-only picture review before Foley",
        "foley_status": "BLOCKED_UNTIL_OWNER_APPROVES_THIS_EXACT_ARTIFACT",
        "crossfade_frames": 0,
        "freeze_frames_added": 0,
        "static_hold_frames_added": 0,
        "approved_dialogue_source": str(VOICE),
        "approved_dialogue_source_sha256": sha256(VOICE),
        "technical_manifest": str(FULL_MANIFEST.relative_to(PROJECT)).replace("\\", "/"),
        "director_qc": str(FULLFILM_DIRECTOR_QC.relative_to(PROJECT)).replace("\\", "/"),
    }
    project = register_project_final_output(
        PROJECTS,
        PROJECT_ID,
        expected_source_fingerprint=str(readiness["sourceFingerprint"]),
        record=record,
    )
    result = {
        "ok": True,
        "registered_at": now_local(),
        "project_id": PROJECT_ID,
        "video": str(FULL_VIDEO),
        "sha256": actual,
        "maestro_final_output": project.get("finalOutput", {}),
        "owner_review": "PENDING",
        "foley": "NOT_STARTED",
    }
    atomic_json(QC / "maestro_registration_dialogue_review_v1.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("prepare", "assemble", "register"))
    args = parser.parse_args()
    result = prepare() if args.stage == "prepare" else assemble() if args.stage == "assemble" else register()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
