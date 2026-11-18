"""Two-person 2D tracking and explicit, bounded motion heuristics. No physics verdict."""
from itertools import permutations
from pathlib import Path
import json
import math
import subprocess

import cv2
import numpy as np

BODY_EDGES = [(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),
              (1,11),(11,12),(12,13),(8,11),(0,1)]
COLORS = {'A': (255,160,40), 'B': (50,165,255)}
JOINTS = {'head': 0, 'neck': 1, 'right_shoulder': 2, 'right_elbow': 3, 'right_wrist': 4,
    'left_shoulder': 5, 'left_elbow': 6, 'left_wrist': 7, 'right_hip': 8,
    'right_knee': 9, 'right_ankle': 10, 'left_hip': 11, 'left_knee': 12, 'left_ankle': 13}


def pose(person):
    raw = person.get('pose_keypoints_2d', [])
    if len(raw) < 54 or len(raw) % 3: raise ValueError('OpenPose body18 inválido.')
    p = np.asarray(raw, dtype=float).reshape(-1, 3)[:18]
    if not np.isfinite(p).all(): raise ValueError('Coordenadas não finitas.')
    return p


def center(p):
    chosen = p[[1,2,5,8,11]]
    valid = chosen[:,2] >= 0.3
    if valid.sum() < 2:
        chosen = p; valid = chosen[:,2] >= 0.3
    return chosen[valid,:2].mean(axis=0) if valid.any() else None


def torso(p):
    top = p[1,:2] if p[1,2] >= .3 else (p[2,:2]+p[5,:2])/2
    hips = p[[8,11]]
    valid = hips[:,2] >= .3
    return float(np.linalg.norm(top-hips[valid,:2].mean(axis=0))) if valid.any() else 0.0


def appearance(image, p):
    if image is None: return None
    selected = p[[1,2,5,8,11]]
    selected = selected[selected[:,2] >= .3]
    if len(selected) < 2: return None
    x0,y0 = np.maximum(0, np.floor(selected[:,:2].min(axis=0))).astype(int)
    x1,y1 = np.ceil(selected[:,:2].max(axis=0)).astype(int)
    h,w = image.shape[:2]; x1=min(w,x1);y1=min(h,y1)
    if x1-x0 < 4 or y1-y0 < 4: return None
    crop = cv2.cvtColor(image[y0:y1,x0:x1],cv2.COLOR_BGR2HSV)
    hist=cv2.calcHist([crop],[0,1],None,[12,8],[0,180,0,256]);cv2.normalize(hist,hist)
    return hist


