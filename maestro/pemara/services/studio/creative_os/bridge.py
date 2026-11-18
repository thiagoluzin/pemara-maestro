"""Injected bridge: Maestro keeps its transport; a coordinator must inject MCP tools."""
from dataclasses import dataclass
from typing import Callable
import copy


@dataclass
class Bridge:
    submit: Callable
    status: Callable
    capabilities: Callable
    output_path: Callable
    cancel: Callable
    transport: str = "maestro_internal_direct"
    prepare: Callable | None = None
    provenance: Callable | None = None


def normalize_save_video(graph, dynamic_format: bool):
    """Adapt exporter schema without changing sampling or mutating pinned templates."""
    result = copy.deepcopy(graph)
    if dynamic_format:
        for node in result.values():
            if node.get("class_type") == "SaveVideo":
                inputs = node["inputs"]
                if "codec" in inputs and "format.codec" not in inputs:
                    inputs["format.codec"] = inputs.pop("codec")
    return result
