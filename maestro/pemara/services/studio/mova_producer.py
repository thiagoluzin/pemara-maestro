"""Deterministic producer gate for MOVA review takes.

The producer runs without a GPU. It translates prompt intent into the shortest
review duration that still contains action, reaction and a changed ending.
"""

from __future__ import annotations

import math
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np


MOVA_REVIEW_FPS = 24
MOVA_REVIEW_DURATIONS = (4, 5, 6)
MOVA_REVIEW_RESOLUTION = (832, 480)
MOVA_REVIEW_STEPS = 25
MOVA_REQUIRED_DIALOGUE_LOCALE = "pt-BR"
MOVA_FORBIDDEN_DIALOGUE_LOCALES = ("pt-PT",)
MOVA_FINAL_HOLD_SECONDS = 0.75
MOVA_FINAL_HOLD_MAX_LUMA_DELTA = 1.75
MOVA_AUDIO_MIN_LUFS = -28.0
MOVA_AUDIO_MAX_LUFS = -12.0
MOVA_AUDIO_MAX_TRUE_PEAK_DBFS = -1.0
MOVA_VISIBLE_TEXT_MAX_GLYPH_PIXELS = 3500
MOVA_VISIBLE_UI_MAX_NEUTRAL_FRACTION = 0.25
PRODUCER_VERSION = "mova_take_producer_v2_ptbr_motion_gate"


