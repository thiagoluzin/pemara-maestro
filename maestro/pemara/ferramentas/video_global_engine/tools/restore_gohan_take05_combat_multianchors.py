from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ARCHIVE = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\archive"
    r"\owner_rejected_routes"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1__rejected_regressive_v6__20260820_225449"
)
PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
SOURCE_DIR = ARCHIVE / "keyframes"
TARGET_DIR = PROJECT / "base_images" / "approved"
REGISTRY_PATH = PROJECT / "qc" / "approved_take05_combat_multianchor_registry.json"
FILES = {
    "K1": "take07_multi_anchor_A_parry_tailless_v1_1664x936.png",
    "K2": "take07_multi_anchor_B_body_punch_tailless_v1_1664x936.png",
    "K3": "take07_frenetic_C_rising_knee_anchor_v2_1664x936.png",
}
TZ = ZoneInfo("America/Sao_Paulo")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    restored: dict[str, dict] = {}
    for anchor_id, name in FILES.items():
        source = SOURCE_DIR / name
        if not source.is_file():
            raise FileNotFoundError(source)
        expected = digest(source)
        target = TARGET_DIR / f"boundary_{anchor_id}_{name}"
        if target.exists() and digest(target) != expected:
            raise RuntimeError(f"Destino divergente: {target}")
        if not target.exists():
            shutil.copy2(source, target)
        actual = digest(target)
        if actual != expected:
            raise RuntimeError(f"Copia divergente da ancora {anchor_id}")
        metadata = target.with_suffix(".json")
        record = {
            "anchor_id": anchor_id,
            "status": "approved_for_video",
            "file": str(target),
            "metadata": str(metadata),
            "sha256": actual,
            "source_file": str(source),
            "source_sha256": expected,
            "pixels_modified": False,
            "approval_basis": (
                "Existing combat anchor photos were approved in Maestro; owner later reaffirmed "
                "that the anchor photos are excellent and must not be regenerated."
            ),
            "rejected_video_reused": False,
            "restored_at": datetime.now(TZ).isoformat(),
        }
        metadata.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        restored[anchor_id] = record
    registry = {
        "status": "PASS_OWNER_APPROVED_EXACT_COPIES",
        "purpose": "Take 05 frenetic combat adjacent-anchor chain",
        "image_generation_used": False,
        "video_from_rejected_route_used": False,
        "anchors": restored,
        "created_at": datetime.now(TZ).isoformat(),
    }
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "ok": True,
        "registry": str(REGISTRY_PATH),
        "anchors": {
            key: {"file": value["file"], "sha256": value["sha256"]}
            for key, value in restored.items()
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
