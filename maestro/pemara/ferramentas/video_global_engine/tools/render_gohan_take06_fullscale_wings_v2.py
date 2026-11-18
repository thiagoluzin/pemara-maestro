from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import requests


STUDIO = "http://127.0.0.1:8029"
COMFY = "http://127.0.0.1:8188"
PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
QUEUE = PROJECT / "take_queue.json"
WORK = PROJECT / "work" / "take06_fullscale_wings_v2"
OUTPUTS = WORK / "native_segments"
MANIFEST = WORK / "render_manifest.json"
COMFY_OUTPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output")
PAUSE_FLAG = Path(r"E:\Pemara\maestro\pemara\dados\flags\video_generation_paused.flag")
MODEL = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
FRAMES = 124
FPS = 24
DURATION = 5.166667


PROMPT_A = (
    "One uninterrupted photorealistic live-action 5.166667-second combat-launch segment between "
    "the exact supplied owner-approved H and G frames. Perfect Cell is a full-height adult heavyweight "
    "in every frame, with fixed anatomy, body proportions and scale relative to Gohan. His two black "
    "dorsal wings are already fully formed and clearly visible in the very first frame and remain "
    "physically attached, unchanged and present through the final frame; the wings never sprout, grow, "
    "appear, retract, merge, duplicate, disappear or morph. Cell is completely tailless throughout. "
    "SSJ2 Gohan continues the inherited close pressure, connects two distinct heavy impacts with visible "
    "recoil, then a decisive third blow launches the same full-size Cell through the stone breach. The "
    "camera physically arcs beside the first impact then accelerates into a deep chase; near rocks cross "
    "the lens faster than the fighters and distant walls. Continuous fast action from first to last "
    "frame. No miniature Cell, scale drift, new anatomy, tail, wing birth, animation, anime, cel shading, "
    "game render, plastic CGI, extra character, duplicated body, extra limb, repeated loop, slow motion, "
    "turn-taking, pose hold, freeze, internal cut or static ending."
)

PROMPT_B = (
    "One uninterrupted photorealistic live-action 5.166667-second pursuit-and-finish segment between "
    "the exact supplied owner-approved G and I frames. Perfect Cell remains the same full-height adult "
    "heavyweight with fixed anatomy and proportions; any apparent reduction is caused only by real "
    "perspective as he crosses deep physical distance toward the mountain, never by body-scale change. "
    "Both black dorsal wings already exist in frame one, stay attached and unchanged throughout, and "
    "remain part of his silhouette even at long distance; they never sprout, grow, appear, retract, "
    "merge, duplicate, disappear or morph. Cell is completely tailless in every frame. He inherits the "
    "high-speed flight through the breach. SSJ2 Gohan catches the same vector, lands one final "
    "redirecting impact without pausing, gathers blue-white energy while still moving and immediately "
    "fires a massive Kamehameha that drives that same adult Cell into the mountain. The rock face ruptures "
    "while beam light, debris, dust, aura and the pursuing camera remain active through the final frame. "
    "No miniature Cell, physical shrink, scale drift, new anatomy, tail, wing birth, beam through Gohan, "
    "long charge pose, animation, anime, cel shading, game render, plastic CGI, duplicate Cell, slow "
    "motion, freeze, internal cut, static explosion or gore."
)


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(anchor: dict, label: str) -> dict:
    path = Path(str(anchor.get("file") or ""))
    expected = str(anchor.get("sha256") or "").lower()
    if str(anchor.get("status") or "") != "approved_for_video":
        raise RuntimeError(f"Anchor {label} is not approved_for_video.")
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    if expected and expected != actual:
        raise RuntimeError(f"Anchor {label} hash drift: {actual} != {expected}")
    return {"label": label, "file": str(path), "sha256": actual, "status": "approved_for_video"}


