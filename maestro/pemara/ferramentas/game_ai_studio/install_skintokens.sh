#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y curl ca-certificates python3-venv libgl1 libglib2.0-0 libegl1 libx11-6 libxext6 libsm6 libxrender1 libxi6 libxfixes3 libxkbcommon0
if [ ! -x /root/.local/bin/uv ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi
UV=/root/.local/bin/uv
ENV_DIR=/opt/maestro-game-ai/envs/skintokens
REPO=/mnt/d/PemaraRuntimes/maestro-game-ai/apps/SkinTokens
mkdir -p /opt/maestro-game-ai/envs
if [ ! -x "$ENV_DIR/bin/python" ]; then "$UV" venv --python 3.11 "$ENV_DIR"; fi
PY="$ENV_DIR/bin/python"
"$UV" pip install --python "$PY" torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
"$UV" pip install --python "$PY" -r "$REPO/requirements.txt" 'transformers<5' 'numpy<2.3'
ABI=$("$PY" -c 'import torch;print(str(torch._C._GLIBCXX_USE_CXX11_ABI).upper())')
"$UV" pip install --python "$PY" "https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3.post1/flash_attn-2.8.3.post1%2Bcu12torch2.7cxx11abi${ABI}-cp311-cp311-linux_x86_64.whl"
cd "$REPO"
"$PY" -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen3-0.6B', local_dir='models/Qwen3-0.6B', ignore_patterns=['*.bin','*.safetensors'])"
CHECK_LOG=/mnt/d/PemaraRuntimes/maestro-game-ai/logs/skintokens-pip-check.log
if ! "$UV" pip check --python "$PY" > "$CHECK_LOG" 2>&1; then
    cat "$CHECK_LOG"
    # Keep the upstream metadata warning visible; only accept this exact known case.
    "$PY" - "$CHECK_LOG" <<'PY'
import sys,importlib.metadata
from pathlib import Path
text=Path(sys.argv[1]).read_text()
assert 'Found 1 incompatibility' in text and 'The package `bpy` was built for a different platform' in text
assert importlib.metadata.version('bpy') == '5.0.1'
assert 'Tag: cp39-cp39-manylinux_2_28_x86_64' in importlib.metadata.distribution('bpy').read_text('WHEEL')
print('Known upstream bpy metadata warning retained in installation receipt.')
PY
fi
"$PY" -c 'import flash_attn, torch, bpy; print("IMPORTS_OK", torch.__version__, bpy.app.version_string)'
"$PY" /mnt/e/Pemara/maestro/pemara/ferramentas/game_ai_studio/test_skintokens_environment.py
date --iso-8601=seconds > /mnt/d/PemaraRuntimes/maestro-game-ai/logs/skintokens-software.done
