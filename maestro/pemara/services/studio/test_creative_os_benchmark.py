import tempfile
import unittest
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.routing import route
from test_creative_os_ir import sample


class BenchmarkTests(unittest.TestCase):
    def test_revoked_owner_verdict_is_not_cached_as_approval(self):
        with tempfile.TemporaryDirectory() as d:
            s=CreativeService(d,d,Bridge(Mock(),Mock(),Mock(),Mock(),Mock()))
            s.store.put('generations',{'human_verdict':'approved','provenance':{'workflow_hash':'hash'}},entity_id='g')
            s.store.put('benchmarks',{'generation_id':'g','config_hash':'hash','human_approved':True})
            self.assertTrue(s.benchmark_history()[0]['human_approved'])
            s.store.put('generations',{'human_verdict':'rejected','provenance':{'workflow_hash':'hash'}},entity_id='g',create=False)
            self.assertFalse(s.benchmark_history()[0]['human_approved'])

    def test_repeated_seed_does_not_qualify_adaptation(self):
        ir=sample(); signature=route(ir,{})['signature']
        rows=[{'generation_id':str(i),'engine_id':'minimax_h3','config_hash':'hash','signature':signature,'human_approved':True,'seed':1} for i in range(3)]
        result=route(ir,{},rows)
        self.assertFalse(any('LOCAL_REVIEWED_HISTORY' in r['reason_codes'] for r in result['recommendations']))
