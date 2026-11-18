#!/usr/bin/env python3
"""Fail-closed bridge from Unimedia editorial artifacts into Maestro contracts.

This module deliberately imports data contracts, never donor source code.  Its
first gate is a deterministic review package; project creation is implemented
below that gate so an automatic approval from the source run cannot silently
become a Maestro approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


BRIDGE_VERSION = "maestro_unimedia_editorial_bridge_v1_1"
REVIEW_SCHEMA_VERSION = "1.0"
IMPORT_INTEGRITY_SCHEMA_VERSION = "1.0"
IMPORT_INTEGRITY_RELATIVE_PATH = "qc/editorial_import/import-integrity.json"
SOURCE_REPOSITORY = "flaviomartil/unimedia-engine"
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_SCENES = 200
MAX_TAKE_DURATION_SECONDS = 10.0
MIN_TAKE_DURATION_SECONDS = 2.0
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_ASSET_BYTES = 1024 * 1024 * 1024
MIN_FREE_AFTER_IMPORT_BYTES = 512 * 1024 * 1024
MAX_VISIBLE_TEXT_ITEMS = 40
MAX_VISIBLE_TEXT_CHARS = 500
MAX_BRIEF_CHARS = 4000
IMAGE_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_ASSET_SUFFIXES = {".mp4", ".webm", ".mov"}
ASSET_KINDS = {"image", "photo", "template", "thumb", "video"}
IMAGE_ASSET_KINDS = ASSET_KINDS - {"video"}


class BridgeError(ValueError):
    """Raised when a bridge gate cannot safely continue."""


class Issue:
    __slots__ = ("code", "level", "message", "scene_id")

    def __init__(self, code: str, level: str, message: str, scene_id: str = "") -> None:
        self.code = code
        self.level = level
        self.message = message
        self.scene_id = scene_id

    def as_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "level": self.level, "message": self.message}
        if self.scene_id:
            payload["sceneId"] = self.scene_id
        return payload


class Bundle:
    __slots__ = (
        "root",
        "plan",
        "manifest",
        "cost",
        "factpack",
        "asset_rights",
        "artifact_hashes",
        "project_id",
        "issues",
        "metrics",
    )

    def __init__(
        self,
        *,
        root: Path,
        plan: dict[str, Any],
        manifest: dict[str, Any],
        cost: dict[str, Any] | None,
        factpack: dict[str, Any] | None,
        asset_rights: dict[str, Any] | None,
        artifact_hashes: dict[str, str],
        project_id: str,
        issues: list[Issue],
        metrics: dict[str, Any],
    ) -> None:
        self.root = root
        self.plan = plan
        self.manifest = manifest
        self.cost = cost
        self.factpack = factpack
        self.asset_rights = asset_rights
        self.artifact_hashes = artifact_hashes
        self.project_id = project_id
        self.issues = issues
        self.metrics = metrics

    @property
    def blocking_issues(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "blocking"]

    @property
    def risk_issues(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "risk"]


class ReviewPackage:
    __slots__ = (
        "directory",
        "manifest_path",
        "markdown_path",
        "approval_example_path",
        "authorization_example_path",
        "manifest_sha256",
    )

    def __init__(
        self,
        *,
        directory: Path,
        manifest_path: Path,
        markdown_path: Path,
        approval_example_path: Path,
        authorization_example_path: Path,
        manifest_sha256: str,
    ) -> None:
        self.directory = directory
        self.manifest_path = manifest_path
        self.markdown_path = markdown_path
        self.approval_example_path = approval_example_path
        self.authorization_example_path = authorization_example_path
        self.manifest_sha256 = manifest_sha256


class ApplyResult:
    __slots__ = ("project_dir", "created", "project_id", "take_count", "asset_count")

    def __init__(
        self,
        *,
        project_dir: Path,
        created: bool,
        project_id: str,
        take_count: int,
        asset_count: int,
    ) -> None:
        self.project_dir = project_dir
        self.created = created
        self.project_id = project_id
        self.take_count = take_count
        self.asset_count = asset_count


def _reject_non_finite_json(value: str) -> None:
    raise ValueError(f"constante numerica JSON nao finita: {value}")


def _read_json_object(path: Path, label: str, *, optional: bool = False) -> dict[str, Any] | None:
    if not path.is_file():
        if optional:
            return None
        raise BridgeError(f"{label} ausente: {path}")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise BridgeError(f"Nao foi possivel medir {label}: {exc}") from exc
    if size > MAX_JSON_BYTES:
        raise BridgeError(
            f"{label} excede o limite de {MAX_JSON_BYTES} bytes para importacao segura."
        )
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8-sig"),
            parse_constant=_reject_non_finite_json,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise BridgeError(f"{label} invalido em {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BridgeError(f"{label} deve ser um objeto JSON: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_pretty(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def _atomic_text_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _slugify(value: Any, fallback: str = "unimedia_editorial") -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:64]
    if not slug:
        slug = fallback
    if not PROJECT_ID_RE.fullmatch(slug):
        raise BridgeError("Identificador do projeto nao pode ser normalizado com seguranca.")
    return slug


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _asset_path(root: Path, raw_ref: Any) -> Path | None:
    ref = str(raw_ref or "").strip()
    if not ref:
        return None
    candidate = Path(ref)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _validate_factpack(factpack: dict[str, Any] | None, issues: list[Issue]) -> int:
    if factpack is None:
        issues.append(
            Issue(
                "factpack-missing",
                "risk",
                "O run nao trouxe factpack.json; afirmacoes ficam sem citacao verificavel no bridge.",
            )
        )
        return 0
    if factpack.get("version") != 1:
        issues.append(Issue("factpack-version", "blocking", "factpack.version deve ser 1."))
    source_hash = str(factpack.get("sourceHash") or "").lower()
    if not SHA256_RE.fullmatch(source_hash):
        issues.append(Issue("factpack-source-hash", "blocking", "factpack.sourceHash deve ser SHA-256."))
    facts = factpack.get("facts")
    if not isinstance(facts, list):
        issues.append(Issue("factpack-facts", "blocking", "factpack.facts deve ser uma lista."))
        return 0
    seen: set[str] = set()
    for index, fact in enumerate(facts):
        label = f"factpack.facts[{index}]"
        if not isinstance(fact, dict):
            issues.append(Issue("fact-invalid", "blocking", f"{label} deve ser objeto."))
            continue
        fact_id = str(fact.get("id") or "").strip()
        if not fact_id or fact_id in seen:
            issues.append(Issue("fact-id-invalid", "blocking", f"{label}.id ausente ou duplicado."))
        seen.add(fact_id)
        if not str(fact.get("claim") or "").strip():
            issues.append(Issue("fact-claim-missing", "blocking", f"{label}.claim esta vazio."))
        source_ref = fact.get("sourceRef")
        if not isinstance(source_ref, dict) or not str(source_ref.get("quote") or "").strip():
            issues.append(Issue("fact-quote-missing", "blocking", f"{label} nao possui citacao de origem."))
    return len(facts)


def _validate_plan_and_assets(
    root: Path,
    plan: dict[str, Any],
    manifest: dict[str, Any],
    issues: list[Issue],
) -> tuple[list[dict[str, Any]], int]:
    if plan.get("version") != 1:
        issues.append(Issue("plan-version", "blocking", "plan.version deve ser 1."))
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict):
        issues.append(Issue("canvas-missing", "blocking", "plan.canvas esta ausente."))
    else:
        width = _number(canvas.get("width"))
        height = _number(canvas.get("height"))
        if not width or not height or abs((width / height) - (16 / 9)) > 0.01:
            issues.append(
                Issue(
                    "canvas-policy",
                    "blocking",
                    "A politica LTX/Gemma vigente aceita este bridge somente em 16:9.",
                )
            )
    if str(manifest.get("aspect") or "16:9").strip() != "16:9":
        issues.append(Issue("manifest-aspect", "blocking", "manifest.aspect deve ser 16:9."))

    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issues.append(Issue("scenes-missing", "blocking", "plan.scenes deve conter ao menos uma cena."))
        return [], 0
    if len(scenes) > MAX_SCENES:
        issues.append(Issue("scene-count-policy", "blocking", f"O bridge aceita no maximo {MAX_SCENES} cenas."))
    manifest_count = manifest.get("sceneCount")
    if isinstance(manifest_count, int) and manifest_count != len(scenes):
        issues.append(
            Issue(
                "scene-count-mismatch",
                "blocking",
                f"manifest.sceneCount={manifest_count} diverge de plan.scenes={len(scenes)}.",
            )
        )

    seen_ids: set[str] = set()
    asset_count = 0
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            issues.append(Issue("scene-invalid", "blocking", f"plan.scenes[{index}] deve ser objeto."))
            continue
        scene_id = str(scene.get("id") or f"cena-{index + 1}").strip()
        if not scene_id or len(scene_id) > 64 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", scene_id):
            issues.append(Issue("scene-id-invalid", "blocking", "ID de cena invalido.", scene_id))
        if scene_id in seen_ids:
            issues.append(Issue("scene-id-duplicate", "blocking", "ID de cena duplicado.", scene_id))
        seen_ids.add(scene_id)
        if not str(scene.get("templateId") or "").strip():
            issues.append(Issue("scene-template-missing", "blocking", "Cena sem templateId.", scene_id))
        duration = _number(scene.get("durationSec"))
        if duration is None or duration < MIN_TAKE_DURATION_SECONDS or duration > MAX_TAKE_DURATION_SECONDS:
            issues.append(
                Issue(
                    "scene-duration-policy",
                    "blocking",
                    f"durationSec deve ficar entre {MIN_TAKE_DURATION_SECONDS:g}s e {MAX_TAKE_DURATION_SECONDS:g}s.",
                    scene_id,
                )
            )
        if not str(scene.get("title") or "").strip() and not str(scene.get("narration") or "").strip():
            issues.append(Issue("scene-content-missing", "blocking", "Cena sem titulo e narracao.", scene_id))
        if len(str(scene.get("artBrief") or "").strip()) < 8:
            issues.append(
                Issue("scene-art-brief-missing", "blocking", "Cena precisa de artBrief revisavel.", scene_id)
            )
        elif len(str(scene.get("artBrief") or "")) > MAX_BRIEF_CHARS:
            issues.append(
                Issue("scene-art-brief-too-long", "blocking", "artBrief excede o limite seguro.", scene_id)
            )
        if len(str(scene.get("motionBrief") or "").strip()) < 8:
            issues.append(
                Issue(
                    "scene-motion-brief-missing",
                    "blocking",
                    "Cena precisa de motionBrief antes de virar take.",
                    scene_id,
                )
            )
        elif len(str(scene.get("motionBrief") or "")) > MAX_BRIEF_CHARS:
            issues.append(
                Issue(
                    "scene-motion-brief-too-long",
                    "blocking",
                    "motionBrief excede o limite seguro.",
                    scene_id,
                )
            )
        visible_text = scene.get("visibleText")
        if visible_text is None:
            visible_text = []
        if (
            not isinstance(visible_text, list)
            or len(visible_text) > MAX_VISIBLE_TEXT_ITEMS
            or any(
                not isinstance(item, str) or len(item) > MAX_VISIBLE_TEXT_CHARS
                for item in visible_text
            )
        ):
            issues.append(
                Issue(
                    "scene-visible-text-invalid",
                    "blocking",
                    "visibleText deve conter somente strings curtas e limitadas.",
                    scene_id,
                )
            )
        cues = scene.get("cues")
        if cues is None:
            cues = []
        if not isinstance(cues, list):
            issues.append(Issue("scene-cues-invalid", "blocking", "scene.cues deve ser lista.", scene_id))
        else:
            for cue in cues:
                if not isinstance(cue, dict) or not isinstance(cue.get("text", ""), str):
                    issues.append(
                        Issue("scene-cue-invalid", "blocking", "Cue editorial invalido.", scene_id)
                    )
                    continue
                cue_at = _number(cue.get("at"))
                if cue_at is None or cue_at < 0 or duration is None or cue_at > duration:
                    issues.append(
                        Issue(
                            "scene-cue-timing",
                            "blocking",
                            "Cue editorial deve ficar dentro da duracao da cena.",
                            scene_id,
                        )
                    )
                if len(str(cue.get("text") or "")) > MAX_VISIBLE_TEXT_CHARS:
                    issues.append(
                        Issue("scene-cue-too-long", "blocking", "Texto do cue excede o limite.", scene_id)
                    )
        assets = scene.get("assets")
        if assets is None:
            assets = []
        if not isinstance(assets, list):
            issues.append(Issue("scene-assets-invalid", "blocking", "scene.assets deve ser lista.", scene_id))
            continue
        for asset_index, asset in enumerate(assets):
            asset_count += 1
            if not isinstance(asset, dict):
                issues.append(Issue("asset-invalid", "blocking", "Asset deve ser objeto.", scene_id))
                continue
            resolved = _asset_path(root, asset.get("ref"))
            if resolved is None:
                issues.append(Issue("asset-ref-missing", "blocking", "Asset sem ref.", scene_id))
                continue
            if not _is_inside(resolved, root):
                issues.append(
                    Issue(
                        "asset-outside-source",
                        "blocking",
                        f"Asset {asset_index + 1} saiu da raiz do run.",
                        scene_id,
                    )
                )
                continue
            if not resolved.is_file():
                issues.append(Issue("asset-missing", "blocking", f"Asset ausente: {resolved.name}.", scene_id))
                continue
            kind = str(asset.get("kind") or "image").casefold()
            expected_suffixes = VIDEO_ASSET_SUFFIXES if kind == "video" else IMAGE_ASSET_SUFFIXES
            if kind not in ASSET_KINDS or resolved.suffix.casefold() not in expected_suffixes:
                issues.append(
                    Issue(
                        "asset-media-type",
                        "blocking",
                        "Tipo/extensao do asset nao pertence a lista permitida.",
                        scene_id,
                    )
                )
                continue
            if resolved.stat().st_size > MAX_ASSET_BYTES:
                issues.append(
                    Issue("asset-size-limit", "blocking", "Asset excede o limite de tamanho.", scene_id)
                )
                continue
            expected = str(asset.get("sha256") or "").lower()
            if not SHA256_RE.fullmatch(expected):
                issues.append(Issue("asset-hash-missing", "blocking", "Asset sem SHA-256 valido.", scene_id))
            elif _sha256(resolved) != expected:
                issues.append(Issue("asset-hash-mismatch", "blocking", "SHA-256 do asset divergiu.", scene_id))
    return scenes, asset_count


def _metrics(
    scenes: list[dict[str, Any]],
    fact_count: int,
    asset_count: int,
    manifest: dict[str, Any],
    cost: dict[str, Any] | None,
) -> dict[str, Any]:
    durations = [
        float(value)
        for scene in scenes
        if isinstance(scene, dict)
        for value in [_number(scene.get("durationSec"))]
        if value is not None
    ]
    templates = [str(scene.get("templateId") or "").strip() for scene in scenes if isinstance(scene, dict)]
    templates = [template for template in templates if template]
    titles = [str(scene.get("title") or "").strip().casefold() for scene in scenes if isinstance(scene, dict)]
    repeated_titles = len(titles) - len(set(title for title in titles if title))
    total_cost = 0.0
    if isinstance(cost, dict):
        totals = cost.get("totals")
        if isinstance(totals, dict):
            total_cost = _number(totals.get("usd")) or 0.0
    if total_cost == 0:
        source_cost = manifest.get("cost")
        if isinstance(source_cost, dict):
            total_cost = _number(source_cost.get("usd")) or 0.0
    reuse = manifest.get("reuse") if isinstance(manifest.get("reuse"), dict) else {}
    return {
        "sceneCount": len(scenes),
        "durationSeconds": round(sum(durations), 6),
        "averageSceneSeconds": round(sum(durations) / len(durations), 6) if durations else 0,
        "maximumSceneSeconds": max(durations, default=0),
        "templateUniqueRatio": round(len(set(templates)) / len(templates), 6) if templates else 0,
        "repeatedTitleCount": repeated_titles,
        "factCount": fact_count,
        "assetCount": asset_count,
        "sourceCostUsd": round(total_cost, 6),
        "assetsReused": int(reuse.get("reused") or 0),
        "assetsGenerated": int(reuse.get("generated") or 0),
    }


def load_bundle(source_dir: str | Path) -> Bundle:
    """Read and validate a source run without writing anywhere."""

    root = Path(source_dir).expanduser().resolve()
    if not root.is_dir():
        raise BridgeError(f"Diretorio de run ausente: {root}")
    plan_path = root / "plan.json"
    manifest_path = root / "manifest.json"
    cost_path = root / "cost.json"
    factpack_path = root / "factpack.json"
    rights_path = root / "asset-rights.json"
    plan = _read_json_object(plan_path, "plan.json")
    manifest = _read_json_object(manifest_path, "manifest.json")
    assert plan is not None and manifest is not None
    cost = _read_json_object(cost_path, "cost.json", optional=True)
    factpack = _read_json_object(factpack_path, "factpack.json", optional=True)
    asset_rights = _read_json_object(rights_path, "asset-rights.json", optional=True)

    artifact_paths = [plan_path, manifest_path]
    for optional_path in (cost_path, factpack_path, rights_path):
        if optional_path.is_file():
            artifact_paths.append(optional_path)
    artifact_hashes = {path.name: _sha256(path) for path in artifact_paths}

    issues: list[Issue] = []
    run_id = str(manifest.get("runId") or plan.get("id") or "unimedia_editorial")
    project_id = _slugify(run_id)
    scenes, asset_count = _validate_plan_and_assets(root, plan, manifest, issues)
    fact_count = _validate_factpack(factpack, issues)
    gates = manifest.get("gates") if isinstance(manifest.get("gates"), dict) else {}
    roteiro = gates.get("roteiro") if isinstance(gates.get("roteiro"), dict) else {}
    if str(roteiro.get("approvedBy") or "").casefold() != "human":
        issues.append(
            Issue(
                "source-auto-approved",
                "risk",
                "O roteiro de origem nao registra aprovacao humana; o gate do Maestro deve substitui-la.",
            )
        )
    degraded = manifest.get("degraded")
    if isinstance(degraded, list) and degraded:
        issues.append(
            Issue(
                "source-degraded",
                "risk",
                "O run declara degradacoes: " + ", ".join(str(item) for item in degraded) + ".",
            )
        )
    metrics = _metrics(scenes, fact_count, asset_count, manifest, cost)
    return Bundle(
        root=root,
        plan=plan,
        manifest=manifest,
        cost=cost,
        factpack=factpack,
        asset_rights=asset_rights,
        artifact_hashes=artifact_hashes,
        project_id=project_id,
        issues=issues,
        metrics=metrics,
    )


def build_review_manifest(bundle: Bundle) -> dict[str, Any]:
    scenes = []
    for index, scene in enumerate(bundle.plan.get("scenes") or []):
        if not isinstance(scene, dict):
            continue
        scenes.append(
            {
                "sceneId": str(scene.get("id") or f"cena-{index + 1}"),
                "templateId": str(scene.get("templateId") or ""),
                "title": str(scene.get("title") or ""),
                "narration": str(scene.get("narration") or ""),
                "visibleText": scene.get("visibleText") if isinstance(scene.get("visibleText"), list) else [],
                "durationSec": _number(scene.get("durationSec")) or 0,
                "artBrief": str(scene.get("artBrief") or ""),
                "motionBrief": str(scene.get("motionBrief") or ""),
                "assetCount": len(scene.get("assets") or []) if isinstance(scene.get("assets"), list) else 0,
            }
        )
    return {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "kind": "maestro-unimedia-editorial-review",
        "bridgeVersion": BRIDGE_VERSION,
        "sourceRepository": SOURCE_REPOSITORY,
        "sourceRunId": str(bundle.manifest.get("runId") or bundle.plan.get("id") or ""),
        "sourceArtifacts": bundle.artifact_hashes,
        "candidate": {
            "projectId": bundle.project_id,
            "title": str(bundle.plan.get("title") or bundle.manifest.get("title") or bundle.project_id),
            "topic": str(bundle.plan.get("topic") or bundle.manifest.get("topic") or ""),
            "language": str(bundle.plan.get("language") or bundle.manifest.get("language") or "pt-BR"),
            "style": str(bundle.plan.get("style") or bundle.manifest.get("style") or ""),
        },
        "metrics": bundle.metrics,
        "issues": [issue.as_dict() for issue in bundle.issues],
        "scenes": scenes,
        "maestroPolicy": {
            "sourceOfTruth": "Maestro",
            "primaryTakeOrchestration": "primary_take_orchestration_h3_ltx25_v1",
            "engineSelection": "owner_required_no_default_no_fallback",
            "audioDefault": "visual_only",
            "nativeAudioWithoutOwnerDirective": "forbidden",
            "gpuWorkStartedByImport": False,
            "assetsImportedByDefault": False,
            "humanReview": "fail_closed_sha256_bound",
        },
        "rightsGate": {
            "requiredBeforeApply": True,
            "codeCopiedFromSourceRepository": False,
            "assetBytesRequireSeparateRightsManifest": True,
        },
    }


def _review_markdown(bundle: Bundle, payload: dict[str, Any], manifest_sha256: str) -> str:
    lines = [
        f"# Review editorial para o Maestro — {payload['candidate']['title']}",
        "",
        f"- Projeto candidato: `{bundle.project_id}`",
        f"- Run de origem: `{payload['sourceRunId']}`",
        f"- Cenas: {bundle.metrics['sceneCount']}",
        f"- Duracao estimada: {bundle.metrics['durationSeconds']}s",
        f"- Custo registrado na origem: USD {bundle.metrics['sourceCostUsd']:.6f}",
        f"- SHA-256 deste manifest: `{manifest_sha256}`",
        "",
        "## Gates obrigatorios",
        "",
        "- O Maestro continua sendo a fonte de verdade.",
        "- O importador nao inicia GPU, audio, render ou publicacao.",
        "- Audio entra como `visual_only` ate diretiva explicita do proprietario.",
        "- Codigo do repositorio de origem nao e copiado.",
        "- Bytes de assets exigem autorizacao e manifest de direitos separados.",
        "",
    ]
    if bundle.blocking_issues:
        lines.extend(["## Bloqueios", ""])
        for issue in bundle.blocking_issues:
            suffix = f" (`{issue.scene_id}`)" if issue.scene_id else ""
            lines.append(f"- `{issue.code}`{suffix}: {issue.message}")
        lines.append("")
    if bundle.risk_issues:
        lines.extend(["## Riscos que exigem aceite explicito", ""])
        for issue in bundle.risk_issues:
            lines.append(f"- `{issue.code}`: {issue.message}")
        lines.append("")
    lines.extend(["## Cenas", ""])
    for scene in payload["scenes"]:
        lines.extend(
            [
                f"### {scene['sceneId']} — {scene['title'] or '(sem titulo)'}",
                "",
                f"- Template: `{scene['templateId']}`",
                f"- Duracao: {scene['durationSec']}s",
                f"- Arte: {scene['artBrief'] or '(ausente)'}",
                f"- Movimento: {scene['motionBrief'] or '(ausente)'}",
                "",
                f"**Narracao:** {scene['narration'] or '(vazia)'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Como aprovar",
            "",
            "1. Corrija todos os bloqueios acima.",
            "2. Obtenha autorizacao escrita para uso derivado/comercial dos dados que serao importados.",
            "3. Copie `approved.example.json` para `approved.json`, preencha o revisor e mantenha o SHA exato.",
            "4. Copie `authorization.example.json` para `authorization.json` somente com evidencia real do titular.",
            "",
        ]
    )
    return "\n".join(lines)


def write_review_package(bundle: Bundle, review_dir: str | Path) -> ReviewPackage:
    """Write deterministic review artifacts; never create an approval."""

    directory = Path(review_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "editorial-review.manifest.json"
    markdown_path = directory / "editorial-review.md"
    approval_example_path = directory / "approved.example.json"
    authorization_example_path = directory / "authorization.example.json"

    payload = build_review_manifest(bundle)
    manifest_text = _canonical_pretty(payload)
    manifest_sha256 = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    _atomic_text_write(manifest_path, manifest_text)
    _atomic_text_write(markdown_path, _review_markdown(bundle, payload, manifest_sha256))
    _atomic_text_write(
        approval_example_path,
        _canonical_pretty(
            {
                "approved": True,
                "manifestSha256": manifest_sha256,
                "reviewer": "PREENCHER",
                "approvedAt": "PREENCHER_ISO_8601",
                "acceptedRisks": [issue.code for issue in bundle.risk_issues],
                "importAssets": False,
                "note": "Aprovacao editorial para criar projeto PLANNED; nao autoriza GPU nem publicacao.",
            }
        ),
    )
    _atomic_text_write(
        authorization_example_path,
        _canonical_pretty(
            {
                "schemaVersion": "1.0",
                "sourceRepository": SOURCE_REPOSITORY,
                "authorizationBasis": "repository_owner_written_permission",
                "grantor": "PREENCHER_TITULAR",
                "authorizedTo": "Pemara",
                "grantedAt": "PREENCHER_ISO_8601",
                "scopes": ["generated_editorial_metadata"],
                "assetRightsConfirmed": False,
                "evidenceReference": "PREENCHER_CAMINHO_OU_REFERENCIA_DA_AUTORIZACAO",
            }
        ),
    )
    return ReviewPackage(
        directory=directory,
        manifest_path=manifest_path,
        markdown_path=markdown_path,
        approval_example_path=approval_example_path,
        authorization_example_path=authorization_example_path,
        manifest_sha256=manifest_sha256,
    )


def validate_review_approval(
    approval_path: str | Path,
    review: ReviewPackage,
    bundle: Bundle,
) -> dict[str, Any]:
    """Validate a human approval bound to the exact review manifest."""

    if bundle.blocking_issues:
        codes = ", ".join(issue.code for issue in bundle.blocking_issues)
        raise BridgeError(f"A revisao possui bloqueios que nao podem ser aceitos: {codes}.")
    expected_text = _canonical_pretty(build_review_manifest(bundle))
    expected_sha = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    try:
        actual_sha = _sha256(review.manifest_path)
    except OSError as exc:
        raise BridgeError(f"Nao foi possivel verificar a integridade do review: {exc}") from exc
    if review.manifest_sha256 != expected_sha or actual_sha != expected_sha:
        raise BridgeError(
            "Integridade do review falhou: o manifest foi alterado ou nao representa o bundle atual."
        )
    approval = _read_json_object(Path(approval_path).expanduser().resolve(), "approved.json")
    assert approval is not None
    if approval.get("approved") is not True:
        raise BridgeError("approved.json precisa declarar approved=true.")
    approved_sha = str(approval.get("manifestSha256") or "").lower()
    if approved_sha != review.manifest_sha256:
        raise BridgeError("Aprovacao obsoleta: manifestSha256 nao corresponde ao review atual.")
    reviewer = str(approval.get("reviewer") or "").strip()
    approved_at = str(approval.get("approvedAt") or "").strip()
    if len(reviewer) < 2 or not approved_at or "T" not in approved_at:
        raise BridgeError("approved.json precisa registrar reviewer e approvedAt ISO-8601.")
    accepted = approval.get("acceptedRisks")
    if not isinstance(accepted, list) or any(not isinstance(item, str) for item in accepted):
        raise BridgeError("approved.json.acceptedRisks deve ser uma lista de codigos.")
    required = {issue.code for issue in bundle.risk_issues}
    missing = sorted(required - set(accepted))
    if missing:
        raise BridgeError("Riscos sem aceite explicito: " + ", ".join(missing) + ".")
    if not isinstance(approval.get("importAssets", False), bool):
        raise BridgeError("approved.json.importAssets deve ser booleano.")
    return approval


def validate_source_authorization(
    authorization_path: str | Path,
    *,
    import_assets: bool = False,
) -> dict[str, Any]:
    """Require an explicit rights basis before any project data is copied."""

    authorization = _read_json_object(
        Path(authorization_path).expanduser().resolve(), "authorization.json"
    )
    assert authorization is not None
    if str(authorization.get("schemaVersion") or "") != "1.0":
        raise BridgeError("authorization.json.schemaVersion deve ser 1.0.")
    if str(authorization.get("sourceRepository") or "") != SOURCE_REPOSITORY:
        raise BridgeError(f"authorization.json deve cobrir {SOURCE_REPOSITORY}.")
    basis = str(authorization.get("authorizationBasis") or "").strip()
    allowed_bases = {
        "repository_owner_written_permission",
        "explicit_license",
        "original_content_owner",
    }
    if basis not in allowed_bases:
        raise BridgeError("authorizationBasis nao comprova uma base de uso aceita pelo bridge.")
    grantor = str(authorization.get("grantor") or "").strip()
    granted_at = str(authorization.get("grantedAt") or "").strip()
    evidence = str(authorization.get("evidenceReference") or "").strip()
    authorized_to = str(authorization.get("authorizedTo") or "").strip().casefold()
    if len(grantor) < 2 or "T" not in granted_at or len(evidence) < 5:
        raise BridgeError("authorization.json precisa de grantor, grantedAt ISO e evidenceReference.")
    if authorized_to != "pemara":
        raise BridgeError("authorization.json.authorizedTo deve identificar a Pemara.")
    scopes = authorization.get("scopes")
    if not isinstance(scopes, list) or any(not isinstance(item, str) for item in scopes):
        raise BridgeError("authorization.json.scopes deve ser uma lista de strings.")
    scope_set = set(scopes)
    if "generated_editorial_metadata" not in scope_set:
        raise BridgeError("A autorizacao nao cobre generated_editorial_metadata.")
    if import_assets:
        if "generated_assets" not in scope_set:
            raise BridgeError("A importacao de assets exige o escopo generated_assets.")
        if authorization.get("assetRightsConfirmed") is not True:
            raise BridgeError("A importacao de assets exige assetRightsConfirmed=true.")
    return authorization


def _default_engine_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_queue_template(engine_root: Path) -> dict[str, Any]:
    template_path = engine_root / "templates" / "editorial_import_queue.template.json"
    template = _read_json_object(template_path, "editorial_import_queue.template.json")
    assert template is not None
    policy_path = engine_root / "policies" / "primary_take_orchestration_h3_ltx25.json"
    policy = _read_json_object(policy_path, "primary_take_orchestration_h3_ltx25.json")
    assert policy is not None
    if policy.get("policy_id") != "primary_take_orchestration_h3_ltx25_v1":
        raise BridgeError("A politica primaria vigente nao corresponde ao contrato do bridge.")
    selection = policy.get("selection") if isinstance(policy.get("selection"), dict) else {}
    if (
        selection.get("required") is not True
        or selection.get("default_engine_id") is not None
        or selection.get("fallback_allowed") is not False
    ):
        raise BridgeError("A politica deve exigir escolha explicita entre H3 e LTX 2.5, sem fallback.")
    allowed_engine_ids = {
        str(item.get("engine_id") or "").strip()
        for item in selection.get("allowed_engines", [])
        if isinstance(item, dict)
    }
    if allowed_engine_ids != {"minimax_h3", "ltx_2_5"}:
        raise BridgeError("A politica do bridge deve permitir somente H3 e LTX 2.5.")
    review_policy = (
        template.get("engine_policy", {}).get("review_motion_pipeline", {})
        if isinstance(template.get("engine_policy"), dict)
        else {}
    )
    required = {
        "version": "h3_ltx25_rife425_midpoint48_retime60_v1",
        "status": "LOCKED_APPROVED",
        "source_fps": 24,
    }
    if any(review_policy.get(key) != value for key, value in required.items()):
        raise BridgeError("Template editorial divergiu da politica temporal aprovada.")
    return json.loads(json.dumps(template))


def _frames_for_duration(duration_seconds: float) -> int:
    intervals = max(6, min(30, int(round(duration_seconds * 3))))
    return intervals * 8 + 1


def _scene_palette(scene: dict[str, Any]) -> list[str]:
    palette = scene.get("palette")
    if not isinstance(palette, dict):
        return []
    values: list[str] = []
    for value in palette.values():
        color = str(value or "").strip()
        if color and color not in values:
            values.append(color)
    return values


def _animation_prompt(scene: dict[str, Any]) -> str:
    motion = str(scene.get("motionBrief") or "").strip()
    return (
        f"{motion} Animate the approved anchor as one readable cinematic infographic take. "
        "Use evident physical camera translation, coherent foreground/midground/background depth, "
        "independent internal action and materially different start, middle and end states. "
        "Preserve the approved layout, identity, objects, palette and information hierarchy exactly. "
        "Do not generate text, captions, logos, watermarks, extra subjects or native audio. "
        "Finish on the last information cue with a clean motivated cut and no static tail."
    ).strip()


def _take_from_scene(
    scene: dict[str, Any],
    *,
    index: int,
    timeline_start: float,
    plan: dict[str, Any],
    review: ReviewPackage,
    reviewer: str,
) -> dict[str, Any]:
    take_id = f"{index + 1:03d}"
    source_scene_id = str(scene.get("id") or f"cena-{index + 1}")
    title = str(scene.get("title") or source_scene_id).strip()
    narration = str(scene.get("narration") or "").strip()
    art_brief = str(scene.get("artBrief") or "").strip()
    motion_brief = str(scene.get("motionBrief") or "").strip()
    design_brief = str(plan.get("designBrief") or plan.get("artDirection") or "").strip()
    duration = float(_number(scene.get("durationSec")) or 0)
    negative = [
        "no generated text",
        "no watermark",
        "no native audio",
        "no slideshow",
        "no living photo",
        "no digital zoom only",
        "no flat 2D parallax only",
        "no static tail",
    ]
    project_negative = str(plan.get("artNegative") or "").strip()
    if project_negative:
        negative.append(project_negative)
    source_assets = []
    for asset in scene.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        source_assets.append(
            {
                "kind": str(asset.get("kind") or "image"),
                "sha256": str(asset.get("sha256") or ""),
                "role": str(asset.get("role") or ""),
                "status": "reference_only_not_imported",
            }
        )
    return {
        "id": take_id,
        "slug": _slugify(title, fallback=f"take_{take_id}"),
        "timeline_start_seconds": round(timeline_start, 6),
        "timeline_end_seconds": round(timeline_start + duration, 6),
        "target_duration_seconds": duration,
        "role": "educational_infographic_take",
        "objective": title or narration,
        "transition": {"is_transition": False},
        "editorial": {
            "source_scene_id": source_scene_id,
            "template_id": str(scene.get("templateId") or ""),
            "slide": str(scene.get("slide") or ""),
            "title": title,
            "narration": narration,
            "visible_text": scene.get("visibleText") if isinstance(scene.get("visibleText"), list) else [],
            "keywords": scene.get("keywords") if isinstance(scene.get("keywords"), list) else [],
            "cues": scene.get("cues") if isinstance(scene.get("cues"), list) else [],
            "palette": scene.get("palette") if isinstance(scene.get("palette"), dict) else {},
            "art_brief": art_brief,
            "motion_brief": motion_brief,
            "source_assets": source_assets,
            "review_manifest_sha256": review.manifest_sha256,
            "reviewed_by": reviewer,
        },
        "shot_contract": {
            "provider_style": BRIDGE_VERSION,
            "subject": art_brief,
            "action": motion_brief,
            "scene": title,
            "camera": {
                "angle": "defined by the approved editorial art brief",
                "movement": motion_brief,
                "lens": "preserve readable infographic geometry",
                "focus": "information hierarchy locked",
            },
            "lighting": design_brief,
            "mood": str(plan.get("style") or "editorial"),
            "motion_beats": {
                "start": "establish the approved composition and first information cue",
                "middle": motion_brief,
                "end": "land on the final information cue and prepare a clean cut",
            },
            "visual_references": {
                "start_frame": "",
                "start_frame_json": "",
                "end_frame": "",
                "end_frame_json": "",
                "style_refs": [],
                "object_refs": [],
            },
            "variants": {"count": 1, "duration_seconds": duration, "select_before_final": True},
            "negative_rules": negative,
        },
        "base_image": {
            "status": "pending_human_qc",
            "model": "pending_maestro_selection",
            "prompt": " ".join(value for value in (design_brief, art_brief) if value),
            "negative_prompt": ", ".join(negative),
            "file": "",
            "metadata": "",
            "json_rule": "required_sidecar_before_video",
            "approval_required_before_video": True,
            "candidate_assets": [],
        },
        "video_generation": {
            "profile": "owner_selection_required",
            "engine_selection_required": True,
            "allowed_profiles": [
                "minimax_h3_fl2va_int8_720p24",
                "ltx25_two_stage_distilled_960x544p24",
            ],
            "fallback_allowed": False,
            "backend": "pending_owner_selection",
            "text_encoder": "engine_managed_after_selection",
            "conditioning_profile": "identity_locked",
            "width": 0,
            "height": 0,
            "fps": 0,
            "frames": 0,
            "steps": 0,
            "guidance": 0.0,
            "start_end_frame_enabled": False,
        },
        "audio_directive": {
            "status": "awaiting_owner_directive",
            "authority": "owner_only",
            "scope": "this_take",
            "mode": "visual_only",
            "usage_authorized": False,
            "inherit_from_previous_take": False,
            "inherit_from_previous_project": False,
            "source_file": "",
            "timing": "",
            "mix_instructions": "",
            "owner_approval": "pending",
        },
        "animation_prompt": _animation_prompt(scene),
        "motion_layers": {
            "camera": motion_brief,
            "foreground": "readable foreground with coherent differential motion",
            "midground": "primary information action independent from the camera",
            "background": "stable geography with slower coherent motion",
            "internal_action": "reveal approved information cues without generating text",
            "lighting_particles": "supporting only; never replace the information event",
        },
        "video": {
            "status": "pending",
            "preview_model": "Owner selection required: MiniMax H3 or LTX 2.5",
            "final_model": "approved H3 or LTX 2.5 take plus post-approval RealESRGAN FHD",
            "provider_profile": "primary_take_orchestration_h3_ltx25_v1",
            "output_preview": "",
            "output_final": "",
        },
        "qc": {
            "status": "pending",
            "editorial_gate": {
                "status": "approved_for_project_planning",
                "manifest_sha256": review.manifest_sha256,
                "reviewer": reviewer,
            },
            "contact_sheet": "",
            "first_frame": "",
            "mid_frame": "",
            "last_frame": "",
            "approval_criteria": [
                "approved information hierarchy preserved",
                "visible text is added in deterministic post-production only",
                "evident physical camera movement and perspective change",
                "real foreground, midground and background depth",
                "internal action independent from the camera",
                "clear progression through start, middle and end",
                "no text leakage, watermark, native audio or identity drift",
            ],
            "rejection_reasons": [],
        },
        "maestro_status": "PLANNED",
    }


def build_project_payloads(
    bundle: Bundle,
    review: ReviewPackage,
    approval: dict[str, Any],
    authorization: dict[str, Any],
    *,
    engine_root: str | Path | None = None,
    now: str | None = None,
    imported_assets: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build native Maestro payloads without writing project state."""

    if bundle.blocking_issues:
        raise BridgeError("Nao e possivel montar projeto com bloqueios editoriais.")
    if str(approval.get("manifestSha256") or "") != review.manifest_sha256:
        raise BridgeError("Aprovacao nao pertence ao review informado.")
    if str(authorization.get("sourceRepository") or "") != SOURCE_REPOSITORY:
        raise BridgeError("Autorizacao nao pertence ao repositorio de origem.")
    root = Path(engine_root).resolve() if engine_root is not None else _default_engine_root()
    queue = _load_queue_template(root)
    created_at = now or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    scenes = [scene for scene in bundle.plan.get("scenes") or [] if isinstance(scene, dict)]
    first_scene = scenes[0] if scenes else {}
    factpack = bundle.factpack or {}
    objectives = factpack.get("learningObjectives") if isinstance(factpack.get("learningObjectives"), list) else []
    objective = "; ".join(str(item).strip() for item in objectives if str(item).strip())
    if not objective:
        objective = str(bundle.plan.get("topic") or bundle.manifest.get("topic") or "").strip()
    reviewer = str(approval.get("reviewer") or "")
    bridge_record = {
        "bridge_version": BRIDGE_VERSION,
        "source_repository": SOURCE_REPOSITORY,
        "source_run_id": str(bundle.manifest.get("runId") or bundle.plan.get("id") or ""),
        "source_artifacts": bundle.artifact_hashes,
        "review_manifest_sha256": review.manifest_sha256,
        "reviewer": reviewer,
        "approved_at": str(approval.get("approvedAt") or ""),
        "accepted_risks": list(approval.get("acceptedRisks") or []),
        "authorization_basis": str(authorization.get("authorizationBasis") or ""),
        "authorization_grantor": str(authorization.get("grantor") or ""),
        "authorization_evidence": str(authorization.get("evidenceReference") or ""),
        "authorization_scopes": list(authorization.get("scopes") or []),
        "asset_import_requested": bool(approval.get("importAssets", False)),
        "gpu_work_started": False,
        "code_copied_from_source_repository": False,
    }
    manifest = {
        "schema_version": "1.2",
        "project_id": bundle.project_id,
        "title": str(bundle.plan.get("title") or bundle.manifest.get("title") or bundle.project_id),
        "idea": str(bundle.plan.get("topic") or bundle.manifest.get("topic") or ""),
        "objective": objective,
        "audience": str(factpack.get("audience") or "not_specified"),
        "duration_target_seconds": bundle.metrics["durationSeconds"],
        "aspect_ratio": "16:9",
        "preview_resolution": "1280x720",
        "final_resolution": "1920x1080",
        "fps_preview": 60,
        "fps_final": 60,
        "style": {
            "primary": str(bundle.plan.get("style") or "editorial"),
            "references": [],
            "palette": _scene_palette(first_scene),
            "mood": [str(bundle.plan.get("artDirection") or "editorial")],
        },
        "audio": {
            "directive_status": "awaiting_owner_directive",
            "authority": "owner_only",
            "scope": "take_or_project_as_explicitly_communicated",
            "default_without_directive": "visual_only",
            "inherit_from_previous_take": False,
            "inherit_from_previous_project": False,
            "mode": "visual_only",
            "file": "",
            "duration_seconds": None,
            "timeline_rule": "visual_story_beats_until_owner_audio_directive",
            "music_provider": None,
            "voice_provider": None,
        },
        "created_at": created_at,
        "updated_at": created_at,
        "maestro_status": "PLANNED",
        "primary_orchestration_policy": "../../policies/primary_take_orchestration_h3_ltx25.json",
        "take_queue": "take_queue.json",
        "editorial_bridge": bridge_record,
    }
    timeline = 0.0
    takes = []
    for index, scene in enumerate(scenes):
        take = _take_from_scene(
            scene,
            index=index,
            timeline_start=timeline,
            plan=bundle.plan,
            review=review,
            reviewer=reviewer,
        )
        takes.append(take)
        timeline += float(_number(scene.get("durationSec")) or 0)
    queue["project_id"] = bundle.project_id
    queue["takes"] = takes
    queue["source_editorial"] = bridge_record
    plan_negative = str(bundle.plan.get("artNegative") or "").strip()
    if plan_negative and plan_negative not in queue["global_negative_rules"]:
        queue["global_negative_rules"].append(plan_negative)

    overlay_scenes = []
    for index, scene in enumerate(scenes):
        overlay_scenes.append(
            {
                "takeId": f"{index + 1:03d}",
                "sourceSceneId": str(scene.get("id") or f"cena-{index + 1}"),
                "templateId": str(scene.get("templateId") or ""),
                "slide": str(scene.get("slide") or ""),
                "title": str(scene.get("title") or ""),
                "visibleText": scene.get("visibleText") if isinstance(scene.get("visibleText"), list) else [],
                "keywords": scene.get("keywords") if isinstance(scene.get("keywords"), list) else [],
                "cues": scene.get("cues") if isinstance(scene.get("cues"), list) else [],
                "palette": scene.get("palette") if isinstance(scene.get("palette"), dict) else {},
                "durationSec": _number(scene.get("durationSec")) or 0,
                "renderPolicy": "deterministic_post_production_only",
            }
        )
    editorial = {
        "factpack": bundle.factpack
        or {
            "version": 1,
            "status": "missing_requires_human_source_citations",
            "facts": [],
            "forbiddenInferences": [],
        },
        "cost": bundle.cost
        or {
            "version": 1,
            "status": "not_supplied",
            "entries": [],
            "totals": {"usd": bundle.metrics["sourceCostUsd"]},
        },
        "overlay_plan": {
            "schemaVersion": "1.0",
            "projectId": bundle.project_id,
            "canvas": bundle.plan.get("canvas") if isinstance(bundle.plan.get("canvas"), dict) else {},
            "audioMode": "visual_only",
            "textPolicy": "never_generated_inside_image_or_video_model",
            "scenes": overlay_scenes,
        },
        "plan_qc": {
            "schemaVersion": "1.0",
            "projectId": bundle.project_id,
            "reviewManifestSha256": review.manifest_sha256,
            "metrics": bundle.metrics,
            "issues": [issue.as_dict() for issue in bundle.issues],
            "gates": {
                "editorialHumanReview": "PASS",
                "rightsAuthorization": "PASS_METADATA_ONLY"
                if not approval.get("importAssets")
                else "PASS_METADATA_AND_ASSETS",
                "anchorHumanReview": "PENDING",
                "motionHumanReview": "PENDING",
                "finalMasterQc": "PENDING",
            },
        },
        "asset_catalog": {
            "schemaVersion": "1.0",
            "projectId": bundle.project_id,
            "retrievalPolicy": "only_human_approved_entries_are_reusable",
            "entries": imported_assets or [],
        },
    }
    return manifest, queue, editorial


