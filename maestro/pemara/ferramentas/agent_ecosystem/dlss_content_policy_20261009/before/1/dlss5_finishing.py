"""Mandatory local DLSS 5 finishing; originals and technical receipts are retained."""
from __future__ import annotations

import hashlib
from fractions import Fraction
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid
import actor_protection as actors

RUNTIME = Path(r'E:\Pemara\third_party\video2dlssnr-v1.4.1')
EXE = RUNTIME / 'nvidia-original' / 'video2dlssnr.exe'
WRAPPER = RUNTIME / 'release' / 'nr_video_frame_preserving.py'
FFMPEG = RUNTIME / 'release' / 'out' / 'ffmpeg.exe'
FFPROBE = RUNTIME / 'release' / 'out' / 'ffprobe.exe'
PROFILE = 'dlss5_required_natural_re1_v1'
ACTOR_PROFILE = 'dlss5_natural_background_actor_protected_v1'
ASSEMBLY_PROFILE = 'dlss5_required_provenance_assembly_v2'
REQUIRED = True
PARAMETERS = {'style': 1, 'intensity': 0.5, 'local_structure': 0.5, 'local_tone': 0,
              'skin': 0.25, 'detail': 0.5, 'color': 0, 'auto_mask': True, 'scale': 1}
PINNED = {
    EXE: '7658f780aaa0ce9112d93a036273e19c4d62bf03ffae1a7bb6099d485a97ff58',
    EXE.parent / 'nvngx_dlssnr.dll': 'e16bcf15e16e13f527491cdf7845b2fe6521a738d8f7c9c721866a8496e1fc8e',
    EXE.parent / 'nvngx.dll_dlssnr.dll': 'a64d48ec6157a6811f9b812de47ecb718f4143c3355879c22515e6418b7c1bea',
    EXE.parent / 'nvngx_dlss.dll': 'c85f971ce023c9f3492fc7455f0b01a24ba18ea39636407a846902c4360b0b7e',
    WRAPPER: '96118179e0b1b2f384d00e74ce5c8878b0f487224aadaf27f102ee5f010fda67',
}
_LOCK = threading.RLock()
_VERIFIED = {}

class DLSS5RequiredError(RuntimeError):
    pass

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def _run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, **kwargs)

def preflight():
    if REQUIRED is not True:
        raise DLSS5RequiredError('DLSS 5 obrigatorio: desativacao nao permitida.')
    for path in [WRAPPER, FFMPEG, FFPROBE, EXE.parent / 'nvngx_dlss.dll']:
        if not path.is_file():
            raise DLSS5RequiredError(f'DLSS 5 obrigatorio: runtime ausente: {path}')
    for path, expected in PINNED.items():
        if not path.is_file():
            raise DLSS5RequiredError(f'DLSS 5 obrigatorio: componente ausente: {path.name}')
        token = (path.stat().st_size, path.stat().st_mtime_ns)
        if _VERIFIED.get(str(path)) != token:
            if sha(path) != expected:
                raise DLSS5RequiredError(f'DLSS 5 obrigatorio: hash divergente: {path.name}')
            _VERIFIED[str(path)] = token
    return {'required': True, 'profile': PROFILE, 'parameters': dict(PARAMETERS),
            'actor_protection': {'profile': ACTOR_PROFILE, 'mode': actors.MODE,
                'explicit_mask_required': True, 'automatic_actor_segmentation': False,
                'image_formats': ['png', 'webp'], 'video_mask': 'one reviewed PNG per presentation frame',
                'visual_qualification': 'PENDING_REAL_MEDIA_COMPARISON'}}

def receipt_path(path):
    return Path(str(path) + '.dlss5.json')

def valid_receipt(path):
    try:
        data = json.loads(receipt_path(path).read_text(encoding='utf-8'))
        profile = data.get('profile')
        selective = data.get('actor_protection') or {}
        if profile == ACTOR_PROFILE and (selective.get('mode') != actors.MODE or not selective.get('contract_sha256')):
            return None
        if profile == ASSEMBLY_PROFILE and not data.get('processing_modes'):
            return None
        if profile in {PROFILE, ACTOR_PROFILE, ASSEMBLY_PROFILE} and data.get('technical_pass') is True and data.get('output_sha256') == sha(path):
            return data
    except (OSError, ValueError):
        pass
    return None

