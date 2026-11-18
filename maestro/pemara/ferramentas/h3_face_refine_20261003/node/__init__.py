"""Local H3-only integration. No broad T8 extension or other engine is loaded."""
import logging
from .graph import ensure_face_refine
from .stable_sage import PemaraH3SageLongSequencePatch, PemaraH3SageStrideDiagnostic

NODE_CLASS_MAPPINGS = {"PemaraH3SageLongSequencePatch": PemaraH3SageLongSequencePatch,
    "PemaraH3SageStrideDiagnostic": PemaraH3SageStrideDiagnostic}
NODE_DISPLAY_NAME_MAPPINGS = {}


def refine_new_h3_prompt(payload):
    if isinstance(payload.get("prompt"), dict):
        # Only new submissions; never rewrite running jobs or persisted history.
        try:
            payload["prompt"] = ensure_face_refine(payload["prompt"])
        except Exception as exc:
            logging.exception("[PEMARA] H3 graph cleanup/Sage binding failed; submission blocked")
            # Core logs/swallow handler exceptions. An explicit missing class
            # forces ordinary prompt validation to refuse the unrefined graph.
            payload["prompt"] = {"pemara_face_refine_blocked": {
                "class_type": "PEMARA_FACE_REFINE_BINDING_BLOCKED", "inputs": {},
                "_meta": {"title": str(exc)}}}
    return payload


try:
    from server import PromptServer
    if getattr(PromptServer, "instance", None) is not None:
        PromptServer.instance.add_on_prompt_handler(refine_new_h3_prompt)
        logging.info("[PEMARA] Face Refine REMOVED by owner; Sage long-sequence guard active")
except ImportError:
    pass  # Standalone CPU contract tests.
