"""Render the internal Android 16 speech bridge from approved anchor A to B.

This is a visual-only MiniMax H3 FL2VA render.  It deliberately stays hidden
from the Maestro take catalog and never changes an owner-approval field.  The
approved Version E audio is added later by the lip-sync/assembly stage.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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
PRODUCTION = PROJECT / "production_manifest.json"
WORK = PROJECT / "work" / "android16_speech_fullfilm_v1"
OUTPUTS = WORK / "native_segments"
MANIFEST = WORK / "speech_render_manifest.json"
COMFY_OUTPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output")
PAUSE_FLAG = Path(r"E:\Pemara\maestro\pemara\dados\flags\video_generation_paused.flag")
MODEL = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
FRAMES = 158  # MiniMax H3 temporal grid 17k+5; 6.583333 s at 24 fps.
FPS = 24
DURATION = FRAMES / FPS
SEED = 20260821161
ROUTE = "VEJITO_STANDARD_ANDROID16_SPEECH_A_B_158F_V1"


PROMPT = (
    "One uninterrupted photorealistic live-action 6.583333-second dramatic speech bridge between "
    "the exact supplied owner-approved A and B frames in the destroyed Cell Games arena. Preserve "
    "the exact production design, silhouettes, scale, storm daylight, colors and physical materials "
    "of both supplied frames. Android 16 is ONLY the detached mechanical head in the extreme "
    "foreground: pale ceramic-and-metal face, red synthetic hair, visible steel mechanisms, green "
    "armor collar only; his face and skin must never turn green. Keep his face large, readable and "
    "nearly three-quarter to camera for the full speech. His lips and mechanical jaw articulate "
    "subtly and naturally from 00:00.133 through 00:05.424, close during the natural pause from "
    "00:02.502 to 00:03.319, then close completely after 00:05.424 and remain closed. No theatrical "
    "over-enunciation, no broad grimaces and no tear. During the same interval the camera performs "
    "a continuous low physical dolly-arc of modest distance, with clear parallax in nearby gravel, "
    "Android 16's head, Perfect Cell, Gohan and distant ridges; wind moves dust, Gohan's clothing and "
    "Cell's two rigid dorsal wing plates independently. Perfect Cell remains a tall adult bio-armored "
    "creature with fixed proportions, two black dorsal wings present throughout and a clean, "
    "completely tailless pelvis. Cell keeps both feet on the ground through the first eighty-four "
    "percent while shifting weight and watching Gohan; he must not step on, touch or deform the head. "
    "Only after Android 16's lips have closed, in the final sixteen percent, Cell lifts the same "
    "correctly formed boot in one continuous threatening motion above the intact mechanical head, "
    "arriving at exact approved frame B with downward motion only beginning. Gohan remains a teenage "
    "Super Saiyan in a torn dark-purple gi, reacts with restrained grief and alarm and advances a half "
    "step without transforming yet. Useful physical movement fills every frame and the exit remains "
    "active. No crush, foot contact, green Android 16 face, blood, flesh, gore, tail, stinger, cable, "
    "third rear appendage, duplicate character, extra limb, scale drift, anime, cel shading, game "
    "render, plastic CGI, soap-opera acting, internal cut, crossfade, zoom-only move, slow motion, "
    "freeze, held pose, static ending, subtitle, text, logo or watermark."
)


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid JSON root: {path}")
    return value


def atomic_save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def approved_anchor(label: str) -> dict:
    manifest = load(PRODUCTION)
    record = manifest.get("anchors", {}).get(label)
    if not isinstance(record, dict) or record.get("status") != "approved_for_video":
        raise RuntimeError(f"Anchor {label} is not approved_for_video")
    path = Path(str(record.get("file") or "")).resolve(strict=True)
    expected = str(record.get("sha256") or "").lower()
    actual = sha256(path)
    if expected and actual != expected:
        raise RuntimeError(f"Anchor {label} hash drift: {actual} != {expected}")
    return {"label": label, "file": str(path), "sha256": actual, "status": record["status"]}


def ensure_idle() -> None:
    if PAUSE_FLAG.exists():
        raise RuntimeError(f"Video generation pause flag is active: {PAUSE_FLAG}")
    studio = requests.get(f"{STUDIO}/api/generative/status", timeout=20)
    studio.raise_for_status()
    if not studio.json().get("online", True):
        raise RuntimeError(f"Maestro generative service is offline: {studio.json()}")
    response = requests.get(f"{COMFY}/queue", timeout=20)
    response.raise_for_status()
    state = response.json()
    if state.get("queue_running") or state.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle; refusing to mix GPU work")
    stats = requests.get(f"{COMFY}/system_stats", timeout=20)
    stats.raise_for_status()
    devices = stats.json().get("devices") or []
    free = int(devices[0].get("vram_free") or 0) if devices else 0
    if free < 24 * 1024**3:
        raise RuntimeError(f"MiniMax H3 requires 24 GiB free; available={free / 1024**3:.2f} GiB")


def probe(path: Path) -> dict:
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
    payload = json.loads(completed.stdout)
    stream = payload["streams"][0]
    result = {
        "codec": stream.get("codec_name"),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": stream.get("avg_frame_rate"),
        "frames": int(stream.get("nb_read_frames") or 0),
        "pix_fmt": stream.get("pix_fmt"),
        "duration_seconds": float(payload["format"].get("duration") or 0),
        "size_bytes": int(payload["format"].get("size") or 0),
    }
    if (result["width"], result["height"], result["frames"]) != (1280, 720, FRAMES):
        raise RuntimeError(f"Unexpected technical result: {result}")
    if result["fps"] != "24/1" or abs(result["duration_seconds"] - DURATION) > 0.01:
        raise RuntimeError(f"Unexpected timing result: {result}")
    return result


def submit(start: dict, end: dict) -> str:
    data = {
        "prompt": PROMPT,
        "mode": "video",
        "model": MODEL,
        "width": "1280",
        "height": "720",
        "steps": "20",
        "guidance": "1.0",
        "seed": str(SEED),
        "frames": str(FRAMES),
        "fps": str(FPS),
        "duration": f"{DURATION:.6f}",
        "video_duration": f"{DURATION:.6f}",
        "video_conditioning_profile": "identity_locked",
        "enable_minimax_h3_native_audio": "false",
        "enable_minimax_h3_live_preview": "false",
    }
    start_path = Path(start["file"])
    end_path = Path(end["file"])
    with start_path.open("rb") as first, end_path.open("rb") as last:
        response = requests.post(
            f"{STUDIO}/api/generative/job",
            data=data,
            files={
                "base_image": (start_path.name, first, "image/png"),
                "end_image": (end_path.name, last, "image/png"),
            },
            timeout=90,
        )
    response.raise_for_status()
    job_id = str(response.json().get("job_id") or "")
    if not job_id:
        raise RuntimeError(f"Maestro returned no job id: {response.text[:500]}")
    return job_id


def wait_job(job_id: str, timeout_seconds: int = 2700) -> dict:
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
                f"STATUS job={job_id[:8]} state={status} progress={job.get('progress')} "
                f"message={job.get('message')}",
                flush=True,
            )
            last_report = now
        if status == "done":
            return job
        if status in {"error", "cancelled"}:
            raise RuntimeError(f"Job ended as {status}: {job.get('error')}")
        time.sleep(8)
    raise TimeoutError(f"Timed out waiting for job {job_id}")


def materialize(job_id: str, job: dict) -> Path:
    outputs = (job.get("result") or {}).get("outputs") or []
    video = next((item for item in outputs if item.get("kind") == "video"), None)
    if not video:
        raise RuntimeError("No video output in result")
    source = COMFY_OUTPUT / Path(str(video.get("subfolder") or "")) / str(video.get("filename") or "")
    if not source.is_file():
        raise FileNotFoundError(source)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    target = OUTPUTS / f"android16_speech_A_B_{job_id[:16]}_minimax_h3_158f.mp4"
    shutil.copy2(source, target)
    return target


def main() -> int:
    start = approved_anchor("A")
    end = approved_anchor("B")
    if MANIFEST.is_file():
        existing = load(MANIFEST)
        output = Path(str(existing.get("output") or ""))
        if existing.get("route") == ROUTE and existing.get("status") == "GENERATED_PENDING_INTERNAL_QC" and output.is_file():
            info = probe(output)
            print(json.dumps({"ok": True, "reused": True, "output": str(output), "technical": info}, indent=2))
            return 0
    ensure_idle()
    manifest = {
        "schema_version": "1.0",
        "project_id": PROJECT.name,
        "scope": "INTERNAL_SPEECH_BRIDGE_NOT_VISIBLE_IN_MAESTRO",
        "route": ROUTE,
        "status": "SUBMITTING",
        "created_at": now_local(),
        "auto_approval": False,
        "owner_approval": "PENDING_FULL_FILM_PLAYBACK",
        "start_anchor": start,
        "end_anchor": end,
        "engine": MODEL,
        "frames": FRAMES,
        "fps": FPS,
        "duration_seconds": DURATION,
        "seed": SEED,
        "prompt": PROMPT,
        "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
    }
    atomic_save(MANIFEST, manifest)
    job_id = submit(start, end)
    manifest.update({"status": "RUNNING", "job_id": job_id, "started_at": now_local()})
    atomic_save(MANIFEST, manifest)
    job = wait_job(job_id)
    output = materialize(job_id, job)
    technical = probe(output)
    manifest.update(
        {
            "status": "GENERATED_PENDING_INTERNAL_QC",
            "completed_at": now_local(),
            "prompt_id": job.get("prompt_id"),
            "output": str(output),
            "sha256": sha256(output),
            "technical": technical,
        }
    )
    atomic_save(MANIFEST, manifest)
    print(json.dumps({"ok": True, "reused": False, "output": str(output), "technical": technical}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
