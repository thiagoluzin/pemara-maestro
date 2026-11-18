#!/usr/bin/env python3
"""Read-only HubMesh intake for the Pemara ecosystem.

The script discovers public repository links mentioned in recent HubMesh
episodes. It never clones, installs, executes, or approves a repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


SOURCE_URL = "https://hubmesh.dev/"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
USER_AGENT = "Pemara-Ecosystem-Radar/1.0 (+read-only)"
POST_PATTERN = re.compile(r"^/posts/\d{4}-\d{2}-\d{2}-[A-Za-z0-9_-]+/?$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.title = ""
        self._in_h1 = False
        self._h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "h1" and not self.title:
            self._in_h1 = True
            self._h1_parts = []
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h1" and self._in_h1:
            self.title = " ".join(" ".join(self._h1_parts).split())
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._h1_parts.append(data)


def _fetch(url: str, timeout: float) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "hubmesh.dev":
        raise ValueError("Somente paginas HTTPS de hubmesh.dev sao permitidas.")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type != "text/html":
                raise RuntimeError(f"Conteudo inesperado em {url}: {content_type}")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Falha ao consultar HubMesh: {exc}") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Resposta do HubMesh excedeu o limite seguro.")
    return body.decode("utf-8", errors="replace")


def _parse(html: str) -> LinkParser:
    parser = LinkParser()
    parser.feed(html)
    parser.close()
    return parser


def discover_episode_urls(index_html: str, limit: int) -> list[str]:
    parser = _parse(index_html)
    seen: set[str] = set()
    episodes: list[str] = []
    for href in parser.links:
        parsed = urllib.parse.urlparse(href)
        path = parsed.path
        if not POST_PATTERN.fullmatch(path) or path in seen:
            continue
        seen.add(path)
        episodes.append(urllib.parse.urljoin(SOURCE_URL, path))
        if len(episodes) >= limit:
            break
    return episodes


def _github_repository(url: str) -> tuple[str, str] | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "github.com",
        "www.github.com",
    }:
        return None
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    slug = f"{parts[0]}/{parts[1].removesuffix('.git')}"
    if not REPO_PATTERN.fullmatch(slug):
        return None
    if slug.lower() == "flaviomartil/hubmesh-dev":
        return None
    return slug, f"https://github.com/{slug}"


def repositories_from_episode(html: str) -> tuple[str, list[dict[str, str]]]:
    parser = _parse(html)
    unique: dict[str, dict[str, str]] = {}
    for href in parser.links:
        repository = _github_repository(href)
        if not repository:
            continue
        slug, canonical_url = repository
        unique.setdefault(
            slug.lower(),
            {"repository": slug, "url": canonical_url},
        )
    return parser.title, list(unique.values())


def build_report(
    *,
    limit: int = 5,
    timeout: float = 15.0,
    keyword: str = "",
) -> dict[str, object]:
    limit = max(1, min(int(limit), 25))
    index_html = _fetch(SOURCE_URL, timeout)
    episodes = []
    repositories: dict[str, dict[str, str]] = {}
    needle = keyword.strip().lower()
    for episode_url in discover_episode_urls(index_html, limit):
        html = _fetch(episode_url, timeout)
        title, items = repositories_from_episode(html)
        episode_items = []
        for item in items:
            searchable = f"{item['repository']} {title}".lower()
            if needle and needle not in searchable:
                continue
            record = {
                **item,
                "episodeTitle": title,
                "episodeUrl": episode_url,
                "decision": "review_required",
            }
            episode_items.append(record)
            repositories.setdefault(item["repository"].lower(), record)
        episodes.append(
            {
                "title": title,
                "url": episode_url,
                "repositoryCount": len(episode_items),
            }
        )
    return {
        "schemaVersion": 1,
        "source": SOURCE_URL,
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy": {
            "mode": "read_only_signal",
            "autoInstall": False,
            "requiredChecks": [
                "license",
                "maintainer_and_release_activity",
                "dependency_and_secret_scan",
                "capability_overlap",
                "sandbox_smoke_test",
                "human_approval",
            ],
        },
        "episodes": episodes,
        "repositories": list(repositories.values()),
    }


def _write_json(report: dict[str, object], output: str) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if not output:
        sys.stdout.write(rendered)
        return
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lista sinais publicos do HubMesh sem instalar repositorios."
    )
    parser.add_argument("--limit", type=int, default=5, help="Episodios (1-25).")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--keyword", default="")
    parser.add_argument("--output", default="", help="JSON de saida; vazio imprime.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = build_report(
            limit=args.limit,
            timeout=max(1.0, min(args.timeout, 60.0)),
            keyword=args.keyword,
        )
        _write_json(report, args.output)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"hubmesh_radar: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
