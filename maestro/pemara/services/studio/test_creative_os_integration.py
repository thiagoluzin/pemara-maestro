import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from creative_os.integration import archive_workflow,export_graph
from creative_os.ir import CreativeError


class IntegrationTests(unittest.TestCase):
    def test_native_h3_retains_video_latent_without_changing_sampling(self):
        import copy
        graph = {
            '6':{'class_type':'MiniMaxH3ImageToVideo','inputs':{'prompt':'original'}},
            '11':{'class_type':'SamplerCustomAdvanced','inputs':{'seed':13}},
            '12':{'class_type':'LTXVSeparateAVLatent','inputs':{'av_latent':['11',0]}},
            '16':{'class_type':'SaveVideo','inputs':{'filename_prefix':'owner/shot'}}}
        before=copy.deepcopy(graph)
        changed=export_graph(graph,{})
        added=[n for n in changed.values() if n['class_type']=='SaveLatent']
        self.assertEqual(len(added),1)
        self.assertEqual(added[0]['inputs']['samples'],['12',0])
        self.assertEqual(graph,before)
        self.assertTrue(all(changed[k] == v for k,v in graph.items()))
        self.assertEqual(export_graph(changed,{}),changed)
        graph['6']['class_type']='LTXVConditioning'
        self.assertEqual(export_graph(graph,{}),graph)

    def test_effective_graph_provenance_and_legacy_exporter(self):
        graph={'1':{'class_type':'SaveVideo','inputs':{'format':'mp4','codec':'h264'}}}
        schema={'SaveVideo':{'input':{'required':{'format':['COMFY_DYNAMICCOMBO_V3',{}]}}}}
        changed=export_graph(graph,schema)
        self.assertEqual(changed['1']['inputs']['format.codec'],'h264')
        self.assertEqual(export_graph(graph,{}),graph)
        with tempfile.TemporaryDirectory() as d:
            a=archive_workflow(d,'prompt',changed)
            self.assertEqual(archive_workflow(d,'prompt',changed),a)
            with self.assertRaises(CreativeError): archive_workflow(d,'prompt',graph)

    def test_new_routes_inherit_studio_security(self):
        import main
        client=TestClient(main.app)
        with patch.object(main,'_comfy_request',side_effect=AssertionError('No live Comfy calls in test')):
            self.assertEqual(client.get('/api/creative/health').status_code,403)
            with patch.object(main,'_is_internal_request',return_value=True),patch.object(main,'_browser_origin_allowed',return_value=True):
                response=client.get('/api/creative/health')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['codex_transport'],'mcp_only')
