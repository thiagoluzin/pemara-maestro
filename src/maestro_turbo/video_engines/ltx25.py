"""Stateless LTX 2.5 adapter and compatibility policy."""

from __future__ import annotations

from typing import Any

from maestro_turbo.anchor_intelligence.compiler_ltx25 import compile_ltx25_prompt, ltx25_frame_count

from .base import BaseVideoEngine, EngineError


LTX25_VERSION = "Lightricks/LTX-2.5@5e6e71018ee1756ed329b697a7b4aedc934dfce9"
LTX25_NODE_COMMIT = "15d09abb5a187a8dcaea2fc31fe51ee96e6c9d0d"
OFFICIAL_WORKFLOWS = (
    "LTX-2.5_T2V_I2V_Two_Stage_Distilled.json",
    "LTX-2.5_T2V_I2V_Single_Stage_Distilled.json",
    "LTX-2.5_A2V_Two_Stage_Distilled.json",
    "LTX-2.5_T2A_Single_Stage_Distilled.json",
    "LTX-2.5_ICLoRA_Union_Control_Distilled.json",
    "LTX-2.5_V2V_ICLoRA_Single_Stage_Distilled.json",
    "LTX-2.5_ICLoRA_Ingredients_Single_Stage_Distilled.json",
    "LTX-2.5_ICLoRA_Motion_Track_Distilled.json",
    "LTX-2.5_ICLoRA_Inpaint_Two_Stage_Distilled.json",
    "LTX-2.5_ICLoRA_Outpaint_Two_Stage_Distilled.json",
)


class Ltx25VideoEngine(BaseVideoEngine):
    id = "ltx_2_5"
    display_name = "LTX 2.5"

    def capabilities(self) -> dict[str, Any]:
        return {
            "t2v": True,
            "i2v": True,
            "a2v": True,
            "t2a": True,
            "native_audio": True,
            "two_stage": True,
            "ic_lora": ["union_control", "v2v", "ingredients", "motion_track", "inpaint", "outpaint"],
            "frame_rule": "8n+1",
            "fps": [24],
            "duration_seconds": {"min": 1, "max": 30},
        }

    def readiness(self) -> dict[str, Any]:
        value = self.runtime_attestation
        install_ready = bool(
            value.get("core_assets_verified")
            and value.get("workflows_verified")
            and value.get("node_commit") == LTX25_NODE_COMMIT
            and value.get("model_version") == LTX25_VERSION
        )
        smoke_ready = bool(install_ready and value.get("gpu_smoke_pass"))
        state = "READY" if smoke_ready else "READY_FOR_GPU_SMOKE" if install_ready else "UNATTESTED"
        return {
            "state": state,
            "ready": install_ready,
            "production_ready": smoke_ready,
            "gpu_smoke_required": not smoke_ready,
            "runtime_attestation_required": not install_ready,
            "compatibility_asset_policy": "allowlisted_ltx23_ic_lora_only",
        }

    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        width = int(request.get("width") or 960)
        height = int(request.get("height") or 544)
        fps = float(request.get("fps") or 24.0)
        duration = float(request.get("duration_seconds") or 6.0)
        if (width, height) != (960, 544):
            raise EngineError("LTX25_PROFILE_GEOMETRY_INVALID", "O perfil fixado exige primeiro estágio 960x544.")
        if fps != 24.0:
            raise EngineError("LTX25_FPS_INVALID", "O perfil fixado exige 24 FPS.")
        if not 1 <= duration <= 30:
            raise EngineError("LTX25_DURATION_INVALID", "LTX 2.5 aceita duração entre 1 e 30 segundos.")
        value = dict(request)
        value.update(
            {
                "width": width,
                "height": height,
                "fps": fps,
                "duration_seconds": duration,
                "num_frames": ltx25_frame_count(duration, fps),
            }
        )
        return value

    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        value = self.validate_request(request)
        return compile_ltx25_prompt(
            anchor_contract,
            duration_seconds=value["duration_seconds"],
            fps=value["fps"],
            width=value["width"],
            height=value["height"],
        )

    def build_workflow_descriptor(self, request: dict[str, Any]) -> dict[str, Any]:
        value = self.validate_request(request)
        workflow_id = str(request.get("workflow_id") or OFFICIAL_WORKFLOWS[0])
        if workflow_id not in OFFICIAL_WORKFLOWS:
            raise EngineError("LTX25_WORKFLOW_NOT_ALLOWED", "Workflow fora do catálogo LTX 2.5 fixado.")
        return {
            "engine_id": self.id,
            "workflow_id": workflow_id,
            "model_version": LTX25_VERSION,
            "node_commit": LTX25_NODE_COMMIT,
            "parameters": value,
            "fallback_allowed": False,
        }
