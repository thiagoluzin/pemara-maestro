import json,hashlib,shutil
from pathlib import Path
R=Path(r"E:/Pemara");A=Path(r"E:/Pemara/maestro/pemara/ferramentas/agent_ecosystem/music_workflow_audit_20261016");A.mkdir(parents=True,exist_ok=True)
files=["AGENTS.md","maestro/pemara/app/assets/maestro.js","maestro/pemara/app/assets/maestro-build.json","maestro/pemara/app/index.html","maestro/pemara/services/studio/main.py","maestro/pemara/services/studio/music_creation.py","maestro/pemara/services/studio/music_writer.py",".agents/skills/pemara-music-production-lead/SKILL.md",".agents/skills/pemara-music-production-lead/references/music-production-contract.md",".agents/skills/pemara-music-arranger/SKILL.md",".agents/skills/pemara-music-mix-engineer/SKILL.md",".agents/skills/pemara-music-listening-qc/SKILL.md",".agents/skills/pemara-messenger-turbo/references/turbo_registry.json",".agents/skills/pemara-messenger-turbo/references/routing-map.md",".agents/skills/pemara-music-production-lead/agents/openai.yaml"]
manifest=[]
for rel in files:
 src=R/rel;dest=A/"before"/rel
 if dest.exists():raise RuntimeError("Backup already exists; do not overwrite "+str(dest))
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
 digest=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 manifest.append({"path":str(src),"backup":str(dest),"sha256":digest})
(A/"backup_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("verified backups",len(manifest))

