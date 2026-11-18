"""Apply the owner-requested replacement; originals are backed up separately."""
from pathlib import Path
import ast

root = Path('E:/Pemara/maestro/pemara')
path = root / 'services/studio/main.py'
source = path.read_text(encoding='utf-8-sig')
tree = ast.parse(source)
lines = source.splitlines(keepends=True)
replacements = {
    '_build_qwen_image_workflow': '''def _build_qwen_image_workflow(prompt, negative, model, lora, lora_strength,
                               width, height, steps, cfg, seed, prefix):
    if lora:
        raise ValueError("As LoRAs do Qwen antigo não são compatíveis com o Qwen-Image 2.1.")
    return _build_qwen21_workflow(prompt, negative, model, width, height, steps, cfg, seed, prefix)
''',
    '_build_qwen_edit_workflow': '''def _build_qwen_edit_workflow(prompt, negative, model, width, height, steps, cfg,
                              seed, prefix, base_image_name):
    return _build_qwen21_workflow(prompt, negative, model, width, height, steps, cfg,
                                 seed, prefix, base_image_name)
''',
}
for node in sorted([n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in replacements],
                   key=lambda n: n.lineno, reverse=True):
    lines[node.lineno-1:node.end_lineno] = [replacements[node.name]]
source = ''.join(lines)
source = 'from qwen21_workflow import build_workflow as _build_qwen21_workflow\n' + source
source = source.replace('"qwen_image_2512_fp8_e4m3fn.safetensors"', '"qwen_image_2.1_int8_convrot.safetensors"')
source = source.replace('"qwen_image_edit_2511_fp8mixed.safetensors"', '"qwen_image_2.1_int8_convrot.safetensors"')
source = source.replace('DEFAULT_QWEN_LORA = "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"\n', '')
source = source.replace('DEFAULT_QWEN_VAE = "qwen_image_vae.safetensors"\n', '')
source = source.replace('DEFAULT_QWEN_CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"\n', '')
source = source.replace('m.lower().startswith("qwen_image") and "_edit_" not in m.lower()', 'm == DEFAULT_QWEN_MODEL')
source = source.replace('m.lower().startswith("qwen_image_edit")', 'm == DEFAULT_QWEN_EDIT_MODEL')
source = source.replace('''            if selected_lora == DEFAULT_QWEN_LORA:
                st = 4
                cfg = 1.0
''', '')
source = source.replace('DEFAULT_MARKETING_CARD_GUIDANCE = 4.0', 'DEFAULT_MARKETING_CARD_GUIDANCE = 1.0')
source = source.replace('DEFAULT_MARKETING_CARD_STEPS = 52', 'DEFAULT_MARKETING_CARD_STEPS = 40')
source = source.replace('cfg = _safe_float(guidance, 4.0, 1.0, 8.0)', 'cfg = _safe_float(guidance, 1.0, 1.0, 8.0)')
source = source.replace('st = _safe_int(steps, 28, 8, 80)\n        cfg = _safe_float(guidance, 3.5, 1.0, 8.0)',
                        'st = _safe_int(steps, 40 if selected_model == DEFAULT_QWEN_MODEL else 28, 8, 80)\n        cfg = _safe_float(guidance, 1.0 if selected_model == DEFAULT_QWEN_MODEL else 3.5, 1.0, 8.0)')
source = source.replace('_safe_int(width, 1024, 512, 1536, 32)', '_safe_int(width, 1024, 512, 4096 if selected_model == DEFAULT_QWEN_MODEL else 1536, 32)')
source = source.replace('_safe_int(height, 1024, 512, 1536, 32)', '_safe_int(height, 1024, 512, 4096 if selected_model == DEFAULT_QWEN_MODEL else 1536, 32)')
ast.parse(source)
path.write_text(source, encoding='utf-8')

path = root / 'app/assets/maestro.js'
source = path.read_text(encoding='utf-8-sig')
source = source.replace('} else if (mode === "image" && model.startsWith("qwen_image")) {\n    $("#gen-steps").value = 40;\n    $("#gen-guidance").value = 4;',
                        '} else if (["image", "edit", "marketing_card"].includes(mode) && model.startsWith("qwen_image_2.1")) {\n    $("#gen-steps").value = 40;\n    $("#gen-guidance").value = 1;\n    $("#gen-lora").value = "";')
path.write_text(source, encoding='utf-8')

path = root / 'services/studio/h3_workflow.py'
source = path.read_text(encoding='utf-8-sig').replace('Qwen Image 2512 FP8', 'Qwen Image 2.1 INT8').replace('Qwen Image Edit 2511', 'Qwen Image 2.1 Edit')
source = source.replace('qwen_image_2512_fp8_e4m3fn.safetensors','qwen_image_2.1_int8_convrot.safetensors').replace('qwen_image_edit_2511_fp8mixed.safetensors','qwen_image_2.1_int8_convrot.safetensors')
path.write_text(source, encoding='utf-8')
print('Studio migration applied')
