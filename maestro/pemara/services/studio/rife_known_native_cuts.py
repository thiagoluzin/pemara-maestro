"""Hash-bound cut metadata carried across frame-preserving Seed restoration.

Pure metadata/clock validation; no model, torch, Comfy or network operation.
Live installation requires separately admitted, source-specific processing.
"""
from fractions import Fraction
from pathlib import Path
import hashlib,json,subprocess
PROTOCOL='pemara-frame-preserving-native-cuts-v2'

def need(ok,message):
 if not ok:raise ValueError(message)

def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def validate(data,original_hash,original_frames,original_fps,restored_frames,restored_fps):
 need(data.get('protocol')==PROTOCOL,'CUT_PROTOCOL_REQUIRED')
 need(data.get('source_sha256')==original_hash,'CUT_ORIGINAL_SOURCE_HASH_MISMATCH')
 need(type(data.get('native_frames')) is int and data['native_frames']==original_frames==restored_frames,'CUT_FRAME_PRESERVATION_REQUIRED')
 old,new=Fraction(original_fps),Fraction(restored_fps)
 need(Fraction(data['native_fps'])==old==new and 24<=old<=60,'CUT_NATIVE_CADENCE_PRESERVATION_REQUIRED')
 cuts=data.get('native_cut_frames')
 need(isinstance(cuts,list) and bool(cuts) and all(type(x) is int and 0<x<original_frames for x in cuts),'CUT_RANGE_OR_TYPE_INVALID')
 need(cuts==sorted(set(cuts)),'CUTS_SORTED_AND_UNIQUE_REQUIRED')
 total=Fraction(original_frames,1)/old*60
 need(total.denominator==1,'WHOLE_CLIP_NOT_EXACT60_ALIGNED')
 boundaries=[]
 for cut in cuts:
  native_time=Fraction(cut,1)/old
  target_time=native_time*60
  first=(target_time.numerator+target_time.denominator-1)//target_time.denominator
  boundaries.append({'native_first_new_frame':cut,'native_boundary_seconds':str(native_time),
   'first_new_target_frame':first,'first_new_target_PTS_seconds':str(Fraction(first,60)),
   'representation_offset_seconds':str(Fraction(first,60)-native_time),
   'previous_target_holds_old_angle_when_fractional':True,
   'source_clock_or_duration_changed':False})
 return {'protocol':PROTOCOL,'source_sha256':original_hash,'native_frames':original_frames,'native_fps':str(old),
  'target_frames':int(total),'target_fps':60,'native_cut_frames':cuts,'boundaries':boundaries,
  'scope':'Known cut suppresses optical flow across angles. Exact output grid remains j/60; quantization is explicit, not a native clock edit. Actual Seed/RIFE quality is not proved here.'}

def load_audio_source_companion(original,restored_frames,restored_fps,ffprobe):
 original=Path(original);companion=Path(str(original)+'.cuts.json')
 companion_hash=digest(companion)
 data=json.loads(companion.read_text(encoding='utf-8-sig'))
 raw=subprocess.check_output([str(ffprobe),'-v','error','-count_frames','-select_streams','v:0','-show_streams','-of','json',str(original)],stderr=subprocess.PIPE)
 streams=json.loads(raw)['streams'];need(len(streams)==1,'ONE_ORIGINAL_VIDEO_STREAM_REQUIRED')
 s=streams[0];need(Fraction(s['avg_frame_rate'])==Fraction(s['r_frame_rate']),'ORIGINAL_CFR_REQUIRED')
 original_hash=digest(original)
 proof=validate(data,original_hash,int(s['nb_read_frames']),s['avg_frame_rate'],restored_frames,restored_fps)
 need(digest(original)==original_hash and digest(companion)==companion_hash,'CUT_INPUT_CHANGED_DURING_PROBE')
 proof['companion']={'path':str(companion.resolve()),'sha256':companion_hash}
 proof['original_source_path']=str(original.resolve())
 return set(proof['native_cut_frames']),proof
