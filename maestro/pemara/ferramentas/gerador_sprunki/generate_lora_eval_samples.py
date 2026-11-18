#!/usr/bin/env python
"""
Gera amostras limpas para avaliar a LoRA Sprunki mais recente.

Nao usa static/generated antigo. Salva tudo dentro do experimento informado.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
COMFY_OUTPUT = ROOT.parent / "ComfyUI" / "output"
COMFY_URL = "http://127.0.0.1:8188"
DEFAULT_WORKFLOW = ROOT / "workflow_api.json"

PROMPTS = [
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, round eyes, expressive mouth, orange body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, sleepy eyes, small smile, blue body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, big surprised eyes, open mouth, green body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, mischievous eyes, sharp smile, purple body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, headphones, cyan body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, small hat, yellow body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, tiny antenna, red body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, shy expression, pink body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, wide grin, lime body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, nervous expression, gray body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, confident expression, black body, no text, no watermark",
    "sprunki_char, single full body character, clean official Sprunki inspired music game character, simple flat vector shapes, centered on plain white background, black outline, cute round eyes, white body, no text, no watermark",
]


def post_json(path: str, payload: dict) -> dict:
    req = Request(
        COMFY_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_json(path: str) -> dict:
    with urlopen(COMFY_URL + path, timeout=30) as resp:
        return json.loads(resp.read())


def wait_for_health(timeout: int = 20) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            get_json("/system_stats")
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("ComfyUI nao respondeu em 127.0.0.1:8188")


def make_workflow(prompt: str, seed: int, prefix: str, lora_name: str, strength: float, steps: int) -> dict:
    wf = json.loads(DEFAULT_WORKFLOW.read_text(encoding="utf-8"))
    wf["2"]["inputs"]["lora_name"] = lora_name
    wf["2"]["inputs"]["strength_model"] = strength
    wf["2"]["inputs"]["strength_clip"] = strength
    wf["5"]["inputs"]["width"] = 1024
    wf["5"]["inputs"]["height"] = 1024
    wf["6"]["inputs"]["text"] = prompt
    wf["15"]["inputs"]["steps"] = steps
    wf["16"]["inputs"]["noise_seed"] = seed
    wf["9"]["inputs"]["filename_prefix"] = prefix
    return wf


def wait_for_prompt(prompt_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = get_json(f"/history/{prompt_id}")
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(2)
    raise RuntimeError(f"Timeout esperando prompt {prompt_id}")


def copy_outputs(history: dict, dest: Path) -> list[Path]:
    copied = []
    for output in history.get("outputs", {}).values():
        for item in output.get("images", []):
            src = COMFY_OUTPUT / item.get("subfolder", "") / item["filename"]
            if src.exists():
                target = dest / item["filename"]
                shutil.copy2(src, target)
                copied.append(target)
    return copied


def parse_strengths(value: str, fallback: float) -> list[float]:
    if not value:
        return [fallback]
    strengths = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        strengths.append(float(item))
    return strengths or [fallback]


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera amostras de avaliacao da LoRA Sprunki")
    parser.add_argument("--experiment", default="lora_20260618_000101")
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--strength", type=float, default=0.85)
    parser.add_argument("--strengths", default="", help="Lista separada por virgula. Ex: 0.15,0.30,0.45")
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--seed", type=int, default=18062026)
    parser.add_argument("--lora-name", default="sprunki_lora.safetensors")
    args = parser.parse_args()

    wait_for_health()

    exp_dir = ROOT / "experiments" / args.experiment
    out_dir = exp_dir / "eval_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    strengths = parse_strengths(args.strengths, args.strength)
    manifest = []
    client_id = str(uuid.uuid4())
    jobs_total = args.count * len(strengths)
    job = 0
    for strength in strengths:
        strength_dir = out_dir / f"strength_{strength:.2f}".replace(".", "_")
        strength_dir.mkdir(parents=True, exist_ok=True)
        for index, prompt in enumerate(PROMPTS[: args.count], start=1):
            job += 1
            seed = args.seed + index
            prefix = f"eval_{args.experiment}_s{strength:.2f}_{index:02d}".replace(".", "_")
            workflow = make_workflow(prompt, seed, prefix, args.lora_name, strength, args.steps)
            result = post_json("/prompt", {"prompt": workflow, "client_id": client_id})
            prompt_id = result["prompt_id"]
            print(f"[{job:02d}/{jobs_total}] strength={strength:.2f} prompt_id={prompt_id} seed={seed}")
            history = wait_for_prompt(prompt_id)
            files = copy_outputs(history, strength_dir)
            manifest.append(
                {
                    "index": index,
                    "strength": strength,
                    "seed": seed,
                    "prompt": prompt,
                    "prompt_id": prompt_id,
                    "files": [str(p) for p in files],
                }
            )

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