def _rights_entries(bundle: Bundle) -> dict[str, dict[str, Any]]:
    rights = bundle.asset_rights
    if not isinstance(rights, dict):
        raise BridgeError("importAssets=true exige asset-rights.json.")
    if str(rights.get("schemaVersion") or "") != "1.0":
        raise BridgeError("asset-rights.json.schemaVersion deve ser 1.0.")
    entries = rights.get("assets")
    if not isinstance(entries, list):
        raise BridgeError("asset-rights.json.assets deve ser uma lista.")
    by_sha: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise BridgeError(f"asset-rights.json.assets[{index}] deve ser objeto.")
        sha = str(entry.get("sha256") or "").lower()
        if not SHA256_RE.fullmatch(sha) or sha in by_sha:
            raise BridgeError("asset-rights.json possui SHA-256 invalido ou duplicado.")
        relative = Path(str(entry.get("path") or ""))
        if not str(relative) or relative.is_absolute() or ".." in relative.parts:
            raise BridgeError("asset-rights.json.path deve ser relativo e permanecer no run.")
        resolved = (bundle.root / relative).resolve()
        if not _is_inside(resolved, bundle.root) or not resolved.is_file() or _sha256(resolved) != sha:
            raise BridgeError("asset-rights.json aponta para bytes ausentes ou com hash divergente.")
        license_name = str(entry.get("license") or "").strip()
        rights_holder = str(entry.get("rightsHolder") or "").strip()
        source_reference = str(entry.get("sourceReference") or "").strip()
        reviewed_by = str(entry.get("reviewedBy") or "").strip()
        reviewed_at = str(entry.get("reviewedAt") or "").strip()
        if (
            entry.get("approvedForImport") is not True
            or len(license_name) < 3
            or license_name.casefold() in {"unknown", "desconhecida", "none"}
            or len(rights_holder) < 2
            or len(source_reference) < 3
            or len(reviewed_by) < 2
            or "T" not in reviewed_at
        ):
            raise BridgeError("Cada asset precisa de licenca, titular, origem e revisao humana completas.")
        by_sha[sha] = {**entry, "resolvedPath": resolved}
    return by_sha


