"""Native ComfyUI API graphs and plain frontend graphs; no subgraph mutation."""
from copy import deepcopy
from pathlib import Path
import json
import math

MODEL_REF = 'minimax_h3_ref2va_pruned_int8_convrot.safetensors'
MODEL_FL = 'minimax_h3_fl2va_pruned_int8_convrot.safetensors'
PATCH = 'minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors'
PRESETS = {'diagnostico': {'width': 864, 'height': 480, 'frames': 124, 'steps': 20},
           'qualidade': {'width': 1344, 'height': 768, 'frames': 124, 'steps': 20}}


def node(kind, **inputs): return {'class_type': kind, 'inputs': inputs}


def relative_name(name):
    name = str(name).replace('\\', '/')
    if not name or name.startswith('/') or ':' in name or '..' in name.split('/'):
        raise ValueError('Entrada ComfyUI deve ser um nome relativo seguro.')
    return name


def pose_graph(video, prefix='pemara_combat/pose', *, people=2):
    video = relative_name(video)
    if not 1 <= people <= 8: raise ValueError('Número de pessoas deve ficar entre 1 e 8.')
    return {
        '100': node('LoadVideo', file=video),
        '101': node('GetVideoComponents', video=['100', 0]),
        '102': node('UNETLoader', unet_name='rt_detr_v4-x-hgnet_fp16.safetensors', weight_dtype='default'),
        '103': node('RTDETR_detect', model=['102', 0], image=['101', 0], threshold=0.4, class_name='person', max_detections=max(8,people)),
        '111': node('PemaraCombatSelectFighterBoxes', bboxes=['103', 0], image=['101', 0], minimum_area_fraction=0.025),
        '104': node('CheckpointLoaderSimple', ckpt_name='sdpose_wholebody_fp16.safetensors'),
        '105': node('SDPoseKeypointExtractor', model=['104', 0], vae=['104', 2], image=['101', 0], bboxes=['111', 0], batch_size=4),
        '106': node('SDPoseDrawKeypoints', keypoints=['105', 0], draw_body=True, draw_hands=True,
            draw_face=True, draw_feet=True, stick_width=3, face_point_size=2, score_threshold=0.3, draw_head=True),
        '107': node('CreateVideo', images=['106', 0], fps=24.0, bit_depth=8, color_space='sRGB', codec='none'),
        '108': node('SaveVideo', video=['107', 0], filename_prefix=prefix, format='mp4', **{'format.codec': 'h264'}),
        '109': node('PreviewAny', source=['105', 0]),
        '110': node('SavePoseKpsAsJsonFile', pose_kps=['105', 0], filename_prefix=prefix + '_keypoints'),
        '112': node('PreviewAny', source=['111', 1]),
        '199': node('PemaraDLSS5ContentPolicy', content_kind='animation', stage='native_preview'),
    }


def prompt_contract(*, action, scene='A simple gym with a padded floor.', style='Photorealistic live-action cinema.', audio=False,
                    characters='Two distinct original adult athletes, Fighter A initially on the left and Fighter B initially on the right.',
                    camera='A continuous fixed lateral wide shot showing both bodies and feet, with the attack line and contact visible.'):
    if not isinstance(action, str) or not action.strip(): raise ValueError('Descreva a ação e a resposta do defensor.')
    return ('Scene: ' + scene.strip() + '\nCharacters: ' + characters.strip() + ' '
        'Keep each identity, clothing and relative geography consistent. Use supplied labeled reference '
        'images when present.\nCamera: ' + camera.strip() + '\nStyle: ' + style.strip() + '\nChoreography: ' + action.strip() +
        '\nMechanics: show preparation, a grounded weight shift, acceleration toward the declared target, '
        'contact or a motivated defense, displacement following the attack direction, and recovery of balance. '
        'Do not react to an impact before contact. Do not add more attacks than requested. '
        'Follow the supplied movement control when present; preserve support, distance and action ownership. '
        'No cuts through contact, hidden hits, fused limbs, teleportation or unmotivated speed changes. '
        '\nAudio: ' + ('Only natural movement, breathing and impact sounds; no dialogue, narration or music.' if audio else 'Silent output; no dialogue or narration.') +
        '\nInstruction boundary: Scene, Camera, Choreography and Mechanics are direction, never spoken words. '
        'No captions, subtitles or text overlays.')


