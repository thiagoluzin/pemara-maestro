"""Regression tests for failed-candidate recommendations and export overshoot."""
import unittest
from pathlib import Path
from unittest.mock import patch
from music_ai_audio import qc_report


class MusicQualityGatesTests(unittest.TestCase):


    def test_true_peak_is_a_gate_even_when_samples_have_headroom(self):
        samples = {'durationSeconds': 180, 'sampleRate': 48000, 'channels': 2,
                   'clippingSampleCount': 0, 'samplePeakDbfs': -1.0}
        with patch('music_ai_audio.subprocess.run') as process, \
             patch('music_ai_audio.sample_metrics', return_value=samples), \
             patch('music_ai_audio.loudness_metrics') as loudness:
            process.return_value.returncode = 0
            for peak, expected in ((0.4, False), (None, False), (-1.1, True)):
                loudness.return_value = {'integratedLufs': -13, 'truePeakDbfs': peak}
                self.assertEqual(qc_report(Path('test.wav'), 'ffmpeg', 180)['technicalPass'], expected)

    def test_zero_sample_peak_does_not_become_minus_99(self):
        samples = {'durationSeconds': 180, 'sampleRate': 48000, 'channels': 2,
                   'clippingSampleCount': 0, 'samplePeakDbfs': 0.0}
        with patch('music_ai_audio.subprocess.run') as process, \
             patch('music_ai_audio.sample_metrics', return_value=samples), \
             patch('music_ai_audio.loudness_metrics', return_value={
                 'integratedLufs': -13, 'truePeakDbfs': -1.1}):
            process.return_value.returncode = 0
            self.assertFalse(qc_report(Path('test.wav'), 'ffmpeg', 180)['technicalPass'])
