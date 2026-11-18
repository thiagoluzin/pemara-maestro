"""Retirement blocks execution and preserves authenticated historical media."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from generative_jobs import GenerativeJobStore
import main


class MusicRetirementTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.store = GenerativeJobStore(self.root / 'jobs.json', recover_on_init=False)
        self.store_patch = patch.object(main, '_GEN_JOB_STORE', self.store)
        self.store_patch.start()
        self.environment = patch.dict(os.environ, {'STUDIO_INTERNAL_TOKEN': 'retirement-test-token'})
        self.environment.start()
        self.client = TestClient(main.app)
        self.headers = {'X-Studio-Internal-Token': 'retirement-test-token'}

    def tearDown(self):
        self.environment.stop()
        self.store_patch.stop()
        self.directory.cleanup()

    def history(self, relative='outputs/master.wav'):
        media = self.root / 'old' / 'outputs' / 'master.wav'
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b'historical approved master unchanged')
        self.store.update('old', mode='music_reinstrument', status='done',
            job_dir=str(media.parent.parent), original_name='source.wav',
            review_status='APPROVED', library_visible=True,
            result={'artifacts': [{'key': 'masterWav', 'relativePath': relative, 'mediaType': 'audio/wav'}]})
        return media.read_bytes()

    def test_removed_status_and_every_mutation_return_410_without_uploading(self):
        before = self.store.list()
        response = self.client.get('/api/music-reinstrument/status', headers=self.headers)
        self.assertEqual(response.status_code, 410)
        for method, suffix in [('POST', 'jobs'), ('POST', 'jobs/old/score-review'),
            ('POST', 'jobs/old/review'), ('POST', 'jobs/old/cancel'), ('PUT', 'jobs'),
            ('PATCH', 'jobs/old'), ('DELETE', 'jobs/old')]:
            with self.subTest(method=method, suffix=suffix):
                response = self.client.request(method, '/api/music-reinstrument/' + suffix,
                                               headers=self.headers, content=b'ignored upload')
                self.assertEqual(response.status_code, 410, response.text)
        self.assertEqual(self.store.list(), before)
        self.assertFalse(hasattr(main, '_start_music_reinstrument_worker'))
        self.assertFalse(hasattr(main, '_start_score_first_orchestration_worker'))

    def test_retired_feature_and_history_still_require_authorization(self):
        for method, suffix in [('GET', 'status'), ('GET', 'jobs'), ('POST', 'jobs'),
                               ('GET', 'jobs/old/artifacts/masterWav')]:
            self.assertEqual(self.client.request(method, '/api/music-reinstrument/' + suffix).status_code, 403)

    def test_old_downloads_and_library_work_without_generation_runtime(self):
        expected = self.history()
        response = self.client.get('/api/music-reinstrument/jobs/old/artifacts/masterWav', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, expected)
        assets = main._music_reinstrument_library_assets()
        self.assertEqual(len(assets), 1)
        public = self.client.get('/api/music-reinstrument/jobs/old', headers=self.headers).json()
        self.assertNotIn('job_dir', public)
        self.assertNotIn('relativePath', public['result']['artifacts'][0])

    def test_archived_artifact_cannot_traverse_outside_job(self):
        self.history('../outside.wav')
        (self.root / 'outside.wav').write_bytes(b'outside')
        response = self.client.get('/api/music-reinstrument/jobs/old/artifacts/masterWav', headers=self.headers)
        self.assertEqual(response.status_code, 404)
        with self.assertRaises(FileNotFoundError):
            main._resolve_archived_music_artifact(self.root / 'old', '..')

    def test_reading_history_does_not_promote_or_mutate_existing_reviews(self):
        self.history()
        before = self.store.get('old')
        self.client.get('/api/music-reinstrument/jobs', headers=self.headers)
        response = self.client.post('/api/music-reinstrument/jobs/old/review', headers=self.headers,
                                    json={'decision': 'APPROVED'})
        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.store.get('old'), before)


if __name__ == '__main__':
    unittest.main()