def track(frames, *, video=None, fps=24):
    if not isinstance(frames,list) or not frames: raise ValueError('Pose deve conter uma lista de frames.')
    cap=cv2.VideoCapture(str(video)) if video else None
    tracks={}; rows=[]; flags=[]; initialized=False
    for i, frame in enumerate(frames):
        width=int(frame['canvas_width']);height=int(frame['canvas_height'])
        image=None
        if cap is not None:
            ok,image=cap.read()
            if ok and image.shape[:2] != (height,width): image=cv2.resize(image,(width,height))
            if not ok:image=None
        candidates=[]
        for number,person in enumerate(frame.get('people',[])):
            p=pose(person);c=center(p)
            if c is not None:
                candidates.append({'pose':p,'center':c,'hist':appearance(image,p),'source_detection_index':number})
        # Bound assignment complexity. Additional people are reported rather than silently tracked as fighters.
        if len(candidates)>4:
            flags.append({'frame':i,'kind':'EXTRA_PEOPLE','count':len(candidates)})
            candidates=sorted(candidates,key=lambda c:float((c['pose'][:,2]>=.3).sum()),reverse=True)[:4]
        assigned={};ambiguous=False
        if not initialized and len(candidates)>=2:
            pair=sorted(sorted(candidates,key=lambda c:torso(c['pose']),reverse=True)[:2],key=lambda c:c['center'][0])
            assigned={'A':pair[0],'B':pair[1]};initialized=True
        elif initialized and candidates:
            actors=['A','B']
            def cost(actor,c):
                state=tracks.get(actor)
                if state is None:return 1.0
                prediction=state['center']+state['velocity']*min(i-state['frame'],6)
                scale=max(30,state['torso'])
                spatial=float(np.linalg.norm(c['center']-prediction))/scale
                common=(state['pose'][:,2]>=.3)&(c['pose'][:,2]>=.3)
                shape=0.0
                if common.sum()>=4:
                    a=(state['pose'][common,:2]-state['center'])/max(20,state['torso'])
                    b=(c['pose'][common,:2]-c['center'])/max(30,torso(c['pose']) or scale)
                    shape=float(np.linalg.norm(a-b,axis=1).mean())*.2
                color=0.0
                if state['hist'] is not None and c['hist'] is not None:
                    color=.6*float(cv2.compareHist(state['hist'],c['hist'],cv2.HISTCMP_BHATTACHARYYA))
                return spatial+shape+color
            choices=[]
            if len(candidates)>=2:
                for a,b in permutations(range(len(candidates)),2):
                    choices.append((cost('A',candidates[a])+cost('B',candidates[b]),a,b))
                choices.sort()
                best=choices[0]
                ambiguous=len(choices)>1 and choices[1][0]-best[0]<.15
                for actor,n in zip(actors,best[1:]):
                    if cost(actor,candidates[n])<2.5:assigned[actor]=candidates[n]
            else:
                actor=min(actors,key=lambda a:cost(a,candidates[0]))
                if cost(actor,candidates[0])<2.5:assigned[actor]=candidates[0]
        if ambiguous:flags.append({'frame':i,'kind':'TRACK_ASSIGNMENT_AMBIGUOUS','identity_confirmed':False})
        for actor in ('A','B'):
            if actor not in assigned: flags.append({'frame':i,'actor':actor,'kind':'FIGHTER_POSE_MISSING'})
        row={'frame':i,'seconds':i/fps,'width':width,'height':height,'actors':{},'assignment_ambiguous':ambiguous}
        for actor,c in assigned.items():
            old=tracks.get(actor)
            velocity=(c['center']-old['center'])/max(1,i-old['frame']) if old else np.zeros(2)
            if old:velocity=.65*velocity+.35*old['velocity']
            length=torso(c['pose']) or (old['torso'] if old else 50.0)
            limit=max(15,length*.25);velocity=np.clip(velocity,-limit,limit)
            tracks[actor]={'frame':i,**c,'velocity':velocity,'torso':length}
            row['actors'][actor]={'body18':c['pose'].round(4).tolist(),'center':c['center'].round(4).tolist(),
                'torso_length_px':round(torso(c['pose']),4),'source_detection_index':c['source_detection_index'],
                'identity_status':'UNCERTAIN_ASSOCIATION' if ambiguous else 'TEMPORAL_TRACK_HYPOTHESIS'}
            if any(c['pose'][j,2]<.3 for j in (0,10,13)):
                flags.append({'frame':i,'actor':actor,'kind':'HEAD_OR_FEET_LOW_CONFIDENCE_OR_OCCLUDED'})
        rows.append(row)
    if cap:cap.release()
    return {'schema_version':'1.0','fps':fps,'frames':rows,'flags':flags,
        'track_names':'A starts left and B right; temporary IDs, not verified personal identity',
        'method':'bounded temporal assignment + velocity + body shape + optional torso HSV',
        'physical_force_known':False,'depth_known':False,'human_review_required':True}


