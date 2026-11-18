"""Explicit internet-production intent, editorial planning and local evidence.

This module never posts, schedules, starts a model, grants approval or changes
source videos. Audience measurements are supplied explicitly, not inferred from
the operator's review player.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import tempfile
import threading
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit


PROFILE = "social_v1"
BODY_LIMIT = 64 * 1024
STATE_LIMIT = 4 * 1024 * 1024
PLATFORMS = {"youtube", "youtube_shorts", "instagram_reels", "threads", "tiktok", "facebook"}
PLAN_FIELDS = {
    "audience": "Público", "promise": "Promessa do vídeo",
    "emotion": "Emoção pretendida", "opening": "Abertura recomendada",
    "alternativeOpening": "Abertura alternativa", "progression": "Progressão e consequências",
    "payoff": "Recompensa final", "mobileFraming": "Enquadramento para o destino",
    "silentComprehension": "Compreensão sem som", "constraints": "Instruções que devem ser preservadas",
}
REQUIRED_PLAN_FIELDS = tuple(key for key in PLAN_FIELDS if key != "constraints")
CHECKLIST = [
    "O começo apresenta um conflito, uma emoção ou uma pergunta legível?",
    "O contexto é compreensível para quem ainda não conhece este projeto?",
    "Cada beat acrescenta informação, reação e consequência?",
    "A recompensa cumpre a promessa da abertura?",
    "A cena funciona na tela do celular e continua legível sem som?",
    "As instruções de duração, silêncio, estilo e continuidade foram preservadas?",
    "O MP4 real foi revisto; o contrato escrito não substitui essa revisão?",
]
_LOCK = threading.RLock()
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_UUID = re.compile(r"^[a-f0-9]{32}$")


class PublicationConflictError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: Any, field: str, maximum: int = 2400) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} deve ser texto.")
    if len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field} excede o limite de {maximum} caracteres ou contém NUL.")
    return value.strip()


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def _unquoted(value: str) -> str:
    # Fenced code, block quotes, markup and inline quotations are evidence, not
    # the user's current instruction. Keep apostrophes inside ordinary words.
    value = re.sub(r"```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)", " ", value)
    value = re.sub(r"(?m)^\s*>.*$", " ", value)
    value = re.sub(r"<[^>]*>|`[^`]*`|\"[^\"]*\"|“[^”]*”|‘[^’]*’|«[^»]*»", " ", value)
    value = re.sub(r"(?<!\w)'[^'\n]*'(?!\w)", " ", value)
    return value


def detect_intent(brief: str, *, mode: str = "auto", platforms: list[str] | None = None) -> dict[str, Any]:
    brief = _text(brief, "brief", 8000)
    if not isinstance(mode, str) or mode not in {"auto", "internet", "standard"}:
        raise ValueError("distributionMode deve ser auto, internet ou standard.")
    if platforms is not None and (
        not isinstance(platforms, list) or len(platforms) > len(PLATFORMS)
        or any(not isinstance(item, str) or item not in PLATFORMS for item in platforms)
    ):
        raise ValueError("Plataformas inválidas.")
    requested = list(dict.fromkeys(platforms or []))
    clauses = re.split(r"[.!?;,\n]+|\bmas\b|\bpor[eé]m\b", _unquoted(brief), flags=re.IGNORECASE)
    destination = r"(?:internet|redes?(?:\s+sociais)?|instagram|reels?|threads|tiktok|tik\s*tok|youtube|shorts?|facebook)"
    trigger = re.compile(
        rf"\b(?:(?:public\w*|post\w*|divulg\w*|compartilh\w*|distribu\w*)\b.{{0,85}}\b{destination}\b"
        rf"|(?:para|pro|pra)\s+(?:(?:o|a|os|as)\s+)?{destination}\b"
        rf"|(?:video|filme|clipe)\s+(?:sera\s+|vai\s+ser\s+|e\s+)?(?:no|na|nos|nas)\s+{destination}\b"
        rf"|nao\s+(?:no|na|nos|nas)\s+{destination}\b"
        rf"|(?:reels|shorts|tiktok)\s*(?:do|de|sobre|com|:)"
        rf"|(?:crie|criar|faca|fazer|produza|produzir)\b.{{0,45}}\b(?:reel|reels|short|shorts)\b)"
    )
    decision: bool | None = None
    evidence = ""
    generic_enabled = False
    detected: list[str] = []
    platform_patterns = (
        ("youtube_shorts", r"\bshorts?\b"),
        ("instagram_reels", r"\b(?:instagram|reels?)\b"),
        ("threads", r"\bthreads\b"), ("tiktok", r"\btik\s*tok\b"),
        ("facebook", r"\bfacebook\b"), ("youtube", r"\byoutube\b"),
    )
    for clause in clauses:
        normalized = _normalized(clause)
        match = trigger.search(normalized)
        if not match:
            continue
        prefix = normalized[max(0, match.start() - 100):match.end()]
        negation_text = re.sub(r"\bnao\s+(?:so|apenas|somente|(?:se\s+)?esqueca\s+de|deixe\s+de)\b", " ", prefix)
        negative = bool(re.search(r"\b(?:nao|nunca|jamais|evitar|proibido)\b", negation_text)) or bool(
            re.search(r"\bsem\s+(?:public|post|divulg|compartilh|distribu)\w*", prefix)
        )
        # Descriptions of references/third-party examples do not opt a project in.
        reported = bool(re.search(r"\b(?:exemplo|citacao|frase|referencia|documento|print|disse|falou|leia|copie|disser|suponha)\b", normalized[:match.start()]))
        reported = reported or bool(re.match(r"\s*(?:como|por que|sera que)\b", normalized))
        if reported:
            continue
        clause_platforms = [key for key, pattern in platform_patterns if re.search(pattern, normalized)]
        if "youtube_shorts" in clause_platforms and "youtube" in clause_platforms:
            clause_platforms.remove("youtube")
        generic_destination = bool(re.search(r"\b(?:internet|redes?)\b", match.group()))
        if negative:
            if generic_destination:
                generic_enabled = False
                detected.clear()
            else:
                detected = [item for item in detected if item not in clause_platforms]
        else:
            generic_enabled = generic_enabled or generic_destination
            detected = list(dict.fromkeys(detected + clause_platforms))
        decision = generic_enabled or bool(detected)
        evidence = clause.strip()
    enabled = mode == "internet" or (mode == "auto" and decision is True)
    if mode == "standard":
        enabled = False
    if not enabled:
        detected = []
    return {
        "mode": "internet" if enabled else "standard",
        "source_text": evidence if mode == "auto" else brief,
        "selection": mode,
        "platforms": requested or detected,
        "objective": "qualified_reach" if enabled else "original_brief",
        "editorial_profile": PROFILE if enabled else None,
        "default_action": "prepare_only",
        "reason": "explicit_selection" if mode != "auto" else (
            "affirmative_brief" if enabled else "negative_brief" if decision is False else "no_explicit_intent"
        ),
    }


def intent_view(intent: Any) -> dict[str, Any]:
    intent = intent if isinstance(intent, dict) else {}
    platforms = intent.get("platforms") if isinstance(intent.get("platforms"), list) else []
    return {
        "mode": "internet" if intent.get("mode") == "internet" else "standard",
        "sourceText": str(intent.get("source_text") or ""),
        "selection": str(intent.get("selection") or "auto"),
        "platforms": [p for p in platforms if isinstance(p, str) and p in PLATFORMS],
        "editorialProfile": intent.get("editorial_profile"),
        "defaultAction": "prepare_only",
    }


def initial_state(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1, "revision": 0, "updatedAt": None,
        "directionSourceFingerprint": None,
        "plan": {field: "" for field in PLAN_FIELDS},
        "packages": [], "measurements": [], "planHistory": [],
    }


def editorial_readiness(plan: dict[str, Any]) -> dict[str, Any]:
    missing = [PLAN_FIELDS[field] for field in REQUIRED_PLAN_FIELDS if len(str(plan.get(field) or "").strip()) < 8]
    return {
        "status": "DIRECTION_READY" if not missing else "NEEDS_DIRECTION",
        "readyForExistingGates": not missing,
        "missingFields": missing,
        "humanApproved": False,
        "note": "Completude do contrato; não é aprovação artística, previsão de alcance ou autorização de GPU.",
    }


def _direction_fingerprint(manifest: dict[str, Any]) -> str:
    source = {key: manifest.get(key) for key in (
        "title", "objective", "duration_target_seconds", "final_resolution",
    )}
    return hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _plan_readiness(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    result = editorial_readiness(state["plan"])
    result["briefChanged"] = bool(any(state["plan"].values())) and (
        state.get("directionSourceFingerprint") != _direction_fingerprint(manifest)
    )
    if result["briefChanged"]:
        result["status"] = "NEEDS_DIRECTION_REVIEW"
        result["readyForExistingGates"] = False
        result["missingFields"].append("Revisar e salvar a direção após a mudança de briefing ou formato")
    return result


def planning_brief(manifest: dict[str, Any], state: dict[str, Any]) -> str:
    plan = state["plan"]
    lines = [
        "MODO PUBLICAÇÃO NA INTERNET — DIREÇÃO ANTES DA GERAÇÃO",
        f"Projeto: {manifest.get('title') or manifest.get('project_id') or ''}",
        f"Pedido original: {manifest.get('objective') or manifest.get('idea') or ''}",
        f"Duração contratada: {manifest.get('duration_target_seconds', '')} s; preservar instruções explícitas.",
        "Definir promessa, contexto e duas aberturas por escrito antes das âncoras. Recomendar uma sem gerar dois filmes.",
        "Cada beat acrescenta informação, reação e consequência. A progressão pode ocorrer dentro de um plano contínuo.",
        "Preservar pedidos de silêncio, contemplação, estilo, duração e formato. Internet não impõe 9:16 nem duração curta.",
        "Não usar explosões, volume alto, cortes constantes ou palavras como viral como substituto de direção.",
        "A recompensa cumpre a promessa. Não inventar pesos do algoritmo nem prometer visualizações.",
    ]
    lines.extend(f"{label}: {plan.get(field) or '[preencher com direção concreta]'}" for field, label in PLAN_FIELDS.items())
    lines.extend(["", "REVISAR NO ROTEIRO E NO MP4 REAL", *[f"- {item}" for item in CHECKLIST]])
    return "\n".join(lines)


def _project(root: Path, project_id: str) -> Path:
    if not isinstance(project_id, str) or not _ID.fullmatch(project_id):
        raise ValueError("projectId inválido.")
    resolved_root = root.resolve()
    directory = (resolved_root / project_id).resolve()
    if directory.parent != resolved_root:
        raise ValueError("Projeto fora da raiz permitida.")
    if not directory.is_dir():
        raise FileNotFoundError(project_id)
    return directory


def _local(directory: Path, relative: str) -> Path:
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError("Arquivo fora do projeto.")
    return path


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    if path.stat().st_size > STATE_LIMIT:
        raise ValueError("Arquivo de planejamento excede o limite.")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Documento de planejamento inválido.")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if len(data) > STATE_LIMIT:
        raise ValueError("Limite do histórico atingido; preserve e arquive os resultados antes de continuar.")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".internet-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _load(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _read(_local(directory, "project_manifest.json"))
    state = _read(_local(directory, "edit/internet_publication.json")) or initial_state(manifest)
    return manifest, state


def _enabled(manifest: dict[str, Any]) -> None:
    if (manifest.get("distribution_intent") or {}).get("mode") != "internet":
        raise ValueError("Este projeto não está no modo Publicação na internet.")


def _revision(state: dict[str, Any], expected: Any) -> None:
    if isinstance(expected, bool) or not isinstance(expected, int) or expected != state["revision"]:
        raise PublicationConflictError("O planejamento mudou. Atualize antes de salvar.")


def _save(directory: Path, state: dict[str, Any]) -> None:
    state["revision"] += 1
    state["updatedAt"] = now()
    _write(_local(directory, "edit/internet_publication.json"), state)


def get_publication(root: Path, project_id: str) -> dict[str, Any]:
    directory = _project(root, project_id)
    with _LOCK:
        manifest, state = _load(directory)
        result = copy.deepcopy(state)
    result.update({
        "projectId": project_id,
        "intent": intent_view(manifest.get("distribution_intent")),
        "readiness": _plan_readiness(manifest, state),
        "checklist": CHECKLIST,
        "directorBrief": planning_brief(manifest, state),
        "measurementSummary": measurement_summary(state["measurements"]),
        "safety": {"autoPublish": False, "autoGenerate": False, "sourceMutation": False},
    })
    return result


def save_plan(root: Path, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) - {"expectedRevision", "plan"}:
        raise ValueError("Campos não permitidos no planejamento.")
    fields = payload.get("plan")
    if not isinstance(fields, dict) or set(fields) - set(PLAN_FIELDS):
        raise ValueError("Plano deve conter somente os campos editoriais permitidos.")
    normalized = {key: _text(value, key) for key, value in fields.items()}
    directory = _project(root, project_id)
    with _LOCK:
        manifest, state = _load(directory)
        _enabled(manifest)
        _revision(state, payload.get("expectedRevision"))
        previous = copy.deepcopy(state["plan"])
        state["plan"].update(normalized)
        fingerprint = _direction_fingerprint(manifest)
        if state["plan"] != previous or state.get("directionSourceFingerprint") != fingerprint:
            if len(state["planHistory"]) >= 100:
                raise ValueError("Limite de revisões atingido; preserve o histórico antes de continuar.")
            state["planHistory"].append({"revision": state["revision"], "plan": previous, "replacedAt": now(),
                                        "directionSourceFingerprint": state.get("directionSourceFingerprint")})
            state["directionSourceFingerprint"] = fingerprint
            _save(directory, state)
    return get_publication(root, project_id)


def generation_direction(directory: Path, take_id: str, ordered_ids: list[str]) -> str:
    manifest, state = _load(directory)
    if (manifest.get("distribution_intent") or {}).get("mode") != "internet":
        return ""
    readiness = _plan_readiness(manifest, state)
    if not readiness["readyForExistingGates"]:
        raise ValueError("INTERNET_DIRECTION_REQUIRED: " + ", ".join(readiness["missingFields"]))
    plan = state["plan"]
    parts = [
        "Internet editorial direction; preserve approved anchor geometry, identity, chronology and all explicit scene instructions.",
        f"Progression: {plan['progression']}",
        f"Framing: {plan['mobileFraming']}",
        f"Visual comprehension: {plan['silentComprehension']}",
    ]
    if ordered_ids and take_id == ordered_ids[0]:
        parts.append(f"Opening for this first take: {plan['opening']}")
    if ordered_ids and take_id == ordered_ids[-1]:
        parts.append(f"Payoff for this last take: {plan['payoff']}")
    if plan.get("constraints"):
        parts.append(f"Explicit constraints: {plan['constraints']}")
    return "\n".join(parts)


def require_direction(root: Path, project_id: str) -> None:
    """Shared preflight for anchor execution as well as video generation."""
    generation_direction(_project(root, project_id), "", [])


COUNT_METRICS = {
    "views", "engagedViews", "reach", "nonFollowerReach", "shownInFeed", "choseToWatch",
    "eligibleStarts", "viewersAt3Seconds", "completions", "shares", "saves", "comments", "newFollowers",
}
DECIMAL_METRICS = {"averageWatchSeconds", "averageWatchPercent"}


def _number(value: Any, field: str, maximum: float = 1_000_000_000_000, *, integer: bool = False) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{field} deve ser um número finito.")
    if value < 0 or value > maximum or (integer and value != int(value)):
        raise ValueError(f"{field} fora da faixa permitida.")
    if not math.isfinite(value):
        raise ValueError(f"{field} deve ser um número finito.")
    return int(value) if integer else float(value)


def _post_url(value: Any, platform: str) -> str:
    url = _text(value, "postUrl", 2000)
    parsed = urlsplit(url)
    domains = {
        "youtube": ("youtube.com", "youtu.be"), "youtube_shorts": ("youtube.com", "youtu.be"),
        "instagram_reels": ("instagram.com",), "threads": ("threads.com", "threads.net"),
        "tiktok": ("tiktok.com",), "facebook": ("facebook.com", "fb.watch"),
    }[platform]
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Informe o link HTTPS público da publicação, sem credenciais.")
    if not any(host == domain or host.endswith("." + domain) for domain in domains):
        raise ValueError("O link não pertence à plataforma informada.")
    if not parsed.path or parsed.path == "/":
        raise ValueError("Informe o link da publicação, não apenas o site.")
    return url


def metric_rates(metrics: dict[str, Any]) -> dict[str, Any]:
    rates: dict[str, Any] = {}
    for label, numerator, denominator in (
        ("choseToWatchPercent", "choseToWatch", "shownInFeed"),
        ("retainedAt3SecondsPercent", "viewersAt3Seconds", "eligibleStarts"),
        ("completionPercent", "completions", "eligibleStarts"),
        ("sharesPerReachPercent", "shares", "reach"),
        ("followersPerReachPercent", "newFollowers", "reach"),
    ):
        top, bottom = metrics.get(numerator), metrics.get(denominator)
        if top is not None and bottom is not None and bottom > 0:
            rates[label] = {"value": round(100 * top / bottom, 2), "numerator": numerator, "denominator": denominator}
    return rates


def record_measurement(root: Path, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"expectedRevision", "packageId", "platform", "postUrl", "windowHours", "metrics", "notes"}
    if set(payload) - allowed:
        raise ValueError("Campos não permitidos no resultado.")
    platform = payload.get("platform")
    if not isinstance(platform, str) or platform not in PLATFORMS:
        raise ValueError("Plataforma inválida.")
    post_url = _post_url(payload.get("postUrl"), platform)
    window = _number(payload.get("windowHours"), "windowHours", 8760)
    raw = payload.get("metrics")
    if not isinstance(raw, dict) or not raw or set(raw) - COUNT_METRICS - DECIMAL_METRICS:
        raise ValueError("Informe somente métricas agregadas suportadas.")
    metrics = {
        key: None if value is None else _number(
            value, key, 72000 if key == "averageWatchSeconds" else 1000 if key == "averageWatchPercent" else 1e12,
            integer=key in COUNT_METRICS,
        ) for key, value in raw.items()
    }
    if not any(value is not None for value in metrics.values()):
        raise ValueError("Informe pelo menos uma métrica observada.")
    for small, large in (("nonFollowerReach", "reach"), ("choseToWatch", "shownInFeed"),
                         ("viewersAt3Seconds", "eligibleStarts"), ("completions", "eligibleStarts")):
        if metrics.get(small) is not None and metrics.get(large) is not None and metrics[small] > metrics[large]:
            raise ValueError(f"{small} não pode exceder {large}.")
    directory = _project(root, project_id)
    with _LOCK:
        manifest, state = _load(directory)
        _enabled(manifest)
        _revision(state, payload.get("expectedRevision"))
        package = next((item for item in state["packages"] if item["id"] == payload.get("packageId")), None)
        if package is None or package.get("status") == "FAILED":
            raise ValueError("Selecione um pacote preparado deste projeto.")
        if package.get("platform") != platform:
            raise ValueError("A plataforma deve corresponder ao pacote escolhido.")
        if len(state["measurements"]) >= 1000:
            raise ValueError("Limite de resultados atingido; preserve o histórico.")
        measurement = {
            "id": uuid.uuid4().hex, "recordedAt": now(), "source": "owner_reported",
            "packageId": package["id"], "sourceSha256": package["sourceSha256"],
            "platform": platform, "postUrl": post_url, "windowHours": window,
            "videoDurationSeconds": package["durationSeconds"], "metrics": metrics,
            "rates": metric_rates(metrics), "notes": _text(payload.get("notes", ""), "notes", 1000),
        }
        state["measurements"].append(measurement)
        _save(directory, state)
    return get_publication(root, project_id)


def measurement_summary(measurements: list[dict[str, Any]]) -> dict[str, Any]:
    # Different observation windows and repeated snapshots of one post are not
    # independent experiments. Never sum snapshots into an inflated view count.
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for item in measurements:
        latest[(item["platform"], _post_identity(item["postUrl"]))] = item
    observations = list(latest.values())
    comparisons: list[dict[str, Any]] = []
    for item in observations:
        peers = [other for other in observations if other["postUrl"] != item["postUrl"]
                 and other["platform"] == item["platform"]
                 and abs(other["windowHours"] - item["windowHours"]) <= max(1, item["windowHours"] * .1)
                 and abs(other["videoDurationSeconds"] - item["videoDurationSeconds"]) <= max(1, item["videoDurationSeconds"] * .1)]
        values = [other["rates"]["retainedAt3SecondsPercent"]["value"] for other in peers
                  if "retainedAt3SecondsPercent" in other.get("rates", {})]
        own = item.get("rates", {}).get("retainedAt3SecondsPercent")
        if own and len(values) >= 3:
            baseline = statistics.median(values)
            comparisons.append({
                "measurementId": item["id"], "metric": "retainedAt3SecondsPercent",
                "value": own["value"], "peerMedian": baseline, "comparablePosts": len(values),
                "hypothesis": "Testar mais clareza na abertura." if own["value"] < baseline else "Abertura merece novos testes com público comparável.",
                "confidence": "descriptive_only",
            })
    return {
        "status": "DESCRIPTIVE_COMPARISON" if comparisons else "INCONCLUSIVE",
        "distinctPosts": len(observations), "snapshots": len(measurements), "comparisons": comparisons,
        "note": "Dados declarados pelo proprietário. Sem pesos secretos, previsão de views ou prova causal. Compare também tema e público; pouca exposição aumenta a incerteza.",
    }


def _post_identity(url: str) -> str:
    """Ignore sharing/tracking parameters without fetching any external URL."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    params = dict(parse_qsl(parsed.query))
    if host in {"youtube.com", "youtu.be"}:
        parts = parsed.path.strip("/").split("/")
        video_id = params.get("v") if parsed.path == "/watch" else (
            parts[0] if host == "youtu.be" else parts[1] if len(parts) > 1 and parts[0] in {"shorts", "embed"} else None
        )
        if video_id:
            return "youtube:" + video_id
    retained = [(key, value) for key, value in parse_qsl(parsed.query) if key in {"v", "story_fbid", "fbid", "id"}]
    return host + parsed.path.rstrip("/") + ("?" + urlencode(sorted(retained)) if retained else "")


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _approved_master(root: Path, project_id: str) -> tuple[Path, dict[str, Any]]:
    # Use the same canonical file/approval resolution as the existing player.
    # A technical pass or a READY file is insufficient to package for publishing.
    import video_projects
    project = video_projects.get_project(root, project_id)
    output = project.get("finalOutput") or {}
    if not output.get("ready") or output.get("stale") or output.get("reviewStatus") != "APPROVED_BY_OWNER":
        raise ValueError("A preparação do pacote exige o master exato aprovado pelo proprietário.")
    source = video_projects.get_project_final_output_path(root, project_id, download=True)
    if source.stat().st_size > 1024 * 1024 * 1024:
        raise ValueError("Master excede o limite de 1 GiB deste exportador local.")
    digest = _sha256(source)
    if not output.get("sha256") or digest != str(output["sha256"]).lower():
        raise ValueError("O hash do master diverge do arquivo aprovado.")
    return source, output


