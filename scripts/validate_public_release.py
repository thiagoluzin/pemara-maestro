#!/usr/bin/env python3
"""Fail closed on personal, secret, runtime or generated artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt"}
TEXT_NAMES = {"LICENSE", ".gitignore", ".gitattributes"}
FORBIDDEN_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".log", ".pyc", ".pem", ".pfx", ".key",
    ".safetensors", ".ckpt", ".pt", ".pth", ".gguf", ".onnx",
    ".mp4", ".mov", ".mkv", ".webm", ".wav", ".flac",
}
FORBIDDEN_PARTS = {
    "__pycache__", "models", "model-cache", "runtime", "runtimes", "outputs", "output",
    "logs", "receipts", "sessions", "attachments", "projects", "backups", ".env",
}
IGNORED_WORKTREE_PARTS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv", "dist", "build"
}
CONTENT_RULES = {
    "machine path": re.compile(
        r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|" + "/" + "home/)",
        re.IGNORECASE,
    ),
    "email address": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+[.][A-Z]{2,}", re.IGNORECASE),
    "secret assignment": re.compile(r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"][^'\"]{8,}", re.IGNORECASE),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def validate(root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if any(part.casefold() in IGNORED_WORKTREE_PARTS or part.casefold().endswith(".egg-info") for part in relative.parts):
            continue
        if path.is_dir():
            continue
        if any(part.casefold() in FORBIDDEN_PARTS for part in relative.parts):
            findings.append({"path": relative.as_posix(), "rule": "forbidden path"})
            continue
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            findings.append({"path": relative.as_posix(), "rule": "forbidden file type"})
            continue
        if path.stat().st_size > 2 * 1024 * 1024:
            findings.append({"path": relative.as_posix(), "rule": "file exceeds 2 MiB"})
            continue
        if path.suffix.casefold() not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            findings.append({"path": relative.as_posix(), "rule": "unexpected file type"})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append({"path": relative.as_posix(), "rule": "non-UTF-8 file"})
            continue
        for name, pattern in CONTENT_RULES.items():
            if pattern.search(text):
                findings.append({"path": relative.as_posix(), "rule": name})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    findings = validate(root)
    print(json.dumps({"ok": not findings, "root": str(root), "findings": findings}, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
