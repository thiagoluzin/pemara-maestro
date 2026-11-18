"""Render the remaining V6 action connectors serially through the local Maestro H3 API."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8029"
COMFY = "http://127.0.0.1:8188"
PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
WORK = PROJECT / "work" / "continuous_rebuild_v6"
MANIFEST = WORK / "production_manifest_continuous_v6.json"
COMFY_OUTPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output")
PAUSE_FLAG = Path(r"E:\Pemara\maestro\pemara\dados\flags\video_generation_paused.flag")
PILOT_ID = "C01_P02"


def read_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8-sig"))


def atomic_manifest(payload: dict) -> None:
    temp = MANIFEST.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(MANIFEST)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_idle() -> None:
    if PAUSE_FLAG.exists():
        raise RuntimeError("Video generation pause flag is active.")
    queue = requests.get(f"{COMFY}/queue", timeout=15).json()
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle.")


def submit(take: dict, seed: int) -> str:
    generation = take["video_generation"]
    data = {
        "prompt": take["animation_prompt"], "mode": "video",
        "model": generation["model"], "width": "1280", "height": "720",
        "steps": "20", "guidance": "1.0", "seed": str(seed), "frames": "124",
        "fps": "24", "duration": "5.166667", "video_duration": "5.166667",
        "video_conditioning_profile": "identity_locked",
        "enable_minimax_h3_native_audio": "false",
        "enable_minimax_h3_live_preview": "false",
    }
    with Path(take["base_image"]["file"]).open("rb") as start, Path(take["end_image"]["file"]).open("rb") as end:
        files = {
            "base_image": (Path(start.name).name, start, "image/png"),
            "end_image": (Path(end.name).name, end, "image/png"),
        }
        response = requests.post(f"{BASE}/api/generative/job", data=data, files=files, timeout=60)
    response.raise_for_status()
    job_id = str(response.json().get("job_id") or "")
    if not job_id:
        raise RuntimeError(f"Maestro returned no job ID: {response.text}")
    return job_id


def wait_job(take_id: str, job_id: str) -> dict:
    last_report = 0.0
    while True:
        job = requests.get(f"{BASE}/api/generative/job/{job_id}", timeout=20).json()
        status = str(job.get("status") or "")
        now = time.time()
        if now - last_report >= 30:
            print(f"STATUS {take_id} job={job_id[:8]} state={status} progress={job.get('progress')} message={job.get('message')}", flush=True)
            last_report = now
        if status == "done":
            return job
        if status in {"error", "cancelled"}:
            raise RuntimeError(f"{take_id} job {job_id} ended as {status}: {job.get('error')}")
        time.sleep(10)


def materialize(take_id: str, job: dict) -> Path:
    outputs = (job.get("result") or {}).get("outputs") or []
    video = next((item for item in outputs if item.get("kind") == "video"), None)
    if not video:
        raise RuntimeError(f"No video output for {take_id}.")
    relative = Path(str(video.get("subfolder") or "")) / str(video.get("filename") or "")
    source = COMFY_OUTPUT / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    target = WORK / "connectors" / f"{take_id}.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def main() -> None:
    ensure_idle()
    manifest = read_manifest()
    for index, take in enumerate(manifest["takes"], start=1):
        take_id = str(take["id"])
        target = WORK / "connectors" / f"{take_id}.mp4"
        if take_id == PILOT_ID and target.is_file():
            take["generation_result"] = {
                "status": "generated_pending_visual_qc", "job_id": "656640fe2a6c47fa9f05cd7cc03b3d0b",
                "seed": 2026082101, "file": str(target), "sha256": sha256(target),
            }
            atomic_manifest(manifest)
            print(f"SKIP {take_id}: pilot already materialized", flush=True)
            continue
        if target.is_file():
            print(f"SKIP {take_id}: output already exists", flush=True)
            continue
        ensure_idle()
        seed = 2026082100 + index
        print(f"START {take_id} seed={seed}", flush=True)
        job_id = submit(take, seed)
        take["generation_result"] = {"status": "running", "job_id": job_id, "seed": seed}
        atomic_manifest(manifest)
        job = wait_job(take_id, job_id)
        output = materialize(take_id, job)
        take["generation_result"] = {
            "status": "generated_pending_visual_qc", "job_id": job_id, "seed": seed,
            "prompt_id": job.get("prompt_id"), "file": str(output), "sha256": sha256(output),
            "width": 1280, "height": 720, "fps": 24, "frames": 124, "duration_seconds": 5.166667,
        }
        atomic_manifest(manifest)
        print(f"DONE {take_id} file={output.name} sha256={take['generation_result']['sha256']}", flush=True)
    manifest["status"] = "ALL_CONNECTORS_GENERATED_PENDING_VISUAL_QC"
    manifest["render_authorized"] = False
    atomic_manifest(manifest)
    print("ALL_CONNECTORS_GENERATED", flush=True)


if __name__ == "__main__":
    main()
