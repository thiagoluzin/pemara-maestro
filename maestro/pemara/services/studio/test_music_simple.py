"""Prompt-only vocal creation, automatic YuE2 chaining, and local writer contracts."""
import json
import threading
import io
import unittest
from unittest.mock import patch
from music_writer import validate_song, write_song
import music_creation as music
from levo_music import build_levo2_workflow
with patch("urllib.request.urlopen", side_effect=AssertionError("No live service calls in tests")):
    import main
from fastapi.testclient import TestClient

SONG = {"title": "Nova manhã", "caption": "theatrical heavy rock, distorted guitar, male vocals",
        "lyrics": "[Verse]\nEu atravessei a escuridão\n[Chorus]\nAgora a luz está em minha mão",
        "vocal_language": "pt", "instrumental": False}
from test_music_qwen import PLAN
SONG['production_plan'] = PLAN


class SimpleMusicTest(unittest.TestCase):
    def test_prompt_only_form_defaults_to_auto_vocal(self):
        with patch.object(main, "_is_internal_request", return_value=True), \
             patch.object(main, "_start_generative_job", return_value="test") as start:
            response = TestClient(main.app).post("/api/generative/job", data={
                "mode": "music", "provider": music.YUE_ID, "prompt": "Rock pesado sobre esperança"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(start.call_args.args[0]["music_action"], "auto")
        self.assertFalse(start.call_args.args[0]["music_instrumental"])
        self.assertFalse(start.call_args.args[0]["music_abc_reviewed"])

    def test_normalizer_accepts_prompt_without_lyrics_or_score(self):
        spec = main._normalize_generative_job_spec(dict(mode="music", provider=music.YUE_ID,
            prompt="Rock pesado sobre esperança", duration=30))
        self.assertEqual(spec["music_action"], "auto")
        self.assertFalse(spec["music_instrumental"])
        self.assertFalse(spec["music_abc_reviewed"])

    def test_auto_yue_chains_actual_plan_output_into_audio(self):
        graph = music.yue_workflow(prompt=SONG["caption"], lyrics=SONG["lyrics"], instrumental=False,
            duration=30, seed=123, music_action="auto", music_abc="", prefix="audio/test")
        self.assertEqual(graph["2"]["inputs"]["abc"], ["8", 0])
        self.assertEqual(graph["8"]["class_type"], "YuE2GenerateABC")
        self.assertEqual(graph["2"]["inputs"]["lyrics"], SONG["lyrics"])
        self.assertIn("target duration 30 seconds", graph["8"]["inputs"]["style"])
        self.assertIn("Start singing immediately", graph["8"]["inputs"]["style"])
        self.assertIn("SaveAudioAdvanced", [n["class_type"] for n in graph.values()])

    def test_single_job_writes_and_returns_audio_without_score_approval(self):
        def schema(path, **kwargs):
            if path == "/system_stats": return {"devices": [{"vram_free": 30 * 1024**3}]}
            cls = path.rsplit("/", 1)[-1]
            return {cls: {"input": {"required": {"ckpt_name": [[music.YUE_CHECKPOINT]]}}}}
        score = "X:1\nK:C\n% intro\nV: Vocal\nz16|\n% verse\nV: Vocal\nC D E F|"
        score_outputs = [{"kind": "text", "text": score}]
        audio_outputs = [{"kind": "audio", "url": "/test.flac"},
                         {"kind": "text", "node": "10", "text": "{'yue2_truncated': False}"},
                         {"kind": "text", "node": "11", "text": "27.96"}]
        with patch("music_writer.write_song", return_value=dict(SONG)) as writer, \
             patch.object(main, "_prepare_comfy_gpu_for_mova"), \
             patch.object(main, "_comfy_request", side_effect=schema), \
             patch.object(main, "_queue_comfy_workflow", side_effect=[("score-test", score_outputs), ("auto-test", audio_outputs)]) as queue, \
             patch.object(main, "_finish_simple_music", side_effect=lambda result, song, **kw: {**result, **song}) :
            result = main._run_audio_generative(prompt="Rock pesado sobre esperança", mode="music", provider=music.YUE_ID,
                negative="", duration=30, seed=123, prompt_influence=0.5, loop=False,
                music_action="auto", music_instrumental=False)
        writer.assert_called_once()
        self.assertEqual(queue.call_count, 2)
        rendered_score = queue.call_args.args[0]["2"]["inputs"]["abc"]
        self.assertNotIn("% intro", rendered_score)
        self.assertIn("% verse", rendered_score)
        self.assertEqual(result["outputs"][0]["kind"], "audio")
        self.assertEqual(result["approval_status"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(result["lyrics"], SONG["lyrics"])

    def test_failed_writer_does_not_submit_or_fall_back_to_instrumental(self):
        with patch("music_writer.write_song", side_effect=RuntimeError("writer failed")), \
             patch.object(main, "_comfy_request", return_value={"devices": [{"vram_free": 30 * 1024**3}]}), \
             patch.object(main, "_prepare_comfy_gpu_for_mova"), \
             patch.object(main, "_queue_comfy_workflow") as queue:
            with self.assertRaisesRegex(RuntimeError, "writer failed"):
                main._run_audio_generative(prompt="Rock pesado sobre esperança", mode="music", provider=music.YUE_ID,
                    negative="", duration=30, seed=123, prompt_influence=0.5, loop=False,
                    music_action="auto", music_instrumental=False)
            queue.assert_not_called()

    def test_local_writer_uses_gpu_and_releases_model_after_stream(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self):
                yield json.dumps({"response": json.dumps(SONG), "done": True}).encode()
        gpu_state = {"models": [{"name": "qwen3.8-27b-uncensored-yarn-524k:latest", "size": 2000, "size_vram": 2000}]}
        with patch("music_writer.urllib.request.urlopen", side_effect=[Response(), io.BytesIO(json.dumps(gpu_state).encode()),
                   io.BytesIO(b'{"models": []}')]) as call:
            song = write_song("Rock pesado sobre esperança", 30)
        payload = json.loads(call.call_args_list[0].args[0].data)
        self.assertEqual(payload["options"]["num_gpu"], 99)
        self.assertIn("qwen3.8-27b", payload["model"])
        self.assertEqual(payload["keep_alive"], 0)
        self.assertFalse(song["instrumental"])
        self.assertEqual(song["lyrics"], SONG["lyrics"])
        self.assertEqual(song["writer_vram_bytes"], 2000)
        self.assertTrue(song["writer_unloaded"])

    def test_writer_rejects_cpu_or_partial_gpu_placement(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self): yield json.dumps({"response": "{", "done": False}).encode()
        for allocated in (0, 500):
            state = {"models": [{"name": "qwen3.8-27b-uncensored-yarn-524k:latest", "size": 2000, "size_vram": allocated}]}
            with patch("music_writer.urllib.request.urlopen", side_effect=[Response(), io.BytesIO(json.dumps(state).encode())]):
                with self.assertRaisesRegex(RuntimeError, "integralmente na GPU"): write_song("rock", 30)

    def test_writer_rejects_empty_vocals_remote_endpoint_and_cancel(self):
        with self.assertRaises(ValueError): validate_song({**SONG, "lyrics": ""})
        with patch.dict("os.environ", {"MAESTRO_MUSIC_WRITER_URL": "https://remote.example"}):
            with self.assertRaises(ValueError): write_song("a song", 30)
        cancel = threading.Event(); cancel.set()
        with self.assertRaisesRegex(RuntimeError, "cancelada"): write_song("a song", 30, cancel_event=cancel)

    def test_writer_separates_lyrics_from_caption_and_normalizes_sections(self):
        song = validate_song({**SONG, "caption": SONG["caption"] + "\n[Verse 1]\nSome repeated lyric",
                              "lyrics": SONG["lyrics"].replace("[Verse]", "[Verse 1]")})
        self.assertEqual(song["caption"], SONG["caption"])
        self.assertEqual(song["lyrics"], SONG["lyrics"])

    def test_short_vocal_score_removes_intro_preserving_header_and_notes(self):
        score = 'X:1\nM:4/4\nK:C\n% intro\nV: Vocal\nz16|\n% verse\nV: Vocal\nC D E F|'
        self.assertEqual(music.prepare_vocal_score(score, 30), 'X:1\nM:4/4\nK:C\n% verse\nV: Vocal\nC D E F|')
        self.assertEqual(music.prepare_vocal_score(score, 180), score)
        with self.assertRaises(ValueError): music.prepare_vocal_score('', 30)

    def test_supplied_lyrics_and_instrumentals_remain_explicit(self):
        music.validate(music.YUE_ID, "instrumental piano concert", 30, instrumental=True, music_action="auto")
        music.validate(music.ACE_ID, "vocal piano concert", 30, lyrics=SONG["lyrics"], instrumental=False, music_action="auto")
        graph = music.yue_workflow(prompt="instrumental piano concert", lyrics="", instrumental=True,
            duration=30, seed=123, music_action="auto", music_abc="", prefix="audio/test")
        self.assertEqual(graph["8"]["inputs"]["lyrics"], "[Instrumental]")
        with self.assertRaises(ValueError):
            music.validate(music.YUE_ID, "vocal piano concert", 30, lyrics=SONG["lyrics"], instrumental=False,
                           music_action="generate", music_abc="X:1\nK:C\nC D E F|", music_abc_reviewed=False)

    def test_levo_uses_mixed_vocal_with_generated_lyrics(self):
        vocal = build_levo2_workflow(SONG["caption"], "", 15, "audio/test", lyrics=SONG["lyrics"], instrumental=False)
        self.assertEqual(vocal["3"]["inputs"]["gen_type"], "mixed")
        self.assertIn("[verse]", vocal["2"]["inputs"]["lyric"])
        instrumental = build_levo2_workflow("piano concert", "", 15, "audio/test")
        self.assertEqual(instrumental["3"]["inputs"]["gen_type"], "bgm")


if __name__ == "__main__": unittest.main()
