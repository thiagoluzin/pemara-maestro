import asyncio
from types import SimpleNamespace
from unittest.mock import patch
import pytest
import main
from video_request import resolve_video_request
from photo_animation import photo_animation_direction
from h3_prompt_writing import compile_base_prompt, normalize_quoted_speech


def test_owner_mirassol_request_without_colon():
    text = 'Sem modificar a foto em nada coloque o leão do mirassol, jogador do mirassol e o fantasma da serie B correndo atras dos torcedores e do mascote do corinthias com a frase Arere o Corinthias vai jogar a Serie B, Arere o Corinthias vai jogar a Serie B'
    plan = resolve_video_request(text)
    assert plan['dialogue'] == ['Arere o Corinthias vai jogar a Serie B, Arere o Corinthias vai jogar a Serie B']
    assert plan['native_audio'] and plan['motion'] == 'run'
    wrapped = photo_animation_direction(text, content_kind='animation', camera_pose='Static')
    assert 'All subjects are silent' not in wrapped
    assert resolve_video_request(plan['prompt'])['prompt'] == plan['prompt']


@pytest.mark.parametrize('sign', ['"SÉRIE B"', '<d>[Portuguese] SÉRIE B</d>'])
@pytest.mark.parametrize('chant', ['"Arerê, o Corinthians vai jogar a Série B!"', 'Arerê, o Corinthians vai jogar a Série B!', '<d>[Portuguese] Arerê, o Corinthians vai jogar a Série B!</d>'])
def test_structured_sections_survive_preview_wrapper_and_compiler(sign, chant):
    text = f'[VISUAL INSTRUCTIONS — DO NOT SPEAK]\nPreserve the {sign} sign. Camera tracks backward smoothly. The characters run.\n[AUDIO — SPOKEN/SUNG WORDS ONLY]\n{chant}\n[AUDIO INSTRUCTIONS — DO NOT SPEAK]\nThe lion leads the chant. No narration. Preserve the "comic book" style.'
    plan = resolve_video_request(text, camera_pose='Static')
    assert plan['dialogue'] == ['Arerê, o Corinthians vai jogar a Série B!']
    assert plan['camera_pose'] == 'Follow Action'
    assert normalize_quoted_speech(plan['prompt']) == plan['prompt']
    wrapped = photo_animation_direction(plan['prompt'], content_kind='animation', camera_pose=plan['camera_pose'])
    compiled = compile_base_prompt(wrapped, mode='I2VA', duration_seconds=10).prompt
    assert compiled.count('<d>') == 1
    assert 'camera and framing remain fixed' not in compiled
    assert 'The lion leads the chant' in compiled
    assert 'The characters run' in compiled


def test_plain_quote_rule_still_preserves_multiple_speakers():
    p = resolve_video_request('João diz "Olá!" Maria responde "Vamos!"')
    assert p['dialogue'] == ['Olá!', 'Vamos!']


def test_visual_section_cannot_become_narration_by_speech_label():
    plan = resolve_video_request('[VISUAL INSTRUCTIONS — DO NOT SPEAK]\nA placa tem a mensagem: Arerê.\n[AUDIO INSTRUCTIONS — DO NOT SPEAK]\nSom ambiente.')
    assert plan['dialogue'] == []


@pytest.mark.parametrize('separator', [' ', ': ', ':'])
def test_natural_phrase_separator(separator):
    assert resolve_video_request('Eles correm com a frase' + separator + 'Arerê!')['dialogue'] == ['Arerê!']


@pytest.mark.parametrize('text',[
 'Os três correm. Vídeo de 15 segundos. Fala: Corre, Timão! Corre, Timão! Que o fantasma da Série B tá atrás de vocês!',
 'Os três correm. Vídeo de quinze segundos. Ele diz: "Corre, Timão! Corre, Timão! Que o fantasma da Série B tá atrás de vocês!"',
 'Os três correm falando a mensagem: Corre, Timão! Corre, Timão! Que o fantasma da Série B tá atrás de vocês! Pode fazer um vídeo de 15 segundos único.',
])
def test_actual_request_separates_literal_speech_and_duration(text):
    plan=resolve_video_request(text,duration=6,native_audio=False)
    assert plan['duration_seconds']==15
    assert plan['native_audio'] is True
    assert plan['motion']=='run'
    assert plan['dialogue']==['Corre, Timão! Corre, Timão! Que o fantasma da Série B tá atrás de vocês!']
    again=resolve_video_request(plan['prompt'],duration=plan['duration_seconds'],native_audio=plan['native_audio'])
    assert again['prompt']==plan['prompt']
    assert again['dialogue']==plan['dialogue']


