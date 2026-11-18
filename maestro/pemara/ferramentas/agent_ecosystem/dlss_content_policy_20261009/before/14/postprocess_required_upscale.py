"""Maestro-owned backend worker for the mandatory approved upscale route.

Codex must submit this workflow through comfyui-local MCP, never execute this
backend client's non-dry-run mode. --dry-run performs local discovery only.
"""
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
import uuid

STUDIO = Path(__file__).resolve().parents[3]/'services/studio'
sys.path.insert(0,str(STUDIO))
import dlss5_finishing as dlss
import upscaling_required as policy

IO_ROOT = policy.ENGINE.parent/'ComfyUI'

def http(base,route,data=None):
    req = urllib.request.Request(base.rstrip('/')+route,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.load(r)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output_dir',type=Path)
    p.add_argument('--name',default='candidate')
    p.add_argument('--work-dir',type=Path,required=True)
    p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--comfy-url',default='http://127.0.0.1:8188')
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--dry-run',action='store_true')
    # Accepted for compatibility with the existing worker command contract.
    p.add_argument('--gpu',default=0)
    p.add_argument('--chunk-size',default=17)
    p.add_argument('--per-batch',default=1)
    a=p.parse_args(argv)
    profile=policy.load_profile(a.profile)
    dlss.preflight()
    source=a.source.resolve()
    source_hash=dlss.sha(source)
    if source_hash.upper()!=a.expected_sha256.upper():
        raise ValueError('Fonte alterada; upscale bloqueado.')
    restoration_source=policy.native_source(source)
    restoration_hash=dlss.sha(restoration_source)
    probe=dlss._probe(restoration_source)
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    fps=Fraction(video['avg_frame_rate'])
    if Fraction(video['r_frame_rate'])!=fps or not 24<=fps<=60:
        raise ValueError('CFR 24..60 FPS obrigatório.')
    if video['pix_fmt'] not in {'yuv420p','yuvj420p','rgb24','bgr24','yuv444p'} or video.get('color_transfer') in {'smpte2084','arib-std-b67'}:
        raise ValueError('SDR 8-bit obrigatório; HDR requer outro perfil.')
    if sum(s['codec_type']=='audio' for s in probe['streams'])>1:
        raise ValueError('Múltiplas faixas exigem qualificação; sem descarte silencioso.')
    frames=int(video['nb_read_frames'])
    out_frames=policy.output_frame_count(frames,str(fps))
    target=profile['target']
    artifacts = [policy.RIFE_REPO/'train_log/flownet.pkl',
                 STUDIO/'rife_required_runner.py',
                 policy.WORKFLOW_DIR/'seedvr2_stage_template.json',
                 Path(policy.__file__), Path(dlss.__file__), Path(__file__),
                 dlss.WRAPPER,
                 policy.ENGINE.parent/'comfy_extensions/pemara_upscaling_required/__init__.py']
    hashes = {str(x):dlss.sha(x) for x in artifacts}
    if hashes[str(artifacts[0])]!=policy.RIFE_HASH:
        raise ValueError('Modelo RIFE divergente.')
    runtime_models = Path(r'D:\PemaraRuntimes\ComfyUI-v0.36.0-pemara\models')
    models = [runtime_models/'diffusion_models'/policy.SEED_MODEL,
              runtime_models/'vae'/policy.VAE_MODEL]
    for model in models:
        if not model.is_file():
            raise ValueError('Modelo obrigatório ausente: '+model.name)
        hashes[str(model)] = dlss.sha(model)
    inputs={'pipeline_version':policy.PIPELINE,'profile':profile,
            'source':{'path':str(source),'sha256':source_hash},
            'restoration_source':{'path':str(restoration_source),'sha256':restoration_hash},
            'source_frames':frames,'source_fps':str(fps),'artifact_hashes':hashes}
    fingerprint=hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()
    required_bytes = max(2*1024**3,target['width']*target['height']*out_frames*2)
    print('[plan] PROCESSING_FINGERPRINT='+fingerprint,flush=True)
    print('[plan] REQUIRED_WORK_BYTES='+str(required_bytes),flush=True)
    if a.dry_run:
        print('[dry-run] local-only; no ComfyUI interaction, GPU or writes',flush=True)
        return 0
    a.work_dir.mkdir(parents=True,exist_ok=True)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex[:12]
    upload=IO_ROOT/'input'/('required_upscale_'+restoration_hash[:16]+restoration_source.suffix.lower())
    if not upload.exists():
        shutil.copy2(restoration_source,upload)
    if dlss.sha(upload)!=restoration_hash:
        raise ValueError('Cópia de entrada divergente.')
    graph=policy.build_workflow(upload.name,video['width'],video['height'],
        target['width'],target['height'],'upscaling_obrigatorio/'+token)
    policy.assert_graph(graph)
    dlss._atomic_json(a.work_dir/('workflow_'+token+'.api.json'),graph)
    # Autonomous Maestro backend operation. Codex uses the MCP equivalent.
    queue=http(a.comfy_url,'/queue')
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise RuntimeError('ComfyUI ocupado; aguardar GPU, sem fallback.')
    for name in {n['class_type'] for n in graph.values()}:
        if name not in http(a.comfy_url,'/object_info/'+name):
            raise RuntimeError('Nó obrigatório ausente: '+name)
    submitted=http(a.comfy_url,'/prompt',{'prompt':graph,'client_id':'maestro_required_upscale_'+token})
    if submitted.get('node_errors') or not submitted.get('prompt_id'):
        raise RuntimeError('Validação do workflow obrigatório recusada: '+json.dumps(submitted))
    pid=submitted['prompt_id']
    print('[upscale] COMFY_PROMPT_ID='+pid,flush=True)
    deadline=time.monotonic()+7200
    entry=None
    while time.monotonic()<deadline:
        entry=http(a.comfy_url,'/history/'+pid).get(pid)
        if entry:
            break
        time.sleep(1)
    if not entry or entry.get('status',{}).get('status_str')!='success':
        raise RuntimeError('Acabamento não concluído; fonte e intermediários preservados: '+json.dumps(entry))
    records=entry.get('outputs',{}).get('15',{}).get('videos',[])
    if len(records)!=1:
        raise ValueError('Resultado obrigatório sem vídeo único verificável.')
    record=records[0]
    delivered=(IO_ROOT/'output'/record.get('subfolder','')/record['filename']).resolve()
    if not delivered.is_relative_to((IO_ROOT/'output').resolve()):
        raise ValueError('Resultado fora da raiz de output.')
    proof=policy.valid_receipt(delivered)
    if not proof or proof['source_sha256']!=restoration_hash:
        raise ValueError('Resultado sem recibo da cadeia completa.')
    if dlss.sha(source)!=source_hash:
        raise ValueError('Fonte alterada durante o processamento.')
    if dlss.sha(restoration_source)!=restoration_hash:
        raise ValueError('Fonte de restauração alterada durante o processamento.')
    name=Path(a.name).name.replace(' ','_')
    candidate=a.output_dir/(name+'_required_'+fingerprint[:12].lower()+'_'+token+'.mp4')
    shutil.copy2(delivered,candidate)
    dlss.carry_receipt(delivered,candidate)
    proof=dict(proof,output=str(candidate.resolve()),output_sha256=dlss.sha(candidate))
    dlss._atomic_json(policy.receipt_path(candidate),proof)
    sidecar=candidate.with_suffix('.json')
    payload={'schema_version':'2.0','type':'pemara_hd_review_candidate_result',
        'pipeline_version':policy.PIPELINE,'profile_id':profile['profile_id'],
        'processing_fingerprint':fingerprint,'fingerprint':{'value':fingerprint,'inputs':inputs},
        'source_sha256':source_hash,'candidate':str(candidate.resolve()),
        'candidate_sha256':dlss.sha(candidate),'qc_status':'technical_pass_visual_qc_pending',
        'technical_validation':{'status':'technical_pass','full_chain':proof},
        'human_approval':{'status':'pending','claimed_by_postprocessor':False},
        'comfy_prompt_ids':[pid]}
    dlss._atomic_json(sidecar,payload)
    print('[done] REVIEW_CANDIDATE='+str(candidate.resolve()),flush=True)
    print('[done] SIDECAR='+str(sidecar.resolve()),flush=True)
    print('[done] PROCESSING_FINGERPRINT='+fingerprint,flush=True)
    print('[done] REUSED=false',flush=True)
    return 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('[error] '+str(error),file=sys.stderr,flush=True)
        raise SystemExit(1)
