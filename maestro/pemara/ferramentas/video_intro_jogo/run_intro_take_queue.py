from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
MAESTRO_BASE = ROOT.parent.parent
ENGINE_PROJECT = ROOT.parent / "video_global_engine" / "projetos" / "intro_ritmos_revolta"
QUEUE_FILE = ENGINE_PROJECT / "take_queue.json"
OUT = ENGINE_PROJECT / "takes"
WORK = ROOT / "outputs" / "work"
COMFY_OUT = ROOT.parent / "ComfyUI" / "output" / "maestro_generative"
COMFY_OUTPUT_ROOT = ROOT.parent / "ComfyUI" / "output"
VIDEO_PAUSE_FLAG = MAESTRO_BASE / "dados" / "flags" / "video_generation_paused.flag"
STUDIO = os.environ.get("MAESTRO_STUDIO_URL", "http://127.0.0.1:8029").rstrip("/")

# Motor aprovado para a RTX 5090 (ver registry 2026-07-17 e regra v8).
# Wan 5B TI2V foi reprovado para producao em 2026-07-11 e movido para
# quarentena em 2026-07-19; nao apontar DEFAULT_MODEL para ele de novo.
# Quant: Q5_K_M cabe residente na VRAM da 5090 com 181-241 frames 720p;
# Q8_0 (2x14,35GB) thrashou a 260s/step em 2026-07-19 e fica proibido como default.
DEFAULT_MODEL = "wan2.2_i2v_high_noise_14B_Q5_K_M.gguf"
DEFAULT_LORA = ""
DEFAULT_IMAGE_MODEL = "flux1-krea-dev_fp8_scaled.safetensors"
MIN_TAKE_SECONDS_DEFAULT = 6
MAX_STEPS_DEFAULT = 24
MIN_BASE_IMAGE_WIDTH = 1024
REJECTED_BASE_STATUSES = {"approved_reference", "legacy_reference", "existing_reference"}
CONTROLLED_VIDEO_PREFIX = (
    "Animate this approved modern cinematic anime keyframe as a real video take, not a slideshow or living photo. "
    "Preserve the exact composition, objects, style, lighting and scene identity. Do not introduce new objects, "
    "new characters, camera rigs, geometric props, text, logos or symbols. Use the scene plan with discipline: "
    "one clear camera move, one physical environment/object event, and one light/particle change. The motion must "
    "have beginning, middle and end. Prioritize fidelity over spectacle. Avoid static hold, simple zoom only, "
    "image loop, hallucinated equipment, random foreground blocks, triangles, cones, prisms and extra actors. "
)

VEOKLING_VIDEO_PREFIX = (
    "Use Veo/Kling-style shot discipline. The approved start frame defines composition, geography, objects, "
    "style and identity. Build a short cinematic take with a visible beginning, middle and end. Use explicit "
    "camera motion, foreground/background parallax, one physical event, and controlled lighting or particles. "
    "Do not improvise new subjects. Do not turn this into a living photo. "
)

VEOKLING_NEGATIVE = (
    "slideshow, static hold, simple zoom only, living photo, fake text, generated logo, watermark, camera rig, "
    "camera operator, random human, humanoid silhouette, intrusive prop, colored triangle, color band, cone, prism, "
    "crystal, poster text, deformed object, style drift, sudden cut"
)

AGGRESSIVE_VIDEO_PREFIX = (
    "Animate this approved modern cinematic anime keyframe as a real video take, not a slideshow or living photo. "
    "Preserve the 2020s anime film style, clean line art, detailed painted background, composition, "
    "objects and lighting. Use strong visible motion in at least five layers: cinematic camera move, "
    "foreground parallax, background parallax, particles/atmosphere, object transformation, and animated lighting. "
    "Camera must move clearly: dolly, truck, crane, tilt, push-in, pull-back, rack focus or 20-45 degree orbit when appropriate. "
    "Foreground objects should cross frame when possible. Add one clear event with beginning, middle and end. "
    "No static hold, no simple zoom only, no still image loop. Do not use pixel art, retro sprite style or low-resolution texture. "
)

MOTION_PREFIXES = {
    "controlled": CONTROLLED_VIDEO_PREFIX,
    "aggressive": AGGRESSIVE_VIDEO_PREFIX,
}

ANIME_VIDEO_PREFIX = AGGRESSIVE_VIDEO_PREFIX


def load_queue(queue_file: Path = QUEUE_FILE) -> dict:
    return json.loads(queue_file.read_text(encoding="utf-8-sig"))


def video_generation_paused() -> bool:
    value = os.environ.get("PEMARA_VIDEO_GENERATION_PAUSED", "").strip().lower()
    return value in {"1", "true", "yes", "sim", "on"} or VIDEO_PAUSE_FLAG.exists()


def video_pause_message() -> str:
    return (
        "BLOQUEADO: geracao local de video esta pausada ate segunda ordem. "
        f"Flag: {VIDEO_PAUSE_FLAG}. Use --ignore-video-pause apenas para teste deliberado."
    )


