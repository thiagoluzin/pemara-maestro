"""Reconcile the six approved Gohan take records with Maestro's canonical state.

This does not approve the dialogue full film.  It only mirrors the owner take
decisions already exposed by the live Maestro project endpoint, after matching
each active file and SHA-256.  Original manifests are archived for rollback.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import requests


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
) / PROJECT_ID
API = f"http://127.0.0.1:8029/api/video-projects/{PROJECT_ID}"
MANIFEST_NAMES = ("production_manifest.json", "take_queue.json")


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid JSON root: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    response = requests.get(API, timeout=20)
    response.raise_for_status()
    live = response.json()
    readiness = live.get("assemblyReadiness") or {}
    counts = live.get("takeCounts") or {}
    if readiness.get("ready") is not True or readiness.get("blockers"):
        raise RuntimeError("Live Maestro assembly readiness is not clean")
    if int(counts.get("approved") or 0) != 6:
        raise RuntimeError(f"Expected six approved takes in Maestro, got {counts}")
    if (live.get("finalOutput") or {}).get("ready") is True:
        raise RuntimeError("A final output already exists; refusing to overwrite state")

    live_sources = readiness.get("sources") or []
    if [str(item.get("takeId")) for item in live_sources] != ["01", "02", "03", "04", "05", "06"]:
        raise RuntimeError("Live Maestro source order differs from the six-take contract")
    source_by_id = {str(item["takeId"]): item for item in live_sources}
    observed_at = now_local()
    fingerprint = str(readiness.get("sourceFingerprint") or "")
    if not fingerprint:
        raise RuntimeError("Live Maestro did not provide a source fingerprint")

    documents = {name: load(PROJECT / name) for name in MANIFEST_NAMES}
    verified_sources: list[dict] = []
    canonical = documents["take_queue.json"]
    for take in canonical.get("takes") or []:
        take_id = str(take.get("id") or "")
        if take_id not in source_by_id:
            raise RuntimeError(f"Take {take_id} is absent from live Maestro readiness")
        video = take.get("video") or {}
        active = Path(str(video.get("output_active") or "")).resolve(strict=True)
        if not active.is_relative_to(PROJECT.resolve()):
            raise RuntimeError(f"Take {take_id} active video left the project")
        relative = active.relative_to(PROJECT.resolve()).as_posix()
        live_relative = str(source_by_id[take_id].get("videoFile") or "").replace("\\", "/")
        if relative != live_relative:
            raise RuntimeError(f"Take {take_id} active file differs from live Maestro")
        actual_hash = sha256(active)
        declared_hash = str(video.get("sha256") or "").lower()
        if not declared_hash or declared_hash != actual_hash:
            raise RuntimeError(f"Take {take_id} SHA-256 drift")
        if active.stat().st_size != int(source_by_id[take_id].get("videoBytes") or -1):
            raise RuntimeError(f"Take {take_id} byte size differs from live Maestro")
        verified_sources.append(
            {
                "take_id": take_id,
                "file": str(active),
                "relative_file": relative,
                "sha256": actual_hash,
                "bytes": active.stat().st_size,
                "fps": video.get("fps"),
                "frames": video.get("frames"),
                "duration_seconds": video.get("duration_seconds"),
            }
        )

    archive = PROJECT / "archive" / f"maestro_take_approval_reconciliation_{datetime.now():%Y%m%d_%H%M%S}"
    archive.mkdir(parents=True, exist_ok=False)
    for name in MANIFEST_NAMES:
        shutil.copy2(PROJECT / name, archive / f"{name}.before.json")

    approval_record = {
        "source": "LIVE_MAESTRO_PROJECT_ENDPOINT",
        "endpoint": API,
        "observed_at": observed_at,
        "live_updated_at": live.get("updatedAt"),
        "approved_take_count": 6,
        "source_fingerprint": fingerprint,
        "files_and_hashes_verified": True,
        "scope": "TAKES_01_TO_06_ONLY_FULL_FILM_REMAINS_PENDING_OWNER_REVIEW",
        "rollback_archive": str(archive),
    }

    for name, document in documents.items():
        by_id = {str(item.get("id")): item for item in document.get("takes") or []}
        if sorted(by_id) != ["01", "02", "03", "04", "05", "06"]:
            raise RuntimeError(f"{name} does not contain exactly the six main takes")
        for source in verified_sources:
            take = by_id[source["take_id"]]
            video = take.get("video") or {}
            if Path(str(video.get("output_active") or "")).resolve() != Path(source["file"]).resolve():
                raise RuntimeError(f"{name} take {source['take_id']} points to another video")
            if str(video.get("sha256") or "").lower() != source["sha256"]:
                raise RuntimeError(f"{name} take {source['take_id']} points to another hash")
            take["status"] = "APPROVED"
            take["maestro_status"] = "APPROVED"
            take.setdefault("release_gates", {})["human"] = "APPROVED"
            take["owner_take_approval"] = {
                "status": "APPROVED",
                "source": "MAESTRO_CANONICAL_STATE",
                "observed_at": observed_at,
                "source_fingerprint": fingerprint,
                "approved_file_sha256": source["sha256"],
                "scope": "THIS_TAKE_ONLY",
            }
        document["status"] = "TAKES_01_06_APPROVED_FULL_FILM_DIALOGUE_REVIEW_PENDING"
        document["updated_at"] = observed_at
        document["owner_take_approval_reconciliation"] = approval_record
        assembly = document.setdefault("assembly", {})
        assembly["status"] = "READY_FOR_DIALOGUE_FULL_FILM_REVIEW_ASSEMBLY"
        assembly["all_sources_owner_approved"] = True
        assembly["sources"] = verified_sources
        assembly["full_film_owner_approval"] = "PENDING"
        atomic_json(PROJECT / name, document)

    project_manifest_path = PROJECT / "project_manifest.json"
    project_manifest = load(project_manifest_path)
    shutil.copy2(project_manifest_path, archive / "project_manifest.json.before.json")
    project_manifest["status"] = "TAKES_01_06_APPROVED_FULL_FILM_DIALOGUE_REVIEW_IN_PROGRESS"
    project_manifest["maestro_status"] = "IN_PROGRESS"
    project_manifest["updated_at"] = observed_at
    project_manifest["owner_take_approval_reconciliation"] = approval_record
    atomic_json(project_manifest_path, project_manifest)

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "created_at": observed_at,
        "project_id": PROJECT_ID,
        "approval_scope": "TAKES_01_TO_06_ONLY",
        "full_film_owner_review": "PENDING",
        "maestro": {
            "updated_at": live.get("updatedAt"),
            "approved": counts.get("approved"),
            "assembly_ready": readiness.get("ready"),
            "source_fingerprint": fingerprint,
        },
        "verified_sources": verified_sources,
        "rollback_archive": str(archive),
    }
    atomic_json(PROJECT / "qc" / "maestro_take_approval_reconciliation_v1.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
