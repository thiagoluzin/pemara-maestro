"""Remove persistent burned-in subtitles while preserving video motion/audio.

The detector looks for low-saturation bright pixels that remain at the same
screen coordinates through a substantial portion of the clip.  Moving white
objects are rejected by temporal occupancy; only the detected glyph shapes and
their outline are inpainted.  Final delivery is encoded with NVENC and the
original audio stream is copied unchanged.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np


LOG = logging.getLogger("subtitle_cleanup")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--band-top", type=int, default=540)
    parser.add_argument("--band-bottom", type=int, default=675)
    parser.add_argument("--left", type=int, default=160)
    parser.add_argument("--right", type=int, default=1160)
    parser.add_argument("--occupancy", type=float, default=0.30)
    parser.add_argument("--min-luma", type=int, default=188)
    parser.add_argument("--max-saturation", type=int, default=72)
    parser.add_argument("--dilate", type=int, default=7)
    parser.add_argument("--inpaint-radius", type=float, default=3.0)
    parser.add_argument(
        "--method",
        choices=("temporal-flow", "telea"),
        default="temporal-flow",
        help="temporal-flow preserva movimento; telea e apenas fallback local.",
    )
    parser.add_argument("--flow-scale", type=float, default=0.5)
    parser.add_argument("--mask-preview", type=Path)
    parser.add_argument("--frame-preview", type=Path)
    parser.add_argument("--preview-frame", type=int, default=60)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--log", type=Path, default=Path("subtitle_cleanup.log"))
    return parser


def configure_logging(path: Path) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()],
    )


def require_executable(value: str, label: str) -> str:
    executable = shutil.which(value)
    if not executable:
        raise FileNotFoundError(f"{label} nao encontrado: {value}")
    return executable


def open_video(path: Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Nao foi possivel abrir o video: {path}")
    return capture


def white_pixels(frame: np.ndarray, *, min_luma: int, max_saturation: int) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return ((hsv[:, :, 1] <= max_saturation) & (hsv[:, :, 2] >= min_luma)).astype(np.uint8)


def temporal_subtitle_mask(
    path: Path,
    *,
    band_top: int,
    band_bottom: int,
    left: int,
    right: int,
    occupancy: float,
    min_luma: int,
    max_saturation: int,
    dilate: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    capture = open_video(path)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    expected_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    top = max(0, min(height - 1, band_top))
    bottom = max(top + 1, min(height, band_bottom))
    x0 = max(0, min(width - 1, left))
    x1 = max(x0 + 1, min(width, right))
    occupancy_count = np.zeros((bottom - top, x1 - x0), dtype=np.uint16)
    frame_count = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            bright = white_pixels(
                frame[top:bottom, x0:x1],
                min_luma=min_luma,
                max_saturation=max_saturation,
            )
            occupancy_count += bright
            frame_count += 1
    finally:
        capture.release()
    if frame_count < 2:
        raise RuntimeError("Video sem quadros suficientes para detectar legenda temporal.")

    threshold = max(2, int(round(frame_count * occupancy)))
    core_roi = (occupancy_count >= threshold).astype(np.uint8) * 255
    # Remove isolated compression noise before expanding over the dark outline.
    core_roi = cv2.morphologyEx(core_roi, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(core_roi, connectivity=8)
    filtered = np.zeros_like(core_roi)
    for component in range(1, component_count):
        area = int(stats[component, cv2.CC_STAT_AREA])
        component_height = int(stats[component, cv2.CC_STAT_HEIGHT])
        component_width = int(stats[component, cv2.CC_STAT_WIDTH])
        if 3 <= area <= 1800 and component_height <= 38 and component_width <= 160:
            filtered[labels == component] = 255

    kernel_size = max(1, int(dilate))
    if kernel_size % 2 == 0:
        kernel_size += 1
    expanded_roi = cv2.dilate(filtered, np.ones((kernel_size, kernel_size), np.uint8), iterations=1)
    core = np.zeros((height, width), dtype=np.uint8)
    expanded = np.zeros((height, width), dtype=np.uint8)
    core[top:bottom, x0:x1] = filtered
    expanded[top:bottom, x0:x1] = expanded_roi
    details: dict[str, float | int] = {
        "width": width,
        "height": height,
        "fps": fps,
        "expected_frames": expected_frames,
        "decoded_frames": frame_count,
        "occupancy_threshold_frames": threshold,
        "core_pixels": int(np.count_nonzero(core)),
        "expanded_pixels": int(np.count_nonzero(expanded)),
    }
    if details["core_pixels"] < 250:
        raise RuntimeError(f"Mascara de legenda pequena demais: {details}")
    return core, expanded, details


def frame_has_subtitle(
    frame: np.ndarray,
    core_mask: np.ndarray,
    *,
    min_luma: int,
    max_saturation: int,
) -> bool:
    core_pixels = int(np.count_nonzero(core_mask))
    if core_pixels == 0:
        return False
    bright = white_pixels(frame, min_luma=min_luma, max_saturation=max_saturation)
    overlap = int(np.count_nonzero((bright > 0) & (core_mask > 0)))
    return overlap / core_pixels >= 0.18


def inpaint_frame(frame: np.ndarray, mask: np.ndarray, radius: float) -> np.ndarray:
    return cv2.inpaint(frame, mask, radius, cv2.INPAINT_TELEA)


def read_frames(input_path: Path) -> tuple[list[np.ndarray], float]:
    capture = open_video(input_path)
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames: list[np.ndarray] = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frames.append(frame)
    finally:
        capture.release()
    if len(frames) < 2:
        raise RuntimeError("Video sem quadros suficientes para limpeza temporal.")
    return frames, fps


def _flow_gray(frame: np.ndarray, mask: np.ndarray, radius: float, scale: float) -> np.ndarray:
    # The burned text is removed before optical-flow estimation so its static
    # screen position cannot overpower the actual scene motion.
    prepared = inpaint_frame(frame, mask, radius)
    gray = cv2.cvtColor(prepared, cv2.COLOR_BGR2GRAY)
    if scale != 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return gray


def warp_clean_source_to_target(
    source_clean: np.ndarray,
    source_original: np.ndarray,
    target_original: np.ndarray,
    mask: np.ndarray,
    *,
    radius: float,
    flow_scale: float,
) -> np.ndarray:
    if not 0.2 <= flow_scale <= 1.0:
        raise ValueError("flow_scale deve ficar entre 0.2 e 1.0.")
    target_gray = _flow_gray(target_original, mask, radius, flow_scale)
    source_gray = _flow_gray(source_original, mask, radius, flow_scale)
    # Dense flow from target coordinates to source coordinates is directly
    # usable as a cv2.remap lookup into the already-clean source frame.
    flow = cv2.calcOpticalFlowFarneback(
        target_gray,
        source_gray,
        None,
        pyr_scale=0.5,
        levels=4,
        winsize=35,
        iterations=5,
        poly_n=7,
        poly_sigma=1.5,
        flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN,
    )
    height, width = target_original.shape[:2]
    if flow_scale != 1.0:
        flow = cv2.resize(flow, (width, height), interpolation=cv2.INTER_LINEAR)
        flow[:, :, 0] /= flow_scale
        flow[:, :, 1] /= flow_scale
    grid_x, grid_y = np.meshgrid(
        np.arange(width, dtype=np.float32),
        np.arange(height, dtype=np.float32),
    )
    return cv2.remap(
        source_clean,
        grid_x + flow[:, :, 0],
        grid_y + flow[:, :, 1],
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT101,
    )


def temporal_flow_clean_frames(
    frames: list[np.ndarray],
    has_subtitle: list[bool],
    mask: np.ndarray,
    *,
    radius: float,
    flow_scale: float,
) -> list[np.ndarray]:
    if len(frames) != len(has_subtitle):
        raise ValueError("Quantidade de quadros e marcadores nao confere.")
    mask_pixels = mask > 0
    forward: list[np.ndarray] = []
    for index, original in enumerate(frames):
        if not has_subtitle[index]:
            forward.append(original.copy())
            continue
        if index == 0:
            forward.append(inpaint_frame(original, mask, radius))
            continue
        warped = warp_clean_source_to_target(
            forward[index - 1],
            frames[index - 1],
            original,
            mask,
            radius=radius,
            flow_scale=flow_scale,
        )
        cleaned = original.copy()
        cleaned[mask_pixels] = warped[mask_pixels]
        forward.append(cleaned)

    backward: list[np.ndarray | None] = [None] * len(frames)
    for index in range(len(frames) - 1, -1, -1):
        original = frames[index]
        if not has_subtitle[index]:
            backward[index] = original.copy()
            continue
        if index == len(frames) - 1:
            backward[index] = inpaint_frame(original, mask, radius)
            continue
        next_clean = backward[index + 1]
        assert next_clean is not None
        warped = warp_clean_source_to_target(
            next_clean,
            frames[index + 1],
            original,
            mask,
            radius=radius,
            flow_scale=flow_scale,
        )
        cleaned = original.copy()
        cleaned[mask_pixels] = warped[mask_pixels]
        backward[index] = cleaned

    previous_anchor: list[int | None] = []
    anchor: int | None = None
    for index, present in enumerate(has_subtitle):
        if not present:
            anchor = index
        previous_anchor.append(anchor)
    next_anchor: list[int | None] = [None] * len(frames)
    anchor = None
    for index in range(len(frames) - 1, -1, -1):
        if not has_subtitle[index]:
            anchor = index
        next_anchor[index] = anchor

    result: list[np.ndarray] = []
    for index, original in enumerate(frames):
        if not has_subtitle[index]:
            result.append(original.copy())
            continue
        forward_frame = forward[index]
        backward_frame = backward[index]
        assert backward_frame is not None
        before = previous_anchor[index]
        after = next_anchor[index]
        if before is None:
            blended = backward_frame
        elif after is None:
            blended = forward_frame
        else:
            distance_before = index - before
            distance_after = after - index
            backward_weight = distance_before / (distance_before + distance_after)
            blended = cv2.addWeighted(
                forward_frame,
                1.0 - backward_weight,
                backward_frame,
                backward_weight,
                0.0,
            )
        cleaned = original.copy()
        cleaned[mask_pixels] = blended[mask_pixels]
        result.append(cleaned)
    return result


def write_previews(
    original_frames: list[np.ndarray],
    cleaned_frames: list[np.ndarray],
    expanded_mask: np.ndarray,
    *,
    frame_index: int,
    mask_preview: Path | None,
    frame_preview: Path | None,
) -> None:
    if mask_preview:
        mask_preview.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(mask_preview), expanded_mask):
            raise RuntimeError(f"Falha ao gravar mascara: {mask_preview}")
    if not frame_preview:
        return
    if not 0 <= frame_index < len(original_frames):
        raise RuntimeError(f"Quadro de preview indisponivel: {frame_index}")
    comparison = np.hstack((original_frames[frame_index], cleaned_frames[frame_index]))
    frame_preview.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(frame_preview), comparison):
        raise RuntimeError(f"Falha ao gravar preview: {frame_preview}")


def encode_clean_video(
    input_path: Path,
    output_path: Path,
    frames_to_encode: list[np.ndarray],
    *,
    ffmpeg: str,
    fps: float,
    cleaned_frames: int,
) -> dict[str, int | float]:
    height, width = frames_to_encode[0].shape[:2]
    staging = output_path.with_name(f".{output_path.stem}.{int(time.time())}.part.mp4")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s:v",
        f"{width}x{height}",
        "-r",
        f"{fps:.8f}",
        "-i",
        "pipe:0",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p6",
        "-tune",
        "hq",
        "-rc",
        "vbr",
        "-cq",
        "16",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        "-shortest",
        str(staging),
    ]
    child = subprocess.Popen(command, stdin=subprocess.PIPE)
    frames = 0
    try:
        if child.stdin is None:
            raise RuntimeError("FFmpeg nao abriu stdin para quadros raw.")
        for frame in frames_to_encode:
            child.stdin.write(frame.tobytes())
            frames += 1
        child.stdin.close()
        code = child.wait(timeout=180)
        if code != 0:
            raise RuntimeError(f"FFmpeg/NVENC terminou com codigo {code}.")
        if not staging.is_file() or staging.stat().st_size < 1024:
            raise RuntimeError("Saida NVENC ausente ou vazia.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(output_path)
    except Exception:
        if child.poll() is None:
            child.kill()
        raise
    finally:
        staging.unlink(missing_ok=True)
    return {"frames": frames, "cleaned_frames": cleaned_frames, "fps": fps}


def probe_output(ffprobe: str, path: Path) -> dict:
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio = next((item for item in streams if item.get("codec_type") == "audio"), {})
    if video.get("codec_name") != "h264" or int(video.get("width") or 0) != 1280 or int(video.get("height") or 0) != 720:
        raise RuntimeError(f"Video de saida fora do contrato: {payload}")
    if not audio:
        raise RuntimeError("A limpeza removeu o audio por engano.")
    return payload


def main() -> int:
    args = build_parser().parse_args()
    configure_logging(args.log)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Video de entrada ausente: {input_path}")
    if input_path == output_path:
        raise ValueError("A saida deve preservar o video original em outro caminho.")
    ffmpeg = require_executable(args.ffmpeg, "ffmpeg")
    ffprobe = require_executable(args.ffprobe, "ffprobe")
    if output_path.exists() and not args.force:
        probe = probe_output(ffprobe, output_path)
        LOG.info("Saida existente e valida; nada a fazer: %s", output_path)
        print(json.dumps({"ok": True, "reused": True, "output": str(output_path), "probe": probe}, ensure_ascii=False))
        return 0

    core, expanded, mask_details = temporal_subtitle_mask(
        input_path,
        band_top=args.band_top,
        band_bottom=args.band_bottom,
        left=args.left,
        right=args.right,
        occupancy=args.occupancy,
        min_luma=args.min_luma,
        max_saturation=args.max_saturation,
        dilate=args.dilate,
    )
    LOG.info("Mascara temporal detectada: %s", mask_details)
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "mask": mask_details}, ensure_ascii=False))
        return 0

    frames, fps = read_frames(input_path)
    subtitle_flags = [
        frame_has_subtitle(
            frame,
            core,
            min_luma=args.min_luma,
            max_saturation=args.max_saturation,
        )
        for frame in frames
    ]
    if args.method == "temporal-flow":
        cleaned = temporal_flow_clean_frames(
            frames,
            subtitle_flags,
            expanded,
            radius=args.inpaint_radius,
            flow_scale=args.flow_scale,
        )
    else:
        cleaned = [
            inpaint_frame(frame, expanded, args.inpaint_radius) if present else frame.copy()
            for frame, present in zip(frames, subtitle_flags)
        ]
    write_previews(
        frames,
        cleaned,
        expanded,
        frame_index=args.preview_frame,
        mask_preview=args.mask_preview,
        frame_preview=args.frame_preview,
    )
    encode_details = encode_clean_video(
        input_path,
        output_path,
        cleaned,
        ffmpeg=ffmpeg,
        fps=fps,
        cleaned_frames=sum(subtitle_flags),
    )
    probe = probe_output(ffprobe, output_path)
    result = {
        "ok": True,
        "reused": False,
        "input": str(input_path),
        "output": str(output_path),
        "mask": mask_details,
        "method": args.method,
        "encode": encode_details,
        "probe": probe,
    }
    LOG.info("Limpeza concluida: %s", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        LOG.exception("FALHOU")
        raise
