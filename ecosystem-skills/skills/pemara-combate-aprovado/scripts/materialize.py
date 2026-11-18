"""Verify/clone the approved CPU-only baseline. No network or GPU operations."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

EXPECTED = '8f43f0a5bba26ff59482b2a41ad145244aab526e225b4dfa4a9f3d64751992a2'
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify(base):
    path = base / 'assets/workflow_aprovado.api.json'
    if SHA(path) != EXPECTED:
        raise ValueError('Approved workflow hash mismatch')
    graph = json.loads(path.read_text(encoding='utf-8'))
    model = graph['8']['inputs']['model']
    chain = []
    while model:
        node = graph[model[0]]
        chain.append(node['class_type'])
        model = node['inputs'].get('model')
    expected = ['SpectrumApplyMiniMaxH3', 'PemaraH3SageLongSequencePatch',
                'MiniMaxH3MemoryEfficientSageAttentionPatch', 'MiniMaxH3SigmaShift', 'UNETLoader']
    if chain != expected or graph['7']['inputs']['model'] != graph['8']['inputs']['model']:
        raise ValueError('Sampling model chain mismatch')
    if graph['6']['inputs']['length'] != 243 or 'last_frame' in graph['6']['inputs']:
        raise ValueError('Baseline first-frame-only geometry mismatch')
    return graph

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify-only', action='store_true')
    for key in ['out-dir', 'name', 'image', 'identity-file', 'identity-sha256', 'approval-receipt', 'prompt-file']:
        p.add_argument('--' + key)
    p.add_argument('--seed', type=int)
    args = p.parse_args()
    base = Path(__file__).resolve().parents[1]
    graph = verify(base)
    if args.verify_only:
        print(json.dumps({'verified': True, 'baseline_sha256': EXPECTED, 'render_submitted': False}))
        return
    required = ['out_dir', 'name', 'image', 'identity_file', 'identity_sha256', 'approval_receipt']
    if any(not getattr(args, key) for key in required):
        p.error('Cloning requires: ' + ', '.join('--' + x.replace('_', '-') for x in required))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.name):
        p.error('Use a safe alphanumeric candidate name')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.(png|jpg|jpeg|webp)', args.image, flags=re.I):
        p.error('--image must be a basename already uploaded through MCP')
    identity = Path(args.identity_file).resolve(strict=True)
    approval = Path(args.approval_receipt).resolve(strict=True)
    if SHA(identity).lower() != args.identity_sha256.lower():
        raise ValueError('Canonical identity hash mismatch')
    # Receipt existence is provenance only; a human must inspect approval scope.
    approval_data = json.loads(approval.read_text(encoding='utf-8'))
    if not isinstance(approval_data, dict):
        raise ValueError('Approval receipt must be a JSON object')
    if args.seed is not None and not 0 <= args.seed < 2**64:
        p.error('Seed must fit uint64')
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    wf = out / (args.name + '.api.json')
    receipt = out / (args.name + '.receipt.json')
    if wf.exists() or receipt.exists():
        raise FileExistsError('Refusing to overwrite an existing candidate')
    graph = copy.deepcopy(graph)
    graph['5']['inputs']['image'] = args.image
    if args.prompt_file:
        graph['6']['inputs']['prompt'] = Path(args.prompt_file).read_text(encoding='utf-8')
    if args.seed is not None:
        graph['9']['inputs']['noise_seed'] = args.seed
    for key in ['16', 'save240']:
        graph[key]['inputs']['filename_prefix'] = 'combat_candidates/' + args.name + '/' + key
    wf.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding='utf-8')
    receipt.write_text(json.dumps({'baseline_sha256': EXPECTED, 'workflow': str(wf),
        'workflow_sha256': SHA(wf), 'identity': str(identity), 'identity_sha256': SHA(identity),
        'approval_receipt': str(approval), 'approval_scope_requires_review': True,
        'content_kind': 'live_action', 'variant': 'BASE_I2VA_NOT_CONTINUUM',
        'runtime_image_name': args.image, 'render_submitted': False,
        'mcp_validation_required': True, 'owner_video_approved': False}, indent=2), encoding='utf-8')
    print(json.dumps({'workflow': str(wf), 'receipt': str(receipt), 'render_submitted': False}))

if __name__ == '__main__':
    main()
