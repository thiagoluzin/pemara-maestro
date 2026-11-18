"""Closed registry that requires an explicit H3 or LTX 2.5 selection."""

from __future__ import annotations

from typing import Any, Iterable

from .base import BaseVideoEngine, EngineError, EngineSelectionRequired
from .h3 import H3VideoEngine
from .ltx25 import Ltx25VideoEngine


class VideoEngineRegistry:
    def __init__(self, engines: Iterable[BaseVideoEngine]):
        self._engines = {engine.id: engine for engine in engines}
        if tuple(self._engines) != ("minimax_h3", "ltx_2_5"):
            raise RuntimeError("VIDEO_ENGINE_REGISTRY_INVALID")

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._engines)

    def get(self, engine_id: Any) -> BaseVideoEngine:
        selected = str(engine_id or "").strip()
        if not selected:
            raise EngineSelectionRequired()
        engine = self._engines.get(selected)
        if engine is None:
            raise EngineError("ENGINE_NOT_ALLOWED", f"Motor desconhecido ou removido: {selected}.", details={"allowed": list(self.ids)})
        return engine

    def describe(self) -> dict[str, Any]:
        return {
            "selection_required": True,
            "default_engine_id": None,
            "fallback_allowed": False,
            "engines": [self._engines[item].public_descriptor() for item in self.ids],
        }

    def compile_job(self, engine_id: Any, anchor_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        engine = self.get(engine_id)
        return {
            "engine_id": engine.id,
            "compiled_prompt": engine.compile_prompt(anchor_contract, request),
            "workflow": engine.build_workflow_descriptor(request),
        }


def build_video_engine_registry(attestations: dict[str, dict[str, Any]] | None = None) -> VideoEngineRegistry:
    values = attestations or {}
    return VideoEngineRegistry(
        (
            H3VideoEngine(values.get("minimax_h3")),
            Ltx25VideoEngine(values.get("ltx_2_5")),
        )
    )
