"""Verify local deployment without calling any ComfyUI endpoint."""
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STUDIO=ROOT/'services/studio'
sys.path.insert(0,str(STUDIO))
from creative_os.ir import digest

def request(path,body=None,headers=None):
 req=urllib.request.Request('http://127.0.0.1:8029'+path,data=json.dumps(body).encode() if body is not None else None,
     headers={'Content-Type':'application/json',**(headers or {})})
 try:
  with urllib.request.urlopen(req,timeout=15) as response:return response.status,json.loads(response.read())
 except urllib.error.HTTPError as error:return error.code,json.loads(error.read())

def main():
 files=[*(STUDIO/'creative_os').glob('*.py'),STUDIO/'main.py',STUDIO/'gpu_lease.py']
 expected=digest({str(p.relative_to(STUDIO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
 code,health=request('/api/creative/health')
 bad_code,bad=request('/api/creative/shots',{'version':'invalid'})
 public_code,_=request('/api/creative/health',headers={'X-Forwarded-Host':'untrusted.example'})
 hq_code,hq=request('/api/creative/hq')
 result={'health_http':code,'health':health,'expected_build_hash':expected,'build_matches':health.get('build_hash')==expected,
         'invalid_ir_http':bad_code,'invalid_ir':bad,'untrusted_forwarded_host_http':public_code,'hq_http':hq_code,
         'hq_profiles':hq.get('profiles'),'hq_jobs':len(hq.get('jobs',[])),'called_comfyui':False}
 with urllib.request.urlopen('http://127.0.0.1:9501/assets/creative-os.js?v=20260907-v7',timeout=10) as response:
  data=response.read();result['frontend_asset_http']=response.status
  result['frontend_asset_matches']=hashlib.sha256(data).digest()==hashlib.sha256((ROOT/'app/assets/creative-os.js').read_bytes()).digest()
 result['pass']=code==hq_code==200 and bad_code==422 and public_code==403 and result['build_matches'] and result['frontend_asset_matches']
 (ROOT/'dados/creative_os/deployment_verification_20260907.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))
 raise SystemExit(not result['pass'])

if __name__=='__main__':main()
