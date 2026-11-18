from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
PROJECTS = BASE / "ferramentas" / "video_global_engine" / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
SOURCE = PROJECT / "takes" / "maestro_generated" / "take_02_36b6ff95cf664414_minimax_h3_preview.mp4"
OUTPUT = PROJECT / "takes" / "maestro_generated" / "take_02_microtake_v3_motion_cut_4s.mp4"
MANIFEST = PROJECT / "qc" / "take02_microtake_v3_motion_cut_4s.json"
CONTACT = PROJECT / "qc" / "take02_microtake_v3_motion_cut_4s_contact_20.jpg"
QUEUE = PROJECT / "take_queue.json"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-y", "-i", str(SOURCE),
            "-vf", "trim=start_frame=0:end_frame=96,setpts=N/(24*TB)",
            "-an", "-r", "24", "-fps_mode", "cfr", "-frames:v", "96",
            "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq",
            "-profile:v", "high", "-rc", "vbr", "-cq", "16", "-b:v", "0",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
        ],
        check=True,
    )
    probe = json.loads(
        subprocess.check_output(
            [
                str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames",
                "-show_entries", "format=duration,size", "-of", "json", str(OUTPUT),
            ],
            text=True,
            encoding="utf-8",
        )
    )
    stream = probe["streams"][0]
    frames = int(stream["nb_read_frames"])
    duration = float(probe["format"]["duration"])
    if frames != 96 or abs(duration - 4.0) > 0.01:
        raise ValueError(f"Recorte invalido: frames={frames}, duration={duration}")
    freeze = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(OUTPUT), "-vf", "freezedetect=n=0.003:d=0.35", "-an", "-f", "null", "NUL"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    freeze_events = [line.strip() for line in freeze.stderr.splitlines() if "freeze_" in line]
    if freeze_events:
        raise ValueError("Recorte ainda possui freeze >=0.35s: " + " | ".join(freeze_events))
    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-y", "-i", str(OUTPUT),
            "-vf", "fps=5,scale=256:-1,tile=5x4", "-frames:v", "1", str(CONTACT),
        ],
        check=True,
    )

    if str(STUDIO) not in sys.path:
        sys.path.insert(0, str(STUDIO))
    from video_projects import set_take_generation_state

    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    take = next(item for item in queue["takes"] if str(item.get("id")) == "02")
    job_id = str(take.get("maestro_last_job_id") or "")
    if job_id != "36b6ff95cf66441493ac5cc2fa5ab3cb":
        raise ValueError(f"Job ativo inesperado: {job_id}")
    set_take_generation_state(
        PROJECTS,
        PROJECT_ID,
        "02",
        status="READY",
        job_id=job_id,
        preview_path=OUTPUT,
    )

    now = datetime.now(timezone.utc).isoformat()
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    take = next(item for item in queue["takes"] if str(item.get("id")) == "02")
    take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take["maestro_status"] = "READY"
    take["render_authorized"] = False
    take["maestro_notes"] = (
        "Novo footage H3 V3, nao uma remontagem do V2. O bruto de 5,166667 s foi reprovado internamente porque chegou cedo "
        "a uma pose com relampago no ultimo segundo. Este candidato preserva somente os primeiros 96 quadros/4,000 s: "
        "dolly fisico, descida da bota, impacto, fissura e reacao de Gohan. Bruto e videos anteriores permanecem no historico."
    )
    qc = take.setdefault("qc", {})
    qc.update(
        {
            "status": "new_footage_motion_cut_pending_human_review",
            "human_visual_approval": "pending",
            "transition_motion_gate": {
                "status": "technical_pass_pending_owner_visual_qc",
                "new_generated_footage": True,
                "source_frames": 124,
                "published_frames": 96,
                "published_duration_seconds": 4.0,
                "discarded_static_pose_tail_seconds": 1.166667,
                "freeze_events_at_least_0_35_seconds": 0,
                "crossfade_frames": 0,
            },
            "audio_gate": "BLOCKED_UNTIL_OWNER_PICTURE_APPROVAL",
        }
    )
    take["maestro_updated_at"] = now
    queue["render_authorized"] = False
    queue["status"] = "TAKE02_V3_NEW_FOOTAGE_PENDING_OWNER_REVIEW"
    queue["updated_at"] = now
    atomic_json(QUEUE, queue)

    payload = {
        "schemaVersion": "gohan_take02_microtake_v3_motion_cut_4s",
        "createdAt": now,
        "status": "PENDING_OWNER_VISUAL_REVIEW",
        "sourceRaw": str(SOURCE),
        "sourceRawSha256": sha256(SOURCE),
        "sourceRawInternalQc": "REJECTED_STATIC_POSE_TAIL_AFTER_4_SECONDS",
        "candidate": str(OUTPUT),
        "candidateSha256": sha256(OUTPUT),
        "width": 1280,
        "height": 720,
        "fps": 24,
        "frames": frames,
        "durationSeconds": duration,
        "freezeEventsAtLeast0_35Seconds": [],
        "contactSheet": str(CONTACT),
        "humanVisualReviewRequired": True,
    }
    atomic_json(MANIFEST, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
