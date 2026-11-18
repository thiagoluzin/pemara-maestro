"""Controlled three-take video Gauntlet Loop pilot for Maestro.

The module deliberately does not generate media and never changes a take's
approval state.  It creates a small, inspectable pilot, prepares an isolated
critic brief for OpenCode, and stores the critic's evidence plus a bounded
recommendation.  The existing Maestro human-review gate remains authoritative.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PILOT_SCHEMA = "maestro_video_gauntlet_v1"
PILOT_TAKE_IDS = ("01", "02", "03")
STATE_FILE = Path("qc") / "gauntlet_loop.json"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
REFERENCE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VALID_SUGGESTED_VERDICTS = {
    "APPROVE_RECOMMENDED",
    "REGENERATE_RECOMMENDED",
    "BLOCKED",
}
CRITERIA = {
    "characterConsistency": {
        "label": "Consistência de personagens",
        "minimumApprovalScore": 4,
        "description": "Identidade, roupa, proporção, elenco e objetos vinculados permanecem estáveis.",
    },
    "composition": {
        "label": "Composição",
        "minimumApprovalScore": 4,
        "description": "Enquadramento, geografia e legibilidade da ação correspondem à referência e ao objetivo.",
    },
    "cameraMotion": {
        "label": "Câmera e movimento",
        "minimumApprovalScore": 4,
        "description": "Há movimento físico coerente, sem loop, reset, congelamento ou zoom artificial.",
    },
    "noGeneratedText": {
        "label": "Ausência de texto gerado",
        "minimumApprovalScore": 5,
        "description": "Não há texto, legenda, logo, watermark ou interface gerados em nenhum quadro inspecionado.",
    },
    "crossTakeContinuity": {
        "label": "Continuidade entre takes",
        "minimumApprovalScore": 4,
        "description": "Paleta, direção, estado final e transição combinam com os takes vizinhos disponíveis.",
    },
}

# A Gauntlet project starts with no user-supplied keyframe. Its first anchor
# must therefore be a text-to-image request, never an image-edit job with an
# empty source path. The frames share the same visual world so the first human-
# approved anchor can inform continuity decisions for the remaining takes.
PILOT_ANCHOR_PROMPTS = {
    "01": (
        "Original cinematic 16:9 animated anchor frame for a three-shot proof of concept. "
        "A quiet modern creative studio at blue hour, an empty central worktable with one "
        "small matte-white geometric artifact, deep indigo walls, warm amber practical light, "
        "clean 2D digital-painting linework, clear foreground middle-ground and background, "
        "wide establishing composition, stable geometry, full-bleed edge-to-edge image. "
        "No people or characters, no numbers, letters, crop marks, camera overlay or interface."
    ),
    "02": (
        "Original cinematic 16:9 animated anchor frame in the exact same modern creative studio "
        "from take 01: deep indigo walls, warm amber practical light, empty central worktable "
        "and one small matte-white geometric artifact. Use a closer three-quarter camera angle; "
        "the artifact emits a subtle soft glow while the room identity, architecture, palette and "
        "2D digital-painting linework remain stable. Clear foreground middle-ground and background, "
        "full-bleed edge-to-edge image. No people or characters, no numbers, letters, crop marks, "
        "camera overlay or interface."
    ),
    "03": (
        "Original cinematic 16:9 animated anchor frame in the exact same modern creative studio "
        "from takes 01 and 02: deep indigo walls, warm amber practical light, empty central "
        "worktable and one small matte-white geometric artifact. Use a calm resolved composition; "
        "the artifact glow has settled and a subtle reflected light defines the final stable pose. "
        "Preserve the same architecture, palette and 2D digital-painting linework, with clear "
        "foreground middle-ground and background, full-bleed edge-to-edge image. No people or characters, "
        "no numbers, letters, crop marks, camera overlay, interface, split screen, diptych, panel, collage "
        "or duplicated scene. Render one single continuous full-frame composition."
    ),
}
PILOT_ANCHOR_NEGATIVE = (
    "readable text, subtitles, logo, watermark, UI, HUD, number, digit, letter, caption, timecode, "
    "camera overlay, crop mark, split screen, diptych, panel, collage, duplicate scene, tiled image, "
    "picture frame, border, letterbox, "
    "people, characters, faces, silhouettes, animals, duplicate artifact, extra objects, "
    "photorealism, 3D render, blurry image, distorted geometry"
)

# The pilot declares one explicit LTX 2.5 profile. It remains blocked by the
# normal owner render gate and never falls back to H3 or another engine.
PILOT_VIDEO_GENERATION = {
    "profile": "ltx25_two_stage_distilled_960x544p24",
    "width": 960,
    "height": 544,
    "fps": 24,
    "frames": 97,
    "steps": 8,
    "guidance": 1.0,
    "camera_speed": 0.7,
    "video_conditioning_profile": "identity_locked",
}

PILOT_TAKE_DIRECTION = {
    "01": {
        "duration": 4,
        "camera_pose": "Pan Left",
        "animation_prompt": (
            "Animate this approved keyframe as a real four-second cinematic video, never a living photo. "
            "Preserve the exact blue-hour studio, the empty worktable and one matte-white artifact; add no people, "
            "characters, objects, text, logos or interface. Camera physically tracks left through the existing "
            "foreground table edge, producing real occlusion and different motion in foreground, artifact and rear wall; "
            "do not use a pan or digital zoom. Beginning: the artifact is matte and still. Middle: its existing core emits "
            "one soft cobalt pulse while the warm tabletop reflection shifts independently. End: the pulse settles into a "
            "small stable glow and the camera reaches a new angle. Cut on the settled reflection; no loop, reset or static tail."
        ),
        "shot_contract": {
            "subject": "one existing matte-white geometric artifact on the empty worktable",
            "action": "a single cobalt pulse changes the artifact from matte to a settled low glow",
            "scene": "the approved blue-hour creative studio, unchanged in identity and geometry",
            "camera": {
                "movement": "physical leftward track through the foreground table edge, with real parallax",
                "angle": "wide establishing three-quarter view",
                "lens": "natural cinematic wide lens",
                "focus": "artifact and tabletop reflection",
            },
            "lighting": "deep indigo ambience with warm practical reflection responding once",
            "mood": "quiet discovery",
            "motion_beats": {
                "start": "matte artifact in the established room",
                "middle": "one cobalt pulse and a moving warm reflection",
                "end": "settled low glow from a newly revealed camera angle",
            },
            "visual_references": {"end_frame_note": "keep the same room and one artifact; only the glow state changes"},
            "story_purpose": "establish the room and reveal that the artifact is active",
            "dramatic_question": "what changed inside the apparently inert artifact?",
            "story_change": "the artifact changes from matte to visibly but calmly activated",
            "reaction": "the tabletop reflection responds to the pulse",
            "cut_motivation": "cut when the reflection settles at the new camera angle",
            "duration_reason": "four seconds are needed to read the room, pulse and settled response once",
            "distinct_story_events": 2,
        },
        "motion_layers": {
            "camera": "physical leftward translation, never a pan-only move",
            "environment": "foreground table edge occludes the artifact while the rear wall shifts more slowly",
            "particles": "none",
            "objects": "one internal artifact pulse only",
            "lighting": "one warm reflection travels across the existing tabletop",
        },
    },
    "02": {
        "duration": 4,
        "camera_pose": "Pan Right",
        "animation_prompt": (
            "Animate this approved keyframe as a real four-second cinematic video, never a living photo. Preserve the exact "
            "studio, empty worktable and one matte-white artifact from take 01; add no people, characters, extra objects, "
            "text, logos or interface. Camera physically slides right around the existing foreground table corner, with real "
            "depth and different motion in the corner, artifact and indigo wall; do not use a pan or digital zoom. Beginning: "
            "the low artifact glow is stable. Middle: the existing glow gathers once and releases a gentle blue light wave across "
            "the tabletop while the warm practical reflection answers from the opposite side. End: both reflections settle in a "
            "new three-quarter composition. Cut as the two light responses meet; no loop, reset or static tail."
        ),
        "shot_contract": {
            "subject": "the same single matte-white artifact and its existing tabletop reflections",
            "action": "the settled glow gathers once, sends one gentle light wave across the table and receives a warm reflection",
            "scene": "the same approved indigo studio at blue hour",
            "camera": {
                "movement": "physical rightward slide around the foreground worktable corner with real parallax",
                "angle": "closer three-quarter view",
                "lens": "natural cinematic medium-wide lens",
                "focus": "artifact, moving blue reflection and warm answer",
            },
            "lighting": "indigo ambience, one controlled blue wave and one warm practical response",
            "mood": "a measured escalation",
            "motion_beats": {
                "start": "the take 01 low glow is stable",
                "middle": "a single blue wave travels across the tabletop",
                "end": "blue and warm reflections meet and settle at the new angle",
            },
            "visual_references": {"end_frame_note": "preserve the studio and one artifact with stronger but controlled reflection"},
            "story_purpose": "turn the discovery into a visible exchange inside the room",
            "dramatic_question": "will the room answer the artifact's signal?",
            "story_change": "a lone glow becomes a completed blue-and-warm reflection exchange",
            "reaction": "the warm practical reflection answers the blue wave",
            "cut_motivation": "cut when the two responses meet in one readable composition",
            "duration_reason": "four seconds are needed to establish the stable glow, complete one wave and read the answer",
            "distinct_story_events": 2,
        },
        "motion_layers": {
            "camera": "physical rightward translation around the foreground table corner",
            "environment": "foreground corner, table surface and distant indigo wall shift at distinct speeds",
            "particles": "none",
            "objects": "one existing artifact gathers and releases one light wave",
            "lighting": "blue wave and warm practical reflection move independently once",
        },
    },
    "03": {
        "duration": 4,
        "camera_pose": "Zoom Out",
        "animation_prompt": (
            "Animate this approved keyframe as a real four-second cinematic video, never a living photo. Preserve the exact "
            "blue-hour studio, empty worktable and one matte-white artifact from takes 01 and 02; add no people, characters, "
            "extra objects, text, logos or interface. Camera physically retreats and rises slightly behind the existing foreground "
            "table edge, creating real occlusion and different motion in foreground, artifact and background; do not use a digital "
            "zoom. Beginning: the reflections from take 02 are calm. Middle: the artifact brightens once, then the blue reflection "
            "contracts into a stable final pool of light as the warm practical returns to normal. End: the room is visibly settled in "
            "a new resolved composition. Cut exactly on that stable changed state; no loop, reset or static tail."
        ),
        "shot_contract": {
            "subject": "the same single artifact resolving the studio's completed light exchange",
            "action": "one final brightening contracts into a stable pool of blue light while warm practical light normalizes",
            "scene": "the same approved studio, now in its resolved state",
            "camera": {
                "movement": "physical backward and slightly upward translation behind the foreground table edge with real parallax",
                "angle": "calm resolving wide three-quarter view",
                "lens": "natural cinematic wide lens",
                "focus": "artifact and the shrinking reflection pool",
            },
            "lighting": "one final blue contraction followed by restored warm practical balance",
            "mood": "calm resolution",
            "motion_beats": {
                "start": "the take 02 reflection exchange is calm",
                "middle": "one final brightening and contraction",
                "end": "a stable blue pool and normalized warm practical complete the room's new state",
            },
            "visual_references": {"end_frame_note": "the same room and one artifact remain, now in a clearly resolved light state"},
            "story_purpose": "show the consequence and give the edit a stable final state",
            "dramatic_question": "does the signal resolve without changing the room's identity?",
            "story_change": "moving reflections resolve into one stable final pool of light",
            "reaction": "the warm practical light returns to its normal balance",
            "cut_motivation": "the stable resolved pool is the final-cut image",
            "duration_reason": "four seconds are needed to read the final brightening, contraction and completed calm state",
            "distinct_story_events": 2,
        },
        "motion_layers": {
            "camera": "physical backward and slightly upward translation through foreground occlusion",
            "environment": "foreground table edge, artifact and distant wall separate through real depth",
            "particles": "none",
            "objects": "one existing artifact brightens and settles once",
            "lighting": "blue reflection contracts while the warm practical independently returns to normal",
        },
    },
}

_STATE_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} deve conter um objeto JSON.")
    return payload


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _atomic_text_write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _validate_project_id(project_id: str) -> str:
    value = str(project_id or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,79}", value):
        raise ValueError("projectId deve ter 3 a 80 caracteres minúsculos, números, hífen ou sublinhado.")
    return value


def _validate_take_id(take_id: str) -> str:
    value = str(take_id or "").strip()
    if value not in PILOT_TAKE_IDS:
        raise ValueError("O piloto Gauntlet aceita somente os takes 01, 02 e 03.")
    return value


def _project_dir(root: Path, project_id: str) -> Path:
    root = Path(root).resolve()
    project = (root / _validate_project_id(project_id)).resolve()
    if project.parent != root:
        raise ValueError("projectId inválido.")
    return project


def _queue_path(project_dir: Path) -> Path:
    manifest = _read_json(project_dir / "project_manifest.json")
    filename = str(manifest.get("take_queue") or "take_queue.json").strip()
    candidate = (project_dir / filename).resolve()
    if candidate.parent != project_dir.resolve() or candidate.suffix.lower() != ".json":
        raise ValueError("A fila do projeto Gauntlet é inválida.")
    return candidate


def _load_queue(project_dir: Path) -> dict[str, Any]:
    queue = _read_json(_queue_path(project_dir))
    if not isinstance(queue.get("takes"), list):
        raise ValueError("A fila do projeto possui takes inválidos.")
    return queue


def _state_path(project_dir: Path) -> Path:
    return project_dir / STATE_FILE


def _load_state(project_dir: Path) -> dict[str, Any]:
    path = _state_path(project_dir)
    if not path.is_file():
        raise FileNotFoundError("gauntlet_loop")
    state = _read_json(path)
    if state.get("schemaVersion") != PILOT_SCHEMA:
        raise ValueError("O arquivo de estado Gauntlet possui versão incompatível.")
    takes = state.get("takes")
    if not isinstance(takes, dict) or set(takes) != set(PILOT_TAKE_IDS):
        raise ValueError("O estado Gauntlet deve conter exatamente os takes 01, 02 e 03.")
    return state


def _find_take(queue: dict[str, Any], take_id: str) -> dict[str, Any]:
    take_id = _validate_take_id(take_id)
    take = next(
        (
            item
            for item in queue["takes"]
            if isinstance(item, dict) and str(item.get("id") or "").strip() == take_id
        ),
        None,
    )
    if take is None:
        raise ValueError(f"A fila não contém o take obrigatório {take_id}.")
    return take


def _safe_existing_file(project_dir: Path, raw_path: str, extensions: set[str]) -> Path:
    path = Path(str(raw_path or "").strip())
    if not path or not str(path):
        raise FileNotFoundError("arquivo")
    candidate = path.resolve() if path.is_absolute() else (project_dir / path).resolve()
    if (
        not candidate.is_relative_to(project_dir.resolve())
        or not candidate.is_file()
        or candidate.suffix.lower() not in extensions
    ):
        raise FileNotFoundError("arquivo")
    return candidate


def _reference_path(project_dir: Path, state: dict[str, Any], take_id: str) -> Path:
    registered = str(state["takes"][take_id].get("referenceFile") or "").strip()
    if not registered:
        raise FileNotFoundError("reference_image")
    candidate = _safe_existing_file(project_dir, registered, REFERENCE_EXTENSIONS)
    refs_dir = (project_dir / "refs").resolve()
    if not candidate.is_relative_to(refs_dir):
        raise FileNotFoundError("reference_image")
    return candidate


def _candidate_path(project_dir: Path, queue: dict[str, Any], take_id: str) -> Path:
    take = _find_take(queue, take_id)
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    for field in (
        "output_active",
        "output_final",
        "output_upscaled",
        "output_review_candidate",
        "output_preview",
    ):
        raw = str(video.get(field) or "").strip()
        if not raw:
            continue
        try:
            return _safe_existing_file(project_dir, raw, VIDEO_EXTENSIONS)
        except FileNotFoundError:
            continue
    raise FileNotFoundError("candidate_video")


def _file_identity(project_dir: Path, path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    return {
        "relativePath": path.resolve().relative_to(project_dir.resolve()).as_posix(),
        "sha256": digest.hexdigest(),
        "bytes": stat.st_size,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def _score_average(scores: dict[str, int]) -> float:
    return round(sum(scores.values()) / len(CRITERIA), 2)


def _normalize_scores(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(CRITERIA):
        expected = ", ".join(CRITERIA)
        raise ValueError(f"scores deve conter exatamente: {expected}.")
    normalized: dict[str, int] = {}
    for key in CRITERIA:
        raw = value[key]
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 5:
            raise ValueError(f"scores.{key} deve ser um inteiro entre 0 e 5.")
        normalized[key] = raw
    return normalized


def _short_text(value: Any, field: str, minimum: int, maximum: int) -> str:
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum:
        raise ValueError(f"{field} deve ter entre {minimum} e {maximum} caracteres.")
    return text


def _review_for_candidate(state: dict[str, Any], take_id: str, candidate_sha256: str) -> dict[str, Any] | None:
    reviews = state["takes"][take_id].get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("A lista de revisões Gauntlet é inválida.")
    return next(
        (
            item
            for item in reviews
            if isinstance(item, dict) and str(item.get("candidateSha256") or "") == candidate_sha256
        ),
        None,
    )


def _previous_score(state: dict[str, Any], take_id: str) -> float | None:
    reviews = state["takes"][take_id].get("reviews")
    if not isinstance(reviews, list) or not reviews:
        return None
    previous = reviews[-1]
    if not isinstance(previous, dict):
        return None
    try:
        return float(previous.get("averageScore"))
    except (TypeError, ValueError):
        return None


def _candidate_version(state: dict[str, Any], take_id: str, candidate_sha256: str) -> int:
    reviews = state["takes"][take_id].get("reviews")
    seen: list[str] = []
    if isinstance(reviews, list):
        for review in reviews:
            if isinstance(review, dict):
                digest = str(review.get("candidateSha256") or "")
                if digest and digest not in seen:
                    seen.append(digest)
    if candidate_sha256 not in seen:
        seen.append(candidate_sha256)
    return len(seen)


def _recommendation(
    state: dict[str, Any],
    take_id: str,
    candidate_sha256: str,
    scores: dict[str, int],
    suggested_verdict: str,
    previous_average: float | None,
) -> tuple[str, str, float | None]:
    average = _score_average(scores)
    improvement = (
        round(average - previous_average, 2) if previous_average is not None else None
    )
    if suggested_verdict == "BLOCKED":
        return "BLOCKED_NEEDS_HUMAN", "O crítico não conseguiu concluir uma inspeção verificável.", improvement
    if scores["noGeneratedText"] < CRITERIA["noGeneratedText"]["minimumApprovalScore"]:
        return "REGENERATE_RECOMMENDED", "Texto, logo, watermark ou interface gerados são bloqueadores.", improvement
    scores_pass = all(
        scores[key] >= int(rule["minimumApprovalScore"])
        for key, rule in CRITERIA.items()
    )
    if scores_pass and suggested_verdict == "APPROVE_RECOMMENDED":
        return "APPROVE_RECOMMENDED", "Todos os critérios atingiram o limiar; aguarda decisão humana.", improvement
    version = _candidate_version(state, take_id, candidate_sha256)
    max_regenerations = int(state["policy"]["maxRegenerations"])
    if version - 1 >= max_regenerations:
        return "STOP_MAX_REGENERATIONS", "O limite de regenerações do piloto foi atingido; aguarda direção humana.", improvement
    threshold = float(state["policy"]["marginalImprovementThreshold"])
    if improvement is not None and improvement < threshold:
        return "STOP_MARGINAL_IMPROVEMENT", "A melhoria ficou abaixo do limiar; aguarda direção humana.", improvement
    return "REGENERATE_RECOMMENDED", "Há uma lacuna objetiva acima do limiar de qualidade.", improvement


def _pilot_readme(project_id: str) -> str:
    return f"""# Piloto Gauntlet de vídeo — {project_id}

