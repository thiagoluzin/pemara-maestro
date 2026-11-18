"""Reviewable repair, memory, continuity and direction without implicit renders."""
from .ir import CreativeError, digest, identifier, validate_ir
from .routing import route

BIBLE_KINDS = {"character", "scene", "prop"}
CONTINUITY_FIELDS = ("identity", "pose", "body_orientation", "spatial_position", "motion_direction",
                     "prop_state", "weapon_state", "lighting", "background", "camera", "framing", "audio_ambience")


def save_bible(service, project_id, kind, item_id, payload, expected=None):
    identifier(project_id); identifier(item_id)
    if kind not in BIBLE_KINDS or not isinstance(payload, dict):
        raise CreativeError("INVALID_BIBLE", "Bible deve ser character, scene ou prop.")
    if len(str(payload)) > 32000: raise CreativeError("BIBLE_TOO_LARGE", "Bible excede limite.")
    refs = payload.get("references", [])
    if not isinstance(refs, list): raise CreativeError("INVALID_REFERENCE", "references deve ser lista.")
    for ref in refs: service.assets.resolve(ref, project_id)
    return service.store.put("bibles", {"project_id": project_id, "kind": kind, "item_id": item_id, "content": payload},
        entity_id=digest([project_id,kind,item_id]), expected=expected, create=expected is None)


def repair_plan(service, generation_id, payload):
    parent = service.sync(generation_id)
    if parent["status"] not in {"done", "error", "canceled", "interrupted"}:
        raise CreativeError("PARENT_ACTIVE", "Aguarde o job atual terminar.", 409)
    mode = payload.get("strategy", "same_model_retry")
    supported = {"same_model_retry", "selective_rerun", "first_last"}
    if mode not in supported:
        raise CreativeError("REPAIR_UNAVAILABLE", "Retake, controle e troca de motor exigem adapter qualificado; não há fallback.", 409)
    if mode == "first_last" and parent["engine_id"] != "minimax_h3":
        raise CreativeError("REPAIR_UNAVAILABLE", "Este modo de reparo exige H3.", 409)
    proposed = validate_ir(payload.get("ir", parent["ir"]))
    if proposed["project_id"] != parent["project_id"] or proposed["shot_id"] != parent["ir"]["shot_id"]:
        raise CreativeError("REPAIR_SCOPE", "Reparo deve preservar projeto e plano.")
    from .ir import ENGINES
    if ENGINES.get(proposed["generation"]["preferred_engine"]) != parent["engine_id"]:
        raise CreativeError("ENGINE_MISMATCH", "Reparo não troca o motor escolhido.", 409)
    for key,value in parent["ir"]["generation"].items():
        if key.startswith("max_") and proposed["generation"].get(key) != value:
            raise CreativeError("BUDGET_CHANGE", "Reparo não pode aumentar ou remover seu próprio orçamento.",409)
    changed = [k for k in proposed if proposed.get(k) != parent["ir"].get(k)]
    bindings = payload.get("bindings", parent.get("bindings", {}))
    if not isinstance(bindings, dict): raise CreativeError("INVALID_BINDINGS", "Bindings deve ser objeto.")
    if parent.get("source") == "maestro_manual" and parent.get("references") and not bindings.get("base_asset_id"):
        raise CreativeError("REFERENCE_BINDING_REQUIRED", "Reanalise a imagem no Maestro ou vincule o asset original; nenhuma referência será descartada.",409)
    for key in ("base_asset_id", "end_asset_id"):
        original=parent.get("bindings",{}).get(key)
        if original and bindings.get(key) != original:
            raise CreativeError("REFERENCE_CHANGE_REQUIRES_NEW_SHOT", "Reparo deve preservar as referências originais.",409)
    if mode == "first_last" and not bindings.get("end_asset_id"):
        raise CreativeError("LAST_FRAME_REQUIRED", "Vincule um quadro final.")
    reason = str(payload.get("reason", "")).strip()
    if not reason: raise CreativeError("REPAIR_REASON", "Descreva a falha e a correção.")
    return service.store.put("repairs", {"parent_generation_id": generation_id, "shot_id": parent["shot_id"],
        "engine_id": parent["engine_id"], "strategy": mode, "ir": proposed, "bindings": bindings,
        "reason": reason[:4000], "changed": changed, "preserved": [k for k in proposed if k not in changed],
        "status": "planned", "child_generation_id": None})


