#!/usr/bin/env python3
"""Build the corrected owner-reviewable Fusion Dance motion reference.

This is motion reference only. It follows the owner-supplied Goku demonstration
and stops on two simultaneous mirrored fingertip contacts. It contains no
fusion, character appearance, camera motion, face transfer or transformation.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 720
HEIGHT = 1280
FPS = 30
FRAMES = 109  # 4n+1; (109 - 1) / 30 = 3.6 s on the pose timeline.
PROJECT = Path(__file__).resolve().parents[1] / "projetos" / "gogeta_fusao_single_take_15s_v2"
OUT_DIR = PROJECT / "motion_driver_v3"
POSE_VIDEO = OUT_DIR / "gogeta_fusion_dance_dwpose_v3_109f_720x1280p30.mp4"
REVIEW_VIDEO = OUT_DIR / "gogeta_fusion_dance_dwpose_v3_review_109f_720x1280p30.mp4"
CONTACT_SHEET = OUT_DIR / "gogeta_fusion_dance_dwpose_v3_contact_sheet.jpg"
MANIFEST = OUT_DIR / "gogeta_fusion_dance_dwpose_v3.json"
REFERENCE_STORYBOARD = Path(
    r"E:\Pemara\.codex-remote-attachments\01a00b36-5a01-7dd2-a34a-8778812671f3"
    r"\4bc0d9ad-dee2-423c-b56b-0239184a58f1\1-Photo-1.jpg"
)
LOCAL_REFERENCE_STORYBOARD = OUT_DIR / "reference_storyboard_owner_supplied.jpg"
LOCAL_SOURCE_VIDEO = PROJECT / "references" / "goku_fusion_dance_source_WNQm4HxcaZY.mp4"

BODY_EDGES = (
    ("head", "neck"),
    ("neck", "left_shoulder"), ("neck", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("left_wrist", "left_index"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("right_wrist", "right_index"),
    ("neck", "hip_center"),
    ("hip_center", "left_hip"), ("hip_center", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
)

KEY_TIMES = (0.0, 0.58, 1.16, 1.78, 2.35, 2.92, 3.6)
KEY_LABELS = (
    "FU — braços horizontais para fora",
    "FU — passo 1 e arco ascendente",
    "FU — passo 2, braços sobre a cabeça",
    "SION — passo 3, braços retornam para fora",
    "SION — joelho externo sobe; braços em oposição",
    "HA — inclinação simétrica começa",
    "HA — DOIS pares de indicadores tocam; pernas externas estendidas",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def lerp_pose(a, b, amount: float):
    amount = smooth(amount)
    return {
        key: (
            a[key][0] + (b[key][0] - a[key][0]) * amount,
            a[key][1] + (b[key][1] - a[key][1]) * amount,
        )
        for key in a
    }


def mirror(pose):
    swap = {
        "left_shoulder": "right_shoulder", "right_shoulder": "left_shoulder",
        "left_elbow": "right_elbow", "right_elbow": "left_elbow",
        "left_wrist": "right_wrist", "right_wrist": "left_wrist",
        "left_index": "right_index", "right_index": "left_index",
        "left_hip": "right_hip", "right_hip": "left_hip",
        "left_knee": "right_knee", "right_knee": "left_knee",
        "left_ankle": "right_ankle", "right_ankle": "left_ankle",
    }
    return {swap.get(name, name): (WIDTH - xy[0], xy[1]) for name, xy in pose.items()}


def pose(cx: float, *, arms: str, feet: str = "wide"):
    base = {
        "head": (cx, 455), "neck": (cx, 515),
        "left_shoulder": (cx - 42, 540), "right_shoulder": (cx + 42, 540),
        "hip_center": (cx, 770), "left_hip": (cx - 30, 770), "right_hip": (cx + 30, 770),
        "left_knee": (cx - 35, 915), "left_ankle": (cx - 48, 1070),
        "right_knee": (cx + 35, 915), "right_ankle": (cx + 48, 1070),
    }
    if arms == "outward":
        base.update({
            "left_elbow": (cx - 105, 545), "left_wrist": (cx - 160, 545), "left_index": (cx - 188, 545),
            "right_elbow": (cx - 28, 590), "right_wrist": (cx - 105, 600), "right_index": (cx - 136, 600),
        })
    elif arms == "rising":
        base.update({
            "left_elbow": (cx - 96, 500), "left_wrist": (cx - 116, 425), "left_index": (cx - 112, 394),
            "right_elbow": (cx - 5, 480), "right_wrist": (cx - 35, 405), "right_index": (cx - 28, 374),
        })
    elif arms == "overhead":
        base.update({
            "left_elbow": (cx - 48, 455), "left_wrist": (cx - 10, 370), "left_index": (cx + 2, 342),
            "right_elbow": (cx + 36, 455), "right_wrist": (cx + 68, 380), "right_index": (cx + 78, 350),
        })
    elif arms == "opposition":
        base.update({
            "left_elbow": (cx - 102, 555), "left_wrist": (cx - 165, 555), "left_index": (cx - 195, 555),
            "right_elbow": (cx - 22, 610), "right_wrist": (cx - 104, 625), "right_index": (cx - 134, 625),
        })
    else:
        raise ValueError(arms)
    if feet == "step_left":
        base.update({"left_knee": (cx - 8, 920), "left_ankle": (cx + 25, 1065)})
    elif feet == "step_right":
        base.update({"right_knee": (cx + 7, 920), "right_ankle": (cx - 22, 1065)})
    elif feet == "outer_knee_up":
        base.update({"left_knee": (cx - 75, 820), "left_ankle": (cx - 10, 845)})
    return base


def final_left():
    # Owner-confirmed end: both mirrored index pairs meet simultaneously.
    return {
        "head": (286, 560), "neck": (276, 620),
        "left_shoulder": (238, 642), "right_shoulder": (309, 650),
        "left_elbow": (226, 512), "left_wrist": (288, 450), "left_index": (360, 452),
        "right_elbow": (306, 710), "right_wrist": (337, 690), "right_index": (360, 690),
        "hip_center": (270, 785), "left_hip": (241, 782), "right_hip": (296, 790),
        "left_knee": (196, 900), "left_ankle": (105, 1055),
        "right_knee": (316, 920), "right_ankle": (330, 1070),
    }


KEY_POSES = (
    pose(175, arms="outward"),
    pose(205, arms="rising", feet="step_left"),
    pose(235, arms="overhead", feet="step_right"),
    pose(260, arms="outward", feet="step_left"),
    pose(278, arms="opposition", feet="outer_knee_up"),
    lerp_pose(pose(278, arms="opposition", feet="outer_knee_up"), final_left(), 0.52),
    final_left(),
)


def timeline(seconds: float):
    for index in range(len(KEY_TIMES) - 1):
        if seconds <= KEY_TIMES[index + 1]:
            span = KEY_TIMES[index + 1] - KEY_TIMES[index]
            amount = (seconds - KEY_TIMES[index]) / span
            return index, lerp_pose(KEY_POSES[index], KEY_POSES[index + 1], amount)
    return len(KEY_TIMES) - 2, KEY_POSES[-1]


def font(size: int):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def draw_hand(draw, wrist, index, color):
    dx, dy = index[0] - wrist[0], index[1] - wrist[1]
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    # Five short rays make hand tracking explicit while preserving one index tip.
    for spread in (-2, -1, 0, 1, 2):
        tip = (index[0] + nx * spread * 5, index[1] + ny * spread * 5)
        draw.line((wrist, tip), fill=color, width=3)
        draw.ellipse((tip[0]-3, tip[1]-3, tip[0]+3, tip[1]+3), fill=color)


def draw_actor(draw, points, color):
    for start, end in BODY_EDGES:
        draw.line((points[start], points[end]), fill=color, width=7, joint="curve")
    for point in points.values():
        draw.ellipse((point[0]-6, point[1]-6, point[0]+6, point[1]+6), fill=color)
    head = points["head"]
    draw.ellipse((head[0]-25, head[1]-30, head[0]+25, head[1]+30), outline=color, width=6)
    draw_hand(draw, points["left_wrist"], points["left_index"], color)
    draw_hand(draw, points["right_wrist"], points["right_index"], color)


def render_frame(frame_index: int, *, review: bool):
    seconds = frame_index / FPS
    stage_index, left = timeline(seconds)
    right = mirror(left)
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    if review:
        for y in range(760, HEIGHT, 70):
            draw.line((50, y, WIDTH - 50, y), fill=(24, 31, 45), width=2)
        draw.line((WIDTH // 2, 145, WIDTH // 2, 1110), fill=(40, 50, 70), width=2)
        draw.line((50, 1070, WIDTH - 50, 1070), fill=(70, 82, 105), width=3)
    draw_actor(draw, left, (255, 120, 35))
    draw_actor(draw, right, (35, 160, 255))
    contact_pairs = (
        (left["left_index"], right["right_index"]),
        (left["right_index"], right["left_index"]),
    )
    contact_distances = [math.dist(a, b) for a, b in contact_pairs]
    contact_count = sum(distance < 18 for distance in contact_distances)
    for (a, b), distance in zip(contact_pairs, contact_distances):
        if distance < 18:
            cx = (a[0] + b[0]) / 2
            cy = (a[1] + b[1]) / 2
            draw.ellipse((cx-8, cy-8, cx+8, cy+8), fill=(255, 245, 180))
    if review:
        draw.text((24, 24), "PRÉVIA DE POSE V3 · ROSTO OFF · CÂMERA FIXA", font=font(20), fill="white")
        label = KEY_LABELS[min(stage_index + 1, len(KEY_LABELS) - 1)]
        draw.text((24, 64), label, font=font(24), fill="white")
        draw.text((24, 1120), f"{seconds:04.2f}s / 3.60s · contatos: {contact_count}/2", font=font(20), fill=(210, 220, 238))
        draw.text((24, 1154), "Revisar: 3 passos, arco contínuo, joelho externo, inclinação e DOIS contatos.", font=font(18), fill=(210, 220, 238))
        draw.rectangle((24, 1210, WIDTH - 24, 1228), fill=(35, 42, 58))
        draw.rectangle((24, 1210, 24 + int((WIDTH - 48) * frame_index / (FRAMES - 1)), 1228), fill=(245, 170, 48))
    return image


def encode(path: Path, *, review: bool):
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "h264_nvenc",
        "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    for frame_index in range(FRAMES):
        process.stdin.write(render_frame(frame_index, review=review).tobytes())
    process.stdin.close()
    if process.wait():
        raise RuntimeError(f"NVENC failed for {path.name}")


def make_contact_sheet():
    indices = [round(value * (FRAMES - 1) / 11) for value in range(12)]
    thumbs = []
    for index in indices:
        frame = render_frame(index, review=True)
        frame.thumbnail((240, 427), Image.Resampling.LANCZOS)
        thumbs.append(frame)
    sheet = Image.new("RGB", (960, 1281), (7, 9, 15))
    for i, frame in enumerate(thumbs):
        x = (i % 4) * 240
        y = (i // 4) * 427
        sheet.paste(frame, (x, y))
    sheet.save(CONTACT_SHEET, quality=94, subsampling=0)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if REFERENCE_STORYBOARD.is_file():
        shutil.copy2(REFERENCE_STORYBOARD, LOCAL_REFERENCE_STORYBOARD)
    encode(POSE_VIDEO, review=False)
    encode(REVIEW_VIDEO, review=True)
    make_contact_sheet()
    record = {
        "schema_version": "3.0",
        "project_id": "gogeta_fusao_single_take_15s_v2",
        "asset_type": "dwpose_pose_video",
        "source_driver_kind": "synthetic_kinematic_pose_sequence",
        "status": "PENDING_HUMAN_REVIEW",
        "is_dwpose": True,
        "is_exact_pose_control": False,
        "is_motion_reference": True,
        "target_render_engine": "MiniMax H3 REF2VA",
        "is_synthetic_pose": True,
        "face_transfer": "disabled",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": str(POSE_VIDEO),
        "sha256": sha256(POSE_VIDEO),
        "review_file": str(REVIEW_VIDEO),
        "review_sha256": sha256(REVIEW_VIDEO),
        "contact_sheet": str(CONTACT_SHEET),
        "contact_sheet_sha256": sha256(CONTACT_SHEET),
        "reference_storyboard": str(LOCAL_REFERENCE_STORYBOARD),
        "reference_storyboard_sha256": sha256(LOCAL_REFERENCE_STORYBOARD) if LOCAL_REFERENCE_STORYBOARD.is_file() else "",
        "owner_supplied_source_video": str(LOCAL_SOURCE_VIDEO),
        "owner_supplied_source_video_sha256": sha256(LOCAL_SOURCE_VIDEO) if LOCAL_SOURCE_VIDEO.is_file() else "",
        "width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES,
        "motion_timeline_seconds": (FRAMES - 1) / FPS,
        "encoder": "h264_nvenc",
        "camera": "fixed_for_pose_review",
        "canonical_corrections": {
            "fingertip_contacts": 2,
            "contacts": "upper_and_lower_mirrored_index_pairs_simultaneous",
            "driver_scope": "dance_only",
            "fusion_and_transformation_excluded": True,
        },
        "beats": [
            {"start": 0.0, "end": 1.78, "event": "three mirrored lateral steps while both arms complete one continuous overhead arc"},
            {"start": 1.78, "end": 2.35, "event": "arms return outward and each outer knee rises"},
            {"start": 2.35, "end": 3.6, "event": "mirrored inward lean, outer legs extend, upper and lower mirrored index pairs meet simultaneously"},
        ],
        "production_generation_authorized": False,
        "next_gate": "OWNER_APPROVAL_OF_SYNTHETIC_DWPOSE_PREVIEW",
    }
    MANIFEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(REVIEW_VIDEO)


if __name__ == "__main__":
    main()
