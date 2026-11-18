"""Actual CPU score/voice/master test using synthetic local fixtures only."""
from pathlib import Path
import sys
import shutil
import json
import uuid
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'services/studio'))
from music_score_first import (ScoreTranscriptionRequest, LockedScoreOrchestrationRequest,
                              run_score_transcription, run_locked_score_orchestration)
from music_reinstrument import sha256_file
HERE = Path(__file__).resolve().parent
job = HERE / 'cpu_fixtures' / ('score_roundtrip_' + uuid.uuid4().hex[:8])
(job / 'source').mkdir(parents=True)
source = job / 'source' / 'original.wav'
shutil.copy2(HERE / 'cpu_fixtures/guitar_di_candidate.wav', source)
vocal = job / 'source' / 'vocal_fixture.wav'
shutil.copy2(source, vocal)
score = HERE / 'cpu_fixtures/guitar_fixture.mid'
before = sha256_file(source)
qwen_fixture = {'sourceSha256': before, 'writer_model': 'deterministic_test_fixture',
    'sectionEvidence': 'fixture', 'plan': {'duration_seconds': 6, 'bpm': 120,
    'style': 'traditional heavy metal technical fixture', 'tracks': {
        'guitar': {'gainDb': -3, 'density': .8, 'velocityScale': 1, 'role': 'rhythm'}},
    'sections': [{'name': 'verse', 'start': 0, 'end': 3, 'energy': .4, 'lead': 'vocals', 'instruments': ['guitar']},
                 {'name': 'chorus', 'start': 3, 'end': 6, 'energy': 1, 'lead': 'guitar', 'instruments': ['guitar']}]}}
def progress(value, message): print(f'{value}% {message}', flush=True)
phase_one = run_score_transcription(ScoreTranscriptionRequest(source_path=source, output_dir=job,
    original_name='technical-fixture.wav', preset='traditional_heavy_metal', instruments=('guitar',),
    supplied_score_path=score, keep_vocals=True, supplied_vocal_path=vocal, qwen_plan=qwen_fixture),
    progress=progress, ffmpeg=shutil.which('ffmpeg'), ffprobe=shutil.which('ffprobe'))
assert phase_one['technicalPass'], phase_one['score']
score_artifact = next(a for a in phase_one['artifacts'] if a['key'] == 'scoreMidi')
locked = job / score_artifact['relativePath']
voice = phase_one['vocalPreservation']
phase_two = run_locked_score_orchestration(LockedScoreOrchestrationRequest(source_path=source,
    score_path=locked, score_sha256=phase_one['scoreSha256'], output_dir=job,
    original_name='technical-fixture.wav', preset='traditional_heavy_metal', instruments=('guitar',),
    keep_vocals=True, vocal_path=Path(voice['path']), vocal_sha256=voice['sha256'], derive_accompaniment=False,
    qwen_plan=qwen_fixture),
    progress=progress, ffmpeg=shutil.which('ffmpeg'), ffprobe=shutil.which('ffprobe'))
receipt = {'sourceUnchanged': before == sha256_file(source), 'scoreReviewSimulation': 'synthetic_fixture_only',
    'artisticApproval': False, 'phaseOne': phase_one, 'phaseTwo': phase_two}
(HERE / 'score_roundtrip_verification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
assert phase_two['qc']['technicalPass'], phase_two['qc']
assert receipt['sourceUnchanged']
print(json.dumps({'pass': True, 'status': phase_two['status'], 'voiceHashUnchanged': phase_two['vocalPreservation']['assetUnchanged']}), flush=True)
