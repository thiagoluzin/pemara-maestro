"""Assemble the corrected Gohan SSJ2 film as one motion-first 720p24 source."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE = PROJECT / "take_queue.json"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")
OUTPUT = PROJECT / "edit" / "gohan_ssj2_cell_continuous_v6_motion_source_720p24.mp4"
MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_continuous_v6_motion_source.json"
CONTACT = PROJECT / "qc" / "gohan_ssj2_cell_continuous_v6_motion_source_contact_32.jpg"
BOUNDARIES = PROJECT / "qc" / "gohan_ssj2_cell_continuous_v6_motion_boundaries_39.jpg"

# Frame ends are exclusive.  Take 03 is intentionally omitted because the
# transformation is already completed by CP02_03 and 03 held an effects-only
# tableau.  No crossfades are used.  Generated connectors are trimmed before
# any FL2VA endpoint pull or repeated composition.
EDIT = [
    ("01", 0, 109, "retain short Android 16 setup; remove its slow remainder"),
    ("C01_P02", 10, 120, "physical camera approach into the descending boot"),
    ("P02", 0, 107, "stomp, mechanical fragments and Gohan rush; remove detected 0.54s freeze ending at 14.13s in the first assembly"),
    ("CP02_03", 0, 110, "anger shockwave and SSJ2 transformation in motion"),
    ("C03_04", 12, 84, "introduce exactly two blue Cell Juniors; cut before adult-Cell endpoint reversal"),
    ("04", 36, 226, "two-Junior combat from active entry through final elimination"),
    ("C04_05_R1", 0, 120, "Junior fragments to separate tailless adult Cell clash"),
    ("05", 5, 195, "direct close combat through rising launch preparation"),
    ("C05_06_R1", 0, 90, "uppercut continuation and aerial pursuit; cut before endpoint hold"),
    ("06", 10, 200, "deflection, block, knee and wall-flight consequence"),
    ("C06_07_R1", 0, 100, "tailless wall-breach chase; cut before repeated closing geometry"),
    ("07", 10, 200, "frenetic exchange and decisive pressure"),
    ("C07_08_R1", 0, 100, "launch and long camera corridor; retain last frame where Cell is still a distant moving silhouette"),
    ("08", 112, 240, "resume with Cell already distant, then Kamehameha and mountain impact; exclude return to close combat"),
]

CONNECTOR_QC = {
    "C01_P02": "PASS: tailless Cell advances and jumps; camera closes physically to the descending boot; rubble and dust retain independent motion.",
    "CP02_03": "PASS: stomp consequence becomes anger shockwave and SSJ2 transformation with continuous forward motion; tailless Cell enters at depth.",
    "C03_04": "PASS_WITH_EDITORIAL_TRIM: exactly two cobalt-blue Juniors enter as separate bodies; late adult-Cell endpoint reversal excluded at frame 84.",
    "C04_05_R1": "PASS: blue Junior fragments; separate adult Cell enters; direct clash; no tail; full-frame progression.",
    "C05_06_R1": "PASS_WITH_EDITORIAL_TRIM: aerial launch and pursuit progress; endpoint hold excluded at frame 90.",
    "C06_07_R1": "PASS_WITH_EDITORIAL_TRIM: wall-flight and approach progress; only two rigid back plates, no curved tail; repetitive ending excluded.",
    "C07_08_R1": "PASS_WITH_EDITORIAL_TRIM: immediate launch and long-distance camera travel; late anchor re-entry excluded at frame 100.",
}

REVIEW_SOURCE_HASHES = {
    "01": "213a2122e04668b2eea2b6bf7a144cf8143ef6942371219bf0a02ac23b677750",
    "P02": "36d87f72d283c37cff5d3d31279cc41c7ec8e90372606fcd11c31061af977836",
}

SOURCE_OVERRIDES = {
    "01": PROJECT / "takes" / "maestro_generated" / "take_01_6ce4a308ecd04870_minimax_h3_preview.mp4",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt",
        "-show_entries", "format=duration,size", "-of", "json", str(path),
    ], text=True, encoding="utf-8"))


def main() -> None:
    if OUTPUT.exists() or MANIFEST.exists():
        raise FileExistsError("V6 motion source already exists; preserve it and create a new version for another attempt.")
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    takes = {str(t.get("id")): t for t in queue.get("takes", []) if isinstance(t, dict)}
    timeline = []
    sources = []
    cursor = 0
    for take_id, start, end, reason in EDIT:
        take = takes[take_id]
        if take_id in CONNECTOR_QC:
            video = take.get("video") or {}
            if str(video.get("status") or "").lower() != "ready":
                raise ValueError(f"Corrected connector {take_id} has no ready MP4")
        elif take_id not in REVIEW_SOURCE_HASHES and str(take.get("maestro_status") or "").upper() != "APPROVED":
            raise ValueError(f"Source take {take_id} is not owner approved")
        path = SOURCE_OVERRIDES.get(take_id) or Path(str((take.get("video") or {}).get("output_active") or ""))
        if not path.is_file() and take_id == "C01_P02":
            path = PROJECT / "work" / "continuous_rebuild_v6" / "connectors" / "C01_P02.mp4"
        if not path.is_file():
            raise FileNotFoundError(path)
        if take_id in REVIEW_SOURCE_HASHES and sha256(path).lower() != REVIEW_SOURCE_HASHES[take_id]:
            raise ValueError(f"Review source {take_id} does not match the locked reviewed artifact")
        info = probe(path)
        stream = info["streams"][0]
        count = int(stream.get("nb_read_frames") or 0)
        if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
            raise ValueError(f"{take_id} is outside 720p24 contract")
        if start < 0 or end > count or start >= end:
            raise ValueError(f"Invalid frame window for {take_id}: {start}-{end}/{count}")
        item = {"takeId": take_id, "path": path, "sourceFrames": count, "sourceSha256": sha256(path), "sourceStartFrame": start, "sourceEndFrameExclusive": end, "editFrames": end - start, "editReason": reason}
        sources.append(item)
        timeline.append({**{k: (str(v) if isinstance(v, Path) else v) for k, v in item.items()}, "outputStartFrame": cursor, "outputEndFrameExclusive": cursor + end - start, "outputStartSeconds": cursor / 24.0, "outputEndSeconds": (cursor + end - start) / 24.0})
        cursor += end - start

    expected_frames = cursor
    filters = []
    labels = []
    command = [str(FFMPEG), "-hide_banner", "-y"]
    for index, item in enumerate(sources):
        command.extend(["-i", str(item["path"])])
        label = f"v{index}"
        filters.append(f"[{index}:v]trim=start_frame={item['sourceStartFrame']}:end_frame={item['sourceEndFrameExclusive']},setpts=N/(24*TB)[{label}]")
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[out]")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-an", "-r", "24", "-fps_mode", "cfr", "-frames:v", str(expected_frames), "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-profile:v", "high", "-rc", "vbr", "-cq", "16", "-b:v", "0", "-maxrate", "24M", "-bufsize", "48M", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT)])
    subprocess.run(command, check=True)

    result = probe(OUTPUT)
    stream = result["streams"][0]
    frames = int(stream.get("nb_read_frames") or 0)
    duration = float(result["format"]["duration"])
    if frames != expected_frames or abs(duration - expected_frames / 24.0) > 0.01:
        raise ValueError(f"Unexpected assembly timing: {frames} frames, {duration}s")
    decode = subprocess.run([str(FFMPEG), "-v", "error", "-i", str(OUTPUT), "-f", "null", "NUL"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if decode.returncode:
        raise ValueError(decode.stderr[-2000:])
    freeze = subprocess.run([str(FFMPEG), "-hide_banner", "-i", str(OUTPUT), "-vf", "freezedetect=n=0.003:d=0.4", "-an", "-f", "null", "NUL"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    freeze_events = [line.strip() for line in freeze.stderr.splitlines() if "freeze_" in line]
    if freeze_events:
        raise ValueError("Freeze >=0.4s remains: " + " | ".join(freeze_events))

    CONTACT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT), "-vf", f"fps={32 / duration:.12f},scale=240:-1,tile=8x4", "-frames:v", "1", str(CONTACT)], check=True)
    boundary_frames = []
    for item in timeline[:-1]:
        center = int(item["outputEndFrameExclusive"])
        boundary_frames.extend([center - 1, center, center + 1])
    selection = "+".join(f"eq(n\\,{frame})" for frame in boundary_frames)
    subprocess.run([str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT), "-vf", f"select={selection},scale=320:-1,tile=3x13", "-fps_mode", "passthrough", "-frames:v", "1", str(BOUNDARIES)], check=True)

    manifest = {
        "schemaVersion": "gohan_ssj2_cell_continuous_v6_motion_source", "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "RIFE60_PENDING", "output": str(OUTPUT), "outputSha256": sha256(OUTPUT), "width": 1280, "height": 720,
        "fps": 24, "frames": frames, "durationSeconds": duration, "audio": "none; Foley gated until owner picture approval",
        "transition": "hard action cuts only; generated moving connectors; no crossfade; no freeze; no static tail",
        "omittedTake03": "Redundant effects-only tableau removed; transformation already completes in CP02_03 and Juniors enter in C03_04.",
        "connectorInternalQc": CONNECTOR_QC, "freezeEventsAtLeast0_4Seconds": [],
        "plannedRifeFinish": "Practical-RIFE 4.25 midpoint x2 to 48fps, then 60fps cadence for 1.25x final action speed",
        "plannedDeliveryDurationSeconds": frames * 2 / 60.0, "contactSheet": str(CONTACT), "boundarySheet": str(BOUNDARIES),
        "timeline": timeline, "humanPlaybackRequired": True,
    }
    atomic_json(MANIFEST, manifest)

    for take_id, evidence in CONNECTOR_QC.items():
        take = takes[take_id]
        take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
        take["maestro_status"] = "NEEDS_REVIEW"
        take["render_authorized"] = False
        take.setdefault("video_generation", {})["render_authorized"] = False
        gate = take.setdefault("qc", {}).setdefault("transition_motion_gate", {})
        gate.update({"status": "approved_for_internal_assembly", "evident_camera": True, "real_depth": True, "internal_action": True, "clear_progression": True, "continuous_action": True, "motion_across_all_intervals": True, "moving_anchor_context": True, "no_crossfade": True, "no_freeze": True, "no_static_tail": True, "no_reset": True, "evidence": evidence})
        take["qc"]["status"] = "internal_visual_qc_pass_pending_full_film_owner_review"
        take["qc"]["human_visual_approval"] = "pending_full_film_owner_review"
    queue["status"] = "V6_MOTION_SOURCE_READY_FOR_RIFE60"
    queue["render_authorized"] = False
    queue["assembly_candidate_v6"] = {"file": str(OUTPUT), "sha256": manifest["outputSha256"], "status": "RIFE60_PENDING", "timeline": [t["takeId"] for t in timeline]}
    atomic_json(QUEUE, queue)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
