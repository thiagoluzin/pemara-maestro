"""Baixa somente os pesos oficiais do Chatterbox para o cache local.

Nao instancia o modelo, nao sintetiza audio e nao inicializa CUDA.
"""

from pathlib import Path

from huggingface_hub import snapshot_download


FILES = [
    "ve.pt",
    "t3_mtl23ls_v3.safetensors",
    "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json",
    "conds.pt",
    "Cangjie5_TC.json",
]


def main() -> int:
    cache_dir = Path(__file__).resolve().parent / "model-cache" / "huggingface" / "hub"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = snapshot_download(
        repo_id="ResembleAI/chatterbox",
        repo_type="model",
        revision="main",
        allow_patterns=FILES,
        cache_dir=cache_dir,
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
