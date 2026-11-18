from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "clips"
WORK = ROOT / "outputs" / "work"
COMFY_OUT = ROOT.parent / "ComfyUI" / "output" / "maestro_generative"
STUDIO = os.environ.get("MAESTRO_STUDIO_URL", "http://127.0.0.1:8029").rstrip("/")
LORA_NAME = "intro_ritmos_60s_v1_000056250.safetensors"
LORA_TAG = "step56250_lora012"
RUN_TAG = "20260703"

OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)

NEGATIVE = (
    "static image, frozen frame, slideshow, no motion, humans, characters, heroes, monsters, "
    "bosses, bodies, faces, eyes, humanoid silhouettes, crowd, readable text, fake letters, "
    "watermark, UI, subtitles, anime character, medieval fantasy, photoreal actors, plastic 3D, "
    "clean futuristic city, comedy, bright happy palette, gore, jumpscare, random cuts"
)

SCENES = [
    (
        "pulse_street",
        """Five second animated environmental game intro shot, HD pixel art, modern PS1/SNES look.
        Strong visible motion every second: a golden musical note pulses brighter and dimmer, dust particles drift,
        foreground cables slide past camera, background street lights parallax, camera slowly dollies forward along
        an empty music street. Abandoned drums, guitar, amps, cables, amber street lamps, abstract neon music symbols,
        no readable text. Dark amber and purple palette, CRT grain. No characters, no humans, no faces.""",
    ),
    (
        "maestro_studio",
        """Five second animated environmental shot inside an empty music studio, HD pixel art, 2.5D parallax.
        Strong visible motion: camera pushes toward a dark piano, three candles flicker independently, wax glows,
        dust moves through light beams, loose papers lift and settle, cable shadows sway slightly. Two small empty
        chairs face the piano. Sad mysterious tone. No people, no silhouettes, no readable text.""",
    ),
    (
        "spectral_hat",
        """Five second animated supernatural environmental shot, HD pixel art, low camera close to cracked concrete.
        Strong visible motion: a black spectral hat slowly rises from the floor, purple light pulses under it,
        cracks spread outward frame by frame, small black fragments orbit the hat, color drains from the edges
        toward the center. Slow ominous zoom, CRT static. No body, no hand, no face, no creature.""",
    ),
    (
        "silence_wave",
        """Five second animated environmental shot of a musical street split by a purple silence wave.
        Strong visible motion: a vertical wall of purple energy sweeps left to right, warm amber instruments lose
        color as it passes, neon music symbols turn off, dust bursts outward, puddles reflect six small colored
        light streaks at the end without forming bodies. Camera tracks sideways with parallax. No characters,
        no humans, no readable text.""",
    ),
]


def post_job(scene_name: str, prompt: str) -> str:
    data = {
        "prompt": prompt,
        "mode": "video",
        "model": "wan2.2_ti2v_5B_fp16.safetensors",
        "negative": NEGATIVE,
        "lora": LORA_NAME,
        "lora_strength": "0.12",
        "width": "1280",
        "height": "720",
        "steps": "30",
        "guidance": "7",
        "seed": "-1",
        "frames": "121",
        "fps": "24",
    }
    response = requests.post(f"{STUDIO}/api/generative/job", data=data, timeout=60)
    response.raise_for_status()
    payload = response.json()
    (WORK / f"job_multiscene_{scene_name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload["job_id"]


def wait_job(job_id: str, scene_name: str) -> dict:
    last = None
    while True:
        payload = requests.get(f"{STUDIO}/api/generative/job/{job_id}", timeout=20).json()
        if payload != last:
            print(f"{scene_name}: {payload.get('status')} {payload.get('progress')}% {payload.get('message')}")
            last = payload
        if payload.get("status") in {"done", "error"}:
            (WORK / f"status_multiscene_{scene_name}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return payload
        time.sleep(20)


def newest_video_before() -> set[Path]:
    return set(COMFY_OUT.glob("video_*"))


def newest_after(before: set[Path]) -> Path:
    files = [p for p in COMFY_OUT.glob("video_*") if p not in before and p.suffix.lower() in {".mp4", ".webm"}]
    if not files:
        files = [p for p in COMFY_OUT.glob("video_*") if p.suffix.lower() in {".mp4", ".webm"}]
    return max(files, key=lambda p: p.stat().st_mtime)


def convert_clip(src: Path, dst: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def concat(clips: list[Path], dst: Path) -> None:
    list_file = WORK / "multiscene_concat.txt"
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(dst)],
        check=True,
    )


def main() -> int:
    final_clips: list[Path] = []
    for index, (scene_name, prompt) in enumerate(SCENES, start=1):
        before = newest_video_before()
        job_id = post_job(scene_name, prompt)
        status = wait_job(job_id, scene_name)
        if status.get("status") != "done":
            print(f"ERRO {scene_name}: {status.get('error')}")
            return 2
        src = newest_after(before)
        dst = OUT / f"intro_multiscene_{index:02d}_{scene_name}_{LORA_TAG}_{RUN_TAG}.mp4"
        convert_clip(src, dst)
        final_clips.append(dst)

    final = OUT / f"intro_preview_20s_multiscene_{LORA_TAG}_{RUN_TAG}.mp4"
    concat(final_clips, final)
    smooth60 = OUT / f"intro_preview_20s_multiscene_{LORA_TAG}_{RUN_TAG}_60fps_interp.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(final),
            "-vf",
            "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(smooth60),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-show_entries",
            "stream=width,height,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(smooth60),
        ],
        check=False,
    )
    print(f"FINAL={final}")
    print(f"SMOOTH60={smooth60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
