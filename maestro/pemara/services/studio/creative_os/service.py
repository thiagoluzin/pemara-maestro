"""Shot analysis and durable generation lineage over existing Maestro workers."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from .adapters import adapter_for
from .assets import Assets, file_hash
from .ir import CreativeError, digest, identifier, validate_ir
from .routing import route
from .store import Store


class CreativeService:
    def __init__(self, root, projects_root, bridge):
        self.root, self.bridge = Path(root).resolve(), bridge
        self.store = Store(self.root / "creative_os.sqlite")
        self.assets = Assets(self.store, projects_root)

    def save_shot(self, ir, expected=None):
        ir = validate_ir(ir)
        # Composite key avoids SH001 from two projects colliding.
        key = digest([ir["project_id"], ir["shot_id"]])
        return self.store.put("shots", {"ir": ir, "ir_hash": digest(ir)}, entity_id=key,
                              expected=expected, create=expected is None)

    def analyze(self, shot_id):
        shot = self.store.get("shots", shot_id)
        return {"shot": shot, "route": route(shot["ir"], self.bridge.capabilities(), self.benchmark_history())}

    def benchmark_history(self):
        rows=self.store.list("benchmarks",500)
        result=[]
        with self.store.transaction() as con:
            for row in rows:
                generation=self.store.read(con,"generations",row.get("generation_id"))
                if not generation or generation.get("human_verdict") not in {"approved","rejected"}: continue
                if row.get("config_hash") != (generation.get("provenance") or {}).get("workflow_hash"): continue
                result.append({**row,"human_approved":generation["human_verdict"] == "approved"})
        return result

    def attach_job(self, job_id, project_id="maestro_manual"):
        """Index an existing manually requested job; this never submits GPU work."""
        identifier(job_id); identifier(project_id)
        job = self.bridge.status(job_id)
        if not job or job.get("mode") != "video" or job.get("engine_id") not in {"minimax_h3", "ltx_2_5"}:
            raise CreativeError("INVALID_JOB", "Escolha um job de vídeo H3/LTX existente.", 409)
        key = digest(["legacy_job", job_id])
        with self.store.transaction() as con:
            existing = self.store.read(con,"generations",key)
            if existing:
                if existing["project_id"] != project_id: raise CreativeError("JOB_PROJECT_CONFLICT", "Job já vinculado a outro projeto.",409)
                return existing
            spec = job.get("request_spec") or {}
            ir = validate_ir({"version":"0.2","project_id":project_id,"shot_id":job_id,
                "duration_seconds":float(spec.get("video_duration") or 5),
                "content":{"description":spec.get("prompt") or job.get("prompt", "")},
                "generation":{"preferred_engine":job["engine_id"],"quality_mode":"balanced"}})
            shot_key=digest([project_id,job_id])
            self.store.write(con,"shots",shot_key,{"ir":ir,"ir_hash":digest(ir)},create=True)
            return self.store.write(con,"generations",key,{"shot_id":shot_key,"project_id":project_id,"ir":ir,
                "job_id":job_id,"engine_id":job["engine_id"],"request_spec":spec,"request_hash":digest(spec),
                "parent_generation_id":None,"status":"queued","human_verdict":None,"artifacts":[],
                "transport":self.bridge.transport,"references":job.get("input_files",{}),"source":"maestro_manual"},create=True)

    def generate(self, shot_id, bindings, idempotency_key, *, parent_id=None, expected_ir_hash=None):
        identifier(idempotency_key)
        if not isinstance(bindings, dict): raise CreativeError("INVALID_BINDINGS", "Bindings deve ser objeto.")
        shot = self.store.get("shots", shot_id)
        if expected_ir_hash and shot["ir_hash"] != expected_ir_hash:
            raise CreativeError("SHOT_CHANGED", "O plano mudou antes do envio.",409)
        decision = route(shot["ir"], self.bridge.capabilities())
        if not decision["can_generate"]:
            raise CreativeError(decision["blocked"][0], "Geração bloqueada: " + ", ".join(decision["blocked"]), 409)
        adapter = adapter_for(decision["selected_engine"])
        spec = adapter.build_job(shot["ir"], bindings)
        if spec.get('creative_all_in_one') and not self.bridge.capabilities().get('optional',{}).get('h3_all_in_one',{}).get('enabled'):
            raise CreativeError('ALL_IN_ONE_UNAVAILABLE','All-In-One não qualificado no runtime atual.',409)
        inputs = {}
        refs = []
        for label in ("base", "end"):
            if bindings.get(f"{label}_asset_id"):
                path, record = self.assets.resolve(bindings[f"{label}_asset_id"], shot["ir"]["project_id"], image=True)
                inputs[f"{label}_bytes"], inputs[f"{label}_name"] = path.read_bytes(), path.name
                refs.append({"asset_id": record["id"], "sha256": record["sha256"], "role": label})
        if inputs.get("end_bytes") and not inputs.get("base_bytes"):
            raise CreativeError("FIRST_FRAME_REQUIRED", "Quadro final exige quadro inicial nesta integração.")
        if self.bridge.prepare:
            spec = self.bridge.prepare(spec, bindings, inputs)
        if parent_id:
            parent = self.store.get("generations", parent_id)
            if parent["shot_id"] != shot_id or parent["engine_id"] != decision["selected_engine"]:
                raise CreativeError("PARENT_MISMATCH", "Parent deve ser do mesmo plano e motor.", 409)
        request_hash = digest({"ir": shot["ir"], "spec": spec, "refs": refs, "parent": parent_id})
        generation_id = digest([shot_id, idempotency_key])
        with self.store.transaction() as con:
            existing = self.store.read(con, "generations", generation_id)
            if existing:
                if existing["request_hash"] != request_hash:
                    raise CreativeError("IDEMPOTENCY_CONFLICT", "A chave já identifica outra configuração.", 409)
                return existing
            record = self.store.write(con, "generations", generation_id, {
                "shot_id": shot_id, "project_id": shot["ir"]["project_id"], "ir": shot["ir"],
                "engine_id": decision["selected_engine"], "parent_generation_id": parent_id,
                "request_hash": request_hash, "request_spec": spec, "references": refs, "bindings": bindings,
                "status": "submitting", "human_verdict": None, "job_id": None,
                "artifacts": [], "transport": self.bridge.transport, "route": decision}, create=True)
        try:
            job_id = self.bridge.submit(spec, **inputs)
        except Exception as exc:
            # Never replay an uncertain submission under the same key.
            self.store.put("generations", {**record, "status": "submission_failed", "error": str(exc)},
                           entity_id=generation_id, expected=record["revision"], create=False)
            raise
        return self.store.put("generations", {**record, "job_id": job_id, "status": "queued"},
                              entity_id=generation_id, expected=record["revision"], create=False)

    def sync(self, generation_id):
        record = self.store.get("generations", generation_id)
        if not record.get("job_id") or record["status"] in {"done", "error", "canceled"}:
            return record
        job = self.bridge.status(record["job_id"])
        if not job:
            raise CreativeError("JOB_UNKNOWN", "Job ausente; nenhum reenvio automático.", 409)
        normalized = adapter_for(record["engine_id"]).normalize_result(job)
        if record.get('request_spec',{}).get('creative_all_in_one') and job.get('status') == 'done':
            observed=(job.get('result') or {}).get('creative_all_in_one') or {}
            provenance=self.bridge.provenance((job.get('result') or {}).get('prompt_id')) if self.bridge.provenance else {}
            if not observed.get('headless_expansion') or not observed.get('workflow_hash') or (provenance or {}).get('workflow_hash')!=observed['workflow_hash']:
                raise CreativeError('ALL_IN_ONE_PROVENANCE','Expansão real do All-In-One não confirmada.',409)
        if record.get('source') == 'fun_control' and job.get('status') == 'done':
            request=record['request_spec']['creative_fun_control_request']
            observed=(job.get('result') or {}).get('creative_fun_control') or {}
            provenance=self.bridge.provenance((job.get('result') or {}).get('prompt_id')) if self.bridge.provenance else {}
            if any(observed.get(k)!=request[k] for k in ('asset_sha256','control_kind','strength')) or observed.get('source_ir_hash')!=digest(record['ir']) or not observed.get('workflow_hash') or (provenance or {}).get('workflow_hash')!=observed['workflow_hash']:
                raise CreativeError('CONTROL_PROVENANCE','Resultado não corresponde ao controle solicitado.',409)
        if record.get('source') == 'timeline_director' and job.get('status') == 'done':
            contract = record['timeline_contract']
            observed = (job.get('result') or {}).get('creative_timeline') or {}
            provenance = self.bridge.provenance((job.get('result') or {}).get('prompt_id')) if self.bridge.provenance else {}
            if any(observed.get(k) != contract[k] for k in ('workflow_hash','source_ir_hash','output_frames','seed')) or (provenance or {}).get('workflow_hash') != contract['workflow_hash']:
                raise CreativeError('TIMELINE_PROVENANCE','Resultado não corresponde à timeline solicitada.',409)
            if len([o for o in normalized['outputs'] if o.get('kind') == 'video']) != 1:
                raise CreativeError('TIMELINE_OUTPUT_COUNT','Timeline deve entregar exatamente um vídeo contínuo.',409)
        if "output_indices" in record:
            outputs = normalized["outputs"]
            indices = record["output_indices"]
            if job.get("status") == "done" and any(i >= len(outputs) for i in indices):
                raise CreativeError("MOTION_OUTPUT_MISSING", "Resultado multissegmento incompleto; nenhum mapeamento inferido.",409)
            normalized["outputs"] = [outputs[i] for i in indices if i < len(outputs)]
        artifacts = record["artifacts"]
        if job.get("status") == "done" and not artifacts:
            folder = self.root / "artifacts" / generation_id
            folder.mkdir(parents=True, exist_ok=True)
            for index, output in enumerate(normalized["outputs"]):
                path = self.bridge.output_path(output)
                if not path: continue
                source = Path(path)
                target = folder / f"{index:03d}{source.suffix.lower()}"
                sha = file_hash(source)
                if target.exists() and file_hash(target) != sha:
                    raise CreativeError("ARTIFACT_CONFLICT", "Artefato persistido divergiu.", 409)
                if not target.exists():
                    temp = folder / f".{uuid.uuid4().hex}.tmp"
                    shutil.copyfile(source, temp)
                    if file_hash(temp) != sha: raise CreativeError("COPY_MISMATCH", "Cópia de artefato divergiu.")
                    temp.replace(target)
                artifacts.append({"relative_path": str(target.relative_to(self.root)).replace("\\", "/"),
                                  "sha256": sha, "kind": output.get("kind"), "size": target.stat().st_size})
        return self.store.put("generations", {**record, **normalized, "artifacts": artifacts,
            "provenance": self.bridge.provenance(normalized.get("prompt_id")) if self.bridge.provenance and normalized.get("prompt_id") else record.get("provenance"),
            "actual_seed": record.get("actual_seed_override", (job.get("result") or {}).get("seed")),
            "timings": {k: job.get(k) for k in ("started_at", "finished_at")}},
            entity_id=generation_id, expected=record["revision"], create=False)
