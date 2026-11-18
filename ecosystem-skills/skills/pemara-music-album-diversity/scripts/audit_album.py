"""Triage written album plans; never evaluates performed audio or artistic quality."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import unicodedata


def normalized(value: object) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if not isinstance(value, str):
        return ''
    value = re.sub(r'\[[^\]]*\]', ' ', value)
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', value).casefold()))


def shingles(text: str, size: int = 5) -> set[tuple[str, ...]]:
    words = text.split()
    if len(words) < size:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def signature(value: object) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return ' '.join(value.casefold().split()) if isinstance(value, str) else ''


def audit(plan: dict, lyric_threshold: float = .75) -> dict:
    if not 0 < lyric_threshold <= 1:
        raise ValueError('lyric_threshold must be in (0, 1]')
    tracks = plan.get('tracks')
    if not isinstance(tracks, list) or not tracks:
        raise ValueError('tracks must be a nonempty list')
    ids = [str(t.get('id', '')).strip() for t in tracks if isinstance(t, dict)]
    if len(ids) != len(tracks) or any(not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Every track needs a unique nonempty id')
    dimensions = ('riff_signature', 'rhythm_signature', 'form', 'vocal_phrasing')
    normalized_tracks, missing = [], []
    for t in tracks:
        arrangement = t.get('arrangement', {})
        if not isinstance(arrangement, dict):
            raise ValueError('arrangement must be an object')
        fields = {key: normalized(t.get(key)) for key in ('lyrics', 'hook')}
        fields.update({key: signature(arrangement.get(key)) for key in dimensions})
        fields['id'] = str(t['id'])
        normalized_tracks.append(fields)
        absent = [key for key, value in fields.items() if key != 'id' and not value]
        if absent:
            missing.append({'id': str(t['id']), 'fields': absent})
    pairs = []
    for a, b in itertools.combinations(normalized_tracks, 2):
        sa, sb = shingles(a['lyrics']), shingles(b['lyrics'])
        similarity = len(sa & sb) / len(sa | sb) if sa and sb else None
        equal = [key for key in ('hook', *dimensions) if a[key] and a[key] == b[key]]
        reasons = []
        if a['lyrics'] and a['lyrics'] == b['lyrics']:
            reasons.append('EXACT_LYRICS')
        elif similarity is not None and similarity >= lyric_threshold:
            reasons.append('SIMILAR_LYRIC_SHINGLES')
        if 'hook' in equal:
            reasons.append('EXACT_HOOK')
        if 'riff_signature' in equal and len(set(equal) & set(dimensions)) >= 2:
            reasons.append('SHARED_RIFF_AND_ARRANGEMENT_DIMENSION')
        if reasons:
            pairs.append({'ids': [a['id'], b['id']], 'reasons': reasons,
                          'equal_fields': equal, 'lyric_shingle_similarity': similarity})
    return {'tracks': len(tracks), 'review_pairs': pairs, 'missing_evidence': missing,
            'status': 'REVIEW_REQUIRED' if pairs or missing else 'NO_PLAN_FLAGS',
            'threshold_is_heuristic': True, 'lyric_threshold': lyric_threshold,
            'audio_listened': False, 'artistic_approval': False,
            'limitation': 'Text/signature comparison only. Does not verify performed riffs, transposition, singing or album quality.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--lyric-threshold', type=float, default=.75)
    args = parser.parse_args()
    if args.plan.resolve() == args.out.resolve():
        parser.error('Output must not overwrite the source plan')
    data = args.plan.read_bytes()
    result = audit(json.loads(data), args.lyric_threshold)
    result['source_sha256'] = hashlib.sha256(data).hexdigest()
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'review_pairs': len(result['review_pairs']),
                      'missing_tracks': len(result['missing_evidence'])}))


if __name__ == '__main__':
    main()
