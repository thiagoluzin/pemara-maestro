"""
daily_lora_cycle.py

Ciclo diario de treino da LoRA Sprunki.

Fluxo:
1. Monta um dataset versionado em experiments/<run>/dataset/img.
2. Usa ratings.json, quando existir, para separar gold/good/variants.
3. Normaliza captions com o gatilho sprunki_char.
4. Chama auto_train.py e salva logs/modelo no experimento.
5. Gera amostras de avaliacao em varias forcas de LoRA.
6. Respeita deadline para a janela diaria de treino.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_DATASET = ROOT / "lora_dataset" / "img" / "20_sprunki_char"
EXPERIMENTS_DIR = ROOT / "experiments"
LOG_DIR = ROOT / "logs"
LOCK_FILE = LOG_DIR / "daily_lora_cycle.lock"
LATEST_MODEL_DIR = ROOT / "lora_dataset" / "model"
COMFY_LORA_DIR = ROOT.parent / "ComfyUI" / "models" / "loras"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
BASE_CAPTION = (
    "sprunki_char, official Incredibox music game character sprite, "
    "simple 2d cartoon character, clean silhouette, full body, centered, "
    "flat colors, clean outline, white background"
)


def enforce_gpu_window(name: str) -> None:
    guard_root = Path(r"E:\Pemara")
    if str(guard_root) not in sys.path:
        sys.path.insert(0, str(guard_root))
    try:
        from gpu_window_guard import enforce

        enforce(name=name, kind="training")
    except SystemExit:
        raise
    except Exception as exc:
        log(f"[GPU-GUARD] Falha ao validar janela GPU; bloqueando por seguranca: {exc}")
        raise SystemExit(20)


def log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def parse_deadline(value: str | None) -> float | None:
    if not value:
        return None
    return datetime.fromisoformat(value).timestamp()


def ensure_no_lock(force: bool = False) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCK_FILE.exists():
        return

    try:
        payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        pid = int(payload.get("pid", 0))
    except Exception:
        pid = 0

    if force:
        LOCK_FILE.unlink(missing_ok=True)
        return

    if pid and is_pid_running(pid):
        raise RuntimeError(f"Outro ciclo ja esta rodando com PID {pid}.")

    LOCK_FILE.unlink(missing_ok=True)


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def write_lock(run_id: str) -> None:
    LOCK_FILE.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "run_id": run_id,
                "started_at": datetime.now().isoformat(timespec="seconds"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def load_ratings(dataset_dir: Path) -> dict[str, int]:
    ratings_file = dataset_dir / "ratings.json"
    if not ratings_file.exists():
        return {}
    try:
        raw = json.loads(ratings_file.read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in raw.items()}
    except Exception:
        return {}


def normalize_caption(text: str) -> str:
    text = " ".join((text or "").replace("\n", " ").split())
    if not text:
        return BASE_CAPTION
    if "sprunki_char" not in text:
        text = f"{BASE_CAPTION}, {text}"
    elif "official Incredibox music game character sprite" not in text:
        text = text.replace("sprunki_char", BASE_CAPTION, 1)
    return text


def bucket_for_rating(rating: int, has_ratings: bool) -> str:
    if has_ratings:
        if rating >= 5:
            return "30_sprunki_char_gold"
        if rating >= 4:
            return "20_sprunki_char_good"
        if rating >= 3:
            return "5_sprunki_char_variants"
        return ""
    return "20_sprunki_char_good"


def prepare_dataset(source_dir: Path, target_img_dir: Path) -> dict:
    if not source_dir.exists():
        raise FileNotFoundError(f"Dataset nao encontrado: {source_dir}")

    ratings = load_ratings(source_dir)
    has_ratings = bool(ratings)
    counts: dict[str, int] = {}
    copied = 0
    skipped = 0

    for image in sorted(source_dir.iterdir()):
        if image.suffix.lower() not in IMAGE_EXTS:
            continue

        rating = ratings.get(image.name, 0)
        bucket = bucket_for_rating(rating, has_ratings)
        if not bucket:
            skipped += 1
            continue

        dest_dir = target_img_dir / bucket
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_image = dest_dir / image.name
        shutil.copy2(image, dest_image)

        caption_src = image.with_suffix(".txt")
        caption = caption_src.read_text(encoding="utf-8", errors="ignore") if caption_src.exists() else ""
        dest_image.with_suffix(".txt").write_text(normalize_caption(caption), encoding="utf-8")

        counts[bucket] = counts.get(bucket, 0) + 1
        copied += 1

    if copied == 0:
        raise RuntimeError("Nenhuma imagem valida foi copiada para treino.")

    return {
        "source": str(source_dir),
        "target": str(target_img_dir),
        "has_ratings": has_ratings,
        "copied": copied,
        "skipped": skipped,
        "counts": counts,
    }


def run_command_until_deadline(cmd: list[str], cwd: Path, log_path: Path, deadline_ts: float | None) -> int:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    with log_path.open("w", encoding="utf-8", errors="ignore") as log_file:
        log_file.write(f"$ {' '.join(cmd)}\n\n")
        log_file.flush()

        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        while process.poll() is None:
            if deadline_ts and time.time() >= deadline_ts:
                log("Deadline atingido. Encerrando processo de treino.")
                terminate_process_tree(process)
                return 124
            time.sleep(15)

        return int(process.returncode or 0)


def terminate_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=60)
    except Exception:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except Exception:
            process.kill()


def copy_latest_model(output_dir: Path, run_dir: Path) -> dict:
    model = output_dir / "sprunki_lora.safetensors"
    if not model.exists():
        return {"status": "missing", "source": str(model)}

    LATEST_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    latest = LATEST_MODEL_DIR / "sprunki_lora_daily_latest.safetensors"
    local = run_dir / "sprunki_lora.safetensors"
    shutil.copy2(model, latest)
    shutil.copy2(model, local)

    result = {
        "status": "copied",
        "latest_model": str(latest),
        "experiment_model": str(local),
    }

    if COMFY_LORA_DIR.exists():
        comfy_name = f"sprunki_lora_{run_dir.name}.safetensors"
        comfy_target = COMFY_LORA_DIR / comfy_name
        shutil.copy2(model, comfy_target)
        result["comfy_eval_lora"] = comfy_name
        result["comfy_eval_path"] = str(comfy_target)

    return result


def run_eval_samples(
    experiment: str,
    python: str,
    count: int,
    strengths: str,
    lora_name: str,
    deadline_ts: float | None,
) -> dict:
    if count <= 0:
        return {"status": "skipped", "reason": "eval disabled"}

    if deadline_ts and time.time() >= deadline_ts:
        return {"status": "skipped", "reason": "deadline reached before eval"}

    cmd = [
        python,
        str(ROOT / "generate_lora_eval_samples.py"),
        "--experiment",
        experiment,
        "--count",
        str(count),
        "--strengths",
        strengths,
        "--lora-name",
        lora_name,
    ]
    log_path = EXPERIMENTS_DIR / experiment / "eval_samples.log"
    code = run_command_until_deadline(cmd, ROOT, log_path, deadline_ts)
    return {
        "status": "success" if code == 0 else "timeout" if code == 124 else "failed",
        "returncode": code,
        "log": str(log_path),
        "count": count,
        "strengths": strengths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ciclo diario de treino LoRA Sprunki")
    parser.add_argument("--deadline", default=None, help="ISO datetime final da janela. Ex: 2026-06-18T05:30:00")
    parser.add_argument("--steps", type=int, default=int(os.environ.get("SPRUNKI_LORA_STEPS", "900")))
    parser.add_argument("--dim", type=int, default=int(os.environ.get("SPRUNKI_LORA_DIM", "8")))
    parser.add_argument("--alpha", type=int, default=int(os.environ.get("SPRUNKI_LORA_ALPHA", "8")))
    parser.add_argument("--batch-size", type=int, default=int(os.environ.get("SPRUNKI_LORA_BATCH", "2")))
    parser.add_argument("--learning-rate", type=float, default=float(os.environ.get("SPRUNKI_LORA_LR", "0.00002")))
    parser.add_argument("--eval-samples", type=int, default=int(os.environ.get("SPRUNKI_LORA_EVAL_SAMPLES", "4")))
    parser.add_argument("--eval-strengths", default=os.environ.get("SPRUNKI_LORA_EVAL_STRENGTHS", "0.15,0.30,0.45"))
    parser.add_argument("--seed", type=int, default=int(os.environ.get("SPRUNKI_LORA_SEED", "42")))
    parser.add_argument("--flux-model", default=os.environ.get("SPRUNKI_FLUX_MODEL"))
    parser.add_argument("--run-prefix", default=os.environ.get("SPRUNKI_LORA_RUN_PREFIX", "lora"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Remove lock antigo antes de iniciar")
    args = parser.parse_args()

    deadline_ts = parse_deadline(args.deadline)
    if deadline_ts and time.time() >= deadline_ts:
        log("Fora da janela de treino. Nada a fazer.")
        return 0

    if not args.dry_run:
        enforce_gpu_window("sprunki-daily-lora-cycle")

    effective_prefix = "dryrun" if args.dry_run and args.run_prefix == "lora" else args.run_prefix
    safe_prefix = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in effective_prefix)
    run_id = datetime.now().strftime(f"{safe_prefix}_%Y%m%d_%H%M%S")
    run_dir = EXPERIMENTS_DIR / run_id
    dataset_img_dir = run_dir / "dataset" / "img"
    output_dir = run_dir / "model"
    train_log = run_dir / "train.log"

    ensure_no_lock(force=args.force)
    write_lock(run_id)

    try:
        log(f"Iniciando ciclo {run_id}")
        run_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        dataset_report = prepare_dataset(SOURCE_DATASET, dataset_img_dir)
        config = {
            "run_id": run_id,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "deadline": args.deadline,
            "steps": args.steps,
            "dim": args.dim,
            "alpha": args.alpha,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "eval_samples": args.eval_samples,
            "eval_strengths": args.eval_strengths,
            "seed": args.seed,
            "flux_model": args.flux_model,
            "dataset": dataset_report,
        }
        (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        log(f"Dataset preparado: {dataset_report['copied']} imagens em {dataset_report['counts']}")

        if args.dry_run:
            log("Dry-run concluido. Treino nao foi iniciado.")
            return 0

        cmd = [
            args.python,
            str(ROOT / "auto_train.py"),
            "--dataset",
            str(dataset_img_dir),
            "--output",
            str(output_dir),
            "--steps",
            str(args.steps),
            "--dim",
            str(args.dim),
            "--alpha",
            str(args.alpha),
            "--batch-size",
            str(args.batch_size),
            "--learning-rate",
            str(args.learning_rate),
            "--seed",
            str(args.seed),
        ]
        if args.flux_model:
            cmd.extend(["--flux-model", args.flux_model])

        code = run_command_until_deadline(cmd, ROOT, train_log, deadline_ts)
        status = "success" if code == 0 else "timeout" if code == 124 else "failed"
        log(f"Treino finalizado com status={status} code={code}")

        summary = {
            **config,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "returncode": code,
            "train_log": str(train_log),
        }

        if code == 0:
            model_copy = copy_latest_model(output_dir, run_dir)
            summary["model_copy"] = model_copy
            summary["latest_model"] = model_copy.get("latest_model")
            eval_lora_name = model_copy.get("comfy_eval_lora", "sprunki_lora.safetensors")
            summary["eval"] = run_eval_samples(
                run_id,
                args.python,
                args.eval_samples,
                args.eval_strengths,
                eval_lora_name,
                deadline_ts,
            )

        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return code
    finally:
        LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
