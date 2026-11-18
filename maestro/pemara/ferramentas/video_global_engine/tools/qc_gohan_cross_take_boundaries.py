from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
QUEUE = PROJECT / "take_queue.json"
QC_DIR = PROJECT / "qc" / "assembled_candidates" / "cross_take_boundaries"
MAIN_IDS = ("01", "02", "03", "04", "05", "06")
SHEET_BASENAME = "assembly_cross_take_boundaries_contact_sheet.jpg"
REPORT_BASENAME = "assembly_cross_take_boundaries_report.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def active_video(take: dict) -> Path:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    for key in ("output_active", "output_preview", "output_review_candidate"):
        path = Path(str(video.get(key) or ""))
        if path.is_file():
            return path
    raise FileNotFoundError(f"Take {take.get('id')} sem video ativo.")


def probe_fps(video: Path) -> float:
    raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate", "-of", "default=nw=1:nk=1",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    numerator, denominator = raw.split("/", 1)
    return float(numerator) / float(denominator)


def extract_edge(video: Path, output: Path, *, tail: bool, fps: float) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if tail:
        command += ["-sseof", f"{-4.0 / fps:.6f}"]
    command += ["-i", str(video)]
    if not tail:
        command += ["-t", f"{4.0 / fps:.6f}"]
    command += [
        "-vf", f"fps={fps:.8f},scale=320:180,tile=4x1:nb_frames=4:padding=0:margin=0",
        "-frames:v", "1", str(output),
    ]
    subprocess.run(command, check=True)


def main() -> int:
    queue = read(QUEUE)
    by_id = {str(item.get("id")): item for item in queue.get("takes", [])}
    QC_DIR.mkdir(parents=True, exist_ok=True)
    cards: list[Image.Image] = []
    joins: list[dict] = []
    for left_id, right_id in zip(MAIN_IDS, MAIN_IDS[1:]):
        left_video = active_video(by_id[left_id])
        right_video = active_video(by_id[right_id])
        left_fps = probe_fps(left_video)
        right_fps = probe_fps(right_video)
        left_strip = QC_DIR / f"take_{left_id}_tail4.jpg"
        right_strip = QC_DIR / f"take_{right_id}_head4.jpg"
        extract_edge(left_video, left_strip, tail=True, fps=left_fps)
        extract_edge(right_video, right_strip, tail=False, fps=right_fps)
        with Image.open(left_strip) as opened:
            left = opened.convert("RGB").copy()
        with Image.open(right_strip) as opened:
            right = opened.convert("RGB").copy()
        row = Image.new("RGB", (left.width + right.width, 180), "black")
        row.paste(left, (0, 0))
        row.paste(right, (left.width, 0))
        card = Image.new("RGB", (row.width, row.height + 42), "#111111")
        card.paste(row, (0, 42))
        ImageDraw.Draw(card).text(
            (16, 12),
            f"TAKE {left_id} -> {right_id} — {left_fps:g}/{right_fps:g}fps, four outgoing / four incoming",
            fill="white",
        )
        cards.append(card)
        joins.append({
            "from_take": left_id,
            "to_take": right_id,
            "from_video": str(left_video),
            "to_video": str(right_video),
            "from_fps": left_fps,
            "to_fps": right_fps,
            "tail_strip": str(left_strip),
            "head_strip": str(right_strip),
        })
    sheet = Image.new("RGB", (max(card.width for card in cards), sum(card.height for card in cards)), "#050505")
    y = 0
    for card in cards:
        sheet.paste(card, (0, y))
        y += card.height
    sheet_path = QC_DIR.parent / SHEET_BASENAME
    sheet.save(sheet_path, quality=93, optimize=True)
    report_path = QC_DIR.parent / REPORT_BASENAME
    report_path.write_text(
        json.dumps(
            {
                "project_id": PROJECT.name,
                "status": "PENDING_MANUAL_BOUNDARY_REVIEW",
                "crossfade_frames": 0,
                "sheet": str(sheet_path),
                "joins": joins,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "joins": len(joins), "sheet": str(sheet_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
