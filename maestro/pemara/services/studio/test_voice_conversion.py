"""Meaningful import, timing and persistence checks; no GPU model invocation."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import numpy as np
import soundfile as sf

from voice_studio import VoiceStudio, digest, write_json
from voice_studio_models import VoiceCreate
from voice_conversion import VoiceConversion, ConversionCreate, create_conversion_router
from voice_conversion_media import probe, extract_timeline, run, RATE
from voice_conversion_runtime import exact_length, stitch, windows


def video_fixture(path, *, offset=.7, duration=3):
    run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-f', 'lavfi', '-i', f'color=c=navy:s=160x90:r=10:d={duration}',
         '-itsoffset', str(offset), '-f', 'lavfi', '-i', 'sine=frequency=330:sample_rate=44100:duration=1',
         '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', str(path)])


def fixture_completion(service, job_id):
    folder = service.folder(job_id); request = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
    media = request['source']; source = service.root / 'media' / media['id'] / media['file']
    extract_timeline(source, folder / 'original_timeline.wav', media, request['settings']['audioTrack'])
    data, rate = sf.read(folder / 'original_timeline.wav', always_2d=True)
    # Identity signal fixture proves placement and delivery, not voice quality.
    sf.write(folder / 'speech.wav', data, rate, subtype='PCM_16')
    receipt = {'engine': 'synthetic-conversion-fixture', 'requestSha256': digest(folder / 'request.json'),
        'wavSha256': digest(folder / 'speech.wav'), 'originalTimelineSha256': digest(folder / 'original_timeline.wav'),
        'sourceSamples': len(data), 'outputSamples': len(data), 'sampleRate': rate, 'duration': len(data) / rate,
        'preservedBackground': False, 'metrics': {'complete': True, 'finish_reason': 'converted'}}
    write_json(folder / 'result.json', receipt)


class TimingTests(unittest.TestCase):
    def test_real_container_audio_offset_and_trailing_silence_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source.mkv'; video_fixture(path)
            media = probe(path); target = Path(tmp) / 'timeline.wav'
            self.assertTrue(media['hasVideo']); self.assertAlmostEqual(media['duration'], 3, places=2)
            extract_timeline(path, target, media, media['tracks'][0]['index'])
            data, rate = sf.read(target, always_2d=True)
            self.assertEqual(len(data), 3 * RATE)
            heard = np.where(np.abs(data[:, 0]) > .005)[0]
            self.assertAlmostEqual(heard[0] / rate, .7, delta=.005)
            self.assertAlmostEqual(heard[-1] / rate, 1.7, delta=.005)
            self.assertLess(np.max(np.abs(data[round(1.8 * rate):])), .0001)

    def test_overlapping_chunks_remain_at_original_samples_without_duplication(self):
        count = 47 * RATE
        spans = list(windows(count)); self.assertGreater(len(spans), 1)
        data = np.sin(np.arange(count) / 37).astype('float32')
        result = stitch([data[start:end] for start, end in spans], spans, count)
        self.assertEqual(len(result), len(data)); np.testing.assert_allclose(result, data, atol=1e-6)

    def test_large_duration_drift_and_voiced_tail_are_blocked(self):
        with self.assertRaises(ValueError): exact_length(np.array([float('nan')]), 1)
        with self.assertRaises(ValueError): exact_length(np.ones(44100), 33000)
        with self.assertRaises(ValueError): exact_length(np.ones(44110), 44100)
        self.assertEqual(len(exact_length(np.zeros(44110), 44100)), 44100)
        self.assertEqual(len(exact_length(np.zeros(44090), 44100)), 44100)

    def test_no_audio_and_more_than_five_minutes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'silent.mp4'
            run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-f', 'lavfi', '-i', 'color=s=160x90:r=1:d=1', '-an', '-c:v', 'libx264', str(path)])
            with self.assertRaisesRegex(ValueError, 'faixa de áudio'): probe(path)
            metadata = {'format': {'duration': '301'}, 'streams': [{'index': 0, 'codec_type': 'audio'}]}
            with patch('voice_conversion_media.run') as mocked:
                mocked.return_value.stdout = json.dumps(metadata).encode()
                with self.assertRaisesRegex(ValueError, '5 minutos'): probe(path)


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.library = VoiceStudio(self.root / 'library', comfy=lambda *args: {}, launcher=lambda _: None)
        self.launches = []
        self.service = VoiceConversion(self.library, self.root / 'conversion', comfy=lambda *args: {}, launcher=self.launches.append)
        app = FastAPI(); app.include_router(create_conversion_router(self.service, lambda request: request.headers.get('X-Test') == 'yes'))
        self.client = TestClient(app); self.headers = {'X-Test': 'yes'}
        self.original = self.root / 'guide.mkv'; video_fixture(self.original)
        voice_id = uuid.uuid4().hex; folder = self.library.root / 'voices' / voice_id; folder.mkdir(parents=True)
        reference = folder / 'source.wav'; sf.write(reference, np.sin(np.arange(2 * RATE) / 11) * .1, RATE)
        self.voice = self.library.register_voice(voice_id, VoiceCreate(name='Voz autorizada de teste', transcript='Referência sintética.', authorized=True), reference)

    def tearDown(self):
        self.client.close(); self.tmp.cleanup()

    def upload(self):
        response = self.client.post('/api/voice-conversion/media?filename=guide.mkv', content=self.original.read_bytes(), headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text); return response.json()

    def options(self, media):
        return ConversionCreate(requestId=uuid.uuid4().hex, mediaId=media['id'], voiceId=self.voice['id'],
                                audioTrack=media['tracks'][0]['index'], preserveBackground=False)

    def test_import_conversion_exact_delivery_and_persistent_history(self):
        original_hash = digest(self.original); media = self.upload(); options = self.options(media)
        first = self.service.create(options); self.service.create(options)
        self.assertEqual(self.launches, [first['id']])
        fixture_completion(self.service, first['id']); ready = self.service.get(first['id'])
        self.assertEqual(ready['status'], 'COMPLETED')
        self.assertIn('/voice-conversion/jobs/', ready['audioUrl'])
        response = self.client.get('/api/voice-conversion/jobs/' + first['id'] + '/audio/wav', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        audio, rate = sf.read(io.BytesIO(response.content)); self.assertEqual(len(audio), 3 * RATE)
        self.assertEqual(digest(self.original), original_hash)
        restored = VoiceConversion(self.library, self.service.root, comfy=lambda *args: {}, launcher=lambda _: None)
        self.assertEqual(restored.jobs()['jobs'][0]['status'], 'COMPLETED')

    def test_wrong_track_missing_voice_and_source_tampering_are_rejected(self):
        media = self.upload(); options = self.options(media)
        with self.assertRaises(HTTPException): self.service.create(options.model_copy(update={'audioTrack': 100}))
        with self.assertRaises(HTTPException): self.service.create(options.model_copy(update={'voiceId': 'a' * 32}))
        record = self.service.media(media['id']); source = self.service.root / 'media' / media['id'] / record['file']; source.write_bytes(b'altered')
        with self.assertRaises(HTTPException): self.service.create(options)

    def test_authentication_applies_before_raw_upload_is_consumed(self):
        response = self.client.post('/api/voice-conversion/media?filename=guide.mkv', content=b'not media')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(list((self.service.root / 'media').glob('*')) if (self.service.root / 'media').exists() else [], [])
        for suffix in ['/status', '/jobs', '/media/' + 'a' * 32 + '/preview']:
            self.assertEqual(self.client.get('/api/voice-conversion' + suffix).status_code, 403)

    def test_browser_origin_guard_is_applied_before_upload(self):
        app = FastAPI()
        app.include_router(create_conversion_router(self.service, lambda request: True,
                           lambda request: request.headers.get('origin') != 'https://foreign.example'))
        with TestClient(app) as client:
            response = client.post('/api/voice-conversion/media?filename=guide.mkv', content=b'not media', headers={'Origin': 'https://foreign.example'})
            self.assertEqual(response.status_code, 403)

    def test_output_tampering_blocks_download(self):
        media = self.upload(); record = self.service.create(self.options(media)); fixture_completion(self.service, record['id'])
        self.service.get(record['id']); (self.service.folder(record['id']) / 'speech.wav').write_bytes(b'altered')
        self.assertEqual(self.service.get(record['id'])['status'], 'INTEGRITY_ERROR')
        response = self.client.get('/api/voice-conversion/jobs/' + record['id'] + '/audio/wav', headers=self.headers)
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
