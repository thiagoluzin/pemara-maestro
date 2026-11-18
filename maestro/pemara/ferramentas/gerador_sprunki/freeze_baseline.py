"""
freeze_baseline.py

Congela o estado atual do gerador Sprunki antes de experimentos A/B.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASELINE_DIR = ROOT / "experiments" / "baseline_flux1_dev"


def copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return True


def main() -> int:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    copied = {
        "workflow_api": copy_if_exists(ROOT / "workflow_api.json", BASELINE_DIR / "workflow_api.json"),
        "model_matrix": copy_if_exists(ROOT / "model_matrix.json", BASELINE_DIR / "model_matrix.json"),
        "lora_model": copy_if_exists(
            ROOT / "lora_dataset" / "model" / "sprunki_lora.safetensors",
            BASELINE_DIR / "sprunki_lora.safetensors",
        ),
        "dataset": copy_if_exists(
            ROOT / "lora_dataset" / "img" / "20_sprunki_char",
            BASELINE_DIR / "dataset" / "20_sprunki_char",
        ),
    }

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "baseline": "flux1_dev",
        "path": str(BASELINE_DIR),
        "copied": copied,
    }
    (BASELINE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
