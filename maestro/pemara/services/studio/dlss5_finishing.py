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
import dlss5_content_policy as content_policy

RUNTIME = Path(r'E:\Pemara\third_party\video2dlssnr-v1.4.1')
EXE = RUNTIME / 'nvidia-original' / 'video2dlssnr.exe'
FFMPEG = RUNTIME / 'release' / 'out' / 'ffmpeg.exe'
FFPROBE = RUNTIME / 'release' / 'out' / 'ffprobe.exe'
LEGACY_PROFILE = 'dlss5_required_natural_re1_v1'
PROFILE = 'dlss5_required_full_frame_20261010_v1'
ACTOR_PROFILE = 'dlss5_natural_background_actor_protected_v1'
ASSEMBLY_PROFILE = 'dlss5_required_provenance_assembly_v2'
REQUIRED = True
PARAMETERS = {'style': 1, 'intensity': 1.0, 'local_structure': 1.0, 'local_tone': 0,
              'skin': 1.0, 'detail': 1.0, 'color': 0, 'auto_mask': False, 'scale': 1}
PINNED = {
    EXE: '7658f780aaa0ce9112d93a036273e19c4d62bf03ffae1a7bb6099d485a97ff58',
    EXE.parent / 'nvngx_dlssnr.dll': 'e16bcf15e16e13f527491cdf7845b2fe6521a738d8f7c9c721866a8496e1fc8e',
    EXE.parent / 'nvngx.dll_dlssnr.dll': 'a64d48ec6157a6811f9b812de47ecb718f4143c3355879c22515e6418b7c1bea',
    EXE.parent / 'nvngx_dlss.dll': 'c85f971ce023c9f3492fc7455f0b01a24ba18ea39636407a846902c4360b0b7e',
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
    for path in [FFMPEG, FFPROBE, EXE.parent / 'nvngx_dlss.dll']:
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
            'content_policy': content_policy.status(),
            'processing_mode':'full_frame', 'coverage_percent':100, 'automatic_masks':False,
            'actor_protection': {'required':False, 'applied':False, 'explicit_mask_required':False},
            'legacy_actor_profile_readable':ACTOR_PROFILE}


def receipt_path(path):
    return Path(str(path) + '.dlss5.json')


def staging_receipt(path):
    try:
        data = json.loads(Path(str(path)+'.dlss5.staging.json').read_text(encoding='utf-8'))
        if (data.get('content_policy_version') == content_policy.VERSION
            and data.get('content_kind') in content_policy.PROTECTED
            and data.get('technical_pass') is False
            and data.get('output_sha256') == sha(path)):
            return data
    except (OSError, ValueError):
        pass
    return None


def preserve_native_preview(path, content_kind):
    kind = content_policy.normalize(content_kind)
    if kind not in content_policy.PROTECTED:
        raise DLSS5RequiredError('Staging protegido exige live_action ou mixed.')
    data = {'content_policy_version': content_policy.VERSION, 'content_kind':kind,
            'required':True,'stage':'native_preview','status':'PENDING_ACTOR_MASKS',
            'technical_pass':False,'dlss_applied':False,
            'output':str(Path(path).resolve()),'output_sha256':sha(path),
            'owner_approval':'PENDING','final_delivery_allowed':False}
    _atomic_json(Path(str(path)+'.dlss5.staging.json'),data)
    return data

def valid_receipt(path):
    try:
        data = json.loads(receipt_path(path).read_text(encoding='utf-8'))
        profile = data.get('profile')
        selective = data.get('actor_protection') or {}
        if profile == ACTOR_PROFILE and (selective.get('mode') != actors.MODE or not selective.get('contract_sha256')):
            return None
        if profile == ASSEMBLY_PROFILE and not data.get('processing_modes'):
            return None
        if profile in {PROFILE, LEGACY_PROFILE, ACTOR_PROFILE, ASSEMBLY_PROFILE} and data.get('technical_pass') is True and data.get('output_sha256') == sha(path):
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
            '--nr-style', '1', '--nr-intensity', '1', '--nr-local-structure', '1', '--nr-local-tone', '0',
            '--nr-skin', '1', '--nr-detail', '1', '--nr-color', '0']
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

