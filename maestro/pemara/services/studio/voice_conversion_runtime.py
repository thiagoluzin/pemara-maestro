"""Local speech-to-speech, retaining source time rather than resynthesizing text.

Called only by the ComfyUI conversion node. Original media, separation stems,
native conversions and the sample-exact delivery remain distinct immutable files.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

from voice_conversion_contract import ENGINE, CLI, MODEL, MODEL_SHA, SEPARATOR, SEPARATOR_SHA, ROUTE
from voice_conversion_media import RATE, extract_timeline
from voice_studio_runtime import sha, save

CHUNK_SECONDS = 20
OVERLAP_SECONDS = 1
MAX_NATIVE_DRIFT_SECONDS = .08


def mono(data):
    return data.mean(axis=1) if data.ndim == 2 else data


def exact_length(data, wanted, *, tolerance=MAX_NATIVE_DRIFT_SECONDS, rate=RATE):
    """Permit only codec-hop rounding; never stretch speech to hide time drift."""
    if not np.isfinite(data).all():
        raise ValueError('O conversor retornou amostras de áudio inválidas.')
    difference = len(data) - wanted
    if abs(difference) > round(tolerance * rate):
        raise ValueError('O conversor alterou a duração além da tolerância. A saída nativa foi preservada; não houve aceleração ou corte da fala.')
    if difference > 0:
        tail = data[wanted:]
        if np.max(np.abs(tail), initial=0) > .015:
            raise ValueError('O áudio convertido possui fala além do final da fonte. A entrega foi bloqueada para evitar cortar fonemas.')
        return data[:wanted]
    if difference < 0:
        return np.pad(data, ((0, -difference), (0, 0)) if data.ndim == 2 else (0, -difference))
    return data


def windows(count, rate=RATE):
    maximum, overlap = CHUNK_SECONDS * rate, OVERLAP_SECONDS * rate
    start = 0
    while start < count:
        end = min(count, start + maximum)
        yield start, end
        if end == count:
            break
        start = end - overlap


def stitch(parts, spans, count, rate=RATE):
    output = np.zeros(count, np.float64)
    weights = np.zeros(count, np.float64)
    for index, (part, (start, end)) in enumerate(zip(parts, spans)):
        if len(part) != end - start:
            raise ValueError('Trecho convertido fora da sua janela original.')
        gain = np.ones(len(part), np.float64)
        if index:
            overlap = max(0, spans[index - 1][1] - start)
            gain[:overlap] = np.linspace(0, 1, overlap, endpoint=False)
        if index + 1 < len(spans):
            overlap = max(0, end - spans[index + 1][0])
            gain[-overlap:] = np.linspace(1, 0, overlap, endpoint=False) if overlap else gain[-overlap:]
        output[start:end] += part * gain
        weights[start:end] += gain
    if np.any(weights <= 0):
        raise ValueError('A montagem deixou lacunas na linha do tempo.')
    return output / weights


def main(job):
    job = Path(job).resolve()
    request = json.loads((job / 'request.json').read_text(encoding='utf-8'))
    request_hash = sha(job / 'request.json')
    if request['schema'] != 'pemara-voice-conversion-v1' or request['id'] != job.name:
        raise ValueError('Receita de conversão incompatível.')
    source = request['source']; reference = request['reference']; settings = request['settings']
    if Path(source['file']).name != source['file']:
        raise ValueError('Nome de fonte inválido.')
    source_path = job.parent.parent / 'media' / settings['mediaId'] / source['file']
    if sha(source_path) != source['sha256'] or sha(job / 'reference.wav') != reference['sha256'] or reference.get('authorized') is not True:
        raise ValueError('Fonte ou referência alterada, ou autorização ausente.')
    started = time.time()

    def progress(phase, **values):
        if (job / 'cancel.flag').exists():
            raise InterruptedError('Conversão cancelada pelo operador.')
        try:
            save(job / 'progress.json', {'status': 'generating', 'phase': phase, 'progress': values,
                                        'startedAt': started, 'updatedAt': time.time()})
        except PermissionError:
            pass  # Observational progress must not abort native conversion.

    def execute(command, name, phase, **values):
        progress(phase, **values)
        with (job / (name + '.log')).open('ab') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                while process.poll() is None:
                    if time.time() - started > 3600:
                        raise TimeoutError('A conversão excedeu uma hora. Os arquivos foram preservados.')
                    progress(phase, **values)
                    time.sleep(1)
            except BaseException:
                process.terminate()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=10)
                raise
        if process.returncode:
            raise RuntimeError(f'O motor local não concluiu a etapa {phase}. O registro {name}.log foi preservado para diagnóstico.')

    progress('verifying')
    if sha(MODEL) != MODEL_SHA:
        raise ValueError('Os pesos Seed-VC diferem da instalação fixada. Conversão bloqueada.')
    if settings['preserveBackground'] and sha(SEPARATOR) != SEPARATOR_SHA:
        raise ValueError('O separador de voz difere da instalação fixada.')
    original = job / 'original_timeline.wav'
    progress('extracting')
    extract_timeline(source_path, original, source, settings['audioTrack'])
    original_data, rate = sf.read(original, dtype='float32', always_2d=True)
    if rate != RATE or len(original_data) != source['samples']:
        raise ValueError('Linha do tempo extraída inválida.')
    source_voice = mono(original_data)
    background = np.zeros_like(original_data)
    stems = job / 'stems'
    if settings['preserveBackground']:
        stems.mkdir(exist_ok=True)
        execute([str(CLI), '--task', 'sep', '--family', 'htdemucs', '--model', str(SEPARATOR), '--backend', 'cuda',
                 '--threads', '8', '--audio', str(original), '--out-dir', str(stems), '--log'], 'separation', 'separating')
        vocals = [path for path in stems.glob('*.wav') if 'vocals' in path.stem.lower()]
        if len(vocals) != 1:
            raise ValueError('O separador não retornou uma faixa vocal identificável.')
        isolated, isolated_rate = sf.read(vocals[0], dtype='float32', always_2d=True)
        if isolated_rate != RATE:
            raise ValueError('O separador retornou uma taxa de áudio incompatível.')
        isolated = exact_length(isolated, len(original_data))
        if isolated.shape[1] == 1:
            isolated = np.repeat(isolated, 2, axis=1)
        background = original_data - isolated
        source_voice = mono(isolated)
    sf.write(job / 'source_voice.wav', source_voice, RATE, subtype='PCM_16')
    spans = list(windows(len(source_voice)))
    parts, timing = [], []
    encoder = shutil.which('ffmpeg')
    if not encoder:
        raise ValueError('FFmpeg local indisponível.')
    for index, (start, end) in enumerate(spans):
        raw = job / f'source_{index:03d}.wav'
        native = job / f'converted_native_{index:03d}.wav'
        prepared = job / f'converted_44100_{index:03d}.wav'
        clip = source_voice[start:end]
        sf.write(raw, clip, RATE, subtype='PCM_16')
        if float(np.max(np.abs(clip), initial=0)) < .0001:
            parts.append(np.zeros(end - start, dtype='float32'))
            timing.append({'startSample': start, 'endSample': end, 'silent': True})
            continue
        execute([str(CLI), '--task', 'vc', '--family', 'seed_vc', '--model', str(MODEL), '--backend', 'cuda',
                 '--threads', '8', '--task-route', ROUTE, '--audio', str(raw), '--voice-ref', str(job / 'reference.wav'),
                 '--seed', str(settings['seed']), '--num-inference-steps', '30', '--request-option', 'duration_scale=1.0',
                 '--out', str(native), '--log'], f'conversion_{index:03d}', 'converting', segment_index=index + 1, segment_count=len(spans))
        execute([encoder, '-nostdin', '-v', 'error', '-n', '-i', str(native), '-ac', '1', '-ar', str(RATE),
                 '-c:a', 'pcm_s16le', str(prepared)], f'resample_{index:03d}', 'assembling')
        converted, native_rate = sf.read(prepared, dtype='float32')
        difference = len(converted) - (end - start)
        parts.append(exact_length(converted, end - start))
        timing.append({'startSample': start, 'endSample': end, 'nativeSamplesAt44100': len(converted),
                       'roundingCorrectionSamples': difference, 'timeStretch': False, 'nativeSha256': sha(native)})
    progress('assembling')
    converted_voice = stitch(parts, spans, len(source_voice))
    # Silence belongs to the source timeline. Suppress codec hiss in genuinely
    # silent source windows without shifting any samples or cropping speech.
    window = RATE // 50
    envelope = np.ones(len(source_voice), dtype='float32')
    for start in range(0, len(source_voice), window):
        end = min(len(source_voice), start + window)
        if np.max(np.abs(source_voice[start:end]), initial=0) < .0001:
            envelope[start:end] = 0
    converted_voice *= envelope
    sf.write(job / 'converted_voice.wav', converted_voice, RATE, subtype='PCM_16')
    mixed = background + converted_voice[:, None]
    peak = float(np.max(np.abs(mixed), initial=0))
    gain = min(1., .98 / max(peak, 1e-12))
    mixed *= gain
    sf.write(job / 'speech.wav', mixed, RATE, subtype='PCM_16')
    progress('validating')
    delivered = sf.info(job / 'speech.wav')
    if delivered.frames != source['samples'] or delivered.samplerate != RATE:
        raise ValueError('A saída não manteve o tempo exato da fonte.')
    receipt = {'schema': 'pemara-voice-conversion-result-v1', 'engine': ENGINE, 'route': ROUTE, 'networkGeneration': False,
               'requestSha256': request_hash, 'sourceSha256': source['sha256'], 'referenceSha256': reference['sha256'],
               'modelSha256': MODEL_SHA, 'wavSha256': sha(job / 'speech.wav'), 'originalTimelineSha256': sha(original), 'duration': delivered.duration,
               'sampleRate': RATE, 'sourceSamples': source['samples'], 'outputSamples': delivered.frames,
               'preservedBackground': settings['preserveBackground'], 'mixGain': gain, 'segments': timing,
               'timeStretch': False, 'metrics': {'complete': True, 'finish_reason': 'converted'},
               'createdAt': time.time(), 'artisticApproval': 'pending', 'synthesisSeconds': time.time() - started}
    execute([encoder, '-nostdin', '-v', 'error', '-n', '-i', str(job / 'speech.wav'), '-codec:a', 'libmp3lame',
             '-b:a', '192k', str(job / 'speech.mp3')], 'mp3_export', 'exporting')
    receipt['mp3Sha256'] = sha(job / 'speech.mp3')
    save(job / 'result.json', receipt)


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except Exception as error:
        save(Path(sys.argv[1]) / 'error.json', {'message': str(error)[:1200], 'cancelled': isinstance(error, InterruptedError), 'createdAt': time.time()})
        raise