def _collect_asset_imports(bundle: Bundle) -> list[dict[str, Any]]:
    by_sha = _rights_entries(bundle)
    imports: list[dict[str, Any]] = []
    for scene_index, scene in enumerate(bundle.plan.get("scenes") or []):
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id") or f"cena-{scene_index + 1}")
        for asset_index, asset in enumerate(scene.get("assets") or []):
            if not isinstance(asset, dict):
                continue
            sha = str(asset.get("sha256") or "").lower()
            rights = by_sha.get(sha)
            if rights is None:
                raise BridgeError(f"Asset {scene_id}/{asset_index + 1} nao possui direitos aprovados por SHA-256.")
            source = _asset_path(bundle.root, asset.get("ref"))
            if source is None or source != rights["resolvedPath"]:
                raise BridgeError(f"Asset {scene_id}/{asset_index + 1} diverge do path aprovado.")
            imports.append(
                {
                    "takeId": f"{scene_index + 1:03d}",
                    "sourceSceneId": scene_id,
                    "assetIndex": asset_index + 1,
                    "kind": str(asset.get("kind") or "image"),
                    "role": str(asset.get("role") or ""),
                    "sha256": sha,
                    "sourcePath": source,
                    "license": str(rights.get("license") or ""),
                    "rightsHolder": str(rights.get("rightsHolder") or ""),
                    "sourceReference": str(rights.get("sourceReference") or ""),
                    "reviewedBy": str(rights.get("reviewedBy") or ""),
                    "reviewedAt": str(rights.get("reviewedAt") or ""),
                }
            )
    return imports


