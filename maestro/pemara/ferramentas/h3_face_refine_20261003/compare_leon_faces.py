"""CPU before/after face sheets using the actual refine report's tracked boxes."""
import argparse
import json
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument('original', type=Path)
p.add_argument('refined', type=Path)
p.add_argument('report', type=Path)
p.add_argument('--qc', type=Path, required=True)
args = p.parse_args()
report = json.loads(args.report.read_text(encoding='utf-8'))
boxes = {}
for track in report['tracks']:
    start = track['source_start']
    valid = track['valid_source_frames']
    for item in track['plan']['frames']:
        index = item['frame_index']
        if index < valid and item.get('source_face_box_xyxy'):
            boxes.setdefault(start + index, item['source_face_box_xyxy'])
caps = [cv2.VideoCapture(str(path)) for path in (args.original, args.refined)]
if not all(cap.isOpened() for cap in caps):
    raise RuntimeError('Both native source files must be readable')
if not boxes:
    raise RuntimeError('No tracked human face boxes to review')
args.qc.mkdir(exist_ok=True)
paths = []
for page in range(3):
    sheet = Image.new('RGB', (1024, 1450), '#111111')
    draw = ImageDraw.Draw(sheet)
    for slot in range(10):
        seconds = page * 10 + slot
        index = seconds * 24
        nearest = min(boxes, key=lambda value: abs(value-index))
        x, y = (slot % 2) * 512, (slot // 2) * 290
        draw.text((x+5, y+260), f'{seconds:02d}s | ORIGINAL / FACE REFINE', fill='white')
        if abs(nearest-index) > 12:
            draw.text((x+5, y+120), 'No nearby tracked face: inspect full frame', fill='orange')
            continue
        box = boxes[nearest]
        cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
        edge = max(box[2]-box[0], box[3]-box[1]) * 1.5
        for side, cap in enumerate(caps):
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f'Missing real frame {index}')
            height, width = frame.shape[:2]
            left, top = max(0, int(cx-edge/2)), max(0, int(cy-edge/2))
            right, bottom = min(width, int(cx+edge/2)), min(height, int(cy+edge/2))
            crop = Image.fromarray(cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2RGB))
            crop.thumbnail((256, 256), Image.Resampling.LANCZOS)
            sheet.paste(crop, (x + side*256 + (256-crop.width)//2, y+(256-crop.height)//2))
    path = args.qc / f'face_before_after_{page+1:02d}.jpg'
    sheet.save(path, quality=95)
    paths.append(str(path))
for cap in caps:
    cap.release()
print(json.dumps({'sheets': paths, 'review': 'visual comparison only; no automatic identity approval'}))
