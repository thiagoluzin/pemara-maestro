#!/usr/bin/env python3
"""Validate the Messenger Turbo registry without third-party dependencies."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SKILL_DIR / "references" / "turbo_registry.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    skill_root = Path(data["canonical_skill_root"])
    profile_root = Path(data["profile_root"])
    errors: list[str] = []

    aliases = data["aliases"]
    specialized = data["specialized_profiles"]
    if len(aliases) != len(set(aliases)):
        errors.append("aliases contains duplicates")
    if len(specialized) != len(set(specialized)):
        errors.append("specialized_profiles contains duplicates")
    overlap = sorted(set(aliases) & set(specialized))
    if overlap:
        errors.append(f"alias/specialized overlap: {', '.join(overlap)}")

    for name in aliases:
        skill = skill_root / name / "SKILL.md"
        profile = profile_root / f"{name}.md"
        if not skill.is_file():
            errors.append(f"missing canonical skill: {skill}")
            continue
        if not profile.is_file():
            errors.append(f"missing alias profile: {profile}")
            continue
        content = profile.read_text(encoding="utf-8")
        canonical_marker = f"E:/Pemara/.agents/skills/{name}/SKILL.md"
        if "AGENTS_TURBO_ALIAS_V1" not in content:
            errors.append(f"missing alias marker: {profile}")
        if canonical_marker not in content:
            errors.append(f"wrong canonical pointer: {profile}")
        if sha256(skill) == sha256(profile):
            errors.append(f"duplicated skill content returned: {profile}")

    for name in specialized:
        profile = profile_root / f"{name}.md"
        skill = skill_root / name / "SKILL.md"
        if not profile.is_file():
            errors.append(f"missing specialized profile: {profile}")
        if not skill.is_file():
            errors.append(f"missing homonymous skill for specialization: {skill}")
        if profile.is_file() and skill.is_file() and sha256(profile) == sha256(skill):
            errors.append(f"specialized profile became an exact duplicate: {profile}")

    dispatcher = profile_root / f"{data['dispatcher_profile']}.md"
    if not dispatcher.is_file():
        errors.append(f"missing dispatcher profile: {dispatcher}")

    report = {
        "schema_version": data["schema_version"],
        "aliases": len(aliases),
        "specialized_profiles": len(specialized),
        "dispatcher": str(dispatcher),
        "errors": errors,
        "ok": not errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
