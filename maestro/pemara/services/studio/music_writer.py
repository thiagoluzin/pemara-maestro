"""Prompt-to-song writing on a local GPU model, released before audio generation."""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from music_ending import ending_budget
from copy import deepcopy
from music_qwen import CREATION_INSTRUMENTS, plan_schema, validate_plan, creation_caption

SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "title": {"type": "string"}, "caption": {"type": "string"},
    "lyrics": {"type": "string"}, "vocal_language": {"type": "string"},
    "instrumental": {"type": "boolean"}, "production_plan": plan_schema(CREATION_INSTRUMENTS)},
    "required": ["title", "caption", "lyrics", "vocal_language", "instrumental", "production_plan"]}


def _require_declared_tracks(schema, raw):
    """Ask Qwen to supply tracks it already named; never invent their settings."""
    plan = raw.get('production_plan') if isinstance(raw, dict) else None
    if not isinstance(plan, dict):
        return
    selected = set(plan['tracks']) if isinstance(plan.get('tracks'), dict) else set()
    if isinstance(plan.get('sections'), list):
        for section in plan['sections']:
            if not isinstance(section, dict):
                continue
            members = section.get('instruments')
            if isinstance(members, list):
                selected.update(name for name in members if isinstance(name, str))
            if isinstance(section.get('lead'), str):
                selected.add(section['lead'])
    selected &= set(CREATION_INSTRUMENTS)
    if not selected:
        return
    closed = plan_schema(tuple(name for name in CREATION_INSTRUMENTS if name in selected), require_all=True)
    target = schema['properties']['production_plan']['properties']
    target['tracks'] = closed['properties']['tracks']
    target['sections'] = closed['properties']['sections']


def validate_song(song):
    if not isinstance(song, dict) or type(song.get("instrumental")) is not bool:
        raise ValueError("O escritor local retornou uma direção musical inválida.")
    for field, limit in (("title", 120), ("caption", 1500), ("lyrics", 4096), ("vocal_language", 40)):
        value = song.get(field)
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError(f"O escritor local retornou {field} inválido.")
        song[field] = value.strip()
    if not song["title"] or len(song["caption"]) < 8:
        raise ValueError("O escritor local não retornou título e direção musical.")
    # Some small writers repeat lyrics in caption; keep musical direction only.
    song["caption"] = re.split(r"\[(?:Verse|Chorus|Bridge|Intro|Outro)\b", song["caption"], maxsplit=1, flags=re.I)[0].strip()
    if len(song["caption"]) < 8:
        raise ValueError("O escritor local não retornou uma direção musical separada da letra.")
    song["lyrics"] = re.sub(r"\[(Verse|Chorus|Bridge)\s*\d*\]", lambda m: f'[{m[1].title()}]', song["lyrics"], flags=re.I)
    if song["instrumental"]:
        song["lyrics"] = ""
    elif len(song["lyrics"]) < 25 or not re.search(r"\[(?:Verse|Chorus)\]", song["lyrics"], re.I):
        raise ValueError("O escritor local não retornou uma letra cantável. Tente novamente.")
    return song


def _validate_written_song(raw, *, duration, provided_lyrics, instrumental,
                           max_duration, min_duration, provided_bpm):
    if not isinstance(raw, dict):
        raise ValueError('Qwen nao retornou um plano JSON valido.')
    raw = deepcopy(raw)
    if instrumental is not None and raw.get('instrumental') is not instrumental:
        raise ValueError("Qwen tentou alterar a escolha de voz/instrumental.")
    if provided_lyrics is not None and raw.get('lyrics') != provided_lyrics:
        raise ValueError("Qwen tentou reescrever a letra fornecida pelo proprietario.")
    song = validate_song(raw)
    plan = song.get('production_plan')
    if not isinstance(plan, dict) or not isinstance(plan.get('tracks'), dict):
        raise ValueError('Plano Qwen sem pistas instrumentais validas.')
    instruments = tuple(plan['tracks'])
    invalid = set(instruments) - set(CREATION_INSTRUMENTS)
    if not instruments or invalid:
        names = ', '.join(sorted(str(name)[:60] for name in invalid)) or 'nenhuma pista'
        raise ValueError(f'Plano Qwen com instrumentos invalidos: {names}. Use as chaves do contrato.')
    song['production_plan'] = validate_plan(plan, instruments=instruments, duration=duration,
                                          max_duration=max_duration, min_duration=min_duration)
    if song['instrumental'] and ('vocals' in instruments or any(
            s['lead'] == 'vocals' for s in song['production_plan']['sections'])):
        raise ValueError('Plano instrumental Qwen incluiu canto.')
    if provided_bpm and song['production_plan']['bpm'] != provided_bpm:
        raise ValueError('Qwen tentou alterar o BPM escolhido pelo proprietario.')
    song['sonic_caption'] = song['caption']
    song['caption'] = creation_caption(song['caption'], song['production_plan'])
    song['duration_seconds'] = song['production_plan']['duration_seconds']
    if provided_lyrics is not None:
        song['lyrics'] = provided_lyrics
    return song