def anchors_from_queue() -> dict[str, dict]:
    queue = load(QUEUE)
    take = next(item for item in queue.get("takes", []) if str(item.get("id") or "") == "06")
    if str(take.get("status") or "") != "USER_REJECTED_CORRECTED_CANDIDATE_REQUIRED":
        raise RuntimeError("Take 06 is not in the owner-rejected replacement state.")
    if str(take.get("maestro_status") or "") != "DIRECTOR_REVIEW":
        raise RuntimeError("Take 06 is not isolated from the ready/approved catalog state.")
    h = file_record(take["base_image"], "H")
    i = file_record(take["end_image"], "I")
    internal = next(
        item for item in take.get("internal_anchors", [])
        if isinstance(item, dict) and str(item.get("label") or "") == "G"
    )
    g = file_record(internal, "G")
    return {"H": h, "G": g, "I": i}


def ensure_idle() -> None:
    if PAUSE_FLAG.exists():
        raise RuntimeError(f"Video generation pause flag is active: {PAUSE_FLAG}")
    status = requests.get(f"{STUDIO}/api/generative/status", timeout=20)
    status.raise_for_status()
    payload = status.json()
    if not payload.get("online", True):
        raise RuntimeError(f"Maestro generative service is offline: {payload}")
    queue = requests.get(f"{COMFY}/queue", timeout=20)
    queue.raise_for_status()
    state = queue.json()
    if state.get("queue_running") or state.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle; refusing to mix GPU work.")


def submit(segment: dict) -> str:
    data = {
        "prompt": segment["prompt"],
        "mode": "video",
        "model": MODEL,
        "width": "1280",
        "height": "720",
        "steps": "20",
        "guidance": "1.0",
        "seed": str(segment["seed"]),
        "frames": str(FRAMES),
        "fps": str(FPS),
        "duration": str(DURATION),
        "video_duration": str(DURATION),
        "video_conditioning_profile": "identity_locked",
        "enable_minimax_h3_native_audio": "false",
        "enable_minimax_h3_live_preview": "false",
    }
    start = Path(segment["start_anchor"]["file"])
    end = Path(segment["end_anchor"]["file"])
    with start.open("rb") as start_handle, end.open("rb") as end_handle:
        files = {
            "base_image": (start.name, start_handle, "image/png"),
            "end_image": (end.name, end_handle, "image/png"),
        }
        response = requests.post(f"{STUDIO}/api/generative/job", data=data, files=files, timeout=90)
    response.raise_for_status()
    job_id = str(response.json().get("job_id") or "")
    if not job_id:
        raise RuntimeError(f"Maestro returned no job id: {response.text[:500]}")
    return job_id


def wait_job(segment_id: str, job_id: str, timeout_seconds: int = 2400) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_report = 0.0
    while time.monotonic() < deadline:
        response = requests.get(f"{STUDIO}/api/generative/job/{job_id}", timeout=30)
        response.raise_for_status()
        job = response.json()
        status = str(job.get("status") or "")
        now = time.monotonic()
        if now - last_report >= 25:
            print(
                f"STATUS {segment_id} job={job_id[:8]} state={status} "
                f"progress={job.get('progress')} message={job.get('message')}",
                flush=True,
            )
            last_report = now
        if status == "done":
            return job
        if status in {"error", "cancelled"}:
            raise RuntimeError(f"{segment_id} ended as {status}: {job.get('error')}")
        time.sleep(8)
    raise TimeoutError(f"Timed out waiting for {segment_id} job {job_id}")


def materialize(segment_id: str, job: dict) -> Path:
    outputs = (job.get("result") or {}).get("outputs") or []
    video = next((item for item in outputs if item.get("kind") == "video"), None)
    if not video:
        raise RuntimeError(f"No video output in {segment_id} result.")
    source = COMFY_OUTPUT / Path(str(video.get("subfolder") or "")) / str(video.get("filename") or "")
    if not source.is_file():
        raise FileNotFoundError(source)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    target = OUTPUTS / f"{segment_id}_{str(job.get('job_id') or '')[:16]}_minimax_h3.mp4"
    shutil.copy2(source, target)
    return target


