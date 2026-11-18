from __future__ import annotations

import unittest
from pathlib import Path

from h3_workflow import workflow_status as h3_workflow_status
from live_action_workflows import (
    LIVE_ACTION_PACK_VERSION,
    LiveActionContractError,
    advance_live_action_state,
    build_live_action_comfy_graph,
    compile_live_action_plan,
    load_live_action_pack,
    workflow_pack_status,
)


APPROVED_HASH = "a" * 64


def approved_anchor(name: str, *, moving: bool = False) -> dict:
    anchor = {
        "path": f"anchors/{name}.png",
        "sha256": APPROVED_HASH,
        "ownerApproved": True,
        "approvalScope": f"take:{name}",
    }
    if moving:
        anchor["movingContext"] = {
            "hasMotionBefore": True,
            "hasMotionAfter": True,
        }
    return anchor


def identity_matrix() -> list[dict]:
    return [
        {
            "id": "fighter_a",
            "face": "same approved adult actor face",
            "bodyScale": "athletic human proportions",
            "wardrobe": "physical layered wardrobe with stable colors",
            "anatomy": "two arms, two legs, five fingers per visible hand",
            "forbiddenChanges": ["face swap", "extra limbs", "plastic skin"],
            "stateByBeat": {
                "early_0_30": "guard moving forward",
                "middle_30_70": "contact and recoil",
                "late_70_100": "recovering while still moving",
            },
        }
    ]


def motion_contract() -> dict:
    return {
        "beats": {
            "early_0_30": "inherited movement continues",
            "middle_30_70": "irreversible physical event develops",
            "late_70_100": "visible consequence exits still in motion",
        },
        "cameraEvidence": {
            "physicalTranslation": True,
            "perspectiveChange": "foreground overlap changes against the set",
        },
        "depthPlanes": {
            "foreground": "fast debris crosses lens",
            "midground": "actors exchange weight and position",
            "background": "stable architecture reveals parallax",
        },
        "internalActions": ["cloth reacts to acceleration", "dust reacts to impact"],
        "progression": {
            "start": "balanced guard",
            "middle": "contact displaces both bodies",
            "end": "damaged floor and moving recovery",
        },
    }


def combat_identity_matrix() -> list[dict]:
    return [
        {
            "id": "fighter_a",
            "combatPersonality": "forward pressure with compact grounded mechanics",
            "visualSignature": "green body-attached energy only during owned techniques",
            "ownedMechanics": ["shadow_kick", "rising_strike"],
            "forbiddenMechanics": ["hellfire", "ice", "chain_spear"],
        },
        {
            "id": "fighter_b",
            "combatPersonality": "counter-attacker who controls distance with a chained weapon",
            "visualSignature": "warm hellfire and one physical chained spear",
            "ownedMechanics": ["chain_spear", "hellfire_counter"],
            "forbiddenMechanics": ["green_shadow_energy", "ice"],
        },
    ]


def two_fighter_identity_matrix() -> list[dict]:
    result = identity_matrix()
    second = dict(result[0])
    second["id"] = "fighter_b"
    second["face"] = "same second approved adult actor face"
    result.append(second)
    return result


def signature_move_contract() -> dict:
    return {
        "moveId": "shadow_kick",
        "ownerId": "fighter_a",
        "opponentId": "fighter_b",
        "canonicalMechanic": "rear foot drives the whole body through one horizontal kick line",
        "outcome": "direct contact displaces fighter_b and changes the spatial advantage",
        "cutMotivation": "cut while both bodies and displaced debris still carry momentum",
        "modelMayChooseDifferentMove": False,
        "dominantExchangeCount": 1,
        "physicsChain": {
            "anticipation": "fighter_a lowers the center of mass and loads the rear leg",
            "propulsion": "rear foot pushes against wet ground and the full torso accelerates",
            "contact": "the ordinary boot visibly meets the armored torso",
            "displacement": "both centers of mass change position on the same impact vector",
            "reaction": "fighter_b folds and travels backward instead of posing",
            "recovery": "fighter_a lands through the line while fighter_b keeps falling",
        },
        "effectLifecycle": {
            "type": "energy",
            "ownerId": "fighter_a",
            "attachment": "green shadow energy stays attached to fighter_a's moving silhouette and boot",
            "onset": "energy appears only after rear-foot propulsion begins",
            "trajectory": "the afterimage follows the same body vector without becoming a beam",
            "contact": "one green pressure pulse occurs at visible boot contact",
            "decay": "the body-attached trail collapses immediately after landing",
            "environmentalConsequence": "wet mud and cloth catch a brief green reflection at contact",
            "forbiddenTransfers": ["fighter_b gains green energy", "green fire appears"],
        },
        "readability": {
            "contactVisible": True,
            "attackVectorReadable": True,
            "cutawayAtImpact": False,
            "cameraShakeCarriesImpact": False,
        },
    }


