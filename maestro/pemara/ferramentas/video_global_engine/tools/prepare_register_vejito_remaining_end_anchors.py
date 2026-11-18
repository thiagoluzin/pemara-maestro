"""Normalize and register the four remaining Vegetto end anchors for owner review."""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


BASE = Path(r"E:\Pemara\maestro\pemara")
PROJECT_ID = "vejito_super_boo_minimax_h3_8x8s"
PROJECTS = BASE / "ferramentas" / "video_global_engine" / "projetos"
PROJECT = PROJECTS / PROJECT_ID
STUDIO = BASE / "services" / "studio"
STAGING = PROJECT / "keyframes" / "candidates" / "remaining_story_boundaries"
sys.path.insert(0, str(STUDIO))

from video_projects import _atomic_json_write, register_anchor_candidate  # noqa: E402


SPECS = {
    "M05": {
        "anchor": "anchor_08",
        "source": Path(r"C:\Users\admin_remoto\.codex\generated_images\01a0014d-6b3d-7260-a3c3-741bf24ae132\exec-d98c27c5-36b0-42a5-8247-449bce639066.png"),
        "objective": "Vegetto reverte a tracao e arremessa Super Boo atraves de duas ilhas rochosas, que permanecem destruidas.",
        "prompt": "Photorealistic live-action anchor_08: exact Super Saiyan Vegetto follows through after throwing the exact single Super Boo through two separately shattered floating islands; costume, Potara, debris sequence and storm lighting remain coherent.",
    },
    "M06": {
        "anchor": "anchor_10",
        "source": Path(r"C:\Users\admin_remoto\.codex\generated_images\01a0014d-6b3d-7260-a3c3-741bf24ae132\exec-ba4f8c6c-2dee-4b1f-8f2f-303b33e88fe2.png"),
        "objective": "Boo sobe em espiral enquanto Vegetto pousa numa ilha inclinada e inicia a concentracao azul.",
        "prompt": "Photorealistic live-action anchor_10: exact Super Boo spins upward with physical inertia while exact Super Saiyan Vegetto lands on an inclined island and begins only the first blue Kamehameha concentration; prior destruction persists.",
    },
    "M07": {
        "anchor": "anchor_11",
        "source": Path(r"C:\Users\admin_remoto\.codex\generated_images\01a0014d-6b3d-7260-a3c3-741bf24ae132\exec-2061b11e-4784-4afd-9c0c-b968cc851d70.png"),
        "objective": "Os feixes azul e rosa partem das maos em diagonais opostas, ainda separados por um vazio legivel.",
        "prompt": "Photorealistic live-action anchor_11: exact Vegetto and exact Super Boo fire one blue and one pink beam from their hands on opposite diagonals; a clear empty gap remains before collision and neither beam crosses a body.",
    },
    "M08": {
        "anchor": "anchor_12",
        "source": Path(r"C:\Users\admin_remoto\.codex\generated_images\01a0014d-6b3d-7260-a3c3-741bf24ae132\exec-6b05e359-8074-4981-9b43-c09f34a8c10e.png"),
        "objective": "A coluna azul vence o contra-feixe, arremessa Boo e deixa Vegetto exausto com os bracos abaixados.",
        "prompt": "Photorealistic live-action anchor_12: the blue Kamehameha has physically defeated the pink counter-beam, Super Boo recoils at the advancing blast front, and exhausted Super Saiyan Vegetto lowers his arms after release amid permanent environmental damage.",
    },
}


