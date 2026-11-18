"""Preserved native audio, gain-only masters and QC of actual encoded deliveries."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from music_ai_audio import MusicAiAudioError, sample_metrics, loudness_metrics, qc_report, sha256_file


def finish_audio(source: Path, directory: Path, ffmpeg: str, *, cancel_event=None) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    original = sample_metrics(source)
    receipt = {'schema': 'pemara.music-delivery.v1', 'nativePath': str(source),
               'nativeSha256': sha256_file(source), 'nativeMetrics': original,
               'artisticApproval': False, 'listeningRequired': True, 'attempts': []}
    report = directory / 'music_delivery.json'
    def save():
        report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    if original['clippingSampleCount'] or original.get('nonFiniteSampleCount', 0):
        raise MusicAiAudioError('A fonte gerada atingiu o teto ou contem amostras invalidas; preservada sem ocultar o defeito.')
    loudness = loudness_metrics(source, ffmpeg)
    if original['samplePeakDbfs'] is None or loudness['truePeakDbfs'] is None:
        raise MusicAiAudioError('Fonte silenciosa ou true peak indisponivel.')
    duration = float(original['durationSeconds'])
    gain = min(0.0, -2.0 - max(original['samplePeakDbfs'], loudness['truePeakDbfs']))
    for attempt in range(3):
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('Masterizacao musical cancelada; fontes preservadas.')
        master = directory / f'master_{attempt + 1}.wav'
        preview = directory / f'preview_{attempt + 1}.mp3'
        commands = [
            [ffmpeg, '-nostdin', '-hide_banner', '-v', 'error', '-i', str(source),
             '-af', f'volume={gain:.4f}dB', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(master)],
            [ffmpeg, '-nostdin', '-hide_banner', '-v', 'error', '-i', str(master),
             '-c:a', 'libmp3lame', '-b:a', '320k', str(preview)]]
        for command in commands:
            completed = subprocess.run(command, capture_output=True, timeout=max(300, duration * 3))
            if completed.returncode:
                raise MusicAiAudioError('A exportacao musical falhou; fonte e tentativas foram preservadas.')
        master_qc, preview_qc = qc_report(master, ffmpeg, duration), qc_report(preview, ffmpeg, duration)
        item = {'gainDb': gain, 'master': str(master), 'preview': str(preview),
                'masterQc': master_qc, 'previewQc': preview_qc}
        receipt['attempts'].append(item)
        receipt['technicalPass'] = bool(master_qc['technicalPass'] and preview_qc['technicalPass'])
        if receipt['technicalPass']:
            receipt.update({'masterSha256': sha256_file(master), 'previewSha256': sha256_file(preview)})
            save()
            return {**receipt, 'master': master, 'preview': preview, 'report': report}
        save()
        peaks = [q.get('truePeakDbfs') for q in (master_qc, preview_qc)]
        if any(peak is None for peak in peaks):
            break
        gain -= max(.5, max(peaks) + 1.5)
    raise MusicAiAudioError('O master/MP3 falhou no QC; candidatos e recibos preservados.')