def execute_repair(service, repair_id):
    with service.store.transaction() as con:
        item = service.store.read(con,"repairs",repair_id)
        if not item: raise CreativeError("NOT_FOUND", "Reparo ausente.", 404)
        if item["status"] != "planned": return item
        parent = service.store.read(con,"generations",item["parent_generation_id"])
        budget = parent["ir"]["generation"]
        # Reservations count too: parallel requests cannot overrun the budget.
        import json
        rows = [json.loads(r[0]) for r in con.execute("SELECT data FROM entities WHERE kind='repairs'")]
        used = [r for r in rows if r["shot_id"] == item["shot_id"] and r["status"] != "planned"]
        if any(r["status"] == "submitting" for r in used):
            raise CreativeError("REPAIR_IN_PROGRESS", "Outro reparo está sendo enviado para este plano.",409)
        limit_key = "max_mode_changes" if item["strategy"] == "first_last" else "max_same_model_retries"
        if len(used) >= budget.get("max_repairs", 2) or sum(r["strategy"] == item["strategy"] for r in used) >= budget.get(limit_key, 1):
            raise CreativeError("REPAIR_BUDGET", "Orçamento de reparos esgotado.", 409)
        if len(used) >= budget.get("max_full_retries",2):
            raise CreativeError("REPAIR_BUDGET", "Orçamento de renders completos esgotado.",409)
        if "max_gpu_minutes" in budget:
            generations=[json.loads(r[0]) for r in con.execute("SELECT data FROM entities WHERE kind='generations'")]
            related=[g for g in generations if g.get("shot_id")==item["shot_id"]]
            durations=[]
            for generation in related:
                timing=generation.get("timings") or {}
                if not timing.get("started_at") or not timing.get("finished_at"):
                    raise CreativeError("GPU_BUDGET_UNMEASURED", "Tempo anterior desconhecido; não consumir orçamento às cegas.",409)
                durations.append(max(0,timing["finished_at"]-timing["started_at"]))
            if (sum(durations)+max(durations,default=0))/60 > budget["max_gpu_minutes"]:
                raise CreativeError("GPU_BUDGET", "Orçamento insuficiente para outra execução estimada.",409)
        item = service.store.write(con,"repairs",repair_id,{**item,"status":"submitting"},expected=item["revision"])
    try:
        shot = service.store.get("shots",item["shot_id"])
        service.save_shot(item["ir"],shot["revision"])
        child = service.generate(item["shot_id"],item["bindings"],repair_id,parent_id=item["parent_generation_id"],expected_ir_hash=digest(item["ir"]))
        return service.store.put("repairs",{**item,"status":"submitted","child_generation_id":child["id"]},entity_id=repair_id,expected=item["revision"],create=False)
    except Exception as exc:
        service.store.put("repairs",{**item,"status":"failed","error":str(exc)},entity_id=repair_id,expected=item["revision"],create=False)
        raise


def continuity(service, left_id, right_id, observations=None):
    left, right = service.sync(left_id), service.sync(right_id)
    if left["project_id"] != right["project_id"]: raise CreativeError("PROJECT_MISMATCH", "Compare planos do mesmo projeto.")
    if left["status"] != "done" or right["status"] != "done": raise CreativeError("GENERATION_NOT_READY", "Conclua os dois planos.",409)
    if not isinstance(observations or {},dict): raise CreativeError("INVALID_REVIEW", "Observações devem ser objeto.")
    values = {k: {"state":"unmeasured","evidence":None} for k in CONTINUITY_FIELDS}
    for key,value in (observations or {}).items():
        if key not in values or not isinstance(value,dict) or value.get("state") not in {"match","mismatch","unmeasured"} or not value.get("evidence"):
            raise CreativeError("INVALID_REVIEW", "Comparação exige dimensão, estado e evidência.")
        values[key] = value
    mismatches = [k for k,v in values.items() if v["state"] == "mismatch"]
    return service.store.put("continuity", {"project_id":left["project_id"],"left":left_id,"right":right_id,
        "left_hashes":[a["sha256"] for a in left["artifacts"]],"right_hashes":[a["sha256"] for a in right["artifacts"]],
        "dimensions":values,"decision":"REPAIR_REQUIRED" if mismatches else "PENDING_HUMAN_REVIEW",
        "suggestions":["first_last", "bridge_shot"] if mismatches else [],"automatic_semantic_claim":False})


def director(service, project_id, shot_ids):
    identifier(project_id)
    if not isinstance(shot_ids,list) or not 1 <= len(shot_ids) <= 100 or len(set(shot_ids)) != len(shot_ids):
        raise CreativeError("INVALID_SEQUENCE", "Escolha 1–100 planos sem repetição.")
    caps = service.bridge.capabilities()
    history = service.benchmark_history()
    steps=[]
    for shot_id in shot_ids:
        shot=service.store.get("shots",shot_id)
        if shot["ir"]["project_id"] != project_id: raise CreativeError("PROJECT_MISMATCH", "Plano de outro projeto.")
        steps.append({"shot_id":shot_id,"ir_hash":shot["ir_hash"],"route":route(shot["ir"],caps,history),
                      "depends_on":steps[-1]["shot_id"] if steps else None})
    return service.store.put("directions", {"project_id":project_id,"steps":steps,"status":"planned",
        "auto_submit":False,"gates":["explicit_engine","technical_evaluation","human_artifact_verdict","continuity_review"],
        "bibles":service.store.where("bibles","project_id",project_id)})
