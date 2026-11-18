"""Explainable recommendations never override the owner's engine selection."""
from .ir import CreativeError, ENGINES, features, validate_ir

OPTIONAL_NODES = {
    "h3_all_in_one": ("H3OneNode",),
    "h3_motion_director": ("H3MotionDirector", "MiniMaxH3MotionDirector"),
    "h3_timeline_director": ("H3TimelineDirector", "MiniMaxH3TimelineDirector"),
    "h3_prompt_rewriter": ("H3PromptRewriter", "MiniMaxH3PromptRewriter", "MiniMaxH3PromptWriterOmni"),
    "h3_fun_control": ("H3FunControlLoader", "H3FunControlApply"),
    "h3_latent_upscale": ("MinimaxH3LatentUpscalerNode2D", "MinimaxH3LatentUpscaler3D", "MMH3SplitUpscale"),
}


def capabilities(descriptors, nodes, *, runtime=None, error=None):
    # Optional node names are hints, not a claim that an external API is supported.
    optional = {name: {"node_candidates_detected": [n for n in candidates if n in nodes],
                       "integrated": False, "enabled": False,
                       "reason": "EXTERNAL_ADAPTER_BENCHMARK_REQUIRED"}
                for name, candidates in OPTIONAL_NODES.items()}
    engines = {}
    for engine in descriptors:
        engine_id = engine["id"]
        if engine_id != "minimax_h3":
            continue
        required = {"minimax_h3": {"MiniMaxH3ImageToVideo", "UNETLoader", "SaveVideo"},
                    "ltx_2_5": {"LTXVImgToVideoInplace", "UNETLoader", "SaveVideo"}}[engine_id]
        missing = sorted(required - set(nodes))
        readiness = engine.get("readiness", {})
        engines[engine_id] = {**engine, "missing_nodes": missing,
            "runnable": not error and not missing and readiness.get("production_ready") is True,
            "auto_route": False, "benchmark_status": "unqualified"}
    return {"engines": engines, "optional": optional, "runtime": runtime or {},
            "available": error is None, "error": error, "selection_required": True,
            "fallback_allowed": False, "default_engine_id": None,
            "save_latent_node_available": "SaveLatent" in nodes,
            "h3_latent_package_roundtrip_qualified": False}


def route(ir, caps, history=()):
    ir = validate_ir(ir)
    f = features(ir)
    scores = {"minimax_h3": 0}
    reasons = {key: [] for key in scores}
    if f["physical_interaction"] == "high" or f["causal_complexity"] == "high":
        scores["minimax_h3"] += 30; reasons["minimax_h3"].append("COMPLEX_PHYSICAL_ACTION")
    if f["weapon_persistence"] == "critical":
        scores["minimax_h3"] += 25; reasons["minimax_h3"].append("CRITICAL_WEAPON")
    if f["reference_count"] > 1:
        scores["minimax_h3"] += 30; reasons["minimax_h3"].append("MULTI_REFERENCE_INTENT")
    # Only real reviewed local records can contribute, and only matching signatures.
    signature = {k: f[k] for k in ("human_count", "physical_interaction", "weapon_persistence")}
    for engine in scores:
        rows = [r for r in history if r.get("engine_id") == engine and r.get("signature") == signature
                and type(r.get("human_approved")) is bool and r.get("config_hash")]
        rows = list({r.get("generation_id"):r for r in rows if r.get("generation_id")}.values())
        if len({r.get("seed") for r in rows if r.get("seed") is not None}) >= 3:
            scores[engine] += round(30 * sum(r["human_approved"] for r in rows) / len(rows), 2)
            reasons[engine].append("LOCAL_REVIEWED_HISTORY")
    ranked = sorted((dict(engine_id=e, score=s, reason_codes=reasons[e],
                          runnable=bool(caps.get("engines", {}).get(e, {}).get("runnable")))
                     for e, s in scores.items()), key=lambda v: v["score"], reverse=True)
    selected = ENGINES.get(ir["generation"]["preferred_engine"])
    blocked = []
    if not selected: blocked.append("ENGINE_SELECTION_REQUIRED")
    elif selected != "minimax_h3": blocked.append("ENGINE_REMOVED")
    elif not caps.get("engines", {}).get(selected, {}).get("runnable"): blocked.append("ENGINE_UNAVAILABLE")
    if f["has_pose_video"] or f["has_face_video"]: blocked.append("EXACT_CONTROL_NOT_INTEGRATED")
    return {"selected_engine": selected, "recommendations": ranked, "features": f,
            "signature": signature, "reason_codes": (["OWNER_SELECTION_PRESERVED"] if selected else []) + blocked,
            "can_generate": not blocked, "blocked": blocked, "fallback_allowed": False}
