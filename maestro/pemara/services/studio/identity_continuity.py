"""Local identity evidence checks. No GPU, service calls or artistic approval."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class IdentityContinuityError(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def artifact(item, root):
    if not isinstance(item, dict) or not item.get('path') or not item.get('sha256'):
        raise IdentityContinuityError('IDENTITY_ARTIFACT_REQUIRED')
    path = (Path(root) / item['path']).resolve()
    if not path.is_file() or digest(path) != str(item['sha256']).lower():
        raise IdentityContinuityError('IDENTITY_ARTIFACT_MISSING_OR_CHANGED: ' + str(path))
    return path


def _state(value):
    if not isinstance(value, dict):
        raise IdentityContinuityError('IDENTITY_STATE_REQUIRED')
    for key in ('dirt', 'wetness'):
        if type(value.get(key)) is not int or not 0 <= value[key] <= 3:
            raise IdentityContinuityError('IDENTITY_STATE_LEVEL_0_TO_3: ' + key)
    if not isinstance(value.get('damage'), list) or any(not isinstance(x, str) or not x.strip() for x in value['damage']):
        raise IdentityContinuityError('IDENTITY_DAMAGE_LIST_REQUIRED')


def validate_research(char):
    if char.get('origin') not in {'existing', 'original'}:
        raise IdentityContinuityError('CHARACTER_ORIGIN_REQUIRED')
    if char['origin'] == 'original':
        return
    research = char.get('research', {})
    if research.get('status') != 'REVIEWED' or not research.get('version') or not research.get('reviewer'):
        raise IdentityContinuityError('CHARACTER_RESEARCH_BEFORE_ANCHORS_REQUIRED')
    sources = research.get('sources', [])
    if not sources or any(not all(s.get(k) for k in ('id', 'url', 'title', 'accessedAt', 'versionScope')) for s in sources):
        raise IdentityContinuityError('CHARACTER_RESEARCH_SOURCES_REQUIRED')
    if not any(s.get('kind') == 'primary' for s in sources) and not research.get('primaryUnavailableReason'):
        raise IdentityContinuityError('CHARACTER_RESEARCH_PRIMARY_SOURCE_REQUIRED')
    if research.get('blockingUnknowns') != []:
        raise IdentityContinuityError('CHARACTER_RESEARCH_UNRESOLVED_VERSION_OR_DETAILS')
    source_ids = {s['id'] for s in sources}
    facts = research.get('facts', {})
    for topic in ('appearance', 'wardrobeMaterials', 'combatMechanics', 'powersAndLimits', 'personalityAndMovement'):
        fact = facts.get(topic, {})
        if not fact.get('summary') or not fact.get('sourceIds') or not set(fact['sourceIds']).issubset(source_ids):
            raise IdentityContinuityError('CHARACTER_RESEARCH_TOPIC_WITH_SOURCES_REQUIRED: ' + topic)
    adaptations = research.get('adaptations')
    if not isinstance(adaptations, list) or any(not a.get('change') or not a.get('ownerDirection') for a in adaptations):
        raise IdentityContinuityError('CHARACTER_ADAPTATIONS_MUST_BE_EXPLICIT')


def compile_identity_continuity(contract, root, character_ids, anchors):
    if not isinstance(contract, dict):
        raise IdentityContinuityError('IDENTITY_CONTINUITY_REQUIRED')
    bible_path = artifact(contract.get('bible'), root)
    bible = json.loads(bible_path.read_text(encoding='utf-8-sig'))
    if bible.get('schemaVersion') != 'pemara-character-bible@1':
        raise IdentityContinuityError('IDENTITY_BIBLE_VERSION')
    characters = bible.get('characters')
    if not isinstance(characters, list) or not characters:
        raise IdentityContinuityError('IDENTITY_CHARACTERS_REQUIRED')
    by_id = {c.get('id'): c for c in characters}
    if len(by_id) != len(characters) or not set(character_ids).issubset(by_id):
        raise IdentityContinuityError('IDENTITY_CHARACTER_SET_MISMATCH')
    states = contract.get('states', {})
    if set(states) != set(character_ids):
        raise IdentityContinuityError('IDENTITY_STATE_CHARACTER_SET_MISMATCH')
    lines = ['[FIXED CHARACTER IDENTITY]']
    for cid in sorted(character_ids):
        char = by_id[cid]
        validate_research(char)
        invariants = char.get('invariants')
        if not isinstance(invariants, list) or not invariants or any(not isinstance(x, str) or not x.strip() for x in invariants):
            raise IdentityContinuityError('IDENTITY_INVARIANTS_REQUIRED: ' + cid)
        refs = char.get('references', [])
        if not refs:
            raise IdentityContinuityError('IDENTITY_REFERENCE_REQUIRED: ' + cid)
        for ref in refs:
            artifact(ref, bible_path.parent)
            if ref.get('role') != 'canonical' or ref.get('ownerApproved') is not True or not ref.get('approvalEvidence'):
                raise IdentityContinuityError('IDENTITY_CANONICAL_APPROVAL_REQUIRED: ' + cid)
        state = states[cid]
        for phase in ('entry', 'exit'):
            _state(state.get(phase))
        entry, end = state['entry'], state['exit']
        if (end['dirt'] < entry['dirt'] or end['wetness'] < entry['wetness'] or not set(entry['damage']).issubset(end['damage'])) and not str(state.get('physicalChangeReason', '')).strip():
            raise IdentityContinuityError('IDENTITY_UNEXPLAINED_CLEANUP_OR_HEALING: ' + cid)
        lines += [cid + ': ' + '; '.join(invariants), 'Persistent state: ' + json.dumps(state, ensure_ascii=False, sort_keys=True)]
    previous = contract.get('previousState')
    if previous is not None:
        previous_path = artifact(previous, root)
        prior = json.loads(previous_path.read_text(encoding='utf-8-sig'))
        for cid in character_ids:
            if prior.get(cid) != states[cid]['entry']:
                raise IdentityContinuityError('IDENTITY_ENTRY_DOES_NOT_MATCH_PREVIOUS_EXIT: ' + cid)
    elif contract.get('firstTake') is not True:
        raise IdentityContinuityError('IDENTITY_PREVIOUS_STATE_REQUIRED')
    review = contract.get('anchorReview', {})
    if review.get('status') != 'PASS' or not str(review.get('reviewer', '')).strip() or not str(review.get('notes', '')).strip():
        raise IdentityContinuityError('IDENTITY_ANCHOR_VISUAL_REVIEW_REQUIRED')
    if review.get('bibleSha256', '').lower() != digest(bible_path):
        raise IdentityContinuityError('IDENTITY_ANCHOR_REVIEW_STALE_BIBLE')
    reviewed = review.get('artifacts', [])
    expected = {str(a.get('sha256', '')).lower() for a in anchors}
    actual = {str(a.get('sha256', '')).lower() for a in reviewed}
    if not expected or actual != expected:
        raise IdentityContinuityError('IDENTITY_ANCHOR_REVIEW_SCOPE_MISMATCH')
    for a in reviewed:
        artifact(a, root)
    block = '\n'.join(lines)
    return {'status': 'EVIDENCE_VALIDATED_NOT_ARTISTIC_APPROVAL', 'fixedPromptBlock': block,
            'fixedPromptSha256': hashlib.sha256(block.encode()).hexdigest(),
            'bibleSha256': digest(bible_path), 'exitState': {cid: states[cid]['exit'] for cid in character_ids},
            'visualReviewRequiredAfterRender': True, 'gpuTouched': False}


def validate_candidate_review(review, root, bible_sha256):
    """Require explicit, artifact-bound observations; never run a visual classifier."""
    artifact(review.get('candidate'), root)
    if review.get('bibleSha256') != bible_sha256 or not review.get('reviewer'):
        raise IdentityContinuityError('IDENTITY_CANDIDATE_REVIEW_STALE_OR_UNSIGNED')
    observations = review.get('observations', [])
    if {x.get('phase') for x in observations} != {'start', 'middle', 'end'} or len(observations) != 3:
        raise IdentityContinuityError('IDENTITY_CANDIDATE_THREE_PHASES_REQUIRED')
    for observation in observations:
        if not observation.get('notes') or not isinstance(observation.get('timestampSeconds'), (float, int)) or observation['timestampSeconds'] < 0:
            raise IdentityContinuityError('IDENTITY_CANDIDATE_OBSERVATION_REQUIRED')
    dimensions = ('identity', 'combat', 'physics', 'lighting', 'water', 'realism')
    verdicts = review.get('dimensions', {})
    if any(verdicts.get(k) not in {'PASS', 'FAIL', 'PENDING', 'NOT_APPLICABLE'} for k in dimensions):
        raise IdentityContinuityError('IDENTITY_SEPARATE_REVIEW_DIMENSIONS_REQUIRED')
    if verdicts['identity'] not in {'PASS', 'FAIL', 'PENDING'}:
        raise IdentityContinuityError('IDENTITY_CANNOT_BE_NOT_APPLICABLE')
    return {'selectionAllowedByReview': review.get('fullPlaybackAndContactsReviewed') is True and all(v in {'PASS', 'NOT_APPLICABLE'} for v in verdicts.values()),
            'ownerApprovalInferred': False, 'dimensions': verdicts}