def motion_diagnostics(tracked):
    frames=tracked['frames'];fps=tracked['fps'];events=[];flags=list(tracked['flags'])
    last_event={}; previous={}
    for row in frames:
        i=row['frame'];actors=row['actors']
        for actor in ('A','B'):
            other='B' if actor=='A' else 'A'
            if actor not in actors or other not in actors:continue
            p=np.array(actors[actor]['body18']);q=np.array(actors[other]['body18'])
            scale=max(20,actors[other]['torso_length_px'])
            for joint,limb in ((4,'right_hand'),(7,'left_hand')):
                if p[joint,2]<.3:continue
                targets=[j for j in (0,1,2,5,8,11) if q[j,2]>=.3]
                if not targets:continue
                target=min(targets,key=lambda j:float(np.linalg.norm(p[joint,:2]-q[j,:2])))
                distance=float(np.linalg.norm(p[joint,:2]-q[target,:2]))/scale
                key=(actor,limb);old=previous.get(key);previous[key]=(i,distance,p[joint,:2])
                if old is None or old[0]!=i-1:continue
                approach=old[1]-distance
                speed=float(np.linalg.norm(p[joint,:2]-old[2]))/scale
                if distance<.30 and approach>.015 and speed>.02 and i-last_event.get(key,-1000)>round(fps*.30):
                    last_event[key]=i
                    events.append({'id':f'near_{len(events)+1:03}','attacker':actor,'defender':other,'limb':limb,
                        'target_proxy_joint':target,'frame':i,'seconds':i/fps,
                        'normalized_2d_distance':round(distance,4),'approach_per_frame':round(approach,4),
                        'status':'POSSIBLE_2D_NEARNESS_NOT_CONFIRMED_CONTACT','physical_contact_confirmed':False,
                        'phases':{'preparation':[max(0,i-round(fps*.4)),max(0,i-round(fps*.2))],
                            'weight_transfer_and_acceleration':[max(0,i-round(fps*.2)),i],
                            'contact_candidate':[max(0,i-2),min(len(frames)-1,i+2)],
                            'reaction_candidate':[i,min(len(frames)-1,i+round(fps*.3))],
                            'recovery_candidate':[min(len(frames)-1,i+round(fps*.3)),min(len(frames)-1,i+round(fps*.7))]},
                        'phase_status':'HEURISTIC_WINDOWS_REQUIRE_VISUAL_REVIEW','force':'UNKNOWN','depth':'UNKNOWN'})
        if row['assignment_ambiguous']:
            for event in events:
                if event['frame']==i:event['status']='TRACK_AMBIGUITY_INVALIDATES_CONTACT_ASSIGNMENT'
    # These are review flags for either rendering errors OR pose-estimation errors.
    # Image-space displacement is never interpreted as a measured physical force.
    for before,after in zip(frames,frames[1:]):
        for actor,data in after['actors'].items():
            if actor not in before['actors']:continue
            old=before['actors'][actor];p=np.asarray(data['body18']);q=np.asarray(old['body18'])
            scale=max(30,data['torso_length_px'],old['torso_length_px'])
            good=(p[:,2]>=.3)&(q[:,2]>=.3)
            if good.sum()>=4 and float(np.linalg.norm(np.asarray(data['center'])-old['center']))>scale*.65:
                flags.append({'frame':after['frame'],'actor':actor,'kind':'BODY_JUMP_OR_TRACK_OR_CAMERA_ERROR_REVIEW'})
            for joint in np.flatnonzero(good & (np.linalg.norm(p[:,:2]-q[:,:2],axis=1)>scale)):
                flags.append({'frame':after['frame'],'actor':actor,'joint':int(joint),'kind':'JOINT_JUMP_OR_POSE_ERROR_REVIEW'})
            if any(p[j,2]>=.3 and (p[j,0]<3 or p[j,0]>after['width']-3 or p[j,1]<3 or p[j,1]>after['height']-3) for j in (0,4,7,10,13)):
                flags.append({'frame':after['frame'],'actor':actor,'kind':'HEAD_HAND_OR_FOOT_AT_FRAME_EDGE'})
    ambiguous=sum(r['assignment_ambiguous'] for r in frames)
    paired=sum(len(r['actors'])==2 for r in frames)
    return {'schema_version':'1.0','frames':len(frames),'fps':fps,'duration_seconds':len(frames)/fps,
        'paired_tracking_fraction':paired/len(frames),'ambiguous_frame_fraction':ambiguous/len(frames),
        'contact_candidates':events,'flags':flags,'automatic_quality_score':None,
        'identity':'TEMPORAL_TRACKS_ONLY_NOT_FACE_ID_VERIFICATION',
        'contact':'2D_NEARNESS_CANDIDATES_ONLY','biomechanics':'PARTIAL_OBSERVABILITY_NOT_PHYSICS_PROOF',
        'human_verdict':'PENDING','render_success_does_not_imply_cinematic_success':True}