def finish_file(path, *, protection_manifest=None, protect_actors=False, content_kind=None):
    """Process a newly produced file atomically; errors never authorize raw delivery."""
    path = Path(path).resolve()
    if path.suffix.lower() in {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.gif', '.apng'}:
        raise DLSS5RequiredError('DLSS 5 proibido em videos por ordem do proprietario de 2026-10-22; permitido somente em ancoras. Usar a fonte anterior ao DLSS.')
    with _LOCK:
        manifest = Path(protection_manifest).resolve() if protection_manifest else actors.sidecar(path)
        protection_requested = protect_actors or protection_manifest is not None or manifest.exists()
        existing = valid_receipt(path)
        try:
            kind = content_policy.resolve(path, content_kind=content_kind,
                protection_requested=protection_requested, existing=existing, source_sha256=sha(path))
        except (OSError, ValueError) as error:
            raise DLSS5RequiredError(str(error)) from error
        if existing:
            # Preserve qualified historical files; a policy change never reapplies NR.
            return existing
        if protection_requested:
            raise DLSS5RequiredError('DLSS 5 integral obrigatorio: remover exportador/mascaras seletivas do workflow novo.')
        suffix = path.suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.webp'}:
            raise DLSS5RequiredError(f'DLSS 5 obrigatorio: formato nao qualificado: {suffix}')
        source_hash = sha(path)
        preflight()
        native = path.with_name(path.stem + '.before_dlss5.' + source_hash[:12] + path.suffix)
        if native.exists() and sha(native) != source_hash:
            raise DLSS5RequiredError('Original preservado divergente; sem sobrescrever.')
        if not native.exists():
            shutil.copy2(path, native)
        dest = path.with_name(path.stem + '.dlss5_pending_' + uuid.uuid4().hex[:8] + path.suffix)
        log = Path(str(dest) + '.log')
        start = time.monotonic()
        checks = _image(native, dest, log)
        if sha(path) != source_hash or sha(native) != source_hash:
            raise DLSS5RequiredError('Fonte mudou durante DLSS 5; candidato preservado, entrega bloqueada.')
        data = {'required': True, 'profile': PROFILE,
                'processing_mode': 'full_frame', 'coverage_percent':100,
                'actor_protection_applied':False, 'automatic_masks':False,
                'parameters': dict(PARAMETERS), 'source': str(native),
                'content_kind': kind, 'content_policy_version': content_policy.VERSION,
                'source_sha256': source_hash, 'output': str(path), 'output_sha256': sha(dest),
                'technical_pass': True, 'owner_approval': 'PENDING', 'processing_seconds': round(time.monotonic() - start, 3), **checks}
        os.replace(dest, path)
        _atomic_json(receipt_path(path), data)
        return data

def carry_receipt(source, dest):
    """Conforming an already finished file does not apply the neural pass twice."""
    data = valid_receipt(source)
    if not data:
        pending = staging_receipt(source)
        if pending:
            return preserve_native_preview(dest, pending['content_kind'])
        if Path(dest).suffix.lower() in {'.mp4','.mov','.mkv','.webm','.avi','.gif','.apng'}:
            return preserve_video_policy(dest)
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


def preserve_video_policy(path):
    """Record the no-NR video policy without invoking any media processing."""
    path=Path(path).resolve()
    if path.suffix.lower() not in {'.mp4','.mov','.mkv','.webm','.avi','.gif','.apng'}:
        raise ValueError('Video policy requires a video file.')
    proof={'required':False,'applied':False,'scope':'anchors_only',
        'policy_version':content_policy.VERSION,'media_role':'video',
        'output':str(path),'output_sha256':sha(path),'dlss5_applied':False}
    _atomic_json(Path(str(path)+'.finishing_policy.json'),proof)
    return proof
