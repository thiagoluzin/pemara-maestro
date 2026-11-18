import io
from unittest.mock import patch
from PIL import Image
import main
from types import SimpleNamespace
from contextlib import ExitStack
from photo_animation import photo_animation_direction
from h3_prompt_writing import compile_base_prompt
import pytest


def test_animation_request_is_visual_direction_without_invented_dialogue():
    text = photo_animation_direction('Animar esta foto sem perder identidade',
        content_kind='animation', camera_pose='Static')
    prompt = compile_base_prompt(text, mode='I2VA', duration_seconds=5.125).prompt
    assert 'illustrated or animated visual style' in prompt
    assert 'camera and framing remain fixed' in prompt
    assert 'No dialogue, narration' in prompt
    assert '<d>' not in prompt


def test_explicit_dialogue_and_compiled_documents_preserved():
    text = photo_animation_direction('O personagem diz: "Olá!"',
        content_kind='animation', camera_pose='Static')
    prompt = compile_base_prompt(text, mode='I2VA', duration_seconds=5.125).prompt
    assert '<d>[Portuguese] Olá!</d>' in prompt
    assert 'Only the explicitly supplied dialogue' in prompt
    assert photo_animation_direction(prompt,content_kind='animation',camera_pose='Static') == prompt


def test_preserve_canvas_keeps_top_and_bottom_of_square_source(tmp_path):
    source = Image.new('RGB',(100,100),'white')
    for y in range(100):
        for x in range(100):
            source.putpixel((x,y),(255,0,0) if y<20 else (0,0,255) if y>=80 else (255,255,255))
    data = io.BytesIO()
    source.save(data,format='PNG')
    with patch.object(main,'COMFY_INPUT_DIR',str(tmp_path)):
        name = main._save_comfy_input_image(data.getvalue(),'source.png',(160,96),preserve_canvas=True)
    actual = Image.open(tmp_path/name)
    assert actual.size == (160,96)
    assert actual.getpixel((80,4)) == (255,0,0)
    assert actual.getpixel((80,91)) == (0,0,255)
    assert actual.getpixel((0,50)) == (0,0,0)


@pytest.mark.parametrize('conditioning', ['identity_locked','manus_motion'])
def test_real_photo_route_compiles_policy_and_preserves_full_input(tmp_path, conditioning):
    data = io.BytesIO()
    Image.new('RGB',(100,100),'red').save(data,format='PNG')
    model = main.MINIMAX_H3_MODEL_NAME
    engine = SimpleNamespace(id='minimax_h3',readiness=lambda:{'production_ready':True})
    class CapturedGraph(Exception):
        pass
    def capture(graph, **kwargs):
        prompt = graph['6']['inputs']['prompt']
        assert 'illustrated or animated visual style' in prompt
        assert 'No dialogue, narration' in prompt
        image = Image.open(tmp_path / graph['5']['inputs']['image'])
        assert image.getpixel((544,4)) == (255,0,0)
        assert image.getpixel((0,304)) == (0,0,0)
        assert 'audio' not in graph['15']['inputs']
        raise CapturedGraph()
    with ExitStack() as stack:
        for name,value in {
            '_video_generation_paused':lambda:False,
            '_resolve_video_engine':lambda *a,**kw:(engine,model),
            '_comfy_online':lambda:(True,{}),
            '_model_files':lambda *a,**kw:[model],
            '_video_model_files':lambda *a:[model],
            '_queue_comfy_workflow':capture,
        }.items():
            stack.enter_context(patch.object(main,name,value))
        stack.enter_context(patch.object(main,'COMFY_INPUT_DIR',str(tmp_path)))
        stack.enter_context(patch.object(main,'_comfy_request',side_effect=AssertionError('No network in unit test')))
        import pytest
        with pytest.raises(CapturedGraph):
            main._run_generative(prompt='Animar esta foto sem perder identidade',
                mode='video',model=model,engine_id='minimax_h3',content_kind='animation',
                negative='',lora='',lora_strength=0,width=1088,height=608,steps=10,
                guidance=1,seed=1,frames=124,fps=24,video_duration=5.125,
                base_image_bytes=data.getvalue(),base_image_name='source.png',
                camera_pose='Static',h3_quality_profile='h3_production',video_conditioning_profile=conditioning)


def test_photo_running_dialogue_reaches_real_sampler_with_single_start_frame(tmp_path):
    data=io.BytesIO(); Image.new('RGB',(100,100),'red').save(data,format='PNG')
    model=main.MINIMAX_H3_MODEL_NAME
    engine=SimpleNamespace(id='minimax_h3',readiness=lambda:{'production_ready':True})
    captured={}
    class StopBeforeGPU(Exception): pass
    def capture(graph, **kwargs):
        captured.update(graph)
        raise StopBeforeGPU()
    with ExitStack() as stack:
        for name,value in {'_video_generation_paused':lambda:False,
            '_resolve_video_engine':lambda *a,**kw:(engine,model),'_comfy_online':lambda:(True,{}),
            '_model_files':lambda *a,**kw:[model],'_video_model_files':lambda *a:[model],
            '_queue_comfy_workflow':capture}.items(): stack.enter_context(patch.object(main,name,value))
        stack.enter_context(patch.object(main,'COMFY_INPUT_DIR',str(tmp_path)))
        stack.enter_context(patch.object(main,'_comfy_request',side_effect=AssertionError('No network')))
        with pytest.raises(StopBeforeGPU):
            main._run_generative(prompt='Os três correm do fantasma. Vídeo de 15 segundos. Fala: Corre, Timão!',
                mode='video',model=model,engine_id='minimax_h3',content_kind='animation',
                negative='',lora='',lora_strength=0,width=1088,height=608,steps=10,guidance=1,
                seed=1,frames=124,fps=24,video_duration=6,enable_minimax_h3_native_audio=False,
                base_image_bytes=data.getvalue(),base_image_name='source.png',
                camera_pose='Static',h3_quality_profile='h3_production',video_conditioning_profile='manus_motion')
    inputs=captured['6']['inputs']
    assert inputs['length']==362 and 'last_frame' not in inputs
    assert 'full running strides' in inputs['prompt']
    assert '<d>[Portuguese] Corre, Timão!</d>' in inputs['prompt']
    assert 'audio' in captured['15']['inputs']
    assert any(n['class_type']=='SpectrumApplyMiniMaxH3' for n in captured.values())
    assert any(n['class_type']=='MiniMaxH3MemoryEfficientSageAttentionPatch' for n in captured.values())
