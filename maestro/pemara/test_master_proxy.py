import os
import unittest
from unittest.mock import patch

import MASTER


class StudioProxyHeadersTest(unittest.TestCase):
    def test_authenticated_studio_proxy_injects_server_side_token(self):
        incoming = {
            "Host": "maestro.pemaratech.com.br",
            "Content-Type": "application/json",
            "Cookie": "maestro_session=browser-secret",
            "X-Studio-Internal-Token": "untrusted-browser-value",
        }
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            headers = MASTER._proxy_headers(
                "/api/studio/api/generative/status",
                incoming,
            )

        self.assertEqual(headers["X-Studio-Internal-Token"], "trusted-test-token")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Host", headers)
        self.assertNotIn("Cookie", headers)

    def test_non_studio_proxy_never_receives_studio_token(self):
        with patch.dict(os.environ, {"STUDIO_INTERNAL_TOKEN": "trusted-test-token"}):
            headers = MASTER._proxy_headers(
                "/api/dashboard/snapshot",
                {"X-Studio-Internal-Token": "untrusted-browser-value"},
            )

        self.assertNotIn("X-Studio-Internal-Token", headers)

    def test_dictation_proxy_has_a_dedicated_small_body_limit(self):
        with patch.dict(os.environ, {
            "MAESTRO_MAX_PROXY_BYTES": str(8 * 1024 * 1024 * 1024),
            "MAESTRO_DICTATION_MAX_BYTES": str(16 * 1024 * 1024),
        }):
            dictation = MASTER._proxy_body_limit(
                "http://127.0.0.1:8029/api/dictation/transcriptions?language=pt"
            )
            generative = MASTER._proxy_body_limit(
                "http://127.0.0.1:8029/api/generative/job"
            )

        self.assertEqual(dictation, 16 * 1024 * 1024)
        self.assertEqual(generative, 8 * 1024 * 1024 * 1024)

    def test_tool_proxy_strips_maestro_cookie_but_keeps_tool_cookie(self):
        headers = MASTER._tool_proxy_headers(
            {
                "Cookie": "maestro_session=owner-secret; theme=dark; tool_session=abc",
                "Authorization": "Bearer tool-token",
                "X-Studio-Internal-Token": "must-not-pass",
            },
            "comfy.pemaratech.com.br",
            True,
        )

        self.assertEqual(headers["Cookie"], "theme=dark; tool_session=abc")
        self.assertEqual(headers["Authorization"], "Bearer tool-token")
        self.assertEqual(headers["X-Forwarded-Host"], "comfy.pemaratech.com.br")
        self.assertEqual(headers["X-Forwarded-Proto"], "https")
        self.assertNotIn("X-Studio-Internal-Token", headers)

    def test_public_tool_routes_are_fixed_and_never_include_raw_apis(self):
        self.assertEqual(MASTER.PUBLIC_TOOL_ROUTES["comfy"]["port"], 8188)
        self.assertEqual(MASTER.PUBLIC_TOOL_ROUTES["sprunki"]["port"], 5005)
        self.assertEqual(MASTER.PUBLIC_TOOL_ROUTES["perplexica"]["port"], 3002)
        self.assertNotIn("ollama", MASTER.PUBLIC_TOOL_ROUTES)
        self.assertNotIn("studio", MASTER.PUBLIC_TOOL_ROUTES)

    def test_health_is_degraded_when_any_managed_service_is_offline(self):
        responses = [
            (True, 4, "online")
            for _ in MASTER.HEALTH_TARGETS
        ]
        responses[-1] = (False, 2000, "timed out")
        with patch.object(MASTER, "_request_json", side_effect=responses):
            health = MASTER.maestro_health()

        self.assertFalse(health["ok"])
        self.assertEqual(health["status"], "degraded")
        self.assertEqual(health["online_count"], len(MASTER.HEALTH_TARGETS) - 1)
        self.assertEqual(health["total_count"], len(MASTER.HEALTH_TARGETS))


if __name__ == "__main__":
    unittest.main()
