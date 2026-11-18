"""Stream RIFE 4.25 inside the serial mandatory ComfyUI finishing node.

The caller owns GPU admission. Do not run this GPU worker as a ComfyUI client.
"""
import argparse
import atexit
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid

parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('audio_source')
parser.add_argument('output')
parser.add_argument('--width', type=int, required=True)
parser.add_argument('--height', type=int, required=True)
parser.add_argument('--lanczos', action='store_true', help='Conventional spatial scaling after native-resolution RIFE; no neural restoration.')
parser.add_argument('--cuts-json', help='Known native frame boundaries of an edited clip; never interpolate across them.')
args = parser.parse_args()
# An optional explicit edit-boundary companion is hash-bound to the exact source.
# It only prevents optical-flow interpolation across known edits; no timing changes.
cut_companion = Path(str(args.source) + '.cuts.json')
pending_original_cut_companion = None
native_cut_metadata = None
editorial_overlay = None
encoder_working_directory = None
if args.cuts_json:
    known_cuts = set(json.loads(Path(args.cuts_json).read_text()))
elif cut_companion.is_file():
    cut_data = json.loads(cut_companion.read_text(encoding='utf-8-sig'))
    with Path(args.source).open('rb') as cut_source:
        assert hashlib.file_digest(cut_source, 'sha256').hexdigest() == cut_data['source_sha256'], 'Cut companion source mismatch.'
    known_cuts = set(cut_data['native_cut_frames'])
    assert all(type(x) is int and x > 0 for x in known_cuts), 'Invalid edit boundary.'
elif Path(str(args.audio_source) + '.cuts.json').is_file():
    # Seed's temporary video has no sidecar. Verify the original input and
    # restored cadence/count before forwarding its explicitly known edits.
    pending_original_cut_companion = Path(str(args.audio_source) + '.cuts.json')
    known_cuts = set()
else:
    known_cuts = set()
repo = Path(r'E:\Pemara\third_party\Practical-RIFE')
model_file = repo / 'train_log/flownet.pkl'
with model_file.open('rb') as f:
    assert hashlib.file_digest(f,'sha256').hexdigest() == '6615790efd627772917205db291f51cd392528a157ecbb2ecaeec3bff8eb6de2'
sys.path.insert(0, str(repo))
sys.path.insert(0, r'E:\Pemara\maestro\pemara\services\studio')
import numpy as np
import torch
import torch.nn.functional as F
from train_log.RIFE_HDv3 import Model

ffmpeg = r'E:\Pemara\third_party\video2dlssnr-v1.4.1\release\out\ffmpeg.exe'
ffprobe = r'E:\Pemara\third_party\video2dlssnr-v1.4.1\release\out\ffprobe.exe'
probe = json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-show_streams','-of','json',args.source]))
v = next(x for x in probe['streams'] if x['codec_type']=='video')
w,h = v['width'],v['height']
fps = Fraction(v['avg_frame_rate'])
assert 24 <= fps <= 60, 'Cadence outside the qualified 24..60 FPS range.'
n = int(v['nb_read_frames'])
if pending_original_cut_companion is not None:
    from rife_known_native_cuts import load_audio_source_companion
    known_cuts, native_cut_metadata = load_audio_source_companion(args.audio_source, n, str(fps), ffprobe)
if Path(str(args.audio_source) + '.titles.json').is_file():
    from rife_editorial_overlay import load_original_source_overlay
    overlay_ass, editorial_overlay = load_original_source_overlay(args.audio_source, n, str(fps), args.width, args.height, ffprobe)
    encoder_working_directory = str(overlay_ass.parent)
assert all(x < n for x in known_cuts), 'Edit boundary outside source.'
exact_count = Fraction(n,1) / fps * 60
assert exact_count.denominator == 1, 'Duration must align exactly to 1/60 s.'
count = int(exact_count)
from upscaling_required import spatial_filter as make_spatial_filter
spatial_filter = make_spatial_filter(w,h,args.width,args.height,lanczos=args.lanczos)
color_args=[]
for key,flag in [('color_range','-color_range'),('color_space','-colorspace'),
                 ('color_transfer','-color_trc'),('color_primaries','-color_primaries')]:
    value=v.get(key)
    if value and value!='unknown':
        color_args += [flag,value]
if args.lanczos and v.get('color_space')=='bt709':
    spatial_filter=spatial_filter.replace(':flags=lanczos,',':flags=lanczos:in_range=pc:out_range=tv:out_color_matrix=bt709,')
