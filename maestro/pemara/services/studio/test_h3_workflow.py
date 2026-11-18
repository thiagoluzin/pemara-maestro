from pathlib import Path
import unittest

from h3_workflow import (
    ENGINE_POLICY,
    FAST_H3_MODEL_NAME,
    FAST_H3_VARIANT,
    H3_FL2VA_MODEL_NAME,
    H3_REF2VA_MODEL_NAME,
    H3_SAGE_ATTENTION_NODE,
    ensure_h3_sage_attention,
    take_readiness,
    validate_h3_comfy_graph,
    workflow_status,
)


class H3WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[2]

    def test_live_inventory_routes_installed_agents_and_official_skill(self):
        status = workflow_status(self.workspace, comfy_online=True)
        self.assertEqual(status["enginePolicy"], ENGINE_POLICY)
        self.assertGreaterEqual(status["catalog"]["installedSkills"], 1)
        self.assertTrue(status["officialPromptSkill"]["ok"])
        self.assertTrue(any(item["name"] == "h3-prompt-writing" for item in status["routedSkills"]))
        self.assertEqual(status["continuousActionContract"]["crossfadeFrames"], 0)
        self.assertEqual(status["qualityPolicy"]["defaultProfile"], "h3_production")
        profiles = {item["id"]: item for item in status["qualityProfiles"]}
        self.assertEqual((profiles["h3_production"]["width"], profiles["h3_production"]["height"], profiles["h3_production"]["steps"]), (1088, 608, [10]))
        self.assertEqual((profiles["h3_production"]["verticalWidth"], profiles["h3_production"]["verticalHeight"]), (608, 1088))
        self.assertFalse(profiles["h3_production"]["nativeAudio"])

    def test_take_readiness_accepts_official_fl2va_contract(self):
        spec = {
            "projectId": "film",
            "takeId": "B01_02",
            "status": "PLANNED",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "keyframeName": "start.png",
            "endKeyframeName": "end.png",
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "prompt": "integrated_multimodal_description: [Shot 1] action\n\noverall_soundscape: N/A\n\nnon_diegetic_music: N/A",
            "h3PromptContract": {
                "mode": "FL2VA",
                "contractVersion": "official",
                "localOnly": True,
            },
        }
        result = take_readiness(spec)
        self.assertTrue(result["ready"])
        self.assertEqual(result["next"], "queue_candidate")

    def test_take_readiness_accepts_official_ref2va_contract(self):
        spec = {
            "projectId": "film",
            "takeId": "S01",
            "status": "PLANNED",
            "generationProfile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
            "keyframeName": "start.png",
            "endKeyframeName": "end.png",
            "minimaxAnchorControl": {
                "referenceImages": ["appearance_1.png", "appearance_2.png"],
                "referenceVideo": "motion.mp4",
            },
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "prompt": (
                "subject_definitions:\n<Subject 1> is the actor whose appearance comes from <Picture 1>; <Video 1> supplies approximate temporal structure\n\n"
                "summary:\nLive action\n\n"
                "retention_analysis:\nPreserve identity\n\n"
                "detailed_description:\n[Shot 1] action\n\n"
                "overall_soundscape:\nN/A\n\n"
                "non_diegetic_music:\nN/A"
            ),
            "h3PromptContract": {
                "mode": "REF2VA",
                "contractVersion": "official",
                "localOnly": True,
            },
        }
        result = take_readiness(spec)
        self.assertTrue(result["ready"])
        self.assertEqual(result["next"], "queue_candidate")

    def test_take_readiness_rejects_ref2va_without_subject_identity_roles(self):
        spec = {
            "generationProfile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
            "minimaxAnchorControl": {
                "referenceImages": ["appearance_1.png", "appearance_2.png"],
                "referenceVideo": "motion.mp4",
            },
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "prompt": (
                "subject_definitions:\n<Picture 1> actor; <Video 1> motion\n\n"
                "summary:\nLive action\n\n"
                "retention_analysis:\nPreserve identity\n\n"
                "detailed_description:\n[Shot 1] action\n\n"
                "overall_soundscape:\nN/A\n\n"
                "non_diegetic_music:\nN/A"
            ),
            "h3PromptContract": {
                "mode": "REF2VA",
                "contractVersion": "official",
                "localOnly": True,
            },
        }
        result = take_readiness(spec)
        self.assertFalse(result["ready"])
        self.assertFalse(next(gate for gate in result["gates"] if gate["id"] == "reference_subjects")["pass"])

    def test_take_readiness_rejects_exact_pose_claim_for_ref2va(self):
        spec = {
            "generationProfile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
            "minimaxAnchorControl": {
                "referenceImages": ["appearance.png"],
                "referenceVideo": "motion.mp4",
            },
            "takeExecutionContract": {
                "declaredControlsVerified": True,
                "motionBinding": "exact_pose",
            },
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "prompt": (
                "subject_definitions:\n<Subject 1> is the actor in <Picture 1>\n\n"
                "summary:\nLive action\n\n"
                "retention_analysis:\nPreserve identity\n\n"
                "detailed_description:\n[Shot 1] action\n\n"
                "overall_soundscape:\nN/A\n\n"
                "non_diegetic_music:\nN/A"
            ),
            "h3PromptContract": {
                "mode": "REF2VA",
                "contractVersion": "official",
                "localOnly": True,
            },
        }
        result = take_readiness(spec)
        self.assertFalse(result["ready"])
        self.assertFalse(next(gate for gate in result["gates"] if gate["id"] == "motion_capability")["pass"])

    def test_take_readiness_rejects_static_or_incomplete_prompt_contract(self):
        spec = {
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "keyframeName": "start.png",
            "endKeyframeName": "end.png",
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "prompt": "a loose prompt",
            "h3PromptContract": {"mode": "FL2VA", "localOnly": True},
        }
        result = take_readiness(spec)
        self.assertFalse(result["ready"])
        self.assertEqual(result["next"], "repair_contract")

    def test_take_readiness_accepts_ref2va_with_appearance_images_only(self):
        spec = {
            "projectId": "luffy",
            "takeId": "01",
            "generationProfile": "minimax_h3_ref2va_int8_vertical_720x1280p24",
            "keyframeName": "start.png",
            "endKeyframeName": "end.png",
            "minimaxAnchorControl": {
                "referenceImages": ["normal.png", "gear2.png", "gear5.png"],
            },
            "takeExecutionContract": {
                "declaredControlsVerified": True,
                "anchorBinding": "references_only",
                "motionBinding": "prompt_guided",
            },
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "prompt": (
                "subject_definitions:\n<Subject 1> is the actor in <Picture 1>\n\n"
                "summary:\nLive action\n\n"
                "retention_analysis:\nPreserve identity\n\n"
                "detailed_description:\n[Shot 1] action\n\n"
                "overall_soundscape:\nNative ambience\n\n"
                "non_diegetic_music:\nOriginal score"
            ),
            "h3PromptContract": {
                "mode": "REF2VA",
                "contractVersion": "official",
                "localOnly": True,
            },
            "status": "REJECTED",
        }
        result = take_readiness(spec)
        self.assertTrue(result["ready"])
        self.assertEqual(result["next"], "queue_candidate")

    def test_graph_gate_rejects_ref2va_conditioning_with_fl2va_weights(self):
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_FL2VA_MODEL_NAME}},
            "2": {"class_type": H3_SAGE_ATTENTION_NODE, "inputs": {"model": ["1", 0]}},
            "3": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0]}},
            "4": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "steps": 10}},
            "6": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {}},
        }
        with self.assertRaisesRegex(ValueError, "H3_GRAPH_MODEL_MISMATCH"):
            validate_h3_comfy_graph(workflow, mode="REF2VA")

    def test_graph_gate_distinguishes_reference_video_from_exact_pose(self):
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_REF2VA_MODEL_NAME}},
            "2": {"class_type": H3_SAGE_ATTENTION_NODE, "inputs": {"model": ["1", 0]}},
            "3": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0]}},
            "4": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "steps": 10}},
            "6": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {}},
        }
        ensure_h3_sage_attention(workflow)
        result = validate_h3_comfy_graph(workflow, mode="REF2VA")
        self.assertTrue(result["ok"])
        with self.assertRaisesRegex(ValueError, "H3_EXACT_POSE_UNSUPPORTED"):
            validate_h3_comfy_graph(
                workflow,
                mode="REF2VA",
                exact_pose_control_required=True,
            )

    def test_sage_patch_is_inserted_and_connected_to_every_sampling_consumer(self):
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_FL2VA_MODEL_NAME}},
            "6": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0]}},
            "7": {"class_type": "BasicScheduler", "inputs": {"model": ["1", 0], "steps": 10}},
            "8": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {}},
        }
        ensure_h3_sage_attention(workflow)
        result = validate_h3_comfy_graph(workflow, mode="T2VA")
        self.assertTrue(result["ok"])
        self.assertEqual(result["sageAttention"], "connected_required")
        sage_nodes = [
            node for node in workflow.values()
            if node.get("class_type") == H3_SAGE_ATTENTION_NODE
        ]
        self.assertEqual(len(sage_nodes), 1)
        self.assertEqual(workflow["6"]["inputs"]["model"], workflow["7"]["inputs"]["model"])

    def test_disconnected_sage_patch_does_not_satisfy_required_attention(self):
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_FL2VA_MODEL_NAME}},
            "2": {"class_type": "OtherModelSource", "inputs": {}},
            "3": {"class_type": H3_SAGE_ATTENTION_NODE, "inputs": {"model": ["2", 0]}},
            "4": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0]}},
            "5": {"class_type": "BasicScheduler", "inputs": {"model": ["1", 0], "steps": 10}},
            "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {}},
        }
        with self.assertRaisesRegex(ValueError, "H3_GRAPH_SAGE_DISCONNECTED"):
            validate_h3_comfy_graph(workflow, mode="T2VA")

    def test_fast_h3_requires_t2v_checkpoint_sage_and_eight_steps(self):
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": FAST_H3_MODEL_NAME}},
            "2": {"class_type": H3_SAGE_ATTENTION_NODE, "inputs": {"model": ["1", 0]}},
            "3": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0]}},
            "4": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "steps": 8}},
            "5": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {}},
        }
        ensure_h3_sage_attention(workflow)
        result = validate_h3_comfy_graph(
            workflow, mode="T2VA", model_variant=FAST_H3_VARIANT
        )
        self.assertTrue(result["ok"])
        for mode in ("I2VA", "FL2VA", "L2VA"):
            self.assertTrue(validate_h3_comfy_graph(workflow, mode=mode, model_variant=FAST_H3_VARIANT)["ok"])
        with self.assertRaisesRegex(ValueError, "H3_FAST_REFERENCE_UNSUPPORTED"):
            validate_h3_comfy_graph(
                workflow, mode="REF2VA", model_variant=FAST_H3_VARIANT
            )
        workflow["4"]["inputs"]["steps"] = 10
        with self.assertRaisesRegex(ValueError, "H3_FAST_STEPS_REQUIRED"):
            validate_h3_comfy_graph(
                workflow, mode="T2VA", model_variant=FAST_H3_VARIANT
            )


if __name__ == "__main__":
    unittest.main()
