from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import prepare_gohan_overnight_vejito_batch as base


PROJECT = base.PROJECT
QUEUE_PATH = PROJECT / "take_queue.json"
PRODUCTION_PATH = PROJECT / "production_manifest.json"
PROJECT_PATH = PROJECT / "project_manifest.json"
MAIN_REGISTRY_PATH = PROJECT / "qc" / "approved_anchor_registry.json"
SLAP_REGISTRY_PATH = PROJECT / "qc" / "approved_take04_slap_anchor_registry.json"
REJECTION_PATH = PROJECT / "qc" / "take_04A_v1_director_rejection.json"
ARCHIVE = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\archive\owner_rejected_routes"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1__rejected_regressive_v6__20260820_225449"
)
SOURCE_ANCHOR = ARCHIVE / "keyframes" / "take06_magic_slap_deflection_anchor_v1_1664x936.png"
SOURCE_VIDEO = ARCHIVE / "takes" / "maestro_generated" / "take_06R1_magic_slap_corrected_v2.mp4"
SOURCE_APPROVAL = ARCHIVE / "qc" / "owner_approvals_06r1_07.json"
APPROVED_VIDEO_SHA256 = "bbd629bf4ecc8c3be86bc9c1a10a545ed4e88ada2f0deedb7310995ec93467e8"
APPROVED_ANCHOR_SHA256 = "f0bae3eb427c813059d3cb3ce1ac539fe33f2497ddf36716df88abe911bcc835"
DEST_ANCHOR = PROJECT / "base_images" / "approved" / "boundary_S_take04_owner_approved_magic_slap.png"
DEST_METADATA = DEST_ANCHOR.with_suffix(".json")
TZ = ZoneInfo("America/Sao_Paulo")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_anchor(raw: dict) -> dict:
    return {
        "file": raw["file"],
        "metadata": raw["metadata"],
        "sha256": raw["sha256"],
        "status": "approved_for_video",
    }


