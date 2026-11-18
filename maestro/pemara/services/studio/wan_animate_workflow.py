"""Pinned Wan2.2 Animate Move-mode workflows and fail-closed graph gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


WAN22_ANIMATE_PROFILE = "wan22_animate_dwpose_move_bf16_vertical_v1"
WAN22_ANIMATE_MODEL_NAME = "wan2.2_animate_14B_bf16.safetensors"
WAN21_ANIMATE_VAE = "wan_2.1_vae.safetensors"
WAN_ANIMATE_TEXT_ENCODER = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
WAN_ANIMATE_CLIP_VISION = "clip_vision_h.safetensors"
WAN_ANIMATE_NATIVE_FPS = 30
WAN_ANIMATE_CHUNK_FRAMES = 77
WAN_ANIMATE_CONTINUE_FRAMES = 5
WAN_ANIMATE_DEFAULT_STEPS = 20
WAN_ANIMATE_DEFAULT_CFG = 1.0
WAN_ANIMATE_VERTICAL_WIDTH = 720
WAN_ANIMATE_VERTICAL_HEIGHT = 1280


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_destination(base_dir: Path, item: dict[str, Any]) -> Path:
    if item["destination_root"] == "comfy_models":
        root = base_dir / "ferramentas" / "ComfyUI" / "models"
    elif item["destination_root"] == "dwpose_ckpts":
        root = (
            base_dir
            / "ferramentas"
            / "ComfyUI"
            / "custom_nodes"
            / "comfyui_controlnet_aux"
            / "ckpts"
        )
    else:
        raise ValueError(f"Raiz Wan Animate nao suportada: {item['destination_root']}")
    relative = Path(item.get("destination_filename") or item["filename"])
    return root / relative


def kit_status(base_dir: Path, *, verify_hash: bool = False) -> dict[str, Any]:
    lock_path = base_dir / "tools" / "model_installers" / "models.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    artifacts = [
        item for item in lock.get("artifacts", [])
        if item.get("component") == "wan_animate"
    ]
    details: list[dict[str, Any]] = []
    ready = bool(artifacts)
    for item in artifacts:
        path = _artifact_destination(base_dir, item)
        exists = path.is_file()
        size_ok = exists and path.stat().st_size == int(item["expected_bytes"])
        hash_ok = None
        if verify_hash and size_ok:
            hash_ok = _sha256(path) == str(item["sha256"]).lower()
        artifact_ready = bool(size_ok and (hash_ok is not False))
        ready = ready and artifact_ready
        details.append({
            "id": item["id"],
            "path": str(path),
            "exists": exists,
            "sizeOk": bool(size_ok),
            "hashOk": hash_ok,
            "ready": artifact_ready,
        })
    return {
        "profile": WAN22_ANIMATE_PROFILE,
        "model": WAN22_ANIMATE_MODEL_NAME,
        "ready": bool(ready),
        "hashVerified": bool(verify_hash and ready),
        "nativeFps": WAN_ANIMATE_NATIVE_FPS,
        "moveMode": True,
        "poseVideoInput": True,
        "faceTransferDefault": False,
        "artifacts": details,
    }


def _chunk_lengths(total_frames: int) -> list[int]:
    if total_frames < 25:
        raise ValueError("Wan Animate exige ao menos 25 quadros.")
    first = min(WAN_ANIMATE_CHUNK_FRAMES, total_frames)
    lengths = [first]
    produced = first
    per_extension = WAN_ANIMATE_CHUNK_FRAMES - WAN_ANIMATE_CONTINUE_FRAMES
    while produced < total_frames:
        new_frames = min(per_extension, total_frames - produced)
        lengths.append(new_frames + WAN_ANIMATE_CONTINUE_FRAMES)
        produced += new_frames
    return lengths


def build_dwpose_preview_workflow(
    *,
    driver_video_name: str,
    prefix: str,
    width: int = 720,
    height: int = 1280,
    frames: int = 451,
    fps: int = WAN_ANIMATE_NATIVE_FPS,
) -> dict[str, Any]:
    if not driver_video_name:
        raise ValueError("DWPose exige um video-driver RGB real.")
    if fps != WAN_ANIMATE_NATIVE_FPS:
        raise ValueError("A previa DWPose deve ser normalizada em 30 FPS.")
    workflow = {
        "1": {"class_type": "VHS_LoadVideo", "inputs": {
            "video": driver_video_name,
            "force_rate": fps,
            "custom_width": width,
            "custom_height": height,
            "frame_load_cap": frames,
            "skip_first_frames": 0,
            "select_every_nth": 1,
        }},
        "2": {"class_type": "DWPreprocessor", "inputs": {
            "image": ["1", 0],
            "detect_hand": "enable",
            "detect_body": "enable",
            "detect_face": "disable",
            "resolution": min(width, height),
            "bbox_detector": "yolox_l.onnx",
            "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
            "scale_stick_for_xinsr_cn": "disable",
        }},
        "3": {"class_type": "SaveWEBM", "inputs": {
            "images": ["2", 0],
            "filename_prefix": prefix,
            "codec": "vp9",
            "fps": fps,
            "crf": 14.0,
        }},
    }
    validate_dwpose_preview_graph(workflow)
    return workflow


def validate_dwpose_preview_graph(workflow: dict[str, Any]) -> dict[str, Any]:
    dw_nodes = [node for node in workflow.values() if node.get("class_type") == "DWPreprocessor"]
    if len(dw_nodes) != 1:
        raise ValueError("DWPOSE_GRAPH_INVALID: deve existir exatamente um DWPreprocessor.")
    inputs = dw_nodes[0].get("inputs", {})
    if inputs.get("detect_body") != "enable" or inputs.get("detect_hand") != "enable":
        raise ValueError("DWPOSE_BODY_HANDS_REQUIRED: corpo e maos precisam estar ligados.")
    if inputs.get("detect_face") != "disable":
        raise ValueError("DWPOSE_FACE_FORBIDDEN: transferencia facial nao foi autorizada.")
    source = inputs.get("image")
    if not isinstance(source, list) or str(source[0]) not in workflow:
        raise ValueError("DWPOSE_DRIVER_DISCONNECTED: video-driver nao chega ao DWPose.")
    if workflow[str(source[0])].get("class_type") != "VHS_LoadVideo":
        raise ValueError("DWPOSE_DRIVER_INVALID: a origem deve ser um video real carregado.")
    saves = [node for node in workflow.values() if node.get("class_type") == "SaveWEBM"]
    if not saves or saves[0].get("inputs", {}).get("images") != ["2", 0]:
        raise ValueError("DWPOSE_PREVIEW_DISCONNECTED: a pose nao chega ao arquivo de revisao.")
    return {"ok": True, "faceTransfer": False, "body": True, "hands": True}


def build_move_workflow(
    *,
    prompt: str,
    negative: str,
    reference_image_name: str,
    approved_pose_video_name: str,
    prefix: str,
    width: int = 720,
    height: int = 1280,
    frames: int = 451,
    fps: int = WAN_ANIMATE_NATIVE_FPS,
    steps: int = WAN_ANIMATE_DEFAULT_STEPS,
    cfg: float = WAN_ANIMATE_DEFAULT_CFG,
    seed: int = 1,
) -> dict[str, Any]:
    if not reference_image_name or not approved_pose_video_name:
        raise ValueError("Wan Animate Move exige imagem aprovada e video DWPose aprovado.")
    if fps != WAN_ANIMATE_NATIVE_FPS:
        raise ValueError("Wan Animate Move de producao exige 30 FPS.")
    if (width, height) != (WAN_ANIMATE_VERTICAL_WIDTH, WAN_ANIMATE_VERTICAL_HEIGHT):
        raise ValueError(
            "WAN_ANIMATE_VERTICAL_GEOMETRY_REQUIRED: "
            f"o perfil fixado exige {WAN_ANIMATE_VERTICAL_WIDTH}x{WAN_ANIMATE_VERTICAL_HEIGHT}."
        )
    if width % 16 or height % 16:
        raise ValueError("Wan Animate exige dimensoes multiplas de 16.")
    if steps < WAN_ANIMATE_DEFAULT_STEPS:
        raise ValueError("Wan Animate BF16 de producao nao aceita reducao abaixo de 20 passos.")
    workflow: dict[str, Any] = {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": WAN22_ANIMATE_MODEL_NAME,
            "weight_dtype": "default",
        }},
        "2": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": WAN_ANIMATE_TEXT_ENCODER,
            "type": "wan",
            "device": "default",
        }},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["3", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["3", 0]}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": WAN21_ANIMATE_VAE}},
        "7": {"class_type": "LoadImage", "inputs": {"image": reference_image_name}},
        "8": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": WAN_ANIMATE_CLIP_VISION}},
        "9": {"class_type": "CLIPVisionEncode", "inputs": {
            "clip_vision": ["8", 0], "image": ["7", 0], "crop": "none",
        }},
        "10": {"class_type": "VHS_LoadVideo", "inputs": {
            "video": approved_pose_video_name,
            "force_rate": fps,
            "custom_width": width,
            "custom_height": height,
            "frame_load_cap": frames,
            "skip_first_frames": 0,
            "select_every_nth": 1,
        }},
    }
    node_id = 20
    accumulated_images: list[Any] | None = None
    previous_offset: list[Any] | int = 0
    for index, chunk_length in enumerate(_chunk_lengths(frames)):
        wan_id = str(node_id)
        sampler_id = str(node_id + 1)
        trim_id = str(node_id + 2)
        decode_id = str(node_id + 3)
        slice_id = str(node_id + 4)
        wan_inputs: dict[str, Any] = {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "vae": ["6", 0],
            "width": width,
            "height": height,
            "length": chunk_length,
            "batch_size": 1,
            "continue_motion_max_frames": WAN_ANIMATE_CONTINUE_FRAMES,
            "video_frame_offset": previous_offset,
            "clip_vision_output": ["9", 0],
            "reference_image": ["7", 0],
            "pose_video": ["10", 0],
        }
        if accumulated_images is not None:
            wan_inputs["continue_motion"] = accumulated_images
        workflow[wan_id] = {"class_type": "WanAnimateToVideo", "inputs": wan_inputs}
        workflow[sampler_id] = {"class_type": "KSampler", "inputs": {
            "model": ["2", 0],
            "seed": int(seed),
            "steps": int(steps),
            "cfg": float(cfg),
            "sampler_name": "euler",
            "scheduler": "simple",
            "positive": [wan_id, 0],
            "negative": [wan_id, 1],
            "latent_image": [wan_id, 2],
            "denoise": 1.0,
        }}
        workflow[trim_id] = {"class_type": "TrimVideoLatent", "inputs": {
            "samples": [sampler_id, 0], "trim_amount": [wan_id, 3],
        }}
        workflow[decode_id] = {"class_type": "VAEDecode", "inputs": {
            "samples": [trim_id, 0], "vae": ["6", 0],
        }}
        workflow[slice_id] = {"class_type": "ImageFromBatch", "inputs": {
            "image": [decode_id, 0], "batch_index": [wan_id, 4], "length": 4096,
        }}
        new_images: list[Any] = [slice_id, 0]
        if accumulated_images is None:
            accumulated_images = new_images
            node_id += 5
        else:
            batch_id = str(node_id + 5)
            workflow[batch_id] = {"class_type": "ImageBatch", "inputs": {
                "image1": accumulated_images, "image2": new_images,
            }}
            accumulated_images = [batch_id, 0]
            node_id += 6
        previous_offset = [wan_id, 5]
    save_id = str(node_id)
    workflow[save_id] = {"class_type": "SaveWEBM", "inputs": {
        "images": accumulated_images,
        "filename_prefix": prefix,
        "codec": "vp9",
        "fps": fps,
        "crf": 14.0,
    }}
    validate_move_graph(workflow)
    return workflow


def validate_move_graph(workflow: dict[str, Any]) -> dict[str, Any]:
    classes = [str(node.get("class_type") or "") for node in workflow.values()]
    if classes.count("UNETLoader") != 1:
        raise ValueError("WAN_ANIMATE_MODEL_GATE: grafo deve carregar um unico checkpoint.")
    loader = next(node for node in workflow.values() if node.get("class_type") == "UNETLoader")
    if loader.get("inputs", {}).get("unet_name") != WAN22_ANIMATE_MODEL_NAME:
        raise ValueError("WAN_ANIMATE_MODEL_MISMATCH: somente o BF16 fixado e autorizado.")
    if "LoraLoaderModelOnly" in classes:
        raise ValueError("WAN_ANIMATE_QUALITY_GATE: LoRA aceleradora nao autorizada em producao.")
    video_loaders = {
        node_id: node
        for node_id, node in workflow.items()
        if node.get("class_type") == "VHS_LoadVideo"
    }
    if len(video_loaders) != 1:
        raise ValueError("WAN_ANIMATE_POSE_SOURCE_INVALID: deve existir um unico video DWPose aprovado.")
    pose_source_id = next(iter(video_loaders))
    if int(video_loaders[pose_source_id].get("inputs", {}).get("force_rate") or 0) != 30:
        raise ValueError("WAN_ANIMATE_FPS_GATE: video de pose deve entrar em 30 FPS.")
    wan_nodes = [node for node in workflow.values() if node.get("class_type") == "WanAnimateToVideo"]
    if not wan_nodes:
        raise ValueError("WAN_ANIMATE_NODE_MISSING: nao existe condicionamento de pose.")
    for node in wan_nodes:
        inputs = node.get("inputs", {})
        if (
            int(inputs.get("width") or 0),
            int(inputs.get("height") or 0),
        ) != (WAN_ANIMATE_VERTICAL_WIDTH, WAN_ANIMATE_VERTICAL_HEIGHT):
            raise ValueError(
                "WAN_ANIMATE_VERTICAL_GEOMETRY_REQUIRED: "
                "todos os chunks devem permanecer em 720x1280."
            )
        if inputs.get("pose_video") != [pose_source_id, 0]:
            raise ValueError("WAN_ANIMATE_POSE_DISCONNECTED: pose_video nao recebe o asset aprovado.")
        for forbidden in ("face_video", "background_video", "character_mask"):
            if forbidden in inputs:
                raise ValueError(f"WAN_ANIMATE_MOVE_MODE_REQUIRED: entrada {forbidden} deve ficar desconectada.")
    saves = [node for node in workflow.values() if node.get("class_type") == "SaveWEBM"]
    if len(saves) != 1 or int(saves[0].get("inputs", {}).get("fps") or 0) != 30:
        raise ValueError("WAN_ANIMATE_OUTPUT_FPS_GATE: saida revisavel deve ser 30 FPS.")
    return {
        "ok": True,
        "model": WAN22_ANIMATE_MODEL_NAME,
        "poseConnected": True,
        "moveMode": True,
        "faceTransfer": False,
        "chunks": len(wan_nodes),
        "fps": 30,
    }
