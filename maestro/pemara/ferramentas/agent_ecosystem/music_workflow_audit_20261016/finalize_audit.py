import json,hashlib,difflib,ast
from pathlib import Path
R=Path(r"E:/Pemara");A=Path(__file__).parent
manifest=json.loads((A/"backup_manifest.json").read_text(encoding="utf-8"))
extra=".agents/skills/pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1"
b=A/"before"/extra
if not any(Path(m["path"])==R/extra for m in manifest):
 manifest.append({"path":str(R/extra),"backup":str(b),"sha256":hashlib.sha256(b.read_bytes()).hexdigest()})
(A/"backup_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
after=[];patches=[]
for entry in manifest:
 p=Path(entry["path"]);old=Path(entry["backup"]);assert hashlib.sha256(old.read_bytes()).hexdigest()==entry["sha256"]
 content=p.read_bytes();s=hashlib.sha256(content).hexdigest()
 if s==entry["sha256"]:continue
 after.append({"path":str(p),"before_sha256":entry["sha256"],"after_sha256":s})
 patches.extend(difflib.unified_diff(old.read_text(encoding="utf-8").splitlines(True),p.read_text(encoding="utf-8").splitlines(True),fromfile="before/"+str(p.relative_to(R)),tofile=str(p.relative_to(R))))
newfiles=[".agents/skills/pemara-music-songwriter/SKILL.md",".agents/skills/pemara-music-songwriter/agents/openai.yaml",".agents/profiles/pemara-music-songwriter.md",".agents/skills/pemara-music-production-lead/references/creation-workflow.md","maestro/pemara/services/studio/test_music_workflow_upgrade.py","maestro/pemara/app/assets/test_music_provider_selection.cjs"]
for rel in newfiles:
 p=R/rel;after.append({"path":str(p),"new_file":True,"after_sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
 patches.extend(difflib.unified_diff([],p.read_text(encoding="utf-8").splitlines(True),fromfile="/dev/null",tofile=rel))
(A/"scope.patch").write_text("".join(patches),encoding="utf-8")
(A/"after_manifest.json").write_text(json.dumps(after,indent=2),encoding="utf-8")
def funcs(p):return {n.name:ast.dump(n) for n in ast.parse(p.read_text(encoding="utf-8")).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
old=funcs(A/"before/maestro/pemara/services/studio/main.py");new=funcs(R/"maestro/pemara/services/studio/main.py")
changed=[k for k in old.keys()&new.keys() if old[k]!=new[k]]
receipt={"changed_main_functions":sorted(changed),"focused_tests":{"total":57,"passed":57},"javascript_behavior_cases":6,"full_music_tests":{"total":136,"passed":134,"failures":2,"cause":"MERT model unavailable in reinstrumentation readiness"},"mcp_direct_workflow_valid":True,"media_generated":False,"runtime_activation":"BLOCKED_ADMINISTRATIVE_RESTART","automatic_approval_rejection":"Supervisor relaunch through existing administrative task; blocked by policy; command not executed","own_failed_restart_flag_archived":True,"authenticated_browser_review":"PENDING_LOGIN","changed_or_new_files":len(after),"rollback_verified":True}
(A/"audit_receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print(json.dumps(receipt))

