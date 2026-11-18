"""Measured technical critic, explicit unknown semantic dimensions, human master gate."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from .assets import file_hash, safe_path
from .ir import CreativeError
from .critic import temporal_diagnostics

DIMENSIONS = ("identity", "anatomy", "spatial_quality", "temporal_stability", "temporal_degradation",
              "action_compliance", "action_completion", "causal_coherence", "contact_physics",
              "prop_persistence", "weapon_persistence", "camera_compliance", "continuity", "realism")


def inspect_video(path):
    binary = shutil.which("ffprobe")
    if not binary: raise CreativeError("FFPROBE_MISSING", "ffprobe não disponível.", 503)
    result = subprocess.run([binary, "-v", "error", "-count_frames", "-show_entries",
        "stream=codec_type,width,height,nb_read_frames,r_frame_rate:format=duration", "-of", "json", str(path)],
        capture_output=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode or result.stderr: return {"pass": False, "failures": ["MEDIA_DECODE_ERROR"]}
    try:
        data = json.loads(result.stdout)
        video = next(s for s in data["streams"] if s.get("codec_type") == "video")
        duration = float(data["format"]["duration"])
        valid = math.isfinite(duration) and duration > 0 and video["width"] > 0 and video["height"] > 0 and int(video["nb_read_frames"]) > 1
    except (KeyError, ValueError, StopIteration, TypeError):
        return {"pass": False, "failures": ["MEDIA_METADATA_INVALID"]}
    return {"pass": valid, "failures": [] if valid else ["MEDIA_INVALID"], "duration_seconds": duration,
            "video": video, "method": "ffprobe_count_frames", "audio_present": any(s.get("codec_type")=="audio" for s in data["streams"])}


def evaluate(service, generation_id, observations=None):
    if observations is not None and not isinstance(observations, dict):
        raise CreativeError("INVALID_SCORE", "Observações devem ser objeto.")
    record = service.sync(generation_id)
    if record["status"] != "done": raise CreativeError("GENERATION_NOT_READY", "Aguarde a geração terminar.", 409)
    technical = []
    temporal = []
    for artifact in record["artifacts"]:
        if artifact["kind"] != "video": continue
        path = safe_path(service.root, artifact["relative_path"])
        if file_hash(path) != artifact["sha256"]: raise CreativeError("ARTIFACT_CHANGED", "Artefato alterado.", 409)
        technical.append({"sha256": artifact["sha256"], **inspect_video(path)})
        if technical[-1]["pass"]:
            temporal.append({"sha256":artifact["sha256"],**temporal_diagnostics(path)})
    scores = {name: None for name in DIMENSIONS}
    evidence = {}
    for name, value in (observations or {}).items():
        if name not in scores or not isinstance(value, dict): raise CreativeError("INVALID_SCORE", "Dimensão de avaliação inválida.")
        score = value.get("score")
        if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1 or not str(value.get("evidence", "")).strip():
            raise CreativeError("INVALID_SCORE", "Score exige valor 0–1 e evidência textual.")
        scores[name], evidence[name] = score, value["evidence"]
    technical_pass = bool(technical) and all(item["pass"] for item in technical)
    return service.store.put("evaluations", {"generation_id": generation_id, "technical": technical,
        "temporal_diagnostics": temporal,
        "technical_pass": technical_pass, "scores": scores, "evidence": evidence,
        "score_source": "supplied_review" if evidence else "unmeasured", "human_approved": False,
        "decision": "PENDING_HUMAN_REVIEW" if technical_pass else "FAIL"})


def verdict(service, generation_id, decision, artifact_sha256, notes=""):
    if decision not in {"approved", "rejected"}: raise CreativeError("INVALID_VERDICT", "Escolha approved ou rejected.")
    record = service.sync(generation_id)
    if record["status"] != "done": raise CreativeError("GENERATION_NOT_READY", "Geração não concluída.", 409)
    artifact = next((a for a in record["artifacts"] if a["sha256"] == artifact_sha256 and a["kind"] == "video"), None)
    if not artifact: raise CreativeError("ARTIFACT_MISMATCH", "Escolha o hash exato do vídeo.", 409)
    if file_hash(safe_path(service.root, artifact["relative_path"])) != artifact_sha256:
        raise CreativeError("ARTIFACT_CHANGED", "Vídeo mudou antes da decisão.", 409)
    if decision == "approved":
        evaluations = service.store.where("evaluations", "generation_id", generation_id)
        if not evaluations or not evaluations[0]["technical_pass"] or not any(t["sha256"] == artifact_sha256 and t["pass"] for t in evaluations[0]["technical"]):
            raise CreativeError("TECHNICAL_GATE_REQUIRED", "Avaliação técnica do artefato é obrigatória.", 409)
    with service.store.transaction() as con:
        latest = service.store.read(con,"generations",generation_id)
        updated = service.store.write(con,"generations",generation_id,{**latest,"human_verdict":decision,"human_notes":str(notes)[:4000]}, expected=record["revision"])
        if decision == "approved":
            master_id = generation_id
            master = service.store.read(con,"masters",master_id)
            if master and master["artifact"]["sha256"] != artifact_sha256:
                raise CreativeError("MASTER_IMMUTABLE", "Master aprovado é imutável; crie outra geração.", 409)
            if not master:
                master = service.store.write(con,"masters",master_id,{"generation_id":generation_id,
                    "engine_id":record["engine_id"],"project_id":record["project_id"],"artifact":artifact,
                    "state":"APPROVED", "notes":str(notes)[:4000]},create=True)
            elif master["state"] != "APPROVED":
                master = service.store.write(con,"masters",master_id,{**master,"state":"APPROVED"})
            updated["master"] = master
        else:
            master = service.store.read(con,"masters",generation_id)
            if master: service.store.write(con,"masters",generation_id,{**master,"state":"REVOKED"})
        return updated