def build_ltx_prompt_contract(
    prompt: str,
    *,
    allowed_humans: List[str] | None = None,
    duration_seconds: float = 0.0,
    distinct_story_events: int = 1,
) -> Dict[str, Any]:
    """Move prohibitions to the true negative channel and lock cast/motion.

    Listing forbidden people inside the positive prompt primes the model with
    exactly those concepts. Project takes therefore replace the legacy HUMAN
    CAST POLICY block with a compact positive cast constraint; detailed
    exclusions are returned for Comfy's real negative conditioning channel.
    Long editorial takes remain continuous, but their motion is budgeted into
    smaller temporal blocks with one dominant event per block.
    """

    source = (prompt or "").strip()
    if not source:
        raise ValueError("Prompt LTX vazio para contrato de producao.")
    cleaned = re.sub(
        r"\bHUMAN CAST POLICY\b.*?\bEND HUMAN CAST POLICY\b\.?",
        " ",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    moved_negative_additions: List[str] = []

    def _move_negative_sentence(match: re.Match[str]) -> str:
        sentence = re.sub(
            r"^(?:no|never|do not)\s+",
            "",
            match.group(1).strip(),
            flags=re.IGNORECASE,
        ).rstrip(". ")
        if sentence:
            moved_negative_additions.append(sentence)
        return " "

    cleaned = re.sub(
        r"(?:^|(?<=[.!?]\s))((?:No|Never|Do not)\s+[^.]{1,500}\.)",
        _move_negative_sentence,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    names = list(dict.fromkeys(
        str(item).strip() for item in (allowed_humans or []) if str(item).strip()
    ))
    cast_contract: Dict[str, Any] = {
        "known": allowed_humans is not None,
        "allowed_humans": names,
        "exact_count": len(names) if allowed_humans is not None else None,
        "one_physical_instance_per_identity": allowed_humans is not None,
        "closed_inventory": allowed_humans is not None,
        "preserve_first_frame_screen_order": allowed_humans is not None,
        "automatic_verification": False,
        "human_review_required": allowed_humans is not None,
    }
    additions: List[str] = list(moved_negative_additions)
    if allowed_humans is not None:
        if names:
            cast_line = (
                f"CAST LOCK: exactly {len(names)} named human subjects remain in the shot from first "
                f"to final frame: {', '.join(names)}. Each name owns one continuous physical body; every "
                "later reference to that name means that same body. Preserve identity, anatomy, wardrobe, "
                "count, proportions, first-frame left-to-right order, facing, action axis and spatial continuity."
            )
        else:
            cast_line = (
                "CAST LOCK: the approved scene contains zero human subjects from first to final frame; "
                "preserve the empty human cast and animate only the approved non-human scene elements."
            )
        additions.extend([
            "unauthorized person",
            "extra person",
            "adult",
            "parent",
            "villager",
            "crowd",
            "background person",
            "human silhouette",
            "human reflection",
            "portrait of a person",
            "statue of a person",
            "duplicate character",
            "same-identity duplicate",
            "second instance of the same identity",
            "third instance of the same identity",
            "clone",
            "twin copy",
            "identity replacement",
            "subject disappearance",
            "subject re-entry",
            "teleportation",
            "dissolve transition",
            "ghosting",
            "motion smear",
            "body merging",
            "extra limb",
            "missing limb",
            "face morph",
            "melting anatomy",
            "hard cut",
            "empty intermediate frame",
            "reverse motion",
            "left-right reversal",
            "screen-side swap",
            "mirrored direction",
            "portal spawning",
            "doorway spawning",
            "reflection spawning",
            "reset to first frame",
            "subtitle",
            "caption",
            "visible text",
            "watermark",
            "interface overlay",
        ])
    else:
        cast_line = ""

    duration = max(0.0, float(duration_seconds or 0.0))
    event_count = max(1, int(distinct_story_events or 1))
    block_count = 2 if duration > 6.0 or event_count > 1 else 1
    motion_blocks: List[Dict[str, Any]] = []
    if duration > 0:
        for index in range(block_count):
            start = duration * index / block_count
            end = duration * (index + 1) / block_count
            motion_blocks.append({
                "index": index + 1,
                "start_seconds": round(start, 2),
                "end_seconds": round(end, 2),
                "max_dominant_events": 1,
            })
    motion_line = ""
    if len(motion_blocks) > 1:
        labels = "; ".join(
            f"block {item['index']} {item['start_seconds']:.2f}-{item['end_seconds']:.2f}s"
            for item in motion_blocks
        )
        motion_line = (
            f"CONTINUOUS MOTION BLOCKS: {labels}. Execute at most one dominant physical event in each "
            "block. Cross each boundary as the same continuous shot, with stable entity slots and identities. "
            "Keep camera direction, geography and the exact cast continuous."
        )

    effective_parts = [cleaned, cast_line, motion_line]
    return {
        "prompt": " ".join(item for item in effective_parts if item).strip(),
        "negative_additions": additions,
        "cast_contract": cast_contract,
        "motion_blocks": motion_blocks,
        "legacy_positive_cast_block_removed": cleaned != source,
        "positive_negative_directives_moved": len(moved_negative_additions),
    }


def build_ltx_negative_prompt(
    negative: str,
    *,
    allowed_humans: List[str] | None,
    additions: List[str],
) -> str:
    """Keep allowed cast names out of classifier-free negative conditioning."""

    parts = [part.strip() for part in (negative or "").split(",") if part.strip()]
    if allowed_humans is not None:
        allowed_name_keys = {
            str(item).strip().casefold()
            for item in allowed_humans
            if str(item).strip()
        }
        parts = [
            part for part in parts
            if "any human other than exactly" not in part.casefold()
            and part.casefold() not in allowed_name_keys
        ]
    parts.extend(str(item).strip() for item in additions if str(item).strip())
    return ", ".join(dict.fromkeys(parts))


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _quoted_dialogue(prompt: str) -> List[str]:
    candidates = re.findall(r'["“”]([^"“”]{2,240})["“”]', prompt or "", flags=re.DOTALL)
    return [re.sub(r"\s+", " ", item).strip() for item in candidates if item.strip()]


def _without_quoted_dialogue(prompt: str) -> str:
    return re.sub(r'["â€œâ€][^"â€œâ€]{2,240}["â€œâ€]', ' "DIALOGUE" ', prompt or "", flags=re.DOTALL)


def _looks_like_portuguese_dialogue(dialogue: List[str], prompt: str) -> bool:
    if not dialogue:
        return False
    plain_prompt = _plain(prompt)
    if re.search(r"\b(portugues|brazilian portuguese|pt[-_ ]?br)\b", plain_prompt):
        return True
    plain_dialogue = _plain(" ".join(dialogue))
    markers = re.findall(
        r"\b(que|quer|para|voce|voces|prefere|continuar|andando|agora|nao|sim|de novo|escutar|olhar)\b",
        plain_dialogue,
    )
    return len(markers) >= 2


def _requests_forbidden_portuguese_locale(prompt: str) -> bool:
    """Detect an affirmative pt-PT request without flagging a prohibition list."""

    positive = re.compile(
        r"\b(?:em|in|speak|speaks|spoken|fale|fala|falado|sotaque|accent)\b.{0,40}"
        r"\b(?:pt[-_ ]?pt|portugues(?:a)?\s+(?:de|from)\s+portugal|european portuguese|portugues europeu)\b"
    )
    for raw_line in (prompt or "").splitlines():
        line = _plain(raw_line)
        if not positive.search(line):
            continue
        if re.search(r"\b(no|not|never|sem|nao|nunca|forbid|forbidden|proibid|bloquead)\w*\b", line):
            continue
        return True
    return False


def _locomotion_directives(prompt: str) -> List[str]:
    """Find positive locomotion instructions outside spoken dialogue/negative lists."""

    detected: List[str] = []
    patterns = {
        "walk": r"\b(walk|walks|walking|stroll|strolls|step|steps|stepping)\b",
        "andar": r"\b(andar|anda|andam|andando|caminh\w*|passo|passos|pisad\w*)\b",
        "body_translation": r"\b(move(?:s|d)?\s+(?:toward|towards|forward|backward)|avanca|avancar|recua|recuar|desloca\w*)\b",
    }
    for raw_line in _without_quoted_dialogue(prompt).splitlines():
        line = _plain(raw_line).strip()
        if not line:
            continue
        if re.search(r"\b(forbidden|proibido|negative|sem|no |nao |never|nunca|do not|nao deve)\b", line):
            continue
        for label, pattern in patterns.items():
            if re.search(pattern, line):
                detected.append(label)
    return sorted(set(detected))


def _explicit_duration(prompt: str) -> float | None:
    plain = _plain(prompt)
    direct = re.findall(
        r"(?:duracao|duration)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:s|sec|second|seconds|segundo|segundos)\b",
        plain,
    )
    if direct:
        return float(direct[-1].replace(",", "."))
    endpoints = [
        float(match.replace(",", "."))
        for match in re.findall(r"\d+(?:[.,]\d+)?\s*[-–]\s*(\d+(?:[.,]\d+)?)", plain)
    ]
    return max(endpoints) if endpoints else None


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ']+\b", text or "", flags=re.UNICODE))


def analyze_mova_take(prompt: str, fps: int = MOVA_REVIEW_FPS) -> Dict[str, Any]:
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("Prompt MOVA vazio para analise do produtor.")

    plain = _plain(prompt)
    dialogue = _quoted_dialogue(prompt)
    portuguese_dialogue = _looks_like_portuguese_dialogue(dialogue, prompt)
    forbidden_locale_requested = _requests_forbidden_portuguese_locale(prompt)
    locomotion_directives = _locomotion_directives(prompt)
    dialogue_words = sum(_word_count(line) for line in dialogue)
    punctuation_pauses = sum(len(re.findall(r"[,;:.!?]", line)) for line in dialogue)
    speech_seconds = (dialogue_words / 2.35) + (punctuation_pauses * 0.16) if dialogue_words else 0.0

    has_action = bool(re.search(r"\b(action|acao|move|walk|andar|oferece|gesto|gesture|turns?|vira|fala|speaks?|articula)\b", plain))
    has_reaction = bool(re.search(r"\b(reaction|reacao|reage|reacts?|espera|waits?|olha|looks?|silencios|gaze|express)\w*\b", plain))
    has_changed_end = bool(re.search(r"\b(changed final|final pose|pose final|payoff|estado final|ends? different|termina diferente|corte)\b", plain))
    has_timing_arc = all(token in plain for token in ("anticipation", "reaction")) or all(
        token in plain for token in ("inicio", "reacao")
    )
    explicit = _explicit_duration(prompt)

    recommended = 4
    reasons: List[str] = []
    if dialogue_words:
        dialogue_duration = max(4, min(6, math.ceil(speech_seconds + 1.15)))
        recommended = max(recommended, dialogue_duration)
        reasons.append(
            f"fala detectada com {dialogue_words} palavras; reserva para articulacao e reacao: {dialogue_duration}s"
        )
    else:
        dialogue_duration = 0

    if has_action and has_reaction:
        recommended = max(recommended, 5)
        reasons.append("acao e reacao precisam aparecer no mesmo take")
    if has_timing_arc:
        recommended = 6
        reasons.append("o prompt exige inicio, virada, reacao e estado final alterado")
    if explicit is not None:
        explicit_rounded = max(4, min(6, math.ceil(explicit)))
        recommended = max(recommended, explicit_rounded)
        reasons.append(f"duracao explicita encontrada no prompt: {explicit:g}s")

    recommended = min(MOVA_REVIEW_DURATIONS[-1], recommended)
    frames = int(round(recommended * fps)) + 1
    requested_beyond_review = bool(explicit and explicit > MOVA_REVIEW_DURATIONS[-1])
    if not reasons:
        reasons.append("gesto ou evento simples com tempo para leitura e corte")

    estimates = {
        4: {"min": 20, "max": 28},
        5: {"min": 26, "max": 34},
        6: {"min": 33, "max": 42},
    }
    estimate = estimates[recommended]
    return {
        "version": PRODUCER_VERSION,
        "recommended_duration_seconds": recommended,
        "recommended_frames": frames,
        "fps": fps,
        "resolution": {"width": MOVA_REVIEW_RESOLUTION[0], "height": MOVA_REVIEW_RESOLUTION[1]},
        "steps": MOVA_REVIEW_STEPS,
        "estimated_generation_minutes": estimate,
        "dialogue": {
            "detected": bool(dialogue_words),
            "words": dialogue_words,
            "estimated_speech_seconds": round(speech_seconds, 2),
            "minimum_duration_seconds": dialogue_duration,
        },
        "voice_contract": {
            "portuguese_dialogue": portuguese_dialogue,
            "required_locale": MOVA_REQUIRED_DIALOGUE_LOCALE if portuguese_dialogue else None,
            "forbidden_locales": list(MOVA_FORBIDDEN_DIALOGUE_LOCALES) if portuguese_dialogue else [],
            "explicit_forbidden_locale_request": forbidden_locale_requested,
            "prompt_can_guarantee_accent": False,
            "human_pt_br_listening_required": portuguese_dialogue,
            "delivery_allowed": not portuguese_dialogue,
            "status": "PENDING_PT_BR_LISTENING" if portuguese_dialogue else "NOT_APPLICABLE",
        },
        "motion_contract": {
            "locomotion_directives_detected": locomotion_directives,
            "locomotion_allowed": not bool(dialogue_words),
            "locomotion_overridden": bool(dialogue_words and locomotion_directives),
            "allowed_dialogue_motion": ["eye gaze", "one head turn", "one hand gesture", "facial reaction"],
            "feet_planted_during_dialogue": bool(dialogue_words),
            "unprompted_motion_allowed": False,
            "required_final_hold_seconds": MOVA_FINAL_HOLD_SECONDS,
            "automatic_final_hold_qc": True,
        },
        "story_contract": {
            "action": has_action,
            "reaction": has_reaction,
            "changed_final_state": has_changed_end,
        },
        "explicit_duration_seconds": explicit,
        "requested_beyond_review_limit": requested_beyond_review,
        "reasons": reasons,
        "approval_status": "PRE_GENERATION_REVIEW",
        "upscale_allowed": False,
    }


def enforce_mova_policy(plan: Dict[str, Any]) -> None:
    voice = plan.get("voice_contract") or {}
    if voice.get("explicit_forbidden_locale_request"):
        raise ValueError(
            "O Maestro bloqueou o take: portugues de Portugal (pt-PT) e permanentemente proibido. "
            "Use portugues brasileiro (pt-BR)."
        )


def build_mova_effective_prompt(prompt: str, plan: Dict[str, Any]) -> str:
    """Append a highest-priority contract that the UI cannot weaken or omit."""

    voice = plan.get("voice_contract") or {}
    motion = plan.get("motion_contract") or {}
    rules = [
        "PERMANENT MAESTRO QUALITY CONTRACT (highest priority; overrides conflicting movement directions):",
        "Perform only motion explicitly allowed below. Never invent, repeat, extend or amplify an action.",
    ]
    if voice.get("portuguese_dialogue"):
        rules.extend([
            "All quoted dialogue must be spoken only in natural neutral Brazilian Portuguese from Brazil (pt-BR).",
            "European Portuguese, Portugal pronunciation and a Portugal accent are forbidden.",
            "Speak every quoted word exactly once: no translation, paraphrase, substitution, omission or extra word.",
            "Only the explicitly named speaker may move their lips; all other mouths stay closed.",
        ])
    if not motion.get("locomotion_allowed"):
        rules.extend([
            "Dialogue motion budget: every character keeps both feet planted and stays in the original screen position.",
            "No walking, step, foot lift, body translation, sliding, approaching the camera or leaving the mark.",
            "Allowed motion only: subtle eye gaze, one small head turn, one small hand gesture and facial reaction.",
        ])
    rules.extend([
        f"For the final {float(motion.get('required_final_hold_seconds') or MOVA_FINAL_HOLD_SECONDS):.2f} seconds, all character poses must remain stable for the cut.",
        "Camera and background geometry remain stable. No drift, warp, morph, duplicate subject or invented movement.",
    ])
    return f"{(prompt or '').strip()}\n\n" + "\n".join(f"- {rule}" if index else rule for index, rule in enumerate(rules))


def inspect_mova_final_hold(
    video_path: str | Path,
    *,
    ffmpeg: str,
    duration_seconds: float,
    hold_seconds: float = MOVA_FINAL_HOLD_SECONDS,
    max_luma_delta: float = MOVA_FINAL_HOLD_MAX_LUMA_DELTA,
) -> Dict[str, Any]:
    """Strict full-frame motion gate for the required final edit hold."""

    video_path = Path(video_path)
    start = max(0.0, float(duration_seconds) - float(hold_seconds))
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"select='gte(t,{start:.3f})',tblend=all_mode=difference,signalstats,metadata=print:file=-",
        "-an",
        "-f",
        "null",
        os.devnull,
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=90)
        deltas = [float(value) for value in re.findall(r"lavfi\.signalstats\.YAVG=([0-9.]+)", completed.stdout)]
        if len(deltas) < 2:
            raise RuntimeError("quadros insuficientes para medir a pose final")
        mean_delta = sum(deltas) / len(deltas)
        passed = mean_delta <= float(max_luma_delta)
        return {
            "status": "PASS" if passed else "AUTO_REJECTED",
            "passed": passed,
            "hold_seconds": float(hold_seconds),
            "mean_luma_delta": round(mean_delta, 4),
            "max_luma_delta": float(max_luma_delta),
            "sampled_frames": len(deltas),
            "method": "ffmpeg_frame_difference_v1",
        }
    except Exception as exc:
        return {
            "status": "UNVERIFIED",
            "passed": False,
            "hold_seconds": float(hold_seconds),
            "mean_luma_delta": None,
            "max_luma_delta": float(max_luma_delta),
            "sampled_frames": 0,
            "method": "ffmpeg_frame_difference_v1",
            "error": str(exc),
        }


def inspect_visible_text(
    video_path: str | Path,
    *,
    occupancy: float = 0.20,
    max_glyph_pixels: int = MOVA_VISIBLE_TEXT_MAX_GLYPH_PIXELS,
    max_ui_neutral_fraction: float = MOVA_VISIBLE_UI_MAX_NEUTRAL_FRACTION,
) -> Dict[str, Any]:
    """Reject persistent burned captions and large hallucinated UI panels.

    This is deliberately a conservative delivery gate, not OCR. Persistent
    subtitle-like bright glyphs are measured in the lower 45 percent, while a
    separate neutral-panel score catches the full-screen document/UI failure
    mode seen in spoken LTX takes. Human review remains mandatory after PASS.
    """

    path = Path(video_path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {
            "status": "UNVERIFIED",
            "passed": False,
            "method": "temporal_visible_text_v1",
            "error": f"video indisponivel: {path}",
        }
    occupancy_count: np.ndarray | None = None
    neutral_fractions: List[float] = []
    frames = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            top = int(round(height * 0.55))
            roi = frame[top:height, :width]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            bright_glyph = ((hsv[:, :, 1] <= 72) & (hsv[:, :, 2] >= 188)).astype(np.uint16)
            if occupancy_count is None:
                occupancy_count = np.zeros_like(bright_glyph, dtype=np.uint16)
            occupancy_count += bright_glyph

            panel_top = int(round(height * 0.42))
            panel_hsv = cv2.cvtColor(frame[panel_top:height, :width], cv2.COLOR_BGR2HSV)
            neutral = (panel_hsv[:, :, 1] < 60) & (panel_hsv[:, :, 2] > 195)
            neutral_fractions.append(float(np.mean(neutral)))
            frames += 1
    finally:
        capture.release()

    if frames < 2 or occupancy_count is None:
        return {
            "status": "UNVERIFIED",
            "passed": False,
            "method": "temporal_visible_text_v1",
            "error": "quadros insuficientes",
        }

    threshold = max(2, int(round(frames * float(occupancy))))
    core = (occupancy_count >= threshold).astype(np.uint8) * 255
    core = cv2.morphologyEx(core, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(core, connectivity=8)
    filtered = np.zeros_like(core)
    for component in range(1, component_count):
        area = int(stats[component, cv2.CC_STAT_AREA])
        component_height = int(stats[component, cv2.CC_STAT_HEIGHT])
        component_width = int(stats[component, cv2.CC_STAT_WIDTH])
        if 3 <= area <= 1800 and component_height <= 44 and component_width <= 200:
            filtered[labels == component] = 255

    glyph_pixels = int(np.count_nonzero(filtered))
    median_neutral_fraction = float(np.median(neutral_fractions))
    failures: List[str] = []
    if glyph_pixels > int(max_glyph_pixels):
        failures.append("PERSISTENT_VISIBLE_GLYPHS")
    if median_neutral_fraction > float(max_ui_neutral_fraction):
        failures.append("HALLUCINATED_UI_PANEL")
    return {
        "status": "PASS" if not failures else "AUTO_REJECTED",
        "passed": not failures,
        "failures": failures,
        "sampled_frames": frames,
        "occupancy_threshold_frames": threshold,
        "persistent_glyph_pixels": glyph_pixels,
        "max_glyph_pixels": int(max_glyph_pixels),
        "median_neutral_panel_fraction": round(median_neutral_fraction, 4),
        "max_neutral_panel_fraction": float(max_ui_neutral_fraction),
        "method": "temporal_visible_text_v1",
    }


def inspect_mova_media(
    video_path: str | Path,
    *,
    ffmpeg: str,
    expected_duration_seconds: float,
    require_audio: bool = True,
    enforce_loudness: bool = True,
) -> Dict[str, Any]:
    """Verify visual structure and, only when requested, the audio delivery."""

    video_path = Path(video_path)
    ffmpeg_path = Path(ffmpeg)
    sibling_probe = ffmpeg_path.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    ffprobe = str(sibling_probe) if sibling_probe.is_file() else (shutil.which("ffprobe") or "ffprobe")
    try:
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,sample_rate,channels,r_frame_rate",
                "-of",
                "json",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        payload = json.loads(probe.stdout or "{}")
        streams = payload.get("streams") or []
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
        duration = float((payload.get("format") or {}).get("duration") or 0.0)
        duration_delta = abs(duration - float(expected_duration_seconds))

        summaries: List[tuple[str, str]] = []
        if audio_stream and enforce_loudness:
            loudness = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-af",
                    "ebur128=peak=true",
                    "-f",
                    "null",
                    os.devnull,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            summaries = re.findall(
                r"I:\s*(-?[0-9.]+)\s*LUFS[\s\S]{0,500}?Peak:\s*(-?[0-9.]+)\s*dBFS",
                loudness.stderr or "",
            )
        integrated_lufs = float(summaries[-1][0]) if summaries else None
        true_peak_dbfs = float(summaries[-1][1]) if summaries else None

        visual_failures: List[str] = []
        audio_failures: List[str] = []
        warnings: List[str] = []
        if not video_stream:
            visual_failures.append("VIDEO_STREAM_MISSING")
        if not audio_stream:
            if require_audio:
                audio_failures.append("AUDIO_STREAM_MISSING")
            else:
                warnings.append("AUDIO_DEFERRED_TO_SEPARATE_PASS")
        if duration_delta > 0.20:
            visual_failures.append("DURATION_MISMATCH")
        if audio_stream and enforce_loudness and (
            integrated_lufs is None or true_peak_dbfs is None
        ):
            audio_failures.append("LOUDNESS_UNVERIFIED")
        elif audio_stream and enforce_loudness:
            if not MOVA_AUDIO_MIN_LUFS <= integrated_lufs <= MOVA_AUDIO_MAX_LUFS:
                audio_failures.append("LOUDNESS_OUT_OF_RANGE")
            if true_peak_dbfs > MOVA_AUDIO_MAX_TRUE_PEAK_DBFS:
                audio_failures.append("TRUE_PEAK_TOO_HIGH")
        elif audio_stream and not enforce_loudness:
            warnings.append("LOUDNESS_DEFERRED_TO_SEPARATE_AUDIO_QC")
        failures = visual_failures + audio_failures
        return {
            "status": "PASS" if not failures else "AUTO_REJECTED",
            "passed": not failures,
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name"),
            "audio_sample_rate": int(audio_stream.get("sample_rate") or 0),
            "audio_channels": int(audio_stream.get("channels") or 0),
            "duration_seconds": round(duration, 4),
            "expected_duration_seconds": float(expected_duration_seconds),
            "duration_delta_seconds": round(duration_delta, 4),
            "integrated_lufs": integrated_lufs,
            "true_peak_dbfs": true_peak_dbfs,
            "loudness_range_lufs": [MOVA_AUDIO_MIN_LUFS, MOVA_AUDIO_MAX_LUFS],
            "max_true_peak_dbfs": MOVA_AUDIO_MAX_TRUE_PEAK_DBFS,
            "failures": failures,
            "visual_failures": visual_failures,
            "audio_failures": audio_failures,
            "warnings": warnings,
            "visual_passed": not visual_failures,
            "audio_required": bool(require_audio),
            "audio_qc_enforced": bool(enforce_loudness),
            "audio_passed": not audio_failures if (require_audio or enforce_loudness) else None,
            "method": "ffprobe_ebur128_v1",
        }
    except Exception as exc:
        return {
            "status": "UNVERIFIED",
            "passed": False,
            "failures": ["MEDIA_QC_ERROR"],
            "method": "ffprobe_ebur128_v1",
            "error": str(exc),
        }


def enforce_dialogue_duration(plan: Dict[str, Any], frames: int, fps: float) -> None:
    dialogue = plan.get("dialogue") or {}
    minimum = int(dialogue.get("minimum_duration_seconds") or 0)
    if not dialogue.get("detected") or minimum <= 0:
        return
    requested = max(0.0, (int(frames) - 1) / float(fps))
    if requested + 0.01 < minimum:
        raise ValueError(
            "O Produtor MOVA bloqueou o take: "
            f"a fala precisa de pelo menos {minimum}s ({minimum * int(fps) + 1} quadros a {int(fps)} FPS), "
            f"mas foram pedidos {requested:.1f}s."
        )
