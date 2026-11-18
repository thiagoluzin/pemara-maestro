from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
ARCHIVE = ENGINE / "archive" / "owner_rejected_routes" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1__rejected_regressive_v6__20260820_225449"
APPROVED = PROJECT / "base_images" / "approved"
CONTACT = PROJECT / "qc" / "approved_anchor_contact_sheet_9frames.jpg"
ROUTE_ID = "GOHAN_SSJ2_CELL_VEJITO_STANDARD_LIVEACTION_R1"


ANCHORS = [
    ("A", "keyframes", "anchor_00_speech_onset_candidate"),
    ("B", "keyframes", "anchor_01_pre_stomp_candidate"),
    ("C", "base_images", "take02_cell_esmaga_android_16_anchor_9804af7c5312"),
    ("D", "base_images", "take03_gohan_super_saiyajin_2_anchor_d8724f626c47"),
    ("E", "base_images", "take04_cell_juniors_em_um_golpe_anchor_1d0a20158ca8"),
    ("F", "base_images", "take05_gohan_domina_cell_corpo_a_corpo_anchor_7bc8888ef1d6"),
    ("G", "base_images", "take06_cell_lancado_pela_arena_anchor_bdd4b9b79e35"),
    ("H", "base_images", "take07_gohan_cell_trocacao_pressao_anchor_4dbdaabe7124"),
    ("I", "base_images", "take08_gohan_kamehameha_cell_montanha_anchor_fd584da7b853"),
]

