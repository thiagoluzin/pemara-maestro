from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
QUEUE_PATH = PROJECT / "take_queue.json"
PRODUCTION_PATH = PROJECT / "production_manifest.json"
PROJECT_PATH = PROJECT / "project_manifest.json"
OUTPUT_DIR = PROJECT / "takes" / "maestro_generated"
QC_DIR = PROJECT / "qc" / "micro_assembly"
TZ = ZoneInfo("America/Sao_Paulo")
CONFIG = {
    "01": ("01A", "01B", "take_01_vejito_standard_microassembly_24fps_v1.mp4"),
    "05": ("05A", "05B", "take_05_vejito_standard_microassembly_24fps_v1.mp4"),
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    payload = json.loads(
        subprocess.run(
            [
                "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,nb_read_frames:format=duration",
                "-of", "json", str(path),
            ],
            check=True, capture_output=True, text=True,
        ).stdout
    )
    stream = payload["streams"][0]
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    top, bottom = str(stream["avg_frame_rate"]).split("/", 1)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": float(top) / float(bottom),
        "frames": frames,
        "duration_seconds": float(payload["format"]["duration"]),
    }


def take_video(take: dict) -> Path:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    for field in ("output_active", "output_preview", "output_review_candidate"):
        raw = str(video.get(field) or "").strip()
        if raw:
            candidate = Path(raw).resolve()
            if candidate.is_relative_to(PROJECT.resolve()) and candidate.is_file():
                return candidate
    raise FileNotFoundError(f"microtake {take.get('id')} sem video local")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Monta um take principal sem crossfade a partir de dois microtrechos aprovados tecnicamente."
    )
    parser.add_argument("take_id", choices=sorted(CONFIG))
    parser.add_argument("--a-head", type=int, default=0)
    parser.add_argument("--a-tail", type=int, default=0)
    parser.add_argument("--b-head", type=int, default=1)
    parser.add_argument("--b-tail", type=int, default=0)
    args = parser.parse_args()
    queue = read_json(QUEUE_PATH)
    production = read_json(PRODUCTION_PATH)
    project = read_json(PROJECT_PATH)
    by_id = {
        str(take.get("id")): take
        for take in queue.get("takes", [])
        if isinstance(take, dict)
    }
    a_id, b_id, filename = CONFIG[args.take_id]
    main_take = by_id[args.take_id]
    take_a = by_id[a_id]
    take_b = by_id[b_id]
    video_a = take_video(take_a)
    video_b = take_video(take_b)
    probe_a = probe(video_a)
    probe_b = probe(video_b)
    for label, info in ((a_id, probe_a), (b_id, probe_b)):
        if info["width"] != 1280 or info["height"] != 720 or abs(info["fps"] - 24.0) > 0.01:
            raise RuntimeError(f"{label} nao corresponde a 1280x720/24fps.")

    a_start = max(0, args.a_head)
    a_end = probe_a["frames"] - max(0, args.a_tail)
    b_start = max(0, args.b_head)
    b_end = probe_b["frames"] - max(0, args.b_tail)
    if a_end <= a_start or b_end <= b_start:
        raise RuntimeError("Trim removeu todos os quadros de um microtrecho.")
    useful_frames = (a_end - a_start) + (b_end - b_start)
    target_frames = 240
    pts_factor = target_frames / useful_frames
    filter_graph = (
        f"[0:v]trim=start_frame={a_start}:end_frame={a_end},setpts=PTS-STARTPTS[a];"
        f"[1:v]trim=start_frame={b_start}:end_frame={b_end},setpts=PTS-STARTPTS[b];"
        f"[a][b]concat=n=2:v=1:a=0,setpts={pts_factor:.12f}*PTS,"
        f"fps=24,trim=end_frame={target_frames},setpts=PTS-STARTPTS[v]"
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / filename
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video_a), "-i", str(video_b),
        "-filter_complex", filter_graph, "-map", "[v]", "-an",
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
        "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-frames:v", str(target_frames), str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr[-4000:])
    assembled = probe(output)
    if (
        assembled["width"] != 1280
        or assembled["height"] != 720
        or abs(assembled["fps"] - 24.0) > 0.01
        or assembled["frames"] != target_frames
        or abs(assembled["duration_seconds"] - 10.0) > 0.02
    ):
        raise RuntimeError(f"Saida montada fora do contrato: {assembled}")

    now = datetime.now(TZ).isoformat()
    video = main_take.setdefault("video", {})
    history = video.setdefault("output_history", [])
    if not isinstance(history, list):
        history = []
        video["output_history"] = history
    for field in ("output_active", "output_preview", "output_review_candidate"):
        previous = str(video.get(field) or "").strip()
        if previous and previous != str(output):
            history.append({
                "path": previous,
                "role": field,
                "replaced_at": now,
                "replaced_by_job_id": f"overnight-{args.take_id}-microassembly-v1",
            })
    video.update(
        {
            "status": "ready",
            "output_active": str(output),
            "output_preview": str(output),
            "output_review_candidate": str(output),
            "source_microsegments": [str(video_a), str(video_b)],
            "assembly_method": "hard_concat_adjacent_anchors_no_crossfade_retime_useful_motion",
            "crossfade_frames": 0,
            "freeze_frames_added": 0,
            "static_hold_frames_added": 0,
        }
    )
    main_take["maestro_status"] = "READY"
    main_take["maestro_last_job_id"] = f"overnight-{args.take_id}-microassembly-v1"
    main_take["maestro_last_error"] = ""
    main_take["maestro_updated_at"] = now
    main_take["status"] = "READY_PENDING_OWNER_REVIEW"
    main_take["render_authorized"] = True
    main_take["video_generation"]["render_authorized"] = True
    qc = main_take.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["auto_approved"] = False
    qc["microassembly"] = {
        "source_a": str(video_a),
        "source_b": str(video_b),
        "a_trim": {"head_frames": args.a_head, "tail_frames": args.a_tail},
        "b_trim": {"head_frames": args.b_head, "tail_frames": args.b_tail},
        "useful_source_frames": useful_frames,
        "retime_factor": pts_factor,
        "target_frames": target_frames,
        "target_duration_seconds": 10.0,
        "crossfade_frames": 0,
    }

    archive_payload = {
        "parent_take_id": args.take_id,
        "status": "PRESERVED_INTERNAL_SOURCES_NOT_OWNER_APPROVED",
        "assembled_candidate": str(output),
        "assembled_sha256": sha256(output),
        "microtakes": [copy.deepcopy(take_a), copy.deepcopy(take_b)],
        "created_at": now,
    }
    archive_path = QC_DIR / f"take_{args.take_id}_internal_microsegments_v1.json"
    write_json(archive_path, archive_payload)
    queue["takes"] = [
        take for take in queue["takes"]
        if str(take.get("id")) not in {a_id, b_id}
    ]
    queue["updated_at"] = now
    remaining_internal = [
        take for take in queue["takes"]
        if isinstance(take, dict) and take.get("internal_microsegment")
    ]
    queue["status"] = (
        "OVERNIGHT_GENERATION_AUTHORIZED"
        if remaining_internal
        else "ALL_TAKE_CANDIDATES_READY_PENDING_OWNER_REVIEW"
    )
    production["takes"] = copy.deepcopy(
        [
            take for take in queue["takes"]
            if isinstance(take, dict)
            and str(take.get("role") or "").lower() != "project_final_output"
        ]
    )
    production["updated_at"] = now
    production["status"] = queue["status"]
    project["updated_at"] = now
    project["status"] = queue["status"]
    project["maestro_status"] = "READY"
    write_json(QUEUE_PATH, queue)
    write_json(PRODUCTION_PATH, production)
    write_json(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "take_id": args.take_id,
        "output": str(output),
        "sha256": sha256(output),
        "technical": assembled,
        "auto_approved": False,
        "internal_archive": str(archive_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
