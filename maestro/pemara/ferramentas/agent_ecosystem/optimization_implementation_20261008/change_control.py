"""Scoped backup and compare-before-write for this implementation."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = Path('E:/Pemara')
SKILLS = ROOT / '.agents/skills'
PROFILES = ROOT / '.agents/profiles'
RECEIPT = BASE / 'changes.json'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return Path(path).read_text(encoding='utf-8-sig')

def put(path, text):
    path = Path(path).resolve()
    roots = [(ROOT, 'pemara'), (Path('C:/Users/admin_remoto/.agents/skills'), 'user_agents'), (Path('C:/Users/admin_remoto/.codex/skills'), 'user_codex')]
    for root, label in roots:
        if path.is_relative_to(root):
            backup = BASE / 'source_before' / label / path.relative_to(root)
            break
    else:
        raise ValueError(f'Outside approved roots: {path}')
    records = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {}
    key = path.as_posix()
    original = path.read_bytes() if path.exists() else None
    new = text.encode('utf-8') if isinstance(text, str) else text
    if original == new:
        return
    current_hash = digest(original) if original is not None else None
    if key in records:
        if current_hash != records[key]['after_sha256']:
            raise RuntimeError(f'Concurrent change detected: {path}')
    else:
        if original is not None:
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                raise RuntimeError(f'Backup already exists without receipt: {backup}')
            backup.write_bytes(original)
            assert digest(backup.read_bytes()) == current_hash
        records[key] = {'before_sha256': current_hash, 'backup': backup.as_posix() if original is not None else None, 'before_bytes': len(original) if original is not None else 0}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(new)
    records[key].update(after_sha256=digest(new), after_bytes=len(new))
    RECEIPT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

def skill(name, description, body):
    put(SKILLS / name / 'SKILL.md', f'---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n{body.strip()}\n')

def alias(name):
    put(PROFILES / f'{name}.md', f'''---
name: {name}
description: "Perfil de compatibilidade da skill {name}; fonte operacional canônica única."
---

# {name} — Agent Turbo alias

<!-- AGENTS_TURBO_ALIAS_V1 -->

1. Leia integralmente `E:/Pemara/.agents/skills/{name}/SKILL.md` antes de atuar.
2. As instruções e referências condicionais vivem na skill; não mantenha uma segunda cópia neste perfil.
3. Preserve o projeto, a stack, o escopo e as aprovações exatas do proprietário.
4. O perfil não cria subagentes, gera mídia ou publica por si só.
''')
