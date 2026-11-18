"""Deterministic LTX 2.5 API workflow derived from the pinned official graph.

The editor workflow is exported once through the matching ComfyUI frontend. At
runtime this module verifies that export byte-for-byte, disables the optional
prompt enhancer, binds the compiled Maestro prompt directly, and patches only
the declared generation inputs. No engine fallback is implemented here.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


LTX25_API_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "ferramentas"
    / "video_global_engine"
    / "workflows"
    / "ltx25"
    / "LTX-2.5_T2V_I2V_Two_Stage_Distilled.api.json"
)
LTX25_API_TEMPLATE_SHA256 = "01d1d5c4d2a28fe5fef4fef405fcce98e41a68c081d8e65e311a8d55b0b2652c"
LTX25_TRANSFORMER = "ltx-2.5-22b-distilled-transformer-nvfp4.safetensors"
LTX25_TEXT_ENCODER = "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors"

_OPTIONAL_PROMPT_ENHANCER_NODES = {
    "5544",
    "5575:5572",
    "5014:5549",
    "5014:5546",
    "5014:5555",
    "5014:5557",
    "5014:5560",
    "5014:5558",
    "5014:5556",
    "5014:5504",
    "5014:5505",
}


class Ltx25WorkflowError(ValueError):
    """The pinned LTX 2.5 graph or requested binding is invalid."""


def _load_template() -> dict[str, Any]:
    try:
        raw = LTX25_API_TEMPLATE.read_bytes()
    except OSError as exc:
        raise Ltx25WorkflowError(f"Workflow API LTX 2.5 ausente: {LTX25_API_TEMPLATE}") from exc
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != LTX25_API_TEMPLATE_SHA256:
        raise Ltx25WorkflowError(
            "Workflow API LTX 2.5 divergiu do export oficial fixado: "
            f"{actual_sha256}."
        )
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise Ltx25WorkflowError("Workflow API LTX 2.5 nao contem JSON valido.") from exc
    if not isinstance(payload, dict):
        raise Ltx25WorkflowError("Workflow API LTX 2.5 deve ser um objeto JSON.")
    return copy.deepcopy(payload)


def _node(workflow: dict[str, Any], node_id: str, class_type: str | None = None) -> dict[str, Any]:
    value = workflow.get(node_id)
    if not isinstance(value, dict):
        raise Ltx25WorkflowError(f"No obrigatorio ausente no workflow LTX 2.5: {node_id}.")
    if class_type and value.get("class_type") != class_type:
        raise Ltx25WorkflowError(
            f"No {node_id} mudou de tipo: {value.get('class_type')} != {class_type}."
        )
    inputs = value.get("inputs")
    if not isinstance(inputs, dict):
        raise Ltx25WorkflowError(f"No {node_id} nao possui inputs validos.")
    return value


def _sanitize_prompt_path(workflow: dict[str, Any]) -> None:
    for node_id in _OPTIONAL_PROMPT_ENHANCER_NODES:
        workflow.pop(node_id, None)
    _node(workflow, "5014:2483", "CLIPTextEncode")["inputs"]["text"] = ["5508", 0]
    conditioning = _node(workflow, "5014:1241", "LTXVConditioning")
    _node(workflow, "5516:4828", "CFGGuider")["inputs"].update(
        {"positive": ["5014:1241", 0], "negative": ["5014:1241", 1]}
    )
    _node(workflow, "5517:4964", "CFGGuider")["inputs"].update(
        {"positive": ["5014:1241", 0], "negative": ["5014:1241", 1]}
    )
    if conditioning.get("class_type") != "LTXVConditioning":
        raise Ltx25WorkflowError("Condicionamento LTX 2.5 inesperado.")


def _bind_two_anchors(workflow: dict[str, Any], end_image_name: str) -> None:
    workflow["2005"] = {
        "class_type": "LoadImage",
        "inputs": {"image": end_image_name},
    }
    workflow["5014:4991"] = {
        "class_type": "ResizeImageMaskNode",
        "inputs": {
            "resize_type": "scale longer dimension",
            "resize_type.longer_size": 1536,
            "scale_method": "lanczos",
            "input": ["2005", 0],
        },
    }
    workflow["5514:3337"] = {
        "class_type": "LTXVPreprocess",
        "inputs": {"img_compression": 18, "image": ["5014:4991", 0]},
    }
    workflow["9101"] = {
        "class_type": "LTXVAddGuide",
        "inputs": {
            "positive": ["5014:1241", 0],
            "negative": ["5014:1241", 1],
            "vae": ["5575:5571", 0],
            "latent": ["5514:3059", 0],
            "image": ["5514:3336", 0],
            "frame_idx": 0,
            "strength": 0.9,
        },
    }
    workflow["9102"] = {
        "class_type": "LTXVAddGuide",
        "inputs": {
            "positive": ["9101", 0],
            "negative": ["9101", 1],
            "vae": ["5575:5571", 0],
            "latent": ["9101", 2],
            "image": ["5514:3337", 0],
            "frame_idx": -1,
            "strength": 0.9,
        },
    }
    workflow.pop("5514:3159", None)
    workflow.pop("5517:4970", None)
    _node(workflow, "5514:4528", "LTXVConcatAVLatent")["inputs"]["video_latent"] = ["9102", 2]
    _node(workflow, "5516:4828", "CFGGuider")["inputs"].update(
        {"positive": ["9102", 0], "negative": ["9102", 1]}
    )
    workflow["9201"] = {
        "class_type": "LTXVCropGuides",
        "inputs": {
            "positive": ["9102", 0],
            "negative": ["9102", 1],
            "latent": ["5516:4845", 0],
        },
    }
    _node(workflow, "5517:4975", "LTXVLatentUpsampler")["inputs"]["samples"] = ["9201", 2]
    _node(workflow, "5517:4969", "LTXVConcatAVLatent")["inputs"]["video_latent"] = ["5517:4975", 0]
    _node(workflow, "5517:4964", "CFGGuider")["inputs"].update(
        {"positive": ["9201", 0], "negative": ["9201", 1]}
    )
    workflow["9202"] = {
        "class_type": "LTXVCropGuides",
        "inputs": {
            "positive": ["9201", 0],
            "negative": ["9201", 1],
            "latent": ["5517:4973", 0],
        },
    }
    _node(workflow, "5518:5538", "VAEDecodeTiled")["inputs"]["samples"] = ["9202", 2]


def build_ltx25_i2v_workflow(
    *,
    prompt: str,
    negative: str,
    base_image_name: str,
    end_image_name: str = "",
    width: int = 960,
    height: int = 544,
    frames: int = 145,
    fps: float = 24.0,
    seed: int = 42,
    filename_prefix: str = "maestro_generative/video/ltx25",
    include_native_audio: bool = False,
) -> dict[str, Any]:
    """Build a pinned one- or two-anchor LTX 2.5 two-stage API prompt."""

    prompt = str(prompt or "").strip()
    negative = str(negative or "").strip()
    base_image_name = str(base_image_name or "").strip()
    end_image_name = str(end_image_name or "").strip()
    if not prompt:
        raise Ltx25WorkflowError("Prompt LTX 2.5 vazio.")
    if not base_image_name:
        raise Ltx25WorkflowError("LTX 2.5 I2V exige imagem-ancora inicial.")
    if (int(width), int(height)) != (960, 544):
        raise Ltx25WorkflowError("O workflow LTX 2.5 fixado exige primeiro estagio 960x544.")
    if float(fps) != 24.0:
        raise Ltx25WorkflowError("O workflow LTX 2.5 fixado exige 24 FPS.")
    frames = int(frames)
    if not 25 <= frames <= 721 or (frames - 1) % 8:
        raise Ltx25WorkflowError("LTX 2.5 exige 8n+1 quadros entre 25 e 721.")

    workflow = _load_template()
    _sanitize_prompt_path(workflow)
    _node(workflow, "2004", "LoadImage")["inputs"]["image"] = base_image_name
    _node(workflow, "5508", "PrimitiveStringMultiline")["inputs"]["value"] = prompt
    _node(workflow, "5509", "PrimitiveStringMultiline")["inputs"]["value"] = negative
    _node(workflow, "5511", "PrimitiveFloat")["inputs"]["value"] = 24.0
    _node(workflow, "5014:4988", "PrimitiveInt")["inputs"]["value"] = frames
    _node(workflow, "5014:5506", "PrimitiveBoolean")["inputs"]["value"] = True
    _node(workflow, "5514:3059", "EmptyLTXVLatentVideo")["inputs"].update(
        {"width": 960, "height": 544, "length": frames, "batch_size": 1}
    )
    _node(workflow, "5575:5569", "UNETLoader")["inputs"].update(
        {"unet_name": LTX25_TRANSFORMER, "weight_dtype": "default"}
    )
    _node(workflow, "5575:5574", "CLIPLoader")["inputs"].update(
        {"clip_name": LTX25_TEXT_ENCODER, "type": "ltxv", "device": "default"}
    )
    _node(workflow, "5516:4832", "RandomNoise")["inputs"]["noise_seed"] = int(seed)
    _node(workflow, "5517:4967", "RandomNoise")["inputs"]["noise_seed"] = int(seed)
    _node(workflow, "4852", "SaveVideo")["inputs"]["filename_prefix"] = str(filename_prefix)
    _node(workflow, "5514:3159", "LTXVImgToVideoInplace")["inputs"]["strength"] = 0.9
    if end_image_name:
        _bind_two_anchors(workflow, end_image_name)
    if not include_native_audio:
        _node(workflow, "5518:4849", "CreateVideo")["inputs"].pop("audio", None)
    validate_ltx25_api_workflow(workflow, expect_end_anchor=bool(end_image_name))
    return workflow


def validate_ltx25_api_workflow(
    workflow: dict[str, Any], *, expect_end_anchor: bool | None = None
) -> None:
    """Fail closed on drift, external prompt enhancement, or broken links."""

    forbidden_types = {"TextGenerateLTX2Prompt", "GemmaAPITextEncode"}
    types = {str(node.get("class_type") or "") for node in workflow.values() if isinstance(node, dict)}
    if types & forbidden_types:
        raise Ltx25WorkflowError("O workflow LTX 2.5 ainda contem aprimorador de prompt externo.")
    load_images = [node for node in workflow.values() if node.get("class_type") == "LoadImage"]
    if expect_end_anchor is True and len(load_images) != 2:
        raise Ltx25WorkflowError("O workflow LTX 2.5 de duas ancoras deve carregar duas imagens.")
    if expect_end_anchor is False and len(load_images) != 1:
        raise Ltx25WorkflowError("O workflow LTX 2.5 I2V deve carregar uma imagem.")
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            raise Ltx25WorkflowError(f"No invalido no workflow LTX 2.5: {node_id}.")
        for name, value in node["inputs"].items():
            if (
                isinstance(value, list)
                and len(value) == 2
                and isinstance(value[0], str)
                and value[0] not in workflow
            ):
                raise Ltx25WorkflowError(f"Link quebrado em {node_id}.{name}: {value[0]}.")
    if expect_end_anchor:
        if workflow.get("9102", {}).get("inputs", {}).get("frame_idx") != -1:
            raise Ltx25WorkflowError("A ancora final LTX 2.5 deve usar frame_idx=-1.")
        if workflow.get("9102", {}).get("inputs", {}).get("strength") != 0.9:
            raise Ltx25WorkflowError("A ancora final LTX 2.5 deve usar forca 0.9.")
        if workflow.get("5517:4975", {}).get("inputs", {}).get("samples") != ["9201", 2]:
            raise Ltx25WorkflowError("O segundo estagio deve consumir o latent recortado.")
        if workflow.get("5518:5538", {}).get("inputs", {}).get("samples") != ["9202", 2]:
            raise Ltx25WorkflowError("O decoder deve consumir o latent final recortado.")

