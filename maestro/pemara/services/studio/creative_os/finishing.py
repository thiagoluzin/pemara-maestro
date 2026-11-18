"""Durable deferred finishing. Approved sources remain immutable; outputs are candidates."""
import json
import os
import threading
import time
from pathlib import Path
from .assets import safe_path, file_hash
from .evaluation import inspect_video
from .ir import CreativeError, digest, identifier


class Finishing:
    def __init__(self, service, profiles, executor, health, admission, cleanup=None):
        self.service, self.store = service, service.store
        self.profiles, self.executor, self.health, self.admission = profiles, executor, health, admission
        self.cleanup = cleanup
        self.lock = threading.Lock()
        self.worker = None
        self.stop = threading.Event()

    def master(self, master_id):
        record = self.store.get("masters",master_id)
        generation = self.store.get("generations",record["generation_id"])
        if record["state"] != "APPROVED" or generation.get("human_verdict") != "approved":
            raise CreativeError("MASTER_NOT_APPROVED", "Acabamento exige aprovação humana vigente.",409)
        path = safe_path(self.service.root,record["artifact"]["relative_path"])
        if file_hash(path) != record["artifact"]["sha256"]: raise CreativeError("MASTER_CHANGED", "Master alterado.",409)
        return record,path

    def latent(self, generation_id, payload):
        generation = self.service.sync(generation_id)
        if generation["status"] != "done": raise CreativeError("GENERATION_NOT_READY", "Geração não concluída.",409)
        artifact = next((a for a in generation["artifacts"] if a["kind"] == "latent" and a["sha256"] == payload.get("sha256")),None)
        if not artifact: raise CreativeError("LATENT_NOT_CAPTURED", "Não há latent capturado e vinculado a esta geração.",409)
        if file_hash(safe_path(self.service.root,artifact["relative_path"])) != artifact["sha256"]:
            raise CreativeError("LATENT_CHANGED", "Latent alterado.",409)
        required=("engine_version","checkpoint_hash","vae_hash","workflow_hash","conditioning_hash","width","height","frames","fps","seed")
        if any(payload.get(k) is None for k in required): raise CreativeError("LATENT_METADATA", "Metadados de compatibilidade incompletos.")
        for k in ("checkpoint_hash","vae_hash","workflow_hash","conditioning_hash"):
            if len(str(payload[k])) != 64 or any(c not in "0123456789abcdef" for c in str(payload[k])):
                raise CreativeError("LATENT_METADATA", "Hash inválido.")
        if (generation.get("provenance") or {}).get("workflow_hash") != payload["workflow_hash"]:
            raise CreativeError("LATENT_WORKFLOW", "Workflow não corresponde à geração.",409)
        return self.store.put("latents", {"version":1,"generation_id":generation_id,"engine":generation["engine_id"],
            "artifact":artifact,"metadata":{k:payload[k] for k in required},"state":"AVAILABLE",
            "compatible_finishing_profiles":[],"roundtrip_qualified":False})

    def enqueue(self, master_id, profile_id, key):
        identifier(key)
        master,_ = self.master(master_id)
        profile=self.profiles.get(profile_id)
        if not profile or not profile.get("enabled"):
            raise CreativeError("FINISHING_UNAVAILABLE", "Perfil não instalado ou ainda não qualificado.",409)
        if profile.get("requires_captured_latent"):
            generation=self.store.get("generations",master["generation_id"])
            if not (generation.get("provenance") or {}).get("latent_capture") or not any(a.get("kind")=="latent" for a in generation.get("artifacts",[])):
                raise CreativeError("LATENT_NOT_CAPTURED","Este master não possui latent com modelos registrados antes da geração.",409)
        job_id=digest([master_id,key])
        fingerprint=digest([master["artifact"]["sha256"],profile])
        with self.store.transaction() as con:
            old=self.store.read(con,"hq_jobs",job_id)
            if old:
                if old["fingerprint"] != fingerprint: raise CreativeError("IDEMPOTENCY_CONFLICT", "Chave de HQ já usada com outro perfil.",409)
                return old
            job=self.store.write(con,"hq_jobs",job_id,{"master_id":master_id,"source_sha256":master["artifact"]["sha256"],
                "profile_id":profile_id,"profile":profile,"fingerprint":fingerprint,"state":"QUEUED",
                "human_verdict":None,"artifacts":[],"restart_policy":"NO_BLIND_REPLAY","cleanup_policy":"RETAIN_SOURCE_AND_CANDIDATE"},create=True)
        self.start()
        return job

    def start(self, *, resume=False):
        with self.lock:
            if self.worker and self.worker.is_alive(): return
            with self.store.transaction() as con:
                state=self.store.read(con,"workers","hq") or {}
                if state.get("paused") and not resume: return
                self.store.write(con,"workers","hq",{**state,"paused":False})
            self.stop.clear()
            self.worker=threading.Thread(target=self.run,name="creative-hq",daemon=True)
            self.worker.start()

    def cancel(self, job_id):
        with self.store.transaction() as con:
            job=self.store.read(con,"hq_jobs",job_id)
            if not job: raise CreativeError("NOT_FOUND", "HQ ausente.",404)
            if job["state"] != "QUEUED": raise CreativeError("HQ_ACTIVE", "Somente HQ aguardando pode ser cancelado aqui.",409)
            return self.store.write(con,"hq_jobs",job_id,{**job,"state":"CANCELED"},expected=job["revision"])

    def recover(self):
        # Worker restart never resubmits an uncertain GPU operation.
        from gpu_lease import GpuLeaseRegistry
        with self.store.transaction() as con:
            for row in con.execute("SELECT data FROM entities WHERE kind='hq_jobs'").fetchall():
                job=json.loads(row[0])
                if job["state"] == "RUNNING" and not GpuLeaseRegistry._pid_is_running(job.get("worker_pid")):
                    self.store.write(con,"hq_jobs",job["id"],{**job,"state":"INTERRUPTED","incident":"WORKER_EXIT_UNCERTAIN_NO_REPLAY"})
            for row in con.execute("SELECT data FROM entities WHERE kind='assemblies'").fetchall():
                job=json.loads(row[0])
                if job["status"] in {"queued","running"} and not GpuLeaseRegistry._pid_is_running(job.get("worker_pid")):
                    self.store.write(con,"assemblies",job["id"],{**job,"status":"interrupted","automatic_retry":False})
        self.start()

    def run(self):
        while not self.stop.is_set():
            with self.store.transaction() as con:
                rows=con.execute("SELECT data FROM entities WHERE kind='hq_jobs' ORDER BY rowid").fetchall()
                job=next((j for r in rows if (j:=json.loads(r[0]))["state"] == "QUEUED"),None)
            if not job: return
            # Admission callback holds the shared GPU lease throughout execution.
            try:
                with self.admission(job):
                    master,source=self.master(job["master_id"])
                    with self.store.transaction() as con:
                        current=self.store.read(con,"hq_jobs",job["id"])
                        if current["state"] != "QUEUED": continue
                        job=self.store.write(con,"hq_jobs",job["id"],{**current,"state":"RUNNING","worker_pid":os.getpid(),"started_at":time.time()})
                    before=self.health()
                    target=self.service.root / "hq" / job["id"]
                    target.mkdir(parents=True,exist_ok=True)
                    output=self.executor(job,source,target)
                    self.master(job["master_id"])
                    path=Path(output).resolve()
                    if target.resolve() not in path.parents or path == source.resolve():
                        raise CreativeError("HQ_OUTPUT_PATH", "Saída deve ser um candidato separado.")
                    quality=inspect_video(path)
                    if not quality["pass"]: raise CreativeError("HQ_INVALID", "Candidato falhou na decodificação.")
                    after=self.health()
                    elapsed=time.time()-job["started_at"]
                    previous=[j for j in self.store.list("hq_jobs",500) if j.get("profile_id")==job["profile_id"] and j.get("elapsed_seconds")]
                    incidents=[]
                    if len(previous)>=3 and elapsed > 2*sum(j["elapsed_seconds"] for j in previous[:3])/3:
                        incidents.append("ELAPSED_TIME_DEGRADATION")
                    before_ram=(before.get("system") or {}).get("ram_free")
                    after_ram=(after.get("system") or {}).get("ram_free")
                    if before_ram and after_ram and before_ram-after_ram>2*1024**3:
                        incidents.append("RAM_GROWTH_REVIEW")
                    artifact={"relative_path":path.relative_to(self.service.root).as_posix(),"sha256":file_hash(path),"kind":"video","size":path.stat().st_size}
                    self.store.put("hq_jobs",{**job,"state":"PENDING_HUMAN_REVIEW","finished_at":time.time(),"artifacts":[artifact],
                        "health_before":before,"health_after":after,"elapsed_seconds":elapsed,"time_per_step":None,
                        "health_incidents":incidents,"technical":quality,"semantic_equivalence":"UNMEASURED"},entity_id=job["id"],expected=job["revision"],create=False)
                    if incidents:
                        self.store.put("workers",{"paused":True,"incidents":incidents,"job_id":job["id"]},entity_id="hq",create=False)
                        if self.cleanup: self.cleanup()
                        return
            except BlockingIOError:
                self.stop.wait(5)
                continue
            except Exception as exc:
                current=self.store.get("hq_jobs",job["id"])
                self.store.put("hq_jobs",{**current,"state":"FAILED","error":str(exc),"finished_at":time.time()},entity_id=job["id"],expected=current["revision"],create=False)
                self.store.put("workers",{"paused":True,"incidents":[str(exc)],"job_id":job["id"]},entity_id="hq",create=False)
                # Stop the batch after any incident; leave remaining jobs queued for explicit resume.
                return

    def review(self, job_id, decision, sha):
        if decision not in {"approved","rejected"}: raise CreativeError("INVALID_VERDICT", "Decisão inválida.")
        job=self.store.get("hq_jobs",job_id)
        if job["state"] not in {"PENDING_HUMAN_REVIEW","APPROVED","REJECTED"}: raise CreativeError("HQ_NOT_READY", "HQ não concluído.",409)
        self.master(job["master_id"])
        artifact=next((a for a in job["artifacts"] if a["sha256"]==sha),None)
        if not artifact or file_hash(safe_path(self.service.root,artifact["relative_path"])) != sha:
            raise CreativeError("ARTIFACT_CHANGED", "Hash do candidato divergiu.",409)
        return self.store.put("hq_jobs",{**job,"state":decision.upper(),"human_verdict":decision},entity_id=job_id,expected=job["revision"],create=False)

    def status(self):
        with self.store.transaction() as con:
            state=self.store.read(con,"workers","hq") or {"paused":False}
        return {"worker_alive":bool(self.worker and self.worker.is_alive()),"profiles":self.profiles,
                "worker_state":state,
                "jobs":self.store.list("hq_jobs"),"automatic_comfy_restart":False,
                "incident_policy":"stop batch; retain files; explicit resume; never replay RUNNING"}
