import hashlib,json
from pathlib import Path
from huggingface_hub import model_info
from transformers import DINOv3ViTModel, AutoImageProcessor
root=Path('D:/PemaraRuntimes/maestro-game-ai/apps/ComfyUI/models/facebook/dinov3-vitl16-pretrain-lvd1689m')
repo='facebook/dinov3-vitl16-pretrain-lvd1689m'
rev='ea8dc2863c51be0a264bab82070e3e8836b02d51'
info=model_info(repo,revision=rev,files_metadata=True)
files=[]
for f in info.siblings:
 p=root/f.rfilename
 if not p.is_file(): continue
 h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
 if f.lfs: assert h==f.lfs.sha256, 'SHA256 mismatch'
 files.append({'path':f.rfilename,'bytes':p.stat().st_size,'sha256':h})
print('HASHES_VERIFIED',flush=True)
model=DINOv3ViTModel.from_pretrained(str(root),local_files_only=True)
processor=AutoImageProcessor.from_pretrained(str(root),local_files_only=True)
receipt={'repo':repo,'revision':rev,'files':files,'cpuModelLoadPassed':True,'processorLoadPassed':True,'full3dGenerationTested':False,'parameters':sum(p.numel() for p in model.parameters())}
(root/'maestro-weights-verified.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='files'}),flush=True)