NEGATIVE = (
    "anime, animation, cel shading, manga, illustration, plastic 3D game render, "
    "extra fighter, duplicate body, duplicate limb, missing Potara, black Super Saiyan hair, "
    "beam through body, text, logo, watermark"
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = ImageOps.fit(
            image,
            (1536, 864),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        image.save(target, format="PNG", optimize=True)
    with Image.open(target) as check:
        check.load()
        if check.size != (1536, 864) or check.mode != "RGB":
            raise ValueError(f"QC dimensional falhou: {target}")


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    queue = read_json(queue_path)
    by_id = {str(item.get("id")): item for item in queue["takes"] if isinstance(item, dict)}
    queue_changed = False
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for take_id, spec in SPECS.items():
        take = by_id[take_id]
        requests = take.setdefault("maestro_director_requests", [])
        if not isinstance(requests, list):
            requests = []
            take["maestro_director_requests"] = requests
        existing_candidate = take.get("end_anchor_candidate")
        existing_request_id = (
            str(existing_candidate.get("candidate_request_id") or "")
            if isinstance(existing_candidate, dict)
            else ""
        )
        if existing_request_id:
            cleaned = [
                item
                for item in requests
                if not (
                    isinstance(item, dict)
                    and str(item.get("id") or "") != existing_request_id
                    and str(item.get("status") or "").upper() == "PENDING"
                    and str(item.get("reason") or "").startswith("Preparar anchor_")
                    and not item.get("candidate_file")
                )
            ]
            if len(cleaned) != len(requests):
                take["maestro_director_requests"] = cleaned
                queue_changed = True
            continue
        latest = requests[-1] if requests and isinstance(requests[-1], dict) else None
        if latest is None or str(latest.get("status") or "").upper() not in {"PENDING", "IN_PROGRESS"}:
            requests.append({
                "id": uuid.uuid4().hex,
                "status": "PENDING",
                "category": "ANCHOR",
                "reason": f"Preparar {spec['anchor']} como segunda ancora aprovada do take {take_id}.",
                "created_at": now,
                "updated_at": now,
                "anchor_side": "end",
            })
            queue_changed = True
    if queue_changed:
        queue["updated_at"] = now
        _atomic_json_write(queue_path, queue)

    registered = []
    for take_id, spec in SPECS.items():
        target = STAGING / f"{spec['anchor']}_candidate.png"
        normalize(spec["source"], target)
        take = by_id[take_id]
        requests = take.get("maestro_director_requests")
        if not isinstance(requests, list) or not requests:
            raise ValueError(f"{take_id} sem pedido de ancora no Maestro")
        existing = take.get("end_anchor_candidate")
        request_id = (
            str(existing.get("candidate_request_id") or "")
            if isinstance(existing, dict) and existing.get("candidate_request_id")
            else str(requests[-1].get("id") or "")
        )
        digest = sha256(target)
        metadata = {
            "prompt": spec["prompt"],
            "model": "OpenAI built-in imagegen",
            "negative": NEGATIVE,
            "sourceOutput": str(spec["source"]),
            "sourceGeneratedAt": datetime.fromtimestamp(
                spec["source"].stat().st_mtime
            ).astimezone().isoformat(timespec="seconds"),
            "sourceSha256": digest,
            "generator": "OpenAI built-in imagegen",
            "workflow": "approved_anchor06_identity_chain_then_exact_1536x864_qc",
            "objective": spec["objective"],
            "requiredObjects": {
                "anchorSide": "end",
                "storyAnchor": spec["anchor"],
                "characters": ["Vegetto Super Saiyan", "Super Boo"],
                "potaraContinuity": "required when an ear is unobscured",
                "beamPhysics": "never crosses a body without collision response",
            },
        }
        (target.with_suffix(".prompt.json")).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if isinstance(existing, dict) and existing.get("file"):
            existing_path = Path(str(existing["file"]))
            if not existing_path.is_file() or sha256(existing_path) != digest:
                raise ValueError(f"{take_id} ja possui outro candidato final registrado")
            qc_status = str((take.get("qc") or {}).get("status") or "")
        else:
            result = register_anchor_candidate(
                PROJECTS,
                PROJECT_ID,
                take_id,
                request_id=request_id,
                image_bytes=target.read_bytes(),
                original_filename=target.name,
                metadata=metadata,
            )
            qc_status = str(result.get("qcStatus") or "")
        registered.append({
            "takeId": take_id,
            "anchor": spec["anchor"],
            "staging": str(target),
            "sha256": digest.upper(),
            "width": 1536,
            "height": 864,
            "status": qc_status,
            "requestId": request_id,
        })

    manifest_path = PROJECT / "project_manifest.json"
    manifest = read_json(manifest_path)
    batches = manifest.setdefault("anchor_candidate_batches", [])
    batch_record = {
        "id": "remaining_story_boundaries",
        "status": "PENDING_HUMAN_APPROVAL_IN_MAESTRO",
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "candidates": registered,
    }
    if isinstance(batches, list):
        manifest["anchor_candidate_batches"] = [
            item
            for item in batches
            if not isinstance(item, dict) or item.get("id") != batch_record["id"]
        ] + [batch_record]
    elif isinstance(batches, dict):
        batches[batch_record["id"]] = batch_record
    else:
        manifest["anchor_candidate_batches"] = [batch_record]
    _atomic_json_write(manifest_path, manifest)
    print(json.dumps({"registered": registered}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
