from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('E:/Pemara')
HERE = Path(__file__).resolve().parent
path = ROOT/'maestro/pemara/services/studio/h3_workflow.py'
backup = HERE/'source_before/maestro/pemara/services/studio/h3_workflow.py'
backup.parent.mkdir(parents=True, exist_ok=True)
if backup.exists():
    raise RuntimeError('Metadata backup already exists')
shutil.copy2(path, backup)
digest = hashlib.sha256(path.read_bytes()).hexdigest()
assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
manifest = json.loads((HERE/'source_before.json').read_text(encoding='utf-8'))
manifest.append({'path': str(path), 'backup': str(backup), 'sha256_before': digest})
(HERE/'source_before.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
text = path.read_text(encoding='utf-8-sig')
start, end = text.index('WORKFLOW_SKILLS = ('), text.index('\ndef _agents_root')
block = text[start:end]

def replace(old, new):
    global block
    if block.count(old) != 1:
        raise RuntimeError(f'Expected one metadata occurrence: {old[:90]}')
    block = block.replace(old, new)

replace('WORKFLOW_SKILLS = (', '''WORKFLOW_SKILLS = (
    ("pemara-video-production-lead", "sequence_production_and_artistic_review"),
    ("pemara-cinematography-director", "blocking_camera_lighting_and_visual_readability"),
    ("pemara-performance-director", "playable_intention_acting_reaction_and_recovery"),
    ("pemara-film-editor", "approved_source_selection_rhythm_and_causal_cuts"),''')
replace('"label": "Roteiro e contrato de takes",', '"label": "Producao, roteiro e direcao dos takes",')
replace('"agents": ["pemara-live-action-showrunner", "pemara-live-action-combat-director", "pemara-live-action-kinetic-supervisor", "project-planner", "creative-director", "pemara-cinematic-take-director"],',
        '"agents": ["pemara-video-production-lead", "pemara-cinematic-take-director", "pemara-performance-director", "pemara-cinematography-director", "pemara-film-editor", "pemara-live-action-showrunner", "pemara-live-action-combat-director", "pemara-live-action-kinetic-supervisor", "project-planner", "creative-director"],')
replace('"output": "roteiro, take queue, continuidade e beats 0-30/30-70/70-100",',
        '"output": "intencao, sequencia causal, atuacao, fotografia, cobertura, continuidade, cortes e beats 0-30/30-70/70-100; carregar especialistas por fase",')
replace('"agents": ["image-production", "pemara-cinematic-take-director"],',
        '"agents": ["image-production", "pemara-cinematography-director", "pemara-cinematic-take-director"],')
replace('"agents": ["creative-director", "pemara-live-action-combat-director", "pemara-video-motion-director", "h3-prompt-writing"],',
        '"agents": ["pemara-performance-director", "pemara-cinematography-director", "creative-director", "pemara-live-action-combat-director", "pemara-video-motion-director", "h3-prompt-writing"],')
replace('"output": "modo T2VA/I2VA/FL2VA/L2VA/Ref2VA, timeline, keyframes, som e musica",',
        '"output": "modo H3 qualificado, timeline, ancoras por rota, intencao e camera; audio somente no escopo autorizado",')
replace('"agents": ["pemara-live-action-qc", "video-production", "pemara-video-motion-director"],',
        '"agents": ["pemara-video-production-lead", "pemara-live-action-qc", "pemara-performance-director", "pemara-cinematography-director", "video-production", "pemara-video-motion-director"],')
replace('"output": "ffprobe, contact sheet, identidade, fisica e movimento integral",',
        '"output": "MP4 integral observado: historia, atuacao, fotografia, identidade, fisica e movimento; timestamps, correcao e integridade, sem inferir aprovacao por metadata",')
replace('"label": "Conectores de acao continua",', '"label": "Continuidade e cortes de acao",')
replace('"agents": ["pemara-live-action-kinetic-supervisor", "pemara-live-action-continuity", "pemara-cinematic-take-director", "pemara-video-motion-director"],',
        '"agents": ["pemara-film-editor", "pemara-live-action-kinetic-supervisor", "pemara-live-action-continuity", "pemara-cinematic-take-director", "pemara-video-motion-director"],')
replace('"output": "ponte fisica irreversivel entre takes aprovados",',
        '"output": "corte cinetico direto entre fontes aprovadas e compativeis; conector causal apenas quando permitido e autorizado; caso contrario corrigir a fonte",')
replace('"label": "Picture lock FHD60",', '"label": "Montagem aprovada e acabamento FHD60",')
replace('"agents": ["video-production"],', '"agents": ["pemara-film-editor", "pemara-video-production-lead", "video-production"],')
replace('"label": "Foley apos picture lock",', '"label": "Audio adicional somente quando solicitado",')
replace('"output": "candidatos de Foley sincronizados, nunca anexados automaticamente",',
        '"output": "audio existente preservado; Foley novo somente no escopo explicitamente autorizado, candidato com escuta e aprovacao proprias",')
replace('"agents": ["video-production", "test-engineer", "documentation-and-adrs"],',
        '"agents": ["pemara-video-production-lead", "pemara-film-editor", "video-production", "test-engineer", "documentation-and-adrs"],')

# Only catalogue/stage descriptions change. Runtime and generation functions are byte-identical.
new = text[:start]+block+text[end:]
assert new[:start] == text[:start]
assert new[new.index('\ndef _agents_root'):] == text[end:]
path.write_text(new, encoding='utf-8')
print('Quatro novas funcoes registradas no catalogo H3. Alterado somente WORKFLOW_SKILLS/STAGES.')