TAKE_BOUNDARIES = {
    "01": ("A", "C", ["B"]),
    "02": ("C", "D", []),
    "03": ("D", "E", []),
    "04": ("E", "F", []),
    "05": ("F", "H", ["G"]),
    "06": ("H", "I", []),
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def approved(metadata: dict) -> bool:
    decision = str(metadata.get("human_review", {}).get("decision", "")).upper()
    statuses = " ".join(
        str(metadata.get(key, "")).upper()
        for key in ("status", "validation_status")
    )
    visual = str(metadata.get("visual_qc", {}).get("status", "")).upper()
    return decision == "APPROVED" or "APPROVED" in statuses or "OWNER_APPROVED" in visual


def build_contact_sheet(paths: list[Path]) -> None:
    filters = []
    labels = []
    for index in range(len(paths)):
        filters.append(
            f"[{index}:v]scale=480:270:force_original_aspect_ratio=decrease,"
            f"pad=480:270:(ow-iw)/2:(oh-ih)/2:black[a{index}]"
        )
        labels.append(f"[a{index}]")
    layout = "0_0|480_0|960_0|0_270|480_270|960_270|0_540|480_540|960_540"
    filters.append("".join(labels) + f"xstack=inputs=9:layout={layout}[out]")
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for path in paths:
        command.extend(["-i", str(path)])
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", "-q:v", "2", str(CONTACT)])
    subprocess.run(command, check=True)


def main() -> None:
    if not PROJECT.is_dir() or not ARCHIVE.is_dir():
        raise SystemExit("projeto ativo ou arquivo rejeitado ausente")
    APPROVED.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().isoformat()
    registry: dict[str, dict] = {}
    ordered_paths: list[Path] = []

    for label, folder, stem in ANCHORS:
        source_image = ARCHIVE / folder / f"{stem}.png"
        source_meta = ARCHIVE / folder / f"{stem}.json"
        if not source_image.is_file() or not source_meta.is_file():
            raise SystemExit(f"âncora ou metadata ausente: {stem}")
        metadata = read_json(source_meta)
        if not approved(metadata):
            raise SystemExit(f"âncora não tem evidência de aprovação: {stem}")
        source_sha = sha256(source_image)
        expected = str(metadata.get("image_sha256") or metadata.get("sha256") or "").lower()
        if expected and expected != source_sha:
            raise SystemExit(f"hash diverge para {stem}: {source_sha}")

        target_image = APPROVED / f"boundary_{label}_{stem}.png"
        target_meta = target_image.with_suffix(".json")
        if target_image.exists() or target_meta.exists():
            raise SystemExit(f"destino já existe: {target_image}")
        shutil.copy2(source_image, target_image)
        copied_sha = sha256(target_image)
        if copied_sha != source_sha:
            raise SystemExit(f"cópia sem integridade: {stem}")
        normalized = {
            "schema_version": "2.0",
            "label": label,
            "asset_id": stem,
            "visual_route_id": ROUTE_ID,
            "image_file": str(target_image),
            "sha256": copied_sha,
            "status": "APPROVED_FOR_VIDEO",
            "approval": {
                "previous_evidence": {
                    "source_metadata": str(source_meta),
                    "source_status": metadata.get("status") or metadata.get("validation_status"),
                    "human_review": metadata.get("human_review", {}),
                    "visual_qc": metadata.get("visual_qc", {}),
                },
                "reconfirmed_by_owner_at": now,
                "reconfirmation_message": "as fotos ancoras estao otimas, nao sei pq inventar e fazer novas",
            },
            "copy_integrity": "sha256_match",
            "source_archive": str(source_image),
            "media_regenerated": False,
        }
        write_json(target_meta, normalized)
        registry[label] = {
            "file": str(target_image),
            "metadata": str(target_meta),
            "sha256": copied_sha,
            "status": "approved_for_video",
        }
        ordered_paths.append(target_image)

    build_contact_sheet(ordered_paths)
    contact_sha = sha256(CONTACT)
    write_json(PROJECT / "qc" / "approved_anchor_registry.json", {
        "status": "PASS_OWNER_APPROVED_EXACT_COPIES",
        "created_at": now,
        "owner_message": "as fotos ancoras estao otimas, nao sei pq inventar e fazer novas",
        "source_route_video_status": "REJECTED_NOT_REUSED",
        "anchors": registry,
        "contact_sheet": str(CONTACT),
        "contact_sheet_sha256": contact_sha,
        "image_generation_used": False,
    })

    for filename in ("production_manifest.json", "take_queue.json"):
        path = PROJECT / filename
        data = read_json(path)
        data["anchors"] = registry
        data["approved_anchor_contact_sheet"] = str(CONTACT)
        for item in data["takes"]:
            start, end, internal = TAKE_BOUNDARIES[item["id"]]
            item["base_image"] = dict(registry[start])
            item["end_image"] = dict(registry[end])
            item["internal_anchors"] = [dict(registry[label], label=label) for label in internal]
            item["art_direction_gate"]["anchor_status"] = "PASS"
            item["art_direction_gate"]["human_anchor_review"] = "APPROVED"
            item["art_direction_gate"]["anchor_contact_sheet"] = str(CONTACT)
            item["status"] = "READY_FOR_VIDEO_PREFLIGHT"
            item["maestro_status"] = "READY"
            item["render_authorized"] = False
        data["status"] = "APPROVED_ANCHORS_RESTORED_VIDEO_PREFLIGHT_REQUIRED"
        data["render_authorized"] = False
        data["updated_at"] = now
        if filename == "production_manifest.json":
            data["art_direction_bible"]["anchor_source_policy"] = "reuse_exact_owner_approved_images_no_regeneration"
            data["art_direction_bible"]["owner_anchor_reconfirmation"] = now
        write_json(path, data)

    project_path = PROJECT / "project_manifest.json"
    project = read_json(project_path)
    project["status"] = "APPROVED_ANCHORS_RESTORED_VIDEO_PREFLIGHT_REQUIRED"
    project["maestro_status"] = "READY"
    project["render_authorized"] = False
    project["approved_anchors"] = registry
    project["approved_anchor_contact_sheet"] = str(CONTACT)
    project["updated_at"] = now
    write_json(project_path, project)

    with (PROJECT / "FIXLOG.md").open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n## {now} — restauração das âncoras aprovadas\n\n"
            "- O proprietário esclareceu que somente o vídeo/rota deveria ser descartado; as fotos-âncora estavam ótimas.\n"
            "- Nove PNGs aprovados foram copiados byte a byte do rollback, com SHA-256 conferido.\n"
            "- Nenhuma âncora foi regenerada; as intermediárias B e G foram aninhadas nos Takes 01 e 05.\n"
            "- O Maestro continua mostrando somente os seis takes principais e vídeo permanece bloqueado até o preflight.\n"
        )
    print(json.dumps({
        "status": "APPROVED_ANCHORS_RESTORED",
        "anchor_count": len(registry),
        "contact_sheet": str(CONTACT),
        "contact_sheet_sha256": contact_sha,
        "video_generation_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
