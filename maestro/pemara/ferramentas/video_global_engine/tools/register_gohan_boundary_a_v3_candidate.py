from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
SOURCE = Path(r"C:\Users\admin_remoto\.codex\generated_images\01a01ac7-2d55-7082-bd5e-61f8b41eb18a\exec-10eaeeb9-68d0-4024-8037-5642454a57df.png")
TARGET = PROJECT / "base_images" / "boundary_A_android16_speech_cell_threat_candidate_v3.png"
META = TARGET.with_suffix(".json")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"fonte ausente: {SOURCE}")
    if TARGET.exists():
        raise SystemExit(f"candidata já existe: {TARGET}")
    shutil.copy2(SOURCE, TARGET)
    now = datetime.now().astimezone().isoformat()
    sha = digest(TARGET)
    metadata = {
        "schema_version": "2.0",
        "project_id": "gohan_ssj2_android16_cell_6x10s_liveaction_v1",
        "asset_id": "boundary_A_android16_speech_cell_threat_candidate_v3",
        "role": "take_01_start_shared_moving_boundary_candidate",
        "visual_route_id": "GOHAN_SSJ2_CELL_VEJITO_STANDARD_LIVEACTION_R1",
        "image_file": str(TARGET),
        "sha256": sha,
        "generator": "OpenAI built-in image generation",
        "status": "PENDING_HUMAN_QC",
        "created_at": now,
        "reference_roles": {
            "android16_identity_only": "archived owner-approved anchor_00_speech_onset_candidate.png",
            "production_finish_only": "Vejito canonical final_master_boundary_contact_12frames_v1.jpg",
        },
        "art_direction_qc": {
            "internal_status": "PASS_TO_OWNER_REVIEW",
            "photorealistic_live_action": True,
            "android16_face_and_scalp_green": False,
            "android16_green_only_on_detached_lower_armor": True,
            "cell_tail_present": False,
            "forbidden_render_mode_detected": False,
            "human_review": "PENDING",
        },
        "previous_rejected_candidates": [
            "base_images/rejected/boundary_A_v1_rejected_android16_organic_face.png",
            "base_images/rejected/boundary_A_v2_rejected_android16_green_head.png",
        ],
    }
    write_json(META, metadata)

    queue_path = PROJECT / "take_queue.json"
    queue = read_json(queue_path)
    take = next(item for item in queue["takes"] if item["id"] == "01")
    take["base_image"] = {
        "status": "pending_human_qc",
        "file": str(TARGET),
        "metadata": str(META),
        "sha256": sha,
    }
    take["art_direction_gate"]["anchor_status"] = "PENDING_HUMAN_QC"
    take["art_direction_gate"]["human_anchor_review"] = "PENDING"
    take["maestro_status"] = "NEEDS_REVIEW"
    queue["status"] = "BOUNDARY_A_V3_PENDING_OWNER_REVIEW"
    queue["updated_at"] = now
    write_json(queue_path, queue)

    project_path = PROJECT / "project_manifest.json"
    project = read_json(project_path)
    project["status"] = "BOUNDARY_A_V3_PENDING_OWNER_REVIEW"
    project["maestro_status"] = "NEEDS_REVIEW"
    project["opening_anchor_candidate"] = metadata
    project["updated_at"] = now
    write_json(project_path, project)

    with (PROJECT / "FIXLOG.md").open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n## {now} — Âncora A candidata V3\n\n"
            "- V1 reprovada internamente por rosto orgânico/zumbi no Android 16.\n"
            "- V2 reprovada pelo proprietário por tornar a cabeça do Android 16 verde.\n"
            "- V3 reconstruída do zero com identidade aprovada: rosto/couro cabeludo claros, moicano laranja e verde restrito aos fragmentos inferiores de armadura.\n"
            "- Registrada apenas como candidata; geração de vídeo permanece bloqueada.\n"
        )
    print(json.dumps({"status": "PENDING_HUMAN_QC", "image": str(TARGET), "sha256": sha}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
