"""Music routing, explicit score review, persistence and cancellation contracts."""
import asyncio
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import music_creation as music
# Import never contacts the Comfy service; all service operations below are mocks.
with patch("urllib.request.urlopen", side_effect=AssertionError("No live network in unit tests")):
    import main
from generative_jobs import GenerativeJobStore


def audio_args(provider):
    return dict(prompt="gentle acoustic instrumental piano", mode="music", provider=provider,
                negative="", duration=10, seed=123, prompt_influence=0.5, loop=False)


class MusicCreationTest(unittest.TestCase):
    def test_form_endpoint_preserves_lyrics_and_explicit_model(self):
        from fastapi.testclient import TestClient
        payload = {"prompt": "heavy theatrical guitar rock", "mode": "music", "provider": music.ACE_ID,
                   "duration": "180", "music_lyrics": "[Verse]\nA new original song",
                   "music_instrumental": "false", "music_model": "acestep-v15-xl-base", "music_bpm": "156"}
        with patch.object(main, "_is_internal_request", return_value=True), \
             patch.object(main, "_start_generative_job", return_value="api-song") as start:
            response = TestClient(main.app).post("/api/generative/job", data=payload)
        self.assertEqual(response.status_code, 200)
        request = start.call_args.args[0]
        self.assertFalse(request["music_instrumental"])
        self.assertEqual(request["music_lyrics"], payload["music_lyrics"])
        self.assertEqual(request["music_model"], payload["music_model"])
        self.assertEqual(request["music_bpm"], 156)

    def test_reject_unreviewed_and_malformed_abc(self):
        for abc, reviewed in [("X:1\nK:C\nC D E F|", False), ("random text", True)]:
            with self.assertRaises(ValueError):
                music.validate(music.YUE_ID, "piano concert", 10,
                               music_abc=abc, music_abc_reviewed=reviewed)

    def test_lyrics_and_instrumental_are_explicit(self):
        with self.assertRaises(ValueError):
            music.validate(music.ACE_ID, "piano concert", 10, lyrics="sing this", instrumental=True)
        with self.assertRaises(ValueError):
            music.validate(music.ACE_ID, "piano concert", 10, instrumental=False)
        music.validate(music.ACE_ID, "piano concert", 10, lyrics="[Verse]\nHello", instrumental=False)
        with self.assertRaises(ValueError):
            music.validate(music.ACE_ID, "piano concert", float("nan"))

    def test_planning_never_contains_audio_and_audio_consumes_exact_score(self):
        args = dict(prompt="piano concert", lyrics="", instrumental=True, duration=6,
                    seed=123, music_abc="X:1\nK:C\nC D E F|", prefix="audio/test")
        plan = music.yue_workflow(**args, music_action="plan")
        self.assertNotIn("YuE2GenerateMusic", [n["class_type"] for n in plan.values()])
        graph = music.yue_workflow(**args, music_action="generate")
        self.assertNotIn("YuE2GenerateABC", [n["class_type"] for n in graph.values()])
        self.assertEqual(graph["2"]["inputs"]["abc"], args["music_abc"])
        self.assertEqual(graph["4"]["inputs"]["seconds"], ["2", 1])

    def test_ace_original_output_and_no_provider_fallback(self):
        candidate = dict(data=b"flac-test", extension=".flac", media_type="audio/flac",
                         model="acestep-v15-turbo", seed=123, duration_seconds=10,
                         runtime_commit=music.ACE_COMMIT)
        with patch.object(main, "_comfy_request", return_value={}), \
             patch.object(main, "_prepare_comfy_gpu_for_mova"), \
             patch.object(music, "run_ace", return_value=candidate) as run, \
             patch.object(main, "_finish_simple_music", side_effect=lambda result, *args, **kw: result), \
             patch.object(main, "_write_studio_output", return_value={"kind": "audio", "url": "/test.flac"}):
            result = main._run_audio_generative(**audio_args(music.ACE_ID), gpu_job_id="job-123")
        self.assertEqual(result["provider"], music.ACE_ID)
        self.assertEqual(result["approval_status"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(run.call_args.kwargs["gpu_job_id"], "job-123")
        with patch.object(main, "_run_elevenlabs_music") as cloud:
            with self.assertRaises(ValueError):
                main._run_audio_generative(**audio_args("unknown_engine"))
            cloud.assert_not_called()

    def test_plan_result_survives_restart_without_score_approval(self):
        def schema(path, **kwargs):
            cls = path.rsplit("/", 1)[-1]
            return {cls: {"input": {"required": {"ckpt_name": [[music.YUE_CHECKPOINT]]}}}}
        abc = "X:1\nK:C\nC D E F|"
        with patch.object(main, "_comfy_request", side_effect=schema), \
             patch.object(main, "_queue_comfy_workflow", return_value=("prompt-test", [{"kind": "text", "text": abc}])):
            result = main._run_audio_generative(**audio_args(music.YUE_ID), music_action="plan")
        self.assertEqual(result["outputs"], [])
        self.assertEqual(result["approval_status"], "PENDING_SCORE_REVIEW")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "jobs.json")
            GenerativeJobStore(path).update("plan", status="done", result=result)
            self.assertEqual(GenerativeJobStore(path).get("plan")["result"]["music_abc"], abc)

    def test_local_job_reserves_and_releases_gpu(self):
        with tempfile.TemporaryDirectory() as folder:
            store = GenerativeJobStore(Path(folder, "jobs.json"))
            spec = dict(prompt="gentle piano concert", mode="music", provider=music.ACE_ID,
                        duration=10, music_instrumental=True)
            with patch.object(main, "_GEN_JOB_STORE", store), \
                 patch.object(main, "_persist_job_input", return_value=None), \
                 patch.object(main, "_wait_for_gpu_lease") as acquire, \
                 patch.object(main._GPU_LEASE_REGISTRY, "release") as release, \
                 patch.object(main, "_run_generative", return_value={"ok": True}):
                job_id = main._start_generative_job(spec)
                for _ in range(100):
                    if (store.get(job_id) or {}).get("status") in {"done", "error"}:
                        break
                    time.sleep(0.01)
                self.assertEqual(store.get(job_id)["status"], "done")
                acquire.assert_called_once()
                release.assert_called_once_with(job_id)
                self.assertTrue(store.get(job_id)["request_spec"]["music_instrumental"])

    def test_cancel_terminates_only_owned_worker_and_clears_callback(self):
        event = threading.Event()
        event.set()
        class Process:
            pid = 123
            returncode = None
            def poll(self): return self.returncode
            def terminate(self): self.returncode = -1
            def wait(self, timeout): return self.returncode
        worker = Process()
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(music, "PROJECT", Path(folder)), \
             patch.object(music, "provider_status", return_value={music.ACE_ID: {"configured": True, "models": music.ACE_CHOICES}}), \
             patch.object(music.subprocess, "Popen", return_value=worker):
            callbacks = []
            with self.assertRaisesRegex(RuntimeError, "cancelada"):
                music.run_ace(prompt="piano concert", lyrics="", instrumental=True, duration=10,
                    seed=123, music_model="acestep-v15-turbo", music_bpm=0,
                    cancel_event=event, process_cb=callbacks.append)
            self.assertEqual(worker.returncode, -1)
            self.assertEqual(callbacks, [worker, None])


if __name__ == "__main__":
    unittest.main()
