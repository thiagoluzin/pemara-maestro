"""Exercise the node worker contract with a fake Studio, never the GPU model."""
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import uuid

from test_voice_studio import wav_bytes
from voice_studio import VoiceStudio, digest
from voice_studio_models import NarrationCreate
import voice_studio_runtime as worker


class RuntimeTests(unittest.TestCase):
    def test_per_attempt_placement_keeps_default_and_rejects_invalid_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            job = Path(temporary)
            self.assertEqual(worker.execution_placement(job), (32, None))
            path = job / 'execution-placement.json'
            data = {'schema': 'pemara-drama3-placement-v1', 'jobId': job.name, 'gpuExpertLayers': 16}
            path.write_text(json.dumps(data))
            self.assertEqual(worker.execution_placement(job), (16, digest(path)))
            for invalid in [True, -1, 33, '16']:
                path.write_text(json.dumps({**data, 'gpuExpertLayers': invalid}))
                with self.assertRaises(ValueError): worker.execution_placement(job)
            path.write_text(json.dumps({**data, 'jobId': 'different'}))
            with self.assertRaises(ValueError): worker.execution_placement(job)

    def test_atomic_receipt_survives_transient_windows_reader_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'progress.json'
            target.write_text('{"old":true}')
            original = worker.os.replace
            calls = []
            def replacement(source, destination):
                calls.append((source, destination))
                if len(calls) < 3:
                    raise PermissionError('Simulated Windows read handle')
                return original(source, destination)
            with patch.object(worker.os, 'replace', side_effect=replacement), patch.object(worker.time, 'sleep'):
                worker.save(target, {'phase': 'generating'})
            self.assertEqual(len(calls), 3)
            self.assertEqual(json.loads(target.read_text()), {'phase': 'generating'})
            self.assertEqual(list(Path(temporary).glob('*.tmp')), [])

    def test_reference_options_complete_receipt_and_original_audio_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            service = VoiceStudio(Path(temporary), comfy=lambda *args: {}, launcher=lambda _: None)
            identifier = uuid.uuid4().hex
            service.create(NarrationCreate(requestId=identifier, text='Uma narração completa.', mode='chunked', maxFrames=16384))
            folder = service.folder(identifier)
            request_path = folder / 'request.json'; request = json.loads(request_path.read_text(encoding='utf-8'))
            (folder / 'reference.wav').write_bytes(wav_bytes())
            request['reference'] = {'transcript': 'Texto exato da referência.', 'authorized': True, 'sha256': digest(folder / 'reference.wav')}
            request_path.write_text(json.dumps(request), encoding='utf-8')
            captured = {}
            class FakeStudio:
                def __init__(self, output): self.output = output; self.references = {}; self.exports = {}
                def load(self, options):
                    captured['model'] = options
                    captured['memory_environment'] = {
                        key: os.environ.get(key) for key in (
                            'FISH_DRAMA3_ONESHOT_MEMORY_BOUNDED',
                            'FISH_DRAMA3_ONESHOT_REFERENCE_AUDIO',
                            'FISH_DRAMA3_ONESHOT_REFERENCE_TEXT')}
                def snapshot(self): return {'status': 'ready', 'phase': 'complete', 'result': self.result} if hasattr(self, 'result') else {'status': 'ready'}
                def generate(self, options):
                    captured['generation'] = options; captured['reference'] = self.references.copy()
                    path = folder / 'native/speech.wav'; path.parent.mkdir(exist_ok=True); path.write_bytes(wav_bytes())
                    self.exports['wav'] = path
                    self.result = {'wav_url': 'wav', 'metrics': {'complete': True, 'finish_reason': 'eos'}}
                def shutdown(self): captured['shutdown'] = True
            modules = {
                'fish_drama3': types.ModuleType('fish_drama3'),
                'fish_drama3.web_service': types.SimpleNamespace(Studio=FakeStudio),
                'fish_drama3.web_planning': types.SimpleNamespace(generation_plan=lambda options: {'risk': 'low'}),
                'fish_drama3.web_config': types.SimpleNamespace(generation_options=lambda options, _: options),
            }
            with patch.dict('sys.modules', modules), patch.object(worker.sys, 'argv', ['worker', str(folder)]), \
                    patch.object(worker.shutil, 'which', return_value=None), patch('builtins.print'), \
                    patch.dict(os.environ, {'FISH_DRAMA3_ONESHOT_REFERENCE_AUDIO': 'stale.wav',
                                            'FISH_DRAMA3_ONESHOT_REFERENCE_TEXT': 'stale'}):
                worker.main()
            options = captured['generation']
            self.assertEqual(options['reference_text'], request['reference']['transcript'])
            self.assertEqual(options['generation_mode'], 'chunked'); self.assertEqual(options['max_frames'], 16384)
            self.assertFalse(options['allow_partial']); self.assertTrue(captured['shutdown'])
            self.assertEqual(captured['memory_environment'], {
                'FISH_DRAMA3_ONESHOT_MEMORY_BOUNDED': '1',
                'FISH_DRAMA3_ONESHOT_REFERENCE_AUDIO': str(folder / 'reference.wav'),
                'FISH_DRAMA3_ONESHOT_REFERENCE_TEXT': request['reference']['transcript']})
            self.assertEqual(captured['model']['gpu_expert_layers'], 32)
            self.assertEqual(captured['model']['headroom_percent'], 5)
            self.assertEqual((folder / 'speech.wav').read_bytes(), wav_bytes())
            receipt = json.loads((folder / 'result.json').read_text())
            self.assertEqual(receipt['requestSha256'], digest(request_path)); self.assertFalse(receipt['networkGeneration'])
            self.assertEqual(receipt['artisticApproval'], 'pending')


if __name__ == '__main__':
    unittest.main()
