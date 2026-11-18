"""Fail-closed MiniMax H3 workflow contracts for Pemara live action.

The module compiles declarative, reviewable production plans.  It never queues
ComfyUI, starts a GPU job, promotes a candidate, or infers owner approval.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any


LIVE_ACTION_PACK_VERSION = "pemara-minimax-h3-live-action@1"
PACK_RELATIVE_ROOT = Path(
    "ferramentas/video_global_engine/workflows/minimax_h3_live_action"
)
VALID_RISKS = {"normal", "high", "critical"}
MOTION_BEATS = ("early_0_30", "middle_30_70", "late_70_100")
CONTINUOUS_COMBAT_WORKFLOW_IDS = {
    "h3_live_action_continuous_bilateral_combat_8s",
    "h3_live_action_continuous_bilateral_start_chain_8s",
}
START_CHAIN_WORKFLOW_ID = "h3_live_action_continuous_bilateral_start_chain_8s"
IDENTITY_FIELDS = (
    "id",
    "face",
    "bodyScale",
    "wardrobe",
    "anatomy",
    "forbiddenChanges",
    "stateByBeat",
)
COMBAT_IDENTITY_TEXT_FIELDS = ("id", "combatPersonality", "visualSignature")
PHYSICS_CHAIN_FIELDS = (
    "anticipation",
    "propulsion",
    "contact",
    "displacement",
    "reaction",
    "recovery",
)
CONTINUOUS_EXCHANGE_FIELDS = (
    "id",
    "attackerId",
    "defenderId",
    "mechanic",
    "phase",
    "supportAndPropulsion",
    "visibleContactOrEvasion",
    "defenderResponseAfterCause",
    "groundTranslationMechanism",
    "environmentalLag",
    "activeRecovery",
)
EFFECT_LIFECYCLE_FIELDS = (
    "attachment",
    "onset",
    "trajectory",
    "contact",
    "decay",
    "environmentalConsequence",
)
VALID_EFFECT_TYPES = {"none", "energy", "fire", "ice", "weapon", "hybrid"}
KINETIC_CHARACTER_FIELDS = (
    "characterId",
    "screenPosition",
    "rootVector",
    "speedClass",
    "weightBearingFoot",
    "torsoAngularDirection",
    "limbPhase",
    "gazeTarget",
    "contactState",
    "damageFatigueState",
)
KINETIC_AFFINITY_CHANNELS = (
    "characters",
    "actionPhase",
    "cameraGeography",
    "objectEffects",
    "environment",
)
KINETIC_PASS_DECISIONS = {"MATCH", "RECOVERABLE_BY_CAUSAL_CONNECTOR"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class LiveActionContractError(ValueError):
    """Raised when a live-action plan would make an unsupported claim."""

    def __init__(self, errors: list[str] | tuple[str, ...] | str) -> None:
        if isinstance(errors, str):
            errors = [errors]
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _workspace_root(workspace_root: Path | str | None) -> Path:
    if workspace_root is None:
        return Path(__file__).resolve().parents[2]
    return Path(workspace_root).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LiveActionContractError(f"PACK_FILE_MISSING: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LiveActionContractError(
            f"PACK_JSON_INVALID: {path}:{exc.lineno}:{exc.colno}"
        ) from exc
    if not isinstance(value, dict):
        raise LiveActionContractError(f"PACK_OBJECT_REQUIRED: {path}")
    return value


def load_live_action_pack(
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Load and structurally validate the declarative workflow pack."""

    pack_root = _workspace_root(workspace_root) / PACK_RELATIVE_ROOT
    manifest = _read_json(pack_root / "manifest.json")
    errors: list[str] = []
    if manifest.get("schemaVersion") != LIVE_ACTION_PACK_VERSION:
        errors.append(
            "PACK_VERSION_MISMATCH: "
            f"expected {LIVE_ACTION_PACK_VERSION}, got {manifest.get('schemaVersion')}"
        )
    workflow_files = manifest.get("workflowFiles")
    if not isinstance(workflow_files, list) or not workflow_files:
        errors.append("PACK_WORKFLOW_FILES_REQUIRED")
        workflow_files = []

    workflows: list[dict[str, Any]] = []
    workflow_ids: set[str] = set()
    for relative in workflow_files:
        workflow = _read_json(pack_root / str(relative))
        workflow_id = str(workflow.get("id") or "")
        if not workflow_id:
            errors.append(f"WORKFLOW_ID_REQUIRED: {relative}")
        elif workflow_id in workflow_ids:
            errors.append(f"WORKFLOW_ID_DUPLICATE: {workflow_id}")
        workflow_ids.add(workflow_id)
        if workflow.get("engine") != "minimax_h3":
            errors.append(f"WORKFLOW_ENGINE_INVALID: {workflow_id}")
        if workflow.get("fallbackAllowed") is not False:
            errors.append(f"WORKFLOW_FALLBACK_FORBIDDEN: {workflow_id}")
        workflows.append(workflow)

    events_file = str(manifest.get("eventsFile") or "")
    events = _read_json(pack_root / events_file) if events_file else {}
    event_types = events.get("eventTypes")
    if not isinstance(event_types, list) or not event_types:
        errors.append("PACK_EVENT_TYPES_REQUIRED")

    quality_profiles = manifest.get("qualityProfiles")
    if not isinstance(quality_profiles, dict):
        errors.append("PACK_QUALITY_PROFILES_REQUIRED")

    if errors:
        raise LiveActionContractError(errors)

    return {
        **manifest,
        "root": str(pack_root),
        "workflows": workflows,
        "events": events,
    }


