"""Build reviewable H3 graph, never enqueue or record owner approval."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'services/studio'))
from main import _build_minimax_h3_fl2va_workflow

project=ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
request=json.loads((project/'production_request.json').read_text(encoding='utf-8'))
anchors={item['role']:item for item in request['anchors']}
graph=_build_minimax_h3_fl2va_workflow(
    (project/'prompt_h3.txt').read_text(encoding='utf-8'),'',1344,768,736,20,19980121,
    'RE2_LEON_FIRST_LICKER/T01_master_native_audio_face_refine_attempt01',anchors['start']['comfyInput'],
    end_image_name=anchors['end']['comfyInput'],include_native_audio=True,
    allow_owner_long_window=True,h3_quality_profile='h3_master')
path=project/'workflows/T01_master_30s_native_audio_face_refine.api.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(path),'nodes':len(graph),'submitted':False,'ownerApproval':'PENDING'}))
