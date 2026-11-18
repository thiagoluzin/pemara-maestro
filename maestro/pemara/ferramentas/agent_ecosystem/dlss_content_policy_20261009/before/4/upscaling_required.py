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
PIPELINE = 'seedvr2_3b_rife_exact60_dlss5_foley_v1'
REQUIRED = True
SEED_MODEL = 'seedvr2_3b_int8_convrot.safetensors'
VAE_MODEL = 'seedvr2_ema_vae_fp16.safetensors'
RIFE_REPO = Path(r'E:\Pemara\third_party\Practical-RIFE')
RIFE_HASH = '6615790efd627772917205db291f51cd392528a157ecbb2ecaeec3bff8eb6de2'
TARGETS = {(1920,1080): '1080p', (1080,1920): '1080p_vertical',
           (2560,1440): '1440p', (1440,2560): '1440p_vertical',
           (3840,2160): '4k', (2160,3840): '4k_vertical'}

def profile_id(width, height):
    try:
        return PIPELINE + '_' + TARGETS[(int(width), int(height))]
    except KeyError:
        raise ValueError('Acabamento obrigatório aceita FHD, QHD e UHD em paisagem ou retrato.')

def load_profile(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    target = data['target']
    expected = canonical_profile(target['width'], target['height'])
    if data != expected:
        raise ValueError('Perfil obrigatório alterado; não reduzir ou substituir etapas silenciosamente.')
    return data

def canonical_profile(width, height):
    return {'schema_version': '1.0', 'profile_id': profile_id(width,height),
        'pipeline_version': PIPELINE, 'required': True,
        'target': {'width': int(width), 'height': int(height), 'fps': 60,
                   'geometry': 'contain_then_pad_no_crop', 'depth': '8-bit SDR'},
        'stages': ['SeedVR2 3B', 'Practical-RIFE 4.25 exact60', 'DLSS 5 Natural', 'original audio stream copy'],
        'seedvr2': {'model': SEED_MODEL, 'vae': VAE_MODEL, 'seed': 20261006,
            'steps': 1, 'cfg': 1.0, 'sampler': 'euler', 'scheduler': 'simple',
            'color_correction': 'lab', 'temporal_chunk_frames': 17, 'latent_overlap': 1,
            'vae_tile': 512, 'vae_overlap': 128, 'vae_temporal_size': 16, 'vae_temporal_overlap': 4},
        'rife': {'version': '4.25', 'model_sha256': RIFE_HASH, 'timestamps': 'j/60',
                 'cut_threshold_mean_rgb': 0.35, 'endpoint': 'clamp_last_frame'},
        'dlss5': {'profile': dlss.PROFILE, 'parameters': dict(dlss.PARAMETERS)},
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

def output_frame_count(frames, fps):
    duration = Fraction(int(frames),1) / Fraction(str(fps))
    exact = duration*60
    if exact.denominator != 1:
        raise ValueError('Duração não alinhada a 1/60 s: exige decisão editorial, sem corte silencioso.')
    return int(exact)

def build_workflow(input_file, sw, sh, width, height, filename_prefix):
    p = canonical_profile(width,height)
    cw,ch = contain_dimensions(sw,sh,width,height)
    template = json.loads((WORKFLOW_DIR/'seedvr2_stage_template.json').read_text(encoding='utf-8'))
    graph = copy.deepcopy(template)
    graph['1']['inputs']['file'] = input_file
    graph['3']['inputs'].update(width=cw,height=ch)
    graph.pop('14',None)
    graph['15'] = {'class_type': 'PemaraUpscaleRequiredSave', 'inputs': {
        'images': ['13',0], 'source_video': ['1',0], 'width': width, 'height': height,
        'filename_prefix': filename_prefix, 'profile_id': p['profile_id']}}
    return graph

def assert_graph(graph):
    """Validate the exact linked Seed path; a model name elsewhere is insufficient."""
    # The executor adds cache fingerprints after submission. Those are runtime
    # metadata, while class types and linked inputs define the processing path.
    graph = {key: {'class_type':node['class_type'], 'inputs':node['inputs']}
             for key,node in graph.items()}
    end = graph['15']
    p = canonical_profile(int(end['inputs']['width']),int(end['inputs']['height']))
    if end['class_type'] != 'PemaraUpscaleRequiredSave' or end['inputs']['profile_id'] != p['profile_id']:
        raise ValueError('Exportador/perfil obrigatório inválido.')
    template = build_workflow(graph['1']['inputs']['file'],
        graph['3']['inputs']['width'],graph['3']['inputs']['height'],
        end['inputs']['width'],end['inputs']['height'],end['inputs']['filename_prefix'])
    # Geometry may have even rounding; use the explicitly planned dimensions.
    template['3']['inputs'].update(width=graph['3']['inputs']['width'],height=graph['3']['inputs']['height'])
    if graph != template:
        raise ValueError('Workflow obrigatório não corresponde ao caminho aprovado de SeedVR2 3B.')
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
        if data.get('pipeline_version') == PIPELINE and data.get('technical_pass') is True and data.get('output_sha256') == dlss.sha(path) and dlss.valid_receipt(path):
            return data
    except (OSError,ValueError):
        pass
    return None

def policy_status():
    return {'required': True, 'pipeline': PIPELINE, 'target_fps': 60,
        'profiles': [canonical_profile(w,h) for w,h in TARGETS],
        'stages': canonical_profile(1080,1920)['stages'],
        'applies_to': 'new_upscale_jobs_after_source_visual_approval',
        'preserve_native_generation_and_engine': True, 'raw_fallback': False,
        'historical_media_auto_migration': False}

def inherit_assembly(sources,dest):
    proofs=[valid_receipt(path) for path in sources]
    if not sources or not all(proofs) or not dlss.valid_receipt(dest):
        raise ValueError('Master exige fontes com SeedVR2 3B + RIFE60 + DLSS5 comprovados.')
    data={'required':True,'pipeline_version':PIPELINE,'output':str(Path(dest).resolve()),
          'output_sha256':dlss.sha(dest),'technical_pass':True,
          'method':'video_bitstream_copy_from_required_finished_sources',
          'inherited_from':[{'file':str(path),'sha256':proof['output_sha256'],
                             'profile_id':proof.get('profile_id')} for path,proof in zip(sources,proofs)],
          'human_approval':'PENDING'}
    dlss._atomic_json(receipt_path(dest),data)
    return data
