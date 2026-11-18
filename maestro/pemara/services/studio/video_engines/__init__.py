"""Explicit video-engine adapters. No default and no cross-engine fallback."""

from .base import EngineError, EngineSelectionRequired
from .registry import VideoEngineRegistry, build_video_engine_registry

__all__ = ["EngineError", "EngineSelectionRequired", "VideoEngineRegistry", "build_video_engine_registry"]
