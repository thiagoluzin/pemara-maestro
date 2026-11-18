"""Local MiniMax H3 prompt compiler based on the official prompt-writing skill.

The compiler is deliberately deterministic: it performs no network request and
does not send project text or media to an external prompt optimizer.  The
official files are pinned under ``third_party/MiniMax-H3-official``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable


OFFICIAL_REPOSITORY = "https://github.com/MiniMax-AI/MiniMax-H3"
OFFICIAL_COMMIT = "d21241f0a4b3acbb34c97dae47fa417b7065e438"
PROMPT_CONTRACT_VERSION = "minimax-h3-official-prompt-writing@2026-08-15"

_BASE_SECTION_ORDER = (
    "integrated_multimodal_description:",
    "overall_soundscape:",
    "non_diegetic_music:",
)
_REF_SECTION_ORDER = (
    "subject_definitions:",
    "summary:",
    "retention_analysis:",
    "detailed_description:",
    "overall_soundscape:",
    "non_diegetic_music:",
)
_MODES = {"T2VA", "I2VA", "FL2VA", "L2VA", "REF2VA"}
_LABEL_RE = re.compile(r"<(?:Subject|Picture|Video|Audio)\s+\d+>")
_QUOTED_TEXT_RE = re.compile(
    r'''"(?P<straight>(?:[^"\\]|\\.)*)"|“(?P<curly>[^”]*)”|«(?P<angle>[^»]*)»|‘(?P<curly_single>[^’]*)’|(?<!\w)'(?P<single>[^']+)'(?!\w)''',
    re.DOTALL,
)
_SPEECH_CUE_RE = re.compile(
    r"\b(?P<generic>o\s+personagem(?:\s+da\s+fala)?\s+)?"
    r"(?:(?:deve|vai)\s+)?"
    r"(?:ter\s+a\s+seguinte\s+fala|(?:dizer|falar|diz|diga|fala|fale)"
    r"(?:\s+(?:exatamente|somente|apenas))?|(?:texto\s+da\s+|seguinte\s+)?fala)"
    r"\s*:?[ \t\r\n]*$", re.IGNORECASE,
)


_REQUEST_SECTION_RE = re.compile(
    r"(\[(?:VISUAL|AUDIO|INSTRU[ÇC][ÕO]ES?\s+(?:VISUAIS|DE\s+[ÁA]UDIO))\b[^\]\r\n]*\])",
    re.IGNORECASE,
)


def normalize_quoted_speech(description: str) -> str:
    """Honor explicit visual/instruction sections before the ordinary quote rule.

    Repeated preview/worker/compiler passes are idempotent. Historical dialogue
    tags accidentally inserted inside DO NOT SPEAK sections become literal text.
    """
    sections = _REQUEST_SECTION_RE.split(description)
    if len(sections) == 1:
        return _normalize_plain_quoted_speech(description)
    output = [_normalize_plain_quoted_speech(sections[0])]
    for index in range(1, len(sections), 2):
        header, body = sections[index:index + 2]
        protected = bool(re.search(r'DO NOT SPEAK|N[ÃA]O (?:FALAR|NARRAR)|VISUAL|INSTRUCTIONS|INSTRU', header, re.I))
        literal_audio = not protected and bool(re.search(r'SPOKEN|SUNG|FALA|CANTAD', header, re.I))
        if protected:
            body = re.sub(r'<d>\s*(?:\[[^]]+\]\s*)?(.*?)</d>', lambda m: '"' + m.group(1) + '"', body, flags=re.S)
        else:
            body = _normalize_plain_quoted_speech(body)
            if literal_audio and body.strip() and '<d>' not in body:
                body = '\n<d>[Portuguese] ' + body.strip() + '</d>\n'
        output.extend((header, body))
    return ''.join(output)


def _normalize_plain_quoted_speech(description: str) -> str:
    """Owner rule: every quoted span in the plain prompt is literal speech.

    No speech verb or contextual classifier is required. Keep existing H3
    dialogue blocks intact, including quotation marks inside spoken content.
    """
    parts = re.split(r"(<d>.*?</d>)", description, flags=re.DOTALL)

    def convert(match: re.Match[str]) -> str:
        spoken = next(value for value in match.groupdict().values() if value is not None)
        return f"<d>[Portuguese] {spoken}</d>" if spoken.strip() else match.group(0)

    # Retain the established short form for the owner's original single-speaker
    # request. Other text outside quotes stays untouched, including speaker names.
    quotes = list(_QUOTED_TEXT_RE.finditer(description))
    if len(parts) == 1 and len(quotes) == 1 and not re.search(r"\(S\d", description):
        quote = quotes[0]
        cue = _SPEECH_CUE_RE.search(description[:quote.start()])
        if cue and cue.group("generic") and convert(quote) != quote.group(0):
            return (description[:cue.start()] + "The character (S1) says: "
                    + convert(quote) + description[quote.end():])
    return "".join(
        part if index % 2 else _QUOTED_TEXT_RE.sub(convert, part)
        for index, part in enumerate(parts)
    )


def _collapse_description(value: str) -> str:
    # Dialogue is literal source text: do not normalize its words or spacing.
    parts = re.split(r"(<d>.*?</d>)", value, flags=re.DOTALL)
    return "".join(
        part if index % 2 else re.sub(r"\s+", " ", part)
        for index, part in enumerate(parts)
    ).strip()


@dataclass(frozen=True)
class H3PromptDocument:
    prompt: str
    mode: str
    duration_seconds: float
    contract_version: str = PROMPT_CONTRACT_VERSION
    official_commit: str = OFFICIAL_COMMIT


def detect_base_mode(*, has_first_frame: bool, has_last_frame: bool) -> str:
    if has_first_frame and has_last_frame:
        return "FL2VA"
    if has_first_frame:
        return "I2VA"
    if has_last_frame:
        return "L2VA"
    return "T2VA"


def _duration_label(duration_seconds: float) -> str:
    value = Decimal(str(max(0.0, float(duration_seconds))))
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _collapse_whitespace(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _alignment_instruction(mode: str, duration_seconds: float, final_shot: int) -> str:
    duration = _duration_label(duration_seconds)
    if mode == "T2VA":
        return ""
    if mode == "I2VA":
        return (
            "For the target video, at 0.00 seconds into the target video, "
            "<Picture 1> (from [Shot 1]) is fully referenced."
        )
    if mode == "FL2VA":
        return (
            "How the reference pictures align with the target video — "
            "Picture 1 (from Shot 1) aligns with the 0.00-second mark of the "
            f"target video; Picture 2 (from Shot {final_shot}) aligns with the "
            f"{duration}-second mark of the target video."
        )
    return (
        "How the reference pictures align with the target video — "
        f"<Picture 1> (from [Shot {final_shot}]) aligns with the "
        f"{duration}-second mark of the target video."
    )


def _assert_section_order(prompt: str, sections: Iterable[str]) -> None:
    positions = [prompt.find(section) for section in sections]
    if any(position < 0 for position in positions):
        missing = [section for section, position in zip(sections, positions) if position < 0]
        raise ValueError(f"Prompt H3 incompleto; secoes ausentes: {', '.join(missing)}")
    if positions != sorted(positions):
        raise ValueError("As secoes do prompt H3 estao fora da ordem oficial.")


def validate_base_prompt(prompt: str, mode: str) -> None:
    normalized_mode = str(mode or "").upper()
    if normalized_mode not in _MODES - {"REF2VA"}:
        raise ValueError(f"Modo base H3 invalido: {mode}")
    _assert_section_order(prompt, _BASE_SECTION_ORDER)
    if "[Shot 1]" not in prompt:
        raise ValueError("Prompt H3 base exige [Shot 1].")
    if normalized_mode == "I2VA" and not prompt.startswith("For the target video,"):
        raise ValueError("I2VA exige a instrucao oficial de alinhamento do primeiro quadro.")
    if normalized_mode in {"FL2VA", "L2VA"} and not prompt.startswith(
        "How the reference pictures align with the target video"
    ):
        raise ValueError(f"{normalized_mode} exige a instrucao oficial de keyframes.")


def compile_base_prompt(
    description: str,
    *,
    mode: str,
    duration_seconds: float,
    overall_soundscape: str = "N/A",
    non_diegetic_music: str = "N/A",
    final_shot: int = 1,
) -> H3PromptDocument:
    """Compile a T2VA/I2VA/FL2VA/L2VA prompt in the official section order."""

    normalized_mode = str(mode or "").upper()
    if normalized_mode not in _MODES - {"REF2VA"}:
        raise ValueError(f"Modo base H3 invalido: {mode}")
    body = str(description or "").strip()
    if not body:
        raise ValueError("A descricao H3 nao pode ficar vazia.")

    # A caller may submit an already-compiled official document. Preserve it
    # byte-for-byte after validation instead of nesting the sections again.
    if all(section in body for section in _BASE_SECTION_ORDER):
        validate_base_prompt(body, normalized_mode)
        return H3PromptDocument(body, normalized_mode, float(duration_seconds))

    body = _collapse_description(normalize_quoted_speech(body))
    if not body.startswith("[Shot 1]"):
        body = f"[Shot 1] {body}"
    instruction = _alignment_instruction(
        normalized_mode,
        duration_seconds,
        max(1, int(final_shot)),
    )
    sections = (
        f"integrated_multimodal_description: {body}",
        f"overall_soundscape: {_collapse_whitespace(overall_soundscape) or 'N/A'}",
        f"non_diegetic_music: {_collapse_whitespace(non_diegetic_music) or 'N/A'}",
    )
    prompt = "\n\n".join((*([instruction] if instruction else []), *sections))
    validate_base_prompt(prompt, normalized_mode)
    return H3PromptDocument(prompt, normalized_mode, float(duration_seconds))


def compile_ref_prompt(
    *,
    subject_definitions: str,
    summary: str,
    retention_analysis: str,
    detailed_description: str,
    overall_soundscape: str,
    non_diegetic_music: str,
    duration_seconds: float,
) -> H3PromptDocument:
    """Compile the six official Ref2VA sections without external processing."""

    values = {
        "subject_definitions": str(subject_definitions or "").strip(),
        "summary": str(summary or "").strip(),
        "retention_analysis": str(retention_analysis or "").strip(),
        "detailed_description": str(detailed_description or "").strip(),
        "overall_soundscape": str(overall_soundscape or "").strip(),
        "non_diegetic_music": str(non_diegetic_music or "").strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError(f"Ref2VA incompleto; secoes vazias: {', '.join(missing)}")
    if "[Shot 1]" not in values["detailed_description"]:
        raise ValueError("Ref2VA exige [Shot 1] em detailed_description.")
    defined_labels = set(_LABEL_RE.findall(values["subject_definitions"]))
    used_labels = set(
        _LABEL_RE.findall(
            "\n".join(
                (
                    values["summary"],
                    values["retention_analysis"],
                    values["detailed_description"],
                    values["overall_soundscape"],
                    values["non_diegetic_music"],
                )
            )
        )
    )
    unresolved = sorted(used_labels - defined_labels)
    if unresolved:
        raise ValueError(f"Ref2VA contem labels sem definicao: {', '.join(unresolved)}")
    prompt = "\n\n".join(f"{name}:\n{value}" for name, value in values.items())
    _assert_section_order(prompt, _REF_SECTION_ORDER)
    return H3PromptDocument(prompt, "REF2VA", float(duration_seconds))


def official_skill_integrity(workspace_root: Path) -> dict[str, object]:
    """Report the pinned official files and hashes without downloading anything."""

    root = (
        Path(workspace_root)
        / "third_party"
        / "MiniMax-H3-official"
        / "skills"
        / "h3-prompt-writing"
    )
    expected = {
        "SKILL.md": "95d74fee00e78641fb9e774ab17488516ceece441231519287f0d3128eaa8c54",
        "references/base-en.txt": "088fb632fa3cbb18c9821024fb689e6f0f356f824c8f2e6b8e43a33239b137c7",
        "references/ref-en.txt": "b621067b41988c4d92be715b7a98ba48338f4076ab6041d95fcf463ea7c8ccdd",
    }
    files: dict[str, object] = {}
    ok = True
    for relative, expected_hash in expected.items():
        path = root / Path(relative)
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        match = actual == expected_hash
        ok = ok and match
        files[relative] = {
            "present": path.is_file(),
            "sha256": actual,
            "expected_sha256": expected_hash,
            "match": match,
        }
    return {
        "ok": ok,
        "repository": OFFICIAL_REPOSITORY,
        "commit": OFFICIAL_COMMIT,
        "contract_version": PROMPT_CONTRACT_VERSION,
        "files": files,
    }
