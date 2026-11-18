import json
import tempfile
import unittest
from pathlib import Path

from video_gauntlet import (
    PILOT_TAKE_IDS,
    critic_brief,
    create_pilot,
    get_pilot,
    register_reference,
    repair_pilot_anchor_contract,
    repair_pilot_video_contract,
    submit_verdict,
)


class VideoGauntletPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project_id = "gauntlet_pilot_3_takes"
        create_pilot(self.root, project_id=self.project_id)
        self.project = self.root / self.project_id

    def tearDown(self):
        self.temp.cleanup()

    def _set_candidate(self, take_id: str, contents: bytes) -> Path:
        candidate = self.project / "takes" / f"take_{take_id}_candidate.mp4"
        candidate.write_bytes(contents)
        queue_path = self.project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        take = next(item for item in queue["takes"] if item["id"] == take_id)
        take["video"]["output_active"] = str(candidate)
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        return candidate

    def _register_reference(self, take_id: str) -> None:
        reference = self.project / "refs" / f"take_{take_id}_reference.png"
        reference.write_bytes(b"not-a-real-png-but-a-local-reference")
        register_reference(self.root, self.project_id, take_id, f"refs/{reference.name}")

    @staticmethod
    def _scores(value: int = 4, text: int = 5):
        return {
            "characterConsistency": value,
            "composition": value,
            "cameraMotion": value,
            "noGeneratedText": text,
            "crossTakeContinuity": value,
        }

    def _verdict(self, brief, scores, suggested="REGENERATE_RECOMMENDED"):
        return {
            "criticId": "opencode-fresh-critic",
            "candidateSha256": brief["candidate"]["sha256"],
            "suggestedVerdict": suggested,
            "scores": scores,
            "largestGap": "A câmera perde a legibilidade da ação no terço final.",
            "repairPrompt": "Mantenha a ação central e encerre em pose estável, sem reset.",
            "observations": ["Quadros intermediários mostram a ação principal sem leitura suficiente."],
        }

    def test_creates_exactly_three_bounded_takes(self):
        view = get_pilot(self.root, self.project_id)
        self.assertEqual([item["takeId"] for item in view["takes"]], list(PILOT_TAKE_IDS))
        self.assertEqual(view["policy"]["maxRegenerations"], 2)
        self.assertTrue(view["humanApprovalRequired"])
        self.assertTrue((self.project / "README_GAUNTLET_PILOT.md").is_file())

    def test_new_pilot_uses_the_authorized_ltx25_contract_for_every_take(self):
        queue = json.loads((self.project / "take_queue.json").read_text(encoding="utf-8"))
        self.assertEqual(queue["assembly"]["preview"]["fps"], 24)
        for take in queue["takes"]:
            generation = take["video_generation"]
            self.assertEqual(take["target_duration_seconds"], 4)
            self.assertEqual(generation["profile"], "ltx25_two_stage_distilled_960x544p24")
            self.assertEqual(
                (generation["width"], generation["height"], generation["fps"], generation["frames"]),
                (960, 544, 24, 97),
            )
            self.assertEqual((generation["steps"], generation["guidance"]), (8, 1.0))
            self.assertEqual(take["shot_contract"]["distinct_story_events"], 2)
            self.assertIn("physical", take["animation_prompt"].lower())
            self.assertIn("no loop", take["animation_prompt"].lower())

    def test_repair_moves_only_unrendered_planned_takes_to_ltx25(self):
        queue_path = self.project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        for take in queue["takes"]:
            take.pop("video_generation", None)
            take.pop("shot_contract", None)
            take.pop("motion_layers", None)
            take["target_duration_seconds"] = 8
            take["animation_prompt"] = "Legacy placeholder"
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        repaired = repair_pilot_video_contract(self.root, self.project_id)
        self.assertEqual(repaired["videoContractRepair"]["repairedTakeIds"], list(PILOT_TAKE_IDS))
        self.assertFalse(repaired["videoContractRepair"]["renderStarted"])
        fixed_queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertTrue(all(
            take["video_generation"]["profile"] == "ltx25_two_stage_distilled_960x544p24"
            for take in fixed_queue["takes"]
        ))

    def test_anchor_generation_is_text_to_image_without_a_video_style_photo_gate(self):
        queue = json.loads((self.project / "take_queue.json").read_text(encoding="utf-8"))
        policy = queue["anchor_generation_policy"]
        self.assertFalse(policy["pilot_first"])
        self.assertEqual(policy["pilot_takes"], ["01"])
        self.assertFalse(policy["remaining_batch_requires_pilot_human_approval"])
        self.assertTrue(policy["require_explicit_human_confirmation"])
        for take in queue["takes"]:
            base = take["base_image"]
            self.assertEqual(base["generation_mode"], "text_to_image")
            self.assertTrue(base["prompt"])
            self.assertTrue(base["negative_prompt"])
            self.assertIn("number", base["negative_prompt"])

    def test_repair_converts_the_legacy_empty_image_edit_contract(self):
        queue_path = self.project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue.pop("anchor_generation_policy")
        for take in queue["takes"]:
            take["base_image"] = {"status": "reference_required", "reference_file": ""}
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        repaired = repair_pilot_anchor_contract(self.root, self.project_id)
        self.assertEqual(repaired["anchorContractRepair"]["repairedTakeIds"], list(PILOT_TAKE_IDS))
        fixed_queue = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(fixed_queue["anchor_generation_policy"]["pilot_takes"], ["01"])
        self.assertFalse(fixed_queue["anchor_generation_policy"]["pilot_first"])
        self.assertTrue(all(
            take["base_image"]["generation_mode"] == "text_to_image"
            for take in fixed_queue["takes"]
        ))

    def test_repair_restores_an_approval_without_explicit_human_confirmation(self):
        queue_path = self.project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        take = next(item for item in queue["takes"] if item["id"] == "01")
        request_id = "a" * 32
        candidate = self.project / "base_images" / "take01_legacy.png"
        metadata = candidate.with_suffix(".json")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_bytes(b"candidate")
        metadata.write_text(json.dumps({
            "validation_status": "approved_for_video",
            "human_review": {"decision": "APPROVED"},
            "approval_evidence": "legacy",
        }), encoding="utf-8")
        take["base_image"].update({
            "status": "approved_for_video",
            "file": str(candidate),
            "metadata": str(metadata),
            "candidate_request_id": request_id,
            "approved_at": "legacy",
        })
        take["qc"] = {"status": "anchor_approved_for_video"}
        take["maestro_director_requests"] = [{
            "id": request_id,
            "status": "DELIVERED",
            "review_decision": "APPROVED",
            "reviewed_at": "legacy",
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")

        repaired = repair_pilot_anchor_contract(self.root, self.project_id)
        self.assertEqual(
            repaired["anchorContractRepair"]["restoredUnconfirmedApprovalTakeIds"], ["01"]
        )
        fixed_queue = json.loads(queue_path.read_text(encoding="utf-8"))
        fixed_take = next(item for item in fixed_queue["takes"] if item["id"] == "01")
        self.assertEqual(fixed_take["base_image"]["status"], "pending_human_qc")
        self.assertNotIn("review_decision", fixed_take["maestro_director_requests"][0])
        fixed_sidecar = json.loads(metadata.read_text(encoding="utf-8"))
        self.assertEqual(fixed_sidecar["validation_status"], "pending_human_qc")
        self.assertNotIn("human_review", fixed_sidecar)

    def test_brief_and_pass_recommendation_do_not_grant_human_approval(self):
        self._register_reference("01")
        self._set_candidate("01", b"candidate-one")
        brief = critic_brief(self.root, self.project_id, "01")
        review = submit_verdict(
            self.root,
            self.project_id,
            "01",
            self._verdict(brief, self._scores(), suggested="APPROVE_RECOMMENDED"),
        )
        self.assertEqual(review["recommendation"], "APPROVE_RECOMMENDED")
        self.assertTrue(review["humanApprovalRequired"])
        with self.assertRaisesRegex(ValueError, "já recebeu"):
            submit_verdict(
                self.root,
                self.project_id,
                "01",
                self._verdict(brief, self._scores(), suggested="APPROVE_RECOMMENDED"),
            )

    def test_stops_when_the_second_version_has_only_marginal_improvement(self):
        self._register_reference("01")
        self._set_candidate("01", b"candidate-one")
        first = critic_brief(self.root, self.project_id, "01")
        first_review = submit_verdict(
            self.root,
            self.project_id,
            "01",
            self._verdict(first, self._scores(2), suggested="REGENERATE_RECOMMENDED"),
        )
        self.assertEqual(first_review["recommendation"], "REGENERATE_RECOMMENDED")
        self._set_candidate("01", b"candidate-two")
        second = critic_brief(self.root, self.project_id, "01")
        second_review = submit_verdict(
            self.root,
            self.project_id,
            "01",
            self._verdict(second, self._scores(2), suggested="REGENERATE_RECOMMENDED"),
        )
        self.assertEqual(second_review["recommendation"], "STOP_MARGINAL_IMPROVEMENT")

    def test_reference_cannot_escape_the_project_refs_directory(self):
        outside = self.root / "outside.png"
        outside.write_bytes(b"outside")
        with self.assertRaisesRegex(ValueError, "refs"):
            register_reference(self.root, self.project_id, "01", str(outside))


if __name__ == "__main__":
    unittest.main()
