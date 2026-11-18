from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
VIDEO = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4"
SOURCE_MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_motion_source.json"
OUTPUT = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v2_motion_windows.json"


def main() -> None:
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8-sig"))
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise FileNotFoundError(VIDEO)
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if abs(fps - 60.0) > 0.01:
        raise ValueError(f"FPS inesperado: {fps}")

    sample_step = 6  # Compare positions 0.1 second apart.
    window_seconds = 0.5
    previous_gray = None
    samples: list[dict] = []
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % sample_step == 0:
            gray = cv2.cvtColor(cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
            if previous_gray is not None:
                delta = float(cv2.absdiff(gray, previous_gray).mean())
                flow = cv2.calcOpticalFlowFarneback(
                    previous_gray,
                    gray,
                    None,
                    0.5,
                    2,
                    15,
                    2,
                    5,
                    1.1,
                    0,
                )
                magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
                samples.append(
                    {
                        "time": frame_index / fps,
                        "delta": delta,
                        "flowMedian": float(np.median(magnitude)),
                        "flowP75": float(np.percentile(magnitude, 75)),
                    }
                )
            previous_gray = gray
        frame_index += 1
    cap.release()

    duration = frame_index / fps
    windows: list[dict] = []
    cursor = 0.0
    while cursor < duration:
        subset = [item for item in samples if cursor <= item["time"] < cursor + window_seconds]
        if subset:
            windows.append(
                {
                    "start": round(cursor, 3),
                    "end": round(min(cursor + window_seconds, duration), 3),
                    "deltaMedian": round(float(np.median([item["delta"] for item in subset])), 4),
                    "flowMedian": round(float(np.median([item["flowMedian"] for item in subset])), 4),
                    "flowP75Median": round(float(np.median([item["flowP75"] for item in subset])), 4),
                }
            )
        cursor += window_seconds

    global_flow = np.array([item["flowMedian"] for item in windows], dtype=np.float32)
    low_threshold = float(np.percentile(global_flow, 25))
    critical_threshold = float(np.percentile(global_flow, 10))

    take_windows: list[dict] = []
    output_cursor = 0
    for item in source["timeline"]:
        output_cursor += int(item["editFrames"])
        end = output_cursor / 30.0  # Each 24fps source frame becomes two final frames at 60fps.
        start = end - int(item["editFrames"]) / 30.0
        subset = [win for win in windows if win["start"] >= start and win["end"] <= end + 0.001]
        take_windows.append(
            {
                "takeId": item["takeId"],
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "medianFlow": round(float(np.median([win["flowMedian"] for win in subset])), 4),
                "lowMotionWindowCount": sum(win["flowMedian"] <= low_threshold for win in subset),
                "criticalMotionWindowCount": sum(win["flowMedian"] <= critical_threshold for win in subset),
                "windowCount": len(subset),
            }
        )

    payload = {
        "video": str(VIDEO),
        "fps": fps,
        "frames": frame_index,
        "duration": duration,
        "sampleStepFrames": sample_step,
        "windowSeconds": window_seconds,
        "lowMotionThresholdP25": round(low_threshold, 4),
        "criticalMotionThresholdP10": round(critical_threshold, 4),
        "takes": take_windows,
        "lowestMotionWindows": sorted(windows, key=lambda item: (item["flowMedian"], item["deltaMedian"]))[:30],
        "windows": windows,
        "note": "Automated optical-flow screening; owner playback and visual direction remain authoritative.",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("lowMotionThresholdP25", "criticalMotionThresholdP10", "takes", "lowestMotionWindows")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
