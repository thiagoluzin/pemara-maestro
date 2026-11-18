import os
import os.path as op
import re
import time
import json
from datetime import datetime

import gradio as gr
import torch
import torchaudio

from download import download_model

APP_DIR = op.dirname(op.abspath(__file__))
download_model(APP_DIR)
print("Successful downloaded model.")

from vllm.v1.engine.processor import Processor
from vllm.engine.llm_engine import LLMEngine

Processor._validate_model_input = lambda *args, **kwargs: None
LLMEngine._validate_token_prompt = lambda *args, **kwargs: None

from vllm import __version__ as vllm_version
from vllm import LLM, SamplingParams
from megatron.tokenizer import build_tokenizer
from mucodec.generate_1rvq import Tango


class _Args:
    pass


class VllmInf:
    def __init__(self, model_path, vocab_file, tokenizer="Qwen2Tokenizer", extra_vocab_size=16384):
        args = _Args()
        args.vocab_file = vocab_file
        args.load = model_path
        args.extra_vocab_size = extra_vocab_size
        args.patch_tokenizer_type = tokenizer

        self.tokenizer = build_tokenizer(args)
        self.text_offset = len(self.tokenizer.tokenizer.get_vocab())
        self.max_tokens = 8192
        self.llm = LLM(
            model=model_path,
            trust_remote_code=True,
            max_model_len=self.max_tokens,
            dtype="bfloat16",
        )

    def run(self, audios):
        batch_token_ids = []
        max_tokens = self.max_tokens
        for audio in audios:
            audio = audio + self.text_offset
            sentence_ids = (
                [self.tokenizer.sep_token_id]
                + audio.tolist()
                + [self.tokenizer.tokenizer.sep_token_id]
            )
            max_tokens = min(max_tokens, self.max_tokens - len(sentence_ids))
            batch_token_ids.append(sentence_ids)

        sampling_params = SamplingParams(n=1, max_tokens=max_tokens, top_p=0.1, temperature=0.1)

        if vllm_version == "0.8.5":
            outputs = self.llm.generate(prompt_token_ids=batch_token_ids, sampling_params=sampling_params)
        else:
            inputs = [{"prompt_token_ids": tids} for tids in batch_token_ids]
            outputs = self.llm.generate(prompts=inputs, sampling_params=sampling_params)

        return [self.tokenizer.detokenize(o.outputs[0].token_ids) for o in outputs]


TANGO = None
VLLM_INF = None

SEGMENT_PATTERN = re.compile(
    r"\[(?P<structure>[^\[\]]+)\]\s*\[(?P<start>[^\[\]:]+):(?P<end>[^\[\]]+)\]\s*(?P<lyric>[^;]*)"
)

_SPECIAL_TOKENS_TO_STRIP = (
    "<|endoftext|>",
    "<|im_end|>",
    "<|im_start|>",
    "<|begin_of_text|>",
    "<|end_of_text|>",
)


def _strip_special_tokens(text):
    if not text:
        return text
    for tok in _SPECIAL_TOKENS_TO_STRIP:
        text = text.replace(tok, "")
    return text


def parse_lyric_output(raw_text):
    if raw_text is None:
        return []

    raw_text = _strip_special_tokens(raw_text)
    segments = []
    for chunk in raw_text.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = SEGMENT_PATTERN.search(chunk)
        if m:
            segments.append({
                "structure": m.group("structure").strip(),
                "start": m.group("start").strip(),
                "end": m.group("end").strip(),
                "lyric": m.group("lyric").strip(),
            })
        else:
            segments.append({"structure": "unknown", "start": "", "end": "", "lyric": chunk})
    return segments


def _escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_segments_markdown(segments):
    """Render segments as collapsible <details> blocks."""
    if not segments:
        return "*(No lyrics detected)*"

    blocks = []
    for seg in segments:
        header_bits = [f"<strong>[{_escape_html(seg['structure'])}]</strong>"]
        if seg["start"] or seg["end"]:
            header_bits.append(
                f"<code>{_escape_html(seg['start'])} - {_escape_html(seg['end'])}</code>"
            )
        summary = "  ".join(header_bits)

        lyric = seg["lyric"]
        if lyric:
            sentences = [s.strip() for s in lyric.split(".") if s.strip()]
            body = "<ul>" + "".join(f"<li>{_escape_html(s)}</li>" for s in sentences) + "</ul>"
        else:
            body = "<p><em>(no lyric)</em></p>"

        blocks.append(f"<details><summary>{summary}</summary>{body}</details>")

    return "\n".join(blocks)


def transcribe_song(audio_path, progress=gr.Progress(track_tqdm=True)):
    if audio_path is None or not op.isfile(audio_path):
        return "*(Please upload an audio file first.)*", json.dumps(
            {"error": "No audio file provided"}, indent=2
        )

    progress(0.0, "Loading audio")
    src_wave, fs = torchaudio.load(audio_path)
    if fs != 48000:
        src_wave = torchaudio.functional.resample(src_wave, fs, 48000)

    progress(0.2, "Encoding audio with codec")
    start_time = time.time()
    code = TANGO.sound2code(src_wave)
    audio_codes = code[0][0].cpu().numpy()

    progress(0.5, "Running SongPrep transcription")
    lyrics = VLLM_INF.run([audio_codes])
    raw_lyric = _strip_special_tokens(lyrics[0] if lyrics else "")

    elapsed = time.time() - start_time
    progress(1.0, "Done")

    segments = parse_lyric_output(raw_lyric)
    pretty = format_segments_markdown(segments)

    info = {
        "filename": op.basename(audio_path),
        "num_segments": len(segments),
        "inference_duration": elapsed,
        "timestamp": datetime.now().isoformat(),
        "raw_output": raw_lyric,
    }
    return pretty, json.dumps(info, indent=2, ensure_ascii=False)


with gr.Blocks(title="SongPrep Demo Space") as demo:
    gr.Markdown("# 🎵 SongPrep Demo Space")
    gr.Markdown(
        "Upload a song and SongPrep will analyze its **structure** and "
        "transcribe the **lyrics** with timestamps. "
        "Project: [SongPrep on GitHub](https://github.com/tencent-ailab/SongPrep)"
    )

    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                label="Upload Song Audio",
                type="filepath",
                sources=["upload"],
                elem_id="song-audio",
            )
            transcribe_btn = gr.Button("Transcribe Song", variant="primary")

        with gr.Column():
            pretty_output = gr.Markdown(
                label="Parsed Lyrics (click a section to expand)",
                value="*(Results will appear here.)*",
            )
            info_output = gr.JSON(label="Inference Info")

    transcribe_btn.click(
        fn=transcribe_song,
        inputs=[audio_input],
        outputs=[pretty_output, info_output],
    )


if __name__ == "__main__":
    torch.set_num_threads(1)

    codec_path = op.join(APP_DIR, "mucodec.safetensors")
    vocab_file = op.join(APP_DIR, "conf/vocab_type.yaml")

    TANGO = Tango(model_path=codec_path)
    VLLM_INF = VllmInf(APP_DIR, vocab_file)

    demo.launch(server_name="0.0.0.0", server_port=7860)
