from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
CHILD = ENGINE / "projetos" / "gohan_ssj2_take06_magic_slap_multi_anchor_v1"
PARENT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")
SLAP = CHILD / "takes" / "maestro_generated" / "take_06A2_2a73f882f4f44c04_minimax_h3_preview.mp4"
COMBAT = PARENT / "takes" / "maestro_generated" / "take_06R1_ae9107199e5c4433_minimax_h3_preview.mp4"
OUTPUT = PARENT / "takes" / "maestro_generated" / "take_06R1_magic_slap_corrected_v2.mp4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            [str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames", "-show_entries", "format=duration,size", "-of", "json", str(path)],
            text=True,
            encoding="utf-8",
        )
    )


def main() -> None:
    for path in (SLAP, COMBAT, FFMPEG, FFPROBE):
        if not path.is_file():
            raise FileNotFoundError(path)
    # 74 frames: corrected projectile and palm deflection, all before the 3.208 s freeze.
    # 166 frames: resume the already-valid original after its bad projectile interval.
    slap_source = 3.0
    slap_target = 74 / 24
    combat_start = 3.333333
    combat_end = 10.125
    combat_source = combat_end - combat_start
    combat_target = 166 / 24
    filters = (
        f"[0:v]trim=start=0:end={slap_source:.6f},setpts={slap_target/slap_source:.12f}*(PTS-STARTPTS),fps=24,trim=end_frame=74,setpts=N/(24*TB)[a];"
        f"[1:v]trim=start={combat_start:.6f}:end={combat_end:.6f},setpts={combat_target/combat_source:.12f}*(PTS-STARTPTS),fps=24,trim=end_frame=166,setpts=N/(24*TB)[b];"
        "[a][b]concat=n=2:v=1:a=0[vout]"
    )
    edit_dir = CHILD / "edit"
    edit_dir.mkdir(parents=True, exist_ok=True)
    candidate = edit_dir / "take06_magic_slap_corrected_v2.mp4"
    subprocess.run(
        [str(FFMPEG), "-y", "-i", str(SLAP), "-i", str(COMBAT), "-filter_complex", filters, "-map", "[vout]", "-an", "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(candidate)],
        check=True,
    )
    info = probe(candidate)
    stream = info["streams"][0]
    frames = int(stream.get("nb_read_frames") or 0)
    duration = float(info["format"]["duration"])
    if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
        raise ValueError(f"Formato inesperado: {stream}")
    if frames != 240 or abs(duration - 10.0) > 0.01:
        raise ValueError(f"Montagem invalida: frames={frames}, duration={duration}")
    shutil.copy2(candidate, OUTPUT)
    if sha256(candidate) != sha256(OUTPUT):
        raise ValueError("Hash divergiu na copia ao projeto principal.")

    queue_path = PARENT / "take_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    take = next(item for item in queue["takes"] if str(item.get("id")) == "06R1")
    now = datetime.now(timezone.utc).isoformat()
    video = take.setdefault("video", {})
    previous = str(video.get("output_active") or "")
    if previous and previous != str(OUTPUT):
        video.setdefault("output_history", []).append({"path": previous, "role": "output_active", "replaced_at": now, "replaced_by": "magic_slap_corrected_v2"})
    video.update({"status": "ready", "output_active": str(OUTPUT), "output_preview": str(OUTPUT), "output_review_candidate": str(OUTPUT)})
    take["status"] = "VIDEO_PENDING_HUMAN_REVIEW"
    take["maestro_status"] = "READY"
    take["render_authorized"] = False
    take["maestro_last_job_id"] = "take06_magic_slap_corrected_v2"
    take["maestro_last_error"] = ""
    take["maestro_updated_at"] = now
    take["maestro_notes"] = (
        "V2 corrige o atravessamento: usa somente 0-3,000 s do 06A2, onde Gohan desvia o projetil com a palma, "
        "e retoma em 3,333 s do 06R1 original, depois da magia, preservando o combate e o lançamento sem cauda nova. "
        "Dois cortes em movimento, sem crossfade; candidatos anteriores preservados. Pendente revisao humana."
    )
    qc = take.setdefault("qc", {})
    qc["status"] = "video_pending_human_review"
    qc["human_visual_approval"] = "pending"
    qc["transition_motion_gate"] = {"status": "pending_human_review", "method": "corrected_slap_plus_valid_post_projectile_combat_hard_cut", "frames": frames, "duration_seconds": duration, "crossfade_frames": 0, "freeze_frames": 0}
    atomic_json(queue_path, queue)
    manifest = {"schemaVersion": "gohan_take06_magic_slap_corrected_v2", "createdAt": now, "candidate": str(candidate), "candidateSha256": sha256(candidate), "registeredParentCandidate": str(OUTPUT), "frames": frames, "fps": 24, "durationSeconds": duration, "transition": "hard_cut_after_deflected_projectile", "sources": [{"path": str(SLAP), "sha256": sha256(SLAP), "interval": [0.0, slap_source], "frames": 74}, {"path": str(COMBAT), "sha256": sha256(COMBAT), "interval": [combat_start, combat_end], "frames": 166}], "humanVisualReviewRequired": True}
    atomic_json(edit_dir / "take06_magic_slap_corrected_v2.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
