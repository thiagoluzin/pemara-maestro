import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.planning import director
from creative_os.direction import status,advance,assemble
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class DirectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.submit=Mock(return_value='job')
        self.s=CreativeService(self.tmp.name,self.tmp.name,Bridge(self.submit,lambda _: {'status':'running'},
            lambda:{'engines':{'minimax_h3':{'runnable':True}}},Mock(),Mock()))
        one=sample();two=sample();two['shot_id']='SH02'
        self.shots=[self.s.save_shot(one),self.s.save_shot(two)]
        self.plan=director(self.s,'audit',[s['id'] for s in self.shots])
    def tearDown(self):self.tmp.cleanup()

    def test_order_idempotence_and_human_gate(self):
        current=status(self.s,self.plan['id'])
        self.assertTrue(current['steps'][0]['can_generate'])
        self.assertFalse(current['steps'][1]['can_generate'])
        first=advance(self.s,self.plan['id'],{},'first')
        self.assertEqual(first['id'],advance(self.s,self.plan['id'],{},'first')['id'])
        with self.assertRaises(CreativeError): advance(self.s,self.plan['id'],{},'second')
        with self.assertRaises(CreativeError): assemble(self.s,self.plan['id'],'assembly')
        self.submit.assert_called_once()

    def test_changed_ir_invalidates_plan(self):
        ir=sample();ir['content']['action']['primary']='another intent'
        self.s.save_shot(ir,self.shots[0]['revision'])
        with self.assertRaises(CreativeError):advance(self.s,self.plan['id'],{},'new')
        self.submit.assert_not_called()

    def test_scoped_history_is_not_hidden_by_other_projects(self):
        first=advance(self.s,self.plan['id'],{},'first')
        with self.s.store.transaction() as con:
            for i in range(501):self.s.store.write(con,'generations',f'other{i}',{'shot_id':'other','status':'done'},create=True)
        self.assertEqual(status(self.s,self.plan['id'])['steps'][0]['generation_id'],first['id'])
        with self.assertRaises(CreativeError):advance(self.s,self.plan['id'],{},'repeat')
