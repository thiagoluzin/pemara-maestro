"""Resumable official HF downloads with range checks and SHA-256 verification."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CHUNK=32*1024*1024

def api(path):
    with urllib.request.urlopen('https://huggingface.co/api/models/'+path,timeout=30) as r:
        return json.load(r)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def fetch(repo,revision,info,dest):
    size=info['size'];sha=info.get('lfs',{}).get('oid')
    if dest.exists() and dest.stat().st_size==size and (not sha or digest(dest)==sha):return
    dest.parent.mkdir(parents=True,exist_ok=True)
    parts=dest.parent/(dest.name+'.zico-parts');parts.mkdir(exist_ok=True)
    def part(index):
        start=index*CHUNK;end=min(size-1,start+CHUNK-1)
        file=parts/str(index);header=parts/(str(index)+'.headers')
        if file.exists() and file.stat().st_size==end-start+1:return file
        for attempt in range(4):
            url=f'https://huggingface.co/{repo}/resolve/{revision}/{info["path"]}?download=true&zico={start}-{end}-{attempt}'
            result=subprocess.run(['curl.exe','-L','--fail','--silent','--show-error','--connect-timeout','20','--max-time','120',
                '--range',f'{start}-{end}','--dump-header',str(header),'--output',str(file),url],capture_output=True,text=True)
            headers=header.read_text(errors='replace') if header.exists() else ''
            ranges=re.findall(r'content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)',headers,re.I)
            if result.returncode==0 and file.stat().st_size==end-start+1 and (size<=CHUNK or ranges and tuple(map(int,ranges[-1]))==(start,end,size)):
                return file
        raise RuntimeError(f'Failed range {repo}/{info["path"]}: {start}-{end}')
    count=(size+CHUNK-1)//CHUNK
    print(f'Download {repo}/{info["path"]}: {size/1e9:.2f} GB',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures=[pool.submit(part,i) for i in range(count)]
        for n,f in enumerate(concurrent.futures.as_completed(futures),1):
            f.result()
            if n%10==0 or n==count:print(f'  {n}/{count} blocos',flush=True)
    temporary=dest.with_suffix(dest.suffix+'.verified-partial')
    with temporary.open('wb') as out:
        for i in range(count):
            with (parts/str(i)).open('rb') as source:shutil.copyfileobj(source,out,8*1024*1024)
    if temporary.stat().st_size!=size or sha and digest(temporary)!=sha:raise RuntimeError('Checksum mismatch: '+str(dest))
    os.replace(temporary,dest)
    # Only remove verified download fragments inside this exact newly-created directory.
    for item in parts.iterdir():
        if item.is_file():item.unlink()
    parts.rmdir()
    print('  SHA-256 OK',flush=True)

def main():
    plans=[('hkchengrex/MMAudio', ROOT/'engines/mmaudio/repo',
            {'weights/mmaudio_large_44k_v2.pth','ext_weights/v1-44.pth','ext_weights/synchformer_state_dict.pth'}),
           ('apple/DFN5B-CLIP-ViT-H-14-384',ROOT/'engines/mmaudio/clip',{'open_clip_config.json','open_clip_pytorch_model.bin'}),
           ('fishaudio/s2-pro',ROOT/'engines/fish/repo/checkpoints/s2-pro',None)]
    receipts=[]
    for repo,target,names in plans:
        revision=api(repo)['sha']
        items=api(repo+'/tree/'+revision+'?recursive=true')
        for info in items:
            if info['type']!='file' or names and info['path'] not in names or info['path'] in {'overview.png','.gitattributes'}:continue
            dest=target/info['path']
            fetch(repo,revision,info,dest)
            receipts.append({'repo':repo,'revision':revision,'path':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest)})
        (ROOT/('mmaudio_weights_verified.json' if repo.startswith('apple/') else 'weights_download_progress.json')).write_text(json.dumps(receipts,indent=2),encoding='utf-8')
    (ROOT/'all_weights_verified.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')

if __name__=='__main__':main()