def _project_file_from_integrity(target: Path, relative_path: object) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        return None
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    candidate = (target / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(target)
    except ValueError:
        return None
    return candidate


def _write_import_integrity(staging: Path) -> None:
    files: dict[str, str] = {}
    for path in sorted(staging.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(staging).as_posix()
        if relative == IMPORT_INTEGRITY_RELATIVE_PATH:
            continue
        files[relative] = _sha256(path)
    required = {
        "project_manifest.json",
        "take_queue.json",
        "editorial/asset_catalog.json",
        "editorial/overlay_plan.json",
        "editorial/plan_qc.json",
        "qc/editorial_import/approved.json",
        "qc/editorial_import/authorization.json",
        "qc/editorial_import/editorial-review.manifest.json",
    }
    if not required.issubset(files):
        missing = ", ".join(sorted(required - set(files)))
        raise BridgeError(f"Import incompleto antes da promocao atomica: {missing}.")
    payload = {
        "schemaVersion": IMPORT_INTEGRITY_SCHEMA_VERSION,
        "bridgeVersion": BRIDGE_VERSION,
        "algorithm": "sha256",
        "files": files,
    }
    integrity_path = staging / Path(*PurePosixPath(IMPORT_INTEGRITY_RELATIVE_PATH).parts)
    _atomic_text_write(integrity_path, _canonical_pretty(payload))


def _verify_import_integrity(
    target: Path,
    *,
    expected_control_hashes: dict[str, str] | None = None,
) -> bool:
    integrity_path = target / Path(*PurePosixPath(IMPORT_INTEGRITY_RELATIVE_PATH).parts)
    try:
        payload = _read_json_object(integrity_path, "import-integrity.json", optional=True)
    except BridgeError:
        return False
    if not isinstance(payload, dict):
        return False
    if (
        payload.get("schemaVersion") != IMPORT_INTEGRITY_SCHEMA_VERSION
        or payload.get("bridgeVersion") != BRIDGE_VERSION
        or payload.get("algorithm") != "sha256"
    ):
        return False
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        return False
    required = {
        "project_manifest.json",
        "take_queue.json",
        "editorial/asset_catalog.json",
        "editorial/overlay_plan.json",
        "editorial/plan_qc.json",
        "qc/editorial_import/approved.json",
        "qc/editorial_import/authorization.json",
        "qc/editorial_import/editorial-review.manifest.json",
    }
    if not required.issubset(files):
        return False
    for relative, expected_sha in (expected_control_hashes or {}).items():
        if files.get(relative) != expected_sha:
            return False
    for relative, expected_sha in files.items():
        if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
            return False
        candidate = _project_file_from_integrity(target, relative)
        if candidate is None or not candidate.is_file():
            return False
        try:
            if _sha256(candidate) != expected_sha:
                return False
        except OSError:
            return False
    return True


def _existing_project_matches(
    target: Path,
    bundle: Bundle,
    review: ReviewPackage,
    approval_path: str | Path,
    authorization_path: str | Path,
) -> bool:
    try:
        manifest = _read_json_object(
            target / "project_manifest.json", "project_manifest.json", optional=True
        )
    except BridgeError:
        return False
    if not isinstance(manifest, dict):
        return False
    record = manifest.get("editorial_bridge")
    try:
        control_hashes = {
            "qc/editorial_import/editorial-review.manifest.json": _sha256(review.manifest_path),
            "qc/editorial_import/approved.json": _sha256(
                Path(approval_path).expanduser().resolve()
            ),
            "qc/editorial_import/authorization.json": _sha256(
                Path(authorization_path).expanduser().resolve()
            ),
        }
    except OSError:
        return False
    return bool(
        isinstance(record, dict)
        and record.get("source_artifacts") == bundle.artifact_hashes
        and record.get("review_manifest_sha256") == review.manifest_sha256
        and record.get("bridge_version") == BRIDGE_VERSION
        and _verify_import_integrity(target, expected_control_hashes=control_hashes)
    )


def _safe_cleanup_staging(staging: Path, projects_root: Path, project_id: str) -> None:
    resolved = staging.resolve()
    expected_prefix = f".{project_id}.import-"
    if resolved.parent != projects_root or not resolved.name.startswith(expected_prefix):
        raise BridgeError("Recusa de limpeza: staging saiu da raiz autorizada.")
    if resolved.exists():
        shutil.rmtree(resolved)


def apply_project(
    bundle: Bundle,
    review: ReviewPackage,
    approval_path: str | Path,
    authorization_path: str | Path,
    *,
    projects_root: str | Path,
    engine_root: str | Path | None = None,
    now: str | None = None,
) -> ApplyResult:
    """Atomically create a PLANNED Maestro project; never overwrite a project."""

    approval = validate_review_approval(approval_path, review, bundle)
    import_assets = bool(approval.get("importAssets", False))
    authorization = validate_source_authorization(authorization_path, import_assets=import_assets)
    imports = _collect_asset_imports(bundle) if import_assets else []
    root = Path(projects_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    copy_bytes = sum((bundle.root / name).stat().st_size for name in bundle.artifact_hashes)
    copy_bytes += sum(Path(item["sourcePath"]).stat().st_size for item in imports)
    free_bytes = shutil.disk_usage(root).free
    if free_bytes - copy_bytes < MIN_FREE_AFTER_IMPORT_BYTES:
        raise BridgeError(
            "Espaco livre insuficiente para importar e preservar a margem de seguranca."
        )
    target = (root / bundle.project_id).resolve()
    if target.parent != root or not PROJECT_ID_RE.fullmatch(target.name):
        raise BridgeError("Projeto candidato saiu da raiz autorizada.")
    if target.exists():
        if _existing_project_matches(
            target,
            bundle,
            review,
            approval_path,
            authorization_path,
        ):
            return ApplyResult(
                project_dir=target,
                created=False,
                project_id=bundle.project_id,
                take_count=int(bundle.metrics["sceneCount"]),
                asset_count=len(imports),
            )
        raise BridgeError(f"Projeto ja existe e nao corresponde ao mesmo import: {target}")

    engine = Path(engine_root).resolve() if engine_root is not None else _default_engine_root()
    imported_catalog: list[dict[str, Any]] = []
    staging = Path(tempfile.mkdtemp(prefix=f".{bundle.project_id}.import-", dir=root)).resolve()
    if staging.parent != root or not staging.name.startswith(f".{bundle.project_id}.import-"):
        raise BridgeError("Staging de importacao saiu da raiz autorizada.")
    try:
        for folder in (
            "input",
            "refs",
            "keyframes",
            "base_images",
            "takes",
            "edit",
            "qc",
            "audio",
            "output",
            "logs",
            "training_exports",
            "editorial",
        ):
            (staging / folder).mkdir()
        source_dir = staging / "input" / "editorial_source"
        source_dir.mkdir()
        for name, expected_sha in bundle.artifact_hashes.items():
            source = bundle.root / name
            destination = source_dir / name
            shutil.copy2(source, destination)
            if _sha256(destination) != expected_sha:
                raise BridgeError(f"Copia do artefato {name} falhou na verificacao SHA-256.")

        asset_dir = staging / "input" / "editorial_assets"
        asset_dir.mkdir()
        for item in imports:
            source = Path(item["sourcePath"])
            suffix = source.suffix.lower()
            safe_stem = _slugify(source.stem, fallback="asset")[:36]
            filename = f"take_{item['takeId']}_{item['assetIndex']:02d}_{safe_stem}{suffix}"
            staged_asset = asset_dir / filename
            final_asset = target / "input" / "editorial_assets" / filename
            shutil.copy2(source, staged_asset)
            if _sha256(staged_asset) != item["sha256"]:
                raise BridgeError(f"Asset {filename} falhou na verificacao SHA-256.")
            sidecar = {
                "schema_version": "1.0",
                "project_id": bundle.project_id,
                "type": "editorial_asset_candidate",
                "media_file": str(final_asset),
                "take_id": item["takeId"],
                "source_scene_id": item["sourceSceneId"],
                "kind": item["kind"],
                "role": item["role"],
                "sha256": item["sha256"],
                "license": item["license"],
                "rights_holder": item["rightsHolder"],
                "source_reference": item["sourceReference"],
                "rights_reviewed_by": item["reviewedBy"],
                "rights_reviewed_at": item["reviewedAt"],
                "validation_status": "pending_human_qc",
                "approval_required_before_video": True,
                "qc_checklist": [
                    "abrir e inspecionar o asset real",
                    "confirmar correspondencia com o briefing da cena",
                    "confirmar ausencia de texto falso, watermark e artefatos",
                    "promover para approved_for_video somente por acao humana no Maestro",
                ],
                "rejection_reasons": [],
                "imported_by": BRIDGE_VERSION,
            }
            if item["kind"] in IMAGE_ASSET_KINDS:
                sidecar["image_file"] = str(final_asset)
            else:
                sidecar["video_file"] = str(final_asset)
            _atomic_text_write(staged_asset.with_suffix(".json"), _canonical_pretty(sidecar))
            imported_catalog.append(
                {
                    "id": f"{bundle.project_id}-{item['takeId']}-{item['assetIndex']:02d}",
                    "takeId": item["takeId"],
                    "sourceSceneId": item["sourceSceneId"],
                    "kind": item["kind"],
                    "role": item["role"],
                    "file": str(final_asset),
                    "sidecar": str(final_asset.with_suffix(".json")),
                    "sha256": item["sha256"],
                    "license": item["license"],
                    "rightsHolder": item["rightsHolder"],
                    "sourceReference": item["sourceReference"],
                    "status": "pending_human_qc",
                    "reusable": False,
                }
            )

        manifest, queue, editorial = build_project_payloads(
            bundle,
            review,
            approval,
            authorization,
            engine_root=engine,
            now=now,
            imported_assets=imported_catalog,
        )
        by_take: dict[str, list[dict[str, Any]]] = {}
        for entry in imported_catalog:
            by_take.setdefault(str(entry["takeId"]), []).append(entry)
        for take in queue.get("takes") or []:
            if not isinstance(take, dict):
                continue
            take_assets = by_take.get(str(take.get("id") or ""), [])
            image_candidates = [
                entry for entry in take_assets if entry.get("kind") in IMAGE_ASSET_KINDS
            ]
            if image_candidates:
                take["base_image"]["candidate_assets"] = [
                    {
                        "file": entry["file"],
                        "sidecar": entry["sidecar"],
                        "sha256": entry["sha256"],
                        "status": "pending_human_qc",
                    }
                    for entry in image_candidates
                ]

        _atomic_text_write(staging / "project_manifest.json", _canonical_pretty(manifest))
        _atomic_text_write(staging / "take_queue.json", _canonical_pretty(queue))
        _atomic_text_write(staging / "editorial" / "factpack.json", _canonical_pretty(editorial["factpack"]))
        _atomic_text_write(staging / "editorial" / "cost.json", _canonical_pretty(editorial["cost"]))
        _atomic_text_write(
            staging / "editorial" / "overlay_plan.json", _canonical_pretty(editorial["overlay_plan"])
        )
        _atomic_text_write(
            staging / "editorial" / "asset_catalog.json", _canonical_pretty(editorial["asset_catalog"])
        )
        _atomic_text_write(staging / "editorial" / "plan_qc.json", _canonical_pretty(editorial["plan_qc"]))

        qc_dir = staging / "qc" / "editorial_import"
        qc_dir.mkdir(parents=True)
        shutil.copy2(review.manifest_path, qc_dir / review.manifest_path.name)
        shutil.copy2(review.markdown_path, qc_dir / review.markdown_path.name)
        shutil.copy2(Path(approval_path).resolve(), qc_dir / "approved.json")
        shutil.copy2(Path(authorization_path).resolve(), qc_dir / "authorization.json")
        _write_import_integrity(staging)
        os.replace(staging, target)
    except Exception:
        if staging.exists():
            _safe_cleanup_staging(staging, root, bundle.project_id)
        raise
    return ApplyResult(
        project_dir=target,
        created=True,
        project_id=bundle.project_id,
        take_count=len(queue.get("takes") or []),
        asset_count=len(imported_catalog),
    )


def _status_payload(
    bundle: Bundle,
    review: ReviewPackage,
    *,
    status: str,
    result: ApplyResult | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "projectId": bundle.project_id,
        "reviewManifest": str(review.manifest_path),
        "reviewMarkdown": str(review.markdown_path),
        "reviewManifestSha256": review.manifest_sha256,
        "blockingCodes": [issue.code for issue in bundle.blocking_issues],
        "riskCodes": [issue.code for issue in bundle.risk_issues],
        "sceneCount": bundle.metrics["sceneCount"],
        "durationSeconds": bundle.metrics["durationSeconds"],
        "gpuStarted": False,
        "audioMode": "VISUAL_ONLY",
    }
    if result is not None:
        payload.update(
            {
                "projectDir": str(result.project_dir),
                "created": result.created,
                "takeCount": result.take_count,
                "assetCount": result.asset_count,
            }
        )
    return payload


def _print_status(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(_canonical_pretty(payload), end="")
        return
    print(f"STATUS={payload['status']}")
    print(f"PROJECT_ID={payload['projectId']}")
    print(f"REVIEW_MANIFEST={payload['reviewManifest']}")
    print(f"REVIEW_MARKDOWN={payload['reviewMarkdown']}")
    print(f"REVIEW_SHA256={payload['reviewManifestSha256']}")
    blocking = payload.get("blockingCodes") or []
    risks = payload.get("riskCodes") or []
    print("BLOCKING_CODES=" + (",".join(blocking) if blocking else "NONE"))
    print("RISK_CODES=" + (",".join(risks) if risks else "NONE"))
    print(f"SCENES={payload['sceneCount']}")
    print(f"DURATION_SECONDS={payload['durationSeconds']}")
    print("GPU_STARTED=NO")
    print("AUDIO_MODE=VISUAL_ONLY")
    if "projectDir" in payload:
        print(f"PROJECT_DIR={payload['projectDir']}")
        print("PROJECT_CREATED=" + ("YES" if payload.get("created") else "NO_ALREADY_IDENTICAL"))
        print(f"TAKES={payload['takeCount']}")
        print(f"ASSETS_IMPORTED={payload['assetCount']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Valida um run editorial do Unimedia, emite review humano por SHA-256 e, "
            "com autorizacao explicita, cria um projeto PLANNED no Maestro sem iniciar GPU."
        )
    )
    parser.add_argument("source", type=Path, help="Diretorio do run com plan.json e manifest.json.")
    parser.add_argument(
        "--review-dir",
        required=True,
        type=Path,
        help="Diretorio isolado para o pacote de revisao.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Cria o projeto apos validar approved.json e authorization.json.",
    )
    parser.add_argument(
        "--approval",
        type=Path,
        help="Padrao com --apply: <review-dir>/approved.json.",
    )
    parser.add_argument(
        "--authorization",
        type=Path,
        help="Padrao com --apply: <review-dir>/authorization.json.",
    )
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=_default_engine_root() / "projetos",
        help="Raiz canonica de projetos do Maestro.",
    )
    parser.add_argument(
        "--engine-root",
        type=Path,
        default=_default_engine_root(),
        help="Raiz do video_global_engine usada para validar politicas e templates.",
    )
    parser.add_argument("--json", action="store_true", help="Emite o status como JSON.")
    args = parser.parse_args(argv)

    try:
        bundle = load_bundle(args.source)
        review = write_review_package(bundle, args.review_dir)
        if bundle.blocking_issues:
            _print_status(
                _status_payload(bundle, review, status="BLOCKED"),
                as_json=args.json,
            )
            return 2
        if not args.apply:
            _print_status(
                _status_payload(bundle, review, status="AWAITING_HUMAN_REVIEW"),
                as_json=args.json,
            )
            return 0
        approval_path = args.approval or (Path(args.review_dir) / "approved.json")
        authorization_path = args.authorization or (Path(args.review_dir) / "authorization.json")
        result = apply_project(
            bundle,
            review,
            approval_path,
            authorization_path,
            projects_root=args.projects_root,
            engine_root=args.engine_root,
        )
        status = "PROJECT_CREATED" if result.created else "PROJECT_ALREADY_IDENTICAL"
        _print_status(
            _status_payload(bundle, review, status=status, result=result),
            as_json=args.json,
        )
        return 0
    except BridgeError as exc:
        if args.json:
            print(_canonical_pretty({"status": "ERROR", "error": str(exc)}), end="", file=sys.stderr)
        else:
            print("STATUS=ERROR", file=sys.stderr)
            print(f"ERROR={exc}", file=sys.stderr)
            print("GPU_STARTED=NO", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
