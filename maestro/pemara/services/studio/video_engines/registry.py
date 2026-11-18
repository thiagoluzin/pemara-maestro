"""Explicit owner-authorized engines; Hunyuan retired on 2026-11-15."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .base import BaseVideoEngine, EngineError, EngineSelectionRequired
from .h3 import H3VideoEngine
from retired_models import is_retired_engine


class VideoEngineRegistry:
    def __init__(self, engines: Iterable[BaseVideoEngine]):
        self._engines = {engine.id: engine for engine in engines}
        if set(self._engines) != {"minimax_h3"}:
            raise RuntimeError("VIDEO_ENGINE_REGISTRY_INVALID: motor autorizado: MiniMax H3.")

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._engines)

    def get(self, engine_id: Any) -> BaseVideoEngine:
        selected = str(engine_id or "").strip()
        if is_retired_engine(selected):
            raise EngineError("ENGINE_REMOVED_BY_OWNER", "Motor removido pelo proprietario em 15/11/2026. Escolha explicitamente um motor disponivel.", status_code=410)
        if not selected:
            raise EngineSelectionRequired()
        engine = self._engines.get(selected)
        if engine is None:
            raise EngineError(
                "ENGINE_NOT_ALLOWED",
                f"Motor desconhecido ou removido: {selected}.",
                details={"allowed": list(self.ids)},
            )
        return engine

    def describe(self) -> dict[str, Any]:
        return {
            "ok": True,
            "selection_required": True,
            "default_engine_id": None,
            "fallback_allowed": False,
            "engines": [self._engines[engine_id].public_descriptor() for engine_id in self.ids],
        }


def build_video_engine_registry(workspace_root: Path, *, comfy_online: bool = False) -> VideoEngineRegistry:
    return VideoEngineRegistry(
        (
            H3VideoEngine(workspace_root, comfy_online=comfy_online),
        )
    )
