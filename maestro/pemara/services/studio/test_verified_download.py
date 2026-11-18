import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from verified_download import prepare_verified_zip
with patch("urllib.request.urlopen", side_effect=AssertionError("No live network")):
    import main
from fastapi.testclient import TestClient


class VerifiedDownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Música original.mp4"
        self.body = bytes(range(256)) * 9000
        self.source.write_bytes(self.body)

    def test_complete_zip_keeps_exact_media_and_contains_no_local_path(self):
        archive = prepare_verified_zip(self.source, self.root / "cache")
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(z.read(self.source.name), self.body)
            receipt = json.loads(z.read("VERIFICAR.json"))
            self.assertEqual(receipt['sha256'], hashlib.sha256(self.body).hexdigest())
            self.assertEqual(receipt['bytes'], len(self.body))
            self.assertNotIn(str(self.root), json.dumps(receipt))
        stamp = archive.stat().st_mtime_ns
        self.assertEqual(prepare_verified_zip(self.source, self.root / "cache"), archive)
        self.assertEqual(archive.stat().st_mtime_ns, stamp)
        self.assertEqual(self.source.read_bytes(), self.body)

    def test_truncated_mobile_transfer_cannot_extract(self):
        archive = prepare_verified_zip(self.source, self.root / "cache")
        with self.assertRaises(zipfile.BadZipFile):
            zipfile.ZipFile(io.BytesIO(archive.read_bytes()[:-100]))

    def test_mutated_source_gets_a_different_package(self):
        old = prepare_verified_zip(self.source, self.root / "cache")
        self.source.write_bytes(b"new source")
        new = prepare_verified_zip(self.source, self.root / "cache")
        self.assertNotEqual(new, old)
        with zipfile.ZipFile(new) as z:
            self.assertEqual(z.read(self.source.name), b"new source")

    def test_damaged_cached_zip_is_rebuilt_from_preserved_original(self):
        target = prepare_verified_zip(self.source, self.root / 'cache')
        target.write_bytes(b'broken archive')
        self.assertEqual(prepare_verified_zip(self.source, self.root / 'cache'), target)
        with zipfile.ZipFile(target) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(z.read(self.source.name), self.body)

    def test_video_archive_retains_authentication_download_gate_and_range(self):
        client = TestClient(main.app)
        url = '/api/video-projects/p/takes/t/preview?archive=true'
        with patch.object(main, '_is_internal_request', return_value=False), patch.object(main, '_get_take_download_path') as resolve:
            self.assertEqual(client.get(url).status_code, 403)
            resolve.assert_not_called()
        with patch.object(main, '_is_internal_request', return_value=True), patch.object(main, 'BASE_DIR', str(self.root)), patch.object(main, '_get_take_download_path', return_value=self.source):
            full = client.get(url)
            self.assertEqual(full.status_code, 200)
            self.assertEqual(full.headers['content-type'], 'application/zip')
            with zipfile.ZipFile(io.BytesIO(full.content)) as z:
                self.assertEqual(z.read(self.source.name), self.body)
            partial = client.get(url, headers={'Range': 'bytes=100-599'})
            self.assertEqual(partial.status_code, 206)
            self.assertEqual(partial.content, full.content[100:600])
        with patch.object(main, '_is_internal_request', return_value=True), patch.object(main, '_get_take_download_path', side_effect=PermissionError('blocked')):
            self.assertEqual(client.get(url).status_code, 409)

    def test_audio_archive_contains_the_named_mp3_and_exact_bytes(self):
        client = TestClient(main.app)
        with patch.object(main, '_is_internal_request', return_value=True), patch.object(main, 'BASE_DIR', str(self.root)), patch('audio_download.resolve_audio_source', return_value=self.source), patch('audio_download.prepare_mp3', return_value=self.source):
            full = client.get('/api/generative/audio-export/Última música.mp3', params={'source':'/local', 'archive':'true'})
            self.assertEqual(full.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(full.content)) as z:
                self.assertEqual(z.read('Última música.mp3'), self.body)

if __name__ == '__main__':
    unittest.main()