Este projeto testa o ciclo controlado de três takes curtos. Não há aprovação
automática e o Maestro continua sendo a fonte de verdade da fila.

1. Coloque uma referência visual aprovada por take em `refs/`, por exemplo
   `refs/take_01_reference.png`.
2. Registre a referência pelo endpoint `.../gauntlet/reference`.
3. Gere um candidato normalmente pelo Maestro, sem sobrescrever uma versão boa.
4. Obtenha o briefing em `.../gauntlet/brief` e envie-o a um contexto novo do
   agente `critico-video-gauntlet` no OpenCode.
5. O crítico registra uma recomendação; a decisão de aprovar ou regerar continua
   humana no Maestro.

O piloto aceita somente os takes 01, 02 e 03, cada um com até duas regenerações.
"""


def _pilot_anchor_policy() -> dict[str, Any]:
    return {
        "version": "anchor_generation_policy_v1",
        "status": "gauntlet_controlled_pilot",
        "provider": "maestro_local_executor",
        "human_review_required": True,
        "require_explicit_human_confirmation": True,
        "pilot_first": False,
        "pilot_takes": ["01"],
        "remaining_batch_requires_pilot_human_approval": False,
        "configured_at": _utc_now(),
    }


def _pilot_anchor_base(take_id: str) -> dict[str, Any]:
    take_id = _validate_take_id(take_id)
    return {
        "status": "anchor_generation_required",
        "reference_file": "",
        "generation_mode": "text_to_image",
        "prompt": PILOT_ANCHOR_PROMPTS[take_id],
        "negative_prompt": PILOT_ANCHOR_NEGATIVE,
    }


def _apply_pilot_video_contract(take: dict[str, Any], take_id: str) -> bool:
    """Make an unrendered Gauntlet take executable by the authorized LTX route."""

    take_id = _validate_take_id(take_id)
    direction = deepcopy(PILOT_TAKE_DIRECTION[take_id])
    generation = deepcopy(PILOT_VIDEO_GENERATION)
    generation["camera_pose"] = direction.pop("camera_pose")
    desired = {
        "target_duration_seconds": direction.pop("duration"),
        "animation_prompt": direction.pop("animation_prompt"),
        "video_generation": generation,
        "shot_contract": direction.pop("shot_contract"),
        "motion_layers": direction.pop("motion_layers"),
    }
    changed = any(take.get(key) != value for key, value in desired.items())
    if changed:
        take.update(desired)
    return changed


def create_pilot(
    root: Path,
    *,
    project_id: str = "gauntlet_pilot_3_takes",
    name: str = "Piloto Gauntlet — 3 takes",
    objective: str = "Validar um ciclo controlado de geração, crítica independente e revisão humana para três takes curtos.",
) -> dict[str, Any]:
    """Create an empty, bounded pilot without starting video generation."""

    project_id = _validate_project_id(project_id)
    name = _short_text(name, "name", 3, 120)
    objective = _short_text(objective, "objective", 20, 2000)
    project_dir = _project_dir(root, project_id)
    with _STATE_LOCK:
        if project_dir.exists():
            raise FileExistsError(project_id)
        project_dir.mkdir(parents=True)
        for directory in ("input", "refs", "keyframes", "takes", "edit", "qc", "audio", "output", "logs"):
            (project_dir / directory).mkdir()
        now = _utc_now()
        manifest = {
            "schema_version": "1.1",
            "project_id": project_id,
            "title": name,
            "objective": objective,
            "duration_target_seconds": 12,
            "preview_resolution": "1280x720",
            "final_resolution": "1920x1080",
            "fps_preview": 24,
            "fps_final": 60,
            "created_at": now,
            "updated_at": now,
            "maestro_status": "PLANNED",
            "audio": {"music_provider": None, "voice_provider": None},
            "take_queue": "take_queue.json",
        }
        takes = []
        for take_id, role, take_objective in (
            ("01", "opening", "Estabelecer o espaço, o sujeito e a composição-base."),
            ("02", "action", "Executar a ação principal preservando a continuidade do take 01."),
            ("03", "resolution", "Mostrar a consequência e uma pose final estável para o corte."),
        ):
            takes.append(
                {
                    "id": take_id,
                    "slug": f"gauntlet_{role}",
                    "sequence": int(take_id),
                    "target_duration_seconds": 8,
                    "role": role,
                    "objective": take_objective,
                    "base_image": _pilot_anchor_base(take_id),
                    "animation_prompt": "Piloto Gauntlet: definir direção visual aprovada antes da geração.",
                    "video": {"status": "planned", "upscale_allowed": False},
                    "qc": {
                        "status": "gauntlet_waiting_anchor_generation",
                        "required": [rule["label"] for rule in CRITERIA.values()],
                    },
                    "maestro_status": "PLANNED",
                    "maestro_notes": "Piloto criado; requer referência aprovada, geração normal e crítica independente.",
                }
            )
            _apply_pilot_video_contract(takes[-1], take_id)
        queue = {
            "schema_version": "1.1",
            "project_id": project_id,
            "methodology": "maestro_video_gauntlet_pilot",
            "status": "ready",
            "assembly": {
                "preview": {"width": 1280, "height": 720, "fps": 24, "format": "mp4"},
                "final": {"width": 1920, "height": 1080, "fps": 60, "format": "mp4"},
                "rule": "never_render_full_movie_as_one_prompt",
            },
            "global_negative_rules": [
                "no generated text, subtitle, logo, watermark or UI",
                "no loop, reset, frozen tail or simple zoom",
                "do not upscale before human approval",
            ],
            "anchor_generation_policy": _pilot_anchor_policy(),
            "takes": takes,
        }
        state = {
            "schemaVersion": PILOT_SCHEMA,
            "projectId": project_id,
            "createdAt": now,
            "updatedAt": now,
            "policy": {
                "maxRegenerations": 2,
                "marginalImprovementThreshold": 0.25,
                "humanApprovalRequired": True,
                "automaticGeneration": False,
            },
            "takes": {
                take_id: {"referenceFile": "", "reviews": []}
                for take_id in PILOT_TAKE_IDS
            },
        }
        _atomic_json_write(project_dir / "project_manifest.json", manifest)
        _atomic_json_write(project_dir / "take_queue.json", queue)
        _atomic_json_write(_state_path(project_dir), state)
        _atomic_text_write(project_dir / "README_GAUNTLET_PILOT.md", _pilot_readme(project_id))
    return get_pilot(root, project_id)


def _restore_unconfirmed_gauntlet_anchor(project_dir: Path, take: dict[str, Any]) -> bool:
    """Return a legacy auto-approved anchor to pending human review.

    A prior Studio build did not record an explicit confirmation bit for the
    Gauntlet's required human approval. A candidate carrying an approval
    without that bit is intentionally preserved but cannot unlock video work.
    """

    base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
    if str(base.get("status") or "").strip().lower() != "approved_for_video":
        return False
    raw_metadata = str(base.get("metadata") or "").strip()
    if not raw_metadata:
        return False
    metadata_path = Path(raw_metadata).resolve()
    if (
        not metadata_path.is_file()
        or not metadata_path.is_relative_to(project_dir.resolve())
        or metadata_path.suffix.lower() != ".json"
    ):
        return False
    sidecar = _read_json(metadata_path)
    human_review = sidecar.get("human_review") if isinstance(sidecar.get("human_review"), dict) else {}
    if bool(human_review.get("explicit_human_confirmation", False)):
        return False

    request_id = str(base.get("candidate_request_id") or "").strip().lower()
    requests = take.get("maestro_director_requests")
    request = next(
        (
            item for item in requests
            if isinstance(item, dict) and str(item.get("id") or "").strip().lower() == request_id
        ),
        None,
    ) if isinstance(requests, list) else None
    if request is None or str(request.get("status") or "").upper() != "DELIVERED":
        return False

    sidecar["validation_status"] = "pending_human_qc"
    for field in ("reviewed_at", "human_review", "approval_evidence", "visual_qc"):
        sidecar.pop(field, None)
    base["status"] = "pending_human_qc"
    base.pop("approved_at", None)
    for field in ("review_decision", "review_reason", "reviewed_at"):
        request.pop(field, None)
    qc = take.get("qc") if isinstance(take.get("qc"), dict) else {}
    qc["status"] = "anchor_delivered_pending_user_approval"
    qc.pop("human_visibility_gate", None)
    take["qc"] = qc
    _atomic_json_write(metadata_path, sidecar)
    return True


def repair_pilot_anchor_contract(root: Path, project_id: str) -> dict[str, Any]:
    """Repair legacy Gauntlet queues that incorrectly requested image editing.

    Earlier pilot folders stored an empty ``reference_required`` base image.
    The normal Maestro anchor executor interprets that as image editing and
    fails before submitting a generation job. This migration is deliberately
    narrow: it only changes takes that have neither a delivered candidate nor
    an approved source image, and it never approves an image or video.
    """

    project_dir = _project_dir(root, project_id)
    repaired_take_ids: list[str] = []
    restored_unconfirmed_approval_take_ids: list[str] = []
    with _STATE_LOCK:
        _load_state(project_dir)
        queue_path = _queue_path(project_dir)
        queue = _load_queue(project_dir)
        existing_policy = queue.get("anchor_generation_policy")
        policy = existing_policy if isinstance(existing_policy, dict) else {}
        policy.update({
            "version": "anchor_generation_policy_v1",
            "status": "gauntlet_controlled_pilot",
            "provider": str(policy.get("provider") or "maestro_local_executor"),
            "human_review_required": True,
            "require_explicit_human_confirmation": True,
            "pilot_first": False,
            "pilot_takes": ["01"],
            "remaining_batch_requires_pilot_human_approval": False,
            "configured_at": str(policy.get("configured_at") or _utc_now()),
        })
        policy.pop("require_human_approval_phrase", None)
        queue["anchor_generation_policy"] = policy

        for take_id in PILOT_TAKE_IDS:
            take = _find_take(queue, take_id)
            if _restore_unconfirmed_gauntlet_anchor(project_dir, take):
                restored_unconfirmed_approval_take_ids.append(take_id)
            base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
            has_candidate = any(
                str(base.get(field) or "").strip()
                for field in ("file", "metadata", "candidate_request_id")
            )
            has_source = str(base.get("source_approved_image") or "").strip()
            if has_candidate or has_source:
                continue
            base.update(_pilot_anchor_base(take_id))
            take["base_image"] = base
            qc = take.get("qc") if isinstance(take.get("qc"), dict) else {}
            qc["status"] = "gauntlet_waiting_anchor_generation"
            take["qc"] = qc
            repaired_take_ids.append(take_id)

        queue["updated_at"] = _utc_now()
        _atomic_json_write(queue_path, queue)

    view = get_pilot(root, project_id)
    view["anchorContractRepair"] = {
        "repairedTakeIds": repaired_take_ids,
        "restoredUnconfirmedApprovalTakeIds": restored_unconfirmed_approval_take_ids,
        "generationMode": "text_to_image",
        "pilotTakeIds": ["01"],
        "humanApprovalRequiredBeforeRemainingTakes": True,
    }
    return view


def repair_pilot_video_contract(root: Path, project_id: str) -> dict[str, Any]:
    """Move only unrendered Gauntlet takes to the authorized LTX contract.

    The migration deliberately leaves references, approvals, completed renders
    and non-planned takes intact.  It does not enqueue a video job.
    """

    project_dir = _project_dir(root, project_id)
    repaired_take_ids: list[str] = []
    with _STATE_LOCK:
        _load_state(project_dir)
        queue_path = _queue_path(project_dir)
        queue = _load_queue(project_dir)
        for take_id in PILOT_TAKE_IDS:
            take = _find_take(queue, take_id)
            video = take.get("video") if isinstance(take.get("video"), dict) else {}
            status = str(
                take.get("maestro_status") or video.get("status") or "PLANNED"
            ).upper()
            has_render = any(
                str(video.get(field) or "").strip()
                for field in ("output_active", "output_final", "preview", "file")
            )
            if status not in {"", "PLANNED"} or has_render:
                continue
            if _apply_pilot_video_contract(take, take_id):
                repaired_take_ids.append(take_id)
        if repaired_take_ids:
            queue["updated_at"] = _utc_now()
            _atomic_json_write(queue_path, queue)

    view = get_pilot(root, project_id)
    view["videoContractRepair"] = {
        "repairedTakeIds": repaired_take_ids,
        "generationProfile": PILOT_VIDEO_GENERATION["profile"],
        "renderStarted": False,
    }
    return view


def get_pilot(root: Path, project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(root, project_id)
    with _STATE_LOCK:
        state = _load_state(project_dir)
        queue = _load_queue(project_dir)
        take_views = []
        for take_id in PILOT_TAKE_IDS:
            record = state["takes"][take_id]
            reviews = record.get("reviews") if isinstance(record.get("reviews"), list) else []
            reference_ready = False
            candidate_ready = False
            try:
                _reference_path(project_dir, state, take_id)
                reference_ready = True
            except FileNotFoundError:
                pass
            try:
                _candidate_path(project_dir, queue, take_id)
                candidate_ready = True
            except FileNotFoundError:
                pass
            last = reviews[-1] if reviews else None
            take_views.append(
                {
                    "takeId": take_id,
                    "referenceReady": reference_ready,
                    "candidateReady": candidate_ready,
                    "reviewCount": len(reviews),
                    "lastRecommendation": str(last.get("recommendation") or "") if isinstance(last, dict) else "",
                    "latestAverageScore": last.get("averageScore") if isinstance(last, dict) else None,
                }
            )
        return {
            "projectId": state["projectId"],
            "schemaVersion": state["schemaVersion"],
            "policy": state["policy"],
            "criteria": CRITERIA,
            "takes": take_views,
            "humanApprovalRequired": True,
        }


def register_reference(root: Path, project_id: str, take_id: str, reference_file: str) -> dict[str, Any]:
    """Register an existing reference image inside the pilot's refs directory."""

    project_dir = _project_dir(root, project_id)
    take_id = _validate_take_id(take_id)
    with _STATE_LOCK:
        state = _load_state(project_dir)
        raw_reference = Path(str(reference_file or "").strip())
        if (
            raw_reference.is_absolute()
            or not raw_reference.parts
            or raw_reference.parts[0].lower() != "refs"
            or ".." in raw_reference.parts
        ):
            raise ValueError("A referência deve estar dentro da pasta refs do próprio projeto.")
        reference = _safe_existing_file(project_dir, reference_file, REFERENCE_EXTENSIONS)
        if not reference.is_relative_to((project_dir / "refs").resolve()):
            raise ValueError("A referência deve estar dentro da pasta refs do próprio projeto.")
        state["takes"][take_id]["referenceFile"] = reference.relative_to(project_dir).as_posix()
        state["updatedAt"] = _utc_now()
        _atomic_json_write(_state_path(project_dir), state)
    return get_pilot(root, project_id)


