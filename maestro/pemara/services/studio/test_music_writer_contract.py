"""Regression: five-minute vocal metal cannot fail on vocal/unknown track keys."""
from copy import deepcopy
import json
import threading
import unittest
from unittest.mock import patch
from music_qwen import CREATION_INSTRUMENTS, plan_schema, validate_plan
from music_writer import SCHEMA, write_song

PROMPT = ('Criar uma música estilo iron Maiden anos 1980 baseado no heavy metal britânico '
          'da época com duração de 5 minutos. Bateria e baixos muito forte e vocais rasgados '
          'além dos solos de guitarra e letra em inglês')
TRACK = {'gainDb': -3, 'density': .8, 'velocityScale': 1, 'role': 'original metal performance'}
SONG = {'title': 'Original Test Song', 'caption': 'British heavy metal, driving bass and drums, gritty male vocals',
        'lyrics': '[Verse]\nOriginal words across the night\n[Chorus]\nWe follow our own light',
        'vocal_language': 'en', 'instrumental': False,
        'production_plan': {'duration_seconds': 300, 'bpm': 140, 'style': '1980s British heavy metal',
            'tracks': {name: deepcopy(TRACK) for name in ('guitar', 'bass', 'drums', 'vocals')},
            'sections': [{'name': 'Verse', 'start': 0, 'end': 150, 'energy': .5,
                          'lead': 'vocals', 'instruments': ['guitar', 'bass', 'drums', 'vocals']},
                         {'name': 'Chorus and final decay', 'start': 150, 'end': 300, 'energy': .9,
                          'lead': 'guitar', 'instruments': ['guitar', 'bass', 'drums', 'vocals']}]}}
METADATA = {'writer_model': 'qwen-local', 'writer_unloaded': True}

