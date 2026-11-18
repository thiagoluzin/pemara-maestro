"""Read-only inventory of skill sources; writes evidence beside this script."""
import hashlib
import difflib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOTS = [Path('E:/Pemara/.agents/skills'), Path('C:/Users/admin_remoto/.agents/skills'), Path('C:/Users/admin_remoto/.codex/skills')]
rows = []
protocols = defaultdict(list)
for root in ROOTS:
    for path in sorted(root.rglob('SKILL.md')):
        data = path.read_bytes()
        text = data.decode('utf-8-sig')
        match = re.search(r'^name:\s*(.+)$', text, re.M)
        row = {'path': path.as_posix(), 'root': root.as_posix(), 'name': match.group(1).strip().strip('"\'') if match else path.parent.name, 'bytes': len(data), 'lines': len(text.splitlines()), 'sha256': hashlib.sha256(data).hexdigest(), 'metadata': (path.parent / 'agents/openai.yaml').is_file(), 'nested': path.parent.parent != root}
        rows.append(row)
        block = re.search(r'<!--[^\n]*TURBO ENGINE v2.*?<!--[^\n]*-->', text, re.S)
        if block:
            normalized = block.group().replace('\r\n', '\n')
            protocols[hashlib.sha256(normalized.encode()).hexdigest()].append({'path': path.as_posix(), 'chars': len(normalized)})

names = defaultdict(list)
hashes = defaultdict(list)
for row in rows:
    names[row['name']].append(row)
    hashes[row['sha256']].append(row['path'])

registry_path = ROOTS[0] / 'pemara-messenger-turbo/references/turbo_registry.json'
registry = json.loads(registry_path.read_text(encoding='utf-8'))
profile_root = Path(registry['profile_root'])
profile_comparisons = []
for name in registry['specialized_profiles']:
    skill_lines = (ROOTS[0] / name / 'SKILL.md').read_text(encoding='utf-8').splitlines()
    profile_lines = (profile_root / f'{name}.md').read_text(encoding='utf-8').splitlines()
    comparison = difflib.SequenceMatcher(None, skill_lines, profile_lines)
    profile_comparisons.append({
        'name': name,
        'line_similarity': round(comparison.ratio(), 3),
        'profile_lines_not_matched': sum(j2-j1 for tag,i1,i2,j1,j2 in comparison.get_opcodes() if tag != 'equal'),
        'diff': list(difflib.unified_diff(profile_lines, skill_lines, fromfile='profile', tofile='skill', n=2)),
    })
report = {
    'scope': 'Filesystem sources in three roots; plugin caches excluded; discovery precedence and actual token usage not measured.',
    'roots': [{'path': root.as_posix(), 'recursive_skill_files': sum(row['root'] == root.as_posix() for row in rows), 'direct_skill_files': sum(row['root'] == root.as_posix() and not row['nested'] for row in rows)} for root in ROOTS],
    'profile_files': len(list(profile_root.glob('*.md'))),
    'aliases': len(registry['aliases']),
    'specialized_profiles': len(registry['specialized_profiles']),
    'profile_comparisons': profile_comparisons,
    'same_name_groups': [{'name': name, 'exact_same_bytes': len({item['sha256'] for item in items}) == 1, 'files': items} for name, items in names.items() if len(items) > 1],
    'exact_duplicate_groups': [paths for paths in hashes.values() if len(paths) > 1],
    'turbo_blocks': [{'sha256': digest, 'copies': len(items), 'chars_each': items[0]['chars'], 'files': [item['path'] for item in items]} for digest, items in protocols.items()],
    'skills': rows,
}
output = Path(__file__).with_name('inventory.json')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({
    'roots': report['roots'], 'profile_files': report['profile_files'],
    'same_names': [{'name': group['name'], 'copies': len(group['files']), 'identical': group['exact_same_bytes']} for group in report['same_name_groups']],
    'exact_duplicate_groups': report['exact_duplicate_groups'],
    'turbo_blocks': [{'copies': group['copies'], 'chars_each': group['chars_each']} for group in report['turbo_blocks']],
    'output': output.as_posix()
}, ensure_ascii=False, indent=2))
