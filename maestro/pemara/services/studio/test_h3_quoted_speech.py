"""Exercise photo animation up to the queue boundary without submitting a job."""
import re
import unittest
from unittest.mock import patch

import main
from h3_acceleration import validate_spectrum


class QueueBoundaryReached(Exception):
    pass


class QuotedSpeechIntegrationTest(unittest.TestCase):
    def test_photo_animation_passes_only_requested_words_as_dialogue(self):
        for audio in (True, False):
            with self.subTest(native_audio=audio):
                captured = {}

                def capture(graph, **kwargs):
                    captured.update(graph)
                    raise QueueBoundaryReached()

                with (
                    patch.object(main, "_require_authorized_video_engine"),
                    patch.object(main, "_comfy_online", return_value=(True, {})),
                    patch.object(main, "_comfy_request", side_effect=AssertionError("No HTTP in this test")),
                    patch.object(main, "_model_files", return_value=[]),
                    patch.object(main, "_video_model_files", return_value=[main.MINIMAX_H3_MODEL_NAME]),
                    patch.object(main, "_save_comfy_input_image", return_value="speech_reference.png"),
                    patch.object(main, "_queue_comfy_workflow", side_effect=capture),
                    self.assertRaises(QueueBoundaryReached),
                ):
                    main._run_generative(
                        prompt='Ele sorri. "EU SOU O THIAGO" Depois acena. "TUDO BEM?"',
                        mode="video", model=main.MINIMAX_H3_MODEL_NAME,
                        negative="", lora="", lora_strength=0.0,
                        width=1088, height=608, steps=10, guidance=1.0,
                        seed=42, frames=243, fps=24.0,
                        h3_quality_profile="h3_production",
                        base_image_bytes=b"test-reference-not-rendered",
                        base_image_name="speech_reference.png",
                        enable_minimax_h3_native_audio=audio,
                    )
                prompt = captured["6"]["inputs"]["prompt"]
                self.assertEqual(re.findall(r"<d>\[Portuguese\] (.*?)</d>", prompt),
                                 ["EU SOU O THIAGO", "TUDO BEM?"])
                self.assertNotIn("DEVE TER A SEGUINTE FALA", prompt)
                self.assertEqual(captured["5"]["inputs"]["image"], "speech_reference.png")
                self.assertEqual("audio" in captured["15"]["inputs"], audio)
                self.assertTrue(validate_spectrum(captured))


if __name__ == "__main__":
    unittest.main()
