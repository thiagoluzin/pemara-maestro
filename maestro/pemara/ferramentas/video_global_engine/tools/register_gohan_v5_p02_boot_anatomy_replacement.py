"""Register the corrected P02 boot-anatomy anchor without approving video."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
ENGINE = BASE / "ferramentas" / "video_global_engine"
PROJECTS = ENGINE / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
SOURCE = PROJECT / "base_images" / "anchor_p02_p01_impact_axis_candidate.png"
PROMPT_FILE = PROJECT / "prompts" / "anchor_p02_p01_impact_axis_candidate.md"
DISCARDED_HUMAN_SHOE = PROJECT / "base_images" / "anchor_p02_cell_boot_sideprofile_candidate.png"
DISCARDED_MISALIGNED = PROJECT / "base_images" / "anchor_p02_cell_bioarmor_boot_sideprofile_candidate.png"
TAKE_ID = "P02"
EXPECTED_REQUEST_ID = "b84f8e2ad53440479de35e248d6e538a"

sys.path.insert(0, str(STUDIO))

from video_projects import _atomic_json_write, register_anchor_candidate, utc_now  # noqa: E402


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_file() or not PROMPT_FILE.is_file():
        raise FileNotFoundError("Imagem normalizada ou prompt P02 ausente.")

    queue = read_json(QUEUE_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    requests = take.get("maestro_director_requests") or []
    latest = requests[-1] if requests else {}
    request_id = str(latest.get("id") or "")
    request_status = str(latest.get("status") or "").upper()
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}

    if request_id != EXPECTED_REQUEST_ID or request_status not in {"PENDING", "IN_PROGRESS"}:
        raise RuntimeError("O pedido P02 ativo nao corresponde a rejeicao recem-registrada.")
    if video.get("output_active"):
        raise RuntimeError("P02 ja possui video ativo; registro de ancora interrompido.")
    if base.get("candidate_request_id"):
        raise RuntimeError("P02 ja possui outro candidato ativo.")

    image_hash = sha256(SOURCE)
    prompt = PROMPT_FILE.read_text(encoding="utf-8")
    now = utc_now()
    result = register_anchor_candidate(
        PROJECTS,
        PROJECT_ID,
        TAKE_ID,
        request_id=request_id,
        image_bytes=SOURCE.read_bytes(),
        original_filename=SOURCE.name,
        metadata={
            "prompt": prompt,
            "model": "OpenAI built-in image generation",
            "negative": (
                "new composition, side-profile boot, boot missing the head, boot beside the head, "
                "altered impact axis, human shoe, sneaker, leather, laces, hand-foot fusion, fingers, toes, claws, "
                "knuckles, palm texture, fleshy digits, "
                "duplicated legs, extra feet, malformed limbs, face-on sole, giant oval sole, "
                "tail, stinger, cable, tentacle, rear appendage, visible pelvis, hips, back, "
                "wing roots, contact, blood, gore, tear, liquid, anime, game render, text"
            ),
            "sourceOutput": str(SOURCE.resolve()),
            "sourceGeneratedAt": now,
            "sourceSha256": image_hash,
            "generator": "OpenAI built-in image generation",
            "workflow": "identity_preserving_reframe_then_exact_1536x864_normalization",
            "objective": (
                "Preservar da P01 o eixo exato da pisada sobre a cabeca do Android 16, "
                "sem reabrir a anatomia traseira de Cell."
            ),
            "requiredObjects": {
                "anchorSide": "start",
                "characters": [
                    "one ordinary Super Saiyan teenage Gohan running",
                    "one Android 16 intact mechanical head",
                    "one cropped Cell lower leg and the P01 bio-armored boot aligned over Android 16",
                ],
                "bootAnatomy": [
                    "continuous lower shin",
                    "rigid ankle joint",
                    "curved heel",
                    "closed rounded toe box",
                    "single flat treaded outsole",
                    "P01 near-frontal underside angle",
                    "air gap before impact",
                    "boot striking center aligned with Android 16 crown and forehead",
                ],
                "excludedFromFrame": [
                    "Cell knee",
                    "Cell pelvis",
                    "Cell hips",
                    "Cell torso",
                    "Cell back",
                    "Cell wings",
                    "Cell rear silhouette",
                    "Cell wing roots",
                ],
                "forbidden": [
                    "side-profile boot",
                    "boot missing the head",
                    "boot beside the head",
                    "altered impact axis",
                    "human shoe",
                    "sneaker",
                    "leather",
                    "laces",
                    "hand-foot fusion",
                    "fingers",
                    "toes",
                    "claws",
                    "tail",
                    "stinger",
                    "tentacle",
                    "cable",
                    "contact",
                    "gore",
                ],
            },
        },
    )

    manifest = read_json(MANIFEST_PATH)
    batches = manifest.setdefault("anchor_candidate_batches", {})
    batches["v5_p02_reframed"] = {
        "status": "PENDING_HUMAN_APPROVAL_IN_MAESTRO",
        "take_id": TAKE_ID,
        "request_id": request_id,
        "source": str(SOURCE.resolve()),
        "prompt_file": str(PROMPT_FILE.resolve()),
        "sha256": image_hash.upper(),
        "width": 1536,
        "height": 864,
        "video_generation_authorized": False,
        "replacement_reason": (
            "The latest registered predecessor moved the boot outside Android 16's head. "
            "This replacement restores P01's boot-to-head impact axis without a new angle."
        ),
        "rejected_predecessor_request_id": "e1de5d8e38544e1a9b6979360ebb57fb",
        "rejected_predecessor_preserved": True,
        "rejected_registered_request_ids": [
            "2119e9394c5e45f8a88a7c9e12409f76",
            "e1de5d8e38544e1a9b6979360ebb57fb",
        ],
        "rejected_unregistered_candidate": {
            "file": str(DISCARDED_HUMAN_SHOE.resolve()),
            "sha256": sha256(DISCARDED_HUMAN_SHOE).upper() if DISCARDED_HUMAN_SHOE.is_file() else "",
            "reason": "Departed from P01 and redesigned Cell's integrated bio-armor as a human shoe.",
            "preserved": DISCARDED_HUMAN_SHOE.is_file(),
        },
        "rejected_misaligned_candidate": {
            "file": str(DISCARDED_MISALIGNED.resolve()),
            "sha256": sha256(DISCARDED_MISALIGNED).upper() if DISCARDED_MISALIGNED.is_file() else "",
            "reason": "Boot was displaced outside Android 16's head instead of following P01's impact axis.",
            "preserved": DISCARDED_MISALIGNED.is_file(),
        },
    }
    manifest["status"] = "V5_P02_BOOT_ANATOMY_ANCHOR_PENDING_OWNER_APPROVAL"
    manifest["render_authorized"] = False
    manifest["updated_at"] = utc_now()
    _atomic_json_write(MANIFEST_PATH, manifest)

    print(json.dumps({
        "ok": True,
        "takeId": TAKE_ID,
        "requestId": request_id,
        "status": result.get("status"),
        "qcStatus": result.get("qcStatus"),
        "canGenerate": result.get("canGenerate"),
        "anchorCandidate": result.get("anchorCandidate"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