def safe_run_label(label: str) -> str:
    label = (label or "").strip().lower()
    if not label:
        return ""
    label = re.sub(r"[^a-z0-9_-]+", "_", label)
    return label.strip("_")[:64]


def ledger_file(kind: str, take: dict, run_tag: str = "") -> Path:
    """Return a per-run ledger path so labelled variants never overwrite each other."""
    suffix = f"_{safe_run_label(run_tag)}" if run_tag else ""
    return WORK / f"{kind}_take_{take['id']}_{take['slug']}{suffix}.json"


def selected_takes(queue: dict, requested: list[str]) -> list[dict]:
    takes = queue["takes"]
    if not requested:
        return takes
    requested_set = {item.zfill(2) for item in requested}
    return [take for take in takes if take["id"] in requested_set or take["slug"] in requested_set]


def comfy_output_path(output: dict) -> Path:
    filename = output.get("filename") or ""
    subfolder = output.get("subfolder") or ""
    folder_type = output.get("type") or "output"
    if folder_type != "output" or not filename:
        raise ValueError(f"Output inesperado do Studio: {output}")
    base = (COMFY_OUTPUT_ROOT / subfolder).resolve()
    root = COMFY_OUTPUT_ROOT.resolve()
    path = (base / filename).resolve()
    if root not in path.parents and path != root:
        raise ValueError(f"Output fora da pasta do ComfyUI: {path}")
    if not path.exists():
        raise FileNotFoundError(f"Output do job nao encontrado: {path}")
    return path


def first_output_path(status: dict, kinds: set[str]) -> Path:
    outputs = (((status.get("result") or {}).get("outputs")) or [])
    for output in outputs:
        if output.get("kind") in kinds:
            return comfy_output_path(output)
    raise FileNotFoundError(f"Job terminou sem output {sorted(kinds)}: {json.dumps(status, ensure_ascii=False)[:500]}")


def base_image_is_legacy(take: dict) -> bool:
    base = take.get("base_image", {})
    status = (base.get("status") or "").lower()
    model = (base.get("model") or "").lower()
    file = (base.get("file") or "").lower()
    return (
        status in REJECTED_BASE_STATUSES
        or model == "existing_reference"
        or "assets_referencia" in file
    )


def base_image_metadata_candidates(take: dict, base_path: Path) -> list[Path]:
    base = take.get("base_image", {})
    candidates: list[Path] = [base_path.with_suffix(".json")]
    metadata = (base.get("metadata") or "").strip()
    if metadata:
        candidates.append(Path(metadata))

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def validate_base_image_json(take: dict, base_path: Path) -> tuple[Path, dict]:
    sidecar_path = base_path.with_suffix(".json")
    if not sidecar_path.exists():
        raise RuntimeError(
            f"BLOQUEADO {take['id']}_{take['slug']}: imagem-base sem JSON lateral obrigatorio. "
            f"Sem JSON = ativo invalido. Esperado: {sidecar_path}"
        )

    candidates = base_image_metadata_candidates(take, base_path)
    for metadata_path in candidates:
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise RuntimeError(
                f"BLOQUEADO {take['id']}_{take['slug']}: JSON da imagem-base invalido: "
                f"{metadata_path} ({exc})"
            ) from exc

        prompt = (metadata.get("prompt") or metadata.get("image_prompt") or "").strip()
        if not prompt:
            raise RuntimeError(
                f"BLOQUEADO {take['id']}_{take['slug']}: JSON da imagem-base sem prompt: {metadata_path}"
            )

        image_file = (metadata.get("image_file") or metadata.get("file") or "").strip()
        if not image_file:
            raise RuntimeError(
                f"BLOQUEADO {take['id']}_{take['slug']}: JSON da imagem-base sem image_file: {metadata_path}"
            )
        try:
            if Path(image_file).resolve() != base_path.resolve():
                raise RuntimeError(
                    f"BLOQUEADO {take['id']}_{take['slug']}: JSON aponta para outra imagem. "
                    f"base={base_path} json_image_file={image_file}"
                )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"BLOQUEADO {take['id']}_{take['slug']}: nao foi possivel validar image_file "
                f"em {metadata_path}: {exc}"
            ) from exc

        validation_status = (metadata.get("validation_status") or "").lower()
        if validation_status not in {"approved", "approved_keyframe", "approved_for_video"}:
            raise RuntimeError(
                f"BLOQUEADO {take['id']}_{take['slug']}: JSON da imagem-base esta como "
                f"'{validation_status}'. Marque como approved_for_video apos QC humano."
            )

        return metadata_path, metadata

    listed = ", ".join(path.as_posix() for path in candidates)
    raise RuntimeError(
        f"BLOQUEADO {take['id']}_{take['slug']}: imagem-base sem JSON obrigatorio. "
        f"Sem JSON = ativo invalido. Candidatos: {listed}"
    )


