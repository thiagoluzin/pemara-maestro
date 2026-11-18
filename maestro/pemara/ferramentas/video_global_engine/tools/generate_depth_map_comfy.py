#!/usr/bin/env python3
"""Generate a reproducible relative depth control map with local ComfyUI."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import shutil
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image


COMFY_URL = "http://127.0.0.1:8188"
COMFY_INPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\input")
COMFY_OUTPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output")


def api_get(route: str) -> dict:
    with urllib.request.urlopen(f"{COMFY_URL}{route}", timeout=30) as response:
        return json.load(response)


def api_post(route: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{COMFY_URL}{route}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
    return json.loads(body) if body else {}


def release_comfy_memory() -> None:
    try:
        api_post("/free", {"unload_models": True, "free_memory": True})
    except Exception as exc:
        print(f"WARNING: ComfyUI memory release failed: {exc}", flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--resolution", type=int, default=768)
    parser.add_argument("--checkpoint", default="depth_anything_v2_vits.pth")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_sha = sha256_file(source)
    if source_sha != args.expected_source_sha256.strip().upper():
        raise RuntimeError(f"Source hash mismatch: {source_sha}")
    if output.exists() and not args.force:
        raise FileExistsError(output)
    queue = api_get("/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle.")
    atexit.register(release_comfy_memory)

    output.parent.mkdir(parents=True, exist_ok=True)
    input_name = f"pemara_depth_{uuid.uuid4().hex}_{source.name}"
    shutil.copy2(source, COMFY_INPUT / input_name)
    prefix = f"maestro_generative/depth/{output.stem}"
    workflow = {
        "1": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "2": {"class_type": "DepthAnythingV2Preprocessor", "inputs": {
            "image": ["1", 0], "ckpt_name": args.checkpoint,
            "resolution": args.resolution}},
        "3": {"class_type": "SaveImage", "inputs": {
            "images": ["2", 0], "filename_prefix": prefix}},
    }
    started = time.perf_counter()
    prompt_id = api_post(
        "/prompt", {"prompt": workflow, "client_id": str(uuid.uuid4())}
    )["prompt_id"]
    print(f"PROMPT_ID={prompt_id}", flush=True)
    deadline = time.time() + 30 * 60
    generated: Path | None = None
    while time.time() < deadline:
        history = api_get(f"/history/{prompt_id}").get(prompt_id)
        if history:
            status = history.get("status") or {}
            if status.get("completed") and status.get("status_str") == "success":
                item = history["outputs"]["3"]["images"][0]
                generated = (
                    COMFY_OUTPUT / str(item.get("subfolder") or "") / item["filename"]
                )
                break
            if status.get("completed"):
                raise RuntimeError(json.dumps(status, ensure_ascii=False))
        time.sleep(2)
    if generated is None or not generated.is_file():
        raise TimeoutError(prompt_id)
    shutil.copy2(generated, output)
    with Image.open(output) as image:
        dimensions = list(image.size)
        mode = image.mode
    elapsed = time.perf_counter() - started
    sidecar = {
        "schema_version": "1.0",
        "type": "relative_depth_control_not_game_asset",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "source_sha256": source_sha,
        "output": str(output),
        "output_sha256": sha256_file(output),
        "dimensions": dimensions,
        "mode": mode,
        "preprocessor": "DepthAnythingV2Preprocessor",
        "checkpoint": args.checkpoint,
        "resolution": args.resolution,
        "elapsed_seconds": elapsed,
        "validation_status": "pending_visual_qc",
        "integration_policy": "technical depth control only; never a game asset",
    }
    output.with_suffix(".json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OUTPUT={output}", flush=True)
    print(f"SHA256={sidecar['output_sha256']}", flush=True)
    print(f"ELAPSED_SECONDS={elapsed:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
