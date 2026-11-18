"""Executa pedidos ANCHOR pendentes de um projeto do Maestro, um por vez.

O painel Maestro registra o pedido antes de iniciar a GPU por uma rota explicita.
Este executor supervisionado consome somente pedidos ANCHOR PENDING. Ele pode
editar uma imagem oficial ou gerar uma candidata do zero quando o contrato do
take declarar ``generation_mode=text_to_image``. A entrega usa a rota canonica,
mantem a revisao humana obrigatoria e retoma o lote apos falhas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


VIDEO_ENGINE_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = (VIDEO_ENGINE_ROOT / "projetos").resolve()
PROJECT_DIR = Path.cwd().resolve()
PROJECT_ID = PROJECT_DIR.name
QUEUE_FILE = PROJECT_DIR / "take_queue.json"
COMFY_OUTPUT_ROOT = (VIDEO_ENGINE_ROOT.parent / "ComfyUI" / "output").resolve()
DEFAULT_STUDIO_URL = "http://127.0.0.1:8029"
EDIT_MODEL = "qwen_image_edit_2511_fp8mixed.safetensors"
TEXT_MODEL = "qwen_image_2512_fp8_e4m3fn.safetensors"
TEXT_LORA = "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"
WIDTH = 1536
HEIGHT = 864
EDIT_STEPS = 40
EDIT_GUIDANCE = 4.0
TEXT_STEPS = 4
TEXT_GUIDANCE = 1.0
NETWORK_ATTEMPTS = 12
NETWORK_RETRY_SECONDS = 5
START_ATTEMPTS = 3
RESUMABLE_JOB_STATUSES = {"queued", "running", "canceling", "done"}
NEGATIVE = (
    "people, person, human, character, humanoid silhouette, body, face, eyes, "
    "hands, animal, extra objects, duplicated objects, new architecture, "
    "readable text, letters, logo, watermark, UI, photorealism, 3D render, "
    "pixel art, blur, fog wash, warped geometry, melted objects, digital zoom, crop, "
    "picture frame, photo frame, decorative frame, border, mat, card, poster, "
    "inset image, screenshot, black bars, letterbox, pillarbox"
)


class ExecutorAlreadyRunningError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_project(project_dir: Path) -> None:
    global PROJECT_DIR, PROJECT_ID, QUEUE_FILE
    resolved = project_dir.resolve()
    if resolved.parent != PROJECTS_ROOT or not resolved.is_dir():
        raise ValueError("Diretorio de projeto invalido para o executor ANCHOR.")
    queue_file = resolved / "take_queue.json"
    if not queue_file.is_file():
        raise FileNotFoundError(f"Fila canonica ausente: {queue_file}")
    PROJECT_DIR = resolved
    PROJECT_ID = resolved.name
    QUEUE_FILE = queue_file


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def acquire_executor_lock() -> Path:
    lock_path = PROJECT_DIR / "tools" / "anchor_executor.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for _attempt in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                payload = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                payload = {}
            existing_pid = int(payload.get("pid", 0) or 0)
            if pid_is_running(existing_pid):
                raise ExecutorAlreadyRunningError(
                    f"Executor ANCHOR ja esta ativo no PID {existing_pid}."
                )
            lock_path.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "pid": os.getpid(),
                    "project_id": PROJECT_ID,
                    "started_at": utc_now(),
                },
                handle,
                ensure_ascii=False,
            )
            handle.flush()
            os.fsync(handle.fileno())
        return lock_path
    raise RuntimeError("Nao foi possivel adquirir o lock do executor ANCHOR.")


def created_at_timestamp(value: Any) -> float:
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def get_json_with_retry(
    session: requests.Session,
    url: str,
    *,
    timeout: int = 30,
    attempts: int = NETWORK_ATTEMPTS,
    retry_seconds: int = NETWORK_RETRY_SECONDS,
) -> dict[str, Any]:
    for attempt in range(1, max(1, attempts) + 1):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError(f"Resposta JSON inesperada de {url}.")
            return payload
        except (requests.ConnectionError, requests.Timeout):
            if attempt >= max(1, attempts):
                raise
            logging.warning(
                "Studio indisponivel em %s (tentativa %d/%d); nova tentativa em %ds.",
                url,
                attempt,
                attempts,
                retry_seconds,
            )
            time.sleep(max(0, retry_seconds))
    raise RuntimeError(f"Falha inesperada consultando {url}.")


def load_queue() -> dict[str, Any]:
    return json.loads(QUEUE_FILE.read_text(encoding="utf-8-sig"))


def pending_requests() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    queue = load_queue()
    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for take in queue.get("takes", []):
        if not isinstance(take, dict):
            continue
        requests_list = take.get("maestro_director_requests")
        if not isinstance(requests_list, list):
            continue
        for request in requests_list:
            if not isinstance(request, dict):
                continue
            if (
                str(request.get("category") or "").upper() == "ANCHOR"
                and str(request.get("status") or "").upper() == "PENDING"
            ):
                pending.append((take, request))
    pending.sort(key=lambda pair: (str(pair[0].get("id") or ""), str(pair[1].get("created_at") or "")))
    return pending


def generation_mode(take: dict[str, Any]) -> str:
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    requested = str(
        base.get("generation_mode")
        or take.get("anchor_generation_mode")
        or "image_edit"
    ).strip().lower()
    if requested in {"text_to_image", "text2image", "t2i", "image"}:
        return "text_to_image"
    return "image_edit"


def anchor_source(take: dict[str, Any]) -> Path | None:
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if generation_mode(take) == "text_to_image":
        return None
    source = Path(str(base.get("source_approved_image") or base.get("file") or "")).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Imagem oficial ausente: {source}")
    return source


def build_prompt(take: dict[str, Any], request: dict[str, Any] | None = None) -> str:
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    stored_prompt = str(
        base.get("prompt")
        or take.get("image_prompt")
        or ""
    ).strip()
    if stored_prompt:
        # Project-specific prompts are authoritative for both text-to-image and
        # image-edit jobs.  The legacy fallback below remains intentionally
        # environmental for the older Ritmos transition projects.
        constructive_correction = str(base.get("correction_prompt") or "").strip()
        request_reason = str((request or {}).get("reason") or "").strip()
        if (
            not constructive_correction
            and request_reason
            and not request_reason.casefold().startswith("preparar uma imagem")
            and not request_reason.casefold().startswith("produzir a nova foto")
        ):
            constructive_correction = request_reason
        return (
            f"{stored_prompt} Constructive revision: {constructive_correction}"
            if constructive_correction
            else stored_prompt
        )
    if generation_mode(take) == "text_to_image":
        raise ValueError(
            f"Take {take.get('id') or ''} usa texto-para-imagem sem prompt salvo."
        )

    contract = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
    camera = contract.get("camera") if isinstance(contract.get("camera"), dict) else {}
    action = str(contract.get("action") or take.get("objective") or "").strip()
    scene = str(contract.get("scene") or "").strip()
    movement = str(camera.get("movement") or "").strip()
    take_id = str(take.get("id") or "")
    request_reason = str((request or {}).get("reason") or "").strip()
    correction = (
        request_reason
        if request_reason and not request_reason.casefold().startswith("preparar uma imagem")
        else ""
    )
    correction_instruction = (
        f" Director correction that must be obeyed: {correction}. "
        "Do not repeat that rejected composition or defect."
        if correction
        else ""
    )
    return (
        "Create a new cinematic 16:9 modern anime anchor frame from the supplied approved "
        f"environment for take {take_id}. Preserve the exact same empty world, "
        "object identities, architecture, palette, lighting and crisp 2D digital-painting "
        "linework while creating a genuinely new physical camera viewpoint. "
        f"Scene direction: {scene}. Camera movement and viewpoint: {movement}. "
        f"Visible environmental action: {action}.{correction_instruction} "
        "Keep clear foreground, middle-ground and background separation. This must be a new "
        "viewpoint, not a crop or digital zoom. Render a full-bleed, edge-to-edge scene that "
        "fills the entire 16:9 canvas; never place it inside a picture frame, decorative border, "
        "card, poster, inset, screen, matte, letterbox or pillarbox. Empty environment only; "
        "no people, characters, "
        "faces, silhouettes, animals, extra objects, duplicated objects, new architecture, "
        "readable text, logo, watermark, UI, photorealism, 3D render, blur wash or distorted geometry."
    )


def negative_prompt(take: dict[str, Any]) -> str:
    """Resolve a project-specific negative prompt without changing legacy jobs."""

    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    configured = str(
        base.get("negative_prompt")
        or take.get("image_negative_prompt")
        or ""
    ).strip()
    return configured or NEGATIVE


def find_matching_job(
    session: requests.Session,
    studio_url: str,
    *,
    prompt: str,
    source: Path | None,
    mode: str,
    model: str,
    not_before: float,
) -> dict[str, Any] | None:
    payload = get_json_with_retry(
        session,
        f"{studio_url}/api/generative/jobs?page=1&page_size=100&mode={mode}",
    )
    expected_base_name = source.name if source is not None else ""
    matches = [
        job
        for job in payload.get("items", [])
        if isinstance(job, dict)
        and str(job.get("status") or "") in RESUMABLE_JOB_STATUSES
        and str(job.get("prompt") or "") == prompt
        and str(job.get("base_image_name") or "") == expected_base_name
        and str(job.get("model") or "") == model
        and float(job.get("created_at", 0) or 0) >= not_before
    ]
    if not matches:
        return None
    return max(matches, key=lambda job: float(job.get("created_at", 0) or 0))


def start_job(
    session: requests.Session,
    studio_url: str,
    prompt: str,
    source: Path | None,
    *,
    mode: str,
    model: str,
    negative: str,
    seed: int,
    not_before: float,
) -> str:
    existing = find_matching_job(
        session,
        studio_url,
        prompt=prompt,
        source=source,
        mode=mode,
        model=model,
        not_before=not_before,
    )
    if existing:
        job_id = str(existing.get("job_id") or "").strip()
        if job_id:
            logging.info(
                "retomando job=%s status=%s para base=%s",
                job_id,
                existing.get("status"),
                source.name if source is not None else "text-only",
            )
            return job_id

    text_to_image = mode == "image"
    data = {
        "prompt": prompt,
        "mode": mode,
        "model": model,
        "negative": negative,
        "lora": TEXT_LORA if text_to_image else "",
        "lora_strength": "1" if text_to_image else "0",
        "width": str(WIDTH),
        "height": str(HEIGHT),
        "steps": str(TEXT_STEPS if text_to_image else EDIT_STEPS),
        "guidance": str(TEXT_GUIDANCE if text_to_image else EDIT_GUIDANCE),
        "seed": str(seed),
        "frames": "601",
        "fps": "30",
        "provider": "",
        "duration": "30",
        "prompt_influence": "0.5",
        "loop": "false",
        "camera_pose": "",
        "camera_speed": "0.8",
        "video_conditioning_profile": "identity_locked",
    }
    for attempt in range(1, START_ATTEMPTS + 1):
        try:
            if source is None:
                response = session.post(
                    f"{studio_url}/api/generative/job",
                    data=data,
                    timeout=120,
                )
            else:
                with source.open("rb") as handle:
                    response = session.post(
                        f"{studio_url}/api/generative/job",
                        data=data,
                        files={"base_image": (source.name, handle, "image/png")},
                        timeout=120,
                    )
            response.raise_for_status()
            job_id = str(response.json().get("job_id") or "").strip()
            if not job_id:
                raise RuntimeError(f"Studio nao devolveu job_id: {response.text[:500]}")
            return job_id
        except (requests.ConnectionError, requests.Timeout):
            recovered = find_matching_job(
                session,
                studio_url,
                prompt=prompt,
                source=source,
                mode=mode,
                model=model,
                not_before=not_before,
            )
            recovered_id = str((recovered or {}).get("job_id") or "").strip()
            if recovered_id:
                logging.info(
                    "POST perdeu a resposta, mas o job=%s foi localizado e sera retomado.",
                    recovered_id,
                )
                return recovered_id
            if attempt >= START_ATTEMPTS:
                raise
            logging.warning(
                "Falha de rede ao iniciar foto (tentativa %d/%d); nova tentativa em %ds.",
                attempt,
                START_ATTEMPTS,
                NETWORK_RETRY_SECONDS,
            )
            time.sleep(NETWORK_RETRY_SECONDS)
    raise RuntimeError("Falha inesperada ao iniciar job de foto-base.")


def wait_job(session: requests.Session, studio_url: str, job_id: str, poll_seconds: int) -> dict[str, Any]:
    while True:
        job = get_json_with_retry(
            session,
            f"{studio_url}/api/generative/job/{job_id}",
        )
        status = str(job.get("status") or "")
        logging.info("job=%s status=%s progress=%s message=%s", job_id, status, job.get("progress"), job.get("message"))
        if status not in {"queued", "running", "canceling"}:
            if status != "done":
                raise RuntimeError(f"Job {job_id} terminou como {status}: {job.get('error')}")
            return job
        time.sleep(poll_seconds)


def output_path(job: dict[str, Any]) -> Path:
    outputs = ((job.get("result") or {}).get("outputs") or [])
    image = next((item for item in outputs if item.get("kind") == "image"), None)
    if not image:
        raise RuntimeError(f"Job sem output de imagem: {job.get('job_id')}")
    subfolder = str(image.get("subfolder") or "")
    filename = str(image.get("filename") or "")
    candidate = (COMFY_OUTPUT_ROOT / subfolder / filename).resolve()
    if COMFY_OUTPUT_ROOT not in candidate.parents or not candidate.is_file():
        raise FileNotFoundError(f"Output invalido ou ausente: {candidate}")
    return candidate


def publish_candidate(
    session: requests.Session,
    studio_url: str,
    take: dict[str, Any],
    request: dict[str, Any],
    job: dict[str, Any],
    image: Path,
    prompt: str,
    *,
    mode: str,
    model: str,
    negative: str,
) -> None:
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    required_objects = (
        base.get("required_objects")
        if isinstance(base.get("required_objects"), dict)
        else {}
    )
    result = job.get("result") or {}
    outputs = result.get("outputs") or []
    output = next(item for item in outputs if item.get("kind") == "image")
    metadata = {
        "prompt": prompt,
        "model": str(result.get("model") or model),
        "negative": negative,
        "seed": result.get("seed"),
        "sourceOutput": str(output.get("filename") or ""),
        "sourceGeneratedAt": utc_now(),
        "sourceSha256": digest,
        "generator": "Maestro Studio / ComfyUI",
        "workflow": (
            f"Qwen Image 2512 text-to-image + Lightning; {WIDTH}x{HEIGHT}; "
            f"{TEXT_STEPS} steps; CFG {TEXT_GUIDANCE:g}"
            if mode == "image"
            else (
                f"Qwen Image Edit 2511; {WIDTH}x{HEIGHT}; "
                f"{EDIT_STEPS} steps; CFG {EDIT_GUIDANCE:g}"
            )
        ),
        "objective": f"Imagem-ancora dirigida para o take {take.get('id') or ''}.",
        "requiredObjects": required_objects,
    }
    target = f"{studio_url}/api/video-projects/{PROJECT_ID}/takes/{take['id']}/anchor-candidate"
    for attempt in range(1, NETWORK_ATTEMPTS + 1):
        try:
            with image.open("rb") as handle:
                response = session.post(
                    target,
                    data={
                        "requestId": str(request["id"]),
                        "metadata": json.dumps(metadata, ensure_ascii=False),
                    },
                    files={"image": (image.name, handle, "image/png")},
                    timeout=120,
                )
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("takeId") or "") != str(take.get("id") or ""):
                raise RuntimeError(f"Resposta inesperada ao publicar {take.get('id')}: {payload}")
            return
        except (requests.ConnectionError, requests.Timeout):
            if attempt >= NETWORK_ATTEMPTS:
                raise
            logging.warning(
                "Entrega de %s perdeu conexao (tentativa %d/%d); repetindo de forma idempotente em %ds.",
                take.get("id"),
                attempt,
                NETWORK_ATTEMPTS,
                NETWORK_RETRY_SECONDS,
            )
            time.sleep(NETWORK_RETRY_SECONDS)
    raise RuntimeError(f"Falha inesperada ao publicar {take.get('id')}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa a fila de fotos-ancora do Maestro.")
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--base-url", default=os.environ.get("MAESTRO_STUDIO_URL", DEFAULT_STUDIO_URL))
    parser.add_argument("--take-id", action="append", default=[], help="Processa somente este take; pode repetir.")
    parser.add_argument("--max-takes", type=int, default=0, help="Limite desta rodada; 0 processa todos os pendentes.")
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument(
        "--intent-path",
        type=Path,
        help="Autorizacao persistida do lote; removida somente apos conclusao com sucesso.",
    )
    parser.add_argument(
        "--recover-only",
        action="store_true",
        help="Publica somente jobs ja concluidos; nunca inicia GPU nem aguarda jobs ativos.",
    )
    parser.add_argument("--log-file", type=Path)
    args = parser.parse_args()
    configure_project(args.project_dir)
    if args.intent_path is not None:
        args.intent_path = args.intent_path.resolve()
        expected_parent = (PROJECT_DIR / "tools").resolve()
        if args.intent_path.parent != expected_parent:
            parser.error("--intent-path deve ficar dentro de tools/ do projeto.")
    args.log_file = args.log_file or PROJECT_DIR / "tools" / "anchor_executor.log"

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(args.log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    try:
        lock_path = acquire_executor_lock()
    except ExecutorAlreadyRunningError as exc:
        logging.info("%s", exc)
        return 0
    completed_successfully = False
    try:
        selected = pending_requests()
        if args.take_id:
            wanted = {item.upper() for item in args.take_id}
            selected = [pair for pair in selected if str(pair[0].get("id") or "").upper() in wanted]
        if args.max_takes > 0:
            selected = selected[: args.max_takes]
        if not selected:
            logging.info("Nenhum pedido ANCHOR PENDING para executar.")
            completed_successfully = True
            return 0

        studio_url = str(args.base_url).rstrip("/")
        session = requests.Session()
        for index, (take, request) in enumerate(selected, start=1):
            take_id = str(take.get("id") or "")
            try:
                source = anchor_source(take)
                prompt = build_prompt(take, request)
                negative = negative_prompt(take)
                text_to_image = generation_mode(take) == "text_to_image"
                mode = "image" if text_to_image else "edit"
                model = TEXT_MODEL if text_to_image else EDIT_MODEL
                configured_seed = (
                    take.get("base_image", {}).get("seed")
                    if isinstance(take.get("base_image"), dict)
                    else None
                )
                seed = (
                    int(configured_seed)
                    if isinstance(configured_seed, int) and not isinstance(configured_seed, bool)
                    else -1
                )
                not_before = created_at_timestamp(request.get("created_at"))
                existing = find_matching_job(
                    session,
                    studio_url,
                    prompt=prompt,
                    source=source,
                    mode=mode,
                    model=model,
                    not_before=not_before,
                )
                if args.recover_only and (
                    existing is None or str(existing.get("status") or "") != "done"
                ):
                    logging.info("[%d/%d] sem job concluido para recuperar take=%s", index, len(selected), take_id)
                    continue
                logging.info(
                    "[%d/%d] iniciando ou retomando take=%s request=%s modo=%s base=%s",
                    index,
                    len(selected),
                    take_id,
                    request.get("id"),
                    mode,
                    source or "texto puro",
                )
                if existing is not None:
                    job_id = str(existing.get("job_id") or "")
                else:
                    job_id = start_job(
                        session,
                        studio_url,
                        prompt,
                        source,
                        mode=mode,
                        model=model,
                        negative=negative,
                        seed=seed,
                        not_before=not_before,
                    )
                job = (
                    existing
                    if existing is not None and str(existing.get("status") or "") == "done"
                    else wait_job(session, studio_url, job_id, max(1, args.poll_seconds))
                )
                image = output_path(job)
                publish_candidate(
                    session,
                    studio_url,
                    take,
                    request,
                    job,
                    image,
                    prompt,
                    mode=mode,
                    model=model,
                    negative=negative,
                )
                logging.info("[%d/%d] entregue take=%s job=%s output=%s", index, len(selected), take_id, job_id, image.name)
            except Exception:
                logging.exception("falha no take=%s; fila preservada para nova tentativa", take_id)
                return 1
        completed_successfully = True
        return 0
    finally:
        lock_path.unlink(missing_ok=True)
        if completed_successfully and args.intent_path is not None:
            args.intent_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
