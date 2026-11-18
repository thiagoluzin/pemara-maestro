from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ID = "scorpion_johnny_cage_living_forest_h3_80s_liveaction_v1"
R15_ROUTE_ID = "R15_FROM_ZERO_IMAGEGEN_H3_VEJITO_METHOD"
R16_ROUTE_ID = "R16_SIGNATURE_COMBAT_REBUILD"
REPLACEMENT_SCOPE = f"route:{R15_ROUTE_ID}"
R15_MASTER_REL = (
    "deliveries/"
    "cage_x_scorpion_r15_master_720p60_hunyuan_foley_pending_human_review.mp4"
)
R15_MASTER_SHA256 = (
    "26AB4B5E9638BC65A2C4E5E7C9A967A662036E00C97E417DEBAD5786A67526CD"
)
IDENTITY_REFERENCE_REL = (
    "routes/r15_from_zero/anchors/A_CAST_WORLD_MASTER_IMAGEGEN_ORIGINAL.png"
)
IDENTITY_REFERENCE_SHA256 = (
    "51B1BCE34EE6D3AD36DA1F958FB4860BD380934D9489ED82B8C84819F5FBD421"
)
R16_BASE_REL = "routes/r16_signature_combat"
COMBAT_PLAN_REL = f"{R16_BASE_REL}/combat_plan.json"
ANCHOR_PLAN_REL = f"{R16_BASE_REL}/anchor_plan.json"
HANDOFFS_REL = f"{R16_BASE_REL}/kinetic_handoffs.json"
DIRECTION_REL = f"{R16_BASE_REL}/docs/DIRECAO_R16_SIGNATURE_COMBAT.md"
R16_MANIFEST_REL = f"{R16_BASE_REL}/production_manifest.json"
R16_LIFECYCLE_REL = f"{R16_BASE_REL}/lifecycle_state.json"
R15_LIFECYCLE_REL = "routes/r15_from_zero/lifecycle_state.json"
REJECTION_REPORT_REL = "qc/R15_OWNER_REJECTION_COMBAT_DIRECTION_20260904.md"

DECLARED_FAILURES = [
    "generic choreography without character-authored decisions",
    "weak combat physics and insufficient mass transfer",
    "Johnny Cage signature green techniques were not reliably readable",
    "Scorpion powers behaved as decoration instead of owned mechanics",
    "take junctions reset movement instead of inheriting kinetic state",
    "overall direction resembled campy 1990s action rather than grounded live action",
]

PRESERVED_STRENGTHS = [
    "stable visual identity",
    "absence of visible anatomy hallucinations",
    "practical live-action materials",
    "coherent Living Forest geography and photographic language",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)


