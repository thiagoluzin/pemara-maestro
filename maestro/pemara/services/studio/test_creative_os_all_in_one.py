import unittest
from creative_os.all_in_one import build
from creative_os.adapters import H3Adapter
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class AllInOneTests(unittest.TestCase):
    def test_headless_template_expansion_has_real_sampler(self):
        result=build(prompt='Leaves sway',seed=42)
        self.assertTrue(result['headless_expansion'])
        types=[n['class_type'] for n in result['graph'].values()]
        self.assertIn('SamplerCustomAdvanced',types);self.assertNotIn('H3OneNode',types)
        self.assertEqual(result['graph']['9']['inputs']['steps'],10)
        self.assertNotIn('audio',result['graph']['14']['inputs'])

    def test_first_last_map_to_correct_native_inputs(self):
        result=build(prompt='Cube slides',seed=42,first_frame='safe/first.png',last_frame='safe/last.png')
        graph=result['graph'];self.assertEqual(result['mode'],'i2v')
        self.assertEqual(graph['6']['inputs']['first_frame'],['200',0])
        self.assertEqual(graph['6']['inputs']['last_frame'],['201',0])
        self.assertEqual(graph['200']['inputs']['image'],'safe/first.png')
        self.assertNotIn('4',graph)
        with self.assertRaises(CreativeError):build(prompt='Cube',seed=42,first_frame='../escape.png')

    def test_explicit_adapter_never_changes_engine_or_profile(self):
        ir=sample();native=H3Adapter().build_job(ir,{'seed':42})
        expanded=H3Adapter().build_job(ir,{'seed':42,'h3_adapter':'all_in_one'})
        self.assertTrue(expanded.pop('creative_all_in_one'));self.assertEqual(native,expanded)
        ir['generation']['native_audio']=True
        with self.assertRaises(CreativeError):H3Adapter().build_job(ir,{'seed':42,'h3_adapter':'all_in_one'})
