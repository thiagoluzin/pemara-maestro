"""Install and verify the official Comfy-Org FLUX.1 Fill dev weight."""

from __future__ import annotations

import argparse
import hashlib
import logging
import shutil
from pathlib import Path


REPO = "Comfy-Org/flux1-dev"
REMOTE = "split_files/diffusion_models/flux1-fill-dev.safetensors"
EXPECTED_BYTES = 23_804_922_408
EXPECTED_SHA256 = "03e289f530df51d014f48e675a9ffa2141bc003259bf5f25d75b957e920a41ca"
MODEL_DIR = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\diffusion_models")
DESTINATION = MODEL_DIR / "flux1-fill-dev.safetensors"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid(path: Path) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == EXPECTED_BYTES
        and sha256(path) == EXPECTED_SHA256
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--parts", type=int, default=32)
    parser.add_argument(
        "--log", type=Path,
        default=Path(__file__).with_name("download_flux_fill.log"),
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(args.log, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    log = logging.getLogger("flux-fill-installer")
    if valid(DESTINATION):
        log.info("VALIDO: %s", DESTINATION)
        return 0
    usage = shutil.disk_usage(MODEL_DIR)
    required = EXPECTED_BYTES + 15 * 1024**3
    if usage.free < required:
        raise RuntimeError(
            f"Espaco insuficiente: {usage.free} livres; {required} necessarios com reserva"
        )
    log.info("Plano: %s -> %s (%d bytes)", f"{REPO}/{REMOTE}", DESTINATION, EXPECTED_BYTES)
    if args.dry_run:
        log.info("DRY-RUN OK")
        return 0

    # Hugging Face's Xet transfer stalls on this Windows host. Reuse the
    # generic verified ranged downloader: it resumes each independent part
    # and only publishes the file after exact size and SHA-256 checks.
    import ranged_model_download as ranged

    ranged.ROOT = MODEL_DIR
    ranged.BASE_URLS = (
        "https://hf-mirror.com/Comfy-Org/flux1-dev/resolve/main/"
        "split_files/diffusion_models",
        "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/"
        "split_files/diffusion_models",
    )
    ranged.MODELS = {
        DESTINATION.name: {
            "size": EXPECTED_BYTES,
            "sha256": EXPECTED_SHA256,
        }
    }
    ranged.download_model(
        DESTINATION.name,
        workers=max(1, args.workers),
        parts=max(1, args.parts),
    )
    if not valid(DESTINATION):
        raise RuntimeError("Verificacao final do FLUX Fill falhou")
    log.info("VALIDO: %s", DESTINATION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
