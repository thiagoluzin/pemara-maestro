"""General Maestro bridge. The historical campaign node is left untouched."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import soundfile as sf
import torch

ROOT = Path('E:/Pemara/maestro/pemara/dados/studio/voice_studio/jobs').resolve()
WORKER = Path('E:/Pemara/maestro/pemara/services/studio/voice_studio_runtime.py')
SOURCE = Path(os.environ.get('PEMARA_DRAMA3_SOURCE', 'E:/a terra rejeita/Ferramentas/Drama3/source'))


class PemaraDrama3Studio:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'job_id': ('STRING', {'default': '', 'multiline': False})}}

    RETURN_TYPES = ('AUDIO', 'STRING')
    RETURN_NAMES = ('audio', 'receipt')
    FUNCTION = 'generate'
    CATEGORY = 'PEMARA/audio/local'
    OUTPUT_NODE = True
    DESCRIPTION = 'Narração e clonagem locais com receita persistida no Maestro; sem API externa.'

    def generate(self, job_id):
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise ValueError('Identificador de narração inválido.')
        job = (ROOT / job_id).resolve()
        if job.parent != ROOT or not (job / 'request.json').is_file():
            raise ValueError('Receita não encontrada no estúdio de voz.')
        if (job / 'result.json').exists():
            raise ValueError('Esta tentativa já possui áudio. Crie uma nova versão no Maestro.')
        if (job / 'cancel.flag').exists():
            raise ValueError('Esta tentativa foi cancelada.')
        # Executed serially inside ComfyUI, after earlier prompts have finished.
        # Drop cached models before starting the isolated speech runtime.
        import comfy.model_management
        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        environment = os.environ.copy()
        environment['PYTHONUTF8'] = '1'
        environment['PATH'] = 'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3/bin;' + environment.get('PATH', '')
        with (job / 'worker.log').open('a', encoding='utf-8') as log:
            process = subprocess.Popen([str(SOURCE / '.venv/Scripts/python.exe'), '-u', str(WORKER), str(job)],
                                       cwd=SOURCE, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 3750
            try:
                while process.poll() is None:
                    import comfy.model_management
                    comfy.model_management.throw_exception_if_processing_interrupted()
                    if time.monotonic() > deadline:
                        raise TimeoutError('Tempo de execução do estúdio excedido.')
                    time.sleep(1)
            except BaseException:
                (job / 'cancel.flag').touch()
                try:
                    process.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    process.terminate(); process.wait(timeout=15)
                raise
        if process.returncode:
            error = json.loads((job / 'error.json').read_text(encoding='utf-8')) if (job / 'error.json').exists() else {}
            raise RuntimeError(error.get('message', 'Drama 3 falhou; consulte o registro protegido da tentativa.'))
        receipt = json.loads((job / 'result.json').read_text(encoding='utf-8'))
        with (job / 'speech.wav').open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != receipt['wavSha256']:
                raise RuntimeError('Integridade da narração alterada.')
        samples, rate = sf.read(job / 'speech.wav', dtype='float32', always_2d=True)
        audio = {'waveform': torch.from_numpy(samples.T.copy()).unsqueeze(0), 'sample_rate': int(rate)}
        encoded = json.dumps(receipt, ensure_ascii=False)
        return {'ui': {'text': [encoded]}, 'result': (audio, encoded)}


NODE_CLASS_MAPPINGS = {'PemaraDrama3Studio': PemaraDrama3Studio}
NODE_DISPLAY_NAME_MAPPINGS = {'PemaraDrama3Studio': 'PEMARA Estúdio de Voz · Drama 3 local'}
from .conversion import PemaraVoiceConvert
NODE_CLASS_MAPPINGS['PemaraVoiceConvert'] = PemaraVoiceConvert
NODE_DISPLAY_NAME_MAPPINGS['PemaraVoiceConvert'] = 'PEMARA Trocar Voz de Vídeo · Seed-VC local'
