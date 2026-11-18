"""Bounded-memory checks for media; preserve the exact bytes and SHA-256."""
import hashlib
import os
from pathlib import Path

CHUNK_BYTES = 1024 * 1024


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_matches_bytes(path: Path, data: bytes) -> bool:
    with path.open("rb") as handle:
        if os.fstat(handle.fileno()).st_size != len(data):
            return False
        offset = 0
        while offset < len(data):
            chunk = handle.read(min(CHUNK_BYTES, len(data) - offset))
            # Native prefix comparison avoids both a full-file copy and a
            # Python memoryview element comparison or temporary bytes slice.
            if not chunk or not data.startswith(chunk, offset):
                return False
            offset += len(chunk)
        return not handle.read(1)
