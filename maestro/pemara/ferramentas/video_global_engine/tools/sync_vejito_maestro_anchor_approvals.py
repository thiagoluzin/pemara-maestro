"""Promote only integrity-checked Maestro anchor approvals to shared keyframes."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\vejito_super_boo_ltx25_60s"
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON raiz invalido: {path}")
    return data


def write_json(path: Path, data: dict) -> None:
    temp = path.with_name(f".{path.name}.maestro-sync.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
    temp.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_anchor(take: dict, anchor_number: int) -> dict:
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if str(base.get("status") or "") != "approved_for_video":
        raise ValueError(f"T{anchor_number + 1:02d} ainda nao possui aprovacao de ancora no Maestro.")
    image = Path(str(base.get("file") or "")).resolve()
    metadata = Path(str(base.get("metadata") or "")).resolve()
    if not image.is_relative_to(PROJECT.resolve()) or not image.is_file():
        raise ValueError(f"Imagem aprovada saiu do projeto: {image}")
    if not metadata.is_relative_to(PROJECT.resolve()) or not metadata.is_file():
        raise ValueError(f"Sidecar aprovado ausente: {metadata}")
    sidecar = read_json(metadata)
    human = sidecar.get("human_review") if isinstance(sidecar.get("human_review"), dict) else {}
    visual = sidecar.get("visual_qc") if isinstance(sidecar.get("visual_qc"), dict) else {}
    image_hash = digest(image)
    if str(sidecar.get("validation_status") or "") != "approved_for_video":
        raise ValueError(f"Sidecar de anchor_{anchor_number:02d} nao esta aprovado.")
    if str(human.get("decision") or "") != "APPROVED" or not human.get("explicit_human_confirmation"):
        raise ValueError(f"anchor_{anchor_number:02d} sem confirmacao humana explicita.")
    if str(visual.get("cast_verification_status") or "") != "VERIFIED":
        raise ValueError(f"anchor_{anchor_number:02d} sem conferencia visual do elenco.")
    if str(sidecar.get("image_sha256") or "").lower() != image_hash:
        raise ValueError(f"SHA256 divergente em anchor_{anchor_number:02d}.")
    return {
        "image": image,
        "metadata": metadata,
        "sidecar": sidecar,
        "sha256": image_hash,
        "reviewed_at": str(sidecar.get("reviewed_at") or ""),
        "cast": visual.get("actual_visible_characters") or [],
    }


def promote(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(destination) != digest(source):
            raise ValueError(f"Destino canonico ja contem outro arquivo: {destination}")
        return
    shutil.copy2(source, destination)
    if digest(destination) != digest(source):
        destination.unlink(missing_ok=True)
        raise OSError(f"Falha de integridade ao promover {destination.name}.")


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    manifest_path = PROJECT / "project_manifest.json"
    production_path = PROJECT / "production_manifest.json"
    queue = read_json(queue_path)
    manifest = read_json(manifest_path)
    production = read_json(production_path)
    queue_takes = {
        str(item.get("id")): item
        for item in queue.get("takes", [])
        if isinstance(item, dict)
    }
    approvals: dict[int, dict] = {}
    for anchor_number in range(5):
        approvals[anchor_number] = approved_anchor(
            queue_takes[f"T{anchor_number + 1:02d}"], anchor_number
        )
        target = PROJECT / "keyframes" / f"anchor_{anchor_number:02d}.png"
        promote(approvals[anchor_number]["image"], target)
        canonical_sidecar = dict(approvals[anchor_number]["sidecar"])
        canonical_sidecar["canonical_shared_anchor"] = target.as_posix()
        canonical_sidecar["canonical_shared_anchor_sha256"] = approvals[anchor_number]["sha256"]
        write_json(target.with_suffix(".json"), canonical_sidecar)

    approved_numbers = set(approvals) | {5, 6}
    for take in queue_takes.values():
        take_id = str(take.get("id") or "")
        if not take_id.startswith("T") or not take_id[1:].isdigit():
            continue
        index = int(take_id[1:])
        start_number, end_number = index - 1, index
        shot = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
        refs = shot.get("visual_references") if isinstance(shot.get("visual_references"), dict) else {}
        refs.update({
            "start_frame_file": str((PROJECT / "keyframes" / f"anchor_{start_number:02d}.png").resolve()),
            "start_frame_approved": start_number in approved_numbers,
            "end_frame_file": str((PROJECT / "keyframes" / f"anchor_{end_number:02d}.png").resolve()),
            "end_frame_approved": end_number in approved_numbers,
            "shared_boundary_contract": "end anchor N is start anchor N+1",
        })
        shot["visual_references"] = refs
        take["shot_contract"] = shot
        if 1 <= index <= 5:
            take["status"] = "READY_FOR_LTX25_SERIAL_RENDER"
            take["render_authorized"] = True
            take["qc"]["human_anchor_approval"] = "approved_in_maestro"

    for take in production.get("takes", []):
        if not isinstance(take, dict):
            continue
        take_id = str(take.get("id") or "")
        if not take_id.startswith("T") or not take_id[1:].isdigit():
            continue
        index = int(take_id[1:])
        generation = take.get("generation") if isinstance(take.get("generation"), dict) else {}
        if 1 <= index <= 5:
            generation["render_authorized"] = True
            generation["status"] = "READY_FOR_LTX25_SERIAL_RENDER"
        take["generation"] = generation
        keyframes = take.get("shot_contract", {}).get("keyframes")
        if isinstance(keyframes, dict):
            keyframes["approved"] = (index - 1) in approved_numbers and index in approved_numbers
            keyframes["approval_source"] = "Maestro explicit human anchor review"

    batch = manifest.get("anchor_candidate_batches", {}).get("fusion_and_ssj", {})
    if isinstance(batch, dict):
        batch["status"] = "HUMAN_APPROVED_IN_MAESTRO_AND_PROMOTED"
        for item in batch.get("candidates", []):
            if not isinstance(item, dict):
                continue
            raw = str(item.get("anchor") or "").removeprefix("anchor_")
            if raw.isdigit() and int(raw) in approvals:
                number = int(raw)
                evidence = approvals[number]
                item.update({
                    "status": "HUMAN_APPROVED_IN_MAESTRO",
                    "maestro_reviewed_at": evidence["reviewed_at"],
                    "maestro_verified_cast": evidence["cast"],
                    "promoted_path": f"keyframes/anchor_{number:02d}.png",
                    "promoted_sha256": evidence["sha256"].upper(),
                })
    manifest["status"] = "READY_T01_TO_T05_SERIAL_LTX25_RENDER"
    manifest["maestro_status"] = "IN_PROGRESS"
    manifest["render_authorized"] = True
    manifest["render_authority"] = "Maestro explicit human anchor approvals plus owner instruction to continue"
    manifest["render_scope"] = "T01-T05 serial; each video returns to Maestro human review"
    queue["status"] = "READY_T01_TO_T05_SERIAL_LTX25_RENDER"
    queue["render_authorized"] = True

    write_json(queue_path, queue)
    write_json(production_path, production)
    write_json(manifest_path, manifest)
    print(json.dumps({
        "promoted": [f"anchor_{number:02d}" for number in approvals],
        "sha256": {f"anchor_{number:02d}": value["sha256"] for number, value in approvals.items()},
        "renderScope": manifest["render_scope"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