def continuous_combat_contract() -> dict:
    return {
        "intermediateGuideAllowed": False,
        "activeCutWithoutConnector": True,
        "exchanges": [
            {
                "id": "x1",
                "attackerId": "fighter_a",
                "defenderId": "fighter_b",
                "mechanic": "rising_strike",
                "phase": "early_0_30",
                "supportAndPropulsion": "rear foot and hip load before the glove accelerates",
                "visibleContactOrEvasion": "glove visibly compresses the guard",
                "defenderResponseAfterCause": "head and torso rotate only after glove contact",
                "groundTranslationMechanism": "fighter_b replants the rear foot during recoil",
                "environmentalLag": "wet cloth and droplets trail the torso response",
                "activeRecovery": "both fighters step through into the next exchange",
                "causeBeforeEffect": True,
                "defenderMotionBeforeContactForbidden": True,
            },
            {
                "id": "x2",
                "attackerId": "fighter_b",
                "defenderId": "fighter_a",
                "mechanic": "chain_spear",
                "phase": "middle_30_70",
                "supportAndPropulsion": "planted pivot and shoulder cast the weighted chain",
                "visibleContactOrEvasion": "fighter_a parries the links at the forearm",
                "defenderResponseAfterCause": "fighter_a rotates only after chain pressure",
                "groundTranslationMechanism": "fighter_a takes two visible recovery steps",
                "environmentalLag": "mud and links continue after the body changes vector",
                "activeRecovery": "fighter_b reels while fighter_a closes distance",
                "causeBeforeEffect": True,
                "defenderMotionBeforeContactForbidden": True,
            },
            {
                "id": "x3",
                "attackerId": "fighter_a",
                "defenderId": "fighter_b",
                "mechanic": "shadow_kick",
                "phase": "late_70_100",
                "supportAndPropulsion": "two steps and rear-foot drive launch the intact body",
                "visibleContactOrEvasion": "ordinary boot meets chest armor before displacement",
                "defenderResponseAfterCause": "fighter_b travels backward only after boot contact",
                "groundTranslationMechanism": "fighter_a lands and fighter_b skids a visible furrow",
                "environmentalLag": "armor, water and leaves trail the impact vector",
                "activeRecovery": "camera and both bodies exit with usable momentum",
                "causeBeforeEffect": True,
                "defenderMotionBeforeContactForbidden": True,
            },
        ],
    }


def kinetic_boundary_state(*, root_vector: str) -> dict:
    return {
        "characters": [
            {
                "characterId": "fighter_a",
                "screenPosition": "midground screen-left at the shared root",
                "rootVector": root_vector,
                "speedClass": "fast",
                "weightBearingFoot": "right",
                "torsoAngularDirection": "clockwise rotation still accelerating",
                "limbPhase": "striking arm retracting",
                "gazeTarget": "fighter_b",
                "contactState": "right foot in loaded ground contact",
                "damageFatigueState": "breathing hard with unchanged wardrobe damage",
            }
        ],
        "camera": {
            "positionAndLens": "low physical 35mm camera outside the action line",
            "translationVector": "trucking screen-left to screen-right",
            "speedClass": "medium",
            "angularPhase": "short clockwise arc still opening",
            "foregroundOcclusion": "none",
        },
        "objectEffects": [],
        "environment": {
            "persistentDamage": "same cracked stone rail remains broken",
            "movingElements": "dust and cloth continue screen-right",
            "foreground": "debris crosses screen-right",
            "midground": "fighter_a continues screen-right",
            "background": "stable architecture reveals opposing parallax",
        },
    }


def kinetic_handoff_contract() -> dict:
    return {
        "sourceExit": kinetic_boundary_state(root_vector="screen-left to screen-right"),
        "destinationEntry": kinetic_boundary_state(root_vector="screen-left to screen-right"),
        "affinity": {
            "characters": "MATCH",
            "actionPhase": "MATCH",
            "cameraGeography": "MATCH",
            "objectEffects": "MATCH",
            "environment": "RECOVERABLE_BY_CAUSAL_CONNECTOR",
        },
        "decision": "GENERATED_MOVING_CONNECTOR",
        "firstSecondRebuildsPose": False,
        "occlusionHidesReset": False,
    }


class LiveActionWorkflowPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(__file__).resolve().parents[2]

    def test_pack_contains_six_h3_only_workflows_and_gated_events(self) -> None:
        pack = load_live_action_pack(self.workspace)
        status = workflow_pack_status(self.workspace)

        self.assertEqual(pack["schemaVersion"], LIVE_ACTION_PACK_VERSION)
        self.assertTrue(status["ok"])
        self.assertEqual(
            set(status["workflowIds"]),
            {
                "h3_live_action_identity_performance",
                "h3_live_action_physical_action",
                "h3_live_action_signature_combat",
                "h3_live_action_continuous_bilateral_combat_8s",
                "h3_live_action_continuous_bilateral_start_chain_8s",
                "h3_live_action_moving_connector",
            },
        )
        self.assertEqual({item["engine"] for item in pack["workflows"]}, {"minimax_h3"})
        self.assertTrue(all(item["fallbackAllowed"] is False for item in pack["workflows"]))
        self.assertIn("LIVE_ACTION_RENDER_AUTHORIZED", status["eventTypes"])
        self.assertIn("LIVE_ACTION_CANDIDATE_REJECTED", status["eventTypes"])
        self.assertIn("LIVE_ACTION_INTERMEDIATE_GUIDE_CONFLICT_PROVEN", status["eventTypes"])
        self.assertIn("LIVE_ACTION_OWNER_ROUTE_REJECTED", status["eventTypes"])
        self.assertIn("LIVE_ACTION_SIGNATURE_COMBAT_PLAN_REGISTERED", status["eventTypes"])
        self.assertIn("LIVE_ACTION_CAUSAL_MOTION_GATE_PASSED", status["eventTypes"])

    def test_canonical_h3_status_exposes_the_live_action_pack_and_agents(self) -> None:
        status = h3_workflow_status(self.workspace, comfy_online=True)
        routed = {item["name"]: item for item in status["routedSkills"]}

        self.assertTrue(status["liveActionPack"]["ok"])
        self.assertEqual(len(status["liveActionPack"]["workflowIds"]), 6)
        for name in (
            "pemara-live-action-showrunner",
            "pemara-live-action-continuity",
            "pemara-live-action-qc",
            "pemara-live-action-combat-director",
            "pemara-live-action-kinetic-supervisor",
        ):
            self.assertIn(name, routed)
            self.assertTrue(routed[name]["installed"])

    def test_closeup_identity_route_uses_ref2va_and_hero_quality_without_claiming_exact_pose(self) -> None:
        spec = {
            "workflowId": "h3_live_action_identity_performance",
            "risk": "normal",
            "shotScale": "close_up",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": False,
            "identityMatrix": identity_matrix(),
            "appearanceReferences": [approved_anchor("face_reference")],
            "motionBinding": "reference_video",
            "motionContract": motion_contract(),
        }

        plan = compile_live_action_plan(spec, workspace_root=self.workspace)

        self.assertTrue(plan["readyForPreflight"])
        self.assertFalse(plan["readyForQueue"])
        self.assertEqual(plan["mode"], "REF2VA")
        self.assertEqual(plan["effectiveRisk"], "high")
        self.assertEqual(plan["qualityProfile"], {
            "id": "h3_hero",
            "width": 1344,
            "height": 768,
            "steps": 14,
            "fps": 24,
        })
        self.assertIn("MiniMaxH3ReferenceToVideo", plan["requiredNodes"])
        self.assertNotIn("MiniMaxH3ImageToVideo", plan["requiredNodes"])
        self.assertFalse(plan["capabilityClaims"]["exactPoseControl"])

    def test_normal_action_route_uses_fl2va_and_production_middle_ground(self) -> None:
        spec = {
            "workflowId": "h3_live_action_physical_action",
            "risk": "normal",
            "shotScale": "medium",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": True,
            "identityMatrix": identity_matrix(),
            "anchors": {
                "start": approved_anchor("action_start"),
                "end": approved_anchor("action_end"),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }

        plan = compile_live_action_plan(spec, workspace_root=self.workspace)

        self.assertTrue(plan["readyForQueue"])
        self.assertEqual(plan["mode"], "FL2VA")
        self.assertEqual(plan["qualityProfile"], {
            "id": "h3_production",
            "width": 1088,
            "height": 608,
            "steps": 10,
            "fps": 24,
        })
        self.assertIn("MiniMaxH3ImageToVideo", plan["requiredNodes"])
        self.assertIn("MiniMaxH3AddGuide", plan["optionalNodes"])
        self.assertNotIn("RIFE", " ".join(plan["requiredNodes"]))
        self.assertEqual(plan["finishingOrder"], [
            "picture_lock", "seedvr2_3b_int8_candidate", "rife_exact60_candidate",
            "dlss5_natural_candidate", "original_audio_stream_copy",
            "technical_qc_and_human_listening", "separate_owner_review",
        ])

    def test_signature_combat_requires_owned_move_complete_physics_and_effect_lifecycle(self) -> None:
        spec = {
            "workflowId": "h3_live_action_signature_combat",
            "risk": "high",
            "shotScale": "medium_wide",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": False,
            "identityMatrix": two_fighter_identity_matrix(),
            "combatIdentityMatrix": combat_identity_matrix(),
            "signatureMoveContract": signature_move_contract(),
            "anchors": {
                "start": approved_anchor("signature_start"),
                "intermediate": approved_anchor("signature_contact"),
                "end": approved_anchor("signature_end"),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }

        plan = compile_live_action_plan(spec, workspace_root=self.workspace)

        self.assertEqual(plan["workflowId"], "h3_live_action_signature_combat")
        self.assertEqual(plan["qualityProfile"]["id"], "h3_hero")
        self.assertFalse(plan["readyForQueue"])
        self.assertEqual(plan["signatureMoveContract"]["moveId"], "shadow_kick")

        spec["signatureMoveContract"]["moveId"] = "hellfire"
        with self.assertRaisesRegex(LiveActionContractError, "SIGNATURE_MOVE_NOT_OWNED"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

    def test_signature_combat_rejects_generic_move_choice_and_missing_contact_chain(self) -> None:
        move = signature_move_contract()
        move["modelMayChooseDifferentMove"] = True
        del move["physicsChain"]["displacement"]
        spec = {
            "workflowId": "h3_live_action_signature_combat",
            "risk": "normal",
            "shotScale": "wide",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": False,
            "identityMatrix": two_fighter_identity_matrix(),
            "combatIdentityMatrix": combat_identity_matrix(),
            "signatureMoveContract": move,
            "anchors": {
                "start": approved_anchor("signature_start"),
                "intermediate": approved_anchor("signature_contact"),
                "end": approved_anchor("signature_end"),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }

        with self.assertRaises(LiveActionContractError) as raised:
            compile_live_action_plan(spec, workspace_root=self.workspace)
        self.assertIn("MODEL_SELECTED_MOVE_FORBIDDEN", raised.exception.errors)
        self.assertIn("COMPLETE_PHYSICS_CHAIN_REQUIRED", raised.exception.errors)

    def test_continuous_combat_uses_owner_proven_8s_two_anchor_route(self) -> None:
        spec = {
            "workflowId": "h3_live_action_continuous_bilateral_combat_8s",
            "risk": "critical",
            "shotScale": "medium_wide",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": True,
            "identityMatrix": two_fighter_identity_matrix(),
            "combatIdentityMatrix": combat_identity_matrix(),
            "continuousCombatContract": continuous_combat_contract(),
            "anchors": {
                "start": approved_anchor("continuous_start"),
                "end": approved_anchor("continuous_end"),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }
        plan = compile_live_action_plan(spec, workspace_root=self.workspace)
        self.assertTrue(plan["readyForQueue"])
        self.assertEqual(plan["durationContract"]["nativeFrames"], 192)
        self.assertEqual(plan["qualityProfile"], {
            "id": "h3_approved_action_720p8s",
            "width": 1280,
            "height": 720,
            "steps": 20,
            "fps": 24,
        })
        self.assertNotIn("MiniMaxH3AddGuide", plan["optionalNodes"])

        runtime = {
            "prompt": (
                "integrated_multimodal_description:\n[Shot 1] ONE UNINTERRUPTED EIGHT-SECOND reciprocal physical fight\n\n"
                "overall_soundscape:\nN/A\n\nnon_diegetic_music:\nN/A"
            ),
            "startImageName": "continuous_start.png",
            "endImageName": "continuous_end.png",
            "frames": 192,
            "lastFrameIndex": 191,
            "seed": 789,
            "prefix": "live_action/continuous_take",
        }
        graph = build_live_action_comfy_graph(spec, runtime, workspace_root=self.workspace)
        classes = {node["class_type"] for node in graph.values()}
        self.assertNotIn("MiniMaxH3AddGuide", classes)
        self.assertEqual(graph["6"]["inputs"]["length"], 192)
        # The proven 720p H3 route samples at the model-safe 1344x768 native
        # geometry, then conforms node 14 to the requested 1280x720 output.
        self.assertEqual(graph["6"]["inputs"]["width"], 1344)
        self.assertEqual(graph["6"]["inputs"]["height"], 768)
        self.assertEqual(graph["14"]["inputs"]["width"], 1280)
        self.assertEqual(graph["14"]["inputs"]["height"], 720)
        self.assertEqual(graph["6"]["inputs"]["last_frame_index"], 191)
        self.assertEqual(graph["8"]["inputs"]["steps"], 20)

        spec["anchors"]["intermediate"] = approved_anchor("forbidden_contact")
        with self.assertRaisesRegex(LiveActionContractError, "CONTINUOUS_COMBAT_INTERMEDIATE_ANCHOR_FORBIDDEN"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

    def test_continuous_start_chain_uses_one_anchor_and_leaves_exit_unforced(self) -> None:
        spec = {
            "workflowId": "h3_live_action_continuous_bilateral_start_chain_8s",
            "risk": "critical",
            "shotScale": "medium_wide",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": True,
            "identityMatrix": two_fighter_identity_matrix(),
            "combatIdentityMatrix": combat_identity_matrix(),
            "continuousCombatContract": continuous_combat_contract(),
            "anchors": {"start": approved_anchor("continuous_start")},
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }
        plan = compile_live_action_plan(spec, workspace_root=self.workspace)
        self.assertEqual(plan["mode"], "I2VA")
        self.assertEqual(plan["durationContract"]["nativeFrames"], 192)

        runtime = {
            "prompt": (
                "integrated_multimodal_description:\n[Shot 1] ONE UNINTERRUPTED EIGHT-SECOND reciprocal physical fight\n\n"
                "overall_soundscape:\nN/A\n\nnon_diegetic_music:\nN/A"
            ),
            "startImageName": "continuous_start.png",
            "frames": 192,
            "seed": 790,
            "prefix": "live_action/continuous_start_chain_take",
        }
        graph = build_live_action_comfy_graph(spec, runtime, workspace_root=self.workspace)
        conditioning = graph["6"]["inputs"]
        self.assertEqual(conditioning["first_frame"], ["5", 0])
        self.assertNotIn("last_frame", conditioning)
        self.assertNotIn("last_frame_index", conditioning)
        self.assertNotIn("MiniMaxH3AddGuide", {node["class_type"] for node in graph.values()})
        self.assertEqual(conditioning["length"], 192)
        self.assertEqual(graph["8"]["inputs"]["steps"], 20)

        spec["anchors"]["end"] = approved_anchor("forbidden_end")
        with self.assertRaisesRegex(LiveActionContractError, "START_CHAIN_END_ANCHOR_FORBIDDEN"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

    def test_critical_action_requires_an_approved_intermediate_anchor(self) -> None:
        spec = {
            "workflowId": "h3_live_action_physical_action",
            "risk": "critical",
            "shotScale": "wide",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": True,
            "identityMatrix": identity_matrix(),
            "anchors": {
                "start": approved_anchor("critical_start"),
                "end": approved_anchor("critical_end"),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }

        with self.assertRaisesRegex(LiveActionContractError, "INTERMEDIATE_ANCHOR_REQUIRED"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

    def test_connector_rejects_freeze_crossfade_or_unmoving_boundaries(self) -> None:
        spec = {
            "workflowId": "h3_live_action_moving_connector",
            "risk": "normal",
            "shotScale": "medium",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": True,
            "identityMatrix": identity_matrix(),
            "anchors": {
                "start": approved_anchor("boundary_a", moving=True),
                "end": approved_anchor("boundary_b", moving=True),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
            "continuity": {
                "entryVelocity": "fighter travels screen-left to screen-right",
                "exitVelocity": "same vector continues into the destination take",
                "irreversibleChange": "impact breaks the stone rail",
                "kineticHandoff": kinetic_handoff_contract(),
                "crossfadeFrames": 0,
                "freezeFrames": 1,
                "staticHoldFrames": 0,
                "resetAllowed": False,
            },
        }

        with self.assertRaisesRegex(LiveActionContractError, "FORBIDDEN_EDITORIAL_TRANSITION"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

        spec["continuity"]["freezeFrames"] = 0
        spec["anchors"]["end"]["movingContext"]["hasMotionAfter"] = False
        with self.assertRaisesRegex(LiveActionContractError, "MOVING_BOUNDARY_REQUIRED"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

    def test_connector_blocks_source_regeneration_affinity_or_pose_rebuild(self) -> None:
        handoff = kinetic_handoff_contract()
        handoff["affinity"]["characters"] = "SOURCE_REGEN_REQUIRED"
        handoff["firstSecondRebuildsPose"] = True
        spec = {
            "workflowId": "h3_live_action_moving_connector",
            "risk": "normal",
            "shotScale": "medium",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": False,
            "identityMatrix": identity_matrix(),
            "anchors": {
                "start": approved_anchor("boundary_a", moving=True),
                "end": approved_anchor("boundary_b", moving=True),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
            "continuity": {
                "entryVelocity": "fighter travels screen-left to screen-right",
                "exitVelocity": "same vector continues into the destination take",
                "irreversibleChange": "impact breaks the stone rail",
                "kineticHandoff": handoff,
                "crossfadeFrames": 0,
                "freezeFrames": 0,
                "staticHoldFrames": 0,
                "resetAllowed": False,
            },
        }

        with self.assertRaises(LiveActionContractError) as raised:
            compile_live_action_plan(spec, workspace_root=self.workspace)
        self.assertIn(
            "KINETIC_AFFINITY_BLOCKED[characters:SOURCE_REGEN_REQUIRED]",
            raised.exception.errors,
        )
        self.assertIn("KINETIC_POSE_REBUILD_FORBIDDEN", raised.exception.errors)

    def test_ref2va_fails_closed_when_exact_pose_is_claimed(self) -> None:
        spec = {
            "workflowId": "h3_live_action_identity_performance",
            "risk": "high",
            "shotScale": "close_up",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": True,
            "identityMatrix": identity_matrix(),
            "appearanceReferences": [approved_anchor("face_reference")],
            "motionBinding": "exact_pose",
            "motionContract": motion_contract(),
        }

        with self.assertRaisesRegex(LiveActionContractError, "EXACT_POSE_UNSUPPORTED"):
            compile_live_action_plan(spec, workspace_root=self.workspace)

    def test_materializes_real_ref2va_comfy_graph_for_identity_work(self) -> None:
        spec = {
            "workflowId": "h3_live_action_identity_performance",
            "risk": "high",
            "shotScale": "close_up",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": False,
            "identityMatrix": identity_matrix(),
            "appearanceReferences": [approved_anchor("face_reference")],
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }
        runtime = {
            "prompt": (
                "subject_definitions:\n<Subject 1> is the adult actor in <Picture 1>\n\n"
                "summary:\nA restrained live-action reaction\n\n"
                "retention_analysis:\nPreserve face, anatomy and wardrobe\n\n"
                "detailed_description:\n[Shot 1] The actor turns while the camera trucks left\n\n"
                "overall_soundscape:\nN/A\n\n"
                "non_diegetic_music:\nN/A"
            ),
            "referenceImageNames": ["approved_face.png"],
            "frames": 124,
            "seed": 123,
            "prefix": "live_action/identity_take",
        }

        graph = build_live_action_comfy_graph(
            spec, runtime, workspace_root=self.workspace
        )
        classes = {node["class_type"] for node in graph.values()}

        self.assertIn("MiniMaxH3ReferenceToVideo", classes)
        self.assertNotIn("MiniMaxH3ImageToVideo", classes)
        self.assertNotIn("VAEDecodeAudio", classes)
        self.assertEqual(graph["1"]["inputs"]["unet_name"], "minimax_h3_ref2va_pruned_int8_convrot.safetensors")
        self.assertEqual(graph["6"]["inputs"]["ref_image_size"], "max")
        self.assertEqual(graph["8"]["inputs"]["steps"], 14)

    def test_materializes_real_fl2va_graph_with_middle_guide_for_action(self) -> None:
        spec = {
            "workflowId": "h3_live_action_physical_action",
            "risk": "normal",
            "shotScale": "medium",
            "engineSelection": "minimax_h3",
            "fallbackAllowed": False,
            "ownerRenderAuthorized": False,
            "identityMatrix": identity_matrix(),
            "anchors": {
                "start": approved_anchor("action_start"),
                "end": approved_anchor("action_end"),
                "intermediate": approved_anchor("action_contact"),
            },
            "motionBinding": "prompt_guided",
            "motionContract": motion_contract(),
        }
        runtime = {
            "prompt": (
                "integrated_multimodal_description:\n[Shot 1] Physical live-action contact develops through three beats\n\n"
                "overall_soundscape:\nN/A\n\n"
                "non_diegetic_music:\nN/A"
            ),
            "startImageName": "approved_start.png",
            "endImageName": "approved_end.png",
            "intermediateImageName": "approved_contact.png",
            "intermediateFrameIndex": 62,
            "frames": 124,
            "seed": 456,
            "prefix": "live_action/action_take",
        }

        graph = build_live_action_comfy_graph(
            spec, runtime, workspace_root=self.workspace
        )
        classes = {node["class_type"] for node in graph.values()}

        self.assertIn("MiniMaxH3ImageToVideo", classes)
        self.assertIn("MiniMaxH3AddGuide", classes)
        self.assertNotIn("MiniMaxH3ReferenceToVideo", classes)
        self.assertEqual(graph["6"]["inputs"]["width"], 1088)
        self.assertEqual(graph["6"]["inputs"]["height"], 608)
        self.assertEqual(graph["8"]["inputs"]["steps"], 10)
        self.assertEqual(graph["22"]["inputs"]["frame_idx"], 62)


class LiveActionEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(__file__).resolve().parents[2]

    def test_preflight_does_not_grant_render_authorization(self) -> None:
        record = {"state": "DRAFT", "history": []}
        record = advance_live_action_state(record, {"type": "LIVE_ACTION_STORY_APPROVED", "actor": "owner"}, workspace_root=self.workspace)
        record = advance_live_action_state(record, {"type": "LIVE_ACTION_ANCHORS_LOCKED", "actor": "owner"}, workspace_root=self.workspace)
        record = advance_live_action_state(record, {"type": "LIVE_ACTION_PREFLIGHT_PASSED", "actor": "technical"}, workspace_root=self.workspace)

        self.assertEqual(record["state"], "PREFLIGHT_PASSED")
        self.assertFalse(record["renderAuthorized"])

        record = advance_live_action_state(record, {"type": "LIVE_ACTION_RENDER_AUTHORIZED", "actor": "owner"}, workspace_root=self.workspace)
        self.assertEqual(record["state"], "RENDER_AUTHORIZED")
        self.assertTrue(record["renderAuthorized"])

    def test_illegal_gate_skip_is_rejected(self) -> None:
        with self.assertRaisesRegex(LiveActionContractError, "ILLEGAL_EVENT_TRANSITION"):
            advance_live_action_state(
                {"state": "DRAFT", "history": []},
                {"type": "LIVE_ACTION_PICTURE_LOCKED", "actor": "owner"},
                workspace_root=self.workspace,
            )

    def test_causal_motion_gate_requires_frame_level_physics_evidence(self) -> None:
        record = {"state": "CANDIDATE_READY", "history": []}
        event = {
            "type": "LIVE_ACTION_CAUSAL_MOTION_GATE_PASSED",
            "actor": "technical",
            "fullFrameReview": True,
            "reactionStartsAfterContact": True,
            "groundedTravelExplained": True,
            "airborneTravelExplained": True,
            "hoveringAbsent": True,
            "rigidSlidingAbsent": True,
            "evidence": {"path": "qc/take01/causal_motion.json", "sha256": APPROVED_HASH},
        }
        updated = advance_live_action_state(record, event, workspace_root=self.workspace)
        self.assertEqual(updated["state"], "CAUSAL_MOTION_QC_PASSED")
        broken = dict(event)
        broken["reactionStartsAfterContact"] = False
        with self.assertRaisesRegex(LiveActionContractError, "reactionStartsAfterContact"):
            advance_live_action_state(record, broken, workspace_root=self.workspace)

    def test_rejection_preserves_artifact_and_authorizes_only_same_scope_replacement(self) -> None:
        record = {
            "state": "CANDIDATE_READY",
            "history": [],
            "renderAuthorized": True,
        }
        record = advance_live_action_state(
            record,
            {
                "type": "LIVE_ACTION_CANDIDATE_REJECTED",
                "actor": "owner",
                "scope": "take:07",
                "artifact": {
                    "path": "takes/rejected/take07.mp4",
                    "sha256": APPROVED_HASH,
                },
            },
            workspace_root=self.workspace,
        )

        self.assertEqual(record["state"], "REPLACEMENT_REQUIRED")
        self.assertFalse(record["assemblyAllowed"])
        self.assertTrue(record["sameScopeReplacementAuthorized"])
        self.assertEqual(record["replacementScope"], "take:07")
        self.assertEqual(record["preservedArtifacts"][0]["sha256"], APPROVED_HASH)

        with self.assertRaisesRegex(LiveActionContractError, "REPLACEMENT_SCOPE_MISMATCH"):
            advance_live_action_state(
                record,
                {
                    "type": "LIVE_ACTION_REPLACEMENT_ADMITTED",
                    "actor": "technical",
                    "scope": "take:08",
                    "preflightPassed": True,
                    "gpuAdmissionPassed": True,
                },
                workspace_root=self.workspace,
            )

        record = advance_live_action_state(
            record,
            {
                "type": "LIVE_ACTION_REPLACEMENT_ADMITTED",
                "actor": "technical",
                "scope": "take:07",
                "preflightPassed": True,
                "gpuAdmissionPassed": True,
            },
            workspace_root=self.workspace,
        )
        self.assertEqual(record["state"], "RENDER_AUTHORIZED")
        self.assertTrue(record["renderAuthorized"])
        self.assertFalse(record["assemblyAllowed"])

    def test_intermediate_guide_conflict_requires_two_preserved_failures(self) -> None:
        record = {
            "state": "TECHNICAL_REPLACEMENT_REQUIRED",
            "history": [],
            "replacementScope": "take:09",
            "sameScopeReplacementAuthorized": True,
            "preservedArtifacts": [
                {"path": "takes/rejected/take09_attempt01.mp4", "sha256": APPROVED_HASH, "attempt": 1, "scope": "take:09"},
                {"path": "takes/rejected/take09_attempt02.mp4", "sha256": APPROVED_HASH, "attempt": 2, "scope": "take:09"},
            ],
        }
        event = {
            "type": "LIVE_ACTION_INTERMEDIATE_GUIDE_CONFLICT_PROVEN",
            "actor": "technical",
            "sameDefectConfirmed": True,
            "intermediateAnchor": {
                "path": "anchors/take09_middle.png",
                "sha256": APPROVED_HASH,
                "immutable": True,
            },
        }
        updated = advance_live_action_state(record, event, workspace_root=self.workspace)
        self.assertEqual(updated["state"], "TECHNICAL_REPLACEMENT_REQUIRED")
        self.assertFalse(updated["exactIntermediateGuideInjectionAllowed"])
        self.assertTrue(updated["startEndOnlyCorrectionAllowed"])
        self.assertEqual(updated["guideConflictEvidence"]["preservedAttempts"], [1, 2])

        broken = dict(record)
        broken["preservedArtifacts"] = record["preservedArtifacts"][:1]
        with self.assertRaisesRegex(LiveActionContractError, "TWO_PRESERVED_GUIDE_FAILURES_REQUIRED"):
            advance_live_action_state(broken, event, workspace_root=self.workspace)

    def test_owner_route_rejection_preserves_master_and_registers_combat_plan_without_render(self) -> None:
        record = {
            "state": "FINISH_CANDIDATE_READY",
            "history": [],
            "renderAuthorized": False,
        }
        record = advance_live_action_state(
            record,
            {
                "type": "LIVE_ACTION_OWNER_ROUTE_REJECTED",
                "actor": "owner",
                "scope": "route:r15",
                "artifact": {
                    "path": "deliveries/r15_master.mp4",
                    "sha256": APPROVED_HASH,
                },
                "declaredFailures": [
                    "generic choreography",
                    "weak physics",
                    "signature move identity missing",
                ],
                "strengthsPreservedAsConstraints": [
                    "stable visual identity",
                    "no hallucinated anatomy",
                ],
            },
            workspace_root=self.workspace,
        )
        self.assertEqual(record["state"], "ROUTE_REPLACEMENT_REQUIRED")
        self.assertTrue(record["rejectedRoutePreserved"])
        self.assertFalse(record["promotionAllowed"])

        record = advance_live_action_state(
            record,
            {
                "type": "LIVE_ACTION_SIGNATURE_COMBAT_PLAN_REGISTERED",
                "actor": "technical",
                "scope": "route:r15",
                "combatPlan": {
                    "path": "routes/r16/combat_plan.json",
                    "sha256": APPROVED_HASH,
                },
            },
            workspace_root=self.workspace,
        )
        self.assertEqual(record["state"], "COMBAT_PLAN_PENDING_OWNER_REVIEW")
        self.assertFalse(record["renderAuthorized"])
        self.assertEqual(record["combatPlan"]["path"], "routes/r16/combat_plan.json")


if __name__ == "__main__":
    unittest.main()
