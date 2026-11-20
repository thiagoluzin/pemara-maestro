"""Scene versions and portable episode outlines, shared by Studio and MCP."""
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import hashlib
import math

import video_projects as projects

STAGES = ("direction", "references", "production", "review", "finishing")


def _visible(take):
    return (isinstance(take, dict) and take.get("visible_in_maestro", True) is not False
            and take.get("role") != "project_final_output")


def versions(root, project_id, take_id):
    folder = projects._project_path(root, project_id)
    if not folder.is_dir():
        raise FileNotFoundError(project_id)
    take = projects._take_record(projects._queue(folder), projects._validate_take_id(take_id))
    if not _visible(take):
        raise FileNotFoundError(take_id)
    video = take.get("video") or {}
    history = video.get("output_history") or []
    entries = [("Versão atual", projects._take_output_path(folder, take)),
               ("Candidato de acabamento", projects._upscale_candidate_path(folder, take))]
    entries.extend(("Versão anterior", projects._valid_project_final_video_path(folder, row.get("path")))
                   for row in reversed(history) if isinstance(row, dict))
    seen = set()
    for label, path in entries:
        if not path or path in seen:
            continue
        seen.add(path)
        stat = path.stat()
        token = hashlib.sha256(f"{path.relative_to(folder)}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()
        yield {"versionId": token, "label": label, "file": path.name}, path


def _marks_path(root, project_id, take_id):
    folder = projects._project_path(root, project_id)
    key = projects._validate_take_id(take_id)
    if not folder.is_dir() or not _visible(projects._take_record(projects._queue(folder), key)):
        raise FileNotFoundError(key)
    path = (folder / "edit" / "frame-marks" / (key + ".json")).resolve()
    if not path.is_relative_to(folder):
        raise ValueError("Referência fora do projeto.")
    return path


def list_marks(root, project_id, take_id):
    return projects._read_json(_marks_path(root, project_id, take_id)).get("marks", [])


def mark_frame(root, project_id, take_id, version_id, seconds):
    if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 0 <= seconds <= 7200:
        raise ValueError("Instante inválido.")
    with projects._QUEUE_MUTATION_LOCK:
        if not any(v["versionId"] == version_id for v, _ in versions(root, project_id, take_id)):
            raise FileNotFoundError("Versão")
        record = {"versionId": version_id, "seconds": round(seconds, 3)}
        path = _marks_path(root, project_id, take_id)
        marks = projects._read_json(path).get("marks", [])
        if record not in marks:
            if len(marks) >= 500:
                raise ValueError("Limite de quadros marcados atingido.")
            marks.append(record)
            projects._atomic_json_write(path, {"marks": marks})
        return record


def _title(value, limit=120):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f"O texto precisa ter de 1 a {limit} caracteres.")
    return value.strip()


def _templates(root):
    return root.resolve() / ".episode_templates"


def templates(root):
    folder = _templates(root)
    rows = [projects._read_json(p) for p in folder.glob("*.json")]
    return sorted(rows, key=lambda r: r["createdAt"], reverse=True)


def save_template(root, name, scenes, content_kind, stages=None):
    if content_kind not in {"live_action", "animation", "mixed"}:
        raise ValueError("Defina o tipo da produção.")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 300:
        raise ValueError("Informe entre 1 e 300 cenas.")
    stages = list(STAGES) if stages is None else stages
    if not isinstance(stages, list) or not stages or any(s not in STAGES for s in stages) or len(set(stages)) != len(stages):
        raise ValueError("Escolha etapas válidas sem repetições.")
    normalized = []
    for s in scenes:
        if not isinstance(s, dict):
            raise ValueError("Cena inválida.")
        seconds = float(s.get("durationSeconds") or 0)
        if not math.isfinite(seconds) or not 0 < seconds <= 7200:
            raise ValueError("Duração de cena inválida.")
        direction = s.get("direction", "")
        if not isinstance(direction, str) or len(direction) > 6000:
            raise ValueError("A direção deve ter até 6000 caracteres.")
        row = {"name": _title(s.get("name")), "durationSeconds": seconds, "direction": direction.strip()}
        if s.get("photography"):
            from cinema_direction import FIELDS
            photo = s["photography"]
            if not isinstance(photo,dict) or any(k not in FIELDS or not isinstance(v,str) or len(v)>FIELDS[k] for k,v in photo.items()):
                raise ValueError("Fotografia do plano inválida.")
            row["photography"] = {k:v for k,v in photo.items() if v}
        normalized.append(row)
    if not 1 <= sum(s["durationSeconds"] for s in normalized) <= 7200:
        raise ValueError("A duração total deve ficar entre 1 e 7200 segundos.")
    record = {"templateId": uuid4().hex, "name": _title(name), "contentKind": content_kind,
              "scenes": normalized, "stages": stages, "createdAt": projects.utc_now()}
    folder = _templates(root)
    folder.mkdir(parents=True, exist_ok=True)
    projects._atomic_json_write(folder / (record["templateId"] + ".json"), record)
    return record


def instantiate(root, template_id, name):
    import re
    if not re.fullmatch(r"[a-f0-9]{32}", template_id):
        raise ValueError("Identificador de modelo inválido.")
    template = projects._read_json(_templates(root) / (template_id + ".json"))
    if not template:
        raise FileNotFoundError(template_id)
    name = _title(name)
    project_id = projects._validate_project_id(projects.slugify(name))
    destination = projects._project_path(root, project_id)
    with projects._QUEUE_MUTATION_LOCK, TemporaryDirectory(dir=root, prefix=".episode-") as stage:
        if destination.exists():
            raise FileExistsError(project_id)
        staging = Path(stage)
        projects.create_project(staging, name=name, project_id=project_id, content_kind=template["contentKind"],
                                duration_seconds=sum(s["durationSeconds"] for s in template["scenes"]),
                                distribution_mode="standard")
        folder = staging / project_id
        manifest = projects._read_json(folder / "project_manifest.json")
        manifest["episode_workflow"] = template.get("stages", list(STAGES))
        projects._atomic_json_write(folder / "project_manifest.json", manifest)
        queue = projects._queue(folder)
        queue["episode_template_id"] = template_id
        queue["takes"] = [{"id": f"T{i:02d}", "name": s["name"], "animation_prompt": s["direction"],
                           "target_duration_seconds": s["durationSeconds"], "maestro_status": "PLANNED",
                           "base_image": {}, "video": {}} for i, s in enumerate(template["scenes"], 1)]
        projects._atomic_json_write(projects._queue_path(folder), queue)
        from cinema_direction import read, path_for
        cinema = read(folder)
        for i,s in enumerate(template["scenes"],1):
            if s.get("photography"):
                cinema["shots"][f"T{i:02d}"]={"values":s["photography"],"elements":[]}
        if cinema["shots"]:
            projects._atomic_json_write(path_for(folder),cinema)
        folder.rename(destination)
    return projects.get_project(root, project_id)


def save_project_template(root, project_id, name):
    folder = projects._project_path(root, project_id)
    if not folder.is_dir():
        raise FileNotFoundError(project_id)
    with projects._QUEUE_MUTATION_LOCK:
        manifest = projects._read_json(folder / "project_manifest.json")
        scenes = [{"name": t.get("name") or t.get("slug") or t.get("id"),
                   "durationSeconds": t.get("target_duration_seconds"),
                   "direction": t.get("animation_prompt") or t.get("prompt") or t.get("objective") or ""}
                  for t in projects._queue(folder)["takes"] if _visible(t)]
        return save_template(root, name, scenes, manifest.get("content_kind"), manifest.get("episode_workflow"))

