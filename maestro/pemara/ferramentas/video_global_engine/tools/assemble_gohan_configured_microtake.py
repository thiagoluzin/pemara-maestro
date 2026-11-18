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
CONFIG = {
    "01": ("01A", "01B"),
    "02": ("02A",),
    "04": ("04A2", "04B"),
    "05": ("05A", "05B", "05C", "05D"),
    "06": ("06A", "06B"),
}
TZ = ZoneInfo("America/Sao_Paulo")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,nb_read_frames:format=duration",
            "-of", "json", str(path),
        ], check=True, capture_output=True, text=True,
    ).stdout
    payload = json.loads(raw)
    stream = payload["streams"][0]
    numerator, denominator = str(stream["avg_frame_rate"]).split("/", 1)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": float(numerator) / float(denominator),
        "frames": int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0),
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


def parse_trims(raw: str, count: int) -> list[tuple[int, int]]:
    chunks = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
    if len(chunks) != count:
        raise ValueError(f"--trims exige {count} pares head:tail.")
    result: list[tuple[int, int]] = []
    for chunk in chunks:
        head_raw, tail_raw = chunk.split(":", 1)
        head, tail = int(head_raw), int(tail_raw)
        if head < 0 or tail < 0:
            raise ValueError("Trims nao podem ser negativos.")
        result.append((head, tail))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("take_id", choices=sorted(CONFIG))
    parser.add_argument("--trims", required=True)
    parser.add_argument("--target-duration", required=True, type=float)
    args = parser.parse_args()
    if args.target_duration <= 0 or args.target_duration > 15:
        raise ValueError("Duracao-alvo precisa ficar entre 0 e 15 segundos.")
    micro_ids = CONFIG[args.take_id]
    trims = parse_trims(args.trims, len(micro_ids))
    queue = read_json(QUEUE_PATH)
    production = read_json(PRODUCTION_PATH)
    project = read_json(PROJECT_PATH)
    by_id = {
        str(take.get("id")): take
        for take in queue.get("takes", [])
        if isinstance(take, dict)
    }
    main_take = by_id[args.take_id]
    micros = [by_id[micro_id] for micro_id in micro_ids]
    videos = [take_video(take) for take in micros]
    probes = [probe(path) for path in videos]
    useful: list[tuple[int, int]] = []
    for take_id, info, (head, tail) in zip(micro_ids, probes, trims):
        if info["width"] != 1280 or info["height"] != 720 or abs(info["fps"] - 24.0) > 0.01:
            raise RuntimeError(f"{take_id} nao corresponde a 1280x720/24fps.")
        end = info["frames"] - tail
        if end <= head:
            raise RuntimeError(f"Trim invalido em {take_id}.")
        useful.append((head, end))
    source_frames = sum(end - start for start, end in useful)
    target_frames = round(args.target_duration * 24)
    target_duration = target_frames / 24.0
    pts_factor = target_frames / source_frames
    filters: list[str] = []
    for index, (start, end) in enumerate(useful):
        filters.append(
            f"[{index}:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[v{index}]"
        )
    if len(videos) == 1:
        filters.append(
            f"[v0]setpts={pts_factor:.12f}*PTS,fps=24,trim=end_frame={target_frames},"
            "setpts=PTS-STARTPTS[outv]"
        )
    else:
        inputs = "".join(f"[v{index}]" for index in range(len(videos)))
        filters.append(
            f"{inputs}concat=n={len(videos)}:v=1:a=0,setpts={pts_factor:.12f}*PTS,"
            f"fps=24,trim=end_frame={target_frames},setpts=PTS-STARTPTS[outv]"
        )
    filter_graph = ";".join(filters)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    duration_tag = str(target_duration).replace(".", "p")
    output = OUTPUT_DIR / f"take_{args.take_id}_vejito_standard_{duration_tag}s_24fps_v1.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for video in videos:
        command += ["-i", str(video)]
    command += [
        "-filter_complex", filter_graph, "-map", "[outv]", "-an",
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
        "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-frames:v", str(target_frames), str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr[-4000:])
    assembled = probe(output)
    if (
        assembled["width"] != 1280 or assembled["height"] != 720
        or abs(assembled["fps"] - 24.0) > 0.01
        or assembled["frames"] != target_frames
        or abs(assembled["duration_seconds"] - target_duration) > 0.02
    ):
        raise RuntimeError(f"Saida fora do contrato: {assembled}")

    now = datetime.now(TZ).isoformat()
    video_record = main_take.setdefault("video", {})
    history = video_record.setdefault("output_history", [])
    if not isinstance(history, list):
        history = []
        video_record["output_history"] = history
    for field in ("output_active", "output_preview", "output_review_candidate"):
        previous = str(video_record.get(field) or "").strip()
        if previous and previous != str(output):
            history.append({
                "path": previous,
                "role": field,
                "replaced_at": now,
                "replaced_by_job_id": f"overnight-{args.take_id}-microassembly-v1",
            })
    video_record.update(
        {
            "status": "ready",
            "output_active": str(output),
            "output_preview": str(output),
            "output_review_candidate": str(output),
            "source_microsegments": [str(path) for path in videos],
            "assembly_method": "adjacent_approved_anchor_segments_hard_concat_no_crossfade",
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
    main_take["target_duration_seconds"] = target_duration
    qc = main_take.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["auto_approved"] = False
    qc["microassembly"] = {
        "sources": [str(path) for path in videos],
        "trims": [
            {"take_id": take_id, "head_frames": head, "tail_frames": tail}
            for take_id, (head, tail) in zip(micro_ids, trims)
        ],
        "source_frames_after_trim": source_frames,
        "retime_factor": pts_factor,
        "target_frames": target_frames,
        "target_duration_seconds": target_duration,
        "crossfade_frames": 0,
    }
    archive = {
        "parent_take_id": args.take_id,
        "status": "PRESERVED_INTERNAL_SOURCES_NOT_OWNER_APPROVED",
        "assembled_candidate": str(output),
        "assembled_sha256": sha256(output),
        "microtakes": [copy.deepcopy(take) for take in micros],
        "created_at": now,
    }
    archive_path = QC_DIR / f"take_{args.take_id}_internal_microsegments_v1.json"
    write_json(archive_path, archive)
    queue["takes"] = [
        take for take in queue["takes"]
        if str(take.get("id")) not in set(micro_ids)
    ]
    queue["updated_at"] = now
    remaining = [
        take for take in queue["takes"]
        if isinstance(take, dict) and take.get("internal_microsegment")
    ]
    queue["status"] = (
        "OVERNIGHT_GENERATION_AUTHORIZED"
        if remaining else "ALL_TAKE_CANDIDATES_READY_PENDING_OWNER_REVIEW"
    )
    production["takes"] = copy.deepcopy(
        [take for take in queue["takes"] if not take.get("internal_microsegment")]
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
        "retime_factor": pts_factor,
        "auto_approved": False,
        "internal_archive": str(archive_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