def critic_brief(root: Path, project_id: str, take_id: str) -> dict[str, Any]:
    """Return a fresh-context review package for one generated candidate."""

    project_dir = _project_dir(root, project_id)
    take_id = _validate_take_id(take_id)
    with _STATE_LOCK:
        state = _load_state(project_dir)
        queue = _load_queue(project_dir)
        reference = _reference_path(project_dir, state, take_id)
        candidate = _candidate_path(project_dir, queue, take_id)
        reference_identity = _file_identity(project_dir, reference)
        candidate_identity = _file_identity(project_dir, candidate)
        already_reviewed = _review_for_candidate(state, take_id, candidate_identity["sha256"])
        take = _find_take(queue, take_id)
        return {
            "projectId": project_id,
            "projectDirectory": str(project_dir),
            "takeId": take_id,
            "candidateVersion": _candidate_version(state, take_id, candidate_identity["sha256"]),
            "candidate": candidate_identity,
            "reference": reference_identity,
            "objective": str(take.get("objective") or "").strip(),
            "animationPrompt": str(take.get("animation_prompt") or "").strip(),
            "criteria": CRITERIA,
            "alreadyReviewed": already_reviewed is not None,
            "humanApprovalRequired": True,
            "submission": {
                "method": "POST",
                "path": f"/api/video-projects/{project_id}/takes/{take_id}/gauntlet/verdict",
                "requiredFields": [
                    "criticId",
                    "candidateSha256",
                    "suggestedVerdict",
                    "scores",
                    "largestGap",
                    "repairPrompt",
                    "observations",
                ],
            },
            "criticInstructions": (
                "Você é um crítico independente em contexto novo. Não leia justificativas do criador, "
                "não edite arquivos e não aprove o take. Inspecione o vídeo candidato real com "
                "pemara_read_video e a referência com pemara_vision. Compare pixels, movimento e "
                "continuidade; não invente observações. Dê notas inteiras de 0 a 5 para todos os "
                "critérios, a maior lacuna objetiva, um reparo curto de prompt e de uma a sete "
                "observações verificáveis. Envie apenas uma recomendação ao Maestro."
            ),
        }


