from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
QUEUE = PROJECT / "take_queue.json"
EXPECTED = {
    "06R1": PROJECT / "takes" / "maestro_generated" / "take_06R1_magic_slap_corrected_v2.mp4",
    "07": PROJECT / "takes" / "maestro_generated" / "take_07_frenetic_multi_anchor_v3.mp4",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    data = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    now = datetime.now(timezone.utc).isoformat()
    approvals: list[dict[str, object]] = []
    for take_id, expected in EXPECTED.items():
        if not expected.is_file():
            raise FileNotFoundError(expected)
        take = next(item for item in data["takes"] if str(item.get("id")) == take_id)
        if str(take.get("maestro_status") or "").upper() != "APPROVED":
            raise ValueError(f"{take_id} nao esta APPROVED no Maestro")
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        active = Path(str(video.get("output_active") or ""))
        candidate = Path(str(video.get("output_review_candidate") or ""))
        if active.resolve() != expected.resolve() or candidate.resolve() != expected.resolve():
            raise ValueError(f"{take_id} nao aponta para o candidato revisado")
        qc = take.setdefault("qc", {})
        qc["status"] = "approved_by_owner"
        qc["human_visual_approval"] = "approved"
        qc["visual_approved_at"] = now
        motion_gate = qc.get("transition_motion_gate")
        if isinstance(motion_gate, dict):
            motion_gate["status"] = "approved_by_owner"
        take["status"] = "OWNER_APPROVED_FINAL"
        take["maestro_updated_at"] = now
        take["maestro_notes"] = (
            str(take.get("maestro_notes") or "").replace(
                "Pendente revisao humana.", "Aprovado pelo proprietario no Maestro."
            )
        )
        approvals.append(
            {
                "takeId": take_id,
                "file": str(expected),
                "sha256": sha256(expected),
                "approvedAt": now,
            }
        )
    temp = QUEUE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(QUEUE)
    audit = PROJECT / "qc" / "owner_approvals_06r1_07.json"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit_temp = audit.with_suffix(".json.tmp")
    audit_temp.write_text(
        json.dumps({"schemaVersion": 1, "approvals": approvals}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    audit_temp.replace(audit)
    print(json.dumps({"ok": True, "audit": str(audit), "approvals": approvals}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
