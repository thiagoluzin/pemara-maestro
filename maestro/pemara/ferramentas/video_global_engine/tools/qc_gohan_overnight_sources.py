from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
QUEUE = PROJECT / "take_queue.json"
QC_DIR = PROJECT / "qc" / "overnight_sources"
TAKE_IDS = (
    "01A", "01B", "02A", "03A", "03B", "03C", "03D", "03E",
    "04A2", "04B", "05A", "05B", "05C", "05D", "06A", "06B",
)
SHEET_LABEL = "SOURCE QC"
COMBINED_BASENAME = "all_overnight_sources_contact_sheet.jpg"
REPORT_BASENAME = "overnight_sources_report.json"
EXPECTED_FPS = 24.0
FREEZE_RE = re.compile(r"freeze_(start|duration|end):\s*([0-9.]+)")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def probe(path: Path) -> dict:
    payload = json.loads(
        run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries",
                "stream=codec_name,width,height,avg_frame_rate,r_frame_rate,nb_frames,pix_fmt:format=duration,size",
                "-of", "json", str(path),
            ]
        ).stdout
    )
    stream = payload["streams"][0]
    fmt = payload["format"]

    def ratio(raw: str) -> float:
        top, bottom = raw.split("/", 1)
        return float(top) / float(bottom)

    return {
        "codec": stream.get("codec_name", ""),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": ratio(stream.get("avg_frame_rate") or stream["r_frame_rate"]),
        "frames": int(stream.get("nb_frames") or 0),
        "pix_fmt": stream.get("pix_fmt", ""),
        "duration_seconds": float(fmt["duration"]),
        "size_bytes": int(fmt["size"]),
    }


def output_path(take: dict) -> Path:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    for field in (
        "output_active", "output_preview", "output_review_candidate",
        "output_native", "file",
    ):
        raw = str(video.get(field) or "").strip()
        if raw:
            candidate = Path(raw).resolve()
            if candidate.is_relative_to(PROJECT.resolve()) and candidate.is_file():
                return candidate
    raise FileNotFoundError(f"video local nao registrado para {take.get('id')}")


def extract_frame(video: Path, output: Path, *, at_end: bool = False) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if at_end:
        command += ["-sseof", "-0.05"]
    command += ["-i", str(video), "-frames:v", "1", str(output)]
    run(command)


def anchor_mae(frame: Path, anchor: Path) -> float:
    with Image.open(frame) as frame_image, Image.open(anchor) as anchor_image:
        left = ImageOps.exif_transpose(frame_image).convert("RGB")
        right = ImageOps.fit(
            ImageOps.exif_transpose(anchor_image).convert("RGB"),
            left.size,
            method=Image.Resampling.LANCZOS,
        )
        stats = ImageStat.Stat(ImageChops.difference(left, right))
        return sum(stats.mean) / (3.0 * 255.0)


def freeze_events(video: Path, duration: float) -> list[dict[str, float]]:
    completed = run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
            "-vf", "freezedetect=n=-50dB:d=0.12", "-an", "-f", "null", "NUL",
        ],
        check=False,
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


def make_contact(video: Path, output: Path, duration: float) -> None:
    sample_fps = 12.0 / max(duration, 0.1)
    vf = (
        f"fps={sample_fps:.8f},"
        "scale=320:180:force_original_aspect_ratio=decrease,"
        "pad=320:180:(ow-iw)/2:(oh-ih)/2:black,tile=4x3"
    )
    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
            "-vf", vf, "-frames:v", "1", "-q:v", "2", str(output),
        ]
    )


