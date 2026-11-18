"""Versioned, JSON-safe contract for image anchors.

The schema deliberately separates observed pixels from owner intent.  Empty or
uncertain fields stay empty; they are never completed with a model guess.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


ANCHOR_CONTRACT_VERSION = "pemara-anchor-intelligence@1"


class AnchorContractError(ValueError):
    """Raised when an anchor contract is incomplete or has been tampered with."""

    def __init__(self, code: str, message: str, details: Any = None):
        self.code = code
        self.details = details
        super().__init__(message)


def _clean_text(value: Any, *, limit: int = 12_000) -> str:
    text = " ".join(str(value or "").replace("\x00", " ").split())
    return text[:limit]


def _clean_list(value: Any, *, limit: int = 100) -> list[Any]:
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    cleaned: list[Any] = []
    for item in items[:limit]:
        if isinstance(item, dict):
            cleaned.append(_clean_mapping(item))
        else:
            text = _clean_text(item, limit=2_000)
            if text:
                cleaned.append(text)
    return cleaned


def _clean_mapping(value: Any, *, depth: int = 0) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    if depth > 5:
        return {}
    result: dict[str, Any] = {}
    for raw_key, raw_value in list(value.items())[:200]:
        key = _clean_text(raw_key, limit=120)
        if not key:
            continue
        if isinstance(raw_value, dict):
            result[key] = _clean_mapping(raw_value, depth=depth + 1)
        elif isinstance(raw_value, (list, tuple)):
            result[key] = _clean_list(raw_value)
        elif isinstance(raw_value, bool) or raw_value is None:
            result[key] = raw_value
        elif isinstance(raw_value, (int, float)):
            result[key] = raw_value
        else:
            result[key] = _clean_text(raw_value)
    return result


def _normalize_intent(intent: Any) -> dict[str, Any]:
    if isinstance(intent, str):
        return {
            "action": _clean_text(intent),
            "preserve": [],
            "explicit_changes": [],
            "new_elements_allowed": [],
            "sound": "",
        }
    value = _clean_mapping(intent)
    return {
        "action": _clean_text(value.get("action") or value.get("description")),
        "preserve": _clean_list(value.get("preserve")),
        "explicit_changes": _clean_list(value.get("explicit_changes")),
        "new_elements_allowed": _clean_list(value.get("new_elements_allowed")),
        "sound": _clean_text(value.get("sound")),
        **{
            key: item
            for key, item in value.items()
            if key not in {"action", "description", "preserve", "explicit_changes", "new_elements_allowed", "sound"}
        },
    }


def _canonical_body(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in contract.items()
        if key not in {"contract_id", "created_at", "updated_at"}
    }


def contract_id_for(contract: dict[str, Any]) -> str:
    encoded = json.dumps(
        _canonical_body(contract),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "anchor_" + hashlib.sha256(encoded).hexdigest()[:24]


def build_anchor_contract(
    *,
    evidence: dict[str, Any],
    intent: dict[str, Any] | str,
    invariants: Any = None,
    allowed_transformations: Any = None,
    negative_constraints: Any = None,
    temporal_plan: Any = None,
    camera_plan: Any = None,
    divergences: Any = None,
    source: Any = None,
) -> dict[str, Any]:
    if not isinstance(evidence, dict) or not evidence:
        raise AnchorContractError(
            "ANCHOR_EVIDENCE_REQUIRED",
            "A leitura visual estruturada da ancora e obrigatoria.",
        )
    normalized_evidence = _clean_mapping(evidence)
    if not any(normalized_evidence.get(key) for key in ("subjects", "environment", "composition", "objects", "visible_text")):
        raise AnchorContractError(
            "ANCHOR_EVIDENCE_EMPTY",
            "A leitura visual nao contem sujeitos, ambiente, composicao, objetos ou texto visivel.",
        )
    normalized_intent = _normalize_intent(intent)
    if not normalized_intent.get("action"):
        raise AnchorContractError(
            "ANCHOR_INTENT_REQUIRED",
            "Descreva explicitamente o que deve acontecer no video.",
        )

    contract: dict[str, Any] = {
        "schema_version": ANCHOR_CONTRACT_VERSION,
        "source": _clean_mapping(source),
        "evidence": normalized_evidence,
        "intent": normalized_intent,
        "invariants": _clean_list(invariants),
        "allowed_transformations": _clean_list(allowed_transformations),
        "negative_constraints": _clean_list(negative_constraints),
        "temporal_plan": _clean_list(temporal_plan),
        "camera_plan": _clean_mapping(camera_plan),
        "divergences": _clean_list(divergences),
        "owner_approval_state": "PENDING_HUMAN_REVIEW",
    }
    contract["contract_id"] = contract_id_for(contract)
    return contract


def validate_anchor_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise AnchorContractError("ANCHOR_CONTRACT_INVALID", "O contrato da ancora deve ser um objeto JSON.")
    if contract.get("schema_version") != ANCHOR_CONTRACT_VERSION:
        raise AnchorContractError(
            "ANCHOR_SCHEMA_UNSUPPORTED",
            f"Versao de contrato nao suportada: {contract.get('schema_version') or 'ausente'}.",
        )
    expected = contract_id_for(contract)
    supplied = str(contract.get("contract_id") or "")
    if supplied != expected:
        raise AnchorContractError(
            "ANCHOR_CONTRACT_ID_MISMATCH",
            "O conteudo da ancora nao corresponde ao identificador imutavel.",
            {"expected": expected, "supplied": supplied},
        )
    if not isinstance(contract.get("evidence"), dict) or not contract["evidence"]:
        raise AnchorContractError("ANCHOR_EVIDENCE_REQUIRED", "O contrato nao possui evidencia visual.")
    if not isinstance(contract.get("intent"), dict) or not _clean_text(contract["intent"].get("action")):
        raise AnchorContractError("ANCHOR_INTENT_REQUIRED", "O contrato nao possui intencao declarada.")
    return deepcopy(contract)