def verify_hash(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected.upper():
        raise RuntimeError(
            f"Hash mismatch for {path}: expected {expected.upper()}, got {actual}"
        )


def append_unique_history(
    history: list[Any], entry: dict[str, Any], *, discriminator: str
) -> None:
    if any(
        isinstance(item, dict) and item.get(discriminator) == entry.get(discriminator)
        for item in history
    ):
        return
    history.append(entry)


def main() -> int:
    script_path = Path(__file__).resolve()
    pemara_root = script_path.parents[3]
    project_root = (
        pemara_root
        / "ferramentas"
        / "video_global_engine"
        / "projetos"
        / PROJECT_ID
    )
    studio_root = pemara_root / "services" / "studio"
    sys.path.insert(0, str(studio_root))

    from live_action_workflows import advance_live_action_state  # noqa: PLC0415

    now = datetime.now().astimezone()
    timestamp = now.isoformat(timespec="seconds")
    backup_stamp = now.strftime("%Y%m%d_%H%M%S")

    required = [
        project_root / "production_manifest.json",
        project_root / "project_manifest.json",
        project_root / "take_queue.json",
        project_root / R15_LIFECYCLE_REL,
        project_root / COMBAT_PLAN_REL,
        project_root / ANCHOR_PLAN_REL,
        project_root / HANDOFFS_REL,
        project_root / DIRECTION_REL,
        project_root / REJECTION_REPORT_REL,
        project_root / R15_MASTER_REL,
        project_root / IDENTITY_REFERENCE_REL,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Missing required project artifacts:\n" + "\n".join(missing))

    verify_hash(project_root / R15_MASTER_REL, R15_MASTER_SHA256)
    verify_hash(project_root / IDENTITY_REFERENCE_REL, IDENTITY_REFERENCE_SHA256)

    hashes = {
        "combatPlan": sha256(project_root / COMBAT_PLAN_REL),
        "anchorPlan": sha256(project_root / ANCHOR_PLAN_REL),
        "kineticHandoffs": sha256(project_root / HANDOFFS_REL),
        "direction": sha256(project_root / DIRECTION_REL),
        "rejectionReport": sha256(project_root / REJECTION_REPORT_REL),
    }

    touched_before = [
        project_root / "production_manifest.json",
        project_root / "project_manifest.json",
        project_root / "take_queue.json",
        project_root / R15_LIFECYCLE_REL,
    ]
    backup_root = (
        project_root
        / "state_backups"
        / f"before_r16_signature_combat_{backup_stamp}"
    )
    backup_root.mkdir(parents=True, exist_ok=False)
    backup_records: list[dict[str, str]] = []
    for source in touched_before:
        relative = source.relative_to(project_root)
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        backup_records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(destination),
            }
        )
    write_json(
        backup_root / "backup_manifest.json",
        {
            "schemaVersion": "cage-x-scorpion-state-backup@1",
            "projectId": PROJECT_ID,
            "createdAt": timestamp,
            "reason": "Before registering owner rejection of R15 and activating the R16 signature-combat plan",
            "files": backup_records,
        },
    )

    r15_lifecycle_path = project_root / R15_LIFECYCLE_REL
    r15_lifecycle = load_json(r15_lifecycle_path)
    rejection_already_recorded = any(
        isinstance(item, dict)
        and item.get("type") == "LIVE_ACTION_OWNER_ROUTE_REJECTED"
        for item in r15_lifecycle.get("history", [])
    )
    if not rejection_already_recorded:
        r15_lifecycle = advance_live_action_state(
            r15_lifecycle,
            {
                "type": "LIVE_ACTION_OWNER_ROUTE_REJECTED",
                "actor": "owner",
                "scope": REPLACEMENT_SCOPE,
                "artifact": {
                    "path": R15_MASTER_REL,
                    "sha256": R15_MASTER_SHA256,
                    "status": "OWNER_REJECTED_PRESERVED_ROLLBACK_ONLY",
                    "recoverable": True,
                },
                "declaredFailures": DECLARED_FAILURES,
                "strengthsPreservedAsConstraints": PRESERVED_STRENGTHS,
            },
            workspace_root=pemara_root,
        )
        r15_lifecycle["history"][-1].update(
            {
                "at": timestamp,
                "artifact": R15_MASTER_REL,
                "sha256": R15_MASTER_SHA256,
                "report": REJECTION_REPORT_REL,
            }
        )
    r15_lifecycle.update(
        {
            "routeId": R15_ROUTE_ID,
            "renderAuthorized": False,
            "assemblyAllowed": False,
            "technicalFinishPreauthorized": False,
            "promotionAllowed": False,
            "humanReviewRequired": False,
            "ownerReview": "REJECTED_ART_DIRECTION_COMBAT_PHYSICS_CHARACTER_IDENTITY",
            "nextRequiredEvent": None,
            "nextRequiredAuthority": None,
            "currentBlocker": "OWNER_REJECTED_ROUTE_PRESERVED_ROLLBACK_ONLY",
            "successorRoute": R16_ROUTE_ID,
            "rejectionReport": REJECTION_REPORT_REL,
            "updatedAt": timestamp,
        }
    )
    write_json(r15_lifecycle_path, r15_lifecycle)

    rejected_artifact = {
        "path": R15_MASTER_REL,
        "sha256": R15_MASTER_SHA256,
        "status": "OWNER_REJECTED_PRESERVED_ROLLBACK_ONLY",
        "recoverable": True,
        "scope": REPLACEMENT_SCOPE,
    }
    r16_lifecycle = {
        "schemaVersion": "cage-x-scorpion-live-action-state@1",
        "eventContract": "ferramentas/video_global_engine/workflows/minimax_h3_live_action/events.json",
        "projectId": PROJECT_ID,
        "routeId": R16_ROUTE_ID,
        "predecessorRouteId": R15_ROUTE_ID,
        "state": "ROUTE_REPLACEMENT_REQUIRED",
        "history": [
            {
                "type": "LIVE_ACTION_OWNER_ROUTE_REJECTED",
                "actor": "owner",
                "from": "FINISH_CANDIDATE_READY",
                "to": "ROUTE_REPLACEMENT_REQUIRED",
                "scope": REPLACEMENT_SCOPE,
                "at": timestamp,
                "inheritedFrom": R15_LIFECYCLE_REL,
            }
        ],
        "preservedArtifacts": [rejected_artifact],
        "replacementScope": REPLACEMENT_SCOPE,
        "sameScopeReplacementAuthorized": True,
        "rejectedRoutePreserved": True,
        "routeRejection": {
            "declaredFailures": DECLARED_FAILURES,
            "strengthsPreservedAsConstraints": PRESERVED_STRENGTHS,
        },
        "renderAuthorized": False,
        "assemblyAllowed": False,
        "promotionAllowed": False,
    }
    r16_lifecycle = advance_live_action_state(
        r16_lifecycle,
        {
            "type": "LIVE_ACTION_SIGNATURE_COMBAT_PLAN_REGISTERED",
            "actor": "technical",
            "scope": REPLACEMENT_SCOPE,
            "combatPlan": {
                "path": COMBAT_PLAN_REL,
                "sha256": hashes["combatPlan"],
            },
        },
        workspace_root=pemara_root,
    )
    r16_lifecycle["history"][-1]["at"] = timestamp
    r16_lifecycle.update(
        {
            "renderAuthorized": False,
            "assemblyAllowed": False,
            "promotionAllowed": False,
            "humanReviewRequired": True,
            "nextRequiredEvent": "LIVE_ACTION_SIGNATURE_COMBAT_PLAN_APPROVED",
            "nextRequiredAuthority": "owner",
            "currentBlocker": "OWNER_COMBAT_PLAN_REVIEW",
            "anchorGenerationAuthorized": False,
            "anchorsGenerated": 0,
            "takesGenerated": 0,
            "gpuTouched": False,
            "kineticHandoffs": {
                "path": HANDOFFS_REL,
                "sha256": hashes["kineticHandoffs"],
            },
            "updatedAt": timestamp,
        }
    )
    write_json(project_root / R16_LIFECYCLE_REL, r16_lifecycle)

    r16_manifest = {
        "schemaVersion": "cage-x-scorpion-r16-production@1",
        "projectId": PROJECT_ID,
        "routeId": R16_ROUTE_ID,
        "predecessorRouteId": R15_ROUTE_ID,
        "status": "COMBAT_PLAN_PENDING_OWNER_REVIEW",
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "objective": "Grounded live-action fight whose character identity, owned signature mechanics, mass transfer and kinetic continuity remain readable without audio.",
        "preservationPolicy": {
            "r15MasterPreserved": True,
            "r15Master": R15_MASTER_REL,
            "r15MasterSha256": R15_MASTER_SHA256,
            "r15PromotionAllowed": False,
            "reuseFromR15": [
                "casting reference",
                "costume and material language",
                "Living Forest geography",
                "photographic language",
            ],
            "forbiddenReuse": [
                "R15 video bitstreams",
                "R15 choreography",
                "R15 connectors",
                "R15 Foley or mix",
                "R15 owner approval",
            ],
        },
        "supervision": {
            "showrunner": "pemara-live-action-showrunner",
            "combatDirector": "pemara-live-action-combat-director",
            "kineticSupervisor": "pemara-live-action-kinetic-supervisor",
            "continuity": "pemara-live-action-continuity",
            "motionDirector": "pemara-video-motion-director",
            "qc": "pemara-live-action-qc",
        },
        "workflow": {
            "id": "h3_live_action_signature_combat",
            "definition": "../../../../workflows/minimax_h3_live_action/signature-combat.workflow.json",
            "engine": "minimax_h3",
            "model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
            "mode": "FL2VA",
            "fallbackAllowed": False,
            "nativeAudio": False,
            "qualityProfile": "h3_production",
            "width": 1088,
            "height": 608,
            "steps": 10,
            "fps": 24,
            "framesPerUnit": 124,
            "effectiveSecondsPerUnit": 5.1667,
            "unitCount": 12,
            "approximateSequenceSecondsBeforeEdit": 62.0,
        },
        "artifacts": {
            "direction": {"path": DIRECTION_REL, "sha256": hashes["direction"]},
            "combatPlan": {
                "path": COMBAT_PLAN_REL,
                "sha256": hashes["combatPlan"],
            },
            "anchorPlan": {
                "path": ANCHOR_PLAN_REL,
                "sha256": hashes["anchorPlan"],
            },
            "kineticHandoffs": {
                "path": HANDOFFS_REL,
                "sha256": hashes["kineticHandoffs"],
            },
            "lifecycle": {"path": R16_LIFECYCLE_REL},
            "r15RejectionReport": {
                "path": REJECTION_REPORT_REL,
                "sha256": hashes["rejectionReport"],
            },
            "identityReference": {
                "path": IDENTITY_REFERENCE_REL,
                "sha256": IDENTITY_REFERENCE_SHA256,
                "scope": "casting, costumes, materials and world only",
            },
        },
        "identityPolicy": {
            "visualIdentity": "immutable",
            "combatIdentity": "owned mechanics and performance envelope",
            "powers": {
                "johnnyCage": "green energy attached only to Cage techniques",
                "scorpion": "hellfire, chain and kunai attached only to Scorpion",
            },
            "forbidden": [
                "ice powers",
                "power ownership swap",
                "generic model-selected strikes",
                "decorative detached effects",
            ],
        },
        "kineticContinuityPolicy": {
            "preferredJunction": "DIRECT_KINETIC_CUT",
            "allowedStates": [
                "MATCH",
                "RECOVERABLE_BY_CAUSAL_CONNECTOR",
                "SOURCE_REGEN_REQUIRED",
            ],
            "sourceRegenerationRequiredFor": [
                "center-of-mass reset",
                "support-foot mismatch",
                "action-phase discontinuity",
                "camera geography contradiction",
                "weapon or effect lifecycle contradiction",
                "persistent environment damage reset",
            ],
            "crossfadeFrames": 0,
            "freezeFrames": 0,
            "staticHoldFrames": 0,
            "rifeAcrossCuts": False,
        },
        "gates": {
            "combatPlanOwnerApproved": False,
            "anchorsGenerated": False,
            "anchorsOwnerApprovedByExactHash": False,
            "preflightPassed": False,
            "freshGpuAdmissionPassed": False,
            "renderAuthorized": False,
            "assemblyAllowed": False,
            "promotionAllowed": False,
        },
        "generation": {
            "paused": True,
            "queued": 0,
            "anchorsGenerated": 0,
            "takesGenerated": 0,
            "connectorsGenerated": 0,
            "gpuTouched": False,
        },
        "nextRequiredEvent": "LIVE_ACTION_SIGNATURE_COMBAT_PLAN_APPROVED",
        "nextRequiredAuthority": "owner",
    }
    write_json(project_root / R16_MANIFEST_REL, r16_manifest)

    root_manifest_path = project_root / "production_manifest.json"
    root_manifest = load_json(root_manifest_path)
    root_manifest.update(
        {
            "status": "ACTIVE_R16_COMBAT_PLAN_PENDING_OWNER_REVIEW",
            "active_route_id": R16_ROUTE_ID,
            "proposed_route_id": R16_ROUTE_ID,
            "proposed_route_status": "COMBAT_PLAN_PENDING_OWNER_REVIEW",
            "proposed_route_document": DIRECTION_REL,
            "active_route_manifest": R16_MANIFEST_REL,
            "visual_route_id": R16_ROUTE_ID,
            "art_direction_bible": DIRECTION_REL,
            "duration_target_seconds": 62.0,
            "main_take_count": 12,
            "main_take_duration_seconds": 5.1667,
            "opening_rule": "Open at peak action and widen physically through the same still-moving chain and existing tree damage; no rewind, reset, fade, freeze or card.",
            "ending_rule": "End while the final Shadow Kick drives Scorpion into the already-damaged tree and the environment continues collapsing; no campy body separation or held pose.",
            "fatality_in_current_scope": False,
            "generation_paused": True,
            "video_generation_paused": True,
            "generation_authorized": False,
            "render_authorized": False,
            "authorization_scope": None,
            "combat_style_contract": COMBAT_PLAN_REL,
            "updated_at": timestamp,
            "legacy_take_records_route_id": R15_ROUTE_ID,
            "takes_active_for_current_route": False,
        }
    )
    root_manifest["live_action_workflow"] = {
        "schema_version": "pemara-minimax-h3-live-action@1",
        "status": "COMBAT_PLAN_PENDING_OWNER_REVIEW",
        "workflow_id": "h3_live_action_signature_combat",
        "workflow_pack": "../../workflows/minimax_h3_live_action/manifest.json",
        "route_manifest": R16_MANIFEST_REL,
        "combat_plan": COMBAT_PLAN_REL,
        "anchor_plan": ANCHOR_PLAN_REL,
        "kinetic_handoffs": HANDOFFS_REL,
        "lifecycle": R16_LIFECYCLE_REL,
        "engine": "minimax_h3",
        "fallback_allowed": False,
        "native_audio": False,
        "render_authorized": False,
        "assembly_allowed": False,
        "takes_queued": 0,
        "videos_generated": 0,
        "predecessor_route": R15_ROUTE_ID,
        "rejected_master": R15_MASTER_REL,
    }
    root_manifest["video_generation"].update(
        {
            "workflow_id": "h3_live_action_signature_combat",
            "configuration_source": COMBAT_PLAN_REL,
            "quality_profile": "h3_production",
            "width": 1088,
            "height": 608,
            "fps": 24,
            "frames": 124,
            "effective_duration_seconds": 5.1667,
            "steps": 10,
            "input_mode": "APPROVED_START_CONTACT_END_ANCHORS",
            "native_audio": False,
            "fallback_allowed": False,
            "generic_worker_block_reason": "R16 requires owner-approved combat plan and exact-hash action anchors before materialization or queue admission.",
        }
    )
    root_manifest["gate_status"] = {
        "combat_plan": "PENDING_OWNER_REVIEW",
        "anchors": "NOT_GENERATED",
        "anchor_exact_hash_approval": "NOT_STARTED",
        "comfy_graph": "NOT_MATERIALIZED",
        "runtime": "NOT_TOUCHED",
        "gpu_admission": "NOT_STARTED",
        "take_generation": "NOT_STARTED",
        "kinetic_junction_qc": "NOT_STARTED",
        "render_authorization": "BLOCKED_PENDING_OWNER_PLAN_AND_ANCHOR_APPROVAL",
    }
    root_manifest["r15_delivery"].update(
        {
            "status": "OWNER_REJECTED_PRESERVED_ROLLBACK_ONLY",
            "humanReview": "REJECTED_BY_OWNER",
            "promotionAllowed": False,
            "rejectionReport": REJECTION_REPORT_REL,
            "supersededBy": R16_ROUTE_ID,
        }
    )
    root_manifest["r16_signature_combat"] = {
        "status": "COMBAT_PLAN_PENDING_OWNER_REVIEW",
        "manifest": R16_MANIFEST_REL,
        "combatPlan": COMBAT_PLAN_REL,
        "anchorPlan": ANCHOR_PLAN_REL,
        "kineticHandoffs": HANDOFFS_REL,
        "lifecycle": R16_LIFECYCLE_REL,
        "anchorsGenerated": 0,
        "takesGenerated": 0,
        "renderAuthorized": False,
        "assemblyAllowed": False,
        "promotionAllowed": False,
    }
    if isinstance(root_manifest.get("assembly"), dict):
        root_manifest["assembly"].update(
            {
                "status": "R15_OWNER_REJECTED_PRESERVED_ROLLBACK_ONLY",
                "all_sources_owner_approved": False,
                "assemblyAllowed": False,
                "promotionAllowed": False,
                "activeForCurrentRoute": False,
            }
        )
    write_json(root_manifest_path, root_manifest)

    project_manifest_path = project_root / "project_manifest.json"
    project_manifest = load_json(project_manifest_path)
    old_final = copy.deepcopy(project_manifest.get("final_output"))
    history = project_manifest.setdefault("final_output_history", [])
    if isinstance(old_final, dict):
        rejected_history = copy.deepcopy(old_final)
        rejected_history.update(
            {
                "route_id": R15_ROUTE_ID,
                "status": "OWNER_REJECTED_ART_DIRECTION_COMBAT_PHYSICS_CHARACTER_IDENTITY",
                "human_review_status": "REJECTED_BY_OWNER",
                "promotion_allowed": False,
                "rejection_report": REJECTION_REPORT_REL,
                "superseded_by": R16_ROUTE_ID,
                "recorded_at": timestamp,
            }
        )
        append_unique_history(history, rejected_history, discriminator="status")
        old_final.update(
            {
                "route_id": R15_ROUTE_ID,
                "qc_status": "TECHNICAL_PASS_OWNER_REJECTED_ART_DIRECTION_COMBAT_PHYSICS_CHARACTER_IDENTITY",
                "active": False,
                "promotion_allowed": False,
                "rejection_report": REJECTION_REPORT_REL,
                "superseded_by": R16_ROUTE_ID,
            }
        )
        old_final["human_review"] = {
            "status": "REJECTED_BY_OWNER",
            "required": False,
            "reason": "Art direction, combat physics, signature identity and take connections",
        }
        project_manifest["final_output"] = old_final
    project_manifest.update(
        {
            "updated_at": timestamp,
            "maestro_status": "R16_COMBAT_PLAN_PENDING_OWNER_REVIEW",
            "generation_paused": True,
            "active_route_id": R16_ROUTE_ID,
            "active_route_manifest": R16_MANIFEST_REL,
            "combat_style_contract": COMBAT_PLAN_REL,
        }
    )
    project_manifest["active_anchor_review"] = {
        "status": "NOT_GENERATED_PENDING_OWNER_COMBAT_PLAN_REVIEW",
        "route_id": R16_ROUTE_ID,
        "plan": ANCHOR_PLAN_REL,
        "planned_images": 25,
        "generated_images": 0,
        "owner_approved_images": 0,
        "video_generation_authorized": False,
        "identity_reference": IDENTITY_REFERENCE_REL,
        "identity_reference_scope": "casting, costumes, materials and world only",
    }
    project_manifest["live_action_workflow"] = copy.deepcopy(
        root_manifest["live_action_workflow"]
    )
    project_manifest["r16_plan"] = copy.deepcopy(root_manifest["r16_signature_combat"])
    write_json(project_manifest_path, project_manifest)

    take_queue_path = project_root / "take_queue.json"
    take_queue = load_json(take_queue_path)
    take_queue.update(
        {
            "route_id": R16_ROUTE_ID,
            "status": "R16_COMBAT_PLAN_PENDING_OWNER_REVIEW",
            "generation_authorized": False,
            "generation_paused": True,
            "render_authorized": False,
            "updated_at": timestamp,
            "combat_style_contract": COMBAT_PLAN_REL,
            "active_route_manifest": R16_MANIFEST_REL,
            "resume_gate": "OWNER_COMBAT_PLAN_APPROVED_THEN_IMAGEGEN_ANCHORS_EXACT_HASH_APPROVED_THEN_PREFLIGHT_AND_FRESH_GPU_ADMISSION_THEN_OWNER_RENDER_AUTHORIZED",
            "legacy_take_records_route_id": R15_ROUTE_ID,
            "takes_active_for_current_route": False,
        }
    )
    take_queue["live_action_workflow"] = copy.deepcopy(
        root_manifest["live_action_workflow"]
    )
    take_queue["engine_lock"].update(
        {
            "profile": "h3_production_1088x608_10_steps_signature_combat",
            "profile_manifest": R16_MANIFEST_REL,
            "pilot_render_authorized_take": None,
            "substitution_authorized": False,
            "native_audio": False,
        }
    )
    take_queue["production_batch"] = {
        "mode": "serial_gate",
        "current": "R16_COMBAT_PLAN_PENDING_OWNER_REVIEW",
        "continue_automatically": False,
        "reason": "Combat direction must be owner-approved before ImageGen anchors; exact-hash anchors, preflight, fresh GPU admission and render authorization remain separate gates.",
    }
    take_queue["anchor_generation_policy"].update(
        {
            "provider": "OpenAI built-in ImageGen",
            "exact_hash_required": True,
            "all_video_anchors_present": False,
            "new_anchor_generation_authorized": False,
            "planned_anchor_count": 25,
            "generated_anchor_count": 0,
            "owner_approved_anchor_count": 0,
            "plan": ANCHOR_PLAN_REL,
        }
    )
    take_queue["assembly"].update(
        {
            "status": "BLOCKED_R16_NO_TAKES",
            "rule": "twelve_signature_combat_units_with_shared_dynamic_boundaries_and_direct_kinetic_cuts_by_default",
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
            "rife_across_cuts": False,
            "assembly_allowed": False,
        }
    )
    for take in take_queue.get("takes") or []:
        if not isinstance(take, dict):
            continue
        if take.get("render_authorized") is True:
            take["legacy_render_authorized_before_r16_route_rejection"] = True
        take["render_authorized"] = False
        take["active_for_current_route"] = False
        take["legacy_route_id"] = R15_ROUTE_ID
    take_queue["r15_master_candidate"].update(
        {
            "status": "OWNER_REJECTED_ART_DIRECTION_COMBAT_PHYSICS_CHARACTER_IDENTITY",
            "humanReview": "REJECTED_BY_OWNER",
            "promotionAllowed": False,
            "preserved": True,
            "rejectionReport": REJECTION_REPORT_REL,
            "supersededBy": R16_ROUTE_ID,
        }
    )
    take_queue["r16_plan"] = {
        "status": "COMBAT_PLAN_PENDING_OWNER_REVIEW",
        "manifest": R16_MANIFEST_REL,
        "combatPlan": COMBAT_PLAN_REL,
        "combatPlanSha256": hashes["combatPlan"],
        "anchorPlan": ANCHOR_PLAN_REL,
        "kineticHandoffs": HANDOFFS_REL,
        "unitCount": 12,
        "framesPerUnit": 124,
        "nativeFps": 24,
        "anchorsGenerated": 0,
        "takesQueued": 0,
        "takesGenerated": 0,
        "renderAuthorized": False,
    }
    write_json(take_queue_path, take_queue)

    result = {
        "ok": True,
        "projectId": PROJECT_ID,
        "activeRoute": R16_ROUTE_ID,
        "state": "COMBAT_PLAN_PENDING_OWNER_REVIEW",
        "backup": str(backup_root),
        "r15MasterVerified": R15_MASTER_SHA256,
        "identityReferenceVerified": IDENTITY_REFERENCE_SHA256,
        "combatPlanSha256": hashes["combatPlan"],
        "anchorsGenerated": 0,
        "takesGenerated": 0,
        "renderAuthorized": False,
        "gpuTouched": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