def test_silent_photo_never_becomes_narration():
    p=resolve_video_request('Animar esta foto sem perder identidade',duration=10)
    assert p['native_audio'] is False and p['dialogue']==[]
    assert p['duration_seconds']==10


def test_no_narration_allows_dialogue_and_no_speech_allows_ambience():
    assert resolve_video_request('Ele diz: "Olá!" Sem narração.')['native_audio'] is True
    p=resolve_video_request('A chuva cai com som ambiente, sem fala.')
    assert p['native_audio'] is True and p['dialogue']==[]
    assert resolve_video_request('A chuva cai, sem áudio.',native_audio=True)['native_audio'] is False


def test_dialogue_words_not_misread_as_action_or_duration():
    p=resolve_video_request('Ele permanece parado e diz: "Corre, Timão! Vídeo de 15 segundos!"',duration=6)
    assert p['motion']=='requested' and p['duration_seconds']==6


@pytest.mark.parametrize('prompt', ['Não correr. Fique sentado.', 'Sem caminhar, apenas sorria.'])
def test_negated_locomotion_not_added(prompt):
    assert resolve_video_request(prompt)['motion']=='requested'


def test_camera_instruction_overrides_default():
    assert resolve_video_request('A câmera acompanha os três correndo',camera_pose='Static')['camera_pose']=='Follow Action'
    assert resolve_video_request('Câmera fixa, os três correm',camera_pose='Zoom Out')['camera_pose']=='Static'


@pytest.mark.parametrize('prompt,variant',[
 ('Sem áudio. Fala: Olá!','base'),
 ('Ele vai dizendo alguma coisa','base'),
])
def test_conflicts_reported_before_generation(prompt,variant):
    with pytest.raises(ValueError): resolve_video_request(prompt,model_variant=variant)


def test_preserves_native_audio_capability_in_existing_fast_variants():
    assert resolve_video_request('Uma rua',native_audio=True,model_variant='fasth3_8step_v2')['native_audio'] is True


def test_visible_run_does_not_freeze_faces_poses_or_frame():
    p=photo_animation_direction('Os três correm do fantasma. Fala: Corre, Timão!',content_kind='animation',camera_pose='Static')
    assert 'full running strides' in p and 'Keep running during dialogue' in p
    assert 'small amplitude' not in p and 'exact face, expression' not in p
    assert '<d>[Portuguese] Corre, Timão!</d>' in p


def test_endpoint_uses_same_resolution_and_has_no_gpu_calls():
    class Request:
        async def json(self):
            return {'prompt':'Os três correm. Vídeo de 15 segundos. Fala: Corre, Timão!', 'video_duration':6}
    with patch.object(main,'_is_internal_request',return_value=True), patch.object(main,'_comfy_request',side_effect=AssertionError('GPU call')):
        result=asyncio.run(main.generative_video_request_preview(Request()))
    assert result['plan']['frames']==362
    assert result['plan']['native_audio'] is True


def test_job_normalizer_carries_the_plan_to_worker():
    engine=SimpleNamespace(id='minimax_h3')
    with patch.object(main,'_resolve_video_engine',return_value=(engine,main.MINIMAX_H3_MODEL_NAME)):
        spec=main._normalize_generative_job_spec({'mode':'video','engine_id':'minimax_h3','model':main.MINIMAX_H3_MODEL_NAME,
          'prompt':'Os três correm. Vídeo de 15 segundos. Fala: Corre, Timão!','video_duration':6,
          'h3_quality_profile':'h3_production','h3_model_variant':'base','content_kind':'animation','fps':24,
          'enable_minimax_h3_native_audio':False})
    assert spec['frames']==362
    assert spec['enable_minimax_h3_native_audio'] is True
    assert '<d>[Portuguese] Corre, Timão!</d>' in spec['prompt']
