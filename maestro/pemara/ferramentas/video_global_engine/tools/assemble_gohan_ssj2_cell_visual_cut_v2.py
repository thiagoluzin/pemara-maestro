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
OUTPUT = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_motion_source_720p24.mp4"
MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v2_motion_source.json"
CONTACT_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v2_motion_source_contact_32.jpg"
BOUNDARY_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v2_motion_source_boundaries_21.jpg"
SCHEMA_VERSION = "gohan_ssj2_cell_visual_cut_v2_motion_source"
SUPERSEDES_CANDIDATE = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v1_720p24.mp4"
TRANSITION_DESCRIPTION = "hard cuts only; four static tails and one frozen opening removed"
PLANNED_FINISH = "Practical-RIFE 4.25 midpoint x2 to 48fps, then setpts cadence at 60fps (1.25x)"

# End frames are exclusive.  The chosen endpoints keep one boundary/anchor frame
# but remove the static tails measured by FFmpeg freezedetect.  Take 03 also
# skips its frozen opening while keeping the same visible start anchor.
EDIT = [
    {"take_id": "01", "start_frame": 0, "end_frame": 215, "reason": "remove static tail from 8.916667s"},
    {"take_id": "02", "start_frame": 0, "end_frame": 212, "reason": "remove static tail from 8.791667s"},
    {"take_id": "03", "start_frame": 12, "end_frame": 226, "reason": "remove frozen opening through 0.5s and static tail from 9.375s"},
    {"take_id": "04", "start_frame": 0, "end_frame": 240, "reason": "no freeze detected"},
    {"take_id": "05", "start_frame": 0, "end_frame": 227, "reason": "remove static tail from 9.416667s"},
    {"take_id": "06", "start_frame": 0, "end_frame": 240, "reason": "no freeze detected"},
    {"take_id": "07", "start_frame": 0, "end_frame": 240, "reason": "no freeze detected"},
    {"take_id": "08", "start_frame": 0, "end_frame": 240, "reason": "no freeze detected"},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            [
                str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt",
                "-show_entries", "format=duration,size", "-of", "json", str(path),
            ],
            text=True,
            encoding="utf-8",
        )
    )


def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    takes = {str(item.get("id")): item for item in queue.get("takes", []) if isinstance(item, dict)}
    sources: list[dict] = []
    for edit in EDIT:
        take_id = edit["take_id"]
        take = takes[take_id]
        if str(take.get("maestro_status") or "").upper() != "APPROVED":
            raise ValueError(f"Take {take_id} nao esta aprovado no Maestro")
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        source = Path(str(video.get("output_active") or ""))
        if not source.is_file():
            raise FileNotFoundError(source)
        info = probe(source)
        stream = info["streams"][0]
        frames = int(stream.get("nb_read_frames") or 0)
        if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
            raise ValueError(f"Take {take_id} fora do contrato 720p24")
        if edit["start_frame"] < 0 or edit["end_frame"] > frames or edit["start_frame"] >= edit["end_frame"]:
            raise ValueError(f"Recorte invalido no take {take_id}: {edit}, frames={frames}")
        sources.append(
            {
                **edit,
                "name": str(take.get("name") or take.get("title") or ""),
                "path": source,
                "source_frames": frames,
                "source_sha256": sha256(source),
                "edit_frames": edit["end_frame"] - edit["start_frame"],
            }
        )

    expected_frames = sum(item["edit_frames"] for item in sources)
    expected_duration = expected_frames / 24.0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    filters: list[str] = []
    labels: list[str] = []
    for index, source in enumerate(sources):
        label = f"t{index}"
        filters.append(
            f"[{index}:v]trim=start_frame={source['start_frame']}:end_frame={source['end_frame']},"
            f"setpts=N/(24*TB)[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(sources)}:v=1:a=0[vout]")

    command = [str(FFMPEG), "-hide_banner", "-y"]
    for source in sources:
        command.extend(["-i", str(source["path"])])
    command.extend(
        [
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-an",
            "-r", "24", "-fps_mode", "cfr", "-frames:v", str(expected_frames),
            "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-profile:v", "high",
            "-rc", "vbr", "-cq", "16", "-b:v", "0", "-maxrate", "24M", "-bufsize", "48M",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
        ]
    )
    subprocess.run(command, check=True)

    output_info = probe(OUTPUT)
    stream = output_info["streams"][0]
    output_frames = int(stream.get("nb_read_frames") or 0)
    output_duration = float(output_info["format"]["duration"])
    if output_frames != expected_frames or abs(output_duration - expected_duration) > 0.01:
        raise ValueError(f"Montagem invalida: frames={output_frames}, duration={output_duration}")
    if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
        raise ValueError(f"Saida fora do contrato: {stream}")

    decode = subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(OUTPUT), "-f", "null", "NUL"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if decode.returncode != 0:
        raise ValueError("Falha de decodificacao: " + decode.stderr[-2000:])

    freeze = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(OUTPUT), "-vf", "freezedetect=n=0.003:d=0.4", "-an", "-f", "null", "NUL"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    freeze_events = [line.strip() for line in freeze.stderr.splitlines() if "freeze_" in line]
    if freeze_events:
        raise ValueError("O V2 ainda possui congelamentos >= 0.4s: " + " | ".join(freeze_events))

    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT), "-vf",
            f"fps={32 / expected_duration:.12f},scale=240:-1,tile=8x4", "-frames:v", "1", str(CONTACT_SHEET),
        ],
        check=True,
    )
    cumulative = 0
    boundary_frames: list[int] = []
    for source in sources[:-1]:
        cumulative += source["edit_frames"]
        boundary_frames.extend([cumulative - 1, cumulative, cumulative + 1])
    selection = "+".join(f"eq(n\\,{frame})" for frame in boundary_frames)
    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT), "-vf",
            f"select={selection},scale=426:-1,tile=3x7", "-fps_mode", "passthrough",
            "-frames:v", "1", str(BOUNDARY_SHEET),
        ],
        check=True,
    )

    timeline = []
    cursor = 0
    for source in sources:
        start = cursor
        cursor += source["edit_frames"]
        timeline.append(
            {
                "takeId": source["take_id"],
                "name": source["name"],
                "outputStartFrame": start,
                "outputEndFrameExclusive": cursor,
                "outputStartSeconds": start / 24.0,
                "outputEndSeconds": cursor / 24.0,
                "source": str(source["path"]),
                "sourceSha256": source["source_sha256"],
                "sourceFrames": source["source_frames"],
                "sourceStartFrame": source["start_frame"],
                "sourceEndFrameExclusive": source["end_frame"],
                "editFrames": source["edit_frames"],
                "editReason": source["reason"],
            }
        )

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "RIFE60_PENDING",
        "supersedesRejectedCandidate": str(SUPERSEDES_CANDIDATE),
        "output": str(OUTPUT),
        "outputSha256": sha256(OUTPUT),
        "encoder": "h264_nvenc",
        "width": 1280,
        "height": 720,
        "fps": 24,
        "frames": output_frames,
        "durationSeconds": output_duration,
        "audio": "none; Foley remains gated by owner picture approval",
        "transition": TRANSITION_DESCRIPTION,
        "freezeEventsAtLeast0_4Seconds": [],
        "plannedRifeFinish": PLANNED_FINISH,
        "plannedDeliveryDurationSeconds": output_frames * 2 / 60.0,
        "contactSheet": str(CONTACT_SHEET),
        "boundarySheet": str(BOUNDARY_SHEET),
        "timeline": timeline,
        "humanPlaybackRequired": True,
    }
    atomic_json(MANIFEST, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
