"""Generic ranged HTTP downloader with exact size and SHA-256 publication."""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path.cwd()
BASE_URLS: tuple[str, ...] = ()
MODELS: dict[str, dict[str, object]] = {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cleanup_legacy_parts(name: str) -> None:
    root = ROOT.resolve()
    for suffix in (".parts", ".parts-v2", ".parts-v3"):
        candidate = (ROOT / f".{name}{suffix}").resolve()
        if candidate.parent == root and candidate.is_dir():
            shutil.rmtree(candidate)


def download_range(url: str, part: Path, start: int, end: int) -> tuple[int, int]:
    expected = end - start + 1
    part.parent.mkdir(parents=True, exist_ok=True)
    zero_progress_attempts = 0
    attempts = 0
    while True:
        existing = part.stat().st_size if part.exists() else 0
        if existing == expected:
            return start, expected
        if existing > expected:
            raise RuntimeError(
                f"Part {part.name} has {existing} bytes; expected at most {expected}"
            )
        attempts += 1
        if attempts > 120:
            raise RuntimeError(f"Too many resume attempts for {part.name}")
        with part.open("ab") as handle:
            try:
                result = subprocess.run(
                    [
                        "curl.exe", "-L", "--fail", "--retry", "0",
                        "--connect-timeout", "30", "--speed-limit", "1024",
                        "--speed-time", "60", "--max-time", "180", "--silent",
                        "--show-error", "--range", f"{start + existing}-{end}", url,
                    ],
                    stdout=handle,
                    check=False,
                    timeout=240,
                )
            except subprocess.TimeoutExpired:
                result = None
        actual = part.stat().st_size if part.exists() else 0
        if actual > expected:
            raise RuntimeError(f"Part {part.name} exceeded its expected range")
        if actual > existing:
            zero_progress_attempts = 0
            continue
        zero_progress_attempts += 1
        if zero_progress_attempts >= 8:
            return_code = "timeout" if result is None else str(result.returncode)
            raise RuntimeError(
                f"No progress for {part.name} after {zero_progress_attempts} attempts "
                f"(curl={return_code})"
            )


def download_model(name: str, workers: int, parts: int) -> Path:
    metadata = MODELS[name]
    size = int(metadata["size"])
    expected_hash = str(metadata["sha256"])
    destination = ROOT / name
    if destination.is_file() and destination.stat().st_size == size:
        if sha256(destination) == expected_hash:
            cleanup_legacy_parts(name)
            return destination
    if not BASE_URLS:
        raise RuntimeError("No ranged download source configured")
    part_dir = ROOT / f".{name}.parts-v3"
    part_dir.mkdir(parents=True, exist_ok=True)
    chunk = math.ceil(size / parts)
    jobs: list[tuple[int, int, Path]] = []
    for index in range(parts):
        start = index * chunk
        if start >= size:
            break
        end = min(size - 1, start + chunk - 1)
        jobs.append((start, end, part_dir / f"part-{index:03d}.bin"))
    last_error: Exception | None = None
    for base_url in BASE_URLS:
        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        download_range,
                        f"{base_url}/{name}",
                        part,
                        start,
                        end,
                    )
                    for start, end, part in jobs
                ]
                for future in as_completed(futures):
                    future.result()
            break
        except Exception as exc:
            last_error = exc
    else:
        raise RuntimeError(f"All download sources failed for {name}: {last_error}")
    assembling = ROOT / f".{name}.assembling"
    with assembling.open("wb") as output:
        for _, _, part in jobs:
            with part.open("rb") as source:
                shutil.copyfileobj(source, output, length=16 * 1024 * 1024)
    if assembling.stat().st_size != size:
        raise RuntimeError(f"Assembled size mismatch for {name}")
    actual_hash = sha256(assembling)
    if actual_hash != expected_hash:
        raise RuntimeError(f"SHA-256 mismatch for {name}: {actual_hash} != {expected_hash}")
    os.replace(assembling, destination)
    for _, _, part in jobs:
        part.unlink(missing_ok=True)
    part_dir.rmdir()
    return destination
