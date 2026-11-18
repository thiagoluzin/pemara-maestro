"""Remove verified stale download caches without touching published weights."""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path


MODELS = Path(r"E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models").resolve()
STALE_DIRS = (
    MODELS / "unet" / "_hf_downloads",
    MODELS / "_hf_staging" / "flux1_fill",
)
STALE_FILES = (
    Path(r"E:\Pemara\fill_probe_1m.bin"),
    Path(r"E:\Pemara\fill_probe_16m.bin"),
    Path(r"E:\Pemara\fill_range_probe.bin"),
    Path(r"E:\Pemara\temp_flux_kontext_workflow.png"),
    Path(r"E:\Pemara\temp_flux_fill_workflow.png"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("incomplete-model-cleanup")
    total = 0
    for directory in STALE_DIRS:
        resolved = directory.resolve()
        if MODELS not in resolved.parents:
            raise RuntimeError(f"Diretorio fora da raiz de modelos: {resolved}")
        if not directory.exists():
            log.info("JA AUSENTE: %s", directory)
            continue
        files = [path for path in directory.rglob("*") if path.is_file()]
        size = sum(path.stat().st_size for path in files)
        total += size
        log.info("CACHE INCOMPLETO: %s files=%d bytes=%d", directory, len(files), size)
        if args.apply:
            shutil.rmtree(directory)
    for path in STALE_FILES:
        if not path.exists():
            log.info("JA AUSENTE: %s", path)
            continue
        if not path.is_file():
            raise RuntimeError(f"Esperava arquivo regular: {path}")
        size = path.stat().st_size
        total += size
        log.info("TEMPORARIO: %s bytes=%d", path, size)
        if args.apply:
            path.unlink()
    log.info("%s bytes=%d", "APLICADO" if args.apply else "DRY-RUN OK", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
