import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from review_proxies import (
    REVIEW_PROXY_MAX_FPS,
    REVIEW_PROXY_MAX_HEIGHT,
    REVIEW_PROXY_MAX_WIDTH,
    build_review_proxy,
    resolve_review_proxy,
)
from video_projects import (
    get_take_download_path,
    get_take_preview_path,
    list_takes,
)


class ReviewProxyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "projeto_proxy"
        self.project.mkdir()
        (self.project / "project_manifest.json").write_text(
            json.dumps({"take_queue": "take_queue.json"}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _source_video(self) -> Path:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.skipTest("ffmpeg nao disponivel")
        source = self.project / "takes" / "master.mp4"
        source.parent.mkdir(parents=True)
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=1920x1080:rate=30:duration=1",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(source),
            ],
            check=True,
            timeout=60,
        )
        return source

    def _queue(self, source: Path) -> None:
        (self.project / "take_queue.json").write_text(
            json.dumps(
                {
                    "takes": [
                        {
                            "id": "01A",
                            "slug": "proxy_mobile",
                            "maestro_status": "APPROVED",
                            "base_image": {"status": "approved_for_video"},
                            "video": {"output_active": str(source)},
                            "qc": {"status": "approved"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_proxy_is_selected_only_for_playback_and_invalidates_on_master_change(self):
        if not shutil.which("ffprobe"):
            self.skipTest("ffprobe nao disponivel")
        source = self._source_video()
        self._queue(source)
        master_hash = self._sha256(source)

        result = build_review_proxy(self.project, "01A", source)
        proxy = Path(result["proxy"])
        sidecar = json.loads(Path(result["sidecar"]).read_text(encoding="utf-8"))

        self.assertTrue(proxy.is_file())
        self.assertEqual(self._sha256(source), master_hash)
        self.assertTrue(sidecar["validation"]["master_preserved"])
        self.assertTrue(sidecar["validation"]["approval_state_unchanged"])
        self.assertFalse(sidecar["validation"]["gpu_used"])
        self.assertLessEqual(sidecar["proxy"]["width"], REVIEW_PROXY_MAX_WIDTH)
        self.assertLessEqual(sidecar["proxy"]["height"], REVIEW_PROXY_MAX_HEIGHT)
        self.assertLessEqual(sidecar["proxy"]["fps"], REVIEW_PROXY_MAX_FPS)
        self.assertEqual(sidecar["proxy"]["video_codec"], "h264")
        self.assertEqual(sidecar["proxy"]["pixel_format"], "yuv420p")
        self.assertEqual(sidecar["proxy"]["audio_codec"], "aac")
        self.assertTrue(sidecar["proxy"]["faststart"])

        self.assertEqual(
            get_take_preview_path(self.root, "projeto_proxy", "01A"),
            proxy.resolve(),
        )
        self.assertEqual(
            get_take_download_path(self.root, "projeto_proxy", "01A"),
            source.resolve(),
        )
        view = list_takes(self.root, "projeto_proxy")["data"][0]
        self.assertTrue(view["hasReviewProxy"])
        self.assertEqual(view["reviewProxyFile"], proxy.name)
        self.assertEqual(view["masterBytes"], source.stat().st_size)
        self.assertEqual(view["reviewProxyBytes"], proxy.stat().st_size)

        stat = source.stat()
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        self.assertIsNone(resolve_review_proxy(self.project, "01A", source))
        self.assertEqual(
            get_take_preview_path(self.root, "projeto_proxy", "01A"),
            source.resolve(),
        )
        self.assertEqual(self._sha256(source), master_hash)


if __name__ == "__main__":
    unittest.main()
