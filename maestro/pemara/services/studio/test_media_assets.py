import os
import tempfile
import unittest
from pathlib import Path

from media_assets import list_media_assets


class MediaAssetsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.comfy = Path(self.temp_dir.name) / "comfy"
        self.studio = Path(self.temp_dir.name) / "studio"
        self.comfy.mkdir()
        self.studio.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create(self, root: Path, name: str, modified: int):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"asset")
        os.utime(path, (modified, modified))
        return path

    def test_lists_only_media_and_orders_newest_first(self):
        self.create(self.comfy, "old.png", 100)
        self.create(self.comfy, "nested/new.mp4", 300)
        self.create(self.studio, "audio/song.mp3", 200)
        self.create(self.studio, "ignore.json", 400)

        result = list_media_assets(self.comfy, self.studio)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["items"][0]["filename"], "new.mp4")
        self.assertIn("subfolder=nested", result["items"][0]["url"])

    def test_filters_kind_and_paginates(self):
        self.create(self.comfy, "one.png", 100)
        self.create(self.comfy, "two.jpg", 200)
        self.create(self.studio, "clip.mp4", 300)

        result = list_media_assets(
            self.comfy,
            self.studio,
            kind="image",
            page=2,
            page_size=1,
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["kind"], "image")

    def test_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            list_media_assets(self.comfy, self.studio, kind="document")

    def test_completed_video_survives_scan_limit_without_duplicates(self):
        video = self.create(self.comfy, "jobs/new.mp4", 300)
        self.create(self.comfy, "older.mp4", 100)
        limited = list_media_assets(self.comfy, self.studio, kind="video",
            max_scan_files=0, recent_comfy_files=[video, video])
        self.assertEqual([x['filename'] for x in limited['items']], ['new.mp4'])
        full = list_media_assets(self.comfy, self.studio, kind="video",
            recent_comfy_files=[video])
        self.assertEqual([x['filename'] for x in full['items']], ['new.mp4', 'older.mp4'])

    def test_priority_files_cannot_escape_root_or_ignore_kind_filter(self):
        outside = self.create(self.studio, "private.mp4", 400)
        image = self.create(self.comfy, "image.png", 300)
        result = list_media_assets(self.comfy, self.studio, kind="video",
            max_scan_files=0, recent_comfy_files=[outside, image, self.comfy / 'missing.mp4'])
        self.assertEqual(result['items'], [])

    def test_merges_reinstrumentation_asset_into_audio_library(self):
        result = list_media_assets(
            self.comfy,
            self.studio,
            kind="audio",
            extra_assets=[
                {
                    "source": "music_reinstrument",
                    "kind": "audio",
                    "filename": "tema - reinstrumentacao.wav",
                    "relative_path": "job/outputs/master.wav",
                    "url": "/api/music-reinstrument/jobs/job/artifacts/masterWav",
                    "media_type": "audio/wav",
                    "modified_at": 500,
                    "size": 1234,
                    "review_status": "PENDING_HUMAN_REVIEW",
                }
            ],
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["source"], "music_reinstrument")
        self.assertEqual(result["items"][0]["review_status"], "PENDING_HUMAN_REVIEW")


if __name__ == "__main__":
    unittest.main()
