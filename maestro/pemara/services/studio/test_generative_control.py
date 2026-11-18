import asyncio
import hashlib
import json
import os
from io import BytesIO
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main
import levo_music
from generative_jobs import GenerativeJobStore
from video_projects import create_project, list_takes, set_take_generation_state
from video_sound import VideoSoundProvider, VideoSoundProviderRegistry, VideoSoundResult


def _spec(mode="image"):
    return {
        "prompt": "teste controlado",
        "mode": mode,
        "model": "model-test",
        "negative": "",
        "lora": "",
        "lora_strength": 0.0,
        "width": 1024,
        "height": 1024,
        "steps": 8,
        "guidance": 1.0,
        "seed": -1,
        "frames": 25,
        "fps": 24.0,
        "provider": "",
        "duration": 4.0,
        "prompt_influence": 0.5,
        "loop": False,
        "camera_pose": "",
        "camera_speed": 0.8,
        "video_conditioning_profile": "identity_locked",
    }


class GenerativeControlTest(unittest.TestCase):
    def test_fast_h3_readiness_requires_checkpoint_and_live_unet_option(self):
        live_schema = {
            "UNETLoader": {
                "input": {
                    "required": {
                        "unet_name": [[main._FAST_H3_MODEL_NAME, main.MINIMAX_H3_MODEL_NAME]],
                    },
                },
            },
        }
        with (
            patch.object(
                main,
                "_h3_workflow_status",
                side_effect=lambda *_args, **_kwargs: {"capabilities": {"fastH3Ready": True}},
            ),
            patch.object(main, "_comfy_request", return_value=live_schema),
        ):
            ready = main._h3_workflow_status_live(comfy_online=True)
        self.assertTrue(ready["capabilities"]["fastH3FileReady"])
        self.assertTrue(ready["capabilities"]["fastH3NodeListed"])
        self.assertTrue(ready["capabilities"]["fastH3Ready"])

        stale_schema = {
            "UNETLoader": {
                "input": {
                    "required": {"unet_name": [[main.MINIMAX_H3_MODEL_NAME]]},
                },
            },
        }
        with (
            patch.object(
                main,
                "_h3_workflow_status",
                side_effect=lambda *_args, **_kwargs: {"capabilities": {"fastH3Ready": True}},
            ),
            patch.object(main, "_comfy_request", return_value=stale_schema),
        ):
            stale = main._h3_workflow_status_live(comfy_online=True)
        self.assertTrue(stale["capabilities"]["fastH3FileReady"])
        self.assertFalse(stale["capabilities"]["fastH3NodeListed"])
        self.assertFalse(stale["capabilities"]["fastH3Ready"])

    def test_fast_h3_normalization_preserves_requested_audio(self):
        request = {
            "prompt": "Uma rua cinematográfica ao amanhecer",
            "mode": "video",
            "engine_id": "minimax_h3",
            "model": main.MINIMAX_H3_MODEL_NAME,
            "h3_model_variant": "fasth3_8step_v2",
            "h3_quality_profile": "h3_production",
            "h3_orientation": "portrait",
            "width": 1088,
            "height": 608,
            "steps": 8,
            "enable_minimax_h3_native_audio": True,
        }
        normalized = main._normalize_generative_job_spec(request)
        self.assertEqual(normalized["width"], 608)
        self.assertEqual(normalized["height"], 1088)
        self.assertEqual(normalized["steps"], 8)
        self.assertTrue(normalized["enable_minimax_h3_native_audio"])

    def test_fast_h3_rejects_non_t2v_creative_controls(self):
        request = {
            "prompt": "Uma rua cinematográfica ao amanhecer",
            "mode": "video",
            "engine_id": "minimax_h3",
            "model": main.MINIMAX_H3_MODEL_NAME,
            "h3_model_variant": "fasth3_8step_v2",
            "h3_quality_profile": "h3_production",
            "width": 1088,
            "height": 608,
            "steps": 8,
            "creative_motion_request": {"action": "walk"},
        }
        with self.assertRaisesRegex(ValueError, "FastH3 aceita texto e primeiro/ultimo quadro"):
            main._normalize_generative_job_spec(request)

    def test_manual_photo_video_queues_without_optional_anchor_analysis(self):
        for engine_id in ('minimax_h3',):
            spec = _spec('video')
            spec['engine_id'] = engine_id
            engine = SimpleNamespace(id=engine_id, readiness=lambda: {'production_ready': True})
            registry = SimpleNamespace(get=lambda _: engine)
            with patch.object(main, '_normalize_generative_job_spec', return_value=spec), patch.object(main, '_video_engine_registry_live', return_value=registry), patch.object(main, '_require_compiled_anchor_receipt') as receipt, patch.object(main, '_run_generative', return_value={'ok': True, 'mode': 'video', 'outputs': []}) as run:
                job_id = main._start_generative_job(spec, base_bytes=b'photo-fixture', base_name='photo.png')
                job = self.wait_terminal(job_id)
                self.assertEqual(job['status'], 'done', job.get('error'))
                receipt.assert_not_called()
                self.assertEqual(run.call_args.kwargs['base_image_bytes'], b'photo-fixture')
                self.assertEqual(run.call_args.kwargs['engine_id'], engine_id)

    def test_photo_video_ignores_obsolete_external_receipt(self):
        spec = _spec('video')
        spec.update(engine_id='minimax_h3', anchor_contract_id='expired', prompt_compiler_version='v1')
        engine = SimpleNamespace(id='minimax_h3', readiness=lambda: {'production_ready': True})
        with patch.object(main, '_normalize_generative_job_spec', return_value=spec), patch.object(main, '_video_engine_registry_live', return_value=SimpleNamespace(get=lambda _: engine)), patch.object(main, '_require_compiled_anchor_receipt', side_effect=AssertionError('External receipt removed')), patch.object(main, '_run_generative', return_value={'ok': True, 'mode': 'video', 'outputs': []}) as run:
            job_id = main._start_generative_job(spec, base_bytes=b'photo-fixture', base_name='photo.png')
            self.assertEqual(self.wait_terminal(job_id)['status'], 'done')
            self.assertEqual(run.call_args.kwargs['base_image_bytes'], b'photo-fixture')

    def test_semantic_review_uses_local_worker_and_honors_gpu_pause(self):
        spec = _spec('semantic_review')
        spec['engine_id'] = 'ltx_2_5'
        with patch.object(main, '_video_generation_paused', return_value=False), patch('creative_os.semantic_critic.execute', return_value={'ok': True}) as execute:
            result = main._run_generative(**spec, base_image_bytes=b'sheet')
            self.assertTrue(result['ok'])
            self.assertEqual(execute.call_args.args[2], b'sheet')
        with patch.object(main, '_video_generation_paused', return_value=True), patch('creative_os.semantic_critic.execute') as execute:
            with self.assertRaises(RuntimeError): main._run_generative(**spec, base_image_bytes=b'sheet')
            execute.assert_not_called()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.store = GenerativeJobStore(root / "jobs.json")
        from creative_os.integration import archive_workflow
        self.patches = [
            patch.object(main, "_GEN_JOB_STORE", self.store),
            patch.object(main, "_GEN_JOB_INPUT_ROOT", root / "inputs"),
            patch.object(main, "_GPU_LEASE_REGISTRY", main.GpuLeaseRegistry(root / "gpu_lease.json")),
            patch.object(main, "_prepare_render_focus", return_value={"ok": True, "test_fixture": True}),
            patch("creative_os.integration.archive_workflow", side_effect=lambda _root, prompt, graph, **kwargs: archive_workflow(root / "workflows", prompt, graph, **kwargs)),
        ]
        for item in self.patches:
            item.start()
        main._ACTIVE_GEN_JOBS.clear()
        with main._VIDEO_TAKE_QUEUE_CONDITION:
            main._VIDEO_TAKE_QUEUE.clear()
            main._VIDEO_TAKE_ACTIVE_JOB_ID = ""
            main._VIDEO_TAKE_QUEUE_CONDITION.notify_all()
        with main._RECOVERED_UPSCALE_ORDER_CONDITION:
            main._RECOVERED_UPSCALE_ORDER.clear()
            main._RECOVERED_UPSCALE_ORDER_CONDITION.notify_all()
        main._VIDEO_UPSCALE_GATE.clear()

    def tearDown(self):
        deadline = time.time() + 2
        while main._ACTIVE_GEN_JOBS and time.time() < deadline:
            time.sleep(0.01)
        main._ACTIVE_GEN_JOBS.clear()
        with main._VIDEO_TAKE_QUEUE_CONDITION:
            main._VIDEO_TAKE_QUEUE.clear()
            main._VIDEO_TAKE_ACTIVE_JOB_ID = ""
            main._VIDEO_TAKE_QUEUE_CONDITION.notify_all()
        with main._RECOVERED_UPSCALE_ORDER_CONDITION:
            main._RECOVERED_UPSCALE_ORDER.clear()
            main._RECOVERED_UPSCALE_ORDER_CONDITION.notify_all()
        main._VIDEO_UPSCALE_GATE.clear()
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_video_engine_readiness_exposes_only_h3(self):
        readiness = main._video_engine_readiness(comfy_online=False)

        self.assertEqual(set(readiness), {"minimax_h3"})
        self.assertFalse(readiness["minimax_h3"])

    def test_video_sound_job_uses_selected_provider_and_stops_at_human_review(self):
        root = Path(self.temp_dir.name) / "projects"
        project = root / "film"
        project.mkdir(parents=True)
        source = project / "approved.mp4"
        source.write_bytes(b"approved-video")

        class FakeProvider(VideoSoundProvider):
            provider_id = "fake_v2s"
            label = "Fake V2S"
            model = "fake/model"

            def status(self):
                return {
                    "providerId": self.provider_id,
                    "label": self.label,
                    "model": self.model,
                    "configured": True,
                    "device": "test",
                }

            def generate(self, request, progress_cb, cancel_event):
                request.output_dir.mkdir(parents=True, exist_ok=True)
                audio = request.output_dir / "candidate.wav"
                audio.write_bytes(b"candidate")
                progress_cb(90, "candidate ready")
                return VideoSoundResult(
                    provider_id=self.provider_id,
                    model=self.model,
                    audio_path=audio,
                    source_video_sha256="abc123",
                    qc={"durationSeconds": 2.0, "sampleRate": 48000, "channels": 2},
                    generation={"device": "test"},
                )

        registry = VideoSoundProviderRegistry()
        registry.register(FakeProvider())
        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", root),
            patch.object(main, "_VIDEO_SOUND_REGISTRY", registry),
            patch.object(main, "_get_take_status", return_value="APPROVED"),
            patch.object(main, "_get_take_preview_path", return_value=source),
            patch.object(main, "_probe_video_sound_duration", return_value=2.0),
            patch.object(main, "_register_take_audio_candidate", return_value={"audioCandidateNeedsReview": True}) as register,
        ):
            started = main._start_take_video_sound_job("film", "01", {
                "providerId": "fake_v2s",
                "prompt": "Passos e impacto sincronizados",
            })
            job = self.wait_terminal(started["jobId"])

        self.assertEqual(job["status"], "done")
        self.assertEqual(job["result"]["status"], "PENDING_HUMAN_REVIEW")
        self.assertTrue(job["human_review_required"])
        self.assertFalse(job["auto_attach"])
        register.assert_called_once()

    def test_video_engine_readiness_requires_comfy_for_minimax_h3(self):
        ltx = {
            "ready": False,
            "hq_profile": {"ready": False},
        }
        with patch.object(main, "_minimax_h3_kit_ready", return_value=True):
            readiness = main._video_engine_readiness(
                comfy_online=False,
                ltx=ltx,
                wan_ready=False,
                wan_reserve_enabled=False,
            )

        self.assertFalse(readiness["minimax_h3"])

    def wait_terminal(self, job_id):
        deadline = time.time() + 3
        while time.time() < deadline:
            job = self.store.get(job_id)
            if job and job.get("status") in {"done", "error", "canceled"}:
                return job
            time.sleep(0.01)
        self.fail("job nao terminou durante o teste")

    def test_mova_releases_idle_comfy_vram_before_starting(self):
        calls = []

        def fake_request(path, payload=None, timeout=30):
            calls.append((path, payload, timeout))
            if path == "/queue":
                return {"queue_running": [], "queue_pending": []}
            return {}

        with patch.object(main, "_comfy_request", side_effect=fake_request):
            main._prepare_comfy_gpu_for_mova()

        self.assertEqual(calls[0][0], "/queue")
        self.assertEqual(calls[1][0], "/free")
        self.assertEqual(
            calls[1][1],
            {"unload_models": True, "free_memory": True},
        )

    def test_mova_refuses_to_compete_with_comfy_queue(self):
        with patch.object(
            main,
            "_comfy_request",
            return_value={"queue_running": [[1]], "queue_pending": []},
        ):
            with self.assertRaisesRegex(RuntimeError, "aguardando GPU"):
                main._prepare_comfy_gpu_for_mova()

    def test_mova_can_wait_for_comfy_queue_without_interrupting_it(self):
        calls = []
        queues = iter(
            [
                {"queue_running": [[1]], "queue_pending": []},
                {"queue_running": [], "queue_pending": []},
            ]
        )

        class FakeCancelEvent:
            def __init__(self):
                self.waits = []

            def is_set(self):
                return False

            def wait(self, timeout):
                self.waits.append(timeout)

        event = FakeCancelEvent()

        def fake_request(path, payload=None, timeout=30):
            calls.append((path, payload, timeout))
            if path == "/queue":
                return next(queues)
            return {}

        with patch.object(main, "_comfy_request", side_effect=fake_request):
            main._prepare_comfy_gpu_for_mova(
                cancel_event=event,
                wait_for_queue=True,
            )

        self.assertEqual(event.waits, [5.0])
        self.assertEqual([call[0] for call in calls], ["/queue", "/queue", "/free"])

    def test_dynamic_vram_recovery_unloads_only_when_comfy_is_idle(self):
        calls = []
        stats_calls = 0

        def fake_request(path, payload=None, timeout=30):
            nonlocal stats_calls
            calls.append((path, payload, timeout))
            if path == "/queue":
                return {"queue_running": [], "queue_pending": []}
            if path == "/system_stats":
                stats_calls += 1
                free_vram = 1024**3 if stats_calls == 1 else 12 * 1024**3
                return {"devices": [{"vram_free": free_vram}]}
            return {}

        with (
            patch.object(main, "_comfy_request", side_effect=fake_request),
            patch.object(main._t, "sleep") as sleep,
        ):
            main._recover_comfy_dynamic_vram()

        self.assertEqual(calls[0][0], "/queue")
        self.assertEqual(
            calls[1],
            ("/free", {"unload_models": True, "free_memory": True}, 15),
        )
        self.assertEqual(stats_calls, 2)
        sleep.assert_called_once_with(1.0)

    def test_dynamic_vram_recovery_refuses_to_unload_an_active_queue(self):
        with patch.object(
            main,
            "_comfy_request",
            return_value={"queue_running": [[1, "other-prompt"]], "queue_pending": []},
        ):
            with self.assertRaisesRegex(RuntimeError, "outra tarefa"):
                main._recover_comfy_dynamic_vram()

    def test_unauthorized_video_engine_is_blocked_before_comfyui(self):
        spec = _spec("video")
        spec["model"] = "wan2.2_i2v_high_noise_14B_fp16.safetensors"
        with patch.dict(os.environ, {
            "STUDIO_ENABLE_UNAUTHORIZED_VIDEO_ENGINES": "0",
            "STUDIO_ENABLE_WAN_RESERVE": "0",
        }):
            with self.assertRaisesRegex(
                main._VideoEngineError,
                "Escolha MiniMax H3",
            ):
                main._run_generative(**spec)

    def test_wan_remains_blocked_even_with_legacy_switches(self):
        model = "wan2.2_i2v_high_noise_14B_fp16.safetensors"
        with patch.dict(os.environ, {
            "STUDIO_ENABLE_UNAUTHORIZED_VIDEO_ENGINES": "0",
            "STUDIO_ENABLE_WAN_RESERVE": "0",
        }):
            self.assertFalse(main._video_engine_authorized(model))
        with patch.dict(os.environ, {
            "STUDIO_ENABLE_UNAUTHORIZED_VIDEO_ENGINES": "1",
            "STUDIO_ENABLE_WAN_RESERVE": "1",
        }):
            self.assertFalse(main._video_engine_authorized(model))

    def test_wan_animate_move_is_not_an_authorized_take_engine(self):
        self.assertFalse(main._video_engine_authorized(main.WAN22_ANIMATE_MODEL_NAME))
        with self.assertRaisesRegex(main._VideoEngineError, "MiniMax H3"):
            main._video_take_model_for_spec({
                "generationProfile": main.WAN22_ANIMATE_PROFILE,
            })

    def test_job_input_is_persisted_and_traversal_is_rejected(self):
        metadata = main._persist_job_input("abc123", "base", b"image-bytes", "foto.png")
        data, name = main._load_job_input(metadata)
        self.assertEqual(data, b"image-bytes")
        self.assertEqual(name, "foto.png")
        with self.assertRaises(ValueError):
            main._load_job_input({"path": "../outside.png", "original_name": "outside.png"})

    def test_upload_reader_stops_at_the_configured_limit(self):
        class FakeUpload:
            def __init__(self, payload):
                self.payload = payload
                self.offset = 0
                self.closed = False

            async def read(self, size):
                chunk = self.payload[self.offset:self.offset + size]
                self.offset += len(chunk)
                return chunk

            async def close(self):
                self.closed = True

        allowed = FakeUpload(b"12345678")
        self.assertEqual(
            asyncio.run(main._read_upload_bounded(allowed, "Imagem", max_bytes=8)),
            b"12345678",
        )
        self.assertTrue(allowed.closed)

        oversized = FakeUpload(b"123456789")
        with self.assertRaisesRegex(ValueError, "excede o limite"):
            asyncio.run(main._read_upload_bounded(oversized, "Imagem", max_bytes=8))
        self.assertTrue(oversized.closed)
        self.assertEqual(oversized.offset, 9)

    def test_media_upload_uses_a_safe_unique_path(self):
        root = Path(self.temp_dir.name) / "media"
        root.mkdir()
        upload = SimpleNamespace(
            filename=r"..\..\video perigoso?.mp4",
            file=BytesIO(b"media-bytes"),
        )
        with patch.object(main, "PASTA", str(root)):
            path, safe_name = main._save_media_upload(upload, "video", max_bytes=32)

        saved = Path(path).resolve()
        self.assertIn(root.resolve(), saved.parents)
        self.assertEqual(safe_name, "video perigoso_.mp4")
        self.assertEqual(saved.read_bytes(), b"media-bytes")
        self.assertTrue(upload.file.closed)

    def test_oversized_media_upload_is_removed(self):
        root = Path(self.temp_dir.name) / "media-large"
        root.mkdir()
        upload = SimpleNamespace(filename="grande.mov", file=BytesIO(b"123456789"))
        with patch.object(main, "PASTA", str(root)):
            with self.assertRaises(main.MediaUploadTooLarge):
                main._save_media_upload(upload, "video", max_bytes=8)

        self.assertEqual(list(root.iterdir()), [])
        self.assertTrue(upload.file.closed)

    def test_media_outputs_are_unique_for_equal_source_names(self):
        root = Path(self.temp_dir.name) / "media-output"
        root.mkdir()
        with patch.object(main, "PASTA", str(root)):
            first = Path(main._unique_media_output("take", "mp4", "editado"))
            second = Path(main._unique_media_output("take", "mp4", "editado"))

        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, root)
        self.assertEqual(first.suffix, ".mp4")
        self.assertIn("take_editado_", first.name)

    def test_completed_job_keeps_retry_spec_and_actions(self):
        fake_result = {"ok": True, "mode": "image", "outputs": []}
        with patch.object(main, "_run_generative", return_value=fake_result):
            job_id = main._start_generative_job(_spec())
            job = self.wait_terminal(job_id)

        decorated = main._job_with_actions(job)
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["request_spec"]["prompt"], "teste controlado")
        self.assertTrue(decorated["actions"]["can_retry"])
        self.assertFalse(decorated["actions"]["can_cancel"])

    def test_live_job_can_be_canceled_without_waiting_for_completion(self):
        started = threading.Event()

        def fake_run(**kwargs):
            started.set()
            while True:
                kwargs["progress_cb"](20, "trabalhando")
                time.sleep(0.01)

        with (
            patch.object(main, "_run_generative", side_effect=fake_run),
            patch.object(main, "_is_internal_request", return_value=True),
        ):
            job_id = main._start_generative_job(_spec())
            self.assertTrue(started.wait(1))
            response = asyncio.run(
                main.generative_job_cancel(SimpleNamespace(headers={}, client=None), job_id)
            )
            self.assertEqual(response["status"], "canceling")
            job = self.wait_terminal(job_id)

        self.assertEqual(job["status"], "canceled")

    def test_inactive_interrupted_upscale_cancel_reconciles_the_take(self):
        self.store.update(
            "upscale-orphan",
            status="interrupted",
            project_id="filme",
            take_id="S10A",
            job_kind="video_upscale",
        )
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(
                main,
                "_get_take_upscale_spec",
                return_value={"lastJobId": "upscale-orphan"},
            ),
            patch.object(main, "_set_take_upscale_state") as set_take_state,
        ):
            response = asyncio.run(
                main.generative_job_cancel(
                    SimpleNamespace(headers={}, client=None),
                    "upscale-orphan",
                )
            )

        self.assertEqual(response["status"], "canceled")
        self.assertTrue(response["take_reconciled"])
        self.assertEqual(self.store.get("upscale-orphan")["status"], "canceled")
        self.assertEqual(set_take_state.call_args.kwargs["status"], "CANCELED")

    def test_upscale_worker_terminalizes_job_even_when_take_state_write_fails(self):
        job_id = "upscale-state-write-failure"
        self.store.update(
            job_id,
            status="queued",
            project_id="filme",
            take_id="S10A",
            job_kind="video_upscale",
        )
        spec = {
            "workDir": Path(self.temp_dir.name) / "upscale-work",
        }
        spec["contentKind"] = "animation"
        with (
            patch.object(main, "_wait_for_comfy_idle_before_upscale", return_value=None),
            patch.object(main, "_set_take_upscale_state", side_effect=OSError("disk full")),
        ):
            main._launch_take_upscale_worker(job_id, "filme", "S10A", spec)
            job = self.wait_terminal(job_id)

        self.assertEqual(job["status"], "error")
        self.assertIn("disk full", job["error"])

    def test_upscale_command_uses_required_seedvr2_rife_dlss_profile(self):
        root = Path(self.temp_dir.name)
        source = root / "take.mp4"
        source.write_bytes(b"source")
        command = main._build_upscale_command(
            {
                "contentKind": "animation",
                "source": source,
                "outputDir": root / "output",
                "workDir": root / "work",
                "name": "take_01",
            },
            source_sha256="A" * 64,
            dry_run=False,
        )

        self.assertIn("--profile", command)
        self.assertTrue(
            any(value.endswith("seedvr2_3b_rife_exact60_dlss5_foley_v1_1080p.json") for value in command)
        )
        self.assertIn("--expected-sha256", command)
        self.assertEqual(command[command.index("--chunk-size") + 1], "17")
        self.assertEqual(command[command.index("--per-batch") + 1], "1")
        self.assertNotIn("--upscale-model", command)
        self.assertFalse(any("animevideov3" in value.lower() for value in command))

    def test_upscale_command_uses_portrait_profile_for_vertical_final(self):
        root = Path(self.temp_dir.name)
        source = root / "take-vertical.mp4"
        source.write_bytes(b"source")
        command = main._build_upscale_command(
            {
                "contentKind": "animation",
                "source": source,
                "outputDir": root / "output",
                "workDir": root / "work",
                "name": "take_01",
                "targetWidth": 1080,
                "targetHeight": 1920,
            },
            source_sha256="A" * 64,
            dry_run=False,
        )

        profile = command[command.index("--profile") + 1]
        self.assertTrue(
            profile.endswith("seedvr2_3b_rife_exact60_dlss5_foley_v1_1080p_vertical.json")
        )

    def test_live_action_and_mixed_select_lanczos_profile_and_pass_kind_to_worker(self):
        root = Path(self.temp_dir.name)
        for kind in ('live_action','mixed'):
            spec={'source':root/'native.mp4','outputDir':root/'output',
                  'workDir':root/'work','name':'take','contentKind':kind,
                  'targetWidth':1080,'targetHeight':1920}
            command=main._build_upscale_command(spec,source_sha256='A'*64,dry_run=True)
            profile=command[command.index('--profile')+1]
            self.assertTrue(profile.endswith('lanczos_nvenc_rife_exact60_dlss5_actor_protected_v1_1080p_vertical.json'))
            self.assertEqual(command[command.index('--content-kind')+1],kind)
            self.assertFalse(any('seedvr2' in item.lower() for item in command))
        spec['contentKind']='unknown'
        with self.assertRaises(ValueError):
            main._build_upscale_command(spec,source_sha256='A'*64,dry_run=True)

    def test_upscale_progress_uses_collected_frames_not_blend_percentage(self):
        self.assertIsNone(
            main._upscale_frame_progress("75% neural + 25% Lanczos")
        )
        self.assertEqual(
            main._upscale_frame_progress("collected 120/480 neural-upscale frames"),
            (120, 480, 25.0),
        )

    def _write_required_receipt_fixture(self, candidate):
        digest = main._sha256_file(candidate).lower()
        main._dlss5.receipt_path(candidate).write_text(json.dumps({"profile": main._dlss5.PROFILE, "technical_pass": True, "output_sha256": digest}), encoding="utf-8")
        main._required_upscale.receipt_path(candidate).write_text(json.dumps({"pipeline_version": main._required_upscale.PIPELINE, "technical_pass": True, "output_sha256": digest}), encoding="utf-8")

    def test_upscale_cache_requires_exact_v2_fingerprint_hash_and_no_rejection(self):
        root = Path(self.temp_dir.name)
        source = root / "take.mp4"
        source.write_bytes(b"source-video")
        output_dir = root / "output"
        output_dir.mkdir()
        candidate = output_dir / "take_01_review_candidate_1920x1080_24fps_aaaaaaaaaaaa.mp4"
        candidate.write_bytes(b"candidate-video")
        self._write_required_receipt_fixture(candidate)
        fingerprint = "A" * 64
        source_sha = main._sha256_file(source)
        sidecar = candidate.with_suffix(".json")
        payload = {
            "schema_version": "2.0",
            "type": "pemara_hd_review_candidate_result",
            "pipeline_version": "seedvr2_3b_rife_exact60_dlss5_foley_v1",
            "processing_fingerprint": fingerprint,
            "fingerprint": {
                "algorithm": "SHA-256",
                "value": fingerprint,
                "inputs": {
                    "source_sha256": source_sha,
                    "profile": {"profile_id": "seedvr2_3b_rife_exact60_dlss5_foley_v1_1080p"},
                },
            },
            "source_sha256": source_sha,
            "candidate": str(candidate.resolve()),
            "candidate_sha256": main._sha256_file(candidate),
            "qc_status": "technical_pass_visual_qc_pending",
            "validation_status": "technical_pass_visual_qc_pending",
            "technical_validation": {"status": "technical_pass"},
            "human_approval": {"status": "pending"},
        }
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
        spec = {
            "source": source,
            "outputDir": output_dir,
            "workDir": root / "work",
            "name": "take_01",
        }
        spec["contentKind"] = "animation"

        reused, reused_sidecar = main._find_reusable_upscale_candidate(
            spec,
            expected_fingerprint=fingerprint,
            expected_source_sha256=source_sha,
        )
        self.assertEqual(reused, candidate.resolve())
        self.assertEqual(reused_sidecar, sidecar.resolve())

        payload["human_approval"] = {"status": "rejected"}
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
        rejected, rejected_sidecar = main._find_reusable_upscale_candidate(
            spec,
            expected_fingerprint=fingerprint,
            expected_source_sha256=source_sha,
        )
        self.assertIsNone(rejected)
        self.assertIsNone(rejected_sidecar)

        payload["human_approval"] = {"status": "pending"}
        payload["schema_version"] = "1.0"
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
        legacy, legacy_sidecar = main._find_reusable_upscale_candidate(
            spec,
            expected_fingerprint=fingerprint,
            expected_source_sha256=source_sha,
        )
        self.assertIsNone(legacy)
        self.assertIsNone(legacy_sidecar)

    def test_upscale_process_reuses_valid_v2_cache_without_starting_gpu_process(self):
        root = Path(self.temp_dir.name)
        source = root / "take.mp4"
        source.write_bytes(b"source-video")
        output_dir = root / "output"
        output_dir.mkdir()
        work_dir = root / "work"
        work_dir.mkdir()
        candidate = output_dir / "take_01_review_candidate_1920x1080_24fps_bbbbbbbbbbbb.mp4"
        candidate.write_bytes(b"candidate-video")
        self._write_required_receipt_fixture(candidate)
        fingerprint = "B" * 64
        source_sha = main._sha256_file(source)
        sidecar = candidate.with_suffix(".json")
        sidecar.write_text(
            json.dumps({
                "schema_version": "2.0",
                "type": "pemara_hd_review_candidate_result",
                "pipeline_version": "seedvr2_3b_rife_exact60_dlss5_foley_v1",
                "processing_fingerprint": fingerprint,
                "fingerprint": {
                    "algorithm": "SHA-256",
                    "value": fingerprint,
                    "inputs": {
                        "source_sha256": source_sha,
                        "profile": {"profile_id": "seedvr2_3b_rife_exact60_dlss5_foley_v1_1080p"},
                    },
                },
                "source_sha256": source_sha,
                "candidate": str(candidate.resolve()),
                "candidate_sha256": main._sha256_file(candidate),
                "qc_status": "technical_pass_visual_qc_pending",
                "technical_validation": {"status": "technical_pass"},
                "human_approval": {"status": "pending"},
            }),
            encoding="utf-8",
        )
        job_id = "cache-only-job"
        self.store.update(
            job_id,
            status="running",
            project_id="filme",
            take_id="01",
            job_kind="video_upscale",
        )
        spec = {
            "source": source,
            "outputDir": output_dir,
            "workDir": work_dir,
            "name": "take_01",
            "upscaleAttempt": 2,
        }
        spec["contentKind"] = "animation"
        current = {
            "lastJobId": job_id,
            "upscaleAttempt": 2,
            "source": source,
        }

        with (
            patch.object(main, "_get_take_upscale_spec", return_value=current),
            patch.object(main, "_run_upscale_plan", return_value=(fingerprint, 1024)),
            patch.object(main, "_upscale_disk_preflight", return_value={"volumes": []}),
            patch.object(main.subprocess, "Popen") as popen,
        ):
            reused, reused_sidecar = main._run_take_upscale_process(
                job_id,
                "filme",
                "01",
                2,
                spec,
                threading.Event(),
            )

        self.assertEqual(reused, candidate.resolve())
        self.assertEqual(reused_sidecar, sidecar.resolve())
        popen.assert_not_called()
        self.assertTrue(self.store.get(job_id)["upscale_cache_reused"])

    def test_upscale_disk_preflight_reports_retryable_shortage_before_gpu(self):
        root = Path(self.temp_dir.name)
        source = root / "take.mp4"
        source.write_bytes(b"x" * 1024)
        output_dir = root / "output"
        work_dir = root / "work"
        output_dir.mkdir()
        work_dir.mkdir()
        spec = {
            "source": source,
            "outputDir": output_dir,
            "workDir": work_dir,
        }
        spec["contentKind"] = "animation"
        usage = SimpleNamespace(total=20 * 1024**3, used=20 * 1024**3 - 1, free=1)

        with patch.object(main.shutil, "disk_usage", return_value=usage):
            with self.assertRaises(main.RecoverableUpscaleError) as raised:
                main._upscale_disk_preflight(spec, required_work_bytes=1024)

        self.assertEqual(raised.exception.code, "UPSCALE_DISK_SPACE")
        self.assertIn("repita o job", str(raised.exception))

    def test_upscale_cleanup_uses_sidecar_base_stem_for_attempt_publication(self):
        root = Path(self.temp_dir.name)
        work_dir = root / "work"
        base_stem = "take_01_review_candidate_1920x1080_24fps_abc123"
        work_root = work_dir / base_stem
        work_root.mkdir(parents=True)
        (work_root / "frame.png").write_bytes(b"frame")
        candidate = root / f"{base_stem}_attempt02.mp4"
        candidate.write_bytes(b"candidate")
        sidecar = candidate.with_suffix(".json")
        sidecar.write_text(
            json.dumps({"candidate_stem": base_stem}),
            encoding="utf-8",
        )

        main._cleanup_completed_upscale_work(
            {"workDir": work_dir},
            candidate,
            sidecar,
        )

        self.assertFalse(work_root.exists())
        self.assertTrue(candidate.is_file())
        self.assertTrue(sidecar.is_file())

    def test_upscale_attempt_guard_rejects_stale_attempt_without_gpu(self):
        root = Path(self.temp_dir.name)
        source = root / "take.mp4"
        source.write_bytes(b"source")
        self.store.update(
            "job-current",
            status="queued",
            project_id="filme",
            take_id="01",
            job_kind="video_upscale",
        )
        current = {
            "lastJobId": "job-current",
            "upscaleAttempt": 4,
            "source": source,
        }
        with patch.object(main, "_get_take_upscale_spec", return_value=current):
            checked = main._assert_upscale_attempt_current(
                "job-current",
                "filme",
                "01",
                4,
                source,
            )
            self.assertEqual(checked["upscaleAttempt"], 4)
            with self.assertRaises(main.UpscaleAttemptObsolete):
                main._assert_upscale_attempt_current(
                    "job-current",
                    "filme",
                    "01",
                    3,
                    source,
                )

    def test_stale_upscale_worker_cancels_only_its_job_without_reconciling_new_attempt(self):
        job_id = "upscale-stale-attempt"
        self.store.update(
            job_id,
            status="queued",
            project_id="filme",
            take_id="S10A",
            job_kind="video_upscale",
        )
        root = Path(self.temp_dir.name)
        spec = {
            "source": root / "source.mp4",
            "outputDir": root / "output",
            "workDir": root / "work",
            "name": "take_S10A",
            "upscaleAttempt": 2,
        }
        spec["contentKind"] = "animation"
        with (
            patch.object(main, "_wait_for_comfy_idle_before_upscale", return_value=None),
            patch.object(main, "_set_take_upscale_state") as set_take_state,
            patch.object(
                main,
                "_run_take_upscale_process",
                side_effect=main.UpscaleAttemptObsolete("attempt 2 ficou obsoleto"),
            ),
        ):
            main._launch_take_upscale_worker(job_id, "filme", "S10A", spec)
            job = self.wait_terminal(job_id)

        self.assertEqual(job["status"], "canceled")
        self.assertEqual(job["error_code"], "UPSCALE_ATTEMPT_OBSOLETE")
        self.assertEqual(set_take_state.call_count, 1)
        self.assertEqual(set_take_state.call_args.kwargs["status"], "UPSCALING")

    def test_start_upscale_persists_profile_and_attempt_before_worker(self):
        root = Path(self.temp_dir.name)
        source = root / "source.mp4"
        source.write_bytes(b"source")
        spec = {
            "status": "APPROVED",
            "source": source,
            "outputDir": root / "output",
            "workDir": root / "work",
            "name": "take_01",
            "upscaleAttempt": 1,
            "nextUpscaleAttempt": 2,
        }
        spec["contentKind"] = "animation"
        with (
            patch.object(main, "_get_take_upscale_spec", return_value=spec),
            patch.object(main, "_set_take_upscale_state") as set_take_state,
            patch.object(main, "_launch_take_upscale_worker") as launch,
        ):
            started = main._start_take_upscale_job("filme", "01")

        job = self.store.get(started["jobId"])
        self.assertEqual(started["stage"], "SEEDVR2_RIFE60_DLSS5_REQUIRED_REVIEW")
        self.assertEqual(started["attempt"], 2)
        self.assertEqual(job["upscale_profile"], "seedvr2_3b_rife_exact60_dlss5_foley_v1_1080p")
        self.assertEqual(job["upscale_attempt"], 2)
        self.assertIn("SeedVR2 3B + RIFE60 + DLSS 5", job["model"])
        self.assertEqual(set_take_state.call_args.kwargs["attempt"], 2)
        launched_spec = launch.call_args.args[3]
        self.assertEqual(launched_spec["upscaleAttempt"], 2)
        self.assertEqual(launched_spec["lastJobId"], started["jobId"])

    def test_start_upscale_persists_vertical_profile_and_geometry(self):
        root = Path(self.temp_dir.name)
        source = root / "source-vertical.mp4"
        source.write_bytes(b"source")
        spec = {
            "status": "APPROVED",
            "source": source,
            "outputDir": root / "output",
            "workDir": root / "work",
            "name": "take_01",
            "upscaleAttempt": 0,
            "nextUpscaleAttempt": 1,
            "targetWidth": 1080,
            "targetHeight": 1920,
        }
        spec["contentKind"] = "animation"
        with (
            patch.object(main, "_get_take_upscale_spec", return_value=spec),
            patch.object(main, "_set_take_upscale_state"),
            patch.object(main, "_launch_take_upscale_worker") as launch,
        ):
            started = main._start_take_upscale_job("filme-vertical", "01")

        job = self.store.get(started["jobId"])
        self.assertEqual(
            job["upscale_profile"],
            "seedvr2_3b_rife_exact60_dlss5_foley_v1_1080p_vertical",
        )
        self.assertEqual((job["width"], job["height"]), (1080, 1920))
        self.assertEqual((started["width"], started["height"]), (1080, 1920))
        launched_spec = launch.call_args.args[3]
        self.assertEqual(
            (launched_spec["targetWidth"], launched_spec["targetHeight"]),
            (1080, 1920),
        )

    def test_pending_upscale_preview_has_dedicated_route_without_replacing_active_preview(self):
        candidate = Path(self.temp_dir.name) / "candidate.mp4"
        candidate.write_bytes(b"pending-review")
        request = SimpleNamespace(headers={}, client=None)
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(
                main,
                "_get_take_upscale_preview_path",
                return_value=candidate,
            ) as getter,
        ):
            response = asyncio.run(
                main.video_take_upscale_preview(request, "filme", "01")
            )

        getter.assert_called_once_with(main.VIDEO_PROJECTS_ROOT, "filme", "01")
        self.assertEqual(Path(response.path), candidate)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_recovered_upscale_fifo_holds_later_jobs_and_wan_gate(self):
        main._install_recovered_upscale_order(["S10A-job", "S10B-job"])
        released = threading.Event()

        def wait_second():
            main._wait_for_recovered_upscale_turn("S10B-job", threading.Event())
            released.set()

        waiter = threading.Thread(target=wait_second)
        waiter.start()
        time.sleep(0.05)
        self.assertFalse(released.is_set())
        self.assertTrue(main._VIDEO_UPSCALE_GATE.is_set())

        main._release_recovered_upscale_turn("S10A-job")
        self.assertTrue(released.wait(1))
        self.assertTrue(main._VIDEO_UPSCALE_GATE.is_set())

        main._release_recovered_upscale_turn("S10B-job")
        waiter.join(1)
        self.assertFalse(main._VIDEO_UPSCALE_GATE.is_set())

    def test_retry_reuses_persisted_parameters_and_input(self):
        fake_result = {"ok": True, "mode": "edit", "outputs": []}
        with (
            patch.object(main, "_run_generative", return_value=fake_result) as run,
            patch.object(main, "_is_internal_request", return_value=True),
        ):
            original_id = main._start_generative_job(
                _spec("edit"),
                base_bytes=b"persisted-image",
                base_name="origem.png",
            )
            self.wait_terminal(original_id)
            response = asyncio.run(
                main.generative_job_retry(SimpleNamespace(headers={}, client=None), original_id)
            )
            retry_id = response["job_id"]
            retried = self.wait_terminal(retry_id)

        self.assertNotEqual(retry_id, original_id)
        self.assertEqual(retried["source_job_id"], original_id)
        self.assertEqual(run.call_args_list[-1].kwargs["base_image_bytes"], b"persisted-image")
        self.assertEqual(run.call_args_list[-1].kwargs["base_image_name"], "origem.png")

    def test_comfy_prompt_cancel_is_bound_to_the_recorded_prompt(self):
        cancel_event = threading.Event()
        calls = []

        def fake_request(path, payload=None, timeout=30):
            calls.append((path, payload))
            if path == "/prompt":
                return {"prompt_id": "prompt-123"}
            if path == "/queue":
                return {"queue_running": [[1, "prompt-123", {}, {}]], "queue_pending": []}
            return {}

        def record(prompt_id):
            self.assertEqual(prompt_id, "prompt-123")
            cancel_event.set()

        with patch.object(main, "_comfy_request", side_effect=fake_request):
            with self.assertRaises(main.GenerationCancelled):
                main._queue_comfy_workflow(
                    {"1": {"class_type": "Test"}},
                    timeout=5,
                    cancel_event=cancel_event,
                    prompt_id_cb=record,
                )

        self.assertIn(("/interrupt", {}), calls)

    def test_comfy_pending_prompt_reports_its_queue_position(self):
        cancel_event = threading.Event()
        messages = []

        def fake_request(path, payload=None, timeout=30):
            if path == "/prompt":
                return {"prompt_id": "prompt-second"}
            if path == "/history/prompt-second":
                return {}
            if path == "/queue" and payload is None:
                return {
                    "queue_running": [[1, "prompt-first", {}, {}]],
                    "queue_pending": [
                        [2, "prompt-other", {}, {}],
                        [3, "prompt-second", {}, {}],
                    ],
                }
            return {}

        def progress(_pct, message):
            messages.append(message)
            if message.startswith("Na fila do ComfyUI"):
                cancel_event.set()

        with (
            patch.object(main, "_comfy_request", side_effect=fake_request),
            patch.object(main._t, "sleep") as sleep,
        ):
            with self.assertRaises(main.GenerationCancelled):
                main._queue_comfy_workflow(
                    {"1": {"class_type": "Test"}},
                    timeout=5,
                    progress_cb=progress,
                    cancel_event=cancel_event,
                )

        self.assertIn("Na fila do ComfyUI — posição 2.", messages)
        sleep.assert_called_with(5.0)

    def test_existing_comfy_prompt_is_reused_after_studio_restart(self):
        calls = []

        def fake_request(path, payload=None, timeout=30):
            calls.append((path, payload))
            if path == "/history/prompt-existing":
                return {
                    "prompt-existing": {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {"1": {"images": [{"filename": "ready.png", "type": "output"}]}},
                    }
                }
            if path == "/queue":
                return {"queue_running": [], "queue_pending": []}
            self.fail(f"chamada inesperada: {path}")

        with patch.object(main, "_comfy_request", side_effect=fake_request):
            prompt_id, outputs = main._queue_comfy_workflow(
                {"1": {"class_type": "Test"}},
                timeout=5,
                resume_prompt_id="prompt-existing",
            )

        self.assertEqual(prompt_id, "prompt-existing")
        self.assertEqual(outputs[0]["filename"], "ready.png")
        self.assertNotIn("/prompt", [path for path, _payload in calls])

    def test_missing_comfy_history_does_not_replay_after_restart(self):
        def fake_request(path, payload=None, timeout=30):
            if path == "/history/prompt-existing": return {}
            if path == "/queue": return {"queue_running": [], "queue_pending": []}
            self.fail(f"unexpected submission or mutation: {path}")
        with patch.object(main, "_comfy_request", side_effect=fake_request):
            with self.assertRaisesRegex(RuntimeError, "COMFY_PROMPT_STATE_UNKNOWN"):
                main._queue_comfy_workflow({"1":{"class_type":"Test"}}, timeout=5,
                                           resume_prompt_id="prompt-existing")

    def test_rewriter_dispatch_preserves_text_as_unapplied_proposal(self):
        from creative_os.adapters import H3Adapter
        from test_creative_os_ir import sample
        spec=H3Adapter().build_job(sample(),{'seed':23})
        spec.update(mode='prompt_rewrite',prompt='Original brief')
        with patch.object(main,'_queue_comfy_workflow',return_value=('rewriter-prompt',
            [{'kind':'text','node':'3','text':'Suggested brief'}])) as queue:
            result=main._run_generative(**main._normalize_generative_job_spec(spec))
        queue.assert_called_once()
        self.assertEqual(result['text'],'Suggested brief')
        self.assertFalse(result['rewriter']['applied'])
        self.assertIsNone(result['rewriter']['human_verdict'])
        extracted=main._extract_comfy_outputs({'outputs':{'3':{'text':['Suggested brief']}}})
        self.assertEqual(extracted,[{'kind':'text','node':'3','text':'Suggested brief'}])

    def test_rewriter_background_worker_obtains_shared_gpu_admission(self):
        from creative_os.adapters import H3Adapter
        from test_creative_os_ir import sample
        spec=H3Adapter().build_job(sample(),{'seed':23});spec.update(mode='prompt_rewrite',prompt='Original')
        admitted=[]
        def admission(*args,**kwargs): admitted.append(args[0])
        def run(**kwargs):
            self.assertEqual(len(admitted),1)
            self.assertEqual(kwargs['mode'],'prompt_rewrite')
            return {'ok':True,'mode':'prompt_rewrite','text':'proposal','outputs':[]}
        with patch.object(main,'_wait_for_gpu_lease',side_effect=admission),patch.object(main,'_run_generative',side_effect=run):
            job_id=main._start_generative_job(spec)
            done=self.wait_terminal(job_id)
        self.assertEqual(done['status'],'done')
        self.assertEqual(admitted,[job_id])

    def test_comfy_aimdo_vbar_fault_is_classified_for_controlled_recovery(self):
        status = {
            "status_str": "error",
            "completed": False,
            "messages": [[
                "execution_error",
                {
                    "node_type": "MiniMaxH3ImageToVideo",
                    "exception_type": "RuntimeError",
                    "exception_message": "Fault failed: 2\n",
                    "traceback": ["comfy_aimdo.model_vbar.vbar_fault"],
                },
            ]],
        }

        with self.assertRaises(main.ComfyDynamicVramFault):
            main._raise_comfy_execution_error(status)

    def test_production_queue_reports_running_and_pending_take_positions(self):
        self.store.update(
            "job-running",
            status="running",
            prompt_id="prompt-running",
            project_id="filme",
            take_id="03",
            mode="video",
            progress=31,
        )
        self.store.update(
            "job-pending",
            status="running",
            prompt_id="prompt-pending",
            project_id="filme",
            take_id="04",
            mode="video",
            progress=8,
        )

        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_comfy_request", return_value={
                "queue_running": [[1, "prompt-running", {}, {}]],
                "queue_pending": [[2, "prompt-pending", {}, {}]],
            }),
        ):
            queue = asyncio.run(main.generative_queue(SimpleNamespace(headers={}, client=None)))

        self.assertEqual(queue["running"], 1)
        self.assertEqual(queue["pending"], 1)
        self.assertEqual(queue["items"][0]["takeId"], "03")
        self.assertEqual(queue["items"][0]["state"], "RUNNING")
        self.assertEqual(queue["items"][1]["takeId"], "04")
        self.assertEqual(queue["items"][1]["position"], 1)

    def test_batch_jobs_start_only_eligible_production_takes(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {"action": "production"}

        takes = {
            "data": [
                {"takeId": "01", "status": "PLANNED", "canGenerate": True, "hasPreview": False},
                {"takeId": "02", "status": "READY", "canGenerate": True, "hasPreview": True},
                {"takeId": "03", "status": "GENERATING", "canGenerate": True, "hasPreview": False},
            ]
        }
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_list_video_takes", return_value=takes),
            patch.object(main, "_get_video_project", return_value={"productionBatch": {"enabled": False}}),
            patch.object(main, "_active_project_video_take_jobs", return_value=[]),
            patch.object(main, "_preflight_video_take_job", return_value={}),
            patch.object(main, "_start_video_take_job", return_value={
                "jobId": "job-01", "stage": "WAN_VALIDATED_BASE"
            }) as starter,
        ):
            result = asyncio.run(main.video_project_batch_jobs(FakeRequest(), "demo"))

        self.assertEqual(result["startedCount"], 1)
        self.assertEqual(result["started"][0]["takeId"], "01")
        starter.assert_called_once()
        self.assertEqual(starter.call_args.args, ("demo", "01", -1))
        self.assertEqual(starter.call_args.kwargs["batch_index"], 1)
        self.assertEqual(starter.call_args.kwargs["batch_size"], 1)

    def test_batch_jobs_respect_fixed_story_blocks_of_three(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {"action": "production"}

        takes = {"data": [
            {"takeId": f"{index:03d}", "status": "PLANNED", "canGenerate": True, "hasPreview": False}
            for index in range(1, 6)
        ]}
        project = {
            "productionBatch": {
                "enabled": True,
                "batchSize": 3,
                "renderOrder": ["001", "002", "003", "004", "005"],
                "strictContiguous": True,
                "requireAllBaseImagesReady": True,
                "requireFullBatch": True,
            }
        }
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_list_video_takes", return_value=takes),
            patch.object(main, "_get_video_project", return_value=project),
            patch.object(main, "_active_project_video_take_jobs", return_value=[]),
            patch.object(main, "_preflight_video_take_job", return_value={}),
            patch.object(main, "_start_video_take_job", side_effect=lambda _project, take_id, _seed, **_batch: {
                "jobId": f"job-{take_id}", "stage": "VIDEO_ENGINE_READY",
            }) as starter,
        ):
            result = asyncio.run(main.video_project_batch_jobs(FakeRequest(), "demo"))

        self.assertEqual(result["batchTakeIds"], ["001", "002", "003"])
        self.assertEqual(result["startedCount"], 3)
        self.assertEqual([call.args[1] for call in starter.call_args_list], ["001", "002", "003"])
        batch_ids = {call.kwargs["batch_id"] for call in starter.call_args_list}
        self.assertEqual(len(batch_ids), 1)
        self.assertEqual(result["productionBatchId"], batch_ids.pop())
        self.assertEqual([call.kwargs["batch_index"] for call in starter.call_args_list], [1, 2, 3])
        self.assertEqual([call.kwargs["batch_size"] for call in starter.call_args_list], [3, 3, 3])

    def test_story_batch_does_not_skip_a_take_with_missing_anchor(self):
        takes = [
            {"takeId": "019", "status": "ERROR", "canGenerate": True, "hasPreview": False},
            {"takeId": "020", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
            {"takeId": "021", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
        ]
        policy = {
            "enabled": True,
            "batchSize": 3,
            "renderOrder": ["019", "020", "021"],
            "strictContiguous": True,
            "requireAllBaseImagesReady": True,
        }

        selected, batch_ids, blocked_ids = main._select_story_production_batch(
            takes,
            [takes[0]],
            policy,
        )

        self.assertEqual([take["takeId"] for take in selected], ["019"])
        self.assertEqual(batch_ids, ["019", "020", "021"])
        self.assertEqual(blocked_ids, ["020", "021"])

    def test_story_batch_releases_an_incomplete_correction_retry(self):
        takes = [
            {
                "takeId": "019",
                "status": "REJECTED",
                "canGenerate": True,
                "hasPreview": True,
                "qcStatus": "unauthorized_human_cast_rejected_rerender_required",
                "directorRequest": {"status": "DELIVERED"},
            },
            {"takeId": "020", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
            {"takeId": "021", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
        ]
        policy = {
            "enabled": True,
            "batchSize": 3,
            "renderOrder": ["019", "020", "021"],
            "strictContiguous": True,
            "requireAllBaseImagesReady": True,
            "requireFullBatch": True,
            "fillEligibleAcrossBatches": True,
            "allowIncompleteCorrectionBatch": True,
        }
        eligible = [take for take in takes if main._production_batch_eligible(take)]

        selected, batch_ids, blocked_ids = main._select_story_production_batch(
            takes,
            eligible,
            policy,
        )

        self.assertEqual([take["takeId"] for take in selected], ["019"])
        self.assertEqual(batch_ids, ["019"])
        self.assertEqual(blocked_ids, [])

    def test_batch_endpoint_starts_one_correction_without_future_anchors(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {"action": "production"}

        takes = {"data": [
            {
                "takeId": "019",
                "status": "REJECTED",
                "canGenerate": True,
                "hasPreview": True,
                "qcStatus": "unauthorized_human_cast_rejected_rerender_required",
                "directorRequest": {"status": "DELIVERED"},
            },
            {"takeId": "020", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
            {"takeId": "021", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
        ]}
        project = {"productionBatch": {
            "enabled": True,
            "batchSize": 3,
            "renderOrder": ["019", "020", "021"],
            "strictContiguous": True,
            "requireAllBaseImagesReady": True,
            "requireFullBatch": True,
            "fillEligibleAcrossBatches": True,
            "allowIncompleteCorrectionBatch": True,
        }}
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_list_video_takes", return_value=takes),
            patch.object(main, "_get_video_project", return_value=project),
            patch.object(main, "_active_project_video_take_jobs", return_value=[]),
            patch.object(main, "_preflight_video_take_job", return_value={}),
            patch.object(main, "_start_video_take_job", return_value={
                "jobId": "job-019", "stage": "VIDEO_ENGINE_READY",
            }) as starter,
        ):
            result = asyncio.run(main.video_project_batch_jobs(FakeRequest(), "demo"))

        self.assertEqual(result["startedCount"], 1)
        self.assertEqual(result["batchTakeIds"], ["019"])
        self.assertTrue(result["incompleteCorrectionBatch"])
        starter.assert_called_once()
        self.assertEqual(starter.call_args.args[:3], ("demo", "019", -1))
        self.assertEqual(starter.call_args.kwargs["batch_index"], 1)
        self.assertEqual(starter.call_args.kwargs["batch_size"], 1)

    def test_rolling_story_batch_fills_three_ready_takes_across_old_blocks(self):
        takes = [
            {"takeId": "016", "status": "READY", "canGenerate": True, "hasPreview": True},
            {
                "takeId": "017",
                "status": "REJECTED",
                "canGenerate": True,
                "hasPreview": True,
                "qcStatus": "audio_locale_rejected_qwen_av_rerender_required",
                "directorRequest": {"status": "CANCELLED"},
            },
            {"takeId": "018", "status": "ERROR", "canGenerate": True, "hasPreview": False},
            {"takeId": "019", "status": "ERROR", "canGenerate": True, "hasPreview": True},
            {"takeId": "020", "status": "PLANNED", "canGenerate": False, "hasPreview": False},
        ]
        policy = {
            "enabled": True,
            "batchSize": 3,
            "renderOrder": ["016", "017", "018", "019", "020"],
            "strictContiguous": True,
            "requireAllBaseImagesReady": True,
            "fillEligibleAcrossBatches": True,
        }
        eligible = [take for take in takes if main._production_batch_eligible(take)]

        selected, batch_ids, blocked_ids = main._select_story_production_batch(
            takes,
            eligible,
            policy,
        )

        self.assertEqual([take["takeId"] for take in selected], ["017", "018", "019"])
        self.assertEqual(batch_ids, ["017", "018", "019"])
        self.assertEqual(blocked_ids, [])

    def test_full_production_batch_never_starts_only_two_jobs(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {"action": "production"}

        takes = {"data": [
            {"takeId": "001", "status": "PLANNED", "canGenerate": True, "hasPreview": False},
            {"takeId": "002", "status": "PLANNED", "canGenerate": True, "hasPreview": False},
        ]}
        project = {"productionBatch": {
            "enabled": True,
            "batchSize": 3,
            "renderOrder": ["001", "002"],
            "requireFullBatch": True,
        }}
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_list_video_takes", return_value=takes),
            patch.object(main, "_get_video_project", return_value=project),
            patch.object(main, "_active_project_video_take_jobs", return_value=[]),
            patch.object(main, "_preflight_video_take_job", return_value={}),
            patch.object(main, "_start_video_take_job") as starter,
        ):
            response = asyncio.run(main.video_project_batch_jobs(FakeRequest(), "demo"))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "PRODUCTION_BATCH_INCOMPLETE")
        self.assertEqual(payload["error"]["details"]["readyCount"], 2)
        self.assertEqual(payload["error"]["details"]["requiredCount"], 3)
        starter.assert_not_called()

    def test_active_production_batch_blocks_a_second_button_submission(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {"action": "production"}

        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_list_video_takes", return_value={"data": []}),
            patch.object(main, "_active_project_video_take_jobs", return_value=[{
                "job_id": "job-active",
                "take_id": "020",
                "status": "running",
            }]),
            patch.object(main, "_start_video_take_job") as starter,
        ):
            response = asyncio.run(main.video_project_batch_jobs(FakeRequest(), "demo"))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "PRODUCTION_BATCH_ACTIVE")
        self.assertEqual(payload["error"]["details"]["activeTakeIds"], ["020"])
        starter.assert_not_called()

    def test_local_anchor_executor_is_blocked_for_codex_imagegen_project(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {"takeIds": ["020"]}

        project = {
            "anchorGeneration": {
                "provider": "codex_builtin_imagegen",
                "requiredGenerator": "Codex built-in imagegen",
                "localExecutorAllowed": False,
            }
        }
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_get_video_project", return_value=project),
            patch.object(main.internet_publication, "require_direction"),
            patch.object(main._ANCHOR_EXECUTOR_MANAGER, "start") as starter,
        ):
            response = asyncio.run(main.video_anchor_executor_start(FakeRequest(), "demo"))

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "LOCAL_ANCHOR_EXECUTOR_FORBIDDEN")
        starter.assert_not_called()

    def test_anchor_pilot_gate_starts_only_the_owner_selected_pilots(self):
        class FakeRequest:
            headers = {}
            client = None

            async def json(self):
                return {}

        pilot_ids = ["01", "03", "04", "10"]
        project = {
            "anchorGeneration": {
                "localExecutorAllowed": True,
                "pilotFirst": True,
                "pilotTakeIds": pilot_ids,
                "remainingBatchRequiresPilotHumanApproval": True,
            }
        }
        take_views = {
            "data": [
                {"takeId": take_id, "keyframeApproved": False}
                for take_id in [*pilot_ids, "02", "05"]
            ]
        }
        with (
            patch.object(main, "_is_internal_request", return_value=True),
            patch.object(main, "_get_video_project", return_value=project),
            patch.object(main.internet_publication, "require_direction"),
            patch.object(main, "_pending_anchor_take_ids", return_value=[*pilot_ids, "02", "05"]),
            patch.object(main, "_list_video_takes", return_value=take_views),
            patch.object(
                main._ANCHOR_EXECUTOR_MANAGER,
                "start",
                return_value={"status": "running", "projectId": "demo"},
            ) as starter,
        ):
            response = asyncio.run(main.video_anchor_executor_start(FakeRequest(), "demo"))

        self.assertEqual(response["pendingTakeIds"], pilot_ids)
        starter.assert_called_once_with("demo", take_ids=pilot_ids)

    def test_take_job_uses_the_duration_derived_frame_count(self):
        keyframe = Path(self.temp_dir.name) / "take01.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "PLANNED",
            "prompt": "Camera avanca.",
            "negative": "no morphing",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "frames": 124,
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "durationSeconds": 4.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_minimax_h3_kit_ready", return_value=True),
            patch.object(main, "_set_take_generation_state"),
            patch.object(main, "_launch_video_take_worker") as launcher,
        ):
            started = main._start_video_take_job("filme", "01", seed=123)

        job = self.store.get(started["jobId"])
        self.assertEqual(started["frames"], 124)
        self.assertEqual(job["frames"], 124)
        launcher.assert_called_once()
        self.assertEqual(launcher.call_args.args[3]["frames"], 124)

    def test_take_job_rejects_retired_fun_camera_profile(self):
        keyframe = Path(self.temp_dir.name) / "take06b.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "REJECTED",
            "prompt": "Physical rightward truck with three-plane parallax.",
            "negative": "static hold, text",
            "generationProfile": "wan22_fun_camera_v1",
            "width": 768,
            "height": 432,
            "frames": 97,
            "fps": 24,
            "steps": 20,
            "guidance": 3.5,
            "cameraPose": "Pan Right",
            "cameraSpeed": 0.5,
            "videoConditioningProfile": "identity_locked",
            "durationSeconds": 4.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        with patch.object(main, "_get_take_generation_spec", return_value=spec):
            with self.assertRaisesRegex(main._VideoEngineError, "MiniMax H3"):
                main._start_video_take_job("filme", "06B", seed=456)

    def test_default_h3_take_job_selects_authorized_model_and_native_contract(self):
        keyframe = Path(self.temp_dir.name) / "take004.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "APPROVED",
            "prompt": "Pedro escuta e reage uma vez.",
            "negative": "visible text, subtitles",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "frames": 141,
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "cameraPose": "Static",
            "cameraSpeed": 0.2,
            "videoConditioningProfile": "identity_locked",
            "durationSeconds": 6.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_minimax_h3_kit_ready", return_value=True),
            patch.object(main, "_set_take_generation_state"),
            patch.object(main, "_launch_video_take_worker") as launcher,
        ):
            started = main._start_video_take_job("curta", "004", seed=789)

        job = self.store.get(started["jobId"])
        self.assertEqual(started["stage"], "MINIMAX_H3_OWNER_LOCKED_PROFILE")
        self.assertEqual(job["model"], main.MINIMAX_H3_MODEL_NAME)
        self.assertEqual(job["generation_profile"], "minimax_h3_fl2va_int8_720p24")
        self.assertEqual((job["width"], job["height"], job["fps"]), (1280, 720, 24))
        self.assertEqual((job["frames"], job["steps"], job["guidance"]), (141, 20, 1.0))
        launcher.assert_called_once()

    def test_removed_ltx23_hq_take_is_blocked_before_worker_launch(self):
        keyframe = Path(self.temp_dir.name) / "take005.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "APPROVED",
            "prompt": "Plano continuo com acao unica.",
            "negative": "visible text, subtitles",
            "generationProfile": "ltx23_dev_two_stage_hq_720p",
            "width": 1280,
            "height": 720,
            "frames": 145,
            "fps": 24,
            "steps": 15,
            "guidance": 3.0,
            "cameraPose": "Static",
            "cameraSpeed": 0.2,
            "videoConditioningProfile": "identity_locked",
            "durationSeconds": 6.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_set_take_generation_state"),
            patch.object(main, "_launch_video_take_worker") as launcher,
        ):
            with self.assertRaises(main._VideoEngineError) as caught:
                main._start_video_take_job("curta", "005", seed=790)

        self.assertEqual(caught.exception.code, "ENGINE_NOT_ALLOWED")
        launcher.assert_not_called()

    def test_minimax_h3_take_job_selects_owner_locked_model(self):
        keyframe = Path(self.temp_dir.name) / "take006.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "APPROVED",
            "prompt": "Soldados reptilianos da FEB avancam com movimento fisico claro.",
            "negative": "human faces, modern weapons",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "frames": 175,
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "cameraPose": "Static",
            "cameraSpeed": 0.2,
            "videoConditioningProfile": "identity_locked",
            "durationSeconds": 7.25,
            "visualOnlyPass": True,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_minimax_h3_kit_ready", return_value=True),
            patch.object(main, "_set_take_generation_state"),
            patch.object(main, "_launch_video_take_worker") as launcher,
        ):
            started = main._start_video_take_job("monte_castello", "006", seed=791)

        job = self.store.get(started["jobId"])
        self.assertEqual(started["stage"], "MINIMAX_H3_OWNER_LOCKED_PROFILE")
        self.assertEqual(job["model"], main.MINIMAX_H3_MODEL_NAME)
        self.assertEqual((job["width"], job["height"], job["fps"]), (1280, 720, 24))
        self.assertTrue(job["visual_only_pass"])
        launcher.assert_called_once()

    def test_minimax_h3_take_recovers_one_vbar_fault_and_retries_same_seed(self):
        keyframe = Path(self.temp_dir.name) / "take006-recovery.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "APPROVED",
            "prompt": "Oocito cientifico sem pessoas em movimento cinematografico.",
            "negative": "human faces, visible text",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "frames": 124,
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "cameraPose": "Static",
            "cameraSpeed": 0.2,
            "videoConditioningProfile": "identity_locked",
            "durationSeconds": 5.0,
            "visualOnlyPass": True,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        attempts = []

        def run_generative(**kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                raise main.ComfyDynamicVramFault("Fault failed: 2")
            return {"ok": True, "mode": "video", "outputs": []}

        preview = Path(self.temp_dir.name) / "take006-recovery-preview.mp4"
        preview.write_bytes(b"preview")
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_minimax_h3_kit_ready", return_value=True),
            patch.object(main, "_set_take_generation_state"),
            patch.object(main, "_run_generative", side_effect=run_generative),
            patch.object(main, "_recover_comfy_dynamic_vram") as recover,
            patch.object(
                main,
                "_finalize_video_take_candidate",
                return_value=(preview, False),
            ),
        ):
            started = main._start_video_take_job("criopreservacao", "006", seed=-1)
            terminal = self.wait_terminal(started["jobId"])

        self.assertEqual(terminal["status"], "done")
        self.assertEqual(terminal["dynamic_vram_recovery_count"], 1)
        self.assertEqual(len(attempts), 2)
        self.assertGreater(attempts[0]["seed"], 0)
        self.assertEqual(attempts[0]["seed"], attempts[1]["seed"])
        self.assertEqual(attempts[1]["resume_prompt_id"], "")
        recover.assert_called_once_with()

    def test_minimax_h3_workflow_never_decodes_audio_without_directive(self):
        workflow = main._build_minimax_h3_fl2va_workflow(
            prompt="FEB reptilian patrol advances.",
            negative="human faces",
            width=1280,
            height=720,
            frames=124,
            steps=20,
            seed=123,
            prefix="test/minimax_h3",
            base_image_name="approved_anchor.png",
            fps=24,
        )
        classes = {node["class_type"] for node in workflow.values()}
        self.assertIn("MiniMaxH3ImageToVideo", classes)
        self.assertIn("LTXVSeparateAVLatent", classes)
        self.assertNotIn("VAEDecodeAudio", classes)
        self.assertNotIn(main.MINIMAX_H3_AUDIO_VAE, json.dumps(workflow))
        self.assertEqual(workflow["1"]["inputs"]["weight_dtype"], "default")
        self.assertEqual(
            (workflow["6"]["inputs"]["width"], workflow["6"]["inputs"]["height"]),
            (1344, 768),
        )
        self.assertEqual(workflow["14"]["class_type"], "ImageScale")
        self.assertEqual(
            (workflow["14"]["inputs"]["width"], workflow["14"]["inputs"]["height"]),
            (1280, 720),
        )
        self.assertEqual(workflow["15"]["inputs"]["images"], ["14", 0])
        self.assertFalse(any(node["class_type"] == "PemaraH3FaceRefine" for node in workflow.values()))
        self.assertNotIn("audio", workflow["15"]["inputs"])
        self.assertEqual(workflow["15"]["inputs"]["fps"], 24)
        effective_prompt = workflow["6"]["inputs"]["prompt"]
        self.assertNotIn("SILENT VISUAL PASS", effective_prompt)
        self.assertNotIn("Avoid:", effective_prompt)
        self.assertEqual(effective_prompt, "FEB reptilian patrol advances.")

    def test_minimax_h3_workflow_supports_text_to_video_without_keyframe(self):
        workflow = main._build_minimax_h3_fl2va_workflow(
            prompt="A red fox crosses a snowy clearing at sunrise.",
            negative="",
            width=1280,
            height=720,
            frames=124,
            steps=20,
            seed=321,
            prefix="test/minimax_h3_t2v",
            base_image_name="",
            fps=24,
        )

        classes = {node["class_type"] for node in workflow.values()}
        self.assertNotIn("LoadImage", classes)
        conditioning = next(
            node for node in workflow.values()
            if node["class_type"] == "MiniMaxH3ImageToVideo"
        )
        self.assertNotIn("first_frame", conditioning["inputs"])
        self.assertNotIn("last_frame", conditioning["inputs"])
        self.assertEqual(
            conditioning["inputs"]["prompt"],
            "A red fox crosses a snowy clearing at sunrise.",
        )

    def test_minimax_h3_workflow_forwards_approved_first_and_last_frames(self):
        workflow = main._build_minimax_h3_fl2va_workflow(
            prompt="The fighters cross the arena axis in one continuous action.",
            negative="",
            width=1280,
            height=720,
            frames=124,
            steps=20,
            seed=777,
            prefix="test/minimax_h3_fl2va_both_frames",
            base_image_name="approved_start.png",
            end_image_name="approved_end.png",
            fps=24,
        )

        conditioning = next(
            node for node in workflow.values()
            if node["class_type"] == "MiniMaxH3ImageToVideo"
        )
        self.assertEqual(conditioning["inputs"]["first_frame"], ["5", 0])
        self.assertEqual(conditioning["inputs"]["last_frame"], ["19", 0])
        self.assertEqual(workflow["5"]["inputs"]["image"], "approved_start.png")
        self.assertEqual(workflow["19"]["inputs"]["image"], "approved_end.png")

    def test_minimax_h3_workflow_supports_timed_last_frame_with_post_anchor_motion(self):
        workflow = main._build_minimax_h3_fl2va_workflow(
            prompt="Reach the approved impact, then continue the physical recoil.",
            negative="",
            width=1088,
            height=608,
            frames=124,
            steps=10,
            seed=778,
            prefix="test/minimax_h3_fl2va_timed_last_frame",
            base_image_name="approved_start.png",
            end_image_name="approved_impact.png",
            fps=24,
            h3_quality_profile="h3_production",
            last_frame_index=110,
        )

        conditioning = next(
            node for node in workflow.values()
            if node["class_type"] == "MiniMaxH3ImageToVideo"
        )
        self.assertEqual(conditioning["inputs"]["last_frame"], ["19", 0])
        self.assertEqual(conditioning["inputs"]["last_frame_index"], 110)

    def test_minimax_h3_workflow_supports_middle_image_guide(self):
        workflow = main._build_minimax_h3_fl2va_workflow(
            prompt="Throw, hit the tree, then recover the chain.",
            negative="",
            width=1088,
            height=608,
            frames=141,
            steps=10,
            seed=779,
            prefix="test/minimax_h3_fl2va_middle_guide",
            base_image_name="pre_spear.png",
            end_image_name="post_spear_recovery.png",
            fps=24,
            h3_quality_profile="h3_production",
            last_frame_index=123,
            guide_image_name="tree_gouge.png",
            guide_frame_index=64,
        )

        self.assertEqual(workflow["21"]["inputs"]["image"], "tree_gouge.png")
        self.assertEqual(workflow["22"]["class_type"], "MiniMaxH3AddGuide")
        self.assertEqual(workflow["22"]["inputs"]["positive"], ["6", 0])
        self.assertEqual(workflow["22"]["inputs"]["latent"], ["6", 1])
        self.assertEqual(workflow["22"]["inputs"]["frame_idx"], 64)
        self.assertEqual(workflow["7"]["inputs"]["conditioning"], ["22", 0])

    def test_minimax_h3_ref2va_workflow_forwards_all_anchors_and_motion_driver(self):
        workflow = main._build_minimax_h3_ref2va_workflow(
            prompt=(
                "subject_definitions:\n<Picture 1> start. <Picture 2> contact. <Video 1> motion.\n\n"
                "summary:\nFollow <Video 1>.\n\nretention_analysis:\nRetain <Picture 1>.\n\n"
                "detailed_description:\n[Shot 1] Live action.\n\noverall_soundscape:\nN/A\n\n"
                "non_diegetic_music:\nN/A"
            ),
            negative="",
            width=720,
            height=1280,
            frames=362,
            steps=20,
            seed=1234,
            prefix="test/minimax_h3_ref2va",
            reference_image_names=["la01.png", "la02.png", "la03.png", "la04.png", "la05.png"],
            reference_video_name="fusion_driver.mp4",
            fps=24,
            include_native_audio=True,
        )

        conditioning = workflow["6"]
        self.assertEqual(conditioning["class_type"], "MiniMaxH3ReferenceToVideo")
        self.assertEqual(
            workflow["1"]["inputs"]["unet_name"],
            main.MINIMAX_H3_REF2VA_MODEL_NAME,
        )
        self.assertEqual(len(conditioning["inputs"]["ref_images"]), 5)
        self.assertEqual(conditioning["inputs"]["ref_videos"], {"ref_video_1": ["50", 0]})
        self.assertEqual(workflow["50"]["class_type"], "VHS_LoadVideo")
        self.assertEqual(workflow["50"]["inputs"]["force_rate"], 24)
        self.assertEqual(workflow["50"]["inputs"]["frame_load_cap"], 362)
        self.assertEqual(workflow["17"]["inputs"]["vae_name"], main.MINIMAX_H3_AUDIO_VAE)
        self.assertNotIn("first_frame", conditioning["inputs"])
        self.assertNotIn("last_frame", conditioning["inputs"])

    def test_minimax_h3_live_preview_is_opt_in_and_does_not_change_sampling(self):
        baseline = main._build_minimax_h3_fl2va_workflow(
            prompt="A continuous live-action redirect.",
            negative="",
            width=1280,
            height=720,
            frames=124,
            steps=20,
            seed=991,
            prefix="test/minimax_h3_preview_off",
            base_image_name="start.png",
            end_image_name="end.png",
            fps=24,
        )
        preview = main._build_minimax_h3_fl2va_workflow(
            prompt="A continuous live-action redirect.",
            negative="",
            width=1280,
            height=720,
            frames=124,
            steps=20,
            seed=991,
            prefix="test/minimax_h3_preview_on",
            base_image_name="start.png",
            end_image_name="end.png",
            enable_live_preview=True,
            fps=24,
        )

        self.assertNotIn("ModelPreviewOverrideKJ", {node["class_type"] for node in baseline.values()})
        self.assertEqual(preview["20"]["class_type"], "ModelPreviewOverrideKJ")
        self.assertEqual(preview["20"]["inputs"]["preview_frames"], 1)
        from h3_acceleration import model_chain, validate_spectrum
        self.assertTrue(validate_spectrum(preview))
        chain = model_chain(preview, preview["7"]["inputs"]["model"][0])
        self.assertEqual([n["class_type"] for _, n in chain[:4]],
            ["SpectrumApplyMiniMaxH3", "PemaraH3SageLongSequencePatch",
             "MiniMaxH3MemoryEfficientSageAttentionPatch", "ModelPreviewOverrideKJ"])
        self.assertEqual(preview["7"]["inputs"]["model"], preview["8"]["inputs"]["model"])
        self.assertEqual(preview["10"], baseline["10"])
        self.assertEqual(preview["11"]["inputs"]["sampler"], baseline["11"]["inputs"]["sampler"])
        self.assertEqual(preview["8"]["inputs"]["steps"], 20)
        self.assertEqual(preview["3"], baseline["3"])

    def test_minimax_h3_text_to_video_dispatches_without_saving_an_image(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "width": 1280,
            "height": 720,
            "frames": 124,
            "fps": 24.0,
            "video_duration": 6.0,
            "steps": 20,
            "guidance": 1.0,
        })
        queued = {}

        def queue_workflow(workflow, **_kwargs):
            queued["workflow"] = workflow
            return "prompt-h3-t2v", [{"kind": "video"}]

        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(
                main,
                "_video_model_files",
                return_value=[main.MINIMAX_H3_MODEL_NAME],
            ),
            patch.object(main, "_save_comfy_input_image") as save_image,
            patch.object(main, "_queue_comfy_workflow", side_effect=queue_workflow),
            patch.object(
                main,
                "_finalize_video_mp4",
                return_value=[{"kind": "video", "path": "t2v.mp4"}],
            ),
        ):
            result = main._run_generative(**spec)

        self.assertTrue(result["ok"])
        self.assertEqual(result["model"], main.MINIMAX_H3_MODEL_NAME)
        self.assertEqual(result["frames"], 141)
        save_image.assert_not_called()
        workflow = queued["workflow"]
        self.assertNotIn("LoadImage", {node["class_type"] for node in workflow.values()})
        self.assertNotIn("first_frame", workflow["6"]["inputs"])

    def test_motion_director_uses_existing_h3_worker_and_preserves_plan(self):
        from creative_os.adapters import H3Adapter
        from test_creative_os_ir import sample
        shots=[sample(),sample()]
        shots[1]['shot_id']='SH02'
        spec=H3Adapter().build_job(shots[0],{'seed':42})
        spec['creative_motion_request']={'shots':shots,'motion_context':True,'selected':None}
        queued={}
        def enqueue(workflow,**kwargs):
            queued.update(workflow=workflow)
            return 'motion-prompt',[{'kind':'video','filename':'first.mp4'},{'kind':'video','filename':'second.mp4'}]
        with (
            patch.object(main,'_require_authorized_video_engine'),
            patch.object(main,'_comfy_online',return_value=(True,{})),
            patch.object(main,'_model_files',return_value=[]),
            patch.object(main,'_video_model_files',return_value=[main.MINIMAX_H3_MODEL_NAME]),
            patch.object(main,'_save_comfy_input_image') as save_image,
            patch.object(main,'_queue_comfy_workflow',side_effect=enqueue),
            patch.object(main,'_finalize_video_mp4',side_effect=lambda outputs,**kwargs:outputs),
        ):
            normalized=main._normalize_generative_job_spec(spec)
            result=main._run_generative(**normalized)
        save_image.assert_not_called()
        self.assertEqual(queued['workflow']['20']['class_type'],'MiniMaxH3MotionDirector')
        self.assertEqual(queued['workflow']['20']['inputs']['steps'],10)
        self.assertEqual(result['creative_motion']['selected_shots'],['SH01','SH02'])
        self.assertEqual(result['frames'],248)
        self.assertAlmostEqual(result['duration_seconds'],248/24)
        self.assertFalse(result['native_audio_enabled'])

    def test_all_in_one_uses_expanded_template_in_existing_h3_worker(self):
        from creative_os.adapters import H3Adapter
        from test_creative_os_ir import sample
        shots=[sample()]
        spec=H3Adapter().build_job(shots[0],{'seed':42,'h3_adapter':'all_in_one'})
        queued={}
        def enqueue(workflow,**kwargs):
            queued.update(workflow=workflow)
            return 'motion-prompt',[{'kind':'video','filename':'expanded.mp4'}]
        with (
            patch.object(main,'_require_authorized_video_engine'),
            patch.object(main,'_comfy_online',return_value=(True,{})),
            patch.object(main,'_model_files',return_value=[]),
            patch.object(main,'_video_model_files',return_value=[main.MINIMAX_H3_MODEL_NAME]),
            patch.object(main,'_save_comfy_input_image') as save_image,
            patch.object(main,'_queue_comfy_workflow',side_effect=enqueue),
            patch.object(main,'_finalize_video_mp4',side_effect=lambda outputs,**kwargs:outputs),
        ):
            normalized=main._normalize_generative_job_spec(spec)
            result=main._run_generative(**normalized)
        save_image.assert_not_called()
        self.assertEqual(queued['workflow']['6']['class_type'],'MiniMaxH3ReferenceToVideo')
        self.assertEqual(queued['workflow']['9']['inputs']['steps'],10)
        self.assertEqual(result['creative_all_in_one']['headless_expansion'],True)
        self.assertEqual(result['frames'],124)
        self.assertAlmostEqual(result['duration_seconds'],123/24)
        self.assertFalse(result['native_audio_enabled'])

    def test_fun_control_uses_existing_h3_worker_and_preserves_native_sampling(self):
        from creative_os.adapters import H3Adapter
        from test_creative_os_ir import sample
        shots=[sample()]
        spec=H3Adapter().build_job(shots[0],{'seed':42})
        spec['creative_fun_control_request']={'ir':shots[0],'asset_id':'fixture','asset_sha256':'1'*64,'control_kind':'depth','strength':1.0}
        queued={}
        def enqueue(workflow,**kwargs):
            queued.update(workflow=workflow)
            return 'motion-prompt',[{'kind':'video','filename':'controlled.mp4'}]
        from creative_os.fun_control import patch_graph
        def apply_fixture(ns,graph,request):
            return patch_graph(graph,'fixture.mp4',1.0), {'strength':1.0,'asset_sha256':'1'*64}
        with (
            patch('creative_os.fun_control.apply_in_worker',side_effect=apply_fixture),
            patch.object(main,'_require_authorized_video_engine'),
            patch.object(main,'_comfy_online',return_value=(True,{})),
            patch.object(main,'_model_files',return_value=[]),
            patch.object(main,'_video_model_files',return_value=[main.MINIMAX_H3_MODEL_NAME]),
            patch.object(main,'_save_comfy_input_image') as save_image,
            patch.object(main,'_queue_comfy_workflow',side_effect=enqueue),
            patch.object(main,'_finalize_video_mp4',side_effect=lambda outputs,**kwargs:outputs),
        ):
            normalized=main._normalize_generative_job_spec(spec)
            result=main._run_generative(**normalized)
        save_image.assert_not_called()
        self.assertEqual(queued['workflow']['creative_control_apply']['class_type'],'H3FunControlApply')
        self.assertEqual(queued['workflow']['8']['inputs']['steps'],10)
        self.assertEqual(result['creative_fun_control']['strength'],1.0)
        self.assertEqual(result['frames'],124)
        self.assertAlmostEqual(result['duration_seconds'],123/24)
        self.assertFalse(result['native_audio_enabled'])

    def test_timeline_director_uses_existing_h3_worker_and_preserves_contract(self):
        from creative_os.adapters import H3Adapter
        from test_creative_os_ir import sample
        shots=[sample()]
        shots[0]['duration_seconds']=10
        spec=H3Adapter().build_job(shots[0],{'seed':42})
        spec['creative_timeline_request']={'ir':shots[0],'segment_count':2}
        queued={}
        def enqueue(workflow,**kwargs):
            queued.update(workflow=workflow)
            return 'motion-prompt',[{'kind':'video','filename':'continuous.mp4'}]
        with (
            patch.object(main,'_require_authorized_video_engine'),
            patch.object(main,'_comfy_online',return_value=(True,{})),
            patch.object(main,'_model_files',return_value=[]),
            patch.object(main,'_video_model_files',return_value=[main.MINIMAX_H3_MODEL_NAME]),
            patch.object(main,'_save_comfy_input_image') as save_image,
            patch.object(main,'_queue_comfy_workflow',side_effect=enqueue),
            patch.object(main,'_finalize_video_mp4',side_effect=lambda outputs,**kwargs:outputs),
        ):
            normalized=main._normalize_generative_job_spec(spec)
            result=main._run_generative(**normalized)
        save_image.assert_not_called()
        self.assertEqual(queued['workflow']['20']['class_type'],'MiniMaxH3TimelinePlanner')
        self.assertEqual(queued['workflow']['8']['inputs']['steps'],10)
        self.assertEqual(result['creative_timeline']['segment_count'],2)
        self.assertEqual(result['frames'],226)
        self.assertAlmostEqual(result['duration_seconds'],226/24)
        self.assertFalse(result['native_audio_enabled'])

    def test_minimax_h3_vertical_workflow_preserves_9x16_geometry(self):
        workflow = main._build_minimax_h3_fl2va_workflow(
            prompt="The same anime family walks uphill together.",
            negative="identity drift",
            width=720,
            height=1280,
            frames=243,
            steps=20,
            seed=456,
            prefix="test/minimax_h3_vertical",
            base_image_name="approved_vertical_anchor.png",
            include_native_audio=True,
        )

        self.assertEqual(
            (workflow["6"]["inputs"]["width"], workflow["6"]["inputs"]["height"]),
            (768, 1344),
        )
        self.assertEqual(
            (workflow["14"]["inputs"]["width"], workflow["14"]["inputs"]["height"]),
            (720, 1280),
        )
        self.assertEqual(workflow["14"]["inputs"]["crop"], "center")
        self.assertEqual(workflow["10"]["inputs"]["sampler_name"], "res_multistep")
        self.assertIn("VAEDecodeAudio", {node["class_type"] for node in workflow.values()})

    def test_minimax_h3_vertical_run_selects_portrait_geometry_without_profile_nameerror(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "width": 720,
            "height": 1280,
            "frames": 243,
            "fps": 24.0,
            "steps": 20,
            "guidance": 1.0,
            "base_image_bytes": b"approved-vertical-anchor",
            "base_image_name": "approved_vertical_anchor.png",
            "allow_validated_video_geometry": True,
            "enable_minimax_h3_native_audio": True,
        })

        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(
                main,
                "_video_model_files",
                return_value=[main.MINIMAX_H3_MODEL_NAME],
            ),
            patch.object(main, "_save_comfy_input_image", return_value="anchor.png"),
            patch.object(
                main,
                "_build_minimax_h3_fl2va_workflow",
                return_value={"workflow": {"class_type": "test"}},
            ) as build,
            patch.object(
                main,
                "_queue_comfy_workflow",
                return_value=("prompt-h3-vertical", [{"kind": "video"}]),
            ),
            patch.object(
                main,
                "_finalize_video_mp4",
                return_value=[{"kind": "video", "path": "vertical.mp4"}],
            ),
        ):
            result = main._run_generative(**spec)

        self.assertTrue(result["ok"])
        self.assertEqual(result["model"], main.MINIMAX_H3_MODEL_NAME)
        self.assertEqual(build.call_args.kwargs["width"], 720)
        self.assertEqual(build.call_args.kwargs["height"], 1280)

    def test_manus_motion_is_model_agnostic_and_dispatches_minimax_h3(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "width": 1280,
            "height": 720,
            "frames": 243,
            "fps": 24.0,
            "steps": 20,
            "guidance": 1.0,
            "base_image_bytes": b"approved-anchor",
            "base_image_name": "approved_anchor.png",
            "video_conditioning_profile": "manus_motion",
        })

        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(
                main,
                "_video_model_files",
                return_value=[main.MINIMAX_H3_MODEL_NAME],
            ),
            patch.object(main, "_save_comfy_input_image", return_value="anchor.png"),
            patch.object(
                main,
                "_build_minimax_h3_fl2va_workflow",
                return_value={"workflow": {"class_type": "test"}},
            ) as build,
            patch.object(
                main,
                "_queue_comfy_workflow",
                return_value=("prompt-h3-motion", [{"kind": "video"}]),
            ),
            patch.object(
                main,
                "_finalize_video_mp4",
                return_value=[{"kind": "video", "path": "motion.mp4"}],
            ),
        ):
            result = main._run_generative(**spec)

        self.assertTrue(result["ok"])
        self.assertEqual(result["model"], main.MINIMAX_H3_MODEL_NAME)
        self.assertEqual(result["video_conditioning_profile"], "manus_motion")
        build.assert_called_once()

    def test_h3_automatically_aligns_duration_to_temporal_grid(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "width": 1280,
            "height": 720,
            "frames": 241,
            "fps": 24.0,
            "duration": 10.0,
            "video_duration": 10.0,
            "steps": 20,
            "guidance": 1.0,
            "base_image_bytes": b"approved-anchor",
            "base_image_name": "approved_anchor.png",
        })

        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(
                main,
                "_video_model_files",
                return_value=[main.MINIMAX_H3_MODEL_NAME],
            ),
            patch.object(main, "_save_comfy_input_image", return_value="anchor.png"),
            patch.object(
                main,
                "_build_minimax_h3_fl2va_workflow",
                return_value={"workflow": {"class_type": "test"}},
            ) as build,
            patch.object(
                main,
                "_queue_comfy_workflow",
                return_value=("prompt-h3-timing", [{"kind": "video"}]),
            ),
            patch.object(
                main,
                "_finalize_video_mp4",
                return_value=[{"kind": "video", "path": "timed.mp4"}],
            ),
        ):
            result = main._run_generative(**spec)

        self.assertEqual(build.call_args.kwargs["frames"], 243)
        self.assertEqual(build.call_args.kwargs["fps"], 24.0)
        self.assertEqual(result["frames"], 243)
        self.assertEqual(result["fps"], 24.0)
        self.assertAlmostEqual(result["duration_seconds"], 242 / 24)

    def test_h3_timing_clamps_and_aligns_every_supported_edge(self):
        cases = (
            (10.0, 24.0, False, 243),
            (5.0, 30.0, False, 124),
            (0.1, 24.0, False, 124),
            (100.0, 60.0, False, 362),
            (30.625, 24.0, True, 736),
        )
        for duration, fps, allow_long, expected_frames in cases:
            with self.subTest(duration=duration, fps=fps, allow_long=allow_long):
                frames, rate, effective_duration = main._minimax_h3_timing(
                    duration,
                    fps,
                    allow_owner_long_window=allow_long,
                )
                self.assertEqual(frames, expected_frames)
                self.assertEqual(rate, 24.0)
                self.assertAlmostEqual(effective_duration, (expected_frames - 1) / 24.0)

    def test_h3_fifteen_seconds_uses_trained_maximum_at_native_fps(self):
        frames, rate, effective_duration = main._minimax_h3_timing(15.0, 60.0)

        self.assertEqual(frames, 362)
        self.assertEqual(rate, 24.0)
        self.assertAlmostEqual(effective_duration, 361 / 24)

    def test_h3_persistent_job_spec_records_native_fifteen_second_contract(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "frames": 362,
            "fps": 60.0,
            "video_duration": 15.0,
        })

        normalized = main._normalize_generative_job_spec(spec)

        self.assertEqual(normalized["frames"], 362)
        self.assertEqual(normalized["fps"], 24.0)
        self.assertAlmostEqual(normalized["video_duration"], 361 / 24)

    def test_h3_persistent_job_spec_disables_native_audio_by_default(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "video_duration": 6.0,
        })

        normalized = main._normalize_generative_job_spec(spec)

        self.assertIs(normalized["enable_minimax_h3_native_audio"], False)

    def test_h3_persistent_job_spec_preserves_explicit_native_audio_opt_out(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "video_duration": 6.0,
            "enable_minimax_h3_native_audio": False,
        })

        normalized = main._normalize_generative_job_spec(spec)

        self.assertIs(normalized["enable_minimax_h3_native_audio"], False)

    def test_h3_explicit_native_audio_opt_in_dispatches_audio_nodes(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_MODEL_NAME,
            "width": 1280,
            "height": 720,
            "frames": 124,
            "fps": 24.0,
            "video_duration": 6.0,
            "steps": 20,
            "guidance": 1.0,
            "enable_minimax_h3_native_audio": True,
        })
        normalized = main._normalize_generative_job_spec(spec)
        queued = {}

        def queue_workflow(workflow, **_kwargs):
            queued["workflow"] = workflow
            return "prompt-h3-native-audio", [{"kind": "video"}]

        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(
                main,
                "_video_model_files",
                return_value=[main.MINIMAX_H3_MODEL_NAME],
            ),
            patch.object(main, "_queue_comfy_workflow", side_effect=queue_workflow),
            patch.object(
                main,
                "_finalize_video_mp4",
                return_value=[{"kind": "video", "path": "native-audio.mp4"}],
            ),
        ):
            result = main._run_generative(**normalized)

        workflow = queued["workflow"]
        self.assertEqual(workflow["17"]["inputs"]["vae_name"], main.MINIMAX_H3_AUDIO_VAE)
        self.assertEqual(workflow["18"]["inputs"]["samples"], ["12", 1])
        self.assertEqual(workflow["15"]["inputs"]["audio"], ["18", 0])
        self.assertIs(result["native_audio_enabled"], True)

    def test_vertical_minimax_h3_profile_selects_h3_model(self):
        model = main._video_take_model_for_spec({
            "generationProfile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
        })

        self.assertEqual(model, main.MINIMAX_H3_MODEL_NAME)

    def test_ref2va_take_selects_separate_ref2va_checkpoint(self):
        model = main._video_take_model_for_spec({
            "generationProfile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
            "minimaxAnchorControl": {"mode": "ref2va_motion"},
        })

        self.assertEqual(model, main.MINIMAX_H3_REF2VA_MODEL_NAME)

    def test_ref2va_explicit_checkpoint_survives_engine_resolution(self):
        spec = _spec("video")
        spec.update({
            "model": main.MINIMAX_H3_REF2VA_MODEL_NAME,
            "width": 1088,
            "height": 608,
            "frames": 124,
            "fps": 24.0,
            "video_duration": 124 / 24,
            "steps": 10,
            "guidance": 1.0,
            "minimax_reference_images": [(b"approved-reference", "identity.png")],
            "minimax_reference_mode": "ref2va_motion",
            "strict_video_model": True,
            "allow_validated_video_geometry": True,
            "visual_only_pass": True,
            "enable_minimax_h3_native_audio": False,
            "h3_quality_profile": "h3_production",
        })
        queued = {}

        def queue_workflow(workflow, **_kwargs):
            queued["workflow"] = workflow
            return "prompt-ref2va", [{"kind": "video"}]

        with (
            patch.object(main, "_require_authorized_video_engine"),
            patch.object(main, "_comfy_online", return_value=(True, {})),
            patch.object(main, "_model_files", return_value=[]),
            patch.object(
                main,
                "_video_model_files",
                return_value=[main.MINIMAX_H3_MODEL_NAME, main.MINIMAX_H3_REF2VA_MODEL_NAME],
            ),
            patch.object(main, "_save_comfy_input_image", return_value="identity.png"),
            patch.object(main, "_queue_comfy_workflow", side_effect=queue_workflow),
            patch.object(
                main,
                "_finalize_video_mp4",
                return_value=[{"kind": "video", "path": "ref2va.mp4"}],
            ),
        ):
            result = main._run_generative(**spec)

        self.assertEqual(result["model"], main.MINIMAX_H3_REF2VA_MODEL_NAME)
        self.assertEqual(
            queued["workflow"]["1"]["inputs"]["unet_name"],
            main.MINIMAX_H3_REF2VA_MODEL_NAME,
        )
        self.assertEqual(
            queued["workflow"]["6"]["class_type"],
            "MiniMaxH3ReferenceToVideo",
        )

    def test_ref2va_preflight_fails_closed_when_separate_checkpoint_is_missing(self):
        keyframe = Path(self.temp_dir.name) / "ref-start.png"
        keyframe.write_bytes(b"approved")
        spec = {
            "status": "PLANNED",
            "generationProfile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
            "keyframe": keyframe,
            "minimaxAnchorControl": {
                "mode": "ref2va_motion",
                "referenceImages": [],
                "referenceVideo": None,
            },
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_minimax_h3_kit_ready", return_value=True),
            patch.object(main, "_minimax_h3_ref2va_ready", return_value=False),
        ):
            with self.assertRaises(main.TakeJobConflict) as caught:
                main._preflight_video_take_job("film", "S01")

        self.assertEqual(caught.exception.code, "REF2VA_MODEL_NOT_READY")

    def test_minimax_h3_integrity_cache_survives_studio_restart(self):
        root = Path(self.temp_dir.name) / "models"
        components = {
            ("diffusion_models", "model.safetensors"): b"model",
            ("text_encoders", "text.safetensors"): b"text",
            ("vae", "video.safetensors"): b"video",
            ("vae", "audio.safetensors"): b"audio",
        }
        registry = {}
        for (folder, filename), payload in components.items():
            path = root / folder / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            registry[(folder, filename)] = (len(payload), hashlib.sha256(payload).hexdigest())
        cache_path = Path(self.temp_dir.name) / "minimax_h3_integrity_cache.json"

        with (
            patch.object(main, "COMFY_MODELS_DIR", str(root)),
            patch.object(main, "MINIMAX_H3_COMPONENTS", registry),
            patch.object(main, "_MINIMAX_H3_INTEGRITY_CACHE_PATH", cache_path),
            patch.object(main, "_MINIMAX_H3_INTEGRITY_CACHE", {"signature": None, "ok": False}),
        ):
            self.assertTrue(main._minimax_h3_kit_ready(verify_hash=True))
            self.assertTrue(cache_path.is_file())
            main._MINIMAX_H3_INTEGRITY_CACHE.update({"signature": None, "ok": False})
            with patch.object(main.hashlib, "sha256", side_effect=AssertionError("rehash")):
                self.assertTrue(main._minimax_h3_kit_ready(verify_hash=True))

    def test_h3_long_take_forwards_approved_end_frame_to_worker(self):
        keyframe = Path(self.temp_dir.name) / "take040_start.png"
        end_frame = Path(self.temp_dir.name) / "take040_end.png"
        keyframe.write_bytes(b"start-image")
        end_frame.write_bytes(b"end-image")
        spec = {
            "status": "PLANNED",
            "prompt": "Plano continuo com inicio, virada, reacao e despedida.",
            "negative": "visible text, subtitles, pt-PT",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "frames": 243,
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "durationSeconds": 10.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
            "endKeyframe": end_frame,
            "endKeyframeName": end_frame.name,
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_minimax_h3_kit_ready", return_value=True),
            patch.object(main, "_set_take_generation_state"),
            patch.object(main, "_launch_video_take_worker") as launcher,
        ):
            started = main._start_video_take_job("curta", "040", seed=8040)

        job = self.store.get(started["jobId"])
        self.assertEqual(job["frames"], 243)
        self.assertEqual(job["end_image_name"], end_frame.name)
        self.assertFalse(job["auto_resume"])
        self.assertEqual(launcher.call_args.kwargs["end_bytes"], b"end-image")

    def test_removed_ltx_take_stops_before_worker_launch(self):
        keyframe = Path(self.temp_dir.name) / "take015.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "PLANNED",
            "prompt": "Movimento continuo controlado.",
            "negative": "visible text",
            "generationProfile": "ltx23_distilled_fp8_720p",
            "width": 1280,
            "height": 720,
            "frames": 145,
            "fps": 24,
            "steps": 8,
            "guidance": 1.0,
            "durationSeconds": 6.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        with (
            patch.object(main, "_get_take_generation_spec", return_value=spec),
            patch.object(main, "_set_take_generation_state") as set_state,
            patch.object(main, "_run_generative") as run_generative,
        ):
            with self.assertRaises(main._VideoEngineError) as caught:
                main._start_video_take_job("curta", "015", seed=1501)

        self.assertEqual(caught.exception.code, "ENGINE_NOT_ALLOWED")
        run_generative.assert_not_called()
        set_state.assert_not_called()

    def test_video_take_queue_runs_h3_jobs_one_at_a_time_in_fifo_order(self):
        keyframe = Path(self.temp_dir.name) / "take-fifo.png"
        keyframe.write_bytes(b"base-image")
        spec = {
            "status": "PLANNED",
            "prompt": "Movimento controlado.",
            "negative": "visible text",
            "generationProfile": "minimax_h3_fl2va_int8_720p24",
            "width": 1280,
            "height": 720,
            "frames": 141,
            "fps": 24,
            "steps": 20,
            "guidance": 1.0,
            "durationSeconds": 6.0,
            "keyframe": keyframe,
            "keyframeName": keyframe.name,
        }
        first_started = threading.Event()
        release_first = threading.Event()
        second_started = threading.Event()
        execution_order = []

        def fake_run_generative(**kwargs):
            seed = int(kwargs["seed"])
            execution_order.append(seed)
            if seed == 101:
                first_started.set()
                release_first.wait(timeout=2)
            else:
                second_started.set()
            return {"ok": True, "mode": "video", "outputs": []}

        preview = Path(self.temp_dir.name) / "preview.mp4"
        preview.write_bytes(b"preview")
        try:
            with (
                patch.object(main, "_get_take_generation_spec", return_value=spec),
                patch.object(main, "_minimax_h3_kit_ready", return_value=True),
                patch.object(main, "_set_take_generation_state"),
                patch.object(main, "_run_generative", side_effect=fake_run_generative),
                patch.object(main, "_materialize_video_take_preview", return_value=preview),
                patch.object(main, "_attach_take_audio_delivery", return_value=preview),
                patch.object(main, "_is_internal_request", return_value=True),
                patch.object(
                    main,
                    "_comfy_request",
                    return_value={"queue_running": [], "queue_pending": []},
                ),
            ):
                first = main._start_video_take_job("curta", "001", seed=101)
                second = main._start_video_take_job("curta", "002", seed=202)

                self.assertTrue(first_started.wait(timeout=1))
                time.sleep(0.1)
                self.assertFalse(second_started.is_set())
                queued = self.store.get(second["jobId"])
                self.assertEqual(queued["status"], "queued")
                self.assertEqual(queued["queue_mode"], "serial")
                self.assertIn("fila serial", queued["message"].lower())
                queue = asyncio.run(
                    main.generative_queue(SimpleNamespace(headers={}, client=None))
                )
                self.assertEqual((queue["running"], queue["pending"]), (1, 1))
                self.assertEqual(
                    [item["jobId"] for item in queue["items"]],
                    [first["jobId"], second["jobId"]],
                )

                release_first.set()
                self.assertEqual(self.wait_terminal(first["jobId"])["status"], "done")
                self.assertEqual(self.wait_terminal(second["jobId"])["status"], "done")
        finally:
            release_first.set()
            main._wake_video_take_queue()

        self.assertEqual(execution_order, [101, 202])

    def test_wan_output_is_atomically_materialized_inside_the_project(self):
        root = Path(self.temp_dir.name)
        project_root = root / "projects"
        comfy_root = root / "comfy_output"
        create_project(project_root, name="Materializacao")
        source = comfy_root / "maestro_generative" / "video_00001.mp4"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"valid-video-payload")
        result = {
            "outputs": [{
                "kind": "video",
                "filename": source.name,
                "subfolder": "maestro_generative",
                "type": "output",
            }],
        }
        self.store.update(
            "job-preview-1",
            model="wan-test",
            seed=123,
            prompt_id="prompt-test",
            width=768,
            height=432,
            frames=121,
            fps=30,
        )

        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", project_root),
            patch.object(main, "COMFY_OUTPUT_DIR", str(comfy_root)),
            patch.object(
                main,
                "_inspect_video_temporal_motion",
                return_value={"status": "PASS", "detector": "test"},
            ),
        ):
            first = main._materialize_video_take_preview(
                "materializacao", "01", "job-preview-1", result
            )
            second = main._materialize_video_take_preview(
                "materializacao", "01", "job-preview-1", result
            )

        expected_root = (project_root / "materializacao" / "takes" / "maestro_generated").resolve()
        self.assertEqual(first, second)
        self.assertTrue(first.is_relative_to(expected_root))
        self.assertEqual(first.read_bytes(), source.read_bytes())
        sidecar = first.with_suffix(f"{first.suffix}.json")
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(metadata["job_id"], "job-preview-1")
        self.assertEqual(metadata["source"]["subfolder"], "maestro_generative")
        self.assertEqual(metadata["source"]["sha256"], metadata["registered_preview"]["sha256"])
        self.assertEqual(metadata["motion_qc"]["status"], "PASS")

    def test_locked_vertical_h3_review_policy_publishes_rife60_and_preserves_native24(self):
        root = Path(self.temp_dir.name)
        project_root = root / "projects"
        studio_output = root / "studio_output"
        create_project(project_root, name="Materializacao H3 vertical travada")
        source = studio_output / "video" / "20260808" / "h3-vertical.mp4"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"valid-h3-vertical-native24-payload")
        result = {
            "model": main.MINIMAX_H3_MODEL_NAME,
            "outputs": [{
                "kind": "video",
                "filename": source.name,
                "path": "video/20260808/h3-vertical.mp4",
            }],
        }
        self.store.update(
            "job-h3-vertical-locked",
            model=main.MINIMAX_H3_MODEL_NAME,
            generation_profile=main.MINIMAX_H3_VERTICAL_PROFILE,
            seed=908,
            width=720,
            height=1280,
            frames=243,
            fps=24,
        )

        def fake_review_pipeline(*, source, output, **kwargs):
            del kwargs
            self.assertIn("_minimax_h3_native24", source.name)
            output.write_bytes(b"valid-h3-rife425-retime60-payload")
            return {
                "locked_approved": True,
                "pipeline_version": "h3_vertical_rife425_midpoint48_cfr60_duration_v1",
                "source": {"fps": "24/1", "frames": 243},
                "interpolation": {
                    "engine": "Practical-RIFE",
                    "model": "4.25",
                    "mode": "single_midpoint_between_adjacent_source_frames",
                    "direct_factor5_forbidden": True,
                },
                "delivery": {
                    "fps": 60,
                    "frames": 605,
                    "duration_seconds": 10.083333,
                    "width": 720,
                    "height": 1280,
                    "encoder": "h264_nvenc",
                    "speed_factor_from_midpoint_48fps": 1.25,
                },
            }

        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", project_root),
            patch.object(main, "STUDIO_OUTPUT_DIR", str(studio_output)),
            patch.object(main, "_load_ltx_review_pipeline_policy", return_value={"enabled": True}),
            patch.object(main, "_run_ltx_review_pipeline", side_effect=fake_review_pipeline),
            patch.object(main, "_inspect_video_temporal_motion", return_value={"status": "PASS"}),
        ):
            preview = main._materialize_video_take_preview(
                "materializacao_h3_vertical_travada",
                "001",
                "job-h3-vertical-locked",
                result,
            )

        self.assertIn("_minimax_h3_rife425_retime60_preview", preview.name)
        self.assertEqual(preview.read_bytes(), b"valid-h3-rife425-retime60-payload")
        native = preview.with_name(preview.name.replace("_rife425_retime60_preview", "_native24"))
        self.assertTrue(native.is_file())
        self.assertEqual(native.read_bytes(), source.read_bytes())
        self.assertEqual(result["review_pipeline"]["delivery"]["fps"], 60)
        self.assertEqual(result["review_pipeline"]["native_preview_path"], str(native.resolve()))

    def test_temporal_motion_gate_rejects_a_frozen_first_frame(self):
        completed = SimpleNamespace(
            returncode=0,
            stderr=(
                "[Parsed_freezedetect_0] "
                "lavfi.freezedetect.freeze_start: 0\n"
            ),
            stdout="",
        )
        with patch.object(main.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "QC_MOTION_FROZEN"):
                main._inspect_video_temporal_motion(Path("frozen.mp4"))

    def test_temporal_motion_gate_accepts_motion_after_a_short_hold(self):
        completed = SimpleNamespace(
            returncode=0,
            stderr=(
                "Duration: 00:00:04.00\n"
                "[Parsed_freezedetect_0] lavfi.freezedetect.freeze_start: 0\n"
                "[Parsed_freezedetect_0] lavfi.freezedetect.freeze_end: 0.9\n"
            ),
            stdout="",
        )
        with patch.object(main.subprocess, "run", return_value=completed) as run:
            qc = main._inspect_video_temporal_motion(Path("moving.mp4"))
        self.assertEqual(qc["status"], "PASS")
        self.assertLess(qc["freeze_ratio"], 0.70)
        self.assertIn("freezedetect=n=-45dB:d=0.75", run.call_args.args[0])

    def test_temporal_motion_gate_rejects_mostly_frozen_video(self):
        completed = SimpleNamespace(
            returncode=0,
            stderr=(
                "Duration: 00:00:04.00\n"
                "[Parsed_freezedetect_0] lavfi.freezedetect.freeze_start: 0\n"
                "[Parsed_freezedetect_0] lavfi.freezedetect.freeze_end: 1.5\n"
                "[Parsed_freezedetect_0] lavfi.freezedetect.freeze_start: 1.8\n"
                "[Parsed_freezedetect_0] lavfi.freezedetect.freeze_end: 3.7\n"
            ),
            stdout="",
        )
        with patch.object(main.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "QC_MOTION_INSUFFICIENT"):
                main._inspect_video_temporal_motion(Path("mostly-frozen.mp4"))

    def test_human_cast_surge_gate_rejects_a_generated_crowd(self):
        with self.assertRaisesRegex(RuntimeError, "QC_CAST_SURGE"):
            main._assess_detected_human_face_counts(
                [1, 5, 8, 5, 4, 3, 4, 4, 4, 3],
                expected_human_count=3,
            )

        with self.assertRaisesRegex(RuntimeError, "QC_CAST_SURGE"):
            main._assess_detected_human_face_counts(
                [1, 2, 1, 2, 2, 3, 2, 2, 0, 0],
                expected_human_count=1,
            )

        # Regression from Pyramix take 019: the anchor contains only Pedro and
        # Lira, while the rejected render grows to four face-like bodies.
        with self.assertRaisesRegex(RuntimeError, "QC_CAST_SURGE"):
            main._assess_detected_human_face_counts(
                [0, 0, 0, 0, 2, 2, 2, 4, 4, 3],
                expected_human_count=1,
                expected_non_human_count=1,
                detector_tolerance=0,
            )

    def test_human_cast_surge_gate_tolerates_detector_noise(self):
        qc = main._assess_detected_human_face_counts(
            [2, 3, 3, 4, 3, 2, 3, 4, 3, 2],
            expected_human_count=3,
        )
        self.assertEqual(qc["status"], "PASS")
        self.assertEqual(qc["peak_detected_faces"], 4)

    def test_eye_verified_cast_gate_has_no_extra_false_positive_tolerance(self):
        qc = main._assess_detected_human_face_counts(
            [1, 0, 1, 1, 0],
            expected_human_count=1,
            detector_tolerance=0,
        )
        self.assertEqual(qc["status"], "PASS")
        self.assertEqual(qc["detector_tolerance"], 0)

        with self.assertRaisesRegex(RuntimeError, "QC_CAST_SURGE"):
            main._assess_detected_human_face_counts(
                [1, 2, 2, 2, 1],
                expected_human_count=1,
                detector_tolerance=0,
            )

    def test_human_cast_surge_gate_counts_named_stylized_faces_in_baseline(self):
        qc = main._assess_detected_human_face_counts(
            [2, 1, 1, 5, 3, 1, 2, 1, 1, 0],
            expected_human_count=1,
            expected_non_human_count=2,
        )

        self.assertEqual(qc["status"], "PASS")
        self.assertEqual(qc["expected_face_like_count"], 3)
        self.assertEqual(qc["peak_detected_faces"], 5)

    def test_interrupted_current_take_resumes_with_the_same_job_id(self):
        project_root = Path(self.temp_dir.name) / "projects"
        create_project(project_root, name="Recuperacao")
        project = project_root / "recuperacao"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"fake-png-for-mocked-generator")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Camera avanca.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "shot_contract": {"variants": {"duration_seconds": 4}},
            "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24"},
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        set_take_generation_state(
            project_root,
            "recuperacao",
            "01",
            status="GENERATING",
            job_id="job-take-1",
        )
        self.store.update(
            "job-take-1",
            status="interrupted",
            progress=9,
            project_id="recuperacao",
            take_id="01",
            mode="video",
            seed=123,
            auto_resume=True,
        )
        fake_result = {"ok": True, "mode": "video", "outputs": []}
        recovered_preview = project / "takes" / "maestro_generated" / "take_01_recovered.mp4"
        recovered_preview.parent.mkdir(parents=True, exist_ok=True)
        recovered_preview.write_bytes(b"recovered-video")

        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", project_root),
            patch.object(main, "_wait_for_recovered_video_engine", return_value=None),
            patch.object(main, "_run_generative", return_value=fake_result),
            patch.object(main, "_materialize_video_take_preview", return_value=recovered_preview),
            patch.object(main, "_attach_take_audio_delivery", return_value=recovered_preview),
        ):
            resumed = main._recover_interrupted_video_take_jobs()
            job = self.wait_terminal("job-take-1")

        self.assertEqual(resumed, ["job-take-1"])
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["resume_count"], 1)
        self.assertEqual(list_takes(project_root, "recuperacao")["data"][0]["status"], "READY")

    def test_interrupted_non_resumable_take_is_unlocked_for_new_request(self):
        project_root = Path(self.temp_dir.name) / "projects"
        create_project(
            project_root,
            name="Recuperacao manual",
            project_id="recuperacao-manual",
        )
        project = project_root / "recuperacao-manual"
        keyframe = project / "keyframes" / "take01.png"
        keyframe.write_bytes(b"fake-png-for-retry")
        queue_path = project / "take_queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["takes"] = [{
            "id": "01",
            "animation_prompt": "Camera avanca.",
            "base_image": {"status": "approved_for_video", "file": str(keyframe)},
            "shot_contract": {"variants": {"duration_seconds": 4}},
            "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24"},
            "video": {"status": "pending"},
            "qc": {},
        }]
        queue_path.write_text(json.dumps(queue), encoding="utf-8")
        set_take_generation_state(
            project_root,
            "recuperacao-manual",
            "01",
            status="GENERATING",
            job_id="job-manual-retry",
        )
        self.store.update(
            "job-manual-retry",
            status="interrupted",
            progress=8,
            project_id="recuperacao-manual",
            take_id="01",
            mode="video",
            job_kind="video_take",
            auto_resume=False,
        )

        with patch.object(main, "VIDEO_PROJECTS_ROOT", project_root):
            resumed = main._recover_interrupted_video_take_jobs()

        take = list_takes(project_root, "recuperacao-manual")["data"][0]
        job = self.store.get("job-manual-retry")
        self.assertEqual(resumed, [])
        self.assertEqual(take["status"], "ERROR")
        self.assertTrue(take["canGenerate"])
        self.assertEqual(job["status"], "interrupted")
        self.assertTrue(job["recoverable"])
        self.assertIn("liberado", job["message"])

    def test_job_progress_never_moves_backwards_between_pipeline_stages(self):
        self.store.update("monotonic-job", status="running", progress=33)

        main._set_gen_job("monotonic-job", status="running", progress=8, message="nova etapa")

        job = self.store.get("monotonic-job")
        self.assertEqual(job["progress"], 33)
        self.assertEqual(job["message"], "nova etapa")

    def test_audio_qc_failure_preserves_completed_video_candidate(self):
        projects = Path(self.temp_dir.name) / "projects"
        preview = projects / "curta" / "takes" / "preserved.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"completed-video")
        result = {"review_pipeline": {"status": "PENDING_HUMAN_REVIEW", "qc": {}}}
        progress = []

        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", projects),
            patch.object(main, "_materialize_video_take_preview", return_value=preview),
            patch.object(main, "_apply_take_editorial_lettering", return_value=preview),
            patch.object(
                main,
                "_attach_take_audio_delivery",
                side_effect=RuntimeError("ASR temporariamente indisponivel"),
            ),
            patch.object(main, "_probe_audio_delivery_media", return_value={
                "audio": {"codec_name": "aac", "sample_rate": "48000", "channels": 2},
                "has_audio": True,
            }),
        ):
            delivered, audio_blocked = main._finalize_video_take_candidate(
                "curta",
                "006",
                "job-preserved",
                result,
                progress_cb=lambda pct, msg: progress.append((pct, msg)),
                cancel_event=threading.Event(),
                process_cb=lambda _process: None,
            )

        self.assertEqual(delivered, preview.resolve())
        self.assertTrue(audio_blocked)
        self.assertEqual(result["approval_status"], "PENDING_HUMAN_REVIEW_AUDIO_BLOCKED")
        delivery = result["audio_delivery"]
        self.assertFalse(delivery["ready"])
        self.assertTrue(delivery["approval_blocked"])
        self.assertIn("CANDIDATE_PRESERVED", result["postprocess_warnings"][0]["status"])
        self.assertEqual(result["review_pipeline"]["status"], "PENDING_HUMAN_REVIEW_AUDIO_BLOCKED")
        self.assertEqual(progress[-1][0], 99)

    def test_ptbr_exact_speech_gate_normalizes_only_accents_and_punctuation(self):
        expected = "Pedro, você prefere contar os sons ou marcar o silêncio para nós?"
        transcript = "Pedro, voce prefere contar os sons ou marcar o silencio para nos."
        self.assertEqual(
            main._normalize_spoken_ptbr(expected),
            main._normalize_spoken_ptbr(transcript),
        )
        self.assertNotEqual(
            main._normalize_spoken_ptbr(expected),
            main._normalize_spoken_ptbr("Pedro, você prefere cortar os sons."),
        )

    def test_ptbr_asr_near_homophone_preserves_render_only_for_human_listening(self):
        assessment = main._assess_spoken_ptbr_asr(
            "Mais baixo, por favor. Assim eu consigo prestar atenção.",
            "Mas baixo, por favor, assim eu consigo prestar atenção.",
        )
        self.assertTrue(assessment["accepted_for_human_review"])
        self.assertFalse(assessment["exact"])
        self.assertEqual(
            assessment["status"],
            "ASR_NEAR_HOMOPHONE_REQUIRES_HUMAN_LISTENING",
        )
        self.assertEqual(assessment["ambiguous_tokens"], [{
            "index": 0,
            "expected": "mais",
            "transcribed": "mas",
        }])
        mismatch = main._assess_spoken_ptbr_asr(
            "Mais baixo, por favor.",
            "Fale alto agora.",
        )
        self.assertFalse(mismatch["accepted_for_human_review"])
        self.assertEqual(mismatch["status"], "TEXT_MISMATCH")

    def test_ptbr_asr_phonetic_segmentation_ambiguity_reaches_human_review(self):
        cases = [
            (
                "Claro. Vou baixar o volume e tocar só uma nota. Assim?",
                "Claro! Vou baixar o volume e tocar soma nota. Assim?",
            ),
            (
                "Assim tá bom. A passagem acendeu. Vamos agora, antes que ela apague de novo.",
                "Acinta bom, a passagem acendeu, vamos agora, antes que ela pague de novo.",
            ),
            (
                "A peça encaixa direitinho, mas o ritmo trava antes do final.",
                "A peça em caixa direitinho, mas o ritmo trava antes do final.",
            ),
        ]
        for expected, transcript in cases:
            with self.subTest(transcript=transcript):
                assessment = main._assess_spoken_ptbr_asr(expected, transcript)
                self.assertTrue(assessment["accepted_for_human_review"])
                self.assertFalse(assessment["exact"])
                self.assertEqual(
                    assessment["status"],
                    "ASR_PHONETIC_AMBIGUITY_REQUIRES_HUMAN_LISTENING",
                )

    def test_ptbr_asr_rejects_repetition_and_semantic_negation_change(self):
        expected = "A peça encaixa direitinho, mas o ritmo trava antes do final."
        repeated = f"{expected} {expected}"
        repetition = main._assess_spoken_ptbr_asr(expected, repeated)
        self.assertFalse(repetition["accepted_for_human_review"])
        self.assertEqual(repetition["status"], "TEXT_MISMATCH")

        negation = main._assess_spoken_ptbr_asr(
            "Pedro não deve sair da caverna.",
            "Pedro deve sair da caverna.",
        )
        self.assertFalse(negation["accepted_for_human_review"])
        self.assertEqual(negation["status"], "TEXT_MISMATCH")

    def test_ptbr_exact_repetition_boundary_uses_whisper_word_timestamps(self):
        expected = "A peça encaixa direitinho, mas o ritmo trava antes do final."
        tokens = main._normalize_spoken_ptbr(expected).split()
        words = [
            {"text": token, "start": index * 0.2, "end": (index + 1) * 0.2}
            for index, token in enumerate(tokens + tokens)
        ]
        boundary = main._ptbr_exact_repetition_boundary(expected, {"words": words})
        self.assertAlmostEqual(boundary, len(tokens) * 0.2)

    def test_conditioned_audio_timeline_delays_reactions_until_after_speech(self):
        prompt = main._append_ltx_conditioned_audio_timeline(
            "Lira performs one controlled action.",
            {
                "tts_generation": {
                    "conditioning_alignment": {
                        "dialogue_start_seconds": 1.1,
                        "speech_duration_seconds": 3.6,
                    },
                    "asr_gate": {
                        "words": [
                            {"text": "Claro", "start": 0.0, "end": 0.5},
                            {"text": "Assim", "start": 3.1, "end": 3.4},
                        ],
                    },
                },
            },
        )
        self.assertIn("0.00-1.10s is a silent setup", prompt)
        self.assertIn("1.10-4.50s is the only authorized articulation", prompt)
        self.assertIn("Reactions caused by the line begin only after 4.50s", prompt)
        self.assertNotIn("Claro", prompt)

    def test_native_h3_music_preserves_video_and_requires_music_review(self):
        projects = Path(self.temp_dir.name) / "projects"
        preview = projects / "dupla" / "takes" / "take001_music.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"native-h3-music-video")
        result = {"review_pipeline": {"delivery": {}, "qc": {}}}
        spec = {
            "required": True,
            "dialogueRequired": False,
            "musicRequired": True,
            "strategy": "minimax_h3_native_music",
            "musicDirection": "Original upbeat K-pop-inspired instrumental, no lyrics.",
        }
        probe = {
            "audio": {"codec_name": "aac", "sample_rate": "48000", "channels": 2},
            "has_audio": True,
        }
        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", projects),
            patch.object(main, "_get_take_audio_delivery_spec", return_value=spec),
            patch.object(main, "_probe_audio_delivery_media", return_value=probe),
        ):
            delivered = main._attach_take_audio_delivery("dupla", "001", preview, result)

        self.assertEqual(delivered, preview.resolve())
        delivery = result["audio_delivery"]
        self.assertEqual(
            delivery["status"],
            "NATIVE_MINIMAX_H3_MUSIC_ATTACHED_PENDING_HUMAN_REVIEW",
        )
        self.assertEqual(delivery["source_kind"], "minimax_h3_native_music")
        self.assertTrue(delivery["music_required"])
        self.assertTrue(delivery["human_listening_required"])
        self.assertEqual(
            result["review_pipeline"]["delivery"]["audio"],
            "minimax_h3_native_music_aac",
        )
        self.assertTrue(result["review_pipeline"]["qc"]["human_music_listening_required"])

    def test_native_h3_music_marks_joint_dialogue_for_review(self):
        projects = Path(self.temp_dir.name) / "projects"
        preview = projects / "luffy" / "takes" / "take001_joint_av.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"native-h3-joint-av-video")
        result = {"review_pipeline": {"delivery": {}, "qc": {}}}
        spec = {
            "required": True,
            "dialogueRequired": True,
            "musicRequired": True,
            "strategy": "minimax_h3_native_music",
            "musicDirection": "Original cinematic score, no lyrics.",
        }
        probe = {
            "audio": {"codec_name": "aac", "sample_rate": "32000", "channels": 2},
            "has_audio": True,
        }
        with (
            patch.object(main, "VIDEO_PROJECTS_ROOT", projects),
            patch.object(main, "_get_take_audio_delivery_spec", return_value=spec),
            patch.object(main, "_probe_audio_delivery_media", return_value=probe),
        ):
            main._attach_take_audio_delivery("luffy", "001", preview, result)

        delivery = result["audio_delivery"]
        self.assertTrue(delivery["dialogue_required"])
        self.assertEqual(delivery["source_review_status"], "generated_pending_asr_and_human_listening")
        self.assertTrue(result["review_pipeline"]["qc"]["human_dialogue_listening_required"])

    def test_levo2_workflow_is_instrumental_bounded_and_uses_trained_nodes(self):
        workflow = levo_music.build_levo2_workflow(
            "dark cinematic arena score, martial percussion, 96 bpm",
            "vocals, cheerful melody",
            15,
            "maestro_generative/music/test",
        )

        self.assertEqual(workflow["1"]["class_type"], "SongGeneration_Loader")
        self.assertEqual(workflow["3"]["inputs"]["gen_type"], "bgm")
        self.assertEqual(workflow["3"]["inputs"]["duration_seconds"], 15)
        self.assertIn("Avoid these elements", workflow["3"]["inputs"]["description"])
        self.assertIn("[inst-medium]", workflow["2"]["inputs"]["lyric"])

        with self.assertRaisesRegex(ValueError, "piloto de 5 a 15"):
            levo_music.build_levo2_workflow("score", "", 60, "test")

    def test_levo2_provider_status_is_safe_and_music_only(self):
        fake = {
            "label": "LeVo 2 local (RTX 5090)",
            "configured": True,
            "modes": ["music"],
            "message": "pronto",
        }
        with patch.object(main, "_levo2_status", return_value=fake):
            providers = main._audio_provider_status()

        self.assertEqual(providers[main.LEVO2_PROVIDER_ID]["modes"], ["music"])
        self.assertNotIn("path", json.dumps(providers[main.LEVO2_PROVIDER_ID]).lower())
        self.assertEqual(providers["eleven_sfx"]["modes"], ["sfx"])

    def test_levo2_dispatch_marks_pilot_for_human_review(self):
        spec = _spec("music")
        spec.update({"provider": main.LEVO2_PROVIDER_ID, "duration": 15})
        cancel_event = threading.Event()
        process_cb = object()
        candidate = {
            "data": b"fLaC-neural-pilot",
            "extension": ".flac",
            "media_type": "audio/flac",
            "duration_seconds": 15,
            "model": "Tencent SongGeneration LeVo 2 v2-large",
        }
        with (
            patch.object(main, "_run_levo2_music", return_value=candidate) as run,
            patch.object(
                main,
                "_write_studio_output",
                return_value={"kind": "audio", "url": "/api/generative/output?path=test.flac"},
            ),
        ):
            result = main._run_generative(
                **spec,
                cancel_event=cancel_event,
                process_cb=process_cb,
            )

        self.assertEqual(result["provider"], main.LEVO2_PROVIDER_ID)
        self.assertEqual(result["approval_status"], "PENDING_HUMAN_REVIEW")
        self.assertTrue(result["pilot"])
        self.assertTrue(result["outputs"][0]["requires_human_listening"])
        self.assertIs(run.call_args.kwargs["cancel_event"], cancel_event)
        self.assertIs(run.call_args.kwargs["process_cb"], process_cb)


if __name__ == "__main__":
    unittest.main()
