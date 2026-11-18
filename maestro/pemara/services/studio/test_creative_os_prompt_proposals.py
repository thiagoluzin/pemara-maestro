import tempfile
import unittest
from unittest.mock import Mock
from creative_os.service import CreativeService
from creative_os.prompt_proposals import propose, review, apply
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class PromptProposalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bridge = Mock()
        self.s = CreativeService(self.tmp.name, self.tmp.name, self.bridge)
        self.shot = self.s.save_shot(sample())
        self.p = propose(self.s, self.shot['id'], 'Reviewed scene description', {'prompt_id':'test-only'})

    def tearDown(self): self.tmp.cleanup()

    def test_requires_exact_review_and_preserves_original(self):
        with self.assertRaises(CreativeError): apply(self.s, self.p['id'])
        with self.assertRaises(CreativeError): review(self.s, self.p['id'], 'approved', 'wrong')
        review(self.s, self.p['id'], 'rejected', self.p['suggestion_hash'])
        with self.assertRaises(CreativeError): apply(self.s, self.p['id'])
        self.assertEqual(self.s.store.get('shots',self.shot['id'])['ir'],self.shot['ir'])
        self.assertFalse(self.bridge.mock_calls)

    def test_apply_is_atomic_idempotent_and_preserves_engine_and_locks(self):
        review(self.s, self.p['id'], 'approved', self.p['suggestion_hash'])
        applied = apply(self.s, self.p['id'])
        self.assertEqual(apply(self.s, self.p['id']),applied)
        current=self.s.store.get('shots',self.shot['id'])
        self.assertEqual(current['ir']['generation'],self.shot['ir']['generation'])
        self.assertEqual(current['ir'].get('constraints'),self.shot['ir'].get('constraints'))
        self.assertEqual(len(self.s.store.history('shots',self.shot['id'])),2)
        self.assertFalse(self.bridge.mock_calls)

    def test_changed_shot_blocks_stale_rewrite(self):
        review(self.s, self.p['id'], 'approved', self.p['suggestion_hash'])
        ir=self.shot['ir']; ir['content']['description']='New owner direction'
        self.s.save_shot(ir,self.shot['revision'])
        with self.assertRaises(CreativeError): apply(self.s,self.p['id'])
        self.assertFalse(self.bridge.mock_calls)
