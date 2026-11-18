"""Offline preflight/review evidence CLI. Never renders or approves media."""
from pathlib import Path
import argparse
import json
import sys

workspace = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(workspace/'services/studio'))
from live_action_workflows import compile_live_action_plan
from identity_continuity import validate_candidate_review, validate_research, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--spec', type=Path)
    choice.add_argument('--review', type=Path)
    choice.add_argument('--research', type=Path)
    p.add_argument('--bible', type=Path)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    try:
        if args.research:
            bible = json.loads(args.research.read_text(encoding='utf-8-sig'))
            characters = bible.get('characters')
            if not isinstance(characters, list) or not characters:
                raise ValueError('CHARACTER_RESEARCH_CHARACTERS_REQUIRED')
            for character in characters: validate_research(character)
            result = {'status': 'RESEARCH_RECORD_VALIDATED_NOT_VISUAL_APPROVAL', 'bibleSha256': digest(args.research)}
            passed = True
        elif args.spec:
            spec = json.loads(args.spec.read_text(encoding='utf-8-sig'))
            spec['identityContinuityRequired'] = True
            result = compile_live_action_plan(spec, workspace_root=workspace)
            passed = True
        else:
            if not args.bible: raise ValueError('--bible required with --review')
            result = validate_candidate_review(json.loads(args.review.read_text(encoding='utf-8-sig')), workspace, digest(args.bible))
            passed = result['selectionAllowedByReview']
        result['gpuTouched'] = False
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result = {'status': 'BLOCKED', 'error': str(exc), 'gpuTouched': False}
        passed = False
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': passed, 'report': str(args.report), 'gpuTouched': False}))
    return 0 if passed else 1


if __name__ == '__main__': sys.exit(main())
