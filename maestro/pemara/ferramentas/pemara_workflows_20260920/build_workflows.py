"""Install reviewable workflows; never submit a generation."""
import copy
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'workflows'
OUT.mkdir(exist_ok=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, graph):
    (OUT / name).write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')


for source, name in [
    ('image_hidream_o1', '01_HiDream_Full_ancoras'),
    ('image_qwen_Image_2512', '04_Qwen_2512_texto_layout'),
    ('image_flux2_klein_text_to_image', '05_FLUX_Klein_rascunho'),
    ('audio_yue2_text2music', '10_YuE2_composicao_ABC'),
    ('audio_yue2_music_cover', '11_YuE2_cover_SheetSage'),
]:
    graph = read(ROOT / 'upstream' / (source + '.json'))
    if source == 'image_flux2_klein_text_to_image':
        # Choose the upstream distilled branch using ordinary top-level bypass.
        for node in graph['nodes']:
            if node['id'] in (75, 9):
                node['mode'] = 4
            elif node['id'] in (77, 78):
                node['mode'] = 0
            if node['type'] == 'SaveImage':
                node['widgets_values'] = ['PEMARA/IMAGE/klein_draft']
    if source == 'image_hidream_o1':
        for node in graph['nodes']:
            if node['id'] == 112:
                node['widgets_values'][1] = 50
            elif node['id'] == 213:
                node['widgets_values'][0] = 'llada_image_edit_source.png'
            elif node['id'] == 227:
                node['widgets_values'] = ['PEMARA/IMAGE/master_anchor_candidate']
    write(name + '.json', graph)

# Add only top-level nodes. Upstream subgraphs remain untouched.
graph = read(ROOT / 'upstream/image_hidream_o1.json')
example = read(ROOT / 'sources/ComfyUI-Photoshoot/example_workflows/photoshoot-anchor-set.json')
shoot = copy.deepcopy(next(n for n in example['nodes'] if n['type'] == 'Krea2Photoshooting'))
shoot.update(id=240, title='PEMARA — lote de 8, revisar antes do próximo', pos=[-2300, 3500], inputs=[])
state = json.loads(shoot['properties']['shootingState'])
state['anzahl'] = 8
state['aktiv']['rausch'] = False
state['aktiv']['format'] = False
shoot['properties']['shootingState'] = json.dumps(state)
for output in shoot['outputs']:
    output['links'] = []
prompt = next(n for n in graph['nodes'] if n['id'] == 171)
old_outputs = copy.deepcopy(prompt['outputs'])
join = copy.deepcopy(next(n for n in example['nodes'] if n['type'] == 'Krea2PromptJoin'))
join.update(id=171, title='PEMARA — identidade fixa + direção', pos=prompt['pos'],
            outputs=old_outputs, inputs=[])
description = copy.deepcopy(prompt)
description.update(id=241, title='Descrição canônica aprovada', pos=[-2750, 3500])
description['widgets_values'] = ['Preserve the exact identity, proportions, clothing and materials of the approved reference. {kamera}, {pose}, {ausdruck}.']
description['outputs'][0]['links'] = []
graph['nodes'] = [join if n['id'] == 171 else n for n in graph['nodes']]
graph['nodes'] += [shoot, description]
link_id = max(link[0] for link in graph['links'])
for origin, slot, name in [(description, 0, 'text'), (shoot, 2, 'kamera'), (shoot, 0, 'pose'), (shoot, 1, 'ausdruck')]:
    link_id += 1
    join['inputs'].append({'name': name, 'type': 'STRING', 'link': link_id})
    origin['outputs'][slot]['links'].append(link_id)
    graph['links'].append([link_id, origin['id'], slot, 171, len(join['inputs']) - 1, 'STRING'])
# Series noise is fixed, but cannot serve as proof of identity.
sampler = next(n for n in graph['nodes'] if n['type'] == 'SamplerCustom')
sampler['widgets_values'][1:3] = [776610, 'fixed']
next(n for n in graph['nodes'] if n['id'] == 154)['widgets_values'] = [True]
next(n for n in graph['nodes'] if n['id'] == 227)['widgets_values'] = ['PEMARA/IMAGE/photoshoot_candidate']
graph['last_node_id'] = 241
graph['last_link_id'] = link_id
next(n for n in graph['nodes'] if n['id'] == 112)['widgets_values'][1] = 50
next(n for n in graph['nodes'] if n['id'] == 213)['widgets_values'][0] = 'llada_image_edit_source.png'
write('02_HiDream_Photoshoot_lote8.json', graph)

for variant in ('base', 'turbo'):
    graph = read(ROOT / f'sources/Comfyui-LLaDa-Image-T8/example_workflows/{variant}_editing.json')
    for node in graph['nodes']:
        if node['type'] == 'SaveImage':
            node['widgets_values'] = [f'PEMARA/IMAGE/llada_{variant}_candidate']
    write(f'03_LLaDA_{variant}_correcao.json', graph)

for variant in ('Base', 'Flash'):
    graph = {
        '1': {'class_type': 'PemaraAuK', 'inputs': {
            'variant': variant, 'instruction': 'Generate speech saying: Este é um teste de voz do PEMARA.',
            'seconds': 3.0, 'seed': 42}},
        '2': {'class_type': 'SaveAudio', 'inputs': {
            'audio': ['1', 0], 'filename_prefix': f'PEMARA/AUDIO/auk_{variant.lower()}_candidate'}},
    }
    write(f'12_AuK_{variant}_voz.api.json', graph)
    graph['3'] = {'class_type': 'LoadAudio', 'inputs': {'audio': 'PEMARA_EXEMPLO_SUBSTITUIR.wav'}}
    graph['1']['inputs']['audio'] = ['3', 0]
    graph['1']['inputs']['instruction'] = 'Preserve the voice and words. Speak slightly more slowly and clearly.'
    write(f'13_AuK_{variant}_editar.api.json', graph)

