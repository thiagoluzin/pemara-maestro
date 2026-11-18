import io
import json
from pathlib import Path
import wave
import pytest
import production_presets as presets
import video_projects as vp

@pytest.fixture
def project(tmp_path):
    view=vp.create_project(tmp_path,name='Saiyan test',project_id='saiyan_test',production_preset=presets.PRESET)
    return tmp_path/'saiyan_test',view

def test_preset_is_seven_takes_70_seconds_at_24fps(project):
    folder,view=project;q=presets._read(folder/'take_queue.json')
    assert len(q['takes'])==7 and view['durationSeconds']==70 and view['final']['fps']==24
    assert view['productionPreset']==presets.PRESET
    assert all(t['video_generation']['frames']==243 and t['video_generation']['steps']==20 for t in q['takes'])
    assert all(t['video_generation']['h3_scene_profile']=='combat_full_v1' for t in q['takes'])

def test_new_anchors_only_and_no_voice_or_publication(project):
    folder,_=project;m=presets._read(folder/'project_manifest.json');b=presets._read(folder/'character_bible.json')
    assert m['new_anchors_required'] and not m['reuse_historical_images']
    assert not b['approved_references'] and not m['audio']['human_vocalizations']
    assert not m['automatic_batch_allowed'] and not m['finishing_policy']['dlss_video']

def test_preset_preserves_builtin_image_generator_choice(project):
    folder,view=project
    assert view['anchorGeneration']['provider']=='codex_builtin_imagegen'
    assert view['anchorGeneration']['localExecutorAllowed'] is False

def test_saiyan_cannot_enter_generic_60fps_finishing(project):
    folder,_=project
    with pytest.raises(ValueError,match='24 FPS'):
        vp.get_take_upscale_spec(folder.parent,folder.name,'T01')

def test_r17_return_uses_its_own_exact_ten_second_pilot_gate(project):
    folder,_=project;m=presets._read(folder/'project_manifest.json')
    m['production_route_id']='r17_start_chain_owner_10s_v1';presets._write(folder/'project_manifest.json',m)
    q=presets._read(folder/'take_queue.json')
    obsolete=folder/'qc/old.mp4';obsolete.write_bytes(b'old unit artifact')
    presets._write(folder/'qc/single_contact_pilot.json',{'owner_approved':True,'artifact':'qc/old.mp4','sha256':presets.sha(obsolete)})
    with pytest.raises(ValueError,match='piloto R17'):presets.validate_admission(folder,q['takes'][0],q)
    fresh=folder/'qc/r17.mp4';fresh.write_bytes(b'new unit artifact')
    record={'owner_approved':True,'artifact':'qc/r17.mp4','sha256':presets.sha(fresh)}
    presets._write(folder/'qc/r17_10s_pilot.json',record)
    presets.validate_admission(folder,q['takes'][0],q)
    fresh.write_bytes(b'changed artifact')
    with pytest.raises(ValueError,match='bytes'):presets.validate_admission(folder,q['takes'][0],q)

def test_storyboard_subplans_cover_exactly_each_ten_seconds(project):
    folder,_=project;s=presets._read(folder/'storyboard.json')
    for take in s['takes']:
        plans=take['subplans'];assert plans[0]['editorial_range_seconds'][0]==0
        assert plans[-1]['editorial_range_seconds'][1]==10
        for a,b in zip(plans,plans[1:]):assert a['editorial_range_seconds'][1]==b['editorial_range_seconds'][0]
        assert all('No dialogue' in p['prompt_en'] for p in plans)
    assert s['end']=='FIRST_ENERGY_CONTACT_NO_WINNER'

def test_final_sequence_stops_at_first_collision(project):
    folder,_=project;s=presets._read(folder/'storyboard.json');last=s['takes'][-1]['subplans'][-1]['prompt_en']
    assert 'FIRST visible frame' in last and 'No sustained beam struggle' in last

def test_unreviewed_single_pilot_blocks_generation(project):
    folder,_=project;q=presets._read(folder/'take_queue.json')
    with pytest.raises(ValueError,match='único soco'):presets.validate_admission(folder,q['takes'][0],q)
    with pytest.raises(ValueError,match='T01 exato'):presets.validate_admission(folder,q['takes'][1],q)

def test_pilot_hash_and_scope_are_checked(project):
    folder,_=project;q=presets._read(folder/'take_queue.json');p=folder/'qc/pilot.mp4';p.write_bytes(b'unit fixture; not a real cinematic result')
    record={'owner_approved':True,'artifact':'qc/pilot.mp4','sha256':presets.sha(p)}
    presets._write(folder/'qc/single_contact_pilot.json',record)
    presets.validate_admission(folder,q['takes'][0],q)
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='bytes'):presets.validate_admission(folder,q['takes'][0],q)

def test_existing_projects_keep_their_policy(tmp_path):
    vp.create_project(tmp_path,name='Existing project',project_id='existing',content_kind='animation')
    presets.validate_admission(tmp_path/'existing',{}, {'takes':[]})
    assert vp.get_project(tmp_path,'existing')['productionPreset']==''

def test_unknown_preset_does_not_create_directory(tmp_path):
    with pytest.raises(ValueError):vp.create_project(tmp_path,name='Unknown preset',project_id='bad',production_preset='invented')
    assert not (tmp_path/'bad').exists()

def test_soundtrack_preserves_all_bytes_beyond_first_megabyte(project):
    folder,_=project;buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(b'\0'*48000*4*8)
    original=buf.getvalue();assert len(original)>1024*1024
    record=presets.store_soundtrack(folder,io.BytesIO(original),'test.wav',rights_confirmed=True)
    assert (folder/'audio'/record['file']).read_bytes()==original
    assert record['voices']=='UNKNOWN' and record['listening']=='PENDING_OWNER'

def test_soundtrack_needs_owner_file_and_usage_authorization(project):
    folder,_=project
    with pytest.raises(ValueError,match='Confirme'):presets.store_soundtrack(folder,io.BytesIO(b''),'a.wav')
    with pytest.raises(ValueError,match='Formato'):presets.store_soundtrack(folder,io.BytesIO(b''),'a.exe',rights_confirmed=True)

def test_reference_review_is_bound_to_exact_hash(project):
    folder,_=project;source=folder/'refs/a.png';source.write_bytes(b'unit hash fixture, not generated artwork')
    presets._write(folder/'production_assets.json',{'assets':[{'id':'SS02','file':'refs/a.png','sha256':presets.sha(source),'status':'PENDING'}]})
    with pytest.raises(ValueError,match='mudou'):presets.review_asset(folder,'SS02',decision='APPROVED',expected_sha256='0'*64)
    result=presets.review_asset(folder,'SS02',decision='APPROVED',expected_sha256=presets.sha(source))
    assert result['status']=='APPROVED' and 'no video' in result['review_scope']
    source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='registrado'):presets.asset_path(folder,'SS02')

def test_reference_cannot_escape_project(project,tmp_path):
    folder,_=project;outside=tmp_path/'outside.png';outside.write_bytes(b'fixture')
    presets._write(folder/'production_assets.json',{'assets':[{'id':'SS02','file':str(outside),'sha256':presets.sha(outside),'status':'PENDING'}]})
    with pytest.raises(ValueError):presets.asset_path(folder,'SS02')
