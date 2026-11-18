"""CPU-only dense review sheets and motion observations for the completed candidate."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('video', type=Path)
    parser.add_argument('--qc', type=Path, required=True)
    args = parser.parse_args()
    args.qc.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError('Cannot open candidate')
    fps = cap.get(cv2.CAP_PROP_FPS)
    if abs(fps-24)>.001:
        raise ValueError('Review expects actual 24 FPS')
    count = 0
    previous = None
    differences = []
    sheets = []
    sheet = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.cvtColor(cv2.resize(frame, (160, 92)), cv2.COLOR_BGR2GRAY)
        if previous is not None:
            differences.append(float(np.abs(small.astype(np.float32)-previous.astype(np.float32)).mean()))
        previous = small
        if count % 6 == 0:
            sampled = count // 6
            within = sampled % 30
            if within == 0:
                sheet = Image.new('RGB', (1920, 1040), '#111111')
            thumb = Image.fromarray(cv2.cvtColor(cv2.resize(frame, (320, 183)), cv2.COLOR_BGR2RGB))
            x, y = within % 6 * 320, within // 6 * 208
            sheet.paste(thumb, (x,y))
            ImageDraw.Draw(sheet).text((x+6,y+185), f'frame {count:03d} | {count/fps:05.2f} s', fill='white')
            if within == 29:
                path = args.qc / f'motion_sheet_{sampled//30+1:02d}.jpg'
                sheet.save(path, quality=92)
                sheets.append(str(path))
        count += 1
    cap.release()
    if count != 720:
        raise ValueError(f'Actual decoded frame count is {count}, expected 720')
    low_ranges = []
    start = None
    for index, value in enumerate(differences + [999.0], start=1):
        if value < .02 and start is None:
            start = index-1
        if value >= .02 and start is not None:
            if index-start >= 24:
                low_ranges.append({'start_frame': start, 'end_frame': index-1,
                                   'seconds': (index-start)/fps})
            start = None
    report = {'decoded_frames': count, 'fps': fps,
              'mean_luma_frame_difference_0_255': float(np.mean(differences)),
              'max_luma_frame_difference_0_255': float(np.max(differences)),
              'possible_low_motion_ranges': low_ranges,
              'large_change_frames': [i+1 for i,v in enumerate(differences) if v>35],
              'dense_review_sheets': sheets, 'sample_interval_seconds': .25,
              'observations_only': True, 'identity_verified': False,
              'human_approved': False,
              'limitations': 'Metrics flag review points; they do not certify natural motion, facial identity, or artistic quality.'}
    (args.qc / 'motion_observations.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
