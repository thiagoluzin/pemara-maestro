"""Prepare owner-review assets and a bounded Face Refine diagnostic, no submission."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
IMAGES=Path('C:/Users/admin_remoto/.codex/generated_images/01a103ba-e6c9-7532-b729-144d39cfe760')
INPUT=ROOT/'ferramentas/ComfyUI/input'
sys.path.insert(0,str(ROOT/'services/studio'))
from h3_prompt_writing import compile_base_prompt

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

anchors=[]
for role,source in [('start','exec-a7e8f1c8-45ad-46be-adcf-d76460cab28b.png'),('end','exec-3cb6d606-0ad5-4dbc-8ea7-6dec9f596c1a.png')]:
    dest=PROJECT/'anchors'/f'{role}_candidate_v1.png'
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(IMAGES/source,dest)
    input_name=f're2_leon_licker_{role}_candidate_v1.png'
    shutil.copy2(dest,INPUT/input_name)
    anchors.append({'role':role,'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                    'comfyInput':input_name,'ownerApproved':False,'approvalEvidence':None})

description=('A single uninterrupted cinematic live-action shot based on Leon A first Licker discovery in Resident Evil 2 (1998). '
    'The same youthful adult male officer Leon Kennedy from the first and last reference images keeps exactly the same face, '
    'chestnut curtain-parted hair, cobalt blue short-sleeved RPD uniform, padded vest, blue elbow protectors and black fingerless gloves. '
    'The narrow first-floor west corridor keeps its gray-green plaster, dark teal lower walls, wood-framed windows and failing fluorescent tubes. '
    '0-9 seconds: camera slowly tracks backwards ahead of Leon as he takes cautious quiet steps, pistol down, gaze searching; '
    '9-16 seconds: he slows and stops on hearing a wet scratching sound above, notices a falling saliva drop, brow tightens, '
    'eyes and chin gradually lift; 16-24 seconds: camera gently tilts upward and widens, revealing an eyeless skinless red muscular '
    'Licker gripping the ceiling with four limbs, exposed brain, ivory sickle claws, long wet tongue; '
    '24-30.67 seconds: Leon raises the same handgun in a controlled two-handed stance, recoils one half-step, '
    'takes a sharp breath and watches the creature while its tongue sways and its claws shift against plaster. '
    'The endpoint matches the last reference frame. Anatomically credible separated human and quadruped, grounded weight, '
    'tactile costume and moist organic material, subtle film grain, readable facial detail, practical low-key lighting. '
    'The encounter remains unresolved; his pistol never fires. The camera motion continues gently without an editorial cut.')
sound=('Native synchronized stereo sound: measured boot steps with corridor reverberation, soft uniform movement, '
       'failing fluorescent hum, faint rain beyond windows, wet claw scraping from ceiling, isolated saliva drip, '
       'Leon breathing and a brief startled inhale, Licker throat rasp and moist tongue movement. '
       'Sparse silence between noises creates tension. No narration or spoken dialogue.')
prompt=compile_base_prompt(description,mode='FL2VA',duration_seconds=736/24,overall_soundscape=sound,non_diegetic_music='N/A')
(PROJECT/'prompt_h3.txt').write_text(prompt.prompt,encoding='utf-8')
save(PROJECT/'production_request.json',{
    'title':'RE2 1998 — Leon encontra o primeiro Licker', 'status':'PENDING_OWNER_ANCHOR_REVIEW',
    'engine':'minimax_h3','durationRequested':30,'singleContinuousTake':True,'nativeAudio':True,
    'profile':'h3_master','width':1344,'height':768,'steps':20,'fps':24,'frames':736,
    'nativeDuration':736/24,'deliveryFrames':720,'deliveryTrimTailFrames':16,
    'originalPreserved':True,'faceRefine':{'enabled':True,'steps':12,'denoise':.45,'canvas':512},
    'identityContinuityRequired':True,'anchors':anchors,'artisticApproval':'PENDING',
    'research':{'version':'Resident Evil 2 1998 PS1 Leon A first west-corridor encounter',
        'sources':['https://residentevil.fandom.com/wiki/Licker_Scene_(Leon)',
                   'https://www.youtube.com/watch?v=O68_yYCDDK0'],
        'primaryEvidence':'Original-game image at right in comparison thumbnail; corridor reviewed. Thumbnail shows Claire, not Leon.',
        'limitations':'Full original FMV not yet reviewed. Costume and creature are candidate adaptations requiring owner confirmation.'},
    'promptCompiler':prompt.contract_version})

save(Path(__file__).resolve().parent/'face_diagnostic.api.json',{
    '1':{'class_type':'LoadImage','inputs':{'image':anchors[0]['comfyInput']}},
    '2':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
    '3':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_int8_convrot.safetensors'}},
    '4':{'class_type':'ImageScale','inputs':{'image':['1',0],'upscale_method':'lanczos','width':1088,'height':608,'crop':'center'}},
    '5':{'class_type':'RepeatImageBatch','inputs':{'image':['4',0],'amount':5}},
    '6':{'class_type':'PemaraH3FaceRefine','inputs':{'images':['5',0],'clip':['2',0],'vae':['3',0],
        'source_prompt':'technical adapter diagnostic only','fps':24.,'seed':329847,
        'filename_prefix':'PEMARA_FACE_DIAGNOSTIC/face_5frames','enabled':True,'steps':12,'denoise':.45,
        'canvas_size':512,'detector':'human','confidence':.5}},
    '7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'PEMARA_FACE_DIAGNOSTIC/refined'}}})
print(json.dumps({'project':str(PROJECT),'anchors':anchors,'productionSubmitted':False},ensure_ascii=False))