def choreography_ir(tracked, report):
    """Observable image-space state + candidate phase windows, not inferred biomechanics."""
    paired=[r for r in tracked['frames'] if len(r['actors'])==2 and not r['assignment_ambiguous']]
    def state(row):
        a=row['actors'];return {'frame':row['frame'],'seconds':row['seconds'],
            'positions_px':{k:v['center'] for k,v in a.items()},
            'inter_actor_distance_px':float(np.linalg.norm(np.array(a['A']['center'])-a['B']['center'])),
            'units':'image pixels, not meters','identity_status':'TEMPORAL_TRACK_HYPOTHESIS'}
    actions=[]
    for event in report['contact_candidates']:
        i=event['frame'];start=max(0,i-10);end=min(len(tracked['frames'])-1,i+17)
        observations={}
        for actor in ('A','B'):
            a=tracked['frames'][start]['actors'].get(actor);b=tracked['frames'][end]['actors'].get(actor)
            observations[actor]={'displacement_px':(np.array(b['center'])-a['center']).tolist() if a and b else None,
                'reaction_causality':'UNVERIFIED','balance_recovery':'UNVERIFIED'}
        actions.append({**event,'intended_target':'USER_DIRECTION_REQUIRED; proxy_joint_is_not_intention',
            'observations':observations,'weight_transfer':'NOT_MEASURED','phase_verification':'VISUAL_REVIEW_REQUIRED'})
    return {'schema_version':'1.0','content_kind':'live_action','coordinate_system':'image pixels; time at 24 FPS',
        'initial':state(paired[0]) if paired else None,'final':state(paired[-1]) if paired else None,
        'candidate_actions':actions,'physical_depth':'UNKNOWN','force':'UNKNOWN',
        'anime_adaptation':'Requires explicit human staging if anatomy or depth cannot be recovered.',
        'human_approval':'PENDING'}


def compare_poses(reference, candidate):
    """One shared frame-zero translation/scale; never recenter each actor or warp time."""
    def fit_frame(frame):
        points=[]
        for actor in ('A','B'):
            if actor in frame['actors']:
                p=np.asarray(frame['actors'][actor]['body18']);points.extend(p[p[:,2]>=.3,:2])
        if len(points)<4:return None
        points=np.array(points);return points.mean(axis=0),max(20,float(np.ptp(points[:,1])))
    if reference['fps']!=candidate['fps'] or len(reference['frames'])!=len(candidate['frames']):
        raise ValueError('Comparação exige FPS e quantidade de frames idênticos; não haverá alinhamento temporal silencioso.')
    a=next((x for f in reference['frames'] if len(f['actors'])==2 and (x:=fit_frame(f)) is not None),None)
    b=next((x for f in candidate['frames'] if len(f['actors'])==2 and (x:=fit_frame(f)) is not None),None)
    if a is None or b is None:return {'status':'INSUFFICIENT_PAIRED_POSE_EVIDENCE','physical_quality_proven':False}
    offset_a,scale_a=a;offset_b,scale_b=b;errors=[];rows=[]
    for ra,rb in zip(reference['frames'],candidate['frames']):
        distances=[]
        if ra['assignment_ambiguous'] or rb['assignment_ambiguous']:
            rows.append({'frame':ra['frame'],'error':None,'status':'AMBIGUOUS_TRACK_EXCLUDED'});continue
        for actor in ('A','B'):
            if actor not in ra['actors'] or actor not in rb['actors']:continue
            p=np.asarray(ra['actors'][actor]['body18']);q=np.asarray(rb['actors'][actor]['body18'])
            valid=(p[:,2]>=.3)&(q[:,2]>=.3)
            if valid.any():
                distances.extend(np.linalg.norm((p[valid,:2]-offset_a)/scale_a-(q[valid,:2]-offset_b)/scale_b,axis=1).tolist())
        error=float(np.mean(distances)) if distances else None
        rows.append({'frame':ra['frame'],'seconds':ra['seconds'],'error':error,'visible_joint_pairs':len(distances)})
        if error is not None:errors.append(error)
    return {'status':'HEURISTIC_2D_COMPARISON','mean_normalized_pose_error':float(np.mean(errors)) if errors else None,
        'valid_frame_fraction':len(errors)/len(reference['frames']),
        'alignment':'one shared translation/scale from initial paired poses; native timestamps, no DTW',
        'transform':{'reference_offset':offset_a.tolist(),'candidate_offset':offset_b.tolist(),
                     'reference_scale':scale_a,'candidate_scale':scale_b},'per_frame':rows,
        'force_known':False,'contact_proven':False,'identity_proven':False,'physical_quality_proven':False}


