"""Serial SeedVR2 3B -> exact RIFE60 -> DLSS5 -> original-audio export."""
from pathlib import Path
from fractions import Fraction
import json
import os
import shutil
import subprocess
import sys
import uuid

STUDIO = Path(r'E:\Pemara\maestro\pemara\services\studio')
sys.path.insert(0, str(STUDIO)) if str(STUDIO) not in sys.path else None
import dlss5_finishing as dlss
import upscaling_required as policy
import folder_paths

class PemaraUpscaleRequiredSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'source_video': ('VIDEO',),
            'width': ('INT', {'default':1920,'min':1080,'max':3840}),
            'height': ('INT', {'default':1080,'min':1080,'max':3840}),
            'filename_prefix': ('STRING', {'default':'upscaling_obrigatorio/candidate'}),
            'profile_id': ('STRING', {'default':policy.profile_id(1920,1080)})},
            'hidden': {'prompt':'PROMPT'}}
    RETURN_TYPES = ('VIDEO',)
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Pemara/Finishing'
    IS_CHANGED = classmethod(lambda cls, **kwargs: float('nan'))

    def save(self, images, source_video, width, height, filename_prefix, profile_id, prompt):
        import comfy.model_management as mm
        from comfy_api.latest import VideoFromFile
        profile = policy.assert_graph(prompt)
        assert profile_id == profile['profile_id'] == policy.profile_id(width,height)
        dlss.preflight()
        source = source_video.get_stream_source()
        if not isinstance(source,str):
            raise ValueError('Fonte deve ser um arquivo verificável; preservar áudio original.')
        source = Path(source).resolve()
        roots = [Path(folder_paths.get_input_directory()).resolve(),
                 Path(folder_paths.get_output_directory()).resolve()]
        if not any(source.is_relative_to(root) for root in roots):
            raise ValueError('Fonte fora das raízes de mídia do runtime.')
        if source_video.get_active_trim_window() != (0.0,0.0):
            raise ValueError('Aplicar cortes antes do acabamento; esta etapa preserva a fonte inteira.')
        source_hash = dlss.sha(source)
        before = dlss._probe(source)
        video = next(s for s in before['streams'] if s['codec_type']=='video')
        audio = [s for s in before['streams'] if s['codec_type']=='audio']
        if len(audio)>1 or video['pix_fmt'] not in {'yuv420p','yuvj420p','rgb24','bgr24','yuv444p'}:
            raise ValueError('Este perfil exige SDR 8-bit e no máximo uma faixa de áudio.')
        if video.get('color_transfer') in {'smpte2084','arib-std-b67'}:
            raise ValueError('HDR exige perfil próprio, sem conversão silenciosa para SDR.')
        fps = Fraction(video['avg_frame_rate'])
        if Fraction(video['r_frame_rate']) != fps or not 24 <= fps <= 60:
            raise ValueError('Cadência deve ser CFR entre 24 e 60 FPS.')
        frames = int(video['nb_read_frames'])
        target_frames = policy.output_frame_count(frames, str(fps))
        duration = float(Fraction(frames,1)/fps)
        timestamps = dlss._timestamps(source)
        if len(timestamps)!=frames or any(abs(t-i/float(fps))>0.002 for i,t in enumerate(timestamps)):
            raise ValueError('Fonte com PTS irregular: corrigir antes do RIFE exato.')
        if images.ndim==5 and images.shape[0]==1:
            images = images[0]
        if images.ndim!=4 or images.shape[0]!=frames:
            raise ValueError('SeedVR2 deve conservar todos os quadros da fonte, sem truncamento.')
        cw,ch = policy.contain_dimensions(video['width'],video['height'],width,height)
        if tuple(images.shape[1:3])!=(ch,cw):
            raise ValueError('Geometria SeedVR2 diverge do plano contain/pad.')
        out_root = Path(folder_paths.get_output_directory()).resolve()
        prefix = Path(filename_prefix)
        if prefix.is_absolute() or '..' in prefix.parts:
            raise ValueError('Prefixo de exportação inválido.')
        destination = out_root / prefix.parent
        destination.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex[:12]
        final = destination / (prefix.name+'_'+token+'.mp4')
        work = destination / ('.required_work_'+token)
        work.mkdir()
        seed_file = work/'seedvr2_native_fps.mp4'
        candidate = work/'candidate60.mp4'
        # Retain SeedVR2's float CPU frames; unload cached diffusion models
        # before RIFE/D3D12. The ComfyUI serial worker owns this entire job.
        mm.unload_all_models()
        mm.soft_empty_cache()
        encoder = shutil.which('ffmpeg')
        if not encoder:
            raise ValueError('FFmpeg com libx264 ausente; sem fallback de codec.')
        with (work/'seed_encode.log').open('wb') as log:
            process = subprocess.Popen([encoder,'-v','error','-y','-f','rawvideo',
                '-pix_fmt','rgb24','-s',f'{cw}x{ch}','-r',str(fps),'-i','-',
                '-an','-c:v','libx264','-preset','slow','-crf','15','-pix_fmt','yuv420p',str(seed_file)],
                stdin=subprocess.PIPE,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                for image in images:
                    process.stdin.write((image[...,:3].clamp(0,1)*255).round().byte().cpu().contiguous().numpy().tobytes())
                process.stdin.close()
                if process.wait()!=0:
                    raise RuntimeError('Falha ao salvar a etapa SeedVR2; intermediário preservado.')
            finally:
                if process.poll() is None:
                    process.kill()
        rife_python = policy.RIFE_REPO/'.venv/Scripts/python.exe'
        command = [str(rife_python),str(STUDIO/'rife_required_runner.py'),str(seed_file),
                   str(source),str(candidate),'--width',str(width),'--height',str(height)]
        with (work/'rife.log').open('wb') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        # DLSS is final and idempotent. This also checks full decode and audio.
        dlss.finish_file(candidate)
        after = dlss._probe(candidate)
        v = next(s for s in after['streams'] if s['codec_type']=='video')
        assert (v['width'],v['height'])==(width,height)
        assert Fraction(v['avg_frame_rate'])==60 and int(v['nb_read_frames'])==target_frames
        assert abs(float(v['duration'])-duration)<=0.002
        pts = dlss._timestamps(candidate)
        assert len(pts)==target_frames and all(abs(t-i/60)<=0.002 for i,t in enumerate(pts))
        if audio:
            assert dlss._audio_hash(source)==dlss._audio_hash(candidate), 'Áudio original alterado.'
            assert dlss._audio_pcm_hash(source,duration)==dlss._audio_pcm_hash(candidate,duration), 'Sinal de áudio alterado.'
        else:
            assert not any(s['codec_type']=='audio' for s in after['streams'])
        assert dlss.sha(source)==source_hash, 'Fonte mudou durante o acabamento.'
        shutil.copy2(candidate,final)
        dlss.carry_receipt(candidate,final)
        receipt = {'required':True,'pipeline_version':policy.PIPELINE,'profile_id':profile_id,
            'profile':profile,'source':str(source),'source_sha256':source_hash,
            'output':str(final),'output_sha256':dlss.sha(final),'technical_pass':True,
            'source_frames':frames,'source_fps':str(fps),'frames':target_frames,
            'fps':60,'width':width,'height':height,'duration_seconds':duration,
            'audio_preserved':bool(audio),'audio_absent_preserved':not bool(audio),
            'timestamps':'j/60','seed_graph':{k:{'class_type':n['class_type'],'inputs':n['inputs']} for k,n in prompt.items()},'intermediates':str(work),
            'human_approval':'PENDING','approval_of_reference_is_not_approval_of_new_output':True}
        dlss._atomic_json(policy.receipt_path(final),receipt)
        record = {'filename':final.name,'subfolder':final.parent.relative_to(out_root).as_posix(),
                  'type':'output','upscaling_required':True,'profile':profile_id}
        return {'ui':{'videos':[record]},'result':(VideoFromFile(str(final)),)}

class PemaraUpscalingPolicy:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{}}
    RETURN_TYPES = ('STRING',)
    FUNCTION = 'status'
    CATEGORY = 'Pemara/Finishing'
    def status(self):
        return (json.dumps(policy.policy_status()),)

NODE_CLASS_MAPPINGS = {'PemaraUpscaleRequiredSave':PemaraUpscaleRequiredSave,
                      'PemaraUpscalingPolicy':PemaraUpscalingPolicy}
NODE_DISPLAY_NAME_MAPPINGS = {'PemaraUpscaleRequiredSave':'Upscaling obrigatório — SeedVR2 3B + RIFE60 + DLSS5 + áudio',
                             'PemaraUpscalingPolicy':'Upscaling obrigatório — política'}