def write_song(prompt, duration, *, cancel_event=None, progress_cb=None,
               provided_lyrics=None, instrumental=None, max_duration=900, min_duration=6,
               provided_bpm=0):
    endpoint = os.environ.get("MAESTRO_MUSIC_WRITER_URL", "http://127.0.0.1:11435").rstrip("/")
    url = urllib.parse.urlsplit(endpoint)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password:
        raise ValueError("O escritor de música exige um endpoint local.")
    if cancel_event is not None and cancel_event.is_set():
        raise RuntimeError("Criação da letra cancelada.")
    if progress_cb:
        progress_cb(4, "Criando a letra e a direção musical com IA local.")
    payload = {
        "model": os.environ.get("MAESTRO_MUSIC_WRITER_MODEL", "qwen3.8-27b-uncensored-yarn-524k:latest"),
        "stream": True, "think": False, "format": SCHEMA, "keep_alive": 0,
        "options": {"num_gpu": 99, "num_ctx": 8192, "num_predict": 3500, "temperature": 0.8},
        "system": (
            "You are a songwriter for local music generation. Return only the requested JSON. "
            "Create an ORIGINAL song from the user's idea; never reproduce existing lyrics. "
            "Default to a VOCAL song; instrumental=true ONLY when the user explicitly asks for no voice/instrumental. "
            "Write the lyrics in the requested language, otherwise Brazilian Portuguese. "
            "Caption must be in English: genre, mood, instruments, groove and vocal performance. "
            "Do not invent a different genre or remove requested instruments. "
            "Use [Verse], [Chorus], [Bridge] section tags and short, natural singable lines. "
            "Use concrete imagery, a coherent narrative and a memorable recurring hook. "
            "Avoid generic motivational filler, forced rhymes and awkward Portuguese word order. " +
            ("Choose a complete, coherent song structure and lyric length appropriate to the idea. "
             "No target duration is imposed; 900 seconds is only a ceiling, not a length to fill. "
             if duration is None else
             "Fit the lyrics to the requested duration: brief hook for under 30s, verse+chorus for 30-60s, "
             "for longer songs, develop distinct narrative verses, recurring hooks and instrumental contrasts "
             "proportional to tempo and duration, rather than forcing every song into two short verses. ") +
            "Translate references into specific musical decisions: rhythm articulation, guitar/bass timbre, "
            "drum groove, vocal delivery and contrasting sections. Avoid repeating the same story or hook "
            "across a collection. Never equate loudness, clipping or dense lyrics with musical weight. " +
            "Maximum 4096 characters of lyrics. "
            "Include a concise final [Outro] that closes the narrative. Reserve time for the ending: "
            "finish every sung line before the outro, final chord decay and silence. Avoid excessive verses, "
            "repeated choruses or long solos that would exceed the time. Keep the complete song under the limit. "
            "Set vocal_language to the language code, e.g. pt, en. Do not include technical instructions in lyrics. "
            "You also coordinate production: return production_plan with duration_seconds, bpm (30..300), "
            "style, contiguous sections (name,start,end,energy,lead,instruments) covering the whole duration "
            "energy is a fraction from 0.0 to 1.0 (e.g. verse 0.5, chorus 0.9), NEVER a percentage or 1..10 rating. "
            "Section start/end are seconds, contiguous from zero to duration_seconds. "
            "and tracks (gainDb -18..6, density .15..1.2, velocityScale .5..1.25, role). "
            "Use ONLY these exact tracks keys: piano,violin,cello,guitar,bass,drums,synth,percussion,acoustic_guitar,vocals. "
            "tracks must be a nonempty object. Electric, lead and rhythm guitar use the key guitar; "
            "electric bass uses bass; drum kit uses drums. Describe variants and solos in role/style, not new keys. "
            "Vocals use vocals, not voice, singer or vocal. Include vocals in section instruments only if it is a tracks key. "
            "For instrumental songs omit vocals and never use lead=vocals. "
            "lead is vocals, none, or a selected instrument. Develop energy by section, with a distinct ending. "
            "For model-choice duration, choose a natural duration within engine_limits, not its ceiling. "
            "For a manual duration, retain that exact duration. Preserve supplied_lyrics exactly when given. "
            "Respect forced_instrumental and forced_bpm when provided. Do not replace owner style or requested instruments. "
            "Keep caption and style concise (each under 400 characters), track roles brief and sections musically necessary."
        ),
        "prompt": json.dumps({"idea": prompt, "duration_seconds": duration,
                              "duration_mode": "model_choice" if duration is None else "user_selected",
                              "ending_budget": {"limit_seconds": max_duration} if duration is None else ending_budget(duration),
                              "engine_limits": {"min_seconds": min_duration, "max_seconds": max_duration},
                              "supplied_lyrics": provided_lyrics, "forced_instrumental": instrumental,
                              "forced_bpm": provided_bpm or None}, ensure_ascii=False),
    }
    payload['format'] = deepcopy(SCHEMA)
    duration_schema = payload['format']['properties']['production_plan']['properties']['duration_seconds']
    duration_schema.update({'minimum': min_duration, 'maximum': max_duration})
    if duration is not None:
        duration_schema['const'] = duration
    if provided_bpm:
        payload['format']['properties']['production_plan']['properties']['bpm']['const'] = provided_bpm
    original_prompt = payload['prompt']
    for attempt in range(2):
        raw = None
        try:
            raw, metadata = request_json(payload, endpoint, cancel_event=cancel_event)
            song = _validate_written_song(raw, duration=duration, provided_lyrics=provided_lyrics,
                instrumental=instrumental, max_duration=max_duration, min_duration=min_duration,
                provided_bpm=provided_bpm)
        except ValueError as exc:
            if attempt:
                raise ValueError(f'Qwen nao concluiu um plano valido apos uma correcao automatica: {exc}') from exc
            if progress_cb:
                progress_cb(8, 'Qwen ajustando o formato do plano musical automaticamente.')
            payload = deepcopy(payload)
            _require_declared_tracks(payload['format'], raw)
            payload['options']['temperature'] = .2
            payload['prompt'] = original_prompt + '\n' + json.dumps({
                'validation_error': str(exc), 'instruction':
                'Regenerate a complete valid song for the SAME owner request. Correct only invalid fields. '
                'Keep explicit owner lyrics, language, style, duration, BPM and vocal choices. '
                'Use exact allowed tracks keys and a nonempty tracks object; section instruments must be tracks keys.',
                'numeric_limits': {'section_energy': [0, 1], 'gainDb': [-18, 6], 'density': [.15, 1.2],
                                   'velocityScale': [.5, 1.25], 'bpm': [30, 300],
                                   'duration_seconds': [min_duration, max_duration]},
                'previous_answer': raw}, ensure_ascii=False)
            continue
        song.update(metadata)
        song['writer_validation_attempts'] = attempt + 1
        return song


