"""Build benchmark artifacts using existing builders; never contacts ComfyUI."""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO))


def h3_baseline() -> dict:
    from h3_workflow import (
        H3_FL2VA_MODEL_NAME, H3_REF2VA_MODEL_NAME,
        resolve_h3_quality_profile, validate_h3_comfy_graph,
    )
    from video_workflows import validate_video_fps

    source = ast.parse((STUDIO / "main.py").read_text(encoding="utf-8-sig"))
    namespace = {
        "Dict": Dict, "Any": Any, "validate_video_fps": validate_video_fps,
        "_H3_FL2VA_MODEL_NAME": H3_FL2VA_MODEL_NAME,
        "_H3_REF2VA_MODEL_NAME": H3_REF2VA_MODEL_NAME,
        "_resolve_h3_quality_profile": resolve_h3_quality_profile,
        "_validate_h3_comfy_graph": validate_h3_comfy_graph,
    }
    # Execute only literal H3 constants and the pure existing builder, not main startup.
    for node in source.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id.startswith("MINIMAX_H3_"):
                if isinstance(node.value, (ast.Constant, ast.Name)):
                    exec(compile(ast.Module(body=[node], type_ignores=[]), "main.constants", "exec"), namespace)
        if isinstance(node, ast.FunctionDef) and node.name == "_build_minimax_h3_fl2va_workflow":
            exec(compile(ast.Module(body=[node], type_ignores=[]), "main.builder", "exec"), namespace)
    return namespace["_build_minimax_h3_fl2va_workflow"](
        prompt="integrated_multimodal_description: [Shot 1] A locked wide camera observes a sunlit empty courtyard. Leaves on one small tree sway gently in a steady breeze. Natural stone surfaces, consistent daylight, one continuous shot.\n\noverall_soundscape: N/A\n\nnon_diegetic_music: N/A",
        negative="", width=1088, height=608, frames=124, steps=10, seed=20260907,
        prefix="creative_os_audit_20260907/h3_reference", base_image_name="",
        include_native_audio=False, h3_quality_profile="h3_production",
    )


def save_graph(name: str, graph: dict) -> Path:
    directory = ROOT / "dados" / "creative_os" / "benchmarks" / "20260907"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{name}.json"
    raw = json.dumps(graph, ensure_ascii=False, indent=2).encode()
    # Preserve any earlier benchmark configuration.
    if target.exists() and target.read_bytes() != raw:
        raise RuntimeError(f"Refusing to overwrite {target}")
    target.write_bytes(raw)
    print(json.dumps({"path": str(target), "sha256": hashlib.sha256(raw).hexdigest()}))
    return target


if __name__ == "__main__":
    if len(sys.argv) == 1:
        save_graph("h3_reference", h3_baseline())
    else:
        from ltx25_workflow import build_ltx25_i2v_workflow
        save_graph("ltx_reference", build_ltx25_i2v_workflow(
            prompt="A locked wide camera observes a sunlit empty courtyard. Leaves on one small tree sway gently in a steady breeze. Natural stone surfaces, consistent daylight, one continuous shot.",
            negative="", base_image_name=sys.argv[1], frames=121, seed=20260907,
            filename_prefix="creative_os_audit_20260907/ltx_reference", include_native_audio=False,
        ))
