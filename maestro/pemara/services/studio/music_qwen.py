"""Validated musical planning; Qwen proposes, code protects explicit choices."""
from __future__ import annotations
import math
from copy import deepcopy
from typing import Any

PLAN_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "duration_seconds": {"type": "number", "minimum": 2, "maximum": 900},
    "bpm": {"type": "integer", "minimum": 30, "maximum": 300},
    "style": {"type": "string", "minLength": 8, "maxLength": 1500},
    "sections": {"type": "array", "minItems": 1, "maxItems": 20, "items": {
        "type": "object", "additionalProperties": False, "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
            "start": {"type": "number", "minimum": 0, "maximum": 900},
            "end": {"type": "number", "minimum": 0, "maximum": 900},
            "energy": {"type": "number", "minimum": 0, "maximum": 1},
            "lead": {"type": "string"},
            "instruments": {"type": "array", "items": {"type": "string"}}},
        "required": ["name", "start", "end", "energy", "lead", "instruments"]}},
    "tracks": {"type": "object", "additionalProperties": {"type": "object",
        "additionalProperties": False, "properties": {
            "gainDb": {"type": "number", "minimum": -18, "maximum": 6},
            "density": {"type": "number", "minimum": .15, "maximum": 1.2},
            "velocityScale": {"type": "number", "minimum": .5, "maximum": 1.25},
            "role": {"type": "string", "minLength": 1, "maxLength": 200}},
        "required": ["gainDb", "density", "velocityScale", "role"]}}},
    "required": ["duration_seconds", "bpm", "style", "sections", "tracks"]}

CREATION_INSTRUMENTS = ('piano', 'violin', 'cello', 'guitar', 'bass', 'drums',
                        'synth', 'percussion', 'acoustic_guitar', 'vocals')


def plan_schema(instruments: tuple[str, ...], *, require_all: bool = False) -> dict:
    """Expose the same closed instrument vocabulary to decoding and validation."""
    if not instruments or len(set(instruments)) != len(instruments):
        raise ValueError('Lista de instrumentos do contrato invalida.')
    schema = deepcopy(PLAN_SCHEMA)
    track = schema['properties']['tracks']['additionalProperties']
    schema['properties']['tracks'] = {
        'type': 'object', 'additionalProperties': False, 'minProperties': 1,
        'properties': {name: deepcopy(track) for name in instruments}}
    if require_all:
        schema['properties']['tracks']['required'] = list(instruments)
    section = schema['properties']['sections']['items']['properties']
    section['instruments']['items']['enum'] = list(instruments)
    section['instruments']['uniqueItems'] = True
    section['lead']['enum'] = list(dict.fromkeys((*instruments, 'vocals', 'none')))
    return schema


def _number(value: Any, low: float, high: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Plano Qwen invalido: {label} deve estar entre {low:g} e {high:g}; recebido {value!r}.")
    return float(value)


def validate_plan(plan: dict, *, instruments: tuple[str, ...], duration: float | None,
                  max_duration: float = 900, min_duration: float = 6,
                  reference_sections: list[dict] | None = None) -> dict:
    if not isinstance(plan, dict) or set(plan) != set(PLAN_SCHEMA['required']):
        raise ValueError("Plano Qwen incompleto ou com campos nao permitidos.")
    result = deepcopy(plan)
    seconds = _number(result['duration_seconds'], min_duration, max_duration, 'duracao')
    if duration is not None and abs(seconds - duration) > 0.01:
        raise ValueError("Qwen tentou alterar a duracao fixada pelo proprietario ou pela fonte.")
    _number(result['bpm'], 30, 300, 'BPM')
    if type(result['bpm']) is not int or not isinstance(result['style'], str) or not 8 <= len(result['style']) <= 1500:
        raise ValueError("Plano Qwen sem estilo/BPM validos.")
    selected = set(instruments)
    tracks = result['tracks']
    if not isinstance(tracks, dict) or set(tracks) != selected:
        raise ValueError("Qwen alterou os instrumentos escolhidos.")
    for name, track in tracks.items():
        if not isinstance(track, dict) or set(track) != {'gainDb', 'density', 'velocityScale', 'role'}:
            raise ValueError("Plano de pista Qwen invalido.")
        for field, low, high in [('gainDb', -18, 6), ('density', .15, 1.2), ('velocityScale', .5, 1.25)]:
            _number(track[field], low, high, name + '.' + field)
        if not isinstance(track['role'], str) or not 1 <= len(track['role']) <= 200:
            raise ValueError("Papel instrumental Qwen invalido.")
    sections = result['sections']
    if not isinstance(sections, list) or not 1 <= len(sections) <= 20:
        raise ValueError("Secoes Qwen invalidas.")
    cursor = 0.0
    for section in sections:
        if not isinstance(section, dict) or set(section) != {'name', 'start', 'end', 'energy', 'lead', 'instruments'}:
            raise ValueError("Secao Qwen incompleta.")
        start = _number(section['start'], 0, seconds, 'inicio de secao')
        end = _number(section['end'], 0, seconds, 'fim de secao')
        if abs(start - cursor) > .01 or end <= start:
            raise ValueError("Secoes Qwen com lacuna, sobreposicao ou ordem invalida.")
        _number(section['energy'], 0, 1, 'energia')
        if not isinstance(section['name'], str) or not 1 <= len(section['name']) <= 80:
            raise ValueError("Nome de secao invalido.")
        members = section['instruments']
        if (not isinstance(section['lead'], str) or section['lead'] not in selected | {'vocals', 'none'}
                or not isinstance(members, list) or not all(isinstance(name, str) for name in members)
                or len(set(members)) != len(members) or not set(members) <= selected):
            missing = [name for name in members if isinstance(name, str) and name not in selected] if isinstance(members, list) else []
            raise ValueError(f"Instrumento de secao nao autorizado em {section['name']!r}: "
                             f"lead={section['lead']!r}, pistas ausentes={missing!r}; "
                             f"pistas existentes={sorted(selected)!r}.")
        cursor = end
    if abs(cursor - seconds) > .01:
        raise ValueError("Plano Qwen nao cobre a duracao completa.")
    if reference_sections and [(s['start'], s['end']) for s in sections] != [(s['start'], s['end']) for s in reference_sections]:
        raise ValueError("Qwen tentou reescrever as fronteiras da referencia.")
    return result








def creation_caption(caption: str, plan: dict) -> str:
    roles = '; '.join(f"{name}: {track['role']}" for name, track in plan['tracks'].items())
    form = '; '.join(f"{s['name']} {s['start']:g}-{s['end']:g}s energy {s['energy']:g} lead {s['lead']}"
                     for s in plan['sections'])
    result = f"{caption}. Producer style: {plan['style']}. Roles: {roles}. Form: {form}. Complete ending."
    if len(result) > 1500:
        raise ValueError('Direcao Qwen excedeu o limite de condicionamento; nenhuma secao foi cortada silenciosamente.')
    return result


