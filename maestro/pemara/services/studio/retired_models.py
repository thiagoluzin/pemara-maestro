"""Owner-requested local model retirement, 2026-11-15.

Historical projects remain readable. New requests must choose a retained engine;
retirement never downloads weights or selects a replacement model.
"""
from __future__ import annotations

from typing import Any

RETIRED_IMAGE_ENGINE_IDS = frozenset({
    "llada_base", "llada_turbo", "flux3_klein", "flux2_klein", "z_image", "z_image_turbo",
})
RETIRED_VIDEO_ENGINE_IDS = frozenset({"hunyuan_video_15"})
_EXCLUSIVE_ENCODERS = frozenset({
    "qwen_3_4b.safetensors", "qwen3vl_4b_int8_convrot.safetensors",
    "qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors",
})
_MODEL_INPUTS = frozenset({
    "ckpt_name", "unet_name", "clip_name", "clip_name1", "clip_name2", "vae_name",
    "model_name", "control_net_name", "lora_name", "weight_file", "checkpoint",
})


class ModelRetiredError(ValueError):
    code = "MODEL_REMOVED_BY_OWNER"
    status_code = 410


def is_retired_engine(value: Any) -> bool:
    selected = str(value or "").strip().lower()
    return selected in RETIRED_IMAGE_ENGINE_IDS | RETIRED_VIDEO_ENGINE_IDS or selected.startswith(
        ("flux", "llada", "z_image", "z-image", "hunyuan15", "hunyuan_video_15")
    )


def is_retired_model(value: Any) -> bool:
    path = str(value or "").strip().replace("\\", "/").lower()
    name = path.rsplit("/", 1)[-1]
    return name in _EXCLUSIVE_ENCODERS or name.startswith(
        ("llada-image-", "flux", "z_image", "z-image", "hunyuanvideo1.5_", "hunyuanvideo15_")
    ) or "tongyi-mai--z-image" in path or "black-forest-labs--flux.2-klein-4b" in path


def require_model_allowed(model: Any = "", engine_id: Any = "") -> None:
    if is_retired_engine(engine_id) or is_retired_model(model):
        selected = str(engine_id or model)
        raise ModelRetiredError(
            f"Modelo removido pelo proprietario em 15/11/2026: {selected}. "
            "Escolha explicitamente um motor disponivel."
        )


def workflow_retired_assets(workflow: Any) -> list[str]:
    """Inspect model-loader inputs, not prompt prose or historical metadata."""
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            inputs = value.get("inputs")
            if isinstance(inputs, dict):
                for key, item in inputs.items():
                    if key in _MODEL_INPUTS and isinstance(item, str) and is_retired_model(item):
                        found.add(item)
            for item in value.values():
                if isinstance(item, (dict, list)):
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(workflow)
    return sorted(found)


def require_workflow_allowed(workflow: Any) -> None:
    assets = workflow_retired_assets(workflow)
    if assets:
        raise ModelRetiredError(
            "Workflow usa modelo removido pelo proprietario em 15/11/2026: "
            + ", ".join(assets) + ". Escolha explicitamente um workflow de motor disponivel."
        )