def request_json(payload, endpoint, *, cancel_event=None):
    """Shared local Qwen transport; require GPU residency and release before audio."""
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
        raise ValueError("O orquestrador musical exige um endpoint local.")
    if cancel_event is not None and cancel_event.is_set():
        raise RuntimeError("Planejamento musical cancelado.")
    request = urllib.request.Request(endpoint + "/api/generate", json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
    fragments = []
    done = False
    gpu_checked = False
    gpu_bytes = 0
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            for line in response:
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError("Criação da letra cancelada.")
                if time.monotonic() - started > 900:
                    raise RuntimeError("O escritor local excedeu o tempo de criação da letra.")
                item = json.loads(line)
                if item.get("error"):
                    raise RuntimeError("O escritor local falhou. Confira o modelo configurado.")
                if item.get("response") and not gpu_checked:
                    with urllib.request.urlopen(endpoint + "/api/ps", timeout=10) as state_response:
                        models = json.load(state_response).get("models", [])
                    active = next((m for m in models if str(m.get("name", "")).removesuffix(":latest") ==
                                   payload["model"].removesuffix(":latest")), {})
                    gpu_bytes = int(active.get("size_vram") or 0)
                    if not gpu_bytes or gpu_bytes < 0.95 * int(active.get("size") or 0):
                        raise RuntimeError("O Qwen não carregou integralmente na GPU. Libere a VRAM e tente novamente.")
                    gpu_checked = True
                fragments.append(item.get("response", ""))
                if sum(map(len, fragments)) > 40000:
                    raise ValueError("Resposta do escritor local excedeu o limite.")
                if item.get("done"):
                    done = True
                    break
    except (OSError, TimeoutError) as exc:
        raise RuntimeError("Não foi possível criar a letra com a IA local. Confira o Ollama e tente novamente.") from exc
    if not done:
        raise RuntimeError("A criação local da letra foi interrompida antes de terminar.")
    try:
        result = json.loads("".join(fragments))
    except json.JSONDecodeError as exc:
        raise ValueError("O escritor local não retornou uma letra válida. Tente novamente.") from exc
    release_deadline = time.monotonic() + 30
    while True:
        with urllib.request.urlopen(endpoint + "/api/ps", timeout=10) as state_response:
            active_models = json.load(state_response).get("models", [])
        if not any(str(m.get("name", "")).removesuffix(":latest") == payload["model"].removesuffix(":latest")
                   for m in active_models):
            break
        if time.monotonic() >= release_deadline:
            raise RuntimeError("O Qwen ainda está ocupando a GPU; o áudio não foi iniciado. Tente novamente após liberar a VRAM.")
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("Criação da letra cancelada.")
        time.sleep(0.25)
    return result, {"writer_model": payload["model"], "writer_vram_bytes": gpu_bytes,
                    "writer_unloaded": True}
