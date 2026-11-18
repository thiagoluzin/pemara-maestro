"""Read public upstream metadata without installing or executing plugin code."""
import ast
import concurrent.futures
import json
import urllib.request
from pathlib import Path

REPOS={
 'h3_prompt_rewriter':'pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI',
 'h3_motion_director':'j955229/ComfyUI-MiniMax-H3-Motion-Director',
 'h3_timeline_director':'Songssx/ComfyUI-MiniMaxH3-TimelineDirector',
 'h3_fun_control':'wyzborrero/ComfyUI-H3-FunControl',
 'h3_latent_upscale':'LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler',
}

def read(url):
 request=urllib.request.Request(url,headers={'User-Agent':'CreativeOS-readonly-audit','Accept':'application/vnd.github+json'})
 with urllib.request.urlopen(request,timeout=20) as response: return response.read().decode('utf-8')

def inspect(item):
 key,repo=item
 try:
  meta=json.loads(read('https://api.github.com/repos/'+repo))
  commit=json.loads(read('https://api.github.com/repos/'+repo+'/commits/'+meta['default_branch']))['sha']
  source=read('https://raw.githubusercontent.com/'+repo+'/'+commit+'/__init__.py')
  names=[]
  for node in ast.walk(ast.parse(source)):
   if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NODE_CLASS_MAPPINGS' for t in node.targets) and isinstance(node.value,ast.Dict):
    names.extend(k.value for k in node.value.keys if isinstance(k,ast.Constant) and isinstance(k.value,str))
  return key,{'repository':repo,'url':meta['html_url'],'commit':commit,'license_reported_by_github':(meta.get('license') or {}).get('spdx_id'),
    'node_ids_declared_in_init':names,'node_inventory_complete':bool(names),'installed_by_this_audit':False,
    'enabled':False,'code_executed':False,'weights_license':'NOT_REVIEWED','qualification':'LOCAL_ADAPTER_AND_BENCHMARK_REQUIRED'}
 except Exception as exc: return key,{'repository':repo,'error':str(exc),'enabled':False,'qualification':'UNKNOWN'}

if __name__=='__main__':
 root=Path(__file__).resolve().parents[1]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: result=dict(pool.map(inspect,REPOS.items()))
 target=root/'dados/creative_os/optional_upstream_audit_20260907.json'
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
