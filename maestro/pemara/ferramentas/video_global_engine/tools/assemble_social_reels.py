#!/usr/bin/env python3
"""Assemble the canonical Ritmos intro and F1->F2 transition as PT-BR videos.

The script is intentionally read-only with respect to Maestro state: it does not
change take approval, queues, runtime assets, or source masters. It resolves the
current take files from each canonical queue, preserves their order, burns captions,
mixes the official music, renders a 1920x1080 H.264/AAC master for each project,
and mirrors every completed delivery bundle to Google Drive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any


ENGINE_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ENGINE_ROOT / "projetos"
INTRO_ROOT = PROJECTS_ROOT / "intro_ritmos_revolta"
TRANSITION_ROOT = PROJECTS_ROOT / "transicao_f1_f2_cold_iron_wan"
GAME_ROOT = PROJECTS_ROOT / "Ritmos da Revolta"
FINAL_DRIVE_DIR = Path(
    os.environ.get("PEMARA_FINALS_DIR", "G:/Meu Drive/Takes Finais")
)

INTRO_QUEUE = INTRO_ROOT / "take_queue_novo_plano_20260720.json"
INTRO_PLAN = INTRO_ROOT / "direction" / "intro_full_editorial_plan.json"
INTRO_MUSIC = Path(
    "E:/Pemara/Ritmos da Revolta/assets/sounds/music/Sunlit_Concrete_Cracks.mp3"
)
INTRO_LOGO_SOURCE = (
    GAME_ROOT / "assets" / "backgrounds" / "menu_bg.png"
)
INTRO_OUTPUT = (
    INTRO_ROOT / "output" / "reels" / "ritmos_intro_reel_ptbr_master.mp4"
)

TRANSITION_QUEUE = TRANSITION_ROOT / "take_queue.json"
TRANSITION_TIMING = TRANSITION_ROOT / "direction" / "audio_structure.json"
TRANSITION_MUSIC = Path(
    "E:/Pemara/maestro/pemara/plano_editor_videos/F1-F2/Cold_Iron_Hours.mp3"
)
TRANSITION_OUTPUT = (
    TRANSITION_ROOT
    / "output"
    / "reels"
    / "transicao_f1_f2_reel_ptbr_master.mp4"
)
TRANSITION2_ROOT = PROJECTS_ROOT / "transicao_f2_f3_raizes_ferro_wan"
TRANSITION2_QUEUE = TRANSITION2_ROOT / "take_queue.json"
TRANSITION2_TIMING = TRANSITION2_ROOT / "direction" / "audio_structure.json"
TRANSITION2_MUSIC = Path(
    "E:/Pemara/Ritmos da Revolta/assets/sounds/music/Raízes_de_Ferro_fase3.wav"
)
TRANSITION2_OUTPUT = (
    TRANSITION2_ROOT
    / "output"
    / "reels"
    / "transicao_f2_f3_reel_ptbr_master.mp4"
)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
VIDEO_CRF = "17"
VIDEO_PRESET = "medium"
AUDIO_BITRATE = "320k"
TARGET_LUFS = -14.0
TARGET_TP = -2.0
TARGET_LRA = 11.0
SCRIPT_VERSION = "1.3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--project",
        choices=("intro", "transition", "transition2", "all"),
        default="all",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--skip-drive",
        action="store_true",
        help="Mantem a entrega somente no projeto e em PRONTOS.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"{name} was not found in PATH")
    return executable


def run(
    command: list[str],
    label: str,
    *,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(f"[social-reels] {label}", flush=True)
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            f"{label} failed: {details or f'exit {exc.returncode}'}"
        ) from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def publish_final_bundle(
    output: Path,
    ass_path: Path,
    srt_path: Path,
    sidecar: Path,
) -> list[Path]:
    """Atomically mirror every final deliverable to the mounted Google Drive."""
    contact = output.with_name(output.stem + "_contact.jpg")
    sources = [output, ass_path, srt_path, sidecar, contact]
    missing = [path for path in sources if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Final bundle is incomplete: " + ", ".join(str(path) for path in missing)
        )

    FINAL_DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    published: list[Path] = []
    for source in sources:
        destination = FINAL_DRIVE_DIR / source.name
        temporary = destination.with_name(destination.name + ".uploading")
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        published.append(destination)
    print(
        "[social-reels] published final bundle to "
        f"{FINAL_DRIVE_DIR.resolve()}",
        flush=True,
    )
    return published


def probe(path: Path, ffprobe: str, *, count_frames: bool = False) -> dict[str, Any]:
    command = [ffprobe, "-v", "error"]
    if count_frames:
        command.append("-count_frames")
    command.extend(
        [
            "-show_entries",
            (
                "stream=index,codec_type,codec_name,width,height,pix_fmt,"
                "r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,"
                "sample_rate,channels:format=duration,size,bit_rate"
            ),
            "-of",
            "json",
            str(path),
        ]
    )
    result = run(command, f"ffprobe {path.name}", capture=True)
    value = json.loads(result.stdout)
    if not value.get("streams"):
        raise RuntimeError(f"No streams found in {path}")
    return value


def duration(probe_data: dict[str, Any]) -> float:
    return float((probe_data.get("format") or {}).get("duration") or 0.0)


def first_existing(values: list[Any]) -> Path | None:
    for value in values:
        if not value:
            continue
        path = Path(str(value))
        if path.is_file():
            return path.resolve()
    return None


def resolve_take_source(
    project_root: Path,
    take: dict[str, Any],
    *,
    allow_unapproved_technical: bool = False,
) -> tuple[Path, str, str]:
    status = str(take.get("maestro_status") or "").upper()
    video = take.get("video") or {}
    qc = take.get("qc") or {}
    approved = status == "APPROVED"
    technical_exception = (
        allow_unapproved_technical
        and status == "REJECTED"
        and str(qc.get("technical_status") or "").upper() == "PASS"
        and str(qc.get("status") or "").lower() == "ready_for_user_review"
    )
    if not approved and not technical_exception:
        raise RuntimeError(
            f"{take.get('id')}: take is not eligible (Maestro status {status!r})"
        )

    source = first_existing(
        [
            video.get("output_active"),
            video.get("output_upscaled"),
            video.get("output_upscale_candidate"),
            video.get("output_final"),
            video.get("output_review_candidate"),
        ]
    )
    if source is None:
        candidates = [
            str(video.get("output_active") or ""),
            str(video.get("output_final") or ""),
            str(video.get("output_review_candidate") or ""),
        ]
        names = [Path(value).name for value in candidates if value]
        for name in names:
            matches = list(project_root.rglob(name))
            if matches:
                source = matches[0].resolve()
                break
    if source is None:
        raise RuntimeError(f"{take.get('id')}: no current source file was found")
    eligibility = "approved" if approved else "technical_pass_user_assembly_exception"
    return source, status, eligibility


def distribute_durations(
    groups: list[dict[str, Any]],
    target_total: float,
) -> list[dict[str, Any]]:
    """Use native footage only, reallocating surplus without stretching or freezing."""
    for group in groups:
        native = sum(float(item["actual_duration"]) for item in group["items"])
        requested = float(group["target_duration"])
        group["native_duration"] = native
        group["use_duration"] = min(native, requested)

    deficit = target_total - sum(float(group["use_duration"]) for group in groups)
    if deficit > 0.0005:
        for group in reversed(groups):
            capacity = float(group["native_duration"]) - float(group["use_duration"])
            addition = min(capacity, deficit)
            group["use_duration"] = float(group["use_duration"]) + addition
            deficit -= addition
            if deficit <= 0.0005:
                break
    if deficit > 0.0005:
        raise RuntimeError(
            f"Native footage is {deficit:.3f}s short; stretching/freeze is forbidden"
        )

    surplus = sum(float(group["use_duration"]) for group in groups) - target_total
    if surplus > 0.0005:
        for group in reversed(groups):
            removable = min(float(group["use_duration"]), surplus)
            group["use_duration"] = float(group["use_duration"]) - removable
            surplus -= removable
            if surplus <= 0.0005:
                break

    for group in groups:
        items = group["items"]
        desired = float(group["use_duration"])
        for item in items:
            item["use_duration"] = min(
                float(item["target_duration"]),
                float(item["actual_duration"]),
            )
        missing = desired - sum(float(item["use_duration"]) for item in items)
        if missing > 0.0005:
            for item in reversed(items):
                capacity = float(item["actual_duration"]) - float(item["use_duration"])
                addition = min(capacity, missing)
                item["use_duration"] = float(item["use_duration"]) + addition
                missing -= addition
                if missing <= 0.0005:
                    break
        if missing > 0.0005:
            raise RuntimeError(
                f"Group {group['id']} cannot cover its allocated duration"
            )
        extra = sum(float(item["use_duration"]) for item in items) - desired
        if extra > 0.0005:
            for item in reversed(items):
                removable = min(float(item["use_duration"]), extra)
                item["use_duration"] = float(item["use_duration"]) - removable
                extra -= removable
                if extra <= 0.0005:
                    break

    planned = sum(
        float(item["use_duration"])
        for group in groups
        for item in group["items"]
    )
    if not math.isclose(planned, target_total, abs_tol=0.002):
        raise RuntimeError(f"Duration allocation mismatch: {planned} vs {target_total}")
    return groups


def quantize_plan_frames(plan: dict[str, Any]) -> dict[str, Any]:
    """Convert allocated seconds to an exact CFR frame budget without padding."""
    target_frames = round(float(plan["target_duration"]) * FPS)
    items = [item for group in plan["groups"] for item in group["items"]]
    for item in items:
        ideal = float(item["use_duration"]) * FPS
        available = math.floor(float(item["actual_duration"]) * FPS + 1e-6)
        item["available_frames"] = available
        item["use_frames"] = min(math.floor(ideal + 1e-6), available)
        item["_frame_fraction"] = ideal - math.floor(ideal + 1e-6)

    missing = target_frames - sum(int(item["use_frames"]) for item in items)
    if missing > 0:
        candidates = sorted(
            items,
            key=lambda item: (float(item["_frame_fraction"]), int(item["available_frames"])),
            reverse=True,
        )
        while missing > 0:
            progressed = False
            for item in candidates:
                if int(item["use_frames"]) < int(item["available_frames"]):
                    item["use_frames"] = int(item["use_frames"]) + 1
                    missing -= 1
                    progressed = True
                    if missing == 0:
                        break
            if not progressed:
                raise RuntimeError(
                    "Native frame budget cannot cover the requested CFR duration"
                )
    elif missing < 0:
        to_remove = -missing
        candidates = sorted(
            items,
            key=lambda item: float(item["_frame_fraction"]),
        )
        while to_remove > 0:
            progressed = False
            for item in candidates:
                if int(item["use_frames"]) > 1:
                    item["use_frames"] = int(item["use_frames"]) - 1
                    to_remove -= 1
                    progressed = True
                    if to_remove == 0:
                        break
            if not progressed:
                raise RuntimeError("Could not reduce CFR frame allocation safely")

    for item in items:
        item["use_duration"] = int(item["use_frames"]) / FPS
        item.pop("_frame_fraction", None)
    for group in plan["groups"]:
        group["use_duration"] = sum(
            float(item["use_duration"]) for item in group["items"]
        )
    plan["target_frames"] = target_frames
    plan["target_duration"] = target_frames / FPS
    return plan


def build_intro_plan(ffprobe: str) -> dict[str, Any]:
    queue = load_json(INTRO_QUEUE)
    editorial = load_json(INTRO_PLAN)
    queue_by_id = {str(item["id"]): item for item in queue.get("takes", [])}
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for slot in editorial["editorial_timeline"]:
        editorial_id = str(slot["editorial_id"])
        block_id = re.match(r"^\d+", editorial_id)
        if not block_id:
            raise RuntimeError(f"Invalid editorial id: {editorial_id}")
        take_id = str(slot.get("existing_take_id") or editorial_id)
        take = queue_by_id.get(take_id)
        if not take:
            raise RuntimeError(f"Intro take missing from queue: {take_id}")
        source, status, eligibility = resolve_take_source(INTRO_ROOT, take)
        media_probe = probe(source, ffprobe)
        actual = duration(media_probe)
        if actual <= 0.1:
            raise RuntimeError(f"{take_id}: invalid source duration {actual}")
        normalized_block_id = str(int(block_id.group(0)))
        group = grouped.setdefault(
            normalized_block_id,
            {
                "id": normalized_block_id,
                "caption": "",
                "runtime_title": "",
                "target_duration": 0.0,
                "items": [],
            },
        )
        group["target_duration"] += float(slot["edit_duration"])
        group["items"].append(
            {
                "id": take_id,
                "status": status,
                "eligibility": eligibility,
                "source": source,
                "target_duration": float(slot["edit_duration"]),
                "actual_duration": actual,
                "probe": media_probe,
            }
        )

    story_by_block = {
        str(item["block"]): item for item in editorial["story_blocks"]
    }
    for block_id, group in grouped.items():
        story = story_by_block[block_id]
        group["caption"] = str(story.get("caption") or "")
        group["runtime_title"] = str(story.get("runtime_title") or "")

    target_total = float(editorial["audio_measurement"]["duration_seconds"])
    groups = distribute_durations(list(grouped.values()), target_total)
    plan = quantize_plan_frames({
        "project_id": "intro_ritmos_revolta",
        "project_root": INTRO_ROOT,
        "music": INTRO_MUSIC,
        "output": INTRO_OUTPUT,
        "target_duration": target_total,
        "groups": groups,
        "exceptions": [],
    })
    plan["logo"] = {
        "source": INTRO_LOGO_SOURCE,
        "crop": "800:380:560:30",
        "width": 1000,
        "start": sum(float(group["use_duration"]) for group in plan["groups"][:-1]),
        "end": float(plan["target_duration"]),
        "composition": "screen",
    }
    return plan


def build_transition_plan(
    ffprobe: str,
    *,
    project_id: str = "transicao_f1_f2_cold_iron_wan",
    project_root: Path = TRANSITION_ROOT,
    queue_path: Path = TRANSITION_QUEUE,
    timing_path: Path = TRANSITION_TIMING,
    music_path: Path = TRANSITION_MUSIC,
    output_path: Path = TRANSITION_OUTPUT,
    allow_unapproved_technical: bool = True,
) -> dict[str, Any]:
    queue = load_json(queue_path)
    timing = load_json(timing_path)
    queue_by_id = {str(item["id"]): item for item in queue.get("takes", [])}
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    exceptions: list[dict[str, str]] = []

    microtakes = timing.get("microtakes") or [
        item
        for slide in timing.get("slides", [])
        for item in slide.get("microtakes", [])
    ]
    for slot in microtakes:
        take_id = str(slot["id"])
        take = queue_by_id.get(take_id)
        if not take:
            raise RuntimeError(f"Transition take missing from queue: {take_id}")
        source, status, eligibility = resolve_take_source(
            project_root,
            take,
            allow_unapproved_technical=allow_unapproved_technical,
        )
        if eligibility != "approved":
            exceptions.append(
                {
                    "take_id": take_id,
                    "maestro_status": status,
                    "eligibility": eligibility,
                    "note": (
                        "Included because the current user explicitly said the takes "
                        "were ready for assembly; Maestro approval was not changed."
                    ),
                }
            )
        media_probe = probe(source, ffprobe)
        actual = duration(media_probe)
        if actual <= 0.1:
            raise RuntimeError(f"{take_id}: invalid source duration {actual}")
        slide_id = str(slot["canonical_slide"])
        group = grouped.setdefault(
            slide_id,
            {
                "id": slide_id,
                "caption": str(slot["caption"]),
                "runtime_title": "",
                "target_duration": 0.0,
                "items": [],
            },
        )
        group["target_duration"] += float(slot["editorial_duration_seconds"])
        group["items"].append(
            {
                "id": take_id,
                "status": status,
                "eligibility": eligibility,
                "source": source,
                "target_duration": float(slot["editorial_duration_seconds"]),
                "actual_duration": actual,
                "probe": media_probe,
            }
        )

    target_total = float(timing["duration_seconds"])
    groups = distribute_durations(list(grouped.values()), target_total)
    return quantize_plan_frames({
        "project_id": project_id,
        "project_root": project_root,
        "music": music_path,
        "output": output_path,
        "target_duration": target_total,
        "groups": groups,
        "exceptions": exceptions,
    })


def ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{cs:02d}"


def srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{ms:03d}"


def subtitle_events(plan: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cursor = 0.0
    for group in plan["groups"]:
        start = cursor
        cursor += float(group["use_duration"])
        caption = str(group.get("caption") or "")
        title = str(group.get("runtime_title") or "")
        if caption:
            events.append(
                {
                    "style": "Narracao",
                    "text": caption,
                    "start": start + min(0.35, max(0.0, (cursor - start) / 8)),
                    "end": cursor - min(0.25, max(0.0, (cursor - start) / 10)),
                }
            )
        if title and not plan.get("logo"):
            events.append(
                {
                    "style": "Titulo",
                    "text": title,
                    "start": start + 0.2,
                    "end": cursor - 0.15,
                }
            )
    return events


def write_subtitles(plan: dict[str, Any]) -> tuple[Path, Path]:
    output = Path(plan["output"])
    ass_path = output.with_suffix(".ass")
    srt_path = output.with_suffix(".srt")
    events = subtitle_events(plan)
    ass_lines = [
        "[Script Info]",
        f"Title: {plan['project_id']} PT-BR Reel",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
        (
            "Style: Narracao,Arial,46,&H00FFFFFF,&H000000FF,&H00101010,"
            "&H98000000,-1,0,0,0,100,100,0,0,3,4,1,2,140,140,80,1"
        ),
        (
            "Style: Titulo,Arial,64,&H00FFFFFF,&H000000FF,&H00101010,"
            "&H70000000,-1,0,0,0,100,100,2,0,3,5,2,5,120,120,0,1"
        ),
        "",
        "[Events]",
        (
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text"
        ),
    ]
    for event in events:
        text = str(event["text"]).replace("\n", r"\N")
        ass_lines.append(
            "Dialogue: 0,"
            f"{ass_time(float(event['start']))},"
            f"{ass_time(float(event['end']))},"
            f"{event['style']},,0,0,0,,"
            r"{\fad(220,220)}"
            + text
        )
    ass_path.write_text("\n".join(ass_lines) + "\n", encoding="utf-8")

    srt_lines: list[str] = []
    for index, event in enumerate(events, start=1):
        srt_lines.extend(
            [
                str(index),
                (
                    f"{srt_time(float(event['start']))} --> "
                    f"{srt_time(float(event['end']))}"
                ),
                str(event["text"]),
                "",
            ]
        )
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return ass_path, srt_path


def escape_filter_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value


def loudnorm_measurement(ffmpeg: str, music: Path) -> dict[str, Any]:
    result = run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(music),
            "-af",
            (
                f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:"
                f"LRA={TARGET_LRA}:print_format=json"
            ),
            "-vn",
            "-f",
            "null",
            os.devnull,
        ],
        f"measuring {music.name}",
        capture=True,
    )
    matches = re.findall(r"\{[\s\S]*?\}", result.stderr or "")
    for candidate in reversed(matches):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if "input_i" in value:
            return value
    raise RuntimeError(f"loudnorm did not return metrics for {music}")


def second_pass_loudnorm(metrics: dict[str, Any]) -> str:
    return (
        f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
        f"measured_I={metrics['input_i']}:"
        f"measured_TP={metrics['input_tp']}:"
        f"measured_LRA={metrics['input_lra']}:"
        f"measured_thresh={metrics['input_thresh']}:"
        f"offset={metrics['target_offset']}:linear=true:print_format=summary"
    )


def filter_script(plan: dict[str, Any], ass_path: Path, metrics: dict[str, Any]) -> str:
    items = [item for group in plan["groups"] for item in group["items"]]
    chains: list[str] = []
    labels: list[str] = []
    for index, item in enumerate(items):
        use_frames = int(item["use_frames"])
        chains.append(
            f"[{index}:v]fps={FPS},trim=end_frame={use_frames},"
            "setpts=PTS-STARTPTS,"
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease:"
            "flags=lanczos,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
            "setsar=1,"
            "format=yuv420p,"
            "setparams=range=limited:color_primaries=bt709:"
            "color_trc=bt709:colorspace=bt709"
            f"[v{index}]"
        )
        labels.append(f"[v{index}]")

    chains.append(
        "".join(labels)
        + f"concat=n={len(items)}:v=1:a=0[concatv]"
    )
    video_label = "concatv"
    audio_index = len(items)
    logo = plan.get("logo")
    if logo:
        logo_index = len(items)
        audio_index += 1
        logo_start = float(logo["start"])
        logo_end = float(logo["end"])
        chains.append(
            f"[{logo_index}:v]fps={FPS},crop={logo['crop']},"
            f"scale={int(logo['width'])}:-2:flags=lanczos,"
            "format=rgba,"
            "lumakey=threshold=0.13:tolerance=0.10:softness=0.08,"
            f"trim=duration={float(plan['target_duration']):.6f},"
            "setpts=PTS-STARTPTS,"
            f"fade=t=in:st={logo_start:.6f}:d=0.45:alpha=1[logov]"
        )
        chains.append(
            "[concatv][logov]"
            f"overlay=(W-w)/2:(H-h)/2:format=auto:"
            f"enable='between(t,{logo_start:.6f},{logo_end:.6f})'[brandv]"
        )
        video_label = "brandv"
    chains.append(
        f"[{video_label}]subtitles='{escape_filter_path(ass_path)}'[vout]"
    )
    chains.append(
        f"[{audio_index}:a]"
        f"atrim=duration={float(plan['target_duration']):.6f},"
        "asetpts=PTS-STARTPTS,"
        f"{second_pass_loudnorm(metrics)}[aout]"
    )
    return ";\n".join(chains) + "\n"


def make_contact_sheet(
    ffmpeg: str,
    output: Path,
    target_duration: float,
) -> Path:
    contact = output.with_name(output.stem + "_contact.jpg")
    interval = max(3.0, target_duration / 20.0)
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(output),
            "-vf",
            (
                f"fps=1/{interval:.6f},"
                "scale=384:216:flags=lanczos,tile=5x4"
            ),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(contact),
        ],
        f"contact sheet {output.name}",
    )
    return contact


def final_loudness(ffmpeg: str, output: Path) -> dict[str, Any]:
    result = run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(output),
            "-af",
            (
                f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:"
                f"LRA={TARGET_LRA}:print_format=json"
            ),
            "-vn",
            "-f",
            "null",
            os.devnull,
        ],
        f"final loudness {output.name}",
        capture=True,
    )
    matches = re.findall(r"\{[\s\S]*?\}", result.stderr or "")
    for candidate in reversed(matches):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if "input_i" in value:
            return value
    raise RuntimeError(f"Could not measure final loudness: {output}")


def validate_final(
    ffmpeg: str,
    ffprobe: str,
    output: Path,
    target_frames: int,
) -> dict[str, Any]:
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(output),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            os.devnull,
        ],
        f"full decode {output.name}",
    )
    media_probe = probe(output, ffprobe, count_frames=True)
    videos = [
        stream
        for stream in media_probe["streams"]
        if stream.get("codec_type") == "video"
    ]
    audios = [
        stream
        for stream in media_probe["streams"]
        if stream.get("codec_type") == "audio"
    ]
    if len(videos) != 1 or len(audios) != 1:
        raise RuntimeError(f"{output}: expected one video and one audio stream")
    video = videos[0]
    frames = int(video.get("nb_read_frames") or video.get("nb_frames") or 0)
    if int(video.get("width") or 0) != WIDTH or int(video.get("height") or 0) != HEIGHT:
        raise RuntimeError(f"{output}: wrong dimensions")
    if frames != target_frames:
        raise RuntimeError(f"{output}: {frames} frames, expected {target_frames}")
    return media_probe


def output_fingerprint(plan: dict[str, Any], ass_path: Path) -> str:
    sources = [
        {
            "path": str(item["source"]),
            "size": Path(item["source"]).stat().st_size,
            "mtime_ns": Path(item["source"]).stat().st_mtime_ns,
            "use_duration": round(float(item["use_duration"]), 6),
        }
        for group in plan["groups"]
        for item in group["items"]
    ]
    payload = {
        "script_version": SCRIPT_VERSION,
        "project_id": plan["project_id"],
        "sources": sources,
        "music": {
            "path": str(plan["music"]),
            "size": Path(plan["music"]).stat().st_size,
            "mtime_ns": Path(plan["music"]).stat().st_mtime_ns,
        },
        "captions_sha256": sha256(ass_path),
        "target_duration": plan["target_duration"],
        "logo": (
            {
                "path": str(Path(plan["logo"]["source"]).resolve()),
                "size": Path(plan["logo"]["source"]).stat().st_size,
                "mtime_ns": Path(plan["logo"]["source"]).stat().st_mtime_ns,
                "crop": plan["logo"]["crop"],
                "width": plan["logo"]["width"],
                "start": plan["logo"]["start"],
                "end": plan["logo"]["end"],
                "composition": plan["logo"]["composition"],
            }
            if plan.get("logo")
            else None
        ),
        "format": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "video": f"libx264 crf {VIDEO_CRF} preset {VIDEO_PRESET}",
            "audio": f"AAC {AUDIO_BITRATE} {TARGET_LUFS} LUFS",
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()


def render_plan(
    plan: dict[str, Any],
    ffmpeg: str,
    ffprobe: str,
    *,
    execute: bool,
    force: bool,
    publish_drive: bool,
) -> dict[str, Any]:
    output = Path(plan["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    if not Path(plan["music"]).is_file():
        raise RuntimeError(f"Music is missing: {plan['music']}")
    ass_path, srt_path = write_subtitles(plan)
    fingerprint = output_fingerprint(plan, ass_path)
    sidecar = output.with_suffix(".json")
    target_frames = int(plan["target_frames"])
    target_duration = target_frames / FPS

    existing_reusable = False
    if output.is_file() and sidecar.is_file() and not force:
        try:
            current = load_json(sidecar)
            existing_reusable = (
                current.get("processing_fingerprint") == fingerprint
                and current.get("validation_status")
                in {"technical_pass_visual_qc_pending", "technical_and_visual_pass"}
                and current.get("output", {}).get("sha256") == sha256(output)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            existing_reusable = False

    summary = {
        "project_id": plan["project_id"],
        "output": str(output),
        "take_count": sum(len(group["items"]) for group in plan["groups"]),
        "target_frames": target_frames,
        "target_duration_seconds": target_duration,
        "exceptions": plan["exceptions"],
        "action": "skip" if existing_reusable else "render",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if not execute:
        return summary
    if existing_reusable:
        if publish_drive:
            publish_final_bundle(output, ass_path, srt_path, sidecar)
        return summary

    music_metrics = loudnorm_measurement(ffmpeg, Path(plan["music"]))
    script_path = output.with_name(output.stem + "_filter.ffscript")
    script_path.write_text(
        filter_script(plan, ass_path, music_metrics),
        encoding="utf-8",
    )
    items = [item for group in plan["groups"] for item in group["items"]]
    command = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y"]
    for item in items:
        command.extend(["-i", str(item["source"])])
    if plan.get("logo"):
        command.extend(
            [
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-i",
                str(plan["logo"]["source"]),
            ]
        )
    command.extend(
        [
            "-i",
            str(plan["music"]),
            "-/filter_complex",
            str(script_path),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-frames:v",
            str(target_frames),
            "-r",
            str(FPS),
            "-fps_mode",
            "cfr",
            "-c:v",
            "libx264",
            "-preset",
            VIDEO_PRESET,
            "-crf",
            VIDEO_CRF,
            "-pix_fmt",
            "yuv420p",
            "-color_range",
            "tv",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    run(command, f"rendering {output.name}")
    media_probe = validate_final(ffmpeg, ffprobe, output, target_frames)
    contact = make_contact_sheet(ffmpeg, output, target_duration)
    loudness = final_loudness(ffmpeg, output)
    payload = {
        "schema_version": "1.0",
        "tool_version": SCRIPT_VERSION,
        "validation_status": "technical_pass_visual_qc_pending",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project_id": plan["project_id"],
        "processing_fingerprint": fingerprint,
        "state_policy": {
            "approval_mutated": False,
            "queue_mutated": False,
            "runtime_asset_promoted": False,
        },
        "format": {
            "destination": "horizontal_master",
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "reframe": (
                "full source frame preserved in a 16:9 canvas; no crop, stretch, "
                "or vertical reframe"
            ),
            "captions": "PT-BR burned into video; ASS and SRT sidecars retained",
        },
        "timeline": {
            "duration_seconds": target_duration,
            "frame_count": target_frames,
            "source_policy": "native footage only; no stretch, freeze, or generated hold",
            "groups": [
                {
                    "id": group["id"],
                    "caption": group["caption"],
                    "runtime_title": group["runtime_title"],
                    "use_duration": group["use_duration"],
                    "items": [
                        {
                            "id": item["id"],
                            "maestro_status": item["status"],
                            "eligibility": item["eligibility"],
                            "source": str(item["source"]),
                            "actual_duration": item["actual_duration"],
                            "use_duration": item["use_duration"],
                        }
                        for item in group["items"]
                    ],
                }
                for group in plan["groups"]
            ],
        },
        "exceptions": plan["exceptions"],
        "music": {
            "source": str(Path(plan["music"]).resolve()),
            "source_measurement": music_metrics,
            "target_lufs": TARGET_LUFS,
            "target_true_peak_dbtp": TARGET_TP,
            "final_measurement": loudness,
        },
        "captions": {
            "ass": str(ass_path.resolve()),
            "srt": str(srt_path.resolve()),
        },
        "branding": (
            {
                "source": str(Path(plan["logo"]["source"]).resolve()),
                "crop": plan["logo"]["crop"],
                "composition": plan["logo"]["composition"],
                "start_seconds": plan["logo"]["start"],
                "end_seconds": plan["logo"]["end"],
                "generic_runtime_title_removed": True,
            }
            if plan.get("logo")
            else None
        ),
        "output": {
            "file": str(output.resolve()),
            "size_bytes": output.stat().st_size,
            "sha256": sha256(output),
            "probe": media_probe,
        },
        "qc": {
            "contact_sheet": str(contact.resolve()),
            "full_decode": "pass",
            "visual_review": "pending",
        },
    }
    temporary = sidecar.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, sidecar)
    script_path.unlink(missing_ok=True)
    if publish_drive:
        publish_final_bundle(output, ass_path, srt_path, sidecar)
    return summary


def main() -> int:
    args = parse_args()
    ffmpeg = require_tool("ffmpeg")
    ffprobe = require_tool("ffprobe")
    plans: list[dict[str, Any]] = []
    if args.project in {"intro", "all"}:
        plans.append(build_intro_plan(ffprobe))
    if args.project in {"transition", "all"}:
        plans.append(build_transition_plan(ffprobe))
    if args.project in {"transition2", "all"}:
        plans.append(
            build_transition_plan(
                ffprobe,
                project_id="transicao_f2_f3_raizes_ferro_wan",
                project_root=TRANSITION2_ROOT,
                queue_path=TRANSITION2_QUEUE,
                timing_path=TRANSITION2_TIMING,
                music_path=TRANSITION2_MUSIC,
                output_path=TRANSITION2_OUTPUT,
                allow_unapproved_technical=False,
            )
        )
    for plan in plans:
        render_plan(
            plan,
            ffmpeg,
            ffprobe,
            execute=args.execute,
            force=args.force,
            publish_drive=not args.skip_drive,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("[social-reels] interrupted", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001
        print(f"[social-reels] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
