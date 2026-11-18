"""Register the P02 post-impact end anchor without authorizing another video."""

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
SOURCE = PROJECT / "base_images" / "anchor_p02_postimpact_mechanical_debris_candidate.png"
PROMPT_FILE = PROJECT / "prompts" / "anchor_p02_postimpact_mechanical_debris_candidate.md"
TAKE_ID = "P02"
REQUEST_ID = "3924fa874b034f6c8ad112d6642f3eba"

sys.path.insert(0, str(STUDIO))

from video_projects import _atomic_json_write, register_anchor_candidate, utc_now  # noqa: E402


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_file() or not PROMPT_FILE.is_file():
        raise FileNotFoundError("Imagem final ou prompt da ancora final P02 ausente.")
    queue = read_json(QUEUE_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    latest = (take.get("maestro_director_requests") or [])[-1]
    if (
        str(latest.get("id") or "") != REQUEST_ID
        or str(latest.get("status") or "").upper() not in {"PENDING", "IN_PROGRESS"}
        or str(latest.get("anchor_side") or "").lower() != "end"
    ):
        raise RuntimeError("O pedido ativo nao corresponde a ancora final P02.")
    if str(take.get("maestro_status") or "").upper() != "PLANNED":
        raise RuntimeError("P02 nao esta no estado seguro para registrar a segunda ancora.")
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    if video.get("output_active") or video.get("output_preview"):
        raise RuntimeError("P02 ainda possui um video ativo; registro interrompido.")

    image_hash = digest(SOURCE)
    prompt = PROMPT_FILE.read_text(encoding="utf-8")
    now = utc_now()
    result = register_anchor_candidate(
        PROJECTS,
        PROJECT_ID,
        TAKE_ID,
        request_id=REQUEST_ID,
        image_bytes=SOURCE.read_bytes(),
        original_filename=SOURCE.name,
        metadata={
            "prompt": prompt,
            "model": "OpenAI built-in image generation",
            "negative": (
                "intact Android 16 head, complete face, living anatomy, flesh, blood, gore, "
                "Perfect Cell, Cell boot, leg, spotted carapace, wing, pelvis, back, tail, "
                "pointed tip, curved appendage, stinger, cable, tentacle, snake shape, "
                "second character, pose, static hold, text, logo, watermark, anime, game render"
            ),
            "sourceOutput": str(SOURCE.resolve()),
            "sourceGeneratedAt": now,
            "sourceSha256": image_hash,
            "generator": "OpenAI built-in image generation",
            "workflow": "approved_start_identity_plus_tail_free_motion_reference_to_postimpact_end_anchor",
            "objective": "Fixar o estado irreversivel de cabeca mecanica esmagada e Cell ausente.",
            "requiredObjects": {
                "anchorSide": "end",
                "characters": ["one approved teenage Super Saiyan Gohan launching forward"],
                "mechanicalDebris": [
                    "broken beige ceramic-metal faceplate shards",
                    "bent internal metal frame",
                    "snapped green Android 16 casing plates",
                    "copper wires, circuits and screws",
                    "shallow impact crater and floor crack",
                ],
                "forbidden": [
                    "intact Android 16 head",
                    "recognizable complete face",
                    "Perfect Cell",
                    "Cell tail or appendage",
                    "blood or gore",
                    "static pose",
                ],
            },
        },
    )

    manifest = read_json(MANIFEST_PATH)
    record = manifest.setdefault("p02_post_impact_end_anchor", {})
    record.update({
        "status": "PENDING_HUMAN_APPROVAL_IN_MAESTRO",
        "request_id": REQUEST_ID,
        "anchor_side": "end",
        "source": str(SOURCE.resolve()),
        "prompt_file": str(PROMPT_FILE.resolve()),
        "sha256": image_hash.upper(),
        "width": 1536,
        "height": 864,
        "video_generation_authorized": False,
    })
    manifest["status"] = "V5_P02_END_ANCHOR_PENDING_OWNER_APPROVAL"
    manifest["render_authorized"] = False
    manifest["updated_at"] = utc_now()
    _atomic_json_write(MANIFEST_PATH, manifest)
    print(json.dumps({
        "ok": True,
        "takeId": TAKE_ID,
        "requestId": REQUEST_ID,
        "qcStatus": result.get("qcStatus"),
        "canGenerate": result.get("canGenerate"),
        "endAnchorCandidate": result.get("endAnchorCandidate"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
