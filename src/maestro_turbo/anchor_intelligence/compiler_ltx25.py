"""LTX 2.5 chronological prompt dialect compiled from an anchor contract."""

from __future__ import annotations

import json
from typing import Any

from .reconciler import reconcile_anchor_contract


COMPILER_VERSION = "pemara-anchor-ltx25@1"


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def ltx25_frame_count(duration_seconds: float, fps: float = 24.0) -> int:
    duration = max(1.0, min(30.0, float(duration_seconds)))
    rate = max(1.0, min(60.0, float(fps)))
    target = max(9, int(round(duration * rate)) + 1)
    lower = max(9, ((target - 1) // 8) * 8 + 1)
    upper = lower + 8
    return min((lower, upper), key=lambda item: (abs(item - target), 0 if item >= target else 1, item))


def compile_ltx25_prompt(
    contract: dict[str, Any],
    *,
    duration_seconds: float = 6.0,
    fps: float = 24.0,
    width: int = 960,
    height: int = 544,
) -> dict[str, Any]:
    reconciled = reconcile_anchor_contract(contract, raise_on_blocker=True)
    if int(width) % 32 or int(height) % 32:
        raise ValueError("LTX25_DIMENSIONS_INVALID: largura e altura devem ser multiplos de 32.")
    frames = ltx25_frame_count(duration_seconds, fps)
    phases = reconciled["temporal_plan"] or [
        {"phase": "opening", "rule": "the first frame is the supplied anchor with no redesign"},
        {"phase": "development", "rule": "the requested physical action progresses continuously"},
        {"phase": "resolution", "rule": "the action resolves while identity, geometry, lighting, and geography remain locked"},
    ]
    prompt = "\n".join(
        [
            "Opening frame: reproduce the supplied anchor exactly as the initial visual state.",
            f"Visible facts: {_compact(reconciled['evidence'])}.",
            f"Requested action only: {_compact(reconciled['intent'])}.",
            f"Chronological motion: {_compact(phases)}.",
            f"Camera: {_compact(reconciled['camera_plan'])}.",
            f"Continuity invariants: {_compact(reconciled['invariants'])}.",
            f"Permitted changes and nothing else: {_compact(reconciled['allowed_transformations'])}.",
            "Maintain a single coherent shot unless the owner explicitly asked for a cut. Motion must have physical cause, intermediate states, and a stable final state.",
        ]
    )
    return {
        "engine_id": "ltx_2_5",
        "compiler_version": COMPILER_VERSION,
        "anchor_contract_id": reconciled["contract_id"],
        "prompt": prompt,
        "negative_prompt": ", ".join(reconciled["do_not_invent"]),
        "parameters": {
            "duration_seconds": float(duration_seconds),
            "fps": float(fps),
            "num_frames": frames,
            "width": int(width),
            "height": int(height),
            "frame_rule": "8n+1",
        },
        "reconciliation": reconciled,
    }
