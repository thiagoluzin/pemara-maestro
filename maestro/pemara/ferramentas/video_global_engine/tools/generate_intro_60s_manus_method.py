#!/usr/bin/env python3
"""Gera keyframes e microtakes retomáveis do minuto Manus Method."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


DEFAULT_PROJECT = Path(__file__).resolve().parents[1] / "projetos" / "intro_ritmos_revolta" / "full_minute_manus_method"
DEFAULT_STUDIO = "http://127.0.0.1:8029"
COMFY_OUTPUT = Path(__file__).resolve().parents[2] / "ComfyUI" / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--studio", default=DEFAULT_STUDIO)
    parser.add_argument("--takes", nargs="*", default=[])
    parser.add_argument("--keyframes-only", action="store_true")
    parser.add_argument("--videos-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=10)
    return parser.parse_args()


def setup_log(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("intro60")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    log.addHandler(stream_handler)
    return log


def load_manifest(project: Path) -> dict:
    path = project / "production_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Manifesto não encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def ffprobe_video(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames:format=duration",
        "-of", "json", str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def valid_video(path: Path, frames: int, width: int, height: int, fps: int) -> bool:
    if not path.is_file() or path.stat().st_size < 100_000:
        return False
    try:
        data = ffprobe_video(path)
        stream = data["streams"][0]
        return (
            int(stream["width"]) == width
            and int(stream["height"]) == height
            and stream["avg_frame_rate"] == f"{fps}/1"
            and int(stream["nb_read_frames"]) == frames
        )
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, json.JSONDecodeError):
        return False


def start_job(studio: str, data: dict, image: Path | None = None) -> str:
    files = None
    handle = None
    try:
        if image:
            handle = image.open("rb")
            files = {"base_image": (image.name, handle, "image/png")}
        response = requests.post(f"{studio}/api/generative/job", data=data, files=files, timeout=90)
        response.raise_for_status()
        payload = response.json()
    finally:
        if handle:
            handle.close()
    return payload["job_id"]


def wait_job(studio: str, job_id: str, poll_seconds: int, log: logging.Logger) -> dict:
    last = None
    while True:
        response = requests.get(f"{studio}/api/generative/job/{job_id}", timeout=30)
        response.raise_for_status()
        payload = response.json()
        state = (payload.get("status"), payload.get("progress"), payload.get("message"))
        if state != last:
            log.info("job=%s status=%s progress=%s message=%s", job_id, *state)
            last = state
        if payload.get("status") in {"done", "error"}:
            return payload
        time.sleep(poll_seconds)


def output_path(payload: dict, kinds: set[str]) -> Path:
    result = payload.get("result") or {}
    for output in result.get("outputs") or []:
        if output.get("kind") in kinds:
            path = COMFY_OUTPUT / str(output.get("subfolder") or "") / str(output["filename"])
            if path.is_file():
                return path
    raise RuntimeError(f"Saída {sorted(kinds)} não encontrada no resultado do job.")


def write_sidecar(path: Path, content: dict) -> None:
    path.with_suffix(".json").write_text(
        json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    project = args.project.resolve()
    manifest = load_manifest(project)
    generation = manifest["generation"]
    selected = {item.upper() for item in args.takes}
    takes = [
        item for item in manifest["microtakes"]
        if not item.get("existing_video") and (not selected or item["id"].upper() in selected)
    ]
    if not takes:
        raise RuntimeError("Nenhum microtake novo selecionado.")

    keyframes = project / "keyframes"
    videos = project / "microtakes"
    logs = project / "logs"
    keyframes.mkdir(parents=True, exist_ok=True)
    videos.mkdir(parents=True, exist_ok=True)
    log = setup_log(logs / "generation.log")

    status = requests.get(f"{args.studio}/api/generative/status", timeout=30).json()
    if not status.get("ok") or not status.get("comfy_online"):
        raise RuntimeError("Maestro Studio/ComfyUI indisponível.")
    if status.get("pauses", {}).get("video") and not args.keyframes_only:
        raise RuntimeError(status["pauses"].get("video_reason") or "Geração de vídeo pausada.")

    plan = {
        "project": str(project),
        "takes": [item["id"] for item in takes],
        "keyframes": not args.videos_only,
        "videos": not args.keyframes_only,
        "image_model": generation["image_model"],
        "video_model": generation["video_model"],
    }
    log.info("PLANO %s", json.dumps(plan, ensure_ascii=False))
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        log.info("DRY-RUN concluído; nenhuma geração iniciada.")
        return 0

    if not args.videos_only:
        for index, take in enumerate(takes, start=1):
            destination = keyframes / f"{take['id']}_qwen2512_seed{take['seed']}.png"
            if destination.is_file() and destination.stat().st_size > 100_000 and not args.force:
                log.info("[%d/%d] keyframe %s já existe", index, len(takes), take["id"])
                continue
            log.info("[%d/%d] gerando keyframe %s", index, len(takes), take["id"])
            data = {
                "prompt": take["image_prompt"],
                "mode": "image",
                "model": generation["image_model"],
                "negative": manifest["global_negative"],
                "lora": generation["image_lora"],
                "lora_strength": "1.0",
                "width": "1344", "height": "768", "steps": "4", "guidance": "1.0",
                "seed": str(take["seed"]),
            }
            job_id = start_job(args.studio, data)
            payload = wait_job(args.studio, job_id, args.poll_seconds, log)
            if payload.get("status") != "done":
                raise RuntimeError(f"Keyframe {take['id']} falhou: {payload.get('error')}")
            source = output_path(payload, {"image"})
            shutil.copy2(source, destination)
            write_sidecar(destination, {
                "schema_version": "1.0", "type": "start_frame", "take_id": take["id"],
                "created_at": datetime.now().astimezone().isoformat(), "model": generation["image_model"],
                "seed": take["seed"], "prompt": take["image_prompt"],
                "negative": manifest["global_negative"], "validation_status": "pending_visual_qc",
            })

    if not args.keyframes_only:
        for index, take in enumerate(takes, start=1):
            keyframe = keyframes / f"{take['id']}_qwen2512_seed{take['seed']}.png"
            if not keyframe.is_file():
                raise FileNotFoundError(f"Keyframe obrigatório ausente: {keyframe}")
            destination = videos / f"{take['id']}_wan22_seed{take['seed']}_768x432_30fps.mp4"
            if valid_video(destination, take["frames"], generation["width"], generation["height"], generation["fps"]) and not args.force:
                log.info("[%d/%d] vídeo %s já está válido", index, len(takes), take["id"])
                continue
            log.info("[%d/%d] gerando vídeo %s (%d quadros)", index, len(takes), take["id"], take["frames"])
            prompt = (
                "Animate this premium cinematic anime keyframe as a real action shot with continuous physical "
                "motion, changing composition and strong depth. " + take["motion_prompt"] +
                " Preserve environment identity and object shapes. No random cut, no morphing, no living-photo look."
            )
            data = {
                "prompt": prompt, "mode": "video", "model": generation["video_model"],
                "negative": manifest["global_negative"], "lora": "", "lora_strength": "0",
                "width": str(generation["width"]), "height": str(generation["height"]),
                "steps": str(generation["steps"]), "guidance": str(generation["guidance"]),
                "seed": str(take["seed"]), "frames": str(take["frames"]), "fps": str(generation["fps"]),
                "video_conditioning_profile": "manus_motion",
            }
            job_id = start_job(args.studio, data, keyframe)
            payload = wait_job(args.studio, job_id, args.poll_seconds, log)
            if payload.get("status") != "done":
                raise RuntimeError(f"Vídeo {take['id']} falhou: {payload.get('error')}")
            source = output_path(payload, {"video"})
            shutil.copy2(source, destination)
            if not valid_video(destination, take["frames"], generation["width"], generation["height"], generation["fps"]):
                raise RuntimeError(f"Vídeo {take['id']} foi gerado, mas falhou no ffprobe.")
            write_sidecar(destination, {
                "schema_version": "1.0", "type": "microtake", "take_id": take["id"],
                "created_at": datetime.now().astimezone().isoformat(), "model": payload.get("result", {}).get("model"),
                "seed": take["seed"], "frames": take["frames"], "fps": generation["fps"],
                "width": generation["width"], "height": generation["height"], "prompt": prompt,
                "negative": manifest["global_negative"], "source_keyframe": str(keyframe),
                "video_conditioning_profile": "manus_motion",
                "validation_status": "pending_visual_qc",
            })
    log.info("OK: lote concluído")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        logging.getLogger("intro60").exception("FALHOU")
        raise
