"""Register the exact Gohan FHD60 upscale as the sole Maestro review item.

This does not promote a final master.  It replaces the visible 720p review
candidate with its verified FHD60 derivative while preserving the former
manifest and media as rollback.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / PROJECT_ID
PROJECT_MANIFEST = PROJECT / "project_manifest.json"
SOURCE_SHA256 = "ED63AD0A1E974D1D8B3C4DEFFFC44021A6D34BA47EF17DDCCF2727B403E73F2B"
CANDIDATE_SHA256 = "09F5938534D58C2D2648B36CAF93282EF6CC2F2A0335951F1C34BC6265700134"
CANDIDATE = (
    PROJECT
    / "deliveries"
    / "upscale_v5"
    / "GOHAN_SSJ2_ANDROID16_FOLEY_FHD60_V5_review_candidate_1920x1080_60fps_8ab12262fe4b.mp4"
)
SIDECAR = CANDIDATE.with_suffix(".json")
QC_DIR = PROJECT / "qc" / "upscale_fhd60_v5"
REGISTRATION = QC_DIR / "maestro_registration_fhd60_v5.json"


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_sidecar(sidecar: dict) -> None:
    if str(sidecar.get("source_sha256") or "").upper() != SOURCE_SHA256:
        raise RuntimeError("Upscale sidecar points to a different 720p source hash.")
    if str(sidecar.get("candidate_sha256") or "").upper() != CANDIDATE_SHA256:
        raise RuntimeError("Upscale sidecar candidate hash does not match the locked FHD60 artifact.")
    technical = sidecar.get("technical_validation") or {}
    if technical.get("status") != "technical_pass":
        raise RuntimeError(f"Technical validation is not a pass: {technical!r}")
    required_passes = (
        "full_decode",
        "frame_count",
        "fps",
        "geometry",
        "codec_color",
        "audio_stream_copy",
    )
    failures = [key for key in required_passes if technical.get(key) != "pass"]
    if failures:
        raise RuntimeError(f"Technical validation failures: {failures}")
    source_audio = str(sidecar.get("source_audio_packet_sha256") or "").upper()
    candidate_audio = str(sidecar.get("candidate_audio_packet_sha256") or "").upper()
    if not source_audio or source_audio != candidate_audio:
        raise RuntimeError("Audio packet-copy identity gate failed.")
    streams = (sidecar.get("candidate_probe") or {}).get("streams") or []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or (video.get("width"), video.get("height")) != (1920, 1080):
        raise RuntimeError(f"Unexpected FHD geometry: {video!r}")
    if video.get("r_frame_rate") != "60/1" or str(video.get("nb_frames")) != "2482":
        raise RuntimeError(f"Unexpected FHD cadence: {video!r}")
    if not audio or audio.get("codec_name") != "aac" or str(audio.get("sample_rate")) != "48000":
        raise RuntimeError(f"Unexpected preserved audio stream: {audio!r}")


def preserve_manifests() -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    rollback = PROJECT / "archive" / f"before_upscale_fhd60_v5_registration_{stamp}"
    rollback.mkdir(parents=True, exist_ok=False)
    for name in ("project_manifest.json", "production_manifest.json", "take_queue.json"):
        source = PROJECT / name
        if source.is_file():
            shutil.copy2(source, rollback / name)
    atomic_json(
        rollback / "rollback_record.json",
        {
            "created_at": now_local(),
            "operation": "REGISTER_FHD60_V5_REVIEW_CANDIDATE",
            "candidate": str(CANDIDATE),
            "candidate_sha256": CANDIDATE_SHA256,
            "media_deleted": False,
            "rollback_preserved": True,
        },
    )
    return rollback


def maestro_view() -> dict:
    studio = ENGINE.parent.parent / "services" / "studio"
    if str(studio) not in sys.path:
        sys.path.insert(0, str(studio))
    from video_projects import project_view

    return project_view(PROJECT)


def main() -> int:
    if not CANDIDATE.is_file() or not SIDECAR.is_file():
        raise FileNotFoundError("FHD60 candidate or sidecar is missing.")
    actual_hash = sha256(CANDIDATE)
    if actual_hash != CANDIDATE_SHA256:
        raise RuntimeError(f"Candidate SHA-256 drift: {actual_hash}")
    sidecar = load_json(SIDECAR)
    validate_sidecar(sidecar)

    original_bytes = PROJECT_MANIFEST.read_bytes()
    manifest = json.loads(original_bytes.decode("utf-8-sig"))
    previous = manifest.get("final_output")
    previous_sha = str((previous or {}).get("sha256") or "").upper()
    already_registered = previous_sha == CANDIDATE_SHA256
    if not already_registered and previous_sha != SOURCE_SHA256:
        raise RuntimeError(
            "Refusing to replace an unexpected Maestro review item: "
            f"current SHA-256 is {previous_sha or '<missing>'}."
        )

    rollback = None
    if not already_registered:
        rollback = preserve_manifests()
        history = manifest.setdefault("final_output_history", [])
        if not isinstance(history, list):
            history = []
            manifest["final_output_history"] = history
        history.append(
            {
                **previous,
                "superseded_at": now_local(),
                "superseded_reason": "FHD60 upscale derivative registered for owner review",
                "preserved": True,
            }
        )
        del history[:-20]

        relative_candidate = CANDIDATE.relative_to(PROJECT).as_posix()
        relative_sidecar = SIDECAR.relative_to(PROJECT).as_posix()
        previous_file = str((previous or {}).get("file") or "")
        previous_sources = (previous or {}).get("sources") or []
        manifest["final_output"] = {
            "file": relative_candidate,
            "review_file": relative_candidate,
            "display_name": "FILME COMPLETO - FALA DO 16 + FOLEY - FHD 1080P60 - PARA APROVACAO",
            "title": "GOHAN SSJ2 - VIDEO COMPLETO + FALA DO ANDROID 16 + FOLEY - FHD60",
            "duration_seconds": 41.36666666666667,
            "width": 1920,
            "height": 1080,
            "fps": 60,
            "frames": 2482,
            "video_codec": "h264_nvenc_realesrgan_x2_balanced_75_25",
            "audio_codec": "aac_48k_stereo_packet_copy_from_owner_reviewed_720p60_v4",
            "sha256": CANDIDATE_SHA256.lower(),
            "qc_status": "TECHNICAL_AND_ASSISTANT_VISUAL_PASS_PENDING_OWNER_EXACT_FHD60_PLAYBACK",
            "purpose": "single complete FHD60 upscaled review candidate before final promotion",
            "foley_status": "PRESERVED_FROM_720P60_V4_PENDING_OWNER_FHD_LISTENING",
            "human_review_required": True,
            "auto_approval": False,
            "candidate_review_only": True,
            "final_promotion_allowed": False,
            "crossfade_frames": 0,
            "freeze_frames_added": 0,
            "static_hold_frames_added": 0,
            "technical_manifest": relative_sidecar,
            "source_fingerprint": str(sidecar.get("processing_fingerprint") or ""),
            "sources": previous_sources,
            "registered_at": now_local(),
            "human_review": {
                "status": "PENDING_OWNER_EXACT_FHD60_PLAYBACK",
                "required": True,
                "approval_blocked_until_exact_fhd60_playback": True,
            },
            "upscale": {
                "source_file": previous_file,
                "source_sha256": SOURCE_SHA256.lower(),
                "source_owner_instruction": "feito, faça o upscaling",
                "source_approved_for_upscale": True,
                "source_final_master_approval_claimed": False,
                "engine": "RealESRGAN_x2plus",
                "blend": "75% neural + 25% Lanczos",
                "encoder": "NVIDIA NVENC HQ",
                "processing_fingerprint": str(sidecar.get("processing_fingerprint") or ""),
                "audio_packet_sha256": str(sidecar.get("candidate_audio_packet_sha256") or "").lower(),
            },
            "assistant_visual_qc": {
                "status": "PASS_PENDING_OWNER_REVIEW",
                "full_contact_sheet": "qc/upscale_fhd60_v5/full_contact_24.jpg",
                "take05_contact_sheet": "qc/upscale_fhd60_v5/take05_contact_16.jpg",
                "freeze_events_over_0p35s": 0,
                "black_events_over_0p15s": 0,
                "new_upscale_artifacts_detected": False,
            },
            "previous_review_candidate": {
                "file": previous_file,
                "sha256": SOURCE_SHA256.lower(),
                "preserved": True,
            },
        }
        manifest["take_review_candidates"] = []
        catalog = manifest.setdefault("maestro_catalog_policy", {})
        catalog["visible_review_item"] = "final_output_only"
        catalog["take_review_candidates_hidden"] = True
        catalog["media_deleted"] = False
        manifest["status"] = "FULL_FILM_FHD60_V5_PENDING_OWNER_VISUAL_AND_LISTENING_REVIEW"
        manifest["maestro_status"] = "IN_PROGRESS"
        manifest["updated_at"] = now_local()
        atomic_json(PROJECT_MANIFEST, manifest)

    try:
        view = maestro_view()
        final_view = view.get("finalOutput") or {}
        if not final_view.get("ready"):
            raise RuntimeError(f"Maestro did not resolve the FHD60 candidate: {final_view!r}")
        if str(final_view.get("masterFile") or "") != CANDIDATE.name:
            raise RuntimeError(f"Maestro resolved another artifact: {final_view!r}")
        if str(final_view.get("sha256") or "").upper() != CANDIDATE_SHA256:
            raise RuntimeError(f"Maestro exposed a different candidate hash: {final_view!r}")
    except Exception:
        if not already_registered:
            temporary = PROJECT_MANIFEST.with_name(f".{PROJECT_MANIFEST.name}.restore.tmp")
            temporary.write_bytes(original_bytes)
            os.replace(temporary, PROJECT_MANIFEST)
        raise

    record = {
        "ok": True,
        "registered_at": now_local(),
        "project_id": PROJECT_ID,
        "candidate": str(CANDIDATE),
        "candidate_sha256": CANDIDATE_SHA256,
        "source_sha256": SOURCE_SHA256,
        "already_registered": already_registered,
        "rollback": str(rollback) if rollback else None,
        "maestro_final_output": final_view,
        "owner_review": "PENDING_EXACT_FHD60_PLAYBACK",
        "candidate_review_only": True,
        "final_promotion_allowed": False,
        "previous_720p_candidate_preserved": True,
    }
    atomic_json(REGISTRATION, record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
