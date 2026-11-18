from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
CHILD = ENGINE / "projetos" / "gohan_ssj2_take07_frenetic_multi_anchor_v2"
PARENT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")
SOURCES = [
    (CHILD / "takes" / "maestro_generated" / "take_07A2_381e72ab53294fad_minimax_h3_preview.mp4", 3.75),
    (CHILD / "takes" / "maestro_generated" / "take_07B2_ccf43ec8d4a04bad_minimax_h3_preview.mp4", 5.0),
    (CHILD / "takes" / "maestro_generated" / "take_07C2_6794aec655a84ab7_minimax_h3_preview.mp4", 5.0),
    (CHILD / "takes" / "maestro_generated" / "take_07D2_6bcf7bdd9496425b_minimax_h3_preview.mp4", 5.0),
]
OUTPUT = PARENT / "takes" / "maestro_generated" / "take_07_frenetic_multi_anchor_v3.mp4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            [str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames", "-show_entries", "format=duration,size", "-of", "json", str(path)],
            text=True,
            encoding="utf-8",
        )
    )


def main() -> None:
    for path, _ in SOURCES:
        if not path.is_file():
            raise FileNotFoundError(path)
    for path in (FFMPEG, FFPROBE):
        if not path.is_file():
            raise FileNotFoundError(path)

    edit_dir = CHILD / "edit"
    qc_dir = CHILD / "qc"
    edit_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)
    candidate = edit_dir / "take07_frenetic_multi_anchor_v3.mp4"

    filters: list[str] = []
    labels: list[str] = []
    for index, (_, source_seconds) in enumerate(SOURCES):
        label = f"s{index}"
        speed_factor = 2.5 / source_seconds
        filters.append(
            f"[{index}:v]trim=start=0:end={source_seconds:.6f},"
            f"setpts={speed_factor:.12f}*(PTS-STARTPTS),fps=24,"
            f"trim=end_frame=60,setpts=N/(24*TB)[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append("".join(labels) + "concat=n=4:v=1:a=0[vout]")

    subprocess.run(
        [str(FFMPEG), "-y"]
        + sum((["-i", str(path)] for path, _ in SOURCES), [])
        + ["-filter_complex", ";".join(filters), "-map", "[vout]", "-an", "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(candidate)],
        check=True,
    )

    info = probe(candidate)
    stream = info["streams"][0]
    frames = int(stream.get("nb_read_frames") or 0)
    duration = float(info["format"]["duration"])
    if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
        raise ValueError(f"Formato inesperado: {stream}")
    if frames != 240 or abs(duration - 10.0) > 0.01:
        raise ValueError(f"Montagem invalida: frames={frames}, duration={duration}")

    freeze = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(candidate), "-vf", "freezedetect=n=0.003:d=0.4", "-an", "-f", "null", "NUL"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    freeze_events = [line.strip() for line in freeze.stderr.splitlines() if "freeze_" in line]
    if freeze_events:
        raise ValueError("Montagem contem congelamento >=0,4 s: " + " | ".join(freeze_events))

    contact_sheet = qc_dir / "take07_frenetic_v3_contact_20.jpg"
    boundary_sheet = qc_dir / "take07_frenetic_v3_boundaries.jpg"
    subprocess.run(
        [str(FFMPEG), "-y", "-i", str(candidate), "-vf", "fps=2,scale=320:-1,tile=5x4", "-frames:v", "1", str(contact_sheet)],
        check=True,
    )
    boundary_filter = (
        "select=eq(n\\,58)+eq(n\\,59)+eq(n\\,60)+"
        "eq(n\\,118)+eq(n\\,119)+eq(n\\,120)+"
        "eq(n\\,178)+eq(n\\,179)+eq(n\\,180),scale=426:-1,tile=3x3"
    )
    subprocess.run(
        [str(FFMPEG), "-y", "-i", str(candidate), "-vf", boundary_filter, "-vsync", "0", "-frames:v", "1", str(boundary_sheet)],
        check=True,
    )

    shutil.copy2(candidate, OUTPUT)
    if sha256(candidate) != sha256(OUTPUT):
        raise ValueError("Hash divergiu na copia ao projeto principal.")

    queue_path = PARENT / "take_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    take = next(item for item in queue["takes"] if str(item.get("id")) == "07")
    now = datetime.now(timezone.utc).isoformat()
    video = take.setdefault("video", {})
    previous = str(video.get("output_active") or "")
    if previous and previous != str(OUTPUT):
        history = video.setdefault("output_history", [])
        if not any(item.get("path") == previous for item in history):
            history.append({"path": previous, "role": "output_active", "replaced_at": now, "replaced_by": "frenetic_multi_anchor_v3"})
    video.update({"status": "ready", "output_active": str(OUTPUT), "output_preview": str(OUTPUT), "output_review_candidate": str(OUTPUT)})
    take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take["maestro_status"] = "READY"
    take["render_authorized"] = False
    take["maestro_last_job_id"] = "take07_frenetic_multi_anchor_v3"
    take["maestro_last_error"] = ""
    take["maestro_updated_at"] = now
    take["maestro_notes"] = (
        "V3 substitui os 07A/B/C lentos por quatro microtakes freneticos com golpes, defesas, deslocamento e impactos sucessivos. "
        "Cada bloco usa movimento real acelerado para 2,5 s; cortes secos em acao, sem crossfade e sem congelamento. "
        "Um Gohan SSJ2 e um Perfect Cell sem rabo nos quatro blocos. Rejeitados preservados; pendente revisao humana."
    )
    qc = take.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["human_visual_approval"] = "pending"
    qc["transition_motion_gate"] = {
        "status": "pending_human_review",
        "method": "four_frenetic_tailless_microtakes_hard_cut_on_impacts",
        "frames": frames,
        "duration_seconds": duration,
        "crossfade_frames": 0,
        "freeze_frames": 0,
    }
    for request in reversed(take.get("maestro_director_requests", [])):
        if request.get("status") == "PENDING" and request.get("category") == "PROGRESSION":
            request["status"] = "DELIVERED"
            request["updated_at"] = now
            request["delivered_candidate"] = str(OUTPUT)
            break
    atomic_json(queue_path, queue)

    manifest = {
        "schemaVersion": "gohan_take07_frenetic_multi_anchor_v3",
        "createdAt": now,
        "candidate": str(candidate),
        "candidateSha256": sha256(candidate),
        "registeredParentCandidate": str(OUTPUT),
        "frames": frames,
        "fps": 24,
        "durationSeconds": duration,
        "transition": "three_hard_cuts_on_continuing_impacts",
        "crossfadeFrames": 0,
        "freezeEvents": freeze_events,
        "contactSheet": str(contact_sheet),
        "boundarySheet": str(boundary_sheet),
        "sources": [
            {"path": str(path), "sha256": sha256(path), "interval": [0.0, source_seconds], "targetFrames": 60}
            for path, source_seconds in SOURCES
        ],
        "humanVisualReviewRequired": True,
    }
    atomic_json(edit_dir / "take07_frenetic_multi_anchor_v3.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
