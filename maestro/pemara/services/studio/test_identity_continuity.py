import copy
import json
from pathlib import Path
import tempfile
import unittest
from identity_continuity import compile_identity_continuity, validate_candidate_review, digest, IdentityContinuityError
from live_action_workflows import compile_live_action_plan, LiveActionContractError
from test_live_action_workflows import identity_matrix, motion_contract


class IdentityContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'ref.png').write_bytes(b'reference fixture')
        self.ref = {'path': str(self.root/'ref.png'), 'sha256': digest(self.root/'ref.png'), 'role': 'canonical', 'ownerApproved': True, 'approvalEvidence': 'fixture owner decision'}
        self.bible = {'schemaVersion': 'pemara-character-bible@1', 'characters': [{'id': 'fighter_a', 'origin': 'original', 'invariants': ['black forearm protection', 'dirty fabric'], 'references': [self.ref]}]}
        self.save_bible()
        self.state = {'dirt': 2, 'wetness': 2, 'damage': ['left sleeve torn']}
        self.contract = {'bible': {'path': str(self.root/'bible.json'), 'sha256': digest(self.root/'bible.json')}, 'firstTake': True, 'states': {'fighter_a': {'entry': copy.deepcopy(self.state), 'exit': copy.deepcopy(self.state)}}, 'anchorReview': {'status': 'PASS', 'reviewer': 'fixture reviewer', 'notes': 'Compared original and anchor', 'bibleSha256': digest(self.root/'bible.json'), 'artifacts': [self.ref]}}

    def save_bible(self):
        (self.root/'bible.json').write_text(json.dumps(self.bible))

    def compile(self):
        return compile_identity_continuity(self.contract, self.root, {'fighter_a'}, [self.ref])

    def test_evidence_does_not_approve_and_preserves_fixed_identity(self):
        result = self.compile()
        self.assertIn('black forearm protection', result['fixedPromptBlock'])
        self.assertEqual(result['status'], 'EVIDENCE_VALIDATED_NOT_ARTISTIC_APPROVAL')
        self.assertFalse(result['gpuTouched'])

    def test_changed_reference_is_rejected(self):
        (self.root/'ref.png').write_bytes(b'changed')
        with self.assertRaisesRegex(IdentityContinuityError, 'MISSING_OR_CHANGED'): self.compile()

    def test_rejected_reference_is_not_usable(self):
        self.bible['characters'][0]['references'][0]['ownerApproved'] = False
        self.save_bible()
        self.contract['bible']['sha256'] = digest(self.root/'bible.json')
        with self.assertRaisesRegex(IdentityContinuityError, 'CANONICAL_APPROVAL'): self.compile()

    def test_cleaning_requires_cause(self):
        self.contract['states']['fighter_a']['exit']['dirt'] = 0
        with self.assertRaisesRegex(IdentityContinuityError, 'UNEXPLAINED'): self.compile()
        self.contract['states']['fighter_a']['physicalChangeReason'] = 'Cloth washed in visible stream'
        self.compile()

    def test_previous_exit_must_match(self):
        self.contract['firstTake'] = False
        with self.assertRaisesRegex(IdentityContinuityError, 'PREVIOUS_STATE'): self.compile()
        (self.root/'previous.json').write_text(json.dumps({'fighter_a': dict(self.state, dirt=3)}))
        self.contract['previousState'] = {'path': 'previous.json', 'sha256': digest(self.root/'previous.json')}
        with self.assertRaisesRegex(IdentityContinuityError, 'ENTRY_DOES_NOT_MATCH'): self.compile()

    def test_research_required_for_existing_characters(self):
        self.bible['characters'][0]['origin'] = 'existing'
        self.save_bible(); self.contract['bible']['sha256'] = digest(self.root/'bible.json')
        with self.assertRaisesRegex(IdentityContinuityError, 'RESEARCH_BEFORE_ANCHORS'): self.compile()

    def test_review_is_bound_to_bible_and_anchors(self):
        self.contract['anchorReview']['bibleSha256'] = '0'*64
        with self.assertRaisesRegex(IdentityContinuityError, 'STALE_BIBLE'): self.compile()

    def test_research_sources_and_version_uncertainties_are_enforced(self):
        from identity_continuity import validate_research
        research = {'status':'REVIEWED','version':'fixture edition','reviewer':'reviewer','sources':[{'id':'s1','url':'https://example.org/official','title':'fixture','accessedAt':'2026-09-08','versionScope':'fixture edition','kind':'primary'}], 'facts':{topic:{'summary':'fixture researched fact','sourceIds':['s1']} for topic in ['appearance','wardrobeMaterials','combatMechanics','powersAndLimits','personalityAndMovement']},'blockingUnknowns':[],'adaptations':[]}
        char={'origin':'existing','research':research}
        validate_research(char)
        research['blockingUnknowns']=['which costume edition?']
        with self.assertRaisesRegex(IdentityContinuityError,'UNRESOLVED'): validate_research(char)
        research['blockingUnknowns']=[]
        research['facts']['powersAndLimits']['sourceIds']=['unknown']
        with self.assertRaisesRegex(IdentityContinuityError,'TOPIC_WITH_SOURCES'): validate_research(char)

    def test_full_playback_not_inferred_from_three_samples(self):
        r = {'candidate':self.ref,'bibleSha256':'fixture','reviewer':'reviewer','observations':[{'phase':p,'timestampSeconds':i,'notes':'examined'} for i,p in enumerate(['start','middle','end'])], 'dimensions':dict.fromkeys(['identity','combat','physics','lighting','water','realism'],'PASS')}
        self.assertFalse(validate_candidate_review(r,self.root,'fixture')['selectionAllowedByReview'])
        r['fullPlaybackAndContactsReviewed']=True
        self.assertTrue(validate_candidate_review(r,self.root,'fixture')['selectionAllowedByReview'])

    def test_workflow_integration_and_required_missing_contract(self):
        spec = {'workflowId': 'h3_live_action_identity_performance', 'risk': 'normal', 'shotScale': 'close_up', 'engineSelection': 'minimax_h3', 'fallbackAllowed': False, 'identityMatrix': identity_matrix(), 'appearanceReferences': [dict(self.ref, approvalScope='fixture')], 'motionBinding': 'reference_video', 'motionContract': motion_contract(), 'identityContinuityRequired': True}
        with self.assertRaisesRegex(LiveActionContractError, 'IDENTITY_CONTINUITY_REQUIRED'): compile_live_action_plan(spec)
        spec['identityContinuity'] = self.contract
        plan = compile_live_action_plan(spec)
        self.assertIn('black forearm', plan['identityContinuity']['fixedPromptBlock'])
        self.assertFalse(plan['readyForQueue'])
        from unittest.mock import patch
        from live_action_workflows import build_live_action_comfy_graph
        prompt = '\n'.join(str(section) + ': reviewed shot direction' for section in plan['promptContract']['sections'])
        with patch('main._build_minimax_h3_ref2va_workflow', return_value={'fixture': True}) as builder:
            graph = build_live_action_comfy_graph(spec, {'prompt':prompt, 'prefix':'fixture', 'referenceImageNames':['ref.png']})
        self.assertEqual(graph, {'fixture':True})
        compiled = builder.call_args.kwargs['prompt']
        self.assertTrue(compiled.startswith('[FIXED CHARACTER IDENTITY]'))
        self.assertIn('black forearm protection', compiled)
        self.assertIn('[SHOT ACTION AND CAMERA]', compiled)
        self.assertEqual(builder.call_args.kwargs['steps'], plan['qualityProfile']['steps'])

    def test_good_combat_cannot_override_bad_identity(self):
        r = {'candidate': self.ref, 'bibleSha256': 'fixture', 'reviewer': 'human', 'observations': [{'phase': p, 'timestampSeconds': i, 'notes': 'examined'} for i,p in enumerate(['start','middle','end'])], 'dimensions': dict.fromkeys(['identity','combat','physics','lighting','water','realism'],'PASS')}
        r['dimensions']['identity'] = 'FAIL'
        result = validate_candidate_review(r, self.root, 'fixture')
        self.assertFalse(result['selectionAllowedByReview'])
        self.assertFalse(result['ownerApprovalInferred'])


if __name__ == '__main__': unittest.main()
