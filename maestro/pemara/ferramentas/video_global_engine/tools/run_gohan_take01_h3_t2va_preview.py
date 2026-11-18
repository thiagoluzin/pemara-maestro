"""Submit one isolated MiniMax H3 T2VA preview for Gohan/Android 16 take 01.

This deliberately does not mutate the production FL2VA manifests or approve
any keyframe.  It saves a PNG sequence so the review MP4 can be encoded with
NVENC after generation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(r"E:\Pemara\maestro\pemara")
PROJECT = ROOT / "ferramentas" / "video_global_engine" / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
COMFY_URL = "http://127.0.0.1:8188"
MODEL = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
TEXT_ENCODER = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VIDEO_VAE = "minimax_h3_video_vae_fp16.safetensors"
SEED = 2026081901
FRAMES = 243
FPS = 24


PROMPT = """integrated_multimodal_description: [Shot 1] Photorealistic live-action cinematic feature-film imagery faithful to the Cell Games silhouettes and colors, with natural skin pores, sweat, weathered fabric, practical bio-engineered armor and premium physically based visual effects. A very low medium-wide shot begins in a ruined stone arena beneath turbulent storm clouds. The severed but fully mechanical head of Android 16 rests intact in the extreme foreground among green armor fragments, ceramic plates and exposed circuits, with no blood, flesh or gore. Perfect Cell approaches in the midground without touching the head, while teenage Super Saiyan Gohan stands in the background wearing a torn dark-purple gi, his golden hair moving in the wind. The camera performs a continuous low tracking push with visible physical translation and strong foreground-to-background parallax, gliding beside Android 16's head and slowly arcing upward past Cell toward Gohan. From 00:00.500 to 00:06.350, Android 16 (S1), using a deep restrained male Brazilian Portuguese voice from Sao Paulo with natural cinematic delivery and no melodramatic over-enunciation, looks toward Gohan and says exactly: <d>[Portuguese] Não tenha medo de libertar sua força. Proteja a vida que eu aprendi a amar.</d> His mechanical lips and jaw articulate subtly and naturally, then close completely after the final word and remain closed. Gohan listens, loosens his fists, and a single tear begins to form while Cell continues one measured step. From 00:06.350 to 00:10.083, Cell enters the same visual axis, places one boot beside the head without contact, then raises it above the intact head in preparation for an irreversible downward strike. Gohan recognizes the intention and advances half a step too late; his expression changes from grief to alarm. Loose stones shift, dust crosses the lens at a different speed from Cell and Gohan, Cell's back plates respond to the wind, and the shot ends with the boot still raised and descending motion only beginning, handing active movement into the next take. No crushing occurs in this preview. No anime drawing, cel shading, game render, cosplay fabric, plastic skin, subtitles, text, logo, watermark, duplicate character, extra fighter, extra limb, blood, flesh, gore, instant Super Saiyan 2 transformation, repeated action, pose reset, simple zoom, crossfade, freeze frame or static tail.

overall_soundscape: Strong arena wind moves dust, fabric, hair and Cell's armor plates while small stones scrape over cracked ground. Android 16's dialogue is clean and close, followed by his lips closing, Cell's weighted footstep and Gohan's restrained breath; the head is not struck in this take.

non_diegetic_music: N/A"""


def request_json(path: str, *, method: str = "GET", payload: dict | None = None, timeout: int = 30) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        COMFY_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"ComfyUI request failed for {path}: {exc}") from exc


def workflow(prefix: str) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["1", 0], "shift_video": 12.0, "shift_audio": 3.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": TEXT_ENCODER, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VIDEO_VAE}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["3", 0], "vae": ["4", 0], "prompt": PROMPT, "width": 1344, "height": 768, "length": FRAMES}},
        "7": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["6", 0]}},
        "8": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": SEED}},
        "10": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["7", 0], "sampler": ["10", 0], "sigmas": ["8", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["11", 0]}},
        "13": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["12", 0], "vae": ["4", 0], "tile_size": 512, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}},
        "14": {"class_type": "ImageScale", "inputs": {"image": ["13", 0], "upscale_method": "lanczos", "width": 1280, "height": 720, "crop": "center"}},
        "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": prefix}},
    }


def main() -> int:
    queue = request_json("/queue", timeout=10)
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not empty; refusing to mix jobs.")

    stats = request_json("/system_stats", timeout=10)
    devices = stats.get("devices") or []
    free_vram = int(devices[0].get("vram_free") or 0) if devices else 0
    if free_vram < 24 * 1024**3:
        raise RuntimeError(f"MiniMax H3 requires 24 GiB free for this preview; available={free_vram / 1024**3:.2f} GiB")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"take01_t2va_preview_{timestamp}"
    prefix = f"maestro_generative/video/{run_id}/frame"
    graph = workflow(prefix)
    response = request_json("/prompt", method="POST", payload={"prompt": graph}, timeout=30)
    prompt_id = str(response.get("prompt_id") or "")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return prompt_id: {response}")

    log_dir = PROJECT / "logs" / run_id
    log_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "runId": run_id,
        "status": "SUBMITTED",
        "scope": "T2VA_PREVIEW_ONLY_NO_ANCHORS",
        "engine": "MiniMax H3 FL2VA checkpoint in T2VA mode",
        "model": MODEL,
        "promptId": prompt_id,
        "seed": SEED,
        "frames": FRAMES,
        "fps": FPS,
        "steps": 20,
        "nativeAudioDecoded": False,
        "productionManifestMutated": False,
        "promptSha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest().upper(),
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "outputPrefix": prefix,
    }
    manifest_path = log_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PROMPT_ID={prompt_id}", flush=True)
    print(f"RUN_ID={run_id}", flush=True)
    print(f"MANIFEST={manifest_path}", flush=True)

    started = time.monotonic()
    last_report = -30
    while True:
        elapsed = int(time.monotonic() - started)
        if elapsed - last_report >= 30:
            current_queue = request_json("/queue", timeout=10)
            print(
                f"PROGRESS elapsed={elapsed}s running={len(current_queue.get('queue_running') or [])} pending={len(current_queue.get('queue_pending') or [])}",
                flush=True,
            )
            last_report = elapsed
        history = request_json(f"/history/{prompt_id}", timeout=15)
        item = history.get(prompt_id)
        if item:
            status = item.get("status") or {}
            if status.get("completed"):
                if str(status.get("status_str") or "").lower() != "success":
                    raise RuntimeError(f"MiniMax H3 job failed: {status}")
                outputs = item.get("outputs") or {}
                images = ((outputs.get("15") or {}).get("images") or [])
                manifest.update(
                    {
                        "status": "COMPLETED",
                        "completedAt": datetime.now(timezone.utc).isoformat(),
                        "elapsedSeconds": elapsed,
                        "images": images,
                    }
                )
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"COMPLETED elapsed={elapsed}s frames={len(images)}", flush=True)
                for image in images[:1]:
                    print(f"FIRST_IMAGE={json.dumps(image, ensure_ascii=False)}", flush=True)
                return 0
        if elapsed > 3600:
            raise TimeoutError("MiniMax H3 preview exceeded one hour.")
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