def validate_cinematic_contract(take: dict) -> None:
    """Gate for takes authored under novo_plano.md before any GPU request."""
    contract = take.get("shot_contract") or {}
    if contract.get("contract_version") != "novo_plano_20260720":
        return

    required = {
        "story_purpose",
        "dramatic_question",
        "story_change",
        "environment_state_before",
        "environment_state_after",
        "environmental_reaction",
        "duration_reason",
        "cut_motivation",
        "motion_beats",
        "camera",
        "visual_references",
        "negative_rules",
    }
    missing = sorted(key for key in required if not contract.get(key))
    if missing:
        raise RuntimeError(
            f"BLOQUEADO {take['id']}_{take['slug']}: contrato cinematografico incompleto: "
            + ", ".join(missing)
        )

    if int(contract.get("distinct_story_events", 0)) < 2:
        raise RuntimeError(
            f"BLOQUEADO {take['id']}_{take['slug']}: contrato exige ao menos dois eventos narrativos."
        )
    if (
        take.get("id") == "01"
        and str(contract.get("environment_damage", "")).strip().lower() not in {"none", "nenhum"}
    ):
        raise RuntimeError(
            f"BLOQUEADO {take['id']}_{take['slug']}: Take 1 deve manter a rua intacta."
        )

    references = contract["visual_references"]
    for field in ("start_frame", "start_frame_json", "end_frame", "end_frame_json"):
        path = Path(str(references.get(field) or ""))
        if not path.is_file():
            raise RuntimeError(
                f"BLOQUEADO {take['id']}_{take['slug']}: referencia obrigatoria ausente: {field}={path}"
            )


def resolve_take_duration_seconds(take: dict, args: argparse.Namespace) -> int:
    """Duracao do take com piso obrigatorio (blindagem 2026-07-19).

    Regra do usuario: takes com pelo menos 6s. O piso so pode ser furado
    de forma deliberada com --allow-short-takes.
    """
    duration = int(take["target_duration_seconds"])
    if args.max_take_seconds > 0:
        duration = min(duration, args.max_take_seconds)
    if not args.allow_short_takes and duration < args.min_take_seconds:
        print(
            f"AVISO {take['id']}_{take['slug']}: duracao {duration}s abaixo do piso "
            f"{args.min_take_seconds}s; subindo para o piso. Use --allow-short-takes para furar."
        )
        duration = args.min_take_seconds
    return duration


def validate_steps_budget(args: argparse.Namespace) -> None:
    """Bloqueia render longo no escuro (Q8 24+ steps = 40min sem arquivo)."""
    if args.steps > MAX_STEPS_DEFAULT and not args.allow_high_steps:
        raise SystemExit(
            f"BLOQUEADO: steps={args.steps} acima do teto {MAX_STEPS_DEFAULT}. "
            "Steps alto no escuro ja custou 40min de GPU sem arquivo. "
            "Use --allow-high-steps apenas em comparativo tecnico isolado e documentado."
        )


def validate_geometry_rule(args: argparse.Namespace) -> None:
    """Regra ABSOLUTA do usuario (2026-07-19): nativo sempre 1280x720@30fps.

    Upscale/interpolacao e pos-processamento; nunca render nativo em outra
    geometria. Excecao deliberada: --allow-custom-geometry para laboratorio.
    """
    if args.allow_custom_geometry:
        return
    if (args.width, args.height, args.fps) != (1280, 720, 30):
        print(
            f"AVISO: geometria {args.width}x{args.height}@{args.fps} substituida pela regra "
            "absoluta 1280x720@30fps. Use --allow-custom-geometry apenas em teste deliberado."
        )
        args.width, args.height, args.fps = 1280, 720, 30


