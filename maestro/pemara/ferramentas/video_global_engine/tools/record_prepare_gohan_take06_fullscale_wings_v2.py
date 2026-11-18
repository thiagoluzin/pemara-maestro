from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write  # noqa: E402


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
MANIFEST_NAMES = ("take_queue.json", "production_manifest.json", "project_manifest.json")
REASON = (
    "Cell perde a escala adulta e fica pequeno; as duas asas dorsais surgem apenas "
    "durante o take, em vez de existirem desde o primeiro quadro."
)
CORRECTION_PROMPT = (
    "One uninterrupted photorealistic live-action finishing shot using the exact owner-approved "
    "H, G and I boundaries. Perfect Cell is a full-height adult heavyweight from the first frame "
    "through the mountain impact, always keeping the same body scale and proportions relative to "
    "Gohan and the environment. Both black dorsal wings are already fully formed and clearly present "
    "in frame one and remain physically attached, unchanged and visible throughout; they never sprout, "
    "grow, appear, retract, merge, disappear or morph. Cell is completely tailless in every frame. "
    "SSJ2 Gohan catches him at full speed, lands two heavy connected impacts, launches him toward the "
    "mountain and immediately fires a massive blue-white Kamehameha that drives the same full-size Cell "
    "into the rock face. Fast physical camera translation, real depth, continuous action and moving "
    "debris through the last frame. No miniature Cell, scale drift, new anatomy, tail, animation, anime, "
    "cel shading, game render, plastic CGI, pose hold, internal cut or static aftermath."
)


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT / path


def find_take(document: dict, take_id: str = "06") -> dict | None:
    takes = document.get("takes")
    if not isinstance(takes, list):
        return None
    for take in takes:
        if isinstance(take, dict) and str(take.get("id") or "") == take_id:
            return take
    return None


def protected_take_fingerprints(document: dict) -> dict[str, str]:
    takes = document.get("takes")
    if not isinstance(takes, list):
        return {}
    return {
        str(take.get("id")): canonical(take)
        for take in takes
        if isinstance(take, dict) and str(take.get("id")) in {"01", "02", "03", "04", "05"}
    }


def append_unique_history(video: dict, record: dict) -> None:
    history = video.setdefault("output_history", [])
    if not isinstance(history, list):
        history = []
        video["output_history"] = history
    path = str(record.get("path") or "")
    digest = str(record.get("sha256") or "")
    for item in history:
        if isinstance(item, dict) and str(item.get("path") or "") == path and str(item.get("sha256") or "") == digest:
            item.update(record)
            return
    history.append(record)


def mark_take_for_replacement(take: dict, rejected: dict, stamp: str) -> None:
    take["status"] = "USER_REJECTED_CORRECTED_CANDIDATE_REQUIRED"
    take["maestro_status"] = "DIRECTOR_REVIEW"
    take["render_authorized"] = True
    take["render_block_reason"] = ""
    take["animation_prompt"] = CORRECTION_PROMPT
    take["maestro_updated_at"] = stamp
    take["maestro_last_error"] = ""
    take["qc_status"] = "user_rejected_director_pending"

    generation = take.setdefault("generation", {})
    if isinstance(generation, dict):
        generation.update({
            "status": "CORRECTED_CANDIDATE_PENDING_GENERATION",
            "native_output": "",
            "output_preview": "",
            "output_sha256": "",
        })

    release = take.setdefault("release_gates", {})
    if isinstance(release, dict):
        release.update({
            "art_direction": "REJECTED_IDENTITY_CONTINUITY",
            "cinematic": "PENDING_REPLACEMENT",
            "motion": "PENDING_REPLACEMENT",
            "technical": "PENDING_REPLACEMENT",
            "human": "REJECTED",
            "video_contact_sheet": "",
        })

    video = take.setdefault("video", {})
    if not isinstance(video, dict):
        video = {}
        take["video"] = video
    append_unique_history(video, {
        "path": rejected["path"],
        "sha256": rejected["sha256"],
        "role": "owner_rejected_candidate_preserved_not_for_assembly",
        "rejected_at": stamp,
        "reason": REASON,
    })
    previous_active = str(video.get("output_active") or video.get("output_preview") or "")
    if previous_active and previous_active != rejected["path"]:
        previous_path = resolve_path(previous_active)
        previous_hash = sha256(previous_path) if previous_path.is_file() else ""
        append_unique_history(video, {
            "path": str(previous_path),
            "sha256": previous_hash,
            "role": "superseded_candidate_preserved_not_for_assembly",
            "superseded_at": stamp,
        })
    video.update({
        "status": "owner_rejected_replacement_pending",
        "output_active": "",
        "output_preview": "",
        "output_review_candidate": "",
        "preview_model": "",
        "fps": 0,
        "frames": 0,
        "duration_seconds": 0,
        "sha256": "",
        "owner_rejected_candidate": copy.deepcopy(rejected),
    })

    qc = take.setdefault("qc", {})
    if not isinstance(qc, dict):
        qc = {}
        take["qc"] = qc
    qc.update({
        "status": "user_rejected_director_pending",
        "auto_approved": False,
        "human_visual_approval": "rejected",
        "director_visual_review": "REJECTED_BY_OWNER",
        "owner_video_decision": {
            "decision": "REJECTED",
            "decided_at": stamp,
            "preview": rejected["path"],
            "preview_sha256": rejected["sha256"],
            "reason": REASON,
            "source": "explicit_owner_message",
        },
    })

    request = {
        "id": uuid.uuid4().hex,
        "status": "PENDING",
        "category": "IDENTITY_CONTINUITY",
        "reason": REASON,
        "correction_contract": (
            "Cell adulto em escala constante; duas asas dorsais negras existentes desde o quadro 1 "
            "ate o impacto final; zero rabo; reutilizar somente as ancoras H, G e I ja aprovadas."
        ),
        "created_at": stamp,
        "updated_at": stamp,
    }
    requests = take.setdefault("maestro_director_requests", [])
    if not isinstance(requests, list):
        requests = []
        take["maestro_director_requests"] = requests
    requests.append(request)
    take["maestro_notes"] = (
        "REPROVADO PELO PROPRIETARIO: Cell ficou pequeno e as asas nasceram durante o video. "
        "O arquivo foi preservado, esta proibido na montagem e um substituto H-G-I foi autorizado."
    )


