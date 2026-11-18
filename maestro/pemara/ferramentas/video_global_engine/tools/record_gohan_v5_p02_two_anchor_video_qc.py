"""Record internal visual QC for the generated P02 candidate without granting owner approval."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE_PATH = PROJECT / "take_queue.json"
MANIFEST_PATH = PROJECT / "project_manifest.json"
PILOT_PATH = PROJECT / "work" / "v5_p02_impact_axis" / "production_manifest_v5_p02_impact_axis.json"
VIDEO = PROJECT / "takes" / "maestro_generated" / "take_P02_0efeb200cef748e4_minimax_h3_preview.mp4"
CONTACT = PROJECT / "qc" / "p02_two_anchor_0efeb200" / "contact_2fps.png"
EXPECTED_SHA = "36d87f72d283c37cff5d3d31279cc41c7ec8e90372606fcd11c31061af977836"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def gate() -> dict:
    return {
        "status": "approved",
        "evident_camera": True,
        "real_depth": True,
        "internal_action": True,
        "clear_progression": True,
        "continuous_action": True,
        "motion_across_all_intervals": True,
        "moving_anchor_context": True,
        "no_crossfade": True,
        "no_freeze": True,
        "no_static_tail": True,
        "no_reset": True,
        "evidence": (
            "Full decode and 2 fps visual contact sheet verified. The aligned boot makes visible contact; "
            "the faceplate fractures into mechanical debris; the boot/leg leaves without tail anatomy; "
            "Gohan advances through changing scale and perspective while dust, stones, debris, aura and "
            "electricity remain active through the final frame. No crossfade, reset, freeze or static tail. "
            f"Candidate SHA256={EXPECTED_SHA}; contact={CONTACT.as_posix()}"
        ),
    }


def update_take(take: dict, require_active_match: bool = True) -> None:
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    if require_active_match and Path(str(video.get("output_active", ""))).resolve() != VIDEO.resolve():
        raise RuntimeError("O video ativo nao corresponde ao candidato inspecionado.")
    if not require_active_match:
        video.update({
            "status": "ready",
            "output_active": str(VIDEO),
            "output_preview": str(VIDEO),
            "output_review_candidate": str(VIDEO),
        })
        take["video"] = video
    take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take["maestro_status"] = "NEEDS_REVIEW"
    take["render_authorized"] = False
    take.setdefault("video_generation", {})["render_authorized"] = False
    take.setdefault("qc", {})["status"] = "internal_visual_qc_pass_pending_owner_review"
    take["qc"]["human_visual_approval"] = "pending_video_review"
    take["qc"]["transition_motion_gate"] = gate()
    take["qc"]["candidate"] = {
        "file": VIDEO.as_posix(),
        "sha256": EXPECTED_SHA,
        "job_id": "0efeb200cef748e492fcfc7af556ad86",
        "seed": 2026082022,
        "width": 1280,
        "height": 720,
        "fps": 24,
        "frames": 124,
        "duration_seconds": 5.166667,
        "contact_sheet": CONTACT.as_posix(),
        "status": "PENDING_OWNER_REVIEW",
    }


def main() -> None:
    if not VIDEO.is_file() or not CONTACT.is_file():
        raise FileNotFoundError("Video ou contact sheet de QC ausente.")
    if hashlib.sha256(VIDEO.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("SHA256 do candidato mudou depois do QC.")
    queue = read_json(QUEUE_PATH)
    manifest = read_json(MANIFEST_PATH)
    pilot = read_json(PILOT_PATH)
    queue_take = next(item for item in queue["takes"] if str(item.get("id")) == "P02")
    pilot_take = next(item for item in pilot["takes"] if str(item.get("id")) == "P02")
    update_take(queue_take)
    update_take(pilot_take, require_active_match=False)
    queue["status"] = "V5_P02_VIDEO_PENDING_OWNER_REVIEW"
    queue["render_authorized"] = False
    manifest["status"] = "V5_P02_VIDEO_PENDING_OWNER_REVIEW"
    manifest["maestro_status"] = "NEEDS_REVIEW"
    manifest["render_authorized"] = False
    manifest.setdefault("directed_correction_v5_p02_impact_axis", {})["candidate_qc"] = {
        "status": "INTERNAL_PASS_PENDING_OWNER_REVIEW",
        "file": VIDEO.as_posix(),
        "sha256": EXPECTED_SHA,
        "contact_sheet": CONTACT.as_posix(),
    }
    pilot["status"] = "INTERNAL_QC_PASS_PENDING_OWNER_REVIEW"
    pilot["render_authorized"] = False
    atomic_json(QUEUE_PATH, queue)
    atomic_json(MANIFEST_PATH, manifest)
    atomic_json(PILOT_PATH, pilot)
    print(json.dumps({"ok": True, "takeId": "P02", "status": queue_take["status"],
                      "sha256": EXPECTED_SHA.upper(), "humanApproval": "pending"}, indent=2))


if __name__ == "__main__":
    main()
