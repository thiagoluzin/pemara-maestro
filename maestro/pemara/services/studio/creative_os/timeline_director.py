"""Typed, bounded continuous H3 timeline compiler; no runtime I/O."""
import copy
import json
from .adapters import H3Adapter
from .ir import CreativeError, digest, validate_ir


def compile_timeline(ir, *, seed, segment_count=2):
    ir = validate_ir(ir)
    if type(segment_count) is not int or not 2 <= segment_count <= 6:
        raise CreativeError('TIMELINE_COUNT', 'Informe 2–6 segmentos.')
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise CreativeError('INVALID_SEED', 'Timeline exige seed explícita.')
    overlap = 22
    minimum = (124 * segment_count - overlap * (segment_count-1)) / 24
    if ir['duration_seconds'] < minimum:
        raise CreativeError('TIMELINE_DURATION', f'Esta divisão exige pelo menos {minimum:.3f} segundos.')
    target = (ir['duration_seconds']*24 + overlap*(segment_count-1)) / segment_count
    frames = min(range(124,363,17),key=lambda n:abs(n-target))
    segment = copy.deepcopy(ir)
    segment['duration_seconds'] = frames / 24
    spec = H3Adapter().build_job(segment, {'seed':seed,'h3_quality_profile':'h3_production'})
    if spec['enable_minimax_h3_native_audio']:
        raise CreativeError('TIMELINE_AUDIO', 'Integração inicial Timeline exporta somente vídeo sem áudio.')
    timeline = {'selection':{'start':0.0,'duration':frames/24},'videoClips':[],'images':[],'audios':[]}
    graph = {
        '1':{'class_type':'UNETLoader','inputs':{'unet_name':'minimax_h3_fl2va_pruned_int8_convrot.safetensors','weight_dtype':'default'}},
        '2':{'class_type':'MiniMaxH3SigmaShift','inputs':{'model':['1',0],'shift_video':12.0,'shift_audio':3.0}},
        '3':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
        '4':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_fp16.safetensors'}},
        '5':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_audio_vae_fp32.safetensors'}},
        '8':{'class_type':'BasicScheduler','inputs':{'model':['2',0],'scheduler':'simple','steps':10,'denoise':1.0}},
        '10':{'class_type':'KSamplerSelect','inputs':{'sampler_name':'res_multistep'}},
        '20':{'class_type':'MiniMaxH3TimelinePlanner','inputs':{'width':1088,'height':608,'generation_seconds':frames/24,'timeline_data':json.dumps(timeline)}},
        '21':{'class_type':'MiniMaxH3FiniteSegmentExpansion','inputs':{'plan':['20',0],'segment_prompts':json.dumps([spec['prompt']]*segment_count,ensure_ascii=False),'segment_count':segment_count,'overlap_frames':overlap,'inject_continuity_instruction':True}},
        '22':{'class_type':'MiniMaxH3FiniteSegmentSampler','inputs':{'model':['2',0],'clip':['3',0],'vae':['4',0],'audio_vae':['5',0],'finite_plan':['21',0],'sampler':['10',0],'sigmas':['8',0],'seed':seed,'continue_audio_latent':False,'ref_image_size':'match'}},
        '23':{'class_type':'CreateVideo','inputs':{'images':['22',1],'fps':24.0,'bit_depth':8}},
        '24':{'class_type':'SaveVideo','inputs':{'video':['23',0],'filename_prefix':'creative_os/timeline','format':'mp4','format.codec':'h264'}},
    }
    from h3_workflow import ensure_h3_sage_attention
    graph = ensure_h3_sage_attention(graph)
    return {'graph':graph,'workflow_hash':digest(graph),'source_ir_hash':digest(ir),'segment_count':segment_count,
        'segment_frames':frames,'overlap_frames':overlap,'output_frames':frames*segment_count-overlap*(segment_count-1),
        'seed':seed,'generation_submitted':False,'human_verdict':None,'base_spec':spec}


def compile_request(request, *, engine_id, seed, profile, native_audio):
    if engine_id != 'minimax_h3' or profile != 'h3_production' or native_audio:
        raise CreativeError('TIMELINE_SCOPE','Timeline exige H3 Production explícito, sem áudio.')
    if not isinstance(request,dict) or set(request)-{'ir','segment_count'}:
        raise CreativeError('TIMELINE_REQUEST','Pedido de Timeline inválido.')
    return compile_timeline(request.get('ir'),seed=seed,segment_count=request.get('segment_count',2))
