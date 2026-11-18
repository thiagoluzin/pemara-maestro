from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path('E:/Pemara')
HERE = Path(__file__).resolve().parent
SKILLS = ROOT / '.agents/skills'
NAMES = ['pemara-video-production-lead', 'pemara-cinematography-director',
         'pemara-performance-director', 'pemara-film-editor']
existing = ['pemara-cinematic-take-director', 'pemara-video-motion-director',
            'pemara-live-action-showrunner', 'pemara-live-action-continuity',
            'pemara-live-action-combat-director', 'pemara-live-action-kinetic-supervisor',
            'pemara-live-action-qc', 'pemara-voice-performance-director',
            'creative-director', 'video-production', 'pemara-messenger-turbo',
            'pemara-ecosystem-orchestrator']
paths = [ROOT/'AGENTS.md', ROOT/'.agents/README_PEMARA_ECOSYSTEM.md',
         ROOT/'.agents/profiles/agents-turbo.md', ROOT/'.agents/profiles/video-production.md',
         ROOT/'.agents/profiles/creative-director.md',
         SKILLS/'pemara-messenger-turbo/references/turbo_registry.json',
         SKILLS/'pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1',
         SKILLS/'pemara-video-motion-director/references/model-research.md',
         SKILLS/'pemara-cinematic-take-director/references/vejito-liveaction-standard.md']
for name in existing:
    paths.append(SKILLS/name/'SKILL.md')
    paths.extend((SKILLS/name/'agents').glob('*.yaml'))
manifest = []
for path in paths:
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT)
    dst = HERE/'source_before'/rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise RuntimeError(f'Backup already exists: {dst}')
    shutil.copy2(path, dst)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256(dst.read_bytes()).hexdigest() == digest
    manifest.append({'path': str(path), 'backup': str(dst), 'sha256_before': digest})
(HERE/'source_before.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
init = Path('C:/Users/admin_remoto/.codex/skills/.system/skill-creator/scripts/init_skill.py')
labels = [('Produção de vídeo Pemara', 'Planeje cenas e coordene a qualidade da produção'),
          ('Fotografia e câmera Pemara', 'Dirija enquadramento, câmera, luz e profundidade'),
          ('Atuação e performance Pemara', 'Dirija intenção, gestos, reação e peso dos personagens'),
          ('Montagem de filme Pemara', 'Construa ritmo, continuidade e cortes com intenção')]
for name, (label, short) in zip(NAMES, labels):
    args = ['python', str(init), name, '--path', str(SKILLS),
            '--interface', f'display_name={label}', '--interface', f'short_description={short}',
            '--interface', f'default_prompt=Use ${name} para melhorar esta produção de vídeo com decisões concretas e evidências.']
    if name == NAMES[0]:
        args += ['--resources', 'references']
    subprocess.run(args, check=True)
print(f'Backup verificado: {len(manifest)} arquivos. Criadas {len(NAMES)} estruturas de skill.')
