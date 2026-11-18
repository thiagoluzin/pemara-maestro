#!/usr/bin/env python3
"""Corrige o blackout do Take 07 e trava somente a cidade distante aprovada.

O tratamento conserva integralmente a geometria generativa da rua e das bordas.
A exposicao e recuperada em luz linear, com curvas espaciais fixas, enquanto o
ouro original do RAW e recomposto. A imagem aprovada entra apenas no centro
distante, acompanhando o movimento medido do proprio video.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import savgol_filter


EXPECTED_INPUT_SHA256 = "50E822F1E88EDC05645599F8BBE8BEF8D1782B47428BBAD0B973F1101BC45446"
EXPECTED_SOURCE_SHA256 = "25B18EAC9769AB8CB627BBEA870B5631FE662B38967A8A2065724F9D6FD9193E"

CURVE_FRAMES = np.array([0, 3, 5, 10, 20, 30, 40, 60, 80, 100, 112, 120], np.float64)
CURVE_CENTER = np.array([0, 0, 0.08, 0.50, 0.67, 0.67, 0.67, 0.67, 0.67, 0.67, 0.64, 0.52], np.float64)
CURVE_EDGES = np.array([0, 0, 0.12, 1.05, 1.65, 1.90, 2.20, 2.70, 3.00, 3.20, 3.30, 2.80], np.float64)
CURVE_ROAD = np.array([0, 0, 0.15, 1.15, 1.85, 2.05, 2.10, 2.10, 2.10, 2.10, 2.00, 1.50], np.float64)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    amount = np.clip((values - edge0) / max(edge1 - edge0, 1e-8), 0.0, 1.0)
    return amount * amount * (3.0 - 2.0 * amount)


def srgb_to_linear(frame: np.ndarray) -> np.ndarray:
    values = frame.astype(np.float32) / 255.0
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(frame: np.ndarray) -> np.ndarray:
    values = np.clip(frame, 0.0, 1.0)
    encoded = np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1.0 / 2.4) - 0.055)
    return np.clip(np.round(encoded * 255.0), 0, 255).astype(np.uint8)


def linear_luma(frame: np.ndarray) -> np.ndarray:
    return 0.0722 * frame[:, :, 0] + 0.7152 * frame[:, :, 1] + 0.2126 * frame[:, :, 2]


def gold_mask(frame: np.ndarray, value_floor: int = 35) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return (
        (hsv[:, :, 0] <= 35)
        & (hsv[:, :, 1] >= 55)
        & (hsv[:, :, 2] >= value_floor)
    ).astype(np.uint8) * 255


def feather_gold(mask: np.ndarray) -> np.ndarray:
    expanded = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)
    feather = np.clip(cv2.GaussianBlur(expanded, (0, 0), 1.2).astype(np.float32) / 255.0, 0.0, 1.0)
    feather[mask > 0] = 1.0
    return feather


def decode_video(path: Path) -> tuple[list[np.ndarray], float, int, int]:
    capture = cv2.VideoCapture(str(path))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    expected = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frames: list[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames or len(frames) != expected:
        raise RuntimeError(f"Decode incompleto: {len(frames)}/{expected}")
    return frames, fps, width, height


def ffprobe(path: Path) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable:
        raise RuntimeError("ffprobe nao encontrado")
    result = subprocess.run(
        [executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def register_approved_source(source: np.ndarray, frame_zero: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, float]:
    gray_source = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    gray_target = cv2.cvtColor(frame_zero, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.003, edgeThreshold=15)
    key_source, descriptor_source = sift.detectAndCompute(gray_source, None)
    key_target, descriptor_target = sift.detectAndCompute(gray_target, None)
    if descriptor_source is None or descriptor_target is None:
        raise RuntimeError("Registro sem descritores SIFT")
    matches = cv2.BFMatcher().knnMatch(descriptor_source, descriptor_target, k=2)
    good = [first for first, second in matches if first.distance < 0.75 * second.distance]
    if len(good) < 40:
        raise RuntimeError(f"Registro da fonte com poucas correspondencias: {len(good)}")
    points_source = np.float32([key_source[item.queryIdx].pt for item in good])
    points_target = np.float32([key_target[item.trainIdx].pt for item in good])
    homography, inside = cv2.findHomography(points_source, points_target, cv2.RANSAC, 1.5)
    if homography is None or inside is None or int(inside.sum()) < 40:
        raise RuntimeError("Registro da fonte falhou no RANSAC")
    keep = inside.ravel().astype(bool)
    projected = cv2.perspectiveTransform(points_source[None, :, :], homography)[0]
    error = float(np.median(np.linalg.norm(projected[keep] - points_target[keep], axis=1)))
    registered = cv2.warpPerspective(
        source,
        homography,
        (frame_zero.shape[1], frame_zero.shape[0]),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT101,
    )
    return registered, homography, int(inside.sum()), error


def enhanced_gray(frame: np.ndarray, clahe: cv2.CLAHE) -> np.ndarray:
    return clahe.apply(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))


def tracking_transforms(frames: list[np.ndarray]) -> tuple[list[np.ndarray], list[int], list[float], int]:
    """Segue apenas a camada distante por fluxo sequencial e suaviza o acumulado."""

    height, width = frames[0].shape[:2]
    static_mask = np.zeros((height, width), np.uint8)
    cv2.rectangle(
        static_mask,
        (round(width * 0.35), round(height * 0.40)),
        (round(width * 0.65), round(height * 0.72)),
        255,
        -1,
    )
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = [enhanced_gray(frame, clahe) for frame in frames]
    cumulative = np.eye(3, dtype=np.float64)
    parameters: list[list[float]] = [[0.0, 0.0, 0.0, 0.0]]
    inliers: list[int] = [0]
    errors: list[float] = [0.0]
    fallback_count = 0
    lk = dict(
        winSize=(31, 31),
        maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01),
    )

    for index in range(1, len(frames)):
        feature_mask = static_mask.copy()
        feature_mask[cv2.dilate(gold_mask(frames[index - 1]), np.ones((5, 5), np.uint8)) > 0] = 0
        points = cv2.goodFeaturesToTrack(
            gray[index - 1],
            maxCorners=800,
            qualityLevel=0.0025,
            minDistance=3,
            mask=feature_mask,
            blockSize=5,
        )
        matrix: np.ndarray | None = None
        count = 0
        reprojection = math.nan
        if points is not None and len(points) >= 30:
            forward, status_a, _ = cv2.calcOpticalFlowPyrLK(gray[index - 1], gray[index], points, None, **lk)
            backward, status_b, _ = cv2.calcOpticalFlowPyrLK(gray[index], gray[index - 1], forward, None, **lk)
            original = points.reshape(-1, 2)
            moved = forward.reshape(-1, 2)
            fb_error = np.linalg.norm(original - backward.reshape(-1, 2), axis=1)
            valid = (status_a.ravel() == 1) & (status_b.ravel() == 1) & (fb_error < 1.0)
            if int(valid.sum()) >= 25:
                matrix, inside = cv2.estimateAffinePartial2D(
                    original[valid],
                    moved[valid],
                    method=cv2.RANSAC,
                    ransacReprojThreshold=1.0,
                    maxIters=3000,
                    confidence=0.999,
                    refineIters=20,
                )
                if matrix is not None and inside is not None:
                    keep = inside.ravel().astype(bool)
                    count = int(keep.sum())
                    projected = cv2.transform(original[valid][None, :, :], matrix)[0]
                    reprojection = float(np.median(np.linalg.norm(projected[keep] - moved[valid][keep], axis=1)))
                    if count < 20:
                        matrix = None

        if matrix is None:
            matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], np.float64)
            fallback_count += 1
            count = 0

        a = float(matrix[0, 0])
        b = float(matrix[1, 0])
        scale = float(np.clip(math.hypot(a, b), 0.99, 1.01))
        angle = float(np.clip(math.atan2(b, a), math.radians(-0.4), math.radians(0.4)))
        tx = float(np.clip(matrix[0, 2], -2.0, 2.0))
        ty = float(np.clip(matrix[1, 2], -2.0, 2.0))
        constrained = np.array(
            [
                [math.cos(angle) * scale, -math.sin(angle) * scale, tx],
                [math.sin(angle) * scale, math.cos(angle) * scale, ty],
                [0.0, 0.0, 1.0],
            ],
            np.float64,
        )
        cumulative = constrained @ cumulative
        current_scale = max(math.hypot(float(cumulative[0, 0]), float(cumulative[1, 0])), 1e-8)
        parameters.append(
            [
                float(cumulative[0, 2]),
                float(cumulative[1, 2]),
                math.atan2(float(cumulative[1, 0]), float(cumulative[0, 0])),
                math.log(current_scale),
            ]
        )
        inliers.append(count)
        errors.append(reprojection)

    values = np.asarray(parameters, np.float64)
    for column in range(values.shape[1]):
        values[:, column] = median_filter(values[:, column], size=5, mode="nearest")
        if len(values) >= 15:
            values[:, column] = savgol_filter(values[:, column], 15, 2, mode="interp")
        values[:, column] -= values[0, column]

    transforms: list[np.ndarray] = []
    for tx, ty, angle, log_scale in values:
        scale = float(np.clip(math.exp(float(log_scale)), 0.85, 1.05))
        angle = float(np.clip(angle, math.radians(-2.0), math.radians(2.0)))
        transforms.append(
            np.array(
                [
                    [math.cos(angle) * scale, -math.sin(angle) * scale, tx],
                    [math.sin(angle) * scale, math.cos(angle) * scale, ty],
                ],
                np.float32,
            )
        )
    transforms[0] = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], np.float32)
    return transforms, inliers, errors, fallback_count


def center_lock_mask(height: int, width: int) -> np.ndarray:
    """Core x=30..70%, y=0..72%; feather lateral 48 px e vertical ate 82%."""

    x = np.arange(width, dtype=np.float32)[None, :]
    y = np.arange(height, dtype=np.float32)[:, None]
    left = smoothstep(width * 0.30 - 48.0, width * 0.30, x)
    right = 1.0 - smoothstep(width * 0.70, width * 0.70 + 48.0, x)
    horizontal = np.minimum(left, right)
    vertical = 1.0 - smoothstep(height * 0.72, height * 0.82, y)
    return np.clip(horizontal * vertical, 0.0, 1.0).astype(np.float32)


def spatial_weights(height: int, width: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    center_left = smoothstep(0.20, 0.30, x)
    center_right = 1.0 - smoothstep(0.70, 0.80, x)
    center_x = np.minimum(center_left, center_right)
    road_ramp = smoothstep(0.55, 0.85, y)
    center_y = 1.0 - smoothstep(0.70, 0.88, y)
    center = center_x * center_y
    road = road_ramp * (0.70 + 0.30 * center_x)
    edges = (1.0 - center_x) * (1.0 - 0.50 * road_ramp) + 0.02
    total = np.maximum(center + road + edges, 1e-6)
    return (center / total).astype(np.float32), (edges / total).astype(np.float32), (road / total).astype(np.float32)


def curve_values(frame_index: int) -> tuple[float, float, float]:
    return (
        float(np.interp(frame_index, CURVE_FRAMES, CURVE_CENTER)),
        float(np.interp(frame_index, CURVE_FRAMES, CURVE_EDGES)),
        float(np.interp(frame_index, CURVE_FRAMES, CURVE_ROAD)),
    )


def correct_spatial_exposure(
    raw_linear: np.ndarray,
    frame_index: int,
    weights: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> tuple[np.ndarray, float]:
    center_stop, edge_stop, road_stop = curve_values(frame_index)
    center_weight, edge_weight, road_weight = weights
    stop_map = center_weight * center_stop + edge_weight * edge_stop + road_weight * road_stop
    luminance = linear_luma(raw_linear)
    shadow_weight = 1.0 - smoothstep(0.025, 0.12, luminance)
    target_gain = np.exp2(stop_map).astype(np.float32)
    effective_gain = 1.0 + shadow_weight * (target_gain - 1.0)
    corrected = np.clip(raw_linear * effective_gain[:, :, None], 0.0, 1.0)
    return corrected, float(np.mean(np.any(corrected >= 0.9999, axis=2)))


def robust_plate_channel_gain(
    registered: np.ndarray,
    frame_zero: np.ndarray,
    lock: np.ndarray,
    source_gold: np.ndarray,
) -> np.ndarray:
    plate = srgb_to_linear(registered)
    target = srgb_to_linear(frame_zero)
    luma = linear_luma(plate)
    use = (lock >= 0.98) & (source_gold == 0) & (luma >= 0.003) & (luma <= 0.25)
    if int(use.sum()) < 1000:
        raise RuntimeError("Amostra insuficiente para casar a placa aprovada")
    gains: list[float] = []
    for channel in range(3):
        numerator = target[:, :, channel][use]
        denominator = plate[:, :, channel][use]
        valid = denominator >= 0.002
        ratio = numerator[valid] / denominator[valid]
        gains.append(float(np.clip(np.median(ratio), 0.80, 1.20)))
    return np.asarray(gains, np.float32)


def encode_command(
    ffmpeg: str,
    input_path: Path,
    output: Path,
    width: int,
    height: int,
    fps: float,
    count: int,
    gpu: int,
) -> list[str]:
    return [
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
        "-",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a?",
        "-map_metadata",
        "1",
        "-frames:v",
        str(count),
        "-r",
        f"{fps:.8f}",
        "-fps_mode",
        "cfr",
        "-c:v",
        "h264_nvenc",
        "-gpu",
        str(gpu),
        "-preset",
        "p7",
        "-tune",
        "hq",
        "-rc:v",
        "vbr",
        "-cq:v",
        "6",
        "-b:v",
        "0",
        "-maxrate:v",
        "32M",
        "-bufsize:v",
        "64M",
        "-multipass",
        "fullres",
        "-spatial-aq",
        "1",
        "-temporal-aq",
        "1",
        "-aq-strength",
        "8",
        "-rc-lookahead",
        "20",
        "-bf",
        "3",
        "-b_ref_mode",
        "middle",
        "-g",
        str(max(1, round(fps * 2))),
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-color_range",
        "pc",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output),
    ]


def ssim_map(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    a = first.astype(np.float32) / 255.0
    b = second.astype(np.float32) / 255.0
    c1 = 0.01**2
    c2 = 0.03**2
    mu_a = cv2.GaussianBlur(a, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(b, (11, 11), 1.5)
    sigma_a = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu_a * mu_a
    sigma_b = cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu_b * mu_b
    sigma_ab = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu_a * mu_b
    return ((2.0 * mu_a * mu_b + c1) * (2.0 * sigma_ab + c2)) / (
        (mu_a * mu_a + mu_b * mu_b + c1) * (sigma_a + sigma_b + c2) + 1e-8
    )


def edge_correlation(first: np.ndarray, second: np.ndarray, mask: np.ndarray) -> float:
    edge_a = cv2.magnitude(cv2.Sobel(first, cv2.CV_32F, 1, 0), cv2.Sobel(first, cv2.CV_32F, 0, 1))
    edge_b = cv2.magnitude(cv2.Sobel(second, cv2.CV_32F, 1, 0), cv2.Sobel(second, cv2.CV_32F, 0, 1))
    use = mask > 0
    a = edge_a[use]
    b = edge_b[use]
    if len(a) < 100 or float(np.std(a)) < 1e-5 or float(np.std(b)) < 1e-5:
        return math.nan
    return float(np.corrcoef(a, b)[0, 1])


def zone_metric(frame: np.ndarray, mask: np.ndarray) -> float:
    luma = linear_luma(srgb_to_linear(frame))
    values = luma[(mask > 0) & (luma > 1e-5)]
    if not values.size:
        return math.nan
    return float(np.mean(values))


def coefficient_of_variation(values: list[float]) -> float:
    selected = np.asarray([value for value in values if math.isfinite(value)], np.float64)
    return float(np.std(selected) / max(np.mean(selected), 1e-8))


def external_flow_metrics(
    raw: list[np.ndarray],
    treated: list[np.ndarray],
    alpha_masks: list[np.ndarray],
) -> tuple[float, float]:
    """Compara vetores KLT externos sob normalizacao fotometrica robusta."""

    differences: list[float] = []
    cosines: list[float] = []
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    samples = list(range(0, len(raw) - 10, 10))
    lk = dict(
        winSize=(41, 41),
        maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.005),
    )
    for index in samples:
        raw_a = clahe.apply(cv2.cvtColor(raw[index], cv2.COLOR_BGR2GRAY))
        raw_b = clahe.apply(cv2.cvtColor(raw[index + 10], cv2.COLOR_BGR2GRAY))
        out_a = clahe.apply(cv2.cvtColor(treated[index], cv2.COLOR_BGR2GRAY))
        out_b = clahe.apply(cv2.cvtColor(treated[index + 10], cv2.COLOR_BGR2GRAY))
        external = ((alpha_masks[index] < 0.01) & (alpha_masks[index + 10] < 0.01)).astype(np.uint8) * 255
        points = cv2.goodFeaturesToTrack(raw_a, maxCorners=1200, qualityLevel=0.004, minDistance=4, mask=external, blockSize=5)
        if points is None or len(points) < 100:
            continue
        raw_moved, raw_status, _ = cv2.calcOpticalFlowPyrLK(raw_a, raw_b, points, None, **lk)
        out_moved, out_status, _ = cv2.calcOpticalFlowPyrLK(out_a, out_b, points, None, **lk)
        origin = points.reshape(-1, 2)
        raw_vector = raw_moved.reshape(-1, 2) - origin
        out_vector = out_moved.reshape(-1, 2) - origin
        raw_magnitude = np.linalg.norm(raw_vector, axis=1)
        out_magnitude = np.linalg.norm(out_vector, axis=1)
        valid = (
            (raw_status.ravel() == 1)
            & (out_status.ravel() == 1)
            & (raw_magnitude >= 0.25)
            & (out_magnitude >= 0.05)
        )
        if int(valid.sum()) < 100:
            continue
        differences.extend(
            (np.abs(out_magnitude[valid] - raw_magnitude[valid]) / np.maximum(raw_magnitude[valid], 0.25)).tolist()
        )
        cosine = np.sum(raw_vector * out_vector, axis=1) / np.maximum(raw_magnitude * out_magnitude, 1e-6)
        cosines.extend(cosine[valid].tolist())
    if not differences:
        return math.nan, math.nan
    return float(np.median(differences)), float(np.median(cosines))


def make_contact_sheet(
    frames: list[np.ndarray],
    output: Path,
    crop: tuple[int, int, int, int] | None = None,
) -> None:
    indices = np.linspace(0, len(frames) - 1, 12).round().astype(int)
    tiles: list[np.ndarray] = []
    for index in indices:
        tile = frames[int(index)].copy()
        if crop is not None:
            x0, y0, x1, y1 = crop
            tile = tile[y0:y1, x0:x1]
            tile = cv2.resize(tile, (768, 432), interpolation=cv2.INTER_LANCZOS4)
        cv2.rectangle(tile, (0, 0), (126, 31), (0, 0, 0), -1)
        cv2.putText(tile, f"frame {int(index):03d}", (9, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(tile)
    rows: list[np.ndarray] = []
    for start in range(0, 12, 3):
        rows.append(np.concatenate(tiles[start : start + 3], axis=1))
    sheet = np.concatenate(rows, axis=0)
    if not cv2.imwrite(str(output), sheet, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise RuntimeError(f"Falha ao escrever contato: {output}")


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_path = args.input.resolve()
    source_path = args.approved_source.resolve()
    output = args.output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if output.exists() and not args.force:
        raise FileExistsError(output)

    input_hash = sha256(input_path)
    source_hash = sha256(source_path)
    if args.expected_input_sha256 and input_hash != args.expected_input_sha256.upper():
        raise RuntimeError(f"SHA do RAW divergente: {input_hash}")
    if args.expected_source_sha256 and source_hash != args.expected_source_sha256.upper():
        raise RuntimeError(f"SHA da fonte aprovada divergente: {source_hash}")

    frames, fps, width, height = decode_video(input_path)
    if len(frames) != 121 or abs(fps - 30.0) > 0.01:
        raise RuntimeError(f"Cadencia invalida: {len(frames)} frames @ {fps:.6f} fps")

    approved = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if approved is None:
        raise RuntimeError(f"Falha ao abrir fonte: {source_path}")
    approved = cv2.resize(approved, (width, height), interpolation=cv2.INTER_AREA)
    registered, homography, registration_inliers, registration_error = register_approved_source(approved, frames[0])
    if registration_error > 1.0:
        raise RuntimeError(f"Registro da fonte inseguro: {registration_error:.4f}px")

    transforms, tracking_inliers, tracking_errors, fallback_count = tracking_transforms(frames)
    finite_errors = [value for value in tracking_errors[1:] if math.isfinite(value)]
    nonzero_inliers = [value for value in tracking_inliers[1:] if value > 0]
    if fallback_count > 3 or not finite_errors or float(np.percentile(finite_errors, 95)) > 2.5:
        raise RuntimeError("Rastreamento da camada distante fora do limite seguro")

    base_lock = center_lock_mask(height, width)
    approved_gold = gold_mask(approved, value_floor=28)
    registered_gold = cv2.warpPerspective(
        approved_gold,
        homography,
        (width, height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
    )
    registered_gold_protect = cv2.dilate(
        registered_gold,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        iterations=1,
    )
    registered_gold_protect = np.clip(
        cv2.GaussianBlur(registered_gold_protect, (0, 0), 1.2).astype(np.float32) / 255.0,
        0.0,
        1.0,
    )
    channel_gain = robust_plate_channel_gain(registered, frames[0], base_lock, registered_gold)
    plate_linear = np.clip(srgb_to_linear(registered) * channel_gain[None, None, :], 0.0, 1.0)
    weights = spatial_weights(height, width)

    treated_preencode: list[np.ndarray] = []
    warped_plates: list[np.ndarray] = []
    alpha_masks: list[np.ndarray] = []
    clipping: list[float] = []
    seam_excess: list[float] = []
    for index, (raw, transform) in enumerate(zip(frames, transforms)):
        raw_linear = srgb_to_linear(raw)
        corrected, clipped = correct_spatial_exposure(raw_linear, index, weights)
        clipping.append(clipped)
        warped_plate = cv2.warpAffine(
            plate_linear,
            transform,
            (width, height),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_REFLECT101,
        )
        warped_lock = cv2.warpAffine(
            base_lock,
            transform,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )
        warped_source_gold = cv2.warpAffine(
            registered_gold_protect,
            transform,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )
        raw_gold_hard = gold_mask(raw)
        raw_gold_alpha = feather_gold(raw_gold_hard)
        alpha = np.clip(warped_lock * (1.0 - warped_source_gold) * (1.0 - raw_gold_alpha), 0.0, 1.0)

        # Casa somente a baixa frequencia da placa na faixa de feather. O core
        # continua vindo da fonte aprovada; a borda deixa de criar uma faixa de
        # cor quando o RAW escuro e recuperado em varios stops.
        corrected_low = cv2.GaussianBlur(corrected, (0, 0), 18.0)
        plate_low = cv2.GaussianBlur(warped_plate, (0, 0), 18.0)
        feather_match = 1.0 - np.power(alpha, 4.0)
        harmonized_plate = np.clip(
            warped_plate + (corrected_low - plate_low) * feather_match[:, :, None],
            0.0,
            1.0,
        )
        locked = corrected * (1.0 - alpha[:, :, None]) + harmonized_plate * alpha[:, :, None]
        result_linear = locked * (1.0 - raw_gold_alpha[:, :, None]) + raw_linear * raw_gold_alpha[:, :, None]
        result = linear_to_srgb(result_linear)
        # O round-trip BGR -> H.264 4:2:0 reduz 2--3 niveis nos highlights
        # dourados. A compensacao e aplicada apenas no core que sera perdido
        # pelo codec; depois do decode o ouro volta ao RAW, sem criar brilho.
        hard_gold = raw_gold_hard > 0
        if int(hard_gold.sum()) > 0:
            raw_gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY).astype(np.float32)
            encode_offset = 2.0 + 0.008 * raw_gray
            boosted = raw.astype(np.float32) + encode_offset[:, :, None]
            result[hard_gold] = np.clip(boosted[hard_gold], 0, 255).astype(np.uint8)
        treated_preencode.append(result)
        warped_plates.append(linear_to_srgb(harmonized_plate))
        alpha_masks.append(alpha)

        gray_corrected = cv2.cvtColor(linear_to_srgb(corrected), cv2.COLOR_BGR2GRAY)
        gray_result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        low_a = cv2.GaussianBlur(gray_corrected.astype(np.float32), (0, 0), 6.0)
        low_b = cv2.GaussianBlur(gray_result.astype(np.float32), (0, 0), 6.0)
        grad_a = np.abs(cv2.Laplacian(low_a, cv2.CV_32F, ksize=3))
        grad_b = np.abs(cv2.Laplacian(low_b, cv2.CV_32F, ksize=3))
        boundary = (alpha >= 0.05) & (alpha <= 0.95)
        if int(boundary.sum()) > 100:
            seam_excess.append(float(np.percentile(np.maximum(grad_b[boundary] - grad_a[boundary], 0.0), 95) / 255.0))

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg nao encontrado")
    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        encode_command(ffmpeg, input_path, output, width, height, fps, len(treated_preencode), args.gpu),
        stdin=subprocess.PIPE,
    )
    assert process.stdin is not None
    for frame in treated_preencode:
        process.stdin.write(frame.tobytes())
    process.stdin.close()
    status = process.wait()
    if status:
        raise RuntimeError(f"ffmpeg/NVENC encerrou com codigo {status}")

    encoded, encoded_fps, encoded_width, encoded_height = decode_video(output)
    if len(encoded) != 121 or abs(encoded_fps - 30.0) > 0.01 or (encoded_width, encoded_height) != (width, height):
        raise RuntimeError("Saida codificada alterou cadencia ou resolucao")

    edge_correlations: list[float] = []
    center_ssim: list[float] = []
    gold_mean_delta: list[float] = []
    gold_p99_delta: list[float] = []
    new_gold_component_max = 0
    center_hard = base_lock >= 0.98
    for raw, out, plate, alpha in zip(frames, encoded, warped_plates, alpha_masks):
        raw_gold = gold_mask(raw) > 0
        source_gold = gold_mask(plate, value_floor=28) > 0
        strong = (alpha >= 0.95) & (~source_gold) & (~raw_gold)
        gray_out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        gray_plate = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        corr = edge_correlation(gray_out, gray_plate, strong.astype(np.uint8) * 255)
        if math.isfinite(corr):
            edge_correlations.append(corr)
        ssim = ssim_map(gray_out, gray_plate)
        if int(strong.sum()) > 100:
            center_ssim.append(float(np.mean(ssim[strong])))

        if int(raw_gold.sum()) > 50:
            raw_luma = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)[raw_gold].astype(np.float32)
            out_luma = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)[raw_gold].astype(np.float32)
            gold_mean_delta.append(float(abs(np.mean(out_luma) - np.mean(raw_luma)) / max(np.mean(raw_luma), 1e-6)))
            gold_p99_delta.append(float(abs(np.percentile(out_luma, 99) - np.percentile(raw_luma, 99)) / max(np.percentile(raw_luma, 99), 1e-6)))

        output_gold = gold_mask(out) > 0
        allowed = cv2.dilate(raw_gold.astype(np.uint8), np.ones((5, 5), np.uint8), iterations=1) > 0
        novel = (output_gold & (~allowed) & center_hard).astype(np.uint8)
        components, _, stats, _ = cv2.connectedComponentsWithStats(novel, 8)
        if components > 1:
            new_gold_component_max = max(new_gold_component_max, int(np.max(stats[1:, cv2.CC_STAT_AREA])))

    flow_difference, flow_cosine = external_flow_metrics(frames, encoded, alpha_masks)

    zone_center = np.zeros((height, width), np.uint8)
    zone_sky = np.zeros((height, width), np.uint8)
    zone_road = np.zeros((height, width), np.uint8)
    zone_edges = np.zeros((height, width), np.uint8)
    cv2.rectangle(zone_center, (round(width * 0.30), 0), (round(width * 0.70), round(height * 0.72)), 255, -1)
    cv2.rectangle(zone_sky, (round(width * 0.30), round(height * 0.05)), (round(width * 0.70), round(height * 0.42)), 255, -1)
    cv2.rectangle(zone_road, (0, round(height * 0.72)), (width - 1, height - 1), 255, -1)
    cv2.rectangle(zone_edges, (0, 0), (round(width * 0.20), height - 1), 255, -1)
    cv2.rectangle(zone_edges, (round(width * 0.80), 0), (width - 1, height - 1), 255, -1)
    sample = encoded[10:121]
    zone_cv = {
        "center": coefficient_of_variation([zone_metric(frame, zone_center) for frame in sample]),
        "sky": coefficient_of_variation([zone_metric(frame, zone_sky) for frame in sample]),
        "road": coefficient_of_variation([zone_metric(frame, zone_road) for frame in sample]),
        "edges": coefficient_of_variation([zone_metric(frame, zone_edges) for frame in sample]),
    }

    valid_tracking_errors = [value for value in finite_errors if math.isfinite(value)]
    objective_gates = {
        "native_121f_30fps": len(encoded) == 121 and abs(encoded_fps - 30.0) <= 0.01,
        "source_hash_exact": source_hash == EXPECTED_SOURCE_SHA256,
        "input_hash_exact": input_hash == EXPECTED_INPUT_SHA256,
        "source_registration_median_le_1px": registration_error <= 1.0,
        "tracking_median_le_1px": float(np.median(valid_tracking_errors)) <= 1.0,
        "tracking_p95_le_2_5px": float(np.percentile(valid_tracking_errors, 95)) <= 2.5,
        "center_edge_correlation_ge_0_70": float(np.median(edge_correlations)) >= 0.70,
        "center_ssim_ge_0_60": float(np.median(center_ssim)) >= 0.60,
        "gold_mean_delta_le_3pct": float(max(gold_mean_delta, default=0.0)) <= 0.03,
        "gold_p99_delta_le_2pct": float(max(gold_p99_delta, default=0.0)) <= 0.02,
        "new_central_gold_component_le_12px": new_gold_component_max <= 12,
        "seam_gradient_excess_p95_le_5pct": float(max(seam_excess, default=0.0)) <= 0.05,
        "external_geometry_not_warped": True,
        "external_flow_magnitude_difference_le_3pct": flow_difference <= 0.03,
        "external_flow_cosine_ge_0_98": flow_cosine >= 0.98,
    }

    input_probe = ffprobe(input_path)
    output_probe = ffprobe(output)
    input_audio = [stream for stream in input_probe.get("streams", []) if stream.get("codec_type") == "audio"]
    output_audio = [stream for stream in output_probe.get("streams", []) if stream.get("codec_type") == "audio"]
    objective_gates["audio_stream_count_preserved"] = len(input_audio) == len(output_audio)
    all_passed = all(objective_gates.values())

    contact_full = output.with_name(output.stem + "_gate_12f_3x4.png")
    contact_center = output.with_name(output.stem + "_center_lock_12f_3x4.png")
    make_contact_sheet(encoded, contact_full)
    make_contact_sheet(
        encoded,
        contact_center,
        (round(width * 0.20), 0, round(width * 0.80), round(height * 0.82)),
    )

    final_transform = transforms[-1]
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "take07_spatial_linear_exposure_and_distant_center_source_lock",
        "created_at": datetime.now().astimezone().isoformat(),
        "input": str(input_path),
        "input_sha256": input_hash,
        "approved_source": str(source_path),
        "approved_source_sha256": source_hash,
        "output": str(output),
        "output_sha256": sha256(output),
        "frames": len(encoded),
        "fps": encoded_fps,
        "duration_seconds": len(encoded) / encoded_fps,
        "width": encoded_width,
        "height": encoded_height,
        "encoder": "h264_nvenc_yuv420p_full_range",
        "audio_streams_input": len(input_audio),
        "audio_streams_output": len(output_audio),
        "approved_source_registration_inliers": registration_inliers,
        "approved_source_registration_reprojection_median_px": registration_error,
        "approved_source_plate_channel_gain_bgr_linear": channel_gain.tolist(),
        "tracking_region": {"x0_fraction": 0.35, "x1_fraction": 0.65, "y0_fraction": 0.40, "y1_fraction": 0.72},
        "tracking_inliers_min": int(min(nonzero_inliers)),
        "tracking_inliers_median": float(np.median(nonzero_inliers)),
        "tracking_reprojection_median_px": float(np.median(valid_tracking_errors)),
        "tracking_reprojection_p95_px": float(np.percentile(valid_tracking_errors, 95)),
        "tracking_fallback_frames": fallback_count,
        "tracking_final_affine": final_transform.tolist(),
        "center_lock": {
            "core_x_fraction": [0.30, 0.70],
            "core_y_fraction": [0.0, 0.72],
            "lateral_feather_px": 48,
            "bottom_feather_to_y_fraction": 0.82,
            "road_below_y_fraction_locked": False,
            "source_gold_excluded": True,
            "raw_gold_recomposed": True,
            "gold_codec_compensation": "BGR + 2.0 + 0.008*luma on hard RAW-gold pixels before YUV420 encode",
            "maximum_alpha_fraction": float(max(np.mean(alpha >= 0.01) for alpha in alpha_masks)),
        },
        "exposure": {
            "domain": "linear_bt709_from_srgb",
            "curve_frames": CURVE_FRAMES.astype(int).tolist(),
            "center_stops": CURVE_CENTER.tolist(),
            "edge_stops": CURVE_EDGES.tolist(),
            "road_stops": CURVE_ROAD.tolist(),
            "full_gain_below_linear_y": 0.025,
            "gain_fades_to_zero_at_linear_y": 0.12,
            "maximum_clipped_pixel_fraction": float(max(clipping)),
            "zone_luma_cv_frames_10_120": zone_cv,
        },
        "gold_preservation": {
            "maximum_mean_luma_delta_fraction": float(max(gold_mean_delta, default=0.0)),
            "maximum_p99_luma_delta_fraction": float(max(gold_p99_delta, default=0.0)),
            "maximum_new_central_component_area_px": new_gold_component_max,
        },
        "center_fidelity": {
            "edge_correlation_median": float(np.median(edge_correlations)),
            "edge_correlation_min": float(np.min(edge_correlations)),
            "ssim_median": float(np.median(center_ssim)),
            "ssim_min": float(np.min(center_ssim)),
        },
        "seam_gradient_excess_p95_max_fraction": float(max(seam_excess, default=0.0)),
        "external_motion": {
            "geometry_warp_applied_outside_center": False,
            "klt_median_relative_magnitude_difference": flow_difference,
            "klt_median_cosine": flow_cosine,
            "note": "Fluxo e diagnostico fotometrico; a operacao externa altera apenas luz, nunca coordenadas.",
        },
        "contacts": {"full": str(contact_full), "center_lock": str(contact_center)},
        "objective_gates": objective_gates,
        "validation_status": "objective_qc_passed_pending_visual_qc" if all_passed else "objective_qc_failed_do_not_upscale",
        "publication_authorized": False,
        "hd_authorized": False,
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--approved-source", type=Path, required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--expected-input-sha256", default=EXPECTED_INPUT_SHA256)
    parser.add_argument("--expected-source-sha256", default=EXPECTED_SOURCE_SHA256)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    print(json.dumps(run(parse_args()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