def main() -> None:
    now = datetime.now(TZ).isoformat()
    if sha256(SOURCE_VIDEO) != APPROVED_VIDEO_SHA256:
        raise RuntimeError("O video 06R1 nao corresponde ao SHA aprovado pelo proprietario.")
    if sha256(SOURCE_ANCHOR) != APPROVED_ANCHOR_SHA256:
        raise RuntimeError("A ancora do tapa divergiu do artefato aprovado preservado.")
    approval = read(SOURCE_APPROVAL)
    approval_entry = next(
        (
            item for item in approval.get("approvals", [])
            if str(item.get("takeId")) == "06R1"
            and str(item.get("sha256") or "").lower() == APPROVED_VIDEO_SHA256
        ),
        None,
    )
    if approval_entry is None:
        raise RuntimeError("O registro de aprovacao do Take 06R1 nao foi encontrado.")

    DEST_ANCHOR.parent.mkdir(parents=True, exist_ok=True)
    if not DEST_ANCHOR.exists():
        shutil.copy2(SOURCE_ANCHOR, DEST_ANCHOR)
    if sha256(DEST_ANCHOR) != APPROVED_ANCHOR_SHA256:
        raise RuntimeError("A copia da ancora aprovada nao preservou o SHA.")
    metadata = {
        "schema_version": "1.0",
        "status": "approved_for_video",
        "image_generation_used": False,
        "copied_byte_for_byte": True,
        "sha256": APPROVED_ANCHOR_SHA256,
        "source_file": str(SOURCE_ANCHOR),
        "source_video": str(SOURCE_VIDEO),
        "source_video_sha256": APPROVED_VIDEO_SHA256,
        "owner_approval": copy.deepcopy(approval_entry),
        "purpose": "Take 04 intermediate boundary locking the visible lateral magic deflection.",
        "restored_at": now,
    }
    write(DEST_METADATA, metadata)
    slap_anchor = {
        "file": str(DEST_ANCHOR),
        "metadata": str(DEST_METADATA),
        "sha256": APPROVED_ANCHOR_SHA256,
        "status": "approved_for_video",
    }
    write(SLAP_REGISTRY_PATH, {
        "schema_version": "1.0",
        "project_id": PROJECT.name,
        "image_generation_used": False,
        "source_owner_approved_video_sha256_verified": True,
        "anchors": {"S": slap_anchor},
        "updated_at": now,
    })

    queue = read(QUEUE_PATH)
    production = read(PRODUCTION_PATH)
    project = read(PROJECT_PATH)
    main_anchors = read(MAIN_REGISTRY_PATH)["anchors"]
    queue["takes"] = [
        take for take in queue["takes"]
        if str(take.get("id")) not in {"04A2", "04B"}
    ]
    main_take = next(take for take in queue["takes"] if str(take.get("id")) == "04")
    old_micro = next(take for take in queue["takes"] if str(take.get("id")) == "04A")
    old_video = copy.deepcopy(old_micro.get("video") or {})
    rejected_path = str(
        old_video.get("output_active")
        or old_video.get("output_preview")
        or old_video.get("output_review_candidate")
        or ""
    )
    if not rejected_path or not Path(rejected_path).is_file():
        raise RuntimeError("O candidato 04A v1 nao esta preservado localmente.")
    rejected = {
        "path": rejected_path,
        "status": "DIRECTOR_REJECTED_ACTION_AND_TAIL",
        "reason": (
            "The shot sustains a palm block instead of a lateral deflection and grows a visible "
            "tail on Perfect Cell during the advance."
        ),
        "preserved": True,
        "owner_reviewed": False,
        "rejected_at": now,
        "job_id": str(old_micro.get("maestro_last_job_id") or ""),
    }
    main_video = copy.deepcopy(main_take.get("video") or {})
    history = list(main_video.get("output_history") or [])
    history.append({
        "path": rejected_path,
        "role": "director_rejected_action_and_tail_candidate",
        "replaced_at": now,
        "replaced_by_job_id": "overnight-04-approved-slap-anchor-chain",
    })
    rejected_candidates = list(main_video.get("rejected_candidates") or [])
    rejected_candidates.append(rejected)
    main_take["video"] = {
        "status": "pending_internal_microsegments",
        "output_active": "",
        "output_preview": "",
        "output_review_candidate": "",
        "output_history": history,
        "rejected_candidates": rejected_candidates,
    }
    main_take["status"] = "INTERNAL_SEGMENTS_PENDING"
    main_take["maestro_status"] = "READY"
    main_take["maestro_last_job_id"] = ""
    main_take["maestro_last_error"] = ""
    main_take["render_authorized"] = False
    main_take["video_generation"]["render_authorized"] = False
    main_take.setdefault("release_gates", {})["art_direction"] = "FAIL_04A_V1_TAIL"
    main_take["release_gates"]["motion"] = "FAIL_04A_V1_BLOCK"
    main_take["release_gates"]["human"] = "PENDING"

    anchor_e = clean_anchor(main_anchors["E"])
    anchor_f = clean_anchor(main_anchors["F"])
    first = base.micro_take(
        main_take,
        "04A2",
        "INTERNAL 04A2 — esfera e tapa curvo E-S",
        anchor_e,
        slap_anchor,
        "E",
        "S",
        (
            "One uninterrupted photorealistic live-action 5.125-second action shot between exact approved E and owner-approved S. "
            "The cast remains exactly two bodies: SSJ2 Gohan and one completely tailless Perfect Cell with two broad flat back wings. "
            "Cell instantly releases one compact blue-white sphere. Gohan steps diagonally across its path and performs one sharp sweeping open-palm slap across the sphere's outer edge. "
            "Contact lasts one beat: the sphere immediately bends into the exact bright curved arc already visible above and away from Gohan in approved S. The energy remains completely outside his torso and never becomes a straight sustained beam. "
            "The lateral camera physically crosses foreground rubble during the change of direction; hand, curved energy, debris, cloth, aura and both bodies keep moving independently. "
            "Cell keeps the same tailless body and broad symmetrical flat wings throughout. No tail, no thin rear appendage, no prolonged block, no beam struggle, no energy through Gohan, no second projectile, no duplicated body or limb, no anime, no cel shading, no game render, no plastic CGI, no pause, no freeze and no internal cut."
        ),
        "Cell releases one compact sphere immediately while Gohan crosses diagonally and swings his open palm laterally.",
        "One brief edge contact visibly bends the sphere into a steep curved path above and away from Gohan as the camera trucks through rubble.",
        "The deflected arc is already separating from Gohan in exact approved S while both fighters and all depth planes remain moving.",
    )
    second = base.micro_take(
        main_take,
        "04B",
        "INTERNAL 04B — avanço após o tapa S-F",
        slap_anchor,
        anchor_f,
        "S",
        "F",
        (
            "One uninterrupted photorealistic live-action 5.125-second continuation between exact owner-approved S and approved F. "
            "The deflected curved energy streak immediately exits high to the side while SSJ2 Gohan completes the same slap follow-through, plants once and explodes forward. "
            "One completely tailless Perfect Cell, retaining only two broad flat back wings, recoils and attempts a quick guard. Gohan crosses real ground, breaks the guard with one compact body contact and converts it into the rising heavy strike of exact approved F. "
            "A low side track accelerates into a close orbit; foreground rocks, fighters and distant ruins move at different speeds and overlap changes every second. "
            "No tail, no thin rear appendage, no new projectile after the opening moment, no sustained energy, no repeated punch, no duplicated body or limb, no anime, no cel shading, no game render, no plastic CGI, no slow motion, no pause, no freeze and no internal cut."
        ),
        "The curved streak exits away from both bodies while Gohan finishes the slap and immediately launches forward.",
        "Gohan crosses real distance, Cell raises a quick guard and the camera accelerates from side track into close orbit.",
        "One rising heavy contact sends the still-tailless Cell upward into exact approved F with continuing camera and debris motion.",
    )

    queue["takes"] = [take for take in queue["takes"] if str(take.get("id")) != "04A"]
    queue["takes"].extend([first, second])
    queue["updated_at"] = now
    overnight = queue.setdefault("overnight_generation", {})
    overnight["take04A_v1_rejected"] = rejected
    overnight["take04_replacement_chain"] = ["04A2", "04B"]
    overnight["take04_approved_slap_anchor"] = copy.deepcopy(slap_anchor)
    overnight["take04_anchor_image_generation_used"] = False
    internal = [item for item in list(overnight.get("internal_microsegments") or []) if item != "04A"]
    for item in ("04A2", "04B"):
        if item not in internal:
            internal.append(item)
    overnight["internal_microsegments"] = internal
    production["takes"] = copy.deepcopy(
        [take for take in queue["takes"] if not take.get("internal_microsegment")]
    )
    production["updated_at"] = now
    production["overnight_generation"] = copy.deepcopy(overnight)
    project["updated_at"] = now
    project["overnight_generation"] = copy.deepcopy(overnight)
    write(REJECTION_PATH, rejected)
    write(QUEUE_PATH, queue)
    write(PRODUCTION_PATH, production)
    write(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "rejected_candidate": rejected_path,
        "approved_anchor_restored": str(DEST_ANCHOR),
        "anchor_sha256": APPROVED_ANCHOR_SHA256,
        "source_video_owner_approval_verified": True,
        "replacement_microsegments": ["04A2", "04B"],
        "image_generation_used": False,
        "auto_approved": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
