"""Local HunyuanVideo 1.5 I2V, explicitly authorized on 2026-11-10."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from video_workflows import HUNYUAN15_I2V_MODEL, build_hunyuan15_i2v_workflow
from .base import BaseVideoEngine, EngineError
from retired_models import is_retired_engine, require_model_allowed


class Hunyuan15VideoEngine(BaseVideoEngine):
    id = "hunyuan_video_15"
    display_name = "HunyuanVideo 1.5"

    @property
    def manifest_path(self) -> Path:
        return self.workspace_root / "services/studio/hunyuan15_install.json"

    def capabilities(self) -> dict[str, Any]:
        return {"t2v": False, "i2v": True, "first_last_frame": False,
                "reference_images": False, "native_audio": False, "fps": [24],
                "duration_seconds": {"min": 5, "max": 10},
                "delivery": ["1280x720", "720x1280"], "frame_rule": "4n+1",
                "default_steps": 50, "allowed_steps": [15, 25, 50], "default_guidance": 6.0,
                "acceleration": {"attention": "sage2_cuda_safe_masks", "cache": "easycache",
                                 "dynamic_vram": False, "torch_compile": False},
                "model": HUNYUAN15_I2V_MODEL}

    def readiness(self, *, verify_hash: bool = False) -> dict[str, Any]:
        if is_retired_engine(self.id):
            return {"state": "REMOVED", "ready": False, "production_ready": False,
                    "message": "HunyuanVideo 1.5 removido pelo proprietario em 15/11/2026; historico preservado."}
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            manifest = {}
        assets = []
        for asset in manifest.get("assets", []):
            path = Path(asset["path"])
            stat = path.stat() if path.is_file() else None
            ok = bool(stat and stat.st_size == asset["expected_bytes"]
                      and stat.st_mtime_ns == asset.get("verified_mtime_ns")
                      and asset.get("verified_sha256") == asset.get("sha256"))
            if verify_hash and stat and stat.st_size == asset["expected_bytes"]:
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                ok = ok and digest == asset["sha256"]
            assets.append({"name": asset["filename"], "ok": ok,
                           "expected_bytes": asset["expected_bytes"],
                           "actual_bytes": stat.st_size if stat else 0})
        ready = bool(self.comfy_online and len(assets) == 5 and all(a["ok"] for a in assets)
                     and manifest.get("mcp_workflow_valid") is True)
        return {"state": "READY" if ready else "PARTIAL", "ready": ready,
                "production_ready": ready, "assets": assets,
                "gpu_generation_tested": bool(manifest.get("gpu_generation_tested")),
                "artistic_approval": "PENDING_OWNER_REVIEW",
                "message": (("Geracao GPU concluida; qualidade visual aguarda revisao do proprietario."
                             if manifest.get("gpu_generation_tested") else
                             "Instalado e validado; primeira geracao GPU e qualidade visual ainda nao avaliadas.")
                            if ready else "HunyuanVideo 1.5 em preparacao: downloads, integridade e validacao pendentes.")}

    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        require_model_allowed(HUNYUAN15_I2V_MODEL, self.id)
        if request.get("mode") not in (None, "video", "i2v"):
            raise EngineError("HUNYUAN_I2V_ONLY", "Escolha imagem para video e forneca uma ancora aprovada.")
        if request.get("h3_model_variant") not in (None, "", "base") or request.get("h3_scene_profile") not in (None, "", "auto"):
            raise EngineError("HUNYUAN_CONTROL_UNSUPPORTED", "Variantes e perfis H3 pertencem ao motor H3.")
        if any(request.get(k) for k in ("loop", "lora", "end_image", "end_image_name", "end_image_bytes",
                "pose_video_name", "pose_video_bytes", "camera_pose", "creative_all_in_one",
                "creative_motion_request", "creative_timeline_request", "creative_fun_control_request",
                "enable_minimax_h3_native_audio", "enable_minimax_h3_live_preview")):
            raise EngineError("HUNYUAN_CONTROL_UNSUPPORTED", "Hunyuan I2V usa uma ancora inicial e prompt; controle solicitado nao qualificado.")
        width, height = int(request.get("width") or 1280), int(request.get("height") or 720)
        if (width, height) not in ((1280, 720), (720, 1280)):
            raise EngineError("HUNYUAN_GEOMETRY_INVALID", "Hunyuan I2V 720p exige 1280x720 ou 720x1280.")
        fps = float(request.get("fps") or 24)
        duration = float(request.get("duration_seconds") or request.get("video_duration") or 5)
        if fps != 24 or not math.isfinite(duration) or not 5 <= duration <= 10:
            raise EngineError("HUNYUAN_TIMING_INVALID", "Hunyuan exige 24 FPS e duracao de 5 a 10 segundos.")
        steps = int(request.get("steps") or 50)
        guidance = float(request.get("guidance") or 6)
        if steps not in (15, 25, 50) or guidance != 6:
            raise EngineError("HUNYUAN_PROFILE_INVALID", "Use 50 passos ou os testes de 15/25 passos autorizados pelo proprietario; guidance 6.")
        frames = 4 * round(duration * fps / 4) + 1
        supplied_frames = request.get("frames")
        if supplied_frames is not None and int(supplied_frames) != frames:
            raise EngineError("HUNYUAN_FRAMES_INVALID", "Quadros devem corresponder a duracao na grade 4n+1.")
        result = dict(request)
        result.update(width=width, height=height, fps=fps, steps=steps, guidance=guidance,
                      frames=frames, num_frames=frames, duration_seconds=(frames-1)/fps,
                      video_duration=(frames-1)/fps, model=HUNYUAN15_I2V_MODEL)
        return result

    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        self.validate_request(request)
        return {"engine_id": self.id, "prompt": str(request.get("prompt") or "").strip(),
                "negative": str(request.get("negative") or ""), "compiler_version": "owner-prompt-v1"}

    def build_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        spec = self.validate_request(request)
        return build_hunyuan15_i2v_workflow(prompt=str(spec.get("prompt") or ""),
            negative=str(spec.get("negative") or ""), input_image=str(spec.get("input_image") or spec.get("base_image_name") or ""),
            width=spec["width"], height=spec["height"], frames=spec["frames"], fps=spec["fps"],
            steps=spec["steps"], cfg=spec["guidance"], seed=int(spec.get("seed") or 42),
            content_kind=str(spec.get("content_kind") or "unknown"))

    def estimate_resources(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"minimum_vram_gb": 14, "offloading": True, "serial_only": True,
                "installed_assets_gb": 29.86, "profile": "720p-i2v-fp16-50steps"}
