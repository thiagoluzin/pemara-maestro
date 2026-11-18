"""Finalize a persisted Studio job from a verified ComfyUI video artifact.

This is an incident-recovery path for the Windows asyncio listener failure: the
GPU worker can finish and save the MP4 even though ComfyUI history is no longer
reachable over HTTP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from generative_jobs import GenerativeJobStore


ROOT = Path(__file__).resolve().parents[2]
JOB_STORE_PATH = ROOT / "dados" / "studio" / "generative_jobs.json"
COMFY_OUTPUT_ROOT = ROOT / "ferramentas" / "ComfyUI" / "output"
H3_MODEL = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"


def inspect_video(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    probe = json.loads(completed.stdout)
    video = next(
        (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if not video:
        raise RuntimeError("O artefato recuperado nao possui stream de video.")
    duration = float((probe.get("format") or {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("O artefato recuperado possui duracao invalida.")
    rate_text = str(video.get("r_frame_rate") or "0/1")
    rate = float(Fraction(rate_text))
    if rate <= 0:
        raise RuntimeError("O artefato recuperado possui FPS invalido.")
    return {
        "duration": duration,
        "fps": rate,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "codec": str(video.get("codec_name") or ""),
    }


def artifact_receipts(job_id: str, result: dict, output_root: Path) -> list[dict]:
    if result.get("model") != H3_MODEL or not result.get("prompt_id"):
        return []
    root = output_root.resolve()
    receipts = []
    for item in result.get("outputs", []):
        if item.get("type") != "output" or item.get("kind") != "video":
            continue
        path = (root / str(item.get("subfolder") or "").replace("\\", "/") / item["filename"]).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != ".mp4":
            continue
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        receipts.append({"job_id": job_id, "prompt_id": str(result["prompt_id"]),
                         "relative_path": path.relative_to(root).as_posix(), "sha256": digest})
    return receipts


def recover(job_id: str, video_path: Path) -> dict[str, Any]:
    video_path = video_path.resolve(strict=True)
    output_root = COMFY_OUTPUT_ROOT.resolve(strict=True)
    try:
        relative = video_path.relative_to(output_root)
    except ValueError as exc:
        raise RuntimeError("O video recuperado esta fora da saida oficial do ComfyUI.") from exc
    if not video_path.name.startswith("minimax_h3_fl2va_") or video_path.suffix.lower() != ".mp4":
        raise RuntimeError("O arquivo nao corresponde a uma saida MP4 MiniMax H3.")

    store = GenerativeJobStore(JOB_STORE_PATH, recover_on_init=False)
    job = store.get(job_id)
    if not job:
        raise RuntimeError(f"Job inexistente: {job_id}")
    if str(job.get("model") or "") != H3_MODEL:
        raise RuntimeError("O job indicado nao usa o MiniMax H3 esperado.")
    if str(job.get("status") or "") not in {"canceled", "error", "interrupted"}:
        raise RuntimeError("O worker do Studio ainda esta ativo; cancele-o antes da recuperacao.")

    prompt_id = str(job.get("prompt_id") or "")
    with video_path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    expected = {"job_id": job_id, "prompt_id": prompt_id,
                "relative_path": relative.as_posix(), "sha256": digest}
    if not prompt_id or expected not in job.get("artifact_receipts", []):
        raise RuntimeError("O recibo original deste job nao comprova o arquivo selecionado.")

    media = inspect_video(video_path)
    subfolder = str(relative.parent).replace("/", "\\")
    query = urlencode(
        {"filename": video_path.name, "subfolder": subfolder, "type": "output"}
    )
    result = {
        "ok": True,
        "mode": "video",
        "message": (
            f"Video MP4 {media['width']}x{media['height']}/{media['fps']:g}fps "
            "recuperado apos falha HTTP do ComfyUI."
        ),
        "prompt_id": str(job.get("prompt_id") or ""),
        "seed": None,
        "model": H3_MODEL,
        "lora": "",
        "video_conditioning_profile": str(
            (job.get("request_spec") or {}).get("video_conditioning_profile") or "identity_locked"
        ),
        "frames": int(job.get("frames") or 0),
        "fps": media["fps"],
        "duration_seconds": media["duration"],
        "outputs": [
            {
                "node": "16",
                "kind": "video",
                "filename": video_path.name,
                "subfolder": subfolder,
                "type": "output",
                "url": f"/api/generative/comfy-view?{query}",
            }
        ],
        "recovered_after_comfy_http_failure": True,
    }
    return store.update(
        job_id,
        expected_updated_at=job["updated_at"],
        status="done",
        progress=100,
        message="Concluido; video recuperado apos falha HTTP do ComfyUI.",
        error=None,
        result=result,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--video-path", type=Path, required=True)
    args = parser.parse_args()
    recovered = recover(args.job_id, args.video_path)
    print(json.dumps(recovered, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
