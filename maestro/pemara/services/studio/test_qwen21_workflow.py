import ast
from pathlib import Path
import unittest

from qwen21_workflow import MODEL, build_workflow


class Qwen21Tests(unittest.TestCase):
    def test_edit_samples_encoder_latent_at_requested_reference_dimensions(self):
        graph = build_workflow('Blue teapot', '', MODEL, 1536, 1024, 40, 1, 42, 'test', 'input.png')
        self.assertEqual(graph['6']['inputs']['latent_image'], ['4', 2])
        self.assertEqual(graph['4']['inputs']['resolution'], 0)
        self.assertEqual(graph['4']['inputs']['images.image_1'], ['10', 0])
        self.assertEqual(graph['10']['inputs']['width'], 1536)
        self.assertEqual(graph['10']['inputs']['height'], 1024)
        self.assertNotIn('5', graph)

    def test_new_model_rejects_retired_checkpoint(self):
        with self.assertRaises(ValueError):
            build_workflow('test', '', 'qwen_image_2512_fp8_e4m3fn.safetensors',
                           1024, 1024, 40, 1, 42, 'test')

    def test_studio_wrapper_rejects_incompatible_lightning_lora(self):
        tree = ast.parse(Path(__file__).with_name('main.py').read_text(encoding='utf-8-sig'))
        funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ('_build_qwen_image_workflow', '_build_qwen_edit_workflow')]
        scope = {'_build_qwen21_workflow': build_workflow}
        exec(compile(ast.Module(body=funcs, type_ignores=[]), '<studio-qwen>', 'exec'), scope)
        with self.assertRaises(ValueError):
            scope['_build_qwen_image_workflow']('test', '', MODEL, 'old-Lightning.safetensors',
                                               1, 1024, 1024, 40, 1, 42, 'test')
        graph = scope['_build_qwen_image_workflow']('test', '', MODEL, '', 0,
                                                   2048, 2048, 40, 1, 42, 'test')
        self.assertEqual(graph['5']['inputs']['width'], 2048)
        self.assertEqual(graph['6']['inputs']['positive'], ['4', 0])
        self.assertEqual(graph['6']['inputs']['negative'], ['4', 1])
        self.assertEqual(graph['4']['inputs']['images'], {})


if __name__ == '__main__':
    unittest.main()
