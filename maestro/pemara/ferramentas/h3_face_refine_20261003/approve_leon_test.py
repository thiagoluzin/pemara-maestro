"""Record the owner's actual chat approval and verify immutable identity bindings."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import shutil

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
sys.path.insert(0,str(ROOT/'services/studio'))
from identity_continuity import digest, compile_identity_continuity

now=datetime.now(timezone.utc).isoformat()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

request_path=PROJECT/'production_request.json'
request=json.loads(request_path.read_text(encoding='utf-8'))
approval={'actor':'owner','literal':'Aprovado','scope':'Two displayed start/end anchors and proposed 30-second Leon/Licker encounter',
          'recordedAt':now,'source':'direct user message in this Codex task','videoApproved':False}
for anchor in request['anchors']:
    if digest(anchor['path'])!=anchor['sha256']:
        raise ValueError('Approved anchor changed: '+anchor['role'])
    if digest(ROOT/'ferramentas/ComfyUI/input'/anchor['comfyInput'])!=anchor['sha256']:
        raise ValueError('Comfy input differs from approved pixels')
    anchor.update(ownerApproved=True,approvalEvidence=approval)
save(PROJECT/'approval_anchors.json',{'approval':approval,'anchors':request['anchors']})

source={'id':'scene1998','url':'https://residentevil.fandom.com/wiki/Licker_Scene_(Leon)',
        'title':'Licker Scene (Leon) — original Resident Evil 2 transcript', 'kind':'secondary',
        'accessedAt':'2026-10-03','versionScope':'1998 original, Leon A, police station west wing',
        'reviewedEvidence':'Retrieved search-page text identifies first encounter and Leon reaction Oh, boy. Full FMV unavailable.'}
original={'id':'original_corridor','url':'https://www.youtube.com/watch?v=O68_yYCDDK0','kind':'primary',
          'title':'Original-game corridor in comparison thumbnail', 'accessedAt':'2026-10-03',
          'versionScope':'Original RE2 corridor only; thumbnail character is Claire',
          'reviewedEvidence':'Original-game right-hand panel examined: gray-green corridor, teal lower walls. Not evidence of Leon costume.'}
visual={'id':'owner_visual','url':str(PROJECT/'approval_anchors.json'),'kind':'owner_approved_adaptation',
        'title':'Owner-approved live-action anchor designs', 'accessedAt':now,
        'versionScope':'Only this 30-second cinematic adaptation',
        'reviewedEvidence':'Exact two images displayed and approved by the owner in chat.'}

def research(facts):
    return {'status':'REVIEWED','version':'Resident Evil 2 1998 Leon A first Licker encounter; approved live-action adaptation',
            'reviewer':'Codex — limited retrieved scene text, corridor pixels and owner-approved anchors',
            'sources':[source,original,visual],'facts':facts,'blockingUnknowns':[],
            'limitations':['Full original FMV not reviewed. Precise wardrobe materials and creature dimensions are not claimed as canon.',
                           'No additional fighting abilities are depicted; only discovery, raising a handgun and creature posture.'],
            'adaptations':[{'change':'Photorealistic actor/creature materials and a continuous 30-second suspense shot, without new combat outcome',
                            'ownerDirection':'Original user request for cinematic realistic high quality; Aprovado on the two exact anchors.'}]}
def fact(text,ids):return {'summary':text,'sourceIds':ids}
def reference(role):
    a=next(x for x in request['anchors'] if x['role']==role)
    return {'path':a['path'],'sha256':a['sha256'],'role':'canonical','ownerApproved':True,
            'approvalEvidence':approval,'approvalScope':'this take and its identity comparison only'}

leon={'id':'leon','origin':'existing','invariants':[
    'Same adult male actor and youthful clean-shaven face as approved start/end images; chestnut parted hair.',
    'Same blue short-sleeved RPD uniform, vest, elbow protectors, gloves, utility belt and handgun.',
    'Human anatomy and proportions; restrained anxious breathing, then controlled two-handed aim; never fires.'],
    'references':[reference('start'),reference('end')],'missingViews':['full back','complete profile'],
    'research':research({
        'appearance':fact('Leon is the protagonist of the original encounter. Exact live-action face/proportions are the approved adaptation.', ['scene1998','owner_visual']),
        'wardrobeMaterials':fact('Blue RPD costume follows the approved images; weave, padding and sweat are cinematic material interpretations.', ['owner_visual']),
        'combatMechanics':fact('This take only depicts recognition and raising the handgun shown in the approved endpoint. No shots, hits or victory.', ['owner_visual']),
        'powersAndLimits':fact('No supernatural ability is depicted. Human reaction, posture and firearm handling are the approved scene action.', ['owner_visual']),
        'personalityAndMovement':fact('The original encounter is a startled discovery. Slow approach, upward look and brief recoil adapt that reaction.', ['scene1998','owner_visual'])})}
licker={'id':'licker','origin':'existing','invariants':[
    'Same ceiling creature as approved end image: exposed brain, eyeless face, red skinless muscle, ivory claws and long wet tongue.',
    'Keep quadrupedal body, limb proportions and ceiling grip. No human-face transformation, added armor, horns or extra limbs.',
    'Creature remains separate from Leon, shifts claws and tongue; unresolved encounter without invented injury or death.'],
    'references':[reference('end')],'missingViews':['full dorsal view','complete limb anatomy outside approved framing'],
    'research':research({
        'appearance':fact('Licker is the original creature encountered in the west wing. Exact practical-creature design is fixed by the approved endpoint.', ['scene1998','owner_visual']),
        'wardrobeMaterials':fact('No wardrobe. Wet muscle, brain, claws and saliva are the physical material adaptation approved in the endpoint.', ['owner_visual']),
        'combatMechanics':fact('Only ceiling grip, tongue movement and discovery are depicted. No fighting technique, attack impact or outcome is asserted.', ['owner_visual']),
        'powersAndLimits':fact('No additional powers or numerical physical dimensions are invented. Movement is constrained to the approved ceiling posture.', ['owner_visual']),
        'personalityAndMovement':fact('Threatening reveal follows the first Licker encounter; suspense posture and small organic movements are cinematic adaptation.', ['scene1998','owner_visual'])})}
bible={'schemaVersion':'pemara-character-bible@1','status':'OWNER_APPROVED_VISUAL_SCOPE','characters':[leon,licker]}
save(PROJECT/'character_bible.json',bible)
states={cid:{'entry':{'dirt':1,'wetness':wet,'damage':[]},'exit':{'dirt':1,'wetness':wet,'damage':[]},
             'physicalChangeReason':''} for cid,wet in [('leon',1),('licker',3)]}
contract={'bible':{'path':str(PROJECT/'character_bible.json'),'sha256':digest(PROJECT/'character_bible.json')},
          'firstTake':True,'states':states,
          'anchorReview':{'status':'PASS','reviewer':'owner; visual binding verified by Codex',
                         'notes':'Both displayed anchors and proposed discovery/standoff approved: Aprovado.',
                         'bibleSha256':digest(PROJECT/'character_bible.json'),
                         'artifacts':[{k:a[k] for k in ('path','sha256')} for a in request['anchors']]}}
identity=compile_identity_continuity(contract,ROOT,['leon','licker'],request['anchors'])
save(PROJECT/'qc/identity_preflight.json',identity)
request.update(status='OWNER_APPROVED_READY_FOR_SUBMISSION',identityContinuity=contract,anchorApproval=approval)
save(request_path,request)
path=PROJECT/'workflows/T01_master_30s_native_audio_face_refine.api.json'
graph=json.loads(path.read_text(encoding='utf-8'))
for node in graph.values():
    if node.get('class_type')=='PemaraH3FaceRefine':
        node['inputs']['detector']='human' # Actor face; creature anatomy stays source-bound.
save(path,graph)
print(json.dumps({'approvalRecorded':True,'identity':identity['status'],'workflow':str(path),'submitted':False}))
