from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine")
PROJECT = ENGINE / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
QUEUE = PROJECT / "take_queue.json"
FFMPEG = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ProgramData\chocolatey\bin\ffprobe.exe")
TAKE_ORDER = ["01", "02", "03", "04", "05", "06R1", "07", "08"]
OUTPUT = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v1_720p24.mp4"
MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v1.json"
CONTACT_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v1_contact_32.jpg"
BOUNDARY_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v1_boundaries_21.jpg"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            [
                str(FFPROBE), "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt",
                "-show_entries", "format=duration,size", "-of", "json", str(path),
            ],
            text=True,
            encoding="utf-8",
        )
    )


def main() -> None:
    for binary in (FFMPEG, FFPROBE):
        if not binary.is_file():
            raise FileNotFoundError(binary)
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    takes_by_id = {str(item.get("id")): item for item in queue["takes"] if isinstance(item, dict)}
    sources: list[dict] = []
    for take_id in TAKE_ORDER:
        take = takes_by_id[take_id]
        if str(take.get("maestro_status") or "").upper() != "APPROVED":
            raise ValueError(f"Take {take_id} nao esta aprovado no Maestro")
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        path = Path(str(video.get("output_active") or ""))
        if not path.is_file():
            raise FileNotFoundError(path)
        info = probe(path)
        stream = info["streams"][0]
        frames = int(stream.get("nb_read_frames") or 0)
        duration = float(info["format"]["duration"])
        if (int(stream["width"]), int(stream["height"]), str(stream["r_frame_rate"])) != (1280, 720, "24/1"):
            raise ValueError(f"Take {take_id} fora do contrato 720p24: {stream}")
        if frames not in {240, 243}:
            raise ValueError(f"Take {take_id} tem {frames} quadros; esperado 240 ou 243")
        sources.append(
            {
                "takeId": take_id,
                "name": str(take.get("name") or ""),
                "path": path,
                "frames": frames,
                "duration": duration,
                "sha256": sha256(path),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    filters: list[str] = []
    labels: list[str] = []
    for index, source in enumerate(sources):
        label = f"t{index}"
        # Preserve the entire approved source, including its last transition frame,
        # while normalizing every narrative beat to exactly 240 frames / 10 seconds.
        factor = 10.0 / float(source["duration"])
        filters.append(
            f"[{index}:v]setpts={factor:.12f}*(PTS-STARTPTS),fps=24,"
            f"trim=end_frame=240,setpts=N/(24*TB)[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append("".join(labels) + "concat=n=8:v=1:a=0[vout]")

    command = [str(FFMPEG), "-y"]
    for source in sources:
        command.extend(["-i", str(source["path"])])
    command.extend(
        [
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-an",
            "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
            "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(OUTPUT),
        ]
    )
    subprocess.run(command, check=True)

    output_info = probe(OUTPUT)
    output_stream = output_info["streams"][0]
    output_frames = int(output_stream.get("nb_read_frames") or 0)
    output_duration = float(output_info["format"]["duration"])
    if output_frames != 1920 or abs(output_duration - 80.0) > 0.01:
        raise ValueError(f"Montagem invalida: frames={output_frames}, duration={output_duration}")
    if (int(output_stream["width"]), int(output_stream["height"]), str(output_stream["r_frame_rate"])) != (1280, 720, "24/1"):
        raise ValueError(f"Saida fora do contrato: {output_stream}")

    decode = subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(OUTPUT), "-f", "null", "NUL"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if decode.returncode != 0:
        raise ValueError("Falha de decodificacao: " + decode.stderr[-2000:])

    freeze = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(OUTPUT), "-vf", "freezedetect=n=0.003:d=0.4", "-an", "-f", "null", "NUL"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    freeze_events = [line.strip() for line in freeze.stderr.splitlines() if "freeze_" in line]

    subprocess.run(
        [
            str(FFMPEG), "-y", "-i", str(OUTPUT), "-vf",
            "fps=0.4,scale=240:-1,tile=8x4", "-frames:v", "1", str(CONTACT_SHEET),
        ],
        check=True,
    )
    boundary_frames: list[int] = []
    for boundary in range(1, 8):
        center = boundary * 240
        boundary_frames.extend([center - 1, center, center + 1])
    selection = "+".join(f"eq(n\\,{frame})" for frame in boundary_frames)
    # One row per transition: last frame, first frame, next frame.
    boundary_filter = f"select={selection},scale=426:-1,tile=3x7"
    subprocess.run(
        [
            str(FFMPEG), "-y", "-i", str(OUTPUT), "-vf", boundary_filter,
            "-fps_mode", "passthrough", "-frames:v", "1", str(BOUNDARY_SHEET),
        ],
        check=True,
    )

    timeline = []
    for index, source in enumerate(sources):
        timeline.append(
            {
                "takeId": source["takeId"],
                "name": source["name"],
                "startSeconds": index * 10.0,
                "endSeconds": (index + 1) * 10.0,
                "source": str(source["path"]),
                "sourceFrames": source["frames"],
                "sourceDurationSeconds": source["duration"],
                "sourceSha256": source["sha256"],
            }
        )
    manifest = {
        "schemaVersion": "gohan_ssj2_cell_visual_cut_v1",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "PICTURE_LOCK_CANDIDATE_PENDING_OWNER_PLAYBACK",
        "purpose": "visual cut for sequence review before Foley",
        "output": str(OUTPUT),
        "outputSha256": sha256(OUTPUT),
        "encoder": "h264_nvenc",
        "width": 1280,
        "height": 720,
        "fps": 24,
        "frames": output_frames,
        "durationSeconds": output_duration,
        "audio": "none; Foley pending picture-lock approval",
        "transition": "seven hard cuts on approved moving boundaries; no crossfade",
        "freezeEvents": freeze_events,
        "contactSheet": str(CONTACT_SHEET),
        "boundarySheet": str(BOUNDARY_SHEET),
        "timeline": timeline,
        "humanPlaybackRequired": True,
    }
    atomic_json(MANIFEST, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
