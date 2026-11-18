from pathlib import Path
import hashlib,json,shutil
import pytest
import dlss5_finishing as dlss
import upscaling_required as policy

@pytest.mark.parametrize('kind',['animation','live_action','mixed'])
def test_new_profiles_do_not_schedule_video_nr(kind):
    for size in policy.TARGETS:
        profile=policy.canonical_profile(*size,kind)
        assert 'dlss5' not in profile['profile_id']
        assert profile['dlss5']=={'allowed_on_video':False,'scope':'anchors_only'}
        assert not any('DLSS' in stage for stage in profile['stages'])
        assert policy.load_profile(policy.PROFILE_DIR/(profile['profile_id']+'.json'))==profile
        if kind!='animation':assert 'seedvr2' not in profile

def test_removed_video_implementation_and_wrapper_are_absent():
    assert not hasattr(dlss,'_video')
    assert not hasattr(dlss,'WRAPPER')
    assert not Path(r'E:\Pemara\third_party\video2dlssnr-v1.4.1\release\nr_video_frame_preserving.py').exists()

@pytest.mark.parametrize('suffix',['.png','.jpg','.webp'])
def test_anchor_route_still_uses_single_image_processor(tmp_path,monkeypatch,suffix):
    from PIL import Image
    p=tmp_path/('anchor'+suffix);Image.new('RGB',(64,64),(40,60,80)).save(p)
    called=[]
    monkeypatch.setattr(dlss,'preflight',lambda:None)
    def image(source,dest,log):
        called.append(source);shutil.copy2(source,dest);return {'frames':1,'width':64,'height':64}
    monkeypatch.setattr(dlss,'_image',image)
    proof=dlss.finish_file(p,content_kind='animation')
    assert len(called)==1 and proof['technical_pass'] and proof['frames']==1
    assert dlss.valid_receipt(p)==proof

def test_video_policy_record_does_not_call_nr_or_change_bytes(tmp_path,monkeypatch):
    p=tmp_path/'movie.mp4';p.write_bytes(b'original audio and video bytes');before=dlss.sha(p)
    def forbidden(*a,**k):raise AssertionError('No rendering permitted')
    monkeypatch.setattr(dlss,'_image',forbidden);monkeypatch.setattr(dlss,'preflight',forbidden)
    proof=dlss.preserve_video_policy(p)
    assert dlss.sha(p)==before and proof['output_sha256']==before
    assert proof['dlss5_applied'] is False and proof['applied'] is False
