"""Project-scoped assets with role mapping and exact content identity."""
from pathlib import Path
import hashlib
from .ir import CreativeError, identifier

ROLES = {"character_identity", "prop_geometry", "environment", "wardrobe", "motion_reference", "audio_reference", "style_reference", "first_frame", "last_frame", "generated_video", "latent"}


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise CreativeError("ASSET_PATH", "Use caminho relativo com barras /.")
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise CreativeError("ASSET_PATH", "Arquivo não encontrado dentro do projeto.")
    return path


class Assets:
    def __init__(self, store, projects_root):
        self.store, self.root = store, Path(projects_root).resolve()

    def register(self, project_id, relative_path, role):
        identifier(project_id)
        if role not in ROLES: raise CreativeError("ASSET_ROLE", "Papel do asset inválido.")
        path = safe_path(self.root / project_id, relative_path)
        record = self.store.put("assets", {"project_id": project_id, "relative_path": relative_path,
            "role": role, "sha256": file_hash(path), "size": path.stat().st_size})
        return {**record, "uri": f"asset://{project_id}/{record['id']}"}

    def resolve(self, asset_id, project_id, *, image=False):
        if str(asset_id).startswith("asset://"):
            parts = asset_id[8:].split("/")
            if len(parts) != 2 or parts[0] != project_id: raise CreativeError("ASSET_SCOPE", "Asset de outro projeto.")
            asset_id = parts[1]
        record = self.store.get("assets", asset_id)
        if record["project_id"] != project_id: raise CreativeError("ASSET_SCOPE", "Asset de outro projeto.")
        path = safe_path(self.root / project_id, record["relative_path"])
        if path.stat().st_size != record["size"] or file_hash(path) != record["sha256"]:
            raise CreativeError("ASSET_CHANGED", "Asset mudou desde o registro.", 409)
        if image and (path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} or path.stat().st_size > 64*1024*1024):
            raise CreativeError("INVALID_IMAGE", "Imagem inválida ou maior que 64 MB.")
        return path, record

    def reference_sheet(self, project_id):
        identifier(project_id)
        return {"version": 1, "project_id": project_id, "format": "creative_os_reference_sheet",
                "external_plugin_compatible": False,
                "assets": [{**a, "uri": f"asset://{project_id}/{a['id']}"}
                           for a in self.store.list("assets", 500) if a["project_id"] == project_id]}
