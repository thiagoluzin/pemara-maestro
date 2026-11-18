"""Current owner-authorized live-action finishing, without any spatial neural pass.

Executed only by ComfyUI's serial worker. This is not a ComfyUI client.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import json
import os
import subprocess
import time
import uuid

STUDIO = Path(__file__).resolve().parent

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(path)]))


# One exact-source exception authorized by the owner on2026-11-16. Other
# animation sources remain blocked here and retain the canonical Seed route.
ANIMATION_EXCEPTION_MANIFEST = Path('G:\\a vida de uma familia atipica\\acabamento_fhd60_v001\\FAST_AUTHORIZATION.json')
ANIMATION_EXCEPTION_SHA256 = 'a08e22e0e4cdf95d7ebaf57ea428c1d6c060d6b571284b9f5a28fb893ef7a687'
ANIMATION_EXCEPTION_SOURCE_SHA256 = 'a5a651ea18eab9e49749719fddfb1c368b055f9b564510205edb99f7ef974c5b'

def validate_animation_exception(authorization_manifest, source_sha256, width, height, cuts, frames, fps):
    supplied=Path(authorization_manifest).resolve(strict=True)
    # Exact E02 owner authorization; preserve the pre-existing E01 exception.
    if source_sha256 == '58d9ae9b7a67f9dbab10c168ae6e1026e40a57e9201497f5694e405f365dad72':
        if supplied != Path('G:\\a vida de uma familia atipica\\acabamento_T01E02_fhd60_v001\\FAST_AUTHORIZATION.json').resolve(strict=True) or sha(supplied) != '5864382bde6c4a595a5c2ef000a045459d84e85da3feba5aa8931bbabdff3c83':
            raise ValueError('Exact E02 owner finishing authorization required.')
        data=json.loads(supplied.read_text(encoding='utf-8-sig'))
        if (data.get('status')!='OWNER_AUTHORIZED_FAST_FINISHING' or data.get('content_kind')!='animation'
                or data['source']['sha256']!=source_sha256 or (width,height,frames,Fraction(fps))!=(1920,1080,5792,Fraction(24))
                or cuts!=[362*n for n in range(1,16)] or data['known_native_cut_frames']!=cuts
                or any(data.get(k) is not False for k in ('seedvr2','dlss5_video','spatial_neural_restoration'))):
            raise ValueError('E02 finishing source, geometry, cuts or policy changed.')
        return {'id':data['authorization_id'],'manifest':str(supplied),'sha256':sha(supplied),'source_sha256':source_sha256,
            'owner_request':data['owner_request'],'content_kind':'animation','global_animation_default_unchanged':True,'human_approval_of_new_derivative_claimed':False}
    if supplied!=ANIMATION_EXCEPTION_MANIFEST.resolve(strict=True) or sha(supplied)!=ANIMATION_EXCEPTION_SHA256:
        raise ValueError('Exact owner animation finishing authorization required.')
    data=json.loads(supplied.read_text(encoding='utf-8-sig'))
    if data.get('status')!='OWNER_AUTHORIZED_FAST_FINISHING' or data.get('content_kind')!='animation':
        raise ValueError('Animation exception status/classification invalid.')
    if source_sha256!=ANIMATION_EXCEPTION_SOURCE_SHA256 or data['source']['sha256']!=source_sha256:
        raise ValueError('Animation exception belongs to a different source.')
    if (width,height,frames,Fraction(fps))!=(1920,1080,5792,Fraction(24)):
        raise ValueError('Animation exception geometry/cadence/source length changed.')
    if cuts!=[362*n for n in range(1,16)] or data['known_native_cut_frames']!=cuts:
        raise ValueError('All15 exact owner-master edit boundaries required.')
    if data.get('seedvr2') is not False or data.get('dlss5_video') is not False or data.get('spatial_neural_restoration') is not False:
        raise ValueError('Animation exception cannot add a neural spatial pass.')
    return {'id':data['authorization_id'],'manifest':str(supplied),'sha256':sha(supplied),
        'source_sha256':source_sha256,'owner_request':data['owner_request'],'content_kind':'animation',
        'global_animation_default_unchanged':True,'human_approval_of_new_derivative_claimed':False}

class PemaraLanczosRife60NoNRSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'source_video': ('VIDEO',),
            'width': ('INT', {'default':1920,'min':1080,'max':3840}),
            'height': ('INT', {'default':1080,'min':1080,'max':3840}),
            'filename_prefix': ('STRING', {'default':'finishing_no_nr/candidate'}),
            'content_kind': (['live_action','mixed','animation'],),
            'expected_sha256': ('STRING', {'default':''}),
            'known_cut_frames_json': ('STRING', {'default':'[]'})},
            'optional': {'authorization_manifest': ('STRING', {'default':''})},
            'hidden': {'prompt':'PROMPT'}}
    RETURN_TYPES = ('VIDEO',)
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Pemara/Finishing'

    def save(self, source_video, width, height, filename_prefix, content_kind,
             expected_sha256, known_cut_frames_json, prompt, authorization_manifest=''):
        import folder_paths
        import comfy.model_management as mm
        from comfy_api.latest import VideoFromFile
        import upscaling_required as policy
        assert content_kind in {'live_action','mixed','animation'}
        assert (width,height) in policy.TARGETS
        source = source_video.get_stream_source()
        assert isinstance(source,str), 'Verified file source required.'
        source = Path(source).resolve()
        roots = [Path(folder_paths.get_input_directory()).resolve(),Path(folder_paths.get_output_directory()).resolve()]
        assert any(source.is_relative_to(root) for root in roots)
        assert source_video.get_active_trim_window() == (0.0,0.0)
        assert len(expected_sha256)==64 and sha(source)==expected_sha256
        before=probe(source);v=next(s for s in before['streams'] if s['codec_type']=='video')
        fps=Fraction(v['avg_frame_rate']);frames=int(v['nb_read_frames'])
        assert Fraction(v['r_frame_rate'])==fps and 24<=fps<=60
        assert v['pix_fmt']=='yuv420p' and v.get('color_transfer') not in {'smpte2084','arib-std-b67'}
        assert sum(s['codec_type']=='audio' for s in before['streams'])<=1
        cuts=json.loads(known_cut_frames_json)
        assert isinstance(cuts,list) and all(type(n) is int and 0<n<frames for n in cuts)
        authorization=None
        if content_kind=='animation':
            authorization=validate_animation_exception(authorization_manifest,expected_sha256,width,height,cuts,frames,fps)
        elif authorization_manifest:
            raise ValueError('Animation-only authorization cannot relabel live-action/mixed media.')
        prefix=Path(filename_prefix)
        assert not prefix.is_absolute() and '..' not in prefix.parts
        root=Path(folder_paths.get_output_directory()).resolve()
        directory=root/prefix.parent;directory.mkdir(parents=True,exist_ok=True)
        token=uuid.uuid4().hex[:12];final=directory/(prefix.name+'_'+token+'.mp4')
        cut_path=directory/(prefix.name+'_'+token+'.cuts.json')
        cut_path.write_text(json.dumps(sorted(set(cuts))),encoding='utf8')
        mm.unload_all_models();mm.soft_empty_cache()
        runner=STUDIO/'rife_required_runner.py'
        command=[str(policy.RIFE_REPO/'.venv/Scripts/python.exe'),str(runner),str(source),str(source),str(final),
            '--width',str(width),'--height',str(height),'--lanczos','--cuts-json',str(cut_path)]
        started=time.monotonic()
        with Path(str(final)+'.worker.log').open('wb') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        after=probe(final);out=next(s for s in after['streams'] if s['codec_type']=='video')
        assert (out['width'],out['height'])==(width,height)
        assert Fraction(out['avg_frame_rate'])==60 and int(out['nb_read_frames'])==policy.output_frame_count(frames,str(fps))
        assert abs(float(out['duration'])-frames/float(fps))<.002
        for k in ('color_range','color_space','color_transfer','color_primaries'):
            assert out.get(k)==v.get(k),(k,v.get(k),out.get(k))
        def audio_hash(path):
            return hashlib.sha256(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0?','-c:a','copy','-f','data','pipe:1'])).hexdigest()
        assert audio_hash(source)==audio_hash(final), 'Original audio bitstream changed.'
        assert sha(source)==expected_sha256
        subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],check=True,capture_output=True)
        receipt={'pipeline':'lanczos_nvenc_rife425_exact60_no_nr_v1','content_kind':content_kind,
            'source':str(source),'source_sha256':expected_sha256,'output':str(final),'output_sha256':sha(final),
            'frames':int(out['nb_read_frames']),'fps':60,'width':width,'height':height,
            'duration_seconds':frames/float(fps),'audio_bitstream_preserved':True,
            'dlss5_video':False,'seedvr2':False,'spatial_neural_restoration':False,
            'command':command,'runner_sha256':sha(runner),'model_sha256':policy.RIFE_HASH,
            'known_native_cut_frames':sorted(set(cuts)),'elapsed_seconds':round(time.monotonic()-started,3),
            'processing_graph':prompt,'technical_pass':True,'owner_approval':'PENDING'}
        if authorization:
            receipt['pipeline']='lanczos_nvenc_rife425_exact60_animation_owner_exception_v1'
            receipt['owner_authorization']=authorization
        Path(str(final)+'.finishing.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
        record={'filename':final.name,'subfolder':final.parent.relative_to(root).as_posix(),'type':'output'}
        return {'ui':{'videos':[record]},'result':(VideoFromFile(str(final)),)}