def combined_sheet(items: list[tuple[str, Path]], output: Path) -> None:
    cards: list[Image.Image] = []
    for take_id, path in items:
        with Image.open(path) as opened:
            contact = opened.convert("RGB").copy()
        card = Image.new("RGB", (contact.width, contact.height + 42), "#111111")
        card.paste(contact, (0, 42))
        ImageDraw.Draw(card).text((18, 11), f"TAKE {take_id} — {SHEET_LABEL}", fill="white")
        cards.append(card)
    columns = 2
    rows = (len(cards) + columns - 1) // columns
    width = max(card.width for card in cards) * columns
    height = max(card.height for card in cards) * rows
    canvas = Image.new("RGB", (width, height), "#050505")
    for index, card in enumerate(cards):
        x = (index % 2) * card.width
        y = (index // 2) * card.height
        canvas.paste(card, (x, y))
    canvas.save(output, quality=92, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    QC_DIR.mkdir(parents=True, exist_ok=True)
    queue = read_json(QUEUE)
    by_id = {
        str(take.get("id")): take
        for take in queue.get("takes", [])
        if isinstance(take, dict)
    }
    reports: list[dict] = []
    contacts: list[tuple[str, Path]] = []
    missing: list[str] = []
    for take_id in TAKE_IDS:
        take = by_id.get(take_id)
        if take is None:
            missing.append(take_id)
            continue
        try:
            video = output_path(take)
        except FileNotFoundError:
            missing.append(take_id)
            continue
        info = probe(video)
        start_frame = QC_DIR / f"take_{take_id}_first.png"
        end_frame = QC_DIR / f"take_{take_id}_last.png"
        contact = QC_DIR / f"take_{take_id}_contact_12frames.jpg"
        extract_frame(video, start_frame)
        extract_frame(video, end_frame, at_end=True)
        make_contact(video, contact, info["duration_seconds"])
        contacts.append((take_id, contact))

        start_anchor = Path(take["base_image"]["file"])
        end_anchor = Path(take["end_image"]["file"])
        freezes = freeze_events(video, info["duration_seconds"])
        freeze_violations = [
            event for event in freezes
            if event.get("duration", 0.0) >= 0.12
            and not (event.get("start", 0.0) <= 0.001 and event.get("end", 0.0) <= 0.10)
        ]
        registered_video = take.get("video") if isinstance(take.get("video"), dict) else {}
        expected_duration = float(
            registered_video.get("duration_seconds")
            or take.get("target_duration_seconds")
            or take.get("native_duration_seconds")
            or 0.0
        )
        technical_errors: list[str] = []
        if info["width"] != 1280 or info["height"] != 720:
            technical_errors.append("resolution_not_1280x720")
        if abs(info["fps"] - EXPECTED_FPS) > 0.01:
            technical_errors.append(f"fps_not_{EXPECTED_FPS:g}")
        if abs(info["duration_seconds"] - expected_duration) > 0.20:
            technical_errors.append("duration_out_of_tolerance")
        if freeze_violations:
            technical_errors.append("visible_hold_detected")
        reports.append(
            {
                "take_id": take_id,
                "parent_take_id": take.get("parent_take_id") or take_id,
                "video": str(video),
                "sha256": sha256(video),
                "technical": info,
                "endpoint_checks": {
                    "start_anchor": str(start_anchor),
                    "end_anchor": str(end_anchor),
                    "first_frame_normalized_mae": round(anchor_mae(start_frame, start_anchor), 6),
                    "last_frame_normalized_mae": round(anchor_mae(end_frame, end_anchor), 6),
                },
                "freeze_events": freezes,
                "freeze_violations": freeze_violations,
                "technical_errors": technical_errors,
                "technical_status": "PASS" if not technical_errors else "FAIL",
                "art_direction_status": "PENDING_MANUAL_VISUAL_QC",
                "cinematic_status": "PENDING_MANUAL_VISUAL_QC",
                "motion_status": "PENDING_MANUAL_VISUAL_QC",
                "human_status": "PENDING_OWNER_REVIEW",
                "contact_sheet": str(contact),
            }
        )

    combined = QC_DIR / COMBINED_BASENAME
    if contacts:
        combined_sheet(contacts, combined)
    payload = {
        "project_id": queue.get("project_id"),
        "status": (
            "INCOMPLETE" if missing else
            "TECHNICAL_FAIL" if any(item["technical_status"] == "FAIL" for item in reports)
            else "TECHNICAL_PASS_VISUAL_QC_PENDING"
        ),
        "auto_approval": False,
        "missing": missing,
        "combined_contact_sheet": str(combined) if contacts else "",
        "takes": reports,
    }
    report_path = QC_DIR / REPORT_BASENAME
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if missing and not args.allow_incomplete:
        return 2
    return 1 if payload["status"] == "TECHNICAL_FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
