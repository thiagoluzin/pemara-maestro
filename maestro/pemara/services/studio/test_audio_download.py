"""Verify real encoding, safe local sources and mobile download headers."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from audio_download import mp3_filename, prepare_mp3, resolve_audio_source
with patch("urllib.request.urlopen", side_effect=AssertionError("No live network in tests")):
    import main
from fastapi.testclient import TestClient


class AudioDownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "song.flac"
        self.ffmpeg = shutil.which("ffmpeg")
        self.assertIsNotNone(self.ffmpeg, "FFmpeg is required for delivery")
        subprocess.run([self.ffmpeg, "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=0.6", "-ac", "2", str(self.source)], check=True)
        self.cache = self.root / "cache"

    def test_real_mp3_preserves_source_and_reuses_cache(self):
        original = hashlib.sha256(self.source.read_bytes()).digest()
        output = prepare_mp3(self.source, self.cache, self.ffmpeg)
        probe = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_streams",
                                "-show_format", "-of", "json", str(output)], capture_output=True, check=True)
        data = json.loads(probe.stdout)
        self.assertEqual(data["streams"][0]["codec_name"], "mp3")
        self.assertEqual(data["streams"][0]["channels"], 2)
        self.assertGreater(float(data["format"]["duration"]), 0.5)
        with patch("audio_download.subprocess.run", side_effect=AssertionError("Must reuse encoded MP3")):
            self.assertEqual(prepare_mp3(self.source, self.cache, self.ffmpeg), output)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), original)
        stat = self.source.stat()
        import os
        os.utime(self.source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
        self.assertNotEqual(prepare_mp3(self.source, self.cache, self.ffmpeg), output)

    def test_mobile_filename_mime_disposition_and_range(self):
        with patch.object(main, "STUDIO_OUTPUT_DIR", str(self.root)), \
             patch.object(main, "BASE_DIR", str(self.root)), \
             patch.object(main, "_is_internal_request", return_value=True), \
             patch.object(main, "get_ffmpeg", return_value=self.ffmpeg):
            client = TestClient(main.app)
            url = "/api/generative/audio-export/Minha%20M%C3%BAsica.mp3"
            response = client.get(url, params={"source": "/api/generative/output?path=song.flac"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "audio/mpeg")
            self.assertIn("attachment;", response.headers["content-disposition"])
            self.assertIn('filename="Minha M_sica.mp3"', response.headers["content-disposition"])
            self.assertIn("Minha%20M%C3%BAsica.mp3", response.headers["content-disposition"])
            ranged = client.get(url, params={"source": "/api/generative/output?path=song.flac", "download": "false"},
                                headers={"Range": "bytes=0-127"})
            self.assertEqual(ranged.status_code, 206)
            self.assertEqual(len(ranged.content), 128)
            self.assertIn("inline;", ranged.headers["content-disposition"])

    def test_only_local_audio_outputs_can_be_exported(self):
        resolver = lambda *args: ""
        self.assertEqual(resolve_audio_source("/api/generative/output?path=song.flac", self.root, resolver), self.source.resolve())
        for source in ("https://example.com/song.flac", "/api/generative/output?path=../song.flac",
                       "/api/generative/output?path=C:/private.flac", "/unknown?path=song.flac",
                       "/api/generative/output?path=song.flac&path=other.flac"):
            with self.assertRaises(ValueError):
                resolve_audio_source(source, self.root, resolver)
        with self.assertRaises(FileNotFoundError):
            resolve_audio_source("/api/generative/comfy-view?filename=missing.flac", self.root, resolver)
        (self.root / "video.mp4").write_bytes(b"video")
        with self.assertRaises(ValueError):
            resolve_audio_source("/api/generative/output?path=video.mp4", self.root, resolver)

    def test_conversion_failure_does_not_publish_partial_file(self):
        self.source.write_bytes(b"invalid audio")
        with self.assertRaises(RuntimeError):
            prepare_mp3(self.source, self.cache, self.ffmpeg)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_friendly_filename_cannot_inject_headers(self):
        self.assertEqual(mp3_filename('folder/name"\r\nX-Header:bad.flac'), "name___X-Header_bad.mp3")
        self.assertEqual(mp3_filename(""), "Musica.mp3")


if __name__ == "__main__":
    unittest.main()
