import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from project_assembly import AssemblyError, assemble_project


class ProjectAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "approved_sequence"
        for name in ("takes", "audio", "output", "qc"):
            (self.project / name).mkdir(parents=True, exist_ok=True)
        self.ffmpeg = shutil.which("ffmpeg")
        self.ffprobe = shutil.which("ffprobe")
        if not self.ffmpeg or not self.ffprobe:
            self.skipTest("FFmpeg/FFprobe indisponivel")

    def tearDown(self):
        self.temp.cleanup()

    def _make_source(self, take_id: str, frequency: int) -> tuple[Path, Path]:
        video = self.project / "takes" / f"take{take_id}.mp4"
        audio = self.project / "audio" / f"take{take_id}.wav"
        subprocess.run([
            self.ffmpeg, "-v", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc2=size=320x180:rate=30:duration=1",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        ], check=True)
        subprocess.run([
            self.ffmpeg, "-v", "error", "-y",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration=1:sample_rate=48000",
            "-c:a", "pcm_s16le", str(audio),
        ], check=True)
        return video, audio

    def test_assembles_compatible_approved_sources_with_hard_cuts_and_qc(self):
        first_video, first_audio = self._make_source("01", 440)
        second_video, second_audio = self._make_source("02", 660)
        sources = [
            {
                "takeId": "01",
                "videoFile": first_video.relative_to(self.project).as_posix(),
                "audioFile": first_audio.relative_to(self.project).as_posix(),
                "audioEmbedded": False,
            },
            {
                "takeId": "02",
                "videoFile": second_video.relative_to(self.project).as_posix(),
                "audioFile": second_audio.relative_to(self.project).as_posix(),
                "audioEmbedded": False,
            },
        ]

        record = assemble_project(
            self.project,
            sources=sources,
            source_fingerprint="a" * 64,
            job_id="assemblytest01",
            ffmpeg=self.ffmpeg,
            ffprobe=self.ffprobe,
        )

        self.assertEqual(record["qc_status"], "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING")
        self.assertEqual(record["video_codec"], "h264")
        self.assertEqual(record["audio_codec"], "aac")
        self.assertAlmostEqual(record["duration_seconds"], 2.0, delta=0.12)
        self.assertRegex(record["sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue((self.project / record["file"]).is_file())
        self.assertTrue((self.project / record["review_file"]).is_file())
        self.assertTrue((self.project / record["qc_file"]).is_file())
        self.assertEqual(len(record["boundary_frames"]), 1)

    def test_rejects_mixed_video_geometry_before_writing_master(self):
        first_video, first_audio = self._make_source("01", 440)
        second_video = self.project / "takes" / "take02.mp4"
        subprocess.run([
            self.ffmpeg, "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=1",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(second_video),
        ], check=True)
        second_audio = self.project / "audio" / "take02.wav"
        shutil.copy2(first_audio, second_audio)

        with self.assertRaisesRegex(AssemblyError, "incompativeis"):
            assemble_project(
                self.project,
                sources=[
                    {"takeId": "01", "videoFile": "takes/take01.mp4", "audioFile": "audio/take01.wav"},
                    {"takeId": "02", "videoFile": "takes/take02.mp4", "audioFile": "audio/take02.wav"},
                ],
                source_fingerprint="b" * 64,
                job_id="assemblytest02",
                ffmpeg=self.ffmpeg,
                ffprobe=self.ffprobe,
            )
        self.assertFalse(any((self.project / "output").iterdir()))


if __name__ == "__main__":
    unittest.main()
