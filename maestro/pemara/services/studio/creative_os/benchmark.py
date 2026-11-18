"""Benchmark ledger uses completed generations and actual owner verdicts only."""
from .ir import CreativeError, digest
from .routing import route

CLASSES = {f"B{i:02d}": name for i,name in enumerate(("Environment","Product","Single Human","Object Interaction",
    "Combat","Pose Control","Talking Human","First/Last","Localized Repair","Extension","H3 References","H3 Two Stage HQ","HQ Stability"),1)}


def register(service, generation_id, benchmark_class):
    if benchmark_class not in CLASSES: raise CreativeError("BENCHMARK_CLASS", "Classe B01–B13 obrigatória.")
    record=service.sync(generation_id)
    if record["status"] != "done" or not record.get("artifacts"): raise CreativeError("GENERATION_NOT_READY", "Benchmark exige geração concluída.",409)
    if record.get("actual_seed") is None or not (record.get("provenance") or {}).get("workflow_hash"):
        raise CreativeError("BENCHMARK_PROVENANCE", "Seed real e workflow hash obrigatórios.",409)
    analysis=route(record["ir"],{})
    key=digest([generation_id,benchmark_class])
    data={"generation_id":generation_id,"engine_id":record["engine_id"],"class":benchmark_class,
          "seed":record["actual_seed"],"config_hash":record["provenance"]["workflow_hash"],
          "signature":analysis["signature"],"timings":record.get("timings"),
          "human_approved":None if record.get("human_verdict") is None else record["human_verdict"] == "approved",
          "artifact_hashes":[a["sha256"] for a in record["artifacts"]]}
    with service.store.transaction() as con:
        old=service.store.read(con,"benchmarks",key)
        return service.store.write(con,"benchmarks",key,data,expected=old["revision"] if old else None,create=not old)


def matrix(service):
    rows=service.store.list("benchmarks",500)
    groups=[]
    for cls in CLASSES:
        for engine in ("minimax_h3","ltx_2_5"):
            matched=[r for r in rows if r["class"] == cls and r["engine_id"] == engine]
            reviewed=[r for r in matched if type(r.get("human_approved")) is bool]
            seeds=len({r["seed"] for r in reviewed})
            groups.append({"class":cls,"engine_id":engine,"runs":len(matched),"reviewed_seeds":seeds,
                "ranking_eligible":seeds>=3,"status":"insufficient_evidence" if seeds<3 else "reviewable_not_auto_promoted"})
    return {"classes":CLASSES,"groups":groups,"profiles":{"REFERENCE":"installed_baseline",
        "FAST_SAFE":"alias_of_reference_until_benchmarked","EXPERIMENTAL":"disabled_until_reviewed"}}