class WriterContractTests(unittest.TestCase):
    def test_decoder_vocabulary_is_closed_and_matches_validation(self):
        schema = SCHEMA['properties']['production_plan']
        tracks = schema['properties']['tracks']
        self.assertFalse(tracks['additionalProperties'])
        self.assertEqual(set(tracks['properties']), set(CREATION_INSTRUMENTS))
        self.assertEqual(tracks['minProperties'], 1)
        section = schema['properties']['sections']['items']['properties']
        self.assertEqual(set(section['instruments']['items']['enum']), set(CREATION_INSTRUMENTS))
        locked = plan_schema(('guitar', 'bass'), require_all=True)
        self.assertEqual(locked['properties']['tracks']['required'], ['guitar', 'bass'])
        self.assertNotIn('vocals', locked['properties']['tracks']['properties'])

    def test_five_minute_vocal_plan_accepts_vocals_as_creation_track(self):
        with patch('music_writer.request_json', return_value=(deepcopy(SONG), METADATA)) as request:
            song = write_song(PROMPT, 300)
        self.assertEqual(song['duration_seconds'], 300)
        self.assertEqual(song['vocal_language'], 'en')
        self.assertFalse(song['instrumental'])
        self.assertIn('vocals', song['production_plan']['tracks'])
        self.assertEqual(song['writer_validation_attempts'], 1)
        duration = request.call_args.args[0]['format']['properties']['production_plan']['properties']['duration_seconds']
        self.assertEqual(duration['const'], 300)

    def test_energy_bounds_are_visible_in_schema_prompt_and_repair(self):
        failed = deepcopy(SONG); failed['production_plan']['sections'][0]['energy'] = 80
        with patch('music_writer.request_json', side_effect=[(failed, METADATA), (deepcopy(SONG), METADATA)]) as request:
            result = write_song(PROMPT, 300)
        first, second = [call.args[0] for call in request.call_args_list]
        energy = first['format']['properties']['production_plan']['properties']['sections']['items']['properties']['energy']
        self.assertEqual((energy['minimum'], energy['maximum']), (0, 1))
        self.assertIn('NEVER a percentage', first['system'])
        self.assertIn('recebido 80', second['prompt'])
        self.assertEqual(result['writer_validation_attempts'], 2)

    def test_invalid_or_empty_tracks_are_corrected_once_by_same_local_model(self):
        for bad_tracks in ({}, {'electric_guitar': TRACK}, {'lead_guitar': TRACK, 'vocal': TRACK}):
            failed = deepcopy(SONG); failed['production_plan']['tracks'] = bad_tracks
            with patch('music_writer.request_json', side_effect=[(failed, METADATA), (deepcopy(SONG), METADATA)]) as request:
                result = write_song(PROMPT, 300)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(result['writer_validation_attempts'], 2)
            first, second = [call.args[0] for call in request.call_args_list]
            self.assertEqual(first['model'], second['model'])
            self.assertTrue(second['prompt'].startswith(first['prompt']))
            self.assertEqual(json.loads(first['prompt'])['idea'], PROMPT)
            self.assertLess(second['options']['temperature'], first['options']['temperature'])

    def test_failed_repair_is_bounded_and_does_not_drop_validation(self):
        failed = deepcopy(SONG); failed['production_plan']['tracks'] = {}
        with patch('music_writer.request_json', return_value=(failed, METADATA)) as request:
            with self.assertRaisesRegex(ValueError, 'apos uma correcao automatica'):
                write_song(PROMPT, 300)
        self.assertEqual(request.call_count, 2)

    def test_repair_requires_tracks_referenced_by_sections(self):
        failed = deepcopy(SONG)
        del failed['production_plan']['tracks']['guitar']
        del failed['production_plan']['tracks']['bass']
        with patch('music_writer.request_json', side_effect=[(failed, METADATA), (deepcopy(SONG), METADATA)]) as request:
            result = write_song(PROMPT, 300)
        repaired = request.call_args_list[1].args[0]['format']['properties']['production_plan']['properties']['tracks']
        self.assertEqual(set(repaired['required']), {'guitar', 'bass', 'drums', 'vocals'})
        self.assertEqual(set(repaired['properties']), set(repaired['required']))
        self.assertEqual(set(result['production_plan']['tracks']), set(repaired['required']))

    def test_repair_retains_provided_lyrics_bpm_and_manual_duration(self):
        failed = deepcopy(SONG); failed['production_plan']['duration_seconds'] = 290
        with patch('music_writer.request_json', side_effect=[(failed, METADATA), (deepcopy(SONG), METADATA)]) as request:
            result = write_song(PROMPT, 300, provided_lyrics=SONG['lyrics'], provided_bpm=140)
        self.assertEqual(result['lyrics'], SONG['lyrics'])
        self.assertEqual(result['production_plan']['bpm'], 140)
        self.assertEqual(result['duration_seconds'], 300)
        for call in request.call_args_list:
            initial = json.loads(call.args[0]['prompt'].split('\n')[0])
            self.assertEqual(initial['supplied_lyrics'], SONG['lyrics'])
            self.assertEqual(initial['forced_bpm'], 140)

    def test_instrumental_plan_cannot_add_vocals(self):
        failed = deepcopy(SONG); failed['instrumental'] = True
        with patch('music_writer.request_json', return_value=(failed, METADATA)):
            with self.assertRaisesRegex(ValueError, 'incluiu canto'):
                write_song('original instrumental metal', 300, instrumental=True)

    def test_non_string_section_members_are_validation_errors(self):
        plan = deepcopy(SONG['production_plan'])
        for members in ([{'bad': 'guitar'}], ['guitar', 'guitar']):
            plan['sections'][0]['instruments'] = members
            with self.assertRaises(ValueError):
                validate_plan(plan, instruments=tuple(plan['tracks']), duration=300)

    def test_service_failures_are_not_retried_as_bad_plans(self):
        with patch('music_writer.request_json', side_effect=RuntimeError('service unavailable')) as request:
            with self.assertRaisesRegex(RuntimeError, 'service unavailable'):
                write_song(PROMPT, 300)
        self.assertEqual(request.call_count, 1)

    def test_incomplete_json_gets_one_repair_attempt(self):
        with patch('music_writer.request_json', side_effect=[ValueError('invalid JSON'),
                   (deepcopy(SONG), METADATA)]) as request:
            result = write_song(PROMPT, 300)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(result['writer_validation_attempts'], 2)

    def test_cancellation_does_not_start_planning(self):
        event = threading.Event(); event.set()
        with patch('music_writer.request_json') as request:
            with self.assertRaisesRegex(RuntimeError, 'cancelada'):
                write_song(PROMPT, 300, cancel_event=event)
        request.assert_not_called()
