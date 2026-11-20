"""Project photography, per-shot overrides and reviewed visual elements."""
from pathlib import Path
from uuid import uuid4
import hashlib
import io

from PIL import Image
import video_projects as vp
from production_presets import asset_records, asset_path

FIELDS = {"lighting":100,"palette":100,"framing":80,"lens":80,"movement":100}
ROLES = {"personagem","cenário","objeto","figurino"}
LABELS = {"lighting":"Lighting","palette":"Color palette","framing":"Framing","lens":"Lens","movement":"Camera movement"}


class Conflict(ValueError):
    pass


def folder_for(root, project):
    folder = vp._project_path(root,project)
    if not folder.is_dir():
        raise FileNotFoundError(project)
    return folder


def path_for(folder):
    folder = folder.resolve()
    path = (folder/"edit"/"cinema"/"direction.json").resolve()
    if not path.is_relative_to(folder):
        raise ValueError("Pasta da direção inválida.")
    return path


def read(folder):
    return vp._read_json(path_for(folder)) or {"revision":0,"look":{},"shots":{},"elements":[]}


def visible_take(folder, tid):
    record = vp._take_record(vp._queue(folder),vp._validate_take_id(tid))
    if record.get("visible_in_maestro") is False or record.get("role")=="project_final_output":
        raise FileNotFoundError(tid)
    return record


def gallery(folder, data):
    items = list(data["elements"])
    for a in asset_records(folder):
        if a.get("status")=="APPROVED":
            items.append({"id":"asset."+a["id"],"name":a.get("title") or a["id"],"role":a.get("roleLabel") or "referência",
                          "sha256":a["sha256"]})
    return items


def view(folder):
    data = read(folder)
    return dict(data, elements=gallery(folder,data))


def save(folder, body):
    tid = body.get("takeId")
    look = body.get("values")
    allowed = FIELDS if tid else {"lighting":100,"palette":100}
    if not isinstance(look,dict) or set(look)-set(allowed):
        raise ValueError("Campos de fotografia inválidos.")
    clean = {}
    for k,v in look.items():
        if not isinstance(v,str) or len(v)>allowed[k]:
            raise ValueError("Valor de fotografia inválido.")
        if v.strip():
            clean[k] = v.strip()
    with vp._QUEUE_MUTATION_LOCK:
        data = read(folder)
        if body.get("revision") != data["revision"]:
            raise Conflict("A direção mudou em outro aparelho. Reabra o painel.")
        if tid:
            visible_take(folder,tid)
            ids = body.get("elements",[])
            if not isinstance(ids,list) or len(ids)>20 or not all(isinstance(i,str) for i in ids):
                raise ValueError("Seleção de referências inválida.")
            library = {i["id"]:i for i in gallery(folder,data)}
            if any(i not in library for i in ids):
                raise ValueError("Referência revisada indisponível.")
            data["shots"][tid] = {"values":clean,"elements":list(dict.fromkeys(ids))}
        else:
            data["look"] = clean
        data["revision"] += 1
        vp._atomic_json_write(path_for(folder),data)
        return view(folder)


def add_element(folder, name, role, blob):
    folder = folder.resolve()
    if not isinstance(name,str) or not 1<=len(name.strip())<=100 or role not in ROLES or not 0<len(blob)<=8*1024**2:
        raise ValueError("Informe nome, categoria e imagem de até 8 MB.")
    try:
        with Image.open(io.BytesIO(blob)) as img:
            if img.format not in {"PNG","JPEG","WEBP"} or img.width*img.height>24_000_000 or getattr(img,"is_animated",False):
                raise ValueError("Imagem não suportada.")
            ext = {"PNG":"png","JPEG":"jpg","WEBP":"webp"}[img.format]
            img.verify()
    except (OSError,Image.DecompressionBombError) as exc:
        raise ValueError("Imagem inválida.") from exc
    sha = hashlib.sha256(blob).hexdigest()
    with vp._QUEUE_MUTATION_LOCK:
        data = read(folder)
        for item in data["elements"]:
            if (item["name"],item["role"],item["sha256"])==(name.strip(),role,sha):
                return view(folder)
        if len(data["elements"])>=200: raise ValueError("Limite de 200 elementos por projeto.")
        item = {"id":uuid4().hex,"name":name.strip(),"role":role,"sha256":sha,"ext":ext}
        p = (path_for(folder).parent/"elements"/(sha+"."+ext)).resolve()
        if not p.is_relative_to(folder): raise ValueError("Pasta de elementos inválida.")
        vp._atomic_bytes_write(p,blob)
        data["elements"].append(item)
        data["revision"] += 1
        vp._atomic_json_write(path_for(folder),data)
        return view(folder)


def element_file(folder, key):
    folder = folder.resolve()
    if key.startswith("asset."):
        source, record = asset_path(folder,key[6:])
        if record.get("status")!="APPROVED": raise FileNotFoundError(key)
        return source
    item = next((e for e in read(folder)["elements"] if e["id"]==key),None)
    if not item: raise FileNotFoundError(key)
    p = (path_for(folder).parent/"elements"/(item["sha256"]+"."+item["ext"])).resolve()
    if not p.is_relative_to(folder) or not p.is_file(): raise FileNotFoundError(key)
    with p.open("rb") as stream:
        if hashlib.file_digest(stream,"sha256").hexdigest()!=item["sha256"]: raise Conflict("A referência mudou.")
    return p


def prompt_direction(folder, tid, control=None):
    data = read(folder)
    shot = data["shots"].get(tid,{})
    values = dict(data["look"],**shot.get("values",{}))
    pieces = [f"{label}: {values[k]}." for k,label in LABELS.items() if k in values]
    ids = shot.get("elements",[])
    if ids:
        library = {i["id"]:i for i in gallery(folder,data)}
        # Extra pictures are supported only on an explicitly selected Ref2VA graph.
        ref_mode = bool(control and control.get("mode")=="ref2va_motion")
        known = {vp._file_sha256(p) for p in control["referenceImages"]} if ref_mode else set()
        for key in ids:
            if key not in library: raise ValueError("Referência de continuidade indisponível.")
            source = element_file(folder,key)
            asset = library[key]
            pieces.append(f"Continuity reference ({asset['role']}): {asset['name']}.")
            if ref_mode and asset["sha256"] not in known:
                if len(control["referenceImages"])>=9:
                    raise ValueError("Ref2VA comporta nove imagens somando âncoras e referências selecionadas.")
                control["referenceImages"].append(source)
                picture = f"<Picture {len(control['referenceImages'])}>"
                control["referenceDefinitions"].append({"label":picture,"anchorId":key,"role":asset["role"]})
                control["referenceSubjects"].append({"label":f"<Subject {len(control['referenceSubjects'])+1}>",
                    "description":asset["name"],"sources":[picture],"relation":"fully_preserved",
                    "retention":"Preserve the reviewed visual appearance of this element."})
                known.add(asset["sha256"])
    return " ".join(pieces)

