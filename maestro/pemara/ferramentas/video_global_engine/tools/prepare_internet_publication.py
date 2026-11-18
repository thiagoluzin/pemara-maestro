"""Preview/apply a publication brief through the Studio API; never run a model.

Default is read-only. --apply persists explicit intent and an optional written
direction plan in the canonical project. The Studio remains the single writer.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from urllib.parse import quote, urlsplit


def api(base: str, path: str, payload: dict | None = None, method: str = "GET") -> dict:
    address = urlsplit(base)
    if address.scheme != "http" or address.hostname != "127.0.0.1" or address.username or address.password or address.path or address.query or address.fragment:
        raise ValueError("Use somente a URL HTTP de loopback do Studio, sem caminho ou credenciais.")
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8") if payload is not None else None
    if data is not None and len(data) > 64 * 1024:
        raise ValueError("Pedido excede 64 KiB.")
    connection = HTTPConnection("127.0.0.1", address.port or 80, timeout=30)
    try:
        # No redirect following, external hosts, file schemes or social credentials.
        connection.request(method, path, body=data, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Resposta do Studio excede o limite local.")
        body = json.loads(raw.decode("utf-8"))
        if not 200 <= response.status < 300:
            raise ValueError(body.get("error", {}).get("message") or body.get("erro") or f"HTTP {response.status}")
        return body
    finally:
        connection.close()


def text_file(path: Path, maximum: int) -> str:
    if path.stat().st_size > maximum:
        raise ValueError(f"Arquivo excede {maximum} bytes: {path.name}")
    return path.read_text(encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="ID exato de um projeto existente no Maestro")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--brief", default="")
    source.add_argument("--brief-file", type=Path)
    parser.add_argument("--mode", choices=("auto", "internet", "standard"), default="auto")
    parser.add_argument("--plan-file", type=Path, help="JSON com os dez campos editoriais, sem aprovações")
    parser.add_argument("--apply", action="store_true", help="Persistir via Studio; nunca gera/publica")
    parser.add_argument("--studio-url", default="http://127.0.0.1:8029")
    args = parser.parse_args()
    try:
        if args.apply and not args.project:
            raise ValueError("--apply exige --project; não cria nem escolhe um projeto por inferência.")
        brief = text_file(args.brief_file, 32000) if args.brief_file else args.brief
        plan = json.loads(text_file(args.plan_file, 60000)) if args.plan_file else None
        if plan is not None and not isinstance(plan, dict):
            raise ValueError("O arquivo de direção deve conter um objeto JSON.")
        base = args.studio_url
        preview = api(base, "/api/video-projects/briefing-preview", {"brief": brief, "distributionMode": args.mode}, "POST")
        output = {"applied": False, "preview": preview, "autoGenerate": False, "autoPublish": False}
        if args.project:
            path = "/api/video-projects/" + quote(args.project, safe="")
            if args.apply:
                update = {"publicationBrief": brief}
                if args.mode != "auto":
                    update["distributionMode"] = args.mode
                api(base, path, update, "PATCH")
                output["applied"] = True
            current = api(base, path + "/internet-publication")
            if args.apply and plan is not None:
                current = api(base, path + "/internet-publication/plan", {
                    "expectedRevision": current["revision"], "plan": plan,
                }, "POST")
            output["publication"] = current
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, HTTPException) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "autoGenerate": False, "autoPublish": False}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
