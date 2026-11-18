"""Rewriter output is a proposal; review and application never submit GPU work."""
import copy
from .ir import CreativeError, digest, validate_ir


def proposal_data(shot, text, provenance):
    if not isinstance(text, str) or not text.strip() or len(text) > 32000:
        raise CreativeError("INVALID_PROMPT", "Sugestão deve conter até 32.000 caracteres.")
    if not isinstance(provenance, dict) or not provenance.get("prompt_id"):
        raise CreativeError("PROVENANCE_REQUIRED", "Informe o prompt_id da reescrita.")
    return {
        "shot_id": shot["id"], "source_ir_hash": shot["ir_hash"],
        "original_description": shot["ir"]["content"].get("description", ""),
        "suggestion": text.strip(), "suggestion_hash": digest(text.strip()),
        "provenance": provenance, "provenance_verified": False,
        "status": "PENDING_HUMAN_REVIEW", "semantic_constraints_verified": False,
        "preserved_constraints": copy.deepcopy(shot["ir"].get("constraints", {})),
        "human_verdict": None, "generation_submitted": False}


def propose(service, shot_id, text, provenance):
    return service.store.put("prompt_proposals",proposal_data(service.store.get("shots",shot_id),text,provenance))


def review(service, proposal_id, decision, suggestion_hash):
    if decision not in ("approved", "rejected"):
        raise CreativeError("INVALID_VERDICT", "Escolha approved ou rejected.")
    with service.store.transaction() as con:
        proposal = service.store.read(con, "prompt_proposals", proposal_id)
        if proposal is None:
            raise CreativeError("NOT_FOUND", "Sugestão ausente.", 404)
        if suggestion_hash != proposal["suggestion_hash"]:
            raise CreativeError("HASH_MISMATCH", "Revisão não corresponde ao texto exato.", 409)
        if proposal["status"] == "APPLIED":
            raise CreativeError("ALREADY_APPLIED", "Crie nova revisão do plano; histórico aplicado é imutável.", 409)
        return service.store.write(con, "prompt_proposals", proposal_id,
            {**proposal, "human_verdict": decision, "status": decision.upper()},
            expected=proposal["revision"])


def apply(service, proposal_id):
    with service.store.transaction() as con:
        proposal = service.store.read(con, "prompt_proposals", proposal_id)
        if proposal is None:
            raise CreativeError("NOT_FOUND", "Sugestão ausente.", 404)
        if proposal["status"] == "APPLIED":
            return proposal
        if proposal.get("human_verdict") != "approved":
            raise CreativeError("HUMAN_REVIEW_REQUIRED", "Revise a reescrita antes de aplicá-la.", 409)
        shot = service.store.read(con, "shots", proposal["shot_id"])
        if not shot or shot["ir_hash"] != proposal["source_ir_hash"]:
            raise CreativeError("STALE_IR", "O plano mudou desde a reescrita.", 409)
        ir = copy.deepcopy(shot["ir"])
        ir["content"]["description"] = proposal["suggestion"]
        ir = validate_ir(ir)
        updated = service.store.write(con, "shots", shot["id"],
            {**shot, "ir": ir, "ir_hash": digest(ir)}, expected=shot["revision"])
        return service.store.write(con, "prompt_proposals", proposal_id,
            {**proposal, "status": "APPLIED", "applied_ir_hash": updated["ir_hash"]},
            expected=proposal["revision"])
