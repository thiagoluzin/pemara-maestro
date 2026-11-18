"""Isolated Qwen3-TTS pt-BR voice-clone worker for Maestro video ADR."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--reference-audio", required=True)
    parser.add_argument("--reference-text-file", required=True)
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=20260804)
    return parser.parse_args()


def read_required_text(path: Path, label: str) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{label} vazio.")
    return value


def main() -> None:
    args = arguments()
    model_dir = Path(args.model_dir).resolve(strict=True)
    reference_audio = Path(args.reference_audio).resolve(strict=True)
    reference_text = read_required_text(
        Path(args.reference_text_file).resolve(strict=True), "Texto de referencia"
    )
    target_text = read_required_text(Path(args.text_file).resolve(strict=True), "Fala alvo")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if reference_audio.suffix.casefold() not in {".wav", ".flac", ".mp3", ".m4a"}:
        raise ValueError("Formato de referencia de voz nao autorizado.")
    if output.suffix.casefold() != ".wav":
        raise ValueError("A entrega intermediaria Qwen3-TTS deve ser WAV.")
    if not torch.cuda.is_available():
        raise RuntimeError("Qwen3-TTS requer CUDA para este pipeline do Maestro.")

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
    clone_prompt = model.create_voice_clone_prompt(
        ref_audio=str(reference_audio),
        ref_text=reference_text,
    )
    wavs, sample_rate = model.generate_voice_clone(
        text=target_text,
        language="Portuguese",
        voice_clone_prompt=clone_prompt,
    )
    if not wavs:
        raise RuntimeError("Qwen3-TTS nao retornou audio.")
    waveform = np.asarray(wavs[0], dtype=np.float32).squeeze()
    if waveform.ndim != 1 or waveform.size < int(sample_rate * 0.25):
        raise RuntimeError("Qwen3-TTS retornou uma forma de onda invalida.")
    peak = float(np.max(np.abs(waveform))) if waveform.size else 0.0
    if not np.isfinite(waveform).all() or peak <= 1e-5:
        raise RuntimeError("Qwen3-TTS retornou silencio ou amostras invalidas.")
    sf.write(str(output), waveform, int(sample_rate), subtype="PCM_16")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output),
                "sample_rate": int(sample_rate),
                "duration_seconds": round(float(waveform.size) / float(sample_rate), 6),
                "peak": round(peak, 6),
                "language": "Portuguese",
                "locale_target": "pt-BR",
                "seed": args.seed,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
