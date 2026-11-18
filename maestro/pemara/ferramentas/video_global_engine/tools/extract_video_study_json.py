from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from analyze_intro_fidelity import (
    contact_sheet,
    extract_frames,
    ffprobe,
    ffprobe_frames,
    metrics_for_frames,
    motion_profile,
    write_json,
)


PROJECT = Path(__file__).resolve().parents[1] / "projetos" / "intro_ritmos_revolta"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT).as_posix()
    except ValueError:
        return path.as_posix()


def read_sidecar(video: Path) -> dict[str, Any] | None:
    sidecar = video.with_suffix(".json")
    if not sidecar.exists():
        return None
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc), "_path": sidecar.as_posix()}


def summarize_motion(motion: list[dict[str, Any]]) -> dict[str, Any]:
    if not motion:
        return {
            "sample_count": 0,
            "avg_mean_abs_diff": 0,
            "max_mean_abs_diff": 0,
            "avg_changed_ratio_gt_18": 0,
            "motion_class": "unknown",
        }
    mean_values = [float(row["mean_abs_diff"]) for row in motion]
    changed_values = [float(row["changed_ratio_gt_18"]) for row in motion]
    avg_motion = sum(mean_values) / len(mean_values)
    avg_changed = sum(changed_values) / len(changed_values)
    if avg_motion < 2.5:
        motion_class = "muito_estatico"
    elif avg_motion < 5.0:
        motion_class = "movimento_baixo"
    elif avg_motion < 9.0:
        motion_class = "movimento_medio"
    else:
        motion_class = "movimento_forte"
    return {
        "sample_count": len(motion),
        "avg_mean_abs_diff": round(avg_motion, 4),
        "max_mean_abs_diff": round(max(mean_values), 4),
        "avg_changed_ratio_gt_18": round(avg_changed, 5),
        "motion_class": motion_class,
    }


def likely_flags(video: Path, probe: dict[str, Any], metrics: list[dict[str, Any]], motion: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    duration = float(probe.get("format", {}).get("duration") or 0)
    if duration and duration < 3.9 and "take_09" not in video.name:
        flags.append("duracao_menor_que_esperado")
    if duration and "take_09" in video.name and duration < 3.0:
        flags.append("take_titulo_curto")
    motion_summary = summarize_motion(motion)
    if motion_summary["motion_class"] in {"muito_estatico", "movimento_baixo"}:
        flags.append("movimento_fraco")
    if metrics:
        bright = sum(float(row["bright_ratio_luma_gt_220"]) for row in metrics) / len(metrics)
        dark = sum(float(row["dark_ratio_luma_lt_24"]) for row in metrics) / len(metrics)
        sat = sum(float(row["saturation_mean"]) for row in metrics) / len(metrics)
        if bright > 0.14:
            flags.append("brilho_estourado")
        if dark > 0.34:
            flags.append("escuro_dominante")
        if sat > 0.36:
            flags.append("saturacao_alta_revisar_artefatos")
    if "titulo" in video.name:
        flags.append("texto_precisa_qc_manual")
    return flags


def analyze_video(video: Path, out_dir: Path, sample_fps: float) -> dict[str, Any]:
    item_dir = out_dir / video.stem
    frames_dir = item_dir / f"frames_{str(sample_fps).replace('.', '_')}fps"
    item_dir.mkdir(parents=True, exist_ok=True)

    probe = ffprobe(video)
    probe_full = ffprobe(video, full=True)
    timeline = ffprobe_frames(video)

    extract_frames(video, frames_dir, sample_fps)
    sheet = item_dir / "contact_sheet.jpg"
    contact_sheet(video, sheet, sample_fps, "4x3")

    metrics = metrics_for_frames(frames_dir, sample_fps)
    motion = motion_profile(metrics, frames_dir, sample_fps)
    sidecar = read_sidecar(video)

    write_json(item_dir / "01_ffprobe.json", probe)
    write_json(item_dir / "02_ffprobe_full.json", probe_full)
    write_json(item_dir / "03_frame_timeline.json", timeline)
    write_json(item_dir / "04_sampled_frame_metrics.json", metrics)
    write_json(item_dir / "05_motion_profile.json", motion)
    if sidecar is not None:
        write_json(item_dir / "06_source_sidecar.json", sidecar)

    source_copy = item_dir / video.name
    if not source_copy.exists():
        shutil.copy2(video, source_copy)

    summary = {
        "video": video.as_posix(),
        "video_relative": rel(video),
        "study_dir": item_dir.as_posix(),
        "contact_sheet": sheet.as_posix(),
        "source_copy": source_copy.as_posix(),
        "source_sidecar_found": sidecar is not None,
        "ffprobe": probe,
        "motion_summary": summarize_motion(motion),
        "qc_flags_auto": likely_flags(video, probe, metrics, motion),
    }
    write_json(item_dir / "00_summary.json", summary)
    return summary


def default_latest_videos() -> list[Path]:
    patterns = [
        "takes/*veo_kling_smoke_4s*.mp4",
        "output/*veo_kling_smoke_4s*.mp4",
    ]
    videos: list[Path] = []
    for pattern in patterns:
        videos.extend(PROJECT.glob(pattern))
    return sorted(set(videos), key=lambda path: path.as_posix())


def build_project_video_catalog(out_dir: Path) -> None:
    rows = []
    for video in sorted(PROJECT.rglob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True):
        rows.append(
            {
                "path": video.as_posix(),
                "relative": rel(video),
                "size_bytes": video.stat().st_size,
                "last_write_time": datetime.fromtimestamp(video.stat().st_mtime).isoformat(timespec="seconds"),
                "has_sidecar_json": video.with_suffix(".json").exists(),
            }
        )
    write_json(out_dir / "project_video_catalog_filesystem.json", rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract study JSON, frames and QC sheets for Pemara video takes.")
    parser.add_argument("--out", default=str(PROJECT / "qc" / f"video_study_{datetime.now():%Y%m%d_%H%M%S}"))
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--catalog-project", action="store_true")
    parser.add_argument("videos", nargs="*")
    args = parser.parse_args()

    out_dir = Path(args.out)
    videos = [Path(v) for v in args.videos] if args.videos else default_latest_videos()
    videos = [video for video in videos if video.exists()]
    if not videos:
        raise SystemExit("Nenhum video encontrado para analisar.")

    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = [analyze_video(video, out_dir, args.sample_fps) for video in videos]
    write_json(
        out_dir / "00_STUDY_MANIFEST.json",
        {
            "schema_version": "1.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project": PROJECT.as_posix(),
            "sample_fps": args.sample_fps,
            "video_count": len(videos),
            "videos": summaries,
            "training_note": "Use only approved videos as positive examples; rejected videos must be labeled as negative/diagnostic.",
        },
    )
    if args.catalog_project:
        build_project_video_catalog(out_dir)
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
