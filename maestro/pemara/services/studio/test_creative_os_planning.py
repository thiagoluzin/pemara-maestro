import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.planning import repair_plan,execute_repair,save_bible,director,continuity
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.submit=Mock(return_value='job1')
        self.s=CreativeService(self.tmp.name,self.tmp.name,Bridge(self.submit,lambda _: {'status':'done','result':{}},
            lambda:{'engines':{'minimax_h3':{'runnable':True}}},Mock(),Mock()))
        self.shot=self.s.save_shot(sample())
        self.parent=self.s.generate(self.shot['id'],{},'original')
        self.s.sync(self.parent['id'])
    def tearDown(self): self.tmp.cleanup()

    def test_repair_child_and_budget(self):
        repair=repair_plan(self.s,self.parent['id'],{'reason':'more visible movement'})
        result=execute_repair(self.s,repair['id'])
        child=self.s.store.get('generations',result['child_generation_id'])
        self.assertEqual(child['parent_generation_id'],self.parent['id'])
        self.assertEqual(child['engine_id'],self.parent['engine_id'])
        execute_repair(self.s,repair['id']); self.assertEqual(self.submit.call_count,2)
        second=repair_plan(self.s,self.parent['id'],{'reason':'again'})
        with self.assertRaises(CreativeError): execute_repair(self.s,second['id'])

    def test_no_automatic_engine_escalation(self):
        ir=sample();ir['generation']['preferred_engine']='ltx25'
        with self.assertRaises(CreativeError): repair_plan(self.s,self.parent['id'],{'reason':'change','ir':ir})
        with self.assertRaises(CreativeError): repair_plan(self.s,self.parent['id'],{'reason':'retake','strategy':'ltx_retake'})

    def test_bible_revision_and_direction_no_submit(self):
        first=save_bible(self.s,'audit','character','hero',{'immutable':['face']})
        with self.assertRaises(CreativeError): save_bible(self.s,'audit','character','hero',{})
        second=save_bible(self.s,'audit','character','hero',{'immutable':['face','body']},first['revision'])
        self.assertEqual(second['revision'],2)
        plan=director(self.s,'audit',[self.shot['id']])
        self.assertFalse(plan['auto_submit']);self.assertEqual(self.submit.call_count,1)

    def test_unknown_continuity_is_not_pass(self):
        result=continuity(self.s,self.parent['id'],self.parent['id'])
        self.assertEqual(result['decision'],'PENDING_HUMAN_REVIEW')
        self.assertTrue(all(v['state']=='unmeasured' for v in result['dimensions'].values()))
