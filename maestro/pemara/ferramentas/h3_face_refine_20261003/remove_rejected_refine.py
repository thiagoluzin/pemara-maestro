"""Owner-requested removal; preserve rejected media and independent Sage fix."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = Path('D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara')
PROJECT = ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
BACKUP = HERE/'rollback/owner_removal_20261004'
NODE = 'PemaraH3FaceRefine'
sys.path.insert(0, str(ROOT/'services/studio'))
sys.path.insert(0, str(ROOT))
from h3_face_refine import remove_face_refine

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value):
    content = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode() if not isinstance(value, bytes) else value
    if p.exists() and p.read_bytes()==content: return
    if p.exists():
        backup=BACKUP/(hashlib.sha256(str(p).encode()).hexdigest()[:12]+'_'+p.name)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists(): shutil.copy2(p,backup)
    p.write_bytes(content)

def frontend(data):
    g=deepcopy(data); links={x[0]:x for x in g.get('links',[])}
    retired={n['id']:n for n in g['nodes'] if n.get('type')==NODE}
    for nid,node in retired.items():
        inp=next(i for i in node['inputs'] if i['name']=='images')
        source=links[inp['link']]
        for link in links.values():
            if link[1]==nid and link[3] not in retired:
                if link[2]!=0: raise ValueError('Report consumer requires manual reconciliation')
                link[1:3]=source[1:3]
    g['nodes']=[n for n in g['nodes'] if n['id'] not in retired]
    g['links']=[x for x in links.values() if x[1] not in retired and x[3] not in retired]
    for n in g['nodes']:
        for inp in n.get('inputs',[]):
            matches=[x[0] for x in g['links'] if x[3]==n['id'] and x[4]==n['inputs'].index(inp)]
            if inp.get('link') is not None: inp['link']=matches[0] if matches else None
        for slot,out in enumerate(n.get('outputs',[])):
            out['links']=[x[0] for x in g['links'] if x[1]==n['id'] and x[2]==slot]
    g.get('extra',{}).pop('pemara_face_refine',None)
    return g

def workflows():
    paths={Path(x['path']) for x in read(HERE/'receipts/deployment.json')['inventory']}
    roots=[ROOT/'ferramentas/video_global_engine',ROOT/'ferramentas/h3_upgrades_20260927',
           Path('D:/PemaraRuntimes/state/ComfyUI-v0.36.0-pemara/user/default/workflows')]
    roots+=list((RUNTIME/'custom_nodes').glob('creative_os_h3_*/workflows'))
    roots+=list((RUNTIME/'custom_nodes').glob('creative_os_h3_*/example_workflows'))
    for root in roots:
        paths.update(p for p in root.rglob('*.json') if 'workflows' in p.parts and not any(x in p.parts for x in ('rollback','archive','receipts','history','.git')))
    changes=[]
    for p in sorted(paths):
        if not p.is_file(): continue
        d=read(p); after=deepcopy(d)
        if isinstance(d,dict) and d and all(isinstance(n,dict) and 'class_type' in n for n in d.values()): after=remove_face_refine(d)
        elif isinstance(d,dict) and isinstance(d.get('nodes'),list): after=frontend(d)
        elif isinstance(d,dict):
            after.pop('faceRefine',None)
            required=after.get('nodeContract',{}).get('required',[])
            if NODE in required: required.remove(NODE)
        if after!=d:
            before=sha(p);save(p,after);changes.append({'path':str(p),'before':before,'after':sha(p)})
    # Keep only Sage exported at runtime, remove the automatic Face Refine hook.
    save(RUNTIME/'custom_nodes/pemara_h3_face_refine/__init__.py',(HERE/'node/__init__.py').read_bytes())
    save(RUNTIME/'custom_nodes/pemara_h3_face_refine/graph.py',(ROOT/'services/studio/h3_face_refine.py').read_bytes())
    save(HERE/'receipts/owner_removal.json',{'status':'REMOVED_FROM_WORKFLOWS_AND_RUNTIME_EXPORTS','checkedFiles':len(paths),
         'changes':changes,'sageCorrectionPreserved':True,'ownerRequest':'UM IXO ESSE FACE REFINE TIRA ISSO, COLOCA O VIDEO ORIGINAL SEM ELE E APAGA DOS WORKFLOWS'})
    print(json.dumps({'checkedFiles':len(paths),'changedFiles':len(changes)}))

def original():
    from services.studio import video_projects as projects
    source=PROJECT/'takes/native_attempt02/original_before_refine.mp4'
    if sha(source)!='38479a34661f026bf047f7b3fb04fe10f55d725d520369ca5549642884f22bea': raise ValueError('Original source hash changed')
    target=PROJECT/'outputs/Leon_primeiro_Licker_RE2_1998_30s_H3_ORIGINAL_audio_nativo_v1.mp4'
    if target.exists():
        previous=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames','-of','json',str(target)]))
        if int(previous['streams'][0]['nb_frames'])!=720:
            rollback=PROJECT/'qc/original_remux_extra_bframes.mp4'
            if rollback.exists(): raise FileExistsError(rollback)
            target.rename(rollback)
    if not target.exists():
        subprocess.run(['ffmpeg','-hide_banner','-nostdin','-v','error','-i',str(source),'-t','30','-frames:v','720','-map','0:v:0','-map','0:a:0','-c:v','libx264','-crf','0','-preset','fast','-c:a','copy','-movflags','+faststart',str(target)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(target)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    if int(v['nb_frames'])!=720 or abs(float(v['duration'])-30)>.001: raise ValueError('Original trim is not exactly 720 frames')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
    # Verify every original decoded frame; preserve native compressed audio packets.
    def frames(path):
        text=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-map','0:v:0','-frames:v','720','-f','framemd5','-'],text=True)
        return [line.split(',')[-1].strip() for line in text.splitlines() if not line.startswith('#')]
    if frames(source)!=frames(target): raise ValueError('Original decoded frames changed')
    def packets(path):
        data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_packets','-show_data_hash','sha256','-show_entries','packet=stream_index,data_hash','-of','json',str(path)]))
        return [[p['data_hash'] for p in data['packets'] if p['stream_index']==i] for i in (0,1)]
    src,dst=packets(source),packets(target)
    if dst[1]!=src[1][:len(dst[1])]: raise ValueError('Compressed original audio packet verification failed')
    old=read(PROJECT/'delivery_candidate.json');old['status']='OWNER_REJECTED_FACE_REFINE';old['ownerApproval']='REJECTED'
    save(PROJECT/'qc/delivery_face_refine_owner_rejected.json',old)
    receipt={'status':'ORIGINAL_READY_FOR_OWNER_REVIEW','ownerApproval':'PENDING_VIDEO_REVIEW',
      'source':{'path':str(source),'sha256':sha(source),'preserved':True},
      'delivery':{'path':str(target),'sha256':sha(target),'frames':720,'seconds':30,'fps':24,'width':v['width'],'height':v['height'],'audioCodec':a['codec_name'],'audioChannels':a['channels'],'audioDuration':a['duration']},
      'faceRefine':{'applied':False,'status':'REMOVED_BY_OWNER'},'audioOrigin':'MiniMax H3 native; original encoded packets retained',
      'checks':{'fullDecode':True,'originalDecodedFramesBitExact':True,'originalAudioPacketsVerified':True,'visualOwnerApproval':False},
      'checkedAt':datetime.now(timezone.utc).isoformat()}
    save(PROJECT/'delivery_candidate.json',receipt)
    queue=read(PROJECT/'take_queue.json');take=queue['takes'][0]
    take.setdefault('rejected_video_history',[]).append({'file':old['delivery']['path'],'sha256':old['delivery']['sha256'],'status':'OWNER_REJECTED','reason':'Face Refine rejected; owner requested original'})
    take['video_generation']['face_refine']={'enabled':False,'status':'REMOVED_BY_OWNER'}
    take['notes']='Original H3 sem Face Refine, audio nativo. Aguardando avaliacao do proprietario.'
    save(PROJECT/'take_queue.json',queue)
    job=take['maestro_last_job_id'];pid=PROJECT.name
    projects.set_take_generation_state(PROJECT.parent,pid,'T01',status='READY',job_id=job,
      result={'provider':'MiniMax H3','native_prompt_id':job,'face_refine':False,'delivery_receipt':'delivery_candidate.json',
              'audio_delivery':{'status':'NATIVE_H3_ATTACHED_PENDING_HUMAN_REVIEW','ready':True,'required':True,'human_listening_required':True,'human_approved':False}},preview_path=target)
    mp=PROJECT/'project_manifest.json';manifest=read(mp)
    if isinstance(manifest.get('candidate_output'),dict): manifest['candidate_output']['status']='OWNER_REJECTED'
    manifest['objective']='Leon descobre o primeiro Licker no RPD de RE2 1998. Video H3 original, sem Face Refine, audio nativo.'
    save(mp,manifest)
    ready=projects.get_project_assembly_readiness(PROJECT.parent,pid)
    candidate=projects.register_project_candidate_output(PROJECT.parent,pid,expected_source_fingerprint=ready['sourceFingerprint'],expected_manifest_sha256=sha(mp),
      record={'file':str(target),'sha256':sha(target),'duration_seconds':30,'width':v['width'],'height':v['height'],'fps':24,'technical_review':receipt['checks']})
    req=read(PROJECT/'production_request.json');req['status']='ORIGINAL_READY_FOR_OWNER_REVIEW';req['videoApproved']=False
    req['faceRefine']={'enabled':False,'status':'REMOVED_BY_OWNER'};save(PROJECT/'production_request.json',req)
    print(json.dumps({'candidate':candidate,'originalDecodedFramesBitExact':True,'originalAudioPacketsVerified':True},ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='workflows': workflows()
    elif sys.argv[1]=='original': original()
