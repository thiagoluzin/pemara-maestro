#!/usr/bin/env python3
"""Create and validate evidence receipts for Pemara online security releases."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
STATUSES = {"pass", "fail", "not_applicable", "quarantined", "unknown"}
CONTROL_KEYS = (
    "rls_tenant_isolation",
    "server_side_business_rules",
    "object_authorization_idor",
    "secrets",
    "input_xss_upload",
    "auth_session_csrf",
    "mass_assignment_race",
    "agent_llm_boundaries",
)
VALIDATION_KEYS = (
    "focused_tests",
    "secret_scan",
    "static_analysis",
    "web_baseline",
    "deployed_artifact",
)


def check_item(name: str, item: Any, errors: list[str], unknown: list[str], quarantined: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{name}: objeto ausente ou invalido")
        return
    status = item.get("status")
    evidence = item.get("evidence")
    if status not in STATUSES:
        errors.append(f"{name}: status invalido")
        return
    if not isinstance(evidence, list) or not any(isinstance(x, str) and x.strip() for x in evidence):
        errors.append(f"{name}: evidencia concreta obrigatoria")
    if status == "fail":
        errors.append(f"{name}: falha aberta")
    elif status == "unknown":
        unknown.append(name)
    elif status == "quarantined":
        quarantined.append(name)


def template(target: str, release_boundary: str) -> dict[str, Any]:
    empty = lambda: {"status": "unknown", "evidence": []}
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "release_boundary": release_boundary,
        "scope_owned_or_authorized": False,
        "inventory_evidence": [],
        "controls": {key: empty() for key in CONTROL_KEYS},
        "validation": {key: empty() for key in VALIDATION_KEYS},
        "data_integrity": empty(),
        "rollback": empty(),
        "residual_risks": [],
        "decision": "REVIEW_REQUIRED",
    }


def validate(receipt: dict[str, Any]) -> tuple[str, list[str]]:
    errors: list[str] = []
    unknown: list[str] = []
    quarantined: list[str] = []
    if receipt.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version incompatível")
    if not isinstance(receipt.get("target"), str) or not receipt["target"].strip():
        errors.append("target obrigatorio")
    if receipt.get("release_boundary") not in {"local", "pilot", "production"}:
        errors.append("release_boundary deve ser local, pilot ou production")
    if receipt.get("scope_owned_or_authorized") is not True:
        errors.append("escopo nao confirmado como proprio/autorizado")
    inventory = receipt.get("inventory_evidence")
    if not isinstance(inventory, list) or not any(isinstance(x, str) and x.strip() for x in inventory):
        errors.append("inventory_evidence obrigatoria")

    controls = receipt.get("controls") if isinstance(receipt.get("controls"), dict) else {}
    validation = receipt.get("validation") if isinstance(receipt.get("validation"), dict) else {}
    for key in CONTROL_KEYS:
        check_item(f"controls.{key}", controls.get(key), errors, unknown, quarantined)
    for key in VALIDATION_KEYS:
        check_item(f"validation.{key}", validation.get(key), errors, unknown, quarantined)
    check_item("data_integrity", receipt.get("data_integrity"), errors, unknown, quarantined)
    check_item("rollback", receipt.get("rollback"), errors, unknown, quarantined)

    if errors:
        decision = "BLOCKED"
    elif unknown:
        decision = "REVIEW_REQUIRED"
    elif quarantined:
        decision = "QUARANTINE"
    else:
        decision = "PASS"

    diagnostics = errors + [f"{name}: revisao pendente" for name in unknown]
    diagnostics += [f"{name}: quarentena declarada" for name in quarantined]
    return decision, diagnostics


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("o recibo deve ser um objeto JSON")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--target", required=True)
    init.add_argument("--release-boundary", choices=("local", "pilot", "production"), default="local")
    init.add_argument("--out", required=True)
    verify = sub.add_parser("validate")
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--write-decision", action="store_true")
    args = parser.parse_args()

    try:
        if args.command == "init":
            out = Path(args.out).resolve()
            write_json(out, template(args.target, args.release_boundary))
            print(json.dumps({"receipt": str(out), "decision": "REVIEW_REQUIRED"}, ensure_ascii=False))
            return 0

        path = Path(args.receipt).resolve()
        receipt = load_json(path)
        decision, diagnostics = validate(receipt)
        if args.write_decision:
            receipt["decision"] = decision
            receipt["validated_at"] = datetime.now(timezone.utc).isoformat()
            write_json(path, receipt)
        print(json.dumps({"receipt": str(path), "decision": decision, "diagnostics": diagnostics}, ensure_ascii=False))
        return 0 if decision == "PASS" else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "BLOCKED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
