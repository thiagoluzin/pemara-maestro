"""Local media import and exact source-timeline preparation for voice conversion."""
from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

RATE = 44100
MAX_SECONDS = 300
MAX_UPLOAD = 1024 * 1024 * 1024
SUFFIXES = {'.mp4', '.mov', '.mkv', '.webm', '.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.opus'}


def run(command, *, timeout=120):
    return subprocess.run(command, check=True, capture_output=True, timeout=timeout,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def probe(path):
    executable = shutil.which('ffprobe')
    if not executable:
        raise ValueError('FFprobe local indisponível.')
    try:
        data = json.loads(run([executable, '-v', 'error', '-show_entries',
            'format=duration,start_time:stream=index,codec_type,codec_name,duration,start_time,channels:stream_tags=language,title',
            '-of', 'json', str(path)], timeout=30).stdout)
        streams = data.get('streams', [])
        audios = [stream for stream in streams if stream['codec_type'] == 'audio']
        video = next((stream for stream in streams if stream['codec_type'] == 'video'), None)
        format_info = data.get('format', {})
        # Video's own timeline wins over a longer/offset audio stream.
        duration = float((video or {}).get('duration') or format_info.get('duration') or 'nan')
        origin = float((video or {}).get('start_time') or format_info.get('start_time') or 0)
    except (ValueError, KeyError, subprocess.SubprocessError, OSError) as error:
        raise ValueError('Não foi possível ler este vídeo ou áudio.') from error
    if not audios:
        raise ValueError('Este arquivo não possui faixa de áudio.')
    if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS or not math.isfinite(origin):
        raise ValueError('Use um vídeo ou áudio de até 5 minutos, com duração válida.')
    tracks = []
    for stream in audios:
        start = float(stream.get('start_time') or 0)
        if not math.isfinite(start) or abs(start - origin) > MAX_SECONDS:
            raise ValueError('A faixa de áudio possui marcação temporal incompatível.')
        tracks.append({'index': stream['index'], 'codec': stream.get('codec_name'),
                       'channels': stream.get('channels'), 'language': stream.get('tags', {}).get('language', ''),
                       'title': stream.get('tags', {}).get('title', ''), 'offsetSeconds': start - origin})
    return {'duration': duration, 'samples': round(duration * RATE), 'sampleRate': RATE, 'timelineOrigin': origin,
            'hasVideo': bool(video), 'tracks': tracks}


def extract_timeline(path, target, media, track_index):
    track = next((track for track in media['tracks'] if track['index'] == track_index), None)
    if track is None:
        raise ValueError('Selecione uma faixa de áudio presente no arquivo.')
    encoder = shutil.which('ffmpeg')
    if not encoder:
        raise ValueError('FFmpeg local indisponível.')
    # Actual decoded PTS include codec priming/skip-sample corrections. Rebase
    # them against the video origin, rather than discarding PTS and guessing
    # an offset from the container's first compressed audio packet.
    origin = media.get('timelineOrigin', 0)
    filters = [f'asetpts=PTS-({origin:.9f})/TB', f'aresample={RATE}:async=1:first_pts=0',
               'apad', f'atrim=end_sample={media["samples"]}']
    run([encoder, '-nostdin', '-v', 'error', '-n', '-copyts', '-i', str(path), '-map', f'0:{track_index}',
         '-vn', '-af', ','.join(filters), '-ac', '2', '-ar', str(RATE), '-c:a', 'pcm_s16le', str(target)])
    with wave.open(str(target)) as audio:
        if audio.getnframes() != media['samples'] or audio.getframerate() != RATE:
            raise ValueError('O áudio extraído não corresponde à linha do tempo da fonte.')