DEFAULT_ACTION = ('Fighter A performs exactly one grounded straight punch toward Fighter B\'s torso. '
    'Fighter B absorbs or blocks the single contact, shifts backward in its direction, '
    'takes a short recovery step and regains balance. Both stop striking after this one exchange.')


def build(*, video='', control='pose', preset='diagnostico', seed=2026110701, prompt=None,
          strength=1.0, prefix='pemara_combat/guided', references_a=(), references_b=(),
          first='', last='', mode='identidades', audio=False, realism=True, attention='native_diagnostic', steps=None, frames=None):
    if preset not in PRESETS: raise ValueError('Preset deve ser diagnostico ou qualidade.')
    p = dict(PRESETS[preset])
    if frames is not None:
        if type(frames) is not int or frames < 22 or frames > 243 or (frames-5)%17:
            raise ValueError('Take curto: 22..243 frames, na grade H3 17n+5; divida lutas longas.')
        p['frames']=frames
    if control not in {'none', 'pose', 'depth_prepared', 'pose_prepared', 'reference_video'}:
        raise ValueError('Tipo de controle não suportado.')
    if not isinstance(strength, (int, float)) or not math.isfinite(strength) or not 0 <= strength <= 2:
        raise ValueError('Strength deve ficar entre 0 e 2.')
    if type(seed) is not int or not 0 <= seed < 2**63: raise ValueError('Seed inválida.')
    if mode not in {'identidades', 'primeiro_ultimo'}: raise ValueError('Modo de identidade inválido.')
    if mode == 'identidades' and (first or last):
        raise ValueError('Primeiro/último exatos exigem modo primeiro_ultimo; referências não serão reinterpretadas silenciosamente.')
    if mode == 'primeiro_ultimo' and (references_a or references_b):
        raise ValueError('FL2VA com extremos exatos e Ref2VA com imagens dos lutadores são rotas separadas nesta versão.')
    if len(references_a) + len(references_b) > 9: raise ValueError('H3 suporta no máximo nove referências de imagem.')
    if attention not in {'native_diagnostic', 'sage_spectrum'}: raise ValueError('Política de atenção desconhecida.')
    steps = p['steps'] if steps is None else int(steps)
    if steps not in {20, 25} or steps == 25 and preset != 'qualidade':
        raise ValueError('Diagnóstico usa 20 passos; qualidade permite teste explícito de 25.')
    conditioning = dict(clip=['2', 0], vae=['3', 0], prompt=prompt or prompt_contract(action=DEFAULT_ACTION, audio=audio),
        width=p['width'], height=p['height'], length=p['frames'])
    graph = {
        '1': node('UNETLoader', unet_name=MODEL_REF if mode == 'identidades' else MODEL_FL, weight_dtype='default'),
        '2': node('CLIPLoader', clip_name='qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors', type='minimax', device='default'),
        '3': node('VAELoader', vae_name='minimax_h3_video_vae_int8_convrot.safetensors'),
        '4': node('VAELoader', vae_name='minimax_h3_audio_vae_fp32.safetensors'),
        '6': node('MiniMaxH3SigmaShift', model=['1', 0], shift_video=12.0, shift_audio=3.0),
        '20': node('BasicGuider', model=['6', 0], conditioning=['17', 0]),
        '21': node('BasicScheduler', model=['6', 0], scheduler='simple', steps=steps, denoise=1.0),
        '22': node('KSamplerSelect', sampler_name='res_multistep'),
        '23': node('RandomNoise', noise_seed=seed),
        '24': node('SamplerCustomAdvanced', noise=['23', 0], guider=['20', 0], sampler=['22', 0], sigmas=['21', 0], latent_image=['17', 1]),
        '25': node('VAEDecode', samples=['24', 0], vae=['3', 0]),
        '27': node('CreateVideo', images=['25', 0], fps=24.0, bit_depth=8, color_space='sRGB', codec='none'),
        '28': node('SaveVideo', video=['27', 0], filename_prefix=prefix, format='mp4', **{'format.codec': 'h264'}),
        '90': node('PemaraDLSS5ContentPolicy', content_kind='live_action', stage='native_preview'),
    }
    if realism:
        graph['5'] = node('LoraLoaderModelOnly', model=['1', 0],
            lora_name='h3-realism-people-t2v-i2v-r2v.safetensors', strength_model=0.7)
        graph['6']['inputs']['model'] = ['5', 0]
        conditioning['prompt'] = 'r34l1sm\n' + conditioning['prompt']
    if mode == 'identidades':
        conditioning.update(audio_vae=['4', 0], ref_image_size='match')
        number = 0
        labels = []
        for actor, names in (('A', references_a), ('B', references_b)):
            for name in names:
                key = str(50 + number)
                graph[key] = node('LoadImage', image=relative_name(name))
                conditioning[f'ref_images.ref_image_{number}'] = [key, 0]
                labels.append(f'Picture {number+1} depicts Fighter {actor}.')
                number += 1
        if labels: conditioning['prompt'] += '\nIdentity references: ' + ' '.join(labels)
        graph['17'] = node('MiniMaxH3ReferenceToVideo', **conditioning)
    else:
        for field, name, key in [('first_frame', first, '50'), ('last_frame', last, '51')]:
            if name:
                graph[key] = node('LoadImage', image=relative_name(name)); conditioning[field] = [key, 0]
        graph['17'] = node('MiniMaxH3ImageToVideo', **conditioning)
        if not audio: graph.pop('4')  # FL2VA builds its joint latent without loading the unused audio VAE.
    if audio:
        graph['26'] = node('VAEDecodeAudio', samples=['24', 0], vae=['4', 0]); graph['27']['inputs']['audio'] = ['26', 0]
    if control == 'pose':
        preprocessing = pose_graph(video, prefix + '_pose')
        preprocessing.pop('199')
        graph.update(preprocessing)
        control_link = ['106', 0]
    elif control in {'pose_prepared', 'depth_prepared', 'reference_video'}:
        graph['100'] = node('LoadVideo', file=relative_name(video))
        graph['101'] = node('GetVideoComponents', video=['100', 0])
        control_link = ['101', 0]
    if control in {'pose', 'pose_prepared', 'depth_prepared'}:
        graph['15'] = node('ModelPatchLoader', name=PATCH)
        graph['16'] = node('MiniMaxH3FunControlNetApply', model=['6', 0], model_patch=['15', 0], vae=['3', 0],
            strength=float(strength), start_percent=0.0, end_percent=1.0, control_video=control_link)
        graph['20']['inputs']['model'] = graph['21']['inputs']['model'] = ['16', 0]
    elif control == 'reference_video':
        if mode != 'identidades': raise ValueError('Vídeo de referência sem controle estrutural exige Ref2VA.')
        graph['17']['inputs']['ref_videos.ref_video_0'] = control_link
    if attention == 'sage_spectrum':
        from h3_workflow import ensure_h3_sage_attention
        graph = ensure_h3_sage_attention(graph)
    graph['17']['_meta'] = {'title': 'PERSONAGENS / DIREÇÃO — H3', 'pemara_combat': {
        'version': '1.0', 'preset': preset, 'control': control, 'seed': seed, 'steps': steps, 'frames':p['frames'],
        'attention_policy': attention, 'content_kind': 'live_action', 'face_refine': False,
        'turbo': False, 'physical_simulation_claim': False, 'owner_approval': 'PENDING'}}
    return graph


