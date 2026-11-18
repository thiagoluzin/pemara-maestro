#!/usr/bin/env python3
"""Cria masters 4K60/FHD60 preservando as fontes.

Aceita um vídeo montado ou os microtakes brutos. No modo microtakes, cada take
é interpolado e reconstruído isoladamente; as transições acontecem só depois.
"""

from __future__ import annotations

import argparse
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
    parser.add_argument("input", type=Path, help="Vídeo de entrada (não é modificado).")
    parser.add_argument("output_dir", type=Path, help="Pasta dos masters finais.")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(r"D:\PemaraVideoWork\max_quality"),
        help="Pasta retomável para PNGs intermediários.",
    )
    parser.add_argument("--name", default=None, help="Nome-base dos arquivos finais.")
    parser.add_argument("--dry-run", action="store_true", help="Valida e mostra o plano sem executar.")
    parser.add_argument("--gpu", type=int, default=0, help="Índice Vulkan da GPU.")
    parser.add_argument(
        "--microtakes-dir",
        type=Path,
        help="Usa os MP4 brutos desta pasta, em ordem alfabética, em vez do vídeo montado.",
    )
    parser.add_argument(
        "--reverse-takes",
        nargs="*",
        default=[],
        help="IDs de microtakes que devem ser invertidos antes do RIFE (ex.: 01F).",
    )
    parser.add_argument("--transition", type=float, default=0.12, help="Duração do fade entre microtakes.")
    parser.add_argument("--contrast", type=float, default=1.03, help="Contraste uniforme da montagem.")
    parser.add_argument("--saturation", type=float, default=1.07, help="Saturação uniforme da montagem.")
    parser.add_argument(
        "--microtakes",
        nargs="+",
        type=Path,
        help="Lista explicita e ordenada de microtakes brutos.",
    )
    parser.add_argument("--sharpness", type=float, default=0.18, help="Nitidez final leve; zero desativa.")
    parser.add_argument("--target-fps", type=int, default=60, help="FPS de entrega dos microtakes.")
    parser.add_argument("--rife-model", default="rife-v4.6", help="Modelo local do RIFE ncnn.")
    parser.add_argument("--upscale-scale", type=int, choices=(2, 3, 4), default=3, help="Escala do AnimeVideo-v3.")
    parser.add_argument("--fhd-only", action="store_true", help="Gera apenas a entrega Full HD.")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} não encontrado: {path}")


def resolve_program(name: str) -> str:
    result = shutil.which(name)
    if not result:
        raise FileNotFoundError(f"Executável obrigatório não encontrado no PATH: {name}")
    return result


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
    raise RuntimeError("O arquivo não contém stream de vídeo.")


def frame_count(directory: Path) -> int:
    return sum(1 for item in directory.glob("*.png") if item.is_file())


def reset_partial_frames(directory: Path, expected: int) -> bool:
    """Retorna True quando a etapa já está completa; remove apenas PNGs parciais."""
    directory.mkdir(parents=True, exist_ok=True)
    current = frame_count(directory)
    if current == expected:
        print(f"[retomar] {directory.name}: {current} quadros completos", flush=True)
        return True
    if current:
        print(f"[retomar] removendo etapa parcial {directory.name}: {current}/{expected}", flush=True)
        for item in directory.glob("*.png"):
            if item.is_file():
                item.unlink()
    return False


def stage_ready(directory: Path, expected: int, signature: dict) -> bool:
    """Valida contagem e assinatura; nunca reaproveita intermediário incompatível."""
    # Os executáveis ncnn varrem todos os arquivos da pasta de imagens. O
    # marcador precisa ficar ao lado dela, ou pode ser interpretado como frame.
    marker = directory.parent / f".{directory.name}.stage.json"
    legacy_marker = directory / ".stage.json"
    legacy_marker.unlink(missing_ok=True)
    directory.mkdir(parents=True, exist_ok=True)
    current = frame_count(directory)
    saved = None
    if marker.is_file():
        try:
            saved = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            saved = None
    if current == expected and saved == signature:
        print(f"[retomar] {directory.parent.name}/{directory.name}: {current} quadros", flush=True)
        return True
    if current or marker.exists():
        print(f"[retomar] invalidando {directory.parent.name}/{directory.name}: {current}/{expected}", flush=True)
    for item in directory.glob("*.png"):
        if item.is_file():
            item.unlink()
    marker.unlink(missing_ok=True)
    return False


