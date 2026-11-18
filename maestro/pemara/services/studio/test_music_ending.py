import unittest
from music_ending import score_seconds, generation_ending, compact_score
from music_creation import run_yue_auto, validate, YUE_ID

SCORE = 'X:1\nM:4/4\nL:1/8\nQ:1/4=120\nV: Vocal\nV: Ins\nK:C\nV: Vocal\nC8|z8|\nV: Ins\n[CEG]8|Z|'


def audio(truncated=False, seconds=9.5):
    return [{"kind": "audio", "url": "/candidate.flac"},
            {"kind": "text", "node": "10", "text": "tensor(...), {'yue2_truncated': " + str(truncated) + "}"},
            {"kind": "text", "node": "11", "text": str(seconds)}]


class MusicEndingTest(unittest.TestCase):
    def test_full_native_ceiling_is_allowed_and_values_above_it_are_rejected(self):
        validate(YUE_ID, 'heavy guitar rock', 900, instrumental=True, music_action='auto')
        with self.assertRaises(ValueError):
            validate(YUE_ID, 'heavy guitar rock', 901, instrumental=True, music_action='auto')

    def test_simultaneous_voices_chords_and_multimeasure_rests(self):
        self.assertEqual(score_seconds(SCORE), 4)
        self.assertEqual(score_seconds(SCORE.replace('Z|', 'Z3|')), 8)

    def test_tuplets_broken_rhythm_and_fractional_notes(self):
        header = 'X:1\nM:4/4\nL:1/8\nQ:1/4=120\nK:C\n'
        self.assertEqual(score_seconds(header + '(3CDE F>G A/2B/2 c//d//e//f//|'), 1.5)

    def test_unsupported_repeat_or_tempo_change_is_not_silently_miscounted(self):
        for value in (SCORE + '\nQ:1/4=90', SCORE.replace('C8|', '|:C8:|')):
            with self.assertRaises(ValueError): score_seconds(value)

    def test_compaction_preserves_tempo_first_vocal_phrase_and_original_final_chord(self):
        score = ('X:1\nM:4/4\nL:1/8\nQ:1/4=120\nK:C\n% intro\n'
                 'V: Vocal\nZ4|\nV: Ins\nC8|D8|E8|F8|\n% verse\n'
                 'V: Vocal\nC8|D8|\nV: Ins\nZ2|\n% outro\n'
                 'V: Vocal\nZ|\nV: Ins\nC4z4|')
        result = compact_score(score, 7)
        self.assertEqual(score_seconds(result), 6)
        self.assertIn('Q:1/4=120', result)
        self.assertIn('C8|D8|', result)
        self.assertTrue(result.endswith('V: Ins\nC4z4|'))

    def test_end_token_is_required_even_if_audio_fits_time(self):
        self.assertFalse(generation_ending(audio(True), 10)['end_token_reached'])
        self.assertFalse(generation_ending(audio(False, 12), 10)['within_duration'])
        with self.assertRaises(RuntimeError): generation_ending([{'kind': 'audio'}], 10)

    def test_three_minute_and_instrumental_paths_plan_before_audio(self):
        for instrumental in (False, True):
            calls = []
            def queue(graph):
                calls.append(graph)
                return ('score', [{'kind': 'text', 'text': SCORE}]) if '8' in graph else ('audio', audio(False, 175))
            _, _, result = run_yue_auto(prompt='heavy guitar rock', lyrics='[Verse]\nWords',
                instrumental=instrumental, duration=180, seed=10, queue=queue)
            self.assertEqual(len(calls), 2)
            self.assertTrue(result['ending_check']['end_token_reached'])
            self.assertEqual(calls[1]['2']['inputs']['max_duration'], 180)

    def test_overlong_score_is_recomposed_without_audio_cut_or_tempo_edit(self):
        calls = []
        def queue(graph):
            calls.append(graph)
            if len(calls) == 1: return 'long', [{'kind': 'text', 'text': SCORE.replace('C8|z8|', 'Z100|')}]
            if len(calls) == 2: return 'short', [{'kind': 'text', 'text': SCORE}]
            return 'audio', audio()
        _, _, result = run_yue_auto(prompt='piano', lyrics='', instrumental=True, duration=10, seed=1, queue=queue)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result['music_abc'], SCORE)
        self.assertEqual(calls[-1]['2']['inputs']['max_duration'], 10)

    def test_truncated_first_audio_automatically_replans_and_retains_rejected_candidate(self):
        calls = []
        def queue(graph):
            calls.append(graph)
            if '8' in graph: return 'score', [{'kind': 'text', 'text': SCORE}]
            return 'render', audio(len(calls) == 2)
        _, _, result = run_yue_auto(prompt='piano', lyrics='', instrumental=True, duration=10, seed=1, queue=queue)
        self.assertEqual(len(calls), 4)
        self.assertFalse(result['music_attempts'][1]['ending_check']['end_token_reached'])
        self.assertEqual(result['music_attempts'][1]['outputs'][0]['url'], '/candidate.flac')
        self.assertTrue(result['ending_check']['end_token_reached'])

    def test_repeated_truncation_fails_and_never_claims_completion(self):
        def queue(graph):
            return ('score', [{'kind': 'text', 'text': SCORE}]) if '8' in graph else ('render', audio(True))
        with self.assertRaisesRegex(RuntimeError, 'duas tentativas'):
            run_yue_auto(prompt='piano', lyrics='', instrumental=True, duration=10, seed=1, queue=queue)


if __name__ == '__main__': unittest.main()
