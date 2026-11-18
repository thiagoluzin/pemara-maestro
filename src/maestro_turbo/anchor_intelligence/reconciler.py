"""Fail-closed reconciliation between pixels and requested motion."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .schema import validate_anchor_contract


class AnchorConflictError(ValueError):
    def __init__(self, message: str, blockers: list[dict[str, Any]]):
        self.code = "ANCHOR_DECISION_REQUIRED"
        self.blockers = blockers
        super().__init__(message)


def _text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _render_constraint(value: Any) -> str:
    if isinstance(value, dict):
        target = value.get("target") or value.get("field") or value.get("id") or "element"
        rule = value.get("rule") or value.get("value") or value.get("description") or value.get("change") or "preserve exactly"
        return f"{target}: {rule}"
    return " ".join(str(value or "").split())


def reconcile_anchor_contract(contract: dict[str, Any], *, raise_on_blocker: bool = False) -> dict[str, Any]:
    value = validate_anchor_contract(contract)
    intent = value.get("intent") or {}
    invariants = value.get("invariants") or []
    allowed = value.get("allowed_transformations") or []
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    invariant_text = " | ".join(_text(item) for item in invariants)
    allowed_text = " | ".join(_text(item) for item in allowed)
    for change in intent.get("explicit_changes") or []:
        rendered = _render_constraint(change)
        target = _text(change.get("target") if isinstance(change, dict) else change)
        if target and target in invariant_text and target not in allowed_text:
            blockers.append({
                "code": "CHANGE_VIOLATES_INVARIANT",
                "field": target,
                "detail": rendered,
                "decision_required": True,
            })

    for divergence in value.get("divergences") or []:
        if not isinstance(divergence, dict):
            warnings.append({"code": "VISION_DIVERGENCE", "detail": _render_constraint(divergence)})
            continue
        item = deepcopy(divergence)
        severity = _text(item.get("severity"))
        if item.get("decision_required") is True or severity in {"high", "critical", "blocking"}:
            item.setdefault("code", "IMAGE_INTENT_DIVERGENCE")
            blockers.append(item)
        else:
            item.setdefault("code", "VISION_DIVERGENCE")
            warnings.append(item)

    uncertainties = (value.get("evidence") or {}).get("uncertainties") or []
    for preserve in intent.get("preserve") or []:
        preserve_text = _text(preserve)
        if preserve_text and any(preserve_text in _text(item) or _text(item) in preserve_text for item in uncertainties):
            blockers.append({
                "code": "PRESERVATION_TARGET_UNCERTAIN",
                "field": _render_constraint(preserve),
                "detail": "A imagem nao sustenta esse detalhe com seguranca.",
                "decision_required": True,
            })

    do_not_invent = [
        "Do not add subjects, limbs, props, text, logos, architecture, weather, or story events absent from the anchor unless explicitly allowed.",
        "Do not duplicate, replace, restyle, recolor, or swap the identity and wardrobe of visible subjects.",
        "Do not change screen geography, subject count, camera axis, or visible text without an explicit allowed transformation.",
    ]
    do_not_invent.extend(filter(None, (_render_constraint(item) for item in value.get("negative_constraints") or [])))
    do_not_invent.extend(f"Preserve invariant — {_render_constraint(item)}" for item in invariants if _render_constraint(item))
    result = {
        "contract_id": value["contract_id"],
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "evidence": value["evidence"],
        "intent": intent,
        "invariants": invariants,
        "allowed_transformations": allowed,
        "temporal_plan": value.get("temporal_plan") or [],
        "camera_plan": value.get("camera_plan") or {},
        "do_not_invent": list(dict.fromkeys(do_not_invent)),
        "owner_approval_state": "PENDING_HUMAN_REVIEW",
    }
    if blockers and raise_on_blocker:
        raise AnchorConflictError("A imagem e a intencao exigem uma decisao do proprietario.", blockers)
    return result
