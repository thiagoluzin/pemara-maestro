"""MiniMax H3 prompt dialect compiled from a reconciled anchor contract."""

from __future__ import annotations

import json
from typing import Any

from .reconciler import reconcile_anchor_contract


COMPILER_VERSION = "pemara-anchor-h3@1"


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def compile_h3_prompt(contract: dict[str, Any], *, duration_seconds: float = 6.0) -> dict[str, Any]:
    reconciled = reconcile_anchor_contract(contract, raise_on_blocker=True)
    duration = max(4.0, min(15.0, float(duration_seconds)))
    temporal = reconciled["temporal_plan"] or [
        {"phase": "0-30%", "rule": "begin from the exact anchor state; only the requested action starts"},
        {"phase": "30-70%", "rule": "continue the same physical action with coherent internal motion"},
        {"phase": "70-100%", "rule": "resolve the requested action without a freeze, reset, or invented event"},
    ]
    prompt = "\n".join(
        [
            "integrated_multimodal_description:",
            f"VISIBLE ANCHOR EVIDENCE: {_compact(reconciled['evidence'])}",
            f"OWNER-REQUESTED ACTION: {_compact(reconciled['intent'])}",
            f"IMMUTABLE CONTINUITY: {_compact(reconciled['invariants'])}",
            f"ONLY ALLOWED TRANSFORMATIONS: {_compact(reconciled['allowed_transformations'])}",
            f"PHYSICAL TIMELINE: {_compact(temporal)}",
            f"CAMERA CONTRACT: {_compact(reconciled['camera_plan'])}",
            "Motion remains continuous inside the same geography. Start from the supplied pixels exactly; no establishing rewrite.",
            "overall_soundscape:",
            str(reconciled["intent"].get("sound") or "Only sound causally produced by the visible action and environment; no invented dialogue."),
            "non_diegetic_music:",
            "N/A unless explicitly requested by the owner.",
        ]
    )
    return {
        "engine_id": "minimax_h3",
        "compiler_version": COMPILER_VERSION,
        "anchor_contract_id": reconciled["contract_id"],
        "prompt": prompt,
        "negative_prompt": ", ".join(reconciled["do_not_invent"]),
        "parameters": {"duration_seconds": duration, "native_fps": 24, "steps": 20, "guidance": 1.0},
        "reconciliation": reconciled,
    }
