"""Register anchor 07 for T08 while preserving approved anchor 06 as T07 start."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
PROJECTS = BASE / "ferramentas" / "video_global_engine" / "projetos"
PROJECT_ID = "vejito_super_boo_ltx25_60s"
PROJECT = PROJECTS / PROJECT_ID
sys.path.insert(0, str(STUDIO))

from video_projects import _atomic_json_write, register_anchor_candidate, utc_now  # noqa: E402


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    queue = read_json(queue_path)
    by_id = {str(item.get("id")): item for item in queue["takes"] if isinstance(item, dict)}
    now = utc_now()

    anchor_06 = (PROJECT / "keyframes" / "anchor_06.png").resolve()
    take_07 = by_id["T07"]
    take_07["base_image"] = {
        "status": "approved_for_video",
        "file": str(anchor_06),
        "model": "OpenAI built-in imagegen",
        "prompt": "Approved shared anchor 06: Super Saiyan Vegetto and Super Boo locked above the clouds.",
        "image_sha256": digest(anchor_06),
        "approved_at": now,
    }
    requests_07 = take_07.get("maestro_director_requests")
    if isinstance(requests_07, list) and requests_07:
        requests_07[-1]["status"] = "CANCELLED"
        requests_07[-1]["updated_at"] = now
    take_07["qc"]["status"] = "anchor_approved_for_video"
    take_07["maestro_updated_at"] = now
    queue["updated_at"] = now
    _atomic_json_write(queue_path, queue)

    queue = read_json(queue_path)
    take_08 = next(item for item in queue["takes"] if item.get("id") == "T08")
    requests = take_08.get("maestro_director_requests")
    if not isinstance(requests, list) or not requests:
        raise ValueError("T08 sem pedido de ancora no Maestro.")
    request_id = str(requests[-1].get("id") or "")
    image = PROJECT / "keyframes" / "candidates" / "continuation_block" / "anchor_07_candidate_v1_1536x864.png"
    image_hash = digest(image)
    prompt = (
        "Super Boo hits the shattered battlefield first, opens a fresh deep crater, and keeps one clear grip "
        "on Super Saiyan Vegetto's ankle while pulling him downward; Vegetto twists from attack into defense."
    )
    result = register_anchor_candidate(
        PROJECTS,
        PROJECT_ID,
        "T08",
        request_id=request_id,
        image_bytes=image.read_bytes(),
        original_filename=image.name,
        metadata={
            "prompt": prompt,
            "model": "OpenAI built-in imagegen",
            "negative": "anime, animation, cel shading, manga, cartoon, 3D render, game cinematic, plastic skin, extra character, duplicate fighter, missing Potara, black hair, text, logo, watermark",
            "sourceOutput": str((image.parent / "anchor_07_candidate_v1_source.png").resolve()),
            "sourceGeneratedAt": now,
            "sourceSha256": image_hash,
            "generator": "OpenAI built-in imagegen",
            "workflow": "anchor06_identity_reference_then_exact_16x9_inspected_crop",
            "objective": prompt,
            "requiredObjects": {
                "characters": ["Vegetto Super Saiyan", "Super Boo"],
                "action": "Super Boo grips Vegetto ankle at a newly formed crater",
                "potaraContinuity": "required on every unobscured visible fused ear",
            },
        },
    )

    manifest_path = PROJECT / "project_manifest.json"
    manifest = read_json(manifest_path)
    batches = manifest.setdefault("anchor_candidate_batches", {})
    continuation = batches.setdefault("continuation", {"candidates": []})
    continuation["status"] = "ANCHOR_07_PENDING_HUMAN_APPROVAL_IN_MAESTRO"
    continuation["updated_at"] = now
    record = {
        "anchor": "anchor_07",
        "status": "PENDING_HUMAN_APPROVAL_IN_MAESTRO",
        "path": "keyframes/candidates/continuation_block/anchor_07_candidate_v1_1536x864.png",
        "source_path": "keyframes/candidates/continuation_block/anchor_07_candidate_v1_source.png",
        "width": 1536,
        "height": 864,
        "sha256": image_hash.upper(),
        "maestro_take": "T08",
        "maestro_request_id": request_id,
    }
    continuation["candidates"] = [
        item for item in continuation.get("candidates", [])
        if isinstance(item, dict) and item.get("anchor") != "anchor_07"
    ] + [record]
    manifest["updated_at"] = now
    _atomic_json_write(manifest_path, manifest)
    print(json.dumps({
        "takeId": result.get("takeId"),
        "qcStatus": result.get("qcStatus"),
        "anchorCandidate": result.get("anchorCandidate"),
        "registered": record,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
