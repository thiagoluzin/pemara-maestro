from pathlib import Path
import re
import unittest

from h3_prompt_writing import (
    OFFICIAL_COMMIT,
    compile_base_prompt,
    compile_ref_prompt,
    detect_base_mode,
    official_skill_integrity,
    normalize_quoted_speech,
)


class H3PromptWritingTests(unittest.TestCase):
    def test_owner_photo_speech_request_contains_only_literal_dialogue(self):
        document = compile_base_prompt(
            'O PERSONAGEM DA FALA DEVE TER A SEGUINTE FALA: "EU SOU O THIAGO"',
            mode="I2VA", duration_seconds=6,
        )
        self.assertEqual(re.findall(r"<d>\[Portuguese\] (.*?)</d>", document.prompt),
                         ["EU SOU O THIAGO"])
        self.assertNotIn("DEVE TER A SEGUINTE FALA", document.prompt)
        self.assertIn("The character (S1) says:", document.prompt)
        self.assertIn("<Picture 1>", document.prompt)
        self.assertEqual(compile_base_prompt(document.prompt, mode="I2VA",
                                            duration_seconds=6).prompt, document.prompt)

    def test_speech_preserves_literal_spacing_accents_and_punctuation(self):
        for opening, closing in [('"', '"'), ('“', '”'), ('«', '»'), ("'", "'"), ('‘', '’')]:
            with self.subTest(quotes=opening):
                document = compile_base_prompt(
                    f'O personagem diz: {opening}Eu  sou o Thiago!\nTudo bem?{closing}',
                    mode="I2VA", duration_seconds=6,
                )
                self.assertIn("<d>[Portuguese] Eu  sou o Thiago!\nTudo bem?</d>", document.prompt)
        self.assertEqual(normalize_quoted_speech("Fala: 'Olá, Thiago!'"),
                         "Fala: <d>[Portuguese] Olá, Thiago!</d>")

    def test_speech_keeps_surrounding_action_and_named_subject(self):
        value = 'Maria olha para a câmera e diz: "Eu sou o Thiago". Depois acena.'
        self.assertEqual(normalize_quoted_speech(value),
                         'Maria olha para a câmera e diz: <d>[Portuguese] Eu sou o Thiago</d>. Depois acena.')

    def test_all_quotes_are_speech_without_context_exceptions(self):
        cases = [
            '"EU SOU O THIAGO"',
            'Ele sorri. "EU SOU O THIAGO" Depois acena.',
            'A placa diz: "EU SOU O THIAGO".',
            'O cartaz tem o texto "EU SOU O THIAGO".',
            'O personagem não diz: "EU SOU O THIAGO".',
            'Não faça o personagem falar: "EU SOU O THIAGO".',
            'A narração diz: "EU SOU O THIAGO".',
            'O homem em voz em off diz: "EU SOU O THIAGO".',
        ]
        for value in cases:
            with self.subTest(value=value):
                self.assertEqual(re.findall(r"<d>\[Portuguese\] (.*?)</d>",
                                            normalize_quoted_speech(value)), ["EU SOU O THIAGO"])

    def test_multiple_quotes_preserve_order_and_directions(self):
        value = 'Ele sorri. "Oi!" Depois acena. “Eu sou o Thiago.”'
        result = normalize_quoted_speech(value)
        self.assertEqual(result, 'Ele sorri. <d>[Portuguese] Oi!</d> Depois acena. <d>[Portuguese] Eu sou o Thiago.</d>')
        self.assertEqual(normalize_quoted_speech(result), result)

    def test_unquoted_text_and_authored_dialogue_are_unchanged(self):
        cases = [
            'Ele sorri e acena.',
            "The character doesn't move.",
            'O personagem diz: "".',
            'O personagem diz: "Sem fechar aspas.',
            'The man (S1) says: <d>[Portuguese] Eu sou o Thiago.</d>',
        ]
        for value in cases:
            with self.subTest(value=value):
                self.assertEqual(normalize_quoted_speech(value), value)

    def test_new_quotes_next_to_authored_dialogue_are_converted_without_nesting(self):
        authored = '(S1) says: <d>[Portuguese] Ele disse "oi".</d>'
        self.assertEqual(normalize_quoted_speech(authored + ' Depois "Tchau!"'),
                         authored + ' Depois <d>[Portuguese] Tchau!</d>')

    def test_detects_all_base_modes(self):
        self.assertEqual(detect_base_mode(has_first_frame=False, has_last_frame=False), "T2VA")
        self.assertEqual(detect_base_mode(has_first_frame=True, has_last_frame=False), "I2VA")
        self.assertEqual(detect_base_mode(has_first_frame=True, has_last_frame=True), "FL2VA")
        self.assertEqual(detect_base_mode(has_first_frame=False, has_last_frame=True), "L2VA")

    def test_fl2va_uses_official_alignment_and_section_order(self):
        document = compile_base_prompt(
            "Live-action, one continuous physical dodge reaches the supplied ending.",
            mode="FL2VA",
            duration_seconds=5.125,
            overall_soundscape="N/A",
            non_diegetic_music="N/A",
        )
        self.assertTrue(document.prompt.startswith("How the reference pictures align"))
        self.assertIn("Picture 2 (from Shot 1) aligns with the 5.13-second mark", document.prompt)
        self.assertLess(
            document.prompt.index("integrated_multimodal_description:"),
            document.prompt.index("overall_soundscape:"),
        )
        self.assertLess(
            document.prompt.index("overall_soundscape:"),
            document.prompt.index("non_diegetic_music:"),
        )

    def test_already_compiled_prompt_is_not_nested(self):
        first = compile_base_prompt(
            "Live-action, continuous motion.",
            mode="I2VA",
            duration_seconds=6,
        )
        second = compile_base_prompt(first.prompt, mode="I2VA", duration_seconds=6)
        self.assertEqual(second.prompt, first.prompt)

    def test_ref2va_rejects_unresolved_labels(self):
        with self.assertRaisesRegex(ValueError, "labels sem definicao"):
            compile_ref_prompt(
                subject_definitions="<Subject 1> is the fighter in <Picture 1>.",
                summary="[reference generation] <Subject 2> fights.",
                retention_analysis="<Subject 1>: fully_preserved - identity remains.",
                detailed_description="[Shot 1] <Subject 1> enters.",
                overall_soundscape="Wind and impacts.",
                non_diegetic_music="N/A",
                duration_seconds=5,
            )

    def test_ref2va_emits_six_sections(self):
        document = compile_ref_prompt(
            subject_definitions="<Subject 1> is the fighter in <Picture 1>.",
            summary="[reference generation] <Subject 1> fights.",
            retention_analysis="<Subject 1>: fully_preserved - identity remains.",
            detailed_description="Live-action. [Shot 1] <Subject 1> enters.",
            overall_soundscape="Wind and impacts.",
            non_diegetic_music="N/A",
            duration_seconds=5,
        )
        self.assertEqual(document.mode, "REF2VA")
        self.assertIn("detailed_description:", document.prompt)

    def test_official_skill_is_pinned_and_intact(self):
        workspace_root = Path(__file__).resolve().parents[2]
        status = official_skill_integrity(workspace_root)
        self.assertTrue(status["ok"])
        self.assertEqual(status["commit"], OFFICIAL_COMMIT)


if __name__ == "__main__":
    unittest.main()
