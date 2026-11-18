"""Stateless MiniMax H3 adapter."""

from __future__ import annotations

from typing import Any

from maestro_turbo.anchor_intelligence.compiler_h3 import compile_h3_prompt

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
        }

    def readiness(self) -> dict[str, Any]:
        attestation = self.runtime_attestation
        ready = bool(attestation.get("production_ready") and attestation.get("components_verified"))
        return {
            "state": "READY" if ready else "UNATTESTED",
            "ready": ready,
            "production_ready": ready,
            "runtime_attestation_required": not ready,
        }

    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        duration = float(request.get("duration_seconds") or 6.0)
        if not 4 <= duration <= 15:
            raise EngineError("H3_DURATION_INVALID", "MiniMax H3 aceita duração entre 4 e 15 segundos.")
        value = dict(request)
        value.update({"duration_seconds": duration, "fps": 24.0, "steps": 20, "guidance": 1.0})
        return value

    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        value = self.validate_request(request)
        return compile_h3_prompt(anchor_contract, duration_seconds=value["duration_seconds"])

    def build_workflow_descriptor(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "engine_id": self.id,
            "workflow_family": "minimax_h3",
            "parameters": self.validate_request(request),
            "fallback_allowed": False,
        }