def probe_video(path: Path) -> dict:
    import subprocess

    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_read_frames,pix_fmt",
            "-show_entries", "format=duration,size", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    data = json.loads(completed.stdout)
    stream = data["streams"][0]
    result = {
        "codec": stream.get("codec_name"),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": stream.get("avg_frame_rate"),
        "frames": int(stream.get("nb_read_frames") or 0),
        "pix_fmt": stream.get("pix_fmt"),
        "duration_seconds": float(data["format"].get("duration") or 0),
        "size_bytes": int(data["format"].get("size") or 0),
    }
    if (result["width"], result["height"], result["frames"]) != (1280, 720, FRAMES):
        raise RuntimeError(f"Unexpected technical result for {path.name}: {result}")
    if result["fps"] != "24/1":
        raise RuntimeError(f"Unexpected fps for {path.name}: {result['fps']}")
    return result


def main() -> int:
    ensure_idle()
    anchors = anchors_from_queue()
    manifest = {
        "schema_version": "1.0",
        "project_id": PROJECT.name,
        "take_id": "06",
        "route": "VEJITO_STANDARD_H3_MULTI_ANCHOR_H_G_I_FULLSCALE_WINGS_LOCK_V2",
        "status": "RENDERING_INTERNAL_SEGMENTS",
        "created_at": now_local(),
        "auto_approval": False,
        "visible_in_maestro": False,
        "anchors": anchors,
        "segments": [
            {
                "id": "06A2",
                "start_anchor": anchors["H"],
                "end_anchor": anchors["G"],
                "seed": 20260821061,
                "prompt": PROMPT_A,
                "status": "pending",
            },
            {
                "id": "06B2",
                "start_anchor": anchors["G"],
                "end_anchor": anchors["I"],
                "seed": 20260821062,
                "prompt": PROMPT_B,
                "status": "pending",
            },
        ],
        "next_gate": "INTERNAL_ART_CINEMATIC_MOTION_QC",
    }
    if MANIFEST.is_file():
        existing = load(MANIFEST)
        if str(existing.get("route") or "") == manifest["route"]:
            manifest = existing
    atomic_save(MANIFEST, manifest)

    for segment in manifest["segments"]:
        segment_id = str(segment["id"])
        existing_output = Path(str(segment.get("output") or ""))
        if segment.get("status") == "generated_pending_internal_qc" and existing_output.is_file():
            print(f"SKIP {segment_id}: existing verified native segment", flush=True)
            continue
        ensure_idle()
        print(
            f"START {segment_id} {segment['start_anchor']['label']}->{segment['end_anchor']['label']} "
            f"seed={segment['seed']}",
            flush=True,
        )
        job_id = submit(segment)
        segment.update({"status": "running", "job_id": job_id, "started_at": now_local()})
        atomic_save(MANIFEST, manifest)
        job = wait_job(segment_id, job_id)
        job["job_id"] = job_id
        output = materialize(segment_id, job)
        segment.update(
            {
                "status": "generated_pending_internal_qc",
                "completed_at": now_local(),
                "prompt_id": job.get("prompt_id"),
                "output": str(output),
                "sha256": sha256(output),
                "technical": probe_video(output),
            }
        )
        atomic_save(MANIFEST, manifest)
        print(f"DONE {segment_id} output={output.name} sha256={segment['sha256']}", flush=True)

    manifest["status"] = "INTERNAL_SEGMENTS_GENERATED_PENDING_QC"
    manifest["completed_at"] = now_local()
    atomic_save(MANIFEST, manifest)
    print(
        json.dumps(
            {
                "ok": True,
                "take_id": "06",
                "status": manifest["status"],
                "segments": [
                    {key: item.get(key) for key in ("id", "job_id", "output", "sha256", "technical")}
                    for item in manifest["segments"]
                ],
                "auto_approval": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
