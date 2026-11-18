from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


PROJECT = Path(__file__).resolve().parents[1] / "projetos" / "intro_ritmos_revolta"
GOLDEN = PROJECT / "output" / "ritmos_intro_60s_final_fhd.mp4"
PREVIEW = PROJECT / "output" / "intro_preview_20260709_071533.mp4"
GOLDEN_CAPTURE = PROJECT / "qc" / "golden_veo31_ritmos_intro_60s_final_fhd" / "golden_capture.json"


def run_json(cmd: list[str]) -> Any:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ffprobe(video: Path, full: bool = False) -> Any:
    if full:
        return run_json(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)])
    return run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=filename,duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,sample_rate,channels",
            "-of",
            "json",
            str(video),
        ]
    )


def ffprobe_frames(video: Path) -> Any:
    return run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=media_type,key_frame,pkt_pts_time,best_effort_timestamp_time,pict_type,pkt_size,width,height",
            "-of",
            "json",
            str(video),
        ]
    )


def extract_frames(video: Path, out_dir: Path, fps: float) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = list(out_dir.glob("frame_*.jpg"))
    if existing:
        return
    fps_arg = str(fps).rstrip("0").rstrip(".")
    run(["ffmpeg", "-y", "-i", str(video), "-vf", f"fps={fps_arg}", str(out_dir / "frame_%04d.jpg")])


def contact_sheet(video: Path, out: Path, fps: float, tile: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fps_arg = str(fps).rstrip("0").rstrip(".")
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps={fps_arg},scale=320:-1,tile={tile}",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out),
        ]
    )


def image_metrics(path: Path, timestamp: float) -> dict[str, Any]:
    image = Image.open(path).convert("RGB")
    arr = np.asarray(image).astype(np.float32)
    rgb = arr.reshape(-1, 3)
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    lum = arr[:, :, 0] * 0.2126 + arr[:, :, 1] * 0.7152 + arr[:, :, 2] * 0.0722
    saturation = np.divide(mx - mn, np.maximum(mx, 1.0))
    edge_h = np.abs(np.diff(lum, axis=1))
    edge_v = np.abs(np.diff(lum, axis=0))
    edge_density = float((edge_h > 18).mean() * 0.5 + (edge_v > 18).mean() * 0.5)
    return {
        "frame_file": path.as_posix(),
        "timestamp_seconds": round(timestamp, 3),
        "width": int(image.width),
        "height": int(image.height),
        "mean_rgb": [round(float(v), 3) for v in rgb.mean(axis=0)],
        "std_rgb": [round(float(v), 3) for v in rgb.std(axis=0)],
        "luminance_mean": round(float(lum.mean()), 3),
        "luminance_std": round(float(lum.std()), 3),
        "saturation_mean": round(float(saturation.mean()), 4),
        "dark_ratio_luma_lt_24": round(float((lum < 24).mean()), 5),
        "bright_ratio_luma_gt_220": round(float((lum > 220).mean()), 5),
        "edge_density": round(edge_density, 5),
        "dominant_rgb_rough": dominant_colors(arr),
        "dark_components": dark_components(lum),
    }


