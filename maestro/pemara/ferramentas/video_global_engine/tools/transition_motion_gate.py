#!/usr/bin/env python3
"""Block video takes that do not prove the universal continuous-action contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PILLARS = (
    "evident_camera",
    "real_depth",
    "internal_action",
    "clear_progression",
)

CONTINUITY_QC_FLAGS = (
    "continuous_action",
    "motion_across_all_intervals",
    "moving_anchor_context",
    "no_crossfade",
    "no_freeze",
    "no_static_tail",
    "no_reset",
)

ALLOWED_EDITORIAL_METHODS = {
    "generated_action_connector",
    "single_continuous_take",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 8


def _transition_items(manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    continuous_policy = manifest.get("continuous_action_contract", {})
    all_takes_required = (
        isinstance(continuous_policy, dict)
        and continuous_policy.get("required") is True
    )
    root_hint = " ".join(
        str(manifest.get(key, "")).lower()
        for key in ("project_id", "sequence_id", "role", "type")
    )
    root_is_transition = "transition" in root_hint or "transicao" in root_hint

    found: list[tuple[str, dict[str, Any]]] = []
    for collection_name in ("takes", "microtakes", "shots"):
        collection = manifest.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for index, item in enumerate(collection):
            if not isinstance(item, dict):
                continue
            transition = item.get("transition", {})
            explicit = item.get("is_transition") is True or (
                isinstance(transition, dict) and transition.get("is_transition") is True
            )
            item_hint = " ".join(
                str(item.get(key, "")).lower()
                for key in ("id", "slug", "role", "type")
            )
            if all_takes_required or root_is_transition or explicit or "transition" in item_hint or "transicao" in item_hint:
                label = str(item.get("id") or item.get("slug") or f"{collection_name}[{index}]")
                found.append((label, item))
    return found


def _contract(item: dict[str, Any]) -> dict[str, Any]:
    direct = item.get("transition_motion_contract")
    if isinstance(direct, dict):
        return direct
    shot_contract = item.get("shot_contract", {})
    if isinstance(shot_contract, dict):
        nested = shot_contract.get("transition_motion_contract")
        if isinstance(nested, dict):
            return nested
    return {}


def _require_text(errors: list[str], label: str, payload: dict[str, Any], field: str) -> None:
    if not _text(payload.get(field)):
        errors.append(f"{label}: missing descriptive field '{field}'")


def _validate_contract(label: str, item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = _contract(item)
    if not contract:
        return [f"{label}: missing transition_motion_contract"]

    camera = contract.get("camera_evidence", {})
    if not isinstance(camera, dict):
        camera = {}
    _require_text(errors, f"{label}.evident_camera", camera, "movement")
    _require_text(errors, f"{label}.evident_camera", camera, "perspective_change")
    if camera.get("physical_translation") is not True:
        errors.append(f"{label}.evident_camera: physical_translation must be true")

    depth = contract.get("real_depth", {})
    if not isinstance(depth, dict):
        depth = {}
    for field in (
        "foreground",
        "midground",
        "background",
        "differential_motion",
        "occlusion_or_scale_change",
    ):
        _require_text(errors, f"{label}.real_depth", depth, field)

    action = contract.get("internal_action", {})
    if not isinstance(action, dict):
        action = {}
    _require_text(errors, f"{label}.internal_action", action, "primary_event")
    elements = action.get("independent_elements", [])
    if not isinstance(elements, list) or len([value for value in elements if _text(value)]) < 2:
        errors.append(
            f"{label}.internal_action: at least two descriptive independent_elements are required"
        )
    if action.get("camera_independent") is not True:
        errors.append(f"{label}.internal_action: camera_independent must be true")

    progression = contract.get("progression", {})
    if not isinstance(progression, dict):
        progression = {}
    for field in ("start", "middle", "end", "end_state_change", "exit_or_cut"):
        _require_text(errors, f"{label}.clear_progression", progression, field)
    states = [str(progression.get(field, "")).strip().casefold() for field in ("start", "middle", "end")]
    if all(states) and len(set(states)) != 3:
        errors.append(f"{label}.clear_progression: start, middle and end must be different")

    continuity = contract.get("continuity", {})
    if not isinstance(continuity, dict):
        continuity = {}
    method = str(continuity.get("editorial_method") or "").strip().casefold()
    if method not in ALLOWED_EDITORIAL_METHODS:
        errors.append(
            f"{label}.continuity: editorial_method must be generated_action_connector "
            "or single_continuous_take"
        )
    if continuity.get("continuous_action") is not True:
        errors.append(f"{label}.continuity: continuous_action must be true")
    if continuity.get("motion_handoff") is not True:
        errors.append(f"{label}.continuity: motion_handoff must be true")
    if continuity.get("action_occupies_full_duration") is not True:
        errors.append(f"{label}.continuity: action_occupies_full_duration must be true")
    _require_text(errors, f"{label}.continuity", continuity, "entry_motion")
    _require_text(errors, f"{label}.continuity", continuity, "exit_motion")
    interval_motion = continuity.get("interval_motion", {})
    if not isinstance(interval_motion, dict):
        interval_motion = {}
    for field in ("early_0_30", "middle_30_70", "late_70_100"):
        _require_text(errors, f"{label}.continuity.interval_motion", interval_motion, field)
    for field in ("crossfade_frames", "freeze_frames", "static_hold_frames"):
        value = continuity.get(field)
        if isinstance(value, bool) or value != 0:
            errors.append(f"{label}.continuity: {field} must be exactly 0")

    transition = item.get("transition", {})
    explicit_transition = item.get("is_transition") is True or (
        isinstance(transition, dict) and transition.get("is_transition") is True
    )
    if explicit_transition:
        anchor_context = continuity.get("moving_anchor_context", {})
        if not isinstance(anchor_context, dict):
            anchor_context = {}
        for side in ("start", "end"):
            if anchor_context.get(f"{side}_has_motion_before_and_after") is not True:
                errors.append(
                    f"{label}.continuity.moving_anchor_context: "
                    f"{side}_has_motion_before_and_after must be true"
                )
            _require_text(
                errors,
                f"{label}.continuity.moving_anchor_context",
                anchor_context,
                f"{side}_source",
            )

    return errors


def _validate_approval(label: str, item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    qc = item.get("qc", {})
    if not isinstance(qc, dict):
        return [f"{label}: missing visual qc"]
    gate = qc.get("transition_motion_gate", {})
    if not isinstance(gate, dict):
        return [f"{label}: missing qc.transition_motion_gate"]
    if str(gate.get("status", "")).casefold() != "approved":
        errors.append(f"{label}: qc.transition_motion_gate.status must be approved")
    for pillar in PILLARS:
        if gate.get(pillar) is not True:
            errors.append(f"{label}: visual QC pillar '{pillar}' must be true")
    for flag in CONTINUITY_QC_FLAGS:
        if gate.get(flag) is not True:
            errors.append(f"{label}: visual QC continuity flag '{flag}' must be true")
    if not _text(gate.get("evidence")):
        errors.append(f"{label}: visual QC evidence is required")
    return errors


def validate_manifest(
    manifest: dict[str, Any], stage: str, selected_ids: set[str] | None = None
) -> tuple[list[str], int]:
    errors: list[str] = []
    policy = manifest.get("universal_transition_motion_gate", {})
    if not isinstance(policy, dict) or policy.get("required") is not True:
        errors.append("manifest: universal_transition_motion_gate.required must be true")
    continuous = manifest.get("continuous_action_contract", {})
    if not isinstance(continuous, dict):
        continuous = {}
    required_policy_flags = (
        "required",
        "generated_connector_required_between_takes",
        "crossfade_forbidden",
        "freeze_frame_forbidden",
        "static_tail_forbidden",
        "motion_handoff_required",
        "full_duration_motion_required",
        "three_interval_motion_required",
        "moving_transition_anchors_required",
    )
    for flag in required_policy_flags:
        if continuous.get(flag) is not True:
            errors.append(f"manifest: continuous_action_contract.{flag} must be true")

    items = _transition_items(manifest)
    if selected_ids:
        items = [(label, item) for label, item in items if label in selected_ids]
        missing = sorted(selected_ids - {label for label, _ in items})
        for label in missing:
            errors.append(f"manifest: requested transition take not found: {label}")
    if not items:
        errors.append("manifest: no video takes found")
        return errors, 0

    for label, item in items:
        errors.extend(_validate_contract(label, item))
        if stage == "approval":
            errors.extend(_validate_approval(label, item))
    return errors, len(items)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate continuous action and the four universal motion pillars for every video take."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--stage", choices=("contract", "approval"), default="contract")
    parser.add_argument("--takes", nargs="*", default=None, help="Optional transition take IDs")
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"TRANSITION MOTION GATE: ERROR - {exc}", file=sys.stderr)
        return 2

    selected = set(args.takes) if args.takes else None
    errors, count = validate_manifest(manifest, args.stage, selected)
    if errors:
        print(f"TRANSITION MOTION GATE: REJECTED ({len(errors)} issue(s))", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print(
        f"TRANSITION MOTION GATE: PASS - {count} video take(s), stage={args.stage}, "
        "4/4 pillars"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
