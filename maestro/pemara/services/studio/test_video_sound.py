import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from video_sound import (
    ExternalCommandVideoSoundProvider,
    VideoSoundProviderRegistry,
    VideoSoundRequest,
    load_external_provider_specs,
)


class VideoSoundProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / "source.mp4"
        self.video.write_bytes(b"video-source")

    def tearDown(self):
        self.temp.cleanup()

    def test_registry_exposes_capabilities_without_leaking_executor_details(self):
        provider = ExternalCommandVideoSoundProvider({
            "id": "fake_v2s",
            "label": "Fake video sound",
            "enabled": True,
            "model": "fake/model",
            "outputExtension": ".wav",
            "minDurationSeconds": 0.5,
            "maxDurationSeconds": 15,
            "argvTemplate": [
                sys.executable,
                "-c",
                "from pathlib import Path; Path(r'{output_audio}').write_bytes(b'candidate')",
            ],
        })
        registry = VideoSoundProviderRegistry()
        registry.register(provider)

        status = registry.status()

        self.assertEqual(status["defaultProviderId"], "fake_v2s")
        self.assertEqual(status["providers"][0]["providerId"], "fake_v2s")
        self.assertEqual(status["providers"][0]["model"], "fake/model")
        self.assertNotIn("argvTemplate", status["providers"][0])

    def test_external_provider_runs_argument_vector_and_materializes_project_local_output(self):
        provider = ExternalCommandVideoSoundProvider({
            "id": "fake_v2s",
            "label": "Fake video sound",
            "enabled": True,
            "model": "fake/model",
            "outputExtension": ".wav",
            "minDurationSeconds": 0.5,
            "maxDurationSeconds": 15,
            "argvTemplate": [
                sys.executable,
                "-c",
                "from pathlib import Path; Path(r'{output_audio}').write_bytes(b'candidate')",
            ],
        })
        output_dir = self.root / "project" / "audio" / "video_sound" / "job-1"
        request = VideoSoundRequest(
            job_id="job-1",
            source_video=self.video,
            output_dir=output_dir,
            prompt="Passos e impacto",
            negative_prompt="musica",
            duration_seconds=2.0,
            seed=7,
        )

        with patch("video_sound.probe_audio", return_value={"sha256": "fixture"}):
            result = provider.generate(request, lambda *_: None, threading.Event())

        self.assertTrue(result.audio_path.is_file())
        self.assertTrue(result.audio_path.is_relative_to(output_dir.resolve()))
        self.assertEqual(result.provider_id, "fake_v2s")
        self.assertEqual(result.model, "fake/model")

    def test_external_provider_configuration_rejects_shell_strings(self):
        with self.assertRaisesRegex(ValueError, "argvTemplate"):
            ExternalCommandVideoSoundProvider({
                "id": "unsafe",
                "label": "Unsafe",
                "enabled": True,
                "model": "unsafe/model",
                "outputExtension": ".wav",
                "argvTemplate": "tool --input {input_video} > {output_audio}",
            })

    def test_hostile_prompt_is_passed_as_one_literal_argument(self):
        provider = ExternalCommandVideoSoundProvider({
            "id": "literal_prompt",
            "label": "Literal prompt",
            "enabled": True,
            "model": "fake/model",
            "outputExtension": ".wav",
            "argvTemplate": [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(sys.argv[2].encode())",
                "{output_audio}",
                "{prompt}",
            ],
        })
        output_dir = self.root / "project" / "audio" / "video_sound" / "job-hostile"
        hostile = "impacto; Remove-Item C:\\nao-executar | $(tambem-nao)"
        request = VideoSoundRequest(
            job_id="job-hostile",
            source_video=self.video,
            output_dir=output_dir,
            prompt=hostile,
            duration_seconds=2.0,
        )

        with patch("video_sound.probe_audio", return_value={"sha256": "fixture"}):
            result = provider.generate(request, lambda *_: None, threading.Event())

        self.assertEqual(result.audio_path.read_text(encoding="utf-8"), hostile)

    def test_output_extension_cannot_escape_the_job_directory(self):
        with self.assertRaisesRegex(ValueError, "outputExtension"):
            ExternalCommandVideoSoundProvider({
                "id": "unsafe_extension",
                "label": "Unsafe extension",
                "enabled": True,
                "model": "unsafe/model",
                "outputExtension": "../outside.wav",
                "argvTemplate": [sys.executable, "--version"],
            })

    def test_external_provider_specs_are_loaded_additively(self):
        config = self.root / "providers.json"
        config.write_text(json.dumps({
            "version": 1,
            "providers": [{
                "id": "local_adapter",
                "label": "Local adapter",
                "enabled": False,
                "model": "future/model",
                "outputExtension": ".flac",
                "argvTemplate": ["future-tool", "--video", "{input_video}", "--out", "{output_audio}"],
            }],
        }), encoding="utf-8")

        specs = load_external_provider_specs(config)

        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["id"], "local_adapter")


if __name__ == "__main__":
    unittest.main()
