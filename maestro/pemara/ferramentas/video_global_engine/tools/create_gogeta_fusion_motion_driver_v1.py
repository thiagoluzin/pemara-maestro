#!/usr/bin/env python3
"""Create a deterministic pose-blocking preview for the corrected Gogeta shot.

This is a review asset only. It contains no face transfer and is not a final render.
"""

from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 720
HEIGHT = 1280
FPS = 30
FRAMES = 451  # (451 - 1) / 30 == 15.0 seconds on the motion timeline.
PROJECT = Path(__file__).resolve().parents[1] / "projetos" / "gogeta_fusao_single_take_15s_v2"
OUT_DIR = PROJECT / "motion_driver_v1"
OUT_VIDEO = OUT_DIR / "driver_gogeta_fusion_blocking_v01_451f_720x1280p30.mp4"
OUT_META = OUT_VIDEO.with_suffix(".json")

LIMBS = (
    ("head", "neck"),
    ("left_shoulder", "right_shoulder"),
    ("neck", "hip_center"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("left_wrist", "left_index"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("right_wrist", "right_index"),
    ("hip_center", "left_hip"),
    ("hip_center", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def interpolate(a: dict[str, tuple[float, float]], b: dict[str, tuple[float, float]], amount: float):
    amount = ease(amount)
    return {
        name: (
            a[name][0] + (b[name][0] - a[name][0]) * amount,
            a[name][1] + (b[name][1] - a[name][1]) * amount,
        )
        for name in a
    }


def mirror_pose(pose: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
    swap = {
        "left_shoulder": "right_shoulder",
        "right_shoulder": "left_shoulder",
        "left_elbow": "right_elbow",
        "right_elbow": "left_elbow",
        "left_wrist": "right_wrist",
        "right_wrist": "left_wrist",
        "left_index": "right_index",
        "right_index": "left_index",
        "left_hip": "right_hip",
        "right_hip": "left_hip",
        "left_knee": "right_knee",
        "right_knee": "left_knee",
        "left_ankle": "right_ankle",
        "right_ankle": "left_ankle",
    }
    return {
        swap.get(name, name): (WIDTH - point[0], point[1])
        for name, point in pose.items()
    }


def start_left(cx: float = 190.0) -> dict[str, tuple[float, float]]:
    return {
        "head": (cx, 505), "neck": (cx, 565),
        "left_shoulder": (cx - 42, 585), "right_shoulder": (cx + 42, 585),
        "left_elbow": (cx - 102, 588), "left_wrist": (cx - 150, 588), "left_index": (cx - 178, 588),
        "right_elbow": (cx - 25, 630), "right_wrist": (cx - 112, 640), "right_index": (cx - 176, 640),
        "hip_center": (cx, 790), "left_hip": (cx - 30, 790), "right_hip": (cx + 30, 790),
        "left_knee": (cx - 38, 930), "left_ankle": (cx - 54, 1080),
        "right_knee": (cx + 36, 930), "right_ankle": (cx + 52, 1080),
    }


def step_left(index: int) -> dict[str, tuple[float, float]]:
    centers = (190, 225, 260, 290)
    cx = centers[index]
    pose = start_left(cx)
    if index == 1:
        pose.update({
            "left_elbow": (cx - 84, 535), "left_wrist": (cx - 105, 475), "left_index": (cx - 112, 452),
            "right_elbow": (cx + 8, 525), "right_wrist": (cx - 35, 455), "right_index": (cx - 48, 435),
            "left_knee": (cx - 15, 935), "left_ankle": (cx + 12, 1075),
        })
    elif index == 2:
        pose.update({
            "left_elbow": (cx - 40, 505), "left_wrist": (cx - 12, 430), "left_index": (cx, 408),
            "right_elbow": (cx + 35, 505), "right_wrist": (cx + 60, 430), "right_index": (cx + 72, 408),
            "right_knee": (cx + 10, 935), "right_ankle": (cx - 15, 1075),
        })
    elif index == 3:
        # SION beat: fists point away while the outer knee rises toward center.
        pose.update({
            "left_elbow": (cx - 90, 620), "left_wrist": (cx - 145, 620), "left_index": (cx - 165, 620),
            "right_elbow": (cx - 10, 650), "right_wrist": (cx - 92, 665), "right_index": (cx - 112, 665),
            "left_knee": (cx + 28, 865), "left_ankle": (cx + 72, 895),
            "right_knee": (cx + 28, 935), "right_ankle": (cx + 48, 1080),
        })
    return pose


def hah_left() -> dict[str, tuple[float, float]]:
    return {
        "head": (292, 620), "neck": (278, 672),
        "left_shoulder": (246, 682), "right_shoulder": (310, 690),
        "left_elbow": (238, 545), "left_wrist": (322, 502), "left_index": (360, 500),
        "right_elbow": (298, 740), "right_wrist": (334, 694), "right_index": (360, 690),
        "hip_center": (270, 810), "left_hip": (245, 805), "right_hip": (292, 812),
        "left_knee": (205, 900), "left_ankle": (112, 1025),
        "right_knee": (315, 925), "right_ankle": (328, 1075),
    }


def kneel_pose() -> dict[str, tuple[float, float]]:
    return {
        "head": (360, 575), "neck": (360, 635),
        "left_shoulder": (310, 655), "right_shoulder": (410, 655),
        "left_elbow": (300, 780), "left_wrist": (325, 925), "left_index": (330, 955),
        "right_elbow": (455, 705), "right_wrist": (472, 775), "right_index": (480, 795),
        "hip_center": (365, 805), "left_hip": (330, 805), "right_hip": (400, 805),
        "left_knee": (300, 980), "left_ankle": (285, 1080),
        "right_knee": (455, 900), "right_ankle": (480, 1080),
    }


def rise_pose() -> dict[str, tuple[float, float]]:
    return {
        "head": (360, 515), "neck": (360, 575),
        "left_shoulder": (310, 600), "right_shoulder": (410, 600),
        "left_elbow": (285, 705), "left_wrist": (300, 785), "left_index": (304, 805),
        "right_elbow": (435, 705), "right_wrist": (420, 785), "right_index": (416, 805),
        "hip_center": (360, 790), "left_hip": (325, 790), "right_hip": (395, 790),
        "left_knee": (295, 930), "left_ankle": (250, 1080),
        "right_knee": (425, 930), "right_ankle": (470, 1080),
    }


def charge_pose() -> dict[str, tuple[float, float]]:
    return {
        "head": (360, 500), "neck": (360, 560),
        "left_shoulder": (300, 595), "right_shoulder": (420, 595),
        "left_elbow": (275, 690), "left_wrist": (300, 770), "left_index": (305, 790),
        "right_elbow": (445, 690), "right_wrist": (420, 770), "right_index": (415, 790),
        "hip_center": (360, 790), "left_hip": (315, 790), "right_hip": (405, 790),
        "left_knee": (270, 925), "left_ankle": (185, 1080),
        "right_knee": (450, 925), "right_ankle": (535, 1080),
    }


def transform_pose(pose: dict[str, tuple[float, float]], *, dx: float = 0, dy: float = 0, scale: float = 1.0):
    return {
        key: ((x - 360) * scale + 360 + dx, (y - 760) * scale + 760 + dy)
        for key, (x, y) in pose.items()
    }


def timeline_pose(seconds: float):
    if seconds < 1.0:
        amount = seconds / 1.0
        left = interpolate(step_left(0), step_left(1), amount)
        return "FU · passo lateral 1/3 + braços iniciam arco", left, mirror_pose(left), None
    if seconds < 2.0:
        amount = (seconds - 1.0) / 1.0
        left = interpolate(step_left(1), step_left(2), amount)
        return "FU · passo lateral 2/3 + braços sobre a cabeça", left, mirror_pose(left), None
    if seconds < 3.2:
        amount = (seconds - 2.0) / 1.2
        left = interpolate(step_left(2), step_left(3), amount)
        return "SION · passo 3/3 + joelhos e braços em oposição", left, mirror_pose(left), None
    if seconds < 4.5:
        amount = (seconds - 3.2) / 1.3
        left = interpolate(step_left(3), hah_left(), amount)
        return "HAH · inclinação espelhada + dois contatos de indicadores", left, mirror_pose(left), None
    if seconds < 6.6:
        amount = (seconds - 4.5) / 2.1
        angle = amount * math.tau * 0.55
        scale = 1.0 - 0.62 * ease(amount)
        spread = 1.0 - 0.84 * ease(amount)
        left = transform_pose(hah_left(), dx=(1 - spread) * 66 + math.sin(angle) * 22, dy=math.cos(angle) * 18, scale=scale)
        right = mirror_pose(transform_pose(hah_left(), dx=(1 - spread) * 66 + math.sin(angle) * 22, dy=math.cos(angle) * 18, scale=scale))
        return "FUSÃO · duas silhuetas continuam visíveis e comprimem em uma", left, right, amount
    if seconds < 7.6:
        return "GOGETA BASE · emerge ajoelhado, cabelo preto", None, None, kneel_pose()
    if seconds < 9.5:
        amount = (seconds - 7.6) / 1.9
        return "GOGETA BASE · levanta e estabiliza o corpo", None, None, interpolate(kneel_pose(), rise_pose(), amount)
    if seconds < 12.5:
        amount = (seconds - 9.5) / 3.0
        pose = interpolate(rise_pose(), charge_pose(), min(1.0, amount * 1.4))
        tremor = math.sin(seconds * 38.0) * (1.5 + amount * 2.5)
        pose = transform_pose(pose, dx=tremor)
        return "CARGA DE KI · cabelo ainda PRETO; pressão cresce", None, None, pose
    amount = (seconds - 12.5) / 2.5
    pose = transform_pose(charge_pose(), dy=-10 * ease(amount), scale=1.0 + 0.04 * ease(amount))
    return "TRANSFORMAÇÃO · dourado e explosão começam JUNTOS", None, None, pose


def draw_pose(draw: ImageDraw.ImageDraw, pose: dict[str, tuple[float, float]], color, *, alpha: int = 255, gold_hair: bool = False):
    line_color = (*color, alpha)
    for start, end in LIMBS:
        draw.line((pose[start], pose[end]), fill=line_color, width=8, joint="curve")
    for name, point in pose.items():
        radius = 8 if name not in {"left_index", "right_index"} else 5
        draw.ellipse((point[0]-radius, point[1]-radius, point[0]+radius, point[1]+radius), fill=line_color)
    head = pose["head"]
    draw.ellipse((head[0]-27, head[1]-31, head[0]+27, head[1]+31), outline=line_color, width=7)
    hair_color = (255, 214, 74, alpha) if gold_hair else (*color, alpha)
    for offset in (-24, -12, 0, 12, 24):
        draw.line((head[0] + offset * 0.45, head[1] - 27, head[0] + offset, head[1] - 66 - abs(offset) * 0.35), fill=hair_color, width=6)


def draw_aura(draw: ImageDraw.ImageDraw, center, radius: float, color, alpha: int):
    x, y = center
    for multiplier, width in ((1.0, 6), (0.78, 3), (1.18, 2)):
        r = radius * multiplier
        draw.ellipse((x-r, y-r*1.25, x+r, y+r*1.25), outline=(*color, alpha), width=width)


def load_font(size: int):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def frame_image(frame_index: int) -> Image.Image:
    seconds = min(15.0, frame_index / FPS)
    stage, left, right, merged = timeline_pose(seconds)
    image = Image.new("RGB", (WIDTH, HEIGHT), (5, 8, 15))
    draw = ImageDraw.Draw(image, "RGBA")

    # Stable-camera review grid: the body motion is judged without camera disguise.
    for y in range(760, HEIGHT, 65):
        draw.line((60, y, WIDTH-60, y), fill=(45, 58, 75, 120), width=2)
    draw.line((WIDTH//2, 150, WIDTH//2, 1160), fill=(80, 92, 112, 110), width=2)
    draw.line((60, 1085, WIDTH-60, 1085), fill=(100, 115, 135, 180), width=3)

    if left is not None and right is not None:
        fusion_amount = 0.0 if seconds < 4.5 else min(1.0, (seconds - 4.5) / 2.1)
        alpha = int(255 - fusion_amount * 105)
        draw_pose(draw, left, (255, 138, 50), alpha=alpha)
        draw_pose(draw, right, (60, 165, 255), alpha=alpha)
        if seconds >= 3.9:
            for point in ((360, 500), (360, 690)):
                radius = 8 + 12 * fusion_amount + math.sin(seconds * 18) * 3
                draw.ellipse((point[0]-radius, point[1]-radius, point[0]+radius, point[1]+radius), fill=(255, 245, 190, 235))
        if seconds >= 4.5:
            radius = 95 + fusion_amount * 115
            draw_aura(draw, (360, 720), radius, (190, 100, 255), 150)
    elif merged is not None:
        is_gold = seconds >= 12.5
        if seconds >= 9.5:
            amount = min(1.0, max(0.0, (seconds - 9.5) / 3.0))
            draw_aura(draw, (360, 760), 150 + 55 * amount, (120, 205, 255), 120)
            for index in range(16):
                angle = (index / 16) * math.tau + seconds * 0.35
                radius = 85 + amount * 170
                x = 360 + math.cos(angle) * radius
                y = 800 + math.sin(angle) * radius * 0.7
                draw.ellipse((x-5, y-5, x+5, y+5), fill=(170, 215, 255, 170))
        if is_gold:
            amount = min(1.0, (seconds - 12.5) / 2.5)
            draw_aura(draw, (360, 750), 210 + 190 * ease(amount), (255, 205, 55), 210)
            for index in range(24):
                angle = (index / 24) * math.tau
                inner = 150 + 45 * amount
                outer = inner + 110 + 150 * amount
                draw.line((360 + math.cos(angle)*inner, 760 + math.sin(angle)*inner,
                           360 + math.cos(angle)*outer, 760 + math.sin(angle)*outer),
                          fill=(255, 214, 70, 140), width=4)
        draw_pose(draw, merged, (235, 240, 248) if not is_gold else (255, 204, 65), gold_hair=is_gold)

    title_font = load_font(27)
    small_font = load_font(20)
    draw.text((28, 28), "DRIVER DE POSE V1 · ROSTO OFF · CÂMERA ESTÁVEL", font=small_font, fill=(215, 225, 240, 255))
    draw.text((28, 72), stage, font=title_font, fill=(255, 255, 255, 255))
    draw.text((28, 1120), f"{seconds:05.2f}s / 15.00s", font=small_font, fill=(190, 205, 225, 255))
    draw.text((28, 1154), "Revisar: passos, arco dos braços, joelho, HAH duplo, 2→1, carga preta, explosão dourada.", font=small_font, fill=(190, 205, 225, 255))
    bar_left, bar_top, bar_right = 28, 1210, WIDTH - 28
    draw.rounded_rectangle((bar_left, bar_top, bar_right, bar_top + 18), radius=9, fill=(40, 50, 65, 255))
    progress = seconds / 15.0
    draw.rounded_rectangle((bar_left, bar_top, bar_left + (bar_right-bar_left)*progress, bar_top + 18), radius=9, fill=(240, 170, 55, 255))
    return image


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT_VIDEO),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame_index in range(FRAMES):
            process.stdin.write(frame_image(frame_index).tobytes())
    finally:
        process.stdin.close()
    return_code = process.wait()
    if return_code:
        raise SystemExit(f"ffmpeg NVENC failed with code {return_code}")

    metadata = {
        "schema_version": "1.0",
        "project_id": "gogeta_fusao_single_take_15s_v2",
        "asset_type": "procedural_pose_blocking_preview",
        "status": "PENDING_HUMAN_MOTION_REVIEW",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": str(OUT_VIDEO),
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "frames": FRAMES,
        "motion_timeline_seconds": (FRAMES - 1) / FPS,
        "encoder": "h264_nvenc",
        "face_transfer": "disabled",
        "camera": "stable_for_motion_review",
        "approved_anchor_set": "live_action_v3",
        "beats": [
            {"start": 0.0, "end": 3.2, "event": "three mirrored lateral steps and 180-degree arm sweep"},
            {"start": 3.2, "end": 4.5, "event": "SION knee beat into mirrored HAH with two fingertip contacts"},
            {"start": 4.5, "end": 6.6, "event": "two visible bodies compress into one fusion"},
            {"start": 6.6, "end": 9.5, "event": "base Gogeta emerges kneeling and rises with black hair"},
            {"start": 9.5, "end": 12.5, "event": "Ki charge grows while hair remains black"},
            {"start": 12.5, "end": 15.0, "event": "gold transformation and Ki explosion start together"}
        ],
        "production_generation_authorized": False,
        "next_gate": "OWNER_APPROVAL_OF_MOTION_PREVIEW",
    }
    OUT_META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT_VIDEO)


if __name__ == "__main__":
    main()
