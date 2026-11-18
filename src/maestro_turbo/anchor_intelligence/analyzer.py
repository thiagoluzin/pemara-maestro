"""Strict image validation and vision-model request/response helpers."""

from __future__ import annotations

import base64
import json
import re
from typing import Any


MAX_ANCHOR_BYTES = 20 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class AnchorImageError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def validate_anchor_image(data: bytes, mime_type: str = "") -> str:
    if not data:
        raise AnchorImageError("ANCHOR_IMAGE_REQUIRED", "Envie a imagem-ancora.")
    if len(data) > MAX_ANCHOR_BYTES:
        raise AnchorImageError("ANCHOR_IMAGE_TOO_LARGE", "A imagem-ancora excede 20 MB.")
    detected = ""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        detected = "image/jpeg"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        detected = "image/webp"
    if detected not in ALLOWED_MIME_TYPES:
        raise AnchorImageError("ANCHOR_IMAGE_TYPE_INVALID", "Use PNG, JPEG ou WebP valido.")
    declared = str(mime_type or "").split(";", 1)[0].strip().lower()
    if declared and declared in ALLOWED_MIME_TYPES and declared != detected:
        raise AnchorImageError("ANCHOR_IMAGE_MIME_MISMATCH", "O tipo declarado nao corresponde aos bytes da imagem.")
    return detected


def vision_analysis_instruction(intent: str) -> str:
    return f"""You are a forensic visual continuity analyst for image-to-video generation.
Read only what is visible in the supplied anchor. Do not infer names, lore, unseen anatomy,
off-frame objects, future actions, or hidden text. Record uncertainty explicitly. Compare the
pixels against this owner intent: {intent!r}.

Return one JSON object and no prose with these keys:
subjects (array: id, count, visible_identity_markers, face, hair, body_proportions, clothing,
pose, screen_position, gaze, occlusions, confidence), objects, environment, composition,
camera (shot_size, angle, lens_impression, axis, depth_layers), lighting, palette, visible_text,
geometry_relationships, uncertainties, recommended_invariants, allowed_motion_candidates,
divergences (array: severity, field, evidence, intent, decision_required), and analysis_notes.
Use null or [] when pixels do not support a fact. Never complete missing details."""


def build_vision_messages(data: bytes, mime_type: str, intent: str) -> list[dict[str, Any]]:
    detected = validate_anchor_image(data, mime_type)
    prompt = vision_analysis_instruction(" ".join(str(intent or "").split())[:12_000])
    encoded = base64.b64encode(data).decode("ascii")
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{detected};base64,{encoded}"}},
            ],
        }
    ]


def parse_vision_response(content: str) -> dict[str, Any]:
    raw = str(content or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise AnchorImageError("VISION_RESPONSE_INVALID", "O analisador visual nao retornou JSON valido.")
        try:
            payload = json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AnchorImageError("VISION_RESPONSE_INVALID", "O analisador visual retornou JSON malformado.") from exc
    if not isinstance(payload, dict):
        raise AnchorImageError("VISION_RESPONSE_INVALID", "A leitura visual deve ser um objeto JSON.")
    required_any = {"subjects", "environment", "composition", "objects", "visible_text"}
    if not required_any.intersection(payload):
        raise AnchorImageError("VISION_RESPONSE_INCOMPLETE", "A leitura visual nao trouxe os campos de evidencia.")
    return payload