def dominant_colors(arr: np.ndarray, bins: int = 4) -> list[dict[str, Any]]:
    quant = np.clip((arr // (256 / bins)).astype(np.int32), 0, bins - 1)
    codes = quant[:, :, 0] * bins * bins + quant[:, :, 1] * bins + quant[:, :, 2]
    vals, counts = np.unique(codes.reshape(-1), return_counts=True)
    order = np.argsort(counts)[::-1][:5]
    total = float(codes.size)
    colors = []
    for idx in order:
        code = int(vals[idx])
        r = code // (bins * bins)
        g = (code // bins) % bins
        b = code % bins
        center = [int((v + 0.5) * (256 / bins)) for v in (r, g, b)]
        colors.append({"rgb_bin_center": center, "ratio": round(float(counts[idx]) / total, 5)})
    return colors


def dark_components(lum: np.ndarray) -> list[dict[str, Any]]:
    # Downsample enough to keep the component pass cheap and stable.
    h, w = lum.shape
    target_w = 192
    scale = max(1, int(round(w / target_w)))
    small = lum[::scale, ::scale]
    mask = small < 18
    visited = np.zeros(mask.shape, dtype=bool)
    comps: list[dict[str, Any]] = []
    mh, mw = mask.shape
    min_area = max(20, int(mask.size * 0.004))
    for y0 in range(mh):
        for x0 in range(mw):
            if not mask[y0, x0] or visited[y0, x0]:
                continue
            stack = [(x0, y0)]
            visited[y0, x0] = True
            xs: list[int] = []
            ys: list[int] = []
            while stack:
                x, y = stack.pop()
                xs.append(x)
                ys.append(y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < mw and 0 <= ny < mh and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
            area = len(xs)
            if area < min_area:
                continue
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            comps.append(
                {
                    "area_ratio": round(area / float(mask.size), 5),
                    "bbox_norm": [
                        round(x_min / mw, 4),
                        round(y_min / mh, 4),
                        round((x_max + 1) / mw, 4),
                        round((y_max + 1) / mh, 4),
                    ],
                }
            )
    return sorted(comps, key=lambda c: c["area_ratio"], reverse=True)[:8]


def metrics_for_frames(frame_dir: Path, fps: float) -> list[dict[str, Any]]:
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    return [image_metrics(path, idx / fps) for idx, path in enumerate(frames)]


def motion_profile(metrics: list[dict[str, Any]], frame_dir: Path, fps: float) -> list[dict[str, Any]]:
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    rows: list[dict[str, Any]] = []
    previous = None
    for idx, path in enumerate(frames):
        arr = np.asarray(Image.open(path).convert("L").resize((320, 180))).astype(np.float32)
        if previous is not None:
            diff = np.abs(arr - previous)
            rows.append(
                {
                    "from_time": round((idx - 1) / fps, 3),
                    "to_time": round(idx / fps, 3),
                    "mean_abs_diff": round(float(diff.mean()), 4),
                    "p95_abs_diff": round(float(np.percentile(diff, 95)), 4),
                    "changed_ratio_gt_18": round(float((diff > 18).mean()), 5),
                }
            )
        previous = arr
    return rows


def scene_segments_from_motion(motion: list[dict[str, Any]], min_gap: float = 2.0) -> list[dict[str, Any]]:
    if not motion:
        return []
    values = np.array([row["mean_abs_diff"] for row in motion], dtype=np.float32)
    threshold = float(values.mean() + values.std() * 0.75)
    cuts = [0.0]
    last_cut = 0.0
    for row in motion:
        t = float(row["to_time"])
        if row["mean_abs_diff"] >= threshold and t - last_cut >= min_gap:
            cuts.append(t)
            last_cut = t
    end = float(motion[-1]["to_time"])
    if end not in cuts:
        cuts.append(end)
    segments = []
    for i in range(len(cuts) - 1):
        segments.append(
            {
                "index": i + 1,
                "start_seconds": round(cuts[i], 3),
                "end_seconds": round(cuts[i + 1], 3),
                "duration_seconds": round(cuts[i + 1] - cuts[i], 3),
                "method": "motion_threshold_from_sampled_frames",
                "threshold_mean_abs_diff": round(threshold, 4),
            }
        )
    return segments


def take_contracts_from_golden(capture_path: Path, golden_metrics: list[dict[str, Any]], golden_motion: list[dict[str, Any]]) -> list[dict[str, Any]]:
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    rows = capture.get("visual_take_reading", [])
    contracts = []
    for idx, row in enumerate(rows, start=1):
        times = str(row.get("approx_time", ""))
        start, end = parse_time_window(times)
        motion_slice = [m for m in golden_motion if start <= float(m["from_time"]) < end]
        metrics_slice = [m for m in golden_metrics if start <= float(m["timestamp_seconds"]) < end]
        avg_motion = float(np.mean([m["mean_abs_diff"] for m in motion_slice])) if motion_slice else 0.0
        max_motion = float(np.max([m["mean_abs_diff"] for m in motion_slice])) if motion_slice else 0.0
        avg_edges = float(np.mean([m["edge_density"] for m in metrics_slice])) if metrics_slice else 0.0
        contracts.append(
            {
                "take_index": idx,
                "source_time_window": times,
                "start_seconds": start,
                "end_seconds": end,
                "scene": row.get("scene", ""),
                "must_keep_elements": row.get("dominant_elements", []),
                "must_create_motion": row.get("motion_target", []),
                "local_rule": row.get("local_rule", ""),
                "numeric_targets_from_golden": {
                    "avg_sample_motion_mean_abs_diff": round(avg_motion, 4),
                    "max_sample_motion_mean_abs_diff": round(max_motion, 4),
                    "avg_edge_density": round(avg_edges, 5),
                },
                "negative_constraints": [
                    "no static hold",
                    "no living photo only",
                    "no undefined black blob or opaque foreground smear",
                    "no humanoid silhouette",
                    "no fake text before title",
                    "no low resolution pixelated output",
                ],
            }
        )
    return contracts


def parse_time_window(text: str) -> tuple[float, float]:
    try:
        left, right = text.split("-")
        return parse_ts(left), parse_ts(right)
    except Exception:
        return 0.0, 0.0


def parse_ts(text: str) -> float:
    parts = [float(part) for part in text.strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return parts[0]


def preview_hallucination_report(preview_metrics: list[dict[str, Any]], preview_motion: list[dict[str, Any]]) -> dict[str, Any]:
    take02_metrics = [m for m in preview_metrics if m["timestamp_seconds"] < 6.1]
    take04_metrics = [m for m in preview_metrics if m["timestamp_seconds"] >= 6.1]
    take02_motion = [m for m in preview_motion if m["from_time"] < 6.1]
    take04_motion = [m for m in preview_motion if m["from_time"] >= 6.1]
    motion02 = float(np.mean([m["mean_abs_diff"] for m in take02_motion])) if take02_motion else 0.0
    motion04 = float(np.mean([m["mean_abs_diff"] for m in take04_motion])) if take04_motion else 0.0
    return {
        "preview_file": PREVIEW.as_posix(),
        "human_feedback": {
            "take_02": "small hallucination: undefined black spot/smear appeared in the first take.",
            "take_04": "too little movement; hat scene feels like glow/scale breathing rather than an event.",
        },
        "observed_issues": [
            {
                "take_id": "02",
                "approx_time_seconds": [3.0, 4.5],
                "severity": "medium",
                "type": "unplanned_foreground_artifact",
                "description": "Large dark undefined foreground/cable/column shape crosses or occupies the scene without semantic purpose.",
                "likely_cause": "Prompt asked for strong foreground parallax; model invented unreadable black obstruction instead of readable cables/energy/paper.",
                "frames_to_review": [
                    "qc/preview_20260709_071533/frames_05s/frame_0007.jpg",
                    "qc/preview_20260709_071533/frames_05s/frame_0008.jpg",
                    "qc/preview_20260709_071533/frames_05s/frame_0009.jpg",
                    "qc/preview_20260709_071533/frames_05s/frame_0010.jpg",
                ],
                "next_negative_prompt_additions": [
                    "no undefined black blob",
                    "no opaque black foreground smear",
                    "no random dark curtain",
                    "no unreadable black mass blocking the camera",
                ],
                "next_positive_prompt_fix": "Foreground parallax must be readable: paper sheets, golden notes, guitar cables with visible shape, speaker grille, rain, sparks, or energy ribbons.",
            },
            {
                "take_id": "04",
                "approx_time_seconds": [6.0, 12.0],
                "severity": "high",
                "type": "insufficient_motion_event",
                "description": "Hat stays centered with limited camera/event evolution; movement is mostly glow and slight scale.",
                "likely_cause": "Base keyframe is too centered and stable; prompt event is not enforced by temporal milestones.",
                "next_positive_prompt_fix": "Use explicit milestones: second 0 low angle, second 2 ring expands and cracks, second 4 hat levitates/rotates, second 5 particles rush toward lens, final frame shows changed floor state.",
            },
        ],
        "numeric_motion_summary": {
            "take_02_avg_sample_motion_mean_abs_diff": round(motion02, 4),
            "take_04_avg_sample_motion_mean_abs_diff": round(motion04, 4),
            "motion_ratio_take04_over_take02": round(motion04 / motion02, 4) if motion02 else None,
        },
        "dark_component_samples": [
            {
                "timestamp_seconds": m["timestamp_seconds"],
                "dark_ratio_luma_lt_24": m["dark_ratio_luma_lt_24"],
                "largest_dark_components": m["dark_components"][:3],
            }
            for m in take02_metrics
            if 2.5 <= float(m["timestamp_seconds"]) <= 5.0
        ],
    }


def compare_preview_to_golden(golden_motion: list[dict[str, Any]], preview_motion: list[dict[str, Any]]) -> dict[str, Any]:
    golden_mean = float(np.mean([m["mean_abs_diff"] for m in golden_motion])) if golden_motion else 0.0
    preview_mean = float(np.mean([m["mean_abs_diff"] for m in preview_motion])) if preview_motion else 0.0
    golden_p75 = float(np.percentile([m["mean_abs_diff"] for m in golden_motion], 75)) if golden_motion else 0.0
    preview_p75 = float(np.percentile([m["mean_abs_diff"] for m in preview_motion], 75)) if preview_motion else 0.0
    return {
        "summary": "Golden VEO uses stronger scene changes, readable effects and composition changes; local preview still needs motion/event enforcement.",
        "motion_comparison": {
            "golden_sample_fps": 1,
            "preview_sample_fps": 2,
            "golden_mean_abs_diff_avg": round(golden_mean, 4),
            "preview_mean_abs_diff_avg": round(preview_mean, 4),
            "golden_p75_mean_abs_diff": round(golden_p75, 4),
            "preview_p75_mean_abs_diff": round(preview_p75, 4),
        },
        "workflow_decision": {
            "do_not_use_preview_as_training_positive_without_labels": True,
            "use_preview_take02_as": "diagnostic sample: good ambience but mark black foreground as negative",
            "use_preview_take04_as": "negative/needs_regeneration sample for insufficient event motion",
            "use_golden_as": "primary visual/motion contract source",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", default=str(GOLDEN))
    parser.add_argument("--preview", default=str(PREVIEW))
    parser.add_argument("--out", default=str(PROJECT / "qc" / "fidelity_analysis_20260709"))
    args = parser.parse_args()

    golden = Path(args.golden)
    preview = Path(args.preview)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    golden_frames = out / "golden_frames_1s"
    preview_frames = out / "preview_frames_05s"
    extract_frames(golden, golden_frames, 1)
    extract_frames(preview, preview_frames, 2)
    contact_sheet(golden, out / "golden_contact_2s.jpg", 0.5, "6x5")
    contact_sheet(preview, out / "preview_contact_05s.jpg", 2, "6x4")

    golden_probe = ffprobe(golden)
    preview_probe = ffprobe(preview)
    golden_probe_full = ffprobe(golden, full=True)
    preview_probe_full = ffprobe(preview, full=True)
    golden_timeline = ffprobe_frames(golden)
    preview_timeline = ffprobe_frames(preview)

    golden_metrics = metrics_for_frames(golden_frames, 1)
    preview_metrics = metrics_for_frames(preview_frames, 2)
    golden_motion = motion_profile(golden_metrics, golden_frames, 1)
    preview_motion = motion_profile(preview_metrics, preview_frames, 2)

    write_json(out / "00_manifest.json", {
        "schema_version": "1.0",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Create fidelity data from VEO golden and current local preview for local video studio training.",
        "golden_video": golden.as_posix(),
        "preview_video": preview.as_posix(),
        "outputs": {
            "golden_contact": (out / "golden_contact_2s.jpg").as_posix(),
            "preview_contact": (out / "preview_contact_05s.jpg").as_posix(),
            "golden_frames_dir": golden_frames.as_posix(),
            "preview_frames_dir": preview_frames.as_posix(),
        },
        "notes": [
            "Preview take 02 contains unplanned black foreground artifact.",
            "Preview take 04 has insufficient event/camera motion.",
            "Use JSON contracts before generating more local takes.",
        ],
    })
    write_json(out / "01_golden_ffprobe.json", golden_probe)
    write_json(out / "02_golden_ffprobe_full.json", golden_probe_full)
    write_json(out / "03_golden_frame_timeline.json", golden_timeline)
    write_json(out / "04_golden_sampled_frame_metrics_1s.json", golden_metrics)
    write_json(out / "05_golden_motion_profile_1s.json", golden_motion)
    write_json(out / "06_golden_auto_scene_segments.json", scene_segments_from_motion(golden_motion))
    write_json(out / "07_golden_take_contracts_from_veo.json", take_contracts_from_golden(GOLDEN_CAPTURE, golden_metrics, golden_motion))
    write_json(out / "08_preview_ffprobe.json", preview_probe)
    write_json(out / "09_preview_ffprobe_full.json", preview_probe_full)
    write_json(out / "10_preview_frame_timeline.json", preview_timeline)
    write_json(out / "11_preview_sampled_frame_metrics_05s.json", preview_metrics)
    write_json(out / "12_preview_motion_profile_05s.json", preview_motion)
    write_json(out / "13_preview_hallucination_report.json", preview_hallucination_report(preview_metrics, preview_motion))
    write_json(out / "14_comparison_preview_vs_golden.json", compare_preview_to_golden(golden_motion, preview_motion))
    write_json(out / "15_training_fidelity_dataset_index.json", {
        "golden_positive": {
            "video": golden.as_posix(),
            "contracts": (out / "07_golden_take_contracts_from_veo.json").as_posix(),
            "frame_metrics": (out / "04_golden_sampled_frame_metrics_1s.json").as_posix(),
            "motion_profile": (out / "05_golden_motion_profile_1s.json").as_posix(),
        },
        "local_preview_diagnostics": {
            "video": preview.as_posix(),
            "hallucination_report": (out / "13_preview_hallucination_report.json").as_posix(),
            "motion_profile": (out / "12_preview_motion_profile_05s.json").as_posix(),
        },
        "next_generation_gate": [
            "Before rendering, pick one golden take contract.",
            "Generate or select an approved keyframe matching must_keep_elements.",
            "Prompt must include temporal milestones, not only aesthetic style.",
            "Reject any take with undefined black foreground artifact.",
            "Reject any hat/chapeu take without visible event by second 3.",
        ],
    })

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
