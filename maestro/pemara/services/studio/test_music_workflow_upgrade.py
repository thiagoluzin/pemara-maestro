"""Behavioral regressions: YuE2 default, explicit engines and native direct generation."""
import unittest
from copy import deepcopy
from unittest.mock import patch, MagicMock
import music_creation as music
from music_writer import write_song
from test_music_writer_contract import SONG, METADATA
from test_music_ending import audio
with patch("urllib.request.urlopen", side_effect=AssertionError("No live network in tests")):
    import main


class MusicWorkflowUpgradeTest(unittest.TestCase):
    def test_missing_engine_defaults_to_yue_but_explicit_engine_survives(self):
        base = dict(mode="music", prompt="Original heavy guitar rock", duration=300)
        self.assertEqual(main._normalize_generative_job_spec(base)["provider"], music.YUE_ID)
        self.assertEqual(main._normalize_generative_job_spec({**base, "provider": music.ACE_ID})["provider"], music.ACE_ID)
        self.assertEqual(main._normalize_generative_job_spec({**base, "provider": music.YUE_ID, "music_action":"direct"})["music_action"], "direct")

    def test_status_does_not_replace_unavailable_default_with_ace_or_cloud(self):
        registry = MagicMock()
        registry.describe.return_value = {}
        for ready in (False, True):
            providers = {music.ACE_ID: {"configured":True}, music.YUE_ID: {"configured":ready,"default_duration_seconds":30}}
            with self.subTest(ready=ready), patch.object(main,"_comfy_online",return_value=(False,{})), \
                 patch.object(main,"_video_engine_registry_live",return_value=registry), \
                 patch.object(main,"_video_engine_readiness",return_value={}), \
                 patch.object(main,"_h3_workflow_status_live",return_value={}), \
                 patch.object(main,"_model_files",return_value=[]), \
                 patch.object(main,"_audio_provider_status",return_value=providers), \
                 patch.object(main,"_is_internal_request",return_value=False):
                status = main.generative_status(None)
            self.assertEqual(status["defaults"]["audio_provider"],music.YUE_ID)
            self.assertEqual(status["defaults"]["music_provider"],music.YUE_ID)

    def test_direct_mode_cannot_silently_discard_score_or_change_engine(self):
        for extra in ({"music_abc":"X:1\nK:C\nC|"}, {"music_abc_reviewed":True}, {"music_abc":23}):
            with self.assertRaises(ValueError):
                music.validate(music.YUE_ID, "Original guitar rock", 300, music_action="direct", **extra)
        with self.assertRaises(ValueError):
            music.validate(music.ACE_ID, "Original guitar rock", 300, music_action="direct")

    def test_direct_route_has_no_score_and_retains_truncated_attempt(self):
        calls = []
        def queue(graph):
            calls.append(graph)
            return str(len(calls)), audio(len(calls)==1, 280)
        _, _, evidence = music.run_yue_direct(prompt="Raw thrash guitar, shouted English vocals",
            lyrics="[Verse]\nOriginal words", instrumental=False, duration=300, seed=12, queue=queue)
        self.assertEqual(len(calls),2)
        for graph in calls:
            self.assertNotIn("YuE2GenerateABC", [node["class_type"] for node in graph.values()])
            self.assertEqual(graph["2"]["inputs"]["abc"], "")
            self.assertEqual(graph["2"]["inputs"]["max_duration"],300)
            self.assertNotIn("ABC arrangement", graph["2"]["inputs"]["style"])
        self.assertFalse(evidence["music_attempts"][0]["ending_check"]["end_token_reached"])
        self.assertEqual(evidence["music_attempts"][0]["outputs"][0]["url"],"/candidate.flac")
        self.assertEqual(evidence["effective_yue_mode"],"off")

    def test_direct_repeated_truncation_fails_instead_of_delivering(self):
        with self.assertRaisesRegex(RuntimeError,"duas tentativas"):
            music.run_yue_direct(prompt="Heavy guitar rock",lyrics="",instrumental=True,
                duration=30,seed=1,queue=lambda graph:("attempt",audio(True,25)))

    def test_model_duration_is_a_ceiling_in_direct_mode(self):
        calls=[]
        def queue(graph):
            calls.append(graph)
            return "direct",audio(False,280)
        _,_,evidence=music.run_yue_direct(prompt="Heavy guitar rock",lyrics="",instrumental=True,
            duration=30,seed=1,queue=queue,music_duration_auto=True)
        self.assertEqual(calls[0]["2"]["inputs"]["max_duration"],900)
        self.assertIsNone(evidence["requested_duration_seconds"])
        self.assertNotIn("900 seconds maximum",calls[0]["2"]["inputs"]["style"])

    def test_writer_keeps_compact_sound_direction_separate_from_production_plan(self):
        with patch("music_writer.request_json",return_value=(deepcopy(SONG),METADATA)):
            song=write_song("Original heavy metal in English",300)
        self.assertEqual(song["sonic_caption"],SONG["caption"])
        self.assertIn("Producer style",song["caption"])
        self.assertNotIn("Producer style",song["sonic_caption"])

    def test_backend_direct_uses_qwen_and_preserves_manual_lyrics(self):
        song=deepcopy(SONG)
        song.update({"sonic_caption":"Raw original thrash, forceful English vocals","caption":"Expanded producer plan"})
        metadata={"music_abc":"","effective_yue_mode":"off"}
        with patch("music_writer.write_song",return_value=song) as writer, \
             patch.object(main,"_comfy_request",return_value={"devices":[{"vram_free":30*1024**3}]}), \
             patch.object(main,"_prepare_comfy_gpu_for_mova"), \
             patch.object(music,"run_yue_direct",return_value=("render",[{"kind":"audio","url":"/test.flac"}],metadata)) as direct, \
             patch.object(music,"run_yue_auto") as score, \
             patch.object(main,"_finish_simple_music",side_effect=lambda result,*args,**kw:result):
            result=main._run_audio_generative(prompt="Original heavy metal",mode="music",provider=music.YUE_ID,
                negative="",duration=300,seed=12,prompt_influence=.5,loop=False,music_action="direct",
                music_instrumental=False,music_lyrics=SONG["lyrics"])
        score.assert_not_called()
        self.assertEqual(writer.call_args.kwargs["provided_lyrics"],SONG["lyrics"])
        self.assertEqual(direct.call_args.kwargs["prompt"],song["sonic_caption"])
        self.assertEqual(direct.call_args.kwargs["duration"],300)
        self.assertEqual(result["approval_status"],"PENDING_HUMAN_REVIEW")

    def test_qwen_chosen_duration_is_not_replaced_by_native_fifteen_minute_ceiling(self):
        for action, runner in (("direct","run_yue_direct"),("auto","run_yue_auto")):
            song=deepcopy(SONG)
            metadata={"music_abc":"", "music_duration_auto":False, "requested_duration_seconds":300}
            with self.subTest(action=action), patch("music_writer.write_song",return_value=song), \
                 patch.object(main,"_comfy_request",return_value={"devices":[{"vram_free":30*1024**3}]}), \
                 patch.object(main,"_prepare_comfy_gpu_for_mova"), \
                 patch.object(music,runner,return_value=("render",[{"kind":"audio","url":"/test.flac"}],metadata)) as generate, \
                 patch.object(main,"_finish_simple_music",side_effect=lambda result,*args,**kw:result):
                result=main._run_audio_generative(prompt="Original heavy metal",mode="music",provider=music.YUE_ID,
                    negative="",duration=900,seed=12,prompt_influence=.5,loop=False,music_action=action,
                    music_instrumental=False,music_duration_auto=True)
            self.assertEqual(generate.call_args.kwargs["duration"],300)
            self.assertFalse(generate.call_args.kwargs["music_duration_auto"])
            self.assertTrue(result["music_duration_auto"])
            self.assertEqual(result["duration_decision_source"],"qwen")
            self.assertIsNone(result["requested_duration_seconds"])


if __name__ == "__main__":
    unittest.main()
