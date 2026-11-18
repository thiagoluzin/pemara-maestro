"""Finish the owner-approved original with existing local RIFE, no Face Refine."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,subprocess,math
import cv2,numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PROJECT=ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
SOURCE=PROJECT/'outputs/Leon_primeiro_Licker_RE2_1998_30s_H3_ORIGINAL_audio_nativo_v1.mp4'
SOURCE_SHA='ff824bd6c1228bf4ed03d7c2ae04ba6d92964f08c8bfae47f890f779260d6b06'
RIFE=Path('E:/Pemara/third_party/Practical-RIFE')
WEIGHT_SHA='6615790efd627772917205db291f51cd392528a157ecbb2ecaeec3bff8eb6de2'
OUT=PROJECT/'outputs/Leon_primeiro_Licker_RE2_1998_FULLHD_1920x1080_60FPS_audio_nativo_v1.mp4'
QC=PROJECT/'qc/fhd60_original_v1';QC.mkdir(parents=True,exist_ok=True)
CUTS={402,579}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(c):return subprocess.run(c,capture_output=True,text=True,check=True)

def main():
    if sha(SOURCE)!=SOURCE_SHA:raise ValueError('Owner-approved original changed')
    if sha(RIFE/'train_log/flownet.pkl')!=WEIGHT_SHA:raise ValueError('RIFE weight changed')
    if OUT.exists():raise FileExistsError('Preserve existing finished candidate')
    save(QC/'owner_picture_lock.json',{'ownerQuote':'Já vi ficou ótimo. 60fps e fullhad agora',
       'approvedSource':str(SOURCE),'approvedSourceSha256':SOURCE_SHA,'sourceApproved':True,
       'authorizedFinishing':{'width':1920,'height':1080,'fps':60,'durationSeconds':30},
       'newGeneration':False,'faceRefine':False,'derivativeOwnerApproved':False,
       'recordedAt':datetime.now(timezone.utc).isoformat()})
    sys.path.insert(0,str(RIFE));sys.path.insert(0,str(ROOT/'services/studio'))
    import torch
    import ltx_review_pipeline as rp
    rp._validate_runtime({},'ffmpeg')
    if not torch.cuda.is_available() or torch.cuda.mem_get_info()[0]<8*1024**3:raise RuntimeError('Insufficient free local CUDA memory')
    from train_log.RIFE_HDv3 import Model
    model=Model();model.load_model(str(RIFE/'train_log'),-1);model.eval()
    torch.set_grad_enabled(False);torch.backends.cudnn.benchmark=True
    cap=cv2.VideoCapture(str(SOURCE));assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT))==720
    assert (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))==(1344,768)
    temp=OUT.with_name(OUT.stem+'.partial.mp4')
    if temp.exists():raise FileExistsError(temp)
    command=['ffmpeg','-hide_banner','-nostdin','-v','error','-n','-f','rawvideo','-pix_fmt','bgr24',
       '-s','1344x768','-r','60','-i','pipe:0','-i',str(SOURCE),'-map','0:v:0','-map','1:a:0',
       '-vf','scale=1890:1080:flags=lanczos,pad=1920:1080:15:0:color=black,setsar=1',
       '-c:v','h264_nvenc','-preset','p7','-tune','hq','-cq','15','-b:v','0','-profile:v','high',
       '-pix_fmt','yuv420p','-c:a','copy','-t','30','-movflags','+faststart',str(temp)]
    cache={};tensors={};read_index=-1;interpolated=0;source_samples=0;cut_samples=0
    def get(index):
        nonlocal read_index
        while read_index<index:
            ok,frame=cap.read()
            if not ok:raise RuntimeError('Source decode failed')
            read_index+=1;cache[read_index]=frame
        if index not in tensors:
            rgb=np.ascontiguousarray(cache[index][:,:,::-1])
            tensors[index]=torch.from_numpy(rgb).to('cuda').permute(2,0,1).unsqueeze(0).float()/255
        return tensors[index]
    with (QC/'encode.log').open('wb') as log:
        encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
        try:
            with torch.inference_mode():
                for out_index in range(1800):
                    # Integer arithmetic gives exact 24/60 source positions; no speed change.
                    numerator=out_index*2;lo=min(719,numerator//5);fraction=(numerator%5)/5;hi=min(719,lo+1)
                    left,right=get(lo),get(hi)
                    if fraction==0 or lo==hi or hi in CUTS:
                        frame=cache[lo];source_samples+=1
                        if hi in CUTS and fraction:cut_samples+=1
                    else:
                        pred=model.inference(left,right,timestep=fraction,scale=1.)
                        rgb=(pred[0].clamp(0,1).permute(1,2,0)*255).round().byte().cpu().numpy()
                        frame=np.ascontiguousarray(rgb[:,:,::-1]);interpolated+=1
                    encoder.stdin.write(frame.tobytes())
                    for i in list(cache):
                        if i<lo:del cache[i];tensors.pop(i,None)
                    if out_index%120==0:print(json.dumps({'frame':out_index,'total':1800,'percent':round(out_index/18,1)}),flush=True)
            encoder.stdin.close()
            if encoder.wait():raise RuntimeError('Encoding failed; see encode.log')
        finally:
            cap.release()
            if encoder.poll() is None:encoder.kill();encoder.wait()
    probe=json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(temp)]).stdout)
    v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(1920,1080,'60/1',1800)
    assert abs(float(v['duration'])-30)<.001 and abs(float(probe['format']['duration'])-30)<.025
    run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(temp),'-f','null','NUL'])
    def audio_packets(p):
        d=json.loads(run(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_data_hash','sha256','-show_entries','packet=data_hash','-of','json',str(p)]).stdout)
        return [x['data_hash'] for x in d['packets']]
    assert audio_packets(SOURCE)==audio_packets(temp)
    assert sha(SOURCE)==SOURCE_SHA
    temp.rename(OUT)
    save(QC/'ffprobe.json',probe)
    receipt={'status':'TECHNICAL_PASS_PENDING_OWNER_REVIEW','file':str(OUT),'sha256':sha(OUT),
       'source':str(SOURCE),'sourceSha256':SOURCE_SHA,'sourceOwnerApproved':True,'humanApproved':False,
       'width':1920,'height':1080,'fps':60,'frames':1800,'durationSeconds':30,
       'interpolation':{'engine':'Practical-RIFE','model':'4.25','modelSha256':WEIGHT_SHA,
                       'exactTimestampSampling':True,'interpolatedFrames':interpolated,'sourceFrameSamples':source_samples,
                       'cutFrames':sorted(CUTS),'noInterpolationAcrossCuts':True,'cutHoldSamples':cut_samples},
       'spatialFinishing':'Lanczos to 1890x1080; 15px black padding each side; no cropping or stretching',
       'faceRefine':False,'audioNative':True,'audioEncodedPacketsUnchanged':True,
       'fullDecode':True,'sourcePreserved':True,'checkedAt':datetime.now(timezone.utc).isoformat()}
    save(QC/'delivery.json',receipt)
    run(['ffmpeg','-hide_banner','-nostdin','-v','error','-i',str(OUT),'-vf','fps=1,scale=320:180,tile=6x5','-frames:v','1','-update','1',str(QC/'contact_sheet.jpg')])
    for name,second in [('leon_closeup',18),('licker_reveal',14),('ending',29.8)]:
        run(['ffmpeg','-hide_banner','-nostdin','-v','error','-ss',str(second),'-i',str(OUT),'-frames:v','1','-update','1',str(QC/(name+'.png'))])
    print(json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
