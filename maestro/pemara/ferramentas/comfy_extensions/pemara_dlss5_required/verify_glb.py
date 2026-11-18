"""Validate self-contained GLB in Maestro's existing isolated 3D environment."""
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import numpy as np
from PIL import Image
import trimesh


def verify_glb(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError('GLB truncado: cabecalho ausente.')
        magic, version, length = struct.unpack('<4sII', header)
        if magic != b'glTF' or version != 2 or length != size:
            raise ValueError('GLB invalido: cabecalho, versao ou tamanho divergente.')
        chunks = []
        while stream.tell() < size:
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError('GLB com cabecalho de chunk truncado.')
            chunk_length, chunk_type = struct.unpack('<II', header)
            if chunk_length % 4 or chunk_length > size - stream.tell():
                raise ValueError('GLB com chunk truncado ou desalinhado.')
            chunks.append((chunk_type, stream.read(chunk_length)))
    if not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError('GLB sem primeiro chunk JSON.')
    document = json.loads(chunks[0][1])
    if document.get('asset', {}).get('version') != '2.0':
        raise ValueError('GLB exige asset glTF 2.0.')
    buffers = document.get('buffers', [])
    images = document.get('images', [])
    if any('uri' in b for b in buffers) or any('uri' in i and not i['uri'].startswith('data:') for i in images):
        raise ValueError('GLB exige recursos incorporados para entrega remota.')
    binary = next((data for kind, data in chunks[1:] if kind == 0x004E4942), b'')
    if len(buffers) > 1 or (buffers and not 0 <= len(binary) - buffers[0]['byteLength'] <= 3):
        raise ValueError('GLB com buffer binario ausente ou tamanho divergente.')
    for view in document.get('bufferViews', []):
        if view['buffer'] != 0 or view.get('byteOffset', 0) < 0 or view['byteLength'] <= 0 or view.get('byteOffset', 0) + view['byteLength'] > (buffers[0]['byteLength'] if buffers else 0):
            raise ValueError('GLB com bufferView fora do buffer incorporado.')
    for image in images:
        if 'uri' in image:
            data = base64.b64decode(image['uri'].split(',', 1)[1], validate=True)
        else:
            view = document['bufferViews'][image['bufferView']]
            offset = view.get('byteOffset', 0)
            data = binary[offset:offset + view['byteLength']]
        with Image.open(io.BytesIO(data)) as decoded:
            decoded.verify()
    scene = trimesh.load(path, force='scene', process=False)
    if not scene.geometry:
        raise ValueError('GLB sem geometria.')
    vertices = faces = 0
    for mesh in scene.geometry.values():
        if (not isinstance(mesh, trimesh.Trimesh) or not len(mesh.vertices) or not len(mesh.faces)
            or not np.isfinite(mesh.vertices).all() or mesh.faces.min() < 0 or mesh.faces.max() >= len(mesh.vertices)
            or not np.any(mesh.area_faces > 0)):
            raise ValueError('GLB com malha vazia, degenerada ou indices/coordenadas invalidos.')
        vertices += len(mesh.vertices)
        faces += len(mesh.faces)
    materials = document.get('materials', [])
    textures = document.get('textures', [])
    for texture in textures:
        source = texture.get('source')
        if not isinstance(source, int) or not 0 <= source < len(images):
            raise ValueError('GLB com textura sem imagem valida.')
    for mesh in document.get('meshes', []):
        for primitive in mesh.get('primitives', []):
            if 'material' in primitive and not 0 <= primitive['material'] < len(materials):
                raise ValueError('GLB com referencia de material invalida.')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'format':'glb', 'version':version, 'bytes':size, 'sha256':digest,
        'meshes':len(scene.geometry), 'vertices':vertices, 'faces':faces, 'bounds':scene.bounds.tolist(),
        'materials':len(materials), 'textures':len(textures), 'images':len(images),
        'technical_pass':True, 'dlss5_applied':False, 'owner_approval':'PENDING'}


if __name__ == '__main__':
    print(json.dumps(verify_glb(sys.argv[1])))
