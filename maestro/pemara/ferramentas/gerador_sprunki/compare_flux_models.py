"""
compare_flux_models.py

Gera lotes A/B no ComfyUI para comparar FLUX.1-dev contra FLUX.1 Krea dev FP8.
"""

from __future__ import annotations

import argparse
import copy
import json
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_MODELS = ["flux1_dev", "flux1_krea_fp8"]


def log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_workflow(model_key: str, matrix: dict) -> Path:
    model = matrix["models"][model_key]
    workflow = ROOT / model["workflow"]
    if not workflow.exists():
        raise FileNotFoundError(f"Workflow nao encontrado para {model_key}: {workflow}")
    return workflow


def check_comfyui(url: str) -> None:
    response = requests.get(f"{url}/system_stats", timeout=5)
    response.raise_for_status()


def inject(workflow: dict, prompt: str, seed: int, params: dict, prefix: str) -> dict:
    wf = copy.deepcopy(workflow)
    apply_lora_fallback(wf)
    if "6" in wf:
        wf["6"]["inputs"]["text"] = prompt
    if "12" in wf:
        wf["12"]["inputs"]["guidance"] = params.get("guidance_scale", 3.5)
    if "15" in wf:
        wf["15"]["inputs"]["steps"] = params.get("steps", 28)
    if "16" in wf:
        wf["16"]["inputs"]["noise_seed"] = seed
    if "5" in wf:
        wf["5"]["inputs"]["width"] = params.get("width", 1024)
        wf["5"]["inputs"]["height"] = params.get("height", 1024)
    if "14" in wf:
        wf["14"]["inputs"]["width"] = params.get("width", 1024)
        wf["14"]["inputs"]["height"] = params.get("height", 1024)
    if "9" in wf:
        wf["9"]["inputs"]["filename_prefix"] = prefix
    return wf


def apply_lora_fallback(workflow: dict) -> None:
    if "2" not in workflow:
        return

    lora_dir = ROOT.parent / "ComfyUI" / "models" / "loras"
    lora_name = workflow["2"].get("inputs", {}).get("lora_name", "sprunki_lora.safetensors")
    lora_path = lora_dir / lora_name
    alternate_lora = lora_dir / "sprunki_lora.safetensors"

    if not lora_path.exists() and alternate_lora.exists():
        workflow["2"]["inputs"]["lora_name"] = alternate_lora.name
        return

    if lora_path.exists():
        return

    del workflow["2"]
    if "6" in workflow and workflow["6"]["inputs"].get("clip") == ["2", 1]:
        workflow["6"]["inputs"]["clip"] = ["10", 0]
    if "13" in workflow and workflow["13"]["inputs"].get("model") == ["2", 0]:
        workflow["13"]["inputs"]["model"] = ["14", 0]
    if "14" in workflow and workflow["14"]["inputs"].get("model") == ["2", 0]:
        workflow["14"]["inputs"]["model"] = ["1", 0]


def submit_workflow(url: str, workflow: dict) -> str:
    client_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["prompt_id"]


def wait_for_output(url: str, prompt_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            hist = requests.get(f"{url}/history/{prompt_id}", timeout=15).json()
            outputs = hist.get(prompt_id, {}).get("outputs", {})
            for node_out in outputs.values():
                images = node_out.get("images", [])
                if images:
                    return images[0]
        except Exception as exc:
            last_error = str(exc)
        time.sleep(3)
    raise TimeoutError(f"Timeout aguardando {prompt_id}. Ultimo erro: {last_error}")


def download_image(url: str, image_info: dict, dest: Path) -> None:
    params = {
        "filename": image_info["filename"],
        "subfolder": image_info.get("subfolder", ""),
        "type": image_info.get("type", "output"),
    }
    response = requests.get(f"{url}/view", params=params, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)


def score_image(path: Path) -> dict | None:
    try:
        from quality_evaluator import evaluate_sprunki

        return evaluate_sprunki(str(path), reference_dir=str(ROOT / "static" / "referencias"))
    except Exception as exc:
        return {"error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparacao A/B de modelos FLUX para Sprunki")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--prompts", default="ab_prompts.json")
    parser.add_argument("--matrix", default="model_matrix.json")
    parser.add_argument("--comfyui-url", default=COMFYUI_URL)
    parser.add_argument("--limit", type=int, default=0, help="Limita quantidade de prompts")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    matrix = load_json(ROOT / args.matrix)
    prompts = load_json(ROOT / args.prompts)
    if args.limit > 0:
        prompts = prompts[: args.limit]
    params = matrix.get("comparison", {})
    seeds = params.get("seeds", [10101])

    run_id = datetime.now().strftime("compare_flux_%Y%m%d_%H%M%S")
    run_dir = ROOT / "experiments" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompts.json").write_text(json.dumps(prompts, indent=2), encoding="utf-8")
    (run_dir / "matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    if args.dry_run:
        log(f"Dry-run criado em {run_dir}")
        return 0

    check_comfyui(args.comfyui_url)
    scores = []

    for model_key in args.models:
        workflow_path = resolve_workflow(model_key, matrix)
        workflow = load_json(workflow_path)
        model_dir = run_dir / model_key
        model_dir.mkdir(parents=True, exist_ok=True)

        for idx, prompt_item in enumerate(prompts):
            seed = int(seeds[idx % len(seeds)])
            prompt_id = prompt_item["id"]
            prefix = f"{run_id}_{model_key}_{prompt_id}_{seed}_"
            output_name = f"{prompt_id}_{seed}.png"
            dest = model_dir / output_name

            log(f"{model_key}: gerando {prompt_id} seed={seed}")
            wf = inject(workflow, prompt_item["prompt"], seed, params, prefix)
            comfy_prompt_id = submit_workflow(args.comfyui_url, wf)
            image_info = wait_for_output(args.comfyui_url, comfy_prompt_id, timeout=args.timeout)
            download_image(args.comfyui_url, image_info, dest)
            score = score_image(dest)
            scores.append(
                {
                    "model": model_key,
                    "prompt_id": prompt_id,
                    "seed": seed,
                    "path": str(dest),
                    "comfy_prompt_id": comfy_prompt_id,
                    "score": score,
                }
            )
            (run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "models": args.models,
        "count": len(scores),
        "scores_file": str(run_dir / "scores.json"),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"Comparacao concluida em {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
