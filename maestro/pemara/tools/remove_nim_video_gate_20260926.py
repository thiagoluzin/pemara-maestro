from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT/'backups/remove_nim_video_gate_20260926'
CHANGED=[]
def update(path,transform):
    path=Path(path);before=path.read_text(encoding='utf-8-sig');after=transform(before)
    if before==after:return
    rel=path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path('skills')/path.name
    dest=BACKUP/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
    path.write_text(after,encoding='utf-8');CHANGED.append(str(path))
def main_edit(s):
    start=s.index('@app.post("/api/generative/anchor-intelligence/analyze")')
    end=s.index('@app.get("/api/generative/status")',start)
    s=s[:start]+'''@app.post("/api/generative/anchor-intelligence/analyze")
async def generative_anchor_intelligence_analyze(request: Request):
    """Retired endpoint: never reads or sends an image to an external provider."""
    if not _is_internal_request(request):
        return _public_forbidden()
    return JSONResponse(status_code=410, content={
        "ok": False, "code": "EXTERNAL_ANCHOR_ANALYSIS_REMOVED",
        "erro": "Analise externa de ancora removida. Use a foto aprovada e a direcao de movimento.",
    })


'''+s[end:]
    s=s.replace('        _require_anchor_analysis_receipt(contract)\n','').replace('        _register_compiled_anchor_receipt(contract, compiled)\n','')
    start=s.index('        normalized_mode = (mode or "").lower().strip()',s.index('async def generative_chat('))
    end=s.index('        return _run_generative(',start)
    s=s[:start]+s[end:]
    start=s.index('        if base_bytes is not None and (spec.get("anchor_contract_id")',s.index('def _start_generative_job('))
    end=s.index('        readiness = engine.readiness()',start)
    s=s[:start]+s[end:]
    return s
update(ROOT/'services/studio/main.py',main_edit)
def integration_edit(s):
    a=s.index('        if inputs.get("base_bytes"):',s.index('    def prepare('))
    b=s.index('        return ns["_normalize_generative_job_spec"](spec)',a)
    return s[:a]+'''        # Local prompt compilation is optional; approved images need no external receipt.
        compiled = bindings.get("compiled_prompt")
        if compiled:
            spec = {**spec, "prompt": str(compiled), "negative": str(bindings.get("compiled_negative", ""))}
'''+s[b:]
update(ROOT/'services/studio/creative_os/integration.py',integration_edit)
update(ROOT/'app/index.html',lambda s:re.sub(r'            <section class="gen-anchor-intelligence.*?</section>\n\n','',s,count=1,flags=re.S))
def js_edit(s):
    a=s.index('function clearAnchorIntelligence(');b=s.index('function renderVideoEnginePicker()',a);s=s[:a]+s[b:]
    a=s.index('async function analyzeAnchorIntelligence()');b=s.index('async function runGen(event)',a);s=s[:a]+s[b:]
    s=re.sub(r'  \$\("#gen-anchor-external-consent"\).*?\n  \}\);\n','',s,count=1,flags=re.S)
    s='\n'.join(line for line in s.split('\n') if not any(token in line for token in ('clearAnchorIntelligence(', '#gen-anchor-', '#gen-prompt-compiler-version','anchorContract: null','compiledAnchorPrompt: null')))
    return s
update(ROOT/'app/assets/maestro.js',js_edit)
for rel in ('ferramentas/video_global_engine/policies/primary_take_orchestration_h3_ltx25.json','ferramentas/video_global_engine/templates/studio_video_model_registry.json'):
    def policy_edit(s):
        v=json.loads(s);v.pop('anchor_intelligence',None)
        v['anchor_approval']={'authority':'owner','external_analysis_required':False,'external_analysis_enabled':False,'preserve_approved_reference':True,'technical_qc_and_video_review_required':True}
        if 'gates' in v:v['gates']=['owner_anchor_approval' if x=='anchor_contract_receipt' else x for x in v['gates']]
        v['updated_at']='2026-09-26'
        return json.dumps(v,ensure_ascii=False,indent=2)+'\n'
    update(ROOT/rel,policy_edit)
for rel in ('ferramentas/video_global_engine/templates/editorial_import_queue.template.json','ferramentas/video_global_engine/templates/take_queue.template.json','services/studio/video_projects.py','ferramentas/video_global_engine/tools/unimedia_editorial_bridge.py'):
    update(ROOT/rel,lambda s:s.replace('anchor_intelligence_contract_v1','identity_locked').replace('h3_ltx25_anchor_intelligence_rife60_human_qc_assembly','h3_ltx25_owner_approved_anchor_rife60_human_qc_assembly'))
skill=Path('E:/Pemara/.agents/skills/pemara-cinematic-take-director/SKILL.md')
def skill_edit(s):
    a=s.index('### Anchor Intelligence do Maestro');b=s.index('## Regra antirremendo',a)
    return s[:a]+'''### Foto aprovada pelo proprietário — 2026-09-26

Direção expressa: remover a análise NVIDIA NIM do workflow e do Maestro.
A foto aprovada pelo proprietário é a referência visual. Não solicitar chave externa,
consentimento de análise ou recibo NVIDIA para liberar I2V. Preservar a imagem original,
hash, escopo de aprovação, identidade e direção de movimento. Validar o grafo e a
admissão GPU pelo MCP; conferir o vídeo gerado e obter sua avaliação artística.
Aprovar foto não aprova automaticamente o vídeo ou a montagem.

'''+s[b:]
update(skill,skill_edit)
update(skill.parent/'references/anchor-intelligence-contract.md',lambda s:'''# Foto aprovada como referência — 2026-09-26

Este contrato substitui a exigência anterior de análise externa NVIDIA NIM por direção
expressa do proprietário: "RANCA ISSO DO WORKFLOW E DO MAESTRO".

1. Preservar a imagem aprovada, seu hash e o escopo de aprovação.
2. Descrever a ação e a câmera sem reescrever a identidade aprovada.
3. Compilar localmente o prompt para o motor escolhido, quando necessário.
4. Validar o grafo e a admissão GPU pelo MCP, mantendo SageAttention no H3.
5. Conferir continuidade, física e materiais no vídeo real.
6. Avaliação artística e aprovação de montagem continuam pertencendo ao proprietário.

Não há envio ao NVIDIA NIM, credencial externa ou recibo de análise no caminho I2V.
''')
update(ROOT/'ferramentas/video_global_engine/docs/decisions/ADR-006-h3-ltx25-anchor-intelligence-turbo.md',lambda s:'# Atualização vinculante — 2026-09-26\n\nA exigência de Anchor Intelligence/NVIDIA NIM foi removida por ordem do proprietário. Foto aprovada é a referência visual; não exige análise externa nem recibo. Permanecem seleção de motor, identidade, MCP/SageAttention, QC técnico e avaliação artística do vídeo. O texto abaixo é histórico e não rege mais a análise de âncoras.\n\n'+s)
project=ROOT/'ferramentas/video_global_engine/projetos/yuna_sending_kilika_liveaction_115s_v1'
update(project/'tools/prepare_plan.py',lambda s:s.replace("'anchorIntelligence':'EXPLICIT_EXTERNAL_CONSENT_REQUIRED'","'anchorIntelligence':'REMOVED_BY_OWNER_DIRECTION'"))
for name in ('analyze_t01.py','analyze_t01_local.py'):
    update(project/'tools'/name,lambda s:'"""Retired: owner removed external image analysis from this production."""\nraise SystemExit("NVIDIA anchor analysis removed by owner direction; use approved reference.")\n')
print(json.dumps({'changed':CHANGED,'backup':str(BACKUP)},indent=2))
