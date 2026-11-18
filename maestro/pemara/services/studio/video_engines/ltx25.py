"""LTX 2.5 adapter with locked assets and official workflows."""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from anchor_intelligence.compiler_ltx25 import compile_ltx25_prompt, ltx25_frame_count
from model_readiness import component_status
from ltx25_workflow import LTX25_API_TEMPLATE, LTX25_API_TEMPLATE_SHA256

from .base import BaseVideoEngine, EngineError


LTX25_MODEL_NAME = "ltx-2.5-22b-distilled-transformer-nvfp4.safetensors"
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
            "base_delivery": ["960x544", "544x960"],
        }

    def _node_state(self) -> dict[str, Any]:
        candidates = (
            Path("D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara")
            / "custom_nodes"
            / "ComfyUI-LTXVideo",
            self.workspace_root / "ferramentas" / "ComfyUI" / "custom_nodes" / "ComfyUI-LTXVideo",
        )
        root = next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])
        commit = ""
        if (root / ".git").exists():
            try:
                commit = subprocess.run(
                    ["git", "-C", str(root), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                commit = ""
        legacy_workflows = list((root / "example_workflows" / "2.3").glob("*.json"))
        return {
            "path": str(root),
            "exists": root.is_dir(),
            "commit": commit,
            "legacy_workflow_count": len(legacy_workflows),
            "ok": commit == LTX25_NODE_COMMIT and not legacy_workflows,
        }

    def _workflow_state(self) -> list[dict[str, Any]]:
        roots = (
            self.workspace_root / "ferramentas" / "video_global_engine" / "workflows" / "ltx25",
            Path("D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara") / "custom_nodes" / "ComfyUI-LTXVideo" / "example_workflows" / "2.5",
            self.workspace_root / "ferramentas" / "ComfyUI" / "custom_nodes" / "ComfyUI-LTXVideo" / "example_workflows" / "2.5",
        )
        workflows = [
            {
                "id": name,
                "path": str(next((root / name for root in roots if (root / name).is_file()), roots[0] / name)),
                "ok": any((root / name).is_file() for root in roots),
            }
            for name in OFFICIAL_WORKFLOWS
        ]
        try:
            api_sha256 = hashlib.sha256(LTX25_API_TEMPLATE.read_bytes()).hexdigest()
        except OSError:
            api_sha256 = ""
        workflows.append(
            {
                "id": LTX25_API_TEMPLATE.name,
                "path": str(LTX25_API_TEMPLATE),
                "sha256": api_sha256,
                "ok": api_sha256 == LTX25_API_TEMPLATE_SHA256,
                "kind": "comfy_api_export",
            }
        )
        return workflows

    def _gpu_smoke_receipt(self) -> dict[str, Any]:
        path = self.workspace_root / "ferramentas" / "video_global_engine" / "receipts" / "ltx25_gpu_smoke.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"ok": False, "path": str(path), "status": "MISSING"}
        output_sha = str(payload.get("output_sha256") or "").lower()
        ok = bool(
            payload.get("status") == "PASS"
            and payload.get("engine_id") == self.id
            and payload.get("model_version") == LTX25_VERSION
            and payload.get("node_commit") == LTX25_NODE_COMMIT
            and payload.get("workflow_id") in OFFICIAL_WORKFLOWS
            and re.fullmatch(r"[a-f0-9]{64}", output_sha)
            and payload.get("technical_qc_pass") is True
        )
        return {
            "ok": ok,
            "path": str(path),
            "status": "PASS" if ok else "INVALID",
            "workflow_id": payload.get("workflow_id"),
            "output_sha256": output_sha if ok else "",
            "owner_approval_state": payload.get("owner_approval_state") or "PENDING_HUMAN_REVIEW",
        }

    def readiness(self, *, verify_hash: bool = False) -> dict[str, Any]:
        assets = component_status(self.workspace_root, "ltx25", verify_hash=verify_hash)
        required_assets = [item for item in assets if item.get("required")]
        node = self._node_state()
        workflows = self._workflow_state()
        manifest_present = bool(assets)
        assets_ok = bool(required_assets) and all(item.get("ok") for item in required_assets)
        workflows_ok = all(item.get("ok") for item in workflows)
        ready_for_smoke = bool(self.comfy_online and manifest_present and assets_ok and node["ok"] and workflows_ok)
        smoke = self._gpu_smoke_receipt()
        production_ready = bool(ready_for_smoke and smoke.get("ok"))
        if production_ready:
            state = "READY"
            message = "LTX 2.5 passou instalacao, workflow e smoke GPU registrado."
        elif ready_for_smoke:
            state = "READY_FOR_GPU_SMOKE"
            message = "LTX 2.5 completo nos gates sem GPU; smoke real aguarda autorizacao do proprietario."
        elif manifest_present:
            state = "PARTIAL"
            message = "LTX 2.5 ainda possui componentes ausentes ou nao verificados."
        else:
            state = "MISSING"
            message = "Manifest LTX 2.5 ainda nao foi instalado."
        return {
            "state": state,
            "ready": ready_for_smoke,
            "production_ready": production_ready,
            "gpu_smoke_required": not production_ready,
            "message": message,
            "version_receipt": LTX25_VERSION,
            "node": node,
            "assets": assets,
            "workflows": workflows,
            "gpu_smoke_receipt": smoke,
            "compatibility_asset_policy": "allowlisted_ltx23_ic_lora_only",
        }

    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        width = int(request.get("width") or 960)
        height = int(request.get("height") or 544)
        fps = float(request.get("fps") or 24.0)
        duration = float(request.get("duration_seconds") or request.get("video_duration") or 6.0)
        if width % 32 or height % 32:
            raise EngineError("LTX25_DIMENSIONS_INVALID", "LTX 2.5 exige largura e altura multiplas de 32.")
        if (width, height) != (960, 544):
            raise EngineError(
                "LTX25_PROFILE_GEOMETRY_INVALID",
                "O perfil LTX 2.5 Two-Stage fixado exige primeiro estagio 960x544.",
            )
        if fps != 24.0:
            raise EngineError("LTX25_FPS_INVALID", "O perfil LTX 2.5 fixado exige 24 FPS.")
        if not 1 <= duration <= 30:
            raise EngineError("LTX25_DURATION_INVALID", "LTX 2.5 exige duracao entre 1 e 30 segundos.")
        result = dict(request)
        result.update({"width": width, "height": height, "fps": fps, "duration_seconds": duration, "num_frames": ltx25_frame_count(duration, fps)})
        return result

    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_request(request)
        return compile_ltx25_prompt(
            anchor_contract,
            duration_seconds=validated["duration_seconds"],
            fps=validated["fps"],
            width=validated["width"],
            height=validated["height"],
        )

    def build_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_request(request)
        workflow_id = str(request.get("workflow_id") or OFFICIAL_WORKFLOWS[0])
        if workflow_id not in OFFICIAL_WORKFLOWS:
            raise EngineError("LTX25_WORKFLOW_NOT_ALLOWED", "O workflow LTX 2.5 nao pertence ao catalogo oficial preso.")
        return {
            "engine_id": self.id,
            "workflow_id": workflow_id,
            "official_node_commit": LTX25_NODE_COMMIT,
            "model": LTX25_MODEL_NAME,
            "parameters": validated,
        }

    def estimate_resources(self, request: dict[str, Any]) -> dict[str, Any]:
        profile = str(request.get("resource_profile") or "rtx5090-performance-nvfp4-int8")
        return {"profile": profile, "vram_gb": 32.0, "free_disk_gb_required": 100.0, "serial_only": True}
