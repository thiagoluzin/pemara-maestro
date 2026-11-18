#!/usr/bin/env python3
"""Validate an operator-supplied LTX 2.5 smoke receipt and optional output."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(payload: Any, output: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["receipt must be a JSON object"]
    expected = {
        "status": "PASS",
        "engine_id": "ltx_2_5",
        "technical_qc_pass": True,
        "owner_approval_state": "PENDING_HUMAN_REVIEW",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{field} must be {value!r}")
    generation = payload.get("generation") or {}
    if generation.get("fallback_allowed") is not False or generation.get("fallback_used") is not False:
        errors.append("fallback must be explicitly disabled and unused")
    digest = str(payload.get("output_sha256") or "")
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        errors.append("output_sha256 is invalid")
    if output is not None:
        if not output.is_file():
            errors.append("output file is missing")
        elif _sha256(output) != digest:
            errors.append("output hash does not match receipt")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    errors = validate(payload, args.output)
    print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
