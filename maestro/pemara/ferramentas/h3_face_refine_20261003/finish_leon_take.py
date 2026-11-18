"""Trim a completed MCP-fetched video to exact 30 s and produce QC evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'

def run(args,path=None):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
    if path:
        path.write_text(result.stderr,encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Command failed; see QC log: '+str(path))
    return result

def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path)
    p.add_argument('--face-report',type=Path,required=True)
    args=p.parse_args()
    source=args.source.resolve()
    facial=json.loads(args.face_report.read_text(encoding='utf-8'))
    if not facial.get('enabled') or facial.get('frames')!=736 or facial.get('detected_faces',0)<1 or not facial.get('tracks'):
        raise ValueError('Requested human Face Refine did not run on the native source')
    if facial.get('audio_modified') is not False or facial.get('sage_attention')!='connected_base_fl2va':
        raise ValueError('Face Refine audio/Sage contract failed')
    if not all(track['stitch'].get('mask_outside_bit_exact') is True for track in facial['tracks']):
        raise ValueError('Face Refine mask preservation audit failed')
    qc=PROJECT/'qc';qc.mkdir(exist_ok=True)
    output=PROJECT/'outputs';output.mkdir(exist_ok=True)
    before=probe(source)
    save(qc/'source_ffprobe.json',before)
    v=next(s for s in before['streams'] if s['codec_type']=='video')
    a=next((s for s in before['streams'] if s['codec_type']=='audio'),None)
    if not a:raise ValueError('Missing requested native audio')
    if (v['width'],v['height'])!=(1344,768):raise ValueError('Unexpected source geometry')
    if v['r_frame_rate']!='24/1':raise ValueError('Unexpected FPS')
    if int(v.get('nb_frames',0))!=736:raise ValueError('Unexpected native source frame count')
    if float(a.get('duration',0))<29.95:raise ValueError('Native audio is shorter than the requested take')
    target=output/'Leon_primeiro_Licker_RE2_1998_30s_H3_FaceRefine_audio_nativo_v1.mp4'
    if target.exists():raise FileExistsError('Preserve previous candidate: '+str(target))
    # Re-encode one copy for frame-accurate trimming. Never overwrite MCP source.
    run(['ffmpeg','-hide_banner','-nostdin','-i',str(source),'-filter_complex',
         '[0:v:0]trim=end_frame=720,setpts=PTS-STARTPTS[v];[0:a:0]atrim=end=30,asetpts=PTS-STARTPTS[a]',
         '-map','[v]','-map','[a]','-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p',
         '-c:a','aac','-b:a','192k','-movflags','+faststart',str(target)],qc/'trim_ffmpeg.log')
    after=probe(target)
    save(qc/'delivery_ffprobe.json',after)
    dv=next(s for s in after['streams'] if s['codec_type']=='video')
    da=next(s for s in after['streams'] if s['codec_type']=='audio')
    if int(dv.get('nb_frames',0))!=720 or abs(float(dv['duration'])-30)>.001:
        raise ValueError('Delivery is not 720 frames/30 seconds')
    # Decode all streams for corruption and duration errors.
    run(['ffmpeg','-hide_banner','-nostdin','-xerror','-v','error','-i',str(target),'-f','null','-'],qc/'decode.log')
    run(['ffmpeg','-hide_banner','-nostdin','-i',str(target),'-vf','fps=1,scale=320:-2,tile=6x5',
         '-frames:v','1','-update','1',str(qc/'contact_sheet_30frames.jpg')],qc/'contact_sheet.log')
    for name,seconds in [('start',0),('early',6),('middle',15),('reveal',23),('end',29.95)]:
        run(['ffmpeg','-hide_banner','-nostdin','-ss',str(seconds),'-i',str(target),
             '-frames:v','1','-update','1',str(qc/(name+'.png'))],qc/(name+'_frame.log'))
    loudness=run(['ffmpeg','-hide_banner','-nostdin','-i',str(target),'-vn',
                  '-af','loudnorm=I=-16:TP=-1:LRA=11:print_format=json','-f','null','-'],qc/'loudness.log')
    raw=loudness.stderr
    measured=json.loads(raw[raw.rfind('{'):raw.rfind('}')+1])
    save(qc/'loudness.json',measured)
    # PCM preview for actual listening; retains native sound content.
    run(['ffmpeg','-hide_banner','-nostdin','-i',str(target),'-vn','-c:a','pcm_s16le',
         str(qc/'native_audio_review.wav')],qc/'audio_extract.log')
    receipt={'status':'PENDING_FULL_VISUAL_AND_AUDIO_REVIEW','ownerApproval':'PENDING_VIDEO_REVIEW',
        'source':{'path':str(source),'sha256':sha(source),'preserved':True},
        'delivery':{'path':str(target),'sha256':sha(target),'frames':720,'seconds':30,'fps':24,
                    'width':dv['width'],'height':dv['height'],'audioCodec':da['codec_name'],
                    'audioChannels':da['channels'],'audioDuration':da['duration']},
        'trimTailFrames':16,'audioOrigin':'MiniMax H3 native; same time trim; no external audio or replacement',
        'faceRefine':{'applied':True,'reportPath':str(args.face_report.resolve()),'reportSha256':sha(args.face_report),
            'detectedFaces':facial['detected_faces'],'tracks':len(facial['tracks']),'windows':len(facial['windows']),
            'steps':facial['steps'],'denoise':facial['denoise'],'canvas':facial['canvas'],
            'outsideMaskBitExactBeforeEncoding':True,'identityVerified':False,
            'fallbackFrameCounts':[track['stitch']['fallback_count'] for track in facial['tracks']]},
        'loudnessInput':measured,'checkedAt':datetime.now(timezone.utc).isoformat(),
        'checks':{'fullDecode':True,'visualReview':False,'audioListening':False},'paidAPINodes':False}
    save(PROJECT/'delivery_candidate.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
