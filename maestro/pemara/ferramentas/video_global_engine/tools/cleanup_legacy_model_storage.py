"""Remove the verified-obsolete D: model cache after consolidation to E:."""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path


ROOT = Path(r"D:\PemaraModels\ComfyUI")
EXPECTED_ROOT = Path(r"D:\PemaraModels\ComfyUI").resolve()
INCOMPLETE_KONTEXT = (
    EXPECTED_ROOT / "flux_kontext_repo" / "split_files" / "diffusion_models"
    / "flux1-dev-kontext_fp8_scaled.safetensors"
)
KONTEXT_FULL_BYTES = 11_904_640_136


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--log", type=Path,
        default=Path(__file__).with_name("cleanup_legacy_model_storage.log"),
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(args.log, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    log = logging.getLogger("legacy-model-cleanup")
    if not ROOT.exists():
        log.info("JA AUSENTE: %s", ROOT)
        return 0
    resolved = ROOT.resolve()
    if resolved != EXPECTED_ROOT or resolved.drive.upper() != "D:":
        raise RuntimeError(f"Raiz fora do escopo permitido: {resolved}")
    model_files = [
        path.resolve() for path in ROOT.rglob("*.safetensors")
        if ".cache" not in {part.lower() for part in path.parts}
    ]
    unexpected = [path for path in model_files if path != INCOMPLETE_KONTEXT]
    if unexpected:
        raise RuntimeError("Pesos nao migrados ainda presentes: " + ", ".join(map(str, unexpected)))
    if INCOMPLETE_KONTEXT.exists() and INCOMPLETE_KONTEXT.stat().st_size >= KONTEXT_FULL_BYTES:
        raise RuntimeError("Kontext legado parece completo; recusando remover automaticamente")
    files = [path for path in ROOT.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    log.info("LEGADO VERIFICADO: files=%d bytes=%d root=%s", len(files), total, ROOT)
    if not args.apply:
        log.info("DRY-RUN OK")
        return 0
    shutil.rmtree(ROOT)
    if ROOT.exists():
        raise RuntimeError(f"Falha ao remover {ROOT}")
    log.info("REMOVIDO: %s bytes=%d", ROOT, total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
