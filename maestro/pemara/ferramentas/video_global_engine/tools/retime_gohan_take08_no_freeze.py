from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")
SOURCE = PROJECT / "takes" / "maestro_generated" / "take_08_8749730ee87949ff_minimax_h3_preview.mp4"
OUTPUT = PROJECT / "takes" / "maestro_generated" / "take_08_motion_retimed_v2.mp4"
USEFUL_END_SECONDS = 9.416667
TARGET_SECONDS = 10.0


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
            [
                str(FFPROBE),
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate,nb_read_frames",
                "-show_entries",
                "format=duration,size",
                "-of",
                "json",
                str(path),
            ],
            text=True,
            encoding="utf-8",
        )
    )


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if not FFMPEG.is_file() or not FFPROBE.is_file():
        raise FileNotFoundError("Runtime FFmpeg do Maestro nao encontrado.")

    multiplier = TARGET_SECONDS / USEFUL_END_SECONDS
    subprocess.run(
        [
            str(FFMPEG),
            "-y",
            "-i",
            str(SOURCE),
            "-vf",
            f"trim=start=0:end={USEFUL_END_SECONDS:.6f},setpts={multiplier:.12f}*(PTS-STARTPTS),fps=24,trim=end_frame=240,setpts=N/(24*TB)",
            "-an",
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            "18",
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ],
        check=True,
    )
    info = probe(OUTPUT)
    stream = info["streams"][0]
    frames = int(stream.get("nb_read_frames") or 0)
    duration = float(info["format"]["duration"])
    if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
        raise ValueError(f"Formato inesperado: {stream}")
    if frames != 240 or abs(duration - TARGET_SECONDS) > 0.01:
        raise ValueError(f"Retiming invalido: frames={frames}, duration={duration}")

    queue_path = PROJECT / "take_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    take = next(item for item in queue["takes"] if str(item.get("id")) == "08")
    video = take.setdefault("video", {})
    previous = str(video.get("output_active") or "")
    now = datetime.now(timezone.utc).isoformat()
    if previous and previous != str(OUTPUT):
        video.setdefault("output_history", []).append(
            {"path": previous, "role": "output_active", "replaced_at": now, "replaced_by": "motion_retimed_v2"}
        )
    video.update(
        {
            "status": "ready",
            "output_active": str(OUTPUT),
            "output_preview": str(OUTPUT),
            "output_review_candidate": str(OUTPUT),
        }
    )
    take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take["maestro_status"] = "READY"
    take["render_authorized"] = False
    take["maestro_last_job_id"] = "take08_motion_retimed_v2"
    take["maestro_last_error"] = ""
    take["maestro_updated_at"] = now
    take["maestro_notes"] = (
        "V2 preserva o bruto H3 e retima somente 0-9,416667 s para 10,000 s, removendo a cauda congelada final. "
        "QC visual: um Gohan SSJ2, um Perfect Cell sem cauda, Kamehameha azul-branco e impacto na montanha. "
        "Candidato pendente de revisao visual humana."
    )
    qc = take.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["human_visual_approval"] = "pending"
    qc["transition_motion_gate"] = {
        "status": "pending_human_review",
        "method": "useful_motion_retimed_no_crossfade",
        "source_useful_end_seconds": USEFUL_END_SECONDS,
        "frames": frames,
        "duration_seconds": duration,
    }
    atomic_json(queue_path, queue)
    print(
        json.dumps(
            {
                "ok": True,
                "source": str(SOURCE),
                "sourceSha256": sha256(SOURCE),
                "candidate": str(OUTPUT),
                "candidateSha256": sha256(OUTPUT),
                "frames": frames,
                "durationSeconds": duration,
                "humanReviewRequired": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
