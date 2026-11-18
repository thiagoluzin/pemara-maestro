"""Duration arithmetic and YuE2 end-token evidence, without audio cuts."""
from fractions import Fraction
import re


def ending_budget(duration):
    duration = float(duration)
    tail = min(8.0, max(1.0, duration * .08))
    return {"limit_seconds": duration, "score_target_seconds": duration - tail,
            "ending_seconds": tail}


def arrangement_style(prompt, duration, instrumental=False):
    if duration is None:
        return (f"{prompt}\nChoose the complete song's natural length and structure yourself. "
                "There is no required target duration. The safety ceiling is 900 seconds, not a goal to fill. "
                "Compose a coherent intro, verses, chorus and resolved final outro with final chord decay "
                "and silence. Finish all sung words and then end the song naturally. "
                "No endless loop or unfinished solo. Write explicit measures, no repeat signs.")
    budget = ending_budget(duration)
    style = (f"{prompt}\nComplete song, target duration {float(duration):g} seconds maximum. "
             f"Compose the entire ABC arrangement within {budget['score_target_seconds']:g} seconds, "
             f"including a short outro and a resolved final cadence. Reserve the last "
             f"{budget['ending_seconds']:g} seconds for the final chord decay and silence. "
             "Finish all sung words before the outro. No endless loop, unfinished solo, or long fade-out. "
             "Write explicit measures, no repeat signs; keep intro and interludes brief.")
    if not instrumental and float(duration) <= 60:
        style += " Start singing immediately; no long instrumental intro. Prioritize the verse and chorus."
    return style


def _length(text):
    if not text:
        return Fraction(1)
    if "/" not in text:
        return Fraction(int(text))
    numerator, denominator = text.split("/", 1)
    if denominator and "/" not in denominator:
        return Fraction(int(numerator or 1), int(denominator))
    if denominator.strip("/"):
        raise ValueError("Fração ABC inválida.")
    return Fraction(int(numerator or 1), 2 ** (1 + len(denominator)))


def score_seconds(abc):
    """Measure the explicit multi-voice ABC subset produced by YuE2.

    Unsupported rhythmic constructs fail explicitly instead of inventing a duration.
    Voices accumulate independently; simultaneous voices are never summed together.
    """
    meter, unit, beat, bpm = Fraction(1), None, Fraction(1, 4), 120
    positions, voice, in_body = {}, "default", False
    tuplet_left, tuplet_factor, next_factor, previous = 0, Fraction(1), Fraction(1), None
    token = re.compile(r"(?:[\^_=]*[A-Ga-gzx][,']*|[ZX]|\[[^\]]+\])([0-9]*(?:/+[0-9]*)?)")
    for raw in abc.splitlines():
        line = raw.split("%", 1)[0].strip()
        if not line:
            continue
        field = re.match(r"^([A-Za-z]):\s*(.*)$", line)
        if field:
            key, value = field.groups()
            if key == "M":
                if in_body: raise ValueError("Mudança de compasso exige novo planejamento.")
                meter = Fraction(1) if value == "C" else Fraction(1, 2) if value == "C|" else Fraction(value)
            elif key == "L":
                if in_body: raise ValueError("Mudança de unidade ABC exige novo planejamento.")
                unit = Fraction(value)
            elif key == "Q":
                if in_body: raise ValueError("Mudança de andamento exige novo planejamento.")
                tempo = re.fullmatch(r"(?:(\d+/\d+)\s*=\s*)?(\d+(?:\.\d+)?)", value)
                if not tempo: raise ValueError("Andamento ABC não mensurável.")
                beat, bpm = Fraction(tempo[1] or "1/4"), float(tempo[2])
            elif key == "K":
                in_body = True
            elif key == "V" and in_body:
                voice = value.split()[0]
                previous = None
            continue
        if not in_body:
            continue
        unit = unit or (Fraction(1, 16) if meter < Fraction(3, 4) else Fraction(1, 8))
        line = re.sub(r'"[^"]*"|![^!]*!|\{[^}]*\}', '', line)
        if re.search(r":\||\|:|\[\d|&", line):
            raise ValueError("Repetições/vozes sobrepostas exigem compassos explícitos.")
        i = 0
        while i < len(line):
            inline_voice = re.match(r"\[V:([^\]]+)\]", line[i:])
            if inline_voice:
                voice = inline_voice[1].strip().split()[0]; previous = None
                i += inline_voice.end(); continue
            tuplet = re.match(r"\(([234])(?::(\d+))?(?::(\d+))?", line[i:])
            if tuplet:
                n = int(tuplet[1]); ratio = int(tuplet[2] or (3 if n == 2 else 2 if n == 3 else 3))
                tuplet_left = int(tuplet[3] or n); tuplet_factor = Fraction(ratio, n)
                i += tuplet.end(); continue
            broken = re.match(r"[><]+", line[i:])
            if broken:
                if previous is None: raise ValueError("Ritmo quebrado ABC inválido.")
                short = Fraction(1, 2 ** len(broken[0])); long = 2 - short
                first, next_factor = (long, short) if broken[0][0] == '>' else (short, long)
                positions[voice] += previous * (first - 1)
                i += broken.end(); continue
            match = token.match(line, i)
            if match:
                value = (meter if match[0][0] in 'ZX' else unit) * _length(match[1]) * next_factor
                next_factor = Fraction(1)
                if tuplet_left:
                    value *= tuplet_factor; tuplet_left -= 1
                positions[voice] = positions.get(voice, Fraction(0)) + value
                previous = value
                i = match.end(); continue
            if line[i] in " |[]()-~.\t":
                i += 1; continue
            raise ValueError("Notação rítmica ABC não suportada pelo controle de duração.")
    if not positions or bpm <= 0 or beat <= 0:
        raise ValueError("Partitura sem duração musical verificável.")
    return float(max(positions.values()) / beat) * 60 / bpm


