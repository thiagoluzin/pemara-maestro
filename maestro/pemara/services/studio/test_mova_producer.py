import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np

from mova_producer import (
    analyze_mova_take,
    build_ltx_negative_prompt,
    build_ltx_prompt_contract,
    build_mova_effective_prompt,
    enforce_dialogue_duration,
    enforce_mova_policy,
    inspect_mova_final_hold,
    inspect_mova_media,
    inspect_visible_text,
)


class MovaProducerTests(unittest.TestCase):
    def test_ltx_cast_lock_removes_forbidden_people_from_positive_prompt(self):
        contract = build_ltx_prompt_contract(
            "Animate. HUMAN CAST POLICY - The only humans are Pedro and Mariana. "
            "Never add adults, villagers or crowds. END HUMAN CAST POLICY. Keep moving.",
            allowed_humans=["Pedro", "Mariana"],
            duration_seconds=8,
            distinct_story_events=2,
        )

        self.assertNotIn("villagers", contract["prompt"])
        self.assertNotIn("crowds", contract["prompt"])
        self.assertIn("exactly 2 named human subjects", contract["prompt"])
        self.assertIn("one continuous physical body", contract["prompt"])
        self.assertTrue(contract["cast_contract"]["one_physical_instance_per_identity"])
        self.assertTrue(contract["cast_contract"]["closed_inventory"])
        self.assertIn("adult", contract["negative_additions"])
        self.assertIn("same-identity duplicate", contract["negative_additions"])
        self.assertIn("screen-side swap", contract["negative_additions"])
        self.assertIn("subtitle", contract["negative_additions"])
        self.assertEqual(len(contract["motion_blocks"]), 2)
        self.assertTrue(contract["legacy_positive_cast_block_removed"])

        negative = build_ltx_negative_prompt(
            "any human other than exactly Pedro, Mariana, including adults, visible text",
            allowed_humans=["Pedro", "Mariana"],
            additions=contract["negative_additions"],
        )
        self.assertNotIn("Pedro", negative)
        self.assertNotIn("Mariana", negative)
        self.assertIn("extra person", negative)

    def test_ltx_moves_explicit_prohibitions_out_of_positive_conditioning(self):
        contract = build_ltx_prompt_contract(
            "Pedro reacts naturally. No duplicate, clone or extra child. "
            "Do not reverse the screen direction. Continue the camera move.",
            allowed_humans=["Pedro"],
            duration_seconds=6,
        )

        self.assertNotIn("duplicate, clone or extra child", contract["prompt"])
        self.assertNotIn("reverse the screen direction", contract["prompt"])
        self.assertIn("duplicate, clone or extra child", contract["negative_additions"])
        self.assertIn("reverse the screen direction", contract["negative_additions"])
        self.assertEqual(contract["positive_negative_directives_moved"], 2)

    def test_long_dialogue_with_full_arc_gets_six_seconds(self):
        prompt = (
            'Action: Mariana offers a choice and waits. Timing: 0.0-1.1 anticipation; '
            '1.1-3.5 action; 3.5-5.0 reaction; 5.0-6.0 changed final pose. '
            'Only Mariana says: "Pedro, quer parar para escutar de novo ou prefere continuar andando?"'
        )

        plan = analyze_mova_take(prompt)

        self.assertEqual(plan["recommended_duration_seconds"], 6)
        self.assertEqual(plan["recommended_frames"], 145)
        self.assertTrue(plan["dialogue"]["detected"])
        self.assertFalse(plan["upscale_allowed"])
        self.assertEqual(plan["voice_contract"]["required_locale"], "pt-BR")
        self.assertTrue(plan["voice_contract"]["human_pt_br_listening_required"])
        self.assertFalse(plan["voice_contract"]["delivery_allowed"])

    def test_action_and_reaction_without_dialogue_gets_five_seconds(self):
        plan = analyze_mova_take(
            "A personagem vira, oferece o objeto e espera. Pedro reage com o olhar antes do corte."
        )

        self.assertEqual(plan["recommended_duration_seconds"], 5)
        self.assertEqual(plan["recommended_frames"], 121)

    def test_short_gesture_gets_four_seconds(self):
        plan = analyze_mova_take("Um gesto simples revela o bilhete e termina no corte.")

        self.assertEqual(plan["recommended_duration_seconds"], 4)
        self.assertEqual(plan["recommended_frames"], 97)

    def test_dialogue_gate_rejects_too_few_frames(self):
        plan = analyze_mova_take(
            'Mariana says: "Pedro, quer parar para escutar de novo ou prefere continuar andando?"'
        )

        with self.assertRaisesRegex(ValueError, "Produtor MOVA bloqueou"):
            enforce_dialogue_duration(plan, frames=97, fps=24)

    def test_spoken_word_andando_does_not_create_locomotion_instruction(self):
        plan = analyze_mova_take(
            'Mariana fala em portugues brasileiro: "Pedro, prefere continuar andando?"'
        )

        self.assertEqual(plan["motion_contract"]["locomotion_directives_detected"], [])
        self.assertFalse(plan["motion_contract"]["locomotion_overridden"])

    def test_dialogue_locomotion_is_overridden_by_permanent_contract(self):
        prompt = (
            'Pedro takes one small step toward the camera. Mariana says in Brazilian Portuguese: '
            '"Pedro, prefere continuar andando?"'
        )
        plan = analyze_mova_take(prompt)
        effective = build_mova_effective_prompt(prompt, plan)

        self.assertTrue(plan["motion_contract"]["locomotion_overridden"])
        self.assertFalse(plan["motion_contract"]["locomotion_allowed"])
        self.assertIn("keeps both feet planted", effective)
        self.assertIn("No walking, step, foot lift", effective)
        self.assertIn("Brazilian Portuguese from Brazil (pt-BR)", effective)

    def test_affirmative_pt_pt_request_is_blocked(self):
        plan = analyze_mova_take(
            'Mariana fala em portugues de Portugal: "Pedro, vamos continuar?"'
        )

        with self.assertRaisesRegex(ValueError, "pt-PT"):
            enforce_mova_policy(plan)

    def test_pt_pt_in_forbidden_list_is_not_mistaken_for_request(self):
        plan = analyze_mova_take(
            'Only Mariana says in Brazilian Portuguese: "Pedro, vamos continuar?"\n'
            'European Portuguese and a Portugal accent are forbidden.'
        )

        enforce_mova_policy(plan)
        self.assertFalse(plan["voice_contract"]["explicit_forbidden_locale_request"])

    @patch("mova_producer.subprocess.run")
    def test_final_hold_qc_rejects_excess_motion(self, run):
        run.return_value = SimpleNamespace(
            stdout="\n".join([
                "lavfi.signalstats.YAVG=2.5",
                "lavfi.signalstats.YAVG=2.8",
                "lavfi.signalstats.YAVG=2.6",
            ])
        )

        qc = inspect_mova_final_hold(
            Path("candidate.mp4"),
            ffmpeg="ffmpeg",
            duration_seconds=6,
        )

        self.assertEqual(qc["status"], "AUTO_REJECTED")
        self.assertFalse(qc["passed"])

    @patch("mova_producer.subprocess.run")
    def test_media_qc_accepts_synchronized_safe_audio(self, run):
        run.side_effect = [
            SimpleNamespace(
                stdout=(
                    '{"streams": ['
                    '{"codec_type": "video", "codec_name": "h264", "r_frame_rate": "24/1"},'
                    '{"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2}'
                    '], "format": {"duration": "6.041"}}'
                )
            ),
            SimpleNamespace(stderr="I: -22.2 LUFS\nPeak: -6.8 dBFS\n"),
        ]

        qc = inspect_mova_media(
            Path("candidate.mp4"),
            ffmpeg="ffmpeg",
            expected_duration_seconds=6.0,
        )

        self.assertEqual(qc["status"], "PASS")
        self.assertTrue(qc["passed"])
        self.assertEqual(qc["audio_codec"], "aac")

    @patch("mova_producer.subprocess.run")
    def test_visual_only_qc_does_not_reject_missing_audio(self, run):
        run.return_value = SimpleNamespace(
            stdout=(
                '{"streams": ['
                '{"codec_type": "video", "codec_name": "h264", "r_frame_rate": "24/1"}'
                '], "format": {"duration": "8.000"}}'
            )
        )

        qc = inspect_mova_media(
            Path("candidate.mp4"),
            ffmpeg="ffmpeg",
            expected_duration_seconds=8.0,
            require_audio=False,
            enforce_loudness=False,
        )

        self.assertEqual(qc["status"], "PASS")
        self.assertTrue(qc["visual_passed"])
        self.assertIsNone(qc["audio_passed"])
        self.assertIn("AUDIO_DEFERRED_TO_SEPARATE_PASS", qc["warnings"])
        run.assert_called_once()

    def test_visible_text_gate_rejects_persistent_burned_caption(self):
        with tempfile.TemporaryDirectory() as temp_name:
            video = Path(temp_name) / "caption.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 12, (320, 180))
            self.assertTrue(writer.isOpened())
            for index in range(12):
                frame = np.full((180, 320, 3), (70 + index, 120, 155), dtype=np.uint8)
                cv2.putText(frame, "BAD CAPTION", (45, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                writer.write(frame)
            writer.release()

            qc = inspect_visible_text(video, occupancy=0.5, max_glyph_pixels=50)

            self.assertEqual(qc["status"], "AUTO_REJECTED")
            self.assertIn("PERSISTENT_VISIBLE_GLYPHS", qc["failures"])


if __name__ == "__main__":
    unittest.main()
