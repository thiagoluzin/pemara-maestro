"""Explicit, reviewed actor masks; CPU composition never infers identity or approval."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, PngImagePlugin

MODE = 'background_only_actor_protected_v1'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sidecar(path):
    return Path(str(path) + '.dlss5.protection.json')


def build_anchor_workflow(image_input, mask_input, subjects, review, *, prefix='actor_protected/anchor'):
    """Build only. Input files are uploaded separately through the authorized channel."""
    if not subjects or review.get('status') != 'PASS' or not review.get('reviewer') or not review.get('note'):
        raise ValueError('Definir sujeitos e revisar a cobertura antes de compilar o acabamento.')
    return {
        '1': {'class_type': 'LoadImage', 'inputs': {'image': image_input}},
        '2': {'class_type': 'LoadImage', 'inputs': {'image': mask_input}},
        # LoadImage's MASK output is inverse alpha; a grayscale matte must use its red channel.
        '3': {'class_type': 'ImageToMask', 'inputs': {'image': ['2', 0], 'channel': 'red'}},
        '4': {'class_type': 'PemaraSaveActorProtectedImage', 'inputs': {
            'images': ['1', 0], 'actor_mask': ['3', 0], 'protected_subjects': ', '.join(subjects),
            'mask_review_note': review['note'], 'mask_reviewer': review['reviewer'],
            'mask_coverage_checked': True, 'filename_prefix': prefix}},
    }


def read_contract(path, source, size, frames):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != '1.0' or data.get('mode') != MODE:
        raise ValueError('Perfil de protecao desconhecido.')
    if data.get('source_sha256') != sha(source):
        raise ValueError('Mascara nao pertence aos bytes da fonte anterior ao DLSS.')
    subjects = data.get('protected_subjects')
    if not isinstance(subjects, list) or not subjects or any(not isinstance(s, str) or not s.strip() for s in subjects):
        raise ValueError('Identifique todos os personagens protegidos, inclusive mortos.')
    review = data.get('mask_review') or {}
    if review.get('status') != 'PASS' or not review.get('reviewer') or not review.get('note'):
        raise ValueError('Mascara exige parecer visual registrado; metadata nao aprova cobertura.')
    entries = data.get('masks')
    if not isinstance(entries, list) or len(entries) != frames:
        raise ValueError('Exigir uma mascara por quadro; nao repetir automaticamente mascara estatica.')
    masks = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get('path') or not entry.get('sha256'):
            raise ValueError('Mascara exige caminho e SHA-256.')
        candidate = Path(entry['path'])
        candidate = (path.parent / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        if candidate.suffix.lower() != '.png' or sha(candidate) != entry['sha256']:
            raise ValueError('Mascara PNG ausente ou alterada.')
        load_mask(candidate, size)
        masks.append({'path': str(candidate), 'sha256': entry['sha256']})
    return {'mode': MODE, 'contract': str(path), 'contract_sha256': sha(path),
            'source_sha256': data['source_sha256'], 'protected_subjects': subjects,
            'mask_review': review, 'masks': masks, 'frames': frames,
            'composition': 'linear_srgb; white=source, black=DLSS; soft matte edges',
            'artistic_status': 'PENDING_OWNER_REVIEW'}


def load_mask(path, size):
    with Image.open(path) as image:
        if image.size != tuple(size) or image.mode != 'L' or getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Mascara deve ser PNG L 8-bit com geometria exata, sem resize automatico.')
        mask = np.asarray(image, dtype=np.uint8).copy()
    if not np.any(mask == 255) or not np.any(mask == 0):
        raise ValueError('Mascara exige interior protegido branco e fundo preto; vazio/integral bloqueado.')
    return mask


def verify_contract(contract):
    if sha(contract['contract']) != contract['contract_sha256']:
        raise ValueError('Contrato mudou durante o acabamento.')
    for entry in contract['masks']:
        if sha(entry['path']) != entry['sha256']:
            raise ValueError('Mascara mudou durante o acabamento.')


def composite_rgba(source, treated, mask):
    if source.shape != treated.shape or source.shape[:2] != mask.shape or source.shape[-1] != 4:
        raise ValueError('Ramos e mascara com geometria divergente.')
    a = source[..., :3].astype(np.float32) / 255
    b = treated[..., :3].astype(np.float32) / 255
    a = np.where(a <= .04045, a / 12.92, ((a + .055) / 1.055) ** 2.4)
    b = np.where(b <= .04045, b / 12.92, ((b + .055) / 1.055) ** 2.4)
    weight = mask.astype(np.float32)[..., None] / 255
    linear = a * weight + b * (1 - weight)
    rgb = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)
    result = source.copy()
    result[..., :3] = np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8)
    result[mask == 255] = source[mask == 255]
    result[mask == 0, :3] = treated[mask == 0, :3]
    # Alpha is inherited from the source, including feathered transparent pixels.
    return result


def compose_image(source, treated, dest, contract):
    if Path(dest).suffix.lower() not in {'.png', '.webp'}:
        raise ValueError('Protecao de ancoras requer PNG ou WebP sem perdas; sem conversao silenciosa.')
    with Image.open(source) as original, Image.open(treated) as processed:
        mask = load_mask(contract['masks'][0]['path'], original.size)
        a = np.asarray(original.convert('RGBA'))
        result = composite_rgba(a, np.asarray(processed.convert('RGBA')), mask)
        info = dict(original.info)
    options = {'lossless': True} if Path(dest).suffix.lower() == '.webp' else {}
    if Path(dest).suffix.lower() == '.png':
        metadata = PngImagePlugin.PngInfo()
        for key, value in info.items():
            if isinstance(value, str):
                metadata.add_text(key, value)
        options['pnginfo'] = metadata
    for key in ('icc_profile', 'exif'):
        if info.get(key):
            options[key] = info[key]
    Image.fromarray(result).save(dest, **options)
    with Image.open(dest) as saved:
        actual = np.asarray(saved.convert('RGBA'))
        if not np.array_equal(actual[mask == 255], a[mask == 255]):
            raise ValueError('Interior protegido alterado na imagem final.')
        if not np.array_equal(actual[..., 3], a[..., 3]):
            raise ValueError('Alpha alterado na composicao.')
    verify_contract(contract)
    return {'actor_protection': contract, 'protected_pixels_exact': True,
            'protected_pixels_scope': 'lossless_image; mask=255', 'alpha_preserved': True}


def _read_frame(stream, count):
    chunks = bytearray()
    while len(chunks) < count:
        data = stream.read(count - len(chunks))
        if not data:
            break
        chunks.extend(data)
    if len(chunks) != count:
        raise ValueError('Video terminou antes da mascara correspondente.')
    return bytes(chunks)


def compose_video(source, treated, dest, contract, ffmpeg, size, fps, *, codec='h264_nvenc'):
    width, height = size
    count = width * height * 4
    processes = []
    logs = []
    try:
        for index, path in enumerate((source, treated)):
            log = open(str(dest) + f'.decode{index}.log', 'wb'); logs.append(log)
            processes.append(subprocess.Popen([str(ffmpeg), '-v', 'error', '-i', str(path),
                '-map', '0:v:0', '-fps_mode', 'passthrough', '-pix_fmt', 'rgba', '-f', 'rawvideo', '-'],
                stdout=subprocess.PIPE, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
        log = open(str(dest) + '.encode.log', 'wb'); logs.append(log)
        args = [str(ffmpeg), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba',
                '-s', f'{width}x{height}', '-r', str(fps), '-i', '-', '-i', str(source),
                '-map', '0:v:0', '-map', '1:a:0?', '-c:v', codec, '-c:a', 'copy']
        if codec in {'h264_nvenc', 'av1_nvenc'}:
            args += ['-preset', 'p7', '-cq', '15', '-pix_fmt', 'yuv420p']
        processes.append(subprocess.Popen(args + [str(dest)], stdin=subprocess.PIPE,
            stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
        a, b, encoder = processes
        for entry in contract['masks']:
            source_frame = np.frombuffer(_read_frame(a.stdout, count), dtype=np.uint8).reshape(height, width, 4)
            treated_frame = np.frombuffer(_read_frame(b.stdout, count), dtype=np.uint8).reshape(height, width, 4)
            mask = load_mask(entry['path'], size)
            encoder.stdin.write(composite_rgba(source_frame, treated_frame, mask).tobytes())
        if a.stdout.read(1) or b.stdout.read(1):
            raise ValueError('Video possui quadros sem mascara; composicao bloqueada.')
        encoder.stdin.close()
        for process in processes:
            if process.wait(timeout=120):
                raise ValueError('Falha no codec/compositor; consultar logs preservados.')
        verify_contract(contract)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill(); process.wait(timeout=10)
            for stream in (process.stdin, process.stdout):
                if stream and not stream.closed:
                    stream.close()
        for log in logs:
            log.close()
    return {'actor_protection': contract, 'protected_pixels_exact': False,
            'protected_pixels_scope': 'exact before encode at mask=255; video codec may change pixels',
            'mask_frames': contract['frames']}
