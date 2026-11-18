import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import video_projects as video_projects_module
from video_projects import (
    AnchorConflictError,
    attach_project_final_review_proxy,
    create_project,
    get_project_assembly_readiness,
    get_project,
    get_project_final_output_path,
    get_take_anchor_image_path,
    get_take_audio_candidate_path,
    get_take_audio_candidate_variant_path,
    get_take_audio_delivery_spec,
    get_take_download_path,
    get_take_generation_spec,
    get_take_preview_path,
    get_take_thumbnail_path,
    get_take_upscale_preview_path,
    get_take_upscale_spec,
    list_projects,
    list_director_requests,
    list_takes,
    patch_project,
    patch_take,
    register_take_audio_candidate,
    register_project_final_output,
    review_project_final_output,
    review_take_audio_candidate,
    register_anchor_candidate,
    review_anchor_candidate,
    set_take_generation_state,
    set_take_upscale_state,
)


class VideoProjectsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_rejection_syncs_only_current_project_and_preserves_request(self):
        create_project(self.root, name="Rejeicao Rapida")
        project = self.root / "rejeicao_rapida"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        preview = project / "takes" / "review.mp4"
        preview.write_bytes(b"preserved-video")
        queue["takes"] = [{"id": "01", "maestro_status": "READY", "video": {"output_preview": str(preview)}}]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with mock.patch.object(video_projects_module, "sync_project_ready_exports") as sync:
            result = patch_take(self.root, "rejeicao_rapida", "01", {
                "status": "REJECTED",
                "directorRequest": {"category": "PROGRESSION", "reason": "Comeca robotizado e lento"},
            })
        sync.assert_called_once_with(project.resolve(), queue_path=queue_path.resolve())
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["directorRequest"]["reason"], "Comeca robotizado e lento")
        self.assertEqual(preview.read_bytes(), b"preserved-video")

    def test_list_takes_omits_items_explicitly_hidden_from_maestro(self):
        create_project(self.root, name="Revisao Sem Microtakes Internos")
        queue_path = self.root / "revisao_sem_microtakes_internos" / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [
            {"id": "01", "maestro_status": "PLANNED"},
            {
                "id": "MT12",
                "role": "transition_microtake",
                "visible_in_maestro": False,
                "maestro_status": "REJECTED",
            },
        ]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        listed = list_takes(self.root, "revisao_sem_microtakes_internos")

        self.assertEqual(listed["pagination"]["totalItems"], 1)
        self.assertEqual([item["takeId"] for item in listed["data"]], ["01"])

    def test_preanalysis_gallery_accepts_single_start_for_explicit_h3_dynamic_end(self):
        gallery = self.root / "qc" / "M08_SCALE_V5_SEEDS.png"
        gallery.parent.mkdir(parents=True)
        Image.new("RGB", (320, 180), (20, 30, 40)).save(gallery)
        gallery_sha256 = video_projects_module.hashlib.sha256(
            gallery.read_bytes()
        ).hexdigest()
        take = {
            "id": "M08",
            "end_image": {
                "status": "DYNAMIC_END_FROM_H3_TAKE_NOT_PRECOMPUTED",
                "static_image_generation_forbidden": True,
                "source_policy": (
                    "LAST_STILL_MOVING_FRAME_OF_HUMAN_APPROVED_H3_TAKE"
                ),
            },
            "preanalysis_anchor_gallery": {
                "status": "READY_HUMAN_REVIEW_PENDING",
                "contact_sheet": "qc/M08_SCALE_V5_SEEDS.png",
                "contact_sheet_sha256": gallery_sha256,
                "candidate_ids": ["M08_START"],
                "h3_choreography_freedom": True,
            },
        }

        resolved, record, actual_sha256 = (
            video_projects_module._validated_preanalysis_gallery(self.root, take)
        )

        self.assertEqual(resolved, gallery.resolve())
        self.assertEqual(record["candidate_ids"], ["M08_START"])
        self.assertEqual(actual_sha256, gallery_sha256)

    def test_preanalysis_gallery_rejects_single_start_without_h3_dynamic_end_contract(self):
        gallery = self.root / "qc" / "M08_SCALE_V5_SEEDS.png"
        gallery.parent.mkdir(parents=True)
        Image.new("RGB", (320, 180), (20, 30, 40)).save(gallery)
        gallery_sha256 = video_projects_module.hashlib.sha256(
            gallery.read_bytes()
        ).hexdigest()
        take = {
            "id": "M08",
            "preanalysis_anchor_gallery": {
                "status": "READY_HUMAN_REVIEW_PENDING",
                "contact_sheet": "qc/M08_SCALE_V5_SEEDS.png",
                "contact_sheet_sha256": gallery_sha256,
                "candidate_ids": ["M08_START"],
                "h3_choreography_freedom": True,
            },
        }

        with self.assertRaisesRegex(ValueError, "END dinamico H3"):
            video_projects_module._validated_preanalysis_gallery(self.root, take)

    def test_take_mode_and_continuity_contract_are_persisted_and_guide_prompt(self):
        create_project(self.root, name="Fluxo Hibrido")
        project = self.root / "fluxo_hibrido"
        keyframe = project / "keyframes" / "precision.png"
        Image.new("RGB", (1280, 720), (25, 35, 45)).save(keyframe)
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "PLANNED",
            "target_duration_seconds": 4,
            "animation_prompt": "The left fighter throws the earring to the right fighter.",
            "base_image": {
                "status": "approved_for_video",
                "file": str(keyframe.resolve()),
            },
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
            },
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        updated = patch_take(self.root, "fluxo_hibrido", "01", {
            "takeMode": "precision",
            "continuityContract": {
                "characterTopology": "Exactly two separate fighters until the fusion flash.",
                "wardrobeLock": "Preserve both approved costumes and earrings.",
                "entryMotion": "The earring is already moving left to right.",
                "exitMotion": "Fusion light expands while both bodies remain readable.",
                "forbiddenTransitions": ["freeze", "crossfade", "static_tail"],
            },
        })

        self.assertEqual(updated["takeMode"], "PRECISION")
        self.assertEqual(
            updated["continuityContract"]["wardrobeLock"],
            "Preserve both approved costumes and earrings.",
        )
        prompt = get_take_generation_spec(
            self.root, "fluxo_hibrido", "01"
        )["prompt"]
        self.assertIn("PRECISION TAKE CONTRACT", prompt)
        self.assertIn("ordered micro-beats", prompt)
        self.assertIn("Exactly two separate fighters", prompt)
        self.assertIn("freeze, crossfade, static_tail", prompt)

    def test_take_mode_rejects_unknown_values_and_legacy_take_is_unspecified(self):
        create_project(self.root, name="Modo Legado")
        project = self.root / "modo_legado"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{"id": "01", "maestro_status": "PLANNED"}]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        self.assertEqual(
            list_takes(self.root, "modo_legado")["data"][0]["takeMode"],
            "UNSPECIFIED",
        )
        with self.assertRaisesRegex(ValueError, "takeMode"):
            patch_take(self.root, "modo_legado", "01", {"takeMode": "montage"})

    def test_assembly_readiness_requires_picture_fhd_and_audio_human_approval(self):
        create_project(self.root, name="Montagem Segura")
        project = self.root / "montagem_segura"
        video = project / "takes" / "take01.mp4"
        video.write_bytes(b"approved-video")
        audio = project / "audio" / "take01.wav"
        audio.write_bytes(b"pending-audio")
        upscale = project / "qc" / "take01_fhd.mp4"
        upscale.write_bytes(b"pending-upscale")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "target_duration_seconds": 10,
            "video": {
                "output_active": str(video.resolve()),
                "upscale_candidate": {
                    "path": str(upscale.resolve()),
                    "status": "PENDING_HUMAN_REVIEW",
                },
            },
            "audio_direction": {
                "delivery_required": True,
                "human_listening_required": True,
                "human_listening_completed": False,
                "salvage_candidate": {
                    "file": str(audio.resolve()),
                    "status": "candidate_pending_human_listening",
                },
            },
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        blocked = get_project_assembly_readiness(self.root, "montagem_segura")
        self.assertFalse(blocked["ready"])
        self.assertEqual(
            {item["code"] for item in blocked["blockers"]},
            {"UPSCALE_REVIEW_PENDING", "AUDIO_NOT_APPROVED"},
        )

        queue["takes"][0]["video"]["upscale_candidate"]["status"] = "APPROVED"
        queue["takes"][0]["audio_direction"].update({
            "human_listening_required": False,
            "human_listening_completed": True,
        })
        queue["takes"][0]["audio_direction"]["salvage_candidate"][
            "status"
        ] = "approved_human_listening"
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        ready = get_project_assembly_readiness(self.root, "montagem_segura")
        self.assertTrue(ready["ready"])
        self.assertEqual(ready["sources"][0]["takeId"], "01")
        self.assertEqual(ready["sources"][0]["videoFile"], "takes/take01.mp4")
        self.assertEqual(ready["sources"][0]["audioFile"], "audio/take01.wav")
        self.assertRegex(ready["sourceFingerprint"], r"^[a-f0-9]{64}$")

    def test_registered_master_is_stale_when_approved_source_fingerprint_changes(self):
        create_project(self.root, name="Master Rastreavel")
        project = self.root / "master_rastreavel"
        take_file = project / "takes" / "take01.mp4"
        take_file.write_bytes(b"current-approved-source")
        master_file = project / "output" / "master.mp4"
        master_file.write_bytes(b"old-master")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "target_duration_seconds": 4,
            "video": {"output_active": str(take_file.resolve())},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["final_output"] = {
            "file": str(master_file.relative_to(project)),
            "duration_seconds": 4,
            "source_fingerprint": "0" * 64,
            "qc_status": "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING",
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        view = get_project(self.root, "master_rastreavel")
        self.assertTrue(view["assemblyReadiness"]["ready"])
        self.assertTrue(view["finalOutput"]["stale"])
        self.assertEqual(view["finalOutput"]["reviewStatus"], "PENDING_OWNER_REVIEW")

    def test_final_output_registration_requires_current_sources_and_owner_review(self):
        create_project(self.root, name="Revisao do Master")
        project = self.root / "revisao_do_master"
        take_file = project / "takes" / "take01.mp4"
        take_file.write_bytes(b"approved-take")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "target_duration_seconds": 4,
            "video": {"output_active": str(take_file.resolve())},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        readiness = get_project_assembly_readiness(self.root, "revisao_do_master")
        master = project / "output" / "master_v1.mp4"
        review = project / "output" / "review_v1.mp4"
        master.write_bytes(b"master")
        review.write_bytes(b"review")

        registered = register_project_final_output(
            self.root,
            "revisao_do_master",
            expected_source_fingerprint=readiness["sourceFingerprint"],
            record={
                "file": "output/master_v1.mp4",
                "review_file": "output/review_v1.mp4",
                "duration_seconds": 4,
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "video_codec": "h264",
                "audio_codec": "aac",
                "sha256": "a" * 64,
                "qc_status": "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING",
            },
        )
        self.assertEqual(
            registered["finalOutput"]["reviewStatus"], "PENDING_OWNER_REVIEW"
        )
        self.assertTrue(registered["finalOutput"]["canReview"])

        approved = review_project_final_output(
            self.root, "revisao_do_master", decision="approve"
        )
        self.assertEqual(approved["status"], "COMPLETED")
        self.assertEqual(approved["finalOutput"]["reviewStatus"], "APPROVED_BY_OWNER")

    def test_final_output_rejection_requires_reason_and_stale_master_cannot_be_approved(self):
        create_project(self.root, name="Master Reprovavel")
        project = self.root / "master_reprovavel"
        take_file = project / "takes" / "take01.mp4"
        take_file.write_bytes(b"source-v1")
        master = project / "output" / "master.mp4"
        master.write_bytes(b"master")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "video": {"output_active": str(take_file.resolve())},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        readiness = get_project_assembly_readiness(self.root, "master_reprovavel")
        register_project_final_output(
            self.root,
            "master_reprovavel",
            expected_source_fingerprint=readiness["sourceFingerprint"],
            record={
                "file": "output/master.mp4",
                "source_fingerprint": readiness["sourceFingerprint"],
                "qc_status": "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING",
            },
        )

        with self.assertRaisesRegex(ValueError, "motivo"):
            review_project_final_output(
                self.root, "master_reprovavel", decision="reject", reason=""
            )
        take_file.write_bytes(b"source-v2")
        with self.assertRaisesRegex(ValueError, "desatualizado"):
            review_project_final_output(
                self.root, "master_reprovavel", decision="approve"
            )

    def test_h3_live_preview_is_explicit_and_profile_scoped(self):
        create_project(self.root, name="Preview H3 Local")
        project = self.root / "preview_h3_local"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "maestro_status": "PLANNED",
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
            },
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        patch_take(self.root, "preview_h3_local", "001", {"h3LivePreview": True})
        persisted = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertTrue(persisted["takes"][0]["video_generation"]["h3_live_preview"])

        persisted["takes"][0]["video_generation"]["profile"] = "wan22_a14b_motion_v1"
        queue_path.write_text(json.dumps(persisted), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exclusivo dos perfis MiniMax H3"):
            patch_take(self.root, "preview_h3_local", "001", {"h3LivePreview": True})

    def test_review_only_project_keeps_video_generation_blocked_after_anchor_approval(self):
        create_project(self.root, name="Revisao somente de ancoras")
        project = self.root / "revisao_somente_de_ancoras"
        keyframe = project / "keyframes" / "anchor.png"
        Image.new("RGB", (1280, 720), (30, 60, 90)).save(keyframe)
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["video_generation_forbidden"] = True
        queue["video_generation_block_reason"] = "Revisao humana de imagens apenas."
        queue["takes"] = [{
            "id": "M01",
            "maestro_status": "PLANNED",
            "video_generation_forbidden": True,
            "video_generation_block_reason": "Revisao humana de imagens apenas.",
            "base_image": {
                "status": "approved_for_video",
                "file": str(keyframe.resolve()),
            },
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
            },
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        listed = list_takes(self.root, "revisao_somente_de_ancoras")["data"][0]
        self.assertFalse(listed["canGenerate"])
        self.assertTrue(listed["generationBlocked"])
        self.assertEqual(listed["generationBlockedReason"], "Revisao humana de imagens apenas.")
        with self.assertRaisesRegex(ValueError, "Revisao humana de imagens apenas"):
            get_take_generation_spec(self.root, "revisao_somente_de_ancoras", "M01")

    def test_continuous_action_generation_contract_is_fail_closed(self):
        queue = {
            "continuous_action_contract": {
                "required": True,
                "generated_connector_required_between_takes": True,
                "crossfade_forbidden": True,
                "freeze_frame_forbidden": True,
                "static_tail_forbidden": True,
                "motion_handoff_required": True,
                "full_duration_motion_required": True,
                "three_interval_motion_required": True,
                "moving_transition_anchors_required": True,
            }
        }
        take = {"shot_contract": {"transition_motion_contract": {"continuity": {
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "interval_motion": {
                "early_0_30": "movimento herdado no inicio",
                "middle_30_70": "acao irreversivel no meio",
                "late_70_100": "consequencia segue ate o fim",
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        }}}}

        video_projects_module._validate_continuous_action_generation_contract(queue, take)
        take["shot_contract"]["transition_motion_contract"]["continuity"][
            "action_occupies_full_duration"
        ] = False
        with self.assertRaisesRegex(ValueError, "action_occupies_full_duration"):
            video_projects_module._validate_continuous_action_generation_contract(queue, take)

    def test_take_execution_contract_rejects_reference_claimed_as_anchor_or_pose_control(self):
        queue = {"take_execution_contract": {
            "required": True,
            "declared_controls_must_exist_in_graph": True,
            "reference_is_not_anchor": True,
            "reference_video_is_not_pose_control": True,
            "model_mode_must_match_conditioning_node": True,
        }}
        take = {
            "control_claims": {
                "anchor_binding": "timeline_exact",
                "motion_binding": "exact_pose",
            },
            "minimax_anchor_control": {"mode": "ref2va_motion"},
        }
        with self.assertRaisesRegex(
            ValueError,
            "TAKE_CONTROL_CONTRACT_UNSATISFIED.*timeline_exact.*nao possui entrada de pose",
        ):
            video_projects_module._validate_take_execution_contract(
                queue,
                take,
                generation_profile="minimax_h3_fl2va_int8_vertical_720x1280p24",
            )

    def test_take_execution_contract_accepts_exact_first_frame_with_prompt_guided_h3_motion(self):
        queue = {"take_execution_contract": {
            "required": True,
            "declared_controls_must_exist_in_graph": True,
            "reference_is_not_anchor": True,
            "reference_video_is_not_pose_control": True,
            "model_mode_must_match_conditioning_node": True,
        }}
        take = {
            "control_claims": {
                "anchor_binding": "first_frame_exact",
                "motion_binding": "prompt_guided",
            },
            "video_generation": {
                "start_end_frame_enabled": False,
                "require_approved_end_frame": False,
            },
        }

        result = video_projects_module._validate_take_execution_contract(
            queue,
            take,
            generation_profile="minimax_h3_fl2va_int8_720p24",
        )

        self.assertEqual(result["anchorBinding"], "first_frame_exact")
        self.assertEqual(result["motionBinding"], "prompt_guided")

        take["video_generation"]["start_end_frame_enabled"] = True
        with self.assertRaisesRegex(
            ValueError,
            "TAKE_CONTROL_CONTRACT_UNSATISFIED.*start_end_frame_enabled=false",
        ):
            video_projects_module._validate_take_execution_contract(
                queue,
                take,
                generation_profile="minimax_h3_fl2va_int8_720p24",
            )

    def test_continuous_action_generation_contract_requires_late_motion(self):
        queue = {
            "continuous_action_contract": {
                "required": True,
                "generated_connector_required_between_takes": True,
                "crossfade_forbidden": True,
                "freeze_frame_forbidden": True,
                "static_tail_forbidden": True,
                "motion_handoff_required": True,
                "full_duration_motion_required": True,
                "three_interval_motion_required": True,
                "moving_transition_anchors_required": True,
            }
        }
        take = {"shot_contract": {"transition_motion_contract": {"continuity": {
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "interval_motion": {
                "early_0_30": "movimento herdado no inicio",
                "middle_30_70": "acao irreversivel no meio",
                "late_70_100": "",
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        }}}}
        with self.assertRaisesRegex(ValueError, "late_70_100"):
            video_projects_module._validate_continuous_action_generation_contract(queue, take)

    def test_continuous_action_generation_contract_rejects_frozen_tail_anchor(self):
        queue = {
            "continuous_action_contract": {
                "required": True,
                "generated_connector_required_between_takes": True,
                "crossfade_forbidden": True,
                "freeze_frame_forbidden": True,
                "static_tail_forbidden": True,
                "motion_handoff_required": True,
                "full_duration_motion_required": True,
                "three_interval_motion_required": True,
                "moving_transition_anchors_required": True,
            }
        }
        take = {"is_transition": True, "shot_contract": {"transition_motion_contract": {"continuity": {
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "interval_motion": {
                "early_0_30": "movimento herdado no inicio",
                "middle_30_70": "acao irreversivel no meio",
                "late_70_100": "consequencia segue ate o fim",
            },
            "moving_anchor_context": {
                "start_source": "take anterior frame final",
                "start_has_motion_before_and_after": False,
                "end_source": "take seguinte frame inicial",
                "end_has_motion_before_and_after": True,
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        }}}}
        with self.assertRaisesRegex(ValueError, "ancora start"):
            video_projects_module._validate_continuous_action_generation_contract(queue, take)

    def test_story_batch_view_opens_a_legacy_client_window_for_correction(self):
        queue = {
            "story_batch_policy": {
                "enabled": True,
                "batch_size": 3,
                "render_order": ["016", "017", "018", "019", "020"],
                "fill_eligible_across_batches": True,
                "require_full_batch": True,
                "allow_incomplete_correction_batch": True,
            },
            "takes": [
                {"id": "016", "maestro_status": "APPROVED"},
                {"id": "017", "maestro_status": "REJECTED"},
                {"id": "018", "maestro_status": "APPROVED"},
                {"id": "019", "maestro_status": "APPROVED"},
                {"id": "020", "maestro_status": "PLANNED"},
            ],
        }

        view = video_projects_module._story_batch_policy_view(queue)

        self.assertTrue(view["correctionMode"])
        self.assertFalse(view["fillEligibleAcrossBatches"])
        self.assertFalse(view["requireFullBatch"])
        self.assertTrue(view["allowIncompleteCorrectionBatch"])

        queue["takes"][1]["maestro_status"] = "APPROVED"
        strict_view = video_projects_module._story_batch_policy_view(queue)
        self.assertFalse(strict_view["correctionMode"])
        self.assertTrue(strict_view["fillEligibleAcrossBatches"])
        self.assertTrue(strict_view["requireFullBatch"])

    @staticmethod
    def _png_bytes(width: int = 1280, height: int = 720, color=(18, 32, 48)) -> bytes:
        buffer = io.BytesIO()
        Image.new("RGB", (width, height), color=color).save(buffer, format="PNG")
        return buffer.getvalue()

    def _pending_anchor(self, project_name: str = "Entrega Ancora") -> tuple[str, Path, str]:
        created = create_project(self.root, name=project_name)
        project_id = created["projectId"]
        project = self.root / project_id
        reference = project / "base_images" / "take01_reference.png"
        reference.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1280, 720), color=(40, 30, 20)).save(reference)
        reference_metadata = reference.with_suffix(".json")
        reference_metadata.write_text(json.dumps({
            "schema_version": "1.0",
            "project_id": project_id,
            "image_file": str(reference),
            "prompt": "Referencia visual aprovada.",
            "validation_status": "approved_for_video",
        }), encoding="utf-8")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01B",
            "slug": "novo_ponto_de_vista",
            "objective": "Criar um novo enquadramento.",
            "animation_prompt": "Mover camera com profundidade real.",
            "maestro_status": "PLANNED",
            "base_image": {
                "status": "needs_derived_anchor",
                "source_approved_image": str(reference),
                "file": str(reference),
                "metadata": str(reference_metadata),
            },
            "video": {"status": "planned"},
            "qc": {"status": "waiting_derived_anchor"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        requested = patch_take(self.root, project_id, "01B", {
            "directorRequest": {
                "category": "ANCHOR",
                "reason": "Criar uma imagem-ancora propria para o novo ponto de vista.",
            },
        })
        return project_id, reference, requested["directorRequest"]["requestId"]

    @staticmethod
    def _anchor_metadata(**updates):
        metadata = {
            "prompt": "Novo enquadramento cinematografico 16:9 sem personagens.",
            "model": "qwen-image-edit",
            "seed": 20260722,
            "sourceOutput": "ComfyUI/output/image_edit_00086_.png",
            "objective": "Criar um novo ponto de vista independente.",
        }
        metadata.update(updates)
        return metadata

    def test_create_list_and_patch_project(self):
        created = create_project(
            self.root,
            name="Filme Teste",
            objective="Validar fluxo",
            duration_seconds=30,
        )
        self.assertEqual(created["projectId"], "filme_teste")
        self.assertTrue((self.root / "filme_teste" / "qc").is_dir())
        listed = list_projects(self.root)
        self.assertEqual(listed["pagination"]["totalItems"], 1)
        patched = patch_project(self.root, "filme_teste", {"status": "IN_PROGRESS"})
        self.assertEqual(patched["status"], "IN_PROGRESS")

    def test_catalog_does_not_validate_every_take_preview_and_anchor(self):
        created = create_project(self.root, name="Catalogo leve")
        queue_path = self.root / created["projectId"] / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [
            {"id": "01", "maestro_status": "APPROVED"},
            {"id": "02", "maestro_status": "GENERATING"},
            {"id": "03", "maestro_status": "REJECTED"},
            {"id": "FILME", "role": "project_final_output", "maestro_status": "FINAL"},
        ]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with mock.patch.object(video_projects_module, "_take_view", side_effect=AssertionError("full take scan")):
            result = list_projects(self.root)
        counts = result["data"][0]["takeCounts"]
        self.assertEqual(counts["planned"], 3)
        self.assertEqual(counts["approved"], 1)
        self.assertEqual(counts["inProduction"], 1)
        self.assertEqual(counts["rejected"], 1)
        self.assertEqual(counts["final"], 0)

    def test_patch_project_updates_final_resolution_to_portrait_fhd(self):
        created = create_project(self.root, name="Filme Vertical")

        patched = patch_project(
            self.root,
            created["projectId"],
            {"finalResolution": "1080x1920"},
        )

        self.assertEqual(
            patched["final"], {"width": 1080, "height": 1920, "fps": 60}
        )
        manifest = json.loads(
            (self.root / created["projectId"] / "project_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["final_resolution"], "1080x1920")
        with self.assertRaisesRegex(ValueError, "finalResolution"):
            patch_project(
                self.root,
                created["projectId"],
                {"finalResolution": "720x1280"},
            )

    def test_patch_project_supports_qhd_uhd_both_orientations(self):
        created=create_project(self.root,name='Acabamento maior')
        for geometry in ('2560x1440','1440x2560','3840x2160','2160x3840'):
            updated=patch_project(self.root,created['projectId'],{'finalResolution':geometry})
            w,h=map(int,geometry.split('x'))
            self.assertEqual(updated['final'],{'width':w,'height':h,'fps':60})

    def test_video_sound_candidate_requires_explicit_human_review(self):
        created = create_project(self.root, name="Som por Video")
        project_id = created["projectId"]
        project = self.root / project_id
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "video": {"status": "ready"},
            "audio_direction": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        candidate = project / "audio" / "video_sound" / "01" / "job-1" / "candidate.wav"
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(b"candidate-audio")

        view = register_take_audio_candidate(
            self.root,
            project_id,
            "01",
            candidate,
            provider_id="fake_v2s",
            model="fake/model",
            source_video_sha256="abc123",
            qc={"durationSeconds": 2.0, "sampleRate": 48000, "channels": 2},
        )

        self.assertTrue(view["audioCandidateNeedsReview"])
        self.assertFalse(view["audioCandidateApproved"])
        reviewed = review_take_audio_candidate(
            self.root,
            project_id,
            "01",
            decision="APPROVED",
        )
        self.assertTrue(reviewed["audioCandidateApproved"])
        self.assertFalse(reviewed["audioCandidateNeedsReview"])

    def test_rejected_video_sound_candidate_is_removed_from_active_slot(self):
        created = create_project(self.root, name="Som Reprovado")
        project_id = created["projectId"]
        project = self.root / project_id
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{"id": "01", "maestro_status": "APPROVED", "video": {}, "audio_direction": {}}]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        candidate = project / "audio" / "video_sound" / "01" / "job-2" / "candidate.wav"
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(b"candidate-audio")
        register_take_audio_candidate(self.root, project_id, "01", candidate, provider_id="fake", model="fake")

        reviewed = review_take_audio_candidate(
            self.root,
            project_id,
            "01",
            decision="REJECTED",
            reason="Impacto fraco",
        )

        self.assertFalse(reviewed["hasAudioCandidate"])
        saved = json.loads(queue_path.read_text(encoding="utf-8"))
        rejected = saved["takes"][0]["audio_direction"]["rejected_candidates"]
        self.assertEqual(rejected[-1]["reason"], "Impacto fraco")

    def test_project_view_uses_manifest_resolution_and_fps(self):
        created = create_project(self.root, name="Perfil do Curta")
        project = self.root / created["projectId"]
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update({
            "preview_resolution": "1280x720",
            "final_resolution": "1920x1080",
            "fps_preview": 24,
            "fps_final": 24,
        })
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        viewed = get_project(self.root, created["projectId"])

        self.assertEqual(viewed["preview"], {"width": 1280, "height": 720, "fps": 24})
        self.assertEqual(viewed["final"], {"width": 1920, "height": 1080, "fps": 24})

    def test_project_exposes_registered_complete_movie_and_review_proxy(self):
        created = create_project(self.root, name="Clipe Completo")
        project = self.root / created["projectId"]
        master = project / "output" / "master_final.mp4"
        review = project / "output" / "master_review.mp4"
        master.write_bytes(b"full-master")
        review.write_bytes(b"review-proxy")
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["final_output"] = {
            "file": str(master),
            "review_file": str(review),
            "duration_seconds": 186.096,
            "width": 1920,
            "height": 1080,
            "fps": 60,
            "video_codec": "h264",
            "audio_codec": "aac",
            "sha256": "abc123",
            "qc_status": "PASS",
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        viewed = get_project(self.root, created["projectId"])

        self.assertTrue(viewed["finalOutput"]["ready"])
        self.assertTrue(viewed["finalOutput"]["hasReviewProxy"])
        self.assertEqual(viewed["finalOutput"]["masterFile"], master.name)
        self.assertEqual(viewed["finalOutput"]["reviewFile"], review.name)
        self.assertEqual(
            get_project_final_output_path(self.root, created["projectId"]),
            review.resolve(),
        )
        self.assertEqual(
            get_project_final_output_path(
                self.root,
                created["projectId"],
                download=True,
            ),
            master.resolve(),
        )

    def test_attach_final_review_proxy_preserves_master_history_and_human_gate(self):
        created = create_project(self.root, name="Clipe com proxy tardio")
        project = self.root / created["projectId"]
        master = project / "output" / "master_fhd.mp4"
        review = project / "qc" / "review_proxy.mp4"
        master.write_bytes(b"master-fhd-preservado")
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_bytes(b"proxy-browser")
        master_sha256 = video_projects_module.hashlib.sha256(
            master.read_bytes()
        ).hexdigest()
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["final_output"] = {
            "file": str(master),
            "sha256": master_sha256,
            "registered_at": "2026-08-26T17:49:59-03:00",
            "human_review": {
                "status": "PENDING_OWNER_REVIEW",
                "required": True,
            },
        }
        manifest["final_output_history"] = [{"file": "output/master_aprovado.mp4"}]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "master ativo mudou"):
            attach_project_final_review_proxy(
                self.root,
                created["projectId"],
                expected_master_sha256="0" * 64,
                review_file=review,
            )
        viewed = attach_project_final_review_proxy(
            self.root,
            created["projectId"],
            expected_master_sha256=master_sha256,
            review_file=review,
        )

        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        final = saved["final_output"]
        self.assertEqual(final["file"], str(master))
        self.assertEqual(final["sha256"], master_sha256)
        self.assertEqual(final["registered_at"], "2026-08-26T17:49:59-03:00")
        self.assertEqual(final["human_review"]["status"], "PENDING_OWNER_REVIEW")
        self.assertEqual(saved["final_output_history"], [{"file": "output/master_aprovado.mp4"}])
        self.assertTrue(viewed["finalOutput"]["hasReviewProxy"])
        self.assertEqual(
            get_project_final_output_path(self.root, created["projectId"]),
            review.resolve(),
        )
        self.assertEqual(
            get_project_final_output_path(
                self.root,
                created["projectId"],
                download=True,
            ),
            master.resolve(),
        )

    def test_project_final_output_rejects_media_outside_project(self):
        created = create_project(self.root, name="Clipe Fora")
        project = self.root / created["projectId"]
        outside = self.root / "outside.mp4"
        outside.write_bytes(b"outside")
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["final_output"] = {"file": str(outside)}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        viewed = get_project(self.root, created["projectId"])

        self.assertEqual(viewed["finalOutput"], {"ready": False})
        with self.assertRaises(FileNotFoundError):
            get_project_final_output_path(self.root, created["projectId"])

    def test_project_final_output_fallback_is_not_counted_as_a_production_take(self):
        created = create_project(self.root, name="Clipe com Entrega")
        project = self.root / created["projectId"]
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [
            {"id": "01", "video": {"status": "pending"}, "qc": {}},
            {
                "id": "MASTER",
                "role": "PROJECT_FINAL_OUTPUT",
                "maestro_status": "FINAL",
                "video": {"output_final": str(project / "output" / "master.mp4")},
                "qc": {"status": "final_master_qc_passed"},
            },
        ]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        listed = list_takes(self.root, created["projectId"])
        viewed = get_project(self.root, created["projectId"])

        self.assertEqual(listed["pagination"]["totalItems"], 1)
        self.assertEqual([item["takeId"] for item in listed["data"]], ["01"])
        self.assertEqual(viewed["takeCounts"]["planned"], 1)
        self.assertEqual(viewed["takeCounts"]["final"], 0)

    def test_reads_and_updates_existing_take_queue(self):
        create_project(self.root, name="Takes Reais")
        project = self.root / "takes_reais"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "slug": "abertura",
            "video": {"status": "pending"},
            "qc": {"transition_motion_gate": {"status": "pending_human_review"}},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        self.assertEqual(list_takes(self.root, "takes_reais")["data"][0]["status"], "PLANNED")
        updated = patch_take(self.root, "takes_reais", "01", {"status": "APPROVED", "notes": "bom"})
        self.assertEqual(updated["status"], "APPROVED")
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(queue["takes"][0]["qc"]["status"], "approved_by_owner")
        self.assertEqual(queue["takes"][0]["qc"]["human_visual_approval"], "approved")
        self.assertEqual(
            queue["takes"][0]["qc"]["transition_motion_gate"]["status"],
            "approved_by_owner",
        )
        self.assertEqual(get_project(self.root, "takes_reais")["takeCounts"]["approved"], 1)
        production = patch_take(self.root, "takes_reais", "01", {"status": "IN_PRODUCTION"})
        self.assertEqual(production["status"], "IN_PRODUCTION")
        self.assertEqual(get_project(self.root, "takes_reais")["takeCounts"]["inProduction"], 1)
        with self.assertRaisesRegex(ValueError, "Use o botao de upscale"):
            patch_take(self.root, "takes_reais", "01", {"status": "UPSCALING"})

    def test_take_prompt_can_be_edited_in_maestro_without_priming_visible_text(self):
        create_project(self.root, name="Prompt no Painel")
        project = self.root / "prompt_no_painel"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "animation_prompt": "Pedro escuta a pausa e olha para Mariana.",
            "speaker": "Pedro",
            "dialogue_pt_br": "Agora.",
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        updated = patch_take(self.root, "prompt_no_painel", "001", {
            "animationPrompt": "Pedro escuta a pausa inteira, baixa a mao e Mariana reage uma vez."
        })
        self.assertIn("baixa a mao", updated["animationPrompt"])
        self.assertEqual(updated["speaker"], "Pedro")
        self.assertEqual(updated["dialoguePtBr"], "Agora.")
        with self.assertRaisesRegex(ValueError, "Prompt positivo bloqueado"):
            patch_take(self.root, "prompt_no_painel", "001", {
                "animationPrompt": "Pedro olha para uma interface sem legenda durante toda a cena."
            })

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            get_project(self.root, "../outside")

    def test_builds_safe_take_generation_spec_and_tracks_job(self):
        create_project(self.root, name="Take Animado")
        project = self.root / "take_animado"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["global_negative_rules"] = ["no text"]
        queue["takes"] = [{
            "id": "01",
            "slug": "abertura",
            "animation_prompt": "Camera avanca com parallax forte.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "shot_contract": {"negative_rules": ["no humans"], "variants": {"duration_seconds": 4}},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 124,
                "steps": 20,
                "guidance": 1.0,
                "camera_pose": "Pan Right",
                "camera_speed": 0.5,
            },
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_generation_spec(self.root, "take_animado", "01")
        self.assertEqual(spec["frames"], 124)
        self.assertEqual(spec["fps"], 24)
        self.assertEqual(spec["generationProfile"], "minimax_h3_fl2va_int8_720p24")
        self.assertEqual(spec["cameraPose"], "Pan Right")
        self.assertEqual(spec["cameraSpeed"], 0.5)
        self.assertEqual(spec["steps"], 20)
        self.assertEqual(spec["guidance"], 1.0)
        self.assertIn("no text", spec["negative"])
        self.assertIn("no humans", spec["negative"])
        self.assertIn("subject replacement", spec["negative"])
        self.assertIn("Camera avanca com parallax forte.", spec["prompt"])
        self.assertIn("integrated_multimodal_description:", spec["prompt"])
        self.assertEqual(spec["h3PromptContract"]["mode"], "I2VA")
        queued = set_take_generation_state(
            self.root, "take_animado", "01", status="QUEUED", job_id="abc123"
        )
        self.assertEqual(queued["status"], "QUEUED")
        self.assertEqual(queued["lastJobId"], "abc123")
        self.assertEqual(
            get_take_generation_spec(self.root, "take_animado", "01")["lastJobId"],
            "abc123",
        )

    def test_take_generation_spec_rejects_unknown_generation_profile(self):
        create_project(self.root, name="Perfil Invalido")
        project = self.root / "perfil_invalido"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Camera avanca.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {"profile": "../../modelo_arbitrario"},
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "MiniMax H3"):
            get_take_generation_spec(self.root, "perfil_invalido", "01")

    def test_minimax_h3_take_uses_owner_locked_visual_only_contract(self):
        create_project(self.root, name="Monte Castello H3")
        project = self.root / "monte_castello_h3"
        keyframe = project / "keyframes" / "take001.png"
        end_frame = project / "keyframes" / "take001_end.png"
        keyframe.write_bytes(b"png")
        end_frame.write_bytes(b"end")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "target_duration_seconds": 6,
            "animation_prompt": "A patrulha reptiliana avanca pela encosta.",
            "audio_directive": {
                "status": "awaiting_owner_directive",
                "mode": "visual_only",
                "usage_authorized": False,
            },
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 175,
                "steps": 20,
                "guidance": 1.0,
                "require_approved_end_frame": True,
                "h3_live_preview": True,
            },
            "shot_contract": {
                "visual_references": {
                    "end_frame_file": str(end_frame),
                    "end_frame_approved": True,
                },
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "monte_castello_h3")["data"][0]
        self.assertEqual(take["engine"], "MiniMax H3 FL2VA INT8 + Qwen3-VL-32B")
        self.assertEqual(take["stage"], "MINIMAX_H3_OWNER_LOCKED_BASE")
        self.assertEqual((take["width"], take["height"], take["fps"]), (1280, 720, 24.0))
        self.assertTrue(take["hasEndKeyframe"])
        self.assertTrue(take["canGenerate"])

        spec = get_take_generation_spec(self.root, "monte_castello_h3", "001")
        self.assertEqual(spec["generationProfile"], "minimax_h3_fl2va_int8_720p24")
        self.assertEqual((spec["frames"], spec["steps"], spec["guidance"]), (175, 20, 1.0))
        self.assertTrue(spec["visualOnlyPass"])
        self.assertEqual(spec["endKeyframe"], end_frame.resolve())
        self.assertTrue(spec["h3LivePreview"])
        self.assertEqual(spec["h3PromptContract"]["mode"], "FL2VA")
        self.assertTrue(spec["h3PromptContract"]["localOnly"])
        self.assertIn("How the reference pictures align", spec["prompt"])
        self.assertIn("integrated_multimodal_description:", spec["prompt"])
        self.assertIn("overall_soundscape: N/A", spec["prompt"])
        self.assertIn("non_diegetic_music: N/A", spec["prompt"])

        queue["takes"][0]["shot_contract"]["visual_references"]["end_frame_approved"] = False
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        blocked = list_takes(self.root, "monte_castello_h3")["data"][0]
        self.assertFalse(blocked["canGenerate"])
        self.assertTrue(blocked["generationBlocked"])
        with self.assertRaisesRegex(ValueError, "exige duas ancoras aprovadas"):
            get_take_generation_spec(self.root, "monte_castello_h3", "001")

    def test_minimax_h3_vertical_take_uses_native_9x16_contract(self):
        create_project(self.root, name="Familia Autista Anime Vertical")
        project = self.root / "familia_autista_anime_vertical"
        keyframe = project / "keyframes" / "take001.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "target_duration_seconds": 10.083333,
            "animation_prompt": "A familia caminha em profundidade com movimento anime fluido.",
            "audio_directive": {
                "status": "authorized",
                "mode": "native_joint_av_offscreen_narration",
                "usage_authorized": True,
            },
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
                "width": 720,
                "height": 1280,
                "fps": 24,
                "frames": 243,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "familia_autista_anime_vertical")["data"][0]
        spec = get_take_generation_spec(
            self.root, "familia_autista_anime_vertical", "001"
        )

        self.assertEqual(take["engine"], "MiniMax H3 FL2VA INT8 + Qwen3-VL-32B")
        self.assertEqual((take["width"], take["height"], take["fps"]), (720, 1280, 24.0))
        self.assertEqual(
            spec["generationProfile"],
            "minimax_h3_fl2va_int8_vertical_720x1280p24",
        )
        self.assertEqual((spec["width"], spec["height"]), (720, 1280))
        self.assertEqual((spec["frames"], spec["steps"], spec["guidance"]), (243, 20, 1.0))

    def test_minimax_h3_fails_closed_on_stale_or_uncontrollable_approved_anchors(self):
        create_project(self.root, name="Gogeta H3 Controlado")
        project = self.root / "gogeta_h3_controlado"
        approved_dir = project / "keyframes_live_action_v3_approved"
        approved_dir.mkdir()
        approved_paths = {}
        anchors = []
        roles = {
            "LA01": "canonical_dance_start",
            "LA02": "canonical_hah_two_fingertip_contacts",
            "LA03": "base_gogeta_emergence_black_hair",
            "LA04": "visible_ki_charge_still_black_hair",
        }
        for index, (anchor_id, role) in enumerate(roles.items(), start=1):
            path = approved_dir / f"{anchor_id.lower()}.png"
            Image.new("RGB", (720, 1280), (index * 20, 30, 40)).save(path)
            approved_paths[anchor_id] = path.resolve()
            anchors.append({
                "id": anchor_id,
                "role": role,
                "normalized_file": f"../../keyframes_live_action_v3_approved/{path.name}",
                "normalized_sha256": video_projects_module.hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        manifest_dir = project / "refs" / "live_action_v3_candidates"
        manifest_dir.mkdir(parents=True)
        manifest_path = manifest_dir / "manifest.json"
        manifest_path.write_text(json.dumps({
            "status": "APPROVED_BY_OWNER",
            "candidate_set": "live_action_v3",
            "anchors": anchors,
            "hard_gates": {
                "prompt_only_rerender_forbidden": True,
                "canonical_dance_requires_approved_motion_driver": True,
                "two_distinct_fingertip_contacts": True,
            },
        }), encoding="utf-8")
        stale_start = project / "keyframes" / "stale_start.png"
        stale_end = project / "keyframes" / "stale_end.png"
        Image.new("RGB", (720, 1280), (1, 2, 3)).save(stale_start)
        Image.new("RGB", (720, 1280), (4, 5, 6)).save(stale_end)
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "S01",
            "target_duration_seconds": 15,
            "animation_prompt": "Live action fusion choreography in one continuous shot.",
            "base_image": {"status": "approved_for_video", "file": str(stale_start)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
                "width": 720,
                "height": 1280,
                "fps": 24,
                "frames": 362,
                "steps": 20,
                "guidance": 1.0,
                "require_approved_end_frame": True,
            },
            "shot_contract": {"visual_references": {
                "end_frame_file": str(stale_end),
                "end_frame_approved": True,
            }},
            "minimax_anchor_control": {
                "manifest": "refs/live_action_v3_candidates/manifest.json",
                "mode": "single_pass",
                "start_anchor_id": "LA01",
                "end_anchor_id": "LA04",
            },
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "MINIMAX_STALE_ANCHOR_SELECTION"):
            get_take_generation_spec(self.root, project.name, "S01")

        take = queue["takes"][0]
        take["base_image"]["file"] = str(approved_paths["LA01"])
        take["shot_contract"]["visual_references"]["end_frame_file"] = str(approved_paths["LA04"])
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MINIMAX_H3_PROMPT_ONLY_FORBIDDEN"):
            get_take_generation_spec(self.root, project.name, "S01")

        take["minimax_anchor_control"].update({
            "mode": "multi_anchor_segment",
            "end_anchor_id": "LA02",
        })
        take["shot_contract"]["visual_references"]["end_frame_file"] = str(approved_paths["LA02"])
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MINIMAX_DANCE_CONTROL_MISSING"):
            get_take_generation_spec(self.root, project.name, "S01")

        take["base_image"]["file"] = str(approved_paths["LA03"])
        take["shot_contract"]["visual_references"]["end_frame_file"] = str(approved_paths["LA04"])
        take["minimax_anchor_control"].update({
            "start_anchor_id": "LA03",
            "end_anchor_id": "LA04",
        })
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        spec = get_take_generation_spec(self.root, project.name, "S01")
        self.assertEqual(spec["minimaxAnchorControl"]["candidateSet"], "live_action_v3")
        self.assertEqual(spec["minimaxAnchorControl"]["mode"], "multi_anchor_segment")

        driver_dir = project / "motion_driver_v1"
        driver_dir.mkdir()
        driver_file = driver_dir / "fusion_driver.mp4"
        driver_file.write_bytes(b"approved-driver-video")
        driver_manifest = driver_dir / "driver.json"
        driver_manifest.write_text(json.dumps({
            "status": "APPROVED_BY_OWNER",
            "file": str(driver_file.resolve()),
            "sha256": video_projects_module.hashlib.sha256(driver_file.read_bytes()).hexdigest(),
        }), encoding="utf-8")
        take["base_image"]["file"] = str(approved_paths["LA01"])
        take["shot_contract"]["visual_references"]["end_frame_file"] = str(approved_paths["LA04"])
        take["minimax_anchor_control"].update({
            "mode": "ref2va_motion",
            "anchor_semantics": "appearance_reference_only",
            "start_anchor_id": "LA01",
            "end_anchor_id": "LA04",
            "motion_driver_manifest": "motion_driver_v1/driver.json",
            "reference_subjects": [
                {
                    "description": "the orange-clad adult performer in <Picture 1> and <Picture 2>.",
                    "sources": ["<Picture 1>", "<Picture 2>", "<Picture 3>", "<Video 1>"],
                    "retention": "Keep the same real face, orange practical costume and body proportions.",
                    "relation": "fully_preserved",
                },
                {
                    "description": "the dark-clad adult performer in <Picture 1> and <Picture 2>.",
                    "sources": ["<Picture 1>", "<Picture 2>", "<Picture 4>", "<Video 1>"],
                    "retention": "Keep the same real face, dark practical costume and body proportions.",
                    "relation": "fully_preserved",
                },
            ],
        })
        take["minimax_ref2va_prompt_override"] = (
            "[Shot 1] The supplied pictures are the exclusive photographic appearance references. "
            "Transfer only skeletal joint timing from the supplied video."
        )
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MINIMAX_DANCE_DRIVER_NOT_POSE_CONTROL"):
            get_take_generation_spec(self.root, project.name, "S01")

        driver_payload = json.loads(driver_manifest.read_text(encoding="utf-8"))
        driver_payload["asset_type"] = "dwpose_pose_video"
        driver_manifest.write_text(json.dumps(driver_payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MINIMAX_REF2VA_NOT_EXACT_POSE_CONTROL"):
            get_take_generation_spec(self.root, project.name, "S01")

        approved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        approved_manifest["hard_gates"]["canonical_dance_requires_approved_motion_driver"] = False
        manifest_path.write_text(json.dumps(approved_manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MINIMAX_REF2VA_NOT_EXACT_POSE_CONTROL"):
            get_take_generation_spec(self.root, project.name, "S01")

        approved_manifest["hard_gates"]["two_distinct_fingertip_contacts"] = False
        manifest_path.write_text(json.dumps(approved_manifest), encoding="utf-8")
        spec = get_take_generation_spec(self.root, project.name, "S01")
        self.assertEqual(spec["h3PromptContract"]["mode"], "REF2VA")
        self.assertEqual(len(spec["minimaxAnchorControl"]["referenceImages"]), 4)
        self.assertEqual(spec["minimaxAnchorControl"]["referenceVideo"], driver_file.resolve())
        self.assertFalse(spec["minimaxAnchorControl"]["temporalAnchorBinding"])
        self.assertIn("<Picture 4>", spec["prompt"])
        self.assertIn("<Video 1>", spec["prompt"])
        self.assertIn("<Subject 1>", spec["prompt"])
        self.assertIn("[reference generation]", spec["prompt"])
        self.assertNotIn("Live action fusion choreography", spec["prompt"])
        self.assertIn("does not provide exact joint control", spec["prompt"])
        self.assertNotIn("gogeta", spec["prompt"].lower())

    def test_anchor_png_accepts_exact_vertical_9x16(self):
        image_info = video_projects_module._validate_anchor_png(
            self._png_bytes(width=1080, height=1920)
        )

        self.assertEqual(image_info["width"], 1080)
        self.assertEqual(image_info["height"], 1920)

    def test_minimax_h3_owner_30s_profile_keeps_one_native_ptbr_narrated_take(self):
        create_project(self.root, name="Dia dos Pais H3 30s")
        project = self.root / "dia_dos_pais_h3_30s"
        keyframe = project / "keyframes" / "familia_16x9.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["engine_policy"] = {
            "minimax_h3_owner_long_av": {
                "enabled": True,
                "native_audio_authorized": True,
                "frames": 736,
                "owner_directive": "MiniMax H3, video unico de 30 segundos, narrado pelo proprio video.",
            }
        }
        queue["takes"] = [{
            "id": "01",
            "target_duration_seconds": 30.625,
            "animation_prompt": (
                "One continuous family shot. The father and all three children remain the exact same four people."
            ),
            "narration_tracks": [{
                "speaker": "Narrador em off",
                "text": "Neste Dia dos Pais, celebramos o amor que aprende novos caminhos.",
                "language": "pt-BR",
                "start_seconds": 0.5,
                "end_seconds": 29.5,
            }],
            "audio_direction": {
                "strategy": "minimax_h3_native_narration_ptbr",
                "delivery_required": True,
                "narrator_voice": {
                    "gender": "male",
                    "age": "adult",
                    "accent": "neutral Sao Paulo Brazilian",
                },
            },
            "audio_directive": {
                "usage_authorized": True,
                "mode": "native_joint_av_offscreen_narration",
            },
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_owner_30s_native_av_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 736,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "dia_dos_pais_h3_30s")["data"][0]
        spec = get_take_generation_spec(self.root, "dia_dos_pais_h3_30s", "01")
        audio = get_take_audio_delivery_spec(self.root, "dia_dos_pais_h3_30s", "01")

        self.assertEqual(take["engine"], "MiniMax H3 FL2VA INT8 + Qwen3-VL-32B")
        self.assertEqual(spec["frames"], 736)
        self.assertAlmostEqual(spec["durationSeconds"], 30.625)
        self.assertFalse(spec["visualOnlyPass"])
        self.assertEqual(spec["audioStrategy"], "minimax_h3_native_narration_ptbr")
        self.assertIn("one continuous MiniMax H3 audiovisual generation", spec["prompt"])
        self.assertIn("invisible off-screen narrator", spec["prompt"])
        self.assertIn("neutral Sao Paulo accent", spec["prompt"])
        self.assertEqual(audio["sourceKind"], "minimax_h3_native_offscreen_narration")
        self.assertTrue(audio["narrationRequired"])

    def test_minimax_h3_native_music_requires_owner_directive_and_keeps_av_enabled(self):
        create_project(self.root, name="Dupla Pop H3")
        project = self.root / "dupla_pop_h3"
        keyframe = project / "keyframes" / "dupla_vertical.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "target_duration_seconds": 10.083,
            "animation_prompt": "Two child performers make a short synchronized stage routine with clear beginning, middle and finish.",
            "audio_direction": {
                "strategy": "minimax_h3_native_music",
                "delivery_required": True,
            },
            "audio_directive": {
                "usage_authorized": True,
                "mode": "native_joint_av_original_music",
                "music_direction": "Original upbeat K-pop-inspired instrumental, no lyrics.",
            },
            "h3_prompt_audio": {
                "overall_soundscape": "Live stage ambience, applause and shoe taps synchronized to the choreography.",
                "non_diegetic_music": "Original upbeat K-pop-inspired instrumental, no lyrics.",
            },
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
                "width": 720,
                "height": 1280,
                "fps": 24,
                "frames": 243,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_generation_spec(self.root, "dupla_pop_h3", "01")
        audio = get_take_audio_delivery_spec(self.root, "dupla_pop_h3", "01")

        self.assertFalse(spec["visualOnlyPass"])
        self.assertEqual(spec["audioStrategy"], "minimax_h3_native_music")
        self.assertIn("K-pop-inspired instrumental", spec["prompt"])
        self.assertEqual(audio["sourceKind"], "minimax_h3_native_music")
        self.assertTrue(audio["musicRequired"])

    def test_minimax_h3_native_music_tracks_native_dialogue_requirement(self):
        create_project(self.root, name="Transformacoes H3")
        project = self.root / "transformacoes_h3"
        keyframe = project / "keyframes" / "hero.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "target_duration_seconds": 10.0,
            "animation_prompt": "The hero transforms in one continuous shot.",
            "dialogue_tracks": [
                {"time_seconds": 0.5, "speaker": "hero", "text": "Gear Second!", "language": "en"},
                {"time_seconds": 3.0, "speaker": "hero", "text": "Gear Third!", "language": "en"},
            ],
            "audio_direction": {
                "strategy": "minimax_h3_native_music",
                "delivery_required": True,
            },
            "audio_directive": {"usage_authorized": True},
            "h3_prompt_audio": {
                "overall_soundscape": "Two spoken transformation calls.",
                "non_diegetic_music": "Original cinematic score, no lyrics.",
            },
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
                "width": 720,
                "height": 1280,
                "fps": 24,
                "frames": 243,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        audio = get_take_audio_delivery_spec(self.root, "transformacoes_h3", "01")

        self.assertTrue(audio["dialogueRequired"])
        self.assertTrue(audio["musicRequired"])
        self.assertIn("Gear Second!", audio["text"])
        self.assertEqual(audio["sourceReviewStatus"], "generated_pending_asr_and_human_listening")

    def test_dialogue_audio_delivery_allows_visual_approval_while_audio_remains_pending(self):
        create_project(self.root, name="ADR PT BR")
        project = self.root / "adr_pt_br"
        legacy = project / "takes" / "take_legacy_approved.mp4"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(b"legacy-audio-reference")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "002",
            "dialogue_tracks": [{
                "speaker": "Rafaela",
                "text": "Vocês ouviram isso?",
                "language": "pt-BR",
            }],
            "audio_direction": {
                "strategy": "external_adr_after_visual_qc",
                "delivery_required": True,
                "forbidden_locale": "pt-PT",
            },
            "reuse_assets": {"legacy_video_files": [str(legacy)]},
            "video": {"status": "ready"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_audio_delivery_spec(self.root, "adr_pt_br", "002")
        self.assertTrue(spec["dialogueRequired"])
        self.assertEqual(Path(spec["source"]).resolve(), legacy.resolve())
        self.assertEqual(spec["sourceReviewStatus"], "human_confirmed_pt_br")
        visual_approved = patch_take(
            self.root, "adr_pt_br", "002", {"status": "APPROVED"}
        )
        self.assertEqual(visual_approved["status"], "APPROVED")
        self.assertEqual(
            visual_approved["audioStatus"], "VISUAL_APPROVED_AUDIO_PENDING"
        )
        self.assertTrue(visual_approved["audioRequired"])
        self.assertFalse(visual_approved["audioReady"])
        self.assertTrue(visual_approved["audioHumanReviewRequired"])

        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(
            queue["takes"][0]["qc"]["status"],
            "approved_visual_audio_pending",
        )

        queue["takes"][0]["video"]["audio_delivery"] = {
            "status": "ATTACHED_PENDING_HUMAN_PTBR_LISTENING",
            "required": True,
            "human_listening_required": True,
        }
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        approved = patch_take(self.root, "adr_pt_br", "002", {"status": "APPROVED"})
        self.assertEqual(approved["status"], "APPROVED")
        self.assertEqual(approved["audioStatus"], "APPROVED_HUMAN_LISTENING")
        self.assertFalse(approved["audioHumanReviewRequired"])

    def test_dialogue_without_exact_legacy_source_routes_to_qwen_ptbr_cast_profile(self):
        create_project(self.root, name="Qwen Voz PT BR")
        project = self.root / "qwen_voz_pt_br"
        reference = project / "audio" / "voice_cast_qwen3_tts" / "mariana.wav"
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_bytes(b"voice-reference")
        manifest = {
            "python": r"C:\PemaraAI\qwen3-tts\.venv\Scripts\python.exe",
            "model_dir": r"C:\PemaraAI\qwen3-tts\models\Qwen3-TTS-12Hz-1.7B-Base",
            "profiles": {
                "mariana": {
                    "speaker": "Mariana",
                    "reference_audio": str(reference),
                    "reference_text": "Pedro, quer parar para escutar de novo?",
                    "reference_take": "003",
                    "status": "REFERENCE_READY_PENDING_HUMAN_CAST_REVIEW",
                }
            },
        }
        (project / "audio" / "voice_cast_qwen3_tts.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "017",
            "dialogue_tracks": [{
                "speaker": "Mariana",
                "text": "Pedro, você prefere contar os sons?",
                "language": "pt-BR",
            }],
            "audio_direction": {"delivery_required": True},
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_audio_delivery_spec(self.root, "qwen_voz_pt_br", "017")
        self.assertEqual(spec["sourceKind"], "qwen3_tts_ptbr_voice_clone")
        self.assertEqual(spec["sourceReviewStatus"], "generated_pending_human_listening")
        self.assertEqual(spec["voiceProfile"]["speaker"], "Mariana")
        self.assertEqual(Path(spec["voiceProfile"]["referenceAudio"]).resolve(), reference.resolve())

    def test_minimax_h3_audio_sync_rejection_keeps_external_ptbr_mix_route(self):
        create_project(self.root, name="H3 Sync PT BR")
        project = self.root / "h3_sync_pt_br"
        keyframe = project / "keyframes" / "take003.png"
        keyframe.write_bytes(b"png")
        current = project / "takes" / "take003_audio_bad.mp4"
        current.write_bytes(b"video")
        approved_audio = project / "audio" / "take003.wav"
        approved_audio.write_bytes(b"wav")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "003",
            "animation_prompt": "A camera atravessa o campo cientifico em profundidade real.",
            "target_duration_seconds": 6,
            "dialogue_tracks": [{
                "speaker": "Narrador pt-BR",
                "text": "Trecho aprovado do master narrado.",
                "language": "pt-BR",
            }],
            "audio_direction": {
                "strategy": "external_pt_br_mix_after_video_qc",
                "delivery_required": True,
                "dialogue_generation_authorized": False,
                "salvage_candidate": {
                    "file": str(approved_audio),
                    "status": "approved_human_listening",
                },
            },
            "audio_directive": {"usage_authorized": True},
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 158,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {
                "status": "ready",
                "output_active": str(current),
                "audio_delivery": {
                    "status": "ATTACHED_HUMAN_CONFIRMED_PTBR_SOURCE_PENDING_MIX_REVIEW",
                    "source": str(approved_audio),
                    "source_kind": "owner_approved_ptbr_narration_and_music_segment",
                    "output": str(current),
                    "human_listening_required": True,
                },
            },
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        rejected = patch_take(self.root, "h3_sync_pt_br", "003", {
            "status": "REJECTED",
            "directorRequest": {
                "category": "AUDIO_SYNC",
                "reason": "A narracao ficou fora da duracao do take H3.",
            },
        })

        self.assertEqual(rejected["status"], "REJECTED")
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        take = queue["takes"][0]
        self.assertEqual(
            take["audio_direction"]["strategy"],
            "external_pt_br_mix_after_video_qc",
        )
        self.assertFalse(take["audio_direction"]["dialogue_generation_authorized"])
        self.assertEqual(
            take["video"]["route_status"],
            "AUDIO_SYNC_REJECTED_H3_EXTERNAL_MIX_REPAIR_REQUIRED",
        )
        generation = get_take_generation_spec(self.root, "h3_sync_pt_br", "003")
        self.assertEqual(generation["audioStrategy"], "external_pt_br_mix_after_video_qc")
        self.assertTrue(generation["visualOnlyPass"])

    def test_removed_ltx25_profile_preserves_media_and_blocks_generation(self):
        create_project(self.root, name="Curta LTX Longo")
        project = self.root / "curta_ltx_longo"
        keyframe = project / "keyframes" / "take001_start.png"
        end_frame = project / "keyframes" / "take001_end.png"
        keyframe.write_bytes(b"start")
        end_frame.write_bytes(b"end")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "target_duration_seconds": 10,
            "characters": ["Pedro", "Mariana"],
            "animation_prompt": "Pedro escuta, escolhe e reage em um plano continuo.",
            "audio_direction": {
                "strategy": "visual_pass_adr",
                "dialogue_generation_authorized": False,
            },
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "ltx25_two_stage_distilled_960x544p24",
                "width": 960,
                "height": 544,
                "fps": 24,
                "frames": 241,
                "steps": 8,
                "guidance": 1.0,
            },
            "shot_contract": {
                "distinct_story_events": 2,
                "human_visibility_contract": {
                    "allowed_humans": ["Pedro", "Mariana"],
                },
                "visual_references": {
                    "end_frame_file": str(end_frame),
                    "end_frame_approved": True,
                },
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "curta_ltx_longo")["data"][0]
        self.assertTrue(end_frame.exists())
        self.assertFalse(take["canGenerate"])
        with self.assertRaisesRegex(ValueError, "perfil legado foi removido"):
            get_take_generation_spec(self.root, "curta_ltx_longo", "001")

    def test_generation_spec_rejects_anchor_cast_that_differs_from_prompt_cast(self):
        create_project(self.root, name="Elenco Ancora")
        project = self.root / "elenco_ancora"
        keyframe = project / "keyframes" / "take001_start.png"
        keyframe.write_bytes(b"start")
        keyframe.with_suffix(".json").write_text(
            json.dumps({"required_objects": {"characters": ["Pedro"]}}),
            encoding="utf-8",
        )
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "target_duration_seconds": 5,
            "characters": ["Pedro", "Mariana"],
            "animation_prompt": "Pedro e Mariana atravessam juntos.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 141,
                "steps": 20,
                "guidance": 1.0,
            },
            "shot_contract": {
                "human_visibility_contract": {
                    "allowed_humans": ["Pedro", "Mariana"],
                    "allowed_non_humans": [],
                },
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "CAST_ANCHOR_MISMATCH"):
            get_take_generation_spec(self.root, "elenco_ancora", "001")

        keyframe.with_suffix(".json").write_text(
            json.dumps({"required_objects": {"characters": ["Pedro", "Mariana"]}}),
            encoding="utf-8",
        )
        spec = get_take_generation_spec(self.root, "elenco_ancora", "001")
        self.assertEqual(spec["anchorVisibleCast"], ["Pedro", "Mariana"])

    def test_generation_spec_prefers_verified_visual_cast_over_intended_cast(self):
        create_project(self.root, name="Elenco Visual Verificado")
        project = self.root / "elenco_visual_verificado"
        keyframe = project / "keyframes" / "take001_start.png"
        keyframe.write_bytes(b"start")
        keyframe.with_suffix(".json").write_text(
            json.dumps({
                "required_objects": {"characters": ["Rafaela", "Miro", "Ticô", "Pim"]},
                "visual_qc": {
                    "cast_verification_status": "VERIFIED",
                    "actual_visible_characters": ["Rafaela"],
                },
            }),
            encoding="utf-8",
        )
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "target_duration_seconds": 5,
            "characters": ["Rafaela"],
            "animation_prompt": "Rafaela espera junto aos controles.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 141,
                "steps": 20,
                "guidance": 1.0,
            },
            "shot_contract": {
                "human_visibility_contract": {
                    "allowed_humans": ["Rafaela"],
                    "allowed_non_humans": [],
                },
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_generation_spec(
            self.root, "elenco_visual_verificado", "001"
        )
        self.assertEqual(spec["anchorVisibleCast"], ["Rafaela"])

        queue["takes"][0]["characters"] = ["Rafaela", "Miro"]
        queue["takes"][0]["shot_contract"]["human_visibility_contract"] = {
            "allowed_humans": ["Rafaela"],
            "allowed_non_humans": ["Miro"],
        }
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "CAST_ANCHOR_MISMATCH"):
            get_take_generation_spec(
                self.root, "elenco_visual_verificado", "001"
            )

    def test_generation_spec_strict_project_rejects_unverified_anchor_cast(self):
        create_project(self.root, name="Elenco Visual Obrigatorio")
        project = self.root / "elenco_visual_obrigatorio"
        keyframe = project / "keyframes" / "take001_start.png"
        keyframe.write_bytes(b"start")
        keyframe.with_suffix(".json").write_text(
            json.dumps({"required_objects": {"characters": ["Pedro"]}}),
            encoding="utf-8",
        )
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["anchor_generation_policy"] = {
            "require_visual_cast_verification_for_video": True,
        }
        queue["takes"] = [{
            "id": "001",
            "target_duration_seconds": 5,
            "characters": ["Pedro"],
            "animation_prompt": "Pedro observa o ambiente vazio.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 141,
                "steps": 20,
                "guidance": 1.0,
            },
            "shot_contract": {
                "human_visibility_contract": {
                    "allowed_humans": ["Pedro"],
                    "allowed_non_humans": [],
                },
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "CAST_ANCHOR_UNVERIFIED"):
            get_take_generation_spec(
                self.root, "elenco_visual_obrigatorio", "001"
            )

        keyframe.with_suffix(".json").write_text(
            json.dumps({
                "required_objects": {"characters": ["Pedro", "Mariana"]},
                "visual_qc": {
                    "cast_verification_status": "VERIFIED",
                    "actual_visible_characters": ["Pedro"],
                },
            }),
            encoding="utf-8",
        )
        spec = get_take_generation_spec(
            self.root, "elenco_visual_obrigatorio", "001"
        )
        self.assertEqual(spec["anchorVisibleCast"], ["Pedro"])

    def test_ltx25_generation_spec_rejects_non_native_geometry(self):
        create_project(self.root, name="LTX Geometria Invalida")
        project = self.root / "ltx_geometria_invalida"
        keyframe = project / "keyframes" / "take001.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "001",
            "animation_prompt": "Acao unica.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "ltx25_two_stage_distilled_960x544p24",
                "width": 768,
                "height": 432,
                "fps": 24,
                "frames": 145,
                "steps": 8,
                "guidance": 1.0,
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "perfil legado foi removido"):
            get_take_generation_spec(self.root, "ltx_geometria_invalida", "001")

    def test_transition_motion_gate_rejects_retired_wan_profile(self):
        create_project(self.root, name="Transicao Com Movimento")
        project = self.root / "transicao_com_movimento"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        manifest_path = project / "production_manifest.json"
        manifest_path.write_text(json.dumps({
            "universal_transition_motion_gate": {"required": True},
        }), encoding="utf-8")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Camera atravessa o ambiente com profundidade real.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {"profile": "wan22_a14b_identity_v1"},
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "MiniMax H3"):
            get_take_generation_spec(self.root, "transicao_com_movimento", "01")

    def test_minimax_h3_transition_prompt_does_not_expose_policy_headings_as_visible_copy(self):
        create_project(self.root, name="Transicao H3 Sem Texto Interno")
        project = self.root / "transicao_h3_sem_texto_interno"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        lettering = project / "assets" / "take01_ptbr.ass"
        lettering.parent.mkdir(parents=True, exist_ok=True)
        lettering.write_text("[Script Info]\nScriptType: v4.00+\n", encoding="utf-8")
        manifest_path = project / "production_manifest.json"
        manifest_path.write_text(json.dumps({
            "universal_transition_motion_gate": {"required": True},
        }), encoding="utf-8")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "target_duration_seconds": 6,
            "animation_prompt": "A camera atravessa o laboratorio; a faixa editorial permanece vazia.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "editorial_lettering": {
                "enabled": True,
                "required": True,
                "language": "pt-BR",
                "ass_file": str(lettering),
            },
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 175,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_generation_spec(
            self.root, "transicao_h3_sem_texto_interno", "01"
        )
        self.assertEqual(
            spec["generationProfile"],
            "minimax_h3_fl2va_int8_720p24",
        )
        self.assertNotIn("TRANSITION MOTION COMPLIANCE", spec["prompt"])
        self.assertIn("Keep reserved caption bands", spec["prompt"])
        self.assertEqual(spec["editorialLettering"]["language"], "pt-BR")
        self.assertEqual(spec["editorialLettering"]["assFile"], lettering.resolve())

    def test_minimax_h3_transition_gate_respects_explicit_fixed_camera_contract(self):
        create_project(self.root, name="H3 Camera Fixa")
        project = self.root / "h3_camera_fixa"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        (project / "production_manifest.json").write_text(json.dumps({
            "universal_transition_motion_gate": {"required": True},
        }), encoding="utf-8")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "target_duration_seconds": 5.125,
            "animation_prompt": "Two performers move continuously in a rehearsal.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "shot_contract": {
                "camera": {
                    "movement": "fixed physical tripod for motion validation",
                    "physical_translation": False,
                },
            },
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 124,
                "steps": 20,
                "guidance": 1.0,
            },
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_generation_spec(self.root, "h3_camera_fixa", "01")
        self.assertIn("Keep the approved physical camera fixed", spec["prompt"])
        self.assertNotIn("Use unmistakable physical camera translation", spec["prompt"])

    def test_take_generation_spec_requires_explicit_engine_selection(self):
        create_project(self.root, name="Duracao Fracionada")
        project = self.root / "duracao_fracionada"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Camera avanca.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "shot_contract": {"variants": {"duration_seconds": 4.041667}},
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "duracao_fracionada")["data"][0]
        self.assertEqual(take["generationProfile"], "owner_selection_required")
        self.assertFalse(take["canGenerate"])
        with self.assertRaisesRegex(ValueError, "MiniMax H3"):
            get_take_generation_spec(self.root, "duracao_fracionada", "01")

    def test_ready_generation_registers_project_preview_and_makes_latest_version_active(self):
        create_project(self.root, name="Preview Registrado")
        project = self.root / "preview_registrado"
        old_final = project / "takes" / "take01_old_final.mp4"
        old_final.write_bytes(b"old-final")
        new_preview = project / "takes" / "maestro_generated" / "take_01_job123_wan_preview.mp4"
        new_preview.parent.mkdir(parents=True, exist_ok=True)
        new_preview.write_bytes(b"new-preview")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "video": {
                "output_final": str(old_final),
                "output_preview": str(old_final),
            },
            "qc": {"status": "approved"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        ready = set_take_generation_state(
            self.root,
            "preview_registrado",
            "01",
            status="READY",
            job_id="job123",
            result={
                "outputs": [{
                    "kind": "video",
                    "filename": "video_00001.mp4",
                    "subfolder": "maestro_generative",
                    "type": "output",
                }],
            },
            preview_path=new_preview,
        )

        self.assertEqual(ready["status"], "READY")
        self.assertTrue(ready["hasPreview"])
        self.assertEqual(ready["previewFile"], new_preview.name)
        self.assertEqual(
            get_take_preview_path(self.root, "preview_registrado", "01"),
            new_preview.resolve(),
        )
        persisted = json.loads(queue_path.read_text(encoding="utf-8"))["takes"][0]
        self.assertEqual(persisted["video"]["output_active"], str(new_preview.resolve()))
        self.assertNotIn("output_final", persisted["video"])
        self.assertEqual(persisted["video"]["output_history"][0]["path"], str(old_final))

        outside = self.root / "outside.mp4"
        outside.write_bytes(b"outside")
        with self.assertRaisesRegex(ValueError, "fora do projeto"):
            set_take_generation_state(
                self.root,
                "preview_registrado",
                "01",
                status="READY",
                job_id="job123",
                preview_path=outside,
            )

    def test_old_job_cannot_overwrite_the_current_take(self):
        create_project(self.root, name="Job Atual")
        project = self.root / "job_atual"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{"id": "01", "video": {}, "qc": {}}]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        set_take_generation_state(self.root, "job_atual", "01", status="QUEUED", job_id="new-job")

        with self.assertRaisesRegex(ValueError, "job antigo"):
            set_take_generation_state(
                self.root,
                "job_atual",
                "01",
                status="READY",
                job_id="old-job",
            )

    def test_pending_anchor_status_cannot_be_misread_as_approved(self):
        create_project(self.root, name="Ancora Pendente")
        project = self.root / "ancora_pendente"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Mover camera.",
            "base_image": {"status": "not_approved", "file": str(keyframe)},
            "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "ancora_pendente")["data"][0]
        self.assertFalse(take["keyframeApproved"])
        self.assertFalse(take["canGenerate"])
        with self.assertRaisesRegex(ValueError, "precisa estar aprovada"):
            get_take_generation_spec(self.root, "ancora_pendente", "01")

    def test_pending_anchor_can_request_director_without_rejecting_take(self):
        create_project(self.root, name="Ancora Para Direcao")
        project = self.root / "ancora_para_direcao"
        keyframe = project / "keyframes" / "take01_reference.png"
        keyframe.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01B",
            "slug": "segundo_plano",
            "base_image": {"status": "not_approved", "file": str(keyframe)},
            "video": {"status": "pending"},
            "qc": {"status": "waiting_derived_anchor"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        listed = list_takes(self.root, "ancora_para_direcao")["data"][0]
        self.assertTrue(listed["canRequestAnchor"])
        requested = patch_take(self.root, "ancora_para_direcao", "01B", {
            "directorRequest": {
                "category": "ANCHOR",
                "reason": "Preparar uma imagem-ancora propria para este novo ponto de vista.",
            },
        })
        self.assertEqual(requested["status"], "PLANNED")
        self.assertEqual(requested["qcStatus"], "waiting_derived_anchor")
        self.assertFalse(requested["canGenerate"])
        self.assertEqual(requested["directorRequest"]["status"], "PENDING")
        self.assertEqual(requested["directorRequest"]["category"], "ANCHOR")
        summary = get_project(self.root, "ancora_para_direcao")
        self.assertEqual(summary["takeCounts"]["inProduction"], 0)
        self.assertEqual(summary["takeCounts"]["directorPending"], 1)
        inbox = list_director_requests(self.root)
        self.assertEqual(inbox["pagination"]["totalItems"], 1)
        self.assertEqual(inbox["data"][0]["takeId"], "01B")

        queued_without_executor = set_take_generation_state(
            self.root,
            "ancora_para_direcao",
            "01B",
            status="QUEUED",
            job_id="unrelated-video-job",
        )
        self.assertEqual(queued_without_executor["directorRequest"]["status"], "PENDING")

        with self.assertRaisesRegex(ValueError, "exige que o take esteja reprovado"):
            patch_take(self.root, "ancora_para_direcao", "01B", {
                "directorRequest": {"category": "CAMERA", "reason": "Mover mais a camera."},
            })

    def test_global_anchor_rejection_remains_planned_for_replacement_delivery(self):
        create_project(self.root, name="Ancora Globalmente Reprovada")
        project = self.root / "ancora_globalmente_reprovada"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "slug": "piloto_regenerado",
            "base_image": {
                "status": "needs_derived_anchor",
                "human_approval": "rejected",
            },
            "video": {"status": "pending"},
            "qc": {"status": "waiting_derived_anchor_after_global_rejection"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        listed = list_takes(self.root, "ancora_globalmente_reprovada")["data"][0]
        self.assertEqual(listed["status"], "PLANNED")
        self.assertFalse(listed["hasKeyframe"])
        self.assertTrue(listed["canRequestAnchor"])

        requested = patch_take(self.root, "ancora_globalmente_reprovada", "01", {
            "directorRequest": {
                "category": "ANCHOR",
                "reason": "Gerar a nova ancora apos a reprovacao global.",
            },
        })
        self.assertEqual(requested["status"], "PLANNED")
        self.assertTrue(requested["canRequestAnchor"])
        self.assertEqual(requested["directorRequest"]["status"], "PENDING")

    def test_planned_take_without_any_base_can_request_anchor(self):
        create_project(self.root, name="Base Ausente")
        project = self.root / "base_ausente"
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01A",
            "slug": "foto_base_ausente",
            "video": {"status": "pending"},
            "qc": {"status": "pending"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        listed = list_takes(self.root, "base_ausente")["data"][0]
        self.assertEqual(listed["status"], "PLANNED")
        self.assertFalse(listed["hasKeyframe"])
        self.assertFalse(listed["canGenerate"])
        self.assertTrue(listed["canRequestAnchor"])

        requested = patch_take(self.root, "base_ausente", "01A", {
            "directorRequest": {
                "category": "ANCHOR",
                "reason": "Criar a primeira foto-base deste take.",
            },
        })
        self.assertEqual(requested["status"], "PLANNED")
        self.assertFalse(requested["hasKeyframe"])
        self.assertTrue(requested["canRequestAnchor"])
        self.assertEqual(requested["directorRequest"]["status"], "PENDING")
        self.assertEqual(requested["directorRequest"]["category"], "ANCHOR")

    def test_manifest_selects_active_queue_and_exposes_registered_preview(self):
        create_project(self.root, name="Fila Ativa")
        project = self.root / "fila_ativa"
        preview = project / "takes" / "take01_review.mp4"
        preview.write_bytes(b"mp4")
        active_queue = project / "take_queue_novo.json"
        active_queue.write_text(json.dumps({
            "schema_version": "1.1",
            "project_id": "fila_ativa",
            "takes": [{
                "id": "01",
                "slug": "abertura",
                "maestro_status": "READY",
                "video": {"output_review_candidate": str(preview)},
                "qc": {"status": "visual_pass_pending_user_review"},
            }],
        }), encoding="utf-8")
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["take_queue"] = active_queue.name
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        take = list_takes(self.root, "fila_ativa")["data"][0]
        self.assertEqual(take["status"], "READY")
        self.assertTrue(take["hasPreview"])
        self.assertEqual(take["previewFile"], preview.name)
        self.assertEqual(get_take_preview_path(self.root, "fila_ativa", "01"), preview.resolve())
        patch_take(self.root, "fila_ativa", "01", {"notes": "revisar"})
        updated = json.loads(active_queue.read_text(encoding="utf-8"))
        self.assertEqual(updated["takes"][0]["maestro_notes"], "revisar")

    def test_rejected_take_keeps_preview_and_can_generate_replacement(self):
        create_project(self.root, name="Candidato Reprovado")
        project = self.root / "candidato_reprovado"
        keyframe = project / "keyframes" / "take01.png"
        Image.new("RGB", (640, 360), color=(18, 32, 48)).save(keyframe)
        preview = project / "takes" / "take01_rejected.mp4"
        preview.write_bytes(b"mp4")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "REJECTED",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24"},
            "video": {"output_preview": str(preview)},
            "qc": {"status": "user_rejected"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "candidato_reprovado")["data"][0]
        self.assertEqual(take["status"], "REJECTED")
        self.assertTrue(take["hasPreview"])
        self.assertTrue(take["canGenerate"])
        self.assertEqual(get_take_preview_path(self.root, "candidato_reprovado", "01"), preview.resolve())

    def test_rejection_creates_director_inbox_request_and_tracks_delivery(self):
        create_project(self.root, name="Pedido Direcao")
        project = self.root / "pedido_direcao"
        keyframe = project / "keyframes" / "take01.png"
        Image.new("RGB", (640, 360), color=(18, 32, 48)).save(keyframe)
        preview = project / "takes" / "take01_review.mp4"
        preview.write_bytes(b"mp4")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video": {"output_preview": str(preview)},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        rejected = patch_take(self.root, "pedido_direcao", "01", {
            "status": "REJECTED",
            "directorRequest": {"category": "CAMERA", "reason": "Camera pouco evidente."},
        })
        self.assertEqual(rejected["status"], "REJECTED")
        self.assertEqual(rejected["directorRequest"]["status"], "PENDING")
        self.assertEqual(rejected["directorRequest"]["category"], "CAMERA")
        inbox = list_director_requests(self.root)
        self.assertEqual(inbox["pagination"]["totalItems"], 1)
        self.assertEqual(inbox["data"][0]["projectId"], "pedido_direcao")
        self.assertEqual(get_project(self.root, "pedido_direcao")["takeCounts"]["directorPending"], 1)

        queued = set_take_generation_state(self.root, "pedido_direcao", "01", status="QUEUED", job_id="job1")
        self.assertEqual(queued["directorRequest"]["status"], "IN_PROGRESS")
        delivered = set_take_generation_state(self.root, "pedido_direcao", "01", status="READY", job_id="job1")
        self.assertEqual(delivered["directorRequest"]["status"], "DELIVERED")
        self.assertEqual(list_director_requests(self.root)["pagination"]["totalItems"], 0)
        self.assertEqual(list_director_requests(self.root, status="DELIVERED")["pagination"]["totalItems"], 1)
        unrelated_variant = set_take_generation_state(
            self.root, "pedido_direcao", "01", status="QUEUED", job_id="job2"
        )
        self.assertEqual(unrelated_variant["directorRequest"]["status"], "DELIVERED")

    def test_download_is_released_only_for_finished_review_states(self):
        create_project(self.root, name="Download Seguro")
        project = self.root / "download_seguro"
        preview = project / "takes" / "take01_review.mp4"
        preview.write_bytes(b"mp4")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "REJECTED",
            "video": {"output_preview": str(preview)},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        rejected = list_takes(self.root, "download_seguro")["data"][0]
        self.assertFalse(rejected["canDownload"])
        with self.assertRaises(PermissionError):
            get_take_download_path(self.root, "download_seguro", "01")

        ready = patch_take(self.root, "download_seguro", "01", {"status": "READY"})
        self.assertTrue(ready["canDownload"])
        self.assertEqual(get_take_download_path(self.root, "download_seguro", "01"), preview.resolve())

    def test_upscale_candidate_stays_pending_until_human_approval(self):
        create_project(self.root, name="Upscale Real")
        project = self.root / "upscale_real"
        raw = project / "takes" / "take01_raw.mp4"
        raw.write_bytes(b"raw-video")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24"},
            "video": {
                "output_active": str(raw),
                "output_preview": str(raw),
                "output_review_candidate": str(raw),
            },
            "qc": {"status": "approved"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        approved = list_takes(self.root, "upscale_real")["data"][0]
        self.assertTrue(approved["canUpscale"])
        spec = get_take_upscale_spec(self.root, "upscale_real", "01")
        self.assertEqual(spec["source"], raw.resolve())
        self.assertEqual(spec["upscaleAttempt"], 0)
        self.assertEqual(spec["nextUpscaleAttempt"], 1)

        queued = set_take_upscale_state(
            self.root,
            "upscale_real",
            "01",
            status="QUEUED",
            job_id="upscale-job",
            attempt=spec["nextUpscaleAttempt"],
        )
        self.assertEqual(queued["status"], "UPSCALING")
        self.assertEqual(queued["upscaleStatus"], "QUEUED")
        self.assertEqual(queued["upscaleAttempt"], 1)

        fhd = project / "qc" / "upscaled" / "take_01_review_candidate_1920x1080_24fps.mp4"
        fhd.parent.mkdir(parents=True, exist_ok=True)
        fhd.write_bytes(b"fhd-video")
        sidecar = fhd.with_suffix(".json")
        sidecar.write_text(json.dumps({
            "schema_version": "2.0",
            "type": "pemara_hd_review_candidate_result",
            "human_review_status": "pending",
            "human_approval": {
                "status": "pending",
                "claimed_by_postprocessor": False,
            },
        }), encoding="utf-8")
        ready = set_take_upscale_state(
            self.root,
            "upscale_real",
            "01",
            status="READY",
            job_id="upscale-job",
            attempt=1,
            output_path=fhd,
            sidecar_path=sidecar,
        )
        self.assertEqual(ready["status"], "READY")
        self.assertFalse(ready["isUpscaled"])
        self.assertFalse(ready["canUpscale"])
        self.assertEqual(ready["upscaleJobId"], "upscale-job")
        self.assertTrue(ready["hasUpscalePreview"])
        self.assertEqual(ready["upscalePreviewFile"], fhd.name)
        self.assertEqual(ready["upscaleCandidateStatus"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(get_take_preview_path(self.root, "upscale_real", "01"), raw.resolve())
        self.assertEqual(
            get_take_upscale_preview_path(self.root, "upscale_real", "01"),
            fhd.resolve(),
        )
        for blocked_status in (
            "PLANNED",
            "IN_PRODUCTION",
            "QUEUED",
            "GENERATING",
            "READY",
            "FINAL",
            "ERROR",
        ):
            with self.subTest(blocked_status=blocked_status):
                with self.assertRaisesRegex(ValueError, "Decida o candidato FHD"):
                    patch_take(
                        self.root,
                        "upscale_real",
                        "01",
                        {"status": blocked_status},
                    )
        still_pending = list_takes(self.root, "upscale_real")["data"][0]
        self.assertEqual(still_pending["status"], "READY")
        self.assertTrue(still_pending["hasUpscalePreview"])
        with self.assertRaisesRegex(ValueError, "Decida o candidato FHD"):
            get_take_generation_spec(self.root, "upscale_real", "01")
        for generation_status in ("QUEUED", "GENERATING", "READY", "ERROR"):
            with self.subTest(generation_status=generation_status):
                with self.assertRaisesRegex(ValueError, "Decida o candidato FHD"):
                    set_take_generation_state(
                        self.root,
                        "upscale_real",
                        "01",
                        status=generation_status,
                        job_id="new-video-job",
                    )

        persisted = json.loads(queue_path.read_text(encoding="utf-8"))["takes"][0]
        self.assertEqual(persisted["video"]["output_active"], str(raw))
        self.assertNotIn("output_upscaled", persisted["video"])
        self.assertEqual(
            persisted["video"]["upscale_candidate"]["path"],
            str(fhd.resolve()),
        )

        promoted = patch_take(
            self.root,
            "upscale_real",
            "01",
            {"status": "APPROVED", "notes": "Upscale conferido quadro a quadro."},
        )
        self.assertEqual(promoted["status"], "APPROVED")
        self.assertEqual(promoted["upscaleStatus"], "APPROVED")
        self.assertTrue(promoted["isUpscaled"])
        self.assertFalse(promoted["canUpscale"])
        self.assertFalse(promoted["hasUpscalePreview"])
        self.assertEqual(get_take_preview_path(self.root, "upscale_real", "01"), fhd.resolve())
        with self.assertRaises(FileNotFoundError):
            get_take_upscale_preview_path(self.root, "upscale_real", "01")
        persisted = json.loads(queue_path.read_text(encoding="utf-8"))["takes"][0]
        self.assertEqual(persisted["video"]["output_active"], str(fhd.resolve()))
        self.assertEqual(persisted["video"]["output_upscaled"], str(fhd.resolve()))
        self.assertEqual(persisted["video"]["upscale_history"][0]["decision"], "APPROVED")
        self.assertEqual(persisted["video"]["output_history"][-1]["path"], str(raw))
        approved_sidecar = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(approved_sidecar["human_review_status"], "approved")
        self.assertEqual(approved_sidecar["human_approval"]["status"], "approved")
        self.assertEqual(
            approved_sidecar["human_approval"]["reason"],
            "Upscale conferido quadro a quadro.",
        )
        self.assertTrue(approved_sidecar["human_approval"]["decided_at"])
        self.assertNotIn("rejected_at", approved_sidecar)
        self.assertNotIn("rejection", approved_sidecar)
        # Batch eligibility is idempotent for the approved active candidate,
        # while the explicit spec remains available for a future profile run.
        self.assertEqual(
            get_take_upscale_spec(self.root, "upscale_real", "01")["source"],
            raw.resolve(),
        )

        # A genuinely new active source makes the take batch-eligible again.
        replacement_raw = project / "takes" / "take01_replacement_raw.mp4"
        replacement_raw.write_bytes(b"replacement-raw-video")
        persisted["video"]["output_active"] = str(replacement_raw)
        persisted["video"]["output_review_candidate"] = str(replacement_raw)
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"][0] = persisted
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        changed_source = list_takes(self.root, "upscale_real")["data"][0]
        self.assertTrue(changed_source["canUpscale"])
        self.assertEqual(
            get_take_upscale_spec(self.root, "upscale_real", "01")["source"],
            replacement_raw.resolve(),
        )
        generation_released = set_take_generation_state(
            self.root,
            "upscale_real",
            "01",
            status="QUEUED",
            job_id="new-video-job",
        )
        self.assertEqual(generation_released["status"], "QUEUED")

    def test_vertical_project_upscale_spec_uses_portrait_final_resolution(self):
        create_project(self.root, name="Upscale Vertical")
        project = self.root / "upscale_vertical"
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["final_resolution"] = "1080x1920"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        raw = project / "takes" / "take01_vertical.mp4"
        raw.write_bytes(b"vertical-video")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "video": {
                "output_active": str(raw),
                "output_preview": str(raw),
                "output_review_candidate": str(raw),
            },
            "qc": {"status": "approved"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_upscale_spec(self.root, "upscale_vertical", "01")

        self.assertEqual(spec["targetWidth"], 1080)
        self.assertEqual(spec["targetHeight"], 1920)

    def test_vertical_upscale_approval_persists_portrait_geometry(self):
        create_project(self.root, name="Upscale Vertical Approval")
        project = self.root / "upscale_vertical_approval"
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["final_resolution"] = "1080x1920"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        raw = project / "takes" / "take01_vertical.mp4"
        candidate = project / "qc" / "upscaled" / "take01_vertical_fhd.mp4"
        raw.parent.mkdir(parents=True, exist_ok=True)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"vertical-video")
        candidate.write_bytes(b"vertical-fhd-video")
        sidecar = candidate.with_suffix(".json")
        sidecar.write_text(json.dumps({
            "schema_version": "2.0",
            "type": "pemara_hd_review_candidate_result",
            "human_review_status": "pending",
            "human_approval": {"status": "pending"},
        }), encoding="utf-8")

        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "READY",
            "maestro_pre_upscale_status": "APPROVED",
            "maestro_upscale_status": "READY",
            "video": {
                "output_active": str(raw),
                "upscale_candidate": {
                    "path": str(candidate.resolve()),
                    "metadata": str(sidecar.resolve()),
                    "status": "PENDING_HUMAN_REVIEW",
                    "job_id": "vertical-upscale-job",
                    "attempt": 1,
                },
            },
            "qc": {"status": "upscale_ready_for_user_review"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        approved = patch_take(
            self.root,
            "upscale_vertical_approval",
            "01",
            {"status": "APPROVED", "notes": "Vertical conferido."},
        )

        self.assertEqual(approved["status"], "APPROVED")
        persisted = json.loads(queue_path.read_text(encoding="utf-8"))["takes"][0]
        self.assertEqual(
            (persisted["video"]["width"], persisted["video"]["height"]),
            (1080, 1920),
        )

        # A retried PATCH must also repair geometry persisted by the legacy
        # horizontal-only approval path.
        persisted["video"]["width"] = 1920
        persisted["video"]["height"] = 1080
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"][0] = persisted
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        patch_take(
            self.root,
            "upscale_vertical_approval",
            "01",
            {"status": "APPROVED", "notes": "Reaplicar decisao vertical."},
        )

        repaired = json.loads(queue_path.read_text(encoding="utf-8"))["takes"][0]
        self.assertEqual(
            (repaired["video"]["width"], repaired["video"]["height"]),
            (1080, 1920),
        )

    def test_upscale_decision_does_not_commit_queue_when_sidecar_write_fails(self):
        create_project(self.root, name="Upscale Atomic Decision")
        project = self.root / "upscale_atomic_decision"
        raw = project / "takes" / "take01_raw.mp4"
        candidate = project / "qc" / "upscaled" / "take01_candidate.mp4"
        raw.parent.mkdir(parents=True, exist_ok=True)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"raw-video")
        candidate.write_bytes(b"candidate-video")
        sidecar = candidate.with_suffix(".json")
        sidecar.write_text(json.dumps({
            "schema_version": "2.0",
            "type": "pemara_hd_review_candidate_result",
            "human_review_status": "pending",
            "human_approval": {"status": "pending"},
        }), encoding="utf-8")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "READY",
            "maestro_pre_upscale_status": "APPROVED",
            "maestro_upscale_status": "READY",
            "video": {
                "output_active": str(raw),
                "upscale_candidate": {
                    "path": str(candidate),
                    "metadata": str(sidecar),
                    "status": "PENDING_HUMAN_REVIEW",
                    "job_id": "job-atomic",
                    "attempt": 1,
                },
            },
            "qc": {"status": "upscale_ready_for_user_review"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        queue_before = queue_path.read_bytes()
        sidecar_before = sidecar.read_bytes()
        original_atomic_write = video_projects_module._atomic_json_write

        def fail_sidecar_write(path, data):
            if Path(path).resolve() == sidecar.resolve():
                raise OSError("sidecar disk failure")
            return original_atomic_write(path, data)

        with mock.patch.object(
            video_projects_module,
            "_atomic_json_write",
            side_effect=fail_sidecar_write,
        ):
            with self.assertRaisesRegex(OSError, "sidecar disk failure"):
                patch_take(
                    self.root,
                    "upscale_atomic_decision",
                    "01",
                    {"status": "REJECTED", "notes": "Nao promover este arquivo."},
                )

        self.assertEqual(queue_path.read_bytes(), queue_before)
        self.assertEqual(sidecar.read_bytes(), sidecar_before)

    def test_rejected_upscale_keeps_active_allows_retry_and_blocks_stale_worker(self):
        create_project(self.root, name="Upscale Retry")
        project = self.root / "upscale_retry"
        raw = project / "takes" / "take01_raw.mp4"
        old_fhd = project / "qc" / "upscaled" / "take01_old_approved.mp4"
        raw.parent.mkdir(parents=True, exist_ok=True)
        old_fhd.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"raw-video")
        old_fhd.write_bytes(b"old-fhd")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "APPROVED",
            "video": {
                "output_active": str(old_fhd),
                "output_upscaled": str(old_fhd),
                "output_review_candidate": str(raw),
                "output_preview": str(raw),
            },
            "qc": {"status": "upscale_approved_human_qc"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        # An older approved FHD output is provenance, not a permanent lock.
        listed = list_takes(self.root, "upscale_retry")["data"][0]
        self.assertTrue(listed["isUpscaled"])
        self.assertTrue(listed["canUpscale"])
        first_spec = get_take_upscale_spec(self.root, "upscale_retry", "01")
        self.assertEqual(first_spec["source"], raw.resolve())
        self.assertEqual(first_spec["nextUpscaleAttempt"], 1)
        set_take_upscale_state(
            self.root,
            "upscale_retry",
            "01",
            status="QUEUED",
            job_id="job-1",
            attempt=1,
        )
        first_candidate = project / "qc" / "upscaled" / "take01_attempt1.mp4"
        first_candidate.write_bytes(b"candidate-1")
        first_sidecar = first_candidate.with_suffix(".json")
        first_sidecar.write_text(json.dumps({
            "schema_version": "2.0",
            "type": "pemara_hd_review_candidate_result",
            "human_review_status": "pending",
            "human_approval": {
                "status": "pending",
                "claimed_by_postprocessor": False,
            },
        }), encoding="utf-8")
        set_take_upscale_state(
            self.root,
            "upscale_retry",
            "01",
            status="READY",
            job_id="job-1",
            attempt=1,
            output_path=first_candidate,
            sidecar_path=first_sidecar,
        )

        rejected = patch_take(
            self.root,
            "upscale_retry",
            "01",
            {"status": "REJECTED", "notes": "Contornos artificiais; refazer."},
        )
        self.assertEqual(rejected["status"], "APPROVED")
        self.assertEqual(rejected["upscaleStatus"], "REJECTED")
        self.assertTrue(rejected["canUpscale"])
        self.assertEqual(get_take_preview_path(self.root, "upscale_retry", "01"), old_fhd.resolve())
        with self.assertRaises(FileNotFoundError):
            get_take_upscale_preview_path(self.root, "upscale_retry", "01")
        persisted = json.loads(queue_path.read_text(encoding="utf-8"))["takes"][0]
        self.assertEqual(persisted["video"]["output_active"], str(old_fhd))
        self.assertEqual(persisted["video"]["output_upscaled"], str(old_fhd))
        self.assertEqual(persisted["video"]["upscale_history"][-1]["decision"], "REJECTED")
        self.assertEqual(persisted["video"]["upscale_history"][-1]["path"], str(first_candidate.resolve()))
        rejected_sidecar = json.loads(first_sidecar.read_text(encoding="utf-8"))
        self.assertEqual(rejected_sidecar["human_review_status"], "rejected")
        self.assertEqual(rejected_sidecar["human_approval"]["status"], "rejected")
        self.assertEqual(
            rejected_sidecar["human_approval"]["reason"],
            "Contornos artificiais; refazer.",
        )
        self.assertEqual(
            rejected_sidecar["rejected_at"],
            rejected_sidecar["human_approval"]["decided_at"],
        )
        self.assertEqual(
            rejected_sidecar["rejection"],
            {
                "status": "rejected",
                "reason": "Contornos artificiais; refazer.",
                "decided_at": rejected_sidecar["rejected_at"],
            },
        )
        with self.assertRaisesRegex(ValueError, "decisao humana"):
            set_take_upscale_state(
                self.root,
                "upscale_retry",
                "01",
                status="READY",
                job_id="job-1",
                attempt=1,
                output_path=first_candidate,
            )

        second_spec = get_take_upscale_spec(self.root, "upscale_retry", "01")
        self.assertEqual(second_spec["nextUpscaleAttempt"], 2)
        set_take_upscale_state(
            self.root,
            "upscale_retry",
            "01",
            status="QUEUED",
            job_id="job-2",
            attempt=2,
        )
        with self.assertRaisesRegex(ValueError, "job antigo"):
            set_take_upscale_state(
                self.root,
                "upscale_retry",
                "01",
                status="READY",
                job_id="job-1",
                attempt=1,
                output_path=first_candidate,
            )
        with self.assertRaisesRegex(ValueError, "tentativa antiga"):
            set_take_upscale_state(
                self.root,
                "upscale_retry",
                "01",
                status="UPSCALING",
                job_id="job-2",
                attempt=1,
            )

        second_candidate = project / "qc" / "upscaled" / "take01_attempt2.mp4"
        second_candidate.write_bytes(b"candidate-2")
        current = set_take_upscale_state(
            self.root,
            "upscale_retry",
            "01",
            status="READY",
            job_id="job-2",
            attempt=2,
            output_path=second_candidate,
        )
        self.assertEqual(current["upscaleAttempt"], 2)
        self.assertEqual(current["upscalePreviewFile"], second_candidate.name)
        self.assertEqual(get_take_preview_path(self.root, "upscale_retry", "01"), old_fhd.resolve())

    def test_legacy_inflight_upscale_is_migrated_to_attempt_one_on_recovery(self):
        create_project(self.root, name="Upscale Legacy")
        project = self.root / "upscale_legacy"
        raw = project / "takes" / "take01_raw.mp4"
        raw.write_bytes(b"raw-video")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "maestro_status": "UPSCALING",
            "maestro_upscale_status": "UPSCALING",
            "maestro_last_job_id": "legacy-job",
            "video": {"output_active": str(raw), "output_preview": str(raw)},
            "qc": {"status": "upscale_in_progress"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_upscale_spec(self.root, "upscale_legacy", "01")
        self.assertEqual(spec["lastJobId"], "legacy-job")
        self.assertEqual(spec["upscaleAttempt"], 1)
        self.assertEqual(spec["nextUpscaleAttempt"], 1)
        recovered = set_take_upscale_state(
            self.root,
            "upscale_legacy",
            "01",
            status="QUEUED",
            job_id="legacy-job",
            attempt=1,
        )
        self.assertEqual(recovered["upscaleAttempt"], 1)
        canceled = set_take_upscale_state(
            self.root,
            "upscale_legacy",
            "01",
            status="CANCELED",
            job_id="legacy-job",
            attempt=1,
        )
        self.assertEqual(canceled["status"], "APPROVED")

    def test_exposes_project_keyframe_as_safe_thumbnail(self):
        create_project(self.root, name="Miniaturas")
        project = self.root / "miniaturas"
        thumbnail = project / "keyframes" / "take01.png"
        Image.new("RGB", (640, 480), color=(18, 32, 48)).save(thumbnail)
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "base_image": {"status": "approved_for_video", "file": str(thumbnail)},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "miniaturas")["data"][0]
        self.assertTrue(take["hasKeyframe"])
        self.assertEqual(take["keyframeFile"], thumbnail.name)
        cached = get_take_thumbnail_path(self.root, "miniaturas", "01")
        self.assertTrue(cached.is_file())
        self.assertEqual(cached.suffix, ".jpg")
        self.assertTrue(cached.is_relative_to((project / "qc" / "maestro_thumbnails").resolve()))
        with Image.open(cached) as image:
            self.assertEqual(image.size, (480, 270))

    def test_exposes_project_local_audio_candidate_for_human_listening(self):
        create_project(self.root, name="Escuta Humana")
        project = self.root / "escuta_humana"
        audio = project / "qc" / "voice" / "take_005_candidate.wav"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"RIFF-test-wave")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "005",
            "speaker": "Zuno",
            "dialogue_pt_br": "Ainda bem que voces escutaram.",
            "audio_direction": {
                "human_listening_required": True,
                "salvage_candidate": {
                    "status": "candidate_pending_human_listening",
                    "source_take": "legacy_008",
                    "file": str(audio),
                    "cpu_asr_transcription": "Ainda bem que voces escutaram.",
                    "automatic_approval": False,
                },
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "escuta_humana")["data"][0]
        self.assertTrue(take["hasAudioCandidate"])
        self.assertTrue(take["audioCandidateNeedsReview"])
        self.assertTrue(take["audioHumanListeningRequired"])
        self.assertEqual(take["audioCandidateFile"], audio.name)
        self.assertEqual(take["audioCandidateSource"], "legacy_008")
        self.assertEqual(
            get_take_audio_candidate_path(self.root, "escuta_humana", "005"),
            audio.resolve(),
        )

        outside = self.root / "outside.wav"
        outside.write_bytes(b"outside")
        queue["takes"][0]["audio_direction"]["salvage_candidate"]["file"] = str(outside)
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        hidden = list_takes(self.root, "escuta_humana")["data"][0]
        self.assertFalse(hidden["hasAudioCandidate"])
        with self.assertRaises(FileNotFoundError):
            get_take_audio_candidate_path(self.root, "escuta_humana", "005")

    def test_exposes_named_project_local_audio_variants(self):
        create_project(self.root, name="Variantes de Voz")
        project = self.root / "variantes_de_voz"
        voice_dir = project / "qc" / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        option_a = voice_dir / "option_a.wav"
        option_b = voice_dir / "option_b.wav"
        option_a.write_bytes(b"RIFF-option-a")
        option_b.write_bytes(b"RIFF-option-b")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "015",
            "audio_direction": {
                "human_listening_required": True,
                "salvage_candidate": {
                    "status": "candidate_pending_human_listening",
                    "file": str(option_a),
                },
                "candidate_variants": [
                    {"id": "option_a", "label": "Opcao A", "file": str(option_a), "status": "candidate_pending_human_listening"},
                    {"id": "option_b", "label": "Opcao B", "file": str(option_b), "status": "candidate_pending_human_listening"},
                ],
            },
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        take = list_takes(self.root, "variantes_de_voz")["data"][0]
        self.assertEqual([item["candidateId"] for item in take["audioCandidates"]], ["option_a", "option_b"])
        self.assertTrue(take["audioCandidateNeedsReview"])
        self.assertEqual(
            get_take_audio_candidate_variant_path(
                self.root,
                "variantes_de_voz",
                "015",
                "option_b",
            ),
            option_b.resolve(),
        )
        with self.assertRaises(ValueError):
            get_take_audio_candidate_variant_path(
                self.root,
                "variantes_de_voz",
                "015",
                "../outside",
            )

    def test_rejects_active_queue_outside_project(self):
        create_project(self.root, name="Fila Insegura")
        project = self.root / "fila_insegura"
        manifest_path = project / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["take_queue"] = "../outside.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            list_takes(self.root, "fila_insegura")

    def test_rejects_take_keyframe_outside_project(self):
        create_project(self.root, name="Take Inseguro")
        project = self.root / "take_inseguro"
        outside = self.root / "outside.png"
        outside.write_bytes(b"png")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Mover camera.",
            "base_image": {"status": "approved_for_video", "file": str(outside)},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        with self.assertRaises(ValueError):
            get_take_generation_spec(self.root, "take_inseguro", "01")

    def test_registers_anchor_candidate_for_human_review_idempotently(self):
        project_id, reference, request_id = self._pending_anchor()
        project = self.root / project_id
        cached_reference = get_take_thumbnail_path(self.root, project_id, "01B")
        self.assertTrue(cached_reference.is_file())
        with self.assertRaises(FileNotFoundError):
            get_take_anchor_image_path(self.root, project_id, "01B")

        image_bytes = self._png_bytes()
        metadata = self._anchor_metadata()
        delivered = register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename="image_edit_00086_.png",
            metadata=metadata,
        )

        self.assertEqual(delivered["takeId"], "01B")
        self.assertEqual(delivered["status"], "PLANNED")
        self.assertFalse(delivered["keyframeApproved"])
        self.assertFalse(delivered["canGenerate"])
        self.assertEqual(delivered["qcStatus"], "anchor_delivered_pending_user_approval")
        self.assertEqual(delivered["directorRequest"]["requestId"], request_id)
        self.assertEqual(delivered["directorRequest"]["status"], "DELIVERED")
        self.assertEqual(delivered["anchorCandidate"]["status"], "pending_human_qc")
        self.assertEqual(delivered["anchorCandidate"]["anchorSide"], "start")
        self.assertFalse(cached_reference.exists())
        self.assertTrue(reference.is_file())

        listed = list_takes(self.root, project_id)["data"][0]
        self.assertEqual(listed["anchorCandidate"]["status"], "pending_human_qc")
        self.assertEqual(listed["anchorCandidate"]["anchorSide"], "start")

        candidate = get_take_anchor_image_path(self.root, project_id, "01B")
        self.assertEqual(candidate.read_bytes(), image_bytes)
        sidecar_path = candidate.with_suffix(".json")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(sidecar["validation_status"], "pending_human_qc")
        self.assertEqual(sidecar["director_request_id"], request_id)
        self.assertEqual(sidecar["width"], 1280)
        self.assertEqual(sidecar["height"], 720)
        self.assertEqual(len(sidecar["image_sha256"]), 64)

        queue_path = project / "take_queue.json"
        before_retry = queue_path.read_bytes()
        retried = register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename="same.png",
            metadata=metadata,
        )
        self.assertEqual(retried["anchorCandidate"]["status"], "pending_human_qc")
        self.assertEqual(queue_path.read_bytes(), before_retry)
        self.assertEqual(list_director_requests(self.root)["pagination"]["totalItems"], 0)
        self.assertEqual(
            list_director_requests(self.root, status="DELIVERED")["pagination"]["totalItems"],
            1,
        )

        with self.assertRaises(AnchorConflictError):
            register_anchor_candidate(
                self.root,
                project_id,
                "01B",
                request_id=request_id,
                image_bytes=image_bytes,
                original_filename="same.png",
                metadata=self._anchor_metadata(prompt="Metadados diferentes para a mesma imagem."),
            )
        with self.assertRaises(AnchorConflictError):
            register_anchor_candidate(
                self.root,
                project_id,
                "01B",
                request_id=request_id,
                image_bytes=self._png_bytes(color=(70, 80, 90)),
                original_filename="different.png",
                metadata=metadata,
            )

    def test_registers_and_approves_end_anchor_without_replacing_start_anchor(self):
        created = create_project(self.root, name="Segunda Ancora")
        project_id = created["projectId"]
        project = self.root / project_id
        start = project / "base_images" / "start.png"
        start.parent.mkdir(parents=True, exist_ok=True)
        start.write_bytes(self._png_bytes(color=(10, 20, 30)))
        request_id = "a" * 32
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "05",
            "slug": "first_last",
            "objective": "Validar duas ancoras.",
            "animation_prompt": "Mover entre as duas ancoras.",
            "maestro_status": "PLANNED",
            "base_image": {"status": "approved_for_video", "file": str(start)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "start_end_frame_enabled": True,
                "require_approved_end_frame": True,
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 192,
            },
            "shot_contract": {"visual_references": {"end_frame_approved": False}},
            "maestro_director_requests": [{
                "id": request_id,
                "status": "PENDING",
                "category": "ANCHOR",
                "reason": "Preparar a segunda ancora.",
            }],
            "video": {"status": "planned"},
            "qc": {"status": "waiting_anchor_human_qc"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        image_bytes = self._png_bytes(color=(80, 90, 100))
        metadata = self._anchor_metadata(
            sourceOutput="generated/end.png",
            requiredObjects={"anchorSide": "end", "storyAnchor": "anchor_08"},
        )

        delivered = register_anchor_candidate(
            self.root,
            project_id,
            "05",
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename="anchor_08.png",
            metadata=metadata,
        )

        self.assertTrue(delivered["keyframeApproved"])
        self.assertTrue(delivered["hasEndKeyframeCandidate"])
        self.assertFalse(delivered["hasEndKeyframe"])
        self.assertFalse(delivered["canGenerate"])
        self.assertEqual(get_take_anchor_image_path(self.root, project_id, "05").read_bytes(), image_bytes)

        approved = review_anchor_candidate(
            self.root,
            project_id,
            "05",
            request_id=request_id,
            decision="APPROVED",
            reason="Segunda ancora conferida.",
            human_confirmed=True,
        )

        self.assertTrue(approved["keyframeApproved"])
        self.assertTrue(approved["hasEndKeyframe"])
        self.assertTrue(approved["canGenerate"])
        spec = get_take_generation_spec(self.root, project_id, "05")
        self.assertEqual(spec["keyframe"], start.resolve())
        self.assertEqual(spec["endKeyframe"].read_bytes(), image_bytes)

    def test_approved_end_anchor_inherits_to_next_start_despite_newer_start_request(self):
        created = create_project(self.root, name="Cadeia de Ancoras")
        project_id = created["projectId"]
        project = self.root / project_id
        start = project / "base_images" / "start.png"
        start.parent.mkdir(parents=True, exist_ok=True)
        start.write_bytes(self._png_bytes(color=(12, 24, 36)))
        end_request_id = "b" * 32
        stray_source_request_id = "c" * 32
        next_start_request_id = "d" * 32
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["anchor_generation_policy"] = {
            "inherit_approved_end_as_next_start": True,
        }
        queue["takes"] = [
            {
                "id": "06",
                "slug": "source",
                "animation_prompt": "Concluir em um novo limite visual.",
                "maestro_status": "PLANNED",
                "base_image": {"status": "approved_for_video", "file": str(start)},
                "video_generation": {
                    "profile": "minimax_h3_fl2va_int8_720p24",
                    "start_end_frame_enabled": True,
                    "require_approved_end_frame": True,
                },
                "shot_contract": {"visual_references": {"end_frame_approved": False}},
                "maestro_director_requests": [{
                    "id": end_request_id,
                    "status": "PENDING",
                    "category": "ANCHOR",
                    "reason": "Preparar limite final compartilhado.",
                }],
                "video": {"status": "planned"},
                "qc": {"status": "waiting_anchor_human_qc"},
            },
            {
                "id": "07",
                "slug": "next",
                "animation_prompt": "Comecar no limite visual anterior.",
                "maestro_status": "PLANNED",
                "base_image": {"status": "waiting_anchor_human_qc", "file": ""},
                "video_generation": {
                    "profile": "minimax_h3_fl2va_int8_720p24",
                    "start_end_frame_enabled": False,
                },
                "shot_contract": {"visual_references": {"start_frame_approved": False}},
                "maestro_director_requests": [{
                    "id": next_start_request_id,
                    "status": "PENDING",
                    "category": "ANCHOR",
                    "reason": "Pedido inicial que deve ser substituido pela fronteira compartilhada.",
                }],
                "video": {"status": "planned"},
                "qc": {"status": "waiting_anchor_human_qc"},
            },
        ]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        image_bytes = self._png_bytes(color=(72, 84, 96))
        register_anchor_candidate(
            self.root,
            project_id,
            "06",
            request_id=end_request_id,
            image_bytes=image_bytes,
            original_filename="shared_end.png",
            metadata=self._anchor_metadata(requiredObjects={"anchorSide": "end"}),
        )
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"][0]["maestro_director_requests"].append({
            "id": stray_source_request_id,
            "status": "PENDING",
            "category": "ANCHOR",
            "reason": "Pedido inicial posterior e independente.",
        })
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        approved = review_anchor_candidate(
            self.root,
            project_id,
            "06",
            request_id=end_request_id,
            decision="APPROVED",
            reason="Fronteira compartilhada conferida.",
            human_confirmed=True,
        )

        self.assertEqual(approved["anchorReview"]["inheritedAsNextStartTakeId"], "07")
        next_take = list_takes(self.root, project_id)["data"][1]
        self.assertTrue(next_take["keyframeApproved"])
        self.assertTrue(next_take["canGenerate"])
        self.assertEqual(get_take_generation_spec(self.root, project_id, "07")["keyframe"].read_bytes(), image_bytes)
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(
            queue["takes"][1]["maestro_director_requests"][0]["status"],
            "SUPERSEDED",
        )

    def test_generation_spec_includes_latest_explicit_director_correction(self):
        created = create_project(self.root, name="Correcao no Prompt")
        project_id = created["projectId"]
        project = self.root / project_id
        keyframe = project / "base_images" / "approved.png"
        keyframe.parent.mkdir(parents=True, exist_ok=True)
        keyframe.write_bytes(self._png_bytes(color=(18, 36, 54)))
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "06",
            "slug": "correction",
            "animation_prompt": "Preserve the approved humanoid identity during one physical action.",
            "maestro_status": "REJECTED",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "video_generation": {
                "profile": "minimax_h3_fl2va_int8_720p24",
                "start_end_frame_enabled": False,
                "frames": 124,
                "fps": 24,
                "steps": 20,
                "guidance": 1.0,
                "width": 1280,
                "height": 720,
            },
            "maestro_director_requests": [{
                "id": "e" * 32,
                "status": "PENDING",
                "category": "MORPHING",
                "reason": "No tail from the waist; keep the short antenna attached to the skull.",
                "render_instruction": (
                    "Keep one compact backward-curved cranial crest fused to the scalp, with an ordinary "
                    "humanlike back, narrow waistline and uninterrupted trousers silhouette."
                ),
            }],
            "video": {"status": "rejected"},
            "qc": {"status": "user_rejected_director_pending"},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        spec = get_take_generation_spec(self.root, project_id, "06")

        self.assertIn("MANDATORY DIRECTOR CORRECTION", spec["prompt"])
        self.assertIn("compact backward-curved cranial crest", spec["prompt"])
        self.assertNotIn("No tail from the waist", spec["prompt"])
        self.assertIn("prior preview was explicitly rejected", spec["prompt"])

    def test_approves_anchor_only_after_integrity_checked_human_review(self):
        project_id, _reference, request_id = self._pending_anchor("Aprovar Ancora")
        patch_take(
            self.root,
            project_id,
            "01B",
            {"generationProfile": "minimax_h3_fl2va_int8_720p24"},
        )
        queue_path = self.root / project_id / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"][0]["imagegen_replacement"] = {
            "status": "awaiting_imagegen",
            "request_id": request_id,
            "human_approval_required": True,
        }
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        image_bytes = self._png_bytes(color=(8, 16, 32))
        register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename="candidate.png",
            metadata=self._anchor_metadata(),
        )

        approved = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            decision="APPROVED",
            reason="Composicao e identidade conferidas.",
        )
        self.assertEqual(approved["status"], "PLANNED")
        self.assertTrue(approved["keyframeApproved"])
        self.assertTrue(approved["canGenerate"])
        self.assertEqual(approved["qcStatus"], "anchor_approved_for_video")
        candidate = get_take_anchor_image_path(self.root, project_id, "01B")
        sidecar = json.loads(candidate.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["validation_status"], "approved_for_video")
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(queue["takes"][0]["base_image"]["status"], "approved_for_video")
        replacement = queue["takes"][0]["imagegen_replacement"]
        self.assertEqual(replacement["status"], "approved_for_video")
        self.assertFalse(replacement["human_approval_required"])
        self.assertEqual(replacement["approved_at"], approved["anchorReview"]["reviewedAt"])
        self.assertEqual(get_take_generation_spec(self.root, project_id, "01B")["keyframe"], candidate)

        reviewed_at = approved["anchorReview"]["reviewedAt"]
        replay = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            decision="APPROVED",
            reason="Composicao e identidade conferidas.",
        )
        self.assertEqual(replay["anchorReview"]["reviewedAt"], reviewed_at)
        with self.assertRaises(AnchorConflictError):
            review_anchor_candidate(
                self.root,
                project_id,
                "01B",
                decision="REJECTED",
                reason="Tentativa de decisao oposta.",
            )

        candidate.write_bytes(self._png_bytes(color=(99, 2, 3)))
        tampered = list_takes(self.root, project_id)["data"][0]
        self.assertFalse(tampered["keyframeApproved"])
        self.assertFalse(tampered["canGenerate"])
        with self.assertRaisesRegex(ValueError, "SHA256"):
            get_take_generation_spec(self.root, project_id, "01B")

    def test_strict_anchor_approval_records_and_repairs_verified_empty_cast(self):
        project_id, _reference, request_id = self._pending_anchor("Ancora Sem Pessoas")
        patch_take(
            self.root,
            project_id,
            "01B",
            {"generationProfile": "minimax_h3_fl2va_int8_720p24"},
        )
        queue_path = self.root / project_id / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["anchor_generation_policy"] = {
            "require_visual_cast_verification_for_video": True,
        }
        queue["takes"][0]["characters"] = []
        queue["takes"][0]["shot_contract"] = {
            "human_visibility_contract": {
                "allowed_humans": [],
                "allowed_non_humans": [],
                "exact_human_count": 0,
                "all_people_forbidden": True,
            },
        }
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=self._png_bytes(),
            original_filename="people_free.png",
            metadata=self._anchor_metadata(),
        )

        reason = "Imagem conferida sem qualquer pessoa visivel."
        with self.assertRaisesRegex(ValueError, "actualVisibleCharacters"):
            review_anchor_candidate(
                self.root,
                project_id,
                "01B",
                request_id=request_id,
                decision="APPROVED",
                reason=reason,
            )

        approved = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            decision="APPROVED",
            reason=reason,
            actual_visible_characters=[],
        )
        candidate = get_take_anchor_image_path(self.root, project_id, "01B")
        sidecar_path = candidate.with_suffix(".json")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(
            sidecar["visual_qc"]["cast_verification_status"], "VERIFIED"
        )
        self.assertEqual(sidecar["visual_qc"]["actual_visible_characters"], [])
        self.assertEqual(approved["anchorExpectedVisibleCharacters"], [])
        self.assertEqual(
            get_take_generation_spec(self.root, project_id, "01B")["anchorVisibleCast"],
            [],
        )

        sidecar.pop("visual_qc")
        sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
        repaired = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            decision="APPROVED",
            reason=reason,
            actual_visible_characters=[],
        )
        repaired_sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(repaired["anchorReview"]["actualVisibleCharacters"], [])
        self.assertEqual(
            repaired_sidecar["visual_qc"]["cast_verification_status"], "VERIFIED"
        )

    def test_rejects_anchor_restores_reference_and_creates_one_new_request(self):
        project_id, reference, request_id = self._pending_anchor("Rejeitar Ancora")
        image_bytes = self._png_bytes(color=(88, 44, 22))
        delivered = register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename="candidate.png",
            metadata=self._anchor_metadata(),
        )
        candidate = get_take_anchor_image_path(self.root, project_id, "01B")
        candidate_sidecar = candidate.with_suffix(".json")
        cached_candidate = get_take_thumbnail_path(self.root, project_id, "01B")
        self.assertTrue(cached_candidate.is_file())

        reason = "O ponto de vista ainda repete demais a composicao original."
        rejected = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            decision="REJECTED",
            reason=reason,
        )
        self.assertEqual(rejected["status"], "PLANNED")
        self.assertFalse(rejected["keyframeApproved"])
        self.assertFalse(rejected["canGenerate"])
        self.assertEqual(rejected["qcStatus"], "waiting_derived_anchor_after_rejection")
        self.assertEqual(rejected["directorRequest"]["status"], "PENDING")
        self.assertEqual(rejected["directorRequest"]["category"], "ANCHOR")
        self.assertEqual(rejected["directorRequest"]["reason"], reason)
        self.assertNotEqual(rejected["directorRequest"]["requestId"], request_id)
        self.assertFalse(cached_candidate.exists())
        self.assertTrue(candidate.is_file())
        self.assertTrue(candidate_sidecar.is_file())
        sidecar = json.loads(candidate_sidecar.read_text(encoding="utf-8"))
        self.assertEqual(sidecar["validation_status"], "rejected_human_qc")

        queue_path = self.root / project_id / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        take = queue["takes"][0]
        self.assertEqual(Path(take["base_image"]["file"]).resolve(), reference.resolve())
        self.assertEqual(take["base_image"]["status"], "needs_derived_anchor")
        self.assertEqual(len(take["maestro_director_requests"]), 2)
        self.assertEqual(take["maestro_director_requests"][0]["review_decision"], "REJECTED")
        self.assertEqual(take["maestro_director_requests"][1]["reason"], reason)
        with self.assertRaises(FileNotFoundError):
            get_take_anchor_image_path(self.root, project_id, "01B")

        next_request_id = rejected["directorRequest"]["requestId"]
        replay = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            decision="REJECTED",
            reason=reason,
        )
        self.assertEqual(replay["directorRequest"]["requestId"], next_request_id)
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(len(queue["takes"][0]["maestro_director_requests"]), 2)
        replay_delivery = register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=image_bytes,
            original_filename="candidate.png",
            metadata=self._anchor_metadata(),
        )
        self.assertEqual(replay_delivery["anchorCandidate"]["status"], "rejected_human_qc")

    def test_owner_can_supersede_an_approved_anchor_without_erasing_history(self):
        project_id, _reference, request_id = self._pending_anchor("Revogar Ancora")
        register_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            image_bytes=self._png_bytes(color=(18, 36, 54)),
            original_filename="candidate.png",
            metadata=self._anchor_metadata(),
        )
        review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            decision="APPROVED",
            reason="Primeira aprovacao.",
        )

        reason = "Lote recusado pelo proprietario por humanos, cachimbos e repeticao."
        rejected = review_anchor_candidate(
            self.root,
            project_id,
            "01B",
            request_id=request_id,
            decision="REJECTED",
            reason=reason,
            supersede=True,
        )
        self.assertFalse(rejected["keyframeApproved"])
        self.assertEqual(rejected["qcStatus"], "waiting_derived_anchor_after_rejection")
        queue = json.loads(
            (self.root / project_id / "take_queue.json").read_text(encoding="utf-8")
        )
        request = queue["takes"][0]["maestro_director_requests"][0]
        self.assertEqual(request["review_decision"], "REJECTED")
        self.assertEqual(request["review_history"][0]["decision"], "APPROVED")
        self.assertTrue(request["approval_revoked_at"])
        self.assertEqual(len(queue["takes"][0]["maestro_director_requests"]), 2)

    def test_anchor_delivery_rejects_invalid_png_without_consuming_request(self):
        project_id, _reference, request_id = self._pending_anchor("Ancora Invalida")
        with self.assertRaisesRegex(ValueError, "16:9"):
            register_anchor_candidate(
                self.root,
                project_id,
                "01B",
                request_id=request_id,
                image_bytes=self._png_bytes(width=1024, height=600),
                original_filename="invalid.png",
                metadata=self._anchor_metadata(),
            )
        take = list_takes(self.root, project_id)["data"][0]
        self.assertEqual(take["directorRequest"]["status"], "PENDING")
        self.assertEqual(take["qcStatus"], "waiting_derived_anchor")

    def test_completed_video_remains_visible_when_audio_qc_is_blocked(self):
        create_project(self.root, name="Audio QC Preservado")
        project = self.root / "audio_qc_preservado"
        preview = project / "takes" / "candidate.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"completed-video")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "dialogue_tracks": [{"speaker": "Pedro", "text": "Mais baixo."}],
            "audio_direction": {"delivery_required": True},
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        set_take_generation_state(
            self.root, "audio_qc_preservado", "01", status="GENERATING", job_id="job-1"
        )
        set_take_generation_state(
            self.root,
            "audio_qc_preservado",
            "01",
            status="READY",
            job_id="job-1",
            result={
                "audio_delivery": {
                    "status": "NATIVE_LTX_AV_CANDIDATE_PRESERVED_AUDIO_QC_FAILED",
                    "ready": False,
                    "required": True,
                    "approval_blocked": True,
                    "human_listening_required": True,
                }
            },
            preview_path=preview,
        )

        take = list_takes(self.root, "audio_qc_preservado")["data"][0]
        self.assertEqual(take["status"], "READY")
        self.assertTrue(take["hasPreview"])
        self.assertFalse(take["audioReady"])
        self.assertEqual(
            take["qcStatus"],
            "video_preserved_audio_blocked_pending_human_review",
        )

    def test_visual_only_video_is_not_marked_as_waiting_for_voice_cast(self):
        create_project(self.root, name="Visual Only Review")
        project = self.root / "visual_only_review"
        preview = project / "takes" / "candidate.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"completed-video")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "audio_directive": {"mode": "visual_only"},
            "video": {"status": "planned"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        set_take_generation_state(
            self.root,
            "visual_only_review",
            "01",
            status="READY",
            job_id="job-visual",
            result={
                "audio_delivery": {
                    "status": "NOT_REQUIRED",
                    "ready": True,
                    "required": False,
                    "human_listening_required": False,
                }
            },
            preview_path=preview,
        )

        take = list_takes(self.root, "visual_only_review")["data"][0]
        self.assertEqual(take["status"], "READY")
        self.assertEqual(take["qcStatus"], "video_pending_human_review")

    def test_director_request_history_is_not_truncated(self):
        project_id, _reference, _request_id = self._pending_anchor("Historico Diretor")
        for index in range(105):
            patch_take(self.root, project_id, "01B", {
                "directorRequest": {
                    "category": "ANCHOR",
                    "reason": f"Nova solicitacao de ancora numero {index:03d}.",
                },
            })
        queue = json.loads((self.root / project_id / "take_queue.json").read_text(encoding="utf-8"))
        self.assertEqual(len(queue["takes"][0]["maestro_director_requests"]), 106)


if __name__ == "__main__":
    unittest.main()
