"""Owner-selected, mandatory finishing contract for new video upscale jobs."""
from __future__ import annotations
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import dlss5_finishing as dlss

ENGINE = Path(__file__).resolve().parents[2] / 'ferramentas/video_global_engine'
PROFILE_DIR = ENGINE / 'upscale_profiles'
WORKFLOW_DIR = ENGINE / 'workflows/upscaling_obrigatorio'
LEGACY_ANIMATION_PIPELINE = 'seedvr2_3b_rife_exact60_dlss5_foley_v1'
PIPELINE = 'seedvr2_3b_rife_exact60_no_nr_v2'
LEGACY_CONVENTIONAL_PIPELINE = 'lanczos_nvenc_rife_exact60_dlss5_actor_protected_v1'
LEGACY_FULL_FRAME_PIPELINE = 'lanczos_nvenc_rife_exact60_dlss5_full_frame_v2'
CONVENTIONAL_PIPELINE = 'lanczos_nvenc_rife_exact60_no_nr_v3'
POLICY_VERSION = 'upscaling_by_content_anchors_only_20261026_v3'
REQUIRED = True

def pipeline_for(content_kind):
    kind = dlss.content_policy.normalize(content_kind)
    if kind == 'unknown':
        raise ValueError('Definir tipo de produção antes do acabamento; SeedVR2 somente em animation.')
    return PIPELINE if kind == 'animation' else CONVENTIONAL_PIPELINE

def pipeline_from_profile_id(identifier):
    for pipeline in (PIPELINE, CONVENTIONAL_PIPELINE):
        if identifier in {pipeline+tag+suffix for tag in ('_','_mixed_') for suffix in TARGETS.values()}:
            return pipeline
    raise ValueError('Perfil de acabamento desconhecido.')

def assert_content_graph(graph):
    seed_nodes = [node for node in graph.values() if isinstance(node,dict) and
        (node.get('class_type') == 'PemaraUpscaleRequiredSave' or
         'seedvr2' in str(node.get('class_type','')).lower() or
         any('seedvr2' in str(value).lower() for key,value in node.get('inputs',{}).items()
             if key in {'unet_name','vae_name','model_name','model','ckpt_name'}))]
    if seed_nodes and dlss.content_policy.graph_kind(graph) != 'animation':
        raise ValueError('SeedVR2 permitido somente em animation; live_action, mixed e unknown bloqueados.')
    neural_spatial = [node for node in graph.values() if isinstance(node,dict) and
        (node.get('class_type') in {'UpscaleModelLoader','ImageUpscaleWithModel','UltimateSDUpscale'} or
         any(name in str(node.get('class_type','')).lower() for name in ('realesrgan','supir','seedvr2')))]
    if neural_spatial and dlss.content_policy.graph_kind(graph) != 'animation':
        raise ValueError('Live action/mixed exige Lanczos + NVENC; restauração neural espacial substituta bloqueada.')

SEED_MODEL = 'seedvr2_3b_int8_convrot.safetensors'
VAE_MODEL = 'seedvr2_ema_vae_fp16.safetensors'
RIFE_REPO = Path(r'E:\Pemara\third_party\Practical-RIFE')
RIFE_HASH = '6615790efd627772917205db291f51cd392528a157ecbb2ecaeec3bff8eb6de2'
TARGETS = {(1920,1080): '1080p', (1080,1920): '1080p_vertical',
           (2560,1440): '1440p', (1440,2560): '1440p_vertical',
           (3840,2160): '4k', (2160,3840): '4k_vertical'}

def profile_id(width, height, content_kind="animation"):
    try:
        return pipeline_for(content_kind) + ('_mixed_' if content_kind == 'mixed' else '_') + TARGETS[(int(width), int(height))]
    except KeyError:
        raise ValueError('Acabamento obrigatório aceita FHD, QHD e UHD em paisagem ou retrato.')

