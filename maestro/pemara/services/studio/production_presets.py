"""Production presets inside the existing Maestro project/approval architecture.

No downloads, generation, artistic approval or service restarts on import.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

PRESET='SAIYAN_SHOWDOWN'
VERSION='saiyan_showdown_20261107_v1'
CAST=('goku','vegeta')
IDENTITY=('Two distinct adult human actors as Goku and Vegeta in the original Saiyan arc. '
    'Goku is taller, with black irregular spiked hair, orange cotton gi, navy undershirt, blue sash, wristbands and boots. '
    'Vegeta is shorter and compact, with a pronounced widow peak, tall black hair, navy undersuit, ivory Saiyan armor '
    'with ochre panels AND shoulder guards, white gloves and boots, brown tail wrapped around his waist. '
    'Preserve the exact approved new faces, anatomy, materials and height relationship. No later-saga designs or Super Saiyan.')
STAGE=('One continuous arid canyon geography in daylight: needle towers west, split cliff east, flat dusty combat lane between them. '
    'Natural skin pores, sweat and restrained highlights, matte woven cloth, scuffed rigid armor. '
    'Keep the action line legible and all contact physically visible. '
    'No dialogue, human vocalizations, narration, captions, subtitles or superimposed writing. '
    'Audio will be created and synchronized separately; do not generate music or speech.')
TAKES=[
 ('T01','A superioridade de Vegeta',[
  (0,2,'WIDE_SIDE','Vegeta advances from the east; Goku retreats west in guard. Show grounded steps and the approach lane.'),
  (2,3.5,'TRACK_SIDE','Vegeta plants his rear foot, drives his hip and lands ONE straight punch on Goku\'s torso. Goku folds and displaces away only after visible contact; Vegeta retracts and recovers.'),
  (3.5,5,'TRACK_SIDE','Continuing the established geography, Vegeta lands a second distinct punch to Goku\'s face. Show approach, contact and the head/body response; do not hide contact with a cut.'),
  (5,7,'LOW_SIDE','Goku braces to block; Vegeta breaks the guard with one grounded body attack. Show the support legs and torso responding as a unit.'),
  (7,10,'WIDE_SIDE','Goku skids west across the visible ground, boots carving dust and displacing small stones; friction decelerates him. Vegeta holds his recovered base in the east.')]),
 ('T02','A surra continua; nasce o Kaioken',[
  (0,3,'OTS_VEGETA','Vegeta closes the same gap toward Goku; the over-shoulder camera follows his approach without reversing the axis.'),
  (3,5,'TRACK_SIDE','Vegeta lands one heavy body strike. Goku reacts after contact and drops onto one knee, visibly absorbing his weight.'),
  (5,7,'CLOSE_GOKU','Goku looks toward Vegeta, steadies his breathing silently, and changes from pain to determined resistance. Preserve the new actor\'s face and accumulated injuries.'),
  (7,10,'LOW_SIDE','Goku activates red Kaioken around his entire body. Heat shimmer displaces the air, dust presses outward and small stones tremble and begin lifting. The red illumination has a physical source; no blond transformation.')]),
 ('T03','Goku inverte o combate',[
  (0,2,'TRACK_SIDE','Goku pushes off the ground and accelerates east toward Vegeta with a short causal dust wake; no teleport.'),
  (2,4,'TRACK_SIDE','Goku drives one fist into Vegeta\'s abdomen. Armor compresses or tilts coherently with the torso; Vegeta reacts after visible contact.'),
  (4,6,'TRACK_SIDE','Vegeta counterattacks once. Goku reads the attack, steps and slips outside its path, then counters through his planted legs and rotating torso.'),
  (6,8,'WIDE_SIDE','Goku\'s next visible strike drives Vegeta laterally along its vector. Keep both whole bodies and the initial support failure readable.'),
  (8,10,'WIDE_SIDE','Goku remains surrounded by red Kaioken while Vegeta attempts to rebuild his stance. Preserve dust, injuries and armor damage.')]),
 ('T04','Vegeta não consegue defender',[
  (0,3,'TRACK_SIDE','Vegeta actively guards against Goku rather than becoming a passive target. He pivots and redirects one incoming strike.'),
  (3,5,'TRACK_SIDE','Goku feints to open Vegeta\'s guard and lands one decisive blow through the opening. Make the feint and actual contact separate readable causes.'),
  (5,7,'LOW_SIDE','Vegeta loses his base after the hit; he takes an involuntary recovery step in the force direction, with knees and hips absorbing the displacement.'),
  (7,10,'ORBIT_GOKU','A short controlled orbit reveals the existing canyon as Goku increases Kaioken. Intensify red atmospheric pressure, heat distortion and driven dust, with muscles straining; not a red color filter.')]),
 ('T05','Vegeta contra a montanha',[
  (0,3,'TRACK_SIDE','Goku compresses into a grounded launch, closes rapidly and lands one final heavy strike on Vegeta. Show the exact point of contact before launch.'),
  (3,5,'WIDE_SIDE','Vegeta is thrown east along the strike vector. His whole body follows a continuous trajectory; do not replace it with a flash or jump cut.'),
  (5,7,'TRACK_FLIGHT','Track alongside Vegeta toward the previously established eastern split cliff. Changing foreground occlusion conveys depth and speed while preserving identity.'),
  (7,9,'CLIFF_WIDE','Vegeta physically hits the eastern cliff. Show body-to-rock contact, then progressive fractures spreading from that point.'),
  (9,10,'CLIFF_WIDE','Large rock fragments detach under the causal fracture; dust begins expanding after contact. Keep part of the collision visible rather than masking it with a generic explosion.')]),
 ('T06','Fúria de Vegeta: Galick Gun',[
  (0,2,'CLIFF_WIDE','Vegeta emerges from the same fresh rubble, dusty and visibly injured, with the same armor damage and no miraculous cleaning.'),
  (2,4,'CLOSE_VEGETA','His disbelief tightens into fury as he fixes his gaze west toward Goku; no speech or vocalization.'),
  (4,6,'LOW_VEGETA','Vegeta adopts the researched Galick Gun charging stance with both palms preparing to project ki west; no Kamehameha hand pose substitution.'),
  (6,8,'LOW_VEGETA','A huge white-violet core grows between his hands, nested in deep violet turbulent plasma, unstable filaments and secondary arcs. Purple light progressively illuminates his body and nearby rock.'),
  (8,10,'CLIFF_WIDE','The colossal charge presses dust outward, fractures ground locally and lifts loose stones. Volumetric illumination and heat distortion reveal scale; he is ready to discharge, not a thin laser.')]),
 ('T07','Kaioken Kamehameha encontra Galick Gun',[
  (0,2,'GEOGRAPHY_WIDE','Show Goku west and Vegeta east across the damaged canyon. Establish the distance and their opposing firing axes before either beam travels.'),
  (2,4,'LOW_GOKU','Goku braces and draws both hands to his hip in the Kamehameha charging stance. A blue-white core grows while RED Kaioken remains around HIS BODY.'),
  (4,6,'CHARGE_COVERAGE','Use separately generated matching coverage of Vegeta\'s violet charge and Goku\'s blue-white charge. This is editorial coverage, not instructions for the generator to invent internal cuts.'),
  (6,8,'GEOGRAPHY_WIDE','Vegeta releases a massive turbulent violet energy front, several body-widths across in the established scale, traveling west toward Goku. White-violet core, plasma layers, arcs and pressure displace dust; not a narrow cylinder.'),
  (8,9,'LOW_GOKU','Goku discharges an equally colossal blue-white Kamehameha east. Red Kaioken stays around Goku; do not exchange attack colors or owners.'),
  (9,10,'COLLISION_WIDE','The blue-white and violet fronts reach one another. End on the FIRST visible frame of turbulent contact and incipient circular pressure displacement. No sustained beam struggle, victory, overpowering or defeated character.')]),
]

def _read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def _write(path,data):
    from video_projects import _atomic_json_write
    _atomic_json_write(Path(path),data)
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def describe():
    return [{'id':PRESET,'name':'Saiyan Showdown — Goku × Vegeta','durationSeconds':70,
        'takeCount':7,'contentKind':'live_action','engine':'minimax_h3','variant':'base',
        'generation':{'width':1344,'height':768,'frames':243,'fps':24,'steps':20},
        'delivery':{'width':1920,'height':1080,'fps':24},'automaticBatch':False,
        'profiles':['human_realism_auto','combat_full_v1'],'newAnchorsRequired':True}]

def prompt(action,camera):
    return f'{IDENTITY}\n{STAGE}\nCamera: {camera}.\nAction: {action}\nEvery strike: prepare, plant, drive through hips, accelerate, make visible contact, displace the defender, then recover. Do not react before the cause. No extra strikes.'

def create(root,*,name='',project_id='',preset=PRESET):
    if preset!=PRESET:raise ValueError('Preset de produção desconhecido.')
    from video_projects import create_project,project_view
    view=create_project(root,name=name or 'Saiyan Showdown — Goku × Vegeta',project_id=project_id,
        objective='Primeira batalha na Terra em sete takes de 10 segundos. Novos atores humanos, coreografia causal e corte no início da colisão Galick Gun/Kamehameha. Validar T01 antes do lote.',
        duration_seconds=70,content_kind='live_action',distribution_mode='standard')
    folder=Path(root)/view['projectId'];manifest=_read(folder/'project_manifest.json');queue=_read(folder/'take_queue.json')
    manifest.update(production_preset=PRESET,preset_version=VERSION,preview_resolution='1344x768',final_resolution='1920x1080',
        fps_preview=24,fps_final=24,identityContinuityRequired=True,automatic_batch_allowed=False,
        h3_scene_profile='combat_full_v1',h3_model_variant='base',engine_id='minimax_h3',
        new_anchors_required=True,reuse_historical_images=False,preset_stage='NEW_IDENTITY_AWAITING_OWNER',
        audio={'music_provider':None,'voice_provider':None,'dialogue':False,'human_vocalizations':False,
            'narration':False,'music_status':'AWAITING_USER_SOUNDTRACK','sound_effects':'LOCAL_LICENSED_PENDING_CONTACT_FRAME_LOCK'},
        finishing_policy={'content_kind':'live_action','fps':24,'fps_owner_directive':'07/11/2026: entrega 24 FPS',
            'resize':'Lanczos contain/pad','encoder':'h264_nvenc','dlss_video':False,'seedvr2':False,'face_refine':False})
    queue.update(project_id=folder.name,identityContinuityRequired=True,automatic_batch_allowed=False,
        anchor_generation_policy={'provider':'codex_builtin_imagegen','local_executor_forbidden':True,
            'required_generator':'Codex built-in imagegen','require_generator_provenance':True,
            'require_visual_cast_verification_for_video':True,'human_review_required':True,
            'pilot_first':True,'pilot_takes':['T01'],'remaining_batch_requires_pilot_human_approval':True},
        assembly={'preview':{'width':1344,'height':768,'fps':24,'format':'mp4'},
                  'final':{'width':1920,'height':1080,'fps':24,'format':'mp4'},'rule':'only approved source frames and reviewed joins'},takes=[])
    storyboard=[]
    for index,(tid,title,beats) in enumerate(TAKES):
        subplans=[{'id':f'{tid}_{n+1:02}', 'editorial_range_seconds':[a,b], 'camera_id':camera,
            'action':action,'prompt_en':prompt(action,camera),'generation_rule':'one dominant action per inference; select complete approved interval, never cut contact',
            'status':'PLANNED_NOT_RENDERED'} for n,(a,b,camera,action) in enumerate(beats)]
        record={'id':tid,'name':title,'status':'PLANNED','maestro_status':'PLANNED','content_kind':'live_action',
            'target_duration_seconds':10,'owner_approved':False,'assembly_eligible':False,
            'render_authorized':index==0,'base_image':{'status':'PENDING','file':''},
            'video_generation':{'profile':'minimax_h3_fl2va_int8_720p24','engine_id':'minimax_h3',
                'h3_model_variant':'base','h3_scene_profile':'combat_full_v1','h3_quality_profile':'h3_master',
                'width':1344,'height':768,'frames':243,'fps':24,'steps':20,'guidance':1.0,
                'start_end_frame_enabled':False,'include_native_audio':False,'fallback_allowed':False},
            'prompt':prompt(beats[0][3],beats[0][2]),'shot_contract':{'prompt':prompt(beats[0][3],beats[0][2]),
                'visible_characters':list(CAST),'subplans':subplans,'execute_as_single_monolithic_prompt':False},
            'subplans':subplans,'generation_gate':'NEW_ANCHOR_OWNER_APPROVAL_AND_SINGLE_CONTACT_PILOT' if index==0 else 'T01_OWNER_APPROVAL_AND_CONTINUITY',
            'video':{},'audio_direction':{'strategy':'local_postproduction_no_voices'},
            'continuity':{'damage':'accumulates; never reset','pose_source':'last approved moving interval',
                'identity_source':'new exact owner-approved stills, never historical images'}}
        queue['takes'].append(record);storyboard.append({'id':tid,'title':title,'timeline_seconds':[index*10,(index+1)*10],'subplans':subplans})
    _write(folder/'project_manifest.json',manifest);_write(folder/'take_queue.json',queue)
    _write(folder/'storyboard.json',{'version':VERSION,'total_seconds':70,'takes':storyboard,'owner_approval':'PENDING','end':'FIRST_ENERGY_CONTACT_NO_WINNER'})
    _write(folder/'character_bible.json',{'version':VERSION,'identityContinuityRequired':True,'status':'NEW_CAST_PENDING_OWNER',
        'characters':[{'id':'goku','origin':'existing','era':'Dragon Ball Z original anime, Saiyan arc','identity':IDENTITY,
            'powers':['red Kaioken','blue-white Kamehameha'],'forbidden':['Super Saiyan','Galick Gun']},
            {'id':'vegeta','origin':'existing','era':'Dragon Ball Z original anime, Saiyan arc','identity':IDENTITY,
            'powers':['violet Galick Gun'],'forbidden':['Kaioken','Kamehameha','later-saga shoulderless armor']}],
        'approved_references':[],'historical_reference_reuse_allowed':False,
        'research':{'status':'PRIMARY_SOURCES_READ_20261107','version':'Saiyan arc first Earth duel',
            'sources':[{'url':'https://en.dragon-ball-official.com/news/01_3929.html','title':'Vegeta from the Saiyan Arc','primary':True,'supports':['dominance','Kaioken reversal','Galick Gun stance']},
            {'url':'https://en.dragon-ball-official.com/news/01_313.html','title':'Dragon Ball Fashion Check Goku','primary':True,'supports':['orange uniform evolution','undershirt and boots']}],
            'adaptations':['new human casting','70-second compression','mountain collision and colossal VFX directed by owner','cut before winner']}})
    _write(folder/'audio/audio_plan.json',{'soundtrack':None,'automatic_download':False,'voices_allowed':False,
        'voice_separation':'optional local Demucs/UVR only after supplied original; human listening required',
        'cues':[{'take':tid,'contact_frame':None,'sfx_source':None,'source_license':None,'status':'AWAITING_PICTURE_LOCK'} for tid,_,_ in TAKES],
        'mix':'deterministic FFmpeg; sync to actual contact frames, never nominal prompt times'})
    return project_view(folder)

def validate_admission(folder,take,queue):
    manifest=_read(Path(folder)/'project_manifest.json')
    if manifest.get('production_preset')!=PRESET:return
    if take.get('id')!='T01':
        first=next((t for t in queue['takes'] if t.get('id')=='T01'),{})
        from video_projects import _take_status
        if _take_status(first) not in {'APPROVED','FINAL'}:
            raise ValueError('SAIYAN_SHOWDOWN: aprove o T01 exato antes dos outros takes; o lote não está liberado.')
    r17_return=manifest.get('production_route_id')=='r17_start_chain_owner_10s_v1'
    pilot_path=Path(folder)/('qc/r17_10s_pilot.json' if r17_return else 'qc/single_contact_pilot.json')
    pilot=_read(pilot_path) if pilot_path.exists() else {}
    if not pilot.get('owner_approved') or not pilot.get('artifact') or not pilot.get('sha256'):
        if r17_return:
            raise ValueError('SAIYAN_SHOWDOWN: aprovar o piloto R17 de 10 segundos exato antes de liberar novos takes; a revisão artística permanece pendente.')
        raise ValueError('SAIYAN_SHOWDOWN: validar primeiro um único soco com contato, reação e peso. O piloto e as novas âncoras ainda exigem revisão.')
    path=(Path(folder)/pilot['artifact']).resolve()
    if not path.is_relative_to(Path(folder).resolve()) or not path.is_file() or sha(path)!=pilot['sha256']:
        raise ValueError('SAIYAN_SHOWDOWN: o piloto aprovado não corresponde aos bytes disponíveis.')

def store_soundtrack(folder,stream,filename,*,rights_confirmed=False):
    folder=Path(folder).resolve()
    if not (folder/'project_manifest.json').is_file():raise FileNotFoundError(folder.name)
    if rights_confirmed is not True:raise ValueError('Confirme que pode usar a trilha fornecida.')
    suffix=Path(filename or '').suffix.lower()
    if suffix not in {'.wav','.flac','.mp3','.m4a','.aac','.ogg'}:raise ValueError('Formato de áudio não permitido.')
    audio=folder/'audio';audio.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=audio,suffix=suffix,prefix='upload_',delete=False) as target:
        temporary=Path(target.name);size=0
        try:
            while True:
                chunk=stream.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>200*1024*1024:raise ValueError('Trilha excede 200 MB.')
                target.write(chunk)
        except Exception:
            target.close();temporary.unlink(missing_ok=True);raise
    try:
        p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(temporary)],capture_output=True,check=True,timeout=30)
        info=json.loads(p.stdout)
        if not any(s.get('codec_type')=='audio' for s in info.get('streams',[])):raise ValueError('Arquivo sem faixa de áudio válida.')
        digest=sha(temporary);destination=audio/('soundtrack_original_'+digest[:16]+suffix)
        if destination.exists():temporary.unlink()
        else:temporary.replace(destination)
        record={'file':destination.name,'sha256':digest,'original_filename':Path(filename).name,'bytes':size,
            'rights_confirmed':True,'original_preserved':True,'voices':'UNKNOWN','listening':'PENDING_OWNER',
            'automatic_voice_removal':False,'automatic_mix':False,'probe':info}
        _write(audio/'soundtrack.json',record);return {k:record[k] for k in ('file','sha256','bytes','listening','voices')}
    except Exception:
        temporary.unlink(missing_ok=True);raise


def asset_records(folder):
    path=Path(folder)/'production_assets.json'
    return _read(path).get('assets',[]) if path.is_file() else []

def asset_path(folder,asset_id):
    folder=Path(folder).resolve()
    record=next((a for a in asset_records(folder) if a.get('id')==asset_id),None)
    if record is None:raise FileNotFoundError(asset_id)
    path=(folder/record['file']).resolve()
    if not path.is_relative_to(folder) or not path.is_file() or sha(path)!=record['sha256']:
        raise ValueError('A referência não corresponde ao arquivo registrado.')
    return path,record

def review_asset(folder,asset_id,*,decision,expected_sha256):
    from video_projects import _QUEUE_MUTATION_LOCK,utc_now
    with _QUEUE_MUTATION_LOCK:
        path,record=asset_path(folder,asset_id)
        if expected_sha256!=record['sha256']:raise ValueError('A imagem mudou; recarregue antes da revisão.')
        if decision not in {'APPROVED','REJECTED'}:raise ValueError('Decisão inválida.')
        if record.get('status')=='APPROVED' and decision=='REJECTED':
            raise ValueError('Esta referência já foi aprovada. Use a revisão de âncora do take para revogar seu uso.')
        records=asset_records(folder)
        target=next(a for a in records if a['id']==asset_id)
        target.update(status=decision,reviewed_at=utc_now(),review_scope='Exact still only; no video or first-frame mapping approved')
        _write(Path(folder)/'production_assets.json',{'version':VERSION,'assets':records})
        _write(Path(folder)/'receipts'/(asset_id+'_visual_review_'+decision.lower()+'.json'),
            {'owner_action':'Maestro explicit reference review','decision':decision,'artifact':str(path),
             'sha256':record['sha256'],'scope':target['review_scope'],'recorded_at':target['reviewed_at']})
        return {k:target[k] for k in ('id','status','sha256','review_scope')}
