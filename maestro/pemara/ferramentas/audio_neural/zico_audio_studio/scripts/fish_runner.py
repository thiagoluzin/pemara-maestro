"""Explicit local Fish Speech job, without cloning or automatic model downloads."""
from argparse import ArgumentParser
from pathlib import Path
import json
import os
import runpy
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
REPO=ROOT/'engines/fish/repo'

def main():
    p=ArgumentParser()
    p.add_argument('--text-file',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--job-id',required=True)
    p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
    if not (ROOT/'all_weights_verified.json').is_file():raise RuntimeError('Instalação dos pesos ainda incompleta.')
    if a.output.exists():raise FileExistsError(a.output)
    text=a.text_file.read_text(encoding='utf-8')
    if not 1<=len(text)<=2000:raise ValueError('Texto deve ter entre 1 e 2000 caracteres.')
    sys.path.insert(0,str(PROJECT/'services/studio'))
    from gpu_lease import GpuLeaseRegistry
    lease=GpuLeaseRegistry(PROJECT/'dados/studio/gpu_lease.json')
    lease.acquire(owner='zico',operation='fish_speech',job_id=a.job_id)
    try:
        from game_gpu_admission import admit
        admit(24000)
        os.environ['HF_HUB_OFFLINE']='1'
        os.chdir(REPO)
        sys.path.insert(0,str(REPO))
        sys.argv=['fish-inference','--text',text,'--checkpoint-path',str(REPO/'checkpoints/s2-pro'),
                  '--output',str(a.output.resolve()),'--output-dir',str(a.output.parent.resolve()),
                  '--device','cuda','--no-compile','--seed',str(a.seed),'--max-new-tokens','2048']
        runpy.run_module('fish_speech.models.text2semantic.inference',run_name='__main__')
    finally:
        lease.release(a.job_id)

if __name__=='__main__':main()