def generation_ending(outputs, duration):
    diagnostics = [item.get('text', '') for item in outputs
                   if item.get('kind') == 'text' and str(item.get('node', '')) == '10']
    # PreviewAny prints a tensor-containing conditioning as Python text. Read only
    # this known scalar, never eval model output or deserialize the tensor.
    flags = re.findall(r"['\"]yue2_truncated['\"]\s*:\s*(True|False|true|false)", '\n'.join(diagnostics))
    seconds = [float(item['text']) for item in outputs
               if item.get('kind') == 'text' and str(item.get('node', '')) == '11']
    if len(flags) != 1 or len(seconds) != 1:
        raise RuntimeError("YuE2 não confirmou o encerramento da música; saída preservada para revisão.")
    truncated = flags[0].lower() == 'true'
    return {"end_token_reached": not truncated, "generated_seconds": seconds[0],
            "within_duration": 0 < seconds[0] <= float(duration) + .04,
            "musical_ending_requires_listening": True}


def compact_score(abc, target):
    """Remove complete aligned phrases, retaining the original ending and tempo.

    Prefer instrumental passages, sparse held notes and repetitions. Never
    truncate a note, alter tempo, or fabricate a replacement cadence. The full
    original score remains in the job's provenance for review and rollback.
    """
    key = re.search(r'(?m)^K:[^\n]*\n', abc)
    if not key: raise ValueError('Partitura ABC sem tonalidade.')
    header, body = abc[:key.end()], abc[key.end():]
    first = re.search(r'(?m)^V:\s*(\S+)', body)
    if not first: raise ValueError('Compactação exige vozes ABC explícitas.')
    primary = first[1]
    sections = re.split(r'(?m)(^%[^\n]*\n)', body)
    section_name, phrases = '% music', []
    for part in sections:
        if part.startswith('%'):
            section_name = part.strip(); continue
        starts = list(re.finditer(r'(?m)^V:\s*' + re.escape(primary) + r'(?:\s|$)', part))
        for n, start in enumerate(starts):
            chunk = part[start.start():starts[n+1].start() if n+1 < len(starts) else len(part)]
            seconds = score_seconds(header + chunk)
            voices = re.split(r'(?m)^V:[^\n]*\n', chunk)[1:]
            # Only remove phrases whose simultaneous voices have equal length.
            lengths = [score_seconds(header + voice) for voice in voices]
            if lengths and max(lengths) - min(lengths) > .05:
                raise ValueError('Vozes ABC desalinhadas; recomposição necessária.')
            primary_notes = re.sub(r'"[^"]*"|%[^\n]*', '', voices[0] if voices else '')
            note_count = len(re.findall(r'[A-Ga-g]', primary_notes))
            phrases.append({'section': section_name, 'abc': chunk, 'seconds': seconds,
                            'notes': note_count, 'keep': True})
    if not phrases: raise ValueError('Nenhuma frase musical completa para compactar.')
    protected, seen = {len(phrases)-1}, set()
    for i, phrase in enumerate(phrases):
        kind = re.sub(r'\d', '', phrase['section'].lower())
        if phrase['notes'] and kind not in seen:
            protected.add(i); seen.add(kind)
    total = sum(p['seconds'] for p in phrases)
    candidates = sorted((i for i in range(len(phrases)) if i not in protected),
                        key=lambda i: (0 if not phrases[i]['notes'] else 1 if phrases[i]['notes'] <= 4 else 2,
                                       -phrases[i]['seconds'], i))
    for i in candidates:
        if total <= target: break
        phrases[i]['keep'] = False; total -= phrases[i]['seconds']
    if total > target: raise ValueError('Frases essenciais e encerramento excedem a duração.')
    result, last_section = header, None
    for phrase in phrases:
        if not phrase['keep']: continue
        if phrase['section'] != last_section:
            result += phrase['section'] + '\n'; last_section = phrase['section']
        result += phrase['abc']
    if score_seconds(result) > target + .04:
        raise ValueError('Composição compactada excede a duração.')
    return result