def load_profile(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    target = data['target']
    expected = canonical_profile(target['width'], target['height'], data.get('content_kind','animation'))
    if data != expected:
        raise ValueError('Perfil obrigatório alterado; não reduzir ou substituir etapas silenciosamente.')
    return data

def canonical_profile(width, height, content_kind='animation'):
    kind = dlss.content_policy.normalize(content_kind)
    pipeline = pipeline_for(kind)
    if pipeline == CONVENTIONAL_PIPELINE:
        data = canonical_profile(width,height,'animation')
        data.update(profile_id=profile_id(width,height,kind), pipeline_version=pipeline,
            content_kind=kind, policy_version=POLICY_VERSION,
            stages=['Practical-RIFE 4.25 exact60 at source resolution',
                    'Lanczos contain/pad + H.264 NVENC',
                    'original audio stream copy'],
            spatial_upscaling={'filter':'lanczos','neural_restoration':False},
            actor_protection={'required':False,'reviewed_mask_per_final_frame':False},
            dlss5_coverage_percent=0,
            visual_qualification='requires_review_of_new_artifact')
        data.pop('seedvr2')
        data.pop('quality_reference')
        return data
    return {'schema_version': '1.0', 'profile_id': profile_id(width,height),
        'pipeline_version': PIPELINE, 'required': True,
        'target': {'width': int(width), 'height': int(height), 'fps': 60,
                   'geometry': 'contain_then_pad_no_crop', 'depth': '8-bit SDR'},
        'stages': ['SeedVR2 3B', 'Practical-RIFE 4.25 exact60', 'original audio stream copy'],
        'seedvr2': {'model': SEED_MODEL, 'vae': VAE_MODEL, 'seed': 20261006,
            'steps': 1, 'cfg': 1.0, 'sampler': 'euler', 'scheduler': 'simple',
            'color_correction': 'lab', 'temporal_chunk_frames': 17, 'latent_overlap': 1,
            'vae_tile': 512, 'vae_overlap': 128, 'vae_temporal_size': 16, 'vae_temporal_overlap': 4},
        'rife': {'version': '4.25', 'model_sha256': RIFE_HASH, 'timestamps': 'j/60',
                 'cut_threshold_mean_rgb': 0.35, 'endpoint': 'clamp_last_frame'},
        'dlss5': {'allowed_on_video':False,'scope':'anchors_only'},
        'audio': {'policy': 'preserve_existing_stream_copy', 'absent': 'remain_silent',
                  'new_foley_generation': False},
        'encode': {'codec': 'h264_nvenc', 'preset': 'p7', 'cq': 15, 'pix_fmt': 'yuv420p'},
        'fallback_allowed': False, 'owner_review_required': True,
        'quality_reference': {'project_id': 're1_tratamento_comparativos_20261006',
            'take_id': 'SEED3B_RIFE60_DLSS5',
            'sha256': '1ce127593045a5d5c8c3932f94535bb778f3c1199819df1fe0a7e1749b17dfef'},
        'visual_qualification': 'owner_approved_RE1_vertical' if (width,height)==(1080,1920)
                                else 'requires_review_of_new_artifact'}

def contain_dimensions(sw,sh,tw,th):
    if min(sw,sh,tw,th) < 2:
        raise ValueError('Geometria inválida.')
    scale = min(Fraction(tw,sw), Fraction(th,sh))
    # Even dimensions are required by the SDR yuv420p delivery contract.
    return max(2,int(sw*scale)//2*2), max(2,int(sh*scale)//2*2)

def spatial_filter(sw, sh, tw, th, *, lanczos):
    cw,ch = contain_dimensions(sw,sh,tw,th) if lanczos else (sw,sh)
    if cw > tw or ch > th:
        raise ValueError('Fonte não cabe na geometria final sem redimensionamento.')
    return (f'scale={cw}:{ch}:flags=lanczos,' if lanczos else '') + f'pad={tw}:{th}:{(tw-cw)//2}:{(th-ch)//2}:black'

def output_frame_count(frames, fps):
    duration = Fraction(int(frames),1) / Fraction(str(fps))
    exact = duration*60
    if exact.denominator != 1:
        raise ValueError('Duração não alinhada a 1/60 s: exige decisão editorial, sem corte silencioso.')
    return int(exact)

def build_workflow(input_file, sw, sh, width, height, filename_prefix, *, content_kind='unknown', protection_manifest=''):
    if protection_manifest:
        raise ValueError('DLSS integral obrigatorio: remover protection_manifest do novo workflow.')
    p = canonical_profile(width,height,content_kind)
    if pipeline_for(content_kind) == CONVENTIONAL_PIPELINE:
        return {'1': {'class_type':'LoadVideo','inputs':{'file':input_file}},
            '15': {'class_type':'PemaraLanczosUpscaleRequiredSave','inputs':{
                'source_video':['1',0], 'width':width, 'height':height,
                'filename_prefix':filename_prefix, 'profile_id':p['profile_id'],
                'content_kind':dlss.content_policy.normalize(content_kind),
                'protection_manifest':str(protection_manifest or '')}}}
    cw,ch = contain_dimensions(sw,sh,width,height)
    template = json.loads((WORKFLOW_DIR/'seedvr2_stage_template.json').read_text(encoding='utf-8'))
    graph = copy.deepcopy(template)
    graph['1']['inputs']['file'] = input_file
    graph['3']['inputs'].update(width=cw,height=ch)
    graph.pop('14',None)
    graph['15'] = {'class_type': 'PemaraUpscaleRequiredSave', 'inputs': {
        'images': ['13',0], 'source_video': ['1',0], 'width': width, 'height': height,
        'filename_prefix': filename_prefix, 'profile_id': p['profile_id'],
        'content_kind': dlss.content_policy.normalize(content_kind),
        'protection_manifest': str(protection_manifest or '')}}
    return graph

def assert_graph(graph):
    """Validate the exact linked Seed path; a model name elsewhere is insufficient."""
    # The executor adds cache fingerprints after submission. Those are runtime
    # metadata, while class types and linked inputs define the processing path.
    graph = {key: {'class_type':node['class_type'], 'inputs':node['inputs']}
             for key,node in graph.items()}
    assert_content_graph(graph)
    end = graph['15']
    inputs = end['inputs']
    kind = inputs.get('content_kind','unknown')
    p = canonical_profile(int(inputs['width']),int(inputs['height']),kind)
    conventional = pipeline_for(kind) == CONVENTIONAL_PIPELINE
    exporter = 'PemaraLanczosUpscaleRequiredSave' if conventional else 'PemaraUpscaleRequiredSave'
    if end['class_type'] != exporter or inputs['profile_id'] != p['profile_id']:
        raise ValueError('Exportador/perfil incompatível com o tipo de produção.')
    sw,sh = (inputs['width'],inputs['height']) if conventional else (
        graph['3']['inputs']['width'],graph['3']['inputs']['height'])
    template = build_workflow(graph['1']['inputs']['file'],sw,sh,
        inputs['width'],inputs['height'],inputs['filename_prefix'],
        content_kind=kind,protection_manifest=inputs.get('protection_manifest',''))
    if not conventional:
        template['3']['inputs'].update(width=sw,height=sh)
    if graph != template:
        raise ValueError('Workflow não corresponde ao acabamento obrigatório por tipo de produção.')
    return p

def receipt_path(path):
    return Path(str(path)+'.upscaling.json')

def native_source(path):
    """Use the retained pre-DLSS bytes when the approved preview had DLSS."""
    path=Path(path).resolve()
    receipt=dlss.valid_receipt(path)
    if not receipt or not receipt.get('source'):
        return path
    original=Path(receipt['source']).resolve()
    if not original.is_file() or dlss.sha(original)!=receipt.get('source_sha256'):
        raise ValueError('Original anterior ao DLSS ausente/divergente; sem upscale recursivo silencioso.')
    before,after=dlss._probe(original),dlss._probe(path)
    a=next(s for s in before['streams'] if s['codec_type']=='video')
    b=next(s for s in after['streams'] if s['codec_type']=='video')
    if any(a.get(k)!=b.get(k) for k in ('width','height','avg_frame_rate','nb_read_frames')):
        raise ValueError('Preview conformado não equivale à fonte nativa; selecionar o original correto.')
    audio_a=any(s['codec_type']=='audio' for s in before['streams'])
    audio_b=any(s['codec_type']=='audio' for s in after['streams'])
    if audio_a!=audio_b or (audio_a and dlss._audio_hash(original)!=dlss._audio_hash(path)):
        raise ValueError('Áudio da fonte preservada diverge do preview aprovado.')
    return original

def valid_receipt(path):
    try:
        data = json.loads(receipt_path(path).read_text(encoding='utf-8'))
        if data.get('technical_pass') is True and data.get('output_sha256') == dlss.sha(path):
            if data.get('pipeline_version') in {PIPELINE,CONVENTIONAL_PIPELINE} and data.get('dlss5_applied') is False:
                return data
            if data.get('pipeline_version') in {LEGACY_ANIMATION_PIPELINE,LEGACY_FULL_FRAME_PIPELINE,LEGACY_CONVENTIONAL_PIPELINE} and dlss.valid_receipt(path):
                return data
    except (OSError,ValueError):
        pass
    return None

def policy_status():
    return {'required': True, 'policy_version':POLICY_VERSION, 'pipeline': 'selected_by_content_kind',
        'routes':{'animation':PIPELINE,'live_action':CONVENTIONAL_PIPELINE,'mixed':CONVENTIONAL_PIPELINE,'unknown':'blocked_before_render'},
        'seedvr2_allowed_only_for':'animation', 'target_fps': 60,
        'profiles': [canonical_profile(w,h,k) for k in ('animation','live_action','mixed') for w,h in TARGETS],
        'stages': {k:canonical_profile(1080,1920,k)['stages'] for k in ('animation','live_action','mixed')},
        'applies_to': 'new_upscale_jobs_after_source_visual_approval',
        'preserve_native_generation_and_engine': True, 'raw_fallback': False,
        'historical_media_auto_migration': False,
        'dlss5_content_policy': dlss.content_policy.status()}

def assert_finished_sources(sources, content_kind):
    expected = pipeline_for(content_kind)
    proofs=[valid_receipt(path) for path in sources]
    if not sources or not all(proofs):
        raise ValueError('Fontes sem recibos completos de acabamento.')
    if any(proof['pipeline_version'] != expected for proof in proofs):
        raise ValueError('Fontes incompatíveis com o tipo atual: SeedVR2 somente em animação; selecionar fontes nativas para live action.')
    return proofs

def inherit_assembly(sources,dest, *, content_kind='unknown'):
    proofs=assert_finished_sources(sources,content_kind)
    dlss.preserve_video_policy(dest)
    pipelines = {proof['pipeline_version'] for proof in proofs}
    if len(pipelines) != 1:
        raise ValueError('Montagem mistura acabamentos diferentes; revisar fontes antes de montar.')
    data={'required':True,'pipeline_version':next(iter(pipelines)),
          'content_kind':dlss.content_policy.normalize(content_kind),'policy_version':POLICY_VERSION,
          'output':str(Path(dest).resolve()),
          'output_sha256':dlss.sha(dest),'technical_pass':True,'dlss5_applied':False,
          'method':'video_bitstream_copy_from_required_finished_sources',
          'inherited_from':[{'file':str(path),'sha256':proof['output_sha256'],
                             'profile_id':proof.get('profile_id')} for path,proof in zip(sources,proofs)],
          'human_approval':'PENDING'}
    dlss._atomic_json(receipt_path(dest),data)
    return data