def _probe(path: Path) -> dict[str, Any]:
    binary = shutil.which("ffprobe")
    if not binary:
        raise ValueError("ffprobe não está disponível para verificar o pacote.")
    result = subprocess.run(
        [binary, "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=30, check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    metadata = json.loads(result.stdout)
    video = next((item for item in metadata.get("streams", []) if item.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("O master não contém um stream de vídeo válido.")
    duration = _number(float((metadata.get("format") or {}).get("duration") or 0), "duration", 7200)
    if duration <= 0:
        raise ValueError("Duração inválida no master.")
    return {"width": video["width"], "height": video["height"], "fps": video.get("r_frame_rate"), "durationSeconds": duration}


def create_package(root: Path, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"expectedRevision", "platform", "title", "description", "coverTimeSeconds", "captionsSrt", "variantLabel"}
    if set(payload) - allowed:
        raise ValueError("Campos não permitidos no pacote.")
    platform = payload.get("platform")
    if not isinstance(platform, str) or platform not in PLATFORMS:
        raise ValueError("Selecione a plataforma do pacote.")
    title = _text(payload.get("title"), "title", 160)
    if len(title) < 3:
        raise ValueError("O título deve ter pelo menos três caracteres.")
    description = _text(payload.get("description", ""), "description", 5000)
    label = _text(payload.get("variantLabel", "Original"), "variantLabel", 120)
    captions = _text(payload.get("captionsSrt", ""), "captionsSrt", 40000)
    if captions and ("-->" not in captions or "<" in captions or ">" in captions.replace("-->", "")):
        raise ValueError("Use legendas SRT em texto simples, sem HTML.")
    cover_time = _number(payload.get("coverTimeSeconds", 0), "coverTimeSeconds", 7200)
    directory = _project(root, project_id)
    with _LOCK:
        manifest, state = _load(directory)
        _enabled(manifest)
        _revision(state, payload.get("expectedRevision"))
        if not _plan_readiness(manifest, state)["readyForExistingGates"]:
            raise ValueError("Preencha a direção antes de preparar o pacote.")
        if len(state["packages"]) >= 100:
            raise ValueError("Limite de pacotes atingido; preserve o histórico.")
        source, approved = _approved_master(root, project_id)
        metadata = _probe(source)
        if cover_time >= metadata["durationSeconds"]:
            raise ValueError("O quadro de capa deve estar dentro da duração do vídeo.")
        if re.search(r"\b4k\b", title, re.IGNORECASE) and min(metadata["width"], metadata["height"]) < 2160:
            raise ValueError("O arquivo não tem resolução 4K; corrija o título.")
        if platform in {"youtube_shorts", "instagram_reels", "tiktok"} and metadata["width"] > metadata["height"]:
            raise ValueError("Este master é horizontal. Prepare e aprove o enquadramento vertical antes de exportar para esse destino; nenhum recorte será aplicado automaticamente.")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ValueError("ffmpeg não está disponível para extrair o quadro de capa.")
        package_id = uuid.uuid4().hex
        package_dir = _local(directory, f"edit/internet_packages/{package_id}")
        package_dir.mkdir(parents=True, exist_ok=False)
        record = {
            "id": package_id, "createdAt": now(), "status": "PENDING_PUBLICATION_REVIEW",
            "platform": platform, "title": title, "description": description, "variantLabel": label,
            "sourceFile": source.relative_to(directory).as_posix(),
            "sourceSha256": approved["sha256"].lower(), "planRevision": state["revision"],
            "planSha256": hashlib.sha256(json.dumps(state["plan"], sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
            "directionSourceFingerprint": state.get("directionSourceFingerprint"),
            "coverTimeSeconds": cover_time, "containsCaptions": bool(captions),
            "autoPublished": False, **metadata,
        }
        try:
            cover = package_dir / "capa.jpg"
            subprocess.run(
                [ffmpeg, "-nostdin", "-v", "error", "-ss", str(cover_time), "-i", str(source),
                 "-frames:v", "1", "-q:v", "2", str(cover)],
                capture_output=True, timeout=45, check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if not cover.is_file() or not cover.stat().st_size:
                raise ValueError("Não foi possível extrair o quadro de capa.")
            record["coverSha256"] = _sha256(cover)
            archive = package_dir / "publication.zip"
            with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as bundle:
                # Copy into an immutable delivery artifact; never hardlink or
                # alter the approved master, and never burn captions into it.
                bundle.write(source, "video" + source.suffix.lower())
                bundle.write(cover, "capa.jpg")
                bundle.writestr("titulo.txt", title)
                bundle.writestr("descricao.txt", description)
                if captions:
                    bundle.writestr("legendas.srt", captions)
                bundle.writestr("direcao.txt", planning_brief(manifest, state))
                bundle.writestr("manifest.json", json.dumps(record, ensure_ascii=False, indent=2))
                bundle.writestr("LEIA-ME.txt", "Pacote preparado localmente. Revise título, capa, legendas e o vídeo antes de publicar.\nA aprovação do master não aprova automaticamente novos metadados.\nNenhuma conta foi acessada e nenhuma publicação foi feita.\n")
            current_source, current_approved = _approved_master(root, project_id)
            if current_source != source or current_approved["sha256"].lower() != record["sourceSha256"]:
                raise PublicationConflictError("O master mudou durante a preparação; pacote preservado como falha.")
            # Verify the actual archived bitstream, not just its source path.
            with zipfile.ZipFile(archive) as bundle, bundle.open("video" + source.suffix.lower()) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != record["sourceSha256"]:
                    raise ValueError("Integridade do vídeo no pacote não confere.")
            record["zipSha256"] = _sha256(archive)
            record["zipBytes"] = archive.stat().st_size
        except Exception:
            record["status"] = "FAILED"
            state["packages"].append(record)
            _save(directory, state)
            raise
        state["packages"].append(record)
        _save(directory, state)
    return get_publication(root, project_id)


def package_download(root: Path, project_id: str, package_id: str) -> Path:
    if not isinstance(package_id, str) or not _UUID.fullmatch(package_id):
        raise ValueError("Identificador do pacote inválido.")
    directory = _project(root, project_id)
    with _LOCK:
        _, state = _load(directory)
        record = next((item for item in state["packages"] if item["id"] == package_id), None)
        if record is None or record.get("status") != "PENDING_PUBLICATION_REVIEW":
            raise FileNotFoundError(package_id)
        _, approved = _approved_master(root, project_id)
        if str(approved.get("sha256", "")).lower() != record.get("sourceSha256"):
            raise ValueError("O pacote pertence a um master anterior; preserve-o como histórico e prepare o master atualmente aprovado.")
        archive = _local(directory, f"edit/internet_packages/{package_id}/publication.zip")
        if not archive.is_file() or _sha256(archive) != record.get("zipSha256"):
            raise ValueError("O pacote foi modificado ou está ausente.")
        return archive
