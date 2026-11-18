from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
CHILD = ENGINE / "projetos" / "gohan_ssj2_take04_cells_jr_multi_anchor_v2"
PARENT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")


CLIPS = (
    ("04A", "take_04A_924b3df4ce5b46f1_minimax_h3_preview.mp4", 2.0, 4.458333),
    ("04B", "take_04B_60cab841505b4ff8_minimax_h3_preview.mp4", 2.0, 3.041667),
    ("04C2", "take_04C2_f17d9ec4d4204c49_minimax_h3_preview.mp4", 2.0, 4.625000),
    ("04D1", "take_04D1_2811b006945941ff_minimax_h3_preview.mp4", 1.0, 4.458333),
    ("04D2R1", "take_04D2R1_0c741031ed2a471f_minimax_h3_preview.mp4", 1.0, 3.875000),
    ("04E", "take_04E_9f6ed1b1542340d7_minimax_h3_preview.mp4", 2.0, 3.750000),
)


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
    command = [
        str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames",
        "-show_entries", "format=duration", "-of", "json", str(path),
    ]
    return json.loads(subprocess.check_output(command, text=True, encoding="utf-8"))


def main() -> None:
    if not FFMPEG.is_file() or not FFPROBE.is_file():
        raise FileNotFoundError("Runtime FFmpeg do Maestro nao encontrado.")

    queue_path = CHILD / "take_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    takes = {str(item.get("id")): item for item in queue.get("takes", []) if isinstance(item, dict)}
    sources: list[Path] = []
    evidence: list[dict] = []
    for take_id, filename, editorial_seconds, motion_end in CLIPS:
        take = takes.get(take_id)
        if not take or str(take.get("maestro_status") or "").upper() != "APPROVED":
            raise ValueError(f"{take_id} nao esta APPROVED no projeto filho.")
        source = CHILD / "takes" / "maestro_generated" / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        info = probe(source)
        stream = info["streams"][0]
        if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
            raise ValueError(f"Formato inesperado em {take_id}: {stream}")
        if int(stream.get("nb_read_frames") or 0) < 124:
            raise ValueError(f"{take_id} tem menos de 124 quadros.")
        sources.append(source)
        evidence.append({
            "take_id": take_id,
            "source": str(source),
            "sha256": sha256(source),
            "editorial_seconds": editorial_seconds,
            "motion_end_seconds": motion_end,
        })

    # Each approved microtake's useful-motion interval is time-compressed to its
    # editorial slot. The cut occurs at the first arrival near the end anchor,
    # before the generated static tail, and the next clip begins on that anchor.
    filters: list[str] = []
    segment_labels: list[str] = []
    for index, (_, _, seconds, motion_end) in enumerate(CLIPS):
        total_frames = round(seconds * 24)
        multiplier = seconds / motion_end
        filters.append(
            f"[{index}:v]trim=start=0:end={motion_end:.6f},"
            f"setpts={multiplier:.12f}*(PTS-STARTPTS),fps=24,"
            f"trim=end_frame={total_frames},setpts=N/(24*TB)[s{index}]"
        )
        segment_labels.append(f"[s{index}]")
    filters.append("".join(segment_labels) + f"concat=n={len(CLIPS)}:v=1:a=0[vout]")

    edit_dir = CHILD / "edit"
    edit_dir.mkdir(parents=True, exist_ok=True)
    candidate = edit_dir / "take04_multi_anchor_motion_retimed_v2.mp4"
    command = [str(FFMPEG), "-y"]
    for source in sources:
        command.extend(["-i", str(source)])
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[vout]",
        "-an", "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
        "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(candidate),
    ])
    subprocess.run(command, check=True)

    result_probe = probe(candidate)
    result_stream = result_probe["streams"][0]
    frames = int(result_stream.get("nb_read_frames") or 0)
    duration = float(result_probe["format"]["duration"])
    if frames != 240 or abs(duration - 10.0) > 0.01:
        raise ValueError(f"Montagem invalida: frames={frames}, duration={duration}")

    parent_takes = PARENT / "takes" / "maestro_generated"
    parent_takes.mkdir(parents=True, exist_ok=True)
    destination = parent_takes / "take_04_multi_anchor_motion_retimed_v2.mp4"
    shutil.copy2(candidate, destination)
    if sha256(candidate) != sha256(destination):
        raise ValueError("Hash divergiu na copia para o projeto principal.")

    parent_queue_path = PARENT / "take_queue.json"
    parent_queue = json.loads(parent_queue_path.read_text(encoding="utf-8"))
    take04 = next(item for item in parent_queue["takes"] if str(item.get("id")) == "04")
    now = datetime.now(timezone.utc).isoformat()
    video = take04.setdefault("video", {})
    previous = str(video.get("output_active") or "")
    history = video.setdefault("output_history", [])
    if previous and previous != str(destination):
        history.append({
            "path": previous,
            "role": "output_active",
            "replaced_at": now,
            "replaced_by": "approved_multi_anchor_motion_retimed_v2",
        })
    video.update({
        "status": "ready",
        "output_active": str(destination),
        "output_preview": str(destination),
        "output_review_candidate": str(destination),
    })
    take04["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take04["maestro_status"] = "READY"
    take04["render_authorized"] = False
    take04["maestro_last_job_id"] = "approved_multi_anchor_motion_retimed_v2"
    take04["maestro_last_error"] = ""
    take04["maestro_updated_at"] = now
    take04["maestro_notes"] = (
        "V2 retimada somente com 04A, 04B, 04C2, 04D1, 04D2R1 e 04E aprovados. "
        "O trecho quase congelado de 04B foi excluido antes da retimagem; cortes secos em movimento. "
        "V1 e todos os candidatos anteriores permanecem preservados."
    )
    qc = take04.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["human_visual_approval"] = "pending"
    qc["transition_motion_gate"] = {
        "status": "pending_human_review",
        "method": "hard_cuts_on_motion_no_crossfade",
        "frames": frames,
        "duration_seconds": duration,
    }
    atomic_json(parent_queue_path, parent_queue)

    manifest = {
        "schema_version": "gohan_take04_approved_multi_anchor_motion_retimed_v2",
        "created_at": now,
        "candidate": str(candidate),
        "candidate_sha256": sha256(candidate),
        "registered_parent_candidate": str(destination),
        "frames": frames,
        "fps": 24,
        "duration_seconds": duration,
        "audio": "visual_only",
        "transition": "hard_cuts_on_motion_no_crossfade",
        "sources": evidence,
        "human_visual_review_required": True,
    }
    atomic_json(edit_dir / "take04_multi_anchor_motion_retimed_v2.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
