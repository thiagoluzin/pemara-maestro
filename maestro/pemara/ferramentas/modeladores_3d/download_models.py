from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from huggingface_hub import snapshot_download
import json
ROOT=Path('D:/PemaraRuntimes/maestro-game-ai/models')
jobs=[('tencent/Hunyuan3D-2.1','0b94677654c57bb9a6b6845cd7b704ccf551d327','Hunyuan3D-2.1',['hunyuan3d-dit-v2-1/*','hunyuan3d-vae-v2-1/*','LICENSE','Notice.txt']),('VAST-AI/TripoSG','2c1c516d22d58db486a058d98d31bb6177344e06','TripoSG',None)]
def get(job):
    repo,rev,name,patterns=job
    print('Downloading '+repo,flush=True)
    p=snapshot_download(repo_id=repo,revision=rev,local_dir=ROOT/name,allow_patterns=patterns,max_workers=3)
    (ROOT/(name+'-download.json')).write_text(json.dumps({'repo':repo,'revision':rev,'path':p},indent=2))
    print('Complete '+repo,flush=True)
with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(get,jobs))
