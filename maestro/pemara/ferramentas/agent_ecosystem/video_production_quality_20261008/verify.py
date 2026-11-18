from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import yaml

ROOT = Path('E:/Pemara')
HERE = Path(__file__).resolve().parent
before = json.loads((HERE/'source_before.json').read_text(encoding='utf-8'))
errors = []
changed = []
for item in before:
    path, backup = Path(item['path']), Path(item['backup'])
    if hashlib.sha256(backup.read_bytes()).hexdigest() != item['sha256_before']:
        errors.append(f'Backup hash mismatch: {backup}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item['sha256_before']:
        changed.append({**item, 'sha256_after': digest})

metadata_path = ROOT/'maestro/pemara/services/studio/h3_workflow.py'
old_metadata = (HERE/'source_before/maestro/pemara/services/studio/h3_workflow.py').read_text(encoding='utf-8-sig')
new_metadata = metadata_path.read_text(encoding='utf-8-sig')
metadata_start, metadata_end = 'WORKFLOW_SKILLS = (', '\ndef _agents_root'
runtime_functions_unchanged = (
    old_metadata[:old_metadata.index(metadata_start)] == new_metadata[:new_metadata.index(metadata_start)]
    and old_metadata[old_metadata.index(metadata_end):] == new_metadata[new_metadata.index(metadata_end):]
)
if not runtime_functions_unchanged:
    errors.append('H3 change extended outside catalogue/stage metadata')

names = ['pemara-video-production-lead', 'pemara-cinematography-director',
         'pemara-performance-director', 'pemara-film-editor']
new_files = []
for name in names:
    base = ROOT/'.agents/skills'/name
    for path in sorted(base.rglob('*')):
        if path.is_file():
            new_files.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    profile = ROOT/'.agents/profiles'/f'{name}.md'
    new_files.append({'path': str(profile), 'sha256': hashlib.sha256(profile.read_bytes()).hexdigest()})
    interface = yaml.safe_load((base/'agents/openai.yaml').read_text(encoding='utf-8'))['interface']
    if not 25 <= len(interface['short_description']) <= 64:
        errors.append(f'Invalid short description length: {name}')
    if f'${name}' not in interface['default_prompt']:
        errors.append(f'Missing skill invocation in prompt: {name}')

for rel in ['.agents/skills/pemara-cinematic-take-director/references/production-gates.md',
            '.agents/skills/pemara-video-motion-director/references/motion-quality-gates.md']:
    path = ROOT/rel
    new_files.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

skill_names = sorted({Path(item['path']).parent.name for item in changed
                      if Path(item['path']).name == 'SKILL.md'} | set(names))
validation = []
validator = Path('C:/Users/admin_remoto/.codex/skills/.system/skill-creator/scripts/quick_validate.py')
for name in skill_names:
    path = ROOT/'.agents/skills'/name
    result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True, encoding='utf-8')
    validation.append({'skill': name, 'exit_code': result.returncode, 'output': result.stdout.strip()+result.stderr.strip()})
    if result.returncode:
        errors.append(f'Skill validation failed: {name}')
    text = (path/'SKILL.md').read_text(encoding='utf-8')
    if '[TODO' in text:
        errors.append(f'Unfinished initializer: {name}')
    for ref in re.findall(r'`(references/[\w./-]+\.md)`', text):
        if not (path/ref).is_file():
            errors.append(f'Missing progressive reference: {name}/{ref}')

registry = subprocess.run([sys.executable, str(ROOT/'.agents/skills/pemara-messenger-turbo/scripts/audit_turbo_registry.py')],
                          capture_output=True, text=True, encoding='utf-8')
registry_report = json.loads(registry.stdout)
if registry.returncode:
    errors.extend(registry_report['errors'])
inventory = json.loads((HERE/'inventory.json').read_text(encoding='utf-8-sig'))
if isinstance(inventory, dict):
    inventory = [inventory]
invalid = [row['Skill'] for row in inventory if row['Status'] != 'valid']
if invalid:
    errors.append(f'Invalid inventory skills: {invalid}')

report = {'ok': not errors, 'errors': errors, 'scope': 'Local agent/skill instructions, routing and H3 catalogue/stage metadata',
          'media_generated': False, 'gpu_jobs_submitted': False, 'backend_metadata_changed': True,
          'generation_runtime_functions_unchanged': runtime_functions_unchanged,
          'studio_restarted': False,
          'human_artistic_approval_inferred': False,
          'backup_files_verified': len(before), 'existing_files_changed': len(changed),
          'new_files': len(new_files), 'changed_skill_validation': validation,
          'inventory_total': len(inventory), 'inventory_invalid': invalid, 'registry': registry_report}
(HERE/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(HERE/'file_changes.json').write_text(json.dumps({'changed': changed, 'new': new_files}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: report[key] for key in ['ok', 'errors', 'backup_files_verified', 'existing_files_changed', 'new_files',
                                             'inventory_total', 'inventory_invalid']}, ensure_ascii=False, indent=2))
print(f'Skills alteradas/criadas validadas: {len(validation)}. Registro: {registry_report["aliases"]} aliases, {registry_report["specialized_profiles"]} especializações.')
sys.exit(0 if not errors else 1)