def png_pixel_width(path: Path) -> int:
    """Le a largura de um PNG pelo IHDR, sem dependencia de PIL."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return 0
    return int.from_bytes(header[16:20], "big")


def validate_base_image_resolution(take: dict, base_path: Path) -> None:
    """Rejeita imagem-base pixelada/pequena (incidente do preview v2)."""
    if base_path.suffix.lower() != ".png":
        return
    width = png_pixel_width(base_path)
    if 0 < width < MIN_BASE_IMAGE_WIDTH:
        raise RuntimeError(
            f"BLOQUEADO {take['id']}_{take['slug']}: imagem-base com {width}px de largura "
            f"(< {MIN_BASE_IMAGE_WIDTH}px). Preview montado com imagem pixelada ja foi "
            "reprovado uma vez. Gere base anime atual com --generate-keyframes."
        )


def preflight_studio_online() -> None:
    """Falha rapido se Studio/ComfyUI estiverem fora (pre-voo obrigatorio)."""
    try:
        payload = requests.get(f"{STUDIO}/api/generative/status", timeout=10).json()
    except Exception as exc:
        raise SystemExit(
            f"BLOQUEADO: Studio offline em {STUDIO} ({exc}). "
            "Suba o Studio antes de gastar GPU. Watchdog: Pemara Studio Generative Watchdog."
        )
    if not payload.get("ok") or not payload.get("comfy_online"):
        raise SystemExit(
            "BLOQUEADO: Studio respondeu, mas ComfyUI esta offline. "
            "Watchdog: Pemara ComfyUI Watchdog (1 min)."
        )


def anime_keyframe_prompt(take: dict) -> str:
    image_prompt = (take.get("image_prompt") or "").strip()
    if image_prompt:
        return image_prompt
    motion = take.get("motion_layers", {})
    return (
        "Modern cinematic anime keyframe for a game intro, 2020s anime film quality, "
        "clean line art, detailed painted background, dramatic lighting, 16:9 composition, "
        "no pixel art, no retro pixels, no low resolution. "
        f"Scene objective: {take.get('objective', '')}. "
        f"Visual objects and motion plan: {json.dumps(motion, ensure_ascii=False)}. "
        f"Scene prompt: {take.get('animation_prompt', '')}. "
        "Single approved keyframe only, no text, no watermark, no characters, no humans, "
        "no faces, no eyes, no humanoid silhouettes."
    )


def _contract_value(contract: dict, key: str, default: str = "") -> str:
    value = contract.get(key, default)
    if isinstance(value, str):
        return value.strip()
    return str(value).strip() if value is not None else default


def build_video_prompt(take: dict, args: argparse.Namespace) -> str:
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file:
        prompt = Path(prompt_file).read_text(encoding="utf-8-sig").strip()
        if not prompt:
            raise RuntimeError(f"BLOQUEADO: arquivo de prompt vazio: {prompt_file}")
        return prompt
    motion_prefix = MOTION_PREFIXES.get(args.motion_profile, CONTROLLED_VIDEO_PREFIX)
    prompt_prefix = (args.prompt_prefix or "").strip()
    contract = take.get("shot_contract") or {}
    if not isinstance(contract, dict):
        contract = {}

    if contract:
        camera = contract.get("camera") or {}
        beats = contract.get("motion_beats") or {}
        references = contract.get("visual_references") or {}
        variants = contract.get("variants") or {}
        parts = [
            prompt_prefix,
            VEOKLING_VIDEO_PREFIX,
            motion_prefix,
            f"Subject: {_contract_value(contract, 'subject')}.",
            f"Action: {_contract_value(contract, 'action')}.",
            f"Scene: {_contract_value(contract, 'scene')}.",
            (
                "Camera: "
                f"{_contract_value(camera, 'movement')}; angle {_contract_value(camera, 'angle')}; "
                f"lens {_contract_value(camera, 'lens')}; focus {_contract_value(camera, 'focus')}. "
                "The camera move must be physically visible, not only a digital zoom."
            ),
            f"Lighting: {_contract_value(contract, 'lighting')}.",
            f"Mood: {_contract_value(contract, 'mood')}.",
            (
                "Motion beats: "
                f"start {_contract_value(beats, 'start')}; "
                f"middle {_contract_value(beats, 'middle')}; "
                f"end {_contract_value(beats, 'end')}."
            ),
            (
                "Visual reference rule: preserve the approved start frame exactly. "
                f"End-frame target: {_contract_value(references, 'end_frame_note', 'use the end motion beat as the final state')}."
            ),
            (
                "Variant rule: this is one short candidate take; it must be judged by QC before final. "
                f"Target duration: {variants.get('duration_seconds') or take.get('target_duration_seconds')} seconds."
            ),
            take.get("animation_prompt", ""),
        ]
        return " ".join(part for part in parts if part).strip()

    return " ".join(part for part in [prompt_prefix, motion_prefix, take["animation_prompt"]] if part).strip()


def build_video_negative(queue_negative: str, take: dict) -> str:
    contract = take.get("shot_contract") or {}
    contract_rules = contract.get("negative_rules") if isinstance(contract, dict) else []
    pieces = [queue_negative, VEOKLING_NEGATIVE, "pixel art, pixelated, retro sprite, low resolution, static keyframe, image loop"]
    if isinstance(contract_rules, list):
        pieces.extend(str(rule) for rule in contract_rules)
    seen: set[str] = set()
    clean: list[str] = []
    for chunk in pieces:
        for item in str(chunk).split(","):
            rule = item.strip()
            key = rule.lower()
            if rule and key not in seen:
                clean.append(rule)
                seen.add(key)
    return ", ".join(clean)


def post_image_job(take: dict, args: argparse.Namespace, negative: str, run_tag: str = "") -> str:
    data = {
        "prompt": anime_keyframe_prompt(take),
        "mode": "image",
        "model": args.image_model,
        "negative": negative + ", pixel art, pixelated, retro sprite, low resolution, slideshow",
        "lora": "",
        "lora_strength": "0",
        "width": str(args.width),
        "height": str(args.height),
        "steps": str(args.image_steps),
        "guidance": str(args.image_guidance),
        "seed": str(args.seed),
    }
    response = requests.post(f"{STUDIO}/api/generative/job", data=data, timeout=60)
    response.raise_for_status()
    payload = response.json()
    WORK.mkdir(parents=True, exist_ok=True)
    ledger_file("job_keyframe", take, run_tag).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload["job_id"]


def post_job(take: dict, args: argparse.Namespace, negative: str, run_tag: str = "") -> str:
    duration = resolve_take_duration_seconds(take, args)
    if args.pemara_estudo_40anos if False else False:
        pass  # placate linter; below block conditionally compiled
    # pemara_estudio_40anos: 81 frames nativos do Wan A14B (sweet-spot) nao importa duracao do take.
    if getattr(args, "pemara_estudio_40anos", False):
        frames = 81
    else:
        frames = max(25, int(duration * args.fps) + 1)
    prompt = build_video_prompt(take, args)
    negative_prompt = build_video_negative(negative, take)
    data = {
        "prompt": prompt,
        "mode": "video",
        "model": args.model,
        "negative": negative_prompt,
        "lora": args.lora,
        "lora_strength": str(args.lora_strength),
        "width": str(args.width),
        "height": str(args.height),
        "steps": str(args.steps),
        "guidance": str(args.guidance),
        "seed": str(args.seed),
        "frames": str(frames),
        "fps": str(args.fps),
        "camera_pose": args.camera_pose,
        "camera_speed": str(args.camera_speed),
    }
    base_file = take.get("base_image", {}).get("file") or ""
    files = None
    handle = None
    try:
        if base_file:
            base_path = Path(base_file)
            if base_path.exists():
                handle = base_path.open("rb")
                files = {"base_image": (base_path.name, handle, "image/png")}

        response = requests.post(f"{STUDIO}/api/generative/job", data=data, files=files, timeout=60)
    finally:
        if handle:
            handle.close()
    response.raise_for_status()
    payload = response.json()
    WORK.mkdir(parents=True, exist_ok=True)
    ledger_file("job", take, run_tag).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload["job_id"]


def wait_job(job_id: str, take: dict, run_tag: str = "", ledger_kind: str = "status") -> dict:
    last_message = None
    while True:
        payload = requests.get(f"{STUDIO}/api/generative/job/{job_id}", timeout=20).json()
        message = f"{payload.get('status')} {payload.get('progress')}% {payload.get('message')}"
        if message != last_message:
            print(f"{take['id']}_{take['slug']}: {message}")
            last_message = message
        if payload.get("status") in {"done", "error"}:
            ledger_file(ledger_kind, take, run_tag).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return payload
        time.sleep(20)


def generate_keyframe(take: dict, args: argparse.Namespace, negative: str, run_tag: str) -> Path:
    job_id = post_image_job(take, args, negative, run_tag)
    status = wait_job(job_id, take, run_tag, "status_keyframe")
    if status.get("status") != "done":
        raise RuntimeError(f"Erro ao gerar keyframe {take['id']}_{take['slug']}: {status.get('error') or status.get('message')}")
    src = first_output_path(status, {"image"})
    dst_dir = ENGINE_PROJECT / "base_images"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"take{take['id']}_{take['slug']}_anime_{run_tag}{src.suffix.lower() or '.png'}"
    shutil.copy2(src, dst)
    metadata = {
        "schema_version": "1.0",
        "project_id": "intro_ritmos_revolta",
        "type": "anime_keyframe_validation",
        "take_id": take["id"],
        "take_slug": take["slug"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "image_file": dst.as_posix(),
        "source_output": src.as_posix(),
        "model": args.image_model,
        "seed": args.seed,
        "width": args.width,
        "height": args.height,
        "prompt": anime_keyframe_prompt(take),
        "negative": negative + ", pixel art, pixelated, retro sprite, low resolution, slideshow",
        "objective": take.get("objective", ""),
        "required_objects": take.get("motion_layers", {}),
        "validation_status": "pending_human_qc",
        "approval_required_before_video": True,
        "qc_checklist": [
            "anime atual/cinematografico, sem pixel art",
            "composicao 16:9 coerente com o take",
            "objetos principais presentes e reconheciveis",
            "sem humanos, corpos, rostos, olhos ou silhuetas humanoides",
            "sem texto inventado, watermark ou UI",
            "espaco visual suficiente para movimento real no I2V",
        ],
        "rejection_reasons": [],
    }
    meta_path = dst.with_suffix(".json")
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    take.setdefault("base_image", {})
    take["base_image"].update(
        {
            "status": "pending_human_qc",
            "model": args.image_model,
            "prompt": anime_keyframe_prompt(take),
            "file": dst.as_posix(),
            "metadata": meta_path.as_posix(),
        }
    )
    print(f"KEYFRAME={dst}")
    print(f"KEYFRAME_JSON={meta_path}")
    return dst


def convert_clip(src: Path, dst: Path, width: int, height: int, fps: int) -> None:
    encoder_probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=True,
    )
    if "h264_nvenc" not in encoder_probe.stdout:
        raise RuntimeError(
            "BLOQUEADO: este FFmpeg nao oferece o encoder h264_nvenc. "
            "A conversao foi interrompida; fallback silencioso para CPU e proibido."
        )

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
        ),
        "-fps_mode",
        "cfr",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-tune",
        "hq",
        "-rc",
        "vbr",
        "-cq",
        "18",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "erro desconhecido").strip()
        raise RuntimeError(
            "BLOQUEADO: H.264 NVENC esta indisponivel ou falhou durante a conversao; "
            "nenhum fallback para encoder CPU foi executado. "
            f"FFmpeg: {detail[-2000:]}"
        )


def concat(clips: list[Path], dst: Path) -> None:
    list_file = WORK / f"take_queue_concat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    list_file.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in clips), encoding="utf-8")
    subprocess.run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(dst),
    ], check=True)


def write_take_metadata(
    take: dict,
    dst: Path,
    src: Path,
    job_id: str,
    status: dict,
    base_path: Path,
    base_metadata_path: Path,
    args: argparse.Namespace,
    negative: str,
) -> Path:
    duration = resolve_take_duration_seconds(take, args)
    # Keep the sidecar aligned with the exact native request sent by
    # --pemara-estudio-40anos (81 frames), rather than the legacy 6 s floor.
    if getattr(args, "pemara_estudio_40anos", False):
        frames = 81
    else:
        frames = max(25, int(duration * args.fps) + 1)
    prompt = build_video_prompt(take, args)
    negative_prompt = build_video_negative(negative, take)
    metadata = {
        "schema_version": "1.0",
        "project_id": "intro_ritmos_revolta",
        "type": "video_take_generation",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "take_id": take["id"],
        "take_slug": take["slug"],
        "timeline_start_seconds": take.get("timeline_start_seconds"),
        "target_duration_seconds": take.get("target_duration_seconds"),
        "output_file": dst.as_posix(),
        "source_output": src.as_posix(),
        "base_image": base_path.as_posix(),
        "base_image_metadata": base_metadata_path.as_posix(),
        "studio_job_id": job_id,
        "studio_status": {
            "status": status.get("status"),
            "progress": status.get("progress"),
            "message": status.get("message"),
            "error": status.get("error"),
        },
        "model": args.model,
        "lora": args.lora,
        "lora_strength": args.lora_strength,
        "motion_profile": args.motion_profile,
        "camera_pose": args.camera_pose,
        "camera_speed": args.camera_speed,
        "provider_profile": "veo_kling_shot_contract" if take.get("shot_contract") else "legacy_motion_prompt",
        "shot_contract": take.get("shot_contract", {}),
        "prompt_file": args.prompt_file.as_posix() if args.prompt_file else "",
        "prompt_override": bool(args.prompt_file),
        "queue_contract_note": (
            "The prompt file supersedes conflicting camera/motion prose in the queue sidecar; "
            "the explicit CLI camera pose and speed are authoritative for Fun Camera."
            if args.prompt_file else ""
        ),
        "prompt_prefix": args.prompt_prefix,
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "frames_requested": frames,
        "steps": args.steps,
        "guidance": args.guidance,
        "seed": args.seed,
        "prompt": prompt,
        "negative": negative_prompt,
        "motion_layers": take.get("motion_layers", {}),
        "qc_status": "awaiting_user_evaluation" if getattr(args, "pemara_estudio_40anos", False) else "pending_human_qc",
        "qc_required": (
            [
                "ffprobe duration/resolution/fps/frame count (esperado: 480p x 16fps x 81 frames, duracao 5.06s)",
                "contact sheet with beginning/middle/end",
                "verify motion event with beginning, middle and end",
                "verify no hallucinated character, text or watermark",
                "APROVACAO HUMANA OBRIGATORIA antes de RIFE+Real-ESRGAN para 1080p30",
            ]
            if getattr(args, "pemara_estudio_40anos", False)
            else [
                "ffprobe duration/resolution/fps/frame count",
                "contact sheet with beginning/middle/end",
                "verify motion event with beginning, middle and end",
                "verify no hallucinated character, text, watermark or black artifact",
                "approve or reject before assembly/final training",
            ]
        ),
    }
    metadata_path = dst.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"TAKE_JSON={metadata_path}")
    return metadata_path


def write_assembly_metadata(final: Path, clips: list[Path], args: argparse.Namespace, run_tag: str) -> Path:
    metadata = {
        "schema_version": "1.0",
        "project_id": "intro_ritmos_revolta",
        "type": "video_preview_assembly",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "run_tag": run_tag,
        "output_file": final.as_posix(),
        "clips": [
            {
                "file": clip.as_posix(),
                "metadata": clip.with_suffix(".json").as_posix(),
            }
            for clip in clips
        ],
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "qc_status": "pending_human_qc",
        "rule": "assembly only from takes with JSON sidecars",
    }
    metadata_path = final.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ASSEMBLY_JSON={metadata_path}")
    return metadata_path


def write_queue_snapshot(queue: dict, run_tag: str) -> None:
    snapshot = WORK / f"take_queue_after_keyframes_{run_tag}.json"
    snapshot.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"QUEUE_SNAPSHOT={snapshot}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera takes da intro Ritmos da Revolta pela fila oficial.")
    parser.add_argument(
        "--queue-json",
        type=Path,
        default=QUEUE_FILE,
        help=f"Fila JSON a executar. Padrao: {QUEUE_FILE}",
    )
    parser.add_argument("--takes", nargs="*", default=["01", "02", "03", "04"], help="IDs ou slugs. Padrao: 01 02 03 04.")
    parser.add_argument("--all", action="store_true", help="Gera todos os takes.")
    parser.add_argument("--assemble", action="store_true", help="Monta um preview com os takes gerados nesta rodada.")
    parser.add_argument("--generate-keyframes", action="store_true", help="Gera novas imagens-base anime atual antes de animar.")
    parser.add_argument("--keyframes-only", action="store_true", help="Gera apenas imagens-base e nao roda video.")
    parser.add_argument("--allow-legacy-base", action="store_true", help="Permite usar imagens antigas de referencia. Nao recomendado.")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--max-take-seconds", type=int, default=0, help="Limita duracao por take nesta rodada. 0 usa a duracao oficial.")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance", type=float, default=7.0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--image-model", default=DEFAULT_IMAGE_MODEL)
    parser.add_argument("--image-steps", type=int, default=32)
    parser.add_argument("--image-guidance", type=float, default=3.5)
    parser.add_argument("--lora", default=DEFAULT_LORA)
    parser.add_argument("--lora-strength", type=float, default=0.12)
    parser.add_argument(
        "--motion-profile",
        choices=sorted(MOTION_PREFIXES),
        default="controlled",
        help="controlled preserva fidelidade; aggressive forca movimento e pode alucinar mais.",
    )
    parser.add_argument("--prompt-prefix", default="", help="Prefixo opcional antes do prompt, ex: trigger de Motion LoRA.")
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="Arquivo UTF-8 que substitui integralmente o prompt da fila para o take selecionado.",
    )
    parser.add_argument(
        "--camera-pose",
        choices=("", "Static", "Pan Up", "Pan Down", "Pan Left", "Pan Right", "Zoom In", "Zoom Out", "Anti Clockwise (ACW)", "ClockWise (CW)"),
        default="",
        help="Trajetoria explicita para Wan2.2 Fun Camera; ignorada pelos demais modelos.",
    )
    parser.add_argument(
        "--camera-speed",
        type=float,
        default=0.8,
        help="Velocidade da trajetoria Wan2.2 Fun Camera (0 a 10).",
    )
    parser.add_argument("--ignore-video-pause", action="store_true", help="Permite rodar mesmo com a flag de pausa de video ativa.")
    parser.add_argument("--run-label", default="", help="Rotulo seguro anexado ao timestamp da rodada, ex: a14b_q4_motion.")
    parser.add_argument("--min-take-seconds", type=int, default=MIN_TAKE_SECONDS_DEFAULT, help="Piso de duracao por take (padrao 6s).")
    parser.add_argument("--allow-short-takes", action="store_true", help="Permite takes abaixo do piso de --min-take-seconds (teste deliberado).")
    parser.add_argument("--allow-high-steps", action="store_true", help="Permite steps acima do teto anti-desperdicio (comparativo tecnico isolado).")
    parser.add_argument("--allow-custom-geometry", action="store_true", help="Permite furar a regra absoluta 1280x720@30fps (laboratorio deliberado).")
    parser.add_argument("--pemara-estudio-40anos", action="store_true", help="Ativa o pipeline pemara_estudio_40anos: Wan renderiza 480p/16fps/81f nativo para avaliacao humana. Upscale postergado a apos o usuario aprovar.")
    parser.add_argument("--dry-run", action="store_true", help="Valida fila, contrato, keyframes e parametros sem enviar job nem usar GPU.")
    args = parser.parse_args()

    if args.prompt_file:
        args.prompt_file = args.prompt_file.resolve()
        if not args.prompt_file.is_file():
            parser.error(f"arquivo de prompt nao encontrado: {args.prompt_file}")

    # pemara_estudio_40anos: quando ativado, sobrescreve geometria/fps/steps para o sweet-spot do Wan A14B.
    # A saida final 1920x1080@30fps e' obtida por RIFE+Real-ESRGAN em pos-processamento, apos aprovacao humana.
    if args.pemara_estudio_40anos:
        args.width = 832
        args.height = 480
        args.fps = 16
        args.steps = 20
        args.guidance = 5.0
        args.allow_custom_geometry = True  # o Studio checa a flag pemara_40anos, nao este param.
        # O runner NAO aplica upscale/RIFE; entrega o preview 480p direto para avaliacao humana.

    validate_steps_budget(args)
    validate_geometry_rule(args)

    if not args.keyframes_only and not args.dry_run and video_generation_paused() and not args.ignore_video_pause:
        print(video_pause_message())
        return 9

    if not args.keyframes_only and not args.dry_run:
        preflight_studio_online()

    queue = load_queue(args.queue_json)
    takes = queue["takes"] if args.all else selected_takes(queue, args.takes)
    if not takes:
        print("Nenhum take selecionado.")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = safe_run_label(args.run_label)
    if label:
        run_tag = f"{run_tag}_{label}"
    negative = ", ".join(queue["global_negative_rules"])
    generated: list[Path] = []

    for take in takes:
        if args.generate_keyframes or base_image_is_legacy(take):
            if not args.generate_keyframes and not args.allow_legacy_base:
                print(
                    f"BLOQUEADO {take['id']}_{take['slug']}: imagem-base antiga/pixel/reference detectada. "
                    "Rode com --generate-keyframes para criar base anime atual."
                )
                return 3
            if args.generate_keyframes:
                generate_keyframe(take, args, negative, run_tag)

        if args.keyframes_only:
            continue

        base_file = take.get("base_image", {}).get("file") or ""
        base_status = (take.get("base_image", {}).get("status") or "").lower()
        if base_status not in {"approved", "approved_keyframe", "approved_for_video"} and not args.allow_legacy_base:
            print(
                f"BLOQUEADO {take['id']}_{take['slug']}: imagem-base esta como '{base_status}'. "
                "Valide o JSON/imagem e marque como approved_for_video antes de animar."
            )
            return 5
        if not base_file or not Path(base_file).exists():
            print(f"BLOQUEADO {take['id']}_{take['slug']}: sem imagem-base aprovada existente.")
            return 4

        base_path = Path(base_file)
        validate_base_image_resolution(take, base_path)
        try:
            base_metadata_path, _base_metadata = validate_base_image_json(take, base_path)
        except RuntimeError as exc:
            print(str(exc))
            return 6
        print(f"BASE_IMAGE_JSON={base_metadata_path}")
        try:
            validate_cinematic_contract(take)
        except RuntimeError as exc:
            print(str(exc))
            return 7

        if args.dry_run:
            duration = resolve_take_duration_seconds(take, args)
            frames = 81 if getattr(args, "pemara_estudio_40anos", False) else max(25, int(duration * args.fps) + 1)
            print(
                "DRY_RUN="
                + json.dumps(
                    {
                        "take": f"{take['id']}_{take['slug']}",
                        "base_image": base_path.as_posix(),
                        "base_image_metadata": base_metadata_path.as_posix(),
                        "model": args.model,
                        "width": args.width,
                        "height": args.height,
                        "fps": args.fps,
                        "frames": frames,
                        "steps": args.steps,
                        "guidance": args.guidance,
                        "seed": args.seed,
                        "motion_profile": args.motion_profile,
                        "camera_pose": args.camera_pose,
                        "camera_speed": args.camera_speed,
                        "prompt_file": args.prompt_file.as_posix() if args.prompt_file else "",
                        "postprocess": "disabled_pending_human_approval",
                    },
                    ensure_ascii=False,
                )
            )
            continue

        job_id = post_job(take, args, negative, run_tag)
        status = wait_job(job_id, take, run_tag)
        if status.get("status") != "done":
            print(f"ERRO {take['id']}_{take['slug']}: {status.get('error') or status.get('message')}")
            return 2
        src = first_output_path(status, {"video"})
        if getattr(args, "pemara_estudio_40anos", False):
            # pemara_estudio_40anos: entrega o preview 480p nativo direto ao usuario.
            # NAO aplica upscale (RIFE/Real-ESRGAN) ate o usuario aprovar.
            dst = OUT / f"intro_take_{take['id']}_{take['slug']}_{run_tag}_preview_480p_16fps_81f.mp4"
            shutil.copyfile(src, dst)
            print(f"PEMARA_40ANOS_PREVIEW (avaliar e aprovar): {dst}")
        else:
            dst = OUT / f"intro_take_{take['id']}_{take['slug']}_{run_tag}.mp4"
            convert_clip(src, dst, args.width, args.height, args.fps)
        write_take_metadata(take, dst, src, job_id, status, base_path, base_metadata_path, args, negative)
        generated.append(dst)
        print(f"OK={dst}")

    if args.generate_keyframes:
        write_queue_snapshot(queue, run_tag)

    if args.assemble and generated:
        final = ENGINE_PROJECT / "output" / f"intro_preview_{run_tag}.mp4"
        final.parent.mkdir(parents=True, exist_ok=True)
        concat(generated, final)
        write_assembly_metadata(final, generated, args, run_tag)
        print(f"ASSEMBLY={final}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
