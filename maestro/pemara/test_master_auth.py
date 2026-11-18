import base64
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import MASTER


class MaestroSessionTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_file_patch = patch.object(
            MASTER,
            "SESSION_FILE",
            Path(self.temp_dir.name) / "auth_sessions.json",
        )
        self.session_file_patch.start()
        MASTER._LOGIN_FAILURES.clear()
        MASTER._TOOL_HANDOFFS.clear()

    def tearDown(self):
        self.session_file_patch.stop()
        self.temp_dir.cleanup()
        MASTER._LOGIN_FAILURES.clear()
        MASTER._TOOL_HANDOFFS.clear()

    def test_session_is_random_persistent_and_revocable(self):
        with patch.dict(os.environ, {"MAESTRO_ADMIN_USER": "owner"}):
            token = MASTER.criar_sessao("owner", now=1000)
            self.assertNotIn("owner", token)
            self.assertTrue(MASTER.sessao_valida(token, now=1001))
            MASTER.revogar_sessao(token, now=1002)
            self.assertFalse(MASTER.sessao_valida(token, now=1003))

    def test_expired_session_is_rejected(self):
        with (
            patch.dict(os.environ, {"MAESTRO_ADMIN_USER": "owner"}),
            patch.object(MASTER, "SESSION_MAX_AGE", 10),
        ):
            token = MASTER.criar_sessao("owner", now=1000)
            self.assertFalse(MASTER.sessao_valida(token, now=1011))

    def test_cookie_parser_requires_the_exact_session_cookie(self):
        self.assertEqual(
            MASTER._cookie_session("theme=dark; maestro_session=session-value"),
            "session-value",
        )
        self.assertEqual(
            MASTER._cookie_session("fake_maestro_session=session-value"),
            "",
        )

    def test_login_csrf_requires_matching_cookie_and_form_token(self):
        token = "csrf-" + ("a" * 40)
        self.assertTrue(
            MASTER._csrf_token_valid(
                f"theme=dark; {MASTER.CSRF_COOKIE_NAME}={token}",
                token,
            )
        )
        self.assertFalse(
            MASTER._csrf_token_valid(
                f"{MASTER.CSRF_COOKIE_NAME}={token}",
                "csrf-" + ("b" * 40),
            )
        )
        self.assertFalse(MASTER._csrf_token_valid("", token))

    def test_login_csrf_accepts_the_matching_token_among_legacy_duplicates(self):
        current = "csrf-" + ("c" * 40)
        stale = "csrf-" + ("s" * 40)
        for header in (
            f"{MASTER.CSRF_COOKIE_NAME}={stale}; {MASTER.CSRF_COOKIE_NAME}={current}",
            f"{MASTER.CSRF_COOKIE_NAME}={current}; {MASTER.CSRF_COOKIE_NAME}={stale}",
        ):
            with self.subTest(header=header):
                self.assertTrue(MASTER._csrf_token_valid(header, current))
                self.assertFalse(
                    MASTER._csrf_token_valid(header, "csrf-" + ("x" * 40))
                )

    def test_signed_login_csrf_survives_missing_or_stale_browser_cookie(self):
        with patch.dict(os.environ, {"MAESTRO_LOGIN_CSRF_SECRET": "test-secret"}):
            token = MASTER._new_login_csrf_token(now=1000, nonce="n" * 24)
            stale = "csrf-" + ("s" * 40)
            self.assertTrue(MASTER._login_csrf_valid("", token, now=1001))
            self.assertTrue(
                MASTER._login_csrf_valid(
                    f"{MASTER.CSRF_COOKIE_NAME}={stale}",
                    token,
                    now=1001,
                )
            )
            self.assertFalse(MASTER._login_csrf_valid("", token + "x", now=1001))
            self.assertFalse(
                MASTER._login_csrf_valid(
                    "",
                    token,
                    now=1000 + MASTER.LOGIN_CSRF_MAX_AGE + 1,
                )
            )

    def test_login_post_origin_guard_rejects_cross_site_browser(self):
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "https://evil.example",
                "cross-site",
            )
        )
        self.assertTrue(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "https://maestro.pemaratech.com.br",
                "same-origin",
            )
        )

    def test_login_post_origin_guard_normalizes_only_default_web_ports(self):
        self.assertTrue(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "https://maestro.pemaratech.com.br:443",
                "same-origin",
            )
        )
        self.assertTrue(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br:443",
                "https://maestro.pemaratech.com.br",
                "same-origin",
            )
        )
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "https://maestro.pemaratech.com.br:8443",
                "same-origin",
            )
        )
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "https://evil.example:443",
                "same-origin",
            )
        )

    def test_state_changing_requests_reject_foreign_origins(self):
        self.assertTrue(
            MASTER._unsafe_request_origin_allowed(
                "sprunki.pemaratech.com.br",
                "https://sprunki.pemaratech.com.br",
                "same-origin",
            )
        )
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "sprunki.pemaratech.com.br",
                "https://maestro.pemaratech.com.br",
                "same-site",
            )
        )
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "sprunki.pemaratech.com.br",
                "",
                "cross-site",
            )
        )
        self.assertTrue(
            MASTER._unsafe_request_origin_allowed(
                "127.0.0.1:9501",
                "",
                "",
            )
        )

    def test_opaque_origin_requires_browser_proven_same_origin_context(self):
        self.assertTrue(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "null",
                "same-origin",
            )
        )
        for fetch_site in ("", "none", "same-site", "cross-site"):
            with self.subTest(fetch_site=fetch_site):
                self.assertFalse(
                    MASTER._unsafe_request_origin_allowed(
                        "maestro.pemaratech.com.br",
                        "null",
                        fetch_site,
                    )
                )

    def test_opaque_origin_does_not_relax_foreign_origin_checks(self):
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "https://evil.example",
                "same-origin",
            )
        )
        self.assertFalse(
            MASTER._unsafe_request_origin_allowed(
                "maestro.pemaratech.com.br",
                "NULL",
                "same-origin",
            )
        )

    def test_login_failures_are_rate_limited_and_expire(self):
        for timestamp in range(10, 15):
            MASTER._record_login_failure("client", now=timestamp)
        self.assertGreater(MASTER._login_retry_after("client", now=15), 0)
        self.assertEqual(MASTER._login_retry_after("client", now=400), 0)

    def test_frontend_token_has_no_hardcoded_fallback(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(MASTER, "_ler_env_local", return_value=""),
        ):
            self.assertEqual(MASTER.token_frontend(), "")

    def test_public_http_requests_receive_a_safe_https_target(self):
        self.assertEqual(
            MASTER._https_redirect_target(
                "maestro.pemaratech.com.br",
                "http",
                "/login?next=%2F",
            ),
            "https://maestro.pemaratech.com.br/login?next=%2F",
        )
        self.assertEqual(
            MASTER._https_redirect_target(
                "maestro.pemaratech.com.br",
                "https",
                "/login",
            ),
            "",
        )
        self.assertEqual(
            MASTER._https_redirect_target("evil.example", "http", "/login"),
            "",
        )
        self.assertEqual(
            MASTER._https_redirect_target(
                "maestro.pemaratech.com.br",
                "http",
                "/login\r\nX-Evil: yes",
            ),
            "https://maestro.pemaratech.com.br/",
        )

    def test_private_gateway_allowlist_accepts_only_hostnames(self):
        parsed = MASTER._parse_gateway_hosts(
            " PC-GERAL-THIAGO-1.tail14cf8c.ts.net., private.example, "
            "https://evil.example, bad.example:8443, -invalid.example"
        )
        self.assertEqual(
            parsed,
            {
                "pc-geral-thiago-1.tail14cf8c.ts.net",
                "private.example",
            },
        )
        self.assertTrue(MASTER.PRIVATE_GATEWAY_HOSTS.issubset(MASTER.ALLOWED_GATEWAY_HOSTS))
        self.assertTrue(MASTER.PRIVATE_GATEWAY_HOSTS.isdisjoint(MASTER.PUBLIC_GATEWAY_HOSTS))

    def test_scrypt_password_hash_takes_precedence_over_plaintext(self):
        salt = b"0123456789abcdef"
        digest = hashlib.scrypt(
            b"correct-password",
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
        encoded = "$".join((
            "scrypt", str(2**14), "8", "1",
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ))
        with patch.dict(os.environ, {
            "MAESTRO_ADMIN_USER": "owner",
            "MAESTRO_ADMIN_PASSWORD": "wrong-plaintext-fallback",
            "MAESTRO_ADMIN_PASSWORD_HASH": encoded,
        }):
            self.assertTrue(MASTER.login_valido("owner", "correct-password"))
            self.assertFalse(MASTER.login_valido("owner", "wrong-plaintext-fallback"))
            self.assertFalse(MASTER.login_valido("other", "correct-password"))

    def test_malformed_or_unsafe_scrypt_hash_is_rejected(self):
        self.assertFalse(MASTER._senha_scrypt_valida("password", "scrypt$2$8$1$bad$bad"))
        self.assertFalse(MASTER._senha_scrypt_valida("password", "argon2$32768$8$1$bad$bad"))

    def test_tool_handoff_is_host_bound_short_lived_and_one_time(self):
        code, config = MASTER.criar_handoff_ferramenta("comfy", now=1000)
        self.assertEqual(config["host"], "comfy.pemaratech.com.br")
        self.assertIsNone(
            MASTER.consumir_handoff_ferramenta(
                code,
                "sprunki.pemaratech.com.br",
                now=1001,
            )
        )
        consumed = MASTER.consumir_handoff_ferramenta(
            code,
            "comfy.pemaratech.com.br",
            now=1001,
        )
        self.assertEqual(consumed["tool"], "comfy")
        self.assertIsNone(
            MASTER.consumir_handoff_ferramenta(
                code,
                "comfy.pemaratech.com.br",
                now=1002,
            )
        )

    def test_tool_handoff_expires_and_unknown_tools_are_rejected(self):
        code, _ = MASTER.criar_handoff_ferramenta("perplexica", now=1000)
        self.assertIsNone(
            MASTER.consumir_handoff_ferramenta(
                code,
                "perplexica.pemaratech.com.br",
                now=1000 + MASTER.TOOL_HANDOFF_MAX_AGE + 1,
            )
        )
        self.assertIsNone(MASTER.criar_handoff_ferramenta("ollama", now=1000))


if __name__ == "__main__":
    unittest.main()