def submit_verdict(root: Path, project_id: str, take_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist one independent critic verdict for the current immutable candidate."""

    project_dir = _project_dir(root, project_id)
    take_id = _validate_take_id(take_id)
    if not isinstance(payload, dict):
        raise ValueError("O veredito deve ser um objeto JSON.")
    allowed = {
        "criticId",
        "candidateSha256",
        "suggestedVerdict",
        "scores",
        "largestGap",
        "repairPrompt",
        "observations",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Campos de veredito não permitidos: {', '.join(sorted(unknown))}")
    critic_id = _short_text(payload.get("criticId"), "criticId", 4, 100)
    candidate_sha256 = _short_text(payload.get("candidateSha256"), "candidateSha256", 64, 64).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256):
        raise ValueError("candidateSha256 deve ser um SHA-256 hexadecimal.")
    suggested = str(payload.get("suggestedVerdict") or "").strip().upper()
    if suggested not in VALID_SUGGESTED_VERDICTS:
        raise ValueError("suggestedVerdict inválido.")
    scores = _normalize_scores(payload.get("scores"))
    largest_gap = _short_text(payload.get("largestGap"), "largestGap", 5, 700)
    repair_prompt = str(payload.get("repairPrompt") or "").strip()
    if len(repair_prompt) > 2000:
        raise ValueError("repairPrompt deve ter no máximo 2000 caracteres.")
    observations = payload.get("observations")
    if not isinstance(observations, list) or not 1 <= len(observations) <= 7:
        raise ValueError("observations deve conter de uma a sete observações.")
    normalized_observations = [
        _short_text(item, "observations[]", 5, 1000) for item in observations
    ]

    with _STATE_LOCK:
        state = _load_state(project_dir)
        queue = _load_queue(project_dir)
        candidate = _candidate_path(project_dir, queue, take_id)
        candidate_identity = _file_identity(project_dir, candidate)
        if candidate_identity["sha256"] != candidate_sha256:
            raise ValueError("O candidato mudou desde o briefing; obtenha um novo briefing antes de enviar o veredito.")
        if _review_for_candidate(state, take_id, candidate_sha256) is not None:
            raise ValueError("Este candidato já recebeu um veredito Gauntlet; gere uma nova versão antes da próxima crítica.")
        _reference_path(project_dir, state, take_id)
        previous_average = _previous_score(state, take_id)
        recommendation, reason, improvement = _recommendation(
            state,
            take_id,
            candidate_sha256,
            scores,
            suggested,
            previous_average,
        )
        review = {
            "reviewedAt": _utc_now(),
            "criticId": critic_id,
            "candidateSha256": candidate_sha256,
            "candidate": candidate_identity,
            "suggestedVerdict": suggested,
            "scores": scores,
            "averageScore": _score_average(scores),
            "previousAverageScore": previous_average,
            "improvement": improvement,
            "largestGap": largest_gap,
            "repairPrompt": repair_prompt,
            "observations": normalized_observations,
            "recommendation": recommendation,
            "recommendationReason": reason,
            "humanApprovalRequired": True,
        }
        state["takes"][take_id]["reviews"].append(review)
        state["updatedAt"] = _utc_now()
        _atomic_json_write(_state_path(project_dir), state)
    return review
