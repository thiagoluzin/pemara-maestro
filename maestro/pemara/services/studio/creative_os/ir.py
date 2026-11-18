"""Model-independent intent; runtime paths and graph internals stay in adapters."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re

ENGINES = {"h3": "minimax_h3", "minimax_h3": "minimax_h3", "ltx25": "ltx_2_5", "ltx_2_5": "ltx_2_5"}
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
ASSET = re.compile(r"^(asset|approved)://[A-Za-z0-9][A-Za-z0-9_./-]{0,240}$")
FORBIDDEN = {"node_id", "node_ids", "class_type", "workflow_path", "absolute_path", "gpu_id", "cuda_device", "sampler", "checkpoint_path"}


class CreativeError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.status = code, status
        super().__init__(message)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def identifier(value: object) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value) or value in {".", ".."}:
        raise CreativeError("INVALID_ID", "Identificador inválido.")
    return value


def walk(value, depth=0):
    if depth > 16:
        raise CreativeError("IR_TOO_DEEP", "Contrato excede 16 níveis.")
    if isinstance(value, dict):
        if FORBIDDEN.intersection(value):
            raise CreativeError("RUNTIME_IN_IR", "Detalhes de runtime pertencem ao adapter.")
        for child in value.values():
            walk(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > 200:
            raise CreativeError("IR_TOO_LARGE", "Lista excede 200 itens.")
        for child in value:
            walk(child, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise CreativeError("INVALID_NUMBER", "Número não finito.")
    elif isinstance(value, str) and value.startswith(("asset://", "approved://")):
        if not ASSET.fullmatch(value) or ".." in value.split("/"):
            raise CreativeError("INVALID_ASSET_URI", "Referência de asset inválida.")


def validate_ir(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise CreativeError("INVALID_IR", "Creative IR deve ser objeto.")
    walk(payload)
    if len(json.dumps(payload, ensure_ascii=False)) > 128_000:
        raise CreativeError("IR_TOO_LARGE", "Creative IR excede o limite.")
    if payload.get("version") != "0.2":
        raise CreativeError("IR_VERSION", "Creative IR exige versão 0.2.")
    for key in ("project_id", "shot_id"):
        identifier(payload.get(key))
    duration = payload.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not 0 < duration <= 30:
        raise CreativeError("INVALID_DURATION", "Duração deve ficar entre 0 e 30 segundos.")
    for key in ("content", "generation"):
        if not isinstance(payload.get(key), dict):
            raise CreativeError("IR_REQUIRED", f"{key} é obrigatório.")
    for key in ("analysis_hints", "cinematography", "style", "control_source", "constraints"):
        if key in payload and not isinstance(payload[key], dict):
            raise CreativeError("INVALID_IR_FIELD", f"{key} deve ser objeto.")
    generation = payload["generation"]
    if generation.get("preferred_engine") not in {*ENGINES, "auto"}:
        raise CreativeError("ENGINE_SELECTION_REQUIRED", "Escolha H3 ou LTX 2.5; auto permite apenas recomendação.")
    if generation.get("quality_mode") not in {"fast", "balanced", "cinema"}:
        raise CreativeError("QUALITY_MODE", "Modo de qualidade inválido.")
    for field in ("max_repairs", "max_full_retries", "max_same_model_retries", "max_mode_changes", "max_model_escalations"):
        if field in generation and (type(generation[field]) is not int or not 0 <= generation[field] <= 10):
            raise CreativeError("INVALID_BUDGET", f"{field} deve ficar entre 0 e 10.")
    for field in ("retake_allowed", "extension_allowed", "native_audio"):
        if field in generation and type(generation[field]) is not bool:
            raise CreativeError("INVALID_BOOLEAN", f"{field} deve ser booleano.")
    for field in ("subjects", "props"):
        if field in payload["content"] and (not isinstance(payload["content"][field], list) or any(not isinstance(v, dict) for v in payload["content"][field])):
            raise CreativeError("INVALID_CONTENT", f"{field} deve ser uma lista de objetos.")
    action = payload["content"].get("action", {})
    if not isinstance(action, dict) or not isinstance(action.get("sequence", []), list):
        raise CreativeError("INVALID_ACTION", "Ação deve conter sequência em lista.")
    for subject in payload["content"].get("subjects", []):
        refs = subject.get("references", [])
        if not isinstance(refs, list) or any(not isinstance(r, str) or not ASSET.fullmatch(r) for r in refs):
            raise CreativeError("INVALID_REFERENCE", "Referências devem ser uma lista de asset URIs.")
    humans = payload.get("analysis_hints", {}).get("human_count", 0)
    if type(humans) is not int or not 0 <= humans <= 200:
        raise CreativeError("INVALID_HUMAN_COUNT", "human_count deve ser inteiro entre 0 e 200.")
    minutes = generation.get("max_gpu_minutes", 60)
    if type(minutes) not in (int, float) or not 0 < minutes <= 1440:
        raise CreativeError("INVALID_BUDGET", "max_gpu_minutes deve ficar entre 0 e 1440.")
    return copy.deepcopy(payload)


def features(ir: dict) -> dict:
    ir = validate_ir(ir)
    hints, content, control = ir.get("analysis_hints", {}), ir["content"], ir.get("control_source", {})
    return {
        "human_count": hints.get("human_count", len(content.get("subjects", []))),
        "causal_complexity": hints.get("causal_complexity", "unknown"),
        "physical_interaction": hints.get("physical_interaction", "unknown"),
        "temporal_risk": hints.get("temporal_risk", "unknown"),
        "weapon_persistence": hints.get("weapon_persistence", "unknown"),
        "action_count": len(content.get("action", {}).get("sequence", [])),
        "reference_count": sum(len(s.get("references", [])) for s in content.get("subjects", [])),
        "has_pose_video": bool(control.get("pose_video")),
        "has_face_video": bool(control.get("face_video")),
        "has_audio": bool(control.get("audio_reference")),
        "duration_seconds": ir["duration_seconds"],
        "evidence_source": "declared_intent_not_pixel_analysis",
    }
