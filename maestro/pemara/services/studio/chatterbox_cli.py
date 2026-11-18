"""Worker isolado para Chatterbox Multilingual V3.

Este arquivo roda apenas quando o usuario solicita voz neural no Editor IA.
O ambiente recomendado e `ferramentas/chatterbox/.venv`, separado do Studio.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _bounded_float(name: str, minimum: float, maximum: float):
    def parse(value: str) -> float:
        try:
            parsed = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} deve ser numerico.") from exc
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
    parser.add_argument("--reference", default="")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--exaggeration",
        type=_bounded_float("exaggeration", 0.0, 1.0),
        default=0.5,
        help="Intensidade emocional do condicionamento.",
    )
    parser.add_argument(
        "--cfg-weight",
        type=_bounded_float("cfg_weight", 0.0, 1.0),
        default=0.5,
        help="Fidelidade ao condicionamento; valores menores permitem mais atuacao.",
    )
    parser.add_argument(
        "--temperature",
        type=_bounded_float("temperature", 0.05, 2.0),
        default=0.8,
    )
    parser.add_argument(
        "--repetition-penalty",
        type=_bounded_float("repetition_penalty", 1.0, 3.0),
        default=2.0,
    )
    parser.add_argument(
        "--min-p",
        type=_bounded_float("min_p", 0.0, 1.0),
        default=0.05,
    )
    parser.add_argument(
        "--top-p",
        type=_bounded_float("top_p", 0.05, 1.0),
        default=1.0,
    )
    args = parser.parse_args()

    import soundfile as sf
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Texto vazio.")
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    # V2 remains the upstream default. Select V3 explicitly so the Maestro
    # does not silently regress to the legacy multilingual checkpoint.
    model = ChatterboxMultilingualTTS.from_pretrained(
        device=torch.device(args.device),
        t3_model="v3",
    )
    kwargs = {
        "language_id": args.language,
        "exaggeration": args.exaggeration,
        "cfg_weight": args.cfg_weight,
        "temperature": args.temperature,
        "repetition_penalty": args.repetition_penalty,
        "min_p": args.min_p,
        "top_p": args.top_p,
    }
    if args.reference:
        reference = Path(args.reference).resolve(strict=True)
        kwargs["audio_prompt_path"] = str(reference)
    wav = model.generate(text, **kwargs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    audio = wav.detach().float().cpu().numpy()
    if audio.ndim == 2:
        audio = audio.T
    # The Studio intentionally uses a neutral temporary extension. Tell
    # libsndfile the container explicitly instead of relying on the suffix.
    sf.write(str(output), audio, model.sr, format="WAV", subtype="PCM_16")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
