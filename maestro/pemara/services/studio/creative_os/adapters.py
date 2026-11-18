"""Translate intent into the existing Maestro job contract, without replacing engines."""
from __future__ import annotations

from abc import ABC, abstractmethod
import json
from h3_prompt_writing import compile_base_prompt
from h3_workflow import H3_QUALITY_PROFILES, DEFAULT_H3_QUALITY_PROFILE
from .ir import CreativeError, ENGINES, validate_ir


def description(ir):
    content = ir["content"]
    body = content.get("description") or content.get("action", {}).get("primary")
    if not isinstance(body, str) or not body.strip():
        raise CreativeError("DESCRIPTION_REQUIRED", "Descreva o plano em content.description ou action.primary.")
    sequence = content.get("action", {}).get("sequence", [])
    if any(not isinstance(item, str) for item in sequence):
        raise CreativeError("INVALID_SEQUENCE", "Sequência deve conter textos.")
    parts = [body.strip(), *sequence]
    for key in ("cinematography", "style"):
        parts.extend(str(v) for v in ir.get(key, {}).values() if isinstance(v, str))
    for key in ("subjects", "props", "environment"):
        if content.get(key):
            parts.append(key + ": " + json.dumps(content[key], ensure_ascii=False))
    if ir.get("constraints"):
        parts.append("Constraints: " + json.dumps(ir["constraints"], ensure_ascii=False))
    return ". ".join(dict.fromkeys(parts))


class BaseAdapter(ABC):
    @abstractmethod
    def build_job(self, ir, bindings): ...

    def supports(self, ir):
        return ENGINES.get(validate_ir(ir)["generation"]["preferred_engine"]) == self.engine_id

    def normalize_result(self, job):
        return {"engine_id": self.engine_id, "status": job.get("status"), "progress": job.get("progress"),
                "prompt_id": job.get("prompt_id"), "outputs": (job.get("result") or {}).get("outputs", []),
                "error": job.get("error"), "fallback_used": False}

    def common(self, ir, bindings):
        if not self.supports(ir):
            raise CreativeError("ENGINE_MISMATCH", "Adapter não corresponde à escolha do proprietário.")
        refs = sum(len(s.get("references", [])) for s in ir["content"].get("subjects", []))
        if refs or ir.get("control_source"):
            raise CreativeError("MODE_NOT_INTEGRATED", "Use o fluxo de referência/controle existente; este adapter inicial cobre T2V/I2V/first-last.")
        seed = bindings.get("seed", -1)
        if type(seed) is not int or not -1 <= seed < 2**63:
            raise CreativeError("INVALID_SEED", "Seed fora do intervalo.")
        return {"mode": "video", "model": "", "engine_id": self.engine_id, "prompt": description(ir),
                "negative": "", "lora": "", "lora_strength": 0.0, "width": 960, "height": 544,
                "steps": 8, "guidance": 1.0, "seed": seed, "frames": 121, "fps": 24.0,
                "provider": "", "duration": 30.0, "video_duration": ir["duration_seconds"],
                "prompt_influence": 0.5, "loop": False, "camera_pose": "", "camera_speed": 0.8,
                "video_conditioning_profile": "identity_locked", "h3_quality_profile": "",
                "enable_minimax_h3_native_audio": ir["generation"].get("native_audio", False),
                "enable_minimax_h3_live_preview": False}


class H3Adapter(BaseAdapter):
    engine_id = "minimax_h3"

    def build_job(self, ir, bindings):
        job = self.common(ir, bindings)
        family=bindings.get('h3_adapter','native')
        if family not in {'native','all_in_one'}:
            raise CreativeError('H3_ADAPTER','Escolha um adapter H3 instalado.')
        profile_id = bindings.get("h3_quality_profile", DEFAULT_H3_QUALITY_PROFILE)
        if profile_id not in H3_QUALITY_PROFILES:
            raise CreativeError("INVALID_PROFILE", "Perfil H3 não instalado.")
        profile = H3_QUALITY_PROFILES[profile_id]
        if not 4 <= ir["duration_seconds"] <= 15:
            raise CreativeError("ENGINE_DURATION", "Adapter H3 exige 4–15 segundos.")
        job.update(width=profile["width"], height=profile["height"], steps=profile["steps"][0], h3_quality_profile=profile_id)
        if profile.get("draftOnly"): job["enable_minimax_h3_native_audio"] = False
        mode = "FL2VA" if bindings.get("end_asset_id") else "I2VA" if bindings.get("base_asset_id") else "T2VA"
        job["prompt"] = compile_base_prompt(job["prompt"], mode=mode, duration_seconds=ir["duration_seconds"]).prompt
        if family=='all_in_one':
            if profile_id!='h3_production' or job['enable_minimax_h3_native_audio']:
                raise CreativeError('ALL_IN_ONE_SCOPE','All-In-One qualificado em Production horizontal sem áudio.')
            job['creative_all_in_one']=True
        return job



def adapter_for(engine_id):
    cls = {"minimax_h3": H3Adapter}.get(engine_id)
    if cls is None: raise CreativeError("ENGINE_SELECTION_REQUIRED", "Selecione um motor.")
    return cls()
