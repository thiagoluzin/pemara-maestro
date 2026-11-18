"""Offline worker for the locally cached Chatterbox pt-BR fine-tune."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def bounded_float(name: str, minimum: float, maximum: float):
    def parse(value: str) -> float:
        parsed = float(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{name} deve estar entre {minimum:g} e {maximum:g}."
            )
        return parsed

    return parse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--exaggeration",
        type=bounded_float("exaggeration", 0.0, 1.0),
        default=0.35,
    )
    parser.add_argument(
        "--cfg-weight",
        type=bounded_float("cfg_weight", 0.0, 1.0),
        default=0.55,
    )
    parser.add_argument(
        "--temperature",
        type=bounded_float("temperature", 0.05, 2.0),
        default=0.65,
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve(strict=True)
    model_dir = Path(args.model_dir).resolve(strict=True)
    sys.path.insert(0, str(source_dir))

    import soundfile as sf
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Texto vazio.")
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    reference = Path(args.reference).resolve(strict=True)
    if not reference.is_file():
        raise ValueError("A referência de voz precisa ser um arquivo de áudio.")
    model = ChatterboxMultilingualTTS.from_local(
        model_dir,
        args.device,
        t3_model="t3_pt_br.safetensors",
    )
    wav = model.generate(
        text,
        language_id=args.language,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        temperature=args.temperature,
        audio_prompt_path=str(reference),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    audio = wav.detach().float().cpu().numpy()
    if audio.ndim == 2:
        audio = audio.T
    sf.write(str(output), audio, model.sr, subtype="PCM_16")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
