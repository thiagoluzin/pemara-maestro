import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from music_ai_audio import sha256_file
from music_listening import prepare_comparison

@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
class ListeningComparisonTests(unittest.TestCase):
    def test_volume_matches_without_rewriting_sources_or_timing(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); source = root / 'source.wav'; candidate = root / 'candidate.wav'
            wave = np.sin(2 * np.pi * 440 * np.arange(48000 * 3) / 48000)
            sf.write(source, np.column_stack([wave * .3, wave * .25]), 48000, subtype='PCM_24')
            sf.write(candidate, np.column_stack([wave * .7, wave * .6]), 48000, subtype='PCM_24')
            before = [sha256_file(source), sha256_file(candidate)]
            result = prepare_comparison(source, candidate, root / 'comparison', shutil.which('ffmpeg'))
            a, b = [result['receipt']['files'][key] for key in ('reference', 'candidate')]
            self.assertLessEqual(abs(a['qc']['integratedLufs'] - b['qc']['integratedLufs']), .4)
            self.assertEqual([sha256_file(source), sha256_file(candidate)], before)
            self.assertEqual(a['qc']['durationSeconds'], 3)
            self.assertTrue(a['qc']['technicalPass'] and b['qc']['technicalPass'])
