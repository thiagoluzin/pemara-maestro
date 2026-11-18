"""Register the approved local test and its eventual candidate, without submitting jobs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'services/studio'))
from services.studio import video_projects as projects

PROJECTS = ROOT / 'ferramentas/video_global_engine/projetos'
PROJECT_ID = 're2_1998_leon_first_licker_face_refine_30s_v1'
PROJECT = PROJECTS / PROJECT_ID

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', action='store_true')
    args = parser.parse_args()
    request = read(PROJECT / 'production_request.json')
    submission = read(PROJECT / request.get('activeSubmission', 'submission_attempt01.json'))
    now = datetime.now(timezone.utc).isoformat()
    manifest_path = PROJECT / 'project_manifest.json'
    queue_path = PROJECT / 'take_queue.json'
    if not manifest_path.exists() and not queue_path.exists():
        for folder in projects.PROJECT_DIRS:
            (PROJECT / folder).mkdir(exist_ok=True)
        manifest = {
            'schema_version': '1.1', 'project_id': PROJECT_ID,
            'title': request['title'],
            'objective': 'Take continuo de 30 segundos: Leon descobre o primeiro Licker no RPD de RE2 1998, em live action. Audio nativo MiniMax H3; Face Refine no rosto humano. Sem disparo ou desfecho de combate.',
            'duration_target_seconds': 30, 'preview_resolution': '1344x768',
            'final_resolution': '1344x768', 'fps_preview': 24, 'fps_final': 24,
            'created_at': now, 'updated_at': now, 'maestro_status': 'IN_PROGRESS',
            'take_queue': 'take_queue.json', 'audio': {'music_provider': None, 'voice_provider': None},
            'distribution_intent': {'enabled': False, 'reason': 'local_review_only', 'platforms': []},
            'identity_continuity_required': True,
            'anchor_approval': request['anchorApproval'],
            'external_render': {'provider': 'comfyui-local MCP', 'prompt_id': submission['prompt_id'],
                                'status': 'RUNNING', 'backend_auto_resume': False},
        }
        def anchor(index):
            record = request['anchors'][index]
            return {'file': str(Path(record['path']).relative_to(PROJECT)),
                    'sha256': record['sha256'], 'status': 'approved_for_video',
                    'approval_evidence': request['anchorApproval']}
        take = {
            'id': 'T01', 'name': 'Leon encontra o primeiro Licker',
            'target_duration_seconds': 30, 'take_mode': 'PRECISION',
            'maestro_status': 'IN_PRODUCTION',
            'notes': 'Render externo MCP em andamento. Aprovacao recebida somente para as ancoras e o encontro. Video ainda sera revisado.',
            'characters': ['Leon S. Kennedy', 'Licker'],
            'base_image': anchor(0), 'end_image': anchor(1),
            'animation_prompt': (PROJECT / 'prompt_h3.txt').read_text(encoding='utf-8'),
            'video_generation': {
                'profile': projects.MINIMAX_H3_OWNER_30S_NATIVE_AV_PROFILE, 'backend': 'comfy_core_minimax_h3_nodes',
                'quality_profile': 'h3_master', 'width': 1344, 'height': 768, 'fps': 24,
                'frames': 736, 'steps': 20, 'native_audio': True,
                'start_end_frame_enabled': True, 'require_approved_end_frame': True,
                'fallback_allowed': False, 'maestro_job_enabled': False,
                'face_refine': {'enabled': True, 'steps': 12, 'denoise': .45, 'canvas': 512, 'detector': 'human'},
            },
            'shot_contract': {'human_visibility_contract': {'allowed_humans': ['Leon S. Kennedy'],
                               'allowed_non_humans': ['Licker']}},
            'identity_continuity': request['identityContinuity'],
            'video': {'status': 'running', 'external_prompt_id': submission['prompt_id']},
            'audio_direction': {'native_audio': True, 'delivery_required': True, 'human_listening_required': True},
            'qc': {'status': 'waiting_for_render', 'human_approved': False},
        }
        queue = {'schema_version': '1.1', 'project_id': PROJECT_ID,
                 'methodology': 'owner_requested_single_continuous_h3_take', 'status': 'in_production',
                 'assembly': {'preview': {'width': 1344, 'height': 768, 'fps': 24, 'format': 'mp4'},
                              'final': {'width': 1344, 'height': 768, 'fps': 24, 'format': 'mp4'},
                              'rule': 'single_30_second_take_explicitly_requested_by_owner'},
                 'takes': [take]}
        projects._atomic_json_write(manifest_path, manifest)
        projects._atomic_json_write(queue_path, queue)
    elif not manifest_path.exists() or not queue_path.exists():
        raise RuntimeError('Partial project registration: preserve and reconcile before writing.')
    if args.candidate:
        delivery = read(PROJECT / 'delivery_candidate.json')
        if delivery.get('faceRefine', {}).get('applied') is not True:
            raise ValueError('Face Refine requested but no successful execution receipt')
        target = Path(delivery['delivery']['path'])
        take = projects.set_take_generation_state(
            PROJECTS, PROJECT_ID, 'T01', status='READY', job_id=submission['prompt_id'],
            result={'provider': 'MiniMax H3', 'native_prompt_id': submission['prompt_id'],
                    'face_refine': delivery['faceRefine']['applied'],
                    'face_refine_receipt': delivery['faceRefine'], 'delivery_receipt': 'delivery_candidate.json',
                    'audio_delivery': {'status': 'NATIVE_H3_ATTACHED_PENDING_HUMAN_REVIEW',
                                       'ready': True, 'required': True, 'human_listening_required': True,
                                       'human_approved': False}}, preview_path=target)
        manifest = read(manifest_path)
        manifest['external_render']['status'] = 'COMPLETED'
        manifest['updated_at'] = now
        projects._atomic_json_write(manifest_path, manifest)
        readiness = projects.get_project_assembly_readiness(PROJECTS, PROJECT_ID)
        record = dict(file=str(target), sha256=delivery['delivery']['sha256'],
                      duration_seconds=30, width=1344, height=768, fps=24,
                      technical_review=delivery['checks'])
        candidate = projects.register_project_candidate_output(
            PROJECTS, PROJECT_ID, expected_source_fingerprint=readiness['sourceFingerprint'],
            expected_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(), record=record)
        print(json.dumps({'take': {'id': take['takeId'], 'status': take['status']}, 'candidate': candidate}, ensure_ascii=False))
    else:
        view = projects.project_view(PROJECT)
        print(json.dumps({'id': PROJECT_ID, 'title': view.get('name'), 'counts': view['takeCounts'],
                          'render': submission['prompt_id'], 'auto_resume': False}, ensure_ascii=False))

if __name__ == '__main__':
    main()
