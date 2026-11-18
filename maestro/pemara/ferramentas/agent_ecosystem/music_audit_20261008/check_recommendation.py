"""Offline reproduction of candidate gating, without music generation or edits."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path('E:/Pemara/maestro/pemara')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'services/studio'))
from music_ai_production import _rank
from music_ai_audio import qc_report

candidates = [
    {'index': index, 'qc': {'technicalPass': False}, 'critic': {
        'muqMulanPromptSimilarity': 0.5,
        'muqEvalMusicalImpression': 4.0,
        'melodySimilarity': 0.9, 'rhythmSimilarity': 0.9,
        'instrumentAudibility': {'bass': 0.2, 'drums': 0.2},
        'orchestralMetalBalance': 0.2,
    }} for index in (1, 2)
]
_rank(candidates, ('bass', 'drums'))
metrics = {'durationSeconds': 180.0, 'sampleRate': 48000, 'channels': 2,
           'clippingSampleCount': 0, 'samplePeakDbfs': -1.0}
with patch('music_ai_audio.subprocess.run') as process, \
     patch('music_ai_audio.sample_metrics', return_value=metrics), \
     patch('music_ai_audio.loudness_metrics', return_value={
         'integratedLufs': -13.0, 'truePeakDbfs': 0.4}):
    process.return_value.returncode = 0
    result = qc_report(Path('synthetic_gate_input.wav'), 'ffmpeg', 180.0)
report = {'scope': 'Synthetic, offline logic probes; no audio was generated.',
          'all_failed_candidates': candidates,
          'failed_candidate_is_recommended': any(c['recommended'] for c in candidates),
          'positive_true_peak_qc': result,
          'positive_true_peak_passes': result['technicalPass']}
(HERE / 'gate_reproductions.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in (
    'failed_candidate_is_recommended', 'positive_true_peak_passes')}))
