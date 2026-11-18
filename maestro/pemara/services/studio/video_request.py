"""Resolve explicit video instructions locally, without inventing dialogue.

The original scene text remains authoritative. This is a bounded parser for
literal speech, duration and action cues, not a general semantic classifier.
"""
import re
import unicodedata
from h3_prompt_writing import normalize_quoted_speech


def _fold(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(c) != 'Mn')


def _bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() in {'true','1','yes','sim','on'}


def resolve_video_request(prompt: str, *, duration=None, native_audio=False,
                          camera_pose='', model_variant='base') -> dict:
    text = str(prompt or '').strip()
    if not text:
        raise ValueError('Descreva o que deve acontecer no vídeo.')
    compiled = 'integrated_multimodal_description:' in text
    structured = bool(re.search(r'\[(?:VISUAL|AUDIO|INSTRU[ÇC][ÕO]ES?)\b', text, re.I))
    normalized = text if compiled else normalize_quoted_speech(text)
    # Literal speech can also follow the owner's natural "com a frase ...".
    # Explicit structured sections are handled centrally by the compiler.
    if not compiled and not structured and '<d>' not in normalized:
        cue = re.search(r'\b(?:diz(?:er|endo)?|fal(?:a|ar|ando)|grit(?:a|ar|ando)|narra(?:r|ndo)?|mensagem|fala)\s*(?:(?:a|o)\s+)?(?:(?:seguinte\s+)?(?:frase|mensagem|texto)\s*)?:\s*(.+)', text, re.I | re.S)
        if not cue:
            cue = re.search(r'\b(?:com\s+a\s+frase|(?:dizendo|falando|gritando|cantando)\s+(?:a\s+)?(?:frase|mensagem))\s*(?::\s*|\s+)(.+)', text, re.I | re.S)
        if cue:
            tail = cue.group(1)
            boundary = re.search(r'(?:\n|(?<=[.!?])\s+)(?=(?:pode\s+fazer|fa[çc]a\s+(?:um|o)\s+v[ií]deo|o\s+v[ií]deo|dura[çc][aã]o|c[aâ]mera)\b)', tail, re.I)
            end = cue.start(1) + (boundary.start() if boundary else len(tail))
            utterance = text[cue.start(1):end].strip()
            if utterance:
                normalized = text[:cue.start(1)] + '<d>[Portuguese] ' + utterance + '</d>' + text[end:]
    dialogue = [re.sub(r'^\[[^]]+\]\s*', '', x).strip()
                for x in re.findall(r'<d>(.*?)</d>', normalized, re.S)]
    directions = re.sub(r'<d>.*?</d>', '', normalized, flags=re.S)
    folded = _fold(directions)
    no_audio = bool(re.search(r'\b(?:sem\s+(?:audio|som)|silencioso|mudo)\b',folded))
    no_speech = no_audio or bool(re.search(r'\bsem\s+(?:fala|dialogo|voz)\b',folded))
    if no_speech and dialogue:
        raise ValueError('O pedido contém fala e também pede silêncio. Retire a fala ou a instrução de silêncio antes de gerar.')
    if not compiled and not structured and not no_speech and not dialogue and re.search(r'\b(?:dizendo|falando|narrando|diga|dizer\s+a\s+frase|fala\s*:)',folded):
        raise ValueError('Informe as palavras da fala após Fala: ou entre aspas. As instruções da cena não serão narradas.')
    sound_requested = bool(re.search(r'\b(?:com\s+(?:audio|som)|som\s+ambiente|efeitos\s+sonoros)\b',folded))
    audio = _bool(native_audio) if compiled else (False if no_audio else (_bool(native_audio) or bool(dialogue) or sound_requested))
    words = {'cinco':5,'seis':6,'dez':10,'quinze':15,'vinte':20,'trinta':30}
    duration_match = None if compiled else re.search(
        r'\b(?:video|take|clipe|clip|duracao)\s*(?:unico\s*)?(?:(?:de|com|por|durante)\s*|[:=]\s*)?(\d+(?:[.,]\d+)?|cinco|seis|dez|quinze|vinte|trinta)\s*(?:segundos?|secs?|s)\b',folded)
    if duration_match:
        token=duration_match.group(1)
        duration=words[token] if token in words else float(token.replace(',','.'))
    motion = 'requested'
    if not compiled:
        # Negated locomotion must not add a positive running/walking directive.
        action_text = re.sub(r'\b(?:nao|sem)\s+(?:(?:deve|devem|pode|podem)\s+)?(?:correr|correndo|corra|corram|caminhar|caminhando|andar|andando)\b','',folded)
        if re.search(r'\b(?:correr|correndo|corra|corram|correm|corrida|run|running|sprint|sprinting)\b',action_text): motion='run'
        elif re.search(r'\b(?:caminhar|caminhando|caminhe|caminhem|caminhada|andar|andando|walk|walking)\b',action_text): motion='walk'
    camera = camera_pose or 'Static'
    if not compiled:
        if re.search(r'\b(?:camera\s+(?:fixa|parada|estatica)|fixed\s+camera)\b',folded): camera='Static'
        elif re.search(r'\bcamera\s+(?:acompanha|acompanhe|segue|seguindo|tracks?\b|follows?\b|tracking\b)',folded): camera='Follow Action'
    return {'version':'video_request_v2','prompt':normalized,'dialogue':dialogue,
            'native_audio':audio,'duration_seconds':duration,'duration_from_prompt':bool(duration_match),
            'camera_pose':camera,'motion':motion,'compiled':compiled,
            'summary':('Fala: ' + ' / '.join(dialogue)) if dialogue else ('Som ambiente, sem narrar instruções.' if audio else 'Sem áudio.')}
