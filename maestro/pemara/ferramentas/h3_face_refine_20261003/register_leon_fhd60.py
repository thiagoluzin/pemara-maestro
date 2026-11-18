"""Expose the finished original in Maestro, retaining artifact-scoped approval."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'services/studio'))
from services.studio import video_projects as vp
P=ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
QC=P/'qc/fhd60_original_v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):vp._atomic_json_write(p,d)

def main():
    r=read(QC/'delivery.json');source=Path(r['source']);target=Path(r['file'])
    if sha(source)!=r['sourceSha256'] or sha(target)!=r['sha256']:raise ValueError('Source or derivative changed')
    r['visualSampleReview']={'reviewed':True,'method':'30 one-second samples plus 18s closeup and 29.8s ending',
                            'limitations':'Sample inspection does not certify every interpolated frame or owner approval',
                            'humanOwnerApproval':False}
    save(QC/'delivery.json',r)
    for name in ['project_manifest.json','take_queue.json','production_request.json','delivery_candidate.json']:
        backup=QC/('before_register_'+name)
        if not backup.exists():shutil.copy2(P/name,backup)
    q=read(P/'take_queue.json');take=q['takes'][0]
    take['owner_approved_source']={'file':str(source),'sha256':r['sourceSha256'],'evidence':'qc/fhd60_original_v1/owner_picture_lock.json','scope':'Exact original 30s native24; new FHD60 derivative pending review'}
    take['video_generation']['face_refine']={'enabled':False,'status':'REMOVED_BY_OWNER'}
    take['notes']='Original aprovado; acabamento Full HD 1920x1080 60fps com audio nativo, sem Face Refine. Derivado disponivel para revisao.'
    take['finishing']={'width':1920,'height':1080,'fps':60,'receipt':'qc/fhd60_original_v1/delivery.json','ownerApproved':False}
    q['assembly']['final'].update(width=1920,height=1080,fps=60)
    save(P/'take_queue.json',q)
    vp.set_take_generation_state(P.parent,P.name,'T01',status='READY',job_id=take['maestro_last_job_id'],preview_path=target,
        result={'provider':'MiniMax H3 + Practical-RIFE 4.25 finishing','native_prompt_id':take['maestro_last_job_id'],
                'face_refine':False,'source_owner_approved':True,'source_sha256':r['sourceSha256'],
                'delivery_receipt':'qc/fhd60_original_v1/delivery.json',
                'audio_delivery':{'status':'NATIVE_H3_PRESERVED_ENCODED_PACKETS','ready':True,'required':True,'human_listening_required':True,'human_approved':False}})
    mp=P/'project_manifest.json';m=read(mp)
    previous=m.get('candidate_output',{})
    if previous.get('sha256')==r['sourceSha256']:
        previous.update(status='OWNER_APPROVED_SOURCE',human_approved=True,approval_evidence='qc/fhd60_original_v1/owner_picture_lock.json')
    m.update(final_resolution='1920x1080',preview_resolution='1920x1080',fps_final=60,fps_preview=60,
             finishing={'status':'READY_FOR_REVIEW','faceRefine':False,'sourceOwnerApproved':True,'derivativeOwnerApproved':False,'receipt':'qc/fhd60_original_v1/delivery.json'})
    save(mp,m)
    readiness=vp.get_project_assembly_readiness(P.parent,P.name)
    candidate=vp.register_project_candidate_output(P.parent,P.name,expected_source_fingerprint=readiness['sourceFingerprint'],expected_manifest_sha256=sha(mp),
       record={'file':str(target),'sha256':r['sha256'],'duration_seconds':30,'width':1920,'height':1080,'fps':60,
               'technical_review':{'fullDecode':True,'audioEncodedPacketsUnchanged':True,'faceRefine':False,'visualSamplesReviewed':True,'ownerApproval':False}})
    save(P/'delivery_candidate.json',{'status':'FHD60_READY_FOR_OWNER_REVIEW','source':{'path':str(source),'sha256':r['sourceSha256'],'ownerApproved':True},
         'delivery':{'path':str(target),'sha256':r['sha256'],'width':1920,'height':1080,'fps':60,'frames':1800,'seconds':30},
         'faceRefine':{'applied':False,'status':'REMOVED_BY_OWNER'},'audioOrigin':'MiniMax H3 native; encoded packets unchanged',
         'checks':r,'ownerApproval':'PENDING_DERIVATIVE_REVIEW'})
    req=read(P/'production_request.json');req.update(status='FHD60_READY_FOR_OWNER_REVIEW',videoApproved=False,
         sourceOriginalApproved=True,finishing={'width':1920,'height':1080,'fps':60,'faceRefine':False,'sourceSha256':r['sourceSha256'],'outputSha256':r['sha256']})
    save(P/'production_request.json',req)
    print(json.dumps(candidate,ensure_ascii=False))

if __name__=='__main__':main()
