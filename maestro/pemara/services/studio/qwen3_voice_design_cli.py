"""Local Qwen3-TTS VoiceDesign worker for original Maestro character voices."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
from pathlib import Path

# Librosa imports Numba transitively. On this Windows runtime the eager JIT
# initialization can spin on CPU for minutes before the TTS model reaches CUDA.
# VoiceDesign does not need those JIT kernels, so disable them before importing
# qwen_tts and keep the worker startup deterministic.
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260819)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    return parser.parse_args()


def load_requests(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("requests") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not 1 <= len(items) <= 4:
        raise ValueError("Forneca de uma a quatro variantes de voz.")
    normalized: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Cada variante deve ser um objeto JSON.")
        request_id = str(item.get("id") or "").strip().lower()
        text = str(item.get("text") or "").strip()
        instruction = str(item.get("instruction") or "").strip()
        if not SAFE_ID.fullmatch(request_id):
            raise ValueError("Identificador de variante invalido.")
        if not 1 <= len(text) <= 500:
            raise ValueError("Texto deve ter entre 1 e 500 caracteres.")
        if not 20 <= len(instruction) <= 1000:
            raise ValueError("Direcao de voz deve ter entre 20 e 1000 caracteres.")
        normalized.append(
            {
                "id": request_id,
                "text": text,
                "instruction": instruction,
                "language": "Portuguese",
            }
        )
    return normalized


def main() -> int:
    args = arguments()
    model_dir = Path(args.model_dir).resolve(strict=True)
    requests = load_requests(Path(args.requests).resolve(strict=True))
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not 128 <= args.max_new_tokens <= 1024:
        raise ValueError("max-new-tokens deve ficar entre 128 e 1024.")
    if not torch.cuda.is_available():
        raise RuntimeError("Qwen3-TTS VoiceDesign requer CUDA neste pipeline.")

    random.seed(args.seed)
    np.random.seed(args.seed % (2**32 - 1))
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    model = Qwen3TTSModel.from_pretrained(
        str(model_dir),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    wavs, sample_rate = model.generate_voice_design(
        text=[item["text"] for item in requests],
        language=[item["language"] for item in requests],
        instruct=[item["instruction"] for item in requests],
        max_new_tokens=args.max_new_tokens,
    )
    if len(wavs) != len(requests):
        raise RuntimeError("Qwen3-TTS retornou quantidade inesperada de variantes.")

    results = []
    for item, wav in zip(requests, wavs, strict=True):
        waveform = np.asarray(wav, dtype=np.float32).squeeze()
        if waveform.ndim != 1 or waveform.size < int(sample_rate * 0.25):
            raise RuntimeError(f"Variante {item['id']} retornou forma de onda invalida.")
        peak = float(np.max(np.abs(waveform))) if waveform.size else 0.0
        if not np.isfinite(waveform).all() or peak <= 1e-5:
            raise RuntimeError(f"Variante {item['id']} retornou silencio ou amostras invalidas.")
        output = output_dir / f"{item['id']}.wav"
        sf.write(str(output), waveform, int(sample_rate), format="WAV", subtype="PCM_16")
        results.append(
            {
                "id": item["id"],
                "output": str(output),
                "sampleRate": int(sample_rate),
                "durationSeconds": round(float(waveform.size) / float(sample_rate), 6),
                "peak": round(peak, 6),
                "textSha256": hashlib.sha256(item["text"].encode("utf-8")).hexdigest(),
                "instructionSha256": hashlib.sha256(
                    item["instruction"].encode("utf-8")
                ).hexdigest(),
            }
        )
    print(json.dumps({"ok": True, "seed": args.seed, "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
