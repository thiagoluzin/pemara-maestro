"""Restore the exact qualified RIFE 4.25 weight; never render or substitute models."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

MODEL_SHA256 = '6615790efd627772917205db291f51cd392528a157ecbb2ecaeec3bff8eb6de2'
MODEL_BYTES = 24636301
OFFICIAL_URL = 'https://drive.google.com/file/d/1ZKjcbmt1hypiFprJPIKW0Tt0lr_2i7bg/view'
SOURCE = Path(__file__).parent / 'rife425_source'


def verify(target):
    destination = Path(target).resolve() / 'third_party/Practical-RIFE/train_log'
    weight = destination / 'flownet.pkl'
    if not weight.is_file() or hashlib.sha256(weight.read_bytes()).hexdigest() != MODEL_SHA256:
        raise ValueError('RIFE 4.25 ausente ou com hash diferente.')
    sources = list(SOURCE.glob('*.py'))
    if len(sources) != 3 or any(not (destination / p.name).is_file() or (destination / p.name).read_bytes() != p.read_bytes() for p in sources):
        raise ValueError('Fontes RIFE 4.25 ausentes ou divergentes.')
    return {'status': 'PASS', 'version': '4.25', 'sha256': MODEL_SHA256, 'target': str(destination)}


def install(archive, target):
    target = Path(target).resolve()
    destination = target / 'third_party/Practical-RIFE/train_log'
    weight = destination / 'flownet.pkl'
    if weight.exists():
        if hashlib.sha256(weight.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError('RIFE existente diferente: preservar e revisar antes de substituir.')
    with zipfile.ZipFile(archive) as package:
        candidates = [item for item in package.infolist() if Path(item.filename).name == 'flownet.pkl']
        if len(candidates) != 1 or candidates[0].file_size != MODEL_BYTES:
            raise ValueError('O pacote nao contem exatamente o peso RIFE 4.25 esperado.')
        data = package.read(candidates[0])
    if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
        raise ValueError('Hash RIFE incorreto: nenhum arquivo foi instalado.')
    sources = sorted(SOURCE.glob('*.py'))
    if len(sources) != 3:
        raise ValueError('Fontes qualificadas RIFE ausentes.')
    for source in sources:
        existing = destination / source.name
        if existing.exists() and existing.read_bytes() != source.read_bytes():
            raise ValueError('Fonte RIFE local diferente: revisar antes de substituir ' + source.name)
    destination.mkdir(parents=True, exist_ok=True)
    if not weight.exists():
        temporary = destination / 'flownet.pkl.installing'
        with temporary.open('xb') as stream:
            stream.write(data)
        os.replace(temporary, weight)
    for source in sources:
        if not (destination / source.name).exists():
            shutil.copy2(source, destination / source.name)
    return {'status': 'PASS', 'version': '4.25', 'sha256': MODEL_SHA256, 'target': str(destination)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-root', default=os.environ.get('PEMARA_ROOT', 'E:/Pemara'))
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--accept-license', action='store_true')
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({'dryRun': True, 'version': '4.25', 'sha256': MODEL_SHA256, 'bytes': MODEL_BYTES,
                          'source': OFFICIAL_URL, 'targetRoot': args.target_root, 'render': False}))
        return
    if args.verify:
        print(json.dumps(verify(args.target_root)))
        return
    if not args.accept_license:
        parser.error('Confirme a licenca MIT do Practical-RIFE com --accept-license.')
    if args.archive:
        print(json.dumps(install(args.archive, args.target_root)))
        return
    existing = Path(args.target_root) / 'third_party/Practical-RIFE/train_log/flownet.pkl'
    if existing.exists():
        print(json.dumps(verify(args.target_root)))
        return
    if importlib.util.find_spec('gdown') is None:
        parser.error('Instale o downloader: python -m pip install gdown==6.1.0; ou use --archive pacote.zip.')
    import gdown
    with tempfile.TemporaryDirectory(prefix='pemara-rife425-') as temporary:
        archive = Path(temporary) / 'rife425.zip'
        result = gdown.download(OFFICIAL_URL, str(archive), fuzzy=True, quiet=False)
        if result is None or not archive.is_file():
            raise RuntimeError('Fonte oficial indisponivel: sem fallback de versao.')
        print(json.dumps(install(archive, args.target_root)))


if __name__ == '__main__':
    main()
