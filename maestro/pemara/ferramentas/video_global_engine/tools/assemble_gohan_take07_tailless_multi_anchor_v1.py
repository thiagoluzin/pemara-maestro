from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
CHILD = ENGINE / "projetos" / "gohan_ssj2_take07_tailless_multi_anchor_v1"
PARENT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")

CLIPS = (
    ("07A", "take_07A_902134a800f14b32_minimax_h3_preview.mp4", 4.458333),
    ("07B", "take_07B_11182cf7deec4d35_minimax_h3_preview.mp4", 4.625000),
    ("07C", "take_07C_aa5f119434ab43c0_minimax_h3_preview.mp4", 4.625000),
)
FRAMES_PER_SEGMENT = 80
FPS = 24


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
    if not FFMPEG.is_file() or not FFPROBE.is_file():
        raise FileNotFoundError("Runtime FFmpeg do Maestro nao encontrado.")

    queue = json.loads((CHILD / "take_queue.json").read_text(encoding="utf-8-sig"))
    by_id = {str(item.get("id")): item for item in queue.get("takes", []) if isinstance(item, dict)}
    sources = []
    evidence = []
    for take_id, filename, motion_end in CLIPS:
        take = by_id.get(take_id)
        if not take or str(take.get("maestro_status") or "").upper() not in {"READY", "APPROVED"}:
            raise ValueError(f"{take_id} nao passou pelo QC interno.")
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
        evidence.append(
            {
                "takeId": take_id,
                "source": str(source),
                "sha256": sha256(source),
                "motionEndSeconds": motion_end,
                "editorialFrames": FRAMES_PER_SEGMENT,
            }
        )

    filters = []
    labels = []
    editorial_seconds = FRAMES_PER_SEGMENT / FPS
    for index, (_, _, motion_end) in enumerate(CLIPS):
        multiplier = editorial_seconds / motion_end
        filters.append(
            f"[{index}:v]trim=start=0:end={motion_end:.6f},"
            f"setpts={multiplier:.12f}*(PTS-STARTPTS),fps={FPS},"
            f"trim=end_frame={FRAMES_PER_SEGMENT},setpts=N/({FPS}*TB)[s{index}]"
        )
        labels.append(f"[s{index}]")
    filters.append("".join(labels) + f"concat=n={len(CLIPS)}:v=1:a=0[vout]")

    edit_dir = CHILD / "edit"
    edit_dir.mkdir(parents=True, exist_ok=True)
    candidate = edit_dir / "take07_tailless_multi_anchor_motion_v2.mp4"
    command = [str(FFMPEG), "-y"]
    for source in sources:
        command.extend(["-i", str(source)])
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
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
            str(candidate),
        ]
    )
    subprocess.run(command, check=True)

    info = probe(candidate)
    stream = info["streams"][0]
    frames = int(stream.get("nb_read_frames") or 0)
    duration = float(info["format"]["duration"])
    if frames != 240 or abs(duration - 10.0) > 0.01:
        raise ValueError(f"Montagem invalida: frames={frames}, duration={duration}")

    destination = PARENT / "takes" / "maestro_generated" / "take_07_multi_anchor_tailless_motion_v2.mp4"
    shutil.copy2(candidate, destination)
    if sha256(candidate) != sha256(destination):
        raise ValueError("Hash divergiu na copia para o projeto principal.")

    parent_queue_path = PARENT / "take_queue.json"
    parent_queue = json.loads(parent_queue_path.read_text(encoding="utf-8-sig"))
    take = next(item for item in parent_queue["takes"] if str(item.get("id")) == "07")
    now = datetime.now(timezone.utc).isoformat()
    video = take.setdefault("video", {})
    previous = str(video.get("output_active") or "")
    if previous and previous != str(destination):
        video.setdefault("output_history", []).append(
            {"path": previous, "role": "output_active", "replaced_at": now, "replaced_by": "tailless_multi_anchor_motion_v2"}
        )
    video.update(
        {
            "status": "ready",
            "output_active": str(destination),
            "output_preview": str(destination),
            "output_review_candidate": str(destination),
        }
    )
    take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take["maestro_status"] = "READY"
    take["render_authorized"] = False
    take["maestro_last_job_id"] = "take07_tailless_multi_anchor_motion_v2"
    take["maestro_last_error"] = ""
    take["maestro_updated_at"] = now
    take["maestro_notes"] = (
        "Take 07 V2 montado com 07A, 07B e 07C condicionados por quatro ancoras sem cauda aprovadas. "
        "Somente movimento util foi usado; tres blocos de 80 quadros, cortes secos nas ancoras, sem crossfade ou hold. "
        "Brutos 07 e 07R1 permanecem preservados. Candidato pendente de revisao visual humana."
    )
    qc = take.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["human_visual_approval"] = "pending"
    qc["transition_motion_gate"] = {
        "status": "pending_human_review",
        "method": "three_tailless_microtakes_hard_cut_on_motion",
        "frames": frames,
        "duration_seconds": duration,
        "crossfade_frames": 0,
        "freeze_frames": 0,
    }
    for request in take.get("maestro_director_requests", []):
        if isinstance(request, dict) and str(request.get("status") or "").upper() == "PENDING":
            request["status"] = "CANCELLED"
            request["updated_at"] = now
    atomic_json(parent_queue_path, parent_queue)

    manifest = {
        "schemaVersion": "gohan_take07_tailless_multi_anchor_motion_v2",
        "createdAt": now,
        "candidate": str(candidate),
        "candidateSha256": sha256(candidate),
        "registeredParentCandidate": str(destination),
        "frames": frames,
        "fps": FPS,
        "durationSeconds": duration,
        "audio": "visual_only",
        "transition": "hard_cuts_on_approved_moving_anchors_no_crossfade",
        "sources": evidence,
        "humanVisualReviewRequired": True,
    }
    atomic_json(edit_dir / "take07_tailless_multi_anchor_motion_v2.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
