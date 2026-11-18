"""Owner video prohibition must fire before IO, receipts, GPU admission or NR."""
import pytest
import dlss5_finishing as dlss

@pytest.mark.parametrize('suffix',['.mp4','.mov','.mkv','.webm','.avi','.gif','.apng'])
@pytest.mark.parametrize('kind',['live_action','mixed','animation'])
def test_video_rejected_before_processing(tmp_path,monkeypatch,suffix,kind):
    path=tmp_path/('original'+suffix)
    path.write_bytes(b'unchanged source')
    def forbidden(*args,**kwargs):
        raise AssertionError('Video must be rejected before any finishing work')
    monkeypatch.setattr(dlss,'preflight',forbidden)
    monkeypatch.setattr(dlss,'valid_receipt',forbidden)
    assert not hasattr(dlss,'_video'), 'Obsolete temporal NR implementation must stay deleted'
    with pytest.raises(dlss.DLSS5RequiredError,match='proibido em videos'):
        dlss.finish_file(path,content_kind=kind)
    assert path.read_bytes()==b'unchanged source'
    assert list(tmp_path.iterdir())==[path]

def test_anchor_policy_remains_enabled():
    policy=dlss.content_policy.status()
    assert policy['anchors']=='full_frame_required'
    assert policy['video_dlss5_allowed'] is False
