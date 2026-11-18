#!/usr/bin/env python3
"""Validate the public Messenger Turbo registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from maestro_turbo.turbo_registry import TurboRegistryError, validate_turbo_registry  # noqa: E402


def main() -> int:
    path = ROOT / "skills" / "pemara-messenger-turbo" / "references" / "turbo_registry.json"
    try:
        result = validate_turbo_registry(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TurboRegistryError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "dispatcher": result["dispatcher_profile"],
                "aliases": len(result["aliases"]),
                "specialized_profiles": len(result["specialized_profiles"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