def mark_stage(directory: Path, signature: dict) -> None:
    (directory.parent / f".{directory.name}.stage.json").write_text(
        json.dumps(signature, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run(command: list[str], log, cwd: Path | None = None) -> None:
    printable = subprocess.list2cmdline(command)
    print(f"[executar] {printable}", flush=True)
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


def validate_output(ffprobe: str, path: Path, width: int, height: int, fps: int, duration: float) -> dict:
    require_file(path, "Master")
    data = probe(ffprobe, path, count_frames=True)
    stream = video_stream(data)
    actual_fps = float(Fraction(stream["avg_frame_rate"]))
    actual_duration = float(data["format"]["duration"])
    if int(stream["width"]) != width or int(stream["height"]) != height:
        raise RuntimeError(f"Resolução inesperada em {path.name}: {stream['width']}x{stream['height']}")
    if abs(actual_fps - fps) > 0.01:
        raise RuntimeError(f"FPS inesperado em {path.name}: {actual_fps}")
    if abs(actual_duration - duration) > 0.05:
        raise RuntimeError(f"Duração inesperada em {path.name}: {actual_duration:.3f}s")
    return data


def microtake_filter(
    take_durations: list[float],
    transition: float,
    width: int,
    height: int,
    contrast: float,
    saturation: float,
    sharpness: float,
) -> str:
    filters = []
    for index in range(len(take_durations)):
        filters.append(
            f"[{index}:v]scale={width}:{height}:flags=lanczos,"
            f"eq=contrast={contrast}:saturation={saturation},"
            f"settb=AVTB,setpts=PTS-STARTPTS[v{index}]"
        )
    if len(take_durations) == 1:
        previous = "v0"
    elif transition == 0:
        concat_inputs = "".join(f"[v{index}]" for index in range(len(take_durations)))
        filters.append(f"{concat_inputs}concat=n={len(take_durations)}:v=1:a=0[xcat]")
        previous = "xcat"
    else:
        previous = "v0"
        offset = take_durations[0] - transition
        for index in range(1, len(take_durations)):
            output = f"x{index}"
            filters.append(
                f"[{previous}][v{index}]xfade=transition=fade:duration={transition:.6f}:"
                f"offset={offset:.6f}[{output}]"
            )
            previous = output
            offset += take_durations[index] - transition
    unsharp = f"unsharp=5:5:{sharpness}:5:5:0," if sharpness > 0 else ""
    filters.append(
        f"[{previous}]{unsharp}setparams=range=limited:color_primaries=bt709:"
        "color_trc=bt709:colorspace=bt709[outv]"
    )
    return ";".join(filters)


def run_microtake_mode(args: argparse.Namespace, ffmpeg: str, ffprobe: str) -> int:
    if args.microtakes:
        sources = [item.resolve() for item in args.microtakes]
        for source in sources:
            require_file(source, "Microtake")
        microtakes_dir = None
    else:
        microtakes_dir = args.microtakes_dir.resolve()
    if not args.microtakes and not microtakes_dir.is_dir():
        raise FileNotFoundError(f"Pasta de microtakes não encontrada: {microtakes_dir}")
    if not args.microtakes:
        sources = sorted(microtakes_dir.glob("*.mp4"))
    if not sources:
        raise RuntimeError("O modo microtakes exige pelo menos um MP4.")
    if args.transition < 0:
        raise RuntimeError("A transição deve ser maior que zero.")

    if args.target_fps <= 0:
        raise RuntimeError("O FPS de entrega deve ser positivo.")

    output_dir = args.output_dir.resolve()
    work_dir = args.work_dir.resolve()
    base_name = args.name or args.input.stem
    reverse_ids = {item.upper() for item in args.reverse_takes}
    take_specs = []
    used_take_ids: set[str] = set()
    for source_index, source in enumerate(sources, start=1):
        data = probe(ffprobe, source, count_frames=True)
        stream = video_stream(data)
        base_take_id = source.stem.split("_")[0].upper()
        take_id = base_take_id
        if take_id in used_take_ids:
            take_id = f"{base_take_id}_{source_index:02d}"
        used_take_ids.add(take_id)
        width = int(stream["width"])
        height = int(stream["height"])
        fps = float(Fraction(stream["avg_frame_rate"]))
        frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
        duration = float(data["format"]["duration"])
        if fps < 24:
            raise RuntimeError(
                f"FPS de origem proibido em {source.name}: {fps}. "
                "O pipeline aceita somente fontes de 24 FPS ou mais."
            )
        if (width, height) != (768, 432) or not frames:
            raise RuntimeError(
                f"Microtake incompatível {source.name}: {width}x{height}, {fps} FPS, {frames} quadros."
            )
        output_frames = round(frames * args.target_fps / fps)
        take_specs.append(
            {
                "id": take_id,
                "source": source,
                "frames": frames,
                "fps": fps,
                "output_frames": output_frames,
                "output_duration": output_frames / args.target_fps,
                "duration": duration,
                "reverse": take_id in reverse_ids or base_take_id in reverse_ids,
            }
        )
    if args.transition >= min(item["duration"] for item in take_specs):
        raise RuntimeError("A transição não pode ser maior ou igual ao menor microtake.")

    durations = [item["output_duration"] for item in take_specs]
    final_duration = sum(durations) - args.transition * (len(take_specs) - 1)
    final_frames = round(final_duration * args.target_fps)
    master_4k = output_dir / f"{base_name}_MAX_4K60_HEVC10.mp4"
    delivery_fhd = output_dir / f"{base_name}_MAX_FHD60.mp4"
    log_path = output_dir / f"{base_name}_max_quality.log"
    report_path = output_dir / f"{base_name}_max_quality_report.json"
    plan = {
        "mode": "raw_microtakes",
        "sources": [
            {
                "id": item["id"],
                "file": str(item["source"]),
                "source_fps": item["fps"],
                "source_frames": item["frames"],
                "delivery_frames": item["output_frames"],
                "duration_seconds": item["duration"],
                "reverse": item["reverse"],
            }
            for item in take_specs
        ],
        "transition": "hard_cut" if args.transition == 0 else "fade",
        "transition_seconds": args.transition,
        "duration_seconds": final_duration,
        "frames": final_frames,
        "target_fps": args.target_fps,
        "interpolator": f"RIFE {args.rife_model} per take, before assembly",
        "upscaler": f"Real-ESRGAN AnimeVideo-v3 x{args.upscale_scale} per take, before assembly",
        "contrast": args.contrast,
        "saturation": args.saturation,
        "sharpness": args.sharpness,
        "master_4k": None if args.fhd_only else str(master_4k),
        "delivery_fhd": str(delivery_fhd),
        "work_dir": str(work_dir),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        print("[dry-run] todos os microtakes foram validados; nenhum arquivo foi alterado.", flush=True)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    upscaled_dirs: list[Path] = []
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        log.write(f"\n=== microtakes {datetime.now().astimezone().isoformat()} ===\n")
        log.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        for index, spec in enumerate(take_specs, start=1):
            take_root = work_dir / spec["id"]
            raw_frames = take_root / "01_raw30"
            rife_frames = take_root / f"02_rife{args.target_fps}"
            upscaled_frames = take_root / f"03_animev3_x{args.upscale_scale}"
            source_stat = spec["source"].stat()
            source_signature = {
                "source": str(spec["source"].resolve()),
                "size": source_stat.st_size,
                "mtime_ns": source_stat.st_mtime_ns,
                "reverse": spec["reverse"],
                "frames": spec["frames"],
            }
            if not stage_ready(raw_frames, spec["frames"], source_signature):
                print(f"[{index}/{len(take_specs)}] {spec['id']}: extraindo bruto", flush=True)
                command = [ffmpeg, "-hide_banner", "-y", "-i", str(spec["source"])]
                if spec["reverse"]:
                    command += ["-vf", "reverse"]
                command += ["-map", "0:v:0", "-vsync", "0", "-start_number", "0", str(raw_frames / "%08d.png")]
                run(command, log)
                if frame_count(raw_frames) != spec["frames"]:
                    raise RuntimeError(f"Extração incompleta em {spec['id']}.")
                mark_stage(raw_frames, source_signature)

            rife_signature = {
                **source_signature,
                "stage": f"RIFE {args.rife_model}",
                "target_fps": args.target_fps,
                "output_frames": spec["output_frames"],
            }
            if not stage_ready(rife_frames, spec["output_frames"], rife_signature):
                print(
                    f"[{index}/{len(take_specs)}] {spec['id']}: RIFE {spec['fps']:g} -> {args.target_fps}",
                    flush=True,
                )
                run(
                    [str(RIFE_EXE), "-i", str(raw_frames), "-o", str(rife_frames), "-m", args.rife_model, "-n", str(spec["output_frames"]), "-g", str(args.gpu), "-j", "2:4:2", "-f", "%08d.png"],
                    log,
                    RIFE_ROOT,
                )
                if frame_count(rife_frames) != spec["output_frames"]:
                    raise RuntimeError(f"RIFE incompleto em {spec['id']}.")
                mark_stage(rife_frames, rife_signature)

            upscale_signature = {
                **rife_signature,
                "stage": f"AnimeVideo-v3 x{args.upscale_scale}",
                "scale": args.upscale_scale,
            }
            if not stage_ready(upscaled_frames, spec["output_frames"], upscale_signature):
                print(
                    f"[{index}/{len(take_specs)}] {spec['id']}: reconstrução AI x{args.upscale_scale}",
                    flush=True,
                )
                run(
                    [str(REALESRGAN_EXE), "-i", str(rife_frames), "-o", str(upscaled_frames), "-n", "realesr-animevideov3", "-s", str(args.upscale_scale), "-g", str(args.gpu), "-j", "2:4:2", "-f", "png"],
                    log,
                    REALESRGAN_ROOT,
                )
                if frame_count(upscaled_frames) != spec["output_frames"]:
                    raise RuntimeError(f"Real-ESRGAN incompleto em {spec['id']}.")
                mark_stage(upscaled_frames, upscale_signature)
            upscaled_dirs.append(upscaled_frames)

        common_inputs: list[str] = []
        for directory in upscaled_dirs:
            common_inputs += ["-framerate", str(args.target_fps), "-start_number", "0", "-i", str(directory / "%08d.png")]

        if not args.fhd_only:
            print(f"[montagem] master 4K{args.target_fps} a partir dos microtakes reconstruídos", flush=True)
        filter_4k = microtake_filter(
            durations, args.transition, 3840, 2160, args.contrast, args.saturation, args.sharpness
        )
        if not args.fhd_only:
            run(
                [ffmpeg, "-hide_banner", "-y", *common_inputs, "-filter_complex", filter_4k, "-map", "[outv]", "-frames:v", str(final_frames), "-an", "-c:v", "libx265", "-preset", "slow", "-crf", "11", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1", "-x265-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-movflags", "+faststart", str(master_4k)],
                log,
            )

        print(f"[montagem] entrega Full HD {args.target_fps} a partir dos microtakes reconstruídos", flush=True)
        filter_fhd = microtake_filter(
            durations, args.transition, 1920, 1080, args.contrast, args.saturation, args.sharpness
        )
        run(
            [ffmpeg, "-hide_banner", "-y", *common_inputs, "-filter_complex", filter_fhd, "-map", "[outv]", "-frames:v", str(final_frames), "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high", "-level:v", "4.2", "-pix_fmt", "yuv420p", "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-movflags", "+faststart", str(delivery_fhd)],
            log,
        )

    report = {
        **plan,
        "completed_at": datetime.now().astimezone().isoformat(),
        "master_4k_probe": None
        if args.fhd_only
        else validate_output(ffprobe, master_4k, 3840, 2160, args.target_fps, final_duration),
        "delivery_fhd_probe": validate_output(
            ffprobe, delivery_fhd, 1920, 1080, args.target_fps, final_duration
        ),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if master_4k.is_file():
        print(f"[concluído] {master_4k}", flush=True)
    print(f"[concluído] {delivery_fhd}", flush=True)
    return 0


def main() -> int:
    args = parse_args()
    source = args.input.resolve()
    output_dir = args.output_dir.resolve()
    base_name = args.name or source.stem
    work_dir = args.work_dir.resolve() / base_name

    require_file(source, "Vídeo de entrada")
    require_file(REALESRGAN_EXE, "Real-ESRGAN ncnn Vulkan")
    require_file(RIFE_EXE, "RIFE ncnn Vulkan")
    ffmpeg = resolve_program("ffmpeg")
    ffprobe = resolve_program("ffprobe")

    if args.microtakes_dir or args.microtakes:
        return run_microtake_mode(args, ffmpeg, ffprobe)

    source_probe = probe(ffprobe, source, count_frames=True)
    source_video = video_stream(source_probe)
    source_width = int(source_video["width"])
    source_height = int(source_video["height"])
    source_fps = float(Fraction(source_video["avg_frame_rate"]))
    source_frames = int(source_video.get("nb_read_frames") or source_video.get("nb_frames") or 0)
    duration = float(source_probe["format"]["duration"])
    if (source_width, source_height) != (1280, 720):
        raise RuntimeError(f"Este perfil exige fonte 1280x720; recebido {source_width}x{source_height}.")
    if abs(source_fps - 30.0) > 0.01 or not source_frames:
        raise RuntimeError(f"Este perfil exige fonte 30 FPS com contagem válida; recebido {source_fps} FPS.")

    interpolated_frames = source_frames * 2
    input_frames = work_dir / "01_input_720p30"
    rife_frames = work_dir / "02_rife_720p60"
    upscaled_frames = work_dir / "03_animev3_4k60"
    master_4k = output_dir / f"{base_name}_MAX_4K60_HEVC10.mp4"
    delivery_fhd = output_dir / f"{base_name}_MAX_FHD60.mp4"
    log_path = output_dir / f"{base_name}_max_quality.log"
    report_path = output_dir / f"{base_name}_max_quality_report.json"

    plan = {
        "source": str(source),
        "source_resolution": f"{source_width}x{source_height}",
        "source_fps": source_fps,
        "source_frames": source_frames,
        "duration_seconds": duration,
        "interpolated_frames": interpolated_frames,
        "upscaler": "Real-ESRGAN AnimeVideo-v3 x3",
        "interpolator": "RIFE v4.6 x2",
        "master_4k": None if args.fhd_only else str(master_4k),
        "delivery_fhd": str(delivery_fhd),
        "work_dir": str(work_dir),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        print("[dry-run] validação concluída; nenhum arquivo foi alterado.", flush=True)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        log.write(f"\n=== execução {datetime.now().astimezone().isoformat()} ===\n")
        log.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")

        source_stat = source.stat()
        source_signature = {
            "source": str(source),
            "size": source_stat.st_size,
            "mtime_ns": source_stat.st_mtime_ns,
            "frames": source_frames,
            "stage": "PNG lossless 720p30",
        }
        if not stage_ready(input_frames, source_frames, source_signature):
            print("[1/4] extraindo PNGs sem perdas", flush=True)
            run(
                [ffmpeg, "-hide_banner", "-y", "-i", str(source), "-map", "0:v:0", "-vsync", "0", "-start_number", "0", str(input_frames / "%08d.png")],
                log,
            )
            if frame_count(input_frames) != source_frames:
                raise RuntimeError("A extração não produziu a contagem esperada de quadros.")
            mark_stage(input_frames, source_signature)

        rife_signature = {
            **source_signature,
            "stage": "RIFE v4.6 30->60",
            "frames": interpolated_frames,
        }
        if not stage_ready(rife_frames, interpolated_frames, rife_signature):
            print("[2/4] interpolando movimento 30 -> 60 FPS com RIFE v4.6", flush=True)
            run(
                [str(RIFE_EXE), "-i", str(input_frames), "-o", str(rife_frames), "-m", "rife-v4.6", "-n", str(interpolated_frames), "-g", str(args.gpu), "-j", "2:4:2", "-f", "%08d.png"],
                log,
                RIFE_ROOT,
            )
            if frame_count(rife_frames) != interpolated_frames:
                raise RuntimeError("O RIFE não produziu a contagem esperada de quadros.")
            mark_stage(rife_frames, rife_signature)

        upscale_signature = {
            **source_signature,
            "stage": "AnimeVideo-v3 x3",
            "frames": interpolated_frames,
        }
        if not stage_ready(upscaled_frames, interpolated_frames, upscale_signature):
            print("[3/4] reconstruindo 720p -> supersampling x3 com AnimeVideo-v3", flush=True)
            run(
                [str(REALESRGAN_EXE), "-i", str(rife_frames), "-o", str(upscaled_frames), "-n", "realesr-animevideov3", "-s", "3", "-g", str(args.gpu), "-j", "2:4:2", "-f", "png"],
                log,
                REALESRGAN_ROOT,
            )
            if frame_count(upscaled_frames) != interpolated_frames:
                raise RuntimeError("O Real-ESRGAN não produziu a contagem esperada de quadros.")
            mark_stage(upscaled_frames, upscale_signature)

        if not args.fhd_only:
            print("[4/5] codificando master 4K60 HEVC 10-bit", flush=True)
            run(
                [ffmpeg, "-hide_banner", "-y", "-framerate", "60", "-start_number", "0", "-i", str(upscaled_frames / "%08d.png"), "-vf", "setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709", "-an", "-c:v", "libx265", "-preset", "slow", "-crf", "11", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1", "-x265-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", str(master_4k)],
                log,
            )

        print(
            "[4/4] codificando entrega Full HD 60 H.264"
            if args.fhd_only else "[5/5] codificando entrega Full HD 60 H.264",
            flush=True,
        )
        run(
            [ffmpeg, "-hide_banner", "-y", "-framerate", "60", "-start_number", "0", "-i", str(upscaled_frames / "%08d.png"), "-vf", "scale=1920:1080:flags=lanczos,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high", "-level:v", "4.2", "-pix_fmt", "yuv420p", "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", str(delivery_fhd)],
            log,
        )

    report = {
        **plan,
        "completed_at": datetime.now().astimezone().isoformat(),
        "master_4k_probe": (
            None if args.fhd_only
            else validate_output(ffprobe, master_4k, 3840, 2160, 60, duration)
        ),
        "delivery_fhd_probe": validate_output(ffprobe, delivery_fhd, 1920, 1080, 60, duration),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.fhd_only:
        print(f"[concluído] {master_4k}", flush=True)
    print(f"[concluído] {delivery_fhd}", flush=True)
    print(f"[relatório] {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[erro] {exc}", file=sys.stderr, flush=True)
        raise
