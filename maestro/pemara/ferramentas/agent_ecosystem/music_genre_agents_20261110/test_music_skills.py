"""Offline regression checks with non-musical arrays; no GPU, API, music or publication."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

ROOT = Path('E:/Pemara/.agents/skills')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ALBUM = load('album_audit', ROOT/'pemara-music-album-diversity/scripts/audit_album.py')
SIGNAL = load('signal_screen', ROOT/'pemara-music-listening-qc/scripts/screen_audio.py')


def track(identifier, **changes):
    result = {'id': identifier, 'title': 'Draft '+identifier,
              'lyrics': 'The night watch carries a sealed message through the city gate',
              'hook': 'Open the gate',
              'arrangement': {'riff_signature': 'E2 G2 F2 E2', 'rhythm_signature': 'short short long',
                              'form': ['verse', 'chorus', 'verse', 'bridge', 'chorus'],
                              'vocal_phrasing': 'short answered phrases'}}
    result.update(changes)
    return result


class AlbumTests(unittest.TestCase):
    def test_renamed_seed_changes_do_not_hide_copied_song(self):
        a, b = track('a'), track('b', title='Another title', seed=9924)
        report = ALBUM.audit({'tracks': [a,b]})
        self.assertIn('EXACT_LYRICS', report['review_pairs'][0]['reasons'])
        self.assertIn('EXACT_HOOK', report['review_pairs'][0]['reasons'])

    def test_new_lyrics_do_not_hide_reused_hook_and_riff(self):
        b = track('b', lyrics='A child sees ships disappear beneath a winter moon')
        self.assertEqual(ALBUM.audit({'tracks':[track('a'),b]})['status'], 'REVIEW_REQUIRED')

    def test_shared_simple_form_and_band_voice_do_not_alone_reject(self):
        b = track('b', lyrics='The river rises over silent houses', hook='Carry the boats')
        b['arrangement'].update(riff_signature='A2 C3 D1', rhythm_signature='long short short', vocal_phrasing='held then clipped')
        result = ALBUM.audit({'tracks':[track('a'),b]})
        self.assertEqual(result['status'], 'NO_PLAN_FLAGS')
        self.assertFalse(result['artistic_approval'])

    def test_missing_evidence_cannot_pass(self):
        result = ALBUM.audit({'tracks':[{'id':'a','title':'Title only'}]})
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(result['missing_evidence'])

    def test_accidentals_and_chords_are_not_erased(self):
        self.assertNotEqual(ALBUM.signature('[E,,B,,]2 ^F,,2'), ALBUM.signature('[F,,C,]2 F,,2'))

    def test_duplicate_ids_are_invalid(self):
        with self.assertRaises(ValueError):
            ALBUM.audit({'tracks':[track('a'),track('a')]})

    def test_cli_writes_report_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'plan.json';output=Path(folder)/'comparison.json'
            source.write_text(json.dumps({'tracks':[track('a'),track('b')]}),encoding='utf-8')
            before=source.read_bytes()
            subprocess.run([sys.executable,str(ROOT/'pemara-music-album-diversity/scripts/audit_album.py'),str(source),'--out',str(output)],check=True,capture_output=True)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(len(json.loads(output.read_text())['review_pairs']),1)


class SignalTests(unittest.TestCase):
    def test_codec_noise_tail_is_detected_despite_high_global_rms(self):
        blocks=[np.full((100,2),.2) for _ in range(10)]+[np.full((100,2),.00007) for _ in range(8)]
        result=SIGNAL.screen_blocks(blocks,100)
        self.assertEqual(result['near_silence_intervals'],[{'start':10,'end':18}])
        self.assertEqual(result['screening_status'],'REVIEW_REQUIRED')
        self.assertFalse(result['audio_listened'])

    def test_short_separate_breaks_are_not_summed(self):
        blocks=[np.zeros((100,2)) for _ in range(3)]+[np.full((100,2),.2)]+[np.zeros((100,2)) for _ in range(2)]
        self.assertFalse(SIGNAL.screen_blocks(blocks,100)['near_silence_intervals'])

    def test_opposite_stereo_polarity_is_not_silence(self):
        data=np.tile([.2,-.2],(1000,1))
        self.assertFalse(SIGNAL.screen_blocks([data],100)['near_silence_intervals'])

    def test_nonfinite_and_actual_duration_failure(self):
        block=np.full((100,2),.2);block[2,0]=float('nan')
        result=SIGNAL.screen_blocks([block],100,min_seconds=4)
        self.assertIn('NONFINITE_SAMPLES',result['failures'])
        self.assertIn('BELOW_REQUESTED_MINIMUM',result['failures'])
        self.assertEqual(result['screening_status'],'TECHNICAL_FAIL')

    def test_discontinuity_across_block_boundary_is_flagged(self):
        result=SIGNAL.screen_blocks([np.full((100,1),-.6),np.full((100,1),.6)],100)
        self.assertIn(1,result['possible_jump_times_first_20'])

    def test_single_peak_does_not_claim_audible_clipping(self):
        block=np.full((100,2),.1);block[30,0]=1
        result=SIGNAL.screen_blocks([block],100)
        self.assertEqual(result['samples_at_digital_limit'],1)
        self.assertFalse(result['failures'])
        self.assertFalse(result['artistic_approval'])

    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            SIGNAL.screen_blocks([],100,min_seconds=8,max_seconds=4)

    def test_file_and_cli_hash_and_read_only_behavior(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'nonmusical_fixture.wav';output=Path(folder)/'screen.json'
            sf.write(source,np.full((8000,2),.1),8000,subtype='PCM_24')
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            result=SIGNAL.screen_file(source,min_seconds=.5,max_seconds=2)
            self.assertEqual(result['sha256'],digest)
            subprocess.run([sys.executable,str(ROOT/'pemara-music-listening-qc/scripts/screen_audio.py'),str(source),'--out',str(output)],check=True,capture_output=True)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),digest)
            self.assertFalse(json.loads(output.read_text())['artistic_approval'])


if __name__=='__main__':
    unittest.main(verbosity=2)
