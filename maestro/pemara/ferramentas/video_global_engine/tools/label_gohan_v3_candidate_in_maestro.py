from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
MANIFEST_PATH = PROJECT_ROOT / "project_manifest.json"
QUEUE_PATH = PROJECT_ROOT / "take_queue.json"
ARCHIVE_DIR = PROJECT_ROOT / "archive" / "catalog_labels_before_v3"

PROJECT_TITLE = "GOHAN SSJ2 — PROJETO ÚNICO — Android 16 e Cell"
TAKE_SLUG = "NOVO_V3_TAKE_02_CELL_ESMAGA_ANDROID_16_4S_REVISAR"
TAKE_TITLE = "NOVO V3 — Take 02 — Cell esmaga Android 16 — 4s — REVISAR"
NOTE_PREFIX = "IDENTIFICAÇÃO NO MAESTRO: " + TAKE_TITLE + ". "


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    manifest = read_json(MANIFEST_PATH)
    queue = read_json(QUEUE_PATH)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for source in (MANIFEST_PATH, QUEUE_PATH):
        backup = ARCHIVE_DIR / source.name
        if not backup.exists():
            shutil.copy2(source, backup)

    manifest["title"] = PROJECT_TITLE
    manifest["updated_at"] = now

    take02 = next((take for take in queue.get("takes", []) if str(take.get("id")) == "02"), None)
    if take02 is None:
        raise RuntimeError("Take 02 não foi encontrado; nenhuma alteração foi gravada.")

    take02["slug"] = TAKE_SLUG
    take02["title"] = TAKE_TITLE
    existing_notes = str(take02.get("maestro_notes", "")).strip()
    if not existing_notes.startswith(NOTE_PREFIX):
        take02["maestro_notes"] = NOTE_PREFIX + existing_notes
    take02["maestro_updated_at"] = now
    queue["updated_at"] = now

    write_json_atomic(MANIFEST_PATH, manifest)
    write_json_atomic(QUEUE_PATH, queue)

    print(json.dumps({
        "project_id": manifest.get("project_id"),
        "project_title": manifest.get("title"),
        "take_id": take02.get("id"),
        "take_slug": take02.get("slug"),
        "take_title": take02.get("title"),
        "preview": take02.get("video", {}).get("output_preview"),
        "status": take02.get("maestro_status"),
        "human_approval": take02.get("qc", {}).get("human_visual_approval"),
        "backup_dir": str(ARCHIVE_DIR),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