def main() -> None:
    documents: dict[str, dict] = {}
    protected_before: dict[str, dict[str, str]] = {}
    for name in MANIFEST_NAMES:
        path = PROJECT / name
        documents[name] = json.loads(path.read_text(encoding="utf-8-sig"))
        protected_before[name] = protected_take_fingerprints(documents[name])

    queue_take = find_take(documents["take_queue.json"])
    if not isinstance(queue_take, dict):
        raise ValueError("Take 06 ausente da fila principal.")
    queue_video = queue_take.get("video") if isinstance(queue_take.get("video"), dict) else {}
    visible_value = str(queue_video.get("output_preview") or queue_video.get("output_active") or "")
    visible_path = resolve_path(visible_value)
    if not visible_path.is_file():
        raise FileNotFoundError(f"Candidato visivel do Take 06 ausente: {visible_path}")
    rejected = {
        "path": str(visible_path),
        "sha256": sha256(visible_path),
        "reason": REASON,
        "preserved": True,
        "assembly_allowed": False,
    }

    stamp = now_local()
    archive = PROJECT / "archive" / ("before_take06_fullscale_wings_v2_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    archive.mkdir(parents=True, exist_ok=False)
    for name in MANIFEST_NAMES:
        shutil.copy2(PROJECT / name, archive / name)
    (archive / "owner_rejection_record.json").write_text(
        json.dumps({"take_id": "06", "recorded_at": stamp, **rejected}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for name in ("take_queue.json", "production_manifest.json"):
        document = documents[name]
        take = find_take(document)
        if not isinstance(take, dict):
            raise ValueError(f"Take 06 ausente de {name}.")
        mark_take_for_replacement(take, rejected, stamp)
        document["status"] = "TAKE06_CORRECTION_IN_PROGRESS"
        document["render_authorized"] = True
        document["updated_at"] = stamp

    project_manifest = documents["project_manifest.json"]
    candidates = project_manifest.get("take_review_candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict) and str(candidate.get("take_id") or "") == "06":
                candidate.update({
                    "status": "OWNER_REJECTED_REPLACEMENT_PENDING",
                    "output": "",
                    "sha256": "",
                    "owner_rejected_output": rejected["path"],
                    "owner_rejected_sha256": rejected["sha256"],
                    "owner_rejected_reason": REASON,
                    "owner_rejected_at": stamp,
                })
                break
    records = project_manifest.setdefault("take_rejection_records", [])
    if not isinstance(records, list):
        records = []
        project_manifest["take_rejection_records"] = records
    records.append({"take_id": "06", "recorded_at": stamp, **copy.deepcopy(rejected)})
    project_manifest["status"] = "TAKE06_CORRECTION_IN_PROGRESS"
    project_manifest["render_authorized"] = True
    project_manifest["updated_at"] = stamp

    for name, document in documents.items():
        after = protected_take_fingerprints(document)
        if after != protected_before[name]:
            raise AssertionError(f"Protecao falhou: um dos Takes 01-05 mudou em {name}.")

    for name, document in documents.items():
        _atomic_json_write(PROJECT / name, document)

    print(json.dumps({
        "ok": True,
        "take_id": "06",
        "rejected": rejected,
        "replacement_status": "CORRECTED_CANDIDATE_PENDING_GENERATION",
        "approved_01_05_unchanged": True,
        "archive": str(archive),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
