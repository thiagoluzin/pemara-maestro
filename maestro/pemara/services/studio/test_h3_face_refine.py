from copy import deepcopy
import unittest
from h3_face_refine import NODE, SAGE, SAGE_GUARD, ensure_face_refine


def source(kind="MiniMaxH3ImageToVideo", model="minimax_h3_fl2va_pruned_int8_convrot.safetensors"):
    return {"1":{"class_type":"UNETLoader","inputs":{"unet_name":model}},
        "2":{"class_type":"CLIPLoader","inputs":{}},"3":{"class_type":"VAELoader","inputs":{}},
        "4":{"class_type":kind,"inputs":{"clip":["2",0],"vae":["3",0],"prompt":"same actor","length":124}},
        "5":{"class_type":"RandomNoise","inputs":{"noise_seed":77}},
        "6":{"class_type":"SamplerCustomAdvanced","inputs":{"latent_image":["4",1],"noise":["5",0]}},
        "7":{"class_type":"VAEDecode","inputs":{"samples":["6",0],"vae":["3",0]}},
        "8":{"class_type":"CreateVideo","inputs":{"images":["7",0],"fps":24.,"audio":["audio",0]}},
        "9":{"class_type":"SaveVideo","inputs":{"video":["8",0],"filename_prefix":"movie/T01"}},
        "audio":{"class_type":"VAEDecodeAudio","inputs":{"samples":["6",0]}}}


class FaceRefineGraphTests(unittest.TestCase):
    def test_long_sequence_sage_guard_covers_model_consumers_once(self):
        graph = source()
        graph['sage'] = {'class_type': SAGE, 'inputs': {'model': ['1', 0]}}
        graph['guide'] = {'class_type': 'BasicGuider', 'inputs': {'model': ['sage', 0]}}
        graph['schedule'] = {'class_type': 'BasicScheduler', 'inputs': {'model': ['sage', 0], 'steps': 20}}
        graph['6']['inputs']['guider'] = ['guide', 0]
        before = deepcopy(graph)
        result = ensure_face_refine(graph)
        guard = 'pemara_sage_guard_sage'
        self.assertEqual(result[guard]['class_type'], SAGE_GUARD)
        for key in ('guide', 'schedule'):
            self.assertEqual(result[key]['inputs']['model'], [guard, 0])
        self.assertEqual(result[guard]['inputs']['model'], ['sage', 0])
        self.assertEqual(result['schedule']['inputs']['steps'], 20)
        self.assertEqual(result['8']['inputs']['audio'], before['8']['inputs']['audio'])
        self.assertEqual(graph, before)
        self.assertEqual(ensure_face_refine(result), result)

    def test_existing_approved_sage_guard_is_reused_without_cycle(self):
        graph = source()
        graph['sage'] = {'class_type': SAGE, 'inputs': {'model': ['1', 0]}}
        graph['guard'] = {'class_type': SAGE_GUARD, 'inputs': {'model': ['sage', 0], 'head_chunks': 8}}
        graph['guide'] = {'class_type': 'BasicGuider', 'inputs': {'model': ['sage', 0]}}
        result = ensure_face_refine(graph)
        self.assertEqual(result['guide']['inputs']['model'], ['guard', 0])
        self.assertEqual(result['guard']['inputs'], graph['guard']['inputs'])
        self.assertEqual(sum(n['class_type'] == SAGE_GUARD for n in result.values()), 1)
        self.assertEqual(ensure_face_refine(result), result)

    def test_rejected_refine_is_removed_and_original_audio_preserved(self):
        graph=source()
        graph['face']={'class_type':NODE,'inputs':{'images':['7',0]}}
        graph['8']['inputs']['images']=['face',0]
        before=deepcopy(graph)
        result=ensure_face_refine(graph)
        self.assertNotIn('face',result)
        self.assertEqual(result['8']['inputs']['images'],['7',0])
        self.assertEqual(result['8']['inputs']['audio'],before['8']['inputs']['audio'])
        self.assertEqual(graph,before)
        self.assertEqual(ensure_face_refine(result),result)

    def test_new_h3_variants_never_add_refine(self):
        for kind in ('MiniMaxH3ImageToVideo','MiniMaxH3ReferenceToVideo','LTXVImgToVideo'):
            graph=source(kind)
            self.assertEqual(ensure_face_refine(graph),graph)

    def test_disabled_policy(self):
        from h3_face_refine import policy
        self.assertFalse(policy()['enabled'])
        self.assertFalse(policy()['default'])

    def test_report_consumer_refused_instead_of_silent_corruption(self):
        graph=source()
        graph['face']={'class_type':NODE,'inputs':{'images':['7',0]}}
        graph['report']={'class_type':'SaveText','inputs':{'text':['face',1]}}
        with self.assertRaisesRegex(ValueError,'report consumer'):
            ensure_face_refine(graph)

    def test_nested_refines_resolve_to_original(self):
        graph=source()
        graph['face1']={'class_type':NODE,'inputs':{'images':['7',0]}}
        graph['face2']={'class_type':NODE,'inputs':{'images':['face1',0]}}
        graph['8']['inputs']['images']=['face2',0]
        result=ensure_face_refine(graph)
        self.assertEqual(result['8']['inputs']['images'],['7',0])
        self.assertFalse(any(n['class_type']==NODE for n in result.values()))

if __name__=='__main__': unittest.main()
