"""Read-only audio signal screening. NO_FLAGS is not listening or artistic approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf


def screen_blocks(blocks, sample_rate: int, *, near_silence_dbfs: float = -65,
                  min_quiet_seconds: float = 5, min_seconds: float | None = None,
                  max_seconds: float | None = None) -> dict:
    if sample_rate <= 0 or not math.isfinite(near_silence_dbfs) or near_silence_dbfs >= 0:
        raise ValueError('Invalid rate or silence threshold')
    if not math.isfinite(min_quiet_seconds) or min_quiet_seconds <= 0:
        raise ValueError('min_quiet_seconds must be positive')
    for bound in (min_seconds, max_seconds):
        if bound is not None and (not math.isfinite(bound) or bound < 0):
            raise ValueError('Invalid duration limit')
    if min_seconds is not None and max_seconds is not None and min_seconds > max_seconds:
        raise ValueError('Minimum exceeds maximum')
    frames = clipped = nonfinite = 0
    channels = None
    previous = None
    windows, quiet, jumps = [], [], []
    quiet_start = None
    threshold = 10 ** (near_silence_dbfs / 20)
    for block in blocks:
        data = np.asarray(block, dtype=np.float64)
        if data.ndim == 1:
            data = data[:, None]
        if data.ndim != 2 or not len(data):
            raise ValueError('Expected nonempty frame/channel blocks')
        if channels is None:
            channels = data.shape[1]
        if not channels or data.shape[1] != channels:
            raise ValueError('Channel layout changed')
        start = frames / sample_rate
        frames += len(data)
        end = frames / sample_rate
        nonfinite += int((~np.isfinite(data)).sum())
        clean = np.nan_to_num(data, nan=0, posinf=0, neginf=0)
        rms = float(np.sqrt(np.mean(np.square(clean))))
        peak = float(np.max(np.abs(clean)))
        clipped += int((np.abs(clean) >= .9999).sum())
        windows.append({'start': start, 'end': end, 'rms': rms, 'sample_peak': peak})
        if rms < threshold:
            if quiet_start is None:
                quiet_start = start
        elif quiet_start is not None:
            if start - quiet_start >= min_quiet_seconds:
                quiet.append({'start': quiet_start, 'end': start})
            quiet_start = None
        if previous is not None and len(jumps) < 20 and np.max(np.abs(clean[0] - previous)) > .8:
            jumps.append(start)
        delta = np.max(np.abs(np.diff(clean, axis=0)), axis=1)
        for index in np.flatnonzero(delta > .8)[:max(0, 20 - len(jumps))]:
            jumps.append(start + (int(index) + 1) / sample_rate)
        previous = clean[-1]
    duration = frames / sample_rate
    if quiet_start is not None and duration - quiet_start >= min_quiet_seconds:
        quiet.append({'start': quiet_start, 'end': duration})
    failures = []
    if not frames:
        failures.append('EMPTY_AUDIO')
    if nonfinite:
        failures.append('NONFINITE_SAMPLES')
    if min_seconds is not None and duration < min_seconds:
        failures.append('BELOW_REQUESTED_MINIMUM')
    if max_seconds is not None and duration > max_seconds:
        failures.append('ABOVE_REQUESTED_MAXIMUM')
    flags = []
    if quiet:
        flags.append('SUSTAINED_NEAR_SILENCE')
    if clipped:
        flags.append('SAMPLES_AT_DIGITAL_LIMIT')
    if jumps:
        flags.append('POSSIBLE_DISCONTINUITIES')
    return {'screening_status': 'TECHNICAL_FAIL' if failures else 'REVIEW_REQUIRED' if flags else 'NO_FLAGS',
            'failures': failures, 'review_flags': flags, 'duration_seconds': duration,
            'frames': frames, 'sample_rate': sample_rate, 'channels': channels,
            'nonfinite_samples': nonfinite, 'samples_at_digital_limit': clipped,
            'near_silence_intervals': quiet, 'possible_jump_times_first_20': jumps,
            'rms_windows': windows, 'near_silence_dbfs': near_silence_dbfs,
            'min_quiet_seconds': min_quiet_seconds, 'audio_listened': False, 'artistic_approval': False,
            'limitation': 'Signal screening only. Intentional pauses, distortion and transients require review. True peak, full decode verification and listening remain separate.'}


def screen_file(path: Path, **kwargs) -> dict:
    with sf.SoundFile(path) as source:
        expected_frames = source.frames
        result = screen_blocks(source.blocks(blocksize=max(1, source.samplerate // 2),
                                             dtype='float32', always_2d=True), source.samplerate, **kwargs)
    if result['frames'] != expected_frames:
        result['failures'].append('INCOMPLETE_DECODE')
        result['screening_status'] = 'TECHNICAL_FAIL'
    with path.open('rb') as handle:
        result['sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest()
    result['artifact_path'] = str(path.resolve())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--min-seconds', type=float)
    parser.add_argument('--max-seconds', type=float)
    parser.add_argument('--near-silence-dbfs', type=float, default=-65)
    parser.add_argument('--min-quiet-seconds', type=float, default=5)
    args = parser.parse_args()
    if args.audio.resolve() == args.out.resolve():
        parser.error('Output must not overwrite source audio')
    result = screen_file(args.audio, min_seconds=args.min_seconds, max_seconds=args.max_seconds,
                         near_silence_dbfs=args.near_silence_dbfs, min_quiet_seconds=args.min_quiet_seconds)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('screening_status', 'duration_seconds', 'review_flags', 'failures')}))
    if result['failures']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
