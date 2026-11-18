"""Shared contract for Maestro video engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class EngineError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422, details: Any = None):
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class EngineSelectionRequired(EngineError):
    def __init__(self):
        super().__init__("ENGINE_SELECTION_REQUIRED", "Escolha explicitamente um motor de video disponivel antes de gerar.")


class BaseVideoEngine(ABC):
    id: str
    display_name: str

    def __init__(self, workspace_root: Path, *, comfy_online: bool = False):
        self.workspace_root = Path(workspace_root).resolve()
        self.comfy_online = bool(comfy_online)

    @abstractmethod
    def readiness(self, *, verify_hash: bool = False) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def estimate_resources(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"vram_gb": None, "disk_gb": None, "profile": request.get("resource_profile") or "unspecified"}

    def public_descriptor(self) -> dict[str, Any]:
        readiness = self.readiness()
        return {
            "id": self.id,
            "display_name": self.display_name,
            "capabilities": self.capabilities(),
            "readiness": readiness,
            "selectable": readiness.get("state") not in {"MISSING", "REMOVED", "QUARANTINED"},
            "fallback": False,
        }
