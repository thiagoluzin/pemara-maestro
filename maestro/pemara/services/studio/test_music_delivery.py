import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from music_delivery import finish_audio
from music_ai_audio import MusicAiAudioError, sha256_file

class MusicDeliveryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg unavailable')
    def test_encoded_file_is_checked_and_native_is_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); source = root / 'source.wav'
            wave = .8 * np.sin(2 * np.pi * 440 * np.arange(48000 * 2) / 48000)
            sf.write(source, np.column_stack([wave, wave]), 48000, subtype='FLOAT')
            before = sha256_file(source)
            result = finish_audio(source, root / 'delivery', shutil.which('ffmpeg'))
            self.assertTrue(result['technicalPass'])
            self.assertLessEqual(result['attempts'][-1]['previewQc']['truePeakDbfs'], -1)
            self.assertEqual(before, sha256_file(source))

    def test_attenuation_does_not_hide_already_clipped_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); source = root / 'clipped.wav'
            sf.write(source, np.ones((480, 2)), 48000, subtype='FLOAT')
            with self.assertRaises(MusicAiAudioError): finish_audio(source, root / 'out', 'ffmpeg')
            self.assertTrue((root / 'out/music_delivery.json').is_file())