# Small editable UI equivalents of the four API graphs.
for source in list(OUT.glob('*AuK*.api.json')):
    api = read(source)
    params = api['1']['inputs']
    editing = '3' in api
    nodes = [
        {'id': 1, 'type': 'PemaraAuK', 'pos': [360, 120], 'size': [450, 320],
         'flags': {}, 'order': 1, 'mode': 0, 'properties': {'Node name for S&R': 'PemaraAuK'},
         'inputs': [{'name': 'audio', 'type': 'AUDIO', 'link': 2 if editing else None}],
         'outputs': [{'name': 'AUDIO', 'type': 'AUDIO', 'links': [1], 'slot_index': 0}],
         'widgets_values': [params['variant'], params['instruction'], params['seconds'], params['seed']]},
        {'id': 2, 'type': 'SaveAudio', 'pos': [870, 120], 'size': [350, 160],
         'flags': {}, 'order': 2, 'mode': 0, 'properties': {'Node name for S&R': 'SaveAudio'},
         'inputs': [{'name': 'audio', 'type': 'AUDIO', 'link': 1}], 'outputs': [],
         'widgets_values': [api['2']['inputs']['filename_prefix']]},
    ]
    links = [[1, 1, 0, 2, 0, 'AUDIO']]
    if editing:
        nodes.append({'id': 3, 'type': 'LoadAudio', 'pos': [0, 120], 'size': [300, 180],
                      'flags': {}, 'order': 0, 'mode': 0, 'properties': {'Node name for S&R': 'LoadAudio'},
                      'inputs': [], 'outputs': [{'name': 'AUDIO', 'type': 'AUDIO', 'links': [2]}],
                      'widgets_values': [api['3']['inputs']['audio'], None, None]})
        links.append([2, 3, 0, 1, 0, 'AUDIO'])
    write(source.name.replace('.api.json', '.json'), {
        'version': 0.4, 'last_node_id': 3 if editing else 2, 'last_link_id': len(links),
        'nodes': nodes, 'links': links, 'groups': [], 'config': {}, 'extra': {}})

# Explicit score-review stages built as ordinary flat graphs. Keep the upstream
# subgraph definitions intact and retain its native sampler defaults.
yue = read(ROOT / 'upstream/audio_yue2_text2music.json')
native = {n['id']: n for n in yue['definitions']['subgraphs'][0]['nodes']}
style = 'Warm vocal, acoustic pop, piano, 90 BPM.'
lyrics = '[Verse]\nMorning light is on the way\nWe begin another day'

def flat_yue(ids):
    nodes = [copy.deepcopy(native[i]) for i in ids]
    for node in nodes:
        node['mode'] = 0
        for port in node.get('inputs', []):
            port['link'] = None
        for port in node.get('outputs', []):
            port['links'] = []
    return {'version': 0.4, 'nodes': nodes, 'links': [], 'groups': [],
            'config': {}, 'extra': {}, 'last_node_id': max(ids), 'last_link_id': 0}

def wire(graph, origin_id, origin_slot, target_id, field):
    source = next(n for n in graph['nodes'] if n['id'] == origin_id)
    target = next(n for n in graph['nodes'] if n['id'] == target_id)
    slot = next(i for i, p in enumerate(target['inputs']) if p['name'] == field)
    number = len(graph['links']) + 1
    source['outputs'][origin_slot]['links'].append(number)
    target['inputs'][slot]['link'] = number
    graph['links'].append([number, origin_id, origin_slot, target_id, slot,
                           source['outputs'][origin_slot]['type']])
    graph['last_link_id'] = number

plan = flat_yue([15, 24, 14])
abc = next(n for n in plan['nodes'] if n['id'] == 24)
abc['widgets_values'][:4] = [style, lyrics, 42, 'fixed']
wire(plan, 15, 1, 24, 'clip')
wire(plan, 24, 0, 14, 'source')
write('10a_YuE2_planejar_ABC_sem_audio.json', plan)

render = flat_yue([15, 25, 18, 8, 5, 9])
music = next(n for n in render['nodes'] if n['id'] == 25)
music['title'] = 'Cole o ABC revisado antes de gerar'
music['widgets_values'][:7] = [style, lyrics, '', 42, 'fixed', 'full', 30]
save = copy.deepcopy(next(n for n in yue['nodes'] if n['id'] == 10))
save['widgets_values'][0] = 'PEMARA/AUDIO/yue2_reviewed_score_candidate'
render['nodes'].append(save)
for source, out, target, field in [
    (15, 1, 25, 'clip'), (15, 0, 8, 'model'), (15, 2, 9, 'vae'),
    (25, 0, 18, 'conditioning'), (25, 0, 8, 'positive'),
    (18, 0, 8, 'negative'), (25, 1, 5, 'seconds'),
    (5, 0, 8, 'latent_image'), (8, 0, 9, 'samples'), (9, 0, 10, 'audio'),
]:
    wire(render, source, out, target, field)
write('10b_YuE2_gerar_com_ABC_revisado.json', render)

print(f'{len(list(OUT.glob("*.json")))} workflows preparados em {OUT}')
