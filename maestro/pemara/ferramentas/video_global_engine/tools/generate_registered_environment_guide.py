#!/usr/bin/env python3
"""Generate one continuity-locked conditioning guide with local Qwen Image Edit."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image


COMFY = "http://127.0.0.1:8188"
COMFY_INPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\input")
COMFY_OUTPUT = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\output")
MODEL = "qwen_image_edit_2511_fp8mixed.safetensors"
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--negative-file", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--denoise", type=float, default=0.52)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--guidance", type=float, default=4.0)
    parser.add_argument("--width", type=int, default=1344)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def release_comfy_memory() -> None:
    try:
        requests.post(
            f"{COMFY}/free",
            json={"unload_models": True, "free_memory": True},
            timeout=15,
        ).raise_for_status()
    except Exception as exc:
        print(f"WARNING: failed to release ComfyUI cache: {exc}", flush=True)


def require_idle_queue() -> None:
    response = requests.get(f"{COMFY}/queue", timeout=30)
    response.raise_for_status()
    queue = response.json()
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle.")


def build_workflow(
    input_name: str,
    prompt: str,
    negative: str,
    seed: int,
    denoise: float,
    steps: int,
    guidance: float,
    width: int,
    height: int,
    prefix: str,
) -> dict:
    return {
        "1": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": CLIP, "type": "qwen_image", "device": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {
            "unet_name": MODEL, "weight_dtype": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "5": {"class_type": "ImageScale", "inputs": {
            "image": ["4", 0], "upscale_method": "lanczos", "width": width,
            "height": height, "crop": "disabled"}},
        "6": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["1", 0], "vae": ["3", 0], "image1": ["5", 0], "prompt": prompt}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["1", 0], "vae": ["3", 0], "image1": ["5", 0], "prompt": negative}},
        "8": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
            "conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}},
        "9": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
            "conditioning": ["7", 0], "reference_latents_method": "index_timestep_zero"}},
        "10": {"class_type": "CFGNorm", "inputs": {"model": ["2", 0], "strength": 1.0}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "12": {"class_type": "KSampler", "inputs": {
            "model": ["10", 0], "positive": ["8", 0], "negative": ["9", 0],
            "latent_image": ["11", 0], "seed": seed, "steps": steps, "cfg": guidance,
            "sampler_name": "euler", "scheduler": "simple", "denoise": denoise}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "SaveImage", "inputs": {
            "images": ["13", 0], "filename_prefix": prefix}},
    }


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    prompt_file = args.prompt_file.resolve()
    negative_file = args.negative_file.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    for path in (prompt_file, negative_file):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_sha = sha256_file(source)
    expected_sha = args.expected_source_sha256.strip().upper()
    if source_sha != expected_sha:
        raise RuntimeError(f"Source SHA-256 mismatch: expected {expected_sha}, got {source_sha}.")
    if not 0.0 < args.denoise <= 1.0:
        raise ValueError("--denoise must be in (0, 1].")
    if args.width % 16 or args.height % 16:
        raise ValueError("Guide dimensions must be multiples of 16.")
    prompt = prompt_file.read_text(encoding="utf-8").strip()
    negative = negative_file.read_text(encoding="utf-8").strip()
    plan = {
        "source": str(source),
        "source_sha256": source_sha,
        "output": str(output),
        "model": MODEL,
        "seed": args.seed,
        "denoise": args.denoise,
        "steps": args.steps,
        "guidance": args.guidance,
        "dimensions": [args.width, args.height],
        "lora": "",
    }
    print(json.dumps(plan, indent=2), flush=True)
    if args.dry_run:
        require_idle_queue()
        print("DRY_RUN_OK", flush=True)
        return 0
    if output.exists() and not args.force:
        raise FileExistsError(f"Output exists; use --force only for this exact guide: {output}")
    require_idle_queue()
    atexit.register(release_comfy_memory)
    output.parent.mkdir(parents=True, exist_ok=True)
    input_name = f"pemara_guide_{uuid.uuid4().hex}_{source.name}"
    shutil.copy2(source, COMFY_INPUT / input_name)
    prefix = f"maestro_generative/conditioning_guides/{output.stem}_{args.seed}"
    workflow = build_workflow(
        input_name, prompt, negative, args.seed, args.denoise, args.steps,
        args.guidance, args.width, args.height, prefix,
    )
    started = time.perf_counter()
    response = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": workflow, "client_id": str(uuid.uuid4())},
        timeout=30,
    )
    response.raise_for_status()
    prompt_id = response.json()["prompt_id"]
    deadline = time.time() + 30 * 60
    generated = None
    while time.time() < deadline:
        history = requests.get(f"{COMFY}/history/{prompt_id}", timeout=30).json().get(prompt_id)
        if history:
            status = history.get("status") or {}
            if status.get("completed") and status.get("status_str") == "success":
                item = history["outputs"]["14"]["images"][0]
                generated = COMFY_OUTPUT / str(item.get("subfolder") or "") / item["filename"]
                break
            if status.get("completed"):
                raise RuntimeError(json.dumps(status, ensure_ascii=False))
        time.sleep(3)
    if not generated or not generated.is_file():
        raise TimeoutError(f"Guide generation did not finish: {prompt_id}")
    shutil.copy2(generated, output)
    with Image.open(output) as image:
        dimensions = list(image.size)
        mode = image.mode
    elapsed = time.perf_counter() - started
    sidecar = {
        "schema_version": "1.0",
        "type": "conditioning_guide_not_game_asset",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "source_sha256": source_sha,
        "output": str(output),
        "output_sha256": sha256_file(output),
        "dimensions": dimensions,
        "mode": mode,
        "model": MODEL,
        "lora": "",
        "seed": args.seed,
        "denoise": args.denoise,
        "steps": args.steps,
        "guidance": args.guidance,
        "prompt_file": str(prompt_file),
        "negative_file": str(negative_file),
        "prompt": prompt,
        "negative": negative,
        "comfy_prompt_id": prompt_id,
        "elapsed_seconds": elapsed,
        "validation_status": "pending_visual_qc",
        "integration_policy": "conditioning only; does not replace an approved slideshow image",
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
