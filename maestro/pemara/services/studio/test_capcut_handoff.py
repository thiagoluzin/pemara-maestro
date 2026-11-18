import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from capcut_handoff import (
    CapCutHandoffError,
    HandoffLimits,
    create_capcut_local_handoff,
)


class CapCutLocalHandoffTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project_dir = self.root / "project"
        (self.project_dir / "media").mkdir(parents=True)
        (self.project_dir / "exports").mkdir()
        self._write("media/video.mp4", b"video-source")
        self._write("media/frame.png", b"image-source")
        self._write("media/voice.wav", b"voice-source")
        self._write("media/music.mp3", b"music-source")
        self._write("media/sfx.flac", b"sfx-source")
        self._write("media/unreferenced_secret.wav", b"must-not-leak")
        self._write("exports/older.mp4", b"old-reference")
        self._write("exports/latest.mp4", b"latest-reference")
        self.project = {
            "projectId": "project-1",
            "name": "Filme local",
            "revision": 8,
            "settings": {
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "sampleRate": 48000,
                "privateSetting": "never-copy",
            },
            "assets": [
                self._asset("video", "video", "media/video.mp4"),
                self._asset("frame", "image", "media/frame.png"),
                self._asset("voice", "audio", "media/voice.wav"),
                self._asset("music", "audio", "media/music.mp3"),
                self._asset("sfx", "audio", "media/sfx.flac"),
                {
                    **self._asset(
                        "unused",
                        "audio",
                        "media/unreferenced_secret.wav",
                    ),
                    "apiKey": "must-never-appear",
                },
            ],
            "clips": [
                self._clip("c-video", "video", "video", start=0.0, duration=2.0),
                self._clip("c-frame", "video", "frame", start=2.0, duration=1.0),
                self._clip("c-voice", "voice", "voice", start=0.0, duration=3.0),
                self._clip("c-music", "music", "music", start=0.0, duration=3.0),
                self._clip("c-sfx", "sfx", "sfx", start=1.0, duration=0.5),
                {
                    "clipId": "caption-b",
                    "track": "text",
                    "text": "Segunda linha",
                    "timelineStart": 1.25,
                    "duration": 1.0,
                },
                {
                    "clipId": "caption-a",
                    "track": "caption",
                    "text": "Primeira fala",
                    "timelineStart": 0.1,
                    "duration": 0.8,
                },
            ],
            "exports": [
                {
                    "exportId": "old",
                    "filename": "older.mp4",
                    "relativePath": "exports/older.mp4",
                    "createdAt": "2026-01-01T00:00:00Z",
                },
                {
                    "exportId": "latest",
                    "filename": "latest.mp4",
                    "relativePath": "exports/latest.mp4",
                    "createdAt": "2026-07-24T00:00:00Z",
                    "privatePromptHistory": "must-never-appear",
                },
            ],
            "migrated_prompt_history": "must-never-appear",
        }

    def tearDown(self):
        self.temporary.cleanup()

    def _write(self, relative: str, payload: bytes) -> None:
        path = self.project_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    @staticmethod
    def _asset(asset_id: str, kind: str, relative: str):
        return {
            "assetId": asset_id,
            "name": Path(relative).name,
            "kind": kind,
            "relativePath": relative,
            "url": "/api/private/value-that-must-not-be-copied",
        }

    @staticmethod
    def _clip(
        clip_id: str,
        track: str,
        asset_id: str,
        *,
        start: float,
        duration: float,
    ):
        return {
            "clipId": clip_id,
            "track": track,
            "assetId": asset_id,
            "timelineStart": start,
            "duration": duration,
            "sourceStart": 0.0,
            "sourceEnd": duration,
            "volume": 1.0,
            "order": 0,
        }

    def test_editable_package_has_curated_structure_manifest_and_valid_checksums(self):
        output = self.root / "editable.zip"
        result = create_capcut_local_handoff(
            self.project,
            self.project_dir,
            output,
            mode="editable",
        )

        self.assertEqual(result.mode, "editable")
        self.assertEqual(result.package_sha256, hashlib.sha256(output.read_bytes()).hexdigest())
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            for directory in (
                "00_reference/",
                "01_video/",
                "02_audio/",
                "03_images/",
                "04_captions/",
            ):
                self.assertIn(directory, names)
            self.assertEqual(
                archive.read("00_reference/final-reference.mp4"),
                b"latest-reference",
            )
            self.assertTrue(any(name.startswith("01_video/video_") for name in names))
            self.assertTrue(any(name.startswith("03_images/image_") for name in names))
            self.assertEqual(
                len([name for name in names if name.startswith("02_audio/") and not name.endswith("/")]),
                3,
            )
            srt = archive.read("04_captions/pt-BR.srt").decode("utf-8")
            self.assertLess(srt.index("Primeira fala"), srt.index("Segunda linha"))
            self.assertIn("00:00:00,100 --> 00:00:00,900", srt)

            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["schemaVersion"], 1)
            self.assertEqual(manifest["target"]["name"], "CapCut Local/LLM")
            self.assertFalse(manifest["target"]["officialServiceAutomation"])
            self.assertEqual(manifest["llm"]["provider"], "ollama")
            self.assertEqual(manifest["llm"]["endpoint"], "loopback-only")
            self.assertTrue(manifest["llm"]["requiresHumanApproval"])
            self.assertFalse(manifest["llm"]["canStartCloudVoice"])
            self.assertEqual(manifest["reference"]["exportId"], "latest")
            self.assertEqual(manifest["captions"]["encoding"], "utf-8")
            self.assertEqual({item["role"] for item in manifest["media"]}, {
                "video",
                "image",
                "voice",
                "music",
                "sfx",
            })

            checksums = self._read_checksums(archive.read("SHA256SUMS"))
            self.assertNotIn("SHA256SUMS", checksums)
            for name, expected in checksums.items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)

            all_regular = b"\n".join(
                archive.read(name)
                for name in names
                if not name.endswith("/")
            )
            self.assertNotIn(b"must-never-appear", all_regular)
            self.assertNotIn(b"must-not-leak", all_regular)
            instructions = archive.read("IMPORTAR_NO_CAPCUT_LOCAL.md").decode("utf-8")
            self.assertIn("CapCut Local/LLM", instructions)
            self.assertIn("nao acessa, controla nem automatiza", instructions)

    def test_quick_mode_contains_reference_voice_and_captions_only(self):
        output = self.root / "quick.zip"
        create_capcut_local_handoff(
            self.project,
            self.project_dir,
            output,
            mode="quick",
        )
        with zipfile.ZipFile(output) as archive:
            regular = [name for name in archive.namelist() if not name.endswith("/")]
            self.assertIn("00_reference/final-reference.mp4", regular)
            self.assertTrue(any(name.startswith("02_audio/voice_") for name in regular))
            self.assertIn("04_captions/pt-BR.srt", regular)
            self.assertFalse(any(name.startswith("01_video/") for name in regular))
            self.assertFalse(any(name.startswith("03_images/") for name in regular))
            self.assertFalse(any("/music_" in name for name in regular))
            self.assertFalse(any("/sfx_" in name for name in regular))
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual([item["role"] for item in manifest["media"]], ["voice"])

    def test_same_project_produces_byte_identical_zip(self):
        first = self.root / "first.zip"
        second = self.root / "second.zip"
        create_capcut_local_handoff(self.project, self.project_dir, first)
        create_capcut_local_handoff(self.project, self.project_dir, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_traversal_absolute_and_sensitive_explicit_sources_are_blocked(self):
        cases = [
            ("../outside.wav", "PATH_TRAVERSAL"),
            (str((self.root / "outside.wav").resolve()), "ABSOLUTE_PATH_FORBIDDEN"),
            ("media/.env.mp3", "SENSITIVE_SOURCE_FORBIDDEN"),
            ("media/migrated_prompt_history.wav", "PROMPT_HISTORY_FORBIDDEN"),
            ("media/tool.py", "UNSUPPORTED_FORMAT"),
        ]
        (self.root / "outside.wav").write_bytes(b"outside")
        for index, (relative, expected_code) in enumerate(cases):
            with self.subTest(relative=relative):
                path = self.project_dir / relative
                if not Path(relative).is_absolute() and ".." not in Path(relative).parts:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"blocked")
                project = self._one_voice_project(relative)
                with self.assertRaises(CapCutHandoffError) as caught:
                    create_capcut_local_handoff(
                        project,
                        self.project_dir,
                        self.root / f"blocked-{index}.zip",
                    )
                self.assertEqual(caught.exception.code, expected_code)

    def test_symlink_source_is_blocked_when_platform_can_create_it(self):
        real = self.project_dir / "media" / "real.wav"
        real.write_bytes(b"voice")
        link = self.project_dir / "media" / "link.wav"
        try:
            os.symlink(real, link)
        except (OSError, NotImplementedError):
            self.skipTest("A plataforma nao permite criar symlink no teste.")
        with self.assertRaises(CapCutHandoffError) as caught:
            create_capcut_local_handoff(
                self._one_voice_project("media/link.wav"),
                self.project_dir,
                self.root / "symlink.zip",
            )
        self.assertEqual(caught.exception.code, "SYMLINK_FORBIDDEN")

    def test_file_count_size_caption_and_overwrite_limits(self):
        tiny = HandoffLimits(
            max_files=1,
            max_file_bytes=5,
            max_total_bytes=20,
            max_caption_cues=1,
            max_caption_chars_per_cue=20,
            max_timeline_seconds=10,
        )
        project = self._one_voice_project("media/voice.wav")
        with self.assertRaises(CapCutHandoffError) as caught:
            create_capcut_local_handoff(
                project,
                self.project_dir,
                self.root / "too-large.zip",
                limits=tiny,
            )
        self.assertEqual(caught.exception.code, "FILE_TOO_LARGE")

        output = self.root / "exists.zip"
        output.write_bytes(b"keep")
        with self.assertRaises(CapCutHandoffError) as caught:
            create_capcut_local_handoff(project, self.project_dir, output)
        self.assertEqual(caught.exception.code, "OUTPUT_EXISTS")
        self.assertEqual(output.read_bytes(), b"keep")

    def _one_voice_project(self, relative: str):
        return {
            "projectId": "one",
            "name": "One",
            "revision": 1,
            "assets": [self._asset("voice", "audio", relative)],
            "clips": [
                self._clip("clip", "voice", "voice", start=0.0, duration=1.0),
            ],
            "exports": [],
        }

    @staticmethod
    def _read_checksums(payload: bytes):
        result = {}
        for line in payload.decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            result[name] = digest
        return result


if __name__ == "__main__":
    unittest.main()