if v.get('color_space')=='bt709' and v.get('color_transfer')=='iec61966-2-1' and v.get('color_range')=='tv':
    # Some NVENC builds omit the sRGB VUI despite the encoder option. Explicit
    # bitstream metadata preserves the measured source tags without grading.
    color_args += ['-bsf:v','h264_metadata=colour_primaries=1:transfer_characteristics=13:matrix_coefficients=1:video_full_range_flag=0']

if editorial_overlay is not None:
    # One deterministic ASS filter in the already mandatory NVENC encode.
    # The safe sibling basename resolves only within the exact input folder.
    spatial_filter += ',' + editorial_overlay['filter']
assert args.width % 2 == args.height % 2 == 0
assert torch.cuda.is_available()
model = Model()
model.load_model(str(repo/'train_log'),-1)
model.eval()
decode_log = Path(args.output+'.decode.log').open('wb')
encode_log = Path(args.output+'.encode.log').open('wb')
decoder = subprocess.Popen([ffmpeg,'-v','error','-i',args.source,'-map','0:v:0','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=decode_log)
encoder = subprocess.Popen([ffmpeg,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r','60','-i','-',
    '-i',args.audio_source,'-map','0:v:0','-map','1:a:0?',
    '-vf',spatial_filter,
    '-c:v','h264_nvenc','-preset','p7','-cq','15','-b:v','0','-pix_fmt','yuv420p','-c:a','copy',
    *color_args,'-t',str(float(Fraction(n,1)/fps)),'-movflags','+faststart',args.output],stdin=subprocess.PIPE,stderr=encode_log,cwd=encoder_working_directory)
pw,ph=math.ceil(w/128)*128,math.ceil(h/128)*128

def read_frame():
    raw=bytearray()
    while len(raw)<w*h*3:
        block=decoder.stdout.read(w*h*3-len(raw))
        if not block:
            break
        raw.extend(block)
    if not raw:
        return None
    assert len(raw)==w*h*3, 'Truncated decoded frame.'
    a=np.frombuffer(raw,dtype=np.uint8).reshape(h,w,3).copy()
    t=torch.from_numpy(a).cuda().permute(2,0,1).unsqueeze(0).float()/255
    return F.pad(t,(0,pw-w,0,ph-h),'replicate')

start=time.monotonic()
cuts=[]
current_index=0
a=read_frame()
b=read_frame()
try:
    with torch.inference_mode():
        for j in range(count):
            position=Fraction(j,60)*fps
            wanted=int(position)
            fraction=float(position-wanted)
            while current_index<wanted:
                a=b if b is not None else a
                b=read_frame()
                current_index+=1
            if fraction==0 or b is None:
                out=a
            else:
                difference=float((a[:,:,:h,:w]-b[:,:,:h,:w]).abs().mean())
                if current_index+1 in known_cuts or difference>.35:
                    if current_index not in cuts:
                        cuts.append(current_index)
                    out=a if current_index+1 in known_cuts else (a if fraction<.5 else b)
                else:
                    out=model.inference(a,b,timestep=fraction,scale=1)
            frame=(out[0,:,:h,:w].clamp(0,1)*255).round().byte().permute(1,2,0).contiguous().cpu().numpy()
            encoder.stdin.write(frame.tobytes())
            if j%120==0:
                print(f'RIFE exact60 {j}/{count}',flush=True)
    encoder.stdin.close()
    assert encoder.wait()==0,'Encoding failed.'
    assert decoder.wait()==0,'Decoding failed.'
finally:
    for proc in (decoder,encoder):
        if proc.poll() is None:
            proc.kill()
    decode_log.close()
    encode_log.close()
meta={'source':args.source,'output':args.output,'model':'Practical-RIFE 4.25','source_fps':str(fps),'output_fps':60,
    'spatial_filter':spatial_filter,'neural_spatial_restoration':not args.lanczos,
    'target_width':args.width,'target_height':args.height,
    'source_frames':n,'output_frames':count,'duration':float(Fraction(n,1)/fps),'timestamps':'j/60; source position j*source_fps/60',
    'cut_threshold_mean_rgb':.35,'known_native_cut_frames':sorted(known_cuts),'native_cut_metadata':native_cut_metadata,
    'editorial_overlay':editorial_overlay,'cut_pairs':cuts,'seconds':round(time.monotonic()-start,3)}
Path(args.output+'.rife.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta),flush=True)
