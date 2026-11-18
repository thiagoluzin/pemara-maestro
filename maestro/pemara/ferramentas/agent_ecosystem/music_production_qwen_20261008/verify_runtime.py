"""CPU-only fixtures; this does not generate the owner's pilot song."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import shutil
import struct
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'services/studio'))
from music_score_first import runtime_paths, build_sfizz_render_command
from music_reinstrument import build_stem_polish_command
from music_ai_audio import sample_metrics, sha256_file
import music_creation

HERE = Path(__file__).resolve().parent
OUT = HERE / 'cpu_fixtures'
OUT.mkdir(exist_ok=True)
paths = runtime_paths()
midi_path = OUT / 'guitar_fixture.mid'
def vlq(value):
    result = [value & 127]
    value >>= 7
    while value:
        result.insert(0, (value & 127) | 128)
        value >>= 7
    return bytes(result)
track = bytearray(b'\x00\xff\x51\x03\x07\xa1\x20')
track_name = b'Original technical guitar fixture for Maestro roundtrip validation'
track.extend(b'\x00\xff\x03' + vlq(len(track_name)) + track_name + b'\x00\xc0\x1b')
for pitch in (40, 47, 52, 64):
    track.extend(bytes((0, 0x90, pitch, 90)))
    track.extend(vlq(960) + bytes((0x80, pitch, 0)))
track.extend(vlq(1920) + b'\xff\x2f\x00')
midi_path.write_bytes(b'MThd' + struct.pack('>IHHH', 6, 0, 1, 480)
                      + b'MTrk' + struct.pack('>I', len(track)) + track)
raw, polished = OUT / 'guitar_di_raw.wav', OUT / 'guitar_di_candidate.wav'
results = []
for command in (build_sfizz_render_command(paths, midi=midi_path, output_wav=raw, patch=paths['sampled_guitar']),
    build_stem_polish_command(shutil.which('ffmpeg'), raw, polished, instrument='guitar',
                             gain_db=-3, calibration_db=0, duration=6, di_guitar=True)):
    run = subprocess.run(command, capture_output=True, text=True, timeout=180)
    results.append({'returncode': run.returncode, 'stderrTail': run.stderr[-3000:]})
    if run.returncode: raise RuntimeError(run.stderr[-2000:])
metrics = sample_metrics(polished)
assert metrics['clippingSampleCount'] == 0 and metrics['nonFiniteSampleCount'] == 0
assert metrics['samplePeakDbfs'] is not None and metrics['samplePeakDbfs'] > -40
receipt = {'technicalFixturePass': True, 'artisticApproval': False,
    'library': 'FreePats FSBS Electric Guitar Direct', 'license': 'CC0-1.0',
    'source': 'https://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html',
    'patch': str(paths['sampled_guitar']), 'patchSha256': sha256_file(paths['sampled_guitar']),
    'archiveSha256': '7ab2a4551bb8847342d6fd10cc56e0642fcaf43f3be8d665269c4dc9bfbbd599',
    'processing': 'declared_saturation_and_EQ_not_captured_amp', 'metrics': metrics,
    'fixtureMidiSha256': sha256_file(midi_path), 'commands': results}
(HERE / 'guitar_qualification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
args = dict(prompt='original traditional heavy metal, natural ending', lyrics='[verse]\nOriginal test',
            instrumental=False, duration=30, seed=123, prefix='audio/QwenProductionValidation',
            music_abc='X:1\nT:Fixture\nM:4/4\nL:1/4\nQ:1/4=120\nK:Em\nE4|E4|]')
for action in ('plan', 'generate'):
    graph = music_creation.yue_workflow(**args, music_action=action)
    (HERE / f'yue_{action}_validation.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'guitarFixture': metrics, 'workflowFilesPrepared': 2}))
