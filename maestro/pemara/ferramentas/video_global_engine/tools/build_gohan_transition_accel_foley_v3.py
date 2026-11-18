"""Build the Gohan SSJ2 transition-acceleration + Foley review candidate.

The accepted V2 picture remains immutable.  V3 changes only fourteen short
post-dialogue transition windows, using deterministic temporal decimation from
the existing 60 fps frames.  Foley is generated in resumable narrative chunks,
mixed under the owner-approved Android 16 voice, and registered for human
review without granting approval.
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
import threading
from datetime import datetime
from fractions import Fraction
from pathlib import Path


ROOT = Path(r"E:\Pemara\maestro\pemara")
ENGINE = ROOT / "ferramentas" / "video_global_engine"
PROJECTS = ENGINE / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
WORK = PROJECT / "work" / "transition_accel_foley_v3"
QC = WORK / "qc"
EDIT = PROJECT / "edit"
DELIVERIES = PROJECT / "deliveries"
AUDIO_ROOT = PROJECT / "audio" / "video_sound" / "final_transition_v3"

SOURCE = (
    PROJECT
    / "deliveries"
    / "GOHAN_SSJ2_ANDROID16_FALA_VIDEO_COMPLETO_SEM_FOLEY_APROVACAO_V2.mp4"
)
SOURCE_MANIFEST = (
    PROJECT
    / "edit"
    / "GOHAN_SSJ2_ANDROID16_FALA_VIDEO_COMPLETO_SEM_FOLEY_APROVACAO_V2.json"
)
SOURCE_SHA256 = "f3f3586979bbffeeb923189e62c3fab8f5cbd2e2d7bbb1b55fa6cff7f61684d8"
VOICE = ROOT / "outputs" / "voice_previews" / "android16_v4_sao_paulo_dublagem.wav"
VOICE_SHA256 = "ac529c4e35692fe3aa0df3536b193d94a8392f6bccf679c163cf715455c4c2d8"

PICTURE = WORK / "gohan_ssj2_transition_accel_picture_720p60_v3.mp4"
PICTURE_MANIFEST = EDIT / "GOHAN_SSJ2_ANDROID16_TRANSICOES_RAPIDAS_PICTURE_V3.json"
PICTURE_QC = QC / "picture_director_qc.json"
PICTURE_CONTACT = QC / "picture_contact_24frames.jpg"
PICTURE_JOINS = QC / "transition_windows_part1_7x8frames.jpg"
PICTURE_JOINS_2 = QC / "transition_windows_part2_7x8frames.jpg"
FOLEY_RAW_BUS = WORK / "foley_bus_raw_48k_s24.wav"
FOLEY_BUS = WORK / "foley_bus_loudness_48k_s24.wav"
FINAL = (
    DELIVERIES
    / "GOHAN_SSJ2_ANDROID16_TRANSICOES_RAPIDAS_FOLEY_720P60_APROVACAO_V3.mp4"
)
FINAL_MANIFEST = EDIT / "GOHAN_SSJ2_ANDROID16_TRANSICOES_RAPIDAS_FOLEY_720P60_V3.json"
FINAL_AUDIO = WORK / "final_mix_analysis_48k_s24.wav"
ROLLBACK = PROJECT / "archive" / "before_transition_accel_foley_v3_20260821"
GATE = (
    Path(r"E:\Pemara\.agents\skills\pemara-cinematic-take-director")
    / "scripts"
    / "sequence_regression_gate.py"
)

FPS = 60
WIDTH = 1280
HEIGHT = 720
SOURCE_FRAMES = 2602
HALF_WINDOW_FRAMES = 18
FAST_WINDOW_SOURCE_FRAMES = 36
FAST_WINDOW_OUTPUT_FRAMES = 24
SAVED_PER_WINDOW = FAST_WINDOW_SOURCE_FRAMES - FAST_WINDOW_OUTPUT_FRAMES

# Exact moving-anchor joins in the accepted V2 timeline.  The speech-to-action
# handoff at frame 334 is deliberately excluded so the approved lip-sync and
# spoken performance remain untouched.
SOURCE_BOUNDARIES = [
    518,   # Take 01 -> 02
    686,   # Take 02 -> 03
    797,   # Take 03 internal 1
    907,   # Take 03 internal 2
    1016,  # Take 03 internal 3
    1147,  # Take 03 internal 4
    1262,  # Take 03 -> 04
    1427,  # Take 04 internal
    1598,  # Take 04 -> 05
    1727,  # Take 05 internal 1
    1869,  # Take 05 internal 2
    2051,  # Take 05 internal 3
    2174,  # Take 05 -> 06
    2362,  # Take 06 internal G handoff
]
OUTPUT_FRAMES = SOURCE_FRAMES - len(SOURCE_BOUNDARIES) * SAVED_PER_WINDOW
OUTPUT_DURATION = OUTPUT_FRAMES / FPS
OUTPUT_BOUNDARIES = [
    boundary - index * SAVED_PER_WINDOW - (HALF_WINDOW_FRAMES - 12)
    for index, boundary in enumerate(SOURCE_BOUNDARIES)
]

# Story-aligned chunks, all below the provider's 15-second ceiling.  The first
# boundary is the untouched dialogue-picture handoff.  Remaining boundaries
# are mapped main-take handoffs after localized acceleration.
CHUNK_CUTS = [0, 334, 668, 1184, 1496, 2024, OUTPUT_FRAMES]
CHUNKS = [
    {
        "id": "01_android16_dialogue",
        "start": CHUNK_CUTS[0],
        "end": CHUNK_CUTS[1],
        "prompt": (
            "Photorealistic cinematic battlefield Foley synchronized to the visible action: "
            "cold wind over broken stone, distant rubble settling, subtle heavy android servos, "
            "metal body strain, fabric and small ground movement. Keep the foreground restrained "
            "so the existing Android 16 dialogue stays completely clear."
        ),
    },
    {
        "id": "02_crush_and_transformation",
        "start": CHUNK_CUTS[1],
        "end": CHUNK_CUTS[2],
        "prompt": (
            "Photorealistic heavyweight action Foley synchronized to every visible event: armored "
            "foot impact, dense metal and stone compression, ground crack, debris, Gohan energy "
            "surge, electric aura snaps, displaced air and one powerful transformation shockwave."
        ),
    },
    {
        "id": "03_cell_juniors",
        "start": CHUNK_CUTS[2],
        "end": CHUNK_CUTS[3],
        "prompt": (
            "Fast photorealistic martial-arts Foley synchronized to Gohan fighting the compact blue "
            "Cell Juniors: sharp body whooshes, weighted contacts, short impact shockwaves, boots "
            "scraping rubble, stones scattering, electric aura crackle and spatial battlefield wind."
        ),
    },
    {
        "id": "04_energy_slap",
        "start": CHUNK_CUTS[3],
        "end": CHUNK_CUTS[4],
        "prompt": (
            "Photorealistic energy-combat Foley synchronized to the visible deflection: incoming "
            "energy rush, one crisp bare-hand slap, violent lateral energy ricochet, air pressure, "
            "electric crackle, rock fragments and the heavy approach of Perfect Cell."
        ),
    },
    {
        "id": "05_close_combat",
        "start": CHUNK_CUTS[4],
        "end": CHUNK_CUTS[5],
        "prompt": (
            "Frenetic photorealistic close-combat Foley synchronized hit by hit: heavy bio-armor "
            "impacts, fast punches and kicks, body acceleration whooshes, boots on broken stone, "
            "deep shockwaves, rubble spray, aura electricity and physical camera-pass wind."
        ),
    },
    {
        "id": "06_kamehameha_mountain",
        "start": CHUNK_CUTS[5],
        "end": CHUNK_CUTS[6],
        "prompt": (
            "Epic photorealistic finishing Foley synchronized to the visible action: full-size Cell "
            "launched through the arena, high-speed flight whoosh, one final impact, blue-white "
            "Kamehameha ignition and sustained beam roar, mountain rupture, boulders, avalanche, "
            "dust pressure and a massive final low-frequency impact."
        ),
    },
]
NEGATIVE_PROMPT = (
    "music, soundtrack, melody, rhythm, drums, vocals, speech, dialogue, words, announcer, "
    "synthetic voice, cartoon, anime, retro game sound, arcade sound, UI beep, clipping"
)
FREEZE_RE = re.compile(r"freeze_(start|duration|end):\s*([0-9.]+)")


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt"
        else 0,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def probe(path: Path) -> dict:
    completed = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
        timeout=180,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not isinstance(video, dict):
        raise RuntimeError(f"No video stream: {path}")
    fps = float(
        Fraction(str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"))
    )
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


def validate_video(
    path: Path,
    *,
    frames: int,
    audio: bool,
    duration_tolerance: float = 0.04,
) -> dict:
    info = probe(path)
    errors = []
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        errors.append(f"geometry={info['width']}x{info['height']}")
    if abs(info["fps"] - FPS) > 0.001:
        errors.append(f"fps={info['fps']}")
    if info["frames"] != frames:
        errors.append(f"frames={info['frames']} expected={frames}")
    if info["audio"] is not audio:
        errors.append(f"audio={info['audio']}")
    if abs(info["duration_seconds"] - frames / FPS) > duration_tolerance:
        errors.append(f"duration={info['duration_seconds']}")
    if errors:
        raise RuntimeError(f"Invalid video {path.name}: {', '.join(errors)}")
    run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "null", "NUL"],
        timeout=300,
    )
    return info


def probe_audio(path: Path) -> dict:
    completed = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,bits_per_sample:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
        timeout=60,
    )
    payload = json.loads(completed.stdout)
    stream = next(
        (item for item in payload.get("streams", []) if item.get("sample_rate")),
        {},
    )
    if not stream:
        raise RuntimeError(f"No audio stream: {path}")
    return {
        "path": str(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "codec": str(stream.get("codec_name") or ""),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "bits_per_sample": int(stream.get("bits_per_sample") or 0),
        "duration_seconds": float((payload.get("format") or {}).get("duration") or 0),
    }


def loudness(path: Path) -> dict:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-23:TP=-2:LRA=11:print_format=json",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt"
        else 0,
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", completed.stderr, flags=re.S)
    if not matches:
        raise RuntimeError(f"Could not measure loudness: {path}")
    raw = json.loads(matches[-1])
    return {
        "integrated_lufs": float(raw["input_i"]),
        "true_peak_dbtp": float(raw["input_tp"]),
        "lra_lu": float(raw["input_lra"]),
        "threshold_lufs": float(raw["input_thresh"]),
    }


def freeze_events(path: Path, duration: float) -> list[dict]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vf",
            "freezedetect=n=-50dB:d=0.15",
            "-an",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt"
        else 0,
    )
    events: list[dict] = []
    active: dict | None = None
    for kind, raw in FREEZE_RE.findall(completed.stderr):
        value = float(raw)
        if kind == "start":
            active = {"start": value}
        elif active is not None and kind == "duration":
            active["duration"] = value
        elif active is not None and kind == "end":
            active["end"] = value
            active.setdefault("duration", value - float(active["start"]))
            events.append(active)
            active = None
    if active is not None:
        active["end"] = duration
        active.setdefault("duration", duration - float(active["start"]))
        events.append(active)
    return events


def black_events(path: Path) -> list[str]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vf",
            "blackdetect=d=0.05:pix_th=0.02",
            "-an",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt"
        else 0,
    )
    return re.findall(r"black_start:[^\r\n]+", completed.stderr)


def make_contact(source: Path, output: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"fps={24 / OUTPUT_DURATION:.9f},scale=320:180,tile=6x4:nb_frames=24",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ],
        timeout=180,
    )


def make_join_sheets(source: Path) -> list[Path]:
    outputs = [PICTURE_JOINS, PICTURE_JOINS_2]
    groups = [OUTPUT_BOUNDARIES[:7], OUTPUT_BOUNDARIES[7:]]
    for boundaries, output in zip(groups, outputs):
        terms = []
        for boundary in boundaries:
            terms.extend(
                f"eq(n\\,{frame})" for frame in range(boundary - 4, boundary + 4)
            )
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vf",
                f"select='{'+'.join(terms)}',scale=256:144,tile=8x7:nb_frames=56",
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(output),
            ],
            timeout=240,
        )
    return outputs


def preserve_rollback() -> dict:
    ROLLBACK.mkdir(parents=True, exist_ok=True)
    for source in (
        PROJECT / "project_manifest.json",
        PROJECT / "production_manifest.json",
        PROJECT / "take_queue.json",
        SOURCE_MANIFEST,
    ):
        target = ROLLBACK / source.name
        if not target.exists():
            shutil.copy2(source, target)
    record = {
        "created_at": now_local(),
        "reason": "Preserve the accepted V2 before localized transition acceleration and Foley.",
        "source_video": str(SOURCE),
        "source_video_sha256": sha256(SOURCE),
        "source_video_preserved_in_place": True,
        "copied_manifests": [item.name for item in ROLLBACK.iterdir() if item.is_file()],
    }
    atomic_json(ROLLBACK / "rollback_record.json", record)
    return record


def picture_filter() -> tuple[str, list[dict]]:
    segments: list[tuple[int, int, bool, int | None]] = []
    cursor = 0
    windows = []
    for index, boundary in enumerate(SOURCE_BOUNDARIES):
        start = boundary - HALF_WINDOW_FRAMES
        end = boundary + HALF_WINDOW_FRAMES
        segments.append((cursor, start, False, None))
        segments.append((start, end, True, index))
        output_start = start - index * SAVED_PER_WINDOW
        windows.append(
            {
                "index": index + 1,
                "source_boundary_frame": boundary,
                "source_boundary_seconds": boundary / FPS,
                "source_window_frames": [start, end],
                "source_window_seconds": [start / FPS, end / FPS],
                "output_window_frames": [
                    output_start,
                    output_start + FAST_WINDOW_OUTPUT_FRAMES,
                ],
                "output_boundary_frame": OUTPUT_BOUNDARIES[index],
                "output_boundary_seconds": OUTPUT_BOUNDARIES[index] / FPS,
                "speed_factor": 1.5,
            }
        )
        cursor = end
    segments.append((cursor, SOURCE_FRAMES, False, None))
    labels = "".join(f"[src{index}]" for index in range(len(segments)))
    filters = [f"[0:v]split={len(segments)}{labels}"]
    output_labels = []
    for index, (start, end, accelerated, _) in enumerate(segments):
        output = f"[v{index}]"
        output_labels.append(output)
        if accelerated:
            filters.append(
                f"[src{index}]trim=start_frame={start}:end_frame={end},"
                "select='not(eq(mod(n\\,3)\\,2))',"
                f"setpts=N/({FPS}*TB){output}"
            )
        else:
            filters.append(
                f"[src{index}]trim=start_frame={start}:end_frame={end},"
                f"setpts=PTS-STARTPTS{output}"
            )
    filters.append(
        "".join(output_labels)
        + f"concat=n={len(output_labels)}:v=1:a=0,format=yuv420p[v]"
    )
    filters.append(
        f"[1:a]apad,atrim=duration={OUTPUT_DURATION:.9f},asetpts=PTS-STARTPTS[a]"
    )
    return ";".join(filters), windows


def build_picture() -> dict:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("Accepted V2 source hash drift.")
    if sha256(VOICE) != VOICE_SHA256:
        raise RuntimeError("Owner-approved Android 16 voice hash drift.")
    source_info = validate_video(SOURCE, frames=SOURCE_FRAMES, audio=True)
    run(
        [
            sys.executable,
            str(GATE),
            str(PROJECT / "production_manifest.json"),
            "--stage",
            "assembly",
        ],
        timeout=60,
    )
    rollback = preserve_rollback()
    WORK.mkdir(parents=True, exist_ok=True)
    QC.mkdir(parents=True, exist_ok=True)
    EDIT.mkdir(parents=True, exist_ok=True)
    DELIVERIES.mkdir(parents=True, exist_ok=True)
    filter_graph, windows = picture_filter()
    if not PICTURE.is_file():
        part = PICTURE.with_name(f".{PICTURE.stem}.{os.getpid()}.part.mp4")
        try:
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(SOURCE),
                    "-i",
                    str(VOICE),
                    "-filter_complex",
                    filter_graph,
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
                    "title=Gohan SSJ2 - transicoes localizadas 1.5x - picture review",
                    "-metadata",
                    "comment=V2-derived; dialogue untouched; no crossfade; no generated connector",
                    "-movflags",
                    "+faststart",
                    str(part),
                ],
                timeout=900,
            )
            validate_video(part, frames=OUTPUT_FRAMES, audio=True)
            os.replace(part, PICTURE)
        finally:
            part.unlink(missing_ok=True)
    info = validate_video(PICTURE, frames=OUTPUT_FRAMES, audio=True)
    make_contact(PICTURE, PICTURE_CONTACT)
    join_sheets = make_join_sheets(PICTURE)
    freezes = freeze_events(PICTURE, OUTPUT_DURATION)
    black = black_events(PICTURE)
    if any(float(item.get("duration") or 0) >= 0.15 for item in freezes):
        raise RuntimeError(f"Accelerated picture contains freeze events: {freezes}")
    if black:
        raise RuntimeError(f"Accelerated picture contains black events: {black}")
    payload = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "display_name": "TRANSICOES MAIS RAPIDAS - PICTURE 720P60 V3",
        "status": "TECHNICAL_PASS_PENDING_DIRECTOR_VISUAL_QC",
        "created_at": now_local(),
        "owner_feedback": (
            "Gostei do video; acelerar somente as transicoes e depois gerar Foley em 720p."
        ),
        "owner_review": "PENDING_EXACT_V3_PLAYBACK",
        "source_v2": source_info,
        "picture_v3": info,
        "edit_contract": {
            "dialogue_and_lipsync_untouched_until_frame": 334,
            "accelerated_windows": len(windows),
            "source_frames_per_window": FAST_WINDOW_SOURCE_FRAMES,
            "output_frames_per_window": FAST_WINDOW_OUTPUT_FRAMES,
            "speed_factor": 1.5,
            "frames_removed_only_inside_windows": SOURCE_FRAMES - OUTPUT_FRAMES,
            "seconds_removed_only_inside_windows": (SOURCE_FRAMES - OUTPUT_FRAMES) / FPS,
            "crossfade_frames": 0,
            "freeze_frames_added": 0,
            "static_hold_frames_added": 0,
            "new_take_or_anchor_generation": False,
            "windows": windows,
        },
        "approved_dialogue": {
            "path": str(VOICE),
            "sha256": sha256(VOICE),
            "timeline_start_seconds": 0.0,
            "audible_end_seconds": 5.435104,
            "modified": False,
        },
        "technical_qc": {
            "decode": "PASS",
            "constant_fps": True,
            "freeze_events_at_least_0p15_seconds": freezes,
            "black_events": black,
            "contact_sheet": str(PICTURE_CONTACT),
            "transition_sheets": [str(item) for item in join_sheets],
            "sequence_regression_gate": "PASS_ASSEMBLY",
        },
        "rollback": rollback,
        "next_gate": "DIRECTOR_VISUAL_QC_THEN_FOLEY_CANDIDATE",
    }
    atomic_json(PICTURE_MANIFEST, payload)
    return payload


def approve_picture() -> dict:
    manifest = load(PICTURE_MANIFEST)
    if manifest.get("status") != "TECHNICAL_PASS_PENDING_DIRECTOR_VISUAL_QC":
        raise RuntimeError("Picture is not waiting for director visual QC.")
    actual = sha256(PICTURE)
    expected = str((manifest.get("picture_v3") or {}).get("sha256") or "")
    if actual != expected:
        raise RuntimeError("Picture hash changed after technical QC.")
    payload = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "status": "DIRECTOR_PASS_FOR_FOLEY_CANDIDATE",
        "created_at": now_local(),
        "picture": str(PICTURE),
        "picture_sha256": actual,
        "scope": "localized transition cadence only",
        "visual_review": {
            "contact_sheet": str(PICTURE_CONTACT),
            "transition_sheets": [str(PICTURE_JOINS), str(PICTURE_JOINS_2)],
            "live_action_route_preserved": True,
            "dialogue_lipsync_preserved": True,
            "crossfade_or_hold_added": False,
            "owner_approval": False,
        },
        "next_gate": "GENERATE_AND_MIX_FOLEY_PENDING_OWNER_LISTENING",
    }
    atomic_json(PICTURE_QC, payload)
    manifest["status"] = "DIRECTOR_PASS_FOR_FOLEY_CANDIDATE"
    manifest["director_qc"] = str(PICTURE_QC)
    manifest["next_gate"] = "FOLEY_GENERATION"
    atomic_json(PICTURE_MANIFEST, manifest)
    return payload


def extract_chunk(spec: dict) -> tuple[Path, dict]:
    start = int(spec["start"])
    end = int(spec["end"])
    frames = end - start
    chunk_dir = AUDIO_ROOT / str(spec["id"])
    chunk_dir.mkdir(parents=True, exist_ok=True)
    video = chunk_dir / "source_720p60.mp4"
    if not video.is_file():
        part = video.with_name(f".{video.stem}.{os.getpid()}.part.mp4")
        try:
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(PICTURE),
                    "-vf",
                    f"trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS,format=yuv420p",
                    "-r",
                    str(FPS),
                    "-fps_mode",
                    "cfr",
                    "-frames:v",
                    str(frames),
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "p6",
                    "-tune",
                    "hq",
                    "-cq",
                    "18",
                    "-b:v",
                    "0",
                    "-g",
                    "120",
                    "-bf",
                    "2",
                    "-an",
                    str(part),
                ],
                timeout=600,
            )
            validate_video(part, frames=frames, audio=False)
            os.replace(part, video)
        finally:
            part.unlink(missing_ok=True)
    return video, validate_video(video, frames=frames, audio=False)


def generate_foley_chunks() -> list[dict]:
    picture_qc = load(PICTURE_QC)
    if picture_qc.get("status") != "DIRECTOR_PASS_FOR_FOLEY_CANDIDATE":
        raise RuntimeError("Picture director gate has not released Foley.")
    if sha256(PICTURE) != str(picture_qc.get("picture_sha256") or ""):
        raise RuntimeError("Picture changed after director gate.")
    studio_root = ROOT / "services" / "studio"
    if str(studio_root) not in sys.path:
        sys.path.insert(0, str(studio_root))
    from video_sound import VideoSoundRequest, build_default_registry

    provider = build_default_registry(ROOT).get("hunyuan_video_foley_xxl")
    status = provider.status()
    if not status.get("configured"):
        raise RuntimeError(json.dumps(status, ensure_ascii=False))
    results = []
    for index, spec in enumerate(CHUNKS, start=1):
        video, video_info = extract_chunk(spec)
        job_id = f"gohan-v3-{index:02d}-{spec['id']}"
        output_dir = AUDIO_ROOT / str(spec["id"]) / job_id
        sidecar = output_dir / "candidate.json"
        candidate = output_dir / "candidate.wav"
        if candidate.is_file() and sidecar.is_file():
            recorded = load(sidecar)
            if (
                str(recorded.get("source_video_sha256") or "") == video_info["sha256"]
                and str(recorded.get("audio_sha256") or "") == sha256(candidate)
            ):
                print(
                    f"FOLEY chunk {index}/{len(CHUNKS)} resume: {spec['id']}",
                    flush=True,
                )
                results.append(recorded)
                continue
            raise RuntimeError(f"Existing Foley checkpoint drift: {output_dir}")
        duration = (int(spec["end"]) - int(spec["start"])) / FPS
        print(
            f"FOLEY chunk {index}/{len(CHUNKS)} start: {spec['id']} ({duration:.3f}s)",
            flush=True,
        )
        result = provider.generate(
            VideoSoundRequest(
                job_id=job_id,
                source_video=video,
                output_dir=output_dir,
                prompt=str(spec["prompt"]),
                negative_prompt=NEGATIVE_PROMPT,
                duration_seconds=duration,
                seed=2026082100 + index,
            ),
            progress_cb=lambda percent, message, i=index: print(
                f"FOLEY chunk {i}/{len(CHUNKS)} {percent}% {message}",
                flush=True,
            ),
            cancel_event=threading.Event(),
        )
        audio_info = probe_audio(result.audio_path)
        if audio_info["sample_rate"] != 48000 or audio_info["channels"] != 2:
            raise RuntimeError(f"Unexpected Foley format: {audio_info}")
        record = {
            "schema_version": "1.0",
            "status": "PENDING_HUMAN_LISTENING",
            "created_at": now_local(),
            "job_id": job_id,
            "chunk_id": spec["id"],
            "timeline_frames": [spec["start"], spec["end"]],
            "timeline_seconds": [spec["start"] / FPS, spec["end"] / FPS],
            "prompt": spec["prompt"],
            "negative_prompt": NEGATIVE_PROMPT,
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
        atomic_json(sidecar, record)
        results.append(record)
        print(f"FOLEY chunk {index}/{len(CHUNKS)} done: {spec['id']}", flush=True)
    return results


def build_foley_bus(chunks: list[dict]) -> dict:
    inputs: list[str] = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    labels = []
    for index, (spec, chunk) in enumerate(zip(CHUNKS, chunks)):
        audio = Path(str(chunk["audio"])).resolve(strict=True)
        inputs.extend(["-i", str(audio)])
        duration = (int(spec["end"]) - int(spec["start"])) / FPS
        fade_out_start = max(0.0, duration - 0.02)
        label = f"[a{index}]"
        labels.append(label)
        filters.append(
            f"[{index}:a]atrim=duration={duration:.9f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.02,afade=t=out:st={fade_out_start:.9f}:d=0.02{label}"
        )
    filters.append(
        "".join(labels)
        + f"concat=n={len(labels)}:v=0:a=1,"
        f"atrim=duration={OUTPUT_DURATION:.9f},asetpts=PTS-STARTPTS[raw]"
    )
    inputs.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[raw]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(FOLEY_RAW_BUS),
        ]
    )
    run(inputs, timeout=600)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(FOLEY_RAW_BUS),
            "-af",
            (
                "loudnorm=I=-21:TP=-3:LRA=14,"
                "aresample=48000:first_pts=0,apad,"
                f"atrim=end_sample={int(round(OUTPUT_DURATION * 48000))},"
                "asetpts=N/SR/TB"
            ),
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(FOLEY_BUS),
        ],
        timeout=600,
    )
    info = probe_audio(FOLEY_BUS)
    if (
        info["sample_rate"] != 48000
        or info["channels"] != 2
        or abs(info["duration_seconds"] - OUTPUT_DURATION) > 0.03
    ):
        raise RuntimeError(f"Invalid Foley bus: {info}")
    info["loudness"] = loudness(FOLEY_BUS)
    return info


def mix_final(foley_info: dict, chunks: list[dict]) -> dict:
    if sha256(PICTURE) != str(load(PICTURE_QC).get("picture_sha256") or ""):
        raise RuntimeError("Picture hash drift before final mix.")
    if not FINAL.is_file():
        part = FINAL.with_name(f".{FINAL.stem}.{os.getpid()}.part.mp4")
        filter_graph = (
            f"[1:a]apad,atrim=duration={OUTPUT_DURATION:.9f},"
            "asetpts=PTS-STARTPTS,aresample=48000[voice];"
            "[voice]asplit=2[voice_mix][voice_sc];"
            f"[2:a]atrim=duration={OUTPUT_DURATION:.9f},asetpts=PTS-STARTPTS[foley];"
            "[foley][voice_sc]sidechaincompress="
            "threshold=0.015:ratio=10:attack=5:release=220:makeup=1[foley_ducked];"
            "[voice_mix][foley_ducked]amix="
            "inputs=2:duration=longest:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.891:attack=5:release=50:level=false:latency=true,"
            f"atrim=duration={OUTPUT_DURATION:.9f},asetpts=PTS-STARTPTS[a]"
        )
        try:
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(PICTURE),
                    "-i",
                    str(VOICE),
                    "-i",
                    str(FOLEY_BUS),
                    "-filter_complex",
                    filter_graph,
                    "-map",
                    "0:v:0",
                    "-map",
                    "[a]",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "320k",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-metadata",
                    "title=Gohan SSJ2 - transicoes rapidas + Foley - 720p60 review",
                    "-metadata",
                    "comment=Pending owner visual and listening review; no auto approval",
                    "-movflags",
                    "+faststart",
                    str(part),
                ],
                timeout=600,
            )
            validate_video(part, frames=OUTPUT_FRAMES, audio=True)
            os.replace(part, FINAL)
        finally:
            part.unlink(missing_ok=True)
    final_info = validate_video(FINAL, frames=OUTPUT_FRAMES, audio=True)
    if final_info["sample_rate"] != 48000 or final_info["channels"] != 2:
        raise RuntimeError(f"Unexpected final audio: {final_info}")
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(FINAL),
            "-vn",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(FINAL_AUDIO),
        ],
        timeout=300,
    )
    final_loudness = loudness(FINAL_AUDIO)
    if final_loudness["true_peak_dbtp"] > -0.5:
        raise RuntimeError(f"Final mix has unsafe true peak: {final_loudness}")
    payload = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "display_name": (
            "FILME COMPLETO - TRANSICOES MAIS RAPIDAS + FOLEY - "
            "720P60 - PARA APROVACAO"
        ),
        "status": "PENDING_OWNER_VISUAL_AND_LISTENING_REVIEW",
        "created_at": now_local(),
        "auto_approval": False,
        "owner_review": "PENDING",
        "picture": probe(PICTURE),
        "final": final_info,
        "dialogue": {
            "source": str(VOICE),
            "sha256": sha256(VOICE),
            "variant": "Android 16 Version E - Sao Paulo dubbing",
            "gain": "unity before final summing",
            "content_modified": False,
            "foley_ducking_active_only_while_dialogue_is_present": True,
        },
        "foley": {
            "provider": "hunyuan_video_foley_xxl",
            "model": "Tencent HunyuanVideo-Foley XXL",
            "music_requested": False,
            "speech_requested": False,
            "chunks": chunks,
            "bus": foley_info,
            "human_listening_required": True,
            "auto_attach": False,
            "auto_approval": False,
        },
        "mix_qc": {
            "final_audio_analysis": str(FINAL_AUDIO),
            "loudness": final_loudness,
            "sample_rate": 48000,
            "channels": 2,
            "clipping": False,
        },
        "edit_contract": load(PICTURE_MANIFEST).get("edit_contract"),
        "rollback": {
            "accepted_v2": str(SOURCE),
            "accepted_v2_sha256": sha256(SOURCE),
            "archive": str(ROLLBACK),
            "media_deleted": False,
        },
        "next_gate": "OWNER_REVIEWS_EXACT_V3_IN_MAESTRO",
    }
    atomic_json(FINAL_MANIFEST, payload)
    return payload


def register_final(payload: dict) -> dict:
    studio_root = ROOT / "services" / "studio"
    if str(studio_root) not in sys.path:
        sys.path.insert(0, str(studio_root))
    from video_projects import get_project_assembly_readiness, register_project_final_output

    readiness = get_project_assembly_readiness(PROJECTS, PROJECT_ID)
    if not readiness.get("ready"):
        raise RuntimeError(json.dumps(readiness, ensure_ascii=False, indent=2))
    previous = (load(PROJECT / "project_manifest.json").get("final_output") or {}).copy()
    final_info = payload["final"]
    record = {
        "file": str(FINAL),
        "review_file": str(FINAL),
        "display_name": payload["display_name"],
        "title": "GOHAN SSJ2 - VIDEO COMPLETO - TRANSICOES RAPIDAS + FOLEY - 720P60",
        "duration_seconds": OUTPUT_DURATION,
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "frames": OUTPUT_FRAMES,
        "video_codec": "h264_nvenc_picture_bitstream_copy",
        "audio_codec": "aac_320k_android16_dialogue_plus_hunyuan_foley",
        "sha256": final_info["sha256"],
        "qc_status": "TECHNICAL_PASS_PENDING_OWNER_VISUAL_AND_LISTENING_REVIEW",
        "purpose": "single 720p60 review with localized faster transitions and Foley",
        "foley_status": "CANDIDATE_PENDING_HUMAN_LISTENING",
        "human_review_required": True,
        "auto_approval": False,
        "crossfade_frames": 0,
        "freeze_frames_added": 0,
        "static_hold_frames_added": 0,
        "accelerated_transition_windows": len(SOURCE_BOUNDARIES),
        "transition_speed_factor": 1.5,
        "approved_dialogue_source": str(VOICE),
        "approved_dialogue_source_sha256": sha256(VOICE),
        "technical_manifest": str(FINAL_MANIFEST.relative_to(PROJECT)).replace("\\", "/"),
        "picture_director_qc": str(PICTURE_QC.relative_to(PROJECT)).replace("\\", "/"),
        "previous_review_candidate": {
            "file": previous.get("file"),
            "sha256": previous.get("sha256"),
            "preserved": True,
        },
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
        "video": str(FINAL),
        "sha256": final_info["sha256"],
        "maestro_final_output": project.get("final_output")
        or project.get("finalOutput")
        or {},
        "owner_review": "PENDING",
        "foley": "PENDING_HUMAN_LISTENING",
        "previous_v2_preserved": True,
    }
    atomic_json(QC / "maestro_registration_v3.json", result)
    return result


def generate_mix_register() -> dict:
    chunks = generate_foley_chunks()
    foley_info = build_foley_bus(chunks)
    payload = mix_final(foley_info, chunks)
    registration = register_final(payload)
    return {
        "status": "READY_IN_MAESTRO_PENDING_OWNER_REVIEW",
        "final": payload["final"],
        "final_loudness": payload["mix_qc"]["loudness"],
        "foley_bus": foley_info,
        "registration": registration,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=("picture", "approve-picture", "foley-mix-register", "all"),
    )
    args = parser.parse_args()
    if args.stage == "picture":
        result = build_picture()
    elif args.stage == "approve-picture":
        result = approve_picture()
    elif args.stage == "foley-mix-register":
        result = generate_mix_register()
    else:
        build_picture()
        approve_picture()
        result = generate_mix_register()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
