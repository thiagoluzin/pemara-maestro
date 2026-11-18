"""Optional model-chosen duration must differ from a 900-second target."""
import io
import json
import unittest
from unittest.mock import patch
import music_creation as music
from music_writer import write_song
with patch('urllib.request.urlopen', side_effect=AssertionError('No live calls in tests')):
    import main
from fastapi.testclient import TestClient

SONG = {'title': 'Nova manhã', 'caption': 'heavy guitar rock, expressive male vocals',
        'lyrics': '[Verse]\nNa noite eu sigo em frente\n[Chorus]\nO novo dia chega',
        'instrumental': False, 'vocal_language': 'pt'}
from test_music_qwen import PLAN
SONG['production_plan'] = PLAN
SCORE = 'X:1\nM:4/4\nL:1/8\nQ:1/4=120\nK:C\nV: Vocal\nC8|z8|\nV: Ins\nZ2|'


class MusicDurationChoiceTest(unittest.TestCase):
    def test_form_and_persistent_spec_keep_explicit_choice(self):
        with patch.object(main, '_is_internal_request', return_value=True), \
             patch.object(main, '_start_generative_job', return_value='duration-choice') as start:
            response = TestClient(main.app).post('/api/generative/job', data={
                'mode': 'music', 'provider': music.YUE_ID, 'prompt': 'Rock sobre o amanhecer',
                'duration': '30', 'music_duration_auto': 'true'})
        self.assertEqual(response.status_code, 200)
        spec = main._normalize_generative_job_spec(start.call_args.args[0])
        self.assertIs(spec['music_duration_auto'], True)
        self.assertEqual(spec['duration'], 900)
        # Retry normalization preserves the choice; legacy/manual requests keep their time.
        self.assertTrue(main._normalize_generative_job_spec(spec)['music_duration_auto'])
        manual = main._normalize_generative_job_spec({**spec, 'music_duration_auto': False, 'duration': 180})
        self.assertEqual(manual['duration'], 180)

    def test_incompatible_engines_and_ambiguous_booleans_are_rejected(self):
        base = dict(mode='music', provider=music.YUE_ID, prompt='Rock sobre o amanhecer', duration=30,
                    music_duration_auto=True)
        for extra in ({'provider': music.ACE_ID}, {'mode': 'sfx'}, {'music_duration_auto': 'false'}):
            with self.assertRaises(ValueError): main._normalize_generative_job_spec({**base, **extra})

    def test_score_and_audio_receive_ceiling_but_no_fixed_length_instruction(self):
        calls = []
        def queue(graph):
            calls.append(graph)
            if '8' in graph: return 'score', [{'kind': 'text', 'text': SCORE}]
            return 'render', [{'kind': 'audio', 'url': '/test.flac'},
                {'kind': 'text', 'node': '10', 'text': "{'yue2_truncated': False}"},
                {'kind': 'text', 'node': '11', 'text': '4'}]
        _, _, result = music.run_yue_auto(prompt=SONG['caption'], lyrics=SONG['lyrics'],
            instrumental=False, duration=30, seed=2, queue=queue, music_duration_auto=True)
        self.assertEqual(calls[-1]['2']['inputs']['max_duration'], 900)
        for style in (calls[0]['8']['inputs']['style'], calls[-1]['2']['inputs']['style']):
            self.assertIn('no required target duration', style)
            self.assertNotIn('within 892 seconds', style)
        self.assertEqual(result['music_abc'], SCORE)
        self.assertIsNone(result['requested_duration_seconds'])
        self.assertEqual(result['duration_ceiling_seconds'], 900)
        self.assertTrue(result['music_duration_auto'])

    def test_unchecked_workflow_keeps_manual_time(self):
        graph = music.yue_workflow(prompt='heavy guitar rock', lyrics=SONG['lyrics'], instrumental=False,
            duration=180, seed=1, music_action='auto', music_abc=SCORE, prefix='test')
        self.assertEqual(graph['2']['inputs']['max_duration'], 180)
        self.assertIn('target duration 180 seconds', graph['2']['inputs']['style'])

    def test_writer_has_freedom_without_a_fifteen_minute_lyric_target(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self): yield json.dumps({'response': json.dumps(SONG), 'done': True}).encode()
        state = {'models': [{'name': 'qwen3.8-27b-uncensored-yarn-524k:latest', 'size': 2000, 'size_vram': 2000}]}
        with patch('music_writer.urllib.request.urlopen', side_effect=[Response(),
                   io.BytesIO(json.dumps(state).encode()), io.BytesIO(b'{"models": []}')]) as call:
            write_song('Rock sobre o amanhecer', None)
        payload = json.loads(call.call_args_list[0].args[0].data)
        direction = json.loads(payload['prompt'])
        self.assertIsNone(direction['duration_seconds'])
        self.assertEqual(direction['duration_mode'], 'model_choice')
        self.assertEqual(direction['ending_budget'], {'limit_seconds': 900})
        self.assertNotIn('Fit the lyrics to the requested duration', payload['system'])

    def test_backend_passes_freedom_to_writer_and_composer(self):
        def schema(path, **kw):
            if path == '/system_stats': return {'devices': [{'vram_free': 30 * 1024**3}]}
            return {}
        metadata = {'music_abc': SCORE, 'music_duration_auto': True}
        with patch('music_writer.write_song', return_value=dict(SONG)) as writer, \
             patch.object(main, '_comfy_request', side_effect=schema), \
             patch.object(main, '_prepare_comfy_gpu_for_mova'), \
             patch.object(music, 'run_yue_auto', return_value=('render', [{'kind': 'audio', 'url': '/test.flac'}], metadata)) as composer, \
             patch.object(main, '_finish_simple_music', side_effect=lambda result, song, **kw: result):
            main._run_audio_generative(prompt='Rock sobre o amanhecer', mode='music', provider=music.YUE_ID,
                negative='', duration=30, seed=1, prompt_influence=.5, loop=False,
                music_action='auto', music_instrumental=False, music_duration_auto=True)
        self.assertIsNone(writer.call_args.args[1])
        self.assertEqual(composer.call_args.kwargs['duration'], 30)
        self.assertIs(composer.call_args.kwargs['music_duration_auto'], False)
        self.assertEqual(composer.call_args.kwargs['production_plan'], PLAN)


if __name__ == '__main__': unittest.main()