def workflow_pack_status(
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return a read-only status report; no model or GPU is touched."""

    try:
        pack = load_live_action_pack(workspace_root)
    except LiveActionContractError as exc:
        return {
            "ok": False,
            "version": LIVE_ACTION_PACK_VERSION,
            "workflowIds": [],
            "eventTypes": [],
            "errors": exc.errors,
            "gpuTouched": False,
        }
    return {
        "ok": True,
        "version": pack["schemaVersion"],
        "workflowIds": [item["id"] for item in pack["workflows"]],
        "eventTypes": [item["type"] for item in pack["events"]["eventTypes"]],
        "errors": [],
        "gpuTouched": False,
    }


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_approved_artifact(
    value: Any,
    label: str,
    errors: list[str],
    *,
    moving_boundary: bool = False,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"APPROVED_ARTIFACT_REQUIRED[{label}]")
        return
    if not _has_text(value.get("path")):
        errors.append(f"ARTIFACT_PATH_REQUIRED[{label}]")
    if not SHA256_RE.fullmatch(str(value.get("sha256") or "")):
        errors.append(f"ARTIFACT_SHA256_REQUIRED[{label}]")
    if value.get("ownerApproved") is not True:
        errors.append(f"OWNER_APPROVAL_REQUIRED[{label}]")
    if not _has_text(value.get("approvalScope")):
        errors.append(f"APPROVAL_SCOPE_REQUIRED[{label}]")
    if moving_boundary:
        moving = value.get("movingContext")
        if not isinstance(moving, dict) or not (
            moving.get("hasMotionBefore") is True
            and moving.get("hasMotionAfter") is True
        ):
            errors.append(f"MOVING_BOUNDARY_REQUIRED[{label}]")


def _validate_identity_matrix(value: Any, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not value:
        errors.append("IDENTITY_MATRIX_REQUIRED")
        return set()
    ids: set[str] = set()
    for index, character in enumerate(value, start=1):
        if not isinstance(character, dict):
            errors.append(f"IDENTITY_CHARACTER_INVALID[{index}]")
            continue
        for field in IDENTITY_FIELDS:
            field_value = character.get(field)
            if field == "forbiddenChanges":
                valid = isinstance(field_value, list) and bool(field_value)
            elif field == "stateByBeat":
                valid = isinstance(field_value, dict) and all(
                    _has_text(field_value.get(beat)) for beat in MOTION_BEATS
                )
            else:
                valid = _has_text(field_value)
            if not valid:
                errors.append(f"IDENTITY_FIELD_REQUIRED[{index}.{field}]")
        character_id = str(character.get("id") or "")
        if character_id and character_id in ids:
            errors.append(f"IDENTITY_ID_DUPLICATE[{character_id}]")
        ids.add(character_id)
    return ids


def _validate_combat_identity_matrix(
    value: Any, identity_ids: set[str], errors: list[str]
) -> dict[str, set[str]]:
    if not isinstance(value, list) or not value:
        errors.append("COMBAT_IDENTITY_MATRIX_REQUIRED")
        return {}
    mechanics_by_id: dict[str, set[str]] = {}
    combat_ids: set[str] = set()
    for index, character in enumerate(value, start=1):
        if not isinstance(character, dict):
            errors.append(f"COMBAT_IDENTITY_CHARACTER_INVALID[{index}]")
            continue
        for field in COMBAT_IDENTITY_TEXT_FIELDS:
            if not _has_text(character.get(field)):
                errors.append(f"COMBAT_IDENTITY_FIELD_REQUIRED[{index}.{field}]")
        character_id = str(character.get("id") or "").strip()
        if character_id in combat_ids:
            errors.append(f"COMBAT_IDENTITY_ID_DUPLICATE[{character_id}]")
        combat_ids.add(character_id)
        owned = character.get("ownedMechanics")
        forbidden = character.get("forbiddenMechanics")
        if not isinstance(owned, list) or not all(_has_text(item) for item in owned):
            errors.append(f"OWNED_MECHANICS_REQUIRED[{index}]")
            owned_set: set[str] = set()
        else:
            owned_set = {str(item).strip() for item in owned}
        if not isinstance(forbidden, list) or not all(
            _has_text(item) for item in forbidden
        ):
            errors.append(f"FORBIDDEN_MECHANICS_REQUIRED[{index}]")
            forbidden_set: set[str] = set()
        else:
            forbidden_set = {str(item).strip() for item in forbidden}
        overlap = sorted(owned_set & forbidden_set)
        if overlap:
            errors.append(
                f"COMBAT_MECHANIC_OWNERSHIP_CONFLICT[{character_id}:{','.join(overlap)}]"
            )
        if character_id:
            mechanics_by_id[character_id] = owned_set
    if combat_ids != identity_ids:
        missing = sorted(identity_ids - combat_ids)
        extra = sorted(combat_ids - identity_ids)
        errors.append(
            "COMBAT_IDENTITY_CAST_MISMATCH: "
            f"missing={','.join(missing) or 'none'} extra={','.join(extra) or 'none'}"
        )
    return mechanics_by_id


def _validate_signature_move_contract(
    value: Any, mechanics_by_id: dict[str, set[str]], errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append("SIGNATURE_MOVE_CONTRACT_REQUIRED")
        return
    for field in (
        "moveId",
        "ownerId",
        "opponentId",
        "canonicalMechanic",
        "outcome",
        "cutMotivation",
    ):
        if not _has_text(value.get(field)):
            errors.append(f"SIGNATURE_MOVE_FIELD_REQUIRED[{field}]")
    move_id = str(value.get("moveId") or "").strip()
    owner_id = str(value.get("ownerId") or "").strip()
    opponent_id = str(value.get("opponentId") or "").strip()
    if owner_id not in mechanics_by_id:
        errors.append(f"SIGNATURE_MOVE_OWNER_UNKNOWN[{owner_id or 'missing'}]")
    elif move_id and move_id not in mechanics_by_id[owner_id]:
        errors.append(f"SIGNATURE_MOVE_NOT_OWNED[{owner_id}:{move_id}]")
    if opponent_id not in mechanics_by_id:
        errors.append(f"SIGNATURE_MOVE_OPPONENT_UNKNOWN[{opponent_id or 'missing'}]")
    if owner_id and owner_id == opponent_id:
        errors.append("SIGNATURE_MOVE_OWNER_OPPONENT_MUST_DIFFER")
    if value.get("modelMayChooseDifferentMove") is not False:
        errors.append("MODEL_SELECTED_MOVE_FORBIDDEN")
    try:
        exchange_count = int(value.get("dominantExchangeCount") or 0)
    except (TypeError, ValueError):
        exchange_count = 0
    if exchange_count != 1:
        errors.append("ONE_DOMINANT_EXCHANGE_REQUIRED")

    physics = value.get("physicsChain")
    if not isinstance(physics, dict) or not all(
        _has_text(physics.get(field)) for field in PHYSICS_CHAIN_FIELDS
    ):
        errors.append("COMPLETE_PHYSICS_CHAIN_REQUIRED")

    effect = value.get("effectLifecycle")
    if not isinstance(effect, dict):
        errors.append("EFFECT_LIFECYCLE_REQUIRED")
    else:
        effect_type = str(effect.get("type") or "").strip().lower()
        if effect_type not in VALID_EFFECT_TYPES:
            errors.append("EFFECT_TYPE_INVALID")
        if str(effect.get("ownerId") or "").strip() != owner_id:
            errors.append("EFFECT_OWNER_MUST_MATCH_MOVE_OWNER")
        if not all(_has_text(effect.get(field)) for field in EFFECT_LIFECYCLE_FIELDS):
            errors.append("COMPLETE_EFFECT_LIFECYCLE_REQUIRED")
        transfers = effect.get("forbiddenTransfers")
        if not isinstance(transfers, list) or not all(
            _has_text(item) for item in transfers
        ):
            errors.append("EFFECT_FORBIDDEN_TRANSFERS_REQUIRED")

    readability = value.get("readability")
    if not isinstance(readability, dict) or not (
        readability.get("contactVisible") is True
        and readability.get("attackVectorReadable") is True
        and readability.get("cutawayAtImpact") is False
        and readability.get("cameraShakeCarriesImpact") is False
    ):
        errors.append("SIGNATURE_CONTACT_READABILITY_REQUIRED")


def _validate_continuous_combat_contract(
    value: Any, mechanics_by_id: dict[str, set[str]], errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append("CONTINUOUS_COMBAT_CONTRACT_REQUIRED")
        return
    exchanges = value.get("exchanges")
    if not isinstance(exchanges, list) or len(exchanges) < 3:
        errors.append("THREE_RECIPROCAL_EXCHANGES_REQUIRED")
        return
    attackers: set[str] = set()
    phases: set[str] = set()
    for index, exchange in enumerate(exchanges, start=1):
        if not isinstance(exchange, dict):
            errors.append(f"CONTINUOUS_EXCHANGE_INVALID[{index}]")
            continue
        for field in CONTINUOUS_EXCHANGE_FIELDS:
            if not _has_text(exchange.get(field)):
                errors.append(f"CONTINUOUS_EXCHANGE_FIELD_REQUIRED[{index}.{field}]")
        attacker = str(exchange.get("attackerId") or "").strip()
        defender = str(exchange.get("defenderId") or "").strip()
        mechanic = str(exchange.get("mechanic") or "").strip()
        phase = str(exchange.get("phase") or "").strip()
        attackers.add(attacker)
        phases.add(phase)
        if attacker not in mechanics_by_id:
            errors.append(f"CONTINUOUS_ATTACKER_UNKNOWN[{index}:{attacker or 'missing'}]")
        elif mechanic and mechanic not in mechanics_by_id[attacker]:
            errors.append(
                f"CONTINUOUS_MECHANIC_NOT_OWNED[{index}:{attacker}:{mechanic}]"
            )
        if defender not in mechanics_by_id or defender == attacker:
            errors.append(f"CONTINUOUS_DEFENDER_INVALID[{index}:{defender or 'missing'}]")
        if phase not in MOTION_BEATS:
            errors.append(f"CONTINUOUS_PHASE_INVALID[{index}:{phase or 'missing'}]")
        if exchange.get("causeBeforeEffect") is not True:
            errors.append(f"CAUSE_BEFORE_EFFECT_REQUIRED[{index}]")
        if exchange.get("defenderMotionBeforeContactForbidden") is not True:
            errors.append(f"PRECONTACT_REACTION_FORBIDDEN_REQUIRED[{index}]")
    if attackers != set(mechanics_by_id):
        errors.append("BILATERAL_ATTACKERS_REQUIRED")
    if phases != set(MOTION_BEATS):
        errors.append("CONTINUOUS_THREE_PHASE_COVERAGE_REQUIRED")
    if value.get("intermediateGuideAllowed") is not False:
        errors.append("CONTINUOUS_INTERMEDIATE_GUIDE_MUST_BE_FORBIDDEN")
    if value.get("activeCutWithoutConnector") is not True:
        errors.append("ACTIVE_CUT_WITHOUT_PATCH_REQUIRED")


def _validate_motion_contract(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("MOTION_CONTRACT_REQUIRED")
        return
    beats = value.get("beats")
    if not isinstance(beats, dict) or not all(
        _has_text(beats.get(beat)) for beat in MOTION_BEATS
    ):
        errors.append("THREE_INTERVAL_MOTION_REQUIRED")
    camera = value.get("cameraEvidence")
    if not isinstance(camera, dict) or not (
        camera.get("physicalTranslation") is True
        and _has_text(camera.get("perspectiveChange"))
    ):
        errors.append("EVIDENT_CAMERA_REQUIRED")
    depth = value.get("depthPlanes")
    if not isinstance(depth, dict) or not all(
        _has_text(depth.get(key)) for key in ("foreground", "midground", "background")
    ):
        errors.append("REAL_THREE_PLANE_DEPTH_REQUIRED")
    internal_actions = value.get("internalActions")
    if not isinstance(internal_actions, list) or len(
        [item for item in internal_actions if _has_text(item)]
    ) < 2:
        errors.append("TWO_INTERNAL_ACTIONS_REQUIRED")
    progression = value.get("progression")
    if not isinstance(progression, dict) or not all(
        _has_text(progression.get(key)) for key in ("start", "middle", "end")
    ):
        errors.append("CLEAR_PROGRESSION_REQUIRED")


def _validate_kinetic_boundary_state(
    value: Any, label: str, errors: list[str]
) -> set[str]:
    if not isinstance(value, dict):
        errors.append(f"KINETIC_BOUNDARY_STATE_REQUIRED[{label}]")
        return set()
    characters = value.get("characters")
    if not isinstance(characters, list) or not characters:
        errors.append(f"KINETIC_CHARACTERS_REQUIRED[{label}]")
        character_ids: set[str] = set()
    else:
        character_ids = set()
        for index, character in enumerate(characters, start=1):
            if not isinstance(character, dict):
                errors.append(f"KINETIC_CHARACTER_INVALID[{label}:{index}]")
                continue
            if not all(_has_text(character.get(field)) for field in KINETIC_CHARACTER_FIELDS):
                errors.append(f"KINETIC_CHARACTER_STATE_INCOMPLETE[{label}:{index}]")
            character_id = str(character.get("characterId") or "").strip()
            if character_id in character_ids:
                errors.append(f"KINETIC_CHARACTER_DUPLICATE[{label}:{character_id}]")
            character_ids.add(character_id)
            if str(character.get("speedClass") or "").strip().lower() not in {
                "slow",
                "medium",
                "fast",
            }:
                errors.append(f"KINETIC_MOVING_SPEED_REQUIRED[{label}:{character_id}]")
    camera = value.get("camera")
    if not isinstance(camera, dict) or not all(
        _has_text(camera.get(field))
        for field in (
            "positionAndLens",
            "translationVector",
            "speedClass",
            "angularPhase",
            "foregroundOcclusion",
        )
    ):
        errors.append(f"KINETIC_CAMERA_STATE_REQUIRED[{label}]")
    objects = value.get("objectEffects")
    if not isinstance(objects, list):
        errors.append(f"KINETIC_OBJECT_EFFECT_STATE_REQUIRED[{label}]")
    else:
        for index, item in enumerate(objects, start=1):
            if not isinstance(item, dict) or not all(
                _has_text(item.get(field))
                for field in (
                    "id",
                    "ownerId",
                    "anchorPoint",
                    "vectorAndSpeed",
                    "tensionOrLifecyclePhase",
                )
            ):
                errors.append(f"KINETIC_OBJECT_EFFECT_INCOMPLETE[{label}:{index}]")
    environment = value.get("environment")
    if not isinstance(environment, dict) or not all(
        _has_text(environment.get(field))
        for field in (
            "persistentDamage",
            "movingElements",
            "foreground",
            "midground",
            "background",
        )
    ):
        errors.append(f"KINETIC_ENVIRONMENT_STATE_REQUIRED[{label}]")
    return character_ids


def _validate_kinetic_handoff(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("KINETIC_HANDOFF_CONTRACT_REQUIRED")
        return
    source_ids = _validate_kinetic_boundary_state(
        value.get("sourceExit"), "sourceExit", errors
    )
    destination_ids = _validate_kinetic_boundary_state(
        value.get("destinationEntry"), "destinationEntry", errors
    )
    if source_ids != destination_ids:
        errors.append("KINETIC_HANDOFF_CAST_MISMATCH")
    affinity = value.get("affinity")
    if not isinstance(affinity, dict):
        errors.append("KINETIC_AFFINITY_REQUIRED")
    else:
        for channel in KINETIC_AFFINITY_CHANNELS:
            decision = str(affinity.get(channel) or "").strip().upper()
            if decision not in KINETIC_PASS_DECISIONS:
                errors.append(f"KINETIC_AFFINITY_BLOCKED[{channel}:{decision or 'missing'}]")
    if value.get("decision") != "GENERATED_MOVING_CONNECTOR":
        errors.append("CONNECTOR_DECISION_REQUIRED")
    if value.get("firstSecondRebuildsPose") is not False:
        errors.append("KINETIC_POSE_REBUILD_FORBIDDEN")
    if value.get("occlusionHidesReset") is not False:
        errors.append("KINETIC_OCCLUSION_RESET_FORBIDDEN")


def _validate_connector(spec: dict[str, Any], errors: list[str]) -> None:
    anchors = spec.get("anchors")
    if not isinstance(anchors, dict):
        errors.append("CONNECTOR_ANCHORS_REQUIRED")
    else:
        _validate_approved_artifact(
            anchors.get("start"), "connector.start", errors, moving_boundary=True
        )
        _validate_approved_artifact(
            anchors.get("end"), "connector.end", errors, moving_boundary=True
        )
    continuity = spec.get("continuity")
    if not isinstance(continuity, dict):
        errors.append("CONTINUITY_CONTRACT_REQUIRED")
        return
    if not _has_text(continuity.get("entryVelocity")):
        errors.append("ENTRY_VELOCITY_REQUIRED")
    if not _has_text(continuity.get("exitVelocity")):
        errors.append("EXIT_VELOCITY_REQUIRED")
    if not _has_text(continuity.get("irreversibleChange")):
        errors.append("IRREVERSIBLE_CHANGE_REQUIRED")
    _validate_kinetic_handoff(continuity.get("kineticHandoff"), errors)
    if (
        int(continuity.get("crossfadeFrames") or 0) != 0
        or int(continuity.get("freezeFrames") or 0) != 0
        or int(continuity.get("staticHoldFrames") or 0) != 0
        or continuity.get("resetAllowed") is not False
    ):
        errors.append(
            "FORBIDDEN_EDITORIAL_TRANSITION: crossfade, freeze, static hold and reset must be zero/false"
        )


def _resolve_effective_risk(
    workflow_id: str, risk: str, shot_scale: str
) -> str:
    if (
        workflow_id == "h3_live_action_identity_performance"
        and risk == "normal"
        and shot_scale in {"close_up", "extreme_close_up"}
    ):
        return "high"
    return risk


def compile_live_action_plan(
    spec: dict[str, Any],
    *,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Compile a reviewed contract into an H3-only execution plan.

    The returned ``readyForQueue`` flag is evidence only.  The caller remains
    responsible for a fresh queue/VRAM admission immediately before enqueue.
    """

    if not isinstance(spec, dict):
        raise LiveActionContractError("LIVE_ACTION_SPEC_OBJECT_REQUIRED")
    pack = load_live_action_pack(workspace_root)
    workflows = {item["id"]: item for item in pack["workflows"]}
    workflow_id = str(spec.get("workflowId") or "")
    workflow = workflows.get(workflow_id)
    if workflow is None:
        raise LiveActionContractError(f"WORKFLOW_UNKNOWN: {workflow_id or 'missing'}")

    errors: list[str] = []
    if spec.get("engineSelection") != "minimax_h3":
        errors.append("ENGINE_LOCK_REQUIRED[minimax_h3]")
    if spec.get("fallbackAllowed") is not False:
        errors.append("FALLBACK_FORBIDDEN")
    risk = str(spec.get("risk") or "").strip().lower()
    if risk not in VALID_RISKS:
        errors.append("RISK_INVALID[normal|high|critical]")
        risk = "normal"
    shot_scale = str(spec.get("shotScale") or "").strip().lower()
    if not shot_scale:
        errors.append("SHOT_SCALE_REQUIRED")
    effective_risk = _resolve_effective_risk(workflow_id, risk, shot_scale)

    identity_ids = _validate_identity_matrix(spec.get("identityMatrix"), errors)
    identity_continuity = None
    if spec.get("identityContinuityRequired") is True or "identityContinuity" in spec:
        from identity_continuity import compile_identity_continuity, IdentityContinuityError

        def identity_artifacts(value):
            if isinstance(value, dict):
                if "path" in value and "sha256" in value:
                    return [value]
                return [a for item in value.values() for a in identity_artifacts(item)]
            if isinstance(value, list):
                return [a for item in value for a in identity_artifacts(item)]
            return []

        try:
            identity_continuity = compile_identity_continuity(
                spec.get("identityContinuity"), _workspace_root(workspace_root), identity_ids,
                identity_artifacts(spec.get("anchors") or spec.get("appearanceReferences") or spec.get("connector")),
            )
        except (IdentityContinuityError, OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(str(exc))
    _validate_motion_contract(spec.get("motionContract"), errors)

    motion_binding = str(spec.get("motionBinding") or "").strip().lower()
    if motion_binding not in {"prompt_guided", "reference_video", "exact_pose"}:
        errors.append("MOTION_BINDING_INVALID")
    if motion_binding == "exact_pose":
        errors.append(
            "EXACT_POSE_UNSUPPORTED: H3 Ref2VA/reference video is not geometric pose control"
        )

    if workflow_id == "h3_live_action_identity_performance":
        references = spec.get("appearanceReferences")
        if not isinstance(references, list) or not references:
            errors.append("APPEARANCE_REFERENCE_REQUIRED")
        else:
            for index, reference in enumerate(references, start=1):
                _validate_approved_artifact(
                    reference, f"appearanceReferences[{index}]", errors
                )
    elif workflow_id in {
        "h3_live_action_physical_action",
        "h3_live_action_signature_combat",
        "h3_live_action_continuous_bilateral_combat_8s",
        START_CHAIN_WORKFLOW_ID,
    }:
        anchors = spec.get("anchors")
        intermediate = None
        if not isinstance(anchors, dict):
            errors.append("ACTION_ANCHORS_REQUIRED")
        else:
            _validate_approved_artifact(anchors.get("start"), "action.start", errors)
            if workflow_id == START_CHAIN_WORKFLOW_ID:
                if anchors.get("end") is not None:
                    errors.append("START_CHAIN_END_ANCHOR_FORBIDDEN")
            else:
                _validate_approved_artifact(anchors.get("end"), "action.end", errors)
            intermediate = anchors.get("intermediate")
            if (
                workflow_id not in CONTINUOUS_COMBAT_WORKFLOW_IDS
                and effective_risk in {"high", "critical"}
                and not intermediate
            ):
                errors.append(
                    "INTERMEDIATE_ANCHOR_REQUIRED: high/critical action risk"
                )
            if intermediate is not None:
                intermediate_items = (
                    intermediate if isinstance(intermediate, list) else [intermediate]
                )
                for index, anchor in enumerate(intermediate_items, start=1):
                    _validate_approved_artifact(
                        anchor, f"action.intermediate[{index}]", errors
                    )
        if workflow_id == "h3_live_action_signature_combat":
            if not intermediate:
                errors.append("SIGNATURE_CONTACT_ANCHOR_REQUIRED")
            mechanics_by_id = _validate_combat_identity_matrix(
                spec.get("combatIdentityMatrix"), identity_ids, errors
            )
            _validate_signature_move_contract(
                spec.get("signatureMoveContract"), mechanics_by_id, errors
            )
        elif workflow_id in CONTINUOUS_COMBAT_WORKFLOW_IDS:
            if intermediate is not None:
                errors.append("CONTINUOUS_COMBAT_INTERMEDIATE_ANCHOR_FORBIDDEN")
            mechanics_by_id = _validate_combat_identity_matrix(
                spec.get("combatIdentityMatrix"), identity_ids, errors
            )
            _validate_continuous_combat_contract(
                spec.get("continuousCombatContract"), mechanics_by_id, errors
            )
    elif workflow_id == "h3_live_action_moving_connector":
        _validate_connector(spec, errors)

    if errors:
        raise LiveActionContractError(errors)

    profile_id = workflow["qualityRoute"][effective_risk]
    profile = pack["qualityProfiles"][profile_id]
    orientation = str(spec.get("orientation") or "landscape").strip().lower()
    if orientation not in {"landscape", "vertical"}:
        raise LiveActionContractError("ORIENTATION_INVALID[landscape|vertical]")
    width_key = "verticalWidth" if orientation == "vertical" else "width"
    height_key = "verticalHeight" if orientation == "vertical" else "height"
    quality = {
        "id": profile_id,
        "width": int(profile[width_key]),
        "height": int(profile[height_key]),
        "steps": int(profile["steps"]),
        "fps": int(profile["fps"]),
    }
    owner_authorized = spec.get("ownerRenderAuthorized") is True
    nodes = workflow["nodeContract"]
    result = {
        "ok": True,
        "packVersion": pack["schemaVersion"],
        "workflowId": workflow_id,
        "engine": "minimax_h3",
        "mode": workflow["mode"],
        "effectiveRisk": effective_risk,
        "qualityProfile": quality,
        "requiredNodes": list(nodes["required"]),
        "optionalNodes": list(nodes.get("optional") or []),
        "capabilityClaims": {
            "exactPoseControl": False,
            "referenceVideoIsPoseControl": False,
            "motionBinding": motion_binding,
        },
        "promptContract": deepcopy(workflow["promptContract"]),
        "durationContract": deepcopy(workflow.get("durationContract") or {}),
        "liveActionMaterialContract": deepcopy(pack["liveActionMaterialContract"]),
        "finishingOrder": list(pack["finishingOrder"]),
        "readyForPreflight": True,
        "readyForQueue": owner_authorized,
        "renderAuthorization": (
            "OWNER_AUTHORIZED_RECHECK_GPU_ADMISSION"
            if owner_authorized
            else "OWNER_RENDER_AUTHORIZATION_REQUIRED"
        ),
        "gpuTouched": False,
        "promotionAllowed": False,
    }
    if identity_continuity is not None:
        result["identityContinuity"] = identity_continuity
    if workflow_id == "h3_live_action_signature_combat":
        result["combatIdentityMatrix"] = deepcopy(spec["combatIdentityMatrix"])
        result["signatureMoveContract"] = deepcopy(spec["signatureMoveContract"])
    elif workflow_id in CONTINUOUS_COMBAT_WORKFLOW_IDS:
        result["combatIdentityMatrix"] = deepcopy(spec["combatIdentityMatrix"])
        result["continuousCombatContract"] = deepcopy(spec["continuousCombatContract"])
    return result


def _validate_runtime_prompt(
    prompt: str, prompt_contract: dict[str, Any], errors: list[str]
) -> None:
    if not prompt.strip():
        errors.append("H3_PROMPT_REQUIRED")
        return
    lowered = prompt.lower()
    for section in prompt_contract.get("sections") or []:
        if f"{section}:" not in lowered:
            errors.append(f"H3_PROMPT_SECTION_REQUIRED[{section}]")


def build_live_action_comfy_graph(
    spec: dict[str, Any],
    runtime_inputs: dict[str, Any],
    *,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Materialize a real ComfyUI API graph through the installed H3 builders.

    Graph construction is CPU-only and does not enqueue it.  ``runtime_inputs``
    contains ComfyUI input names, while immutable paths/hashes remain in
    ``spec`` for the approval and sequence gates.
    """

    if not isinstance(runtime_inputs, dict):
        raise LiveActionContractError("RUNTIME_INPUTS_OBJECT_REQUIRED")
    plan = compile_live_action_plan(spec, workspace_root=workspace_root)
    errors: list[str] = []
    prompt = str(runtime_inputs.get("prompt") or "")
    _validate_runtime_prompt(prompt, plan["promptContract"], errors)
    if plan.get("identityContinuity"):
        prompt = plan["identityContinuity"]["fixedPromptBlock"] + "\n\n[SHOT ACTION AND CAMERA]\n" + prompt
    prefix = str(runtime_inputs.get("prefix") or "").strip()
    if not prefix:
        errors.append("OUTPUT_PREFIX_REQUIRED")
    try:
        frames = int(runtime_inputs.get("frames") or 124)
    except (TypeError, ValueError):
        errors.append("FRAME_COUNT_INVALID")
        frames = 124
    expected_frames = int((plan.get("durationContract") or {}).get("nativeFrames") or frames)
    if (
        plan["workflowId"] in CONTINUOUS_COMBAT_WORKFLOW_IDS
        and frames != expected_frames
    ):
        errors.append(
            f"CONTINUOUS_COMBAT_FRAME_COUNT_REQUIRED[{expected_frames};got={frames}]"
        )
    try:
        seed = int(runtime_inputs.get("seed") or 0)
    except (TypeError, ValueError):
        errors.append("SEED_INVALID")
        seed = 0
    if runtime_inputs.get("includeNativeAudio") is True:
        errors.append(
            "NATIVE_AUDIO_NOT_AUTHORIZED: live-action source workflows are visual-first"
        )

    if plan["mode"] == "REF2VA":
        reference_names = runtime_inputs.get("referenceImageNames")
        if not isinstance(reference_names, list) or not any(
            _has_text(item) for item in reference_names
        ):
            errors.append("RUNTIME_REFERENCE_IMAGE_REQUIRED")
    else:
        if not _has_text(runtime_inputs.get("startImageName")):
            errors.append("RUNTIME_START_IMAGE_REQUIRED")
        if plan["workflowId"] == START_CHAIN_WORKFLOW_ID:
            if _has_text(runtime_inputs.get("endImageName")):
                errors.append("RUNTIME_START_CHAIN_END_IMAGE_FORBIDDEN")
            if runtime_inputs.get("lastFrameIndex") is not None:
                errors.append("RUNTIME_START_CHAIN_LAST_FRAME_INDEX_FORBIDDEN")
        elif not _has_text(runtime_inputs.get("endImageName")):
            errors.append("RUNTIME_END_IMAGE_REQUIRED")
        if _has_text(runtime_inputs.get("intermediateImageName")):
            try:
                int(runtime_inputs.get("intermediateFrameIndex"))
            except (TypeError, ValueError):
                errors.append("RUNTIME_INTERMEDIATE_FRAME_INDEX_REQUIRED")
    if errors:
        raise LiveActionContractError(errors)

    # Lazy import avoids a cycle because main imports h3_workflow, which exposes
    # this pack in the Studio status response.
    from main import (  # pylint: disable=import-outside-toplevel
        _build_minimax_h3_fl2va_workflow,
        _build_minimax_h3_ref2va_workflow,
    )

    quality = plan["qualityProfile"]
    common = {
        "prompt": prompt,
        "negative": str(runtime_inputs.get("negative") or ""),
        "width": quality["width"],
        "height": quality["height"],
        "frames": frames,
        "steps": quality["steps"],
        "seed": seed,
        "prefix": prefix,
        "include_native_audio": False,
        "enable_live_preview": runtime_inputs.get("enableLivePreview") is True,
        "fps": quality["fps"],
        "h3_quality_profile": quality["id"],
    }
    def native_preview(graph):
        graph["pemara_dlss5_content"] = {
            "class_type": "PemaraDLSS5ContentPolicy",
            "inputs": {"content_kind": "live_action", "stage": "native_preview"},
        }
        return graph

    if plan["mode"] == "REF2VA":
        return native_preview(_build_minimax_h3_ref2va_workflow(
            **common,
            reference_image_names=[
                str(item).strip()
                for item in runtime_inputs["referenceImageNames"]
                if _has_text(item)
            ],
            reference_video_name=str(
                runtime_inputs.get("referenceVideoName") or ""
            ).strip(),
        ))

    guide_name = str(runtime_inputs.get("intermediateImageName") or "").strip()
    guide_index = (
        int(runtime_inputs["intermediateFrameIndex"]) if guide_name else None
    )
    last_index_value = runtime_inputs.get("lastFrameIndex")
    last_index = int(last_index_value) if last_index_value is not None else None
    return native_preview(_build_minimax_h3_fl2va_workflow(
        **common,
        base_image_name=str(runtime_inputs["startImageName"]).strip(),
        end_image_name=str(runtime_inputs.get("endImageName") or "").strip(),
        last_frame_index=last_index,
        guide_image_name=guide_name,
        guide_frame_index=guide_index,
    ))


def advance_live_action_state(
    record: dict[str, Any],
    event: dict[str, Any],
    *,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Apply one declared lifecycle event without skipping approval gates."""

    if not isinstance(record, dict) or not isinstance(event, dict):
        raise LiveActionContractError("EVENT_RECORD_OBJECT_REQUIRED")
    pack = load_live_action_pack(workspace_root)
    definitions = {
        item["type"]: item for item in pack["events"]["eventTypes"]
    }
    event_type = str(event.get("type") or "")
    definition = definitions.get(event_type)
    if definition is None:
        raise LiveActionContractError(f"EVENT_UNKNOWN: {event_type or 'missing'}")
    current_state = str(record.get("state") or "DRAFT")
    if current_state not in definition["from"]:
        raise LiveActionContractError(
            f"ILLEGAL_EVENT_TRANSITION: {current_state} --{event_type}--> {definition['to']}"
        )
    actor = str(event.get("actor") or "")
    if actor not in definition["authority"]:
        raise LiveActionContractError(
            f"EVENT_AUTHORITY_REQUIRED: {event_type} requires {','.join(definition['authority'])}"
        )
    if event_type == "LIVE_ACTION_SIGNATURE_COMBAT_PLAN_REGISTERED":
        scope = str(event.get("scope") or "").strip()
        expected_scope = str(record.get("replacementScope") or "").strip()
        combat_plan = event.get("combatPlan")
        plan_errors: list[str] = []
        if record.get("sameScopeReplacementAuthorized") is not True:
            plan_errors.append("SAME_SCOPE_REPLACEMENT_NOT_AUTHORIZED")
        if not scope or scope != expected_scope:
            plan_errors.append(
                f"REPLACEMENT_SCOPE_MISMATCH: expected {expected_scope or 'missing'}, got {scope or 'missing'}"
            )
        if not isinstance(combat_plan, dict):
            plan_errors.append("SIGNATURE_COMBAT_PLAN_ARTIFACT_REQUIRED")
        else:
            if not _has_text(combat_plan.get("path")):
                plan_errors.append("SIGNATURE_COMBAT_PLAN_PATH_REQUIRED")
            if not SHA256_RE.fullmatch(str(combat_plan.get("sha256") or "")):
                plan_errors.append("SIGNATURE_COMBAT_PLAN_SHA256_REQUIRED")
        if plan_errors:
            raise LiveActionContractError(plan_errors)

    if event_type in {
        "LIVE_ACTION_REPLACEMENT_ADMITTED",
        "LIVE_ACTION_TECHNICAL_REPLACEMENT_ADMITTED",
    }:
        scope = str(event.get("scope") or "").strip()
        expected_scope = str(record.get("replacementScope") or "").strip()
        admission_errors: list[str] = []
        if record.get("sameScopeReplacementAuthorized") is not True:
            admission_errors.append("SAME_SCOPE_REPLACEMENT_NOT_AUTHORIZED")
        if not scope or scope != expected_scope:
            admission_errors.append(
                f"REPLACEMENT_SCOPE_MISMATCH: expected {expected_scope or 'missing'}, got {scope or 'missing'}"
            )
        if event.get("preflightPassed") is not True:
            admission_errors.append("REPLACEMENT_PREFLIGHT_REQUIRED")
        if event.get("gpuAdmissionPassed") is not True:
            admission_errors.append("FRESH_GPU_ADMISSION_REQUIRED")
        if event_type == "LIVE_ACTION_TECHNICAL_REPLACEMENT_ADMITTED":
            if event.get("correctionRecorded") is not True:
                admission_errors.append("TECHNICAL_CORRECTION_RECORD_REQUIRED")
            if event.get("anchorHashesUnchanged") is not True:
                admission_errors.append("ANCHOR_HASH_LOCK_REQUIRED")
        if admission_errors:
            raise LiveActionContractError(admission_errors)

    if event_type == "LIVE_ACTION_CAUSAL_MOTION_GATE_PASSED":
        causal_errors: list[str] = []
        for field in (
            "fullFrameReview",
            "reactionStartsAfterContact",
            "groundedTravelExplained",
            "airborneTravelExplained",
            "hoveringAbsent",
            "rigidSlidingAbsent",
        ):
            if event.get(field) is not True:
                causal_errors.append(f"CAUSAL_MOTION_FIELD_REQUIRED[{field}]")
        evidence = event.get("evidence")
        if not isinstance(evidence, dict):
            causal_errors.append("CAUSAL_MOTION_EVIDENCE_REQUIRED")
        else:
            if not _has_text(evidence.get("path")):
                causal_errors.append("CAUSAL_MOTION_EVIDENCE_PATH_REQUIRED")
            if not SHA256_RE.fullmatch(str(evidence.get("sha256") or "")):
                causal_errors.append("CAUSAL_MOTION_EVIDENCE_SHA256_REQUIRED")
        if causal_errors:
            raise LiveActionContractError(causal_errors)

    if event_type == "LIVE_ACTION_INTERMEDIATE_GUIDE_CONFLICT_PROVEN":
        conflict_errors: list[str] = []
        scope = str(record.get("replacementScope") or "").strip()
        preserved = [
            item
            for item in record.get("preservedArtifacts") or []
            if isinstance(item, dict) and str(item.get("scope") or "") == scope
        ]
        distinct_attempts = {int(item.get("attempt") or 0) for item in preserved}
        if not scope or len(distinct_attempts - {0}) < 2:
            conflict_errors.append("TWO_PRESERVED_GUIDE_FAILURES_REQUIRED")
        if event.get("sameDefectConfirmed") is not True:
            conflict_errors.append("SAME_GUIDE_DEFECT_CONFIRMATION_REQUIRED")
        anchor = event.get("intermediateAnchor")
        if not isinstance(anchor, dict):
            conflict_errors.append("IMMUTABLE_INTERMEDIATE_ANCHOR_REQUIRED")
        else:
            if not _has_text(anchor.get("path")):
                conflict_errors.append("INTERMEDIATE_ANCHOR_PATH_REQUIRED")
            if not SHA256_RE.fullmatch(str(anchor.get("sha256") or "")):
                conflict_errors.append("INTERMEDIATE_ANCHOR_SHA256_REQUIRED")
            if anchor.get("immutable") is not True:
                conflict_errors.append("INTERMEDIATE_ANCHOR_MUST_REMAIN_IMMUTABLE")
        if conflict_errors:
            raise LiveActionContractError(conflict_errors)

    updated = deepcopy(record)
    updated.setdefault("history", [])
    updated.setdefault("preservedArtifacts", [])
    updated.setdefault("renderAuthorized", False)
    updated.setdefault("assemblyAllowed", False)
    updated["state"] = definition["to"]
    for key, value in (definition.get("set") or {}).items():
        updated[key] = deepcopy(value)

    if event_type in {
        "LIVE_ACTION_CANDIDATE_REJECTED",
        "LIVE_ACTION_TECHNICAL_CANDIDATE_REJECTED",
        "LIVE_ACTION_OWNER_ROUTE_REJECTED",
    }:
        scope = str(event.get("scope") or "").strip()
        artifact = event.get("artifact")
        rejection_errors: list[str] = []
        if not scope:
            rejection_errors.append("REJECTION_SCOPE_REQUIRED")
        if not isinstance(artifact, dict):
            rejection_errors.append("REJECTED_ARTIFACT_REQUIRED")
        else:
            if not _has_text(artifact.get("path")):
                rejection_errors.append("REJECTED_ARTIFACT_PATH_REQUIRED")
            if not SHA256_RE.fullmatch(str(artifact.get("sha256") or "")):
                rejection_errors.append("REJECTED_ARTIFACT_SHA256_REQUIRED")
        if event_type == "LIVE_ACTION_TECHNICAL_CANDIDATE_REJECTED":
            if isinstance(artifact, dict) and int(artifact.get("attempt") or 0) < 1:
                rejection_errors.append("REJECTED_ARTIFACT_ATTEMPT_REQUIRED")
            if not _has_text(event.get("objectiveQcEvidence")):
                rejection_errors.append("OBJECTIVE_QC_EVIDENCE_REQUIRED")
            if event.get("ownerSameScopeAuthorization") is not True:
                rejection_errors.append("OWNER_SAME_SCOPE_AUTHORIZATION_REQUIRED")
        if event_type == "LIVE_ACTION_OWNER_ROUTE_REJECTED":
            declared_failures = event.get("declaredFailures")
            if not isinstance(declared_failures, list) or not all(
                _has_text(item) for item in declared_failures
            ):
                rejection_errors.append("ROUTE_ARTISTIC_FAILURES_REQUIRED")
        if rejection_errors:
            raise LiveActionContractError(rejection_errors)
        preserved_artifact = deepcopy(artifact)
        preserved_artifact["scope"] = scope
        updated["preservedArtifacts"].append(preserved_artifact)
        updated["replacementScope"] = scope
        updated["sameScopeReplacementAuthorized"] = True
        if event_type == "LIVE_ACTION_OWNER_ROUTE_REJECTED":
            updated["routeRejection"] = {
                "declaredFailures": deepcopy(event["declaredFailures"]),
                "strengthsPreservedAsConstraints": deepcopy(
                    event.get("strengthsPreservedAsConstraints") or []
                ),
            }

    if event_type == "LIVE_ACTION_SIGNATURE_COMBAT_PLAN_REGISTERED":
        updated["combatPlan"] = deepcopy(event["combatPlan"])

    if event_type == "LIVE_ACTION_INTERMEDIATE_GUIDE_CONFLICT_PROVEN":
        updated["guideConflictEvidence"] = {
            "scope": str(updated.get("replacementScope") or ""),
            "intermediateAnchor": deepcopy(event["intermediateAnchor"]),
            "preservedAttempts": sorted(
                {
                    int(item.get("attempt") or 0)
                    for item in updated.get("preservedArtifacts") or []
                    if isinstance(item, dict)
                    and str(item.get("scope") or "") == str(updated.get("replacementScope") or "")
                    and int(item.get("attempt") or 0) > 0
                }
            ),
            "sameDefectConfirmed": True,
        }

    history_item = {
        "type": event_type,
        "actor": actor,
        "from": current_state,
        "to": definition["to"],
    }
    if event.get("scope"):
        history_item["scope"] = str(event["scope"])
    updated["history"].append(history_item)
    return updated
