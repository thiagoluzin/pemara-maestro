#!/usr/bin/env python3
"""Renderiza o minuto completo em Full HD 60 sem criar um master 4K.

Cada microtake bruto e processado isoladamente: extracao sem perdas, RIFE 2x,
AnimeVideo-v3 4x e reducao Lanczos para um mezzanine Full HD lossless. Somente
depois os takes sao montados e codificados uma unica vez para entrega.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
BIN_ROOT = ENGINE_ROOT / "tools" / "bin"
REALESRGAN_ROOT = BIN_ROOT / "realesrgan-ncnn-vulkan-20220424-windows"
RIFE_ROOT = BIN_ROOT / "rife-ncnn-vulkan-20221029-windows" / "rife-ncnn-vulkan-20221029-windows"
REALESRGAN_EXE = REALESRGAN_ROOT / "realesrgan-ncnn-vulkan.exe"
RIFE_EXE = RIFE_ROOT / "rife-ncnn-vulkan.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="Pasta que contem production_manifest.json.")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(r"D:\PemaraVideoWork\ritmos_raw_rebuild_test"),
        help="Intermediarios retomaveis; os seis takes aprovados podem ser reaproveitados.",
    )
    parser.add_argument("--output-dir", type=Path, help="Padrao: <project>/output.")
    parser.add_argument("--name", default="ritmos_manus_method_60s_FHD60")
    parser.add_argument("--takes", nargs="*", default=[], help="IDs dos takes a renderizar; vazio usa todos.")
    parser.add_argument("--target-duration", type=float, help="Duracao exata da entrega; padrao do manifesto.")
    parser.add_argument("--transition", type=float, default=None)
    parser.add_argument("--contrast", type=float, default=1.03)
    parser.add_argument("--saturation", type=float, default=1.07)
    parser.add_argument("--crf", type=int, default=10)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--force-encode", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} nao encontrado: {path}")


def resolve_program(name: str) -> str:
    program = shutil.which(name)
    if not program:
        raise FileNotFoundError(f"Executavel obrigatorio ausente no PATH: {name}")
    return program


def probe(ffprobe: str, path: Path, count_frames: bool = False) -> dict:
    command = [ffprobe, "-v", "error"]
    if count_frames:
        command.append("-count_frames")
    command += ["-show_streams", "-show_format", "-of", "json", str(path)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def video_stream(data: dict) -> dict:
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    raise RuntimeError("Arquivo sem stream de video.")


def frame_count(directory: Path) -> int:
    return sum(1 for item in directory.glob("*.png") if item.is_file())


def stage_ready(directory: Path, expected: int, signature: dict) -> bool:
    marker = directory.parent / f".{directory.name}.stage.json"
    (directory / ".stage.json").unlink(missing_ok=True)
    directory.mkdir(parents=True, exist_ok=True)
    saved = None
    if marker.is_file():
        try:
            saved = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    current = frame_count(directory)
    if current == expected and saved == signature:
        print(f"[retomar] {directory.parent.name}/{directory.name}: {current} quadros", flush=True)
        return True
    if current or marker.exists():
        print(f"[invalidar] {directory.parent.name}/{directory.name}: {current}/{expected}", flush=True)
    for item in directory.glob("*.png"):
        item.unlink()
    marker.unlink(missing_ok=True)
    return False


def mark_stage(directory: Path, signature: dict) -> None:
    marker = directory.parent / f".{directory.name}.stage.json"
    marker.write_text(json.dumps(signature, ensure_ascii=False, indent=2), encoding="utf-8")


def file_stage_ready(path: Path, signature: dict, ffprobe: str, expected_frames: int) -> bool:
    marker = path.with_suffix(path.suffix + ".stage.json")
    saved = None
    if marker.is_file():
        try:
            saved = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    if path.is_file() and saved == signature:
        try:
            stream = video_stream(probe(ffprobe, path, count_frames=True))
            frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
            fps = float(Fraction(stream["avg_frame_rate"]))
            if frames == expected_frames and abs(fps - 60.0) < 0.01:
                print(f"[retomar] {path.parent.name}/{path.name}: {frames} quadros lossless", flush=True)
                return True
        except Exception:
            pass
    path.unlink(missing_ok=True)
    marker.unlink(missing_ok=True)
    return False


def mark_file_stage(path: Path, signature: dict) -> None:
    path.with_suffix(path.suffix + ".stage.json").write_text(
        json.dumps(signature, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run(command: list[str], log, cwd: Path | None = None) -> None:
    printable = subprocess.list2cmdline(command)
    log.write(f"\n$ {printable}\n")
    log.flush()
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode:
        raise subprocess.CalledProcessError(completed.returncode, command)


def resolve_source(project: Path, spec: dict) -> Path:
    if spec.get("existing_video"):
        return (project / spec["existing_video"]).resolve()
    expected = project / "microtakes" / (
        f"{spec['id']}_wan22_seed{spec['seed']}_768x432_30fps.mp4"
    )
    return expected.resolve()


def validate_source(ffprobe: str, source: Path, expected_frames: int) -> dict:
    require_file(source, "Microtake")
    data = probe(ffprobe, source, count_frames=True)
    stream = video_stream(data)
    width = int(stream["width"])
    height = int(stream["height"])
    fps = float(Fraction(stream["avg_frame_rate"]))
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    if (width, height) != (768, 432) or abs(fps - 30.0) > 0.01 or frames != expected_frames:
        raise RuntimeError(
            f"Microtake invalido {source.name}: {width}x{height}, {fps:.4f} FPS, "
            f"{frames}/{expected_frames} quadros."
        )
    return {"width": width, "height": height, "fps": fps, "frames": frames}


def assembly_filter(durations: list[float], transition: float, target_duration: float) -> str:
    filters: list[str] = []
    for index in range(len(durations)):
        filters.append(f"[{index}:v]fps=60,settb=AVTB,setpts=PTS-STARTPTS[v{index}]")
    previous = "v0"
    offset = durations[0] - transition
    for index in range(1, len(durations)):
        output = f"x{index}"
        filters.append(
            f"[{previous}][v{index}]xfade=transition=fade:duration={transition:.6f}:"
            f"offset={offset:.6f}[{output}]"
        )
        previous = output
        offset += durations[index] - transition
    filters.append(
        f"[{previous}]tpad=stop_mode=clone:stop_duration=0.100000,fps=60,"
        f"trim=duration={target_duration:.6f},setpts=PTS-STARTPTS,"
        "setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709[outv]"
    )
    return ";".join(filters)


def validate_output(ffprobe: str, path: Path, expected_frames: int, expected_duration: float) -> dict:
    require_file(path, "Master Full HD 60")
    data = probe(ffprobe, path, count_frames=True)
    stream = video_stream(data)
    width = int(stream["width"])
    height = int(stream["height"])
    fps = float(Fraction(stream["avg_frame_rate"]))
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    duration = float(data["format"]["duration"])
    if (width, height) != (1920, 1080):
        raise RuntimeError(f"Resolucao final inesperada: {width}x{height}")
    if abs(fps - 60.0) > 0.01 or frames != expected_frames:
        raise RuntimeError(f"Cadencia final inesperada: {fps} FPS, {frames}/{expected_frames} quadros")
    if abs(duration - expected_duration) > 0.02:
        raise RuntimeError(f"Duracao final inesperada: {duration:.6f}s")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    project = args.project.resolve()
    manifest_path = project / "production_manifest.json"
    require_file(manifest_path, "Manifesto")
    require_file(REALESRGAN_EXE, "Real-ESRGAN ncnn Vulkan")
    require_file(RIFE_EXE, "RIFE ncnn Vulkan")
    ffmpeg = resolve_program("ffmpeg")
    ffprobe = resolve_program("ffprobe")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    generation = manifest["generation"]
    transition = float(args.transition if args.transition is not None else generation["transition_seconds"])
    target_duration = float(args.target_duration or manifest["duration_target_seconds"])
    if target_duration <= 0:
        raise RuntimeError("Duracao-alvo precisa ser positiva.")
    expected_final_frames = round(target_duration * 60)
    specs = manifest.get("microtakes") or manifest.get("takes") or []
    selected = {item.upper() for item in args.takes}
    specs = [spec for spec in specs if not selected or str(spec.get("id", "")).upper() in selected]
    if not specs:
        raise RuntimeError("O manifesto precisa fornecer ao menos um take selecionado.")

    take_specs: list[dict] = []
    for spec in specs:
        source = resolve_source(project, spec)
        expected = int(spec["frames"])
        measured = validate_source(ffprobe, source, expected)
        take_specs.append(
            {
                "id": spec["id"],
                "seed": spec["seed"],
                "source": source,
                "frames30": expected,
                "frames60": expected * 2,
                "duration": expected / 30.0,
                "reverse": bool(spec.get("reverse", False)),
                "measured": measured,
            }
        )
    if len(take_specs) > 1 and (transition <= 0 or transition >= min(item["duration"] for item in take_specs)):
        raise RuntimeError("Duracao de transicao invalida.")

    theoretical = sum(item["duration"] for item in take_specs) - transition * (len(take_specs) - 1)
    output_dir = (args.output_dir or (project / "output")).resolve()
    work_dir = args.work_dir.resolve()
    master = output_dir / f"{args.name}.mp4"
    log_path = output_dir / f"{args.name}.log"
    report_path = output_dir / f"{args.name}_report.json"
    plan = {
        "project": str(project),
        "microtakes": len(take_specs),
        "raw_source": "768x432/30",
        "interpolation": "RIFE v4.6 x2 per take",
        "reconstruction": "Real-ESRGAN AnimeVideo-v3 x4 per take",
        "mezzanine": "1920x1080/60 FFV1 lossless per take",
        "assembly": f"{len(take_specs)} lossless takes, {transition:.3f}s fades",
        "theoretical_duration_seconds": theoretical,
        "delivery": "1920x1080/60 H.264 High, CRF %d" % args.crf,
        "delivery_duration_seconds": target_duration,
        "delivery_frames": expected_final_frames,
        "master": str(master),
        "work_dir": str(work_dir),
        "sources": [str(item["source"]) for item in take_specs],
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        print(f"[dry-run] {len(take_specs)} fonte(s) validada(s); nenhum arquivo de render foi alterado.", flush=True)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    mezzanines: list[Path] = []
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        log.write(f"\n=== render FHD60 {datetime.now().astimezone().isoformat()} ===\n")
        log.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        for index, spec in enumerate(take_specs, start=1):
            print(f"[{index:02d}/{len(take_specs):02d}] {spec['id']}", flush=True)
            root = work_dir / spec["id"]
            raw = root / "01_raw30"
            rife = root / "02_rife60"
            upscaled = root / "03_animev3_x4"
            mezzanine = root / "04_fhd60_lossless.mkv"
            stat = spec["source"].stat()
            source_signature = {
                "source": str(spec["source"]),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "reverse": spec["reverse"],
                "frames": spec["frames30"],
            }
            if not stage_ready(raw, spec["frames30"], source_signature):
                print("  extracao PNG sem perdas", flush=True)
                extract = [ffmpeg, "-hide_banner", "-y", "-i", str(spec["source"]), "-map", "0:v:0"]
                if spec["reverse"]:
                    extract += ["-vf", "reverse"]
                extract += ["-vsync", "0", "-start_number", "0", str(raw / "%08d.png")]
                run(extract, log)
                if frame_count(raw) != spec["frames30"]:
                    raise RuntimeError(f"Extracao incompleta em {spec['id']}")
                mark_stage(raw, source_signature)

            rife_signature = {**source_signature, "stage": "RIFE v4.6", "output_frames": spec["frames60"]}
            if not stage_ready(rife, spec["frames60"], rife_signature):
                print("  RIFE 30 -> 60", flush=True)
                run(
                    [str(RIFE_EXE), "-i", str(raw), "-o", str(rife), "-m", "rife-v4.6", "-n", str(spec["frames60"]), "-g", str(args.gpu), "-j", "2:4:2", "-f", "%08d.png"],
                    log,
                    RIFE_ROOT,
                )
                if frame_count(rife) != spec["frames60"]:
                    raise RuntimeError(f"RIFE incompleto em {spec['id']}")
                mark_stage(rife, rife_signature)

            upscale_signature = {**rife_signature, "stage": "AnimeVideo-v3 x4", "scale": 4}
            if not stage_ready(upscaled, spec["frames60"], upscale_signature):
                print("  reconstrucao AI AnimeVideo-v3 x4", flush=True)
                run(
                    [str(REALESRGAN_EXE), "-i", str(rife), "-o", str(upscaled), "-n", "realesr-animevideov3", "-s", "4", "-g", str(args.gpu), "-j", "2:4:2", "-f", "png"],
                    log,
                    REALESRGAN_ROOT,
                )
                if frame_count(upscaled) != spec["frames60"]:
                    raise RuntimeError(f"Real-ESRGAN incompleto em {spec['id']}")
                mark_stage(upscaled, upscale_signature)

            mezz_signature = {
                **upscale_signature,
                "stage": "FHD60 FFV1 lossless",
                "contrast": args.contrast,
                "saturation": args.saturation,
                "pix_fmt": "yuv420p",
            }
            if not file_stage_ready(mezzanine, mezz_signature, ffprobe, spec["frames60"]):
                print("  mezzanine Full HD lossless", flush=True)
                run(
                    [ffmpeg, "-hide_banner", "-y", "-framerate", "60", "-start_number", "0", "-i", str(upscaled / "%08d.png"), "-vf", f"scale=1920:1080:flags=lanczos,eq=contrast={args.contrast}:saturation={args.saturation},setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709", "-frames:v", str(spec["frames60"]), "-an", "-c:v", "ffv1", "-level", "3", "-coder", "1", "-context", "1", "-g", "1", "-slices", "24", "-slicecrc", "1", "-pix_fmt", "yuv420p", str(mezzanine)],
                    log,
                )
                mark_file_stage(mezzanine, mezz_signature)
            mezzanines.append(mezzanine)

        if master.is_file() and not args.force_encode:
            try:
                validate_output(ffprobe, master, expected_final_frames, target_duration)
                print(f"[retomar] master final ja validado: {master}", flush=True)
            except Exception:
                master.unlink(missing_ok=True)
        if not master.is_file() or args.force_encode:
            print(f"[montagem] {len(take_specs)} take(s) lossless -> master Full HD 60", flush=True)
            inputs: list[str] = []
            for path in mezzanines:
                inputs += ["-i", str(path)]
            filtergraph = assembly_filter([item["duration"] for item in take_specs], transition, target_duration)
            run(
                [ffmpeg, "-hide_banner", "-y", *inputs, "-filter_complex", filtergraph, "-map", "[outv]", "-frames:v", str(expected_final_frames), "-r", "60", "-fps_mode", "cfr", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-profile:v", "high", "-level:v", "4.2", "-pix_fmt", "yuv420p", "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", str(master)],
                log,
            )

    final_probe = validate_output(ffprobe, master, expected_final_frames, target_duration)
    report = {
        **plan,
        "completed_at": datetime.now().astimezone().isoformat(),
        "sha256": sha256(master),
        "size_bytes": master.stat().st_size,
        "probe": final_probe,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[concluido] {master}", flush=True)
    print(f"[relatorio] {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[erro] {exc}", file=sys.stderr, flush=True)
        raise
