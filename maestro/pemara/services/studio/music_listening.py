"""Gain-only, level-matched stereo listening copies; originals remain immutable."""
from pathlib import Path
import json
import math
import subprocess
from music_ai_audio import loudness_metrics, sample_metrics, sha256_file, qc_report


def prepare_comparison(source: Path, candidate: Path, directory: Path, ffmpeg: str) -> dict:
    paths = {'reference': source, 'candidate': candidate}
    measures = {name: {**sample_metrics(path), **loudness_metrics(path, ffmpeg)} for name, path in paths.items()}
    for values in measures.values():
        if any(values[key] is None or not math.isfinite(values[key]) for key in ('integratedLufs', 'truePeakDbfs')):
            raise ValueError('Comparacao sem loudness/true peak validos.')
    # Choose a common level requiring attenuation only and leave codec headroom.
    target = min(-20, *(v['integratedLufs'] for v in measures.values()),
                 *(v['integratedLufs'] - v['truePeakDbfs'] - 2 for v in measures.values()))
    directory.mkdir(parents=True, exist_ok=False)
    receipt = {'targetLufs': target, 'method': 'measured_gain_only_stereo',
               'nativeMetrics': measures,
               'artisticApproval': False, 'listeningRequired': True, 'files': {}}
    for name, path in paths.items():
        before = sha256_file(path)
        gain = target - measures[name]['integratedLufs']
        output = directory / f'{name}_listening.wav'
        run = subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-i', str(path), '-af', f'volume={gain:.6f}dB',
            '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(output)], capture_output=True, text=True, timeout=600)
        if run.returncode: raise ValueError('Falha na copia de escuta; fontes preservadas.')
        qc = qc_report(output, ffmpeg, measures[name]['durationSeconds'])
        if not qc['technicalPass'] or abs(qc['integratedLufs'] - target) > .4:
            raise ValueError('Comparacao nao conseguiu igualar volume e headroom; fontes preservadas.')
        if sha256_file(path) != before: raise ValueError('A fonte mudou durante a comparacao.')
        receipt['files'][name] = {'path': str(output), 'sourceSha256': before, 'sha256': sha256_file(output),
                                 'gainDb': gain, 'qc': qc}
    report = directory / 'listening_comparison.json'
    report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'report': report, 'reference': directory / 'reference_listening.wav',
            'candidate': directory / 'candidate_listening.wav', 'receipt': receipt}
