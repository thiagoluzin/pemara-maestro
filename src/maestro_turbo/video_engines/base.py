"""Shared contract for public Maestro video-engine adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any


class EngineError(ValueError):
    def __init__(self, code: str, message: str, *, details: Any = None):
        self.code = code
        self.details = details
        super().__init__(message)


class EngineSelectionRequired(EngineError):
    def __init__(self):
        super().__init__("ENGINE_SELECTION_REQUIRED", "Escolha MiniMax H3 ou LTX 2.5 antes de gerar.")


class BaseVideoEngine(ABC):
    id: str
    display_name: str

    def __init__(self, runtime_attestation: dict[str, Any] | None = None):
        self.runtime_attestation = deepcopy(runtime_attestation or {})

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def readiness(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def compile_prompt(self, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_workflow_descriptor(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def public_descriptor(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "capabilities": self.capabilities(),
            "readiness": self.readiness(),
            "fallback": False,
        }
