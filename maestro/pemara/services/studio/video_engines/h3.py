"""MiniMax H3 adapter preserving the established production workflow."""

from __future__ import annotations

from typing import Any

from anchor_intelligence.compiler_h3 import compile_h3_prompt
from h3_workflow import (
    DEFAULT_H3_QUALITY_PROFILE,
    FAST_H3_MODEL_NAME,
    FAST_H3_STEPS,
    FAST_H3_VARIANT,
    FAST_H3_VARIANTS,
    OMNI_H3_VARIANT,
    OMNI_H3_MODEL_NAME,
    H3_FL2VA_MODEL_NAME,
    H3_QUALITY_PROFILES,
    WORKFLOW_VERSION,
    resolve_h3_quality_profile,
    workflow_status,
)

from h3_pika_flex import VARIANT as PIKA_FLEX_VARIANT, STEPS as PIKA_FLEX_STEPS, validate_controls as validate_pika_controls
from .base import BaseVideoEngine, EngineError


class H3VideoEngine(BaseVideoEngine):
    id = "minimax_h3"
    display_name = "MiniMax H3"

    def capabilities(self) -> dict[str, Any]:
        return {
            "t2v": True,
            "i2v": True,
            "first_last_frame": True,
            "reference_images": True,
            "native_audio": True,
            "fps": [24],
            "duration_seconds": {"min": 4, "max": 15},
            "delivery": ["1024x576", "1088x608", "1344x768", "576x1024", "608x1088", "768x1344"],
            "default_profile": DEFAULT_H3_QUALITY_PROFILE,
        }

    def readiness(self, *, verify_hash: bool = False) -> dict[str, Any]:
        status = workflow_status(self.workspace_root, comfy_online=self.comfy_online)
        ready = bool(status.get("productionReady"))
        return {
            "state": "READY" if ready else "PARTIAL",
            "ready": ready,
            "production_ready": ready,
            "message": "MiniMax H3 pronto." if ready else "MiniMax H3 requer os componentes listados.",
            "version_receipt": WORKFLOW_VERSION,
            "components": status.get("components") or [],
            "gates": {"comfy_online": self.comfy_online, "workflow_ok": bool(status.get("ok"))},
        }

    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        duration = float(request.get("duration_seconds") or request.get("video_duration") or 6.0)
        if not 4 <= duration <= 15:
            raise EngineError("H3_DURATION_INVALID", "MiniMax H3 aceita duracao entre 4 e 15 segundos.")
        variant = str(request.get("h3_model_variant") or "base").strip().lower()
        if variant not in {"base", PIKA_FLEX_VARIANT, *FAST_H3_VARIANTS}:
            raise EngineError("H3_VARIANT_INVALID", "Use MiniMax H3 Base, FastH3 V2, FastH3-Omni ou Pika Flex.")
        if variant == PIKA_FLEX_VARIANT:
            validate_pika_controls(request)
        if variant == OMNI_H3_VARIANT and any(request.get(k) for k in (
            "end_image", "end_image_name", "end_image_bytes", "last_frame",
            "guide_image", "guide_image_name", "guide_image_bytes", "creative_all_in_one",
            "creative_motion_request", "creative_timeline_request", "creative_fun_control_request",
        )):
            raise EngineError("H3_OMNI_CONTROL_UNSUPPORTED", "Omni usa referencias; ultimo quadro exato e adapters nao qualificados.")
        if variant == FAST_H3_VARIANT:
            mode = str(request.get("mode") or "text_video").strip().lower()
            if mode not in {"text_video", "t2v", "text-to-video"}:
                raise EngineError("H3_FAST_T2V_ONLY", "FastH3 8-Step V2 aceita somente texto para vídeo.")
            if any(request.get(key) for key in (
                "base_image", "base_image_name", "first_frame", "end_image",
                "reference_images", "reference_video", "guide_image",
            )):
                raise EngineError("H3_FAST_T2V_ONLY", "FastH3 não aceita âncoras, referências ou guia de imagem.")
        requested_profile = str(request.get("h3_quality_profile") or "")
        profile_id, profile, vertical = resolve_h3_quality_profile(
            requested_profile, width=request.get("width"), height=request.get("height"), steps=request.get("steps"),
            model_variant=variant,
        )
        requested_orientation = str(request.get("h3_orientation") or "").strip().lower()
        if requested_orientation and requested_orientation not in {"landscape", "portrait", "horizontal", "vertical"}:
            raise EngineError("H3_ORIENTATION_INVALID", "Use orientação horizontal ou vertical.")
        if requested_orientation:
            vertical = requested_orientation in {"portrait", "vertical"}
        allowed_steps = (PIKA_FLEX_STEPS,) if variant == PIKA_FLEX_VARIANT else (FAST_H3_STEPS,) if variant in FAST_H3_VARIANTS else profile["steps"]
        result = dict(request)
        result.update({
            "duration_seconds": duration,
            "h3_quality_profile": profile_id,
            "h3_model_variant": variant,
            "h3_orientation": "portrait" if vertical else "landscape",
            "width": profile["verticalWidth"] if vertical else profile["width"],
            "height": profile["verticalHeight"] if vertical else profile["height"],
            "steps": int(request.get("steps") or allowed_steps[0]),
            "fps": 24.0,
            "guidance": 1.0,
        })
        if result["steps"] not in allowed_steps:
            if variant in FAST_H3_VARIANTS:
                raise EngineError("H3_FAST_STEPS_REQUIRED", f"A variante FastH3 selecionada exige exatamente {FAST_H3_STEPS} passos.")
            raise EngineError("H3_PROFILE_STEPS_INVALID", f"{profile['label']} exige {min(profile['steps'])}-{max(profile['steps'])} steps.")
        if profile.get("draftOnly") or variant == FAST_H3_VARIANT:
            result["enable_minimax_h3_native_audio"] = False
        return result

    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_request(request)
        return compile_h3_prompt(anchor_contract, duration_seconds=validated["duration_seconds"])

    def build_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_request(request)
        return {
            "engine_id": self.id,
            "workflow_id": WORKFLOW_VERSION,
            "builder": "studio.main._build_minimax_h3_fl2va_workflow",
            "model": (OMNI_H3_MODEL_NAME if validated.get("h3_model_variant") == OMNI_H3_VARIANT
                      else FAST_H3_MODEL_NAME if validated.get("h3_model_variant") == FAST_H3_VARIANT else H3_FL2VA_MODEL_NAME),
            "parameters": validated,
        }

    def estimate_resources(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"profile": "rtx5090-h3-int8", "vram_gb": 30.0, "serial_only": True}
