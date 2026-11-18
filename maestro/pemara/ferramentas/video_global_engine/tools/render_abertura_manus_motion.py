#!/usr/bin/env python3
"""Renderiza os microtakes catastróficos aprovados com o método Manus/Wan 2.2."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import logging
import subprocess
import sys
import time
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path

import requests


ENGINE = Path(__file__).resolve().parents[1]
GAME_TOOLS = ENGINE / "projetos" / "Ritmos da Revolta" / "tools"
if str(GAME_TOOLS) not in sys.path:
    sys.path.insert(0, str(GAME_TOOLS))

from cinematic_direction_gate import validate_take_contract

DEFAULT_PROJECT = ENGINE / "projetos" / "Ritmos da Revolta" / "projeto_video_cutscenes" / "abertura_fase1"
DEFAULT_STUDIO = "http://127.0.0.1:8029"
COMFY_URL = "http://127.0.0.1:8188"
COMFY_OUTPUT = ENGINE.parent / "ComfyUI" / "output"
MIN_VIDEO_FPS = 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--manifest", default="production_manifest.json")
    parser.add_argument("--generation-key", default="catastrophe_generation")
    parser.add_argument("--collection", default="catastrophe_microtakes")
    parser.add_argument("--studio", default=DEFAULT_STUDIO)
    parser.add_argument("--takes", nargs="*", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--model", default="", help="Sobrescreve o modelo de video do manifesto.")
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--fps", type=int, default=0)
    parser.add_argument("--steps", type=int, default=0)
    parser.add_argument("--guidance", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=0, help="Sobrescreve a seed do take selecionado.")
    parser.add_argument("--keyframe", type=Path, default=None, help="Quadro inicial alternativo para continuacao encadeada.")
    parser.add_argument(
        "--end-keyframe",
        type=Path,
        default=None,
        help="Quadro final aprovado para Wan2.2 A14B first/last-frame.",
    )
    parser.add_argument(
        "--expected-end-sha256",
        default="",
        help="SHA-256 obrigatorio do quadro final quando --end-keyframe for usado.",
    )
    parser.add_argument("--motion-prompt-file", type=Path, default=None, help="Arquivo UTF-8 com direcao de movimento alternativa.")
    parser.add_argument("--camera-pose", default="")
    parser.add_argument("--camera-speed", type=float, default=None)
    parser.add_argument(
        "--conditioning-profile",
        choices=("identity_locked", "manus_motion"),
        default="",
        help="identity_locked usa CLIP Vision; manus_motion reproduz o condicionamento do master aprovado.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--output-stem", default="")
    parser.add_argument(
        "--output-label",
        default="",
        help="Rotulo seguro anexado ao arquivo para preservar renders anteriores.",
    )
    return parser.parse_args()


def safe_label(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum() or character in "-_")[:64]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def release_comfy_memory() -> None:
    try:
        requests.post(
            f"{COMFY_URL}/free",
            json={"unload_models": True, "free_memory": True},
            timeout=15,
        ).raise_for_status()
    except Exception as exc:
        print(f"AVISO: falha ao liberar cache do ComfyUI: {exc}", flush=True)


def logger_for(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("abertura_manus_motion")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(formatter)
        log.addHandler(handler)
    return log


def ffprobe(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames:format=duration",
        "-of", "json", str(path),
    ]
    return json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)


def valid_video(path: Path, generation: dict, frames: int) -> bool:
    if not path.is_file() or path.stat().st_size < 100_000:
        return False
    try:
        stream = ffprobe(path)["streams"][0]
        # Wan snaps arbitrary requests down to its valid 4n+1 temporal grid.
        valid_frame_counts = {frames, ((frames - 1) // 4) * 4 + 1}
        return (
            int(stream["width"]) == generation["width"]
            and int(stream["height"]) == generation["height"]
            and stream["avg_frame_rate"] == f"{generation['fps']}/1"
            and int(stream["nb_read_frames"]) in valid_frame_counts
        )
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, json.JSONDecodeError):
        return False


def transcode_nvenc(source: Path, destination: Path, generation: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoders = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
    )
    if "h264_nvenc" not in encoders.stdout:
        raise RuntimeError("h264_nvenc indisponivel; fallback de CPU e proibido.")
    width = int(generation["width"])
    height = int(generation["height"])
    fps = int(generation["fps"])
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(source),
            "-vf", (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps={fps},setsar=1,format=yuv420p"
            ),
            "-an", "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq",
            "-rc", "constqp", "-qp", "14", "-movflags", "+faststart",
            str(destination),
        ],
        check=True,
    )


def submit(
    studio: str,
    data: dict,
    keyframe: Path,
    end_keyframe: Path | None = None,
) -> str:
    with ExitStack() as stack:
        base_handle = stack.enter_context(keyframe.open("rb"))
        files = {"base_image": (keyframe.name, base_handle, "image/png")}
        if end_keyframe:
            end_handle = stack.enter_context(end_keyframe.open("rb"))
            files["end_image"] = (end_keyframe.name, end_handle, "image/png")
        response = requests.post(
            f"{studio}/api/generative/job",
            data=data,
            files=files,
            timeout=90,
        )
    response.raise_for_status()
    return response.json()["job_id"]


def wait(studio: str, job_id: str, seconds: int, log: logging.Logger) -> dict:
    previous = None
    while True:
        response = requests.get(f"{studio}/api/generative/job/{job_id}", timeout=30)
        response.raise_for_status()
        payload = response.json()
        current = (payload.get("status"), payload.get("progress"), payload.get("message"))
        if current != previous:
            log.info("job=%s status=%s progress=%s message=%s", job_id, *current)
            previous = current
        if payload.get("status") in {"done", "error"}:
            payload.setdefault("job_id", job_id)
            return payload
        time.sleep(seconds)


def result_video(payload: dict) -> Path:
    for item in (payload.get("result") or {}).get("outputs") or []:
        if item.get("kind") == "video":
            path = COMFY_OUTPUT / str(item.get("subfolder") or "") / str(item["filename"])
            if path.is_file():
                return path
    raise RuntimeError("O job terminou sem arquivo de vídeo localizável.")


def timed_direction_prompt(take: dict) -> str:
    direction = take.get("direction_contract") or {}
    return " ".join(
        f"From {beat['start']} to {beat['end']} seconds: {beat['action']}"
        for beat in direction.get("beats") or []
    )


def main() -> int:
    args = parse_args()
    project = args.project.resolve()
    manifest_arg = Path(args.manifest)
    manifest_path = manifest_arg.resolve() if manifest_arg.is_absolute() else (project / manifest_arg).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    generation = dict(manifest.get(args.generation_key) or {})
    if not generation:
        raise RuntimeError(f"Bloco de geração ausente: {args.generation_key}")
    overrides = {
        "video_model": args.model,
        "width": args.width,
        "height": args.height,
        "frames": args.frames,
        "fps": args.fps,
        "steps": args.steps,
        "guidance": args.guidance,
    }
    for key, value in overrides.items():
        if value:
            generation[key] = value
    conditioning_profile = (
        args.conditioning_profile
        or str(generation.get("conditioning_profile") or "identity_locked")
    ).strip().lower()
    if conditioning_profile not in {"identity_locked", "manus_motion"}:
        raise RuntimeError(f"Perfil de condicionamento invalido: {conditioning_profile}")
    if int(generation.get("fps") or 0) < MIN_VIDEO_FPS:
        raise RuntimeError(
            f"FPS abaixo de {MIN_VIDEO_FPS} e proibido no Pemara. "
            "Use 24, 30 ou 60 FPS."
        )
    selected = {item.zfill(2) for item in args.takes}
    takes = [
        item for item in manifest.get(args.collection, [])
        if not selected or item["id"] in selected
    ]
    if not takes:
        raise RuntimeError("Nenhum take selecionado.")

    direction_errors = {
        item["id"]: validate_take_contract(
            item, int(generation["fps"]), require_video_approval=True
        )
        for item in takes
    }
    direction_errors = {
        take_id: errors for take_id, errors in direction_errors.items() if errors
    }
    if direction_errors:
        detail = "\n".join(
            f"{take_id}: " + "; ".join(errors)
            for take_id, errors in direction_errors.items()
        )
        raise RuntimeError("Gate de direcao reprovado:\n" + detail)

    status = requests.get(f"{args.studio}/api/generative/status", timeout=30).json()
    if not status.get("ok") or not status.get("comfy_online"):
        raise RuntimeError("Maestro Studio/ComfyUI indisponível.")
    if status.get("pauses", {}).get("video"):
        raise RuntimeError(status["pauses"].get("video_reason") or "Geração de vídeo pausada.")

    source_lock = manifest.get("source_lock") or {}
    expected_source_sha = str(source_lock.get("sha256") or "").strip().upper()
    blocked = [] if expected_source_sha else [
        item["id"] for item in takes
        if item.get("direction_contract", {}).get("catastrophe_keyframe_status") != "approved_visual_qc"
    ]
    if blocked and not args.dry_run:
        raise RuntimeError(
            "Vídeo bloqueado: keyframes catastróficas sem aprovação visual: " + ", ".join(blocked)
        )

    if args.output_stem and len(takes) != 1:
        raise RuntimeError("--output-stem só pode ser usado com um único take.")
    if args.end_keyframe and len(takes) != 1:
        raise RuntimeError("--end-keyframe só pode ser usado com um único take.")
    if args.end_keyframe and not args.expected_end_sha256.strip():
        raise RuntimeError("--end-keyframe exige --expected-end-sha256.")
    if args.output_stem and Path(args.output_stem).name != args.output_stem:
        raise RuntimeError("--output-stem deve ser apenas um nome, sem caminho.")
    destination_dir = (args.output_dir or project / "microtakes" / "catastrophe").resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    log = logger_for(project / "logs" / "catastrophe_production.log")
    output_label = safe_label(args.output_label)
    log.info(
        "PLANO takes=%s model=%s size=%sx%s frames=%s fps=%s steps=%s guidance=%s conditioning=%s label=%s",
        [t["id"] for t in takes], generation["video_model"], generation["width"],
        generation["height"], generation["frames"], generation["fps"], generation["steps"],
        generation["guidance"], conditioning_profile, output_label,
    )
    if not args.dry_run:
        atexit.register(release_comfy_memory)

    for index, take in enumerate(takes, start=1):
        keyframe_value = (
            str(take.get("keyframe_from") or "").strip()
            or str(source_lock.get("stable_copy") or source_lock.get("approved_source") or "").strip()
        )
        keyframe = args.keyframe.resolve() if args.keyframe else Path(keyframe_value)
        if not keyframe.is_absolute():
            keyframe = (project / keyframe).resolve()
        end_keyframe = args.end_keyframe.resolve() if args.end_keyframe else None
        base_stem = args.output_stem or take.get("output_stem") or f"take{take['id']}_wan22_fun_camera"
        stem = base_stem + (f"_{output_label}" if output_label else "")
        destination = destination_dir / f"{stem}.mp4"
        if not keyframe.is_file():
            raise FileNotFoundError(f"Keyframe ausente: {keyframe}")
        keyframe_sha = sha256_file(keyframe)
        if expected_source_sha and keyframe_sha != expected_source_sha:
            raise RuntimeError(
                f"Hash da imagem aprovada divergiu: esperado {expected_source_sha}, obtido {keyframe_sha}."
            )
        end_keyframe_sha = ""
        if end_keyframe:
            if conditioning_profile == "manus_motion":
                raise RuntimeError("manus_motion reproduz o master start-only e nao aceita quadro final.")
            if not end_keyframe.is_file():
                raise FileNotFoundError(f"Keyframe final ausente: {end_keyframe}")
            if "fun_camera" in str(generation["video_model"]).lower():
                raise RuntimeError("Wan2.2 Fun Camera não aceita quadro final; use Wan2.2 A14B I2V.")
            end_keyframe_sha = sha256_file(end_keyframe)
            expected_end_sha = args.expected_end_sha256.strip().upper()
            if end_keyframe_sha != expected_end_sha:
                raise RuntimeError(
                    "Hash da imagem final aprovada divergiu: "
                    f"esperado {expected_end_sha}, obtido {end_keyframe_sha}."
                )
        requested_frames = int(generation.get("frames") or take["frames"])
        recommendation = take.get("recommended_generation") or {}
        render_seed = args.seed or int(take.get("seed") or recommendation.get("seed") or -1)
        if valid_video(destination, generation, requested_frames) and not args.force:
            log.info("[%d/%d] take %s já válido", index, len(takes), take["id"])
            continue

        motion_prompt = (
            args.motion_prompt_file.resolve().read_text(encoding="utf-8").strip()
            if args.motion_prompt_file
            else " ".join(filter(None, (
                recommendation.get("prompt") or take.get("motion_prompt", ""),
                timed_direction_prompt(take),
            )))
        )
        camera_contract = take.get("fun_camera_direction_contract") or {}
        camera_pose = (
            args.camera_pose or recommendation.get("camera_pose")
            or camera_contract.get("camera_pose") or ""
        )
        camera_speed = (
            float(args.camera_speed)
            if args.camera_speed is not None
            else float(recommendation.get("camera_speed") or camera_contract.get("camera_speed") or 0.8)
        )
        strict_identity_lock = bool(
            generation.get("strict_identity_lock") or take.get("strict_identity_lock")
        )
        if conditioning_profile == "manus_motion":
            prompt = (
                "Animate this premium cinematic anime keyframe as a real action shot with continuous physical "
                "motion, changing composition and strong depth. " + motion_prompt +
                " Preserve environment identity and object shapes. No random cut, no morphing, no living-photo look."
            )
        elif end_keyframe:
            prompt = (
                "Animate continuously from the exact approved first frame into the exact approved final frame as a "
                "real premium cinematic anime video. Both endpoint images are identity locks. The physical event "
                "must cause the change; never use a cross-dissolve, global color fade, texture melt or arbitrary "
                "architecture morph. Keep the physical event spatially localized, narrow and translucent; it must "
                "never hide the full frame, dissolve the scene, globally grade it or exchange geometry. Reveal each "
                "changed depth layer without an opaque transition wall. Use a restrained physical camera move and "
                "independently moving foreground, midground and background layers. "
                + motion_prompt + " Keep the event, camera and parallax smooth and readable, never frantic. "
                "Environmental catastrophe only, zero living beings. No random cut, no slideshow."
            )
        elif strict_identity_lock:
            prompt = (
                "Animate this exact approved environmental keyframe as one continuous premium cinematic 2D shot. "
                "Treat the source as a strict identity and geometry lock in every frame: preserve the same street, "
                "architecture, object count, rigid instruments, palette, painterly detail and existing damage. Use "
                "only a restrained physical camera displacement with subtle differential foreground, midground and "
                "background parallax; never invent new geography, repaint the scene or replace objects. Keep stable "
                "deep focus without frame-wide motion blur. " + motion_prompt + " Keep the event localized, smooth "
                "and readable. Environmental catastrophe only, zero living beings. No random cut, morphing, global "
                "grade, crossfade, slideshow or living photo."
            )
        else:
            prompt = (
                "Animate this exact approved environmental keyframe as a real premium cinematic anime video, not a "
                "living photo. Preserve the district, every rigid object identity, palette and existing damage. "
                "The camera must physically travel through the scene and reveal new geography; motion cannot be a "
                "digital zoom. Use independently moving foreground, midground and background layers with natural "
                "motion blur and deep parallax. " + motion_prompt + " Keep the camera move smooth and readable, never "
                "frantic. The final composition and physical damage must be visibly different from the first frame. "
                "Environmental catastrophe only, zero living beings. No random cut, no morphing, no slideshow."
            )
        extended_identity_negative = (
            ""
            if conditioning_profile == "manus_motion"
            else (
                "person, people, human, humanoid, animal, creature, monster, body, face, eyes, head, arms, legs, "
                "silhouette, dancer, performer, portal occupant, living object, object "
                "morphing, static camera, locked camera, tripod shot, simple zoom, digital zoom, living photo, "
                "frozen background, weak parallax, accelerated background, frantic camera, shaky camera, whip pan, "
                "camera teleport, scene cut, new street, new architecture, deformed guitar, duplicated instrument, "
                "disappearing guitar, dissolving guitar, "
                "guitar turning into smoke, erased guitar, temporal smearing, motion smear, ghost guitar, "
                "compression artifacts, soft low-detail image"
            )
        )
        negative = ", ".join(filter(None, [
            manifest.get("global_negative", ""),
            recommendation.get("negative") or take.get("negative_prompt", ""),
            extended_identity_negative,
        ]))
        if args.dry_run:
            log.info(
                "DRY-RUN take=%s source=%s sha256=%s end=%s end_sha256=%s output=%s pose=%s speed=%s seed=%s conditioning=%s",
                take["id"], keyframe, keyframe_sha, end_keyframe, end_keyframe_sha,
                destination, camera_pose, camera_speed, render_seed, conditioning_profile,
            )
            continue
        data = {
            "prompt": prompt,
            "mode": "video",
            "model": generation["video_model"],
            "negative": negative,
            "lora": "",
            "lora_strength": "0",
            "width": str(generation["width"]),
            "height": str(generation["height"]),
            "steps": str(generation["steps"]),
            "guidance": str(generation["guidance"]),
            "seed": str(render_seed),
            "frames": str(requested_frames),
            "fps": str(generation["fps"]),
            "camera_pose": camera_pose,
            "camera_speed": str(camera_speed),
            "video_conditioning_profile": conditioning_profile,
        }
        log.info("[%d/%d] gerando take %s", index, len(takes), take["id"])
        payload = wait(
            args.studio,
            submit(args.studio, data, keyframe, end_keyframe),
            args.poll_seconds,
            log,
        )
        if payload.get("status") != "done":
            raise RuntimeError(f"Take {take['id']} falhou: {payload.get('error') or payload.get('message')}")
        native_output = result_video(payload)
        transcode_nvenc(native_output, destination, generation)
        if not valid_video(destination, generation, requested_frames):
            raise RuntimeError(f"Take {take['id']} falhou na validação ffprobe.")
        destination.with_suffix(".json").write_text(json.dumps({
            "schema_version": "1.0",
            "type": "microtake",
            "take_id": take["id"],
            "created_at": datetime.now().astimezone().isoformat(),
            "model": payload.get("result", {}).get("model") or generation["video_model"],
            "lora": "",
            "seed": render_seed,
            "frames": requested_frames,
            "fps": generation["fps"],
            "width": generation["width"],
            "height": generation["height"],
            "source_keyframe": str(keyframe),
            "source_sha256": keyframe_sha,
            "end_keyframe": str(end_keyframe) if end_keyframe else "",
            "end_keyframe_sha256": end_keyframe_sha,
            "native_output": str(native_output),
            "studio_job_id": payload.get("job_id"),
            "camera_pose": camera_pose,
            "camera_speed": camera_speed,
            "video_conditioning_profile": conditioning_profile,
            "prompt": prompt,
            "negative": negative,
            "encoder": "h264_nvenc_constqp14",
            "probe": ffprobe(destination),
            "sha256": sha256_file(destination),
            "validation_status": "pending_visual_and_motion_qc"
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("[%d/%d] salvo %s", index, len(takes), destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
