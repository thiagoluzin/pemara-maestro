"""Local source preparation. Does not call ComfyUI or change playback speed."""
from pathlib import Path
import hashlib
import json
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw


def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
        capture_output=True, check=True, timeout=60)
    return json.loads(r.stdout)


def sample_sheet(path, output, *, start=0, seconds=None, sample_fps=2, columns=4, page_frames=24):
    info = probe(path)
    duration = float(info['format']['duration'])
    end = min(duration, start + seconds) if seconds else duration
    capture = cv2.VideoCapture(str(path))
    frames = []
    timestamp = start
    while timestamp < end - 1e-6:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if not ok: break
        frames.append((timestamp, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        timestamp += 1 / sample_fps
    capture.release()
    paths = []
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    for page in range((len(frames) + page_frames - 1) // page_frames):
        selected = frames[page * page_frames:(page + 1) * page_frames]
        rows = (len(selected) + columns - 1) // columns
        sheet = Image.new('RGB', (columns * 320, rows * 204), '#171d29')
        draw = ImageDraw.Draw(sheet)
        for j, (time, frame) in enumerate(selected):
            image = Image.fromarray(frame); image.thumbnail((320, 180))
            x, y = j % columns * 320, j // columns * 204
            sheet.paste(image, (x + (320 - image.width) // 2, y + 24 + (180 - image.height) // 2))
            draw.text((x + 6, y + 5), f'{time:.3f}s', fill='white')
        path = output.with_name(output.stem + f'_p{page:02}.jpg')
        sheet.save(path, quality=90); paths.append(str(path))
    return paths


def detect_cuts(path, *, threshold=0.45):
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1: raise ValueError('FPS da referência inválido.')
    previous = None; cuts = []; frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok: break
        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        histogram = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(histogram, histogram)
        if previous is not None:
            score = float(cv2.compareHist(previous, histogram, cv2.HISTCMP_BHATTACHARYYA))
            if score > threshold:
                cuts.append({'frame': frame_index, 'seconds': frame_index / fps, 'score': score,
                    'status': 'POSSIBLE_CUT_OR_FLASH'})
        previous = histogram; frame_index += 1
    capture.release()
    duration = frame_index / fps
    boundaries = [0] + [c['seconds'] for c in cuts] + [duration]
    return {'method': 'adjacent_HS_histogram_heuristic', 'threshold': threshold,
        'fps': fps, 'frames': frame_index, 'duration_seconds': duration, 'cuts': cuts,
        'takes': [{'start_seconds': a, 'end_seconds': b, 'duration_seconds': b-a}
                  for a, b in zip(boundaries, boundaries[1:])], 'human_review_required': True}


def prepare_reference(source, folder, *, start=0.0, width=864, height=480, frames=124, fps=24):
    source = Path(source).resolve(); folder = Path(folder).resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    if frames < 5 or (frames - 5) % 17 or fps != 24:
        raise ValueError('H3 exige grade 17n+5 e 24 FPS.')
    if min(width, height) < 256 or width % 32 or height % 32:
        raise ValueError('Dimensões devem ser múltiplas de 32.')
    info = probe(source)
    duration = frames / fps
    if start < 0 or float(info['format']['duration']) + 1e-3 < start + duration:
        raise ValueError('Referência curta para a janela. Não serão acrescentados freeze, loop ou slow motion.')
    folder.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    key = hashlib.sha256(f'{source_hash}:{start}:{width}:{height}:{frames}:{fps}'.encode()).hexdigest()[:16]
    target = folder / f'reference_{key}.mp4'
    if not target.exists():
        vf = (f'fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,'
              f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
            '-ss', str(start), '-i', str(source), '-vf', vf, '-frames:v', str(frames),
            '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', str(target)],
            check=True, timeout=300)
    check = probe(target)
    v = next(s for s in check['streams'] if s['codec_type'] == 'video')
    if (v['width'], v['height'], int(v.get('nb_frames', 0)), v['r_frame_rate']) != (width, height, frames, '24/1'):
        raise ValueError('A referência preparada não corresponde ao contrato.')
    cuts = detect_cuts(target)
    receipt = {'source': str(source), 'source_sha256': source_hash, 'start_seconds': start,
        'source_audio_preserved_in_original': any(s.get('codec_type') == 'audio' for s in info['streams']),
        'source_audio_in_control': False, 'artifact_role': 'motion_reference_only',
        'reference': str(target), 'sha256': sha256(target), 'width': width, 'height': height,
        'frames': frames, 'fps': fps, 'duration_seconds': duration, 'retimed': False,
        'temporal_sampling': '24fps at original timestamps; no speed change', 'spatial_filter': 'Lanczos contain/pad',
        'cut_analysis': cuts, 'reference_artistic_approval': 'PENDING_HUMAN_REVIEW',
        'sheets': sample_sheet(target, folder / f'reference_{key}', sample_fps=4)}
    folder.joinpath('reference_manifest.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def plan_short_takes(source,folder,max_seconds=124/24):
    """Suggest cut-respecting windows; semantic action boundaries remain reviewable."""
    source=Path(source).resolve();folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    result=detect_cuts(source);windows=[]
    for scene in result['takes']:
        start=scene['start_seconds']
        while start<scene['end_seconds']-1e-3:
            end=min(start+max_seconds,scene['end_seconds'])
            windows.append({'start_seconds':start,'end_seconds':end,'duration_seconds':end-start,
                'status':'SUGGESTED_WINDOW_REVIEW_ACTION_START_CONTACT_AND_RECOVERY',
                'full_diagnostic_124_frames_available':end-start>=124/24-1e-3})
            start=end
    result.update(source=str(source),source_sha256=sha256(source),suggested_windows=windows,
        semantic_action_detection='NOT_AUTOMATICALLY_VERIFIED',automatic_render=False)
    (folder/'plano_takes.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
