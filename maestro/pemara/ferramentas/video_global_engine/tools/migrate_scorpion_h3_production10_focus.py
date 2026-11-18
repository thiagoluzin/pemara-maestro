"""Move the Scorpion/Johnny route from rejected Hero12 to 10-second Production10.

This is a one-project, reversible metadata migration. It preserves every
anchor and rejected artifact, and authorizes only the rejected T01 replacement.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1] / "projetos" / "scorpion_johnny_cage_living_forest_h3_80s_liveaction_v1"
ROUTE = PROJECT / "work" / "h3_fight_only_8x10_r1_noob_style" / "route_manifest.json"
FILES = (PROJECT / "take_queue.json", PROJECT / "production_manifest.json", ROUTE)
ROUTE_ID = "SCJCLF_H3_FIGHT_ONLY_8X10_R2_NOOB_STYLE_PRODUCTION10_FOCUS"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    backup = PROJECT / "archive" / f"before_h3_production10_focus_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    before = {}
    for source in FILES:
        before[str(source.relative_to(PROJECT))] = digest(source)
        target = backup / source.relative_to(PROJECT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    queue = json.loads((PROJECT / "take_queue.json").read_text(encoding="utf-8"))
    queue.update({
        "route_id": ROUTE_ID,
        "status": "h3_production10_focus_t01_replacement_ready",
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generation_paused": False,
        "resume_gate": "T01_REPLACEMENT_AUTHORIZED_AFTER_REJECTION",
    })
    queue["engine_lock"].update({
        "profile": "h3_production",
        "pilot_render_authorized_take": "T01",
    })
    queue["assembly"]["native"].update({"width": 1088, "height": 608})
    queue["production_batch"].update({
        "current": "T01_REPLACEMENT_ONLY",
        "continue_automatically": False,
        "reason": "Production10 + res_multistep + render-focus; T02-T08 remain blocked until T01 human review.",
    })
    for take in queue["takes"]:
        generation = take.setdefault("video_generation", {})
        generation.update({
            "quality_profile": "h3_production",
            "width": 1088,
            "height": 608,
            "fps": 24,
            "frames": 243,
            "steps": 10,
            "guidance": 1.0,
            "sampler": "res_multistep",
            "scheduler": "simple",
            "native_audio": False,
            "render_focus": True,
            "maestro_job_enabled": take.get("id") == "T01",
        })
        if take.get("id") == "T01":
            take["animation_prompt"] = (
                "One continuous ten-second photorealistic live-action fight shot in the established rain-soaked "
                "Living Forest clearing. Begin at the exact amber-versus-emerald impact in A01. The collision "
                "compresses both guards, throws water and bark outward, then separates them with heavy unequal recoil. "
                "Johnny retracts the same leg and lands on both boots; he never rolls or flips. Scorpion uses that "
                "single recovery beat to plant and throw his one chain spear. Johnny reads it late and slips one short "
                "step off line. The same kunai passes his head and gouges the Hollow-Eye tree into exact A04 while the "
                "chain remains taut. A physical 40 mm camera trucks around one foreground branch with real parallax, "
                "keeping both complete bodies and the attack vector readable. Exactly two fighters, one decisive "
                "exchange, grounded stunt weight, practical wet costumes, localized amber hellfire and emerald chi, "
                "persistent bark damage. Motion and recovery continue through the final frame. No repeated attack, "
                "acrobatics, clone, extra limb, duplicate weapon, reset, slow motion, text, gore, fatality or static tail."
            )
            take["render_authorized"] = True
            take["video_generation_forbidden"] = False
            take["video_generation_block_reason"] = ""
            take["maestro_status"] = "REJECTED"
            take["maestro_notes"] = (
                "Hero12 rejeitado preservado. Substituta Production10 autorizada no mesmo escopo, pendente de QC e revisão humana."
            )
        else:
            take["render_authorized"] = False
            take["video_generation_forbidden"] = True
            take["video_generation_block_reason"] = "Aguardando revisão humana da substituta T01 Production10."
    write_json(PROJECT / "take_queue.json", queue)

    production = json.loads((PROJECT / "production_manifest.json").read_text(encoding="utf-8"))
    production.update({
        "status": "H3_PRODUCTION10_FOCUS_T01_READY",
        "active_route_id": ROUTE_ID,
        "visual_route_id": ROUTE_ID,
        "generation_paused": False,
        "generation_authorized": True,
        "authorization_scope": "T01_H3_PRODUCTION10_REPLACEMENT_ONLY",
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    })
    production["generation_engine_policy"].update({"quality_profile": "h3_production", "steps": 10})
    production["video_generation"].update({
        "quality_profile": "h3_production",
        "width": 1088,
        "height": 608,
        "steps": 10,
        "sampler": "res_multistep",
        "scheduler": "simple",
        "generic_maestro_worker_allowed": True,
        "generic_worker_block_reason": "",
        "render_focus_preflight": True,
    })
    production["gate_status"].update({
        "comfy_graph": "PASS_H3_PRODUCTION10_FL2VA_RES_MULTISTEP",
        "runtime": "PENDING_TIMED_T01_REPLACEMENT",
        "technical_qc": "PENDING",
        "motion_qc": "PENDING",
        "speed_qc": "TARGET_3_TO_6_MINUTES",
        "human_take_review": "PENDING",
    })
    write_json(PROJECT / "production_manifest.json", production)

    route = json.loads(ROUTE.read_text(encoding="utf-8"))
    route.update({
        "route_id": ROUTE_ID,
        "status": "T01_PRODUCTION10_REPLACEMENT_READY",
        "generation_authorized": True,
        "authorization_scope": "T01_REPLACEMENT_ONLY",
    })
    route["engine"].update({
        "quality_profile": "h3_production",
        "width": 1088,
        "height": 608,
        "steps": 10,
        "sampler": "res_multistep",
        "scheduler": "simple",
        "render_focus_preflight": True,
    })
    route["scope"]["render_now"] = ["T01"]
    route["main_takes"][0]["status"] = "REPLACEMENT_READY"
    route["gates"].update({
        "comfy_graph": "PASS_FL2VA_PRODUCTION10_RES_MULTISTEP_NO_AUDIO",
        "runtime": "PENDING_TIMED_REPLACEMENT",
        "technical_qc": "PENDING",
        "visual_qc": "PENDING",
        "speed_qc": "TARGET_3_TO_6_MINUTES",
        "human_review": "PENDING",
    })
    write_json(ROUTE, route)

    receipt = {
        "version": "scjclf-h3-production10-focus-migration-v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "backup": str(backup),
        "before_sha256": before,
        "after_sha256": {str(path.relative_to(PROJECT)): digest(path) for path in FILES},
        "main_take_seconds": 10.0,
        "profile": "1088x608p24-243f-10step-res_multistep",
        "render_scope": "T01 replacement only",
    }
    write_json(PROJECT / "logs" / f"h3_production10_focus_migration_{stamp}.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