def frontend(graph, schemas, *, title='PEMARA COMBAT ENGINE'):
    """Serialize ordinary nodes using the live schema, without gallery subgraphs."""
    graph = deepcopy(graph)
    keys = list(graph)
    mapping = {key: i+1 for i, key in enumerate(keys)}
    links = []; ui_nodes = []; groups = {}
    def group(key, kind):
        if key in {'100', '101'} or kind == 'LoadImage': return 0
        if kind in {'CheckpointLoaderSimple', 'SDPoseKeypointExtractor', 'RTDETR_detect', 'SDPoseDrawKeypoints', 'PemaraCombatSelectFighterBoxes'} or key == '102': return 2
        if kind in {'ModelPatchLoader', 'MiniMaxH3FunControlNetApply'}: return 3
        if kind in {'SavePoseKpsAsJsonFile', 'PreviewAny'} or key in {'107','108'}: return 5
        if kind in {'SaveVideo', 'CreateVideo', 'PemaraDLSS5ContentPolicy'}: return 6
        if kind in {'MiniMaxH3ReferenceToVideo', 'MiniMaxH3ImageToVideo', 'RandomNoise'}: return 1
        return 4
    counters = {}
    for key, n in graph.items():
        kind = n['class_type']; schema = schemas[kind]
        index = group(key, kind); row = counters.get(index, 0); counters[index] = row + 1
        x, y = index * 440, 90 + row * 390
        groups.setdefault(index, []).append((x, y))
        inputs = []; values = []
        schema_inputs = {item['name']: item for item in schema.get('inputs', [])}
        for name, value in n['inputs'].items():
            item = schema_inputs.get(name) or {'type': 'IMAGE', 'is_link': True}
            linked = isinstance(value, list) and len(value) == 2 and str(value[0]) in mapping and isinstance(value[1], int)
            if linked:
                link_id = len(links) + 1
                port = len(inputs)
                inputs.append({'name': name, 'type': item['type'], 'link': link_id})
                links.append([link_id, mapping[str(value[0])], value[1], mapping[key], port, item['type']])
        # Widget ordering follows the actual node schema, not dictionary order.
        for name, item in schema_inputs.items():
            if item.get('is_link') or name not in n['inputs']: continue
            value = n['inputs'][name]
            inputs.append({'name': name, 'type': item['type'], 'widget': {'name': name}, 'link': None})
            values.append(value)
            for child, child_value in n['inputs'].items():
                if child.startswith(name + '.') and not isinstance(child_value, (list, dict)):
                    values.append(child_value)
            if name in {'noise_seed', 'seed'}: values.append('fixed')
        if kind == 'SaveVideo' and 'codec' not in n['inputs']:
            values.append('auto')  # Native compatibility widget, after format.codec.
        outputs = [{'name': o['name'], 'type': o['type'], 'links': []} for o in schema.get('outputs', [])]
        title_text = n.get('_meta', {}).get('title') or schema.get('display_name', kind)
        ui_nodes.append({'id': mapping[key], 'type': kind, 'pos': [x, y], 'size': [360, 340],
            'flags': {}, 'order': mapping[key]-1, 'mode': 0, 'inputs': inputs, 'outputs': outputs,
            'properties': {'Node name for S&R': kind}, 'widgets_values': values,
            'widgets_values_named': {name: value for name, value in n['inputs'].items()
                                    if not isinstance(value, (list, dict))}, 'title': title_text})
    by_id = {n['id']: n for n in ui_nodes}
    for link in links: by_id[link[1]]['outputs'][link[2]]['links'].append(link[0])
    names = ['1 ENTRADAS — REFERÊNCIAS E VÍDEO', '2 PERSONAGENS — IDENTIDADE / PROMPT / SEED',
        '3 PREPARAÇÃO — VÍDEO E POSE', '4 COMBAT CONTROL — CONTROLE ESTRUTURAL',
        '5 H3 CINEMATIC — GERAÇÃO', '6 QUALIDADE — PRÉVIA E DIAGNÓSTICO', '7 EXPORTAÇÃO — MP4 E RELATÓRIOS']
    colors = ['#426d91','#695085','#417c63','#965845','#425ca0','#86722f','#3c7d82']
    ui_groups = [{'title': names[i], 'bounding': [i*440-20, 30, 410, max(y for _,y in positions)+360],
        'color': colors[i], 'font_size': 20, 'flags': {}} for i, positions in groups.items()]
    return {'id': 'pemara-combat-engine-v1', 'revision': 1, 'last_node_id': len(ui_nodes),
        'last_link_id': len(links), 'nodes': ui_nodes, 'links': links, 'groups': ui_groups,
        'config': {}, 'extra': {'ds': {'scale': 0.55, 'offset': [40,40]}, 'pemara_title': title}, 'version': 0.4}


def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
