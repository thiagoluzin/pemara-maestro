"""Maestro argv adapter for upstream MMAudio; never replaces the source video."""
from argparse import ArgumentParser
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'engines/mmaudio/repo'

def main():
    p = ArgumentParser()
    p.add_argument('--video', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--prompt', required=True)
    p.add_argument('--negative-prompt', default='')
    p.add_argument('--duration', type=float, default=8)
    p.add_argument('--seed', type=int, default=42)
    args = p.parse_args()
    if not args.video.is_file() or not 0.5 <= args.duration <= 15:
        raise ValueError('Vídeo ou duração inválidos.')
    required = ['weights/mmaudio_large_44k_v2.pth','ext_weights/v1-44.pth','ext_weights/synchformer_state_dict.pth']
    if any(not (REPO / item).is_file() for item in required):
        raise RuntimeError('Pesos MMAudio incompletos; concluir instalação.')
    sys.path.insert(0, str(ROOT.parents[2] / 'services/studio'))
    from game_gpu_admission import admit
    admit(20000)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    env = dict(os.environ, HF_HUB_OFFLINE='1', MMAUDIO_CLIP_MODEL='local-dir:'+str(ROOT/'engines/mmaudio/clip'))
    with tempfile.TemporaryDirectory(prefix='mmaudio_', dir=args.output.parent) as temp:
        cmd = [sys.executable,str(REPO/'demo.py'),'--variant','large_44k_v2','--video',str(args.video.resolve()),
               '--output',temp,'--prompt',args.prompt,'--negative_prompt',args.negative_prompt,
               '--duration',str(args.duration),'--seed',str(max(0,args.seed)),'--skip_video_composite']
        subprocess.run(cmd,cwd=REPO,env=env,check=True)
        flac = Path(temp)/(args.video.stem+'.flac')
        subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(flac),'-ar','48000','-c:a','pcm_s24le',str(args.output)],check=True)

if __name__ == '__main__':
    main()
