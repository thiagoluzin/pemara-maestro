"""Run AuK in its pinned Python environment without changing ComfyUI's torch."""
from pathlib import Path
import os
import subprocess
import tempfile
import time

import numpy as np
import soundfile as sf
import torch
import comfy.model_management


PYTHON = Path('D:/PemaraRuntimes/auk-py311/Scripts/python.exe')
MODELS = Path('D:/PemaraModels/workflows_20260920/auk')


class PemaraAuK:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'variant': (['Base', 'Flash'],),
            'instruction': ('STRING', {'multiline': True}),
            'seconds': ('FLOAT', {'default': 3.0, 'min': 0.1, 'max': 30.0}),
            'seed': ('INT', {'default': 42, 'min': 0, 'max': 2147483647}),
        }, 'optional': {'audio': ('AUDIO',)}}

    RETURN_TYPES = ('AUDIO',)
    FUNCTION = 'process'
    CATEGORY = 'PEMARA/Audio'
    DESCRIPTION = 'AuK local, ambiente isolado. Base: 32 passos; Flash: 4. Sem PE remoto.'

    def process(self, variant, instruction, seconds, seed, audio=None):
        if variant not in ('Base', 'Flash') or not instruction.strip():
            raise ValueError('Selecione Base/Flash e escreva uma instrução.')
        checkpoint = MODELS / ('AuK' if variant == 'Base' else 'AuK-Flash') / (
            'auk_base.safetensors' if variant == 'Base' else 'auk_flash.safetensors')
        qwen = MODELS / 'Qwen2.5-Omni-3B'
        for path in (PYTHON, checkpoint, checkpoint.parent / 'config.yaml', qwen / 'config.json'):
            if not path.is_file():
                raise FileNotFoundError(f'Implantação AuK incompleta: {path}')
        if not 0 < seconds <= 30:
            raise ValueError('A duração deve estar entre 0 e 30 segundos.')
        with tempfile.TemporaryDirectory(prefix='pemara_auk_') as directory:
            work = Path(directory)
            output = work / 'output.wav'
            command = [str(PYTHON), '-m', 'auk.infer.infer_cli', '--ckpt', str(checkpoint),
                       '--qwen_path', str(qwen), '--instruction', instruction,
                       '--gen_seconds', str(seconds), '--seed', str(seed),
                       '--device', 'cuda:0', '--cpu_offload', '--dtype', 'bf16',
                       '--nfe', '32' if variant == 'Base' else '4',
                       '--cfg', '2.0' if variant == 'Base' else '0',
                       '--sway', '-1', '--output', str(output)]
            if audio is not None:
                waveform = audio['waveform']
                rate = int(audio['sample_rate'])
                if waveform.ndim != 3 or waveform.shape[0] != 1 or rate <= 0:
                    raise ValueError('AuK aceita um áudio por execução, em [1, canais, amostras].')
                if not torch.isfinite(waveform).all() or waveform.shape[-1] == 0:
                    raise ValueError('O áudio de entrada está vazio ou contém valores inválidos.')
                if waveform.shape[-1] / rate + seconds > 30:
                    raise ValueError('Referência + saída devem caber em 30 segundos.')
                source = work / 'input.wav'
                sf.write(source, waveform[0].detach().float().cpu().numpy().T, rate, subtype='FLOAT')
                command += ['--audio', str(source)]
            # The external runtime cannot share ComfyUI's allocator.
            comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()
            env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       HF_HUB_DISABLE_TELEMETRY='1', PYTHONUTF8='1')
            with (work / 'process.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                           env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                try:
                    deadline = time.monotonic() + 1800
                    while process.poll() is None:
                        comfy.model_management.throw_exception_if_processing_interrupted()
                        if time.monotonic() > deadline:
                            raise TimeoutError('AuK excedeu 30 minutos.')
                        time.sleep(0.25)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            if process.returncode != 0:
                tail = (work / 'process.log').read_text(encoding='utf-8', errors='replace')[-4000:]
                raise RuntimeError(f'AuK falhou ({process.returncode}): {tail}')
            samples, rate = sf.read(output, dtype='float32', always_2d=True)
            if not samples.size or not np.isfinite(samples).all():
                raise ValueError('AuK produziu áudio inválido.')
            return ({'waveform': torch.from_numpy(samples.T.copy()).unsqueeze(0),
                     'sample_rate': rate},)


NODE_CLASS_MAPPINGS = {'PemaraAuK': PemaraAuK}
NODE_DISPLAY_NAME_MAPPINGS = {'PemaraAuK': 'PEMARA — AuK edição de voz (isolado)'}
