import asyncio
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from main import (
    _EDITOR_SUITE,
    _browser_origin_allowed,
    _dictation_media_suffix,
    _is_internal_request,
    create_dictation_transcription,
    generative_h3_workflow,
    video_take_h3_workflow,
)


class FakeRequest:
    def __init__(self, *, token="trusted-test-token", content_type="audio/webm", body=b"audio"):
        self.headers = CaseInsensitiveHeaders({
            "X-Studio-Internal-Token": token,
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        })
        self.client = SimpleNamespace(host="198.51.100.10")
        self.body = body
        self.stream_started = False

    async def stream(self):
        self.stream_started = True
        yield self.body


class CaseInsensitiveHeaders(dict):
    def get(self, key, default=None):
        wanted = str(key).lower()
        for candidate, value in self.items():
            if str(candidate).lower() == wanted:
                return value
        return default


class StudioInternalAuthTest(unittest.TestCase):
    def request(self, token):
        return SimpleNamespace(
            headers={
                "X-Studio-Internal-Token": token,
                "X-Forwarded-Host": "api-studio.pemaratech.com.br",
            },
            client=SimpleNamespace(host="198.51.100.10"),
        )

    def test_authenticated_maestro_proxy_is_internal(self):
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            self.assertTrue(_is_internal_request(self.request("trusted-test-token")))

    def test_wrong_proxy_token_remains_public(self):
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            self.assertFalse(_is_internal_request(self.request("wrong-token")))

    def test_unknown_forwarded_host_cannot_inherit_loopback_trust(self):
        request = SimpleNamespace(
            headers=CaseInsensitiveHeaders({
                "Host": "127.0.0.1:8029",
                "X-Forwarded-Host": "new-public-host.example",
            }),
            client=SimpleNamespace(host="127.0.0.1"),
        )
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            self.assertFalse(_is_internal_request(request))

    def test_untrusted_host_header_cannot_inherit_loopback_trust(self):
        request = SimpleNamespace(
            headers=CaseInsensitiveHeaders({"Host": "attacker.example"}),
            client=SimpleNamespace(host="127.0.0.1"),
        )
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            self.assertFalse(_is_internal_request(request))

    def test_browser_origin_gate_accepts_only_maestro_and_local_panel(self):
        for origin in (
            "https://maestro.pemaratech.com.br",
            "https://MAESTRO.PEMARATECH.COM.BR:443",
            "http://127.0.0.1:9501",
            "http://localhost:9501",
        ):
            with self.subTest(origin=origin):
                request = SimpleNamespace(
                    headers=CaseInsensitiveHeaders({"Origin": origin})
                )
                self.assertTrue(_browser_origin_allowed(request))

    def test_browser_origin_gate_rejects_foreign_opaque_and_cross_site(self):
        for headers in (
            {"Origin": "https://evil.example"},
            {"Origin": "null"},
            {"Origin": "https://maestro.pemaratech.com.br.evil.example"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(headers=headers):
                request = SimpleNamespace(headers=CaseInsensitiveHeaders(headers))
                self.assertFalse(_browser_origin_allowed(request))

    def test_non_browser_local_client_remains_allowed_by_origin_gate(self):
        request = SimpleNamespace(headers=CaseInsensitiveHeaders({}))
        self.assertTrue(_browser_origin_allowed(request))

    def test_dictation_accepts_only_allowlisted_audio_types(self):
        self.assertEqual(_dictation_media_suffix("audio/webm;codecs=opus"), ".webm")
        self.assertEqual(_dictation_media_suffix("audio/mp4"), ".m4a")
        self.assertEqual(_dictation_media_suffix("application/octet-stream"), "")

    def test_dictation_authenticates_before_reading_audio(self):
        request = FakeRequest(token="wrong-token")
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            response = asyncio.run(create_dictation_transcription(request))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(request.stream_started)

    def test_dictation_returns_only_text_metadata_and_privacy_contract(self):
        request = FakeRequest()

        def fake_transcription(source: Path, **kwargs):
            self.assertEqual(source.read_bytes(), b"audio")
            self.assertEqual(kwargs["language"], "pt")
            return {
                "text": "Uma câmera se afasta lentamente.",
                "language": "pt",
                "durationSeconds": 1.0,
                "segmentCount": 1,
                "engine": "faster-whisper",
                "model": "base",
                "device": "cpu",
                "computeType": "int8",
            }

        with (
            patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}),
            patch.object(_EDITOR_SUITE, "transcribe_short_audio", side_effect=fake_transcription),
        ):
            response = asyncio.run(create_dictation_transcription(request, language="pt"))

        self.assertTrue(response["ok"])
        self.assertEqual(response["transcription"]["text"], "Uma câmera se afasta lentamente.")
        self.assertEqual(response["privacy"], {"stored": False, "cloud": False})

    def test_h3_workflow_inventory_is_closed_before_local_path_disclosure(self):
        request = self.request("wrong-token")
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            response = asyncio.run(generative_h3_workflow(request))
        self.assertEqual(response.status_code, 403)

    def test_h3_take_preflight_authenticates_before_project_lookup(self):
        request = self.request("wrong-token")
        with (
            patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}),
            patch("main._get_take_generation_spec") as generation_spec,
        ):
            response = asyncio.run(video_take_h3_workflow(request, "private-project", "T01"))
        self.assertEqual(response.status_code, 403)
        generation_spec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
