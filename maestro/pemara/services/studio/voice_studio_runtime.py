"""Executed by the existing isolated Drama 3 Python, only from the ComfyUI node."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import wave


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, data):
    path = Path(path)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    # Windows readers/antivirus may briefly hold the previous JSON without
    # delete sharing. Keep atomic publication, but allow that handle to close.
    for attempt in range(40):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(min(.025 * (attempt + 1), .15))


def execution_placement(job):
    """Private per-attempt placement; never changes model or sampling settings."""
    path = Path(job) / 'execution-placement.json'
    if not path.exists():
        return 32, None
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data) != {'schema', 'jobId', 'gpuExpertLayers'} or data['schema'] != 'pemara-drama3-placement-v1' or data['jobId'] != Path(job).name:
        raise ValueError('Configuração de execução incompatível com a tentativa.')
    value = data['gpuExpertLayers']
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 32:
        raise ValueError('A execução requer de zero a 32 camadas de experts na GPU.')
    return value, sha(path)


def main():
    job = Path(sys.argv[1]).resolve()
    source = Path(os.environ.get('PEMARA_DRAMA3_SOURCE', 'E:/a terra rejeita/Ferramentas/Drama3/source'))
    models = Path(os.environ.get('PEMARA_DRAMA3_MODELS', 'G:/Pemara_AI_Models/Drama3/Eng-Ahmd_57d3598'))
    sys.path.insert(0, str(source))
    from fish_drama3.web_service import Studio
    from fish_drama3.web_planning import generation_plan
    from fish_drama3.web_config import generation_options
    request_path = job / 'request.json'
    request_sha = sha(request_path)
    request = json.loads(request_path.read_text(encoding='utf-8'))
    settings, reference = request['settings'], request.get('reference')
    gpu_expert_layers, placement_sha = execution_placement(job)
    if request['schema'] != 'pemara-voice-studio-v1' or request['id'] != job.name:
        raise ValueError('Receita de voz incompatível.')
    if reference and (reference.get('authorized') is not True or sha(job / 'reference.wav') != reference['sha256']):
        raise ValueError('Referência sem autorização ou com integridade alterada.')
    options = dict(text=settings['text'], seed=settings['seed'], temperature=settings['temperature'],
                   top_p=settings['topP'], top_k=settings['topK'], max_frames=settings['maxFrames'],
                   chunk_length=settings['chunkLength'], generation_mode=settings['mode'],
                   allow_partial=False, output_format='wav', reference_text=reference['transcript'] if reference else '')
    options = generation_options(options, False)
    plan = generation_plan(options)
    # Enforce the runtime's budget gate rather than acknowledging it silently.
    if plan['risk'] == 'high':
        raise ValueError('O texto excede o orçamento seguro de áudio. Aumente o limite de duração ou use trechos com continuidade e divida a narração.')
    # This isolated worker produces exactly one result. Separate reference
    # encoding, semantic generation and waveform decoding to avoid retaining
    # their peak allocations together. The native memory monitor stays active.
    os.environ['FISH_DRAMA3_ONESHOT_MEMORY_BOUNDED'] = '1'
    os.environ['FISH_DRAMA3_ONESHOT_CHECKPOINT_PATH'] = str(job / 'native' / 'acoustic-frames.npz')
    for key in ('FISH_DRAMA3_ONESHOT_REFERENCE_AUDIO',
                'FISH_DRAMA3_ONESHOT_REFERENCE_TEXT'):
        os.environ.pop(key, None)
    if reference:
        os.environ['FISH_DRAMA3_ONESHOT_REFERENCE_AUDIO'] = str(job / 'reference.wav')
        os.environ['FISH_DRAMA3_ONESHOT_REFERENCE_TEXT'] = reference['transcript']
    studio = Studio(job / 'native')
    deadline = time.monotonic() + 3600

    def ready():
        while time.monotonic() < deadline:
            if (job / 'cancel.flag').exists():
                raise InterruptedError('Narração cancelada pelo operador.')
            state = studio.snapshot()
            try:
                save(job / 'progress.json', {'status': state['status'], 'phase': state.get('phase'),
                     'progress': state.get('progress'), 'startedAt': state.get('started_at'), 'updatedAt': time.time()})
            except PermissionError:
                # Progress is observational. A reader must not abort synthesis;
                # the next snapshot can update it after the file is released.
                pass
            if state['status'] == 'error' or state.get('error'):
                raise RuntimeError(str(state.get('error') or state.get('message')))
            if state['status'] == 'ready':
                return state
            time.sleep(1)
        raise TimeoutError('A narração excedeu a janela de uma hora. A tentativa foi preservada.')

    try:
        studio.load(dict(bundle=str(models / 'model'), codec=str(models / 'codec/codec.gguf'),
                         threads=8, placement_mode='manual', gpu_expert_layers=gpu_expert_layers, headroom_percent=5))
        ready()
        if reference:
            studio.references['maestro-reference'] = job / 'reference.wav'
            options['reference_id'] = 'maestro-reference'
        studio.generate(options)
        result = ready()['result']
        metrics = result['metrics']
        if not metrics.get('complete') or metrics.get('finish_reason') != 'eos':
            raise ValueError('O Drama 3 não concluiu a leitura; o áudio parcial permanece preservado para diagnóstico.')
        wav = studio.exports[result['wav_url']]
        shutil.copy2(wav, job / 'speech.wav')
        with wave.open(str(job / 'speech.wav')) as audio:
            duration = audio.getnframes() / audio.getframerate()
            rate = audio.getframerate()
        receipt = dict(schema='pemara-voice-result-v1', engine='Drama 3 local', networkGeneration=False,
                       requestSha256=request_sha, wavSha256=sha(job / 'speech.wav'), metrics=metrics,
                       duration=duration, sampleRate=rate, createdAt=time.time(),
                       referenceSha256=reference['sha256'] if reference else None, artisticApproval='pending')
        if placement_sha:
            if sha(job / 'execution-placement.json') != placement_sha:
                raise ValueError('A configuração de execução mudou durante a narração.')
            receipt['executionPlacementSha256'] = placement_sha
            receipt['gpuExpertLayers'] = gpu_expert_layers
        encoder = shutil.which('ffmpeg')
        if encoder:
            try:
                subprocess.run([encoder, '-nostdin', '-v', 'error', '-n', '-i', str(job / 'speech.wav'),
                                '-codec:a', 'libmp3lame', '-b:a', '192k', str(job / 'speech.mp3')],
                               capture_output=True, check=True, timeout=120,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                receipt['mp3Sha256'] = sha(job / 'speech.mp3')
            except (OSError, subprocess.SubprocessError):
                receipt['exportNote'] = 'A exportação MP3 falhou; o WAV original está disponível.'
        save(job / 'result.json', receipt)
        print(json.dumps(receipt), flush=True)
    finally:
        studio.shutdown()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        save(Path(sys.argv[1]) / 'error.json', {'message': str(error)[:1500], 'cancelled': isinstance(error, InterruptedError), 'createdAt': time.time()})
        raise
