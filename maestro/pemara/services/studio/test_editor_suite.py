import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import wave
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from editor_suite import (
    AssistantApply,
    AssistantCreate,
    CaptionCreate,
    ClipCreate,
    ClipPatch,
    EditorSuite,
    EditorSuiteError,
    ProjectCreate,
    ProjectPatch,
    RenderCreate,
    VOICE_PREVIEW_MAX_CHARS,
    VoiceCreate,
)


class EditorSuiteTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe = shutil.which("ffprobe") or "ffprobe"
        self.suite = EditorSuite(
            self.root / "editor",
            ffmpeg=self.ffmpeg,
            ffprobe=self.ffprobe,
            max_upload_bytes=32 * 1024 * 1024,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _sample_video(self) -> bytes:
        target = self.root / "sample.mp4"
        subprocess.run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=#223344:s=320x240:d=0.8:r=24",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=0.8",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(target),
            ],
            check=True,
            timeout=30,
        )
        return target.read_bytes()

    def _upload(self, project_id: str):
        upload = SimpleNamespace(
            filename="Cena çã.mp4",
            content_type="video/mp4",
            file=BytesIO(self._sample_video()),
        )
        return self.suite.add_upload(project_id, upload)

    def _wait_job(self, job_id: str, timeout: float = 30.0):
        deadline = time.time() + timeout
        state = self.suite.get_job(job_id)
        while time.time() < deadline:
            state = self.suite.get_job(job_id)
            if state["status"] in {"completed", "failed", "canceled"}:
                return state
            time.sleep(0.05)
        return state

    def test_short_dictation_reuses_offline_cpu_engine(self):
        source = self.root / "dictation.wav"
        with wave.open(str(source), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\x00\x00" * 8000)
        model = self.root / "faster-whisper-base"
        model.mkdir()
        fake_transcription = {
            "language": "pt",
            "segments": [
                {"start": 0.0, "end": 0.4, "text": "Crie uma cena noturna."},
                {"start": 0.4, "end": 0.5, "text": "Sem legendas."},
            ],
        }

        with (
            patch.object(self.suite, "_resolve_offline_whisper_model", return_value=model),
            patch.object(
                self.suite,
                "_offline_whisper_models",
                return_value=[{"name": "base", "path": str(model)}],
            ),
            patch.object(self.suite, "_transcribe_cpu", return_value=fake_transcription) as transcribe,
        ):
            result = self.suite.transcribe_short_audio(source, language="pt")

        self.assertEqual(result["text"], "Crie uma cena noturna. Sem legendas.")
        self.assertEqual(result["engine"], "faster-whisper")
        self.assertEqual(result["model"], "base")
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(result["computeType"], "int8")
        self.assertGreater(result["durationSeconds"], 0)
        transcribe.assert_called_once()

    def test_short_dictation_rejects_file_without_audio_track(self):
        source = self.root / "not-audio.webm"
        source.write_bytes(b"not audio")
        with patch.object(
            self.suite,
            "_probe",
            return_value={"hasAudio": False, "duration": 0},
        ):
            with self.assertRaises(EditorSuiteError) as raised:
                self.suite.transcribe_short_audio(source)

        self.assertEqual(raised.exception.code, "INVALID_AUDIO")

    def _sample_wav(self) -> bytes:
        stream = BytesIO()
        with wave.open(stream, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(b"\x00\x00" * 16000)
        return stream.getvalue()

    def test_project_revision_and_video_reflow(self):
        project = self.suite.create_project(ProjectCreate(name="Meu filme", width=640, height=360))
        self.assertEqual(project["revision"], 1)
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        self.assertEqual(current["revision"], 2)

        first = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=current["revision"],
                track="video",
                assetId=asset["assetId"],
                sourceStart=0,
                sourceEnd=0.4,
            ),
        )
        second = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=first["revision"],
                track="video",
                assetId=asset["assetId"],
                sourceStart=0.1,
                sourceEnd=0.5,
            ),
        )
        clips = [clip for clip in second["clips"] if clip["track"] == "video"]
        self.assertEqual([clip["timelineStart"] for clip in clips], [0.0, 0.4])
        self.assertAlmostEqual(second["duration"], 0.8, places=4)

        moved = self.suite.patch_clip(
            project["projectId"],
            clips[1]["clipId"],
            ClipPatch(expectedRevision=second["revision"], order=0),
        )
        reordered = [clip for clip in moved["clips"] if clip["track"] == "video"]
        self.assertEqual(reordered[0]["clipId"], clips[1]["clipId"])
        self.assertEqual(reordered[0]["timelineStart"], 0.0)

    def test_stale_revision_is_rejected_without_mutation(self):
        project = self.suite.create_project(ProjectCreate(name="Original"))
        changed = self.suite.patch_project(
            project["projectId"],
            ProjectPatch(expectedRevision=1, name="Atualizado"),
        )
        with self.assertRaises(EditorSuiteError) as caught:
            self.suite.patch_project(
                project["projectId"],
                ProjectPatch(expectedRevision=1, name="Perdido"),
            )
        self.assertEqual(caught.exception.code, "REVISION_CONFLICT")
        self.assertEqual(self.suite.get_project(project["projectId"])["name"], "Atualizado")
        self.assertEqual(changed["revision"], 2)

    def test_trim_outside_asset_is_rejected(self):
        project = self.suite.create_project(ProjectCreate(name="Corte"))
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        with self.assertRaises(EditorSuiteError) as caught:
            self.suite.add_clip(
                project["projectId"],
                ClipCreate(
                    expectedRevision=current["revision"],
                    track="video",
                    assetId=asset["assetId"],
                    sourceStart=0,
                    sourceEnd=9,
                ),
            )
        self.assertEqual(caught.exception.code, "TRIM_OUT_OF_RANGE")

    def test_assistant_output_drops_unknown_actions(self):
        result = self.suite._validate_assistant_actions(
            {
                "reply": "Pronto",
                "summary": "Uma acao valida",
                "actions": [
                    {"type": "set_volume", "clipId": "abc", "volume": 0.5},
                    {"type": "run_command", "text": "format c:"},
                ],
            }
        )
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["type"], "set_volume")

    def test_reviewed_assistant_actions_apply_atomically_in_one_revision(self):
        project = self.suite.create_project(ProjectCreate(name="Antes"))
        result = self.suite.apply_assistant_proposal(
            project["projectId"],
            AssistantApply(
                expectedRevision=project["revision"],
                actions=[
                    {"type": "rename_project", "name": "Depois"},
                    {
                        "type": "add_text",
                        "text": "Titulo revisado",
                        "start": 1.5,
                        "duration": 2.0,
                    },
                ],
            ),
        )
        updated = result["project"]
        self.assertTrue(result["applied"])
        self.assertEqual(updated["revision"], project["revision"] + 1)
        self.assertEqual(updated["name"], "Depois")
        text_clips = [clip for clip in updated["clips"] if clip["track"] == "text"]
        self.assertEqual(len(text_clips), 1)
        self.assertEqual(text_clips[0]["text"], "Titulo revisado")

    def test_assistant_preserves_ollama_http_error_details(self):
        project = self.suite.create_project(ProjectCreate(name="Copiloto"))
        upstream = BytesIO(
            json.dumps({"error": "llama-server binary not found"}).encode("utf-8")
        )
        failure = urllib.error.HTTPError(
            "http://127.0.0.1:11434/api/chat",
            500,
            "Internal Server Error",
            None,
            upstream,
        )
        with (
            patch.object(self.suite, "_ollama_models", return_value=["qwen3.5:4b"]),
            patch("editor_suite.urllib.request.urlopen", side_effect=failure),
            self.assertRaises(EditorSuiteError) as caught,
        ):
            self.suite.assist(
                project["projectId"],
                AssistantCreate(
                    expectedRevision=project["revision"],
                    instruction="Corte o silencio.",
                ),
            )
        self.assertEqual(caught.exception.code, "OLLAMA_REQUEST_FAILED")
        self.assertEqual(caught.exception.status, 502)
        self.assertIn("llama-server binary not found", caught.exception.details)

    def test_render_job_creates_playable_export(self):
        project = self.suite.create_project(
            ProjectCreate(name="Render leve", width=320, height=240, fps=24)
        )
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        with_video = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=current["revision"],
                track="video",
                assetId=asset["assetId"],
                sourceStart=0,
                sourceEnd=0.6,
            ),
        )
        with_text = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=with_video["revision"],
                track="text",
                text="Teste Maestro",
                timelineStart=0.05,
                duration=0.4,
            ),
        )
        job = self.suite.start_render(
            project["projectId"],
            RenderCreate(expectedRevision=with_text["revision"], profile="preview", encoder="cpu"),
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            state = self.suite.get_job(job["jobId"])
            if state["status"] in {"completed", "failed", "canceled"}:
                break
            time.sleep(0.1)
        self.assertEqual(state["status"], "completed", state)
        export = state["result"]["export"]
        path, _metadata = self.suite.export_path(project["projectId"], export["exportId"])
        self.assertGreater(path.stat().st_size, 1000)
        probe = self.suite._probe(path)
        self.assertTrue(probe["hasVideo"])
        self.assertGreater(probe["duration"], 0.4)

    def test_running_job_is_marked_interrupted_after_restart(self):
        project = self.suite.create_project(ProjectCreate(name="Reinicio"))
        job = self.suite._create_job(project["projectId"], "render", "Aguardando")
        self.suite._update_job(job["jobId"], status="running", progress=42)
        restored = EditorSuite(
            self.root / "editor",
            ffmpeg=self.ffmpeg,
            ffprobe=self.ffprobe,
        )
        state = restored.get_job(job["jobId"])
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(state["progress"], 42)

    def test_offline_cpu_captions_add_timed_text_clips_atomically(self):
        project = self.suite.create_project(ProjectCreate(name="Legendas locais"))
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        fake_transcription = {
            "language": "pt",
            "segments": [
                {"start": 0.10, "end": 0.35, "text": "Primeira fala."},
                {"start": 0.40, "end": 0.72, "text": "Segunda fala."},
            ],
        }
        with (
            patch.object(
                self.suite,
                "_resolve_offline_whisper_model",
                return_value=self.root / "modelo-local",
            ),
            patch.object(
                self.suite,
                "_transcribe_cpu",
                return_value=fake_transcription,
            ) as transcribe,
        ):
            job = self.suite.start_captions(
                project["projectId"],
                CaptionCreate(
                    expectedRevision=current["revision"],
                    source="asset",
                    assetId=asset["assetId"],
                    language="pt",
                    timelineStart=2.0,
                ),
            )
            state = self._wait_job(job["jobId"])

        self.assertEqual(state["status"], "completed", state)
        self.assertEqual(state["kind"], "captions")
        self.assertEqual(state["device"], "cpu")
        self.assertEqual(state["computeType"], "int8")
        self.assertEqual(state["result"]["captionCount"], 2)
        updated = state["result"]["project"]
        captions = [
            clip
            for clip in updated["clips"]
            if clip.get("generatedBy") == "offline_cpu_asr"
        ]
        self.assertEqual([clip["text"] for clip in captions], ["Primeira fala.", "Segunda fala."])
        self.assertEqual([clip["timelineStart"] for clip in captions], [2.1, 2.4])
        self.assertEqual(updated["revision"], current["revision"] + 1)
        transcribe.assert_called_once()
        self.assertEqual(transcribe.call_args.kwargs["language"], "pt")

    def test_caption_revision_conflict_preserves_newer_project_without_partial_clips(self):
        project = self.suite.create_project(ProjectCreate(name="Conflito de legenda"))
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        transcribing = threading.Event()
        release = threading.Event()

        def fake_transcribe(*_args, **_kwargs):
            transcribing.set()
            self.assertTrue(release.wait(10))
            return {
                "language": "pt",
                "segments": [{"start": 0.0, "end": 0.5, "text": "Nao deve entrar."}],
            }

        with (
            patch.object(
                self.suite,
                "_resolve_offline_whisper_model",
                return_value=self.root / "modelo-local",
            ),
            patch.object(self.suite, "_transcribe_cpu", side_effect=fake_transcribe),
        ):
            job = self.suite.start_captions(
                project["projectId"],
                CaptionCreate(
                    expectedRevision=current["revision"],
                    source="asset",
                    assetId=asset["assetId"],
                ),
            )
            self.assertTrue(transcribing.wait(10))
            renamed = self.suite.patch_project(
                project["projectId"],
                ProjectPatch(
                    expectedRevision=current["revision"],
                    name="Projeto alterado durante ASR",
                ),
            )
            release.set()
            state = self._wait_job(job["jobId"])

        self.assertEqual(state["status"], "failed", state)
        self.assertEqual(state["error"]["code"], "REVISION_CONFLICT")
        final_project = self.suite.get_project(project["projectId"])
        self.assertEqual(final_project["revision"], renamed["revision"])
        self.assertEqual(final_project["name"], "Projeto alterado durante ASR")
        self.assertFalse(
            any(
                clip.get("generatedBy") == "offline_cpu_asr"
                for clip in final_project["clips"]
            )
        )

    def test_project_mix_can_be_captioned_with_mocked_cpu_asr(self):
        project = self.suite.create_project(ProjectCreate(name="Mix para legenda"))
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        with_video = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=current["revision"],
                track="video",
                assetId=asset["assetId"],
                sourceStart=0,
                sourceEnd=0.6,
            ),
        )
        with (
            patch.object(
                self.suite,
                "_resolve_offline_whisper_model",
                return_value=self.root / "modelo-local",
            ),
            patch.object(
                self.suite,
                "_transcribe_cpu",
                return_value={
                    "language": "pt",
                    "segments": [{"start": 0.05, "end": 0.4, "text": "Audio do projeto."}],
                },
            ),
        ):
            job = self.suite.start_captions(
                project["projectId"],
                CaptionCreate(
                    expectedRevision=with_video["revision"],
                    source="project",
                    language="pt",
                ),
            )
            state = self._wait_job(job["jobId"])

        self.assertEqual(state["status"], "completed", state)
        self.assertEqual(state["source"], "project")
        self.assertEqual(state["result"]["captionCount"], 1)
        caption = next(
            clip
            for clip in state["result"]["project"]["clips"]
            if clip.get("generatedBy") == "offline_cpu_asr"
        )
        self.assertEqual(caption["timelineStart"], 0.05)
        self.assertEqual(caption["captionSource"], "project")

    def test_voice_profile_requires_explicit_consent(self):
        upload = SimpleNamespace(
            filename="voz.wav",
            content_type="audio/wav",
            file=BytesIO(b"not-used"),
        )
        with self.assertRaises(EditorSuiteError) as caught:
            self.suite.create_voice_profile("Minha voz", False, upload)
        self.assertEqual(caught.exception.code, "VOICE_CONSENT_REQUIRED")
        self.assertTrue(upload.file.closed)

    def test_chatterbox_gpu_status_blocks_busy_comfy_without_freeing_models(self):
        calls = []

        def comfy(path, payload=None, **_kwargs):
            calls.append((path, payload))
            return {
                "queue_running": [[1, "video-em-andamento"]],
                "queue_pending": [[2, "proximo-video"]],
            }

        with (
            patch.dict(os.environ, {"MAESTRO_CHATTERBOX_DEVICE": "cuda"}, clear=False),
            patch.object(self.suite, "_comfy_voice_request", side_effect=comfy),
            patch.object(self.suite, "_free_vram_gb", return_value=24.0),
        ):
            status = self.suite._chatterbox_gpu_status(release_idle=True)

        self.assertFalse(status["ready"])
        self.assertEqual(status["reason"], "comfy_busy")
        self.assertEqual(status["comfy"]["running"], 1)
        self.assertEqual(status["comfy"]["pending"], 1)
        self.assertNotIn("/free", [path for path, _payload in calls])

    def test_explicit_chatterbox_rejects_gpu_contention_with_recovery(self):
        project = self.suite.create_project(ProjectCreate(name="GPU protegida"))
        busy = {
            "ready": False,
            "reason": "comfy_busy",
            "message": "A RTX 5090 esta ocupada pela fila de imagem ou video.",
            "freeVramGb": 7.0,
            "minimumFreeVramGb": 8.0,
            "comfy": {"reachable": True, "running": 1, "pending": 0},
        }
        with (
            patch.object(self.suite, "_chatterbox_python", return_value=r"C:\safe\python.exe"),
            patch.object(self.suite, "_chatterbox_gpu_status", return_value=busy),
        ):
            with self.assertRaises(EditorSuiteError) as caught:
                self.suite.start_voice(
                    project["projectId"],
                    VoiceCreate(
                        expectedRevision=project["revision"],
                        text="Teste protegido.",
                        engine="chatterbox",
                    ),
                )

        self.assertEqual(caught.exception.code, "VOICE_GPU_BUSY")
        self.assertEqual(caught.exception.status, 409)
        self.assertIn("Voz do Windows", caught.exception.details["recovery"])

    def test_auto_voice_falls_back_to_windows_while_gpu_is_busy(self):
        project = self.suite.create_project(ProjectCreate(name="Fallback local"))
        captured = {}
        completed = threading.Event()

        def capture(_job_id, _project_id, spec):
            captured.update(spec)
            completed.set()

        busy = {
            "ready": False,
            "reason": "comfy_busy",
            "message": "GPU ocupada.",
            "freeVramGb": 6.0,
            "minimumFreeVramGb": 8.0,
            "comfy": {"reachable": True, "running": 1, "pending": 0},
        }
        with (
            patch.object(self.suite, "_chatterbox_python", return_value=r"C:\safe\python.exe"),
            patch.object(self.suite, "_system_voices", return_value=["Microsoft Maria Desktop"]),
            patch.object(self.suite, "_chatterbox_gpu_status", return_value=busy),
            patch.object(self.suite, "_voice_worker", side_effect=capture),
        ):
            job = self.suite.start_voice(
                project["projectId"],
                VoiceCreate(
                    expectedRevision=project["revision"],
                    text="Use um caminho local seguro.",
                    engine="auto",
                ),
            )
            self.assertTrue(completed.wait(2.0))

        self.assertEqual(job["engine"], "system")
        self.assertEqual(job["engineResolution"], "auto_system_gpu_fallback")
        self.assertEqual(captured["engine"], "system")

    def test_voice_preview_is_bounded_and_never_changes_timeline(self):
        project = self.suite.create_project(ProjectCreate(name="Previa controlada"))
        captured = {}
        completed = threading.Event()

        def capture(_job_id, _project_id, spec):
            captured.update(spec)
            completed.set()

        original = " ".join(["Frase longa para comparar a interpretacao da voz."] * 20)
        with (
            patch.object(self.suite, "_system_voices", return_value=["Microsoft Maria Desktop"]),
            patch.object(self.suite, "_voice_worker", side_effect=capture),
        ):
            job = self.suite.start_voice(
                project["projectId"],
                VoiceCreate(
                    expectedRevision=project["revision"],
                    text=original,
                    engine="system",
                    mode="preview",
                    addToTimeline=True,
                ),
            )
            self.assertTrue(completed.wait(2.0))

        self.assertEqual(job["mode"], "preview")
        self.assertFalse(captured["addToTimeline"])
        self.assertLessEqual(len(captured["text"]), VOICE_PREVIEW_MAX_CHARS)
        self.assertEqual(captured["sourceTextCharacters"], len(original))
        self.assertEqual(captured["synthesizedTextCharacters"], len(captured["text"]))

    def test_elevenlabs_cloud_uses_provider_and_shared_wav_contract(self):
        project = self.suite.create_project(ProjectCreate(name="ElevenLabs cloud"))
        provider = SimpleNamespace(
            synthesize=lambda **kwargs: SimpleNamespace(
                audio_bytes=self._sample_wav(),
                metadata={
                    "provider": "elevenlabs",
                    "voiceId": kwargs["voice_id"],
                    "modelId": "eleven_v3",
                    "preset": "expressive_v3",
                    "outputFormat": "mp3_44100_128",
                    "performance": {
                        "direction": kwargs["direction"],
                        "audioTags": list(kwargs["audio_tags"]),
                    },
                    "requestId": "req_safe",
                },
            )
        )
        with (
            patch.object(
                self.suite,
                "_elevenlabs_capabilities",
                return_value={
                    "featureEnabled": True,
                    "configured": True,
                    "defaultVoiceId": "voice_123",
                },
            ),
            patch.object(self.suite, "_elevenlabs_provider", return_value=provider),
        ):
            job = self.suite.start_voice(
                project["projectId"],
                VoiceCreate(
                    expectedRevision=project["revision"],
                    text="Uma narração dramática para o projeto.",
                    engine="elevenlabs_cloud",
                    providerVoiceId="voice_123",
                    modelId="eleven_v3",
                    preset="dramatic",
                    performanceDirection="dramático e intenso",
                    speed=1.5,
                    addToTimeline=True,
                ),
            )
            state = self._wait_job(job["jobId"])

        self.assertEqual(state["status"], "completed", state)
        asset = state["result"]["asset"]
        self.assertEqual(asset["source"], "tts:elevenlabs_cloud")
        self.assertEqual(asset["mediaType"], "audio/wav")
        self.assertEqual(asset["provenance"]["voiceId"], "voice_123")
        self.assertEqual(asset["provenance"]["providerSpeed"], 1.0)
        voice_clip = next(
            clip for clip in state["result"]["project"]["clips"] if clip["track"] == "voice"
        )
        self.assertGreater(voice_clip["duration"], 0.0)
        path, _metadata = self.suite.asset_path(project["projectId"], asset["assetId"])
        self.assertEqual(path.read_bytes()[:4], b"RIFF")

    def test_capabilities_publish_elevenlabs_contract_without_enabling_cloud(self):
        expected = {
            "provider": "elevenlabs",
            "featureEnabled": False,
            "configured": False,
            "status": "disabled",
        }
        with patch.object(self.suite, "_elevenlabs_capabilities", return_value=expected):
            capabilities = self.suite.capabilities()
        self.assertEqual(capabilities["voice"]["elevenlabs"], expected)

    def test_capabilities_hide_runtime_path_and_publish_safe_voice_readiness(self):
        readiness = {
            "ready": True,
            "reason": "ready",
            "message": "GPU pronta para a voz neural local.",
            "device": "cuda",
            "freeVramGb": 29.5,
            "minimumFreeVramGb": 8.0,
            "comfy": {"reachable": True, "running": 0, "pending": 0},
        }
        with (
            patch.object(self.suite, "_chatterbox_python", return_value=r"C:\private\python.exe"),
            patch.object(self.suite, "_chatterbox_gpu_status", return_value=readiness),
            patch.object(self.suite, "_system_voices", return_value=[]),
            patch.object(self.suite, "_ollama_models", return_value=[]),
            patch.object(self.suite, "_offline_whisper_models", return_value=[]),
        ):
            capabilities = self.suite.capabilities()

        chatterbox = capabilities["voice"]["chatterbox"]
        self.assertNotIn("python", chatterbox)
        self.assertEqual(chatterbox["readiness"], readiness)
        self.assertEqual(chatterbox["previewMaxCharacters"], VOICE_PREVIEW_MAX_CHARS)

    def test_capcut_local_handoff_is_versioned_cached_and_private(self):
        project = self.suite.create_project(
            ProjectCreate(name="Pacote local", width=320, height=240, fps=24)
        )
        asset = self._upload(project["projectId"])
        current = self.suite.get_project(project["projectId"])
        with_video = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=current["revision"],
                track="video",
                assetId=asset["assetId"],
                sourceStart=0,
                sourceEnd=0.5,
            ),
        )
        with_text = self.suite.add_clip(
            project["projectId"],
            ClipCreate(
                expectedRevision=with_video["revision"],
                track="text",
                text="Legenda privada sem historico.",
                timelineStart=0.05,
                duration=0.35,
            ),
        )

        path, metadata = self.suite.capcut_local_handoff_path(
            project["projectId"],
            "editable",
        )
        self.assertTrue(path.is_file())
        self.assertFalse(metadata["cached"])
        self.assertIn(f"r{with_text['revision']}", metadata["filename"])
        self.assertTrue(path.is_relative_to(self.suite._project_dir(project["projectId"])))
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.startswith("01_video/") for name in names))
            self.assertIn("04_captions/pt-BR.srt", names)
            combined = b"\n".join(
                archive.read(name)
                for name in names
                if not name.endswith("/")
            )
            self.assertNotIn(b"migrated_prompt_history", combined)

        cached_path, cached = self.suite.capcut_local_handoff_path(
            project["projectId"],
            "editable",
        )
        self.assertEqual(cached_path, path)
        self.assertTrue(cached["cached"])

        with self.assertRaises(EditorSuiteError) as caught:
            self.suite.capcut_local_handoff_path(project["projectId"], "official")
        self.assertEqual(caught.exception.code, "INVALID_HANDOFF_MODE")

    @unittest.skipUnless(os.name == "nt", "Windows SAPI")
    def test_system_voice_generates_private_audio_and_adds_it_to_timeline(self):
        project = self.suite.create_project(ProjectCreate(name="Narracao privada"))
        job = self.suite.start_voice(
            project["projectId"],
            VoiceCreate(
                expectedRevision=project["revision"],
                text="Teste local de voz do Maestro.",
                engine="system",
                language="pt",
                speed=1.0,
                addToTimeline=True,
            ),
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            state = self.suite.get_job(job["jobId"])
            if state["status"] in {"completed", "failed", "canceled"}:
                break
            time.sleep(0.1)
        self.assertEqual(state["status"], "completed", state)
        updated = state["result"]["project"]
        voice_assets = [asset for asset in updated["assets"] if asset["source"] == "tts:system"]
        voice_clips = [clip for clip in updated["clips"] if clip["track"] == "voice"]
        self.assertEqual(len(voice_assets), 1)
        self.assertEqual(len(voice_clips), 1)
        path, metadata = self.suite.asset_path(project["projectId"], voice_assets[0]["assetId"])
        self.assertGreater(path.stat().st_size, 1000)
        self.assertEqual(metadata["mediaType"], "audio/wav")

    @unittest.skipUnless(os.name == "nt", "Windows SAPI")
    def test_system_voice_preview_creates_audio_without_touching_timeline(self):
        project = self.suite.create_project(ProjectCreate(name="Previa privada"))
        text = "Esta e uma previa curta, local e reversivel."
        job = self.suite.start_voice(
            project["projectId"],
            VoiceCreate(
                expectedRevision=project["revision"],
                text=text,
                engine="system",
                mode="preview",
                addToTimeline=True,
            ),
        )
        state = self._wait_job(job["jobId"])

        self.assertEqual(state["status"], "completed", state)
        self.assertIn("timeline nao foi alterada", state["message"])
        asset = state["result"]["asset"]
        self.assertEqual(asset["name"], "Previa de voz IA.wav")
        self.assertEqual(asset["source"], "tts:system")
        self.assertEqual(asset["provenance"]["mode"], "preview")
        self.assertEqual(asset["provenance"]["sourceTextCharacters"], len(text))
        self.assertEqual(state["result"]["project"]["clips"], [])
        path, metadata = self.suite.asset_path(project["projectId"], asset["assetId"])
        self.assertEqual(path.read_bytes()[:4], b"RIFF")
        self.assertEqual(metadata["mediaType"], "audio/wav")

    @unittest.skipUnless(os.name == "nt", "Windows SAPI")
    def test_canceling_system_voice_stops_process_without_persisting_asset(self):
        project = self.suite.create_project(ProjectCreate(name="Cancelar narracao"))
        stopped = threading.Event()

        class BlockingProcess:
            def __init__(self, *_args, **_kwargs):
                self.returncode = None

            def poll(self):
                return self.returncode

            def terminate(self):
                self.returncode = -15
                stopped.set()

            def kill(self):
                self.terminate()

            def communicate(self, timeout=None):
                stopped.wait(timeout or 2)
                return "", "cancelado"

        with (
            patch.object(self.suite, "_system_voices", return_value=["Microsoft Maria Desktop"]),
            patch.object(self.suite, "_chatterbox_python", return_value=""),
            patch("editor_suite.subprocess.Popen", BlockingProcess),
        ):
            job = self.suite.start_voice(
                project["projectId"],
                VoiceCreate(
                    expectedRevision=project["revision"],
                    text="Esta narracao deve ser cancelada.",
                    engine="system",
                ),
            )
            deadline = time.time() + 3
            while time.time() < deadline:
                with self.suite.process_lock:
                    if job["jobId"] in self.suite.processes:
                        break
                time.sleep(0.01)
            self.suite.cancel_job(job["jobId"])
            state = self._wait_job(job["jobId"], timeout=5)

        self.assertEqual(state["status"], "canceled", state)
        self.assertTrue(stopped.is_set())
        current = self.suite.get_project(project["projectId"])
        self.assertFalse(current["assets"])
        self.assertFalse(current["clips"])

    def test_project_ids_cannot_escape_storage_root(self):
        with self.assertRaises(EditorSuiteError):
            self.suite.get_project("../../fora")
        self.assertFalse((self.root / "fora").exists())


if __name__ == "__main__":
    unittest.main()
