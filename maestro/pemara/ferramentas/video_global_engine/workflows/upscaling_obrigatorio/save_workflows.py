"""Save the mandatory API workflows and their immutable resolution profiles."""
from pathlib import Path
import json
import sys
studio = Path(__file__).resolve().parents[4]/'services/studio'
sys.path.insert(0,str(studio))
import upscaling_required as p
for (w,h),name in p.TARGETS.items():
    profile=p.canonical_profile(w,h)
    (p.PROFILE_DIR/(profile['profile_id']+'.json')).write_text(json.dumps(profile,indent=2,ensure_ascii=False),encoding='utf-8')
    graph=p.build_workflow('RE1_NATIVE24_FOLEY.mp4',768,1344,w,h,'upscaling_obrigatorio/'+name,content_kind='animation')
    p.assert_graph(graph)
    (p.WORKFLOW_DIR/('upscaling_obrigatorio_'+name+'.api.json')).write_text(json.dumps(graph,indent=2,ensure_ascii=False),encoding='utf-8')
pilot=p.build_workflow('RE1_ESR_PILOT_24F.mp4',768,1344,1080,1920,'upscaling_obrigatorio/smoke_fhd60',content_kind='animation')
(p.WORKFLOW_DIR/'smoke_fhd60.api.json').write_text(json.dumps(pilot,indent=2),encoding='utf-8')
print(json.dumps({'profiles':len(p.TARGETS),'workflow_dir':str(p.WORKFLOW_DIR),'required':True}))