def _atomic_json(path, data):
    temp = Path(str(path) + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temp, path)

def _probe(path):
    return json.loads(_run([FFPROBE, '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', path]).stdout)

def _audio_hash(path):
    return _run([FFMPEG, '-v', 'error', '-i', path, '-map', '0:a:0', '-c:a', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).stdout.decode().strip()


def _audio_pcm_hash(path, duration=None):
    args = [FFMPEG, '-v', 'error', '-i', path, '-map', '0:a:0']
    if duration is not None:
        args += ['-t', str(duration)]
    return _run(args + ['-c:a', 'pcm_f32le', '-f', 'hash', '-hash', 'sha256', '-']).stdout.decode().strip()


def _timestamps(path):
    data = json.loads(_run([FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-show_frames',
                           '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', path]).stdout)
    return [float(frame['best_effort_timestamp_time']) for frame in data['frames']]

def _video(source, dest, log):
    before = _probe(source)
    v = next(s for s in before['streams'] if s['codec_type'] == 'video')
    if len([s for s in before['streams'] if s['codec_type'] == 'audio']) > 1:
        raise DLSS5RequiredError('DLSS 5: multiplas faixas de audio exigem qualificacao separada; fonte preservada.')
    if v.get('pix_fmt', '').startswith(('yuva', 'rgba', 'bgra', 'argb', 'abgr', 'gbrap')):
        raise DLSS5RequiredError('DLSS 5: video com alpha exige qualificacao separada; fonte preservada.')
    high_depth = int(v.get('bits_per_raw_sample') or 8) > 8 or bool(re.search(r'(10|12|14|16)', v.get('pix_fmt', '')))
    if high_depth:
        raise DLSS5RequiredError('DLSS 5: video de alta profundidade exige qualificacao separada; fonte preservada.')
    codec = 'av1_nvenc' if dest.suffix.lower() == '.webm' else {'h264':'h264_nvenc', 'hevc':'hevc_nvenc', 'av1':'av1_nvenc'}.get(v.get('codec_name'), 'h264_nvenc')
    args = [sys.executable, WRAPPER, '--exe', EXE, '--in', source, '--out', dest,
            '--nr-scale', '1', '--nr-style', '1', '--nr-intensity', '.5', '--nr-local-structure', '.5',
            '--nr-local-tone', '0', '--nr-skin', '.25', '--nr-detail', '.5', '--nr-color', '0',
            '--nr-auto-mask', '--nr-motion', '1', '--nr-motion-engine', 'lk',
            '--codec', codec, '--cq', '15', '--enc-preset', 'p7', '--bit-depth', '10' if high_depth else '8', '--audio', 'copy']
    with log.open('wb') as output:
        proc = subprocess.run([str(a) for a in args], stdout=output, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, timeout=7200)
    if proc.returncode:
        raise DLSS5RequiredError(f'DLSS 5 falhou; fonte preservada. Log: {log}')
    evidence = log.read_text(errors='replace')
    if 'feature ready; streaming' not in evidence or str(EXE.parent / 'nvngx_dlssnr.dll') not in evidence:
        raise DLSS5RequiredError('DLSS 5: execucao Neural Rendering nao comprovada; sem entrega.')
    after = _probe(dest)
    w = next(s for s in after['streams'] if s['codec_type'] == 'video')
    for key in ['width', 'height', 'avg_frame_rate', 'nb_read_frames']:
        if v.get(key) != w.get(key):
            raise DLSS5RequiredError(f'DLSS 5 alterou {key}; sem entrega.')
    if abs(float(v.get('duration') or before['format']['duration']) - float(w.get('duration') or after['format']['duration'])) > 0.025:
        raise DLSS5RequiredError('DLSS 5 alterou duracao; sem entrega.')
    old_times, new_times = _timestamps(source), _timestamps(dest)
    if len(old_times) != len(new_times) or any(abs(a-b) > .002 for a,b in zip(old_times,new_times)):
        raise DLSS5RequiredError('DLSS 5 alterou os tempos dos quadros; sem entrega.')
    has_audio = any(s['codec_type'] == 'audio' for s in before['streams'])
    if has_audio and _audio_hash(source) != _audio_hash(dest):
        raise DLSS5RequiredError('DLSS 5 alterou o audio; sem entrega.')
    picture_duration = float(v.get('duration') or before['format']['duration'])
    if has_audio and _audio_pcm_hash(source, picture_duration) != _audio_pcm_hash(dest, picture_duration):
        raise DLSS5RequiredError('DLSS 5 alterou o sinal de audio decodificado; sem entrega.')
    _run([FFMPEG, '-v', 'error', '-xerror', '-i', dest, '-f', 'null', '-'], timeout=1800)
    return {'width': w['width'], 'height': w['height'], 'fps': w['avg_frame_rate'], 'frames': int(w['nb_read_frames']),
            'audio_payload_preserved': has_audio, 'audio_pcm_preserved': has_audio,
            'audio_pcm_comparison_seconds': picture_duration,
            'frame_timestamps_preserved': True, 'neural_rendering_evidence': str(log)}

def _image(source, dest, log):
    from PIL import Image, PngImagePlugin
    with Image.open(source) as loaded:
        if getattr(loaded, 'n_frames', 1) != 1:
            raise DLSS5RequiredError('DLSS 5: imagem animada exige tratamento temporal; entrega bloqueada.')
        if loaded.mode not in {'RGB', 'RGBA', 'L', 'LA', 'P', '1'}:
            raise DLSS5RequiredError('DLSS 5: formato de imagem de alta profundidade ainda nao qualificado; entrega bloqueada.')
        info = dict(loaded.info)
        original = loaded.convert('RGBA')
    w, h = original.size
    # Pad only for the model, then crop back. Handles odd PNG dimensions exactly.
    pw, ph = max(64, (w + 1) // 2 * 2), max(64, (h + 1) // 2 * 2)
    canvas = Image.new('RGBA', (pw, ph))
    canvas.paste(original, (0, 0))
    args = [EXE, '--nr-video', '--nr-in', f'{pw}x{ph}', '--nr-arch-spoof', '0', '--nr-motion', '0',
            '--nr-style', '1', '--nr-intensity', '.5', '--nr-local-structure', '.5', '--nr-local-tone', '0',
            '--nr-skin', '.25', '--nr-detail', '.5', '--nr-color', '0', '--nr-auto-mask']
    with log.open('wb') as stderr:
        process = subprocess.run([str(a) for a in args], input=canvas.tobytes(), stdout=subprocess.PIPE,
                                 stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, timeout=300)
    evidence = log.read_text(errors='replace')
    if process.returncode or len(process.stdout) != pw * ph * 4 or 'feature ready; streaming' not in evidence or str(EXE.parent / 'nvngx_dlssnr.dll') not in evidence:
        raise DLSS5RequiredError(f'DLSS 5 de imagem nao comprovado; sem entrega. Log: {log}')
    image = Image.frombytes('RGBA', (pw, ph), process.stdout).crop((0, 0, w, h))
    image.putalpha(original.getchannel('A'))
    options = {}
    if dest.suffix.lower() == '.png':
        metadata = PngImagePlugin.PngInfo()
        for key, value in info.items():
            if isinstance(value, str):
                metadata.add_text(key, value)
        options['pnginfo'] = metadata
    if info.get('icc_profile'):
        options['icc_profile'] = info['icc_profile']
    if info.get('exif'):
        options['exif'] = info['exif']
    if info.get('dpi') and dest.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
        options['dpi'] = info['dpi']
    if dest.suffix.lower() in {'.jpg', '.jpeg'}:
        image = image.convert('RGB')
        options.update(quality=95, subsampling=0)
    elif dest.suffix.lower() == '.webp':
        options['lossless'] = True
    image.save(dest, **options)
    with Image.open(dest) as check:
        if check.size != (w, h):
            raise DLSS5RequiredError('DLSS 5 alterou dimensoes da imagem.')
        if dest.suffix.lower() not in {'.jpg', '.jpeg'} and check.convert('RGBA').getchannel('A').tobytes() != original.getchannel('A').tobytes():
            raise DLSS5RequiredError('DLSS 5 alterou transparencia.')
    return {'width': w, 'height': h, 'frames': 1, 'alpha_preserved': dest.suffix.lower() not in {'.jpg', '.jpeg'}, 'neural_rendering_evidence': str(log)}

def finish_file(path, *, protection_manifest=None, protect_actors=False):
    """Process a newly produced file atomically; errors never authorize raw delivery."""
    path = Path(path).resolve()
    with _LOCK:
        manifest = Path(protection_manifest).resolve() if protection_manifest else actors.sidecar(path)
        protection_requested = protect_actors or protection_manifest is not None or manifest.exists()
        if protection_requested and not manifest.is_file():
            raise DLSS5RequiredError('Protecao dos atores exige mascara explicita; sem fallback integral.')
        existing = valid_receipt(path)
        if existing:
            if protection_requested and (existing.get('profile') != ACTOR_PROFILE or
                    existing['actor_protection'].get('contract_sha256') != actors.sha(manifest)):
                raise DLSS5RequiredError('Fonte ja tratada com outro perfil; usar fonte anterior, sem DLSS recursivo.')
            return existing
        suffix = path.suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.mkv', '.webm'}:
            raise DLSS5RequiredError(f'DLSS 5 obrigatorio: formato nao qualificado: {suffix}')
        source_hash = sha(path)
        protection = None
        if protection_requested:
            try:
                if suffix in {'.png', '.webp'}:
                    from PIL import Image
                    with Image.open(path) as image:
                        size, frames = image.size, getattr(image, 'n_frames', 1)
                    if frames != 1:
                        raise ValueError('Imagem animada requer contrato temporal.')
                elif suffix in {'.mp4', '.mov', '.mkv', '.webm'}:
                    video = next(s for s in _probe(path)['streams'] if s['codec_type'] == 'video')
                    size, frames = (video['width'], video['height']), int(video['nb_read_frames'])
                    if video['avg_frame_rate'] != video['r_frame_rate']:
                        raise ValueError('Protecao temporal exige CFR.')
                else:
                    raise ValueError('Ancoras protegidas exigem PNG/WebP sem perdas.')
                protection = actors.read_contract(manifest, path, size, frames)
            except (OSError, ValueError, KeyError, StopIteration) as error:
                raise DLSS5RequiredError(f'Protecao dos atores invalida: {error}') from error
        preflight()
        native = path.with_name(path.stem + '.before_dlss5.' + source_hash[:12] + path.suffix)
        if native.exists() and sha(native) != source_hash:
            raise DLSS5RequiredError('Original preservado divergente; sem sobrescrever.')
        if not native.exists():
            shutil.copy2(path, native)
        dest = path.with_name(path.stem + '.dlss5_pending_' + uuid.uuid4().hex[:8] + path.suffix)
        log = Path(str(dest) + '.log')
        start = time.monotonic()
        rendered = dest.with_name(dest.stem + '.full_frame_nr' + dest.suffix) if protection else dest
        checks = _image(native, rendered, log) if suffix in {'.png', '.jpg', '.jpeg', '.webp'} else _video(native, rendered, log)
        if protection:
            try:
                if suffix in {'.png', '.webp'}:
                    checks.update(actors.compose_image(native, rendered, dest, protection))
                else:
                    # Both branches use the same already-qualified presentation timestamps.
                    actors.verify_contract(protection)
                    old_times = _timestamps(native)
                    if len(old_times) != frames or any(abs(t - i / float(Fraction(video['avg_frame_rate']))) > .002 for i, t in enumerate(old_times)):
                        raise ValueError('Mascaras exigem fonte CFR desde timestamp zero.')
                    codec = 'av1_nvenc' if suffix == '.webm' else 'h264_nvenc'
                    checks.update(actors.compose_video(native, rendered, dest, protection, FFMPEG, size, video['avg_frame_rate'], codec=codec))
                    after = next(s for s in _probe(dest)['streams'] if s['codec_type'] == 'video')
                    if (after['width'], after['height'], int(after['nb_read_frames'])) != (*size, frames):
                        raise ValueError('Composicao alterou geometria/quadros.')
                    times = _timestamps(dest)
                    if len(times) != len(old_times) or any(abs(a-b) > .002 for a,b in zip(old_times,times)):
                        raise ValueError('Composicao alterou timestamps.')
                    if any(s['codec_type'] == 'audio' for s in _probe(native)['streams']):
                        if _audio_hash(native) != _audio_hash(dest) or _audio_pcm_hash(native) != _audio_pcm_hash(dest):
                            raise ValueError('Composicao alterou audio.')
                    _run([FFMPEG, '-v', 'error', '-xerror', '-i', dest, '-f', 'null', '-'], timeout=1800)
                checks['neural_intermediate'] = {'path': str(rendered), 'sha256': sha(rendered)}
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                raise DLSS5RequiredError(f'Composicao seletiva falhou; fonte preservada: {error}') from error
        if sha(path) != source_hash or sha(native) != source_hash:
            raise DLSS5RequiredError('Fonte mudou durante DLSS 5; candidato preservado, entrega bloqueada.')
        data = {'required': True, 'profile': ACTOR_PROFILE if protection else PROFILE,
                'processing_mode': actors.MODE if protection else 'full_frame',
                'parameters': dict(PARAMETERS), 'source': str(native),
                'source_sha256': source_hash, 'output': str(path), 'output_sha256': sha(dest),
                'technical_pass': True, 'owner_approval': 'PENDING', 'processing_seconds': round(time.monotonic() - start, 3), **checks}
        os.replace(dest, path)
        _atomic_json(receipt_path(path), data)
        return data

def carry_receipt(source, dest):
    """Conforming an already finished file does not apply the neural pass twice."""
    data = valid_receipt(source)
    if not data:
        return finish_file(dest)
    data = dict(data)
    prior_checks = dict(data.get('inherited_stage_checks') or {})
    for key in ('width', 'height', 'fps', 'frames', 'audio_payload_preserved', 'audio_pcm_preserved',
                'audio_pcm_comparison_seconds', 'frame_timestamps_preserved', 'alpha_preserved'):
        if key in data:
            prior_checks[key] = data.pop(key)
    path = Path(dest)
    if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
        from PIL import Image
        with Image.open(path) as image:
            data.update(width=image.width, height=image.height, frames=getattr(image, 'n_frames', 1))
    else:
        probe = _probe(path)
        video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        data.update(width=video['width'], height=video['height'], fps=video['avg_frame_rate'], frames=int(video['nb_read_frames']))
    data.update(output=str(path.resolve()), output_sha256=sha(path), conformed_from=str(source), inherited_stage_checks=prior_checks)
    if data.get('actor_protection'):
        data['actor_protection_scope'] = 'inherited_from_source_stage; geometry/cadence changes require separate review'
    _atomic_json(receipt_path(dest), data)
    return data


def inherit_assembly(sources, dest):
    """Record a bitstream-copy assembly of individually verified finished takes."""
    receipts = [valid_receipt(path) for path in sources]
    if not sources or not all(receipts):
        raise DLSS5RequiredError('Montagem inclui fonte sem DLSS 5 comprovado.')
    modes = sorted({mode for receipt in receipts for mode in
                    receipt.get('processing_modes', [receipt.get('processing_mode', 'full_frame')])})
    data = {'required': True, 'profile': PROFILE if modes == ['full_frame'] else ASSEMBLY_PROFILE,
            'processing_modes': modes, 'parameters': dict(PARAMETERS),
            'output': str(Path(dest).resolve()), 'output_sha256': sha(dest),
            'technical_pass': True, 'owner_approval': 'PENDING',
            'inherited_from': [{'path':str(path), 'sha256':receipt['output_sha256'],
                'profile':receipt['profile'], 'processing_mode':receipt.get('processing_mode'),
                'processing_modes':receipt.get('processing_modes'),
                'actor_protection_contract_sha256':(receipt.get('actor_protection') or {}).get('contract_sha256')}
                for path,receipt in zip(sources,receipts)],
            'method': 'concatenation_video_bitstream_copy'}
    _atomic_json(receipt_path(dest), data)
    return data