def write_review(tracked, source, output):
    """Visual annotations, never an automatic corrected take."""
    cap=cv2.VideoCapture(str(source));frames=tracked['frames'];width=frames[0]['width'];height=frames[0]['height']
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    process=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-y','-f','rawvideo','-pixel_format','bgr24',
        '-video_size',f'{width}x{height}','-framerate',str(tracked['fps']),'-i','pipe:0','-an',
        '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(output)],stdin=subprocess.PIPE)
    try:
        for row in frames:
            ok,image=cap.read()
            if not ok:raise ValueError('Vídeo terminou antes das poses.')
            if image.shape[:2]!=(height,width):image=cv2.resize(image,(width,height))
            for actor,data in row['actors'].items():
                p=np.asarray(data['body18']);color=COLORS[actor]
                for a,b in BODY_EDGES:
                    if min(p[a,2],p[b,2])>=.3:
                        cv2.line(image,tuple(p[a,:2].astype(int)),tuple(p[b,:2].astype(int)),color,2,cv2.LINE_AA)
                c=np.asarray(data['center']).astype(int)
                cv2.putText(image,f'Fighter {actor}'+(' ?' if row['assignment_ambiguous'] else ''),tuple(c+[-30,-35]),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
            cv2.putText(image,f"{row['seconds']:.3f}s | temporal tracks; contact/force NOT verified",(12,22),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1)
            if row['assignment_ambiguous']:cv2.putText(image,'ASSOCIATION UNCERTAIN',(12,44),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,70,255),2)
            process.stdin.write(image.tobytes())
    finally:
        cap.release();process.stdin.close()
    if process.wait(timeout=120):raise RuntimeError('Falha ao exportar prévia de diagnóstico.')


def analyze_file(pose_json, *, video=None, folder=None):
    pose_json=Path(pose_json);folder=Path(folder or pose_json.parent);folder.mkdir(parents=True,exist_ok=True)
    frames=json.loads(pose_json.read_text(encoding='utf-8-sig'))
    tracked=track(frames,video=video)
    report=motion_diagnostics(tracked)
    (folder/'tracking.json').write_text(json.dumps(tracked,indent=2),encoding='utf-8')
    (folder/'diagnostico.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (folder/'coreografia_ir.json').write_text(json.dumps(choreography_ir(tracked,report),indent=2),encoding='utf-8')
    if video:write_review(tracked,video,folder/'previa_marcada.mp4')
    summary=(f"# Diagnóstico do take\n\n{report['frames']} frames, {report['fps']} FPS. "
        f"Dois tracks presentes: {report['paired_tracking_fraction']:.1%}. "
        f"Associação ambígua: {report['ambiguous_frame_fraction']:.1%}.\n\n"
        f"Candidatos de proximidade 2D: {len(report['contact_candidates'])}. "
        "Não representam colisões confirmadas, força ou simulação física.\n\n"
        "Identidade pessoal, impacto, preparação e recuperação exigem revisão visual. "
        "Oclusão, corte, câmera e erros do extrator podem produzir falsos alertas. "
        "Consulte diagnostico.json para os frames e tracking.json para os pontos.\n")
    (folder/'DIAGNOSTICO_TAKE.md').write_text(summary,encoding='utf-8')
    return report
