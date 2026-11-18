from change_control import *
import re
import subprocess
import sys
import yaml
import tomllib
import zipfile

checks={}; errors=[]
records=json.loads(RECEIPT.read_text(encoding='utf-8'))
for path,r in records.items():
    if digest(Path(path).read_bytes())!=r['after_sha256']: errors.append('changed_since_receipt:'+path)
    if r['backup'] and digest(Path(r['backup']).read_bytes())!=r['before_sha256']: errors.append('backup_mismatch:'+path)
checks['tracked_files']=len(records)
reg=SKILLS/'pemara-messenger-turbo/scripts/audit_turbo_registry.py'
cp=subprocess.run([sys.executable,'-B',str(reg)],capture_output=True,text=True,encoding='utf-8')
checks['registry']=json.loads(cp.stdout)
if cp.returncode: errors.append('registry')
rows=json.loads((BASE/'inventory_after.json').read_text(encoding='utf-8-sig'))
checks['curated_skills']=len(rows)
checks['curated_valid']=sum(x['Status']=='valid' for x in rows)
checks['curated_metadata']=sum(x['HasOpenAIYaml'] for x in rows)
if any(x['Status']!='valid' or not x['HasOpenAIYaml'] for x in rows): errors.append('curated_inventory')
skill_dirs={p.parent for p in map(Path,records) if p.name=='SKILL.md'}
skill_dirs.update(SKILLS/x['Skill'] for x in rows)
validator='C:/Users/admin_remoto/.codex/skills/.system/skill-creator/scripts/quick_validate.py'
for p in sorted(skill_dirs):
    n=p.name
    cp=subprocess.run([sys.executable,'-B',validator,str(p)],capture_output=True,text=True,encoding='utf-8')
    if cp.returncode: errors.append('skill:'+n+':'+cp.stdout+cp.stderr)
    meta=p/'agents/openai.yaml'
    if meta.exists():
        m=yaml.safe_load(read(meta)); i=m.get('interface',{})
        if not 25<=len(i.get('short_description',''))<=64: errors.append('metadata_length:'+n)
        if '$'+n not in i.get('default_prompt',''): errors.append('metadata_prompt:'+n)

# Markdown links in changed files. Inline code paths to real references are
# checked only when they are explicit file references, not template examples.
broken=[]
for path in records:
    p=Path(path)
    if p.suffix!='.md': continue
    for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',read(p)):
        if re.match(r'https?://|#|app:|codex:',target): continue
        target=target.strip('<>').split('#')[0]
        if not target or any(c in target for c in ['<','>','{','*']): continue
        q=Path(target) if re.match(r'^[A-Z]:[/\\]',target,re.I) else p.parent/target
        if not q.exists(): broken.append({'file':path,'target':target})
checks['broken_markdown_links']=broken
if broken: errors.append('broken_links')
discovery=json.loads(read(BASE/'discovery_receipt.json'))
config=tomllib.loads(Path('C:/Users/admin_remoto/.codex/config.toml').read_text(encoding='utf-8-sig'))
entries=config.get('skills',{}).get('config',[])
checks['disabled_duplicate_entries']=sum(any(e.get('path')==p and e.get('enabled') is False for e in entries) for p in discovery['disabled_paths'])
if checks['disabled_duplicate_entries']!=11: errors.append('discovery_overrides')
archive=Path(discovery['archive'])
if digest(archive.read_bytes())!=discovery['archive_sha256']: errors.append('duplicate_archive_hash')
with zipfile.ZipFile(archive) as z:
    checks['duplicate_archive_crc_ok']=z.testzip() is None
    checks['duplicate_archive_member_hashes_ok']=all(digest(z.read(r['archive_member']))==r['sha256'] for r in discovery['files'])
if not checks['duplicate_archive_crc_ok'] or not checks['duplicate_archive_member_hashes_ok']: errors.append('duplicate_archive_contents')
checks['validated_skill_directories']=len(skill_dirs)
five=['project-planner','debugger','performance-optimizer','phaser-platformer-architect','phaser-16bit-platformer']
checks['entrypoint_bytes']={n:{'before':records[(SKILLS/n/'SKILL.md').as_posix()]['before_bytes'],'after':(SKILLS/n/'SKILL.md').stat().st_size} for n in five}
checks['errors']=errors
(BASE/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
sys.exit(bool(errors))
