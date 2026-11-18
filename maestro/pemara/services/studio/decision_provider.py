"""Bounded Gemini Decision client. No fallback, retries or secret logging."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DECISION_MODEL = "gemini-decision-1"
DECISION_URL = "https://generativelanguage.googleapis.com/v1beta/decisions"
SECRET_ROOT = Path.home() / ".codex" / "secrets"


class ProviderError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A credential must never follow an endpoint redirect to another host.
        raise ProviderError("PROVIDER_REDIRECT_REFUSED")


def private_setting(name: str, filename: str) -> str:
    """Read only named settings; never export private contents to logs or projects."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value = str(winreg.QueryValueEx(key, name)[0]).strip()
                if value:
                    return value
        except OSError:
            pass
    path = SECRET_ROOT / filename
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and key.strip() == name:
                return value.strip().strip("\"'")
    return ""


def post_json(url: str, body: dict, headers: dict, *, timeout: int = 60) -> dict:
    data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
    if len(data) > 18_000_000:
        raise ProviderError("REQUEST_TOO_LARGE")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.build_opener(NoRedirects).open(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ProviderError("RESPONSE_TOO_LARGE")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ProviderError("INVALID_PROVIDER_RESPONSE")
        return result
    except urllib.error.HTTPError as exc:
        # Remote bodies can include request content; never persist them.
        raise ProviderError(f"PROVIDER_HTTP_{exc.code}") from None
    except (OSError, ValueError):
        raise ProviderError("PROVIDER_CONNECTION_OR_RESPONSE_FAILURE") from None


class DecisionClient:
    def __init__(self, transport=post_json):
        self.transport = transport

    def ready(self) -> bool:
        return bool(private_setting("GEMINI_API_KEY", "gemini.env") or private_setting("GOOGLE_API_KEY", "gemini.env"))

    def evaluate(self, content: list[dict] | str, questions: dict) -> dict:
        key = private_setting("GEMINI_API_KEY", "gemini.env") or private_setting("GOOGLE_API_KEY", "gemini.env")
        if not key:
            raise ProviderError("GEMINI_API_KEY_MISSING")
        if not 1 <= len(questions) <= 1000:
            raise ProviderError("INVALID_QUESTION_COUNT")
        return self.transport(DECISION_URL, {"model": DECISION_MODEL, "input": content, "questions": questions}, {"x-goog-api-key": key})


