"""Seed-VC conversion node; separate from the preserved Drama 3 narration node."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import soundfile as sf
import torch

ROOT = Path('E:/Pemara/maestro/pemara/dados/studio/voice_studio/conversion/jobs').resolve()
WORKER = Path('E:/Pemara/maestro/pemara/services/studio/voice_conversion_runtime.py')


class PemaraVoiceConvert:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'job_id': ('STRING', {'default': ''})}}

    RETURN_TYPES = ('AUDIO', 'STRING')
    RETURN_NAMES = ('audio', 'receipt')
    FUNCTION = 'convert'
    CATEGORY = 'PEMARA/audio/local'
    OUTPUT_NODE = True
    DESCRIPTION = 'Troca de voz local Seed-VC a partir da gravação original, sem nova leitura de texto.'

    def convert(self, job_id):
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise ValueError('Identificador de conversão inválido.')
        folder = (ROOT / job_id).resolve()
        if folder.parent != ROOT or not (folder / 'request.json').is_file():
            raise ValueError('Pedido de conversão não encontrado.')
        if (folder / 'result.json').exists() or (folder / 'cancel.flag').exists():
            raise ValueError('Esta tentativa já terminou ou foi cancelada. Crie uma nova versão.')
        import comfy.model_management
        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        environment = os.environ.copy()
        environment['PYTHONUTF8'] = '1'
        environment['HF_HUB_OFFLINE'] = '1'
        environment['PATH'] = 'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3/bin;' + environment.get('PATH', '')
        with (folder / 'worker.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, '-u', str(WORKER), str(folder)], cwd=WORKER.parent,
                                       env=environment, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                deadline = time.monotonic() + 3750
                while process.poll() is None:
                    comfy.model_management.throw_exception_if_processing_interrupted()
                    if time.monotonic() > deadline: raise TimeoutError('Tempo da conversão excedido.')
                    time.sleep(1)
            except BaseException:
                (folder / 'cancel.flag').touch()
                try: process.wait(timeout=30)
                except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=15)
                raise
        if process.returncode:
            error = json.loads((folder / 'error.json').read_text(encoding='utf-8')) if (folder / 'error.json').exists() else {}
            raise RuntimeError(error.get('message', 'O conversor local não concluiu. Consulte o registro da tentativa.'))
        receipt = (folder / 'result.json').read_text(encoding='utf-8')
        samples, rate = sf.read(folder / 'speech.wav', dtype='float32', always_2d=True)
        audio = {'waveform': torch.from_numpy(samples.T.copy()).unsqueeze(0), 'sample_rate': int(rate)}
        return {'ui': {'text': [receipt]}, 'result': (audio, receipt)}
