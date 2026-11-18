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
QC_DIR = PROJECT / "qc" / "assembled_candidates" / "internal_boundaries"
MAIN_IDS = ("01", "02", "03", "04", "05", "06")
SHEET_BASENAME = "assembly_internal_boundaries_contact_sheet.jpg"
REPORT_BASENAME = "assembly_internal_boundaries_report.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def probe_frames(path: Path) -> int:
    raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames,nb_frames", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    stream = json.loads(raw)["streams"][0]
    return int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)


def probe_fps(path: Path) -> float:
    raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate", "-of", "default=nw=1:nk=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    numerator, denominator = raw.split("/", 1)
    return float(numerator) / float(denominator)


def active_video(take: dict) -> Path:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    for key in ("output_active", "output_preview", "output_review_candidate"):
        path = Path(str(video.get(key) or ""))
        if path.is_file():
            return path
    raise FileNotFoundError(f"Take {take.get('id')} sem video ativo.")


def extract_strip(video: Path, boundary: float, output: Path, fps: float) -> None:
    start = max(0.0, boundary - (4.0 / fps))
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.6f}", "-i", str(video), "-t", f"{8.0 / fps:.6f}",
            "-vf", f"fps={fps:.8f},scale=320:180,tile=8x1:nb_frames=8:padding=0:margin=0",
            "-frames:v", "1", str(output),
        ],
        check=True,
    )


def main() -> int:
    queue = read(QUEUE)
    by_id = {str(item.get("id")): item for item in queue.get("takes", [])}
    QC_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[Image.Image] = []
    report: list[dict] = []
    for take_id in MAIN_IDS:
        take = by_id[take_id]
        assembly = (take.get("qc") or {}).get("microassembly") or {}
        trims = list(assembly.get("trims") or [])
        sources = [Path(path) for path in assembly.get("sources") or []]
        if len(sources) <= 1:
            continue
        if len(trims) != len(sources):
            raise RuntimeError(f"Metadados de montagem inconsistentes no Take {take_id}.")
        useful_frames = [
            probe_frames(source) - int(trim.get("head_frames") or 0) - int(trim.get("tail_frames") or 0)
            for source, trim in zip(sources, trims)
        ]
        total = sum(useful_frames)
        registered_video = take.get("video") if isinstance(take.get("video"), dict) else {}
        active_duration = float(
            registered_video.get("duration_seconds")
            or assembly.get("target_duration_seconds")
            or take.get("target_duration_seconds")
        )
        cumulative = 0
        video = active_video(take)
        active_fps = probe_fps(video)
        for join_index, frames in enumerate(useful_frames[:-1], start=1):
            cumulative += frames
            boundary = active_duration * cumulative / total
            strip_path = QC_DIR / f"take_{take_id}_join_{join_index}_{boundary:.3f}s.jpg"
            extract_strip(video, boundary, strip_path, active_fps)
            with Image.open(strip_path) as opened:
                strip = opened.convert("RGB").copy()
            card = Image.new("RGB", (strip.width, strip.height + 42), "#111111")
            card.paste(strip, (0, 42))
            ImageDraw.Draw(card).text(
                (16, 12),
                f"TAKE {take_id} — JOIN {join_index} — t={boundary:.3f}s — {active_fps:g}fps, four before / four after",
                fill="white",
            )
            rows.append(card)
            report.append({
                "take_id": take_id,
                "join_index": join_index,
                "boundary_seconds": round(boundary, 6),
                "active_fps": active_fps,
                "source_before": str(sources[join_index - 1]),
                "source_after": str(sources[join_index]),
                "strip": str(strip_path),
            })
    if not rows:
        raise RuntimeError("Nenhuma juncao interna encontrada.")
    width = max(row.width for row in rows)
    height = sum(row.height for row in rows)
    sheet = Image.new("RGB", (width, height), "#050505")
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height
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
                "joins": report,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "joins": len(report), "sheet": str(sheet_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
