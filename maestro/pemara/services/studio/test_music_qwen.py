import unittest
from copy import deepcopy
from music_qwen import validate_plan, creation_caption

PLAN = {'duration_seconds': 30, 'bpm': 120, 'style': 'traditional heavy metal',
        'tracks': {'guitar': {'gainDb': -3, 'density': .8, 'velocityScale': 1, 'role': 'rhythm'}},
        'sections': [{'name': 'verse', 'start': 0, 'end': 30, 'energy': .6,
                      'lead': 'vocals', 'instruments': ['guitar']}]}

class QwenPlanTests(unittest.TestCase):
    def test_valid_plan_retains_manual_duration_and_instruments(self):
        self.assertEqual(validate_plan(PLAN, instruments=('guitar',), duration=30), PLAN)

    def test_duration_instrument_and_timeline_changes_are_blocked(self):
        for field, value in [('duration_seconds', 31), ('tracks', {}), ('bpm', float('nan'))]:
            changed = deepcopy(PLAN); changed[field] = value
            with self.assertRaises(ValueError): validate_plan(changed, instruments=('guitar',), duration=30)
        changed = deepcopy(PLAN); changed['sections'][0]['start'] = 1
        with self.assertRaises(ValueError): validate_plan(changed, instruments=('guitar',), duration=30)

    def test_model_may_choose_duration_within_engine_ceiling(self):
        self.assertEqual(validate_plan(PLAN, instruments=('guitar',), duration=None)['duration_seconds'], 30)
        with self.assertRaises(ValueError): validate_plan(PLAN, instruments=('guitar',), duration=None, max_duration=20)

    def test_conditioning_keeps_the_form_and_blocks_silent_truncation(self):
        text = creation_caption('warm original heavy metal', PLAN)
        self.assertIn('verse 0-30s', text)
        self.assertIn('guitar: rhythm', text)
        with self.assertRaises(ValueError): creation_caption('x' * 1500, PLAN)

