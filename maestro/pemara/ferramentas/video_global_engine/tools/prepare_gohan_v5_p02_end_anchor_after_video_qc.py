"""Reject P02C1 internally and request a post-impact end anchor for FL2VA."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
TAKE_ID = "P02"
P02C1 = PROJECT / "takes" / "maestro_generated" / "take_P02_ca3bdd478de14d31_minimax_h3_preview.mp4"
P02C1_SHA256 = "45aa41fb9f971aca2c2b74950e2c633a883e9038cacb35b7eb7840706973ae57"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not P02C1.is_file() or digest(P02C1) != P02C1_SHA256:
        raise RuntimeError("O candidato P02C1 nao corresponde ao arquivo inspecionado.")
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    request_id = uuid.uuid4().hex
    queue = read_json(QUEUE_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if str(base.get("status") or "").lower() != "approved_for_video":
        raise RuntimeError("A ancora inicial P02 deixou de estar aprovada.")

    p02c1_record = {
        "file": P02C1.as_posix(),
        "sha256": P02C1_SHA256,
        "job_id": "ca3bdd478de14d31ae2e257634ed7446",
        "seed": 3125717376079737788,
        "status": "REJECTED_INTERNAL_QC",
        "reason": (
            "A cauda foi eliminada e o impacto ficou alinhado, mas a cabeca mecanica "
            "permanece intacta de 0.8 a 2.0 s e apenas sai do quadro."
        ),
        "qc_contact_sheet": (
            PROJECT / "qc" / "p02c1_no_tail_ca3bdd47" / "contact_2fps.png"
        ).as_posix(),
        "rejected_at": now,
    }
    existing_previous = []
    current_video = take.get("video") if isinstance(take.get("video"), dict) else {}
    if isinstance(current_video.get("previous_candidates"), list):
        existing_previous.extend(current_video["previous_candidates"])
    existing_previous.append(p02c1_record)

    take["status"] = "PLANNED"
    take["maestro_status"] = "PLANNED"
    take["render_authorized"] = False
    take["role"] = "v5_p02_post_impact_end_anchor_pending_human_review"
    take["maestro_notes"] = (
        "Duas geracoes preservadas e reprovadas no QC interno. Rota prompt-only encerrada. "
        "Aguardar ancora final com destrocos mecanicos reais antes de novo FL2VA."
    )
    generation = take.setdefault("video_generation", {})
    generation["render_authorized"] = False
    generation["start_end_frame_enabled"] = True
    generation["require_approved_start_frame"] = True
    generation["require_approved_end_frame"] = True
    take["video"] = {"status": "not_generated", "previous_candidates": existing_previous}
    take.pop("end_anchor_candidate", None)
    requests = take.setdefault("maestro_director_requests", [])
    requests.append({
        "id": request_id,
        "status": "PENDING",
        "category": "ANCHOR",
        "reason": (
            "Gerar a ancora final pos-impacto: cabeca do Android 16 realmente reduzida a "
            "destrocos mecanicos, Gohan em avanco ativo e Cell totalmente ausente."
        ),
        "render_instruction": (
            "Usar a identidade e o mundo da ancora inicial aprovada. Mostrar somente placas "
            "mecanicas quebradas, circuitos, fios e fragmentos; sem rosto intacto, sangue, gore, "
            "Cell, bota, cauda ou apendice."
        ),
        "created_at": now,
        "updated_at": now,
        "anchor_side": "end",
    })
    qc = take.setdefault("qc", {})
    qc["status"] = "waiting_end_anchor_generation_after_video_qc"
    qc["human_visual_approval"] = "pending_end_anchor_review"
    qc["directed_correction_attempt"] = 1
    qc["previous_candidate"] = p02c1_record
    qc["route_decision"] = "CHANGE_TO_APPROVED_START_AND_END_ANCHORS"
    qc["transition_motion_gate"] = {
        "status": "blocked_until_end_anchor_approved",
        "evident_camera": False,
        "real_depth": False,
        "internal_action": False,
        "clear_progression": False,
        "continuous_action": False,
        "motion_across_all_intervals": False,
        "no_crossfade": True,
        "no_freeze": False,
        "no_static_tail": False,
        "no_reset": False,
        "evidence": "Prompt-only route exhausted; post-impact end anchor required.",
    }
    queue["status"] = "V5_P02_END_ANCHOR_PENDING_OWNER_APPROVAL"
    queue["render_authorized"] = False
    queue["route_revision"] = {
        "take_id": TAKE_ID,
        "attempt": "P02_END_ANCHOR",
        "method": "approved start plus owner-approved post-impact end anchor",
        "request_id": request_id,
        "previous_candidates": existing_previous,
    }
    queue["updated_at"] = now
    atomic_json(QUEUE_PATH, queue)

    manifest = read_json(MANIFEST_PATH)
    manifest["status"] = "V5_P02_END_ANCHOR_PENDING_OWNER_APPROVAL"
    manifest["render_authorized"] = False
    manifest["p02_post_impact_end_anchor"] = {
        "status": "PENDING_GENERATION_AND_HUMAN_REVIEW",
        "request_id": request_id,
        "anchor_side": "end",
        "previous_candidates": existing_previous,
        "video_generation_authorized": False,
    }
    manifest["updated_at"] = now
    atomic_json(MANIFEST_PATH, manifest)
    print(json.dumps({
        "ok": True,
        "takeId": TAKE_ID,
        "requestId": request_id,
        "anchorSide": "end",
        "previousCandidatesPreserved": len(existing_previous),
        "videoGenerationAuthorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
