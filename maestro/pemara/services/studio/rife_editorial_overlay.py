"""Optional source-bound ASS in the existing exact60 encoder; no inference."""
from pathlib import Path
from fractions import Fraction
import json,re,subprocess
from rife_known_native_cuts import need,digest
PROTOCOL='pemara-source-bound-editorial-titles-v1'

def ass_time(value):
 fields=value.strip().split(':');need(len(fields)==3,'ASS_TIME_FORMAT_REQUIRED')
 h,m=map(int,fields[:2]);s=Fraction(fields[2])
 need(h>=0 and 0<=m<60 and 0<=s<60,'ASS_TIME_RANGE_INVALID')
 return h*3600+m*60+s

def validate(data,original_hash,native_frames,native_fps,restored_frames,restored_fps,width,height,ass_text):
 need(data.get('protocol')==PROTOCOL,'TITLE_PROTOCOL_REQUIRED')
 need(data.get('source_sha256')==original_hash,'TITLE_ORIGINAL_HASH_MISMATCH')
 need(type(data.get('native_frames')) is int and data['native_frames']==native_frames==restored_frames,'TITLE_FRAME_PRESERVATION_REQUIRED')
 rate=Fraction(native_fps);need(Fraction(data['native_fps'])==rate==Fraction(restored_fps),'TITLE_NATIVE_CADENCE_CHANGED')
 need((data.get('target_width'),data.get('target_height'),data.get('output_fps'))==(width,height,60),'TITLE_TARGET_GEOMETRY_CADENCE_CHANGED')
 need(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.ass',data.get('ass_filename','')),'TITLE_SAFE_SIBLING_BASENAME_REQUIRED')
 need(re.search(r'^PlayResX:\s*'+str(width)+r'\s*$',ass_text,re.M) and re.search(r'^PlayResY:\s*'+str(height)+r'\s*$',ass_text,re.M),'ASS_TARGET_GEOMETRY_REQUIRED')
 need('[Events]' in ass_text and '[V4+ Styles]' in ass_text,'ASS_EVENTS_AND_STYLES_REQUIRED')
 duration=Fraction(native_frames,1)/rate;target=duration*60
 need(target.denominator==1 and 24<=rate<=60,'TITLE_EXACT60_DURATION_REQUIRED')
 events=[]
 for line in ass_text.splitlines():
  if line.startswith('Dialogue:'):
   fields=line.split(',',9);need(len(fields)==10,'ASS_EVENT_FIELDS_INVALID')
   start,end=ass_time(fields[1]),ass_time(fields[2]);need(0<=start<end<=duration,'ASS_EVENT_OUTSIDE_CURRENT_CLIP')
   events.append({'start_seconds':str(start),'end_seconds':str(end),'style':fields[3],'text':fields[9]})
 need(0<len(events)<=8,'BOUNDED_EDITORIAL_TITLE_EVENTS_REQUIRED')
 return {'protocol':PROTOCOL,'source_sha256':original_hash,'native_frames':native_frames,'native_fps':str(rate),
  'target_frames':int(target),'output_fps':60,'width':width,'height':height,'events':events,
  'source_frames_audio_and_clock_unchanged':True,'overlay_clock':'j/60; same encoder and timestamps; no extra frames',
  'filter':'ass=filename='+data['ass_filename'],'visual_acceptance_claimed':False}

def load_original_source_overlay(original,restored_frames,restored_fps,width,height,ffprobe):
 original=Path(original).resolve(strict=True);companion=Path(str(original)+'.titles.json')
 companion_hash=digest(companion)
 data=json.loads(companion.read_text(encoding='utf-8-sig'))
 need(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.ass',data.get('ass_filename','')),'TITLE_SAFE_SIBLING_BASENAME_REQUIRED')
 ass=(original.parent/data['ass_filename']).resolve(strict=True);need(ass.parent==original.parent,'TITLE_SIBLING_REQUIRED')
 need(digest(ass)==data.get('ass_sha256'),'TITLE_SCRIPT_HASH_MISMATCH')
 raw=subprocess.check_output([str(ffprobe),'-v','error','-count_frames','-select_streams','v:0','-show_streams','-of','json',str(original)],stderr=subprocess.PIPE)
 streams=json.loads(raw)['streams'];need(len(streams)==1,'TITLE_ONE_ORIGINAL_VIDEO_REQUIRED')
 stream=streams[0];need(Fraction(stream['avg_frame_rate'])==Fraction(stream['r_frame_rate']),'TITLE_ORIGINAL_CFR_REQUIRED')
 original_hash=digest(original)
 proof=validate(data,original_hash,int(stream['nb_read_frames']),stream['avg_frame_rate'],restored_frames,restored_fps,width,height,ass.read_text(encoding='utf-8-sig'))
 need(digest(original)==original_hash and digest(ass)==data['ass_sha256'] and digest(companion)==companion_hash,'TITLE_INPUT_CHANGED_DURING_PROBE')
 proof.update(companion={'path':str(companion),'sha256':companion_hash},ass_script={'path':str(ass),'sha256':data['ass_sha256']},original_source_path=str(original))
 return ass,proof
