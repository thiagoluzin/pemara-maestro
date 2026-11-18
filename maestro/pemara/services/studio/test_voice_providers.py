import json
import unittest
import urllib.error
import urllib.parse

from voice_providers import (
    ElevenLabsVoiceProvider,
    VoiceProviderError,
    VoiceSettings,
    chatterbox_expression_settings,
    deterministic_cache_key,
    render_performance_text,
    resolve_chatterbox_settings,
)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ):
        self.body = body
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.headers.update(headers or {})
        self.closed = False

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def getcode(self) -> int:
        return self.status

    def close(self) -> None:
        self.closed = True


class FakeOpener:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if not self.outcomes:
            raise AssertionError("Unexpected HTTP request")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.elevenlabs.io/safe",
        code=status,
        msg="provider failure",
        hdrs={},
        fp=None,
    )


class VoiceProviderTest(unittest.TestCase):
    def _provider(self, opener, **kwargs):
        return ElevenLabsVoiceProvider(
            api_key="SUPER_SECRET_SERVER_KEY",
            opener=opener,
            sleeper=kwargs.pop("sleeper", lambda _seconds: None),
            jitter=kwargs.pop("jitter", lambda: 0.5),
            **kwargs,
        )

    def test_performance_contract_rejects_ssml_and_unknown_tags(self):
        rendered, tags = render_performance_text(
            "Olá, mundo.",
            direction="dramatic",
            audio_tags=["chuckles"],
        )
        self.assertEqual(rendered, "[sighs] [excited] [chuckles] Olá, mundo.")
        self.assertEqual(tags, ("sighs", "excited", "chuckles"))

        with self.assertRaises(VoiceProviderError) as ssml:
            render_performance_text("<speak>Não</speak>")
        self.assertEqual(ssml.exception.code, "SSML_NOT_ALLOWED")

        with self.assertRaises(VoiceProviderError) as tag:
            render_performance_text("[shouts] Não", direction="neutral")
        self.assertEqual(tag.exception.code, "AUDIO_TAG_NOT_ALLOWED")

        with self.assertRaises(VoiceProviderError) as direction:
            render_performance_text("Não", direction="livre")
        self.assertEqual(direction.exception.code, "UNSUPPORTED_DIRECTION")

    def test_cache_key_is_deterministic_and_contains_no_script(self):
        first = deterministic_cache_key(
            text="  Olá\r\nmundo  ",
            voice_id="voice_123",
            model_id="eleven_v3",
            output_format="mp3_44100_128",
        )
        second = deterministic_cache_key(
            text="Olá\nmundo",
            voice_id="voice_123",
            model_id="eleven_v3",
            output_format="mp3_44100_128",
        )
        changed = deterministic_cache_key(
            text="Olá\nmundo",
            voice_id="voice_456",
            model_id="eleven_v3",
            output_format="mp3_44100_128",
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")
        self.assertNotIn("Olá", first)

    def test_expressive_v3_synthesis_returns_audio_and_safe_metadata(self):
        audio = b"ID3" + (b"\x00" * 64)
        opener = FakeOpener(
            FakeResponse(
                audio,
                content_type="audio/mpeg; charset=binary",
                headers={"request-id": "req_safe-123"},
            )
        )
        provider = self._provider(opener)

        result = provider.synthesize(
            text="Vamos começar.",
            voice_id="voice_123",
            preset="expressive_v3",
            direction="intense",
            audio_tags=["sighs"],
            language_code="pt-BR",
        )

        self.assertEqual(result.audio_bytes, audio)
        self.assertEqual(result.metadata["modelId"], "eleven_v3")
        self.assertEqual(result.metadata["requestId"], "req_safe-123")
        self.assertEqual(result.metadata["performance"]["audioTags"], ["excited", "sighs"])
        self.assertNotIn("SUPER_SECRET", repr(result.metadata))
        self.assertNotIn("Vamos", repr(result.metadata))

        request, timeout = opener.requests[0]
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        self.assertEqual(query["output_format"], ["mp3_44100_128"])
        self.assertEqual(query["enable_logging"], ["true"])
        self.assertNotIn("SUPER_SECRET", request.full_url)
        self.assertEqual(request.get_header("Xi-api-key"), "SUPER_SECRET_SERVER_KEY")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model_id"], "eleven_v3")
        self.assertTrue(body["text"].startswith("[excited] [sighs]"))
        self.assertNotIn("voice_settings", body)
        self.assertEqual(timeout, 60.0)

    def test_stable_and_preview_presets_send_supported_settings(self):
        audio = b"ID3" + (b"\x01" * 64)
        stable_opener = FakeOpener(FakeResponse(audio, content_type="audio/mpeg"))
        stable = self._provider(stable_opener)
        stable.synthesize(
            text="Narração longa.",
            voice_id="voice_123",
            preset="stable_longform",
        )
        stable_body = json.loads(stable_opener.requests[0][0].data.decode("utf-8"))
        self.assertEqual(stable_body["model_id"], "eleven_multilingual_v2")
        self.assertEqual(stable_body["voice_settings"]["stability"], 0.62)

        preview_opener = FakeOpener(FakeResponse(audio, content_type="audio/mpeg"))
        preview = self._provider(preview_opener)
        preview.synthesize(
            text="Prévia.",
            voice_id="voice_123",
            preset="preview",
            voice_settings=VoiceSettings(speed=1.1),
        )
        preview_body = json.loads(preview_opener.requests[0][0].data.decode("utf-8"))
        self.assertEqual(preview_body["model_id"], "eleven_flash_v2_5")
        self.assertEqual(preview_body["voice_settings"]["speed"], 1.1)

    def test_non_v3_model_rejects_performance_tags_before_network(self):
        opener = FakeOpener()
        provider = self._provider(opener)
        with self.assertRaises(VoiceProviderError) as caught:
            provider.synthesize(
                text="Teste.",
                voice_id="voice_123",
                preset="stable_longform",
                direction="intense",
            )
        self.assertEqual(caught.exception.code, "AUDIO_TAGS_UNSUPPORTED_BY_MODEL")
        self.assertEqual(opener.requests, [])

    def test_voice_list_and_subscription_are_sanitized(self):
        voices_payload = {
            "voices": [
                {
                    "voice_id": "voice_123",
                    "name": "Narrador",
                    "category": "cloned",
                    "description": "Voz principal",
                    "preview_url": "https://cdn.example.test/voice.mp3",
                    "labels": {"language": "pt-BR"},
                    "provider_internal": "must-not-leak",
                }
            ],
            "has_more": True,
            "next_page_token": "next_1",
            "total_count": 8,
            "unexpected": "must-not-leak",
        }
        subscription_payload = {
            "tier": "creator",
            "character_count": 125,
            "character_limit": 1000,
            "can_extend_character_limit": True,
            "next_character_count_reset_unix": 1_800_000_000,
            "voice_slots_used": 2,
            "voice_limit": 10,
            "professional_voice_limit": 1,
            "billing_private": "must-not-leak",
        }
        opener = FakeOpener(
            FakeResponse(json.dumps(voices_payload).encode("utf-8")),
            FakeResponse(json.dumps(subscription_payload).encode("utf-8")),
        )
        provider = self._provider(opener)

        voices = provider.list_voices(page_size=10, search="Narrador")
        subscription = provider.get_subscription()

        self.assertEqual(voices["items"][0]["voiceId"], "voice_123")
        self.assertEqual(voices["items"][0]["labels"], {"language": "pt-BR"})
        self.assertNotIn("provider_internal", repr(voices))
        self.assertNotIn("unexpected", repr(voices))
        self.assertEqual(subscription["remainingCharacters"], 875)
        self.assertNotIn("billing_private", repr(subscription))

    def test_models_and_remote_capabilities_are_sanitized(self):
        models_payload = [
            {
                "model_id": "eleven_v3",
                "name": "Eleven v3",
                "can_do_text_to_speech": True,
                "can_do_voice_conversion": False,
                "max_characters_request": 5000,
                "languages": [{"language_id": "pt", "name": "Portuguese"}],
            }
        ]
        subscription_payload = {
            "tier": "creator",
            "character_count": 1,
            "character_limit": 100,
        }
        opener = FakeOpener(
            FakeResponse(json.dumps(models_payload).encode("utf-8")),
            FakeResponse(json.dumps(subscription_payload).encode("utf-8")),
        )
        provider = self._provider(opener)
        capabilities = provider.capabilities(include_remote=True)

        self.assertTrue(capabilities["isConfigured"])
        self.assertEqual(capabilities["models"][0]["modelId"], "eleven_v3")
        self.assertEqual(capabilities["subscription"]["remainingCharacters"], 99)
        self.assertIn("expressive_v3", capabilities["presets"])
        self.assertNotIn("SUPER_SECRET_SERVER_KEY", repr(capabilities))

    def test_missing_key_and_provider_errors_never_expose_secret(self):
        missing = ElevenLabsVoiceProvider(api_key="", opener=FakeOpener())
        with self.assertRaises(VoiceProviderError) as missing_error:
            missing.list_voices()
        self.assertEqual(missing_error.exception.code, "CONFIGURATION_ERROR")

        secret = "SUPER_SECRET_SERVER_KEY"
        opener = FakeOpener(http_error(401))
        provider = self._provider(opener)
        with self.assertRaises(VoiceProviderError) as auth_error:
            provider.list_voices()
        serialized = json.dumps(auth_error.exception.to_dict())
        self.assertEqual(auth_error.exception.code, "AUTHENTICATION_FAILED")
        self.assertNotIn(secret, serialized)
        self.assertNotIn(secret, repr(provider))
        self.assertNotIn(secret, repr(provider.capabilities()))

    def test_retry_is_limited_to_429_and_5xx_with_jitter(self):
        sleeps = []
        audio = b"ID3" + (b"\x02" * 64)
        opener = FakeOpener(
            http_error(429),
            http_error(503),
            FakeResponse(audio, content_type="audio/mpeg"),
        )
        provider = self._provider(
            opener,
            sleeper=sleeps.append,
            jitter=lambda: 0.0,
            retry_base_seconds=0.2,
        )
        result = provider.synthesize(text="Teste.", voice_id="voice_123")
        self.assertEqual(result.audio_bytes, audio)
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(sleeps, [0.15000000000000002, 0.30000000000000004])

        rejected_opener = FakeOpener(
            http_error(400),
            FakeResponse(audio, content_type="audio/mpeg"),
        )
        rejected = self._provider(rejected_opener)
        with self.assertRaises(VoiceProviderError) as rejected_error:
            rejected.synthesize(text="Teste.", voice_id="voice_123")
        self.assertEqual(rejected_error.exception.code, "PROVIDER_REJECTED")
        self.assertEqual(len(rejected_opener.requests), 1)

        network_opener = FakeOpener(
            urllib.error.URLError("offline"),
            FakeResponse(audio, content_type="audio/mpeg"),
        )
        network = self._provider(network_opener)
        with self.assertRaises(VoiceProviderError) as network_error:
            network.synthesize(text="Teste.", voice_id="voice_123")
        self.assertEqual(network_error.exception.code, "PROVIDER_CONNECTION_ERROR")
        self.assertEqual(len(network_opener.requests), 1)

    def test_audio_content_type_and_size_are_validated(self):
        invalid_type = self._provider(
            FakeOpener(
                FakeResponse(
                    b'{"error":"not audio"}' + (b" " * 32),
                    content_type="application/json",
                )
            )
        )
        with self.assertRaises(VoiceProviderError) as content_error:
            invalid_type.synthesize(text="Teste.", voice_id="voice_123")
        self.assertEqual(content_error.exception.code, "INVALID_PROVIDER_CONTENT_TYPE")

        oversized = self._provider(
            FakeOpener(
                FakeResponse(
                    b"ID3" + (b"\x00" * 64),
                    content_type="audio/mpeg",
                    headers={"Content-Length": "999"},
                )
            ),
            max_audio_bytes=128,
        )
        with self.assertRaises(VoiceProviderError) as size_error:
            oversized.synthesize(text="Teste.", voice_id="voice_123")
        self.assertEqual(size_error.exception.code, "PROVIDER_RESPONSE_TOO_LARGE")

    def test_chatterbox_mapping_is_cpu_only_and_bounded(self):
        quiet = chatterbox_expression_settings(direction="intense", intensity=0.0)
        strong = chatterbox_expression_settings(direction="intense", intensity=1.0)
        self.assertEqual(
            quiet,
            {"exaggeration": 0.5, "cfgWeight": 0.5, "temperature": 0.8},
        )
        self.assertEqual(
            strong,
            {"exaggeration": 0.92, "cfgWeight": 0.34, "temperature": 0.98},
        )
        with self.assertRaises(VoiceProviderError):
            chatterbox_expression_settings(direction="intense", intensity=1.1)

    def test_chatterbox_editor_contract_returns_all_worker_arguments(self):
        settings = resolve_chatterbox_settings(
            "angry",
            1.0,
            {"cfgWeight": 0.31, "top_p": 0.91},
        )
        self.assertEqual(
            set(settings),
            {
                "exaggeration",
                "cfg_weight",
                "temperature",
                "repetition_penalty",
                "min_p",
                "top_p",
            },
        )
        self.assertEqual(settings["exaggeration"], 0.96)
        self.assertEqual(settings["cfg_weight"], 0.31)
        self.assertEqual(settings["top_p"], 0.91)
        with self.assertRaises(VoiceProviderError) as unknown:
            resolve_chatterbox_settings("cinematic", 0.5, None)
        self.assertEqual(unknown.exception.code, "UNSUPPORTED_PRESET")
        with self.assertRaises(VoiceProviderError) as override:
            resolve_chatterbox_settings("natural", 0.5, {"shell": 1})
        self.assertEqual(override.exception.code, "UNSUPPORTED_VOICE_SETTING")


if __name__ == "__main__":
    unittest.main()
